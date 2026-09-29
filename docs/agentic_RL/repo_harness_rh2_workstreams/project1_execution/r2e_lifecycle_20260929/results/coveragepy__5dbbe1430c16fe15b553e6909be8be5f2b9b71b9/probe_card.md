# coveragepy `5dbbe143` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：on_hold**（暂挂；用户决定前只作问题定位）。题面没有说"重复"按什么判定，原目标测试按 slug 判定；按 slug、按消息两种读法都有公开依据（revision_plan §1，第 33–69 行；Codex 复核第 36–38 行），属 v1 §3 P5 的任务目标选择，规则是暂挂为问题定位、交用户决定。Codex（第 45 行）与批次记录（`L/README.md` 第 71 行）都写明整题不进探针。与读法无关的 R-c 已落并验收，准入五条按字面都成立，但不能据此改标 probe_ready。
- **恢复条件**（决定包见 revision_plan §2 第 77–105 行；"推荐 A"是执行者意见，本卡不替用户选）：
  - **选 A（按 slug）**：把 `revision_draft.json` 的 `statement_edits` 落为新的正式修订（新题目版本，公开包随之变化）→ 逐行核对题面改动、没看过隐藏测试与 gold 的新公开读者复读验收 → Codex 复核具体题面 → 按新版本重跑预检与正式评分，至少 gold、noop、CE4、CE1（此时 CE1 才是有公开依据的正确拒绝）→ 重写本卡。
  - **选 B（按消息）**：题面补"按消息判断重复"，原断言改为两条都显示，再补"同一消息只显示一次"；gold 变 0，须按 D4 独立核实 CE1 作正对照，再走同样的验收（revision_plan 第 82 行）。
  - **选 C（不修订）**：改记 `problem_localization_only`，不进探针、能力比较与训练。
- **材料**：修订单 v5 的 `r2e-mr-038`（`hidden_test_text_replace`，`test_1.py` `b95edf2e…` → `05bcd489…`）与 `r2e-mr-039`（`expected_file_replace`，`c65a3c08…` → `fc64a1db…`，75 → 76 键，新增 `ApiTest.test_warn_once_each_slug`）；**题面修订未落**。pins v6 `9a24b8693020…`，v6 逐字保留。派生镜像 `6eefea4028d4`（`rh2-r2e-derived/coveragepy:5dbbe1430c16-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `ab88e4c6bb5a…`）。
- **题目版本**：当前是"原题 + `r2e-mr-038/039`"，题面未改；选 A 或 B 后成为新的标明版本自建修订题。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` 各槽第 3 行；`F/status.json` 本题 5 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=6e81f8d8…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（76/76） | — |
   | CE3：按 slug 去重，另用独立集合 | 合理替代解 | 1 | 1（76/76） | — |
   | noop | — | 0 | 0（74/76） | `test_warn_once`、`…_each_slug`：`TypeError: _warn() got an unexpected keyword argument 'once'` |
   | CE4：第一次 once 之后全部静默 | R-c 的触发反例（第 4 步，原版 1） | 0 | 0（75/76） | `…_each_slug`：`'Hello from the second warning' not found`（`test_1.py:560`） |
   | CE1：按消息去重 | **P5 争议读法的对照**，不是已确认错误候选（Codex 第 42 行） | 0 | 0（75/76） | 只错原目标键：`'Warning, warning 2!' unexpectedly found`（`:549`）；新键通过，说明 R-c 没有替 P5 选边 |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与 `C/` 本地副本一致，失败键与试跑逐一相同。出处（`F/remote/`）：noop `noop_logs/…_a7977e41.eval.log` 第 30、44 行；CE4 `s2_logs/…_2b0c8fdb` 第 37 行；CE1 `s3_logs/…_b023970d` 第 35 行。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；5 条命令都符合预期。agent 身份下题面原例报 `TypeError`（mcve_statement 与显式 `PYTHONPATH` 版本都 rc=1，预期非零）；相关公开测试 `-o addopts=""` 6 passed。私有 gold 对照（root）全部 rc=0，原例只显示 `Warning, warning 1! (bot)`，与 09-25 相同。
3. **S1 处理**：R-c 一处（revision_plan §3，第 107–156 行）：不同 slug、不同消息的两条 once 警告都要显示，堵 CE4，在两种读法下都成立。Codex（第 33–46 行）：R-c 证据充分，可单独落正式修订单；它验证的是"两条不同警告首次均输出"，不是所有去重行为（第 40 行）；整题仍保持 P5 待决（第 45 行）。决定包里"题面修订机制尚待实现"的过时说法已按 Codex 更正（第 46 行）。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；题面未改，本题公开包行（`public_bundles_v0.jsonl` 第 7 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛。P5 待决期间只可作此用途，任何运行结果单列，不并入能力分数 |
| 能力比较 | no（当前版本） | 原目标键按 slug 判定，按消息的实现得 0（CE1），而两种读法都有公开依据；按 v1 §3 P5 与 §11，题意争议未消解的题不进比较分母。恢复见"结论" |
| 训练候选 | no（当前版本） | 同上。选 A / B 之后，旧版本证据不能解除新版本的条件（v1 §2），须完成新版本的公开读者验收与正式评分 |
| 留出评测候选 | no（当前版本） | 同上；定案后仍受 D3 仓库划分与 X1（本题 gold 在同仓 4 题初态中）约束，且只能作标明版本的自建评测 |

## 剩余事项

- **P5 待用户决定**（阻塞，见"结论"）。按 Codex 第 38 行：推荐 A 的理由是来源意图和改动成本，不能据此说按消息实现违反当前公开要求。
- **gold 的潜伏副作用**（revision_plan 第 163 行；`B1/card.md` 第 93–98 行）：G1 首次调用时快照 `disable_warnings`，之后 `set_option` 不生效；G2 once 与非 once 共用抑制列表；G3 `slug=None` 也记入列表。当前没有调用点触发，三个选项都不改变它们。
- **R04**（`B1/card.md` 第 47–50 行）：base 版测试辅助的假 `capture_warning` 不接受 `once`，只影响"给现有调用点加 `once=True`"这类超出题面的改法；`r2e_tests/test_2.py` 未动。
- **共享控制面**：隐藏测试继承候选可改的 `tests/coveragetest.py`（又导入 `tests/helpers.py`），不改源码也可能让目标键通过（`B1/screening_record.json` issue I5；R2E 共性）。
- **X1**（`B1/screening_record.json` issue I7）：本题 gold 原样出现在 `016af5f6`、`97997d2c`、`f5eb5f21` 的 base 中，`ea6906b0` 的 base 含其演进版；同族必须同侧。
- **链路**（恢复后才适用）：与同批其它题相同，见 `L/probe_chain_check.md` §0 第 9–20 行与 Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行。本机开销：rollout 从起容器到可信初始化完成约 53 s；评分 trusted setup 62–63 s（该步 300 s 硬时限）；测试段约 9 s。模型实际收到的题面消息未捕获。

## 证据索引

- 旧卡：`B1/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订与决定包：`L/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-038`、`r2e-mr-039`；`L/board.json` 本题 `state=on_hold`、blocker P5
- Codex：`L/codex_reviews/review_revision_coveragepy.md` 第 33–46、48 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_{gold,noop,s1,s2,s3}.jsonl` 第 3 行、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
