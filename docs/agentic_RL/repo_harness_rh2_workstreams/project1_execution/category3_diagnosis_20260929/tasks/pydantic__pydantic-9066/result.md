# pydantic__pydantic-9066：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“参考修复不可靠，缺正确对照”。已知 gold 修好 IP 默认值后，标准库 dataclass 默认实例的 schema 生成会报 `type-adapter-config-unused`。09-29 CPU 批次已实测并独立复核（S1／T2），缺少的是一份兼顾两类默认值的正对照。

**结论：已找到替代正对照，修法明确，建议转第2类。**

- 替代实现 `fallback` 在原测试下得 1。
- 它保持标准 dataclass 默认值原有行为；在所测 18 类默认值中，与 base 一致或优于 base。复核扩大到 91 例后，发现 `fallback` 有两处边缘缺口，见 §8。
- 修订版测试 v1 补上 dataclass 默认值回归检查后，gold 为 0，`fallback` 为 1。
- 按上游 2.7.1 写法构造的第二正对照 `upstream271` 在原材料和修订版 v1 上也都得 1，说明修订断言不是照 `fallback` 的设计量身定做的。
- 实施依赖 D6 的“测试补丁替换”切片。
- **独立复核已完成**：同意用 `fallback` 作替代正对照，无阻断项，见 §7。

## 1．公开要求与已知 gold 问题

题面：`IPvAnyAddress` 字段以 `IPv4Address("127.0.0.1")` 为默认值时，`model_json_schema()` 报出 `non-serializable-default` 警告，并丢掉 default。期望 schema 中包含可序列化的 default。

gold 为每个没有 `__pydantic_serializer__` 的默认值新建 `TypeAdapter(type(dft), config=...)`。对标准 dataclass，传 config 会触发 `PydanticUserError`，而 gold 没有捕获它，导致整个 schema 生成失败（09-29 CPU 批次已证，本页不重复）。

这一行为需要保护，依据如下（按复核意见收窄）：
- 公开文档 `docs/concepts/dataclasses.md:242-300` 只演示了标准库 dataclass 作**字段类型**，没有演示 dataclass **实例**作默认值；
- 直接依据是：base 本来就支持这一用法，而 `encode_default` 的职责就是编码字段默认值；
- 上游在 2.7.1 把同一问题当作回归修复（#9287），并新增 `test_pydantic_types_as_default_values[builtin-dataclass]`，可作佐证。

## 2．替代正对照 `fallback`

[`fallback.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic9066/fallback.patch)，sha256 `1e5dbc5c…`，只改 `pydantic/json_schema.py` 的 `encode_default`：

1. 先按原逻辑调用 `to_jsonable_python`。**原本能编码的默认值不经过新代码。**
2. 只有它抛出 `PydanticSerializationError` 时，才对该值自身类型建 `TypeAdapter`，并且**不传 config**，以 JSON 模式导出。这样可以避开 BaseModel／dataclass／TypedDict 的 config 冲突。
3. 导出如果也失败，就抛回**原来的**序列化错误，`default_schema` 照旧警告并排除该默认值。只有捕获元组内的三类异常（`PydanticSchemaGenerationError`、`PydanticUserError`、`PydanticSerializationError`）会这样退回警告，其它异常会穿出，见 §8。

## 3．实测结果

镜像 `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9066`，摘要 `sha256:36a21435…dc31`，image ID `5a05759a…`，与记录一致。

**（1）私有行为矩阵**：root、断网；每项都用 `model_json_schema()` 取 `properties.field.default`，并统计警告条数。

| 默认值 | base | gold | `fallback` |
| --- | --- | --- | --- |
| 题面：`IPvAnyAddress` ＋ `IPv4Address` | 缺失 default，1 条警告 | `"127.0.0.1"` | `"127.0.0.1"` |
| IPv6 `::1`、`IPv4Address` 字段、`IPv4Network` | 缺失 default，1 条警告 | 正确 | 正确 |
| `PurePosixPath` | 缺失 default，1 条警告 | `"/a/b"` | `"/a/b"` |
| **标准库 dataclass `StdDC(1)`** | `{"x": 1}` | **`PydanticUserError`（type-adapter-config-unused）** | `{"x": 1}` |
| 标准 dataclass ＋ 模型 config | `{"x": 5}` | **同上报错** | `{"x": 5}` |
| pydantic dataclass、BaseModel 实例、TypedDict、Enum、datetime、Decimal、UUID | 正确 | 同 base | 同 base |
| `timedelta`（`ser_json_timedelta=float`）、`bytes`（`ser_json_bytes=base64`） | 3600.0／`"aGk="` | 同 base | 同 base |
| 任意不可序列化对象 | 缺失 default，1 条警告 | 同 base | 同 base |
| `List[IPvAnyAddress]` 默认值 | 缺失 default，1 条警告 | 同 base（未修） | 同 base（未修） |

公开测试在三个版本下没有失败：`tests/test_json_schema.py` 为 380 passed，`test_dataclasses.py`、`test_networks.py`、`test_types_typeddict.py`、`test_main.py` 合计 673 passed。这次运行没有应用 test_patch。

**（2）原材料正式评分**：F2P 2 项，P2P 367 项。

使用 09-19 的 pydantic_v1 安装命令修订（`pydantic_v1/pydantic__pydantic-9066.json`）和云端**等效**重建的离线 wheel 层：

- Dockerfile 文本与原配方相同；
- 原 8 个 wheel 的清单未上传，这里改用 Python 3.8 兼容的固定版本：hatchling 1.21.1、hatch-fancy-pypi-readme 24.1.0、packaging 23.2、pathspec 0.11.2、pluggy 1.3.0、trove-classifiers 2024.3.3、tomli 2.0.1、editables 0.5；
- 摘要见 [evidence/derived_image.json](evidence/derived_image.json)。**这不是 09-19 原版的逐字节重建。**

| 候选 | reward | F2P | P2P |
| --- | --- | --- | --- |
| noop | 0 | 0/2 | 367/367 |
| gold | 1 | 2/2 | 367/367 |
| `fallback` | **1** | 2/2 | 367/367 |
| `gold_catch_user_error`：在 gold 上把配置冲突也当“无法编码”，dataclass 默认值因此被警告并排除 | 1 | 2/2 | 367/367 |
| `upstream271`：gold 加上游 2.7.1 的一处改动，按 `_type_has_config(type(dft))` 分流 | 1 | 2/2 | 367/367 |

noop 与 gold 结果与 09-29 CPU 批次一致。所有评分参考缺席 0，安装失败 0，清理成功；准备阶段为 10.0–18.0 秒（09-29 批次为约 296 秒，差别来自宿主机）。

## 4．判定

- gold 的回归（S1／T2，§4 第 4 步）沿用 09-29 结论。本次补齐了此前缺少的**替代正对照**。
- `gold_catch_user_error` 说明，仅把异常捕获掉的“窄修”不足以恢复公开行为。它在原材料下也得 1，属于同一覆盖缺口。

## 5．修法（交第2类）

**R-c 修订版测试草案 v1**：[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic9066/revised_test_v1.patch)，sha256 `73d97a37…`；原 test_patch 的 sha256 为 `762cd93f…`。

- 在 F2P `test_default_value_encoding` 的测试体内，追加一个检查：标准库 dataclass 实例作 BaseModel 字段默认值时，schema 中 `default == {'x': 1}`。
- 两个 IP 参数用例都会执行这项检查，所以测试编号不变。
- 正式版本更宜把它拆成单独的 P2P 测试，这需要 D6 支持新增参考。
- 原有的“不可序列化默认值警告”护栏，即 P2P `test_non_serializable_default` 等，保持不变。

**修订版诊断评分**：同时使用 `--recipe` 和 `--materials`，grader 后缀 `+c3-pyd9066-dataclass-default-v1`。

| 候选 | 修订版 reward | 失败位置 |
| --- | --- | --- |
| noop | 0 | IP 默认值无法序列化 |
| gold | **0** | dataclass 默认值处 `PydanticUserError`，按 D4 记录 gold 失败 |
| `fallback`（正对照） | **1** | |
| `upstream271`（第二正对照） | **1** | |
| `gold_catch_user_error` | 0 | dataclass 默认值被警告并排除（测试把该警告视为错误） |

`upstream271`：[`upstream271.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic9066/upstream271.patch)，sha256 `8cb154cf…`。构造见 `_edit_upstream271.py`，来自复核附录。改后的 `encode_default` 与上游 2.7.1 wheel 逐字相同（复核核对）。它与 `fallback` 设计不同：前者按类型是否带 config 分流，后者在序列化失败时才回退。两者都得 1。

**交接给第2类**：

1. `fallback` 可作替代正对照，已由独立复核核实，见 §7；
2. 经 D6 的测试补丁替换或新增 P2P 能力形成正式版本；
3. 复验上表，`upstream271` 作为第二正对照一起跑；
4. 落地时把修订测试注释 “documented BaseModel + stdlib dataclass usage” 改成不声称有文档的写法。这只改注释，本页的评分证据仍对应 `73d97a37…` 版；
5. 如果 D6 支持新增参考，建议把 dataclass 检查拆成独立 P2P 测试，并按上游 2.7.1 测试补上 pydantic dataclass、TypedDict、BaseModel 实例默认值作护栏；
6. Codex 复核；
7. 正式评分所用派生镜像为等效重建，正式入库时应固定一份 wheel 清单并登记来源。

## 6．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练 | 留出 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否（09-30 按 Codex 复核更正：原版有已证的 S1 未修，不能靠事后审计进入普通能力比较；特殊诊断试解另列调查目的，不混用原分数） | 否 | 否 |
| 修订版 | 经 D6 入库并验收后重新评估 | | | |

## 7．独立复核

复核者先封存初判 [review_initial.md](review_initial.md)，结论见 [review.md](review.md)。

- **总判断**：`fallback` 可以作替代正对照，同意本页处置，**无阻断项**。
- **D4 三问**：
  - 满足题面：13 例 IP 默认值都正确；
  - 不破坏旧行为：base 能编码的 49 例中，`fallback` 的完整 schema 与警告都和 base 逐项相等；全量 `tests/`（5011 个 ID）只有 2 个 F2P 不同；
  - 是合理修法：上游 2.7.1 为同一回归补的测试，`fallback` 和上游式都通过。
- **复核核对**：原材料与修订版的正式评分，与 ledger 和复核者独立解析的 eval log 一致。
- **已处理的非阻断建议**：
  - 收窄文档依据（§1）；
  - 写明哪些异常会退回警告（§2）；
  - 把“一致或优于 base”限定在所测范围（开头）；
  - 修正 passed 数与准备阶段耗时的措辞（§3）；
  - 加入上游式第二正对照，已跑正式链：原材料 1、修订版 1。
- **未处理**：修订测试注释的措辞，交第2类落地时一并改，见 §5 第 4 条。

## 8．未做与剩余事项

- `List[IPvAnyAddress]` 这类容器内 IP 默认值，gold 和 `fallback` 都没有修。题面没有提到这种情况，属于 T3 范围说明。
- **`fallback` 的已知缺口**（复核发现，都是边缘输入，不影响它作本题正对照）。如果以后有人拿它当参考解，或据它推断其它输入的期望值，需要知道这些缺口：
  1. **独有的异常穿出**：局部定义、带无法解析的前向引用、且内含 IP 的标准库 dataclass 作默认值时，抛 `PydanticUndefinedAnnotation`；base 和上游式只发警告；
  2. **回退分支不遵守 `ser_json_*`**：例如 `Deque[timedelta]` 配 `ser_json_timedelta='float'`，`fallback` 给出 `["PT90S"]`，模型实际序列化是 `[90.0]`。这类输入上 base 本来就不给 default；
  3. **各修法共有**：自定义 `__get_pydantic_core_schema__` 抛 `ValueError` 时，gold、上游式、`fallback` 都会让它穿出，不能用来区分修法。
- 修订版若要进训练，还需要 §4 第 3 步的退化探测，以及 §2 的其它正面证据；本页未做。
- 真实 actor 开发条件未验；没有模型求解证据。

## 9．版本与证据

- 代码与运行环境见 [环境说明](../../environment.md)。
- 等效派生镜像配方：`rh2/experiments/category3_cloud_20260929/rebuild_wheel_layer.py`。
- 原始证据：[evidence/](evidence/)
  - `formal/`：原材料评分，含 `upstream271`；
  - `formal_revised_v1/`：修订版评分，含 `upstream271`；
  - `semantic_v1/`：私有矩阵；
  - `derived_image.json`：wheel 清单与身份；
  - `evidence_manifest.json`：全部文件的 SHA256。
