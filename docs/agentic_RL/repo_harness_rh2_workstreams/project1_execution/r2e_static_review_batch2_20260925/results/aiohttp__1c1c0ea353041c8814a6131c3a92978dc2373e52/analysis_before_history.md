<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# 私有主审分析（读历史前）：aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52

2026-09-25 · R2E 私有主审（静态）· 本稿在打开任何历史调查之前保存。

- 读过的材料：角色卡、四份方法文档、公开包与 `public_read.md`、私有包、`run_refs.json` 指向的原始账本与 eval 日志、devcheck 目录、跨题比对文件、同仓其它题的公开包。
- 没做的事：没有运行项目代码或容器；没有读任何历史调查或汇总文件。

## 0. 暂定处置

- **题目**：主任务以异常结束时，`run_until_complete(main_task)` 已经把异常抛给调用者。base 的 `finally` 又调用 `_cancel_tasks({main_task}, loop)`（`aiohttp/web.py:522`），经 `loop.call_exception_handler` 把同一个异常再报告一次。要求改成只抛出、不报告。
- **评分构成**：期望共 56 键，全部是 PASSED。
  - 唯一目标键是 `test_run_app_raises_exception[pyloop]`，就是题面示例，只是消息改成 `"foo"`。
  - 另外 55 键与公开的 `tests/test_run_app.py` 逐字相同，agent 可以在本地全部跑一遍。devcheck 实测 55 passed，用时 26.9 s。
- **暂定处置**：本题可以作为开发诊断用的静态候选，状态 `needs_review`（静态候选，待 actor 验证），不需要修订材料。另记两件事：
  1. 次要漏测：Ctrl+C 之后 cleanup 抛出的异常，没有任何键检查。候选如果把这类异常静默吞掉（既不抛出也不报告），仍能得 1。这是下文的 C3，目前只是源码推断。
  2. 跨题包含：`aiohttp__22a12cc2…` 的公开工作树里逐字包含本题的 gold、目标测试和 changelog，划分数据集时要同组处理。
- **最关键的未知项**：C3 在正式评分下的实际得分（推断为 1，待实跑）；真实模型收到的消息；非 gold 候选的真实交付（这两项属 actor 待验）。

## 1. 八方面覆盖

| 方面 | 已查 | 未查 / 缺口 |
|---|---|---|
| 公开需求 | 题面、`public_hints`、`public_read` 的 R1–R7；核对了 base 的 `web.py:300-525`、`web_app.py:156-158, 461-468, 564-590`、`web_runner.py:276-319` | 题面没说 Ctrl+C 之后 cleanup 抛错该怎么处理（R7，有歧义） |
| 材料与初态 | 私有包各文件的 sha256 与 grading / validation bundle 一致；eval 日志的 `RH2_SETUP_HIDDEN_TESTS_TREE`、`RH2_SETUP_ENTRY_SHA256` 也与材料一致；devcheck 实测 HEAD=`87342c79`，初态为 ` M Makefile` 加 3 个未跟踪文件；noop 只错目标键，失败位置 `test_1.py:923` | — |
| 测试是否测到要求 | 目标测试逐行追到 fixture 与断言；隐藏测试与公开测试 diff 后，只多目标测试和一个 import；R4/R5/R6 对应的键已追 | R3（示例以外的失败路径）只执行、不断言；R7 没有键 |
| 是否误拒合理解 | 静态推断 C1、C2 都得 1；"不调用 `call_exception_handler`"这一观测方式有公开依据 | 候选尚未实跑 |
| 回归与 gold | gold 满足 R1–R6；R7 行为从"报告"改成了"抛出"；没有无关改动 | C3 那种静默吞错的回归没有键保护 |
| 开发条件 | devcheck 以 agent 身份（uid 54321）、真实 Claude Code 2.1.205 加桩端点运行，复现命令和公开测试的结果全部符合预期；私有 gold 对照三条复现命令的结果是 0/0/1 | 真实题面消息没有捕获（devcheck 用的是桩提示）；gold 没有在 agent 身份下跑过（私有对照是 root） |
| 交付与评分边界 | 修复落在非测试源码 `aiohttp/web.py`；grader 删掉 `r2e_tests` 后再放入隐藏测试；跑测试不改变 git status（`.coverage` 在 `.gitignore` 里，跑完仍是 4 行） | 没有非 gold 候选经冻结 / 投影的真实交付证据；隐藏测试用到的包内辅助（`aiohttp/test_utils.py`、`aiohttp/pytest_plugin.py`）候选可以改，这是 R2E 共性 |
| 题目关系与用途 | 已核对跨题比对：22a12cc2 包含本题 gold、目标测试和 changelog；4075c653（3.9.0b0）的 base 仍有此 bug；另外两道 aiohttp 题版本很老，无关 | 没查其它仓库 |

## 2. 目标键展开：`test_run_app_raises_exception[pyloop]`

位置：隐藏 `test_1.py:909-923`。

- **fixture**：`patched_loop`（`:58-67`）就是 aiohttp pytest 插件的 `loop`（参数 `[pyloop]`），把 `create_server`/`create_unix_server` 换成 mock 协程，并 `set_event_loop`。
- **输入**：`cleanup_ctx` 里放一个异步生成器，它在 `yield` 之前就 `raise RuntimeError("foo")`。这与题面示例一致。
- **调用链**：`web.run_app(app, loop=patched_loop)`，`print` 和 `handle_signals=True` 都用默认值。
  1. `runner.setup()`（`web.py:337`，位于 try/finally 之外）。
  2. `_make_server` → `app.startup()` → `CleanupContext._on_startup`（`web_app.py:569-573`）抛出 `RuntimeError`，主任务失败。
  3. `run_until_complete` 把异常抛出。
  4. base 的 `finally` 执行 `_cancel_tasks({main_task})`，其中调用 `call_exception_handler`（`web.py:449-459`）。
- **断言**：
  1. `pytest.raises(RuntimeError, match="foo")`：异常照常抛出（R2）。
  2. 在整个 `run_app` 期间，`patched_loop.call_exception_handler`（autospec mock）一次都没被调用（R1）。
- **公开依据**：
  - 题面 Expected 写的是 "raise the exception without logging it"。
  - 读 base 源码可知，`run_app` 唯一的报告途径就是 `call_exception_handler`。
  - 公开测试 `test_run_app_cancels_failed_tasks` 也是用异常处理器来观测报告的。
- **执行证据**：noop 失败在 `test_1.py:923 assert not m.called`，此时 `m.called` 为 True，而 `pytest.raises` 已经通过，正对应"既抛出又报告"。7 次 noop 都是这个失败，7 次 gold 都通过。

## 3. 需求—断言双向表

| 公开要求 / 合理旧行为 | 依据 | 键 / 决定性断言 | 覆盖 | 执行证据 |
|---|---|---|---|---|
| R1 已经抛出的主任务异常不再报告（示例路径） | 题面 Expected；`web.py:518, 522, 449-459` | 目标键 `assert not m.called` | 覆盖 | noop 7 次 FAILED，gold 7 次 PASSED；devcheck 三条复现命令 base 为 1/1/2，gold 为 0/0/1 |
| R2 照常抛出，类型和消息不变 | 题面；公开 `test_run_app.py:664-677` | 目标键 `pytest.raises(..., match="foo")`；`test_startup_cleanup_signals_even_on_failure` 的 `pytest.raises(RuntimeError)` | 覆盖 | 同上 |
| R3 其它失败路径（`site.start()`/`create_server` 失败、`on_startup` 失败）也不重复报告 | 合理推知（题面只举了 cleanup_ctx 一例） | `test_startup_cleanup_signals_even_on_failure` 走的是 create_server 失败路径，但**不断言**是否报告 | 部分 | noop 日志在该键下有 `ERROR asyncio … unhandled exception during asyncio.run() shutdown`，gold 日志没有。10 份加跑日志里，noop 各有 2 处，gold 各有 1 处 |
| R4 后台任务的异常照常报告，消息和 context 字典不变 | 公开 `test_run_app.py:826-856` | `test_run_app_cancels_failed_tasks` 的 `exc_handler.assert_called_with(loop, msg)` | 覆盖 | noop 与 gold 都 PASSED；gold 日志里仍有后台任务 `InvalidStateError` 的报告 |
| R5 先单独取消主任务，cleanup 运行时其它任务仍然活着 | `CHANGES.rst:2076`（#3805）；公开的 TestShutdown | TestShutdown 的 8 个键（`finished is True`、`test_task.exception() is None` 等） | 覆盖（间接） | 两侧都 PASSED |
| R6 Ctrl+C / SIGTERM 时正常返回，退出码为 0 | 公开 `:636-661` 以及用 stopper 的用例 | `test_sigint`/`test_sigterm` 的 `proc.wait() == 0`；另外 40 多个 stopper 用例要求正常返回 | 覆盖 | 两侧都 PASSED |
| R7 Ctrl+C 之后 cleanup 抛出的错误不能被静默丢掉（base 报告它，gold 抛出它） | 题面宽读 "should raise"；base 的旧行为；`docs/web_advanced.rst:1119` | 无 | 缺失 | — |
| 异常路径下 loop 也要关闭 | 公开 `test_run_app_close_loop`（只测正常路径） | 只有正常路径 | 部分 | — |

反向核对：

- 目标键的两条断言都能追到题面。
- 其余 55 键就是公开测试文件本身，依据就是公开测试。
- 没有发现题面之外的要求，例如精确字符串、内部 helper 名或调用顺序。

## 4. R2E 专项

**(a) 期望中的非 PASSED 键**

- 期望里没有 FAILED/ERROR 键（56 键全是 PASSED），所以不存在"更完整的修复把失败键翻成 PASSED，反而判 0"的情况。
- 反方向：只有改 `aiohttp/pytest_plugin.py` 这类文件才会改变收集结果或参数化，正常修法不会碰。

**(b) 题面描述的现象是否出现在 noop 失败原因里**

一致。

- noop 目标键失败在 `assert not m.called`，在此之前 `pytest.raises` 已经通过，也就是"既抛出又报告"。
- 同一路径在日志里的实际输出是 `ERROR asyncio … unhandled exception during asyncio.run() shutdown`，见 `test_startup_cleanup_signals_even_on_failure` 的捕获日志。
- devcheck 以 agent 身份运行题面示例：stderr 上有 2 个 traceback，打上 gold 后只剩 1 个。

**(c) 题面是否泄漏修法**

没有。

- 题面只描述行为；标题点名 `run_app()`，属于正常的定位提示。
- 工作树里没有本修复的 changelog（grep `6807` 和 `raised regardless` 都没有结果）。
- git 没有 remote、refs 或 reflog，HEAD 没有子提交（devcheck 预检与 probe facts）。

**(d) 搬迁伪影与测试辅助**

- 隐藏目录只有三个文件：`test_1.py`、与公开 `tests/conftest.py` 逐字相同的 `conftest.py`、空的 `__init__.py`。
- 只有一个测试文件，不存在跨文件撞键；56 个键各不相同。
- 隐藏测试不导入 `tests/` 下的辅助代码，只用包内的 `aiohttp.test_utils.make_mocked_coro` 和 `aiohttp.pytest_plugin`。候选可以改这两个文件，评分时也不会重置，这是 R2E 共性，正常修法不碰。
- `test_sigint`/`test_sigterm` 用 `-c` 起子进程，要求 cwd 为 `/testbed` 才能导入 aiohttp。grader 的 `run_tests.sh` 满足这个条件。

**(e) 时间、资源、环境敏感的键**

- **TestShutdown 的 8 个键**：
  - 用真实的回环端口和 `ClientSession`，配合 0.1–9 秒不等的 sleep 与超时，余量大约在 0.1–1 秒量级。
  - 例子：`test_shutdown_new_conn_rejected` 里处理器 sleep 9 s，对应 `shutdown_timeout=10`；`test_shutdown_handler_cancellation_suppressed` 要求 0.4 s 的客户端超时发生在 0.5 s 的 PRESTOP 之前。
  - 实测：在 2 CPU / 4 GiB 下，14 次评分（7 次 noop、7 次 gold）和 devcheck 两次全文件运行都通过，同一个键的耗时差不超过 0.01 s。
  - 这些键对所有候选的影响方向相同：一旦出问题，只会造成假阴性。高并发下没有测过。
- **环境敏感的键**：
  - `test_run_app_preexisting_inet6_socket` 需要容器能绑定 `::1`；`test_run_app_abstract_linux_socket` 需要支持抽象 Unix 套接字。
  - 两者在当前的 grader 和 actor 容器里都通过。
  - 如果换沙箱配置（例如关掉 IPv6），这两个键会变成 FAILED 或 SKIPPED，所有候选（包括 gold）都会判 0。
- **固定路径**：`test_run_app_preexisting_unix_socket` 绑定 `/tmp/test_preexisting_sock1`。评分每次用新容器，目前没有影响。

**(f) 材料修订**

`revisions.json` 为 `[]`，没有修订，本项不适用。

## 5. gold 检查

- **改动内容**：
  - `aiohttp/web.py` 新增 `from contextlib import suppress`。
  - `finally` 里把 `_cancel_tasks({main_task}, loop)` 换成 `main_task.cancel()` 加 `with suppress(asyncio.CancelledError): loop.run_until_complete(main_task)`，其余收尾代码移进内层 `finally`。
  - 没有无关改动。来源提交里另有 `CHANGES/6807.bugfix.rst` 和测试改动，已按规则剔除（见 M3 `gold_meta`）。
- **原例已修好**：
  - devcheck 私有 gold 对照（root，同一张派生镜像 `bd9b7c27…`）：pr1 的日志记录数为 0，pr2 的处理器调用数为 0，pr3 的 traceback 数为 1。
  - 评分侧 7 次 gold 都是 56/56。
- **R3**：gold 在 `run_app` 这一层修复，所以 create_server 失败路径上的重复报告也消失了。这是日志证据，没有断言保护。
- **R4/R5/R6**：都保留了。对应键在两侧都是 PASSED，后台任务的 `InvalidStateError` 也仍被报告。
- **R7（没有测试覆盖的行为变化）**：
  - Ctrl+C 之后 cleanup 抛出错误 X 时，X 不在 `suppress(CancelledError)` 的范围内，gold 会重新抛出 X，`run_app` 因此抛出 X，而不是正常返回。
  - base 的做法是报告 X，然后正常返回。
  - gold 的行为符合题面的宽读（"should raise"），但超出了示例范围。由于没有键约束，保守修法（继续报告）也不会被扣分。
- **另一个边角**：如果主任务协程内部自己抛出 `KeyboardInterrupt`/`SystemExit`，gold 会在 `finally` 里再抛一次。示例和测试都不涉及这种情况。
- **判断**：gold 与公开要求相符，没有发现漏修或依赖未交付的改动。

## 6. 候选（供协调者用正式评分实跑）

所有改动都在 `aiohttp/web.py` 中 `run_app` 的 `finally` 块。

| 编号 | 改法 | 预期得分 | 与 gold 结果不同的键 | 用途 |
|---|---|---|---|---|
| C1 合理替代 | 把 `_cancel_tasks({main_task}, loop)` 改成 `if not main_task.done(): _cancel_tasks({main_task}, loop)`，其余不动 | 1 | 无 | 验证不会误拒。它在 R7 上保留 base 的"报告"语义，与 gold 的"抛出"不同 |
| C3 可能蒙混 | 把这一行换成 `main_task.cancel(); loop.run_until_complete(asyncio.gather(main_task, return_exceptions=True))`，或者换成 `with suppress(BaseException): loop.run_until_complete(main_task)` | 1（源码推断） | 无 | 确认漏测：Ctrl+C 之后 cleanup 抛出的异常既不抛出也不报告。另配一个诊断脚本（不计入 reward），见表后说明 |
| C5 常见错误 | 直接删掉 `_cancel_tasks({main_task}, loop)` 这一行 | 0 | 目标键 PASSED，但 TestShutdown 有多个键 FAILED。原因是主任务、`test_task` 和处理器任务被同时取消，例如 `test_shutdown_wait_for_handler` 的 `finished is True` 不成立，`test_task.exception()` 抛出 CancelledError | 负对照：确认 R5 确实由 TestShutdown 保护 |
| C6（可选，口径校准） | 主任务已带异常结束时，临时 `loop.set_exception_handler(lambda l, c: None)` 包住 `_cancel_tasks({main_task}, loop)`，结束后恢复原处理器 | 0 | 目标键 FAILED（`call_exception_handler` 仍被调用） | 说明"只压日志、仍走异常处理器"的写法会被拒。依据：asyncio 的报告通道就是 `call_exception_handler`，装了自定义处理器的用户仍会收到重复报告。只在真实轨迹里出现这类候选时，才当作疑似规格争议复核；它不是缺陷 |

C3 诊断脚本的设计：

- 构造：cleanup_ctx 在 `yield` 之后 `raise RuntimeError`；调用 `run_app(app, print=stopper(loop), loop=loop)`，并装一个 mock 异常处理器。
- 预期：base 和 C1 下处理器被调用 1 次；gold 下 `run_app` 抛出该异常；C3 下两者都不发生。

## 7. 开发需求（逐题）

| 项 | 内容 | 证据级别 |
|---|---|---|
| 导入 | 在 `/testbed` 下，`python`（即 `/testbed/.venv/bin/python`，3.9.21）导入的是 `/testbed/aiohttp`（3.10.6.dev0）。包没有装进 venv，靠 cwd 在 `sys.path` 上 | 镜像层面实测（devcheck `env.out`，agent uid 54321） |
| 依赖 | pytest 8.3.2、pytest-cov 5.0.0、pytest-mock 3.14.0、pytest-asyncio 0.25.2；pip 23.2.1 可用，但不能出网；本题不需要新包 | 实测 |
| 资产 | 无 | 静态 |
| 权限 | agent 可写 `/testbed` 和 home；激活文件不可写；`/tmp` 是 1 GiB tmpfs；资源 2 CPU / 4 GiB / pids 512 | 实测（prelaunch probe facts） |
| 网络 | 解题不需要外网（外部 DNS 和直连都是 DENIED）；公开测试只需要回环（TestShutdown 的端口、子进程信号） | 实测（全文件 55 passed） |
| 构建 | 只改纯 Python 代码，不需要编译；C 扩展是否存在未知，本题也用不到 | 静态 + 导入实测 |
| 验证命令 | 题面示例的三种观测（`public_read` 的 E1/E2/E3）：base 为 1/1/2，gold 为 0/0/1；窄测 4 passed，2.2 s；全文件 55 passed，27 s。公开读者的预测全部与实测一致 | 实测（base 为 agent 身份；gold 为 root 私有容器） |
| 提交边界 | 只改 `aiohttp/web.py`；跑测试不改变 `git status`（`.coverage`、`__pycache__` 都被忽略） | 实测（跑完后仍是 4 行） |
| actor 待验 | 真实题面消息的渲染（devcheck 用的是桩提示 "Devcheck run…"）；非 gold 候选经正式冻结 / 投影的交付；gold 在 agent 身份下的运行 | 未知 |

镜像说明：

- 涉及三张镜像：devcheck 与私有对照用 `bd9b7c27…`；R-f 和环境轮评分用 `ba4b1812…`；加跑评分用 `39f42dc8…`。
- 它们都来自同一配方 `r2e_derive_v1` 和同一来源 digest `3a2a7377…`，是在不同机器上的三次本地构建。
- 评分结果在 `ba4b1812…` 和 `39f42dc8…` 上一致；`bd9b7c27…` 上没有隐藏测试的评分记录，按环境卡的派生构建复核引用。

## 8. 题目关系

- **跨题包含**：本题 gold 新增的 7 行非平凡代码，全部出现在 `aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac` 的公开工作树里。那道题的 base 是 `354153e9`（3.11.0.dev0），题目是 TLS 指纹不匹配。已逐项核对：
  - 它的 `aiohttp/web.py:9` 有 `from contextlib import suppress`，`:517-530` 的 `finally` 与 gold 逐字相同。
  - 它的公开 `tests/test_run_app.py:909-923` 与本题目标测试逐字相同。
  - 它的 `CHANGES.rst:190-194` 有本修复的 changelog（`#6807`）。
  - 反方向不成立，因为本题的 base 更早。
- **影响**：单独解本题时不会泄漏，因为容器里看不到别题的工作树。但如果 22a12cc2 进训练集、本题进留出评测（或者反过来），另一题的工作区里就有本题的答案和测试。建议同组划分，或登记为包含关系。
- **其它同仓题**：
  - `aiohttp__4075c653…`（3.9.0b0，HTTP 解析）的 base 在 `web.py:522` 仍是旧写法。这只说明 bug 存在得更久，不构成包含。
  - `aiohttp__240da100…`、`aiohttp__61833518…` 版本很老，与本题无关。
- **用途**：这是一个小型的关停逻辑修复，只有一个目标键，示例就是测试，回归键 agent 都能在本地运行。不根据静态阅读去猜基座成功率。

## 9. 缺口与建议队列（由协调者安排）

1. **（优先）用正式评分实跑 C1、C3、C5**（C6 可选），并跑 C3 的诊断脚本。若 C3 确实得 1，就登记为次要漏测（清单第 26 项：未测回归）。这不影响本题当前的可用性。
2. **如果要堵 C3 这个漏洞**：可以提材料修订，加一个键，要求 Ctrl+C 之后 cleanup 抛出的错误必须被抛出或被报告。断言写成二选一，让 gold（抛出）和 C1（报告）都能过，C3 过不了。这需要独立复核，而且会改变期望映射。
3. **数据划分**：登记本题与 22a12cc2 的包含关系。
4. **actor 验证**：捕获真实的题面消息；用一个非 gold 候选走一次正式交付。
5. **稳定性**：如果计划多容器并行评分，在并发条件下复测 TestShutdown。

## 附录：证据索引

- **材料摘要**：
  - `PRIVATE_DIR/gold.patch` 的 sha256 是 `926c9558…`，与 validation bundle 和加跑账本的 `patch_sha256` 一致。
  - 隐藏测试树 `a46a7752…`、`run_tests.sh` `8285765f…`，分别等于 eval 日志的 `RH2_SETUP_HIDDEN_TESTS_TREE` 和 `RH2_SETUP_ENTRY_SHA256`。
  - 期望映射 `a7341a36…`。
- **隐藏测试与公开测试的差异**：`diff worktree/tests/test_run_app.py hidden_tests/test_1.py` 只有第 12 行的 import 和新增的 `:909-925`；`conftest.py` 没有差异。
- **评分证据（material=current）**：
  - noop：
    - `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:1`（日志 `…rf-all-noop-a_745bf9bf.eval.log`，失败在 `test_1.py:923`）
    - `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:1`（`…rer_4acb1e5d`）
    - `runs/r2e_t0_batch2_20260924/replay_b2/ledger_watch1c1c_noop.jsonl:1-5`
    - 全部是 55/56，只错目标键。
  - gold：
    - `…ledger_r2e_all_gold.jsonl:1`（`…_dcbb1d7a`）
    - `_rerun2/ledger_gold.jsonl:1`（`…_a5baf932`）
    - `ledger_watch1c1c_gold.jsonl:1-5`
    - 全部是 56/56。
  - 测试段用时 27–30 s，内存峰值约 0.5 GB。
  - 独立参考：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:9, 60`（来源镜像，gold 两次都是 56 passed）。
- **devcheck**：
  - `runs/r2e_actor_20260925/devcheck/aiohttp__1c1c0ea353041c8814a6131c3a92978/orig/captures/{env,r2e_preflight,pr1_1_cmd,pr2_2_cmd,pr3_3_cmd,pr4_4_pytest,pr4_5_pytest}.out`
  - `orig/prelaunch.json`（资源、网络、git 事实）
  - `orig/post_run_facts_root.txt`
  - `orig/stub/requests/messages_000.json`（桩提示，不是题面）
  - `private_gold/private_control.json`
- **跨题**：
  - `runs/r2e_static_prep_20260924/cross_task_gold_scan.json` 的 `pairs[0]`
  - `v3/public/aiohttp__22a12cc2…/worktree/` 下的 `aiohttp/web.py:9, 517-530`、`tests/test_run_app.py:909-923`、`CHANGES.rst:190-194`
