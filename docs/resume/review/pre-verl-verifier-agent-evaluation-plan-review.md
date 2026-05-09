# 接入 verl 前评测计划审查记录

## 审查对象

```text
docs/resume/pre-verl-verifier-agent-evaluation-plan.md
```

## 审查方式

本审查由 sub agent 执行只读复核。审查过程中没有修改任何文件。

审查重点包括：

- 是否将任务数量修正为 23 个 SWE-Bench Lite development instances，而不是误写为 33 个。
- 是否准确引用当前 V5 状态，包括 `core_acceptance` 已通过、`resume_ready_acceptance` 仍然 blocked、12 个 V5 任务、7 条真实 DeepSeek provider run、1 条 strict final verifier accepted run、2 条 real provider trainable records，以及 OpenAI / DeepSeek provider-axis supplemental proof。
- 是否避免公开 leaderboard、完整 SWE-Bench 复现、已经训练出 coding agent、已经接入 `verl` 等过强表述。
- 是否覆盖 verifier correctness 所需的 gold patch replay、no-op fail、invalid patch fail、strict patch replay、verifier determinism、visibility scan 和 evidence hash 检查。
- 是否覆盖 agent evaluation 所需的明确分母、失败分类、provider 成本、延迟指标和 provider-axis comparison 边界。
- 是否补齐最终 evidence bundle、command lineage 和 public-safe scan 的机器产物。

## 第一轮审查发现

第一轮审查没有发现 P1 问题，但发现 2 个 P2 和 2 个 P3。

### P2：缺少 Docker phase coverage matrix 产物

第一版计划记录了 environment setup failure、verifier time 和 episode time，但没有明确把 `Docker phase coverage matrix` 落成机器产物。该问题会削弱报告对 executable repository environment 可靠性的证明。

修复结果：

- 已新增 `pre_verl_docker_phase_coverage_matrix.json`。
- 已要求覆盖 `source_checkout_or_restore`、`dependency_install_or_cache_restore`、`baseline_test_patch_apply`、`candidate_patch_apply`、`verifier_command_run`、`artifact_collection` 和 `workspace_cleanup`。
- 已新增建议 inspect 命令 `repo-harness inspect-pre-verl-docker-phase-coverage PRE_VERL_DOCKER_PHASE_COVERAGE_MATRIX --assert-docker-phase-coverage-complete`。

### P2：最终证据包缺少 command lineage 和 public-safe scan 机器闭环

第一版计划列出了 evaluation inputs、reference integrity report、bundle manifest、final command log 和 public demo index，但没有明确要求 bundle command lineage report、build bundle command log entry、inspect bundle command log entry 和 public-safe scan report。

修复结果：

- 已新增 `pre_verl_evaluation_bundle_command_lineage_report.json`。
- 已新增 `build_pre_verl_evaluation_bundle_command_log_entry.json`。
- 已新增 `inspect_pre_verl_evaluation_bundle_command_log_entry.json`。
- 已新增 `pre_verl_public_safe_scan_report.json`。
- 已要求 bundle build entry 和 bundle inspect entry 都必须指向当前最终 bundle，不能指向 previous bundle 或 pre-final bundle。

### P3：阶段 B 的模型矩阵没有完整展开

第一版以 DeepSeek V4 Flash、DeepSeek V4 Pro 和余额允许时的 OpenAI 小规模对比为主，没有明确说明本地 coder model 是第二轮目标还是 blocked。

修复结果：

- 已将 DeepSeek V4 Pro 标记为强 API model。
- 已将 DeepSeek V4 Flash 标记为中等或低成本 API model。
- 已将 OpenAI 标记为余额允许时的 provider-axis supplemental proof。
- 已将本地 coder model 标记为第二轮目标，未准备好时必须写入 `blocked_local_model_runtime_not_ready`。

### P3：accepted rate 分母字段不够精确

第一版分母说明容易让 diagnostic-only provider run 被误纳入统计。

修复结果：

- 已将分母字段命名为 `real_provider_terminal_outcome_denominator`。
- 已明确排除 diagnostic-only、structured skip、mock、replay、fallback success、synthetic-safe stress record、credential missing skip、adapter not implemented skip 和 cost-limited structured skip。

## 第二轮审查结论

第二轮 sub agent 复核确认：

- P1：无。
- P2：无。
- P3：无。
- 第一轮 2 个 P2 和 2 个 P3 均已关闭。
- 当前计划允许通过检查。

## 允许进入下一步

允许将该计划作为接入 `verl` 之前的可执行实施计划，用于后续生成：

- RepoHarness 验证器可信度报告。
- RepoHarness 智能体评测报告。
- 接入 `verl` 前的 public-safe 展示包。
- 接入 `verl` 前的 evaluation bundle 和 command lineage evidence。

## 补充审查与再次修订

后续补充审查认为，上一版计划方向正确，但仍更接近“pre-verl 评测实施草案”，还需要补齐若干机器可检查的不变量，才能作为完整的 pre-verl 测评关口。

本次已根据补充审查修订计划正文，主要补充如下：

- 将当前 V5 基线事实改为“与当前已绑定验收材料一致”，并明确最终仍以显式路径、sha256、size_bytes 和 command log 为准。
- 将 23 个 SWE-Bench Lite development instances 和 50 个 curated SWE-Bench Lite tasks 明确写成 RepoHarness 自定义冻结评测子集，不构成 SWE-Bench Lite 官方分数，也不得和公开 leaderboard 直接比较。
- 新增 `planned_denominator`、`bound_task_denominator`、`runnable_denominator`、`verifier_correctness_denominator`、`agent_evaluation_planned_denominator`、`real_provider_terminal_outcome_denominator` 和 `trainable_export_eligible_denominator`。
- 将 pre-verl inspect 断言从含义过宽的 complete 断言拆成 `--assert-baseline-complete`、`--assert-task-freeze-complete`、`--assert-verifier-correctness-complete`、`--assert-agent-evaluation-pilot-complete` 和 `--assert-verl-ready` 等更精确口径。
- 将 verifier correctness 的“尽量运行”改为必需检查或结构化豁免，并补充 `parser_confidence_mean`、`low_parser_confidence_count`、`patch_apply_failed_count`、`pass_to_pass_regression_count` 和 `final_verifier_boundary_missing_count`。
- 新增 Agent Runtime Invariant Audit 阶段，产物包括 `pre_verl_agent_runtime_trace_report.json`、`pre_verl_tool_contract_matrix.json`、`pre_verl_permission_boundary_report.json`、`pre_verl_context_compaction_stress_report.json` 和 `pre_verl_transcript_diagnostics_report.json`。
- 新增 Training Export Audit 阶段，产物包括 `pre_verl_export_result_pack_manifest.json`、`pre_verl_sft_export.jsonl`、`pre_verl_rl_rollout_export.jsonl`、`pre_verl_failure_dataset.jsonl`、`pre_verl_preference_pair_blocked_report.json`、`pre_verl_reward_source_taxonomy_report.json` 和 `pre_verl_reward_boundary_audit_report.json`。
- 在 Agent Evaluation 阶段补充 baseline、provider、scaffold、budget 受控轴，要求 provider、scaffold 和 budget 对比优先使用 paired comparison，不满足条件时只能标记为 observation result。
- 补充 Wilson 或 bootstrap 置信区间、provider 调用预算、成本上限、token 上限、timeout、retry policy、model exact id、temperature、top_p、seed policy、provider registry snapshot、dependency cache 和 environment ref。
- 扩大泄漏扫描范围，覆盖 adapter-visible input、prepared messages、model-visible transcript、trajectory observations、tool results、context compaction summary、stdout、stderr、trainable payload、failure dataset 和 public-safe 展示包。
- 新增 `pre_verl_resume_claim_gate_report.json`、`pre_verl_result_summary_table.json`、`pre_verl_interview_qa.md`、`pre_verl_interview_qa_evidence.json`、`pre_verl_demo_card.md` 和 `pre_verl_demo_card.json`，要求每个可展示数字都由 claim gate 绑定 evidence ref、分母和 sha256。

补充修订后，计划定位从“实施草案”升级为“接入 `verl` 前的完整评测关口设计”。正式实施时仍需要新增或复用对应 `build-pre-verl-*` 和 `inspect-pre-verl-*` 命令；在这些命令尚未落地之前，不得把计划中的命令描述为当前仓库已经可执行的入口。
