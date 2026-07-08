# P3 八卡远程预实验交接记录

更新时间：2026-07-09。本文记录本轮在 `ubuntu@204.12.168.119` 机器上执行 P3 八卡预实验期间的环境、尝试、代码改动、关键结论、证据产物和后续建议。本文面向后续接手的执行 agent 或复核 agent，避免重新从远端日志里拼接事实。

## 1. 当前状态

- 远端机器：`ubuntu@204.12.168.119`。
- 外挂卷：`/mnt/p3`，容量约 1.5TB。模型、运行目录、证据目录均应落在该盘或其容器内 bind mount 上。
- 容器：`rh2-p3`，基于 `slimerl/slime` 镜像运行。
- 当前仍在运行的作业：无。最后一个作业 `j5_reduced_gbs20_20260708T171722Z` 已成功退出。
- 当前远端状态：八张 GPU 显存均为 `0 MiB`，根盘和外挂卷仍有余量；容器和证据目录仍保留，方便后续继续执行 J4b 或补拉证据。
- 清理注意：远端 `ps` 仍能看到 Ray 强停后留下的 `defunct` 僵尸进程条目。这些条目不占 GPU 显存，也不代表训练仍在运行；如果继续复用该容器跑新任务，建议先重启容器或做一次完整 Ray 清理。
- 当前已验证的问题：把 `J5_GLOBAL_BATCH_SIZE` 从 16 调到 20 后，能够越过上一轮的 slime `build_dp_schedule` 动态批调度断言，并完成一个真实训练 step 与权重更新耗时记录。
- 重要限定：`global_batch_size=20` 是诊断性重跑参数，不是正式系统方案。正式系统必须在 adapter 或 preflight inspector 中提前判断 batch schedule 是否可行，不能靠人工调参碰运气。

## 2. 本地和远端证据位置

远端核心路径：

- `/mnt/p3/preflight_evidence/`：P3 小型证据目录，包含 driver log、训练日志、CSV、JSON、配置 dump。
- `/mnt/p3/bringup/`：P3 运行目录，包含 rollout dump、事件、评测日志、临时工作区。这个目录体积较大，不应完整下载。
- `/mnt/p3/current_j4_run_id.txt`：当前或最近一次 J4 run id。
- `/mnt/p3/current_j5_run_id.txt`：当前或最近一次 J5 run id。

本地已开始同步的证据目录：

- `docs/agentic_RL/repo_harness_rh2_workstreams/preflight/remote_evidence_20260708/preflight_evidence/`
- `docs/agentic_RL/repo_harness_rh2_workstreams/preflight/remote_evidence_20260708/bringup_selected/`

同步策略：

- 同步 `/mnt/p3/preflight_evidence/` 中的可读证据。
- 已排除 `.pt`、`.bin`、`.distcp`、`.safetensors`、`tapes/`、`rollout_dumps/`、`ckpt/` 等训练二进制或大文件。
- 本地校验结果：约 18MB，492 个文件，没有上述大二进制扩展名。
- 不完整同步 `/mnt/p3/bringup/`，因为其中包含多 GB 的 rollout dump、工作区和评测容器产物。
- 已选择性同步 `/mnt/p3/bringup/` 下的关键小文件到 `bringup_selected/`：`bringup_events.jsonl`、`startup_evidence.json`，以及 formal J4 的 `trajectory_projection.json`、`eligibility_report.json`、`grading_report.json`。这批文件约 600KB，共 63 个文件，没有训练二进制。

## 3. 本轮脚本和代码改动

这些改动还没有提交，需要后续复核后决定是否整理成正式 commit。

### 3.1 存储路径防线

修改文件：

- `rh2/experiments/p3_preflight/common.sh`
- `rh2/experiments/p3_preflight/j3_matrix/run_j3.sh`
- `rh2/experiments/p3_preflight/j4_full_step.sh`
- `rh2/experiments/p3_preflight/j4b_topo_compare.sh`
- `rh2/experiments/p3_preflight/j4c_fully_async_smoke.sh`
- `rh2/experiments/p3_preflight/j5_weight_sync.sh`

目的：

- 防止 Ray session、rollout dump、debug checkpoint 等大文件写入根盘或 Docker overlay。
- 新增 `P3_RUN_ROOT`、`P3_RAY_TMP` 和 `p3_require_large_storage_path`。
- 在检测到 `/mnt/p3` 或 `/root/bringup` 等大盘挂载后，关键路径必须落在这些路径下。
- `j3_matrix/run_j3.sh` 额外补了两处稳定性修正：非 dry-run 时确保 evidence 根目录存在；kernel 错误 grep 没有匹配时不再因为 `set -e` 中断汇总。

经验：

- 30B optimizer checkpoint 单次保存约 380GB，保存耗时约 373 秒。P3 以后若只是验证链路，应默认不保留 checkpoint，除非作业目标就是 checkpoint 测试。

### 3.2 J4 动态采样和 mismatch metrics 默认关闭

修改文件：

- `rh2/experiments/p3_preflight/j4_full_step.sh`

原因：

- slime stock `dynamic_sampling_filter` 在 RepoHarness fan-out 返回 `list[Sample]` 时失败，错误为 `AttributeError: 'list' object has no attribute 'get_reward_value'`。
- 当前 slime pin 的 `--get-mismatch-metrics` 需要同时提供 `--custom-tis-function-path`，否则会在参数层或运行层不成立。

处理：

- `J4_DYNAMIC_FILTER` 默认改为 `0`。
- `J4_MISMATCH_METRICS` 默认改为 `0`。
- 如果开启 mismatch metrics，脚本要求显式提供 `J4_CUSTOM_TIS_FUNCTION_PATH`。

正式系统建议：

- 动态采样过滤不能直接复用 slime stock filter，需要做 fan-out aware 版本，或者在 RepoHarness adapter 层先聚合 sibling branches。

### 3.3 MoE routing tape 捕获与形状修复

修改文件：

- `rh2/src/repoharness2/adapters/slime/generate.py`
- `rh2/experiments/s1_7a_bringup/glue.py`
- `rh2/tests/adapters/test_slime_generate.py`

目的：

- 30B MoE 必须请求 SGLang 返回 routed experts，否则 `--use-rollout-routing-replay` 不可能训练。
- 增加 `RH2_EXPECT_MOE_ROUTING`、`RH2_MOE_NUM_LAYERS`、`RH2_MOE_ROUTER_TOPK` 等环境控制。
- 对 routing tensor 行数进行更严格的补齐、回填和 fail-closed 检查。

经验：

- J3 合成 routing tape 曾触发 MoE `Split sizes doesn't match total dim 0 size`，后续证明 no-routing 控制格可以训练，因此 J3 早期失败不能解释为 30B 训练拓扑不可行。
- 真实 SGLang routing tape 仍会遇到“routing rows 少于 token rows”的样本级失败，当前处理是 fail-closed 标记为不可训练，不能伪造 routing。

### 3.4 细粒度 rollout 计时

修改文件：

- `rh2/src/repoharness2/adapters/slime/generate.py`
- `rh2/experiments/s1_7a_bringup/glue.py`

新增字段：

- `audit_timeline`
- `rollout_timings.materialize_seconds`
- `rollout_timings.harness_run_seconds`
- `rollout_timings.capture_finish_backfill_seconds`
- `rollout_timings.grading_seconds`
- `rollout_timings.projection_seconds`
- `rollout_timings.eligibility_gate_seconds`
- `rollout_timings.delivery_seconds`
- `rollout_timings.cleanup_seconds`
- `rollout_timings.total_audit_seconds`

关键发现：

- 本轮真实黑盒 rollout 的瓶颈明确在 `harness_run_seconds`。
- 已完成样本中常见耗时：
  - 物化：约 4 到 10 秒。
  - 黑盒 harness 运行：约 300 到 1100 秒。
  - 评分：约 4 到 27 秒。
  - 投影和 gate：通常秒级或毫秒级。

结论：

- 长尾问题主要来自黑盒 harness 与模型交互，不来自评分、投影或 eligibility gate。
- 后续是否引入 fully async、partial rollout、长尾 abort 或补采策略，应基于这个分段计时判断。

### 3.5 P3 自定义转换器和离线转换检查

新增文件：

- `rh2/experiments/p3_preflight/rh2_convert.py`
- `rh2/experiments/p3_preflight/lib/j4_converter_offline.py`
- `rh2/experiments/p3_preflight/j4_train_replay.sh`

目的：

- 在 slime 物化训练 tensor 前剔除 `remove_sample=True` 的样本。
- 确保被治理层或投影层 fail-closed 的样本不会影响 routing/top-p 字段存在性判断。
- 用已有 `rollout_*.pt` 进行离线转换检查，不必每次重新跑完整黑盒 rollout。
- 用已有 J4 rollout dump 做 train-only replay，验证训练消费链路。

关键结果：

- formal J4 的离线转换检查通过，44 个 raw samples 中有 31 个 trainable samples，top-p replay 和 routing replay 字段存在且形状可消费。
- J4 train replay 在 `global_batch_size=16` 下成功完成训练 step，证明同一批 top-p/routing tape 可被训练侧消费。

### 3.6 J5 权重同步脚本的小改动

修改文件：

- `rh2/experiments/p3_preflight/j5_weight_sync.sh`

改动：

- 增加 `J5_GLOBAL_BATCH_SIZE` 可配置项。
- 增加 `--custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data`。
- 路径统一走 `P3_RUN_ROOT` 与 `P3_EV`。

经验：

- 如果不加自定义转换器，治理剔除样本可能污染 slime 的 optional field 判断或 batch 组装。
- 但自定义转换器剔除样本后，又会改变每个 step 的实际 sample 数，必须进一步做 batch schedule preflight。

## 4. 已执行作业与结果

### 4.1 J0 / J0.5 / J1 / J2

状态：已有 evidence。

作用：

- J0：环境、镜像、权重、GPU、拓扑留档。
- J0.5：单卡或小规模 kernel smoke。
- J1：NCCL 通信基准。
- J2：SGLang 30B 推理服务探针。

结论摘要：

- 远端机器、镜像、模型和基本通信路径可用。
- SGLang 可以加载 30B MoE 推理分区。
- 这些作业主要是硬件和基础环境检查，不构成训练闭环结论。

### 4.2 J3 训练侧矩阵

重要结果：

- A1，2 卡 TP2/DP1/EP2：OOM，发生在 Megatron DDP 初始化或 buffer 初始化附近，不是 rollout 链路问题。
- A2，4 卡 TP2/DP2/EP4：未 OOM，但使用合成 routing tape 时触发 MoE all-to-all split mismatch。
- A3，6 卡 TP2/DP3/EP2：配置无效，`global batch size` 不能被数据并行相关约束整除，应归为 invalid config。
- A4，8 卡 TP4/CP2/EP8：未 OOM，但合成 routing tape 同样触发 MoE all-to-all split mismatch。
- no-routing 控制实验：A4 形态不带 routing replay 可以成功完成训练 step，说明 30B Megatron 训练本体和八卡硬件链路成立。

关键经验：

- J3 的合成 routing tape 不应作为真实 routing replay 成败的最终证据。
- `kernel_err` 统计口径曾把正常日志里的 `cutlass` 字样当成错误，需要修正。
- 后续 synthetic routing 如果继续使用，必须生成更接近真实 router 的无重复 top-k routing tape，或者把 routing replay 从纯硬件矩阵里拆出去。

### 4.3 J4 早期失败尝试

这些尝试暴露了真实系统问题，不能简单视为无效噪声。

1. dynamic filter 与 fan-out 不兼容：
   - 错误：`AttributeError: 'list' object has no attribute 'get_reward_value'`。
   - 根因：RepoHarness custom generate 会返回 fan-out nested samples，而 slime stock dynamic filter 在 flatten 前假设输入是平铺 `Sample`。
   - 处理：J4 默认关闭 stock dynamic filter。

2. 任务镜像缺失：
   - 错误：`rollout_image_inspect_failed`，8 个 SWE 镜像没有预拉。
   - 处理：预拉 8 个 smoke 镜像，并在容器内用 docker CLI 确认可见。
   - 经验：J4 前必须有 image inspect fail-fast gate，不能启动 30B 后才发现镜像缺失。

3. converter signature / postprocess / routing shape 等边界错误：
   - 处理：引入 `rh2_convert.py`、修复 routing shape、修复 converter 对 slime 内部方法绑定的兼容问题。
   - 经验：这些都应通过离线 converter 检查提前暴露，不应该靠完整 rollout 后才发现。

### 4.4 formal J4：严格 8 题 × 4 样本

Run id：`j4_formal_20260708T160749Z`

配置：

- 拓扑：T3，4 张训练卡 + 4 张推理卡。
- 模型：Qwen3-30B-A3B。
- `top_p=0.95`。
- `--use-rollout-routing-replay` 开启。
- custom generate 使用 RepoHarness S1 glue。
- 自定义转换器开启。

结果：

- 32 个 rollout 事件完成。
- raw returned samples 总数为 44。
- trainable samples 为 31。
- 最长 rollout wall time 约 1093 秒。
- formal J4 在线训练没有启动，失败在 slime 组 batch 之前：
  - 错误：`num_rollouts (19) < global_batch_size (32); need at least one rollout per step.`

解释：

- 不是模型加载失败。
- 不是显存 OOM。
- 不是 top-p tape 全局缺失。
- 不是 routing tape 全局缺失。
- 根因是治理过滤和 fan-out 后，有效 rollout id 数不足以满足 `global_batch_size=32` 的训练 step。

重要产物：

- `j4_converter_offline.json`：离线转换通过。
- `j4_assertions.json`：训练指标和 checkpoint 相关项未通过，因为训练未启动。
- `bringup_events.jsonl`：32 条真实 rollout 事件，包含分段耗时。

### 4.5 J4 train-only replay

Run id：`j4_formal_20260708T160749Z_replay_gbs16_20260708T163514Z`

目的：

- 不重新跑黑盒 rollout，直接用 formal J4 的 `rollout_0.pt` 做训练侧 replay。
- 验证同一批 top-p/routing tape 是否能被 Megatron/slime 消费。

结果：

- Ray job 成功退出。
- `global_batch_size=16`。
- `loss_marker_count=25`。
- `grad_norm_marker_count=2`。
- checkpoint 用后删除。

关键训练指标：

- `train/loss = -0.14717744290828705`
- `train/pg_loss = -0.14717744290828705`
- `train/entropy_loss = 0.8056093454360962`
- `train/train_rollout_logprob_abs_diff = 0.03605957701802254`
- `train/kl_loss = 0.05735120177268982`
- `train/grad_norm = 0.9308214724976641`

解释：

- 训练消费链路成立。
- top-p replay 与 routing replay 至少可以被训练侧真实消费一次。
- formal J4 的失败不是 trainer 消费能力失败，而是在线 rollout 到 batch admission 的数量和调度问题。

### 4.6 J4c fully_async 冒烟

状态：未执行实际冒烟。

原因：

- 远端缺少 J4c 默认需要的 4B dense 模型资产：
  - `/root/models/Qwen3-4B`
  - `/root/models/Qwen3-4B_torch_dist`

决定：

- 没有用 30B MoE 冒充 J4c。

解释：

- J4c 设计目的是验证 fully async 机制和 custom_generate 对 aborted group 的行为。
- 直接用 30B 会改变模型、并行和资源前提，容易把机制问题和 30B 资源问题混在一起。

### 4.7 J5 reduced，`global_batch_size=16`

Run id：`j5_reduced_20260708T165218Z`

配置：

- T3 拓扑：4 张训练卡 + 4 张推理卡。
- `J5_BUFFER_SIZES=536870912`。
- `J5_STEPS=1`。
- `J5_GLOBAL_BATCH_SIZE=16`。
- custom converter 开启。

结果：

- 32 个 rollout 事件完成。
- raw returned samples 总数为 48。
- kept samples 为 41。
- removed samples 为 7。
- 权重同步进度已经触发，日志出现 `Update weights` tqdm，512MB buffer 下一次全量发送窗口约 9 秒级。
- 作业最终失败。

失败点：

```text
AssertionError: dynamic path: could only produce 23 mbs after maximal splitting;
need 24. step 0 has 23 samples, below the alignment threshold (2).
```

根因：

- slime 的 `build_dp_schedule` 不是只看样本总数。
- 它先按 `rollout_id` 切训练 step，每个 step 再按 token 长度打 microbatch。
- microbatch 数必须对齐到 `dp_size * mb_group` 的倍数。
- 当前 T3 训练并行下 `dp_size=2`，因此第一步 23 个 microbatch 无法对齐到 24。

重要解释：

- 这不是权重同步完全失败。
- 它已经触发了权重发送进度。
- 它失败在训练数据调度和动态批对齐，不是 SGLang、NCCL 或 checkpoint 本体。

### 4.8 J5 reduced，`global_batch_size=20`

Run id：`j5_reduced_gbs20_20260708T171722Z`

目的：

- 诊断性重跑，只改变一个变量：`global_batch_size=20`。
- 验证上一轮失败是否确实来自 batch schedule alignment，而不是权重同步本身。

最终状态：

- Ray job 成功退出，脚本返回码为 0。
- 完成 32 个 rollout 事件。
- 已返回 40 个 raw samples。
- kept samples 为 36，removed samples 为 4。
- `global_batch_size=20` 的模拟检查显示第一步 20 个 rollout 对应 26 个保留 samples，满足 `dp_size=2` 的偶数对齐。
- 该轮越过了上一轮 `build_dp_schedule` 断言，完成了一个真实训练 step。
- 作业结束后远端八张 GPU 显存均为 `0 MiB`。

关键训练指标：

- `train/loss = -0.10555558204650879`
- `train/pg_loss = -0.10555558204650879`
- `train/entropy_loss = 1.1074869155883789`
- `train/pg_clipfrac = 0.0`
- `train/ppo_kl = 0.0`
- `train/train_rollout_logprob_abs_diff = 0.0390933096408844`
- `train/kl_loss = 0.05932055115699768`
- `train/grad_norm = 0.8455006486990598`
- `train/global_batch_size = 20`
- `train/step = 0`

关键性能指标：

- `perf/update_weights_time = 11.44766879081726` 秒。
- `perf/data_preprocess_time = 0.3015470504760742` 秒。
- `perf/train_wait_time = 1135.1945157051086` 秒。
- `perf/ref_log_probs_time = 41.02006483078003` 秒。
- `perf/log_probs_time = 35.28698754310608` 秒。
- `perf/actor_train_time = 174.23037600517273` 秒。
- `perf/train_time = 251.7536175251007` 秒。
- `perf/actor_train_tok_per_s = 4527.781079784727`。
- `perf/step_time = 1386.9481332302094` 秒。
- `perf/wait_time_ratio = 0.8184837547322226`。

权重同步记录：

```text
buffer_size_bytes,steps,update_weights_time_s_list,pause_flush_s,send_s,continue_s,three_phase_resolved,rc
536870912,1,11.4,-,-,-,no,0
```

解释：

- 512MB buffer 下，30B 权重全量更新路径可以完成，单次 `update_weights_time` 约 11.45 秒。
- slime 当前日志没有暴露 pause / flush / send / continue 的精确三段耗时，因此 `three_phase_resolved=false` 是诚实状态，不是失败。
- 这轮证明 `gbs16` 的失败根因确实是动态批调度对齐，而不是权重同步、NCCL、SGLang 或训练本体。

最新分段计时观察：

- `harness_run_seconds` 最小约 280 秒，中位数约 614 秒，最大约 1080 秒；完整 32 条里最大 wall time 约 1116 秒。
- `grading_seconds` 最小约 4 秒，中位数约 13 秒，最大约 27 秒。
- 该轮再次确认主要墙钟花在黑盒 harness，评分与投影不是主瓶颈。

限定：

- 即使本轮通过，也不能把 `global_batch_size=20` 作为正式系统修复。
- 它只证明一个窄问题：调度对齐改变后是否能越过上一轮断言并触发训练/权重同步。
- 这不是正式 P3 严格验收绿灯，因为正式系统不能依赖人工选择一个碰巧可对齐的 `global_batch_size`。

## 5. 关键系统结论

### 5.1 当前链路的大方向成立

已经被验证的部分：

- 8 卡机器可以加载 30B MoE 训练分区和推理分区。
- T3 分离拓扑可以启动 SGLang engine。
- 训练侧可以消费已有 top-p/routing replay 数据。
- train-only replay 可以产生有限 loss 和有限 grad norm。
- 权重同步路径可以在 512MB buffer 下完成一次真实更新，`update_weights_time` 约 11.45 秒。

尚未完全闭环的部分：

- 端到端 online J4 严格模式尚未绿灯。
- J5 512MB 单档权重同步诊断已绿灯；2GiB 第二档和更精细的 pause / send / continue 三段分解尚未完成。
- J4b 拓扑对比尚未完成。
- J4c fully_async 冒烟尚未完成。

### 5.2 当前主要风险不是显存，而是治理过滤后的 batch admission

formal J4 和 J5 gbs16 都说明：

- 黑盒 harness 的 fan-out、projection fail-closed、routing tape fail-closed、eligibility 降档和 `remove_sample` 会改变实际训练样本分布。
- 名义上的 `8 题 × n=4 = 32 rollout` 不等于 trainer 看到的可训练 rollout id 数。
- 名义上的 raw samples 总数也不等于 slime 每个 training step 能调度的 microbatch 数。

正式系统要求：

- adapter 或 inspector 必须在训练消费前计算：
  - 当前保留样本数；
  - `rollout_id` 分布；
  - 每个 rollout 展开的 branch 数；
  - 每个 sample 的 token 长度；
  - `dp_size`；
  - `cp_size`；
  - `vpp_size`；
  - `microbatch_group_size_per_vp_stage`；
  - `micro_batch_size`；
  - dynamic batch alignment。
- 如果不满足，应 fail-closed、延迟拼 batch、补采样、重排 sample selection，或者执行 batch schedule repair。
- 不应等 20 分钟 rollout 后让 slime 在 `build_dp_schedule` 内部断言失败。

### 5.3 黑盒 harness 长尾是当前最大吞吐问题

根据分段计时：

- 环境物化和评分不是主耗时。
- 黑盒 harness 与模型交互占据绝大多数时间。
- rollout 长尾已经达到 1000 秒以上。

后续建议：

- 首训先用分离放置 + train_async 双缓冲是合理的。
- 如果 rollout 尾部空闲超过 step 墙钟的 25%，需要启动 fully_async 升级设计。
- 但 fully_async 升级前必须解决：
  - aborted group 的 custom_generate 行为；
  - staleness mask 或准入；
  - dynamic filter 在 fully_async 下静默失效；
  - output queue 阻塞和 worker 异常泄漏监控。

### 5.4 routing tape 不能伪造，也不能盲目吞掉失败

当前做法是正确的：

- routing 行数不足、routing 字段缺失或形状不一致时，样本 fail-closed。
- 不能为了凑 batch 伪造 routing tape。

但后续需要改进：

- 对 fail-closed 的原因做结构化统计。
- 把 routing rows mismatch、top-p tape 缺失、capture 未完成、projection 失败、eligibility 失败分别计数。
- 在 batch admission 之前，先知道到底有多少样本会被剔除。

### 5.5 P3 必须保留离线 replay 阶梯

本轮 J4 replay 的价值很高：

- 它避免了再次跑完整黑盒 rollout。
- 它把“rollout 生成问题”和“训练消费问题”拆开。

后续建议固定为标准调试阶梯：

1. J4-preflight-fast：少题少样本，只验证物化、harness、capture、projection。
2. J4-converter-offline：直接用 `rollout_*.pt` 检查转换器。
3. J4-train-replay：已有 rollout dump 上验证 loss、grad norm、top-p/routing 消费。
4. J4-strict：最后才跑完整 8 题 × 4 样本端到端。

## 6. 还没有完成的内容

- J4b 拓扑对比尚未执行。建议优先补一个 reduced `T1 colocate` 对照，不必强行跑完整 `T2′`。
- J4c fully_async 冒烟尚未执行，因为缺少 4B 模型资产。可以选择下载 4B 后补测，也可以把 fully_async 放到下一轮专项。
- 没有完成 `update_weight_buffer_size` 两档扫描。本轮只测了 512MB。2GiB 档可选，优先级低于 batch admission 修复。
- 没有把 `/mnt/p3/bringup` 下的关键小文件完整选择性下载回本地。当前只同步了 `/mnt/p3/preflight_evidence`，没有完整同步 rollout 工作区。
- formal J4 严格模式仍然没有绿灯，因为 `global_batch_size=32` 下有效 rollout id 数不足。
- batch schedule preflight / repair 仍未实现。当前只是通过 J5 `gbs20` 诊断性证明了根因。

## 7. 后续建议

### 7.1 立即建议

1. 将 `J5 gbs20` 记录为“诊断性对照通过”，不要写成正式方案。
2. 停止继续猜 `global_batch_size`，转入 adapter schedule checker 或 batch repair 实现。
3. 如果还要继续使用当前机器，下一步优先跑 J4b reduced `T1 colocate` 对照；如果不继续，释放前确认 GPU、Ray、SGLang 均已清理。
4. 下载或保留关键证据路径，避免释放机器后丢失。
5. formal J4 重新跑之前，先做离线 schedule preflight，避免再次用 20 分钟 rollout 暴露 Python 层可提前发现的问题。

### 7.2 adapter / inspector 必须补的能力

新增一个 batch schedule preflight，输入为治理过滤后的样本，输出为可训练性报告：

- raw sample count；
- kept sample count；
- removed sample count；
- unique rollout ids；
- 每个 rollout id 的 branch 数；
- 每个 sample 的 token 长度；
- 每个 step 的 sample 数；
- 每个 step 的 microbatch 数；
- `align_to = dp_size * (mb_group if vpp_size > 1 else 1)`；
- 是否会触发 slime `build_dp_schedule` 断言；
- 如果失败，给出明确 `backend_rejection_reason`。

处理策略：

- fail-closed：拒绝当前 batch，记录原因。
- delayed batching：继续收集更多 rollout，直到能组成合法 step。
- sample selection repair：选择能对齐的 rollout id 子集进入训练。
- oversampling：从同一任务池补采更多 rollout。
- 明确不推荐：手动猜 `global_batch_size`。

### 7.3 J4/J5 脚本层建议

- 在 J4/J5 脚本里增加 `--preflight-schedule-only` 或等价检查。
- 在 `rh2_convert.py` 里转换前后都输出 schedule summary。
- `j4_assert.py` 增加 batch admission 专项断言，区分：
  - raw rollout 成功；
  - converter 成功；
  - batch schedule 可行；
  - train step 成功；
  - checkpoint 策略成功。

### 7.4 文档层建议

- 在 `8gpu_preflight_protocol.md` 中补充“治理过滤后的 batch schedule alignment 是独立验收项”。
- 在 `slime_fully_async_upgrade_design.md` 中补充：fully async 不能解决 batch schedule 不合法的问题，它只解决 rollout/trainer overlap 和长尾空闲。
- 在后续 S2 或 P3 收口文档中明确：`global_batch_size`、`rollout_batch_size`、`n_samples_per_prompt` 是训练配置，不是治理过滤后的合法性修复机制。

## 8. 远端机器释放前检查清单

- 确认当前 Ray job 已结束。
- 确认 `nvidia-smi` 八张卡显存为 0MiB。最新检查已经满足该项。
- 确认没有 `sglang`、`raylet`、`train_async.py` 常驻进程。
- 确认没有保留 30B checkpoint。
- 确认 `/mnt/p3/preflight_evidence` 已同步到本地。最新同步路径为 `docs/agentic_RL/repo_harness_rh2_workstreams/preflight/remote_evidence_20260708/preflight_evidence/`。
- 如需要，选择性同步 `/mnt/p3/bringup/<run_id>/artifacts/bringup_events.jsonl` 和关键 JSON。
- 记录最终 run id、exit code、driver log、train log、CSV、JSON。
