# numpy__d89bc4bb 私有主审：读历史前分析

- 角色：R2E 私有主审（`roles/investigator_r2e.md`，单题闭环试行，按统一标准 v1），2026-09-29。本文在打开任何历史调查之前封存。
- 路径缩写（均相对仓库根）：
  - `PUB` = `runs/r2e_static_prep_20260924/v3/public/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`
  - `PRIV` = `runs/r2e_static_prep_20260924/v3/private/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`
  - `PUB43` = `runs/r2e_static_prep_20260924/v3/public/numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d`（同仓另一题的公开包）
- 证据层次标记：【源码】静态阅读推断；【算术】本机纯 Python 浮点算式，不导入项目代码；【运行】既有正式评分日志与账本；【待跑】需要协调者实跑。

## 0. 结论先行

- **题目**：base `a56c4e62`（numpy 1.16.0 开发版）里 `histogram2d` 和 `histogramdd` 的签名没有 `density`。题目要求两者都接受 `density=True`，返回"区间内积分为 1"的概率密度。gold 把 `density` 做成 `normed` 的别名（两者同时传入时抛 `TypeError`），复用已有的 `normed` 归一化代码。
- **评分侧证据完整**：当前材料下 noop 为 0（72/78，6 个目标键的失败原因都是题面所述的 `TypeError`），gold 为 1（78/78），两轮结果一致；独立 runner 在来源镜像上 gold 2/2。期望映射 78 键全为 PASSED，没有 FAILED/ERROR 键、没有撞键、没有材料修订。
- **暂定处置：S1（conditional，待 2 次正式评分确认），走 R-c；另有 1 个 T1 风险，待 1 次实跑。**
  1. **§4 第 3 步退化候选 `DEG`**：归一化分母改用"含区间外样本的全部样本数（或全部权重）"。6 个目标键里所有密度输入都没有区间外样本，所以 `DEG` 在全部 78 键上与 gold 逐位相同【源码＋算术】，预计得 1，判为 T2b。它违反题面"the integral over the range is 1"。
  2. **§4 第 4 步构造候选 `REN`**：把 `normed` 直接改名为 `density`，同时删掉 `normed`。隐藏测试已把 2D/ND 的 `normed=True` 全部改成 `density=True`，不再有任何 2D/ND 的 `normed=` 调用，所以 `REN` 预计得 1。它破坏 base 文档写明、公开测试也在用的 `normed` 接口，判为 S1。
  3. **T1 风险 `ORD`**：一个数学上正确的独立 density 分支，只是先除总数、再除格宽。`TestHistogramdd.test_density_non_uniform_1d` 要求结果与一维 `histogram` 逐位相等，而 `3/10/3 = 0.09999999999999999 ≠ 0.1`，所以 `ORD` 预计 77/78、判 0【算术】。
- **修订草案**（代码见附录 B）：
  - R-c1：两个隐藏文件各加一个含区间外样本的密度测试。
  - R-c2：两个隐藏文件各加一个"`normed=True` 仍返回密度，允许弃用告警"的测试。
  - R-b：把上述逐位相等的键改成 `assert_allclose`；是否采用，看 `ORD` 实跑结果。
- **用途暂定**：
  - 问题定位：yes。
  - 能力比较：conditional。
  - 训练候选：conditional（S1 一旦确认，须先完成 R-c 并验收）。
  - 留出评测候选：conditional。
- **最关键的未知项**：
  - `DEG`、`REN` 的正式评分结果。静态推断把握很高，但 S1 要以实跑为准。
  - 其次是解题侧 devcheck，尤其 `numpy/conftest.py` 依赖的编译扩展和公开测试能否跑通。

## 1. 八方面覆盖

| 方面 | 已查 | 未查 / 缺口 |
| --- | --- | --- |
| 公开需求 | 题面全文，以及 `public_hints`、brief 与 public_read。补读了 base 中 2D/ND/1D 三处 docstring 和实现、公开测试、`pytest.ini` | 模型实际收到的消息没有捕获（只有静态渲染） |
| 材料与初态 | 私有件哈希与各 bundle 一致；初态 diff 为 0 字节；noop 失败位置与题面报错一致（§3） | 当前新机器上重建的派生镜像还没有 noop/gold 正式评分（等 devcheck 或补跑） |
| 测试是否测到要求 | 两个隐藏文件全文已读。6 个目标键逐条展开；72 个回归键按类核对，确认所有候选都不改动它们的受测代码 | 离群点、`normed` 兼容、`density=False`、2D 带权四处没有隐藏断言（§4、§6） |
| 是否误拒合理解 | 无非 PASSED 键。`normed`/`density` 冲突策略不受评分影响。发现逐位相等带来的 T1 风险（`ORD`） | `ORD`、`DEP` 未实跑 |
| 回归与 gold 完整性 | gold 满足全部公开要求、公开测试不受影响，没有无关改动（§7） | gold 只在评分日志里被执行过，公开命令下的 gold 行为等 devcheck 私有对照 |
| 开发条件 | 按环境卡、brief 与评分日志逐阶段列出（§8） | 解题侧全部为"actor 待验"（devcheck 结果在第二步提供） |
| 交付与评分边界 | 两份纯 Python 文件；gold 投影包含这两份、没有忽略路径；隐藏测试不依赖仓库测试辅助 | 共用控制面（根目录 `conftest.py`/`pytest.ini` 可被候选修改）属 A 线共用机制，未逐题复审 |
| 题目关系与用途 | 核对了跨题扫描；在 `PUB43` 逐行确认本题 gold 已包含在该题初态中（§10） | 反方向的 4 题只有扫描结果，没有读它们的私有 gold |

## 2. 公开需求与 public_read 没有捕获的条件

- public_read 的需求表（R1–R13）与我的独立阅读一致。我补三处公开依据：
  - "区间外样本不参与归一化"（R4）不只是推知。`histogram2d` 自己的文档写明"All values outside of this range will be considered outliers and not tallied"（`PUB/worktree/numpy/lib/twodim_base.py:558-562`）；Notes 写明"sum over bins of the product bin_value * bin_area is 1"（同文件 `:590-592`）。一维 `density` 的文档是题面措辞的来源："normalized such that the *integral* over the range is 1"（`PUB/worktree/numpy/lib/histograms.py:607-613`），并写明"Values outside the range are ignored"（`:585-586`）。
  - base 中 nd 的 `normed` 文档写的是 `bin_count / sample_count / bin_volume`（`histograms.py:848-850`）。其中 `sample_count` 可以被字面理解为"全部样本数"，而实现用的是去掉离群格后的 `hist.sum()`（`:960-966`）。`DEG` 恰好对应这种字面误读，题面和上面几处文档可以消解它。
  - `normed` 是 base 两处文档写明的参数（`twodim_base.py:563-565`、`histograms.py:848-855`），6 个公开测试在用 `normed=True`（`PUB/worktree/numpy/lib/tests/test_twodim_base.py:207-231`；`test_histograms.py:548-559,599-606,711-745`）。`public_hints` 同时禁止修改测试文件。
- public_read 没有捕获、而会影响开发或解读的真实条件：
  - 评分侧实测：pytest 7.4.4，插件 hypothesis 6.79.4 与 pytest-env 1.0.1（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-n_2a796254.eval.log:16,19`）。
  - `numpy/conftest.py:11` 导入编译扩展 `numpy.core._multiarray_tests`。公开测试能否收集，取决于该扩展是否在镜像中就地构建。这一点 actor 待验。
  - 在 pytest 7.4.4 下，`TestHistogram` 的 nose 风格 `setup/teardown`（`PUB/worktree/numpy/lib/tests/test_histograms.py:15-19`）会在每个测试的 setup 阶段发出 `PytestRemovedIn8Warning`，再被 `pytest.ini:6-7` 的 `filterwarnings = error` 变成错误。由此推断，整文件运行会出现约 21 个与本题无关的 ERROR。隐藏测试正是为此改成了 `setup_method`（`PRIV/hidden_tests/test_2.py:15-19`）。public_read 用 `-k TestHistogramdd` 规避了这一点。【源码】，待 devcheck 核实。

## 3. 材料一致性与初态（运行证据）

- 私有件与摄入面一致：`hidden_tests/test_1.py`、`test_2.py` 的 sha256 与 `PRIV/grading_bundle.json` 的 `hidden_test_files` 一致；`expected_output.json` 与 bundle 中的字符串逐字相同（sha `f7c02eef…`）；`gold.patch` 与 `validation_bundle.json` 相同，sha `b00869e7…` 也等于账本 gold 行的 `patch_sha256`；`run_tests.sh` 与 bundle 相同。
- 初态：相对 base 的 diff 为 0 字节（`PUB/worktree_manifest.json` 的 `initial_diff`）；两个源码文件的 sha256 与清单一致。
- 当前材料的运行（`PRIV/run_refs.json`，4 行均为 `material=current`，派生镜像均为 `sha256:1bd248e6c0eb…`，`env_recipe`/`resource_recipe` 为 null）：
  - noop：`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:22`，日志 `…noop-n_2a796254.eval.log`：
    - `:5` `APPLY_RC=0`；`:20` collected 78；`:272` "6 failed, 72 passed"；`:274` `RH2_TEST_RC=1`。
    - 6 个失败都是题面报错原文：`:35`、`:51` 为 `TypeError: histogram2d() got an unexpected keyword argument 'density'`（`test_1.py:211,227`）；`:74`、`:109`、`:159`、`:183` 为 `histogramdd()` 的同类报错（`test_2.py:550,602,735,743`）。
  - gold：`ledger_r2e_all_gold.jsonl:22`，日志 `…gold-n_ad7d92eb.eval.log`：
    - `:1-2` 只改了两份文件；`:22` collected 78；`:107` "78 passed"；`:109` `RC=0`。
    - 账本 `projection.included_paths` 为这两份文件，`ignored_paths` 为空。
  - 09-24 复跑（`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:22`，日志 `…rer_d7e7c9c4` / `…rer_2e262307`）：去掉时间戳和对象地址后与上面逐行相同。唯一差别是 noop 的 `test_weights` 用了不同的未设种子随机数据，结果相同。
  - 独立 runner（来源镜像）：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:40,87`，日志 `…/numpy/d89bc4bbf541/gold/a{1,2}/test_output.txt:91` 均为 "78 passed"。
  - 资源与时长：测试段 0.8–1.3 s，内存峰值约 311–320 MB；评分总阶段约 23–27 s。

## 4. 隐藏测试展开

隐藏测试就是公开的两份测试文件做了三类替换（`diff` 已核对）：
1. 2D/ND 的 `normed=True` 全部改成 `density=True`：`test_1.py:211,227`；`test_2.py:550,556,602,605,735,743`。
2. 三个测试改名：`test_norm` 改为 `test_density`；`test_normed_non_uniform_{2d,1d}` 改为 `test_density_non_uniform_{2d,1d}`。
3. `TestHistogram` 的 `setup/teardown` 改成 `setup_method/teardown_method`（空方法，不改变断言）。

没有任何其它新增断言。两个文件只导入 `numpy` 与 `numpy.testing`，不依赖仓库测试模块。搬迁后丢失的 `numpy/conftest.py` 只有 FPU 检查和 doctest 命名空间两个 fixture，与断言无关。键数为 33＋45＝78，没有撞键。

**6 个目标键**（noop 与 gold 结果不同的键，均为 noop FAILED、gold PASSED）：

| 键 | 输入与调用 | 决定性断言 | 测到什么 |
| --- | --- | --- | --- |
| `TestHistogram2d.test_asym`（`test_1.py:207-221`） | 8 点，bins (6,5)，range [[0,6],[0,5]]，格面积均为 1，无区间外点 | `assert_array_almost_equal(H, answer/8., 3)` | 2D 接受 `density`；等宽格下为 计数/总数 |
| `TestHistogram2d.test_density`（`:223-231`） | 9 点，边 [1,2,3,5]² 非等宽，全部在区间内 | 近似等于 `[[1,1,.5],[1,1,.5],[.5,.5,.25]]/9`（decimal 3） | 2D 除以格面积 |
| `TestHistogramdd.test_simple`（`test_2.py:539-574`） | 6 个 3D 点，边 [[-2,0,2],[0,1,2,3]×2]（体积 2）；以及 (2,3,4) 格、range 内（体积 1） | `np.all(H == answer/12.)`（精确）；`answer/6.`（decimal 4） | ND 接受 `density`；除以体积 |
| `TestHistogramdd.test_weights`（`:599-608`） | 100 个随机 2D 点（未设种子），默认 10 格，范围取数据的 min/max | `density(weights=2) == density(无权重)`（精确） | 权重整体缩放不变。只测了均匀权重 |
| `TestHistogramdd.test_density_non_uniform_2d`（`:711-736`） | 非等宽 2D，计数与面积成比例，全部在区间内 | `assert_equal(hist, 1/64)`（精确） | 非等宽 ND 密度 |
| `TestHistogramdd.test_density_non_uniform_1d`（`:738-745`） | 1D 数据 `arange(10)`，边 [0,1,3,6,10] | `assert_equal(hist_1d_density, hist_dd)`（**逐位**） | ND 与一维 `histogram(density=True)` 一致 |

**72 个回归键**：
- `test_1.py` 中与直方图无关的 27 个（eye/diag/flip/tri/vander 等），任何候选都不改动其受测代码。
- `TestHistogram2d` 的 4 个计数型测试（simple、all_outliers、empty、binparameter_combination）。
- 一维 `TestHistogram` 21 个与 `TestHistogramOptimBinNums` 9 个。其中 `test_normed` 要求一维 `normed=True` 恰好发出 1 个 `VisibleDeprecationWarning`（`:42-64`），一维 `test_outliers` 测了一维密度加离群点（`:110-117`）。本题候选都不改动一维代码。
- `TestHistogramdd` 的其余 11 个计数、形状、边界与报错测试。

阅读范围：两个隐藏文件全文；受影响函数（`histogramdd` 全函数、`histogram2d` 全函数、一维 `histogram` 的密度段 `:777-812`）。一维分箱与边界计算未改动，没有细读。

## 5. 需求—断言双向表

| 公开要求或合理旧行为 | 公开依据 | 对应键与断言 | 覆盖 | 证据或下一步 |
| --- | --- | --- | --- | --- |
| R1 `histogram2d` 接受 `density` | 题面 `user_prompt.txt:4-7,18,26-28` | `test_asym`、`test_density`（2D） | 覆盖 | noop 日志 `:35,:51` |
| R2 `histogramdd` 接受 `density` | 题面 `:30-31` | ND 的 4 个目标键 | 覆盖 | noop 日志 `:74,:109,:159,:183` |
| R3 密度＝计数/总数/格面积（含非等宽） | 题面 `:21-22`；`twodim_base.py:563-565,590-592`；`histograms.py:848-850` | 2D `test_density`；ND 的 `non_uniform_2d/1d`、`test_simple` | 覆盖 | — |
| R4 离群点不计入，"区间内积分为 1" | 题面 `:22`；`twodim_base.py:558-562,590-592`；`histograms.py:585-586,607-613` | **无**：所有密度输入都没有区间外样本 | **缺失** | `DEG`【待跑】，预计 1 → T2b |
| R5 返回结构不变 | 题面 `:18` | 各目标键的解包 | 覆盖（隐式） | — |
| R6 带权密度按区间内总权重归一 | `histograms.py:851-855`；`twodim_base.py:566-570` | `test_weights`（只测均匀权重缩放） | 部分 | 忽略权重的实现不在 gold 修改位置，未列候选 |
| R7 `density=False` 返回计数 | 布尔参数语义；一维先例 `histograms.py:607-609`、公开测试 `test_histograms.py:81-83` | 无 | 缺失（T3） | 登记 |
| R8 `normed=True` 保持可用、数值不变 | 两处 base 文档；6 个公开测试；提示"不要改测试" | **无**：隐藏测试已全部换成 `density` | **缺失** | `REN`【待跑】，预计 1 → §4 第 4 步 |
| R9 原位置参数顺序不变 | 签名 `twodim_base.py:533`、`histograms.py:815`；内部按位置调用 `twodim_base.py:655` | 只间接覆盖：2D 用例都经过这次内部位置调用，但都不带权重 | 部分（T3） | 2D 带权在隐藏与公开测试中都没有用例 |
| R10 `normed` 与 `density` 同时传入 | 无公开约定 | 无 | 中性 | gold 抛 `TypeError`，`DEP` 发告警，两者都应得 1 |
| R11 默认值 `None` 还是 `False` | 无 | 无 | 中性 | — |

**反查关键断言的依据**：
- 精确相等 `H == answer/12.`、`== 1/64`、带权缩放相等：公开旧测试对 `normed` 有同样的精确断言。我按不同除法顺序算过（附录 C），这三处对合理顺序都稳健，不构成误拒风险。
- `test_density_non_uniform_1d` 的逐位相等：公开旧版对 `normed` 有同样断言，但对新的 `density` 而言，"与一维逐位相同"只是实现细节，没有公开依据。见 §6 的 `ORD`。

## 6. R2E 专项与 v1 §4 判定

**R2E 专项**：
- (a) 期望映射全为 PASSED，没有需要继续失败的键；更完整的修复（如 `DEP`）也不会翻转任何期望键【源码】。
- (b) 题面报错与 noop 的 6 个目标键失败原因逐字一致（§3）。
- (c) 题面只给出参数名和语义，没有实现代码，不属于 P1。补参数类题点名参数难以避免；base 已有正确的 `normed` 实现，所以核心改动量很小。
- (d) 不依赖 base 版测试辅助；conftest 搬迁的损失无影响；没有撞键；`setup_method` 改名是 R2E 对新版 pytest 的中性适配。
- (e) 多个键使用未设种子的随机数，但断言与数据无关：均匀权重缩放下的精确相等，是因为乘以 2 在二进制浮点中精确，已用 10 万组随机值做过算术核验。两轮 noop 的随机数不同、结果相同。没有时间或资源敏感键。
- (f) 没有材料修订（`revisions.json` 为 `[]`）。

**v1 §4 五步**：

| 步 | 结论 | 依据 |
| --- | --- | --- |
| 1 核心要求有无直接断言 | 有 | 6 个目标键直接断言 2D/ND 的密度数值 |
| 2 是否只用题面示例的字面值 | 否 | 题面示例（5 点反对角、`bins=5`）不在测试中；测试覆盖等宽/非等宽、2D/3D/1D、带权 |
| 3 退化探测 | **`DEG` 预计得 1 → S1（T2b）**【待跑】 | 见下 |
| 4 已有构造候选 | **`REN` 预计得 1，并破坏有文档的常用接口 → S1**【待跑】 | 见下 |
| 5 | 不适用（前面已命中，暂为 conditional） | — |

**退化候选 `DEG`**（唯一的退化候选，补丁见附录 A1）：
- 改法：在 gold 修改的 `histogramdd` 归一化块（`histograms.py:960-971`）中，于去掉离群格之前记下 `total = hist.sum()`，归一化时改用 `s = total`；`density` 作为 `normed` 的别名接入；`histogram2d` 把 `density` 按位置转发。方向属"作用在无关对象上"：用含离群格的整张直方图作分母。
- 违反的公开要求：题面"integral over the range is 1"，以及 `histogram2d` 文档中"离群点不计入""各格 值×面积 之和为 1"。
- 看出违反的输入：`np.histogram2d([0.5,1.5,2.5,9.0],[0.5,1.5,2.5,9.0], bins=3, range=[[0,3],[0,3]], density=True)`。正确结果对角线为 1/3、积分 1；`DEG` 得 0.25、积分 0.75。
- 预计评分：78/78，得 1。理由是所有密度用例都没有区间外样本，整数计数求和精确，所以与 gold 逐位相同。
- 可能的分歧：若复核认为"数据超出 range"属于边缘输入，可降为 §4 第 4 步的 T3/S2。我不这样判，理由有三：题面给出的归一化目标就是"range 内积分"；`range` 的文档用途就是排除离群点；`DEG` 还对应 base 文档 `sample_count` 的字面误读，是真实模型可能写出的实现。
- 其它退化方向按源码推断都会被目标键拒绝，不列为候选、不需实跑：只加参数不实现、只除总数不除面积、只修一个函数。

**构造候选 `REN`**（附录 A2）：
- 改法：两个签名中的 `normed` 改名为 `density`（位置不变），`if normed:` 改为 `if density:`，`histogram2d` 的内部调用同步修改。
- 违反：`np.histogram2d([1,2,3],[1,2,3], bins=[[1,2,3,5]]*2, normed=True)` 抛 `TypeError`。public_read 的 `pytest_histogram2d_public` 预计 2 个失败，`pytest_histogramdd_public` 预计 4 个失败，`compat_normed_positional` 失败。
- 预计评分：78/78，得 1。隐藏测试中 `normed` 只出现在一维 `histogram`（`test_2.py:49,61`）。
- 这是最省事的"改名式"修法，很可能被 RL 学到，判为 S1（§4 第 4 步：破坏有文档、常用的公开行为）。

**合理替代解与 T1 风险**：
- `ORD`（附录 A3）：新增独立的 density 分支（`density` 给出时覆盖 `normed`，与一维先例一致），计算 `hist / hist.sum()` 后逐轴除以格宽；`normed` 路径不动。
  - 它满足全部公开要求，public_read 的全部 6 条命令也都能通过。
  - 预计 77/78，唯一不符的键是 `TestHistogramdd.test_density_non_uniform_1d`（观测 FAILED，期望 PASSED）。
  - 原因：一维密度为 `[0.1]*4`，`ORD` 为 `[0.1, 0.1, 0.09999999999999999, 0.1]`【算术，附录 C】。
  - 解题者用公开材料无法察觉，属于误拒（T1）。概率不高，因为多数解会直接复用 `normed` 分支，但会给 RL 带来假阴性。
- `DEP`（附录 A4）：沿一维先例，`density` 覆盖 `normed`；只传 `normed` 或两者同传时发 `DeprecationWarning`。
  - 预计 78/78 得 1。隐藏测试不调用 2D/ND 的 `normed`；`histogram2d` 默认转发 `None`，不会误发告警。
  - 它会让公开 `normed` 测试在 `filterwarnings = error` 下失败。这说明公开证据更支持"静默别名"，但题面没有禁止弃用。
  - 用途：作为 R-c2 的验收对照（修订后仍须得 1），现在不必跑。

## 7. gold 按公开要求检查

- **原例**：gold 把 `density=True` 接入原有 `normed` 归一化。题面示例应得到反对角线约 0.3125（＝1/(5×0.8×0.8)）、积分 1。这是【源码】推断；公开命令下的执行证据等 devcheck 的私有 gold 对照。
- **离群点与权重**：gold 沿用去掉离群格后的 `hist.sum()`，满足 R4、R6。
- **旧行为**：
  - `density=False` 与 `normed=False` 都返回计数。
  - `normed=True` 静默别名，数值逐位不变，公开测试不受影响。
  - 位置参数保持不变：`density` 追加在 `weights` 之后，内部调用同步追加（`PRIV/gold.patch:9-11,61-63,88-89`）。
- **gold 的设计选择**：
  - 两者同传时抛 `TypeError`（`gold.patch:38-46`），包括 `normed=False, density=True`。
  - `normed` 默认值由 `False` 改为 `None`。
  - 两者都没有公开依据，也都不受评分影响，不算缺陷。
  - 权重段文档仍写 `normed`，只是文案问题。
- **无关改动**：没有。
- **初态失败位置、目标键与退出情况**：见 §3，属执行证据。

## 8. 逐题开发需求

| 阶段 / 条件 | 需求 | 依据 | 证据级别 |
| --- | --- | --- | --- |
| 准备 | 派生镜像（与 grader 同一张），`/testbed` 就地构建的 numpy（编译扩展、生成的 `version.py`） | 环境卡 §1–2；评分日志可导入 | 评分侧实测；解题侧 actor 待验 |
| 导入 | `/testbed` 必须在 `sys.path` 上（在 `/testbed` 下用 `python -c` 或 `python -m pytest`） | `PUB/environment_brief.md:13` | 环境阶段实测（brief） |
| 依赖与网络 | 不需要新依赖、pip 或网络（只改两份纯 Python 文件） | gold；brief `:11` | 源码 |
| 资产 | 无 | — | — |
| 权限 | agent 54321 可写 `/testbed` | brief `:12` | 环境阶段实测 |
| 构建 | 不需要；不要跑 `setup.py` 或 `runtests.py` | public_read §4 | 源码 |
| 公开验证 | public_read 的 6 条命令；`numpy/conftest.py` 需要 `numpy.core._multiarray_tests` | `PUB/worktree/numpy/conftest.py:11` | **actor 待验（devcheck）** |
| 整文件公开测试 | 预计 `TestHistogram` 有 21 个与题无关的 setup 错误（§2） | 源码推断 | 待 devcheck；探针分析时按"与本题无关的恒失败公开测试"解读 |
| 提交边界 | 两份 `.py`；正式导出按字节差异 | 账本 gold 行 `projection` | 评分侧实测 |
| 时长与资源 | 隐藏测试约 1 s；2 CPU / 4 GiB 足够 | 账本 `phases`/`resource` | 实测 |

## 9. 交付与评分边界

- 合法修复只涉及两份非测试源码，不会被投影忽略，也不会被隐藏测试的注入覆盖。隐藏测试放在 `r2e_tests/` 下，与仓库测试互不影响。
- 可见资产中没有答案：初态与 base 相同；与 gold 唯一逐字相同的一行是一维 `histogram` 已有的 `density=None):`。
- 根目录 `pytest.ini`（`filterwarnings = error`）是评分环境的一部分。候选能否改写它或新增根 `conftest.py` 属共用控制面问题，交 A 线；本题没有特例。

## 10. 题目关系（X1）

- **`numpy__43e333e2` 的初态包含本题答案**。该题 base 为 `1798a7d4`，题目与 `np.ma.average` 有关。我逐行核对过：本题 gold 的 25 行非平凡新增行全部逐字出现在 `PUB43/worktree/numpy/lib/histograms.py`（`:944-945,1107-1115`）与 `twodim_base.py`（`:650-651`）。该初态还含本题隐藏测试的新测试名，以及上游后来补的 `test_density_via_normed`（`normed` 应别名到 `density`）与 `test_density_normed_redundancy`（两者同传抛 `TypeError`，见 `PUB43/worktree/numpy/lib/tests/test_histograms.py:823-838`）。后两个测试说明维护者认可"`normed` 别名"这一行为，可作 R-c2 的佐证；但"同传报错"在本题 base 上没有公开依据，不应加入修订。
- 反方向（扫描结果，未读私有件，没有逐行复核）：本题初态逐字包含 18b7cd9d（poly1d）、2f4a9650（savetxt）、5e8301c2（einsum）、d805e9b6（masked repr）的 gold，以及 2f4a9650、a5ea773e（tile）的新测试名。这些题都与直方图无关。
- 处理：两题同进训练时控制重复采样；按仓库划分（D3）时同侧。
- 任务类型：API 补参数，题面写成 bug。上游在 numpy 1.16 公开发布了这项改动，不能排除模型在预训练中见过。

## 11. 问题登记（暂定）

| 编号 | 问题 | 严重度 | 证据层次 | 去向 |
| --- | --- | --- | --- | --- |
| T2（T2b） | 密度用例都没有区间外样本，`DEG` 可满分 | S1，conditional（待 `DEG` 实跑） | 源码＋算术 | R-c1 |
| T2（§4 第 4 步） | 隐藏测试不再覆盖 2D/ND 的 `normed`，删接口的 `REN` 可满分 | S1，conditional（待 `REN` 实跑） | 源码 | R-c2 |
| T1 | `test_density_non_uniform_1d` 要求逐位相等，`ORD` 被判 0 | 待定（`ORD` 实跑后决定） | 算术 | 条件 R-b |
| T3 | `density=False`、2D 带权、位置参数兼容没有隐藏断言 | S2 候选，仅登记 | 源码 | 登记；可选扩展（附录 B 注） |
| X1 | 43e333e2 初态含本题答案；本题初态含 4 题答案 | 登记 | 逐行核对＋扫描 | 采样控制与划分 |
| 环境备注 | 整文件跑公开 `test_histograms.py` 有与题无关的错误 | 登记 | 源码推断 | 待 devcheck |

未命中：E1–E5、D1、P1/P2/P5/P6、G1、X2（材料哈希全部一致）。

## 12. 暂定用途与处置

- `disposition.scope=static_review`；`state` 保持 `needs_review`。理由：静态候选待 actor 验证，另有测试缺口（S1 conditional）待实跑与 R-c。
- v1 用途：
  - `problem_localization`：yes。
  - `capability_comparison`：conditional。还差两项：① devcheck 证实解题侧公开开发路径，并在重建镜像上确认 noop 0 / gold 1；② R-c 落地之前，得 1 的补丁要按两条已登记缺口做事后审计（是否保留 `normed`、归一化是否排除离群点），原始 reward 与审计结果分列。
  - `training_candidate`：conditional。先实跑 `DEG`、`REN`；命中后做 R-c1/R-c2，并按 §5 验收（gold 1、noop 0、`DEG` 0、`REN` 0、`DEP` 1），经 Codex 复核；`ORD` 若确认误拒，同轮做 R-b；另做 X1 采样控制。
  - `heldout_candidate`：conditional。条件同训练候选；按仓库划分；修订后只能作"标明版本的自建评测"；上游已公开。

## 13. 请协调者执行

1. **devcheck 读取点**（结果已有）：
   - 在 base 上：`import_numpy_version` 应为 0；两条 repro 命令应非 0，且报错为题面原文；两条公开 pytest 命令应分别为 6 passed 和 15 passed；`compat_normed_positional` 应为 0。
   - 私有 gold 对照：两条 repro 命令应为 0，积分约 1.0；其余与 base 相同。
   - 记录各命令墙钟时间；确认公开 pytest 收集没有因 `numpy.core._multiarray_tests` 报错。
   - 可选补一条，以 agent 身份在 base 上跑：`cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider -q numpy/lib/tests/test_histograms.py`，用来核实 §2 的"约 21 个无关 ERROR"。
2. **正式评分**（当前材料，重建后的派生镜像；每项核对补丁确实已应用、included_paths 为两份文件、collected 78、日志完整）：

| 候选 | 补丁 | 预计 reward | 预计匹配 | 预计不符键 | 决定什么 |
| --- | --- | --- | --- | --- | --- |
| noop / gold | —／`PRIV/gold.patch` | 0 / 1 | 72/78、78/78 | noop 为 6 个目标键 | 当前版本基线（devcheck 已含正式评分的话可复用） |
| `DEG` | 附录 A1 | 1 | 78/78 | — | §4 第 3 步 → T2b |
| `REN` | 附录 A2 | 1 | 78/78 | — | §4 第 4 步 → S1 |
| `ORD` | 附录 A3 | 0 | 77/78 | `TestHistogramdd.test_density_non_uniform_1d` | T1 → 是否 R-b |

3. **可选私有行为对照**（便宜，用来补足"违反公开要求"的执行证据；在各候选下于 `/testbed` 运行）：
   - `DEG`：`python -c "import numpy as np; H,xe,ye=np.histogram2d([0.5,1.5,2.5,9.0],[0.5,1.5,2.5,9.0],bins=3,range=[[0,3],[0,3]],density=True); I=(H*np.outer(np.diff(xe),np.diff(ye))).sum(); print('integral', I); assert abs(I-1)<1e-12"`。gold 应退出 0，`DEG` 应非 0（积分 0.75）。
   - `REN`：`python -c "import numpy as np; np.histogram2d([1,2,3],[1,2,3],bins=[[1,2,3,5],[1,2,3,5]],normed=True); np.histogramdd(np.c_[[1,2,3],[1,2,3]],bins=[[1,2,3,5],[1,2,3,5]],normed=True); print('normed ok')"`。gold 应退出 0，`REN` 应报 `TypeError`。
   - `ORD`：`python -c "import numpy as np; v=np.arange(10); b=np.array([0,1,3,6,10]); dd=np.histogramdd((v,),(b,),density=True)[0]; h=np.histogram(v,b,density=True)[0]; print(dd.tolist(), h.tolist()); assert np.allclose(dd,h); print('bitwise_equal', bool((dd==h).all()))"`。gold 应输出 `True`；`ORD` 应输出 `False`，但 allclose 成立。
4. **修订验收**（若命中）：先应用 R-c（附录 B1），视 `ORD` 结果再应用 R-b（B2）；按预计结果矩阵（附录 B3）实跑。

## 14. 缺口与未查范围

- 所有候选结论都是预测，均未实跑；解题侧条件没有本批证据。
- 未查：模型实际收到的消息；C 源码与编译扩展；一维分箱细节（未改动）；`install.sh`（公开包未收录）；其它 4 题的私有 gold（跨题关系只按扫描）；共用控制面（A 线）。
- 我读过的原件：角色卡与四份方法文档、统一标准 v1；本题公开包与 public_read、commands.json；本题私有包全部文件；`run_refs.json` 指向的 4 条账本行与 6 份日志；两份跨题扫描；同仓 7 题公开包的题目与 base，以及 `PUB43` 的相关源码与测试。
- 我没有读：任何历史调查、`history/`、各审查目录、本批 README/board/assignments、`runs/` 下的其它分析与汇总文件、其它题私有包。
- 临时文件：`agents/inv_numpy_d89bc4bb/` 下有 base 副本、生成候选与修订 diff 的脚本、`git apply --check` 用的副本树。没有运行项目代码。

---

## 附录 A：候选补丁

以下补丁都相对 base 工作树，在草稿区的 base 副本上用 `git apply --check` 验证过；修改后的文件都能通过 `ast.parse`。gold 也在同一副本上应用成功。

### A1 `DEG`（§4 第 3 步唯一退化候选：用含离群点的总数归一）

```diff
diff --git a/numpy/lib/histograms.py b/numpy/lib/histograms.py
--- a/numpy/lib/histograms.py
+++ b/numpy/lib/histograms.py
@@ -812,7 +812,8 @@
         return n, bin_edges
 
 
-def histogramdd(sample, bins=10, range=None, normed=False, weights=None):
+def histogramdd(sample, bins=10, range=None, normed=False, weights=None,
+                density=None):
     """
     Compute the multidimensional histogram of some data.
 
@@ -957,13 +958,19 @@
     # This preserves the (bad) behavior observed in gh-7845, for now.
     hist = hist.astype(float, casting='safe')
 
+    # total weight of all samples, outlier bins included
+    total = hist.sum()
+
     # Remove outliers (indices 0 and -1 for each dimension).
     core = D*(slice(1, -1),)
     hist = hist[core]
 
+    if density is not None:
+        normed = density
+
     # Normalize if normed is True
     if normed:
-        s = hist.sum()
+        s = total
         for i in _range(D):
             shape = np.ones(D, int)
             shape[i] = nbin[i] - 2
diff --git a/numpy/lib/twodim_base.py b/numpy/lib/twodim_base.py
--- a/numpy/lib/twodim_base.py
+++ b/numpy/lib/twodim_base.py
@@ -530,7 +530,8 @@
     return v
 
 
-def histogram2d(x, y, bins=10, range=None, normed=False, weights=None):
+def histogram2d(x, y, bins=10, range=None, normed=False, weights=None,
+                density=None):
     """
     Compute the bi-dimensional histogram of two data samples.
 
@@ -652,7 +653,7 @@
     if N != 1 and N != 2:
         xedges = yedges = asarray(bins)
         bins = [xedges, yedges]
-    hist, edges = histogramdd([x, y], bins, range, normed, weights)
+    hist, edges = histogramdd([x, y], bins, range, normed, weights, density)
     return hist, edges[0], edges[1]
 
 
```

### A2 `REN`（§4 第 4 步构造候选：`normed` 改名为 `density`，删掉 `normed`）

```diff
diff --git a/numpy/lib/histograms.py b/numpy/lib/histograms.py
--- a/numpy/lib/histograms.py
+++ b/numpy/lib/histograms.py
@@ -812,7 +812,7 @@
         return n, bin_edges
 
 
-def histogramdd(sample, bins=10, range=None, normed=False, weights=None):
+def histogramdd(sample, bins=10, range=None, density=False, weights=None):
     """
     Compute the multidimensional histogram of some data.
 
@@ -961,8 +961,8 @@
     core = D*(slice(1, -1),)
     hist = hist[core]
 
-    # Normalize if normed is True
-    if normed:
+    # Normalize if density is True
+    if density:
         s = hist.sum()
         for i in _range(D):
             shape = np.ones(D, int)
diff --git a/numpy/lib/twodim_base.py b/numpy/lib/twodim_base.py
--- a/numpy/lib/twodim_base.py
+++ b/numpy/lib/twodim_base.py
@@ -530,7 +530,7 @@
     return v
 
 
-def histogram2d(x, y, bins=10, range=None, normed=False, weights=None):
+def histogram2d(x, y, bins=10, range=None, density=False, weights=None):
     """
     Compute the bi-dimensional histogram of two data samples.
 
@@ -652,7 +652,7 @@
     if N != 1 and N != 2:
         xedges = yedges = asarray(bins)
         bins = [xedges, yedges]
-    hist, edges = histogramdd([x, y], bins, range, normed, weights)
+    hist, edges = histogramdd([x, y], bins, range, density, weights)
     return hist, edges[0], edges[1]
 
 
```

### A3 `ORD`（合理替代解：独立 density 分支，先除总数再除格宽；T1 探测）

```diff
diff --git a/numpy/lib/histograms.py b/numpy/lib/histograms.py
--- a/numpy/lib/histograms.py
+++ b/numpy/lib/histograms.py
@@ -812,7 +812,8 @@
         return n, bin_edges
 
 
-def histogramdd(sample, bins=10, range=None, normed=False, weights=None):
+def histogramdd(sample, bins=10, range=None, normed=False, weights=None,
+                density=None):
     """
     Compute the multidimensional histogram of some data.
 
@@ -961,6 +962,17 @@
     core = D*(slice(1, -1),)
     hist = hist[core]
 
+    # density overrides normed when given, as in histogram()
+    if density is not None:
+        normed = False
+        if density:
+            # probability of each bin, divided by the bin volume
+            hist = hist / hist.sum()
+            for i in _range(D):
+                shape = np.ones(D, int)
+                shape[i] = nbin[i] - 2
+                hist = hist / dedges[i].reshape(shape)
+
     # Normalize if normed is True
     if normed:
         s = hist.sum()
diff --git a/numpy/lib/twodim_base.py b/numpy/lib/twodim_base.py
--- a/numpy/lib/twodim_base.py
+++ b/numpy/lib/twodim_base.py
@@ -530,7 +530,8 @@
     return v
 
 
-def histogram2d(x, y, bins=10, range=None, normed=False, weights=None):
+def histogram2d(x, y, bins=10, range=None, normed=False, weights=None,
+                density=None):
     """
     Compute the bi-dimensional histogram of two data samples.
 
@@ -652,7 +653,8 @@
     if N != 1 and N != 2:
         xedges = yedges = asarray(bins)
         bins = [xedges, yedges]
-    hist, edges = histogramdd([x, y], bins, range, normed, weights)
+    hist, edges = histogramdd([x, y], bins, range, normed, weights,
+                              density=density)
     return hist, edges[0], edges[1]
 
 
```

### A4 `DEP`（合理替代解，一维先例：`density` 覆盖 `normed`，`normed` 发弃用告警；修订验收用）

```diff
diff --git a/numpy/lib/histograms.py b/numpy/lib/histograms.py
--- a/numpy/lib/histograms.py
+++ b/numpy/lib/histograms.py
@@ -812,7 +812,8 @@
         return n, bin_edges
 
 
-def histogramdd(sample, bins=10, range=None, normed=False, weights=None):
+def histogramdd(sample, bins=10, range=None, normed=None, weights=None,
+                density=None):
     """
     Compute the multidimensional histogram of some data.
 
@@ -961,6 +962,19 @@
     core = D*(slice(1, -1),)
     hist = hist[core]
 
+    # density overrides the normed keyword, as in histogram()
+    if density is not None:
+        if normed is not None:
+            warnings.warn(
+                "The normed argument is ignored when density is provided. "
+                "In future passing both will result in an error.",
+                DeprecationWarning, stacklevel=2)
+        normed = density
+    elif normed is not None:
+        warnings.warn(
+            "The normed argument is deprecated, use density instead.",
+            DeprecationWarning, stacklevel=2)
+
     # Normalize if normed is True
     if normed:
         s = hist.sum()
diff --git a/numpy/lib/twodim_base.py b/numpy/lib/twodim_base.py
--- a/numpy/lib/twodim_base.py
+++ b/numpy/lib/twodim_base.py
@@ -530,7 +530,8 @@
     return v
 
 
-def histogram2d(x, y, bins=10, range=None, normed=False, weights=None):
+def histogram2d(x, y, bins=10, range=None, normed=None, weights=None,
+                density=None):
     """
     Compute the bi-dimensional histogram of two data samples.
 
@@ -652,7 +653,7 @@
     if N != 1 and N != 2:
         xedges = yedges = asarray(bins)
         bins = [xedges, yedges]
-    hist, edges = histogramdd([x, y], bins, range, normed, weights)
+    hist, edges = histogramdd([x, y], bins, range, normed, weights, density)
     return hist, edges[0], edges[1]
 
 
```

## 附录 B：修订草案（v1 §5；由协调者实施，Codex 复核后才生效）

### B1 R-c1 与 R-c2（相对当前隐藏测试，路径按评分时的 `r2e_tests/`；已在副本上验证能应用、语法正确）

- **R-c1（离群点，两处）**
  - 公开依据：题面"integral over the range is 1"；`twodim_base.py:558-562,590-592`；`histograms.py:585-586,607-613`。
  - 改动：每个文件新增一个 `test_density_outliers`，输入中含区间外样本；ND 版同时覆盖带权与不带权。
  - 断言都用容差，避免再引入运算顺序陷阱。
- **R-c2（`normed` 仍可用，两处）**
  - 公开依据：base 两处 `normed` 文档，6 个公开测试，以及"不要改测试"的提示；上游后来补的 `test_density_via_normed` 作佐证（§10）。
  - 改动：每个文件新增一个 `test_normed_still_accepted`，只断言 `normed=True` 返回与 `density=True` 相同的密度。
  - 不限定是否告警：用 `suppress_warnings` 放行 Deprecation / PendingDeprecation / VisibleDeprecation 三类告警。
  - 不测两者同传的行为：base 上没有公开依据；gold 抛错、`DEP` 告警，两者都应得 1。

```diff
diff --git a/r2e_tests/test_1.py b/r2e_tests/test_1.py
--- a/r2e_tests/test_1.py
+++ b/r2e_tests/test_1.py
@@ -273,6 +273,34 @@
         assert_array_equal(H, answer)
         assert_array_equal(xe, array([0., 0.25, 0.5, 0.75, 1]))
 
+    def test_density_outliers(self):
+        # Values outside the bins are not tallied; density=True still makes
+        # the integral over the binned range equal to 1.
+        x = array([0.5, 1.5, 1.5, 2.5, 10.0, -3.0])
+        y = array([0.5, 0.5, 2.5, 2.5, 10.0, 1.0])
+        bins = [[0, 1, 3], [0, 2, 3]]
+        H, xed, yed = histogram2d(x, y, bins, density=True)
+        area = np.outer(np.diff(xed), np.diff(yed))
+        assert_array_almost_equal((H * area).sum(), 1.0)
+        counts = histogram2d(x, y, bins)[0]
+        assert_array_almost_equal(H, counts / counts.sum() / area)
+
+    def test_normed_still_accepted(self):
+        # The documented `normed` keyword keeps returning the density
+        # (a deprecation warning is acceptable).
+        x = array([1, 2, 3, 1, 2, 3, 1, 2, 3])
+        y = array([1, 1, 1, 2, 2, 2, 3, 3, 3])
+        bins = [[1, 2, 3, 5], [1, 2, 3, 5]]
+        with np.testing.suppress_warnings() as sup:
+            sup.filter(DeprecationWarning)
+            sup.filter(PendingDeprecationWarning)
+            sup.filter(np.VisibleDeprecationWarning)
+            H = histogram2d(x, y, bins, normed=True)[0]
+        answer = array([[1, 1, .5],
+                        [1, 1, .5],
+                        [.5, .5, .25]])/9.
+        assert_array_almost_equal(H, answer, 3)
+
 
 class TestTri(object):
     def test_dtype(self):
diff --git a/r2e_tests/test_2.py b/r2e_tests/test_2.py
--- a/r2e_tests/test_2.py
+++ b/r2e_tests/test_2.py
@@ -743,3 +743,33 @@
         hist_dd, edges_dd = histogramdd((v,), (bins,), density=True)
         assert_equal(hist, hist_dd)
         assert_equal(edges, edges_dd[0])
+
+    def test_density_outliers(self):
+        # Values outside the bins are not tallied; density=True still makes
+        # the integral over the binned region equal to 1, with and without
+        # weights.
+        x = np.array([0.5, 1.5, 1.5, 3.0, -1.0, 0.5, 9.0])
+        y = np.array([0.5, 0.5, 2.5, 2.5, 0.5, -2.0, 9.0])
+        w = np.array([1.0, 2.0, 1.0, 3.0, 4.0, 5.0, 6.0])
+        bins = ([0, 1, 4], [0, 2, 3])
+        area = np.outer(np.diff(bins[0]), np.diff(bins[1]))
+        for weights in (None, w):
+            counts, _ = histogramdd((x, y), bins=bins, weights=weights)
+            hist, _ = histogramdd((x, y), bins=bins, weights=weights,
+                                  density=True)
+            assert_almost_equal((hist * area).sum(), 1)
+            assert_allclose(hist, counts / counts.sum() / area)
+
+    def test_normed_still_accepted(self):
+        # The documented `normed` keyword keeps returning the same density
+        # as `density=True` (a deprecation warning is acceptable).
+        v = np.arange(10)
+        bins = np.array([0, 1, 3, 6, 10])
+        with suppress_warnings() as sup:
+            sup.filter(DeprecationWarning)
+            sup.filter(PendingDeprecationWarning)
+            sup.filter(np.VisibleDeprecationWarning)
+            hist_normed, edges = histogramdd((v,), (bins,), normed=True)
+        hist, _ = histogram(v, bins, density=True)
+        assert_allclose(hist_normed, hist)
+        assert_equal(edges[0], bins)
```

- `expected_output.json` 同步新增 4 个键，均为 PASSED，合计 82 键；新键不撞键：`TestHistogram2d.test_density_outliers`、`TestHistogram2d.test_normed_still_accepted`、`TestHistogramdd.test_density_outliers`、`TestHistogramdd.test_normed_still_accepted`。
- 输入的手算结果：
  - 2D 用例：区间内 4 点，计数 [[1,0],[1,2]]，面积 [[2,1],[4,2]]，gold 积分为 1；`DEG` 以 6 为分母，积分 4/6。
  - ND 用例：不带权时区间内计数 [[1,0],[1,2]]；带权时为 [[1,0],[2,4]]；面积 [[2,1],[6,3]]，gold 两种情况积分都为 1。`DEG` 不带权时以全部 7 个样本为分母，积分 4/7；带权时以全部权重 22 为分母，积分 7/22。
- 可选 T3 扩展，不在本轮，待复核决定：在 2D 离群点用例中也传入非均匀权重，可顺带覆盖 `histogram2d` 带权的位置参数转发。它属于另一个窄问题，需要单列公开依据（`twodim_base.py:566-570`）。

### B2 R-b（条件：`ORD` 实跑确认只错这一个键时才做；须在 B1 之后应用）

```diff
diff --git a/r2e_tests/test_2.py b/r2e_tests/test_2.py
--- a/r2e_tests/test_2.py
+++ b/r2e_tests/test_2.py
@@ -741,7 +741,7 @@
         bins = np.array([0, 1, 3, 6, 10])
         hist, edges = histogram(v, bins, density=True)
         hist_dd, edges_dd = histogramdd((v,), (bins,), density=True)
-        assert_equal(hist, hist_dd)
+        assert_allclose(hist, hist_dd)
         assert_equal(edges, edges_dd[0])
 
     def test_density_outliers(self):
```

- 理由："与一维逐位相同"是运算顺序带来的实现约束，没有公开依据；`assert_allclose`（rtol 1e-7）仍能区分任何语义错误。例如不除格宽会得到 [0.1,0.2,0.3,0.4]，与 [0.1]*4 相差很大。

### B3 修订后的预计验收矩阵

| 候选 | 修订前 | 只做 R-c | R-c＋R-b |
| --- | --- | --- | --- |
| noop | 0（72/78） | 0（74/82：6 个原目标键＋2 个 `test_density_outliers` 失败；`normed` 两键在 base 上通过） | 0 |
| gold（正对照） | 1 | 1 | 1 |
| `DEG` | 1 | 0（2 个 `test_density_outliers`） | 0 |
| `REN` | 1 | 0（2 个 `test_normed_still_accepted`） | 0 |
| `DEP` | 1 | 1（告警被放行） | 1 |
| `ORD` | 0（1 键） | 0（同一键） | 1 |

## 附录 C：浮点核算（本机纯 Python，不导入项目代码）

- 一维密度的顺序 `n/db/n.sum()` 得 `[0.1, 0.1, 0.1, 0.1]`；`ORD` 的顺序 `n/s/db` 得 `[0.1, 0.1, 0.09999999999999999, 0.1]`；`n/(s*db)` 得 `[0.1]*4`。
- `test_simple` 的 ND 用例：gold 顺序 `1/2/1/1/6` 与 `ORD` 顺序 `1/6/2/1/1` 都等于 `1/12.`。
- `non_uniform_2d`：gold 与 `ORD` 两种顺序都精确等于 `1/64`。
- 带权缩放相等：`(2c)/(2s)/dx/dy == c/s/dx/dy`，`(2c)/dx/dy/(2s) == c/dx/dy/s`，10 万组随机值全部成立。

## 附录 D：40 项清单预映射（供 screening_record 使用，稀疏）

- pass：
  - 1：材料哈希一致。
  - 2：noop 的 `TypeError` 与题面一致。
  - 9：gold 改变了结果，并从 `/testbed` 导入。
  - 11：各阶段都不需要网络。
  - 13：约 320 MB、约 1 s。
  - 14：两轮加独立 runner 两次，结果一致。
  - 17：隐藏测试的恢复不覆盖解答。
  - 18：collected 78，summary 完整。
  - 19：78 键唯一。
  - 20：6 个键的失败来自目标行为。
  - 21：失败原因没有被总分隐藏。
  - 22：M3 独立 runner 的 gold 78 passed。
  - 27：gold 正确。
  - 29：可见材料不含答案（静态）。
  - 30：无网络，取不到答案。
- issue：
  - 5：X1。
  - 24：T1 风险，`ORD`。
  - 25：`DEG`、`REN`。
  - 26：`normed`、2D 带权、`density=False` 的回归保护缺失。
- unknown：
  - 3：实际消息没有捕获。
  - 8、10：解题侧待 devcheck。
- not_checked：15、31、33–36。
- not_applicable：7、12、37–40。
