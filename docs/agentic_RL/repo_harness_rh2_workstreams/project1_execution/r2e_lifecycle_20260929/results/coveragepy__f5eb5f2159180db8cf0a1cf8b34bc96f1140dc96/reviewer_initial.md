# 独立复核初判：coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96

独立复核第一步（2026-09-29，单题闭环试行，按统一标准 v1）。本文在读公开读者产物、主审产物与历史引用**之前**写成，是本题的暴露记录（复核者已读 gold、隐藏测试、期望映射与运行原件），不提供给解题模型。

路径简写（均相对仓库根目录）：

- `PUB` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`；`WT` = `PUB/worktree`（解题者在 `/testbed` 看到的初态）
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`
- `LOG_N` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_9e168ae0.eval.log`（noop，material=current）
- `LOG_G` = `runs/r2e_env_repair_20260924/_rerun2/eval_logs/evallog_replay-r2e-envrepair-rer_e7615d5b.eval.log`（gold，material=current）

## 0. 结论先行

| 项 | 初判 | 证据层次 |
| --- | --- | --- |
| 材料与初态 | 一致。题面、base `17204597`、gold、隐藏测试、期望映射相互对应；隐藏测试两文件 sha256 与评分包一致；本题无材料修订 | 原件核对 |
| 当前材料运行 | noop 0（只有 `JsonReportTest.test_branch_coverage` 不符）、gold 1（4/4），各 2 次，同一派生镜像 `sha256:1a2107883a20…`、同一评分代码版本 | 历史真实 RH2（current） |
| 题面报错是否出现在 noop 目标键 | 是，逐字对应（`LOG_N:93` 对 `PUB/user_prompt.txt:28`） | 日志 |
| **主要问题** | **S1（T2c）**。branch 模式只有一个测试实例，它的期望值正是题面报错里写出的 `covered_branches: 1`、`missing_branches: 1`；而且在这个实例上 covered、missing、`num_partial_branches` 三个量都等于 1。硬编码 1/1、两字段对调、把 partial 当 missing，静态推断都会得 1。退化候选 D1 预计得 1，待正式评分（得 1 即再记 T2b） | 静态推断 + 源码推导 |
| 修订建议 | R-c：在 `PRIV/hidden_tests/test_1.py` 加一个非示例实例（num_branches 6 / covered 4 / missing 2 / partial 0），期望映射同步加一个 PASSED 键。代码与验收计划见 §8 | 待协调者实施与实测 |
| 其他登记 | P6：公开 `tests/test_json.py` 的同名测试写死旧 totals，任何正确修复都会让它失败。另有 P4（低）、T3（多文件汇总与 CLI 未测）、E5（可忽略）。X1：`ea6906b0` 的初态含本题答案；`97997d2c` 与本题同 base，公开工作树逐字节相同；本题初态含 `016af5f6`、`5dbbe143` 的修复 | 原件核对 |
| 误拒 | 未发现 T1。"每个文件的 summary 也加这两个键"的候选会得 0，但按第二批规则 1 不算合理修复被误拒：题面限定 totals，公开旧测试也精确断言 per-file 键集。上游后来确实这样做了（见 `ea6906b0` 公开包），所以探针分析时列为疑似规格争议样本 | 静态推断 + 同仓公开包 |
| 用途（v1） | 问题定位 yes；能力比较 conditional；训练候选 no（R-c 验收前）；留出 no | 见 §11 |

## 1. 实际读取范围

- **角色卡与方法。** `r2e_lifecycle_20260929/roles/reviewer_r2e.md` 读了全文；`investigator_r2e.md` 读了全文，因为工具一次载入整份文件，但只把"R2E 的评分口径""材料""第二批补充规则""单题闭环试行补充"四节当作口径；另外两节只是通用流程，不含本题信息。方法文档读了四份全文：`swegym_task_audit_20260920/quality_review_protocol_20260920.md`、`r2e_lifecycle_20260929/r2e_environment_card.md`、`swegym_task_audit_20260920/quality_batch01_20260921/record_template.md`、`task_screening_standard_v1_20260925.md`。40 项清单不在本次方法清单中，未读，所以不给 `checks` 编号。
- **公开包。**
  - 全文：`PUB/user_prompt.txt`、`PUB/environment_brief.md`、`PUB/public_bundle.json`；`PUB/worktree_manifest.json` 只读摘要。
  - `WT` 下全文：`coverage/jsonreport.py`、`coverage/results.py`、`tests/test_json.py`、`tests/conftest.py`、`tests/__init__.py`、`setup.cfg`、`run_tests.sh`。
  - `WT` 下片段：`coverage/xmlreport.py:95-135,190-225`、`coverage/summary.py:75-125`、`coverage/control.py:950-980`、`coverage/report.py:12-42`、`tests/coveragetest.py:17-135,325-340,478-492`、`tests/test_api.py:960-995`、`tests/test_results.py:70-90`、`CHANGES.rst:1-60`、`doc/branch.rst:45-60`、`doc/cmd.rst:470-500`。
  - 在 `WT` 中 grep：`json`、分支计数键名，以及 `json_report` / `JsonReporter` 的调用者。
- **私有包。** 读了全部文件：`gold.patch`、`expected_output.json`、`run_tests.sh`、`revisions.json`、`grading_bundle.json`、`validation_bundle.json`、`run_refs.json`、`hidden_tests/test_1.py`（全文）、`hidden_tests/__init__.py`（空文件）。两个隐藏测试文件的 sha256 与 `grading_bundle.json` 一致。
- **运行原件。**
  - current 账本行 4 条：`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:10`、`ledger_r2e_all_gold.jsonl:10`，以及 `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:10`、`ledger_gold.jsonl:10`。对应的 4 份 eval log 读了全文。
  - M3 独立参考 2 条：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:45,91`，及其 2 份日志。
  - 6 份日志的 sha256 都与 `run_refs.json` 一致。账本里的 `diagnostics_ref` 未打开。
- **同仓跨题。**
  - 两份扫描文件：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json` 与 `cross_task_test_scan.json`，读了 `method` 以及全部涉及 coveragepy 的记录（各 8 条）。
  - 同仓公开包：`coveragepy__ea6906b0…`（`coverage/version.py`、`coverage/jsonreport.py:50-110`；`tests/test_json.py`、`CHANGES.rst`、`CONTRIBUTORS.txt` 只 grep）；`coveragepy__97997d2c…`（`public_bundle.json`、`version.py`，并与本题 worktree 做 `diff -rq`）；`coveragepy__016af5f6…`、`coveragepy__5dbbe143…`（题面前 160 字、`version.py`）。
  - 未读任何其它题的私有包。
- **未读。** `OUTPUT_DIR` 的任何文件、`history/`、`docs/.../r2e_env_repair_20260924/`、各 `*review*` 目录、本批 README / `board.json` / `assignments.json`、`runs/` 下的分析与汇总（上列路径除外）。devcheck 证据本次未提供，也未读。未运行项目代码，未开容器或远端。

## 2. 只凭公开包抽出的目标

- **需求。** 开启 branch coverage 时，JSON 报告的 `totals` 应含 `covered_branches` 与 `missing_branches`，"providing detailed branch coverage information"（`PUB/user_prompt.txt:6-7,20-21`）。题面报错串给出一个实例的值：`'covered_branches': 1, 'covered_lines': 2, 'missing_branches': 1`（`:28`）。
- **两个词的含义有公开依据。**
  - `Numbers.n_executed_branches` 的注释是 "Returns the number of executed branches"（`WT/coverage/results.py:201-204`）；`n_missing_branches` 定义在 `results.py:36`。
  - XML 报告另用 `branch_stats()` 独立算出 `branches-covered`（`WT/coverage/xmlreport.py:122-123,203-205`）。
  - 公开测试 `AnalysisTest.test_many_missing_branches` 说明：从未调用的函数里的 `if` 计 2 个 missing branch、0 个 partial branch（`WT/tests/test_api.py:962-991`，断言在 `:989-991`）。
- **旧行为与约束。**
  - branch 类键只在 `coverage_data.has_arcs()` 时输出（`WT/coverage/jsonreport.py:59-63` 为 totals，`:94-98` 为每个文件）。
  - 公开旧测试对整份 JSON 做精确比较（`WT/tests/test_json.py:35`）：line 模式的 totals 不含 branch 键（`:95-101,143-149`）；branch 模式下每个文件 summary 的键集固定（`:50-58`）。
- **合理实现范围。** 在 totals 的 has_arcs 分支里加这两个键，值是已执行分支数和缺失分支数（直接用 `Numbers` 属性，或在 `report_one_file` 里按 `analysis.branch_stats()` 累加，数值相同）。把两个键也加进每个文件的 summary，是题面没有要求的扩展（见 §5(a)）。
- **公开文档的一处不符（不影响本题）。** `WT/doc/branch.rst:52-54` 说 JSON 报告含 "separate statement and branch coverage percentages"，但 base 的 JSON 没有分开的百分比。题面只要求两个计数键；按这句文档另加百分比键的候选会因 totals 精确比较得 0，这属于题面外的扩展，不算 T1。

## 3. 八方面

| 方面 | 看了什么 | 初判 |
| --- | --- | --- |
| 公开需求 | 题面、`public_hints`、`environment_brief`、`jsonreport.py` / `results.py` / `xmlreport.py`、`doc/cmd.rst:474-485`、`doc/branch.rst:52-54`、公开旧测试 | 要求明确：totals 加两个键，仅限 branch 模式。报错串给了示例值。题面里 "tests that validate the presence" 指的是公开包里看不到的测试（P4，低） |
| 材料与初始问题 | 公开包与评分包里的 base、`worktree_manifest.json`（`initial_diff` 为 0 字节；未跟踪文件只有 `install.sh`、`run_tests.sh`）、`jsonreport.py:51-63`、noop 日志 | base 上确实缺这两个键；noop 目标键的失败原因就是题面报错（`LOG_N:89-93`）。未见 X2 |
| 测试是否测到要求 | `test_1.py` 全文，以及 helper：`tests/coveragetest.py:66-130,330-334,480-488` | 核心断言存在（`test_1.py:61-71`，经 `:35` 整体相等），但只有一个实例，且各值都是 1，判为 T2c（§6） |
| 是否误拒合理解 | 替代实现 A1、A2（§7），以及"line 模式也输出这两个键"的写法 | 未见 T1。A2（per-file 也加）得 0，登记为有上游先例的范围扩展。line 模式也输出键会让 3 个 line 模式键失败，公开依据充分，不算误拒 |
| 回归与 gold 完整性 | `PRIV/gold.patch:5-11`；调用者 `control.py:953-975`、`cmdline.py:604`、`report.py:12-42` | gold 只在 totals 的 has_arcs 分支加两个键，没有无关改动，返回值不变。未测的范围：多文件汇总、`coverage json --branch` 命令行、combine 后的数据（T3） |
| agent 开发条件 | `environment_brief`、环境卡、`setup.cfg:2`、`tests/conftest.py`、评分日志 | 纯 Python 改动。公开测试依赖 xdist 与 flaky 插件（评分日志显示同一 `.venv` 可用，actor 侧待验）。公开同名测试在正确修复后会失败（P6）。devcheck 未提供 |
| 交付与评分边界 | `PRIV/run_tests.sh:1`、账本 `projection` 与 `observations` | 评分导入 `/testbed/coverage/__init__.py`（4 条 current 账本的 `RH2_OBS_IMPORT_PATH`）；gold 投影为 `coverage/jsonreport.py`。只有一个隐藏测试文件，无撞键。运行期答案可达性引用环境卡的预检（"HEAD 没有子提交"），未逐题核 |
| 题目关系与用途 | 两份跨题扫描、4 个同仓公开包 | X1 有三类关系（§9.5） |

## 4. 需求—断言双向表

| 需求 / 旧行为 | 公开依据 | 键 / 决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| R1：branch 模式的 totals 含 `covered_branches`，值为已执行分支数 | `user_prompt.txt:20-21`；`results.py:201-204` | `JsonReportTest.test_branch_coverage`：`test_1.py:69`，经 `:35` 整体相等 | 部分。只有一个实例，其值 1 等于题面示例值，区分不了 executed、missing、partial | noop FAILED（`LOG_N:93,107`），gold PASSED（`LOG_G:23`） |
| R2：branch 模式的 totals 含 `missing_branches`，值为缺失分支数 | 同上；`results.py:36` | `test_1.py:70` | 部分（原因同上） | 同上 |
| R3：两个值随实际测量变化（"detailed branch coverage information"） | `user_prompt.txt:21` 的一般表述 | 没有非示例实例 | **缺失**，即 T2c | — |
| O1：line 模式的 totals 不含 branch 键 | `jsonreport.py:59`；`test_json.py:95-101` | `test_simple_line_coverage`、`test_context_non_relative`、`test_context_relative`（`test_1.py:97-103,145-151`） | 覆盖 | noop 与 gold 均 PASSED |
| O2：branch 模式下每个文件 summary 的键集不变 | `test_json.py:50-58`；题面只提 totals | `test_1.py:50-58`，经 `:35` | 覆盖（也正因此 A2 得 0） | gold PASSED |
| O3：其它 totals 值（`num_branches`、`num_partial_branches`、`percent_covered` 60.0） | `jsonreport.py:51-63` | `test_1.py:61-68` | 覆盖 | gold PASSED |
| O4：meta、contexts、`relative_files` | `jsonreport.py:35-40,90-93` | `test_1.py:39-44,107-159` | 覆盖 | PASSED |
| O5：多文件汇总、命令行、combine | `control.py:953-975`、`cmdline.py:604` | 无 | 缺失（T3） | — |

反向核对：关键断言 `test_1.py:69-70` 的依据是 `user_prompt.txt:21` 和 `:28` 的报错串；`test_1.py:50-58`（每个文件不加新键）的依据是公开旧测试和"题面只要求 totals"。没有发现只有读隐藏材料才能知道的要求。隐藏测试与公开 `tests/test_json.py` 的 diff 只有 totals 里新增的两行（`test_1.py:68-70`，对应 `test_json.py:68`）。

## 5. R2E 专项

- **(a) 非 PASSED 期望键。** 期望的 4 个键全是 PASSED，没有 FAILED / ERROR 键，也没有参数化。会被不同实现翻转的只有 `test_branch_coverage`：
  - A2（每个文件的 summary 也加两个键）：per-file summary 多出键，该测试 FAILED，得 0。这是静态确定的结论，因为 `test_1.py:35` 做整体精确比较。
  - "line 模式也输出这两个键"的写法：3 个 line 模式键 FAILED。
  - 判断：A2 不算第二批规则 1 意义上的"合理修复被误拒"。题面明确限定 totals（`user_prompt.txt:7,21`），而每个文件 summary 的精确输出是公开旧测试断言的旧行为（`test_json.py:50-58`）。但上游后来确实加了（`ea6906b0` 公开工作树 `coverage/jsonreport.py:101-102`，其 `tests/test_json.py:56-57`），所以真实模型若因此得 0，应在探针分析里列为疑似规格争议样本，原始 reward 保留。不建议用 R-b 放宽：那样会去掉有公开依据的 per-file 回归保护。若要接受上游后来的行为，就是改任务目标，属于待用户决定，目前不需要。
- **(b) 题面报错是否出现在 noop 目标键。** 是。`LOG_N:93` 为 `{'totals': {'covered_lines': 2, 'excluded_lines': 0, 'missing_lines': 1, 'num_branches': 2, ...}} != {'totals': {'covered_branches': 1, 'covered_lines': 2, 'excluded_lines': 0, 'missing_branches': 1, ...}}`，与 `user_prompt.txt:28` 一致（题面省略了中间几个键）。09-23 的 noop 日志与 `LOG_N` 内容相同，diff 只有时间戳、对象地址和 PASSED 行的顺序。
- **(c) 题面是否泄漏修法。** 没有：题面没提 `Numbers` 的属性名，键名本身就是需求，不算 P1。但报错串公开了隐藏测试唯一实例的期望值（1 和 1），与 §6 的 T2c 叠加后，硬编码就能通过。
- **(d) 测试支撑与撞键。**
  - 隐藏测试依赖 base 版的测试辅助：`tests/coveragetest.py` 的 `CoverageTest`、`UsingModulesMixin`、`start_import_stop`、`assert_recent_datetime`（`:66-130,330-334,480-488`），以及 `tests/helpers.py` 和 `.venv` 里的 `unittest_mixins`。
  - 原目录 `tests/conftest.py` 的三个 autouse fixture（`:22-78`）对 `r2e_tests/` 不生效，但在本题看不到影响：gold 4/4，noop 只有目标键失败。
  - 候选可以改这些辅助，评分时不会重置；不过决定性比较写在 `test_1.py:35` 本身，改辅助绕不过去。
  - 只有一个隐藏文件，4 个方法名互不相同，无撞键。
- **(e) 时间、随机、资源敏感。**
  - `assert_recent_datetime` 的窗口是 10 秒。
  - `test_1.py:32` 用 `"%Y-%m-%dT%H:%M:%S.%f"` 解析时间戳；当微秒恰好为 0 时，`isoformat()` 会省略小数部分（`jsonreport.py:37`），解析就会报错。这个概率约为每次 1e-6，4 个键都受影响，与修复无关。
  - xdist（`setup.cfg:2` 的 `-n3`）只改变 PASSED 行的顺序；评分按键解析，不受影响。
  - 结论：记 E5，可忽略，不需处理。
- **(f) 材料修订。** 没有。`PRIV/revisions.json` 为 `[]`；`grading_bundle.json` 的 `material_revisions` 为 `[]`；`run_refs.json` 的 `current_material` 中 `env_recipe` 与 `resource_recipe` 都是 null；隐藏测试树的哈希与评分包一致。

## 6. v1 严重度五步

1. **第 1 步：核心要求有没有直接断言？** 有（`test_1.py:61-71`，经 `:35`）。不命中。
2. **第 2 步：核心断言是否只用题面示例的字面值？命中。**
   - branch 模式只有 `test_branch_coverage` 一个实例（`a.py`，`test_1.py:21-25`），它的 totals 期望值就是题面报错里的 `covered_branches: 1`、`missing_branches: 1`。
   - 更麻烦的是，这个实例上几个量恰好相等。`a.py` 第 2 行有两个出口：2→3 没走到，2→exit 走到了。按 `results.py:33-36,201-204` 算，`n_branches=2`、`n_missing_branches=1`、`n_executed_branches=1`、`n_partial_branches=1`，与 `test_1.py:65-70` 一致。
   - 因此下面几种写法都会得 1：硬编码 1/1；两个字段对调；`missing_branches = n_partial_branches`；`covered_branches = n_branches - n_partial_branches`。
   - 结论：S1（T2c）。
3. **第 3 步：退化探测。** D1（§7）静态预测得 1，需协调者用正式评分确认；得 1 即再记 T2b。
4. **第 4 步：已有候选有没有违例？** `run_refs.json` 只有 noop 与 gold，没有真实模型候选，也没有已构造候选的评分。没有证据，记为不命中（未知）。
5. **结论：S1（T2c）；T2b 待 D1 实跑。**

## 7. 退化候选与可区分候选

**D1（退化候选：与输入无关的固定结果）。**

- 改哪里：`coverage/jsonreport.py`，`JsonReporter.report()`，base 第 59-63 行的 `if coverage_data.has_arcs():` 块。
- 怎么改：在 totals 的 `update` 字典里写死两个常量，其它不动。

```diff
             self.report_data["totals"].update({
                 'num_branches': self.total.n_branches,
                 'num_partial_branches': self.total.n_partial_branches,
+                'covered_branches': 1,
+                'missing_branches': 1,
             })
```

- 违反哪条公开要求：题面 "totals ... should include `covered_branches` and `missing_branches`, providing detailed branch coverage information"。这两个值应是实测的分支数。
- 用什么输入能看出来：§8 的 `bcount.py`（应为 covered 4 / missing 2，D1 给出 1/1）；或者任何分支全部覆盖的程序（应为 covered = `num_branches`、missing = 0）。
- 预测：在当前材料上 reward 为 1（4/4）。
- 实跑后要核对三点：账本的 `projection.included_paths` 含 `coverage/jsonreport.py`；日志里 `test_branch_coverage` 为 PASSED；4 个键都被解析到。

**其他候选。** 前两行用于 R-c 验收时的"已知相关错误候选"。改动都在 `jsonreport.py` 的同一处，A2 另外再改一处。

| 候选 | 改法 | 违反 / 性质 | 当前材料预测 | R-c 后预测 |
| --- | --- | --- | --- | --- |
| W2 两字段对调 | `'covered_branches': self.total.n_missing_branches, 'missing_branches': self.total.n_executed_branches` | 语义弄反 | 1 | 0（新键 FAILED：得到 2/4，应为 4/2） |
| W3 把 partial 当 missing | `'covered_branches': self.total.n_branches - self.total.n_partial_branches, 'missing_branches': self.total.n_partial_branches` | missing 与 partial 不是一回事（`test_api.py:989-991`） | 1 | 0（得到 6/0） |
| A2 per-file 也加（范围扩展） | 在 gold 改动之外，`report_one_file` 的 has_arcs 块（`jsonreport.py:94-98`）也加 `'covered_branches': nums.n_executed_branches, 'missing_branches': nums.n_missing_branches` | 不违反 totals 要求，但改变了公开旧测试精确断言的 per-file 输出；与上游后来的行为一致 | 0（`test_branch_coverage` 不符） | 0（不是本次修订的目标） |

另有一种合理写法：把 `n_branches - n_missing_branches` 直接写在字典里，或在 `report_one_file` 里按 `analysis.branch_stats()` 累加 `(t, k)`。它与 gold 数值相同，静态预测在原版和 R-c 后都得 1，不必实跑。

## 8. 修订建议（R-c，针对 S1 / T2c）

- **公开依据。**
  - 题面的一般表述（`user_prompt.txt:7,21`），不限于报错串里的那个实例。
  - "covered / missing branches"按仓库现有的公开定义理解：`Numbers.n_executed_branches`（`results.py:201-204`）、`n_missing_branches`（`results.py:36`）。
  - 公开测试 `test_many_missing_branches`（`test_api.py:962-991`）示范了：未执行的 `if` 计 2 个 missing、0 个 partial。
- **具体改动。**
  - 在 `PRIV/hidden_tests/test_1.py` 的 `JsonReportTest` 类末尾加一个方法（代码如下）。
  - 在 `PRIV/expected_output.json` 加 `"JsonReportTest.test_branch_totals_counts": "PASSED"`。R2E 要求键集严格相等，所以隐藏测试与期望映射必须一起改。

```python
    def test_branch_totals_counts(self):
        """covered_branches / missing_branches in totals follow the measured branches."""
        self.make_file("bcount.py", """\
            def f(x):
                if x:
                    a = 1
                else:
                    a = 2
                if not x:
                    a = 3
                return a

            def g(y):
                if y:
                    return 3
                return 4

            f(True)
            f(False)
            """)
        cov = coverage.Coverage(branch=True)
        mod = self.start_import_stop(cov, "bcount")
        output_path = os.path.join(self.temp_dir, "bcount.json")
        cov.json_report(mod, outfile=output_path)
        with open(output_path) as result_file:
            totals = json.load(result_file)['totals']
        assert totals['num_branches'] == 6
        assert totals['covered_branches'] == 4
        assert totals['missing_branches'] == 2
```

- **期望值的推导（手算，不取自 gold 输出）。**
  - dedent 后，第 2 行（`if x:`）和第 6 行（`if not x:`）在 `f(True)`、`f(False)` 两次调用下两个出口都走到，共 4 个已执行分支。
  - `g` 从未被调用，第 11 行的两个出口都缺失，计 2 个 missing。该行本身也没执行，所以 `num_partial_branches = 0`，情形与 `test_api.py:989-991` 相同。
  - 结果：num_branches 6、covered 4、missing 2、partial 0。四个量两两不同，且都不等于示例里的 1。
- **只断言 totals 的三个键。** 不做整份 JSON 比较，因此不会给 per-file 输出加新约束，也不加重 A2 的问题。模块名用 `bcount`，避开现有 helper 使用的 `a`。
- **独立核对期望值。** 在评分镜像里对同一个 `bcount.py`：
  - 跑 `coverage xml`，预期 `branches-valid="6" branches-covered="4"`。XML 经 `branch_stats` 独立计数（`xmlreport.py:122-123,203-205`）。
  - 跑 `coverage report -m --branch`，预期 Branch 6、BrPart 0、Missing 11-13。
  - 若结果与推导不一致，先查明原因，不要直接照抄 gold 的输出。
- **验收。**
  - gold 为 1（5/5）。
  - noop 为 0：`test_branch_coverage` FAILED，新键因 `KeyError` FAILED。
  - D1、W2、W3 在 R-c 后均为 0（新键 FAILED），它们在原版上的 1 分别留档作为触发反例。
  - A2 仍为 0，不在本次修订范围内。
  - 保存新版本、父版本和修订理由；交 Codex 复核。
- **可选扩展（默认不加）。** 同一测试可以再报第二个文件（如 `cov.json_report([mod, mod2])`），检查 totals 是否跨文件汇总。gold 用的是 `self.total`（`jsonreport.py:21,76`），自然满足。按 R-c"一处修改只针对一个窄问题"的原则，默认不加。

## 9. 其他问题登记

1. **P6。** 公开 `WT/tests/test_json.py:61-69` 的 totals 不含新键，所以任何正确修复都会让公开的 `tests/test_json.py::JsonReportTest::test_branch_coverage` 失败。探针分析时：模型改这条公开测试不算钻空子，公开测试失败也不算模型改错。评分只跑 `r2e_tests`，改它不影响得分，但账本的 `candidate_test_like_paths` 可能会把它标出来。
2. **P4（低）。**
   - 题面说 "tests that validate the presence of these attributes"，但公开包里没有这样的测试；示例代码里的 `# ... execute some code ...` 也需要自己补全。要求本身清楚，公开材料可以消解。
   - 原例能否复现：base 上 `json_report` 的 API 与题面一致（`control.py:953-975`）；缺键可由 `jsonreport.py:51-63` 静态确认，并已由 noop 日志执行确认。
3. **T3。** 未测：多文件汇总、`coverage json` 命令行（`cmdline.py:604` 只经 mock 测试）、combine 后 has_arcs 的数据。gold 的改动与这些路径无关，登记即可。
4. **E5。** 见 §5(e)，可忽略。
5. **X1（机械扫描结果已核实）。**
   - **`coveragepy__ea6906b0…`（coverage 6.1.0a0）的初态含本题答案。** 本题 gold 的两行逐字出现在其 `coverage/jsonreport.py:65-66`；该题初态还把这两个键加进了每个文件的 summary（`:101-102`），其 `tests/test_json.py:56-57,72-73` 也含这两个键。若 `ea6906b0` 进训练，本题答案就暴露了。本题作留出时 `ea6906b0` 不能进训练；按 D3 同仓划分，两者本来就在同一组。
   - **`coveragepy__97997d2c…` 与本题同 base（`17204597`）。** 两题公开工作树 `diff -rq` 无差异：同一初态、不同问题。这不是答案包含，但训练时要注意同一初态会重复出现。
   - **本题初态包含 `coveragepy__016af5f6…` 与 `coveragepy__5dbbe143…`（均为 5.0.2a1）的修复。** 扫描称它们的 gold 行全部出现在本题工作树中。我只核对了测试名：`WT/tests/test_oddball.py:566` 的 `test_unencodable_filename`、`WT/tests/test_api.py:557` 的 `test_warn_once`；按规则未读它们的私有 gold。
   - 测试名扫描里没有以本题为源的记录，这符合预期：本题隐藏测试没有新增测试函数，只改了 `test_branch_coverage` 的期望值。

## 10. 开发需求（解题侧；评分侧的运行只证明评分条件）

- **导入。**
  - 评分侧：`RH2_OBS_IMPORT_PATH=/testbed/coverage/__init__.py`，版本 5.0.5a0（见 4 条 current 账本的 `observations`），所以改 `/testbed/coverage/jsonreport.py` 就会生效。
  - 解题侧：从 `/testbed` 跑 `python -m pytest` 也一样，因为 pytest 以 rootdir 把 `/testbed` 插入 `sys.path`。
  - 在 `/testbed` 之外跑临时脚本时导入的是哪一份 coverage：actor 待验。
- **依赖。**
  - `setup.cfg:2` 的 `addopts = -q -n3 --strict --no-flaky-report -rfe --failed-first` 需要 pytest-xdist 和 flaky 插件。评分日志出现了 "bringing up nodes"，且没有报未知参数，说明同一 `.venv` 里都有。actor（uid 54321）用的是同一个解释器，待 devcheck 核实。
  - 写命令时不要加 `-p no:cacheprovider`：它与 `--failed-first` 冲突（v1 §7.1）。
- **资产、网络、构建。** 都不需要。纯 Python 改动，不必重编 C tracer。
- **权限。** 需要写 `/testbed/coverage/`；`.pytest_cache` 会写在 `/testbed` 下。
- **最小验证。**
  - ① 在 `/testbed` 下写一个含分支的小脚本，用 `coverage.Coverage(branch=True)` 运行，再 `json_report`，检查 totals 的值。
  - ② 跑 `python -m pytest tests/test_json.py`。预期只有 `test_branch_coverage` 因为多出新键而失败（P6）。
  - 评分侧整轮测试约 2 秒；一次正式评分的各阶段合计约 20 秒（见账本 `phases`）。
- **提交边界。** 只需改 `coverage/jsonreport.py`。
- **devcheck。** 本次未提供；以上 actor 条件都记为"待验"。

## 11. 用途初判（v1 §2）

- **`problem_localization`：yes。**
- **`capability_comparison`：conditional。** 还差三个条件：
  - 本题 actor 侧的开发核对（devcheck）；
  - 把 P6 写进探针分析规则；
  - 若在 R-c 之前使用，得 1 的补丁必须按预登记的事后审计核对语义（用非示例输入检查 covered / missing），原始 reward 与语义结果分列。
- **`training_candidate`：no。** 还有未处理的 S1（T2c；T2b 待测）。R-c 验收通过并经 Codex 复核、actor 条件也核对之后，可以重新评估。
- **`heldout_candidate`：no。** 原因同上。另外，修订后的题只能作"标明版本的自建题"；与 `ea6906b0`（含本题答案）的 X1 关系须按 D3 隔离。
- **`intended_use`** 照旧为 `development_diagnostic`。

## 12. 探针就绪差距（初判）

按协调者的读取限制，我没有读本批 README §3。以下按 v1 §2 和环境卡列出，与 §3 的逐条对齐请协调者补。

- **已满足。**
  - 材料一致。
  - 当前材料下 noop 0、gold 1 各 2 次，用的是同一派生镜像与同一评分代码版本；M3 独立 runner 在来源镜像上 gold 也 2 次为 1（仅作参考）。
  - 没有材料修订需要核对。
  - 题面报错与 noop 失败原因一致。
  - 跨题关系已核。
- **未满足（括号内为负责方）。**
  - ① D1 的正式评分（协调者）。
  - ② R-c 的实施、验收与复核（协调者实施，Codex 复核）。
  - ③ 本题 actor 侧开发核对（协调者，devcheck）。
  - ④ 把 P6 与 X1 写进探针分析说明（协调者 / 主审卡片）。
  - ⑤ 与主审分歧的收敛（第二步）。

## 13. 未知项与最值得先做的下一步

- **未知。**
  - D1 的实际得分（静态预测为 1）。
  - actor 侧的命令与导入路径。
  - R-c 新测试期望值在评分镜像上的实测结果（手算为 6 / 4 / 2 / 0）。
- **最值得先做的一件事。** 用正式评分跑一次 D1，确认是否命中 T2b。同一批次顺带跑 W2、W3，以及 R-c 草案下的 gold 和 noop。
