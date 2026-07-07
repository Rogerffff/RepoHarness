# P3 预实验脚本包 implementation-notes（三节制）

范围：把 `8gpu_preflight_protocol.md` 实体化为 `rh2/experiments/p3_preflight/`
执行脚本包（纯本地编写 + 静态验证，无 GPU）。本文只记重要事项；执行期
（真机）事项跑完后追加。

## 1. 设计决策与偏离

- **J3 的"合成 batch 过 Megatron train step"实现方式**：用 slime 自带的
  `--debug-train-only` + `--load-debug-rollout-data`（`ray/rollout.py:636`
  直接从 .pt 读样本、完全不起 SGLang），配 `lib/make_synth_rollout.py` 生成
  `--save-debug-rollout-data` 同格式的合成数据（64 条 × 目标长度，含形状
  正确的 routing tape `(len(tokens)-1, 48, 8)` 与 top-p tape，组内 reward
  0/1 交替保证 GRPO 非零方差）。合成 tape 是随机值：J3 只测显存/耗时/内核
  路径，数值正确性归 J4 真实链路——这是 F2（链路问题与硬件问题不混查）的
  刻意选择。
- **J4c 默认用 Qwen3-4B 而非 30B**（可 `J4C_MODEL_*` 覆盖）：J4c 验证的是
  机制（fully_async 可启动性 + 我方 custom_generate 对 ABORTED 组的行为
  三元组），与模型规模无关；0.5h 时间盒内起 30B 服务不划算，且 4B 是 7a
  已就位资产。三元组打点用包装模块 `p3_preflight.lib.j4c_probe.generate`
  （透明转发给 `s1_7a_bringup.glue.generate`），为此 `p3_preflight/` 与
  `lib/` 加了 `__init__.py` 成为 package。
- **改动了 7a 的 `glue.py`（默认行为不变）**：加环境旋钮
  `RH2_EXPECT_MOE_ROUTING`（默认 "0" = 7a dense 行为逐字不变）。原因：
  glue 原来把 `expect_moe_routing` / 探针 `return_routed_experts` 硬编码
  False（Qwen3-4B dense），J4 的 30B MoE 必须请求 routing tape 否则判据 3
  （loss 消费 rollout_routed_experts）物理不可能过。这是 H-3"J4 复用 S1
  产物接口确认"暴露的真实缺口，改在 7a 文件里而非复制一份 glue，是为了
  单一事实源；7a 的 container_train.sh 未动。
- **J0 权重 digest 口径**：<8MB 小文件（config/index/tokenizer）逐个
  sha256，大权重文件默认记 (size, path) manifest，manifest 本身 sha256 作为
  目录级 digest；`P3_FULL_DIGEST=1` 才全量 sha256（~60GB 顺序读）。P-3 要求
  "digest 入 evidence"，全量哈希默认档太贵且 index 文件已含每个分片的期望
  内容。
- **尾部空闲占比的 step 归属**：`bringup_events.jsonl` 没有 rollout_id，
  `lib/tail_idle.py` 按完成时间戳的最大间隙聚成 `--steps` 簇近似 step 边界
  （J4b 每拓扑 2~3 步下稳定）；口径本体（util<30% 阈值、尾段起点 = 最后
  25% 轨迹开始完成时刻）照协议原文实现。
- **静态核对约定**：slime flag 一律写在 `*_ARGS=( … )` bash 数组里，非
  slime 命令（sglang.launch_server / nccl-tests / docker）的 flag 不进
  `*_ARGS`——`tests/check_p3_scripts.py` 靠这个约定抽 flag 逐个对照
  `reference/slime` 语料（arguments.py ×3 + scripts/tests/examples）。

## 2. 参数核对发现（协议 vs slime 源码，每条脚本已按源码为准）

- **协议 J3 附④"colocate = IPC tensor"不是 CLI 值**：
  `--update-weight-transport` 的 choices 只有 `{nccl, disk}`
  （`arguments.py:146`）；colocate 的 CUDA IPC 是
  `update_weight_from_tensor.py` 内部实现，不由该 flag 表达。脚本一律
  `--update-weight-mode full --update-weight-transport nccl`（分离与
  colocate 对照都适用）。
- **两个 routing replay flag 是不同参数**：协议 J3 附引用锚
  `tests/test_qwen3_30B_A3B.py` 用的是 `--use-routing-replay`
  （`arguments.py:1080`，arXiv 2507.18071）；协议正文要求必开的是
  `--use-rollout-routing-replay`（`arguments.py:1086`，arXiv 2510.11370，
  rollout tape 回放）。脚本按协议正文开后者；引用锚只作并行参数参照。
- **优化器三连 flag 属 Megatron 侧**：`--optimizer-cpu-offload` /
  `--overlap-cpu-optimizer-d2h-h2d` / `--use-precision-aware-optimizer`
  不在 slime `utils/arguments.py`（官方 30B 测试在用，Megatron 解析）。
  注意 `megatron_utils/arguments.py:161-162` 有 optimizer-cpu-offload 的
  ckpt saving bug workaround（`dist_ckpt_save_pre_mcore_014=True`）——J4
  存 checkpoint 时若报 ckpt 错误先查这里。
- **两个 sglang 透传 flag 在 slime 仓库 grep 不到但真实存在**：
  `--sglang-sampling-backend` / `--sglang-disable-cuda-graph` 是
  `sglang_utils/arguments.py:34` 对 SGLang ServerArgs 的自动前缀透传
  （S1-0/7a 在 pin 镜像实跑验证过的 sm_120 规避组合）；
  `tests/check_p3_scripts.py` 白名单显式列出并注明依据。
- **J5"pause/flush/continue 三段停顿分解"无现成打点**：pin `e848052a` 只有
  `@timer def update_weights` 总耗时（日志键 `perf/update_weights_time`，
  `train_metric_utils.py:27`）；三段在
  `update_weight_from_distributed.py:110-133` 是裸 `ray.get`。
  `lib/j5_parse.py` 用 tqdm "Update weights" 时间窗近似 send 段、
  pause/continue 只给上界，报告字段 `three_phase_resolved` 如实标注；
  精确三段需轻量 patch，P3 不改 pin 代码（P-9 纪律）。
- **`weight_versions` 是 `list[str]`**（`types.py:120`），协议/H-1 行文写
  "list"——`lib/m1_staleness_hist.py` 对版本号做 int 转换容错后再算跨度。

## 3. 开放问题（租机后核对/用户确认）

- **分区 GPU 编号假设**：J4/J4b/J5 假设 actor 占前段、rollout 占后段
  （T3 = 0-3 训 / 4-7 推）。ray placement 实际分配需租机后用日志/
  `ray status` 核对，`tail_idle.py --rollout-gpus` 按实际改——写错分区会把
  训练卡的空闲算进 rollout 尾部空闲。
- **J4 动态采样 filter 与 8 题冻结集的相互作用**：filter 丢零方差组时
  会从全局数据集补采 → 8 题集上等于 epoch 回绕重采同题。若观察到 batch
  饥饿，按协议 J4 条款降级（显式关 filter 并记录偏离）。
- **step 墙钟解析的保守性**：`lib/parse_step_metrics.py` 优先抓
  `perf/*_time` 日志键；抓不到时回落"整个 ray job 墙钟 ÷ 步数"（含 ray
  启动、加载、warmup，偏保守）。若 J3 绿灯判定卡在 15min 线附近，先人工
  复核 dmon 曲线再定档。
- **J2 吞吐口径**：`sglang.bench_serving` 的 random 数据集（in 4096/out
  1024）不是 SWE agent 的真实请求形态（多轮长 prefix + radix cache 命中），
  J2 数字只作画像下界；真实形态吞吐以 J4/J4b 的 rollout 段为准。
