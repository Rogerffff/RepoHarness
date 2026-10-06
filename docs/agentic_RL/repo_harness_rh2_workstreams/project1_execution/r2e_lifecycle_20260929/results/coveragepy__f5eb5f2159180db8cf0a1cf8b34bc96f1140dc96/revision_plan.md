# coveragepy f5eb5f21：R-c 修订方案（非示例计数、按数据门控）与 C1 决定包

2026-09-29 · 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内，Claude 执行、Codex 复核）。

**状态：**
- **R-c 定稿，不需要用户决定。** 两项合并为一轮修订，试跑验收 8 个候选全部与预期一致（试跑工具，不是正式评分）。待协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。
- **C1 需要用户做一次决定**（§6）：R-b 窄版 / R-f / 维持原样。R-b 窄版已做成单独的备选草案 `revision_draft_rb.json` 并试跑（§7）：C1 由 0 变 1，负对照 C1swap 仍为 0，其余候选与 R-c 相同。本轮只落 R-c；不裁定时的默认见 §6.5。

路径约定（仓库根相对；`trials/`、`cands/`、`revision_draft*.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`，`W` = `PUB/worktree`（解题者的 `/testbed`）。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/`；`HT` = `PRIV/hidden_tests/test_1.py`（父版本，159 行）；`HT'` = R-c 修订后（220 行）；`HT''` = R-c + R-b 窄版（237 行）。
- `INV` = `runs/r2e_lifecycle_20260929/inv/coveragepy_f5eb/`（协调者正式评分与私有核对）。
- 键名省略类名前缀 `JsonReportTest.`：`BC` = `test_branch_coverage`（原目标键），`K1` = `test_branch_totals_count_branch_arcs`，`K2` = `test_branch_totals_from_saved_branch_data`。

## 1. 模板与要纠正的误判

**模板：R-c**（v1 §5）。两处修改各对应一个有公开依据的窄问题，合并在同一轮完成。

| 项 | 要纠正的 S1 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- |
| R-c 1：非示例计数 | T2c：唯一的分支断言 `HT:61-71` 只用题面错误信息里的示例值 1/1（`PUB/user_prompt.txt:28`）。T2b：退化候选 D0（硬编码 1/1）得 1。第 4 步：C2（把"部分弧"当"未执行弧"）得 1 | D0、C2 正式评分 1.0（`INV/ledger_D0.jsonl:1`、`INV/ledger_C2.jsonl:1`）；W2（两值对调，本轮新写）当前材料试跑 1（`trials/cur_W2.json`） | `card.md` §4 I1–I3；`review.md` §2 A2–A3 |
| R-c 2：按数据门控 | 第 4 步：C3（按配置 `branch` 而不是数据 `has_arcs()` 门控）得 1；在文档写明的流程（先 `coverage run --branch`，再单独 `coverage json`）下两键缺失 | C3 正式评分 1.0（`INV/ledger_C3.jsonl:1`）；P-2 原样执行公开命令 `repro_cli_json`：C3 的 totals 没有两键（`INV/pcheck_P2_C3.json`），gold 为 1/1（`INV/pcheck_P2_gold.json`） | `card.md` §4 I4；`review.md` §0、§2 A4 |

**不在 R-c 内**：C1（每文件 summary 也加两键，被判 0）按 §6 交用户；T3（多文件时 totals 的汇总、`report()` 返回值）维持登记。

## 2. 公开依据

### 2.1 R-c 1：非示例计数

- **题面的一般表述**：`PUB/user_prompt.txt:7` 说 totals 缺这两个属性；`:21` 要求 totals 包含它们，"providing detailed branch coverage information"。`:28` 的错误信息只是一个实例（1/1），没有限定数值。
- **两个量的口径（公开代码）**：
  - `W/coverage/results.py:36`：`n_missing_branches` 数分支行上所有没走过的弧，包括根本没执行过的分支行；
  - `:35`：`n_partial_branches` 只数"已执行的分支行"上缺的弧（`k not in self.missing`），与前者不是一回事；
  - `:201-204`：`n_executed_branches` 的注释是 "Returns the number of executed branches"，等于 `n_branches - n_missing_branches`；
  - `:118-120`：`num_branches` 按分支行的出口数累加。
- **其它报告用同一口径**：XML 每个类取 `sum(t)` 与 `sum(t - k)`（`W/coverage/xmlreport.py:202-205`），总计写成 `branches-valid` / `branches-covered`（`:121-123`）。
- **文档的计数单位**：`W/doc/branch.rst:45-46` "Each line in the file is an execution opportunity, as is each branch destination."——按分支去向（弧）计，不按分支行计。
- **命名平行**：totals 里已有的 `covered_lines` / `missing_lines` 分别是已执行 / 未执行的语句数（`W/coverage/jsonreport.py:51-57`）。
- **公开测试**：`W/tests/test_api.py:962-991`（`test_many_missing_branches`）：从未调用的函数里的 `if` 计 `n_branches` 2、`n_partial_branches` 0、`n_missing_branches` 2（`:989-991`）。BRANCHY 里的函数 `h` 正是这种情形。
- **为什么选 BRANCHY**：四个值 6、0、4、2 两两不同，也都不等于示例里的 1。示例夹具 `a.py` 上已执行弧、未执行弧、部分弧恰好都是 1，常数 1/1（D0）、部分弧口径（C2）、两值对调（W2）都能蒙对；在 BRANCHY 上它们分别报 1/1、6/0、2/4，都会出错。

### 2.2 期望值的推导与独立核对（不取自 gold 的输出）

- `make_file` 去掉缩进后，`f` 在 1–4 行，`g` 在 6–9 行，`h` 在 11–14 行，调用在 16–19 行。
- 没有 `else` 的 `if` 有两个出口：进入条件体（`return 1`），或落到下一条语句（`return 2`）（`W/coverage/parser.py:930-936`）。`return` 在函数内没有后继（`:953-958`），模块层语句各只有一个出口。所以分支行是 2、7、12，`num_branches = 6`。
- `f(0)`、`f(1)` 走过第 2 行的两个出口，`g` 同理走过第 7 行的两个出口；`h` 从未调用，第 12 行的两个出口都没走过，`n_missing_branches = 2`（`results.py:36`），`covered_branches = 6 - 2 = 4`（`:204`）。
- 第 12 行本身没有执行，不计入部分分支（`:35`），`num_partial_branches = 0`。
- **独立核对**（都不是 gold 的 JSON 输出）：
  1. 同一镜像上的 XML 报告给出 `branches-valid="6" branches-covered="4"`（`INV/pcheck_P3_{gold,D0,C2,C3}.json`）。XML 不经过 `jsonreport.py`，四个候选下结果相同。
  2. 主审的静态推导（`analysis_before_history.md` 附录 B）与复核的核对（`review.md` §3.3）。
  3. 修订后 noop 在 K1 上先通过两个锚点（`num_branches == 6`、`num_partial_branches == 0`），到 `HT':211` 才因缺键失败（`trials/rev_noop.json`），说明锚点是 base 已有的行为。
- gold 在 P-3 里报 6/0/4/2、在试跑里通过，这些是验收结果，不是期望的来源。

### 2.3 R-c 2：按数据门控

- **现有代码按数据判断**：`W/coverage/jsonreport.py:38` 的 `meta.branch_coverage` 就是 `coverage_data.has_arcs()`；`:59`、`:94` 已有的分支键也按 `coverage_data.has_arcs()` 输出。其它报告同样按数据：`W/coverage/summary.py:20`、`W/coverage/xmlreport.py:60`。
- **文档写明的用法**：`W/doc/branch.rst:38-40` 用 `coverage run --branch myprog.py` 测量；`:52-54` 说 `coverage xml` 与 `coverage json` 产出的报告 "also include branch information"。
- **报告进程不知道 `--branch`**：`coverage json` 子命令没有 `--branch` 选项（`W/coverage/cmdline.py:374-388`）；报告进程以 `Coverage(branch=options.branch, ...)` 建对象（`:532-545`），先 `load()`（`:578`）再 `json_report()`（`:602-609`）；`branch` 缺省为 False（`W/coverage/config.py:182`）。
- 测试里"`save()` → 新建 `Coverage(data_file=...)` → `load()` → `json_report()`"与 CLI 报告进程的顺序相同，只是没有跨进程。
- 没看过隐藏测试的公开读者，也把"按 `has_arcs()` 门控"列为应保持的约定（R5，`public_read.md:16`）。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即唯一的隐藏测试文件 `HT`（sha256 `ee874f37…`，与当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:10` 一致；修订单 v1–v7 没有本题条目）。
- **修订类别**：`hidden_test_text_replace`，一处 edit：
  - `old` 是文件最后两行 `HT:158-159`（`test_context_relative`），全文只出现一次；
  - `new` = 原两行 + 空行 + 下面的代码，追加在唯一的类 `JsonReportTest` 末尾。
- **修订后**：`HT'` 220 行，sha256 `73ad2f27…`，新增内容在 160–220 行。精确的 old / new 见 `revision_draft.json`。

```python
    # R2E revision (2026-09-29, R-c): the issue asks for totals that give
    # "detailed branch coverage information", so the counts are checked on a
    # program other than the issue's one-branch example.  In BRANCHY, f and g
    # take both branches of their `if`, and h never runs.
    BRANCHY = """\
        def f(x):
            if x:
                return 1
            return 2

        def g(x):
            if x:
                return 1
            return 2

        def h(x):
            if x:
                return 1
            return 2

        f(0)
        f(1)
        g(0)
        g(1)
        """

    def _branchy_report(self, modname, report_from_saved_data=False):
        """Measure BRANCHY with branch=True and return the parsed JSON report."""
        self.make_file(modname + ".py", self.BRANCHY)
        data_file = os.path.join(self.temp_dir, modname + ".coverage")
        cov = coverage.Coverage(branch=True, data_file=data_file)
        mod = self.start_import_stop(cov, modname)
        if report_from_saved_data:
            # Like `coverage run --branch` followed by a separate `coverage json`:
            # the reporting object's own config does not set branch.
            cov.save()
            cov = coverage.Coverage(data_file=data_file)
            cov.load()
        output_path = os.path.join(self.temp_dir, modname + ".json")
        cov.json_report(mod, outfile=output_path)
        with open(output_path) as result_file:
            return json.load(result_file)

    def test_branch_totals_count_branch_arcs(self):
        # 6 branch destinations (two per `if`), 4 taken, 2 never taken.  h's `if`
        # never runs, so it is not a partial branch.
        report = self._branchy_report("branchy")
        totals = report['totals']
        assert totals['num_branches'] == 6
        assert totals['num_partial_branches'] == 0
        assert totals['covered_branches'] == 4
        assert totals['missing_branches'] == 2

    def test_branch_totals_from_saved_branch_data(self):
        # R2E revision (2026-09-29, R-c): the report follows the measured data,
        # as the other reporters do, not the reporting object's own settings.
        report = self._branchy_report("branchy_saved", report_from_saved_data=True)
        assert report['meta']['branch_coverage'] is True
        assert report['totals']['covered_branches'] == 4
        assert report['totals']['missing_branches'] == 2
```

**设计说明**：
- **只断言 totals**，外加三个锚点（`num_branches`、`num_partial_branches`、`meta.branch_coverage`，都是 base 已有的行为）。不碰每文件 summary，对 C1 争议保持中立：C1 修订后仍只在原键 BC 上失败（§5.2）。
- **沿用同文件现有测试的写法**：`make_file`、`start_import_stop`、`self.temp_dir`，以及文件头已有的 `os`、`json`、`coverage` 导入。没有新增对 base 测试辅助的依赖，暴露面与现有测试相同（`review.md` §6）。
- **报告限定到被测模块**：`json_report(mod, ...)`，与现有辅助函数一样，避免测量窗口里执行的其它代码混进 totals（`public_read.md` §3.1 第 3 条）。
- 数据文件显式放在测试临时目录，与已跑过的 P-3 一致；两项用不同模块名（`branchy`、`branchy_saved`），不会复用已导入的模块。
- 不依赖时间、随机数或网络，只写测试自己的临时目录。
- **刻意不测**：
  - 多文件时 totals 的汇总、`report()` 返回值（T3，I9）；
  - 每文件 summary（C1，§6）；
  - 真实 CLI 子进程：进程内的等价流程已覆盖"数据与配置不一致"这一点，CLI 行为已由 P-2 核对。

## 4. 期望映射逐键变化

- **原 4 键不变**，全为 PASSED。
- **新增 2 键**：`K1: PASSED`（R-c 1）、`K2: PASSED`（R-c 2）。
- **合计 6 键**，完整映射见 `revision_draft.json` 的 `expected_after`。正式修订单的期望部分用 `expected_file_replace`：`added` 为这两键，`changed`、`removed` 为空（草案里的 `formal_expected_change`）。
- **期望从哪里来**：两键的 PASSED 来自 §2 的公开语义；gold 通过是验收结果，不是依据。
- **版本记录**（全长哈希见 `revision_draft.json`）：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，159 行） | `ee874f37…` |
  | 父版本 `expected_output.json`（4 键） | `9e555e51…` |
  | 父版本隐藏测试树 | `d03ee4ff…`，`material_revisions` 为空 |
  | 修订后 `test_1.py`（`HT'`，220 行） | `73ad2f27…` |
  | 试跑用 `draft_rc.json` | `feb30002…` |
  | 试跑用 `expected_after.json`（6 键） | `8e622411…` |

## 5. 验收计划与试跑结果

**试跑条件**：
- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`（远端 `/work/code/rh2`），只作试跑。与正式评分的差别见文件头：不做基线重建比对，不核隐藏测试树与入口摘要，权限布置简化为把整个 `/testbed` 交给评分用户。
- **镜像**：派生镜像 `sha256:98b19b5a2ce4…`，配方 `r2e_derive_v1+sysconfig_v1`，与 `INV` 下四份正式账本的 `image_id_actual` 相同。
- **评分入口**：与正式评分相同，以 uid 54322 跑来源入口 `bash run_tests.sh`（pytest，`-n3` 生效），用正式解析器逐键比对。协调者提醒的"R-c 测试还没在 pytest 评分路径上跑过"由此补上：修订版每次 6 键全部解析，没有 missing / extra。正式评分路径仍待落材料后跑。
- **补丁核对**：所有候选补丁先在仓库外的 base 副本上 `git apply --check -v` 通过；副本里 `coverage/jsonreport.py` 的 blob 是 `0c3f313d`，与各补丁的 index 行一致。本轮新写的 W2、A1、C1swap 另确认改后文件能解析。试跑时都是 `RH2_APPLY_RC=0`，草案都报 `RH2_TRIAL_EDITS_APPLIED=1`。
- **草案核对**：在本地按正式摄入的同一规则（每处 old 在当前文本里恰好出现一次，`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:450-460`）重放，生成的文件与试跑所用草案一致，Python 语法检查通过。
- **次数与耗时**：每个候选跑 1 次，共 18 次；单次墙钟 30–57 s，测试段 3.4–7.0 s。

### 5.1 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只差 BC | `trials/env_noop_current.json` |
| gold | 1：4/4 | `trials/env_gold_current.json` |
| D0、C2、C3 | 都是 1.0，4/4 | `INV/ledger_{D0,C2,C3}.jsonl:1`（协调者正式评分） |
| C1 | 0.0：只差 BC，差异项只有 `files` | `INV/ledger_C1.jsonl:1`；`INV/logs_C1/evallog_replay-r2e-inv-f5eb-C1-0_61e26907.eval.log:91-94` |
| W2（本轮新写） | **1**：4/4（触发反例） | `trials/cur_W2.json`（试跑） |

### 5.2 R-c 草案下的验收

结果文件为 `trials/rev_<候选>.json`。

| 候选 | 补丁 | 角色 | 应得 | 应不符的键 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，6/6 | 1 |
| noop | 无 | — | 0 | BC、K1、K2 | 0，恰好这 3 键；K1、K2 都是 `KeyError: 'covered_branches'`（`HT':211`、`:219`） | 0 |
| D0 | `cands/coveragepy_f5eb_D0.patch` | 第 3 步退化候选 | 0 | K1、K2 | 0，恰好这 2 键；都是 `assert 1 == 4` | **1**（正式） |
| C2 | `cands/coveragepy_f5eb_C2.patch` | 第 4 步错误口径 | 0 | K1、K2 | 0，恰好这 2 键；都是 `assert 6 == 4` | **1**（正式） |
| C3 | `cands/coveragepy_f5eb_C3.patch` | 第 4 步按配置门控 | 0 | K2 | 0，只有 K2；`KeyError: 'covered_branches'`（`HT':219`） | **1**（正式） |
| W2 | `cands/coveragepy_f5eb_W2.patch`（本轮新写） | 两值对调 | 0 | K1、K2 | 0，恰好这 2 键；都是 `assert 2 == 4` | **1**（试跑） |
| C1 | `cands/coveragepy_f5eb_C1.patch` | 争议候选（§6） | 0 | BC | 0，只有 BC；K1、K2 通过 | 0（正式） |
| A1 | `cands/coveragepy_f5eb_A1.patch`（本轮新写） | 非 gold 的正确写法 | 1 | — | 1，6/6 | 未跑（静态判断为 1） |

**判读**：
- **正对照 1、noop 0**：成立。gold 的 6 个键在日志里都是 PASSED 行，这是复核 §3.4 第 1 条要的核对。gold 本身满足公开要求：取 `n_executed_branches` / `n_missing_branches`，沿用 `has_arcs()` 门控（`card.md` §2；P-2 下 CLI 流程有两键）。
- **误判已纠正**：D0、C2、C3（当前材料正式评分 1）和 W2（当前材料试跑 1）修订后都得 0，而且各自只在针对它的键上失败，失败原因与预测一致。C3 只在 K2 上以 `KeyError` 失败，符合复核 §3.4 第 2 条。
- **没有误拒**：A1 得 1。它按 `branch_stats()` 逐文件累加，与 XML 同一算法，不用 gold 取的 `Numbers` 属性，说明新断言不依赖 gold 的写法。
- **对 C1 中立**：C1 只在原键 BC 上失败，两个新键通过。
- **旧键不受影响**：所有候选在原 4 键上的结果与当前材料相同。

**本轮新写的两个补丁**（都在仓库外 base 副本上 `git apply --check -v` 通过）：
- **W2**（sha256 `5515226b…`）：在 gold 的位置写 `covered_branches = n_missing_branches`、`missing_branches = n_executed_branches`。违反 §2.1 的口径；`a.py` 上两值都是 1，所以原测试放过它。
- **A1**（sha256 `73da109a…`）：`JsonReporter.__init__` 初始化两个计数；`report_one_file` 的 `has_arcs()` 块按 `analysis.branch_stats()` 累加 `taken` 与 `total - taken`；totals 的 `has_arcs()` 块输出这两个计数。写法取自复核 §3.4 第 3 条。

### 5.3 对照 v1 §5 的验收条目

- 正对照为 1、noop 为 0：满足（试跑）。
- 本次要纠正的误判已纠正：D0、C2、C3、W2 由 1 变 0。
- 已知相关的错误候选仍为 0：D0、C2、C3、W2 都是 0。C1 仍为 0，它是争议候选，不算错误候选。
- 公开核心要求有直接断言：见 §8。
- 保存新版本、父版本、理由和触发反例：见 §1、§3、§4 与 `revision_draft.json`；触发反例的正式账本在 `INV/`。
- Codex 复核：待做。

## 6. C1 决定包

### 6.1 争议的范围

- **C1 做了什么**（`cands/coveragepy_f5eb_C1.patch`）：gold 的两行，再在 `report_one_file` 的 `has_arcs()` 块（`W/coverage/jsonreport.py:94-98`）给每文件 summary 也加 `covered_branches` / `missing_branches`，取该文件自己的计数。
- **为什么得 0**：`HT:35` 做整字典相等，`HT:50-58` 规定分支模式下每文件 summary 恰好 7 个键。当前材料正式评分 0.0，只错 BC；日志显示 "Omitting 2 identical items"，差异项只有 `files`（`INV/logs_C1/…61e26907.eval.log:91-94`），totals 与 gold 完全相同。R-c 下仍只错 BC（`trials/rev_C1.json`）。
- **争议只有一点**：每文件 summary 能不能额外带上这两个计数。totals 的要求（两键、口径、门控）没有分歧。

### 6.2 两边的公开依据

**支持"只改 totals，每文件不变"**：
1. 题面只点名 totals：描述 `PUB/user_prompt.txt:7`（"attributes in the totals"）、期望 `:21`（"The `totals` section … should include"）、实际 `:24`；错误信息也只展示 totals（`:28`）。
2. 公开旧测试锁定了分支模式下每文件 summary 的 7 个键（`W/tests/test_json.py:50-58`，经 `:35` 整字典相等）。
   - 限度：同一条测试也锁定了必须改变的旧 totals（P6），解题者本来就要把这条测试当作"部分过时"。
   - 但它的每文件部分仍是有效的旧行为，gold 保持不变。
3. 一般修复惯例：题面没要求改的输出不改。这是惯例，仓库里没有成文规定。

**支持"每文件也对称加两键"**：
1. 代码结构：已有的两个分支键在 totals 与每文件 summary 里成对写出（`W/coverage/jsonreport.py:59-63` 对 `:94-98`）。
2. 其它报告在每文件和总计两级都给分支数：文本报告的每文件行与 TOTAL 行（`W/coverage/summary.py:84-86`、`:118-120`），XML 的每个类与总计（`W/coverage/xmlreport.py:202-216`、`:121-124`）。
3. 没看过隐藏测试的公开读者判为"多种合理解释、公开材料判断不了"（`public_read.md:18`、`:40`、`:64`），所以真实解题者会分成两种做法。

**不算公开依据**：
- "上游后来也在每文件加了这两键"（`ea6906b0` 的初态）是解题者看不到的未来信息。主审题卡把它写进了倾向 R-b 的理由（`card.md:83`），本决定包不用它。
- 它只在 §6.4 选项 C 的训练风险里作为训练池的事实出现（X1），不作为本题的依据。

### 6.3 为什么交用户

- **R-b 不是明显的模板内修订。** v1 §5 的 R-b 针对"没有公开依据的实现约束"（文案、内部 helper、mock 形状）。每文件 7 个键这一约束有依据，只是很弱（§6.2 前一组第 1、2 条）。
- **R-f 也不是明显的模板内修订。** v1 §3 P5 规定：测试采用的读法有公开依据，走 R-f 补一句；两种读法都有依据，就属于任务目标选择，交用户。这里两边都有依据。
- **C1 算不算 T1 误拒**，取决于"题面没要求改的输出不要改"是否算本题要求，这正是要选择的地方。
- **两位审查者的意见**：
  - 主审：P3 / 疑似 T1，倾向 R-b，交用户（`card.md` §6）；
  - 复核：P3 争议、T1 未证实，倾向 R-b 窄版，并认为它在模板内、可与 R-c 同轮做（`review.md` §4.2–§4.3）。
- 协调者决定交用户，本轮只落 R-c。本决定包按复核 §4.3 的要求补齐各选项。

### 6.4 选项

| | A. R-b 窄版（主审、复核都倾向） | B. R-f：题面补一句"只改 totals" | C. 维持原样（明确裁定） |
| --- | --- | --- | --- |
| 做什么 | 在 R-c 之上放宽 BC 的整字典比较：每文件 summary 可以带这两个计数，带了就必须两个都有、值正确；BRANCHY 上也核对每文件的值（§7） | 题面补一句（草稿见下）；隐藏测试 = R-c | 只落 R-c；把"只改 totals"定为本题目标，C1 型解得 0 登记为已知风险 |
| C1 | 1 | 0，此时违反修订后的题面，属于正确拒绝 | 0，有争议地拒绝 |
| 前提 | 用户接受"每文件 summary 可带同样两个计数"。正式修订单同一题同一目标只许一条（`rh2/src/repoharness2/envpack/ingest_r2e_subset.py:415-418`），所以要用 `revision_draft_rb.json` 的合并条目整体替换 R-c 的隐藏测试条目；期望条目不变 | 题面文本替换修订类已实现并经 Codex 复核（`codex_reviews/review_code_A_B_20260929.md`）。具体题面还要逐项验收：没看过隐藏测试与 gold 的新公开读者复读，逐行核对无隐藏细节与答案，Codex 复核，新版修订单与 pins | 用户明确接受 |
| 公开依据 | §6.2 后一组。放宽后每文件的值仍按与 totals 相同的公开口径核对（每文件用的是该文件的 `analysis.numbers`，`W/coverage/jsonreport.py:75`） | §6.2 前一组。补的句子描述的是公开旧测试里已有的每文件形状，不是隐藏细节 | §6.2 前一组 |
| 验收 | 已试跑（§7）：gold 1、noop 0、C1 1、C1swap 0，D0 / C2 / C3 与 R-c 相同。正式评分加跑 C1、C1swap | 评分材料同 R-c，沿用 §5.2（C1 为 0）；另加新公开读者验收 | 沿用 §5.2 |
| 额外成本 | 草案与试跑已完成；正式评分多 2 次 | 一轮新公开读者，外加题面修订的落地与复核 | 无 |

**对四项用途的影响**（前提：R-c 已按正式材料评分并经 Codex 复核；各选项再满足自己的前提）：

| 选项 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| A. R-b 窄版 | yes | yes | yes | conditional |
| B. R-f | yes | yes | yes | conditional |
| C. 维持原样 | yes | yes，C1 型结果单列 | yes，登记风险 | conditional |
| 不裁定（默认，§6.5） | yes | conditional | conditional | conditional |

- **训练候选**：A、B、C 都还要把 X1 的训练侧影响写进记录（`review.md` §5）。`97997d2c` 与本题初态逐字节相同，训练时要控制同一初态的重复采样；`ea6906b0` 的初态含本题答案。
- **留出评测**：一律 conditional。要按 D3 以仓库划分（`ea6906b0` 与本题同侧），不用于选模型或调提示，修订后只能作"标明版本的自建评测"；B 还要标明题面版本。
- **C 的训练风险**：若用户选择保持每文件键集（C），C1 型解就是违反所选范围、得 0 是正确拒绝；若选 A，同一类解得 0 才是误拒。当前只能确定这是规格争议，不能先称为"与题意无关的奖励噪声"。`ea6906b0` 若同在训练池，它的初态就是"每文件也有两键"的形态，可能让这类输出更常见——这是风险推测，尚未实测。（09-29 协调者按 Codex 复核 §4 第 2 条更正措辞）
- **C 与默认的"单列"规则要预先登记**：
  - 得 0、唯一不符的键是 BC、差异只在每文件 summary 多出这两个键时，单列为"疑似规格争议"，原始 reward 保留；
  - 这类解算不算对，用 BRANCHY 私有核对每文件两值（P-3 的做法）。原因是 `a.py` 上两值都是 1，看不出是否写反。

**B 的题面草稿**（未验收，只在选 B 时启用）：
- old（`PUB/user_prompt.txt:21`；在公开包 `problem_statement` 里恰好出现一次）：
  > The `totals` section in `coverage.json` should include `covered_branches` and `missing_branches`, providing detailed branch coverage information.
- new：原句后接一句
  > The per-file `summary` entries under `files` are not part of this change and keep their current keys.
- 逐行核对：没有隐藏测试的测试名、输入或新值；没有实现细节；"current keys" 指公开旧测试 `W/tests/test_json.py:50-58` 已写明的形状。

**不可选**：去掉每文件 summary 的整字典比较，或接受任意额外键。那会拿掉每文件已有键和行模式形状的保护，超出 R-b 的边界。

### 6.5 不裁定时的默认

- **材料**：只落 R-c（`revision_draft.json`）。C1 型解得 0，但记录上仍是"待决争议"，不写成"正确拒绝"，也不写成"误拒"。
- **能力比较 conditional**：用户裁定前不进正式比较分母，只作问题定位（Codex 复核 §4 第 1 条；原稿写"两种读法由协调者选"，已更正）。下面两条是原稿列出的做法，留作裁定后参考：
  - 按 v1 §2"争议……单列"纳入，C1 型结果按 §6.4 的单列规则处理；
  - 或按 v1 §11 暂不进比较分母。§11 是 SWE-Gym 条目，用于 R2E 是类推。
- **训练候选 conditional**：差 C1 裁定，即选 A、B、C 之一。
- **留出评测 conditional**：差训练候选的质量条件，另加 D3 等限制。
- **探针**：按 Codex 复核（`codex_reviews/review_revision_coveragepy_f5eb.md` §4 第 1 条），C1 属 P5 输出范围选择，**用户裁定前本题暂挂为问题定位，不进正式能力比较，也不标 probe_ready**；R-c 可先正式落地（不依赖裁定）。与 `5dbbe143` 的区别在于争议落在核心要求之外的附加输出上，但处理方式相同：都等用户选定读法。（09-29 协调者按复核更正；原稿写的是"可以按争议单列进探针、由协调者定"）
- 不阻塞其它题（v1 §5）。

### 6.6 执行者意见（建议，不是决定）

**建议选 A（R-b 窄版）。** 理由：
1. 争议点不在核心要求上。三个选项对 totals 的要求（两键、口径、门控）一样严格。
2. 拒绝 C1 的直接依据只有一条公开测试，而解题者本来就必须把它当作"部分过时"（P6）；题面只点名 totals，没有说每文件保持不变。
3. 放宽很窄，而且验值：C1swap 仍为 0，R-c 的负对照在 R-b 下结果不变。
4. 不改题面，不需要新公开读者。R-c 已经让本题成为"标明版本的自建题"，R-b 不增加这方面的代价。

**反方理由也成立**：R-b 模板本来是给"没有公开依据"的约束用的，这里的约束有弱依据。如果用户更看重"题面没要求的输出不要改"这一训练信号，选 B。

**不建议 C 用于训练**：它会把一类核心正确的解稳定地判 0，而 X1 会让这类解更常见。

## 7. R-b 窄版备选草案（选项 A）：改动与试跑

- **草案**：`revision_draft_rb.json`，一条 `hidden_test_text_replace` 合并条目，共 5 处 edit：第 1 处与 R-c 逐字相同，后 4 处是 R-b。期望映射与 R-c 相同（6 键）。修订后 `HT''` 237 行，sha256 `f73a7561…`。
- **改动**：
  1. `_assert_expected_json_report` 增加参数 `optional_summary`（`HT'':16`、`:35-42`）。对列出的文件：如果每文件 summary 出现两键之一，就要求两键都在、等于给定值，核对后从比较对象里移除；其余部分仍整字典相等（`:43`）。
  2. BC 传 `optional_summary={'a.py': {'covered_branches': 1, 'missing_branches': 1}}`（`:81-84`）。单文件时每文件的值与 totals 相同，1/1 出自题面 `:28`。行模式与 contexts 两个测试不传参数，行模式下每文件仍不许出现分支键（R4）。
  3. K1 追加：BRANCHY 的每文件 summary 若出现两键之一，必须是 4/2（`:224-229`）。它挡住每文件两值写错、而 `a.py` 上看不出来的实现。

```python
    # _assert_expected_json_report(self, cov, expected_result, optional_summary=None)
        del (parsed_result['meta']['timestamp'])
        # R2E revision (2026-09-29, R-b): a per-file summary may also carry the
        # two branch counts that the issue asks for in totals.  When it does,
        # both must be there with this file's values; everything else is
        # still compared exactly.
        for filename, counts in (optional_summary or {}).items():
            summary = parsed_result['files'][filename]['summary']
            if any(key in summary for key in counts):
                assert {key: summary.pop(key, None) for key in counts} == counts
        assert parsed_result == expected_result

    # test_branch_coverage
        self._assert_expected_json_report(
            cov, expected_result,
            optional_summary={'a.py': {'covered_branches': 1, 'missing_branches': 1}},
        )

    # test_branch_totals_count_branch_arcs, after the totals asserts
        # R2E revision (2026-09-29, R-b): if the per-file summary also carries
        # the two counts, they must be this file's counts.
        summary = report['files']['branchy.py']['summary']
        if 'covered_branches' in summary or 'missing_branches' in summary:
            assert summary.get('covered_branches') == 4
            assert summary.get('missing_branches') == 2
```

**为什么是"窄版"**：
- 只放行这两个键，而且必须成对出现、值正确；只加一个键，或加别的键，仍判 0。
- totals、每文件已有的 7 个键、行模式的形状，都仍按原样精确比较。
- 它不是把两种相反的输出用"或"并起来（v1 §3 P5 禁止的情形）：两种形状的 totals 相同，每文件只多出可核对的附加信息。主审（`analysis_before_history.md:328`）与复核（`review.md` §4.3 第 1 条）同此判断。

**新写的负对照 C1swap**（`cands/coveragepy_f5eb_C1swap.patch`，sha256 `6389c07a…`）：
- totals 同 gold；每文件块里 covered 取 `nums.n_missing_branches`、missing 取 `nums.n_executed_branches`。
- `a.py` 上仍是 1/1，只能靠 BRANCHY 的每文件核对挡下。
- 已在仓库外 base 副本上 `git apply --check -v` 通过。

**试跑**（结果文件 `trials/rb_<候选>.json`）：

| 候选 | 应得 | 应不符的键 | 试跑结果 | R-c 下 |
| --- | --- | --- | --- | --- |
| gold | 1 | — | 1，6/6 | 1 |
| noop | 0 | BC、K1、K2 | 0，恰好这 3 键 | 0 |
| C1 | 1 | — | **1，6/6** | 0 |
| C1swap | 0 | K1 | 0，只有 K1；`assert 2 == 4`，在每文件核对行（`HT'':228`） | 未跑（静态判断 BC 失败） |
| D0 | 0 | K1、K2 | 0，恰好这 2 键（`assert 1 == 4`） | 0 |
| C2 | 0 | K1、K2 | 0，恰好这 2 键（`assert 6 == 4`） | 0 |
| C3 | 0 | K2 | 0，只有 K2（`KeyError`） | 0 |

**判读**：
- R-b 纠正了 C1 的判分，放宽没有放过每文件值写错的 C1swap。
- R-c 的负对照在 R-b 下结果不变；gold 与 noop 符合预期。
- 未跑：W2、A1 不碰每文件 summary，走的路径与 gold、D0 相同，静态判断结果同 R-c；"只加一个键"的写法，静态判断在 BC 上失败。

## 8. 修订后仍受保护的公开要求与剩余事项

**受保护的公开要求**（R-c）：
- **分支模式下 totals 有两键**：BC（示例夹具）、K1、K2。
- **两值是已执行 / 未执行的分支弧数**（非示例实例）：K1（进程内）、K2（另起报告对象）。
- **按数据门控**：K2。
- **行模式下 totals 与每文件 summary 都不出现分支键**：`test_simple_line_coverage`、`test_context_non_relative`、`test_context_relative`。
- **示例夹具的其余输出**（meta、行号列表、每文件 summary 的 7 个键、百分比等）：BC 的整字典比较。选 A 时，每文件的这两个键例外（§7）。

**仍未覆盖，维持登记**：
- **T3**：多文件时 totals 的汇总、`report()` 返回值（I9）。
- **C1**：§6。
- **P6、P4、X1**：照旧。P6 指公开 `test_branch_coverage` 与任何正确修复冲突。X1 的训练侧影响待写进记录（`review.md` §5）。
- **稳定性**：每个候选试跑 1 次；新测试是确定性的。
- **正式评分**：试跑工具不是正式评分，正式材料上的评分还没跑。

## 9. 边界与交接

- **只做了 v1 §5 模板内的 R-c**：
  - R-b 只做成备选草案并试跑，没有落地；R-f 只写了草稿句子，没有验收。
  - R-c 没有删键，没有放宽已有断言，没有改题面，没有复制 gold 输出作期望。
- 没写 `s2_r2e` 下的正式修订单与 pins，没改生产代码。
- **协调者待办**：
  1. 把 `revision_draft.json` 落为正式修订单：`hidden_test_text_replace`（1 处 edit），另加 `expected_file_replace`（`added` 两键）。
  2. 重建材料与派生镜像。
  3. 正式评分至少跑 gold、noop、D0、C2、C3、C1、**W2**（W2 已是已知相关错误候选，按 Codex 复核改为必跑），可加 A1；按 §5.2 逐键核对：gold 6 键全部解析且 `keys_equal=true`；C3 只在 K2 上以 `KeyError` 失败。R-b 下未跑的 W2 / A1 不写成已验证。
  4. 送 Codex 复核。
  5. 把 §6 交用户：
     - 选 A：用 `revision_draft_rb.json` 的合并条目替换隐藏测试条目，正式评分加跑 C1、C1swap；
     - 选 B：安排新公开读者与题面修订；
     - 选 C 或不裁定：按 §6.4、§6.5 登记。
- **之后**：按 `card.md` §5 重判四项用途，并补 X1 的训练侧登记。
