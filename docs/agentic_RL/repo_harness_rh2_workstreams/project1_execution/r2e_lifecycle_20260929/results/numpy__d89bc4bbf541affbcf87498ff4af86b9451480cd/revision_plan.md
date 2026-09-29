# numpy d89bc4bb：R-c1 + R-c2 + R-b + R-c3 修订方案（区间外样本、`normed` 仍可用、末位浮点、`density=False`）

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态（第 2 轮，定稿草案）：四项修订合并为一轮，试跑验收 10 个候选全部与预期一致（试跑工具，不是正式评分）。不需要用户决定。**

- **第 1 轮**：R-c2 只放行四类弃用告警。
- **Codex 复核结论为"需小改"**（`../../codex_reviews/review_revision_numpy_d89b.md`）：四项方向都成立，但"只放行四类"是没有公开依据的新增实现约束。
- **第 2 轮只改这一处**：两个 `normed` 调用的过滤改为 `sup.filter(Warning)`。然后定点复验 gold、`REN`、`DEP`、`DEPFW`，并新增 `DEPUW` 作复验候选（用不带类别的 `warnings.warn` 弃用 `normed`）；结果都符合预期。
- **下一步**：由协调者落正式修订单（3 条）、重建材料与派生镜像、跑正式评分。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/`，`W` = `PUB/worktree`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/`。
- `HT1` / `HT2` = `PRIV/hidden_tests/test_1.py`（510 行）/ `test_2.py`（745 行），即父版本；`HT1'` / `HT2'` = 第 2 轮修订后的两个文件（544 / 783 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/numpy_d89b/`；`EV` = `runs/r2e_lifecycle_20260929/env_verify/`。

## 1. 模板与要纠正的误判

四项都在 v1 §5 模板内：三项 R-c 各补一个有公开依据的窄问题，一项 R-b 放宽一处没有依据的实现约束。

| 项 | 模板 | 要纠正的问题 | 触发反例（当前材料，协调者正式评分） | 新增或改动的键 |
| --- | --- | --- | --- | --- |
| R-c1 | R-c | T2b（§4 第 3 步）：6 个目标键里所有密度输入都没有区间外样本 | `DEG`（用含离群格的总数归一）得 1.0，78/78（`INV/ledger_DEG.jsonl:1`）；私有对照积分 0.75（`INV/pcheck_DEG_DEG.json`） | 2D、ND 各一个 `test_density_outliers` |
| R-c2 | R-c | §4 第 4 步 S1：隐藏测试把 2D/ND 的 `normed=True` 全部换成 `density=True`，不再调用 `normed` | `REN`（`normed` 改名为 `density`、删掉 `normed`）得 1.0（`INV/ledger_REN.jsonl:1`）；私有对照 `normed=True` 抛 `TypeError`（`INV/pcheck_REN_REN.json`） | 2D、ND 各一个 `test_normed_still_accepted` |
| R-b | R-b | T1：`HT2:744` 要求 ND 密度与一维结果逐位相等 | `ORD`（合理解）得 0.0，77/78，只错 `TestHistogramdd.test_density_non_uniform_1d`（`INV/ledger_ORD.jsonl:1`）；第 3 格为 0.09999999999999999，allclose 成立（`INV/pcheck_ORD_ORD.json`） | 改 `TestHistogramdd.test_density_non_uniform_1d` 的一行 |
| R-c3 | R-c | T2b（§4 第 3 步）：没有任何 `density=False` 用例 | `D1`（只要显式传了 `density` 就归一化）得 1.0，78/78（`INV/ledger_revD1.jsonl:1`） | 2D、ND 各一个 `test_density_false` |

出处：`card.md` §4、§6；`review.md` §0、§2.2、§2.5、§5，附录 A、C；主审 `analysis_before_history.md` 附录 B。

## 2. 公开依据

### R-c1：有区间外样本时，区间内积分仍为 1

**依据类别：题面明示，加 2D 文档。**

- **题面** Expected（`PUB/user_prompt.txt:22`）："normalizing the bin counts so that the integral over the range is 1"。
- **`histogram2d` 文档**（`W/numpy/lib/twodim_base.py`）：
  - `:561-562`：区间外的值 "will be considered outliers and not tallied in the histogram"；
  - `:563-565`：密度公式 `bin_count / sample_count / bin_area`；
  - `:590-592`（Notes）："the sum over bins of the product ``bin_value * bin_area`` is 1"。
- **一维先例**（`W/numpy/lib/histograms.py`）：
  - `:585-586`："Values outside the range are ignored"；
  - `:604-606`：带权时权重被归一，"the integral of the density over the range remains 1"；
  - `:607-613`：density 的定义，"normalized such that the *integral* over the range is 1"。
- **ND 带权**：`W/numpy/lib/histograms.py:851-855`，"Weights are normalized to 1 if normed is True"。
- **公开一维测试** `W/numpy/lib/tests/test_histograms.py:110-117`：有区间外样本时，带权与不带权的积分都为 1。
- **独立佐证**：没看隐藏测试的公开读者列出了 R4"只对落在区间内的样本归一"（`public_read.md` 需求表 R4）。
- **期望值从哪里来**：积分为 1 直接来自题面；逐格值 `counts / counts.sum() / area` 是上面文档给出的密度定义。`counts` 由候选自己的默认调用算出，不是 gold 的输出。

### R-c2：`normed=True` 仍返回同样的密度

**依据类别：base 文档与公开测试（行为要求）。告警类别没有公开规定，所以不限定。**

- **base 文档写明 `normed`**：`W/numpy/lib/twodim_base.py:563-565`、`W/numpy/lib/histograms.py:848-850`。
- **公开测试在用 `normed=True`**：
  - `W/numpy/lib/tests/test_twodim_base.py:207-231`（`test_asym`、`test_norm`）；
  - `W/numpy/lib/tests/test_histograms.py:548-559,599-606,711-745`。
- **提示禁止改测试文件**：`PUB/public_bundle.json:15`，"Do NOT modify the repository's test files"。
- **一维先例弃用但仍接受 `normed`**：`W/numpy/lib/histograms.py:591-599,777-811`。
- **独立佐证**：公开读者列出了 R8"`normed=True` 仍返回密度、数值不变"（`public_read.md` 需求表 R8）。
- **输入与期望都复用现成公开测试**（v1 §5 R-c 允许）：
  - 2D 版就是公开 `test_norm`（`test_twodim_base.py:223-231`）的原样输入与答案；
  - ND 版用公开 `test_normed_non_uniform_1d`（`test_histograms.py:738-745`）的输入，与一维 `histogram(..., density=True)` 比较。比较改用 allclose，理由同 R-b。
- **为什么要放行告警**：
  - 题面与公开材料都没有禁止弃用 `normed`，一维先例就是弃用。`DEP`（沿一维先例弃用 `normed`）在当前材料得 1.0（`INV/ledger_DEP.jsonl:1`），评分原本对"是否弃用"中立。
  - `W/pytest.ini:6-7` 的 `filterwarnings = error` 会把告警变成错误，不放行就会误拒弃用写法。第 1 轮的消融对照（§5.3）证实了这一点。
- **为什么放行任何类别（`sup.filter(Warning)`），而不是列举类别**：
  - 公开材料没有规定弃用必须用哪一类告警。只放行四类弃用告警，等于新增"不能用默认类别"的实现约束：不带类别的 `warnings.warn(...)` 得到 UserWarning，会被判 0。
  - 这不是假设：第 1 轮草案下，`DEPUW`（用不带类别的 `warnings.warn` 弃用 `normed`，其它与 `DEP` 相同）得 0（`trials/ctrl_draft1_DEPUW.json`）；改为 `Warning` 后得 1（`trials/rev2_DEPUW.json`），见 §5.4。
  - 公开测试的 warnings-as-error 设置也不能解释这种区别：它同样会拒绝已放行的 `DEP`、`DEPFW`。
- **放行范围与不变的要求**：
  - 过滤只包住这两个 `normed=True` 调用（`HT1':302-304`、`HT2':778-780`），同文件其它测试仍按 `filterwarnings = error` 运行；
  - 数值断言不变；
  - 告警过滤不会吞掉异常：`REN` 抛的 `TypeError` 照样让这两键失败（`trials/rev2_REN.json`）。
- **刻意不测**：
  - `normed` 与 `density` 同传：gold 抛 `TypeError`，`DEP` 告警后以 `density` 为准，本题 base 上都没有公开依据（`review.md` §2.5）；
  - 有没有告警、是哪一类。

### R-b：`test_density_non_uniform_1d` 的逐位相等

**依据类别：逐位相等只是运算顺序带来的约束，没有公开依据。**

- **被放宽的约束**："ND 的 density 结果与一维结果逐位相同"。
  - 题面、文档与公开测试都没有对新的 `density` 路径作这种承诺；
  - 公开旧测试 `test_histograms.py:738-745` 的逐位比较，测的是 base 现有的 `normed` 实现本身；
  - 公开读者在读私有材料前就把它记为"实现风险提示，不是题面约定"（`public_read.md` §2"数值"一条）。
- **`ORD` 是合理解**：先除区间内总数，再逐轴除格宽，`normed` 路径不动；主审核对它满足已列的公开要求（`analysis_before_history.md` §6），只差末位（相对误差约 1.4e-16）。

### R-c3：`density=False` 返回计数

**依据类别：公开 API 先例推知，不是题面明示。** 题面只写了 `density=True` 应返回密度（`PUB/user_prompt.txt:21-22`），没有提 `density=False`。依据来自同一模块的公开先例：

- **一维 density 文档** `W/numpy/lib/histograms.py:607-609`："If ``False``, the result will contain the number of samples in each bin."
- **公开测试** `W/numpy/lib/tests/test_histograms.py:81-83`："Test that passing False works too"，结果为计数 `[1, 2, 3, 4]`。
- **base 中 2D/ND 的 `normed` 文档**（`twodim_base.py:563-565`、`histograms.py:848-850`）："If False, returns the number of samples in each bin."
- **独立佐证**：公开读者把它列为推知需求 R7"显式传 `density=False` 时返回普通计数"（`public_read.md` 需求表 R7）。
- **期望值从哪里来**：计数由输入直接数出。
  - 2D：9 个点各占 3×3 网格中的一格，计数全为 1；
  - ND：与 `test_density_non_uniform_2d` 同一组数据（边界 `HT2:720-721`，样本 `:727-728`）。该测试 `:731-732` 用 base 的默认调用断言计数为 `[[3, 9], [1, 3]]`：noop 在这一行通过，到后面 `:735` 的 `density=True` 调用处才失败。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`、`r2e_tests/test_2.py`，即 `HT1`、`HT2`；`__init__.py` 不变。
- **草案条目**：每个文件一条 `hidden_test_text_replace`（正式修订单要求同一题同一目标只有一条），共 5 处 edit。按列表顺序应用，每处 `old` 在当时的文本里都恰好出现一次，与试跑工具的纪律相同。
- **与第 1 轮的关系**：
  - 第 1 轮修订后文件，与"主审附录 B（R-c1＋R-c2）→ R-b → 复核附录 A（R-c3）→ 复核附录 C（FutureWarning）"四段 diff 依次 `git apply` 的结果逐字节相同；
  - 第 2 轮与第 1 轮只差两处：每个 `test_normed_still_accepted` 里，四行 `sup.filter(<类别>)` 换成一行 `sup.filter(Warning)`，逐行 diff 已核对；
  - 两处测试注释"(a deprecation warning is acceptable)"没改：弃用告警仍被接受，过滤范围更宽，注释仍成立。

| 文件 | edit | 模板 | 修订后位置 | 内容 |
| --- | --- | --- | --- | --- |
| `test_1.py` | 0 | R-c3 | `HT1':233-239` | 在 `test_all_outliers`（`HT1:233`）前插入 `test_density_false` |
| `test_1.py` | 1 | R-c1＋R-c2 | `HT1':284-294`、`:296-308` | 在 `TestHistogram2d` 末尾（`HT1:274` 之后）追加 `test_density_outliers`、`test_normed_still_accepted`；两项插入点相同，所以放在同一处 edit |
| `test_2.py` | 0 | R-c3 | `HT2':738-746` | 在 `test_density_non_uniform_1d`（`HT2:738`）前插入 `test_density_false` |
| `test_2.py` | 1 | R-b | `HT2':754` | `HT2:744` 的 `assert_equal(hist, hist_dd)` 改为 `assert_allclose(hist, hist_dd)` |
| `test_2.py` | 2 | R-c1＋R-c2 | `HT2':757-771`、`:773-783` | 在文件末尾（`HT2:745` 之后）追加 `test_density_outliers`、`test_normed_still_accepted` |

**`test_1.py`，`TestHistogram2d`：**

R-c3（新键 `TestHistogram2d.test_density_false`）：

```python
    def test_density_false(self):
        # density=False returns the plain counts, as the default does
        x = array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        y = array([1, 1, 1, 2, 2, 2, 3, 3, 3])
        bins = [[1, 2, 3, 5], [1, 2, 3, 5]]
        H, xed, yed = histogram2d(x, y, bins, density=False)
        assert_array_equal(H, np.ones((3, 3)))
```

R-c1（新键 `TestHistogram2d.test_density_outliers`）：

```python
    def test_density_outliers(self):
        # Values outside the bins are not tallied; density=True still makes
        # the integral over the binned range equal to 1.
        x = array([0.5, 1.5, 1.5, 2.5, 10.0, -3.0])
        y = array([0.5, 0.5, 2.5, 2.5, 10.0, 1.0])
        bins = [[0, 1, 3], [0, 2, 3]]
        H, xed, yed = histogram2d(x, y, bins, density=True)
        area = np.outer(np.diff(xed), np.diff(yed))
        assert_array_almost_equal((H * area).sum(), 1.0)
        counts = histogram2d(x, y, bins)[0]
        assert_array_almost_equal(H, counts / counts.sum() / area)
```

R-c2（新键 `TestHistogram2d.test_normed_still_accepted`；第 2 轮）：

```python
    def test_normed_still_accepted(self):
        # The documented `normed` keyword keeps returning the density
        # (a deprecation warning is acceptable).
        x = array([1, 2, 3, 1, 2, 3, 1, 2, 3])
        y = array([1, 1, 1, 2, 2, 2, 3, 3, 3])
        bins = [[1, 2, 3, 5], [1, 2, 3, 5]]
        with np.testing.suppress_warnings() as sup:
            sup.filter(Warning)
            H = histogram2d(x, y, bins, normed=True)[0]
        answer = array([[1, 1, .5],
                        [1, 1, .5],
                        [.5, .5, .25]])/9.
        assert_array_almost_equal(H, answer, 3)
```

**`test_2.py`，`TestHistogramdd`：**

R-c3（新键 `TestHistogramdd.test_density_false`）：

```python
    def test_density_false(self):
        # density=False returns the plain counts, as the default does
        x_edges = np.array([0, 2, 8])
        y_edges = np.array([0, 6, 8])
        x = np.array([1] + [1]*3 + [7]*3 + [7]*9)
        y = np.array([7] + [1]*3 + [7]*3 + [1]*9)
        hist, edges = histogramdd((y, x), bins=(y_edges, x_edges),
                                  density=False)
        assert_equal(hist, np.array([[3, 9], [1, 3]]))
```

R-b（改动的键 `TestHistogramdd.test_density_non_uniform_1d`，只改一行）：
- 改前（`HT2:744`）：`        assert_equal(hist, hist_dd)`
- 改后（`HT2':754`）：`        assert_allclose(hist, hist_dd)`
- 下一行 `assert_equal(edges, edges_dd[0])` 不变。

R-c1（新键 `TestHistogramdd.test_density_outliers`）：

```python
    def test_density_outliers(self):
        # Values outside the bins are not tallied; density=True still makes
        # the integral over the binned region equal to 1, with and without
        # weights.
        x = np.array([0.5, 1.5, 1.5, 3.0, -1.0, 0.5, 9.0])
        y = np.array([0.5, 0.5, 2.5, 2.5, 0.5, -2.0, 9.0])
        w = np.array([1.0, 2.0, 1.0, 3.0, 4.0, 5.0, 6.0])
        bins = ([0, 1, 4], [0, 2, 3])
        area = np.outer(np.diff(bins[0]), np.diff(bins[1]))
        for weights in (None, w):
            counts, _ = histogramdd((x, y), bins=bins, weights=weights)
            hist, _ = histogramdd((x, y), bins=bins, weights=weights,
                                  density=True)
            assert_almost_equal((hist * area).sum(), 1)
            assert_allclose(hist, counts / counts.sum() / area)
```

R-c2（新键 `TestHistogramdd.test_normed_still_accepted`；第 2 轮）：

```python
    def test_normed_still_accepted(self):
        # The documented `normed` keyword keeps returning the same density
        # as `density=True` (a deprecation warning is acceptable).
        v = np.arange(10)
        bins = np.array([0, 1, 3, 6, 10])
        with suppress_warnings() as sup:
            sup.filter(Warning)
            hist_normed, edges = histogramdd((v,), (bins,), normed=True)
        hist, _ = histogram(v, bins, density=True)
        assert_allclose(hist_normed, hist)
        assert_equal(edges[0], bins)
```

**设计说明**：
- **只用两个文件已有的导入**：`HT1:6-17`、`HT2:1-10`。`test_1.py` 已从 `numpy.testing` 导入，所以 `np.testing.suppress_warnings` 可用；`Warning` 是 Python 内建名。不新增导入，不依赖仓库测试辅助代码。
- **没有随机数、定时器、文件或网络**。整套 84 键的测试段 1.4–2.4 s。
- **容差**：
  - R-c1、R-c2 的数值比较都带容差（`assert_array_almost_equal` 6 位、`assert_almost_equal` 7 位、`assert_allclose` rtol 1e-7），不再引入运算顺序陷阱；
  - R-c3 比较的是整数计数，用精确比较；
  - `assert_equal(edges[0], bins)` 精确，因为边界按传入值原样返回。
- **手算**（与试跑实测一致）：
  - R-c1 2D：区间内 4 点，计数 `[[1,0],[1,2]]`，面积 `[[2,1],[4,2]]`，积分为 1。`DEG` 用全部 6 点作分母，积分 4/6，实测 0.666667。
  - R-c1 ND：
    - 不带权计数 `[[1,0],[1,2]]`，带权 `[[1,0],[2,4]]`，面积 `[[2,1],[6,3]]`；
    - `DEG` 不带权时积分 4/7，实测 0.5714285714285714；带权时按手算为 7/22，但它在不带权分支已经失败。
  - R-c1 第二条断言还挡"积分凑成 1、但没有逐格除面积"的写法，例如 `hist / (hist * area).sum()`。
- **刻意不测**（见 §7）：2D 带权的 density、位置参数顺序、空输入或全部离群时的 density（公开读者 R12"未约定"）、`normed` 与 `density` 同传、有没有告警。

## 4. 期望映射逐键变化

- **原 78 键不变**，都是 PASSED。`TestHistogramdd.test_density_non_uniform_1d` 的断言放宽了，期望仍是 PASSED。
- **新增 6 键，都为 PASSED**：
  - `TestHistogram2d.test_density_false`（R-c3）
  - `TestHistogram2d.test_density_outliers`（R-c1）
  - `TestHistogram2d.test_normed_still_accepted`（R-c2）
  - `TestHistogramdd.test_density_false`（R-c3）
  - `TestHistogramdd.test_density_outliers`（R-c1）
  - `TestHistogramdd.test_normed_still_accepted`（R-c2）
- **合计 84 键**。完整映射见 `revision_draft.json` 的 `expected_after`，按收集顺序排列；两轮共用同一份期望。正式修订单的 expected 部分：`added` 为这 6 键，`changed`、`removed` 为空。
- **键集核对**：
  - 用 ast 从第 2 轮修订后两个文件读出的键（类名.方法名，加模块级函数名）恰为这 84 个，顺序一致、无重名；
  - 各类名互不相同，新测试名不与原 78 键撞键；
  - 每次试跑都解析出 84 键，没有 missing / extra。
- **键的性质**：
  - R-c1、R-c3 四键是目标键（noop FAILED、gold PASSED）；
  - R-c2 两键是回归键（noop 与 gold 都 PASSED），专门保护 `normed`。
- **期望从哪里来**：见 §2 各项的"期望值"一条。gold 通过是验证结果，不是依据；没有复制 gold 的输出作期望。
- **版本记录**：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT1`，510 行） | `b680bb79…` |
  | 父版本 `test_2.py`（`HT2`，745 行） | `1d485d6e…` |
  | 父版本隐藏测试树 | `b55abfbe…`，`material_revisions` 为空 |
  | 父版本 `expected_output.json`（78 键） | `f7c02eef…` |
  | **第 2 轮**修订后 `test_1.py`（`HT1'`，544 行） | `cf992ee4…` |
  | **第 2 轮**修订后 `test_2.py`（`HT2'`，783 行） | `e0b2dd5f…` |
  | **第 2 轮**试跑用 `draft_v2.json`（定稿） | `1cf7b26b…` |
  | 两轮共用的 `expected_after.json`（84 键） | `b9c1d0e0…` |
  | 第 1 轮修订后 `test_1.py` / `test_2.py`（547 / 786 行，已被取代） | `0f31279d…` / `d99e2c94…` |
  | 第 1 轮 `draft.json`（已被取代） | `a87a119e…` |
  | 第 1 轮消融用 `draft_noFW.json`（§5.3，不是修订） | `73909332…` |

  父版本四项与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:22` 一致，本题至今没有材料修订。全长哈希见 `revision_draft.json`，其中 `revisions` 就是 `draft_v2.json` 的内容。

## 5. 验收计划与试跑结果

**试跑环境**：
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑。它与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。
- 派生镜像 `sha256:ea786809c49d…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV` 下五份正式账本和 `EV/ledger_l1_{noop,gold}.jsonl:6` 的 `image_id_actual` 相同。
- 所有候选补丁都先在仓库外的 base 副本（两个文件的 blob 为 `ad721550`、`cca316e9`，与 gold 补丁的 index 行一致）上 `git apply --check` 通过。
- 试跑中，每个补丁都报 `RH2_APPLY_RC=0`、两个文件已应用；修订草案报 `RH2_TRIAL_EDITS_APPLIED=2`。
- 两轮共 18 次试跑，同一时间最多 2 个：
  - 第 1 轮 12 次：当前材料对照 2 次、验收 9 次、消融 1 次；
  - 第 2 轮 6 次：定点复验 5 次、对照 1 次。
- 单次墙钟 20–43 s，其中测试段 1.4–2.4 s。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 本轮试跑（当前材料） | 协调者正式评分（同一镜像） |
| --- | --- | --- |
| noop | 0：72/78，恰为 6 个原目标键 FAILED（`trials/env_noop_current.json`） | 0，72/78（`EV/ledger_l1_noop.jsonl:6`） |
| gold | 1：78/78（`trials/env_gold_current.json`） | 1，78/78（`EV/ledger_l1_gold.jsonl:6`） |
| `DEG` | — | **1.0**，78/78（`INV/ledger_DEG.jsonl:1`） |
| `REN` | — | **1.0**，78/78（`INV/ledger_REN.jsonl:1`） |
| `ORD` | — | **0.0**，77/78（`INV/ledger_ORD.jsonl:1`） |
| `DEP` | — | 1.0，78/78（`INV/ledger_DEP.jsonl:1`） |
| `D1` | — | **1.0**，78/78（`INV/ledger_revD1.jsonl:1`） |
| `C1`、`DEPFW`、`DEPUW` | 未跑。静态判断都得 1：隐藏测试从不向 2D/ND 传 `normed`；`C1` 在所有被断言的输入上与 gold 逐位相同（`review.md` §2.1）；`DEPFW`、`DEPUW` 与 `DEP` 行为相同 | — |

### 5.2 修订草案下的验收

"草案"一列：第 2 轮 = `draft_v2.json`（定稿）；第 1 轮 = `draft.json`，与第 2 轮只差 R-c2 的过滤块，沿用理由见 §5.5。"失败处"取自结果里的 `log_tail`，行号按各自草案的修订后文件。

| 候选 | 补丁 | 角色 | 应得 | 应不符的键 | 草案 | 试跑结果 | 失败处 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 第 2 轮 | 1，84/84（`trials/rev2_gold.json`；第 1 轮 `rev_gold.json` 也是 84/84） | — | 1 |
| noop | 无 | 负对照 | 0 | 6 个原目标键，加 2 个 `test_density_outliers`、2 个 `test_density_false` | 第 1 轮 | 0，恰为这 10 键；两个 `test_normed_still_accepted` 为 PASSED（`trials/rev_noop.json`） | 新的 4 键都是 `TypeError`：ND `test_density_outliers` 报 `histogramdd() got an unexpected keyword argument 'density'`（`:769`），ND `test_density_false` 在 `:745` 报 `TypeError`；2D 两键的详细段不在截取的日志尾部（结果文件只留最后 8000 字符），short summary 为 `TypeError` | 0 |
| `DEG` | `cands/numpy_d89b_DEG.patch` | R-c1 的触发反例 | 0 | 两个 `test_density_outliers` | 第 1 轮 | 0，恰为这 2 键（`trials/rev_DEG.json`） | `test_1.py:292`：积分 0.666667，应为 1.0；`test_2.py:770`：积分 0.5714285714285714，应为 1 | **1** |
| `REN` | `cands/numpy_d89b_REN.patch` | R-c2 的触发反例 | 0 | 两个 `test_normed_still_accepted` | 第 2 轮 | 0，恰为这 2 键（`trials/rev2_REN.json`；第 1 轮 `rev_REN.json` 相同） | `HT1':304`：`TypeError: histogram2d() got an unexpected keyword argument 'normed'`；`HT2':780` 同型 | **1** |
| `ORD` | `cands/numpy_d89b_ORD.patch` | R-b 的触发反例（合理解） | 1 | — | 第 1 轮 | 1，84/84（`trials/rev_ORD.json`） | — | **0** |
| `DEP` | `cands/numpy_d89b_DEP.patch` | 合理解：弃用 `normed`（DeprecationWarning） | 1 | — | 第 2 轮 | 1，84/84（`trials/rev2_DEP.json`；第 1 轮也是 1） | — | 1 |
| `D1` | `cands/numpy_d89b_revD1.patch` | R-c3 的触发反例 | 0 | 两个 `test_density_false` | 第 1 轮 | 0，恰为这 2 键（`trials/rev_D1.json`） | `test_1.py:239`：得到 1/9、1/18、1/36 等密度，应为全 1；`test_2.py:746`：得到全 0.015625，应为 `[[3,9],[1,3]]` | **1** |
| `C1` | `cands/numpy_d89b_C1.patch` | 合理解（可选）：`density` 为 None 时取 `normed`，静默别名 | 1 | — | 第 1 轮 | 1，84/84（`trials/rev_C1.json`） | — | 未跑，静态为 1 |
| `DEPFW` | `cands/numpy_d89b_DEPFW.patch` | 合理解（可选）：`DEP` 的两处告警换成 FutureWarning | 1 | — | 第 2 轮 | 1，84/84（`trials/rev2_DEPFW.json`；第 1 轮也是 1） | — | 未跑，静态为 1 |
| `DEPUW` | `cands/numpy_d89b_DEPUW.patch`（第 2 轮新写） | 合理解：用不带类别的 `warnings.warn`（即 UserWarning）弃用 `normed`，其它与 `DEP` 相同；检验放行 `Warning` 生效 | 1 | — | 第 2 轮 | 1，84/84（`trials/rev2_DEPUW.json`） | — | 未跑，静态为 1 |

**三个新写的补丁**：都在仓库外的 base 副本上改好后用 `git diff` 生成，`git apply --check` 通过。
- `C1`（sha256 `f36d2705…`）：按复核初判 §6 的描述写成。
  - `histogramdd` 签名末尾加 `density=None`；
  - 归一化前加 `if density is None: density = normed`，`if normed:` 改为 `if density:`，归一化代码不动；
  - `histogram2d` 签名末尾加 `density=None`，转发 `density=density`。
- `DEPFW`（sha256 `f1a66778…`）：在 `DEP` 补丁上只把两处 `DeprecationWarning` 换成 `FutureWarning`。
- `DEPUW`（sha256 `cfe08fec…`）：在 `DEP` 补丁上删去两处 `warnings.warn` 的类别参数，只留消息和 `stacklevel=2`。
- 后两者与 `DEP` 的 diff 除上述差别外，只差 git 生成的 index 行和 hunk 头部的函数名。

### 5.3 第 1 轮消融对照：需要放行告警（不是修订，不进 acceptance）

- **做法**：第 1 轮草案去掉两处 `sup.filter(FutureWarning)`（`draft_noFW.json`），再跑 `DEPFW`。
- **结果**：得 0，恰在两个 `test_normed_still_accepted` 失败。告警在候选代码的 `numpy/lib/histograms.py:976` 处被当作异常抛出：`FutureWarning: The normed argument is deprecated, use density instead.`（`trials/ablation_noFW_DEPFW.json`）。
- **结论**：
  - 评分入口 `W/run_tests.sh`（与 `PRIV/run_tests.sh` 相同，sha256 `8285765f…`）里的 `-W ignore` 与 `PYTHONWARNINGS` 挡不住，pytest 在每个测试里套用 `W/pytest.ini:6-7` 的 `filterwarnings = error`；
  - 所以新断言必须放行告警。它只说明"需要过滤"，不说明"必须只放行某几类"（Codex 复核 §3 同意这一读法）。

### 5.4 第 2 轮对照：四类名单会误拒 UserWarning 写法（不进 acceptance）

- 同一个 `DEPUW` 补丁，在第 1 轮草案（四类名单）下得 0。它恰在两个 `test_normed_still_accepted` 失败，报 `UserWarning: The normed argument is deprecated, use density instead.`（`numpy/lib/histograms.py:976`，`trials/ctrl_draft1_DEPUW.json`）。
- 在第 2 轮草案（`sup.filter(Warning)`）下得 1（`trials/rev2_DEPUW.json`）。
- 这就是第 2 轮要纠正的误拒，前后都有执行证据；与 Codex 用本题原版 `suppress_warnings` 做的内存探针结论一致。

### 5.5 为什么 noop、`DEG`、`D1`、`ORD`、`C1` 不必在第 2 轮重跑

- **文本上**：第 2 轮只改两个 `test_normed_still_accepted` 的过滤块，其余 82 个测试的文本与第 1 轮逐字节相同（逐行 diff 只有这 2×4 行删、2×1 行增）。
- **行为上**：
  - 这五个候选的补丁都不含任何 `warnings.warn`（逐个 grep 过）；base 中 `histogramdd`（`W/numpy/lib/histograms.py:815-976`）与 `histogram2d`（`W/numpy/lib/twodim_base.py:533-656`）也不发告警。所以它们在 `normed=True` 调用里根本不经过告警路径，过滤写成哪样都不影响结果。
  - 另外，`Warning` 是原四类的共同基类，新过滤放行的范围只增不减。第 1 轮能通过这两键的候选，不会因为这处改动转为失败。
- **结果上**：
  - 第 1 轮中这五个候选都通过了两个 `test_normed_still_accepted`；
  - 它们失败的键（noop 10 键、`DEG` 两个离群键、`D1` 两个 `density=False` 键）都在未改动的测试里，失败原因是 `TypeError` 或数值断言，与告警无关；
  - 所以第 1 轮的试跑结果原样适用于第 2 轮草案。正式评分时它们会在第 2 轮材料上重跑。

### 5.6 判读

- **正对照 1、noop 0**：成立。gold 本身满足公开要求，不需要替代正对照：
  - devcheck 私有 gold 对照里两条复现命令通过、积分为 1.0（`old_findings_delta.md` §2；`review.md` §3 第 7 行）；
  - `normed` 是静默别名（`PRIV/gold.patch` 的 `histogramdd` 别名处理段）；`density=False` 返回计数（R-c3 两键通过）；
  - 四项新断言 gold 全部通过（84/84）。
- **误判已纠正**：
  - `DEG`、`REN`、`D1` 在当前材料正式评分都是 1.0，修订后都是 0；
  - 各自只在针对它的两个新键失败，失败原因正是对应的违例：积分不为 1、`normed` 被删、`density=False` 被归一化；
  - `ORD` 从 0 变为 1；
  - 第 1 轮草案自身会误拒的 `DEPUW`，在第 2 轮得 1。
- **已知相关的错误候选仍为 0**：`DEG`、`REN`、`D1`。`D2` 与 `DEG` 等价，`D3` 与 `REN` 相同（`review.md` §2.1），不另跑。
- **没有误拒**：`ORD`、`DEP`、`C1`、`DEPFW`、`DEPUW` 都得 1。
- **旧键不受影响**：所有修订版试跑中，旧 78 键里只有 noop 的 6 个原目标键失败，与当前材料相同；其余候选的 `status_diff` 只含新键。
- **仍待正式评分**：以上都是试跑层面的结论，正式评分待协调者跑。

## 6. R-b 保留了哪些有依据的行为

- **同一键内保留的**：
  - `assert_allclose(hist, hist_dd)`（rtol 1e-7）仍要求 ND 的 density 与一维 `histogram(..., density=True)` 数值一致。这是题面"probability density function"加一维 density 文档（`histograms.py:607-613`）给出的语义。
  - 它仍能挡住所列的错误候选：
    - 不除格宽得 `[0.1, 0.2, 0.3, 0.4]`；
    - 不除总数得 `[1, 1, 1, 1]`；
    - 不归一化得 `[1, 2, 3, 4]`；
    - 这些与 `[0.1]*4` 都差得远，而 `ORD` 的相对误差约 1.4e-16。
  - `assert_equal(edges, edges_dd[0])` 保持精确。
- **其它精确断言不动，也不需要动**：
  - 涉及三处：`HT2:551` 的 `np.all(H == answer / 12.)`；`HT2:736` 的 `assert_equal(hist, 1 / (8*8))`；`HT2:606` 权重整体放大 2 倍前后逐位相等。
  - 我用本机纯 Python 算术（不导入项目代码）核对了 7 种合理运算顺序：
    - 先除格宽再除总数；
    - 先除总数再除格宽；
    - `c/(s*vol)`；
    - `c/vol/s`；
    - 先乘格宽倒数，再乘总数倒数；
    - `c*(1/(s*vol))`；
    - 先乘总数倒数，再乘格宽倒数。
  - 前两处在全部 7 种顺序下都逐位相等。权重放大 2 倍是 2 的幂缩放，任何顺序下都精确。
  - 只有 `HT2:744` 在"先除总数再除格宽"下差 1 ulp，这正是 R-b 改的那一处。主审附录 C、复核 §2.4 的结论相同。
  - 修订版试跑中 `ORD` 84/84，是它在另外三处精确断言上都通过的执行证据。

## 7. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**：
- **两个函数都接受 `density=True` 并返回密度**：原 6 个目标键。2D 为 `test_asym`、`test_density`；ND 为 `test_simple`、`test_weights`、`test_density_non_uniform_2d`、`test_density_non_uniform_1d`（R-b 后为容差比较）。
- **区间外样本不计入，区间内积分为 1**：两个 `test_density_outliers`，ND 版覆盖带权与不带权。
- **密度等于计数 / 区间内总数 / 格面积**：`test_density_outliers` 的第二条断言；原 `test_density`、`test_density_non_uniform_2d`。
- **`density=False` 返回计数**：两个 `test_density_false`。默认调用返回计数，由原回归键（2D `test_simple` 等）保护。
- **`normed=True` 仍返回同样的密度**：两个 `test_normed_still_accepted`，允许在这次调用里发出任何告警。
- **权重整体缩放不改变密度**：原 `test_weights`，精确比较。
- **一维 `histogram` 行为不变**：30 个回归键，其中 `TestHistogram.test_normed` 断言一维 `normed=True` 恰好发出 1 个 VisibleDeprecationWarning。

**仍未覆盖，维持登记**（T3 或中性，都没有已有候选命中）：
- **2D 带权的 density**：2D 的密度用例都不带权；ND 带权由 R-c1 覆盖。
- **原位置参数顺序**：公开读者 R9，罕见用法。
- **空输入或全部离群时的 density**：公开读者 R12"未约定"。
- **`normed` 与 `density` 同传**：刻意中立。
- **`normed=True` 调用里的告警**：R-c2 对告警有无与类别都中立。
  - 若某个候选在 `normed` 路径上发出非弃用告警（例如 RuntimeWarning），但数值正确，这两键仍会通过。
  - 公开材料对这里是否告警没有要求，数值断言照旧生效，所以不另加约束。
- **X1**：照旧登记（`card.md` §4 第 5 条）。新测试是新写的：按 3 个新测试名和 2 组新输入字面值 grep 了 v3 的 7 个 numpy 公开工作树，没有命中。

## 8. 边界与交接

- **只做 R-c 与 R-b**：
  - 不改题面，不删键，没有放宽任何有依据的断言；R-b 只放宽一处末位浮点约束，见 §6；
  - 没有复制 gold 输出作期望；
  - 四项都有公开依据，不涉及 P5 或其它模板外事项，**不需要用户决定**。
- **没有越界**：
  - 没写 `s2_r2e` 下的正式修订单与 pins，没改生产代码；
  - 远端只在 `/work/r2e/trials/lc_numpy_d89b/d89bc4bb/` 上传补丁与草案并试跑（两轮共 18 次）。
- **本目录新增的文件**：
  - `revision_plan.md`、`revision_draft.json`（第 2 轮定稿）；
  - `trials/`：第 1 轮 12 份、第 2 轮 6 份结果；
  - `cands/numpy_d89b_C1.patch`、`cands/numpy_d89b_DEPFW.patch`、`cands/numpy_d89b_DEPUW.patch`；
  - 其余原件未改。
- **协调者待办**：
  1. **按需送 Codex 复核第 2 轮的小改**：只改了 R-c2 过滤块，另补了 R-c3 依据类别与 §6 措辞。
  2. **落正式修订单**：
     - `test_1.py`、`test_2.py` 各一条 `hidden_test_text_replace`，用 `revision_draft.json` 的 `revisions` 原样（即 `draft_v2.json`），分别 2 处与 3 处 edit；
     - 另加一条 `expected_file_replace`，`added` 为 6 键。
  3. **重建材料与派生镜像**，隐藏测试树摘要会变。
  4. **正式评分**：至少跑 gold、noop、`DEG`、`REN`、`D1`、`ORD`、`DEP`；`C1`、`DEPFW`、`DEPUW` 可选。按 §5.2 判读，并核对补丁确已应用、84 键都已执行、日志完整。
  5. **重判 v1 用途**：按 `card.md` §1、`review.md` §6 重判。训练候选要的正面证据届时齐全：核心断言、当前版本 noop 0 / gold 1、第 2、3 步结果。留出评测仍受 D3 按仓库划分、X1、"标明版本的自建评测"三项限制。
