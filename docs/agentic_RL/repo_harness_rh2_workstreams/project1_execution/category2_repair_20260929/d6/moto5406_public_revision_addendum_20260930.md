# Moto5406：正式交付修正后的公开示例

2026-09-30，沿统一标准R-f及用户既有SWE机制授权推进。本补充与 `moto5406_implementation_brief_20260930.md` 合并构成本题验收范围；不重新请求逐题批准。

原题create/describe两处表名为 `mock_Foundational_AMI_Catalog`，最终期望ARN中的表名却为 `test_table`。只将这两处名称替换为 `test_table`，保留所有地区、API、参数和其它文字。独立公开读者已先读修订版并封存理解、再对照原文，确认没有新增要求；报告为 `runs/category2_repair_20260929/moto5406_public_revision_v1/public_reader/review.md`。这种命名修正不能冒作已运行验证，尚须base/gold对照。

## 固定身份与正式路径

原公开包digest为 `sha256:4aae6fb1cccfb1d044a3692507883113d459769fdb04ad809e79a2a7dc6d6e26`，原题面SHA为 `sha256:97c49325d8a47eca02aa07dbaaffdfdeb9cfdcc591de71af574fa0a3683b1570`。修订公开包digest为 `sha256:1b128b3d708c1a29956bf4e846b81248ec77bd4ecd710f83b9f7a3ab6ca1e39e`，题面SHA为 `sha256:5a010a64e6458e87285378dccbb723da58eae797d8db7427fc49d245baafc4ac`。确切字节及仅两处替换见同目录 `proposal.json`，不可顺手改换行或其它文字。

- 固定R-f登记（建议 `moto5406-table-name-v1`）验证原题目/base、父公开身份、原/新题面SHA及完整新公开身份。只接受登记的两处字面量修正，不提供runtime自由prompt输入。
- producer从原可信216输入重放公开修订，生成新的public和environment；仅本题public发生变化，其余215题及全部validation、原始来源文件保持。可以与本题existing-P2P评分修订同一产物交付。
- 原PublicTaskBundle序列化schema可保持，更新题面及其摘要；修订来源与理由保存在可信登记/manifest。评分修订绑定**有效**公开digest，同时保存原来源公开身份，使父材料还原和消费重放均可验证。不得让新grading仍绑定旧public却通过检查。
- 正式consumer重建期望public/package/grading并逐字段核验，拒绝原公开包配新评分、来源/修订声明不符、未登记文本、伪新摘要、重复或零次替换。旧资格失效，既有五道修订材料/脚本/诊断字节不变。
- actor初始用户消息由正式prepared材料生成并逐字核验。执行器不覆写prompt；公开JSON模型不夹带私有节点、gold、修法或原件分析。

## 验证要求

本题仍先用新版正式评分完成0/1/0和28项逐参考核对。私有候选身份执行题面原例及修订例，验证base存在公开地区问题、gold原例被表名矛盾拒绝而修订例通过；查实际pytest收集、错误位置和输出，不能只看退出码。该辅助对照不改变reward，也不向真实actor提供gold。

真实CC公开开发检查执行修订示例及公开East1回归，记录初始消息字节、实际身份/激活/源码及完整退出。同次原冻结工件直接送独立grader，完整baseline及excluded census校验保留。发布时明确这是带版本的自建修订题，而非来源原题原样。

本补充允许实现者在自己的隔离Moto代码树完成R-f；仍由root非作者审查、冻结和远端执行，不改共享运行快照、不提交推送。原评分子片或本题面子片单独通过均不足以释放整题。
