# 6283：私有属性保护的条件草稿

2026-10-03。此目录是新的私有材料草稿，尚未发布或用于评分。原 `pyd6283-behavior-v1`、CPU结果、模型FrozenPatch和raw reward均保留原字节。真实Python3.8／core0.42复现回执仍待，不能把源码机制重放写成实际运行失败。

Qwen首臂在普通RootModel上修好了实例字典污染，却在构造完成后无条件删除 `__pydantic_private__`。公开 `docs/usage/models.md` 已规定，`model_construct()` 应同正常构造一样初始化私有属性；公开测试也已覆盖RootModel私有默认值的读写。现有40参考没有把这两个行为组合起来。[候选初审](../../../../model_audits_20261003/6283_qwen36_a1_preliminary.md)给出源码依据和适用限制。

本草稿只追加一个P2P：带 `PrivateAttr(default='abc')` 的RootModel经 `model_construct(42)` 后仍能读取 `'abc'`。它不要求内部字典形状、不重新验证输入，也不要求原base的相等缺陷先修好。原2 F2P和38 P2P完整保留，提案为2 F2P＋39 P2P，共41参考。已有正对照gold保留合法私有初始化；是否实际通过新节点仍待验证。

候选矩阵保留noop／gold／validate_construct，追加原Qwen补丁作为具体负对照。Qwen差异逐字绑定原FrozenPatch与源diff，未改模型解。先确认真实依赖下的私有状态回归，再由非作者核查材料；按旧请求安全收口、新版本发布、CPU正负对照及非作者验收接续。公开题面和hints保持不变，新私有测试不得交给solver。

[静态记录](static_result.json)只证明补丁可应用、Python3.8语法可解析、所有v1测试AST保留、参考数与字节身份；不证明pytest结果、正式consumer或模型能力。
