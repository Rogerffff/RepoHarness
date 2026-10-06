# pydantic__pydantic-8567 修订版 v3 聚焦复核

2026-09-30，聚焦复核者（不继承作者与首轮复核者的上下文）。按首轮 [review.md](review.md) 的意见核对 v3，并遵守负责人 09-30 补充的三条原则：题面建议的实现方式不升级为要求；已知错误候选不因“少见”“实现不自然”放过；给出停止条件与交接时必须一并修的项。

**总判断：部分同意。阻断项 3 项。三项可用同一份已私有验证的补丁（草案 v4）一次修完；修后按 §7 的停止条件交第2类，不再开复核轮次。**

- **同意的部分**：v3 新增的第 5 项有充分公开依据，没有发现误拒。我另写的 5 个合理实现在 v3 下都得 1，全量公开测试也都通过；它们的机制都不同于 gold、`upstream261`、`c3_reorder`、`rv_condwrap`，其中一个是上游 pydantic 2.10 写法的回移。`rv_pv_first` 在 v3 下正式为 0。作者 17 份 v3 正式账本逐份核对，与结论页一致；两份替代正对照在 v3 下为 1。
- **B1（新发现，S1）**：v3 只挡住了“把 PV 挪到内层”同族中会运行左侧验证器的写法，挡不住把左侧约束挪到 PV 外面的写法。同族 3 个写法在 v3 下得 1，却让 `Annotated[StrictBool, PlainValidator(...)]`、`x: Annotated[bool, PlainValidator(...)] = Field(strict=True)` 在类定义时抛 `RuntimeError`，也让 `PositiveInt`、`= Field(gt=0)` 的约束在 PV 之后被强制执行。全量公开测试（4639 项）拦不住它们。
- **B2、B3（按原则 2 改判）**：首轮与作者登记为 T3 的 `c3_serpass`、`rv_ser_to_end` 在 v3 下都得 1，二者都违反公开要求，我构造的 4 个同类错误候选也得 1：
  - `c3_serpass`：serializer 与 PV 之间夹一个验证器时，serializer 不生效；
  - `rv_ser_to_end`：PV 两侧都有 serializer 时改用内侧那个，相对 base 是回归。
- **修法**：见 §7 的 v4 草案，只改 F2P 测试体，测试 ID、F2P/P2P 名单与测试命令不变。私有模拟结果：
  - 为 1 的 8 个：两份正对照、`rv_condwrap`、我的 5 个合理实现；
  - 为 0 的 23 个：noop、gold 与全部已知错误候选，各停在针对它的断言上。
- **首轮非阻断建议 1 不宜照原样采纳**。该建议把 `AfterValidator` 夹在 serializer 与 PV 之间，并断言 dump。它会让上游 2.10 写法的回移 `ok_up210` 得 0：serializer 改变类型时有序列化警告，pytest `filterwarnings = ['error']` 会把警告变成失败。它也拦不住 B1。v4 的 `Between` 改用返回同类型值的 serializer，避开了这个问题。

## 1. 核对范围与证据层级

| 层级 | 内容 | 用途 |
| --- | --- | --- |
| 正式评分（只读） | 作者 09-30 的 v3 账本 17 份；复核者 3 个候选在原材料与 v2 上的重跑账本 6 份 | 核对作者结论。我没有运行任何正式评分 |
| 私有模拟评分（本人实跑） | 31 个候选 × 9 个测试版本（v2、v3、4 个 v3 变体、首轮建议 1 的形式、v4、v4b03） | 判断断言强度与修法。不是正式评分 |
| 私有行为矩阵（本人实跑） | 31 个候选 × 34 项行为 | 按公开要求判对错，不以 gold 为答案 |
| 公开测试（本人实跑） | 15 个候选跑相关 5 个模块与 `test_docs.py` 中三页示例（55 项）；12 个候选跑全量 `tests/` | 看公开测试能否暴露错误候选，以及合理实现是否破坏公开行为 |

私有运行条件：
- **镜像**：`c3keep/pydantic8567:src`，image ID `abbc218b…`，RepoDigest `f7798240…7f87015`，与冻结值一致；
- **版本**：Python 3.8.19、pydantic 2.6.0a1、pydantic-core 2.15.0、pytest 7.4.3；
- **容器**：一次性、`--network none`、root；每个候选先 `git checkout -- pydantic tests` 复位，再套候选补丁与测试补丁；
- **判分**：测试命令即评分包的 `eval_cmd`，`pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_validators.py`；按评分包参考名单（F2P 1 项、P2P 158 项）逐名判分；
- **没用到的条件**：grader profile（UID 54322、2 CPU/4 GiB）、派生镜像、非 root 身份。

**私有模拟与正式评分的一致性**：
- 作者 17 个候选在我的私有 v3 下，分数和失败行号与 09-30 正式账本逐项相同；
- 复核者 3 个候选在私有 v2 下与正式重跑相同，都是 1。

## 2. 阻断项 N1 的核对结果

### 2.1 第 5 项的公开依据：成立

| v3 第 5 项的断言 | 公开依据 | 判断 |
| --- | --- | --- |
| 左侧的 `AfterValidator(lambda v: 1 / 0)` 不运行 | 见表下说明 | 有直接文档依据。09-25 独立公开读者也据此推出“plain 左侧的内部验证继续不运行” |
| `replaced.z is True` | PV 的返回值就是验证结果 | 不过严 |
| `model_dump() == {'z': '1'}` | 题面核心要求；serializer 紧挨在 PV 左侧，与题面 `BWrong` 的布局相同 | 没有新增要求 |

第一行的公开依据：
- `PlainValidator` docstring（`pydantic/functional_validators.py:132`）：validation applied **instead** of the inner validation logic；
- `docs/concepts/validators.md:66`：plain validators “terminate validation immediately, no further validators are called and Pydantic does not do any of its internal validation”；
- 同文件 `:69-70`：a plain validator will not call any inner validators；
- 同文件 `:133-134` 规定验证“从右到左再回来”，即左侧是内层；
- 同文件 `:137-263` 的排序示例：PV 左侧的 before、after、wrap 都不出现在输出里。

### 2.2 能否拒绝“把 PV 挪到内层”这一类：只拒掉一半

首轮 N1 据以判 S1 的后果有两类：一是 PV 左侧的验证器被运行，二是左侧约束（`StrictBool`、`PositiveInt`）被套到 PV 外面。v3 第 5 项只在左侧放了一个 `AfterValidator`，只覆盖第一类。

| 同族写法 | 做法 | v3 私有模拟 | 左侧验证器 | 左侧约束 |
| --- | --- | --- | --- | --- |
| `rv_pv_first`（首轮） | PV 挪到最内层 | **0**（L2871 `ZeroDivisionError`，正式评分同） | 运行 | 套到外层 |
| `bad_pv_first_skip_validators` | PV 挪到最内层，丢掉左侧的 Before/After/Wrap/Plain 验证器 | **1** | 不运行 | 套到外层 |
| `bad_nonvalidators_after_pv` | 把左侧的非验证器元数据（serializer、约束、`WithJsonSchema` 等）整体挪到 PV 紧后 | **1** | 不运行 | 套到外层 |
| `bad_pv_first_skip_after` | PV 挪到最内层，只丢掉左侧的 `AfterValidator` | **1** | Before/Wrap 仍运行 | 套到外层 |

`rv_pv_first` 本身已被拒，后 3 个仍得 1，见 §5 B1。

### 2.3 作者 v3 正式账本与结论页：一致（17 份全核）

- **账本逐份核对的项目**：
  - `run_id`，候选补丁 sha256（与 result.md 所列前缀一致），reward、outcome、F2P；
  - grader 版本后缀 `+c3-pyd8567-exact-json-unsupported-v3`；
  - 审计目录 `materials.json` 的 `test_patch`，其 sha256 为 `4600867b…0eba`，与 `revised_test_v3.patch`、`materials_revised_v3.json` 相同；
  - image `b63f44d5…`、UID 54322、`deny_all`、安装 rc 0、清理成功、参考缺席 0。
- **原始日志重数**：按参考名单重数 17 份原始 eval log，均为 P2P 158/158、无缺席；账本记录的日志 sha256 与归档文件一致。
- **失败位置**与 result.md §4 v3 表逐项一致：
  - noop：L2826；
  - gold：L2859，`class WithUnsupported` 处抛 `PydanticSchemaGenerationError`；
  - 9 个 `n_*`：各停在为它设计的断言；
  - `rv_pv_first`：L2871，`ZeroDivisionError`。
- **两份替代正对照**：`upstream261`、`c3_reorder` 在 v3 下正式为 1，在我的私有 v3、v3s、v4 下也都为 1。
- **复核者候选的 6 份重跑账本**：原材料与 v2 上均为 1。v2 审计材料的 sha256 为 `6cff9609…`。
- **`rerun_0930/evidence_manifest.json`**：238 个已归档文件的 sha256 全部相符；另 142 项标为 artifacts/prepared/private，按规定未归档。
- **派生镜像记录**：8 个 wheel 的文件名与 sha256 与 09-29 相同；保留 base 的 13 层，共 14 层；ID `b63f44d5…`，本机现存镜像的 ID 相同。

## 3. 新增断言是否过严：未发现误拒

我另写了 5 个合理实现，机制都不同于 gold、`upstream261`、`c3_reorder`、`rv_condwrap`：

| 候选 | 机制 | v2 | v3 | v4 | 全量公开测试 | 私有矩阵 |
| --- | --- | --- | --- | --- | --- | --- |
| `ok_serdig` | PV 内生成内层 schema，沿 function-before/after/wrap 链找到第一个 `serialization` 并直接沿用；生成失败则不设 | 1 | 1 | 1 | 4639 passed | 无违例 |
| `ok_wrapshim` | 用“从不调用 handler 的 wrap 验证器”包住内层 schema：验证只跑 PV 函数，序列化沿用内层 | 1 | 1 | 1 | 4639 passed | 无违例，附带 JSON Schema 变化（§8） |
| `ok_up210` | 回移上游 2.10.0 的写法：内层顶层有 `serialization` 就用，否则用带 `return_schema` 的 wrap 委托内层 | 1 | 1 | 1 | 4639 passed | 无违例；A08 布局下 dump 有 2 条序列化警告 |
| `ok_post_attach` | `_apply_annotations` 生成完 schema 后，若外层没有 serializer，就把 PV 左侧的 serializer 依次套到最外层 | 1 | 1 | 1 | 4639 passed | 无违例 |
| `ok_pv_first_keep_sers` | “PV 挪到最内层”的正确写法：左侧只保留 serializer，放在 PV 紧外层；其余左侧元数据本来就被取代，直接丢掉 | 1 | 1 | 1 | 4639 passed | 无违例 |

`ok_up210` 的写法与 2.10.0 wheel（sha256 `5e7807ba…30fc`）中该段逻辑相同，只省略了 2.6 没有的 `json_schema_input_type`。

“PV 左侧的验证器绝不运行”会不会误拒合理修法：
- **合理实现不会运行左侧验证器**。这是文档直接写明的行为（§2.1）。合理实现只有两条路：
  - 不生成内层 schema，即排序类；
  - 只为序列化生成内层 schema，即委托类。

  生成 schema 不等于运行验证器，所以两条路都不会调用左侧验证器。私有矩阵中，8 个合理实现在以下各项全部通过：文档排序示例、Before/Wrap/After 在左、夹在中间的验证器、嵌套别名里的验证器。
- **会运行左侧验证器的写法另有错**：
  - `rv_pv_first` 让公开测试 `test_docs.py::test_docs_examples[docs/concepts/validators.md:137-263]` 失败；
  - `rv_before_sem_rebuilt`（按首轮描述重建）被 P2P `test_plain_validator_field_name` 拒。
- **v3 相对 v2 新拒的 2 个候选都是错的**：
  - 一个是 `rv_pv_first`；
  - 另一个是保守的部分修复 `bad_pv_first_if_only_sers`：只有 PV 左侧全是 serializer 才处理。它在题面布局前面多一个约束时就丢掉 serializer：`x: Annotated[int, ser, PV] = Field(gt=0)` 的元数据为 `[Gt, ser, PV]`，dump 得 `-5` 而不是 `'#-5'`；`Annotated[StrictBool, ser, PV]` 也不生效。

原则 1 的核对：v3 与 v4 的断言都只断言行为，不断言实现形状。
- 排序类、委托类、事后补挂类都能通过；
- `Other` 把 `WithJsonSchema` 放在 PV 之后，专门避免“PV 必须在最后”这类实现假设；
- 题面本身没有建议实现方式。

## 4. 我构造的候选及私有结果

全部是私有模拟评分。各测试版本的含义：
- `v3s`：只把第 5 项的源类型改为 `StrictBool`；
- `v3b`：首轮建议 1 的原样形式；
- `v4`：本复核的合并修法；
- `v4b03`：v4 再加 B03 一项，只作 §6 的决策数据，不建议采用；
- `v3f`：`= Field(strict=True)` 写法，31 个候选的结果与 `v3s` 逐一相同；
- `v3sx`、`v3sv2`：中间探索版本，已被 v4 取代。

| 候选 | 定性 | v2 | v3 | v3s | v3b | **v4** | v4b03 | 公开测试 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| noop | — | 0 | 0 | 0 | 0 | 0 | 0 | 与 base 相同 |
| gold | 参考解（D4 不作正对照） | 0 | 0 | 0 | 0 | 0 | 0 | — |
| `upstream261` | 替代正对照 | 1 | 1 | 1 | 1 | **1** | 0 | 作者已跑全量 |
| `c3_reorder` | 第二正对照 | 1 | 1 | 1 | 1 | **1** | 1 | 作者已跑全量 |
| `rv_condwrap` | 合理（首轮） | 1 | 1 | 1 | 1 | **1** | 0 | — |
| `ok_serdig`、`ok_wrapshim` | 合理（本复核） | 1 | 1 | 1 | 1 | **1** | 0 | 全量 4639 passed |
| `ok_up210` | 合理（上游 2.10 回移） | 1 | 1 | 1 | **0** | **1** | 0 | 全量 4639 passed |
| `ok_post_attach`、`ok_pv_first_keep_sers` | 合理（本复核） | 1 | 1 | 1 | 1 | **1** | 1 | 全量 4639 passed |
| `bad_nonvalidators_after_pv` | 错误（B1） | 1 | **1** | 0 | 1 | 0 | 0 | 全量 4639 passed |
| `bad_pv_first_skip_validators` | 错误（B1） | 1 | **1** | 0 | 1 | 0 | 0 | 全量 4639 passed |
| `bad_pv_first_skip_after` | 错误（B1） | 1 | **1** | 0 | 1 | 0 | 0 | 5 模块通过；docs 排序示例失败 |
| `c3_serpass` | 错误（B2；原 T3） | 1 | **1** | 1 | 0 | 0 | 0 | 作者已跑全量 |
| `bad_swap_nearest` | 错误（B2） | 1 | **1** | 1 | 0 | 0 | 0 | 全量 4639 passed |
| `bad_pv_before_first_ser` | 错误（B2） | 1 | **1** | 1 | 0 | 0 | 0 | 全量 4639 passed |
| `bad_swap_adjacent` | 错误（B2） | 1 | **1** | 1 | 0 | 0 | 0 | 全量 4639 passed |
| `rv_ser_to_end` | 错误（B3；首轮 N2，原 T3） | 1 | **1** | 1 | 1 | 0 | 0 | — |
| `bad_rewrap_noinfo` | 错误（B3） | 1 | **1** | 1 | 1 | 0 | 0 | 全量 4639 passed |
| `rv_pv_first` | 错误（首轮 N1） | 1 | 0 | 0 | 0 | 0 | 0 | docs 排序示例失败 |
| `bad_pv_first_if_only_sers` | 错误 | 1 | 0 | 0 | 0 | 0 | 0 | 5 模块与 docs 通过 |
| `rv_before_sem_rebuilt` | 错误（首轮，重建） | 0 | 0 | 0 | 0 | 0 | 0 | P2P 157/158 |
| 作者 9 个 `n_*` | 错误 | 0 | 0 | 0 | 0 | 0 | 0 | — |

说明：
- 除 `rv_before_sem_rebuilt` 外，所有运行都是 P2P 158/158、参考名单无缺席；
- “全量”指 `tests/`：4639 passed、196 skipped、7 xfailed，与 base 相同；
- “5 模块”指 validators、serialize、json_schema、annotated、types，共 1413 passed、6 skipped、2 xfailed；
- 各候选在 34 项行为上的通过情况见 `review_v3/out/matrix_table.md`。

我的错误候选在私有矩阵上的违例：

| 候选 | 违例（base 在这些项上都正确） |
| --- | --- |
| `bad_nonvalidators_after_pv`、`bad_pv_first_skip_validators` | 见表下说明 |
| `bad_pv_first_skip_after` | 同上两个的违例，再加：文档排序示例多出 before-1/2、wrap-1/2；PV 左侧的 Before/Wrap 被运行 |
| `bad_swap_nearest`、`bad_pv_before_first_ser` | 夹在 serializer 与 PV 之间的验证器被运行（含嵌套别名 `Annotated[Annotated[bool, ser, AfterValidator(check)], PV]`）；`[ser, Field(ge=0), PV]` 收 -3 报错；`[ser, Strict(), PV]` 类定义 `RuntimeError` |
| `bad_swap_adjacent` | serializer 与 PV 之间有任何元数据（验证器、`Field(ge=0)`、`WithJsonSchema`、`Strict()`、嵌套别名）时 serializer 不生效 |
| `bad_rewrap_noinfo` | 带 info 的 serializer 在 dump 时抛 `PydanticSerializationError`；PV 前的 `WrapSerializer` 不生效；PV 两侧都有 serializer 时用了内侧 |
| `bad_pv_first_if_only_sers` | PV 左侧除 serializer 外还有约束或验证器时 serializer 不生效，例如 `= Field(gt=0)` 默认值、`StrictBool` 别名 |

前两个候选的违例：
- `Annotated[StrictBool, PV]`、`= Field(strict=True)`＋PV 在类定义时抛 `RuntimeError`；
- `Annotated[PositiveInt, PV]`、`= Field(gt=0)`＋PV、`= Field(max_length=3)`＋PV 收违约值时报 `ValidationError`；
- 题面布局加约束同样出错：`Annotated[StrictBool, ser, PV]`、`= Field(gt=0)`＋`[ser, PV]`；
- `[ser, Field(ge=0), PV]`、`[ser, Strict(), PV]` 同样出错。

## 5. 阻断项

### B1（S1）：v3 放过把 PV 左侧约束挪到外层的写法

- **当前行为**：`bad_nonvalidators_after_pv`、`bad_pv_first_skip_validators`、`bad_pv_first_skip_after` 在 v3 下私有模拟得 1，P2P 158/158。
- **违反的公开要求**：
  - PV 取代内层验证，“Pydantic does not do any of its internal validation”（`validators.md:66`；docstring `:132`）；
  - base 在下列各例上的行为；
  - 首轮矩阵已把“`Annotated[StrictBool / StrictInt / PositiveInt, PlainValidator(...)]` 仍由 PV 接管”列为 base、gold 与两份正对照一致保留的旧行为。
- **证据**（私有矩阵，均为 base 的结果 → 这 3 个候选的结果）：
  - `Annotated[StrictBool, PlainValidator(lambda v: bool(int(v)))]`：`True` → 类定义时抛 `RuntimeError: Unable to apply constraint strict to schema function-plain`；
  - `z: Annotated[bool, PlainValidator(...)] = Field(strict=True)`：同上；
  - `Annotated[PositiveInt, PlainValidator(int)]` 收 `'-5'`：`-5` → `ValidationError`；
  - `z: Annotated[int, PlainValidator(int)] = Field(gt=0)`、`= Field(max_length=3)`：同样由通过变为 `ValidationError`；
  - 题面布局加约束：`Annotated[StrictBool, ser, PV]` 抛 `RuntimeError`，`x: Annotated[int, ser, PV] = Field(gt=0)` 报 `ValidationError`；
  - 公开测试拦不住：前两个候选的全量 `tests/` 都是 4639 passed，与 base 相同，连 docs 排序示例都通过。
- **影响（为什么是 S1，不是 T3）**：
  - 用 `= Field(...)` 写默认值是最常见的加约束方式，pydantic 会把这些约束排在 Annotated 元数据前面。实测 `x: Annotated[int, PV] = Field(gt=0)` 的 metadata 为 `[Gt(gt=0), PlainValidator(...)]`。所以“PV 左侧有约束”不需要特殊写法，也不需要 serializer；
  - 后果是类定义时崩溃，或验证结果改变，属于破坏有文档、常用的公开行为；
  - 判据与首轮 N1 相同（§4 第 4 步，D1 严格版），应判 S1；§5“已知相关错误候选仍为 0”不满足。
- **建议分期**：交第2类时必须修，已并入 v4。
- **文件与行号**：`rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v3.patch` 的第 5 项，应用后位于 `tests/test_validators.py:2868-2873`。
- **复现命令**：`review_v3/run_private.sh`，候选取 `bad_nonvalidators_after_pv`，测试版本取 `t_v3`；行为矩阵用 `review_v3/probe_matrix.py` 与 `probe_extra.py`。
- **修法**：把第 5 项的源类型 `bool` 改为 `StrictBool`，import 加 `StrictBool`。如果不想改 import，可以给该字段加默认值 `= Field(strict=True)`，两种写法等价：31 个候选的私有结果逐一相同。
- **修复验收条件**：
  - 这 3 个候选与 `rv_pv_first` 都在 `class Replaced` 定义处（v4 的 L2869）抛 `RuntimeError`，得 0；
  - 两份正对照、`rv_condwrap` 与 5 个合理实现仍为 1。

### B2：serializer 与 PV 之间还有别的元数据时（A08 布局），v3 放过 4 个错误候选

- **当前行为**：以下 4 个在 v3 下私有模拟均为 1：
  - `c3_serpass`、`bad_swap_adjacent`：serializer 不生效；
  - `bad_swap_nearest`、`bad_pv_before_first_ser`：把夹在中间的验证器或约束挪到 PV 外层，使它们生效。
- **违反的公开要求**：
  - 核心要求：serializer 放在 PV 前面也要生效（题面标题与期望，按一般性理解，见 result.md §1）。A08 就是 serializer 放在 PV 前，只是中间多一项元数据；
  - 中间那项验证器或约束按文档应被 PV 取代，依据同 B1。
- **证据**（私有矩阵）：
  - `[PlainSerializer(f'#{v}'), AfterValidator(...), PV(int)]`：`c3_serpass` 与 `bad_swap_adjacent` dump 得 `7`，应为 `'#7'`；另两个让中间的验证器被运行；
  - 嵌套别名 `Alias = Annotated[bool, ser, AfterValidator(check)]`，字段写作 `Annotated[Alias, PV]`：前两个丢掉 serializer，后两个运行了 `check`，而 base 不运行它；
  - `[ser, Field(ge=0), PV]`：`bad_swap_adjacent` 丢掉 serializer；后两个把 `Ge` 套到外层，收 -3 时报错；
  - `[ser, Strict(), PV]`：后两个在类定义时抛 `RuntimeError`。
- **影响**：serializer 不生效，就是题面症状原样重现；后两个还改变了验证结果。原先以“中间的验证器是死代码、写法罕见”登记 T3，按原则 2 不再以罕见为由放过。嵌套别名复用是这种布局的现实来源。
- **建议分期**：交第2类时必须修，已并入 v4。
- **修法**：在 v4 中加一个模型 `Between`：

  ```python
  class Between(BaseModel):
      w: Annotated[
          int, PlainSerializer(lambda v: v * 10), AfterValidator(lambda v: 1 / 0), PlainValidator(lambda v: int(v))
      ]

  between = Between(w='7')
  assert between.w == 7
  assert between.model_dump() == {'w': 70}
  ```

  serializer 故意返回与注解同类型的值（int）：
  - 首轮建议 1 用的是返回 str 的 serializer。`ok_up210` 在这种布局下，因 `return_schema` 与返回值类型不符而发出序列化警告，pytest 的 `filterwarnings = ['error']` 把警告变成失败，私有 v3b 中它得 0；
  - 那等于顺带考了“无警告”，与要检查的“serializer 被使用”无关。
- **修复验收条件**：
  - `c3_serpass`、`bad_swap_adjacent` 在 L2884 的 dump 处得 0，实得 `{'w': 7}`；
  - `bad_swap_nearest`、`bad_pv_before_first_ser` 在 L2882 的 `Between(w='7')` 处抛 `ZeroDivisionError`，得 0；
  - 8 个合理实现全部为 1，包括 `ok_up210`。

### B3：PV 两侧都有 serializer 时，v3 放过 2 个错误候选

- **当前行为**：`rv_ser_to_end`（首轮 N2）与 `bad_rewrap_noinfo` 在 v3 下私有模拟为 1。
- **违反的公开要求**：
  - base 行为：同一 Annotated 里，后面的 serializer 覆盖前面的。`Annotated[bool, ser('inner'), ser('outer')]` 得 `'outer'`，`[ser('inner'), PV, ser('outer')]` 也得 `'outer'`；
  - 题面期望“顺序不同，结果相同”：PV 放在哪里，不应改变用哪个 serializer。

  这两个候选在 `[inner, PV, outer]` 下都得 `'inner'`，是对 base 原本正确行为的回归。`bad_rewrap_noinfo` 还有两处违例：带 info 的 serializer 在 dump 时抛 `PydanticSerializationError`；PV 前的 `WrapSerializer` 不生效。
- **影响**：典型来源是别名覆盖。别名自带一个 serializer，字段处再加 PV 和新的 serializer，应以字段处（外层）的为准，这两个候选却用了别名里的旧 serializer。
- **建议分期**：交第2类时必须修，已并入 v4。
- **修法**：在 v4 中加一个模型 `Both`。它只锁定已有行为，base、gold 与全部合理实现都满足。

  ```python
  class Both(BaseModel):
      b: Annotated[bool, PlainSerializer(lambda v: 'inner'), validator, PlainSerializer(lambda v: 'outer')]

  assert Both(b='1').model_dump() == {'b': 'outer'}
  ```
- **修复验收条件**：这两个候选在 L2890 得 0，实得 `{'b': 'inner'}`；其余候选不变。

## 6. v3 放过的错误候选与已登记 T3 项：逐项判断（原则 2）

| 项 | v3 下得 1 的 | 违反公开要求？ | 处理 |
| --- | --- | --- | --- |
| 左侧约束被套到外层（B1） | 3 个 `bad_*` | 违反 | v4 修 |
| A08：serializer 与 PV 之间夹元数据（B2） | `c3_serpass` 与 3 个 `bad_*` | 违反 | v4 修 |
| PV 两侧都有 serializer（B3，首轮 N2） | `rv_ser_to_end`、`bad_rewrap_noinfo` | 违反（相对 base 回归） | v4 修 |
| A09 `WrapSerializer`；带 info 的 serializer | v4 下已没有得 1 的已知违例候选 | 违反这两项的已知候选是 `bad_rewrap_noinfo`、`n_const_str`、`n_order_registry`、`n_when_used_lost`、`n_bool_only`、`n_python_only`，v4 下都已为 0 | 不另加断言 |
| B03：生成不了 schema 的类型，serializer 放在 PV 前 | 正对照 `upstream261`，以及 `rv_condwrap`、`c3_serpass`、`ok_serdig`、`ok_up210`、`ok_wrapshim` | 严格说是核心要求的一个实例。这些实现的结果与 base 相同，serializer 不生效，但不是新回归 | 不断言，理由见表下 |
| B06：PV 字段引用运行时不存在的前向引用（例如只在 `TYPE_CHECKING` 下导入的名字）；N3：Python<3.12 的 `typing.TypedDict` | gold、`upstream261` 及其它在 PV 内委托内层 schema 的实现 | 违反“PV 取代内层验证”这一要保护的行为，相对 base 回归，但这是正对照 `upstream261` 自身的已知回归（作者与首轮已复现，我未另行复现） | 不断言：断言就得先放弃 `upstream261` 作正对照，理由同 B03。交接时写明它在这两类输入上不能当参考 |
| A16/A17：serializer 在类型参数里，或源类型自带 serializer | `c3_reorder`（正对照）不保留 | 不违反本题公开要求，理由见表下 | 不断言 |
| B07/B08：没有 serializer 时的序列化 | `upstream261` | 不违反：按注解类型序列化与 `serialization.md:393-396` 一致；base 按运行时推断，也说得通 | 不断言 |
| B11：装饰器 `field_validator(mode='plain')` | 全部版本（含 base） | 不在题面范围：题面讲的是 Annotated 中的 `PlainValidator` 类 | 不断言 |
| A18：serialization 模式的 JSON Schema | `c3_reorder` 由报错变为 `string` | 不违反，属附带改进（首轮已认） | 不断言 |

B03 不断言，理由不是“少见”：
1. D4 与 §5 要求新断言必须被经核实的正对照通过。`upstream261` 是上游 2.6.1 到 2.10 各正式版的修法，也是本题两份正对照之一，它在 B03 上与 base 相同。
2. B03 与要保护的旧行为“PV 能接管生成不了 schema 的类型”直接冲突。serializer 的 schema 要建在源类型的 schema 之上；源类型生成不了时，只改 PV 的委托类实现拿不到这个 serializer，要拿到还得另改 serializer 的 schema 生成。私有 v4b03 中，8 个合理实现有 5 个因此得 0，只剩在注解层处理的 3 个（`c3_reorder`、`ok_post_attach`、`ok_pv_first_keep_sers`）。断言 B03 等于把“在注解层而不是在 PV 内修”定为唯一路线，违反原则 1。
3. 若协调者仍要求覆盖 B03，正对照只能保留 `c3_reorder`，各候选的预期结果见 `review_v3/out/summary.txt` 的 `t_v4b03` 列。

A16/A17 不违反本题公开要求的理由：
- 题面与标题讲的是同一个 Annotated 里 `PlainSerializer` 与 `PlainValidator` 的先后；
- 源类型自身的序列化在 PV 下是否保留，base 从未做到，文档也没有承诺；
- 断言它等于把 gold 的“委托内层 schema”定为唯一答案（原则 1）。

## 7. 交第2类时必须一并修的项与停止条件（原则 3）

**必须一并修的项**：全部在唯一的 F2P 测试体内，测试 ID、F2P/P2P 名单与测试命令都不变。
1. B1：第 5 项的 `bool` 改为 `StrictBool`，import 加 `StrictBool`；或改用等价的 `= Field(strict=True)` 写法。
2. B2：新增 `Between`。
3. B3：新增 `Both`。

三项合在一起就是 `rh2/experiments/category3_cloud_20260929/pydantic8567/review_v3/tests/t_v4.patch`，sha256 `7014f5fc7f017bc025b9de2420e71e5253ee7fad6ab6cdbb55ffa0e42493b86e`。它相对 v3 只改这三处。父版本 v3（`4600867b…`）与触发反例一并留档：B1 3 个、B2 4 个、B3 2 个。

**修后预期**：v4 私有模拟结果如下，正式诊断评分应逐项复现。

| 结果 | 候选 | v4 失败位置 |
| --- | --- | --- |
| 1 | `upstream261`、`c3_reorder`、`rv_condwrap`、`ok_serdig`、`ok_wrapshim`、`ok_up210`、`ok_post_attach`、`ok_pv_first_keep_sers` | — |
| 0 | noop | L2827 `isinstance(data['bar'], ser_type)` |
| 0 | gold | L2860 `class WithUnsupported`，抛 `PydanticSchemaGenerationError` |
| 0 | `n_const_str` / `n_python_only` / `n_field_only` | L2832 / L2833 / L2838 |
| 0 | `n_order_registry`、`n_when_used_lost` / `n_bool_only`、`n_noinfo_only`、`n_two_items` | L2852 / L2853 |
| 0 | `n_swallow_to_any` | L2864 `isinstance(m.u, Unsupported)` |
| 0 | `rv_pv_first`、`bad_nonvalidators_after_pv`、`bad_pv_first_skip_validators`、`bad_pv_first_skip_after` | L2869 `class Replaced`，抛 `RuntimeError`（strict） |
| 0 | `bad_pv_first_if_only_sers` | L2874，实得 `{'z': True}` |
| 0 | `bad_swap_nearest`、`bad_pv_before_first_ser` | L2882 `Between(w='7')`，抛 `ZeroDivisionError` |
| 0 | `c3_serpass`、`bad_swap_adjacent` | L2884，实得 `{'w': 7}` |
| 0 | `rv_ser_to_end`、`bad_rewrap_noinfo` | L2890，实得 `{'b': 'inner'}` |
| 0 | `rv_before_sem_rebuilt` | P2P `test_plain_validator_field_name` 失败（157/158）；F2P 在 L2872 抛 `ZeroDivisionError` |

**停止条件**：
1. **只跑一次正式诊断评分**。作者按 `t_v4.patch` 原文生成 v4 材料，跑一次正式诊断评分（`--materials`）。候选至少包括：noop、gold、两份正对照、`rv_condwrap`、`c3_serpass`、`rv_ser_to_end`、`rv_pv_first`、9 个 `n_*`，以及我的 7 个触发反例（B1 的 3 个、B2 的 `bad_swap_adjacent`、`bad_swap_nearest`、`bad_pv_before_first_ser`、B3 的 `bad_rewrap_noinfo`）。补丁在 `review_v3/cands/`。
2. **全部一致就交接**。reward 与失败位置全部与上表一致，且 P2P 158/158、参考缺席 0、安装 rc 0、清理成功，即算 v4 验收通过，直接交第2类，不再开复核轮次。本复核对 `t_v4` 的判断就是聚焦复核结论；Codex 复核照规定另做。
3. **有不一致只查不一致本身**。先比私有与正式的条件差异（UID 54322、派生镜像），不因此新增断言。一轮内解决不了，按标准 §7.2 记 conditional。
4. **明确不再追加断言的项**：B03、B06/N3、A16/A17、B07/B08、B11、A18，以及单独针对 A09 和带 info serializer 的断言，理由见 §6。以后再出现得 1 的新错误候选，按标准 §8 的抽查处理，不回到本轮。

## 8. 非阻断建议

1. **result.md 需同步更新**：
   - 顶部状态与 §4 的 v3 验收表：“已知错误候选为 0”在 v3 下不成立；
   - §5 的 T3 清单：A08 与 N2 改为已修项；补一条合并 B06 与 N3 的条目，写明它是 `upstream261` 的已知回归；按 §6 更新 B03 的依据；
   - §6 交接用的版本改为 v4；
   - §8 的未做事项。
2. **`ok_wrapshim` 只作过严检查的探针，不宜作正对照**。它把 PV 字段在 validation 模式下的 JSON Schema 由报错改成了内层类型，而 `docs/concepts/json_schema.md:589-590` 写明 PV 会报错、需用 `WithJsonSchema` 覆盖，属附带行为变化。
3. **`ok_up210` 在 A08 布局下有序列化警告**：serializer 改变类型时会出警告，上游 2.10 本身如此，v4 的 `Between` 已避开。以后再加涉及“serializer 改变类型，且中间有包层元数据”的断言，要先用 `ok_up210` 试一遍。
4. **我的 `review_v3/out/` 未入库**：约 5.5 MB、741 个文件，多为 pytest 输出，被 `*/review*/out/` 规则忽略。需要留证时，用 `archive_evidence.py` 登记摘要即可。
5. **过程**：本复核没有提交任何文件。`review_v3/` 下的脚本与补丁已被负责人会话的快照提交一并纳入（945d39cf、c232db7a、521a5856、c2499125、f9f93f67），与本地当前内容一致；`review_v3.md` 写完时尚未提交。

## 9. 未查事项

- **只有私有模拟，没有正式评分**：我的 14 个候选（`ok_*`、`bad_*`、`rv_before_sem_rebuilt`），以及测试版本 v3s、v3f、v3sx、v3sv2、v3b、v4、v4b03，都只有私有模拟评分。私有与正式在已有的 23 次运行上逐项一致，但 v4 仍需按 §7 跑一次正式诊断评分。
- **没在正式评分条件下跑**：没用 grader profile（UID 54322、2 CPU/4 GiB）、派生镜像或非 root 身份。新断言不涉及文件、权限和网络，预计不受影响，但未验证。
- **只查了 Python 3.8.19**：没查其它 Python 版本，例如 N3 的 `TypedDict` 在 3.12 上的差异。
- **公开测试覆盖面**：全量公开测试只跑了 12 个候选；另有 15 个候选跑了相关 5 个模块与 docs 示例；其余候选只有私有模拟。
- **没有真实模型解**。
- **没有重看全部历史**：没重看 v1、v2 的修订过程与 09-29 的全部 evidence，只核了与 v3 相关的账本、清单和派生镜像记录。
- **上游 wheel**：没有重新核对 2.6.1、2.8.0 wheel（首轮已核），只下载核对了 2.10.0 wheel 中 `PlainValidator` 的写法。
- **`rv_before_sem` 是重建件**：按首轮描述重建为 `rv_before_sem_rebuilt`，无法与首轮原件比对哈希。

## 10. 文件与复现

目录：`rh2/experiments/category3_cloud_20260929/pydantic8567/review_v3/`

| 文件 | 内容 |
| --- | --- |
| `make_candidates.py` → `cands/` | 在 base 上逐字替换，生成本复核 14 个候选补丁 |
| `make_tests.py` → `tests/` | 生成测试版本：t_v2、t_v3、t_v3s、t_v3f、t_v3sx、t_v3sv2、t_v3b、t_v4、t_v4b03 |
| `probe_matrix.py`、`probe_extra.py`、`probe_base_facts.py` | 私有行为矩阵（34 项）与 base 事实核对 |
| `run_private.sh`、`run_probe_only.sh` | 私有模拟评分与行为矩阵 |
| `run_public.sh`、`run_full.sh` | 相关 5 个模块加 docs 示例；全量 `tests/` |
| `summarize.py`、`matrix_table.py` | 汇总到 `out/summary.txt`、`out/sim/summary.json`、`out/matrix_table.md` |

复现方法：在 `review_v3/` 目录下运行下面的命令。启动前先等待容器数量低于 3。gold 补丁取自 `evidence/gold/pydantic__pydantic-8567.gold.patch`（sha256 `86200100…`），先复制到任一目录并改名为 `gold.patch`，再把该目录挂载为 `/gold`。

```bash
docker run --rm --network none -v $PWD:/rv -v $PWD/..:/p8567:ro -v <gold 所在目录>:/gold:ro \
  c3keep/pydantic8567:src bash /rv/run_private.sh /rv/out/sim t_v3,t_v4 upstream261 c3_reorder bad_nonvalidators_after_pv
python3 summarize.py out/sim ../../../../../docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl
```
