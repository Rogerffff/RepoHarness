你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `orange3` 的修订草案：
- `orange3__9b5494e26f407b75e79699c9d40be6df1d80a040`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__9b5494e26f407b75e79699c9d40be6df1d80a040/（revision_plan.md、revision_draft.json、trials/）
- `orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本包补充：
- orange3 9b5494e2：派生镜像是 `r2e_derive_v1+env_v2`（不带构建配置步骤；原因见本批 README 09-29 02:12 行与 codex_reviews/review_code_A_B_20260929.md 的 P1），v3 已有修订 `r2e-mr-020`（env_v2 绑定按这个修订号记在 environment_overlay.py）。执行者的主修订 A 把 `test_auto_solver` 从检查 "auto" 字面量与私有钩子改成拟合后看行为（l1 真生效、默认 l2 仍用 lbfgs、'none' 可拟合），键与期望不变。另有额外 S1：P1 得 1 却破坏公开回归测试 GH 2275（默认学习器 repr 变了）——执行者推荐 B′（把同一断言并进 `test_auto_solver`，不动期望），备选 B（新增测试文件与新键，需与 `r2e-mr-020` 合并成新修订并改生产代码里的修订号绑定）。请判断：A 是否把"私有钩子"类过严断言改成了有公开依据的行为断言而没有放宽核心要求；B′ 把回归断言并进目标测试是否合适（一个键里混了两类要求，失败定位会变差），还是应选 B 或别的办法；G1 判 S2 是否成立。
- orange3 22e98f8f：只有 R-f 题面草稿（删掉与 gold 逐行相同的代码块，改为调用仓库函数；Actual Behavior 改成已有运行证据里 base 的实际输出）。请判断：R-f 是否只做了 v1 §5 允许的三类改动、没有写入隐藏测试细节或答案；"改完后无已知 S1、不附 R-c"是否成立；执行者提出的第 3 步退化候选（mapping 改为 `np.arange(len(a))`）是否应在落地前先正式评分。R-f 仍需新公开读者验收，这一点不用你代做。
