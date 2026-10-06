# orange3__9b5494e26f407b75e79699c9d40be6df1d80a040

> **2026-09-25 协调者更正（按 Codex 复核 r2e_static_actor_review_20260925/README.md）**：诊断归因按 Codex 复核 R2 收窄：只错 test_auto_solver 的补丁只标'疑似接口不符'，要核 L1 是否真的生效（W1 同样只错这一键，但把 L1 静默换成 L2）。修订方向上，行为级测试比把 auto / 私有钩子写进题面更能保留解法空间，并且要保留 L1 要求，不能只检查不报错。 以下原文保留不改。

**题目：**base `43f086f0`。`LogisticRegressionLearner(penalty='l1')` 在默认 lbfgs 下抛出 ValueError，题面要求"自动选择支持该 penalty 的 solver"。

**材料：**修订 r2e-mr-020，配方 `r2e_derive_v1+env_v2`（SciPy 1.5.4）。

**处置：**`needs_review` / `static_review`，属题意/测试争议。
- 用途：只作 development_diagnostic，并附"接口被钉死"的说明。
- 不作留出评测：另外 5 道 orange3 题的公开工作树里有本题答案。
- 作 reward 前：先 CPU 校准替代解，再由用户决定修订方向。

## 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 状态 | 执行证据或下一验证 |
| --- | --- | --- | --- | --- |
| L1 拟合不再报错 | 题面原例 | `test_probability`：`iris[:100]` 二分类；断言偏弱，任一行概率和恰为 1 即通过 | 部分：题面原例是三分类，未测 | noop 抛题面原句；gold 13/13 ×2（B5） |
| 自动选择支持该 penalty 的 solver | 题面 Expected Behavior | `test_auto_solver`：接受 `solver="auto"`；私有 `_initialize_wrapped()` 返回时已解析；L1 必须是 `liblinear`；`penalty=None` 透传 | 冲突/过严 | 候选实跑，见下 |
| 默认 l2 行为不变 | base 默认、公开测试 | 9 个 PASSED 回归键（含修订恢复的 `test_LogisticRegression`、`test_coefficients`）；2 个 scorer 键期望 FAILED | 覆盖 | noop 与 gold 在这些键上一致 |
| 默认 repr、pickle、显式 solver 组合、`'none'` | 公开 `test_util` 等 | 无隐藏键 | 缺失（不计分） | gold 下 repr 子集 5 passed（私有对照，root） |

## 八方面

**已查：**
- 题面与 hints。
- 哈希与初态。
- 13 键全部展开并追到调用链。
- 6 类替代解的静态推演。
- gold 与调用者。
- actor 条件：devcheck，正式启动链加 CC 2.1.205，agent 54321，与评分同一镜像 ID。
- 评分边界与预检。
- 修订 r2e-mr-020 与环境配方绑定。
- 池内 7 道 orange3 题的公开源码关系。

**未查：**
- 真实渲染的任务消息（留探针阶段）。
- 任何非 gold 候选的实跑。
- 真实模型求解。
- 正式链的镜像选择（环境卡 §2，B 线接线中）。
- R8/R9/elasticnet 行为与控件的 L1 路径。

## 问题与证据层次

1. **P1 · 接口被钉死**（静态推断；noop 在同一处失败：`'auto' != 'lbfgs'`）。不加 `"auto"`、L1 选 saga、在 `fit` 里解析、显式映射表这几种合理修复，都满足题面，却会判 0。
2. **P2 · 跨题暴露**（精确源码对照）。`4014f248`、`22e98f8f`、`50f6a758`、`f5026689`、`c3fb72ba` 的公开 base 里逐字含有本题 gold 与 `test_auto_solver`。
3. **P3 · 两个 FAILED scorer 键是上游过时期望。**
   - 后来的上游在代码和数据都相同的情况下，把这三处断言改成了本题实测值（`'chest pain'`、`'legs'`），因此是死键。
   - 只有把默认模型改回 liblinear 一类的改动才能翻转它们，而这类改动本就过不了 `test_auto_solver`。
   - 可以关闭历史 open item "原因未定位"。
4. **P3 · 开发噪声。**
   - 公开 LR 测试文件在修好后仍有 2 个既有失败。
   - 控件测试因 orange-widget-base 漂移，在 base 与 gold 上都失败。
   - hints 的 conda 措辞（E09）。
5. **修订 r2e-mr-020 核对通过**：两个恢复键的原失败来自 SciPy 1.7.3 下 `optimize.py:243` 的 `.decode`，修订后评分更严而非更宽。它只在 `+env_v2` 上成立，正式 actor 必须用派生镜像。

## 候选补丁（供协调者实跑，全部只改 `Orange/classification/logistic_regression.py`）

**正对照（预期 reward 1）：**
- **P1**：在 `LogisticRegressionLearner.__init__` 里把默认值改成 `solver="auto"`，并在 `self.params = vars()` 之前加一行 `if solver == "auto": solver = "liblinear" if penalty == "l1" else "lbfgs"`，不覆盖 `_initialize_wrapped`。预期 13/13。公开 `test_util` 的默认 repr 会变，但不计分。
- **P2**：gold 原样，在 `_initialize_wrapped` 的 `if solver == "auto":` 分支里加 `elif penalty == "elasticnet": solver = "saga"`。预期 13/13。

**合理替代（预期 reward 0，题面原例都能通过）：**
- **V1**：保留默认 `solver="lbfgs"`，新增 `_initialize_wrapped`：复制 params；当 `penalty == "l1"` 且 `solver == "lbfgs"` 时改为 `"liblinear"`；其余原样，最后 `return self.__wraps__(**params)`。预期 `test_auto_solver` 第 1 条 `'auto' != 'lbfgs'`，12/13。
- **V3**：gold 原样，只把 `solver = "liblinear"` 改成 `solver = "saga"`。预期 `test_probability` 仍 PASSED，`test_auto_solver` 第 3 条 `'saga' != 'liblinear'`，12/13。
- **V4**：默认改成 `solver="auto"`，不覆盖 `_initialize_wrapped`，改为覆盖 `fit(self, X, Y, W=None)`：`"auto"` 时按 gold 规则把结果写入 `self.params["solver"]`，再 `return super().fit(X, Y, W)`（同 `KNNBase.fit` 先例）。预期 `test_auto_solver` 第 1 条 `'auto' != 'lbfgs'`，12/13。
- **V5**：gold 的 `"auto"` 分支改成 `solver = {"l1": "liblinear", "l2": "lbfgs", "none": "lbfgs", "elasticnet": "saga"}[penalty]`。预期 `penalty=None` 那条抛 KeyError，`test_auto_solver` FAILED，12/13。
- **V7**：只把 `__init__` 的默认值 `solver="lbfgs"` 改成 `"liblinear"`（Orange 较早版本的默认值，git 历史可见）。预期 `test_auto_solver` FAILED，reward 0；请同时记录 scorer 两键是否翻成 PASSED，以验证"过时期望"的解释。

**错误解（预期 reward 0）：**
- **W1**：gold 原样，在 `"auto"` 分支之前加 `if penalty == "l1": params["penalty"] = penalty = "l2"`，即静默丢掉 L1。预期 `test_probability` PASSED（说明它单独抓不住这类错误），`test_auto_solver` 第 3 条 FAILED，12/13。

## 建议与唯一下一步

**唯一下一步：**在 `+env_v2` 派生镜像上用真实 RH2 评分跑以上 8 个候选。

**实跑之后，由用户在三条路中选：**
- (A) 题面最小补全：写明新增 `solver="auto"`、L1 用 liblinear、在创建估计器时解析。缺点是接近把测试抄进题面，而且不点名私有方法仍会误拒 V4。
- (B) 把 `test_auto_solver` 改成行为级检查：这是改 oracle，需要独立复核，并做正反对照。
- (C) 原样只作诊断题，统计时单列。

**独立 reviewer：**目录里已出现 reviewer 初判，本主审没有读，本卡不含其结论。

**详细材料：**[历史前分析](analysis_before_history.md)（其中"批内唯一 orange3 题"一句已在增量中更正）；[历史对照增量](old_findings_delta.md)。

**暴露：**主审已见隐藏测试、gold、期望、运行日志、历史调查和其它 orange3 题的公开源码，不得充当本题独立 solver。
