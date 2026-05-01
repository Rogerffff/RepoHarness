# Stage 07 只读审查记录

## 审查方式

本阶段是高风险阶段，安排了只读 sub agent 审查。审查 agent 没有修改文件。审查分为初审和修复后复审。

## 审查重点

- 是否严格限于 Stage 07 的 `ModelClient` protocol、factory、replay/fake 兼容层和 `simple_react` scaffold registry。
- 是否提前实现 Stage 08 `single_shot_patch`、Stage 10 mock provider 或 Stage 11 real provider。
- Agent Loop 是否通过 `ModelRequestContext` 调用模型，并记录 `model_call_id`、turn、`scaffold_phase`、budget state、`run_config_facts_ref` 和 tool schema snapshot ref。
- ReplayModelClient 和 FakeModelClient 是否保持第一版 replay 兼容，不把 `ReplayScript.expected_outcome` 或注释泄漏给模型可见响应。
- allowed tools policy、`test_feedback_policy=disabled`、直接 `run_tests` 和 `bash pytest` 绕过是否真实被限制。
- `feedback_tests_passed_policy` 的 `stop_immediately`、`require_model_final` 和 `continue` 行为是否符合文档。
- `run_config_facts.json`、`run_metadata.json` 和 metrics 是否记录 scaffold 与 resolved feedback policy。
- 是否破坏第一版 replay、legacy export、RunRecorder、Workspace Adapter 或 tool call / tool result 配对。

## 初审发现

### P1

1. `public_only` 和 `structured_public_feedback` 仍会运行隐藏 suite。
   - 位置：`src/repo_harness/verifier/runner.py`
   - 原因：`run_feedback_public()` 传入空的 fail-to-pass 和 pass-to-pass 列表，但 `_run()` 使用 `fail_to_pass_tests or verifier_config.fail_to_pass_tests`，导致显式空列表回退到隐藏 suite。
   - 修复：`_run()` 改为 `is None` 判断，只有未传入时才使用 verifier config 的隐藏 suite。
   - 回归测试：`tests/unit/test_test_feedback_policy.py` 现在读取 public feedback artifact，断言 `fail_to_pass`、`pass_to_pass` 均为零，且 `test_cases` 为空。

### P2

1. `run_metadata.json` 没有直接记录 scaffold facts 和 resolved feedback policy。
   - 位置：`src/repo_harness/run_metadata/schemas.py`
   - 原因：这些事实存在于 `run_config_facts.json`，但 Stage 07 要求 `run_metadata.json` 中也能直接看到 `scaffold_id`、`scaffold_version` 和 resolved feedback policy。
   - 修复：`RunMetadata` 新增 `scaffold_id`、`scaffold_version`、`scaffold_facts`、`feedback_policy_resolution`、`test_feedback_policy`、`feedback_tests_passed_policy` 和 `hidden_feedback_visible_to_model`；writer 从 `run_config_facts.json` 填充这些字段。
   - 回归测试：`tests/unit/test_feedback_tests_passed_policy.py` 覆盖 `run_metadata.json` 中的 scaffold 与 feedback policy 字段。

### P3

未发现必须记录的 P3 问题。

## 复审结果

复审确认：

- P1 已关闭：公开反馈路径的显式空 suite 不再回退隐藏 suite，public feedback artifact 已有回归断言。
- P2 已关闭：`run_metadata.json` 直接写入 scaffold 与 resolved feedback policy summary，测试已覆盖。
- 未发现新的 P1 或 P2。
- 未发现提前实现 Stage 08、Stage 10 或 Stage 11 的情况。

## 审查验证

sub agent 复审运行：

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_test_feedback_policy.py tests/unit/test_feedback_tests_passed_policy.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_replay_model.py tests/unit/test_fake_model.py tests/unit/test_model_client_factory.py tests/unit/test_context_builder.py tests/unit/test_agent_loop_protocol.py tests/integration/test_agent_loop_replay.py -q
```

验证结果：

- `8 passed`
- `34 passed`

## 主流程补充验证

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_test_feedback_policy.py tests/unit/test_feedback_tests_passed_policy.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_replay_model.py tests/unit/test_fake_model.py tests/unit/test_model_client_factory.py tests/unit/test_context_builder.py tests/unit/test_agent_loop_protocol.py tests/integration/test_agent_loop_replay.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

验证结果：

- feedback policy 定向测试通过，8 个测试通过。
- ModelClient、ContextBuilder、Agent Loop 和 replay integration 相关测试通过，34 个测试通过。
- 编译通过。
- 全量测试通过，258 个测试通过。

## 结论

初审 P1 和 P2 均已修复，复审未发现新的 P1 或 P2。Stage 07 可以提交，并可以进入 Stage 08。
