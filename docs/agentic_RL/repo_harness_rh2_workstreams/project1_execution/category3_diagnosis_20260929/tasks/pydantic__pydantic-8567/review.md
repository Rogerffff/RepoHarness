# pydantic__pydantic-8567 独立复核

2026-09-29，独立复核者（不继承作者上下文）。

**总判断：`upstream261` 与 `c3_reorder` 都可以作正对照（各有已登记的范围差异，不影响 v2 的判分）。作者处置部分同意：原版 S1、gold 失败记录、v2 四组断言的依据与不过严、`c3_serpass` 记 T3，均同意；但 v2 会放过一个违反文档公开行为的错误候选 `rv_pv_first`（得 1），不满足 §5“已知相关错误候选仍为 0”，需补一处断言后重跑修订验收，这是唯一阻断项。**

初判先于读作者材料封存：[review_initial.md](review_initial.md)，sha256 `09af2c13…f17dd45`。注意：该文件已被另一进程的提交 `d7afdce`（dask-8801 作者诊断）一并提交，不是我提交的；内容与本地一致。

## 1．复核怎么做的

- **环境**：镜像 `c3keep/pydantic8567:src`（image ID `abbc218b…`，与原镜像同 ID），一次性容器，root，`--network none`；每个候选前 `git checkout -- pydantic tests` 复位。`/testbed` editable 导入，pydantic 2.6.0a1、core 2.15.0。
- **没做的**：没跑正式评分；没在 grader profile（UID 54322、2CPU/4GiB）或作者的等效派生镜像上跑测试，派生镜像只核了身份与内容。
- **私有模拟判分**：在容器里套用 test_patch，用 bundle 里的 `eval_cmd` 跑 `tests/test_validators.py`，按 grading bundle 的参考名单（F2P 1 个、P2P 158 个）逐名判分。
- **候选**：base、gold、`upstream261`、`c3_reorder`、`c3_serpass`、作者 9 个 `n_*`，另加我自己构造的 4 个：

  | 我的候选 | 做法 | 定性 |
  | --- | --- | --- |
  | `rv_pv_first` | 在 `_apply_annotations` 里把最后一个 `PlainValidator` 挪到元数据最内层（`[annotations[i]] + annotations[:i] + annotations[i+1:]`） | **错误**：原本在 PV 左侧、按文档不应运行的验证器和约束，变成包在 PV 外面运行 |
  | `rv_before_sem` | 内层 schema 生成成功时，PV 退化成“先跑函数、再跑内层验证”（before 语义） | **错误**：破坏 PV 的短路 |
  | `rv_ser_to_end` | 把 PV 前面的 serializer 移到**整个列表末尾**，而不是 PV 紧后 | 边缘：只改变 PV 两侧都有 serializer 时谁生效 |
  | `rv_condwrap` | PV 内 `try: handler(source_type)`；仅当内层 schema 任意位置带 `serialization` 时，才用 `wrap_serializer(lambda v, h: h(v), schema=inner)` 委托，否则不改 | **合理**，与两份正对照机制都不同 |

  以上脚本和补丁按限制只放在会话 scratchpad，不入库。sha256：`rv_pv_first.patch` `a702262a…`、`rv_before_sem.patch` `807828bf…`、`rv_ser_to_end.patch` `7584281b…`、`rv_condwrap.patch` `b9b19883…`、行为矩阵 `matrix.py` `db89909f…`、`matrix2.py` `0fd20f1f…`。关键改动已在上表写明，可按描述重建。

## 2．两份正对照的核实

### 2.1 是否满足题面

两份正对照在下列题面核心实例上都与 gold 输出一致（我的行为矩阵，逐项实跑）：

- 题面原例：内部值 `False/True`，`model_dump()`、`model_dump(mode='json')`、`model_dump_json()` 都是 `'0'/'1'`；
- 非示例：int 与 `x * 10`、两种顺序；
- 带 info 的 PV；`when_used='json'`；`TypeAdapter(List[...])`；pydantic dataclass 字段；`TypedDict` 字段；泛型模型；
- serializer 与 PV 之间夹 `Field(description=...)`、`Gt(0)`、`Strict()`、`WithJsonSchema`；
- 源类型为模型、Enum、`List[int]`、`Dict`、`Decimal`、`Optional`（`unless-none`）、`Union`、`Literal`、`UUID`、`date`；
- 带 info 的 serializer；递归模型；两个 PV 叠加。

### 2.2 是否保留相关旧行为

| 旧行为 | base | gold | `upstream261` | `c3_reorder` |
| --- | --- | --- | --- | --- |
| 未知类型 + PV（默认配置）能建类、保留对象、python dump 为原对象 | 是 | **类定义报错** | 是 | 是 |
| 文档 `validators.md:137-263` 的验证器排序示例（PV 左侧的验证器不运行） | 一致 | 一致 | 一致 | 一致 |
| `Annotated[StrictBool / StrictInt / PositiveInt, PlainValidator(...)]` 仍由 PV 接管 | 是 | 是 | 是 | 是 |
| 短路：`Annotated[int, PlainValidator(lambda v: v)]` 收 `'abc'` | `'abc'` | 同 | 同 | 同 |
| PV 两侧都有 serializer 时外层生效 | `'B'` | 同 | 同 | 同 |
| `@field_serializer` 优先于 Annotated serializer | 是 | 是 | 是 | 是 |
| `tests/test_serialize.py` | 75 passed | 75 | 75 | 75 |
| `tests/test_docs.py` 中 validators/serialization/json_schema 三页示例 | 49 passed | 49 | 49 | 49 |

`test_docs.py` 需要 `ruff`：它在 `/opt/miniconda3/envs/testbed/bin`，不在 `docker exec` 的默认 PATH 里，第一次跑时 50 个全部因找不到 `ruff` 失败；加上该目录后才是上表的结果。

### 2.3 与 base 的差异（都属 T3 或范围外，不影响作正对照）

- **`upstream261`**：
  - 未知类型且 serializer 在 PV 前（作者 B03）：serializer 仍被忽略，和 base 一样；
  - PV 字段引用从未定义的前向引用（作者 B06）：模型变成不完整。我已复现，`class-not-fully-defined`；
  - **作者没列的同族项**：Python 3.8 上 `Annotated[typing.TypedDict 子类, PlainValidator(...)]`，内层抛的是 `PydanticUserError`（`typed-dict-version`），不在 `except PydanticSchemaGenerationError` 范围内，类定义失败；base 可用。gold、`c3_serpass`、`rv_condwrap` 同样失败，`c3_reorder` 不受影响。罕见写法，建议并入 T3 登记；
  - 无 serializer 时按注解类型序列化（作者 B07/B08）：validator 返回类型不符时，每次 dump 多出序列化警告（公开旧测试 `test_plain_validator_field_name` 的模型 dump 时也会出 1 条）；返回子类模型时丢掉子类字段。后者与 `docs/concepts/serialization.md:393-396` 写明的 v2 默认规则一致（按注解类型序列化子类实例），同意不断言。
- **`c3_reorder`**：
  - 只处理同一扁平 Annotated 列表里的 `PlainSerializer`/`WrapSerializer`；
  - serializer 在内层类型里时不修：`TypeAliasType` 别名、`Optional[Annotated[bool, ser]]`、类型参数（作者 A16）、源类型自带（作者 A17）；
  - 它反而修好了未知类型 + serializer 在前（B03），也不受 B06、B19 影响；
  - 对 `[ser, PV]` 的 serialization 模式 JSON Schema 由报错变为 `string`，与 `[PV, ser]` 顺序一致，属附带改进。

### 2.4 是否合理修法

- **`upstream261`**：方法体与 PyPI pydantic 2.6.1 wheel 逐字相同。我自己下载了该 wheel，sha256 `0b6a909d…bae6f` 与作者记录一致，changelog 含 `Fix unsupported types bug with PlainValidator (#8710)`。2.8.0 wheel 中该方法与 2.6.1 逐字相同；2.10.0 改写，但保留同一个 `except PydanticSchemaGenerationError: serialization = None` 边界。它是上游多个正式版实际发布的修法，合理。
- **`c3_reorder`**：改动在公共组合函数里，但只移动 serializer 类元数据，保持 serializer 之间、验证器之间各自的相对顺序。作者的全量测试 4639 passed，我抽读了 5 份输出一致。它在题面范围内没有找到反例，合理。

两份都能作 D4 所说“经独立核实的替代正对照”。交接时需带上 §2.3 的差异清单，以免把某一份的输出当成其它输入的期望值。

## 3．修订测试 v2 的核实

### 3.1 依据与是否过严

| v2 断言 | 依据 | 是否过严 |
| --- | --- | --- |
| 原例内部值与 Python/JSON 精确值 | 题面示例与“两种顺序结果相同” | 不过严：JSON 紧凑格式是 pydantic 默认，所有合理实现一致 |
| `TypeAdapter(List[Annotated[...]])` | 文档演示 Annotated 可嵌套进 `List`；类型复用 | 不过严 |
| `Other`：int、`when_used='json'`、带 info 的 PV、其后 `WithJsonSchema` | serialization.md 的 `when_used`；PV 的两种签名；非示例实例 | 不过严：`WithJsonSchema` 在 PV 之后是常见写法，只拒“要求 PV 在最后”的窄修 |
| 未知类型 + PV 能建类、验证、python dump 为原对象 | PV docstring “instead of the inner validation”、`validators.md:66`；base 行为；上游 #8710 回归测试形态相同 | 不过严：serialization 为 None、any、is-instance 等合理回退都满足 |

`rv_condwrap`（与两份正对照机制不同的合理实现）在 v2 下得 1，没有发现误拒。

### 3.2 v2 私有模拟判分（本人实跑，参考名单逐名判）

| 候选 | v2 | 备注 |
| --- | --- | --- |
| base | 0 | 停在原 `isinstance` 断言 |
| gold | 0 | 停在 `class WithUnsupported`（`PydanticSchemaGenerationError`） |
| `upstream261`、`c3_reorder`、`c3_serpass` | 1 | P2P 158/158 |
| 作者 9 个 `n_*` | 全 0 | P2P 158/158，与正式失败位置一致 |
| `rv_before_sem` | 0 | 被 P2P `test_plain_validator_field_name` 拒 |
| `rv_condwrap` | 1 | 合理实现，正确放行 |
| **`rv_pv_first`** | **1** | **错误候选被放过**，见 §4 N1 |
| `rv_ser_to_end` | 1 | 边缘，见 §4 N2 |

### 3.3 `c3_serpass`：T3 还是 S1

同意作者记 **T3**。实测它只在 serializer 与 PV 之间夹着**验证器**时漏修：

- 漏修：`AfterValidator`、`WrapValidator` 夹在中间；嵌套别名 `Annotated[Alias, PV]`，其中 `Alias = Annotated[bool, ser, AfterValidator(...)]`；
- 不漏：夹 `Field(description=...)`、`Gt(0)`、`Strict()`、`WithJsonSchema` 时正常，因为这些 metadata 不会把 schema 包一层；
- 源类型、入口、模式等其它维度都与正对照一致。

夹在中间的验证器被 PV 取代、本来就不运行（`validators.md:66` 与排序示例），属死代码写法；现实里主要来自嵌套别名复用。它确实是“serializer 放在 PV 前”的实例，但走的是罕见路径，按 §4 第 4 步记 T3 合理。

若想顺手覆盖，有一个便宜的可选断言，见 §5 非阻断 1。

## 4．反例与新问题

**N1（阻断）`rv_pv_first` 在 v2 下得 1，但破坏有文档的公开行为。**

- **违反的公开要求**：`docs/concepts/validators.md:66` 写明 PV “terminate validation immediately, no further validators are called”；`validators.md:137-263` 的排序示例写明 PV 左侧的 before/after/wrap 验证器不运行。
- **实测后果**：
  - 该示例输出多出 `before-1/2`、`wrap-1/2`、`after-1/2`；
  - 公开测试 `test_docs.py::test_docs_examples[docs/concepts/validators.md:137-263]` 失败，gold、两份正对照、`c3_serpass`、`rv_condwrap` 都通过；
  - `Annotated[StrictBool, PlainValidator(...)]`、`Annotated[StrictInt, PlainValidator(...)]` 在**类定义**时抛 `RuntimeError: Unable to apply constraint strict to schema function-plain`；
  - `Annotated[PositiveInt, PlainValidator(...)]` 收 `-5` 由通过变成 `ValidationError`。
- **为什么 v2 放过**：v2 与全部 158 个 P2P 都没有把任何 metadata 放在 PV 左侧；`test_validators.py` 里的 PV 用例只有单个 PV。
- **严重度**：`StrictBool`、`PositiveInt` 这类 pydantic 自带别名就是“`Annotated[..., 约束]`”，作为 PV 的源类型并不罕见。它与作者据以把 gold 回归判 S1 的是同一项 PV 能力（取代内层验证）；它是回归，不是漏修。按 §4 第 4 步（D1 严格版）属 S1，按 §5 验收属“已知相关错误候选”。
- **修法已验证**（scratchpad 草案 `v3probe_test.patch`，sha256 `1147237b…`）：在 v2 测试体末尾追加

  ```python
      # Metadata placed before the plain validator is still replaced by it (documented ordering of validators):
      # an inner validator is not called, while the serializer is still used.
      class Replaced(BaseModel):
          z: Annotated[bool, AfterValidator(lambda v: 1 / 0), serializer, validator]

      replaced = Replaced(z="1")
      assert replaced.z is True
      assert replaced.model_dump() == {"z": "1"}
  ```

  私有模拟结果：
  - 得 0：base、gold（仍只停在未知类型处）、`rv_pv_first`（停在这段新断言，`ZeroDivisionError`）、`rv_before_sem`、作者 9 个 `n_*`；
  - 得 1：`upstream261`、`c3_reorder`、`c3_serpass`、`rv_condwrap`；
  - `AfterValidator` 已在该文件导入，无需改 import。

  另一种等价做法是把上面那个现成公开文档测试加入 P2P。但它在 `tests/test_docs.py`，要改评分命令，还依赖 `ruff` 在 PATH 上，成本更高，不推荐。

**N2（非阻断，T3）`rv_ser_to_end` 得 1。** 它只在 PV 两侧都有 serializer 时让内侧那个生效（`[ser(A), PV, ser(B)]` 输出 `'A'`，其余版本都是 `'B'`）。写法罕见，建议登记。

**N3（非阻断，T3）`upstream261` 的异常捕获范围窄。** 见 §2.3：`typing.TypedDict`（Python<3.12）与从未定义的前向引用，建议与作者 B06 合并为一条：“内层 schema 生成抛非 `PydanticSchemaGenerationError` 时类定义失败”。

**N4（过程）** 我的 `review_initial.md` 被他人提交 `d7afdce` 一并提交。它不属于该提交的任务路径，提请协调者留意提交范围。

## 5．逐条主张核对表（作者 result.md）

| # | 作者主张 | 核对方式 | 结论 |
| --- | --- | --- | --- |
| 1 | gold 让“未知类型 + PV”在类定义时抛 `schema-for-unknown-type` | 实跑 | 属实 |
| 2 | 原材料正式评分：noop 0、gold 1、`upstream261`/`c3_reorder`/`c3_serpass` 1、9 个 `n_*` 全 1 | 读 `evidence/formal_summary.json` 共 41 条；另从 `formal_revised_v2/eval_logs` 原日志逐名重数 6 次运行的 F2P/P2P | 属实；全部 `ref_missing` 0、install rc 0、cleanup true、image `2b170da8…` |
| 3 | v1 正式评分共 13 次，不含 `n_field_only` | 同上 | 属实 |
| 4 | v2 正式评分：noop 0；gold 0（停在 `WithUnsupported`）；两份正对照与 `c3_serpass` 1；9 个 `n_*` 全 0，各停在为它设计的断言 | 同上，并核 `audit_upstream261/materials.json` 的 `revised_patch_sha256` 为 `6cff9609…`，与我使用的 v2 相同；我的私有模拟逐项一致 | 属实 |
| 5 | 私有模拟与正式评分在 v1、v2 全部候选上逐项一致 | 读 `simgrade_v2.log` | 属实。该日志的值是 pytest 退出码（0 = 通过），不是 reward，读时别弄反 |
| 6 | “修订断言对两种设计都成立，说明不是照 gold 机制写的” | 第三种合理设计 `rv_condwrap` 也得 1 | 属实；但“错误候选全 0”只对作者自己的 9 个成立，见 N1 |
| 7 | `upstream261` = gold + 2.6.1 的异常捕获，方法体与 2.6.1 wheel 逐字相同；2.6.4/2.7.0/2.8.0 同；2.10.0 改写但保留同一 catch | 自行下载 2.6.1、2.8.0、2.10.0 wheel 比对；2.6.4、2.7.0 未核 | 已核部分属实 |
| 8 | 上游 2.6.1 新增 `test_plain_validator_with_unsupported_type`，别名名为 `PreviouslySupportedType` | 读作者存档 `upstream_2.6.1_test_diff.txt`；原始 raw 文件未重新下载 | 存档内容与描述一致；未独立重取 |
| 9 | 派生镜像是等效重建、不是 09-19 原版逐字节重建 | 核实见下列 | **说明诚实** |
| 10 | 全量 `tests/`：5 个版本都是 4639 passed，0 failed | 读 `fulltests_v1/*/f1_full_tests.out` | 属实（含 docs 示例测试） |
| 11 | 相关 5 个模块对 14 个版本都是 1413 passed | 未核；我只跑了 `test_serialize.py` 与三页 docs 示例 | 未核 |
| 12 | T3 登记 A08（夹验证器） | 实测，见 §3.3 | 同意 |
| 13 | T3 登记 A09 `WrapSerializer` | 各正对照都修好了 | 同意 |
| 14 | T3 登记 A16/A17（serializer 在类型参数或源类型里） | 实测 `TypeAliasType`、`Optional[Annotated[...]]` 两例同样只有 gold/`upstream261` 修 | 同意，属“注解顺序”之外 |
| 15 | T3 登记 B03（未知类型 + serializer 在前） | 实测 | 同意。它严格说是核心要求的一个实例，但上游 2.6.1 到 2.10.0 都保留这一边界，且要同时满足“无 schema 的类型”和“serializer 在前”两个条件，属边缘组合；强行断言会拒掉上游正式修法 |
| 16 | T3 登记 B06（从未定义的前向引用） | 实测 | 同意；建议并入 N3 |
| 17 | T3 登记 B07/B08（无 serializer 时的序列化差异） | 实测 B07 | 同意，理由见 §2.3 |
| 18 | T3 登记 B11（`field_validator(mode='plain')`） | 未实测 | 在题面（Annotated）之外，同意不断言 |
| 19 | 原版 S1（第 1–4 步） | 对照原 test_patch 与作者 9 个候选的正式结果 | 同意 |

第 9 项派生镜像的核实结果：

- 实际 `RootFS.Layers` 前 13 层与原镜像逐项相同，只多 1 层；
- 容器内 8 个 wheel 的 sha256 与 `derived_image.json` 一致；
- 环境变量含 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS`；
- 配方文本与 `rh2/experiments/env_recipe_repair_20260919/run_pydantic.py:20` 逐字相同；
- wheel 集合与 pydantic-9066 的 `derived_image.json` 相同；
- recipe sha256 `f013894e…` 与 09-19 配方文件一致；
- 09-19 原 wheel 清单不在本仓库，“与原版等效”无法逐项核对，作者已如实写明。

## 6．阻断项与非阻断建议

**阻断项（1 项）**

1. v2 不满足 §5“已知相关错误候选仍为 0”：`rv_pv_first` 得 1（N1）。需把 N1 中那段断言并入 F2P 测试体，形成新版本，再对 noop、gold、两份正对照、`c3_serpass`、作者 9 个 `n_*` 和 `rv_pv_first` 重跑修订版评分。预期结果见 N1 的私有模拟。父版本 v2 与触发反例 `rv_pv_first` 一并留档。

**非阻断建议**

1. **可选**：把 N1 的 `AfterValidator` 放到 serializer 与 validator 之间（`Annotated[bool, serializer, AfterValidator(lambda v: 1 / 0), validator]`）。这样一条断言同时覆盖 N1 与 A08。私有模拟：`upstream261`、`c3_reorder`、`rv_condwrap` 得 1，`c3_serpass`、`rv_pv_first`、gold 得 0（scratchpad `v3between_test.patch`，`45957cf5…`）。这会把 A08 从 T3 升为有断言，由作者或协调者决定。
2. T3 登记补上 N2（`rv_ser_to_end`）和 N3（`typing.TypedDict` 同族），并把行为矩阵里的“文档验证器排序”一项补进错误候选集，避免以后同类重排候选再漏检。
3. 交接第2类时带上 §2.3 的正对照差异清单；`upstream261` 的上游来源已由复核者独立核对 PyPI wheel。
4. 若按作者建议把未知类型检查拆成独立 P2P，同样适用于 N1 的断言，可拆成“PV 仍取代其左侧元数据”一项。
5. 若以后用 `test_docs.py` 做相关检查，运行环境要把 `/opt/miniconda3/envs/testbed/bin` 放进 PATH，否则会全部因缺 `ruff` 失败，不能当作候选错误。
