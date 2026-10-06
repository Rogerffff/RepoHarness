# getmoto__moto-6408

**needs_review / static_review**；仅开发诊断。base `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a`。目标是把已有tag从多标签镜像迁到另一镜像，保留正确归属及其它标签。

| 行为 | 验收 | 判断 |
| --- | --- | --- |
| 已存在的两镜像之间迁移 | 唯一F2P前后首项manifest分别=001/002 | 原序列覆盖，noop失败、gold通过 |
| 唯一归属、两侧其它tag保留 | F2P用first,*_，未查数量或describe状态 | 精确原序列有漏测 |
| 多标签、同tag重复、单tag覆盖、None tag、get/delete | 相关公开P2P | 已展开关键分支；全部95节点清单≠全部函数体 |

历史原件确认gold 96 passed/reward1，noop 1 failed、95 passed/reward0；执行节点、解析键、冻结参考均96，无missing/skip/碰撞。离线wheel增层后的make init真实完成，不能把COPY本身当安装。评分是rh2grader/54322；正式actor待验。

gold对题面已存在目的的序列，静态上正确摘旧tag并保留其它tag。两个限度：只调返回次序或全删来源可能满足新增断言，尚未实跑证明得分；另在“多tag来源→新manifest目的”分支，先append再batch_delete可能连新图一起删掉。后者是**邻接未修旧缺陷，不是已证gold新增回归或题面精确原例**。

八方面已核题意、材料初态、完整test.patch/helper、受影响P2P/调用链、非gold合理路线、gold及交付/环境；测试只检查黑盒，无内部写法要求。官方精确恢复test_ecr_boto3.py，test_globs为空，额外排除为空。同包源码包含关系已核，见下述协调收束；Terraform gitlink不影响所查路径。

历史相同排序反例仍是未执行预测，不能升格为已证奖励漏洞。helper公开可查、旧安装问题已被最新日志覆盖；旧hints/真实AWS说法未作为新结论。详见[分析](analysis_before_history.md)及[历史差分](old_findings_delta.md)。完整SDK/core、其它ECR模块、actor消息/权限/当前镜像资产、稳定性和模型成本未查；已见私有材料，不可作为新solver，独立复核已完成，见[复审](review.md)。

唯一优先下一步：只用base/gold作目的manifest已存在/未存在的受控对照，核完整结果数、标签集合及来源其它tag。先查moving为代表tag；必要时扩展非代表tag以解释新旧错误模式。合理先摘tag实现留作可选延伸；所有CPU/修订均未执行。


协调裁决（2026-09-20T22:11:49.417478+00:00）：受限静态开发诊断候选：gold修复题面两个已存在manifest的迁移，新增断言有公开依据。唯一归属漏测及新目的manifest的旧缺陷限制外推，不据邻接既有错误直接判本题失效；优先base/gold完整状态对照。 同包源码关系已核：5960的scan复制/投影核心原样存在于6185 base；6185类型校验核心原样存在于6408 base，6408 scan另有返回值式演变。仅为公开源码包含/演变，不证明Git祖先、重复题或实际solver泄漏。
