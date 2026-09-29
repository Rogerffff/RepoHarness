# coveragepy `ea6906b0` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v5`（完整评分日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v5/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5`，`C` = `runs/r2e_actor_20260925/grader_cands`，`B2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 6 行全部与期望一致（正对照 gold）；devcheck 13 项全真；两处 S1 已按 R-c 修订，经 Codex 复核与正式评分验收，Codex 点名的两项待确认（C-B 失败原因、git 在正式评分身份下可用）已由完整日志确认；预检通过。
- **材料**：修订单 v5 的 `r2e-mr-036`（`hidden_test_file_add`，新增 `r2e_tests/test_2.py` `f29c0497…`，`test_1.py` 不动）与 `r2e-mr-037`（`expected_file_replace`，`7ab45968…` → `6d252beb…`，46 → 48 键，新增 `HtmlGitignoreTest.test_html_report_is_ignored_by_git`、`ReportingTest.test_no_data_to_report_on_html`）；pins v6 `9a24b8693020…`，v6 逐字保留。派生镜像 `110ba1cbe8ee`（`rh2-r2e-derived/coveragepy:ea6906b092d9-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `9b3c2352bdf4…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-036/037`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/` 各槽第 2 行；`F/status.json` 本题 6 行 `match=true`；日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=6c721a51…` 等于 v5 评分包摘要）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（48/48） | — |
   | C-A：只在原本为空的目录写 `*` | 合理替代解 | 1 | 1（48/48） | — |
   | noop | — | 0 | 0（41/48） | 6 个 `HtmlDeltaTest` 目标键（`File 'htmlcov/.gitignore' should exist`）+ git 键（9 个报告文件未被忽略） |
   | C-B：只写空 `.gitignore` | 触发反例，兼 §4 第 3 步退化探测（空产物，原版 1） | 0 | 0（47/48） | git 键：`assert not_ignored == []`，9 个文件未被忽略，首个 `report_out/coverage_html.js`（`test_2.py:62`） |
   | RE：数据检查前就建目录写入 | 触发反例（第 4 步，原版 1） | 0 | 0（47/48） | 无数据键：`File 'htmlcov' shouldn't exist`（`tests/coveragetest.py:284`） |
   | C-C：gold 加 `encoding=` | 公开替身约束对照（原版 0） | 0 | 0（41/48） | 原 7 个 `HtmlDeltaTest` 键：`TypeError: open() got an unexpected keyword argument 'encoding'`；两个新键通过 |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等；补丁是试跑用过的同一份远端副本，账本补丁摘要与 `C/` 本地副本一致，失败键与试跑逐一相同。出处（`F/remote/`）：noop `noop_logs/…_f3b8b2a8.eval.log` 第 44–313 行；C-B `s2_logs/…_3d635062` 第 50–62 行；RE `s3_logs/…_1a7d0043` 第 43 行；C-C `s4_logs/…_60aa5ec6` 第 54 行起；gold `gold_logs/…_e49905c7` 第 173 行（48 passed）。
   - **Codex 的两项待确认已核**（`L/codex_reviews/review_revision_coveragepy.md` 第 27、29、31 行）：① C-B 失败在 `not_ignored == []`，不再是推断；② 正式评分以 uid 54322、`rh2.grader_sandbox_profile.v1`、`deny_all` 运行，gold 通过 git 键，noop 与 C-B 都越过了测试里对 `git init` / `git status` 返回码的断言、失败在最后的比较上——git 在正式评分身份下可用。"至少覆盖 gold、noop、C-B、RE"已满足。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；9 条命令都符合预期。agent 身份下复现缺陷：报告目录没有 `.gitignore`（pr1_1），在临时仓库里 `git status` 列出 8 个报告文件（pr2_2）；agent 能找到 `/usr/bin/git`；`-o addopts=""` 跑公开 `tests/test_html.py` 46 passed（pr5_6）。pr4_4、pr4_5、pr6_7 的 rc=4 是命令伪影（`-p no:cacheprovider` 与 `--failed-first` 冲突），私有 gold 对照同为 rc=4，与 09-25 相同；gold 下 `.gitignore` 为 `# Created by coverage.py\n*\n`，`git status` 不再列出报告文件。
3. **S1 处理**：R-c 两处（revision_plan §1，第 25–30 行）：H1 用真实 git 判断报告文件是否都被忽略（第 3 步，堵 C-B）；H2 从公开 `tests/test_coverage.py:1843-1848` 原样搬入"无数据时不建目录"（第 4 步，堵 RE）。Codex 通过（第 19–31 行）：搬入的方法与公开旧测试逐字一致，原 mock 测试未替换（不是 R-e），没有钉死 `.gitignore` 内容，没有删改原断言。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；新增的 `test_2.py` 只在评分包里，评分时才放入（日志 `RH2_SETUP_EXPECTED_TEST_FILES=4`）；本题公开包行（`public_bundles_v0.jsonl` 第 9 行）在材料 v3、v4、v5 与当前摄入里哈希相同。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-036/037` 标明版本报告。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言（revision_plan §5 第 170–177 行：有 `.gitignore`、git 真的忽略报告文件、无数据不建目录）；当前版本 noop 0、gold 1；§4 第 2 步（git 键用非默认目录 `report_out`）与第 3 步（C-B）已做；S2、X1 已登记。训练价值另看：低难度题（`B2/card.md` 第 8–9 行） |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题初态含同仓 3–4 题的修复（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2 / 未覆盖**（revision_plan 第 192–195 行）：gold 无条件覆盖用户已有的 `.gitignore`（如 `-d .`）；CLI 路径 `coverage html -d`；成功时 stdout 不多出消息（公开 `tests/test_process.py`、`tests/test_plugins.py` 有测试，devcheck pr6_7 因 rc=4 伪影实际没有跑到）。
- **公开可见的替身约束**：`HtmlDeltaTest` 把 `coverage.html.open` 换成不收 `encoding` 的替身，gold 式写法加 `encoding=` 就得 0（C-C）；公开测试同样失败，旧卡判为不算误拒（`B2/card.md` 第 37 行）。
- **新增评分依赖 git**：评分侧工具，按 v1 §6 记录即可。GPU 机上的镜像须保留 `/usr/bin/git`；缺失时 gold 会在 git 键失败而暴露，不会静默放过（revision_plan 第 181–185 行）。
- **共享控制面**：隐藏测试依赖候选可改的 base 版 `tests/` 辅助（新无数据键用 `tests/coveragetest.py` 的 `assert_doesnt_exist`），把辅助改成空操作可以蒙混（`B2/card.md` 第 41 行；R2E 共性，不按单题修）。
- **X1**（`B2/card.md` 第 32 行）：本题初态含 `5dbbe143`、`97997d2c`、`f5eb5f21`（可能还有 `016af5f6`）的修复；本题修复不在其它题里。
- **题面**：示例写成模块级调用、"被 git 跟踪"的说法不准确，都不影响理解（`B2/card.md` 第 25 行）。
- **解题侧**：无 pip、不联网；`-p no:cacheprovider` 与 `--failed-first` 冲突，要用 `-o addopts=""`。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v5 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返核对不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出。账本 `env_qualification=absent`，能力统计前补接资格账本或单列（Codex 第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 141 s；评分 trusted setup 88–89 s（该步 300 s 硬时限）；测试段 5–7 s。

## 证据索引

- 旧卡：`B2/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）
- 修订：`L/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-036`、`r2e-mr-037`
- Codex：`L/codex_reviews/review_revision_coveragepy.md` 第 19–31、48 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_{gold,noop,s1,s2,s3,s4}.jsonl` 第 2 行、`F/remote/*_logs/`
- devcheck：`D/orig/attempt.json`、`D/orig/captures/`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v5/summary.json`
