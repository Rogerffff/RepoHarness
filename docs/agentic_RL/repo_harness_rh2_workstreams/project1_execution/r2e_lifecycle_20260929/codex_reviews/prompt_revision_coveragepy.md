你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `coveragepy` 的修订草案：
- `coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__97997d2cd6801d0335e3fa162b719d6f8c160266/（revision_plan.md、revision_draft.json、trials/）
- `coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/（revision_plan.md、revision_draft.json、trials/）
- `coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本包补充：
- coveragepy 97997d2c：执行者判定"替换"有直接公开依据（题面第 23 行注释、set_option 文档的 "new value" 与 "same effect as this configuration file"），把替换断言也补上了。请重点核这一判定；若"两种读法都有依据"，这一点应按 P5 交用户，而不是写进测试（plan §2.3 有只改一行的退路）。
- coveragepy ea6906b0：新增 test_2.py 用真实 git 检查报告文件被忽略——请核评分侧依赖 git 是否合理（正式 grader 以 uid 54322 运行，是否能用 git 需正式评分确认），以及搬入的公开旧测试是否原样。
- coveragepy 5dbbe143：执行者写成了 P5 决定包（按消息还是按 slug 去重），并另做了一个与读法无关的 R-c（"不同 slug 各显示一次"）。请判断：决定包是否公允；与读法无关的那条 R-c 能否先单独落正式修订单。
