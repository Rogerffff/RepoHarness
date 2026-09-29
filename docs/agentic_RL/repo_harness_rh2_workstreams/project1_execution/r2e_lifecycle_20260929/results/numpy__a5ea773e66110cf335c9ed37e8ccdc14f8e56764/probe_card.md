# numpy `a5ea773e` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 8 行全部与期望一致（正对照 gold）；devcheck 13 项全真；两处 S1 已按 R-c 修订，经 Codex 复核与正式评分验收；预检通过。
- **材料**：修订单 v4 的 `r2e-mr-023`（`hidden_test_text_replace`，`test_1.py` `c032efe6…` → `c068c691…`；期望映射不变，32 键全 PASSED）；pins v5 `2324c4c4ab82…`，v5 逐字保留。派生镜像 `32f83a090d56`（`rh2-r2e-derived/numpy:a5ea773e6611-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `23a6fb2bf006…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-023`），不当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/`：gold / noop / s1 / s2 / s3 第 3 行，s4 第 2 行，s5 / s6 第 1 行；`F/status.json` 本题 8 行 `match=true`）。目标键 T = `TestTile.test_tile_one_repetition_on_array_gh4679`：

   | 候选 | 角色 | 期望 | 实得 | 不符键 |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（32/32） | — |
   | A：无条件复制 | 合理替代解 | 1 | 1（32/32） | — |
   | noop | — | 0 | 0（31/32） | T |
   | D：按对象身份判断 | 已知错误 | 0 | 0（31/32） | T |
   | B：只处理整数 1 | 触发反例（原版 1） | 0 | 0（31/32） | T |
   | RC2：`copy=(tup == (1,))` | 触发反例（原版 1） | 0 | 0（31/32） | T |
   | C：全 1 时 `return A.copy()` | 触发反例，兼 §4 第 3 步退化探测（提前返回，原版 1） | 0 | 0（31/32） | T |
   | RC3：全 1 提前返回、不传 `ndmin` | 触发反例（原版 1） | 0 | 0（31/32） | T |

   各行 `git_apply` 成功、测试段完整、键集相等；失败键与试跑逐一相同。各候选分别在哪条新断言失败（B / RC2 在元组循环，C / RC3 在形状断言）按试跑日志行号与补丁源码推断（revision_plan 第 103–110 行），正式日志在远端未取回。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；6 条命令都符合预期。agent 身份下题面原例复现（`a` 变成 `[2 3 4 5 6]`，共享内存 `True`）；12 种输入里 10 种全 1 形式在 base 都与输入共享内存。私有 gold 对照（root）全部 rc=0，12 种输入都不共享、形状符合 docstring。
3. **S1 处理**：R-c 两处（revision_plan §2，第 36–58 行）：补元组形式的全 1 `reps`（`(1,)`、`(1,1)`）的变异隔离（§4 第 2 步，堵 B、RC2）；补 `tile(np.arange(5), (1,1)).shape == (1,5)`（§4 第 4 步，堵 C、RC3）。Codex 复核通过（`L/codex_reviews/review_revision_numpy.md` 第 23–28 行），限定：两处须一起保留，删掉形状断言会重新放行 C / RC3；检查的是实际变异隔离与形状，不要求特定复制实现或对象身份。Codex 第二批复核另有一句仍然有效：结果只证明所测候选和输入。正式评分已确认全部对照与键集完整。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，公开包在材料 v3 → v4 之间逐字未变。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；按 `r2e-mr-023` 标明版本报告。注意修好的代码就是现代 numpy 的 `tile` 原文，模型可能凭记忆作答，解读能力差异时要考虑。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言（revision_plan §6 第 122–127 行）；当前版本 noop 0、gold 1；§4 第 2 步与第 3 步（C）已做；S2、X1 已登记。训练价值另看：答案可凭记忆取得 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题修复的重构版与目标测试出现在同仓 6 题初态（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2 / T3**（revision_plan §6 第 131–135 行）：0-d 输入配 `1`（docstring 应为 `(1,)`）、二维输入配整数 `1`、list `[1]` 与 `np.int64(1)` 形式的 `reps` 未测；已知候选在这些输入上的错误都已在别处被拦下。子类保持、空 `reps` 题面没有约定，不纳入。
- **后检**：只有打印型命令 `runs/r2e_actor_20260925/grader_cands/numpy_a5ea_extra_commands.json`（`tile_semantics`，六种全 1 情形），按 v1 §8 抽查时要先写明判读规则。
- **X1**（旧卡 `card.md` 第 42–46 行）：同仓 `18b7cd9d`、`2f4a9650`、`43e333e2`、`5e8301c2`、`d805e9b6`、`d89bc4bb` 的公开初态都含本题修复的重构版（注释逐字相同）与目标测试；机械比对只命中 1/3 行而漏报。
- **共享控制面**（旧 `screening_record.json` N4）：隐藏测试的断言函数来自候选可改、评分不重置的 `numpy/testing/utils.py`。属 A 线链路问题，探针分析时看账本 `candidate_test_like_paths`。
- **解题侧条件**：`/testbed` 须在 `sys.path` 上，`/testbed` 外的脚本要设 `PYTHONPATH=/testbed`；裸 `pytest` 收集会失败（按 `18b7cd9d` 实测推断）；无 pip；公开 `numpy/tests/test_ctypeslib.py` 有 1 个无关 ERROR。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：求解入口换 `r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v4 正式评分即此口径）；GPU 机须载入同一 image ID，否则本卡评分资格重出；模型实际收到的题面消息未对本题捕获；改 C 源码后的重编与交付链未在 numpy 上实测。本机开销：rollout 可信初始化约 73 s；评分 trusted setup 31–73 s（300 s 硬时限）；测试段约 3–4 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）；Codex 第二批复核 `…/r2e_static_batch2_review_20260925/numpy_pillow/README.md` 第 17 行
- 修订：`L/results/numpy__a5ea773e66110cf335c9ed37e8ccdc14f8e56764/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-023`
- Codex：`L/codex_reviews/review_revision_numpy.md` 第 23–28、30–32 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（行号见第 1 条）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
