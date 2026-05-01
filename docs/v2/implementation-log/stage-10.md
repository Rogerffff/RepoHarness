# Stage 10: mock provider and provider artifacts

## 本阶段目标

本阶段目标是在 Stage 07 的 `ModelClient` 协议基础上新增稳定、无网络、无密钥的 mock provider，并补齐 provider artifact 和 provider 错误分类路径。本阶段不接入 DeepSeek、OpenAI 或其他真实 provider，不改变第一版 replay-only 最小闭环。

## 本阶段实现内容

- 新增 `MockProviderClient`：
  - `provider=mock`
  - 默认模型标识为 `mock-provider-v0`
  - 默认场景 `tool_call_success` 可以按 `edit_file -> run_tests -> final answer` 完成固定小任务。
  - 支持 `final_answer` 场景。
  - 支持错误场景 `auth_error`、`rate_limit`、`timeout`、`invalid_response`、`malformed_tool_call`、`context_limit`、`provider_error`。
- 扩展 `ModelCallEvent`：
  - 新增 `provider` 字段。
  - replay provider 和 mock provider 的 `model_call_completed` event 均记录 provider。
- 扩展 `ModelConfig`：
  - 新增 `provider_specific_options`，用于 provider adapter 内部配置。
  - mock 场景配置保留在 provider adapter 边界内，不进入通用 `ModelClient` 协议语义。
- 修改 `ModelClient` factory：
  - 支持 `model.provider=mock`。
  - 保留 replay 和 fake provider 的既有兼容路径。
  - 继续拒绝 DeepSeek、OpenAI 等真实 provider，因为真实 provider 属于 Stage 11。
- 新增 provider raw artifact 写入：
  - `raw_mock_provider_request`
  - `raw_mock_provider_response`
  - artifact metadata 记录 `redaction_status=redacted`、`retention_policy=provider_raw_redacted`、`budget_policy=preserve_json`。
- 新增递归脱敏：
  - 脱敏 `api_key`、`authorization`、`password`、`secret`、`token` 和 `*_token` 等凭证字段。
  - 不误脱敏 `max_output_tokens`、`input_tokens`、`output_tokens` 等普通配置事实。
  - 屏蔽 Authorization / Bearer 文本、OpenAI 风格 key 和长随机密钥形态。
- 新增 `inspect-mock-provider-smoke` CLI：
  - 可以读取单个 run directory 或包含单个 mock run 的父目录。
  - 生成 `mock_provider_smoke_report.json`。
  - 支持 `--assert-accepted` 和 `--assert-export-clean`。
  - 检查 raw provider artifact 是否存在、是否标记已脱敏、是否包含禁入字段。
- 收紧训练导出 eligibility：
  - `run_outcome=failed`、`agent_stop_reason=model_error` 或任意 `model_call_completed.model_error_type` 会使样本不可训练。
  - provider error assistant transcript 不再标记为 trainable。
  - provider error run 默认进入审计诊断路径，不进入正式训练 JSONL。

## 修改的主要文件

- `src/repo_harness/model_client/mock.py`
- `src/repo_harness/model_client/mock_smoke.py`
- `src/repo_harness/model_client/schemas.py`
- `src/repo_harness/model_client/replay.py`
- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/model_client/__init__.py`
- `src/repo_harness/config/schemas.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/evaluation/experiment.py`
- `src/repo_harness/cli/main.py`
- `src/repo_harness/agent_loop/loop.py`
- `src/repo_harness/export/exporter.py`
- `tests/fixtures/run_configs/v2/mock_provider_smoke.yaml`
- `tests/unit/test_mock_provider.py`
- `tests/integration/test_mock_provider_e2e.py`
- `tests/unit/test_model_client_factory.py`
- `tests/unit/test_experiment_config.py`

## 生成的机器可读产物

阶段验收 smoke run 生成了：

- `runs/v2-mock-provider-smoke-20260501T204508Z/stage10_task_001/run_config_facts.json`
- `runs/v2-mock-provider-smoke-20260501T204508Z/stage10_task_001/run_metadata.json`
- `runs/v2-mock-provider-smoke-20260501T204508Z/stage10_task_001/events.jsonl`
- `runs/v2-mock-provider-smoke-20260501T204508Z/stage10_task_001/artifacts.json`
- `runs/v2-mock-provider-smoke-20260501T204508Z/stage10_task_001/metrics.json`
- `runs/v2-mock-provider-smoke-20260501T204508Z/exports/sft.jsonl`
- `runs/v2-mock-provider-smoke-20260501T204508Z/exports/rl.jsonl`
- `runs/v2-mock-provider-smoke-20260501T204508Z/mock_provider_smoke_report.json`

该 smoke report 记录：

- `status=accepted`
- `provider=mock`
- `final_verifier_status=accepted`
- `run_outcome=success`
- `export_audit_status=clean`
- `raw_artifact_redaction_status=redacted`
- `raw_artifact_redaction_checks.secret_like_fields_redacted=true`
- `raw_artifact_redaction_checks.no_authorization_plaintext=true`
- `raw_artifact_redaction_checks.no_raw_request_body=true`
- `raw_artifact_redaction_checks.no_reasoning_summary=true`
- `raw_artifact_redaction_checks.no_openai_style_key=true`

## 运行的验证命令

```bash
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_model_client_factory.py tests/unit/test_mock_provider.py tests/integration/test_mock_provider_e2e.py -q
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_model_client_factory.py tests/unit/test_mock_provider.py tests/integration/test_mock_provider_e2e.py tests/unit/test_replay_model.py tests/unit/test_fake_model.py tests/unit/test_experiment_config.py tests/integration/test_agent_loop_replay.py tests/integration/test_experiment_runner.py -q
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness run-task tests/fixtures/tasks/task_001.yaml --config tests/fixtures/run_configs/v2/mock_provider_smoke.yaml --output-dir runs/v2-mock-provider-smoke-20260501T204508Z
PATH=.venv/bin:$PATH repo-harness inspect-run runs/v2-mock-provider-smoke-20260501T204508Z/stage10_task_001
PATH=.venv/bin:$PATH repo-harness export runs/v2-mock-provider-smoke-20260501T204508Z --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/v2-mock-provider-smoke-20260501T204508Z --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-mock-provider-smoke-20260501T204508Z/exports --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-mock-provider-smoke-20260501T204508Z/exports --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-mock-provider-smoke-20260501T204508Z/exports --all --format rl_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-mock-provider-smoke --run-dir runs/v2-mock-provider-smoke-20260501T204508Z --output runs/v2-mock-provider-smoke-20260501T204508Z/mock_provider_smoke_report.json --assert-accepted --assert-export-clean
rg -n "raw_mock_provider|raw_provider|authorization|reasoning_summary|raw_request_body|sk-" runs/v2-mock-provider-smoke-20260501T204508Z/exports
```

## 验证结果

- Stage 10 定向测试通过，12 个测试通过。
- 相关 provider、experiment 和 agent loop 回归测试通过，39 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，286 个测试通过。
- mock provider smoke run 成功，`inspect-run` 显示 provider 为 `mock`，run outcome 为 `success`，final verifier status 为 `accepted`。
- SFT 和 RL 导出均通过 audit，且均包含 1 个 trainable 样本。
- `inspect-mock-provider-smoke --assert-accepted --assert-export-clean` 通过。
- 对导出目录运行禁入字段搜索没有输出，说明导出 payload 中没有 raw provider artifact、Authorization、reasoning summary、raw request body 或 OpenAI 风格 key。

## 正例证据

- `model.provider=mock` 可以通过 factory 构造 `MockProviderClient`。
- mock provider 通过正式 Agent Loop、Workspace Adapter、RunRecorder、feedback verifier 和 final verifier 完成任务，不绕过既有执行路径。
- `model_call_completed` event 记录 `provider=mock`、`model_id=mock-provider-v0`、token usage 和 raw provider artifact refs。
- raw provider request / response 只以受控 artifact 形式保存，并在 artifact manifest 中标记为已脱敏。
- provider-specific secret、Authorization header 形态、Bearer 文本和 OpenAI 风格 key 不出现在 smoke report 检查范围内。
- provider error 场景会生成结构化 `model_error_type`。
- provider error run 的 assistant transcript 不再作为 trainable target。
- provider error run 的导出 eligibility 为 invalid，原因包含 `model_error:<type>`。
- replay provider 和 fake provider 相关回归测试仍通过。

## 负例证据

- 没有实现 DeepSeek provider。
- 没有实现 OpenAI provider。
- 没有进行真实网络请求。
- 没有读取 `DEEPSEEK_API_KEY`、`OPENAI_API_KEY` 或 `reference/deepseek_api.md`。
- raw provider request、raw provider response、reasoning summary、raw request body 和 Authorization header 没有进入训练导出。
- provider error run 没有被当成正式 trainable 样本。
- unknown tool、Permission System、feedback verifier、formal final verifier 的边界没有被 mock provider 改写。

## 允许降级项

- mock provider 是稳定回归 provider，不追求真实模型能力。
- mock provider 的 tool-call 策略是固定小任务路径，用于协议和 artifact 验收。
- raw provider artifact 在本阶段采用红acted JSON artifact，不实现外部 secret vault 或长期归档策略。
- 本阶段只为 Stage 11 真实 provider 留出 provider-specific options 和 error type 结构，不提前实现真实 provider。

## 禁止降级项

- 不能把 provider raw request、raw response、reasoning summary 或隐藏思考内容放入训练 payload。
- 不能把 provider error assistant 内容作为 trainable target。
- 不能把 provider error run 标记为 clean trainable 样本。
- 不能在 artifact、metadata、export、错误日志或 smoke report 中打印 API key、Authorization header 或本地 secret 文件内容。
- 不能绕过 RunRecorder 写 provider artifact。
- 不能绕过 Workspace Adapter、Permission System 或 tool call / tool result 配对。
- 不能提前把 Stage 11 的真实 provider 伪装成 Stage 10 完成项。

## 已知限制

- mock provider 的默认成功策略只覆盖固定 fixture task，用于回归和 smoke，不代表真实模型能力。
- provider raw artifact 的脱敏策略覆盖当前定义的凭证形态；Stage 11 真实 provider 会继续扩展 DeepSeek 和 OpenAI 的具体请求、响应、错误和 token usage 脱敏规则。
- `inspect-mock-provider-smoke` 是 mock provider 专用检查；真实 provider 会在 Stage 11 使用独立的 smoke report。

## 是否偏离设计文档

未发现需要记录的设计冲突。本阶段按 Stage 10 范围实现 mock provider、provider artifact 和 provider 错误分类，没有提前接入 DeepSeek 或 OpenAI。

## sub agent 审查结论

已安排只读 sub agent 审查。审查发现 1 个 P1、1 个 P2 和 3 个 P3 建议：

- P1：provider error run 可能被导出为 clean trainable 样本。
- P2：raw mock provider request 初始实现没有递归脱敏 provider-specific secrets。
- P3：需要补充 provider error 不进入训练样本的测试。
- P3：需要补充 provider-specific secret redaction 测试。
- P3：需要让 smoke report 暴露更细粒度的 redaction checks。

处理结果：

- P1 已修复：Agent Loop 在 `model_error_type` 存在时不把 assistant transcript 标记为 trainable；Training Exporter 对 `run_outcome=failed`、`agent_stop_reason=model_error` 和 `model_call_completed.model_error_type` 执行 invalid eligibility。
- P2 已修复：mock provider raw request / response 写入前执行递归脱敏，并通过 provider-specific secret fixture 覆盖。
- P3 均已处理：新增 provider error E2E 导出测试、provider-specific secret redaction 单元测试和 smoke report redaction checks。

审查记录保存到 `docs/v2/review/implementation/stage-10-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 11。进入下一阶段前，Stage 10 commit 必须只包含当前阶段相关代码、测试、fixture、阶段日志和审查记录。
