# Stage 09 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了可以在 Stage 09 范围内完成的 P3 项。

## 审查重点

- 是否严格限于 Stage 09 的 `planner_coder_verifier` scaffold。
- 是否提前实现 Stage 10 mock provider 或 Stage 11 real provider。
- planner、coder、verifier、repair、final 是否是同一个 Agent Loop 内的顺序 phase。
- 是否新增后台多智能体系统、mailbox、远程代理、额外 worktree 或复杂团队协作。
- Agent Loop 是否记录 phase transition event。
- 每轮模型调用是否记录当前 `scaffold_phase` 并使用 phase-specific allowed tools。
- provider-ready messages 是否包含当前 phase metadata。
- planner phase 是否禁止 `edit_file`。
- verifier 和 repair phase 的 `run_tests` 是否仍受 resolved `test_feedback_policy` 和测试预算限制。
- verifier phase 的 feedback verifier 是否没有替代 formal final verifier。
- run metadata 和 run config facts 是否记录 scaffold id、scaffold version 和 phase policy。
- 是否破坏 `simple_react`、`single_shot_patch`、replay/fake provider、tool call/tool result 配对或 Permission System 入口边界。
- 是否泄漏 `expected_outcome`、脚本注释、hidden metadata、baseline/final verifier 信息到模型可见内容或训练导出。

## 审查发现

### P1

未发现。

### P2

未发现。

### P3

1. 测试没有直接断言 provider-ready messages 中的 `scaffold_phase_metadata`。
   - 原因：单元测试名称覆盖 phase context，但初始断言只检查了 `ModelRequestContext.scaffold_phase` 和 allowed tool definitions。
   - 处理：单元测试新增对 `request.prepared_messages[-1]["content"]["scaffold_phase_metadata"]` 的直接断言。

2. 测试缺少 failed feedback 后进入 repair 的端到端路径。
   - 原因：初始集成测试覆盖 `planner -> coder -> verifier -> final` 和 planner 禁止编辑，但没有覆盖 `verifier -> repair -> verifier -> final`。
   - 处理：新增 `tests/fixtures/replays/task_002_planner_coder_verifier_repair.yaml` 和集成测试，第一次 feedback 未通过后进入 repair，repair 后再次 verifier，并最终进入 final。

## 审查正例证据

- 没有看到 Stage 10 mock provider 或 Stage 11 real provider 的提前实现。
- `planner/coder/verifier/repair/final` 是同一个 `AgentLoop` 内的 `state.current_phase` 顺序推进。
- 没有新增 mailbox、远程代理、额外 worktree 或团队协作调度。
- `scaffold_phase_transition` event 记录 `from_phase`、`to_phase`、`reason`、`phase_sequence`、`phase_transition_policy` 和 `scaffold_version`。
- 每轮模型调用记录当前 `scaffold_phase`，并按 phase 传入 allowed tool definitions。
- planner 阶段没有 `edit_file`。
- verifier 阶段是否有 `run_tests` 受 resolved `test_feedback_policy` 影响。
- `run_tests` 仍走 feedback verifier；formal final verifier 仍由 agent 停止后的 `verifier_final` 事件记录。
- `run_config_facts.json` 和 `run_metadata.json` 记录了 scaffold id、scaffold version、allowed tools policy、phase policy 和 feedback policy。
- replay 的 `expected_outcome` 仍通过 `model_visible_payload()` 排除。

## 审查负例证据

- 没有 mock provider 或真实 provider 被接受的运行路径。
- 没有后台多智能体相关事件或对象。
- planner 阶段禁止编辑工具时，在 Permission System 前阻断。
- `feedback_tests_passed_policy=require_model_final` 时，feedback accepted 不会直接以 `feedback_tests_passed` 停止。
- verifier feedback 没有被当成 formal final verifier。

## 修复后验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_scaffold_planner_coder_verifier.py tests/integration/test_planner_coder_verifier.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_agent_loop_protocol.py tests/unit/test_scaffold_single_shot_patch.py tests/integration/test_single_shot_patch.py tests/unit/test_experiment_config.py tests/integration/test_agent_loop_replay.py tests/integration/test_experiment_runner.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- Stage 09 定向测试通过，6 个测试通过。
- 相关回归测试通过，43 个测试通过。
- 编译通过。
- 全量测试通过，277 个测试通过。

## 结论

审查没有发现 P1 或 P2。P3 已在 Stage 09 范围内修复并重新验证。Stage 09 可以提交，并可以进入 Stage 10。
