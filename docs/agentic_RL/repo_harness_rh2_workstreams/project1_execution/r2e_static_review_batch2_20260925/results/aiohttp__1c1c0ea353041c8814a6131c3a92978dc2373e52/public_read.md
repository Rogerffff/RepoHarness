# 公开读者报告：aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52

- 角色：R2E 公开读者（静态审查，不解题）。只读了角色卡和本题 `PUBLIC_DIR`。
- 路径约定：下文路径都相对 `PUBLIC_DIR`；`worktree/X` 就是解题容器里的 `/testbed/X`。
- 没有运行项目代码，没有联网，也没有看 git 历史。文中命令一律是"建议，未执行"。

## 概要

题面要求：`web.run_app()` 把应用内部的异常抛给调用者时，不要再把同一个异常另记一遍日志。

这条重复路径可以直接从 base 源码读出来：

1. `run_until_complete(main_task)` 已经把主任务的异常抛出（`worktree/aiohttp/web.py:518`）。
2. `finally` 仍然对这个已完成的主任务调用 `_cancel_tasks({main_task}, loop)`（`:522`）。
3. 这个函数对"没被取消、带异常"的任务调用 `loop.call_exception_handler(...)`（`:449-459`）。
4. 默认处理器把它以 ERROR 级别写进 `asyncio` logger。

其它结论：

- 题面没有泄露修法，示例在 base 接口下成立，复现不需要网络或端口。
- 主要开放点：有一类主任务异常只被记录、不会被抛出（Ctrl+C 后 cleanup 失败），题面没说它该怎么处理。

## 1. 需求表

| # | 需求 | 类别 | 依据 |
|---|---|---|---|
| R1 | 主任务（`_run_app`）以异常结束、`run_app` 把异常抛给调用者时，不再记录同一个异常。base 的记录途径是 `loop.call_exception_handler` → 默认处理器 → `asyncio` logger 的一条 ERROR 记录（带 traceback） | 明示 | 题面：`user_prompt.txt:26, 29`。代码：`worktree/aiohttp/web.py:518, 522, 449-459`。文档旁证：`worktree/docs/web_reference.rst:2984` 说 `run_app` "very similar to `asyncio.run`"，而 `asyncio.run` 只抛主协程的异常、不另外记录（这是 CPython 行为，不在工作树里） |
| R2 | 异常照旧从 `run_app()` 抛出，类型和对象不变；不能靠吞掉异常来消除重复 | 抛出是明示；"原样"是合理推知 | 题面：`user_prompt.txt:26`。公开测试：`worktree/tests/test_run_app.py:673-674`（`pytest.raises(RuntimeError)`） |
| R3 | 触发面不限于 `cleanup_ctx`。`on_startup` 处理器报错、`site.start()` 失败（例如 `create_server` 抛错）、应用协程工厂报错，都会让主任务失败并走同一段收尾代码，都应该不再重复记录 | 合理推知（题面只举了 cleanup_ctx 一例） | 代码：`worktree/aiohttp/web.py:321-322, 337, 421-422, 516-523`。公开测试：`worktree/tests/test_run_app.py:664-677` 正是 `create_server` 失败的例子 |
| R4 | 关停时，其它后台任务被取消时抛出的异常仍要经 `loop.call_exception_handler` 报告。消息文本和 context 字典（只有 `message`/`exception`/`task` 三个键）都不能变 | 公开测试明示 | 公开测试：`worktree/tests/test_run_app.py:826-856`（`exc_handler.assert_called_with(patched_loop, msg)` 按整个字典比较）。代码：`worktree/aiohttp/web.py:453-459` |
| R5 | 保持关停顺序：先单独取消主任务，让 cleanup 钩子在其它任务还活着时运行；再取消其余未完成的任务 | 合理推知，公开测试也覆盖 | 变更记录：`worktree/CHANGES.rst:2076`（#3805）。公开测试：`worktree/tests/test_run_app.py:793-823`；`TestShutdown`（`:909-1243`）里的 cleanup_ctx 在关停时还要 `await` 自己创建的任务 |
| R6 | Ctrl+C / SIGTERM（`KeyboardInterrupt`、`GracefulExit`）的正常退出路径不变：`run_app` 正常返回，进程退出码 0 | 公开测试 | 代码：`worktree/aiohttp/web.py:519-520`。公开测试：`worktree/tests/test_run_app.py:636-661` |
| R7 | 主任务在"被中断后再取消"的收尾阶段才抛出的异常，例如 Ctrl+C 之后 cleanup_ctx 在 `yield` 之后的代码报错，或 `runner.cleanup()` 失败。base 下 `run_app` 吞掉 `GracefulExit`/`KeyboardInterrupt` 后正常返回，这类异常**不会**被抛出，异常处理器写的日志是它唯一的报告 | 有多种合理解释（题面没覆盖） | 代码：`worktree/aiohttp/web.py:434-435, 519-523`，`worktree/aiohttp/web_app.py:575-590`。题面的 "raise without logging" 只适用于本来就会被抛出的异常。保守的读法是保留这类日志，否则错误会被悄悄丢掉。`worktree/docs/web_advanced.rst:1119` 的示例注释 "Ensure any exceptions etc. are raised." 也说明项目希望 cleanup 阶段的异常能被看到。把它们改成抛出属于题面之外的行为变化 |

## 2. 合理实现范围

**应接受的实现类别。** 下面只描述外部行为，不给修复代码：

- a. `run_app` 收尾时先看主任务是否已完成。
  - 已完成：结果或异常已经由 `run_until_complete` 交给调用者，就不再送进"取消并报告"的流程。
  - 未完成（被中断）：照旧先取消它、跑完 cleanup、报告 cleanup 里的异常。
- b. `_cancel_tasks` 只报告本次调用真正取消的任务，也就是调用 `cancel()` 时还没完成的任务。这对 `asyncio.all_tasks(loop)` 那次调用没有影响，因为它本来就只返回未完成的任务。
- c. `run_until_complete(main_task)` 抛出时记一个"主任务异常已经传出去"的标记，收尾时跳过对它的报告。
- d. 让主任务不以异常结束（例如 `_run_app` 把异常交回 `run_app`），由 `run_app` 在收尾之后自己抛出。

在题面场景下，这几类实现的外部行为相同：异常照抛，不调用异常处理器，`asyncio` logger 没有 ERROR 记录。区别在 R7：a/b/c 都会保留中断后 cleanup 失败的日志；d 要看写法，稍不注意，中断路径上 cleanup 的异常会变成没人看的返回值，被悄悄丢掉。

**不应接受、或会被公开测试拦下的做法：**

- 删掉 `_cancel_tasks` 里的 `call_exception_handler`，或者改用别的 logger：`test_run_app_cancels_failed_tasks`（`worktree/tests/test_run_app.py:826-856`）会失败。
- 改消息文本，或在 context 字典里增删键：同一个测试是按整个字典比较的。
- 用吞掉异常的方式"去重"：违反 R2，`worktree/tests/test_run_app.py:664-677` 会失败。
- 不再先单独取消主任务，把它和其它任务一起取消：违背 `CHANGES.rst:2076` 的设计理由。`TestShutdown` 很可能受影响（推断：cleanup_ctx 里 `await` 的任务会被提前取消，`test_task.exception()` 会抛 `CancelledError`）。
- 只在 `CleanupContext._on_startup` 这类具体触发点特殊处理：重复记录发生在 `run_app` 的收尾，不在触发点，这样改对其它路径无效（见 R3）。

**命名、输出、默认行为：**

- 题面不要求新增参数、公开 API、日志文本或输出格式。`run_app` 的签名（`worktree/aiohttp/web.py:462-482`）不用改。
- `_cancel_tasks` 是私有函数，只在 `web.py:522-523` 被调用，公开材料没有约定它的签名。
- 环境是 Python 3.9.21（`environment_brief.md:10`），仓库声明支持 `>=3.8`（`worktree/setup.cfg:45`）。3.11 才有的 `asyncio.Runner`、`Task.cancelling()` 等不能用。
- 仓库惯例要求 PR 在 `CHANGES/` 下加一个 towncrier 片段（`worktree/CHANGES/README.rst`）。解题者不知道 issue/PR 编号，这个片段不是修复的一部分，不应作为判分依据（推断）。

**没有约定的边角**（不同的合理实现结果不同，公开材料无法裁定）：

- 主任务自己以 `KeyboardInterrupt`/`GracefulExit` 结束：异常在任务协程内部抛出，随后被 `web.py:519-520` 吞掉。base 也会把它当成 "unhandled exception" 报告。修复后 a/b 不再报告，c/d 取决于写法。
- 评判测试用什么方式观测"是否记录"（mock 异常处理器、`caplog`，还是抓 stderr）未知。a/b/c 在这几种观测方式下结论一致。

## 3. 题面质量与初态线索

### 3.1 题面是否给出或强烈暗示修法

没有。

- 题面只描述行为（`user_prompt.txt:25-29`）。
- 示例（`:11-23`）是复现脚本，不是修好的实现。
- 题面没提到 `_cancel_tasks`、`call_exception_handler` 或 `main_task`。

定位提示比较强，但属于正常范围：

- 标题点名 `run_app()`，它就在 `worktree/aiohttp/web.py:462`。
- 复现时输出的日志文本 "unhandled exception during asyncio.run() shutdown" 可以 grep 回 `web.py:455`。
- 这段文本与 CPython `asyncio.runners` 里取消剩余任务时用的文本相同（CPython 知识，未在工作树核实），提示 `_cancel_tasks` 是照 `asyncio.run` 的收尾写的。

### 3.2 题面描述的行为能否从 base 源码读出

能读出来，调用链完整：

1. `run_app` 创建 `main_task = loop.create_task(_run_app(...))`（`web.py:494-514`）。
2. `_run_app` 先执行 `await runner.setup()`。这一步在 `try/finally` 之外（`web.py:337`）。
3. `BaseRunner.setup` 注册信号处理（`web_runner.py:279-285`），再调用 `_make_server()`（`:287`）。
4. `AppRunner._make_server` 调用 `self._app.startup()`（`web_runner.py:391`），发出 `on_startup` 信号（`web_app.py:445-450`）。
5. `CleanupContext._on_startup` 挂在这个信号上（`web_app.py:156-158`），它里面的 `await it.__anext__()`（`web_app.py:572`）抛出示例中的 `RuntimeError`。
6. 主任务以异常结束。`run_until_complete(main_task)` 把异常抛出（`web.py:518`），`except (GracefulExit, KeyboardInterrupt)` 不匹配。
7. `finally` 里执行 `_cancel_tasks({main_task}, loop)`（`web.py:522`）：
   - `cancel()` 对已完成的任务不起作用；
   - `gather(..., return_exceptions=True)` 立即完成；
   - `task.cancelled()` 为假、`task.exception()` 不为空，于是调用 `loop.call_exception_handler({...})`（`web.py:449-459`）。
8. 异常继续从 `run_app` 抛出。

为什么重复只来自第 522 行：

- 第二次调用 `_cancel_tasks(asyncio.all_tasks(loop), loop)`（`web.py:523`）不会再报告主任务，因为 `all_tasks` 只返回未完成的任务。
- `CHANGES.rst:2440`（#3497 "Ignore done tasks..."）和 `:2076`（#3805，主任务先取消）说明了第 522 行这次显式调用的来历。
- "默认处理器写进 `asyncio` logger ERROR"来自 CPython 3.9 的 asyncio 实现，不在工作树里，也没有在容器里核实。

题面措辞有几处小偏差，都不影响能否解题：

- "logged by `run_app()`"：真正写日志的是事件循环的默认异常处理器（`asyncio` logger），aiohttp 自己没有调用 `logging`。在 `web.py` 里 grep `logger` 找不到，要从 `call_exception_handler` 查起。
- "duplicate log messages"：直接跑示例脚本时，实际是 1 条 `asyncio` ERROR 日志，加上解释器打印的未捕获异常 traceback，也就是 stderr 上同一个 traceback 出现两次。只有调用者自己捕获并记录时，才是两条"日志"。
- "application context" 这个说法比实际机制窄（见 R3）。
- 题面没说 cleanup 阶段（`yield` 之后）抛出的异常怎么处理（见 R7）。

### 3.3 题面示例在 base 接口下是否说得通

说得通：

- `web.Application`、`Application.cleanup_ctx`（`web_app.py:386-387`）、`web.run_app` 都存在。
- `raise` 写在 `yield` 之前的异步生成器是合法写法，第一次 `__anext__` 就会抛出。
- `import asyncio` 没有用到，无害。
- 示例在 `runner.setup()` 阶段就失败，早于任何 `TCPSite` 的创建（`web.py:337` 对比 `:341-378`）。所以复现不需要绑定 8080 端口，也不需要网络。
- 默认 `handle_signals=True` 会调用 `loop.add_signal_handler`，必须在主线程运行；`python -` 和 `python -c` 都满足。

### 3.4 调查入口与缺失信息

- 公开材料足以定位：`worktree/aiohttp/web.py` 里的 `run_app` 和 `_cancel_tasks`。
- 仓库里有现成的验证写法：`worktree/tests/test_run_app.py` 的 `patched_loop` + `stopper` + `loop.set_exception_handler(mock.Mock())`（`:58-77, 826-856`）。
- 没有真正会阻碍开发的缺失信息。以下几点只需正常读代码：
  - `run_until_complete` 已经把主任务的结果交给了调用者；
  - `all_tasks` 不包含已完成的任务；
  - 为什么要先单独取消主任务（`CHANGES.rst:2076`）。

### 3.5 公开提示的三类内容（`public_bundle.json:15` 的 `public_hints`）

- **题目需求**：找到根因，修改非测试源码。
- **给解题者的操作指令**：
  - 不改仓库的测试文件；
  - 测试范围尽量窄；
  - 在 `/testbed` 用 `python -m pytest` 跑测试；
  - 完成后简短总结，停止调用工具。
- **环境事实声明**：
  - `/testbed/.venv` 是项目环境，并且 "`python` and the repo's test tools already point at it"；
  - 没有网络；
  - `pip` 可能不可用；
  - 由另一组测试评判。

对合法解法的影响：

- 最自然的修改位置是 `aiohttp/web.py`，"不改测试文件"不限制合法解法。
- "test tools already point at it" 如果和 `environment_brief.md:13` 的"裸 `pytest` 收集会失败"放在一起看，可能诱导解题者用裸 `pytest`。不过同一段提示也写明了用 `python -m pytest`，照提示做不会出问题。
- 关于 `pip` 的说法和 brief（"有 pip，但不能出网"）不冲突。

### 3.6 初态线索（都与题意无关）

- 未跟踪的 `worktree/run_tests.sh`（`... -m pytest -rA r2e_tests`）暴露了评判测试的目录名 `r2e_tests`。这个目录不在工作树里（见 manifest 的 `not_included`），不泄露测试内容。
- `install.sh` 和 `process_aiohttp_updateasyncio.py` 是镜像构建脚本。
- manifest 显示初态相对 base 只改了 `Makefile`。从现在的内容看，是 `uv pip` 之类的构建改写。这一点是推断：diff 原文的路径在 `PUBLIC_DIR` 之外，我没有打开。

## 4. 开发需求表

- 下面的命令都是**建议，未执行**，按原样在 `/testbed` 下运行。
- `cd /testbed` 之后，`python -`（从 stdin 读脚本）和 `python -m pytest` 都会把当前目录放进 `sys.path`，满足 `environment_brief.md:13` 要求的"`/testbed` 必须在 `sys.path` 上"。所以命令里没有设置 `PYTHONPATH`，也就不会覆盖镜像里可能已经设好的值。

| 操作/资产/服务 | 公开依据 | `environment_brief.md` 支持到哪一层 | 缺口 | 最小命令与预期 |
|---|---|---|---|---|
| 从源码树导入 aiohttp | `environment_brief.md:10, 13`；`worktree/aiohttp/__init__.py:1` | 写明了 Python 3.9.21、venv 路径、包没有装进 venv、`/testbed` 要在 `sys.path` 上 | 没写运行时依赖（multidict、yarl、frozenlist、aiosignal、aiohappyeyeballs、attrs、async-timeout）是否齐全。工作树按设计不含编译产物，看不出容器里有没有 C 扩展；从 `worktree/Makefile:91` 看，`.develop` 依赖空目录 `vendor/llhttp` 的 npm 构建，推断没有编译。aiohttp 对 C 扩展有纯 Python 回退（`helpers.py:466-471`、`http_parser.py:1019-1033` 等都捕获 `ImportError`），而本题只涉及纯 Python 的 `web.py` | 命令 E0：修复前后都打印 `3.10.6.dev0` |
| 复现并区分修复前后（主命令，看日志记录） | 题面示例 `user_prompt.txt:11-23`；代码 `web.py:516-525` | 只需要 Python 和主线程，不需要网络或端口 | "默认处理器写进 `asyncio` logger"属于 CPython 行为，未在容器核实 | 命令 E1。修复前输出两行：`raised: RuntimeError('Unexpected error occurred')` 和 `log records about the error: 1 ['asyncio: unhandled exception during asyncio.run() shutdown']`。修复后第一行不变，第二行变为 `log records about the error: 0 []` |
| 同一场景，换成公开测试的观测方式（loop 异常处理器） | `worktree/tests/test_run_app.py:846-856` | 同上 | 无 | 命令 E2。修复前后都先打印 `raised: RuntimeError('Unexpected error occurred')`。修复前接着打印 `exception handler calls: 1 ['unhandled exception during asyncio.run() shutdown']`，修复后是 `exception handler calls: 0 []` |
| 原样运行题面示例（数 stderr 上的 traceback） | `user_prompt.txt:11-23` | 同上 | 同上 | 命令 E3。修复前输出 `2`（asyncio 日志里一个 traceback，加上未捕获异常的 traceback）；修复后输出 `1` |
| 公开回归测试（窄范围） | `worktree/tests/test_run_app.py:664-677, 793-856`；`worktree/setup.cfg:118-139` | 写明要用 `python -m pytest`，裸 `pytest` 会失败 | brief 没列出装了哪些测试插件。`setup.cfg:133-134` 的 `--cov` 需要 pytest-cov，部分用例用到 `mocker`（pytest-mock）；`worktree/install.sh:6` 和 `worktree/requirements/test.txt:80-87` 表明它们应该已安装。`filterwarnings = error`（`setup.cfg:138-139`）会把测试期间的警告变成失败 | 命令 T1。修复前后预计都是 4 passed、其余 deselected，这 4 个是 `test_run_app_cancels_all_pending_tasks`、`test_run_app_cancels_done_tasks`、`test_run_app_cancels_failed_tasks`、`test_startup_cleanup_signals_even_on_failure`（各带 `[pyloop]`）。T1 不区分修复前后，只防回归：修法删掉后台任务的异常报告或改了 context 字典时，`test_run_app_cancels_failed_tasks` 会失败；修法吞掉异常时，`test_startup_cleanup_signals_even_on_failure` 会失败 |
| 整个公开测试文件（可选） | `worktree/tests/test_run_app.py` | 资源 2 CPU / 4 GiB（`environment_brief.md:12`） | `TestShutdown`（`:909-1243`）用真实的本机端口和 `ClientSession` 访问 `localhost`；`test_sigint`/`test_sigterm`（`:636-661`）会起子进程并发信号。没有外网时 loopback 应该可用，但未核实。这些用例每个都要 sleep 1–9 秒 | 命令 T2：预计全部通过，个别平台相关用例可能 skip/xfail，耗时几十秒（推断） |
| C 扩展、llhttp、npm | `worktree/Makefile:63-68, 91-93`；`vendor/llhttp` 是空目录 | 未提 | 本题不需要 | 无需操作 |

命令 E0（建议，未执行）：

```bash
cd /testbed && python -c "import aiohttp, aiohttp.web; print(aiohttp.__version__)"
```

命令 E1（建议，未执行）。这是主命令：只经过公开 API `web.run_app`，用默认异常处理器，并捕获所有 logging 记录。

```bash
cd /testbed && python - <<'EOF'
import logging
from aiohttp import web

records = []

class Collect(logging.Handler):
    def emit(self, record):
        records.append(record)

logging.getLogger().addHandler(Collect())

async def context(app):
    raise RuntimeError("Unexpected error occurred")
    yield

app = web.Application()
app.cleanup_ctx.append(context)
try:
    web.run_app(app, print=None)
except RuntimeError as exc:
    print("raised:", repr(exc))
else:
    print("raised: nothing")
hits = [
    r for r in records
    if (r.exc_info and isinstance(r.exc_info[1], RuntimeError))
    or "Unexpected error occurred" in r.getMessage()
]
print("log records about the error:", len(hits),
      [r.name + ": " + r.getMessage().splitlines()[0] for r in hits])
EOF
```

命令 E2（建议，未执行）。观测方式与 `test_run_app_cancels_failed_tasks` 相同：

```bash
cd /testbed && python - <<'EOF'
import asyncio
from aiohttp import web

async def context(app):
    raise RuntimeError("Unexpected error occurred")
    yield

app = web.Application()
app.cleanup_ctx.append(context)
loop = asyncio.new_event_loop()
calls = []
loop.set_exception_handler(lambda lp, ctx: calls.append(ctx))
try:
    web.run_app(app, loop=loop, print=None)
except RuntimeError as exc:
    print("raised:", repr(exc))
else:
    print("raised: nothing")
print("exception handler calls:", len(calls), [c.get("message") for c in calls])
EOF
```

命令 E3（建议，未执行）。原样运行题面示例，统计 stderr 上以这个异常结尾的 traceback 个数：

```bash
cd /testbed && python - 2>&1 <<'EOF' | grep -c '^RuntimeError: Unexpected error occurred'
import asyncio
from aiohttp import web

async def context(app: web.Application):
    raise RuntimeError("Unexpected error occurred")
    yield

app = web.Application()
app.cleanup_ctx.append(context)

web.run_app(app)
EOF
```

命令 T1 / T2（建议，未执行）：

```bash
cd /testbed && python -m pytest tests/test_run_app.py -k "cancels or even_on_failure"
cd /testbed && python -m pytest tests/test_run_app.py
```

## 5. 阅读范围

**实际打开过的内容：**

- 角色卡本身。
- `PUBLIC_DIR` 下的材料：
  - `user_prompt.txt`、`public_bundle.json`、`environment_brief.md`：读了全文。
  - `worktree_manifest.json`：只看了结构、`initial_diff`/`untracked_*`/`not_included` 这几个字段和文件权限，没有打开里面指向 `PUBLIC_DIR` 以外的路径（`initial_diff.source`，以及 `public_bundle.json` 的 `source`）。
- `worktree/` 下的源码：
  - `aiohttp/web.py`、`aiohttp/web_runner.py`：全文。
  - `aiohttp/web_app.py`：第 440-591 行，外加 grep。
  - `aiohttp/pytest_plugin.py`：第 40-80、140-265 行。
  - `aiohttp/test_utils.py`：第 545-600 行。
  - `aiohttp/helpers.py`、`aiohttp/http_parser.py`、`aiohttp/http_writer.py`、`aiohttp/http_websocket.py`：只看了 C 扩展回退的片段。
  - `aiohttp/__init__.py`：只看了版本行。
- `worktree/` 下的测试：
  - `tests/test_run_app.py`：第 1-106、625-1244 行，其余部分只看了 grep 结果。
  - `tests/conftest.py`：全文。
  - `tests/test_web_runner.py`：第 170-200 行。
- `worktree/` 下的构建与配置文件：
  - 全文：`setup.cfg`、`Makefile`、`install.sh`、`run_tests.sh`、`process_aiohttp_updateasyncio.py`、`requirements/dev.in`、`requirements/test.in`。
  - 只 grep：`requirements/test.txt`、`requirements/dev.txt`。
- `worktree/` 下的文档与变更记录：
  - `CHANGES/` 的文件列表，`CHANGES/README.rst` 前 60 行。
  - `CHANGES.rst`：grep 结果，以及第 1738-1748、2068-2082、2300-2312、2434-2444 行。
  - `docs/web_reference.rst`：第 1515-1560、2968-3108 行。
  - `docs/web_advanced.rst`：第 740-790、1040-1150 行。
- 对整个工作树 grep 了 `_cancel_tasks`、`call_exception_handler`、`set_exception_handler`、`run_app`、`caplog`。

**没查的范围：**

- `tests/test_run_app.py` 第 106-625 行（站点绑定类用例）只看了 grep 结果；其它测试文件没看。
- `aiohttp/web_protocol.py`、`aiohttp/web_server.py` 没看；`aiohttp/worker.py` 只 grep 了 `run`。
- `examples/`、`.github/`、`tools/` 没看。
- git 历史、上游仓库、`PUBLIC_DIR` 以外的任何路径都没查。没有联网，也没有运行任何命令做验证。

**限制：**

- `user_prompt.txt` 只是静态渲染，不是捕获到的模型请求。
- `worktree/` 不是完整的运行容器：缺 `.venv`、编译产物、`.git` 和隐藏测试。
- 本报告没有验证模型实际收到的消息、运行资源或开发条件。
- 下面这些结论依赖 CPython 行为，要等协调者在真实环境里照跑命令才能确认：
  - 默认异常处理器会写进 `asyncio` logger；
  - `python -` 会把当前目录放进 `sys.path`；
  - 上表列出的各项预期输出。

**上下文说明：** 会话启动时，宿主自动注入了项目级说明（`CLAUDE.md`、`AGENTS.md`、`CLAUDE.local.md`）和 git 状态快照。其中提到 B 线机器上有 aiohttp 的来源镜像和派生镜像 ID，但没有本题的 gold 补丁、隐藏测试、期望结果或旧的审查结论。我没有主动打开其中指向的任何文件。
