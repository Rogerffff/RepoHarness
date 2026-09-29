# orange3__9b5494e2 独立复核初判（第一步，读主审产物之前）

- 角色：独立复核者（静态），2026-09-25。只做静态阅读和已有证据核对；没有运行项目代码或容器，没有改任何原件。下文的"执行证据"都是重读已有日志，不是独立重跑。
- 路径约定：`PUBLIC_DIR` = `runs/r2e_static_prep_20260924/v2/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040`，`PRIVATE_DIR` = 同目录的 `private/…`，`DEVCHECK` = `runs/r2e_actor_20260925/devcheck/orange3__9b5494e26f407b75e79699c9d40be6d`，`WT` = `PUBLIC_DIR/worktree`（都相对仓库根）。
- 当前材料摘要（本人用 `shasum -a 256` 复算本地文件与 4 份 current 日志）：`expected_output.json` = `cd034086…`，等于 `revisions.json` 的 `sha256_after`、`grading_bundle.json` 的 `expected_output_json_sha256`、`run_refs.json` 的 `current_material.expected_sha256`；`hidden_tests/test_1.py` = `99459c0d…`（= grading bundle）；隐藏测试树 `9a87bfe6…` 与 `run_tests.sh` `5dee57d9…` 分别等于日志里的 `RH2_SETUP_HIDDEN_TESTS_TREE` / `RH2_SETUP_ENTRY_SHA256`；`gold.patch` = `162ad8b4…` = 账本 `candidate.patch_sha256`；环境配方 `r2e_derive_v1+env_v2`（scipy 1.5.4）。
- 证据层级：【执行】已有运行日志或捕获；【解析】账本解析结果；【静态】源码与测试推断；【未知】。

## 0. 初判摘要

1. **材料与环境：当前条件下自洽。** `+env_v2` 派生镜像上 gold 13/13 两次、noop 11/13 两次（错配键 `test_auto_solver`、`test_probability`），同类两次日志除时间戳外逐字相同【执行】。修订 r2e-mr-020 只把两个回归键 `test_LogisticRegression`、`test_coefficients` 从 FAILED 改成 PASSED，没有改测试。两键在来源环境的失败确由 SciPy 1.7.3 × scikit-learn 0.22.2.post1 的 `.decode` 崩溃造成；其中 `test_LogisticRegression` 还是 CrossValidation 吞掉异常后读到未初始化内存才失败的。修订属于"恢复测试支撑"，没有弱化断言，也没有扩大需求【执行 + 静态】。
2. **主要问题是误拒：唯一新增的目标键 `test_auto_solver` 要求题面没有给出的接口约定。** 它要求 learner 接受字面量 `solver="auto"`；l2 和 `penalty=None` 映射到 `lbfgs`，l1 必须映射到 `liblinear`（同样支持 l1 的 `saga` 不算）；而且解析结果要体现在 `_initialize_wrapped()` 返回的 sklearn 估计器上。题面只要求"自动选择支持该 penalty 的 solver，使 `penalty='l1'` 不报错"。一种常见的最小修法是保留 `lbfgs` 默认值、只在 l1 时换 solver。它能修好题面原例，但 `test_auto_solver` 一定 FAILED，整题判 0。noop 日志已经实证 base 会把 `"auto"` 原样透传（`'auto' != 'lbfgs'`）。**误拒风险：高。** 至少一类常见的合理修法必然判 0；这类修法占多大比例未知。
3. **期望里的两个 FAILED 键**（`test_learner_scorer`、`test_learner_scorer_multiclass`）是死键。noop、gold、来源环境、`+env_v2` 和 M3 独立 runner 下，它们都以相同的断言值失败（`'chest pain'`、`'legs'`）。它们只取决于默认 l2 路径（lbfgs）的数值结果，与修复无关；遵守 `test_auto_solver` 映射的修法不会让它们翻转。改掉默认 l2 solver 的修法可能让它们翻转【未知，需实验】，但这类修法已经先被 `test_auto_solver` 判 0。失败根因还没定位。公开测试文件里这两键在 base 和 gold 下都失败，对 actor 是一个诱导点：顺手把它们修好反而判 0。
4. 题面描述的报错确实出现在 noop 目标键 `test_probability` 的失败原因里，逐字一致【执行】。题面没有泄漏修法。隐藏测试只有一个文件，不依赖仓库测试辅助代码，没有撞键。`test_probability` 的断言很弱。
5. **暂定处置：** 环境和材料可用；但需求与测试不符（隐藏接口），需要用户决定处置（选项见 §11）。**最值得先做的下一步：**在 `+env_v2` 派生镜像上用 RH2 评分跑一个非 gold 候选 C1：保留 lbfgs 默认，l1 时自动改用 liblinear，不引入 `"auto"`（见 §5.1）。预期题面原例修好，但得分为 0。

## 1. 实际读取范围

- **角色卡与方法：**`roles/reviewer_r2e.md` 全文。`roles/investigator_r2e.md` 只按"R2E 的评分口径""材料"两节取口径；这个文件很短，Read 一次显示了全文，其余几节我看到了，但没有作为依据。`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md` 读了全文。
- **PUBLIC_DIR：**`user_prompt.txt`、`environment_brief.md`、`public_bundle.json` 读了全文；`worktree_manifest.json` 只读顶层字段与 untracked 项，没有逐项读 files 表。
- **WT 源码：**
  - `Orange/classification/logistic_regression.py` 全文；
  - `Orange/base.py` 第 1–200 行、第 460–624 行；
  - `Orange/tests/test_logistic_regression.py`，与隐藏测试做了 diff；
  - `Orange/widgets/model/owlogisticregression.py` 全文；
  - `Orange/widgets/model/tests/test_owlogisticregression.py` 第 1–114 行；
  - `Orange/widgets/evaluate/utils.py` 第 40–75 行；
  - `Orange/preprocess/score.py` 第 158–218 行；
  - `Orange/evaluation/testing.py`，用 grep 定位第 27–45、201–215、545–568 行；
  - `Orange/tests/test_classification.py` 第 440–467 行；
  - `Orange/regression/linear.py` 第 36–52 行；
  - `Orange/classification/neural_network.py` 第 20–32 行；
  - 全仓 grep：`_initialize_wrapped`、`solver`、`penalty`、`LogisticRegressionLearner(`；
  - CHANGELOG 与 `doc/` 里 grep logistic / solver；
  - 确认仓库根目录与 `Orange/` 下没有 `conftest.py` / `pytest.ini`。
- **PRIVATE_DIR：**全部文件全文。
- **current 运行原件：**
  - `runs/r2e_t0_batch3_20260924/replay_b5/ledger_b5_noop.jsonl` 第 13、14 行和 `ledger_b5_gold.jsonl` 第 13、14 行，全字段；
  - 4 份 current `.eval.log` 全文，并把两次重复两两 diff。
- **superseded 运行原件：**
  - `runs/r2e_env_repair_20260924/_rerun2/eval_logs/` 下 gold 日志 `…rer_bf7cd2ce` 读了全文，noop 日志 `…rer_6d1b4b0a` 用 grep 摘要；
  - `runs/r2e_rf_20260923/remote/eval_logs_r2e/` 下两份日志用 grep 摘要；
  - M3 的 a1、a2 `test_output.txt` 用 grep 摘要；
  - superseded 账本行本身没有打开，只用了 `run_refs.json` 的摘要。
- **DEVCHECK：**
  - `orig/` 下读了 `devcheck_stdout.json`、`devcheck_stderr.log`、`prelaunch.json`、`activation_check.json`、`commands_with_preflight.json`、`post_run_facts_root.txt`、`bringup_artifacts/cc_version_observed.json`，以及 `captures/*.out` 全部；
  - `orig/stub/requests/messages_000.json` 只抽取了 user 内容和 system 里的关键词；
  - `private_gold/private_control.json`、`private_gold/stdout.log`；
  - 没有读 `attempt.json`、`stub_script.json`、`stub_log.json`、`harness/trajectory.jsonl`，以及其余 `messages_00x.json`。
- **按要求没有读：**
  - `OUTPUT_DIR` 里的其它文件（包括 `public_read.md`）；
  - 任何 `history/` 目录；
  - `docs/.../r2e_env_repair_20260924/`，包括修订引用的 `material_revisions/*.md` 与 `recipes/env_pins_v2.json`；
  - `runs/r2e_t0_batch2_20260924/diag_orange3/` 与 `runs/r2e_t0_batch3_20260924/dryrun_b3o/`；
  - 任何 `*review*` 目录；
  - `r2e_static_review_20260925/` 下的 README、`assignments.json`、`actor_devcheck.md`；
  - `runs/` 下的分析与汇总文件；
  - 其它题的材料。

## 2. 公开目标（只根据公开包）

- **题面**（`user_prompt.txt:4–20`）：`LogisticRegressionLearner(penalty='l1')` 在 iris 上报 `ValueError: Solver lbfgs supports only 'l2' or 'none' penalties, got l1 penalty.`（:16）。期望行为是"learner 自动选择支持所指定 penalty 的 solver，使 `penalty='l1'` 可用"（:19–20）。
- **公开代码事实：**
  - base 的默认值是 `solver="lbfgs"`（`WT/Orange/classification/logistic_regression.py:39`）。
  - `SklLearner.fit` 通过 `self._initialize_wrapped()` 构造 sklearn 估计器（`WT/Orange/base.py:547–555`）；NN learner 覆写了这个钩子（`WT/Orange/classification/neural_network.py:29–32`、`WT/Orange/regression/neural_network.py:16–17`）。所以这个钩子能靠读代码发现。
  - 控件不传 `solver`（`WT/Orange/widgets/model/owlogisticregression.py:73–84`）；`results_for_preview` 直接构造 `LogisticRegressionLearner(penalty="l1")`（`WT/Orange/widgets/evaluate/utils.py:58`）。这两个调用者都会随修复受益。
- **公开旧测试** `WT/Orange/tests/test_logistic_regression.py` 已经包含 `test_probability`（在 `iris[:100]` 上用 l1），可以用来复现。它与隐藏测试的唯一差异是隐藏测试新增了 `test_auto_solver`（diff 结果）。
- **公开材料里没有出现的内容：**
  - solver 的 `"auto"` 取值：只有同一签名里的 `multi_class="auto"`、Ridge 的 sklearn 原生 `solver='auto'`（`WT/Orange/regression/linear.py:44`）这类通用惯例；
  - l1 应该选 `liblinear` 还是 `saga`；
  - `penalty=None` 应该怎样处理。
  - docs 和 CHANGELOG 里 grep 都没有命中。

## 3. 隐藏测试的 13 个键（另有 1 个 SKIPPED）

| 键（`TestLogisticRegressionLearner.`） | 期望 | noop（current） | gold（current） | 角色 | 测什么（`hidden_tests/test_1.py` 行号） |
| --- | --- | --- | --- | --- | --- |
| `test_auto_solver` | PASSED | FAILED：`'auto' != 'lbfgs'`（noop log:35） | PASSED | **目标** | :135–153，用 `solver="auto"` 构造后，看 `_initialize_wrapped()` 返回值的 `solver` / `penalty` |
| `test_probability` | PASSED | FAILED：题面的 ValueError（noop log:106） | PASSED | **目标** | :60–64，在 `iris[:100]` 上用 l1 拟合；断言 `abs(p.sum(axis=1)-1).all() < 1e-6` |
| `test_LogisticRegression` | PASSED（修订前 FAILED） | PASSED | PASSED | 回归（修订键） | :21–27，默认 learner 做 2 折 CV，要求 0.8 < CA < 1.0 |
| `test_coefficients` | PASSED（修订前 FAILED） | PASSED | PASSED | 回归（修订键） | :109–113，系数长度 |
| `test_learner_scorer` | FAILED | FAILED（`'chest pain'`） | FAILED（同左） | 死键 | :66–71，argmax 属性名 |
| `test_learner_scorer_multiclass` | FAILED | FAILED（`'legs'`） | FAILED（同左） | 死键 | :88–100 |
| 其余 7 个 | PASSED | PASSED | PASSED | 回归 | 见下 |

其余 7 个回归键：
- `…Normalization_todo`（:55–58）：`normalize=True` 必须抛 TypeError，保护构造签名；
- `…scorer_feature`（:73–78）；
- `…multiclass_feature`（:102–107）；
- `…previous_transformation`（:80–86）；
- `test_predict_on_instance`（:115–120）；
- `test_single_class`（:122–127）；
- `test_sklearn_single_class`（:129–133，只测 sklearn 本身）。

`test_LogisticRegressionNormalization` 带 `@unittest.skip`（:29），不成键。

## 4. 需求—断言双向映射

| 公开要求 / 合理旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 证据 |
| --- | --- | --- | --- | --- |
| R1 题面原例：l1 能拟合、不报错 | `user_prompt.txt:8–11,19–20` | `test_probability`（只用 `iris[:100]` 二分类子集） | 部分：原例是全量 iris（3 类），隐藏测试没有覆盖；断言也弱 | noop 失败原因就是题面报错【执行】；DEVCHECK private_gold 在全量 iris 上 rc=0、`solver='liblinear'`【执行，root 身份】 |
| R2 自动选择支持该 penalty 的 solver | `user_prompt.txt:19–20` | `test_auto_solver`：`"auto"` 下 l2→`lbfgs`、None→`lbfgs`、l1→`liblinear`，经 `_initialize_wrapped()` 观察 | **冲突 / 超规格**：字面量、具体 solver 和观察点都没有公开依据 | §5.1 |
| R3 默认 l2 行为不变 | 合理旧行为 | `test_LogisticRegression`、`test_coefficients`、`test_predict_on_instance`、`test_single_class`、scorer 的三个 PASSED 键、`test_auto_solver` 的 l2 段；两个 FAILED 死键也把 l2 数值固定住了 | 覆盖 | 【执行】 |
| R4 构造签名不变 | 公开旧测试 | `…Normalization_todo` | 覆盖 | 【执行】 |
| R5 用户显式指定的 solver 被尊重 | 合理旧行为 | 无 | 缺失 | 【静态】 |
| R6 多类 + l1（原例本身） | `user_prompt.txt:10–11` | 无 | 缺失 | DEVCHECK 中 gold 通过 |
| R7 控件的 L1 选项、`results_for_preview` 可用 | 公开调用者 | 无：控件测试不在评分范围；base 与 gold 下都有 3 个无关失败 | 缺失 | `DEVCHECK/orig/captures/test_widget.out:120–123` |
| R8 共享基类、`solver='auto'` 的其它 learner（如 Ridge）不受影响 | `WT/Orange/regression/linear.py:42–44` | 无 | 缺失 | 【静态】 |

**反查：**`test_auto_solver` 的每条断言在题面里都没有对应，包括 `"auto"` 字面量、`liblinear`、`penalty=None`→`lbfgs` 且 `skl_clf.penalty is None`、以及 `_initialize_wrapped()` 这个观察点。其余键都能追到公开旧测试。

## 5. 误拒、漏测与错误回归

### 5.1 误拒（主要问题）

以下各候选都能修好题面原例（l1 可以拟合）；表中只看它们在 `test_auto_solver` 上的结果和预计得分。

| 候选 | `test_auto_solver` | 预计得分 | 依据 |
| --- | --- | --- | --- |
| gold：默认值改为 `"auto"`，在 `_initialize_wrapped` 里解析 | PASS | 1 | 【执行】 |
| A1：默认值改为 `"auto"`，在 `__init__` 里先解析，再 `self.params = vars()` | PASS：`vars()` 取到解析后的局部变量，base 的 `_initialize_wrapped` 原样透传 | 1 | 【静态】 |
| C7：通用规则"solver 不兼容或未知，就换成该 penalty 的默认 solver" | PASS（`"auto"` 被当作未知值替换）；前提是 None 分支不改写 `penalty` | 1 | 【静态】 |
| **C1**：保留 `"lbfgs"` 默认，l1 且 solver 不支持时改用 `liblinear`，不认识 `"auto"` | FAIL：`'auto' != 'lbfgs'`（与 noop 走同一路径，noop log:35） | **0** | 【静态 + 执行】 |
| C2：与 gold 结构相同，但 l1→`saga` | FAIL：`'saga' != 'liblinear'` | 0 | 【静态】 |
| C3：默认改为 `liblinear`（scikit-learn 0.22 以前的默认，l1、l2 都支持） | FAIL：l2 段 `'liblinear' != 'lbfgs'`；可能还会翻转两个死键【未知】 | 0 | 【静态】 |
| C4：`"auto"` 在 `fit` 覆写里解析，不经过 `_initialize_wrapped` | FAIL：直接调用 base 的 `_initialize_wrapped()` 得到 `"auto"` | 0 | 【静态】 |
| C5：默认 `solver=None` 表示自动，只认 None | FAIL：测试显式传入 `"auto"` | 0 | 【静态】 |
| C6：用字典映射但漏了 `None`，或把 `None` 规范成 scikit-learn 0.22 要求的 `'none'` | FAIL：KeyError，或 `'none' != None` | 0 | 【静态】 |

**结论：**测试接受 gold、A1、C7，拒绝 C1–C6；C1–C6 都满足题面文字。

- C1 是最直接的最小修法之一。
- `_initialize_wrapped` 能从公开代码发现，所以 C4 出现的可能性较低。
- 真正的核心隐藏要求是 `"auto"` 字面量和 `liblinear` 这一具体选择。
- 公开材料对它们有一定暗示：题面说 "automatically select"，同一签名里有 `multi_class="auto"`，`liblinear` 是 l1 的典型选择和历史默认值。所以强模型有机会猜对。
- 但评分在相当程度上测的是"能否猜中上游 API"，而不只是"是否修好 issue"。

### 5.2 漏测

- **`test_probability` 的断言很弱。**`.all()` 返回布尔值，所以断言实际只要求至少一行概率之和恰好为 1，基本等于"拟合和预测不抛异常"。不过 `test_auto_solver` 断言了 `penalty == "l1"` 和 `solver == "liblinear"`，挡住了"把 l1 偷换成 l2"这类蒙混。核心行为没有明显漏测。
- **未覆盖的回归面是 R5–R8。**例如：候选如果把 `"auto"` 解析写进基类 `SklLearner._initialize_wrapped`，会让 `RidgeRegressionLearner(solver='auto')` 拿到 `lbfgs`。scikit-learn 0.22 的 Ridge 没有这个 solver，但隐藏测试发现不了【静态，可能性低】。

### 5.3 错误回归

期望里的 PASSED 键在 base 与 gold 下都是 PASSED，没有发现把错误行为写成期望的键。两个 FAILED 死键见 §6(a)。

## 6. R2E 专项

### (a) 非 PASSED 键

**观测。**两键在所有已看条件下都以相同断言值失败：

| 键 | 失败断言 | current noop | current gold | 来源环境（rerun2 gold） | M3 a1 |
| --- | --- | --- | --- | --- | --- |
| `test_learner_scorer` | `'major vessels colored' != 'chest pain'` | log:49 | log:35 | log:177 | `test_output.txt:161` |
| `test_learner_scorer_multiclass` | `'aquatic' != 'legs'` | log:63 | log:49 | log:191 | `test_output.txt:175` |

R-f 的两份日志也相同。

**机制。**
- `_FeatureScorerMixin.score` 先做 `Normalize()`，再用默认 learner 拟合，取 `abs(coef)`（`WT/Orange/classification/logistic_regression.py:16–19`）。
- `LearnerScorer.score_data` 把派生列按原属性取 max（`WT/Orange/preprocess/score.py:163–188`）。
- 断言写死的是 argmax 对应的属性名。
- gold 的 `"auto"` 对 l2 仍然选 lbfgs，默认 l2 路径与 base 相同，所以 noop 和 gold 的结果一样。
- **与 SciPy 无关（静态推断）：**
  - 来源环境里这两键没有触发 `.decode` 崩溃；
  - `_check_optimize_result` 只有在 `result.status != 0` 时才调用 `.decode`（rerun2 gold log:156–164）；
  - 这说明 Normalize 之后 lbfgs 在 100 次迭代内收敛了；
  - 所以失败与 SciPy 无关，增大 `max_iter` 也不会改变它。

**根因【未知】。**假设：期望的属性名是按 liblinear/OvR 时代的结果写的。lbfgs 不正则化截距；zoo 上 `multi_class="auto"` 加 lbfgs 走 multinomial。这个假设还没验证。

**会不会惩罚正确修复？**
- 遵守 `test_auto_solver` 映射（l2→lbfgs）的修法不会改变默认 l2 数值，这两键仍是 FAILED，不受罚。
- 可能让它们翻转的只有以下超出题意的改动：
  - 改默认 l2 solver（C3）；
  - 改打分路径，例如让 `_FeatureScorerMixin.score` 固定用 liblinear；
  - 改 Normalize。
- 其中 C3 已经先被 `test_auto_solver` 判 0。

**诱导风险。**公开测试文件里这两键在 base（`DEVCHECK/orig/captures/test_lr.out:103–105`）和 gold（`DEVCHECK/private_gold/private_control.json` 的 `test_lr`）下都失败。actor 如果为了让整个文件变绿去改源码，就会判 0；只改公开测试文件本身不影响评分。

**结论。**这两个 FAILED 键不是独立的误拒来源，但它们把"不许修好这两个旧失败"写进了奖励。

### (b) 题面描述的报错是否出现在 noop 目标键里

是。
- current noop log:106 的 `ValueError: Solver lbfgs supports only 'l2' or 'none' penalties, got l1 penalty.` 与 `user_prompt.txt:16` 逐字一致。
- actor 身份下在全量 iris 上的结果相同（`DEVCHECK/orig/captures/mcve_statement.out:15`）。
- 另一个目标键 `test_auto_solver` 的 noop 失败是 `'auto' != 'lbfgs'`（log:35），题面没有描述这一点。

### (c) 题面是否泄漏修法

否。题面只描述期望行为，没有给出 `"auto"`、`liblinear` 或 `_initialize_wrapped`；问题反而是规格不足（§5.1）。

### (d) 测试支撑与撞键

- 隐藏测试只有 `test_1.py` 加一个空的 `__init__.py`。
- 它只导入 Orange 公共 API、numpy 和 sklearn，不导入仓库测试模块的辅助代码。
- 数据集 `iris`、`heart_disease.tab`、`zoo` 通过包内的 `WT/Orange/datasets/` 解析，文件都在；搬迁到 `r2e_tests/` 不影响。根目录 `datasets` 是镜像里指向 `Orange/tests/datasets/` 的软链（manifest）。
- 仓库没有 conftest 或 pytest 配置。
- 单个文件，不会撞键。公开的同名类在 `Orange/tests/` 下，评分时不会被收集。

### (e) 时间、随机、资源敏感

- CrossValidation 默认 `random_state=0`（`WT/Orange/evaluation/testing.py:556`）。
- liblinear 在 `random_state=None` 时用全局 RNG 打乱数据，只影响 `test_probability`，而它的断言很弱。
- `test_auto_solver` 不做拟合。
- 测试约 1.8 s，峰值内存约 1.19 GB（账本 `test_seconds`、`mem_peak_mb`），远低于 4 GiB 限额。
- **对数值环境敏感：**
  - `test_LogisticRegression` 中，lbfgs 在未标准化的 heart_disease 上 100 次迭代不收敛（`DEVCHECK/orig/captures/test_lr.out:89–93` 的 ConvergenceWarning），只是靠 0.8 < CA < 1.0 的宽区间通过；
  - 两个死键同样依赖 scipy / sklearn / numpy 的具体数值；
  - 这些键只在固定的 `+env_v2` 下稳定：current 的 noop 和 gold 各两次，逐字相同。

### (f) 修订 r2e-mr-020

- **修订范围：**只把期望映射里两个键从 FAILED 改为 PASSED（`PRIVATE_DIR/revisions.json:5–33`，`revised_file: null`）。修订前后隐藏测试树摘要相同：superseded 与 current 日志的 `RH2_SETUP_HIDDEN_TESTS_TREE` 都是 `9a87bfe6…`。
- **原来的 FAILED 从哪来【执行】：**
  - 来源环境里，`test_coefficients` 在 sklearn `utils/optimize.py:243` 抛出 `AttributeError: 'str' object has no attribute 'decode'`（rerun2 gold log:164–165）。
  - `test_LogisticRegression` 是同一个异常被 `WT/Orange/evaluation/testing.py:44–45` 吞掉之后，由 `np.empty` 分配的预测数组（:205）保留了未初始化的值（log:55 `6.89514049e-310`），随后 `CA` 报 "mix of binary and continuous targets"（log:97）。
  - 也就是说，来源期望里的这个 FAILED 取决于未初始化内存，本身就不可靠。
- **`+env_v2` 下的结果：**两键在 noop 和 gold 下都是 PASSED（current noop log:111、113；gold log:56、59）；actor 侧也看到 scipy 1.5.4（`DEVCHECK/orig/captures/env.out:6`）。
- **判断：**修订让评分更严格（多了两个必须 PASSED 的键），不弱化断言，也不扩大需求。**同意这项修订。**
- **成立条件：**评分必须用 `r2e_derive_v1+env_v2` 派生镜像（账本 `overlay.recipe_id`，`image_ref` 以 `…-r2e_derive_v1e2` 结尾）。如果在来源镜像上评分，gold 会因为这两键判 0。
- **没有核对：**修订引用的 E17 诊断和 dryrun_b3o 的三次试跑（按要求没读）；这里只用 current 的两次正式运行代替。

## 7. gold 检查

- **题面原例修好了：**`DEVCHECK/private_gold/private_control.json:11`，估计器为 `penalty='l1'`、`solver='liblinear'`。注意这个对照是以 root 身份运行的（:7）。
- **改动范围：**只改了 `Orange/classification/logistic_regression.py`（账本 `projection.included_paths`），没有测试路径，也没有无关改动。apply 时有一条 "new blank line at EOF" 空白警告（:26），无害。
- **行为变化与未测回归：**
  - 默认 `solver` 从 `"lbfgs"` 改成 `"auto"` 后，`learner.params['solver']` 和模型的 `params` 显示 `'auto'`，而不是实际使用的 solver（`WT/Orange/base.py:544` 把 learner params 挂到模型上）。repr 往返测试不受影响：DEVCHECK 的 gold 对照里 `test_regress` 5 passed。
  - 用户显式指定 `solver="lbfgs", penalty="l1"` 时仍然报错。这是尊重用户的显式选择，合理。
  - `"elasticnet"` 在 `"auto"` 下仍选 lbfgs，会失败。但这个 learner 没有 `l1_ratio` 参数，elasticnet 本来就用不了，超出题意。
  - `penalty=None` 在 scikit-learn 0.22.2.post1 拟合时会被拒绝（这个版本要求字符串 `'none'`）。gold 和测试都只保证构造阶段。
  - 多类 + l1 走 liblinear 的 OvR。用户显式指定 `multi_class="multinomial"` 加 l1 时会被 liblinear 拒绝；这没有测试，也超出题意。
- **结论：**gold 满足公开要求，没有看到有害回归。它是可接受的实现之一，不是唯一答案（§5.1）。

## 8. 运行证据核对（按条件区分）

| 条件 | 来源 | 结果 |
| --- | --- | --- |
| current 评分：agent 施加补丁、评分用户 54322、2 CPU / 4 GiB、断网、派生镜像 `f27e31c6…`、`r2e_derive_v1+env_v2` | `ledger_b5_noop.jsonl:13–14`、`ledger_b5_gold.jsonl:13–14` 与对应 4 份 eval.log | noop 11/13 两次；gold 13/13 两次；同类两次日志只差时间戳 |
| superseded：来源版材料、来源环境 scipy 1.7.3 | rerun2 与 R-f 的日志 | 在来源版期望下 gold 13/13；四个非目标键的失败原因见 §6(f) |
| independent_reference：M3，来源镜像 | a1、a2 的 `test_output.txt` | 与 superseded 相同：4 failed（:192–195）；`test_auto_solver`、`test_probability` PASSED |
| actor devcheck：正式启动路径 + 真 Claude Code 2.1.205 + 桩模型，agent 54321，与评分同一镜像 ID | `DEVCHECK/orig` | preflight 全部 ok；scipy 1.5.4；题面原例复现；公开测试文件 3 个失败 |
| 私有 gold 对照：同一镜像的一次性容器，root 身份 | `DEVCHECK/private_gold` | 原例修好；公开测试文件剩 2 个无关失败；控件测试的 3 个无关失败不变 |

DEVCHECK 不是评分结果；私有 gold 对照是 root 身份，不等于 agent 身份下的 gold 行为。

## 9. 开发条件（actor）

- **devcheck 实测**（经 Claude Code Bash，agent 54321；派生镜像 `sha256:f27e31c6…`，与评分用的是同一镜像，`devcheck_stdout.json` 中 `image_is_overlay_derived_id: true`）：
  - `python` 是 `/testbed/.venv/bin/python` 3.7.9；Orange 从 `/testbed` 导入，所以改纯 Python 文件立即生效，不需要构建；
  - sklearn 0.22.2.post1 / scipy 1.5.4；
  - pip 24.0 存在，但网络不通；
  - `/testbed` 属主是 54321，可写；
  - HEAD 为 `43f086f0…` 且没有后继提交，隐藏测试不可见（preflight 全部 ok）；
  - `/rh2/bash_env` 对 agent 不可写。
- **复现与验证命令**（都已在 devcheck 里跑通）：
  - 题面原例：`python -c "…LogisticRegressionLearner(penalty='l1')(Table('iris'))…"`；
  - `python -m pytest Orange/tests/test_logistic_regression.py`：base 下 3 个失败（2 个无关的 scorer 测试 + 目标 `test_probability`），打上 gold 后剩 2 个无关失败。
- **噪声：**
  - lbfgs 的 ConvergenceWarning（`test_lr.out:89–99`），评分时被 `-W ignore` 屏蔽；
  - 控件测试需要 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum` 前缀，但因为 orangewidget 版本不匹配（`test_widget.out:115` 的 `@gui.deferred` 提示），base 与 gold 下都有 3 个无关失败，不能用来验证 L1 选项。
- **缺口与待验：**
  - devcheck 首个请求里只有 devcheck 指令（`orig/stub/requests/messages_000.json`），**没有捕获真实题面与提示词的渲染**。
  - `public_hints` 里"conda 已激活、pip 可用、测试文件会被重置"这些说法对 R2E 不成立（环境卡 §2 E09）；actor 实际收到的内容待验。
  - 环境卡 §2 写的是正式 actor 取来源镜像；这次 devcheck 用的是派生镜像，但正式 rollout 是否一律如此，不在本次静态范围内。如果 actor 跑在来源镜像上，它会看到修订键的 `.decode` 失败，并且能读到 `/r2e_tests`。
- **提交边界：**只需改 `Orange/classification/logistic_regression.py`。R2E 评分只替换 `r2e_tests/` 和 `run_tests.sh`；候选对公开测试文件的改动会保留，但不参与收集。

## 10. 八方面覆盖小结

| 方面 | 已查 | 未查 / 缺项 |
| --- | --- | --- |
| 公开需求 | 题面、公开代码与调用者、docs / CHANGELOG 的 grep | actor 实际渲染的题面与提示词（待验） |
| 材料与初始问题 | base 与 HEAD、gold 应用、摘要一致性、noop 的失败位置 | 修订的证据目录（按要求未读） |
| 测试是否测到要求 | 13 个键全读，断言与 helper 追到源码 | 没有运行任何替代候选 |
| 是否误拒 | §5.1 中九个候选的静态推演 | 需要 CPU 定点实验（C1、C2） |
| 回归与 gold | 调用者（控件、预览、NN 钩子、Ridge），gold 的行为变化 | 没有全仓穷举 |
| 开发条件 | devcheck 全部 captures、环境卡 | 真实题面的渲染 |
| 交付与评分边界 | R2E 替换范围、conftest / pytest 配置、`included_paths` | 平台级的 conftest 注入等沿用既有审查，未逐题复核 |
| 题目关系与用途 | — | 同仓其它题未查（按要求不读其它题） |

## 11. 疑点、未知与最小实验（建议队列）

1. **【首要】C1 反例。**在 `+env_v2` 派生镜像上用 RH2 评分跑这样一个补丁：保留 `solver="lbfgs"` 默认，在 `LogisticRegressionLearner._initialize_wrapped` 里，当 `penalty=="l1"` 且 solver 不支持 l1 时改用 `liblinear`。预期：题面原例和公开的 `test_probability` 都通过，但 RH2 reward 为 0，只有 `test_auto_solver` 错配。可以顺带跑 C2（l1→`saga`）。
2. **C3 实验，用来定位死键根因。**同样条件下评分"默认改为 liblinear"的候选，看两个 FAILED 死键是否翻转为 PASSED，以检验"期望属性名按 liblinear/OvR 写成"的假设。
3. **需要用户决定的处置选项**（不在复核者权限内）：
   - **(i) 公开规格修订：**在题面补一句"新增 `solver="auto"` 并设为默认：l1 用 `liblinear`，其余（包括 `penalty=None`）用 `lbfgs`"。代价是把实现方案写进了题面。
   - **(ii) 测试标准修订：**改成行为断言，接受任一支持 l1 的 solver，不依赖 `"auto"` 字面量，同时保留"默认 l2 不变"的检查。
   - **(iii) 保持原样：**只作为带"隐藏接口 / API 猜测"标签的诊断题，解释基座结果时剔除这个因素。
4. **真实 actor 的题面与提示词渲染**待捕获核对，devcheck 没有覆盖。
