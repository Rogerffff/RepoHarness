# Stage 09: planner_coder_verifier scaffold

## 本阶段目标

本阶段目标是实现计划内增强 `planner_coder_verifier` scaffold，用于比较顺序式 planning、coding、verifier-feedback 和 repair 策略。本阶段的 planner、coder、verifier、repair、final 是同一个 Agent Loop 内的阶段化策略角色，不是后台多智能体系统。

## 本阶段实现内容

- 新增 `planner_coder_verifier` scaffold：
  - `scaffold_id=planner_coder_verifier`
  - `scaffold_version=repo_harness_planner_coder_verifier_v0`
  - phase sequence 为 `planner -> coder -> verifier -> repair -> final`
  - phase transition policy 为 `repo_harness_planner_coder_verifier_linear_v0`
  - 默认 `feedback_tests_passed_policy=require_model_final`
- 扩展 `ScaffoldDefinition`：
  - 增加 phase sequence。
  - 增加 per-phase allowed tools。
  - 增加 per-phase prompt fragment。
- 修改 scaffold registry：
  - 注册 `planner_coder_verifier`。
  - 保留 `simple_react` 和 `single_shot_patch` 既有行为。
- 修改 scaffold policy：
  - 新增 `resolve_allowed_tools_for_phase`。
  - phase allowed tools 仍受 resolved `test_feedback_policy` 约束；`test_feedback_policy=disabled` 时 verifier 和 repair phase 也不能使用 `run_tests`。
- 修改 Agent Loop：
  - 在 `AgentLoopState` 中记录 `current_phase` 和 `phase_history`。
  - 每轮模型调用根据当前 phase 构造 allowed tool definitions。
  - 每轮模型调用的 provider-ready messages 中注入 `scaffold_phase_metadata`。
  - `model_call_started` 和 `model_call_completed` 事件记录当前 `scaffold_phase` 和当前 phase 的 allowed tools。
  - phase 转移写入 `scaffold_phase_transition` event。
  - planner phase 试图调用 `edit_file` 时，在进入 Permission System 前被 scaffold policy 阻断并生成配对 `ToolResult`。
  - verifier phase 的 `run_tests` 仍走 feedback verifier；formal final verifier 仍在 agent 停止后独立运行。
- 修改 ExperimentConfig：
  - Stage 09 允许 `planner_coder_verifier`。
  - provider 范围仍只允许 replay 和 fake；没有提前实现 Stage 10 mock provider 或 Stage 11 real provider。

## 修改的主要文件

- `src/repo_harness/scaffolds/planner_coder_verifier.py`
- `src/repo_harness/scaffolds/schemas.py`
- `src/repo_harness/scaffolds/registry.py`
- `src/repo_harness/scaffolds/policies.py`
- `src/repo_harness/scaffolds/__init__.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/agent_loop/schemas.py`
- `src/repo_harness/evaluation/schemas.py`
- `tests/unit/test_scaffold_planner_coder_verifier.py`
- `tests/integration/test_planner_coder_verifier.py`
- `tests/unit/test_experiment_config.py`
- `tests/fixtures/replays/task_001_planner_coder_verifier_success.yaml`
- `tests/fixtures/replays/task_001_planner_coder_verifier_planner_edit.yaml`
- `tests/fixtures/replays/task_002_planner_coder_verifier_repair.yaml`
- `tests/fixtures/run_configs/v2/planner_coder_verifier_success.yaml`

## 生成的机器可读产物

阶段验收 smoke run 生成了：

- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/run_config_facts.json`
- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/run_metadata.json`
- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/metrics.json`
- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/events.jsonl`
- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/artifacts.json`
- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/final.patch`
- `runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/final.diff`

该 smoke run 证明：

- `inspect-run` 可以读取 Stage 09 run。
- `scaffold_id=planner_coder_verifier`。
- `phase_policy=repo_harness_planner_coder_verifier_linear_v0`。
- `feedback_tests_passed_policy=require_model_final`。
- `test_run_count=1`。
- `feedback_verifier_accepted=true`。
- `model_call_started` 记录 planner、coder、verifier、final 四个 phase。
- `scaffold_phase_transition` 记录 `planner -> coder`、`coder -> verifier`、`verifier -> final`。
- final verifier 状态为 `accepted`，run outcome 为 `success`。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_scaffold_planner_coder_verifier.py tests/integration/test_planner_coder_verifier.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_agent_loop_protocol.py tests/unit/test_scaffold_single_shot_patch.py tests/integration/test_single_shot_patch.py tests/unit/test_experiment_config.py tests/integration/test_agent_loop_replay.py tests/integration/test_experiment_runner.py -q
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v2/planner_coder_verifier_success.yaml --output-dir runs/v2-stage09-smoke-20260501T201525Z --run-id stage09-planner-coder-verifier-success
PATH=.venv/bin:$PATH repo-harness inspect-run runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success
rg -n 'planner_coder_verifier|scaffold_phase_transition|scaffold_phase|phase_policy|feedback_verifier_accepted|final_verifier_status|test_run_count|agent_stop_reason' runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/run_config_facts.json runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/run_metadata.json runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/metrics.json runs/v2-stage09-smoke-20260501T201525Z/stage09-planner-coder-verifier-success/events.jsonl
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- Stage 09 定向测试通过，6 个测试通过。
- 相关回归测试通过，43 个测试通过。
- Stage 09 smoke run 成功，`inspect-run` 显示 run metadata、run config facts 和 tool schema snapshot 均为 ok。
- `python -m compileall src` 通过。
- 全量测试通过，277 个测试通过。

## 正例证据

- `planner_coder_verifier` 注册到 scaffold registry，并声明 planner、coder、verifier、repair、final 五个 phase。
- planner phase 的 allowed tools 只有 `list_files`、`read_file`、`grep`、`git_diff`。
- coder phase 允许编辑工具和必要诊断工具。
- verifier phase 允许 `run_tests`，但仍受 resolved `test_feedback_policy` 和 `max_test_runs` 约束。
- final phase 没有可用工具，只接受最终回答。
- provider-ready messages 包含 `scaffold_phase_metadata`，其中记录当前 phase、phase sequence、phase prompt、phase allowed tools 和 phase transition policy。
- 成功路径按 `planner -> coder -> verifier -> final` 完成任务，formal final verifier accepted。
- repair 路径按 `planner -> coder -> verifier -> repair -> verifier -> final` 完成任务，第一次 feedback 未通过后进入 repair，第二次 feedback 通过后进入 final。
- planner 阶段试图调用 `edit_file` 时被 scaffold policy 阻断，未进入 Permission System。
- `run_config_facts.json` 和 `run_metadata.json` 均记录 `scaffold_id`、`scaffold_version` 和 `phase_policy`。

## 负例证据

- 没有实现 mock provider；`model.provider=mock` 仍不在 Stage 09 支持范围。
- 没有实现 DeepSeek、OpenAI 或其他真实 provider。
- 没有新增后台子代理、agent-to-agent mailbox、远程代理、额外 worktree 或团队协作调度。
- planner 阶段不允许 `edit_file`。
- `feedback_tests_passed_policy=require_model_final` 时，feedback verifier accepted 不会把 agent stop reason 改成 `feedback_tests_passed`；模型必须进入 final phase 输出最终回答。
- verifier phase 的 `run_tests` 没有替代 formal final verifier；`verifier_final` 仍在 Agent Loop 停止后独立运行。

## 允许降级项

- phase transition 是第二版最小顺序策略，不实现复杂动态 planning graph。
- repair phase 只在 feedback verifier 未 accepted 且已经运行测试反馈后进入；不实现多轮智能调度或复杂 retry plan。
- 本阶段不实现后台多代理、远程代理、额外 worktree 或 agent-to-agent mailbox。
- 本阶段不新增 provider 能力。

## 禁止降级项

- 不能把 planner、coder、verifier 实现成后台多智能体系统。
- 不能启动额外 worktree 或远程 agent。
- 不能让 planner phase 调用编辑工具。
- 不能让 verifier phase 的 feedback verifier 替代 formal final verifier。
- 不能绕过 resolved `test_feedback_policy` 或 `max_test_runs`。
- 不能破坏 tool call / tool result 配对。
- 不能把 `ReplayScript.expected_outcome`、脚本注释、hidden metadata、baseline/final verifier 信息放进模型可见内容或训练导出。
- 不能提前实现 Stage 10 mock provider 或 Stage 11 real provider。

## 已知限制

- phase transition policy 是固定顺序策略。
- `planner_coder_verifier` 仍运行在单个 Agent Loop、单个 Workspace Adapter 和单个 RunRecorder 中。
- repair phase 的最小策略足够覆盖 failed feedback 后的修复路径，但不做复杂候选排序。
- Stage 10 mock provider 和 Stage 11 real provider 仍未实现。

## 是否偏离设计文档

未发现需要记录的设计冲突。本阶段按文档要求实现顺序式多阶段 scaffold，并明确没有实现后台多代理系统。`planner_coder_verifier` 已完成，因此最终验收不需要把 Stage 09 标记为 deferred enhancement。

## sub agent 审查结论

已安排只读 sub agent 审查。审查没有发现 P1 或 P2。

审查发现 2 个 P3：

- 测试没有直接断言 provider-ready messages 中的 `scaffold_phase_metadata`。
- 测试缺少 verifier feedback 未通过后进入 repair 的端到端路径。

上述 P3 均已处理：

- 单元测试直接断言 `request.prepared_messages` 中的 `scaffold_phase_metadata`。
- 新增 `task_002_planner_coder_verifier_repair.yaml` 和集成测试，覆盖 `verifier -> repair -> verifier -> final`。

审查记录保存到 `docs/v2/review/implementation/stage-09-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 10。进入下一阶段前，Stage 09 commit 必须只包含当前阶段相关代码、测试、fixture、阶段日志和审查记录。
