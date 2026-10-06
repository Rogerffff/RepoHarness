# orange3 22e98：公开交付收口清单

2026-09-29。**R-f 文本已通过旧独立审查；DG 正式评分也已完成。剩余是 fresh 公开阅读、正式版本落地与实际消息/准备预算核对。**本轮没有新运行。

公开只读包：`runs/category2_repair_20260929/r2e/orange3_22e98_public_v1/`。派发提示：[orange3_22e98_public_reader_prompt.md](orange3_22e98_public_reader_prompt.md)。包中含修订后的 `user_prompt.txt`、`public_task.json`、经主线程意见改正的中性说明、公开工作树与逐文件 SHA256 清单；不含旧题面、gold、隐藏测试、修订理由或私有结论。

修订题面 SHA256 固定为 `f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199`。中性 brief 已注明：这是待交付静态包；`public_hints` 只是来源元数据，不能证明当前 CC 已实际收到；Python/权限/Qt 等是历史环境事实，当前 consumer 与 actor 条件待核。brief 更改不动题面。最终 `manifest.json` SHA256：`fcbeb310d0ba3f7ef683404ad5ee43681720ed9009ecc7af9192d79995ed630e`。

| 项目 | 当前事实 | 尚需动作 |
|---|---|---|
| 文本修订 | 旧 Codex `review_revision_orange3.md` 已通过 R-f；三处替换删除直接答案、改正 base 症状，期望值未变 | fresh 读者只看隔离公开包，独立解释需求、范围与自洽性 |
| 退化探测 | `inv/orange3_22e9/ledger_DG.jsonl` reward0，20/23；失败是 helper 与重复类值两键，共3键 | 不再重跑 DG；完整日志与摘要已有 |
| 当前环境正反对照 | `budget_v5/ledger_{noop,gold}.jsonl` 可复用1200秒预算对照；仅R-f不变评分材料 | 迁移到当前机器须确认镜像/配方/consumer，不把历史条件说成当前已验证 |
| 正式交付 | 当前 ingest 的 statement 仍是旧 `0d196bc2…`；隔离包不是正式修订单 | 主线程落 statement revision、pins、ingest；捕获实际题面，核新 hash及工具提示 |
| 准备预算 | DG 的 trusted setup 实际303.302106秒，测试12.249秒，run.log明确1200秒准备时限；cleanup正常 | 在最终入口分别登记准备、求解、评分预算的实际生效值，不把默认300秒当已验收 |

DG 日志：`runs/r2e_lifecycle_20260929/inv/orange3_22e9/logs_DG/evallog_replay-r2e-inv-22e9-DG-0_76a8bd97.eval.log`；SHA256 `b0563e4402a1c0f2d9cf0b82d789805ca7895f9465bde8cf073d844bf32e155d`。补丁摘要 `02d66b6f84ba0487abe7b9133b1ae5571e901c72dff40238ceabc7594fc88241`。当前结果是有效拒绝，不是准备超时或无分数。

root 已接管 fresh 派发、正式 R-f 落版本与 consumer 检查；本子任务不改旧题卡/board/正式修订单。完成这些前留第2类，不能把修订静态包当实际模型交付证据。
