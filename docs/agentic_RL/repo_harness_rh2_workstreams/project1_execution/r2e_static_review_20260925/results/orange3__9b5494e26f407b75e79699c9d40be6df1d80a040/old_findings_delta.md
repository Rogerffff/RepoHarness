# orange3__9b5494e26f407b75e79699c9d40be6df1d80a040：历史对照增量

2026-09-25 · R2E 私有主审。

**前稿：**
- 历史前稿 `analysis_before_history.md` 已由协调者原样保存，文件头加了一行来历注释；含该注释的文件 SHA256 = `03e5fab9…4840e`。本文不改前稿。
- 协调者开放 `history/…/refs.json` 之后，本文才读下列历史件。
- 没有独立 reviewer 文件可读。

**读过的历史件**（均在 `docs/…/project1_execution/r2e_env_repair_20260924/` 下，下文用字母代称）：

| 代称 | 文件 | 读取范围 |
| --- | --- | --- |
| A | `tasks/orange3__9b54…/screening_record.json` | 全文 |
| B | `tasks/…/findings.md` | 全文 |
| C | `tasks/…/facts.json` | 全文 |
| D | `known_issues.json` | 三个族：`expected_non_passed_keys`、`prompt_quality_candidates`、`dependency_artifact:orange3_9b5494e2_sklearn_scipy` |
| E | `decisions.md` | E05/E09/E12/E14/E17/E20–E24/T0-7 行 |
| F | `material_revisions/orange3__9b54….md` | 全文 |
| G | `repros/orange3__9b54….py` | 全文 |
| H | `packages/p3/README.md` 与 `results_20260924.md` | 只读与本题相关的行 |

另读了 A 引用的 E17 诊断原始日志（`runs/r2e_t0_batch2_20260924/diag_orange3/` 下的 `s141_gold_a`、`s154_gold`、`s141_noop` 三个 `.test.log`，grep）和 `runs/r2e_env_repair_20260924/p3/fixture_check/orange3_9b5494e2_versions.txt`。

**新调查：**因为 A 的 R20 提到同仓其它题，本轮打开了池内另外 6 道 orange3 题的**公开**工作树（`runs/r2e_static_prep_20260924/v2/public/orange3__*/worktree`），只比对 LR 学习器、scorer、预处理、数据和 LR 测试文件。

## 1. 旧主张逐条处置

| 旧主张（来源） | 处置 | 决定性证据与范围 |
| --- | --- | --- |
| 期望里 4 个 FAILED 都是 scikit-learn 0.22.2.post1 × SciPy 1.7.3 的依赖伪影；scorer 两键"推断同源"（B、D 的 dependency 族与 expected 族、F、H §50） | **部分推翻** | 两个恢复键确认：来源环境 gold 日志中 `test_coefficients` 失败于 `sklearn/utils/optimize.py:243` 的 `.decode`；`test_LogisticRegression` 是 CV 吞掉同一失败后，未初始化的预测数组（`6.43e-310`）触发 CA 的 ValueError。scorer 两键不同源：E17 已发现，本轮三份诊断日志再核一遍，SciPy 1.4.1、1.5.4、1.7.3 下失败文本逐字相同（`'chest pain'`、`'legs'`）。 |
| scorer 两键"原因未定位"（A 的 `open_items.grading_keys_unexplained`、D、F 文首） | **推翻（已定位）：上游过时期望** | 见下方"scorer 两键定位"。 |
| "是否对所有候选都恒为 FAILED 未验证"（A 的 open_items；E 的 Codex R2 撤回） | **收窄，仍未实跑** | 能通过 `test_auto_solver` 的实现，必须把 auto+l2 解析为 lbfgs，默认 l2 模型与 gold 相同，这两键保持 FAILED。能把它们翻成 PASSED 的，只有让默认模型回到 liblinear 时代输出的改动（候选 V7：默认改回 `liblinear`）；这类改动本就因 `test_auto_solver` 得 0。静态推断，未执行。 |
| F 原推荐 A："所有正确解都恒 FAILED、假阴性风险低" | **过时** | 历史内已由 Codex R2 撤回，后按 T0-7 改为方案 B 实施。另外它漏掉了本题真正的假阴性来源——`test_auto_solver` 钉死接口（见下）。 |
| H §50："`test_auto_solver` 要求 l2 仍用 lbfgs，所以正确解都会走到不兼容路径——假阴性风险低" | **过时** | `+env_v2` 下不兼容路径已消失（lbfgs 未收敛只发警告）。该句的"假阴性风险低"不适用于接口过严问题。 |
| F 方案 B："这 4 键预计变 PASSED（未验证）" | **推翻（对 scorer 两键）** | 实测只翻了 2 键：B5 gold 13/13 的日志里 scorer 两键仍 FAILED；E17 诊断相同。 |
| T0-7 方案 B：`env_pins_v2`（scipy 1.5.4，`+env_v2`）加 `r2e-mr-020`；真实 grader noop 0（11/13）×2、gold 1（13/13）×2（A、E23/E24） | **确认** | `B5/ledger_b5_{noop,gold}.jsonl` 第 13–14 行：`recipe_id=r2e_derive_v1+env_v2`，镜像 ID `f27e31c68aad…`，评分用户 54322，deny_all。4 份日志 sha 与 `run_refs.json` 一致，重复运行之间只有时间戳不同。期望前后哈希本地重算一致（`9645a5c3…` → `cd034086…`）。 |
| "`r2e-mr-020` 只在 `+env_v2` 镜像上成立"（F、E23） | **确认** | 来源环境（SciPy 1.7.3）下 gold 在这两键上是 FAILED（R-f gold 日志、M3 a1/a2）。修订后的期望配来源镜像会让 gold 得 0。 |
| E17：SciPy 1.4.1 / 1.5.4 下两个恢复键 PASSED，scorer 两键仍 FAILED（gold 3 次、noop 2 次） | **确认** | `s141_gold_a`、`s154_gold`、`s141_noop` 三份日志 grep 结果与该结论一致。 |
| "`test_auto_solver` 要求 `solver="auto"` 字面值，题面只说自动选择"（B、A 的 R16、D 的 prompt_quality 族） | **确认并扩大** | 该测试钉死的不止 `"auto"`，共 4 项：`"auto"` 取值；私有 `_initialize_wrapped()` 返回时已解析；L1 必须是 `liblinear`；`penalty=None` 原样透传。据此有 4 类满足题面却判 0 的替代解（V1、V3、V4、V5，前稿 §5）。静态推断，旁证是 noop 同型失败（`'auto' != 'lbfgs'`，B5 noop 日志第 35 行）。 |
| 公开测试 `Orange/tests/test__orange.py` rc=0；复现 `REPRO_OBSERVED=1`（A 的 R09，B） | **确认，但范围不足** | `test__orange.py` 与本题无关。devcheck（正式启动路径、CC 2.1.205、agent 54321）跑了相关文件：base 上 3 个失败（`test_probability` 加 2 个 scorer），私有 gold 对照后剩 2 个；控件测试在 base 与 gold 上都有 3 个失败，原因是 orange-widget-base 版本漂移（旧记录未提）。复现与 devcheck 的 mcve 一致。 |
| "求解者本地跑 `test_logistic_regression.py` 会看到同样 4 个与修复无关的失败"（A 的 solver_conditions、B） | **过时** | 这是修订前、来源环境下的描述。`+env_v2` 下实为：base 3 个失败（含 1 个目标），正确修复后 2 个（`DC/orig/captures/test_lr.out`、`private_gold/private_control.json`）。 |
| 解释器、pip、网络、git 卫生（A 的 R05/R07/R10/R17） | **确认**（actor 层）；两项未核实 | devcheck `env.out`：python 指向 `.venv`，pip 24.0。`prelaunch.json`：`DNS_EXTERNAL=DENIED`，`/testbed` 属主 54321。预检三项 ok，git 无 refs、remote、reflog，工作区只有 3 个未跟踪项。site-packages 可写与 cwd=/tmp 导入本轮未复核。 |
| 资源：gold 峰值 1238 MB，setup 83 s，测试 2.7 s，chown 89 s / 1.5–4 min（A 的 R12、costs，C） | **过时**（仍在限额内） | 当前 4 行：峰值 1174–1189 MB，可信 setup 32.9–34.8 s，测试 1.78–1.84 s（B5 ledger）。devcheck 从容器启动到可信初始化完成约 35 s（`attempt.json` 时间戳，单次观测，不作校准）。 |
| `public_hints` 的 conda 说法对 R2E 不成立（A 的 R03、E09） | **确认**；真实消息仍未知 | 协调者说明：模型收到的题面由 prepared 任务面渲染，与 `user_prompt.txt` 同源；hints 的实际注入留到探针阶段捕获。devcheck 的用户消息是桩文本。 |
| hygiene：测试文件为 `r2e_tests/{__init__.py,test_1.py}` 加 `run_tests.sh`，gold 只碰 LR 文件（A 的 R04） | **确认** | 日志 `RH2_SETUP_EXPECTED_TEST_FILES=3`；`gold.patch` 只改一个文件。 |
| 同仓其它题依赖组合不同，不自动继承（A 的 R20） | **确认但不完整；新增关系** | 另外 5 道 orange3 题的公开 base 已含本题 gold 的 `_initialize_wrapped`（逐字相同）和 `test_auto_solver`：`4014f248`（3.27.1）、`22e98f8f`（3.28.0）、`50f6a758`（3.31.0）、`f5026689`（3.36.0）、`c3fb72ba`（3.36.1）。`f237f968` 的 base 更早，默认 solver 还是 `liblinear`。旧记录没有登记这层跨题暴露。 |
| 处置 `grading_ok_open_items`（A、H） | **保留其评分环境范围**；本轮静态处置另记 | 历史处置管评分环境；本轮是题意/测试范围，给 `needs_review`（`test_auto_solver` 过严）。建议协调者把 `grading_keys_unexplained` 改为"已解释：上游过时期望，死键"；本文不改历史记录。 |

### scorer 两键定位（对第二行的证据展开）

这两个测试断言在不同 base 上的演变：

| 公开工作树 | 默认 solver | scorer 断言 |
| --- | --- | --- |
| `f237f968`（更早的 base） | `liblinear` | 与本题相同：`'major vessels colored'`、`'aquatic'`（两栖类）、`'hair'`（爬行类） |
| 本题 base `43f086f0`（3.25.0 之后，已加 `<0.23` 临时 pin） | `lbfgs` | 仍是上面那组旧值 |
| 此后 5 道题（最早 `4014f248`，3.27.1） | `"auto"`（即 gold） | 同三处改成 `'chest pain'`、`'legs'`（两栖类）、`'aquatic'`（爬行类） |

本题实测的失败值正是后来这组新值（`'chest pain'`、`'legs'`）。

排除环境原因的依据：
- 本题 base 加 gold 与 `4014f248` 的 LR 源码完全相同。
- `LearnerScorer`、`Continuize`、`SklLearner.preprocessors` 相同。
- `heart_disease.tab`、`zoo.tab` 字节相同。
- `normalize.py` 的差异只涉及 `number_of_decimals` 显示元数据，不改变数值变换。

结论：Orange 把默认 solver 从 liblinear 换成 lbfgs 时，没有同步更新这两个测试的期望，后来上游才改。所以在本题提交上，上游这两个测试本就失败。这是确定性的死键，不是环境问题，也不是本题意图。

## 2. 主审对自己前稿的改判

1. **scorer 两键根因**：前稿写"未定位，弱倾向上游"，现改为"已定位：上游过时期望"。理由是上述跨 base 对照。评分影响不变（低），但可以关闭历史 open item。
2. **"批内唯一的 orange3 题（据环境卡）"是错的**：环境卡只列了带配方身份的题，池内实际有 7 道 orange3 题。清单第 5 项由 not_checked 改为 issue，新增跨题暴露问题：本题答案与目标测试出现在另外 5 道题的公开工作树里。这对留出评测是硬约束；训练时只要模型读到这些题的 `logistic_regression.py`，就能接触到答案。
3. **新增候选 V7**（默认改回 `liblinear`）：来自 `f237f968` 的线索，git 历史中也可见。预期 0：`test_auto_solver` 失败，scorer 两键可能翻成 PASSED。实跑可以顺带验证过时期望的解释。
4. **不变的部分**：主要问题（`test_auto_solver` 钉死接口，合理替代解判 0）、修订 r2e-mr-020 的核对、gold 判断、开发需求。历史只把该问题记为"题意明确度"，没有展开替代解和严重度；本轮维持 P1。

历史也没有执行过任何非 gold 候选，所以"合理替代解判 0"仍是静态推断，不能把新旧两份记录的叙述叠加成执行证据。

## 3. 唯一下一步

在 `+env_v2` 派生镜像上走真实 RH2 评分，跑 `card.md` 列出的候选：
- V1、V3、V4、V5：预期 0；
- P1、P2：预期 1；
- W1：预期 0；
- V7：预期 0，并记录 scorer 两键的状态。

结果出来后，由用户在三条路里选：题面最小补全、测试行为级修订、原样只作诊断。
