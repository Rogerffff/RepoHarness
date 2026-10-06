你是 Codex（独立复核，只读，不要修改任何文件）。仓库根是当前目录。审查口径见 docs/agentic_RL/repo_harness_rh2_workstreams/review-standards.md；处置与修订规则见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/task_screening_standard_v1_20260925.md（统一标准 v1，§5 的修订模板已由用户一次性授权：Claude 执行、Codex 复核，复核通过后才用于正式材料与探针）。本批背景见 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/README.md。

请复核 R2E 修订包 `misc` 的修订草案：
- `datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/（revision_plan.md、revision_draft.json、trials/）
- `pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0`：docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0/（revision_plan.md、revision_draft.json、trials/）

每题的私有材料（隐藏测试、期望映射、gold）在 runs/r2e_static_prep_20260924/v3/private/<instance_id>/，公开包在 runs/r2e_static_prep_20260924/v3/public/<instance_id>/；既有审查产物在 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925/results/ 或 docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/results/；已有候选补丁在 runs/r2e_actor_20260925/grader_cands/。trials/ 下是一次性容器试跑结果（不是正式评分：不核隐藏测试树摘要，权限布置简化；工具见 rh2/experiments/r2e_lifecycle_20260929/trial_grade.py）。

逐题回答（中文、简洁）：
1. 模板是否用对、改动是否只针对有公开依据的窄问题（v1 §5 各模板的边界；R-c 每处修改针对一个有公开依据的窄问题；R-a 删测试须同时删 expected 键、不留 unexpected；R-b 保留有依据的行为要求；R-e 同时覆盖正例与反例；R-f 不写隐藏测试细节、不新增无依据要求）。公开依据是否真实成立（请核对原文与行号）。
2. 验收是否满足 v1 §5：正对照为 1（gold，或经独立核实的替代解——核实依据是否充分）、noop 为 0、本次要纠正的误判已被纠正、已知相关错误候选仍为 0；新断言是否只是把 gold 的输出抄成期望。试跑证据是否支持这些结论，哪些还需正式评分确认。
3. 是否扩大需求、是否因保 gold 而放宽要求、是否泄漏答案或让题面与测试更矛盾。
4. 结论：通过（可落正式修订单）／需小改（写明改什么）／不通过（写明原因与是否暂挂）。


本包补充：
- datalad 19f5b450：R-c 新增 3 个只断言退出码的测试（`run 'exit 5'`→5、输入缺失→1、`--on-failure ignore`→0），期望 +3 键。执行者把草案 v0 里"Python 层 stderr 必须为空"的约束在定稿 v1 去掉了（不把有争议的约束扩到新路径）。请核：三个实例是否都有公开依据、属于同一核心要求；去掉 stderr 约束是否合适。注意本题正式评分在本机常因控制面保护 `chown -R` 超过 300 s 记 infra_failure（链路问题，不是本题材料问题），试跑工具不走这一步。
- pandas 32dd55cb：v3 已有修订 `r2e-mr-016`/`017`（请核对它们的目标，确认本次只改 test_1.py 与之不冲突、不需要合并）。本次三处：T2 用 R-b 改为接受两条有文档的 Period 报错文字；T1 内加 sum 对照（v1 §11 已列）；T1 内加含缺失值的均值断言（§11 未列，执行者在 revision_plan.md §6 单列了公开依据，称它是放宽 T2 的配套条件）。请重点核：R-b 放宽是否"保留有依据的行为要求"而不是为保 gold 放宽；缺失值均值断言的公开依据是否成立、是否扩大需求；执行者按审查记录文字新写的 C3、C3g、C4 补丁（cands/）是否忠实于原描述；"只放宽 T2 时 C3、C4 得 1"等对照是否证明两条新断言都不可少。
