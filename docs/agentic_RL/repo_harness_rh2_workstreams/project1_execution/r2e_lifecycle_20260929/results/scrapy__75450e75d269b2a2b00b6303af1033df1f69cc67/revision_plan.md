# scrapy__75450e75 修订方案（修订执行者，2026-09-29）

单题闭环试行，按统一标准 v1 §5 执行。本文件与 `revision_draft.json` 是**修订草案**；正式修订单、pins、派生镜像材料步骤由协调者落，之后还要正式评分与 Codex 复核。路径均相对仓库根；`PUB` = `runs/r2e_static_prep_20260924/v3/public/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67`，`OUT` = 本目录，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925`，`CX` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/aio_scrapy/README.md`。

## 0. 结论

- **模板：R-c**（v1 §11「协程真正执行、第二次 fetch 不挂；gold 失败，用 K1 作正对照」）。在 `ShellTest` 里补两个 asyncio reactor 下的测试，另加一个隐藏辅助模块：
  1. `test_shell_fetch_async_coroutine_runs`：启用一个 `process_request` 为协程、内部 `await asyncio.sleep(0.1)` 的下载中间件，fetch 后检查 await 之后才写的标记确实写上了。
  2. `test_shell_fetch_async_twice`：设 `SCRAPER_SLOT_MAX_ACTIVE_SIZE=1000`，连续两次 fetch 都要完成。
- **正对照：K1**（`runs/r2e_actor_20260925/grader_cands/scrapy_7545_K1_reuse_reactor_loop.patch`）；gold 在两个新键上失败，按 D4 记录。
- **试跑结果：全部符合预期**（§4）。K1（两次）、K1b 都是 19/19；noop、gold、K2、K3 都为 0，各自只错在预期的键上；修订前得 1 的 gold 与 K3 都被纠正。
- 没有需要用户决定的事项。第二批复核曾把「补测会判掉 gold」列为 T0 级任务定义变更（`B2/results/scrapy__75450e75…/review.md:64`），这一顾虑已被用户 09-26 确认的 v1 D4（经独立核实的替代解可作正对照）与 §11 的去向覆盖，本方案按此执行。

## 1. 触发问题与依据

| 问题 | 证据 | 公开依据 |
| --- | --- | --- |
| gold 让报错消失，但协程挂在一个从不运行的事件循环上：scraper 槽位不释放，累计超过阈值后第二次 fetch 永久挂起；仍得 1 | 当前材料 gold 17/17 match（`OUT/trials/cur_gold.json`）；第二批私有对照 E1：gold rc=124、只有 `FIRST_DONE`，C2 `is_idle()` 为 False（`B2/grader_candidates.md:235-243`；`CX:92`） | 题面 Expected「should execute without errors, properly setting up and utilizing the asyncio event loop within the new thread, **allowing asynchronous operations to proceed as intended**」（`PUB/user_prompt.txt:19`）；`SCRAPER_SLOT_MAX_ACTIVE_SIZE` 的文档语义：只有「正在处理」的响应计入，超过才暂停新请求（`PUB/worktree/docs/topics/settings.rst:1374-1386`）；shell 的 `fetch` 可以反复调用（`PUB/worktree/docs/topics/shell.rst:101-106,132-135`，公开测试 `PUB/worktree/tests/test_command_shell.py:84-88` 在一次 `-c` 里 fetch 两次） |
| 掩盖型 K3（取不到循环就退回 `ensureDeferred`、吞掉 `RuntimeError`）得 1 | 当前材料 17/17 match（`OUT/trials/cur_K3.json`）；Codex 指出其 asyncio-await 缺陷当时只有静态推断（`CX:96`） | 装了 asyncio reactor 后可以在任何协程里用 asyncio 及基于它的库（`PUB/worktree/docs/topics/asyncio.rst:9-11`）；下载中间件的 `process_request` 可以写成协程（`PUB/worktree/docs/topics/coroutines.rst:17-18,32-38`）；源码注释写明 `ensureDeferred` 路径不能正确运行用 asyncio 的协程（`PUB/worktree/scrapy/utils/defer.py:265-268`） |
| 目标断言只用了题面示例的字面值（v1 §4 第 2 步） | 唯一目标键 `test_shell_fetch_async` 只 fetch 一次，只查报错字符串不出现 | 同上，题面按一般表述理解 |

Codex 对后续补测的方向要求（`CX:96`）：「应加真正等待 asyncio future 且验证完成副作用的案例」。新测试 1 正是这一形式；新测试 2 对应已实测的 E1。

## 2. 具体改动

**(1) `r2e_tests/test_1.py`，一条 `hidden_test_text_replace`、一处 edit**：old 为文件末尾的 `test_shell_fetch_async` 整个方法（原文第 119–128 行），new 为原方法加上：

```python
    @defer.inlineCallbacks
    def test_shell_fetch_async_coroutine_runs(self):
        # With the asyncio reactor, a Scrapy coroutine that awaits asyncio (here the
        # process_request coroutine of a downloader middleware) must run to completion.
        reactor_path = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        mw_path = "r2e_tests.shell_asyncio_mw.AsyncioSleepDownloaderMiddleware"
        url = self.url('/html')
        code = (
            "(__import__('signal').alarm(60), "
            f"fetch('{url}'), "
            "print('R2E_MW_DONE', request.meta.get('r2e_asyncio_mw_done'), response.status, flush=True))"
        )
        args = [
            "-c", code,
            "--set", f"TWISTED_REACTOR={reactor_path}",
            "--set", 'DOWNLOADER_MIDDLEWARES={"%s": 543}' % mw_path,
        ]
        _, out, _ = yield self.execute(args, check_code=True)
        self.assertIn(b"R2E_MW_DONE True 200", out)

    @defer.inlineCallbacks
    def test_shell_fetch_async_twice(self):
        # With the asyncio reactor, processing of a fetched response must finish, so a second
        # fetch is not held back by the SCRAPER_SLOT_MAX_ACTIVE_SIZE soft limit.
        reactor_path = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        url = self.url('/html')
        code = (
            "(__import__('signal').alarm(60), "
            f"fetch('{url}'), print('R2E_FETCH_1', response.status, flush=True), "
            f"fetch('{url}'), print('R2E_FETCH_2', response.status, flush=True))"
        )
        args = [
            "-c", code,
            "--set", f"TWISTED_REACTOR={reactor_path}",
            "--set", "SCRAPER_SLOT_MAX_ACTIVE_SIZE=1000",
        ]
        _, out, _ = yield self.execute(args, check_code=True)
        self.assertIn(b"R2E_FETCH_1 200", out)
        self.assertIn(b"R2E_FETCH_2 200", out)
```

**(2) `r2e_tests/shell_asyncio_mw.py`，一条 `hidden_test_file_add`**（正式修订单支持这一类，见 `rh2/src/repoharness2/envpack/ingest_r2e_subset.py:232,314`）：

```python
import asyncio


class AsyncioSleepDownloaderMiddleware:
    # Used by ShellTest.test_shell_fetch_async_coroutine_runs: the process_request
    # coroutine awaits asyncio and marks the request only after the await has finished.

    async def process_request(self, request, spider):
        await asyncio.sleep(0.1)
        request.meta['r2e_asyncio_mw_done'] = True
        return None
```

设计取舍：
- **沿用原测试的写法**：`ProcessTest.execute` 起子进程跑 `scrapy shell -c`，本地测试站点 `self.url('/html')`，`TWISTED_REACTOR` 用 `--set` 传入，与目标测试一致。
- **防挂死**：`-c` 表达式第一项 `signal.alarm(60)`。修法有缺陷时子进程在 60 秒后被 SIGALRM 终止，`ProcessTest` 拿到的退出码为 None（`PUB/worktree/scrapy/utils/testproc.py:24-31` 只在退出码为真时报错），随后断言因缺少标记而失败，不会拖住整个评分。正确修法在几秒内完成；断言里没有任何时序阈值。
- **测完成副作用，不只测不报错**：标记在 `await` 之后才写，只有协程真的在运行中的 asyncio 循环上跑完才会出现；`request` 是 shell 在 fetch 后更新的变量（`PUB/worktree/scrapy/shell.py:114-124`）。
- **阈值 1000**：`/html` 正文约 60 字节，按 `MIN_RESPONSE_SIZE = 1024` 计入（`PUB/worktree/scrapy/core/scraper.py:56,66-73`），大于 1000；响应处理若永远不结束，引擎的 `_needs_backout` 就一直为真（`PUB/worktree/scrapy/core/engine.py:164-169`），第二个请求不会被处理。正确修法处理完即释放。
- **模块位置**：辅助模块放在 `r2e_tests/` 下，子进程按 `r2e_tests.shell_asyncio_mw` 导入。这依赖子进程工作目录是 `/testbed`：`ProcessTest.cwd` 在导入时取 `os.getcwd()`（`testproc.py:11`），评分从 `/testbed` 跑 `run_tests.sh`，试跑与正式评分条件相同。若将来改了评分的工作目录，这个导入会让所有候选（包括正对照）一起失败，表现为正对照 0，而不是静默放过。`--doctest-modules`（`PUB/worktree/pytest.ini:8`）会在收集时导入该模块，它没有 doctest，不产生键（试跑 19 键、无 extra）。

完整条目见 `OUT/revision_draft.json`（与试跑用的 `OUT/trials/inputs/draft_7545.json` 逐字相同，已比对）。

## 3. 修订后期望映射（17 键 → 19 键）

原 17 键全部保留、状态不变（都是 PASSED）；新增两键，状态 PASSED：

- `ShellTest.test_shell_fetch_async_coroutine_runs`
- `ShellTest.test_shell_fetch_async_twice`

新键的期望来自题面与文档（§1），不是抄 gold 输出（gold 在两键上都失败）。

## 4. 验收计划与试跑结果

镜像 `sha256:5a68023b6eba7cd71a6524b1b31ea531858efef1aa12e6174061f4e9187618d8`，配方 `r2e_derive_v1+sysconfig_v1`；结果文件在 `OUT/trials/`。补丁都在 `runs/r2e_actor_20260925/grader_cands/`（sha256 前缀与第二批账本一致）。

| 材料 | 候选（补丁，sha256 前缀） | 应得 | 实得 | 不符的键 | 结果文件 |
| --- | --- | --- | --- | --- | --- |
| 当前 | noop | 0 | 0 | `test_shell_fetch_async` | `cur_noop.json` |
| 当前 | gold（c03c7d89） | （漏判） | 1 | — | `cur_gold.json` |
| 当前 | K3 掩盖根因（`scrapy_7545_K3_mask_runtimeerror.patch`，d1155c86） | 漏判 | 1 | — | `cur_K3.json` |
| **草案** | K1 线程里复用 reactor 的循环（`scrapy_7545_K1_reuse_reactor_loop.patch`，b3702391）**正对照** | 1 | 1（19/19，两次） | — | `draft_K1.json`、`draft_K1_r2.json` |
| **草案** | K1b 两处协程辅助函数优先用运行中的循环（`scrapy_7545_K1b_running_loop_both.patch`，cfb758c7） | 1 | 1 | — | `draft_K1b.json` |
| **草案** | noop | 0 | 0 | `test_shell_fetch_async`、`test_shell_fetch_async_coroutine_runs`（shell 退出码 1，`RuntimeError: There is no current event loop in thread 'Thread-1'`） | `draft_noop.json` |
| **草案** | gold | 0（D4 记录） | 0 | `test_shell_fetch_async_coroutine_runs`（第一次 fetch 即挂起，60 秒后被终止，stdout 为空）、`test_shell_fetch_async_twice`（stdout 只有 `R2E_FETCH_1 200`） | `draft_gold.json` |
| **草案** | K2 只改 `deferred_from_coro`（`scrapy_7545_K2_running_loop_from_coro_only.patch`，48693797） | 0 | 0 | 仅 `test_shell_fetch_async`（与修订前相同） | `draft_K2.json` |
| **草案** | K3 | 0 | 0 | 仅 `test_shell_fetch_async_coroutine_runs`（`RuntimeError: await wasn't used with future`，shell 退出码 1） | `draft_K3.json` |

对照 v1 §5 R-c 验收：正对照 1、noop 0 ✓；要纠正的漏判（gold 式缺陷、K3）已纠正 ✓；已知错误候选 K2 仍为 0 ✓；所有行 `missing` / `extra` 为空 ✓。K1 与 K1b 属于公开读者列出的两个不同实现族（`B2/results/scrapy__75450e75…/public_read.md:64-80` 的 A 与 C），都通过，说明新测试没有锁定修改位置。

与此前静态推断的对照：第二批复核的 E3 预测「gold 第一次 fetch 就挂起」得到证实；它对 K3 的预测是「打印 DONE、另记一条错误」（`B2/results/scrapy__75450e75…/review.md:124-134`），实测是 fetch 直接抛错、shell 退出码 1。两种结果下新测试都判 K3 失败。gold 的整轮测试用时 155 秒（两次 60 秒闹钟），正对照约 37 秒。

## 5. 正对照：K1 的独立核实

- **静态与复核**：公开读者在没看 gold 的情况下把「reactor 线程开跑前把 reactor 的循环设为该线程的当前循环」列为应被接受的实现族 A（`B2/results/scrapy__75450e75…/public_read.md:64-70`），并把 gold 式「新建一个循环」列为语义可疑（同文件 `:82-86`）；第二批独立复核确认 K1、K1b 不被误拒（`B2/results/scrapy__75450e75…/review.md:15,46`）；Codex 复核「K1 / K1b 合理」（`CX:58`）。
- **行为**：第二批私有对照中 K1 在 E1 下两次 fetch 都完成、无报错，单次 fetch 后槽位空闲（`B2/grader_candidates.md:241`；`CX:92`）。
- **评分**：修订前 17/17（`B2/grader_candidates.md:83`）；修订草案下 19/19 两次。
- K1 只改 `scrapy/commands/shell.py` 的 `_start_crawler_thread`：asyncio reactor 下先 `asyncio.set_event_loop(reactor._asyncioEventloop)` 再启动 reactor。
- **原 gold 的失败**：两个新键都失败，原因是 gold 在 `Shell._schedule` 里给 reactor 线程新建了一个不运行的循环，协程任务永远不执行。按 D4 记录，不改题意、不放宽断言。

## 6. 修订后仍受保护的公开要求与未覆盖范围

- **核心要求**（`user_prompt.txt:18-19`）：`test_shell_fetch_async`（原例：不再出现该报错）+ 两个新测试（异步操作真的推进：用 asyncio 的协程跑完；响应处理结束，后续 fetch 不被卡住）。
- **既有行为**：默认 reactor 下 shell 的 16 个回归键不变。
- **仍未覆盖（登记，不在本次修订内）**：自定义 `ASYNCIO_EVENT_LOOP`（公开读者 R9）；主线程 asyncio 路径（R8，相关公开测试因 Twisted 24.11 在 base 就失败）；默认 5 MB 阈值下的长会话（机理与测试 2 相同）；spider 回调里 `await asyncio` 的情形（与测试 1 走同一个 `deferred_from_coro`，未单独测）。
- **题面措辞**：「setting up … the asyncio event loop within the new thread」容易把解题者引向 gold 式做法（第二批复核 `review.md:82-84`）。修订后这类做法得 0，这正是本次要纠正的误判；题面同一句还要求「properly」「allowing asynchronous operations to proceed as intended」，新测试检查的就是这一点。我**不建议**为此做 R-f：补一句「用哪个循环」会直接给出修法方向。若协调者认为需要，可另议。

## 7. 版本记录

- **父版本**：来源材料，无修订；期望 `sha256:3fea4d14e16cd6cddc9c036ef37362fb92059d8f193759ba29ba4977736c3b6d`；隐藏测试树 `sha256:d49355acee68d9b5a2c0380ca743b85927e5507b3bb339a080ffcb27226278d6`；`test_1.py` `sha256:aee512f73b0c266621c9a414e94ae3dbc060f8687f4255eeee61f8810c77d9f0`。
- **新版本**：`test_1.py` 修订后 `sha256:36178735fd29685ec6459b362df45a6172802031c23449f9aa0ecd3f05212974`；新增 `shell_asyncio_mw.py` `sha256:3691d21c38ecef9d61927621c2fd6bf1abf7066297806efa4891258237a26dfe`；期望 19 键（`OUT/trials/inputs/expected_7545.json`）。
- **触发反例**：gold（槽位不释放、第二次 fetch 挂起却得 1）、K3（掩盖根因得 1）。

## 8. 试跑与正式评分的差别

`trial_grade.py` 不做基线重建比对、不核隐藏测试树与入口摘要，权限简化（见脚本文件头）。定稿后需协调者写正式修订单（一条 `hidden_test_text_replace`、一条 `hidden_test_file_add`；期望用 `expected_file_replace`，`added` 2 键），重建派生镜像材料步骤，用正式评分复验 K1 / noop / gold / K2 / K3（可加 K1b），再交 Codex 复核。正式评分的期限需容纳 gold 类挂起候选约 2.5 分钟的测试时间（本次试跑 155 秒）。
