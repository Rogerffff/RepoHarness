# L4 · R2E 48 题材料与适配器一致性分析

材料：原批 24 题账本 `docs/.../env_probe_20260909/ledger/r2e_ledger_v3.jsonl`（`reward_details` 含 missing/extra/mismatch 键与 expected_statuses）；新增 24 题 `runs/env_probe_stage1_20260910/r2e_expansion_preparation/{{candidate_manifest.jsonl,r2e_candidates_full.jsonl,preparation_summary.json}}` 与 `docs/.../env_probe_20260909/ledger/r2e_expansion_20260911_summary.json`；探针实现 `rh2/experiments/env_probe_20260909/r2e_probe.py`（Prime 语义的逐字复刻）；精读 `docs/harness_improve/external_paper_references/reading_notes/O03_r2e_gym.md`、`prime_swe_tasksets_validation.md`、`prime_stack_20260908.md`；已选方案 A `swe_grading_wiring_20260915/r2e_result_expression_decision_20260915.md`。

## 做什么
1. 合并去重得到 48 题清单（repo、commit、image、来源 revision、组别），写 `<包目录>/r2e_tasks_48.json`；核对"24 主批 + 24 新增"确实是 48 道 R2E（不是跨来源候选表）。
2. 每题事实（静态可得）：expected 状态计数（PASSED/FAILED/ERROR/SKIPPED 各多少）、expected 键含 ANSI/参数化空格的数量、v3/expansion 账本里 noop/gold 的 reward 与 missing/extra/mismatch 键、gold 触碰文件（`modified_files`）是否含测试文件（gold 排除测试 → fixture 风险，datalad 类）、`parsed_commit_content` 是否含测试改动、问题描述长度。写 `<包目录>/r2e_task_facts.json`。
3. 来源适配器一致性卡 `<包目录>/L4_r2e_adapter_card.md`（对应清单意见 S9 与定义文档 §2）：输入字段与初态（HEAD=修复提交父提交、镜像内 git 历史含修复提交=泄漏通道）、agent 可见/私有材料（`/r2e_tests` 隐藏；测试生成时可见 gold 的含义）、真实入口（`run_tests.sh`、venv `/testbed/.venv` 属主）、测试选择/收集、parser 与版本（Prime `parse_log_pytest`/`calculate_reward`：键规范化、`" - "` 切分、ANSI）、评分规则与计数（expected 精确匹配，方案 A 字段）、可信测试恢复方式、已知限制（coveragepy 历史环境失败进 expected；datalad fixture 缺失；pillow ANSI 键），以及接入 rh2 时每一项需要的实现点与验收样例。
4. 机器待查清单 `<包目录>/machine_checks.md`：需要镜像才能得到的事实（`/r2e_tests` 内容、`run_tests.sh` 原文、venv 属主与可写性、`git log --all` 里修复提交可达性、脏工作区文件清单、隐藏测试 import 的仓库测试模块是否被 gold 改动）与每项的命令模板。
5. 报告 `<包目录>/L4_report.md`：48 题按风险分层（expected 含 FAILED/ERROR、gold 改测试、noop 已通过、账本有 missing/extra）、方案 A 接入前必须先决定的问题（例如 expected 中的 FAILED 项在我们的条件下变 PASSED 怎么算）。
