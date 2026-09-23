# pandas-dev__pandas-51605

base `b070d87f1187`；`needs_review / static_review`，仅 `development_diagnostic`。目标是 `MultiIndex.isin` 对空候选返回与self等长的全False布尔数组。**隐藏空列表断言合理，但gold新增的len调用阻断原iterator归一化，存在未测回归。**

| 需求/旧行为 | 依据与测试 | 覆盖/证据 |
| --- | --- | --- |
| 空候选全False、长度/dtype正确 | issue3行例、Index.isin文档；F2P严格数组helper | 只测2行空list；公开3行和empty self+empty values未测。 |
| 非空iterator及empty iterator | from_tuples559-563、公开zip构造测试 | gold先len导致预计TypeError；13评分节点均未保护，未执行反例。 |
| 合法输入、普通匹配/NaN/level | 12旧P2P及list-like验证 | 旧P2P实际均过；gold空str/bytes早返回绕过旧拒绝，静态发现。 |

八方面已查：公开合同/材料初态，完整F2P、全部12P2P及fixture/helper，非gold合理路线，gold/构造器/真实axis.isin调用者，环境开发条件，官方恢复与解析，关系/暴露。未验全仓、真实actor/消息、当前镜像和模型表现。

原baseline01通过campaign→worker→归档ReplayGrader；脚本SHA与原config一致。N/G均13收集、13实际节点、13解析键，唯一命中1+12参考。noop题面TypeError/rc1/reward0，gold13PASS/rc0/reward1；这些不证明iterator正确。无reference override。镜像实际ID=null；grader54322与apply54321不等于正式actor。历史安装约693/720秒，纯Python开发不自动要求每次全构建；本轮成本未知。

旧ready_for_probe不沿用；输出类型疑义由公开文档消解，旧Series/DataFrame直接下游说法与本题源码不符。原3行/固定2False漏测例仅为未执行建议。无额外文件排除，未改源/测试/评分。

独立复核已完成，见[复审](review.md)。唯一优先下一步：只用base/gold比较[]、iter([])、iter([(1,3)])，每次创建新迭代器；同时核题面3行空例与原13节点评分。合理修复、空str/bytes及固定两False候选留后续，全部未执行。 正式模型开发前另验actor导入和候选生效。已见gold/隐藏测试/原日志/唯一旧记录，禁止给solver。

协调裁决（2026-09-20T22:14:39.224798+00:00）：暂不优先普通能力探针：新增空list断言合理，但gold在旧iterator规范化之前调用len，静态上破坏非空iterator并漏修空iterator；空str/bytes又绕过旧校验。先作base/gold窄语义对照，未实跑回归。 51605公开base的_fill_token核心和注释包含50319 gold实现；仅源码包含事实，不证明Git祖先、题目重复或真实solver已见答案。
