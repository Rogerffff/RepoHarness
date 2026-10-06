# coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5 公开读者静态审查

- 角色：R2E 公开读者（第二批角色卡）；2026-09-25；干净上下文，只读了角色卡和 `PUBLIC_DIR`。
- 题目：base 提交是 `7fd1ea39925f0856ff607bb30796bc948a8c829d`（见 `public_bundle.json`），包版本 `6.1a0`（`coverage/version.py:8`）。
- 路径：除特别注明外，下文路径都相对 `PUBLIC_DIR/worktree/`，也就是解题者看到的 `/testbed`。行号按公开包里的 base 文件。
- 一句话题意：生成 HTML 覆盖率报告时，在输出目录里额外写一个 `.gitignore`，让 git 忽略这个目录的全部内容。这是新增功能，不是修缺陷。

## 1. 需求表

"性质"一列的含义：明示 = 题面直接写了；推知 = 从公开代码或测试可以合理推出；多解 = 有多种合理解释，公开材料定不下来。

| # | 行为 | 新增 / 保留 | 依据 | 性质 |
|---|---|---|---|---|
| R1 | 生成 HTML 报告后，输出目录根下存在名为 `.gitignore` 的文件 | 新增 | 题面 Expected Behavior | 明示 |
| R2 | 这个 `.gitignore` 让 git 忽略该目录的全部内容 | 新增 | 题面 "ignores all its contents" | 语义明示；具体写什么文本没有约定 |
| R3 | API `Coverage.html_report(...)` 和 CLI `coverage html [-d DIR]` 都要产生它 | 新增 | 两条入口都走 `HtmlReporter.report`：`coverage/control.py:950-987`、`coverage/cmdline.py:636-645`。题面只举了 API | 推知 |
| R4 | 输出目录可以来自 `directory` 参数、`-d` 或 `[html] directory`，默认 `htmlcov` | 新增行为的作用范围 | `coverage/config.py:215,384`；`coverage/html.py:141` 读取 `config.html_dir`；配置目录的例子见 `tests/test_html.py:803-819` | 推知 |
| R5 | 每次成功生成报告后 `.gitignore` 都在，包括增量重跑和所有页面都被 skip 的情况 | 新增 | 静态文件每次都复制（`coverage/html.py:222-225`，注释写着 "must always be copied"）；题面要求生成后目录里"should contain"它 | 推知 |
| R6 | 现有输出文件的名字和内容不变：`index.html`、各源文件页面、5 个 `STATIC_FILES`、`extra_css`、`status.json` | 保留 | `coverage/html.py:128-136,221-229,346-351,357-358`。gold 比对：`tests/test_html.py:568-591` 用 `file_pattern="*.html"`，`:944` 用 `"*.css"`。另见 `tests/test_html.py:139-146` | 公开测试 |
| R7 | 增量报告语义不变：源文件没变的页面不重写；`status.json` 仍是 format 2 | 保留 | `tests/test_html.py:154-246,265-284`（`:272` 断言 `format == 2`） | 公开测试 |
| R8 | `coverage html` 的 stdout 仍只有一行 `Wrote HTML report to <dir>/index.html`；加 `-q` 时没有任何输出 | 保留 | `coverage/html.py:348`；`tests/test_process.py:1320-1321,1353-1354`（用 `re.fullmatch` 断言整段输出）；`tests/test_plugins.py:258-259`（`assert out == ""`） | 公开测试 |
| R9 | `html_report` 的返回值（总覆盖率）不变 | 保留 | `coverage/html.py:219`；`tests/test_html.py:525-526` | 公开测试 |
| R10 | 没有可报告的数据时，仍抛 `CoverageException("No data to report.")`。base 在这种情况下不会创建输出目录 | 保留 | 异常在 `coverage/report.py:67-68` 和 `coverage/html.py:210-211`；目录只在 `html_file` 里创建（`coverage/html.py:235`）；测试见 `tests/test_html.py:356-366` | 抛异常这点有公开测试。无数据时要不要写 `.gitignore`，题面没说，属多解；自然读法是不写 |
| R11 | 输出目录里已经有用户自己的 `.gitignore` 时，是覆盖还是保留 | — | 题面没提 | 多解 |
| R12 | annotate（`-d` 目录）、xml、json 等其它报告是否也要写 | — | 题面只说 HTML | 不需要 |
| R13 | 要不要提供开关 | — | 题面没要求 | 可以作为扩展；但如果默认关闭，就违背了 R1 |

一个可推知但不属于题目要求的旁支影响：维护者的发布流程会把生成的 `htmlcov/` 用 `cp -r htmlcov/ .../doc/sample_html/` 拷进仓库里被跟踪的 `doc/sample_html/`（`howto.txt:24-35`；另见 `Makefile:157`）。如果拷过去的内容里带着 `*` 型 `.gitignore`，那个目录里的新文件就会被 git 忽略。这属于维护流程问题，解题者不必处理。

## 2. 合理实现范围

- **写在哪里**：只要在报告流程里、输出目录已经存在之后写，并且对 API 和 CLI 都生效，就应该接受。可以和静态文件复制放在一起（`make_local_static_report_files`，`coverage/html.py:221-229`），也可以放在 `report()` 或 `index_file()` 里。
  - 如果放得更早（例如 `HtmlReporter.__init__`），实现者要自己保证目录存在，而且会改变"无数据时不建目录"的现状（R10）。这不一定错，但隐藏测试怎么看这一点，公开材料里查不到。
- **怎么生成**：有两种做法，一是运行时直接写出文本，二是在 `coverage/htmlfiles/` 放一个数据文件，再加进 `STATIC_FILES` 一起复制。
  - 在 `/testbed` 从源码运行时，两种做法功能等价。
  - 第二种有两个公开可见的风险：
    1. `setup.py:91-96` 的 `package_data` 用的是 `htmlfiles/*.*`。按 Python glob 的语义，`*` 不匹配以点开头的文件名，所以安装后的包里可能缺这个文件。这是推断，未验证。
    2. 放在 `coverage/htmlfiles/` 下的 `*` 型 `.gitignore`，会让 coverage.py 仓库自己的 git 忽略这个目录里的未跟踪文件，包括这个 `.gitignore` 本身（要 `git add -f` 才加得进去）。
  - 评分环境很可能从源码运行，测试未必能区分这两种做法。
- **写什么内容**：题面只要求"忽略全部内容"。
  - `*`、`/*`、`**` 这类写法（带不带注释行都行）都会让 git 忽略目录里的一切，包括 `.gitignore` 本身，都符合题意。
  - 如果写成 `*` 再加 `!.gitignore`，`.gitignore` 自己仍会显示为未跟踪文件，和 "ignores all its contents" 的字面意思有出入。
  - **这是本题最主要的不确定项**：如果隐藏测试逐字比对文件内容，语义等价的其它写法也可能被判不通过。公开材料无法判断。
- **覆盖策略**：每次都重写，和"只在文件不存在时创建"，两种都说得通，题面没有约定（R11）。
  - 每次都重写，和 `STATIC_FILES` 每次都复制的做法一致。
  - 只在不存在时创建，可以保护用户自己写的 `.gitignore`。比如有人用 `-d .` 把报告写进项目根目录，每次重写就会覆盖掉项目的根 `.gitignore`。
- **文件名**：必须是输出目录根下的 `.gitignore`，不能改名。HTML 输出是扁平目录，页面名由 `flat_rootname` 生成（`coverage/html.py:233-236`），没有子目录。
- **输出**：不应该往 stdout 新增任何消息，否则会破坏 R8 那几个测试。
- **公开测试施加的实现约束**：
  - `HtmlDeltaTest.run_coverage` 用 `mock.patch("coverage.html.open", FileWriteTracker(...).open)` 替换了 `coverage/html.py` 模块里的 `open`（`tests/test_html.py:99-108,124-137`）。这个替身的签名只有 `open(filename, mode="r")`。
  - 所以，如果在 `coverage/html.py` 里新写的 `open(...)` 调用带了 `encoding=`、`newline=` 之类的额外参数，这组公开测试（`test_html_created`、`test_html_delta_*`、`test_file_becomes_100`、`test_status_format_change`）会因为 `TypeError` 失败。
  - html.py 现有的 `open` 调用都只传文件名和 mode（`coverage/html.py:36,43,402,436`）。
  - 通过这个 `open` 写的文件会被记进 `files_written`。现有断言只检查几个指定页面在不在里面，所以每次都写 `.gitignore` 不会破坏现有断言。隐藏测试会不会断言 `.gitignore` 出现或不出现在 `files_written` 里，未知。
  - 用 `shutil` 或其它模块的 API 来写，则不受这个替身影响。
- **文档和变更记录**：`CHANGES.rst:23` 起有 Unreleased 段，`doc/cmd.rst:453-462` 介绍了 HTML 输出目录。更新它们可以，不更新也可以，都不影响功能。
- **想不出**需要改动模板（`coverage/htmlfiles/*.html`）或 `IncrementalChecker` 状态格式的合理理由。改 `STATUS_FORMAT` 会破坏 `tests/test_html.py:272`。

## 3. 题面质量与初态线索

**3.1 题面是否直接给出或强烈暗示了修法。** 题面描述的是目标行为：加一个 `.gitignore`，让它忽略全部内容。它没有给代码、位置，也没有给文件的具体文本，不存在"示例代码就是修好后的实现"的情况。对这类功能型改动，描述目标行为几乎就等于说明要做什么，但写在哪里、写什么字面、要不要覆盖，仍然要开发者自己定。另外，`public_hints` 里 "find the root cause" 的说法和本题性质（缺功能，不是缺陷）不太贴合，不影响解题。

**3.2 题面描述的行为能否从 base 源码读出。** 能。
- html.py 会写出这些文件：逐文件页面（`coverage/html.py:309-310`）、`index.html`（`:346-347`）、`status.json`（`:351` 调到 `:422-437`）、`STATIC_FILES`（`:130-136,224-225`）、`extra_css`（`:228-229`）。
- 没有任何代码写 `.gitignore`。在整个 worktree 里对文件内容 grep `gitignore`（不区分大小写），没有匹配。
- 题面 Actual Behavior 说文件会"被 git 跟踪"，这个说法不精确。git 不会自动跟踪文件，这些文件只是显示为未跟踪，在执行 `git add .` 或 `git add -A` 时才会被加进去。本仓库自己的根 `.gitignore` 第 24 行就已经忽略了 `htmlcov`。这些不影响对题意的理解。

**3.3 题面示例在 base 接口下是否说得通。**
- 按字面对模块调用 `coverage.html_report(directory='htmlcov')` 会得到 `AttributeError`。`coverage` 模块没有模块级的 `html_report`：`coverage/__init__.py:13-22` 只导出 `Coverage` 等名字，`coverage.coverage` 只是类的别名。
- 这个示例应该理解为 `Coverage` 实例的方法调用。见 `coverage/control.py:66-76` 的 docstring（`cov.html_report(directory='covhtml')`）和 `coverage/control.py:950-987`。读者很容易看懂，不构成障碍。
- 题面的目录清单只是节选。base 还会写出 `keybd_closed.png`、`keybd_open.png`、`favicon_32.png`（`coverage/html.py:130-136`）和 `status.json`（`:357`）。按公开测试的 helper，还会有 `helper1_py.html`（`tests/test_html.py:40-44`）。所以这个清单不是完整规格，不能据此推断其它文件应该删掉。

**3.4 公开材料能否定位复现与调查入口。** 能。
- 清单里的 `main_file_py.html`、`helper2_py.html`，和 `tests/test_html.py` 里的 `HtmlTestHelpers.create_initial_files`（`:33-48`）、`HtmlDeltaTest.assert_htmlcov_files_exist`（`:139-146`）一致，说明 `tests/test_html.py` 是自然的调查入口。
- 实现入口是 `coverage/html.py` 中 `HtmlReporter.report` → `make_local_static_report_files`（`:195-229`），读一遍就能找到。

**3.5 缺失信息的影响。** 真正影响能否通过隐藏测试的只有三点，公开材料都无法判断：
- `.gitignore` 的字面内容要求；
- 已经有 `.gitignore` 时的覆盖策略；
- 无数据时要不要写。

写在哪里、怎么写，正常读代码就能解决，不算题面缺陷。

**3.6 初态线索。**
- `worktree_manifest.json` 的 `initial_diff` 是 0 字节，sha256 是空内容的摘要。也就是说，工作树 = base 的跟踪文件 + 未跟踪的 `run_tests.sh`。没有需要解读的镜像初态改动。
- 镜像里还有 `install.sh`，但没有随公开包提供（见 `untracked_missing`）。所以 `.venv` 是怎么装的、C 扩展有没有编译，都不可知。
- `run_tests.sh` 执行的是 `.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests` 目录不在工作树里（是隐藏测试），而且这条命令没有覆盖 `setup.cfg` 里的 `addopts`。

**3.7 `public_hints` 的三类内容。**
- 题目需求："fixing a real GitHub issue"；"Explore the code, find the root cause, and edit NON-TEST source files to fix the issue"。影响：修改应落在非测试源码，主要是 `coverage/html.py`。如果选择加数据文件，`coverage/htmlfiles/` 也属于非测试源码。
- 给解题者的操作指令：
  - "Do NOT modify the repository's test files"：不能在 `tests/test_html.py` 里加断言。自测可以用仓库外临时目录里的脚本，第 4 节的命令就是这样做的。
  - 测试要窄跑，并且在 `/testbed` 下用 `python -m pytest` 运行：这和 `setup.cfg` 的配置是兼容的。
  - 完成后给出简短总结，并停止调用工具。
  - 这些指令都不妨碍合法解法。
- 环境事实声明：
  - `.venv` 位于 `/testbed/.venv`，"python and the repo's test tools already point at it"：`environment_brief.md` 只确认了 `python`（Python 3.7.9）。pytest 插件和 `coverage` 命令行脚本是否就位，没有逐项确认。
  - 无网络，pip 可能不可用：brief 确认 pip / pip3 / uv 都不在 PATH。本题只需要标准库，不受影响。
  - "the fix is judged by a separate set of tests"：和 `run_tests.sh` 跑的 `r2e_tests` 对得上。

## 4. 开发需求表

下面所有命令都是**建议，未执行**。每条都从 `/testbed` 起跑。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 命令编号 |
|---|---|---|---|---|
| 解释器，以及导入 `/testbed` 下的源码 | `setup.py:134` 要求 `python_requires=">=3.6"` | 确认 `python` 指向 `/testbed/.venv/bin/python`（3.7.9） | coverage 是否以 editable 方式装进 `.venv` 未知；C 扩展是否已编译未知（`install.sh` 缺失，`*.so` 被 `.gitignore` 排除）。可能退回 PyTracer，不影响本题 | C1 |
| 编辑非测试源码 | `public_hints` | 以 agent 身份（uid 54321）可写 `/testbed` | 无 | — |
| 通过公开 API 复现，能区分修复前后 | 题面示例；`coverage/control.py:950-987` | 只需标准库和本地源码 | 无 | C2 |
| 通过 CLI 复现，并核对 git 是否真的忽略 | `coverage/cmdline.py:636-645`；`coverage/__main__.py` | 用 `python -m coverage` 就不依赖命令行脚本 | brief 没说有没有 `git`（worktree 不含 `.git`） | C3 |
| pytest 与插件 | `setup.cfg:5` 的 `addopts = -q -n3 --strict-markers --force-flaky --no-flaky-report -rfeX --failed-first`，需要 pytest-xdist 和 flaky；`requirements/pytest.pip` 钉了 pytest 6.2.5、pytest-xdist 2.4.0、flaky 3.7.0 | brief 只确认了 `python`，没列已装的包。`run_tests.sh` 用的是同一份配置，推断插件已装 | 插件是否齐全未核实 | C4 |
| `coverage` 命令行脚本在 PATH 中 | `tests/coveragetest.py:318,371-383`：`run_command("coverage ...")` 直接调这个脚本。用到它的有 `tests/test_html.py:362-365,457-458`、`tests/test_process.py:1313-1359`、`tests/test_plugins.py:240-259` | 未提 | 未知。如果缺失，这些用例在修复前就会失败，属于环境缺口，和修复无关 | C4 |
| 公开回归测试（HTML） | `tests/test_html.py` | 测试在 pytest 临时目录里跑（`tests/mixins.py:55-73`），默认位于 `/tmp` | `/tmp` 只有 1 GiB，对这些小测试足够。`-n3` 在 2 CPU 上会起 3 个 worker，可以改加 `-n0`（需要 xdist） | C5 |
| stdout 约束回归（R8） | `tests/test_process.py:1320-1321,1353-1354`；`tests/test_plugins.py:258-259` | 同上 | 依赖 `coverage` 命令行脚本 | C6 |
| 网络 / pip | — | brief 说明两者都没有 | 本题不需要 | — |

**C1 导入自检**（建议，未执行）

```bash
cd /testbed && python -c "import coverage, coverage.html; print(coverage.__version__, coverage.__file__)"
```

预期修复前后相同：`6.1a0 /testbed/coverage/__init__.py`。如果显示的是 site-packages 路径，说明从其它目录运行时会用到没被修改的安装副本。

**C2 经公开 API 复现**（首选的修复前后区分命令；建议，未执行）

```bash
cd /testbed && python - <<'EOF'
import os, sys, tempfile
sys.path.insert(0, "/testbed")
import coverage
print("coverage from:", coverage.__file__)
work = tempfile.mkdtemp()
os.chdir(work)
with open("demo.py", "w") as f:
    f.write("def f(x):\n    if x:\n        return 1\n    return 2\n\nf(1)\n")
sys.path.insert(0, work)
cov = coverage.Coverage()
cov.start()
import demo
cov.stop()
cov.html_report(directory="htmlcov")
print(sorted(os.listdir("htmlcov")))
gi = os.path.join("htmlcov", ".gitignore")
print(".gitignore exists:", os.path.exists(gi))
if os.path.exists(gi):
    with open(gi) as f:
        print(repr(f.read()))
EOF
```

- 修复前：列表大致是 `['coverage_html.js', 'demo_py.html', 'favicon_32.png', 'index.html', 'keybd_closed.png', 'keybd_open.png', 'status.json', 'style.css']`，然后输出 `.gitignore exists: False`。
- 修复后：列表里多出 `'.gitignore'`（排在最前），输出 `.gitignore exists: True`，并打印出能让 git 忽略全部内容的文本（例如含一行 `*`）。
- 所有产物都在临时目录里，不会弄脏 `/testbed`。

**C3 经 CLI 复现，并核对 git 语义**（建议，未执行）

```bash
cd /testbed && D=$(mktemp -d) && printf 'def f(x):\n    return x + 1\n\nf(1)\n' > "$D/demo.py" && ( cd "$D" && export PYTHONPATH=/testbed && python -m coverage run demo.py && python -m coverage html -d htmlcov && ls -A htmlcov && echo '--- htmlcov/.gitignore:' && { cat htmlcov/.gitignore || true; } && if command -v git >/dev/null 2>&1; then git init -q . && echo '--- git status (htmlcov only):' && git status --porcelain --untracked-files=all -- htmlcov; else echo '(git not found; skipped)'; fi )
```

- 修复前：
  - 先打印一行 `Wrote HTML report to htmlcov/index.html`；
  - `ls -A` 列出的文件里没有 `.gitignore`；
  - 出现 `cat: htmlcov/.gitignore: No such file or directory`；
  - 如果有 git，会逐个列出 `?? htmlcov/<文件名>`，共 8 行。
- 修复后：
  - 第一行输出不变，而且只有这一行，因为 R8 要求如此；
  - `ls -A` 能看到 `.gitignore`，`cat` 能打印出内容；
  - `git status` 对 `htmlcov` 没有任何输出。如果只剩一行 `?? htmlcov/.gitignore`，说明所写的规则没有覆盖 `.gitignore` 自己（见第 2 节"写什么内容"）。

**C4 测试工具与命令行脚本预检**（建议，未执行）

```bash
cd /testbed && python -c "import pytest, xdist, flaky; print('pytest', pytest.__version__)"; command -v coverage || echo "no coverage console script on PATH"
```

预期打印 `pytest 6.2.5`，以及 `/testbed/.venv/bin/coverage` 之类的路径。如果 import 失败，C5 要改用去掉 `addopts` 的写法。如果 `command -v coverage` 没有找到，依赖 `run_command("coverage ...")` 的用例就不能用来判断修复是否正确。

**C5 公开 HTML 回归测试**（建议，未执行）

```bash
cd /testbed && python -m pytest tests/test_html.py -k HtmlDeltaTest -q
cd /testbed && python -m pytest tests/test_html.py -q
```

- 预期修复前后都全部通过。仓库里没有针对 `.gitignore` 的公开测试，所以这只是回归检查。
- 第一条专门覆盖第 2 节说的 `open` 替身约束。如果新代码在 `coverage/html.py` 里调用 `open` 时带了额外参数，这里会出现 `TypeError: open() got an unexpected keyword argument ...`。
- 如果报 `unrecognized arguments: -n3` 或 `--force-flaky`，说明插件不全，可以改用：

```bash
cd /testbed && python -m pytest -o addopts="" tests/test_html.py -q
```

**C6 stdout 约束回归**（建议，未执行；依赖 `coverage` 命令行脚本）

```bash
cd /testbed && python -m pytest tests/test_process.py -k UnicodeFilePathsTest -q && python -m pytest tests/test_plugins.py -k test_local_files_are_importable -q
```

预期修复前后都通过。如果修复额外打印了消息：
- 前者会在 `tests/test_process.py:1321` 或 `:1354` 的 `re.fullmatch` 处失败；
- 后者会在 `tests/test_plugins.py:259` 的 `assert out == ""` 处失败。

## 5. 阅读范围

**实际打开的文件。**
- 角色卡。
- `PUBLIC_DIR` 下的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
- `worktree_manifest.json`：只看了顶层键、`export`、`initial_diff` 的元数据、`untracked_*`，以及按 "sample" 过滤的 `files` 键名。没有打开 `initial_diff.source` 指向的路径，那条路径在 `PUBLIC_DIR` 之外。
- worktree 中的文件：
  - 通读：`run_tests.sh`、`coverage/html.py`、`coverage/__init__.py`、`coverage/version.py`、`setup.cfg`、`MANIFEST.in`、根 `.gitignore`、`tests/test_html.py`、`tests/conftest.py`、`requirements/pytest.pip`（去掉 hash 行）、`tests/gold/html/Makefile`。
  - 只读了部分：
    - `coverage/control.py`：52-90、102-115 附近、196-200、380-392、920-1000；
    - `coverage/cmdline.py`：380-400、615-660；
    - `coverage/report.py`：48-90；
    - `coverage/misc.py`：`file_be_gone`、`ensure_dir`；
    - `coverage/config.py`：只 grep 了 html 相关配置；
    - `tests/goldtest.py`：1-120、168-176；
    - `tests/coveragetest.py`：30-70、270-475；
    - `tests/mixins.py`：55-75；
    - `tests/test_api.py`：38-52、275-292；
    - `tests/test_process.py`：452-480、1300-1360；
    - `tests/test_plugins.py`：250-266 及类名定位；
    - `tox.ini`：1-80；
    - `CHANGES.rst`：1-50；
    - `doc/cmd.rst`：440-520；
    - `setup.py`、`Makefile`、`howto.txt`、`igor.py`、`doc/config.rst`：只 grep 了相关行。
  - 列过目录：`coverage/htmlfiles/`、`tests/`、`tests/gold/html/` 及其 `a`、`styled`、`support` 子目录、`doc/`、`requirements/`。
  - 全 worktree 范围：grep 了 `gitignore`；在 `tests/` 里 grep 了目录枚举和 HTML 相关调用。

**没有查的范围。**
- coverage 其余模块的细节：`results.py`、`files.py`、`inorout.py`、`collector.py`、`ctracer/` 等。
- `lab/`、`perf/`、`ci/`、`.github/`，以及 `doc/` 中除上述之外的文件。
- 其它测试文件的全文。

**范围与限制。**
- 没有读 `PUBLIC_DIR` 之外的任何路径。角色卡里链接的 SWE-Gym 版角色卡也没有打开。
- 没有运行项目代码，没有联网。宿主上的 `python3` 只用来解析 `worktree_manifest.json`。第 4 节的所有命令都未执行，预期结果全部来自静态阅读。
- `user_prompt.txt` 只是静态渲染，不是捕获到的模型实际请求。
- `worktree/` 不是完整的运行容器：没有 `.venv`、`.git`、编译扩展、`install.sh`，也没有隐藏测试 `r2e_tests`。
- 因此本文没有验证模型实际收到的消息、运行资源或开发条件。插件是否就位、`coverage` 命令行脚本是否存在、有没有 `git`，都要靠协调者在真实环境里跑 C1、C4 核对。
