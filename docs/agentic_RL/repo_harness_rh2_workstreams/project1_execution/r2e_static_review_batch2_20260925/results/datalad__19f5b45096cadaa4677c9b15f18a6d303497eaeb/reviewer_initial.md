# datalad__19f5b450 独立复核：第一步初判（读主审产物前）

复核者：Claude（R2E 独立复核角色，干净上下文），2026-09-25。只做静态阅读和已有证据核对，没有运行代码或容器，也没有改原件。证据级别写成：**静态推断**；**current 评分运行**（`run_refs.json` 中 `material=current` 的账本行和日志）；**devcheck 实测**（真实 Claude Code，agent 身份，镜像层面）；**私有对照**（root、不联网、应用 gold 后执行同一批公开命令）。

## 0. 结论先行

- **题目目标**：命令行 `datalad run` 执行的命令以非零码失败时，`datalad` 本身应以同一个退出码退出（题面例子：`exit 3` → 3），而不是统一退 1。
- **初判**：题面、base、隐藏测试、gold 和运行证据相互对应。初态故障在 base 上成立，并且 noop 日志里的失败原因就是题面描述的 `1 != 3`。gold 修到了题面原例，也保住了“没有退出码的失败仍退 1”。**没有发现合理修复被误拒。主要问题是评分偏宽松（漏测）**：唯一目标键 `test_run_exit_code` 只测“一个 run 失败、退出码 3、Python 层 stderr 为空”；另外 18 个键都是 base 公开测试原样搬过来的，没有一个会走进本次改动所在的 `IncompleteResultsError` 分支。按静态推断，硬编码 3、不设默认值地取第一个失败结果的 `exit_code`、把 `run` 改回抛 `CommandError`，这三种错误或带回归的实现都会得 1（§4 C2–C4）。
- **暂定处置**：可列为 development_diagnostic 或基座探针的静态候选。条件是：对通过的补丁另查 C2–C4 这类问题，不能把 reward=1 当成“没有回归”。如果用于训练，题面给出的数值 3 恰好就是唯一断言的值，存在硬编码投机的空间。是否加强测试（§5）属于改变测试标准，要先实跑确认，再由用户决定。
- **唯一最值得先做的下一步**：用正式评分代码实跑 §4 的 C2（硬编码 3）和 C4（`run` 改回抛 `CommandError`），预期两者都得 1。这样能把“宽松”从静态推断坐实为执行证据。

## 1. 八方面：已查与未查

| 方面 | 已查（要点与定位） | 未查或未知 |
| --- | --- | --- |
| 公开需求 | `user_prompt.txt` L1–27；`public_bundle.json` 的 `public_hints`；`environment_brief.md`；base 源码中的公开线索：`datalad/cli/main.py` L184–235、`datalad/core/local/run.py` 文档串 L105–109 与 L1061–1082、`datalad/interface/results.py` L123–135、`CHANGELOG.md` L1134/L1157/L1191；公开 `datalad/cli/tests/test_main.py` 的 `run_main` | 模型实际收到的完整消息：devcheck 发给模型的是桩提示 “Devcheck run: …”，不是任务提示。容器内 `/rh2/public_task_bundle.json` 的内容也没看到 |
| 材料与初始问题 | 哈希全对上：隐藏测试 3 个文件与 grading bundle 一致；期望映射 `42b8016a…`；gold 与 validation bundle 及账本 `patch_sha256 adfb3a3b…` 一致；日志 `RH2_SETUP_HIDDEN_TESTS_TREE=2e5d11bf…` 与 current 一致。revisions 为空；manifest 的 initial_diff 为 0 字节；题面 commit 与 base `b07ea09c` 一致。初态故障路径逐段读过（§附录 A）。noop 执行证据见 §2(b) | — |
| 测试是否测到要求 | 隐藏 `test_1.py` 与 base 公开 `test_main.py` 做过 diff：只新增 `test_run_exit_code`（L214–223），另把两行相对导入改成绝对导入。目标键的决定性断言在 `run_main` L80/L82/L83/L86–87。覆盖情况见 §3 映射表 | — |
| 误拒 | 期望映射 19 键全是 PASSED。核过 5 条实现路线（§3）与 stderr 的捕获机制 | 没有实跑替代解，结论是静态推断加 gold / 私有对照 |
| 回归与 gold | 与改动相邻的回归键逐个追过调用路径；逐个确认其余隐藏用例都不会进入 `IncompleteResultsError` 分支；gold 在私有对照 5 个场景下的行为；未打分的公开回归测试（`test_rerun.py::test_run_failure`，以及 `test_run.py` 中的 `assert_raises(IncompleteResultsError)`） | `test_run.py` 里那几处 `IncompleteResultsError` 断言只读了定位行（L406/L632/L651/L667），测试体没有逐个读 |
| 开发条件 | devcheck：预检、环境、公开命令 pr1–pr5（agent，真实 CC 2.1.205 + 桩端点）；私有 gold 对照（完整输出版）；`datalad/conftest.py`；`tox.ini` | 真实模型求解；经 Qwen adapter 的链路；devcheck 镜像 ID 与 current 评分镜像 ID 不同（§1 末） |
| 交付与评分边界 | 账本 projection 的 `included_paths=["datalad/cli/main.py"]`；其它可修位置都是非测试源码；`datalad/cmdline/main.py` 只是弃用 shim（L9–20）；测试支撑可被候选修改；工作树中可见的 `run_tests.sh` | 平台层的投影和清理机制没有复查，只核了适用性 |
| 题目关系与用途 | 两份跨题扫描；自己在 5 个 datalad 公开工作树中 grep `non0_codes`、`fish for an exit code`、`test_run_exit_code`、`issues/7504`；读了 `datalad__58ba5165` 的公开题面 | 其它题的私有包没有读（按规定） |

镜像身份（证据缺口）：current 评分运行用派生镜像 `sha256:19535845…`（R-f 机，09-23）；devcheck 和私有对照用 `sha256:851a10b6…`（09-25，`/work/b_r2e/derived9`）。两者配方同为 `r2e_derive_v1`，来源镜像 digest 同为 `b225824c…`，但 ID 不同。隐藏测试在 `851a10b6…` 上跑 gold / noop 的结果不在我拿到的材料里。所以解题侧只能写“镜像层面实测”，求解本身仍是“actor 待验”。

## 2. R2E 专项

- **(a) 非 PASSED 期望键**：没有，19 键全是 PASSED，不存在“更完整的修复把应失败的键翻成 PASSED”的风险。`test_help_np` 在 current 两次和 M3 两次运行中都是 SKIPPED，不成键。但它在跳过点（L161–163）之前的帮助输出断言仍会执行：候选如果破坏了 `--help-np` 输出，会多出一个 FAILED 键而判 0。这是期望映射之外的一层回归保护。
- **(b) 题面报错是否出现在 noop 目标键里**：出现了。两次 current noop 日志（R-f `evallog_…noop-d_89096c54.eval.log` L25–50、L165；环境轮复跑 `…rer_573a33ad.eval.log`，与前者 diff 只差临时目录名和耗时）唯一的失败都是 `test_run_exit_code`，原因是 `first = 1, second = 3` / `assert 1 == 3`，来自 `run_main` L83，与题面“退 1 而非 3”一致。devcheck 用 agent 身份在 base 上也复现了：pr1 `EXIT 1`、pr2 在 `test_main.py:83` 抛 `AssertionError`、pr5 真实 console script `exit=1`。
- **(c) 题面是否泄漏修法**：没有泄漏实现位置（没提 `main.py`、`IncompleteResultsError`、`failed`、`exit_code`）。但题面例子就是隐藏测试里那一行调用（`run_main(['run', '--explicit', 'exit 3'], exit_code=3)`）。它和“只断言数值 3”叠在一起，就形成了硬编码投机面（C2）。修法所需的信息可以从公开材料合理找到：CHANGELOG L1191 写明退出码不再转发是 0.16.0 #6447 的副作用，并指出原 `CommandError` 可从 `IncompleteResultsError.failed` 的结果记录取得；`run.py` L1074–1076 的注释也说明了 `exit_code` 键的来历。
- **(d) 测试支撑、搬迁伪影、撞键**：
  - 只有一个隐藏测试文件，20 个函数名互不相同，不会撞键。
  - 决定性的比较走的是 base 版 `datalad/tests/utils_pytest.py::assert_equal`（L80）。评分时不重置这个文件，候选改它就能操纵结果。这是 R2E 通病，公开提示禁止改测试文件，账本里有 `candidate_test_like_paths` 诊断字段。
  - R2E 自加的 `conftest.py` 用临时 HOME 加 git 身份，替代了包级 `datalad/conftest.py`。包级 conftest 还有一个 `capture_logs` fixture，会把 datalad 日志压到 100 级（L229–238）。所以评分时日志是 INFO 级、可以看到，而解题者跑公开测试时日志是静默的。这不影响目标键的判定，理由见 §3。
  - `tox.ini` L69–71 的 `error::DeprecationWarning:^datalad` 在评分时同样生效（日志显示 `configfile: tox.ini`）。候选如果导入弃用 shim `datalad.cmdline.*`，会在测试里变成错误。合理修复不会这样做。
- **(e) 时间、随机、资源敏感键**：`test_help_np` 是否跳过，取决于 fd 0 上的 `ioctl(TIOCGWINSZ)`（`datalad/ui/utils.py` L41–51）。评分如果分配 TTY，它会变成 PASSED/FAILED 新键，所有候选（包括 gold）都判 0。当前评分条件下 6/6 次稳定 SKIPPED。`test_completion` 依赖 argcomplete，`test_script_shims` 依赖评分用户 PATH 上的 console script，环境固定，结果稳定。没有发现时间或随机依赖。评分侧内存峰值 751–813 MB，测试耗时 11–12 s。
- **(f) 修订**：没有（`revisions.json` 为 `[]`），不适用。

## 3. 核心映射（需求 → 断言）与误拒分析

| 需求或旧行为 | 公开依据 | 测试与决定性断言 | 覆盖 | 执行证据 |
| --- | --- | --- | --- | --- |
| `run --explicit 'exit 3'` 应退 3 | 题面例子与 Expected | `test_run_exit_code` → `run_main` L83 `cm.value.code == 3` | 覆盖，但只有这一个值 | noop FAILED（1≠3）；current gold PASSED ×2；私有对照 pr2 通过 |
| 其它非零码也应原样转发 | 题面“same … (e.g., 3)” | 无 | 缺失（C2 可过） | 无 |
| 非 `--explicit` 的 run 同样应转发 | 题面泛指 `datalad run` | 无 | 缺失 | devcheck pr1 第 2 例：base 退 1；私有对照 gold 退 3 |
| 没有 exit_code 的失败仍非零退出（旧行为 1） | `main.py` L200–201 注释；CHANGELOG L1191 “continues to exit with a non-zero exit code” | 无：其余 18 个键都不进该分支（逐个核过：`configuration get` 未设键时返回 ok，见 `configuration.py` L337–340、L371–382；其它键是 argparse、早退或成功路径） | 缺失（C3 可过） | 私有对照 pr1 第 4 例（输入缺失）gold 退 1 |
| `run` 的 Python API 语义（失败抛 `IncompleteResultsError`、写 COMMIT_EDITMSG、on_failure 可配置） | CHANGELOG L1191；公开 `test_rerun.py` L300–320 | 不在隐藏测试中 | 缺失（C4 可过） | devcheck pr4 base 通过；私有对照 gold 通过 |
| 不在 Python 层 stderr 上加输出 | 题面例子用 `run_main` 默认的 `expect_stderr=False`；`main.py` L208–210 “do not want to see the error again”；隐藏测试里 `expect_stderr=True` 被注释掉 | `run_main` L86–87 `stderr == ""` | 有依据的隐含约束 | gold 日志里 INFO 行出现在 pytest 捕获中，而测试通过 |
| InsufficientArgumentsError → 2 等旧退出码 | base 公开测试 | `test_usage_on_insufficient_args`、`test_incorrect_option`、`test_combined_short_option`、`test_incorrect_cfg_override`（最后一个走 `helpers.py` L266–271 早退 3） | 覆盖，但与本次修改的分支无关 | noop / gold 均 PASSED |

**误拒**：没有发现。
- 核过的合理路线有：gold 做法（从 `exc.failed[*]['exit_code']` 取）；从结果的 `exception` 取（`run.py` L1077 传入的是原始 `CommandError`，`.code == 3`）；在 `eval_results` 里给异常附带退出码、再由 `main.py` 读取；取最后一个或最大的非零码。在单失败场景下，这些路线都得到 3。
- 这些路线的附加输出都不会进入 `run_main` 替换的 `sys.stderr`：
  - logging：处理器持有的流不是被替换的对象。gold 日志里 `[INFO] == Command start` 出现在 pytest 捕获中，而测试通过，这就是证据。
  - `ui.error`：`ConsoleLog.error` 写的是 `self.out`，见 `dialog.py` L93–94、L78；`run_main` 已把 `out` 换成 stdout 替身。
  - `_communicate_commanderror`：走的是 `os.write(2, …)`，见 `main.py` L228。
- 会被判 0 的只有一类：用 `print(…, file=sys.stderr)` 或 `sys.stderr.write` 加提示。这有公开依据（见上表最后一行的前一行），应归为“遵循冲突示例的候选”，不算合理修复被误拒。这一点是静态推断，没有实跑。
- 题面没有定义的语义（多个失败取哪个码、`--on-failure ignore` 退几）都不在评分范围内。gold 在 ignore 下退 0，见私有对照 pr1 第 5 例，这符合 ignore 的原意。

**gold 检查**：
- gold 只改 `main.py` 一个分支，题面原例修到了，没有依赖未交付的改动（`exit_code` 键在 base 已存在：`results.py` L132–133、`run.py` L1074–1076）。
- 私有对照（root、不联网）的结果：`--explicit exit 3` 退 3，非 explicit `exit 3` 退 3，`exit 0` 退 0，输入缺失退 1，`--on-failure ignore` 退 0；公开回归子集 pr3/pr4 全过；真实 console script 退 3。
- 两个小瑕疵，都不影响评分：
  - `run` 文档串 L105–109 仍写“会抛 CommandError”，gold 没有更新。
  - `exc.failed` 为 `None` 时 gold 会抛 TypeError。但另一个抛出点 `AnnexRepo.copy_to`（`annexrepo.py` L3087，`failed` 是文件名字符串列表）已弃用，也没有非测试调用者，命令行路径走不到。

## 4. 可区分候选（可直接改成补丁；请协调者用正式评分实跑）

以下预期得分都是**静态推断**。“附加检查”复用 devcheck pr1 的进程内脚本（或 pr5 的 console script），用来显示实现错在哪里。

| ID | 改哪里、怎么改 | 预期隐藏得分 | 附加检查与预期 | 用来区分什么 |
| --- | --- | --- | --- | --- |
| C1 合理替代 | `datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支（L207–210）加：`for r in (exc.failed or []):` 中取 `e = r.get('exception') if isinstance(r, dict) else None`，若 `isinstance(e, CommandError) and e.code` 则 `exit_code = e.code; break` | 1（19/19，无失配键） | pr1 五例依次应为 3/3/0/1/0，与 gold 相同 | 走 exception 路线的合理解不被误拒 |
| C2 硬编码 | 同一分支只加一行 `exit_code = 3` | 1（19/19） | pr1 第 4 例（输入缺失）应退 1、实际退 3；任意 `run 'exit 5'` 都退 3 | 目标键只锁定题面给出的数值，漏测 |
| C3 不设默认值 | 同一分支加 `exit_code = exc.failed[0].get('exit_code')`（没有 `or exit_code` 回退） | 1（19/19） | pr1 第 4 例：输入缺失的结果没有 `exit_code` 键（`run.py` L493–496 用 `get_status_dict` 构造，不带异常），所以得到 `sys.exit(None)`，打印 `EXIT None`，真实进程状态为 0，失败被报成成功。若写成 `exc.failed[0]['exit_code']`，则变成处理器内 KeyError 回溯 | “没有 exit_code 的失败仍非零退出”这一旧行为没有保护 |
| C4 改回抛异常 | `datalad/core/local/run.py::run_command` 在 L1014–1015（`cmd_exitcode, exc = _execute_command(...)`）之后加 `if exc is not None and not rerun_info: raise exc` | 1（19/19）。命令行改走 `CommandError` 分支，`_communicate_commanderror` 用 `os.write(2, …)` 输出，不进 stderr 替身，返回 3 | `python -m pytest datalad/local/tests/test_rerun.py -k test_run_failure` 应失败：L314–315 期望 `IncompleteResultsError`，L319–320 期望 COMMIT_EDITMSG，而后者要到 L1052–1059 才写 | 修复位置不同、导致 Python API 回归，不被评分覆盖 |

可选但不必跑：C5 在同一分支加 `print(f"command exited with {code}", file=sys.stderr)`，预期得 0，失配键是 `test_run_exit_code`（L86–87）。它只用来确认隐含的 stderr 约束，本身属于遵循冲突示例。

## 5. 发现汇总

1. **漏测：目标值单一（中）**。唯一断言值 3 就是题面给出的值（C2）。证据：静态推断加隐藏测试 L221。
2. **漏测：旧行为没有保护（中低）**。隐藏测试中没有任何用例进入 `IncompleteResultsError` 分支的“无退出码”情形（C3）。证据：静态推断加私有对照中 gold 的正确行为。
3. **漏测：修复位置和 API 回归（中）**。`run` 的 Python API 语义只由未打分的公开测试保护（C4）。证据：静态推断。
4. **题面例子的导入全错（低，属于生成题面的伪影）**：
   - `run_main` 不在 `datalad.api`，它是公开 `test_main.py` L53 的测试 helper；
   - `create` 不在 `datalad.utils`，应为 `datalad.api.create`；
   - `chpwd` 在 `datalad.utils` L1743，不在 `datalad.support.gitrepo`。

   不影响对行为的理解；devcheck pr2 证明从 `datalad.cli.tests.test_main` 导入 `run_main` 后可以复现。
5. **隐含的 stderr 约束（低）**：有公开依据，见 §3。
6. **环境敏感的 SKIPPED 测试 `test_help_np`（低）**：当前条件下稳定。
7. **没有发现**：误拒、错误的回归期望、材料错配。

**可选的修订建议（改变的是测试标准，需要用户决定；先做 §4 实跑）**：在隐藏测试里加两项。
- 同一场景换一个码，例如 `exit 5` 应退 5。依据是题面“same … (e.g., 3)”。
- 一个没有退出码的失败，例如 `run --explicit -i does-not-exist 'exit 3'` 应退 1，建议用 `expect_stderr=True`。依据是旧行为：CHANGELOG L1191 与 `main.py` L200–201。

gold 按私有对照和推断能通过这两项，C2、C3 会被判 0。这两项没有扩大原需求。

## 6. 开发需求（解题侧）

均为**镜像层面实测**（devcheck，agent uid 54321）：
- 预检三项 ok。
- `python` 指向 `/testbed/.venv/bin/python`；从 `/` 导入 `datalad` 也指向 `/testbed/datalad`。
- 没有 pip，本题也不需要。pytest 8.3.4、git 2.34.1、git-annex 都在 PATH 上。
- `datalad` console script 在 `.venv/bin`，反映 `/testbed` 源码：私有对照中应用 gold 后，pr5 得到 `exit=3`。
- 激活文件对 agent 不可写。初态 `git status` 只有 `?? install.sh`、`?? run_tests.sh`。
- agent 的 HOME 里没有 git 身份。临时脚本里的 `create` 需要带 `GIT_AUTHOR_*`/`GIT_COMMITTER_*` 环境变量（pr1、pr2、pr5 都这样做，可用）。跑仓库自带测试时，由 `datalad/conftest.py` L28 的 session fixture 建临时 HOME，pr3、pr4 以 agent 身份通过。
- 不需要网络。

**actor 待验**：真实模型求解、模型实际收到的消息，以及隐藏测试在 devcheck 镜像 `851a10b6…` 上的 gold/noop 结果。

## 7. 题目关系

- 本题的 gold 和新增测试不在同仓其它 4 题的公开工作树里：扫描中没有 task=本题 的配对；自己 grep 也核实了。
- 反方向：`datalad__58ba5165` 的 gold（6/6 行）已经包含在本题 base 里。那是 58ba5165 的暴露问题（它的主题是文档标记里括号的解析，与本题无关），不影响本题。
- 另外 3 个 datalad 题（16c1ffc3、6b6fa389、9ba5de09）是 0.16 之前的布局，只有 `datalad/cmdline/main.py`。那时 `run` 仍抛 `CommandError`，退出码会被转发。这属于公开历史，不是本题答案。
- 任务类型：命令行异常处理的小修（单个分支）。题面给了测试调用，但没给修法。
- 外部答案线索：上游修复 PR 的 changelog 被 gold 排除，名为 `pr-7641.md`，见 M3 账本的 `gold_meta`。actor 不联网；预训练是否记住了答案无法静态判断。

## 附录 A：初态故障路径（静态推断，已由 noop 执行印证）

1. `run.py` L1061–1082：命令非零退出时产出 `status='error'` 的结果，带 `exit_code=cmd_exitcode` 和 `exception=exc`（原始 `CommandError`）。`get_status_dict` 还会为 `CommandError` 自动写入 `exit_code`（`results.py` L132–133）。
2. `interface/utils.py` L390–392：`on_failure` 为 continue 或 stop 时，把 error 结果收进 `incomplete_results`；run 的默认值是 stop（CHANGELOG L1157）。
3. `interface/base.py` L939–942：抛出 `IncompleteResultsError(failed=incomplete_results)`。
4. `cli/exec.py`：`call_from_parser` 只做 `list(ret)`，不转换异常。
5. `cli/main.py` L201、L207–210：`IncompleteResultsError` 分支不改 `exit_code=1`，最后 `sys.exit(1)`。

## 附录 B：实际读取范围

- 方法：复核卡全文；主审卡中“R2E 的评分口径”“材料”“第二批补充规则”三节（因为在同一文件里，其余几节也在视野内，但没有作为口径使用）；八方面协议；R2E 第二批环境卡；记录模板。
- 公开包（本题）：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（摘要字段）。`worktree/` 中读过：`datalad/cli/main.py`、`datalad/cli/exec.py`（`call_from_parser` 片段）、`datalad/cli/helpers.py` L245–275、`datalad/cli/tests/test_main.py`（与隐藏测试做 diff）、`datalad/cmdline/main.py`、`datalad/support/exceptions.py` L499–526、`datalad/runner/exception.py` L1–118、`datalad/interface/base.py` L820–959 与 grep、`datalad/interface/utils.py` L293–420、`datalad/interface/results.py` L61–136、`datalad/core/local/run.py` L95–125、L483–503、L680–712、L1000–1113 与 grep、`datalad/local/configuration.py` L295–345、L371–382、`datalad/ui/utils.py` L17–68、`datalad/ui/dialog.py` L60–100、`datalad/support/annexrepo.py` L3060–3090、`datalad/local/tests/test_rerun.py` L300–345、`datalad/core/local/tests/test_run.py`（仅 grep）、`datalad/conftest.py`（grep 加 L226–260）、`tox.ini` 的 `[pytest]` 段、`CHANGELOG.md`（grep 加 L1180–1195）、`changelog.d/`、`run_tests.sh`。
- 私有包（本题）：`hidden_tests/`（全部 3 个文件）、`expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`、`run_refs.json`。
- 运行原件（只读 `run_refs.json` 列出的项）：`runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl` 第 12 行，及两份对应的 eval log；`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` 第 12 行，及两份对应的 eval log（逐字节哈希与 `run_refs.json` 一致）；`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 5、54 行，及 a1/a2 的 `test_output.txt`。
- devcheck：`runs/r2e_actor_20260925/devcheck/datalad__19f5b45096cadaa4677c9b15f18a6d3/` 下的 `orig/`（commands、attempt、activation、prelaunch、post_run_facts、全部 captures、devcheck_stdout、CC 版本、`stub/requests/messages_000.json` 的消息部分），以及 `private_gold/` 与 `private_gold_full/`。
- 跨题比对：`cross_task_gold_scan.json` 与 `cross_task_test_scan.json`（方法说明和涉及本题的配对）。同仓其它 datalad 题**只读了公开包**：各题 `public_bundle.json` 的 base_commit、在 worktree 里 grep，以及 `datalad__58ba5165` 的 `user_prompt.txt`。
- **没有读**：`OUTPUT_DIR` 里的其它文件、任何 `history/`、`docs/.../r2e_env_repair_20260924/`、首批审查目录、Codex 复核目录、其它 `*review*` 目录、本批 README、`assignments.json`、`grader_candidates.md`、`runs/` 下的分析或汇总文件、其它题的私有包、账本中其它题的行、diagnostics.json（本地没有）。
