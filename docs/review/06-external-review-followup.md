# External Review Follow-Up

## 总体判断

外部审查意见整体成立，建议修改。前四项直接影响后续实现口径和评测可信度，应作为高优先级设计修订处理；后两项虽然优先级较低，但修改成本小，可以一起修订，避免后续实现出现空字段、伪字段或不可恢复的 resume 语义。

## 处理结果

| 意见 | 判断 | 处理结果 | 修订位置 |
| --- | --- | --- | --- |
| 正式运行工作区生命周期仍然不够明确 | 采纳 | 增加 source checkout、setup workspace、agent run workspace 三阶段；定义 `dependency_state`、`agent_start_snapshot`、`agent_diff_base` 和 diff 排除路径；明确 setup mutation 默认导致任务 invalid，除非显式声明。 | `docs/06-task-dataset-and-environment-adapters.md`、`docs/11-object-model-config-and-data-flow.md`、`docs/08-trajectory-store-and-training-export.md` |
| 终止原因和最终评测结果被混在一起 | 采纳 | 拆分为 `agent_stop_reason`、`final_verifier_status`、`run_outcome` 三个字段；把 `tests_passed` 改为 `feedback_tests_passed`，并说明最终统计以 final verifier 和 run outcome 为准。 | `docs/03-agent-loop-and-message-protocol.md`、`docs/07-verifier-reward-and-evaluation.md`、`docs/08-trajectory-store-and-training-export.md`、`docs/11-object-model-config-and-data-flow.md`、`docs/12-resume-narrative-and-demo-artifacts.md` |
| `bash` 和 `run_tests` 的测试语义存在冲突 | 采纳 | 明确测试类命令默认从 `bash` 路由到 `run_tests`；如果作为普通 bash observation 运行，只进入上下文和 events，不进入 success rate、reward metadata、fail-to-pass 或 pass-to-pass 统计。 | `docs/04-tool-system-and-orchestration.md`、`docs/05-workspace-sandbox-and-permissions.md` |
| RewardMetadata 示例和公式不一致 | 采纳 | 将示例 `final_reward` 改为 `0.89`，增加 `formula` 字段，并说明 score 是归一化原始分量、penalty 是当前 reward version 下的扣分值。 | `docs/07-verifier-reward-and-evaluation.md`、`docs/08-trajectory-store-and-training-export.md` |
| session resume 缺少可恢复的 workspace 状态依据 | 采纳 | 第一版降级为从 final workspace 继续；不再声称能恢复最后一个稳定 turn；中间 turn 恢复需要 per-turn patch chain、workspace snapshot 或可确定重放事件。 | `docs/10-context-session-and-failure-diagnostics.md`、`docs/08-trajectory-store-and-training-export.md` |
| ToolResult 字段过于命令执行中心化 | 采纳 | 将 ToolResult 改成通用字段加按工具类型扩展字段，命令类、文件读取类、搜索类、diff 类分别定义扩展字段。 | `docs/04-tool-system-and-orchestration.md`、`docs/11-object-model-config-and-data-flow.md` |

## 保留的设计原则

- 仍然保持第一阶段只做设计文档和 Python 骨架，不增加运行时代码。
- 仍然保持 `run_tests` feedback verifier 与 final verifier 共用解析器和 schema。
- 仍然保持 Docker execution mode 的保守表述，不声称生产级安全隔离。
- 仍然保持 transcript 与 events 分离，并让训练导出默认依赖 final verifier、events 和 final diff。
