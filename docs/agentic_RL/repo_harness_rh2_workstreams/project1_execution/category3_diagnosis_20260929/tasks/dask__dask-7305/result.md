# dask__dask-7305：第3类诊断结果

2026-09-29 / Claude（云端，第3类第二批主审子代理）。原分类：第3类“已有具体疑点，缺辨别实验”。登记的下一步是：直接核对大整数 `partition_quantiles` 的端点、dtype 和不同分区数。

> **当前状态（09-30 更新：已按 Codex 复核转第2类，采用 v2；v2 正式诊断评分进行中）**
>
> - **独立复核已完成**，结论“部分同意，阻断 2 项”，全文见 [review.md](review.md)（初判封存稿 [review_initial.md](review_initial.md)）：
>   - 同意原版 S1（T2a＋T2b，另有 T2c）、T1（带 P6 性质）、gold 不完整（G1 → S1）；作者 22 条正式账本逐条核对属实；
>   - **三份替代正对照 `gold_full`、`exact_full`、`higher_full` 都可以用**（D4 的他人核实已满足，review.md §3），核实范围是公开要求的 numpy 大整数，扩展 dtype 与 `npartitions="auto"` 路径不在范围内；
>   - v1 依据成立、不过严（复核者 4 个合理实现在 v1 下都为 1），但 **v1 放过复核者的 4 个错误候选**：`rv_pin_noclip`、`rv_interp_pin_noclip`（相邻大整数时越界或无序，B1）、`rv_maxonly_threshold`（全为负的大 int64，B2），以及构造性较强的 `rv_k_le4`；
>   - 修法：在 F2P 末尾追加两行实例，即草案 v2。
> - **v2 已采用**：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask7305/revised_test_v2.patch) 与复核者的草案逐字节相同（`6e96caa7…3924`）。v1 不能当作充分验收。
> - 复核者 12 个候选的原材料正式评分已补跑（09-30），与复核者的私有模拟逐项一致（§2（2））。
> - **进行中**：v2 正式诊断评分（noop、gold、三份正对照、作者全部错误候选、复核者 12 个候选）。按 Codex 建议，v2 的聚焦复核由第2类承接。

**结论：问题和修法已明确，转第2类（采用 v2；正对照 `gold_full`，`exact_full`、`higher_full` 为第二、第三正对照，均已由独立复核核实）。**

- **原测试没有检查核心要求（S1：T2a＋T2b）**：参考名单里没有一条断言检查 `partition_quantiles` 的端点。唯一涉及大整数的 P2P 走单分区 min/max 快捷路径，在 base 上就能通过。退化候选 `nearest_via_float` 在题面原例上仍返回 `…744／…248`，正式评分却得 1。
- **原 F2P 误拒合理解（T1，带 P6 性质）**：唯一 F2P 把近似的内部分界锁成 `{1,2,4}`，和仓库里可见的旧测试 `{1,2,3,4}` 相反。两个完整、正确的替代实现 `exact_full`、`higher_full` 正式评分都得 0，失败只在这一行。
- **gold 不完整（G1 → §4 第 4 步，S1）**：gold 修好了题面原例，也修好了“大量不同大整数”的情形。下面两种情况仍错：
  - 同一组题面数据请求 3 个输出分区时，唯一值不足分支还在用 `np.interp`；
  - uint64 值跨越 2**63 时，`process_val_weights` 用不带 dtype 的 `np.array(vals)` 转成了 float64。

  这两种情况下端点都偏移，`set_index` 还会静默丢行，例如 3 个不同值、300 行、5 个输出分区时丢掉 100 行。
- **修法**：R-b 放宽内部分界；R-c 补 5 个大整数实例，同时检查端点和行的归属。修订版 v1 正式诊断评分（15 个变体）：noop 0；gold 0；`gold_full`、`exact_full`、`higher_full` 为 1；其余 10 个错误或不完整候选全为 0。
- gold 在修订版上为 0，因此按 D4 改用替代正对照 `gold_full`（gold 加两处最小修补），`exact_full`、`higher_full` 作第二、第三正对照。三者由本主审编写，**已由独立复核核实**（review.md §3）。
- 实施依赖 D6 的“测试补丁替换”切片。测试 ID 与 F2P／P2P 分组不变，不需要 `statement_replace`。

## 1．公开要求

题面标题：“`partition_quantiles` finds incorrect minimum with large unsigned integers”。

- **What happened**：对大整数输入（“large integer inputs”），`partition_quantiles` 求出的最小值和最大值不对；
- **Expected**：“For `partition_quantiles` to find correct minimum and maximum”；
- **MCVE**：两个 uint64 值 `612509347682975743`、`616762138058293247`，单分区，`npartitions=1`，结果为 `…744`、`…248`，dtype `uint64`；
- **附带症状**：对未排序的 uint64 列 `set_index` 时，最小值落进了最后一个分区，因为 `divisions[0]` 比真实最小值大 1。

按题面的一般表述，本页把核心要求定为：**大整数输入下，`partition_quantiles` 返回精确的最小值与最大值**。它不限于 `npartitions=1`，不限于单分区输入，也不限于 2**63 以下的值；有符号大整数也在内。返回的 dtype 保持输入 dtype，这是 MCVE 已展示的现有行为。`set_index` 应把每行放进自己的 divisions 区间。

以下事项不属于核心要求，只登记：
- 题面 Edit 里 `index.min().compute()` 的 dtype 从 uint64 变成 int64：base 与 gold 都是 int64，隐藏测试不涉及；
- “buffer overflow”：是报告者的猜测，不是根因。

公开代码中可见的相关事实（base `8663c6b7`）：
- `partitionquantiles.py` 模块说明写明算法是近似的，内部分界“good enough”即可，但需要准确的全局 min/max；
- `process_val_weights` 在唯一值不足时仍用 `np.interp`；
- `dask/array/percentile.py::_percentile` 对 datetime 已有同类补丁：`result[0] = min(result[0], a.min())`（#6864）；
- 仓库里可见的旧测试 `test_set_index_interpolate` 断言 `set(d1.divisions) == {1, 2, 3, 4}`。

## 2．实测

### 环境与材料

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.dask_s_dask-7305:latest`，经 mirror.gcr.io 按原名拉取。RepoDigests 为 `sha256:21fd7dd8…0b73`，与 ingest 冻结摘要一致；本机 image ID `sha256:b4f186ca…8b99`，已打标签 `c3keep/dask7305:src` |
| 派生配方 | 无（09-19 修复目录中没有本题，按原镜像直接评分） |
| 运行时 | Python 3.8.19、numpy 1.20.3、pandas 1.2.5；Docker 29.3.1、overlay2、cgroup v1 |
| 材料 | 题面 SHA256 `0c2588f7…ff9d`（与 bundle 一致）；gold `aa80a49b…d11d`；原 test_patch `10a206c2…a06`；F2P 1 项、P2P 104 项；评分命令 `pytest -n0 -rA --color=no dask/dataframe/tests/test_shuffle.py` |
| 代码 | 分支 `claude/category3-20260929`，HEAD `742702e`；评分路径与 `a31cdcd` 逐字相同（`git diff` 为空） |

### 候选（全部位于 `rh2/experiments/category3_cloud_20260929/dask7305/candidates/`，由 `make_candidates.py` 从 base 源码生成）

| 候选 | sha256 前缀 | 做法 | 按公开要求判断 |
| --- | --- | --- | --- |
| gold | `aa80a49b` | 整数改用 `nearest` | 不完整：唯一值不足与跨 2**63 时仍错 |
| `gold_full` | `9b4f7bb3` | gold；`process_val_weights` 对整数 dtype 用 `np.array(vals, dtype=dtype)`；唯一值不足分支在 `np.interp` 后钉住两端，中间值夹在两端之间 | 正确（替代正对照，**已由独立复核核实**，review.md §3） |
| `exact_full` | `17a2cd20` | 保留线性插值的内部分界，摘要两端改为精确的 `data.min()/max()`，与 #6864 同一思路；`process_val_weights` 的两处修补同 `gold_full` | 正确（第二正对照，已由独立复核核实） |
| `higher_full` | `ae7e5227` | 整数改用 `higher`，同样是离散取值；`process_val_weights` 的两处修补同上 | 正确（第三正对照，已由独立复核核实） |
| `exact_ends` | `6ebbacee` | 只做 `exact_full` 的摘要部分 | 与 gold 同样不完整 |
| `higher_int` | `cda2b1d9` | 只做 `higher_full` 的摘要部分 | 与 gold 同样不完整 |
| `gold_pin_only` | `b0456f64` | gold＋钉住两端 | 跨 2**63 仍错 |
| `gold_typed_only` | `265665b1` | gold＋带 dtype 的数组 | 唯一值不足时仍错 |
| `nearest_via_float` | `873e589b` | 改用 `nearest`，但在 float64 上取值（只对 2**53 以下有效） | 退化：题面原例仍 +1 |
| `uint_only` | `cc90b805` | 只对 uint64 改用 `nearest`（只覆盖类型子集） | 有符号大整数仍错 |
| `first_last` | `7192e57f` | 端点取每个分区的首尾元素，默认数据已排序（依赖顺序） | 乱序数据错 |
| `k1_only` | `3fc2e898` | 只在 `npartitions=1` 时改用 `nearest`，即题面调用的字面值 | 其它分区数仍错 |
| `clip_partition` | `c978da08` | 在 `shuffle.set_partitions_pre` 把低于 `divisions[0]` 的行塞进第 0 分区（抑制症状） | 分位数端点仍错 |
| `pvw_only` | `ade5e750` | 只做 `process_val_weights` 的两处修补 | 摘要阶段仍 +1 |

“吞掉错误”一类在本题不适用：缺陷是静默的精度损失，没有异常可吞。最接近的构造是抑制症状，即 `clip_partition`。

### （1）私有行为对照

在断网、root 的一次性容器中运行 `behavior.py`（`semantic_control.py`），按公开要求判断，不以 gold 为答案。

记法：
- ok 表示端点精确、有序、在 [min, max] 内、dtype 保持；`set_index` 用例还要求每行在自己的区间内，且内容与 pandas 一致；
- 括号里是两端偏差（首端－最小值／末端－最大值）；
- “丢”表示 `set_index` 结果少了行。

| 用例 | base | gold | `gold_full`／`exact_full` | `exact_ends` | `higher_int` |
| --- | --- | --- | --- | --- | --- |
| 题面原例 k=1 | +1/+1 | ok | ok | ok | ok |
| 同一数据 k=2／3／5 | +1/+1 | +1/+1 | ok | k=2 ok，k=3、5 为 +1 | +1/+1 |
| 1000 个乱序大 uint64、4 分区、最小值在末尾，k=1／4／10 | +1/−34 | ok | ok | ok | ok |
| 1000 个大 int64（跨 0），k=1／4 | −1/−25 | ok | ok | ok | ok |
| 1000 个 uint64 跨 2**63，k=1／4 | +1/+985 | +1/+985 | ok | +1/+985 | +1/+985 |
| 两值都在 2**63 以上，k=1／k=3 | +1/+1 | ok／+1 | ok | ok／+1 | ok／+1 |
| 两值 `[…743, 18446744073709551557]`，k=1 | 首端 0 | 末端 0（结果无序） | ok | 末端 0 | 末端 0 |
| 300 行、3 个不同值，k=5 | +1/+1 | +1/+1 | ok | ok | +1/+1 |
| `set_index`：题面数据 1→3 分区 | 丢 1/2 行 | 丢 1/2 行 | ok | 丢 | 丢 |
| `set_index`：1000 个乱序大 uint64，4→4 | 丢 1 行 | ok | ok | ok | ok |
| `set_index`：跨 2**63，4→4 | 丢 1 行 | 丢 1 行 | ok | 丢 | 丢 |
| `set_index`：3 个不同值 300 行，3→5 | 丢 100 行 | 丢 100 行 | ok | ok | 丢 100 行 |
| 小整数 `x=[4,1,1,3,3]` 的 divisions | `[1,2,3,4]` | `[1,1,2,4]` | `{1,2,4}`／`{1,2,3,4}` | `{1,2,3,4}` | `{1,2,3,4}` |
| `set_index(npartitions="auto")`，1000 个大 uint64 | 丢 1 行 | 丢 1 行 | 丢 1 行 | 丢 1 行 | 丢 1 行 |

说明：
- 本镜像的 base 上，`set_index` 不是把最小值放进最后一个分区（题面现象），而是直接丢掉该行：`set_partitions_pre` 对小于 `divisions[0]` 的值给出分区号 −1。这是默认 disk shuffle 下的现象；`shuffle="tasks"` 时行不丢，但会落到自己的区间之外（独立复核 `review/initial_probes/probe1.py`：题面两个值各 3 行、2→3 分区，disk 下 6 行剩 3 行，tasks 下 3 行越界，base 与 gold 相同）。两种都是错误。
- gold 的 `nearest` 让摘要中的不同值变少，“3 个不同值”这类数据反而必定走唯一值不足分支。base 与 `exact_ends` 的线性插值会产生额外的中间值，因此 `exact_ends` 在这一例上正确，gold 不正确。
- `npartitions="auto"` 路径另在 `shuffle.set_index` 中对 divisions 做 `np.interp`，所有候选都丢 1 行（`clip_partition` 例外，它把行塞回第 0 分区）。
- dask 自带的 `assert_eq`／`assert_divisions` 对大 uint64 不可靠：它用 numpy 比较 uint64 索引与 Python int 的 division，会提升到 float64。实例：`exact_full` 在“3 个不同值”一例中，分区 0 的最大值 `…743` 按整数确实小于下一个 division `…744`，numpy 比较却给出 False，`assert_eq` 因此报错，而逐分区的 Python int 核对通过。所以上表与修订测试都以 Python int 判定。
- 仓库里可见的 `test_shuffle.py`（base 版）下，gold、`gold_full`、`nearest_via_float`、`gold_pin_only`、`gold_typed_only` 都在旧的 `test_set_index_interpolate` 上失败（`{1,2,4}` ≠ `{1,2,3,4}`），其余 103 项通过；`exact_full`、`higher_full`、`exact_ends`、`higher_int` 等 104 项全过；`first_last` 另外弄坏了 `test_set_index`、`test_empty_partitions`。

上游对照（只作佐证，不作公开依据；PyPI wheel：2021.3.0 `9943b582…`、2024.1.0 `717102ef…`，只读了源码，未运行）：
- 上游保留了 gold 的 `nearest`；
- 直到 2024.1.0，`process_val_weights` 仍是不带 dtype 的 `np.array(vals)`，唯一值不足分支仍用 `np.interp`；gold 残留的两处问题在上游一直没有改；
- 上游对 CuPy 走“线性＋round＋`vals[0] = data.min()`”，也就是精确端点思路（只修了最小值）。

### （2）原材料正式评分

`replay_grade.py run`，grader `swebench-4.1.0+swegym_parsers@242429c1`，无派生镜像。所有行的参考缺席都是 0，安装 rc 0，清理成功。

| 候选 | reward | F2P | P2P 失败 | 说明 |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/1 | 0/104 | 与历史一致 |
| gold | 1 | 1/1 | 0/104 | 与历史一致 |
| `nearest_via_float` | **1** | 1/1 | 0/104 | 题面原例仍错，却得满分；投影包含 `partitionquantiles.py`，105 passed |
| `gold_full` | 1 | 1/1 | 0/104 | |
| `exact_full` | **0** | 0/1 | 0/104 | 唯一失败：`assert {1, 2, 3, 4} == {1, 2, 4}` |
| `higher_full` | **0** | 0/1 | 0/104 | 同上 |
| `exact_ends` | 0 | 0/1 | 0/104 | 同上 |

其余作者候选只做了私有模拟：在容器里应用原 test_patch，运行 `-k interpolate` 的 3 项。
- `gold_pin_only`、`gold_typed_only` 3/3 通过；
- `higher_int`、`uint_only`、`first_last`、`k1_only`、`clip_partition`、`pvw_only` 都败在 F2P 的 `{1,2,4}` 断言上。

**独立复核者的 12 个候选（09-30 补跑原材料正式评分）**：结果与复核者的私有模拟逐项一致（review.md §4.2 “原测试”一列）。参考缺席 0，安装 rc 0，清理成功。

| 候选 | 复核定性 | reward | 说明 |
| --- | --- | --- | --- |
| `rv_lower_full` | 合理 | 1 | 内部分界与 gold 相同 |
| `rv_exact_linear`、`rv_minmax_graph` | 合理 | **0** | 内部分界 `{1,2,3,4}`，误拒（T1） |
| `rv_dup_branch` | 合理 | **0** | 内部分界 `{1,3,4}`，误拒（T1） |
| `rv_interp_pin_noclip`、`rv_swallow_int64`、`rv_k_le4` | 错误 | **1** | 原测试放过（S1） |
| `rv_pin_noclip`、`rv_maxonly_threshold`、`rv_si_override`、`rv_len2` | 错误 | 0 | 败在 `{1,2,4}` 断言 |
| `rv_sorted_assume` | 错误 | 0 | 另有 P2P `test_set_index` 失败（103/104） |

## 3．判定（v1 §3–§4）

| 步 | 结果 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | **无 → S1（T2a）** | F2P 只查小整数的内部分界；P2P `large_uint` 用 1 个输入分区、1 个输出分区，`shuffle.set_index` 的快捷路径用 `mins + [maxes[-1]]` 覆盖分位数结果，base 也通过。没有任何断言调用 `partition_quantiles` 或检查端点 |
| 2 是否只用题面示例的字面值 | 是（T2c） | 唯一的大整数断言就是 MCVE 的两个值加 `npartitions=1`，而且走的是快捷路径 |
| 3 退化探测 | **`nearest_via_float` 正式得 1 → S1（T2b）** | 违反的公开要求：题面原例本身，端点仍为 `…744／…248` |
| 4 已有得 1 的候选是否在同一核心要求的其它实例上违例 | **是 → S1（G1）** | gold 在同一组题面数据 `npartitions=3` 时端点 +1；uint64 跨 2**63 时端点偏移，甚至出现无序结果；`set_index` 静默丢行。三处都是“大整数下 min/max 正确”这一要求的实例，不是罕见路径：唯一值不足是模块文档明写要处理的分支，2**63 以上正是 uint64 区别于 int64 的取值范围 |
| T1 | **误拒** | 替代实现 `exact_full`、`higher_full` 完整且正确，正式评分得 0，只因内部分界是 `{1,2,3,4}`。模块说明允许近似的内部分界，题面对内部分界没有要求，仓库里可见的旧测试恰好要求 `{1,2,3,4}` |
| P6 | 登记 | 可见的旧 `test_set_index_interpolate` 写死 `{1,2,3,4}`，按 gold 思路修复的解题者会看到它失败。探针分析时，这一失败不算改错 |
| T3 | 登记 | `set_index(npartitions="auto")` 在 `shuffle.py` 里再做一次 `np.interp`，所有候选都丢行。题面用的是默认 `npartitions`，该路径不属于核心要求；`index.min()` 的 dtype 另见 §1 |

P5 不适用：没有“两种读法”，内部分界本就允许不同。

## 4．修法（交第2类）

### R-b＋R-c：修订版测试草案 v1

草案文件：[`revised_test_v1.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask7305/revised_test_v1.patch)，sha256 `d3f78c2c…5ce0`。材料 JSON 为 [`materials_revised_v1.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask7305/materials_revised_v1.json)，grader 后缀 `+c3-dask7305-exact-ends-v1`。由 `make_revised_test.py` 从 base 测试文件生成。

草案只改 F2P `test_set_index_interpolate` 的函数体，并新增一个模块级 helper `_assert_exact_int_divisions`。P2P `test_set_index_interpolate_large_uint` 与原补丁逐字相同。测试 ID、分组和评分命令都不变。

- **R-b**：小整数一段删除 `set(d1.divisions) == {1, 2, 4}`，改为以下行为断言：
  - `npartitions == 3`；
  - 首尾分别为 1 和 4；
  - divisions 有序且都是整数；
  - `assert_eq(d1, df.set_index("x"))`，即内容一致、每行落在自己的区间。

  浮点 y 一段不变。
- **R-c**：helper 对每个实例依次检查：
  1. `partition_quantiles` 的结果 dtype 等于输入 dtype，首尾等于精确的 min/max，结果有序；
  2. `set_index` 的 divisions 首尾精确；
  3. 逐分区检查每行都在自己的区间内；
  4. 所有索引值与输入一致，即不丢行。

  全部用 Python int 比较：numpy 把 uint64 与 int 的比较提升到 float64，会掩盖差 1 的错误，`assert_divisions` 就受这个影响。

  五个实例（数据都是确定的，两端都无法用 float64 精确表示）：
  - `issue_1to1`：MCVE 本身；
  - `issue_1to3`：同一数据，3 个输出分区；
  - `uint_200_4to4`：200 个乱序大 uint64，最小值在最后一个输入分区；
  - `int64_200_4to4`：200 个跨 0 的大 int64；
  - `span63_200_4to4`：200 个跨 2**63 的 uint64。

逐实例的私有核对（`rev_instances.py`，每个实例单独执行，不因前一处失败而停）：

| 实例 | 单独拦住的错误候选 |
| --- | --- |
| 小整数（放宽后） | 无；全部 15 个变体通过，包括 `first_last` 的 `{1,3,4}` |
| `issue_1to1` | base、`nearest_via_float`、`clip_partition`、`pvw_only` |
| `issue_1to3` | gold、`exact_ends`、`higher_int`、`gold_typed_only`、`uint_only`、`first_last`、`k1_only` |
| `uint_200_4to4` | `first_last`、`k1_only` |
| `int64_200_4to4` | `uint_only`、`first_last`、`k1_only` |
| `span63_200_4to4` | gold、`exact_ends`、`higher_int`、`gold_pin_only`、`uint_only`、`first_last`、`k1_only` |

每个大整数实例都至少单独拦住一个错误候选：`gold_typed_only` 只靠 `issue_1to3`，`gold_pin_only` 只靠 `span63`。作者候选中只有 `gold_full`、`exact_full`、`higher_full` 六项全过；独立复核另写的 4 个合理实现与 4 个错误候选也六项全过，后者由 v2 追加的两行拦下（见 v2 小节）。

修订版正式诊断评分（`--materials`，F2P／P2P 名单与命令不变）：

所有行：grader `swebench-4.1.0+swegym_parsers@242429c1+c3-dask7305-exact-ends-v1`，参考缺席 0，安装 rc 0，清理成功。修订后的 grading 摘要为 `sha256:7609d1e0…c798`（原为 `b94a8bce…8eb2`）。

| 候选 | 原材料 | 修订版 v1 | 修订版失败位置（F2P 中第一处失败的实例） |
| --- | --- | --- | --- |
| noop | 0 | 0 | `issue_1to1` |
| gold | 1 | **0** | `issue_1to3`（G1） |
| `gold_full`（正对照） | 1 | **1** | — |
| `exact_full` | **0** | **1** | —（T1 已纠正） |
| `higher_full` | **0** | **1** | —（T1 已纠正） |
| `nearest_via_float`（退化） | **1** | **0** | `issue_1to1`（T2b 已纠正） |
| `exact_ends` | 0 | 0 | `issue_1to3` |
| `higher_int` | 私有 0 | 0 | `issue_1to3` |
| `gold_pin_only` | 私有 1 | 0 | `span63_200_4to4` |
| `gold_typed_only` | 私有 1 | 0 | `issue_1to3` |
| `uint_only` | 私有 0 | 0 | `issue_1to3` |
| `first_last` | 私有 0 | 0 | `issue_1to3`；另有 2 项 P2P 失败（`test_set_index`、`test_empty_partitions`） |
| `k1_only` | 私有 0 | 0 | `issue_1to3` |
| `clip_partition` | 私有 0 | 0 | `issue_1to1` |
| `pvw_only` | 私有 0 | 0 | `issue_1to1` |

“私有”指该候选在原材料上只做了私有模拟（应用原 test_patch 后跑 `-k interpolate` 的 3 项），未做正式评分。修订版一列全部是正式诊断评分。

修订后仍受保护的公开要求：
- 大整数的精确 min/max，覆盖不同输出分区数、多分区乱序输入、有符号、跨 2**63 的情形；
- 结果 dtype；
- `set_index` 行的归属与不丢行；
- 小整数的首尾值、有序、整数类型、内容一致；
- 浮点插值的原有三条断言；
- `interpolate_int`、`large_uint` 以及其余 102 项 P2P。

### 正对照（D4）

gold 通不过有依据的新断言（`issue_1to3`、`span63`），因此不能作正对照；本页不为保住 gold 而删去这两例。

改用 `gold_full` 作替代正对照，它只在 gold 之外补两处：
- 整数 dtype 下 `np.array(vals, dtype=dtype)`；
- 唯一值不足分支钉住两端。

`exact_full`、`higher_full` 作第二、第三正对照，证明放宽后的内部分界同时接受 `{1,2,4}` 与 `{1,2,3,4}`。三者都由本主审编写，**须由他人独立核实**：按公开要求核对补丁，并复跑私有矩阵。

### R-f

不需要。修订测试的每项要求都能从题面的一般表述、MCVE 的输出和 divisions 的公开语义推出，不引入隐藏细节。

### 交接给第2类

1. D6 “测试补丁替换”切片落地本草案。测试 ID 与分组不变，不需要改参考名单或 `statement_replace`。
2. 独立核实 `gold_full`（及 `exact_full`、`higher_full`）确实满足公开要求，再作正对照。
3. 复验：修订版下 noop 0、`gold_full` 1；gold 与另外 10 个错误或不完整候选为 0。
4. Codex 复核。

## 5．当前用途（v1 §2，D6 落地前）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | 否（误拒未消解：完整正确解得 0；退化解得 1。按 v1 §11 不进比较分母） | 否 | 否 |
| 修订版 v1（草案） | 是 | conditional：D6 落地并复验、正对照经独立核实 | conditional：同左，另加 Codex 复核 | 否（修订题只能作标明版本的自建题） |

## 6．未做与剩余事项

- 独立复核：尚未进行。
- 替代正对照的独立核实：尚未进行。
- 真实 actor 开发条件：未验，没有模型求解证据。
- `npartitions="auto"` 路径（T3）：只登记，未设计修订。
- 上游 2024.1.0 在新 numpy 下的实际行为：未运行，只读了源码。
- 旧题卡所说“公开读者的最小命令”（直接调用 `partition_quantiles`）：已在私有矩阵里以 root 身份执行，未在 actor 身份下执行。

## 7．版本与证据

- 实验文件：`rh2/experiments/category3_cloud_20260929/dask7305/`，包括：
  - `make_candidates.py`、`candidates/*.patch`；
  - `behavior.py`、`rev_instances.py`；
  - `semantic_spec*.json`；
  - `make_revised_test.py`、`revised_test_v1.patch`、`materials_revised_v1.json`；
  - `run_formal.sh`、`summarize_*.py`。
- 原始证据：[evidence/](evidence/)，其中：
  - `formal/`：原材料评分；
  - `formal_revised_v1/`：修订版诊断评分；
  - `semantic_v1/`：私有矩阵与原隐藏测试；
  - `semantic_v2/`：加修订隐藏测试；
  - `semantic_v3/`：逐实例核对；
  - 全部文件的 SHA256 见 `evidence_manifest.json`。
- 环境：见[环境说明](../../environment.md)。
