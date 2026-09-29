# numpy__d89bc4bb 独立复核初判（第一步）

独立复核者（新上下文，未参与主审）· 2026-09-29 · 口径：统一标准 v1，加主审卡"R2E 的评分口径 / 材料 / 第二批补充规则 / 单题闭环试行补充"四节。本文件写于读任何公开读者产物、主审产物与历史材料之前。

路径缩写（均相对仓库根）：`PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`；`PRV` = `runs/r2e_static_prep_20260924/v3/private/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`；`WT` = `PUB/worktree`。

## 0. 初判摘要

- **当前材料上评分依据成立。** noop 得 0（72/78，6 键不符）、gold 得 1（78/78），各有 2 次运行（`PRV/run_refs.json` L10–100 的 current 行）；M3 独立 runner 在来源镜像上 gold 也是 2/2。账本、日志、`expected_output.json`、隐藏测试、`gold.patch`、`run_tests.sh` 的 sha256 全部吻合（附录 A）。本题没有材料修订（`PRV/revisions.json` = `[]`）。
- **核心要求有直接断言，且不是只用题面示例**（v1 §4 第 1、2 步不命中）。`histogram2d` 与 `histogramdd` 的 `density=True` 都有断言：覆盖非均匀 bin、3 维、权重，并与 1-D `histogram` 交叉比对；测试数据都不是题面示例。
- **gold 修改位置周围有三处公开行为完全没测。** 以下都是静态推断，我预测它们会得 1，要等协调者跑正式评分：
  1. **`density=False` 应返回计数。** 隐藏测试从没给这两个函数传过 `density=False`。退化候选 D1（只要显式传了 density 就归一化）预测得 1。实跑得 1 即为 S1（T2b）。
  2. **题面写明"integral over the range is 1"。** 但所有 density 断言的样本都落在 bin 内，没有越界样本。错误候选 D2（分母用全部样本数，而不是范围内的计数）预测得 1。这属于同一核心要求的另一实例，按第 4 步判 S1。
  3. **`normed` 旧参数兼容。** 隐藏测试把 dd/2d 的全部 `normed=True` 用例都改成了 `density=True`，没有任何键再覆盖 `normed`。回归候选 D3（把 `normed` 直接改名为 `density`）预测得 1。它破坏了有文档、常用的公开行为，按第 4 步判 S1。
- **没发现合理解被误拒。** 期望映射全是 PASSED，没有非 PASSED 键；合理替代解 C1 预测得 1。只有一处低风险 T1：`test_density_non_uniform_1d` 用精确相等，换一种等价的运算顺序会差 1 ulp。但公开旧测试里已有同样的精确断言，所以这条要求有公开依据。
- **错误回归、材料错配：未发现。开发缺口：** 本次没提供 devcheck，actor 侧未核。静态推断公开测试可能有与修复无关的 ERROR 噪声（§9 第 6 条）。
- **题目关系（X1）：** 本题 gold 逐字出现在同仓 numpy `43e333e2` 的公开工作树里（我打开了该题公开包核对）。
- **暂定处置：** `needs_review`，严重度 conditional，倾向 S1，等 D1–D3 的正式评分。命中后按 §11 的 R-c1–R-c3 修订。唯一最值得先做的：用正式评分跑 D1、D2、D3 与 C1。

## 1. 实际读取范围

- 方法：两张角色卡（复核卡全文；主审卡按指示只读四节）、八方面协议、R2E 环境卡、记录模板、统一标准 v1。
- 公开包：`PUB/user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（摘要字段）。
- 工作树源码：`WT/numpy/lib/histograms.py` L555–977、`WT/numpy/lib/twodim_base.py` L525–665、`WT/pytest.ini`、`WT/run_tests.sh`、`WT/numpy/conftest.py`、`WT/numpy/_globals.py` L45。
- 工作树文档与测试：`WT/doc/release/1.15.0-notes.rst`（grep histogram/normed 段）；`WT/numpy/lib/tests/test_histograms.py`、`test_twodim_base.py`（与隐藏测试逐行 diff，并看了引用行）。
- 私有包：`PRV/gold.patch`、`hidden_tests/{__init__,test_1,test_2}.py`（全文）、`expected_output.json`、`run_tests.sh`、`revisions.json`、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`。
- 运行原件：`run_refs.json` 里全部 4 条 current 行的账本行（line 22），以及它们的 `.eval.log` 全文或规范化 diff；`independent_reference` 的 M3 两份日志与账本 L40、L87。
- 跨题线索：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`、`cross_task_test_scan.json` 中涉及本题的条目。同仓公开包只看了 numpy `43e333e2` 的公开工作树（grep 定位）与 6 道同仓题的 `user_prompt.txt` 首行和标题。
- 自己做的计算：scratchpad 里一个纯 Python 浮点演算脚本（附录 C），没有运行项目代码。
- 没读：`OUTPUT_DIR` 里的其它文件、任何 `history/`、审查目录、本批 README / `board.json` / `assignments.json`、其它题的私有包、devcheck（没有提供）。

## 2. 公开目标（只据公开包）

- 题面（`PUB/user_prompt.txt` L4–31）：`histogram2d` 与 `histogramdd` 要接受 `density`。`density=True` 返回概率密度，原文是"normalizing the bin counts so that the integral over the range is 1"（L22）。现在的报错是 `TypeError: histogram2d() got an unexpected keyword argument 'density'`（L27），两个函数都受影响（L31）。
- base 里能查到的相关公开规格：
  - 1-D `np.histogram` 的 `density`：False 返回计数，True 返回密度且积分为 1，并覆盖 `normed`（`WT/numpy/lib/histograms.py` L607–615）。实现先除 bin 宽、再除计数总和（L787–789）；两者都给时 density 优先，并发 DeprecationWarning（L777–785）。
  - `histogramdd` / `histogram2d` 的 `normed` 有文档（histograms.py L848–850；twodim_base.py L563–565、L588–592）。权重在 normed 时归一化（histograms.py L851–855；twodim_base.py L566–570）。range 外的样本是 outlier，不计入（twodim_base.py L558–562）。
  - 发布说明写明 `np.histogram` 的 `normed` 从 1.15 起发 DeprecationWarning，但仍接受（`WT/doc/release/1.15.0-notes.rst` L79–80）。
  - 公开旧测试：dd/2d 用 `normed=True`（`WT/numpy/lib/tests/test_twodim_base.py` L211、L227；`test_histograms.py` L550、L556、L602、L605、L735、L743）；1-D `density=False` 返回计数（test_histograms.py L81–83）；1-D 有越界样本时 density 积分仍为 1（L110–112）。
  - `WT/pytest.ini` L6–7 设了 `filterwarnings = error`：测试内的任何警告都会变成错误。
- 合理路线：两个函数都加 `density` 并复用已有的归一化代码；`normed` 保留为别名（或弃用但仍接受）。两者同时给时是报错还是 density 优先，公开材料里两种都有先例。

## 3. 隐藏测试与目标键

- **隐藏测试的来源。** 我用 `diff` 与公开 base 逐行核过：
  - `test_1.py` = base `test_twodim_base.py`，把 L211、L227 的 `normed=True` 改成 `density=True`，并把 `test_norm` 改名为 `test_density`。
  - `test_2.py` = base `test_histograms.py`，把 dd 的 6 处 `normed=True` 改成 `density=True`，把 `test_normed_non_uniform_{1d,2d}` 改名为 `test_density_*`。另外把 `TestHistogram` 的 nose 式 `setup/teardown` 改成了 `setup_method/teardown_method`（L15、L18，方法体都是 `pass`）。
  - 除此之外逐字相同。
- **目标键 6 个**（noop 为 FAILED、gold 为 PASSED；两次 noop 相同）：

| 目标键 | 调用与输入 | 决定性断言 | 测的公开要求 |
| --- | --- | --- | --- |
| `TestHistogram2d.test_asym` | test_1.py L208–211：8 个点，bins (6,5)，range [[0,6],[0,5]]，`density=True` | L219 `assert_array_almost_equal(H, answer/8., 3)`；L220–221 核边 | 2d 接受 density。bin 面积为 1，所以这里 PDF 等于 PMF，本键区分不了两者 |
| `TestHistogram2d.test_density` | L224–227：9 个点，非均匀 bin [1,2,3,5] | L228–231 `answer/9`（含 .5、.25 两档） | 2d 在非均匀 bin 下是 PDF，不是 PMF |
| `TestHistogramdd.test_simple` | test_2.py L549–556：3 维，bin 体积 2；range 版 bins (2,3,4) | L551 `np.all(H == answer / 12.)`（精确）；L559 `answer / 6.`（4 位） | dd 的 3 维 PDF |
| `TestHistogramdd.test_weights` | L600–606：随机 100×2 数据，权重全为 2 | L606 `assert_array_equal(w_hist, n_hist)` | 均匀权重下密度不变。这个断言区分不了"density 下忽略权重" |
| `TestHistogramdd.test_density_non_uniform_2d` | L720–735：面积不均，各格计数与面积成正比 | L736 `assert_equal(hist, 1 / (8*8))`（精确） | dd 在非均匀 bin 下是 PDF |
| `TestHistogramdd.test_density_non_uniform_1d` | L740–743 | L744 `assert_equal(hist, hist_dd)`（与 1-D `histogram(density=True)` 精确相等）；L745 核边 | dd 的 1 维结果与 `histogram` 一致 |

- **回归键 72 个，测试体我全读了。** 与本修复相关的有：
  - `TestHistogram2d` 其余 4 键：默认计数、全 outlier、空输入、bin 组合。
  - `TestHistogramdd` 其余 11 键：形状、空输入、bins 报错、inf 边、最右边、相等边、dtype、大整数。
  - 1-D `histogram` 的 `TestHistogram` 21 键与 `TestHistogramOptimBinNums` 9 键，保护 1-D 函数不被改坏。其中 `test_normed`（L42–64）要求 1-D `normed=True` 恰好发 1 个 VisibleDeprecationWarning；`test_f32_rounding`（L137–142）会走 `np.histogram2d` 的默认路径。
  - `TestEye`、`TestDiag`、`Flip*`、`Tri`、`tril/triu`、`Vander` 等 21 键与修改无关，只是同文件的回归。
- **键数与撞键。** test_1 有 33 键、test_2 有 45 键，合计 78，与期望一致。各类名互不相同，模块级函数只在 test_1 里，**没有撞键**。

## 4. 需求—断言双向表

| 公开要求 / 合理旧行为 | 公开依据 | 键 / 断言 | 覆盖 |
| --- | --- | --- | --- |
| 2d 接受 `density=True` 不报错 | 题面 L4–7、L27 | test_asym、test_density | 覆盖 |
| 2d `density=True` 是 PDF（非均匀 bin） | 题面 L22；histogram 文档 L610–613 | test_density L228–231 | 覆盖 |
| dd 接受 `density=True`，结果是 PDF | 题面 L31 | dd 的 4 个目标键 | 覆盖（3 维、非均匀、1 维交叉比对） |
| 不传 density 时返回计数 | 旧行为；histograms.py L848–849 | 2d `test_simple` 等；dd `test_simple` L542–546 | 覆盖 |
| `density=False` 返回计数 | histogram 文档 L607–609；公开测试 L81–83；题面说的是"density parameter" | 无 | **缺失**（D1） |
| 积分在 range 上为 1（越界样本不计入） | 题面 L22；twodim_base.py L561–562；histogram 文档 L610–611；公开 1-D 测试 L110–112 | 无：所有 density 调用的样本都在 bin 内 | **缺失**（D2） |
| `normed=True` 仍可用（作别名，或弃用但仍接受） | histograms.py L848–850；twodim_base.py L563–565；公开测试多处；发布说明 L79–80 | 无：隐藏测试里的 `normed` 只出现在 1-D `test_normed` | **缺失**（D3） |
| 非均匀权重在 density 下正确归一化 | histograms.py L853；twodim_base.py L568 | 只有均匀权重（`test_weights`） | 部分（T3） |
| 两者同时给时的行为 | 公开材料没规定：`histogram` 是 density 优先加警告，gold 是 TypeError | 无 | 不应测（两种都有依据） |
| 位置参数顺序（weights 仍是第 5 个） | 公开签名 | 无 | 缺失（T3，罕见用法） |
| 1-D `histogram` 行为不变 | 旧行为 | TestHistogram 21 键 | 覆盖 |

反查：6 个目标键的关键断言都能追到题面或公开文档。L744 精确相等断言的依据，是公开旧测试 `test_normed_non_uniform_1d` 里同样的精确断言（base test_histograms.py L738–745）。

## 5. v1 §4 五步

1. **核心要求有没有直接断言：** 有（6 个目标键），不命中。
2. **是否只用题面示例的字面值：** 否。题面示例是 x=[1..5]、y=[5..1]、bins=5；测试用了别的数据、非均匀 bin、3 维与权重。不命中。
3. **退化探测：** D1 预测得 1，待实跑。得 1 即为 S1（T2b）。
4. **已有或已构造的候选：** D2 在越界样本上违反同一核心要求"integral over the range is 1"；D3 破坏有文档的 `normed`。两者都预测得 1，待实跑，得 1 即为 S1。
5. 暂不适用。

结论：conditional，缺的证据是正式评分。

## 6. 候选（写成可改成补丁的描述；预测均为静态推断）

实跑时请核对三点：补丁确实交付（账本 `projection.included_paths` 含两个文件）、6 个目标键确实执行、78 个键没有 missing 或 unexpected。

### C1：合理替代解（用来查误拒）

- `numpy/lib/histograms.py::histogramdd`：
  - 签名改为 `histogramdd(sample, bins=10, range=None, normed=False, weights=None, density=None)`。
  - 在 L964 注释"Normalize if normed is True"之前加 `if density is None: density = normed`，不发警告。这仿照 `histogram` 文档里的"Overrides the normed keyword"。
  - L965 的 `if normed:` 改为 `if density:`，归一化代码不动。
- `numpy/lib/twodim_base.py::histogram2d`：签名末尾加 `density=None`，L655 改为 `histogramdd([x, y], bins, range, normed, weights, density=density)`。
- 预期：1。

### D1：退化候选（第 3 步；与输入无关的固定结果）

- 改法：`histogramdd` 签名末尾加 `density=None`，L965 改为 `if normed or density is not None:`。也就是只要显式传了 density，不论 True 还是 False 都归一化。`histogram2d` 签名末尾加 `density=None`，并转发 `density=density`。
- 违反的公开要求：`density=False` 应返回计数（histogram 文档 L607–609；公开测试 L81–83）。
- 可看出的输入：`np.histogram2d([1, 2, 3], [1, 2, 3], bins=2, density=False)[0]` 应为 `[[1., 0.], [0., 2.]]`，D1 给出 `[[1/3, 0], [0, 2/3]]`。
- 预期：1。隐藏测试从不给 dd/2d 传 `density=False`，所有 density 调用见 test_1.py L211、L227 与 test_2.py L550、L556、L602、L605、L735、L743。

### D2：错误实现（第 4 步；分母用错对象）

- 改法：
  - `histogramdd` 签名末尾加 `density=None`。
  - 在 L964 之前加一个 density 分支 `if density:`：按 base 的顺序逐维除以 `dedges[i]`，最后除以 `total = N if weights is None else weights.sum()`。这里的 total 是全部样本，包括 range 或 bins 之外的。
  - `elif normed:` 分支保留 base 代码。
  - `histogram2d` 的转发同 C1。
- 违反的公开要求：题面"integral over the range is 1"，以及 twodim_base.py L561–562 的"outliers ... not tallied"。
- 可看出的输入：`H, xe, ye = np.histogram2d([0.5, 1.5, 1.5, 9.], [0.5, 0.5, 1.5, 9.], bins=2, range=[[0, 2], [0, 2]], density=True)`。`(H * np.outer(np.diff(xe), np.diff(ye))).sum()` 应为 1，D2 给出 0.75。
- 预期：1。所有 density 调用的样本都在 bin 内：test_1.py L208–211、L224–227；test_2.py L540–556、L600–606（默认 range 取数据极值）、L727–735、L740–743。权重全为 2 时 `weights.sum()` 等于 `hist.sum()`，所以 `test_weights` 也能过。

### D3：回归候选（第 4 步；删掉旧参数）

- 改法：两个函数签名里把 `normed=False` 直接改名为 `density=False`，位置不变。`histogramdd` 的 L965 改为 `if density:`，`histogram2d` 的 L655 转发 `density`。
- 违反的公开行为：
  - `normed` 是有文档的公开参数（histograms.py L848–850；twodim_base.py L563–565）。
  - 公开旧测试依赖它。
  - `histogram` 的先例是弃用但仍接受（L591–599；发布说明 L79–80）。
- 可看出的输入：`np.histogram2d([1, 2, 3], [1, 2, 3], bins=2, normed=True)` 在 base 上返回密度，D3 会报 `TypeError`。公开测试 `numpy/lib/tests/test_twodim_base.py::TestHistogram2d::test_asym` 也会失败。
- 预期：1。隐藏测试里的 `normed` 只出现在 1-D 的 `TestHistogram.test_normed`（test_2.py L42–64）。

## 7. R2E 专项

**(a) 非 PASSED 期望键。** 78 个期望键全是 PASSED，没有非 PASSED 键。更完整的修复（例如给 `normed` 加弃用警告，或两者同时给时报错）碰不到任何键，不会被翻转判 0。

但要注意 `WT/pytest.ini` 的 L6–7 `filterwarnings = error` 在评分时生效（noop 日志 L18 显示 `configfile: pytest.ini`）。例如某个候选：`histogram2d` 保留默认 `normed=False`，并把它连同 `density` 一起转发；`histogramdd` 仿照 `histogram`，在两者都非 None 时发 DeprecationWarning。这样即使调用方只传了 `density`，也会发警告，2d 的两个目标键会因警告变成错误而失败。

这种候选对从没传过 `normed` 的用户发出误导性的弃用警告，而仓库自己约定警告即错误，所以拒绝它有公开依据，不算误拒。但分析真实候选时要读日志，分清是"警告变错误"还是"数值错误"。

**(b) 题面报错是否出现在 noop 目标键。** 出现了：`TypeError: histogram2d() got an unexpected keyword argument 'density'`（noop 日志 L35、L51）；dd 的报错同型（L74、L109、L159、L183）。

**(c) 题面是否泄漏修法。** 没有。题面只有用法示例与期望语义，没有实现，也没有别名策略。

**(d) 测试支撑、搬迁伪影与撞键。**
- 隐藏测试只导入 `numpy`、`numpy.testing` 与 `numpy.lib.histograms`（test_1.py L6–17；test_2.py L1–10），不依赖仓库测试模块里的 helper。
- 搬离 `numpy/lib/tests/` 后失去了 `numpy/conftest.py`。它只做 FPU 模式检查和 doctest 命名空间（`WT/numpy/conftest.py` L39–62），没有影响。
- `setup→setup_method` 是无害的搬迁改写（两个方法都是 `pass`）。没有撞键。
- 通用面：评分时不重置 `/testbed/pytest.ini`、根目录 conftest 与 `numpy/testing`，候选可以借此影响判分。这属于 A 线的通用链路（E3），账本已有 `candidate_touched_conftest_or_fixture` / `candidate_test_like_paths` 字段，本题没有特例。

**(e) 时间、随机与资源敏感。**
- 多个键用了未设种子的 `np.random.rand`（例如 test_2.py L145、L580、L594、L600；test_1.py L234），但断言都是对任意数据成立的性质。
- `test_weights` 的精确相等靠"权重为 2 时是 2 的幂缩放"来保证。
- 两次 noop 的随机数据不同，键结果却相同（附录 B）；gold 在 RH2 上 2 次、M3 上 2 次都是 78/78。
- 没见到时间或资源敏感的键（测试约 1 秒）。

**(f) 材料修订。** 本题没有，不适用。

## 8. gold 检查

- **是否修到原例：** 静态看修到了。`histogram2d` 多了 `density` 参数并按位置转发，`histogramdd` 的 `if density:` 走原来的归一化（gold.patch L61–63、L88–89、L36–49）。原例本身没有实跑。
- **旧行为：**
  - `normed` 保留为别名（L38–45）。默认值从 False 改为 None，但语义不变。
  - 两者同时给时一律 `TypeError`（L46），包括 `normed=False, density=True`。这与 `histogram` 的"density 优先加警告"不同。但 base 里不存在"同时给"的旧用法，所以不算回归，只是政策选择；测试也没测这一点，这是对的。
- **无关改动：** 没有。小瑕疵：`histogram2d` 的文档仍写"Weights are normalized to 1 if `normed` is True"，Notes 里也仍用 normed 描述，但不影响行为。
- gold 通过全部 78 键，没发现 gold 自身违反公开要求。

## 9. 八方面覆盖（已查 / 未查）

1. **公开需求：** 已查题面、公开提示、两个函数与 `histogram` 的文档、发布说明、公开旧测试。未查：实际渲染给模型的完整消息（手上只有静态材料）。
2. **材料与初始问题：** 已查 base 源码确实没有 `density`（histograms.py L815、twodim_base.py L533）、manifest 的 `initial_diff` 为空、noop 的失败位置。原例没有实跑。
3. **测试是否测到要求：** 6 个目标键都逐条追到了调用、输入和断言。缺 D1、D2、D3 三处。
4. **误拒：** 没有确认的误拒。C1 预测得 1；精确浮点有低风险 T1（见 §10）。
5. **回归与 gold：** 已查，回归键全读。没有穷举仓库里的其它调用者；仓库内调用者只有 `histogram2d` 与 benchmarks，都兼容。
6. **开发条件：**
   - 只有 `PUB/environment_brief.md` L10–13 里"环境阶段实测"的陈述。**本次没有提供 devcheck，actor 侧未核。**
   - 静态推断：公开 `test_histograms.py` 的 `TestHistogram` 用 nose 式 `setup`（L15、L18）。在 pytest 7.4.4 加 `filterwarnings = error` 下，整类 21 个测试可能 ERROR。这是与修复无关的噪声，待 devcheck 确认。
   - 修改是纯 Python，不需要构建。
7. **交付与评分边界：** gold 交付了两个文件（gold 日志 L1–2；账本 `projection.included_paths`）；评分时导入的是 `/testbed/numpy/__init__.py`（账本 `RH2_OBS_IMPORT_PATH`）。通用面见 §7(d)。
8. **题目关系：** 见 §10 的 X1。

## 10. 问题登记（v1 编号，注明证据层次）

| 编号 | 问题 | 证据层次 | 暂定严重度 |
| --- | --- | --- | --- |
| T2b（待定） | D1：没测 `density=False` | 静态推断，加预测 | conditional；实跑得 1 即 S1 |
| T2（第 4 步，待定） | D2：没测有越界样本时"range 上积分为 1" | 静态推断，加预测 | conditional；得 1 即 S1 |
| T2（第 4 步，待定） | D3：没测 `normed` 兼容 | 静态推断，加预测 | conditional；得 1 即 S1 |
| T3 | 没测非均匀权重下的 density，也没测位置参数顺序 | 静态 | S2，登记 |
| T1（低风险） | `test_density_non_uniform_1d` L744 用精确相等（详见表下） | 纯 Python 浮点演算（附录 C），不是项目代码 | 登记，不建议修订；真实候选踩中再议 |
| X1 | 本题 gold 被同仓其它题的公开工作树包含，本题工作树也含其它题的修复（详见表下） | 已核：`43e333e2` 方向与两条测试名 | 登记；训练时控制重复采样；留出须按仓库划分 |
| 开发（actor 待验） | 没有 devcheck；公开测试噪声是推断 | 静态 | — |

- **T1 的细节：** 另一种等价运算顺序会差 1 ulp。例如先除以总数、再除以宽度，或者乘倒数，第 3 个 bin 会得到 0.09999999999999999 或 0.10000000000000002，而不是 0.1，于是判 0。但公开旧测试 L738–745 对 `normed` 做了同样的精确比对；复用现有归一化代码的写法都能过。
- **X1 的细节：**
  - 本题 gold 的 25 行逐字出现在 numpy `43e333e2` 的公开工作树里：`runs/r2e_static_prep_20260924/v3/public/numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d/worktree/numpy/lib/histograms.py` L944–945、L1107–1115，以及同目录 `twodim_base.py` L650–651。本题的新测试名见该题 `numpy/lib/tests/test_histograms.py` L787、L814。
  - 反向：本题工作树含 `2f4a9650` 的 `test_0D_3D`（`WT/numpy/lib/tests/test_io.py` L346）和 `a5ea773e` 的 `test_tile_one_repetition_on_array_gh4679`（`WT/numpy/lib/tests/test_shape_base.py` L610）。
  - 机械比对还称本题工作树含 `18b7cd9d`、`2f4a9650`、`5e8301c2`、`d805e9b6` 的 gold。核对需要它们的私有 gold，我没核。
- **外部答案可达：** 上游 numpy 1.15 起公开了同一修复，这属于外部答案可达。它不影响评分，只影响留出评测的解释。

## 11. 修订建议（对应候选实跑得 1 后才执行）

三处修订都放进现有目标测试，不改键集。

### R-c1（D1 命中时）

依据：histogram 文档 L607–609；公开测试 L81–83。

- `PRV/hidden_tests/test_1.py` 的 `TestHistogram2d.test_density` 末尾加：
  ```python
          # density=False returns the plain counts
          H, xed, yed = histogram2d(
              x, y, [[1, 2, 3, 5], [1, 2, 3, 5]], density=False)
          assert_array_equal(H, np.ones((3, 3)))
  ```
- `test_2.py` 的 `TestHistogramdd.test_density_non_uniform_2d` 末尾加：
  ```python
          hist, edges = histogramdd((y, x), bins=(y_edges, x_edges), density=False)
          assert_equal(hist, relative_areas)
  ```

### R-c2（D2 命中时）

依据：题面 L22；twodim_base.py L561–562；公开 1-D 测试 L110–112。

- `test_1.py` 的 `TestHistogram2d.test_density` 末尾加：
  ```python
          # samples outside the range are not tallied; the density integrates to 1 over the range
          H, xed, yed = histogram2d([0.5, 1.5, 1.5, 9.], [0.5, 0.5, 1.5, 9.],
                                    bins=2, range=[[0, 2], [0, 2]], density=True)
          assert_array_almost_equal(H, [[1/3., 0], [1/3., 1/3.]])
          assert_array_almost_equal((H * np.outer(np.diff(xed), np.diff(yed))).sum(), 1)
  ```
- `test_2.py` 的 `TestHistogramdd.test_density_non_uniform_1d` 末尾加。这里用 allclose，避开 §10 的精确浮点问题。值 7、8、9 在 bin 外，6 落在最右边、计入最后一个 bin：
  ```python
          # values outside the bins are not counted, as in histogram
          bins = np.array([0, 1, 3, 6])
          hist, edges = histogram(v, bins, density=True)
          hist_dd, edges_dd = histogramdd((v,), (bins,), density=True)
          assert_allclose(hist_dd, hist)
  ```

### R-c3（D3 命中时）

依据：histograms.py L848–850；twodim_base.py L563–565；发布说明 L79–80。

新断言必须容忍弃用警告：pytest.ini 会把警告变成错误，而合理解可能给 `normed` 加警告。`np.VisibleDeprecationWarning` 继承自 `UserWarning`（`WT/numpy/_globals.py` L45），所以两类警告都要过滤。不要断言警告有无，也不要测"两者同时给"。

- `test_1.py` 顶部的导入加上 `suppress_warnings`，然后在 `TestHistogram2d.test_density` 末尾加：
  ```python
          # the documented normed argument keeps working (a deprecation warning is allowed)
          with suppress_warnings() as sup:
              sup.filter(DeprecationWarning)
              sup.filter(np.VisibleDeprecationWarning)
              Hn, xed, yed = histogram2d(
                  x, y, [[1, 2, 3, 5], [1, 2, 3, 5]], normed=True)
          assert_array_almost_equal(Hn, answer, 3)
  ```
- `test_2.py` 的 `TestHistogramdd.test_density_non_uniform_2d` 末尾加同样的 `suppress_warnings` 块，调用 `histogramdd((y, x), bins=(y_edges, x_edges), normed=True)`，断言用 `assert_allclose(hist, 1 / (8*8))`。

### 验收（v1 §5）

- gold 为 1，noop 为 0。
- 对应的 D1、D2、D3 各为 0。
- C1 为 1。另加一个变体也须为 1：C1 的基础上把两个函数的 `normed` 默认值改为 None，并在 `normed is not None` 时发 DeprecationWarning（用来验证 R-c3 不会误拒弃用写法）。
- 键集与期望映射不变；隐藏测试树的哈希和派生镜像要重建。
- 由 Codex 复核。

### 不建议

不要测"两者同时给"的行为。gold 的 TypeError 与 `histogram` 的 density 优先都有依据，这属于 P5 类的政策选择。

## 12. 用途结论（初判，v1 §2）

- `problem_localization`：yes。
- `capability_comparison`：conditional。评分依据已核（当前材料上 noop 0、gold 1 各 2 次）；还差本批公开开发路径的 actor 实测（没有提供 devcheck）。
- `training_candidate`：conditional。还差 D1（第 3 步）与 D2、D3（第 4 步）的正式评分；任一得 1，须先完成对应的 R-c 修订与验收，并经 Codex 复核。X1 已登记。
- `heldout_candidate`：conditional，倾向 no。条件同上；另外 gold 逐字出现在 `43e333e2` 的公开初态里，上游也已公开，所以必须按仓库划分。修订后只能作"标明版本的自建评测"。
- `intended_use`：`development_diagnostic`。

## 13. 探针就绪差距（初判）

按指示我没读本批 README §3，以下只按 v1 §2 列。

- **已满足：**
  - 当前材料上的评分正/负对照（协调者已有的运行）。
  - 核心要求与断言的映射（本文 §3–4）。
  - v1 第 1、2 步。
- **未满足：**
  - 第 3 步退化探测的实跑。谁补：协调者。
  - 第 4 步 D2、D3 的实跑。谁补：协调者。
  - 如果命中：R-c 修订、验收与 Codex 复核。谁补：协调者 / Codex。
  - actor 侧开发核对（devcheck）：原例能否复现、公开测试命令与噪声、墙钟时间。谁补：协调者。
  - 与主审结论对账（第二步）。谁补：复核者。

## 14. 唯一最值得先做的下一步

用正式评分把 D1、D2、D3、C1 各跑一次。都是纯 Python 补丁，单次测试约 1 秒，全流程约 20 秒。三个错误候选里任何一个得 1，就按 §11 做对应的 R-c。

## 附录

### A. 材料一致性（sha256）

- 以下各项与 `PRV/grading_bundle.json` L8–32、`run_refs.json` L5–6 全部一致：
  - `PRV/gold.patch` = `b00869e7…d7bf`，也等于四条账本行的 `candidate.patch_sha256`。
  - `expected_output.json` = `f7c02eef…7b40`。
  - `test_1.py` = `b680bb79…254e`，`test_2.py` = `1d485d6e…d5fe4`，隐藏测试树 = `b55abfbe…9032`（noop 日志 L3 为 `RH2_SETUP_HIDDEN_TESTS_TREE`）。
  - `run_tests.sh` = `8285765f…6aaf`（日志 L4）。
- 6 份日志的 sha256 都与 `run_refs.json` 的记录相符。

### B. 运行原件要点

- **R-f 全池（09-23）：** 账本 `runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl` line 22。
  - noop：`report.reward` 0.0，`expected_match` 72/78，`keys_equal` True，missing 与 unexpected 为空。
  - gold：1.0，78/78，`projection.included_paths` 为两个 gold 文件。
  - 共同条件：派生镜像 `rh2-r2e-derived/numpy:d89bc4bbf541-r2e_derive_v1`（`sha256:1bd248e6…`），`recipe_id` 为 `r2e_derive_v1`；grader uid 54322，2 CPU / 4 GiB，网络 `deny_all`；`RH2_OBS_PKG_VERSION` 为 `1.16.0.dev0+a56c4e6`。
- **环境轮中央复跑：** 账本 `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` line 22。`run_refs` 标为 09-24，账本 `started_at_utc` 为 2026-09-23T18:33Z。结果同上。
- **noop 日志：** `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_d7e7c9c4.eval.log`。
  - L16–20：pytest 7.4.4，`configfile: pytest.ini`，收集 78 项。
  - L266–272：6 个失败全是 `unexpected keyword argument 'density'`。
- **gold 日志：** `..._2e262307.eval.log`。L1–2 显示两个文件被修改；L107 为 78 passed。
- **09-23 与 09-24 的比较：** 两份 noop 日志规范化（地址、时间戳、数组内容）后，只有 `test_weights` 回溯里的随机数据不同；两份 gold 日志规范化后完全相同。
- **M3 独立 runner（来源镜像）：** `runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/numpy/d89bc4bbf541/gold/a{1,2}/test_output.txt` 的 L91 都是 78 passed，两份一致；账本 L40、L87 的 reward 都是 1。

### C. 精确相等断言的浮点演算

scratchpad 里的纯 Python 脚本（IEEE double，与 numpy float64 逐元素运算一致）比较了几种运算顺序。计数 [1,2,3,4]、宽度 [1,2,3,4]、总数 10 下的结果：

| 运算顺序 | 与 `histogram` 精确相等 |
| --- | --- |
| 先除宽度再除总数（gold / base 的顺序） | 是 |
| `c/(s*vol)` | 是 |
| `c/vol/s` | 是 |
| 先除总数再除宽度 | 否，第 3 个 bin 为 0.09999999999999999 |
| 乘倒数 | 否，第 3 个 bin 为 0.10000000000000002 |

同样的几种顺序在 `test_density_non_uniform_2d`（1/64）和 `test_simple`（1/12）上都精确相等。
