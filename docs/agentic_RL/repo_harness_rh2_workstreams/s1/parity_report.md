# S1-8 parity 报告：parity-core（token 逐位）与 parity-cross（治理事实级）

- 执行计划：`../03-s1-execution-plan.md` S1-8 节；拆分依据：`s1_supplementary_clauses.md` C1（验收级）。
- 脚本：`rh2/experiments/s1_parity.py`（可直接运行；`rh2/tests/adapters/test_s1_parity.py` 用 importlib 加载同一模块复跑全部断言，纳入 `uv run pytest` 全量套件）。
- 运行方式：`cd rh2 && uv run python experiments/s1_parity.py`（输出机器可读 JSON；本报告数值即 2026-07-08 本机实跑结果）。
- 相关交付物：`rh2/src/repoharness2/contracts/export.py`（TrainingExportRecord）、`rh2/src/repoharness2/adapters/offline_export/exporter.py`、`rh2/src/repoharness2/adapters/verifiers_projection.py`。

---

## 1. parity-core：slime 在线消费形状 vs 离线导出（token 逐位，E8 解耦证据本体）

### 1.1 判据说明

同一批 S1-6 mock 链产出（真实 `GenerationCaptureHook` → `backfill_leaf_sample` → `project_from_slime` → `finalize_rollout` 全链，只有 docker/harness/SGLang 响应/评分提交是接口同形替身），分两路消费后比对：

```text
A 路（slime 在线消费形状）：rh2_custom_generate 交付的叶链 Sample——
    tokens / loss_mask / rollout_log_probs / reward / metadata 两个派生视图键。
B 路（离线导出）：FinalizedRollout + capture 记录 + artifact 字节流
    -> TrainingExportRecord（records.jsonl）+ artifacts/*.bin + manifest.json。

逐位判据（任一不等即 parity 失败）：
1. token ids：导出 artifact（小端 int32）解码后 == Sample.tokens 逐位相等。
   导出器不转述任何中间对象——token 序列从 GenerationCaptureRecord 的原始
   payload 重建（末轮 prompt + 末轮输出），并逐轮验证"每轮 prompt 是全序列
   前缀 + 每个 mask=1 段逐位等于该轮 output_ids"后才落盘；
2. loss mask：投影 LossMaskSpan 展开的逐 token 0/1 向量 == Sample.loss_mask；
3. rollout logprobs：按 mask=1 段回填的 float64 向量 == Sample.rollout_log_probs
   （工具段 0.0，slime pad 语义）；
4. reward facts：导出记录内嵌 RewardFacts 的 JSON 形态 == 投影 RewardFacts
   逐字段相等，且 Sample.reward == raw_reward；
5. 派生视图互检：Sample.metadata 的 eligibility_report_ref /
   training_eligibility_class == 导出记录同名字段；
6. digest 清单：manifest 里每条 record 的 canonical digest、每个 artifact 的
   sha256、records.jsonl 全文 digest 全部离线重算命中；
7. 幂等：同输入 + 固定 exported_at_utc 重复导出，records.jsonl 与
   manifest.json 逐字节相同（覆盖写、不追加）。
```

### 1.2 结果（两条链全过）

| 链 | 形状 | token 数 | mask=1 数 | token/mask/logprob/reward 逐位 | 幂等重导出 | 资格档 |
| --- | --- | --- | --- | --- | --- | --- |
| dense_2turn | prompt 12 + 生成 10 + 工具 5 + 生成 8（Qwen3-4B 形态，top-p tape，dense 显式声明） | 35 | 18 | 全部一致 | 一致 | offline_or_sft_candidate（S1 封顶） |
| moe_probe_15_16 | prompt 15 + 生成 16（uh_probe 真实形状：offsets 17、routing [30,48,8]） | 31 | 16 | 全部一致 | 一致 | offline_or_sft_candidate（S1 封顶） |

records.jsonl digest（幂等对照锚点，固定 `exported_at_utc=2026-07-08T03:00:00Z`）：dense `sha256:7fe15458…43bec0`，MoE `sha256:87b26230…86fc03`。

**资格门（audit 拒收）**：同一 mock 链注入 infra 评分（`failed_to_grade` + reward=None）→ gate 按 S1-5 地板降到 `audit_only_or_rejected` → 导出器 fail-closed 抛 `[audit_tier_not_exportable]`；同时 schema 层第二道防线成立——`TrainingExportRecord.training_eligibility_class` 的 Literal 里没有 audit 值，"导出 audit 档"不可表示（`tests/contracts/test_export.py::test_audit_tier_is_unrepresentable`）。

## 2. parity-cross：verifiers 路 vs slime 路（治理事实级，token 不比）

### 2.1 判据说明

S0-3 真实 verifiers Trace（`default_subprocess_deepseek.json` 的 `d703bc8d`，真实 deepseek-chat 端点、3 轮工具往返）经 `project_from_verifiers`，与 slime mock 链经 `project_from_slime`，**走同一个 `finalize_rollout` 关口**（grade→project→scan→gate），随后只比治理事实/RewardFacts/eligibility/logprob_source/provenance 的结构与语义——renderer/tokenizer/template 两路不同，token 逐位没有意义（C1 原文）。判据分两半：

```text
共享治理面必须一致（与来源框架无关的语义）：
  - projection.schema_id 同为 rh2.trajectory_projection.v1，gate_version 同值
    （同一个 gate 实现判两路）；扫描器版本一致、扫描结论同为 clean；
  - RewardFacts：reward_scope 同为 trace_level、raw_reward 同为 1.0、
    credit_assignment_strategy 同为 direct_trace_reward、reward_event_refs
    各自恰好指向本路 GradingReport.report_id（gate 逐值对账两路都过）、
    segment_count == 各自 len(branches)；
  - 七维中的 reward_scope / security_and_leakage / clean_grading 两路全 ok。

路径差异必须恰好落在声明的降级点（多一处少一处都算 parity 失败）：
  - logprob_alignment：slime ok；verifiers 失败且理由恰为 [logprob_missing]；
  - loss_mask_integrity：slime ok；verifiers 失败且理由恰为 [no_trainable_tokens]
    （文本中继 token 身份不可证明 -> mask 全 0）；
  - policy_staleness：slime ok；verifiers 失败且理由恰为 [staleness_facts_missing]
    （评测线无训练后端握手事实，fail-closed）；
  - logprob_source/provenance：slime 分支 aligned_per_token + LogprobProvenance
    (engine=sglang/0.5.9)；verifiers 分支 missing + None（schema 强制搭配，
    伪造出处不可表示）；
  - tape 声明：slime top_p_kept_token_ids / not_applicable_dense_model；
    verifiers not_captured_text_relay（top_p=None）/ not_captured_text_relay；
  - capture 回链：slime 每分支非空且全 complete；verifiers 恒空（无捕获 ->
    schema 链保证 mask=1 不可表示）；
  - 哨兵值：verifiers 投影 renderer_cls_name=VerifiersEvalRelayNoRenderer、
    tokenizer_name=eval_relay_untokenized:deepseek-chat（不伪装真实 renderer）。
```

### 2.2 结果（全过）

```text
共享治理面：reward_scope / security_and_leakage / clean_grading 两路全 ok；
            RewardFacts 语义逐字段一致（数值 1.0，出处各指本路评分报告）。
预期分歧：  logprob_alignment=[logprob_missing]、
            loss_mask_integrity=[no_trainable_tokens]、
            policy_staleness=[staleness_facts_missing]，不多不少。
资格结论：  slime = offline_or_sft_candidate（含 s1_default_ceiling_offline）；
            verifiers = audit_only_or_rejected。
导出面：    verifiers 文本中继轨迹送导出器 -> [audit_tier_not_exportable] 拒收
            （评测线样本进不了训练导出，资格门跨路径生效）。
```

## 3. 6 份真实 toy dump 投影结果（EvalClient 显式降级路径）

12 条 Trace 全部可投影，每条的降级标注逐项核对通过（`not_captured_text_relay` ×2、`logprob=missing`、mask 全 0 且采样段理由恒为 `token_capture_unavailable_downgraded`、无 capture 回链、renderer/tokenizer 哨兵值）；采样段 token 计数之和与 dump 顶层 `num_output_tokens` 逐条相等（外部一致性核对），reward 与 summary 逐条相等。计数座标系来自 provider usage 差分（`input_tokens = prompt_tokens + cached_input_tokens`，deepseek 的 cache 计入实测生效）。

| dump | trace | prompt | response | 采样 token | reward |
| --- | --- | --- | --- | --- | --- |
| default_docker | f7ef95fb / 2d9c3e10 | 101 / 114 | 91 / 91 | 48 / 48 | 1.0 / 1.0 |
| default_subprocess | 2bee049d / e688e2f2 | 101 / 114 | 91 / 91 | 48 / 48 | 1.0 / 1.0 |
| default_subprocess_deepseek | d703bc8d / fef9ecc7 | 484 / 498 | 150 / 278 | 124 / 224 | 1.0 / 1.0 |
| default_subprocess_maxturns1 | 21d4da72 / dbb6fa74 | 101 / 114 | 24 / 24 | 24 / 24 | 1.0 / 1.0 |
| null_docker | 2f4d8f56 / 76b542ac | 53 / 66 | 24 / 24 | 24 / 24 | 0.0 / 0.0 |
| null_subprocess | 0d753188 / 155f7dcd | 53 / 66 | 24 / 24 | 24 / 24 | 0.0 / 0.0 |

第 7 份 dump（`default_subprocess_deepseek_attempt.json`，缺 key 的 error 轨迹，nodes=0）：两条 Trace 均 fail-closed 拒收，reason_code=`trace_has_no_branches`——error 轨迹只可审计、不产投影，这是拒收路径的真实样本而非合成用例。

## 4. 发现与边界

1. **parity-core 当场抓出 fixture 级 logprob 漂移**：脚本首版 MoE 链镜像了 S1-6 测试 fixture 的形态——叶链 `rollout_log_probs` 用 `-(i+1)*0.03125` 系列、mock SGLang 响应用 `-(i+1)*0.05` 系列（两处数值不同源）。S1-6 测试不比数值所以无害，parity-core 的逐位比对第一次运行就拒绝通过；脚本侧已改为同源。真实链路里 TrajectoryManager 与 capture 钩子读的是同一份 meta_info，不会出现这种分叉——这恰好演示了 parity-core 的探测能力（建议 S1-9 收口时顺手把 `tests/adapters/test_slime_generate.py` 的 MoE 叶链 logprobs 改成与响应同源，消除 fixture 内部不一致）。
2. **EvalClient 轨迹在 S1 语义下恒为 audit 档**：mask 全 0 → gate 的 `loss_mask_integrity` 维 `no_trainable_tokens` 失败（地板 audit）。因此文本中继轨迹永远进不了训练导出；S1 的 SFT 候选唯一来源是 slime 主线（token-faithful）。若未来要把"文本级 SFT 候选"（重新 tokenize 的行为克隆）纳入导出面，需要同时动 gate 维度语义与 `ExportTokenFidelity`（v1 只有 token_faithful），属显式升级不是配置开关。
3. **多分支（compaction）eval 轨迹显式不支持**：文本中继没有 token 级 fork 点，`CompactedSubTraceLineage.fork_point_token_index` 无法诚实构造，`project_from_verifiers` 对多叶 Trace 抛 `eval_relay_multi_branch_not_supported`（6 份 dump 均单分支，未触发）；token-faithful 的 verifiers 路径（TrainClient + capture sidecar）同样显式不在 S1-8 范围（节点带 token 字段即拒收，不静默降级）。
4. **导出器对 compaction 分支同样拒绝**（`lineage_reconstruction_not_supported`）：重放前缀的 token 重建需要树侧血缘，S1-8 的重建规则只对线性追加式多轮成立（末轮 prompt 是全序列前缀，逐轮前缀校验兜底）。
