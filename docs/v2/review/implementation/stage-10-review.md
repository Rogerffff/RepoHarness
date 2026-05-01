# Stage 10 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了 P1、P2 和可以在 Stage 10 范围内处理的 P3 项，并重新运行验证。

## 审查重点

- 是否严格限于 Stage 10 的 mock provider、provider artifact 和 provider 错误分类。
- 是否提前实现 Stage 11 DeepSeek、OpenAI 或其他真实 provider。
- mock provider 是否继续通过 `ModelClient`、Agent Loop、Workspace Adapter、RunRecorder 和 Verifier 既有边界运行。
- raw provider request 和 raw provider response 是否只作为受控 artifact 保存。
- raw provider artifact 是否脱敏。
- provider raw response、raw request body、reasoning summary、Authorization header 或 API key 是否进入训练 payload。
- provider error 是否有结构化 `model_error_type`。
- provider error run 是否不会被导出为正式 trainable 样本。
- replay provider、fake provider、simple_react、single_shot_patch 和 planner_coder_verifier 是否保持兼容。
- tool call / tool result 配对、Permission System 入口和 unknown tool 边界是否保持不变。

## 审查发现

### P1

1. provider error run 可能被导出为 clean trainable 样本。
   - 风险：mock provider 的错误响应会产生 assistant transcript；如果 exporter 只看 transcript 是否存在，错误响应可能进入 SFT 或 RL 训练目标。
   - 处理：Agent Loop 在 `response.model_error_type` 存在时将 assistant transcript 标记为 `trainable=false`；Training Exporter 在 `run_outcome=failed`、`agent_stop_reason=model_error` 或任意 `model_call_completed.model_error_type` 存在时将样本判为 invalid；invalid reason 记录为 `model_error:<type>`。

### P2

1. raw mock provider request 初始实现没有递归脱敏 provider-specific secrets。
   - 风险：Stage 11 真实 provider 会使用 provider-specific options；如果 Stage 10 不先建立递归脱敏边界，后续密钥或 provider 特有敏感配置可能进入 artifact。
   - 处理：mock provider raw request / response 写入前递归脱敏 `api_key`、`authorization`、`password`、`secret`、`token` 和 `*_token` 字段，并过滤 Bearer、Authorization 文本、OpenAI 风格 key 和长随机密钥形态。脱敏规则已收窄，避免误脱敏 `max_output_tokens`、`input_tokens`、`output_tokens` 等普通配置事实。

### P3

1. 需要补充 provider error 不进入训练样本的测试。
   - 处理：新增 mock provider `auth_error` E2E 导出测试，断言 SFT JSONL 为空、audit sample 为 invalid、invalid reason 为 `model_error:auth_error`，并且 assistant transcript 没有 trainable 标记。

2. 需要补充 provider-specific secret redaction 测试。
   - 处理：新增单元测试，覆盖 `provider_specific_options.api_key`、嵌套 `token` 和 `authorization` 字段脱敏，且原始 secret 字符串不出现在 raw artifact 文本中。

3. 需要让 smoke report 暴露更细粒度的 redaction checks。
   - 处理：`mock_provider_smoke_report.json` 新增 `raw_artifact_redaction_checks`，包含 `secret_like_fields_redacted`、`no_authorization_plaintext`、`no_raw_request_body`、`no_reasoning_summary` 和 `no_openai_style_key`。

## 审查正例证据

- `model.provider=mock` 通过 factory 构造 mock provider；`model.provider=deepseek` 仍被拒绝，说明没有提前实现 Stage 11。
- mock provider 默认成功路径通过真实 Agent Loop 执行 `edit_file`、`run_tests` 和最终回答。
- raw provider request 和 raw provider response 通过 RunRecorder 写入 artifact manifest。
- artifact metadata 记录 `redaction_status=redacted` 和 `retention_policy=provider_raw_redacted`。
- smoke report 的 redaction checks 全部为 true。
- provider error 场景有结构化 `model_error_type`。
- provider error run 被 exporter 判为 invalid，不进入正式训练 JSONL。
- replay/fake provider、experiment runner 和 agent loop 相关回归测试通过。

## 审查负例证据

- 没有 DeepSeek、OpenAI 或真实网络 provider 的 accepted 路径。
- 没有 API key、Authorization header 或本地 secret 文件内容写入 artifact、metadata、export 或 smoke report。
- 没有 provider raw request body、provider raw response、reasoning summary 或隐藏思考内容进入训练 payload。
- 没有绕过 RunRecorder、Workspace Adapter、Permission System 或 formal final verifier。

## 修复后验证

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
PATH=.venv/bin:$PATH repo-harness inspect-mock-provider-smoke --run-dir runs/v2-mock-provider-smoke-20260501T204508Z --output runs/v2-mock-provider-smoke-20260501T204508Z/mock_provider_smoke_report.json --assert-accepted --assert-export-clean
```

验证结果：

- Stage 10 定向测试通过，12 个测试通过。
- 相关 provider 和 agent loop 回归测试通过，39 个测试通过。
- 编译通过。
- 全量测试通过，286 个测试通过。
- mock provider smoke run accepted。
- SFT 和 RL 导出 audit 均 clean。

## 结论

审查提出的 P1 和 P2 已修复并通过测试覆盖。P3 已在 Stage 10 范围内处理。Stage 10 可以提交，并可以进入 Stage 11。
