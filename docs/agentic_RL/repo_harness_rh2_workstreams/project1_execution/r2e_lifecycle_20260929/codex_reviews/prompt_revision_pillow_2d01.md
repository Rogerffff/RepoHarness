你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `pillow_2d01` 的修订草案：
- `pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题）：
- 既有审查产物都在本批 results/pillow__2d01f7d02243d1b9cd3f2a3c3587d87703e00f96/ 下：public_read.md、analysis_before_history.md（附录 B 是主审的 R-c 草案）、old_findings_delta.md、card.md、screening_record.json、reviewer_initial.md、review.md（§5 是合并版 R-c 与验收矩阵）、cands/。
- 协调者在当前材料上的正式评分与私有行为对照在 runs/r2e_lifecycle_20260929/inv/pillow_2d01/。D、C1、C3、复核者补充的 A（写完后原地反相调用者的图像）、B（改读取端不反相）正式评分都是 1.0，C2 是 0.0。
- 修订：合并版 R-c 的四项全部并进已有目标测试 `test_photometric`（参数 [1]、[L] 两键），不新增键，62 键期望不变，只有一条 `hidden_test_text_replace`。四项是：
  1. 未指定或显式 262=1 时保留 BlackIsZero；
  2. libtiff 压缩路径（G4 / LZW）的 WhiteIsZero 往返；
  3. 保存前快照：保存不得原地改动调用者的图像；
  4. 未压缩条带的存储字节与所声明的 262 一致。
- 题意问题：像素是否要反相按 P4 登记，不交用户；R-f 可选，本轮没做。
- 请核：
  - 四项各自的公开依据（原文与行号）；
  - 期望值是否由输入与公开语义推出，而不是抄 gold；
  - 第 4 项"存储字节"在 P4（反相语义）未定的情况下，是否把某一种实现方式变成了隐性要求——例如只改标签不反相的实现，是否本应算合理解；
  - 并进已有两个键、失败只能靠日志行号区分，是否可接受；
  - C1 是否确为合理替代解，A、B 是否确为错误解。
- 试跑：修订版上 gold 1、C1 1，noop / D / C3 / C2 / A / B 都是 0，各停在专门针对它的断言行（执行者报告：noop 459、D 476、C3 492、C2 460、A 457、B 468）。镜像里 libtiff 可用，正式重建后仍须确认。
- devcheck 事实（与修订无关）：公开测试 `Tests/test_file_tiff.py` 的 `test_closed_file`、`test_context_manager` 用了 `pytest.warns(None)`，在镜像的 pytest 8 下报 `TypeError`；base 与 gold 同样失败，是公开测试与 pytest 版本的旧冲突。
