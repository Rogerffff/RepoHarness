# Pydantic 8567：两份正对照候选的非作者语义窄核

2026-10-03 / Codex 非作者子代理。对象为 `pyd8567-order-old-behavior-v5` 的 c3_reorder 与 ok_post_attach。已接触题主私有上下文和四节点结果，接续 [材料窄核](non_author_remaining_material_review_20261003.md)，不是盲审。仅写本报告与同名 JSON；没有运行项目依赖、SSH、Docker、模型或修改固定发布成员。

**两份候选都具备修复公开 serializer 顺序问题的真实机制，可继续作为不同实现路线的正对照提名。限定下述内置元数据路径，未发现可由源码直接证明的公开行为回归。当前新consumer的完整162正式参考仍缺，不能称“一般语义通过”或完整正对照已验。** 本轮不新增题级发布阻断；普通探针仍按前一报告等待正式 CPU／actor／运输验收。

## 固定身份与已有证据

| 对象 | SHA256 |
| --- | --- |
| 当前 effective_test.patch | `a1ed762e8f64ddaa9654c2281e66e7be993de5b6b13a27ee04e8cf3387e5bfc6` |
| c3_reorder.patch | `221bbe05b331ff83740ba64eff3a91666c5eb0b2062e80b1fa3c4e75721f86a1` |
| ok_post_attach.patch | `8095d0789fc5edc5fc6d4a693aabed717e2ec26faf926fc25b79c0b1da0d6543` |

复用上一窄核已经确认的候选字节、base `8060fa1c…`、发布输入和私有安装身份。本轮读取两份补丁、有效测试、公开 base 必要源码／文档／现有 serializer 测试及上一报告；没有改动或重新执行历史工件。

既有私有 root 诊断在 Python3.8.19／core2.15.0、正确源码及候选 SHA、断网2 CPU／4 GiB／PID512下，两份候选均通过四节点：原v4 F2P、未知类型 serializer 两种顺序 B03 F2P、被取代的未定义内层前向引用 B06 P2P、Python3.8 stdlib TypedDict 内层 N3 P2P。原v4 F2P 的一次通过同时执行了其中多个断言，包括双 serializer 外层优先、TypeAdapter list、when_used=json、带 info 的 PV、被取代的 StrictBool／AfterValidator、中间 AfterValidator。这些是该固定测试体的实证；该四节点结果本身不能覆盖所有WrapSerializer／BeforeValidator／WrapValidator组合，也不等于162参考全过。

**旧证据继续有效。** 上一材料核查已接触的云端result／review及题主本轮补充均确认：c3_reorder已有独立语义核查与v4正式31行；ok_post_attach也在旧v4独立合理实现检查中获得支持。它们的适用意见和范围内行为直接复用，本轮不机械重核或重跑。新四节点补充的是B03／B06／N3及当前私有安装身份，不能把“本轮没跑某种布局”写成“此前从未验证”。A16／A17源类型／类型参数serializer、B11装饰器形式等旧范围限制保留，不把附带改进或旧题外缺陷提升为新阻断。

## 实际路径及为何能修复

公开 base `_generate_schema.py:1693` 的 `_apply_annotations` 先将元数据按原顺序叠成 handler；最后的元数据在外层。`_get_wrapped_inner_schema`（1805行）调用元数据的 `__get_pydantic_core_schema__`，普通 before／after／wrap validator 都调用内层 handler，再包成相应 function schema。`functional_validators.py:155` 的 PlainValidator 直接返回 function-plain schema，**不调用传入 handler**。因此左侧 serializer 原本没有机会构建，这就是题面的丢失机制。

`functional_serializers.py:32`／`:75` 的 PlainSerializer／WrapSerializer 调用 handler 得到 schema，再把其 serializer 设置在 `schema['serialization']`；没有把 serializer 当验证器运行。两份候选都沿用这些原方法，保留 func、info、return_type、when_used 等选项。

- **c3_reorder**：在已展开元数据且完成 known-type prepare 后，找到最后一个内置 PlainValidator；仅把它左侧的 PlainSerializer／WrapSerializer按原相对顺序移到其紧外层，其它左侧元数据留在 PlainValidator 里面，右侧元数据次序不变。PlainValidator 自身未改，因此仍不会构建或调用被取代的内层 handler。此时 serializer 的 handler 是 PlainValidator 的输出，取得 function-plain schema后即可设置序列化。它并非把所有元数据都挪到外层。
- **ok_post_attach**：先按原顺序生成最终 schema；如果最终 schema 或连续 function-before／after／wrap 的内层已有 serializer，就保留现有结果。否则按相对顺序补挂最后一个 PlainValidator左侧的 serializer。补挂所用 handler仅返回已经构建的 `current`，并未调用原 source_type 的内层 handler。它能修复丢失，而不重新引入被 PV 取代的未知类型、前向引用或 TypedDict schema。

两份候选都可能为 serializer 声明的 return_type调用 `handler.generate_schema(return_type)`，这是序列化输出类型的构建，不能误记为恢复被取代的 source_type 内层验证。四节点结果也支持这一区分。

## 逐项语义判断和证据边界

| 项目 | c3_reorder | ok_post_attach | 结论层级 |
| --- | --- | --- | --- |
| 单PV，serializer在前／后 | serializer在PV紧外层被原方法消费；在后者保持原位 | 在前丢失时补挂，在后已有时保留 | 公开原例及B03已有实证，机制核对成立 |
| PV左侧 before／after／wrap 及约束 | 原相对次序留在PV内层；PV不调用其handler | 原PV已跳过它们；补挂handler只返回结果 | After／StrictBool已有实证；Before／Wrap依源码推断，未在本轮运行 |
| serializer与PV之间有元数据 | 只移动serializer，避免把中间验证器带到外层 | 只补serializer，不重新构建中间验证器 | 中间After已有实证；其它同类推断待窄验 |
| PV右侧 before／after／wrap | 顺序不变，仍包在PV／serializer外面 | 顺序不变；补挂在最终包装上 | 构建路径未改变验证次序；dump的core执行未新增实证 |
| 两侧都有serializer | 左侧移入后，右侧仍更外层；原方法设置serializer时维持覆盖顺序 | 从根及function包装查到已有serializer即返回，左侧不抢优先级 | v4的Both外层优先已有实证；其它包装复用旧适用意见，本轮未新增该组合运行 |
| 左侧有多个serializer | 保留它们相对顺序，最后一个设置相同schema上的serializer | 按相同相对顺序补挂，最后一个覆盖 | 与原serializer方法一致；不声称所有serializer会串联执行 |
| WrapSerializer | 与PlainSerializer一起移动，仍调用原WrapSerializer方法 | 与PlainSerializer一起补挂，仍调用原方法 | handler及when_used选项原样保存；旧适用意见复用，本轮未新增nxt交互运行 |
| 多个PV | 选择最后PV，其左侧其它PV仍被跳过；serializer取自最后PV左侧 | 原最后PV已取代前面handler，再补其左侧serializer | 静态路径一致，但不能据此新增多PV公共保证，见下文 |

序列化优先级按可观察输出判断，不能仅因补挂位置在最终 function schema上就判错。对内置 before／after／wrap，schema生成和验证顺序可直接追踪；序列化 handler如何穿过这些包装由实际core执行证明，复用旧适用运行证据。本轮未模拟core来替代它；只有材料／core／行为条件差异影响该范围，才补对应布局。

**多PlainValidator的边界应保留。** 当前公开 base 的 `docs/concepts/validators.md:69-70`明确只允许一个PlainValidator；“最后PV跳过前面PV”可由源码推导，但这不是本题新增的公共支持承诺。不要为了验证候选而把多PV、任意自定义 `__get_pydantic_core_schema__`、自定义包装／definition-ref拓扑扩成正式新要求。若以多PV做一次低成本私有健壮性检查，应记录为范围外观察，不能单独据其失败拒绝本题正对照。上述结论限定标准内置元数据；ok_post_attach只遍历三类function包装，并不是通用的serializer发现算法。

## 最小后续CPU检查建议

没有新发现的已证缺陷需要改固定测试。优先完成计划中的正式五候选矩阵，验证162参考及新节点的正式消费；旧v4已核中间元数据、优先级和相关serializer行为不另设一轮CPU要求。

如题主需要一个低成本交叉检查，最多补**B03未知类型与WrapSerializer两种顺序**这一组，先用于ok_post_attach；c3_reorder只有相应旧证据不覆盖或条件变化时才补。它针对两份补丁共同处理WrapSerializer、但新B03实际只用PlainSerializer的组合，不是已证缺陷或新增评分闸门：

```python
class Unsupported:
    pass

serializer = WrapSerializer(lambda value, nxt: 'custom!', return_type=str)
validator = PlainValidator(lambda value: Unsupported())
for annotation in (
    Annotated[Unsupported, serializer, validator],
    Annotated[Unsupported, validator, serializer],
):
    adapter = TypeAdapter(annotation)
    value = adapter.validate_python(1)
    assert isinstance(value, Unsupported)
    assert adapter.dump_python(value) == 'custom!'
    assert adapter.dump_json(value) == b'"custom!"'
```

以上只是建议，未执行。WrapSerializer允许自行返回结果、不调用nxt；不要要求未知类型的默认nxt序列化本来就能成功，借此扩大B03。无需把多PV、无关JSON schema、source-type或类型参数serializer范围加入新检查。若正式矩阵或此窄查出现差异，保存逐布局输出、警告、异常及源码身份，先判断当前公开范围和旧证据能否覆盖，再作局部确认。

## 当前用途与停止条件

两份提名分别代表重排和事后补挂，可继续作为正式consumer验收的不同机制正对照候选。本报告完成其材料／源码层窄核，**未签发完整正对照资格**。正式162参考必须逐ID完整执行，新增三节点保留；运行／运输／actor条件和非作者CPU核查仍按已有计划完成。旧适用核查直接复用，不因换到新三方流程失效；可选B03交叉检查也不赋予所有自定义schema或多PV兼容结论。

没有新的公开可证反例时，不因还能想象范围外包装而延长本轮；若出现范围内异常，按该布局做局部确认并撤下有回归的提名，保留另一份及原材料。现阶段不需要更换两份补丁、修改发布清单或再做全题盲审。机器可读结论见 [同名JSON](non_author_8567_positive_semantics_20261003.json)。
