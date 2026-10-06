你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `pillow` 的修订草案：
- `pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__3ac9396e8c991e7baab66187af2a35c3f4e83605/（revision_plan.md、revision_draft.json、trials/）
- `pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/（revision_plan.md、revision_draft.json、trials/）
- `pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2b061b68dbbf4fb590ab532b6fdffea8ee063ae8/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本包补充：
- pillow 3ac9396e 有两份草案：revision_draft.json（A+B：B 是按 v1 §4 第 4 步另列的 S1，堵 RC6）与 revision_draft_a_only.json（只有 v1 §11 列的 A）。请判断 B 的公开依据是否成立、是否属于 R-c 范围；另外 K1、K1b、K2 在修订后仍得 1，请核它们是不是满足公开要求的合理解（若是错误解，说明本题仍有未处理的 S1）。
- pillow 2b061b68 是 R-f（题面修订）草稿：请按 v1 §5 "R-f 的验收"核对每条 statement_edits 是否只做三种允许的改动、是否写进了隐藏测试细节；执行者认为 R-f 之后仍有两处有候选证据的 S1（plan §6），请判断是否成立。
