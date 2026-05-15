# Stage 1 执行计划：RL Schema 与最小 LLMGateway Contract

状态：已执行完成，并通过 Stage 1 新增测试和 Stage 0H 回归测试。前置条件是 Stage 0H contract hardening v1 已经完成，并且 canonical fixture、shape rule、visibility baseline 和 blocked-by-stage 报告已经落地。

## Stage 1 要做什么

Stage 1 的目标是新增一个训练后端无关的 `src/repo_harness/rl/` schema 包，并定义最小 async `LLMGateway.generate_turn(...)` contract。这个阶段只固定 RepoHarness 与训练框架之间的正式数据结构和校验边界，不实现完整 `RepoHarnessRuntime.run_episode(...)`，也不实现 verl adapter。

## 第一项工作

第一项工作必须是把 Stage 0H 已经落地的 `tests/fixtures/repo_harness_verl/` canonical fixture 接入正式 schema roundtrip 测试和非法字段拒绝测试。不要重新发明一套新样例。

## 计划新增模块

- `src/repo_harness/rl/__init__.py`：导出 Stage 1 对外稳定使用的 schema、validator 和 fake/mock gateway。
- `src/repo_harness/rl/episode.py`：`RepoHarnessEpisodeRequest`、`RepoHarnessEpisodeResult`、episode status、invalid reason、diagnostics 和 budget consumption。
- `src/repo_harness/rl/gateway.py`：`LLMGatewayRequest`、`LLMGatewayResponse`、`GenerationRecord`、async `LLMGateway` protocol 和 async fake/mock gateway。
- `src/repo_harness/rl/training_view.py`：`TrainingView`、`ResponseSpan`、结构化 `AuditRef`、batch 可传播字段投影规则、token / mask / log probability 校验。
- `src/repo_harness/rl/timing.py`：`TimingSummary` 和 `ResourceSummary` 的结构定义。
- `src/repo_harness/rl/visibility.py`：模型可见字段、batch 可传播字段、evaluator-only denylist 和 opaque audit ref 校验。

## Schema 风格

Stage 1 schema 沿用项目现有 Pydantic v2 和 `repo_harness.schema_base.StrictBaseModel` 风格。默认禁止未知字段；只有 `LLMGatewayResponse.extra_fields`、provider options 这类被 contract 明确定义为开放扩展点的字段，才允许通过专门 validator 或 allowlist 承接。

字段变化要延续 Stage 0 / Stage 0H 的 required、optional、default 策略。Stage 1 必须能解析当前 Stage 0H fixture；`TimingSummary` 和 `ResourceSummary` 的完整性加严留到 Stage 4，Stage 1 先用安全默认值或可选字段承接最小形态。

## 实施顺序

1. 先新增 `src/repo_harness/rl/` 包和 route、status、visibility 等共享常量。
2. 再让 Stage 0H canonical fixture 能构造、序列化、反序列化，并保持 sha256 fixture 内容稳定。
3. 然后实现非法 route、空 response、response overflow、嵌套 audit ref、绝对路径 audit ref 和 evaluator-only 字段泄漏的拒绝规则。
4. 单条 `TrainingView` validator 只校验自身 token、mask、log probability 长度和 span 边界；mixed logprob 必须通过 batch helper，例如 `validate_formal_online_rl_batch(...)` 拒绝。
5. 最后补上最小 async `LLMGateway` protocol 和 async fake/mock gateway，供 Stage 2 runtime facade 测试复用。

## 出口标准

- schema 包不能 import `verl`。
- Stage 0H fixture 可以通过正式 schema roundtrip。
- 不合法 route、非法 `extra_fields`、空 response、overflow、mixed logprob 和 audit path 泄漏会被明确拒绝。
- `openai`、`deepseek` 等 provider route 可以用于评测、teacher data、SFT、preference data 和 offline diagnostic replay，但默认 `invalid_for_online_rl=true`，不能作为正式 online PPO / GRPO rollout policy sample。
- `LLMGatewayResponse.extra_fields` 与未来 `AgentLoopOutput.extra_fields` 的边界写入 schema 和测试。
- fake/mock gateway 可以通过 async `generate_turn(...)` 稳定返回最小 `LLMGatewayResponse`。
- `LLMGatewayResponse.response_mask` 只能为 `1`，工具 observation token 只能在 episode 级 `TrainingView` 中以 `response_mask=0` 表示。
- `RepoHarnessEpisodeResult.status` 能表达 Stage 2 runtime 需要区分的 `invalid_task` 和 `infrastructure_error`，并且这些状态不能被当成可训练样本。
- `python -m compileall src`、Stage 1 新增单元测试，以及 Stage 0H 三组回归测试通过。

## Stage 1 明确不做

- 不抽出完整 `RepoHarnessRuntime.run_episode(...)`。
- 不实现 `training_fast` recorder。
- 不实现 `TrainingView -> AgentLoopOutput` 转换。
- 不实现 `RepoHarnessVerlAgentLoop` 或 `VerlLLMGateway`。
- 不接真实 vLLM、SGLang、Ray 或 verl 训练流程。
