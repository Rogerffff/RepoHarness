你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `aiohttp_240d` 的修订草案：
- `aiohttp__240da100151933883d7dea0528d45877df025b92`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__240da100151933883d7dea0528d45877df025b92/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（本题是今晚新审完的题，既有审查产物在本批 results/aiohttp__240da100151933883d7dea0528d45877df025b92/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、reviewer_initial.md、review.md；协调者对 DG1/WR1/AL1/SC1 的正式评分与私有行为对照在 runs/r2e_lifecycle_20260929/inv/aiohttp_240d/）：
- R-c 两项：`test_request_port_other_url`（非示例端口实例，堵退化候选 DG1）与 `test_https_connect_port`（https 显式端口的 CONNECT 目标，堵 WR1/WR2 这类把端口并进 host 的错层修复）。请核两项的公开依据（题面一般表述、公开 connector 代码与旧测试），是否只针对 S1、没有扩大需求。
- 复核者指出：`tests/test_client.py` 在本环境一收集就 SyntaxError（Python 3.9 与 2014 年版 aiohttp 不兼容），解题者跑不到其中的 `test_host_port`，所以第 2 项是防住 WR1 类改法的唯一保护——请判断这一点对"是否必做"的影响。
- 本题有跨题包含 X1：本题 gold 与新测试逐字出现在 aiohttp 61833518 的公开初态里。请判断它对训练 / 留出用途的影响是否已写清（这不是修订本身的问题）。
