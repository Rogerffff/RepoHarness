# dask__dask-8597：第3类诊断结果

2026-09-30 / Claude（云端，第3类第二批主审作者）。原分类：第3类“已有具体疑点，缺辨别实验”。工作清单登记的下一步：“运行已设计的 split=True 部分修复与默认警告对照，核正式得分和实际数组；同时确认已验数组开发路径，不能靠候选池身份跳过。”

读历史材料前的初判封存在 [initial_judgment.md](initial_judgment.md)。

> **收口状态（09-30）**
>
> - **作者诊断已完成，证据已归档**，见 [evidence/](evidence/)，本页分数都有账本支持。已完成的项目：
>   - 正式评分：原材料 21 次、修订草案 v1 诊断评分 21 次、修订草案 v2 诊断评分 21 次；
>   - 私有行为矩阵：21 个变体，每个 41 格；
>   - 修订测试逐实例核对；
>   - pytest 8.3.2 下的修订测试私有核对；
>   - 开发路径等效核对。
> - **还没做**：独立复核（v1 §7.3）。正对照仍是 gold，不需要 D4 的替代正对照。4 个非 gold 合理实现只用来查误拒，由本主审编写，复核时请一并核对。
> - **下一步**：请不继承上下文的复核者做独立复核。重点：
>   1. `split_only_zero` 零宽数组全对，只丢默认大块警告。本页据此判 S1，并在修订测试里加了默认警告断言。请核对这条行为是否属于“有文档、常用的公开行为”（§3）。
>   2. 两个“多发警告”的候选被判 0：`swallow_warn` 在每次零宽索引时都发除零 `RuntimeWarning`；`eager_empty` 在结果超过约 5000 行时，经 `from_array` 自动分块发 `RuntimeWarning`，这是 base 既有的缺陷。本页按同一标准判两者不合格（§3）。若复核认为由既有缺陷引出的警告不应计入，可把 c4 的下标数降到 4000 以下，例如 1200。按本页的探针推算（未实跑），这样 `cap_one`、`cap_hundred` 仍为 0，`eager_empty` 变为 1。探针结果是 `from_array(np.zeros((n, 0)))` 在 n=4000 时不告警、n=5000 时告警，`cap_hundred` 在超过 500 个下标时告警。
>   3. `clamp1` 只在极端规模或极小 `array.chunk-size` 下误发警告，本页判为合理实现，登记 T3。
>   4. 修订 v2 是否还有能通过的错误候选。已知边界：零宽时把每块固定封顶在 2400 行及以上的写法能通过 v2，见 §3。
>
>   复核用原镜像 `xingyaoww/sweb.eval.x86_64.dask_s_dask-8597`（本机标签 `c3keep/dask8597:src`）即可做私有对照；正式评分要用 compat_v1 派生镜像，见 §2。

**结论：问题和修法已明确，建议转第2类。**（独立复核尚未进行。）

- **09-21 登记的“仅 split=True 时算阈值”部分修复已坐实（S1，§4 第 4 步）。**
  - 候选 `split_only` 逐字采用 09-21 复核给出的条件，正式评分 **1**：F2P 通过，116 项 P2P 全过。
  - 实际数组：默认配置与 `False` 下，原例得到 `(1, 0)`、float64，结果正确；但在有文档的 `array.slicing.split-large-chunks: True` 下，**题面原例本身仍抛 `OverflowError`**。
  - 非空数组在默认配置下的大块 `PerformanceWarning` 也消失了。守护这条文档行为的公开旧测试 `test_getitem_avoids_large_chunks` 在评分日志里是 FAILED（`DID NOT WARN`），测试退出码为 1；但它不在参考名单里，reward 仍为 1。
- **原测试只测题面原例的字面值（S1：§4 第 2 步 T2c；第 3 步 T2b）。** 共 11 个错误候选正式评分得 1：
  - 只在部分配置有效：`split_only`、`split_only_zero`；
  - 只覆盖示例的形态：`last_axis_only`、`axis0_only`、`dedup_slice`；
  - 只在较小规模下正确：`cap_one`（超过 5 个下标误发警告）、`cap_hundred`（超过 500 个）、`eager_empty`（结果约 5000 行以上时误发警告）；
  - 提前返回的退化候选：`single_block`；
  - 只覆盖 dtype 子集：`float_blocks_dep`；
  - 返回类型不对：`return_numpy`。

  noop 0、gold 1，与 09-19 历史一致。
- **没有发现误拒（T1）。**
  - 4 个与 gold 写法不同的合理实现在原材料和两版修订上都得 1：`clamp1`、`lazy_threshold`、`errstate_catch`、`eager_single_chunk`。其中 `eager_single_chunk` 改的是 `Array.__getitem__`，修改位置与 gold 不同。
  - 原测试判 0 的 4 个候选确实有错：`swallow_warn`、`warn_zero` 多发警告，`swallow_self` 形状错，`float_blocks` 图依赖不一致。
- **修法：R-c 修订版 v2。** 只改唯一 F2P 的函数体，测试 ID 与分组不变：
  - 原 3 行保留；
  - 补 4 个非示例实例，每个在 `split-large-chunks` 为 None／False／True 时各跑一遍，并显式检查结果是 dask Array；
  - 保留默认配置对真正大块的 `PerformanceWarning`。

  修订版正式诊断评分：noop 0；gold 与 4 个合理实现为 1；15 个错误候选全为 0。
  - v1 的 c4 只有 120 个下标，放过了 `cap_hundred` 与 `eager_empty`，两者正式评分都是 1。v2 把 c4 改为 12000 个下标，其余不变。
  - c2、c3、c4 与默认警告断言各至少单独拦住一个错误候选。
- **gold 仍作正对照**，不需要 D4。
- **开发路径已在云端按等效方式核对，与 09-25 记录一致。**
  - 在 actor 等效镜像（公开镜像加离线 pytest 7.4.4，wheel sha256 与 `actor_dask8597_v1` 相同）中，以 UID 54321 执行 09-25 登记的 5 条开发命令，结果全部符合预期；模拟一次源码修改后，解题者能直接看到三种配置下的实际数组。
  - 原公开镜像（pytest 8.3.2）上，两项公开旧测试仍因 `pytest.warns(None)` 报 `TypeError`，所以 actor 必须用派生镜像。
  - 正式 actor 入口（CC 2.1.205 加桩端点）云端没有，未跑。
- **实施依赖 D6 的“测试补丁替换”切片**，不改参考名单，也不需要 `statement_replace`。评分沿用 compat_v1 配方；修订测试本身不依赖该配方，pytest 8.3.2 下私有核对结果相同。

## 1．公开要求

**题面**（标题“Indexing 0-D dask array handling raises exceptions”）：
- `dask.array.from_array(numpy.zeros((3, 0)))[[0]]` 抛 `OverflowError: cannot convert float infinity to integer`；
- 期望“match numpy behavior”：`numpy.zeros((3, 0))[[0]]` 得到 `array([], shape=(1, 0), dtype=float64)`。

标题里的“0-D”用词不准确：原例是二维数组，其中一个轴长度为 0，不是零维标量。原例能消除歧义（P4，登记）。

**核心要求**（按题面的一般表述，v1 §4）：数组的其它轴中有长度为 0 的轴时，用整数列表做花式索引不应报错；结果的 shape、dtype 与 NumPy 相同，并且仍是 dask Array。空数组没有数值可比，shape、dtype 和结果类型就是这道题要比较的全部内容。核心要求不限于原例的以下形态：
- 二维、零长度轴在最后、沿第 0 轴索引；
- 单个下标 `[0]`、默认分块（单块）、float64；
- 默认配置。`array.slicing.split-large-chunks` 是有文档的公开配置（`dask/dask.yaml`、`docs/source/array-slicing.rst`、`take` 的 docstring），取 `True` 或 `False` 时同样要成立。

**根因**（base 源码可见）：`take` 用其它轴元素数之积 `other_numel` 估算每块能放多少行。`other_numel` 为 0 时，`nbytes / 0` 得 `inf`，numpy 先发除零 `RuntimeWarning`，随后 `math.ceil(inf)` 抛 `OverflowError`。

**修改位置直接相关、需要保留的已有公开行为**：
- **默认大块警告**：默认配置下，花式索引产生超过 `array.chunk-size`（默认 128MiB）5 倍的块时发 `PerformanceWarning`。依据有三处：
  - `array-slicing.rst`：“Dask warns when indexing like this produces a chunk that's 5x larger than the `array.chunk-size` config option”；
  - `dask.yaml`：`split-large-chunks: null  # ... Warns by default.`；
  - 公开旧测试 `test_getitem_avoids_large_chunks`。它不在参考名单里，原因是其中用了 pytest 8 已不接受的 `pytest.warns(None)`。
- **`False` 静音、`True` 拆块**：P2P 中的 `test_take_avoids_large_chunks`、`test_take_uses_config` 保护 `True` 拆块；`False` 静音只由上面那项非参考测试保护。
- **空块不是“大块”**：零字节的块永远不会超过 `array.chunk-size` 的 5 倍，这是同一条文档规则的直接推论。因此空块不应触发警告或拆块。
- **不产生多余警告**：
  - NumPy 原例不告警；
  - 仓库公开的 `setup.cfg` 用 `filterwarnings = error:::dask[.*]`（numpy、pandas、distributed 同理）把归属这些模块的警告设为错误；
  - 公开旧测试 `test_slicing_integer_no_warnings` 要求普通整数索引不告警。

**不属于核心要求（只登记）**：
- **先切片出零长度轴、再做列表索引**，例如 `da.ones((3, 4))[:0, [1, 3]]`，原数组本身不空。根因相同，gold 与所有在 `take` 里修的实现都能处理；但它不是题面说的“带零长度轴的数组”，登记为 T3。
- **极端规模或极小 `array.chunk-size` 下的阈值**：见 `clamp1`。
- **非 NumPy 后端**（cupy、sparse）的 meta 类型：未查。
- **用 dask 数组作下标**（`x[da.from_array(...)]`）：走另一条路径，base 上就不出错（矩阵 Z9）。
- **相邻的既有缺陷，本题范围外**：用自动分块创建较大的零大小数组时，`auto_chunks` 自身会除零。例如 `da.from_array(np.zeros((n, 0)))`、`da.zeros((n, 0))`，在 base 上 n=4000 不告警，n=5000 起发 `RuntimeWarning: divide by zero encountered in divide`；显式 `chunks=-1` 不告警。gold 也不修它。探针见 `evidence/probes/auto_chunks_threshold.txt`（`probe_auto_chunks.sh`）。修订测试的输入都很小，不会碰到它；第2类加实例时要避开“自动分块的大零大小输入”。

## 2．实测

### 环境与材料

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.dask_s_dask-8597:latest`，本机标签 `c3keep/dask8597:src`；RepoDigests `sha256:ab148b56…03fb`，与 ingest 冻结摘要一致；image ID `sha256:f6d90e1b…7fd7` |
| 派生镜像 | compat_v1 云端等效重建，`sha256:194ec0f6…46f0`，标签 `rh2-envrepair/compat-v1-dask__dask-8597:c3cloud`，记录见 [evidence/derived/image.json](evidence/derived/image.json)。保留 base 的全部层，只加一层 `COPY wheels/ /opt/rh2/compat-wheels/`。wheel `pytest-7.4.4-py3-none-any.whl` 共 325287 字节，sha256 `b090cdf5…01d8`，与 09-19 compat_v1、09-25 `actor_dask8597_v1` 计划登记的一致，镜像内文件已复核。09-19 原版派生 ID 为 `sha256:065c32c1…`，本机 ID 不能跨机比较。**这是等效重建，不是逐字节重建** |
| 安装配方 | 09-19 compat_v1 [`dask__dask-8597.json`](../../../env_recipe_repair_20260919/compat_v1/recipes/dask__dask-8597.json)，sha256 `bb63e37f…f22d`。评分安装段先离线装 pytest 7.4.4，再执行原有的 `pip install --no-deps -e .`；每份评分日志都打印 `RH2_COMPAT_VERSIONS={"pytest": "7.4.4"}` |
| 运行时 | Python 3.9.19、numpy 1.26.4、dask `2022.01.0+10.gc1c88f066`（`/testbed` 可编辑安装）；原镜像 pytest 8.3.2，配方安装后为 7.4.4；Docker 29.3.1、overlay2、cgroup v1 |
| 材料 | 题面 sha256 `6a8ccf4a…fa05`；gold `e1ed047b…22e4`，与 ingest 一致；原 test_patch `472ecb0e…23c7`，与 09-21 复核登记一致。F2P 1 项、P2P 116 项，都在 `dask/array/tests/test_slicing.py`。评分命令 `pytest -n0 -rA --color=no dask/array/tests/test_slicing.py` |
| 评分 | grader `swebench-4.1.0+swegym_parsers@242429c1`，修订版另加后缀 `+c3-dask8597-rc-v1` 或 `-v2`。profile `sha256:3ec1bfa8…0a94`：UID 54322、`deny_all`、2 CPU／4 GiB。候选以 UID 54321 `git apply`，投影只含被改动的源文件 |
| 代码 | 分支 `claude/category3-20260929`。运行期间 HEAD 由 `c6bb4ef6` 变为 `5d4b90c0`，是负责人提交的其它题目。评分路径与 `a31cdcd` 逐字相同：`git diff` 只列出快照提交加入的两个诊断包装和 R2E 摄入。两个 HEAD 之间，`rh2/src`、`rh2/scripts` 与这两个包装都没有变化 |

### 候选

全部候选由 [`make_candidates.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/make_candidates.py) 对 base 源码做逐字替换生成，替换前断言原文恰好出现一次。`gold_regen` 与导出的 gold 只差 hunk 头部的函数名，用来核对替换位置，不参与评分。判对错依据的是公开要求，不以 gold 为答案。

**（a）合理实现（查误拒 T1）**

| 候选 | sha256 前缀 | 做法 |
| --- | --- | --- |
| gold | `e1ed047b` | 在 `take` 中把 `other_numel == 0` 并入 `isnan` 分支，阈值取无穷大 |
| `clamp1` | `b571bcdf` | 常见的防除零写法 `max(other_numel, 1)`。阈值有限：默认配置下约 1600 万行才拆块，约 8400 万行才告警 |
| `lazy_threshold` | `e28d8e74` | 阈值先设为无穷大，只在 `other_numel > 0` 时计算。这是 09-21 复核提出的非 gold 路线 |
| `errstate_catch` | `04c8e7dc` | 在 `np.errstate(divide="ignore")` 下相除，`math.ceil` 溢出时取无穷大 |
| `eager_single_chunk` | `7f32a1e1` | 改在 `Array.__getitem__`：数组没有元素时，用 NumPy 在同形状的空替身上算出结果，再以单块包成 dask Array。修改位置与写法都和 gold 不同 |

**（b）错误候选（查漏判）**，类别对应作者须知 §2.3：

| 候选 | sha256 前缀 | 构造 | 类别 | 违反公开要求的输入（实测） |
| --- | --- | --- | --- | --- |
| `split_only` | `fbe14ce1` | 09-21 登记：只在 `split-large-chunks is True` 时算阈值 | 只对部分配置有效 | `True` 下原例仍抛 `OverflowError`；默认配置不再发大块警告 |
| `split_only_zero` | `dd88cbbd` | 在 `split_only` 上再加 `other_numel == 0` | 同上 | 零宽数组三种配置都对；默认配置不再发大块警告 |
| `last_axis_only` | `6e6b65b5` | 只看最后一个轴是否为空 | 示例形态子集 | `np.zeros((0, 3))[:, [2, 0, 2]]`、`(6, 0, 4)` 仍抛 `OverflowError` |
| `axis0_only` | `911578ce` | 只处理沿第 0 轴的索引 | 示例形态子集 | `np.zeros((0, 3))[:, [2, 0, 2]]` 仍抛 `OverflowError` |
| `dedup_slice` | `e5f8f780` | 空数组里把整数列表换成它覆盖的切片 | 示例字面值（单个下标） | `[0, 1, 2] * 4` 得 3 行，不是 12 行 |
| `cap_one` | `52e0d25a` | 零宽时每块 1 行 | 只对小规模有效 | 默认配置下超过 5 个下标就误发“large chunk”警告；`True` 下逐行拆块 |
| `cap_hundred` | `c8685c4d` | 零宽时每块 100 行 | 只对小规模有效 | 默认配置下超过 500 个下标误发警告 |
| `eager_empty` | `279c86a2` | 与 `eager_single_chunk` 相同，但用 `from_array` 的自动分块包装结果 | 只对小规模有效 | 结果约 5000 行以上时，自动分块发除零 `RuntimeWarning`（上文登记的既有缺陷）。原设计为合理实现，v2 实测后改判 |
| `single_block` | `684f549a` | 提前返回，所有行都从第一个块取 | 退化（提前返回） | 其它轴有多个块时，计算抛 `KeyError`（缺块） |
| `float_blocks_dep` | `042ad64b` | 提前返回，块由 `np.zeros(shape)` 生成，仍引用输入块 | dtype 子集 | int32、int64 数组算出 float64 块 |
| `return_numpy` | `9451367d` | 数组没有元素时直接返回 `numpy.ndarray` | 返回类型子集 | 结果不是 dask Array，没有 `.compute()`、`.chunks` |
| `swallow_warn` | `cdc58ac0` | `try/except OverflowError` 取无穷大，不避开除法 | 吞掉错误 | 数组正确，但每次都发 numpy 除零 `RuntimeWarning` |
| `warn_zero` | `b9df2fe1` | 零宽时阈值写成 0 | 阈值错误 | 默认配置对空块误发警告；`True` 下 `ZeroDivisionError` |
| `swallow_self` | `27c1f592` | 溢出时原样返回输入 | 吞掉错误并报告成功 | 原例得 `(3, 0)` |
| `float_blocks` | `310bfa8b` | 提前返回，块由 `np.zeros` 生成，不引用输入 | 退化（空产物） | 图依赖不一致，`HighLevelGraph.validate` 报错 |

**“依赖执行顺序”一类在本题不适用。** 空数组的行里没有数据，下标的顺序和重复只影响长度，不影响内容。最接近的构造是：
- `single_block`：依赖所需的行都在第一个块；
- `dedup_slice`：把乱序、重复的下标当成连续区间。

修订测试的 c3 实例用乱序、重复加负下标，覆盖了 gold 的分块计划。

### （1）私有行为矩阵

对 21 个变体（base、gold 与 19 个候选），在断网、root 的一次性容器中执行 [`behavior.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/behavior.py)（经 `semantic_control.py`）。镜像为 compat_v1 派生镜像，已先离线装好 pytest 7.4.4。

零宽实例（Z*）的判定条件：
- 不抛异常；
- 返回 dask Array；
- shape、dtype 与 NumPy 一致；
- `assert_eq` 通过（它检查图、逐块 shape／dtype 与计算结果）；
- 不发 `PerformanceWarning` 或 `RuntimeWarning`。

每个零宽实例都在 `split-large-chunks` 为 None／False／True 时各跑一遍。

零宽实例如下：

| 编号 | 输入与索引 | 说明 |
| --- | --- | --- |
| Z1 | `np.zeros((3, 0))[[0]]` | 题面原例 |
| Z2 | `np.zeros((0, 3))[:, [2, 0, 2]]` | 零轴在前，沿第 1 轴索引 |
| Z3 | `np.zeros((6, 0, 4), dtype="i4")`，chunks `(2, -1, 2)`，下标 `[5, 0, 5, -1, 3]` | 零轴在中间，int32，多块 |
| Z4 | `(6, 0)`，chunks `(2, -1)`，下标 `[5, 0, 5, -1]` | 被索引轴多块 |
| Z5 | 12 个下标 | 较多下标 |
| Z6 | int64 | 整数 dtype |
| Z7 | 布尔列表 | |
| Z8 | `da.take` | 公开函数入口 |
| Z9 | dask 数组作下标 | base 就对，不是本题实例 |
| Z10 | `ones((3, 4))[:0, [1, 3]]` | 混合切片，T3 |
| Z11 | `(3, 0, 4)` | 其它轴多块 |
| Z12 | 空下标 | base 就对 |

非空项与边缘项：
- **N 大块**：公开旧测试 `test_getitem_avoids_large_chunks` 的场景。默认配置应告警，`False` 应静音，`True` 应拆成 12 块。
- **N 小**：`test_slicing_integer_no_warnings` 的场景。
- **E**：`array.chunk-size` 设为 1kB 时，零宽数组用 700 个下标。只登记 T3。

| 变体 | 原例 Z1（None／False／True） | 其它零宽实例（Z2–Z8、Z11） | 非空：默认大块警告 | 边缘（T3，不断言） |
| --- | --- | --- | --- | --- |
| base | 三种配置都抛 `OverflowError` | 全部抛 `OverflowError` | 正常 | Z10、E 抛异常 |
| gold、`lazy_threshold`、`errstate_catch` | 全部 `(1, 0)`、float64 | 全部正确 | 正常 | Z10、E 都正确 |
| `clamp1` | 正确 | 全部正确 | 正常 | E：1kB 下 700 个下标误发大块警告 |
| `eager_single_chunk` | 正确 | 全部正确 | 正常 | Z10 抛 `OverflowError`（原数组不空，不经过它的分支）；E 正确 |
| `eager_empty` | 正确 | 全部正确（本矩阵下标都很少；12000 个下标见修订测试） | 正常 | Z10 同上；E：`from_array` 自动分块发除零警告 |
| `split_only` | 正确／正确／**`OverflowError`** | `True` 下全部 `OverflowError` | **不告警** | — |
| `split_only_zero` | 正确 | 全部正确 | **不告警** | — |
| `last_axis_only` | 正确 | Z2、Z3、Z11 抛 `OverflowError` | 正常 | Z10 抛异常 |
| `axis0_only` | 正确 | Z2 抛 `OverflowError` | 正常 | Z10 抛异常 |
| `dedup_slice` | 正确 | Z3、Z4、Z5、Z7、Z11 长度错（如 Z5 得 3 行，而不是 12 行） | 正常 | Z10、E 错 |
| `cap_one` | 正确 | Z5 在默认配置下误发大块警告；`True` 下拆成 12 个 1 行块 | 正常 | E 误发警告 |
| `cap_hundred` | 正确 | 全部正确（本矩阵下标不到 500 个） | 正常 | E 误发警告 |
| `single_block` | 正确 | Z3、Z11 计算时 `KeyError`（缺块）；Z4 靠 numpy 的越界容忍“碰巧”对，同时发 `DeprecationWarning` | 正常 | — |
| `float_blocks_dep` | 正确 | Z3、Z6 声明 int32／int64，算出 float64 | 正常 | — |
| `return_numpy` | 返回 `ndarray` | 全部返回 `ndarray` | 正常 | — |
| `swallow_warn` | 数组正确，但发除零 `RuntimeWarning` | 同左 | 正常 | — |
| `warn_zero` | 默认配置误发警告，`False` 正确，`True` 抛 `ZeroDivisionError` | 同左 | 正常 | — |
| `swallow_self` | 得 `(3, 0)` | 除 Z2 外形状都错（Z2 的结果碰巧与输入同形） | 正常 | — |
| `float_blocks` | 图校验失败 | 全部图校验失败 | 正常 | — |

所有变体的 N 小一项都正确。逐格原始输出见 `evidence/semantic_v1/out/<变体>/behavior.out`。同一批容器里还应用原 test_patch 跑了整份 `test_slicing.py`（私有模拟评分，`orig_file`），结果与下面的正式评分逐一相同。

### （2）原材料正式评分

`replay_grade.py run`，加 compat_v1 配方与派生镜像，逐个串行；命令见 [`run_formal.sh`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/run_formal.sh) 的 `orig` 模式。所有行都满足：参考缺席 0、安装 rc 0、清理成功、`stage_error` 为空，评分日志中 pytest 为 7.4.4。

| 候选 | reward | F2P | P2P 失败 | 测试退出码 | 非参考旧测试（大块警告） | 说明 |
| --- | --- | --- | --- | --- | --- | --- |
| noop | 0 | 0/1 | 0/116 | 1 | PASSED | F2P 失败于 `RuntimeWarning: divide by zero encountered in scalar divide`（warnings-as-errors）；118 passed，与 09-19 历史一致 |
| gold | 1 | 1/1 | 0/116 | 0 | PASSED | 119 passed、2 skipped、2 xfailed，与 09-19 历史一致 |
| `clamp1`、`lazy_threshold`、`errstate_catch`、`eager_single_chunk` | 1 | 1/1 | 0/116 | 0 | PASSED | 合理实现 |
| `split_only` | **1** | 1/1 | 0/116 | **1** | **FAILED** | 非参考旧测试 `DID NOT WARN`：默认大块警告消失，但该测试不计分 |
| `split_only_zero` | **1** | 1/1 | 0/116 | **1** | **FAILED** | 同上 |
| `last_axis_only`、`axis0_only`、`dedup_slice` | **1** | 1/1 | 0/116 | 0 | PASSED | |
| `cap_one`、`cap_hundred`、`eager_empty` | **1** | 1/1 | 0/116 | 0 | PASSED | |
| `single_block`、`float_blocks_dep`、`return_numpy` | **1** | 1/1 | 0/116 | 0 | PASSED | |
| `swallow_warn` | 0 | 0/1 | 0/116 | 1 | PASSED | F2P 失败于 `RuntimeWarning: divide by zero encountered in scalar divide` |
| `warn_zero` | 0 | 0/1 | 0/116 | 1 | PASSED | F2P 失败于 `PerformanceWarning: Slicing is producing a large chunk` |
| `swallow_self` | 0 | 0/1 | 0/116 | 1 | PASSED | F2P 失败于 `a and b have different shapes (a: (3, 0), b: (1, 0))` |
| `float_blocks` | 0 | 0/1 | 0/116 | 1 | PASSED | F2P 失败于 `incorrect dependencies[...]`（`HighLevelGraph.validate`） |

加粗的是违反公开要求却得 1 的错误候选，共 11 个。

### （3）默认警告对照

09-21 主审与复核都推测：“仅 split=True 时算阈值”会丢掉默认警告，并漏修 `True` 下的零长度轴。实测结果：
- **正式评分链**：gold 的评分日志中 `test_getitem_avoids_large_chunks` 为 PASSED。`split_only`、`split_only_zero` 为 FAILED，位置在 `test_slicing.py:884` 的 `arr[indexer]`，报错如下：

  ```
  Failed: DID NOT WARN. No warnings of type (<class 'dask.array.core.PerformanceWarning'>,) were emitted.
  ```

  整份测试的退出码因此为 1，但 reward 仍为 1，与 09-21 对计分机制的静态判断一致。
- **私有矩阵中的实际数组**：
  - 默认配置下，gold 的 `arr[[0] + [1] * 11]` 发 1 条 `PerformanceWarning`，块为 `(1, 11)`；`split_only` 不告警，块同样为 `(1, 11)`；
  - `True` 下两者都拆成 12 个 1 行块，都不告警；
  - `split_only` 在 `True` 下对题面原例先发除零 `RuntimeWarning`，再抛 `OverflowError`。
- **反方向，即对空块误发警告**：
  - `warn_zero` 在原例上就触发，原测试判 0；
  - `cap_one` 超过 5 个下标才触发，`cap_hundred` 超过 500 个才触发。原例只有 1 个下标，所以原测试判它们 1。

### （4）开发路径核对（“已验数组开发路径”）

历史证据是 09-25 的正式 actor 入口（CC 2.1.205、UID 54321、`actor_dask8597_v1`），原始捕获文件不在云端；正式入口需要 CC 安装包与桩端点，云端也没有。本页因此用 [`devpath_check.sh`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/devpath_check.sh) 做等效核对：
1. 在一次性断网容器里，以 root 离线装 pytest 7.4.4，pin 与 wheel 同 `actor_dask8597_v1`；
2. 把 `/testbed` 交给 UID 54321；
3. 以该身份逐条执行 [`commands/dask__dask-8597.json`](../../../../../../../rh2/experiments/task2_swegym_dev_20260925/commands/dask__dask-8597.json) 的 5 条命令。

这不是正式入口的复验。

| 命令 | actor 等效（pytest 7.4.4，UID 54321） | 原公开镜像（pytest 8.3.2，UID 54321） |
| --- | --- | --- |
| env | rc 0；`/opt/miniconda3/envs/testbed/bin/python`，dask 从 `/testbed` 导入，numpy 1.26.4，pytest 7.4.4 | rc 0；pytest 8.3.2 |
| mcve（预期非零） | rc 1，`slicing.py:647` 抛 `OverflowError`，即目标缺陷 | rc 1，同左 |
| narrow（预期 0） | rc 0：两项警告旧测试与 `missing[chunks0]`，3 passed、1 xfailed | **rc 1**：两项旧测试报 `TypeError: exceptions must be derived from Warning`（`pytest.warns(None)`） |
| file | rc 0：118 passed、2 skipped、2 xfailed | rc 1：116 passed、2 failed |
| tree | 干净，HEAD `c1c88f06` | 干净 |

另外三点：
- **修改后的实际数组**：以 UID 54321 用 `git apply` 应用 gold，模拟一次修改；再在 `warnings.simplefilter("error")` 下，对 `(3, 0)[[0]]`、`(0, 3)[:, [2, 0]]`、`(6, 0, 4) int32[[5, 0, 5]]` 在三种配置下取值。结果都是 dask Array，计算后分别为 `(1, 0)`、`(0, 2)`、`(3, 0, 4)`，dtype 与 NumPy 相同。解题者用公开 API 就能核对题面要求的数组。
- **`pip check`**：仍只报 base 原有的 `distributed 2024.8.0 has requirement dask==2024.8.0` 冲突，不影响本地数组路径，与 09-25 记录一致。
- **结论**：开发路径不能靠“候选池身份”跳过，也不需要跳过。按 09-25 的做法，actor 必须使用装了 pytest 7.4.4 的派生镜像；否则 narrow 命令中的两项公开旧测试无法运行，解题者也就看不到默认大块警告被破坏。

### （5）上游对照（只作佐证）

来源为 PyPI wheel，只读源码：
- dask 2022.2.0 的 `take` 与 gold 逐字相同；
- 2023.12.1 改用 `math.prod(max(x) for x in other_chunks)`，但仍保留 `or other_numel == 0` 时取无穷大；
- 2024.12.1 把 `take` 改写为基于 `_shuffle`，不再使用 split-large-chunks 阈值。

wheel sha256：2022.2.0 为 `feaf838f…`，2023.12.1 为 `55f316f3…`，2024.12.1 为 `1f32acdd…`。gold 的写法在上游保留了约两年，没有迹象表明 gold 本身有缺陷。

## 3．判定（v1 §3–§4）

| 步 | 结果 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有，不命中 | F2P 用 `assert_eq` 对原例检查 shape、dtype、逐块 shape／dtype、图与计算结果 |
| 2 是否只用题面示例的字面值 | **是 → S1（T2c）** | 唯一 F2P 就是题面原例：`(3, 0)`、`[0]`、第 0 轴、默认配置、单块、float64。116 项 P2P 中没有任何“其它轴长度为 0”的数组：`test_empty_list`、`test_empty_slice` 用的是非空数组上的空下标或空切片，走不到 `other_numel == 0` |
| 3 退化探测 | **`single_block` 正式得 1 → S1（T2b）** | 在 gold 的修改位置提前返回。违反的公开要求：其它轴有多个块的零宽数组（如 `(6, 0, 4)`、`(3, 0, 4)`）计算时 `KeyError` |
| 4 已有具体候选中，是否有得 1 而违反公开要求的 | **是 → S1** | 见下 |
| T1 | 未发现 | 4 个合理实现在原材料与两版修订上都得 1 |
| P4 | 登记 | 标题“0-D”用词不准，原例可消除歧义 |
| P5 | 不适用 | 没有两种相反的目标读法 |
| E1（开发条件） | 已处理，登记 | 公开镜像的 pytest 8.3.2 使两项公开旧测试报 `TypeError`；`actor_dask8597_v1` 与 compat_v1 已固定 pytest 7.4.4，云端等效复核通过 |
| T3 | 登记 | 混合切片 `x[:0, [1, 3]]`：gold 正确，`eager_single_chunk` 不处理；极端规模或极小 `array.chunk-size`（`clamp1`）；非 NumPy 后端（未查） |

第 4 步命中的依据：
- **09-21 登记的候选**：`split_only` 在有文档的 `True` 配置下，题面原例本身仍报错，属于同一核心要求的实例；同时去掉了有文档的默认大块警告。
- **只破坏文档行为**：`split_only_zero` 的零宽数组全对，只去掉默认大块警告，属于“有文档、常用的公开行为”。理由有两条：默认配置下每次花式索引都经过这条检查，文档专门用一段说明它；公开旧测试 `test_getitem_avoids_large_chunks` 直接断言它。
- **其余候选**：分别在零轴位置、索引轴、下标、规模、dtype、返回类型上违反核心要求，都不是罕见路径。
  - `cap_hundred` 超过 500 个下标即误发警告；
  - `eager_empty` 结果约 5000 行以上即误发警告。

  这两个量级在零宽数组的索引中都算常见，例如对 `(n, 0)` 的特征矩阵做几千行的重采样。

**多发警告的候选为什么判不合格，不算误拒**：
- **`swallow_warn`**：数组正确，只是每次零宽索引都多一条除零 `RuntimeWarning`。判不合格的理由：
  - 题面要求“match numpy behavior”，而 NumPy 原例不发任何警告；
  - 仓库公开的 `setup.cfg` 把归属 dask 模块的警告设为错误，这是本仓库对贡献代码的公开约束，解题者跑任何公开测试都会看到；
  - 修法很简单，加一行 `np.errstate` 或先判零即可，见 `errstate_catch`、`lazy_threshold`，不需要照抄 gold。
- **`eager_empty`**：同一标准。它的警告来自 base 既有的 `auto_chunks` 缺陷，但正是这个实现把索引结果交给自动分块，才让零宽索引出现了警告。去掉自动分块的同一设计 `eager_single_chunk` 在两版修订上都得 1，可见修订测试拒绝的是“多发警告”这一行为，而不是“在 `__getitem__` 里处理”这一设计。若复核认为既有缺陷引出的警告不该计入，替代办法见收口状态第 2 条。
- **`warn_zero`**：对零字节的块报“large chunk”，与文档规则矛盾；`True` 下还会除零。

**`clamp1` 为什么判为合理、只登记 T3**：它把空行按 1 个元素估算，阈值有限。
- 默认配置下，单块要超过约 8400 万个下标才会误发警告；只有 `array.chunk-size` 设到 1kB 这类极小值时，700 个下标才会误发。
- 两者都是罕见路径，结果始终正确，按 §4 第 4 步属于 T3。
- 修订测试不断言这种规模：用少见配置去拒绝一个常见的防除零写法，不合理。

**v2 的已知边界**：零宽时把每块固定封顶的写法（`cap_*`），在 c4 有 12000 个下标、默认配置下，只有封顶小于 2400 行（告警线为封顶的 5 倍，低于 12000）才会被拦住。
- 自然出现的有限阈值有两类：
  - 很小的常数，如 `cap_one`、`cap_hundred`，v2 能拦住；
  - 由 `array.chunk-size` 推出的公式，如 `clamp1` 约 1600 万行，属于罕见路径。
- 所以 v2 取 12000，登记此边界。

## 4．修法（交第2类）

### R-c：修订版测试草案 v2（当前草案；父版本 v1）

- 草案文件：[`revised_test_v2.patch`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/revised_test_v2.patch)，sha256 `4a5ce4e1…70ed`；
- 材料 JSON：[`materials_revised_v2.json`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/materials_revised_v2.json)，grader 后缀 `+c3-dask8597-rc-v2`；
- 修订后 grading 摘要：`sha256:fde54821…9df5`（原为 `75b4a558…4098`）；
- 生成脚本：`make_revised_test.py`，由 base 测试文件生成。

**改动范围**：只改 F2P `test_slice_array_null_dimension` 的函数体，测试 ID、F2P／P2P 分组和评分命令都不变。原来的 3 行原样保留在最前面，其后追加两部分。

1. **4 个非示例实例**：每个在 `split-large-chunks` 为 None、False、True 时各跑一遍，逐一 `assert isinstance(result, da.Array)` 与 `assert_eq(result, x[index])`：
   - c1 `np.zeros((3, 0))[[0]]`：题面原例放到三种配置下；
   - c2 `np.zeros((0, 3))[:, [2, 0, 2]]`：零轴在前，沿第 1 轴索引，下标重复；
   - c3 `np.zeros((6, 0, 4), dtype="i4")`，chunks `(2, -1, 2)`，下标 `[5, 0, 5, -1, 3]`：零轴在中间，int32；被索引轴与尾轴都有多个块；下标乱序、重复、含负数；
   - c4 `np.zeros((3, 0))[[0, 1, 2] * 4000]`：单块内 12000 个下标，属常见规模。gold 执行整条 F2P 只需 0.04 秒。
2. **默认大块警告**：在 `array.chunk-size = 0.1Mb` 下执行 `with pytest.warns(da.PerformanceWarning): arr[[0] + [1] * 11]`。场景取自公开旧测试 `test_getitem_avoids_large_chunks`；这里只用 `pytest.warns(类)`，pytest 8 也能运行。

“空块不应告警”没有单独写断言，而是沿用仓库 `setup.cfg` 的 warnings-as-errors。原 F2P 在 base 上失败，靠的也是这条配置（`RuntimeWarning`），修订版的依赖方式与之相同。所有实例的输入都很小，不会碰到 §1 登记的 `auto_chunks` 既有缺陷。

**v1 → v2**：只改 c4，从 `[0, 1, 2] * 40`（120 个下标）改为 `[0, 1, 2] * 4000`（12000 个）。原因是 v1 评分后，本主审另造了阈值候选 `cap_hundred`，并发现 `eager_empty` 在大结果上多发警告。这两个候选在 v1 上正式评分都是 1，在 v2 上都是 0。v1 的补丁、材料与 21 次评分保留为父版本证据。

**逐实例核对**（[`rev_cases.py`](../../../../../../../rh2/experiments/category3_cloud_20260929/dask8597/rev_cases.py)，每个实例是独立的 pytest 用例，放在 `dask/array/tests/` 下，警告过滤与 F2P 相同）：

| 实例 | 单独拦住的错误候选 | 与其它实例共同拦住的错误候选 |
| --- | --- | --- |
| 原 3 行 | — | 原测试已拦住的 4 个：`swallow_warn`、`warn_zero`、`swallow_self`、`float_blocks` |
| c1（三种配置） | — | `split_only`（`True`）、`return_numpy` 等 |
| c2 | `axis0_only` | `last_axis_only`、`split_only`（`True`）等 |
| c3 | `single_block`、`float_blocks_dep` | `last_axis_only`、`dedup_slice` 等 |
| c4（12000 个下标） | `cap_one`、`cap_hundred`、`eager_empty` | `dedup_slice` 等 |
| 默认大块警告 | `split_only_zero` | `split_only` |

- c2、c3、c4 与默认警告断言各至少单独拦住一个错误候选。
- c1 没有单独拦住的候选。保留它，是因为它把题面原例本身放到三种配置下，直接对应 `split_only` 的缺陷，而且成本很低。
- gold 与 4 个合理实现通过全部用例；base 只通过默认警告一项。
- 完整结果见 `evidence/semantic_rev2/out/*/rev_cases.out`。该模块同时包含 v1 的 c4（120 个下标）作对照。

**修订版正式诊断评分**（`--materials`，加 compat_v1 配方；F2P／P2P 名单与评分命令不变）。所有行都满足：参考缺席 0、安装 rc 0、清理成功、`stage_error` 为空。

| 候选 | 原材料 | 修订 v1 | 修订 v2 | v2 中 F2P 第一处失败（实例：评分日志 `E` 行） |
| --- | --- | --- | --- | --- |
| noop | 0 | 0 | 0 | 原 3 行：除零 `RuntimeWarning` |
| gold（正对照） | 1 | 1 | **1** | — |
| `clamp1`、`lazy_threshold`、`errstate_catch`、`eager_single_chunk` | 1 | 1 | **1** | — |
| `split_only` | **1** | 0 | 0 | c1 在 `True` 下：除零 `RuntimeWarning`，随后本会抛 `OverflowError` |
| `split_only_zero` | **1** | 0 | 0 | 默认大块警告：`DID NOT WARN` |
| `last_axis_only` | **1** | 0 | 0 | c2：除零 `RuntimeWarning` |
| `axis0_only` | **1** | 0 | 0 | c2：除零 `RuntimeWarning` |
| `dedup_slice` | **1** | 0 | 0 | c3：`a and b have different shapes (a: (6, 0, 4), b: (5, 0, 4))` |
| `cap_one` | **1** | 0 | 0 | c4（默认配置）：`PerformanceWarning: Slicing is producing a large chunk` |
| `cap_hundred` | **1** | **1** | 0 | c4（默认配置）：同上 |
| `eager_empty` | **1** | **1** | 0 | c4：`RuntimeWarning: divide by zero encountered in divide`（`from_array` 自动分块） |
| `single_block` | **1** | 0 | 0 | c3：numpy `DeprecationWarning: Out of bound index found`。原因是它从错误的块取行；私有矩阵中，同类实例计算到缺块时抛 `KeyError` |
| `float_blocks_dep` | **1** | 0 | 0 | c3：`assert dtype('float64') == dtype('int32')` |
| `return_numpy` | **1** | 0 | 0 | c1：`assert isinstance(result, da.Array)` 失败 |
| `swallow_warn` | 0 | 0 | 0 | 原 3 行：除零 `RuntimeWarning` |
| `warn_zero` | 0 | 0 | 0 | 原 3 行：`PerformanceWarning` |
| `swallow_self` | 0 | 0 | 0 | 原 3 行：形状 `(3, 0)` 与 `(1, 0)` 不同 |
| `float_blocks` | 0 | 0 | 0 | 原 3 行：图依赖校验失败 |

v2 纠正了原材料上 11 个错误候选得 1 的误判；原本判 0 的 4 个错误候选仍为 0；没有合理实现被新断言拒绝。评分环境：grader 后缀 v1 为 `+c3-dask8597-rc-v1`，v2 为 `+c3-dask8597-rc-v2`；v1 修订后的 grading 摘要为 `sha256:21882f1f…9c32`。

**pytest 8.3.2 下的私有核对**：在原公开镜像上不加配方，应用 v2 后跑整份文件，结果如下：
- gold 为 1：F2P 通过，116 项 P2P 全过；两项非参考旧测试因 `warns(None)` 失败，不计分；
- base、`split_only_zero`、`cap_hundred` 都是 0。

v1 做过同样的核对，结果一致。修订测试本身不依赖 compat_v1 配方；保留配方，是为了让 grader 与 actor 的开发条件以及 09-19 历史一致。

**修订后仍受保护的公开要求**：
- 零宽数组的列表索引在三种 `split-large-chunks` 设置下都不报错；
- 零长度轴可以在前、中、后，可以沿不同的轴索引，被索引轴与其它轴可以有多个块；
- 下标可以重复、乱序、含负数，也可以是常见规模；
- 结果是 dask Array，shape、dtype 与 NumPy 一致，并通过 `assert_eq` 的图与逐块校验；
- 零宽索引不产生警告；默认配置对真正的大块仍发 `PerformanceWarning`；
- 116 项 P2P 继续保护 `True` 拆块、`chunk-size` 配置、未知块大小等已有行为。

### 正对照

gold 通过全部新断言，仍作正对照，不需要 D4。4 个合理实现只用来证明修订没有误拒，由本主审编写，复核时请一并核对。

### 没有采用的做法

- **把两项公开旧测试 `test_getitem_avoids_large_chunks`、`test_slicing_integer_no_warnings` 加入 P2P**：同样能保护默认警告，但有两个问题：
  - 要改参考分组，不在 D6 首个切片的能力内；
  - 两项测试用了 `pytest.warns(None)`，会把评分绑死在 compat 配方上。

  本草案改为把默认警告断言直接写进 F2P 函数体，只需要测试补丁替换。
- **R-f**：不需要。修订测试的每项要求，都能从题面的一般表述、原例的 NumPy 输出、split-large-chunks 与大块警告的公开文档推出，不引入隐藏细节。

### 交接给第2类

1. 用 D6 的“测试补丁替换”切片落地 `revised_test_v2.patch`。测试 ID 与分组不变，不改参考名单，不需要 `statement_replace`。
2. 评分继续用 compat_v1 配方：离线 pytest 7.4.4，wheel sha256 `b090cdf5…01d8`。入库时固定派生镜像清单；本页用的是云端等效重建。
3. actor 继续用 `actor_dask8597_v1`（公开镜像加 pytest 7.4.4）。换机器后按已验配方重建，并在正式入口复验 5 条开发命令；云端只做了等效核对。
4. 复验：修订版下 noop 0、gold 1，4 个合理实现为 1，15 个错误候选为 0。
5. 独立复核，以及 Codex 复核（v1 §5）。
6. 若再加实例，避免用自动分块创建较大的零大小输入，理由见 §1 登记的既有缺陷。

## 5．当前用途（v1 §2，D6 落地前）

| 版本 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| 原版 | 是 | conditional：沿用旧 19 题的有条件比较，本页再补一项条件。原材料上 11 个错误候选得 1，比较须预登记事后审计，至少检查：`True` 配置下的原例、默认大块警告、其它轴为零长度的非示例实例、较多下标时是否多发警告、结果类型 | 否（S1 未处理） | 否（已用于模型比较） |
| 修订版 v2（草案） | 是 | conditional：D6 落地并复验 | conditional：同左，另需独立复核与 Codex 复核 | 否（修订后的题只能作标明版本的自建题） |

## 6．未做与剩余事项

- 独立复核：尚未进行。
- 正式 actor 入口（CC 2.1.205 加桩端点）的开发核对：云端没有条件，未做；已做 UID 54321 的等效核对。
- 非 NumPy 后端（cupy、sparse）：未查。
- 全仓测试：未跑，只跑了评分所用的 `test_slicing.py`。
- 上游 2024.12.1 的实际行为：未运行，只读了源码。
- T3 各项与 `auto_chunks` 既有缺陷：只登记，不设计修订。
- `materials_revised_v2.json` 的 `reason` 字段写于加入 `cap_hundred`、`eager_empty`、`eager_single_chunk` 之前，其中列出的是当时已知、在原材料上得 1 的 9 个错误候选。评分用的就是这份文件，所以没有改写；完整清单以本页为准。

## 7．版本与证据

**实验文件**，在 `rh2/experiments/category3_cloud_20260929/dask8597/`：

| 用途 | 文件 |
| --- | --- |
| 生成候选 | `make_candidates.py`、`candidates/*.patch` |
| 私有矩阵与逐实例核对 | `behavior.py`、`rev_cases.py`、`make_spec.py`、`run_semantic.sh`、`summarize_semantic.py` |
| 修订草案 | `make_revised_test.py`、`original_test.patch`、`revised_test_v1.patch`、`revised_test_v2.patch`、`revised_test_v*.py.tail`、`materials_revised_v1.json`、`materials_revised_v2.json` |
| 正式评分 | `run_formal.sh`、`summarize_formal.py` |
| 开发路径核对 | `devpath_check.sh` |
| 既有缺陷探针 | `probe_auto_chunks.sh` |

**原始证据**，在 [evidence/](evidence/)，全部文件的 SHA256 见 `evidence_manifest.json`：

| 目录 | 内容 |
| --- | --- |
| `formal/` | 原材料正式评分 21 次。每次运行都有 `ledger_<候选>.jsonl`、`run_<候选>.out`、评分日志与 `audit_<候选>/`；批量摘要见 `formal/batch_orig.log`，后补运行见证据根目录的 `formal_cap_hundred_*.log`、`formal_eager_single_chunk_*.log` |
| `formal_revised_v1/` | 修订 v1 诊断评分 21 次；批量驱动日志为根目录的 `formal_revised_v1_batch.log` |
| `formal_revised_v2/` | 修订 v2 诊断评分 21 次；批量驱动日志为根目录的 `formal_revised_v2_batch.log` |
| `semantic_v1/` | 私有矩阵，以及按原测试的私有模拟评分 |
| `semantic_v2/`、`semantic_rev2/` | 修订 v1、v2 的私有模拟评分与逐实例核对 |
| `semantic_v3_pytest8/`、`semantic_rev2_pytest8/` | 原镜像 pytest 8.3.2 下对修订 v1、v2 的核对 |
| `devpath/` | 开发路径等效核对 |
| `probes/` | `auto_chunks` 既有缺陷探针与 `array.chunk-size` 默认值 |
| `derived/` | 派生镜像记录；wheel 副本已删除，sha256 见 `image.json` |

**过程说明**：`run_semantic.sh` 的早期版本会把 specs 目录里已有的变体一并重跑，现已改为只跑请求的变体。私有矩阵是确定性的，重跑只会用相同结果覆盖同一输出目录；归档的是最后一次运行。正式评分每个候选、每个版本只跑一次。

**环境**：见[环境说明](../../environment.md)。
