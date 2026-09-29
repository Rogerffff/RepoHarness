你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `scrapy` 的修订草案：
- `scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__e938752973b4fc53e0fa0c0bc68a431613b987e4/（revision_plan.md、revision_draft.json、trials/）
- `scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__75450e75d269b2a2b00b6303af1033df1f69cc67/（revision_plan.md、revision_draft.json、trials/）
- `scrapy__9a15fcf89a151811de8ac783419df0512c863d5e`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/scrapy__9a15fcf89a151811de8ac783419df0512c863d5e/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本包补充：
- scrapy 9a15fcf8 在 v1 §11 只列了 R-a（删两个在 py3 下必报 TypeError 的无效键），执行者另合并了两处 R-c：把公开的 tests/test_http_headers.py 原样加入隐藏测试（只做 R-a 时 Codex 构造的 bad_headers_str 得 1）；补两个非示例实例（目标断言只用了题面示例字面值，逐字特判示例的补丁得 1，v1 §4 第 2 步）。请核这两处的公开依据与是否属 R-c 范围，以及 R-a 部分是否同时删了测试与期望键、没有留下 unexpected。
- scrapy 75450e75 新增了一个隐藏辅助模块与子进程内 60 秒闹钟：请核它是否只防挂起、没有引入与公开要求无关的时间约束或时序抖动风险（v1 §3 E5）。
