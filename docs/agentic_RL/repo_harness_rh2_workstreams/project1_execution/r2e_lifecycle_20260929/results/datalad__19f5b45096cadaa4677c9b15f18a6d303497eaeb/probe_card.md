# datalad `19f5b450` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v6`（本题账本 `F/ledgers/ledger_<槽位>_budget1200.jsonl` 各 1 行，完整日志是 `F/remote/<槽位>_logs/` 下文件名带 `-b-` 的那份），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v6/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready（带链路条件：探针机的评分时限）**。题目层面五条都满足：正式评分 7 行全部与期望一致（正对照 gold）；devcheck 13 项全真；S1（示例拟合、两处第 4 步漏判）已按 R-c 修订，经 Codex 复核与正式评分验收；预检通过。**但这 7 行全部是在评分时限放宽到 1200 s 下得到的**（`rh2/experiments/r2e_lifecycle_20260929/replay_grade_budget.py` 只把 `env_reset_timeout_seconds` 从 300 s 改为 1200 s，评分语义不变），**缺省 300 s 下没有验证**：本机缺省预算实跑的 noop / gold（修订前材料）都在评分前的控制面保护（`chown -R` 整棵 `/testbed`，含 `.venv`）超时，记 `infra_failure`、没有分数；v6 材料没有在缺省预算下跑过。所以本题进探针的前提是先定探针机的评分时限（晨报待决定第 3 项）。这是链路条件，不是本题材料不满足；时限未定就派发，本题只会产出无效尝试。
- **材料**：修订单 v6 的 `r2e-mr-048`（`hidden_test_text_replace`，`test_1.py` `b2c90c1b…` → `6f1d831d…`，原目标测试之后新增 3 个只断言退出码的测试）、`r2e-mr-049`（`expected_file_replace`，`42b8016a…` → `e51fad3d…`，19 → 22 键，新增 `test_run_exit_code_other_value`、`test_run_missing_input_exit_code`、`test_run_on_failure_ignore_exit_code`，均 PASSED）；pins v7 `27c0bb40bd6f…`。v7 修订单逐字保留这两条、只追加 aiohttp `240d`；当前评分包的隐藏测试树 `ad814752…` 与 v6 评分日志头相同。派生镜像 `261d5e44af6e`（`rh2-r2e-derived/datalad:19f5b45096ca-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `754093b7458f…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-048/049`），不当原 benchmark 报；gold 在修订版上仍为 1。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 本题 7 行 `match=true`、`budget_relaxed_env_reset_1200s=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（22/22） | — |
   | K1：只转发 `action=='run'` 的 `CommandError`，经 fd 2 报告 | 合理替代解 | 1 | 1（22/22） | — |
   | noop | — | 0 | 0（20/22） | 原目标键 `assert 1 == 3`；`…_other_value` `assert 1 == 5` |
   | H：分支里写死 `exit_code = 3` | 触发反例（第 2 步），兼 §4 第 3 步退化探测（与输入无关的固定结果，原版 1） | 0 | 0（20/22） | `…_other_value` `assert 3 == 5`；`…_missing_input_…` `assert 3 == 1` |
   | K3：取首条失败记录的 `exit_code`、缺字段不回退 | 触发反例（第 4 步，原版 1） | 0 | 0（21/22） | `…_missing_input_…` `assert None == 1`（真实进程会以 0 退出） |
   | K2：删掉 `run.py` 的 `try/except`，`CommandError` 直接上抛 | 触发反例（第 4 步，原版 1） | 0 | 0（21/22） | `…_on_failure_ignore_…` `assert 3 == 0` |
   | K4：gold 加一行 `print(…, file=sys.stderr)` | stderr 规格争议候选（原版 0） | 0 | 0（21/22） | 原目标键，失败在 `run_main` 的"stderr 为空"断言（`test_1.py:87`） |

   "原版"指 09-25 第二批正式评分（`runs/r2e_actor_20260925/grader/ledger_d19f5_*.jsonl`，旧镜像 `851a10b6`，19 键；H 的这份账本在 `B2/review.md` 第 44 行曾记为本地缺失，现已在该目录）。各行 `git_apply` 成功、测试段完整、日志不截断、键集相等（无 missing / unexpected），补丁摘要与 `F/plan.json` 所列本地副本（gold 在私有包，其余在 `C/`）一致，失败键与试跑（revision_plan 第 119–127 行）逐一相同。账本 `phases.grader_trusted_setup`（可信 setup + 控制面保护）：6 行 333.8–339.1 s（三路并发，同时还在跑放宽预算复验）；v6 另两路结束后单独跑的 K4 为 241.3 s。测试段 25–29 s。
2. **devcheck**（`D/orig/attempt.json`，同一镜像 `261d5e44…`）：13 项 checks 全真；7 条命令（预检、env、公开读者 5 条）都符合预期。agent 身份下复现题面缺陷：pr1 五例依次退出 1 / 1 / 0 / 1 / 0（带不带 `--explicit` 的 `exit 3` 都退 1），pr2 的 `run_main(exit_code=3)` 断言失败（rc 1，预期内），console script 退 1（pr5）；公开 `test_main.py` 选中的 7 项、`test_run.py` 2 项、`test_rerun.py::test_run_failure` 都通过。私有 gold 对照（root、断网）6 条全部 rc 0：五例依次 3 / 3 / 0 / 1 / 0，console script 退 3。
3. **S1 处理**：R-c 一处、三个新键（`L/results/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/revision_plan.md` §1–§3，第 20–96 行）：`run 'exit 5'` → 5（换退出码、去掉 `--explicit`，堵 H）；输入缺失 → 1（堵 K3）；`--on-failure ignore` → 0（堵 K2）。新测试 `expect_stderr=True`，即不检查 stderr；原目标测试一字未改。Codex 通过（`L/codex_reviews/review_revision_misc.md` 第 7–21 行），**限定**：①准确分类是"第一项为核心要求的非示例实例，后两项为同一失败处理链必须保留的公开行为"，不能统称"所有失败都转发底层退出码"（第 15 行）；②K4 仍称"stderr 规格争议候选"，不能因为它仍为 0 就认定它是已证明的错误解（第 19 行）；③`chown -R` 超时单列为 `infra_failure`，不能充当候选得 0，也不能据此否定本题材料（第 53 行）。Codex 列的正式评分（第 50 行）今晚已完成。
4. **公开包干净**：devcheck `r2e_preflight_ok`（解释器、隐藏测试、git 历史三项 ok）；git sanitize 后 refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 12 行）在 09-29 起各次摄入里逐字相同；题面与 gold 无逐行重叠（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | conditional | 开发路径与评分依据已核，按 `r2e-mr-048/049` 标明版本报告。**只差链路条件**：探针机评分须用本卡验证过的时限口径，或在目标机实测保护一段稳定低于 300 s；否则本题评分记 `infra_failure`、`reward=None`，只能作无效尝试单列，不算模型失败，也不悄悄移出分母（`L/codex_reviews/review_probe_chain_20260929.md` 第 76 行）。另：只错原目标键、且失败在 `test_1.py:87`（stderr）而不在 `:83`（退出码）的样本，标"疑似规格争议"复核，原始 reward 保留（`B2/review.md` 第 34、109 行） |
| 训练候选 | conditional | 质量条件已齐：核心要求有直接断言（原例 + `exit 5` 非示例实例），另两条同链路公开行为有键（revision_plan 第 138 行）；当前版本 noop 0、gold 1；§4 第 2 步（`exit 5`）、第 3 步（H）、第 4 步（K2、K3）已做；S2、X1 已登记。**只差同一链路条件**：训练评分同样受这一 300 s 时限约束，须先让本题在训练机上拿到有效分数。stderr 争议按 v1 §8 抽查失败样本 |
| 留出评测候选 | conditional | 差：① 同上链路条件；② D3 仓库划分未定，本题初态含 `58ba5165` 的修复（X1），两题须整仓同侧；③ 若探针结果用于选模型、调提示或调配方即不再符合；④ 只能作标明版本的自建评测 |

## 剩余事项（第一项链路时限阻塞派发，其余已登记、不阻塞）

- **链路：评分时限（派发前须落定）**
  - 缺省 300 s：本机 noop / gold 都 `failed_to_grade`，`grading_control_surface_protect_timeout_after_300s`（`runs/r2e_lifecycle_20260929/env_verify/ledger_l0_{noop,gold}.jsonl` 第 3 行；修订前材料、镜像 `77f982d0`）。该时限即 `GradingEnvSpec.env_reset_timeout_seconds`，CLI 与环境变量都调不了（`L/probe_chain_check.md` 第 34 行）。
  - 今晚本机本题共 11 次评分：缺省预算 2 次都超时；放宽的 9 次里 8 次上述一段合计 308–339 s（含 v5 任务面、修订前材料的放宽复验 noop 0〔18/19〕、gold 1〔19/19〕，`runs/r2e_lifecycle_20260929/budget_v5/ledger_{noop,gold}.jsonl` 第 2 行，只作环境对照），只有并发较低时的 K4 为 241 s。所以"本机缺省预算必超时"准确说是"本机并发评分时基本都超时"。
  - 与宿主有关：09-25 第二批在另一台机器上用缺省预算，同一段只要 35–54 s，6 行都拿到有效分数（旧镜像）；本机 overlay2 未开 metacopy，`chown` 会整文件复制上层（`L/README.md` 第 65 行）。
  - 放宽口径：包装只替换这一时限，补丁、投影、测试脚本、解析与计分不变；按 Codex，这一项同时管 checkout、census、可信 setup、控制面保护与前后观测各步，不只是 `chown`（`review_probe_chain_20260929.md` 第 68 行）；本轮候选阶段仍是缺省 900 s（账本 `budgets`）。
  - 恢复条件（用户 / A 线定，`L/morning_summary_20260929.md` §3 待决定第 3 项）：给 R2E 大环境题显式评分预算（A 线开放配置，或探针沿用本卡的 1200 s 包装）并在目标机测通；或在目标机实测该段稳定低于 300 s。只降并发不能保证（Codex 同文第 76 行）。
- **stderr 规格争议（登记，低）**：原目标测试沿用 `run_main` 默认 `expect_stderr=False`，要求 Python 层 `sys.stderr` 为空：经 `print(file=sys.stderr)` 输出说明的修复判 0，经日志、`ui.error`、`os.write(2, …)` 输出的不受影响。公开依据两边都有（`B2/review.md` 第 27–34 行）；本次修订没把它扩到新路径。
- **S2 / 未覆盖**（revision_plan 第 144 行）：`--on-failure continue`、一次调用多条失败且退出码不同、rerun、run-procedure（公开读者判为多解，不加断言）；Python API 仍抛 `IncompleteResultsError` 只由不计分的公开 `test_run.py` / `test_rerun.py` 保护。已知违反者 K2 被 ignore 键挡住；审查中构造的 C4（在 `run_command` 里改回抛 `CommandError`）没有评分，复核判断它对隐藏测试的效果与 K2 相同（`B2/review.md` 第 59–64 行），据此推断也会被 ignore 键挡住（未实跑）。
- **题面与公开文档（P4 登记）**：Run docstring、0.16.0 changelog、`cli.rst` 对失败语义说法不一，会把解题者引向 K2 路线（此版本得 0）；题面示例三处导入写错（`B2/card.md` 第 38 行）。
- **解题侧**：agent 的 HOME 没有 git 身份，不设就 `create` 报 `Author identity unknown`，公开提示没说（`B2/card.md` 第 40 行；devcheck `env.out` 仍有警告）；无 pip、不联网；git-annex、console script 可用。
- **环境敏感键**：`test_help_np` 在 stdin 不是 TTY 时 SKIPPED、不成键；若改用 TTY 评分，所有候选（含 gold）都会多一个键而判 0（`B2/screening_record.json` issue `datalad_19f5-skip-depends-on-tty`）。
- **共享控制面**：隐藏测试导入候选可改的 `datalad.tests.utils_pytest` 等辅助，评分时不重置（`B2/card.md` 第 32 行）。
- **X1**：本题初态含 `58ba5165` 的修复（其 gold 新增 6 行全部命中，`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`；`B2/card.md` 第 41 行）；本题 gold 不在其它题初态里。
- **链路（共同项）**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v6 正式评分即此口径，本题另加时限包装）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 371 s（devcheck `stages`）；放宽预算下每次评分约 12 分钟（同一路相邻两行的开始时间差）。

## 证据索引

- 旧卡：`B2/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v7.json`（v6 起）的 `r2e-mr-048`、`r2e-mr-049`
- Codex：`L/codex_reviews/review_revision_misc.md` 第 7–21、46–53 行；`L/codex_reviews/review_probe_chain_20260929.md` 第 68、76、78 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*_budget1200.jsonl`、`F/remote/*_logs/*-b-*.eval.log`、`F/remote/r2e-v6-u{1,2,3}.log`（每次本题评分前记 `{"replay_grade_budget": {"env_reset_timeout_seconds": 1200.0}}`）
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v6/summary.json`
- 时限对照：`runs/r2e_lifecycle_20260929/env_verify/ledger_l0_{noop,gold}.jsonl` 第 3 行；`runs/r2e_lifecycle_20260929/budget_v5/ledger_{noop,gold}.jsonl` 第 2 行；`runs/r2e_actor_20260925/grader/ledger_d19f5_*.jsonl`
