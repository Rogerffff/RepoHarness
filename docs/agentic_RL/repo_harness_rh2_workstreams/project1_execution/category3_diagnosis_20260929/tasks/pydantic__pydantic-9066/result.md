# pydantic__pydantic-9066：第3类诊断结果

2026-09-29 / Claude（云端，第3类负责人）。原分类：第3类“参考修复不可靠，缺正确对照”。已知 gold 修好 IP 默认值后，标准库 dataclass 默认实例的 schema 生成会报 `type-adapter-config-unused`。09-29 CPU 批次已实测并独立复核（S1／T2），缺少的是一份兼顾两类默认值的正对照。

**结论：已找到替代正对照，修法明确，建议转第2类。**

- 替代实现 `fallback` 在原测试下得 1。
- 它保持标准 dataclass 默认值原有行为；18 类默认值的行为矩阵与 base 一致或优于 base。
- 修订版测试 v1 补上 dataclass 默认值回归检查后，gold 为 0，`fallback` 为 1。
- 实施依赖 D6 的“测试补丁替换”切片。
- 替代正对照的独立核实**尚在进行**，见 §7。

## 1．公开要求与已知 gold 问题

题面：`IPvAnyAddress` 字段以 `IPv4Address("127.0.0.1")` 为默认值时，`model_json_schema()` 报出 `non-serializable-default` 警告，并丢掉 default。期望 schema 中包含可序列化的 default。

gold 为每个没有 `__pydantic_serializer__` 的默认值新建 `TypeAdapter(type(dft), config=...)`。对标准 dataclass，传 config 会触发 `PydanticUserError`，而 gold 没有捕获它，导致整个 schema 生成失败。公开文档 `docs/concepts/dataclasses.md` 支持“标准库 dataclass 与 BaseModel 混用”，所以这是有文档的常用行为（09-29 CPU 批次已证，本页不重复）。

## 2．替代正对照 `fallback`

[`fallback.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic9066/fallback.patch)，sha256 `1e5dbc5c…`，只改 `pydantic/json_schema.py` 的 `encode_default`：

1. 先按原逻辑调用 `to_jsonable_python`。**原本能编码的默认值不经过新代码。**
2. 只有它抛出 `PydanticSerializationError` 时，才对该值自身类型建 `TypeAdapter`，并且**不传 config**，以 JSON 模式导出。这样可以避开 BaseModel／dataclass／TypedDict 的 config 冲突。
3. 导出如果也失败，就抛回**原来的**序列化错误，`default_schema` 照旧警告并排除该默认值。

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

公开测试 `tests/test_json_schema.py`（380 项）以及 `test_dataclasses.py`、`test_networks.py`、`test_types_typeddict.py`、`test_main.py`（共 673 项）在三个版本下全部通过。

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

noop 与 gold 结果与 09-29 CPU 批次一致。所有评分参考缺席 0，安装失败 0，清理成功；准备阶段约 16–18 秒（09-29 批次为约 296 秒，差别来自宿主机）。

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
| `gold_catch_user_error` | 0 | dataclass 默认值被警告并排除（测试把该警告视为错误） |

**交接给第2类**：

1. 独立核实 `fallback` 可作替代正对照，见 §7；
2. 经 D6 的测试补丁替换或新增 P2P 能力形成正式版本；
3. 复验上表；
4. Codex 复核；
5. 正式评分所用派生镜像为等效重建，正式入库时应固定一份 wheel 清单并登记来源。

## 6．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练 | 留出 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | conditional（沿用 09-29 条件） | 否 | 否 |
| 修订版 | 经 D6 入库并验收后重新评估 | | | |

## 7．独立复核

待进行，重点是核实 `fallback` 是否满足全部公开要求且不破坏相关旧行为。

## 8．未做与剩余事项

- `List[IPvAnyAddress]` 这类容器内 IP 默认值，gold 和 `fallback` 都没有修。题面没有提到这种情况，属于 T3 范围说明。
- 真实 actor 开发条件未验；没有模型求解证据。

## 9．版本与证据

- 代码与运行环境见 [环境说明](../../environment.md)。
- 等效派生镜像配方：`rh2/experiments/category3_cloud_20260929/rebuild_wheel_layer.py`。
- 原始证据：[evidence/](evidence/)
  - `formal/`：原材料评分；
  - `formal_revised_v1/`：修订版评分；
  - `semantic_v1/`：私有矩阵；
  - `derived_image.json`：wheel 清单与身份；
  - `evidence_manifest.json`：全部文件的 SHA256。
