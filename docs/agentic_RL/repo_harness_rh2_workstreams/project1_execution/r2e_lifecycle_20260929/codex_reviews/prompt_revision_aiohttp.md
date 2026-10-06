你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `aiohttp` 的修订草案：
- `aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/（revision_plan.md、revision_draft.json、trials/）
- `aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__22a12cc2e2ef289d9e96fd87dfc17272177e52ac/（revision_plan.md、revision_draft.json、trials/）
- `aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本包补充：
- aiohttp 61833518：执行者新构造了错误补丁 AP1m（chunked 写出器每块合成一次写、空块照发），在 results/<题>/cands/；请核它是否是合理的"已知错误候选"，以及新测试抓的是提前 EOF 而不只是空写入这一判断。
- aiohttp 22a12cc2（R-e）：mock 目标测试被重写（键名不变）。请重点核：只替换网络、指纹经公开 `ssl=Fingerprint(...)` 配置并由真实 `Fingerprint.check` 校验，是否没有把 gold 的内部实现写进测试；"请求值覆盖连接器默认值"的文档依据是否成立。
- aiohttp 1c1c0ea3：执行者判定第 2 步命中（唯一断言"不报告"的键就是题面示例输入），补了 OSError 启动失败的非示例实例；C3（Ctrl+C 后吞掉 cleanup 错误）仍为 1，登记为 S2 不处理——请判断这一分级。
- 执行者说明：22a12cc2 与 1c1c0ea3 的试跑日志尾部被覆盖率表占满，各候选失败在哪个断言是按失败键分布推断的。请据此判断现有试跑证据够不够，哪些要留给正式评分完整日志确认。
