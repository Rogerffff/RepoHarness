你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `numpy_d89b` 的修订草案：
- `numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题）：
- 既有审查产物都在本批 results/numpy__d89bc4bbf541affbcf87498ff4af86b9451480cd/ 下：public_read.md、analysis_before_history.md（附录 B 是主审的 R-c 草案）、old_findings_delta.md、card.md、screening_record.json、reviewer_initial.md、review.md（附录 A、C 是复核补充的 diff）、cands/。本题没有已批准的材料修订。
- 协调者在当前材料上的正式评分与私有行为对照在 runs/r2e_lifecycle_20260929/inv/numpy_d89b/：
  - DEG（用含离群格的总数归一）1.0；
  - REN（`normed` 改名为 `density`、删掉 `normed`）1.0；
  - D1（只要显式传了 `density` 就归一化）1.0；
  - ORD（合理解，第 3 格浮点末位不同）0.0，只错 `TestHistogramdd.test_density_non_uniform_1d`；
  - DEP 1.0。
- 修订一轮四项，两个隐藏测试文件各一条 `hidden_test_text_replace`，期望映射 78 键 → 84 键（新增 6 键都是 PASSED）：
  - R-c1：有区间外样本时，区间内积分仍为 1；
  - R-c2：`normed=True` 仍返回同样的密度；告警放行名单含 DeprecationWarning、PendingDeprecationWarning、FutureWarning、VisibleDeprecationWarning 四类；
  - R-b：`test_density_non_uniform_1d` 的逐位相等放宽为 allclose；
  - R-c3：`density=False` 返回计数。
- 请核：
  - 四项各自的公开依据（原文与行号）；
  - R-b 放宽的是否只是没有依据的实现约束（逐位相等），有依据的行为是否都保留；
  - R-c2 的告警放行名单是否合理。执行者提出一个问题：名单不含 UserWarning，用不带类别的 `warnings.warn` 弃用 `normed` 的实现会在两个 `normed` 键失败；目前没有这样的候选。若应全部放行，可改成 `sup.filter(Warning)`，只动两行，不改变本轮任何候选的结论。请判断该不该放行；
  - 新键的期望值是否由公开语义推出，而不是抄 gold。
- 试跑：修订版上 gold 1（84/84）；noop 0，只在 10 个预期的键失败；DEG、REN、D1 都是 0，各自只在针对它的 2 个新键失败；ORD、DEP，以及可选的 C1、DEPFW 都是 1。
- 消融对照：去掉 FutureWarning 一行后，DEPFW 在两个 `normed` 键被判 0，原因是告警被 `pytest.ini` 当成错误。
