# 8 卡预实验协议（P3）：训练侧未知关闭 + 吞吐画像

定位：一次性 8×RTX Pro 6000 租用的**测量协议**——租卡按墙钟计费，本文把"测什么、按什么顺序、每项的通过判据与放弃线"预先定死，租到卡照单执行。姊妹单卡作业（pass-rate 预筛 + pre-RL 诊断）规格见 §6。

**执行时机**：最早 = S1 闭环收口后（依赖 S1-6 编排胶水与 7a 验证过的链路）；截止 = S4 开训前。**推荐贴前不贴后**——本协议的放弃线带"重议 E1 / 换硬件"的推翻性结论，越早知道越好；它不依赖 S2/S3（安全加固与治理评分不碰训练内核），预实验数据即弃。

要关闭的未知（对账清单）：

```text
U-C  训练侧四项：Megatron 内核在 sm_120 可用性 / PCIe all-to-all 实测带宽 /
     colocate 训推显存水位与 sleep-resume 切换 / CPU offload 的 step 时间代价
S1-7b  30B-A3B 全要素训练 step（routing tape + top-p tape 首次真实进 loss）
E6 回填  "训练 step 10~30min" 纸面估算 → 实测；C3 墙钟反推的输入
权重同步  update_weights 到 rollout 引擎的耗时
```

---

## 1. 前置条件（租卡前完成，缺一不租）

```text
P-1 slime 镜像 digest 已 pin（S1-0 产物）且 U-H 已关闭
P-2 S1 闭环代码 commit 固定；7a 报告在手（bring-up 链路已验证）
P-3 Qwen3-30B-A3B 权重的获取方案确认——**双路径（codex 二轮核查）**：
    rollout 侧用 HF checkpoint；训练侧必须先用 slime 的
    convert_hf_to_torch_dist.py 转成 Megatron torch_dist 格式
    （转换命令、模型脚本、路径与 digest 全部入 evidence；转换本身
    需要 GPU/大内存，计入 J0 时间盒或提前在单卡租用时做）
    （~60GB：租用机带宽实测后
    决定现场拉取还是对象存储中转；下载时间计入 J0 时间盒）
P-4 8 题冻结集镜像引用与 J4 运行配置写成脚本（复用 S0 探针形态）
P-5 nccl-tests 二进制或构建脚本备好（J1 用）
P-6 记录模板（本文 §5）与 nvidia-smi/dmon 采样脚本备好
P-7 主机内存分档确认：**400GB = 勉强最低线，≥512GB = 推荐线**
    （拆账：优化器 CPU offload 366GB + Ray object store + SGLang host
    内存 + 评分沙箱同机 + 双缓冲期两批数据在途 + 页缓存/日志；
    须记录 Ray object store 配置）。< 400GB 即提前红灯——
    30B 训练在本机不成立，直接进 §3 放弃线选项 (b)
P-8 M2 采集脚本提前备好（基于 slime examples/train_infer_mismatch_helper
    的 mis.py 改）——不指望 24h 机时内现写
```

## 1.5 拓扑候选与显存账（2026-07-08 增补：分离放置 + 异步为主案候选）

背景：colocate 同步模式下 agentic rollout 的长尾空等是已知吞吐杀手（用户 verl 实战教训）；slime **原生支持分离放置**（`--rollout-num-gpus N` 不带 `--colocate`）与四档长尾武器（train_async 双缓冲 / over-sampling+动态采样 / `--partial-rollout` + `--mask-offpolicy-in-partial-rollout` / `fully_async_rollout` in-flight 池跨步保活）。显存粗账（Qwen3-30B-A3B：权重 bf16 61GB，KV 96KB/token，32k 单序列 KV 3.0GB）：

```text
训练分区（TP2，权重+梯度 61GB/卡 + 激活 5~15GB @full recompute）：
  6 卡 TP2×DP3 ✓ / 4 卡 TP2×DP2 ✓ / 2 卡 TP2×DP1 ✓（但无 DP，step 慢）
  优化器一律 CPU offload（见 P-7 主机内存硬预检）
rollout 分区（mem-fraction 0.75）：
  2 卡 TP2×1 引擎：权重 30.5GB/卡，KV 池 ~83GB ≈ 27 条满 32k（bf16 KV）
  4 卡 TP2×2 引擎：权重 30.5GB/卡，KV 池 ~166GB ≈ 55 条（官方示例形态）
  6 卡 TP2×3 引擎：KV 池 ~250GB ≈ 83 条（T2′ 的推理侧形态，
    引擎数 = rollout_num_gpus ÷ per-engine TP，须整除）
  4 卡 TP4×1 引擎：权重 15GB/卡，KV 池 ~228GB ≈ 76 条（单引擎大 KV 备选）
  FP8 KV 使容量翻倍；GRPO n=8 同组共享 prompt 前缀（radix cache），
  实际并发容量显著高于上述下界
候选拓扑（2026-07-08 第三轮修订，rollout-heavy 对齐行业惯例）：
  T1 colocate 8 卡  ——纯同步对照（slime train_async.py:11 断言禁
     colocate：colocate 模式下没有双缓冲，只有 train.py 全同步）
  T2′ 分离 2 训 + 6 推 ——对齐 MAI 推理:训练 5.3:1（4096:768 GB300）
     与 RollArt 3:1 的 rollout-heavy 惯例；风险 = 2 卡训练 step 变慢
     反而拉长双缓冲周期，J3 实测定夺
  T3 分离 4 + 4     ——slime fully_async 官方示例同款
     （examples/fully_async：ACTOR 4 / ROLLOUT 4 / TP2×2 引擎）
时间换显存旋钮清单（按代价从小到大）：
  --sglang-mem-fraction-static 下调 / FP8 KV / --recompute-granularity full
  （已默认）/ --optimizer-cpu-offload（必开）/ --offload-train·--offload-rollout
  （colocate 换入换出）/ CP=2 / mbs=1 + --use-dynamic-batch-size
```

## 1.6 异步档位决策（2026-07-08 第三轮调研定案，证据两线程交叉）

**行业证据**：bounded-staleness 异步是分离式大规模 SWE RL 主流（MAI/GLM-5/Composer/RollArt/MiniMax 全带显式准入界），但**上限很紧**——RollArt 默认 α=1 且实测 α=2 后期退化；MiniMax lag 上限个位数；最松的 MAI 也只有 8 次推理更新（40 梯度步）。反例：Kimi K2 同规模刻意选 colocate 同步 + partial rollout（<30s 全参更新）。正确表述是"尽量异步 + 很紧的界"。

**slime 现状（源码级核查）**：分离 + fully_async 是官方支持形态，但四个缺口——
① partial-rollout 的 token 级续接**未接入** fully_async 路径（README 明示 aborted 组"starts over"；样本 tokens 保留使续跑可能意外生效但官方不支持）；
② `--mask-offpolicy` 在 fully_async 下有盲区（引擎 pause/continue 使单次 generate 内 token 跨版本且不被 mask）；
③ **`--dynamic-sampling-filter-path` 与 `--over-sampling-batch-size` 在 fully_async 路径静默失效**（过滤逻辑只在 sglang_rollout 标准路径）——E2 定案的"动态采样默认开"在该路径不成立，需自建；
④ 无原生 staleness 准入旋钮——但记账字段齐全（`Sample.weight_versions` list，types.py:120/382）+ 天然插入点（`--buffer-filter-path`）。

**定案**：
```text
首训档位 = 分离放置（T2′/T3 由 J3/J4b 定）+ train_async 双缓冲
  + staleness 记账（不准入，只记录）。
  理由：双缓冲结构性 staleness 上界 ≈ 1×update_interval 个版本，
  天然落在行业最紧实践（α=1）内，不需自建准入；
  fully_async 的四缺口不该由首训背。
staleness 记账从 S1 起做：weight_versions → TrajectoryProjection
  handshake 字段 → gate 记录分布（为升级决策与 E8 资源证据备数）。
升级档位（预注册触发）= fully_async + 自建三件
  （buffer_filter staleness 准入 α=1 / custom_generate 内重写
  DAPO 过滤 / 整组同版本准入策略）。
  触发条件：J4b 或首训实测 rollout 尾部空闲 > 每步墙钟的 25%。
防误用断言（升级档启用时写进启动脚本）：若 rollout-function-path
  为 fully_async 且设置了 --dynamic-sampling-filter-path 或
  --over-sampling-batch-size，启动即 fail——防止误以为 DAPO
  过滤仍生效（该路径静默忽略这两个参数）。
```

## 2. 作业序列（按信息量排序，总时间盒 ≤ 24h 墙钟）

| # | 作业 | 时间盒 | 关闭什么 |
| --- | --- | --- | --- |
| J0 | 环境就位：镜像/权重/GPU 可见性/`nvidia-smi topo -m` 拓扑留档 | 2h（含下载） | — |
| J0.5 | **训练内核最小冒烟（10min，插 J0 尾）**：slime 镜像单卡跑 tiny dense 模型 1 个 train step——把"Megatron 在 sm_120 一票否决"这个 U-C 核心疑点前置，避免 J1/J2 的 1.5h 白烧 | 0.2h | U-C 内核项预检 |
| J1 | PCIe 通信微基准（nccl-tests：`alltoall_perf` **+ `broadcast_perf` + `all_reduce_perf`**，2/4/8 卡三档——权重同步走 broadcast，只测 all-to-all 画像不完整） | 0.7h | U-C 带宽项 |
| J2 | 推理侧 8 卡 serving 冒烟：SGLang 30B，TP/DP/EP 按 slime 示例缩配，32k 上下文，记 tokens/s 与显存 | 1h | 训推共存的推理半边 |
| J3 | **训练侧并行配置扫描（核心矩阵）**：合成固定 batch 过 Megatron train step | 4h | U-C 内核/显存/step 时间 |
| J4 | **全要素（S1-7b 本体）**：custom_generate，8 题 × **n=4**（n=2 会被动态采样饿死 batch，与 S1-7a 的 A2 条款同款坑——注意对称性：fully_async 里怕 filter 静默失效，标准路径里怕 filter 活着饿死 batch；若必须 n=2 则显式关 filter 并记录偏离），E2 生产 flags，真实训练 step——在 T3（4+4，官方示例同款）执行 | 3h | S1-7b + tape 消费 |
| J4b | **拓扑/异步对比（第三轮修订）**：T1 colocate 同步 vs T3 双缓冲 vs T2′ 双缓冲，各连跑 2~3 步，记每步墙钟分解、GPU util 曲线、**rollout 尾部空闲占比**。**预注册优先序：T3 先（直接复用 J4 的步数作 T3 数据点）→ T1 → T2′ 时间允许才做**；允许结论"T2′ 数据缺失，按 T3/T1 先定主案、T2′ 留首训期间对比" | 2.5h | 放置模式决策 |
| J4c | **fully_async 冒烟（30min）**：官方示例配置起 fully_async，**设计成强制触发 abort**（长生成 + `update_weights_interval=1` + `save_debug_rollout_data`），**判定口径写死**：对比 abort 前后同 trajectory 的 `Sample.tokens` 前缀是否保留、response 重生成的分叉点位置、`response_length / loss_mask / weight_versions` 三字段一致性——只跑通不触发 abort 只能得到"能启动"一个 bit | 0.5h | 升级档位可行性 |
| J5 | 权重同步与切换：跨分区 update_weights 的**耗时、节奏与字节量**（pause/flush/continue 三段停顿分解；`--update-weight-buffer-size` 512MB 默认对 MoE 两遍 pass 的敏感度扫 2 档）、colocate 的 offload/onload 显存曲线 | 1h | U-C 切换项 + 权重同步 |
| J5b | **异步正确性与质量测量（两线程调研增补）**：见下方专项清单 | 并入 J3/J4 | staleness/数值正确性 |
| J6 | 吞吐画像汇总与 E6 回填（分析，不占机时；机器可提前退租） | — | E6/C3 |
| J7 | 可选：若本机即训练机，按 DF-6 runbook 批量同步镜像（与 J3/J4 并行，吃网络不吃 GPU） | 后台 | 数据侧准备 |

### J3 矩阵（先粗后细，OOM 立即降档不恋战）

```text
固定：Qwen3-30B-A3B bf16、E2 生产 flags、--optimizer-cpu-offload、
     sequence-parallel 开、合成 batch = 64 条 × 目标长度
主轴 A 训练分区规模 × 并行组合（对应 §1.5 拓扑的训练侧，第三轮修订；
     **MoE 参数必须逐项显式**——参照锚：slime 自带 30B-A3B 测试用
     8 卡 colocate `TP4/CP2/EP8` + routing replay，
     reference/slime/tests/test_qwen3_30B_A3B.py:55）：
     A1 2 卡 · TP2×DP1 · EP2·ETP1     （T2′ 训练侧：必测——决定
                                       rollout-heavy 是否被训练步反噬）
     A2 4 卡 · TP2×DP2 · EP4·ETP1     （T3 训练侧）
     A3 6 卡 · TP2×DP3 · EP2·ETP1     （回退候选：仅当 A1/A2 step 过慢）
     A4 8 卡 · TP4×CP2 · EP8          （slime 官方测试同款，T1 对照）
     A5 任一 · CP=2                   （仅当 32k 显存不够时启用）
每个组合的启动配置必须完整写出（租卡前入脚本，P-4；
     完整清单见下方"J3 附：四组启动参数清单"）——
     失败时才分得清是硬件、拓扑还是参数写错。

### J3 附：四组启动参数清单（codex 二轮核查修正版，租卡前逐组入脚本）

```text
① checkpoint / model args：
   训练侧 torch_dist（P-3 转换产物）+ rollout 侧 HF 路径分别指定；
   所有训练脚本必须 source scripts/models/qwen3-30B-A3B.sh
   （--num-experts 128 / --moe-router-topk 8 / --moe-router-dtype fp32 /
   --moe-grouped-gemm / --moe-permute-fusion 等模型参数由它展开），
   并在 evidence 中 dump 展开后的 MODEL_ARGS。
② train parallel + MoE args（按 A1~A5 逐组合填）：
   TP/PP/EP/ETP/DP + --moe-token-dispatcher-type（alltoall 起步，
   DeepEP 视 J1 结果）+ --use-rollout-routing-replay（V4/M1 硬前提，必开）
   + 长上下文显存三件套（每拓扑必填）：--micro-batch-size 1 /
   --log-probs-chunk-size 1024（32k 下 logprob 重算的隐藏 OOM 点）/
   --max-tokens-per-gpu = CTX/CP。
③ rollout SGLang args（两种模式二选一，写明）：
   模式甲 TP-only 多引擎：--rollout-num-gpus-per-engine N（=TP）；
   模式乙 DP/EP：--sglang-dp-size / --sglang-ep-size /
   --sglang-enable-dp-attention / --sglang-enable-dp-lm-head /
   --sglang-moe-dense-tp-size 1，可选 DeepEP：
   --sglang-moe-a2a-backend deepep + --sglang-deepep-mode auto。
   （注意：不存在 "--enable-ep-moe" 这个参数——上一稿笔误，已订正）
④ async + weight sync + transport args：
   --update-weight-mode / --update-weight-transport（分离基线 =
   full + nccl；colocate = IPC tensor）/ --update-weights-interval 1 /
   --update-weight-buffer-size（512MB 起，J5 扫 2 档）/
   --rollout-data-transport（基线现值；NIXL 作为可选记录项，
   slime 30B R3 测试用 nixl）。
算法 flags（J4 用，写死不现场配）：E2 定案 = --advantage-estimator grpo
   + n=4 + --eps-clip 0.2 / --eps-clip-high 0.28 +
   --disable-grpo-std-normalization + 动态采样 filter；
   --use-tis 的开关决策挂 M2 实测（失配大则开）。
   旁注：slime 官方 30B-A3B R3 测试用 gspo + --use-tis +
   --eps-clip 4e-4——这是 T5 预案（GSPO 切换）的现成参照配置。
```
主轴 B 上下文：32k（目标档）→ 24k（降级档）
副轴 mbs：1 → 2（显存允许才试）
每格记录：step 墙钟 / 显存峰值（train 态）/ tokens/s /
     是否 OOM / 内核报错摘要
执行序：A1×32k×mbs1 起步；通过 → 扫 A2/A3 比速度；
     OOM → 先 mbs 后 CP 后 24k，记录降档路径
```

**"rollout 尾部空闲占比"的计算定义（升级档位触发条件的口径，不能现场发明）**：

```text
尾部空闲占比 = （rollout 阶段内，推理分区 GPU 平均利用率 < 30% 阈值的
              尾段时长）/ 当前 step 总墙钟
测量方式：nvidia-smi dmon 1s 采样（推理分区卡）+ 每条轨迹的
  完成时间戳（slime rollout_time 指标辅助）；"尾段"起点 =
  最后 25% 轨迹开始完成的时刻。
```

### J5b 专项清单（报告实践 + slime 源码两轮调研的增补测量，随 J3/J4/J4b 顺带采集）

```text
M1 staleness 直方图：Sample.weight_versions 的长度与版本跨度分布
   （一条 SWE 轨迹平均跨几个 policy version——升级档位 α 定档的实测依据）。
   **采集点显式声明（codex 核查）**：slime 的 _convert_samples_to_train_data
   （ray/rollout.py:735）不透传 weight_versions——必须在我们的
   projection 层（消费转换前的 Sample）采集，或开 save_debug_rollout_data；
   不得指望训练侧 train_data 里还有它。
M2 训推 logprob 失配：同批 token 的 rollout logprob vs trainer 重算
   logprob 的逐 token 差分布（MAI 一等监控项："小失配跨长轨迹复合
   会破坏 IS 校正"；这是 GRPO 正确性项）。
   工具落点：--get-mismatch-metrics 或 debug train data；采集脚本
   基于 examples/train_infer_mismatch_helper（mis.py）提前备好（P-8）。
M3 update 停顿吞吐塌陷：单次 update_weights 造成的 rollout 吞吐
   下陷深度与恢复时长（pause/flush 清 KV 后前缀重算的代价）
M4 abort 回收率与浪费：每次权重更新 abort 的在途组数、被丢弃重算的
   token 量（有效算力利用的直接扣减项）
M5 router 排队与 prefix cache 命中率：X-SMG-Routing-Key 一致性路由下
   GRPO 同组是否稳定命中同引擎（组内 8 兄弟共享前缀的 KV 收益实测）。
   **前提（codex 二轮核查）：同组同引擎不是自动成立**——slime 默认
   可能给每个 sample 不同 session id；custom_generate 必须显式把
   routing key 设为 group 级（同组同 key），否则 M5 数字不可解释。
M6 DP 序列打包失衡：各 DP rank 的 token 负载差（Composer 每步全局
   packing 的动因；失衡即空泡）
M7 生成引擎故障率：SGLang 引擎崩溃/超时次数与恢复行为
   （MAI 三层看门狗的动因；Nemotron 56% 故障来自生成引擎）
M8 优化器状态与权重推送的交互观察：若采用 per-step 推送，
   记录 loss/grad-norm 在推送前后的行为（GLM-5 每次推送后重置
   优化器的动因——slime 无此机制，观察是否需要）
```

### J4 判据（全要素 step 的六项断言）

```text
1. rollout（8 题 × n=4，top_p=0.95；n=2 仅作显式关 filter 后的降级档）经 S1 链路产出合格 Sample；
2. 启动期探针：renderer 类名断言（U-G）+ top-p tape 探针（U-H 同款）通过；
3. loss 路径消费 rollout_top_p_token_ids/offsets 与 rollout_routed_experts
   无 raise、loss 有限值；
4. 训练 step 完成且 grad norm 非 NaN；
5. 训练分区与推理分区**各自**显存水位留档、全程无 OOM（J4 在 T3 分离拓扑执行；colocate 的 offload/onload 水位归 J4b 的 T1 对照与 J5）；
6. checkpoint 用后即弃（8 题来自 Verified 仓库——A1/D5 条款，
   不得作为任何后续起点；acceptance 记录该声明）。
```

## 3. 通过判据与降级阶梯

```text
绿灯（S4 可按 E6 现行预算排期）：
  J3 最优配置的训练 step（64 轨迹 × ~20k token、32k 上下文）≤ 15min
  且 J4 六项全过，**且 J4b 产出明确的放置模式决策**——
  预期主案 = 分离（T2′ 或 T3，按 J4b 的每步墙钟与尾部空闲占比定）
  + train_async 双缓冲 + staleness 记账（§1.6 定案；双缓冲的
  结构性 staleness 上界即行业最紧实践 α≈1，无需自建准入）。
  colocate 仅当 J4b 显示跨分区 update_weights 开销吃掉全部重叠收益
  时才回退（注意 colocate 在 slime 里无双缓冲，纯同步）。
  升级档位（fully_async + 自建三件）触发条件预注册：
  rollout 尾部空闲 > 每步墙钟 25%（J4b 与首训双处测量）；
  本轮 J4c 只验证可启动性与 aborted 组 token 复用真实语义。
黄灯（可开训但重排预算）：step ∈ 15~30min → E6 步数上限按 C3 反推收紧，
  或采纳 24k 上下文档；沙箱并发杠杆（16→32）优先于降步数。
红灯（触发放弃线，停下与用户重议）：
  所有配置在 24k/mbs1 仍 OOM，或最优 step > 45min，或 Megatron
  在 sm_120 有不可绕过的内核缺陷。
  重议选项：(a) E1 降档（无先验背书，最后选择）；
  (b) S4 训练改租云端 NVLink 机（8×A100/H100 短租），本机专职
      数据/评分/单卡推理——**代价旁注：本协议除 J1/J2 外的实测数据
      基本作废，S4 放置决策全部重做，(b) 不是轻量退路**；
  (c) 每步轨迹数 64→32，拉长步数换显存/时间。
```

## 4. 执行纪律

- 每作业独立日志 + 配置 dump；失败不修不猜，记录后按矩阵继续（排障留给分析阶段，机时只用来采数）。
- J1~J3 用合成数据，J4 才碰真实链路——链路问题与硬件问题不混查（F2 原则的预实验内延续）。
- 所有脚本与判据版本进 evidence 目录：`preflight/`（本目录），报告 `preflight_report.md`，implementation-notes 三节制随执行建立。

## 5. 记录模板（preflight_report.md 骨架）

```text
机器：卡型×8 / 驱动 / CUDA / PCIe 拓扑（topo -m 原文）
J1：2/4/8 卡 all-to-all 带宽表（GB/s，msg size 两档）
J3：矩阵表（配置 × 上下文 × mbs → step 时间 / 显存峰 / tokens/s / 备注）
J4：六项断言逐条 + rollout 态/train 态显存水位 + 单步端到端墙钟分解
J5：update_weights 耗时 / sleep-resume 前后显存
结论：绿/黄/红灯判定 + E6 回填数字 + C3 反推结果
     （30 步/50 步全程墙钟预测，含 rollout 段）
```

## 6. 姊妹单卡作业：pass-rate 预筛 + pre-RL 行为诊断（A3 归属落地）

**时机（2026-07-08 修订）**：**S2 末 / S3 初——环境验证门完成之后**，不与 8 卡作业同期提前。理由（用户评审提出，采纳）：
1. pass-rate 有效性依赖环境门先行——golden patch 跑不通的坏环境 pass-rate 恒 0，分不清"题难"还是"环境坏"；flaky 环境的 pass-rate 是噪声。漏斗顺序以 DF-7 为准：静态门 → 环境验证门 → GPU pass-rate 筛。
2. 无关键路径收益——预筛的消费者（bring-up 题单）本来就等 S2 ingestion。
3. 30B 早期行为信号由本协议 J4 覆盖（8 题 × n4 全要素即迷你行为冒烟），不需为此提前烧完整诊断。

```text
输入：static_gate_survivors 216 题中**通过 S2 环境验证门**的存活集
配置：训练路径 eval 模式（同 harness 同栈）；T=1.0、top_p=0.95
预算分层（控制单卡墙钟 ≈ 1 天，按环境门存活数等比缩放；
  估算式：约 204 存活题 × n4 + 60 题 × n4 ≈ 1056 条轨迹 ×
  ~600s ÷ 并发 16 ≈ 11h）：
  存活全量 × n=4  → pass-rate 粗估，过滤 [0.1,0.8]
  诊断子集 60 题（分层抽）追加 × n=4 → 合计 n=8 的细估 + 诊断指标
产出：
  per-task pass-rate JSON（bring-up 题单的最终输入）
  诊断指标（E3 第 0 段硬门）：valid tool-call rate / submit rate /
    empty-patch rate / timeout rate / solve-none rate / 零方差组占比 /
    平均 turn 与 token——对照 E3 触发条件预演
判据：诊断指标若显示行为崩坏（valid action / submit 大面积失败），
  按 E3 定案先修行为锚，不进 RL。
后续批次（不在本作业）：held-out 候选与 R2E success-run 池的预筛，
  等题单范围确定后按同规格分批（同样以各自环境验证门为前置）。
```

## 7. 结果回填清单（执行后逐项勾）

```text
[ ] 实验设计文档 E6：墙钟表"训练 step（纸面）"→ 实测值；C3 反推更新
[ ] 实验设计文档 §4.1 第 4 条：训练侧"完全未验证"状态翻转
[ ] final_review V 清单：U-C 关闭记录
[ ] S1/S4 执行文档：7b 判据引用本报告（由执行线程操作，本线程只交报告）
[ ] E1 定案栏：35B-A3B 升级选项重议（仅当 J3 显存/速度富余显著时）
```

## 8. 交接给 S1 执行线的契约事项（下个检查点提出，防遗忘）

```text
H-1 staleness 记账（S1-3 / S1-5 契约追加，成本极低）：
    project_from_slime 必须把 Sample.weight_versions（slime
    types.py:120，list——一条轨迹可跨多版本）透传进
    TrajectoryProjection 的 handshake 字段；gate（S1-5）记录
    staleness 分布（版本跨度 max-min 与列表长度），只记录不准入。
    关键依据（codex 核查）：slime 的 _convert_samples_to_train_data
    （ray/rollout.py:735）不透传该字段——采集必须发生在 projection
    层（转换前的 Sample），这恰是 S1-3 的输入位置，顺路带走即可。
    版本聚合口径：handshake 同时存原始 list 与派生 max_lag，
    派生口径的选择权留给升级档位的准入设计。
H-2 训练拓扑输入变更：S1-6/S1-7a 的 slime 启动配置按本协议 §1.5/§1.6
    准备为"分离放置 + train_async"（7a 单/双卡不受影响，但配置模板
    应与 S4 目标形态同构，避免 7a 验过的配置到 S4 换形态重验）。
H-3 J4 复用 S1 产物的接口确认：J4 需要 S1-6 编排胶水在分离拓扑下
    可运行——若 S1-6 只在 colocate mock 下测过，需在 S1-9 验收前
    补一个分离配置的 mock 冒烟。
```
