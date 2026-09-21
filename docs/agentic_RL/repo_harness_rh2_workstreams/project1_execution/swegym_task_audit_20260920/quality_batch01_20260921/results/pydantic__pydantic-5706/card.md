# pydantic__pydantic-5706

base `70e7e99ca186`，调查Sequence[int]的JSON Schema与JSON验证不一致。建议 `needs_review/static_review`、仅开发诊断：先澄清外部目标，再核回归保护，暂不以原题直接解释模型能力。

| 需求或旧行为 | 依据/验收 | 覆盖 |
|---|---|---|
| schema与JSON一致 | 题面提出更早拒绝；两个F2P要求成功 | 支持方向合理，但非唯一明示 |
| 普通List行为 | 两个List参数P2P及相邻schema测试 | 已覆盖 |
| Python range、tuple、deque行为 | 公开test_types.py与sequence_validator | 不在273个P2P或官方执行文件 |

八方面均已按范围查：题面/base、全部新增断言与fixture、F2P及相关P2P、替代路线、gold、开发依赖、恢复投影、用途暴露。未逐条读全部P2P体，未验正式actor、消息、镜像答案资产或跨题关系。独立复核已完成，见review.md。

已核09-19原始RH2与哈希：修复配方、Python3.8/core0.31.0下，noop为2失败/275通过/1预期失败，gold为277通过/1预期失败；安装均rc0，冻结参考全部命中。额外通过的两个warning用例不在参考集。noop两个F2P都先停在schema导出，gold才执行到JSON正例；该正例只检查truthy，没有数据保真与负例。

独立发现：直接Sequence→list可能通过JSON验收，却破坏Python容器和输入边界；gold回调另有绕过自定义items hooks的静态泛化风险，后者不是已证原int例回归。历史候选与轨迹已核：单行映射后出现6失败/10通过，range拒绝、tuple/deque变list，且早于修改旧测试。新增原件补证已确认：09-16独立source-only矩阵的base/gold旧Sequence各16过，候选6败10过；gold/候选官方完整文件均277过1xfail。09-09旧完整候选满分另有账本/原日志支持。两者均不等于当前配方RH2反例。generator文档与旧测试冲突，暂不直接增成硬评分。

旧候选还改过测试和安装元数据；下一对照只重建已核的生产代码改动，让三方消费相同配方，避免混淆修复效力。本审已见私有答案与旧轨迹，产物不得回流求解上下文。

唯一优先CPU是当前条件适用性核验：从精确base重建上述单行source-only候选，同一配方对照base/gold/候选的官方得分与range成功、tuple/deque保持；尚未执行。方向澄清不能由gold得分代替；grader安装成功也不能代证actor可开发。细节和最小类定义见同目录old_findings_delta.md；独立判断留在封存前稿。

复核补充：8511较新base的Sequence实现含对应JSON/Python分支；非两题重复的证明，完整祖先/全池关系未查。

历史补证由原reviewer追加，旧正文与初判字节未改；12份pytest原日志直接支持行为计数，但UID/网络启动条件仍按授权索引说明分层，未凭目录名独立确认。无需为重证旧事实再跑旧脚本，不扩大generator/string结论。
