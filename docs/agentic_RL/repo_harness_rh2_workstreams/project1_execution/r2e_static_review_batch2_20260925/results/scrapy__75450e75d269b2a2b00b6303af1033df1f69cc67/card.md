# scrapy__75450e75：scrapy shell 在 asyncio reactor 下 fetch 报"no current event loop"

私有主审短卡（2026-09-25，静态审查；审查者见过 gold、隐藏测试和旧环境记录）。详细证据见 `analysis_before_history.md`（初判）和 `old_findings_delta.md`（历史核对）。

## 1. 目标与建议用途

- **题目**：base `26ebdbf4efd5`（scrapy 2.7.1）。`scrapy shell` 在一个守护线程里跑 reactor；在 asyncio reactor 下，`deferred_from_coro` 在这个线程里向策略要"当前循环"，于是抛 RuntimeError，报错以 `Spider error processing` 日志的形式出现。gold 在 `Shell._schedule` 里为线程设置事件循环，同时新增 `scrapy/utils/reactor.py::set_asyncio_event_loop`。
- **建议用途**：开发诊断（基座探针候选）。要带着两条质量注记使用；reward=1 不代表修法语义正确，需要抽查补丁。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
|---|---|---|---|---|
| asyncio reactor 下 `-c "fetch(url)"` 不再出现该 RuntimeError | 题面 Title / Actual | `test_shell_fetch_async`：退出码 0，且 `assertNotIn(b"RuntimeError: There is no current event loop in thread", err)` | 覆盖，但只按字符串判断 | noop 0 共 4/4（RH2 2 次 + M3 2 次），gold 1 共 4/4 |
| 协程真正在 reactor 线程上执行（"allowing asynchronous operations to proceed as intended"） | 题面 Expected | 无 | **缺失** | gold 下 C2 输出 `(None, None, False)`，base 为 `True`（devcheck 各 1 次）；E1 |
| 换一种异常或换一句文本也算"有错" | 题面 "without errors" | 只查那一句文本 | 部分 | K3 |
| 默认 reactor 下 shell 既有语义不变 | 公开 `tests/test_command_shell.py` | 16 个回归键（与公开文件逐字相同） | 覆盖 | gold 16/16 |
| 主线程 asyncio 路径；自定义 `ASYNCIO_EVENT_LOOP` | `tests/test_crawler.py:479-484`；`utils/reactor.py:104-119` | 无 | 缺失 | 相关公开测试因 Twisted 24.11 在 base 就失败 |

反查：两条断言都能在题面找到依据，没有要求函数名或内部结构。问题出在过宽，不是过严。

## 3. 八方面：已查与未查

- **公开需求**：已查。题面有三处问题：说 fetch 会"raises"，实际是日志加退出码 0；示例里的 `execute` 和端口都缺；"within the new thread" 是方向提示，但没说复用哪个循环。**未查**：本题实际渲染给模型的消息（devcheck 用的是专用提示）。
- **材料与初态**：已查，一致。noop 的失败栈就是题面报错（`defer.py:270`、`Thread-1`）。
- **测试是否测到要求**：已查全部 17 个键。目标断言过宽。
- **误拒**：静态上没有发现；K1 待实跑。
- **回归与 gold**：gold 语义不完整（有执行证据）；asyncio 路径没有回归键。
- **开发条件**：agent 身份实测可用（`.venv`、无 pip、回环与 `file://` 可用，能复现报错，公开 shell 测试 16 例通过）。有一个与本题无关的恒失败：`test_default_loop_asyncio_deferred_signal`，原因是 Twisted 24.11 没有 `_handleSignals`。**未查**：真实模型求解。另外 devcheck 镜像 `21da38a7…` 与评分镜像 `2e6e1f3b…` 是否内容等价，没有核对。
- **交付与评分边界**：修复只涉及普通源码，额外排除为空。隐藏测试依赖 `scrapy/utils/testproc.py`、`testsite.py`、`tests/__init__.py` 和根 `conftest.py`，候选都能改（通用漏洞面，未做攻击实验）。
- **题目关系**：本题 gold 没有出现在同仓其它题的初态里；反过来，本题初态包含 a95a338e、e9387529 的修复，暴露的是那两题。

## 4. 具体问题与证据层次

1. **目标测试过宽**（25、32）：掩盖根因的修法也能得 1。证据是静态分析，待 K3 实跑。
2. **gold 语义不完整**（27）：gold 为 reactor 线程新建了一个不运行的循环，协程 Task 永不执行，scraper 槽位一直不空闲（devcheck 一次执行）。据源码推断，槽位累计超过 `SCRAPER_SLOT_MAX_ACTIVE_SIZE` 后，下一次 fetch 会永久阻塞（待 E1）。
3. **asyncio 路径缺少回归覆盖**（26），低。
4. **题面不精确**（23），低；不影响可解性。
5. **公开测试恒失败**（10），低，是解题侧条件。
6. **`test_dns_failures` 依赖评分网络**（11），低：若网络能解析任意主机名，这个键会缺失，所有候选都判 0；当前稳定。
7. 旧 issue"提示说有 pip"已被 v3 提示解决，关闭。

## 5. 待实跑的候选（正式评分）

- **K1（合理替代解，预计 reward 1）**：改 `scrapy/commands/shell.py` 的 `Command._start_crawler_thread`。
  - 把线程目标换成一个内部函数：若 `scrapy.utils.reactor.is_asyncio_reactor_installed()` 为真，先 `import asyncio; from twisted.internet import reactor; asyncio.set_event_loop(reactor._asyncioEventloop)`，再调用 `self.crawler_process.start(stop_after_crawl=False, install_signal_handlers=False)`。
  - 预计 17/17，没有不符键。附跑 C2 应为 `(None, None, True)`，计数 0。
- **K1b（可选，另一族合理解，预计 1）**：改 `scrapy/utils/defer.py` 的 `deferred_from_coro` 和 `deferred_to_future`，两处取循环都改为 `try: loop = asyncio.get_running_loop()` / `except RuntimeError: loop = get_asyncio_event_loop_policy().get_event_loop()`。预计 17/17。
- **K2（不完整修复，预计 0，重复 5 次）**：只按 K1b 改 `deferred_from_coro`，`deferred_to_future` 不动。
  - 预计每次 16/17，唯一不符键是 `ShellTest.test_shell_fetch_async`：协程会在 `maybe_deferred_to_future → deferred_to_future` 处再次报同一句错。
  - 5 次里只要有 1 次得 1，就记为时序导致的假通过：这次报错比 base 晚一个循环迭代，可能赶不上子进程退出。
- **K3（掩盖根因，预计 1，用来证明测试过宽）**：改 `scrapy/utils/defer.py` 两处。
  - `deferred_from_coro`：把 `get_asyncio_event_loop_policy().get_event_loop()` 包进 `try`，`except RuntimeError: return ensureDeferred(o)`。
  - `maybe_deferred_to_future`：asyncio 分支改为 `try: return deferred_to_future(d)` / `except RuntimeError: return d`。
  - 预计 17/17，没有不符键。这就是问题所在：asyncio reactor 下协程改由 `ensureDeferred` 驱动，违反 `defer.py:266-267` 的注释，也违反题面的 "proceed as intended"。

## 6. E1：gold 槽位累计后是否挂起（私有一次性容器，root，不联网）

对三种代码状态各跑一次：**base**、**gold**、**K1**。命令外层超时为 `timeout -k 5 60`。

```bash
cd /testbed && timeout -k 5 60 python -m scrapy.cmdline shell -c "(fetch('file:///testbed/tests/sample_data/test_site/index.html'), print('FIRST_DONE', flush=True), fetch('file:///testbed/tests/sample_data/test_site/index.html'), print('SECOND_DONE', flush=True))" --set TWISTED_REACTOR=twisted.internet.asyncioreactor.AsyncioSelectorReactor --set SCRAPER_SLOT_MAX_ACTIVE_SIZE=1000 >/tmp/e1.out 2>/tmp/e1.err; echo "rc=$?"; cat /tmp/e1.out; echo "crawled=$(grep -c 'Crawled (200)' /tmp/e1.err) loop_err=$(grep -c 'There is no current event loop' /tmp/e1.err)"
```

预期输出（index.html 只有 311 字节，槽位按 1024 字节计，1024 > 1000）：

| 代码状态 | rc | stdout | crawled | loop_err |
|---|---|---|---|---|
| base | 0 | 依次为 `FIRST_DONE`、`SECOND_DONE`、`(None, None, None, None)` | 2 | 4（每次报错 2 行；只要 ≥2 即符合） |
| gold | 124（超时） | 只有 `FIRST_DONE` | 1 | 0 |
| K1 | 0 | 与 base 相同 | 2 | 0 |

如果 gold 也打印出 `SECOND_DONE`，第 4 节第 2 条里的"挂起"推断就不成立，只保留"槽位不空闲"这一条执行证据。

## 7. 处置与下一步

- **静态处置**：`needs_review`，理由是静态候选待 actor 验证，另有测试过宽和 gold 语义缺陷两条质量问题。可作开发诊断的基座探针候选。
- **不建议**修订隐藏测试来惩罚 gold 式修法：那样 gold 本身会判 0，必须同时改 gold 和 expected，属于改变任务定义（37），由用户决定。
- **与历史的分歧**：历史（P4 环境审查）只判了环境资格。我确认它的环境结论，另外补了一个恒失败公开测试（Twisted `_handleSignals`）、一个依赖评分网络的键，并关闭了已过时的 pip 提示 issue。两条质量问题是历史没有覆盖的范围。独立 reviewer 的意见尚无。
- **唯一优先的下一步**：用正式评分跑 K1、K3 和 K2（K2 重复 5 次），同时在私有容器里跑 E1。
