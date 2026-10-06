# Pydantic 8511 当前题卡

2026-10-03。**继承护栏与窄修工件已准备，私有安装／五节点已实跑，正式验收仍待；不使用gold作为正对照。**

修复目标是赋值式Field(repr=False)隐藏字段，普通字段继续显示。R4已证明gold与窄修原评分均1，但gold使无本地注解的子类继承必填Field、repr=False Field或工厂Field时装饰失败；窄修只遍历本地annotations，三类行为均通过。[历史汇总](../../../../../task2_swegym_dev_conditions_20260925/results.md)与[既有复核](../../../../../swegym40_status_20260929/reviews/mypy_pydantic.md)保留，不重做发现过程。

原1 F2P＋168 P2P保留，追加四个P2P：三类子类正常构造／取值，以及默认Field仍显示。三类继承检查不要求base尚未满足的repr=False效果，不把它们误分为新F2P。[窄修工件](controls/narrow.patch)直接复用历史真实导出，未自行改写为另一解法。

新正式预期noop0／gold0／narrow1。gold失败原因必须是继承回归，而非安装或收集失败。本题安装用既有 `pydantic_v1` 离线依赖＋editable方案收口；原R4的pdm rc127／make rc2仍是历史事实，原reward1不能替代完整安装验收。

cpu-a第五版入口的私有诊断已实际运行三份候选：editable安装、从候选pyproject导出测试依赖、离线测试依赖安装和收集均退出0；Python3.8.19／core2.14.5／`/testbed`源码身份及实际2 CPU／4 GiB／PID512吻合。所选五个节点中，noop仅原F2P失败，gold三类继承在创建子类时报准确的无注解Field `TypeError`，narrow全部通过，三个容器均零残留。[逐节点与原件指针](../../cpu_diagnostics_20261003/private_results.json)固定本轮事实。

这证明本轮私有安装配方可执行及四个新增节点的预期区分，**不等于完整173参考的正式reward、consumer安装验收或非作者CPU复核**。新材料登记、完整正式矩阵、公开actor交付及独立核查仍待，再提交探针。
