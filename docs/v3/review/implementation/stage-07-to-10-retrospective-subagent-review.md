# V3 阶段 7 至阶段 10 追溯子代理智能体审查记录

## 审查背景

阶段 7、阶段 8、阶段 9 和阶段 10 的原始阶段审查文件均记录了一个过程性限制：当时尝试创建只读子代理智能体时，环境返回 `agent thread limit reached`，因此改为等价独立只读自审。用户在最终验收后指出，该限制来源于此前子代理智能体线程没有及时清理，不应让阶段 7 至阶段 10 永久停留在自审状态。

本文件补充记录追溯审查。原始阶段审查文件不重写历史过程，本文件作为追加审查证据，说明旧线程清理、重新创建子代理智能体、发现项、修复项、复审结论和是否仍允许当前第三版（V3）验收证据继续使用。

## 执行方式

已关闭此前不再需要的子代理智能体线程，然后为阶段 7 至阶段 10 分别创建新的只读审查子代理智能体：

- 阶段 7：只读审查 Agent Loop 集成、Docker backend evidence、final verifier evidence、tool call 配对和污染检查。
- 阶段 8：只读审查 Experiment Runner 状态机、checkpoint、resume、interrupt injection 和 inspect evidence。
- 阶段 9：只读审查 context compaction、prepared messages 绑定、tool observation 替换、long rollout diagnostics 和 inspect 负例覆盖。
- 阶段 10：只读审查 core failure diagnostics、reward metadata、supporting context evidence、distribution report 和污染边界。

阶段 9 初次追溯审查发现 P2 后，又创建独立只读复审子代理智能体，专门复查阶段 9 修复后的代码、测试、机器产物和 inspect 行为。

## 阶段 7 审查结论

阶段 7 未发现新的 P1、P2 或 P3 阻断项。

审查确认：

- 真实仓库运行仍然通过常规 Agent Loop、Docker backend 和 final verifier，最终 `accepted=true`。
- SWE-Bench-like 诊断运行没有被冒充为 accepted evidence；它只证明 Agent Loop、final patch freeze、strict replay 和 RepoHarness 自有 final verifier 通路。
- Stage 7 contamination scan 没有发现 evaluator-only patch、raw `test_patch`、raw `FAIL_TO_PASS`、raw `PASS_TO_PASS`、official harness report、provider raw marker、credential marker 或本机绝对路径进入模型可见 surface。
- tool call 与 tool result 配对完整。
- Docker backend status 是真实 Docker backend evidence，不是第二版（V2）interface-only 路径。

边界说明：

- SWE-Bench-like 阶段 7 运行是诊断性 failed run，仍然不能作为最终 accepted SWE-Bench-like evidence。最终验收已绑定阶段 13 生成的 accepted SWE-Bench-like Agent Loop run。

## 阶段 8 审查结论

阶段 8 未发现新的 P1 或 P2 阻断项。

审查确认：

- Experiment Runner 支持 `pending`、`running`、`completed`、`failed`、`skipped` 和 `interrupted` schema 状态。
- resume manifest 能跳过 completed run，并恢复 pending 或 interrupted run。
- checkpoint inspect 会拒绝在最终 `run_metadata.json` 写入前出现 `run_metadata_ref`。
- baseline、agent_loop 和 final_verifier 三个 interrupt injection 入口在代码层面存在；阶段机器产物正式演示了 baseline interrupt 路径。

保留的 P3 范围说明：

- 阶段 8 的正式机器产物只演示 baseline interrupt injection。代码和测试覆盖了其他固定注入点，但没有为每一个状态组合都生成同等重量的阶段机器产物。该项是阶段范围内允许保留的诊断增强项，不阻断阶段 9 或最终验收。

## 阶段 9 初次审查发现

阶段 9 初次追溯审查发现一个 P2：

- `context_compaction_report.json` 的第二个 context revision 中，`kept_tool_result_ids` 包含 `call_long_output_repeat_result`。
- 该 tool result 属于未来的工具观察，在该 revision 对应的 `prepared_messages` 中尚不存在。
- `inspect-context-report --assert-consistent` 当时只校验 prepared messages sha256、model input hash 和 observation 替换结果，没有重新根据当前 revision 的 prepared messages 计算 `kept_tool_result_ids`，因此没有捕获该时间一致性问题。

风险判断：

- 该问题不会把隐藏 evaluator-only 材料放入模型可见上下文，但会让 context compaction 报告的工具结果保留集合不再严格对应当前 revision。
- 第三版（V3）要求 context compaction 具备可审计性，因此该问题必须修复后才能重新收口验收。

同时记录一个 P3：

- inspect 当时没有读取 `content_replacement_state_ref` 指向的 state payload 来复算 `content_replacement_state_hash`。这不是即时泄漏风险，但属于审计完整性缺口，已随 P2 一并修复。

## 阶段 9 修复内容

修复文件：

- `src/repo_harness/v3_context_diagnostics.py`
- `tests/integration/test_context_compaction_v3.py`

修复内容：

- `kept_tool_result_ids` 改为从当前 context revision 的 `prepared_messages` 计算，而不是从完整 transcript 计算。
- `inspect-context-report` 重新读取当前 revision 的 prepared messages，复算 expected kept ids，并在报告值不一致时拒绝。
- `inspect-context-report` 解析 `content_replacement_state_ref`，读取 state payload，并校验 state payload 内的 `state_hash` 与报告中的 `content_replacement_state_hash` 一致。
- 新增负例测试覆盖“未来 tool result 被写入 kept ids”和“content replacement state hash 被篡改”。

修复后阶段 9 机器产物：

- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/`
- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json`
- `runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json`

修复后验证：

- `PATH=.venv/bin:$PATH python -m compileall src/repo_harness/v3_context_diagnostics.py`：通过。
- `PATH=.venv/bin:$PATH python -m pytest tests/integration/test_context_compaction_v3.py -q`：`5 passed`。
- `PATH=.venv/bin:$PATH repo-harness inspect-context-report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/context_compaction_report.json --assert-consistent`：通过。
- `PATH=.venv/bin:$PATH repo-harness inspect-long-rollout-diagnostics runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix --report runs/v3-stage-09-context-diagnostics-20260503T-stage9-subagent-fix/long_rollout_diagnostics.json --assert-complete`：通过。

阶段 9 修复复审结论：

- 修复后的 `kept_tool_result_ids` 与每个 context revision 的 prepared messages 当前内容一致。
- 新增负例能够捕获未来 tool result 注入和 state hash drift。
- 修复后的 long rollout diagnostics 仍然完整。
- 未发现新的 P1、P2 或 P3 问题。

## 阶段 10 审查结论

阶段 10 未发现新的 P1 或 P2 阻断项。

审查确认：

- `failure_diagnostics_core_report.json` 和 `failure_distribution_report.json` 的核心字段完整。
- final verifier hidden result、hidden selector 和 reward outcome 没有进入模型可见上下文或正式训练 payload。
- 阶段 10 报告本身没有把 long rollout diagnostics 当作 context compaction 的替代证据。
- 阶段 10 支持 evidence ref 和 sha256 校验。

保留的 P3 范围说明：

- 阶段 10 的 `input_run` 是用于诊断构造的审计输入，包含 `run_outcome`、`reward_metadata`、`gold_patch` 等 audit-only 标记。这些标记没有进入模型可见 prompt、prepared messages 或正式训练 payload。该项记录为 audit-only 输入边界风险，不阻断最终验收。
- 原始阶段 10 `command_log.jsonl` 记录了绝对 `cwd`，这符合 CommandLogEntry 对运行目录审计的要求，但不能被复制进模型可见上下文或正式训练 payload。最终 export audit 和 acceptance inspect 仍需继续检查该边界。

阶段 9 修复后刷新了阶段 10 支持证据，避免阶段 10 继续绑定旧的 context compaction 报告：

- `runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/`
- `PATH=.venv/bin:$PATH repo-harness inspect-reward-diagnostics runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix --core-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_diagnostics_core_report.json --distribution-report runs/v3-stage-10-failure-diagnostics-20260503T-stage9-subagent-fix/failure_distribution_report.json --assert-core-complete`：通过。

## 总体结论

阶段 7、阶段 8 和阶段 10 的追溯子代理智能体审查没有发现需要修改代码或重建阶段产物的 P1/P2 阻断项。

阶段 9 的追溯子代理智能体审查发现一个 P2 和一个随同修复的 P3；两者均已修复、重新生成阶段机器产物、通过 inspect 验证，并由独立只读复审子代理智能体确认没有新的阻断项。

因此，阶段 7 至阶段 10 的子代理智能体审查缺口已经补齐。第三版（V3）后续最终验收必须使用修复后的阶段 9 产物和刷新后的阶段 10 产物重新构建 `ACCEPTANCE_INPUTS`、`v3_acceptance_report.json` 和 `acceptance_bundle_manifest.json`。如果未来再次遇到子代理智能体创建失败，应先关闭不再需要的旧子代理智能体线程并重试；只有在清理后仍无法创建时，才允许使用等价独立只读自审，并且必须把原因、审查维度和结论写入阶段审查记录。
