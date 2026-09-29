你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `scrapy_a95a` 的修订草案：
- `scrapy__a95a338eeada7275a5289cf036136610ebaf07eb`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题）：
- 既有审查产物都在本批 results/scrapy__a95a338eeada7275a5289cf036136610ebaf07eb/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md（§5 修订草案，附录 A 是补丁）、screening_record.json、reviewer_initial.md、review.md、cands/。本题没有已批准的材料修订。
- 协调者在当前材料上的正式评分与私有对照在 runs/r2e_lifecycle_20260929/inv/scrapy_a95a/：
  - D（吞 `TypeError` 返回 False）、C1（合理替代解）、C2（关掉有文档的警告）、C3（恒 False）都是 1.0；
  - 私有语义对照 pcheck_semantics_*.json；
  - 解题者环境 `sys.warnoptions` 为 `[]`（pcheck_warnoptions_agent.json）。
- 修订：`test_1.py` 一条 `hidden_test_text_replace`，含两处改动。
  - R1（R-c）：`test_partial` 补"partial 包装带返回值的生成器应为 True"，外加复核建议的关键字绑定一行。
  - R2：给测试类加 `setUp`，进入 `warnings.catch_warnings()`，`simplefilter("always", UserWarning)`，`addCleanup` 复原；把两个死键 `test_generators_return_something`、`test_indentation_error` 的期望从 FAILED 改为 PASSED。键集仍是 5 个。
  - 死键成因：评分命令 run_tests.sh 用 `PYTHONWARNINGS='ignore::UserWarning,…' python -W ignore`，测试里的 `catch_warnings(record=True)` 记录不到警告，两个键在所有候选下都在 `:79`、`:256` 报 `0 != 1`。
  - R1、R2 必须同批：只做 R1 挡不住 C2，只做 R2 挡不住 D。
- **请重点判断 R2 的模板归属**。执行者与复核判为 R-a 恢复型：让在评分命令下必然失败的有效断言恢复生效，并改期望。v1 §5 的 R-a 原本是"删无效测试并删期望键"。请判断：
  - R2 属于 R-a，还是其它模板，还是模板外；
  - 会不会扩大需求：两个复活键断言的是公开测试里已有的警告行为，`docs/news.rst:1919-1921` 有文档；
  - 如果判模板外，revision_plan.md §8 已写好交用户的决定包（方案 A–E，建议 B），请评价其公允性。
- 试跑（试跑工具执行的就是 `bash run_tests.sh`，含 `-W ignore` 与 `PYTHONWARNINGS`）：
  - 修订草案下 gold ×2 都是 1，两个复活键 PASSED，即 R2 在 pytest 8.3.4 下生效；
  - C1 1；noop ×2 都是 0，只差 `test_partial`；
  - D 0，只差 `test_partial`（`:278`）；C2 0，恰好差两个复活键；C3 0（`:79` 与 `:278`）。
