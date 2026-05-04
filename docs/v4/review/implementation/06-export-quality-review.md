# V4 Stage 6 Implementation Review: Export Quality

## 审查范围

本次审查覆盖阶段 6 的 export quality、trajectory packing、failure dataset、reward audit、reward hacking risk、patch quality、test-overfitting risk、preference pair trainability、blocked pair report、export fixtures 和 CLI inspect 命令。

审查文件和产物包括：

- `src/repo_harness/v4_export_quality.py`
- `src/repo_harness/cli/main.py`
- `tests/unit/test_v4_export_quality.py`
- `docs/v4/evidence/export-quality/`
- `docs/v4/implementation-log/06-export-quality.md`

## 审查方法

- 对照 `docs/v4/implementation-plan.md` 阶段 6 要求逐项检查。
- 检查 outcome tier 与 trainability status 是否分离。
- 检查 reward scalar / reward label 是否只允许在 audit-only structured reward 或 RewardMetadata 中存在，并且 `model_visible=false`。
- 检查 failure dataset 是否具有 task、run、turn、tool、workspace、final verifier、failure taxonomy 和 evidence 绑定。
- 检查 SFT、reinforcement learning rollout 和 preference export 是否都有 valid fixture 与 negative fixture。
- 检查 final verifier 是否仍然是 accepted / rejected / inconclusive 权威来源。

## 审查发现和修复记录

### 已修复 P1：outcome tier 没有受 final verifier 强约束

初始实现只要求 trainable 样本来自 final verifier accepted，但没有强制 `verifier_accepted`、`verifier_rejected`、`verifier_inconclusive` 与 final verifier result 一一对应。

修复结果：

- inspect 增加 outcome tier 到 final verifier result 的映射检查。
- trainable 样本仍然额外要求 final verifier accepted。
- 单元测试覆盖 outcome tier 与 final verifier result 不一致。

### 已修复 P1：preference pair trainability 检查不足

初始实现只检查 trainable pair 数量和 blocked report 字段，未验证 chosen / rejected sample、baseline blocked、compare scope 或 count 一致性。

修复结果：

- inspect 校验 `trainable_preference_pair_count` 与 records 一致。
- inspect 校验 `blocked_pair_count` 与 records 一致。
- trainable pair 必须有 chosen sample、rejected sample、`baseline_blocked=false` 和 compare scope。
- chosen sample 必须引用 final verifier accepted trainable 样本。
- rejected sample 必须引用 final verifier rejected diagnostic 样本。
- blocked pair 必须有 blocked reason。
- no trainable pair 时必须使用 `no_trainable_preference_pair` 口径。

### 已修复 P1：failure dataset 缺少 run_id 和 failure category

初始实现未把 `run_id` 和 `failure_category` 作为 required fields。

修复结果：

- failure dataset 生成记录增加 `run_id` 和 `failure_category`。
- inspect 将两者加入 required fields。
- 单元测试覆盖缺失 run 或 failure category。

### 已修复 P2：patch quality metrics 太薄

初始实现只记录 minimal / excessive 状态和主事实布尔值。

修复结果：

- patch quality report 增加 changed file count、changed line count、test file change ratio、generated file change count、duplicate change count 和 unrelated change risk。
- inspect 强制每条 patch record 包含这些指标。
- 单元测试覆盖指标缺失。

### 已修复 P2：test-overfitting 风险缺 verifier bypass 和修改 verifier 配置

初始 risk 集合没有覆盖 `verifier_bypass_attempt` 和 `modified_verifier_configuration`。

修复结果：

- risk set 增加上述两类。
- 生成报告中两类风险均 flagged 且 export_blocked。
- 单元测试覆盖风险缺失。

### 已修复 P2：blocked pair report 没有 no-trainable 专门语义

初始实现不会在无 trainable preference pair 时强制 `no_trainable_preference_pair`。

修复结果：

- inspect 在 `trainable_preference_pair_count=0` 时要求 blocked reason 为 `no_trainable_preference_pair`。
- inspect 校验 blocked report sample count 与 blocked pair count 一致。
- 单元测试覆盖无 trainable pair 但没有专门 blocked reason。

### 已修复 P3：reward label 和 reward visibility 负例不足

初始测试未单独覆盖 reward label 进入 trainable target，也没有覆盖 `structured_reward.model_visible=true`。

修复结果：

- 单元测试覆盖 reward label 出现在 trainable target。
- inspect 校验 `structured_reward.model_visible=false`。
- 单元测试覆盖 RewardMetadata 和 structured reward visibility 违规。

## 正例确认

- `trajectory_quality_manifest.json` 绑定统一 V4 contamination denylist version、denylist sha256 和 allowlist policy version。
- `sample_tier_manifest.json` 区分 outcome tier 和 trainability status。
- `reward_audit_report.json` 保留 final verifier authority，不把 rejected 样本提升为 accepted。
- `blocked_pair_report.json` 包含 warning、blocked reason、样本数量、拒绝原因分布和下一步修复入口。
- 三种 export 格式都有 valid 和 negative fixture。

## 负例确认

阶段 6 单元测试覆盖用户要求的负例，包括 reward scalar / reward label 泄露、hidden selector 泄露、packing 回指缺失、reward audit 覆盖 final verifier、outcome / trainability 混用、RewardMetadata 缺字段、failure dataset 缺绑定、缺 negative fixture、test-overfitting 未标记、excessive patch 主事实化、preference pair 和 blocked pair 错误。

## 最终结论

阶段 6 经只读 subagent 审查和复审。初轮发现的 P1/P2/P3 均已修复；复审未发现剩余 P1、P2 或 P3。阶段 6 可以进入阶段 7。
