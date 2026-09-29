# pydantic__pydantic-8567 独立复核：初判（读作者材料前封存）

2026-09-29，独立复核者。写完不再修改。

## 本稿读过什么

- 统一标准 `task_screening_standard_v1_20260925.md` §3–§5、§9。
- `s2/ingest/` 三个 bundle 中本题的题面、gold、test_patch、F2P（1 个）与 P2P（158 个，全部在 `tests/test_validators.py`）、eval_cmd。
- 既有调查：`swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-8567/result.md`；`quality_expansion_20260925/results/pydantic__pydantic-8567/` 下的 `card.md`、`public_read.md`、`review.md`、`old_findings_delta.md`。
- 镜像 `c3keep/pydantic8567:src`（一次性容器、`--network none`）中 base 源码：`pydantic/functional_validators.py` 的 `PlainValidator`、`pydantic/functional_serializers.py` 的 `PlainSerializer`/`WrapSerializer`、`_generate_schema.py` 的 `_apply_annotations`/`_get_wrapped_inner_schema`。
- base 实跑一个小探针：公开原例得 `x=False, y=True`，`model_dump()` 为 `{'x': '0', 'y': True}`，JSON 为 `{"x":"0","y":true}`，复现题面症状；`Annotated[Custom, PlainValidator(lambda v: v)]` 在默认配置下可建类且保留原对象；`Annotated[int, PlainValidator(lambda v: str(v))]` dump 出 `'3'` 且无警告。

未读：作者 `result.md`、`evidence/`、`pydantic8567/` 下除 gold 与原 test_patch 外的任何文件内容。**如实说明**：我在 `ls` 时看到了该目录的文件名（如 `upstream261.patch`、`c3_reorder.patch`、`c3_serpass.patch`、`n_*.patch`），并且派发说明里写了 `c3_serpass` 漏修“serializer 与 PlainValidator 之间夹着验证器”的情况；文件内容没有读。

## 根因（源码直接可见）

`_apply_annotations` 按 metadata 顺序逐层包 handler，后面的 annotation 在外层。`PlainSerializer.__get_pydantic_core_schema__` 调 `handler(source_type)` 再写 `schema['serialization']`；`PlainValidator.__get_pydantic_core_schema__` 直接返回新的 plain validator schema，**不调内层 handler**。所以列表中排在 `PlainValidator` 前面（内层）的一切 metadata，包括 serializer，都被丢掉；排在后面（外层）的 serializer 能拿到 plain schema 并挂上 serialization。

## (a) 题面核心要求

按标题与期望行为的一般表述：**`Annotated` 里的 `PlainSerializer` 不论放在 `PlainValidator` 之前还是之后都要生效**，两种顺序对同一输入给出同样的验证与序列化结果。具体到原例：内部值仍为 `False/True`（验证语义不变），`model_dump()`、`model_dump(mode='json')`、`model_dump_json()` 都得到 `'0'/'1'`。

一般性理解包括：任意类型与任意 serializer 函数（不是只对 bool 或 `str(int(x))`）；`PlainValidator` 的 no-info 与 with-info 两个签名分支；`BaseModel` 字段与 `TypeAdapter` 等所有走 `Annotated` 的入口；Python 与 JSON 两种 dump 模式，并遵守 serializer 自身的 `when_used`、`return_type`。

题面没有要求：任意多个 serializer 的全排列可交换；改变 JSON Schema；改变 `PlainValidator` 的验证短路语义。

## (b) 我会用哪些输入检验“是否破坏旧行为”

1. **未知类型 + PlainValidator**：默认配置下 `Annotated[Custom, PlainValidator(lambda v: v)]` 能建类、保留原对象；python dump 仍返回原对象。这是 `PlainValidator` “取代内部验证”的常见用途，base 可用。
2. **验证短路**：`Annotated[int, PlainValidator(lambda v: v)]` 输入 `'abc'` 仍通过、返回 `'abc'`；docstring 示例 `Annotated[int, PlainValidator(lambda v: int(v)+1)]` 得 2。
3. **验证链顺序**：`Annotated[int, AfterValidator(f), PlainValidator(g), AfterValidator(h)]` 中 f 不运行、h 运行（文档 validators.md 所述顺序语义）。
4. **原本就正确的顺序**（validator 在前、serializer 在后）结果不变。
5. **`when_used='json'`**：serializer 在前时，python dump 保留原值、JSON dump 用 serializer。
6. **多个 serializer**：`[PlainSerializer(a), PlainValidator(v), PlainSerializer(b)]` 应仍由最外层 b 生效（与 base 在无 validator 干扰时的“外层覆盖”一致）。
7. with-info validator 仍收到 `field_name` 与已验证数据（公开旧测试 `test_plain_validator_field_name`）。
8. 无 serializer 时的 dump 输出与警告：validator 返回与注解不同类型的值（`Annotated[int, PlainValidator(lambda v: str(v))]`）在 base 无警告、原样输出。这是没有文档承诺的边缘行为，改变它记观察，不直接判不合理。
9. 公开旧测试：整份 `tests/test_validators.py` 与 `tests/test_serialize.py`。

## (c) 我认为合理的修法

1. **在 `PlainValidator` 内委托内层 schema 做序列化**：调 `handler(source_type)`，把结果作为 `serialization` 的依据（如 wrap serializer 调 `h(v)`，或直接取内层的序列化规则）。gold 属于此类，但它无保护地调 handler，会让未知类型建类失败——必须捕获 `PydanticSchemaGenerationError` 并回退到旧行为。回退后，“未知类型 + serializer 在前”仍会丢 serializer，属残余缺口，需要单独判断。
2. **只转移内层已有的 serialization 规则**：取内层 schema 的 `serialization`（并同样保护构建失败）。更轻量；风险是 serializer 与 PlainValidator 之间若有别的 metadata 把 schema 包了一层（例如 after 验证器或不适用的约束），顶层没有 `serialization` 键就会漏掉。
3. **在 `_apply_annotations` 层调整顺序**：把位于 `PlainValidator` 之前的 serializer 类 metadata 移到其后，保持 serializer 之间、validator 之间各自的相对顺序。这天然覆盖未知类型；风险是影响面在公共组合逻辑，要证明验证顺序与多 serializer 覆盖关系不变。
4. 不合理的方向（应被拒）：全局重排所有 metadata；把 `PlainValidator` 改成先跑内层验证；只修 no-info 或只修 with-info；只修 JSON 或只修 Python；忽略 `when_used`；硬编码 bool、`str`、字段名或原例 lambda；无条件调用 handler 导致未知类型建类失败。

关于“serializer 与 PlainValidator 之间夹着验证器”：它确实是“serializer 放在 PlainValidator 之前”这一表述的实例。但夹在中间的验证器被 PlainValidator 取代、根本不运行，属于死代码写法；现实里更可能来自嵌套别名展开（`Annotated[Alias, PlainValidator(...)]`，Alias 内含 serializer 和验证器）。初判倾向：若只有“夹着被短路的验证器或不适用约束”这类写法触发，按罕见路径登记 T3；若常用的非验证 metadata（`Field(...)`、`Strict()`、适用的约束等）也会触发，就应升为同一核心要求的实例（S1）。第二步要实测区分。

## (d) 修订测试应补什么

1. 两种顺序都断言**精确值**，覆盖 `model_dump()`、`model_dump(mode='json')` / `model_dump_json()`，并断言内部值 `False/True`（原测试只断言 `isinstance(..., str)`，常量 `'x'` 也能过）。
2. 一个**非示例实例**：不同类型与 serializer（如 int 与 `x * 10`），serializer 在前。
3. **with-info** 的 `PlainValidator` 在 serializer 在前时也生效。
4. **`when_used='json'`** 在 serializer 在前时被遵守。
5. **未知类型 + PlainValidator 能建类**（公开旧行为）。gold 过不了这一条，按 §9 D4 需要经独立核实的替代正对照，并记录 gold 失败；不能为保住 gold 删掉这条。
6. 可选：`TypeAdapter` 路径；多 serializer 外层覆盖。夹验证器的情形等第二步实测后再定是否入测试。

注意不要过严：不应要求无 serializer 时的 dump 警告行为、JSON Schema、内部 helper 或 schema 形状；“未知类型 + serializer 在前”若同时拒掉 gold 与上游 2.6.1 式修法，需要单独论证是否属于核心要求。
