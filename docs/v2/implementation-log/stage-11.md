# Stage 11: real provider smoke path

## 本阶段目标

本阶段目标是在 Stage 07 的通用 `ModelClient` 协议和 Stage 10 的 provider artifact / redaction / error taxonomy 基础上，接入最小真实 provider 路径。主 provider 是 DeepSeek，备用 provider 是 OpenAI。真实 provider 只用于 smoke 和协议验收，不替代 mock provider 的稳定无网络回归职责，也不改变第一版 replay-only 最小闭环。

本阶段严格保留以下边界：

- DeepSeek 是 primary provider。
- OpenAI 只能作为 DeepSeek 明确 fallback 条件下的备用 provider，不能作为普通 primary provider。
- provider raw request、provider raw response、reasoning summary、Authorization header 和 API key 不能进入训练 payload。
- 无凭证环境可以结构化 skip，但不能记录为真实 provider accepted。
- 有 DeepSeek 凭证时，至少一个固定小任务必须通过 formal final verifier。

## 官方文档检查

本阶段已检查官方文档：

- DeepSeek 官方文档首页：`https://api-docs.deepseek.com/zh-cn/`
- DeepSeek tool calls 文档：`https://api-docs.deepseek.com/zh-cn/guides/tool_calls`
- DeepSeek chat completion 文档：`https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/`
- OpenAI Python quickstart：`https://developers.openai.com/api/docs/quickstart?language=python`
- OpenAI Chat Completions API 文档：`https://platform.openai.com/docs/api-reference/chat/create`

DeepSeek 三个官方页面在本地检查中均返回 HTTP 200。OpenAI 文档通过 OpenAI 官方文档工具读取，并确认 Python SDK、`OPENAI_API_KEY` 环境变量和 chat completions endpoint 的使用方式。

`real_provider_smoke_report.json` 中记录：

- `official_docs_checked=true`
- `official_docs_url=https://api-docs.deepseek.com/zh-cn/`
- `checked_at_date=2026-05-01`

## 本阶段实现内容

- 新增 DeepSeek provider adapter：
  - 使用 OpenAI-compatible 请求形态。
  - 默认 base URL 为 `https://api.deepseek.com`。
  - 默认模型为 `deepseek-v4-pro`。
  - 允许 `deepseek-v4-pro` 和 `deepseek-v4-flash`。
  - 明确拒绝 deprecated model：`deepseek-chat` 和 `deepseek-reasoner`。
  - DeepSeek 特有参数只保留在 DeepSeek adapter 内，不进入通用 `ModelClient` 协议。
- 新增 OpenAI fallback provider adapter：
  - 通过官方 Python SDK 的 `OpenAI` client 调用。
  - API key 只从 `OPENAI_API_KEY` 读取。
  - 只能在 `requested_provider=deepseek`、`actual_provider=openai`、`fallback_reason` 和 `fallback_policy_version` 明确存在时使用。
  - 不能通过普通 `ExperimentConfig` 或 factory 路径作为 primary provider 使用。
- 新增 provider artifact 共用逻辑：
  - 写入受控 provider request / response artifact。
  - artifact metadata 标记 `export_allowed=false`、`training_payload_allowed=false`、`redaction_status=redacted`、`retention_policy=provider_raw_redacted`。
  - 保存 endpoint category、provider、model、request id 和 token usage 的脱敏事实。
- 新增 provider redaction 共用逻辑：
  - 递归脱敏 `api_key`、`apikey`、`authorization`、`password`、`secret`、`token` 和 `*_token` 等字段。
  - 过滤 Bearer token、OpenAI 风格 key、DeepSeek / OpenAI local secret 字符串和 reasoning 字段。
  - provider exception message 经过清洗后再进入 report 或 model error。
- 新增 provider error taxonomy：
  - `auth_error`
  - `rate_limit`
  - `invalid_response`
  - `tool_call_parse_failure`
  - `context_limit`
  - `provider_timeout`
  - `provider_error`
- 新增 real provider smoke runner：
  - CLI：`repo-harness run-real-provider-smoke`
  - CLI：`repo-harness inspect-real-provider-smoke`
  - 生成 `real_provider_smoke_report.json`。
  - 支持无凭证结构化 skip。
  - 支持有 DeepSeek 凭证时运行固定小任务并检查 formal final verifier。
  - 支持显式允许 OpenAI fallback，但 fallback run 必须独立记录，不允许伪装成 DeepSeek primary success。
- 扩展 run metadata facts：
  - `requested_provider`
  - `actual_provider`
  - `fallback_reason`
  - `fallback_policy_version`
  - `provider_base_url`
  - `provider_endpoint_category`
  - `credential_source`
- 扩展 `ModelClient` factory 和 Eval Runner：
  - 支持 `deepseek` primary provider。
  - 保留 `replay`、`fake` 和 `mock` 兼容路径。
  - 拒绝 direct `openai` primary provider。
  - 只允许带有 DeepSeek fallback policy 的 OpenAI fallback configuration。

## 修改的主要文件

- `src/repo_harness/model_client/redaction.py`
- `src/repo_harness/model_client/providers/__init__.py`
- `src/repo_harness/model_client/providers/common.py`
- `src/repo_harness/model_client/providers/deepseek.py`
- `src/repo_harness/model_client/providers/openai.py`
- `src/repo_harness/model_client/real_smoke.py`
- `src/repo_harness/model_client/mock.py`
- `src/repo_harness/model_client/factory.py`
- `src/repo_harness/model_client/__init__.py`
- `src/repo_harness/evaluation/runner.py`
- `src/repo_harness/evaluation/schemas.py`
- `src/repo_harness/run_metadata/schemas.py`
- `src/repo_harness/run_metadata/writer.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_provider_client.py`
- `tests/unit/test_model_client_factory.py`
- `tests/unit/test_experiment_config.py`
- `tests/integration/test_real_provider_smoke.py`

## 生成的机器可读产物

DeepSeek accepted smoke run 生成：

- `runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/run_config_facts.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/run_metadata.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/events.jsonl`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/artifacts.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/verifier.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/reward.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/metrics.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports/sft_20260501T211845Z_fabcec6586/export_manifest.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports/sft_20260501T211845Z_fabcec6586/audit_report.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports/rl_20260501T211846Z_9328a5e914/export_manifest.json`
- `runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports/rl_20260501T211846Z_9328a5e914/audit_report.json`

无凭证 skip smoke run 生成：

- `runs/v2-real-provider-skip-20260501T215000Z/real_provider_smoke_report.json`

DeepSeek accepted smoke report 记录：

- `status=accepted_with_credentials`
- `requested_provider=deepseek`
- `actual_provider=deepseek`
- `provider_model=deepseek-v4-pro`
- `provider_base_url=https://api.deepseek.com`
- `provider_endpoint_url=https://api.deepseek.com/chat/completions`
- `fallback_used=false`
- `credential_status=present`
- `credential_source=local_secret_file_redacted`
- `redaction_status=redacted`
- `final_verifier_status=accepted`
- `run_outcome=success`

无凭证 skip smoke report 记录：

- `status=skipped_no_credentials`
- `requested_provider=deepseek`
- `actual_provider=null`
- `fallback_used=false`
- `credential_status=missing_all`

## 运行的验证命令

```bash
python - <<'PY'
import urllib.request
urls = [
    "https://api-docs.deepseek.com/zh-cn/",
    "https://api-docs.deepseek.com/zh-cn/guides/tool_calls",
    "https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/",
]
for url in urls:
    req = urllib.request.Request(url, headers={"User-Agent": "RepoHarness-doc-check"})
    with urllib.request.urlopen(req, timeout=20) as response:
        print(f"{url} {response.status} {response.geturl()}")
PY

PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest tests/unit/test_provider_client.py tests/unit/test_model_client_factory.py tests/unit/test_experiment_config.py tests/integration/test_real_provider_smoke.py -q
PATH=.venv/bin:$PATH python -m pytest -q

PATH=.venv/bin:$PATH repo-harness run-real-provider-smoke \
  --output-dir runs/v2-real-provider-smoke-20260501T214500Z \
  --report runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json \
  --allow-openai-fallback \
  --allow-local-secret-file

PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke \
  --report runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json \
  --allow-skip-without-credentials \
  --require-accepted-with-credentials

PATH=.venv/bin:$PATH repo-harness export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001 --format sft_jsonl
PATH=.venv/bin:$PATH repo-harness export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001 --format rl_jsonl
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports --all --assert-clean
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports --all --format sft_jsonl --require-trainable-samples
PATH=.venv/bin:$PATH repo-harness inspect-export runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports --all --format rl_jsonl --require-trainable-samples

python - <<'PY'
import json
import re
from pathlib import Path

paths = [
    Path("runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports/sft_20260501T211845Z_fabcec6586/data.sft.jsonl"),
    Path("runs/v2-real-provider-smoke-20260501T214500Z/deepseek-primary-task-001/exports/rl_20260501T211846Z_9328a5e914/data.rl.jsonl"),
]
blocked = [
    "raw_deepseek_provider",
    "raw_provider",
    "authorization: bearer",
    "reasoning_content",
    "reasoning_summary",
    "raw_request_body",
]
secret_pattern = re.compile(r"sk-[A-Za-z0-9_-]{12,}")
for path in paths:
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    for marker in blocked:
        if marker in lowered:
            raise SystemExit(f"blocked marker {marker!r} found in {path}")
    if secret_pattern.search(text):
        raise SystemExit(f"secret-like token found in {path}")
    for line in text.splitlines():
        json.loads(line)
print("training payload provider raw leakage check passed")
PY

env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE=1 PATH=.venv/bin:$PATH repo-harness run-real-provider-smoke \
  --output-dir runs/v2-real-provider-skip-20260501T215000Z \
  --report runs/v2-real-provider-skip-20260501T215000Z/real_provider_smoke_report.json \
  --allow-openai-fallback

PATH=.venv/bin:$PATH repo-harness inspect-real-provider-smoke \
  --report runs/v2-real-provider-skip-20260501T215000Z/real_provider_smoke_report.json \
  --allow-skip-without-credentials \
  --require-accepted-with-credentials
```

## 验证结果

- DeepSeek 官方文档检查通过，三个页面均返回 HTTP 200。
- Stage 11 定向测试通过，34 个测试通过。
- `python -m compileall src` 通过。
- 全量测试通过，306 个测试通过。
- DeepSeek accepted smoke run 通过 `inspect-real-provider-smoke`。
- DeepSeek accepted smoke run 的 formal final verifier 状态为 `accepted`，run outcome 为 `success`。
- SFT 和 RL 导出均通过 audit，并且均包含 1 个 trainable 样本。
- 训练 payload 泄漏扫描通过，没有发现 provider raw artifact 标识、Authorization header、reasoning 字段、raw request body 或 secret-like token。
- 无凭证 skip smoke run 通过 `inspect-real-provider-smoke`，状态为 `skipped_no_credentials`，没有被记成真实 provider accepted。

## 正例证据

- `model.provider=deepseek` 可以通过 factory 构造 `DeepSeekProviderClient`。
- DeepSeek provider 使用官方 OpenAI-compatible base URL `https://api.deepseek.com`。
- DeepSeek 默认模型为 `deepseek-v4-pro`。
- DeepSeek deprecated model `deepseek-chat` 和 `deepseek-reasoner` 会被拒绝。
- DeepSeek raw request / response 只作为受控 artifact 记录，artifact metadata 标记不允许进入 export 和 training payload。
- 有凭证时，DeepSeek primary provider 可以完成固定小任务，并通过 formal final verifier。
- 无凭证时，real provider smoke 生成结构化 skip report。
- OpenAI adapter 使用官方 Python SDK 形态，但 direct OpenAI primary provider 被 factory、Eval Runner 和 `ExperimentConfig` 拒绝。
- OpenAI fallback 必须有 `requested_provider=deepseek`、`actual_provider=openai`、`fallback_reason` 和 `fallback_policy_version`，否则 inspection 会拒绝。
- provider error 类型有结构化 `model_error_type`。
- replay、fake 和 mock provider 的既有路径没有被移除。

## 负例证据

- 没有把 OpenAI fallback 成功伪装成 DeepSeek primary success。
- 没有把无凭证 skip 伪装成真实 provider accepted。
- 没有把 direct OpenAI provider 暴露为普通实验配置选项。
- 没有把 DeepSeek 或 OpenAI raw request body、raw response、reasoning summary、Authorization header 或 API key 写入训练导出。
- 没有把 `reference/deepseek_api.md` 文件路径或文件内容写入训练导出。
- 没有绕过 RunRecorder 写 provider artifact。
- 没有绕过 Workspace Adapter、Permission System、Agent Loop 或 strict patch replay final verifier。

## 允许降级项

- 无 DeepSeek 和 OpenAI 凭证时，真实 provider smoke 可以结构化 skip。
- OpenAI fallback adapter 已实现，但本地没有安装官方 `openai` Python SDK 时，fallback smoke 不能运行成功；这不影响 DeepSeek primary accepted smoke。
- 本阶段只做真实 provider 最小 smoke，不实现 provider cost optimizer、多 provider scheduler 或大规模重试队列。
- 真实 provider 运行仍然是评测运行，不表示已经训练出了 coding agent。

## 禁止降级项

- 不能把 OpenAI fallback 成功记成 DeepSeek primary success。
- 不能把无凭证 skip 记成真实 provider accepted。
- 不能把 direct OpenAI provider 当成第二版 primary provider。
- 不能把 provider raw response、raw request body、reasoning summary、hidden thinking、Authorization header 或 API key 放入 SFT target、RL rollout payload、preference payload、metadata、skipped manifest 或训练 prompt。
- 不能在异常栈、调试日志、artifact、metadata、export 或 smoke report 中打印 API key、本地 secret 文件内容或完整 Authorization header。
- 不能用 feedback verifier accepted 替代 formal final verifier。

## 已知限制

- 本地 OpenAI fallback smoke 没有执行 accepted 路径，因为 DeepSeek primary 已经 accepted，且当前环境未安装官方 `openai` Python SDK；adapter 通过测试注入 SDK 形态验证。
- DeepSeek accepted run 的 `agent_stop_reason` 为 `max_turns`，但 formal final verifier 为 `accepted`，`run_outcome=success`。本阶段验收依据是 formal final verifier 和 run outcome，不把 feedback verifier 或 agent stop reason 当作正式 reward 来源。
- local secret helper 默认关闭。本地验收显式使用 `--allow-local-secret-file` 读取 `reference/deepseek_api.md`，report 只记录 `credential_source=local_secret_file_redacted`，不记录 key 值或文件内容。
- 本阶段没有实现 Stage 12 的 repo materialization、Stage 13 的任务集扩展、Stage 14 的 Docker backend 或 Stage 15 的最终验收汇总。

## 是否偏离设计文档

发现一个需要明确记录的范围差异：`docs/v2/implementation-plan.md` 的第二版范围强调不要实现复杂 provider fallback 或调度系统，而用户本阶段补充规则要求 DeepSeek primary 和 OpenAI fallback。实现采取受控折中：

- 实现 OpenAI adapter 和 fallback schema。
- 不允许 OpenAI 作为普通 primary provider。
- 不实现多 provider scheduler、成本优化或自动跨 provider 实验合并。
- fallback 必须显式记录 `fallback_reason`、`fallback_policy_version`、`requested_provider` 和 `actual_provider`。

因此该实现满足用户明确要求，同时没有扩展成第二版范围外的通用多 provider 系统。

## sub agent 审查结论

已安排只读 sub agent 审查。审查发现 2 个 P1、4 个 P2 和 3 个 P3 建议：

- P1：DeepSeek model constraint 初始实现不够严格，可能允许 deprecated model 或非文档指定默认模型。
- P1：DeepSeek credential strategy 初始实现默认读取 local secret file，不符合默认 env-only 策略。
- P2：OpenAI 初始实现可能暴露为 primary provider。
- P2：fallback success report 初始缺少足够的 requested / actual provider 事实。
- P2：provider error taxonomy 初始分类不够可靠。
- P2：Stage 11 测试覆盖不足。
- P3：本地未安装官方 OpenAI SDK。
- P3：阶段日志和审查记录需要补齐。
- P3：reasoning summary 和 provider raw payload 检查需要加强。

处理结果：

- P1 已修复：DeepSeek 默认模型固定为 `deepseek-v4-pro`，允许模型列表收窄为 `deepseek-v4-pro` 和 `deepseek-v4-flash`，deprecated model 被拒绝并有单元测试覆盖。
- P1 已修复：credential helper 默认只使用环境变量；local secret file 只有显式 `--allow-local-secret-file` 或 provider option 才允许，且 report 只记录 redacted source。
- P2 已修复：factory、Eval Runner 和 `ExperimentConfig` 均拒绝 direct OpenAI primary provider。
- P2 已修复：fallback report 和 run config facts 记录 `requested_provider`、`actual_provider`、`fallback_reason`、`fallback_policy_version`、`provider_model`、`provider_base_url` 或 endpoint category。
- P2 已修复：HTTP status、provider message 和 payload 共同参与 `model_error_type` 分类。
- P2 已修复：新增 DeepSeek adapter、OpenAI adapter、redaction、taxonomy、smoke report、skip path 和 fallback validation 测试。
- P3 已记录：OpenAI SDK 未安装是当前环境限制，不影响 DeepSeek primary accepted smoke；adapter 通过注入 SDK 形态测试。
- P3 已处理：阶段日志和审查记录已经补齐。
- P3 已处理：artifact metadata 和训练 payload 泄漏扫描增加 reasoning / raw payload 禁入检查。

审查记录保存到 `docs/v2/review/implementation/stage-11-review.md`。

## 是否可以进入下一阶段

可以进入 Stage 12。进入下一阶段前，Stage 11 commit 必须只包含当前阶段相关代码、测试、阶段日志和审查记录。
