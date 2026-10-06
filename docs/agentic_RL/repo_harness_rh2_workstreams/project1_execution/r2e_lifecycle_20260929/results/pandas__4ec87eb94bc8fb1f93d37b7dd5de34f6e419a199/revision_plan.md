# pandas 4ec87eb9：R-c 修订方案（第 2 版：新断言并入已有目标测试，不新增键）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：R-c 一项。按协调者要求改了结构，重新做了一轮试跑验收：4 个候选（gold、noop、C0、C1）全部与预期一致（试跑工具，不是正式评分），另做 2 次诊断试跑。不需要用户决定。** 这一版只改隐藏测试 `test_1.py`，期望映射保持 237 键不变，已批准的 r2e-mr-007 原样保留，所以可以直接按模板落地（§7）。之后重建派生镜像材料、跑正式评分，再送 Codex 复核。

路径约定（仓库根相对；`trials/`、`cands/`、`card.md`、`public_read.md`、`commands.json`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，328 行）；`HT'` = 本版修订后的 `test_1.py`（343 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/pandas_4ec8/`；`DC` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`。

## 0. 与第 1 版的差异

| 项 | 第 1 版 | 第 2 版（本版） |
| --- | --- | --- |
| 结构 | 新增独立测试 `test_groupby_quantile_NA_float_nonnan_storage`，期望 237 → 238 键 | 两段断言并入已有目标测试 `test_groupby_quantile_NA_float(any_float_dtype)` 的末尾，期望 237 键不变 |
| 断言用的 dtype | 固定 `Float64` | 随该测试的 `any_float_dtype` 参数（`float`、`float32`、`float64`、`Float32`、`Float64`），多覆盖了 `Float32` |
| C0 的失败键 | 只有新键 | `test_groupby_quantile_NA_float[Float32]`、`[Float64]` |
| noop 的失败键 | 原 4 个目标键 + 新键 | 原 4 个目标键，与当前材料逐键相同 |
| 正式落地 | 期望文件要与 r2e-mr-007 合并，协调者不能自行做 | 只有一条 `hidden_test_text_replace`，按模板落地 |

- **为什么不新增键**：本题的期望文件已有用户 09-24 批准的 r2e-mr-007（`expected_file_replace`）。修订机制规定同一题同一目标只允许一条修订（`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:416-417`）。新增键就要改期望文件，只能把改动合并成新条目去取代 007，等于改动一条已批准的修订，协调者不能自行做。`test_1.py` 本身没有已批准修订（r2e-mr-006 是新增 `conftest.py`），所以只改它、不改期望，就能按模板落地。
- **代价：失败定位比独立键粗**。`NA_float[Float32]` 或 `[Float64]` 失败时，可能是原有的部分 NA 断言（`HT':257`、`:265`）没过，也可能是新增的存储断言（`HT':272`、`:278-280`）没过。评分是二值的，不受影响；事后审计要区分时，读正式日志里失败断言的行号。
- 第 1 版的方案、草案与试跑结果都保留在 `trials/round1/`：`revision_plan_round1.md`、`revision_draft_round1.json` 与 8 份结果文件。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。只有一个 S1，对应一处修改。

| 项 | 要纠正的 S1 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- |
| R-c 1 | T2b（v1 §4 第 3 步）。隐藏测试里所有浮点扩展数组的 NA 都由列表构造，掩码位置底层恰好是 NaN，所以测试区分不了"按掩码忽略 NA"和"依赖底层恰好是 NaN" | C0（在 gold 同一位置写 `out = vals._data`）正式评分 1.0，237/237（`INV/ledger_C0.jsonl:1`）。私有行为对照里，C0 在 astype / reindex / `Int64` 除法三种输入上得 [1.0] / [0.0] / [1.0]，gold 得 [2.0] / [2.5] / [2.0]（`INV/pcheck_C0.json`、`INV/pcheck_gold.json`） | `card.md:14-27`（结论）、`card.md:77-117`（§4 草案）；`old_findings_delta.md:37` |

**不在本轮**：
- **结果 dtype**（float64 还是 `Float64`）：按主审结论登记为 P3，不修订、不交用户（`card.md:119-127`）。新断言用 `check_dtype=False`，既不新增也不放宽 dtype 约束；dtype 仍由所在测试原有的断言约束。
- **T3 缺口**（`card.md:73`）：浮点扩展数组的 DataFrame 入口、混合列不丢列、无 NA 时 dtype 的旧行为，照旧登记。

## 2. 公开依据

- **题面的一般表述**：
  - 标题 `PUB/user_prompt.txt:4`、描述 `:7`：含 `pd.NA` 时 `GroupBy.quantile` 报 `TypeError`；
  - Expected `:22`："correctly handling and ignoring the `pd.NA` value"。
  - 示例 `:13-16` 只是其中一个实例：由列表构造，NA 位底层恰好是 NaN（`W/pandas/core/arrays/floating.py:172-175`）。
- **是否缺失只看掩码**：
  - `FloatingArray` 文档（`W/pandas/core/arrays/floating.py:194-197`）：由 data 与 mask 两个数组表示，mask 为 True 即缺失。
  - 公开旧测试 `W/pandas/tests/arrays/floating/test_to_numpy.py:84-89`：一个掩码位底层存 0.0 的 `FloatingArray`，该位置照样按 NA 处理（`to_numpy(na_value=-1)` 只在掩码位填 -1）。
  - 公开文档：归约默认跳过缺失值（`W/doc/source/user_guide/missing_data.rst:827-828`）；groupby 的聚合函数排除 NA（`W/doc/source/user_guide/groupby.rst:557`）。
- **常用公开操作会产生底层不是 NaN 的 NA**（新断言用前两种）：
  - `Int64` 转浮点扩展类型：`IntegerArray` 构造时在掩码位填 1（`W/pandas/core/arrays/integer.py:225-228`）；转 `Float32` / `Float64` 走掩码类型之间的快速路径，数据原样保留（`W/pandas/core/arrays/masked.py:312-320`，314 行注释 `TODO deal with NaNs for FloatingArray case`），掩码位是 1.0。转 numpy 浮点类型则走 `to_numpy(na_value=np.nan)`（`integer.py:360-376`），得到普通 NaN。
  - `reindex` / `take` 引入的 NA：新位置填 `_internal_fill_value`（`masked.py:380-387`），`FloatingArray` 的是 0.0（`floating.py:242-243`）。
  - `Int64` 除法：直接在底层数据上运算再套回掩码（`W/pandas/core/arrays/numeric.py:143`、`integer.py:470-475`）。新断言没用这一种。
  - 当前镜像实测（`INV/pcheck_gold.json` 的 stdout）：astype 得 data `[1. 1. 3.]`、mask `[False True False]`；reindex 得 data `[2.5 0.]`、mask `[False True]`。
- **期望值用到的方法语义**：`GroupBy.quantile` 按 "a la numpy.percentile" 计算（`W/pandas/core/groupby/groupby.py:2401`），缺省 `interpolation="linear"`（`:2399`）。
- **与 base 现有行为一致（执行证据）**：新断言在 numpy 浮点参数（`float`、`float32`、`float64`）下也会执行，此时缺失值是普通 NaN。修订版 noop 试跑中这三个键全部 PASSED（`trials/rev_noop.json`），说明 base 对"含缺失值的浮点数据"本来就给出同样的 2.0 与 3.0 / 4.0。修复只需让掩码浮点类型与之一致。
- **独立佐证**：没看隐藏测试与 gold 的公开读者
  - 把"忽略 NA 不应取决于掩码位置底层存的是什么"列为合理推知需求 R5（`public_read.md:25`）；
  - 把"把 `_data` 原样交给内核"列为不应算作正确的做法（`public_read.md:59`）；
  - 在公开命令 `variants_float_masked` 里写了与第一段相同的检查 `masked_slot_not_nan`，期望 2.0（`commands.json:27-28`）。devcheck 中，base 上该项 ERR（`DC/orig/attempt.json:246`），gold 私有对照该项 OK `[2.0]`（`DC/private_control.json:38`）。
- **这是同一核心要求的非示例实例，不是新需求**：输入仍是"含缺失值的浮点数据"，只是 NA 来自另两种常用操作。不涉及 dtype；不涉及未掩码的 NaN（`floating.py:188-192` 说 NaN 与 NA 的区分属实验性，新断言不碰）；也不涉及 DataFrame 入口。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`（`HT`）。私有 `conftest.py`（r2e-mr-006）不动。
- **宿主测试**：`test_groupby_quantile_NA_float(any_float_dtype)`（`HT:251-265`）。它就是题面场景的目标测试（GH#42849），参数来自私有 conftest 的 `any_float_dtype`：`float`、`float32`、`float64`、`Float32`、`Float64`（`PRIV/hidden_tests/conftest.py:10`，`W/pandas/_testing/__init__.py:135-136`）。5 个参数键当前都期望 PASSED；其中 `[Float32]`、`[Float64]` 是目标键，另 3 个在 base 上已通过。
- **草案条目**：一条 `hidden_test_text_replace`，一处 edit。
  - `old` = 宿主测试最后一行 `    tm.assert_series_equal(result, expected)\n` 加两个空行，再加下一个测试的定义行 `def test_groupby_quantile_NA_int(any_int_ea_dtype):\n`。这一段全文恰好出现一次（`HT:265-268`）。
  - `new` = 原最后一行 + 空行 + 两段新断言 + 两个空行 + 原定义行。
  - 修订后新断言位于 `HT':267-280`，`test_groupby_quantile_NA_int` 移到 `HT':283`；文件从 328 行变为 343 行，仍是纯 ASCII；新增行最长 83 字符。
- **不新增键，期望映射不变。**

并入后宿主测试的末尾（`HT':265-280`；前面原有的断言不变）：

```python
    tm.assert_series_equal(result, expected)

    # Missing is decided by the mask alone, whatever the underlying data holds
    # there. Int64 -> float dtype: for the masked Float dtypes the masked slot
    # keeps the integer array's filler (1.0) instead of NaN.
    ser = pd.Series(pd.array([1, None, 3], dtype="Int64").astype(any_float_dtype))
    result = ser.groupby([0, 0, 0]).quantile(0.5)
    tm.assert_series_equal(result, pd.Series([2.0], index=[0]), check_dtype=False)

    # NA introduced by reindex: for the masked Float dtypes 0.0 sits under the
    # mask. Two groups, one of them with two valid values.
    ser = pd.Series([2.5, 3.5, 4.0], dtype=any_float_dtype).reindex([0, 1, 2, 3])
    result = ser.groupby(["a", "a", "b", "b"]).quantile(0.5)
    tm.assert_series_equal(
        result, pd.Series([3.0, 4.0], index=["a", "b"]), check_dtype=False
    )
```

**设计说明**：
- **为什么随参数取 dtype，而不固定 `Float64`**：
  - 固定 `Float64` 的话，base 上 3 个 numpy 参数键也会因新断言报 `TypeError` 而失败，原本在 base 上通过的回归键就变成了目标键，改变了现有键的含义。
  - 随参数取 dtype：numpy 参数下断言测的是 base 已有的 NaN 路径，照旧通过；掩码参数下测的正是本题缺口。noop 的失败键因此与当前材料逐键相同（§5.2）。
  - 顺带把 `Float32` 纳入覆盖。
- **每个参数下都成立**：期望值只取决于"忽略缺失值后的中位数"，与 dtype 无关；2.5、3.5、4.0、1.0、3.0 在 float32 下都能精确表示，内核按 float64 计算。gold 与 C1 试跑中 5 个参数键全部 PASSED。
- **依赖**：只用文件头已有的导入（`pd`、`tm`，`HT:4, 9`）与宿主测试自己的 fixture；没有随机、时间、资源因素。
- **`check_dtype=False`**：新断言只管"忽略 NA 与底层存储无关"。读 `W/pandas/_testing/asserters.py:992-1003`（只有 `check_dtype` 为真才比 dtype）、`:1077-1086` 与 `:150-170`（`check_dtype=False` 时不比数组类，逐元素比数值）可知：它不新增 dtype 约束。这是源码推断，没有另造 `Float64` 候选试跑。
- **期望值不依赖底层存储**：即使某个环境里掩码位恰好是 NaN，正确解照样通过，只是对 C0 失去鉴别力。鉴别力已由试跑实证（§5）。
- **两段各自都能挡住 C0**：只并入第一段、只并入第二段的两次诊断试跑中，C0 都在 `NA_float[Float32]`、`[Float64]` 失败（§5.3）。第二段还顺带覆盖"两组、其中一组有两个有效值"的插值（`card.md:73` 的 T3 缺口之一）。
- **刻意不测**：dtype（P3）；DataFrame 入口与混合列（T3）；列表 q 下的同类存储（与已有断言同一分支）；`Int64` 除法（与 astype 同属"底层保留旧值"，私有对照已覆盖）；掩码位与未掩码 NaN 并存（实验性语义）。

## 4. 期望映射

- **不变**：237 键全部 PASSED，与当前正式材料相同（`expected_output.json` sha256 `bdf1ddf5…`）。`revision_draft.json` 的 `expected_after` 与当前映射逐键、逐序相同，`json.dumps(indent=4)` 能还原当前文件的字节；`formalize_revisions.py` 不会生成期望修订。
- **期望从哪里来**（由公开语义推出，不是照抄 gold 输出）：
  - 第一段：`[1.0, 缺失, 3.0]` 忽略缺失后是 `[1.0, 3.0]`，按 numpy.percentile 的线性插值，中位数为 2.0；
  - 第二段：a 组 `[2.5, 3.5]` 得 3.0；b 组 `[4.0, 缺失]` 只有一个有效值，得 4.0；
  - 索引与名称：按列表分组时 base 的现有行为，修复不改变它；
  - base 上 numpy 浮点参数跑同样的断言得到同样的值（§2 执行证据）；公开读者没看隐藏测试，也对第一段的同一输入写出了 2.0（`commands.json:27-28`）。gold 通过是验证结果，不是依据。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，328 行） | `5a4d2be4…` |
  | 父版本 `conftest.py`（不变） | `632b5ee3…` |
  | `expected_output.json`（237 键，不变） | `bdf1ddf5…` |
  | 父版本隐藏测试树 | `6a859754…`，`material_revisions` 为 r2e-mr-006、r2e-mr-007 |
  | 本版修订后 `test_1.py`（`HT'`，343 行） | `719e63ae…` |
  | 试跑用 `draft_r2.json` | `c5ebaabc…` |

  父版本各项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:33` 一致。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。
- 期望一律取 `--expected current`，即远端正式材料里的 237 键映射。所以"期望不变"是直接对着当前材料验的。
- 派生镜像 `sha256:85f550e62cc0…`，配方 `r2e_derive_v1+material_v2+sysconfig_v1`，与第 1 版试跑、`INV/ledger_C0.jsonl`、`INV/ledger_C1.jsonl` 相同。
- 补丁：gold 取 `PRIV/gold.patch`；C0、C1 取 `cands/`，与协调者正式评分用过的 `INV/` 副本 sha256 相同。本版没有新写补丁。
- 每次试跑都是 `RH2_APPLY_RC=0`，草案都报 `RH2_TRIAL_EDITS_APPLIED=1`，237 键全部解析到，没有 missing / extra。
- 单次试跑墙钟 73–100 s，测试段 7.0–10.2 s（pytest 自报 3.4–4.2 s）。

### 5.1 当前材料上的对照（不进 acceptance）

材料与镜像自第 1 版以来没有变化，沿用第 1 版的环境确认。

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：恰好 4 个目标键 FAILED（`test_groupby_quantile_NA_float[Float32]`、`[Float64]`，`test_groupby_quantile_allNA_column[Float32]`、`[Float64]`），233 passed | `trials/round1/env_noop_current.json`（试跑） |
| gold | 1：237/237 | `trials/round1/env_gold_current.json`（试跑） |
| C0 | **1**：237/237（触发反例） | `INV/ledger_C0.jsonl:1`（协调者正式评分） |
| C1 | 1：237/237 | `INV/ledger_C1.jsonl:1`（协调者正式评分） |

### 5.2 修订草案下的验收

结果文件为 `trials/rev_<候选>.json`；键名省略前缀 `test_groupby_quantile_`。

| 候选 | 补丁 | 角色 | 应得 | 应不符的键 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，237/237；`NA_float` 5 个参数键全 PASSED | 1 |
| noop | 无 | — | 0 | `NA_float[Float32]`、`[Float64]`、`allNA_column[Float32]`、`[Float64]` | 0，恰好这 4 键，失败摘要为 `TypeErr...`；观测映射与当前材料的 noop 逐键相同；`NA_float` 的 3 个 numpy 参数键 PASSED | 0 |
| C0 | `cands/pandas_4ec8_C0.patch` | 第 3 步退化候选，触发反例 | 0 | 只有 `NA_float[Float32]`、`[Float64]` | 0，恰好这 2 键，失败摘要为 `Asserti...`（断言失败，不是报错）；其余 235 键全 PASSED | **1**（正式） |
| C1 | `cands/pandas_4ec8_C1.patch` | 合理替代解（统一的掩码数组分支） | 1 | — | 1，237/237 | 1（正式） |

**判读**：
- **正对照 1、noop 0**：成立。gold 本身满足公开要求：私有对照在 astype / reindex / 除法三种输入上都给出正确值（`INV/pcheck_gold.json`），devcheck 的 8 个公开变体全部 OK（`DC/private_control.json:38`）。
- **误判已纠正**：C0 在当前材料正式得 1，修订后试跑得 0。在当前材料上，C0 已通过这两个键的原有断言（正式 237/237）；修订后它在这两个键失败，所以失败只能来自新并入的断言，也就是只因"掩码位底层不是 NaN"被拒。
- **没有误拒**：C1 仍得 1；gold 与 C1 下 5 个参数键都 PASSED，满足"每个参数键仍应 PASSED"。
- **旧键不受影响**：noop 的观测映射与当前材料逐键相同；gold、C1 全部 PASSED；C0 除宿主的两个键外全部 PASSED。
- **日志截断说明**：试跑工具只保留日志末尾 8000 字符，FAILURES 段被 `-rA` 的结果摘要挤掉，看不到具体断言行与数值。C0 在第一段得 1.0（应为 2.0）的数值由 `INV/pcheck_C0.json` 佐证（同一表达式得 `[1.0]`）。正式评分的日志是完整的，协调者应在那里确认 C0 的失败落在 `HT':272`。

### 5.3 诊断试跑（不进 acceptance）

- **目的**：确认两段各自都能挡住 C0。
- **做法**：同一锚点，宿主测试末尾只并入其中一段；期望仍取 `current`；候选 C0。

| 诊断 | 草案 | 结果 |
| --- | --- | --- |
| 只并入第一段（Int64 转浮点） | `trials/diag_seg1_draft.json`（sha256 `9f61e2bf…`） | `mismatch`，恰好 `NA_float[Float32]`、`[Float64]` FAILED（`Asserti...`），其余 PASSED（`trials/diag_seg1_C0.json`） |
| 只并入第二段（reindex、两组） | `trials/diag_seg2_draft.json`（sha256 `d162a090…`） | 同上（`trials/diag_seg2_C0.json`） |

与源码推断一致：内核按底层数值排序（`W/pandas/_libs/groupby.pyx:843-844`），C0 让掩码位的 1.0 或 0.0 参与取位（`:857-866`），分别得 1.0（应为 2.0）与 b 组 0.0（应为 4.0）。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（键名省略前缀 `test_groupby_quantile_`）：
- **含 NA 的浮点扩展列能算，NA 被忽略**：`NA_float[Float64]`、`[Float32]` 的原有断言（值用 0.2，不是示例的 2.5；标量 q 与列表 q）。
- **忽略 NA 与掩码位底层存储无关**（本次并入）：同样由 `NA_float[Float32]`、`[Float64]` 承载，两种 NA 来源，单组与两组。
- **numpy 浮点含 NaN 的旧行为**：`NA_float[float]`、`[float32]`、`[float64]`，现在也跑同样的新断言。
- **全 NA 组得缺失值**：`allNA_column[Float32]`、`[Float64]`。
- **结果 dtype 为 float64**（P3）：`NA_float` 与 `allNA_column` 的原有断言。
- **旧行为**：与公开文件相同的 222 键（object 报错并带警告、`Int64` / `boolean` 可空数组、插值与整数回转、datetime / timedelta、q 越界、缺失分组键、丢列警告、`axis=1`），以及 `NA_int` 的 8 个键。

**仍未覆盖，维持登记**：
- **T3**：
  - DataFrame 入口的浮点扩展列、混合列不丢列、无 NA 时 dtype 的旧行为；
  - 另一种挡不住的候选：只在部分 NA 来源上把掩码位改写成 NaN（例如只改 astype 与 take 的填充），quantile 里仍直接用 `_data`。它能过新断言，但对 `Int64` 除法和直接构造的 `FloatingArray` 仍会算错。目前没有这类候选的实例，按 v1 §8 抽查。
- **失败定位变粗**：见 §0。
- **P3**（dtype）、**P4**（题面写 "group `1`"，没提 FutureWarning）、**X1**（`7dd34ea7` 的公开初态含本题 gold 与原来 3 个新测试）：照旧。并入的断言是新写的，第一段的构造写法（`dtype="Int64").astype(`）在 v3 的 7 个 pandas 公开工作树的 `pandas/tests` 下没有命中。

## 7. 正式落地要点（交协调者）

1. **只有一条修订**：`hidden_test_text_replace`（target `test_1.py`）。`test_1.py` 此前没有修订，`formalize_revisions.py` 能直接生成；可用 `revision_draft.json` 的 `revised_hidden_test_sha256`（`719e63ae…`）核对重算结果。
2. **期望文件不改**：`expected_after` 与当前映射相同，`formalize_revisions.py` 不会生成期望修订，r2e-mr-007 原样保留。
3. **重建派生镜像材料**（隐藏测试树摘要会变），然后正式评分至少跑 gold、noop、C0、C1，按 §5.2 判读。在完整日志里确认：C0 的失败落在 `HT':272`；gold 下宿主测试 5 个参数键全部 PASSED。
4. **送 Codex 复核**。
5. **已放弃的方案（仅供用户参考）**：第 1 版新增独立键，并把期望修订合并成一条新条目取代 r2e-mr-007。好处是失败定位更细（独立键只承载存储断言）；代价是改动一条用户已批准的修订，协调者不能自行做，需用户同意。评分是二值的，两种结构对当前四个对照（gold、noop、C0、C1）的得分相同（09-29 协调者按 Codex 复核改：第 2 版额外覆盖 Float32，不能宣称对任何候选普遍等价）；本版不需要这一步，所以不建议为此改动 007。第 1 版的试跑证据在 `trials/round1/`，届时可复用。

## 8. 边界

- **只做 R-c**：不改题面，不增删键，不放宽已有断言，期望不照抄 gold 输出；依据都是公开的，不涉及 P5 或其它模板外事项，**不需要用户决定**。
- 没写 `s2_r2e` 下的正式材料，没改生产代码。远端只用了上传与试跑两类命令（第 1 版另用过一次给定的建目录命令），同一时间最多 2 个试跑。
- **之后按正式评分结果重判 v1 用途**（`card.md` 的用途表）：训练候选要的正面证据（核心断言、noop 0 / gold 1、第 2、3 步结果）届时齐全，另待 Codex 复核；留出评测仍为 no（修订后只能作标明版本的自建题，另有 X1 与审查暴露）。
