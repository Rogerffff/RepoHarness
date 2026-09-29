# python__mypy-17071

**保留为受限静态候选；needs_review / static_review，仅 development_diagnostic。** base `4310586460e0` 上，参数回调`TypeGuard[T]`中的T被漏收集，使合法返回T误报未绑定变量。公开源码足以定位；正式actor尚未验。

| 需求/旧行为 | 决定性检查 | 覆盖边界 |
|---|---|---|
| 合法TypeGuard回调返回T不报错，并保留str推断 | 新F2P真实build后整份输出仅str note | no-op多出目标错误，str已正确；未跑补全题面CLI |
| TypeIs对应行为 | 第二F2P同形断言 | 有公开对称源码依据，issue未明示，范围待审 |
| bool表示、TypeIs正负分支收窄 | 两个P2P共六个reveal断言 | 两侧都通过；不保护真正未绑定T的错误 |
| 未绑定T、嵌套/别名、共享visitor消费者保持 | 已沿调用者读公开旧例 | 未执行、未冻结为奖励引用 |

原G/N账本和日志：同初态、派生image `65be1535…`，真实四项执行，gold=1/no-op=0。依赖修订只加离线wheel，未改测试或引用；安装各步成功。已有证据属于grader/54322，不能借给正式public-image actor/54321。

八方面均已静态检查：公开要求、材料、全部新增断言、替代/部分实现、gold与旧回归、开发条件、投影/恢复/泄漏/评分、关系与用途。未知包括actor可达性、原例CPU对照、替代候选、重复稳定性、实际泄漏与盲解。题面重复且代码需小幅补全；原始hints已核，但当前公开包未包含。未据这些现象判不可解。

具体疑点是：直接关闭`check_unbound_return_typevar`可能通过四引用却漏公开负例；TypeGuard-only窄修复在较窄issue契约下可能被TypeIs引用拒绝，完整合法性仍待规范判断；旧记录的helper断言绕过亦有静态依据。三者均未重放，不写已证误判。低覆盖和共享visitor影响不自动等于坏题。

当前`test_globs=()`，只恢复两份官方.test；gold源码正常交付，额外排除=[]。**唯一优先下一步：**固定已核派生grader，比较补全公开原例的base/gold，并加入回调只含U、函数却返回另一T的真实unbound负例。独立[复核](review.md)已完成：TypeIs有公开源码依据，不单凭issue未提就定误拒；实际typing-extensions为4.8.0，静态stub支持TypeIs，不是导入失败。正式actor另在模型开发前核验，具体候选按首项结果选择；未知成本=null。

原件：`W/{gold,noop}/ledger.jsonl:1`（W全路径及全部证据见封存初稿、历史对照）。审查者已见gold、隐藏测试及本题历史，产物不可交solver。
