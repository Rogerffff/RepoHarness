# Stage 07: ModelClient protocol, replay/fake factory, and scaffold registry

## 本阶段目标

本阶段目标是把第一版 replay-only 模型调用路径迁移到通用 `ModelClient` protocol，并引入最小 scaffold registry。Stage 07 只迁移 `simple_react`，只支持 replay 和 fake provider，不实现 `single_shot_patch`、mock provider 或真实 provider。

## 本阶段实现内容

- 新增 `model_client/protocol.py`：
  - 定义 `ModelClient.generate(request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse`。
- 新增 `model_client/factory.py`：
  - 根据 `RunConfig.model.provider` 构造 replay 或 fake client。
  - 对 unsupported provider 给出清晰 `ConfigError`。
- 修改 ReplayModelClient/FakeModelClient：
  - 新路径通过 `ModelRequestContext` 调用。
  - 保留 legacy `prepared_messages` 调用兼容，避免破坏既有单元测试和外部测试入口。
  - raw replay request 记录 `model_call_id`、scaffold、allowed tools、budget state、tool schema snapshot ref 和 `run_config_facts_ref`。
  - raw replay response 继续只写 model-visible payload，不写 `expected_outcome` 或注释。
- 新增 scaffold registry：
  - `ScaffoldDefinition`
  - `ScaffoldRegistry`
  - `build_scaffold`
  - `resolve_feedback_policy`
  - `resolve_allowed_tools`
  - `tool_registry_for_allowed_tools`
- 迁移 `simple_react`：
  - 作为 `ScaffoldDefinition` 注册。
  - 保持第一版默认行为：`test_feedback_policy=oracle_hidden_feedback`，`feedback_tests_passed_policy=stop_immediately`。
- 扩展 runtime config：
  - 新增 `test_feedback_policy`。
  - 新增 `feedback_tests_passed_policy`。
  - 用户不能配置 `not_applicable`；它只作为 disabled 测试反馈策略的解析后事实。
- 修改 ContextBuilder：
  - system prompt 不再写死 `simple_react agent`。
  - scaffold 只提供 prompt fragment 和策略元数据，ContextBuilder 仍负责最终初始消息和可见性隔离。
- 修改 Agent Loop：
  - 依赖通用 `ModelClient`。
  - 每轮构造 `ModelRequestContext` 后调用模型。
  - `model_call_started` 和 `model_call_completed` 事件记录 turn、scaffold phase、budget state、allowed tools、tool schema snapshot ref 和 `run_config_facts_ref`。
  - allowed tools policy 真实限制已知工具；被 scaffold 禁止的工具在进入 permission system 前生成配对 `ToolResult`。
  - `test_feedback_policy=disabled` 时，直接 `run_tests` 不可用，`bash` 中的 `pytest`、`python -m pytest`、`tox`、`nox` 或任务 test command 路由到测试反馈策略检查并被拒绝。
  - `feedback_tests_passed_policy=stop_immediately` 保持第一版行为。
  - `require_model_final` 在 feedback verifier accepted 后继续消费下一轮模型 final answer。
  - `continue` 把 accepted feedback 当成普通观察，允许后续修改，并由 formal final verifier 产生最终成败。
- 修改 Eval Runner：
  - 从 scaffold registry 解析 `runtime.scaffold_id`。
  - 写入只包含 resolved allowed tools 的 tool schema snapshot。
  - 写入 resolved feedback policy 到 `run_config_facts.json`、`run_metadata.json` 和 metrics。
  - 通过 model client factory 构造 replay/fake client。
- 修改 verifier feedback：
  - `public_only` 和 `structured_public_feedback` 使用 public feedback 路径，不运行隐藏 fail-to-pass/pass-to-pass suite。
  - `oracle_hidden_feedback` 才运行隐藏 suite，并在模型可见结果中显示隐藏反馈。

## 修改的主要文件

- `src/repo_harness/model_client/protocol.py`
- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/model_client/replay.py`
- `src/repo_harness/model_client/__init__.py`
- `src/repo_harness/scaffolds/schemas.py`
- `src/repo_harness/scaffolds/registry.py`
- `src/repo_harness/scaffolds/policies.py`
- `src/repo_harness/scaffolds/simple_react.py`
- `src/repo_harness/scaffolds/__init__.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/agent_loop/schemas.py`
- `src/repo_harness/context/builder.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/evaluation/metrics.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/__init__.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/run_metadata/writer.py`
- `src/repo_harness/tools/minimal.py`
- `src/repo_harness/verifier/runner.py`
- `tests/unit/test_model_client_factory.py`
- `tests/unit/test_feedback_tests_passed_policy.py`
- `tests/unit/test_test_feedback_policy.py`
- `tests/unit/test_agent_loop_protocol.py`
- `tests/unit/test_context_builder.py`
- `tests/unit/test_experiment_config.py`
- `tests/integration/test_agent_loop_replay.py`
- `tests/fixtures/run_configs/v2/replay_require_model_final.yaml`

## 生成的机器可读产物

阶段验收 smoke run 生成了：

- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/run_config_facts.json`
- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/run_metadata.json`
- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/metrics.json`
- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/events.jsonl`
- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/artifacts.json`
- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/final.patch`
- `runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final/final.diff`

该 smoke run 证明 `require_model_final` 下 agent stop reason 为 `final_answer`，并且 `run_metadata.json` 和 `run_config_facts.json` 都记录了 `feedback_policy_resolution`。

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_replay_model.py tests/unit/test_fake_model.py tests/unit/test_model_client_factory.py tests/unit/test_context_builder.py tests/unit/test_agent_loop_protocol.py tests/unit/test_feedback_tests_passed_policy.py tests/unit/test_test_feedback_policy.py tests/integration/test_agent_loop_replay.py -q
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v2/replay_require_model_final.yaml --output-dir runs/v2-stage07-smoke-20260501T194000Z --run-id stage07-require-model-final
PATH=.venv/bin:$PATH repo-harness inspect-run runs/v2-stage07-smoke-20260501T194000Z/stage07-require-model-final
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_test_feedback_policy.py tests/unit/test_feedback_tests_passed_policy.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_replay_model.py tests/unit/test_fake_model.py tests/unit/test_model_client_factory.py tests/unit/test_context_builder.py tests/unit/test_agent_loop_protocol.py tests/integration/test_agent_loop_replay.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
```

## 验证结果

- Stage 07 验收测试通过，42 个测试通过。
- Stage 07 smoke run 成功，`inspect-run` 显示 run metadata、run config facts 和 tool schema snapshot 均为 ok。
- 修复 P1/P2 后，feedback policy 定向测试通过，8 个测试通过。
- 修复 P1/P2 后，ModelClient、ContextBuilder、Agent Loop 和 replay integration 相关测试通过，34 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，258 个测试通过。

## 正例证据

- `ModelClient` factory 可以构造 replay 和 fake client。
- Agent Loop 通过 `ModelRequestContext` 调用模型。
- `model_call_started` 和 `model_call_completed` 事件记录 `model_call_id`、turn、scaffold phase、budget state、allowed tools、tool schema snapshot ref 和 `run_config_facts_ref`。
- `simple_react` 默认行为与第一版 replay 兼容，`run_tests accepted` 后可以 stop immediately。
- `require_model_final` 可以在 accepted feedback 后继续消费 replay final answer。
- `continue` 可以在 accepted feedback 后继续执行后续修改，并由 formal final verifier 保留负样本结果。
- `test_feedback_policy=disabled` 下，`run_tests` 不进入 allowed tool schema snapshot，直接 `run_tests` 和 `bash pytest` 都不能获得测试反馈。
- `public_only` 和 `structured_public_feedback` 的 feedback artifact 不包含隐藏 suite 计数或 declared hidden test cases。
- `oracle_hidden_feedback` 保留第一版 replay 的隐藏反馈可见行为，并在 run facts 中显式标记。
- `run_metadata.json` 直接记录 `scaffold_id`、`scaffold_version`、`scaffold_facts`、`feedback_policy_resolution`、`test_feedback_policy` 和 `feedback_tests_passed_policy`。

## 负例证据

- 不支持的 provider 会被 factory 拒绝。
- 不支持的 scaffold id 会被 registry 拒绝。
- 用户配置 `feedback_tests_passed_policy=not_applicable` 会 schema validation fail。
- `test_feedback_policy=disabled` 下，已知但不允许的 `run_tests` 在进入 permission system 前被拒绝并生成配对 `ToolResult`。
- `test_feedback_policy=disabled` 下，`bash` 请求测试命令被路由到 `run_tests` 策略检查并拒绝，不能绕过测试反馈策略。
- public feedback 路径传入显式空 hidden suite 时不会回退到 verifier config 的隐藏 suite。

## 允许降级项

- Stage 07 只注册和运行 `simple_react`。
- Stage 07 只支持 replay 和 fake provider。
- Fake provider 仍是 replay-compatible deterministic client，不是 Stage 10 mock provider。
- public feedback 的最小实现使用任务 test command 的公开反馈路径，并禁止 declared hidden suite；更细的 public smoke suite 配置留到后续任务源扩展阶段。

## 禁止降级项

- 不能绕过 `ModelRequestContext` 调用模型。
- 不能把 `ReplayScript.expected_outcome`、注释、baseline 原始日志、reward-only 字段或 hidden evaluator metadata 放进模型可见内容。
- 不能让 `test_feedback_policy=disabled` 下的模型通过 `run_tests` 或 `bash pytest` 获得测试反馈。
- 不能让 public feedback 执行或暴露 hidden fail-to-pass / pass-to-pass suite。
- 不能把 `feedback_tests_passed` stop reason 用在 resolved policy 为 `not_applicable` 的 run。
- 不能绕过 RunRecorder、Workspace Adapter、Permission System 或 tool call / tool result 配对。

## 已知限制

- Stage 07 不实现 `single_shot_patch`；该能力属于 Stage 08。
- Stage 07 不实现 planner/coder/verifier；该能力属于 Stage 09。
- Stage 07 不实现 mock provider；该能力属于 Stage 10。
- Stage 07 不实现 DeepSeek 或 OpenAI provider；真实 provider 属于 Stage 11。
- Stage 07 不新增 Docker backend；Docker 扩展路径属于 Stage 14。

## 是否偏离设计文档

未发现需要记录的设计冲突。本阶段按照文档要求只做 ModelClient 解耦、replay/fake 兼容、`simple_react` scaffold registry 和反馈策略解析。未提前实现后续阶段能力。

## sub agent 审查结论

已安排只读 sub agent 审查。初审发现 1 个 P1 和 1 个 P2：

- P1：public feedback 路径仍因 `or` 回退运行隐藏 suite。
- P2：`run_metadata.json` 未直接记录 scaffold facts 和 resolved feedback policy。

上述问题均已修复，并补充回归测试。复审未发现新的 P1 或 P2。审查记录保存到 `docs/v2/review/implementation/stage-07-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 08。进入下一阶段前，Stage 07 commit 必须只包含当前阶段相关代码、测试、fixture、阶段日志和审查记录。
