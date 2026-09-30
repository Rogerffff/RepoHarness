# dask__dask-7305 独立复核：初判（读作者材料前封存）

2026-09-30，独立复核者（Claude 子代理，不继承作者上下文）。写完不再修改。

## 本稿读过什么

- 统一标准 v1 §2–§5、§7、§9；本目录 README（两节校准）、environment.md、batch2_author_brief.md；参考写法 conan-13403、pydantic-8567 的 review。
- `s2/ingest/` 三个 bundle 中本题的题面、public_hints、gold（sha256 `aa80a49b…d11d`）、test_patch（`10a206c2…ba06`）、F2P（1 个）与 P2P（104 个，全部在 `dask/dataframe/tests/test_shuffle.py`）、`eval_cmd`（`pytest -n0 -rA --color=no`）。
- 镜像 `c3keep/dask7305:src`（image `b4f186ca…`，RepoDigest `…dask_s_dask-7305@sha256:21fd7dd8…0b73`，与 ingest 冻结值一致）中的 base 源码：`dask/dataframe/partitionquantiles.py`、`dask/array/percentile.py::_percentile`、`dask/dataframe/shuffle.py` 的 `set_index`、`set_partition`、`set_partitions_pre`。环境：Python 3.8.19、numpy 1.20.3、pandas 1.2.5，`/testbed` 干净。
- 两个小探针（一次性容器、`--network none`、root，属私有对照）：base 与 gold 上的 `partition_quantiles` 端点与 `set_index` 行守恒。

**如实说明**：派发说明里已经转述了作者的主要主张（S1＝T2a＋T2b，退化候选 `nearest_via_float` 得 1；T1＝F2P 锁 `{1,2,4}`，`exact_full`、`higher_full` 得 0；gold 的三处不完整；修订 v1 为 R-b＋R-c）。作者的 `result.md`、`evidence/`、实验目录我都没有打开。下面的判断以原件、源码与我自己的探针为依据。

## 根因（源码直接可见）

`percentiles_summary` 对非分类数据用 `interpolation="linear"` 调 `np.percentile`，整数先得到 float64 再 `np.round(...).astype(data.dtype)`。float64 只有 53 位尾数，大于 2**53 的整数在这一步被舍入，所以每个分区摘要的 0 与 100 分位就已经不是真实最小、最大值。uint64 靠近 2**64 时，float 转回 uint64 还会溢出。

## (a) 题面核心要求

标题与“期望行为”：`partition_quantiles` 对大整数输入要给出**正确的最小值和最大值**。按一般表述理解：

- 结果首项等于真实最小值、末项等于真实最大值，值精确、dtype 保持（题面输出就是 uint64）；
- 对“大整数”一般成立：超过 float64 精度（> 2**53）的 uint64，包括 int64 放不下的 ≥ 2**63 的 uint64（这正是“large unsigned integers”最典型的情形）；题面正文写的是“large integer inputs”，int64 大值（含负数）也在范围内；
- 不限于示例的形态：任意输入分区数、任意输出分区数（包括输出分区数多于唯一值个数）、最小值在数据末尾（题面明确说“minimum value is towards the end”）。

与核心要求直接相连的公开后果：`set_index` 的 divisions 由它得出。divisions[0] 大于真实最小值时，行会被放错分区；我在 base 上实测 disk shuffle 下还会**静默丢行**（200 行只剩 199 行）。题面“Anything else”描述的正是这一症状，属于有依据、常用的公开行为。

题面没有要求：
- 内部分界（非端点的分位值）取什么值。模块 docstring 写明是 approximate、“no statistical guarantees”；
- 用哪种插值方式；
- 题面“Edit”里 `df.index.min().compute().dtype` 变成 int64 的旁注。它不在标题与期望行为里，属于另一个函数（归约）。

## (b) 原测试可能有什么问题

1. **F2P 锁了内部分界（T1）。** 唯一的 F2P `test_set_index_interpolate` 把 `set(d1.divisions) == {1,2,3,4}` 改成 `{1,2,4}`。数据 `x=[4,1,1,3,3]`、3 个输出分区，两种结果的端点都是 1 和 4，都正确。改后的集合只对应 gold 选的 `nearest` 插值。按精确整数算线性插值、改用 lower／higher／midpoint、只修端点等合理修法，内部分界会不同，都会被判 0。题面与公开文档里找不到“内部分界必须取某个数据值”的依据。
2. **直接测试题面问题的新测试走不到 bug（T2a）。** `test_set_index_interpolate_large_uint` 在 P2P 里，说明它在 base 上就通过。原因是它用 1 个输入分区、`npartitions=1`，`set_index` 走“数据已排序”的快速路径，直接用精确的 `mins`/`maxes` 作 divisions，`partition_quantiles` 的结果被丢弃。所以核心要求在参考测试里没有会在 base 上失败的直接断言，按 §4 第 1 步为 S1。
3. **退化候选会得 1（T2b，待实跑）。** F2P 只看小整数上的 `{1,2,4}`。只要把整数插值换成 `nearest`，哪怕仍经 float64 计算（`nearest_via_float` 一类），也能通过 F2P 与全部 P2P，而题面原例的最小值仍然错误。按 §4 第 3 步为 S1。
4. **示例拟合（T2c）。** 唯一直接相关的断言只用题面两个字面值和 `npartitions=1`。
5. P2P 里没有任何测试直接调 `partition_quantiles` 检查端点，也没有 ≥ 2**63、int64 大值、输出分区多于唯一值、`set_index` 行守恒这些实例。

## (c) gold 可能有什么问题（G1，已有探针支持）

gold 只在 `percentiles_summary` 里把整数改成 `nearest`，下游 `process_val_weights` 没动。

1. **唯一值不足分支仍用 `np.interp`。** 当 `len(vals) < npartitions + 1`（唯一值个数不超过输出分区数）时，结果经 float64 插值，端点再次被舍入。实测：题面原例改用 `npartitions=3`，gold 返回 `…744`、`…248`，与 base 同错。`set_index` 用 disk shuffle 时，6 行只剩 3 行（静默丢行）；用 tasks shuffle 时 3 行放错分区。
2. **uint64 跨 2**63 时转成 float64。** `process_val_weights` 用 `np.array(vals)` 把 Python int 列表转回数组。值同时有小于和不小于 2**63 的时候，numpy 1.20 推断成 float64，再 `astype(uint64)` 时丢精度，2**64-1 溢出为 0。实测：gold 对 `[2**63+1, 2**63+1025, 5, 2**64-1]` 返回 `[5, 0]`，divisions 不单调。
3. int64 大值（含负数）在 gold 上正确（一例实测）。
4. 待查：`set_index(npartitions="auto")` 在 `shuffle.py` 里对 divisions 再做一次 `np.interp`，可能同样舍入。这不在 gold 的修改位置。

因此 gold 在同一核心要求的非示例实例上不满足题面。若修订补这些实例，gold 会失败，需要按 D4 用经独立核实的替代正对照。

## (d) 我认为合理的修法与待查的候选方向

合理修法（内部分界可以各不相同）：
- 整数用 nearest、lower、higher 等不需要插值的方式取实际数据值，并让下游保持整数精度：`process_val_weights` 按原 dtype 或 object 建数组，唯一值不足分支改成重复已有值，不再插值；
- 保留 linear，但用精确整数算术（Python int 或 object 数组）计算后再取整；
- 保留近似内部值，但把端点强制设为精确的最小、最大值，并把内部值夹在两者之间（要注意 float 转 uint64 的溢出）。

我准备构造的反例方向：
- 吞错或抑制症状：只在 `set_index` 里用精确的 mins/maxes 改写 divisions 两端，`partition_quantiles` 本身不修；
- 部分规模或阈值：只修 `len(vals) >= npartitions + 1` 的分支（即 gold 式）；只在输出分区数为 1 时返回精确端点；
- 依赖顺序：只从第一个、最后一个分区取端点，假设数据已排序，而题面明确说最小值在数据末尾；
- dtype 子集：只修 uint64 不修 int64；借 int64 视图修（≥ 2**63 会坏）；
- 只处理示例字面值：例如只在长度为 2 或 `npartitions=1` 时特判；
- 端点改对但内部值舍入越过最大值：只覆盖首末两个值，不夹住内部值；
- 至少一个“合理但与 gold 不同”的实现：精确整数 linear，用来查修订版是否过严。

## (e) 修订测试应补什么、注意什么

- 断言放宽为行为断言：divisions 是整数（原有 `test_set_index_interpolate_int`）、有序、端点等于真实最小、最大值，不锁内部集合；
- 直接调 `partition_quantiles`，检查首末值与 dtype，覆盖非示例实例：多输入分区且最小值在后面的分区、输出分区多于唯一值、跨 2**63 的 uint64、int64 大负数；
- `set_index` 必须强制走分位数路径（输入分区数与输出不同，或数据无序），并检查行数守恒、每行落在自己分区的 divisions 范围内；disk 与 tasks 两种 shuffle 都要看；
- 不要过严：不锁内部分界值、不锁插值方式；`npartitions="auto"` 路径是否纳入要先确认；divisions 允许重复。
