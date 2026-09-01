# W9 实现报告 · faithful DIS custom loss 的 CP（context parallel）>1 支持

日期：2026-09-02。范围：计划 06 §3 W9 行 + §1 A1 CP 语义（owner 拍板：目标链路必须同时支持 CP=1 与 CP>1，CP=2 是显存不足时的现实候选，数值临场定）。miles 基座：`reference/miles-rh2-integration`，分支 `rh2-integration-v3`（HEAD 63c7a94e7）。本文引用的 miles 行号均指该基座。

**只改了三处**：`rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py`（实现）、新增 `rh2/tests/adapters_miles/test_w9_cp_faithful_dis.py`（32 个测试）、`rh2/tests/adapters_miles/test_faithful_dis_loss.py` 中一个因本工作包而失效的 oracle（T1，见 §5.1）。**未触碰**：`training/faithful_dis.py` 标量权威、`contracts/`、`reference/`、其它既有测试、并行 agent 正在改的 `generate_fn.py`/`adapters/slime/`/`bringup.py`/`envpack/`/`grading/`。无 git commit/stash；manifest 未改（归集成者）。

---

## 0. 交付物一览

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py` | 修改 | 移除 `cp.size != 1` 整体 fail-closed，改为真实 CP 切分语义：CP 状态校验、token 流对账、本 rank 分片长度推导与三列长度校验、逐 token 分子只在分片上算、计数 CP 组内归约、零贡献旗标/记账事件的 rank 0 单点发射、空分片 rank 的 autograd 图连接；模块 docstring 新增 "CP>1 切分语义" 条目 |
| `rh2/tests/adapters_miles/test_w9_cp_faithful_dis.py` | 新增 | 30 个单进程 mock ParallelState 测试 + 2 个两进程 CPU gloo 测试（均 `integration_base`） |
| `rh2/tests/adapters_miles/test_faithful_dis_loss.py` | 修改 1 个测试 | `test_cp_not_supported_fail_closed` → `test_cp1_shaped_batch_under_cp2_rejected_before_reducer`，期望 reason_code `cp_not_supported` → `cp_token_stream_missing`（T1） |

---

## 1. 切分规则与对齐假设（与 miles 哪个函数同源）

**切分规则一句话**：每条样本（thd 按 `total_length`、bshd 按 `max_seq_len`）补齐到 `2·cp_size·chunk_size` 后等分成 `2·cp_size` 块，rank r 拥有第 `r` 块与第 `2·cp_size−1−r` 块（zigzag），本 rank 的 response 位置 = 这两块与 response 区间的交集按块序拼接；唯一来源是 miles `cp_utils.get_logits_and_tokens_offset_with_cp`（`miles/backends/training_utils/cp_utils.py:19-67`），本函数与 miles 的取行/切 mask/切 logprob 三处都是它的消费者。

到达 `faithful_dis_loss_function` 时各列的形态（integration base 代码事实，逐条核实）：

| 列 | 到达时形态 | miles 生产/消费锚点 | 本函数在 CP>1 下的处理 |
|---|---|---|---|
| `rollout_log_probs`（behavior） | **已是本 rank 分片** | `data.py:93-116` `get_rollout_data` 用 `slice_log_prob_with_cp`（`cp_utils.py:411-437`）切过 | 长度必须 == 本 rank 分片长度（否则 `batch_column_length_mismatch`） |
| `advantages` | **已是本 rank 分片** | `loss.py:80-83` 本 rank 分片形状的 kl → `math_utils.py:453` `get_grpo_returns` 的 `ones_like(kl[i])·reward` 广播；`advantages.py:131-170` `normalize_advantages` 在 CP>1 下用同一 offset 规则切 mask 做加权 | 同上；"advantage 广播"由 miles 在分片形状上完成，本函数只校验对齐 |
| `loss_masks` | **全量** | reducer `get_sum_of_sample_mean`（`cp_utils.py:98-168`）与 `get_local_response_loss_masks`（`:171-192`）各自用 `_slice_loss_mask_for_local_cp`（`:70-84`）切片 | 先按 `response_length` 校验全量，再用 `get_local_response_loss_masks` 取本 rank 分片；分片长度与 offset 规则独立算出的行数对账（`cp_layout_inconsistent`） |
| `unconcat_tokens` + sampling-mask CSR | **全量** | `data.py:174` `batch["unconcat_tokens"] = tokens`（切片前保存）；`logit_processors.py:122-153` 按全局偏移取本 rank logits 行/target/`response_indices`；`:247` `build_local_sampling_mask` 据 `response_indices` 从全量 CSR 选本 rank 行的支持集 | target∈support 断言在每个 rank 对**整条** response 执行（本 rank 分片的超集，见 §5.3）；current logprob 的支持集重归一化由 miles 在本 rank 行上完成 |
| `logits` / `batch["tokens"]` | 本 rank zigzag 布局 `[1, Σ_i 2·chunk_size_i (+尾部 pad), V]` | `data.py:219` `slice_with_cp`（`cp_utils.py:256-303`），`:226-232` 拼接 + 尾部 pad；`model.py:776` get_batch keys 含 `tokens` | `batch["tokens"]` 必须等于 `unconcat_tokens` 用同一 `slice_with_cp` 切出的分片前缀，且 `logits.shape[:-1] == tokens.shape` |
| `rollout_mask_sums` | 逐样本标量，各 rank 相同 | `train_data_conversion.py:209` | 用全量 mask 核账（比分片口径更强） |

三层归约在 CP>1 下的成立方式：本函数只产本 rank 分片的逐 token 分子，交给 dispatcher 构造的 CP 感知 reducer（`loss.py:163-171` → `get_sum_of_sample_mean` CP 分支按同一规则切 mask、除以整 execution 分母）；各 rank 的 `片段分子/D_e` 经 DP×CP 梯度归约求和恰好重构完整 `loss_e`——与 sibling 分散到不同 microbatch 的重构机制同构。dispatcher 的 `loss_parallel_size = intra_dp_cp.size`（`loss.py:203-208`）与 DDP 归约的 ÷size 相消，标量权威（`DENOMINATOR_SEMANTICS_V1="provenance_tokens"`）语义与数值未动。

指标/事件的 CP 口径（与 `aggregate_train_losses` 的 DP×CP **求和**口径对齐，`log_utils.py:441-492`）：`loss`/`dis_microbatch_provenance_tokens`/`dis_accepted_tokens`/`dis_rejected_tokens` 报**本 rank 分片值**（跨 CP 求和后 = CP=1 数值）；`dis_zero_contribution_microbatch` 按 CP 组内总 accepted 判定、只由 cp rank 0 报 1（其余 rank 报 0，聚合后 = CP=1 数值），组内求和用一次 `dist.all_reduce`（与 `math_utils.py:35-82` `compute_ess_ratio_contribution` 同款，含"只由 rank 0 发射非线性量"的做法）；`sample_dis_accounting` 事件用组内归约后的整条 response 计数、只由 cp rank 0 发射一次（judge 的逐样本事实不被切分拆半、不重复）。

---

## 2. 移除 fail-closed 后的形状校验清单（无静默降级）

| reason_code | 触发条件 | 出现时机 | 测试 |
|---|---|---|---|
| `cp_state_invalid` | `parallel_state.cp` 缺失 / `size` 非正整数（含 None、bool）/ `rank` 越界 | 入口，任何计算之前 | `test_cp_state_missing_rejected`、`test_cp_size_none_rejected`、`test_cp_rank_or_size_out_of_range_rejected[4 组]` |
| `allgather_cp_unverified` | `cp.size>1` 且 `args.allgather_cp=True`（DSA 连续切分布局，W9 未验证；CP=1 不拦，原样交 miles） | 入口 | `test_cp2_allgather_cp_rejected` |
| `cp_token_stream_missing` | `cp.size>1` 而 batch 无 `tokens`（get_batch 切片后的本 rank token 流） | 消费任何列之前 | `test_cp2_tokens_missing_rejected`、`test_cp1_shaped_batch_declared_under_cp2_is_rejected_before_any_compute`、既有测试的更新 oracle |
| `logits_tokens_shape_mismatch` | `logits.shape[:-1] != tokens.shape` | 同上 | `test_cp2_logits_rows_not_matching_tokens_rejected` |
| `cp_token_stream_mismatch` | `tokens` 前缀 ≠ `unconcat_tokens` 按 zigzag 规则切出的本 rank 分片（全量布局误入、rank 串位都在此拒绝——全量 12 行 ≥ 本地 8 行，只靠行数下界抓不住） | 同上 | `test_cp2_full_layout_tensors_rejected`、`test_cp2_token_stream_from_other_rank_rejected` |
| `batch_column_length_mismatch`（沿用） | `loss_masks` 长度 ≠ `response_length`（必须全量）；`rollout_log_probs`/`advantages` 长度 ≠ 本 rank 分片长度（必须已切片） | 列消费时 | `test_cp2_locally_sliced_loss_masks_rejected`、`test_cp2_unsliced_full_column_rejected[2 列]` |
| `cp_layout_inconsistent` | miles 切出的 loss_mask 分片长度 ≠ offset 规则独立算出的本 rank 行数（miles 内部两处切片实现漂移的哨兵） | 分片推导时 | 由 `test_local_layout_helper_agrees_with_miles_mask_slicing` 正向钉死；反例需伪造 miles 内部漂移，未构造 |
| `current_logprob_length_mismatch`（沿用） | miles 取出的 current logprob 行数 ≠ 本 rank 分片长度 | logprob 计算后 | 逻辑同上，正向由守恒测试覆盖 |
| `cp_group_missing` | `cp.size>1` 而 `cp.group` 为 None（组内计数无法归约，零贡献判定无法与 CP=1 一致） | 计数归约处 | `test_cp_group_missing_rejected_at_reduce_point` |
| `target_not_in_support`（沿用） | 任一 rank 对整条 response 的断言失败 | gather 前 | `test_cp2_target_not_in_support_across_rank_boundary_raises_on_every_rank[位 1/2/7/8 × 两 rank]`、gloo `test_cp2_gloo_cross_rank_target_violation_raises_on_both_ranks` |

不存在"cp 读不到就按 CP=1 算"、"cp.size>1 但跳过断言"或"列长度不符时截断/补零"的路径；所有 CP 相关拒绝都在触达 reducer 与 collective 之前（负例测试把两者都换成会炸的桩）。

---

## 3. CP=1 逐位不变证据

1. **既有测试**：`test_faithful_dis_loss.py`（53 个，其中 52 个 oracle 未动全绿，1 个因本工作包失效而改 oracle，见 §5.1）、`test_train_seam_metamorphic.py`（12，含 dispatcher/megatron 缩放链与 F2 零信号 seam）、`test_w0_knob_consumption.py`（18）全绿，两条 lane 都跑。
2. **HEAD 版 vs 工作树版逐位对拍**（一次性脚本，会话 scratchpad，未入库；复现方法：`git show HEAD:rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py` 另存为独立模块名后与工作树版同批调用）：60 个随机 batch（1~4 样本、response 2~8 token、随机支持集/loss_mask/advantage、log-ratio 均匀落在 ±3 覆盖区间内外）在 CP=1 下 `loss`、全部 4 个 metrics、`dL/dlogits`、`sample_dis_accounting` entries **全部 `torch.equal`/`==`**；7 种 fail-closed 变异（非有限、mask 非 0/1、缺/矛盾 `rollout_mask_sums`、缺 behavior、advantage 长度错、mask 覆盖数错）两版 reason_code 相同。
3. **结构性证据**（`test_cp1_layout_is_identity_and_reduce_is_noop`）：CP=1 下 `_local_response_layout` 返回的分片列表就是传入的全量列表对象本身（miles `get_local_response_loss_masks` 在 `cp.size==1` 原样返回），分片长度 == `response_lengths`；`_cp_all_reduce_sum` 原样返回同一张量、不触碰 `torch.distributed`；零贡献旗标与事件的发射条件（`cp.rank == 0`）恒真。

CP=1 下**可观察到的两处差异**（都不是数值差异，如实列出）：

- 单 token response（R=1）在 `true_on_policy_mode=True` 路径：HEAD 版抛 `RuntimeError: zero-dimensional tensor cannot be concatenated`（miles 形状 quirk，finding W9-F1），工作树版正常出 loss。生产 megatron 路径不受影响（返回 `[R,1]`），RH2 launch 未启用 true_on_policy_mode。
- fail-closed 检查顺序：`loss_masks` 的校验（长度/0-1/`rollout_mask_sums` 核账）现在在 current logprob 计算之前（分片长度必须先于三列校验推导出来）。只影响**同时存在多处损坏**时哪个 reason_code 先报，单一损坏的 reason_code 与旧版逐一相同（上面第 2 条）。

---

## 4. CP=2 模拟测试清单

固定数据（thd，VOCAB=17，三样本各自成 execution）：s0 total 12/resp 10 → rank0 拥有 response 位 {0,1,8,9}、rank1 {2..7}（两处跨 rank 边界 1|2、7|8）；s1 total 7/resp 4 → rank0 **空分片**、rank1 全有；s2 total 9/resp 6 → rank0 {0}、rank1 {1..5}。测试侧切分只用 miles 公开 helper 并显式传 `cp_rank/cp_size`（`get_logits_and_tokens_offset_with_cp`、`slice_with_cp(parallel_state=...)`、`assemble_log_prob_from_cp`），不读全局状态。

**正例（mock ParallelState，`_cp_all_reduce_sum` seam 用 monkeypatch 两遍模拟：第一遍记录各 rank 本地计数，第二遍回填组内总数）**

| 测试 | 断言 |
|---|---|
| `test_zigzag_local_positions_match_hand_computed` | miles helper 给出的本 rank 位置 == 人工按规则算出的集合；两 rank 恰好划分整条 response |
| `test_local_layout_helper_agrees_with_miles_mask_slicing` | 被测 `_local_response_layout` 的分片长度/内容 == miles 切片 == 人工集合 |
| `test_cp1_baseline_matches_execution_authority` | CP=1 参照物本身仍与标量权威 `faithful_dis_loss_by_execution` 一致（分母 8/4/5） |
| `test_cp2_mock_numerators_grads_and_counts_reconstruct_cp1` | 逐 token 分子经 `assemble_log_prob_from_cp` 拼回 == CP=1（`torch.equal`）；两 rank 部分和 == CP=1 loss（float64，rtol/atol 1e-12，求和顺序不同）；`dL/dlogits` 本地块拼回 == CP=1（`torch.equal`，pad 行梯度精确 0）；三个线性计数指标跨 rank 求和 == CP=1；seam 每 rank 每遍恰好调用一次（含空分片 rank）；旗标两 rank 都 0 |
| `test_cp2_mock_empty_shard_rank_is_zero_loss_but_graph_connected` | 只含 s1 的 microbatch：rank0 分片全空 → loss 精确 0、`backward()` 可跑、梯度全 0、本地计数 0、旗标按组内总数为 0；rank1 单独等于 CP=1 全量 |
| `test_cp2_mock_zero_signal_semantics_match_cp1[all_rejected / zero_provenance]` | 组内 accepted=0 → 旗标 `[1.0, 0.0]`（只 rank 0 报，聚合和 == CP=1 的 1.0）；两 rank loss 精确 0 且带图、梯度精确 0；provenance 计数跨 rank 和 == CP=1 |
| `test_cp2_mock_accounting_event_emitted_once_with_group_counts` | rank 0 发射的 entries == CP=1 发射的 entries（s0 (5,8)、s1 (3,4)、s2 (3,5)）；rank 1 不发射 |
| `test_cp2_target_not_in_support_positive_control` | 支持集完好时两 rank 都正常出有限 loss（排除"总是炸"假阳性） |

**正例（两进程 CPU gloo 组，真实 `dist.all_reduce` + 真实 `GroupInfo.group` + miles CP 感知 reducer）**

| 测试 | 断言 |
|---|---|
| `test_cp2_gloo_two_process_group_reconstructs_cp1` | 与 mock 正例同一套守恒/对齐断言（分子/梯度逐位、loss 1e-12、计数求和）；旗标 `[0,0]`；记账事件只 rank 0 发射一次且 entries == CP=1 |

**负例**

| 测试 | 期望 |
|---|---|
| `test_cp2_target_not_in_support_across_rank_boundary_raises_on_every_rank[1/2/7/8]` | s0 跨 rank 边界两侧位置的 target 被剔除出支持集 → **两个 rank 都**抛 `target_not_in_support`，且在 reducer 与 collective 之前 |
| `test_cp2_gloo_cross_rank_target_violation_raises_on_both_ranks` | 真实两进程：s0 位 2（rank1 拥有，紧邻 1|2 边界）损坏 → 两 rank 都抛同一 reason_code，无单边挂起，无事件发射 |
| §2 表中全部 fail-closed 负例 | 见 §2 |

---

## 5. T1 决策（实现后明确报告）

1. **既有测试 oracle 改动**：`test_cp_not_supported_fail_closed` 断言的正是本工作包被要求移除的 `cp_not_supported` 路径，无法保留。改为 `test_cp1_shaped_batch_under_cp2_rejected_before_reducer`：同一输入（cp.size=2 声明下的 CP=1 形态 batch）仍在触达 reducer 之前被拒绝，reason_code 变为 `cp_token_stream_missing`——测试意图（"cp.size≠1 时绝不静默按 CP=1 算"）保留，只是拒绝理由具体化。硬约束"不改既有测试"与"移除 fail-closed"在此处不可能同时满足，按"改则 T1 报告"处理。
2. **`allgather_cp` 在 CP>1 下 fail-closed**（`allgather_cp_unverified`）：DSA 的连续切分布局在 get_batch/logit_processors 各有一条分支再经 `allgather_cp_redistribute` 转回 zigzag，W9 只验证了 zigzag 布局的 token 流对账与守恒。miles 只对 DeepSeek V4 强制该旗标（`arguments.py:3723-3724`），默认 False（`:426-429`）。CP=1 不拦（该旗标不改变本函数任何布局假设，原样交 miles）。解锁条件：补 allgather 布局的 token 流对账规则 + 对应守恒测试。
3. **target∈support 断言在每个 rank 对整条 response 执行**，而不是只查本 rank 分片：CSR 与 `unconcat_tokens` 到达时都是全量，整条断言与切分规则无关，任一 rank 发现损坏即拒绝，也避免"只查本 rank 行"在切分规则漂移时漏查。代价是 cp_size 倍的 CPU 侧整型比较，可忽略。"对本 rank 分片逐位执行"的验收由跨 rank 边界负例（两侧位置、两个 rank）证明。
4. **指标/事件的 CP 口径**（§1 末段）：线性计数报本 rank 值、非线性旗标与逐样本事件由 rank 0 单点发射——沿 miles `compute_ess_ratio_contribution` 的既有模式，不新增 metrics key，不改事件 schema。
5. **空分片 rank 的 autograd 图连接**：miles 对空块返回 `logits.new_zeros((0,))`（不带图，`math_utils.py:1021`/`:1057`），本 rank 在整个 microbatch 没有 response 行时 loss 没有 `grad_fn`，megatron backward 会直接报错。本函数在 `loss.requires_grad` 为 False 时加 `0.0 * logits.sum()`（数值与梯度精确 0；与 `loss.py:186-188` 对 allgather_cp 的处理同款）。CP=1 下 response 至少一行，分支不可达（§3 第 2 条 60 个随机 batch 逐位一致也覆盖）。
6. **log-prob 形状归一**：`get_log_probs_and_entropy` 对 `[R]` 再 `squeeze(-1)` 会把 R=1 压成零维（finding W9-F1），本函数用 `reshape(-1)` 规整后再校验长度——只改形状不改数值，同时修掉 CP=1 单 token response 在 true_on_policy 路径的既有崩溃。
7. **CP>1 下新增输入要求 `batch["tokens"]`**：生产 get_batch 无条件提供（`model.py:776`），单元测试构造 CP>1 batch 时必须给。这是能抓住"全量布局误入"的唯一可靠对账物（§2 `cp_token_stream_mismatch`）。CP=1 不要求（保持既有测试与行为不变）。
8. **fail-closed 检查顺序调整**（§3 末）。
9. **测试 seam**：`_cp_all_reduce_sum` 是模块级函数，单进程 mock 测试用 monkeypatch 替换以模拟组内求和；其真实语义（`dist.all_reduce` SUM）由 gloo 两进程测试覆盖。seam 本身在 group 缺失时 fail-closed，不会因为被"忘记 patch"而静默。

## 6. 偏离说明

- 改了一个既有测试（§5.1），原因如上。
- 计划文本把工作项写成"CP 归约"；核实后本函数**不自建**跨 CP 的 loss 归约（R6-ext B4 定案：分子交 miles reducer，DP/CP 归约由 miles 链路完成），唯一新增的 collective 是计数的组内 SUM（服务于零贡献旗标与逐样本事件的正确性），loss/梯度的 CP 归约仍由 miles 的 reducer + DDP 完成。

## 7. Findings（miles 侧，未改任何 reference/ 文件）

| 编号 | 内容 | 影响 |
|---|---|---|
| **W9-F1** | `logit_processors.py:265` 对 `calculate_log_probs_and_entropy` 的返回无条件 `squeeze(-1)`；true_on_policy 路径（`math_utils.py:1066`）已返回一维 `[R]`，R=1 时被压成零维，随后任何 `torch.cat` 崩溃（stock `policy_loss_function` 的 `torch.cat(log_probs)` 同样暴露）。megatron 路径返回 `[R,1]` 无此问题 | 单 token response，或 CP>1 下本 rank 恰好只有一行的分片。faithful DIS 已用 `reshape(-1)` 规避；RH2 launch 未启用 true_on_policy_mode，生产不受影响 |
| **W9-F2** | 空块返回 `logits.new_zeros((0,))`（`math_utils.py:1021`、`:1057`）不带 autograd 图；zigzag CP 下某 rank 在整个 microbatch 没有 response 行时（典型：长 prompt + 短 response + micro_batch_size=1，response 整体落在另一 rank 的块里）loss 无 `grad_fn`。dispatcher 只对 allgather_cp 做了图连接（`loss.py:186-188`），stock PPO 在 zigzag CP 下同样暴露 | faithful DIS 已自行连接图（§5.5）。**若 C 包改选 stock PPO 并用 CP>1，此项须进其独立验收 oracle**（A8 口径：不能继承 faithful DIS 的 CP 结论） |
| **W9-F3** | CP>1 下 fail-stop 的不对称：只在本 rank 分片上可见的损坏（如某 rank 分片里的非有限 behavior logprob）在计数 all_reduce 之前抛错，兄弟 rank 会阻塞在 collective 直到 watchdog/超时把 job 杀掉；全量数据类损坏（target∉support、mask 长度、sums）在所有 rank 一致抛错 | job 仍然停止，但错误在兄弟 rank 上表现为 collective 超时而非直接异常。loss 函数内无法在不增加一次"预协商" collective 的情况下消除；记为开放问题 |

## 8. 开放问题（含只有真机能验证的项）

1. **真机 CP=2 端到端**（归 GPU spike C 包，W7 judge 覆盖 CP 语义）：ring attention 下 logits 真由 CP 切分产生，bf16 下 CP=2 与 CP=1 的 loss/梯度只能在数值容差内对拍（本地 float64 逐位相等的口径到真机会变成容差口径，阈值临场定）；NCCL 上 int64 计数 `all_reduce`（本地只用 gloo/CPU 验证）；`0.0 * logits.sum()` 在 megatron/TP 词表并行 logits 上的开销与行为。
2. **bshd 格式 + CP>1** 未测（分支代码存在：`_authenticate_local_token_stream` 与 `_local_response_layout` 都带 `max_seq_lens`；miles 默认 thd）。
3. **`allgather_cp`（DSA）解锁**：见 §5.2。
4. **Ulysses CP（`cp_comm_type="a2a"`）**：上游 `tests/fast/backends/training_utils/test_ulysses_cp_utils.py` 表明 response 侧仍是 zigzag 布局，本函数不感知 `cp_comm_type`；dispatcher 的 `loss_parallel_size` 在 true_on_policy+ulysses 下取 `intra_dp.size`（`loss.py:203-207`），在本函数之外，未验证。
5. **W9-F3 的不对称 fail-stop**：是否值得加一次组内"错误预协商"（多一次 collective）由 owner 权衡。
6. `recompute_loss_function=True` 时 loss 函数在 backward 重算一遍：计数 all_reduce 会跑两次（各 rank 一致，无挂起），`sample_dis_accounting` 事件会重复发射——这是 CP=1 就存在的既有性质（judge `_dedupe_fact` 去重），非 W9 引入，记录备查。

## 9. 测试/证据/账本状态

命令与计数（cwd `rh2/`；`-p no:cacheprovider` 仅避免写缓存文件）：

| lane | 命令 | 改前 | 改后 |
|---|---|---|---|
| 默认 base（pin） | `uv run pytest tests/adapters_miles/ -q` | 278 passed, 185 skipped | **278 passed, 217 skipped**（+32 skipped = W9 新测试全部 `integration_base`） |
| integration base | `RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q` | 463 passed | **495 passed**（+32） |
| 标量权威 | `uv run pytest tests/training/ -q` | 18 passed | 18 passed（未动） |
| W9 单文件 | 同 integration 环境，`tests/adapters_miles/test_w9_cp_faithful_dis.py` | — | 32 passed（30 mock + 2 gloo，约 5s） |
| ruff | `uv run ruff check` 三个改动文件 | — | All checks passed |

manifest 未更新（由集成者更新）。gloo 测试用 `torch.multiprocessing.spawn` 起两个子进程、文件 rendezvous、300s 上限，子进程每步写 progress 文件（超时时附在断言信息里定位卡点）；子进程通过 `importlib` 按路径加载同目录 `conftest.py` 复用 ray stub 与路径装配，不依赖 pytest 的 conftest 导入。

---

## 收尾五段

① **待拍板 T0**：无。未改标量权威语义、公共 schema/事件 schema、样本准入、reward/loss 权重；未新增可能产生系统性样本偏置的拒绝路径（所有新增拒绝都是"配置/布局不一致即整 microbatch fail-stop"，不是逐样本剔除）。
② **T1 决策**：§5 共 9 条。
③ **临时挡板**：新增 `allgather_cp_unverified`（CP>1 + DSA allgather 布局；解锁条件见 §5.2）；命中/解除的旧挡板：`cp_not_supported` 整体 fail-closed 已解除（本工作包目标）。
④ **推翻/修正的旧结论**：`faithful_dis_loss.py` 旧 docstring/06 计划把 W9 表述为"接 CP 归约"，核实后 loss/梯度的 CP 归约本就由 miles reducer + DDP 承担，本函数需要做的是切分对账与计数归约（§6）；`training/faithful_dis.py` 模块注释"CP/VPP 维度的分布式归约留接线期在真实并行环境验证"这句仍然有效（真机部分归 C 包），本轮未改该文件。
⑤ **测试/证据/账本**：§9；CP=1 逐位证据 §3；CP=2 清单 §4。

**本轮没有改变哪些已定案语义**：faithful DIS 公式、ε 预注册值、`provenance_tokens` 分母语义与 `rollout_mask_sums` 核账、ratio detach、区间外权重精确 0、F2 零贡献 microbatch 不抛错 + 全局零信号归 train_one_step、C2 target∈support 在 gather 前且 CPU 侧断言、B5 设备约定、实验 FT trainer 锁、replay/per-token-loss fail-closed、`sample_dis_accounting` 事件 schema、metrics key 集合、CP=1 的全部数值。
