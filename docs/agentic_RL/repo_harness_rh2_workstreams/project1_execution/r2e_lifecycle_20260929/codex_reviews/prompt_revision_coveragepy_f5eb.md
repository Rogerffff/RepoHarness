你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `coveragepy_f5eb` 的修订草案：
- `coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题，既有审查产物都在本批 results/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、reviewer_initial.md、review.md、cands/；协调者对 D0、C1、C2、C3 的正式评分与私有核对（含 BRANCHY 夹具的 API / XML 独立核对）在 runs/r2e_lifecycle_20260929/inv/coveragepy_f5eb/）：
- R-c 两项合并为一处 hidden_test_text_replace：BRANCHY 非示例计数（6/0/4/2）与"另起不设 branch 的报告对象后 totals 仍为 4/2"（堵按配置门控的 C3）。期望 4 → 6 键。请核两项的公开依据、期望是否由公开语义推出（不是抄 gold），以及执行者新写的 W2（两值对调）、A1（非 gold 的正确写法）是否合理。
- C1（把两键也加进每文件 summary，现被判 0）：主审交用户、复核倾向 R-b 窄版。执行者另做了 revision_draft_rb.json（R-c + R-b 窄版：每文件 summary 可以带这两个键，带了就要成对出现且值正确）并试跑；决定包在 revision_plan.md §6（A R-b 窄版 / B R-f / C 维持原样），执行者建议 A 但承认"每文件 7 个键"这条约束只有弱公开依据、R-b 处在模板边界。请判断：R-c 本身可否先落正式修订单；R-b 是否属于预授权模板内（若是，可随后落），还是属于两种读法都有依据、须用户决定的 P5；决定包是否公允。
