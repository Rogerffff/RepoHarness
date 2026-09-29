# pandas `4ec87eb9` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`R` = `L/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199`（本题审查产物：公开读、主审两步、修订方案两版；**没有独立复核的 `reviewer_initial.md` / `review.md`**；没有旧审查卡），`F` = `runs/r2e_lifecycle_20260929/formal_v8`（本题在 `F/ledgers/ledger_{gold,noop,s1,s2}.jsonl` 各第 2 行，完整日志在 `F/remote/<槽位>_logs/`），`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v8/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199`（v8 镜像），`D0` = `runs/r2e_lifecycle_20260929/devcheck_rev/unrev/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199`（修订前镜像），`INV` = `runs/r2e_lifecycle_20260929/inv/pandas_4ec8`（协调者实跑），`CX` = `L/codex_reviews/review_revision_pandas_4ec8.md`，`HT'` = 修订后 `r2e_tests/test_1.py`。键名省略前缀 `test_groupby_quantile_`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：on_hold（缺独立复核）**。修订本身已完整验收：正式评分 4 行与期望一致，Codex 要求的三项确认都已由完整日志核实（第 1 条）；两次 devcheck 13 项全真；预检通过。缺的是 v1 §7.3"每题都做独立复核"（`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md` 第 222–226 行；本批 `L/README.md` 第 36 行也把它列为未审题的必经步骤）：`L/assignments.json` 里本题只有公开读者、主审两步、修订执行两轮，没有 reviewer 会话（同轮的 `f5eb`、`d805` 都有）；主审卡把它列为未满足（`R/card.md` 第 141 行）；Codex 只复核了修订草案（`L/codex_reviews/prompt_revision_pandas_4ec8.md` 第 3–12 行），自己也写明"通过的是修订草案，不是正式评分验收或探针准入"（`CX` 第 3 行）。所以第 3 条的"按 v1 §4 判定过"目前只有主审一方的判断。
- **为什么不是纯流程缺口**：结果 dtype 这一项正需要第二方核对。公开读者判为"多种合理解释、公开材料无法消除"（`R/public_read.md` 第 14、36–41 行）；主审判为 P3（公开依据站在 float64 一边，不算 T1，不交用户，`R/card.md` 第 119–127 行）；原目标断言按缺省 `check_dtype` 要求 float64，返回 `Float64` 的修法会得 0。Codex 在 `f5eb` 上的口径是"依据弱不等于没有公开依据"，把同类的输出形式二选一判为 P5（`L/codex_reviews/review_revision_coveragepy_f5eb.md` 第 39–44 行）；本题的 dtype 判断没有人按这一口径核过。
- **恢复条件**：派一个不继承协调上下文的新会话做独立复核，按 v1 §4"分歧处理"只针对主审判断给反证，至少覆盖：①dtype 归 P3，还是 T1 / P5；②§4 第 4 步（现有构造候选只有 C0、C1）与 T3 登记是否足够。复核同意主审：不需重跑评分与 devcheck，直接改标 probe_ready，用途改为 yes / yes / yes / conditional（留出条件同下表）。复核判 T1 或 P5：按 v1 §3 / §5 处理（R-b，或交用户暂挂），新版本重做验收与 Codex 复核。
- **材料**：修订单 v8 的 `r2e-mr-055`（`hidden_test_text_replace`，`test_1.py` `5a4d2be4…` → `719e63ae…`，328 → 343 行：两段新断言并入已有目标测试 `test_groupby_quantile_NA_float(any_float_dtype)` 末尾，`HT':267-280`；期望不改，237 键）；与用户 09-24 批准（T0-6）的 `r2e-mr-006`（私有 `conftest.py`，`632b5ee3…`）、`r2e-mr-007`（期望 `19f481a2…` → `bdf1ddf5…`，删 2 个 ERROR 键、加 13 键）目标不同，二者原样保留（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v8.json` 第 154、172、1703 行起）。pins v9 `9b766c2aec84…`（其后 v10 只改 orange3 `4014`）；评分日志头 `RH2_SETUP_HIDDEN_TESTS_TREE=ec3a3499…` 等于当前评分包（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl` 第 33 行，`material_revisions` 为 006 / 007 / 055）。派生镜像 `c057430b5e89`（`rh2-r2e-derived/pandas:4ec87eb94bc8-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `46b176fbee40…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-006/007/055`），不当原 benchmark 报；gold 在修订版上仍为 1。

## 准入五条（README §3）

1. **正式评分**（`F/status.json` 本题 4 行 `match=true`，缺省 300 s 时限）：

   | 候选 | 角色 | 期望 | 实得 | 不符键与失败断言（正式日志） |
   | --- | --- | --- | --- | --- |
   | gold（`quantile` 的 `pre_processor` 新增浮点扩展数组分支，`to_numpy(dtype=float, na_value=np.nan)`） | 正对照 | 1 | 1（237/237） | —；`NA_float` 5 个参数键全 PASSED |
   | C1：统一的掩码数组分支，保留整数 `inference` | 合理替代解 | 1 | 1（237/237） | — |
   | noop | — | 0 | 0（233/237） | `NA_float[Float32/Float64]`、`allNA_column[Float32/Float64]`：`TypeError: float() argument must be a string or a number, not 'NAType'`（`test_1.py:254`、`:299`），与修订前逐键相同；3 个 numpy 参数键照旧 PASSED |
   | C0：同一位置写 `out = vals._data`，底层值直接交内核、不按掩码置 NaN | §4 第 3 步退化候选（原版 1，237/237） | 0 | 0（235/237） | 只有 `NA_float[Float32]`、`[Float64]`：`HT':272`，`[left]: [1.0]`、`[right]: [2.0]`（`F/remote/s1_logs/…_908321f7.eval.log` 第 60–72、102–114 行） |

   Codex 要求的三项（`CX` 第 44 行）：①gold / noop / C0 / C1 = 1 / 0 / 0 / 1，**已确认**；②4 行都解析到 237 键、`keys_equal=true`，无 missing / unexpected，另有 2 个既有 skip（`test_1.py:39`）不变，**已确认**；③C0 的完整失败位置与数值，**已确认**：两个键都停在 `:272`（第一段：`Int64` 转浮点扩展类型，掩码位底层是 1.0），得 1.0、应为 2.0；它之前的原有断言（`:257`、`:265`）都已通过，所以失败只来自新断言。**正式日志确认不了的一点**：第二段（`reindex`，`:278-280`）能否单独挡住 C0。C0 在 `:272` 已失败，第二段没有执行；这一点只有试跑诊断 `R/trials/diag_seg2_C0.json`（试跑工具，不是正式评分）。各行由 agent/54321 `git_apply` 成功，投影只含 `pandas/core/groupby/groupby.py`，测试段完整、日志不截断；补丁摘要等于 `R/cands/`（`F/remote/slots_manifest.json`）。"原版"指 `INV/ledger_{C0,C1}.jsonl` 第 1 行（镜像 `85f550e6`）。账本可信 setup + 保护 84–88 s（300 s 时限内，4 路并发），测试段 11–12 s。
2. **devcheck**：v8 镜像（`D/orig/attempt.json`，`c057430b…`，与正式评分同一 ID）13 项 checks 全真，8 条命令都符合预期；修订前镜像（`D0/orig/attempt.json`，`85f550e6…`）同一组命令同样全过。agent 身份下：题面原例与定位命令 rc 1（`TypeError`，预期内）；`variants_float_masked` rc 1（6 项 ERR，含 `masked_slot_not_nan`；`mixed_frame_keeps_float64` 为 BAD；无 NA 基线 OK）；公开 `test_quantile.py` 222 passed / 2 skipped；相关路径 40 passed / 3 xfailed。私有 gold 对照（root、断网）全部 rc 0，`variants_float_masked` 8 项全 OK（`masked_slot_not_nan` 得 [2.0]，结果 dtype 都是 float64）。无异常；非编译题。
3. **S1 处理**：R-c 一项（`R/revision_plan.md` §1–§3，第 26–102 行）：目标键的浮点扩展输入都由列表构造，掩码位底层恰好是 NaN，所以 C0 得 1；在已有目标测试末尾并入两段：`Int64` 转浮点类型（掩码位底层 1.0）、`reindex` 引入的 NA（底层 0.0，两组）。选择并入而不新增键，是为避开与已批准的 `r2e-mr-007` 同目标冲突（第 12–24 行）；dtype 随参数取，numpy 参数下 base 照旧通过；新断言 `check_dtype=False`，不新增 dtype 约束。Codex 通过（`CX` 第 1–46 行），**限定**：①期望由"排除缺失后按线性插值取中位数"推出，不是抄 gold（第 15 行）；②只查数值，不要求内部存 1.0 / 0.0，也不绑定 gold 写法（第 36 行）；③并入旧键使失败定位变粗，靠回溯行号区分（第 40 行）；④与第 1 版结构只能说"当前四个对照得分相同"，不是普遍等价（第 46 行，revision_plan 第 199 行已按此更正）；⑤T3、dtype、X1 继续登记（第 44 行）。**独立复核：未做**（见"结论"）。
4. **公开包干净**：两次 devcheck 都 `r2e_preflight_ok`（三项 ok）；git sanitize 后 refs / remotes / reflog / 不可达对象都为 0；修订只动评分包，本题公开包行（`docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/public_bundles_v0.jsonl` 第 33 行）在 09-29 各次摄入（v4 前、v8 前、v9 前的备份与当前）逐字相同；题面与 gold 无逐行重叠（`runs/r2e_static_prep_20260924/statement_gold_overlap_scan.json`）；新断言的构造写法 `dtype="Int64").astype(` 在 v3 的 7 个 pandas 公开工作树 `pandas/tests` 下没有命中（revision_plan 第 191 行）。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | conditional | 差独立复核（重点是 dtype 的定性）。开发路径、评分依据、本批运行条件都已核（第 1、2 条）。复核同意后改 yes，只能按 `r2e-mr-006/007/055` 标明版本报告；若探针出现"其余都对、只有结果 dtype 是 `Float64`"的补丁，单列为规格争议样本，原始 reward 保留（`R/card.md` 第 127 行）。批次运行条件属链路 |
| 训练候选 | conditional | 差：同上。正面覆盖证据已齐：部分 NA 被忽略（`NA_float[Float32/Float64]` 原有断言，值用 0.2 而不是示例的 2.5，标量与列表 q）、忽略 NA 与掩码位底层存储无关（新并入两段）、全 NA 组（`allNA_column`）、结果 dtype float64（原有断言，P3）都有决定性断言（revision_plan 第 178–184 行）；v8 上 noop 0、gold 1；§4 第 2 步（不只用示例字面值）、第 3 步（C0）已做，第 4 步只有构造候选 C0、C1；T3、X1 已登记 |
| 留出评测候选 | conditional | 差：①独立复核与训练候选的质量条件；②D3 仓库划分未定，`7dd34ea7` 公开初态逐字含本题 gold 与原有 3 个新测试（X1），pandas 各题须整仓同侧；③若探针结果用于选模型、调提示或调配方即不再符合；④只能作标明版本的自建评测 |

## 剩余事项

- **独立复核**（阻塞，见"结论"）。
- **P3 结果 dtype**（`R/screening_record.json` issue `P3_result_dtype`）：主审的依据是同方法对 `Int64` / `boolean` 返回 float64 的公开测试、base 上无 NA 的 `Float64` 返回 float64（devcheck 实测）、v1.1.0 的同类约定，且返回 `Float64` 会连带改变无 NA 时的既有行为；反向依据是 `Series.quantile` 与 groupby 的 mean / median 保留掩码 dtype。待复核定性。
- **T3**（revision_plan 第 186–189 行）：DataFrame 入口的浮点扩展列、混合列不丢浮点列、无 NA 时 dtype 的旧行为、稀疏浮点路径都没有断言。"只在部分 NA 来源上把掩码位改成 NaN、quantile 里仍直接用 `_data`"的候选能过新断言，但对 `Int64` 除法和直接构造的 `FloatingArray` 仍算错；目前没有这类候选实例，按 v1 §8 抽查。
- **失败定位变粗**：事后审计要区分原有断言（`HT':257`、`:265`）与新断言（`:272`、`:278-280`），读正式日志的行号（revision_plan 第 23 行）。
- **P4**：题面写 "group `1`"，实际标签是 1.0；题面没提先出现的 FutureWarning。
- **X1**：见用途表；本题 base 也含同仓其它题的修复；训练时控制同源题的采样。
- **共享控制面**：隐藏测试依赖候选可改、评分时不重置的 `pandas._testing`；候选可以在 `/testbed` 根目录新建 `conftest.py`（通用问题，交 A 线）。
- **已批准修订**：`r2e-mr-006` / `007`（T0-6）原样保留；本轮没有改期望文件，也没有改动已批准条目。
- **后检（可选）**：`INV/private_check_A2.py`，或公开命令 `variants_float_masked` 里的 `masked_slot_not_nan`，可对得 1 的补丁抽查，结果与原始 reward 分列。
- **链路（恢复后才适用，同批共同项）**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行；Codex `L/codex_reviews/review_probe_chain_20260929.md` 第 1–3 行"改后可以"）：求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v8 正式评分即此口径）；接真实模型前先收口 Codex 的两项 P1（去掉静止屏障里以 root 执行的 git，第 9–31 行；往返不一致、评分 fatal、清理未知时停止派发，第 33–41 行）；GPU 机须载入同一 image ID（按 tag→ID 核对），否则本卡评分资格重出；账本 `env_qualification=absent`，能力统计前补接资格账本或单列（第 78 行）。本机开销：rollout 从起容器到可信初始化完成约 94 s（`D/orig/attempt.json` 的 `stages`）；评分见第 1 条。模型实际收到的题面消息未对本题捕获。

## 证据索引

- 审查产物：`R/{public_read.md,commands.json,analysis_before_history.md,old_findings_delta.md,card.md,screening_record.json}`（`card.md` 与 `screening_record.json` 的 v1 用途是修订前结论，已由本卡取代）；角色记录 `L/assignments.json`（本题只有 public_reader、investigator step1 / step2、revision_executor 两轮）
- 修订：`R/{revision_plan.md,revision_draft.json,trials/,cands/}`（第 1 版存档在 `R/trials/round1/`）；正式条目见"材料"
- Codex：`CX` 第 1–46 行；提示 `L/codex_reviews/prompt_revision_pandas_4ec8.md`
- 修订前实跑：`INV/ledger_{C0,C1}.jsonl`、`INV/logs_*/`、`INV/pcheck_*.json`；`runs/r2e_lifecycle_20260929/env_verify/ledger_l2_{noop,gold}.jsonl` 第 8 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/`、`F/remote/*_logs/`、`F/remote/slots_manifest.json`
- devcheck：`D/orig/{attempt.json,captures/}`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v8/{summary.json,lane.log}`；`D0/`（修订前镜像）
