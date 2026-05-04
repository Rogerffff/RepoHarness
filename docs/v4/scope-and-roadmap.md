# RepoHarness V4 范围和路线图

## 1. V4 背景和 V3 基线

RepoHarness 是一个面向 agentic training 和 post-training 的轻量级软件工程智能体 Harness。它的主线不是复刻完整开发者产品，也不是建设大规模训练集群，而是在真实或半真实仓库任务中稳定地产生可执行、可审计、可导出的智能体轨迹。核心数据流仍然是：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

V4 以 V3 当前最终验收结果为可信基线。范围编写前已经只读确认：

- V3 closure commit 为 `17b1b95 fix: handle excluded post acceptance docs`；范围编写前 HEAD 指向该提交。后续 V4 文档提交后，基线检查应改为确认 `17b1b95` 是当前 HEAD 的祖先，而不是要求 HEAD 永远停在该提交。
- `repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete` 通过。
- `repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable` 通过。

V4 必须准确继承以下 V3 已实现事实，不能在范围文档中把它们重写、弱化或夸大：

1. 固定 SWE-Bench-like 输入冻结已经完成。
2. adapter-visible task input 和 evaluator-only evidence 已拆分，任务输入可见性不再依赖隐含约定。
3. V3 schema、visibility policy、污染 denylist、trajectory store facts、Docker facts、SWE-Bench-like facts、context compaction facts、failure diagnostics、policy snapshots、command log 和 acceptance report schema 已建立。
4. Docker backend 已经从 V2 的 interface-only 或拒绝路径升级为真实 Docker backend。
5. Docker 仍然只是 Docker-based executable repository environment，不是生产级安全沙箱，也不提供多租户安全隔离承诺。
6. 真实 repository-level task adapter 和 source materialization 已实现。
7. 固定 SWE-Bench-like 小子集已经实现，使用 RepoHarness 自有 verifier，不声称公开 SWE-Bench Lite 榜单或 SWE-Bench Verified 榜单可比。
8. Agent Loop 已经集成真实 repository-level task 和 SWE-Bench-like task。
9. Experiment resume 和 checkpoint 最小能力已实现。
10. Context compaction 和 long rollout diagnostics 已实现。
11. Core failure diagnostics 已实现，但它不是完整 reward system，也不替代 final verifier。
12. V3 export audit 已实现，并继承 V2 export 契约。
13. PreparedMessages 与 export observation 的硬绑定已经纳入审计。
14. 最终 acceptance 使用显式 RUN_SELECTION_MANIFEST 和 ACCEPTANCE_INPUTS。
15. 当前 V3 新最终验收已经通过，核心 `real_repository` 和 `swebench_like` 角色都是 DeepSeek + Docker + `final_verifier_status=accepted`。
16. 当前 export audit 的唯一非阻塞 warning 是 `preference_pair_baseline_blocked`，其 blocked reason / residual risk 是 `no_trainable_preference_pair`。V4 需要把它转化为训练导出质量改进目标，不能把它描述成已经解决。

当前 V3 最终验收还包含以下具体证据：

- `inspect-v3-acceptance --assert-complete` 已通过。
- `inspect-acceptance-bundle --assert-immutable` 已通过。
- 预验收全量测试记录为 `488 passed in 220.34s`。
- V2 regression 通过，状态为 `passed`，`task_count=20`，真实 provider 为 `accepted_with_credentials`。
- V3 export audit 状态为 `passed_with_warnings`，唯一非阻塞 warning 是 `preference_pair_baseline_blocked`，其 blocked reason / residual risk 是 `no_trainable_preference_pair`。

技术报告材料和 Claude Code 参考实现对 V4 的启发主要来自以下方面：

- rollout orchestration 可以降维为单机队列、租约、重试、预算、资源锁、批处理恢复和机器可审计运行选择。
- PR / issue task construction 和 executable coding task generation 可以降维为少量固定修订、固定 source archive、人工可审计任务构造流程和 baseline verifier。
- failure filtering、trajectory packing、reward hacking risk audit 和 training data quality audit 可以降维为导出前质量分层、失败数据集、patch quality metrics、reward audit report 和严格 trainable/diagnostic 分流。
- Claude Code 的 query loop、tool lifecycle、permission decision、hook lifecycle、MCP、slash command、skill、session/context/memory、subagent/sidechain transcript、tool result truncation/artifact、background task 机制只能作为训练轨迹事实和审计边界的参考，不能把 V4 写成完整 Claude Code 或 Codex 产品复刻。

## 2. V4 总目标

V4 的总目标是：在 V3 已经通过的可执行仓库任务、Docker backend、SWE-Bench-like 小子集、上下文压缩诊断、导出审计和最终验收机制之上，进一步增强 RepoHarness 稳定产出更多真实、可比较、训练友好的 agent 轨迹的能力。

V4 的中心判断是：RepoHarness 现在最需要的不是更多产品能力，而是更稳定的数据生产能力、更清楚的任务构造边界、更高质量的训练导出和失败诊断材料。因此 V4 最小完成定义只承诺三条第零优先级（P0）主线：

1. 单机 rollout 和实验编排升级。
2. 受控固定任务集扩展和人工可审计 PR / issue 任务构造。
3. 训练导出质量、trajectory packing 和 failure / reward 审计升级。

本轮 V4 implementation phase 还明确把两个低风险、高审计价值的 P1 增强与 P0 一起纳入：

1. P1-2 的轻量 audit-only 版本：只做权限判断、工具生命周期和 hook 审计事实，不做完整 Claude Code / Codex 产品式 hook 系统。
2. P1-4 的完整轻量卡片版本：生成 dataset card、run card、export card，以及 provenance、污染扫描和复现命令索引。

本轮 V4 implementation phase 不纳入完整 P1-1 provider / scaffold / budget 评测矩阵，不纳入完整 P1-3 context strategy / project context / session continuation，也不纳入任何 P2 候选。P1-1 在本阶段只要求 P0 轨迹和导出保留必要元数据，方便后续版本做可比较分析。

## 3. V4 与 V3 的差异

V3 的重点是证明 RepoHarness 可以在真实 Docker backend、真实 repository-level task、固定 SWE-Bench-like 小子集和严格可见性审计下完成端到端验收。V3 已经证明了核心路径可以跑通，并且最终 acceptance 能够以显式输入和不可变 bundle 复核。

V4 的重点不是重写这一条路径，而是把 V3 的验收式运行升级为更适合训练数据生产和评测分析的稳定流程：

- 从少量最终验收运行，升级为单机可恢复批处理和可查询运行选择。
- 从少量固定任务，升级为约 10 个 accepted / auditable tasks，并且每个任务都有可复查的构造证据。
- 从“导出干净”升级为“导出分层清楚、失败可分析、训练适用性可审计”。
- 从 V3 的 `preference_pair_baseline_blocked` warning 和 `no_trainable_preference_pair` blocked reason，升级为显式的 preference pair 可训练性改进目标和阻塞原因报告，而不是把 warning 静默吞掉。

V4 不改变以下 V3 基础边界：

- final verifier 仍然是成功和 reward 主事实的权威来源。
- evaluator-only evidence、gold patch、hidden test selector、official harness report、official report、官方 resolved status、provider raw response、Authorization marker 和 provider credential marker 不进入模型可见上下文或正式训练 payload。
- Docker 仍然按 executable repository environment 描述，不升级宣传为生产级沙箱。
- RepoHarness 仍然是单机优先、轻量、可审计的软件工程智能体 Harness，不是完整产品系统或分布式强化学习平台。

## 4. V4 第零优先级（P0）最小完成范围

### P0-1：单机 rollout 和实验编排升级

目标是把 V3 的单次或少量验收式运行升级为更适合训练和评测数据生产的单机 rollout orchestration。这个能力必须服务于“稳定产出更多可比较轨迹”，不能变成大规模集群调度项目。

V4 应该包含：

1. rollout queue：用显式 manifest 描述待运行任务、provider、scaffold、预算、环境后端和选择条件。
2. run leasing：单机 worker 获取运行租约，记录租约开始、续约、完成、释放和过期事实。
3. 失败重试：把 provider error、environment error、tool error、verifier inconclusive、timeout 等失败类别与重试策略分开记录。
4. 预算控制：记录每个 run 的 token、wall time、tool count、test run count、provider retry 和 Docker resource facts。
5. 资源锁：避免同一 source workspace、Docker image build、dependency cache、固定任务 materialization 被并发破坏。
6. 批量运行状态：能够区分 queued、leased、running、accepted、failed、invalid、retried、skipped、quarantined。
7. run selection query：最终验收和导出不依赖手工挑选路径，而是由可审计 query 产生 run selection manifest。
8. command log lineage：每个批处理 run 能够追溯到触发命令、队列 manifest、worker log 和重试报告。
9. 可恢复批处理：中断后可以根据队列状态、租约状态和 checkpoint 继续运行，不重复污染已完成 run。
10. resource usage facts：比 V3 更清楚地记录单机资源使用事实，但不承诺跨机器调度。

建议机器产物：

- `rollout_queue_manifest.json`
- `worker_run_log.jsonl`
- `lease_state_report.json`
- `batch_resume_report.json`
- `retry_policy_report.json`
- `resource_usage_report.json`
- `run_selection_query_report.json`

验收原则：

- 必须能 inspect 队列、租约、批处理恢复、重试、资源使用和 run selection query。
- 必须能模拟 worker 中断后恢复，证明 completed run 不被重复执行，expired lease 可以被重新认领。
- 必须证明 fallback 成功不会伪装成 primary provider 成功。
- 必须继续产出显式 RUN_SELECTION_MANIFEST 和 ACCEPTANCE_INPUTS。

非目标：

- Kubernetes。
- 大规模异步强化学习 rollout 集群。
- 训练推理服务解耦。
- 云端多租户调度系统。

### P0-2：受控固定任务集扩展和人工可审计 PR / issue 任务构造

目标是从 V3 的少量固定任务扩展到约 10 个 accepted / auditable tasks，并建立可复查、可冻结、可审计的任务构造流程。这里的重点是任务质量和审计证据，不是大规模自动挖掘。V4 最小验收门槛建议为至少 8 个 accepted / auditable task definitions，其中至少 4 个必须是通过 V4 PR / issue 构造流程新增的任务；V3 既有任务可以作为回归锚点计入少量基线任务，但不能替代 V4 新构造任务。

V4 应该包含：

1. 真实 PR / issue 到任务定义的人工可审计流程：记录原始来源、固定修订、人工选择理由、可见输入、evaluator-only evidence 和 verifier 计划。
2. fixed source archive / fixed revision：正式任务不能依赖浮动默认分支，也不能在验收时联网拉取不可控内容。
3. baseline verifier：构造任务前必须证明 baseline 状态、预期失败、通过用例和执行环境可复现。对 bug-fix task，`fail_to_pass` 的初始失败是有效任务信号，不能被误判为 invalid；`pass_to_pass`、setup、依赖安装、环境健康检查和 broad regression failure 才用于判定任务是否 unstable、quarantined 或 rejected。
4. flaky 检测：对固定任务进行重复 verifier 运行，记录不稳定测试、环境超时和依赖问题。
5. 环境稳定性评分：以依赖安装、测试耗时、失败波动、Docker 平台事实、缓存命中为依据形成稳定性报告。
6. 依赖缓存：记录依赖缓存来源、hash、命中情况和失效原因，提升单机重复运行稳定性。
7. source materialization 可重复检查：重复 materialization 必须得到一致 source hash、task input hash 和 verifier plan hash。
8. evaluator-only evidence 隔离继续作为硬门槛：gold patch、官方 resolved status、隐藏测试选择器、raw test patch 和其他 evaluator-only evidence 不得进入 adapter-visible input 或模型上下文。
9. generated task definition 可审计：任务定义可以由工具辅助生成，但正式接受前必须有人工可审查 manifest 和 denylist scan。

建议机器产物：

- `pr_task_construction_manifest.json`
- `source_archive_manifest.json`
- `task_validity_report.json`
- `baseline_verifier_report.json`
- `source_materialization_report.json`
- `flaky_detection_report.json`
- `generated_task_definition.jsonl`

验收原则：

- 必须能从任务定义追溯到固定 source archive、fixed revision、baseline verifier 和 evaluator-only evidence 分区。
- 必须有 negative test 证明 raw gold patch、raw test patch、官方 resolved status 或 hidden test selector 一旦进入 model-visible 输入就会被污染检查拒绝。
- 必须区分 accepted task、diagnostic-only task、quarantined task 和 rejected task；diagnostic-only、quarantined 和 rejected 不能计入 accepted / auditable task 最低数量。
- 约 10 个任务是目标规模，优先 accepted / auditable，而不是追求数量；最终验收必须通过 `task_validity_report.json` 或等价 inspect 命令证明至少 8 个 accepted / auditable task definitions，并证明至少 4 个是 V4 新构造 PR / issue task。

非目标：

- 完整 SWE-Bench Lite 或 SWE-Bench Verified 榜单复现。
- 大规模自动 PR mining。
- 默认联网构造任务。
- 使用浮动默认分支作为正式任务来源。
- 不可人工审计的大规模自动数据构造。

### P0-3：训练导出质量、trajectory packing 和 failure / reward 审计升级

目标是让 V4 不只是“导出干净”，而是导出更适合监督微调、偏好训练、强化学习 rollout 分析、失败诊断和评测系统使用的高质量轨迹数据。

V4 应该包含：

1. 样本分层：把 success、partial success、failure、invalid、diagnostic-only、trainable 明确分开。
2. failure dataset：把 tool failure、environment failure、format error、permission denial、context limit、patch apply failure、verifier failure、timeout、no progress 等类别导出为可分析数据集。
3. trajectory packing：在不破坏回放和审计的前提下，把多 turn 轨迹打包为训练友好的样本，并保留原始 trajectory ref。
4. preference pair 可训练性改进：针对 V3 的 `preference_pair_baseline_blocked` warning 和 `no_trainable_preference_pair` blocked reason / residual risk，建立可训练 pair 产生条件、阻塞原因统计和 fallback 规则。
5. patch quality metrics：记录 patch 行数、文件数、测试相关改动、非相关改动、重复改动、生成文件改动和过大 patch 风险。
6. minimal patch / excessive patch 判断：把“最小必要改动”和“过度改动风险”作为诊断事实，不作为替代 final verifier 的成功标准。
7. test overfitting 风险审计：检查是否出现只改测试、绕过 verifier、删除失败路径、硬编码隐藏 selector、污染 evaluator-only evidence 等风险。
8. reward hacking risk audit：审计 reward 相关信号是否被模型看到，是否存在把诊断信号误当训练目标的风险。
9. diagnostic_only 与 trainable 严格分流：诊断材料可以导出用于分析，但进入训练 payload 必须通过 export policy、visibility policy 和污染扫描。
10. RunSpec 级元数据保留：即使 V4 不启用 P1 provider / scaffold matrix，P0 trajectory quality 和 export 样本也必须保留 `scaffold_id`、`tool_policy_id`、`verifier_id`、`environment_id` 和任务来源标识，避免后续质量分析需要重新解释轨迹。

建议机器产物：

- `trajectory_quality_manifest.json`
- `sample_tier_manifest.json`
- `failure_dataset.jsonl`
- `packing_manifest.json`
- `reward_audit_report.json`
- `reward_hacking_risk_audit_report.json`
- `patch_quality_report.json`

验收原则：

- final verifier 仍然是 accepted / rejected / inconclusive 的权威来源。
- LLM judge、reward audit、patch quality metrics 只能作为诊断或过滤辅助，不能替代 final verifier。
- trainable payload 不得包含 evaluator-only evidence、reward-only evidence、gold patch、hidden test selector、official harness report、official report、官方 resolved status、provider raw response、Authorization marker 或 provider credential marker。
- reward scalar、reward label、verifier 原始输出、verifier trace、隐藏测试执行细节和隐藏 selector 命中细节只能作为评测、审计、筛选、分层或外部元数据使用；如果需要随导出保留，也必须位于非模型可见字段中，并接受 export policy、visibility policy 和污染扫描约束，不能进入模型可见训练 payload 或训练 target 文本。
- `no_trainable_preference_pair` 不能被掩盖。如果 V4 仍然不能产生可训练 preference pair，必须产出明确的阻塞原因分布、样本数量、被拒绝原因和后续修复入口。

非目标：

- 训练强化学习算法。
- 训练 reward model。
- 实现完整防作弊奖励模型。
- 声称已经训练出 coding agent。
- 用 LLM judge 或 reward audit 替代 final verifier。

## 5. V4 第一优先级（P1）本阶段取舍

P1 范围价值高，但不应挤掉三条 P0 主线。本轮 V4 implementation phase 已经做出明确取舍：

- 与 P0 一起纳入：P1-2 轻量 audit-only 版本、P1-4 完整轻量卡片版本。
- 仅保留元数据，不做完整增强：P1-1 provider / scaffold / budget matrix。
- 本阶段不完成：P1-3 context strategy / project context / session continuation。

任何被纳入本阶段实际实施或最终验收的 P1，都必须像 P0 一样定义 schema、inspect 命令、正例、负例、是否通过 run selection role ref、ACCEPTANCE_INPUTS 或 acceptance bundle 绑定、失败时是否阻塞，以及允许降级为非验收候选的条件。没有这些验收口径的 P1 只能保留为非验收候选，不能成为 V4 本阶段完成定义的一部分。

### P1-1：小型 provider / scaffold / budget 评测矩阵

本阶段处理结论：只保留必要元数据，不实现完整评测矩阵，不把矩阵报告作为 V4 本阶段验收硬门。

后续候选范围：

- 2 个 provider 条件。
- 2 个 scaffold。
- 3 到 5 个固定任务。
- 固定预算。
- 严格 compare scope。
- token usage 和 provider error taxonomy。
- fallback policy 明确记录。

本阶段必须保留的元数据：

- `provider_id`
- `provider_mode`
- `model_id`
- `scaffold_id`
- `budget_policy_id`
- `fallback_policy_id`
- `token_usage`
- `provider_error_category`
- `tool_policy_id`
- `verifier_id`
- `environment_id`

本阶段不完成的机器产物：

- `provider_eval_matrix_report.json`
- `provider_compare_scope.json`
- `scaffold_comparison_report.json`
- `scaffold_quality_metrics.json`
- `per_scaffold_export_quality.jsonl`

本阶段边界：

- 不做 provider leaderboard。
- 不做大规模真实 provider rollout。
- 不把真实 provider 对比作为 V4 本阶段验收硬门。
- 不把 fallback 成功伪装成 primary provider 成功。
- 不把 raw provider response 放进训练 payload。

### P1-2：permission trace 和 hook audit-only 最小闭环

Claude Code 参考实现显示，真实 agent 产品里的工具调用会经过 schema validation、permission decision、PreToolUse / PostToolUse / tool error hooks、permission hooks 和工具结果处理。RepoHarness V4 可以把这些能力降维为审计事实，而不是实现完整交互式产品。

本阶段处理结论：与 P0 一起纳入轻量 audit-only 版本，只记录权限判断、工具生命周期和 hook 审计事实，不实现完整 Claude Code / Codex 产品式 hook 系统。

本阶段纳入范围：

- `permission_decision_trace.jsonl`。
- allow / deny / ask / safety deny / hook deny 审计样例。
- `tool_lifecycle_trace.jsonl` 或等价 tool lifecycle audit facts，用于记录工具查找、schema validation、permission decision、hook decision、execution status、artifact ref、truncation status 和 tool_result pairing status。
- before_tool / after_tool / tool_error 的 audit-only hook 事件。
- hook 默认 audit-only。
- public diagnostic 必须显式标记，并通过污染检查后才能进入模型上下文。
- hook 不得改写 final verifier、reward 主事实或历史 transcript。
- `permission_decision_trace.jsonl` 至少应包含 `decision_stage`、`rule_source`、`matched_rule`、`permission_mode`、`headless_or_interactive`、`hook_override`、`content_safety_check` 和 `final_decision`，避免只能看到允许或拒绝结果却无法审计规则来源。

本阶段机器产物：

- `hook_policy_snapshot.json`
- `hook_audit_report.json`
- `tool_lifecycle_trace.jsonl`
- `permission_decision_trace.jsonl`
- `permission_policy_dataset_manifest.json`
- `tool_contract_v4_snapshot.json`

本阶段不完成：

- 不做完整命令面板。
- 不做插件市场。
- 不做用户可配置、项目可配置、插件可配置或技能 frontmatter 可配置的完整 hook 系统。
- 不做 before_model_call / after_model_call hook；如果后续版本需要模型调用前后审计，必须单独定义 schema、污染边界和验收口径。
- 不做 stop hook、session hook、file changed hook、subagent hook 或远程会话 hook。
- hook 不得改写 final verifier、reward 主事实或历史 transcript。
- hook 不得改写工具输入、工具结果、模型历史消息或正式 training target。
- 不自动批准危险命令。

### P1-3：context strategy、project context 和 session continuation

V3 已经实现 context compaction 和 long rollout diagnostics。V4 可以在 P1 中比较更明确的上下文策略，但必须继续保留 PreparedMessages 与 export observation 的硬绑定。

本阶段处理结论：不完成完整 P1-3。V4 本阶段只继承 V3 已有的 context compaction、long rollout diagnostics、PreparedMessages 与 export observation 绑定，并要求 P0 / P1-2 / P1-4 产物继续保留 `prepared_messages_ref`、`model_input_hash` 和 `context_revision` 相关审计事实。

后续候选范围：

- keep-recent。
- summary。
- artifact-only。
- retrieval-assisted context。
- ProjectContextSnapshot。
- 三段式 session continuation。
- 用户追加约束后继续运行。
- 中断后恢复继续运行。

如果后续版本重新纳入 P1-3，必须满足以下硬要求：

- 必须绑定 `prepared_messages_ref`。
- 必须校验 `model_input_hash`。
- 必须记录 `context_revision`。
- 必须证明 export observation 与模型当时看到的一致。
- 默认不得跨实验携带长期用户记忆。

本阶段不完成的机器产物：

- `context_strategy_registry.json`
- `context_strategy_comparison_report.json`
- `context_replacement_trace.jsonl`
- `project_context_snapshot.json`
- `session_continuation_manifest.json`

本阶段边界：

- 不做 provider KV cache 恢复。
- 不默认跨实验长期用户记忆。
- 不建设百万 token 框架。
- 不建设产品级 memory database。
- 不把 retrieval-assisted context 作为本阶段实现内容。
- 不把 session continuation 作为本阶段验收内容。

### P1-4：dataset card / run card / export card

本阶段处理结论：与 P0 一起纳入完整轻量版本，用于把 V4 任务来源、运行条件、导出边界、污染扫描、失败分布和复现命令转化为人工可读且机器可读的审计卡片。

本阶段纳入范围：

- dataset card。
- run card。
- export card。
- license / provenance summary。
- contamination scan summary。
- 任务来源表。
- 模型条件表。
- 失败分布表。
- 可复现命令索引。

本阶段机器产物：

- `dataset_card.md`
- `dataset_card.json`
- `run_card.json`
- `export_card.json`
- `provenance_summary.json`
- `contamination_scan_summary.json`
- `repro_command_index.json`

本阶段边界：

- 不自动发布到外部平台。
- 不对外宣称公开 leaderboard。
- 不声称数据无需人工审查即可直接训练。

## 6. V4 第二优先级（P2）本阶段不进入范围

P2 范围全部标记为本轮 V4 implementation phase 不完成。它们可以保留为后续版本的条件成熟候选，但不得进入本阶段 implementation plan 的实施任务、验收硬门、RUN_SELECTION_MANIFEST 角色选择、ACCEPTANCE_INPUTS 必要输入或 acceptance bundle 必要产物。

### P2-1：Frozen MCP snapshot 和只读外部工具

Claude Code 参考实现中 MCP 涉及连接、认证、工具 schema、资源列表、输出截断、二进制内容和权限。RepoHarness V4 如果纳入 MCP，应该从本地 fixture 和冻结快照开始。

后续候选范围，本阶段不完成：

- 本地 fake / fixture MCP server。
- frozen MCP tool snapshot。
- tool schema、resource listing、server identity、permission rules 冻结。
- 大输出写 ArtifactRef。
- MCP raw blob 和 hidden metadata 不进入训练目标。

本阶段不完成的机器产物：

- `mcp_policy_snapshot.json`
- `mcp_tool_snapshot.json`
- `mcp_output_artifact_report.json`

边界：

- 不做 OAuth。
- 不做多传输协议。
- 不做远程 MCP marketplace。
- 不允许运行中动态新增工具。

### P2-2：代码检索专项评测

后续候选范围，本阶段不完成：

- file localization。
- grep / rg trace。
- symbol search。
- retrieval trace。
- retrieval quality report。
- 文件定位效率指标。

本阶段不完成的机器产物：

- `code_retrieval_task_manifest.json`
- `retrieval_trace.jsonl`
- `retrieval_quality_report.json`
- `file_localization_metrics.json`

边界：

- 不训练 retrieval agent。
- 不建设大型向量数据库服务。
- 不用检索评测替代 final verifier。

### P2-3：受控只读子代理和 sidechain transcript

Claude Code 参考实现里的 subagent、background task、sidechain transcript、worktree isolation 和 task notification 是完整产品能力。RepoHarness V4 只能选择最小、只读、诊断优先的形态。

后续候选范围，本阶段不完成：

- 主 agent 调用只读 reviewer 子代理。
- verifier-planning 子代理。
- 子代理独立 transcript。
- 子代理独立工具池和权限 snapshot。
- 父子可见性边界。
- sidechain 默认 diagnostic export，不进入主训练 target。

本阶段不完成的机器产物：

- `subagent_policy_snapshot.json`
- `sidechain_transcript_manifest.json`
- `delegation_graph.json`
- `subagent_visibility_audit.json`

边界：

- 不做 agent swarm。
- 不做 parallel reinforcement learning。
- 不做自动 worktree 分叉。
- 不做后台多智能体系统。

### P2-4：prompt injection / instruction conflict diagnostic tasks

后续候选范围，本阶段不完成：

- 小规模固定 fixture 的 prompt injection diagnostic-only task。
- conflicting instruction diagnostic-only task。
- hidden/evaluator-only instruction leakage negative tests。
- honesty、instruction hierarchy、tool safety 和 refusal correctness 的诊断报告。

本阶段不完成的机器产物：

- `prompt_injection_task_manifest.json`
- `instruction_conflict_diagnostic_report.json`
- `prompt_injection_visibility_audit.json`

边界：

- 不把 prompt injection 诊断任务放入 V4 最小完成硬门。
- 不把 LLM judge 诊断结果替代 final verifier。
- 不把恶意 fixture、hidden instruction 或 evaluator-only trap 暴露给正式训练 payload。

## 7. V4 明确非目标

V4 必须明确不做以下事项：

1. 不复现完整 SWE-Bench Lite 或 SWE-Bench Verified 榜单。
2. 不声称生产级安全沙箱。
3. 不实现分布式强化学习 rollout 集群。
4. 不训练强化学习算法。
5. 不训练 reward model。
6. 不复刻完整 Claude Code / Codex 产品。
7. 不实现完整插件市场或远程 MCP 生态。
8. 不默认跨实验长期用户记忆。
9. 不做不可人工审计的大规模自动任务生成。
10. 不用 LLM judge 或 reward audit 替代 final verifier。
11. 不声称 V4 已经训练出 coding agent。

## 8. V4 验收原则

V4 acceptance 应该延续 V3 的显式输入、不可变 bundle 和 inspect-first 原则。建议遵守：

1. 以 V3 当前 acceptance 为前置门槛。V4 验收前仍应能通过 V3 acceptance report 和 acceptance bundle 的 inspect 检查，避免在 V4 中破坏 V3 基线。
2. 每个 P0 能力必须有机器产物、schema、inspect 命令和 negative test。
3. 本阶段明确纳入的 P1-2 和 P1-4 必须随 P0 一起定义 schema、inspect、negative tests、acceptance inputs 或 acceptance bundle 绑定方式；不能以“增强项”为由跳过验收口径。
4. 在开启本阶段未纳入的 P1/P2 实施之前，必须先通过 P0 stability gate：V3 回归通过、P0 schema / inspect / negative tests 完成、P0 acceptance dry run 通过、selected run refs / role refs 已进入 RUN_SELECTION_MANIFEST，P0 机器产物已通过 ACCEPTANCE_INPUTS 或 acceptance bundle 绑定。
5. RUN_SELECTION_MANIFEST 和 ACCEPTANCE_INPUTS 继续作为最终验收显式输入，不允许验收脚本自动选择“最新看起来成功”的 run。
6. command log lineage 必须能追溯到触发命令、队列 manifest、worker log、retry policy、run selection query 和导出 audit。
7. evaluator-only evidence 隔离、visibility policy、污染 denylist、PreparedMessages 与 export observation 绑定必须继续作为硬门。
8. final verifier 仍然是 accepted / rejected / inconclusive 的主事实来源。reward audit、patch quality metrics、LLM judge 风险检查只能作为诊断或过滤辅助。
9. provider fallback、mock provider、credential-gated real provider 必须在报告中显式区分，不能把 fallback 成功写成 primary 成功。
10. Docker 事实必须继续被记录，但文档和报告不能把 Docker backend 宣称为生产级安全沙箱。
11. V4 导出应继续继承 V2/V3 export 契约，新增 trajectory packing、sample tiers 和 failure dataset 也必须保留原始 trajectory ref。
12. 对任务构造和数据导出，宁可把不稳定样本放入 diagnostic-only 或 quarantined，也不能为了数量把不可审计样本放入 trainable payload。

## 9. V4 关键机器产物清单

P0-1 单机 rollout 和实验编排：

- `rollout_queue_manifest.json`
- `worker_run_log.jsonl`
- `lease_state_report.json`
- `batch_resume_report.json`
- `retry_policy_report.json`
- `resource_usage_report.json`
- `run_selection_query_report.json`

P0-2 任务构造和固定任务集扩展：

- `pr_task_construction_manifest.json`
- `source_archive_manifest.json`
- `task_validity_report.json`
- `baseline_verifier_report.json`
- `source_materialization_report.json`
- `flaky_detection_report.json`
- `generated_task_definition.jsonl`

P0-3 导出质量、trajectory packing 和 failure / reward 审计：

- `trajectory_quality_manifest.json`
- `sample_tier_manifest.json`
- `failure_dataset.jsonl`
- `packing_manifest.json`
- `reward_audit_report.json`
- `reward_hacking_risk_audit_report.json`
- `patch_quality_report.json`

本阶段纳入的 P1-2 轻量 audit-only 产物：

- `hook_policy_snapshot.json`
- `hook_audit_report.json`
- `tool_lifecycle_trace.jsonl`
- `permission_decision_trace.jsonl`
- `permission_policy_dataset_manifest.json`
- `tool_contract_v4_snapshot.json`

本阶段纳入的 P1-4 轻量卡片产物：

- `dataset_card.md`
- `dataset_card.json`
- `run_card.json`
- `export_card.json`
- `provenance_summary.json`
- `contamination_scan_summary.json`
- `repro_command_index.json`

本阶段只保留元数据、不生成完整报告的 P1-1 字段：

- `provider_id`
- `provider_mode`
- `model_id`
- `scaffold_id`
- `budget_policy_id`
- `fallback_policy_id`
- `token_usage`
- `provider_error_category`
- `tool_policy_id`
- `verifier_id`
- `environment_id`

本阶段不完成的 P1 / P2 产物：

- `provider_eval_matrix_report.json`
- `provider_compare_scope.json`
- `scaffold_comparison_report.json`
- `scaffold_quality_metrics.json`
- `per_scaffold_export_quality.jsonl`
- `context_strategy_registry.json`
- `context_strategy_comparison_report.json`
- `context_replacement_trace.jsonl`
- `project_context_snapshot.json`
- `session_continuation_manifest.json`

- `mcp_policy_snapshot.json`
- `mcp_tool_snapshot.json`
- `mcp_output_artifact_report.json`
- `code_retrieval_task_manifest.json`
- `retrieval_trace.jsonl`
- `retrieval_quality_report.json`
- `file_localization_metrics.json`
- `subagent_policy_snapshot.json`
- `sidechain_transcript_manifest.json`
- `delegation_graph.json`
- `subagent_visibility_audit.json`
- `prompt_injection_task_manifest.json`
- `instruction_conflict_diagnostic_report.json`
- `prompt_injection_visibility_audit.json`

## 10. V4 风险和降级路径

### 风险：任务扩展数量压倒任务质量

V4 的任务规模目标是约 10 个 accepted / auditable tasks，而不是越多越好。如果某些 PR / issue task 无法稳定复现 baseline verifier、source materialization 或 flaky 检测，应降级为 diagnostic-only、quarantined 或 rejected，不应放入 trainable payload。

### 风险：rollout 编排膨胀成集群调度

P0-1 只做单机队列、租约、重试、资源锁和可恢复批处理。若 implementation plan 开始引入 Kubernetes、云端调度、多租户资源隔离、训练推理服务拆分，应移出 V4。

### 风险：provider 真实调用成本和凭证不稳定

真实 provider 条件必须 credential-gated，并在报告中明确 `accepted_with_credentials`、mock、fallback 和 skipped。结构性验收可以使用 mock 或 replay，但核心 V4 accepted 轨迹需要明确哪些是真实 provider 条件，不能混淆。

本阶段不做完整 provider / scaffold / budget 评测矩阵，因此不能把 P0 轨迹中的 provider、scaffold、budget 元数据解读为 provider 对比结论、scaffold 排名或预算策略优劣结论。

### 风险：Docker 平台差异造成任务不稳定

Docker backend 必须继续记录平台、镜像、资源、命令和 verifier facts。对 Apple Silicon、依赖安装慢、测试耗时长或 flaky 的任务，应通过 baseline verifier report、flaky detection report 和 environment stability score 降级处理。

### 风险：`no_trainable_preference_pair` 被误当成已解决

V4 必须显式处理这个 V3 残余项。优先路径是构造足够可比较的 accepted / failed / partial 轨迹，产生可训练 preference pair。降级路径是保留 warning，但生成更清楚的 blocked pair report，说明缺失原因、样本分布和后续修复入口。

### 风险：reward audit 或 LLM judge 被误用为成功判定

reward audit、reward hacking risk audit、patch quality metrics 和 test overfitting audit 都只能做诊断、过滤和风险提示。它们不能替代 final verifier，也不能把 final verifier 未接受的样本提升为 accepted。

### 风险：Claude Code 参考实现诱导范围膨胀

Claude Code 的 MCP、hook、slash command、skill、session memory、subagent、background task 是真实产品能力。RepoHarness V4 本阶段只吸收其中对训练轨迹有用且已经明确纳入的事实形态，例如 policy snapshot、permission trace、tool lifecycle trace、audit-only hook facts、artifact reference 和导出卡片。context replacement trace、MCP snapshot、sidechain transcript manifest 等仍属于本阶段不完成的后续候选。完整产品复刻必须留在非目标之外。

本阶段纳入的 P1-2 只允许实现 audit-only 的权限、工具生命周期和 hook 审计事实。用户可配置 hook、插件式 hook、技能 frontmatter hook、stop hook、session hook、文件变化 hook、subagent hook、远程会话 hook、以及会改写工具输入、工具结果、模型历史或 final verifier 主事实的 hook，都明确不属于本阶段。

## 11. 后续 implementation plan 编写提示

后续 V4 implementation plan 应该从本范围文档出发，按可验收产物组织阶段，而不是按产品功能菜单组织阶段。建议至少覆盖：

1. V4 schema 和 inspect 命令阶段：定义 P0 机器产物，以及本阶段纳入的 P1-2 / P1-4 机器产物 schema、negative tests 和 acceptance report 扩展。
2. V4 SWE / PR task feasibility and freeze preparation 阶段：执行 `docs/v4/swe-task-feasibility-experiment-plan.md` 定义的候选扫描、Docker image prewarm、baseline verifier probe、flaky probe、patch feasibility probe 和 freeze readiness decision，产出 V4 task selection manifest。
3. V4 task source freeze / construction preflight 阶段：基于 feasibility 结果冻结 source archive、任务 manifest、baseline verifier、flaky evidence、source materialization repeat check 和 evaluator-only evidence 分区，再允许进入批量 rollout。
4. rollout queue 和 worker 阶段：实现单机 queue、lease、retry、resource usage、command lineage 和 batch resume，并在工具执行链路上生成 P1-2 的 `permission_decision_trace.jsonl`、`tool_lifecycle_trace.jsonl` 和 audit-only hook facts。
5. task construction 阶段：实现 PR / issue task construction manifest、fixed archive、baseline verifier、flaky detection、source materialization repeat check 和 task quarantine。
6. export quality 阶段：实现 sample tiers、failure dataset、trajectory packing、preference pair trainability、patch quality 和 reward hacking risk audit，并生成 P1-4 的 dataset card、run card、export card、provenance summary、contamination scan summary 和 repro command index。
7. integration acceptance 阶段：用显式 RUN_SELECTION_MANIFEST 绑定 V4 selected run refs / role refs，用 ACCEPTANCE_INPUTS 或 acceptance bundle 绑定 P0 机器产物、本阶段纳入的 P1-2 / P1-4 机器产物、V2/V3 回归和 export audit。
8. 本阶段不完成项确认阶段：implementation plan 必须明确完整 provider / scaffold / budget matrix、context strategy comparison、session continuation、MCP snapshot、retrieval task、prompt injection diagnostic task 和只读 subagent 都不进入本阶段实施和验收；P1-1 只保留 provider、scaffold、budget、fallback、token usage 和 provider error 元数据。

implementation plan 还应明确：

- 不修改 V3 acceptance 产物。
- 不默认联网构造正式任务。
- 不把浮动默认分支作为正式任务来源。
- 不把 evaluator-only evidence、reward-only evidence、gold patch、hidden test selector、provider raw response 放进训练 payload。
- 不把 official harness report、official report、Authorization marker 或 provider credential marker 放进模型可见上下文或正式训练 payload。
- 不把 Docker backend 宣称为生产级安全沙箱。
- 不把 V4 写成完整 Claude Code / Codex 产品复刻。
