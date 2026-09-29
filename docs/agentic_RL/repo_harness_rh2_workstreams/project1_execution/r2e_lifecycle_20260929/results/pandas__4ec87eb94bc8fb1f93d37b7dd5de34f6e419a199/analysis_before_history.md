# pandas__4ec87eb9 私有主审：读历史前的初判

- 角色：R2E 私有主审（单题闭环试行 2026-09-29，按统一标准 v1）。本稿在打开任何历史调查之前写成。没有读 history 包、`r2e_env_repair_20260924/`、各 `*review*` 目录、本批 README / board / assignments，也没有读 `revisions.json` 的 `evidence` 所指的修订说明和 dryrun 目录。
- 性质：静态阅读，加上已有的原始运行证据（账本与 eval log）。没有运行项目代码，也没有开容器。文中"预计"都是读代码得出的推断；需要协调者实跑的内容集中在 §10 和附录。
- 路径简写：
  - `PUB/` = `runs/r2e_static_prep_20260924/v3/public/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`，`WT/` = `PUB/worktree/`
  - `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/`
  - `NOOP1` / `NOOP2` = `runs/r2e_t0_batch2_20260924/replay_b3/eval_logs/evallog_replay-r2e-t0-batch2-pan_4ae6eaa6.eval.log` / `…_c3f7181e.eval.log`
  - `GOLD1` / `GOLD2` = 同目录的 `…_0ac6a231.eval.log` / `…_3b39925f.eval.log`
  - 其余路径都相对仓库根。

## 0. 结论速览（暂定）

- **题目**：对含 `pd.NA` 的 `Float64` / `Float32` 列调用 `GroupBy.quantile` 会抛 `TypeError`。gold 在 `quantile` 的 `pre_processor` 里给浮点扩展数组加了一条分支：`vals.to_numpy(dtype=float, na_value=np.nan)`，并设 `inference = float64`（`PRIV/gold.patch:17-19`）。
- **当前材料**：已应用 r2e-mr-006/007，期望共 237 键，全部 PASSED。
  - noop 两次都是 233/237，4 个目标键都以题面那条 `TypeError` 失败。
  - gold 两次都是 237/237。
  - 修订只补回了测试 fixture。我逐字核对过，没有弱化断言。
- **最主要的发现（待实跑确认）**：隐藏测试里所有 Float 输入都用列表构造，所以掩码位置底层存的恰好是 NaN（`WT/pandas/core/arrays/floating.py:174`）。
  - 因此退化补丁 C0（把底层 `_data` 直接交给 Cython 内核，不按 mask 置 NaN）预计能 237/237 得 1。
  - 但 C0 在常见输入上不会忽略 NA。`reindex` 引入的 NA 底层是 0.0；`Int64` 转 `Float64`、或 `Int64 / 1` 得到的 NA 底层是 1.0。内核按底层数值排序，所以这些值会混进分位数。
  - 例如题面自己的数据，只是 NA 改由 `reindex` 引入：`[2.5, NA]` 的中位数 C0 会算成 0.0，正确值是 2.5。
  - 若正式评分得 1：v1 §4 第 3 步命中，定为 S1（T2b），建议走 R-c（草案见附录 B）。
- **次要发现**：
  - 结果 dtype：题面没写，测试钉死 numpy `float64`。公开旧行为支持这一读法：同一方法对 `Int64` / `boolean` 返回 float64，有公开测试；无 NA 的 `Float64` 在 base 上也返回 float64。登记为 P3，有依据，不算 T1。
  - 另有若干 T3 覆盖缺口。
  - X1：pandas `7dd34ea7` 的初态逐字包含本题 gold 和三个新测试。
- **暂定处置**：S1（T2b），conditional，等 C0 的正式评分结果；`training_candidate` 与 `capability_comparison` 都是 conditional。
- **唯一最值得先做的下一步**：用正式评分跑 C0，同时做一次私有行为对照（§10.1，附录 A）。

## 1. 材料与运行证据

| 项 | 事实 | 证据 |
| --- | --- | --- |
| 当前材料 | 修订 r2e-mr-006（新增私有 `r2e_tests/conftest.py`，放入两个 fixture）+ r2e-mr-007（期望文件：删 2 个 ERROR 键、加 13 个 PASSED 键）；期望 237 键全 PASSED | `PRIV/revisions.json`；`PRIV/expected_output.json`；`PRIV/grading_bundle.json` 的 `material_revisions` |
| 隐藏测试构成 | 隐藏 `test_1.py` = 公开 `WT/pandas/tests/groupby/test_quantile.py` + 3 个新函数（隐藏文件 251-289 行），其余逐字相同（本地 `diff` 核对） | `PRIV/hidden_tests/test_1.py:251-289` |
| noop（current） | 两次都是 239 collected、4 failed、233 passed、2 skipped；两份日志除时间与内存地址外逐字相同 | `NOOP1:24, 1305-1310`；`NOOP2` |
| gold（current） | 两次都是 237 passed、2 skipped；投影 `included_paths=[pandas/core/groupby/groupby.py]`，`git_apply` 成功 | `GOLD1:254-272`；`runs/r2e_t0_batch2_20260924/replay_b3/ledger_b3_gold.jsonl` 第 1-2 行 |
| 运行身份（旧机） | `rh2-r2e-derived/pandas:4ec87eb94bc8-r2e_derive_v1m2`，image ID `sha256:b4ff9483…`，配方 `r2e_derive_v1+material_v2`（`sha256:b5a70d04…`）；grader 导入 `/testbed/pandas/__init__.py`；2 CPU / 4 GiB / tmpfs 1 GiB / `deny_all`；内存峰值约 762 MB；测试段约 2.3-2.4 s | `ledger_b3_noop.jsonl` 第 1 行的 `observations`、`policy`、`resource` |
| 修订前（superseded） | 来源材料是 226 键 = 224 PASSED + `test_groupby_quantile_NA_float` / `_NA_int` 两个 ERROR（`fixture 'any_float_dtype' not found`）。当时 noop 只错 `allNA_column` 两键。M3 独立 runner 在来源镜像上得到同样的 224 passed + 2 errors | `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-p_e47e4f78.eval.log:31-45, 793-798`；`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/pandas/4ec87eb94bc8/gold/a1/test_output.txt:13-26, 255-258` |
| 新机器 | 派生镜像已重建，但本题当前材料在新机上的 noop / gold 与 devcheck 结果我还没看到 | 待协调者提供 |

## 2. 隐藏测试展开

**目标键**（noop 与 gold 结果不同的键，共 4 个）：

1. `test_groupby_quantile_NA_float[Float32]` 与 `[Float64]`（`PRIV/hidden_tests/test_1.py:251-265`）。
   - 输入：`DataFrame({"x": [1, 1], "y": [0.2, np.nan]}, dtype=any_float_dtype)`，键列 `x` 同样是扩展 dtype。
   - 断言一：`df.groupby("x")["y"].quantile(0.5)` 等于 `Series([0.2], dtype=float, index=[1.0] 且 name="x", name="y")`。
   - 断言二：`quantile([0.5, 0.75])` 等于 `[0.2, 0.2]`，索引为 `MultiIndex(([1.0], [0.5, 0.75]), names=["x", None])`，默认 float64。
   - 两处都用 `tm.assert_series_equal`，默认检查 dtype。
   - fixture 来自私有 conftest，参数为 `tm.FLOAT_NUMPY_DTYPES + tm.FLOAT_EA_DTYPES`（`PRIV/hidden_tests/conftest.py:10-21`）。
2. `test_groupby_quantile_allNA_column[Float64]` 与 `[Float32]`（`test_1.py:280-287`）。
   - 输入 `[pd.NA] * 2`，期望 `Series([nan], dtype=float, index=[1.0] 且 name="x", name="y")`。

**调用路径**（base）：

1. `quantile` 的标量分支调用 `_get_cythonized_result(numeric_only=False, needs_mask=True, cython_dtype=float64)`（`WT/pandas/core/groupby/groupby.py:2472-2484`）。
2. `pre_processor` 依次判断 object / 整数 / 布尔扩展数组 / datetime / timedelta。`FloatingArray` 都不命中，落到 `np.asarray(vals)`（`2442-2457`）。
3. `BaseMaskedArray.to_numpy(dtype=None)` 返回 object 数组，掩码位置填 `pd.NA`（`WT/pandas/core/arrays/masked.py:280-299`）。
4. `vals.astype(float64)` 抛出 `TypeError`（`groupby.py:2957`）。
5. 异常被捕获，发 FutureWarning，因为没有输出列，按原消息重抛（`3026-3047`）。

gold 让 `FloatingArray` 在第 2 步改走 `to_numpy(float, na_value=nan)`。mask 仍由 `isna(values)` 从原数组取（`groupby.py:2963`）。

内核 `group_quantile` 的做法（`WT/pandas/_libs/groupby.pyx:828-868`）：
- 只用 mask 数每组有多少个非缺失值（`833`）。
- 排序用的是数值本身（`844`）。
- 取位置时假定缺失值排在组末（`857, 868`）。这依赖掩码位置是 NaN，这一点是 §6 第 3 步的关键。

**回归键**（233 个）：
- 222 个与公开测试文件逐字相同：插值方式、整数推断回转、datetime / timedelta、object 报错并带 FutureWarning、q 越界报错、分组键含缺失值、`Int64` / `boolean` 可空数组、丢列警告、`axis=1`。
- 另 11 个是新测试里 base 已经能通过的参数：`NA_float` 的 3 个 numpy 浮点 dtype，以及 `NA_int` 的 8 个可空整数 dtype。注意 `NA_int` 其实不含 NA，只测 `Int*` 扩展数组的 Series 与 DataFrame 两个入口。
- gold 新分支只作用于"扩展数组且浮点 dtype"，不触及这 233 键的输入。
- 阅读范围：`test_1.py` 与 `conftest.py` 全文读过；198 个 `test_quantile` 参数组合没有逐个推演，只核对了它们都是 numpy dtype，不经过新分支。

## 3. 需求—断言双向表

正向：公开要求 / 合理旧行为 → 断言。

| # | 公开要求 / 合理旧行为 | 依据 | 键与决定性断言 | 覆盖 | 执行证据 / 待做 |
| --- | --- | --- | --- | --- | --- |
| R1 | 题面例：`Float64` 列含 NA，`SeriesGroupBy.quantile(0.5)` 不报错，NA 被忽略 | `PUB/user_prompt.txt`（Example / Expected Behavior） | `NA_float[Float64]` 断言一（值用 0.2，不是示例的 2.5） | 覆盖 | noop FAILED（`NOOP1:291-298, 547-549`）；gold PASSED（`GOLD1:258`） |
| R3 | 列表形式的 q 同样要能算 | 标量 q 与列表 q 共用 `pre_processor`（`groupby.py:2472-2499`） | `NA_float[Float*]` 断言二 | 覆盖 | 同上 |
| R4 | `Float32` 同样要能算 | 同属 `FloatingArray` | `NA_float[Float32]`、`allNA[Float32]` | 覆盖 | noop FAILED（`NOOP1:32-41, 288-290`）；gold PASSED |
| R6 | 全为 NA 的组结果为缺失值 | 内核在 `non_na_sz == 0` 时写 NaN（`groupby.pyx:852-853`）；公开测试中全 NaN 浮点组得 NaN | `allNA_column[Float*]` | 覆盖 | noop FAILED（`NOOP1:550-558, 807-809`）；gold PASSED（`GOLD1:267-268`） |
| **R5** | "忽略 NA" 只看 mask，与掩码位置底层存的数值无关 | 题面 "ignoring the pd.NA value"；`FloatingArray` 文档写明 "mask … True is missing"（`WT/pandas/core/arrays/floating.py:196-197`）；常见操作会在掩码位置留下非 NaN（§6 第 3 步） | **无**：所有 Float 输入的掩码位置都是 NaN | **缺失** | C0 实跑（§10.1）；R-c（附录 B） |
| R7 | 结果 dtype 为 numpy `float64` | 题面未写。支持 float64：同一方法对 `Int64` / `boolean` 返回 float64 的公开测试（`WT/pandas/tests/groupby/test_quantile.py:215-236`）；无 NA 的 `Float64` 在 base 上返回 float64（`groupby.py:2457, 2957`）；1.1.0 修同类 `Int` 问题的记录（`WT/doc/source/whatsnew/v1.1.0.rst:1135`）。反向证据：`Series.quantile` 对掩码数组尽量保留原 dtype（`WT/pandas/core/array_algos/quantile.py:44-46, 185`）；groupby 的 mean / median 保留浮点扩展 dtype（`WT/pandas/core/groupby/ops.py:307-311`） | `NA_float` / `allNA` 里的 `dtype=float` 加 `assert_series_equal` 默认 dtype 检查 | 覆盖（有公开依据的约定，另一读法存在） | 可选 C2（§10.3） |
| R2 | `DataFrameGroupBy` 入口，以及混合列 frame 不再静默丢掉 Float64 列 | 标题写的是 `GroupBy.quantile`；两个入口共用 `_iterate_slices`（`groupby.py:3019-3043`） | 浮点扩展数组无；`NA_int` 覆盖 `Int` 的 frame 入口（`test_1.py:275-277`） | 缺失（T3） | — |
| P1-P5 | object 列报错并带警告；`Int64` / `boolean` 返回 float64；插值与整数回转；datetime / timedelta / q 越界 / 缺失分组键；只在标量 q 时发丢列警告 | 公开测试 | 公开文件对应的 222 键 | 覆盖 | noop 与 gold 都 PASSED |
| P6 | 无 NA 的 `Float64` 仍返回 float64（旧行为） | 读代码推知 | 无 | 缺失（T3，轻微） | 公开命令 `variants_float_masked` 会打印 |

反向：关键断言 → 公开依据。

- 4 个目标键的数值（0.2 / NaN，标量 q 与列表 q，Float32 与 Float64）对应 R1、R3、R4、R6，是题面一般表述的实例，没有超出题面。
- `dtype=float`：来自 R7 的公开旧行为，题面本身没写（P3，登记）。
- 索引 `Float64Index([1.0], name="x")`：这是 base 对 `Float64` 键列的分组行为，修复不改变它。同样的期望在 noop 下的 numpy 浮点参数上已经通过（`NOOP1:1292-1294`）。
- 另外 11 个新增回归键在 base 上已通过（`NOOP1:1292-1302`），不构成新需求。
- 没有精确报错文案断言，没有 mock，也不约束内部 helper 名或调用顺序。

## 4. R2E 专项

- **(a) 非 PASSED 期望键**：当前没有。修订前的 2 个 ERROR 键是 fixture 缺失造成的无效键，已由 r2e-mr-007 移除，并换成展开后的 13 个键。
  - 更完整的正确修复不会让任何键翻转，唯一例外是把结果改成 `Float64` 掩码 dtype：4 个目标键会因 dtype 失败，见 R7 与 P3。
  - 两个 SKIPPED 由测试代码无条件跳过（`test_1.py:38-41`），不成键，候选影响不到。
- **(b) 题面报错是否出现在 noop 目标键里**：出现，4 个目标键都是 `TypeError: float() argument must be a string or a number, not 'NAType'`，在 `groupby.py:3047` 重抛（`NOOP1:288, 547, 807, 1067`），与题面逐字一致。
  - 题面没提先出的 FutureWarning；评分侧有 `-W ignore`，不影响。
- **(c) 题面是否泄漏修法**：没有。题面只有症状和示例，不涉及 `pre_processor`、`to_numpy` 或 mask。
- **(d) 依赖测试辅助、搬迁伪影、跨文件撞键**：
  - 搬迁伪影（原 `pandas/conftest.py` 不再加载，导致 fixture 缺失）已被修订补上。
  - 隐藏测试与私有 conftest 都导入候选可改、评分时不重置的 `pandas._testing`：用它的断言函数，以及 `FLOAT_EA_DTYPES` 等 dtype 列表（`WT/pandas/_testing/__init__.py:133-136`）。
    - 改 dtype 列表会改变参数化，使键集合不符，只会判 0。
    - 改断言函数属于所有 pandas 题共有的通用控制面风险，不在本题展开。
  - 只有一个测试文件，不会撞键。
- **(e) 时间、随机、资源敏感**：没有。
  - `RandomState(0)` 是确定的；防段错误的 100 次循环也是确定的。
  - 整个测试约 1 s；两次 noop、两次 gold 逐键相同。
- **(f) 修订核对**：
  - r2e-mr-006：私有 conftest 的两个 fixture 与 base 的 `WT/pandas/conftest.py:1258-1269` 和 `1329-1343` 逐字相同（本地 `diff` 为空），只导入 `pytest` 与 `pandas._testing`，没有 autouse 或 hook。
  - r2e-mr-007：让题面场景 `NA_float[Float*]` 真正执行，是加强，不是弱化。
    - 修订前的目标键只有 `allNA` 两个。那时"浮点扩展数组一律返回 NaN"这类退化补丁就能得 1。
    - 新增的其余 11 键在 base 上已通过，没有扩大需求。
    - 期望取 PASSED 的依据是：这些都是上游修复提交自带的测试，本意就应当通过；不是照抄 gold 的输出。
  - 缺项：修订版没有独立 runner 的同版本对照（环境卡 §1 说明改用一次性容器试跑）。那个 dryrun 目录我没有读。

## 5. gold 检查

- **是否修到原例**：修到。`FloatingArray` 在新分支里转成 float64，掩码位置置为 NaN。R1、R3、R4、R6 都满足，R5 也满足，因为它不依赖底层存储。R2 的 frame 入口共用同一条路径，也能修到（读代码推知）。
- **结果 dtype**：float64，与 `Int` / `boolean` 的约定一致。
- **无关改动**：没有。只多了一个 `is_float_dtype` 导入和 3 行分支。
- **未测的回归面**：`is_float_dtype` 对浮点子类型的 `SparseArray` 也返回 True，所以稀疏浮点数组也会改走 `to_numpy`。按读代码判断，结果与原来的 `np.asarray` 相同，但没有测试。
- **初态失败位置**：执行证据（`NOOP1`）与源码推断（`groupby.py:2957`，以及公开读者的 `locate_root_cause` 命令）一致。
- **更正公开读者的一处说法**：公开读者的路线 3（只改 Cython 内核）单独做修不好本题，因为 `TypeError` 在调用内核之前、`groupby.py:2957` 的 Python 代码里就抛出了。

## 6. v1 §4 严重度五步（暂定）

1. **核心要求有没有直接断言**：有。`NA_float[Float64]` 在题面入口上断言了"NA 被忽略"之后的结果值。不命中。
2. **核心断言是否只用题面示例的字面值**：不是。值是 0.2 而不是 2.5，另外还有 Float32、列表 q 和全 NA 组。按严格版本也不命中。
   - 但所有输入都和示例一样由列表构造，掩码位置都是 NaN。这个偶然的共同性质留给第 3 步去探测。
3. **退化探测**：C0 = 在 gold 同一个 `elif` 位置写 `out = vals._data`，属于"抑制症状"，也就是跳过缺失值转换。
   - 预计能 237/237 得 1。4 个目标键的输入掩码位置都是 NaN，其余键不经过这个分支。
   - 违反的公开要求：题面 "correctly handling and ignoring the pd.NA value"；`FloatingArray` 文档规定是否缺失看 mask。
   - 能暴露违例的输入都是常见操作，不是边缘路径：
     - `reindex` / `take` 在新 NA 位置填 `_internal_fill_value = 0.0`（`masked.py:382`、`floating.py:243`）。
     - `Int64` 转 `Float64` 的快速路径保留整数数组构造时在掩码位置填的 1（`masked.py:312-320`、`integer.py:228`）。
     - `Int64` 除法在底层数据上直接运算，再套回原 mask（`WT/pandas/core/arrays/numeric.py:143`、`integer.py:469-475`）。
   - 按内核逻辑（`groupby.pyx:833, 844, 857`）推算：
     - `pd.Series([2.5], dtype="Float64").reindex([0, 1])` 分成一组：C0 得 0.0，正确值 2.5。
     - `pd.Series(pd.array([1, None, 3], dtype="Int64").astype("Float64"))` 分成一组：C0 得 1.0，正确值 2.0。
   - **若正式评分得 1，即为 S1（T2b）。** 证据现在只到源码推断这一层。
4. **已有候选在同一核心要求的其它实例上违规**：目前没有真实模型候选。审查中构造的候选只有 C0（已归入第 3 步）和 C2（dtype 读法不同，按 R7 的分析不算违反公开要求）。没有新增命中。
5. 要等第 3 步的结果；若 C0 实跑得 0，再按 S2 登记已知缺口。

## 7. 问题清单（v1 编号）

| 编号 | 问题 | 严重度 / 状态 | 证据层次 | 去向 |
| --- | --- | --- | --- | --- |
| T2（T2b，待定） | 隐藏测试不区分"按 mask 忽略 NA"与"依赖掩码位置恰好是 NaN"，C0 预计得 1 | S1，conditional | 源码推断；正式评分待跑 | R-c：补一个掩码位置非 NaN 的实例（附录 B） |
| P3（有依据） | 结果 dtype 题面未写，测试钉死 float64；另一读法（保留 `Float64`）也说得通 | 登记，不算 T1 | 读代码与公开测试 | 不修订。若真实模型给出"其余全对、只有 dtype 为 `Float64`"的补丁，作为规格争议待复核样本，保留原始 reward，不自动豁免 |
| T3 | 浮点扩展数组的 frame 入口与混合列不丢列（R2）、无 NA 时 dtype 的旧行为（P6）、每组多个有效值的插值没有断言 | 登记 | 静态 | R-c 草案的第二个实例顺带覆盖"两组、多个有效值"；其余按 §8 抽查 |
| X1 | pandas `7dd34ea7` 的初态含本题 gold 与三个新测试；本题 base 含同仓其它题的修复与测试 | 登记 | 机械比对 + 本地核对 | 见 §8 |
| P4（轻微） | 题面写 "group `1`"，实际索引标签是 1.0（键列同为 `Float64`）；题面没提先出的 FutureWarning | 登记 | 静态 | 无需处理 |
| 通用（非本题） | 隐藏测试依赖候选可改的 `pandas._testing`；候选还可以在 `/testbed` 根目录新建 `conftest.py` | 不在本题处置 | 静态 | 引用共享控制面审查 |

## 8. 题目关系（第 8 方面）

- **本题 gold 已在另一题的公开初态里**：`cross_task_gold_scan.json` 记录本题 gold 的 4 行在 `pandas__7dd34ea7…` 的公开工作树里逐字出现（4/4）。
  - 我打开了该题的**公开包**核对：`runs/r2e_static_prep_20260924/v3/public/pandas__7dd34ea7a121ce4282ce095b058c5c46568f07af/worktree/pandas/core/groupby/groupby.py:2685-2687` 与 `:68` 确有这几行。
  - 该题 `test_quantile.py:250, 267, 280` 就是本题的三个新测试（`cross_task_test_scan.json` 同样命中）。
  - 那道题是另一个问题（`RangeIndex.difference`），base 为 `f5c224215ad0`。
- **反方向，本题 base 里包含的其它题的修复或测试**：
  - 按 gold 逐字比对命中：`19c5eea5`（2/2）、`877876098c`（5/5）、`f656217a`（12/12）。
  - 只按测试函数名命中：`294cbc8d`、`32dd55cb`。我在 `WT/pandas/tests` 里抽查到对应函数名确实存在；没有读这些题的私有包，所以只凭函数名，可能有同名巧合。
- **影响**：按 D3 按仓库划分，同仓的题会落在同一侧。训练时要控制同源重复采样；如果以后改按时间划分，要核对 `7dd34ea7` 与本题的前后关系。
- **其它**：本题是小型 Python 缺陷修复。外部可达答案是上游 GH#42849 的修复，但解题侧不联网。审查暴露：本稿作者读过 gold 与隐藏测试。

## 9. 开发需求（逐阶段）

| 阶段 | 需求 | 当前事实 | 证据级别 |
| --- | --- | --- | --- |
| 准备 | 派生镜像（当前材料配方 `r2e_derive_v1+material_v2`） | 旧机 image ID `b4ff9483…`；新机已重建，ID 待记 | 旧机实测；新机待核 |
| 解题：导入 | 用 `/testbed` 的就地构建 pandas | grader 观测到导入路径 `/testbed/pandas/__init__.py`；环境卡写 actor 的 `python` = `/testbed/.venv/bin/python` | grader 实测；本题 actor 待验（devcheck） |
| 解题：依赖 | 不需要新包 | Python 3.8.20、pytest 8.3.4、hypothesis 6.113.0（评分日志）；numpy 版本未知（日志没打印） | grader 实测；actor 与 grader 用同一个 `.venv` |
| 解题：资产、网络 | 都不需要 | grader `deny_all`；解题侧不联网 | 实测 / 提示 |
| 解题：权限 | 写 `/testbed/pandas/core/groupby/groupby.py` | agent uid 54321 可写 `/testbed`（`PUB/environment_brief.md`） | 环境阶段实测；actor 待验 |
| 构建 | 纯 Python 修复不需要构建 | 评分侧 `RH2_INSTALL_SKIPPED=1`，不重编。改 `.pyx` 的路线既不必要，也不能单独修好本题 | 实测 + 静态 |
| 公开测试 | `python -m pytest pandas/tests/groupby/test_quantile.py`，base 与 gold 预计都是 222 passed、2 skipped | 静态计数：隐藏文件 = 公开文件 + 15 键 | actor 待验 |
| 提交边界 | 只改非测试源码 | 初态已有改动（`pandas/__init__.py`、`_version.py`、`setup.cfg`、`versioneer.py`，以及删掉的 `pyproject.toml`）来自安装，与本题无关，不要还原；gold 投影只含 `groupby.py` | 实测 |
| 墙钟 | 快 | 隐藏测试的 pytest 用时 0.85-0.96 s，测试段约 2.4 s，内存峰值约 762 MB | 实测 |

公开读者的 `commands.json`（6 条）足够用于开发核对，不需要修改。其中 `variants_float_masked` 的 `masked_slot_not_nan` 一项正好能用公开方式识别 C0 这类补丁，也适合作为 R-c 之前的事后审计。

## 10. 需要协调者实跑（私有，不进解题者说明）

补丁与脚本全文见附录 A、B。

1. **C0 退化候选，正式评分 1 次（当前材料）**：
   - 预计 1.0（237/237）。
   - 同时核对三件事：账本 `projection.included_paths` 含 `pandas/core/groupby/groupby.py`；补丁应用成功；日志里 4 个目标键确实执行且 PASSED。
   - 另做一次私有行为对照（附录 A-2），分别在 base+gold 与 base+C0 上跑：gold 应得 2.5 / 2.0 / 2.0；C0 预计得 0.0 / 1.0 / 1.0；并打印掩码位置的底层值作为佐证。
   - 若 C0 得 1 且行为对照如预期：S1（T2b）成立，进入第 6 项。
   - 若得 0：先查清 C0 失败在哪个键，再重新判定。
2. **C1 合理替代解（可选，低优先级）**：统一的 `BaseMaskedArray` 分支。预计 1。只用来确认测试不约束实现位置，不改变处置。
3. **C2 `Float64` 结果候选（可选诊断）**：预计 0，且只有 4 个目标键因 dtype 不匹配而 mismatched。不改变 P3 的判断，除非真实模型出现这类补丁。
4. **devcheck 核对要点**（公开命令）：
   - `env_import_version`：记下 numpy 版本；确认 pandas 与 `_libs` 的 `.so` 都来自 `/testbed`。
   - `repro_issue_example`：base 上应出现题面那条 `TypeError`。
   - `variants_float_masked`：base 上 6 项 ERR、1 项 BAD、1 项 OK；私有 gold 对照下 8 项全 OK，尤其 `masked_slot_not_nan`，它同时验证 R-c 的正对照成立。
   - `public_test_quantile`：base 与 gold 都应为 222 passed、2 skipped。
   - `related_quantile_paths`：应通过。
   - 以上任何一项不符都要解释，不能直接核销。
5. **新机器、当前材料下的 noop 与 gold 各复评一次**（若 devcheck 没有包含）：noop 应为 233/237，mismatched 是那 4 个键；gold 应为 237/237。
6. **若 C0 命中，做 R-c 修订与验收**（附录 B）：
   - gold 1、noop 0、C0 0（只有新键 FAILED）、C1 1。
   - 保存新版本与父版本、理由和触发反例 C0，交 Codex 复核。

## 11. 暂定处置与用途（v1 §2）

- **状态**：`needs_review`。原因：第 3 步退化探测待实跑；若命中需要 R-c；actor 条件待 devcheck。
- **严重度**：S1（T2b），conditional。
- **四项用途（暂定）**：
  - `problem_localization`：yes。
  - `capability_comparison`：conditional。还差两项：新机 devcheck 与当前材料的 noop / gold 复评；在 R-c 之前，得 1 的补丁要用 `masked_slot_not_nan` 这类检查做预登记的事后审计。
  - `training_candidate`：conditional。先跑 C0；若命中，要等 R-c 验收与 Codex 复核。
  - `heldout_candidate`：conditional，偏 no。本题材料已修订，只能作"标明版本的自建题"；有 X1 关联；审查暴露已记录。

## 八方面覆盖与未查项

| 方面 | 已查 | 未查 / 未知 |
| --- | --- | --- |
| 公开需求 | 题面、公开读者报告、公开测试、相关源码 | 模型实际收到的消息（`user_prompt.txt` 只是静态渲染） |
| 材料与初始问题 | 两次 noop 的失败位置与消息；base 源码路径；gold 的行号与 base 对应 | 新机器上的复现 |
| 测试是否测到要求 | 4 个目标键逐项追过；回归键按来源分组核对 | 198 个 `test_quantile` 组合没有逐个推演（不经过新分支） |
| 是否误拒合理解 | 没有精确文案或实现形态约束；dtype 有公开依据 | C2 未实跑 |
| 回归与 gold 完整性 | gold 对 R1-R6 的读码核对；稀疏浮点路径 | 稀疏浮点、`_get_cythonized_result` 其它调用方的实跑 |
| agent 开发条件 | 环境卡、`environment_brief.md`、评分侧实测 | actor 侧（devcheck）、numpy 版本 |
| 交付与评分边界 | gold 投影与应用；私有 conftest 的作用范围；`pandas._testing` 依赖 | 共享控制面审查没有复读 |
| 题目关系与用途 | 两份跨题比对；打开 `7dd34ea7` 公开包逐字核对 | 其它题私有包（按规定不读） |

## 附录 A：候选补丁（针对 base 的 `pandas/core/groupby/groupby.py`）

**A-1 C0（第 3 步退化候选）**。只凭 gold 的修改位置就能写出。`BaseMaskedArray` 已在该文件第 80 行导入。整数和布尔掩码数组已被前面的分支处理，所以只有 `FloatingArray` 会落到这里。hunk 里的空行上下文行首有一个空格。

```diff
--- a/pandas/core/groupby/groupby.py
+++ b/pandas/core/groupby/groupby.py
@@ -2453,6 +2453,8 @@ class GroupBy(BaseGroupBy[FrameOrSeries]):
             elif is_timedelta64_dtype(vals.dtype):
                 inference = np.dtype("timedelta64[ns]")
                 out = np.asarray(vals).astype(float)
+            elif isinstance(vals, BaseMaskedArray):
+                out = vals._data
             else:
                 out = np.asarray(vals)
 
```

- 违反：题面 "ignoring the pd.NA value"。是否缺失由 mask 决定（`floating.py:196-197`），C0 却让掩码位置的底层数值参与排序与插值。
- 预计正式评分：1.0，因为隐藏输入的掩码位置都是 NaN。

**A-2 私有行为对照脚本**。分别在 base+gold 与 base+C0 上用 `/testbed/.venv/bin/python` 运行，身份不限。

```python
import pandas as pd
a = pd.array([1, None, 3], dtype="Int64").astype("Float64")
print("astype data/mask", a._data, a._mask)                      # 预计 [1. 1. 3.] [False  True False]
print("astype", pd.Series(a).groupby([0, 0, 0]).quantile(0.5).tolist())    # gold [2.0]；C0 预计 [1.0]
b = pd.Series([2.5], dtype="Float64").reindex([0, 1])
print("reindex data/mask", b.array._data, b.array._mask)         # 预计 [2.5 0. ] [False  True]
print("reindex", b.groupby([1, 1]).quantile(0.5).tolist())                  # gold [2.5]；C0 预计 [0.0]
c = pd.array([1, None, 3], dtype="Int64") / 1
print("div data", c._data)                                        # 预计 [1. 1. 3.]
print("div", pd.Series(c).groupby([0, 0, 0]).quantile(0.5).tolist())       # gold [2.0]；C0 预计 [1.0]
```

**A-3 C1（合理替代解，可选）**。用一条分支统一处理所有掩码数组；整数仍保留 `inference = int64`，以免改变 P3。

```diff
--- a/pandas/core/groupby/groupby.py
+++ b/pandas/core/groupby/groupby.py
@@ -2439,7 +2439,11 @@ class GroupBy(BaseGroupBy[FrameOrSeries]):
                 )
 
             inference: np.dtype | None = None
-            if is_integer_dtype(vals.dtype):
+            if isinstance(vals, BaseMaskedArray):
+                out = vals.to_numpy(dtype=float, na_value=np.nan)
+                if is_integer_dtype(vals.dtype):
+                    inference = np.dtype(np.int64)
+            elif is_integer_dtype(vals.dtype):
                 if isinstance(vals, ExtensionArray):
                     out = vals.to_numpy(dtype=float, na_value=np.nan)
                 else:
```

预计 1.0。

**A-4 C2（`Float64` 结果，可选诊断）**：在 gold 的基础上改两处。
- gold 新分支里改为 `inference = vals.dtype`。
- `post_processor` 开头加：

  ```python
  if inference is not None and not isinstance(inference, np.dtype):
      return inference.construct_array_type()._from_sequence(vals, dtype=inference)
  ```

  `ExtensionArray.T` 在 `WT/pandas/core/arrays/base.py:1220` 有定义，所以返回的扩展数组可以沿原路径包装成 Series。

预计 0，只有 4 个目标键 mismatched（dtype 为 `Float64` / `Float32`，期望是 float64）。

## 附录 B：R-c 修订草案（仅在 C0 命中时执行）

- **公开依据**：
  - 题面 "correctly handling and ignoring the pd.NA value"。
  - `FloatingArray` 文档说明 mask 为 True 即缺失（`WT/pandas/core/arrays/floating.py:196-197`）。
  - 会在掩码位置留下非 NaN 的都是公开常用操作：`Series.astype("Float64")`、`reindex`、`Int64` 除法。
- **改动范围**：只针对 R5 这一个窄问题，不新增 dtype 约束，所以用 `check_dtype=False`，dtype 仍由原有键约束。
- **放置位置**：追加到 `r2e_tests/test_1.py`（`PRIV/hidden_tests/test_1.py`，放在 `test_groupby_quantile_allNA_column` 之后）。
- **期望文件**：在 `expected_output.json` 增加键 `test_groupby_quantile_NA_float_nonnan_storage`，值为 `PASSED`。它与现有键不冲突。

```python
def test_groupby_quantile_NA_float_nonnan_storage():
    # GH#42849 的一般情形：是否缺失只看掩码，与掩码位置底层存的数值无关
    # Int64 转 Float64：NA 位置底层是 1.0
    ser = pd.Series(pd.array([1, None, 3], dtype="Int64").astype("Float64"))
    result = ser.groupby([0, 0, 0]).quantile(0.5)
    tm.assert_series_equal(result, pd.Series([2.0], index=[0]), check_dtype=False)

    # reindex 引入的 NA：底层是 0.0；两组，其中一组有两个有效值
    ser = pd.Series([2.5, 3.5, 4.0], dtype="Float64").reindex([0, 1, 2, 3])
    result = ser.groupby(["a", "a", "b", "b"]).quantile(0.5)
    tm.assert_series_equal(
        result, pd.Series([3.0, 4.0], index=["a", "b"]), check_dtype=False
    )
```

**验收计划（v1 §5）**：

- 正对照 gold 为 1（238/238），行为推算：2.0；a 组 3.0，b 组 4.0。
- noop 为 0：新键因 `TypeError` 失败，原来的 4 个键也失败。
- C0 为 0：只有新键 FAILED，第一段得 1.0，第二段 b 组得 0.0。
- C1 为 1。
- 修订后仍受保护的公开要求：R1、R3、R4、R6，以及新加的 R5。
- 保存新版本、父版本、理由和触发反例 C0；Codex 复核。
- 若 `reindex` 在新机上实测掩码位置不是 0.0，第二段就测不到 C0，但第一段（由 `integer.py:228` 保证）仍然有效。也可以换成公开构造器 `pd.arrays.FloatingArray(np.array([1.0, 5.0, 3.0]), np.array([False, True, False]))`，直接给出非 NaN 的底层值。

## 附录 C：实际阅读范围

- **方法文档**：角色卡、八方面协议、R2E 环境卡、记录模板、40 项清单、统一标准 v1。
- **公开**：`PUB/` 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json`（顶层字段）；公开读者的 `public_read.md` 与 `commands.json`。
- **公开包内源码**：
  - `WT/` 下 `groupby.py` 的导入段、2380-2530、2824-3072，以及日志里引用的片段。
  - `groupby.pyx:770-886`。
  - `masked.py` 的 184-206、270-340、373-398。
  - `floating.py` 的 85-176、182-320。
  - `integer.py` 的 180-240、455-480。
  - `numeric.py` 中 `_arith_method` 的相关行。
  - `array_algos/quantile.py` 全文。
  - `ops.py` 的 300-315、370-385。
  - `generic.py` 中 `_wrap_aggregated_output`。
  - `pandas/conftest.py` 两个 fixture 所在段与导入段。
  - `_testing/__init__.py` 的 dtype 列表。
  - `test_quantile.py`（与隐藏文件做了 diff）。
  - whatsnew 中关于 quantile 与 33136 的检索结果。
- **私有**：`PRIV/` 下全部文件：`gold.patch`、`hidden_tests/*`、`expected_output.json`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`、`run_refs.json`。
- **运行证据**：
  - current 的 4 份日志全文或 grep，以及 `ledger_b3_noop.jsonl` / `ledger_b3_gold.jsonl` 中本题的行。
  - superseded 的 R-f noop / gold 日志与 M3 的 a1 日志，用 grep 查看。
  - 所有日志的 sha256 都与 `run_refs.json` 一致。
- **跨题**：两份 cross scan 中与 pandas 相关的记录；`pandas__7dd34ea7…` 的公开包（`groupby.py`、`test_quantile.py`、`user_prompt.txt` 开头）；本题公开包内对其它题测试函数名的检索。
- **未读**：所有历史调查与审查目录、修订说明与 dryrun 目录、其它题的私有包、本批 README / board / assignments。scratchpad 只建了自己的空目录，没有写入临时文件。
