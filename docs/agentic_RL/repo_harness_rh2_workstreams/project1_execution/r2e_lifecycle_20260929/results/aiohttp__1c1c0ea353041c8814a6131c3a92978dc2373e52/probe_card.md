# aiohttp `1c1c0ea3` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 6 行全部与期望一致（正对照 gold）；devcheck 13 项全真；v1 §10/§11 原记 conditional（第 2 步待核），今晚第 2 步核对命中（示例拟合），已按 R-c 修订，经 Codex 复核与正式评分验收；Codex 点名"仍属源码推断"的 F1、C5 失败原因已由完整日志确认；预检通过。
- **材料**：修订单 v5 的 `r2e-mr-040`（`hidden_test_text_replace`，`test_1.py` `26317e3d…` → `abd5a527…`）与 `r2e-mr-041`（`expected_file_replace`，`a7341a36…` → `4dc7bde2…`，56 → 57 键，新增 `test_run_app_raises_exception_on_server_start_failure[pyloop]`）；pins v6 `9a24b8693020…`，v6 逐字保留。派生镜像 `a12abdbed03c`（`rh2-r2e-derived/aiohttp:1c1c0ea35304-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `8cb0d20fb318…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-040/041`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` gold / noop / s1 / s2 / s3 第 4 行，s4 第 3 行；`F/status.json` 本题 6 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=a00b8ac2…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（57/57） | — |
   | C1：主任务已结束就不再走 `_cancel_tasks` | 合理替代解 | 1 | 1（57/57） | — |
   | C3：取消后 `gather(return_exceptions=True)` | 已登记 S2（v1 §10），本修订不针对；不能当合理正对照（Codex 第 13 行） | 1 | 1（57/57） | — |
   | noop | — | 0 | 0（55/57） | 原目标键（`test_1.py:923`）与新键（`:943`）：`assert not m.called` 失败 |
   | F1：只对 `RuntimeError` 不报告 | 触发反例（第 2 步示例拟合，原版 1） | 0 | 0（56/57） | 新键：`pytest.raises(OSError, match=…)` 已通过，随后 `assert not m.called` 失败（`:943`） |
   | C5：删掉单独取消主任务那一行 | 已知错误，兼 §4 第 3 步退化探测（在 gold 位置"关掉"，原版 0） | 0 | 0（50/57） | `TestShutdown` 7 键，见下 |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与本地副本一致（F1 在 `L/results/<本题>/cands/`，其余在 `C/`），失败键与试跑逐一相同。
   - **F1、C5 的失败原因已由完整日志确认**（Codex `L/codex_reviews/review_revision_aiohttp.md` 第 40 行要求）：
     - F1（`F/remote/s1_logs/…_4abdfd77.eval.log` 第 90–119 行）：`OSError("Address already in use")` 已被抛出并匹配，随后异常处理器仍被调用。源码推断"F1 对非 `RuntimeError` 仍既抛出又报告"成立。
     - C5（`F/remote/s2_logs/…_360fb8ec.eval.log`）：6 键在 `test_task.exception()` / `t.exception()` 处得到 `CancelledError`（第 285、501、719、946、1114、1364 行），`test_shutdown_close_websockets` 在 `assert client_finished` 失败且客户端任务显示为已取消（第 1188 行）。日志里没有 `Connect call failed` 或连接失败异常（出现的 `ClientConnectorError` 只是测试源码里的 `except` 行）。结论：失败来自测试任务随主任务一起被取消，即取消顺序被破坏，不是环境抖动。
     - 时序 watch 键 `TestShutdown.test_shutdown_handler_cancellation_suppressed` 在 gold、noop、F1、C1、C3 的正式评分里都 PASSED，只在 C5 下因同一个 `CancelledError` 失败；6 份日志都没有连接失败。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；7 条命令都符合预期。agent 身份下复现重复报告：日志记录 1 条（pr1_1）、异常处理器被调用 1 次（pr2_2）、同一 traceback 打印 2 次（pr3_3）；公开 `tests/test_run_app.py` 55 passed（pr4_5，约 37 s）。私有 gold 对照（root）全部 rc=0：0 条、0 次、1 次，与 09-25 相同。
3. **S1 处理**：第 2 步命中（revision_plan §1，第 11–44 行：唯一的"不报告"断言输入形态就是题面示例）。R-c 补一个非示例实例：服务器启动失败的 `OSError`，异常来源与类型都不同于示例；依据是题面标题与描述的一般表述、公开旧测试 `tests/test_run_app.py:664-677`（第 46–62 行）。Codex 通过（第 7–15 行）：未扩大需求、未放宽原断言、未改题面；C3 维持 S2 合理，但仍是错误候选，不能说"所有错误候选均已拦住"（第 13 行）。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，本题公开包行（`public_bundles_v0.jsonl` 第 1 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-040/041` 标明版本报告。批次运行条件属链路 |
| 训练候选 | yes | 核心要求"`run_app()` 抛出的异常不再报告"有示例与非示例两个实例的直接断言，另有后台任务照常报告、先单独取消主任务的回归键（revision_plan §6 第 137–147 行）；当前版本 noop 0、gold 1；§4 第 2 步已做，第 3 步 C5 为 0；C3（"吞掉错误"方向）得 1，但只违反 Ctrl+C 之后的边缘路径，按 v1 §10 记 S2 并登记；X1 已登记。旧复核认为用于训练时 C3 风险应升为"中"（`B2/review.md` 第 36 行），按 v1 仍是 S2，训练中按 D2 暂停规则处理 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题 gold 与目标测试逐字在 `22a12cc2` 公开初态里（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2：C3**（revision_plan 第 145 行）：Ctrl+C 之后 cleanup 抛出的错误，base 报告、gold 抛出、C3 两样都不做。探针与训练抽查用后检 `rh2/experiments/r2e_actor_20260925/postcheck/aiohttp_1c1c0ea3_cleanup_error.py`，只作诊断，不改分。
- **E5 / 时序**（`B2/card.md` 第 39–42 行；`B2/review.md` 第 35 行）：watch 键的首个请求不预热，与 `site.start()` 竞态；来源宿主机两次失败都不在发布镜像内，RH2 容器内此前 21/21 通过，今晚正式评分 5/5（C5 除外）。一旦翻转所有候选（含 gold）都判 0；先看堆栈并做同条件对照，不按抖动删键。
- **环境敏感键**（`B2/card.md` 第 44 行）：`test_run_app_preexisting_inet6_socket` 需要绑定 `::1`，`test_run_app_abstract_linux_socket` 需要抽象 Unix 套接字；换沙箱配置会让所有候选判 0。
- **X1**（`B2/card.md` 第 34 行）：`aiohttp__22a12cc2` 的公开工作树逐字包含本题 gold、目标测试与 changelog。
- **共享控制面**：包内测试辅助可被候选修改并在评分时重放（`B2/card.md` 第 33 行；R2E 共性）。
- **初态**：源镜像带 ` M Makefile` 与未跟踪的 `process_aiohttp_updateasyncio.py`，census 基线已按初态处理。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v5 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出。账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 146 s；评分 trusted setup 114–124 s（该步 300 s 硬时限，本题在同轮 7 题里最高之一，GPU 机并发评分时留意）；测试段 26–41 s。

## 证据索引

- 旧卡：`B2/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-040`、`r2e-mr-041`
- Codex：`L/codex_reviews/review_revision_aiohttp.md` 第 7–15、37–41 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
