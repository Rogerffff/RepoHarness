你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `pandas_4ec8` 的修订草案：
- `pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题，既有审查产物都在本批 results/pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、cands/；协调者对 C0、C1 的正式评分与私有行为对照在 runs/r2e_lifecycle_20260929/inv/pandas_4ec8/）：
- 本题已有用户 09-24 批准的 r2e-mr-006（新增 conftest.py）与 r2e-mr-007（期望映射替换）。第 1 版草案新增了测试键，会与 r2e-mr-007 同目标冲突（同一题同一目标只允许一条修订），所以第 2 版把两段新断言（Int64 转浮点后掩码位底层是 1.0；reindex 引入的掩码位底层是 0.0）并进已有目标测试 `test_groupby_quantile_NA_float(any_float_dtype)`，不新增键、期望保持 237 键。第 1 版存档在 trials/round1/。
- 请核：两段断言的公开依据（题面"忽略 pd.NA"、quantile 与 numpy.percentile 语义、pandas 掩码数组文档）；期望值（2.0；3.0 / 4.0）是否由公开语义推出而不是抄 gold；dtype 随参数取、不固定 Float64 的理由（numpy 参数键在 base 上照旧通过）；并入已有键导致失败定位变粗是否可接受；C0（把掩码数组底层值直接交给内核）是否确为退化候选、C1 是否为合理替代解。
- 执行者说明：试跑日志被截断，C0 失败落在第 272 行只能间接推出，需正式评分完整日志确认。
