你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `pillow_4bc6` 的修订草案：
- `pillow__4bc6483564ae1a254911e98280b9a501f047a2e0`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题）：
- 既有审查产物都在本批 results/pillow__4bc6483564ae1a254911e98280b9a501f047a2e0/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md（附录 A 是 R-c 草案）、screening_record.json、reviewer_initial.md、review.md、cands/。本题 revisions.json 为空。
- 协调者在当前材料上的正式评分与公开规范性检查对照在 runs/r2e_lifecycle_20260929/inv/pillow_4bc6/：
  - D1（mode "1" 返回 `image.copy()`）、A1（`point(lambda v: 0 if v else 255)`）、W1（原地改调用者图像）、A2（`_lut` 放行 mode "1"）都是 1.0（24/24）；
  - pcheck_canon_*.json：D1 输出等于输入，W1 改了输入。
- 修订：`test_1.py` 一条 `hidden_test_text_replace`，新增独立键 `test_invert_mode_1`，对 `hopper("1")` 断言反相结果且输入不被修改；期望 24 → 25 键。
- 请核：
  1. 新断言的公开依据（原文与行号）；
  2. "输入不被修改"的依据：`invert` 对 L / RGB 本来就返回新图、不改输入；
  3. 期望值是否由公开语义推出，而不是抄 gold；
  4. W1 属第 4 步 S1 的判断；
  5. gold 对非规范取值（`color=1` 存成字节 1，反相后得 254、按 1-bit 看仍是全白，devcheck 已实测）只登记为 S2、不断言，是否合理，还是该交用户（revision_plan.md §7 写了 A / B 两个选项，推荐 A）。
- 试跑：修订版上 gold、A1、A2 为 1；noop、D1、W1 为 0，D1、W1 只在新键失败；24 个旧键状态不变。修订后 `test_1.py` 为 `9bdba0cc…`（491 行），期望映射为 `b2a68136…`。
