# pandas `32dd55cb` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`R` = `L/results/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0`，`F` = `runs/r2e_lifecycle_20260929/formal_v6`（本题是缺省预算：账本 `F/ledgers/ledger_{gold,noop,s1,s2,s3,s4}.jsonl` 各 1 行，完整日志是 `F/remote/<槽位>_logs/` 下文件名不带 `-b-` 的那份），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v6/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0`，`B1` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0`。键简称：T1 = `TestDataFrameAnalytics.test_mean_extensionarray_numeric_only_true`，T2 = `TestDataFrameAnalytics.test_mean_datetimelike_numeric_only_false`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 6 行全部与期望一致（正对照 gold，缺省预算）；devcheck 13 项全真；T2 误拒合理解（R-b）与"只修 mean"的现存漏判（R-c：sum 对照，加上 R-b 配套的含缺失值均值断言）一起修订，经 Codex 复核与正式评分验收；Codex 标为"源码推导"的 C4 实际值已由正式日志确认；预检通过。
- **材料**：v3 起的 `r2e-mr-016`（新增私有 `r2e_tests/conftest.py` `053ce359…`）、`r2e-mr-017`（期望 13 键 ERROR → PASSED，`b115c1cc…` → `9771cde5…`），加修订单 v6 的 `r2e-mr-050`（`hidden_test_text_replace` 两处 edit，`test_1.py` `4a153a37…` → `3ad05d5c…`；期望映射不变，92 键全 PASSED）；pins v7 `27c0bb40bd6f…`。v7 修订单逐字保留上述条目；当前评分包的隐藏测试树 `94ed0f7b…` 与 v6 评分日志头相同。派生镜像 `8a3ebfbaf0c3`（`rh2-r2e-derived/pandas:32dd55cb8331-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `4c0546cbe086…`，镜像材料步骤含 `r2e-mr-016`、`r2e-mr-050`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-016/017/050`），不当原 benchmark 报；gold 在修订版上仍为 1。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 本题 6 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold（EA 块一律改调 `values._reduce`） | 正对照 | 1 | 1（92/92） | — |
   | C1：只对数值 EA 调 `_reduce`（`runs/r2e_actor_20260925/grader_cands/pandas_32dd_C1_numeric_ea_only.patch`） | 原误拒（首批正式 91/92，只错 T2），已纠正 | 1 | 1（92/92） | — |
   | noop | — | 0 | 0（91/92） | T1：题面那条 `ValueError`（`test_1.py:914`）；T2 修订后通过 |
   | C3g：gold 式分派只对 mean 生效（`R/cands/`） | 现存漏判（当前材料试跑 92/92，非正式评分），兼 §4 第 3 步退化探测 | 0 | 0（91/92） | T1 的 sum 对照抛同一 `ValueError`（`:929`） |
   | C3：C1 再加 `name == 'mean'` 条件（`R/cands/`） | 放宽 T2 后会被放行的已知错误 | 0 | 0（91/92） | 同上（`:929`） |
   | C4：窄修 `IntegerArray.sum`，让它接受 `axis` / `dtype`（`R/cands/`） | 同上 | 0 | 0（91/92） | T1 含缺失值的均值：`[left]: [2.0, 1.3333333333333333]`，期望 `[2.0, 2.0]`（`:925`） |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等（无 missing / unexpected）；补丁摘要与 `F/plan.json` 所列本地副本一致。**Codex 说"C4 的 4/3 是源码推导，截断日志未直接保留该实际值"（`L/codex_reviews/review_revision_misc.md` 第 40 行），现由正式日志 `F/remote/s4_logs/evallog_replay-r2e-v6-s4-0928202_e3fea27a.eval.log` 第 63 行直接确认**；试跑日志截掉的 noop、C3、C3g 失败点也由正式日志给出（`:914`、`:929`，对应修订后 `test_1.py` 的原例均值与 sum 对照）。账本 `phases.grader_trusted_setup` 75–79 s（300 s 时限内），测试段 11–14 s。
2. **devcheck**（`D/orig/attempt.json`，同一镜像 `8a3ebfba…`）：13 项 checks 全真；6 条命令都符合预期。agent 身份下：题面原例逐字复现 `ValueError: the 'dtype' parameter is not supported in the pandas implementation of sum()`（`mcve_statement` rc 1）；`sum(numeric_only=True)` 抛同一错误（`mcve_sum` rc 1，说明 sum 是同一缺陷的非示例实例）；公开 `frame/test_analytics.py` 91 passed / 1 skipped，`arrays/integer/test_function.py` 25 passed。私有 gold 对照（root、断网）只有 `test_analytics` rc 1：公开 `test_mean_datetimelike_numeric_only_false` 写死旧文字，gold 抛 `mean is not implemented for PeriodArray…`（`test_analytics.py:900`）。这正是 R-b 处理的冲突，按 P6 登记（见剩余事项），不是新镜像回归；`test_function.py` 在 gold 下 25 passed。
3. **S1 处理**：`R/revision_plan.md` §1–§3（第 22–112 行），三处一起落：R-b 让 T2 接受两条有文档的 Period 报错文字（datetime / timedelta 均值与"Period 必须抛 TypeError"保留）；R-c sum 对照（v1 §11 已列，堵 C3、C3g）；R-c 题面式混合帧含缺失值的均值（R-b 的配套，堵 C4）。Codex 通过（`L/codex_reviews/review_revision_misc.md` 第 23–44 行），**限定**：①缺失值均值未在 §11 单列，但在 §5 R-c 授权内（第 29 行）；②两条新断言"对当前草案及已知反例"都不能单独删掉，依据是逐项移除对照，不是穷举（第 33–40 行）；③sum 不锁 dtype，与 `r2e-mr-016/017` 不冲突、不需要合并（第 42 行）。Codex 列的正式评分（第 51 行）今晚已完成。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；git sanitize 后 refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 32 行）在 09-29 起各次摄入里逐字相同；题面与 gold 无逐行重叠（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-016/017/050` 标明版本报告。旧卡"T1 过、只错 T2 的解单独归类"的诊断口径（`B1/card.md` 第 62 行）随 R-b 作废：修订后 T2 是回归键，只错 T2 表示改坏了 datetime / timedelta 均值或 Period 报错。P6 按剩余事项解读。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：题面原例（全 Int64 帧均值）、题面式混合帧含缺失值的均值、非 mean 归约 sum，另有 T2 与 90 个回归键（revision_plan 第 143 行）；当前版本 noop 0、gold 1；§4 第 2 步（sum、含缺失值的混合帧）与第 3 步（C3g）已做，第 4 步的已知候选 C3、C4 为 0；S2 已登记；X1 按机械扫描登记（见剩余事项），训练时控制同源重复采样 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定；按扫描线索，本题修复出现在 `19c5eea5`、`294cbc8d` 的初态，本题初态含 `87787609` 的修复，pandas 须整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **P6（登记）**：公开 `pandas/tests/frame/test_analytics.py:896–900` 写死旧的 Period 报错文字；gold 式修法（所有 EA 块改调 `_reduce`）会让它失败，C1 式不会。探针分析时，模型改这条公开测试不算钻空子，它失败也不算模型改错（v1 §3 P6）。公开提示"不要改仓库的测试文件"会把解题者推向保留旧文字的路线；此版本两条路线都得 1。
- **S2 / 未覆盖**（revision_plan 第 155 行）：`prod/min/max/median/std/var` 等其它归约（按静态阅读，base 上报的是另一种错误）、整列缺失（多解）、`axis=1`、默认 `numeric_only=None` 路径（题面未要求，gold 也未修）；只修 mean 与 sum 的实现仍可能得 1，是有意不扩的范围。gold 在 `numeric_only=False` 且含 datetimelike 列时会截断 Int64 均值，未测、不影响判分（`B1/card.md` 第 32–36 行，`B1/screening_record.json` issue I5）。
- **未实跑的合理路线**：C1 的公开测试是否全过仍是代码推断（revision_plan 第 25 行）；旧卡列的"只在 `numeric_only=True` 时分派""在 nanops 层支持掩码"等写法（`B1/card.md` 第 52–58 行）没有构造补丁、没有评分。新断言只比数值，不绑实现位置。
- **环境敏感键**：期望绑定"无 SciPy"：`test_1.py:564` 因缺 SciPy 被 SKIPPED、不成键；评分环境若装了 SciPy，该测试成键，所有候选会因键集不等判 0（`B1/card.md` 第 46 行）。
- **共享控制面**：评分 rootdir 为 `/testbed`，候选新增的根 `conftest.py`、`setup.cfg` 的 pytest 段、对 `pandas/_testing.py` 的改动都会在评分时生效；账本有 `candidate_touched_conftest_or_fixture` 观测字段（`B1/screening_record.json` issue I6）。
- **解题侧**：`.venv` 下 Python 3.7.9、pytest 7.4.4，有 pip 但不联网；初态带 versioneer 相关的已跟踪改动（`setup.cfg` 只剩 `[versioneer]` 段、`pyproject.toml` 已删），不要回退，pandas 自带的 pytest 配置因此不生效（devcheck `env.out`；`B1/public_read.md` 第 83 行）。
- **X1（机械扫描线索，未人工核对；旧审查未查跨题关系，`B1/card.md` 第 48 行）**：本题 gold 新增 3 行逐字出现在 `19c5eea5`、`294cbc8d` 的公开初态（`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`）；T1 的测试名出现在 `19c5eea5`、`294cbc8d`、`4ec87eb9`、`7dd34ea7`、`f656217a` 的初态（`cross_task_test_scan.json`，只比函数名，可能巧合）；本题初态含 `87787609` 的修复（5/5 行）及其测试名。
- **链路（共同项）**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v6 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 92 s（devcheck `stages`）；评分可信 setup + 保护 75–79 s、测试段 11–14 s。

## 证据索引

- 旧卡：`B1/{card.md,screening_record.json,review.md,public_read.md}`（旧 usage 只有 `intended_use`；`card.md` 第 3 行有 09-25 协调者更正）
- 修订：`R/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v7.json` 的 `r2e-mr-016`、`r2e-mr-017`（v3 起）与 `r2e-mr-050`（v6 起）
- Codex：`L/codex_reviews/review_revision_misc.md` 第 23–53 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_{gold,noop,s1,s2,s3,s4}.jsonl`、`F/remote/*_logs/`（不带 `-b-` 的日志）、`F/remote/build.log`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v6/summary.json`
