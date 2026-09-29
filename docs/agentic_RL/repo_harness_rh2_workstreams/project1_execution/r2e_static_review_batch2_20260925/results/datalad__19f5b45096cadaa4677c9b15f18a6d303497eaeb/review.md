# datalad__19f5b450 独立复核：第二步

复核者：Claude（R2E 独立复核角色），2026-09-25。本步在读完公开读者、主审产物和历史引用之后写成。

- 做了什么：静态阅读，并核对已有证据。
- 没做什么：没有运行代码或容器，没有改任何原件。`reviewer_initial.md` 是封存稿，也没有改。

证据分三类，写法约定如下：

- **正式评分**：协调者 09-25 用 RH2 回放代码在 derived9 镜像 `851a10b6…` 上跑，每个候选 1 次。
- **公开侧对照**：一次性容器，root 身份，不联网。它既不是 grader，也不是真实 actor。
- **静态推断**：没有执行过。

## 0. 结论

**同意主审的核心结论：**

- 题意可以从公开材料恢复。
- 材料、初态故障和 gold 三者一致。
- 唯一的目标键只测题面原例，评分偏宽。
- 没有发现合理修复被误拒。
- 处置为 `needs_review`：它是静态候选，待 actor 验证，另附“测试偏窄”。用途限于 development_diagnostic。
- 若要进入训练奖励，需要先做补测修订。这属于 T0，由用户决定。

**执行证据已经证实“测试偏窄”：** 三个错误实现都得 1，即 K2（恢复抛 `CommandError`）、K3（取第一条失败记录的 `exit_code` 且不回退）、H（硬编码 3）。合理替代解 K1 也得 1。K4（gold 基础上再往 Python 层 stderr 打印一行）得 0，唯一不符的键是 `test_run_exit_code`，失败在 `test_1.py:87`。这些结果与主审的预测一致，也与我初判的 C1–C5 一致。因此 checks 25/26/32 的证据级别应由“静态推断”改为“正式评分 1 次”。

**修改 1：stderr 约束怎么定性。** 主审把“Python 层 `sys.stderr` 必须为空”写成“有公开依据的隐含约束”，但公开依据其实指向两边：

- 支持这条约束的：题面示例所用 `run_main` 的默认值 `expect_stderr=False`。
- 指向相反方向的：`docs/source/design/cli.rst` L65-71 说命令失败时“the error is reported, as if the command would have been executed directly”；`main.py` L224 的 `_communicate_commanderror` docstring 用的是同一说法。

对真实命令行用户来说，K1 用 `os.write(2)` 输出、K4 用 `print(file=sys.stderr)` 输出，结果都是 stderr 上多一行。评分之所以能区分二者，只是因为 `run_main` 替换的是 Python 的 `sys.stderr` 对象，不捕获 fd 2。

我仍不把 K4 叫作“合理修复被误拒”，理由见 §3.1。按补充规则 1，K4 应单列为“遵循冲突示例的候选”：失败在同一个键、但断言位于 L87（而不是 L83）的样本，标为“疑似规格争议待复核”，原始 reward 0 保留。check 24 建议由 pass 改为 issue（低）。

**修改 2：补测最小化。** 主审提议的 4 类补测都有公开依据，也不扩大原需求。但只要三条进程内 CLI 断言，就能区分全部已知错误候选：

1. `exit 5` 应退 5；
2. 输入缺失应退 1；
3. `--on-failure ignore` 应退 0。

Python API 断言可以作为可选项。补测属 T0，由用户决定，决定前应先在沙盒试跑（§3.3）。

**新的证据缺口：** H 的评分只见于协调者转述。本地 `runs/r2e_actor_20260925/grader/` 里没有 H 的账本或日志，只有补丁 `grader_cands/datalad_19f5_H_hardcode_exit_3.patch`（sha256 `f84d6fdd…`）。

## 1. 新执行证据核对

| 候选 | 补丁 sha256 前 8 位 | 补丁与描述是否一致 | 正式评分（本地账本 / 日志） | 公开侧对照 |
| --- | --- | --- | --- | --- |
| gold | adfb3a3b | — | 1，19/19。`grader/ledger_d19f5_gold.jsonl`；`eval_logs/evallog_replay-2b261be984a2-data_c5d14c3c.eval.log` L130 为 PASSED | `private_gold_full`：pr1 五例依次 3/3/0/1/0；pr4 全过；console script 退出 3 |
| K1 | 76da16ac | 一致：只取第一条 `action=='run'`、且 `exception` 为非零 `CommandError` 的记录，先 `_communicate_commanderror(e)` 再取 `.code` | 1，19/19。`…434271e44b56…eval.log` L45 的 `CommandError: 'exit 3' failed…` 出现在 pytest 捕获的 stderr 里，没进 `fakeerr`；L131 为 PASSED | `private_public_b2/d19f5_K1….json`：3/3/0/1/0；pr4 全过 |
| K2 | 18d8b1fc | 一致：删掉 `run.py::_execute_command` 里的 try/except | 1，19/19。投影为 `datalad/core/local/run.py`。`…5e57c388f1f9…eval.log` L43 的 CommandError 在 pytest 捕获里；L126 为 PASSED | `d19f5_K2….json`：五例依次 3/3/0/1/**3**，ignore 模式也退 3；pr4 中 **`test_basics` 与 `test_run_failure` 失败**，两处都是 `CommandError` 取代了预期的 error 记录或 `IncompleteResultsError` |
| K3 | b3d00aab | 一致 | 1，19/19。`…d618dc8d4268…eval.log` L130 为 PASSED | `d19f5_K3….json`：输入缺失一例为 **EXIT None**，真实进程会以 0 退出；其余四例同 gold；pr4 全过 |
| K4 | ca816938 | 一致：gold 加一行 `print(..., file=sys.stderr)` | 0，18/19，不符 `test_run_exit_code`。`…4f0b745164ad…eval.log` L40 在 `test_1.py:87`，L44 为 `first = 'datalad: command exited with code 3\n'` | 未跑 |
| H | f84d6fdd | 一致：只加 `exit_code = 3` | **本地没有账本和日志**，只有协调者转述的 1（19/19） | 协调者转述：输入缺失一例退 3。本地没有文件 |

**材料版本与镜像。** 本地 5 份日志都有 `RH2_SETUP_HIDDEN_TESTS_TREE=2e5d11bf…`，说明是当前材料；都收集到 20 项，`test_help_np` 都是 SKIPPED。账本的 `scripts_digest d2af423c…` 与配方摘要 `0da821a1…` 都与 R-f 运行相同。因此“隐藏测试没在 `851a10b6…` 上跑过”这个缺口已经补上：gold 在该构建上 19/19。我初判 §1 和主审 `recipe_ref` 里的相应说明都已过时。

**K2 与我初判 C4 的关系。** C4 的改法是在 `run_command` 里加 `if exc is not None and not rerun_info: raise exc`，位置与 K2 不同。

- 对隐藏测试，两者效果相同：同一个 `CommandError` 进入 CLI 的 CommandError 分支，经 fd 2 输出，退 3。
- 对公开侧，K2 破坏得更多：它连 rerun 也一并改掉，并跳过 "Command exit" 这条日志。

C4 本身没有跑过。但要支撑“Python API 回归不受评分保护”这一结论，K2 的结果已经足够。

## 2. 主审的决定性主张逐项核对

| # | 主张与出处 | 引用是否支持；证据属于哪个版本和环境 | 判定 |
| --- | --- | --- | --- |
| 1 | 隐藏测试 = 公开 `test_main.py` + 1 个新测试 + 两行导入改写；唯一目标键只测原例（analysis §2–§3） | 我初判独立做的 diff 结果相同；current noop/gold 日志和新的 5 份日志都支持 | 同意 |
| 2 | K2、K3、硬编码 3 都会得 1（card §4.1） | K2、K3 有本地正式评分账本；H 只有协调者转述 | 同意，证据已升级；H 还缺本地证据 |
| 3 | 没有合理解被误拒；唯一的精确约束是 Python 层 stderr 为空（card §4.3，check 24） | K1=1、K4=0 证实了约束的边界；但“公开依据”只写了一侧，见 §3.1 | **修改**：定性和 check 状态都要改 |
| 4 | gold 满足 R1–R4、R6、R7（delta §2.1） | `private_gold_full`（root、不联网、`851a10b6`）：五例 3/3/0/1/0，console script 退 3，pr3/pr4 通过；gold 在同一构建上正式评分 19/19 | 同意 |
| 5 | 公开文档互相矛盾，这会诱导出 K2（issue `public-docs-conflict`） | 逐处核过：`run.py` L105-106 说会抛 `CommandError`；`CHANGELOG.md` L1191 说改抛 `IncompleteResultsError`、CLI 不再转发退出码；`cli.rst` L65-71 说转发。K2 在公开侧破坏 `test_basics`/`test_run_failure`，ignore 模式退 3，违反 `common_args.py` L95-99 | 同意。补充：这个陷阱用公开回归（公开读者建议的 C4/pr4）就能发现 |
| 6 | R7“ignore 退 0”有公开依据 | `common_args.py` L95-97 明写 ignore “does not lead to a non-zero exit code” | 同意 |
| 7 | R4“非命令失败退 1” | `cli.rst` L61-63 写着 “Incomplete results (exit code 1)” | 同意 |
| 8 | 与 58ba5165 同族（issue `relation`） | 核过三点：58ba 的 `interface/base.py` L187/L192 是 `[^\[\]]*`，本题 L218/L223 是 `.*?`；两题的 `cli/main.py` sha256 同为 `ce784b9d…`；CHANGELOG 顶部分别是 0.17.9（2022-11）和 1.1.3（2024-08） | 同意 |
| 9 | 另外三题属于 0.4–0.5 时代 | 16c1ffc3 的 CHANGELOG 是 0.5.x，9ba5de09 是 0.4.x；6b6fa389 既没有 `CHANGELOG.md` 也没有 `cli/`，版本没法取 | 同意；6b6fa389 的版本未核 |
| 10 | 隐藏测试没在 `851a10b6` 上跑过（`recipe_ref`，delta #2） | `ledger_d19f5_gold.jsonl` 已经补上 | **过时** |
| 11 | 历史 25 条逐条核对（delta §1） | 抽查的几项都支持主审的结论：`agent_probe.log` L146 为 `Author identity unknown`；M3 `pkgsrc.txt` 里只有 editable 的 dist-info（`file:///testbed`，editable=true）；M3 `git_scrub/out_after.txt` L151 只有 `test_run_exit_code` 失败；prelaunch 里 `DNS_EXTERNAL=DENIED`、`WORKDIR_OWNER=54321` | 同意 |
| 12 | 证据分级 | 主审各处都标了评分实跑、解题侧实测、私有对照、独立参考、历史探针（非正式链）。没看到把 superseded 行、M3、一次性试跑和 actor 混在一起用的情况 | 同意 |

## 3. 主审可能没想到的范围

### 3.1 stderr 约束的公开信号指向两边（新）

**支持约束的一侧。** 题面示例用 `run_main`，默认 `expect_stderr=False`（公开 `test_main.py` L53-98）。它要求被替换的 Python `sys.stderr` 为空。公开读者在读隐藏材料之前也发现了这一点，但标的是“多解”（public_read R9）。

**指向相反方向的一侧。**

- `cli.rst` L65-71 定义“内部 shell 命令失败”这一类：错误要被报告，就像直接在命令行执行一样，退出码与底层命令一致。
- `main.py` L223-224 的 `_communicate_commanderror` 正是这一类的实现，docstring 是 “Behave as if the command ran directly”，输出走 `os.write(2, …)`（L228）。

也就是说，公开设计文档鼓励“报告错误并转发退出码”。

**执行事实。** K1 走的是这条现成路径，得 1；K4 改用 `print(file=sys.stderr)`，得 0。对真实命令行用户，两者都是 stderr 上多一行，没有可观察的区别。评分能区分它们，是 `run_main` 的实现细节造成的。

**定性。** K4 符合题面文字，也符合 `cli.rst`，但违反题面示例所用 helper 的默认约束。所以我按补充规则 1 把它单列为“遵循冲突示例的候选”，而不叫“合理修复被误拒”。理由有两条：

- 公开代码已经有同时满足两边的现成途径（`_communicate_commanderror`）；
- 把题面示例的导入改正后运行（公开读者 C2 或 devcheck pr2 那种写法），就能暴露 K4 的问题。

**影响。** 低，但不只是“随手 print”才会踩到：照 `cli.rst` 去补错误报告的模型也可能落进来。

**建议：**

- issue `stderr-exactness` 补两处反向依据（`cli.rst` L65-71、`main.py` L224），并附上 K1 作为两边都满足的例子；
- check 24 由 pass 改为 issue（低）；
- 真实 rollout 中，凡是 `test_run_exit_code` 失败在 L87（`assert '<非空>' == ''`）、而 L83 的退出码断言已经通过的，标为疑似规格争议待复核，原始 reward 保留。

### 3.2 失败键相同，原因不同（新，对应补充规则 1）

- noop 与 K4 都只错 `test_run_exit_code` 这一个键，原因不同：noop 断言在 L83（`1 == 3`，没修好）；K4 在 L87（退出码已经对了，只是多了一行 Python 层 stderr）。
- 键级别的诊断分不开这两种情况。要筛出疑似规格争议，得看断言的位置和信息。
- 反过来，H、K3、K2 和 gold、K1 都是 19/19。用作诊断时，通过的补丁要另跑公开回归（pr1 五例加 pr4）作旁证。旁证结果单列，不改 reward。主审的 `proposed_action` 已经包含这一点，我同意。

### 3.3 最小补测（只在进入训练奖励时考虑）

三条断言都用进程内 `run_main`，每条用一个新的临时数据集：

| 断言 | 公开依据 |
| --- | --- |
| (a) `run --explicit 'exit 5'` → 5 | 题面 “the same non-zero exit code … (e.g., 3)” |
| (b) `run --explicit -i does-not-exist 'exit 3'` → 1 | `cli.rst` L61-63；`main.py` L200-201。如果担心过严，可以只断言非零，依据 CHANGELOG L1191 “continues to exit with a non-zero exit code” |
| (c) `--on-failure ignore run --explicit 'exit 3'` → 0 | `common_args.py` L95-97 |

**区分力（推断，依据是 §1 的执行事实）：**

- H：(a) 得 3，(b) 得 3，不通过；
- K3：(b) 得 None，不通过；
- K2：(c) 得 3，不通过；
- K1 与 gold：(b)=1、(c)=0 已在公开侧对照中观测到；(a) 按实现推断为 5，能通过。

**是否扩大需求：** 没有。(a) 属于题面原意，(b)、(c) 是有明文记载的旧行为。

**未知：** 在 `run_main` 默认 `expect_stderr=False` 下，gold 和 K1 跑 (b)、(c) 时 Python 层 stderr 是否为空。按 gold 私有对照，这两例的输出只有日志和 stdout 上的结果行，推断为空。需要沙盒试跑确认；如果不为空，(b)、(c) 改用 `expect_stderr=True`。

**Python API 断言（主审提议的第 4 条）可以作为可选项。** 它是唯一直接保护 R6 的断言，但 K2 已经会被 (c) 抓住。如果引入 `test_run.py` 的用例，还会增加键的数量，并带来 git-annex 依赖（评分镜像里有 git-annex）。

**流程：** 属 T0，因为改变了测试标准和期望映射，需要用户决定。实施时沿用既有的修订流程：新材料版本、重建派生镜像，gold 与 noop 各跑 ≥2 次，并用 K1/K2/K3/K4/H 做双向复验。

### 3.4 记录层面

以下内容已经过时：

- `screening_record.recipe_ref.actor_devcheck_image_id` 的注释写着“隐藏测试未在此构建上运行”；
- `disposition.pending` 里的 K1–K4 评分实跑已经完成；
- checks 25/26/32 的证据应更新为正式评分；
- `costs.candidate_runs` 可以填 5（gold 与 K1–K4，本地可证），H 待补证据。

另外，记录模板要求把静态候选另列在 `probe_candidates.json`，本题目录里没有这个文件。是否补由协调者决定。

## 4. 方法层面的检查

- **是否先看了答案，再把隐藏要求说成“显然”：** 没有发现。R2/R4/R6/R7 的依据都是公开文本（题面、`cli.rst`、`common_args.py`、CHANGELOG、公开测试），不是从 gold 反推的。stderr 约束在公开读者读隐藏材料之前就已经被指出过。不足之处只是反向信号没写全（§3.1）。
- **公开读者的疑义能否从公开材料合理消除：** 都能。
  - R8/R10（多失败、其它命令）：评分不涉及，任何选择都接受。
  - R9（stderr）：用现成的 fd 2 途径就能两边都满足。
  - 文档矛盾：CLI 退出码按题面加 `cli.rst` 处理，Python API 按 CHANGELOG 加公开测试保持不变。
  - git-annex、console script、身份：devcheck 已经实测。
- **修订建议是否扩大原需求：** 没有，见 §3.3。主审也正确地把它标为 T0、需用户决定。
- **“可探针”是否把静态候选与剩余条件分开：** 分开了。记录里 `static_candidate: true`，`pending` 单列 actor 求解与渲染消息。现在 K 系列评分已经做完，剩下的条件只有：真实模型求解、实际渲染消息，以及“通过的补丁要附公开回归旁证”这条解读规则。
- **是否把“环境已验”当成“质量合格”：** 没有。主审明确把历史的 `environment_qualified` 限定在环境维度。
- **是否只在核对旧结论：** 不是。读历史之前的 `analysis_before_history.md` 已经独立完成了八个方面的核查。

## 5. 与我初判的差异及理由

1. **初判低估了公开文档的矛盾，这里修正为同意主审。** 初判只把 CHANGELOG L1191 与题面的关系判为“可合理消除”，没有读 `cli.rst`，也没有把 `run.py` L105-106 的 docstring 当作错误路线的公开诱因（虽然我列了 C4）。主审把三者的矛盾记为 prompt_quality 问题，K2 的公开侧结果（ignore 退 3、公开 run 测试失败）说明这个诱因确实会产出一个得 1 的回归实现。
2. **初判对 stderr 约束的判断是“有公开依据（低）”，现在补上反向依据**，定性见 §3.1。
3. **初判的镜像 ID 缺口已补上**（§1）。
4. **初判的 5 个候选预测全部与执行事实一致**：C1≈K1，C2=H（本地缺证据），C3=K3（包括 `EXIT None`），C4≈K2，C5≈K4。
5. **初判的补测只提了 exit 5 和输入缺失两条，现在加上 ignore→0**：它不需要引入 Python API 测试就能抓住 K2。这与主审的方向收敛。

## 6. 保留的分歧

- **D1：stderr 约束的定性和 check 24 的状态。** 主审记为 pass 加一个低风险 issue，依据只写一侧。我认为应记为 issue（低），依据是两边都有，失败样本要标疑似规格争议。事实层面没有分歧（K1=1、K4=0），分歧只在记录口径，由协调者收敛。
- **D2：补测范围。** 主审提 4 类，我提 3 条最小集。两者都是给用户的提案，不需要在本审查内收敛。
- **未解决：H 的正式评分本地没有证据。**

## 7. 最小后续实验

1. **补齐 H 的证据**：取回 H 的账本和日志，或者重跑 H 一次（成本约 2 分钟），使“硬编码 3 得 1”有本地原件。
2. **仅当考虑训练用途时**：在沙盒试跑 §3.3 的三条断言。gold 跑 ×2、noop 跑 1 次，K1、K2、K3、K4、H 各跑 1 次。确认两件事：gold 和 K1 通过、Python 层 stderr 为空；H、K3、K2 被区分出来。结果交用户作 T0 决定。
3. **actor**：用真实模型求解一次，观察它是否落入 K2（照 docstring 改）或 K4（照 `cli.rst` 用 print 报告）。
4. **诊断探针期间**：每个 reward=1 的补丁都附跑 pr1 五例和 pr4，结果单列，不改原始 reward。

## 附录：本步实际读取范围

- **`OUTPUT_DIR`**：`public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`，均为全文。自己的 `reviewer_initial.md` 只作对照，没有修改。
- **历史**：`v3/history/…/refs.json` 列出的这些文件：
  - `findings.md`、`screening_record.json`、复现脚本，均为全文；
  - `known_issues.json` 中的两个族；
  - `decisions.md`、`results_20260924.md`、`packages/p2/README.md` 中本题相关的行（grep）。

  另外，为核对主审的引用，打开了三份原始证据：`agent_probe.log` L140-152、M3 `pkgsrc.txt`、M3 `git_scrub/out_after.txt`（grep）。`facts.json` 没有读。
- **新执行证据**：
  - `runs/r2e_actor_20260925/grader/` 下的 `ledger_d19f5_{gold,K1,K2,K3,K4}.jsonl`、对应的 `stdout_d19f5_*.log`、`b2_chain_d19f5.sh`；
  - `eval_logs/` 下对应的 5 份日志（sha256 与账本一致）；
  - `private_public_b2/d19f5_{K1,K2,K3}.json`；
  - `grader_cands/datalad_19f5_*.patch`，共 5 份。
- **公开包（补读）**：本题 `docs/source/design/cli.rst` L50-80、`datalad/cli/common_args.py` L88-102、`datalad/core/local/run.py` L205-215、`docs/source/design/result_records.rst` L74-90、`datalad/core/local/tests/test_run.py` L100-112 与 L146-160、`datalad/local/tests/test_rerun.py` L333-349、`datalad/cli/main.py` L222-224。同仓其它 datalad 题只读了公开包：CHANGELOG 顶部、`cli/main.py` 的哈希、58ba 的 `interface/base.py` L187/L192。
- **没有读**：本批 README、`assignments.json`、`grader_candidates.md`、首批审查目录、Codex 复核目录、其它题的私有包。
