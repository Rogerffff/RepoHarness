<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5 私有主审：读历史前分析

- 角色：R2E 私有主审（第二批角色卡），2026-09-25，干净上下文；**尚未打开任何历史调查**。
- 暴露：读过 gold、隐藏测试、expected、运行日志与账本、devcheck 证据、同仓跨题比对；本稿不给解题模型。
- 证据级别用语：**执行证据**（已有运行原件）、**代码配置**（读 RH2 代码得出）、**静态推断**（读题目源码/测试推出，未执行）、**未知**。
- 路径约定：`W/` = `PUBLIC_DIR/worktree/`（即 `/testbed` 初态）；`H/` = `PRIVATE_DIR/hidden_tests/`；`DC/` = `runs/r2e_actor_20260925/devcheck/coveragepy__ea6906b092d9bb09285094eee94e/`。

## 0. 结论先行（暂定）

1. **题意**：生成 HTML 覆盖率报告时，在输出目录写一个 `.gitignore`，让 git 忽略该目录的全部内容。这是新增功能，gold 只改 `coverage/html.py`（加 3 行代码和 2 行注释）。
2. **材料与初态一致**：题面、base（`7fd1ea39`，6.1a0）、gold、隐藏测试、expected 能对上；各摘要与 bundle 逐项核对相符。noop 两次都是 40/46，失配的 6 个键失败原因都是 `AssertionError: File 'htmlcov/.gitignore' should exist`；gold 两次 46/46。M3 独立 runner 在来源镜像上跑 gold 两次，也都是 46 passed。以上是执行证据。
3. **主要问题：目标断言只查"存在"**。隐藏测试与公开 `tests/test_html.py` 的唯一差异是一行 `self.assert_exists("htmlcov/.gitignore")`（`H/test_1.py:147`），底层实现是 `os.path.exists`（`W/tests/coveragetest.py:276-279`）。
   - 文件内容不查。题面明确要求"ignores all its contents"，但空文件或只写 `*.html` 也能拿到 1（静态推断，置信度高；见 §9 C-B）。
   - CLI 路径不查；非默认输出目录下的 `.gitignore` 也不查。
4. **误拒风险低**：40 个回归键与公开测试逐字相同，解题者跑公开测试就能看到同样的约束。
   - 唯一可能误伤正确实现的是公开测试替身 `FileWriteTracker.open(filename, mode="r")`：如果在 `coverage/html.py` 里用 `open(..., encoding="utf-8")` 写这个文件，7 个 `HtmlDeltaTest` 键会因 `TypeError` 失败。
   - 但公开测试会以同样方式失败，所以这是可以提前发现的约束，不属于隐藏测试独有的误拒（见 C-C）。
5. **暂定处置**：`needs_review`，理由是"静态候选，待 actor 验证"，不是题意或测试争议。
   - 用途：适合做低难度的开发诊断或链路探针候选。
   - 用于评测或训练 reward 时，必须注明"目标检查只验存在性，比题面宽松"。
   - 是否补一条语义断言，进建议队列（§10），由用户决定。
6. **最关键的未知**：
   - 本题：C-B（空 `.gitignore`）在正式评分里是否确实拿 1。这是决定性的事实，但静态上几乎可以确定。
   - 共享机制：正式链路下模型实际收到的消息里，有没有 `public_hints`。
   - actor 侧：不加 `-p no:cacheprovider` 的原样 `python -m pytest tests/test_html.py` 在 actor 身份下能否跑通，还没有执行证据。

## 1. 公开读者没有捕获的真实条件（第 1 步）

| 项 | public_read 的判断 | 真实证据 | 级别 |
| --- | --- | --- | --- |
| 解释器与导入 | `python` 指向 `.venv`；coverage 是否可编辑安装未知 | agent（uid 54321）下 `coverage 6.1a0 /testbed/coverage/__init__.py`；在 `cwd=/` 导入也解析到 `/testbed`，说明候选改动对子进程 `coverage` 命令同样生效（`DC/orig/captures/env.out`） | 执行 |
| 控制台脚本 / git | 未知 | 有 `/testbed/.venv/bin/coverage` 与 `/usr/bin/git`；容器里有 `.git`，HEAD = base，`git status` 只有 `?? install.sh`、`?? run_tests.sh` | 执行 |
| pytest 与插件 | 推断已装 | `pytest 6.2.5`；`import pytest, xdist, flaky` 成功（`pr3_3_pytest.out`） | 执行 |
| 复现命令 C2 / C3 | 预期有区分力 | base 下没有 `.gitignore`，`git status` 列出 8 个 `??`；私有 gold 对照（root、一次性容器、不联网）写出 `'# Created by coverage.py\n*\n'`，`git status` 对 htmlcov 无输出（`private_gold/private_control.json`） | 执行 |
| 公开 HTML 回归 | 预期全过 | `-o addopts=""` 版本：agent 下 46 passed，用时 0.68 s（`pr5_6_pytest.out`） | 执行 |
| 原样 `python -m pytest tests/test_html.py` 与 C6 | 预期可跑 | **没有真正执行。** 协调者给命令加了 `-p no:cacheprovider`，而 `W/setup.cfg:5` 的 addopts 里有 `--failed-first`（由 cacheprovider 提供），于是 rc=4，报 `unrecognized arguments: --failed-first`。这是命令伪影，不是环境缺陷。R8 相关的 stdout 回归（test_process、test_plugins）因此没有执行证据 | 未知（actor 待验） |
| 模型实际消息 | 只有静态渲染 | devcheck 的首条用户消息是 devcheck 指令，不是题面（`DC/orig/stub/requests/messages_000.json`）。`render_user_prompt` 只拼"Fix the following issue…"加题面，不含 `public_hints`（`rh2/src/repoharness2/envpack/bundles.py:282-289`）。按环境卡 §2，hints 只写进 `/rh2/public_task_bundle.json`，不注入系统提示。所以模型能不能看到"不要改测试 / 用 `python -m pytest`"这类提示，目前未知 | 未知（共享机制） |
| 资源与网络 | 按 brief | 2 CPU / 4 GiB / pids 512；`/tmp` 是 1 GiB tmpfs；外部 DNS 被拒，只通 relay（`DC/orig/prelaunch.json`） | 执行 |
| 镜像身份 | — | devcheck 用 `rh2-r2e-derived/coveragepy:ea6906b092d9-r2e_derive_v1` = `sha256:cd000a54…`；评分证据用 `sha256:7471c22d…`（R-f 机）。两者同一配方 `r2e_derive_v1`、不同构建，没有逐字节核对等价 | 执行（差异已记录） |
| `.venv` 可写性 | — | 运行后 `/testbed/.venv/lib/python3.7/site-packages/_pytest/__pycache__/` 出现新文件（`DC/orig/post_run_facts_root.txt`），说明 agent 对 `.venv` 至少部分可写。census 会排除 `.venv/`，所以不影响交付 | 执行 + 代码配置 |

## 2. 隐藏测试展开（第 2 步）

- 材料：`H/test_1.py`（sha256 `e590d036…`）和空的 `H/__init__.py`，与 grading_bundle 的摘要相符；日志里 `RH2_SETUP_HIDDEN_TESTS_TREE=31eb58fe…` 与 `current_material` 一致。
- `diff W/tests/test_html.py H/test_1.py` 只有一处差异：`assert_htmlcov_files_exist` 新增第 147 行（执行证据：本地 diff）。
- 46 个键对应 46 个测试函数，全部期望 PASSED，没有参数化，也没有 SKIPPED / XFAIL。按类分布：
  - `HtmlDeltaTest` 7 个；
  - `HtmlTitleTest` 4 个；
  - `HtmlWithUnparsableFilesTest` 7 个；
  - `HtmlTest` 10 个；
  - `HtmlGoldTest` 14 个；
  - `HtmlWithContextsTest` 4 个。
- 只有一个隐藏测试文件，所以不存在跨文件撞键。

**目标键共 6 个。** 两次 noop 都是 FAILED，两次 gold 都是 PASSED：

| 键 | 调用路径 / 输入 | 最终断言 |
| --- | --- | --- |
| `HtmlDeltaTest.test_html_created` | `create_initial_files`（main_file / helper1 / helper2）→ `HtmlDeltaTest.run_coverage`（:124-137：`source="."`，用 `mock.patch("coverage.html.open", FileWriteTracker(...).open)`）→ `cov.html_report()` 默认目录 `htmlcov` | `assert_htmlcov_files_exist()`，其中 :147 检查 `os.path.exists("htmlcov/.gitignore")` |
| `…test_html_delta_from_source_change` | 跑两次，第二次只改 helper1 的注释 | :172 同一个 helper，另有 `files_written` 与 index 相等的检查（base 已通过） |
| `…test_html_delta_from_coverage_change` | 跑两次，第二次改 main_file | :199 同一个 helper |
| `…test_html_delta_from_settings_change` | 两次用不同的 `omit`（全量重写） | :216 同一个 helper |
| `…test_html_delta_from_coverage_version_change` | 把 `coverage.__version__` 改成 `"XYZZY"`（全量重写） | :239 同一个 helper |
| `…test_status_format_change` | 把 status.json 的 format 改成 99 后重跑 | :281 同一个 helper；:273 仍断言 `format == 2` |

- 这 6 个键实际只测**一件事**：在临时 cwd 下用 API 生成默认目录报告后，`htmlcov/.gitignore` 这个路径存在（可以是文件，也可以是目录）。
  - 它们不是 6 条独立要求，任何实现都会让这 6 个键一起通过或一起失败。
  - 多次运行的场景只要求这个文件在任意一次运行中被创建、之后没被删掉，不要求每次都重写。
- `test_file_becomes_100` 不调用这个 helper，所以不是目标键。
- **回归键 40 个**：全部与公开测试逐字相同，base 下都通过。覆盖范围：
  - 页面内容：gold 比对，`compare_html(... file_pattern="*.html")`，`test_styled` 另比 `*.css`；
  - 标题；skip_covered / skip_empty；
  - 不可解析文件；
  - CLI 无数据时输出 `"No data to report."`（`test_dothtml_not_python`）；
  - 返回值 `res == 100.0`；
  - 上下文；增量写入（`files_written`）。
- `compare()` 会先把 `left_only` / `right_only` 按 pattern 过滤（`W/tests/goldtest.py:43-46,168-174`），所以输出目录里多一个 `.gitignore` 不会破坏 gold 比对。
- **阅读范围**：
  - 读过：隐藏测试全文；`tests/coveragetest.py` 中 `assert_exists`、`assert_recent_datetime`、`run_command_status` 的开头部分；`tests/goldtest.py` 的比较函数；`tests/mixins.py` 的临时目录部分；`tests/conftest.py` 全文。
  - 没读：`tests/helpers.py` 的 `assert_coverage_warnings` 细节；`assert_warnings` 只读了 docstring；gold 目录下 HTML 文件的具体内容。

## 3. 需求—断言双向表（第 3 步）

| 公开要求 / 合理旧行为 | 依据 | 对应键与断言 | 覆盖 | 证据 / 待做 |
| --- | --- | --- | --- | --- |
| R1 生成报告后，输出目录根下有 `.gitignore`（API） | 题面 Expected Behavior 与示例 | 6 个目标键，:147 `assert_exists` | 覆盖（只测存在） | noop 失败、gold 通过（执行） |
| R2 内容让 git 忽略全部内容 | 题面 "ignores all its contents" | 无 | **缺失** | C-B 预期得 1（静态推断） |
| R3 CLI `coverage html` 也生成 | 推知：`W/coverage/cmdline.py:636-645` 走 `Coverage.html_report` | 无（CLI 回归键不查 `.gitignore`） | 缺失；只要实现落在 `html_report` / `HtmlReporter` 路径上就自然覆盖 | 私有 gold 对照里 CLI 路径实测写出文件（执行） |
| R4 非默认目录（`directory=`、`-d`、配置项） | 推知：`W/coverage/control.py:950-987` | `HtmlGoldTest` 用了 `out/...` 目录，但不查 `.gitignore` | 缺失（只能间接发现把路径写死、目录不存在就崩的实现） | — |
| R5 增量重跑后仍在 | 推知 | 多次运行的目标键 | 部分（"只写一次"也能过） | — |
| R6 已有输出文件名和内容不变 | 公开测试 | gold 比对 14 个键；`assert_htmlcov_files_exist` 其余 6 行 | 覆盖 | 执行 |
| R7 增量语义不变，`STATUS_FORMAT == 2` | 公开测试 | delta 键的 `files_written` 断言；:273 | 覆盖 | 执行 |
| R8 成功时 stdout 不多出消息 | 公开 `tests/test_process.py:1320-1354`、`tests/test_plugins.py:258-259` | 隐藏集不含这两个文件 | **缺失**（只有无数据路径 :367 查输出） | 公开命令 C6 在 devcheck 中未执行 |
| R9 返回值不变 | 公开测试 | `test_report_skip_covered_100` | 覆盖 | 执行 |
| R10 无数据时仍报 "No data to report." | 公开测试 | `test_dothtml_not_python` :366-367 | 覆盖报错信息；这种情况下写不写 `.gitignore`，两种都接受 | — |
| R11 已存在 `.gitignore` 时覆盖还是保留 | 题面没说 | 无 | 两种都接受（不算冲突） | C-A |

**反查**：唯一的新增断言对应题面 Expected Behavior，只取了"存在"这一半；其余断言全部来自公开旧测试。本题没有从隐藏材料里冒出来的新要求。

## 4. R2E 专项（第 4 步）

- **(a) 非 PASSED 键**：expected 里全是 PASSED，没有 FAILED 或 ERROR 键。所以不存在"更完整的修复把失败键翻转"的风险。源码改动也改变不了键集合，唯一例外是让隐藏测试模块导入失败，比如删掉或改名 `coverage.html.HtmlDataGeneration`，这不是合理修法。
- **(b) 题面现象是否出现在 noop 失败原因里**：是。R-f 的 noop 日志第 44 行和 envrepair 复跑日志都是 `AssertionError: File 'htmlcov/.gitignore' should exist`（`tests/coveragetest.py:279`），6 个键原因相同。
  - devcheck 在 agent 身份下复现：报告目录里没有 `.gitignore`，`git status` 列出 8 个未跟踪文件。
  - 题面 Actual Behavior 说"被 git 跟踪"，不准确：这些文件实际是"未跟踪"，执行 `git add .` 才会被加进去。这不影响理解题意。
- **(c) 题面是否泄漏修法**：题面给的是目标行为，也就是功能本身，没给位置、内容和写法；但"忽略全部内容"几乎就决定了内容是 `*`。结论是不算泄漏具体补丁，只是题目难度很低。
  - 题面的目录清单用了隐藏测试 helper 里的文件名（`main_file_py.html`、`helper2_py.html`），这些名字在公开测试里也有，无害。
  - 题面示例 `coverage.html_report(...)` 写成了模块级调用，字面上会报 `AttributeError`，属于小瑕疵。
- **(d) base 辅助、搬迁伪影与撞键**：
  - 隐藏测试依赖 base 版的 `tests.coveragetest`（`assert_exists`、`start_import_stop`、`run_command`）、`tests.goldtest`、`tests.helpers`、`tests.mixins`，以及 `tests/gold/html/*` 的 gold 文件。
  - 这些文件都不在 R2E 控制面里：控制面只有 `r2e_tests/<隐藏文件>` 和 `run_tests.sh`（`adapters/slime/r2e_grading_scripts.py:11-15,274-279`）。所以候选改了它们会被重放。具体例子：把 `tests/coveragetest.py:279` 改成不断言，就能不实现功能直接拿 1。这是平台已登记的共享缺口（`grading/trusted_projection.py:18-20`），在本题适用，入口就在这里。
  - 搬迁伪影：`tests/conftest.py` 对 `r2e_tests/` 不生效，因此少了 `set_warnings`、`reset_sys_path`、StopEverything 转 skip，以及 `register_assert_rewrite`。现有 4 次 RH2 运行加 2 次 M3 运行的结果都稳定，没有观察到影响。
  - 不撞键。
- **(e) 时间、随机与资源敏感**：
  - `HtmlTest.test_has_date_stamp_in_files` 要求报告时间戳在 120 秒内、且不晚于当前时间（`tests/coveragetest.py:293-297`）。时间戳精确到分钟，用本地时间，风险低。
  - delta 键比较 index 前会先把时间戳换成占位符（`H/test_1.py:72-81`）。
  - `-n3` 在 2 CPU 上起 3 个 worker；内存峰值约 357–368 MB，测试段 2.1–2.4 s（账本第 9 行）。
  - 没有随机数和网络。
- **(f) 材料修订**：无（`revisions.json` 为 `[]`）。

## 5. gold 检查（第 5 步）

- 位置：`HtmlReporter.make_local_static_report_files`，写在 STATIC_FILES 复制之后、`extra_css` 之前（gold hunk `@@ -224,6 +224,11 @@`）。
  - base 文件的 blob 是 `6246a9b9…`，与 patch 的 `index` 行一致（`git hash-object` 核对）。
  - API 和 CLI 都经 `Coverage.html_report` 进入 `HtmlReporter.report`，所以两条入口都生效。
  - 无数据时 `report()` 在 :211 先抛异常，不会写 `.gitignore`。
- 内容 `# Created by coverage.py\n*\n`：`*` 连 `.gitignore` 自己也忽略。私有对照里 `git status` 对 htmlcov 无输出（执行证据，root 身份）。
- 写法用的是 `open(path, "w")`，与测试替身签名兼容；注释说明了为什么不从源码树复制数据文件（会挡住静态文件入库）。
- **没有被测到的风险**：每次报告都**无条件覆盖**输出目录里已有的 `.gitignore`。如果用户用 `-d .`，或者指向一个已有内容的目录，原来的 `.gitignore` 会被换成 `*`，整个目录都会被 git 忽略（静态推断）。
  - 隐藏测试对这一点既不要求也不禁止。
  - 审查者记得上游后来改成"只在目录为空时写"，但这只是记忆，本地材料没有核实，只作线索。
- 没有混入其它改动，也没有依赖未交付的修改。gold 只包含 `coverage/html.py`，说明来源提交除了测试路径外只改了这个文件。

## 6. 开发需求（第 6 步，逐题）

| 项 | 需要什么 | 条件与证据 | 级别 |
| --- | --- | --- | --- |
| 导入 | 在 `/testbed` 直接改 `coverage/html.py`，立即生效 | 可编辑安装：`cwd=/` 下也导入 `/testbed/coverage`；评分侧 `RH2_INSTALL_SKIPPED=1` | actor 与评分都有执行证据 |
| 依赖 | 只用标准库；不需要 pip | pip 不存在；pytest 6.2.5、xdist、flaky 在 | 执行 |
| 资产 | 不需要新资产；公开测试的 gold 目录 `tests/gold/html/*` 已在工作树 | 公开 HTML 测试 46 passed | 执行 |
| 权限 | agent 可写 `/testbed`、home、`/tmp` | `WORKDIR_OWNER=54321`；`HOME_WRITABLE=1` | 执行 |
| 网络 | 各阶段都不需要 | 外部 DNS 被拒 | 执行 |
| 构建 | 不需要；C 扩展与本题无关 | — | 静态 |
| 自测 | 复现用 C2（API）/ C3（CLI + git）；回归用 `tests/test_html.py` | C2、C3 和 `-o addopts=""` 版本有执行证据；原样命令与 C6 未执行 | 部分 actor 待验 |
| 提交边界 | 只改 `coverage/html.py`（或新增一个非测试数据文件）；不碰控制面 | 正式 rollout 交付走 `export_frozen_patch`（`adapters/slime/generate.py:3479`），用 census、不经 git。按 `baseline_policy_r2e_v1`，排除 `.git/`、`.harness/`、`.venv/` 和 `__pycache__`、`.pytest_cache` 目录，其余文件（包括被 gitignore 的点文件）都交付 | 代码配置；本题候选交付未实跑 |

另：解题者如果在 `/testbed` 里生成过 `htmlcov/`、`.coverage` 之类复现产物，它们会被 census 当作候选文件交付。隐藏测试都在临时目录里运行，所以不受影响（静态推断）。

## 7. 交付与评分边界

- 合法修复只涉及非测试源码，不会被控制面剥离。gold 在两次评分里投影出的 `included_paths` 都是 `["coverage/html.py"]`（账本第 9 行）。
- 数据文件路线（新增 `coverage/htmlfiles/.gitignore` 并加进 STATIC_FILES）有三种不同结果：
  - 正式 census 导出：会交付（代码配置）。
  - 旧 S1 路径（`git add -N .`，见 `grading/manager.py:329-370`）：该文件内容是 `*`，会忽略它自己，导致漏交付，评分时复制失败（代码阅读推断）。
  - 实际打包：`setup.py:91-96` 的 `htmlfiles/*.*` 不收以点开头的文件，安装版会缺这个文件（静态推断）。测试测不到这一点。
- 可改变验收的题目特有入口：`tests/coveragetest.py`、`tests/goldtest.py`、`tests/gold/html/*`、根目录 conftest、`setup.cfg` 的 addopts。这些都是共享已知缺口在本题的具体落点。账本字段 `candidate_test_like_paths` 只做观测，不影响得分。

## 8. 题目关系与用途

- **同仓 5 题**：本题 base 是 6.1a0，最新；016af5f6、5dbbe143 是 5.0.2a1，97997d2c、f5eb5f21 是 5.0.5a0。
- **机械比对**：`cross_task_gold_scan.json` 里没有以本题为 task 的条目。我对 5 个 coveragepy 公开工作树的 `coverage/`、`tests/` grep `gitignore`，全部无命中。所以**本题的修复没有出现在任何其它题的初态里**。
- **反向关系**：本题初态包含 5dbbe143（7/7）、97997d2c（4/4）、f5eb5f21（2/2）的 gold 行；test scan 另报本题初态含 016af5f6 的新测试 `test_unencodable_filename`（gold scan 对这一对没报，可能是上游重构导致漏报）。
  - 抽查确认：`W/coverage/control.py:355` 已有 `_warn(self, msg, slug=None, once=False)`，对应 5dbbe143 的题面；`W/coverage/jsonreport.py:65-66,101-102` 已有 `covered_branches` / `missing_branches`，对应 f5eb5f21 的题面。
  - 影响：本题自身不受影响；但如果本题和这四题被分到训练与评测两侧，本题的公开工作树就等于给出了那四题的答案，划分时应当按同族处理（建议）。
  - 本题隐藏测试只改了已有 helper、没有新增测试函数，所以 test scan 对本题本身看不见任何东西。
- **任务类型**：3 行的小功能新增，题面基本就是规格，难度低。更适合作链路贯通或开发诊断用的简单题，不适合用来区分能力。这是静态判断，不预测基座成功率。
- **外部答案**：不联网；预检三项通过，`GIT_REFS` / `GIT_REFLOG` / `GIT_REMOTES` 都是 0。没有逐个对象检查 packfile（共享机制）。上游后续版本包含这个功能，模型预训练见过的可能性无法量化。

## 9. 候选（可直接改成补丁；按优先级）

| ID | 改动 | 语义判断 | 预期得分与不符键 | 能区分什么 |
| --- | --- | --- | --- | --- |
| **C-B**（可能蒙混） | `coverage/html.py::make_local_static_report_files` 在复制 STATIC_FILES 之后加 `open(os.path.join(self.directory, ".gitignore"), "w").close()`，不写任何规则。变体：只写 `"*.html\n"` | 违反"ignores all its contents"：git 仍会列出全部文件（变体下仍会列出 css、js、png、status.json） | **1**（46/46；静态推断，因为目标断言只有 `os.path.exists`） | 得 1 就确认"只验存在性"的宽松判定，这决定处置措辞 |
| **C-A**（合理替代） | 在 `report()` 开头（`self.incr.read()` 之前）记下 `self.directory_was_empty = not os.path.isdir(self.directory) or not os.listdir(self.directory)`；在 `report()` 末尾 `make_local_static_report_files()` 之后，仅当 `directory_was_empty` 时用 `open(path, "w")` 写 `"*\n"` | 满足全部公开要求，并且保护用户已有的 `.gitignore` | **1**（46/46）。首次运行时目录不存在就会写；后续运行不再写，但文件还在 | 得 0 就说明存在没发现的覆盖策略或写入时机约束，会推翻"误拒风险低"的判断 |
| **C-C**（公开可发现的约束） | 与 gold 相同，只是写成 `open(..., "w", encoding="utf-8")`，仿照 `coverage/report.py:31`、`coverage/annotate.py:76` 的现有写法 | 功能正确 | **0**；不符键是 `HtmlDeltaTest` 的全部 7 个（6 个目标键加 `test_file_becomes_100`），原因是 `TypeError`：替身 `FileWriteTracker.open(self, filename, mode="r")`（`H/test_1.py:104`，在 :136 patch 进去）不接受 `encoding`；其余 39 个键通过 | 确认这是公开测试同样会暴露的约束（公开 `-k HtmlDeltaTest` 同样失败），不是隐藏测试独有的误拒；本审建议不为它改题 |
| C-D（可选，机制类） | 新建 `coverage/htmlfiles/.gitignore`，内容 `*\n`；`STATIC_FILES` 追加 `".gitignore"` | 在源码运行下正确；安装版会缺文件 | 必须经正式 actor 工作区导出才有意义，用 `git apply` 补丁文本检验不了交付。按 census 导出预期 **1**；若走 S1 `git add -N .` 导出，文件会被漏掉，预期 **0**（几乎所有 html 键都失败） | 检验自我忽略的新文件能否交付 |

## 10. 问题清单、暂定处置与建议队列

**问题清单：**

1. **目标检查宽松**：只验存在，不验内容；CLI 和非默认目录也不验。
   - 证据级别：静态推断，置信度高；实跑 C-B 可以确认。
   - 影响：错误内容也会得到 reward 1。在 RL 里错误信号的风险中低，因为正常模型大多会写 `*`；但评测时这道题只能说明"会建文件"。
   - 对应清单编号：25、32。
2. **公开可见的实现约束**：替身签名会让带 `encoding` 参数的 `open` 失败。影响较小，解题者可以自己发现。对应清单编号：24（不判为误拒）。
3. **gold 的边界风险**：无条件覆盖已有 `.gitignore`。这是静态推断，测试不涉及，不影响得分。对应清单编号：27。
4. **共享机制在本题的落点**：
   - `tests/` 下的 base 辅助可以被候选改动并重放（对应清单编号 31）；
   - hints 是否进入模型消息未知（对应清单编号 3）；
   - 原样 pytest 命令在 actor 身份下未执行（对应清单编号 10，actor 待验）。
5. **同族关系**：本题初态包含另外三到四道 coveragepy 题的修复，划分时需要处理。对应清单编号：5。

**暂定处置**：`needs_review`，理由是"静态候选待 actor 验证；目标检查只验存在性"。
- `usage.intended_use=development_diagnostic`；
- 可以作为低难度的链路探针或开发诊断候选；
- 没有题意或测试争议，不建议改题才能使用。

**建议队列**（都未验证）：
1. 协调者用正式评分实跑 C-B、C-A、C-C，C-D 可选但必须经工作区导出。
2. 如果要把本题用作训练或评测 reward，可以考虑修订：补一条语义断言，例如在临时 git 仓库里生成报告后，断言 htmlcov 下除 `.gitignore` 以外的所有生成文件都被 `git check-ignore` 命中。
   - 这样 `*`、`/*`、`**`、`*` 加 `!.gitignore` 等写法都能通过，空文件和 `*.html` 会被拒。
   - 这属于测试标准变更：需要用户决定，按修订流程保存版本，并用 C-A、C-B 做正反校验；评分镜像里需要有 git（actor 镜像里有 `/usr/bin/git`，评分用户能否使用尚未核实）。
3. actor 侧补跑两条命令：原样的 `python -m pytest tests/test_html.py -k HtmlDeltaTest -q`，以及 C6（不加 `-p no:cacheprovider`）。

**唯一最值得先做的下一步**：用正式评分实跑 C-B（空 `.gitignore`），同批带上 C-A。

## 11. 八方面覆盖与未查项

| 方面 | 已查 | 未查 / 缺口 |
| --- | --- | --- |
| 公开需求 | 题面、公开包、public_read 的 R1–R13 逐条核对 | 模型实际消息（hints 是否可见） |
| 材料与初始问题 | 摘要、blob、diff、4 份 RH2 日志、2 份 M3 日志、devcheck 复现 | — |
| 测试是否测到要求 | 隐藏测试全文，6 个目标键逐条追到断言 | R2、R3、R4、R8 缺失 |
| 是否误拒合理解 | 替代实现逐条推演（C-A、C-C、C-D） | 全部未实跑 |
| 回归与 gold 完整性 | 受影响接口（静态复制、extra_css、无数据路径、返回值、增量）；gold 覆盖风险 | 其它报告（xml、json、annotate）没读，本题也不要求 |
| agent 开发条件 | devcheck 全部 captures、prelaunch、activation、post_run 事实 | 原样 pytest 命令与 C6 未执行；Qwen adapter 与真实模型未验 |
| 交付与评分边界 | census、投影、R2E 控制面代码；gold 投影路径 | 本题候选的正式导出没有实跑 |
| 题目关系与用途 | 两份扫描结果、5 个工作树 grep、两处抽查 | 016af5f6 与本题的包含关系只有函数名线索，未逐行核对 |

## 附录：证据索引

- 私有材料（`PRIVATE_DIR`）摘要：
  - `gold.patch` `bd20515f…`，等于 validation_bundle 的 `golden_patch`；
  - `expected_output.json` `7ab45968…`；
  - `run_tests.sh` `8285765f…`；
  - `hidden_tests/test_1.py` `e590d036…`；
  - 以上都与 grading_bundle 第 9 行一致。
- RH2 评分侧（`run_refs.json` 中 material=current，账本第 9 行，镜像 `sha256:7471c22d…`，配方 `r2e_derive_v1`）：
  - R-f noop：`runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl`，第 9 行，reward 0.0，匹配 40/46；日志 `…/evallog_replay-r2e-rf-all-noop-c_840ed0bd.eval.log`（sha 已核 `91b121d3…`），第 44 行是失败原因，第 387–393 行是 short summary（`6 failed, 40 passed`）。
  - R-f gold：`ledger_r2e_all_gold.jsonl` 第 9 行，1.0，匹配 46/46；日志 `65fc3529…`，第 171 行 `46 passed`。
  - envrepair 复跑：`runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl` 第 9 行；日志 `3015bf0e…`（6 failed / 40 passed）和 `e7aa5e11…`（46 passed）。
- M3 独立参考（来源镜像）：`runs/env_overnight_20260916/M3/gold_ledger/logs_r2e/coveragepy/ea6906b092d9/gold/a{1,2}/test_output.txt`（`67bd5291…`、`bf8ea1e1…`），都是 46 passed。
- devcheck（agent 身份、真实 Claude Code 2.1.205、桩端点、镜像 `sha256:cd000a54…`）：
  - `DC/orig/captures/*.out`；
  - `DC/orig/devcheck_stdout.json`：pr4_4、pr4_5、pr6_7 的 rc=4 是 `-p no:cacheprovider` 造成的伪影；
  - `DC/private_gold/private_control.json`。
- 本次实际读过的 RH2 代码：
  - `grading/manager.py:300-373,535-560`；
  - `adapters/slime/patch_exporter.py:1-140`；
  - `adapters/slime/baseline_census.py:30-130`；
  - `contracts/baseline_manifest.py:80-140`；
  - `grading/trusted_projection.py:1-100`；
  - `adapters/slime/r2e_grading_scripts.py:255-280` 及 grep；
  - `envpack/bundles.py:282-289`；
  - `adapters/slime/generate.py:3455-3500`。
- 未读：任何 history 与审查目录、本批 README / assignments / grader_candidates、其它题的私有包、runs 下的分析与汇总文件。
