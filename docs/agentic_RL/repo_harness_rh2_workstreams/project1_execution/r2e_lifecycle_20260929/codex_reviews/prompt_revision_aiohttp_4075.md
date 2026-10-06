你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `aiohttp_4075` 的修订草案：
- `aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题）：
- 既有审查产物都在本批 results/aiohttp__4075c653fb67a29740bf9ac050bb02d10a57343a/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、reviewer_initial.md、review.md、cands/。card.md 附录 C、D 是 R-c 补丁，附录 E 是 expected 增量与私有矩阵，附录 F 是 ALT2，附录 G 是 I4 的依据。本题没有已批准的材料修订。
- 协调者实跑在 runs/r2e_lifecycle_20260929/inv/aiohttp_4075/：
  - 当前材料正式评分：DG1 1.0、ALT1 1.0、ALT2 1.0（都是 129/129）；
  - 私有矩阵 pcheck_matrix_{none,gold,DG1,ALT1,ALT2}.json：base / gold / 各候选对 20 余种请求的接受与拒绝；
  - 公开测试私有对照 pcheck_public_{ALT1,ALT2,gold}.json：四个公开测试文件全部通过；
  - C 扩展核对 pcheck_cext_agent.json：`vendor/llhttp` 为空、无 `.so`、C 解析器不可用。
- 修订一条 `hidden_test_text_replace`（三处 edit），期望 129 键 → 134 键：
  - R-c #1：字段名中部的西里尔字母 о；
  - R-c #2：FF 单独分隔、VT 分隔两例，要求 `BadStatusLine`；
  - R-c #3：请求目标里夹 LF、FF 两例，断言父类 `BadHttpMessage`。
  - **gold 在修订版按设计为 0**：gold 把请求目标里的 LF / FF / CR / TAB 从 base 的拒绝改成了接受（I4），复核判第 4 步 S1。失败只落在 R-c #3 两键。
  - 按已授权的 D4 改用替代正对照：ALT2（gold 加请求行控制字符检查）为主，ALT1 第二；批量环境复验的正对照改用 ALT2 补丁并记 sha256（revision_draft.json 的 `env_reverify_positive_control`）。
- 请核：
  1. I4 是否确为第 4 步 S1、R-c #3 是否在模板内：公开依据见 card 附录 G 与复核 §3；base 原本拒绝。
  2. ALT1 / ALT2 作为"经独立核实的替代解"的依据是否充分：两者都比 gold、base 更严，会拒绝目标里的 `\x01` 和版本号里的 FF；ALT1 另拒字段名里的 `/`。
  3. 执行者为证明修订没有暗中要求这些更严之处，另加了 ALT3（请求行出现空白类控制字符就拒）与 ALT4（只检查请求目标），修订版试跑都得 1。执行者指出复核 §4 有一处说错：所谓"最小变体"其实也会拒绝版本号里的 FF，因为 FF 就在 `[\t\n\x0b\x0c\r]` 里，所以另写了 ALT4。ALT3、ALT4 的行为只有标准库模拟，还没有私有矩阵实测。
  4. **剩余缺口**：请求目标里的 CR、TAB 没有断言。"gold 切分 + 只显式拒 `\n`、`\x0c`"的写法能在修订版得 1，同时仍放行 CR、TAB。这是静态推断，没有已有候选，执行者只登记，没有扩大范围。请判断：按 v1 §4 第 4 步（破坏同一要求的其它实例），是否应当本轮就给 R-c #3 加 CR、TAB 两个参数（期望 +2 键），还是登记即可。
- 试跑：修订版上 ALT2、ALT1、ALT3、ALT4 都得 1；gold 0（只在 R-c #3 两键）；noop 0（恰好 5 键）；DG1 0（西里尔字母键与 VT 键）。
