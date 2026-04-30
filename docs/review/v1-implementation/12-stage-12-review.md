# Stage 12 Read-Only Review

## Scope

本次审查针对 Stage 12: Training Exporter 的当前实现，重点对照：

- `docs/14-v1-implementation-plan.md`
- `docs/08-trajectory-store-and-training-export.md`
- `docs/11-object-model-config-and-data-flow.md`

审查方式为 sub agent 只读审查；sub agent 没有直接修改仓库文件。

## Findings

### P1: 导出脱敏没有覆盖供应商凭据

审查指出：导出脱敏只覆盖本机绝对路径，若 transcript、tool observation、summary 或 final patch 中出现 `sk-...`、`Authorization` header、token、password 等凭据文本，会原样进入 JSONL。

处理结果：

- 已修复。
- `_sanitize_text()` 现在会脱敏：
  - `Authorization: Bearer ...`
  - `Bearer ...`
  - `sk-...`
  - `api_key=...`
  - `token=...`
  - `password=...`
  - `secret=...`
- 新增单元测试覆盖 provider credential 脱敏。

### P2: Observation 应优先来自 PreparedMessages

审查指出：SFT 和 RL 导出直接从 transcript 或 events 的 preview 构造 tool observation，可能和 ContextManager 替换后的模型实际可见内容不一致。

处理结果：

- 已修复。
- Exporter 现在从 `prepared_messages` artifact 中建立 tool observation 映射。
- SFT tool message 和 RL trajectory observation 会优先使用 `prepared_messages` 中模型实际看到的 content。
- 如果某个最后工具结果没有后续模型上下文，导出会明确标记为 `transcript_preview_without_followup_context` 或 `event_preview_without_followup_context`。
- 导出 payload 保留 `prepared_message_refs` 和 `content_replacement_state_refs`，并在具体 observation 上记录 `prepared_messages_ref`、`content_replacement_state_ref`、`context_revision` 和 `context_replacement`。

### P2: RL reward 必须校验 formal final verifier 来源

审查指出：RL 导出只读取 `reward.json`，没有校验 `verifier.json` 是否为 final verifier、final verifier mode 是否为 strict patch replay，也没有校验 reward metadata 是否存在。

处理结果：

- 已修复。
- Exporter 现在校验：
  - `verifier.json` 必须存在。
  - `verifier_stage` 必须是 `final`。
  - metrics 中 `final_verifier_mode` 必须是 `strict_patch_replay`。
  - `reward.json` 必须存在。
- 不满足这些条件的样本会被标记为 `invalid_for_training=true`，并写出明确 `invalid_reason`。
- RL payload 中的 `reward_metadata` 会记录 reward source 是否为 formal final verifier。

### P2: 未跟踪 `docs/build-your-own/` 超出 Stage 12 范围

审查指出：未跟踪的 walkthrough/demo 文档更接近 Stage 13，不属于 Stage 12 Training Exporter。

处理结果：

- 不提交。
- 当前阶段暂存范围会继续排除 `docs/build-your-own/` 和旧审查材料。

### P3: Preference pair 在 reward 相等但 outcome 不同时被跳过

审查指出：排序键包含 run outcome，但 reward 相等时直接跳过 pair，会漏掉 reward 持平但 outcome 不同的偏好对。

处理结果：

- 已修复。
- Preference ranking 现在使用 `(final_reward, outcome_rank)`。
- 只有 reward 和 outcome rank 都相等时才跳过。
- 新增单元测试覆盖 reward 相等但 success/failed outcome 不同时仍生成 preference pair。

## Residual Risk

- 第一版 secret scanning 是保守正则脱敏，不是完整 secret scanner。
- 最后一次工具结果如果没有后续 model turn，就不存在对应 `prepared_messages` observation；Exporter 会显式标记 fallback 来源。
- SFT 导出仍基于 RepoHarness transcript/prepared artifact 的中间格式，不是任何真实 provider 的原生格式。
