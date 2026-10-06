# pydantic__pydantic-8567：第3类诊断结果

2026-09-29 / Claude（云端，第3类第二批主审作者）。原分类：第3类“参考修复不可靠，缺正确对照”。09-29 CPU 批次已实测并复核：gold 修好了题面两种顺序的序列化，但让“普通类 + `PlainValidator`”在类定义阶段报错；原测试只查 `isinstance(str)`，不查精确值和 JSON（S1／T2a）。那时缺的是一份能保住这项能力的正对照。

> **当前状态（09-30 更新：已转第2类，采用 v4）**
>
> - **首轮独立复核**（[review.md](review.md)）核实两份替代正对照 `upstream261`、`c3_reorder`；唯一阻断 `rv_pv_first` 由 v3 处理，v3 正式诊断评分 17 次符合当时预期。
> - **v3 聚焦复核**（[review_v3.md](review_v3.md)）：部分同意，阻断 3 项。
>   - **B1（S1）**：v3 只拒掉会运行 PV 左侧验证器的写法，没拒掉把 PV 左侧约束挪到外层的写法（`bad_nonvalidators_after_pv` 等 3 个，v3 下为 1）；
>   - **B2**：serializer 与 PV 之间夹有其它元数据时 serializer 不生效，或中间的验证器被挪到外层生效（`c3_serpass` 与 3 个同类候选）。作者原记 T3，按“已知错误不因少见放过”改判；
>   - **B3**：PV 两侧都有 serializer 时改用内侧那个，相对 base 回归（`rv_ser_to_end`、`bad_rewrap_noinfo`）。
>
>   B1 与首轮阻断 `rv_pv_first` 属同一状态边界（PV 左侧元数据的处理），连续两轮出现新阻断，按协作协议 §5 熔断：不再增量修补，采用复核者按根因写好、私有验证过的 `t_v4` 作 v4（逐字相同），由 Codex 确认，不再开 Claude 复核轮次。
> - **v4 正式诊断评分 31 次与复核停止条件逐项一致**（§4 v4 小节）：两份正对照、`rv_condwrap` 与复核者 5 个合理实现为 1；noop、gold（只在未知类型处失败，D4）与全部 22 个已知错误候选为 0，reward 与失败行号全部吻合。
> - **已按 Codex 09-30 复核转第2类**，交接见[交接清单](../../handover_to_category2_20260930.md)。转第2类不等于最终验收。

**结论：问题和修法已明确，转第2类（采用 v4）。** 两份替代正对照已由独立复核核实。

- **gold 的回归已复现，上游有佐证。** 普通类 `Unsupported` 加 `PlainValidator`，在默认配置下 base 能建类、能验证；gold 在类定义阶段抛 `PydanticSchemaGenerationError`（`schema-for-unknown-type`）。上游在下一个补丁版 2.6.1 修了同一问题（#8710）。
- **原测试很弱。** 本次在 gold 修改位置附近构造了 9 个错误候选，分别只做固定输出、只修 Python 模式、只修 bool 等。**9 个在原材料正式评分全部得 1**；noop 为 0，gold 为 1。
- **修订草案 v2（R-c）。** 所有补充断言都写进唯一的 F2P 测试体，测试 ID 不变。补充四项：
  1. 题面示例的内部值，以及 Python、JSON 两种输出的精确值；
  2. 同一注解类型放进 `TypeAdapter(List[...])` 使用；
  3. 一个非示例实例；
  4. 未知类型回归检查。

  修订版正式诊断评分结果：

  | 候选 | 结果 |
  | --- | --- |
  | noop | 0 |
  | gold | **0**（只在未知类型处失败，按 D4 记录 gold 失败） |
  | 替代正对照 `upstream261` | **1** |
  | 第二正对照 `c3_reorder` | **1** |
  | 9 个错误候选 | 全 0，每个都停在为它设计的断言上 |
- **两份正对照机制不同。**
  - `upstream261`：gold 加上游 2.6.1 的一处异常捕获，方法体与 2.6.1 wheel 逐字相同。
  - `c3_reorder`：本页自写，不改 `PlainValidator`，而是在注解排序处把 serializer 移到它后面。

  修订断言对两种设计都成立，说明它们不是照着 gold 的机制写的。两份都由本页构造，**已由独立复核核实**（review.md §2）。
- **v1 到 v2 的变化是自查发现的。** 自查时构造的 `n_field_only` 只修模型字段，它在 v1 下得 1。v2 因此多加了一行 `TypeAdapter(List[...])` 检查，见 §4。
- **v2 到 v3 的变化来自独立复核。** 复核者的 `rv_pv_first` 在 v2 下得 1。v3 在测试体末尾加一段断言：放在 `PlainValidator` 之前的验证器按文档应被取代、不能运行，serializer 仍要生效。v3 下它为 0，其余候选的结果与 v2 相同。
- **实施依赖 D6 的“测试补丁替换”切片。** 派生镜像是云端等效重建，不是 09-19 原版的逐字节重建。

## 1．公开要求

**题面**：`PlainSerializer` 放在 `PlainValidator` 前面时不生效，题面期望 `BRight` 与 `BWrong` 的结果相同。
- 示例调用 `model_dump_json`，报告的错误输出是 `{"x": "0", "y": true}`，期望 `y` 也是 `"1"`；
- 验证后的内部值由 `PlainValidator` 决定，分别是 `False`／`True`，修复不应改变它们。

**核心要求（按题面的一般性理解，v1 §4）**：Annotated 类型里的 serializer，无论放在 `PlainValidator` 前还是后，都要生效。具体包括：
- Python 输出和 JSON 输出都要生效；
- 不限于 bool 类型，也不限于题面的 lambda；
- 这个注解类型可以复用。base 文档 `docs/concepts/validators.md` 写明，Annotated 用来“把验证绑定到类型而不是模型或字段”，并演示了嵌套进 `List` 的用法。

非示例实例还用到一个有文档的 serializer 选项：`docs/concepts/serialization.md` 的 `FancyInt` 示例，`when_used='json'`，即 Python 模式输出原值，JSON 模式输出 `'1,234'`。

**需要保护的已有能力：`PlainValidator` 取代内层验证，所以能用于 pydantic 生成不了 schema 的类型。**
- **公开依据**：
  - `PlainValidator` 的 docstring：“validation should be applied **instead** of the inner validation logic”；
  - `docs/concepts/validators.md:66`：“Plain validators … terminate validation immediately, no further validators are called and Pydantic does not do any of its internal validation”；
  - base 在默认配置下支持这一用法（§2，B01／B02）。
- **上游佐证（只作佐证，不当公开依据）**：
  - pydantic 2.6.1 changelog：“Fix unsupported types bug with `PlainValidator` (#8710)”；
  - 该版新增测试 `test_plain_validator_with_unsupported_type`，其中类型别名名为 `PreviouslySupportedType`。

  见 [`upstream_2.6.1_test_diff.txt`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/upstream_2.6.1_test_diff.txt)。

## 2．私有行为矩阵

条件：root 身份、断网、一次性容器。镜像 `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8567`：
- 摘要 `sha256:f7798240…7f87015`，与 ingest 冻结值一致；
- image ID `abbc218b…`，与 09-29 CPU 批次一致；
- 环境为 core 2.15.0、Python 3.8.19、pydantic 2.6.0a1。

矩阵用 [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/behavior.py) 跑，共 35 项，每项单独捕获异常和警告。全部补丁都由 [`make_candidate.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/make_candidate.py) 在 base 上做逐字替换生成，重新生成后与冻结补丁逐字节相同。

**（1）正对照、gold 与 base**。✓ 表示与 gold 输出相同。

| 场景 | base | gold | `upstream261` | `c3_reorder` | `c3_serpass`（未采用） |
| --- | --- | --- | --- | --- | --- |
| A01 题面原例：Python／JSON | `y` 为 `true` | `{"x":"0","y":"1"}`，内部值 False／True | ✓ | ✓ | ✓ |
| A03 `TypeAdapter`；A15 `List` 元素，均为错序 | serializer 未生效 | 生效 | ✓ | ✓ | ✓ |
| A04 FancyInt（`when_used='json'`）＋带 info 的 PV | JSON 输出 `1234` | Python `1234`，JSON `"1,234"` | ✓ | ✓ | ✓ |
| A05／A06／A10／A12／A13：int、`field_name`、`unless-none`、`return_type`、模型源类型 | 未生效 | 生效 | ✓ | ✓ | ✓ |
| A07 三项元数据（中间夹 `WithJsonSchema`）；A09 `WrapSerializer` 在前 | 未生效 | 生效 | ✓ | ✓ | ✓ |
| A08 serializer 与 PV 之间夹 `AfterValidator` | 7 | `"#7"` | ✓ | ✓ | **7（未修）** |
| A16 serializer 在类型参数里（`List[Annotated[int, ser]]` 外面再套 PV） | `[1,2]` | `["i1","i2"]` | ✓ | `[1,2]` | `[1,2]` |
| A17 源类型自带 serializer ＋ PV | JSON 报 `PydanticSerializationError` | `"21.0C"` | ✓ | 同 base | ✓ |
| **B01／B02 未知类型 ＋ PV（默认配置）** | 类能建成，验证、dump 正常 | **类定义抛 `schema-for-unknown-type`** | 同 base | 同 base | 同 base |
| B03 未知类型，serializer 放在 PV 前 | serializer 被忽略，JSON 报错 | 类定义抛错 | 同 base | **`"custom!"`** | 同 base |
| B06 PV 字段带未定义的前向引用 | 模型完整 | 模型不完整，实例化报 `class-not-fully-defined` | 同 gold | 同 base | 同 gold |
| B07 验证函数返回的类型与注解不符 | 无警告 | 每次 dump 1 条序列化警告 | 同 gold | 同 base | 同 base |
| B08 验证函数返回子类模型 | 含子类字段 `b` | 只有 `a` | 同 gold | 同 base | 同 base |
| B05 未知类型，`arbitrary_types_allowed=True`，serializer 放在前面 | serializer 被忽略，JSON 报错 | `"custom!"` | ✓ | ✓ | ✓ |
| B04 `arbitrary_types_allowed`；B09 docstring 示例；B10 `field_name`；B12 文档中的验证器排序；B13 `MaxLen` 被取代；B14 文档 `WithJsonSchema` 示例；B17 `Callable` | 行为一致 | 一致 | 一致 | 一致 | 一致 |
| B11 装饰器 `field_validator(mode='plain')` ＋ Annotated serializer | 未生效 | 未生效 | 未生效 | 未生效 | 未生效 |
| A18 题面模型在 serialization 模式下的 JSON schema | 抛 `invalid-for-json-schema` | 同 base | 同 base | 两字段均为 `string` | 两字段均为 `string` |

说明：
- `c3_serpass` 是本页先写的“只沿用内层顶层 `serialization`”窄修。它在 A08 上漏修，不作正对照，记为 T3，见 §5。
- `c3_reorder` 在 A16、A17 上不修。这两种情况是 serializer 来自类型参数或源类型自身，而不是注解顺序，超出题面范围，记为 T3。

**（2）错误候选**，都是为检验测试强度构造的，不是合理实现。各类别对应作者须知 §2.3。

| 候选 | 构造 | 类别 | 私有矩阵上的违例 |
| --- | --- | --- | --- |
| `n_const_str` | PV 一律用 `str(v)` 序列化 | 固定结果（§4 第 3 步退化） | 题面原例得 `"True"`，不是 `"1"` |
| `n_python_only` | 只在 Python 模式委托内层 serializer | 模式子集 | 题面原例 JSON 仍是 `"y": true`，与题面报告的错误一模一样 |
| `n_bool_only` | 只在源类型为 `bool` 时走 gold 逻辑 | 示例字面值 | int 类型的实例未修 |
| `n_noinfo_only` | 只改 no-info 分支 | 路径子集 | 带 info 的 PV 未修；未知类型同样报错 |
| `n_swallow_to_any` | 内层 schema 生成失败时退成 `any_schema` | 吞掉错误 | 未知类型能建类，但验证函数被静默丢掉，`u='abc'` 原样保留 |
| `n_when_used_lost` | 重新包装内层函数，丢掉 `when_used` | serializer 选项子集 | FancyInt 在 Python 模式也输出 `'1,234'` |
| `n_order_registry` | PV 取全局登记的“最近一个 PlainSerializer” | 依赖执行顺序 | 单字段错序模型用到别处的旧 serializer，也会污染无关字段 |
| `n_two_items` | 只在元数据恰为两项时交换顺序 | 规模／阈值 | 三项元数据未修 |
| `n_field_only` | 只在模型字段的元数据上换序 | 使用路径子集 | `TypeAdapter`、`List` 元素未修 |

**（3）公开测试**，均未应用 test_patch：
- 相关 5 个模块（validators、serialize、json_schema、annotated、types）：14 个版本（base、gold、3 个替代实现、9 个错误候选）都是 1413 passed、6 skipped、2 xfailed，**没有任何区分力**；
- 全量 `tests/`：base、gold、`upstream261`、`c3_reorder`、`c3_serpass` 都是 4639 passed、196 skipped、7 xfailed、0 failed。由于都没有失败，通过集合相同。

## 3．原材料正式评分

条件：
- F2P 1 项，P2P 158 项；
- 09-19 `pydantic_v1` 安装命令修订 [`pydantic__pydantic-8567.json`](../../../env_recipe_repair_20260919/pydantic_v1/pydantic__pydantic-8567.json)，recipe sha256 `f013894e…`；
- 云端等效重建的离线 wheel 层（`rebuild_wheel_layer.py --kind build`）：Dockerfile 文本与原配方相同，8 个 wheel 的固定版本与 sha256 和 pydantic-9066 所用集合逐一相同；
- 派生镜像 `sha256:2b170da8…`，保留 base 的 13 层，只加 1 层，见 [evidence/derived_image.json](evidence/derived_image.json)；
- **这不是 09-19 原版的逐字节重建。**

所有运行：grader UID 54322、`deny_all`、2 CPU／4 GiB；安装 rc 0；参考缺席 0；P2P 158/158；清理成功；导入包版本 2.6.0a1。

| 候选 | sha256 | reward | F2P |
| --- | --- | --- | --- |
| noop | — | 0 | 0/1：`isinstance(True, str)` 失败 |
| gold | `86200100…`（与 ingest 一致） | 1 | 1/1 |
| `upstream261` | `79731949…` | 1 | 1/1 |
| `c3_reorder` | `221bbe05…` | 1 | 1/1 |
| `c3_serpass` | `09c0877a…` | 1 | 1/1 |
| `n_const_str` | `55a01957…` | **1** | 1/1 |
| `n_python_only` | `fd676993…` | **1** | 1/1 |
| `n_bool_only` | `e5dfa345…` | **1** | 1/1 |
| `n_noinfo_only` | `b97f84d7…` | **1** | 1/1 |
| `n_swallow_to_any` | `91479fee…` | **1** | 1/1 |
| `n_when_used_lost` | `cedc8a52…` | **1** | 1/1 |
| `n_order_registry` | `7e9a3c68…` | **1** | 1/1 |
| `n_two_items` | `39204a67…` | **1** | 1/1 |
| `n_field_only` | `6bcfbc02…` | **1** | 1/1 |

noop 与 gold 的结果和 09-29 CPU 批次一致。每次运行约 25 秒，其中准备阶段约 9–11 秒。

## 4．修法：R-c 修订版测试草案 v2 与诊断评分

**草案**：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v2.patch)，sha256 `6cff9609…`；原 test_patch 的 sha256 为 `e0d94467…`。

改法：只改 F2P `test_plain_validator_plain_serializer` 的测试体，并在 import 里加 `WithJsonSchema`。原有两行 `isinstance` 保留，其后追加：

1. **题面示例（T2a）**：
   - `blah.foo is False`、`blah.bar is True`；
   - `model_dump() == {'foo': '0', 'bar': '1'}`；
   - `model_dump_json() == '{"foo":"0","bar":"1"}'`。
2. **同一类型不作模型字段使用（T2c，路径）**：
   - `TypeAdapter(List[Annotated[bool, serializer, validator]])` 验证 `['0','1']` 得到 `[False, True]`；
   - `dump_json` 结果为 `b'["0","1"]'`。
3. **非示例实例（T2c）**：
   - 单字段模型：`Annotated[int, PlainSerializer(FancyInt 函数, return_type=str, when_used='json'), PlainValidator(lambda v, info: int(v)), WithJsonSchema({'type': 'integer'}, mode='validation')]`；
   - 输入 `'1234'`，Python 输出 `1234`，JSON 输出 `'{"x":"1,234"}'`；
   - 这个实例在类型、serializer、带 info 的签名、元数据个数上都与题面示例不同。
4. **回归（G1→S1）**：
   - 默认配置下，模型字段 `Annotated[Unsupported, PlainValidator(lambda v: Unsupported())]` 能建类；
   - `u='abc'` 验证后得到 `Unsupported` 实例；
   - `model_dump()['u']` 仍是该实例。形态与上游 2.6.1 回归测试相同。

测试 ID 与 F2P／P2P 名单都不变。

**修订版诊断评分**：使用 `--recipe` 与 `--materials`，grader 后缀 `+c3-pyd8567-exact-json-unsupported-v2`。所有运行参考缺席 0、P2P 158/158、清理成功。

| 候选 | v2 reward | 失败位置（正式评分日志） |
| --- | --- | --- |
| noop | 0 | `isinstance(data['bar'], ser_type)` |
| gold | **0** | `class WithUnsupported` 定义处抛 `PydanticSchemaGenerationError`，按 D4 记录 gold 失败 |
| `upstream261`（替代正对照，已由复核核实） | **1** | |
| `c3_reorder`（第二正对照，已由复核核实） | **1** | |
| `c3_serpass`（不作正对照，见 §5 T3） | 1 | |
| `n_const_str` | 0 | `data == {'foo':'0','bar':'1'}`，实得 `'True'` |
| `n_python_only` | 0 | `model_dump_json()`，实得 `"bar":true` |
| `n_field_only` | 0 | `ta.dump_json(...)`，实得 `b'[false,true]'` |
| `n_bool_only`、`n_noinfo_only`、`n_two_items` | 0 | `other.model_dump_json()`，实得 `{"x":1234}` |
| `n_when_used_lost` | 0 | `other.model_dump()`，实得 `'1,234'` |
| `n_order_registry` | 0 | `other.model_dump()`，实得 `'1234'`（用了别处的旧 serializer） |
| `n_swallow_to_any` | 0 | `isinstance(m.u, Unsupported)`，实得 `'abc'` |

**v1 到 v2 的过程（留档）**：
- v1（[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v1.patch)，`84a10ba6…`）没有第 2 项；
- v1 正式诊断评分：noop 0、gold 0、3 个替代实现 1、前 8 个错误候选 0；
- 随后自查构造 `n_field_only`，它在私有模拟中 v1 得 1，原材料正式评分也得 1，于是加了第 2 项，形成 v2；
- 私有模拟评分与正式评分在 v1、v2 的全部候选上逐项一致。

**正对照说明**：
- **`upstream261`**，[`upstream261.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/upstream261.patch)：
  - 在 gold 的基础上，把 `handler(source_type)` 放进 `try`，捕获 `PydanticSchemaGenerationError` 后设 `serialization=None`，即退回 base 的行为；
  - 方法体与 PyPI 2.6.1 wheel 逐字相同（脚本核对），2.6.4、2.7.0、2.8.0 也相同，见 [`upstream_2.6.1_plain_validator.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/upstream_2.6.1_plain_validator.py)；
  - 这是对 gold 的最小窄修。
- **`c3_reorder`**，[`c3_reorder.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/c3_reorder.patch)：
  - 在 `_generate_schema._apply_annotations` 里，把位于最后一个 `PlainValidator` 之前的 `PlainSerializer`／`WrapSerializer` 移到它紧后面，保持它们之间的相对顺序；`PlainValidator` 本身不改；
  - 私有矩阵中它在 B03、B06、B07、B08 上保持或优于 base；A16、A17 不修，属于题面范围外。
- 两者都由本页构造，按 v1 §9 D4 须由他人独立核实；独立复核已核实（review.md §2）。

### v3：处理复核阻断项（09-30 重跑验证）

**草案**：[`revised_test_v3.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v3.patch)，sha256 `4600867b…0eba`；材料 [`materials_revised_v3.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/materials_revised_v3.json)，版本 `c3-pyd8567-exact-json-unsupported-v3`。父版本 v2（`6cff9609…`）留档。

在 v2 的测试体末尾追加第 5 项：

```python
class Replaced(BaseModel):
    z: Annotated[bool, AfterValidator(lambda v: 1 / 0), serializer, validator]

replaced = Replaced(z='1')
assert replaced.z is True
assert replaced.model_dump() == {'z': '1'}
```

- **依据**：`docs/concepts/validators.md:66`：Plain validator 会立即终止验证，“no further validators are called”；`PlainValidator` 的 docstring 写明它取代内层验证。放在它之前（元数据左侧）的 `AfterValidator` 因此不应运行。
- **拦下**：`rv_pv_first`（把 PV 挪到最内层，被取代的验证器仍然运行，抛 `ZeroDivisionError`）。
- 测试 ID、F2P／P2P 名单、测试命令都不变。

**复核者候选的来源**：复核者的补丁只在其会话临时目录，未入库。实验目录中的 `rv_pv_first.patch`（`eb842ab8…`）、`rv_condwrap.patch`（`177c3af4…`）、`rv_ser_to_end.patch`（`a8301321…`）是按 review.md §1 的描述重建的，哈希与复核者的补丁不同；它们在原材料与 v2 上的分数与复核者的私有模拟一致。

**正式诊断评分（09-30 重跑）**：
- 条件：`--recipe` 与 `--materials`，grader 后缀 `+c3-pyd8567-exact-json-unsupported-v3`；
- 派生镜像按同一配方在云端重建：8 个 wheel 的文件名与 sha256 与此前逐一相同，保留 base 的 13 层只加 1 层；本机派生 ID 为 `sha256:b63f44d5…`（本机构建 ID 每次不同，此前为 `2b170da8…`）；
- 全部 23 次运行（v3 17 次，另有复核者 3 个候选在原材料与 v2 上各 3 次）：参考缺席 0，P2P 158/158，安装 rc 0，清理成功。

| 候选 | 性质 | 原材料 | v2 | v3 | v3 失败位置（评分日志） |
| --- | --- | --- | --- | --- | --- |
| noop | — | 0 | 0 | 0 | `isinstance(data['bar'], ser_type)` |
| gold | 参考解（D4：不作正对照） | 1 | 0 | 0 | 未知类型断言：`PydanticSchemaGenerationError` |
| `upstream261` | 替代正对照（已核实） | 1 | 1 | **1** | — |
| `c3_reorder` | 第二正对照（已核实） | 1 | 1 | **1** | — |
| `rv_condwrap` | 合理实现（复核者） | 1 | 1 | **1** | — |
| `c3_serpass` | T3 边缘（§5 第 1 项） | 1 | 1 | 1 | — |
| `rv_ser_to_end` | T3 边缘（复核 N2） | 1 | 1 | 1 | — |
| **`rv_pv_first`** | 错误（复核阻断项） | 1 | **1** | **0** | 新增断言：`ZeroDivisionError` |
| `n_const_str` | 错误 | 1 | 0 | 0 | `{'foo':'0','bar':'True'}` |
| `n_python_only` | 错误 | 1 | 0 | 0 | JSON 仍为 `"bar":true` |
| `n_field_only` | 错误 | 1 | 0 | 0 | `b'[false,true]'` |
| `n_bool_only`、`n_noinfo_only`、`n_two_items` | 错误 | 1 | 0 | 0 | `'{"x":1234}'`，应为 `'{"x":"1,234"}'` |
| `n_when_used_lost` | 错误 | 1 | 0 | 0 | Python 模式也输出 `'1,234'` |
| `n_order_registry` | 错误 | 1 | 0 | 0 | 用了别处的旧 serializer，得 `'1234'` |
| `n_swallow_to_any` | 错误 | 1 | 0 | 0 | 未知类型验证函数被丢掉 |

原材料与 v2 两列中，复核者 3 个候选取自 09-30 重跑，其余取自 09-29 的归档账本。

**v3 验收（v1 §5）**：

| 验收项 | 结果 |
| --- | --- |
| 正对照为 1，noop 为 0 | 满足：`upstream261`、`c3_reorder` 为 1，noop 为 0 |
| 已知错误候选为 0 | 满足：9 个作者错误候选与 `rv_pv_first` 都为 0，各停在针对它的断言上 |
| 合理实现不被拒 | 满足：`rv_condwrap` 为 1；T3 登记的两个边缘候选不受影响 |
| gold 的处理 | gold 只在未知类型回归断言处失败，按 D4 记录，改用替代正对照 |
| 独立复核与 Codex 复核 | 首轮复核阻断已处理；**v3 聚焦复核又发现 3 项阻断，v3 不再采用**，见下一小节 |

### v4：熔断收口（09-30 正式诊断评分验证，采用版本）

**为什么是熔断**：首轮复核的阻断 `rv_pv_first`（把 PV 挪到最内层，被取代的左侧验证器仍然运行）与 v3 聚焦复核的 B1（把 PV 左侧约束挪到外层继续生效）是同一状态边界——“PV 左侧元数据的处理”——上连续两轮出现的新阻断。按协作协议 §5，不再在 v3 上增量修补，采用复核者按根因写好、在私有模拟中验证过的 `t_v4`，由 Codex 确认，不再开 Claude 复核轮次。

**草案**：[`revised_test_v4.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v4.patch)，sha256 `7014f5fc…b86e`，与复核者的 `review_v3/tests/t_v4.patch` 逐字节相同；材料 [`materials_revised_v4.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/pydantic8567/materials_revised_v4.json)，版本 `c3-pyd8567-exact-json-unsupported-v4`。父版本 v3（`4600867b…`）留档。只改唯一 F2P 测试体，测试 ID、F2P／P2P 名单与测试命令不变。

相对 v3 的三处改动：

| 改动 | 依据 | 拦下 |
| --- | --- | --- |
| 第 5 项 `Replaced` 的字段类型由 `bool` 改为 `StrictBool`（import 加 `StrictBool`） | PV 取代内层验证：它左侧的约束同样不应生效（PV docstring、`validators.md:66`） | B1：`bad_nonvalidators_after_pv`、`bad_pv_first_skip_validators`、`bad_pv_first_skip_after`（类定义时抛 `RuntimeError`，strict 约束被套到 PV 外层） |
| 新增 `Between`：`Annotated[int, PlainSerializer(v*10), AfterValidator(1/0), PlainValidator(int)]`，断言 `Between(w='7').w == 7`、`model_dump() == {'w': 70}` | serializer 无论与 PV 相隔几个元数据都要生效；夹在中间的验证器同样被 PV 取代，不运行 | B2：`c3_serpass`、`bad_swap_adjacent`（serializer 不生效），`bad_swap_nearest`、`bad_pv_before_first_ser`（中间验证器被挪到外层运行） |
| 新增 `Both`：PV 两侧各有一个 serializer，断言外层（`'outer'`）生效 | 与没有 PV 时相同，是 base 已有行为 | B3：`rv_ser_to_end`、`bad_rewrap_noinfo` |

`Between` 的 serializer 故意返回同类型值：若按首轮复核的建议 1 用返回 str 的 serializer，上游 2.10 写法的回移 `ok_up210` 会因序列化警告被 pytest `filterwarnings = ['error']` 判失败（review_v3.md §1、§8）。

**正式诊断评分**：`--recipe` 与 `--materials`，grader 后缀 `+c3-pyd8567-exact-json-unsupported-v4`，派生镜像 `b63f44d5…`；31 次全部参考缺席 0、安装 rc 0、清理成功，除 `rv_before_sem_rebuilt` 外 P2P 158/158。

| 候选 | 性质 | v4 reward | v4 失败位置（测试文件行号） |
| --- | --- | --- | --- |
| `upstream261`、`c3_reorder` | 替代正对照（已核实） | **1** | — |
| `rv_condwrap` | 合理（首轮复核者） | **1** | — |
| `ok_serdig`、`ok_wrapshim`、`ok_up210`、`ok_post_attach`、`ok_pv_first_keep_sers` | 合理（聚焦复核者） | **1** | — |
| noop | — | 0 | 2827：`isinstance(data['bar'], ser_type)` |
| gold | 参考解（D4：不作正对照） | 0 | 2860：未知类型 `class WithUnsupported`，抛 `PydanticSchemaGenerationError` |
| `n_const_str`／`n_python_only`／`n_field_only` | 错误 | 0 | 2832／2833／2838 |
| `n_order_registry`、`n_when_used_lost`／`n_bool_only`、`n_noinfo_only`、`n_two_items` | 错误 | 0 | 2852／2853 |
| `n_swallow_to_any` | 错误 | 0 | 2864：`isinstance(m.u, Unsupported)` |
| `rv_pv_first`、`bad_nonvalidators_after_pv`、`bad_pv_first_skip_validators`、`bad_pv_first_skip_after` | 错误（B1 同族） | 0 | 2869：`class Replaced` 抛 `RuntimeError`（strict） |
| `bad_pv_first_if_only_sers` | 错误 | 0 | 2874 |
| `bad_swap_nearest`、`bad_pv_before_first_ser` | 错误（B2） | 0 | 2882：`Between(w='7')` 抛 `ZeroDivisionError` |
| `c3_serpass`、`bad_swap_adjacent` | 错误（B2） | 0 | 2884：得 `{'w': 7}` |
| `rv_ser_to_end`、`bad_rewrap_noinfo` | 错误（B3） | 0 | 2890：得 `{'b': 'inner'}` |
| `rv_before_sem_rebuilt` | 错误 | 0 | P2P `test_plain_validator_field_name` 失败（157/158） |

逐次失败原因见 `evidence/rerun_0930/formal_revised_v4/failure_reasons.txt`。复核者的候选补丁已从 `review_v3/cands/` 复制到实验目录。

**v4 验收（v1 §5）与停止条件（review_v3.md §7）**：

| 验收项 | 结果 |
| --- | --- |
| 正对照为 1，noop 为 0 | 满足 |
| 误拒已纠正且不新增误拒 | 满足：8 个合理实现（含上游 2.10 写法的回移 `ok_up210`）为 1 |
| 已知错误候选为 0 | 满足：22 个已知错误候选为 0，各停在针对它的断言上 |
| 停止条件：reward 与失败位置与复核表逐项一致，P2P 158/158、参考缺席 0、安装 rc 0、清理成功 | 满足（`rv_before_sem_rebuilt` 的 P2P 157/158 是复核表本身的预期） |
| Codex 确认 | **待做**（熔断规则要求） |

## 5．判定（v1 §4）

**原版：S1。** 命中的步骤如下：

- **第 1 步，T2a**：核心要求是“Python 与 JSON 都使用 serializer 的输出”，参考测试只断言 Python 输出是 `str`，JSON 没有断言。`n_python_only`（JSON 与题面报告的错误完全相同）和 `n_const_str` 都得 1。
- **第 2 步，T2c 示例拟合**：测试只用了题面同一类型、同一 lambda、直接模型字段、两项元数据。`n_bool_only`、`n_noinfo_only`、`n_two_items`、`n_order_registry`、`n_field_only` 都得 1。
- **第 3 步，T2b 退化**：在 gold 修改位置构造与输入无关的固定输出 `n_const_str`，得 1。
- **第 4 步，G1→S1**：gold 得 1，但破坏了有文档、常用的 `PlainValidator` 能力（接管 pydantic 无 schema 的类型）。上游在下一个补丁版修复，可作佐证。

**已由 v4 修复的原 T3 项**（09-30 v3 聚焦复核按“已知错误不因少见放过”改判）：
- **A08**：serializer 与 PV 之间夹了验证器（B2，v4 的 `Between`）；
- **N2**：PV 两侧都有 serializer 时改用内侧（B3，v4 的 `Both`）。

**登记为 T3 或不断言（v4 之后不再追加断言，review_v3.md §6、§7）**：
1. **A09 `WrapSerializer`、带 info 的 serializer**：v4 下已没有得 1 的已知违例候选，不另加断言。
2. **A16／A17**：serializer 来自类型参数或源类型自身。gold 与 `upstream261` 修了，`c3_reorder` 没修；这超出“注解顺序”的题面范围，断言它等于把 gold 的“委托内层 schema”定为唯一答案。
3. **B03**：生成不了 schema 的类型、serializer 放在 PV 前。严格说是核心要求的一个实例，但不断言，理由不是“少见”：`upstream261`（上游 2.6.1–2.10 的正式修法，也是本题正对照）在 B03 上与 base 相同；B03 与要保护的“PV 接管生成不了 schema 的类型”直接冲突，私有 v4b03 中 8 个合理实现有 5 个因此得 0，断言它等于把“在注解层修”定为唯一路线。若协调者仍要求覆盖，正对照只能保留 `c3_reorder`，预期见 `review_v3/out/summary.txt` 的 `t_v4b03` 列。
4. **B06／N3**：PV 字段引用运行时不存在的前向引用；Python < 3.12 的 `typing.TypedDict`。gold、`upstream261` 等在 PV 内委托内层 schema 的实现相对 base 回归，这是正对照 `upstream261` 自身的已知回归；断言它就得先放弃 `upstream261`。交接时写明它在这两类输入上不能当参考。
5. **B07／B08**：没有 serializer 时，gold 与上游式按注解类型序列化，base 按运行时推断。两种都说得通（`serialization.md:393-396`），修订版不断言。
6. **B11**：装饰器形式的 `field_validator(mode='plain')` 同样会丢掉 Annotated serializer。所有版本都一样，不在题面范围内。
7. **A18**：serialization 模式的 JSON Schema，`c3_reorder` 由报错变为 `string`，属附带改进。

## 6．交接给第2类

1. **正对照**：`upstream261` 作替代正对照，`c3_reorder` 作第二正对照，两者都**已由独立复核核实**（review.md §2）。`ok_wrapshim` 只作过严检查的探针，不宜作正对照：它把 PV 字段在 validation 模式下的 JSON Schema 由报错改成了内层类型，而 `docs/concepts/json_schema.md:589-590` 写明 PV 会报错、需用 `WithJsonSchema` 覆盖。
2. **落地**：以 R-c 草案 v4（`7014f5fc…`）替换原 test_patch 形成正式版本。测试 ID、F2P／P2P 名单与测试命令不变。所需的 D6“测试补丁替换”是已获总体授权、尚未实现的后续实施项（D6 已验收的首片只有 `append_mypy_p2p`）；本页的 `--materials` 诊断评分不等于正式 actor 已消费修订版。
3. **复验**：落地后复验 §4 v4 小节的表（31 个候选）。
4. **可选拆分**：如果 D6 支持新增参考，建议把第 4 项未知类型回归拆成独立 P2P。可沿用上游测试名 `test_plain_validator_with_unsupported_type`，形态相同。
5. **镜像**：正式入库时固定一份 wheel 清单并登记来源，因为本页派生镜像是等效重建。
6. **复核**：Codex 确认 v4（熔断规则）与 Codex 复核。
7. **提醒**：正对照的范围差异随交接保留。`upstream261` 在 B06、B07、B08、N3 上与 base 不同（B06、N3 是它自身相对 base 的回归，不能当参考）；`c3_reorder` 在 A16、A17 上不修。以后再加涉及“serializer 改变类型，且中间有包层元数据”的断言，先用 `ok_up210` 试一遍（上游 2.10 在这种布局下有序列化警告）。

## 7．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练 | 留出 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否（09-30 按 Codex 复核更正：原版有已证的 S1 未修，不能靠事后审计进入普通能力比较；特殊诊断试解另列调查目的，不混用原分数） | 否 | 否 |
| 修订版 v4 | 经 Codex 确认、D6 入库并验收后重新评估 | | | |

## 8．未做与剩余事项

- **独立复核**：首轮已完成，两份正对照已核实；v3 聚焦复核的 3 项阻断由 v4 处理，v4 正式诊断评分与停止条件逐项一致。按熔断规则，v4 由 Codex 确认，不再开 Claude 复核轮次。
- **聚焦复核未查**（review_v3.md §9）：复核者的候选与各修订版本只有私有模拟（v4 现已正式评分）；只查了 Python 3.8；全量公开测试只跑了 12 个候选；`rv_before_sem` 是按首轮描述重建的。
- **真实 actor 开发条件**：本次未验。09-29 CPU 批次在原版上做过 actor 核对。
- **模型求解**：没有模型求解证据。
- **v1 修订的正式评分**：不含 `n_field_only`，它只有私有模拟结果。
- **全量公开测试**：只跑了 base、gold 与 3 个替代实现，错误候选只跑了相关的 5 个模块。
- **§5 的 T3 项**：只登记，没有为它们设计断言。
- **修订版进训练前的条件**：还需要 v1 §2 的其它正面证据，本页未做。
- **派生镜像**：是等效重建，不是 09-19 原版。
- **上游资料来源**：github.com 的 PR 页面读不到，上游资料只来自 PyPI wheel、wheel 内 changelog，以及 raw.githubusercontent.com 的测试文件。

## 9．版本与证据

- **代码与运行环境**：见 [环境说明](../../environment.md)。
- **既有材料**：
  - [CPU 批次结果](../../../swegym_cpu_preprobe_20260929/tasks/pydantic__pydantic-8567/result.md)
  - [题卡](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8567/card.md)
  - [复核](../../../swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8567/review.md)
- **实验文件**：`rh2/experiments/category3_cloud_20260929/pydantic8567/`
  - 候选：`make_candidate.py`、12 个候选补丁；
  - 私有矩阵：`behavior.py`；
  - 修订测试：`_edit_revised_test*.py`、`original_test.patch`、`revised_test_v1.patch`、`revised_test_v2.patch`、`revised_test_v3.patch`；
  - 诊断评分材料：`materials_revised_v1.json`、`materials_revised_v2.json`、`materials_revised_v3.json`、`materials_revised_v4.json`（v4 补丁 `revised_test_v4.patch`）；
  - v3 聚焦复核材料：`review_v3/`（候选 `cands/` 14 个，已复制到实验目录；测试变体 `tests/`；脚本与 `out/` 运行输出）；
  - 复核者候选（按 review.md 重建）：`rv_pv_first.patch`、`rv_condwrap.patch`、`rv_ser_to_end.patch`；
  - 私有对照与模拟评分：`semantic_spec*.json`、`fulltests_spec.json`、`simgrade*_spec.json`、`simgrade.py`；
  - 正式评分：`run_formal.sh`；
  - 上游佐证：`upstream_2.6.1_*`。
- **原始证据**：[evidence/](evidence/)
  - `formal/`、`formal_revised_v1/`、`formal_revised_v2/`：账本、评分日志、审计；
  - `formal_summary.json`：41 次正式运行的逐项摘要，包括失败位置；
  - `semantic_v1/`、`semantic_v1b/`：私有矩阵与相关公开测试；
  - `fulltests_v1/`：全量测试；
  - `simgrade_v1/`、`simgrade_v2/`：私有模拟评分；
  - `derived_image.json`：wheel 清单与镜像身份；
  - `evidence_manifest.json`：全部文件的 SHA256；
  - `rerun_0930/`：09-30 重跑，含 `formal_revised_v3/`（17 次）、`formal_revised_v4/`（31 次，含 `failure_reasons.txt`）、`formal/` 与 `formal_revised_v2/`（复核者 3 个候选各 3 次）、`derived/image.json`（重建记录），以及本目录自己的 `evidence_manifest.json`。
- **归档前扫描**：已扫描凭据字样与本机私有路径，未命中。
