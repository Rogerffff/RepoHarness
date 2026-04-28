# Context, Session, And Failure Diagnostics

## 设计目标

软件工程 agent 的长轨迹会快速膨胀上下文：文件内容、搜索结果、测试输出、错误日志和多轮 patch 都可能占用大量 token。RepoHarness 必须从设计阶段就规划上下文和失败诊断。

## 上下文增长问题

主要来源：

- 多次读取大文件。
- 搜索结果过多。
- 测试输出过长。
- 失败重试反复产生类似日志。
- verifier 输出和 patch diff 叠加。

如果不控制，上下文限制会变成主要失败原因。

## 第一版上下文策略

第一版设计简单策略：

- 截断过长工具输出。
- 保留最近 N 轮工具结果。
- 对旧测试输出只保留摘要。
- 每次测试只保留关键失败片段。
- 保存完整输出到文件路径，模型上下文只接收 preview。
- 最终 summary 单独写入 run directory。

复杂自动压缩和语义记忆只作为后续扩展。

## Session Resume

第一版 session resume 设计为从 run directory 恢复：

- 读取 `transcript.jsonl`。
- 读取 `events.jsonl`。
- 读取 `final.diff`。
- 重新运行 verifier。
- 从最后一个稳定 turn 继续。

resume 不要求恢复每个未完成工具进程。未完成工具必须标记为 interrupted 或 timeout。

## Failure Diagnostics

标准失败类型：

- `dependency_install_failed`
- `test_timeout`
- `assertion_failure`
- `permission_denied`
- `invalid_tool_call`
- `context_limit`
- `patch_apply_failed`
- `no_progress`
- `regression_detected`

每次失败必须能关联到 task、turn、tool、workspace state 和 verifier result。

## 失败类型、终止原因和重试策略

终止原因、verifier error type 和 failure diagnostics 需要统一口径。未来实现应维护一张机器可读分类表，至少包含：

| failure type | 典型来源 | 是否允许模型重试 | 是否直接终止运行 |
| --- | --- | --- | --- |
| `dependency_install_failed` | baseline setup | 否 | 是，任务标记为 invalid |
| `test_timeout` | feedback verifier 或 final verifier | 可以，预算内允许修复 | 否，除非超过全局 timeout |
| `assertion_failure` | verifier parser | 可以 | 否 |
| `permission_denied` | permission event | 可以，模型可换低风险方案 | 视权限模式而定 |
| `invalid_tool_call` | tool schema validation | 可以 | 否，除非超过无效调用预算 |
| `context_limit` | context manager | 通常否 | 是，除非压缩后可恢复 |
| `patch_apply_failed` | workspace adapter | 可以 | 否 |
| `no_progress` | repeated failure heuristic | 否 | 是 |
| `regression_detected` | final verifier | 可以，若仍有预算 | 否，最终无预算时失败 |

这些分类应进入 events、metrics 和 summary。训练导出可以根据这些字段过滤无效轨迹，或者保留有诊断价值的失败轨迹作为偏好数据。

## 面试案例

准备三个面试案例：

1. 权限和 sandbox 边界：解释 permission 决定是否执行，Docker execution mode 决定执行边界，但不声称生产级安全沙箱。
2. verifier reward 与评测一致性：解释为什么 shared verifier 能减少 reward/eval 口径漂移。
3. 长轨迹失败诊断：展示一次任务因为上下文、测试超时或 patch 回归失败，如何从 events 追踪原因。

## Claude Code 参考

参考模块：

- `reference/claude-code-docs/claude-doc/10-context-memory-session.md`
- `reference/claude-code-typescript-src/services/compact/autoCompact.ts`
- `reference/claude-code-typescript-src/services/compact/microCompact.ts`
- `reference/claude-code-typescript-src/services/SessionMemory/`

RepoHarness 只借鉴上下文治理思想，第一版不实现完整自动 compact 系统。
