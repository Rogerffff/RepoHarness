# python__mypy-16963

目标是在 base `f19b5d3a0263` 支持 `Type[TypedDict]` 及其Union的传递和构造，保留返回类型。建议 `needs_review / static_review`，仅开发诊断；先核完整题面与gold的行为范围。

| 需求/旧行为 | 测试映射 | 结论 |
| --- | --- | --- |
| 间接关键字构造有效 | F2P中cls(x=1,y=2)无错误 | noop报不能实例化，gold通过 |
| 位置参数、缺字段、额外字段应报错 | 同一F2P三条诊断 | 有负向保护，单纯返回Any过不了 |
| 结果不能退化Any；Union、Car/Boat/Truck有效 | F2P仅reveal输入cls，未检查调用结果或这些路径 | 关键公开行为未直接保护 |

八方面已核版本材料、需求、全部断言和两fixture/runner、替代路线、相关旧行为、gold、开发需求与交付边界。完整公开例、广回归、实际CC消息/actor、跨题关系和模型能力未验。gold复用已有签名，无缺交付依赖；直接构造路径不变，但helper把可选字段也作必需，属于新增支持边界欠缺，非已证实旧行为回归。

09-19原件记录F2P=1/P2P=0，两侧均成功安装；同一节点gold通过、noop实际诊断失败，无参考缺席。11 workers只执行1 item。八个固定wheel配方只补离线安装，证明派生grader条件，不证明actor消费。

另有两个静态疑点：保留参数签名却令结果为Any可能漏测；复用公开直接TD检查会给等价但不同措辞，可能被精确错误文本拒绝。均未实测。旧报告的“非法参数规格不可公开推知”和“只删兜底就满分”不沿用；独立reviewer已收口。

唯一优先CPU：固定条件下base/gold跑两个最小例及完整Car/Boat/Truck，保留`--warn-return-any`并逐行记录。若gold仅Boat仍错，先厘清No errors与旁注范围；若完整通过则撤回该疑点。冻结reward不变。审查已见gold、隐藏材料及历史，产物不得给solver，额外排除为空。

复核收口：独立复核与主审分别发现返回精度及Boat路径疑点；先base/gold完整原例，零P2P不自动否定。reviewer在初判见过本base含12417同形guard，已披露，不据此断定重复或Git祖先。 详细依据与处置分歧见 review.md；未回写封存前稿。
