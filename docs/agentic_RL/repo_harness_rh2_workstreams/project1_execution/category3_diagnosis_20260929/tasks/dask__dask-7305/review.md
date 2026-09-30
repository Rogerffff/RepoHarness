# dask__dask-7305 独立复核

2026-09-30 / 独立复核者（Claude 子代理，不继承作者上下文）。初判写于读作者材料之前（05:53 UTC 封存）：[review_initial.md](review_initial.md)，sha256 `3fadf04ce802566ae436d0a42cff99ee9beccf56306667df65fd4e306d052069`，之后未改。该文件已被负责人的快照提交 `ad9c443` 一并提交，提交内容的 sha256 与此相同；提交不是我做的。

**总判断：部分同意，阻断项 2 项。**

- **原版判定同意。** S1（T2a＋T2b，另有 T2c）、T1（带 P6 性质）、gold 不完整（G1，按统一标准 §4 第 4 步为 S1）都成立，严重度步骤用得对。作者 22 条正式账本与评分日志逐条核对，数字属实。
- **三份替代正对照都可以用（D4）。** `gold_full`、`exact_full`、`higher_full` 在我的 42 项行为检查上全部正确，`test_shuffle.py` 的 104 项 P2P 全过。它们与 base、gold 的差异只在内部分界，修订测试不检查内部分界，不影响判分。
- **v1 的依据成立，也不过严。** 我另写了 4 个“合理但与 gold、三份正对照都不同”的实现，在 v1 下全部为 1。
- **但 v1 还不能验收。** 我构造的 4 个错误候选在 v1 下得 1，不满足统一标准 §5“已知相关的错误候选仍为 0”：
  - `rv_pin_noclip`、`rv_interp_pin_noclip` 只把两端改成精确值，经 float64 舍入的内部值不夹住。遇到几个相邻的大整数（间距小于 float64 在该量级的精度），结果会越过真实最大值，或者无序；
  - `rv_maxonly_threshold` 只在 `data.max() > 2**53` 时走精确路径。全为大负数的 int64 分区仍经 float64，端点错；
  - `rv_k_le4` 只在输出分区数 ≤ 4 时走精确路径（构造性较强）。

  原因是 v1 的大整数实例值间距都很大（最小 997），int64 实例打乱后每个分区都跨 0，输出分区数都 ≤ 4。
- **修法**：在 v1 的 F2P 末尾追加 2 行实例（本页 §5）。草案 v2 在私有模拟下：三份正对照与 4 个合理实现为 1；noop、gold、`nearest_via_float` 与我的 8 个错误候选为 0。

## 1．复核范围与证据层级

- **镜像**：`c3keep/dask7305:src`，image `sha256:b4f186ca…8b99`，RepoDigest `xingyaoww/sweb.eval.x86_64.dask_s_dask-7305@sha256:21fd7dd8…0b73`，与 ingest 冻结摘要一致。环境为 Python 3.8.19、numpy 1.20.3、pandas 1.2.5，`/testbed` 干净。
- **材料**：
  - gold（`aa80a49b…d11d`）与原 test_patch（`10a206c2…ba06`）直接从 ingest bundle 取出；
  - v1 为 `revised_test_v1.patch`（`d3f78c2c…5ce0`），与作者 15 个 `formal_revised_v1/audit_*/materials.json` 里的 test_patch 逐字节相同。
- **我的运行都是私有对照**：root、`--network none`、一次性容器，不是正式评分。
  - **行为矩阵** `matrix.py`：21 组数据，每组分别检查 `partition_quantiles` 与 `set_index`，共 42 项；另看小整数的分界和可空整数。覆盖 27 个版本：base、gold、三份正对照、作者其余 10 个候选、我的 12 个候选。按公开要求判定，不以 gold 为答案，比较一律转成 Python int。
  - **私有模拟评分** `run_private.py grade`：先应用候选，再应用测试补丁，按评分包命令 `pytest -n0 -rA --color=no dask/dataframe/tests/test_shuffle.py` 运行，按 F2P（1 项）与 P2P（104 项）参考名单逐名判分。共 18 个版本，每个版本分别跑原测试、v1、草案 v2，共 54 次。另以 UID 54322（`setpriv`，补丁仍由 root 应用）重跑草案 v2 的 6 个版本（三份正对照与 3 个放过 v1 的错误候选），结果与 root 相同。
  - **更宽的回归**：`run_regression.sh`，见 §3.2。
- **没做**：
  - 正式评分（按要求不跑）；
  - 完整的 grader profile：我的容器只断网，没有 2 CPU／4 GiB 等资源限制，也不经过正式 grader。作者的正式账本已在该 profile 下跑过原材料与 v1，我只做了核对。
- **文件位置**：`rh2/experiments/category3_cloud_20260929/dask7305/review/`。
  - `make_review_candidates.py` 从 base 源码生成 12 个候选补丁（`candidates/`）；
  - `make_revised_test_v2_draft.py` 生成 `revised_test_v2_draft.patch`；
  - 运行输出在 `out/`：`grade_summary.txt`、`matrix_summary.txt`、`grade_uid_summary.txt` 是汇总，逐次日志在 `out/grade/`、`out/matrix/` 等子目录。`out/` 目前被 `rh2/experiments/category3_cloud_20260929/.gitignore` 忽略，由负责人在复核结束后归档。

## 2．作者主张逐条核对

| # | 作者主张 | 核对方式 | 结论 |
| --- | --- | --- | --- |
| 1 | 核心要求：大整数下 `partition_quantiles` 的首末值精确，不限输出分区数、输入分区数，包括 2**63 以上与有符号大整数；dtype 保持；`set_index` 每行落在自己的区间。不含内部分界与 `index.min()` 的 dtype | 与我初判 (a) 独立得出的范围比对 | 同意，两者一致 |
| 2 | T2a：没有断言检查端点；P2P `large_uint` 走快捷路径，base 也通过 | 读 `shuffle.set_index`：输出分区数等于输入分区数，且各分区的 min/max 有序、互不重叠时，直接用精确的 `mins + [maxes[-1]]` 作 divisions，分位数结果被丢弃。私有模拟：base 加原测试时 `test_set_index_interpolate_large_uint` 为 PASSED | 属实 |
| 3 | T2c：唯一的大整数断言就是 MCVE 字面值加 `npartitions=1` | 对照 test_patch | 属实 |
| 4 | T2b：退化候选 `nearest_via_float` 正式得 1，题面原例仍是 `…744／…248` | 账本：reward 1、F2P 1/1、P2P 无失败，投影含 `partitionquantiles.py`，日志 105 passed，日志 sha256 与账本一致。我的矩阵：42 项错 40 项，含题面原例（首末各 +1）。私有模拟原测试为 1 | 属实。它只凭 gold 的修改位置就能写出，符合“退化候选”。另外，我的 `rv_interp_pin_noclip`、`rv_swallow_int64`、`rv_k_le4` 在原测试下也得 1 |
| 5 | T1：`exact_full`、`higher_full` 正式得 0，唯一失败是 `{1,2,3,4} == {1,2,4}` | 账本与日志逐条核对；私有模拟复现 | 属实。误拒面比作者列的更宽：我的 `rv_exact_linear`、`rv_minmax_graph`（`{1,2,3,4}`）和 `rv_dup_branch`（`{1,3,4}`）在原测试下也都是 0 |
| 6 | P6：仓库里可见的旧测试写死 `{1,2,3,4}` | base `test_shuffle.py:614` | 属实 |
| 7 | G1：gold 在 3 个输出分区、uint64 跨 2**63 时端点偏移，`set_index` 静默丢行 | 我的探针与矩阵：gold 42 项错 20 项，全部落在两类实例上：唯一值不足（输出分区多于唯一值），以及 uint64 跨 2**63（含混入 2**64−1 的哨兵值） | 属实，有一处补充：丢行是默认 disk shuffle 下的现象，`shuffle="tasks"` 时行不丢，但会落到自己的区间之外。例如题面两个值各 3 行、2→3 分区：disk 下 6 行剩 3 行，tasks 下 3 行越界，base 与 gold 相同（`review/initial_probes/probe1.py`）。两种都是错误 |
| 8 | 第 4 步判 S1：三处都是同一核心要求的实例，不是罕见路径 | — | 同意 |
| 9 | 上游到 2024.1.0 都没修这两处 | 我另外下载了 PyPI 的 2025.9.1 wheel（sha256 `2a8a7dc9…`，`review/upstream_check.py`）：`process_val_weights` 仍是 `np.array(vals)`，唯一值不足分支仍用 `np.interp`；2021.3.0、2024.1.0 的 wheel 摘要与作者记录一致 | 属实，而且上游至今没修。三份正对照都不是上游写法，只能靠独立核实（本页 §3） |
| 10 | T3：`npartitions="auto"` 路径所有候选都丢行 | 读 `shuffle.set_index` 中那次 `np.interp`；`review/probe_auto.py` 实跑 base 与三份正对照：1000 个乱序大 uint64、4 个输入分区，都丢 1 行，divisions 首末偏 +1／−34 | 属实，同意登记 T3。它发生在 `partition_quantiles` 之后的另一段代码，三份正对照都没改它 |
| 11 | v1 正式诊断评分 15 条：noop 0、gold 0、三份正对照 1、其余 10 个 0，以及各自的失败位置 | 账本、日志、materials 的 sha256 逐条核对。私有模拟复现了 noop、gold、三份正对照与 `nearest_via_float` | 属实 |
| 12 | 逐实例核对（`semantic_v3`） | 读 15 个输出 | 与作者的表一致 |
| 13 | “只有三份正对照六项全过” | — | 只对作者的候选集成立：我的 4 个合理实现和 4 个错误候选也都六项全过（本页 §4） |
| 14 | 修订要求都能从题面推出，不需要 R-f | — | 同意；本页 §5 补的两个实例同样来自题面的一般表述 |
| 15 | 证据已归档 | `evidence_manifest.json` 共 501 条：366 个已复制，哈希全部一致；135 个未复制，都在 `formal*/artifacts/`、`prepared/`、`private/` 下 | 属实 |
| 16 | 用途：原版只作问题定位；v1 为 conditional | — | 同意。v1 还要先处理本页的 2 个阻断项 |
| 17 | v1 全部用 Python int 比较，因为 numpy 把 uint64 与 int 的比较提升到 float64，`assert_eq` 因此不可靠 | 镜像内实跑 `np.uint64(612509347682975743) < 612509347682975744`，结果为 False | 属实，这个做法必要 |

## 3．三份正对照的核实（D4）

三份都在同两处修补 `process_val_weights`：
- 整数 dtype 用 `np.array(vals, dtype=dtype)` 建数组；
- 唯一值不足分支在 `np.interp` 之后，用 Python int 钉住首末值，并把中间值夹在两端之间。

它们的区别在分区摘要：

| 正对照 | 分区摘要的做法 |
| --- | --- |
| `gold_full` | 同 gold，用 `nearest` 取样本值 |
| `exact_full` | 保留线性插值，`round` 后夹到分区的 [min, max]，再把 0 与 100 分位设成精确的 min、max（#6864 思路加夹紧） |
| `higher_full` | 用 `higher` 取样本值 |

三份的改动都只在整数 dtype 分支里，float、datetime、categorical 路径的代码没有改。

### 3.1 是否满足题面公开要求

- **行为矩阵**：三份都是 42/42。除了作者矩阵已有的情形，还覆盖以下实例：
  - 相邻大整数（间距为 1，小于该量级 float64 的间距 128）；
  - 只有 2～3 个相邻值、输出分区多于唯一值；
  - uint64 靠近 2**64、int64 靠近 2**63−1 与 −2**63；
  - 常规值中混入 2**64−1 这类哨兵值；
  - 全为大负数的 int64，以及有序、跨 0 的 int64；
  - 4→10 的上采样与 4→1 的下采样。
- **私有模拟评分**：三份在 v1 与草案 v2 下都是 1。作者的 v1 正式账本也是 1。

### 3.2 是否保留 base 的相关旧行为

- `test_shuffle.py` 的 104 项 P2P 全过，原测试、v1、草案 v2 下都如此（私有模拟；原测试与 v1 另有作者正式账本）。
- 更宽的回归：在其它用到 `set_index` 的 7 个测试文件里，按关键词选出 318 项（`test_dataframe.py`、`test_multi.py`、`test_categorical.py`、`test_merge_column_and_index.py`、`test_rolling.py`、`io/tests/test_csv.py`、`io/tests/test_io.py`，`-k 'set_index or divisions or quantile or repartition or sort' --runslow`）。三份正对照的逐项结果与 base 完全相同：317 项通过，1 项失败。失败的 `test_multi.py::test_concat_unknown_divisions` 在 base 上同样失败，原因是 pytest 8 不再接受 `pytest.warns(None)`，与本题无关。不加 `--runslow` 时 gold 也与 base 相同（`review/run_regression*.sh`，`out/regression*/`）。
- 可空整数 `UInt64`：base 与三份正对照都抛同一个 `TypeError: Cannot interpret 'UInt64Dtype()' as a data type`。base 本来就不支持，不算回归。
- 小整数的内部分界：`exact_full`、`higher_full` 与 base 相同，都是 `[1,2,3,4]`；`gold_full` 与 gold 相同，是 `[1,1,2,4]`，会让可见旧测试失败（P6）。

### 3.3 与 base／gold 的差异，是否影响判分

| 项目 | base | gold | `gold_full` | `exact_full` | `higher_full` |
| --- | --- | --- | --- | --- | --- |
| 小整数 `x=[4,1,1,3,3]` 的 divisions | `[1,2,3,4]` | `[1,1,2,4]` | `[1,1,2,4]` | `[1,2,3,4]` | `[1,2,3,4]` |
| 可见旧测试 `{1,2,3,4}` | 过 | 不过（P6） | 不过（P6） | 过 | 过 |
| 42 项行为检查 | 错 40 | 错 20 | 全对 | 全对 | 全对 |
| 取值顶端的内部分界 | — | — | 样本值 | 见下 | 样本值 |
| `npartitions="auto"` | 丢 1 行 | 丢 1 行（作者实测） | 丢 1 行 | 丢 1 行 | 丢 1 行 |

`exact_full` 在取值顶端的表现（`review/probe_top.py`，私有对照）：
- 本镜像 numpy 1.20.3 下，float64 的 2**64 转 uint64 得 0，2**63 转 int64 得 −2**63。`exact_full` 先 `astype` 再夹紧，溢出的内部值会被夹成分区最小值；
- 200 个 `2**64−200..2**64−1`、4→4 时，`exact_full` 的结果相对 2**64 为 `[-200, -200, -199, -198, -1]`，几乎所有行都进最后一个分区；`gold_full` 为 `[-200, -158, -102, -56, -1]`，分区均衡；
- 150 个常规值加 50 个靠近 2**64 的值、4→8 时，`exact_full` 把 50 个顶端值全放进最后一个分区；`gold_full` 能把它们单独分出来。

这只影响分区是否均衡，端点与顺序仍然正确（矩阵的 `top64_dense`、`top63_int64_dense`、`sentinel64` 都通过），不违反公开要求。

这些差异都落在内部分界或 T3 路径上，v1 与草案 v2 都不检查，所以不影响判分。

### 3.4 修法是否合理

- `gold_full` 是 gold 加两处最小修补，改动面最小；
- `exact_full` 与我的错误候选 `rv_pin_noclip` 的唯一差别就是“夹紧”这一步。有了它，内部值不会越过两端，这正是它正确、而 `rv_pin_noclip` 错误的原因；
- `higher_full` 是离散取值的另一种选择。

三份都不是上游写法，上游至今未修。它们在本题范围内没有找到反例。

**结论**：三份都可以作 D4 所说“经独立核实的替代正对照”。建议以 `gold_full` 为主正对照，因为它与 gold 差异最小；`exact_full`、`higher_full` 作第二、第三正对照，证明放宽后的内部分界能接受不同实现。交接时带上 §3.3 的差异清单。

## 4．反例与新问题

### 4.1 我的候选

均由 `make_review_candidates.py` 从 base 源码生成，按公开要求预先定性。

| 候选 | 做法 | 定性 |
| --- | --- | --- |
| `rv_pin_noclip` | 分区摘要仍用线性插值加 `round`，只把首末改成分区的精确 min/max，内部值不夹住；`process_val_weights` 的两处修补同 `gold_full` | 错误。即 #6864／上游 CuPy 分支式的“只钉端点”：相邻大整数时，内部值经 float64 舍入越过真实最大值 |
| `rv_interp_pin_noclip` | gold 加带 dtype 建数组；唯一值不足分支 `np.interp` 后转回整数，只改首末，不夹住中间值 | 错误：相邻大整数时结果无序、越界 |
| `rv_maxonly_threshold` | 只有 `data.max() > 2**53` 才用 `nearest`；`process_val_weights` 两处修补同上 | 错误（值域阈值）：全为大负数的分区仍经 float64 |
| `rv_swallow_int64` | gold；`np.array(vals, dtype=np.int64)`，吞掉 `OverflowError` 后改用不带 dtype 的 `np.array(vals)` | 错误（吞掉错误）：值 ≥ 2**63 时静默退回 float64 |
| `rv_si_override` | 不改分位数，只在 `shuffle.set_index` 里用逐分区的精确 min/max 改写 divisions 首末 | 错误（抑制症状）：`partition_quantiles` 本身仍错 |
| `rv_sorted_assume` | 整数按位置直接取分区中的第 k 个元素，默认分区已排序 | 错误（依赖顺序） |
| `rv_len2` | 分区不超过 2 行（题面原例的形态）时才用 `nearest` | 错误（示例拟合） |
| `rv_k_le4` | 只有输出分区数 ≤ 4 时才用 `nearest`；`process_val_weights` 两处修补同 `gold_full` | 错误（分区数阈值，构造性较强）：5 个及以上输出分区时仍经 float64 |
| `rv_lower_full` | `gold_full`，但取 `lower` | 合理 |
| `rv_exact_linear` | 保留线性插值，用 Python 整数与 2**32 定点权重精确计算；唯一值不足分支同样精确插值 | 合理；内部分界与 base 相同 |
| `rv_minmax_graph` | 摘要与合并都不动（仍是 base），在任务图里另算每个分区的精确 min/max，最后钉住首末、夹住中间值并排序 | 合理；修在 `partition_quantiles` 的出口 |
| `rv_dup_branch` | gold 加带 dtype 建数组；唯一值不足时，整数改走“重复已有值”的分支，不再插值 | 合理；小整数分界为 `[1,1,3,4]` |

派发要求的构造方向与候选的对应：
- 吞掉错误、抑制症状：`rv_swallow_int64`、`rv_si_override`；
- 只对部分规模或阈值有效：`rv_maxonly_threshold`（值域）、`rv_k_le4`（输出分区数）、`rv_pin_noclip` 与 `rv_interp_pin_noclip`（值的间距、唯一值个数）；
- 依赖顺序：`rv_sorted_assume`；
- 只覆盖 dtype 子集：`rv_swallow_int64`（只按 int64 建数组，uint64 ≥ 2**63 失效）、`rv_maxonly_threshold`（只顾正数）；
- 只处理题面示例字面值：`rv_len2`；
- 合理但与 gold、三份正对照都不同：`rv_lower_full`、`rv_exact_linear`、`rv_minmax_graph`、`rv_dup_branch`。

### 4.2 私有对照结果

矩阵列是 42 项行为检查中错了几项；后三列是私有模拟评分（不是正式评分）。

| 候选 | 定性 | 矩阵错项 | 原测试 | v1 | 草案 v2 | 草案 v2 下 F2P 第一处失败 |
| --- | --- | --- | --- | --- | --- | --- |
| base | — | 40 | 0 | 0 | 0 | `issue` 1→1 |
| gold | 不完整 | 20 | 1 | 0 | 0 | `issue` 1→3 |
| `gold_full` | 正对照 | 0 | 1 | 1 | 1 | — |
| `exact_full` | 正对照 | 0 | 0 | 1 | 1 | — |
| `higher_full` | 正对照 | 0 | 0 | 1 | 1 | — |
| `nearest_via_float`（作者） | 退化 | 40 | 1 | 0 | 0 | `issue` 1→1 |
| `rv_pin_noclip` | 错误 | 4 | 0 | **1** | 0 | 新增的相邻值簇：末值比最大值大 28 |
| `rv_interp_pin_noclip` | 错误 | 6 | **1** | **1** | 0 | 新增的相邻值簇：结果无序 |
| `rv_maxonly_threshold` | 错误 | 5 | 0 | **1** | 0 | 新增的全负 int64：首值比最小值大 2 |
| `rv_swallow_int64` | 错误 | 6 | **1** | 0 | 0 | v1 的 `span63` |
| `rv_si_override` | 错误 | 26 | 0 | 0 | 0 | `issue` 1→1 |
| `rv_sorted_assume` | 错误 | 25 | 0 | 0 | 0 | 小整数首值为 3；P2P `test_set_index` 也失败 |
| `rv_len2` | 错误 | 29 | 0 | 0 | 0 | v1 的 `uint200` |
| `rv_k_le4` | 错误 | 6 | **1** | **1** | 0 | 新增的相邻值簇（5 个输出分区）：首值比最小值大 30 |
| `rv_lower_full` | 合理 | 0 | 1 | 1 | 1 | — |
| `rv_exact_linear` | 合理 | 0 | 0 | 1 | 1 | — |
| `rv_minmax_graph` | 合理 | 0 | 0 | 1 | 1 | — |
| `rv_dup_branch` | 合理 | 0 | 0 | 1 | 1 | — |

作者的其余 9 个错误或不完整候选（`exact_ends`、`higher_int`、`gold_pin_only`、`gold_typed_only`、`uint_only`、`first_last`、`k1_only`、`clip_partition`、`pvw_only`）在矩阵中分别错 20、20、6、14、29、37、39、40、40 项；v1 正式账本都是 0。草案 v2 只在 v1 的 F2P 末尾追加断言，它们会在 v1 原来的失败处以同样方式失败，所以 v2 下也必然是 0，我没有另跑。

私有模拟与作者正式账本在重叠的 6 个版本上一致：noop／base、gold、三份正对照、`nearest_via_float`，原测试与 v1 均如此。

### 4.3 新问题

- **N1（阻断，见本页 §5 B1）**：v1 放过 `rv_pin_noclip`、`rv_interp_pin_noclip`，以及构造性较强的 `rv_k_le4`。
- **N2（阻断，见本页 §5 B2）**：v1 放过 `rv_maxonly_threshold`。
- **N3（非阻断）**：原测试下，三个错误候选 `rv_interp_pin_noclip`、`rv_swallow_int64`、`rv_k_le4` 也得 1；三个合理实现 `rv_exact_linear`、`rv_minmax_graph`、`rv_dup_branch` 得 0。这进一步支持原版 S1 与 T1，不改变处置。
- **N4（非阻断）**：base 丢行的规模可以很大。300 行、3 个相邻值（`big+99..big+101`）、3→5 分区时，base 的 `set_index` 丢掉全部 300 行：divisions 首值被舍入到 `big+129`，高于所有数据。
- **N5（非阻断）**：`npartitions="auto"` 与 `shuffle="tasks"` 两条路径，修订测试都没有单独覆盖。前者按作者意见登记 T3；后者的错放可由逐分区区间检查发现，默认 disk 下的丢行可由行数检查发现。

## 5．阻断项与非阻断建议

**阻断项（2 项；只影响修订 v1 的验收，不影响“原版 S1、只作问题定位”的结论）**

1. **B1：相邻的大整数。** v1 放过 `rv_pin_noclip`、`rv_interp_pin_noclip`（以及构造性较强的 `rv_k_le4`）。
   - **违反的公开要求**：题面“correct minimum and maximum”对任何大整数输入都成立，而这两个候选让最大值出错或结果无序；divisions 必须有序，`set_index` 的每行应在自己的区间。
   - **实测后果**：数据为 300 行、3 个相邻值 `big+99..big+101`、3→5 分区时：
     - `rv_pin_noclip` 的末值为 `…975872`，比真实最大值 `…975844` 大 28；
     - `rv_interp_pin_noclip` 的结果无序，`set_index` 的 divisions 也无序，行落在区间外。

     这样的数据是现实中常见的形态：少数几个相邻 ID 反复出现。
   - **v1 为什么放过**：v1 的大整数实例相邻值间距都 ≥ 997，float64 的舍入误差（该量级约 ±64）碰不到端点；输出分区数也都 ≤ 4，所以只在 ≤ 4 个分区时走精确路径的 `rv_k_le4` 也能通过。
   - **修法**：在 F2P 末尾追加：

     ```python
         _assert_exact_int_divisions([big + 99 + j % 3 for j in range(300)], "uint64", 3, 5)
     ```

     这 3 个值经 float64 都会舍入成 `big+129`，高于真实最大值，所以只要内部值不夹住就一定失败，与随机分位点无关。这一行同时覆盖唯一值不足分支和 5 个输出分区。
   - **修后预期**（已私有验证）：`rv_pin_noclip`、`rv_interp_pin_noclip`、`rv_k_le4` 为 0，都失败在这一行；三份正对照与 4 个合理实现为 1。
2. **B2：全为负的大 int64。** v1 放过 `rv_maxonly_threshold`。
   - **违反的公开要求**：题面写的是“large integer inputs”，作者也把有符号大整数列为核心要求。
   - **实测后果**：全为大负数时，首末值分别偏 +2 与 −1，`set_index` 丢 1 行；数据有序、跨 0 时第一个分区全为负，首值偏 −1。
   - **v1 为什么放过**：v1 的 int64 实例打乱后，每个分区都同时含正负值，分区最大值都超过 2**53。
   - **修法**：追加：

     ```python
         _assert_exact_int_divisions([-big - 997 * k for k in order], "int64", 4, 4)
     ```

   - **修后预期**（已私有验证）：该候选为 0，失败在这一行（`-612509347683174144 == -612509347683174146`）；其余同 B1。

两行合并为草案 v2：`review/revised_test_v2_draft.patch`，sha256 `6e96caa74e7ae6db75a13b30200b3736de7321fe3ad9a6f73a5d80664f213924`。它只在 v1 的 F2P 末尾追加两行调用（外加两行注释），测试 ID、分组和评分命令都不变。

草案 v2 只是私有对照中的草稿，没有经过正式评分。采纳后请作者：
- 重新生成补丁与 materials；
- 按统一标准 §5 跑正式诊断评分，范围为 noop、gold、三份正对照、作者全部错误候选、我的 8 个错误候选与 4 个合理实现；
- 父版本 v1 与触发反例一并留档。

**非阻断建议**

1. result.md 的两处措辞：
   - “本镜像的 base 上，`set_index` … 直接丢掉该行”后补一句：这是默认 disk shuffle 下的现象，`shuffle="tasks"` 时行不丢，但落在区间之外；
   - “只有三份正对照六项全过”改为“作者候选中只有三份正对照六项全过”。
2. 交接第2类时带上 §3.3 的正对照差异清单，并把我的 12 个候选（尤其放过 v1 的 4 个）加入已知错误候选与合理候选集。
3. 可选：再加一个取值顶端的实例，例如在常规 uint64 值里混入几个 2**64−1，用来防止将来出现“float 转回整数时溢出”一类候选。目前没有已知候选需要它，`sentinel64` 一例三份正对照都能通过。
4. T3 登记保留 `npartitions="auto"`，并注明 `shuffle="tasks"` 没有单独的实例。

## 6．未查

- 正式评分：未跑，按要求如此。本页数字除作者账本外都是私有模拟；
- 完整 grader profile（2 CPU／4 GiB 等）下的草案 v2 运行：只以 UID 54322 跑了 6 个版本，没有加资源限制；
- 真实 actor 的开发条件与模型求解；
- `npartitions="auto"` 路径的修法（只复跑了丢行现象）；
- 其它平台与 numpy 版本：本镜像 numpy 1.20.3 下，float 转 uint64 溢出得 0；其它版本、其它平台（例如 longdouble 精度不同）未查；
- 性能：`gold_full` 等在唯一值不足分支里有 Python 级循环（长度为输出分区数加 1），大规模下的耗时未测；
- 作者矩阵 `behavior.py` 的逐文件输出（`semantic_v1/v2`）：只读了 `semantic_v3` 的逐实例结果与 result.md 的汇总。
