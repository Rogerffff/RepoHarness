# 夜间工作包通用规则（所有 agent 必读）

日期：2026-09-16 夜。协调者：Claude 主会话（"临时讨论流水线"分支）。用户休息，不裁定；早上集中看报告。

## 你能做与不能做
- 模型：全部 sub-agent 用 Opus 5。**不要再派生你自己的 sub-agent**（并行度由协调者控制在 6 左右）。
- 只有 M2/M3 两个机器包允许 SSH 到协调者在派发消息里指定的机器；其它包一律不连远程机器。任何包都不得把主机地址/端口/密钥写进文件，文件里只写"机器 2"/"机器 3"。
- 只在你的包目录写文件：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/<包名>/`（记录、报告、脚本）与 `runs/env_overnight_20260916/<包名>/`（大文件、日志、临时 worktree）。
- 不修改 `rh2/src`、`rh2/tests` 的既有文件；不修改本目录之外的任何文档；不执行任何 `git commit / push / stash / reset / checkout`（在 `runs/env_overnight_20260916/repos/*` 克隆里只允许 `git worktree add --detach` / `git worktree remove --force` / `git show` / `git log` / `git grep` / `git ls-tree`）。
- 不连接任何远程机器（另一会话正在用机器 1 跑 e2）；不读取 `docs/.../project1_execution/tmp/API.md`；不把任何密钥、主机地址写进文件。
- 不启动 Docker、不装依赖、不调用模型 API。
- 记录用中文，术语/路径/标识符保留原文；每条结论附证据引用（文件路径 + 行号或 commit:path，或日志路径）。
- 未检查的项写 `not_checked`，证据不足写 `unknown`；不因为没发现问题就写 pass；不复述旧结论当新发现。
- 每完成一题/一小组就落盘（增量写 JSON），不要攒到最后。到本机时间 **08:30** 停止新任务，写完当前题并交总结。
- 最终回复给协调者不超过 25 行：覆盖范围、产物路径、最重要的 5 个发现、未完成项。细节放文件。

## 记录形状（沿 `environment_screening_definition_20260915.md` §1，稀疏填写）
`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/environment_screening_definition_20260915.md` 是权威；40 项检查编号见 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/environment_screening_checklist_20260915.md`。题级记录 JSON 至少含：
`task_id, source, task_revision("upstream"), materials_refs, public_view(要求/约束/未知项，先写), checks{编号: {status, evidence_refs[], note, by}}, issues[{category, severity(P1/P2/P3), evidence_refs, proposed_action, next_experiment}], file_rules{additional_exclusions: [], rationale, evidence_refs}, proposed_regression_tests[], disposition_hint{state, reason}, costs{minutes}`。
`checks.status ∈ not_checked / pass / issue / unknown / not_applicable`。

## 材料位置（本机，绝对路径）
- 216 题四面材料：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/public_bundles_v0.jsonl`（题面 `problem_statement`、`image`、`workdir`）、`grading_bundles_v2_v0.jsonl`（`test_patch`、`fail_to_pass`、`pass_to_pass`、`eval_cmd`、`version`）、`validation_bundles_v0.jsonl`（`golden_patch`）、`environment_packages_v0.jsonl`；原始行（含 `hints_text`，**不视为 agent 可见**）：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl`。
- 逐题信号表：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/task_signals_swegym.json`（in_e2、fragile_reference_id、stage1 gold/empty 判定与安装 rc、DeepSeek 候选 oracle）；按仓库任务清单：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/tasks_by_repo.json`。
- 本地仓库裸克隆（无 checkout）：`runs/env_overnight_20260916/repos/<mypy|moto|dvc|MONAI|pydantic|dask|conan|modin|pandas>`。读某题代码：`git -C <repo> worktree add --detach runs/env_overnight_20260916/<包名>/wt/<instance_id> <base_commit>`，用完 `git -C <repo> worktree remove --force <路径>`。
- 历史证据：昨夜 216 探针与勘误 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/README.md`；阶段一日志 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<instance_id>/<empty|gold>/offline/a1/{test_output.txt,status_map.json,eval.sh}`；24 条 DeepSeek 轨迹与审查 `runs/env_probe_20260909_final_sync/ledger/logs_cc/<instance_id>/{stream.jsonl,candidate.diff,prompt.txt}`、`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/solvability_review_20260909/`；e1 真机结果 `runs/swe_grading_wiring_20260915/e1/` 与 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swe_grading_wiring_20260915/e1_report_20260915.md`、`e1_codex_review_20260916.md`；gold 静态预检 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swe_grading_wiring_20260915/precheck_after_pb.md`。
- 已批决定（直接沿用，不重问）：第四组 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/README.md` §0/§6.5（默认测试名通配已取消；额外排除默认为空）；接线状态 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swe_grading_wiring_20260915.md` §6.10–6.12。
- 外部做法汇总（按需读对应条目）：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/README.md`。
