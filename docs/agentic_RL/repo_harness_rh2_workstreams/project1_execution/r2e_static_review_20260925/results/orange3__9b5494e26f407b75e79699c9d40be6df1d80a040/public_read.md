# 公开读者报告：orange3__9b5494e26f407b75e79699c9d40be6df1d80a040

- 角色：R2E 公开读者（静态审查，不解题）。只读了角色卡和 `PUBLIC_DIR` 下的文件；下文路径都相对 `PUBLIC_DIR`。没有运行项目代码，没有联网。
- 公开包不含 `.venv`，所以看不到 scikit-learn 源码。凡是关于 sklearn 行为的说法，都来自我对 sklearn 0.22 源码的记忆，标为 **[sklearn 记忆，未核对]**；解题者可以在容器里核对（见 §4）。
- 题目一句话：base 上 `LogisticRegressionLearner(penalty='l1')` 一拟合就抛 sklearn 的 solver/penalty 不兼容错误；题面要求学习器"自动选择支持所给 penalty 的 solver"。

## 1. 需求表

"类型"一列：**明示**＝题面直接写了；**可推知**＝从公开仓库的接口或测试可以合理推出；**多解**＝有多种合理解释。

| # | 要改变 / 要保留的行为 | 类型 | 依据 |
|---|---|---|---|
| R1 | `LogisticRegressionLearner(penalty='l1')` 在分类数据上拟合（题面示例是 iris）不再抛 `ValueError`，而是返回可用模型 | 明示 | `user_prompt.txt:6-20` |
| R2 | 做法：由学习器自动挑一个支持该 penalty 的 solver，而不是要求调用者自己传 solver，也不是只把报错换个说法 | 明示方向，细节未定 | `user_prompt.txt:19-20` |
| R3 | 默认构造 `LogisticRegressionLearner()` 可用，并且 `repr` 仍是 `'LogisticRegressionLearner()'`（连调两次） | 可推知（公开测试） | `worktree/Orange/tests/test_util.py:57-60`。repr 从构造函数签名的默认值和 `getattr` 取值对比生成（`worktree/Orange/util.py:365-393`），而 `getattr` 会落到 `self.params`（`worktree/Orange/base.py:563-567`） |
| R4 | 默认 l2 学习器的数值结果不应明显变化，因为多条公开测试带阈值或具体特征名断言 | 可推知（保守） | `worktree/Orange/tests/test_logistic_regression.py:21-27, 66-107`；`worktree/Orange/tests/test_classification.py:311-318, 320-327` |
| R5 | `repr(LogisticRegressionLearner(tol=0.0002))` 能 `eval` 往返；用默认参数得到的模型能 pickle 往返 | 可推知 | `test_classification.py:440-463, 393-417` |
| R6 | 构造函数仍拒绝未知关键字参数：`LogisticRegressionLearner(normalize=True)` 仍抛 `TypeError`。也就是说不宜给 `__init__` 加 `**kwargs` | 可推知 | `test_logistic_regression.py:55-58` |
| R7 | 学习器的 `params['penalty']` 保持传入值。控件测试把 `learner.params.get('penalty')` 与 `'l1'`/`'l2'` 直接比较 | 可推知 | `worktree/Orange/widgets/tests/base.py:371-381, 397-426`；`worktree/Orange/widgets/model/tests/test_owlogisticregression.py:49-55` |
| R8 | 显式传入的有效组合（如 `solver='saga', penalty='l1'`、`solver='liblinear'`）在 base 上原样透传给 sklearn 并可用，修复后不应坏掉 | 可推知 | `worktree/Orange/base.py:520-530, 547-555` |
| R9 | `penalty='none'` 配默认 solver 在 base 上可用（lbfgs 支持 `'none'`，**[sklearn 记忆，未核对]**），修复后不应变成报错 | 可推知（依赖 sklearn 行为） | `worktree/Orange/classification/logistic_regression.py:37-42` |
| A1 | 用户显式写 `solver='lbfgs', penalty='l1'` 时，是自动换 solver，还是尊重显式选择、照样报错？ | 多解 | base 的默认值本身就是 `"lbfgs"`（`logistic_regression.py:39`），不改默认值就分不清"用户显式传入"和"用了默认值" |
| A2 | l1 选哪个 solver：`liblinear` 还是 `saga`？两者都支持 l1 **[sklearn 记忆，未核对]** | 多解 | 题面没说 |
| A3 | 选中的 solver 应在哪里看得到：`learner.params['solver']`、`learner.solver`、学习器 repr、`model.params`，还是只在 `model.skl_model.solver` | 多解 | `base.py:486-488, 542-548, 563-567` |
| A4 | `'elasticnet'` 算不算范围内？倾向范围外 | 多解 | Orange 签名没有 `l1_ratio`（`logistic_regression.py:37-40`），`_get_sklparams` 只转发签名里有的参数（`base.py:520-530`）。elasticnet 需要 saga 加 `l1_ratio` **[sklearn 记忆，未核对]**，所以换哪个 solver 都配不起来 |
| A5 | l1 同时配 `multi_class='multinomial'` 或 `dual=True` 时怎么办 | 多解，题面没涉及 | liblinear 不支持 multinomial；非 liblinear 的 solver 不支持 `dual=True` **[sklearn 记忆，未核对]** |

## 2. 合理实现范围

不猜标准答案、不写修复，只列哪些做法都应算合理，以及它们对外能看到的差别。

- **在哪里做选择。** 以下几处都合理：
  - 在 `LogisticRegressionLearner` 里覆盖 `_initialize_wrapped`。仓库先例：`worktree/Orange/classification/neural_network.py:29-32`。
  - 覆盖 `fit`。先例 `worktree/Orange/base.py:603-607` 的 `KNNBase.fit` 会在拟合时就地改 `self.params`。
  - 在 `__init__` 里决定。

  对外可见的差别：
  - 如果在 `__init__` 里把算出来的 solver 写进 `params`，而它和签名默认值不同，默认学习器的 repr 就会多出 `solver=...`，违反 R3。
  - 如果在 `fit` 时就地改 `self.params`，学习器的 repr 会在第一次拟合后改变。而且 `model.params` 和 `learner.params` 是同一个 dict（`base.py:544` 是引用赋值，不是拷贝）。之后改了 penalty 再拟合，可能沿用旧 solver。模块级共享实例同样受影响，例如 `worktree/Orange/ensembles/stack.py:100` 的默认 `aggregate=LogisticRegressionLearner()`。这些都没有公开测试覆盖，属于实现质量差异。
  - 如果只在构造 sklearn 估计器时用参数副本，`learner.params['solver']` 和 `model.params['solver']` 保留原值（默认值或哨兵值），实际用的 solver 只能从 `model.skl_model.solver` 看到。
- **"自动"怎么表达。** 两种都合理：
  - 新增一个哨兵默认值，例如 `"auto"` 或 `None`。仓库里有 Orange 自己解析 `'auto'` 的先例：`worktree/Orange/projection/manifold.py:73-77` 的 `eigen_solver`。`worktree/Orange/regression/linear.py:44` 的 `solver='auto'` 则是 sklearn Ridge 本身接受的值，不是 Orange 解析的。注意哨兵值不能原样交给 sklearn：0.22 的 `LogisticRegression` 不接受 `'auto'` **[sklearn 记忆，未核对]**。
  - 保留默认 `"lbfgs"`，只在组合不兼容时换 solver。

  两者对 A1 的回答不同。
- **l1 用哪个 solver。** liblinear 和 saga 都能让题面示例通过 **[sklearn 记忆，未核对]**。
  - liblinear 在 `multi_class='auto'` 下对多类问题走 OvR（一对多）。
  - saga 可以走 multinomial。但默认预处理不含 Normalize（`base.py:506-510`），数据未标准化时 saga 在 `max_iter=100` 下可能不收敛，并发出 ConvergenceWarning。
- **l2（默认）。** 保持 lbfgs 最保守，能满足 R4。把默认整体改成 liblinear 或 saga 也能消掉报错，但那不是"按 penalty 自动选择"，还会改变默认 l2 模型的数值结果，可能碰到 R4 那几条带阈值的测试（没运行，无法判断）。
- **其它 penalty。** 如果把"非 l2 一律换 liblinear"，会让 R9（`'none'`）退化，因为 liblinear 不支持 `'none'` **[sklearn 记忆，未核对]**。
- **控件。** `worktree/Orange/widgets/model/owlogisticregression.py:73-84` 构造学习器时不传 solver，学习器修好后控件自动受益，所以不需要改控件；改了也不算错。
- **约定。** 题面对命名（参数名、哨兵值）、输出（是否发警告、是否记录所选 solver）和默认行为（显式 solver 是否被覆盖）都没有约定。公开材料判断不了评分是否依赖 A1–A3 这些细节。这是本题最主要的未知。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出或强烈暗示修法

- `user_prompt.txt:20` 给出了修法方向（"automatically select a solver that supports the specified penalty"），但没有代码，没有 solver 名，也没有参数或 API 约定。它对解题者是有用的约束，不是实现泄露。
- 示例代码（`user_prompt.txt:9-12`）是出错的调用，不是修好后的实现。

### 3.2 报错能否从 base 源码读出确实会发生

能。调用链如下：

1. 默认 `solver="lbfgs"` 由 Orange 自己写在签名里：`worktree/Orange/classification/logistic_regression.py:37-42`。
2. `self.params = vars()` 经 `_get_sklparams` 按 sklearn 构造函数的参数名过滤（`worktree/Orange/base.py:512-530`）。
3. `_initialize_wrapped` 原样用这些参数构造 `LogisticRegression`（`base.py:547-548`），`fit` 直接调用它（`base.py:550-555`）。
4. Orange 这一侧没有任何 penalty/solver 检查，`Learner.__call__` 也不捕获异常（`base.py:107-144`）。

报错原文来自 sklearn，不在工作树里。它与 `worktree/requirements-core.txt:4` 的约束 `scikit-learn>=0.22.0,<0.23` 一致：0.22 的 `_check_solver` 就是这条消息 **[sklearn 记忆，未核对]**。不论 sklearn 是哪个版本，lbfgs 都不支持 l1，所以一定会报错，只是措辞可能随版本不同。

另外，仓库**已有的公开测试** `worktree/Orange/tests/test_logistic_regression.py:60-64`（`test_probability`，在 `iris[:100]` 上用 `penalty='l1'`）走的正是这条路径。按上面的推理它在 base 上应当失败，可以直接当复现入口（推断，未运行）。

### 3.3 题面示例在 base 接口下是否说得通

说得通。`penalty` 是构造参数（`logistic_regression.py:37`），学习器可以直接调用（`base.py:107`）。`iris_data` 在示例里没有定义，自然理解是 `Table('iris')`，对应文件 `worktree/Orange/datasets/iris.tab` 存在。完整 iris 是三分类，liblinear 和 saga 两条路都能拟合 **[sklearn 记忆，未核对]**。题头的 commit `43f086f0bacc` 与 `public_bundle.json:9` 的 `base_commit` 一致。

### 3.4 题面没提、但读调用者就能看到的影响

- 控件 "Logistic Regression" 提供 "Lasso (L1)" 选项（`owlogisticregression.py:44-45`）。在 base 上选 L1 会被控件吞成 "Fitting failed." 错误：见 `worktree/Orange/widgets/utils/owlearnerwidget.py:76`、`:164-176`，其中第 175 行 `except BaseException`。
- 预览工具 `worktree/Orange/widgets/evaluate/utils.py:57-58` 也构造了 `penalty="l1"` 的学习器。

这些都属于正常读代码的范围，不是题面缺陷。

### 3.5 public_hints 分类（`public_bundle.json:15`）

- **题目需求**："fixing a real GitHub issue"；"find the root cause, and edit NON-TEST source files to fix the issue"。
- **操作指令**：探索代码；不改测试文件；只跑窄范围测试；完成后简短总结并停止调用工具。
- **环境事实声明**：
  - "/testbed、bash 已在该目录"：与 `environment_brief.md:10` 一致。
  - "预激活的 conda 环境 `testbed`，python/pip/测试工具都指向它"：与本镜像不符。实际 `python` 指向 `/testbed/.venv/bin/python`（3.7.9）；pip 有，但不能出网（`environment_brief.md:10-11`）。
  - "评分会重置测试文件，测试改动永不计分"：按角色卡，这不是本来源的实际机制。
- **对合法解法的影响**：
  - 修复只需要改非测试源码，所以"不改测试"不限制合法解法。
  - 照做 conda 说法（例如 `conda activate testbed`）会失败，但无实际影响，因为 `python` 已经指向 `.venv`。
  - "pip 可用"不等于能装包；本题也不需要新依赖。

### 3.6 初态线索

- `worktree_manifest.json` 的 `initial_diff` 为 0 字节，说明镜像初态相对 base 没有改动。未跟踪的文件只有三个：`install.sh`、`run_tests.sh`，以及软链 `datasets -> Orange/tests/datasets/`。
- `worktree/run_tests.sh:1` 执行 `pytest -rA r2e_tests`，但工作树里没有 `r2e_tests`（manifest 的 `files` 里也没有含 `r2e` 的路径）。它透露评分用 pytest 跑隐藏目录 `r2e_tests`，并带 `QT_QPA_PLATFORM=minimal`、`xvfb-run` 和 `-W ignore`。解题者如果直接跑它，pytest 会报找不到路径（预计退出码 4），这对判断修复没有信号（推断，未执行）。
- `worktree/install.sh:18-33`：
  - 构建流程是 Python 3.7、`uv venv`、`setup.py build_ext --inplace`、`setup.py develop`。
  - 第 29 行 `uv pip install scipy scikit-learn` 没带版本约束。按 uv 的一般行为，已满足的包不会被升级，所以 sklearn 大概率仍是 `requirements-core.txt:4` 装的 0.22.x。这只是推断，`environment_brief.md` 没写 sklearn 版本。
  - brief 第 14 行说环境配方把 scipy 改成了 1.5.4，说明实际镜像并不完全等于 install.sh 的产物，版本最好在容器里核对。
  - 如果在无网环境重跑 install.sh，`uv venv` 可能先重建 `.venv` 再在装包步骤失败，把环境弄坏（推断）。建议不要运行它。
- `worktree/Orange/__init__.py:8` 导入 `.version`，而 `Orange/version.py` 被 `.gitignore` 忽略、由 setup.py 生成，静态工作树里没有；编译扩展（`*.so`）也不在。所以静态工作树本身不能 import，容器里应该有（`environment_brief.md:6`）。
- 小出入，影响很低：`worktree/.gitignore` 里没有 `.venv`，而 brief 说 `.venv` 属于被忽略的构建产物，manifest 的 `untracked_in_image` 也没列 `.venv`。容器里 `git status` 可能显示 `.venv/`，也可能被其它 exclude 规则隐藏，公开材料无法判断。

### 3.7 缺失信息：哪些真正阻碍，哪些只需读代码

- **不阻碍开发、只需正常调查**：定位入口很清楚。类名加报错可以直接找到 `logistic_regression.py:32-42` 和 `base.py:547-555`，现成的复现测试是 `test_probability`。sklearn 的版本和 solver/penalty 兼容规则在公开包里没有，但容器里的 `.venv` 可以读到。
- **真正的未知**（不影响写出合理修复，但影响能否对上评分）：A1（显式 solver 是否被覆盖）、A2（l1 用哪个 solver）、A3（所选 solver 在哪里可见）。题面和公开仓库都没有约定。

## 4. 开发需求表

下表所有命令都是**建议，未执行**；"预期"是按代码阅读推断的，没有验证。

| 操作 / 资产 / 服务 | 公开依据 | environment_brief 支持到哪一层 | 缺口 | 最小命令（建议，未执行）与预期现象 |
|---|---|---|---|---|
| 解释器与导入 Orange | `worktree/install.sh:30-31`；`worktree/Orange/__init__.py:8` | `python` 指向 `/testbed/.venv/bin/python`（3.7.9），环境阶段实测（`:10`） | 静态包里没有编译扩展和 `Orange/version.py`，无法静态确认能 import | `python -c "import Orange; print(Orange.__file__)"`。预期打印 `/testbed/Orange/__init__.py` |
| 查依赖版本 | `worktree/requirements-core.txt:4`；`install.sh:22-29` | 只写了 scipy 1.5.4（`:14`） | 没写 sklearn 版本 | `python -c "import sys, sklearn, scipy, numpy; print(sys.version); print(sklearn.__version__, scipy.__version__, numpy.__version__)"`。预期 3.7.9、scipy 1.5.4；sklearn 按推断应为 0.22.x |
| 读 sklearn 的 solver/penalty 规则 | 报错原文（`user_prompt.txt:16`） | 未涉及 | 公开包没有 sklearn 源码 | `python -c "import inspect, sklearn.linear_model._logistic as m; print(inspect.getsource(m._check_solver)); print(inspect.getsource(m._check_multi_class))"`。预期打印兼容规则；模块名按 0.22 写，版本不同需要调整 |
| 复现 bug（纯库，不需要 Qt） | `user_prompt.txt:9-12`；`worktree/Orange/datasets/iris.tab` | 纯库调用不需要 xvfb（`:13`） | 无 | `python -c "from Orange.data import Table; from Orange.classification import LogisticRegressionLearner as L; m = L(penalty='l1')(Table('iris')); print(m.skl_model)"`。base 上预期 `ValueError: Solver lbfgs supports only 'l2' or 'none' penalties, got l1 penalty.`（措辞取决于 sklearn 版本）；修复后打印一个带支持 l1 的 solver 的 `LogisticRegression` |
| penalty 覆盖面（可选） | R9、A2 | 同上 | 无 | `python -c "from Orange.data import Table; from Orange.classification import LogisticRegressionLearner as L; d = Table('iris'); [print(p, L(penalty=p)(d).skl_model.solver) for p in ('l1', 'l2', 'none')]"`。修复后三种都应能拟合；`'none'` 在 base 上也能拟合 **[sklearn 记忆，未核对]** |
| 公开单测（直接覆盖本 bug） | `worktree/Orange/tests/test_logistic_regression.py:60-64` | brief 没明说有 pytest；`install.sh:22` 和 `run_tests.sh:1` 表明 `.venv` 里有 | 无 | `python -m pytest -q Orange/tests/test_logistic_regression.py`（或 `python -m unittest -v Orange.tests.test_logistic_regression`）。base 上预期只有 `test_probability` 失败（同一个 ValueError），`test_LogisticRegressionNormalization` 被 skip（`:29`）；修复后应全部通过 |
| 回归检查（repr / 默认结果 / pickle） | R3–R6；`test_util.py:43-60`；`test_classification.py:310-331, 381-463` | 同上 | 无 | `python -m pytest -q Orange/tests/test_util.py::TestUtil::test_reprable Orange/tests/test_classification.py::SklTest Orange/tests/test_classification.py::LearnerReprs`。修复前后都应通过。可选更重的一组：`python -m pytest -q Orange/tests/test_classification.py::LearnerAccessibility`（遍历全部分类学习器） |
| 控件测试（Qt） | `worktree/Orange/widgets/model/tests/test_owlogisticregression.py`；`worktree/requirements-gui.txt` | 需要前缀 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum`，`xvfb-run` 在 `/usr/bin`（`:13`） | 没写 PyQt5 / orange-widget-base 是否齐全；按 `install.sh:22-24` 推断应该装了 | `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -q Orange/widgets/model/tests/test_owlogisticregression.py`。修复前后都应通过：base 上 L1 拟合失败被吞成 `Error.fitting_failed`，而 `widgets/tests/base.py:428` 只在 `LEARNER` 是 `SklModel` 子类时检查模型，本题不触发，所以该测试不能区分修复前后 |
| 数据集资产 | `worktree/Orange/datasets/{iris,heart_disease,zoo,titanic,housing}.tab`；`worktree/Orange/widgets/tests/datasets/testing_dataset_{cls,reg}.tab`；`worktree/Orange/tests/datasets/{adult_sample_missing,test8}.tab` | 未涉及 | 无，都在工作树里 | 不需要额外动作 |
| 网络 / 装包 / 外部服务 | 本题不需要新依赖，也不需要 DB 或网络 | 无出网，装不了新包（`:11`） | 无 | 不要运行 `install.sh`（理由见 §3.6）。`run_tests.sh` 依赖不存在的 `r2e_tests`，跑了只会报找不到路径 |
| 写权限与资源 | 修改点在 `worktree/Orange/classification/` 或 `worktree/Orange/base.py` | agent（uid 54321）可写 `/testbed`；默认 2 CPU / 4 GiB，`/tmp` 1 GiB（`:12`） | 资源是否够跑控件测试未验证 | 相关测试都很轻；按 hints 只跑单个文件即可 |

## 5. 阅读范围

**实际打开的文件**（都在 `PUBLIC_DIR` 内）：

- 公开包顶层：
  - `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`
  - `worktree_manifest.json`：只看了结构，以及 `export`、`initial_diff`、`untracked_*` 字段和个别文件条目。没有打开它指向的外部路径，例如 `initial_diff.source`。
- 构建、依赖与开发说明：
  - 全文：`worktree/install.sh`、`worktree/run_tests.sh`、`worktree/requirements-{core,dev,gui,sql,opt}.txt`、`worktree/requirements.txt`、`worktree/setup.cfg`、`worktree/pyproject.toml`、`worktree/tox.ini`、`worktree/README-dev.md`、`worktree/.gitignore`
  - 只 grep：`worktree/CONTRIBUTING.md`、`worktree/CHANGELOG.md`（另读了开头）、`worktree/.github/workflows/linux_workflow.yml`
- 库源码：
  - 全文：`worktree/Orange/classification/logistic_regression.py`、`worktree/Orange/base.py`、`worktree/Orange/classification/__init__.py`、`worktree/Orange/classification/base_classification.py`、`worktree/Orange/classification/neural_network.py`、`worktree/Orange/regression/neural_network.py`
  - 片段：`worktree/Orange/util.py:320-410`、`worktree/Orange/__init__.py`（grep）、`worktree/Orange/projection/manifold.py:66-80`、`worktree/Orange/projection/pca.py:95-135`、`worktree/Orange/regression/linear.py:36-50`
- 测试：
  - 全文：`worktree/Orange/tests/test_logistic_regression.py`、`worktree/Orange/widgets/model/tests/test_owlogisticregression.py`
  - 片段：`worktree/Orange/tests/test_util.py:40-75`、`worktree/Orange/tests/test_classification.py:1-51, 305-467`、`worktree/Orange/widgets/tests/base.py:120-460`
- 控件与文档：
  - 全文：`worktree/Orange/widgets/model/owlogisticregression.py`
  - 片段：`worktree/Orange/widgets/evaluate/utils.py:40-80`、`worktree/Orange/widgets/utils/owlearnerwidget.py`（grep）、`worktree/doc/visual-programming/source/widgets/model/logisticregression.md:1-30`
- 在 `worktree/` 里 grep 过的关键词：`LogisticRegressionLearner`、`penalty`、`solver`、`_initialize_wrapped`、文档里的 logistic。另外列了数据集目录。

**没有查的范围：**

- sklearn 源码：不在公开包里。相关结论都标了 [sklearn 记忆，未核对]。
- 编译扩展和 `Orange/version.py`：静态包里没有。
- 其余控件、canvas、文档正文和 benchmark 等与本题无关的目录。
- 隐藏测试 `r2e_tests`：不可见，也没有尝试寻找。
- 上游后续提交或 PR：按角色卡没有查。

**必须保留的两个限制：**

1. `user_prompt.txt` 只是 `render_user_prompt` 的静态渲染，不是捕获的模型实际消息。
2. `worktree/` 不是完整的运行容器（没有 `.venv`、编译产物、`.git` 和隐藏测试）。

本报告没有验证模型实际收到的消息、运行资源或开发条件；§4 中所有"预期"都是阅读推断。
