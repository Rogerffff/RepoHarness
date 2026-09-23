你是本批 SWE-Gym 题目质量审查协调者，负责完整首批 12 题，模型按用户要求为 GPT-6 Astra、max 思考程度。用户授权今晚自主组织 sub-agent 调查及独立 reviewer；本任务的总协调者在另一 Codex 任务（local，threadId=01a08bd3-b639-7c71-a1ee-f3f4d05b3a0e）。请立即执行，不只交计划。

本任务可能在新 worktree 启动，但最新源码、文档、未提交材料的权威工作区是：
${REPO_ROOT}
所有相对材料路径按上述目录解析，不能按新 worktree 解析。允许只读调查该目录当前 RH2 实现；不要因默认分支里没有这些未提交文件而重复生成或等待。用户已授权结果写回上述目录限定的本批输出位置。先读上述工作区 AGENTS.md，再读：
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/README.md
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/coordinator_handoff.md
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/materials.md
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/actor_environment_card.md
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/batch_manifest.json
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/review_response_20260921.md
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_review_protocol_20260920.md
本批计划已被独立检查，四项澄清已采纳，无需再启动整套计划审查。旧交接卡的“尚未派发/授权后”由这条正式授权取代。

背景：项目一要建立真实 coding agent 的可靠、高效后训练闭环，主链 miles + SGLang + Claude Code + RH2。216 题已有 CPU 环境诊断，其中 166 题涉及环境修订，164 题组合验证、另 2 题原材料隔离；这不是质量通过率。本次需要独立检查题意、测试覆盖/误拒/漏测、gold 回归、开发条件等八方面，不能只核 Claude 旧结论。评分环境通过不等于 agent/54321 解题环境通过；static 候选也不是 runtime-ready。当前共享链路状态以同级上方 chain_readiness.md 和实际源码为准，避免把旧已修缺陷重新报为当前故障。

输入用 runs/swegym_quality_batch01_20260921_v2/，详见 manifest。输出全部写 ${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/：你独占 assignments.json、batch_report.md、probe_candidates.json、cpu_queue.json、method_adjustments.md 和 results/；总协调者独占 orchestration.json、orchestration.md、acceptance/、expansion/。不要覆盖其余文件。角色只能写自己获分配的 results/<instance_id>/ 文件。现有材料和旧证据保持不变。可在工作区 runs/ 下另存本批只读核验结果，但不要把可见私有信息混入公开包。

执行依赖：先 Conan15422/14177 和 Dask8597/8801 四题完成角色链与方法校准，再做固定余八题 Pydantic8511/5706、DVC5839/9395/3620、mypy10424/16963/12417。不因难度或结果换题。每题独立公开读者用 fresh context（fork_turns=none），只给该题 public 目录、public_reader 角色卡及输出路径，不给本消息、计划选择理由、manifest、旧报告、gold/隐藏测试。本题 public_read.md 落盘后才开始该题私有主审；主审 fresh context 可同仓2–3题，先原件自由调查、再按八方面查缺，保存 analysis_before_history.md 后，你才给 history/<id>/refs.json。独立 reviewer 也 fresh context、不是主审，先仅原件写 reviewer_initial.md，再 followup 给主审/公开结论写 review.md。不要把角色合并；独立复读日志不称独立复现。并发按工具容量安排，闲槽可做不同题的不同阶段，不因晚间目标破坏同题顺序。

每题给短卡、需求与验收断言双向映射、开发需求及证据缺口、screening_record.json。保持正式原题/断言/参考/二值reward不变，不擅自补隐藏要求到题面。首波开始即交接成熟单题 CPU 验证队列，3–5 个候选是目标不是门槛；不用等12题才交接。分析 unknown/not_checked 不能填通过，不要求隐藏测试对 solver 可见或全仓测试都可跑。

你可以使用 sub-agent，子任务继承本任务配置即可，不另建侧边栏任务。阅读历史项目代码和已有日志只作静态分析，不在宿主安装/运行历史项目，不开 Docker/SSH、不下载大镜像、不调用付费模型、不租机、不修改生产代码、不提交推送。不接触旧已删远端。需要 CPU/模型执行则输出可执行方案与前置，由总协调者另行安排。本夜允许自主方法改进并记录；任务/评分语义变更只提具体候选，不直接改。

进度协调：登记真实 agent ID、角色、题目、开始结束时间与证据路径。首波四题收口、发现重要方法缺口、或全部12题完成时，使用 send_message_to_thread 给上述总协调者发简短通知和具体结果路径。用户已授权这种任务内协作；不要给其他人发消息。首波通知后可以继续固定余八题，不必等总协调者答复。完成12题后向总协调者请求下一固定小批；不要自行一次铺开216题。总协调者会核额度、抽验质量及授权扩量，你不要兑换任何重置卡或建重复自动化。

目标是在 Asia/Singapore 2026-09-21 08:00 前尽量推进有用、完整且可复核的工作。07:30 后优先收口在手题；08:00 不启动新题。当前题若确需继续，落盘状态并通知总协调者，不能把部分结果写完成。现在先检查材料/写 assignments.json，然后启动第一波。
