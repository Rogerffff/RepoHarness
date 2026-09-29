你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `datalad_16c1` 的修订草案：
- `datalad__16c1ffc349df566151db0beb6d355ca27266bb8c`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（今晚新审完的题）：
- 既有审查产物都在本批 results/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/ 下：public_read.md、analysis_before_history.md、old_findings_delta.md、card.md（附录 B 是可执行草案）、screening_record.json、reviewer_initial.md、review.md、cands/。
- 协调者在当前材料上的正式评分（本机评分须把控制面保护时限放宽到 1200 s，账本 `*_budget1200`，评分语义不变）在 runs/r2e_lifecycle_20260929/inv/datalad_16c1/：
  - D（`except ValueError` 改 `except Exception`，吞掉过滤器异常）1.0，是第 3 步退化候选；
  - N（无条件把 `**_kwargs` 传给过滤器，旧式单参过滤器报 TypeError）1.0，归第 4 步；
  - C2（传全部参数，含默认值）0.0，是 T1 误拒；
  - C1 1.0；
  - 私有行为对照在同目录 pcheck_*.json。
- 修订：B.1（R-c，新增两个测试）+ B.2（R-b，放宽 `sadfilter` 的"未传入的 `dataset` 不得出现"）+ B.3（expected 加两个键，10 键），放在同一版本。
  - `revision_draft.json` 是完整版本；`revision_draft_rc_only.json` 是 R-b 撤回或待决时的默认版本（只有 R-c）。
- 试跑（试跑工具，不走控制面保护）：
  - 修订版上 gold、C1、C2 为 1；noop、D、N、F（固定传 `dataset=None`）、C-ign（忽略过滤器返回值）为 0，各在预期键失败。
  - 只上 R-c：C2 仍为 0，误拒没纠正。
  - 只上 R-b：F 为 1，出现新漏洞。
  - 所以两项必须同批。
- **请重点判断 R-b 是否属于 P5**（两种读法都有公开依据时交用户）。执行者的看法：
  - 严格读法（没传的参数不出现）的依据：同一函数里渲染钩子只收调用方写出的 `_kwargs` 这一代码先例，加上题面字面；
  - 放宽读法（没传时可以是 None）的依据：base 的命令行入口本来就把没传的 `dataset` 以 None 传入，同一个钩子会看到它；
  - 同仓后续题 `58ba5165`、`19f5b450` 的公开初态显示上游后来连默认值一起传，但那是解题者看不到的未来版本，不算依据。
  - 执行者按你对 coveragepy `f5eb` 的判法写了 A / B / C 决定包（revision_plan.md §7），建议 A（R-b 与 R-c 同批）；主审与复核都判"不是 P5"。
  - 若你判为 P5：用户选定前本题只作问题定位，默认只落 R-c-only 版本（已试跑）。
- 另请看 revision_plan.md §6：执行者核对账本时发现 `grader_profile_digest` 与 09-23 不同（`1bb8e0cf…` → `3ec1bfa8…`），复核写的"profile 相同"不成立，差在哪里还没有拆查。请判断这是否影响本题结论。
