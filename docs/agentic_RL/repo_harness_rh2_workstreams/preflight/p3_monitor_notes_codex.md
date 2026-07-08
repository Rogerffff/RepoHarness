# P3 预实验监控备忘（Codex）

更新时间：2026-07-08

用途：记录在隔壁线程执行 8GPU P3 预实验期间，Codex 只读巡检远程机器、slime/Megatron 配置和 evidence 产物后发现的风险、遗漏与建议补测项。本文只作为执行提示，不替代 `8gpu_preflight_protocol.md` 的验收口径。

## 当前远程状态快照

- 机器：`ubuntu@204.12.168.119`，需要 `~/.ssh/vastai_ed25519`。
- Volume：`/mnt/p3`，1.5T，模型与 evidence 都在该盘；截至首次巡检已用约 828G。
- 镜像：`slimerl/slime@sha256:a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75`，J0 记录为 pin 匹配。
- J0/J0.5/J1/J2：已有 evidence。J0.5 单卡 dense train step 成功；J1 三类 NCCL 基准有表；J2 双 TP2 SGLang engine 32k 探针通过。
- 注意：远程 `/home/ubuntu/claude-code-verl-stage0h` 不是完整 git checkout，只是目录拷贝。收尾报告应补本地 commit、脚本 checksum、远程目录 checksum 或 tarball digest，避免事后无法复原代码版本。

## 已观察到的 J3 结果

### A1：2 卡 TP2/DP1/EP2 基线

- 结果：32k 与 24k 都 OOM。
- 关键证据：OOM 发生在 Megatron DDP 初始化 `_ParamAndGradBuffer`，不是长上下文激活阶段。
- 日志确认当前 A1 已经覆盖常规省显存项：
  - `use_distributed_optimizer=True`（slime 默认强制打开）
  - `--optimizer-cpu-offload`
  - `--overlap-cpu-optimizer-d2h-h2d`
  - `--use-precision-aware-optimizer`
  - `--micro-batch-size 1`
  - `--recompute-granularity full`
  - `--sequence-parallel`
- 因此不能说“忽略了常规显存优化”。更准确结论是：当前 A1 基线双卡拓扑不成立。

建议补测：

1. `A1-offload-train`：同 A1 但加 `--offload-train`。这会触发 slime 的 `disable_grad_buffers_cpu_backup=True` 和 `disable_param_buffers_cpu_backup=True` 路径。未必能救，因为爆的是 GPU grad buffer 本身，但成本低，适合作为双卡救援补测。
2. `A1-PP2`：尝试 `2 卡 · TP1 × PP2 × DP1 · EP2`。这是换模型切分形态，不应作为主路线，但可验证 pipeline split 是否能降低每 rank 初始化显存。

若这两个补测均失败，后续不应继续把 T2′（2 训 + 6 推）作为主候选；J4b 应优先 T3 与 T1。

### A2：4 卡 TP2/DP2/EP4 基线

- 结果：32k 与 24k 都未 OOM，但都 `rc=1`。
  - 32k：显存峰约 81GB，step_wall 约 188.5s。
  - 24k：显存峰约 72.8GB，step_wall 约 158.5s。
- 关键错误：`RuntimeError: Split sizes doesn't match total dim 0 size`，发生在 MoE `all_to_all_single`，路径是 actor/log_probs 前向的 MoE dispatch。
- 这不是显存不够，疑似合成 routing tape / EP-DP 组合 / alltoall split 与训练 forward 不匹配。
- 新怀疑点：`rh2/experiments/p3_preflight/lib/make_synth_rollout.py` 用 `torch.randint(0, num_experts, (rows, layers, topk))` 生成 routing tape，会允许同一 token/layer 的 top-k expert id 重复。真实 router/SGLang 的 top-k 通常应是无重复专家 id；重复专家可能破坏 MoE dispatcher 的 split-size 计数不变量。因此 A2 的错误更可能是 synthetic tape 无效，而不是 A2 拓扑或硬件不可用。
- CSV 中 `kernel_err=1` 目前也可能是误报：`run_j3.sh` 的 grep 包含 `cutlass`，而日志里正常提示 `pip install flash-attn-4==4.0.0b11 nvidia-cutlass-dsl[cu13]`。应把真实错误看作 split mismatch，不应写成 kernel failure。

建议补测/排查：

1. 继续让 J3 矩阵自然推进，不要中途改主参数。
2. 对所有 `rc=1 && kernel_err=1` 的 A2/A3 结果，单独归因为 “MoE all-to-all split/routing synthetic data issue”，不要误判成 4 卡不可训练。
3. 若 A4（官方同款 8 卡 TP4/CP2/EP8）通过，优先怀疑 A2/A3 合成 routing tape 与非官方 EP/DP 组合不兼容，而非模型/硬件不行。
4. 若 A4 也同类错误，需要回查 `make_synth_rollout.py` 的 `rollout_routed_experts` 形状、`routed_experts_start_len`、以及 slime 对 `--use-rollout-routing-replay` 的消费假设。
5. 建议新增一个小补丁/旁路脚本生成 “unique top-k routing tape”：对每个 token/layer 用 `torch.randperm(num_experts)[:topk]` 或等价无重复采样，而不是独立 `randint`。补测 A2 32k 或 A4，若错误消失，说明原 J3 synthetic tape 不合法。
6. 建议收尾时修正 `kernel_err` 统计口径：不要把 flash-attn 安装建议中的 `cutlass` 字样计为内核错误；可只匹配 `cutlass.*(error|failed|unsupported)` 或保留原始 grep 命中行。
7. 若 A3/A4 继续因同类 split mismatch 失败，建议加一个 `no-routing-replay` 控制格：同 A2 或 A4，但去掉 `--use-rollout-routing-replay` 并移除/忽略 `rollout_routed_experts`。这个控制格不能替代 routing tape 验收，但可以把 “Megatron 30B 训练硬件/显存/step 时间” 与 “routing replay tape 语义” 分开，避免 J3 被合成数据问题拖偏。

### 额外配置观察

- slime 官方 30B 测试锚点是 8 卡 `TP4 + CP2 + EP8`，并使用真实 rollout routing；A2/A3 这类非官方 EP/DP 组合更像探索项。若 A4 官方同款通过，应优先以 A4/T1 或 T3 修正形态推进，不要为了 A2/A3 花太多租卡时间。
- 官方测试还支持 DeepEP 路径：`--moe-token-dispatcher-type flex --moe-enable-deepep`。当前 P3 脚本按协议使用 alltoall。DeepEP 可作为可选性能/兼容性补测，但不建议在主矩阵中途切换，因为会改变变量。

### A3：6 卡 TP2/DP3/EP2 基线

- 结果：32k 与 24k 都快速失败，显存峰仅约 562MiB，未进入模型加载/训练。
- 关键错误：`AssertionError: global batch size (64) is not divisible by micro batch size (1) times data parallel size (3)`。
- 这是矩阵设计/静态校验漏项，不是训练能力失败。`tests/check_p3_scripts.py` 只检查了 `TP × CP × PP × DP == GPUs` 和 EP 整除性，但未检查 Megatron 的 `global_batch_size % (micro_batch_size × data_parallel_size) == 0`。

建议补测/修正：

1. A3 当前结果应标为 invalid_config，而不是 failed_train。
2. 若仍需要 A3，补测时把 `global_batch_size` 改成可被 3 整除的值，例如 48 或 96；但这会改变 tokens/step，需要在报告里和 A1/A2/A4 分开解释。
3. 或者删除/降级 A3，把时间留给 A4 官方同款、A5 CP=2、以及 routing tape 修复补测。

### A4：8 卡 TP4/CP2/EP8 官方同款

- 32k 结果：未 OOM，显存峰约 34.6GB，ref forward 完成后，在 actor/log_probs 的 routing replay 阶段失败。
- 24k 结果：同样未 OOM，显存峰约 32.3GB，ref forward 完成后，在 actor/log_probs 的 routing replay 阶段失败。
- 关键错误同 A2：`RuntimeError: Split sizes doesn't match total dim 0 size`。
- A4 是最接近 slime 官方 30B 测试的训练形态。它也复现同类 split mismatch，强烈支持当前 J3 的主问题是 synthetic routing tape 不满足真实 router 不变量，而不是 A2/A4 拓扑或硬件不可用。

建议即时处理：

1. 在 J3/J4 决策前，优先补一个 `unique top-k routing tape` 版本的 A4 32k 或 A4 24k。现在 A4 两个上下文长度都失败在同一位置，这个补测优先级高于继续扩展更多普通矩阵格。
2. 同时补一个 `no-routing-replay` A4 控制格，用于确认训练硬件/显存/step 时间基线。
3. 如果执行线程直接进入 J4，也可以接受，但解释口径必须改变：J4 使用真实 `custom_generate` + SGLang routing tape，不再使用 J3 合成 tape。因此 J4 是“真实 routing tape 是否满足 slime 回放语义”的验证，而不是普通拓扑速度测试。若 J4 通过，说明 J3 synthetic tape 不合法；若 J4 也同类失败，才应升级为 `capture_wire`/回填逻辑或 slime routing replay 契约问题。
4. 在上述控制项完成前，不建议用当前 J3 rc=1 结果推翻 8 卡训练链路；当前证据只能说明“J3 合成 routing replay 数据不可直接作为拓扑成功/失败判据”。

### A5：4 卡 TP2/CP2/DP1/EP4 降档

- 结果：未运行。
- 这不是当前遗漏。`run_j3.sh` 默认 `J3_CONFIGS="a1 a2 a3 a4"`，A5 在脚本与协议里都写成“仅当 32k 显存不够时启用”的 CP=2 降档。
- 当前 A2/A4 失败不是显存问题，而是 routing replay split mismatch；A5 不能优先解决这个问题。若后续修复 routing tape 后 A2 仍显存压力过高，再启用 A5 更合理。

## 不建议中途改变的事项

- 不建议在 J3 主矩阵中途为了救某一格改全局 flags。当前矩阵价值在于保留失败形态。
- 不建议把 A1 OOM 直接扩展为 “30B 双卡永远不可行”。应写成 “当前 A1 TP2/DP1/EP2 基线不可行，offload_train/PP2 救援待测或已测”。
- 不建议把 A2 rc=1 写成 OOM 或硬件失败；它目前是 MoE split/routing 语义错误。

## 待继续监控

- 若继续做 J3 控制实验，优先看 `unique top-k routing tape` 是否能让 A4/A2 的 routing replay 通过。
- 若继续做 A1 双卡救援，只能把 `offload_train` / `PP2` 当作探索项；不要让它阻塞 T3/T1 主线。
- J4 若直接启动，应明确它是在验证真实 SGLang routing tape 与 slime routing replay 的契约，而不是补 J3 普通速度矩阵。
- J4/J4b 是否按协议保留 top-p tape、routing replay、mismatch metrics、checkpoint discard 声明。

## 12:01 后新增观察：执行线程已启动 `diag_no_replay` 控制实验

- 远端出现新的 Ray job：A4 形态（8 卡 `TP4/CP2/EP8`，32k，`--debug-train-only`，`num_rollout=1`），但命令里没有 `--use-rollout-routing-replay`。
- 这是正确的控制实验：如果它跑通，说明 Megatron 30B 训练本体、A4 拓扑、top-p tape 训练路径大体成立，J3 主失败集中在 routing replay 数据或契约。
- 结果：已跑通，Ray job `raysubmit_TYS831QyDXbjffRE` 返回 `SUCCEEDED` / exit 0。
- 关键指标：
  - `ref_log_probs_time = 179.773s`
  - `actor_train_time = 468.893s`
  - `train_time = 649.329s`
  - `step_time = 663.309s`
  - `actor_train_tok_per_s = 4472.56`
  - `train/grad_norm = 3.2955`
  - `train/train_rollout_logprob_abs_diff = 1.6389`（因为这是合成数据 + 无 routing replay 控制实验，不能当真实失配质量结论）
- 解释：A4/30B/top-p/反传本体成立。J3 原 A2/A4 的 `Split sizes doesn't match total dim 0 size` 不应再被解释为 8 卡训练拓扑、显存或基础 Megatron 链路失败，应收敛到 routing replay 数据或契约。
- 当前补测 evidence 写在容器内 `/root/preflight_evidence_diag_no_replay`，不是宿主挂载盘 `/mnt/p3/preflight_evidence`。后续收尾要把该目录复制回 `/mnt/p3` 或记录 tarball digest，否则机器释放后证据会丢。
- 如果 `diag_no_replay` 通过，下一步优先级应是：
  1. `unique top-k routing tape` 的 A4 32k/24k；
  2. 若 unique tape 仍失败，再跑 J4 真实 routing tape；
  3. 若 J4 真实 routing tape 也同类失败，再查 `capture_wire.py`、`backfill_leaf_sample()` 与 slime `prepare_routed_experts_for_routing_replay()` 的行数/切片契约。
- 限定：该控制实验只跑 `num_rollout=1`，不是完整 J3 速度矩阵，也不是 J4 全链路验收。它的价值是证明 “30B 训练本体可以越过 ref forward 并进入 actor_train”，不要把它包装成正式拓扑吞吐结论。
- 运行中观察：`actor_train` 阶段出现 PyTorch/Megatron 的 `AccumulateGrad node's stream does not match...` warning。当前脚本禁用了 CUDA graph，因此这更像性能/同步警告，不应直接判失败；若后续 step 时间异常偏慢，可把它列为性能排查项。

## J4 运行中观察

- J4 已启动，Ray job `raysubmit_jdcC9jk5SMHwxRtM`，入口是 `train_async.py`，形态为 T3：4 张训练卡 + 4 张推理卡。
- 启动命令确认带有：
  - `--use-rollout-routing-replay`
  - `--rollout-top-p 0.95`
  - `--get-mismatch-metrics` 未在当前命令中看到。远端实际脚本已把 `J4_MISMATCH_METRICS` 默认改为 `0`，注释说明当前 slime pin 要求同时提供 `J4_CUSTOM_TIS_FUNCTION_PATH` 才能开启。这应在最终报告里作为协议偏离说明：J4 不采集 mismatch metrics，本次只验证 routing/top-p/训练闭环；M2 失配质量指标需另起带 TIS 函数的补测。
  - `RH2_EXPECT_MOE_ROUTING=1`
  - `--save-debug-rollout-data /root/preflight_j4/rollout_dumps/rollout_{rollout_id}.pt`
- 参数打印确认 `use_rollout_routing_replay=True` 且 `use_routing_replay=True`，所以训练侧 routing replay 环境变量路径应会打开；日志中 `moe_enable_routing_replay=False` 是另一个字段，不应单独视为 routing replay 未开启。
- SGLang 侧已经启用 routed experts 返回：日志里的 server args 显示 `enable_return_routed_experts=True`，并分配了 `HostCache[routed_experts]` 与 `DeviceCache[routed_experts]`。
- 当前 GPU 水位：训练卡约 46GB/卡，推理卡约 75GB/卡；说明 J4 正在真实加载 30B 训练与推理分区，不是空跑。
- 注意：`j4_exit_code.txt` 当前内容为 `1`，但时间戳早于当前 Ray job 启动，暂按旧/中间状态文件处理；最终仍以 Ray job 状态、`j4_wall.txt`、`j4_assertions.json` 和脚本结束后的 exit code 为准。
- 风险观察：脚本传了 `--sglang-disable-cuda-graph`，参数里也有 `disable_cuda_graph=True`，但日志仍显示 `Capture piecewise CUDA graph begin`。这可能说明 piecewise CUDA graph 是 SGLang 的另一条路径。如果 J4 因启动时间、显存或 CUDA graph 相关问题失败，应补查是否还需要额外关闭 piecewise graph。
- 非致命性能观察：SGLang 在 RTX Pro 6000 Blackwell 上提示缺少 MoE kernel config，使用 default MoE kernel config，可能影响推理吞吐，但不是功能失败。

### J4 失败：dynamic filter 不支持 fan-out `Sample`

- 结果：J4 失败，Ray job `raysubmit_jdcC9jk5SMHwxRtM` 为 `FAILED`，`j4_wall_seconds=179 rc=1`。
- 通过项：
  - SGLang 两个 TP2 engine 启动成功，`enable_return_routed_experts=True`；
  - startup probe 通过，`j4_assertions.json` 的 `2_startup_probes=PASS`；
  - 训练到推理的权重同步通过，`Timer update_weights end (elapsed: 11.2s)`；
  - 显存无 OOM，`5_memory_watermark_no_oom=PASS`。
- 失败点：第一次真实 rollout 生成后，`slime.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std` 抛出：
  `AttributeError: 'list' object has no attribute 'get_reward_value'`。
- 根因：RepoHarness / TrajectoryManager 的 custom generate 会返回 fan-out 形态，即单个原始样本可以变成 `list[Sample]`。slime 的 `generate_and_rm_group()` 注释已经允许这一点，并且后续 `_get_rollout_data()` 会在 `_validate_rollout_id_annotated()` 后 flatten 嵌套样本；但是 stock dynamic filter 在 flatten 之前调用，`check_reward_nonzero_std(args, samples: list[Sample])` 仍假设 group 内每个元素都是 `Sample`，没有处理 `list[list[Sample]]`。
- 这次失败还没有进入 ref logprobs、actor train 或 routing replay 消费，所以不能用它判断真实 routing tape 是否能训练。
- 建议补测：
  1. 立即补一轮 `J4_DYNAMIC_FILTER=0` 的 J4，让真实 `custom_generate` + top-p tape + routing tape + 训练消费先闭环；
  2. 动态采样过滤另做 fan-out aware 版本，例如对每个原始 group 先 flatten sibling samples，再按“同一原始 rollout 的 reward 聚合值”或“任一/平均 sibling reward”计算非零方差；
  3. 在最终报告中明确：J4 当前失败是 dynamic filter 与 fan-out shape 的兼容性问题，不是 SGLang、权重同步、显存、top-p 或 routing replay 已失败。
- `j4_assertions.json` 当前状态：
  - `1_rollout_samples=FAIL`，`num_samples=0`；
  - `2_startup_probes=PASS`；
  - `3_tape_consumed_loss_finite=UNKNOWN`；
  - `4_grad_norm=UNKNOWN`；
  - `5_memory_watermark_no_oom=PASS`；
  - `6_checkpoint_produced_then_discarded=FAIL`（未产出 checkpoint，但脚本仍执行了 discard 声明）。
- 执行线程已经把这次失败产物复制到 `/mnt/p3/preflight_evidence/j4_fail_dynamic_filter/`，后续重跑 J4 时不应覆盖这份失败证据。

### J4 重跑：已绕开 dynamic filter

- 12:27 UTC 观察到新的 J4 Ray job `raysubmit_2RUzfttBtqWPLBiX` 正在运行。
- 入口命令确认：
  - 保留 `--use-rollout-routing-replay`；
  - 保留 `--rollout-top-p 0.95`；
  - 未出现 `--dynamic-sampling-filter-path`，说明这轮确实绕开了上一次 `check_reward_nonzero_std` 与 fan-out `list[Sample]` 不兼容的失败点。
- 12:29 UTC 该轮失败，失败点比上一轮靠后：
  - SGLang 两个 TP2 engine 启动成功；
  - `Timer update_weights end (elapsed: 11.1s)`，权重同步成功；
  - 生成了 `/root/preflight_j4/rollout_dumps/rollout_0.pt`；
  - 随后训练侧在 `fill_routing_replay()` 报错：
    `ValueError: rollout_routed_experts is required in rollout_data when use_rollout_routing_replay is set.`

#### J4 重跑的真正根因：任务镜像未预拉，32 个样本全部 materialize abort

- `rollout_0.pt` 结构：`samples` 长度 32，每个样本都有 `rollout_routed_experts` 键，但值全是 `None`。
- 统计结果：
  - `status='aborted'`：32/32；
  - `abort_reason='rh2_materialize_failed:SlimeBindingError'`：32/32；
  - `response_length=1`，`loss_mask` 全 0；
  - `rollout_top_p_token_ids` 全为空列表；
  - `rollout_top_p_token_offsets` 只有长度 2 的零宽占位。
- `bringup_events.jsonl` 里的直接错误：
  `rollout_image_inspect_failed`，例如
  `swebench/sweb.eval.x86_64.django_1776_django-11099:latest 不可用：No such image`。
- 远端宿主机 `docker images` 确认没有任何 SWE 任务镜像，只有主运行容器镜像。
- Docker Hub 查询确认 `_1776_` 镜像本身存在：
  `docker manifest inspect swebench/sweb.eval.x86_64.django_1776_django-11099:latest`
  返回成功。因此当前不应改成 `_s_` 命名；更直接的修复是按 J4 数据里的 8 个 image 引用逐个 `docker pull`。

建议立即反馈给执行线程：

1. **不要把这轮 J4 写成 routing replay 失败。** 它没有产生有效 rollout，自然没有 routing tape。
2. 在继续 J4/J4b 前，先预拉 `/root/preflight_j4/swe_bringup_8.jsonl` 中的 8 个唯一 `metadata.image`：
   - `swebench/sweb.eval.x86_64.django_1776_django-11099:latest`
   - `swebench/sweb.eval.x86_64.django_1776_django-11133:latest`
   - `swebench/sweb.eval.x86_64.django_1776_django-16139:latest`
   - `swebench/sweb.eval.x86_64.sympy_1776_sympy-14711:latest`
   - `swebench/sweb.eval.x86_64.sympy_1776_sympy-15349:latest`
   - `swebench/sweb.eval.x86_64.psf_1776_requests-1142:latest`
   - `swebench/sweb.eval.x86_64.psf_1776_requests-2931:latest`
   - `swebench/sweb.eval.x86_64.astropy_1776_astropy-14995:latest`
3. 预拉后先做一个便宜的 sanity check：在 `rh2-p3` 容器里用 `/root/tarballs/docker-cli/docker image inspect <image>` 逐个通过，确保 custom_generate 的 PATH/宿主 docker socket 视角可见，而不只是宿主 shell 可见。
4. 再重跑 J4。若那时仍缺 `rollout_routed_experts`，才进入 capture/backfill/routing replay 的代码层排查。
5. 后续脚本层建议补一条 J4 前置门：如果 8 个 image 任一不可 inspect，则直接 fail fast，不要启动 30B 训练和 SGLang 服务。

### 镜像预拉进度

- 12:36 UTC：预拉脚本已经实际运行，日志为
  `/mnt/p3/preflight_evidence/j4_image_prefetch.log`。
- 已完成并通过 digest 检查：
  - `django__django-11099`，约 2.67GB，59.3 秒；
  - `django__django-11133`，约 2.67GB，4.9 秒；
  - `django__django-16139`，约 2.82GB，27.5 秒。
- 正在拉第 4 个：
  - `sympy__sympy-14711`。
- 磁盘状态：系统盘 `/` 从预拉前约 184GB 可用降到约 180GB 可用，仍安全；
  `/mnt/p3` 仍约 673GB 可用。当前镜像落在宿主机 Docker 默认数据目录，
  短期 8 个 smoke 镜像没问题，长期大规模镜像仍建议迁移 Docker data root 到 `/mnt/p3`。
- GPU 状态：8 张卡均 0MiB，说明当前没有继续跑 J4/J4b。
- 12:37 UTC：8 个镜像全部预拉完成，日志记录
  `all_images_prefetched_and_digest_verified=true`。
- 宿主机 Docker 镜像清单确认 8 个 `swebench/sweb.eval...` 镜像均在场，总 Docker
  image size 从 44.35GB 增至 52.11GB。系统盘 `/` 仍有约 177GB 可用。
- 容器内可见性确认：在 `rh2-p3` 内通过
  `/root/tarballs/docker-cli/docker image inspect <image>` 检查 8 个镜像全部 `OK`。
- 因此，阻塞 J4 的任务镜像缺失问题已经解除；下一次 J4 如果仍然失败，应重新按失败
  边界定位，不要沿用“镜像缺失”解释。
- 12:39 UTC：执行线程已经重新启动 J4：
  `cd /workspace/rh2/experiments/p3_preflight && P3_EV=/root/preflight_evidence bash ./j4_full_step.sh`。
  此时 Ray job 尚未提交，GPU 仍空闲。
- 证据管理良好：上一轮缺镜像失败产物已移到
  `/mnt/p3/preflight_evidence/j4_fail_missing_images_before_prefetch_20260708T123904Z/`，
  当前 `/mnt/p3/preflight_evidence/j4/` 已重新初始化，没有覆盖旧失败证据。
- 12:41 UTC：新 J4 Ray job `raysubmit_1zW7jY54R9etAQjb` 正在运行。
  当前处于 SGLang 加载/启动区间：
  - 训练卡 0~3 约 46.8GB；
  - 推理卡 4~7 约 74.0GB；
  - `RolloutManager` 已 `Launch router`；
  - 还没有 `bringup_events.jsonl`、`rollout_dumps` 或 exit/assertion 文件。
  下一判断点：SGLang `Application startup complete`、权重同步、真实 rollout 产物。
- 12:43 UTC：两个 SGLang engine 均已 `Application startup complete`，
  `update_weights` 已开始且 SGLang 端返回大量
  `POST /update_weights_from_distributed HTTP/1.1" 200 OK`。尚无
  `bringup_events.jsonl` 或 rollout dump，说明真实 rollout 还没有完成。
- 磁盘观察：系统盘 `/` 可用约 159GB（从预拉完成后的约 177GB 下降），仍安全；
  这次 J4 会启动 rollout/grading 容器，继续监控系统盘避免 Docker 默认目录膨胀。
- 12:47 UTC：确认已经越过环境镜像物化阶段：
  - 远端有 32 个 `rh2-rollout-*` 容器正在运行，对应 8 题 × 每题 4 样本；
  - 推理卡 4~7 利用率约 37%~64%，说明真实 agent/model 交互正在发生；
  - 训练卡 0~3 仍处于等待 rollout 的加载态；
  - 尚无 `bringup_events.jsonl` 或 rollout dump，说明还没有单条 rollout 完成。
  当前不应中断，需等待第一批样本完成后再判断 tape 是否齐全。
- 12:52~12:54 UTC：J4 暴露出新的真实阻塞点，已经不是镜像问题。
  多条样本完成了真实 harness 路径：
  `step2_workspace_materialized` → `step3_harness_completed` →
  `step4_capture_records_ready`，但随后在 `assemble/finalize` 阶段 fail-closed：
  - `rh2_finalize_failed:SlimeProjectionError`：
    `[routing_shape_unknown] b0.rollout_routed_experts 是扁平载荷（base64/bytes/一维 list），必须提供 moe_num_layers 与 moe_router_topk 才能切行（Qwen3-30B-A3B 为 48 与 8）。`
  - `rh2_assemble_failed:SlimeBindingError`：
    `[routing_rows_mismatch_backfill] 最后一轮 routing 元素数 ... 不能按 len(tokens)-1=... 行整除。`
  这说明 SGLang/会话侧已经产生了某种 routed-experts 载荷，但 rh2 的真实 J4
  glue/projection/backfill 路径没有拿到足够的 MoE 形状元数据，或对多轮/full-prefix
  routing tape 的切行语义仍有不一致。
- 本地代码边界核对：
  - `SlimeBindingConfig` 已有 `moe_num_layers` / `moe_router_topk` 字段；
  - `s1_parity.py` 里的工作例会显式给 Qwen3-30B-A3B 使用 `48` / `8`；
  - `s1_7a_bringup/glue.py` 当前只从环境变量读取
    `RH2_EXPECT_MOE_ROUTING`，构造 `SlimeBindingConfig` 时只显式传入
    `expect_moe_routing=EXPECT_MOE_ROUTING`；
  - `p3_preflight/j4_full_step.sh` 当前只设置 `RH2_MODEL_ID=Qwen/Qwen3-30B-A3B`
    与 `RH2_EXPECT_MOE_ROUTING=1`，没有设置或传递
    `RH2_MOE_NUM_LAYERS=48` / `RH2_MOE_ROUTER_TOPK=8`。
  因此最小根因假设是：P3 J4 真实 glue 配置遗漏了 Qwen3-30B-A3B 的 MoE
  routing 形状参数；补齐后仍需单独验证 `routing_rows_mismatch_backfill`
  是否随之消失，因为这可能还涉及最后一轮和 full-prefix routing payload 的行语义。
- 建议反馈给执行线程：不要继续把当前 J4 当作有效训练闭环等待。当前已获得足够证据说明
  所有完成样本都会在 routing tape 组装或投影处被拒绝。更省钱的路径是保留本轮证据，
  停掉当前 J4，补齐 MoE 形状配置后先用 1~2 题、每题 1~2 样本做小规模重跑，确认
  `rollout_routed_experts` 能进入最终 `Sample`，再恢复 8 题 × 4 样本。
- 12:56 UTC：事件流统计确认失败已经具有代表性：
  - 已完成事件 27 条；
  - `Status.ABORTED`：27/27；
  - `rh2_finalize_failed:SlimeProjectionError`：16/27；
  - `rh2_assemble_failed:SlimeBindingError`：11/27；
  - 27/27 都至少走到
    `step1_custom_generate_invoked`、`step2_workspace_materialized`、
    `step3_harness_completed`、`step4_capture_records_ready`；
  - 16/27 还走到 `step5_leaf_samples_assembled_and_backfilled` 与
    `step6_grading_completed`，随后在最终投影处因 routing shape unknown 被拒绝。
  这进一步说明：环境物化、黑盒 harness、模型交互、capture wire、评分路径都已经被真实执行；
  当前阻塞集中在 MoE routing tape 载荷进入 rh2 `Sample`/projection 的形状和行语义。
- 12:56 UTC 远端运行态：
  - Ray job `raysubmit_1zW7jY54R9etAQjb` 仍为 `RUNNING`；
  - 32 个 rollout 中剩余 5 个容器仍在运行；
  - GPU 0~3 约 48GB 显存但利用率 0%，GPU 4~7 约 75.5GB 显存且仍有推理利用率；
  - host 侧 `/mnt/p3/preflight_evidence/j4/` 只有 `dmon_all.csv`、`j4_full_args.txt`、
    `j4_train.log`，还没有最终断言文件。
  由于 27 个已完成样本已经全部落在同一 routing tape 阻塞族，继续跑完剩余 5 个只会补充
  失败样本数量，不会改变当前结论。建议止损停止本轮 J4。
- 12:57~12:59 UTC：连续三轮只读轮询：
  - `bringup_events.jsonl` 从 27 行增加到 29 行；
  - 剩余 rollout 容器从 5 个减少到 3 个后不再下降；
  - Ray job 仍为 `RUNNING`；
  - GPU 0~3 利用率为 0%，GPU 6/7 仍有推理利用率，说明少数长尾 rollout 继续占住整轮资源；
  - host 侧仍未出现最终断言或 checkpoint 文件。
  因此这轮 J4 同时暴露两个问题：
  1. 已完成样本全部因 routing tape 形状/行语义失败；
  2. 同步等待整组 32 条样本会被最后几条长尾拖住训练和推理资源。
  第二点不改变当前最小修复顺序：先补齐 routing tape 配置并小规模重跑，再讨论长尾 abort/
  partial/buffer 的异步调度优化。
- 12:59 UTC：仍为 29/32，剩余 3 个容器全部是 `django__django-11133`。
  SGLang 日志仍在持续 decode，因此不像进程死锁，更像同一任务组的长尾轨迹。训练侧 GPU
  0~3 显存仍占用但利用率为 0，说明同步训练闭环正在等待 rollout 组收齐。
- 13:01 UTC：J4 自然结束，Ray job `FAILED`，8 张 GPU 显存均回到 0MiB。
  host 侧出现 `j4_assertions.json`、`j4_assertions_acceptance.txt`、`j4_wall.txt`。
  关键断言：
  - `1_rollout_samples`: `PASS`，`num_samples=32`，`dump_files=["rollout_0.pt"]`；
  - `2_startup_probes`: `PASS`，`engine_weight_version="1"`；
  - `3_tape_consumed_loss_finite`: `FAIL`，`routing tape missing`，`num_loss_values=0`；
  - `4_grad_norm`: `UNKNOWN`，`num_values=0`；
  - `5_memory_watermark_no_oom`: `PASS`，无 OOM；
  - `6_checkpoint_produced_then_discarded`: `FAIL`，但 `j4_assertions_acceptance.txt`
    声明 `checkpoint_discarded=true`。该 FAIL 的根因是没有走到有效训练 step，自然没有生成
    可丢弃 checkpoint。
  `j4_wall_seconds=1290 rc=1`。
- 最终事件统计：
  - `Status.ABORTED`: 32/32；
  - `rh2_finalize_failed:SlimeProjectionError`: 19/32；
  - `rh2_assemble_failed:SlimeBindingError`: 13/32；
  - 8 个任务各 4 条全部覆盖，不是单任务偶发。
  训练尾日志最终失败：
  `ValueError: rollout_routed_experts is required in rollout_data when use_rollout_routing_replay is set.`
  这与事件统计完全一致：J4 已经证明 30B + top-p + SGLang 请求层能启动，任务镜像与黑盒
  harness 能跑，但 routing tape 没有以训练侧要求的 `rollout_routed_experts` 字段进入
  `rollout_data`。
- `startup_evidence.json` 显示启动探针通过：`generated_token_count=16`、
  `logprobs_entries=16`、`top_p_token_offsets_len=17`、`top_p_kept_token_count=21`、
  `routing_rows_expected=24`、`engine_weight_version="1"`。这证明 probe 层至少拿到了
  token/logprob/top-p 相关证据，并认为 routing rows 有期望值。
- `rollout_0.pt` 反查：
  - `samples` 长度 32；
  - 每条都有 `rollout_routed_experts` 字段，但 32/32 都是 `None`；
  - `rollout_top_p_token_ids` 32/32 为空，`rollout_top_p_token_offsets` 32/32 为 `[0, 0]`；
  - `response_length` 32/32 为 1，`loss_mask` 32/32 为 `[0]`；
  - `status` 32/32 为 `aborted`，`remove_sample` 32/32 为 `True`；
  - Sample metadata 只保留粗粒度 `abort_reason`（如
    `rh2_finalize_failed:SlimeProjectionError`），具体 `routing_shape_unknown` 与
    `routing_rows_mismatch_backfill` 细节只在 `bringup_events.jsonl`。
  因此后续检查不能只看 slime dump；必须把事件流作为同级证据，否则会丢失根因细节。
- 入口代码核对：
  - `rh2/experiments/s1_7a_bringup/glue.py:80-84` 只读取
    `RH2_EXPECT_MOE_ROUTING`；
  - `rh2/experiments/s1_7a_bringup/glue.py:336-350` 构造
    `SlimeBindingConfig` 时只传入
    `expect_moe_routing=EXPECT_MOE_ROUTING`，未传入
    `moe_num_layers` / `moe_router_topk`；
  - `rh2/experiments/p3_preflight/j4_full_step.sh:176-185` 只向 Ray runtime env
    注入 `RH2_MODEL_ID=Qwen/Qwen3-30B-A3B` 与 `RH2_EXPECT_MOE_ROUTING=1`；
  - `rh2/experiments/s1_parity.py:327-339` 的 30B 工作例显式传入
    `moe_num_layers=48`、`moe_router_topk=8`。
  这给出最小修复方向：把 30B 的 MoE routing 形状以显式配置传入真实
  `s1_7a_bringup.glue` 路径，并在小规模 J4 重跑中先验证
  `rollout_routed_experts` 非空。修完后还要继续验证 13 条
  `routing_rows_mismatch_backfill` 是否消失；如果不消失，再进一步排查 full-prefix
  routing payload 与最后一轮 token 对齐语义。
- 13:04~13:08 UTC：四轮空闲监控确认远端没有自动重跑：
  - 8 张 GPU 显存均为 0MiB，利用率 0；
  - 只剩主容器 `rh2-p3`；
  - Ray job 列表只显示失败的 `raysubmit_1zW7jY54R9etAQjb`；
  - `/mnt/p3/preflight_evidence/j4/` 文件稳定为
    `dmon_all.csv`、`j4_assertions.json`、`j4_assertions_acceptance.txt`、
    `j4_full_args.txt`、`j4_train.log`、`j4_wall.txt`。
  当前机器处于空闲可修复/可重跑状态。

### J4 修复后重跑监控

- 13:12 UTC：执行线程已经启动新的 J4：
  `raysubmit_qswmi1uskmBrEqWD`，Ray 状态 `RUNNING`。
  远端运行环境已经包含修复项：
  - `RH2_MOE_NUM_LAYERS=48`；
  - `RH2_MOE_ROUTER_TOPK=8`。
  新命令还新增：
  - `--custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data`；
  - `--global-batch-size 16`（上一轮为 32）。
  32 个 `rh2-rollout-*` 容器已经全部启动，`/mnt/p3/preflight_evidence/j4/`
  已重新初始化，只剩当前轮的 `dmon_all.csv`、`j4_full_args.txt`、`j4_train.log`。
  下一判断点：第一批完成样本是否仍是 `aborted`，以及 `rollout_0.pt`
  中 `rollout_routed_experts` 是否非空。
- 13:13 UTC：证据卫生问题。新 Ray job 的 `start_time=1783516157399`
  （约 13:09:17 UTC），但容器内：
  - `/root/preflight_j4/artifacts/bringup_events.jsonl` 修改时间仍是 13:00:54；
  - `/root/preflight_j4/rollout_dumps/rollout_0.pt` 修改时间仍是 13:00:54；
  - 只有 `/root/preflight_j4/artifacts/startup_evidence.json` 在 13:11:56 更新。
  `bringup_events.jsonl` 当前 32 行全是上一轮失败事件，第一行时间为 12:48:00，
  最后一行为 13:00:54，均早于新 job 启动时间。若新运行继续向该文件追加，
  或最终 inspector 读取旧 `rollout_0.pt`，会造成跨轮证据污染。
  建议执行线程立刻确认本轮是否会在正式写入前清空
  `/root/preflight_j4/artifacts/bringup_events.jsonl` 与
  `/root/preflight_j4/rollout_dumps/`；否则应该停止重跑、归档旧目录、用全新
  `BRINGUP` 目录或显式清理后再跑。
- 13:16 UTC：远端已经停止/重置这轮重跑：
  - GPU 全空；
  - 无 `rh2-rollout-*` 容器；
  - `ray job list` 连接 `127.0.0.1:8265` 被拒绝，说明 Ray 已停止；
  - `/mnt/p3/preflight_evidence/j4/` 当前为空。
  这符合证据污染风险暴露后的正确处理方向：不要在旧 `/root/preflight_j4`
  状态上继续产出验收文件，应该清理或换新 `BRINGUP` 目录后再启动干净重跑。
- 13:16~13:17 UTC：又启动了新 Ray job `raysubmit_E1JHCyzYniawbxsG`。
  修复变量仍在：
  - `RH2_MOE_NUM_LAYERS=48`；
  - `RH2_MOE_ROUTER_TOPK=8`；
  - `--custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data`。
  但路径仍然复用旧目录：
  - `RH2_BRINGUP_ARTIFACT_DIR=/root/preflight_j4/artifacts`；
  - `--save-debug-rollout-data /root/preflight_j4/rollout_dumps/rollout_{rollout_id}.pt`。
  当时旧文件仍在：
  - `bringup_events.jsonl` 仍为上一轮 32 行，修改时间 13:00:54；
  - `rollout_0.pt` 仍为上一轮 dump，修改时间 13:00:54。
  因此这轮仍有证据污染风险。除非执行线程能证明 job 内部会在正式写入前清理这些文件，
  否则仍建议停止并清空 `/root/preflight_j4/artifacts/bringup_events.jsonl`、
  `/root/preflight_j4/rollout_dumps/` 后再跑。
- 13:25 UTC：证据污染实际发生，`bringup_events.jsonl` 从旧 32 行追加到 36 行。
  新 job 启动后追加事件 4 条：
  - `Status.COMPLETED`: 3 条；
  - `Status.ABORTED`: 1 条；
  - 3 条完成样本已经走到
    `step7_projection_completed`、`step8_gate_finalized`、`step9_samples_delivered`；
  - 完成样本的 `response_lengths` 与 `top_p_offsets_len` 不再是上一轮的 `[1]` / `[2]`，
    例如首条为 `response_lengths=[993]`、`top_p_offsets_len=[994]`。
  技术含义：`RH2_MOE_NUM_LAYERS=48` 与 `RH2_MOE_ROUTER_TOPK=8` 的修复已经让部分
  MoE routing tape 成功进入可交付样本。
  仍存在的问题：1 条新样本在 `assemble` 阶段失败：
  `[routing_rows_mismatch_backfill] 最后一轮 routing 元素数 11535360 != len(tokens)-1 行的期望 7409280（rows=19295 x layers=48 x topk=8）。`
  这说明剩余问题不再是“完全缺 MoE 形状”，而是部分轨迹的 routing 行语义或 full-prefix
  token 对齐仍不一致。
  结论：当前 run 可作为技术诊断，但由于事件文件混入上一轮 32 条旧失败事件，不能作为正式
  J4 验收 evidence。
- 13:28 UTC：新追加事件达到 13 条：
  - `Status.COMPLETED`: 8 条；
  - `Status.ABORTED`: 5 条；
  - 失败原因全部为 `rh2_assemble_failed:SlimeBindingError`；
  - 不再出现 `routing_shape_unknown`。
  完成样本的 `response_lengths` 包括 993、4933、1029、1088 等，证明它们不是上一轮那种
  `response_length=1` 的占位失败样本。失败样本的错误均为
  `routing_rows_mismatch_backfill`，例如：
  - routing 元素数 `11535360`，期望 `7409280`（`rows=19295 x layers=48 x topk=8`）；
  - routing 元素数 `8355840`，期望 `8170752`；
  - routing 元素数 `7583232`，期望 `7860864`。
  技术结论进一步收敛：MoE 形状元数据传递已修好；剩余是部分轨迹的 routed-experts 行数
  与 tokenizer/renderer 复原出的最后一轮 token 行数不一致。
- 13:38 UTC：`raysubmit_E1JHCyzYniawbxsG` 最终失败：
  - Ray job 状态 `FAILED`，`driver_exit_code=1`；
  - 新 `rollout_0.pt` 已覆盖，大小约 430MB；
  - dump 内 `samples=36`，其中 `completed=22`、`aborted=14`；
  - `remove_sample=False`: 22，`remove_sample=True`: 14；
  - `rollout_routed_experts` 非空：22；
  - `rollout_top_p_token_ids` 非空：22；
  - `loss_mask` 非零：22；
  - reward 分布：`0.0` 为 33，`1.0` 为 3。
  技术含义：修复后的路径已经能产出带 routing tape、top-p tape 和 loss mask 的可训练样本。
  但训练没有进入 optimizer step，因为新增的自定义 converter 在远端仍是旧代码：
  `from slime.ray.rollout import RolloutRayActor`，当前 slime 版本没有该符号，实际类名为
  `RolloutManager`。因此失败栈为：
  `ImportError: cannot import name 'RolloutRayActor' from 'slime.ray.rollout'`。
- 本地工作树中 `rh2/experiments/p3_preflight/rh2_convert.py` 已经改成
  `from slime.ray.rollout import RolloutManager`，但远端容器
  `/workspace/rh2/experiments/p3_preflight/rh2_convert.py` 仍是旧版 `RolloutRayActor`。
  结论：下一轮重跑前必须先同步远端容器内代码；否则会重复同一 ImportError。
- 另一个非 routing 问题：日志显示 `django__django-11133` 至少一条轨迹陷入
  `code-review skill` 相关循环，反复请求 `Skill` 工具并超过
  `max_turns_per_sid=25` 后被 adapter 以 429 kill。这是 agent 行为质量和长尾问题，
  不应与 routing replay bug 混在一起。
- 13:40 UTC：远端容器已同步 converter 修复：
  `/workspace/rh2/experiments/p3_preflight/rh2_convert.py` 第 54 行变为
  `from slime.ray.rollout import RolloutManager`。GPU 空闲，Ray 未运行，host
  `j4` evidence 目录为空。下一轮重跑不会再因为 `RolloutRayActor` ImportError
  直接失败。
- 13:41 UTC：新 Ray job `raysubmit_hArChmiTHvjNnVP3` 已启动，且仍带
  `RH2_MOE_NUM_LAYERS=48` / `RH2_MOE_ROUTER_TOPK=8`。但是证据目录问题未修：
  - `RH2_BRINGUP_ARTIFACT_DIR` 仍为 `/root/preflight_j4/artifacts`；
  - 旧 `startup_evidence.json` 修改时间为 13:19:04；
  - 旧 `bringup_events.jsonl` 修改时间为 13:37:21，大小 80286；
  - 旧 `rollout_0.pt` 修改时间为 13:37:52，大小约 430MB。
  因此 host 侧 `j4` evidence 虽然被清空，容器内真实 BRINGUP 目录仍然不是干净状态。
  若继续运行，新事件会再次混入旧事件文件。必须在 Ray job 提交前清理容器内
  `/root/preflight_j4/artifacts` 和 `/root/preflight_j4/rollout_dumps`，或者为每次重跑使用
  唯一 `BRINGUP` 目录。
- 13:47~13:52 UTC：`raysubmit_hArChmiTHvjNnVP3` 开始产出新事件。按该 job 启动时间
  `1783518007.818` 切分：
  - 新事件 7 条；
  - `Status.COMPLETED`: 5；
  - `Status.ABORTED`: 2；
  - 失败仍为 `rh2_assemble_failed:SlimeBindingError`，也就是部分轨迹的 routing rows
    mismatch；
  - 剩余 rollout 容器 25 个。
  该 run 的 converter 已修为 `RolloutManager`，因此这轮最重要的技术判断是能否越过
  converter 进入训练侧；但因事件文件仍混入旧 run，仍不能作为正式验收 evidence。
- 14:02 UTC：`raysubmit_hArChmiTHvjNnVP3` 最终失败：
  - Ray job 状态 `FAILED`，`driver_exit_code=1`；
  - 32/32 rollout 完成，`rollout_0.pt` 已保存；
  - 失败栈：
    `TypeError: RolloutManager._convert_samples_to_train_data() takes 2 positional arguments but 3 were given`。
  原因：`RolloutManager` 在 slime 中是 `@ray.remote` 类，直接调用
  `RolloutManager._convert_samples_to_train_data(_Proxy(args), kept)` 不是普通 Python
  未绑定方法调用，会经过 Ray actor 包装层。该方法源码本身在
  `/root/slime/slime/ray/rollout.py:691-805`，逻辑并不依赖 rollout server 状态，主要依赖：
  `self.args`、`self._post_process_rewards(samples)`、以及 samples 字段。
  建议修复方向：
  1. 最稳：在 `rh2_convert.py` 中复制/内联 slime 默认转换逻辑的必要部分，避免依赖 Ray
     remote class 的私有方法绑定；
  2. 中期：给 slime 提 PR，把默认 sample→train_data 转换抽成可导入普通函数；
  3. 不优先：继续尝试从 Ray wrapper 中取原始 class 方法，因为这会绑定到 Ray 内部实现细节。
  另外，这轮仍然混入旧 `bringup_events.jsonl`，所以即使 converter 修好，正式验收仍需要唯一
  `BRINGUP` 目录或显式清理。
- 14:05 UTC：执行线程把 converter 改为
  `default_convert = RolloutManager._convert_samples_to_train_data.__wrapped__`，该属性存在，签名为
  `(self, samples, *, _ray_trace_ctx=None)`。但是 `RolloutManager._post_process_rewards`
  也是 Ray 包装方法，也有 `.__wrapped__`；当前远端 `_Proxy._post_process_rewards`
  仍指向包装方法本身。建议同步改为
  `_post_process_rewards = RolloutManager._post_process_rewards.__wrapped__`，否则下一轮可能在
  reward post-process 处因 wrapper 绑定或缺少 `self.args` 再失败。
## 2026-07-08 14:15-14:18 UTC 监控补充

- 读取远端 Ray job `raysubmit_jLLpp7JkeRCMR9BQ` 后确认：上一轮所谓“正常加载”的 J4 最终失败，直接错误为 `FileNotFoundError: Prompt dataset path '/root/preflight_j4/swe_bringup_8.jsonl' does not exist.`。这说明当时没有真正进入 SWE rollout，更没有进入训练转换或 loss 阶段。
- 远端 `j4_full_step.sh` 当前版本已经包含实跑前重新生成 `${BRINGUP}/swe_bringup_8.jsonl` 的逻辑；单独执行 `make_prompt_data.py --out /tmp/rh2_prompt_probe.jsonl` 成功产出 8 行。因此缺文件不是生成器不可用，而是上一轮清理与重跑顺序或脚本版本同步问题。
- 远端随后启动了新一轮 J4 wrapper：`P3_EV=/root/preflight_evidence J4_GLOBAL_BATCH_SIZE=16 bash ./j4_full_step.sh > /root/preflight_evidence/j4_wrapper_latest.log 2>&1`。本轮已确认 `/root/preflight_j4/swe_bringup_8.jsonl` 存在，大小 10900 字节。
- 潜在未修风险仍在：`/workspace/rh2/experiments/p3_preflight/rh2_convert.py` 使用 `RolloutManager._convert_samples_to_train_data.__wrapped__`，但 `_Proxy._post_process_rewards = RolloutManager._post_process_rewards` 仍未取 `__wrapped__`。如果 slime 默认转换器调用 `self._post_process_rewards(...)`，后续可能再次出现 Ray remote wrapper 签名或绑定问题。
- 当前判断：缺 prompt 文件问题已被新一轮启动纠正；是否完成正确修复仍需等新轮越过 rollout dump 和 train-data conversion 后才能确认。

## 2026-07-08 14:19 UTC 新轮运行状态

- 新轮 Ray job `raysubmit_JNeLtSnrAs48JEiP` 已进入 `RUNNING`。GPU 0~3 约 57GB 显存，GPU 4~7 约 74.6GB 显存，符合 4 张训练卡 + 4 张推理卡的 T3 形态。
- 训练日志已越过 prompt 数据加载和 RolloutManager 初始化，`Filtered 0 samples longer than max_length=32767` 说明 `/root/preflight_j4/swe_bringup_8.jsonl` 被 slime 成功读取。
- SGLang 侧已出现 `HostCache[routed_experts] allocated: shape=(917562, 48, 8)` 和 `DeviceCache[routed_experts] allocated: shape=(8192, 48, 8)`，说明 48 层、topk=8 的 MoE routing tape cache 当前配置正确。
- 截至 14:19 UTC，还没有产生 `/root/preflight_j4/artifacts/bringup_events.jsonl` 或 `/root/preflight_j4/rollout_dumps/rollout_0.pt`，因此尚不能证明 rollout、转换器和训练 step 成功。

## 2026-07-08 14:24 UTC 新轮中段状态

- Ray job `raysubmit_JNeLtSnrAs48JEiP` 仍为 `RUNNING`。训练卡 GPU 0~3 约 48GB 显存，推理卡 GPU 4~7 约 75GB 显存，推理侧有 20%~88% 不等的利用率。
- 日志显示 `/root/preflight_j4/swe_bringup_8.jsonl` 已被 slime 读取，`Filtered 0 samples longer than max_length=32767`；上一轮的 prompt 数据集缺失问题已经越过。
- 训练侧已加载 `/root/models/Qwen3-30B-A3B_torch_dist`，14:20:25 出现 `Timer train_wait start`，表示 trainer 正在等待 rollout batch。
- 截至 14:24 UTC，`bringup_events.jsonl` 和 `rollout_0.pt` 仍未出现。当前仍是正常等待 rollout 的状态；成败点尚未到达转换器和训练 step。

## 2026-07-08 14:29 UTC rollout 已开始

- Ray job `raysubmit_JNeLtSnrAs48JEiP` 仍为 `RUNNING`。推理卡 GPU 4~7 约 75.5GB 显存，GPU 4/7 利用率约 92%/94%，GPU 5/6 约 36%，说明 rollout 侧正在工作。
- `/root/preflight_j4/artifacts/bringup_events.jsonl` 已出现，大小约 19.6KB。当前共有 14 条事件：10 条 `Status.COMPLETED`，4 条 `Status.ABORTED`。
- 4 条 abort 都是 `rh2_assemble_failed:SlimeBindingError`，细节为 `routing_rows_mismatch_backfill`，具体表现是 routing 元素数与 `(len(tokens)-1) * 48 * 8` 期望行数不一致。这与前面已知的少数轨迹路由行数不齐问题一致，治理层按 fail-closed 处理。
- 当前准入完成样本数为 10，尚不足 `global_batch_size=16`。`rollout_0.pt` 仍未出现，说明 slime 尚未把这一轮 rollout 封装成训练 batch，转换器与训练 step 尚未被验证。

## 2026-07-08 14:35 UTC rollout 接近 batch 阈值

- Ray job `raysubmit_JNeLtSnrAs48JEiP` 仍为 `RUNNING`。推理卡继续有明显利用率，说明仍在处理剩余样本。
- 当前事件数 27：15 条 `Status.COMPLETED`，12 条 `Status.ABORTED`。离 `global_batch_size=16` 只差 1 条完成样本，后续还有 5 条轨迹未收口，因此仍有机会形成一个训练 step。
- 所有 abort 仍为 `rh2_assemble_failed:SlimeBindingError`，主要细节为 `routing_rows_mismatch_backfill`。这是一个橙色风险：fail-closed 治理是正确的，但 routing tape 对长轨迹的行数对齐稳定性明显不足，若最后完成样本不足 16，会导致本轮训练 batch 饿死。
- `rollout_0.pt` 尚未出现，因此转换器、训练 loss、grad norm、checkpoint 判据仍未被验证。

## 2026-07-08 14:40 UTC 新轮失败结论

- Ray job `raysubmit_JNeLtSnrAs48JEiP` 最终 `FAILED`，8 张 GPU 显存归零。
- 本轮 32 条 rollout 全部收口，`rollout_0.pt` 已写出。样本统计为：15 条 completed、17 条 aborted；15 条 trainable 样本全部有 `rollout_routed_experts`、`rollout_top_p_token_ids` 和非零 `loss_mask`，17 条 aborted 样本 `remove_sample=True`。
- 失败直接原因是自定义转换器仍有 Ray remote wrapper 绑定问题：
  `rh2_convert.py` 第 63 行把 `_Proxy._post_process_rewards` 设为 `RolloutManager._post_process_rewards`，没有取 `.__wrapped__`。slime 默认 `_convert_samples_to_train_data` 内部调用 `self._post_process_rewards(samples)` 后进入 Ray actor 包装对象，报错：
  `AttributeError: 'ActorClass(RolloutManager)' object has no attribute 'custom_reward_post_process_func'`。
- 这验证了此前的潜在风险判断：下一轮必须先把 `_post_process_rewards` 改成 `RolloutManager._post_process_rewards.__wrapped__` 或等价的普通函数绑定，否则会稳定复现。
- 另一个独立风险：本轮只有 15 条 trainable 样本，低于 `global_batch_size=16`。即使修复转换器，本轮同分布重跑仍可能因为 routing mismatch 过多而形成不了一个完整训练 step；可以继续重跑赌随机性，也可以临时降到 `J4_GLOBAL_BATCH_SIZE=8` 做“转换器 + loss 消费 + checkpoint”诊断闭环，但这会偏离原 J4 严格判据。

## 2026-07-08 14:53-14:55 UTC 后续线程修复观察

- 隔壁线程已新增离线转换边界检查脚本 `rh2/experiments/p3_preflight/lib/j4_converter_offline.py`，并把它接入 `j4_full_step.sh` 后处理。该方向正确：可以用既有 `rollout_0.pt` 快速复现转换器问题，不必每次重新烧完整黑盒 rollout。
- 远端已对上一轮 `j4_fail_postprocess_bound_20260708T144347Z` 的 dump 跑 `j4_converter_offline_after_fix.json`，结果为 `PASS`：32 条输入样本、15 条 trainable 样本，输出 train_data 15 条，top-p replay 与 routing replay 均在场。这证明 postprocess/Ray wrapper 绑定问题已被离线关闭。
- 当前修复不是简单使用 `RolloutManager._post_process_rewards.__wrapped__`，而是在 `_Proxy` 中实现普通 `_post_process_rewards`，并继续调用 `RolloutManager._convert_samples_to_train_data.__wrapped__`。这同样能避开 Ray actor wrapper。
- 注意：离线转换检查证明的是“转换边界通过”，不是“训练 step 必然发生”。上一轮只有 15 条 trainable 样本，仍小于 `global_batch_size=16`；正式 J4 仍需单独证明准入样本数足够。
- 隔壁线程已启动一个 mini J4：`J4_ROLLOUT_BATCH_SIZE=4`、`J4_N_SAMPLES_PER_PROMPT=2`、`J4_GLOBAL_BATCH_SIZE=4`、`RH2_MAX_RESPONSE_LEN=512`、`SWE_AGENT_TIME_BUDGET_SEC=180`、`RH2_MAX_TURNS_PER_SID=6`。这是合理的低成本探针，目标应是验证新时间线、离线转换、loss/grad/checkpoint 链路，而不是替代严格 J4。

## 2026-07-08 15:02 UTC mini J4 中段状态

- mini J4 Ray job `raysubmit_rUcTBNtTYhx2FgmL` 仍为 `RUNNING`，训练侧处于 `train_wait` 后等待可训练 rollout，推理侧 GPU 4~7 有明显利用率。
- 新增的 `audit_timeline` / `rollout_timings` 已生效：当前 2 条事件都带有 `materialize_seconds`、`harness_run_seconds`、`capture_finish_backfill_seconds`、`grading_seconds`、`projection_seconds`、`eligibility_gate_seconds`、`delivery_seconds`、`cleanup_seconds`、`total_audit_seconds`。
- 当前 2 条事件均为 `Status.ABORTED`，失败阶段为 assemble，失败类型为 `SlimeBindingError`，具体 detail：
  `routing_rows_mismatch_backfill`，最后一轮 routing 元素数 `7336704` 不等于 `(len(tokens)-1) * 48 * 8` 的期望 `7302912`，对应 `rows=19018 x layers=48 x topk=8`。
- 这说明 mini 的低成本探针已经提前暴露了同一个核心问题：MoE routing tape 回填对齐仍不稳定。当前不是 Docker 物化、镜像缺失、无模型捕获或评分问题。
- 两条事件的时间分布几乎一致：`materialize_seconds≈3.3~3.5`、`harness_run_seconds≈216`、`cleanup_seconds≈0.4`、`total_audit_seconds≈225`。长尾主要来自黑盒 Claude Code harness 运行阶段，而不是环境物化或清理。因为 assemble 在 routing 回填处失败，评分、投影、gate 还没有被覆盖。
- 重要提醒：`j4_converter_offline.py` 与 `j4_assert.py` 当前都没有显式检查 `num_trainable_samples >= global_batch_size`。它们可以证明转换边界和字段形状，但不能单独证明训练 step 一定形成。严格 J4 或最终验收需要把这个条件加入 acceptance 判断，避免“总样本数足够但可训练样本不足”的假阳性。

## 2026-07-08 15:06 UTC mini J4 结束与新修复 run 启动

- `j4_mini_20260708T145432Z` 已结束。`j4_wall.txt` 记录 `j4_wall_seconds=484 rc=0`，但后置断言失败：没有 `rollout_0.pt`、没有 converter offline 产物、没有 checkpoint。
- `j4_assertions.json` 结果：
  - `1_rollout_samples=FAIL`：`num_samples=0`、`num_trainable_samples=0`、`expected_min=8`；
  - `2_startup_probes=PASS`：启动探针证明 renderer 与 tape 请求能力在场；
  - `3_tape_consumed_loss_finite=FAIL`：无可训练样本；
  - `4_grad_norm=UNKNOWN`：没有训练 step；
  - `5_memory_watermark_no_oom=PASS`：8 卡显存峰值留档，无 OOM；
  - `6_checkpoint_produced_then_discarded=FAIL`：没有 checkpoint。
- 关键判断：Ray/slime 命令自身 `rc=0` 不能作为训练闭环成功证据。治理层把样本全部剔除或没有形成训练 batch 时，slime 仍可能“正常退出”。因此 P3/J4 验收必须以后置断言和训练事实为准，尤其要显式要求可训练样本数达到 `global_batch_size` 且至少有一次 optimizer step / checkpoint 事实。
- 隔壁线程已启动新 run：`j4_mini_fix_20260708T150538Z`，Ray job `raysubmit_7Dt12tHgV1NCuUud`。远端代码显示 routing 回填修复为：当最后一轮 routing tape 行数多于 `len(sample.tokens)-1` 且能被 `layers*topk` 整除时，裁掉前缀多余行，并在 sample metadata 写入：
  `rh2_routing_backfill_trimmed_prefix_rows`、`rh2_routing_backfill_actual_rows`、`rh2_routing_backfill_expected_rows`。
- 对该修复的复核意见：方向可能合理，因为上一轮差值是 `88 * 48 * 8`，像“最后一轮 prompt 多出一段前缀上下文”。但这是语义性放宽，后续 evidence 必须证明裁掉的是前缀上下文而不是中间错位。最低要求是：
  1. 裁剪行数进入 artifact / sample metadata；
  2. 裁剪后样本通过 projection 与 EligibilityGate；
  3. converter offline 与训练 step 同时通过；
  4. 严格 J4 仍不能只凭 mini run 替代。

## 2026-07-08 15:13 UTC `j4_mini_fix` 前两条样本越过治理链路

- 新 run `j4_mini_fix_20260708T150538Z` 的 Ray job `raysubmit_7Dt12tHgV1NCuUud` 仍在 `RUNNING`。
- 当前事件文件已出现 2 条事件，均为完成状态，没有 `routing_rows_mismatch_backfill`，说明“裁前缀 routing 行”的修复至少让这 2 条样本越过 assemble。
- 这 2 条事件已经覆盖完整环境治理链路：`capture_finish_backfill_seconds`、`grading_seconds`、`projection_seconds`、`eligibility_gate_seconds`、`delivery_seconds` 都有值。分段计时：
  - `materialize_seconds≈2.8~2.9`；
  - `harness_run_seconds≈215~245`；
  - `capture_finish_backfill_seconds≈5.1~5.2`；
  - `grading_seconds≈6.9~7.2`；
  - `projection_seconds≈1.7~3.3`；
  - `eligibility_gate_seconds≈0.005`；
  - `cleanup_seconds≈0.7~0.9`；
  - `total_audit_seconds≈233~264`。
- 当前判断：修复已经把前一轮卡死的 assemble 问题推进到了后续阶段，且时间线足够定位长尾。长尾主要仍是黑盒 Claude Code harness 运行，评分与投影不是当前瓶颈。
- 仍未覆盖的关键点：尚无 `rollout_0.pt`，所以 converter offline、训练 loss、grad norm、checkpoint 尚未被证明。也尚未从 dump 中核对 `rh2_routing_backfill_trimmed_prefix_rows` 是否随样本落盘。

## 2026-07-08 15:17 UTC `j4_mini_fix` 训练侧失败：routing tape 形状错误

- `j4_mini_fix_20260708T150538Z` 最终 `FAILED`，8 张 GPU 显存归零。Ray job 直接错误：
  `AssertionError: torch.Size([7252224]), torch.Size([18887])`，栈在
  `/root/slime/slime/backends/megatron_utils/cp_utils.py:374`
  `prepare_routed_experts_for_routing_replay`。
- 环境治理侧已经明显进步：
  - `bringup_events.jsonl` 共有 8 条事件；
  - 8 条事件全部完成，没有 abort；
  - 16 条叶样本状态全为 `Status.COMPLETED`；
  - `rollout_0.pt` 已写出，包含 16 个样本；
  - 16 个样本全是 `remove_sample=False`，均带 `rollout_routed_experts`、`rollout_top_p_token_ids`、`rollout_top_p_token_offsets`、`loss_mask`、`tokens`。
- 但是训练侧失败说明当前 routing replay 还没有真正接通。原因不是“缺字段”，而是字段形状不符合 slime 训练侧约定。
- 对照 slime 源码：
  - `slime/utils/types.py` 的原生 `Sample._apply_meta_info` 会把 SGLang 返回的扁平 `routed_experts` reshape 成 `(expected_rows, args.num_layers, args.moe_router_topk)`；
  - `slime/backends/megatron_utils/cp_utils.py` 的 `_pad_routed_experts` 也按三维 `experts.shape == [rows, num_layers, topk]` 使用；
  - 当前 RepoHarness backfill 只是裁剪后把 `flat` 扁平列表写入 `sample.rollout_routed_experts`，因此 Megatron 看到的是一维长度 `rows * 48 * 8`，第一维不等于 `token_ids.shape[0]-1`。
- 新增的重要修复建议：
  1. `backfill_leaf_sample` 写入 `sample.rollout_routed_experts` 时，应按 slime 原生语义 reshape 为 `[rows][moe_num_layers][moe_router_topk]` 或等价 `torch.Tensor(shape=(rows, 48, 8))`，不能写扁平列表；
  2. `j4_converter_offline.py` 必须新增真实训练侧形状断言：每个可训练样本的 routing tensor/list 第一维等于 `len(tokens)-1`，后两维等于 `48, 8`；不能只检查元素总数与字段存在；
  3. 严格验收必须确认 `prepare_routed_experts_for_routing_replay` 这层不再报错，不能把 converter offline 的 PASS 当成 routing replay 已消费。
- 额外观察：这轮 `trim_count=8`，说明 16 个样本里有 8 个发生了前缀行裁剪。示例裁剪行数包括 `540`、`44`、`88`。这加强了“多余前缀上下文”假设，但也要求最终报告解释为什么裁剪前缀是语义安全的，或者至少在 P3 里标记为需要后续更严格 token 对齐审计的风险。
- 计时数据：8 条事件的 `harness_run_seconds` p50 约 `386.6` 秒，最大约 `395.1` 秒；`grading_seconds` p50 约 `14.1` 秒，最大约 `24.3` 秒；`projection_seconds` 最大约 `3.3` 秒。当前长尾瓶颈仍然是黑盒 harness，而非评分或投影。

## 2026-07-08 15:22 UTC routing 三维化修复的离线探针

- 隔壁线程已经意识到核心问题：`rollout_routed_experts` 不能只保存扁平向量，训练侧需要 `[tokens - 1, num_layers, moe_router_topk]` 三维形状。
- 远端代码已出现三处关键修复：
  1. `repoharness2/adapters/slime/generate.py` 中新增 `_shape_routing_experts(...)`，在 backfill 时把裁剪后的 routing tape reshape 为三维张量或嵌套列表；
  2. `rh2_convert.py` 中新增 `_normalize_routing_tape(...)`，在进入 `RolloutManager._convert_samples_to_train_data.__wrapped__` 前再次强制校验并规范成三维张量；
  3. `j4_converter_offline.py` 的检查从“元素总数存在”升级为逐样本检查 `shape == (len(tokens) - 1, 48, 8)`。
- 我用已经失败的旧 dump `/root/preflight_j4_mini_fix_20260708T150538Z/rollout_dumps/rollout_0.pt` 直接跑修复后的转换器，结果通过：
  - `dump_exists=True`，大小约 `242611641` 字节；
  - `convert_status PASS`；
  - `num_train_samples=16`；
  - `has_routed=True`，`len_routed=16`；
  - 前几个样本 shape 为 `(18886, 48, 8)`、`(19426, 48, 8)`、`(20132, 48, 8)`、`(18978, 48, 8)`、`(19022, 48, 8)`；
  - `mismatches=[]`。
- 结论：上一轮导致 Megatron 报 `torch.Size([7252224])` 的扁平形状问题，在离线转换层已经被关闭。还不能宣布 J4 成功，因为这只证明旧 dump 可以转换成训练侧形状；仍需要新一轮 Ray job 真实越过 `prepare_routed_experts_for_routing_replay`，产生有限 loss、grad norm 与 checkpoint 事实。
- 当前远端没有新的 Ray job 在运行，8 张 GPU 显存均为 `0 MiB`。最近的 Ray job 仍是旧的 `raysubmit_7Dt12tHgV1NCuUud`，状态为 `FAILED`，错误仍是修复前的扁平 routing tape 断言。
- 建议下一步：先用修复后的代码重跑 mini J4，而不是直接回到严格全量 J4。mini run 的验收条件应明确包括：
  1. `rollout_0.pt` 中每个可训练样本 routing shape 均为 `(len(tokens)-1, 48, 8)`；
  2. Megatron `prepare_routed_experts_for_routing_replay` 不再触发形状断言；
  3. 至少一个 optimizer step 产生有限 `pg_loss`、`grad_norm`；
  4. checkpoint 产生后按协议删除留证；
  5. `j4_assertions.json` 不能仅凭 Ray `rc=0` 通过，必须绑定训练事实。

## 2026-07-08 15:25 UTC 新 Ray job：回放旧 dump 验证训练侧

- 新 Ray job 已提交：`raysubmit_Z1zeSrFrg2sziBRb`，状态 `RUNNING`，输出目录为 `/root/preflight_j4_replay_shape_fix_20260708T152408Z`。
- 这轮不是重新跑完整黑盒 harness，而是使用上一轮已经生成的旧 dump：
  `--load-debug-rollout-data '/root/preflight_j4_mini_fix_20260708T150538Z/rollout_dumps/rollout_{rollout_id}.pt'`。
- 这个选择合理：它可以在不重新消耗 8 个 SWE-Bench 黑盒 rollout 的情况下，直接验证修复后的 `rh2_convert.py` 是否能把旧 dump 转成 Megatron routing replay 能消费的三维张量，并产生训练 loss / grad / checkpoint。
- 当前命令仍保留关键训练配置：`--use-rollout-routing-replay`、`--rollout-top-p 0.95`、`--global-batch-size 4`、`--custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data`。
- 注意：这轮不能替代“完整 J4 环境链路”验收，因为它跳过了 materialize / harness / grading / projection / gate 的重新执行；但它正好针对上一轮训练侧 shape 失败，是当前最省成本的正确诊断。

## 2026-07-08 15:28 UTC 回放任务已越过 routing replay 失败点

- `raysubmit_Z1zeSrFrg2sziBRb` 仍在 `RUNNING`，但已经越过上一轮失败点。
- 日志关键节点：
  - `Timer data_preprocess start/end` 正常结束，耗时约 `0.2s`；
  - 没有再次出现 `AssertionError: torch.Size([7252224]), torch.Size([18887])`；
  - `Timer ref_log_probs` 正常完成，耗时约 `25.6s`；
  - `Timer log_probs` 正常完成，耗时约 `19.0s`；
  - 已打印 rollout 训练统计：`rollout/raw_reward=0.1875`、`rollout/advantages≈0.0625`、`rollout/log_probs≈-0.2046`、`rollout/ref_log_probs≈-0.1074`；
  - 当前进入 `Timer actor_train start`，正在跑 actor train microbatch。
- 结论：`rollout_routed_experts` 三维化修复已经通过 Megatron `prepare_routed_experts_for_routing_replay` 这一层的真实消费验证。接下来还需要继续确认：
  1. `actor_train` 完成；
  2. 出现有限 `pg_loss` / `grad_norm` 等训练指标；
  3. checkpoint 产生；
  4. checkpoint 按协议删除留证；
  5. `j4_assertions.json` 对这轮 replay 不能被误记为完整环境 J4，只能作为“训练侧 replay shape 修复”的证据。

## 2026-07-08 15:31 UTC 回放任务已产生训练指标和 checkpoint

- `raysubmit_Z1zeSrFrg2sziBRb` 仍在 `RUNNING`，但训练侧已经完成关键部分：
  - `actor_train` 8/8 microbatch 完成；
  - `Timer actor_train end`，耗时约 `155.0s`；
  - `Timer train end`，耗时约 `200.8s`。
- 训练指标已经出现且为有限值：
  - step 0：`train/loss=-0.0624999925`、`train/pg_loss=-0.0624999925`、`train/grad_norm≈2.2482`、`train/global_batch_size=4`；
  - step 1：`train/loss≈-0.06226358`、`train/pg_loss≈-0.06226358`、`train/ppo_kl≈0.000846`、`train/grad_norm≈1.1881`、`train/global_batch_size=4`。
- checkpoint 已经开始保存到 `/root/preflight_j4_replay_shape_fix_20260708T152408Z/ckpt`，当前看到：
  - `ckpt/iter_0000000/__1_0.distcp`
  - `ckpt/iter_0000000/__2_0.distcp`
  - `ckpt/iter_0000000/__3_0.distcp`
  - `ckpt/iter_0000000/common.pt`
- 结论：训练侧 replay shape 问题已经被实证关闭。它证明了旧 dump 经修复后的 converter 能被 Megatron routing replay 消费，并完成至少两个 optimizer step。
- 仍需等待 Ray job 最终结束，并检查：
  1. 是否保存完整 checkpoint；
  2. 是否按协议删除 checkpoint 或写明保留原因；
  3. 这轮 evidence 是否明确标注为 debug replay，而不是完整环境 J4；
  4. 后续仍需一次完整 mini J4 或严格 J4 覆盖 materialize / harness / grading / projection / gate 重新执行。

## 2026-07-08 15:33 UTC 新严重问题：debug checkpoint 写满根盘

- 远端宿主机 `df -h` 显示根分区 `/dev/vda1` 已 `247G/247G`，`Use%=100%`，而挂载盘 `/mnt/p3` 还有约 `664G` 可用。
- `docker exec` 已开始失败，错误为：
  `OCI runtime exec failed: write /tmp/runc-process...: no space left on device`。
- `sudo du -xhd1 /var/lib/docker` 显示 Docker overlay 占用约 `231G`，主要位于 `/var/lib/docker/overlay2`。
- 大文件定位显示本轮 debug replay 的 checkpoint 写进了容器 root overlay，而不是写进 `/mnt/p3`：
  `/var/lib/docker/overlay2/.../diff/root/preflight_j4_replay_shape_fix_20260708T152408Z/ckpt/iter_0000000/`
  下存在多个巨大 `.distcp` 文件：
  - `__0_1.distcp` 约 `8.3GB`
  - `__0_0.distcp` 约 `9.3GB`
  - `__2_1.distcp` 约 `11.6GB`
  - `__1_1.distcp` 约 `12.1GB`
  - `__1_0.distcp` 约 `12.9GB`
  - `__2_0.distcp` 约 `26.0GB`
  - `__3_1.distcp` 约 `50.5GB`
  - `__3_0.distcp` 约 `51.7GB`
- 结论：训练侧 replay 已经成功产出 checkpoint，但保存路径错误导致根盘被撑满。这是后处理 / 路径规划问题，不是训练 replay shape 修复失败。
- 建议立即处理：
  1. 停止继续提交新的 Ray job；
  2. 记录本轮 checkpoint 已产生的事实与文件清单；
  3. 删除本轮 debug checkpoint，释放根盘；
  4. 后续所有 `--save`、`--load`、`--save-debug-rollout-data`、evidence 输出都必须写入挂载盘 `/mnt/p3` 或容器内明确绑定到 `/mnt/p3` 的路径；
  5. `j4_assert.py` 应增加根盘保护：运行前检查根盘可用空间，checkpoint 保存路径禁止落入容器 root overlay。

## 2026-07-08 15:35 UTC 根盘仍满，判定为阻塞态

- 等待一轮后重新检查，根分区仍为 `247G/247G`、`Use%=100%`，没有自行释放。
- GPU 2 和 GPU 3 仍显示高利用率，说明训练 / 保存相关进程没有完全退出。
- 宿主机仍有多个 `rh2-rollout-*` 容器运行：
  - `rh2-rollout-0f8fb070-ed46-4dfc-91d4--6419ddc4`
  - `rh2-rollout-84c46ae6-5229-4ef3-9ec7--8eada032`
  - `rh2-rollout-d78b3488-061b-49b7-b599--3ed1fb06`
  - `rh2-rollout-e1762615-35bf-43e0-b6f4--e4ebdfdf`
  - `rh2-rollout-2b181b20-5631-4e0c-a475--a3ebe0c0`
  - `rh2-rollout-4959cf9c-583f-4d8f-bf96--e33ec7b5`
  - `rh2-p3`
- 当前状态已不适合继续提交任务。需要先清理根盘。建议执行方优先采用“进程内正常清理”，如果 `docker exec` 继续因为 `no space left on device` 失败，再考虑宿主机侧清理：
  1. 停止当前 Ray job / 训练进程；
  2. 删除 `/root/preflight_j4_replay_shape_fix_20260708T152408Z/ckpt`；
  3. 删除已经不再需要的 `rh2-rollout-*` 容器；
  4. 重新检查 `df -h / /mnt/p3`；
  5. 修改脚本，使下一次 `--save` 指向 `/mnt/p3/...`。

## 2026-07-08 15:40 UTC 清理线程执行中，但空间尚未释放

- 隔壁线程已经开始清理，采取的动作包括：
  1. 宿主机检查 `df`、Docker 容器、GPU 进程；
  2. 尝试 `docker rm -f rh2-rollout-*`；
  3. 尝试进入 `rh2-p3` 停止 `train_async.py` / `MegatronTrainRayActor` / Ray；
  4. 宿主侧尝试 kill GPU 上的 `MegatronTrainRayActor.save_model` 相关 PID；
  5. 定位 `rh2-p3` 容器可写层约 `189GB`，确认最大 overlay 基本就是本轮 replay checkpoint。
- 我从宿主机只读复查后，当前状态仍未恢复：
  - `df -h / /mnt/p3`：根分区仍为 `247G/247G`、`Use%=100%`；`/mnt/p3` 仍有约 `664G` 可用；
  - GPU 状态：GPU 0/1 仍保留约 `85GB/87GB` 显存但利用率为 0，GPU 2/3 显存降到约 `3MiB` 但利用率仍显示 100；
  - `docker ps` 中 6 个 `rh2-rollout-*` 容器仍处于 `Up 42 minutes`，`rh2-p3` 仍在；
  - 进程列表中大量 Ray 相关进程处于 `defunct`，说明父进程尚未完全回收。
- 这说明执行线程的第一轮清理还没有真正释放 Docker overlay 空间。根盘满导致 `docker exec` 不可靠，后续清理应尽量走宿主机路径或先重启/回收 Docker/Ray 父进程。
- 我中止了一条长时间运行的只读 `du -xhd1 /var/lib/docker/overlay2` 扫描，避免在根盘满时继续给 overlay 增加 I/O 压力。
- 当前建议保持：
  1. 暂停任何新的 J4 / Ray job；
  2. 先完成本轮 checkpoint 删除和容器回收；
  3. 根盘至少恢复到有数十 GB 可用后，再执行后处理断言；
  4. 下一轮 debug replay 必须把 `--save` 指向 `/mnt/p3/...`，并且最好临时关闭或立即清理 checkpoint 保存。

## 2026-07-08 15:42 UTC 清理仍在进行，`rm -rf` 正在删除 overlay checkpoint

- 轻量复查显示根盘仍为 `247G/247G`、`Use%=100%`，尚未释放。
- GPU 状态仍异常：GPU 0/1 约 `85GB/87GB` 显存但利用率 0，GPU 2/3 仅约 `3MiB` 显存但利用率 100。这个状态不像正常训练，更像进程/驱动资源尚未完全回收。
- Docker 容器仍未回收，6 个 `rh2-rollout-*` 容器仍处于 `Up 44 minutes`，`rh2-p3` 仍在。
- 关键进程状态：
  - `docker rm -f rh2-rollout-*` 仍在运行；
  - 宿主机侧已经定位 `rh2-p3` 的 `UpperDir`，并启动：
    `sudo rm -rf .../diff/root/preflight_j4_replay_shape_fix_20260708T152408Z/ckpt .../diff/tmp/ray/session_2026-07-08_15-24-37_418231_478106`；
  - 对应 `rm` 进程处于 `D` 状态，说明正在等待磁盘 I/O，不是命令没有启动。
- 当前建议：继续等待该 `rm -rf` 完成，不要同时发起 Docker 重启或更多大规模 `du/find` 扫描，避免在满盘和 overlay 删除过程中增加 I/O 压力。下一次只做轻量 `df`、GPU、进程状态复查。

## 2026-07-08 15:45 UTC `rm` 可能卡在 overlay unlink，GPU 存在驱动残留

- 进一步只读诊断显示：
  - `rm` 进程已经运行约 `6m09s`，状态仍为 `D`；
  - `wchan` 显示为 `-`，但 `/proc/1196457/stack` 显示调用栈停在：
    `vfs_unlink -> do_unlinkat -> __x64_sys_unlinkat`；
  - `/proc/1196457/io` 几乎没有 I/O 进展：`read_bytes=0`、`write_bytes=0`、`cancelled_write_bytes=0`。
- 这比“正常删除大 checkpoint”更像 overlay unlink 在满盘/容器层状态下被卡住。继续等待仍可能成功，但已经不是健康状态。
- `nvidia-smi --query-compute-apps` 显示两个残留 GPU PID：
  - `1169841, [Not Found], 85250 MiB`
  - `1171179, [Not Found], 87282 MiB`
  但宿主 `ps` 已找不到对应正常进程，只能看到大量 `python3` / Ray `defunct` 进程。这说明 GPU 驱动侧还有残留上下文没有被容器父进程回收。
- 如果再等待数分钟仍不释放，建议升级恢复手段：
  1. 优先由执行线程统一停止 Docker / containerd 或重启宿主机，避免两个线程同时操作；
  2. 重启前确认 evidence 已经在 `/root/preflight_evidence/j4_replay_shape_fix_20260708T152408Z` 或可恢复位置；
  3. 重启后首先删除 overlay checkpoint 或直接删除重建 `rh2-p3` 容器；
  4. 之后所有路径迁移到 `/mnt/p3`，再继续 J4。

## 2026-07-08 15:50 UTC checkpoint 目录已删除，正在等待 `sync` / overlay 刷新

- 新一轮检查显示：
  - `UP/root/preflight_j4_replay_shape_fix_20260708T152408Z/ckpt` 已经 `ckpt_missing`；
  - `UP/tmp/ray/session_2026-07-08_15-24-37_418231_478106` 已经 `ray_session_missing`；
  - 清理 shell 的子进程变为 `sync`，说明 `rm -rf` 本身已经结束，正在等待文件系统同步。
- `lsof +L1` 没有看到根盘上巨大的已删除 checkpoint 被持有；只看到一批 `/dev/shm/nccl-* (deleted)` 小文件，主要由 `ray::Mega` 进程持有，不是根盘空间主因。
- 当前判断：空间释放路径已经进入收尾阶段。应继续等待 `sync` 完成后再查 `df`。如果 `sync` 完成后根盘仍为 100%，再考虑 Docker/containerd 层面的缓存或 overlay 状态异常。

## 2026-07-08 15:52 UTC `sync` 仍卡住，根盘未释放

- `sync` 子进程 `1205437` 已运行约 `3m36s`，状态为 `D`，等待点为 `wb_wait_for_completion`。
- 根分区仍为 `247G/247G`、`Use%=100%`，没有因为 checkpoint 目录删除而释放。
- GPU 残留状态仍存在：GPU 0/1 占用约 `85GB/87GB` 但利用率 0，GPU 2/3 几乎无显存但利用率 100。
- 6 个 `rh2-rollout-*` 容器仍然 `Up 51 minutes`，`docker rm -f` 仍在等待。
- 判断更新：这不再像普通的大文件删除等待，而是 Docker overlay / 文件系统写回 / 容器父进程回收异常。继续等待仍可能恢复，但如果再持续不变，应升级到 Docker/containerd 服务重启或整机重启。由于当前根盘已满且 GPU 残留，继续实验没有意义。

## 2026-07-08 15:56 UTC GPU 显存释放，但 Docker / 根盘仍未恢复

- 两分钟后复查：
  - GPU 显存已经全部归零，说明训练侧 GPU 上下文基本释放；
  - GPU 2/3 仍显示 `utilization.gpu=100`，但显存为 `0MiB`，可能是驱动状态尚未完全刷新；
  - 根分区仍是 `247G/247G`、`Use%=100%`；
  - `sync` 进程 `1205437` 已脱离原父进程，`PPID=1`，仍为 `D` 状态，等待 `wb_wait_for_completion`，已持续约 `6m24s`；
  - `docker ps` 调用没有及时返回，我已中止该只读命令，避免监控命令继续挂住。
- 当前判断：GPU 成本风险下降了，但机器的 Docker / 根盘状态仍然不可用于继续实验。在线清理路径没有完成恢复。
- 建议升级为恢复流程：
  1. 让执行线程停止继续尝试 `docker exec` / `docker rm`；
  2. 如果宿主机允许，优先尝试重启 Docker / containerd 服务；
  3. 如果服务重启也卡住或失败，直接重启机器；
  4. 重启后先验证 `/` 可用空间、Docker 容器状态、`/mnt/p3` 挂载，再恢复 evidence；
  5. 后续脚本必须把 checkpoint 和 debug output 写到 `/mnt/p3`，不能再写容器根目录。

## 2026-07-08 15:58 UTC SSH 连接被关闭 / 重置，疑似进入重启恢复

- 最后一轮轻量复查时，SSH 已无法正常建立：
  - 一条连接返回 `Connection closed by 204.12.168.119 port 22`；
  - 另一条连接返回 `kex_exchange_identification: read: Connection reset by peer`。
- 这通常意味着执行线程触发了 Docker/containerd 服务重启、SSH 服务受系统恢复影响，或整机正在重启。
- 下一步恢复后应首先检查：
  1. `df -h / /mnt/p3`，确认根盘空间已经释放；
  2. `nvidia-smi`，确认 GPU 没有残留上下文；
  3. `docker ps -a`，确认 `rh2-p3` 和 `rh2-rollout-*` 的状态；
  4. `/mnt/p3` 是否仍正常挂载；
  5. replay 成功 evidence 是否仍保存在 `/root/preflight_evidence/j4_replay_shape_fix_20260708T152408Z` 或已同步到 `/mnt/p3`。

## 2026-07-08 16:01 UTC 机器恢复后体检通过

- 机器已重新可 SSH，`uptime` 显示刚启动约 `1 min`。
- 根盘已恢复：
  - `/dev/vda1`：`247G` 总量，已用 `73G`，可用 `175G`，使用率 `30%`；
  - `/mnt/p3`：`1.5T` 总量，已用 `837G`，可用 `664G`，使用率 `56%`；
  - `/mnt/p3` 挂载正常，来源 `rh2`，类型 `virtiofs`。
- GPU 已完全释放：8 张 GPU 显存均为 `0MiB`，利用率均为 `0%`。
- Docker 状态：
  - 临时 `rh2-rollout-*` 容器已不在；
  - 只剩 `rh2-p3`，状态为 `Exited (255)`，大小约 `6.65GB`，不再是 170GB 级别 overlay；
  - `docker system df` 显示容器可回收约 `6.651GB`，镜像总量约 `52.11GB`。
- evidence 已在挂载盘：
  - `/mnt/p3/preflight_evidence/j4_mini_fix_20260708T150538Z`
  - `/mnt/p3/preflight_evidence/j4_replay_shape_fix_20260708T152408Z`
  - `/mnt/p3/rh2_recovered_evidence_20260708/j4_mini_fix_20260708T150538Z`
  - `/mnt/p3/rh2_recovered_evidence_20260708/j4_replay_shape_fix_20260708T152408Z`
- `/root/preflight_evidence` 现在是指向 `/mnt/p3/preflight_evidence` 的软链接，这能降低后续 evidence 再次写爆根盘的风险。
- 当前判断：机器恢复成功，GPU 和根盘成本风险解除。继续实验前仍需确认新的容器启动参数会把 checkpoint / debug output 写到 `/mnt/p3`，尤其是 `--save`、`--load`、`--save-debug-rollout-data`。

## 2026-07-08 16:03 UTC replay 成功 evidence 已确认保留

- 复查 `/mnt/p3/preflight_evidence/j4_replay_shape_fix_20260708T152408Z/j4`，关键文件仍在：
  - `j4_replay_args.txt`，约 `2.8KB`；
  - `j4_replay_train.log`，约 `86KB`；
  - `dmon_all.csv`，约 `547KB`。
- `j4_replay_train.log` 中保留了核心训练证据：
  - rollout 指标：`rollout/raw_reward=0.1875`、`rollout/advantages≈0.0625`；
  - step 0：`train/pg_loss=-0.0624999925`、`train/grad_norm≈2.2482`、`train/global_batch_size=4`；
  - step 1：`train/pg_loss≈-0.06226358`、`train/ppo_kl≈0.000846`、`train/grad_norm≈1.1881`、`train/global_batch_size=4`；
  - `Timer train end (elapsed: 200.8s)`；
  - `saving checkpoint at iteration 0 to /root/preflight_j4_replay_shape_fix_20260708T152408Z/ckpt`。
- 这证明：虽然 checkpoint 本体已被删除用于释放根盘，但“训练侧 replay 成功、产生有限 loss/grad/checkpoint 保存动作”的证据没有丢。
- 当前仍无新 J4 run：`rh2-p3` 处于 `Exited (255)`，没有新的 evidence 目录。

## 2026-07-08 16:05 UTC 恢复后持续空闲，无新任务

- 再观察约两分钟后复查：
  - 根分区仍稳定在 `73G/247G`，可用约 `175G`，使用率 `30%`；
  - `/mnt/p3` 仍为 `837G/1.5T`，可用约 `664G`；
  - 8 张 GPU 显存和利用率均为 0；
  - `rh2-p3` 仍为 `Exited (255)`，没有新的容器启动；
  - 宿主机进程中没有 `train_async`、Ray、SGLang、J4 相关进程；
  - `/mnt/p3/preflight_evidence` 没有出现新的 J4 run，最新仍是 `j4_replay_shape_fix_20260708T152408Z`。
- 当前判断：机器已经从满盘 / GPU 残留故障中恢复，处于安全空闲状态。后续等待执行线程重启容器并提交修正版 run。

## 2026-07-08 16:14-16:15 UTC 正式 J4 已启动，路径保护生效

- 执行线程在正式 J4 前先修复路径风险：
  - `common.sh` 改为外接卷优先；
  - `j4_full_step.sh`、`j4b_topo_compare.sh`、`j4c_fully_async_smoke.sh`、`j5_weight_sync.sh` 的默认运行目录切到 `P3_RUN_ROOT`；
  - 本地检查包括 shell 语法、`j4_full_step.sh --dry-run`、`tests/check_p3_scripts.py` 40 项、slime adapter / projection 相关 66 项，均通过。
- 正式 J4 run 已启动：
  - evidence 目录：`/mnt/p3/preflight_evidence/j4_formal_20260708T160749Z`；
  - Ray job：`raysubmit_bLBqr6QdR1UtqLqJ`，状态 `RUNNING`；
  - 关键参数：`rollout-batch-size=8`、`n-samples-per-prompt=4`、`global-batch-size=32`、`rollout-max-response-len=2048`、`SWE_AGENT_TIME_BUDGET_SEC=600`、`RH2_MAX_TURNS_PER_SID=25`；
  - `--use-rollout-routing-replay`、`--rollout-top-p=0.95` 均在场。
- 路径核验：
  - `--load` / `--save`：`/root/bringup/j4_formal_20260708T160749Z/ckpt`；
  - `--save-debug-rollout-data`：`/root/bringup/j4_formal_20260708T160749Z/rollout_dumps/rollout_{rollout_id}.pt`；
  - prompt 数据：`/root/bringup/j4_formal_20260708T160749Z/swe_bringup_8.jsonl`；
  - evidence：`/root/preflight_evidence/j4_formal_20260708T160749Z`。
- 容器 mount 已确认：
  - `/root/bringup` -> `/mnt/p3/bringup`；
  - `/root/preflight_evidence` -> `/mnt/p3/preflight_evidence`；
  - `/root/models` -> `/mnt/p3/models`；
  - 因此本轮 checkpoint、debug dump、evidence 均应落在外接卷，而不是容器根盘。
- 资源状态：
  - 根盘 `/`：约 `91G/247G`，可用 `157G`，使用率 `37%`；
  - `/mnt/p3`：约 `837G/1.5T`，可用 `664G`；
  - GPU 0-3 约 `48GB`，GPU 4-7 约 `75GB`，符合训练侧 + SGLang rollout 资源形态；
  - `rh2-p3` 正常运行，约 32 个 `rh2-rollout-*` 沙箱容器已启动。
- 当前日志显示处于权重同步阶段，`update_weights` 正在推进并收到 SGLang `update_weights_from_distributed` 响应。尚未看到正式 J4 的 `rollout_0.pt` 或正式 run 的 `bringup_events.jsonl` 落盘。

## 2026-07-08 16:17 UTC 正式 J4 进入真实 rollout generation

- 资源状态稳定：
  - 根盘 `/`：约 `93G/247G`，可用 `155G`，使用率 `38%`，没有再次快速写爆；
  - `/mnt/p3`：约 `837G/1.5T`，可用 `664G`；
  - Docker 中仍有 32 个 `rh2-rollout-*` 沙箱容器，均运行约 4 分钟，大小约 `337MB` 到 `692MB`；
  - `rh2-p3` 正常运行。
- 训练 / 推理状态：
  - `update_weights` 已完成，日志显示 `Timer update_weights end (elapsed: 11.1s)`；
  - `Rollout generation: 0/32` 已出现，正式 rollout 阶段开始；
  - SGLang 日志显示真实 `Prefill` / `Decode`，GPU 4-7 有明显利用率；
  - 当前 `token usage` 仍较低，约 `0.02` 到 `0.06`，没有显存接近上限迹象。
- 文件状态：
  - `/mnt/p3/preflight_evidence/j4_formal_20260708T160749Z/j4/j4_train.log` 和 `driver.log` 正在增长；
  - `/mnt/p3/bringup/j4_formal_20260708T160749Z/artifacts/startup_evidence.json` 已写出；
  - 还没有正式 run 的 `bringup_events.jsonl` 或 `rollout_0.pt`，这符合黑盒 harness 样本尚未完成时的状态。
- 当前判断：正式 J4 已经通过初始化与权重同步，正在真实黑盒 rollout。下一轮重点看是否开始有完成/失败事件落盘，以及是否出现路径、评分、projection 或 routing backfill 类问题。

## 2026-07-08 16:20 UTC 首批正式 J4 事件落盘

- 当前资源仍稳定：
  - 根盘 `/`：约 `90G/247G`，可用 `158G`，使用率 `37%`；
  - `/mnt/p3`：约 `838G/1.5T`，可用 `663G`；
  - `rh2-rollout-*` 容器从 32 个降到 26 个，说明部分 rollout 已结束并清理；
  - GPU 4-7 有明显 SGLang 推理利用率，GPU 0-3 保持训练侧权重驻留。
- `/mnt/p3/bringup/j4_formal_20260708T160749Z/artifacts/bringup_events.jsonl` 已出现，轻量汇总：
  - 事件数：`7`；
  - 样本数：`8`；
  - 状态：全部 `Status.COMPLETED`；
  - `remove_sample=false`：`8/8`；
  - abort：`0`；
  - eligibility：`offline_or_sft_candidate` 为 `7/7`；
  - grading failure category：全部 `tests_failed`；
  - reward：当前均为 `0.0`。
- 覆盖任务：
  - `sympy__sympy-15349`：4 条事件；
  - `psf__requests-2931`：1 条事件；
  - `sympy__sympy-14711`：1 条事件；
  - `astropy__astropy-14995`：1 条事件。
- 计时分布：
  - `wall_seconds`：最小约 `340.9`，中位数约 `370.77`，最大约 `432.45`；
  - `materialize_seconds`：中位数约 `7.779`；
  - `harness_run_seconds`：中位数约 `345.118`；
  - `capture_finish_backfill_seconds`：中位数约 `0.459`；
  - `grading_seconds`：中位数约 `15.95`；
  - `projection_seconds`：中位数约 `1.385`；
  - `eligibility_gate_seconds`：中位数约 `0.003`。
- 观察：
  - 当前已经完整覆盖 materialize / harness / capture / backfill / grading / projection / gate / delivery；
  - 没有看到 routing backfill mismatch、converter、评分 infra failure 或 cleanup failure；
  - 日志中出现多次 `Model attempted to call undefined function: deep-research`，这是模型行为和工具约束质量问题，当前没有导致系统失败，但应在 P3 报告中记录。
- 当前仍未看到 `rollout_0.pt`，说明样本还未达到训练侧组包 / dump 阶段或仍在 rollout generation 中。

## 2026-07-08 16:22 UTC 首批长上下文溢出样本被 fail-closed 拒收

- 资源状态继续健康：
  - 根盘 `/`：约 `87G/247G`，使用率 `36%`；
  - `/mnt/p3`：约 `838G/1.5T`，使用率 `56%`；
  - `rh2-p3` 正常运行，Ray job `raysubmit_bLBqr6QdR1UtqLqJ` 仍为 `RUNNING`；
  - `rh2-rollout-*` 容器数降到 `21`，说明正式 J4 仍在逐步收敛样本。
- 事件流轻量汇总：
  - 事件数：`11`；
  - 样本数：`13`；
  - `Status.COMPLETED`：`11`；
  - `Status.ABORTED`：`2`；
  - `remove_sample=true`：`2`。
- 两个拒收样本的共同原因：
  - `abort_reason=rh2_assemble_failed:SlimeBindingError`；
  - `failure_records.stage=assemble`；
  - 详细错误为 `routing_rows_mismatch_backfill`，即最后一轮 routing 元素数小于 `len(tokens)-1` 对应的期望行数。
- 结合日志看，两个拒收样本之前均出现过 `prompt exceeds max_context_tokens`：
  - session `5fc9f73d-afd3-4483-8203-a9e4b26636cf`：`33526 >= 32768`；
  - session `712134eb-b435-464a-8335-9080703efafd`：多次约 `36302` 到 `37470 >= 32768`。
- 当前判断：
  - 这不是磁盘、Docker、SGLang 服务或训练侧崩溃；
  - fail-closed 行为是正确的，两个样本被 `remove_sample=true` 拒收，没有进入训练；
  - 但错误归因还不够理想：长上下文溢出应该在更早阶段被归为明确的上下文预算 / 截断策略问题，而不是等到 assemble 阶段表现为 `SlimeBindingError`。
- 需要在 P3 结论中记录：
  - 600 秒、25 轮、32K 上下文在黑盒 Claude Code 样式 harness 下已经能触发上下文溢出；
  - 后续正式训练需要决定是降低 `RH2_MAX_TURNS_PER_SID`、开启 compaction、增大上下文窗口，还是在 capture 阶段对超过预算的样本直接拒收并给出专门的 failure category。

## 2026-07-08 16:24-16:26 UTC 正式 J4 出现正向 reward，同时长上下文拒收扩大

- 资源状态仍稳定：
  - 根盘 `/`：约 `79G/247G`，使用率 `32%`；
  - `/mnt/p3`：约 `839G/1.5T`，使用率 `56%`；
  - Ray job 仍为 `RUNNING`；
  - `rh2-rollout-*` 容器数降到 `9`，说明第一轮 32 个 rollout 已接近结束。
- 事件流更新：
  - 事件数：`23`；
  - 样本数：`25`；
  - `Status.COMPLETED`：`18`；
  - `Status.ABORTED`：`7`；
  - `remove_sample=true`：`7`，全部为 `rh2_assemble_failed:SlimeBindingError`；
  - 完成样本均为 `offline_or_sft_candidate`，原因是 S1 默认上限 `s1_default_ceiling_offline`。
- reward 分布：
  - `reward=1.0`：`6`；
  - `reward=0.0`：`19`；
  - 其中 `django__django-11099` 四条全 resolved，`django__django-16139` 已出现正负混合。
- 任务覆盖与结果：
  - `sympy__sympy-15349`：4 条，均 `0.0`；
  - `sympy__sympy-14711`：4 条，均 `0.0`；
  - `astropy__astropy-14995`：4 条，均 `0.0`；
  - `django__django-11099`：4 条，均 `1.0`；
  - `django__django-16139`：3 条，`[1.0, 0.0, 1.0]`；
  - `psf__requests-1142`：2 条，均 `0.0`；
  - `psf__requests-2931`：3 条，均 `0.0`，其中另有上下文溢出拒收。
- 计时分布：
  - `wall_seconds`：最小约 `340.9`，中位数约 `635.32`，最大约 `765.51`；
  - 这说明长尾主要来自黑盒 harness 运行时间，而不是评分、projection 或 gate。
- 当前尚未看到：
  - `rollout_0.pt`；
  - `data_preprocess`；
  - `ref_log_probs`；
  - `log_probs`；
  - `actor_train`；
  - `pg_loss` / `grad_norm`。
- 当前判断：
  - 正式 J4 已经证明真实黑盒 rollout、评分、projection、eligibility、group repair signal 都在跑；
  - 但它还没有进入训练侧消费阶段，后续必须继续确认是否能凑够有效样本并产出 `rollout_0.pt`；
  - 长上下文溢出拒收已经从偶发变成显著现象，正式训练前需要把它从 assemble 错误前移为专门的上下文预算判定。

## 2026-07-08 16:28-16:30 UTC 第一轮 rollout 进入最后 3 个黑盒长尾

- 事件流暂时停在：
  - 事件数：`29`；
  - 样本数：`39`；
  - `Status.COMPLETED`：`28`；
  - `Status.ABORTED`：`11`；
  - 有效样本仍未达到 `global_batch_size=32`；
  - reward 分布仍为 `reward=1.0` 共 `6`、`reward=0.0` 共 `33`。
- 剩余容器：
  - `rh2-rollout-f5e12c0c-...`：`django__django-16139`；
  - `rh2-rollout-f4b2450d-...`：`django__django-11133`；
  - `rh2-rollout-555a2ea3-...`：`django__django-11133`。
- 容器内状态：
  - 三个容器都不是僵尸，仍在运行 `/usr/local/bin/claude -p ...`；
  - Claude 进程 elapsed 约 `8m50s`，接近但尚未超过 `SWE_AGENT_TIME_BUDGET_SEC=600`；
  - 容器日志没有明显错误输出。
- 当前判断：
  - 长尾主要是黑盒 harness 自身运行时间；
  - 这 3 个样本的结果会决定第一轮是否凑够至少 32 个有效样本并进入训练侧；
  - 如果这 3 个也被拒收或超时，正式 J4 可能只验证 rollout/gate/evidence，而不能验证训练 step。

## 2026-07-08 16:31-16:33 UTC 正式 J4 生成 dump，但训练调度因有效 rollout 数不足失败

- 第一轮正式 J4 已收口：
  - `rh2-rollout-*` 容器数降为 `0`；
  - GPU 显存全部释放为 `0 MiB`；
  - 根盘 `/`：约 `73G/247G`，使用率 `30%`；
  - `/mnt/p3`：约 `842G/1.5T`，使用率 `57%`；
  - Ray job `raysubmit_bLBqr6QdR1UtqLqJ` 状态为 `FAILED`。
- 事件流最终口径：
  - 事件数：`32`；
  - 样本数：`44`；
  - `Status.COMPLETED`：`31`；
  - `Status.ABORTED`：`13`；
  - `remove_sample=true`：`13`，全部为 `rh2_assemble_failed:SlimeBindingError`；
  - reward 分布：`reward=1.0` 共 `9`，`reward=0.0` 共 `35`。
- 文件产物：
  - `rollout_0.pt` 已生成：`/mnt/p3/bringup/j4_formal_20260708T160749Z/rollout_dumps/rollout_0.pt`，大小约 `976,520,976` 字节；
  - `j4_converter_offline.json` 已生成，状态为 `PASS`；
  - `j4_assertions.json` 已生成。
- converter 口径：
  - `num_input_samples=44`；
  - `num_trainable_samples=31`；
  - `num_removed_samples=13`；
  - `top_p_replay_present=true`；
  - `routing_replay_present=true`；
  - `routing_first_shape=[20321, 48, 8]`。
- slime 真实失败点：
  - `slime/ray/rollout.py` 调用 `build_dp_schedule` 时触发断言；
  - 错误为 `AssertionError: num_rollouts (19) < global_batch_size (32); need at least one rollout per step.`。
- `rollout_0.pt` 结构检查解释了 `31` 和 `19` 的差异：
  - dump 内部共有 `44` 条 sample；
  - `remove_sample=False` 且 `status=completed` 的 sample 有 `31` 条；
  - 但这些样本只对应 `19` 个非空 `rollout_id`；
  - 某些 `rollout_id` 产生了多个 sample，例如 `rollout_id=22` 有 `8` 条，`rollout_id=9` 有 `3` 条；
  - slime 的数据并行调度使用的是有效 rollout 数，而不是分叉后的 sample 数。
- 本轮暴露出两个工程问题：
  - `j4_assertions.json` 中 `num_trainable_samples=31`、`expected_min=32`，但 `1_rollout_samples.status` 仍为 `PASS`，这个检查脚本判据偏松，应改成硬失败；
  - J4 协议当前把“分叉 sample 数”当作足够训练的近似指标，但 slime 的实际调度口径是“有效 rollout 数”，两者不能混用。
- 建议给执行线程的补测方向：
  - 不要立刻重跑完整 32 个黑盒 rollout；
  - 优先用已经生成的 `rollout_0.pt` 做离线 replay，把 `global_batch_size` 降到不超过有效 rollout 数的安全值，例如 `16`，验证 `data_preprocess`、`ref_log_probs`、`log_probs`、`actor_train`、`pg_loss`、`grad_norm` 和 routing replay 消费；
  - 后续正式协议再决定是扩大 `num_rollout` / `rollout_batch_size`，还是把 `global_batch_size` 设为小于保守有效 rollout 数的值。

## 2026-07-08 16:35-16:37 UTC 执行线程启动 train-only replay

- 执行线程已识别正式 J4 的失败根因，并转向使用 slime 自带 `--load-debug-rollout-data`：
  - 复用正式 J4 生成的 `/root/bringup/j4_formal_20260708T160749Z/rollout_dumps/rollout_{rollout_id}.pt`；
  - 跳过 SGLang rollout 和黑盒 harness；
  - 降低 `global_batch_size` 到 `16`；
  - 保留同一个 custom converter、top-p replay、routing replay 和 30B MoE 训练并行配置。
- 远端 replay run：
  - 目录：`/mnt/p3/preflight_evidence/j4_formal_20260708T160749Z_replay_gbs16_20260708T163514Z`；
  - Ray job：`raysubmit_YJWmF2t4d5QE1Jzy`；
  - 状态：`RUNNING`。
- 参数确认：
  - `debug_train_only=true`；
  - `load_debug_rollout_data=/root/bringup/j4_formal_20260708T160749Z/rollout_dumps/rollout_{rollout_id}.pt`；
  - `global_batch_size=16`；
  - `use_rollout_routing_replay=true`；
  - `use_routing_replay=true`。
- 当前日志阶段：
  - Ray placement group 已分配 GPU 0-3；
  - Megatron actor 正在初始化，已经开始 tokenizer 和 process group 初始化；
  - 尚未进入 `data_preprocess` / `ref_log_probs` / `log_probs` / `actor_train`。
- 资源状态：
  - 根盘和 `/mnt/p3` 稳定；
  - GPU 使用仍处于加载早期；
  - 没有新的 `rh2-rollout-*` 容器，符合 train-only replay 目标。

## 2026-07-08 16:38 UTC replay 越过调度断言并进入训练侧 logprob 阶段

- Ray job `raysubmit_YJWmF2t4d5QE1Jzy` 仍为 `RUNNING`。
- 资源状态：
  - 根盘 `/`：约 `73G/247G`，使用率 `30%`；
  - `/mnt/p3`：约 `842G/1.5T`，使用率 `57%`；
  - GPU 0-3 约 `50GB`，GPU 4-7 几乎为空，符合 train-only replay 只占训练侧 4 卡的预期。
- 日志关键证据：
  - `load_debug_rollout_data ... is set, will not instantiate sglang servers and will only run the training process`；
  - `global_batch_size=16`；
  - `Timer data_preprocess start/end`，耗时约 `0.3s`；
  - `Timer ref_log_probs start` 已出现。
- 当前判断：
  - replay 已经验证 `global_batch_size=16` 能越过正式 J4 中的 `num_rollouts (19) < global_batch_size (32)` 调度断言；
  - 这说明训练消费链路正在被真实验证，而不是停在 rollout 阶段；
  - 后续还需要确认 `ref_log_probs`、`log_probs`、`actor_train`、`pg_loss`、`grad_norm` 和 checkpoint 丢弃。

## 2026-07-08 16:39-16:42 UTC replay 完成真实训练 step，进入 checkpoint 保存

- 训练侧阶段已完成：
  - `ref_log_probs`：约 `37.0s`；
  - `log_probs`：约 `29.1s`；
  - `actor_train`：约 `153.6s`；
  - `train_time`：约 `220.9s`。
- 关键训练指标：
  - `train/loss=-0.14717744290828705`；
  - `train/pg_loss=-0.14717744290828705`；
  - `train/grad_norm=0.9308214724976641`；
  - `train/train_rollout_logprob_abs_diff=0.03605957701802254`；
  - `train/global_batch_size=16`；
  - `train/step=0`。
- 性能指标：
  - `perf/ref_log_probs_tflops≈60.44`；
  - `perf/log_probs_tflops≈76.91`；
  - `perf/actor_train_tflops≈43.73`；
  - `perf/actor_train_tok_per_s≈4123.30`。
- 资源状态：
  - GPU 0-3 进入高显存训练状态，约 `88GB` 到 `90GB`；
  - GPU 4-7 空闲，符合 debug train-only replay；
  - 根盘仍稳定在约 `30%` 使用率。
- 当前状态：
  - job 仍为 `RUNNING`；
  - 日志显示正在保存 checkpoint 到 `/root/bringup/j4_formal_20260708T160749Z_replay_gbs16_20260708T163514Z/ckpt`；
  - 还需要确认 checkpoint 用后删除、`replay_summary.json` 写出、Ray job 最终成功。

## 2026-07-08 16:48-16:49 UTC replay 成功收口，checkpoint 已删除

- Ray job `raysubmit_YJWmF2t4d5QE1Jzy` 最终状态：`SUCCEEDED`。
- checkpoint 保存结果：
  - 日志显示 `successfully saved checkpoint from iteration 0`；
  - `save_model` 耗时约 `373.0s`；
  - 保存期间 checkpoint 峰值目录约 `399G`，全部在 `/mnt/p3` 绑定卷路径下；
  - 根盘 `/` 始终稳定在约 `30%` 使用率，没有复现根盘写爆。
- 脚本清理结果：
  - `checkpoint_discarded=true`；
  - `/mnt/p3/bringup/j4_formal_20260708T160749Z_replay_gbs16_20260708T163514Z` 回到 `0`；
  - `/mnt/p3` 从保存峰值约 `1.3T/1.5T` 回落到约 `842G/1.5T`；
  - GPU 0-7 全部回到 `0 MiB`。
- replay summary：
  - `rc=0`；
  - `source_run=j4_formal_20260708T160749Z`；
  - `global_batch_size=16`；
  - `loss_marker_count=25`；
  - `grad_norm_marker_count=2`；
  - `checkpoint_discarded=true`；
  - `replay_wall_seconds=763`。
- 本轮结论：
  - 正式 J4 的 rollout dump 可以被 slime 训练侧真实消费；
  - top-p / routing replay 至少没有在 logprob 或 actor train 阶段触发 shape / missing-field 错误；
  - 30B MoE、4 卡训练侧、`global_batch_size=16` 可以完成 `ref_log_probs`、`log_probs`、`actor_train`、checkpoint save 和 checkpoint discard；
  - 正式 J4 原失败不是“训练消费不可行”，而是严格 `global_batch_size=32` 与有效 rollout 数口径不匹配。
- 后续协议建议：
  - J4 严格端到端判据应以 slime 实际调度口径 `effective rollout count` 为准，不应只看 branch/sample 数；
  - `j4_assertions.json` 里 `num_trainable_samples=31 < expected_min=32` 却标为 `PASS` 的问题必须修；
  - 正式 8 卡预实验要么扩大采样余量，要么把首个训练 step 的 `global_batch_size` 降到保守值，再单独测更大 batch。

## 2026-07-08 16:55 UTC 执行线程转入 J5 reduced 权重同步测试

- 执行线程已完成 J4 replay 证据核对，并同步了脚本更新：
  - `j4b_topo_compare.sh`；
  - `j5_weight_sync.sh`；
  - `j4_train_replay.sh`。
- J4c 暂未启动，原因是远端缺少 `/root/models/Qwen3-4B` 和 `/root/models/Qwen3-4B_torch_dist`，不适合临时下载/转换模型资产。
- 新启动的 J5 reduced run：
  - run id：`j5_reduced_20260708T165218Z`；
  - Ray job：`raysubmit_Ba8tJBgaTVHuhfac`；
  - 状态：`RUNNING`；
  - `J5_BUFFER_SIZES=536870912`；
  - `J5_STEPS=1`；
  - `J5_GLOBAL_BATCH_SIZE=16`。
- Ray job 参数确认：
  - `--custom-convert-samples-to-train-data-path p3_preflight.rh2_convert.convert_samples_to_train_data`；
  - `--global-batch-size 16`；
  - `--use-rollout-routing-replay`；
  - `--update-weight-buffer-size 536870912`；
  - `--update-weight-transport nccl`；
  - `--rollout-top-p 0.95`。
- 当前资源形态：
  - 根盘 `/`：约 `73G/247G`，使用率 `30%`；
  - `/mnt/p3`：约 `842G/1.5T`，使用率 `57%`；
  - GPU 0-3 约 `46GB`，训练侧已加载；
  - GPU 4-7 约 `74GB`，SGLang rollout 侧已加载，其中多张卡有高利用率。
- 当前判断：
  - J5 reduced 已经进入真实 30B train + rollout 形态；
  - 这不是 train-only replay，会重新跑一轮真实 rollout；
  - 后续重点观察权重同步耗时、是否复现 J4 的上下文溢出 / 有效 rollout 数不足、以及 512MB buffer 的稳定性。

## 2026-07-08 16:57-16:58 UTC J5 reduced 权重同步通过，但 rollout 容器初始化疑似阻塞

- Ray job `raysubmit_Ba8tJBgaTVHuhfac` 仍为 `RUNNING`。
- 权重同步层已经明确跑通：
  - `Timer update_weights start` 出现在 `16:55:37`；
  - SGLang 多次返回 `POST /update_weights_from_distributed HTTP/1.1 200 OK`；
  - `Timer update_weights end (elapsed: 9.2s)`；
  - Ray 任务摘要中 `SGLangEngine.update_weights_from_distributed FINISHED: 232`，`MegatronTrainRayActor.update_weights FINISHED: 4`。
- 当前唯一正在运行的 Ray 任务是 `RolloutManager.generate RUNNING: 1`，说明卡点已经越过训练侧和权重同步侧，落在 rollout 生成阶段。
- 32 个 `rh2-rollout-*` 容器已经创建，覆盖 8 个 SWE smoke 题，每题 4 个样本。
- 但是 evidence 目录仍只有：
  - `swe_bringup_8.jsonl`；
  - `startup_evidence.json`；
  - 没有新的 `bringup_events.jsonl`、rollout dump 或样本事件文件。
- 采样检查前 3 个 rollout 容器，均出现同一模式：
  - 主进程是 `sleep infinity`；
  - 启动命令停在 `bash -c id agent ... && chown -R agent:agent /home/agent /testbed ...`；
  - 子进程 `chown -R agent:agent /home/agent /testbed` 处于 `D` 状态；
  - 容器日志为空，CPU 约 `0%`。
- 资源状态：
  - 根盘 `/` 约 `92G/247G`，使用率 `37%`，没有写爆；
  - `/mnt/p3` 约 `842G/1.5T`，使用率 `57%`；
  - GPU 0-3 约 `48GB`，GPU 4-7 约 `75GB`，但利用率均接近 `0%`；
  - `rh2-p3` 主容器内存约 `507GiB`，说明训练与 SGLang 资源仍被占用。
- 当前判断：
  - J5 reduced 已经证明 512MB buffer 的 `update_weights` 能完成一次；
  - 当前不是训练消费失败，也不是 SGLang 初始化失败；
  - 更像是 rollout 环境物化阶段的文件所有权调整或 Docker overlay I/O 阻塞，导致 GPU 资源在等待环境初始化时空转。
- 建议后续记录为一个独立工程风险：
  - 对 SWE-Bench 镜像启动阶段的 `chown -R /testbed` 做耗时埋点；
  - 评估是否可以在环境镜像生产期预置 `agent` 用户和目录权限，避免每个 rollout 容器启动时递归 `chown`；
  - 正式训练前需要避免“训练侧和 SGLang 已加载、但 32 个沙箱卡在物化阶段”的长时间资源浪费。

## 2026-07-08 17:00 UTC J5 reduced 已越过 chown，真实 Claude Code rollout 开始

- 延迟检查显示 J5 reduced 没有永久死锁。
- 采样检查前 3 个 rollout 容器：
  - 容器总 elapsed 约 `04:30`；
  - `claude` 进程 elapsed 约 `00:33` 到 `00:35`；
  - 这意味着从容器创建到 Claude Code 启动之间约有 `3` 到 `4` 分钟被环境初始化消耗，其中主要可见步骤是 `chown -R agent:agent /home/agent /testbed`。
- 当前容器内命令已经进入真实黑盒 harness：
  - `/usr/local/bin/claude -p ... --permission-mode bypassPermissions --output-format stream-json --include-partial-messages --include-hook-events --verbose --disallowedTools Task WebFetch WebSearch`。
- 资源状态：
  - GPU 4-7 从 `0%` 转为有推理利用率，采样时约 `38% / 94% / 49% / 55%`；
  - GPU 0-3 仍保持训练侧模型常驻，约 `48GB`；
  - 根盘 `/` 约 `93G/247G`，使用率 `38%`；
  - `/mnt/p3` 仍约 `842G/1.5T`。
- 事件目录仍未新增 `bringup_events.jsonl` 或 rollout dump，说明当前处于 agent 交互进行中，样本尚未完成。
- 当前判断：
  - J5 reduced 的权重同步和真实黑盒 rollout 已经同时成立；
  - 但启动阶段暴露了环境物化固定成本，32 路并发时会造成训练侧和 SGLang 资源空等；
  - 后续是否接受该开销，取决于完整 J5 的 wall time、尾部空闲比例和样本完成率。

## 2026-07-08 17:02 UTC J5 reduced 首批 rollout 产物落盘

- Ray job 仍为 `RUNNING`。
- Ray 日志显示进度：
  - `Rollout generation: 4/32 [06:12<43:26, 93.10s/it]`。
- `bringup_events.jsonl` 已出现，当前有 `5` 条事件。
- 当前完成事件的共同特征：
  - `statuses=["Status.COMPLETED"]`；
  - `remove_sample=[false]`；
  - `abort_reason=[null]`；
  - `truncated_meta=[false]`；
  - `weight_versions_engine` 与 `weight_versions_sample` 均包含版本 `1`，说明样本确实在权重同步后的行为策略版本上产生；
  - `top_p_offsets_len` 与 `response_lengths + 1` 对齐；
  - `capture_stats` 有 staged / committed / dropped_uncommitted 统计。
- 已生成的关键产物：
  - `grading_report.json`；
  - `eligibility_report.json`；
  - `trajectory_projection.json`；
  - `capture_records.json`；
  - `group_repair_signal.json`；
  - top-p ids / offsets；
  - rollout logprobs；
  - routing tape，单条约 `30MB`。
- 当前 5 条完成样本的 reward 均为 `0.0`。
- 资源状态：
  - rollout 容器从 `32` 降到 `27`，说明已有若干容器完成并退出；
  - GPU 4-7 继续有推理利用率；
  - 根盘与外挂盘稳定。
- 当前判断：
  - J5 reduced 已经证明“512MB buffer 权重同步 -> 真实 Claude Code rollout -> token / logprob / top-p / routing tape -> 评分与资格报告 -> trajectory projection”这一段真实跑通；
  - 尚未证明训练侧能消费本轮 J5 样本，因为还没有达到 `global_batch_size=16` 并进入 `data_preprocess/ref_log_probs/log_probs/actor_train`；
  - 需要继续观察最终有效样本数量、奖励分布，以及是否因全 0 reward 或有效 rollout 数不足而被 slime 调度拒绝。

## 2026-07-08 17:06 UTC J5 reduced 样本数超过 batch 下限，但长上下文问题复现

- Ray job 仍为 `RUNNING`。
- `bringup_events.jsonl` 当前有 `15` 条事件。
- 累计样本状态：
  - `Status.COMPLETED`: `18`；
  - `Status.ABORTED`: `1`；
  - `remove_sample=false`: `18`；
  - `remove_sample=true`: `1`。
- 拒收原因：
  - `rh2_assemble_failed:SlimeBindingError`: `1`；
  - Ray 日志同时出现 `[rh2-capture] ... prompt exceeds max_context_tokens (35455 >= 32768)`。
- 奖励分布：
  - `reward=0.0`: `17`；
  - `reward=1.0`: `2`。
- 题目分布：
  - `psf__requests-2931`: `2`；
  - `sympy__sympy-15349`: `4`；
  - `sympy__sympy-14711`: `2`；
  - `astropy__astropy-14995`: `4`；
  - `django__django-11099`: `2`；
  - `django__django-16139`: `1`。
- `response_lengths` 范围：`1` 到 `3561`。
- 当前产物目录数：`14` 个 rollout 目录。
- 资源状态：
  - 根盘 `/` 回落到约 `84G/247G`，使用率 `34%`；
  - `/mnt/p3` 约 `843G/1.5T`，使用率 `57%`；
  - GPU 4-7 仍在推理侧工作，采样时约 `71% / 70% / 53% / 71%`；
  - GPU 0-3 仍是训练侧常驻，利用率为 `0%`，等待 rollout 收齐后进入训练消费。
- 当前判断：
  - J5 reduced 已经产生超过 `global_batch_size=16` 的完成样本数量，并且奖励不再是全 0；
  - 但是否满足 slime 训练调度口径仍要等 rollout 阶段结束，因为 J4 曾经出现“样本数接近够，但有效 rollout id 口径不够”的失败；
  - 长上下文超限问题没有消失，正式训练前仍需要保留 fail-closed 拒收、上下文预算、compaction 或缩短任务 prompt 的专项处理。

## 2026-07-08 17:12 UTC J5 reduced 进入 rollout 收尾段，长上下文拒收增加

- Ray job 仍为 `RUNNING`。
- Ray 日志进度：
  - `8/32 [10:30<30:30, 76.26s/it]`；
  - `12/32 [11:59<17:13, 51.67s/it]`；
  - `16/32 [13:23<10:31, 39.49s/it]`；
  - `24/32 [13:57<02:46, 20.84s/it]`。
- `bringup_events.jsonl` 当前有 `29` 条事件。
- 累计样本状态：
  - `Status.COMPLETED`: `35`；
  - `Status.ABORTED`: `6`；
  - `remove_sample=false`: `35`；
  - `remove_sample=true`: `6`。
- 拒收原因：
  - `rh2_assemble_failed:SlimeBindingError`: `6`。
- 奖励分布：
  - `reward=0.0`: `36`；
  - `reward=1.0`: `5`。
- 题目覆盖：
  - `psf__requests-2931`: `4`；
  - `sympy__sympy-15349`: `4`；
  - `sympy__sympy-14711`: `4`；
  - `astropy__astropy-14995`: `4`；
  - `django__django-11099`: `4`；
  - `django__django-16139`: `3`；
  - `psf__requests-1142`: `4`；
  - `django__django-11133`: `2`。
- `response_lengths` 范围扩大到 `1` 到 `13138`。
- 长上下文超限日志增加：
  - `35455 >= 32768`；
  - `34681 >= 32768`；
  - `32855 >= 32768`；
  - `32899 >= 32768`；
  - `32943 >= 32768`；
  - `49246 >= 32768`；
  - `47212 >= 32768`；
  - `47256 >= 32768`；
  - `47300 >= 32768`。
- 当前还没有 `rollout_*.pt` dump，说明 rollout 尚未全部汇总给 slime 训练侧。
- 资源状态：
  - 根盘 `/` 约 `75G/247G`，使用率 `31%`；
  - `/mnt/p3` 约 `846G/1.5T`，使用率 `57%`；
  - GPU 4-7 仍在推理侧工作；
  - GPU 0-3 训练侧等待。
- 当前判断：
  - J5 reduced 已经基本证明真实 rollout 侧可持续产出多题、多样本、含 top-p 与 routing tape 的可投影轨迹；
  - 长上下文超限是当前最大可见失败来源，且会随 Claude Code 多轮交互明显放大；
  - 需要等最终汇总后确认两点：第一，slime 是否按有效 rollout 口径接受这些样本；第二，是否进入 `data_preprocess/ref_log_probs/log_probs/actor_train`。

## 2026-07-08 17:15 UTC J5 reduced 最终失败：rollout 完成，但 DP schedule 差一个 microbatch

- Ray job `raysubmit_Ba8tJBgaTVHuhfac` 最终状态：`FAILED`。
- 32 个 rollout index 全部到达事件层：
  - index 覆盖 `0..31`；
  - group 覆盖 `0..7`；
  - 每个 group 都有 `4` 个事件。
- 最终累计样本状态：
  - `Status.COMPLETED`: `41`；
  - `Status.ABORTED`: `7`；
  - `remove_sample=false`: `41`；
  - `remove_sample=true`: `7`。
- 最终奖励分布：
  - `reward=0.0`: `39`；
  - `reward=1.0`: `9`。
- 最终 group 分布：
  - group 0：`4` completed，reward 全 `1.0`；
  - group 1：`5` completed + `1` aborted，reward 全 `0.0`；
  - group 2：`6` completed + `1` aborted，`5` 个 `1.0`；
  - group 3：`5` completed + `1` aborted，reward 全 `0.0`；
  - group 4：`4` completed，reward 全 `0.0`；
  - group 5：`3` completed + `3` aborted，reward 全 `0.0`；
  - group 6：`7` completed + `1` aborted，reward 全 `0.0`；
  - group 7：`7` completed，reward 全 `0.0`。
- rollout 性能日志：
  - `perf/rollout_time`: `1132.1208s`；
  - `rollout/response_len/mean`: `998.29`；
  - `rollout/response_len/median`: `841.0`；
  - `rollout/response_len/max`: `4202`；
  - `rollout/zero_std/count_1.0`: `1`；
  - `rollout/zero_std/count_0.0`: `6`；
  - `perf/tokens_per_gpu_per_sec`: `25.65`；
  - `perf/effective_tokens_per_gpu_per_sec`: `10.58`。
- 失败堆栈：
  - `RolloutManager.generate()` 完成 rollout 后进入 `_split_train_data_by_dp(data)`；
  - `build_dp_schedule()` 断言失败；
  - 错误文本：
    `AssertionError: dynamic path: could only produce 23 mbs after maximal splitting; need 24. step 0 has 23 samples, below the alignment threshold (2).`
- 这次失败与 J4 失败同属“训练调度有效样本口径”问题，但形态更具体：
  - J4 是 `num_rollouts (19) < global_batch_size (32)`；
  - J5 reduced 是 rollout 样本完成很多，但 DP schedule 只能切出 `23` 个 microbatch，低于目标 `24`。
- 训练阶段实际没有进入：
  - 没有 `ref_log_probs/log_probs/actor_train/pg_loss/grad_norm`；
  - `j5_update_weights.csv` 记录 `rc=1`；
  - `update_weights.json` 中 `per_step_update_weights_time_s=[]`，因为失败发生在后续训练 step 前，无法形成完整权重同步耗时分解。
- 资源收尾：
  - GPU 0-7 全部释放到 `0 MiB`；
  - 根盘 `/` 约 `73G/247G`，使用率 `30%`；
  - `/mnt/p3` 约 `847G/1.5T`，使用率 `57%`；
  - 只有主容器 `rh2-p3` 仍运行。
- 产物大小：
  - `/mnt/p3/bringup/j5_reduced_20260708T165218Z` 约 `5.3G`；
  - `/mnt/p3/preflight_evidence/j5_reduced_20260708T165218Z` 约 `763K`；
  - 最大文件主要是 routing tape，单文件约 `38MB` 到 `50MB`。
- 当前判断：
  - J5 reduced 正向证明：512MB buffer 权重同步可跑通一次；真实 Claude Code rollout 可完成 32/32；token、logprob、top-p tape、routing tape、评分、资格、投影都能批量产出；奖励不是全 0。
  - J5 reduced 未证明：slime 后续训练消费可在当前参数下启动；`global_batch_size=16` 并不足以保证 DP schedule 能对齐。
  - 下一步不应该重跑同配置。应先离线复用本轮事件和 trajectory 产物，检查 `p3_preflight.rh2_convert.convert_samples_to_train_data` 产出的 train data 在 slime `build_dp_schedule` 口径下为什么只有 `23` 个 microbatch，并决定是调整 batch / DP schedule 参数，还是在 converter 里做更明确的 group / sample 保守选择。
