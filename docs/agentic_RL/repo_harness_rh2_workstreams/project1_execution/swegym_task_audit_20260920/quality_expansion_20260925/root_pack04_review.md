# Pydantic 包：根任务抽验

2026-09-25 / Codex B。**三题静态交付通过抽验：6283保留有条件开发候选，5386先处理接口与验收，8567先做参考补丁兼容性诊断。** 本次只读原件与历史证据，没有运行项目或批准模型探针。

| 题目 | 根任务核到的依据 | 保留的边界 |
| --- | --- | --- |
| 5386 | 公开要求是在类定义期间读字段；隐藏新增测试却在无字段类上断言新命名的`__pydantic_init_subclass__`调用。base先调用父元类建类，随后才`set_model_fields`；gold的新hook放在字段收集和`complete_model_class`之后。 | 固定新接口与未测字段就绪是实际静态缺口，不能通过重复gold解决。`complete_model_class(...raise_errors=False)`可以返回False，因此字段metadata可读不等于所有前向引用已解析。正式修订接口/题面尚未批准。 |
| 6283 | 新equality断言对应公开问题。`RootModel`在类上定义extra/private默认值，base的共享`model_construct`仍写实例属性；gold按root标识跳过这些写入，保留post-init。 | 目标得到覆盖不等于共享构造行为完整。`model_construct`不验证输入，不能要求非幂等validator前后输入的两条路径相等，也不能强制归一化显式`_fields_set`。 |
| 8567 | base的PlainValidator直接生成plain schema，不调用传入的inner handler；gold无条件调用`handler(source_type)`。annotation包装链确可到未知类型报错路径。新增断言只看Python dump值为str，没有检查JSON或精确内容。 | 默认配置下无schema的Custom类型是有依据的窄对照，但尚未实际运行，不能称已证gold回归。生成serialization schema不等于运行inner validation；base依赖为pydantic-core 2.15.0，不能照题面旧版本替代。 |

六份原日志和账本与报告一致，安装退出均0；noop测试退出1、gold退出0。5386为120pass/1fail/29skip/9xfail→121pass/29skip/9xfail；6283为40pass/1fail/3xfail→41pass/3xfail；8567为164pass/1fail→165pass。参考P2P分别106、38、158，失败均0；这些运行不是本次新增实验，也不证明actor开发条件。

核对五个角色的显式Astra/high/fork_turns=none记录、九份封存稿及整包封存后材料release顺序成立。根任务抽验关键源码、gold/test补丁与日志；没有重扫已核的完整源码树。协调修正中保留5386/6283整体正确性unknown、6283覆盖缺口和8567动态未知的做法合理。

无需返工关键结论。执行需求见[定向提案](pack04_followups.md)，仍由任务二择取并登记；私有base/gold对照不能代替公开actor验证。
