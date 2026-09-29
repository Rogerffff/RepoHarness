# pydantic__pydantic-9066 独立复核：`fallback` 能否作 D4 替代正对照

2026-09-29，独立复核者（Claude 子会话，不继承作者上下文）。

**总判断：`fallback` 可以作本题窄修订的替代正对照。这里的窄修订是 R-c：在 F2P 测试里补一条“标准库 dataclass 默认实例”的回归检查。我同意作者的处置：用 `fallback` 作正对照，记录 gold 在修订版上的失败，经 D6 交第2类。无阻断项。** 有几处表述需要收窄，`fallback` 的两类已知缺口需要登记，见第四节。

## 复核方式

步骤按规定顺序进行：

1. 先读题面、gold、测试补丁、F2P/P2P 和 `fallback.patch`，写出初判 `review_initial.md`。写完后没有再改。
2. 自己在一次性容器里实测。
3. 最后才读作者的 `result.md` 和 `evidence/`，逐条核对。

读作者结论前，我还额外做了一项工作：从 PyPI 取上游 pydantic 2.7.0 至 2.11.0 的 `encode_default`，以及 2.7.1 的测试，作为“上游式修复”的参照。

实测环境：

- 原镜像 `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9066:latest`，ID `sha256:5a05759a…`，RepoDigest `@sha256:36a21435…dc31`；
- Python 3.8.19，HEAD `a3b7214a1`，pydantic `2.7.0a1`（从 `/testbed` 以 editable 方式导入），pydantic-core `2.16.3`；
- 每次 `docker run --rm --network none`，以 root 身份在容器内 `git apply` 候选补丁。

对比了五个变体：

| 变体 | 内容 |
| --- | --- |
| base | 不打补丁 |
| gold | 本题 gold |
| `fallback` | 作者的替代实现 |
| **上游式** | 我自己构造：gold 加上上游 2.7.1 的一行改动，把 `hasattr(dft, '__pydantic_serializer__')` 换成 `_type_has_config(type(dft))` |
| gold_catch | 我独立构造：gold 把 `except` 扩到 `PydanticUserError`。事后比对，它与作者的 `gold_catch_user_error.patch` 逐字节相同，sha256 `95824e97…` |

复核脚本和原始输出放在本次会话的临时目录，未入库。附录给出关键构造，可据此复现。**没有跑正式评分，没有删镜像，也没有 commit。**

另外说明：`review_initial.md` 在本复核进行中被另一会话提交进了 `e5af884`，不是本复核提交的，内容与我写入时一致。

## 一、D4 三问的结论

### 1. 是否满足公开题面要求：满足

题面要求：`IPvAnyAddress` 字段以 `IPv4Address("127.0.0.1")` 为默认值时，schema 应带可编码的 default，不再发出 `non-serializable-default` 警告。

在我的 91 例矩阵里，以 IP 对象作默认值的 13 例（A01–A13），`fallback` 都给出了正确字符串且无警告。另有 A14 用字符串 `'127.0.0.1'` 作默认值，各变体本来就正常。这 13 例是：

- 题面原例；
- IPv6；
- 字段类型为 `IPv4Address`、`IPv6Address` 本身；
- `IPvAnyNetwork`、`IPvAnyInterface`、`IPv6Network`、`IPv6Interface`；
- `Optional[...]`；
- `Field(default=...)`；
- `mode='serialization'`；
- 标准库 dataclass、pydantic dataclass 自带 IP 默认值时的 `TypeAdapter(...).json_schema()`。

base 在这 13 例上全部是“缺 default 加 1 条警告”。gold 与上游式的结果和 `fallback` 相同。

### 2. 是否不破坏相关旧行为：未发现常用行为被破坏

**base 原本能编码的用例，输出完全不变。** base 无警告、正常生成的用例共 49 个，覆盖：

- 普通值 31 例：int、str、float、bool、None、list、dict（含整数键）、tuple、set、frozenset、Decimal、UUID、Path、三种 Enum、datetime、date、time、timedelta、bytes、Pattern、AnyUrl、NamedTuple、±inf、nan、ByteSize、Any 等；
- `ser_json_*` 相关 5 例：`ser_json_timedelta='float'`、`ser_json_bytes='base64'`、`ser_json_inf_nan` 两种取值，以及 `ser_json_timedelta='float'` 下内含 timedelta 的标准库 dataclass（C08）；
- 类实例作默认值 12 例：标准库 dataclass、pydantic dataclass、BaseModel、TypedDict 实例的不同写法；
- IP 字符串默认值 1 例（A14）。

在这 49 例上，`fallback` 的完整 schema 与警告列表都与 base 逐项相等。gold 有 9 例在这里抛出 `PydanticUserError(type-adapter-config-unused)`，gold_catch 有 9 例把 default 丢掉并发出警告，上游式与 base 全部相等。

**base 原本发警告的用例，行为有三种走向。** 这类用例共 39 个：

- 23 例 `fallback` 给出了 default；
- 14 例仍发警告，文案与 base 相同；
- 2 例从“警告”变成抛异常，见第三节反例 1、3。

**公开测试结果（我的开发态运行，均已应用原 test_patch）：**

| 测试文件 | base | gold、`fallback`、上游式 |
| --- | --- | --- |
| `tests/test_json_schema.py` | 2 failed / 380 passed / 1 skipped / 1 xfailed | 382 passed / 1 skipped / 1 xfailed |
| `tests/test_dataclasses.py` | 199 passed / 11 skipped | 同 base |
| `tests/test_networks.py` | 232 passed / 1 skipped / 1 xfailed | 同 base |
| `tests/test_types.py` | 811 passed / 3 skipped / 1 xfailed | 同 base |

`test_json_schema.py` 中，gold、`fallback`、上游式的 F2P 为 2/2，P2P 为 367/367；base 的 F2P 为 0/2，P2P 为 367/367。

**全量 `tests/`（base 对比 `fallback`，共 5011 个测试 ID）：** 两边唯一的差异是 2 个 F2P。`test_docs.py` 在两边各有 513 个失败，原因都是镜像里没有 `ruff` 可执行文件，属于环境问题。我改用一个直接返回 0 的 stub `ruff` 跳过 lint 步骤后，base、gold、`fallback` 的 `test_docs.py` 都是 506 passed / 29 skipped，结果相同。

### 3. 是否是合理的上游式修复：是，但设计与上游最终写法不同

我比对了上游各版本的 `encode_default`：

- 上游 2.7.0 的 `encode_default` 与本题 gold 逐字相同；
- 2.7.1 只改了一处，就是上面那行 `_type_has_config` 分流。HISTORY 记为 "Fix `model_json_schema` with config types (#9287)"，并新增了 `test_pydantic_types_as_default_values`，其中 `builtin-dataclass` 参数就是本题 gold 的回归（2.7.1 sdist `tests/test_json_schema.py:6036-6138`）；
- 2.7.1 到 2.11.0 一直沿用这一写法。

两种设计的差别：

| 方面 | 上游最终写法 | `fallback` |
| --- | --- | --- |
| 顺序 | 先对非配置类型建 `TypeAdapter`，并传入 config | 先走 base 的通用推断，失败后才借用该值所属类型的 pydantic 序列化器 |
| 与 base 的一致性 | 在我测的用例上也与 base 一致 | 由写法本身保证与 base 一致 |
| 回退分支是否遵守 `ser_json_*` | 遵守 | 不遵守 |
| 标准库 dataclass 内含 IP 的默认值 | 仍发警告 | 能编码 |

`fallback` 没有吞错、提前返回、硬编码之类的退化特征：失败时会抛回原错误，由 `default_schema` 照旧发出警告。

**用上游自己的回归测试直接检验。** 我把 2.7.1 为这个回归补的 `test_pydantic_types_as_default_values`（2.7.1 sdist `tests/test_json_schema.py:6036-6138`，4 个参数）原样移植到独立测试文件，只补了 import，然后在各变体上运行：

| 变体 | 结果 |
| --- | --- |
| base、`fallback`、上游式 | 4/4 通过 |
| gold、gold_catch | `[builtin-dataclass]` 失败，其余 3 项通过 |

这个结果与修订测试 v1 中 dataclass 检查那一部分的判定完全一致：gold 与 gold_catch 失败，`fallback` 与上游式通过。base 在上游测试上通过，但在 v1 上得 0，原因是 v1 前面的 IP 断言已经失败。

## 二、作者主张逐条核对

行号指作者 `result.md`。

| # | 主张 | 判断 | 依据 |
| --- | --- | --- | --- |
| 1 | L5：已找到替代正对照，修法明确，建议转第2类 | 同意 | 第一节三问；无阻断项 |
| 2 | L7、L55-60：`fallback` 在原测试下得 1；noop 0，gold 1，gold_catch 1 | 属实 | `evidence/formal/ledger_*.jsonl`：`fallback` 的 reward 1.0，F2P 2/2，`p2p_fail` 0/367，`reference_missing_count` 0，parsed 376，candidate sha `1e5dbc5c…` 与补丁一致。我独立解析 4 份 eval log，369 个参考 ID 各出现一次，状态与表一致。我的开发态运行同样是 2/2、367/367 |
| 3 | L8：保持标准 dataclass 默认值的原有行为；18 类行为矩阵与 base 一致或优于 base | 在作者的 18 类之内属实，扩大范围后需要收窄 | 作者 18 类的原始输出（`semantic_v1/*/b1_behavior.out`）与表一致；我逐类独立复现，包括 PurePosixPath：base 缺 default，gold 与 `fallback` 为 `"/a/b"`。但在我的 91 例中，`fallback` 并非处处“一致或优于”：反例 1 从警告变为异常；反例 2 新给出的 default 不遵守 `ser_json_*` |
| 4 | L9、L78-85：修订版 v1 中 noop 0，gold 0，`fallback` 1，gold_catch 0 | 属实 | `formal_revised_v1/ledger_*.jsonl` 与表一致。失败位置：gold 和 gold_catch 在 `tests/test_json_schema.py:6044`，即 dataclass 检查那一行；gold 抛 `PydanticUserError`，gold_catch 以 `PydanticJsonSchemaWarning` 失败。noop 在 `:6032`，即 IP 断言。4 份修订 eval_script 的 sha256 相同（`e462d30a…`）。我用 `revised_test_v1.patch` 做开发态复跑：base 0，gold 0，`fallback` 1，gold_catch 0，**上游式 1**，P2P 均为 367/367 |
| 5 | L10、L93：实施依赖 D6，正式入库需固定 wheel 清单 | 同意 | 标准 §5“模板外”与 §9 D6 |
| 6 | L15：题面要求 | 属实 | `public_bundles_v0.jsonl` 本题的 problem_statement |
| 7 | L17：gold 回归的机制 | 属实 | gold 对标准库 dataclass 实例建 `TypeAdapter(type(dft), config={})`，触发 `type_adapter.py:195-204` 的禁用条件，而 gold 只捕获 `PydanticSchemaGenerationError`。矩阵中 D01、D02、D06-D09、D11、D12 以及 C08 均抛此错 |
| 8 | L17：公开文档支持混用，所以这是“有文档的常用行为” | 结论成立，依据需收窄 | `docs/concepts/dataclasses.md:242-300` 只演示了标准库 dataclass 作字段类型，默认值是 `None`，没有演示“dataclass 实例作默认值”在 schema 中的编码。保护这一行为的更直接依据是：base 本来就支持；`encode_default` 的职责是编码字段默认值；上游 2.7.1 把同一问题当回归修复并补了测试（#9287）。修订测试里的注释 "documented BaseModel + stdlib dataclass usage" 也有同样问题 |
| 9 | L23：原本能编码的默认值不经过新代码 | 属实 | `fallback.patch:23-28` 先原样调用 `to_jsonable_python`；49 个 base 正常用例的完整 schema 与 base 逐项相等 |
| 10 | L24：不传 config，避开 config 冲突 | 属实，但作者没有写出副作用 | 回退分支里 `ser_json_timedelta`、`ser_json_bytes`、`ser_json_inf_nan` 都不生效，见反例 2 |
| 11 | L25：导出也失败时抛回原错误，照旧警告 | 部分属实 | 只对 `fallback.patch:36` 捕获的三类异常成立：`PydanticSchemaGenerationError` 是 `PydanticUserError` 的子类，实际等于全部 `PydanticUserError` 加上序列化错误。其它异常会直接穿出 `default_schema`（后者只接 `PydanticSerializationError`），见反例 1、3 |
| 12 | L29：原镜像身份 | 属实 | `docker image inspect`：Id `5a05759a…`，RepoDigest `@sha256:36a21435…dc31` |
| 13 | L45：`test_json_schema.py` 380 项，另四个文件共 673 项，三个版本全部通过 | 属实，措辞需补充 | `semantic_v1/*/b2_*.out`、`b3_*.out`：380 passed、1 skipped、1 xfailed；673 passed、68 skipped、1 xfailed，三个版本相同。“项”指 passed 数。b2 运行时没有应用 test_patch，不含 F2P 两项。作者没有跑 `test_types.py`，我补跑了，结果相同 |
| 14 | L49-53：等效派生镜像，Dockerfile 文本相同，原 8 个 wheel 的清单未上传，不是逐字节重建 | 说明诚实，已核实能核的部分 | 配方文本与 09-19 原构建脚本 `rh2/experiments/env_recipe_repair_20260919/run_pydantic.py:20` 逐字相同（另见 `rebuild_wheel_layer.py:14-15`）。派生镜像 `8606971e…` 保留了 base 的 13 层，只加 1 层；镜像内 8 个 wheel 的 sha256 与字节数和 `derived_image.json` 一致；环境变量含 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS`。本仓库里没有原清单，preprobe 的 `evidence_audit.json:2040` 只记了布尔值 `wheel_log_matches_8_public_manifest`，所以“与原版本等效”无法逐项核对，作者已如实写明。8 份 ledger 都显示 `RH2_OBS_PKG_VERSION=2.7.0a1`，导入路径是 `/testbed/pydantic/__init__.py`，UID 54322，`deny_all` |
| 15 | L62：参考缺席 0，安装失败 0，清理成功，准备阶段约 16–18 秒 | 前三项属实，秒数有小误差 | 原材料 4 份 ledger 的 `grader_trusted_setup` 为 18.0、15.9、10.2（gold_catch）、15.8 秒；修订版为 10.0–17.4 秒 |
| 16 | L62：noop 与 gold 的结果与 09-29 CPU 批次一致 | 属实 | preprobe `result.md` 表：noop 0，F2P 0/2，P2P 367/367；gold 1，F2P 2/2，P2P 367/367 |
| 17 | L66-67：gold_catch 说明只捕获异常的“窄修”不足以恢复公开行为；它在原材料下也得 1 | 属实 | 原材料 ledger reward 1.0；我的矩阵中，它在 9 个 base 正常用例上丢掉 default 并发出警告 |
| 18 | L71-76：修订测试 v1 的内容，测试 ID 不变 | 属实 | sha256 `73d97a37…` 与 `materials_revised_v1.json` 一致；原 test_patch `762cd93f…` 与 bundle 一致。修订版日志 parsed 376，369 个参考 ID 各出现一次 |
| 19 | 修订断言的依据 | 充分 | 依据见第 8 行的收窄说明 |
| 20 | 修订断言的宽严 | 合适 | 同时接受 `fallback` 与上游式；拒绝 gold（抛错）与 gold_catch（丢 default）。v1 中 dataclass 检查那一部分，在 gold、gold_catch、`fallback`、上游式上的判定与上游 2.7.1 回归测试完全一致（见第一节第 3 问）。只断言 `properties.point.default == {'x': 1}`，不锁 schema 结构；不要求 `fallback` 独有的行为（dataclass 内的 IP、容器内的 IP）。检查放在 F2P 测试体内会降低诊断粒度，但 reward 语义正确；拆成独立 P2P 需要 D6，与作者 L75 的说明一致 |
| 21 | L108：`List[IPvAnyAddress]` 等容器内的 IP，gold 和 `fallback` 都没修，属 T3 | 属实，同意 | 矩阵 E07（list）、E08（dict）、E10（tuple）、E15（deque）在五个变体上都仍发警告；上游 2.7.1 到 2.11 的写法同样不处理 |

## 三、我发现的反例与新问题

以下均为实测结果。除特别注明外，“base”指原镜像不打补丁。

**反例 1：回退分支漏捕异常，警告变成硬错误。这是 `fallback` 独有的问题，属边缘输入。**

构造方式：在函数内定义一个标准库 dataclass，它带有无法解析的前向引用 `other: 'Optional[LocalThing]' = None`（`LocalThing` 是局部类），同时内容里有一个 IP；把它的实例作为 `Any` 字段的默认值。

| 变体 | 结果 |
| --- | --- |
| base | 发警告，不给 default |
| 上游式 | 同 base |
| gold | 抛 `PydanticUserError` |
| `fallback` | 抛 `PydanticUndefinedAnnotation: name 'LocalThing' is not defined` |

原因：`PydanticUndefinedAnnotation` 是 `NameError` 的子类（`errors.py:91`），不在 `fallback.patch:36` 的捕获元组里。

**反例 2：回退分支不遵守 `ser_json_*`，新给出的 default 与模型自身的 JSON 序列化不一致。这是 `fallback` 独有的问题，属边缘输入。**

| 用例 | base | gold / 上游式 | `fallback` | `model_dump_json` 实际输出 |
| --- | --- | --- | --- | --- |
| `Deque[timedelta]`，`ser_json_timedelta='float'` | 警告，无 default | `[90.0]` | `["PT90S"]` | `[90.0]` |
| `Deque[bytes]`，`ser_json_bytes='base64'` | 警告，无 default | `["YWJj"]` | `["abc"]` | `["YWJj"]` |
| `Deque[float]` 含 inf，`ser_json_inf_nan='constants'` | 警告，无 default | `[Infinity]` | `[null]` | `[Infinity]` |
| 标准库 dataclass 同时含 IP 与 timedelta，`ser_json_timedelta='float'` | 警告，无 default | gold 抛错；上游式发警告 | `{"ip": "1.2.3.4", "td": "PT90S"}` | `{"ip":"1.2.3.4","td":90.0}` |

这些都不是 base 原本就有的输出，所以不算破坏旧行为。但它说明 `fallback` 在配置这一维度上不如上游写法完整。

**反例 3：自定义 `__get_pydantic_core_schema__` 抛出非 pydantic 异常会穿出。这是所有基于 TypeAdapter 的修法共有的问题。** 在 base 上它只是警告；gold、上游式、`fallback`、gold_catch 都抛 `ValueError`。它不能用来区分 `fallback` 与 gold。

**观察 4：几项共有的行为变化，不构成对 `fallback` 的反对理由。**

- 带 `__get_validators__` 的旧式类型，在所有修法下都多出一条 `PydanticDeprecatedSince20` 警告；
- `SecretStr`、`SecretBytes` 的默认值：base 发警告，所有修法都改成 `"**********"`；
- `Deque[int]` 的默认值：base 发警告，所有修法都给出 `[1, 2]`。

**观察 5：`fallback` 比上游多编码了一类输入，修订测试不应要求这一点。**

内含 IP 的标准库 dataclass 默认值：`fallback` 能编码，上游式仍发警告，gold 抛错。如果修订测试要求这一点，上游式修法就会被判 0。v1 没有这样要求，这是对的。

**更正我初判中的一个静态疑点：** 我曾推测 gold 会把 inf/nan 默认值改成 `None`。实测中，所有变体都保留 `Infinity`/`NaN`，与 base 一致，这个疑点已排除。

## 四、阻断项与非阻断建议

**阻断项：无。** 就 D4 而言，`fallback` 满足题面要求，不破坏我所测的常用行为，属于合理修法，并且修订断言没有贴合它的特有设计。

**非阻断建议：**

1. **收窄 `result.md` L17 与修订测试注释的依据表述。** 文档演示的是“标准库 dataclass 作字段类型”；“实例作默认值时 schema 正常编码”的依据是 base 行为加上 `encode_default` 的职责。上游 2.7.1 #9287 及其测试 `test_pydantic_types_as_default_values[builtin-dataclass]` 可以作为佐证。
2. **修正 L25 的描述，并登记 `fallback` 的已知缺口。**
   - 只有捕获元组内的异常会退回警告；
   - 反例 1 是 `fallback` 独有的异常穿出；反例 3 各修法共有；
   - 反例 2：回退分支不遵守 `ser_json_*`。
   
   这些缺口只影响边缘输入，不影响它作本题正对照；但若以后有人拿它当参考解，或据它推其它输入的期望值，就需要知道这些缺口。
3. **把 L8 的“18 类一致或优于 base”限定为“在所测 18 类中”。**
4. **D6 正式复验时，把上游式变体作为第二个正对照一起跑。** 构造方法见附录，我的开发态结果是 1。这能直接说明修订断言不是按 `fallback` 的设计量身定做的。

   如果 D6 允许新增参考，可把 dataclass 检查拆成独立的 P2P 测试，并照上游测试补上 pydantic dataclass、TypedDict、BaseModel 实例默认值作护栏。移植后的上游测试 4 个参数中，base、`fallback`、上游式全部通过，gold 只在标准库 dataclass 一项上失败。还可以补一个依赖配置的 dataclass 默认值（矩阵 C08：`ser_json_timedelta='float'` 下 base 为 `{"td": 90.0}`，`fallback` 与上游式相同，gold 抛错，gold_catch 丢 default）。
5. **小处措辞。**
   - L45：“380 项”“673 项”是 passed 数；b2 运行时没有带 test_patch；
   - L62：准备阶段的实际范围是 10.0–18.0 秒。
6. 修订版若要进训练，还需要 §4 第 3 步的退化探测，以及 §2 的其它正面证据。这不在本复核范围内，也未做。

## 五、未查

- 未跑正式评分（按要求）。正式评分结论依据作者的 ledger 与 eval log，以及我的开发态 pytest。
- 我的运行都用原镜像（`5a05759a…`），身份是 root，网络为 `--network none`。没有在 grader profile（UID 54322、2CPU/4GiB、deny_all）或作者的等效派生镜像（`8606971e…`）上复跑测试。对派生镜像，只核了身份、层结构和 wheel 字节。
- 09-19 原版的 8 个 wheel 清单：本仓库中没有，未能核对。
- `test_docs.py` 是在 stub `ruff` 下跑的，只核了示例能否运行，不代表 lint 通过。
- 未测 Python 3.8.19 以外的解释器版本，也未测 pydantic-core 2.16.3 以外的版本。
- `evidence_manifest.json` 中已归档的 97 个文件，sha256 全部相符；声明未归档的 51 个文件（artifacts、prepared、private）未查。
- 真实模型候选、actor 开发条件未查（作者也列为剩余项）。

## 附录：复核用的构造（可复现）

- **上游式变体**：先 `git apply` gold，再把 `encode_default` 中 `from .type_adapter import TypeAdapter` 改为 `from .type_adapter import TypeAdapter, _type_has_config`，把 `if hasattr(dft, '__pydantic_serializer__')` 改为 `if _type_has_config(type(dft))`。改后与上游 2.7.1 wheel 中的 `encode_default` 逐字相同。
- **上游参照来源（PyPI 公开包）**：
  - pydantic-2.7.0 wheel，sha256 `9dee74a2…`；
  - pydantic-2.7.1 wheel，sha256 `e029badc…`；
  - pydantic-2.7.1 sdist，sha256 `e9dbb5ea…`；
  - 另有 2.7.4、2.8.0、2.9.0、2.10.0、2.11.0 的 wheel。
- **矩阵分组**（每例都用 `type('Model', (BaseModel,), ...)` 构造模型，调用 `model_json_schema()`，记录完整 schema、异常类型/code 与警告；再在 `warnings.simplefilter('error')` 下重跑一遍，结论不变）：

  | 组 | 用例数 | 内容 |
  | --- | --- | --- |
  | A | 14 | IP 家族 |
  | B | 32 | 普通默认值 |
  | C | 11 | `ser_json_*` 相关 |
  | D | 12 | 类实例作默认值 |
  | E | 17 | 警告路径 |
  | F | 5 | 专找反例 |

- **上游回归测试移植**：把 2.7.1 sdist `tests/test_json_schema.py:6036-6138` 原样放进独立测试文件，补上 `dataclasses`、`pytest`、`TypedDict`、`pydantic`、`BaseModel`、`ConfigDict` 的 import，在每个变体的一次性容器里运行 pytest。
- **修订测试开发态复跑**：先 `git apply` 候选补丁与 `rh2/experiments/category3_cloud_20260929/pydantic9066/revised_test_v1.patch`，再运行 `python -m pytest -rA --tb=short -vv -o console_output_style=classic --no-header -p no:cacheprovider tests/test_json_schema.py`，按 bundle 的 F2P/P2P 参考 ID 计分。
