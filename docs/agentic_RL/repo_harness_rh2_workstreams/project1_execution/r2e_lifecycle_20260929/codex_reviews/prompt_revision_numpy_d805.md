你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `numpy_d805` 的修订草案：
- `numpy__d805e9b66228e68a0eb14d901cd350159c49af18`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题，既有审查产物都在本批 results/numpy__d805e9b66228e68a0eb14d901cd350159c49af18/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、reviewer_initial.md、review.md、cands/；协调者对 K-DE、K-DC、K-DF、K-A5、K-A5b 的正式评分与私有行为对照在 runs/r2e_lifecycle_20260929/inv/numpy_d805/）：
- R-c 两处断言原样采用主审草案：`test_str_repr` 里补 n=100000 的摘要实例与 n=500 的全量显示，期望映射不变（229 键）。请核：两处的公开依据（题面、numpy 打印选项 threshold 的公开文档与行为）；n=500 全量显示采用"阈值以下必须全量显示"的严格读法——复核认为这不构成 P5，执行者用 DG-g（全局阈值改成 99）说明这条读法是承重的；请判断严格读法是否有公开依据、是否扩大需求。
- 正对照：gold 与 K-A5b。K-A5 原稿因调用到 numpy.ma 模块内同名 `max` 而崩溃（补丁错误，不是误拒）；协调者只改这一行做了 K-A5b，当前材料正式评分 1.0。请判断 K-A5b 作为补充正对照的核实依据是否充分。
- 执行者说明：试跑只留 stdout 最后 8000 字符，各候选失败在哪一行是按证据链推定的，正式评分要用完整日志核对（noop 458、K-DE / K-DC 478、K-DF / DG-e 468、DG-g 476）。
- 题面 Actual Behavior 失实（P4）与 T3（非默认 threshold、二维窄轴）本轮不修，请判断登记是否足够。
