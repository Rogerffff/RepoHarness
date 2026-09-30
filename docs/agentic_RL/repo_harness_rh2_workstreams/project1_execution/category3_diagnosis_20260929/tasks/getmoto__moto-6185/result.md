# getmoto__moto-6185：第3类诊断结果

2026-09-29 / Claude（云端，第3类第二批主审）。原分类：第3类“已有具体疑点，缺辨别实验”。登记的下一步是：先对合法嵌套值做 base／gold 的 Put/Get 对照，再处理实际失败。

> **当前状态（09-30 更新）**
>
> - **全部运行已在云端重做并归档**（证据在 [evidence/](evidence/)）：
>   - 派生镜像按 install_wave1 配方重建，三个 wheel 的 SHA256 与登记值逐一相同；
>   - 私有行为矩阵 14 个版本 × 44 个场景：§3.1 行为表 154 格与重跑结果逐格一致；
>   - 正式评分 42 次（原材料、v2、v2s 各 14 次）：与私有模拟评分逐项一致，见 §3.2 与 §5。
> - **作者结论经重跑证实**：原版 S1（6 个错误或部分修复候选正式得 1）、没有误拒、v2 下 gold 与两份附加正对照为 1、错误候选为 0。
> - **还差**：独立复核（重点见 §7），以及 `ctx`、`parity` 作附加正对照的他人核实。

**结论：问题和修法已明确，建议转第2类。** 独立复核尚未进行。

1. **辨别实验的结果：原先怀疑的“gold 漏修深层合法值”，在普通主键名下不成立。** gold 对题面两例（顶层、嵌套 `None`）、字符串值、两层嵌套、list 内 map、batch／transact 入口都能写入并等值读回。旧题卡的两条静态推断都已实测坐实，但只在少见路径上出现，登记为 T3／S2（§4）：
   - 主键（HASH 或 RANGE）**名为 `M`** 的表上，嵌套属性 `S` 仍报 `SerializationException`；
   - 关闭 SDK 参数校验后，非主键属性的 `S` 值为 dict 时，gold 抛内部 `AttributeError`，base 抛的是 `SerializationException`。

   上游到 5.2.3 仍是 gold 的写法（PyPI 对照，仅作佐证）。
2. **原测试真正的问题是漏检，不是误拒。** 题面例 2（嵌套 `S`）没有任何断言，以下两类错误实现在原材料正式评分下都得 1：
   - 只修一部分的实现：`top_only`（只修顶层）、`siblings`（单键 dict 当类型标签）、`depth2`（只修一层嵌套）、`list_as_names`（修复时把 list 内 map 改坏）；
   - 吞掉错误的实现：`swallow`、`skip_s_subtree`。在含属性 `S` 的条目上，它们放过公开测试保护的“非主键 N 给整数”错误，并把错误数据存入。

   判 S1（T2a＋T2b）。
3. **修法 R-c v2**：在原 F2P 函数内追加断言，测试 ID 与命令都不变。gold 仍作正对照；另有两份与 gold 写法不同的合理实现 `ctx`、`parity` 在原材料和 v2 上都得 1（本人所写，待他人核实）。
4. **严格备选 v2s**：在 v2 之外再断言上述两个 gold 缺口，gold 因此为 0，正对照改用 `ctx`。只有复核把这两个缺口判为 S1 时才用，评分数据已备好（§5）。
5. 没有发现误拒：三份与 gold 写法不同的合理实现在原材料正式评分下都得 1。

## 1．公开要求

**题面**：`Table.put_item()` 中，只要 Item 里任意位置（“including nested ones”“It could be deeply nested”“It does not matter where in the payload”）有名为 `S` 的键，就报 `SerializationException: Start of structure or map found where not expected`。题面给了两例：

- `{'index': 0, 'S': None}`；
- `{'index': 0, 'A': {'S': None}}`，并注明“clearly not because of the 'A'”。

同样的条目换成 `s` 或 `A` 作属性名都正常。题面还问“为什么只有大写 `S`”，答案是：`S` 同时是 DynamoDB AttributeValue 的字符串类型标签。

**公开旧行为**（base 中可读）：

- `test_put_item__string_as_integer_value`（F2P 函数的原有部分）：关闭 botocore 参数校验后，主键 `{"S": 123}` 报 `NUMBER_VALUE cannot be converted to String`，主键 `{"S": {"S": "asdf"}}` 报 `Start of structure or map found where not expected`。
- `test_put_item_wrong_datatype`（P2P）：主键 `{"N": 123}`；以及注释为“Same thing - but with a non-key, and nested”的非主键嵌套 `{"M": {"sth": {"N": 5}}}`，都报 `SerializationException`／`NUMBER_VALUE…`。**服务端类型校验对非主键属性同样生效**，这一点有公开测试。
- `_validate_item_types` 的源码注释：“This scenario is usually caught by boto3, but the user can disable parameter validation. Which is why we need to catch it 'server-side' as well”。

**需求—断言对照（原材料）**：

| 公开要求 | 依据 | 原测试 | 判断 |
| --- | --- | --- | --- |
| R1 顶层属性 `S` 可写入并等值读回 | 题面例 1 | 新增 put＋get 相等，值用字符串 `asdf`，不是题面的 `None` | 有断言，而且不是示例字面值 |
| R2 嵌套、深层属性 `S` 可写入并读回 | 题面例 2、“deeply nested”“does not matter where” | **无** | 缺，见 §4 |
| R3 真正的类型错误照旧报错（主键 S 给 int 或 dict；主键与非主键嵌套的 N 给 int） | 上列公开旧测试 | F2P 原有部分＋P2P `test_put_item_wrong_datatype` | 有 |
| R4 属性名为 `S` 不影响其它属性的类型校验 | R3＋题面“`S` 与其它名字一样” | **无** | 缺，见 §4 |
| R5 关闭参数校验时，非主键的 `S` 给 int 或 dict 也报 `SerializationException` | 源码注释与 base 行为；公开测试只测主键 | 无 | 罕见路径，gold 本身不满足 dict 这一半 |
| R6 主键名本身为 `M` 或 `S` 时同样适用 | 题面“any key” | 无 | 少见配置 |

题面只有一种读法，不涉及 P5。题面示例没写 region，照抄会先遇到区域配置错误；公开读者已登记（P4），复现时显式设 `us-east-1`。

## 2．环境

- **原镜像**：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6185`，RepoDigest `sha256:ade7d85a…4eda`，image ID `sha256:47443b04…9325`，与 ingest 及 09-19 配方一致；已打 `c3keep/moto6185:src` 标签。镜像内 Python 3.12.4、boto3／botocore 1.35.9，`moto` 从 `/testbed` 导入。
- **派生镜像**：按 09-19 install_wave1 配方在云端重建（`rebuild_install_wave1.py`），本机派生 ID `sha256:22138934…07d8`（本机构建 ID 每次不同，09-29 那次为 `89f45ee2…`，历史 ID `03d0313e…` 不适用）。原 13 层保留，新增 1 层。三个 wheel（`setuptools 72.1.0`、`wheel 0.43.0`、`packaging 24.1`）的 SHA256 用 `--expect` 与 moto-7584 试点登记的值逐一核对，全部相同。重建记录见 `evidence/derived/getmoto__moto-6185/image.json`。
- **评分代码**：分支 `claude/category3-20260929`，正式评分路径与 `a31cdcd` 逐字相同（`git diff a31cdcd HEAD` 为空）。账本里的 `scripts_digest`（`2b42e653…`）与 grader profile 摘要（`3ec1bfa8…`）是当前代码版本的值，与 09-19 历史（`80f2f995…`、`1bb8e0cf…`）不同。推断原因是 09-19 用的是冻结 baseline 代码，而不是镜像或题目变化；未逐项核对。profile 摘要与本批 moto-7584 的正式评分相同。
- **与历史一致**：noop 与 09-19 逐项相同：安装阶段 `make init` 两次 editable 构建完成，`RH2_INSTALL_RC=0`；36 个节点、1 失败 35 通过；两个带空格的 `test_update_item_with_duplicate_expressions[set …]` 节点合并为 35 个解析键；F2P 失败在新增的顶层 put（第 945 行）。
- 私有对照用原镜像（root、断网、一次性容器）。

## 3．实测

### 3.1 私有行为对照（辨别实验）

脚本 [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/behavior.py) 与 [`behavior_extra.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/behavior_extra.py)。合法值用资源层 API、正常 SDK 校验，put 后再 get 比较；错误值用关闭参数校验的低层 client，与 F2P 同一入口。完整 44 行见 [evidence/semantic_v2_matrix.md](evidence/semantic_v2_matrix.md)（09-30 重跑，14 个版本）。下表是摘录，154 格已与重跑结果逐格核对一致。

| 候选 | 例 1 顶层 None | 例 2 嵌套 None | 顶层 S 字符串值 | 两层 map | list 内 map | 主键名 M＋嵌套 S | 主键名 S | 非主键 S→dict | S 在前＋非主键 N 整数 | S 之下 N 整数 | tests/test_dynamodb 全套 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | SerEx | SerEx | SerEx | SerEx | ok | SerEx | SerEx | SerEx | SerEx | SerEx | 434 过 |
| gold | ok | ok | ok | ok | ok | **SerEx** | ok | **AttributeError** | SerEx | SerEx | 434 过 |
| `ctx` | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx | 434 过 |
| `ctx_list` | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx | 434 过 |
| `parity` | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | SerEx | 434 过 |
| `top_only` | ok | **SerEx** | ok | **SerEx** | ok | SerEx | ok | SerEx | SerEx | SerEx | 434 过 |
| `siblings` | ok | **SerEx** | ok | **SerEx** | ok | SerEx | SerEx | SerEx | SerEx | SerEx | 434 过 |
| `depth2` | ok | ok | ok | **SerEx** | ok | ok | ok | SerEx | SerEx | SerEx | 434 过 |
| `list_as_names` | ok | ok | ok | ok | **SerEx** | ok | ok | SerEx | SerEx | SerEx | 434 过 |
| `null_only` | ok | ok | **SerEx** | SerEx | ok | ok | SerEx | SerEx | SerEx | SerEx | 434 过 |
| `shape` | ok | ok | ok | ok | ok | ok | ok | AttributeError | SerEx | SerEx | 433 过／1 败 |
| `rootkey` | ok | ok | ok | ok | ok | ok | ok | **AttributeError** | SerEx | SerEx | 434 过 |
| `swallow` | ok | ok | ok | ok | ok | ok | SerEx | **AttributeError** | **存入** | SerEx | 434 过 |
| `skip_s_subtree` | ok | ok | ok | ok | ok | ok | ok | SerEx | SerEx | **存入** | 434 过 |

说明：
- `SerEx` 指 `ClientError`，错误码 `SerializationException`。“存入”指 put 成功，且之后 get 能读到这条含整数 N 的错误数据。`AttributeError` 是 moto 内部 `bytesize(dict)` 抛出、直接穿出 client 调用的 Python 异常，条目没有存入。
- 表中 gold 对合法值的“ok”都已做 get 等值比较。旧题卡里的两条疑点，只在“主键名 M”与“非主键 S→dict”两列成立。
- base 本身拒绝一切写入：只要主键名是 `S`，任何 put 都失败。这是题面缺陷的另一个实例，gold 已修好。
- `shape` 在全套中失败的一项是 base 版 F2P 函数本身（主键 `{"S": {"S": …}}` 未报错）。
- update 入口不经过 `_validate_item_types`，所有版本都能写入；batch／transact 入口与 put 共用校验，gold 能写入并读回。

**候选说明**：生成器见 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/make_candidates.py)，都只改 `moto/dynamodb/models/table.py`。

| 候选 | 类别 | 写法 |
| --- | --- | --- |
| `ctx` | 合理实现，与 gold 不同 | 区分“属性名 → AttributeValue”与“类型标签 → 值”两层，`M` 的成员重新当属性名；S／N 的旧错误保留 |
| `ctx_list` | 合理实现 | `ctx`，并对 `L` 元素做同样的 AttributeValue 校验 |
| `parity` | 合理实现 | 按深度奇偶区分：偶数层是属性名，奇数层是类型标签 |
| `top_only` | 只处理题面例 1 | 只放过顶层属性名 `S` |
| `siblings` | 数据形态子集 | 认为只有单键 dict 才是 AttributeValue |
| `depth2` | 规模子集 | 只把顶层与第一层 map 的键当属性名 |
| `list_as_names` | 容器形态出错 | `ctx`，但把 `L` 元素当属性名映射来校验 |
| `null_only` | 示例字面值 | 只在属性 `S` 的值为 NULL 时放过 |
| `shape` | 值形态启发式 | `S` 的值“像 AttributeValue”时当属性名 |
| `rootkey` | 放宽非主键校验 | gold 的递归改为传根属性名，只在主键下检查 `S`→dict |
| `swallow` | 吞掉错误，依赖顺序 | `put_item` 捕获 `SerializationException` 后只校验主键 |
| `skip_s_subtree` | 吞掉错误 | `parity` 写法，但遇到名为 `S` 的属性就不再校验它的值 |

依赖顺序的情形由 `swallow` 覆盖：属性 `S` 排在错误属性之前时，base 先因 `S` 报错，`swallow` 捕获后跳过其余校验；错误属性排在前面时则正常报错（`behavior_extra.py` 的 `nested_N_int_then_attrS` 行）。

### 3.2 原材料正式评分

F2P 1 项，P2P 34 项；09-30 重建的派生镜像 `22138934…`；标签 `install-wave1:getmoto__moto-6185:c3cloud-rebuild`。全部 14 次运行：参考缺席 0、`apply_ok`、安装末命令 RC 0、P2P 34/34、清理成功。

| 候选 | sha256 | 性质 | reward | F2P 失败原因 |
| --- | --- | --- | --- | --- |
| noop | — | — | 0 | 新增的顶层 put 报 `SerializationException` |
| gold | `868fd2d1…` | 参考解 | **1** | — |
| `ctx` | `139572e8…` | 合理（附加正对照） | **1** | — |
| `ctx_list` | `9169306d…` | 合理 | **1** | — |
| `parity` | `d7ca0fd9…` | 合理（附加正对照） | **1** | — |
| `top_only` | `1d82e10d…` | 部分修复 | **1** | —（漏判） |
| `siblings` | `c39acf3b…` | 部分修复 | **1** | —（漏判） |
| `depth2` | `2bdf47a6…` | 部分修复 | **1** | —（漏判） |
| `list_as_names` | `f4a791b5…` | 部分修复 | **1** | —（漏判） |
| `swallow` | `35a765d8…` | 吞掉错误 | **1** | —（漏判） |
| `skip_s_subtree` | `c273d7e3…` | 吞掉错误 | **1** | —（漏判） |
| `rootkey` | `0232a04f…` | 放宽非主键校验（T3 同类） | 1 | — |
| `null_only` | `23b58b21…` | 示例字面值 | 0 | 顶层 `S` 字符串值报 `SerializationException` |
| `shape` | `36f1b5d7…` | 值形态启发式 | 0 | 主键 `{"S": {"S": …}}` 抛内部 `AttributeError` |

noop 与 09-19 历史一致（F2P 失败在新增的顶层 put）。

### 3.3 私有模拟评分（补充）

在私有对照里对原材料、v2、v2s 按参考名单逐项计分，结果见 [evidence/semantic_v2_matrix.md](evidence/semantic_v2_matrix.md) 末尾各行，与正式评分 42 格逐项一致（§3.2、§5）。v1／v1s 是 09-29 的中间草稿，只有私有模拟，其输出已随容器重置丢失，09-30 没有重跑。

## 4．判定（v1 §3–§4）

- **T2a（§4 第 1 步，S1）**：R2（嵌套、深层 `S`）是题面标题与正文明示的核心要求，其中例 2 是题面给出的第二个复现例，原测试没有任何断言。`top_only`、`siblings`、`depth2` 三种部分修复在原材料下正式得 1，却在题面例 2 或“深层”实例上报错。
- **T2b（§4 第 3 步，S1）**：
  - `swallow`：吞掉错误，改在 `put_item` 调用 gold 所改函数的那一处；
  - `skip_s_subtree`：在 gold 的修改函数里跳过 `S` 属性。

  两者在原材料下正式得 1，却违反 R3／R4：条目中只要有名为 `S` 的属性，排在它后面或挂在它下面的非主键 `{"N": 5}` 就不再报错，并被存入。“非主键嵌套 N 给整数要报错”由公开 P2P 直接断言；输入是本题关心的“含属性 S 的条目”，不属于边缘输入。
- **`list_as_names`（§4 第 4 步）**：修复时把 base 本来能写入的 list 内 map 改坏，原材料得 1。它违反的仍是 R2（“does not matter where”），归入上面的 T2a 缺口，一并由 R-c 处理。
- **G1＋T3（§4 第 4 步，S2，登记）**：
  - **主键名为 `M`**：gold 的递归只记父键，并用“父键是否主键名”判断类型标签；而嵌套属性的父键总是类型标签 `M`。合法输入被拒，但只发生在主键名恰为 `M` 的表上，属少见配置。
  - **非主键 `S`→dict**：只在关闭 SDK 参数校验时出现，属罕见路径。gold 给出内部 `AttributeError`，而不是 `SerializationException`；条目不会存入，也仍然是报错。公开测试只对主键断言过这一形态。`rootkey` 与此同类。

  这两点与上面 T2b 的区别在于：T2b 是**静默存入**，而且违反的是**有公开测试直接断言**的行为。上游 moto 4.1.8、4.2.14、5.0.28、5.2.3 的 `_validate_item_types` 都保留 gold 的写法，上游测试也只有顶层用例（PyPI wheel 与 raw.githubusercontent 对照，只作佐证）。
- **T1**：未发现。`ctx`、`ctx_list`、`parity` 与 gold 写法不同，原材料正式评分均为 1。两条精确报错文案都来自公开旧测试。
- **§4 第 2 步**：原 F2P 正例用字符串值 `asdf`，不是题面的 `None`，不属于只测示例字面值。缺的是嵌套形态，按第 1 步处理。v2 同时用题面字面值（`None`）和非示例值（两层嵌套的字符串、list 内的 N）。
- **T5**：36 个节点对应 35 个解析键（`[set` 合并），沿用旧登记。本批所有评分中两节点都通过，未观察到错分。
- **X1**：与 5960、6408 的同包源码包含关系沿用旧登记，本页未重查。

## 5．修法（交第2类）：修订版测试草案 v2

**草案**：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/revised_test_v2.patch)，sha256 `7bbae287…c3a9`，在官方 test_patch 的基础上，于同一 F2P 函数 `test_put_item__string_as_integer_value` 末尾追加断言。测试 ID、P2P、测试命令都不变。父版本 v1 为 `3595f3a3…6bce`，只含第 1 组。

| 新增断言 | 公开依据 | 拦下的错误候选 |
| --- | --- | --- |
| 题面两例：顶层 `S`＝`None`、`A` 下嵌套 `S`＝`None`，put 后 get 相等（R-c） | 题面例 1、例 2 | `top_only`、`siblings` |
| 两层嵌套 map 中的 `S`（字符串值），put 后 get 相等（R-c，非示例实例） | “deeply nested” | `depth2` |
| list 内 map 中的 `S`（N 值），put 后 get 相等（R-c，非示例实例） | “does not matter where in the payload” | `list_as_names` |
| 条目含属性 `S` 时，挂在它下面的、以及排在它后面的非主键 `{"N": 5}` 仍报 `SerializationException`／`NUMBER_VALUE cannot be converted to String`（R-c） | 公开 `test_put_item_wrong_datatype` 的非主键嵌套用例；题面“`S` 与其它名字一样” | `skip_s_subtree`、`swallow` |

修订后仍受保护的公开要求：原 F2P 的主键 S 错误、顶层 `S` 往返，以及 P2P 34 项。

**v2 正式诊断评分**：`--materials`（`materials_revised_v2.json`，版本 `c3-moto6185-nested-s-v2`），grader 后缀 `+c3-moto6185-nested-s-v2`，同一派生镜像。14 次运行健康项同上。失败行号取自私有模拟（修订测试文件），正式评分日志中的异常类型一致。

| 候选 | reward | 失败位置 |
| --- | --- | --- |
| gold（正对照） | **1** | — |
| `ctx`、`ctx_list`、`parity` | **1** | — |
| noop | 0 | 945：顶层 put 报 `SerializationException` |
| `top_only`、`siblings`、`depth2`、`list_as_names` | 0 | 961：嵌套、深层或 list 内实例的 put 报 `SerializationException` |
| `swallow`、`skip_s_subtree` | 0 | 971：含属性 `S` 的条目里，非主键 `{"N": 5}` 没有报错（`DID NOT RAISE`） |
| `null_only` | 0 | 945：顶层 `S` 字符串值报错 |
| `shape` | 0 | 938：原 F2P 部分，主键 `{"S": {"S": …}}` 抛内部 `AttributeError` |
| `rootkey` | 1 | —（T3 同类，v2 不断言） |

**严格备选 v2s**（不作默认）：[`revised_test_v2s.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/moto6185/revised_test_v2s.patch)，sha256 `4122cced…25e4`。在 v2 之外追加两项：
- HASH 主键名为 `M` 的表上，嵌套属性 `S` 可写入并读回；
- 非主键 `{"S": {"S": "asdf"}}` 报 `SerializationException`／`Start of structure or map found where not expected`。

同时删去隐藏测试里与第二项矛盾的注释“Nested 'S'-s like this are allowed for non-key attributes”。v2s 下 gold 为 0，按 D4 改用 `ctx` 作正对照（`parity` 为第二正对照），两者都是本人所写，**待他人核实**。

**v2s 正式诊断评分**（`materials_revised_v2s.json`，版本 `c3-moto6185-nested-s-v2s`）：

| 候选 | reward | 失败位置（私有模拟行号） |
| --- | --- | --- |
| `ctx`（v2s 正对照）、`parity`（第二正对照）、`ctx_list` | **1** | — |
| gold | **0** | 986：HASH 主键名为 `M` 的表上，嵌套 `S` 报 `SerializationException` |
| `rootkey` | 0 | 993：非主键 `{"S": {"S": …}}` 抛内部 `AttributeError` |
| noop、`null_only` | 0 | 944 |
| `top_only`、`siblings`、`depth2`、`list_as_names` | 0 | 960 |
| `swallow`、`skip_s_subtree` | 0 | 970 |
| `shape` | 0 | 938 |

**交接给第2类**：

1. 经 D6 的“测试补丁替换”切片形成正式材料版本，默认用 v2。
2. v2 的正对照是 gold；另有 `ctx`、`parity` 两份附加正对照，本人所写，待他人核实。
3. 正式版本复验 §5 表中全部候选。
4. Codex 复核。
5. 评分使用重建的 install_wave1 配方，见 §2。
6. 独立复核若判定 §4 中的 G1／T3 两项为 S1，改用 v2s，评分数据已在上面。

**非阻断建议**：
- v2 的断言放在一个循环里，失败时只报到循环内的 put 行。若希望失败信息直接指出是哪个实例，可以把各实例拆成独立语句，或在 put 外包一层带实例名的断言；这不影响分数。
- 隐藏测试注释“Nested 'S'-s like this are allowed for non-key attributes”容易被理解为“非主键的 S 可以给 dict”，与 base 注释和真实 AWS 的服务端校验不符。v2 没有改它（评分无关），v2s 已删。

## 6．当前用途（v1 §2）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | conditional：只能作受限比较，须预先登记事后审计（嵌套、深层、list 内的 `S` 往返；含 `S` 属性的条目仍报 N 类型错误），原始 reward 与语义结果分列 | 否（S1 未处理，D6 未实施） | 否 |
| 修订版 v2 | 经 D6 入库并通过验收后重新评估 | | | |

## 7．独立复核

尚未进行。建议复核重点：
- G1／T3 两项（主键名 `M`；关闭参数校验时非主键 `S`→dict）判 S2 是否成立；
- v2 是否仍放过其它错误候选，可另造候选；
- `ctx`／`parity` 能否作为正对照。

## 8．未做与剩余事项

- 未查真实 actor 开发条件：UID 54321、实际消息与 public_hints 的注入，本页只有 root 私有对照和 grader 身份的正式评分。
- 公开读者命令清单 C1–C4 未按正式 actor 身份原样重跑。私有矩阵覆盖了 C2 的全部输入：base 上题面两例、深层均复现缺陷，list 内 map 在 base 上本来就能写入。
- 未查真实 AWS 的行为，本项目不调用真实 AWS；修订版只按 moto 行为和公开旧测试验收。
- 没有模型求解证据。
- `ctx`／`parity` 作为正对照尚未经他人核实；它们在 `tests/test_dynamodb` 全套 434 项上全部通过，这是本人的私有检查。
- 列表内 AttributeValue 的错误类型（例如 `L` 中的 `{"S": 123}`）不在 base 的校验范围内，本题不要求，没有测。

## 9．版本与证据

- 候选补丁、生成器、行为脚本、修订草案与 materials：`rh2/experiments/category3_cloud_20260929/moto6185/`。
- 运行产物：`runs/category3_cloud_20260929/moto6185/`（git 忽略）。09-29 的运行输出随容器重置丢失；09-30 全部重跑，小型原件已归档到 [evidence/](evidence/)，全部文件的 SHA256 见 `evidence_manifest.json`：
  - `formal/`、`formal_revised_v2/`、`formal_revised_v2s/`：正式评分与诊断评分，各含 `failure_reasons.txt`；
  - `semantic_v2/`、`semantic_v2_matrix.md`、`semantic_v2_matrix.json`：私有对照与私有模拟（14 个版本）；规格为实验目录中的 `semantic_spec_v2_full.json`（合并了原 v2、`list_as_names` 与全套测试三份规格）；
  - `derived/`：派生镜像重建记录；`test_orig.patch`：原 test_patch 副本（sha256 `506b3670…`）。
- 官方材料：gold sha256 `868fd2d1…79e1`；test_patch sha256 `506b3670…fc52`；base `dc460a32…`。
