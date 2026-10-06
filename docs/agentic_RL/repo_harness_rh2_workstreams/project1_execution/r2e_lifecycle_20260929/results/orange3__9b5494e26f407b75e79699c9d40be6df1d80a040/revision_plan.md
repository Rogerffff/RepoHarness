# orange3 `9b5494e2`：R-b / R-e 行为级测试修订（2026-09-29，修订执行者）

**结论：修订定稿，试跑通过；一轮修订、一轮验收，收敛。**
- 主修订 A 把 `test_auto_solver` 从"钉接口"改成"拟合后看行为"。
  - 此前被误拒的 4 个合理解（V1 / V3 / V4 / V5）全部由 0 变 1。
  - gold 仍为 1，noop 仍为 0。
  - 两个已知错误候选仍为 0：W1 把 L1 静默换成 L2；V7 把默认 solver 改成 liblinear。
  - 键名、键集合、期望映射都不变；`r2e-mr-020` 不动。
- 另有一个 v1 §11 没列的额外 S1：P1 得 1，却破坏公开回归测试 GH 2275（默认 repr）。这一项单列，可以单独拿掉。
  - 修法 B′（推荐）：把断言并进同一个测试，不动期望，已试跑。
  - 修法 B：新增文件和新键，已试跑，但正式落地成本更高（§7）。
- 全部 20 次都是试跑，不是正式评分；材料落地后要按 §10 走正式评分，再由 Codex 复核。

草案：同目录 `revision_draft.json`。试跑结果：`trials/`，其中 `trials/inputs/` 是本次上传的草案原件。路径均相对仓库根，缩写如下：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040`
- `PRIV` = 同题 `…/v3/private/…`
- `GC` = `runs/r2e_actor_20260925/grader_cands`
- `R1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925`（首批审查）

## 1. 要纠正的误判（触发反例）

当前 `test_auto_solver`（`PRIV/hidden_tests/test_1.py:135-153`）钉死了四个题面没有提到的接口细节。首批正式评分（`R1/grader_candidates.md:35-43`，`+env_v2` 派生镜像）结果如下：

| 候选（补丁） | 做法 | 当前材料得分 | 被哪条钉死 |
| --- | --- | --- | --- |
| V1（`GC/orange3_9b54_OR1_…`） | 保留默认 lbfgs，l1 且 lbfgs 时改 liblinear | 0（12/13） | 必须接受 `solver="auto"` 字面量（`:138`） |
| V3（`GC/orange3_9b54_OR2_…`） | 哨兵 `"auto"`，l1 用 saga | 0 | l1 必须是 `liblinear`（`:152`） |
| V4（`GC/orange3_9b54_V4_…`） | `"auto"` 在 `fit` 里解析 | 0 | 私有 `_initialize_wrapped()` 返回时必须已解析（`:139/:145/:151`） |
| V5（`GC/orange3_9b54_V5_…`） | 映射表，查不到 `None` | 0 | `penalty=None` 原样透传（`:144-147`）。scikit-learn 0.22 拟合时本来就不接受 `None`（合法取值见 noop 日志里的 `_check_solver`：`['l1', 'l2', 'elasticnet', 'none']`） |

- 首批 Codex 复核的方向（`docs/.../r2e_static_actor_review_20260925/README.md:65`）：行为级测试比把 `auto` 和私有钩子写进题面更能保留解法空间，但要保留 L1 要求，不能只检查"不报错"。
- 同一复核的 R2（同文件 `:37`）：W1 只错 `test_auto_solver`，但它把用户指定的 L1 静默换成 L2，必须继续算错。

## 2. 模板

- **R-b**：把没有公开依据的实现约束放宽为有依据的行为断言，包括 `"auto"` 字面量、私有钩子、l1 必须 liblinear、`None` 透传。
- **R-e**：用真实拟合代替对内部钩子的检查，正例与反例都覆盖。
  - 正例：l1 真的生效。
  - 反例 1："一律换成支持 l1 的 solver"（V7）要被拒；具体检查是默认 l2 仍用 lbfgs。
  - 反例 2："忽略用户的 l1"（W1）要被拒。
- 范围：只改这一个测试的函数体。任务目标、其它键、期望映射都不动。

## 3. 公开依据（题面：`PUB/user_prompt.txt`）

| 断言 | 依据 |
| --- | --- |
| l1 拟合不再报错 | 标题 `:4`；`:6` 说报错原因是 "the solver does not support the L1 penalty"；示例 `:10-11`；期望 `:20` 要求 "allowing the use of `penalty='l1'` without errors" |
| 拟合出的模型真的用 l1（`skl_clf.penalty == "l1"`） | `:20` 要求 "automatically select a solver that supports the specified penalty"：要换的是 solver，不是 penalty。W1 把 penalty 换掉，不算"允许使用 l1"（首批 Codex R2） |
| 所选 solver 在 `("liblinear", "saga")` 中 | 这就是 "supports the specified penalty" 在本环境里的具体集合：`:16` 的报错原文说明 lbfgs 只支持 'l2' 与 'none'；scikit-learn 0.22 的 `_check_solver`（环境里的源码，noop 日志中可见）只允许 liblinear 与 saga 配 l1。它与"带 l1 拟合成功"等价，不另加约束 |
| 默认 l2 仍用 lbfgs | base 签名的默认值 `solver="lbfgs"`、`penalty="l2"`（`PUB/worktree/Orange/classification/logistic_regression.py:37-40`）；`:16` 说明 lbfgs 支持 l2，题面只涉及 l1，没有理由改默认模型。这是原测试第 1 段（`:136-141`）保留下来的行为要求，不是新需求 |
| `'none'` 仍能拟合，penalty 保持 `'none'` | `:16` 说明 lbfgs 支持 'none'；base 上可用。这是原测试第 2 段（`None` 透传）在本环境里有意义的写法，并去掉了 solver 约束 |
| 从 `model.skl_model` 读 solver 与 penalty | `skl_model` 是公开属性：`PUB/worktree/Orange/base.py:469-473` 在 `SklModel.__init__` 里设置，本文件的 `coefficients` / `intercept`（`logistic_regression.py:22-29`）也通过它取值 |

## 4. 改动 A（`r2e_tests/test_1.py`，`hidden_test_text_replace`，一处替换）

把整个 `test_auto_solver`（`:135-153`）换成：

```python
    def test_auto_solver(self):
        # Behaviour-level check: the learner has to use a solver that supports
        # the requested penalty. Where and how the solver is chosen (constructor,
        # a sentinel value, fitting time) is not prescribed.

        # l1, the reported case: fitting works and the fitted model really uses
        # l1, on the multiclass data of the report and on binary data
        for data in (self.iris, self.heart_disease):
            skl_clf = LogisticRegressionLearner(penalty="l1")(data).skl_model
            self.assertEqual(skl_clf.penalty, "l1")
            # the scikit-learn 0.22 solvers that support l1
            self.assertIn(skl_clf.solver, ("liblinear", "saga"))

        # l2, the default penalty, is supported by the default solver lbfgs:
        # the default model is unchanged
        skl_clf = LogisticRegressionLearner()(self.zoo).skl_model
        self.assertEqual(skl_clf.solver, "lbfgs")
        self.assertEqual(skl_clf.penalty, "l2")

        # no penalty is supported by lbfgs as well and keeps working
        skl_clf = LogisticRegressionLearner(penalty="none")(self.iris).skl_model
        self.assertEqual(skl_clf.penalty, "none")
```

| 原断言 | 处理 | 新断言（修订后行号） |
| --- | --- | --- |
| `penalty="l2", solver="auto"` → `_initialize_wrapped()` 的 solver 为 lbfgs、penalty 为 l2 | 保留行为，去掉 `"auto"` 与私有钩子 | 默认学习器在 zoo 上拟合，solver 为 `"lbfgs"`、penalty 为 `"l2"`（`:150-152`） |
| `penalty=None, solver="auto"` → lbfgs 且 `None` | `None` 在 0.22 里拟合即报错，没有行为意义；改成合法写法 `'none'` 并实际拟合，不再约束 solver | `penalty="none"` 在 iris 上能拟合，penalty 仍为 `"none"`（`:155-156`） |
| `penalty="l1", solver="auto"` → liblinear 且 l1 | 去掉"必须 liblinear"与私有钩子，改成真实拟合；加一个非示例数据集 | 在题面原例 iris（三类）与 heart_disease（二类，含离散与缺失值）上拟合，penalty 为 `"l1"`，solver 属于 `("liblinear", "saga")`（`:142-146`） |

- **数据集的选择**：
  - 默认 l2 段用 zoo，因为同文件 `test_predict_on_instance` 拟合的是同一个默认模型，在来源镜像的 SciPy 1.7.3 下也是 PASSED（`PRIV/revisions.json` 里 r2e-mr-020 的 reason 只把另外两个键记为失败），说明这里不会走 lbfgs 未收敛的分支。
  - l1 段走 liblinear / saga，不经过 scipy.optimize。
- **修订后仍受保护的公开要求**：
  - l1 能用：`test_auto_solver` 与 `test_probability`；
  - l1 真的生效、所选 solver 支持它：`test_auto_solver`；
  - 默认 l2 模型不变：`test_auto_solver` 的 l2 段，加上 `test_LogisticRegression`、`test_coefficients` 等 9 个回归键；
  - `'none'` 可用：`test_auto_solver`。

## 5. 期望映射的逐键变化

- **无**：13 个键及其状态都不变，`test_auto_solver` 仍期望 PASSED（noop FAILED、gold PASSED，仍是目标键）。
- 不需要新的期望修订；`r2e-mr-020` 原样保留，它的 `+env_v2` 绑定也不变。
- 变化的只有隐藏测试文件：`test_1.py` 的摘要从 `sha256:99459c0d…` 变为 `sha256:f5989a51…`；采用 B′ 时变为 `sha256:be3b9ff0…`。

## 6. 验收（试跑）

**条件**：
- 工具：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`。
- 镜像：R2E 机上本题派生镜像 `sha256:c108281a4cac…`，配方 `r2e_derive_v1+env_v2`（与原批准配方相同，没有构建配置步骤）。
- 每次试跑都核对了：补丁 `RH2_APPLY_RC=0`、草案 `RH2_TRIAL_EDITS_APPLIED`、观测键数，以及失败断言的行号与原因。
- 耗时：每次 3–6 分钟，其中测试本身 6–13 秒，其余是容器准备。

**环境确认（当前材料，不带草案）**：
- noop：mismatch，`test_auto_solver` 与 `test_probability` 为 FAILED（`trials/env_noop_current.json`）；
- gold：match，13/13（`trials/env_gold_current.json`）。

**主修订 A**：

| 候选（补丁 sha256 前 16 位） | 角色 | 应得 | 试跑 | 不符的键 / 失败位置 |
| --- | --- | --- | --- | --- |
| gold（`162ad8b40ffa96b9`） | 正对照 | 1 | `A_gold.json`：match | — |
| noop | 空补丁 | 0 | `A_noop.json`：mismatch | `test_auto_solver`（`:143` l1 拟合抛题面原句 ValueError）、`test_probability` |
| V1 / OR1（`396487018a5b67ee`） | 原误拒 | 1 | `A_OR1.json`：match | — |
| V3 / OR2（`3d05c2c8869c4dc7`） | 原误拒 | 1 | `A_OR2.json`：match | — |
| V4（`825529c1ff973934`） | 原误拒 | 1 | `A_V4.json`：match | — |
| V5（`63af6eef082dc404`） | 原误拒 | 1 | `A_V5.json`：match | — |
| W1（`b32a5a9bcc016fb1`） | 已知错误：静默 l1→l2 | 0 | `A_W1.json`：mismatch | 只错 `test_auto_solver`，`:144` `'l2' != 'l1'` |
| V7（`e3248d441d54e5d7`） | 已知错误：默认改 liblinear | 0 | `A_V7.json`：mismatch | `test_auto_solver`（`:151` `'liblinear' != 'lbfgs'`），两个 scorer 死键翻成 PASSED |
| P1（`d6717cb60f1724d8`） | 修好题面但改默认 repr | 1（主修订下） | `A_P1.json`：match | 见 §7 |
| P2（`5c81aacc0b064d44`） | 合理解 | 1 | `A_P2.json`：match | — |
| G1（`00ba0b7c78014060`） | gold + 默认 multi_class 改 ovr | 1（已登记缺口） | `A_G1.json`：match | 见 §8 |

补丁文件都在 `GC/`；gold 在 `PRIV/gold.patch`。对照 v1 §5 的四项验收：
- 正对照 1、noop 0：满足；
- 要纠正的误判已纠正：V1 / V3 / V4 / V5 都为 1；
- 已知相关的错误候选仍为 0：W1、V7；
- 公开核心要求有直接断言：见 §4 末尾。

## 7. 额外 S1（单列，可单独拿掉）：P1 破坏公开 GH 2275 repr 测试

**事实**：
- P1 在 `__init__` 里把 `"auto"` 解析掉。`params["solver"]` 于是变成 `"lbfgs"`，与签名默认值 `"auto"` 不同。
- `Reprable` 只省略与签名默认值相等的参数（`PUB/worktree/Orange/util.py` 的 `_reprable_omit_param`；文档字符串示例 `C(1, 2)` → `C(a=1)`），所以默认学习器的 repr 从 `LogisticRegressionLearner()` 变成 `LogisticRegressionLearner(solver='lbfgs')`（试跑实测，见下表）。
- 这破坏了公开回归测试 `PUB/worktree/Orange/tests/test_util.py:57-60`：`# GH 2275`，要求 `repr(LogisticRegressionLearner())` 连调两次都等于 `'LogisticRegressionLearner()'`。
- 上游采用 `solver="auto"` 之后仍保留这条断言：同仓后续题 `4014f248`、`50f6a758`、`c3fb72ba` 的公开工作树中，`Orange/tests/test_util.py:63-66` 与 `logistic_regression.py:39-40` 的 `solver="auto"` 并存。
- 首批主审已注意到，但当时按"不计分"放过（`R1/results/orange3__9b5494e2…/card.md:60`）。

**为什么按 §4 第 4 步算 S1**：
- P1 是首批审查中已构造、已评分的候选（`R1/grader_candidates.md:35`，1 分）。
- 它破坏的是仓库里有公开回归测试、并关联 GitHub issue 的行为，属于"有文档的公开行为"。
- 默认学习器是最常用的对象。
- 修法按 R-c "复用现成的公开测试"。

**反面考虑**：repr 也可以看成外观细节、按 S2 处理。所以这一项单列，由复核决定去留。

**B′（推荐）**：把 GH 2275 的断言放进 `test_auto_solver`，写在 l2 段之后：

```python
        # the default learner keeps an argument-free repr, also when repr is
        # called repeatedly (same check as the public Orange/tests/test_util.py,
        # TestUtil.test_reprable, "GH 2275")
        logit = LogisticRegressionLearner()
        for _ in range(2):
            self.assertEqual(repr(logit), 'LogisticRegressionLearner()')
```

B′ 与 A 仍是同一条 `test_1.py` 修订：用 A′ 的 new 文本替换 A 的 new 文本，全文见草案 `optional_extra_s1.B_prime`。不加键、期望不变、`r2e-mr-020` 不动。拿掉 B′ 就用回 A。

| 候选 | 应得 | 试跑 | 说明 |
| --- | --- | --- | --- |
| gold | 1 | `A2_gold.json`：match | gold 保留 `params["solver"] == "auto"`，repr 不变 |
| noop | 0 | `A2_noop.json`：mismatch | `test_auto_solver`、`test_probability` |
| P1 | 0 | `A2_P1.json`：mismatch | 只错 `test_auto_solver`：`:158` `"LogisticRegressionLearner(solver='lbfgs')" != 'LogisticRegressionLearner()'` |
| V4 | 1 | `A2_V4.json`：match | V4 在拟合时改 `self.params`，而新断言用未拟合的新学习器，与公开测试一致；确认它不误拒 V4 |

**B（备选，已试跑，落地成本高）**：
- 做法：新增 `r2e_tests/test_2.py`（`hidden_test_file_add`，target 与 A 不同，是独立的一条修订），类 `TestLogisticRegressionDefaultRepr`，新键 `TestLogisticRegressionDefaultRepr.test_default_learner_repr: PASSED`。
- 试跑：gold 为 match 14/14（`AB_gold.json`）；noop 为 mismatch，失败的仍是那两个键，新键 PASSED（`AB_noop.json`）；P1 为 mismatch，只错新键，位置 `test_2.py:16`（`AB_P1.json`）。
- 期望要加键，所以要**在 r2e-mr-020 基础上合并为一条新修订**：
  - 类型：`expected_file_replace`，替代 r2e-mr-020；
  - 相对来源期望：changed 为 `test_LogisticRegression`、`test_coefficients` 两键 FAILED→PASSED（即 r2e-mr-020 的内容），added 为新键 PASSED，removed 为空；
  - 草案以 r2e-mr-020 之后的期望为起点，见 `optional_extra_s1.B.expected_after`。
- 需要合并的原因：正式机制对同一题的同一目标只允许一条修订（`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:415-418`），而增删键只能用 `expected_file_replace`（同文件 `:403-404`）。
- **额外成本**：
  - `rh2/src/repoharness2/envpack/environment_overlay.py:55-60` 的 `REVISION_ENV_REQUIREMENTS` 以修订编号 `r2e-mr-020` 为键，把本题绑定到 `+env_v2`；换成新编号后要跟着改键。
  - 这属于生产代码，本包不改；该处还在处理 Codex 代码复核的 P1。
  - B′ 没有这笔成本，所以推荐 B′。

## 8. 登记、不修

- **G1**（gold + 默认 `multi_class="ovr"`）在主修订下仍得 1：
  - 它改变多类数据上的默认模型（multinomial → OvR）。Orange 文档没写多类方式，只能通过 `WrapperMeta` 嵌入的 sklearn 文档间接看到（`PUB/worktree/Orange/misc/wrapper_meta.py`）。
  - G1 是复核为验证死键假说构造的题外改动，不是修复尝试。按 v1 §4 第 4 步"有文档、常用"的门槛，判 S2 / T3 登记。
  - 若复核改判 S1，可在 l2 段后加一个行为断言（**未试跑**，需要单独一轮验收）：默认学习器在 zoo 上的系数，等于显式 `multi_class="multinomial"` 学习器的系数（`np.testing.assert_almost_equal`）。
- **把 `"auto"` 解析写进基类 `SklLearner._initialize_wrapped` 的候选**（`R1/results/orange3__9b5494e2…/review.md` §3.1，会弄坏 `RidgeRegressionLearner`）：只有静态推断，没有已评分的补丁；按 §4 第 4 步"只用已有证据"，不修。
- **两个 scorer 死键**（期望 FAILED，上游过时期望）：不动。主修订后 V7 已由 `test_auto_solver` 直接拒绝，死键不再是唯一拦住它的地方。
- **`test_probability` 的弱断言**（`PRIV/hidden_tests/test_1.py:64`）：不动；L1 要求已由新测试直接断言。
- **显式 solver 与 penalty 的组合**（例如 `solver='lbfgs', penalty='l1'` 应该自动换，还是照样报错）：题面没规定，两种读法都合理。新测试有意不测，也不构成 P5。
- **V4 式"拟合时改 `self.params`"**（拟合后 repr 改变）：没有公开测试覆盖，属于实现质量差异，不断言。

## 9. 修订后按 v1 §4 复判

| 步 | 结果 |
| --- | --- |
| 1 核心要求有直接断言 | 有：`test_auto_solver` 的 l1 段，另有 `test_probability` |
| 2 只用示例字面值？ | 否：除题面原例（完整 iris）外，还有 heart_disease（二类、含离散与缺失值）和 `test_probability` 的 `iris[:100]` |
| 3 退化探测 | W1（抑制症状，作用在无关对象上）与 V7（与输入无关的固定结果）试跑都为 0。正式评分待材料落地后补 |
| 4 已有候选得 1 却违反公开要求 | P1（GH 2275）：可选修法 B′ / B。G1：登记为 S2 |
| 5 | 采用 B′ 后，已知范围内没有未处理的 S1；§8 各项登记为 S2 或未知 |

## 10. 正式落地提示（给协调者；本包不写修订单、pins 与生产代码）

1. **新修订**：
   - kind `hidden_test_text_replace`，target `test_1.py`；
   - `sha256_before` 为 `sha256:99459c0d733eb09bcd58548935857702b15920646a51610722362a948709cb9b`（来源文件，本题此前没有测试修订）；
   - `sha256_after` 为 A 的 `sha256:f5989a51bd3379a88d507ed54f5fbcf4af42c3b5efb1101706ab602797a6ab32`，或 B′ 的 `sha256:be3b9ff02bf8b2f28371176844d6ff9cce940c1a9e1148406bf80cd7e46c19f4`；
   - `revised_file` 放在 `s2_r2e/revisions/` 下，`expected_change` 为 null。
   - 本题的 `material_revisions` 变为 `r2e-mr-020` 加新编号，`+env_v2` 绑定仍经 `r2e-mr-020` 生效。
2. **派生镜像**：隐藏测试树摘要会变，要按原配方 `r2e_derive_v1+env_v2` 重建材料步骤。重建时，Codex 代码复核的 P1（构建端与消费端配方摘要口径不一致）仍适用于本题。
3. **正式评分**（在新镜像上）：noop、gold、W1、V7、V1 / V3 / V4 / V5；采用 B′ 时加 P1。应得分同 §6、§7。
4. **Codex 复核**：本修订与额外 S1 的取舍，都要经过 Codex。
5. **记录**：父版本（`test_1.py` `99459c0d…`、期望 `cd034086…`、树 `9a87bfe6…`）、新版本摘要、理由（§1–§3）、触发反例（V1 / V3 / V4 / V5 误拒，W1 必须仍为 0），都在本文件与草案里。

## 11. 环境与残余风险

- 修订后的 `test_auto_solver` 与 `r2e-mr-020` 一样，只在 `+env_v2`（SciPy 1.5.4）镜像上验证过。其中 `'none'` 段是无正则拟合，**没有核实**它是否在 100 步内收敛。若不收敛，在 SciPy 1.7.3 下会触发 E17 的 `.decode` 缺陷，gold 就会失败。本题已绑定 `+env_v2`，这一条不引入新的环境要求；但如果将来去掉 `r2e-mr-020`，需要重新核实。
- 试跑与正式评分的差别（见工具文件头）：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化。所以本页的结果只作定稿依据，不等于正式验收。
- 用途结论与"可以进探针"的其余条件，不在本包范围：真实消息捕获、新镜像上的开发核对、跨题暴露 X1（首批 `card.md` 的 P2：另外 5 道 orange3 题的公开工作树含本题答案），由协调者在题卡里处理。

## 12. 暴露与阅读范围

- **读了**：
  - v1 标准、本批 README、R2E 主审角色卡"评分口径"一节；
  - 首批本题 `card.md`、`review.md`、`public_read.md`，以及 `analysis_before_history.md` 的相关段落；
  - 首批 Codex 复核与 `grader_candidates.md` 的 orange3 段；
  - 本批 Codex 代码复核；
  - `PRIV` 全部文件、`GC` 下本题全部补丁；
  - `PUB` 的题面、环境说明与相关源码和测试；
  - 另外 3 道 orange3 题公开工作树的 `test_util.py` 与 `logistic_regression.py`（只 grep 两处）；
  - ingest 的修订机制代码与 `environment_overlay.py`。
- 本会话见过 gold 与隐藏测试，不能作本题的公开读者或解题者。
