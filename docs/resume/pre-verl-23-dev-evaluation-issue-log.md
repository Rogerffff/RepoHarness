# Pre-verl 二十三题开发测评问题记录

本文档用于记录 pre-verl 二十三题开发测评中暴露出来的 Harness 问题、模型表现问题、环境问题和评测归因问题。

本轮二十三题测评的定位是“开发测评”，目标是尽可能发现 RepoHarness 当前实现中仍然会影响模型解题、轨迹审计、失败归因、奖励计算或者训练导出的明显问题。它不是最终简历展示用正式测评，也不应该直接作为最终 accepted rate 或训练样本质量结论使用。

## 1. 当前状态

- 文档创建时间：2026-05-09。
- 当前阶段：正确模型 `deepseek-v4-pro` 的二十三题开发测评已经完成，正在基于产物做问题复盘。
- 最近 clean targeted smoke 目录：
  `runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-clean-priority-remediation-20260508T164758Z`
- 本轮正确二十三题开发测评目录：
  `runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z`
- 本轮二十三题测评性质：开发测评，用于发现问题；不是最终正式基线。
- 模型配置核对结果：`pre_verl_agentloop_configuration_manifest.json`、`formal_budget_freeze_manifest.json` 和 23 个 `run_configs/*.yaml` 的实际 `model_id` 都是 `deepseek-v4-pro`。`deepseek-v4-flash` 只作为 parent baseline 或错误试跑说明文本出现在 lineage / change summary 中，不是本轮实际执行模型。
- 23 个 run 全部 `FINALIZED`，全部生成 `final_verifier_boundary.json`。
- final verifier status 分布：`accepted=8`，`rejected=13`，`not_executed=2`。
- accepted 任务：第 2、7、9、10、12、17、19、23 题。
- `repo-harness inspect-pre-verl-agentloop-boundary-index` 已通过，`failure_count=0`。
- 对 23 个 run 执行 `inspect-model-visible-context`，开启 `--assert-prepared-messages-bound`、`--assert-no-hidden-test-material`、`--assert-provider-body-equivalent`、`--assert-tool-results-recoverable`、`--assert-no-over-redaction`，全部通过。

### 1.1 本轮修复状态更新

更新时间：2026-05-09。

本轮已经完成计划中的代码修复和非 Docker 定向验证，修复提交如下：

- `9addf3e2 test: add pre-verl dev23 issue scanner`
- `aba1b953 fix: attribute pytest selector failures`
- `c78cebea fix: audit pre-verl verifier outputs`
- `d67e2871 fix: classify final verifier environment failures`
- `6970f7a8 fix: guard wide symbol search scans`
- `58af688a fix: harden pre-verl repo environments`

这些提交修复了 `DEV23-P2-001`、`DEV23-P2-003`、`DEV23-P2-004`、`DEV23-P2-005` 和 `DEV23-P2-006` 的代码路径。当前状态应理解为“代码已修复，单元测试和暂存补丁临时 worktree 验证已通过，仍等待下一轮局部 Docker rerun 或 5 题 targeted smoke 做端到端确认”。旧的二十三题开发测评目录不会被这些代码修改自动改写，因此旧目录仍会保留原始问题痕迹。

`DEV23-P2-002` 本轮明确延期，没有加入新的 hard gate 或更强 convergence policy，避免在上下文压缩机制完成前把收敛策略和本轮 verifier / 环境 / 工具性能修复混在同一个基线里。

## 2. 开发测评使用原则

二十三题开发测评已经完成。本文件中的问题记录用于指导下一轮 hardening，不应该被理解为最终正式基线结论。

本轮结果在对外展示或者写入简历材料前，必须先完成一次问题复盘。复盘至少需要区分以下几类：

- 模型能力问题：模型已经获得足够上下文和工具反馈，但仍然选择了错误补丁、错误假设或者没有完成必要修改。
- Harness 工具问题：工具输出不完整、不可信、误导模型，或者工具执行效率显著影响模型在预算内完成任务。
- Harness 上下文问题：首轮上下文、repository action index、context replacement、context warning 或 provider-ready token 估计影响模型定位和收敛。
- Verifier 和 reward 问题：最终验收、selector 归因、pass_to_pass_score、failure diagnostics 或 reward 字段不能准确反映真实结果。
- 环境材料化问题：Docker image、dependency restore、setup command、workspace copy、symlink、platform 或 package metadata 影响任务可执行性。
- Provider 或 runtime 问题：provider retry、output token limit、malformed tool call repair、provider usage metadata 或 task timeout 影响结果解释。

## 3. 已知观察项

### DEV23-RUN-001：错误模型试跑已废弃

优先级：记录项。

状态：已停止，不进入本轮二十三题开发测评分母。

废弃 run 目录：

`runs/pre-verl-agentloop-23-dev-deepseek-flash-development-20260508T183918Z`

原因：

本目录启动时使用了 `--model-id deepseek-v4-flash`，但本轮二十三题开发测评应使用 `deepseek-v4-pro`。

配置证据：

- `pre_verl_agentloop_configuration_manifest.json` 中 `model_id="deepseek-v4-flash"`。
- `formal_budget_freeze_manifest.json` 中 `model_id="deepseek-v4-flash"`。
- `run_configs/` 下 23 个 run config 的 `model.model_id` 都是 `deepseek-v4-flash`。

停止时状态：

- 第 1 题 `pre_verl_dev_001_sqlfluff__sqlfluff_1625` 已完成。
- 第 2 题 `pre_verl_dev_002_sqlfluff__sqlfluff_2419` 已完成。
- 第 3 题 `pre_verl_dev_003_sqlfluff__sqlfluff_1733` 在运行中被终止，run artifact 中可能仍保留 `RUNNING` 状态。

处理规则：

- 该目录只能作为错误模型试跑证据，不能计入 `deepseek-v4-pro` 二十三题开发测评的 planned denominator、terminal denominator、accepted rate、failure taxonomy 或训练导出。
- 如果该目录中暴露出独立 Harness 问题，只能作为补充线索；是否升级为正式问题，应以正确 `deepseek-v4-pro` 运行或定向复现实验为准。

### DEV23-P2-001：pytest 参数化用例没有归回未参数化 selector

优先级：P2。

状态：代码已修复，等待局部 rerun 或 targeted smoke 端到端验证。

修复提交：

- `aba1b953 fix: attribute pytest selector failures`

修复摘要：

pytest parser 已增加参数化 selector 归因、状态前缀清理、`match_strategy`、`status_source`、`matched_nodeid`、`unmatched_failed_nodeids` 和 `unmatched_error_nodeids` 等审计字段。未参数化 selector 现在可以归回 `selector[...]` 形式的参数化 pytest node id，避免 `summary_counts.failed > 0` 且 `failed_count=0` 这类错误抬高 fail-to-pass 或 pass-to-pass 分数。

原始 clean targeted smoke 证据目录：

`runs/pre-verl-agentloop-targeted-smoke-deepseek-flash-clean-priority-remediation-20260508T164758Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_001_sqlfluff__sqlfluff_1625_deepseek_deepseek-v4-flash`

错误模型试跑补充证据目录，不进入本轮二十三题开发测评分母：

`runs/pre-verl-agentloop-23-dev-deepseek-flash-development-20260508T183918Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_001_sqlfluff__sqlfluff_1625_deepseek_deepseek-v4-flash`

正确 `deepseek-v4-pro` 二十三题开发测评复现证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_004_sqlfluff__sqlfluff_1517_deepseek_deepseek-v4-pro`

正确 `deepseek-v4-pro` 二十三题开发测评补充复现证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_016_pylint_dev__astroid_1866_deepseek_deepseek-v4-pro`

相关文件：

- `pre_verl_pass_to_pass_result.json`
- `pre_verl_final_verifier_result.json`
- `reward.json`
- `verifier.json`

现象：

- `pre_verl_pass_to_pass_result.json` 中 `exit_code=1`。
- `summary_counts.failed=1`。
- `failed_nodeids` 非空，首个失败节点是参数化展开后的 pytest node id，例如：
  `test/cli/commands_test.py::test__cli__command_fix_stdin[SELECT...`
- 但是 `failed_count=0`。
- `reward.json` 中 `pass_to_pass_score=1.0`。

错误模型试跑第 1 题中的补充复现字段：

- `final_verifier_boundary.json` 中 `final_verifier_status="rejected"`，`accepted=false`，`failure_owner="model_wrong_fix"`，`failure_category="model_patch_rejected_by_final_verifier"`。
- `pre_verl_final_verifier_result.json` 中 `fail_to_pass_result.exit_code=1`，`fail_to_pass_result.failed_count=1`。
- `pre_verl_final_verifier_result.json` 中 `pass_to_pass_result.exit_code=1`，`pass_to_pass_result.summary_counts.failed=1`，`pass_to_pass_result.failed_nodeids` 非空，但 `pass_to_pass_result.failed_count=0`。
- `reward.json` 中 `components.pass_to_pass_score=1.0`，因此 rejected 样本的 pass_to_pass regression 风险被低估。

注意：上述补充复现字段来自 `deepseek-v4-flash` 错误模型试跑，只用于说明 parser 问题确实存在，不能计入 `deepseek-v4-pro` 二十三题开发测评的任务结果。

正确 `deepseek-v4-pro` 第 4 题中的复现字段：

- `final_verifier_boundary.json` 中 `final_verifier_status="rejected"`，`accepted=false`，`failure_owner="model_wrong_fix"`，`failure_category="model_patch_rejected_by_final_verifier"`。
- `pre_verl_final_verifier_result.json` 中 `fail_to_pass_result.exit_code=1`，`fail_to_pass_result.summary_counts.failed=3`，`fail_to_pass_result.failed_nodeids` 非空，但 `fail_to_pass_result.failed_count=0`。
- `pre_verl_final_verifier_result.json` 中 `pass_to_pass_result.exit_code=1`，`pass_to_pass_result.summary_counts.failed=3`，`pass_to_pass_result.failed_nodeids` 非空，但 `pass_to_pass_result.failed_count=0`。
- 首个失败 node id 是参数化展开后的 `test/dialects/ansi_test.py::test__dialect__ansi_multiple_semicolons[select...`，说明未参数化 selector 到参数化 node id 的归因仍然不完整。

正确 `deepseek-v4-pro` 第 16 题中的复现字段：

- `final_verifier_boundary.json` 中 `final_verifier_status="rejected"`，`accepted=false`，`failure_owner="model_wrong_fix"`，`failure_category="model_patch_rejected_by_final_verifier"`。
- `pre_verl_final_verifier_result.json` 中 `fail_to_pass_result.exit_code=1`，`fail_to_pass_result.summary_counts.failed=1`，`fail_to_pass_result.failed_nodeids` 非空，但 `fail_to_pass_result.failed_count=0`。
- `pre_verl_final_verifier_result.json` 中 `pass_to_pass_result.exit_code=1`，`pass_to_pass_result.summary_counts.failed=1`，`pass_to_pass_result.failed_nodeids` 非空，但 `pass_to_pass_result.failed_count=0`。
- `reward.json` 中 `components.fail_to_pass_score=1.0` 且 `components.pass_to_pass_score=1.0`，说明这次不只是 regression diagnostics 偏乐观，fail-to-pass 部分完成度也被错误抬高。
- 首个失败 node id 是参数化展开后的 `tests/unittest_brain_builtin.py::TestStringNodes::test_string_format_uninferable[...]`，和第 4 题是同一类未参数化 selector 到参数化 node id 的归因缺失。

可疑原因：

pass_to_pass selector 中包含未参数化的函数选择器，例如：

```text
test/cli/commands_test.py::test__cli__command_fix_stdin
```

pytest 实际运行时展开出参数化用例，例如：

```text
test/cli/commands_test.py::test__cli__command_fix_stdin[...]
```

当前 selector parser 能记录失败的参数化 node id，但没有把这个失败归回原始未参数化 selector。因此 `failed_nodeids` 和 `summary_counts` 已经说明 pytest 有失败，但 selector 聚合层没有把它计入 `failed_count`，最终导致 `pass_to_pass_score` 偏乐观。

为什么不打断本轮二十三题开发测评：

本问题不会把 001 sqlfluff 错误判定为 accepted。当前 final verifier 的 accepted 判断仍然要求：

```text
fail_to_pass exit_code == 0
pass_to_pass exit_code == 0
```

这次 001 sqlfluff 的 `pass_to_pass exit_code=1`，因此不会被错误接受。

本问题已经在正确的 `deepseek-v4-pro` 二十三题开发测评中出现，目标是在下一轮最终正式基线和训练导出前，让 fail_to_pass / pass_to_pass regression score、failed_count 和 selector attribution 与 pytest 实际失败一致。

实际影响：

- rejected 样本的 `pass_to_pass_score` 会偏高。
- rejected 样本的 `fail_to_pass_score` 也可能偏高。
- regression diagnostics 会偏乐观。
- 如果后续导出或分析只看 `pass_to_pass_score`、`failed_count`，而不看 `exit_code`、`summary_counts` 和 `failed_nodeids`，可能低估回归风险。

升级依据：

正确的 `deepseek-v4-pro` 第 4 题已经出现以下组合，因此本问题已升级为正式修复项：

```text
pass_to_pass_result.exit_code == 1
pass_to_pass_result.failed_count == 0
pass_to_pass_result.summary_counts.failed > 0
```

或者：

```text
pass_to_pass_result.exit_code == 1
pass_to_pass_result.failed_count == 0
pass_to_pass_result.failed_nodeids 非空
```

当前建议优先级：

- 目前确认影响 rejected 样本的 selector attribution、`failed_count` 和 regression diagnostics，因此定为 P2。
- 如果后续发现 accepted、reward、训练导出或者正式汇总路径只依赖 `failed_count`，并可能绕过 `exit_code`，则进一步升级为 P1。

后续候选修复方向：

1. 在 pytest selector parser 中加入参数化 node id 归因规则。
2. 当 selector 为 `path::test_func`，失败 node id 为 `path::test_func[...]` 时，应视为同一个 selector 命中。
3. 在结果中增加 `selector_match_strategy`，例如 `exact`、`parameterized_prefix`、`module_prefix`、`unmatched`。
4. 增加 `unmatched_failed_nodeids`，用于审计哪些 pytest 失败没有归入任何 selector。
5. 增加 `parameterized_failed_nodeids_matched`，用于说明有多少参数化失败被归回未参数化 selector。
6. 为 `test__cli__command_fix_stdin` 这类未参数化 selector 覆盖单元测试和 pre-verl regression 测试。

### DEV23-P2-002：convergence nudge 没有阻止长期只读探索和空补丁超时

优先级：P2。

状态：本轮暂不处理，保留为延期观察项。

延期原因：

该问题和上下文膨胀、旧工具结果污染、重复搜索结果残留、关键恢复调用被淹没等因素可能有关。当前正在开发更完整的上下文压缩机制，因此本轮不新增更强 hard gate，也不改变正式基线的 convergence policy。待上下文压缩机制完成并通过 smoke 或二十三题复测后，再判断是否需要处理。

证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_003_sqlfluff__sqlfluff_1733_deepseek_deepseek-v4-pro`

补充证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_014_pylint_dev__astroid_1333_deepseek_deepseek-v4-pro`

现象：

- `final_verifier_boundary.json` 中 `final_verifier_status="not_executed"`，`accepted=false`，`failure_owner="budget_or_timeout"`，`failure_category="budget_exhausted_empty_patch"`，`agent_stop_reason="task_timeout"`。
- `pre_verl_final_verifier_result.json` 中 fail_to_pass 和 pass_to_pass selector suite 都是 `status="skipped"`，`structured_skip_reason="budget_exhausted_empty_patch"`。
- `reward.json` 中 `invalid_for_training=true`，`invalid_reason="budget_exhausted_empty_patch"`，`final_reward=0.0`。
- `metrics.json` 中 `timeout=true`，`turn_count=46`，`tool_call_count=45`，`patch_stats.changed_files=[]`。
- `metrics.json` 中 `loop_diagnostics_summary.consecutive_read_only_tool_calls=43`，`patch_tool_call_count=0`，`empty_search_count=7`，`consecutive_empty_search_count=7`。
- `events.jsonl` 中有 2 次 `convergence_nudge_injected`：第 1 次是 `exploration_no_progress`，第 2 次是 `near_budget_patch_or_stop`。
- `run_metadata.json` 中 `diagnostic_subtypes=["nudge_ignored_empty_patch"]`，`convergence_nudge_summary.latest_nudge_level="near_budget_patch_or_stop"`，`post_latest_nudge_action="no_observed_action_after_nudge"`。
- 第 14 题同样是 `final_verifier_status="not_executed"`，`failure_owner="budget_or_timeout"`，`failure_category="budget_exhausted_empty_patch"`，`agent_stop_reason="task_timeout"`，`reward.invalid_for_training=true`，`invalid_reason="budget_exhausted_empty_patch"`。
- 第 14 题的 `events.jsonl` 中也有 2 次模型可见 `convergence_nudge_injected`，分别是 `exploration_no_progress` 和 `near_budget_patch_or_stop`；第二次提醒发生在第 42 轮，`turns_remaining=6`，之后仍然没有观察到编辑、`git_diff` 或 final answer。

初步归因：

这是模型能力和 Harness 收敛控制共同造成的问题，但对 Harness 来说仍然是一个需要改进的评测控制问题。模型在第 3 题中没有产出任何编辑动作，说明模型自身定位和决策能力不足；但 Harness 已经观察到长期只读探索、空搜索累积和临近预算无补丁，却只注入了软提醒，没有进一步把模型强制收束到“选择一个最小补丁、说明放弃原因或者停止探索”的路径。

评测影响：

- 该任务没有进入 final verifier，无法判断模型是否会产出可验证补丁。
- 工具预算没有耗尽，主要是 wall-clock `task_timeout` 先触发；这会让后续分析难以区分“模型真的无解”还是“长时间低效探索被 Harness 放大”。
- 轨迹对训练不合格是正确的，但它暴露了当前 no-progress / convergence nudge 的控制力度仍偏弱。

需要注意的诊断不一致：

`metrics.json` 的 `loop_diagnostics_summary.model_visible_message_injected=false`，但同一 run 的 `events.jsonl` 中已经有 `convergence_nudge_injected`，且事件字段 `model_visible=true`。这可能是因为 `loop_diagnostics_summary` 保存的是某个诊断快照，而不是 nudge 注入后的最终状态。后续修复时应让最终 metrics 明确区分：

- `diagnostic_detected_no_progress`
- `convergence_nudge_injected`
- `latest_nudge_model_visible`
- `edited_after_latest_nudge`
- `final_answer_after_latest_nudge`

候选修复方向：

1. 对 `near_budget_patch_or_stop` 后仍然没有编辑动作的 run，增加更强的第三阶段 `near_budget_finalize_patch` 提醒，并要求模型只能选择以下三类动作之一：`edit_file`、`git_diff` 后 final answer、或者明确说明无法完成并停止。
2. 在临近任务 wall-clock timeout 时，不只看剩余 turn，还要把剩余秒数纳入 nudge level。当前第 3 题是 `task_timeout` 先触发，不是 `max_turns` 先触发。
3. 将 `update_working_state` 的结果用于收敛判断：如果模型多次更新状态但仍无候选补丁，下一次 nudge 应要求写出唯一候选文件和唯一最小编辑点。
4. 增加一个可审计的 hard-gate 实验策略，但不要直接混入最终正式基线。实验策略可以在连续只读超过阈值且已经触发两次 nudge 后，强制要求下一轮不能再调用只读搜索工具。
5. 在 `run_metadata.failure_diagnostics` 中保留当前 `nudge_ignored_empty_patch`，同时增加 wall-clock 维度字段，例如 `task_timeout_remaining_sec_at_latest_nudge` 和 `task_timeout_remaining_sec_at_last_model_call_started`。

验证方式：

- 增加 fake provider 回归测试：模型在两次 nudge 后继续只读探索，应产生 `nudge_ignored_empty_patch`、`latest_nudge_level="near_budget_patch_or_stop"` 和最终 `budget_exhausted_empty_patch`。
- 增加另一个 fake provider 回归测试：模型在第二次 nudge 后执行 `edit_file`，应记录 `edited_after_latest_nudge=true`。
- 对 `pre_verl_dev_003_sqlfluff__sqlfluff_1733` 做定向复跑或 replay，验证更强 nudge 是否降低空补丁超时概率。

### DEV23-P2-003：final verifier pytest exit code 4 缺少 stdout / stderr 审计材料

优先级：P2。

状态：代码已修复，等待局部 rerun 或 targeted smoke 端到端验证。

修复提交：

- `c78cebea fix: audit pre-verl verifier outputs`

修复摘要：

final verifier 的 fail-to-pass 和 pass-to-pass 命令现在会绑定 combined output、stdout、stderr artifact，并在 selector result 和 boundary step event 中写入 output refs、preview、`pytest_exit_reason`、`verifier_output_unparsed` 和 `pytest_output_parse_warnings`。pytest exit code 也已经结构化分类，避免只留下 `exit_code=4` 和空 summary。

证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro`

相关文件：

- `pre_verl_final_verifier_result.json`
- `final_verifier_boundary.json`
- `reward.json`
- `container_execution_facts/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro_container_000383.json`
- `container_execution_facts/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro_container_000384.json`

现象：

- `final_verifier_boundary.json` 中 `final_verifier_status="rejected"`，`accepted=false`，`failure_owner="model_wrong_fix"`，`failure_category="model_patch_rejected_by_final_verifier"`。
- `pre_verl_final_verifier_result.json` 中 `fail_to_pass_result.exit_code=4`，`summary_counts={}`，`failed_count=0`，`error_count=0`，`failed_nodeids=[]`，`error_nodeids=[]`。
- `pre_verl_final_verifier_result.json` 中 `pass_to_pass_result.exit_code=4`，`summary_counts={}`，`failed_count=0`，`error_count=0`，`failed_nodeids=[]`，`error_nodeids=[]`。
- 两个对应的 Docker container facts 都记录 `exit_code=4`，`timeout=false`，`requested_container_platform="linux/amd64"`，但是 `stdout_ref=null` 且 `stderr_ref=null`。
- `docker_backend_facts.json` 显示 pyvista 环境材料化本身正常：`requested_container_platform="linux/amd64"`，`image_platform="linux/amd64"`，`rg_available=true`。

初步归因：

这是 verifier 和 trajectory 审计层的问题。pytest 的 `exit_code=4` 通常代表 usage error、collection 参数错误或者类似的 pytest 运行层错误。即使根因最终是模型补丁破坏了仓库，Harness 也应该保留 pytest stdout / stderr 或至少保留结构化错误摘要。当前结果只留下了 exit code 和空 summary，无法判断是模型补丁导致收集失败、selector 已失效、pytest 命令参数过长或 verifier adapter 本身存在问题。

评测影响：

- 当前 accepted 判定没有被错误放宽，因为 `exit_code=4` 不会 accepted。
- reward 被置为 `invalid_for_training=true` 是保守的，但 `invalid_reason="model_patch_rejected_by_final_verifier"` 缺少足够审计证据支撑。
- 对开发测评复盘影响较大，因为无法区分“模型错误补丁导致 verifier 无法运行”和“Harness selector / command 生成错误”。
- 如果类似情况在最终正式基线中出现，会削弱“可审计、可导出训练轨迹”的可信度。

候选修复方向：

1. final verifier 执行 fail_to_pass 和 pass_to_pass 时，无论 exit code 是 0、1、2、3、4 还是超时，都应保存 stdout / stderr artifact，并在 result JSON 中绑定 `stdout_ref`、`stderr_ref`、`stdout_preview`、`stderr_preview`。
2. 增加 `pytest_exit_reason` 或类似字段，把 exit code 4 明确标注为 `pytest_usage_or_collection_error`，不要只留下空 summary。
3. 对 `exit_code != 0` 且 `summary_counts={}` 的情况，增加 `verifier_output_missing=true` 或 `verifier_output_unparsed=true`，避免后续分析把它误解成“没有失败用例”。
4. 如果 stdout / stderr 原本为空，应记录 `captured_output_empty=true`，并保留 container command、duration、timeout、platform 和 workspace path，便于复现。
5. 在 failure diagnostics 中增加子类，例如 `final_verifier_exit_code_4_without_output`，用于后续扫描和统计。

验证方式：

- 增加 Docker backend 单元测试或集成测试：构造一个返回 `exit_code=4` 且 stderr 非空的命令，断言 stdout / stderr artifact 被保存并绑定到 container facts。
- 增加 pre-verl final verifier 回归测试：pytest usage error 时，`pre_verl_final_verifier_result.json` 必须包含 output refs、preview 和结构化 exit reason。
- 对 `pre_verl_dev_018_pyvista__pyvista_4315` 做局部复跑或 replay，确认同类 exit code 4 能提供可审计输出。

### DEV23-P2-004：pytest error_count 和 error_nodeids 解析不一致

优先级：P2。

状态：代码已修复，等待局部 rerun 或 targeted smoke 端到端验证。

修复提交：

- `aba1b953 fix: attribute pytest selector failures`
- `c78cebea fix: audit pre-verl verifier outputs`

修复摘要：

pytest parser 和 selector result payload 已统一 failed / error 归因逻辑。`FAILED `、`ERROR ` 等状态前缀会被规范化，`error_nodeids` 和 `error_count` 不再互相脱节；当非零退出但没有可解析测试事实时，会写入不可解析输出标记和 parse warning。

证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_021_pydicom__pydicom_901_deepseek_deepseek-v4-pro`

相关文件：

- `pre_verl_final_verifier_result.json`
- `final_verifier_boundary.json`
- `reward.json`

现象：

- `final_verifier_boundary.json` 中 `final_verifier_status="rejected"`，`accepted=false`，`failure_owner="model_wrong_fix"`，`failure_category="model_patch_rejected_by_final_verifier"`。
- `pre_verl_final_verifier_result.json` 中 `fail_to_pass_result.exit_code=1`。
- `fail_to_pass_result.summary_counts={"errors": 5, "failed": 5}`。
- `fail_to_pass_result.failed_count=5`，`failed_nodeids` 有 5 个测试节点。
- `fail_to_pass_result.error_nodeids` 非空，实际有 6 个条目，但 `fail_to_pass_result.error_count=0`。
- `error_nodeids` 中还出现了带 `FAILED ` 前缀的条目，例如 `FAILED pydicom/tests/test_config.py::TestDebug::test_debug_off_handler_stream`，说明 pytest output parser 对 failure summary 和 error summary 的来源行处理不够严格。

初步归因：

这是 pytest result parser 的计数和节点归因问题，和 `DEV23-P2-001` 属于同一类 verifier / reward 审计风险，但具体表现不同。`DEV23-P2-001` 主要是参数化 node id 没有归回未参数化 selector；本问题是 summary 中已经有 errors，`error_nodeids` 也被解析出来，但 `error_count` 没有同步，且部分 error node id 带有错误前缀。

评测影响：

- 当前 accepted 判定没有被错误放宽，因为 fail_to_pass `exit_code=1`。
- 当前 reward 中 `fail_to_pass_score=0.0`，主要因为 `failed_count=5` 已经足够判定失败。
- 如果后续某个 run 只有 errors、没有 failures，而 parser 仍然让 `error_count=0`，就可能低估 fail_to-pass 或 pass-to-pass 的失败程度。
- 该问题会污染错误类型统计，让开发测评复盘无法准确区分 assertion failure、collection error、runtime error 和 parser artifact。

候选修复方向：

1. pytest parser 应让 `summary_counts.errors > 0`、`error_nodeids` 和 `error_count` 保持一致。
2. 对 failure summary 行和 error summary 行分别解析，避免把 `FAILED path::node` 这样的 summary 行原样塞进 `error_nodeids`。
3. 增加 `unparsed_error_lines` 或 `pytest_output_parse_warnings`，当 summary 和节点计数不一致时留下审计信号。
4. 在 reward 计算前增加一致性检查：如果 `exit_code != 0` 且 `summary_counts.errors > 0`，但 `error_count=0`，应把该样本标记为 `verifier_result_inconsistent` 或至少加入 diagnostics。

验证方式：

- 增加 pytest parser 单元测试，覆盖 `errors=5, failed=5` 且同时存在 failure summary 和 error detail 的输出。
- 增加 pre-verl final verifier 回归测试，断言 `summary_counts.errors`、`error_nodeids` 和 `error_count` 不会互相矛盾。
- 二十三题结束后全局扫描所有 `summary_counts.errors > 0` 但 `error_count=0` 或 `error_nodeids` 非空但 `error_count=0` 的 run，并追加到本问题。

### DEV23-P2-005：`symbol_search` 在宽 root 下仍可能消耗过多 wall-clock 时间

优先级：P2。

状态：代码已修复，等待 targeted smoke 验证真实模型是否按恢复提示收窄搜索。

修复提交：

- `6970f7a8 fix: guard wide symbol search scans`

修复摘要：

`symbol_search(root=".")` 在候选 Python 文件数超过阈值时不再执行昂贵全仓 AST 扫描，而是返回 `scan_requires_narrow_root`、`scan_complete=false`、`semantic_complete=false`、`scanned_file_count=0`、`recommended_narrow_roots`、`recommended_next_calls` 和 `result_envelope.recovery_call`。非宽 root 搜索增加 per-executor AST cache、`cache_hit_file_count`、`cache_miss_file_count`、`slow_scan`、`duration_ms` 等审计字段。首轮 `tool_use_guidance` 也提示优先使用 `repository_action_index` 候选目录作为 `symbol_search.root`。

证据目录一：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro`

证据目录二：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_022_pydicom__pydicom_1139_deepseek_deepseek-v4-pro`

补充证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_003_sqlfluff__sqlfluff_1733_deepseek_deepseek-v4-pro`

现象：

- 第 18 题第 1 轮调用 `symbol_search(query="RectilinearGrid", root=".", symbol_kind="class")`。
- 该次工具调用 `status="ok"`，但 `duration_ms=115277`，约 115 秒。
- 该次工具调用的 typed 字段显示 `search_backend="python_ast_symbol_index"`，`candidate_file_count=347`，`scanned_file_count=347`，`result_kind="symbols_found"`。
- 第 22 题第 1 轮调用 `symbol_search(query="PersonName3", root=".", symbol_kind="class")`。
- 该次工具调用 `status="ok"`，但 `duration_ms=34609`，约 35 秒。
- 该次工具调用的 typed 字段显示 `candidate_file_count=124`，`scanned_file_count=124`，`result_kind="complete_no_symbol_match"`。
- 第 3 题中还有一次较小范围的 `symbol_search(query="indent", root="src/sqlfluff/core/parser")`，扫描 25 个 Python 文件，仍耗时约 6.7 秒。
- 同一轮二十三题中 `grep` 已经稳定走 Docker 内 `ripgrep`，没有出现类似长耗时；因此当前新的性能风险集中在 `symbol_search` 的 Python AST 扫描路径。

初步归因：

`symbol_search` 当前是轻量 Python AST 定义导航工具，但在模型传入 `root="."` 时会对候选 Python 文件逐个解析。对于 PyVista 这类仓库，首轮全仓符号搜索会扫描数百个文件，且缺少可复用索引缓存、候选文件上限、慢扫描恢复提示和自动收窄建议。虽然工具返回结果是正确的，但模型在正式任务里会把这类耗时计入整体 task timeout。

为什么这是 Harness 能力问题：

- 首轮上下文已经提供了 repository action index，第 18 题首轮候选中包含 `pyvista/core/grid.py` 和 `pyvista/core/filters/rectilinear_grid.py`，第 22 题首轮候选中包含 `pydicom/valuerep.py`、`pydicom/dataset.py` 等入口。
- 模型仍然可能按工具提示选择 `symbol_search(root=".")`，说明仅靠提示不足以保证搜索范围足够窄。
- 工具本身知道 `candidate_file_count`、`scanned_file_count` 和 `duration_ms`，但没有在宽 root 时提前要求收窄，也没有返回 `semantic_complete=false` 或带 `recovery_call` 的慢扫描提示。

评测影响：

- 当前没有直接导致 accepted 样本错误或 final verifier 判定错误。
- 第 18 题和第 22 题都不是因为 `symbol_search` 本身失败而 rejected，但这两次调用分别消耗约 115 秒和 35 秒，对 1200 秒级任务预算是明显浪费。
- 在更大仓库或模型多次重复宽 root 符号搜索时，可能复现为 task timeout、低效轨迹和错误的模型能力归因。

候选修复方向：

1. 为 `symbol_search` 增加 per-run 或 per-workspace Python symbol index cache，避免同一仓库重复解析相同 Python 文件。
2. 当 `root="."` 且候选 Python 文件数超过阈值时，优先返回带 `recovery_call` 的可恢复结果，例如建议 `symbol_search(query="...", root="pyvista/core")` 或 `symbol_search(query="...", root="pydicom")`。
3. 在 `symbol_search` typed result 中增加 `slow_scan=true`、`slow_scan_threshold_ms`、`candidate_file_count`、`recommended_narrow_roots` 等字段。
4. 将首轮 `tool_use_guidance` 调整为：只有在 action index 没有可用候选目录时，才对 `symbol_search` 使用 `root="."`；否则应使用候选源码目录作为 root。
5. 对 `symbol_search` 增加软超时或扫描文件上限。达到上限时不能伪装为可信无匹配，应返回 `semantic_complete=false`、`result_kind="partial_symbol_scan"` 和恢复调用。
6. 可选地使用 `ripgrep --files -g '*.py'` 或持久化文件清单作为候选文件发现层，但 AST 解析结果仍应缓存。

验证方式：

- 增加单元测试：构造包含大量 Python 文件的临时仓库，验证第二次相同 `symbol_search` 复用缓存，耗时和解析文件数显著下降。
- 增加工具回归测试：`root="."` 且候选文件数超过阈值时，工具结果必须包含 `slow_scan` 或 `recovery_call`，不能只给一个普通 `complete_no_symbol_match`。
- 对第 18 题和第 22 题做局部复跑或 replay，验证首轮宽 root symbol search 不再出现 30 秒以上耗时。
- 在后续二十三题复盘脚本中加入扫描项：打印所有 `symbol_search.duration_ms > 5000` 的工具调用。

### DEV23-P2-006：PyVista final verifier 环境缺少 `libGL.so.1`，导致第 18 题不可可靠归因为模型错误

优先级：P2。

状态：代码已修复，等待 PyVista 局部 Docker rerun 或 targeted smoke 端到端验证。

修复提交：

- `d67e2871 fix: classify final verifier environment failures`
- `58af688a fix: harden pre-verl repo environments`

修复摘要：

PyVista 环境现在显式冻结 `requested_container_platform="linux/amd64"`，setup 和 runtime shell prefix 包含 `libgl1` 等 VTK / PyVista 所需最小系统库。scheduler 会把仓库级 `requested_container_platform` 写入 run config。Docker backend 的 `_image_exists()` 会校验已有镜像平台是否等于请求平台，避免本地已有同名 arm64 镜像时错误跳过 amd64 build。final verifier 侧会把明确命中外部共享库缺失 marker 的 pytest import/config 错误归为 `final_verifier_environment_error`，并同步到 boundary、reward 和 run metadata。源码材料化和 workspace copy 也已保留 symlink，避免 fixture symlink 复制失败。

证据目录：

`runs/pre-verl-agentloop-23-dev-deepseek-pro-development-20260508T185350Z/run_task_runs/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro`

相关文件：

- `pre_verl_fail_to_pass_result.json`
- `pre_verl_pass_to_pass_result.json`
- `pre_verl_final_verifier_result.json`
- `final_verifier_boundary.json`
- `reward.json`
- `run_metadata.json`
- `artifacts/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro_artifact_000109_command_output.txt`
- `artifacts/pre_verl_agentloop_pre_verl_dev_018_pyvista__pyvista_4315_deepseek_deepseek-v4-pro_artifact_000110_command_output.txt`

现象：

- `pre_verl_fail_to_pass_result.json` 中 `exit_code=4`，`error_type="test_command_error"`，`parse_warnings=["pytest_command_error_exit_code"]`。
- `pre_verl_pass_to_pass_result.json` 中同样是 `exit_code=4` 和 `error_type="test_command_error"`。
- 两个 selector result 都有 `output_artifact_ref`，对应 command output artifact 不是空的。
- command output 中 pytest 在解析 warning 配置 `error::pyvista.PyVistaDeprecationWarning` 时导入 `pyvista`，随后导入 `pyvista/_vtk.py`，最终失败于：

```text
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```

- `task_definitions/pre_verl_dev_018_pyvista__pyvista_4315.yaml` 中 `environment.execution_image="python:3.9"`，`setup_command=None`，没有看到安装 `libGL` 这类系统依赖的任务级步骤。
- `final_verifier_boundary.json` 当前仍写成 `final_verifier_status="rejected"`、`failure_owner="model_wrong_fix"`、`failure_category="model_patch_rejected_by_final_verifier"`。
- `run_metadata.json` 也把该 run 归为 `failure_category="model_failure"`、`failure_type="final_verifier_failed"`。
- `reward.json` 虽然保守地写了 `invalid_for_training=true` 和 `final_reward=0.0`，但 `invalid_reason="model_patch_rejected_by_final_verifier"`，没有指出 final verifier 环境依赖缺失。

初步归因：

这是环境材料化和 verifier 归因问题。第 18 题的 pytest 没有真正进入任务断言阶段，而是在 pytest 配置解析 / PyVista import 阶段因为系统库缺失退出。该错误不能可靠地归因为模型补丁错误。即使模型补丁本身可能不正确，本 run 也没有给出足够证据证明 final verifier 是在完整可执行环境里拒绝模型补丁。

和 `DEV23-P2-003` 的关系：

- `DEV23-P2-003` 仍然成立的一部分是：container execution facts 中 `stdout_ref=null`、`stderr_ref=null`，没有把 stdout / stderr 拆分绑定到 container facts。
- 但复盘发现 selector result 层已经有 `output_artifact_ref`，并且 command output artifact 能看到真实 stderr。
- 因此第 18 题更深层的问题应单独记录为本问题：PyVista final verifier live environment 缺少系统依赖，并且 failure owner / invalid reason 归因不准确。

评测影响：

- 当前 accepted 判定没有被错误放宽，任务没有进入 accepted。
- 但第 18 题作为开发测评分母时被记为 `rejected / model_wrong_fix`，这会低估模型表现并污染 failure taxonomy。
- 该样本已经 `invalid_for_training=true`，不会作为有效训练样本导出，这是正确的保守行为。
- 如果最终正式基线中仍有同类环境错误，应从 accepted rate 分母或模型错误分母中单独剥离为 `environment_or_verifier_failure`。

候选修复方向：

1. 为 PyVista 环境增加系统依赖安装，例如在 Docker image 或任务环境材料化中安装提供 `libGL.so.1` 的包。具体包名需要按目标基础镜像确认，例如 Debian / Ubuntu 系镜像通常需要 `libgl1` 或等价 OpenGL runtime 包。
2. 在 pre-verl materialization 或 run-task setup 后增加 live environment preflight，而不是只依赖 frozen baseline evidence。至少应验证 `python -c "import pyvista"` 或能导入 pytest warning 配置引用的包。
3. final verifier 遇到 pytest `exit_code=4` 时，只有在 clean preflight 失败、stderr 明确命中外部系统共享库缺失，例如 `cannot open shared object file` / `libGL.so.1`，或者同一第三方依赖缺失能在没有模型补丁的 clean verification workspace 中复现时，才应将 `failure_owner` 归为 `environment_or_harness` 或 `harness_or_verifier_input`。不能把所有 `No module named`、`ModuleNotFoundError` 或 `ImportError` 都直接归为环境问题；模型补丁造成的仓库内 import 错误仍应保留为 `model_wrong_fix` 或 `ambiguous_verifier_failure`。
4. `reward.invalid_reason` 应写成类似 `final_verifier_environment_error` 或 `pytest_command_error_environment_dependency_missing`，保留原始 stderr artifact 引用。
5. run matrix 汇总应区分 `model_wrong_fix`、`budget_or_timeout` 和 `environment_or_verifier_failure`，避免把不可执行任务混入模型错误分母。

验证方式：

- 对 PyVista Docker environment 增加 preflight 测试：在 setup 后运行 `python -c "import pyvista"`，缺少 `libGL.so.1` 时必须提前失败并给出环境归因。
- 增加 final verifier 回归测试：模拟 pytest `exit_code=4` 且 stderr 包含 `ImportError: libGL.so.1`，断言 boundary / run_metadata / reward 都归为环境或 verifier 输入问题，而不是 `model_wrong_fix`。
- 修复系统依赖后，局部复跑 `pre_verl_dev_018_pyvista__pyvista_4315`，确认 fail_to_pass 和 pass_to_pass 不再因为 `libGL.so.1` 缺失退出。
- 保留 `DEV23-P2-003` 的 output binding 回归测试，确保 selector result 和 container execution facts 都能绑定足够的 stdout / stderr 审计材料。

## 4. 二十三题开发测评结束后的必查项

测评结束后，需要把每个任务至少检查到以下层次：

1. `final_verifier_boundary.json`：确认是否执行 formal boundary、accepted 判定、failure owner、fail_to_pass 和 pass_to_pass 结果。
2. `pre_verl_final_verifier_result.json`：确认 final verifier 的 exit code、summary counts、failed node ids 和 selector 聚合字段是否一致。
3. `reward.json`：确认 reward 是否与 verifier boundary 一致，特别是 invalid、timeout、rejected patch、pass_to_pass regression 的处理。
4. `run_metadata.json`：确认 failure diagnostics 是否与 final verifier boundary 一致，不能把模型错误错误归因为环境错误。
5. `events.jsonl`：检查 provider retry、tool duration、context warning、convergence nudge、task timeout、tool call repair 和 final verifier 事件。
6. `transcript.jsonl`：抽查模型是否看到了首轮工具提示、repository action index、context warning 和关键工具结果。
7. `docker_backend_facts.json`：确认平台、镜像、ripgrep、workspace execution mode 和搜索 backend 符合本轮基线。
8. `run_config_facts.json`：确认 provider retry、tool schema、permission policy、context estimator、convergence nudge policy 和 baseline id 已冻结。

## 5. 二十三题结束后需要扫描的已知模式

### 5.1 pass_to_pass exit code 和 failed_count 不一致

扫描目标：

- 找出 `pass_to_pass_result.exit_code=1` 但 `failed_count=0` 的 run。
- 进一步检查 `summary_counts.failed`、`summary_counts.error`、`failed_nodeids` 和 `error_nodeids` 是否非空。

示例扫描逻辑：

```bash
PATH=.venv/bin:$PATH python - <<'PY'
import json
from pathlib import Path

root = Path("RUN_DIR/run_task_runs")
for result_path in root.glob("*/pre_verl_pass_to_pass_result.json"):
    data = json.loads(result_path.read_text())
    summary = data.get("summary_counts") or {}
    failed_nodeids = data.get("failed_nodeids") or []
    error_nodeids = data.get("error_nodeids") or []
    if data.get("exit_code") == 1 and data.get("failed_count") == 0:
        if summary.get("failed", 0) or summary.get("errors", 0) or failed_nodeids or error_nodeids:
            print(result_path.parent.name)
            print("  result:", result_path)
            print("  summary_counts:", summary)
            print("  failed_nodeids_sample:", failed_nodeids[:3])
            print("  error_nodeids_sample:", error_nodeids[:3])
PY
```

如果该扫描在后续任务中继续命中，需要把所有命中的任务追加到 `DEV23-P2-001` 的证据列表中，并在最终复盘里统计该问题影响了多少 rejected 样本的 regression diagnostics。

### 5.2 rejected 样本 reward 和 verifier 边界不一致

扫描目标：

- rejected 样本中 `reward.json` 的 `pass_to_pass_score` 是否被明显高估。
- `run_metadata.failure_diagnostics` 是否与 `final_verifier_boundary.failure_owner` 一致。
- invalid、timeout、environment failure、provider failure 是否不会进入 trainable accepted sample。

### 5.3 工具效率和收敛问题

扫描目标：

- 48 轮耗尽但工具预算仍然大量剩余的 run。
- 连续多轮只读、重复搜索、重复读取同一个大文件、只使用 `grep` 不使用 `glob_files` 或 `symbol_search` 的 run。
- 已注入 convergence nudge 但模型仍然没有编辑或没有 final patch 的 run。

### 5.4 搜索事实可信问题

扫描目标：

- `grep` 或 `list_files` 返回 `complete_no_match`，但同时存在 read error、visibility error、backend mismatch、scan limit 或 unclassified path。
- Docker mode 下工具结果没有记录 `search_backend`、`workspace_execution_mode`、`scan_complete_reason`、`read_error_count` 或 `visibility_error_count`。

### 5.5 首轮上下文和 repository action index 问题

扫描目标：

- 首轮 prepared messages 是否包含 `tool_use_guidance`。
- 首轮 prepared messages 是否包含可行动的 `repository_action_index` 候选入口。
- 候选入口是否来自 model-visible issue、公开 expected files 或公开源码浅层索引，不能来自 hidden tests、hidden selector、gold patch 或 targeted smoke 后验分析。

## 6. 问题记录模板

后续每个新问题都按下面格式追加，避免把模型错误、Harness 错误和环境错误混在一起。

### DEV23-XXX：问题标题

优先级：P0 / P1 / P2 / P3。

状态：新发现 / 已复现 / 已修复 / 已验证 / 暂不修复。

影响任务：

- `task_id`

证据路径：

- `run_task_runs/...`

现象：

- 具体字段、事件、命令 exit code、模型行为或者 verifier 结果。

初步归因：

- Harness 工具问题 / Harness 上下文问题 / verifier 和 reward 问题 / 环境材料化问题 / provider 或 runtime 问题 / 模型能力问题 / 暂不能判断。

影响范围：

- 是否影响 accepted 判定。
- 是否影响 reward。
- 是否影响训练导出。
- 是否影响简历展示口径。

建议处理：

- 立即修复 / 本轮开发测评后修复 / 记录为分析风险 / 不处理。

验证方式：

- 单元测试。
- 集成测试。
- inspect 命令。
- targeted smoke。
- 二十三题复跑或局部复跑。

## 7. 当前结论

本轮正确 `deepseek-v4-pro` 二十三题开发测评已经完成。它可以作为开发测评证据使用，但不能直接作为最终简历展示用正式基线，因为本轮明确暴露了 6 类需要进入下一轮 hardening 的 Harness 问题。

`DEV23-P2-001` 已经在 `aba1b953` 中完成代码修复。旧二十三题开发测评目录仍保留原始 `failed_count=0` 痕迹；下一步需要通过第 4 题和第 16 题局部 rerun 或 targeted smoke 确认新 parser 在真实产物中不再产生该不一致。

`DEV23-P2-002` 已经在第 3 题和第 14 题中复现。本轮按照修复计划明确暂不处理，没有引入新的强制收敛 hard gate。该项等待上下文压缩机制完成后再重新评估。

`DEV23-P2-003` 已经在 `c78cebea` 中完成代码修复。final verifier 输出绑定、stdout / stderr artifact、pytest exit reason 和不可解析输出标记已补齐，下一步需要通过第 18 题局部 rerun 确认真实 Docker final verifier 产物中字段完整。

`DEV23-P2-004` 已经随 `aba1b953` 和 `c78cebea` 完成代码修复。下一步需要通过第 21 题局部 rerun 或 parser replay 确认 `summary_counts.errors`、`error_nodeids` 和 `error_count` 保持一致。

`DEV23-P2-005` 已经在 `6970f7a8` 中完成代码修复。下一步 targeted smoke 需要确认真实模型遇到宽 root 保护后会使用 `recommended_narrow_roots` 或 `result_envelope.recovery_call`，不再出现 30 秒以上无保护全仓 AST 扫描。

`DEV23-P2-006` 已经在 `d67e2871` 和 `58af688a` 中完成代码修复。下一步需要通过 PyVista 第 18 题局部 Docker rerun 确认环境不再因为 `libGL.so.1` 缺失退出；如果仍有其他系统依赖缺失，应被归为 environment failure，而不是 `model_wrong_fix`。

下一步建议先做计划中的局部 Docker rerun 或 5 题 targeted smoke，覆盖第 4、16、18、21、22 题，并重新执行 boundary inspect、model-visible context inspect 和问题扫描脚本。`DEV23-P2-002` 的 convergence nudge 强收敛策略继续等待上下文压缩机制完成，并经过 smoke / 二十三题复测后再判断是否需要处理。当前 8/23 accepted 只能作为开发测评模型表现参考，不建议写入最终 accepted rate 展示。
