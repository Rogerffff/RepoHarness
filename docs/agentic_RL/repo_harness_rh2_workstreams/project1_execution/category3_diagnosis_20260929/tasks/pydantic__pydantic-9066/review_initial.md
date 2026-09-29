# pydantic__pydantic-9066 独立复核：初判（读作者结论前封存）

2026-09-29，独立复核者（Claude 子会话，不继承作者上下文）。本文写完即封存，后续核对写进同目录 `review.md`，不回改本文。

## 写本文前读了什么、没读什么

- 已读：
  - 统一规则 `task_screening_standard_v1_20260925.md` 的 §4、§5、§9；
  - 背景卡 `swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-9066/result.md`；
  - `s2/ingest/` 三个 jsonl 中本题的题面、public_hints、gold、test_patch、F2P（2 个）与 P2P（367 个，全部来自 `tests/test_json_schema.py`）；
  - `rh2/experiments/category3_cloud_20260929/pydantic9066/fallback.patch`，只读了补丁本身。
- 在原镜像 `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9066:latest`（本机 ID `5a05759a5549`）里只读查看了以下 base 源码：`pydantic/json_schema.py:988-1027`（`default_schema`）、`:1985-2001`（`encode_default`）、`:2105-2124`（警告种类说明）；`pydantic/type_adapter.py:101-107`（`_type_has_config`）、`:152-235`（`TypeAdapter.__init__`）；`pydantic/errors.py:87,91,131,142`（异常继承关系）；`pydantic/config.py:556-574`（`ser_json_*`）；`docs/concepts/dataclasses.md:242-300`；`pyproject.toml` 中的 `filterwarnings = ['error', ...]`；`tests/test_json_schema.py:1340-1368`（`test_non_serializable_default`）。环境为 pydantic `2.7.0a1`、pydantic-core `2.16.3`。
- 上游对照：从 PyPI 下载了 pydantic 2.7.0、2.7.1、2.7.4、2.8.0、2.9.0、2.10.0、2.11.0 的 wheel，以及 2.7.1 的 sdist，只看 `encode_default`、2.7.1 的 HISTORY 和测试。结果如下：
  - 2.7.0 的 `encode_default` 与本题 gold 逐行相同；
  - 2.7.1 把 `hasattr(dft, '__pydantic_serializer__')` 改成 `_type_has_config(type(dft))`，HISTORY 记为 "Fix `model_json_schema` with config types (#9287)"，并新增 `test_pydantic_types_as_default_values`，覆盖标准库 dataclass、pydantic dataclass、TypedDict、BaseModel 四种实例作为默认值；
  - 2.7.1 到 2.11.0 一直沿用这个写法，2.11 只多传了 `by_alias`。
- **未读**：作者的 `result.md`、`evidence/`，以及补丁目录里除 `fallback.patch` 以外的文件（`behavior.py`、`semantic_spec.json`、`revised_test_v1.patch`、`gold_catch_user_error.patch`、`materials_revised_v1.json`、`_edit_*.py`、`original_test.patch`）。
- **尚未运行**任何打了补丁的代码。

## (a) 题面核心要求

题面标题写的是 "Type `IPv4Address` not parsed"，但示例和报错都说明，问题不在“解析”，而在 JSON schema 默认值编码。模型字段 `ip: IPvAnyAddress = IPv4Address("127.0.0.1")` 调用 `model_json_schema()` 时，base 发出 `PydanticJsonSchemaWarning: Default value 127.0.0.1 is not JSON serializable; excluding default from JSON schema [non-serializable-default]`，并把默认值丢掉。标题措辞有误导，但示例能消解，属于 P4 一类，需登记。

按题面的一般含义理解，核心要求是：`ipaddress` 地址类型的默认值（题面示例是 IPv4，同类的还有 IPv6）在 JSON schema 中应被编码成对应字符串（`'127.0.0.1'`、`'::1'`），写进 `default`，不再发出警告，也不再丢默认值。pydantic 本身已知道如何序列化这些值：它们作为字段值时，`model_dump(mode='json')` 就能得到字符串。

`network` 和 `interface` 类型的默认值可以算同一要求的延伸实例，不是题面示例。

题面没有说，但修复不能破坏的现有行为：

- 已经能编码的默认值，输出不变，包括 `ser_json_timedelta`、`ser_json_bytes` 配置下的结果；
- 真正不可序列化的默认值仍走 `non-serializable-default` 警告，并排除默认值。这是 `json_schema.py:2116` 文档化的行为，公开测试 `test_non_serializable_default` 断言了它；
- 常用模型组合的 schema 生成不能因此抛错。

## (b) 我会构造的检验输入

以下每项都要在 base、gold、fallback 三方上对比 schema 中的 `default`、是否发出警告、是否抛异常。判定依据是公开需求，不以 gold 的输出为答案。

1. **题面与同类实例**：
   - `IPvAnyAddress` 字段配 IPv4 或 IPv6 默认值；
   - `IPv4Address`、`IPv6Address` 字段配对应默认值；
   - `IPvAnyNetwork`、`IPvAnyInterface`、`IPv4Network`、`IPv6Interface` 等字段配对应默认值；
   - `Optional[IPvAnyAddress]` 配 IP 默认值；
   - `Field(default=IPv4Address(...))` 写法；
   - `mode='serialization'`；
   - 标准库 dataclass 或 pydantic dataclass 自身带 IP 默认值字段时的 `TypeAdapter(D).json_schema()`。
2. **普通默认值，应与 base 完全一致**：int、str、float、bool、None、list、dict（含非字符串键）、tuple、set、frozenset、Decimal、UUID、Path、Enum（str、int 两种）、datetime、date、time、timedelta、bytes、`re.Pattern`、`AnyUrl` 实例、NamedTuple、`float('inf')`、`float('nan')`。
3. **config 相关**：
   - `ser_json_timedelta='float'` 下的 timedelta 默认值；
   - `ser_json_bytes='base64'` 下的 bytes 默认值；
   - `ser_json_inf_nan='constants'` 与默认 `'null'` 下的 inf、nan 默认值；
   - 同样的配置下，“容器或 dataclass 里同时有 IP 和 timedelta/bytes”的默认值，用来检验 fallback 不传 config 的后果。
4. **模型类实例作默认值**：
   - 标准库 dataclass 实例，内容普通，即背景卡里的回归；
   - 标准库 dataclass 实例，模型配置 `ser_json_timedelta='float'`、字段含 timedelta；
   - pydantic dataclass 实例、BaseModel 实例、TypedDict 值（运行时是 dict）；
   - 字段注解为 `Any` 而默认值是 dataclass 实例的情形。
5. **警告路径**：
   - 现有两例 `test_non_serializable_default`；
   - 任意自定义类实例（`arbitrary_types_allowed`）；
   - 函数或 lambda；
   - 类对象（`type`）；
   - `SecretStr` 默认值（base 走警告，gold 与 fallback 可能改成 `'**********'`）；
   - IP 放在 list 或 dict 里（`List[IPvAnyAddress] = [IPv4Address(...)]`）；
   - 标准库 dataclass 内含 IP 字段。
6. **专门找 fallback 退化的反例**（见 (c)）：
   - 回退分支里 `TypeAdapter(type(dft))` 会抛出不在捕获列表内的异常类型，例如局部类 dataclass 的前向引用无法解析，触发 `PydanticUndefinedAnnotation`，它是 `NameError` 的子类，不在捕获列表里；
   - 带 `__get_validators__` 的旧式类触发弃用警告，在 `filterwarnings=error` 下会成为异常；
   - 回退分支发出额外的序列化警告。

## (c) 静态上看 fallback 的风险

1. **成功路径与 base 字节级一致。** fallback 先原样执行 base 的 `to_jsonable_python(dft, timedelta_mode=..., bytes_mode=...)`，成功就直接返回。因此凡是 base 能编码的默认值，输出与 base 相同，行为变化只可能出现在 base 原本抛 `PydanticSerializationError` 的输入上，也就是 base 发警告并丢默认值的那些。这一点比 gold 保守：gold 把所有非 pydantic 默认值都改走 `TypeAdapter(type(dft), config=...).dump_python(mode='json')`，理论上可能改变 base 已有的输出，比如 inf、nan 在 `ser_json_inf_nan='null'` 下可能变成 `None`。待实测。
2. **异常处理的宽窄。**
   - 捕获的元组是 `(PydanticSchemaGenerationError, PydanticUserError, PydanticSerializationError)`。`PydanticSchemaGenerationError` 本身就是 `PydanticUserError` 的子类（`errors.py:131`），所以实际捕获的是全部 `PydanticUserError` 加上序列化错误。捕获后 `raise exc from None` 重新抛出最初的序列化错误，`default_schema` 照旧发出与 base 同文案的警告。
   - 这不算“吞掉应暴露的错误”：这些输入在 base 上本来就只是警告，没有暴露过异常。
   - 真正的风险在另一侧，即**捕获得不够**。不在元组里的异常会从 `encode_default` 直接穿出，因为 `default_schema` 只接 `PydanticSerializationError`，整个 `model_json_schema()` 会抛错。这就把 base 的“警告加丢默认值”变成了硬错误。可能的来源有：`PydanticUndefinedAnnotation`（`errors.py:91`，`NameError` 子类）、自定义 `__get_pydantic_core_schema__` 抛出的任意异常，以及 `filterwarnings=error` 下由警告转成的异常。
   - 这些都需要少见的输入，预计只影响边缘路径。
3. **`TypeAdapter(type(dft))` 不传 config。**
   - 好处：对 BaseModel、dataclass、TypedDict 这类自带配置的类型，也不会触发 `type-adapter-config-unused`。gold 正是因为传了非 None 的 `config.config_dict`，才在标准库 dataclass 默认值上报这个错，见 `type_adapter.py:195-204`。
   - 代价：在回退分支内部，`ser_json_timedelta`、`ser_json_bytes`、`ser_json_inf_nan` 不生效。之后那次 `to_jsonable_python(encoded, ...)` 面对的已是 JSON 兼容值，时长和字节不会再按配置改写。
   - 对单独的 IP 默认值，这没有影响。受影响的是“回退分支里的复合值同时含 timedelta、bytes 或 inf”，例如标准库 dataclass 同时有 IP 字段和 timedelta 字段，而模型配置了 `ser_json_timedelta='float'`。这时 schema 的 default 会与模型自己的 JSON 序列化不一致。
   - base 在这类输入上本来也不给 default，所以这不是把原先正确的输出改坏，而是新增输出不完全遵守配置。上游 2.7.1 的写法（非配置类型才走 TypeAdapter 并传 config）在这一点上更完整。
4. **按运行时类型而不是字段注解序列化。** 字段级的 `PlainSerializer` 等不会作用到 default 上。这一点 gold 和上游相同，不是 fallback 特有的问题，也不在题面范围内。
5. **容器里的 IP 仍不编码。** `list`、`dict` 里的 IP 经 `TypeAdapter(list)` 得到的是 `list[Any]`，逐项推断时仍会失败，最终走警告。gold 和上游 2.7.1 同样如此，因此不能用它区分 gold 与 fallback，也不宜据此加严修订断言。
6. **`TypeAdapter` 的命名空间取自调用帧。** 在 `json_schema.py` 内部构造时，解析不到用户局部作用域的前向引用。这与第 2 条的 `PydanticUndefinedAnnotation` 风险是同一件事。
7. **性能与设计取舍。** fallback 只在失败时才建 TypeAdapter，gold 对每个非 pydantic 默认值都建一次。从设计上说，fallback 与上游最终的修法（2.7.1 起的 `_type_has_config` 分流）不同，但属于合理的上游式思路：先用通用推断，失败后再借助该值所属类型的 pydantic schema 编码。没有吞错、提前返回或硬编码 IP 字符串之类的退化特征。

## (d) 修订测试应补什么

1. 保留原有的 IPv4、IPv6 两例。IPv6 相对题面的 IPv4 已是非示例实例，本题不必再补 T2c 实例；如果要加强，可加一个 network 或 interface 默认值。
2. **补标准库 dataclass 实例作 BaseModel 字段默认值。**
   - 断言 schema 正常生成，`default` 等于 base 的编码（例如 `{'x': 1}` 或 `{'name': 'Jon Doe'}`），`$defs` 与 `allOf`/`$ref` 结构与 base 一致，且不发出警告（pyproject 的 `filterwarnings=error` 会把警告变成失败）。
   - 这一条针对 gold 的回归。依据是：BaseModel 字段可以使用标准库 dataclass（`docs/concepts/dataclasses.md:242`），`encode_default` 的职责是编码字段默认值，而 base 已支持这个组合。另外，上游 2.7.1 为同一回归补了 `test_pydantic_types_as_default_values`。
   - 需要注意：文档示例里的默认值是 `None`，并没有直接演示“dataclass 实例作默认值”。公开依据主要是“base 已有的普通行为加上 `encode_default` 的职责”，写依据时不宜夸大成“文档明确示例”。
3. **断言必须检查 default 存在且取值正确，不能只检查“不抛错”。** 否则“gold 加捕获 `PydanticUserError` 后转成警告、丢掉默认值”这样的候选也能通过。它会把 base 已有的 default 丢掉，按公开行为属于退化。修订测试应让这类候选得 0。
4. 可以顺带加入 pydantic dataclass、BaseModel、TypedDict 实例默认值作护栏。它们在 base 与 gold 上本来就正常，只用于防止替代解改坏这些路径。
5. **不应加入的断言**：
   - 只有 fallback 才满足的行为，例如“dataclass 内含 IP 时要编码出 default”，或“容器内 IP 要编码”。前者上游 2.7.1 做不到，会发出警告，加进去等于按 fallback 的设计改题，违反 §5 “不追着候选改分”；
   - 实现细节，例如必须或不得调用 TypeAdapter。
6. 已在 P2P 中的护栏继续保留：`test_non_serializable_default[...]`、`test_{model,dataclass,typeddict}_default_{timedelta,bytes}[...]` 等。
7. **验收时应多跑一个上游式替代解**，即 gold 加上 2.7.1 的 `_type_has_config` 分流，确认修订测试对它也给 1。这样才能说明修订断言没有贴合 fallback 的具体设计。

## 初判

**暂定：fallback 可以作 D4 的替代正对照，但需第二步实测确认。**

- 它满足题面核心要求（静态推断：IP 默认值在回退分支经 `TypeAdapter(IPv4Address)` 编码为字符串）。
- 它对 base 已能编码的默认值保持字节级一致，对不可编码值保留同文案警告。
- 已知弱点有两条：回退分支不遵守 `ser_json_*` 配置；不在捕获元组内的异常会把警告变成硬错误。静态上看两者都只落在少见输入上，不影响题面核心要求与常用行为。

第二步需要重点核实的是：

- 公开测试（四个文件）在 fallback 下是否有新增失败；
- (b) 矩阵中 fallback 与 base 的差异是否只出现在 base 原本发警告的输入上；
- 能否构造出 fallback 把 base 的正常输出改坏，或在常用输入上抛错的反例。
