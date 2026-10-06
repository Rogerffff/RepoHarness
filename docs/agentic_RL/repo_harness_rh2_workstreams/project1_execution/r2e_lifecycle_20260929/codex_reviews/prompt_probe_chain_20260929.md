你是 Codex（独立复核，只读，不要修改任何文件，不要运行容器或连远端）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md。

复核对象：R2E 探针链路检查与原型（2026-09-29 夜，B 线子代理实现，协调者 Claude B 尚未逐行审）。
- 结论文档：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/probe_chain_check.md
- 原型代码：rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py、r2e_probe_e2e.py、grade_frozen_direct.py、replay_grade_budget.py、scenarios/
- 证据：runs/r2e_lifecycle_20260929/probe_proto/（summary.json、attempt/、grade_*/、root_git_config_check/、git_path_set_check/、tests/）
- 相关正式代码（只读对照）：rh2/scripts/replay_grade.py、rh2/src/repoharness2/adapters/slime/replay_grade.py、rh2/experiments 下既有 solve_attempt.py / run_matrix.py（按文档所指路径）、quiescence_barrier.py、grading/manager.py

请回答（中文、简洁，按严重度列问题，给文件与行号）：
1. 原型的 R2E 求解入口是否正确：任务面构造、预检、冻结补丁导出是否确实包含被 .gitignore 忽略的构建产物（orange3 `.so`）且不夹带不该交付的东西（隐藏测试、控制面文件、缓存）；与正式 `export_frozen_patch` 语义是否一致。
2. 端到端证据是否支持文档结论：aiohttp 6183 回放一致；orange3 4014"重编评 1、不重编评 0、gold 1、noop 0"能否证明 grader 加载的是新产物；放宽 env_reset_timeout 的包装是否只改预算、不改评分语义。
3. 两个生产链问题是否描述准确、严重度是否恰当：(a) sanitize 删 `.git/logs/HEAD` 导致正式直评 `baseline_digest_mismatch`；(b) 静止屏障以 root 跑 git 会执行 agent 写进 `.git/config` 的 fsmonitor / external diff——在正式 profile 下是否仍构成 agent→root 代码执行，建议的修法（`-c core.fsmonitor=false`、`--no-ext-diff`，或不经 git 的指纹）是否完整（例如 clean/smudge filter、core.hooksPath、`include.path`、`safe.directory` 等其它 git 配置执行面）。
4. 文档 §4 的 D1–D6 建议有没有遗漏的前置条件或风险；明天用这套原型跑 GPU 基座探针前，哪些必须先改、哪些可以登记后带着跑。
5. 结论：原型可否用于明天的 R2E 基座探针（可以 / 改后可以 / 不可以），写明条件。
