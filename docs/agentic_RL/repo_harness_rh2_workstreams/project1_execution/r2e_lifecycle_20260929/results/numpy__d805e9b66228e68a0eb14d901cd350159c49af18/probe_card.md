# numpy `d805e9b6` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`R` = `L/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18`（本题全部审查产物，含独立复核 `reviewer_initial.md`、`review.md`；修订两轮，第 1 轮存档在 `R/trials/round1/`；没有旧审查卡），`F` = `runs/r2e_lifecycle_20260929/formal_v8`（本题在 `F/ledgers/ledger_{gold,noop,s1,s2}.jsonl` 第 3 行、`ledger_{s3,s4,s5,s6}.jsonl` 第 2 行，完整日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v8/numpy__d805e9b66228e68a0eb14d901cd350159c49af18`（v8 镜像），`D0` = `runs/r2e_lifecycle_20260929/devcheck/numpy__d805e9b66228e68a0eb14d901cd350159c49af18`（修订前镜像），`INV` = `runs/r2e_lifecycle_20260929/inv/numpy_d805`（协调者实跑），`CX1` / `CX2` = `L/codex_reviews/review_revision_numpy_d805.md` / `review_revision_numpy_d805_r2.md`，`HT'` = 修订后 `r2e_tests/test_1.py`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 8 行全部与期望一致（缺省 300 s 时限），主正对照是经独立核实的替代解 K-A5b（v1 §5 / D4），**原 gold 在修订版上按设计为 0**；Codex 列为"推定"的失败位置全部由正式完整日志确认，没有未确认项；两次 devcheck 13 项全真；三组 S1 按 R-c 修订，经主审、独立复核、Codex 两轮复核与正式评分验收；预检通过。
- **gold 为 0 的原因与范围**：gold 对一维数组固定截取首尾各 750 个（`_print_width_1d = 1500`），截后仍多于阈值时才由 numpy 摘要。公开 Quickstart 介绍可以用 `set_printoptions` 提高阈值、强制打印整个数组（公开工作树 `doc/source/user/quickstart.rst:262-267`），摘要规则是 `size > threshold`（`numpy/core/arrayprint.py:252`）。于是 `threshold ≥ 1500` 且 n > 1500 时，gold 先把数组截成 1500 个，再不加省略号地全量打印，静默丢值。修订第 3 处（`threshold=2000`、`np.ma.arange(2000)`、掩 `a[1:50]`）测的就是这一点：gold 在 `HT':492` 失败，token 数 1500 对 2000。它通过示例断言与第 1、2 处（默认打印选项下的全部要求），只在第 3 处失败。gold 在原材料（`runs/r2e_lifecycle_20260929/env_verify/ledger_l0_gold.jsonl` 第 6 行）与第 1 轮草案上为 1，这些旧结果不回写（`CX2` 第 36 行）。
- **以后批量环境复验**：本题正对照必须用 K-A5b 补丁（`R/cands/numpy_d805_KA5b.patch`，sha256 `0cde371bd6e2729bed10e4fee8f5df3034acb93379ab4af8396de3690aa51b43`，与 `INV/numpy_d805_KA5b.patch` 逐字节相同），期望 1（229/229）。**不能用 gold**：自 v8 材料起 gold 期望 0（228/229，只错 `TestMaskedArray.test_str_repr`，失败在 `HT':492`），拿 gold 当正对照会被误报成环境回归。`F/plan.json` 本题各行已记 `positive_control: cands/numpy_d805_KA5b.patch`。
- **材料**：修订单 v8 的 `r2e-mr-056`（`hidden_test_text_replace`，`test_1.py` `72f865c4…` → `14d78a1c…`，4401 → 4434 行：在唯一目标键 `TestMaskedArray.test_str_repr` 的示例断言之后加三处断言，`HT':463-494`；期望不改，229 键；条目 reason 写明正对照为 K-A5b、gold 修订后不满分，`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v8.json` 第 1727 行起）；本题此前没有材料修订。pins v9 `9b766c2aec84…`（其后 v10 只改 orange3 `4014`）；评分日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=71326af5…` 等于当前评分包（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl` 第 21 行）。派生镜像 `c596cd48d037`（`rh2-r2e-derived/numpy:d805e9b66228-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `e0a8970ef09b…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-056`），不当原 benchmark 报，也不与原 benchmark 分数混算（`CX2` 第 37 行）。它比上游修复更严：gold 与已核对的后续源码快照（`numpy__d89bc4bb…` 公开工作树）里的固定宽度写法，在此版本都得 0（`R/revision_plan.md` 第 304 行）。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 本题 8 行 `match=true`）。三处新断言都在唯一目标键 `test_str_repr` 里，得 0 的行都是 228/229、只错这一个键；断言按顺序执行，日志给出的是第一个失败的断言：

   | 候选 | 角色 | 期望 | 实得 | 第一个失败的断言（正式日志）；Codex 推定（`CX1` 第 18–24 行） |
   | --- | --- | --- | --- | --- |
   | K-A5b：一维时若超过阈值，截取宽度取 max(threshold+2, 原宽度)，让 numpy 自己摘要，否则不截 | **主正对照**（D4 替代解；审查者构造、协调者改一行，不是独立求解） | 1 | 1（229/229） | — |
   | gold（固定宽度 1500） | 原 gold，按 D4 记录失败 | 0 | 0 | `:492`（第 3 处 token 断言），token 数 1500 对 2000；第 2 轮新增，Codex 未列推定 |
   | noop | — | 0 | 0 | `:458` 示例 repr：base 打印 100 个值、没有省略号。推定 458，**已确认** |
   | K-DE：截取量写死 750 | §4 第 3 步退化候选（原版 1） | 0 | 0 | `:478`（第 2 处 token 断言），token 数 1000 对 500，每个值显示两次。推定 477–478，**已确认**（跨行调用，回溯报 478） |
   | K-DC：只在 size > threshold 时放宽 | 第 4 步（原版 1） | 0 | 0 | `:478`，token 数 100 对 500，丢 400 个值。推定 477–478，**已确认** |
   | K-DF：截角门槛改成 size > 10000 | 第 4 步（原版 1） | 0 | 0 | `:468`（第 1 处），n=100000 只打印 100 个值、没有省略号。推定 468，**已确认** |
   | DG-e：只修 `__repr__` | 已知相关错误候选（原版试跑 1） | 0 | 0 | `:468`，输出同 K-DF。推定 468，**已确认** |
   | DG-g：全局阈值改成 99（改 `numpy/core/arrayprint.py`） | 已知错误候选，Codex 定为必跑（原版试跑 1） | 0 | 0 | `:476`，n=500 的输出里出现 `...`。推定 476，**已确认** |

   出处（`F/remote/`）：K-A5b `s1_logs/…_545946fc.eval.log` 第 258 行；gold `gold_logs/…_50824e86` 第 79、111–114 行；noop `noop_logs/…_4f5cc733` 第 47、76–79 行；K-DE `s2_logs/…_2515e23f` 第 65、97–100 行；K-DC `s3_logs/…_a350c0d0` 同；K-DF `s4_logs/…_202cdc79` 第 55、83–86 行；DG-e `s5_logs/…_f2aebcf1` 同；DG-g `s6_logs/…_b18cdee9` 第 63、85 行。三处各自必要在正式日志上可见：第 1 处拦 K-DF、DG-e，第 2 处拦 K-DE、K-DC、DG-g，第 3 处拦 gold；各候选在其它两处的行为来自私有核对（`INV/pcheck_*.json`），不是正式评分。"原版"指 `INV/ledger_{KDE,KDC,KDF,KA5b}.jsonl` 第 1 行（均 1.0、229/229，镜像 `c080fc6b`）；DG-e、DG-g 原版只有试跑（`R/trials/round1/cur_DG{e,g}.json`）。各行由 agent/54321 `git_apply` 成功，投影只含 `numpy/ma/core.py`（DG-g 只含 `numpy/core/arrayprint.py`），229 键全解析、`keys_equal=true`，日志不截断；补丁摘要等于 `R/cands/`（`F/remote/slots_manifest.json`）。账本可信 setup + 保护 38–45 s，测试段 4–5 s（4 路并发）。
2. **devcheck**：v8 镜像（`D/orig/attempt.json`，`c596cd48…`，与正式评分同一 ID）13 项 checks 全真，8 条命令都符合预期；修订前镜像（`D0/orig/attempt.json`，`c080fc6b…`）同一组命令同样全过。agent 身份下：题面原例 `repro_issue_repr` rc 1（base 打印 100 个值、没有省略号，与题面 Actual 块不符，即 P4）；`diag_sizes` 显示 n=2000、n=500 都只有 100 个 token；公开 `numpy/ma/tests/test_core.py` 229 passed，打印相关 6 passed。非编译题（修改只涉及 Python 源码）。私有 gold 对照（root、断网）全部 rc 0；其中 `diag_sizes` 的二维数组 (150, 5) 750 个元素只显示 500 个、(101, 10) 1010 个只显示 1000 个，都没有省略号，属于已登记的二维窄轴问题（题外，见剩余事项），与修订无关。
3. **S1 处理**：R-c 三处，都在 `test_str_repr` 里，期望不变（`R/revision_plan.md` §1–§3，第 30–159 行）：①n=100000 的非示例摘要 `'[0 1 2 ..., 99997 -- --]'`（T2c；堵 K-DF、DG-e）；②默认阈值以下 n=500 全量显示，不缺不重（T2b 的 K-DE；第 4 步的 K-DC；也堵 DG-g）；③`threshold=2000` 时 n=2000 全量显示（第 4 步：gold 对有文档的常用行为修不完整，按 D4 改用 K-A5b 作主正对照）。独立复核同意①②，并认定第 2 处的严格读法（n ≤ 阈值时全量显示）不构成 P5（`R/review.md` 第 187–204 行）；复核把自定义阈值归 T3（第 206–214 行），被 Codex 第 1 轮推翻（`CX1` 第 34–40 行），第 2 轮因此补了③。Codex 第 2 轮通过（`CX2` 第 1–3 行），**限定**：①K-A5b 是"经独立核实、满足本轮核心行为的替代正对照，不是所有打印配置下都正确的完整实现，也不是独立求解结果"（第 28 行）；主审原稿的 K-A5 因模块内 `max` 指向 `numpy.ma.max` 崩溃，是候选错误，不是误拒（`CX1` 第 28 行）；②gold 旧版 1、新版 0，不回写旧结果；只能报告为标明材料版本的自建修订题（`CX2` 第 36–37 行）；③更严不自动代表更有训练价值，也不解除 X1、P4 与池级条件（第 38 行）；④`n > threshold ≥ 1500` 登记、本轮不加断言，但实际候选若得 1 却在这里静默丢值，要重新按 S1 判断，不能以"已登记"豁免（第 13–17 行）；⑤DG-g 只证明断言有区分力，不是严格读法的规格依据（`CX1` 第 10 行）；⑥"后续版本仍有此问题"只限已核对的后续源码快照（`CX2` 第 39 行）。`CX2` 第 45 行要求的 8 项正式矩阵（DG-g 必跑）与完整回溯核对，今晚已完成（第 1 条）。
4. **公开包干净**：两次 devcheck 都 `r2e_preflight_ok`（解释器、隐藏测试、git 历史三项 ok）；git sanitize 后 refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 21 行）在 09-29 各次摄入（v4 前、v8 前、v9 前的备份与当前）逐字相同；题面与 gold 无逐行重叠（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）；新断言的输入（`99997 -- --`、`np.ma.arange(100000)`、`range(50, 500)`、`threshold=2000`、`range(50, 2000)`）在 v3 的 7 个 numpy 公开工作树的 `numpy/ma/tests/test_core.py` 里都没有命中（revision_plan 第 303 行）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；只能按 `r2e-mr-056` 标明版本报告（gold 式修法在此版本得 0）。分析规则：P4 的 R-f 落地前，"n ≤ 1000 也被摘要"式失败单列为"P4 相关"，原始 reward 不变（`R/review.md` 第 216–224 行）；比较训练过 numpy 题的模型时，本题标为"已暴露"（第 239 行）。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：示例 repr、非示例摘要、默认阈值下全量显示、提高阈值后全量显示（revision_plan 第 276–281 行）；v8 上 noop 0、主正对照 K-A5b 1；§4 第 2 步（非示例实例）、第 3 步（K-DE）、第 4 步（K-DC、K-DF、DG-e、DG-g、gold）已做；S2 / T3、X1、P4 已登记。复核建议在池级条件核清前写 conditional，并说明池级条件在逐题记录之外统一处理时可写 yes（`R/review.md` 第 246–247 行）；本批按后者，池级条件放在"链路"一栏。训练价值另看：比上游严，上游修复与已核对的后续源码快照在本版本都得 0，而同仓 5 题的初态里就是这种写法 |
| 留出评测候选 | conditional | 差：①D3 仓库划分未定，且有方向：同仓 `18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb` 的初态含本题 gold 与原示例断言（本题留出则它们不能进训练），本题初态含 `a5ea773e` 的修复（本题进训练则它不能留出），整仓划分可同时满足（`R/review.md` 第 226–239 行）；②若探针结果用于选模型、调提示或调配方即不再符合；③只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **同族未断言实例 `n > threshold ≥ 1500`**（revision_plan 第 284–288 行；`CX2` 第 11–17 行）：例如 threshold=2000、n=3000 应摘要。"n ≤ threshold 时不截、否则固定截到 1500"的混合实现能过三处断言，却在这里静默丢值（静态推导，没有候选实例）。要补就在第 3 处的 `try` 块里加 n=3000、期望 `'[0 -- -- ..., 2997 2998 2999]'`，再验收一轮。实际候选得 1 却在此丢值时，按 S1 重判。
- **大 edgeitems（S2 / T3）**（revision_plan 第 289–294 行；`CX2` 第 26 行）：K-A5b 在默认阈值下，n > 1002 且 edgeitems ≥ 501 时漏省略号；gold 在 edgeitems ≥ 750 时出现同类问题。罕见组合，登记不测。
- **二维窄轴**（题外，标题限定一维；`CX1` 第 45 行）：gold 私有对照里 (150, 5)、(101, 10) 都静默丢值（`D/private_control.json` 的 `diag_sizes`）。
- **T3**：子类打印（隐藏测试不含 `test_subclassing.py`）；10^7 规模的性能。
- **P4**（`R/review.md` 第 216–224 行）：题面 Actual 块与 base 实际输出不符，还把"显示约 1000 个值"说成缺陷本身，可能诱导"只要截过就一律摘要"式补丁，这类补丁在第 2 处得 0。这不构成 P2，R-f 的优先级已上调；落地前按上面的"P4 相关"规则单列。
- **X1**（`R/review.md` 第 226–239 行）：见用途表。影响是答案暴露与留出方向，不是重复采样；与同仓 5 题同批训练时，本题的通过率应视为"可能开卷"。
- **E3 共享控制面**：隐藏测试依赖候选可改、评分时不重置的 `numpy/ma/testutils.py` 与 `numpy/testing/**`（交 A 线）；事后审计时标记改动它们或 `numpy/core/arrayprint.py` 的补丁（`R/review.md` 第 246 行）。
- **候选错误归类**：`numpy/ma/core.py` 内的 `max`、`min`、`sum`、`abs`、`round` 等指向 `numpy.ma` 的同名函数，K-A5 就因此崩溃得 0；探针里这类失败归候选错误，不归环境（`R/review.md` 第 257 行）。
- **后检（可选）**：`INV/private_check_6_3.py`（n=500 全量显示且不缺不重；n=100000 为 `'[0 1 2 ..., 99997 -- --]'`），可对得 1 的补丁抽查，结果与原始 reward 分列。
- **链路（同批共同项）**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：
  - **本题 gold = 0**：探针或批次若拿 gold 作健全性对照，须改用 K-A5b（见"结论"）。
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v8 正式评分即此口径）。
  - 接真实模型前先收口 Codex 的两项 P1：去掉静止屏障里以 root 执行的 git（第 9–31 行）；往返不一致、评分 fatal、清理未知时停止派发（第 33–41 行）。
  - GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（第 78 行）。
  - 本机开销：rollout 从起容器到可信初始化完成约 41 s（`D/orig/attempt.json` 的 `stages`）；评分见第 1 条。模型实际收到的题面消息未对本题捕获。

## 证据索引

- 审查产物：`R/{public_read.md,commands.json,analysis_before_history.md,old_findings_delta.md,card.md,screening_record.json,reviewer_initial.md,review.md}`（`card.md` 与 `screening_record.json` 的 v1 用途是修订前结论，已由本卡取代）
- 修订：`R/{revision_plan.md,revision_draft.json,trials/round1/,trials/round2/,cands/}`；正式条目见"材料"
- Codex：`CX1` 第 1–54 行、`CX2` 第 1–45 行
- 修订前实跑：`INV/ledger_{KDE,KDC,KDF,KA5,KA5b}.jsonl`、`INV/logs_*/`、`INV/pcheck_*.json`；`runs/r2e_lifecycle_20260929/env_verify/ledger_l0_{noop,gold}.jsonl` 第 6 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/`、`F/remote/*_logs/`、`F/remote/slots_manifest.json`
- devcheck：`D/orig/{attempt.json,captures/}`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v8/{summary.json,lane.log}`；`D0/`（修订前镜像）
