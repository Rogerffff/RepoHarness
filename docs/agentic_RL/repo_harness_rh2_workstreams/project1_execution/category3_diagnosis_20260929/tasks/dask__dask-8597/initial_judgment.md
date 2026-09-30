# dask__dask-8597 主审：初判（读历史材料前封存）

2026-09-30，第3类第二批主审作者（Claude 子代理）。写完不再修改。

## 本稿读过什么

- 统一标准 v1 全文；本目录 README（“试点校准”“第二批复核补充的校准”）、environment.md、batch2_author_brief.md。
- `s2/ingest/` 三个 bundle 中本题的题面、public_hints、gold（`sha256:e1ed047b…22e4`，1 处改动）、test_patch（新增 1 个测试）、F2P（1 个）、P2P（116 个，全部在 `dask/array/tests/test_slicing.py`）、`eval_cmd`（`pytest -n0 -rA  --color=no`）。
- 镜像 `c3keep/dask8597:src`（image `f6d90e1b…`，RepoDigest `…dask_s_dask-8597@sha256:ab148b56…03fb`，与 ingest 冻结值一致）中的 base 源码：`dask/array/slicing.py` 的 `take`、`slice_wrap_lists`，`dask/dask.yaml` 的 `array.slicing.split-large-chunks: null`，`setup.cfg` 的 `[tool:pytest]`，以及 `test_slicing.py` 中与 `take`、警告、`split-large-chunks` 有关的公开测试。环境：Python 3.9.19、numpy 1.26.4、pytest 8.3.2。
- 一个 base 探针（一次性容器、断网、root，属私有对照）：题面原例在 base 上先发 `RuntimeWarning: divide by zero encountered in scalar divide`（`slicing.py:647`），再抛 `OverflowError: cannot convert float infinity to integer`；把警告设为错误时抛的是 `RuntimeWarning`。

**如实说明**：负责人的派发说明里转述了工作清单登记的下一步：“运行已设计的 `split=True` 部分修复与默认警告对照，核正式得分和实际数组；同时确认已验数组开发路径，不能靠候选池身份跳过。”旧题卡、status.json 条目与 `reviews/dvc_conan_dask.md` 我都还没有打开。标准 §10 有一行“Dask8597（正常题，6/6 全过）……训练候选还差正面覆盖证据（第 2、3 步），暂 conditional”，我读标准时看到了。

## 根因（源码直接可见）

`take` 为“避免产生过大块”计算每个输出块最多能放多少行：

```python
other_numel = np.prod([sum(x) for x in other_chunks])   # 其余各轴元素数之积
if math.isnan(other_numel):
    warnsize = maxsize = math.inf
else:
    maxsize = math.ceil(nbytes / (other_numel * itemsize))
    warnsize = maxsize * 5
```

只要**被索引轴以外**有一个轴长度为 0，`other_numel` 就是 0，`nbytes / 0` 得 `inf`（numpy 标量除法，先发 `RuntimeWarning`），`math.ceil(inf)` 抛 `OverflowError`。gold 把 `other_numel == 0` 并入 `isnan` 分支，令 `maxsize = warnsize = inf`：零字节的行放多少都不会超出块大小预算，也就既不拆块、也不告警。这是根因层面的通用修法。

`maxsize`、`warnsize` 各有一条用途：
- `warnsize`：默认配置（`split-large-chunks` 为 `null`）下，某个输出块行数超过它就发 `PerformanceWarning`；
- `maxsize`：`split-large-chunks: True` 时，行数超过它就用 `np.array_split` 拆块，拆成 `ceil(len / maxsize)` 份。

所以一个修法在默认配置下正确，不代表在 `split=True` 或 `split=False` 下也正确。

## (a) 题面核心要求

标题与“期望行为”：对含长度为 0 的轴的 dask 数组做列表（花式）索引，不应报错，结果应与 numpy 一致（原例 `da.from_array(np.zeros((3, 0)))[[0]]` 应得 `shape=(1, 0)`、`float64` 的空数组）。按一般表述理解，核心要求覆盖：

- 零长度轴在任意位置、被索引的是任意其它轴（原例是 2 维、零轴在最后、索引第 0 轴）；
- 任意列表内容（多个下标、重复、乱序、负下标、布尔列表）与任意分块；
- 结果的 shape、dtype 与 numpy 相同；空数组没有数值可比，**shape 与 dtype 就是这道题的全部“数值”**；
- 公开配置 `array.slicing.split-large-chunks` 的三种取值（`null` 默认、`True`、`False`）与 `array.chunk-size` 下都成立。这两个配置写在 `dask.yaml`／schema 与 `take` 的 docstring 里，是有文档、常用的公开行为；
- 不产生多余的警告：numpy 原例不告警；仓库公开的 `setup.cfg` 把归属 `dask.*` 模块的警告设为错误，`test_slicing.py` 也有“整数切片不应告警”（`test_slicing_integer_no_warnings`）、“`split` 显式设置后不告警”（`test_getitem_avoids_large_chunks`）的公开测试。这一点是否算核心要求，初判倾向“算有公开依据的常用行为”，待实测后定。

题面没有要求：具体修改哪个函数；输出分块的具体形状（公开测试只在非空数组上约束拆块规则）；用 `inf` 还是别的方式跳过拆块。

## (b) 原测试可能有什么问题

1. **示例拟合（§4 第 2 步，T2c）。** 唯一 F2P `test_slice_array_null_dimension` 只测题面原例的字面值：`np.zeros((3, 0))`、索引 `[0]`、第 0 轴、默认配置。116 个 P2P 里没有任何一个用到“其它轴长度为 0”的数组（`test_empty_list`、`test_empty_slice` 用的是非空数组上的空索引或空切片，走不到 `other_numel == 0`）。按 D1 严格版，这一步命中即 S1，走 R-c 补非示例实例。
2. **配置路径没有覆盖（候选辨别点）。** F2P 只在默认配置下跑。只修默认路径的写法（例如令 `warnsize = inf` 但把 `maxsize` 设为 0 或别的有限值）在默认配置下得 1，在 `split-large-chunks: True` 下会除零或产生错误分块。这就是工作清单说的“`split=True` 部分修复”一类，要实测它在原测试下的得分与实际数组。
3. **警告与 pytest 配置的交互（T1 风险，待实测）。** `setup.cfg` 的 `filterwarnings = error:::dask[.*]` 会把以下两种警告变成测试失败：
   - numpy 的除零 `RuntimeWarning`：只用 `try/except OverflowError` 兜底、不避开除法的修法，在普通使用中结果正确（只多一条警告），在测试中却会失败；
   - `take` 的 `PerformanceWarning`（`stacklevel=6`，归属到调用 `x[...]` 的测试模块）：把 `warnsize` 设得过小的修法，在默认配置下会对空数组发“large chunk”警告。
   这两类被判 0 是否合理，要看“不产生多余警告”是否有公开依据（见 (a) 最后一条）。初判倾向：有依据（numpy 不告警；仓库公开配置与公开测试都把 dask 的多余警告当错误），不算 T1；但要实跑确认失败原因确实是警告而不是别的。
4. **gold 本身**：通用修法，初判没有发现 gold 在其它实例上的缺陷；要在矩阵里核对多轴、三种配置、混合切片（例如 `x[:0, [0]]` 先切出零长度轴再走 `take`，`slice_wrap_lists` 的混合分支把 `itemsize` 写死为 8）。

## (c) 计划

- 私有矩阵（`semantic_control.py`，root、断网、一次性容器）：base、gold、`split=True` 部分修复、默认警告对照、只按示例形态特判（只看最后一轴、只看第 0 轴、只处理单个下标）、吞错（`try/except`）、`other_numel` 夹到 1 这类“合理但与 gold 不同”的实现、在 `__getitem__` 层对零大小数组短路的实现；每格记录实际 shape、dtype、chunks、警告与异常。
- 正式评分：原材料 noop、gold 与关键候选（至少 `split=True` 部分修复与一个只按示例形态特判的候选，用来确认 §4 第 2、3 步的后果）。
- 预期结论（待实测）：S1（T2c，可能兼 T2b）→ R-c 在同一测试 ID 下补非示例实例与 `split-large-chunks` 的三种取值，gold 作正对照；转第2类。若警告类候选的判定有争议，另写依据。
