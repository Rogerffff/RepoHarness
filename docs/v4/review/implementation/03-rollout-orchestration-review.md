# V4 Stage 3 Review: Rollout Orchestration

## 审查方式

本阶段使用只读 subagent 审查。由于审查发现 P1/P2/P3 问题，阶段 3 进行了多轮修复和复审。

## 第一轮审查结论

结论：不允许进入阶段 4。

发现：

- P1：resume / checkpoint inherited context 只检查顶层字段，无法拒绝嵌套 hidden verifier、reward、outcome 或 evaluator-only 内容。
- P2：worker log 没有贯穿单机单 worker 约束，也没有校验 state write lease 属于对应 queue item。
- P2：run selection query 没有验证选择结果和 queue ids。
- P2：batch resume scope 未强制为 rollout orchestration phase recovery only。
- P3：budget 逐项超限检查不完整。

修复：

- 添加递归 resume context marker 扫描。
- 校验唯一 worker、每条 worker log 的 worker id、state write lease 与 queue item 匹配。
- run selection query 校验 predicate、selected count 和同目录 queue ids。
- batch resume scope 与 inherited context allowlist 做精确校验。
- budget 逐项超限要求 `budget_exhausted=true`、`continue_allowed=false` 并写入 worker log。

## 第二轮审查结论

结论：不允许进入阶段 4。

发现：

- P1：短 marker `hidden_verifier` 可绕过递归检查。
- P2：worker log 删除所有 `worker_id` 仍可通过。
- P2：run selection query 未检查 `role`、`provider_mode`、`scaffold_id`、`retry_state`、`lease_status` 和 `worker_id`。
- P3：`worker_log_budget_exhausted_recorded` 与实际 worker log 事件未交叉校验。

修复：

- 扩展禁止继承 marker，覆盖 `hidden_verifier`、`reward_label`、`reward_scalar`、`outcome`、`evaluator_only`、`long_term`、`session_continuation` 等短 marker。
- worker log 必须精确包含一个 `worker_id`，每条记录必须有 `worker_id`。
- run selection query 强制检查完整 queue-native predicate。
- `worker_log_budget_exhausted_recorded` 必须与实际 worker log budget exhausted 事件一致。

## 第三轮审查结论

结论：不允许进入阶段 4。

发现：

- P1：裸 `session` marker 未被拒绝。

修复：

- 将 `session` 加入禁止继承 marker 列表。
- 添加在刷新 checkpoint hash 后注入裸 `session` 的负例，确保失败来自 resume marker 检查本身。

## 最终复审结论

最终复审结论：允许进入阶段 4。

确认事项：

- 裸 `session` marker 已被递归拒绝，并有单元测试覆盖。
- worker log 已要求唯一 worker 和 queue item lease 匹配。
- run selection query 已检查 role、provider mode、scaffold id、retry state、lease status、worker id、max workers、status、task source tag、selected count 和 queue ids。
- budget exhausted flag 与 worker log 事件一致。
- batch resume scope 和 inherited context allowlist 已强校验。
- 未发现新的 P1、P2 或 P3。

## 允许进入下一阶段

允许进入阶段 4。
