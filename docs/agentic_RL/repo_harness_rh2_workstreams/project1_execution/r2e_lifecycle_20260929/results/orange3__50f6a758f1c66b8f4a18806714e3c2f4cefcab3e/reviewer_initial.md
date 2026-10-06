# orange3__50f6a758 独立复核·第一步初判（读主审产物前封存）

独立复核子代理（干净上下文，未参与主审）｜2026-09-29 08:24（+08）｜只做静态阅读与已有运行原件核对：未运行项目代码，未开容器或远端，未改任何原件。

路径缩写（均相对仓库根）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e`
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/orange3__50f6a758f1c66b8f4a18806714e3c2f4cefcab3e`

## 0. 初判摘要

- **题目**：Color 控件（`OWColor`）载入变量定义文件时，若文件里有数据中不存在的变量，应弹出警告点名这些变量，且不报错。gold 只改 `Orange/widgets/data/owcolor.py` 的 `OWColor._parse_var_defs`。
- **当前材料的运行**：noop 0（47/48，只错 `TestOWColor.test_load_ignore_warning`），gold 1（48/48）。09-23、09-24 各跑一次，派生镜像相同；M3 独立 runner 的 gold 两次都通过。唯一目标键是 `TestOWColor.test_load_ignore_warning`。
- **初判严重度：S1**。有两个相互独立的问题：
  1. **T1（按 P3 补查后）：误拒合理解。** 唯一目标键要求警告文本与 gold 的名单格式逐字一致：3–5 个名字写成 `'a', 'b' and 'c'`；6 个以上只列前 4 个，再接 `and N other`（`PRIV/hidden_tests/test_1.py:802–820`）。题面只给了两个名字的例子。仓库里缩写名单的写法有好几种，没有一种能推出"不超过 5 个全列，超过 5 个只列 4 个"。一个始终列出全部未用变量的合理修复（C-alt1），静态预测判 0。
  2. **T2c 倾向命中，T2b 待实跑。** 核心断言只用了题面原例的输入形态：只有 categorical 段；控件没有数据，所以全部定义都未用。缺两类断言：numeric 段的未用定义要提示；已有变量与未用变量混在一起时，已有变量的定义仍要生效。退化候选"弹出警告后提前返回"（C-deg）静态预测得 1。
- **只登记的问题**：
  - P6：公开测试 `test_parse_var_defs_no_rename` 末段断言 numeric 段的未用定义不弹警告，与正确修复冲突。
  - P4：题面说应用会抛 `TypeError`；实际上这是测试在 `msg_box.call_args` 为 None 时自己报的错，不是应用行为。
  - X1：本题 gold 与目标测试逐字出现在同仓 c3fb72ba、f5026689 两题的公开初态里。
  - T3：隐藏测试把旧测试块整段删掉而不是改写，丢掉了一处重名检测的边界检查。
- **建议处置**：做一轮修订，R-b 放宽名单格式、R-c 补 numeric 与混合场景；P4 可选做 R-f。**唯一优先下一步**：用当前材料正式评分实跑 C-deg 与 C-alt1，共 2 次，分别确认 T2b 与 T1。
- **需要用户决定的事项**：无。以上修订都在 D4 预授权模板内。

## 1. 实际读取范围

- **角色与方法文档**：
  - `roles/reviewer_r2e.md`：全文。
  - `roles/investigator_r2e.md`：全文。文件很短，一次读完；四节以外的内容只是主审流程，不涉及本题。
  - `task_screening_standard_v1_20260925.md`、`r2e_lifecycle_20260929/r2e_environment_card.md`、`swegym_task_audit_20260920/quality_review_protocol_20260920.md`、`quality_batch01_20260921/record_template.md`：均全文。
- **公开包**：
  - `PUB/user_prompt.txt`、`environment_brief.md`、`public_bundle.json`：全文。
  - `worktree_manifest.json`：export、initial_diff、untracked 三段，以及 3 个文件条目。
  - 本题源码与测试：`PUB/worktree/Orange/widgets/data/owcolor.py` 全文；`.../data/tests/test_owcolor.py` 先与隐藏测试做 diff，另读 853–892 行；`Orange/widgets/tests/base.py` 只读 1–43 行导入，另 grep 过 `QMessageBox`（无结果）；`doc/visual-programming/source/widgets/data/color.md`。
  - 运行说明：`run_tests.sh`；grep 了 `CONTRIBUTING.md:111–112` 与 `.github/workflows/test.yml:84–86`。
  - 名单格式惯例：先在 `Orange/` 下 grep，再读 `utils/state_summary.py:185–195`、`utils/__init__.py:140–158`、`data/owgroupby.py:195–205`、`data/owaggregatecolumns.py:118–130`、`data/owrandomize.py:105–114`。
  - 其它：`Orange/datasets` 目录列表、CHANGELOG grep。
- **私有包**：
  - `PRIV/gold.patch`、`revisions.json`（内容为 `[]`）、`run_tests.sh`、`expected_output.json`。
  - `hidden_tests/test_1.py`：全文；`hidden_tests/__init__.py`：0 字节。
  - `run_refs.json`、`grading_bundle.json`、`validation_bundle.json`。
- **运行原件**：`run_refs.json` 里 `material=current` 的四行全部核对。
  - 四个账本的第 25 行，全文。
  - 四份 `.eval.log`：R-f 两份读全文，环境轮两份读 grep 摘要。
  - 独立参考：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:24,74` 读前 600 字符；a1、a2 的 `test_output.txt` 读 grep 摘要。
  - 六份日志的本地 sha256 都与 `run_refs.json` 所记一致。
- **跨题材料**：
  - 两份 `cross_task_*_scan.json` 里涉及本题和 orange3 的条目。
  - 同仓公开包：c3fb72ba、f5026689 两题 grep 了 `owcolor.py` / `test_owcolor.py`，并看了 base_commit 与题目标题；22e98f8f、4014f248、9b5494e2、f237f968 只看 base_commit 与标题。
  - 在本题工作树里 grep 了上述各题新增测试的函数名。
- **未读**：
  - OUTPUT_DIR 内的全部文件、history/、各审查目录、本批 README / board.json / assignments.json。
  - 其它题的私有包。
  - devcheck 目录：第一步没有提供。
  - 今晚的 `*_budget1200` 账本：没有提供路径，只按协调者说明记录事实。
- **暴露说明**：曾对 `results/` 目录（OUTPUT_DIR 的上一级）做过一次条目计数，只得到数字，没有列出文件名，也没有打开任何文件。

## 2. 八方面覆盖

| 方面 | 看了什么 | 初判 |
| --- | --- | --- |
| 公开需求 | 题面、公开提示、base 版 `_parse_var_defs`、公开测试、Color 文档 | 核心要求：定义里有未用变量时弹警告并点名，不报错。题面没有规定名单格式、缩写规则，也没单独提 numeric 段；但"variable definitions that include unused variables"是一般表述，覆盖两段。题面的 "Actual Behavior" 在 base 上不成立（P4）。 |
| 材料与初始问题 | base `owcolor.py:700–703`；noop 日志 | base 遇到未用定义直接 `continue`，不警告，也不抛异常。noop 在目标键上报的 TypeError 是测试伪影（见 I4）。材料彼此对应：base commit、gold 上下文、隐藏测试与公开测试的差异都吻合。两者的差异正好是"新增目标测试 + 删掉 P6 旧块"。未见 X2。 |
| 测试是否测到要求 | 隐藏测试全文。目标键逐行读；与 `_parse_var_defs` 相关的回归键逐行读；其余回归键按类抽读 | 核心要求有直接断言，但只覆盖原例形态，缺 numeric 段与混合场景（I2）。 |
| 误拒 | 名单格式断言，对照题面与仓库惯例 | T1（I1）。3–5 个名字的连接方式依据较弱；6 个以上名字的缩写规则没有依据。另一项约束是必须经 `QMessageBox.warning` 发出，文本作为第 3 个位置参数；同一函数已有这种写法，风险低，只登记（K2）。 |
| 回归与 gold | gold 逐行；调用者 `load()`（`owcolor.py:642–659`）；相关回归键 | gold 修到了题面原例，也满足一般要求；没有回归，也没有无关改动。公开旧块在 gold 下失败属于 P6，不是 gold 的缺陷。隐藏测试删旧块时丢了一个边界（T3）。 |
| 开发条件 | environment_brief、环境卡、公开 `run_tests.sh` / `CONTRIBUTING.md`、评分侧日志 | 纯 Python 改动，不需要构建或联网。Qt 测试要加 `QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum` 前缀：公开的 `run_tests.sh` 与 `CONTRIBUTING.md:111–112` 能查到，公开提示里没写。修对之后公开测试模块会多 1 个失败（P6），公开侧也没有测试新行为的用例。actor 侧没见到本题的执行证据，记"actor 待验"。 |
| 交付与评分边界 | 账本 projection、`run_tests.sh`、隐藏测试的导入 | 只交付 `owcolor.py`，projection 正常（gold 行 `included_paths`）。隐藏测试依赖 base 版 `Orange/widgets/tests/base.py::WidgetTest`：候选可以改它，评分时也不重置。导入的 `WidgetTest` 被收集成 3 个 SKIPPED，不成键，结果稳定。 |
| 题目关系与用途 | 两份跨题扫描；打开公开包核对 | X1（I5）。题面不给修法，不属于 P1。 |

## 3. 需求—断言双向表

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据 / 下一验证 |
| --- | --- | --- | --- | --- |
| R1 定义里有未用变量时弹警告，点名这些变量 | `PUB/user_prompt.txt:7,21–22`（原例 `'foo'` and `'bar'`） | `PRIV/hidden_tests/test_1.py:801–820`：n=1–7 个名字，`assertIn(message, msg_box.call_args[0][2])` | 有覆盖，但格式过严（I1），且只在原例形态下测（I2） | noop FAILED，TypeError 在 `test_1.py:820`；gold PASSED |
| R2 没有未用定义时不弹警告 | 题意；base 旧行为 | `test_1.py:798–799` 空定义，断言 `assert_not_called`；`:906–909` 定义全部对应已有变量 | 覆盖 | 两侧都 PASSED |
| R3 numeric 段的未用定义同样提示 | 一般表述 `user_prompt.txt:7` | 无。唯一涉及 numeric 未用定义的旧块已从隐藏测试中删除（公开 `test_owcolor.py:885–888`） | 缺失 | 实跑 C-cat |
| R4 不报错、不中断加载：同一文件里已有变量的定义照常生效 | `user_prompt.txt:22`（"No errors should occur"）、`:25`（"disrupting the loading process"）；base `owcolor.py:691–692, 709–719` | 无。目标测试的控件没有数据，没有可应用的定义；其它测试里没有未用定义 | 缺失 | 实跑 C-deg |
| O1 已有警告照常（值重名、变量重名） | 公开测试 | `test_1.py:167–185`、`:879–886`、`:888–909` | 覆盖 | 两侧都 PASSED |
| O2 定义的解析、应用与非法格式 | 公开测试 | `test_1.py:117–165`、`:830–877` | 覆盖 | 两侧都 PASSED |
| 反查 K1：名单的连接与缩写格式 | n=2 有题面字面依据。n=3–5 在仓库里有同风格先例（`owaggregatecolumns.py:123–128`、`owrandomize.py:111`），但不是唯一写法。n≥6 没有依据：各处惯例的阈值是 3、4、30 不等（`state_summary.py:190–195`、`utils/__init__.py:152–153`、`owgroupby.py:201`） | `test_1.py:806–816` | 没有依据的约束，归 T1 | 实跑 C-alt1 |
| 反查 K2：必须经 `QMessageBox.warning` 发出，文本是第 3 个位置参数，且是最后一次调用 | 同函数已有写法 `owcolor.py:683–686, 714–715`；公开测试 `test_owcolor.py:859–860, 876–877` | `test_1.py:796, 820` | 依据较弱，登记 | — |

## 4. 问题清单

| # | 编号 | 初判 | 证据层次 |
| --- | --- | --- | --- |
| I1 | T1（按 P3 补查） | 误拒，须修订（R-b） | 静态推断 + 源码惯例；待 C-alt1 实跑 |
| I2 | T2c / T2b | S1：第 2 步倾向命中，第 3 步待实跑 | 静态推断；待 C-deg 实跑 |
| I3 | P6 | 登记 | 静态推断：gold 下公开旧块必然失败 |
| I4 | P4 | 登记；可选 R-f | 历史 RH2 日志 + 静态推断；原例未在 base 实跑 |
| I5 | X1 | 登记 | 机械扫描 + 公开包核对 |
| I6 | T3 | 登记 | 静态推断 |
| I7 | E3（链路问题，不是题目问题） | 交 A 线 | 协调者说明 + 历史账本 |

**I1 误拒（T1）**

- **断言**：`test_1.py:806–816` 给出七组消息子串。n=6、7 时要求出现 `'foo', 'bar', 'baz', 'qux' and 2 other` / `... and 3 other`，也就是"不超过 5 个全列，超过 5 个只列前 4 个再报剩余个数"。gold 的对应实现在 `PRIV/gold.patch:23–35`。
- **公开依据**：题面只要求 "display a warning message indicating that the variables 'foo' and 'bar' are defined but not used in the data"（`user_prompt.txt:22`），只有 n=2 的写法有字面依据。仓库里的缩写惯例各不相同：
  - `state_summary.py:190–195`：不超过 3 个全列，否则列前 2 个再接 "and N others"；
  - `utils/__init__.py:152–153`：接 "... and N others"，阈值由调用处决定；
  - `owgroupby.py:201`：列前 3 个再接 "and N more"；
  - `owaggregatecolumns.py:123–128`：`'a', 'b' and 'c'` 风格，阈值 30。

  没有一种能推出 gold 的阈值。
- **后果**（均为静态预测）：
  - C-alt1 与 gold 相同，只是始终全列；它在 n=6 失败，判 0。它连题面 n=2 的写法都照搬了，仍被判 0，是最干净的误拒证据。
  - 按 `state_summary` 惯例缩写的候选在 n=4 失败。
  - 只用逗号、不写 "and" 的候选，以及按字母排序输出（`'bar' and 'foo'`）的候选，都在 n=2 失败。
- **补充**：`and 2 other` 是子串匹配，所以写成 "and 2 others" 的候选可以通过；问题只在阈值和列几个名字。

**I2 核心判据只用示例形态（T2c；T2b 待测）**

- 目标测试的输入形态与题面原例相同：
  - 只有 `categorical` 段；
  - 值是空的改名（`renamed_values={}`，另加 `colors={}`）；
  - 控件没有载入数据（`setUp` 只创建控件，`test_1.py:620–622`），所以全部定义都未用。

  变化的只有名字个数。numeric 段、"已有与未用定义混在一起"两种情形都没测。
- 按 D1 严格版"同一个输入形态"，倾向判命中（T2c）。分歧点是名字个数确实有变化，因此以第 3 步的实跑作决定性证据（见 §5）。

**I3 公开旧测试与正确修复冲突（P6）**

- 公开 `PUB/worktree/Orange/widgets/data/tests/test_owcolor.py:885–888`：先 `_create_descs()`，再载入 `{"categorical": {"varA": {"rename": "X"}}, "numeric": {"var not": {"rename": "X"}}}`，断言 `msg_box.assert_not_called()`。`"var not"` 不在数据里，正确修复（包括 gold）会弹出未用警告，这个公开测试随之失败。隐藏测试删掉了这 4 行（见 diff）。
- **影响**：actor 在 base 上跑公开测试会全部通过；修对之后反而多出 1 个失败，而公开侧没有任何测试新行为的用例。按旧测试"修正"修复的候选属于"遵循冲突示例的候选"，例如只对 categorical 段提示，或者对只含 rename 的未用定义不提示。当前隐藏测试会给这类候选 1 分（与 I2 相关）。
- **处理**：登记。分析探针结果时，改动或忽略这 4 行不算钻空子，这 4 行失败也不算改错。

**I4 题面把测试失败现象写成了应用行为（P4）**

- 题面说应用抛出 `TypeError: 'NoneType' object is not subscriptable`，并且 "disrupting the loading process"（`user_prompt.txt:7, 24–25`）。
- base `owcolor.py:700–703, 713–719` 遇到未用定义只做 `continue`。静态推断：原例在没有数据的控件上能走完 `_parse_var_defs` 与 `commit`，既不警告也不抛异常。
- noop 日志 `runs/r2e_rf_20260923/remote/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-o_7674929a.eval.log:54–57` 显示，这个 TypeError 来自测试体里的 `self.assertIn(message, msg_box.call_args[0][2])`（此时 `call_args` 为 None），调用栈中没有 `owcolor.py` 的帧。
- **判断**：期望行为写得很清楚；读源码找不到崩溃点，就能判断题面这段有误，公开材料可以消解。按 P4 登记。
- **可选 R-f**：把 "Actual Behavior" 改成在 base 上核实过的症状："不弹任何警告，数据中不存在的变量定义被静默忽略"。标题里的 "Error Occurs" 同步改。改之前须先在 base 上实跑原例确认。

**I5 同仓跨题包含（X1）**

- **本题答案出现在别题初态**：本题 gold 的 14/14 行逐字出现在 `orange3__c3fb72ba…`（base 419b1882）与 `orange3__f5026689…`（base 3dd6d9c9）的公开初态中。两题的 `worktree/Orange/widgets/data/owcolor.py:695–723` 都有 `unused_vars` 实现，`tests/test_owcolor.py:817` 都有 `test_load_ignore_warning`。两份扫描都命中，已打开公开包核对。
- **反向**：本题初态包含 22e98f8f（7/7）、4014f248（1/1）、9b5494e2（10/10）、f237f968（14/15）的 gold，以及 `test_below_precision`、`test_auto_solver`、`test_partial_matches_with_missing_vars`，分别在本题工作树的 `Orange/tests/test_discretize.py`、`Orange/tests/test_logistic_regression.py`、`Orange/widgets/data/tests/test_owselectrows.py` 中。这些题的主题与本题无关，包含关系只反映提交先后。
- **处理**：登记。训练时要控制同仓重复采样，因为 c3fb72ba、f5026689 的初态直接给出了本题答案与目标测试。留出评测按仓库划分（D3）时，orange3 各题在同一侧。

**I6 旧块删掉而不是改写（T3）**：公开 `:885–888` 原本还保护一个边界：对不存在的变量写 rename，不计入重名检测。隐藏测试把整块删了，而没有改成"只弹未用警告、不弹重名警告"，所以这个边界不再被覆盖。gold 没改重名逻辑，风险低，只登记。

**I7 链路问题（E3）**：按协调者说明，今晚这台机器上评分前的 `chown -R` 在默认 300 s 时限内超时，于是改用 1200 s 时限，账本记为 `*_budget1200`；这不是题目问题，我没有看到这些账本。旁证：09-23/24 四个账本第 25 行的 `phases.grader_trusted_setup` 已经是 160.3–188.1 s（这个阶段是否就是该 chown 步骤，我没有核实），与"在更慢的机器上超过 300 s"相容。

## 5. v1 §4 五步

| 步 | 结果 |
| --- | --- |
| 1 核心要求有没有直接断言 | 有：`test_1.py:798–820`，空定义时不警告，有未用定义时警告文本要含名单。不是 T2a。 |
| 2 是否只用示例字面值或同一输入形态 | 倾向命中（T2c）：只测了 categorical 段、全部未用、控件无数据；名字个数有变化（I2）。 |
| 3 退化探测 | C-deg 静态预测得 1，待正式评分；若得 1 即为 S1（T2b）。 |
| 4 已有候选 | 没有真实模型候选。构造的 C-cat 静态预测得 1，待实跑。 |
| 5 | 前几步已倾向命中，不适用。 |

结论：S1。此外还有与五步并列的 T1 误拒（I1），须按 R-b 修订。

## 6. R2E 专项

- **(a) 非 PASSED 期望键**：期望的 48 个键全是 PASSED，没有 FAILED 或 ERROR 键，所以不存在"更完整的修复把期望失败键翻成 PASSED 而判 0"的问题。反查"更完整"的方向：如果连未用的**值**也警告（即 `renamed_values` 或 `colors` 里数据中不存在的值），会破坏 `DiscAttrTest.test_to_dict`。该测试在 `test_1.py:153–161` 明确要求冗余值 `"d"` 被忽略且 `warns == []`，断言来自公开测试、有依据，所以不算误拒。
- **(b) 题面报错是否出现在 noop 目标键**：出现了（noop 日志 `:55`），但它是测试伪影（I4）。两次 current noop 的失败位置相同：`evallog_replay-r2e-envrepair-rer_df1485a0.eval.log:55,57`。
- **(c) 题面是否泄漏修法**：题面没有修法代码，只给了期望内容（n=2 时怎样点名），不属于 P1。
- **(d) 测试支撑与撞键**：
  - `test_1.py:21` 导入 `from Orange.widgets.tests.base import WidgetTest`。这是 base 版的辅助代码，候选可以改，评分时不重置。
  - 导入的 `WidgetTest` 被 pytest 当作用例类收集，3 个方法都以 ".widget was not set" 为由 SKIPPED（noop 日志 `:111–113`），不成键，结果确定。
  - 只有一个隐藏测试文件，类名不重复，不会撞键。
  - 用到的数据集 `iris`、`heart_disease`、`zoo` 都是跟踪文件（`PUB/worktree/Orange/datasets/`）。
- **(e) 时间、随机、资源敏感的键**：没发现。6 次运行（当前 4 次 + M3 2 次）结果一致。pytest 段耗时 3.4–4.6 s（M3 上 11.7–12.4 s）。`test_color_combo` 在 stderr 打出 "This plugin does not support raise()"，不影响结果。
- **(f) 材料修订**：`revisions.json` 为 `[]`，没有需要核对的修订。

## 7. gold 检查

- **原例**：两个未用的 categorical 定义、控件无数据时，gold 生成 "Definitions for variables 'foo' and 'bar', which do not appear in the data, were ignored."，经 `QMessageBox.warning(self, "Invalid definitions", ...)` 显示，不抛异常。
- **一般要求**：
  - 两段都会收集未用定义：`gold.patch:9, 17` 在两段共用的循环里 append。
  - 有已有变量时，其余定义照常赋值：`warnings.insert(0, warn)`，没有提前返回。
- **无关改动**：没有，只改了 `owcolor.py`。
- **不影响判定的细节**：
  - 警告字符串末尾带 `\n`，再经 `"\n".join` 拼接，与其它警告之间会多出一个空行；
  - 同名变量同时出现在两段时，会被重复列出；
  - 类型不符时也报 "does not appear in the data"（例如 categorical 段里写了一个 numeric 变量）。
- **未测的回归**：没发现 gold 破坏公开行为；公开旧块失败属于 P6。

## 8. 可区分候选（可直接写成补丁）

三个候选都只改 `Orange/widgets/data/owcolor.py` 的 `OWColor._parse_var_defs`。

**C-deg：退化候选（第 3 步，提前返回）**

- **改法**：
  - 与 gold 一样，在 `if var is None:` 分支里执行 `unused_vars.append(var_name)`。
  - 循环结束后，若 `unused_vars` 不为空，用 gold 的同一段代码拼出 `warn`，接着执行 `QMessageBox.warning(self, "Invalid definitions", warn)` 并立即 `return`。这样会跳过 base `owcolor.py:709–719` 里对 `self.disc_descs` / `self.cont_descs` 的赋值、`set_data` 与 `commit.now()`。
- **违反的公开要求**：R4，即 "No errors should occur during this process"、不 "disrupting the loading process"（`user_prompt.txt:22,25`）。base 的行为是文件中已有变量的定义照常生效。
- **能看出问题的输入**：先 `_create_descs()`，再调用 `_parse_var_defs({"categorical": {"varA": {"rename": "a2"}, "foo": {}}, "numeric": {}})`。正确行为是弹出点名 `'foo'` 的警告，并且 `widget.disc_descs[0].name == "a2"`；C-deg 只弹警告，`varA` 没改名，输出也没提交。
- **预测**：当前材料下 48/48，得 1，因为没有任何隐藏测试同时包含已有与未用定义。如果实跑得 1，即为 T2b。

**C-alt1：合理替代解（验证 T1）**

- **改法**：与 gold 相同，只改消息文本。n≥2 时一律生成 `'Definitions for variables ' + ", ".join(names[:-1]) + f" and {names[-1]}" + ", which do not appear in the data, were ignored.\n"`，不缩写。
- **是否满足公开要求**：满足全部公开要求：点名了全部未用变量，n=2 时的写法与题面字面一致。
- **预测**：判 0。不符的键是 `TestOWColor.test_load_ignore_warning`：n=6 时找不到子串 `'foo', 'bar', 'baz', 'qux' and 2 other`。其余 47 个键 PASSED。

**C-cat：部分实现（第 4 步可用；也是 P6 诱导的方向）**

- **改法**：与 gold 相同，但只在 `repo == "categorical"` 时执行 `unused_vars.append(var_name)`。
- **违反的公开要求**：R3，numeric 段的未用定义被静默忽略。例如调用 `_parse_var_defs({"categorical": {}, "numeric": {"nope": {}}})` 时，应当提示 `'nope'`，C-cat 不提示。这个候选同时能让公开旧块 `test_owcolor.py:885–888` 通过。
- **预测**：得 1。

其它登记而不单独实跑的情形：

- **使用控件消息栏**：用 `self.Warning` 显示警告、不经 `QMessageBox.warning` 的候选会判 0（K2）。同一函数已有 `QMessageBox.warning` 先例，属于弱依据，不列入待修项。
- **先警告、后校验格式**：这类候选会在 `test_parse_var_defs_invalid` 中弹出未打补丁的真实模态框；该测试的控件没有定义，名字都算未用。推测测试会一直挂起，直到评分时限，但没有验证，只作风险登记。

## 9. 修订建议与验收

**R-b（I1）**

- **位置**：改写 `PRIV/hidden_tests/test_1.py` 里的 `TestOWColor.test_load_ignore_warning`（:796–820）。
- **保留的要求**：空定义时不警告；有未用定义时一定警告；警告文本作为第 3 个位置参数（K2 有同函数先例）。
- **放宽的要求**：名单的连接方式、名字顺序和缩写阈值。这里只检查名字是否出现，不要求引号；如果认为题面的 `'foo'` 写法足以作为引号的依据，可以改回检查 `'name'`，gold 两种写法都能通过。

```python
    @patch("Orange.widgets.data.owcolor.QMessageBox.warning")
    def test_load_ignore_warning(self, msg_box):
        self.widget._parse_var_defs(dict(categorical={}, numeric={}))
        msg_box.assert_not_called()

        no_change = dict(renamed_values={}, colors={})
        all_names = ("foo", "bar", "baz", "qux", "quux", "corge", "grault")
        for n in range(1, len(all_names) + 1):
            names = all_names[:n]
            msg_box.reset_mock()
            self.widget._parse_var_defs(dict(
                categorical=dict.fromkeys(names, no_change),
                numeric={}))
            msg_box.assert_called()
            text = "\n".join(call[0][2] for call in msg_box.call_args_list)
            if n <= 3:
                # the warning names the unused variables (statement example)
                for name in names:
                    self.assertIn(name, text)
            else:
                # how long lists are abbreviated is not specified publicly
                self.assertTrue(any(name in text for name in names))
```

`n <= 3` 是有意选的：仓库里所有缩写惯例在 3 个名字以内都会全列（`state_summary.py:190`、`owgroupby.py:201`、`owaggregatecolumns.py:125`），`instance_tooltip` 的阈值也不小于 4。

**R-c（I2）**

- **位置**：在同一文件的 `TestOWColor` 中新增下面的测试，并在 `PRIV/expected_output.json` 里加一个键：`"TestOWColor.test_parse_var_defs_unused_and_used": "PASSED"`。键集必须严格相等。

```python
    @patch("Orange.widgets.data.owcolor.QMessageBox.warning")
    def test_parse_var_defs_unused_and_used(self, msg_box):
        self._create_descs()
        self.widget._parse_var_defs(
            {"categorical": {"varA": {"rename": "a2"},
                             "foo": {"renamed_values": {}}},
             "numeric": {"varD": {"colors": "linear_viridis"},
                         "bar": {"colors": "linear_viridis"}}})
        # unused definitions in both sections are reported
        msg_box.assert_called()
        text = "\n".join(call[0][2] for call in msg_box.call_args_list)
        self.assertIn("foo", text)
        self.assertIn("bar", text)
        # definitions of variables that are in the data are still applied
        self.assertEqual(self.widget.disc_descs[0].name, "a2")
        self.assertEqual(self.widget.cont_descs[1].new_palette_name,
                         "linear_viridis")
```

- **公开依据**：
  - 混合场景：`user_prompt.txt:22, 25`，以及 base 的加载语义 `owcolor.py:691–692, 709–719`；
  - numeric 段：一般表述 `user_prompt.txt:7`。
- **静态推演 gold**：
  - 重名检查不触发：改名后是 {a2, varB, varC, varD, varE}，共 5 个。
  - 警告文本为 "Definitions for variables 'foo' and 'bar', ..."。
  - `varA` 被改名为 `a2`，`varD` 的调色板设为 `linear_viridis`，与 `test_1.py:841–858` 的现有断言一致。
- **注意**：numeric 段唯一的公开旧证据恰好是 P6 旧块，它的立场相反。如果主审或 Codex 认为这构成有竞争力的公开依据，可以把 `"bar"` 那一项去掉，只保留 categorical 混合部分；这仍然能拒绝 C-deg，但放过 C-cat。

**验收（一轮修订、一轮验收）**

| 对象 | 预期结果 |
| --- | --- |
| gold | 1（49/49） |
| noop | 0：目标键与新键都 FAILED |
| C-deg | 0：新键在 `disc_descs[0].name` 处失败 |
| C-cat | 0：新键缺少 `"bar"` |
| C-alt1 | 1：误拒得到纠正 |
| C-alt2（可选：只用逗号连接名单，不写 and） | 1 |

修订后仍受保护的公开要求：R1、R2、R3、R4、O1、O2。另外要保存新版本、父版本、修订理由和触发反例（C-alt1 原判 0，C-deg 原判 1），并交 Codex 复核。

**可选 R-f（I4）**：见 I4。这一项要等 R2E 的题面文本替换机制可用后再做，并按 R-f 验收：由新的公开读者读改后的题面、逐行核对改动。

**待用户决定**：无。

## 10. 用途结论（v1 四项，复核初判）

| 用途 | 初判 | 差什么 / 依据 |
| --- | --- | --- |
| `problem_localization` | yes | — |
| `capability_comparison` | conditional | ① I1 尚未处理：要么先做 R-b，要么预先登记事后审计，把"只因名单格式不同而失败"的样本单列，原始 reward 保留；② actor 侧本题开发核对的证据，第一步没看到；③ 本批有效运行条件，即今晚新机在 budget1200 下的 gold/noop，没看到；④ 把 P6 写进探针的解读口径 |
| `training_candidate` | no（当前版本） | I1 误拒与 I2 的 S1 都未处理。R-b + R-c 验收通过、X1 登记之后再评估 |
| `heldout_candidate` | no（当前版本） | 理由同上。修订后只能作为"标明版本的自建评测"；X1 带来的同仓暴露需要登记 |

## 11. 探针就绪差距

第一步规则不允许读本批 README，所以这里没有对照 README §3，改按 v1 §2 与环境卡逐条列出。协调者可以再与 README §3 对齐。

| 条件 | 状态 | 谁来补 |
| --- | --- | --- |
| 评分侧当前材料 gold 为 1、noop 为 0 | 已满足：09-23、09-24 各一次，同一派生镜像 `sha256:9fa2177f…` | — |
| 今晚新机在相同条件下的对照 | 没看到证据（协调者称已用 1200 s 时限跑过，账本名 `*_budget1200`） | 协调者提供路径，第二步核对 |
| 核心要求有决定性断言 | 部分满足：R1、R2 有，R3、R4 缺 | 协调者按 R-c 实施，Codex 复核 |
| 消除误拒 | 未满足（I1） | 协调者按 R-b 实施，用 C-alt1 验收 |
| 退化探测 | 未做 | 协调者用正式评分实跑 C-deg |
| actor 开发条件 | 没看到本题 devcheck | 协调者跑 devcheck（真实 CC + 桩端点） |
| 跨题关联登记 | 本文已登记 X1 | 主审 / 协调者写入记录 |
| 题面 P4 | 已登记；可选 R-f | 视 R2E 题面文本替换机制是否可用 |

## 12. 未知项与唯一优先的下一步

- **未知项**：
  - actor 能否按公开线索跑通 Qt 测试（没看到 devcheck）；
  - 今晚新机的运行结果；
  - C-deg、C-cat、C-alt1 的实际得分（都只是静态预测）；
  - 题面原例在 base 上"不报错也不警告"尚未实跑，目前依据是静态推断，加上 noop 调用栈的旁证。
- **唯一优先的下一步**：在当前材料上用正式评分实跑 C-deg 与 C-alt1（2 次）。同时核对补丁确实交付（projection 含 `owcolor.py`），以及 `test_load_ignore_warning` 确实执行过。这两次结果分别决定 T2b 与 T1，也就是 R-c 与 R-b 是否必要。
