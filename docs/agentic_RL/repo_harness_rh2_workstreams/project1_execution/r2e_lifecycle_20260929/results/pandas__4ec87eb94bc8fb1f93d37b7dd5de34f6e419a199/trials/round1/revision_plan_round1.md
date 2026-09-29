# pandas 4ec87eb9：R-c 修订方案（补"掩码位置底层不是 NaN"的 NA 实例）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：R-c 一项，一轮修订；试跑验收 4 个候选（gold、noop、C0、C1）全部与预期一致（试跑工具，不是正式评分），另做 1 次诊断试跑。不需要用户决定。** 正式落地前，协调者要先处理一个修订单格式问题：本次期望文件改动与已批准的 r2e-mr-007 同一目标，ingest 不允许同一目标两条修订，需要合并（§7 第 2 条）。之后重建派生镜像材料、跑正式评分，再送 Codex 复核。

路径约定（仓库根相对；`trials/`、`cands/`、`card.md`、`public_read.md`、`commands.json`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，328 行）；`HT'` = 修订后的 `test_1.py`（345 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/pandas_4ec8/`；`DC` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。只有一个 S1，对应一处修改。

| 项 | 要纠正的 S1 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- |
| R-c 1 | T2b（v1 §4 第 3 步）。隐藏测试里所有浮点扩展数组的 NA 都由列表构造，掩码位置底层恰好是 NaN，所以测试区分不了"按掩码忽略 NA"和"依赖底层恰好是 NaN" | C0（在 gold 同一位置写 `out = vals._data`）正式评分 1.0，237/237（`INV/ledger_C0.jsonl:1`）。私有行为对照里，C0 在 astype / reindex / `Int64` 除法三种输入上得 [1.0] / [0.0] / [1.0]，gold 得 [2.0] / [2.5] / [2.0]（`INV/pcheck_C0.json`、`INV/pcheck_gold.json`） | `card.md:14-27`（结论）、`card.md:77-117`（§4 草案）；`old_findings_delta.md:37` |

**不在本轮**：
- **结果 dtype**（float64 还是 `Float64`）：按主审结论登记为 P3，不修订、不交用户（`card.md:119-127`）。新键用 `check_dtype=False`，既不新增也不放宽 dtype 约束。
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
- **常用公开操作会产生底层不是 NaN 的 NA**（新测试用前两种）：
  - `Int64` 转 `Float64`：`IntegerArray` 构造时在掩码位填 1（`W/pandas/core/arrays/integer.py:225-228`）；掩码类型之间的 `astype` 走快速路径，数据原样保留（`W/pandas/core/arrays/masked.py:312-320`，314 行注释 `TODO deal with NaNs for FloatingArray case`）。结果：掩码位是 1.0。
  - `reindex` / `take` 引入的 NA：新位置填 `_internal_fill_value`（`masked.py:380-387`），`FloatingArray` 的是 0.0（`floating.py:242-243`）。结果：掩码位是 0.0。
  - `Int64` 除法：直接在底层数据上运算再套回掩码（`W/pandas/core/arrays/numeric.py:143`、`integer.py:470-475`）。新测试没用这一种。
  - 当前镜像实测（`INV/pcheck_gold.json` 的 stdout）：astype 得 data `[1. 1. 3.]`、mask `[False True False]`；reindex 得 data `[2.5 0.]`、mask `[False True]`。
- **期望值用到的方法语义**：`GroupBy.quantile` 按 "a la numpy.percentile" 计算（`W/pandas/core/groupby/groupby.py:2401`），缺省 `interpolation="linear"`（`:2399`）。
- **独立佐证**：没看隐藏测试与 gold 的公开读者
  - 把"忽略 NA 不应取决于掩码位置底层存的是什么"列为合理推知需求 R5（`public_read.md:25`）；
  - 把"把 `_data` 原样交给内核"列为不应算作正确的做法（`public_read.md:59`）；
  - 在公开命令 `variants_float_masked` 里写了与新测试第一段相同的检查 `masked_slot_not_nan`，期望 2.0（`commands.json:27-28`）。devcheck 中，base 上该项 ERR（`DC/orig/attempt.json:246`），gold 私有对照该项 OK `[2.0]`（`DC/private_control.json:38`）。
- **这是同一核心要求的非示例实例，不是新需求**：输入仍是"含 `pd.NA` 的 `Float64` 数据"，只是 NA 来自另两种常用操作。不涉及 dtype；不涉及未掩码的 NaN（`floating.py:188-192` 说 NaN 与 NA 的区分属实验性，新测试不碰）；也不涉及 DataFrame 入口。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`（`HT`）。私有 `conftest.py`（r2e-mr-006）不动。
- **草案条目**：一条 `hidden_test_text_replace`，一处 edit。
  - `old` = `def test_groupby_timedelta_quantile():\n`（`HT:290`，全文恰好出现一次）；
  - `new` = 新测试函数 + 两个空行 + 原锚点。
  - 新函数落在 `test_groupby_quantile_allNA_column`（`HT:280-287`）之后：修订后位于 `HT':290-304`，原 `test_groupby_timedelta_quantile` 移到 `HT':307`。
- **新键**：`test_groupby_quantile_NA_float_nonnan_storage`。模块级函数、不参数化，只新增这一个键，与现有键不重名。

```python
def test_groupby_quantile_NA_float_nonnan_storage():
    # GH#42849, general case: a value is missing iff its mask is set,
    # whatever the underlying data holds at that position.
    # Int64 -> Float64: the masked slot keeps the integer array's filler (1.0).
    ser = pd.Series(pd.array([1, None, 3], dtype="Int64").astype("Float64"))
    result = ser.groupby([0, 0, 0]).quantile(0.5)
    tm.assert_series_equal(result, pd.Series([2.0], index=[0]), check_dtype=False)

    # NA introduced by reindex (0.0 under the mask); two groups, one of them
    # with two valid values.
    ser = pd.Series([2.5, 3.5, 4.0], dtype="Float64").reindex([0, 1, 2, 3])
    result = ser.groupby(["a", "a", "b", "b"]).quantile(0.5)
    tm.assert_series_equal(
        result, pd.Series([3.0, 4.0], index=["a", "b"]), check_dtype=False
    )
```

**设计说明**：
- **与主审草案的差别**：代码行与 `card.md:87-99` 逐行相同，只把两行中文注释换成英文。隐藏测试文件原本是纯 ASCII，保持一致，也避免试跑与正式材料在不同 locale 下读写时编码不一致。
- **依赖**：只用文件头已有的导入（`pd`、`tm`，`HT:4, 9`）；不用 fixture；没有随机、时间、资源因素。
- **`check_dtype=False`**：新键只管"忽略 NA 与底层存储无关"这一个窄问题，结果 dtype 仍由原有 4 个目标键约束（P3，不变）。读 `W/pandas/_testing/asserters.py:992-1003`（只有 `check_dtype` 为真才比 dtype）、`:1077-1086` 与 `:150-170`（`check_dtype=False` 时不比数组类，逐元素比数值）可知：返回 `Float64`、数值正确的候选也能过新键。这是源码推断，没有另造 `Float64` 候选试跑。
- **期望值不依赖底层存储**：即使某个环境里掩码位恰好是 NaN，正确解照样通过，只是这个测试对 C0 失去鉴别力。鉴别力已由试跑实证（§5）。
- **两段各自都能挡住 C0**：第一段由验收试跑证实（C0 在新键失败）；第二段由诊断试跑证实（只保留第二段时 C0 仍在新键失败，§5.3）。第二段还顺带覆盖"两组、其中一组有两个有效值"的插值，这是 `card.md:73` 登记的 T3 缺口之一。
- **刻意不测**：
  - dtype（P3）；
  - DataFrame 入口与混合列（T3）；
  - Float32、列表 q 下的同类存储（与已有键走同一分支）；
  - `Int64` 除法（与 astype 同属"底层保留旧值"，私有对照已覆盖）；
  - 掩码位与未掩码 NaN 并存（实验性语义）。

## 4. 期望映射逐键变化

- **原 237 键不变**，全部 PASSED。
- **新增 1 键**：`test_groupby_quantile_NA_float_nonnan_storage: PASSED`，追加在末尾。
- **合计 238 键**，完整映射见 `revision_draft.json` 的 `expected_after`。相对当前文件：`added` 为这一键，`changed`、`removed` 为空。
- **期望从哪里来**（由公开语义推出，不是照抄 gold 输出）：
  - 第一段：`[1.0, NA, 3.0]` 忽略 NA 后是 `[1.0, 3.0]`，按 numpy.percentile 的线性插值，中位数为 2.0；
  - 第二段：a 组 `[2.5, 3.5]` 得 3.0；b 组 `[4.0, NA]` 只有一个有效值，得 4.0；
  - 索引与名称：按列表分组时 base 的现有行为，修复不改变它；
  - 公开读者没看隐藏测试，就对第一段的同一输入独立写出了 2.0（`commands.json:27-28`）。gold 通过是验证结果，不是依据。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，328 行） | `5a4d2be4…` |
  | 父版本 `conftest.py`（不变） | `632b5ee3…` |
  | 父版本 `expected_output.json`（237 键） | `bdf1ddf5…` |
  | 父版本隐藏测试树 | `6a859754…`，`material_revisions` 为 r2e-mr-006、r2e-mr-007 |
  | 修订后 `test_1.py`（`HT'`，345 行） | `b6b4dbd7…` |
  | 修订后期望（238 键；`json.dumps(indent=4)`、无末尾换行，与当前文件同格式；文本 = 当前文件末尾加一行） | `f7d93a07…` |
  | 试跑用 `draft.json` | `6faf456a…` |

  父版本各项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:33` 一致。全长哈希见 `revision_draft.json`。

## 5. 验收计划与试跑结果

**试跑环境**：
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。
- 派生镜像 `sha256:85f550e62cc0…`，配方 `r2e_derive_v1+material_v2+sysconfig_v1`，与 `INV/ledger_C0.jsonl`、`INV/ledger_C1.jsonl` 的 `image_id_actual` 相同。
- 补丁：gold 取 `PRIV/gold.patch`；C0、C1 取 `cands/`，与协调者正式评分用过的 `INV/` 副本 sha256 相同。本轮没有新写补丁，不需要另做 `git apply --check`。
- 每次试跑都是 `RH2_APPLY_RC=0`（日志为 "Applied patch pandas/core/groupby/groupby.py cleanly"）；修订草案都报 `RH2_TRIAL_EDITS_APPLIED=1`；所有键都解析到，没有 missing / extra。
- 单次试跑墙钟 63–100 s，其中测试段 8.3–10.0 s（pytest 自报 4.2–5.7 s）。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：恰好 4 个目标键 FAILED（`test_groupby_quantile_NA_float[Float32]`、`[Float64]`，`test_groupby_quantile_allNA_column[Float32]`、`[Float64]`），233 passed | `trials/env_noop_current.json`（试跑） |
| gold | 1：237/237 | `trials/env_gold_current.json`（试跑） |
| C0 | **1**：237/237（触发反例） | `INV/ledger_C0.jsonl:1`（协调者正式评分） |
| C1 | 1：237/237 | `INV/ledger_C1.jsonl:1`（协调者正式评分） |

### 5.2 修订草案下的验收

新键简写为"新键"；结果文件为 `trials/rev_<候选>.json`。

| 候选 | 补丁 | 角色 | 应得 | 应不符的键 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，238/238；新键 PASSED | 1 |
| noop | 无 | — | 0 | 原 4 个目标键 + 新键 | 0，恰好这 5 键。新键的失败摘要截成 `- T...`，与题面的 TypeError 一致 | 0 |
| C0 | `cands/pandas_4ec8_C0.patch` | 第 3 步退化候选，触发反例 | 0 | 只有新键 | 0，恰好新键；失败摘要截成 `- A...`，与断言失败（AssertionError）一致；其余 237 键全 PASSED | **1**（正式） |
| C1 | `cands/pandas_4ec8_C1.patch` | 合理替代解（统一的掩码数组分支） | 1 | — | 1，238/238 | 1（正式） |

**判读**：
- **正对照 1、noop 0**：成立。gold 本身满足公开要求：私有对照在 astype / reindex / 除法三种输入上都给出正确值（`INV/pcheck_gold.json`），devcheck 的 8 个公开变体全部 OK（`DC/private_control.json:38`）。
- **误判已纠正**：C0 在当前材料正式得 1，修订后试跑得 0，而且只在新键失败。也就是说，它只因"掩码位底层不是 NaN"这一点被拒。
- **没有误拒**：C1 仍得 1。
- **旧键不受影响**：noop、gold 的旧 237 键，修订前后逐键相同；C0、C1 修订后旧键全部 PASSED，与当前材料的正式结果一致。新测试不改全局状态，所以在当前材料上因旧键得 0 的候选，修订后仍为 0。
- **日志截断说明**：试跑工具只保留日志末尾 8000 字符。`-rA` 输出的 238 行结果摘要把 FAILURES 段挤掉了，只剩被截短的摘要行（`FAILED ...nonnan_storage - A...` / `- T...`）。C0 在第一段得 1.0（应为 2.0）这一具体数值，由私有对照 `INV/pcheck_C0.json` 佐证：同一表达式 `pd.Series(a).groupby([0, 0, 0]).quantile(0.5)` 得 `[1.0]`。正式评分的日志是完整的，协调者应在那里确认 C0 的断言失败落在 `HT':296`。

### 5.3 诊断试跑（不进 acceptance）

- **目的**：确认第二段（reindex、两组）单独也能挡住 C0，而不只是第一段先失败把它掩住。
- **做法**：同一锚点、同一键名，新函数只保留第二段（`trials/diag_seg2_draft.json`，sha256 `0dd86b63…`）；期望映射同上；候选 C0。
- **结果**：`mismatch`，只有新键 FAILED（摘要 `- A...`），其余 237 键 PASSED（`trials/diag_seg2_C0.json`）。与源码推断一致：b 组只有一个有效值，内核按底层数值排序（`W/pandas/_libs/groupby.pyx:843-844`），C0 把掩码位的 0.0 排在 4.0 前面，于是取到 0.0（`:857-866`）。

## 6. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**：
- **含 NA 的浮点扩展列能算，NA 被忽略**：题面场景 `test_groupby_quantile_NA_float[Float64]`（值用 0.2，不是示例的 2.5）及其列表 q 断言；`[Float32]` 同一测试。
- **全 NA 组得缺失值**：`test_groupby_quantile_allNA_column[Float32]`、`[Float64]`。
- **忽略 NA 与掩码位底层存储无关**（新增）：`test_groupby_quantile_NA_float_nonnan_storage`，两种 NA 来源，单组与两组。
- **结果 dtype 为 float64**（P3）：原 4 个目标键。
- **旧行为**：与公开文件相同的 222 键（object 报错并带警告、`Int64` / `boolean` 可空数组、插值与整数回转、datetime / timedelta、q 越界、缺失分组键、丢列警告、`axis=1`），以及 base 上已通过的 11 个新参数键。

**仍未覆盖，维持登记**：
- **T3**：
  - DataFrame 入口的浮点扩展列、混合列不丢列、无 NA 时 dtype 的旧行为；
  - 另一种挡不住的候选：只在部分 NA 来源上把掩码位改写成 NaN（例如只改 astype 与 take 的填充），quantile 里仍直接用 `_data`。它能过新测试，但对 `Int64` 除法和直接构造的 `FloatingArray` 仍会算错。目前没有这类候选的实例，按 v1 §8 抽查。
- **P3**（dtype）、**P4**（题面写 "group `1`"，没提 FutureWarning）、**X1**（`7dd34ea7` 的公开初态含本题 gold 与原来 3 个新测试）：照旧。
- **新测试没有外泄**：它是新写的。按新键名 grep 了 v3 的 7 个 pandas 公开工作树，没有命中；第一段的构造写法（`dtype="Int64").astype("Float64")`）在这些工作树的 `pandas/tests` 下也没有命中。

## 7. 正式落地要点（交协调者）

1. **隐藏测试**：`test_1.py` 此前没有修订（r2e-mr-006 改的是 `conftest.py`），`formalize_revisions.py` 能直接生成 `hidden_test_text_replace` 条目；可用 `revision_draft.json` 的 `revised_hidden_test_sha256` 核对重算结果。
2. **期望文件需要人工合并**（修订单格式问题，不涉及语义）：
   - 当前修订单 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v7.json` 已有 r2e-mr-007（`expected_file_replace`，来源 `19f481a2…` → `bdf1ddf5…`）。ingest 拒绝同一题同一目标两条修订（`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:416-417`），`rh2/experiments/r2e_lifecycle_20260929/formalize_revisions.py:120` 也会在这里停下。
   - 可行做法：新写一条 `expected_file_replace` 取代 r2e-mr-007。
     - `sha256_before` 与 r2e-mr-007 相同（来源原文 `19f481a2…`）；
     - `sha256_after` = `f7d93a07…`（修订后文件 = r2e-mr-007 的修订后文件末尾加一行）；
     - `expected_change`：`removed` 仍是那 2 个旧 ERROR 键，`added` 为 r2e-mr-007 的 13 键加本次 1 键（共 14），`changed` 为空；
     - r2e-mr-007 的内容原样保留在新条目里，依据写 T0-6 加 v1 §9 D4。
   - 另一种做法是让 ingest 支持同一目标的链式修订。那要改生产代码，不在本轮范围。采用哪种由协调者定。
3. **重建派生镜像材料**（隐藏测试树摘要会变），然后正式评分至少跑 gold、noop、C0、C1，按 §5.2 判读。在完整日志里确认新键确实执行（有 PASSED / FAILED 行），以及 C0 的断言失败落在 `HT':296`。
4. **送 Codex 复核**。

## 8. 边界

- **只做 R-c**：不改题面，不删键，不放宽已有断言，期望不照抄 gold 输出；依据都是公开的，不涉及 P5 或其它模板外事项，**不需要用户决定**。
- 没写 `s2_r2e` 下的正式材料，没改生产代码。远端只用了建目录、上传、试跑、取回四类命令，同一时间最多 2 个试跑。
- **之后按正式评分结果重判 v1 用途**（`card.md` 的用途表）：训练候选要的正面证据（核心断言、noop 0 / gold 1、第 2、3 步结果）届时齐全，另待 Codex 复核；留出评测仍为 no（修订后只能作标明版本的自建题，另有 X1 与审查暴露）。
