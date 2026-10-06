# numpy `18b7cd9d` 探针准入卡（2026-09-29）

路径相对仓库根。`L` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929`，`F` = `runs/r2e_lifecycle_20260929/formal_v4`，`D` = `runs/r2e_lifecycle_20260929/devcheck_rev/v4/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9`。准入标准见 `L/README.md` 第 17–25 行。

## 结论

- **状态：probe_ready**。五条都满足：v4 材料、新派生镜像上正式评分 6 行全部与期望一致；devcheck 13 项检查全真；两处 S1 已按 R-c 修订，经 Codex 复核并由正式评分验收；R2E 预检通过。
- **材料**：修订单 v4 的 `r2e-mr-021`（`hidden_test_text_replace`，`test_1.py` `4a86bd4b…` → `aab99f01…`；期望映射不变，11 键全 PASSED）；pins v5 `2324c4c4ab82…`，修订单 v5 逐字保留该条。派生镜像 `e4c267acadde`（`rh2-r2e-derived/numpy:18b7cd9df7a4-r2e_derive_v1m2s`），配方 `r2e_derive_v1+material_v2+sysconfig_v1`（配方摘要 `e2bcdcfc062e…`）。
- **题目版本**：标明版本的自建修订题（R2E-Gym-Subset 原题 + `r2e-mr-021`），分数不能当原 benchmark 报。

## 准入五条（README §3）

1. **正式评分**（09-28 19:29 UTC 起，`F/ledgers/ledger_{gold,noop,s1,s2,s3,s4}.jsonl` 第 1 行；`F/status.json` 本题 6 行 `match=true`）：

   | 候选 | 角色 | 期望 | 实得 | 不符键 |
   | --- | --- | --- | --- | --- |
   | gold | 正对照 | 1 | 1（11/11） | — |
   | A：非 poly1d 返回 `False` | 合理替代解 | 1 | 1（11/11） | — |
   | noop | — | 0 | 0（10/11） | `TestDocs.test_poly_eq` |
   | D：`__eq__` 返回 NotImplemented、`__ne__` 不改 | 已知错误 | 0 | 0（10/11） | 同上 |
   | N：只特判 `None` | 触发反例（原版 1） | 0 | 0（10/11） | 同上 |
   | I：删掉 `__eq__` / `__ne__` | 触发反例，兼 §4 第 3 步退化探测（原版 1） | 0 | 0（10/11） | 同上 |

   各行 `git_apply` 成功、测试段完整、日志不截断、键集相等（无 missing / unexpected）；失败键与试跑（`L/results/numpy__18b7…/trials/rev_*.json`）逐一相同。
2. **devcheck**：`D/orig/attempt.json` 13 项 checks 全真（agent uid 54321、`/testbed/.venv` 激活、激活文件 agent 不可写、容器镜像 = 覆盖表 ID、CC 2.1.205 + 桩 7 条消息、清理零残留）。6 条命令都符合预期；题面原例在 agent 身份下复现 `AttributeError`（`mcve_statement` rc=1，本就预期非零）。私有 gold 对照（`D/private_control.json`，root 一次性容器）5 条都 rc=0，`p == None` 输出 `False`。无不符项。
3. **S1 处理**：R-c 两处（`L/results/numpy__18b7…/revision_plan.md` §2，第 30–50 行）：补 `None` 以外的非 poly1d 比较（`object()`、`3`；§4 第 2 步 T2c，堵 N）；补"系数相同的另一个 poly1d 相等"（§4 第 4 步，堵 I）。Codex 复核通过（`L/codex_reviews/review_revision_numpy.md` 第 7–14 行），限定三条：两处须一起保留，删掉第二处 I 会回到 1；断言不强迫返回 NotImplemented；**未证明所有 list／ndarray 比较情形都已覆盖**。Codex 要求的"正式评分确认交付、测试完整与严格键集"（同文件第 30–32 行）已由上表确认。失败落在哪一行仍以试跑日志为据；正式评分日志在远端 `/work/r2e/formal_v4/`，本机未取回。
4. **公开包干净**：devcheck `r2e_preflight_ok`（`INTERPRETER`、`HIDDEN_TESTS`、`GIT_HISTORY` 都为 ok，agent 身份经 CC Bash 跑）；git sanitize 后 0 ref、0 remote、0 reflog。修订只动评分包，本题公开包在材料 v3 → v4 之间逐字未变。
5. 见下两节。

## v1 四项用途

| 用途 | 结论 | 条件与证据 |
| --- | --- | --- |
| 问题定位 | yes | 无门槛 |
| 能力比较 | yes | 公开开发路径（devcheck v4）与评分依据（v4 正式评分 + Codex）已核；只能按 `r2e-mr-021` 标明版本报告。探针批次的运行条件属链路，见下节 |
| 训练候选 | yes | 正面覆盖证据齐：核心要求有直接断言（revision_plan §6 第 109–114 行）；当前版本 noop 0、gold 1；§4 第 2 步（非示例实例）与第 3 步（I）已做；无未处理 S1，S2 与 X1 已登记。训练价值另看：易题，题面已给修法方向 |
| 留出评测候选 | conditional | 差三件：① D3 按仓库划分尚未定，本题修复出现在同仓 4 题初态（X1），只能整仓同侧；② 本卡准入基座探针，探针结果若用于选模型、调提示或调配方，本题即不再符合留出条件；③ 只能作标明版本的自建评测 |

## 剩余事项（已登记，不阻塞探针）

- **S2 / T3**（revision_plan §6 第 116–123 行）：长度不同的 poly1d 比较（`__eq__` 的 shape 分支；公开 Ticket #554 测试不计分，"去掉 shape 检查"只有静态推断）；反向 `None == p`；list、ndarray 比较语义题面未约定；`assert_equal` 对数组结果按广播比较；"强制转换 `poly1d(other)`"式实现对二维 list 抛 `ValueError`（静态推断，边缘输入）；`test_doctests` 死键（上游原样，repr 与算术无评分保护）。探针抽查可用结构化后检 `rh2/experiments/r2e_actor_20260925/postcheck/numpy_18b7cd9d_behavior.py`（12 项，已用 gold / A 通过、base / D / N / I 不通过验证），不计分。
- **题面**：修法方向在题面明示（旧卡 `card.md` 第 9 行）；公开提示已换 R2E 措辞，但 `public_hints` 不进模型消息。
- **X1**：gold 4 行逐字出现在 numpy `2f4a9650`、`43e333e2`、`5e8301c2`、`d89bc4bb` 的公开初态（`runs/r2e_static_prep_20260924/cross_task_gold_scan.json`，机械扫描线索）；本题初态含 `a5ea773e` 的目标测试与 `d805e9b6` 的修复。训练时控制重复采样。
- **解题侧条件**：numpy 就地构建，`/testbed` 须在 `sys.path` 上（在 `/testbed` 下 `python -m pytest` 可用，裸 `pytest` 收集失败）；无 pip，不联网。
- **链路**（`L/probe_chain_check.md` §0 第 9–20 行、§4 第 99–108 行）：
  - 求解入口换 `rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py`；`run_matrix.py` 按题选入口、评分带 `--image-overlays`，待改。
  - 评分沿用 `scripts/replay_grade.py run` + 覆盖表（v4 正式评分即此口径，覆盖表 `all_v4/overlays.jsonl` `sha256:7b06aa16…`）。GPU 机须载入同一 image ID，ID 变了本卡评分资格要重出。
  - 隐藏测试用的 `assert_equal` 来自候选可改、评分不重置的 `numpy/testing/`（A 线共享控制面问题）；探针分析时看账本 `candidate_test_like_paths`。
  - 模型实际收到的题面消息未对本题捕获（devcheck 用合成消息）。若模型改 C 源码，numpy 以 agent 身份重编并随导出交付的链路未实测（只在 orange3 验过）。
  - 本机开销：rollout 启动到可信初始化完成约 76 s；评分 trusted setup 40–52 s（该步 300 s 硬时限）；测试段约 3 s。

## 证据索引

- 旧卡：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/{card.md,screening_record.json,review.md}`（旧 usage 只有 `intended_use: development_diagnostic`）
- 修订：`L/results/numpy__18b7cd9df7a4d960550b18faa14d5473e7d5c3d9/{revision_plan.md,revision_draft.json,trials/}`；正式条目 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v5.json` 的 `r2e-mr-021`
- Codex：`L/codex_reviews/review_revision_numpy.md` 第 7–14、30–32 行
- 正式评分：`F/status.json`、`F/plan.json`、`F/ledgers/ledger_*.jsonl`（本题均为第 1 行）
- devcheck：`D/orig/attempt.json`、`D/private_control.json`、`runs/r2e_lifecycle_20260929/devcheck_rev/v4/summary.json`
