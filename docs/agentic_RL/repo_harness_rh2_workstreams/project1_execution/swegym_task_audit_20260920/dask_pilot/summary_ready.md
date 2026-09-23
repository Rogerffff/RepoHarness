# Dask 五题静态复核：6818、7894、8597、9212、9378

2026-09-20 / Codex。仅复核这五题的实际公开 prompt/hints、test_patch、gold、关键 exact-base 源码与旧 L1 claims；没有运行 Docker、模型、SWE 测试或新候选，没有改题目、生产代码和历史证据。

**建议四题可作小批诊断探针，7894 先做一个针对性反例。这里的 `probe_candidate` 只表示值得探测，不是题目质量通过或入池认证。** 建议优先顺序为 8597 → 6818 → 9378；9212 可作公开提示了实现的低难度对照，不用于衡量无提示定位能力。

| 题目 | 建议 | 主要依据与限定 | 最小后续 |
| --- | --- | --- | --- |
| [6818](records/dask__dask-6818.json) | `probe_candidate` | 目标是不同 blocksize/persist 调用下结果一致；新增测试检查任务名，P2P检查确定性。S3原例断网不可原样跑，不代表只能推理：可以用本地CSV定位。同名内部属性断言不能冒充完整persist行为覆盖 | 以本地CSV检查实际缓存/结果行为；非gold形状的合理命名方案按行为判断。3个截断P2P键留既定参考修复分期 |
| [7894](records/dask__dask-7894.json) | `needs_counterexample` | 公开要求同时重排 depth/boundary，但7个新增参数点的 boundary 都是非 `none`；trim逻辑无法区分它们。旧“只修depth一定被抓住”结论不成立 | 独立候选只重排depth，比较原7点与混合 `none`/非 `none` 边界的确定性输入。尚未执行，不写成已证实假通过 |
| [8597](records/dask__dask-8597.json) | `probe_candidate` | 完整本地复现与NumPy预期足以定义问题；省略traceback不等于缺少需求。P2P确实检查不能无条件关闭chunk大小保护。旧pytest8导致的相邻用例失败已修 | 按原公开面探针；保留chunk/config对照，不为降低定位难度自动加入隐藏traceback |
| [9212](records/dask__dask-9212.json) | `probe_candidate`，低难度对照 | 公开文本已经给出gold核心函数体，导入片段有小错误。测试允许不同实现，但只检查一个枚举类中的两个成员关系；不能称跨类身份或完整确定性已验证 | 标记 `statement_contains_fix`；需要简单执行对照时使用。8792实现已在本题base中，数据划分时记录这一关联 |
| [9378](records/dask__dask-9378.json) | `probe_candidate` | 正文明确提出 `dask.array.ma.*` 路线，测试与它对应；顶层示例仍有解释空间，应看具体候选。固定3×2 mask不能证明已排除硬编码。旧“缺docstring会导入失败”不成立 | 观察模型自然选择的API；若产生只修顶层且满足公开现象的候选，再决定是否需要最小澄清，不直接改题 |

## 纠正的旧结论

- 五题实际 `public_hints` 都是相同的719字符通用操作提示。旧记录引用的 raw hints、讨论链接和完整 traceback 不在当前公开面；不能用它们定义模型已知信息。
- 7894 的 `map_overlap(..., **kwargs)` 获得本次调用的局部字典；gold 的 `kwargs.pop` 不会删除外部调用者原字典中的键。`new_axis` 比本题公开要求更广，不以候选是否额外实现它判断优劣。
- 7894 的关键覆盖缺口来自实际分支：exact-base `overlap.py:103–120,153–165` 只区别 boundary 是否为 `none`，新增测试却使用 `0/reflect/nearest`。这是自然半修复的有限反例方向，不是新一轮反作弊扩审。
- 9378 exact-base `dask/utils.py:773–774` 明确把缺失 docstring 转为空字符串，因此撤回旧跨版本崩溃假设。`empty_like` 只比较 mask 是合理的测试边界，但不证明任意输入均正确。
- 旧“判别力完整”“gold短而精准所以质量好”“与其它题同文件因此必须同侧”等说法分别收窄为已观察的具体能力、一个参考解法与待数据划分处理的关联，不能代替证据。

## 环境与验证边界

| 题目 | 当前已有环境证据 | 本轮回读 |
| --- | --- | --- |
| 6818 | `compat_v1` 维修对照；gold 124 passed、9 skipped、3 xfailed，来源1+121参考通过 | gold/noop日志SHA-256匹配，noop=0、gold=1 |
| 8597 | `compat_v1` 维修对照；gold 119 passed、2 skipped、2 xfailed；旧两条pytest失效用例已在两侧PASSED | 同上；来源P2P仍是116条，不自动增补参考 |
| 9212 | `compat_v2b` 维修对照；gold 126 passed、3 skipped；原恒失败emscripten用例已恢复 | 同上；空白截断的解析风险不能因环境恢复自动核销 |
| 7894 | 50题原基线中的一题；gold 80 passed | 原baseline两侧日志SHA-256匹配，noop=0、gold=1 |
| 9378 | 50题原基线中的一题；gold 137 passed | 原baseline两侧日志SHA-256匹配，noop=0、gold=1 |

每题JSON逐项保留旧 claim 与 `confirmed / refuted / unresolved / superseded_env` 处置，共112项；列出材料行号与摘要、base commit/源码摘要、10份日志摘要及未执行的最小后续。真实基座探针仍需让 agent 和 grader 消费所选环境的确切身份；已有环境对照没有验证模型解题质量，也不构成正式训练资格。
