# pydantic-5386 初判（封存于读 gold、测试与历史结论之前）

2026-09-30 / 审计者（Sonnet 5.5）。依据：只读题面与 base 代码（镜像 `/testbed`，HEAD `6cbd8d69`）。写完不再改。

1. 题面只给症状：`__init_subclass__` 里读不到子类字段，没有点名任何接口、调用时机或参数。
2. 根因在 base 可见：`ModelMetaclass.__new__` 里 `super().__new__` 会触发 `__init_subclass__`，此时字段还没收集（`collect_fields` 需要类对象本身）。"让 `__init_subclass__` 里直接能读 `model_fields`"在现有结构下不现实；合理修法只能是"类建完后再调一个钩子"。
3. 钩子的名字、是否 classmethod、是否转发类关键字参数、对基类自己是否触发，题面全没说。我按自己对 pydantic 2.x 公开 API 的记忆取名 `__pydantic_init_subclass__`；这个名字不在题面，也不在 base 代码或文档里（base 里只有 `__init_subclass__` 相关旧测试 `test_custom_init_subclass_params`）。
4. N1：`BaseModel` 加 classmethod `__pydantic_init_subclass__(cls, **kwargs)`，元类末尾（`complete_model_class` 之后）调用 `super(cls, cls).__pydantic_init_subclass__(**kwargs)`。文件 `pydantic5386/cands/N1.patch`，sha256 前缀 `da9001181120`。已在 base 镜像冒烟：子类的 `model_fields`、类关键字参数、既有 `tests/test_main.py` 都正常。
5. 预期风险：若隐藏测试写死某个钩子名，题面推不出来（P3，R-f 需要公开依据）；不同名字的合理实现会被拒（T1）；若测试只检查钩子被调用而不检查其中 `model_fields` 已完整，"在钩子里读到字段"这个核心要求缺直接断言（T2a）。
6. 倾向：需要修订（题面补钩子契约，测试补"字段可用"断言）。待读 gold 与测试后验证。
