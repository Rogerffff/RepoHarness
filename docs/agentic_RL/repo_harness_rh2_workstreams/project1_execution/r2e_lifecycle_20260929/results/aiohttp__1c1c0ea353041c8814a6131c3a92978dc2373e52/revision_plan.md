# aiohttp 1c1c0ea3：v1 §4 第 2 步核对与修订方案（R-c：补非示例实例）

2026-09-29 · 修订执行者（Claude，单题闭环试行，统一标准 v1 §4 第 2 步与 §5 模板内）。

**状态：第 2 步命中（S1，T2c 示例拟合），按 R-c 出修订草案，试跑验收通过（试跑工具，不是正式评分）。** 待协调者落正式修订单与派生镜像材料、跑正式评分，再送 Codex 复核。本题原本是 conditional（v1 §10 表 aiohttp `1c1c0ea3` 行，§11），等的就是这一步核对。

路径约定：
- 仓库根相对路径。`PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/`，`PRIV` = 同目录下 `private/…`。
- `trials/`、`cands/`、`revision_draft.json` 相对本目录。

## 1. 第 2 步核对：核心断言是否只用了题面示例的字面值

**判断：是。**

**核心要求**（按题面的一般表述理解，v1 §4）：
- 标题 `PUB/user_prompt.txt:4`：run_app() Logs Exceptions That Are Also Raised, Causing Duplicate Logging。
- Expected `:26`：`run_app()` 应把异常抛出，而不是同时记日志。

也就是说，`run_app()` 抛给调用者的异常，不能再经 loop 的异常处理器报告一次。

**决定性断言只有一处**：`PRIV/hidden_tests/test_1.py:909-923` 的 `test_run_app_raises_exception`（唯一目标键）。它：
- mock 掉 `call_exception_handler`；
- 要求 `pytest.raises(RuntimeError, match="foo")`；
- 断言 `assert not m.called`（`:923`）。

**它的输入形态就是题面示例**（`PUB/user_prompt.txt:15-22`）：app 只有一个 cleanup context，在 `yield` 之前抛 `RuntimeError`，然后调用 `run_app(app)`。唯一不同是消息字面：`"foo"` 对应示例里的 `"Unexpected error occurred"`。消息不影响被测行为，形态（同一个钩子、同一个异常类型、同一个阶段）完全相同。

**文件里其它相关测试都不断言"不报告"**：
- `test_startup_cleanup_signals_even_on_failure`（`:664-677`）走的是示例以外的失败路径：`create_server` 失败，`run_app` 同样把异常抛出。但它只断言异常被抛出、启动与清理信号被调用。
- `test_run_app_cancels_failed_tasks`（`:826-856`）断言的是反方向：后台任务的异常照常报告。
- 全文件只有 `:923` 一处 `assert not m.called`（`grep call_exception_handler|exc_handler` 核对）。

**实测证据**：构造的示例拟合候选 F1 在当前材料上得 1。

| 项 | 内容 |
| --- | --- |
| 补丁 | `cands/aiohttp_1c1c_F1_skip_report_only_for_runtimeerror.patch` |
| 做法 | 只有主任务以 `RuntimeError` 结束时才不报告 |
| 当前材料 | 56/56，得 1（`trials/cur_F1.json`） |
| 实际行为 | 对其它异常（例如端口被占用时的 `OSError`）仍然既抛出又报告 |

因此按 D1 严格版，这一项是 S1（T2c），走 R-c。

**已登记的 S2 不变**：C3（Ctrl+C 之后 cleanup 抛出的错误被静默丢掉）仍按 v1 §10 记为第 4 步的边缘路径 S2，本修订不处理它，见 §6。

## 2. 公开依据（新实例）

- **题面**：
  - 标题 `:4` 说的是 `run_app()` 抛出的异常不应再被记录，没有限定来源；
  - 描述 `:7` 与 Expected `:26` 泛指"application context 里出现的异常"。
- **公开旧测试**：`PUB/worktree/tests/test_run_app.py:664-677` 表明，服务器启动失败（`create_server` 抛异常）时 `run_app` 会把异常抛给调用者。这正是标题说的"会被抛出的异常"。审查时 noop 日志里这一例还有 ERROR 记录，gold 日志里没有（主审卡 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/card.md:20`）。
- **公开代码**：
  - `PUB/worktree/aiohttp/web.py:518`：`loop.run_until_complete(main_task)` 把主任务的异常抛给调用者；
  - `:522`：接着 `_cancel_tasks({main_task}, loop)` 又对同一个异常调用 `call_exception_handler`（`:438-459`）。

  这条重复报告与异常来自哪里无关。主任务在 `runner.setup()`（`:337`）失败，还是在 `site.start()`（`:422`）失败，走的都是这里。
- **辅助依据**：`PUB/worktree/docs/web_reference.rst:2984-2986` 说 `run_app` 与 `asyncio.run` 非常相似。`asyncio.run` 的做法是：主协程的异常直接抛出，只报告其它任务的未处理异常。
- **选这个实例的理由**：它在两个维度上都不同于示例。
  - 异常来源：服务器启动失败，发生在 `runner.setup()` 之后、`try/finally` 之内，而不是 cleanup context；
  - 异常类型：`OSError`，而不是 `RuntimeError`。

  端口被占用是 `run_app` 最常见的启动失败。它不引入新接口，也不要求新行为，只把"抛出的异常不再报告"应用到示例以外的一个实例上。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`。
- **草案条目**：`hidden_test_text_replace`，一处 edit。`old` 是 `\n\nclass TestShutdown:\n`，在文件中唯一；`new` 是下面这段代码加上原来的锚点。插在 `test_run_app_raises_exception`（`:909-923`）之后、`class TestShutdown`（`:926`）之前。

```python
def test_run_app_raises_exception_on_server_start_failure(
    patched_loop: asyncio.AbstractEventLoop,
) -> None:
    # Not the issue's example: the error comes from starting the server
    # (e.g. the port is already in use) instead of a cleanup context, and it
    # is an OSError.  run_app() raises it, so it must not also report it.
    patched_loop.create_server = mock.Mock(
        side_effect=OSError("Address already in use")
    )
    app = web.Application()

    with mock.patch.object(
        patched_loop, "call_exception_handler", autospec=True, spec_set=True
    ) as m:
        with pytest.raises(OSError, match="Address already in use"):
            web.run_app(app, print=stopper(patched_loop), loop=patched_loop)

    assert not m.called
```

几点设计说明：
- 写法沿用同文件 `:664-677`（用 mock 让 `create_server` 失败）和 `:909-923`（mock `call_exception_handler`），不起真实 socket，没有时序因素。
- 传 `print=stopper(...)` 是为了防挂：如果某个候选吞掉异常、让服务器照常运行，测试会以"没有抛出"失败，而不是一直挂着。
- 只断言异常被抛出、且处理器未被调用，不断言控制流或内部 helper。

## 4. 期望映射逐键变化

- 原 56 键：不变，全部 PASSED。
- 新增 `test_run_app_raises_exception_on_server_start_failure[pyloop]`：PASSED。参数后缀 `[pyloop]` 来自 `patched_loop` 依赖的 `loop` fixture，与同文件其它键一致。
- 合计 57 键，完整映射见 `revision_draft.json`。
- **版本记录**：

  | 文件 | sha256 前 8 位 |
  | --- | --- |
  | 父版本 `test_1.py` | `26317e3d` |
  | 父版本 `expected_output.json` | `a7341a36` |
  | 修订后 `test_1.py` | `abd5a527` |
  | 试跑用 `draft.json` | `8f3bb016` |
  | 试跑用 `expected_after.json` | `9475dc01` |

  父版本隐藏测试树摘要为 `a46a7752…`。

## 5. 验收计划与试跑结果

**试跑环境**：
- 派生镜像 `sha256:979915fef224…`，配方 `r2e_derive_v1+sysconfig_v1`；
- 工具 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`，只作试跑；
- 各候选 `git apply` 均成功，草案均报 `RH2_TRIAL_EDITS_APPLIED=1`。

**环境确认**（当前材料）：noop 只在目标键失败（`trials/env_noop_current.json`）；gold 56/56（`trials/env_gold_current.json`）。

**修订草案下的验收**：

| 候选 | 补丁 | 应得 | 应失败的键 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- |
| gold（正对照） | `PRIV/gold.patch` | 1 | — | 1，57/57 | 1 |
| noop | 无 | 0 | 原目标键 + 新键 | 0，恰好这 2 键 | 0 |
| F1（示例拟合，触发反例） | `cands/aiohttp_1c1c_F1_skip_report_only_for_runtimeerror.patch` | 0 | 新键 | 0，恰好新键 | **1**（`trials/cur_F1.json`） |
| C5（已知错误：删掉单独取消主任务） | `runs/r2e_actor_20260925/grader_cands/aiohttp_1c1c_C5_drop_main_cancel.patch` | 0 | TestShutdown 7 键（不变） | 0，恰好这 7 键，与历史 49/56 相同 | 0（历史） |
| C1（合理替代：主任务已结束就不再走 `_cancel_tasks`） | `…/grader_cands/aiohttp_1c1c_C1_skip_done_main_task.patch` | 1 | — | 1，57/57 | 1（历史） |
| C3（已登记 S2：Ctrl+C 后吞掉 cleanup 错误） | `…/grader_cands/aiohttp_1c1c_C3_gather_swallow.patch` | 1（本修订不针对它） | — | 1，57/57 | 1（历史） |

- 修订版每行的结果文件是 `trials/rev_<候选>.json`。历史数据见 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/grader_candidates.md:36-39`。
- **失败原因从哪里判断**：日志尾部被覆盖率表占满，没有保留逐条断言信息。gold 通过新键，说明 `pytest.raises(OSError, match=…)` 这一段对正确实现成立；F1 与 gold 的唯一差别是对非 `RuntimeError` 仍然报告，所以 F1 只能失败在 `assert not m.called`。
- **没有误拒**：C1 在修订后仍得 1，本题的合理替代没有被新断言拒绝。
- **时序键**：`TestShutdown.test_shutdown_handler_cancellation_suppressed`（E5，watch）在 gold、noop、C1、C3、F1 的 8 次试跑里都是 PASSED。C5 在这个键上失败，是 C5 自己破坏了取消顺序（Codex 第二批复核 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/aio_scrapy/README.md:40-41`），不是时序抖动。

## 6. 修订后仍受保护的公开要求与剩余事项

- **run_app 抛出的异常不再报告**：
  - 示例实例：原目标键；
  - 非示例实例（服务器启动失败、`OSError`）：新键。
- **后台任务的异常照常报告**：`test_run_app_cancels_failed_tasks`，不变。
- **先单独取消主任务、cleanup 期间其它任务仍在运行**：TestShutdown 8 键，不变。
- **仍未覆盖，维持登记**：
  - **C3 边缘路径（S2 / T3）**：Ctrl+C 之后 cleanup 抛出的错误，base 报告、gold 抛出、C3 两样都不做。v1 §10 已判为第 4 步的边缘路径，不在本修订范围。探针判读继续用后检 `rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_1c1c0ea3_cleanup_error.py`，按 Codex 意见只作诊断，不改分。
  - **时序键**：按 E5 与 Codex F2 保持 watch。只有看到失败堆栈和同条件对照，才能归因到环境。
  - **跨题包含（X1）**：`aiohttp__22a12cc2…` 的公开工作树逐字包含本题的 gold 与目标测试（主审卡 `card.md:34`），照旧登记。

## 7. 边界与交接

- **只做 R-c**：不改题面、不删键、不放宽任何已有断言，也没有复制 gold 输出作期望。新键的期望 PASSED 来自公开要求，gold 通过是验证结果，不是依据。
- **协调者待办**：
  1. 把 `revision_draft.json` 的 `revisions` 落为正式修订单；
  2. 重建材料；
  3. 按本表至少跑 gold、noop、F1、C1、C5 的正式评分；
  4. 送 Codex 复核。

  之后本题的 v1 用途结论可以从 conditional 更新。本方案没有写 `s2_r2e` 下的正式材料，也没有改生产代码。
