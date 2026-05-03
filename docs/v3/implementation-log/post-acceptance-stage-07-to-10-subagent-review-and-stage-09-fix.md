# V3 追溯实施日志：阶段 7 至阶段 10 子代理智能体补审与阶段 9 修复

## 目标

补齐阶段 7、阶段 8、阶段 9 和阶段 10 在原始实施时因为 `agent thread limit reached` 而没有完成子代理智能体审查的流程缺口。该补充不是新增阶段，也不是扩大第三版（V3）功能范围；它是对既有阶段验收证据的追溯审计和必要修复。

## 实施内容

本次补充完成了以下工作：

- 清理此前不再需要的旧子代理智能体线程。
- 为阶段 7、阶段 8、阶段 9 和阶段 10 分别创建只读子代理智能体，进行追溯审查。
- 根据阶段 9 追溯审查发现，修复 context compaction 报告中的 `kept_tool_result_ids` 时间一致性问题。
- 为阶段 9 新增两个 inspect 负例测试，分别覆盖未来 tool result 注入和 content replacement state hash drift。
- 重新生成阶段 9 context diagnostics 机器产物。
- 重新生成阶段 10 failure diagnostics 机器产物，使其绑定修复后的阶段 9 context report 和 long rollout report。
- 保存追溯审查记录到 `docs/v3/review/implementation/stage-07-to-10-retrospective-subagent-review.md`。

## 主要修改文件

- `src/repo_harness/v3_context_diagnostics.py`
- `tests/integration/test_context_compaction_v3.py`
- `docs/v3/review/implementation/stage-07-to-10-retrospective-subagent-review.md`
- `docs/v3/implementation-log/post-acceptance-stage-07-to-10-subagent-review-and-stage-09-fix.md`

## 机器产物

阶段 9 修复后产物：

- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/`
- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json`
- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json`

阶段 10 刷新后产物：

- `runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/`
- `runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json`
- `runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_distribution_report.json`

## 验证命令和结果

- `PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v3_context_diagnostics.py`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_context_compaction_v3.py -q`：`5 passed`。
- `PATH=.venv/bin:$PATH repo-harness build-v3-context-diagnostics --output-dir runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-context-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json --assert-consistent`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-long-rollout-diagnostics runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json --assert-complete`：通过。
- `PATH=.venv/bin:$PATH repo-harness build-v3-reward-diagnostics --run-dir runs/v3-stage-10-failure-diagnostics-20260502T234500Z/input_run --output-dir runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix --context-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json --long-rollout-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix --core-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_distribution_report.json --assert-core-complete`：通过。

## 正例证据

- 修复后的阶段 9 context report 中，`kept_tool_result_ids` 从当前 context revision 的 prepared messages 计算，不再引用未来工具结果。
- `inspect-context-report` 会重新读取 prepared messages artifact 和 content replacement state artifact，而不是只信任 summary 字段。
- 阶段 10 已重新绑定修复后的阶段 9 context report 和 long rollout report。
- 阶段 7、阶段 8 和阶段 10 的追溯审查没有发现新的 P1 或 P2 阻断项。

## 负例证据

- `test_inspect_context_report_rejects_future_kept_tool_result` 会篡改报告，把未来 tool result 放入当前 revision 的 `kept_tool_result_ids`，inspect 必须拒绝。
- `test_inspect_context_report_rejects_content_replacement_state_hash_drift` 会篡改 `content_replacement_state_hash`，inspect 必须拒绝。

## 允许降级项

- 阶段 8 的正式机器产物仍只演示 baseline interrupt injection；agent_loop 和 final_verifier interrupt injection 由代码和测试覆盖，记录为阶段范围内允许的诊断增强项。
- 阶段 10 的 audit-only input run 可以包含 reward 和 verifier 相关审计标记，但这些标记不得进入模型可见上下文或正式训练 payload。

## 禁止降级项

- 不允许继续使用旧的阶段 9 context compaction 报告作为最终验收输入。
- 不允许在阶段 9 报告中把未来 tool result 计入当前 context revision 的 kept ids。
- 不允许只依赖 summary 字段检查 context compaction；inspect 必须重新读取 artifact refs 和 sha256。
- 不允许因为子代理智能体线程清理问题而永久跳过阶段审查。后续如果创建失败，必须先关闭旧线程并重试。

## 已知限制

本次补充没有改变第三版（V3）的能力范围。它没有新增公开 SWE-Bench Lite 榜单复现能力，没有改变 provider 主线，也没有把诊断性 failed run 变成 accepted run。

## 设计偏离

没有偏离 `docs/v3/implementation-plan.md` 的阶段目标。本次补充是在最终验收后发现流程缺口时进行的审计修复，因此会重新构建最终验收输入、最终验收报告和验收包，避免旧验收证据继续引用存在审计缺陷的阶段 9 报告。

## 审查结论

追溯子代理智能体审查确认：阶段 7、阶段 8 和阶段 10 没有新的阻断项；阶段 9 的 P2 已经修复并复审通过。当前可以进入最终验收证据刷新。
