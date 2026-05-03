# 第三版（V3）阶段 13 实施审查

## 审查范围

本次审查由 subagent `Lorentz` 以只读方式执行，覆盖阶段 13 的最终验收输入绑定、预验收证据、最终 run selection、最终 acceptance report、post-acceptance 文档和 acceptance bundle。

审查对象：

- `runs/v3-final-pre-acceptance-20260503T034631Z/pre_acceptance_command_log.jsonl`
- `runs/v3-final-pre-acceptance-20260503T034631Z/manifests/pre_acceptance_documentation_manifest.json`
- `runs/v3-final-acceptance-20260503T034631Z/run_selection_manifest.json`
- `runs/v3-final-acceptance-20260503T034631Z/v3_acceptance_inputs.json`
- `runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json`
- `docs/v3/final-acceptance.md`
- `docs/v3/walkthrough.md`
- `docs/v3/implementation-log/13-stage-13-final-acceptance-and-docs.md`

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

## 验证结果

- `PATH=.venv/bin:$PATH python -m pytest -q`：通过，`447 passed in 201.53s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3`：通过，accepted。
- `PATH=.venv/bin:$PATH repo-harness inspect-trajectory-store runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 --assert-readable`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-tool-contract runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit runs/v3-stage-11-export-audit-20260503T030000Z --manifest runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json --audit-report runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json --assert-clean`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-acceptance-20260503T034631Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`：通过。

## 结论

未发现 P1、P2 或 P3 遗留问题。subagent `Lorentz` 明确确认四份 post-acceptance 文档与机器产物一致，`v3_acceptance_report.json` 没有把 post-acceptance 文档作为输入，`acceptance_bundle_manifest.json` 已绑定四份 post-acceptance 文档，最终 run selection 没有使用失败的 SWE-Bench-like run。阶段 13 可以收口，第三版（V3）最终验收报告和验收包均可作为最终 acceptance evidence。
