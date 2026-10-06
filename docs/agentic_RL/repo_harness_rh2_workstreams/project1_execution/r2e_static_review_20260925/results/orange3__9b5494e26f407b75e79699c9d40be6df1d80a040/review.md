# orange3__9b5494e2 独立复核（第二步：核对主审产物）

> **2026-09-25 协调者更正（按 Codex 复核 r2e_static_actor_review_20260925/README.md）**：§3.5"原例能跑通、test_probability 通过、只错 test_auto_solver 就记为接口不符"改为只标'疑似接口不符'：失败键模式只用来筛出'疑似规格争议'的待复核样本：保留原始 reward，逐一核对候选是否满足公开要求、是否破坏受影响的旧行为，核实后才标'合理误拒'，不能按失败位置自动免除能力失败。 反例是本批真实评分 W1（把用户指定的 penalty='l1' 静默换成 l2），它也只错 test_auto_solver（12/13），但没有满足题意，必须仍算错误修复。V1 / V3 的合理误拒证据较强；V4 / V5 评分已测，题面原例能否修好是推断。 以下原文保留不改。

- **角色：**独立复核者（静态），2026-09-25。第一步封存稿 `reviewer_initial.md` 未改。
- **本步没有做的事：**没有运行项目代码或容器，没有修改任何原件。
- **"执行证据"的含义：**指协调者已取得的真实 RH2 评分账本和日志。我只是重读，不算独立重跑。

路径缩写（均相对仓库根）：

| 缩写 | 路径 |
| --- | --- |
| `PUB` | `runs/r2e_static_prep_20260924/v2/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040` |
| `PRIV` | 同一题的 `private/…` 目录 |
| `B5` | `runs/r2e_t0_batch3_20260924/replay_b5` |
| `DC` | `runs/r2e_actor_20260925/devcheck/orange3__9b5494e26f407b75e79699c9d40be6d` |
| `GR` | `runs/r2e_actor_20260925/grader` |
| `W(x)` | `runs/r2e_static_prep_20260924/v2/public/orange3__x…/worktree`，即其它 orange3 题的公开工作树 |

## 0. 结论

| 主审主张 | 复核结论 | 决定性依据 |
| --- | --- | --- |
| **P1 接口被钉死**：`test_auto_solver` 把四项接口细节变成得分条件——`"auto"` 取值、私有 `_initialize_wrapped()` 返回时已解析、l1 必须用 `liblinear`、`penalty=None` 原样透传；满足题面的合理替代解会判 0 | **同意，证据升级为执行级**：V1、V3 已在真实 RH2 上各判 0。V4、V5 仍是静态推断 | §2.1 |
| **P2 跨题暴露**：另外 5 道 orange3 题的公开 base 逐字含本题 gold 与目标测试 | **同意**，已逐文件复核 | §2.3 |
| **P3 死键**：两个 FAILED scorer 键是上游过时期望，不是环境问题 | **同意结论，修改证据表述**。"代码相同"应改为"系数计算路径上的代码实质相同"：还有几处主审没列的差异，要么不在这条路径上，要么只影响舍入。因果链最后一环（liblinear/OvR 能否复现旧期望值）要等 V7 实跑 | §2.2 |
| 能把死键翻成 PASSED 的，只有 V7 这类"默认改回 liblinear"的改动，而它本就过不了 `test_auto_solver` | **修改**：还有题外改动能通过 `test_auto_solver`、又可能翻转死键——只改打分路径所用的模型，或把默认 `multi_class` 改成 `"ovr"`。未验证 | §3.2 |
| 修订 r2e-mr-020 只恢复测试支撑，并绑定 `+env_v2` | **同意**，另补一条证据（见 §2.4） | §2.4 |
| check 25："没有能通过全部键的明显错误解" | **小修改**：存在能拿到 1 分的回归型错误解（静态推断），见 §3.1 | §3.1 |
| check 26："gold 保持 pickle" | **小修改**：私有对照没有跑 pickle 用例，这一点只能算静态推断 | §2.5 |
| check 14："无随机源" | **小修改**：gold 的 l1 路径用 liblinear，`random_state=None` 时从全局 RNG 取种子；断言很弱，不影响键的状态 | §2.5 |
| 处置：`needs_review`、只作 development_diagnostic、不作留出评测、先校准替代解再由用户定修订方向 | **同意** | — |

**需要显式保留的分歧**只有一处：死键还有哪些翻转路径（§3.2）。它需要实验解决，见 §7。

## 1. 本步读取范围

**本目录下：**
- `public_read.md`、`analysis_before_history.md`（第 1 行是协调者的来历注释）、`old_findings_delta.md`、`card.md`、`screening_record.json`，均读全文。

**历史引用（`runs/r2e_static_prep_20260924/v2/history/orange3__…/refs.json` 所列）：**
- 读全文：`findings.md`、`material_revisions/orange3__….md`、`repros/orange3__….py`。
- 历史 `screening_record.json`：读了 disposition / open_items、solver_conditions、issues、checks 摘要。
- `known_issues.json`：只读三个相关族。
- `decisions.md`：只 grep 了 E05/E09/E12/E14/E17/E19–E24/T0-6/T0-7 各行。
- `results_20260924.md`、`packages/p3/README.md`：只读 orange3 相关行。
- `facts.json`：只做了关键词抽查。
- 历史引用的 E17 诊断日志 `runs/r2e_t0_batch2_20260924/diag_orange3/*.test.log`：grep 了 6 份。

**协调者的新执行证据：**
- `GR/ledger_or_OR1.jsonl`、`GR/ledger_or_OR2.jsonl`（各 1 行，全字段）；
- `GR/eval_logs/` 下两份 orange3 日志（全文）；
- `GR/cands/orange3_9b54_OR{1,2}_*.patch`；
- `GR/orange3_mcve/OR{1,2}.{json,log}`；
- `GR/stdout_or_OR{1,2}.log`、`GR/run_grader_orange3.sh`。
- 另外本地复算了补丁与日志的 sha256，均与账本一致。

**为核主审新主张，另读了：**
- 另外 6 道 orange3 题公开工作树里的相关文件：LR 源码、LR 测试、打分与预处理模块、统计模块、数据文件（只做比对）；
- 本题公开工作树里的 `Orange/tests/test_classification.py`（类与用例清单、第 310–333 行）、`Orange/tests/test_util.py:43-60`、`Orange/preprocess/preprocess.py:150-175`、`Orange/regression/linear.py:1-47`、`requirements-gui.txt`。

**没有读：**
- 批次目录下的 README、`assignments.json`、`actor_devcheck.md`、`grader_candidates.md`；
- 其它题的私有材料；
- 历史引用未列出的审查目录。

## 2. 逐项核对主审的决定性主张

### 2.1 P1 接口被钉死：同意，已有执行证据

**逐项核对协调者的两次实跑：**

| 项 | OR1（= 主审 V1 = 我的 C1） | OR2（与主审 V3、我的 C2 同类） |
| --- | --- | --- |
| 补丁内容 | 保留默认 `"lbfgs"`；新增 `_initialize_wrapped`，当 penalty 为 l1 且 solver 为 lbfgs 时改用 liblinear | 默认改成 `"auto"`；`"auto"` 时 l1→`saga`，其余→`lbfgs` |
| 补丁 sha256 | `39648701…`，本地复算与账本 `candidate.patch_sha256` 一致 | `3d05c2c8…`，一致 |
| 评分条件 | `r2e_derive_v1+env_v2`，镜像 `f27e31c6…`，agent/54321 应用补丁，rh2grader/54322 跑测试，`deny_all` | 同左 |
| 结果 | reward 0，12/13，只有 `test_auto_solver` 不符（`GR/ledger_or_OR1.jsonl:1`） | reward 0，12/13，只有 `test_auto_solver` 不符（`GR/ledger_or_OR2.jsonl:1`） |
| 失败断言 | 第 1 块：`'auto' != 'lbfgs'`（eval log :36） | 第 3 块：`'saga' != 'liblinear'`（eval log :48）；前两块（l2、None）通过 |
| 目标键 `test_probability` | PASSED（:78） | PASSED（:90） |
| 题面原例（完整 iris，l1） | rc=0，`solver='liblinear'`（`GR/orange3_mcve/OR1.json:7`） | rc=0，`solver='saga'`，另有 sklearn ConvergenceWarning（`OR2.json:7`） |
| 公开 LR 测试文件 | 2 failed / 10 passed，与 gold 私有对照相同（`OR1.json:11`；`DC/private_gold/private_control.json:15`） | 同左（`OR2.json:11`） |

两份日志的 `RH2_SETUP_HIDDEN_TESTS_TREE`、`RH2_SETUP_ENTRY_SHA256` 都与当前材料一致（:5–6），日志 sha256 也与账本一致。

**这两次实跑补上了主审当时没有的一条事实：**
- 在 agent 能看到的公开信号上，V1、V3 与 gold 完全不可区分：题面原例都能跑通，公开 LR 测试文件的结果都是同样的 2 failed / 10 passed。
- 因此 agent 没有任何公开途径发现隐藏的接口要求。
- 结论：P1 从"静态推断 + noop 同型失败旁证"升级为"真实 RH2 执行（各 1 次，路径确定）"。

**误拒的严重程度应分层**（这是对主审的补充，不是分歧）：

| 替代解 | 误拒强度 | 理由 |
| --- | --- | --- |
| V1，以及同族的"拟合出错后回退到 liblinear" | 强 | 行为与 gold 几乎一样，唯一差别是不认识 `"auto"` 字面量。公开材料无法推出这一要求 |
| V4（在 `fit` 里解析） | 中 | `_initialize_wrapped` 钩子可以从 `Orange/base.py:547-555` 和 `neural_network.py:29-32` 读到 |
| V3（l1 选 saga） | 较弱 | 用默认预处理（不标准化）时，saga 在题面原例上会发 ConvergenceWarning（`OR2.json:7`），细心的实现者可能因此改选 liblinear。但题面只要求 "without errors"，警告不是错误，所以仍属误拒 |
| V5（`None` 分支） | 弱 | 只涉及测试里 `penalty=None` 这条题外输入 |

### 2.2 P3 两个 scorer 键是上游过时期望：同意结论，修改证据表述

**我逐文件复核了三点：**

1. **后续上游的新值正好是本题的实测值。**
   - `W(4014f248)/Orange/tests/test_logistic_regression.py` 与本题隐藏测试相比，只有 3 行不同（第 69、92、98 行）：
     - heart_disease 的首位特征：`'major vessels colored'` → `'chest pain'`；
     - 两栖类：`'aquatic'` → `'legs'`；
     - 爬行类：`'hair'` → `'aquatic'`。
   - 本题实测的失败值正是 `'chest pain'` 和 `'legs'`：`B5` 两次 gold，以及 OR1、OR2、E17 的 SciPy 1.4.1 / 1.5.4 与来源 1.7.3，都逐字相同。
   - 例如 `diag_orange3/orig_gold.test.log:161,175` 与 `s154_gold.test.log:19,33`。
2. **旧值属于 liblinear/OvR 时代。**更早的 `W(f237f968)` 默认是 `solver='liblinear'`、`multi_class='ovr'`（其 `logistic_regression.py:39-40`），它的公开测试与本题隐藏测试相比只少一个 `test_auto_solver`，断言值是同一组旧值。
3. **"代码与数据相同"需要改写。**
   - 与 `4014f248` 逐字节相同的文件：`heart_disease.tab`、`zoo.tab`、`iris.tab`、`preprocess/score.py`、`continuize.py`、`preprocess.py`（含 `SklImpute`）、`data/filter.py`、`statistics/util.py`、`basic_stats.py`。本题 base 加 gold 后的 LR 源码也与之相同。
   - 主审没有列出、但确实不同的文件如下。逐一看过，都不改变系数的计算结果，至多影响最后一位舍入：
     - `statistics/distribution.py`：方差由生成器求和改为 `np.dot(...)/np.sum(...)`，只在舍入层面有差别。`Normalize` 通过它取 sd（`normalize.py:49`）。
     - `preprocess/transformation.py`：只是 Indicator 类的重构，外加 `__eq__` / `__hash__`，变换本身未变。
     - `preprocess/impute.py`：不在 `SklImpute` 的数值路径上。`SklImpute` 直接用 sklearn 的 `SimpleImputer` 结果给 X 赋值（`preprocess.py:160-174`）。
     - `base.py`：`_get_sklparams` 改用 `inspect.signature`，结果等价；另有预测阶段的概率扩展和新增的 CatGB/XGB 学习器；`fit` 与 `preprocess` 没变。
     - `remove.py`、`data/table.py`、`data/util.py`：只是元数据、跨步切片行数和命名上的改动。

   所以准确的说法是："系数计算路径上的代码实质相同，数据字节相同"，而不是"代码完全相同"。

**判断：**
- 上游在代码和数据实质不变的情况下改写了期望值，而本题环境下得到的恰好是改写后的值。所以"默认 solver 换成 lbfgs 后，测试期望没有同步更新"是高置信的解释。
- 我第一步的假设（期望值是按 liblinear/OvR 校准的）也由此得到佐证。
- **仍缺一环：**本环境下 liblinear/OvR 能否复现那组旧值。V7 实跑可以补上这一环。
- 对评分的含义：死键性质成立。历史 open item "原因未定位"可以改记为"已解释（跨 base 源码对照 + 多环境运行）"。但"对所有候选恒为 FAILED"这一点只能收窄，不能关闭，见 §3.2。

### 2.3 P2 跨题暴露：同意，已复核

- **LR 源码：**在一份临时副本上对 base 应用 gold（`git apply`），与各题的 `Orange/classification/logistic_regression.py` 逐字节比较：
  - `4014f248`、`22e98f8f`、`50f6a758`、`f5026689` 完全相同；
  - `c3fb72ba` 只多一行 `supports_weights = True`。
- **`test_auto_solver`：**从 5 份公开测试里抽出该函数，sha256 与隐藏测试中的完全一致（均为 `ff603aac…`）。
- **scorer 断言：**5 份公开测试里的首位特征断言都已是 `'chest pain'`。
- **小出入：**主审括注的版本号与各题 `setup.py` 的 `VERSION` 不一致（例如 `4014f248` 记为 3.27.1，`setup.py` 是 3.28.0）。我推测主审用的是 CHANGELOG 的发布号，而 `setup.py` 写的是下一个开发版号。这不影响结论。
- **补充：**这类"早题的修复出现在晚题的 base 里"的关系应在池级双向登记。`f237f968` 的 base 比本题更早，本题公开树里是否含有它的修复，属于那道题的审查范围，本步未查。

### 2.4 修订 r2e-mr-020：同意，补一条证据

- 我把修订逆向套回当前期望，重算得到 `9645a5c3…`，与 `revisions.json` 的 `sha256_before` 一致。主审的哈希核对成立。
- **补充证据：**来源环境下 `test_LogisticRegression` 的 FAILED 取决于未初始化内存。5 次运行里 `y_pred` 的首值各不相同：

  | 运行 | 位置 | 首值 |
  | --- | --- | --- |
  | R-f gold | :55 | `6.43005572e-310` |
  | 中央复跑 gold | :55 | `6.89514049e-310` |
  | M3 a1 | :39 | `6.65747641e-310` |
  | M3 a2 | :39 | `6.13176461e-310` |
  | E17 orig_gold | :39 | `6.27488947e-310` |

  这说明旧期望的 FAILED 本身依赖不确定的内存内容。修订把它改成"两边都 PASSED 的回归键"，是恢复测试支撑，不是弱化断言。
- 主审还指出一个旧期望下的反向激励："在旧期望下，让 lbfgs 收敛的候选会因把这两键修成 PASSED 而判 0"（`analysis_before_history.md` §6(f)）。这条成立，我第一步没有写到。
- 残余风险与主审一致：在任何没有 `+env_v2` 的镜像上评分，gold 会得 0。

### 2.5 其余主张的小修正

| 位置 | 原文 | 修正 |
| --- | --- | --- |
| `screening_record.json` check 26 | "gold 保持默认 repr、pickle 与默认 l2 路径"，证据引私有对照 | 私有对照的 `test_regress` 只有 5 个用例：`test_util::test_reprable`、`SklTest` 3 个（`test_classification.py:310-331`）、`LearnerReprs`（:440-463）。pickle 用例 `LearnerAccessibility.test_all_models_work_after_unpickling`（:393）没跑。"gold 保持 pickle"改标静态推断；这个推断很可能成立，因为 params 里只多了字符串 `'auto'` |
| check 14 | "CV random_state=0，无随机源" | CV 本身确实固定。但 gold 的 l1 路径走 liblinear，`random_state=None` 时从全局 NumPy RNG 取种子（按 sklearn 0.22 源码记忆，未核对），只影响 `test_probability`，其断言只要求任一行概率和恰为 1。键状态不受影响，改成"有一处随机源但不影响键状态"即可 |
| check 16 | "非 gold 候选的交付未实跑" | OR1、OR2 已由 agent/54321 用 `git_apply` 施加，投影只含 LR 文件，评分正常完成。可以更新 |
| check 24 / issues[0] 的 `evidence_level` | "候选未实跑" | 改为"V1、V3 真实 RH2 各 1 次 reward 0（12/13，只有 `test_auto_solver` 不符）；V4、V5 待跑" |

## 3. 反查主审可能没想到的范围

### 3.1 漏测：回归型错误解可以拿满分（静态）

**具体候选：**
- 把 `"auto"` 的解析写进基类 `SklLearner._initialize_wrapped`（`Orange/base.py:547`）：`"auto"` → l1 用 liblinear，否则用 lbfgs；
- 同时把 LR 的默认值改成 `"auto"`。

**后果：**
- 隐藏 13 键全过，得 1 分。
- 但 `RidgeRegressionLearner` 的默认值本来就是 sklearn Ridge 自己的 `solver='auto'`（`Orange/regression/linear.py:42-44`）。它经 `LinearRegressionLearner.fit` → `SklLearner.fit` → `_initialize_wrapped`（:34-36）会拿到 `lbfgs`。
- 按 scikit-learn 0.22 源码记忆（未核对），0.22 的 Ridge 不支持 lbfgs，拟合会报错。
- 公开的 `Orange/tests/test_linear_regression.py` 能发现这个回归，但它不在评分范围内。

**评估：**可能性低，但它是"错误解得 1"的具体例子。check 25/26 应附这一条，不宜写"未发现"。

### 3.2 死键的翻转路径不止 V7（保留分歧，需实验）

- **两个死键分别受什么影响：**
  - `test_learner_scorer` 是二分类，只受默认 l2 模型的求解器和正则化影响；
  - `test_learner_scorer_multiclass` 还受 `multi_class` 影响。
- **`test_auto_solver` 挡不住的两类改动：**它只检查 `_initialize_wrapped()` 返回值的 `.solver` 和 `.penalty`，所以下面两类改动都能通过它：
  - 只改打分路径，例如让 `_FeatureScorerMixin.score`（`logistic_regression.py:16-19`）另用 liblinear/OvR 学习器；
  - 把默认 `multi_class` 改成 `"ovr"`。
- **后果：**如果这类改动恰好复现旧期望值，死键会翻成 PASSED，整题判 0。
- **与主审的分歧：**这两类都是题外改动。前一类会让特征得分与学习器自身的模型不一致，判 0 在行为上说得过去。但主审"只有 V7 且它本就得 0"的表述过强。我第一步写过"改打分路径"，主审前稿 §6(a) 也提到过 `multi_class`，而增量稿把范围收窄了。
- **怎样解决：**只要 V7 显示 liblinear/OvR 能让两键都翻转，前一类改动就同样会翻转。

### 3.3 公开读者的疑义能否从公开材料消除

| 疑义 | 能否消除 | 说明 |
| --- | --- | --- |
| A1：显式 `lbfgs` + `l1` 怎么办 | — | 本身不计分 |
| A3：所选 solver 在哪里可见 | 部分 | 钩子可以从代码读到；但 `"auto"` 字面量从公开材料无法推出，这正是 V1 被误拒的根因 |
| A2：l1 选 liblinear 还是 saga | 部分 | 实验者能观察到 saga 发出收敛警告 |

- 公开读者的疑义在本题**确实对应评分问题**，而且已有执行证据。它不只是"读者没看懂"。
- 公开读者有两处错误预判，主审都已纠正，我同意：公开 LR 测试文件修复后并非全部通过；控件测试因 orange-widget-base 漂移，在修复前后都失败（`requirements-gui.txt:2` 只有下限 `>=4.5.0`）。

### 3.4 主审是否先看答案再说"显然"

- 没有发现这种写法。
- 主审前稿表 2 把 `"auto"` 写成"可推知但非唯一"，把 liblinear 写成"常见选择但非唯一"；card 也明确说这些替代解"满足题面"。
- 唯一接近的一句是 "`penalty=None` → lbfgs：最简实现自然满足"。它在事实上成立，也注明了会失败的实现，可以接受。

### 3.5 用作诊断时的建议

- **失败分类：**如果本题原样进入 development_diagnostic，建议对每次失败补一个事后分类：题面原例能跑通、公开 `test_probability` 通过、且评分只错 `test_auto_solver` 时，记为"接口不符"，而不是"未修复"。否则基座统计会把 V1 类正确修复算作失败。
- **两种相反的混杂：**`solver="auto"` 存在于所有后续 Orange 发行版，也在池内另外 5 题的公开树里。所以命中接口既可能来自能力，也可能来自记忆（主审已提）。反过来，没命中也不代表没修好。本题的成败信号两头都被混杂，不宜作干净的探针。

## 4. 修订建议是否扩大原需求；"可探针"是否分开

### 4.1 三个修订方向

**(A) 题面最小补全**
- 不扩大需求（它就是上游修复的 API），但等于把测试写进题面。
- 如果不点名 `_initialize_wrapped`，V4 类和"在拟合时解析 / 出错回退"类仍会被误拒；点名又进一步泄漏实现。主审已写明这一点，我同意。

**(B) 测试改为行为级检查**
这是原则上最干净的方向。为便于用户决策，给一个可区分的草案（未验证，属于改 oracle，需 T0 决定并独立复核）：
- 键名仍用 `test_auto_solver`，期望仍是 PASSED，键集合不变；
- 断言 1：`LogisticRegressionLearner()(Table('iris')).skl_model.solver == "lbfgs"`。这是**旧行为的回归保护**，不是新需求；
- 断言 2：`m = LogisticRegressionLearner(penalty="l1")(Table('iris'))` 能拟合（这就是题面原例：三分类、完整 iris），并且 `m.skl_model.solver in ("liblinear", "saga")`、`m.skl_model.penalty == "l1"`。

预期各候选的结果：

| 候选 | 预期 |
| --- | --- |
| gold、P1、P2、V1、V3、V4、V5、回退式实现 | 接受 |
| W1（静默改成 l2） | 拒绝 |
| V7（默认改成 liblinear） | 拒绝：默认 l2 行为被改变，属于回归 |
| noop | 仍 FAILED，目标键性质不变 |

代价：隐藏测试树会变，需要按 E21/E24 的做法重建派生镜像，用 noop/gold 加上述候选重新校准。

**(C) 原样只作诊断**
可以接受，但需配合 §3.5 的失败分类。

### 4.2 另一个可选项（不是与主审的分歧）

- **做法：**把两个死键的断言按后续上游的新值改写（`'chest pain'` / `'legs'` / `'aquatic'`），让它们成为两边都 PASSED 的活回归键。
- **好处：**
  - 现在这两个 FAILED 键几乎没有回归信号：只有恰好复现旧值的改动会被罚；改成别的首位特征的改动不会被发现。
  - 改写后，任何改变默认 l2 打分结果的改动都会被抓到，判 0 的理由也变成"破坏旧行为"，而不是"修好了旧失败"。
- **代价：**
  - 需要 T0 决定并重建镜像；
  - 数值更脆（本题已固定 `+env_v2`）；
  - 必须先验证 zoo 多类测试后面的 6 条断言在本环境下也成立。本环境只观测到第一条断言，失败后后面的没有执行。
- **优先级：**低于 P1 的处理。主审建议"保持 FAILED 不修订"也可以接受。

### 4.3 "可探针"的分离

主审没有把本题列为探针候选：`usage` 是 development_diagnostic，`not_approved_for` 是 training 和 final_evaluation，并把真实消息渲染和正式链镜像选择单列为剩余条件。静态结论与剩余条件分得清楚，我同意。

## 5. 与我第一步初判的异同

| 类别 | 内容 |
| --- | --- |
| 被执行证据证实 | C1（=V1）、C2（=V3）判 0，失败断言与我第一步写的逐字一致；题面原例都能修好 |
| 升级 | scorer 死键根因：从我的"未知，假设按 liblinear/OvR 校准"，升级为"上游过时期望"（接受主审的跨 base 证据）。仍缺 V7 这一环 |
| 新增、我第一步不知道的 | P2 跨题暴露；旧期望下的反向激励（让 lbfgs 收敛反而判 0） |
| 保留 | 我第一步提出的三点——随机源说明、基类解析导致 Ridge 回归、改打分路径可翻转死键——主审都没有覆盖，本文分别作为 §2.5、§3.1、§3.2 保留 |
| 我初判的不足 | 我没有把"公开信号与 gold 不可区分"作为误拒严重度的依据（当时还没有 OR 数据）；也没有给误拒强度分层（本文 §2.1 补上） |

## 6. 未解决的分歧（显式保留）

1. **死键的翻转路径是否只限于 V7。**主审认为是；我认为只改打分路径、或改默认 `multi_class` 的题外改动也可能翻转，且能通过 `test_auto_solver`。区分实验见 §7 第 1、2 项。
2. 其余各处都是证据表述上的小修正（§2.2、§2.5、§3.1），不影响处置。

## 7. 最小后续实验

1. **V7（主审候选，协调者已安排）：**记录两个死键是否都翻成 PASSED。
   - 若翻转：因果链闭合，同时证明改打分路径也会翻转，§6 第 1 项按我的判断收口。
   - 若不翻转：过时期望的结论仍成立（依据是上游新值与实测一致），但"旧值来自 liblinear/OvR"要降级为未证。
2. **只在 V7 翻转时才需要：**跑"gold + 默认 `multi_class="ovr"`"，看多类死键是否单独翻转。
3. **P1、P2 正对照（协调者已安排）：**预期 reward 1，证明测试并非只认 gold 的字面写法。
4. **可选，低优先级：**跑"基类解析 `"auto"`"候选（§3.1），同时记录 RH2 得分和公开 `Orange/tests/test_linear_regression.py` 的结果，把漏测从静态推断变成执行证据。
5. **用户决策之后：**如果选 (B)，按 §4.1 的候选表做正反校准，再重建镜像并跑 noop/gold 各两次。

对处置决策而言，现有证据（V1、V3 实跑判 0）已经足够。上面这些实验用于收口证据和选修订方向，不阻塞用户决策。
