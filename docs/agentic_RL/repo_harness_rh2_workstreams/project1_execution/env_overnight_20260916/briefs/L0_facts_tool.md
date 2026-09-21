# L0 · 只读汇总工具 `screening_facts`

目标：实现 `environment_screening_definition_20260915.md` §6 说的"下一实施片只有一个小工具"：只读汇总 driver 账本、sidecar、冻结工件与指定参考，生成每题 `facts.json` 与来源对账摘要；用 e1 真机证据验收。

## 输入（都是现有产物）
- driver 账本 JSONL（字段见 `swe_grading_wiring_20260915.md` §6.5 与 `rh2/src/repoharness2/adapters/slime/replay_grade.py`），e1 样例：`runs/swe_grading_wiring_20260915/e1/ledger_e1.jsonl`、`ledger_e1_pandas.jsonl`。
- eval 日志与 sidecar：`runs/swe_grading_wiring_20260915/e1/eval_logs/<ref>.eval.log`、`<ref>.diagnostics.json`。
- 冻结工件：`runs/swe_grading_wiring_20260915/e1/artifacts/<task>/a*/{frozen_patch.json,baseline_manifest.json,projection.json,classification.json,stage.json}`。
- 参考：`docs/.../s2/ingest/grading_bundles_v2_v0.jsonl`（F2P/P2P、test_patch）；oracle：`runs/env_probe_stage1_20260910/ledger/stage1_offline.jsonl` + 其 `logs/.../status_map.json`；e2 账本以后同形。
- 逐 ID 状态：sidecar 只有计数，**用 `repoharness2.envpack.scoring.parse_eval_log_v2(grading_bundle, log_text)` 离线重解析 eval 日志**得到完整状态映射（标明"parser 推导"来源）；oracle 侧直接读 status_map.json。

## 产出
- 新文件 `rh2/scripts/screening_facts.py`（可 `python scripts/screening_facts.py --ledger ... --eval-log-dir ... --artifacts-dir ... --grading-bundles ... [--oracle-ledger ...] --out-dir ...`），只读，不改任何输入；`rh2/tests/test_screening_facts.py` 用 e1 样例做断言（缺文件时 skip）。用 `rh2/.venv/bin/python` 与 `rh2/.venv/bin/pytest` 运行；`rh2/.venv/bin/ruff check` 通过。不改动 rh2 其它文件。
- 每题 `facts.json` 字段（值带 `source ∈ host_observation / candidate_output / parser_derived / static / oracle` 与 `status ∈ observed / missing / not_applicable`）：运行引用（账本路径+行号、run_id、attempt、candidate）、条件（image、image_id、profile digest、shm、prefix、budgets）、候选（apply_method、classification、projection included/ignored）、评分（outcome、reward、四计数、grader_version）、候选段（install rc、install/test 秒、test rc、log_partial）、观测（导入路径、版本串、runner_integrity_changed）、逐 ID 状态表（rh2 vs 参考 vs oracle）、参考缺席/跳过、段外解析数、阶段秒、内存（0 标 unavailable_or_zero）、缺项清单。
- `reconcile.md`：每题 rh2 与 oracle 的判定与逐 ID 差异（只列差异），条件差异另列；不下因果结论。
- 在 e1 上运行一次，产物放 `<包目录>/facts_e1/`；报告写 `<包目录>/L0_report.md`：字段可观测率、缺项、与 e1 报告数字的核对（如 pandas gold F2P 16/16、P2P 缺席 3、mypy 安装段 `hash -r` 段末 rc=0）。
