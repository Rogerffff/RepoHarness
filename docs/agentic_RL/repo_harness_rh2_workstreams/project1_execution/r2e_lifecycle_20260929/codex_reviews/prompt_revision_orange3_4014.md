你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `orange3_4014` 的修订草案：
- `orange3__4014f2483e3bab0621c9ae0f994947c008183253`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本题补充（09-25 已审的编译题；今晚补做 v1 §4 第 3 步后命中 S1，本包是对应的 R-c）：
- 今晚的准入卡（on_hold）与第 3 步：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/probe_card.md。退化候选 DG（`EqualFreq.__call__` 非 SQL 分支在 `split_eq_freq` 之后"切点有重复就置为 []"，补丁 cands/orange3_4014_DG_dup_to_empty.patch）正式评分 1.0（27/27）：runs/r2e_lifecycle_20260929/inv/orange3_4014/ledger_DG_budget1200.jsonl 与 logs_DG/。本机评分前的控制面保护要放宽到 1200 s，评分语义不变。既有审查在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/orange3__4014f2483e3bab0621c9ae0f994947c008183253/。
- 修订：新断言并进已有目标测试 `TestEqualFreq.test_below_precision`，作为第三段（修订后 test_1.py 第 68–81 行），不新增键，27 键期望不变。数据 `[0, 1, 1+ε, 1+2ε, 1+3ε, 2]`、`EqualFreq(n=6)`；断言切点唯一，且 0 所在区间低于簇里每个值、2 所在区间高于簇里每个值；不规定切点个数与位置。
- 请核：
  - 公开依据（题面 user_prompt.txt 第 26–27 行、`discretize.py` 第 125–132 行 docstring、公开旧测试 `test_equifreq_with_k_instances`）是否支撑"去重不能把不同值之间的切点一起丢掉"；
  - n 取 6（等于不同值个数）的理由：执行者称 n=4 时 gold 自己会把 2 和簇里的值分进同一区间；
  - 断言是否过严或绑定 gold 的实现层（修在 .pyx 还是 Python 层都应可过）；
  - 执行者说初稿"0、1、2 落在三个不同区间"太松，会放过"不断减小 n 直到切点唯一"的写法，并用本地纯 Python 核对（static_check_seg3.py）改成现稿；这个判断是否成立。
- 验收：修订版试跑 gold 1、noop 0（第 55 行，与修订前相同）、DG 0（只在新断言第 80 行）、重编补丁 pyx_build 1（含新 .so）、不重编补丁 pyx_only 0、C1 1、C4 0（第 64 行）、C3 1。两个编译路径补丁是今晚探针原型真实解题产出，本地副本在 runs/r2e_lifecycle_20260929/probe_proto/runs/orange3_4014_{pyx_build,pyx_only}/attempt/candidate/。C3（小量级分辨率缺口）是 09-25 登记的 S2，得 1 不在本轮修订范围，请判断是否仍可只登记。
- 配方：本修订只改隐藏测试（评分侧），不改派生镜像配方；试跑镜像 recipe `r2e_derive_v1+sysconfig_v1`。
