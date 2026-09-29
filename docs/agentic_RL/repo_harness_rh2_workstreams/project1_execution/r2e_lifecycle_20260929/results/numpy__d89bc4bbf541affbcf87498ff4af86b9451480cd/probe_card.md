# numpy `d89bc4bb` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`R` = `L/results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`（本题全部审查产物，含独立复核 `reviewer_initial.md`〔读主审产物前封存〕与 `review.md`；修订两轮；没有旧审查卡），`S` = `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e`，`F` = `runs/r2e_lifecycle_20260929/formal_v10`（账本 `F/ledgers/ledger_{gold,noop,s1…s8}.jsonl` 各 1 行，完整日志 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v10/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`（v10 镜像），`D0` = `runs/r2e_lifecycle_20260929/devcheck/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`（修订前镜像），`INV` = `runs/r2e_lifecycle_20260929/inv/numpy_d89b`（协调者修订前实跑），`CX1` / `CX2` = `L/codex_reviews/review_revision_numpy_d89b.md` / `review_revision_numpy_d89b_r2.md`，`HT1'` / `HT2'` = 修订后的 `r2e_tests/test_1.py` / `test_2.py`（`S/revisions/files/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/r2e_tests/`，544 / 783 行）。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：v10 正式评分 10 行全部与期望一致（缺省 300 s 时限，无放宽），正对照是原 gold（1，84/84）；完整日志确认 DEG、REN、D1 各自只在针对它的 2 个新键失败，noop 恰好 10 个预期键失败，84 键严格相等；两次 devcheck 各 13 项全真；三个 S1（退化候选 DEG、D1，删接口候选 REN）与一个误拒（ORD）按 R-c×3、R-b 修订，经独立复核、Codex 两轮复核与正式评分验收；预检通过。
- **Codex 限定（照录）**：CX2 第 13 行"这只是修订草案复核通过，不是正式评分或探针准入通过"；CX1 第 31、50 行要求重建材料后正式复跑、核补丁交付与完整 84 键执行——v10 已完成（第 1 条），本卡据此给准入。R-c3（`density=False` 返回计数）属**公开 API 先例推知，不是题面明示**（CX1 第 12 行）。
- **材料**：修订单 v10 的 `r2e-mr-058`（`test_1.py` `b680bb79…` → `cf992ee4…`）、`r2e-mr-059`（`test_2.py` `1d485d6e…` → `e0b2dd5f…`），均为 `hidden_test_text_replace`：`TestHistogram2d`、`TestHistogramdd` 各加 `test_density_false`、`test_density_outliers`、`test_normed_still_accepted`，`HT2':754` 改为 `assert_allclose`；`r2e-mr-060`（`expected_file_replace`，`f7c02eef…` → `0135e7b6…`，78 → 84 键，新增 6 个 PASSED，无改无删）（`S/revisions/material_revisions_v10.json` 第 1775 行起）。本题此前没有材料修订。pins v11 `7934bddc6d6d…`；其后 v11（08:28，pins v12）只追加 aiohttp `4075`、pillow `2d01`，本题三条逐字保留，当前评分包第 22 行的隐藏测试树 `6fcb630f…` 等于各评分日志头的 `RH2_SETUP_HIDDEN_TESTS_TREE`。派生镜像 **`8462f1c29203`**（`rh2-r2e-derived/numpy:d89bc4bbf541-r2e_derive_v1m2s`，来源镜像 manifest `8b2a87e17b33…`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `8d3209c61723…`；镜像内含 `r2e-mr-058/059`，`060` 在评分包里，`F/remote/build.log`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-058`–`060`），gold 仍为 1。与原题相比三处更严（DEG、REN、D1 由 1 变 0）、一处放宽（ORD 由 0 变 1），不当原 benchmark 报，也不与原 benchmark 分数混算。以后环境复验照旧用 gold（`b00869e7…`）作正对照，期望 1（84/84）；noop 期望 0（74/84）。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 10 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式完整日志） |
   | --- | --- | --- | --- | --- |
   | gold：`density` 接成 `normed` 的别名（两者同传抛 TypeError） | 正对照 | 1 | 1（84/84） | — |
   | ORD：另写 density 分支，先除区间内总数再逐轴除格宽 | R-b 的触发反例（合理解，原版 0，77/78） | 1 | 1（84/84） | — |
   | DEP：沿一维先例弃用 `normed`（DeprecationWarning） | 合理解 | 1 | 1（84/84） | — |
   | DEPFW / DEPUW：DEP 的告警换成 FutureWarning / 不带类别（即 UserWarning） | 合理解；DEPUW 在第 1 轮"四类名单"草案下试跑得 0 | 1 | 1 / 1（84/84） | — |
   | C1：`density=None` 时取 `normed`，静默别名 | 合理替代解 | 1 | 1（84/84） | — |
   | noop | — | 0 | 0（74/84） | 恰为 10 键：6 个原目标键（2D `test_asym`、`test_density`，ND `test_simple`、`test_weights`、`test_density_non_uniform_{2d,1d}`）加 2 个 `test_density_outliers`、2 个 `test_density_false`，全是 `unexpected keyword argument 'density'`（新键在 `HT1':238,290`、`HT2':745,769`）；2 个 `test_normed_still_accepted` 为 PASSED（回归键） |
   | DEG：用含离群格的总数归一 | §4 第 3 步退化候选（原版 1） | 0 | 0（82/84） | 只错 2 个 `test_density_outliers`：`HT1':292` 积分 0.666667 对 1.0；`HT2':770` 0.5714285714285714 对 1 |
   | REN：`normed` 改名为 `density`、删掉 `normed` | §4 第 4 步构造候选（原版 1） | 0 | 0（82/84） | 只错 2 个 `test_normed_still_accepted`：`HT1':304`、`HT2':780` 在 `sup.filter(Warning)` 块里报 `unexpected keyword argument 'normed'`（放行告警不吞异常） |
   | D1：只要显式传了 `density` 就归一化 | §4 第 3 步退化候选（原版 1） | 0 | 0（82/84） | 只错 2 个 `test_density_false`：`HT1':239` 得 1/9、1/18、1/36 等密度，应全为 1；`HT2':746` 得 0.015625×4，应为 `[[3,9],[1,3]]` |

   出处（`F/remote/`）：gold、ORD、DEP、C1、DEPFW、DEPUW 日志第 113 行均为 "84 passed"；noop `noop_logs/…_0000db78` 第 75、94、227、278 行（新键失败）、第 300、354 行（`normed` 两键 PASSED）、第 355–365 行（"10 failed, 74 passed"）；DEG `s1_logs/…_e2728b26` 第 45、59、80、97、182–184 行；REN `s2_logs/…_0fc60980` 第 39–41、49、60–62、69、154–156 行；D1 `s5_logs/…_b7372b56` 第 43、57、75、87、172–174 行。十行共同核对：agent/54321 `git_apply` 成功（noop 为 `noop`），投影只含 `numpy/lib/histograms.py`、`numpy/lib/twodim_base.py`；collected 84，`keys_equal=true`，解析 84、段外 0，missing / unexpected 为空；日志不截断，本机日志 sha256 与 `F/status.json` 一致；补丁摘要等于 `R/cands/` 本地副本（本卡撰写时重算；`F/remote/slots_manifest.json`），gold 等于私有 gold；入口 `8285765f…` 与评分包一致。CX1 第 22–29 行按试跑原件描述的失败原因，全部由正式日志确认。"原版"指修订前材料上的协调者正式评分（`INV/ledger_{DEG,REN,ORD,DEP,revD1}.jsonl` 第 1 行，镜像 `ea786809`）；C1、DEPFW、DEPUW 原版没有正式评分（静态判断为 1）。账本可信 setup + 保护 42–68 s，测试段 2.6–4.8 s（4 路并发，`budget_relaxed_env_reset_1200s=false`）。
2. **devcheck**：v10 镜像（`D/orig/attempt.json`，`8462f1c2…`，与正式评分同一 ID）13 项 checks 全真，8 条命令都符合预期；修订前镜像（`D0/orig/attempt.json`，`ea786809…`）同一组命令同样全过。agent 身份（CC 2.1.205 + 桩）下：预检三项 ok；两条复现命令 rc 1，报题面原文的 `TypeError`；公开 `TestHistogram2d` 6 passed、`TestHistogramdd` 15 passed；`compat_normed_positional` rc 0；没有 pip，pytest 7.4.4，numpy 从 `/testbed/numpy` 导入（`D/orig/captures/`）。私有 gold 对照（root、断网，`D/private_control.json`）7 条全部 rc 0：两条复现命令积分为 1.0，并断言 `density=False` 返回计数、带权密度按总权重归一。非编译题（修改只涉及两份纯 Python 源码）。
3. **S1 处理**：§4 第 1、2 步不命中（核心断言直接、测试输入不是题面示例；`R/reviewer_initial.md` 第 10 行、`R/analysis_before_history.md` 第 132–133 行）；第 3 步 DEG、D1 与第 4 步 REN 在原版得 1，定为 S1；ORD 为 T1。四项合并一轮（`R/revision_plan.md` §1–§3，第 18–117 行）：R-c1 有区间外样本时积分仍为 1、逐格等于计数 / 区间内总数 / 面积（题面明示，加 2D 文档）；R-c2 `normed=True` 仍返回同样的密度，只在这两个调用里 `sup.filter(Warning)` 放行任何告警（base 文档与公开测试）；R-b 逐位相等放宽为 allclose（rtol 1e-7），同键边界比较仍精确；R-c3 `density=False` 返回计数（一维文档 `histograms.py:607-609`、公开测试 `test_histograms.py:81-83`）。独立复核同意 DEG / REN / ORD，补出 D1 与 R-c3，建议放行 FutureWarning（`R/review.md` 第 13–49 行）。Codex 第 1 轮"需小改"：只放行四类弃用告警是没有公开依据的新约束（CX1 第 3、37–41 行）；第 2 轮只改这两个过滤块、其余 82 个测试逐字节不变，通过（CX2 第 1–9 行）。被纠正的误拒有执行证据：DEPUW 在第 1 轮草案下 0（`R/trials/ctrl_draft1_DEPUW.json`）、第 2 轮 1（`R/trials/rev2_DEPUW.json`），正式评分 s8 也是 1。**另两条限定**：①R-b 保留的 allclose 只"挡住所列错误候选"（不除格宽、不除总数、不归一化），不是"所有语义错误"（CX1 第 48 行，`R/revision_plan.md` 第 372 行）；②没有扩大需求、为保 gold 放宽要求或泄漏答案，题面未改，也不强制 `normed`、`density` 同传时采用 gold 的策略（CX1 第 43 行）。
4. **公开包干净**：两次 devcheck `r2e_preflight_ok`（解释器、隐藏测试、git 历史三项 ok）；git sanitize 后 HEAD `a56c4e62`，refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`S/ingest/public_bundles_v0.jsonl` 第 22 行，不含换行的行摘要 `947c10718257…`，与主审登记值相同）从 `S/ingest_history/material_v3_20260929` 到 v10 各次摄入与当前 v11 输出逐字相同；题面与 gold 的 25 行非平凡新增行重叠 0（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）；3 个新测试名与 2 组新输入字面值在 v3 的 7 个 numpy 公开工作树里都没有命中（`R/revision_plan.md` 第 411 行）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核（84 键全部可解释）；按 `r2e-mr-058`–`060` 标明版本报告。R-c3 来自公开先例推知，建议报告时注明"只在两个 `test_density_false` 键失败"的补丁。若参与比较的模型训练时用过 `43e333e2`（其初态含本题答案），本题结果不再是独立证据，要标注或剔除。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：两函数接受 `density=True` 返回密度（6 个原目标键，含非等宽格、3 维、带权）；区间外样本不计入且积分为 1（ND 含带权）；密度等于计数 / 区间内总数 / 面积；`density=False` 返回计数；`normed=True` 数值不变（`R/revision_plan.md` 第 394–401 行）。v10 上 noop 0、gold 1；§4 第 2 步不命中，第 3 步（DEG、D1）、第 4 步（REN）已由修订堵住，T1（ORD）已纠正；T3、X1 已登记。训练价值另看：base 已有正确的 `normed` 归一化，核心改动量小（`R/analysis_before_history.md` 第 123 行）；与 `43e333e2` 同进训练要控制重复采样 |
| 留出评测候选 | conditional | 差：①D3 按仓库划分的实际名单未落实，且有方向：`43e333e2` 初态逐字含本题 gold（它进训练则本题不能留出）；本题初态含 `18b7cd9d`、`2f4a9650`、`5e8301c2`、`d805e9b6` 的修复（扫描所得；本题进训练则它们不能留出），整仓同侧可同时满足（`R/review.md` 第 147–158 行）；②探针结果若用于选模型、调提示或调配方即不再符合；③只能作标明版本的自建评测，且上游 numpy 1.16 已公开此改动，不能排除预训练见过（第 158 行） |

## 剩余事项（已登记，不阻塞探针）

- **T3 / 未覆盖**（`R/revision_plan.md` 第 403–411 行）：2D 带权的 density（ND 带权已由 R-c1 覆盖）；原位置参数顺序（公开读者 R9）；空输入或全部离群时的 density（R12"未约定"）；`normed` 与 `density` 同传（刻意中立：gold 抛 TypeError，DEP 告警后以 `density` 为准，本题 base 上都没有公开依据）；`normed=True` 调用里有无告警、哪一类（R-c2 中立，数值正确但发 RuntimeWarning 之类的候选也会通过）。
- **其余精确断言**：`HT2':551`、`:606`、`:736` 仍是逐位比较；7 种常见运算顺序在这三处都逐位相等（`R/revision_plan.md` 第 378–390 行），ORD 正式 84/84。若真实候选只因末位差异在这里失败，按 T1 重新评估，不直接记为模型错误。
- **弃用写法与公开测试**：DEP 类写法评分为 1（按设计中立），但会让仓库里未捕获告警的公开 `normed=True` 测试在 `pytest.ini` 的 `filterwarnings = error` 下报错（`R/analysis_before_history.md` 第 158–160 行；`R/public_read.md` 第 38–40 行）。探针分析时，这类公开测试失败来自候选自己的选择，不归环境。
- **X1**（`R/analysis_before_history.md` 第 200–205 行；`R/review.md` 第 147–158 行）：见用途表。本题初态一侧的 4 题关系只按扫描登记，未读它们的私有件。
- **解题侧**（`R/old_findings_delta.md` 第 51–53 行）：在 `/testbed` 下用 `python -m pytest`；没有 pip，不需要网络；整文件跑 `numpy/lib/tests/test_histograms.py` 有 21 个与本题无关的 nose-setup ERROR（09-24 实测，09-28/29 未重跑），按"与本题无关的恒失败公开测试"解读。
- **共享控制面（交 A 线）**：根 `pytest.ini` 是评分环境的一部分，候选能否改写它或新增根 `conftest.py` 属共用控制面问题（`R/analysis_before_history.md` 第 198 行）。
- **未核实**（`R/old_findings_delta.md` 第 77–82 行）：裸 `pytest`、`install.sh` 内容、模型实际收到的题面消息。
- **后检（可选）**：`R/commands.json` 的 `repro_histogram2d_density`、`repro_histogramdd_density`、`compat_normed_positional` 覆盖积分为 1、密度公式、`density=False` 计数、带权归一、位置参数与 `normed` 兼容（位置参数隐藏测试不测）；gold 下全部 rc 0（`D/private_control.json`）。可对得 1 的补丁抽查，结果与原始 reward 分列。
- **链路（同批共同项）**（`L/probe_chain_check.md` §0 第 7–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v10 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。正式链直评的基线摘要问题可递延（第 43–51 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对；后续轮次合并覆盖表时本题行应仍为 `8462f1c29203`），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（第 78 行）。
  - 模型实际收到的题面消息未对本题捕获。本机开销：rollout 从起容器到可信初始化完成约 59 s（`D/orig/attempt.json` 的 `stages`；修订前镜像 65 s）；评分见第 1 条，缺省 300 s 时限够用。

## 证据索引

- 审查产物：`R/{public_read.md,commands.json,analysis_before_history.md,old_findings_delta.md,card.md,screening_record.json,reviewer_initial.md,review.md}`（`card.md` 与 `screening_record.json` 的 v1 用途是修订前结论，已由本卡取代）
- 修订：`R/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目见"材料"；修订后文件 `S/revisions/files/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/`
- Codex：`CX1` 第 1–52 行、`CX2` 第 1–13 行
- 修订前实跑：`INV/ledger_{DEG,REN,ORD,DEP,revD1}.jsonl`、`INV/logs_*/`、`INV/pcheck_*.json`；`runs/r2e_lifecycle_20260929/env_verify/ledger_l1_{noop,gold}.jsonl` 第 6 行（noop 72/78、gold 78/78，镜像 `ea786809`）
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/`、`F/remote/*_logs/`、`F/remote/{slots_manifest.json,build.log,setup.log}`
- devcheck：`D/orig/{attempt.json,captures/}`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v10/{summary.json,lane.log}`；`D0/`（修订前镜像）
