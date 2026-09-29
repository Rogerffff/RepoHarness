# numpy `5e8301c2` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：正式评分 5 行全部与期望一致，正对照是经独立核实的替代解 C-A（v1 §5 / D4），**原 gold 在修订版上为 0，已登记**；devcheck 13 项全真；两处 S1 已按 R-c 修订，经 Codex 复核与正式评分验收；预检通过。
- **材料**：修订单 v4 的 `r2e-mr-022`（`hidden_test_text_replace`，`test_1.py` `799c5db8…` → `18a75701…`；期望映射不变，35 键全 PASSED；条目 reason 写明正对照为 C-A、gold 不满分）；pins v5 `2324c4c4ab82…`，v5 逐字保留。派生镜像 `39eee547d0b2`（`rh2-r2e-derived/numpy:5e8301c2b360-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `f215e8d966a4…`）。
- **题目版本**：标明版本的自建修订题（原题 + `r2e-mr-022`）。修订后 gold 式修法得 0，与原 benchmark 语义不同，不能混报。

## 准入五条（README §3）

1. **正式评分**（`F/ledgers/ledger_{gold,noop,s1,s2,s3}.jsonl` 第 2 行；`F/status.json` 本题 5 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键 |
   | --- | --- | --- | --- | --- |
   | C-A：gold + BLAS 守卫（`runs/r2e_actor_20260925/grader_cands/numpy_5e83_CA_gold_plus_blas_guard.patch`） | 正对照（替代解，D4） | 1 | 1（35/35） | — |
   | UP：上游写法（`L/results/numpy__5e83…/cands/`） | 第二个合理实现 | 1 | 1（35/35） | — |
   | gold | 原 gold，按 D4 记录失败 | 0 | 0（20/35） | 15 个 `TestEinSum.test_einsum_sums_*` |
   | noop | — | 0 | 0（20/35） | 同上 15 键 |
   | C-C：只放宽一个方向 | 触发反例，兼 §4 第 3 步退化探测（原版 1） | 0 | 0（20/35） | 同上 15 键 |

   各行 `git_apply` 成功、测试段完整、键集相等；失败键与试跑逐一相同。**局限**：15 个目标键都调用同一个 `check_einsum_sums`，键级结果区分不出失败在哪条断言。C-C 失败在交换顺序断言、gold 失败在求和维断言，是按试跑报错文本推断的（试跑日志只留末 8000 字符，revision_plan 第 142–144 行）；正式评分日志在远端，本机未取回，这一点仍属推断。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真；6 条命令都符合预期，题面原例在 agent 身份下复现 `ValueError: Size of label 't' …`（`pr1_1_cmd` rc=1）。私有 gold 对照（root）全部 rc=0：题面原例修好，但 `'ij,jk->ik'` 配 `(2,3)×(1,4)` 与三操作数仍报 `shape-mismatch for sum`，正是 gold 在修订版上得 0 的原因；gold 新报错文本把两个尺寸写反（`operand 1 (10) … previous terms (3)`）。
3. **S1 处理**：R-c 两处（revision_plan §2，第 35–64 行）：补交换操作数顺序（§4 第 2 步，堵 C-C）；补两个操作数、被求和标签一侧为 1 的内积与矩阵乘（§4 第 4 步，gold 过不了，按 D4 用 C-A 作正对照）。Codex 复核通过（`L/codex_reviews/review_revision_numpy.md` 第 16–21 行），限定：C-A 的独立核实**限本次范围**；15 个失败键重复执行同一新增块，**不代表新增了 15 种 dtype 覆盖**；须登记 C-A 并保留 gold=0；**多操作数与路径规划不在通过范围内**。正式评分确认的：C-A、UP 为 1，gold、noop、C-C 为 0，交付与键集完整。
4. **公开包干净**：devcheck `r2e_preflight_ok`（三项 ok）；修订只动评分包，公开包在材料 v3 → v4 之间逐字未变。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 开发路径与评分依据已核；只能按 `r2e-mr-022` 标明版本报告（gold 式修法在此版本得 0）。批次运行条件属链路 |
| 训练候选 | yes | 核心要求有直接断言：题面原例、交换顺序、求和维，都与 `optimize=False` 及显式数值比较（revision_plan §7 第 155–160 行）；当前版本 noop 0、正对照 C-A 1；§4 第 2 步与第 3 步（C-C）已做；S2、X1 已登记。训练价值另看：比原题难，照上游 gold 写法会得 0 |
| 留出评测候选 | conditional | 差：① D3 仓库划分未定，本题 gold 与隐藏断言出现在同仓 `43e333e2`、`d89bc4bb` 初态（X1），只能整仓同侧；② 若探针结果用于选模型、调提示或调配方即不再符合；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2 / T3 与范围边界**（revision_plan §7 第 162–166 行）：三个及以上操作数、中间收缩、`einsum_path` 本身（Codex NP-2 与 v1 §10 定为本轮范围外）；`optimize='greedy'`、`'optimal'`、显式路径无断言，只特判 `optimize is True` 的实现仍可能得分；跨操作数且两边都不为 1 的不兼容尺寸只有同一操作数内 `'ii'` 的断言，"整段删掉尺寸检查"的 C-D 没跑。
- **G1**：gold 新报错文本尺寸写反，外观问题，无测试（旧卡 `card.md` 第 39 行 I3）。
- **X1**：本题 gold 6/6 行与隐藏断言块在 numpy `43e333e2`、`d89bc4bb` 公开初态；本题初态含 `18b7cd9d`、`2f4a9650`、`d805e9b6` 的修复与 `a5ea773e` 的目标测试。修订有意没照抄上游 #10930 的取值，但语义与后续题公开测试更接近。
- **解题侧条件**：放在 `/testbed` 外的脚本导入不了 numpy，公开提示没写（旧 I6）；无 pip。
- **后检**：只有打印型命令 `runs/r2e_actor_20260925/grader_cands/numpy_5e83_extra{,2}_commands.json`，按 v1 §8 抽查时要先写明判读规则。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：
  - **本题 gold=0**：探针或批次若拿 gold 作健全性对照，须改用 C-A（sha256 `63198523bc33…`）。
  - 求解入口换 `r2e_solve_attempt.py`，`run_matrix.py` 按题选入口、评分带 `--image-overlays`（待改）；评分沿用 `replay_grade run` + 覆盖表（v4 正式评分即此口径）；GPU 机须载入同一 image ID，否则本卡评分资格重出。
  - 隐藏测试依赖候选可改、评分不重置的 `numpy/testing/`（A 线共享控制面）；模型实际收到的题面消息未对本题捕获；改 C 源码后的重编与交付链未在 numpy 上实测。
  - 本机开销：rollout 可信初始化约 92 s；评分 trusted setup 61–64 s（300 s 硬时限）；测试段 5–7 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use`）；Codex 第二批复核 `…/r2e_static_batch2_review_20260925/numpy_pillow/README.md` NP-2
- 修订：`L/results/numpy__5e8301c2b36097dd8be5a12e0bb4369a1df4fabb/{revision_plan.md,revision_draft.json,trials/,cands/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-022`
- Codex：`L/codex_reviews/review_revision_numpy.md` 第 16–21、30–32 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（本题均为第 2 行）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
