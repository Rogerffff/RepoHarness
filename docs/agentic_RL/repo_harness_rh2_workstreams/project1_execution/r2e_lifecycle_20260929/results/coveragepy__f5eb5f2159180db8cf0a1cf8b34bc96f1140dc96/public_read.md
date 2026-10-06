# coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96：公开阅读

- 角色：R2E 公开读者（单题闭环试行 2026-09-29），干净上下文。只读了角色卡和本题公开包；没有读任何 `private/`、`history/`、gold 补丁、隐藏测试、其它题材料或审查结论。
- 路径约定：下文路径相对本题公开包根目录；`worktree/` 对应解题容器里的 `/testbed`。行号都指公开包里的文件。
- 性质：静态阅读。没有运行项目代码、测试或容器；§4 与同目录 `commands.json` 里的命令都是**建议，未执行**。
- 题目一句话：分支覆盖模式下，JSON 报告的 `totals` 缺少 `covered_branches`、`missing_branches` 两个计数，要求补上。

## 1. 需求表

| 编号 | 行为 | 类型 | 依据 | 明确程度 |
| --- | --- | --- | --- | --- |
| R1 | 启用分支测量时，JSON 报告的 `totals` 增加 `covered_branches` 与 `missing_branches` | 改变 | 题面 `user_prompt.txt:7`、`:21`、`:24`；base 的 totals 只写 5 个行计数键 + `num_branches`、`num_partial_branches`（`worktree/coverage/jsonreport.py:51-63`） | 明示 |
| R2 | 对公开夹具（`a = {'b': 1}` / `if a.get('a'):` / `b = 1`，2 个分支走了 1 个），两值都是整数 1 | 改变 | 题面错误信息 `user_prompt.txt:28`；同一夹具的现有数值见 `worktree/tests/test_json.py:21-25`、`:61-69`（`num_branches` 2、`num_partial_branches` 1、`percent_covered` 60.0） | 明示，但只有这一组数 |
| R3 | 两值按"分支弧"计数：`covered_branches` = 已执行的分支弧数，`missing_branches` = 未执行的分支弧数，两者之和等于 `num_branches` | 改变 | `Numbers.n_missing_branches` 与 `n_executed_branches = n_branches - n_missing_branches`（`worktree/coverage/results.py:36`、`:201-204`）；XML 报告的 `branches-covered` 是同一口径（`worktree/coverage/xmlreport.py:122-123`、`:203-205`） | 可从仓库合理推知。示例里 `missing_branches` 与 `num_partial_branches` 都是 1，示例本身区分不了"未执行分支弧数"（`results.py:36`）和"部分覆盖的分支行数"（`results.py:35`） |
| R4 | 未启用分支测量时，`totals` 和每文件 `summary` 都不出现分支键 | 保留 | 现有门控 `jsonreport.py:59`、`:94`；公开测试用整字典相等锁定非分支形状（`worktree/tests/test_json.py:35`、`:86-101`、`:134-149`）；题面限定 "with branch coverage enabled"（`user_prompt.txt:7`） | 明示（公开测试） |
| R5 | 新键的出现条件与现有分支键一致：看数据是否含弧（`coverage_data.has_arcs()`），而不是看配置 `branch` | 约定 | `jsonreport.py:38`、`:59`、`:94`；`coverage json` 子命令没有 `--branch` 选项（`worktree/coverage/cmdline.py:374-388`），常见用法是先 `coverage run --branch`，再另起进程出报告，此时配置里 `branch` 为假而数据含弧 | 可推知；判分是否覆盖这一差别未知 |
| R6 | 其余输出不变：`meta` 各键；每文件 `executed_lines` / `missing_lines` / `excluded_lines` / `contexts`；summary 与 totals 已有键及数值（含 `percent_covered`）；`report()` 返回值（`--fail-under` 用它） | 保留 | `jsonreport.py:35-40`、`:51-63`、`:71`、`:77-98`；`cmdline.py:611-622`；`tests/test_json.py:40-69` | 明示（代码与公开测试） |
| R7 | 每文件 `files[*].summary` 是否也加这两个键 | 未定 | 题面只点名 totals（`user_prompt.txt:7`、`:21`、`:24`），错误信息也只展示 totals 并用 `...` 省略（`:28`）；但 base 里 totals 与每文件 summary 的分支键是成对写的（`jsonreport.py:59-63` 对 `:94-98`） | 多种合理解释，见 §2、§3.3 |
| R8 | 每文件另给分支明细列表（类似每文件顶层的 `executed_lines` / `missing_lines` 列表） | 未要求 | 题面没有提。注意同名歧义：每文件顶层的 `missing_lines` 是行号列表，summary / totals 里的 `missing_lines` 是计数（`jsonreport.py:78-89`） | 未要求 |
| R9 | CLI `coverage json` 与 API 共用实现，随 R1 同步变化 | 改变 | `cmdline.py:602-609` → `worktree/coverage/control.py:953-975` → `JsonReporter` | 可推知 |

### 1.1 公开提示的三类（`public_bundle.json:15`）

- **题目需求 / 解法约束**：只改非测试源文件；不得修改仓库测试文件，判分用另一组测试。
- **给解题者的操作指令**：先探索、找根因；验证时只跑单个测试文件或模块；从 `/testbed` 用 `python -m pytest`；只用已装的包；完成后简短总结并停止调用工具。
- **环境事实声明**：仓库在 `/testbed`；`python` 与测试工具指向 `/testbed/.venv`；无网络；pip 可能不可用。`environment_brief.md:10-12` 更具体：Python 3.7.9，pip 有但无出网，解题身份 uid 54321，默认 2 CPU / 4 GiB，`/tmp` 1 GiB。
- **对合法解法的影响**：
  1. 任何满足 R1 的修复都会让公开用例 `tests/test_json.py::JsonReportTest::test_branch_coverage` 失败（见 §3.2），而提示禁止改测试，所以解题者只能把这条失败当作预期。
  2. `python -m pytest` 会带上 `worktree/setup.cfg:1-2` 的 addopts（`-q -n3 --strict --no-flaky-report -rfe --failed-first`），前提是 pytest-xdist 与 flaky 已装（推断，未验证，见 §4）。
  3. 其余提示不影响解法；`allowed_tools` 为 bash / edit（`public_bundle.json:5-8`）。

## 2. 合理实现范围

- **应接受的差异**：
  - 只在 totals 的分支块里补两键，这是贴合题面字面的最小做法。
  - 数值可以直接取 `self.total` 上现成的计数，也可以在 `Numbers` 上加等价属性，或逐文件累加；只要结果符合 R3 的口径。`self.total` 由各文件 `Numbers` 相加而来，`__add__` 已累加 `n_missing_branches`（`results.py:259-261`）。
  - 键在 JSON 对象里的顺序不限：公开测试 `json.load` 后按 dict 比较（`tests/test_json.py:29-35`）。
  - 在 `worktree/CHANGES.rst:24-30` 的 Unreleased 段或文档里补一句说明是可选的，不影响行为。
- **已有明确约定**：键名（题面给定）、所在段落（`totals`）、值为整数（题面示例是 1）、非分支模式不出现（R4）、门控沿用 `has_arcs()`（R5）。
- **无法从公开材料确定**：R7。两种做法都说得通：只加 totals 最贴题面字面；对称加到每文件 summary 最贴现有代码结构。如果判分沿用公开测试那种整字典相等（`tests/test_json.py:35`），这两种做法只能有一种通过；公开材料判断不了是哪一种。本角色不猜标准答案。
- **不建议顺手扩展**：例如在 `meta` 加格式版本号、拆出分支覆盖率百分比、给每文件加分支明细列表。`worktree/doc/branch.rst:52-54` 说 JSON 报告含 "separate statement and branch coverage percentages"，但 base 的 JSON 只有一个 `percent_covered`。这是文档和实现早已存在的出入，不是本题要求；照着它加字段，会被整字典相等断言判为失败。
- 除上面这些写法差异外，想不出行为不同但同样应被接受的实现。

## 3. 题面质量与初态线索

### 3.1 题面质量（R2E 自动生成题面）

1. **是否直接给出或强烈暗示修法**：没有给出实现代码，示例代码只是调用方式。但题面点名了键名、所在段落和示例数值，而 base 的 `Numbers` 已经提供所需计数（`results.py:170-179`、`:201-204`），修复几乎是机械的。难点只在找对文件（`coverage/jsonreport.py`，100 行），以及对 R3、R7 做选择。
2. **题面描述的行为能否从 base 源码读出**：能。`jsonreport.py:51-63` 在分支模式下只写 `num_branches`、`num_partial_branches`，确实没有这两个键。但题面说"导致测试 AssertionError"，这在 base 的公开测试上不会发生：公开 `test_branch_coverage` 断言的恰恰是没有这两个键的旧形状（`tests/test_json.py:45-69`），用的是裸 `assert ==`（`:35`）。题面信息是 `X != Y` 格式（unittest `assertEqual` / `assertDictEqual` 的风格），只展示了 `totals`，其余用 `...` 省略（`user_prompt.txt:28`）。所以这条错误信息应看作对判分测试失败的转述或节选，无法用公开测试复现；从它也看不出 `files` 段是否同样有差异，这是 R7 无法判定的原因之一。
3. **题面示例在 base 接口下是否说得通**：说得通。`coverage.Coverage(branch=True)`、`start()` / `stop()`、`json_report(outfile=...)` 在 base 都存在（`control.py:99-104`、`:953-975`）。但 `# ... execute some code ...` 只是占位（`user_prompt.txt:15`）。如果测量窗口内没测到任何文件，`json_report` 会在 `worktree/coverage/report.py:65-66` 抛出 `No data to report.`，所以要自己补被测代码；公开夹具 `tests/test_json.py:21-28` 可以直接借用。另外，未指定 source / include 时，base 只排除标准库和 coverage 自身（`worktree/coverage/inorout.py:321-330`）。如果窗口内执行了 venv 里其他非标准库的 Python 代码（例如导入钩子），这些代码也会被计入。照示例不传 `morfs` 时，它们会一起汇进 totals：不影响"有没有这两个键"，但会影响数值比较。复现时应像公开测试那样，把报告限定到被测文件。
4. **标题把"新增字段"说成 bug**：base 文档从没承诺过这两个字段。`worktree/doc/cmd.rst:474-485` 没有描述 JSON 结构，`worktree/doc/config.rst:378-402` 只列出 `output` / `pretty_print` / `show_contexts`。本质上这是一个小功能补充，不影响可解性。

### 3.2 初态线索

- 工作树就是 base 提交 `17204597c33d`（`user_prompt.txt:1`、`public_bundle.json:9`）。镜像初态相对 base 没有改动：initial diff 为 0 字节（`worktree_manifest.json:14-16`）。
- 镜像的 `/testbed` 里还有两个未跟踪文件 `install.sh` 与 `run_tests.sh`，公开包只收录了后者（`worktree_manifest.json:20-31`）。因此本角色看不到 `.venv` 是怎么建的：是否以 editable 方式安装 coverage、是否编译了 C 扩展，都不知道（`*.so` 本来就被 `worktree/.gitignore:6` 忽略）。
- `worktree/run_tests.sh:1` 跑的是 `r2e_tests`，工作树里没有这个目录；manifest 说明隐藏测试不在工作树（`worktree_manifest.json:33`）。推断：解题者照跑会因找不到路径而失败，这是预期，不说明环境坏了。
- **公开测试与题目要求冲突**：任何满足 R1 的修复都会让 `tests/test_json.py::JsonReportTest::test_branch_coverage` 失败，因为它锁定了旧的 totals 与 summary（`:45-69`）；而提示禁止改测试（`public_bundle.json:15`）。解题者应把这条失败当作预期。它的差异输出反而能用来确认只多出了预期的键。其余 3 个用例（`test_simple_line_coverage`、`test_context_non_relative`、`test_context_relative`）必须继续通过（R4、R6）。
- 版本是 5.0.5a0（`worktree/coverage/version.py:8`）。

### 3.3 调查入口与缺失信息

- **入口明确**：`coverage/jsonreport.py` → `coverage/results.py` 的 `Numbers` / `Analysis` → `tests/test_json.py` 的夹具和期望结构。API 入口在 `control.py:953-975`，CLI 入口在 `cmdline.py:602-609`。
- **真正影响结果的缺失信息**：R7（每文件 summary 是否加键）。它不妨碍开发，但如果判分是整字典相等，它决定成败，而公开材料无法判定。
- **影响较小的**：R3 的口径。题面示例的数值区分不了两种含义，但按 `Numbers` 和 XML 报告的现有口径可以合理推知。
- 其余事项（找文件、取计数、门控条件）读代码就能弄清，不算题面缺陷。

## 4. 开发需求表

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 命令 id |
| --- | --- | --- | --- | --- |
| Python 解释器，导入工作树里的 coverage | `public_bundle.json:15`；`coverage/version.py:8` | 环境阶段实测：`python` → `/testbed/.venv/bin/python`，3.7.9（`:10`） | `.venv` 怎么装的看不到（见 §3.2）。从 `/testbed` 运行时 cwd 在 `sys.path` 首位，导入的就是工作树代码。C 扩展缺失时回退 PyTracer（`worktree/coverage/collector.py:19-33`），不影响本题；唯一例外是环境里设了 `COVERAGE_TEST_TRACER=c` 却没有 C 扩展，这时一导入就 exit 1（`collector.py:24-32`） | `env_versions` |
| pytest 及插件 | `setup.cfg:1-2` 的 addopts 需要 pytest-xdist（`-n3`）、flaky（`--no-flaky-report`）、cacheprovider（`--failed-first`）；测试基类需要 `unittest_mixins`（`tests/coveragetest.py:19-22`、`tests/helpers.py:13`）；期望版本见 `requirements/pytest.pip:7-17`；`run_tests.sh:1` 用同一个 `setup.cfg` 跑判分测试，由此推断插件已装 | 没列已装包；只说 pip 有、无出网（`:11`） | 插件是否齐全、版本是多少都没验证；缺了也无法联网补装 | `pytest_version` |
| 分支覆盖测量 + JSON 输出（API） | 题面示例 `user_prompt.txt:10-18`；`control.py:99-104`、`:953-975` | 可写 `/tmp`（1 GiB）与 `/testbed`（`:12`）；不需要网络或外部服务 | 无；报告要限定到被测文件（`inorout.py:321-330`） | `repro_api_totals` |
| CLI 出口（`coverage run --branch` + `coverage json`） | `cmdline.py:374-388`、`:602-609`；数据文件用 `COVERAGE_FILE` 环境变量指定（`worktree/coverage/config.py:527`） | 同上 | 无 | `repro_cli_json` |
| 公开 JSON 测试 | `tests/test_json.py`（4 个用例） | 2 CPU / 4 GiB 够用；`-n3` 会起 3 个 xdist worker | 测试临时目录在 `$TMPDIR/coverage_test/`（`tests/coveragetest.py:85-88`）。`--failed-first` 默认把缓存写到 `/testbed/.pytest_cache`（被 `.gitignore:29` 忽略），命令里改写到 `/tmp` | `public_test_json` |
| `Numbers` 单测（只在改了 `results.py` 时有用） | `tests/test_results.py` | 同上 | 无 | `public_test_results` |
| 构建 | 不需要：改动是纯 Python，C 扩展与本题无关 | — | — | — |

命令如下（**建议，未执行**；都从 `/testbed` 以解题身份原样运行，只写 `/tmp`；与 `commands.json` 一致）：

1. `env_versions`（expect `zero`）

   ```bash
   cd /testbed && python -c "import sys, coverage; from coverage.collector import CTracer; print('python', sys.executable, sys.version.split()[0]); print('coverage', coverage.__version__, coverage.__file__); print('CTracer', 'available' if CTracer else 'unavailable (PyTracer fallback)')"
   ```

   预计看到 `/testbed/.venv/bin/python 3.7.9`，以及 `coverage 5.0.5a0 /testbed/coverage/__init__.py`；CTracer 两种状态都可以。修复前后相同。

2. `pytest_version`（expect `zero`）

   ```bash
   cd /testbed && python -m pytest --version 2>&1
   ```

   预计退出 0。pytest 4.x 会同时列出已注册插件，应能看到 xdist 与 flaky。如果报 `unrecognized arguments: -n3` 或 `--no-flaky-report`，说明插件缺失，后面两条 pytest 命令需要按公开依据加 `-o addopts=` 清空 ini 选项后再跑。修复前后无差别。

3. `repro_api_totals`（expect `nonzero`；能区分修复前后的主命令）

   ```bash
   cd /testbed && rm -rf /tmp/rh2_cov_json && mkdir -p /tmp/rh2_cov_json && printf "a = {'b': 1}\nif a.get('a'):\n    b = 1\n" > /tmp/rh2_cov_json/rh2_json_probe.py && PYTHONDONTWRITEBYTECODE=1 python -c "import json, sys; sys.path.insert(0, '/tmp/rh2_cov_json'); import coverage; print('coverage', coverage.__version__, coverage.__file__); cov = coverage.Coverage(branch=True, data_file='/tmp/rh2_cov_json/.coverage'); cov.start(); import rh2_json_probe as m; cov.stop(); cov.json_report(m, outfile='/tmp/rh2_cov_json/coverage.json'); r = json.load(open('/tmp/rh2_cov_json/coverage.json')); t = r['totals']; print('totals:', json.dumps(t, sort_keys=True)); print('file summaries:', json.dumps(dict((k, v['summary']) for k, v in r['files'].items()), sort_keys=True)); ok = t.get('covered_branches') == 1 and t.get('missing_branches') == 1; print('RESULT:', 'OK totals has covered_branches=1 missing_branches=1' if ok else 'BUG PRESENT'); sys.exit(0 if ok else 'FAIL: totals lacks covered_branches/missing_branches == 1')"
   ```

   - 修复前：`totals` 只有 7 个键（`covered_lines` 2、`excluded_lines` 0、`missing_lines` 1、`num_branches` 2、`num_partial_branches` 1、`num_statements` 3、`percent_covered` 60.0），打印 `RESULT: BUG PRESENT`，以 FAIL 信息退出，退出码 1。
   - 修复后：`totals` 另有 `covered_branches` 1、`missing_branches` 1，打印 `RESULT: OK ...`，退出码 0。
   - `file summaries` 一行只用来观察每文件 summary 是否也加了键（R7）。如果退出码非 0 却没打印 totals（例如 ImportError），那不是原 bug 现象。

4. `repro_cli_json`（expect `zero`；只看输出）

   ```bash
   cd /testbed && rm -rf /tmp/rh2_cov_cli && mkdir -p /tmp/rh2_cov_cli && printf "a = {'b': 1}\nif a.get('a'):\n    b = 1\n" > /tmp/rh2_cov_cli/rh2_cli_probe.py && export COVERAGE_FILE=/tmp/rh2_cov_cli/.coverage PYTHONDONTWRITEBYTECODE=1 && python -m coverage run --branch /tmp/rh2_cov_cli/rh2_cli_probe.py && python -m coverage json -o /tmp/rh2_cov_cli/coverage.json --include='/tmp/rh2_cov_cli/*' && python -c "import json; r = json.load(open('/tmp/rh2_cov_cli/coverage.json')); print('totals:', json.dumps(r['totals'], sort_keys=True)); print('file summaries:', json.dumps(dict((k, v['summary']) for k, v in r['files'].items()), sort_keys=True))"
   ```

   - 修复前：退出 0，totals 没有两键。
   - 修复后：退出 0，totals 含 `covered_branches` 1、`missing_branches` 1。
   - 如果第 3 条已出现两键而这里没有，说明新键是按配置 `branch` 而不是按 `has_arcs()` 门控的（R5）。

5. `public_test_json`（expect `zero`）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_json.py -rA -o cache_dir=/tmp/rh2_pytest_cache
   ```

   - 修复前：预计 4 passed。
   - 修复后：预计 `test_branch_coverage` 失败（原因见 §3.2），属预期；其余 3 个必须仍通过。如果它们也失败，说明非分支模式下也加了键，或改动了别的字段。

6. `public_test_results`（expect `zero`）

   ```bash
   cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/test_results.py -o cache_dir=/tmp/rh2_pytest_cache
   ```

   修复前后都应全部通过；只在解法改动了 `Numbers` 时有防回归意义。

## 5. 阅读范围

- **打开过的文件**：
  - 角色卡。
  - 公开包里的 `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
  - `worktree_manifest.json`：只用脚本看了顶层键、`initial_diff`、未跟踪文件清单和少量文件条目，没有打开它指向公开包以外的路径（例如 `initial_diff.source`）。
  - `worktree/` 下读了全文的：`run_tests.sh`、`setup.cfg`、`tox.ini`、`.gitignore`、`requirements/*.pip`、`coverage/jsonreport.py`、`coverage/results.py`、`coverage/report.py`、`coverage/version.py`、`coverage/__init__.py`、`tests/test_json.py`、`tests/conftest.py`、`tests/__init__.py`。
  - `worktree/` 下读了相关片段或 grep 结果的：`coverage/control.py`、`cmdline.py`、`config.py`、`inorout.py`、`collector.py`、`xmlreport.py`、`summary.py`、`html.py`、`env.py`、`misc.py`；`tests/coveragetest.py`、`tests/helpers.py`、`tests/test_results.py`、`tests/test_cmdline.py`、`tests/test_config.py`；`doc/branch.rst`、`doc/cmd.rst`、`doc/config.rst` 的 JSON 相关段落；`CHANGES.rst` 开头；`README.rst`；`igor.py`。
- **没查的范围**：`coverage/parser.py`、`sqldata.py`、插件相关模块、HTML 模板、`Makefile`、`lab/`、`perf/`、`ci/`、`.github/`，以及其余测试文件。
- **做过的检查**：没有运行任何项目代码、测试或容器。只在本机用 `bash -n` 和 Python `ast` 检查了命令语法，并确认 `printf` 生成的探针文件内容与公开夹具一致；这不等于在解题环境里执行过。
- **限制**：
  - `user_prompt.txt` 只是静态渲染，不等于模型实际收到的消息。
  - `worktree/` 不是完整的运行容器：不含 `.venv`、编译产物、`.git`、`install.sh` 和隐藏测试。
  - `environment_brief.md` 的实测信息是转述，本角色没有复核。
  - 本文件没有验证模型实际收到的消息、运行资源或开发条件。
