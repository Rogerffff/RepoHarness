# coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9：公开读者报告

- 角色：R2E 公开读者（静态审查，不解题）；2026-09-25。
- 依据：只读了角色卡和本题公开包。`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`worktree_manifest.json` 指公开包根目录下的文件；`coverage/...`、`tests/...`、`doc/...`、`setup.cfg` 等指 `worktree/` 下的文件。没有运行项目代码，没有联网。
- 题意概括：让 `Coverage._warn` 接受关键字参数 `once`，并让 `once=True` 的警告"只显示一次"。消除 `TypeError` 很直接；难点在于题面没有约定"什么算同一条警告"，这是本题最大的不确定项。

## 1. 需求表

| # | 需求 | 改变 / 保留 | 依据 | 确定性 |
| --- | --- | --- | --- | --- |
| R1 | `cov._warn(msg, slug=..., once=True)` 不再抛 `TypeError` | 改变 | 题面 `user_prompt.txt:7,13-14,21`；base 签名只有 `msg, slug=None`（`coverage/control.py:336`） | 明示 |
| R2 | 第一次 `once=True` 的警告照常输出：写到 stderr，格式沿用 `Coverage.py warning: <msg> (<slug>)`，开启 `debug=pid` 时加 `[pid]` 前缀 | 改变（新增）；格式保留 | 题面 `user_prompt.txt:18` 的 "displayed only once"；格式见 `coverage/control.py:346-350`；公开测试 `tests/test_api.py:510-516` | 可合理推知（题面没有给出输出文本） |
| R3 | 之后"重复"的 `once=True` 警告不再输出 | 改变 | 题面 `user_prompt.txt:18` | 要求本身是明示的，但"重复"的定义有多种解释（见 R4） |
| R4 | 去重键：按 `slug`、按消息文本，还是按（消息，slug） | — | 示例 `user_prompt.txt:13-14` 用同一个 slug、两条不同消息；期望行为 `user_prompt.txt:18` 写的是 "only once each ... preventing duplicate warnings" | **有多种合理解释**；两种读法在示例上的 stderr 不同（见 §2） |
| R5 | 不传 `once`（或 `once` 为假）的调用保持原样，每次调用都输出 | 保留 | 现有调用点都不传 `once`（`coverage/control.py:455,697,707`、`report.py:82`、`html.py:88`、`inorout.py:276,343,359,375,384,390`、`data.py:115`、`pytracer.py:230`、`ctracer/tracer.c:605`）；公开测试 `tests/test_api.py:371-384`（有新活动后 "No data was collected" 应再次出现）、`tests/test_process.py:784-810`（核对完整 stderr）、`tests/test_plugins.py:634-650`（"Disabling plug-in" 恰好一条） | 可合理推知（题面只说 "Warnings marked with `once=True`"） |
| R6 | `[run] disable_warnings` 仍按 slug 抑制，不受 `once` 影响 | 保留 | `coverage/control.py:341-343`；`tests/test_api.py:518-539`；`doc/config.rst:156-158` | 可合理推知 |
| R7 | `self._warnings` 继续记录每条已发出警告的原始消息（不带 slug） | 保留 | `coverage/control.py:207-208,345`；`tests/test_html.py:350-363`；`tests/test_oddball.py:130-136` | 可合理推知；被 `once` 抑制的重复警告要不要记入 `_warnings`，题面没说，有多种解释 |
| R8 | `_warn` 会作为回调传给 Collector / PyTracer / CTracer / CoverageData / InOrOut，调用方式是 `warn(msg)` 或 `warn(msg, slug=...)`；`msg` 必须仍是第一个位置参数，新参数必须可以省略 | 保留 | 回调注册 `coverage/control.py:437,468,485`；回调约定 `coverage/collector.py:90-92`；C 端单参数调用 `coverage/ctracer/tracer.c:605`；`coverage/data.py:112-115` | 可合理推知 |
| R9 | 以下三点题面都没约定：`once=True` 且 `slug=None` 怎么办；同一 slug 的 once 调用和非 once 调用混用怎么办；去重状态按 `Coverage` 实例保存还是全进程共享 | — | 题面没有提及 | 有多种解释 / 未说明 |

## 2. 合理实现范围

- **参数**：名字 `once` 由题面规定（`user_prompt.txt:7,13`）。自然的写法是在 `slug` 后面加一个默认值为假的可选参数。仓库仍声明支持 Python 2.7（`setup.py:7,28-29,122`），所以只有 Python 3 才支持的 keyword-only 写法（`*, once=False`）虽然能在 3.7 环境运行，但不符合仓库约定。这只是风格问题，不影响题意。
- **去重键（最关键的分歧）**：
  - 按 slug：示例的第二条（`Warning, warning 2!`）被压掉，stderr 只剩 `Coverage.py warning: Warning, warning 1! (bot)`。支持这种读法的公开依据有三条：一是示例刻意使用同一 slug、不同消息（`user_prompt.txt:13-14`）；二是仓库中"一条警告"的身份和现有抑制机制都以 slug 为键（`coverage/control.py:341`；`doc/config.rst:156-158` 把 slug 称作 "the name of the warning"）；三是很多警告消息带可变部分（模块名、文件名，见 `coverage/inorout.py:375,384,390`），按消息去重对这类警告不起作用。
  - 按消息（或按消息 + slug）：示例两条都显示，各显示一次。支持这种读法的公开依据也有三条：一是期望行为原文 "displayed only once each, preventing duplicate warnings"（`user_prompt.txt:18`），示例里两条消息不同，按字面不算 duplicate；二是 Python 标准库 `warnings` 模块的 `"once"` 动作就是按消息文本（和类别）只显示一次，仓库的 `tests/conftest.py:26` 正在使用这个动作；三是仓库里也有按具体对象去重的先例（`coverage/inorout.py:348-360` 按文件名对 already-imported 警告去重）。
  - 公开材料无法在两者之间做出裁决。还要注意：在题面示例上，"按消息去重"和"只接受参数、完全不去重"的输出一模一样（两条都显示）；只有"按 slug"会产生与"不去重"不同的输出。因此，如果隐藏测试直接检查示例的 stderr，两种合理读法中必有一种失败；如果隐藏测试只检查"不再抛 `TypeError`"，连不做去重的实现也能通过。这一点需要私有侧核对。
- **能区分"真去重"与"只收参数"的公开输入**：对完全相同的消息和 slug 连续两次 `once=True`，两种读法都要求只显示一次。
- **去重状态保存在哪里**：可以是实例属性（与 `_warnings` 并列，`coverage/control.py:207-208`），可以是懒初始化的集合或列表，也可以借用 `self.config.disable_warnings`。在单个实例上、中间不调用报告方法时，这几种做法对示例的表现相同。借用 config 有两点差别：
  - 会改变用户可见的配置：`cov.get_option("run:disable_warnings")` 的结果会变（`coverage/control.py:352-364`）；如果用户通过 `set_option` 传入了列表，改动会落到用户自己的列表对象上（`coverage/config.py:414-430`）。
  - 各报告方法会通过 `override_config` 临时换成配置的深拷贝，结束时还原（`coverage/control.py:46-58`、`coverage/config.py:333-335`）。报告过程中发出的 once 警告（例如 `report.py:82`、`html.py:88` 所在的路径）记下的状态会在报告结束后丢失。

  题面没有要求这些细节，是否被测试也不知道。
- **没有约定的边界情况**：
  - `once=True` 且 `slug=None`：这里有一个容易踩的坑。如果实现把 `None` 记为"已显示"，并对所有调用检查 `slug in 已显示集合`，那么之后所有不带 slug 的警告都会被连带压掉，例如 `coverage/control.py:455-463,707`、`html.py:88`、`data.py:115`、`inorout.py:276-278`、`ctracer/tracer.c:605` 发出的警告。
  - 同一 slug 的非 once 调用是否也要被压掉。
  - 被压掉的重复警告是否记入 `_warnings`。
  - 去重状态按实例保存还是全进程共享。
- **输出**：题面没有给出新的输出文本。自然的做法是复用现有格式，被抑制的调用不输出任何内容。
- **超出需求且有风险的扩展**：给现有调用点加 `once=True`。题面没有这个要求，而且会碰到两个问题：
  - 测试辅助 `tests/coveragetest.py:267` 里的假实现 `capture_warning(msg, slug=None)` 不接受 `once`。在 `assert_warnings` 下，凡是直接通过 `cov._warn` / `self._warn` 发出的警告，只要带上 `once` 就会抛 `TypeError`。例如把 `coverage/control.py:697` 改成 once，会让 `tests/test_api.py:364,377,381` 失败。
  - `tests/test_api.py:380` 的注释说明，设计上期望这条警告在有新活动后再次出现。
- **文档 / CHANGES 不是必需的**：`_warn` 属于私有 API（`coverage/control.py:76-78`）。回调约定的 docstring（`coverage/collector.py:90-92`）可以顺带更新，但不是必需。

## 3. 题面质量与初态线索

### 3.1 题面是否直接给出修法

- `user_prompt.txt:7` 直接点出了根因位置和参数名："the `_warn` method does not recognize the `once` keyword argument"。这等于告诉解题者去改 `coverage/control.py:336` 的签名，消除 `TypeError` 这一半几乎不需要调查。
- 示例代码是调用方代码，不是修好后的实现。去重怎么做、按什么键，题面都没有给出。

### 3.2 题面描述的报错能否从 base 源码读出

- 能。`coverage/control.py:336` 的签名是 `def _warn(self, msg, slug=None):`，传入 `once=True` 会在参数绑定时直接失败。CPython 3.7 的这类报错只写函数名、不写类名，所以消息应当就是 `_warn() got an unexpected keyword argument 'once'`，与 `user_prompt.txt:21` 一致（按报错格式推断，未执行；环境是 Python 3.7.9，见 `environment_brief.md:10`）。
- 仓库里没有任何代码、文档或测试使用或提到 `once` 参数。在 `coverage/`、`tests/` 中检索整词 `once`，只命中无关的注释和标识符（例如 `tests/test_oddball.py:158` 测试样例里名为 `once` 的函数）、`coverage/misc.py:112-129` 的 `expensive` 装饰器说明，以及 `tests/conftest.py:26` 的 `warnings.simplefilter("once", ...)`。可见标题和 "Actual Behavior" 把一个尚不存在的参数写成了 bug，实质是给私有方法新增功能。这对解题影响不大，但意味着期望行为只能来自题面三句话，仓库里没有可以对照的既有约定。

### 3.3 题面示例在 base 接口下是否说得通

- 说得通。`coverage.Coverage()`、`load()`（`coverage/control.py:391-401`）和 `_warn(msg, slug=...)` 都存在，只缺 `once`。示例省略了 `import coverage`，不影响理解。
- 示例里的 `cov.load()` 在 base 上是必要的。`_warn` 会调用 `self._debug.should('pid')`（`coverage/control.py:348`），而 `_debug` 在 `__init__` 中是 `None`（`coverage/control.py:217`），要到 `_init()` 才赋值（`coverage/control.py:253`）。如果不先调用 `load()` 或其它会触发 `_init()` 的方法，加了 `once` 之后示例仍会因 `AttributeError` 失败。公开测试 `tests/test_testing.py:121-125` 没调用 `load()` 也能执行 `cov._warn(...)`，是因为 `assert_warnings` 把 `_warn` 换成了假实现（`tests/coveragetest.py:267-274`）。
- 副作用：当前目录没有数据文件时，`load()` 会新建 SQLite 文件 `.coverage`（`coverage/sqldata.py:292-298,739-742`；该文件被 `.gitignore:8` 忽略）。直接在 `/testbed` 下跑示例会留下这个文件；如果 `/testbed` 里已经有不兼容的 `.coverage`，`load()` 会抛 `CoverageException`（`coverage/sqldata.py:266-283`）。

### 3.4 期望行为的缺口

- 去重键（R4）、边界情况（R9）、`_warnings` 是否记录被抑制的重复（R7）都没有说明，详见 §1、§2。其中只有去重键会直接改变示例的可观察输出。

### 3.5 `public_hints` 的三类内容（`public_bundle.json:15`）

| 提示要点 | 类别 | 与本题和环境的关系 | 对合法解法的影响 |
| --- | --- | --- | --- |
| "fixing a real GitHub issue in the repository checked out at /testbed (your bash tool already runs there)" | 环境事实声明（`/testbed`、bash 所在目录），外加来源说法 | `/testbed` 与 `environment_brief.md:10` 一致；R2E 题面是模型生成的，不是原始 issue，所以 "real GitHub issue" 的说法不准确 | 小：可能让解题者想去查 issue 编号或上游，离线环境里查不到；不影响修法 |
| "pre-activated conda env named `testbed`: `python`, `pip` and the repo's test tools already point at it" | 环境事实声明 | 与 `environment_brief.md:3-4,10-11` 不符：`python` 指向 `/testbed/.venv/bin/python`（3.7.9），pip 可用但不能出网；"test tools already point at it" 在公开材料里没有证据 | 小：`conda activate testbed` 之类的命令会失败；直接用 `python` 不受影响 |
| "Explore the code, find the root cause, and edit NON-TEST source files" | 题目需求 + 操作指令 | 与本题一致：修复点在 `coverage/control.py` | 把改动限定在非测试文件；本题的最小修复本来就不需要改测试 |
| "Do NOT modify test files: grading resets the test files ... test edits never count" | 操作指令 + 机制声明 | 这条机制声明不是本来源的实际机制；公开的 `run_tests.sh:1` 显示评分运行的是 `r2e_tests`，而它不在工作树里 | 指令本身禁止解题者修改 `tests/coveragetest.py:267` 的假 `_warn`。若解题者给现有调用点加 `once=True`，这个假实现会抛 `TypeError`，指令又不允许改它，所以最稳妥的做法是不把改动扩散到调用点（见 §2） |
| "keep runs narrow (a single test file or module)" | 操作指令 | 与 2 CPU / 4 GiB 的资源相符；但 `setup.cfg:2` 的默认 addopts 带 `-n3` | 没有负面影响 |
| "reply with a short summary and stop calling tools" | 操作指令 | — | 无 |

另外，`user_prompt.txt` 本身只有一行抬头和 issue 正文，不含上面这些提示。解题者实际有没有收到 `public_hints`、在什么位置收到，公开包里看不出来。

### 3.6 初态线索

- 根据 `worktree_manifest.json`：`initial_diff` 为 0 字节，所以工作树就是 base 提交 `8240c58c90a0...` 的 323 个跟踪文件，加上未跟踪的 `run_tests.sh`。镜像里还有 `install.sh`，但它不在公开包中（列在 `untracked_missing`）。
- `run_tests.sh:1` 就是评分命令：`.venv/bin/python -W ignore -m pytest -rA r2e_tests`。`r2e_tests/` 不在工作树（manifest 的 `not_included` 写明不含隐藏测试）。解题者在 `/testbed` 能看到这个脚本，但没法用它来验证。
- 版本是 `5.0.2a1`（`coverage/version.py:8`）。`CHANGES.rst:25-33` 的 Unreleased 部分只有 issue 890，与本题无关。

### 3.7 调查入口与容易误导的地方

- 入口清楚：检索 `_warn` 就能找到定义和全部调用点。`tests/coveragetest.py:249-297` 的 `assert_warnings`，以及 `StdStreamCapturingMixin` 提供的 `self.stderr()`（用法见 `tests/test_api.py:510-539`），展示了本仓库怎样测试警告，解题者可以照此写临时验证。
- 容易误导：`tests/test_api.py:357` 的 `test_two_getdata_only_warn_once` 名字里有 "warn_once"，但它测的是另一个机制：没有新活动时，`get_data()` 不再进入 `_post_save_work`（`coverage/control.py:678-679`、`coverage/collector.py:411-420`）。它与 `once` 参数无关。
- 有些判断需要读调用者才能做出，例如 R8 的回调兼容和 `override_config` 的深拷贝。这属于正常读代码，不算题面缺陷。

### 3.8 哪些缺失会真正阻碍开发

- 真正阻碍的只有一项：去重键无法从公开材料确定，而它决定了示例的可观察输出（§2）。
- 不构成阻碍的：环境依赖是否齐全，只影响跑公开测试方不方便；复现和验证示例只需要标准库和仓库源码。其它未约定的细节属于正常的设计选择。

## 4. 开发需求表

下列命令一律是**建议，未执行**；"预计现象"来自阅读推断，没有经过验证。

| 操作 / 资产 / 服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 命令 |
| --- | --- | --- | --- | --- |
| 定位代码 | `user_prompt.txt:7` 点名 `_warn` | `/testbed` 可写，有 bash（第 10-12 行） | 无 | C1 |
| 复现原 bug / 验证新行为 | 示例 `user_prompt.txt:10-15`；报错 `user_prompt.txt:21` | 到解释器层：Python 3.7.9 venv（第 10 行） | `coverage` 在 venv 中以什么方式安装，公开包看不出（`install.sh` 缺失）；`load()` 会在当前目录建 `.coverage` | C2、C3 |
| 回归：旧行为 | `coverage/control.py:341-350`；`tests/test_api.py:498-539` | 同上 | 无 | C4 |
| 公开测试（窄范围） | `tests/test_api.py:357-384,498-539`；`tests/test_testing.py:120-180`；`tests/test_html.py:343-366,1122-1128` | 只说明"有 pip、不能出网"（第 11 行） | 测试依赖是否已装未知：`requirements/pytest.pip:7-17` 列了 pytest 4.6.6、pytest-xdist、flaky、mock、hypothesis、unittest-mixins；`setup.cfg:2` 的 addopts 含 `-n3 --no-flaky-report --failed-first`，缺插件时会直接报参数错误 | C5 |
| 进程级测试（可选） | `tests/test_process.py:784-810` | 未说明 | 子进程用 `PATH` 上的解释器（`tests/coveragetest.py:398-404`），而 `PYTHONPATH` 只加了 `tests/modules` 和 `tests/zipmods.zip`（`tests/coveragetest.py:425-437`），所以要求 `coverage` 已装进 venv，这一点未知 | C6 |
| 评分脚本 | `run_tests.sh:1` | 不支持：隐藏测试不在工作树 | `r2e_tests/` 缺失 | C7 |
| C 扩展 `coverage/tracer*.so` | `.gitignore:6`；导入失败时回退到 PyTracer（`coverage/collector.py:19-31`） | 未说明 | 镜像里是否已编译未知 | 本题不需要：`_warn` 与追踪器无关 |
| 外部服务 / 网络 | 无 | 不能出网 | 本题不需要 | — |
| 资源 | 2 CPU / 4 GiB，`/tmp` 1 GiB（第 12 行） | — | `setup.cfg:2` 的 `-n3` 默认会起 3 个 xdist worker | 用 `-o addopts=""` 以单进程运行（见 C5） |

- **C1 定位**：`cd /testbed && grep -rn "_warn\b" coverage tests/coveragetest.py`
  预计命中：定义 `coverage/control.py:336`；作为回调传出的 `coverage/control.py:437,468,485`；假实现 `tests/coveragetest.py:267-274`。
- **C2 复现**：`cd "$(mktemp -d)" && PYTHONPATH=/testbed python -c 'import coverage; cov = coverage.Coverage(); cov.load(); cov._warn("Warning, warning 1!", slug="bot", once=True); cov._warn("Warning, warning 2!", slug="bot", once=True)'`
  预计 base：traceback 最后一行是 `TypeError: _warn() got an unexpected keyword argument 'once'`，没有任何 `Coverage.py warning:` 行。修复后：不再抛异常，stderr 有 `Coverage.py warning: Warning, warning 1! (bot)`；`Warning, warning 2! (bot)` 是否出现取决于 R4 的去重键。在临时目录里运行，是为了不在 `/testbed` 留下 `.coverage`。
- **C3 区分"真去重"与"只收参数"**：`cd "$(mktemp -d)" && PYTHONPATH=/testbed python -c 'import coverage; cov = coverage.Coverage(); cov.load(); cov._warn("dup", slug="bot", once=True); cov._warn("dup", slug="bot", once=True); print(cov._warnings)'`
  预计修复后：无论哪种读法，`Coverage.py warning: dup (bot)` 都只出现一次；`_warnings` 是 `['dup']` 还是 `['dup', 'dup']` 题面没有约定。只收参数、不去重的实现会输出两行。
- **C4 旧行为**：`cd "$(mktemp -d)" && PYTHONPATH=/testbed python -c 'import coverage; cov = coverage.Coverage(); cov.load(); cov._warn("a", slug="x"); cov._warn("a", slug="x"); cov.set_option("run:disable_warnings", ["y"]); cov._warn("b", slug="y"); print(cov._warnings)'`
  预计 base 和修复后相同：两行 `Coverage.py warning: a (x)`，没有 `b (y)`，stdout 打印 `['a', 'a']`。
- **C5 公开测试**：
  - `cd /testbed && python -m pytest -o addopts="" -p no:cacheprovider -q tests/test_api.py tests/test_testing.py -k warn`
  - `cd /testbed && python -m pytest -o addopts="" -p no:cacheprovider -q tests/test_html.py -k "dotpy_not_python_ignored or no_contexts_warns"`

  预计 base 和修复后都通过：第一条约 6 个用例，第二条 2 个，都不涉及 `once`。`-o addopts=""` 用来清掉 `setup.cfg:2` 的 addopts，这样不依赖 xdist / flaky 插件，并且只起一个进程。如果报 `ModuleNotFoundError: No module named 'unittest_mixins'` 之类的错误，说明镜像缺测试依赖；不能出网，所以补不上。这属于环境问题，不是修复问题。
- **C6 进程级**：`cd /testbed && python -m pytest -o addopts="" -p no:cacheprovider -q tests/test_process.py -k run_twice`
  预计通过（前提是子进程能 `import coverage`）；只要不改现有调用点，修复就不会影响这个用例。
- **C7 评分脚本**：解题时不建议运行 `bash run_tests.sh`。预计 pytest 会因找不到 `r2e_tests` 而报错退出（推断）。

## 5. 阅读范围与限制

**实际打开的文件**（`worktree/` 下的文件省略前缀）：

- 全文读过：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`、`run_tests.sh`、`coverage/control.py`、`tests/conftest.py`、`tests/__init__.py`、`setup.cfg`、`.gitignore`、`requirements/*.pip`。
- `worktree_manifest.json`：用本机 `python3` 只读解析，打印了除逐文件哈希以外的全部顶层字段。没有打开其中 `initial_diff.source` 指向的公开包外路径。
- 读过片段：
  - `coverage/` 下：`config.py`（160-260、333-335、354、414-440）、`sqldata.py`（180-310、735-760）、`report.py`（60-86）、`html.py`（78-95）、`data.py`（95-120）、`inorout.py`（255-400）、`pytracer.py`（220-236）、`collector.py`（19-31、84-106、411-429）、`ctracer/tracer.c`（590-612）、`misc.py`（53-67、108-129）、`version.py`（1-33）。
  - `tests/` 下：`coveragetest.py`（1-320、372-440）、`test_testing.py`（1-200）、`test_api.py`（1-40、330-560）、`test_html.py`（330-370）、`test_oddball.py`（110-140）、`test_process.py`（700-715、776-812、915-935）、`test_plugins.py`（610-660）。
  - 其它：`CHANGES.rst`（1-80）、`doc/cmd.rst`（120-195）、`doc/config.rst`（150-165）。
- 只看了检索命中行：`coverage/env.py`、`setup.py`、`tox.ini`、`Makefile`、`igor.py`、`howto.txt`。
- 在 `coverage/`、`tests/` 中做过的检索：`_warn`、`warn=`、整词 `once`、`disable_warnings`、`Coverage.py warning`、`self.stderr()`、`cov.load()`、`COVERAGE_TEST_TRACER`、`COVERAGE_TESTING`、名字含 `warn` 的测试。

**其它文件操作**：对 OUTPUT 只用 `test -d` / `test -e` 检查了目录和文件是否存在，没有列出结果目录，也没有读其中任何文件；然后写入本文件。

**没查的范围**：
- 工作树内：其余测试文件和其余 `coverage/` 模块（只看了检索命中）、`lab/`、`perf/`、`ci/`、`doc/` 的大部分、`tests/gold/`、`tests/modules/`。
- 公开包里本来就没有的：`install.sh`、隐藏测试 `r2e_tests/`、`.venv`、编译扩展。
- 公开包以外的任何路径、上游仓库历史、网络资料。

**限制**：
- `user_prompt.txt` 只是静态渲染，不是模型实际收到的消息；`public_hints` 是否送达解题者、以什么形式送达，都不知道。
- `worktree/` 不是完整的运行容器：没有 `.venv`、编译扩展、`install.sh` 和隐藏测试。Python 版本、pip、资源等环境事实只来自 `environment_brief.md`。本文不声称模型实际消息、运行资源或开发条件已经验证。
- 上面的命令都没有执行；报错文本、测试是否通过、用例个数都是阅读推断。

**先验知识声明**：审查者是语言模型，训练中可能见过 coveragepy 上游的公开代码及其后续版本。本报告的判断只引用工作树内的文件和行号，没有查上游历史。§1 R4 与 §2 对去重键的分析，只依据题面示例的结构、题面措辞和本仓库现有的抑制机制。请私有侧独立核对，不要把它当作与上游无关的独立证据。
