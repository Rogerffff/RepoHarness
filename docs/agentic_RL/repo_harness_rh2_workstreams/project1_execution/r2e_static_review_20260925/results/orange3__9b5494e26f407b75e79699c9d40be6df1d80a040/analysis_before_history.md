<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# orange3__9b5494e26f407b75e79699c9d40be6df1d80a040：私有主审分析（读历史前）

2026-09-25 · R2E 私有主审（静态审查）。**暂定稿，写于打开任何历史调查之前。** 没有运行项目代码、没有开容器或连远端；只读了材料原件、账本行、原始日志和协调者给的 devcheck 目录。

路径缩写（均相对仓库根）：
- `PUB` = `runs/r2e_static_prep_20260924/v2/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040`
- `PRIV` = `runs/r2e_static_prep_20260924/v2/private/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040`
- `B5` = `runs/r2e_t0_batch3_20260924/replay_b5`（current 行）
- `DC` = `runs/r2e_actor_20260925/devcheck/orange3__9b5494e26f407b75e79699c9d40be6d`

## 0. 暂定结论

- **题目与环境：**
  - 题目目标清楚：`LogisticRegressionLearner(penalty='l1')` 不再因 lbfgs 不支持 L1 而报错，由学习器自动选一个支持该 penalty 的 solver。
  - 材料版本一致，noop 的目标键失败处正是题面那句报错。
  - 环境配方 `+env_v2`（SciPy 1.5.4）与修订 r2e-mr-020 核对成立。4 条 current 运行行都在 `+env_v2` 派生镜像上。
- **主要问题在评分口径：**
  - 目标键 `test_auto_solver` 把题面没写的 4 个接口细节变成得分条件：
    1. 接受 `solver="auto"` 这个取值；
    2. 调私有方法 `_initialize_wrapped()` 时就已完成解析；
    3. L1 必须选 `liblinear`；
    4. `penalty=None` 原样透传。
  - 以下合理修复都会判 0：不引入 `"auto"`（保留默认 lbfgs、遇 L1 自动换）、L1 选 `saga`、在 `fit` 时才解析。这是静态推断：代码路径很短，而且 noop 日志已给出同型失败。待 CPU 反例确认。
- **期望里剩下的两个 FAILED 键**（`test_learner_scorer`、`test_learner_scorer_multiclass`）：
  - 与本题无关，失败文本在 noop/gold、SciPy 1.7.3/1.5.4 下逐字相同。
  - 能通过 `test_auto_solver` 的实现，基本不会把它们翻成 PASSED。
  - 根因未定位：弱倾向于"上游在此提交就不一致"，也可能是其它依赖漂移，见 §6(a)。
- **暂定处置：**`needs_review`，理由是题意/测试争议。可作 development_diagnostic，但须附"接口被钉死"的说明。作 reward 前需要用户决定修订方向（§11）。

## 1. 材料与版本核对

| 项 | 事实 | 依据 |
| --- | --- | --- |
| base | `43f086f0bacc…`，与题面抬头一致；初态 diff 0 字节。未跟踪文件只有 `datasets`（软链到 `Orange/tests/datasets/`）、`install.sh`、`run_tests.sh` | `PUB/public_bundle.json`、`worktree_manifest.json`；`DC/orig/captures/env.out` |
| gold | 只改 `Orange/classification/logistic_regression.py`：默认 `solver="lbfgs"` 改为 `"auto"`；新增 `_initialize_wrapped` 覆盖（复制 params，`"auto"` 时 l1→`liblinear`，其余→`lbfgs`） | `PRIV/gold.patch` sha `162ad8b4…`，与 validation bundle、ledger `patch_sha256` 一致 |
| 隐藏测试 | `test_1.py` 等于公开的 `Orange/tests/test_logistic_regression.py` 加上新增的 `test_auto_solver`（diff 只有这一段）；`__init__.py` 为空 | 本地 diff；sha `99459c0d…` 与 grading bundle 一致 |
| 期望 | 13 键：11 PASSED，2 FAILED（两个 scorer 键）。当前文本 sha 本地重算为 `cd034086…`；把修订逆向套回，得到 `9645a5c3…`，与 `revisions.json` 的 `sha256_before` 一致；键集合与顺序不变 | 本地重算 |
| 入口 | `run_tests.sh` sha `5dee57d9…`，等于日志的 `RH2_SETUP_ENTRY_SHA256` | `B5` 日志头 |
| 目标键 | noop 与 gold 只在 `test_auto_solver`、`test_probability` 两键不同（noop FAILED → gold PASSED）。其余 9 个 PASSED 回归键和 2 个 FAILED scorer 键两边相同 | `B5` noop/gold 日志 |

## 2. 公开读者没有捕获的条件（第 1 步）

- **真实消息：**
  - `public_read.md` 依据的是静态渲染。
  - DC 捕获的真实 Claude Code 请求（`DC/orig/stub/requests/messages_000.json`）里，用户消息是桩指令"Devcheck run: …"，系统提示是 CC 默认提示，不含 public_hints，也没有 conda 字样。
  - 因此**实际任务消息（题面加 hints 的渲染）仍未捕获**。hints 里"conda 已激活"和"测试文件会被重置"的措辞是否进入真实 rollout，属 actor 待验（环境卡 E09）。
- **容器条件：**DC 走正式启动路径，用 Claude Code 2.1.205、桩模型，agent 身份 54321，派生镜像 `f27e31c68aad…`。下面是它对公开读者预判的修正。
  - **证实的预判：**
    - `python` 指向 `/testbed/.venv/bin/python`；Orange 从 `/testbed/Orange` 导入。
    - 版本是 sklearn 0.22.2.post1、scipy 1.5.4。
    - pip 24.0 存在，但 `DNS_EXTERNAL=DENIED`；`xvfb-run` 在 `/usr/bin`。
    - 在 base 上跑题面原例，报的正是题面那句 ValueError（`mcve_statement.out`）。
  - **推翻 ①：**"base 上 `test_logistic_regression.py` 只有 `test_probability` 失败"不对。
    - 还有 `test_learner_scorer`、`test_learner_scorer_multiclass` 两个既有失败。
    - 应用 gold 后这两个仍失败：`DC/private_gold/private_control.json` 的 test_lr 为 2 failed / 10 passed。
  - **推翻 ②：**"控件测试修复前后都应通过"不对。
    - `test_output_learner`、`test_output_learner_name`、`test_parameters` 在 base 与 gold 上都失败。
    - 原因是 orange-widget-base 版本漂移：`requirements-gui.txt:2` 只写了下限 `>=4.5.0`；输出里有 "decorate OWLogisticRegression.apply with @gui.deferred …" 警告；点 apply 后没有发出新的 learner。
    - 这与本题无关，但控件测试不能作开发信号。
  - **公开读者列的未知 A1–A3 被隐藏测试钉死：**见 §4。

## 3. 隐藏测试展开（第 2 步）

### 3.1 目标键

**`test_probability`（`test_1.py:60-64`）**
- 做法：`LogisticRegressionLearner(penalty='l1')` 在 `iris[:100]`（二分类）上拟合，再对 `iris[100:]` 取概率，断言 `abs(p.sum(axis=1) - 1).all() < 1e-6`。
- 调用路径：`Learner.__call__` → `_fit_model` → `SklLearner.fit` → `_initialize_wrapped()` → `LogisticRegression(**params).fit`（`Orange/base.py:542-555`）。
- noop 失败位置：sklearn `_check_solver`（`_logistic.py:445`），抛出题面原句（`B5` noop 日志第 106 行）。
- 断言是弱的：`.all()` 先把数组归约成布尔值，所以只要有一行概率和恰好等于 1，断言就通过。它实际只检查"L1 拟合与预测不抛异常"。
  - 这正是题面的主诉，覆盖成立。
  - 但它不检查 L1 是否真的生效。"静默改成 l2"这类部分解，要靠 `test_auto_solver` 的 penalty 断言兜住。
- 题面原例是完整 iris（三分类），隐藏测试只用二分类子集。三分类 L1 只有私有对照的证据：root 身份，rc=0，`solver='liblinear'`。

**`test_auto_solver`（`test_1.py:135-153`）**
- 做法：三次构造学习器，直接调私有方法 `lr._initialize_wrapped()`，检查返回的 sklearn 估计器属性：
  1. `penalty="l2", solver="auto"` → `.solver == "lbfgs"`，`.penalty == "l2"`
  2. `penalty=None, solver="auto"` → `.solver == "lbfgs"`，`.penalty` 等于 `None`
  3. `penalty="l1", solver="auto"` → `.solver == "liblinear"`，`.penalty == "l1"`
- noop 在第 1 条失败：`'auto' != 'lbfgs'`（`B5` noop 第 35 行）。原因是 base 的 `_initialize_wrapped`（`base.py:547-548`）把 "auto" 原样交给 sklearn 构造函数，而构造函数不做校验。
- 测试注释写 "valid as of sklearn v0.23.0"，但镜像装的是 0.22.2.post1。其 `_check_solver` 只接受 `['l1','l2','elasticnet','none']`（noop 日志里有这段源码），`None` 不是合法值。第 2 条只测透传，不拟合。

### 3.2 回归键（9 个 PASSED，noop 与 gold 相同）

| 键 | 测什么 | 保护的旧行为 / 备注 |
| --- | --- | --- |
| `test_LogisticRegression` | 默认学习器在 heart_disease 上做 2 折 CV，要求 0.8<CA<1.0 | 默认 l2 路径可用。lbfgs 在未标准化数据上 100 次迭代不收敛（DC 的 test_lr 有 ConvergenceWarning）。CV 默认 `random_state=0`（`Orange/evaluation/testing.py:556`） |
| `test_coefficients` | 默认学习器拟合 heart_disease，检查系数长度 | 同上；即修订 r2e-mr-020 的对象 |
| `test_LogisticRegressionNormalization_todo` | `LogisticRegressionLearner(normalize=True)` 抛 TypeError | 构造函数拒绝未知参数，不能加 `**kwargs` |
| `test_learner_scorer_feature` / `_multiclass_feature` | 逐特征 score 与整体 score 一致 | scorer 自洽（与 FAILED 键同一路径，但只比一致性） |
| `test_learner_scorer_previous_transformation` | 离散化后的 iris，score 全部为正 | |
| `test_predict_on_instance` | zoo 上单实例与切片的预测一致 | |
| `test_single_class` | 单类数据抛 ValueError | lbfgs 和 liblinear 都会抛 |
| `test_sklearn_single_class` | 纯 sklearn，不经过 Orange | 死键，与候选无关 |

阅读范围：
- **读了：**
  - 13 个键的测试体全部读完。
  - 调用链：`SklLearner`（`base.py:491-573`）、`_FeatureScorerMixin.score`（`logistic_regression.py:16-19`）、`LearnerScorer.score_data`（`Orange/preprocess/score.py:163-188`）。
  - `Normalize` 的说明（只标准化连续变量）。
  - 数据定位：`Orange/data/table.py:36-42`、`io_base.py:749-786`。
  - CV 默认值。
- **没读：**`Continuize`、`SklImpute`、`CA` 的实现。sklearn 源码只看到了日志里 `_check_solver` 与 `_check_optimize_result` 的片段。

## 4. 双向映射

**表 1：公开要求 / 合理旧行为 → 键**

| # | 要求 | 公开依据 | 键 / 决定性断言 | 状态 | 执行证据 |
| --- | --- | --- | --- | --- | --- |
| R1 | l1 拟合不再报错（题面原例） | `user_prompt.txt:6-20` | `test_probability`（二分类子集，弱断言） | 部分：原例是三分类 | `B5` noop/gold；DC mcve（base 报错，agent 身份）；私有对照 mcve（gold 下三分类 rc=0，root） |
| R2 | 自动选择支持该 penalty 的 solver | `user_prompt.txt:19-20` | `test_auto_solver` | **冲突/过严**：额外要求 "auto" 取值、在 `_initialize_wrapped` 时解析、L1=liblinear、None 透传 | `B5` |
| R3 | 默认 repr 仍是 `LogisticRegressionLearner()` | 公开 `test_util.py:57-60` | 无隐藏键 | 缺失（评分不管） | 私有对照 test_regress 5 passed（gold 保持） |
| R4 | 默认 l2 结果不变 | 公开测试 | `test_LogisticRegression`、`test_coefficients`、两个 scorer 一致性键、`test_predict_on_instance`；两个 FAILED scorer 键实际也钉住了默认 l2 模型的输出 | 覆盖（间接） | `B5` |
| R5 | repr eval 往返、pickle | 公开 `test_classification.py` | 无 | 缺失 | 私有对照同上 |
| R6 | 拒绝未知 kwargs | 公开测试 | `test_LogisticRegressionNormalization_todo` | 覆盖 | `B5` |
| R7 | `params['penalty']` 保持传入值 | 控件测试 | 间接：`test_auto_solver` 查的是估计器的 `.penalty`，不是 learner.params | 部分 | |
| R8 | 显式有效组合原样透传 | base 行为 | 无 | 缺失 | 未验 |
| R9 | `penalty='none'` 可用 | sklearn | 无（`test_auto_solver` 用的是 Python `None`，不拟合） | 缺失 | 未验 |
| A1 | 显式 `lbfgs` 配 `l1` 时怎么办 | 多解 | 无；gold 尊重显式值，照样报错 | 不评分 | |
| A2 | L1 选哪个 solver | 多解 | 第 3 条要求 `liblinear` | **冲突**：题面说"a solver that supports" | |
| A3 | 所选 solver 在哪里可见 | 多解 | 要求在 `_initialize_wrapped()` 的返回值上 | **过严**（私有方法） | |

**表 2：关键断言 → 公开依据**

| 断言 | 公开依据 | 评价 |
| --- | --- | --- |
| 接受 `solver="auto"` 并解析 | 题面只说 "automatically select"。仓库里有同类哨兵：同一签名的 `multi_class="auto"`、`manifold.py:73-77` 的 eigen_solver、`pca.py` 的 svd_solver、Ridge 的 `solver='auto'` | 可推知但非唯一；题面没有提出新增取值 |
| 无参调用 `_initialize_wrapped()` 就返回已解析的估计器 | `base.py:547-548` 有此钩子，`neural_network.py:29-32` 有覆盖先例 | 私有接口。在 `fit` 时解析同样合理（同文件 `KNNBase.fit` 就在 fit 里改 params，`base.py:603-607`），却会失败 |
| L1 → `"liblinear"` | sklearn 0.22 的 `_check_solver` 把 liblinear 和 saga 都列为支持 L1；liblinear 是 sklearn 0.22 之前的默认 solver | 常见选择但非唯一 |
| l2 → `"lbfgs"` | base 的默认值 | 有依据 |
| `penalty=None` → lbfgs，且 `.penalty` 仍为 None | 无；0.22 不接受 None | 最简实现自然满足；只有做校验或把 None 规范成 'none' 的实现会失败 |

## 5. 替代解与部分解（静态推断，未执行）

**会判 0 的合理替代**（每条都修好了题面原例）：
- **V1 不加哨兵：**保留默认 `"lbfgs"`，遇 l1 就换 liblinear。第 1 条得到 `'auto'`，与 noop 同型失败 → 0。
- **V2 哨兵用 `None`：**失败方式同 V1 → 0。
- **V3 与 gold 相同，但 L1 选 saga：**第 3 条 `'saga' != 'liblinear'` → 0。
- **V4 在 `fit` 里解析：**照 `KNNBase` 先例就地改 params，或在 fit 里用副本解析，都不经过 `_initialize_wrapped`。第 1 条得到 `'auto'` → 0。
- **V5 解析时校验 penalty：**对未知值报错，或把 None 规范成 `'none'`。第 2 条失败 → 0。
- **V6 按数据选 solver：**给 `_initialize_wrapped` 加必需参数。测试无参调用会抛 TypeError → 0。

**能通过的实现：**
- gold；
- 在 `__init__` 里把 "auto" 解析后存进 params。隐藏键全过，但默认 repr 会多出 `solver='lbfgs'`，只影响公开的 `test_util`。

**部分 / 错误实现：**
- "静默把 l1 改成 l2"：若改在 `_initialize_wrapped` 里，第 3 条的 penalty 断言会抓住；若只改在 `fit` 里，第 1 条先失败。
- 没有发现能通过全部隐藏键的明显错误解。

## 6. R2E 专项

### (a) 期望里的非 PASSED 键

**`test_learner_scorer`**
- 断言：默认学习器在 Normalize 后的 heart_disease 上，|系数|最大的原始特征应为 `'major vessels colored'`。
- 实际：`'chest pain'`。

**`test_learner_scorer_multiclass`**
- 断言：zoo 上两栖类（第 0 类）|系数|最大的特征应为 `'aquatic'`。
- 实际：`'legs'`。第一条断言就失败，后面 6 条没有执行。

**是不是题目本意：**不是。
- 两者都只走默认 l2 路径。gold 下 `"auto"` 解析为 lbfgs，与 base 是同一个模型。
- 失败文本在 noop 与 gold 上逐字相同（`B5` noop 第 49、63 行；gold 第 35、49 行）。

**已排除 SciPy：**
- 来源环境（SciPy 1.7.3）：R-f gold 日志、M3 两次参考运行。
- `+env_v2`（SciPy 1.5.4）：`B5` 两次、DC、私有对照。
- 两个环境下失败文本逐字相同。
- 这两个测试先做 Normalize。DC 的 ConvergenceWarning 只出现在 `test_LogisticRegression` 和 `test_coefficients`，说明 scorer 路径上的 lbfgs 已收敛。

**已排除随机：**没有随机源；至少 10 次运行结果一致。

**未定位：是上游在此提交就失败，还是其它依赖漂移（如 numpy）。**弱倾向于前者，依据有四条：
- 收敛后的 L2 正则问题严格凸，解唯一，与 SciPy 版本无关。
- 代码和数据都是该提交的跟踪文件。
- 预测的首位特征整体换了（`'legs'` 对 `'aquatic'`），不像数值噪声。
- base 处在 sklearn 迁移窗口：`requirements-core.txt:4` 写着 "<0.23 # temp fix … pull/4768"，测试注释写 "as of sklearn v0.23.0"。

反证缺失：没有上游 CI 记录。

**翻转风险：**
- 能通过 `test_auto_solver` 的实现，必然把 auto+l2 解析为 lbfgs，默认 l2 模型不变，这两键保持 FAILED。
- 只有顺手改了默认 `multi_class`、默认 solver 或默认预处理的候选，才可能把它们翻成 PASSED 而判 0。这些改动超出题面，风险低。
- 开发干扰：agent 修好后，仍会在公开测试文件里看到这 2 个失败，可能误以为相关而去"修"。这是开发干扰，不是评分误判。

修订后没有其它 FAILED 键。

### (b) noop 目标键的失败原因

- `test_probability` 抛出题面原句（`B5` noop 第 106 行；DC mcve 同一句）→ 成立。
- `test_auto_solver` 是新接口断言失败，与题面报错无关，属于目标键中的"接口键"。

### (c) 题面是否泄漏修法

不泄漏。题面只给方向，没有 solver 名、取值或代码。反过来，相对隐藏测试它是规格不足的（§4）。

### (d) 测试辅助、搬迁伪影、跨文件撞键

- 隐藏测试只导入库代码（Orange.data、classification、evaluation 和 sklearn），不导入仓库的测试辅助代码。
- 数据文件 `Table('iris'|'heart_disease.tab'|'zoo')` 按 `dataset_dirs = ['', Orange/datasets]` 解析到跟踪的样例数据。`datasets` 软链不参与；`Orange/tests/datasets` 里也没有同名文件。
- 只有一个测试文件，不会撞键。`__init__.py` 为空，原目录的 conftest 不涉及。
- 结论：无问题。

### (e) 时间、随机、资源敏感

- CV 固定 `random_state=0`。
- 两个回归键依赖 lbfgs 未收敛的结果（ConvergenceWarning 被 `-W ignore` 吞掉）。在 SciPy ≥1.6 加 sklearn 0.22.2.post1 的组合下会变成 AttributeError，所以必须绑定 `+env_v2`。
- 资源：内存峰值 1.17 GB / 4 GiB，测试约 1.8 秒（`B5` ledger）。未见时间或资源敏感。

### (f) 修订 r2e-mr-020

**范围：**
- 只把期望里两处 FAILED 改为 PASSED，键集合与顺序不变，哈希重算一致。
- 隐藏测试树 sha `9a87bfe6…` 在修订前后的运行里相同（R-f 与 `B5` 日志头）。

**原因成立：**
- 来源环境 gold 日志（`runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-gold-o_f0536903.eval.log`）里：
  - `test_coefficients` 失败在 `sklearn/utils/optimize.py:243` 的 `result.message.decode("latin1")`，报 `AttributeError: 'str' object has no attribute 'decode'`。
  - `test_LogisticRegression` 是同一次拟合失败被 CV 吞掉。未初始化的预测数组（含 `6.43e-310` 这类值）随后触发 CA 的 "mix of binary and continuous targets"。
  - M3 两次参考运行相同。
- 在 `+env_v2` 下，两键在 noop 与 gold 上都 PASSED（`B5`；DC test_lr 里只有 ConvergenceWarning）。

**没有弱化断言，也没有扩大需求：**
- 两键测的是 base 已经满足的默认行为。修订把它们从"必须失败"改成回归保护，评分变严而不是变宽。
- 同时消除了一个反向激励：在旧期望下，让 lbfgs 收敛的候选（如调大 `max_iter`）会把这两键修成 PASSED 而判 0。

**当前运行行确实用了该环境配方：**
- 4 条 current 行的 `overlay.recipe_id = r2e_derive_v1+env_v2`，镜像 `rh2-r2e-derived/orange3:9b5494e26f40-r2e_derive_v1e2`，ID `sha256:f27e31c68aad…`，评分用户 54322，`network=deny_all`。
- 评分日志本身不打印版本。SciPy 1.5.4 来自同一镜像 ID 上的 DC `env.out`（agent 身份）和私有对照（root 身份）。
- ledger 不记期望 sha；但 gold 得 13/13、且日志里两键 PASSED，只与修订后的期望相容。

**残余风险：**
- 任何没有 `+env_v2` 的镜像配上修订后期望，gold 会得 0。
- 按环境卡 §2，正式 actor 若取 `public.image`（来源镜像），开发条件就与评分环境不一致：两个回归键会崩，隐藏测试可读，git 里含修复提交。
- DC 已经用派生镜像（`image_is_overlay_derived_id: true`，预检 HIDDEN_TESTS / GIT_HISTORY 都是 ok）。正式链要等 B 线接线后再验。

## 7. gold 检查（第 5 步）

- **修到原例：**私有对照 mcve（完整 iris，l1）rc=0，得到 `solver='liblinear'`；`B5` gold 两次都是 13/13。
- **范围：**单文件，没有无关改动。只有 "auto" 触发改选，显式 solver 原样透传。显式 `lbfgs`+`l1` 仍报错，这是设计选择。
- **回归：**
  - 默认 repr 保持：params 存的是 "auto"，签名默认也是 "auto"。
  - repr / SklTest / LearnerReprs 子集在 gold 下 5 passed（私有对照，root 身份）。
  - 调用者只按 penalty 或默认参数构造学习器，没有读取 `solver` 的代码，因此没有已知破坏。调用者包括 `stack.py:100` 的默认 aggregate、`evaluate/utils.py:57-58`、`owlogisticregression.py:73-84`、ownomogram、owpredictions、owtestandscore。
- **未测的旧行为：**
  - R8（显式有效组合透传）。
  - R9：`'none'` 在 gold 下走 lbfgs，按源码推断可用。
  - elasticnet：auto 下仍走 lbfgs 并报错，与 base 相同。
  - 控件的 L1 路径：控件测试因环境漂移不可用。
- **小瑕疵：**
  - `model.params['solver']` 记的是 "auto"，实际值只在 `model.skl_model.solver` 上。
  - patch 末尾多一个空行（git apply 有警告，不影响应用）。
- **判定：**gold 合理且最小，但不是唯一合理的修复。

## 8. 开发需求（第 6 步）

| 项 | 需求 / 事实 | 证据级别 |
| --- | --- | --- |
| 解释器 / 导入 | `python` = `/testbed/.venv/bin/python` 3.7.9。Orange 从 `/testbed` 源码导入（develop 安装），改 `.py` 立即生效，不需要重建 | actor 实测（DC `env.out`，经 CC Bash，agent 54321） |
| 依赖 | sklearn 0.22.2.post1、scipy 1.5.4；不需要新包；pip 在但不能出网 | actor 实测 |
| 复现 | 题面原例一行命令即可在 base 复现题面原句 | actor 实测（`mcve_statement.out`） |
| 公开测试 | `python -m pytest Orange/tests/test_logistic_regression.py`：base 上 3 个失败（含 2 个既有 scorer 失败），gold 后 2 个失败。agent 要自己认出那 2 个是既有失败；git 可用，可以 stash 后对照 | base 为 actor 实测；gold 侧为 root 私有对照 |
| 回归子集 | `test_util::test_reprable`、`SklTest`、`LearnerReprs`：base 与 gold 都是 5 passed | 同上 |
| 控件测试 | xvfb 前缀可用，但 3 个用例因 orange-widget-base 漂移在 base 与 gold 上都失败，不能作信号 | 同上 |
| 资产 | iris、heart_disease、zoo 都在跟踪的 `Orange/datasets` 里 | 静态阅读加运行结果 |
| 网络 | 解题、构建、测试都不需要网络 | actor 实测（出网被拒） |
| 权限 | `/testbed` 属主是 54321、可写；`/rh2/bash_env` 对 agent 只读 | actor 实测（`prelaunch.json`、DC） |
| 构建 | 不需要构建。不要运行 `install.sh`：无网，而且可能重建 `.venv`。工作区里的 `run_tests.sh` 指向不存在的 `r2e_tests` | 静态（未执行） |
| 提交边界 | 修复应在跟踪的非测试源码里；对 `.venv` 的改动不会进入交付 | 静态 |
| 真实消息 | 题面与 hints 的真实渲染未捕获 | actor 待验 |
| 正式镜像选择 | 必须用 `+env_v2` 派生镜像 | DC 已用；正式链 actor 待验 |

## 9. 八方面覆盖与未查项

| 方面 | 已查 | 未查 / 缺口 |
| --- | --- | --- |
| 公开需求 | 题面、hints、`public_read.md`、公开测试与调用者 | 真实渲染消息 |
| 材料与初态 | 版本、哈希、补丁范围、初态 diff；noop 失败位置（日志加 actor 复现） | — |
| 测试是否测到要求 | 13 键全部读完，并追到调用链 | 三分类 L1 原例不在隐藏测试里；`test_probability` 断言弱 |
| 误拒合理解 | 静态推演了 6 类替代解 | 没有执行 CPU 反例 |
| 回归与 gold | 逐行读 gold，grep 调用者，看私有对照 | R8、R9、elasticnet、控件路径未验 |
| 开发条件 | DC（正式启动路径 + CC + 桩模型）和私有 gold 对照 | 真实模型求解；正式链的镜像选择 |
| 交付与评分边界 | 隐藏测试不依赖测试辅助；预检（隐藏测试可见性、git 历史）为 ok；grader 流程 | 仓库根目录的 conftest、pytest 配置等共享控制面，引用平台审查；本题没有特例，未逐项核 |
| 题目关系与用途 | 批内唯一的 orange3 题（据环境卡） | 同源或派生关系未查。上游后续版本都带 `solver="auto"`，预训练记忆可能帮助命中被钉死的接口；这是污染问题，静态无法核实 |

## 10. 缺口与未知

1. 两个 scorer FAILED 键的根因（上游本就失败，还是依赖漂移）未定位。对评分影响低。
2. "替代解判 0"是静态推断，未执行。旁证是代码路径短、noop 有同型失败。
3. 真实任务消息未捕获。
4. 评分侧的 SciPy 版本是靠镜像 ID 同一性推出的，评分日志没有直接打印。

## 11. 暂定处置与下一步

- **暂定：**`needs_review`，理由是题意/测试争议：`test_auto_solver` 过严，题面规格不足。环境、修订、目标键的失败原因都核对通过。可作 development_diagnostic，但须附"接口被钉死"的说明；作 reward 前需用户决定修订方向。
- **可选方向（建议，未决定）：**
  - **(A) 题面最小补全：**写明新增 `solver="auto"`（作为默认值），L1 用 liblinear、其余用 lbfgs，并在创建 scikit-learn 估计器时解析。
    - 不点名 `_initialize_wrapped`，V4 仍会被误拒；点名又接近把测试抄进题面。
  - **(B) 测试改成行为级：**例如拟合后检查 `model.skl_model` 的 solver 是否支持所给 penalty、penalty 是否保持；默认 l2 仍用 lbfgs。
    - 这会改 oracle，需要独立复核，并做正反对照。
  - **(C) 不修订：**只作诊断题，统计时单列。
- **唯一最值得先做的下一步：**在 `+env_v2` 派生镜像上走真实 RH2 评分，跑 V1、V3、V4 三个替代补丁和一个"静默改 l2"的错误补丁。
  - 预期四者都得 0，并分别记下三个替代补丁确实修好了题面原例。
  - 可顺带在 `solver='liblinear'`（或 `multi_class='ovr'`）下跑一次两个 scorer 测试，看期望值是否按旧 solver 校准。

## 附录 A：证据清单（均已本地打开）

- **current 账本行：**
  - `B5/ledger_b5_noop.jsonl` 第 13、14 行（reward 0，11/13，mismatched 为 `test_auto_solver`、`test_probability`）。
  - `B5/ledger_b5_gold.jsonl` 第 13、14 行（reward 1，13/13）。
  - 4 行都是 `recipe_id=r2e_derive_v1+env_v2`，镜像 ID `f27e31c68aad…`，评分用户 `rh2grader/54322`。
- **current 日志：**`B5/eval_logs/` 下 4 个文件，sha 都与 `run_refs.json` 一致。两次重复运行之间只有时间戳不同。
  - noop：`evallog_replay-69e318acd762-oran_aad1854d.eval.log`、`…_b2317756.eval.log`
  - gold：`evallog_replay-caf6d2fe3186-oran_fbc75b60.eval.log`、`…_9cec0ea7.eval.log`
- **superseded 与独立参考：**
  - R-f gold 日志：读全了失败段。
  - R-f noop 日志：grep。
  - M3 独立参考：`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/orange3/9b5494e26f40/gold/a{1,2}/test_output.txt`（grep）。
  - 没读环境轮中央复跑（`_rerun2`）的日志。
- **actor 与私有对照：**
  - DC：`orig/attempt.json`、`prelaunch.json`、`activation_check.json`、`commands_with_preflight.json`、`captures/*.out`（6 个）、`stub/requests/messages_000.json`（只看系统提示与用户消息）、`post_run_facts_root.txt`。
  - 私有对照：`private_gold/private_control.json`、`stdout.log`。
- **按角色卡没有打开：**
  - `revisions.json` 列出的 `docs/…/r2e_env_repair_20260924/…` 修订说明；
  - `runs/r2e_t0_batch2_20260924/diag_orange3/`、`runs/r2e_t0_batch3_20260924/dryrun_b3o/`；
  - OUTPUT_DIR 里 `public_read.md` 以外的文件；
  - 任何 history 或审查目录。

## 附录 B：40 项预映射（供之后的 screening_record，定稿前可能调整）

| 编号 | 状态 | 说明 |
| --- | --- | --- |
| 1、2 | pass | |
| 3 | unknown | 实际渲染消息未捕获 |
| 4 | pass | |
| 6–9 | pass | env_v2；actor（54321）与 grader（54322）两侧都有实测 |
| 10 | pass（附注） | 2 个既有 scorer 失败，控件测试不可用 |
| 11 | pass | 不需要网络 |
| 13、14 | pass | |
| 16–22 | pass | 非 gold 候选的交付只有 noop/gold 证据 |
| 23、24、32 | issue | 同一根因：`test_auto_solver` 钉死接口 |
| 25 | pass（附注） | 弱断言；三分类原例未测 |
| 26、27 | pass | 附未测项 |
| 29 | pass | 派生镜像预检 |
| 37、38 | pass | 修订 r2e-mr-020 |
| 5、15、30、31、33–36、39 | not_checked | |
| 28、40 | not_applicable | |
