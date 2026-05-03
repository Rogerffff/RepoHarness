# 第三版（V3）阶段 13 实施审查

## 审查范围

本次审查最初由子代理智能体 `Lorentz` 以只读方式执行，覆盖阶段 13 的最终验收输入绑定、预验收证据、最终 run selection、最终 acceptance report、post-acceptance 文档和 acceptance bundle。

阶段 13 原始审查之后，用户指出阶段 7 至阶段 10 的原始阶段审查因为子代理智能体线程没有及时清理而退回自审。因此本文件追加记录补充状态：阶段 7 至阶段 10 已完成追溯子代理智能体审查，阶段 9 发现的 P2 已修复，最终验收报告已经使用修复后的阶段 9 产物和刷新后的阶段 10 产物重新构建。

审查对象包括原始阶段 13 证据和补充刷新后的新证据：

- `runs/v3-final-pre-acceptance-20260503T034631Z/pre_acceptance_command_log.jsonl`
- `runs/v3-final-pre-acceptance-20260503T034631Z/manifests/pre_acceptance_documentation_manifest.json`
- `runs/v3-final-acceptance-20260503T034631Z/run_selection_manifest.json`
- `runs/v3-final-acceptance-20260503T034631Z/v3_acceptance_inputs.json`
- `runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json`
- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json`
- `runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json`
- `runs/v3-final-pre-acceptance-20260503T043025Z/pre_acceptance_command_log.jsonl`
- `runs/v3-final-pre-acceptance-20260503T043025Z/manifests/pre_acceptance_documentation_manifest.json`
- `runs/v3-final-acceptance-20260503T043025Z/run_selection_manifest.json`
- `runs/v3-final-acceptance-20260503T043025Z/v3_acceptance_inputs.json`
- `runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json`
- `docs/v3/final-acceptance.md`
- `docs/v3/walkthrough.md`
- `docs/v3/implementation-log/13-stage-13-final-acceptance-and-docs.md`
- `docs/v3/review/implementation/stage-07-to-10-retrospective-subagent-review.md`

## 审查维度

- 验收报告是否只读取显式输入路径，不扫描 latest run。
- 预验收测试证据是否在 `ACCEPTANCE_DIR` 创建前写入独立目录。
- 全量测试和第二版（V2）回归是否有 stdout、stderr、exit code 和 sha256 证据。
- `RUN_SELECTION_MANIFEST` 是否覆盖必需角色，并且 success-required role 未绑定失败运行。
- `swebench_like` role 是否绑定 accepted 的第三版 Agent Loop run，而不是阶段 12 inspector fixture。
- credential-gated real provider 是否绑定真实 provider accepted-with-credentials evidence，而不是 skip 或 replay/mock evidence。
- `ACCEPTANCE_INPUTS` 是否包含必需类别和阶段 0 至阶段 12 已冻结文档。
- `v3_acceptance_report.json` 是否由新的 acceptance directory 生成。
- post-acceptance 文档是否没有反向进入 `v3_acceptance_report.json` 输入。
- acceptance bundle 是否重新计算并绑定 post-acceptance 文档 sha256。
- 阶段 7 至阶段 10 追溯审查是否补齐原始自审缺口。
- 阶段 9 修复后，context compaction report 是否不再把未来 tool result 计入当前 revision 的 kept ids。
- 新的最终 run selection 是否绑定修复后的阶段 9 和刷新后的阶段 10 产物。

## 发现和修复记录

### P2：最终 run selection 不能复用阶段 12 inspector fixture

阶段 12 日志已经明确说明，阶段 12 的 `swebench_like` role 使用的是 command-level acceptance inspector fixture，不能作为最终 SWE-Bench-like acceptance evidence。阶段 13 因此补跑 `sympy__sympy-24909` 的第三版 Agent Loop run。

修复：

- 生成 `runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3/`。
- 该 run 进入 `single_shot_patch` Agent Loop，最终 `run_outcome=success`，`final_verifier_status=accepted`。
- 最终 `run_selection_manifest.json` 的 `swebench_like` role 绑定该 run。

### P3：补跑过程中保留了两个诊断失败 run

第一次补丁语义不完整，第二次补丁 diff 格式无效。两个失败 run 未进入最终 run selection，保留在同一实验目录中作为诊断证据。

修复：

- 根据结构化 verifier evidence 和补丁应用输出定位问题。
- 第三次补跑使用有效 unified diff，并通过 final verifier。

### P2：阶段 9 context compaction report 的 kept ids 引用未来 tool result

阶段 7 至阶段 10 的追溯子代理智能体审查发现，旧阶段 9 `context_compaction_report.json` 的第二个 context revision 把未来才出现的 `call_long_output_repeat_result` 计入 `kept_tool_result_ids`。这说明报告生成逻辑从完整 transcript 计算 kept ids，而不是从当前 revision 的 prepared messages 计算。

修复：

- `src/repo_harness/v3_context_diagnostics.py` 改为从当前 revision 的 prepared messages 计算 `kept_tool_result_ids`。
- `inspect-context-report` 增加 prepared messages 反查，拒绝报告中出现未来 tool result。
- `inspect-context-report` 增加 `content_replacement_state_ref` payload 读取和 `content_replacement_state_hash` 校验。
- 新增负例测试 `test_inspect_context_report_rejects_future_kept_tool_result` 和 `test_inspect_context_report_rejects_content_replacement_state_hash_drift`。
- 重新生成 `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/`。
- 重新生成 `runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/`，避免阶段 10 继续引用旧阶段 9 报告。

## 验证结果

- `PATH=.venv/bin:$PATH python -m pytest -q`：原始阶段 13 通过，`447 passed in 201.53s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：原始阶段 13 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3`：通过，accepted。
- `PATH=.venv/bin:$PATH repo-harness inspect-trajectory-store runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 --assert-readable`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-tool-contract runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit runs/v3-stage-11-export-audit-20260503T030000Z --manifest runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json --audit-report runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json --assert-clean`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json --assert-complete`：原始阶段 13 通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-acceptance-20260503T034631Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`：原始阶段 13 通过。
- `PATH=.venv/bin:$PATH python -m pytest -q`：补充刷新后重新运行，通过，`449 passed in 236.72s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：补充刷新后重新运行，通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-context-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json --assert-consistent`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-long-rollout-diagnostics runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix --core-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_distribution_report.json --assert-core-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-acceptance-20260503T043025Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`：通过。

## 结论

原始阶段 13 审查未发现 P1、P2 或 P3 遗留问题。后续追溯子代理智能体审查发现的阶段 9 P2 已经修复并重新验收。新的 `runs/v3-final-acceptance-20260503T043025Z/acceptance/v3_acceptance_report.json` 没有把 post-acceptance 文档作为输入，最终 run selection 没有使用失败的 SWE-Bench-like run，也没有继续使用旧阶段 9 context compaction 报告。阶段 13 可以维持收口结论，第三版（V3）新的最终验收报告和验收包均可作为最终 acceptance evidence。
