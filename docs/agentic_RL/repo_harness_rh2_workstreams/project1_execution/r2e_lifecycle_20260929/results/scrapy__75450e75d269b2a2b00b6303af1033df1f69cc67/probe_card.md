# scrapy `75450e75` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67`，`C` = `runs/r2e_actor_20260925/grader_cands`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 6 行全部与期望一致，正对照是经独立核实的替代解 K1（v1 §5 / D4），**原 gold 在修订版上为 0，已登记**；devcheck 13 项全真；S1 已按 R-c 修订，经 Codex 复核与正式评分验收（含 Codex 点名的辅助模块可导入、挂起候选在期限内产出结果）；预检通过。
- **材料**：修订单 v4 的 `r2e-mr-028`（`hidden_test_text_replace`，`test_1.py` `aee512f7…` → `36178735…`）、`r2e-mr-029`（`hidden_test_file_add`，`r2e_tests/shell_asyncio_mw.py` `3691d21c…`）、`r2e-mr-030`（`expected_file_replace`，`3fea4d14…` → `95d7565c…`，17 → 19 键，新增 `ShellTest.test_shell_fetch_async_coroutine_runs`、`…_twice`）；条目 reason 写明正对照为 K1、gold 不满分。pins v5 `2324c4c4ab82…`，v5 逐字保留。派生镜像 `290e9c8f2672`（`rh2-r2e-derived/scrapy:75450e75d269-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `25e665c3a025…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-028/029/030`）。修订后 gold 得 0，不能与原 benchmark 混报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/`：gold / noop / s1 / s2 / s3 第 6 行，s4 第 5 行；`F/status.json` 本题 6 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键 | 测试段 |
   | --- | --- | --- | --- | --- | --- |
   | K1：reactor 线程复用 reactor 的循环（`C/scrapy_7545_K1_reuse_reactor_loop.patch`） | 正对照（替代解，D4） | 1 | 1（19/19） | — | 37 s |
   | K1b：协程辅助函数优先用运行中的循环 | 合理替代解（另一实现族） | 1 | 1（19/19） | — | 37 s |
   | gold | 原 gold，按 D4 记录失败 | 0 | 0（17/19） | `…_coroutine_runs`、`…_twice` | 157 s |
   | noop | — | 0 | 0（17/19） | `test_shell_fetch_async`、`…_coroutine_runs` | 37 s |
   | K2：只改 `deferred_from_coro` | 已知错误（原版就是 0） | 0 | 0（18/19） | `test_shell_fetch_async` | 37 s |
   | K3：取不到循环就退回 `ensureDeferred` | 触发反例，兼 §4 第 3 步退化探测（吞掉错误，原版 1） | 0 | 0（18/19） | `…_coroutine_runs` | 37 s |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；失败键与试跑逐一相同。K1 通过 `…_coroutine_runs` 说明隐藏辅助模块可导入；gold 两个新键各被 60 s 闹钟终止，测试段 157 s 仍完整产出（候选阶段预算 900 s）。gold 挂起、K3 报 `await wasn't used with future` 的具体现象来自试跑日志（revision_plan 第 115–118 行）；正式日志在远端未取回。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；11 条命令都符合预期。agent 身份下复现题面缺陷（`Spider error processing … RuntimeError: There is no current event loop in thread`，shell 退出码 0）。私有 gold 对照（root）两条 rc=1 都是预期内：`pr2_3_cmd` 在 gold 下输出 `is_idle()` 为 `False`、`grep -c` 计数 0 而返回 1，正是 gold 槽位不释放的旧证据；`pr6_9_pytest`（`test_default_loop_asyncio_deferred_signal`）在 base 与 gold 下都失败，原因是 Twisted 24.11 没有 `_handleSignals`，与本题无关。
3. **S1 处理**：R-c 两个新测试 + 一个隐藏辅助模块（revision_plan §1，第 14–22 行）：用 asyncio 的下载中间件协程要真正跑完（堵 K3，也堵 gold 式"新建不运行的循环"）；连续两次 fetch 都要完成（gold 槽位不释放、第二次挂起）。Codex 复核通过（`L/codex_reviews/review_revision_scrapy.md` 第 17–25 行），限定：**60 s 闹钟是实际墙钟上限，不能说完全没有时间约束，也不能宣称零抖动风险**；辅助模块保持私有、不规定修改位置；没有为保 gold 放宽要求。Codex 列的正式复验（第 45 行）今晚已完成：缺省 profile（2 CPU / 4 GiB）下 K1 测试段 37 s、未见误拒，"正式资源配置下确认裕量"这一项在本机成立；按第 48 行，本次修订验收可以核销。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；新增的辅助模块在隐藏测试目录里，评分时才放入；公开包在材料 v3 → v4 之间逐字未变。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-028/029/030` 标明版本报告（gold 式修法在此版本得 0）。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：原例 + 协程跑完 + 两次 fetch（revision_plan §6 第 134–135 行）；当前版本 noop 0、正对照 K1 1；§4 第 2、3 步已做；S2、X1 已登记。60 s 闹钟的时序风险按 E5 登记（K1 共 3 次 19/19：试跑 2 次、正式 1 次，未见误拒） |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题初态含同仓 `a95a338e`、`e9387529` 的修复（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2 / 未覆盖**（revision_plan §6 第 136 行）：自定义 `ASYNCIO_EVENT_LOOP`；主线程 asyncio 路径（相关公开测试因 Twisted 24.11 在 base 就失败）；默认 5 MB 阈值下的长会话；spider 回调里 `await asyncio`（与新测试 1 走同一个 `deferred_from_coro`，未单独测）。
- **E5 / 时序**：新测试靠子进程 + 60 s `signal.alarm`；正确修法几秒完成，本机正式评分测试段 37 s。GPU 机并发高时若出现正对照超时，先查负载，不按抖动删键。
- **环境敏感键**：`ShellTest.test_dns_failures` 依赖评分网络对不存在的主机名解析失败；当前 `deny_all` 下稳定，若网络能解析，该键会缺失、所有候选判 0（旧卡 `card.md` 第 40 行）。
- **题面（P4 登记）**：题面说 fetch 会"raises"，实际是 ERROR 日志加退出码 0；示例依赖测试辅助 `execute`；"within the new thread"容易把人引向 gold 式做法，这类做法在此版本得 0。Codex 判定未新增题面矛盾，revision_plan 第 137 行不建议 R-f。探针里 gold 式补丁得 0 属预期。
- **共享控制面**：隐藏测试依赖候选可改的 `scrapy/utils/testproc.py`、`testsite.py`、`tests/__init__.py` 与根 `conftest.py`（旧卡第 30 行）；辅助模块按评分工作目录 `/testbed` 导入，若评分工作目录变了，正对照也会一起失败（revision_plan 第 91 行）。
- **后检**：只有打印型命令 `C/scrapy_7545_extra_commands.json`，按 v1 §8 抽查时要先写明判读规则。
- **X1**：本题初态含 `a95a338e`、`e9387529` 的修复（暴露的是那两题的答案）和 `9a15fcf8` 的一行修复；本题 gold 不在其它题初态里。
- **解题侧条件**：无 pip；`test_default_loop_asyncio_deferred_signal` 恒失败（Twisted 24.11），装信号处理器的 `CrawlerProcess.start()` 在本环境会崩。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：
  - **本题 gold=0**：探针或批次若拿 gold 作健全性对照，须改用 K1（sha256 `b3702391a87c…`）。
  - 求解入口换 `r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v4 正式评分即此口径）；GPU 机须载入同一 image ID，否则本卡评分资格重出。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 可信初始化约 42 s；devcheck 公开命令较重（求解段 68 s）；评分 trusted setup 29–64 s（300 s 硬时限）；挂起类候选测试段约 157 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-028`、`r2e-mr-029`、`r2e-mr-030`
- Codex：`L/codex_reviews/review_revision_scrapy.md` 第 17–25、40–48 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
