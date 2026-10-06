# 独立复核：coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96（第二步）

复核者第二步（2026-09-29，单题闭环试行，按统一标准 v1）。第一步初判是同目录的 `reviewer_initial.md`，本步没有改它。本步读了公开读者产物、主审产物、历史引用，以及今晚新机器上的实跑。

路径简写（均相对仓库根目录；`PUB`、`PRIV`、`WT`、`LOG_N` 沿用初判）：

- `R` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`
- `NEW` = `runs/r2e_lifecycle_20260929`；`INV` = `NEW/inv/coveragepy_f5eb`；`DC` = `NEW/devcheck/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`

## 0. 结论先行

| 项 | 复核意见 |
| --- | --- |
| S1 定稿 | **同意。** D0、C2、C3 在当前材料、新镜像、正式 profile 上都得 1.0；补丁确已交付，4 个键都执行并被解析（§2）。T2c（示例拟合）、T2b（退化候选得 1）、第 4 步两例的证据齐全 |
| R-c 两项 | **同意，可以按 `R/card.md` 附录 A 开做。** 第 1 项挡住 D0、C2（以及没跑过的"两字段对调"），第 2 项挡住 C3。两项都只断言 totals，公开依据不来自 gold；我没找到会被它们误拒的合理实现（§3）。验收时要补三处核对（§3.4） |
| 第 2 项是否必需 | **必需，不能降为 T3。** 文档写明的分支流程是先 `coverage run --branch`，再另起进程执行 `coverage json`，而 `json` 子命令没有 `--branch` 选项。C3 在这条路径上缺键（P-2）。这属于同一核心要求的常用实例（v1 §4 第 4 步） |
| C1（每文件 summary 也加两键） | **修改我的初判。** 由"不算 T1、只登记"改为"P3 争议、T1 未证实"，与主审标签一致。选项上我现在也倾向 R-b 的窄版：只放行这两个键，出现时必须验值（理由见 §4.2） |
| 交用户的写法 | **需要补齐。** 主审分析写"由复核裁定"（`R/analysis_before_history.md:332`），题卡改成"交用户"（`R/card.md:7,82-85`），前后不一致。三个选项都缺前提、验收、对用途的影响，也没写不裁定时的默认做法（§4.3） |
| X1 对用途的影响 | **部分已登记。** 留出侧（ea6906b0）写了；训练侧只在 `checks.5` 里有一句"控制重复采样"，`usage.v1.training_candidate` 没写。另漏了一条交互：ea6906b0 的初态和新版 coverage 都是"每文件 summary 也有两键"的形态，会提高 C1 型解出现的概率（§5） |
| 我初判的漏项 | 我漏了 R5 / C3（按配置门控）。我初判提出的单测试 R-c 挡不住 C3，放弃，改用主审的 BRANCHY 两项（§7） |

**一句话：** R-c 可以按主审草案开做。C1 建议与 R-c 同轮按 R-b 窄版处理；如果协调者仍要交用户裁定，请先按 §4.3 补齐选项说明。

## 1. 本步读取范围

- **公开读者产物。** `R/public_read.md`、`R/commands.json`，全文。
- **主审产物。**
  - 全文：`R/analysis_before_history.md`、`R/old_findings_delta.md`、`R/card.md`、`R/screening_record.json`。
  - `R/cands/` 下 4 个补丁，与 `INV/` 下的副本逐字节比对一致。
- **历史引用。** 按 `runs/r2e_static_prep_20260924/v3/history/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/refs.json`：
  - 全文读了 `findings.md`、`facts.json`、repro 脚本；`screening_record.json` 读了前 150 行（R01–R15）。
  - `known_issues.json`、`decisions.md`、`results_20260924.md`、`packages/p1/README.md` 只 grep 了本题。
- **新机器实跑。**
  - `NEW/env_verify/ledger_l1_noop.jsonl:2`、`ledger_l1_gold.jsonl:2`：只看账本行，日志在远端，本地没有。
  - `INV/ledger_{D0,C1,C2,C3}.jsonl` 及对应的 `logs_*/…eval.log`：日志 sha256 与账本一致；未打开 diagnostics。
  - `INV/pcheck_*.json`（7 份）、`INV/private_P{1,2,3}*.{py,sh}`、`INV/run.sh`。
  - `DC/devcheck.log`、`DC/private_control.{json,log}`、`DC/orig/captures/*.out`、`DC/orig/prelaunch.json`、`DC/orig/post_run_facts_root.txt`、`DC/orig/activation_check.json`。
- **补核的公开源码。** `WT/doc/branch.rst:25-56`、`WT/coverage/cmdline.py:374-388,532-544`、`WT/coverage/config.py:180-184`、`WT/coverage/control.py:335-339`，以及 `setup.cfg`、`tox.ini`、`metacov.ini` 里的 `branch =`（只有 `metacov.ini:10`，它不是默认 rc 文件）。
- **未读。** `NEW/` 下其它文件（例如 `codex_review_*.jsonl`、`prompts*`）、v4 / v5 材料、其它题的私有包。主审所说"v3–v5 对本题逐字相同"我没有核。

## 2. 主审决定性主张逐项核对

| # | 主审主张 | 我核了什么 | 结论 |
| --- | --- | --- | --- |
| A1 | 题面报错就是隐藏测试在 noop 上输出的 "Differing items" 行，所以第 2 步按构造必然命中 | 初判已核：`LOG_N:93` 对照 `PUB/user_prompt.txt:28` | 同意 |
| A2 | D0 = 1.0（T2b） | `INV/ledger_D0.jsonl:1`：reward 1.0，4/4，`included_paths=["coverage/jsonreport.py"]`，`patch_sha256` 前缀 `1644ae7c` 与补丁文件一致。日志 `INV/logs_D0/…16189261.eval.log`：第 1 行为 ` M coverage/jsonreport.py`；`RH2_SETUP_HIDDEN_TESTS_TREE=d03ee4ff…`（当前材料）；`APPLY_RC=0`；4 个 PASSED | 同意 |
| A3 | C2 = 1.0，BRANCHY 上报 6/0 | `INV/ledger_C2.jsonl:1`，按 A2 同样核法（补丁前缀 `85d59dd2`）。`INV/pcheck_P3_C2.json`：JSON 为 6/0，XML 为 `branches-covered="4" branches-valid="6"` | 同意。违反 R3 有公开依据：`results.py:35-36` 区分 partial 与 missing；`WT/tests/test_api.py:989-991` |
| A4 | C3 = 1.0，文档流程下缺键 | `INV/ledger_C3.jsonl:1`（补丁前缀 `55e34064`）。`pcheck_P2_C3.json`：原样执行公开命令 `repro_cli_json`，totals 没有两键；`pcheck_P2_gold.json`：1/1。`pcheck_P3_C3.json`：进程内 4/2，另起报告对象后缺键 | 同意。公开依据已核：`doc/branch.rst:38-40,52-54`；`cmdline.py:374-388`（json 子命令没有 `--branch`）；`cmdline.py:532-544`；`config.py:182`（`branch` 默认 False） |
| A5 | C1 = 0.0，差异只在每文件 summary | `INV/logs_C1/…61e26907.eval.log:92-94`：显示 "Omitting 2 identical items"，差异项只有 `files`；第 108-109 行只有 `test_branch_coverage` 失败 | 同意 |
| A6 | 新镜像上 noop 0、gold 1 | 两条 env_verify 账本行：noop 3/4，只差目标键；gold 4/4，gold 补丁 sha `c8fa460d`。镜像 `98b19b5a2ce4…`、配方 `+sysconfig_v1`、profile `3ec1bfa8…`，与候选运行相同 | 同意（只核了账本行） |
| A7 | devcheck 13 项检查为真，公开命令符合预期；P6 成立 | `DC/devcheck.log`。`DC/orig/captures`：agent 身份 uid 54321；初态 `repro_api_totals` 退出码 1；`test_json` 4 passed；pytest 4.6.6 + xdist 1.30.0 + flaky 3.6.1。`DC/private_control.json`（root 身份 + gold）：`repro_cli_json` 为 1/1；`public_test_json` 的 rc=1，差异只在 totals | 同意。注意 private_control 与 P-2 / P-3 都是 root 身份的私有核对，不代表 actor 条件；P6 是代码层事实，与身份无关 |
| A8 | P-1：agent 在 cwd=/ 下导入的仍是 `/testbed/coverage` | `pcheck_P1_agent_cwd_root.json` | 同意。这也解除了我初判里"在 /testbed 之外导入的是哪一份 coverage"的未知 |
| A9 | 历史只是环境审查，没有题意层结论 | refs 所列文件 | 同意。`findings.md:11` 自己写明"判分面较窄（题目质量问题，不属本轮）" |

## 3. R-c 草案复核（`R/card.md` 附录 A）

### 3.1 能否挡住已知错误解

| 候选 | 第 1 项：BRANCHY，进程内 | 第 2 项：保存后另起对象 | 预期 reward | 依据 |
| --- | --- | --- | --- | --- |
| gold | 6/0/4/2，通过 | 4/2，通过 | 1 | `pcheck_P3_gold.json` |
| D0 | 1/1，失败 | 1/1，失败 | 0 | `pcheck_P3_D0.json` |
| C2 | 6/0，失败 | 6/0，失败 | 0 | `pcheck_P3_C2.json` |
| C3 | 4/2，通过 | 缺键，`KeyError` 失败 | 0 | `pcheck_P3_C3.json` |
| C1 | 通过 | 通过 | 0（只因原有的 `test_branch_coverage`） | R-c 对 C1 中立 |
| W2 两字段对调（未跑） | 2/4，失败 | 2/4，失败 | 0 | 推导 |

两项合起来能同时挡住 D0、C2、C3。第 2 项的测试写法（先 `save`，再用不设 `branch` 的 `Coverage(data_file=...)` 执行 `load`）与已跑过的 P-3 脚本相同，也与真实 CLI 路径（P-2）结论一致。

### 3.2 会不会误拒合理实现

- **下列写法在两项上都得 4/2，会通过：**
  - 门控用 `coverage_data.has_arcs()`、`analysis.has_arcs()` 或 `config.branch or has_arcs`；
  - 计数取 `self.total` 的现成属性，或在 `report_one_file` 里逐文件累加 `analysis.branch_stats()`。
- **"按分支行计数"的读法会在第 1 项被拒，但这不是误拒。**
  - 这种读法把出口全走到的行记为 covered，把有出口没走到的行记为 missing，在 BRANCHY 上得 2/1。它在题面示例上同样能蒙到 1/1，所以正需要第 1 项把它拦下。
  - 拒它有公开依据：`WT/doc/branch.rst:45-46` 写明 "each branch destination" 是一个执行机会；同一个 totals 里的 `num_branches` 是按弧计的（a.py 只有一个 `if`，却计 2）；XML 的 `branches-covered` 也按弧计。
  - 建议把 `doc/branch.rst:45-46` 补进附录 A 的依据表。
- **夹具锚点合理。** 第 1 项的 `num_branches`、`num_partial_branches` 和第 2 项的 `meta.branch_coverage is True` 都是 base 已有的行为，只用来锚定夹具，没有新增要求。
- **仍然放过的情形：多文件汇总写错。** 例如在 `report_one_file` 里用赋值代替累加，单文件测试看不出来。主审已登记为 T3（I9），我同意不作为开做条件。若想顺手堵上，可以让第 1 项同时报告两个模块；但这会改动已由 P-3 核过的夹具，需要重新核值。

### 3.3 需求范围与期望值来源

- **没有扩大需求。** 两项都是"开启分支测量时，totals 含正确计数"这一核心要求的实例。第 2 项对应公开读者只看公开包时就提出的 R5（`R/public_read.md:16`）。
- **期望值不是抄 gold 的输出。** 来源是主审附录 B 的静态推导（`R/analysis_before_history.md:420-438`），加上 P-3 里 XML 的独立计数。我初判对另一个夹具的手算也按同一口径得出结果。

### 3.4 验收时补三处

1. **R-c 测试还没在评分路径上跑过。** P-3 是 root 身份的独立脚本（用 importlib 导入），不是 pytest 下的 `start_import_stop`。验收 gold 时要核：`num_parsed_tests=6`、`keys_equal=true`，两个新键在日志里是 PASSED 行。
2. **失败位置要对。** C3 只能在 `test_branch_totals_from_saved_branch_data` 失败，且原因是 `KeyError`；D0、C2 在两个新键上都失败；noop 在 3 个键上失败。这与附录 A 矩阵一致，逐键对上才算通过。
3. **可选（各跑 1 次）。**
   - W2（totals 两字段对调）应为 0。
   - 一个非 gold 的正确写法应为 1，用来说明 R-c 不依赖 gold 的具体写法。写法：在 `JsonReporter.__init__` 初始化两个计数；在 `report_one_file` 的 has_arcs 块里分别累加 `sum(k for t, k in analysis.branch_stats().values())` 与 `sum(t - k for t, k in analysis.branch_stats().values())`；在 totals 的 has_arcs 块输出。

## 4. C1 争议

### 4.1 两边是否一致

- **事实一致。**
  - C1 只因为每文件 summary 多了两个键被判 0；totals 没有分歧。
  - 两边都主张保留原始 reward，在探针分析里把它列为疑似规格争议样本，并且不阻塞 R-c。
- **分歧在强度与推荐选项。**
  - 我初判：不算 T1，建议维持原样。
  - 主审：P3 / 疑似 T1，倾向 R-b，交用户裁定（`R/card.md:82-85`；`screening_record.json` 的 `issues[I5]`）。

### 4.2 我改判的理由

- **疑义是只看公开包就会出现的。** 公开读者把这一点判为"多种合理解释、公开材料判断不了"（`R/public_read.md:18,40,64`）。这说明真实解题者会分成两种做法。
- **每文件键集的依据弱，但不是零。**
  - 唯一依据是公开旧测试的整字典比较（`WT/tests/test_json.py:35,50-58`），而同一条测试的 totals 部分注定要失败（P6）。
  - 公开文档也没有描述 JSON 的结构（`R/public_read.md:51`）。
  - 所以我写"T1 未证实"，不写"已证实误拒"。
- **R-b 窄版不会放过核心要求上的错误解。**
  - 窄版只放行这两个键，行模式和其它键仍然精确比较，totals 不变。
  - 再配合第 1 项里"每文件若出现这两个键，必须是 4/2"，以及 C1-swap 负对照，每文件的错误值也拦得住。
- **版本代价已经付过。** R-c 已使本题成为"标明版本的自建题"，R-b 不再增加这方面的代价。
- **维持原样有训练代价。** 它会把一类核心正确的解判 0，在训练里是与题意无关的噪声；而 X1 让这类解更常见（§5）。

### 4.3 选项写法需要补齐（给主审或协调者）

1. **谁来定。**
   - v1 §5 与 §9 D4 已经预授权 R-b 和 R-f，原则是"不逐题上报"（v1 §0 第 5 条）；主审分析也写了"由复核裁定"。
   - 本复核意见：R-b 属于模板内。它放宽的是依据弱的输出形状约束，不是任务目标，也不是 P5 那种把两种相反输出用"或"并起来。
   - 协调者若接受这一归类，可以与 R-c 同轮实施，不必等用户。若协调者认为"是否奖励题面以外的对称扩展"属于需要用户定的范围政策，再交用户；那时题卡要写明两个角色的意见，以及下面几项。
2. **每个选项要写清改什么、前提和验收。**
   - **R-b。** 改动：`_assert_expected_json_report` 加 `optional_summary` 参数；第 1 项加每文件的条件断言；建议两个键同进同出（只出现一个也算失败）。验收：C1 → 1，C1-swap → 0，再加 R-c 矩阵。C1-swap 的写法是：totals 同 gold，每文件块里 covered 取 `nums.n_missing_branches`、missing 取 `nums.n_executed_branches`；它在 a.py 上仍是 1/1，只能靠 BRANCHY 每文件断言拦下。成本：同一轮多跑 2 次评分。
   - **R-f。** 前提：R2E 的"题面文本替换"类尚未实现（v1 §9 D6），需要新的公开读者按 R-f 验收，并经 Codex 复核。句子见 `R/analysis_before_history.md:329`。效果：C1 仍判 0，但题面已经明说只改 totals。
   - **维持原样。** 不改动；C1 型解得 0 作为已登记的风险；探针分析时按疑似规格争议单列。
3. **写清对用途的影响。**
   - 选 R-b 或 R-f 并通过验收后，C1 不再阻塞能力比较和训练候选。
   - 明确选"维持原样"也算已裁定，可以放行，但要登记风险。
   - 不裁定时：R-c 照做；本题的能力比较和训练候选保持 conditional（按主审）。
4. **理由措辞。**
   - "上游后来正是这样做的"（`R/card.md:83`；`R/analysis_before_history.md:193`）来自未来的提交（`ea6906b0` 的初态），解题者看不到，只能作外部佐证。
   - 公开依据应写成三条：代码里两处分支块对称（`jsonreport.py:59-63` 对 `:94-98`）；其它报告在每文件一级也给分支数（`summary.py:86`，XML 按类给）；每文件的形状只有整字典比较的测试作依据。
5. **引用。** 能力比较那条"题意争议未消解只作问题定位"出自 v1 §11 的 SWE-Gym 条目，用于 R2E 是类推，应写明。另外 v1 §2 对能力比较的要求是"争议……单列"，按这一读法，也可以把 C1 型结果单列计数，而不整题剔除。选哪种读法由协调者定；无论哪种，都不影响 R-c 开工。

## 5. X1 对用途的影响

- **已登记。** `screening_record.json` 的 `checks.5`、`issues[I8]`、`usage.v1.heldout_candidate.reason`（ea6906b0 含本题答案；按 D3 以仓库划分，两题在同一侧）。
- **缺第 1 项：训练侧的具体影响。** `usage.v1.training_candidate` 没写。
  - `97997d2c` 与本题初态逐字节相同，训练时要控制同一初态的重复采样。
  - `ea6906b0` 的初态含本题答案，而且已经是"每文件 summary 也有两键"的形态。两题同在训练集时，这是重复暴露，不是评测污染；但它会把模型推向 C1 型输出，与 §4 的选择直接相关。
- **缺第 2 项：反向关系的同步登记。** 本题初态含 `016af5f6`、`5dbbe143` 的答案（`WT/coverage/control.py:337` 的 `once` 参数；`WT/tests/test_oddball.py:566`、`WT/tests/test_api.py:557`）。这影响的是那两题的留出资格：按仓库划分它们与本题同侧即可，但应在那两题的卡片上同步登记。
- **能力比较不受影响。** 每题都在独立上下文里求解，X1 不构成泄漏。

## 6. 反查主审可能没想到的范围

- **题面原例与非默认值。**
  - 题面示例不传 `morfs`，报告会覆盖多个文件；多文件汇总没有测（T3，已登记）。
  - `pretty_print`、`show_contexts`、`--contexts` 过滤都不影响 totals 计数的口径，没发现新缺口。
- **调用者。** `report()` 的返回值（供 `--fail-under` 使用）没有测；gold 没改这里，T3 已登记。
- **共享机制。**
  - devcheck 显示 agent 能写 `.venv`（`DC/orig/post_run_facts_root.txt` 列出 `/testbed/.venv/…/_pytest/__pycache__`）。
  - 隐藏测试引用的 base 测试辅助在评分时不会被重置。R-c 的新测试同样依赖 `make_file` 和 `start_import_stop`，暴露面不变。
  - 同意主审交 A 线（清单 #31）。
- **账本字段。** `code_snapshot_ref` 为 null，需要协调者补填。

## 7. 对我初判的更正

1. **漏了 R5 / C3。** 我只查了计数口径，没有想到"报告对象的配置与数据不一致"这条路径。公开读者和主审都查到了，而且 C3 实跑得 1.0。
2. **我初判的 R-c 不够。** 那是一个 `bcount.py` 单测试，全程在进程内、`branch=True`，挡不住 C3。放弃它，采用主审 BRANCHY 的两项；它们的值已由 P-3 在评分镜像上核过。我手算的 6/4/2/0 与 BRANCHY 数值相同只是巧合，两个夹具不是同一个。
3. **C1 的立场已修改。** 见 §4.2。
4. **两个未知已解除。**
   - "在 /testbed 之外导入的是哪一份 coverage"：由 P-1 解除。
   - "actor 开发条件待验"：由 devcheck 满足。
5. **初判 §12 的未满足项。** ① D0 正式评分、③ actor 开发核对，现在都已满足。

## 8. 流程检查

- **没有看过答案再把隐藏要求说成"显然"。** 主审把 R7 标为争议；R3、R5 给出的公开依据，与公开读者独立得出的一致。
- **公开读者的疑义处理得当。**
  - R3、R5 能由公开材料消除，主审把它们当作测试缺口处理，正确。
  - R7 不能消除，主审列为争议，正确。
  - P4 能消除，主审只登记，正确。
- **其余检查。**
  - 探针就绪表把静态候选与剩余条件分开了（`R/card.md:91-100`）。
  - 没有把 `environment_qualified` 当成质量合格（`R/old_findings_delta.md:19`）。
  - 不是只核旧结论：历史只有环境层，题意层是新做的。
- **小问题。** 主审分析与题卡对"谁来裁定 C1"的说法不一致，见 §4.3。

## 9. 用途与探针就绪（复核意见）

- **`problem_localization`：yes。**
- **`capability_comparison`：conditional。** 还差：C1 的处理（R-b 同轮验收、用户裁定，或按"单列"读法处理），以及在 R-c 验收前纳入时，要按预登记的三项做事后审计。devcheck 与新镜像上的 noop / gold 两项已满足。
- **`training_candidate`：no。** 重评的前提：R-c（以及 R-b，如采纳）验收通过，并经 Codex 复核；同时把 X1 的训练侧影响写进记录。
- **`heldout_candidate`：no。** 与主审一致。
- **总的看法。** 与主审一致，唯一差别是 C1 的推荐处理和谁来裁定。

## 10. 最小后续实验

1. 按附录 A 实施 R-c（若协调者采纳 R-b，同轮一起做），在新材料上跑一轮正式评分：gold、noop、D0、C2、C3、C1；采纳 R-b 时加 C1-swap；可选加 W2 与非 gold 正确写法。共 6–9 次。逐键核对 §3.4 的三处。
2. 交 Codex 复核，保存新版本与父版本；触发反例用 `INV/` 下的 D0、C2、C3（采纳 R-b 时加 C1）。
