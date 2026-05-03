# 第三版（V3）阶段 13：最终验收和文档收口

## 目标

阶段 13 的目标是执行最终预验收、构建显式 `RUN_SELECTION_MANIFEST`、构建 `ACCEPTANCE_INPUTS`、生成新的 `v3_acceptance_report.json`、运行 `inspect-v3-acceptance --assert-complete`，然后在报告生成之后编写 post-acceptance 文档并构建验收包。

## 实现内容

- 运行并固化全量 `python -m pytest -q` 证据。
- 运行并固化第二版（V2）最终验收回归证据。
- 生成预验收命令日志 `pre_acceptance_command_log.jsonl`，绑定命令输入、输出、退出码和 sha256。
- 生成预验收文档清单，绑定范围文档、实施计划、阶段 0 至阶段 12 的 implementation log 和 implementation review。
- 补充运行一个 accepted 的 SWE-Bench-like Agent Loop 任务：`sympy__sympy-24909`。该运行使用固定本地 source checkout 和 adapter-visible 问题描述推导的补丁，final verifier 在 evaluator-only 侧执行。
- 构建最终 `run_selection_manifest.json`。
- 构建最终 `v3_acceptance_inputs.json`。
- 构建最终 `v3_acceptance_report.json` 并运行 `inspect-v3-acceptance --assert-complete`。
- 编写 `docs/v3/final-acceptance.md` 和 `docs/v3/walkthrough.md`。
- 安排 subagent `Lorentz` 执行只读审查，并将审查结论写入阶段 13 审查记录。
- 构建并检查 `acceptance_bundle_manifest.json`。

## 主要文件

- `docs/v3/final-acceptance.md`
- `docs/v3/walkthrough.md`
- `docs/v3/implementation-log/13-stage-13-final-acceptance-and-docs.md`
- `docs/v3/review/implementation/stage-13-review.md`

## 机器产物

- `runs/v3-final-pre-acceptance-20260503T034631Z/evidence/`
- `runs/v3-final-pre-acceptance-20260503T034631Z/pre_acceptance_command_log.jsonl`
- `runs/v3-final-pre-acceptance-20260503T034631Z/manifests/pre_acceptance_documentation_manifest.json`
- `runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3/`
- `runs/v3-final-acceptance-20260503T034631Z/run_selection_manifest.json`
- `runs/v3-final-acceptance-20260503T034631Z/v3_acceptance_inputs.json`
- `runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json`
- `runs/v3-final-acceptance-20260503T034631Z/acceptance/acceptance_command_log.jsonl`
- `runs/v3-final-acceptance-20260503T034631Z/acceptance/acceptance_bundle_manifest.json`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m pytest -q`：通过，`447 passed in 201.53s`。
- `PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete`：通过，状态为 `passed`。
- `PATH=.venv/bin:$PATH repo-harness run-task ... --run-id v3_stage_13_sympy__sympy-24909_public_issue_patch_v3`：通过，运行目录生成成功。
- `PATH=.venv/bin:$PATH repo-harness inspect-run runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3`：通过，`run_outcome=success`，`final_verifier_status=accepted`。
- `PATH=.venv/bin:$PATH repo-harness inspect-trajectory-store runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 --assert-readable`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-tool-contract runs/v3-final-swebench-agent-loop-20260503T035615Z/agent_loop_runs/v3_stage_13_sympy__sympy-24909_public_issue_patch_v3 --assert-frozen`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-swebench-like runs/v3-stage-06-swebench-like-20260502T191500Z --manifest runs/v3-stage-06-swebench-like-20260502T191500Z/swebench_like_task_manifest.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-export-audit runs/v3-stage-11-export-audit-20260503T030000Z --manifest runs/v3-stage-11-export-audit-20260503T030000Z/export_manifest.json --audit-report runs/v3-stage-11-export-audit-20260503T030000Z/audit_report.json --assert-clean`：通过，根状态为 `passed_with_warnings`，inspect 判定为 clean。
- `PATH=.venv/bin:$PATH repo-harness build-v3-run-selection-manifest ...`：通过。
- `PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-inputs ...`：通过。
- `PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-report ...`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-acceptance-20260503T034631Z/acceptance/v3_acceptance_report.json --assert-complete`：通过，报告状态为 `passed`。
- `PATH=.venv/bin:$PATH repo-harness build-v3-acceptance-bundle ...`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-acceptance-20260503T034631Z/acceptance/acceptance_bundle_manifest.json --assert-immutable`：通过。

## 正例证据

- 最终验收报告重新读取 input manifest、run selection manifest、command log 和 contamination scan evidence 后仍然通过。
- 最终 run selection 中的 `swebench_like` 角色绑定 accepted 的 `sympy__sympy-24909` Agent Loop run。
- 预验收命令日志绑定了全量测试、第二版回归和最终 SWE-Bench-like Agent Loop run 的输入与输出。
- 第二版（V2）最终验收回归保持通过。
- 第三版 export audit 重新 inspect 通过。

## 负例证据

阶段 12 已覆盖最终验收 builder 和 inspect 的负例测试，包括 summary 篡改、evidence ref 删除、sha256 修改、旧目录替换、官方 harness report 注入、prompt 污染、checkpoint 污染、context compaction report 污染、adapter input 出现 gold patch prediction、缺失轨迹文件、ArtifactRef sha256 不匹配、ToolContractSnapshot 缺失、export observation 与 prepared messages 不匹配、`ACCEPTANCE_INPUTS` 缺少必需类别、报告引用外部 evidence、documentation ref bundle 后变化、command log 与 input manifest 不一致，以及 credential-gated real provider skip 被伪装成 accepted run。

阶段 13 额外保留了两个 SWE-Bench-like diagnostic failed attempts，用于说明最终 accepted run 之前的根因调试过程。它们没有进入最终 run selection。

## 允许降级项

- export audit 可以存在 `passed_with_warnings`，前提是样本级 audit 明确过滤不可训练或失败运行，并且 `inspect-v3-export-audit --assert-clean` 通过。
- 历史 diagnostic failed run 可以保留为审计证据，但不能作为最终 success-required role。

## 禁止降级项

- 不允许复用阶段 12 的 inspector fixture 当作最终 SWE-Bench-like evidence。
- 不允许把失败的 SWE-Bench-like run 标记为 accepted。
- 不允许覆盖已有 acceptance directory。
- 不允许把 post-acceptance 文档写入 `v3_acceptance_report.json` 的输入清单。

## 已知限制

- `inspect-workspace-backend --status-file` 对 accepted SWE-Bench-like Agent Loop run 的 legacy `docker_stage_status.json` 仍报告 final verifier 细分阶段缺失；该 run 的 final verifier evidence 由 SWE-Bench-like verifier 产物和 `inspect-swebench-like` 覆盖，最终 run selection 通过 trajectory store 和 tool contract 检查。真实 repository-level Docker backend status 仍由阶段 7 accepted run 覆盖。
- 第三版（V3）不声明公开 SWE-Bench Lite 榜单可比。

## 是否偏离设计文档

没有偏离第三版范围和实施计划。阶段 13 额外补跑 accepted SWE-Bench-like Agent Loop run，是为了满足最终 run selection 不能使用阶段 12 inspector fixture 的审查要求。

## 审查结论

阶段 13 由 subagent `Lorentz` 执行只读审查，结论写入 `docs/v3/review/implementation/stage-13-review.md`。审查未发现 P1、P2 或 P3 问题，允许完成第三版最终收口。
