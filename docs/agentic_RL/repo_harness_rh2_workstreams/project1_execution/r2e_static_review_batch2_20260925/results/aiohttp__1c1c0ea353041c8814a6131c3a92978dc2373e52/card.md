# aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52 · 静态审查卡

2026-09-25 · R2E 私有主审（静态）。分析过程见 `analysis_before_history.md`（读历史前保存）与 `old_findings_delta.md`。

## 1. 题目与建议用途

- **题目**：aiohttp 3.10.6.dev0，base `87342c79`。`web.run_app()` 的主任务以异常结束时，异常已经抛给调用者，但 `finally` 里的 `_cancel_tasks({main_task}, loop)`（`aiohttp/web.py:522`）又经 `loop.call_exception_handler` 报告一次，造成重复。要求改成只抛出、不报告。
- **评分构成**：期望共 56 键，全部 PASSED。
  - 唯一目标键是 `test_run_app_raises_exception[pyloop]`，内容就是题面示例。
  - 另外 55 键与公开的 `tests/test_run_app.py` 逐字相同，agent 可以在本地全部运行。
- **建议用途**：开发诊断用的静态候选，待 actor 验证。不是训练或评测准入。

## 2. 关键映射

| 需求或旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一验证 |
|---|---|---|---|---|
| 已抛出的主任务异常不再报告，且照常抛出 | 题面 Expected；`web.py:518, 522, 449-459` | 目标键：`pytest.raises(RuntimeError, match="foo")`，且 `assert not m.called`（`call_exception_handler` 被 mock） | 覆盖（仅示例路径） | noop 7 次都在 `test_1.py:923` 失败；gold 7 次都是 56/56 |
| 后台任务的异常照常报告，context 字典不变 | 公开 `test_run_app.py:826-856` | `test_run_app_cancels_failed_tasks`：`assert_called_with(loop, msg)` | 覆盖 | 两侧都 PASSED |
| 先单独取消主任务，cleanup 期间其它任务仍然活着 | `CHANGES.rst:2076`；公开 TestShutdown | TestShutdown 的 8 个键 | 覆盖（间接） | 实跑 C5 验证 |
| 示例以外的失败路径（create_server 失败）也不重复报告 | 合理推知 | `test_startup_cleanup_signals_even_on_failure` 只执行、不断言 | 部分 | noop 日志有 ERROR，gold 日志没有 |
| Ctrl+C 之后 cleanup 抛出的错误不能被静默丢掉（base 报告，gold 抛出） | 题面宽读、base 旧行为 | 无 | 缺失 | 实跑 C3 加诊断脚本 |

## 3. 八方面

| 方面 | 已查 | 未查 / 缺口 |
|---|---|---|
| 公开需求 | 已查；R3 属合理推知，R7 有歧义 | — |
| 材料与初态 | sha256 与 bundle、eval 日志一致；noop 失败原因与题面一致 | — |
| 测试是否测到要求 | 目标测试逐行追完；隐藏文件与公开文件只差目标测试 | R3 路径不断言；R7 无键 |
| 误拒合理解 | C1 静态推断得 1 | 待实跑 |
| 回归与 gold | gold 覆盖 R1–R6；在 R7 上改为"抛出" | C3 回归无键保护 |
| 开发条件 | devcheck 以 agent 身份实测：复现 1/1/2 → gold 后 0/0/1；公开文件 55 passed，27 s | 真实题面消息与非 gold 交付属 actor 待验 |
| 交付与评分边界 | 修复落在非测试源码；跑测试不改变 git status | 包内测试辅助可被候选修改，属 R2E 共性，未专测 |
| 题目关系 | 已核：`aiohttp__22a12cc2…` 的公开工作树逐字包含本题 gold（`web.py:517-530`）、目标测试（`tests/test_run_app.py:909-923`）和 changelog（`CHANGES.rst:190-194`） | 其它仓库未查 |

## 4. 问题与证据层次

1. **次要漏测（清单第 26 项，源码推断）**：候选 C3 在 Ctrl+C 之后把 cleanup 抛出的异常静默吞掉，推断仍得 1。现有 56 键都不能把它和 gold 区分开。
2. **时序残余风险（历史真实 RH2 证据 + 来源原始记录）**：`TestShutdown.test_shutdown_handler_cancellation_suppressed` 的首个请求没有预热，与 `site.start()` 之间存在竞态。
   - 来源宿主机上新旧两次运行都因此失败（`Connect call failed`）。
   - RH2 14/14 PASSED，M3 2/2。
   - 一旦翻转，所有候选（包括 gold）都判 0。
3. **跨题包含（静态核对）**：见第 3 节"题目关系"。划分时要同组处理，或登记为包含关系。
4. **环境敏感键**：`::1` 绑定和抽象套接字在当前 grader 与 actor 容器都可用；如果换沙箱配置，所有候选都会判 0。
5. **历史环境修复是否已被本次条件覆盖**：是。环境侧处置 `environment_qualified`；v3 提示已改为 `.venv`、`python -m pytest`，旧的 conda 措辞问题已过时。

## 5. 建议、与历史的分歧、下一步

**静态建议**：`needs_review`，理由是"静态候选，待 actor 验证"；不属于题意或测试争议；本题可以直接用于开发诊断。

**与历史的分歧**：历史把时序键视为稳定、族已关闭。我认为应改为 watch：这个竞态机制明确，而且在另一台宿主机上两次失败过。此外，历史 R10 说"测试不需要网络"，这一点措辞有误：外网确实不需要，但回环是必需的。

**独立复核**：尚未进行。

**供正式评分实跑的候选**（都只改 `aiohttp/web.py` 的 `run_app()`）：

- **C1（合理替代，预期 1）**：把 `finally:` 下第一行 `_cancel_tasks({main_task}, loop)` 改成 `if not main_task.done(): _cancel_tasks({main_task}, loop)`，其余不动。预期 56/56，没有键与 gold 不同。
- **C3（可能蒙混，预期 1）**：把 `finally:` 下的 `_cancel_tasks({main_task}, loop)` 换成两行：`main_task.cancel()` 和 `loop.run_until_complete(asyncio.gather(main_task, return_exceptions=True))`，其余不动。预期 56/56，没有键与 gold 不同。
- **C3 诊断脚本（不计入 reward）**：app 的 cleanup_ctx 在 `yield` 之后 `raise RuntimeError("cleanup failed")`；调用 `run_app(app, print=<stopper：loop.call_soon 抛 KeyboardInterrupt>, loop=loop)`，并装一个 mock 异常处理器。预期：
  - base 和 C1：处理器被调用 1 次，`run_app` 正常返回；
  - gold：`run_app` 抛出该 RuntimeError，处理器未被调用；
  - C3：两者都不发生，错误被丢失。
- **C5（常见错误，预期 0）**：直接删掉 `finally:` 下的 `_cancel_tasks({main_task}, loop)` 一行。预期目标键 PASSED，但 TestShutdown 多数键 FAILED，例如 `test_shutdown_wait_for_handler`：`test_task` 和处理器任务会与主任务同时被取消，导致 `finished is True` 不成立、`test_task.exception()` 抛出 CancelledError。
- **C6（可选，口径校准，预期 0）**：主任务已带异常结束时，临时 `loop.set_exception_handler(lambda l, c: None)` 包住原来的 `_cancel_tasks({main_task}, loop)`，之后恢复原处理器。预期目标键 FAILED，因为 `call_exception_handler` 仍被调用。只有真实轨迹中出现这类写法时，才按疑似规格争议复核。

**唯一优先的下一步**：用正式评分实跑 C1、C3、C5，C3 配上诊断脚本。确认 C3 得 1，就登记漏测，并决定是否提修订：加一个二选一断言，要求 cleanup 错误"被抛出或被报告"，让 gold 和 C1 都能通过、C3 不能通过。

## 附录：证据

- **评分（current）**：
  - `runs/r2e_rf_20260923/remote/ledger_r2e_all_{noop,gold}.jsonl:1`
  - `runs/r2e_env_repair_20260924/_rerun2/ledger_{noop,gold}.jsonl:1`
  - `runs/r2e_t0_batch2_20260924/replay_b2/ledger_watch1c1c_{noop,gold}.jsonl:1-5`
  - 日志见 `v3/private/…/run_refs.json`
- **独立参考**：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:9, 60`；其 `status_map.json` 与期望逐键相等。
- **devcheck**：`runs/r2e_actor_20260925/devcheck/aiohttp__1c1c0ea353041c8814a6131c3a92978/{orig/captures/*.out, orig/prelaunch.json, private_gold/private_control.json}`
- **来源宿主机记录**：`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl` 本题行的 `execution_result_content`：旧提交 2 failed，新提交 1 failed（时序键）。
- **跨题**：`runs/r2e_static_prep_20260924/cross_task_gold_scan.json` 的 `pairs[0]`
- **历史**：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks/aiohttp__1c1c…/{findings.md, screening_record.json, facts.json}`
