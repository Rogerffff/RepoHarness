<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb：私有主审分析（读历史前）

2026-09-25 · 私有主审（静态）。只做静态阅读和已有证据核对：没有运行项目代码，没有开容器或远端，没有修改任何原件。本文件在读取任何历史调查之前保存。

路径缩写（均相对仓库根）：
- `PUB`：`runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/`
- `PRIV`：`runs/r2e_static_prep_20260924/v3/private/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/`
- `DEV`：`runs/r2e_actor_20260925/devcheck/datalad__19f5b45096cadaa4677c9b15f18a6d3/`
- 隐藏测试行号指 `PRIV/hidden_tests/test_1.py`；源码行号指 `PUB/worktree/`。

证据级别用语：**评分实跑**（RH2 正式 grader，当前材料）；**解题侧实测**（devcheck：正式启动路径、真实 Claude Code 2.1.205 加桩端点、agent 身份）；**私有 gold 对照**（同一派生镜像的一次性容器，root，不联网）；**独立参考**（M3 runner，来源镜像）；**源码推断**（未执行）。

## 0. 结论先行

- **题目**：从 CLI 调用 `datalad run` 时，如果被执行的命令以非零码 N 退出，datalad 进程应以 N 退出；base 统一退出 1。gold 只改 `datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支：在 `exc.failed` 中找带 `exit_code` 的失败记录，取第一个非零码作为退出码。
- **暂定处置**：`needs_review`，原因是"静态候选待 actor 验证"，另附"测试偏窄"。
  - 适合做开发诊断或基座探针候选，依据有三点：题意可由公开材料恢复；noop 与 gold 只在目标键上不同，4 次评分运行结果稳定；agent 身份下的开发条件和公开验证命令已实测可用。
  - 但隐藏测试只有一个目标键，就是题面原例。按源码推断，以下两类候选都会得 1：K2 按 `Run` docstring 恢复抛 `CommandError`，属于破坏 Python API 的回归实现；K3 取首条失败记录的 `exit_code` 且不回退，属于部分实现，硬编码 3 也属此类。因此 reward=1 不能证明以下四点：任意 N 都被转发、非命令失败仍退 1、`--on-failure ignore` 退 0、Python API 不变。
  - 没有发现合理解被误拒的具体证据。唯一的精确约束是 Python 层 `sys.stderr` 必须为空，而这一点有公开依据：题面示例用的 `run_main` 默认 `expect_stderr=False`。
- **唯一最值得先做的下一步**：用正式评分代码实跑 K2 和 K3，两者预期都得 1，用来确认漏测。同批顺带实跑 K1（预期 1）和 K4（预期 0），确定 stderr 约束的实际边界。候选描述见 §6。

## 1. 实际读取范围

- **方法**：读了角色卡与四份方法文档，包括八方面协议、R2E 第二批环境卡、记录模板和 40 项清单。
- **公开材料**：
  - `public_read.md` 全文；`PUB` 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md` 全文；`worktree_manifest.json` 只看了键与摘要。
  - worktree 中读过的源码：
    - `datalad/cli/`：`main.py` 全文；`exec.py` 的 `call_from_parser`；`common_args.py:88-102`；`helpers.py:255-275`。
    - `datalad/core/local/run.py`：docstring、`on_failure`、`custom_result_renderer`、`run_command` 的失败分支、`_execute_command`、结果记录 990-1120。
    - `datalad/interface/`：`results.py` 的 `get_status_dict`；`utils.py:229-258, 330-420`；`base.py` 中 `eval_results` 的结构及 880-945。
    - 其它模块：`datalad/support/exceptions.py:499-526`、`datalad/support/annexrepo.py:3060-3090`、`datalad/runner/exception.py`、`datalad/ui/dialog.py:60-95`、`datalad/ui/utils.py:17-68`。
  - worktree 中读过的测试与配置：
    - `datalad/cli/tests/test_main.py`，已与隐藏测试做 diff；
    - `datalad/core/local/tests/test_run.py` 的 95-175、398-410、622-672 行；
    - `datalad/local/tests/test_rerun.py` 的 280-350 行；
    - `tox.ini` 的 `[pytest]` 小节，`datalad/conftest.py:80-140`。
  - worktree 中读过的文档：`CHANGELOG.md` 的 1-12 与 1185-1195 行、`docs/source/design/cli.rst:50-80`、`changelog.d/`。
- **私有材料**：读了 `PRIV` 下全部文件，包括 `hidden_tests/{__init__,conftest,test_1}.py`、`expected_output.json`、`gold.patch`、`run_tests.sh`、`grading_bundle.json`、`validation_bundle.json`、`revisions.json`、`run_refs.json`。其中 `test_1.py`、`conftest.py`、gold 与 expected 的 sha256 都与 bundle 行及账本一致。
- **运行原件**：
  - run_refs 列出的 4 行账本（均为第 12 行）和 4 份 `.eval.log`；
  - M3 账本第 5 行及 a1/a2 两份 `test_output.txt`；
  - `DEV/orig/` 与 `DEV/private_gold/` 下的全部文件；桩请求只看了第一份。
- **跨题材料**：读了 `runs/r2e_static_prep_20260924/cross_task_gold_scan.json`。同仓另外 4 题的公开包只读了 `user_prompt.txt` 标题、`public_bundle.json` 的 base 以及 `CHANGELOG.md` 开头；58ba5165 的公开 worktree 还读了 `datalad/cli/main.py` 的哈希和 `datalad/interface/base.py` 中的相关正则。
- **未读**：
  - 任何历史调查，包括 `history/`、`docs/.../r2e_env_repair_20260924/`、其它审查目录；
  - 本批 README 与 `assignments.json`；
  - `runs/` 下的分析与汇总文件；
  - 其它题的私有包；
  - `.venv` 与 `.git` 的内容。关于这两处，只有 devcheck 实测的事实。

## 2. 八方面覆盖

| 方面（清单编号） | 已查内容与证据 | 结论 | 未查 / 缺项 |
|---|---|---|---|
| 公开需求（3、23） | 题面；public_hints；`Run` docstring（run.py:105-106）；0.16.0 changelog（CHANGELOG.md:1191）；cli.rst:61-71；`--on-failure` 帮助文案（common_args.py:95-99） | 主要求明确（R1），向任意 N、非 `--explicit` 推广可以推知。公开文档互相矛盾：docstring 说失败时抛带相同退出码的 `CommandError`；0.16.0 changelog 说 Python API 改为抛 `IncompleteResultsError`、CLI 不再转发退出码；cli.rst 把"内部 shell 命令失败"列为转发退出码的一类。题面没有说明 Python API 是否要跟着改。示例三处导入写错，但意图可以恢复：devcheck 的 pr2 改正导入后能运行 | 模型实际收到的渲染消息未核。devcheck 的用户消息是桩脚本 "Devcheck run: …"，不是题面 |
| 材料与初始问题（1、2、27） | M3 账本第 5 行 `head_is_parent_of_fix=yes`；manifest 显示初态 diff 为 0 字节；各哈希一致；noop 目标键失败原因为 `assert 1 == 3`（评分实跑 ×2）；agent 身份下 base 复现 EXIT 1（解题侧实测 pr1/pr2/pr5） | 材料对应同一任务，初态确实包含题述问题 | — |
| 测试是否测到要求（18-20、25、32） | 20 个收集项全部读完（19 键 + 1 SKIPPED），逐项追到断言 | 唯一目标键只测题面原例：退出码 3、`--explicit`、默认 stop、no-annex。R2、R4、R6、R7 都没有键保护。硬编码 3 也能通过（源码推断） | K2/K3 未实跑 |
| 是否误拒合理解（24、28） | 目标断言只检查两件事：`SystemExit.code`，以及 run_main 所 patch 的 Python 层 `sys.stderr` 为空。不检查实现位置、结果记录、日志或 stdout | 修复放在哪一层、覆盖什么范围都不受限制。唯一精确约束是不能经 Python 层 `sys.stderr` 写字。以下三种输出方式不受影响：<br>- 日志：评分实跑可证，gold 日志里的 INFO 行进了 pytest 捕获，没有进 fakeerr，测试仍 PASSED；<br>- `ui.error`：它写 `ui.out`，run_main 把它 patch 到了 stdout；<br>- `os.write(2, …)`：绕过 Python 的 `sys.stderr` 对象。<br>该约束有公开依据 | K1/K4 未实跑 |
| 回归与 gold 完整性（26、27） | gold diff；`IncompleteResultsError` 的抛出点（interface/base.py:940，以及已弃用的 annexrepo.py:3087）；`exit_code` 字段来源（run.py:1076、results.py:132-133）；公开的 run/rerun 测试 | gold 修到原例。按源码推断，它不改 Python API、ignore 路径和非命令失败的退出码。它的范围比题面宽：任何带 `exit_code` 的失败记录都会被转发，这与 cli.rst 第 3 类一致，但没有测试。Python API 与 rerun 语义都不受隐藏测试保护 | gold 下 C1 五例与 console script 路径的退出码未观测（§9 第 2 条） |
| agent 开发条件（6-15） | devcheck `orig/`，详见 §7 | 解释器、导入、git、git-annex、console script、pytest 都可用；公开读者建议的 5 组命令都能在 agent 身份下运行 | 真实模型求解；经 Qwen adapter 的链路 |
| 交付与评分边界（4、16-17、21-22、29-31） | gold 账本 `projection.included_paths=["datalad/cli/main.py"]`；评分顺序（删掉 `r2e_tests` 后放入隐藏测试）；解析结果（收集 20 项，得 19 键加 1 个 skip）；git 清理（0 refs、0 remotes、0 reflog、HEAD 无子提交）；外部 DNS 为 DENIED | 修改非测试源码的合法修复可以交付。隐藏测试依赖 base 版 `datalad/tests/utils_pytest.py` 等测试辅助，评分时不重置；这是 R2E 的通用通道，不是本题特有。SKIPPED 键依赖 stdin 不是 TTY | `.venv` 未逐项检查。导入路径实测为 `/testbed`，答案经此泄漏的风险低 |
| 题目关系与用途（5、29-30、37-40） | 跨题机械比对，加同仓公开包核对 | 本题 gold 没有出现在同仓另外 4 题的公开工作树里。反向，58ba5165（文档标记方括号）的修复已经在本题初态中。题面不给修法，但示例就是目标测试本体。无材料修订 | 没有读 58ba5165 私有包 |

## 3. 需求—测试双向映射

### 3.1 公开要求 / 合理旧行为 → 键与断言

| 编号 | 要求或旧行为 | 公开依据 | 隐藏键 / 关键断言 | 覆盖 | 执行证据 / 待做 |
|---|---|---|---|---|---|
| R1 | 原例：`run --explicit 'exit 3'`，no-annex，默认 stop，应退出 3 | user_prompt.txt:15-18, 21-25 | `test_run_exit_code`：`run_main(['run','--explicit','exit 3'], exit_code=3)` → test_1.py:83 `assert_equal(cm.value.code, exit_code)` | 覆盖 | 评分实跑：noop 为 FAILED（`assert 1 == 3`，R-f 与 rerun2 各一次）；gold 为 PASSED（R-f、rerun2 各一次，M3 两次）。解题侧实测：base 下 EXIT 1。私有 gold 对照：pr2 输出 `run_main(exit_code=3) passed` |
| R1′ | 失败时不经 Python 层 stderr 输出 | 题面示例用 `run_main`，默认 `expect_stderr=False`（公开 test_main.py:53-98）；main.py:207-210 注释 "we do not want to see the error again" | 同一测试 test_1.py:86-87 `assert_equal(stderr, "")` | 覆盖（隐含约束） | gold 下为空（评分实跑）；K4 待跑 |
| R2 | 任意 N、不带 `--explicit` 时也转发 | user_prompt.txt:22；run.py:105-106；cli.rst:65-71 | 无，只测了 3 和 `--explicit` | 部分 | K3 与硬编码 3 预期都得 1（源码推断） |
| R3 | 命令成功时仍退出 0 | cli/main.py:171-172 | run 成功的情形没有用例；其它命令退 0 的路径由 `test_conflicting_short_option`、`test_librarymode`、`test_cfg_override` 覆盖 | 部分 | — |
| R4 | 非命令失败（输入缺失、数据集有未保存改动、占位符错误）仍退 1 | cli.rst:61-63；run.py:493-496 等处的失败记录没有 `exit_code` | 无：隐藏测试中没有任何用例触发 `IncompleteResultsError` | 缺失 | K3 预期得 1；base 下 C1 第 4 例为 EXIT 1（解题侧实测）；gold 下未观测 |
| R5 | 其它 CLI 退出码不变（2、1、3） | 公开 test_main.py | `test_usage_on_insufficient_args`（2）、`test_subcmd_usage_on_unknown_args`（1）、`test_combined_short_option`（2）、`test_incorrect_option`×4（2）、`test_incorrect_cfg_override`（3） | 覆盖 | noop 与 gold 下都 PASSED |
| R6 | Python API 不变：默认 stop 抛 `IncompleteResultsError`；ignore 返回 error 记录；失败不保存；rerun 退出码与记录一致时不报错 | test_run.py:103-109, 149-158；test_rerun.py:314-348；common_opts.py:354-362；CHANGELOG.md:1191 | 无 | 缺失 | K2 预期得 1；devcheck 的 pr4（3 个用例）在 base 与 gold 下都通过 |
| R7 | `--on-failure ignore` 时不产生非零退出码 | common_args.py:95-99 | 无 | 缺失 | base 下 EXIT 0（解题侧实测）；gold 按源码推断不变 |
| R8、R10 | continue 模式、多个失败、rerun、run-procedure、其它命令 | 公开材料未约定（多解） | 无 | 不适用 | gold 取第一个非零码，覆盖所有带 `exit_code` 的记录 |
| — | CLI 的 help、version、completion、script shims、配置覆盖、librarymode 旧行为 | 公开 test_main.py。它与隐藏文件只差两行导入写法，外加新增的目标测试 | 其余 13 个测试函数（含 script shims 的 3 个参数） | 覆盖（回归） | noop 与 gold 下都 PASSED |

### 3.2 关键断言 → 公开依据（反查）

- `cm.value.code == 3`：来自题面原例（明示）。
- `stderr == ""`：来自题面示例所用 `run_main` 的默认参数。这是隐含依据，需要找到公开的 `run_main` 并读它的签名；`grep run_main` 就能直接定位（public_read §3.4）。
- `create(dataset=tempdir, annex=False)`、`chpwd(tempdir)` 和 `--explicit`：都与题面示例相同。
- `eq_('cmdline', datalad.get_apimode())`：是 run_main 自带的检查，base 已满足。
- 另外 18 个回归键：对应公开 test_main.py 中的同名测试，agent 可以直接运行。
- **结论：没有只有读了隐藏材料才能知道的要求。**

### 3.3 回归键阅读范围

- **读了**：test_1.py 的全部 20 个测试体，以及隐藏 `conftest.py`。
- **没追**：argparse 帮助生成、argcomplete、`wtf`、`configuration`、`clean` 的内部实现。gold 不触及这些路径，这些键在 noop 与 gold 下 4 次运行都是 PASSED。
- **`test_help_np` 的特殊情况**：它在 skip 之前已经执行了节标题、全局选项和命令列表断言（test_1.py:133-159）。如果这些断言失败，会多出一个 FAILED 键并导致判 0，所以它实际上也起回归检查作用。

## 4. R2E 专项

**(a) 非 PASSED 键与翻转风险**
- 期望的 19 个键全是 PASSED，没有 FAILED 或 ERROR 键，因此不存在"更完整的修复让期望失败键变通过而被判 0"的风险。
- `test_help_np` 在评分环境中是 SKIPPED，不成键。原因是 stdin 不是终端：`get_terminal_size()` 用 `ioctl(0, TIOCGWINSZ)` 取尺寸，失败返回 None（ui/utils.py:40-51）。
- 如果评分改用 TTY 运行，所有候选（包括 gold）都会多出这个键，全部判 0。现有 6 份日志中它都一致为 SKIPPED，属于评分配置层面的已知敏感点。

**(b) noop 目标键的失败原因与题面是否一致**
- 失败位置是 test_1.py:83，`assert 1 == 3`（R-f noop 日志第 39-48 行；rerun2 的 noop 日志规范化时间戳和临时路径后逐行相同）。
- 这与题面 Actual Behavior（以 1 而非 3 退出）一致。
- 解题侧实测也复现了同一行为：pr1 第 10 行 `EXIT 1`；pr2 在 test_main.py:83 抛 AssertionError；pr5 输出 `exit=1`。

**(c) 题面是否泄漏修法**
- 没有泄漏：题面没有提到 `IncompleteResultsError`、`exit_code` 字段或 `cli/main.py`。
- 但示例几乎就是目标测试本体（同一命令、`--explicit`、`annex=False`、`exit_code=3`），暴露了测试形态。

**(d) 测试辅助、搬迁伪影与撞键**
- **依赖 base 版测试辅助**：隐藏测试用到 `datalad.tests.utils_pytest`（`assert_equal`、`assert_raises`、`with_tempfile`、`eq_` 等）、`datalad.cli.helpers.get_commands_from_groups`、`datalad.interface.base.get_interface_groups`、`datalad.ui.utils`。评分时不重置这些文件，候选如果改 `utils_pytest.py` 就能改变判定。这是 R2E 的通用通道；账本里的 `candidate_test_like_paths` 只是观测，不会阻止。
- **搬迁伪影**：
  - 相对导入改成了绝对导入。diff 只有这两行差异，外加新增的目标测试。
  - `datalad/conftest.py` 不作用于仓库根下的 `r2e_tests/`。改由隐藏 `conftest.py` 的 autouse 夹具临时替换 HOME 并写入 git 身份（conftest.py:12-21）。
  - `path` 夹具没有被任何测试使用：被装饰函数的参数带默认值，pytest 不会把它当作夹具。
- **撞键**：只有一个测试文件，不会跨文件撞键。
- **仍生效的配置**：`tox.ini` 中的 `error::DeprecationWarning:^datalad` 对隐藏测试同样生效（日志显示 `configfile: tox.ini`）。触发 datalad 自身弃用警告的候选会报错，但 `tox.ini` 是公开的，有公开依据。

**(e) 时间、随机与资源敏感性**
- 没有时间或随机敏感的键。
- 5 个键依赖外部 `datalad` 进程：3 个 `test_script_shims`、`test_cfg_override`、`test_completion`。它们需要 console script 和 argcomplete，在 6 次评分和参考运行中都一致通过。
- `test_version` 与 `test_script_shims` 比较 versioneer 生成的版本号。gold 下版本号是 `0+untagged.17263.gb07ea09.dirty`，进程内和子进程两边一致。
- TTY 依赖见 (a)。

**(f) 材料修订**：无（`revisions.json` 为 `[]`，`run_refs.current_material.material_revisions` 为空）。

## 5. gold 按公开要求检查

- **原例修到了**：评分实跑 4 次 PASSED，M3 参考 2 次 PASSED；私有 gold 对照的 pr2 输出 `run_main(exit_code=3) passed`。
- **逐条对照公开要求**（以下均为源码推断）：
  - R2：取失败记录里的 `exit_code`，所以任意 N 都会被转发。
  - R3：命令成功时不会抛异常，退出码不变。
  - R4：没有 `exit_code` 的记录被滤掉，退出码保持 1。
  - R5：只改了这一个分支，其它退出码不变。
  - R6：没有改 run.py。私有对照 pr4 的 3 个用例通过（rc=0）。
  - R7：ignore 模式不会抛 `IncompleteResultsError`，所以不受影响。
- **无关改动**：没有。
- **遗留**：
  - `Run` docstring（run.py:105-106）仍然说会抛 `CommandError`。gold 没有改它；上游的 `changelog.d/pr-7641.md` 在摄入时被排除（见 M3 账本的 `gold_meta.excluded`）。文档矛盾仍在，但不影响功能。
  - 范围比题面宽（R10），但与 cli.rst 一致。
- **未约定的边界**：命令被信号杀死时退出码为负数，`sys.exit(-9)` 的实际退出状态是 247，而 shell 惯例是 137。公开材料没有约定，不算缺陷。
- **健壮性**：
  - `eval_results` 抛出时总会传入一个列表作为 `failed`。
  - 唯一的另一个抛出点是 annexrepo.py:3087 的 `copy_to`。它已弃用，非测试代码中没有调用者；它传入的是字符串列表，`'exit_code' in r` 对字符串做的是子串判断，不会崩溃。

## 6. 区分候选（交协调者用正式评分代码实跑）

**K1（合理替代解，预期 1）**
- 位置：`datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支，在 `lgr.debug(...)` 之后加入：
  ```python
  for r in (exc.failed or []):
      e = r.get('exception')
      if r.get('action') == 'run' and isinstance(e, CommandError) and e.code:
          _communicate_commanderror(e)   # 经 os.write 写 fd 2，与直接抛 CommandError 时的输出一致
          exit_code = e.code
          break
  ```
- 与 gold 的差别：只处理 run 的记录；从 `exception` 字段取退出码，而不是 `exit_code` 字段；额外把命令错误说明写到 fd 2。
- 预期：19/19，`test_run_exit_code` 为 PASSED。
- 若得 0：说明存在未预料的过严约束，应按误拒调查。

**K2（遵循冲突文档的候选，预期隐藏测试得 1，但公开回归失败）**
- 位置：`datalad/core/local/run.py::_execute_command`（693-709 行）。
- 改法：删掉 `try/except CommandError`，让 `runner.run(command)` 抛出的 `CommandError` 直接向上传播，也就是按 docstring 第 105-106 行恢复 0.16 之前的行为。`cli/main.py` 不改。
- 预期隐藏测试结果：19/19。CLI 现有的 `CommandError` 分支会经 `_communicate_commanderror` 返回 3，错误说明经 `os.write(2)` 输出，不会进入 run_main patch 的 `sys.stderr`。
- 应当失败的公开测试：
  - `datalad/core/local/tests/test_run.py::test_basics`：103-109 行要求 ignore 模式返回 error 记录；149-158 行要求默认抛 `IncompleteResultsError`；
  - `datalad/local/tests/test_rerun.py::test_run_failure`：314-348 行，包括"rerun 的非零码与记录一致时不报错"。
- 区分意义：确认隐藏测试不保护 Python API（R6）和 rerun 语义。
- 变体：按示例把 `run_main` 加进 `datalad.api`，会让生产 API 依赖测试模块和 pytest，隐藏测试大概率仍然通过。结果受循环导入顺序影响，不确定，列为次要。

**K3（部分实现，预期隐藏测试得 1，违反 R4）**
- 位置：`datalad/cli/main.py::_run_with_exception_handler` 的 `IncompleteResultsError` 分支。
- 改法：只加一行 `exit_code = exc.failed[0].get('exit_code')`，不回退到 1。
- 预期隐藏测试结果：19/19。
- 公开行为上的错误：
  - `datalad run --explicit -i does-not-exist 'exit 3'`（public_read C1 第 4 例）的退出码由 1 变成 0，因为 `sys.exit(None)` 以 0 退出；
  - 所有没有 `exit_code` 的失败（例如 `get` 一个不存在的路径）都会以 0 退出，把失败报告成成功。
- 变体：
  - `exc.failed[0]['exit_code']` 在同类失败上会抛 KeyError，打印 traceback 后退 1；
  - 硬编码 `exit_code = 3` 也应得 1（源码推断：隐藏测试中没有其它用例触发 `IncompleteResultsError`）。
- 区分意义：确认隐藏测试不检查"非命令失败仍退 1"和"任意 N"。

**K4（行为正确，但写 Python 层 stderr，预期 0）**
- 位置：在 gold 的 `if non0_codes: exit_code = non0_codes[0]` 之后。
- 改法：加一行 `print(f"datalad: command exited with code {exit_code}", file=sys.stderr)`。
- 预期：`test_run_exit_code` 为 FAILED（test_1.py:86-87），18/19，判 0。
- 如果结果如预期，这属于有公开依据的隐含约束，不按"误拒合理解"计；但如果本题用于训练，应在说明中标为已知的严格点。

## 7. 开发需求（逐题）

| 项目 | 事实 | 证据级别 |
|---|---|---|
| 解释器与导入 | `python` 为 `/testbed/.venv/bin/python`（3.9.21），`VIRTUAL_ENV=/testbed/.venv`。datalad 从 `/testbed/datalad` 导入，在 `cwd=/` 下也是如此，说明是 editable 安装，不需要另加 `sys.path` | 解题侧实测（`DEV/orig/captures/env.out`、`activation_check.json`） |
| 依赖 | 只需纯 Python 修改，不需要新包。没有 pip；pytest 为 8.3.4 | 解题侧实测 |
| 资产与工具 | git 2.34.1；`/usr/bin/git-annex`；console script `/testbed/.venv/bin/datalad`；argcomplete 可用（评分侧 `test_completion` 通过） | 解题侧实测；argcomplete 为评分实跑 |
| git 身份 | HOME 中没有 user.name/email，env.out 有提示。单独运行脚本时要在命令里指定 `GIT_AUTHOR_*` 和 `GIT_COMMITTER_*`。公开 pytest 由 `datalad/conftest.py` 提供身份，pr3/pr4 通过 | 解题侧实测 |
| 权限 | agent uid 54321。`/testbed` 属主为 54321，可写；HOME（tmpfs，256 MiB）与 `/tmp`（1 GiB）可写；激活文件只读（DENIED） | 解题侧实测（`prelaunch.json`、env.out） |
| 网络 | 各阶段都不需要网络。解题侧外部 DNS 和直连都被拒，只能连到模型 relay；评分侧为 `deny_all` | 解题侧实测；评分账本 |
| 构建 | 不需要构建：editable 安装，改源码即生效。gold 账本记录 `RH2_OBS_IMPORT_PATH=/testbed/datalad/__init__.py` | 评分实跑；解题侧实测 |
| 资源 | 2 CPU、4 GiB、pids 上限 512。评分时内存峰值约 0.75-0.81 GB，测试耗时 11-12 s | 评分实跑；解题侧实测 |
| 公开验证路径 | public_read 的 C1-C5 都能在 agent 身份下运行。base 下的结果：<br>- C1（进程内 CLI，5 例）：依次为 1/1/0/1/0；<br>- C2（题面示例，改正导入后）：test_main.py:83 AssertionError；<br>- C3：7 passed；<br>- C4：2+1 passed；<br>- C5（console script）：`exit=1`。<br>gold 下 C2、C3、C4 已观测；C1 与 C5 的退出码因 tail 截断未观测 | 解题侧实测；私有 gold 对照 |
| 提交边界 | 修复放在非测试源码中（gold 改的是 `datalad/cli/main.py`），投影可以交付。不要改 `datalad/tests/utils_pytest.py` 或 `datalad/cli/tests/test_main.py`（public_hints 禁止；评分时也不会重置这些辅助文件） | 代码配置加账本 |
| actor 待验 | 真实模型求解；经 Qwen adapter 的链路；模型实际收到的渲染消息；在没有 git 身份的 HOME 下原样照题面示例调用 `create` 是否失败（未实测） | 未知 |

## 8. 题目关系（同仓跨题）

- **同仓 5 题的时代**：本题 base 在 1.1.3（2024-08）之后。58ba5165 在 0.17.9（2022-11）前后。另外三题（16c1ffc3、6b6fa389、9ba5de09）属于 0.4-0.5 时代（2016-2017），仓库里还没有 `datalad/cli/`，题目主题与退出码无关。
- **本题 gold 是否出现在其它题中**：机械比对没有命中。人工核对：58ba5165 公开工作树的 `datalad/cli/main.py` 与本题 base 哈希相同（sha256 前 12 位 `ce784b9dc740`），不含 gold 行；另外三题没有这个文件。
- **反向关系**：机械比对称 58ba5165 的 gold 新增行 6/6 都出现在本题公开工作树中。我在公开包里核对了对应正则：58ba5165 base 的 `datalad/interface/base.py:187,192` 用的是 `[^\[\]]*`，本题 base 的 `:218,223` 已经是修复后的 `.*?`。没有读 58ba5165 私有包，未逐行确认。影响：如果 58ba5165 留作评测，本题初态包含它的答案，划分数据时应把两题记为同族。
- **上游来源**：issue #7504（见测试注释）与 PR #7641（M3 `gold_meta` 排除的 `changelog.d/pr-7641.md`）。两者公开可检索，不能排除预训练污染（未知）。
- **任务类型**：小型 CLI 行为修复。需要沿"结果记录 → `IncompleteResultsError` → CLI 退出码"这条链定位。题面不给修法，但示例就是目标测试本体。

## 9. 缺口与未知

1. K1-K4 都没有实跑，只有源码推断。
2. 私有 gold 对照每条命令只保留 800 字符的 tail。pr1 的 `ARGS … EXIT` 行和 pr5 的 `exit=` 行都被截掉，因此 gold 下 C1 五例与 console script 路径的退出码没有观测到。
3. 镜像是同一配方的两次不同构建：
   - 当前材料的 4 次评分运行在派生镜像 `sha256:19535845…` 上；
   - devcheck 和私有 gold 对照在同配方 `r2e_derive_v1` 的另一次构建 `sha256:851a10b6…` 上。
   - 本批证据中，隐藏测试没有在后者上跑过。配方相同，风险低。
4. 模型实际收到的渲染题面没有捕获。
5. 没有逐项检查 `.venv` 与镜像其余文件是否存在答案通道，只依据导入路径和 git 清理这两项实测事实。
6. 与 58ba5165 的关系只依据机械比对和公开包一侧的正则核对。

## 10. 建议队列（由协调者安排）

1. **[CPU，优先]** 用正式评分代码实跑 K2 和 K3（预期都得 1，用于确认漏测）；同批跑 K1（预期 1）和 K4（预期 0）。
2. **[CPU，低成本]** 重跑私有 gold 对照中的 pr1 与 pr5，保留完整 stdout，确认 gold 下的结果依次为 3/3/0/1/0 以及 `exit=3`。
3. **[修订提案，需用户决定]** 仅在本题进入训练奖励时考虑，以公开要求为依据补隐藏断言：
   - 不带 `--explicit` 的其它退出码，例如 `exit 5` 应退出 5；
   - 输入缺失时退出 1；
   - `--on-failure ignore` 时退出 0；
   - Python API 默认仍抛 `IncompleteResultsError`，可以直接引用公开 test_run.py 中已有的用例。

   补测会改变期望映射，需要形成修订版，并用 gold 和 K1-K4 双向复验。如果只作诊断探针，可以不改；但对通过的补丁应附公开回归复核，包括 C1 五例和 test_run、test_rerun 中的相关用例。
4. **[actor 待验]** 用真实模型求解一次，观察两点：模型是否按 docstring 去改 Python API（K2 类），以及是否按示例去改 `datalad.api` 的导入。

## 附录 A：运行证据核对

| 角色 | 引用（账本行 / 日志） | 结果 |
|---|---|---|
| noop，R-f（当前材料） | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl` 第 12 行；`…/eval_logs_r2e/evallog_replay-r2e-rf-all-noop-d_89096c54.eval.log`（sha256 与 run_refs 一致） | 0.0，18/19，不匹配 `test_run_exit_code`；收集 20 项，1 failed、18 passed、1 skipped；测试 rc=1；镜像 `sha256:19535845…` |
| gold，R-f（当前材料） | 同目录 `ledger_r2e_all_gold.jsonl` 第 12 行；`evallog_replay-r2e-rf-all-gold-d_61fad0eb.eval.log` | 1.0，19/19；`RH2_OBS_PKG_VERSION=…gb07ea09.dirty`；只投影 `datalad/cli/main.py` |
| noop / gold，环境轮复跑 | `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` 第 12 行；`evallog_replay-r2e-envrepair-rer_{573a33ad,255516cc}.eval.log` | 0.0 / 1.0。与 R-f 对应日志规范化时间戳和临时路径后逐行相同 |
| gold，M3 独立参考（来源镜像） | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 5 行；`…/gold/a1`、`a2/test_output.txt` | 两次都是 19 passed、1 skipped。来源镜像中修复提交可达（`fix_reachable=commit`，HEAD 之后有 1026 个提交），派生镜像已清理 |
| 解题侧开发核对 | `DEV/orig/`（`attempt.json`、`prelaunch.json`、`captures/*.out`） | R2E 预检三项都是 ok。base 下结果：pr1 为 1/1/0/1/0；pr2 为 AssertionError；pr3 为 7 passed；pr4 为 2+1 passed；pr5 为 `exit=1`。镜像 `sha256:851a10b6…`（`r2e_derive_v1`） |
| 私有 gold 对照 | `DEV/private_gold/private_control.json` | gold 能干净应用。各命令 rc 都是 0；pr2 输出 `run_main(exit_code=3) passed`；pr3、pr4 通过。pr1 与 pr5 的退出码被 tail 截掉 |

## 附录 B：40 项清单预映射（稀疏，供 screening_record 使用）

- **pass**：1、2、4、6、7、8、9、10、11、13、17、18、19、20、21、22、27、29、30。
- **pass，但证据有限**：14（noop 和 gold 各 2 次评分运行，另有 M3 的 2 次，都一致）。
- **issue**：
  - 23：公开文档互相矛盾，示例导入写错；
  - 25、26、32：漏测，需 K2/K3 实跑确认；
  - 5：记录与 58ba5165 的同族关系，本身不是缺陷。
- **pass（静态）**：24。唯一精确约束有公开依据，K1/K4 待跑。
- **unknown**：
  - 3：实际渲染消息未捕获；
  - 31：通用的测试辅助篡改通道，本题没有特有入口；
  - 33-36：需要真实模型。
- **not_checked**：15。
- **not_applicable**：12、28、37-39（无材料修订）。
- **not_checked（流程层面）**：40。
