# pydantic__pydantic-6283 静态质量短卡（2026-09-25）

目标是同等根内容经常规构造与model_construct后相等；base `a29286609e79`。静态候选，**needs_review** 的主要未决条件是实际actor开发路径；保留覆盖缺口，不继承旧ready标签。用途仅development_diagnostic。

|需求|断言/依据|判断|
|---|---|---|
|常规与construct相等|唯一F2P新增RootModel[int](42)相等|直接覆盖单例|
|类型、不同值、私有属性仍影响相等|同F2P旧三行及root P2P|相关覆盖|
|construct跳过验证并保留private/post-init|旧嵌套构造、公开实现|无验证已测；private×construct未直接测|
|BaseModel共享构造不退化|公开test_construction.py|不在本题评分选择|

八方面：已读公开目标/精确base；全部修改（仅旧测试加一行，无新helper）；唯一F2P与受影响P2P；RootModel专用构造等合理替代；gold共享构造→root委托→eq调用链；Python/core/pytest开发需求；gold投影和单文件恢复；授权私有暴露/用途。语义抽读root文件175–355涉及构造、赋值、validator、private及四类相等；评分外读共享构造默认/extra/fields_set断言，其余P2P只核状态。

09-19修订grader两安装RC0，noop目标失败，gold通过；38 P2P逐身份PASSED。44 collected，gold41 passed/3 extra配置xfail；parser41。gold只投影main.py，历史初态保留pyproject/lock变化。actual actor消息、状态、权限/import、资产和image ID仍unknown。

gold没有跳过实际私有属性初始化：有post-init仍先调用，只限制None fallback。未发现已证gold回归；旧记录把覆盖缺口当回归、同主题自动同簇及无泄漏结论均收窄。字段集合可由_fields_set显式指定，不应为了相等一律改成相同集合。

唯一优先下一步：任务二按实际actor入口运行题面显式RootModel子类与BaseModel对照smoke，同时采集初态和导入来源；本轮未执行/派发。独立交叉复核与协调收口已完成，详见[复核](review.md)。完整证据见[初判](analysis_before_history.md)及[差异](old_findings_delta.md)。

协调收口：保留有条件开发候选；公开相等目标与新断言直接对应，但private×construct和共享BaseModel覆盖缺口继续成立，不能概括为仅actor未验。 check27按完整正确性口径记unknown，保留目标路径局部正证据。 原主审card/record按完成hash归档；封存初判、delta、review未回改。
