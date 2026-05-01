# Stage 11 只读审查记录

## 审查方式

本阶段安排了只读 sub agent 审查。审查 agent 没有修改文件。主流程根据审查结论修复了 P1、P2 和可以在 Stage 11 范围内处理的 P3 项，并重新运行验证。

## 审查重点

- 是否严格限于 Stage 11 的真实 provider 最小接入、provider 错误路径和 smoke report。
- 是否以 DeepSeek 作为 primary provider。
- 是否把 OpenAI 限制为 DeepSeek fallback provider，而不是新的普通 primary provider。
- 是否检查 DeepSeek 和 OpenAI 官方文档。
- 是否保留 replay、fake 和 mock provider 的既有兼容路径。
- raw provider request 和 raw provider response 是否只作为受控 artifact 保存。
- raw provider artifact 是否脱敏。
- provider raw response、raw request body、reasoning summary、Authorization header 或 API key 是否进入训练 payload。
- 无凭证 skip 是否不会被伪装成真实 provider accepted。
- fallback success 是否不会被伪装成 DeepSeek primary success。
- provider error 是否有结构化 `model_error_type`。
- 是否绕过 RunRecorder、Workspace Adapter、Permission System、Agent Loop 或 formal final verifier。

## 审查发现

### P1

1. DeepSeek model constraint 初始实现不够严格。
   - 风险：如果允许 `deepseek-chat`、`deepseek-reasoner` 或任意模型字符串，Stage 11 会偏离用户要求，且可能把 deprecated model 记成正式 smoke 路径。
   - 处理：新增 DeepSeek model normalization 和 validation。默认模型固定为 `deepseek-v4-pro`；允许 `deepseek-v4-pro` 和 `deepseek-v4-flash`；拒绝 `deepseek-chat`、`deepseek-reasoner` 和其他未允许模型。新增单元测试覆盖。

2. DeepSeek credential strategy 初始实现默认读取 local secret file。
   - 风险：默认读取 `reference/deepseek_api.md` 不符合默认 env-only 凭证策略，也可能让本地 secret helper 行为被误认为常规运行事实。
   - 处理：DeepSeek credential resolver 默认只读取 `DEEPSEEK_API_KEY`。local secret file 只有显式 `--allow-local-secret-file` 或 provider option 才启用；`REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE=1` 可以强制禁用；report 只记录 `credential_source=local_secret_file_redacted`，不记录 key 值、文件内容或完整路径内容。新增单元和集成测试覆盖。

### P2

1. OpenAI 初始实现可能暴露为 primary provider。
   - 风险：用户要求 DeepSeek 是 primary provider，OpenAI 只是备用 fallback。如果 OpenAI 可以作为普通 primary provider 使用，会破坏 provider 验收口径。
   - 处理：factory、Eval Runner 和 `ExperimentConfig` 均拒绝 direct OpenAI primary provider。只有带有 DeepSeek fallback facts 的配置可以构造 OpenAI fallback client。

2. fallback success report 初始缺少足够的 requested / actual provider 事实。
   - 风险：OpenAI fallback 成功可能被下游误读成 DeepSeek 成功。
   - 处理：report 和 run config facts 必须记录 `requested_provider=deepseek`、`actual_provider=openai`、`fallback_reason`、`fallback_policy_version`、`provider_model`、`provider_base_url` 或 endpoint category。`inspect-real-provider-smoke` 会拒绝 fallback 伪装成 primary success。

3. provider error taxonomy 初始分类不够可靠。
   - 风险：认证错误、限速、context limit、timeout、invalid response 和 provider error 可能混在一起，导致 smoke report 和最终验收不能稳定判断失败类型。
   - 处理：根据 HTTP status、错误 payload 和错误 message 共同分类，覆盖 `auth_error`、`rate_limit`、`context_limit`、`provider_timeout`、`invalid_response`、`tool_call_parse_failure` 和 `provider_error`。新增单元测试覆盖。

4. Stage 11 测试覆盖不足。
   - 风险：真实 provider adapter、skip path、fallback validation、credential redaction 和 training payload leakage 可能缺少稳定回归证据。
   - 处理：新增 `tests/unit/test_provider_client.py` 和 `tests/integration/test_real_provider_smoke.py`，并扩展 factory / experiment config 测试。

### P3

1. 本地未安装官方 OpenAI SDK。
   - 处理：记录为已知限制。OpenAI adapter 保持官方 SDK 调用形态，并通过测试注入 SDK 形态验证；本阶段 accepted smoke 由 DeepSeek primary provider 完成。

2. 阶段日志和审查记录需要补齐。
   - 处理：新增 `docs/v2/implementation-log/stage-11.md` 和本文件。

3. reasoning summary 和 provider raw payload 检查需要加强。
   - 处理：artifact metadata 明确 `export_allowed=false` 和 `training_payload_allowed=false`；训练 payload 泄漏扫描覆盖 `raw_provider`、`raw_request_body`、`reasoning_content`、`reasoning_summary`、Authorization 和 secret-like token。

## 审查正例证据

- DeepSeek provider 使用 `https://api.deepseek.com` 和 OpenAI-compatible chat completion 请求形态。
- DeepSeek 默认模型为 `deepseek-v4-pro`，低成本可选模型为 `deepseek-v4-flash`。
- deprecated DeepSeek model 被拒绝。
- OpenAI adapter 使用官方 Python SDK 形态，但不能作为普通 primary provider。
- 无凭证 smoke 生成 `status=skipped_no_credentials`，没有被记成 accepted。
- 有 DeepSeek 凭证时，smoke run 的 formal final verifier 为 `accepted`，run outcome 为 `success`。
- DeepSeek accepted smoke report 记录 `requested_provider=deepseek`、`actual_provider=deepseek`、`provider_model=deepseek-v4-pro`、`provider_base_url=https://api.deepseek.com`。
- provider raw artifact 通过 RunRecorder 记录，并标记 redacted、不可导出、不可进入训练 payload。
- SFT 和 RL 导出 audit 均 clean。
- 训练 payload 泄漏扫描没有发现 provider raw artifact、Authorization、reasoning 字段、raw request body 或 secret-like token。
- replay、fake 和 mock provider 相关回归测试仍通过全量测试间接覆盖。

## 审查负例证据

- direct OpenAI primary provider 被拒绝。
- fallback report 缺少 fallback policy version 时会被 `inspect-real-provider-smoke` 拒绝。
- 无凭证 skip 不会被 `inspect-real-provider-smoke` 记成真实 provider accepted。
- OpenAI fallback success 不能伪装成 DeepSeek primary success。
- API key、本地 secret 文件内容、Authorization header、provider raw request body、provider raw response 和 reasoning summary 没有进入训练导出。
- 本阶段没有实现 provider scheduler、成本优化、大规模重试队列或 Stage 12 之后的能力。

## 修复后验证

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_provider_client.py tests/unit/test_model_client_factory.py tests/unit/test_experiment_config.py tests/integration/test_real_provider_smoke.py -q
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness run-real-provider-smoke --output-dir runs/v2-real-provider-smoke-20260501T214500Z --report runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json --allow-openai-fallback --allow-local-secret-file
PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke --report runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json --allow-skip-without-credentials --require-accepted-with-credentials
PATH=.venv/bin:$PATH repo-harness export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001 --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001 --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports --all --assert-clean
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE=1 PATH=.venv/bin:$PATH repo-harness run-real-provider-smoke --output-dir runs/v2-real-provider-skip-20260501T215000Z --report runs/v2-real-provider-skip-20260501T215000Z/real_provider_smoke_report.json --allow-openai-fallback
PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke --report runs/v2-real-provider-skip-20260501T215000Z/real_provider_smoke_report.json --allow-skip-without-credentials --require-accepted-with-credentials
```

验证结果：

- Stage 11 定向测试通过，34 个测试通过。
- 编译通过。
- 全量测试通过，306 个测试通过。
- DeepSeek accepted smoke run 通过 formal final verifier。
- 无凭证 skip smoke run 通过结构化 skip 检查。
- SFT 和 RL 导出 audit 均 clean。

## 结论

审查提出的 P1 和 P2 已修复并通过测试覆盖。P3 中可以在 Stage 11 范围内处理的事项已经处理；OpenAI SDK 未安装记录为环境限制，不影响 DeepSeek primary accepted smoke。Stage 11 可以提交，并可以进入 Stage 12。
