# Dask9378 首Coder：修法与验证分析

2026-10-03T17:03:10.997400+08:00。默认mask修法有静态及真实自测支持，但**正式137参考尚未运行，原reward=None**。环境准备300秒控制面保护超时，安装／测试未开始；不能把None记成模型0或由自测预写1。同原FP的setup900补评分由GPU负责，本报告固定原首臂事实，后续评分另存。另一模型缺项，单样本不授训练资格或稳定性结论。

169份30,382,873B原件逐SHA／大小核，10项FrozenPatch规范SHA为`ed5ec645234368669128c41ad3a2b9104ecf20bf346535bd22e2f60dda49df4d`。9次成功Edit及全部Write文本重放与最终候选相同，正式测试／conftest未改；生产改动是ma.py追加三函数，另有9个探索脚本。[独立语义窄核](../../reviews/non_author_9378_coder_a1_candidate_review_20261003.md)接受当前窄目标的修法依据，并保留下面三项P2；[JSON身份及来源](model_probe_coder_a1_analysis_20261003.json)绑定原件与执行审查。

模型先查ma、creation和导出，再真实重现顶层丢mask，选择新增`da.ma`入口符合用户B。初版把name传给不支持它的asanyarray，TypeError后修正；随后数轮复杂构造仍丢mask。追加实现一度留下六个同名函数，后面的旧定义遮蔽前面的新定义。L463检查真实函数源码后，L472采用逐块NumPy masked like函数，L485默认ones/zeros例子的data/mask相符。L610才清除重复定义；前后三个函数的签名与可执行语句AST相同，经非作者独立核，不冒充新的完整运行证据。

最终`a.map_blocks(np.ma.<like>, dtype=(dtype or a.dtype), order=order)`逐块保留默认mask并生成ones/zeros有效值。用户B允许正确的新增ma路线，未改顶层入口不是拒绝理由。私有测试用二维多chunk逐元素mask，模型主要自测一维；empty的类型／shape检查也不能代替逐元素mask断言，所以当前仍需完整正式评分。

| 问题 | 证据与当前处置 |
| --- | --- |
| dtype只改变输出元信息 | L522真实`ones_like(dtype=np.float32)`在`chunk.dtype == x.dtype`失败，后面的order分支未执行。map_blocks的dtype专用形参不转发给NumPy函数，最终同逻辑未修；zeros/empty仅静态同结构推论。 |
| chunks/name/shape被忽略 | 最终源码接受这些参数却不读取或转发，没有新增运行反例；复制签名不能证明兼容。 |
| 结论超过验证范围 | L527将dtype失败归为assert_eq问题，简化脚本删去dtype/order后通过，最终仍称全参数支持。134P自测在最终清理前；最终仅重跑ones原示例和一个不覆盖新like的旧P。 |

这三项阻止“全参数兼容”的结论，但没有证明当前用户B的默认mask要求漏判。参数缺陷与正式题分分列，不能因gold实现不同拒绝，也不自行扩展材料。需要完整API验收时应另定支持面并保留原dtype反例；本轮没有新增CPU复修或重跑有效六行矩阵。

| 实际执行 | 范围 |
| --- | --- |
| L494/500：134 passed，4.32秒 | 原公开masked模块，发生于L610之前，不包含私有新增3F。 |
| L518/522：退出1 | 默认调用先执行，float32 dtype一致性失败，order未到达。 |
| L623/627：原示例匹配 | 最终清理后的ones默认data/mask，不验证zeros/empty。 |
| L636/640：1 passed，0.30秒 | 既有test_creation_functions，不是新增like三项。 |
| 原正式评分：infra None | 准备300.479805秒，安装／测试未开始，137参考结果未知。 |

正常求解272.846秒，CC用时269.218秒、API249.557秒；54模型响应、53工具（26 Bash、8 Read、10 Write、9 Edit），两次实际工具错误。输入累计2,200,284 token含反复上下文、输出26,791；最大单请求66,015输入／2,920输出。预算为196608 context／65536输出／240回合／10800秒，正常completed，未观测预算截断。原失败评分317.068秒与求解分开，排队时长未知，不用报告内queue_wait=0代表派发前排队。

本臂每响应只生成一个工具，未测试并行工具运行支持。ma/creation/init读取可合并；大量整段替换和10次helper写入使上下文重复，早点检查实际执行函数可以减少遮蔽造成的无效迭代。这些是改进机会，不能由单样本推断稳定能力。

[线程预算范围独立核](../../reviews/non_author_dask_thread_budget_applicability_review_20261003.md)仅证明9378默认threaded可达、普通assert_eq用sync，未见7305同类默认process池证据。准备超时不证明线程耗尽；在途和同FP补评不热改。baseline重建、actor/manager清理及原None已核；最终runner、137参考和另一模型仍待实际结果。本报告不改原件／请求，不增加模型样本，不授训练资格。
