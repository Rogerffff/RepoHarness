# L5 · 证据索引（只读）

目标：给早上的人一张"哪题、什么条件、做过什么、证据在哪"的表，减少各包重复找文件。

1. 遍历 `runs/env_probe_20260909_final_sync/`、`runs/env_probe_20260909_codex_backup/`、`runs/env_probe_stage1_20260910/`、`runs/swe_grading_wiring_20260915/`、`runs/swe_grading_e1_review_20260916/`（存在的话）与 `docs/.../project1_execution/env_probe_20260909/ledger/`：列出每个账本（路径、行数、schema/字段、run_tag、覆盖的任务数与 gate/candidate 种类、时间范围），每个日志目录的结构与文件命名。
2. 按任务（216 SWE-Gym + 48 R2E）生成 `<包目录>/evidence_index.json`：task → [{{kind: oracle_gold|oracle_empty|oracle_candidate|rh2_e1|deepseek_trajectory|r2e_noop|r2e_gold|monai_control|..., condition 摘要, path, verdict/reward}}]，缺的写 missing。
3. 用 `docs/.../env_overnight_20260916/task_signals_swegym.json` 交叉核对：账本里的判定与 signals 表是否一致，不一致列出。
4. `<包目录>/L5_evidence_index.md`：目录说明 + 已知缺件（例如某题只有 empty 没有 gold）+ 各账本的口径差异提醒（例如 candidate 原组与投影组、v1/v2/v3 R2E 账本被覆盖的历史）。
只读；不改任何输入；不下题目结论。
