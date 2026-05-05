# RepoHarness V5 Scope Review

## 1. 审查背景

本轮审查对象是 `docs/v5/scope-and-roadmap.md`。V5 的目标是补齐最终简历和大厂面试所需结果，而不是继续扩大成完整 SWE-Bench Lite、SWE-Bench Verified、公开 leaderboard、分布式强化学习平台或完整产品复刻。

审查方式：

- 主 agent 编写 V5 scope 初稿。
- 三个只读 subagent 分别从面试吸引力、工程可行性、项目状态一致性角度审查。
- 主 agent 根据 P1 / P2 findings 修订 scope。

## 2. Subagent 审查结论摘要

### 2.1 面试吸引力审查

结论：V5 主方向正确，已经从“实现了一个 Harness”推进到“能被面试官审查的结果包”。

主要发现：

- 初稿的 `multi-provider agent runs` 表述需要硬证据支撑。如果最终只有一个真实 provider 运行，其余 provider 都是 structured skip，不能使用 multi-provider 强表述。
- 12 到 20 个任务的真实性和多样性需要更具体的报告，否则容易被质疑只是数量更多的 fixture。
- Demo card 需要补 canonical live demo path，面试中应该能沿着一个任务从 task freeze、agent run、trajectory、final verifier、export sample 到 acceptance binding 讲完整闭环。
- Matrix cell 应补 patch quality、test overfitting risk、regression summary 和 review notes。
- Failure dataset 应补 failure taxonomy。
- Demo artifact 应明确 public-safe / redacted 展示边界。

处理结果：

- 新增 `core_acceptance` 和 `resume_ready_acceptance` 两层验收。
- 新增 `v5_task_diversity_report.json`。
- 新增 `v5_canonical_demo_walkthrough.md`。
- 新增 `v5_public_demo_bundle_manifest.json`。
- Matrix cell 补入 patch quality、test overfitting risk、regression summary、changed files 和 review notes。
- 新增 `v5_failure_taxonomy_report.json`。
- 强制 result summary 分列 real provider trainable records、mock / replay records、diagnostic records、blocked records 和 synthetic-safe stress records。

### 2.2 工程可行性审查

结论：V5 方向合理，但初稿 P0 范围过大，真实 provider 矩阵、真实 preference pair、任务数量增长和 export stress test 的硬门关系需要收缩和澄清。

主要发现：

- 初稿把 evidence integrity、12 到 20 个任务、三 provider 矩阵、真实 preference pair、1,000 条 export stress、demo artifacts 和 final acceptance 全部放入 P0，范围偏大。
- 真实 provider 凭证缺失时是否仍可通过不够清晰。
- Preference pair 被硬放入 P0，可能诱导实现 agent 凑样本。
- V4 基线状态和仓库现有说明存在冲突，Stage 0 不能只把它归类为普通文档漂移。
- Acceptance report 与 post-acceptance docs 的时间顺序需要明确，避免循环引用。
- 任务数量增长缺少 task inventory / reuse policy。
- Export stress test 在正文是可选，但 Stage 4 和 final acceptance 变成硬门。

处理结果：

- 将 V5 分成 `core_acceptance` 和 `resume_ready_acceptance`。
- P0 provider matrix 收缩为最小 comparison proof：至少 1 个真实 provider family 有实际运行；multi-provider 强表述需要 resume-ready gate。
- 明确至少 2 个真实 provider family 各有至少 2 条真实 agent run records，才能使用 `multi-provider agent runs`。
- Preference pair 改为 resume-ready 声明门；如果没有真实可比较 pair，必须生成 blocked report，并禁止使用 preference export 强表述。
- Stage 0 新增 `v4_review_findings_closure_report.json` 和 `v5_documentation_sync_report.json`。
- Evidence integrity 明确 acceptance report 只能引用 acceptance inputs；post-acceptance docs 只能进入 bundle documentation section。
- Stage 2 新增 task inventory / reuse policy。
- Export stress test 降级为 P1-5，不再是 V5 core final acceptance 必要输入。

### 2.3 项目状态一致性审查

结论：V5 非目标边界整体一致。审查当时，V4 最新基线与 README、AGENTS、Reading Guide、项目定位文档和 V4 final acceptance 文档之间存在状态冲突；该冲突已在 2026-05-05 的 V4 文档同步中收口。

主要发现：

- V5 scope 使用 `e0da89c` 和 `runs/v4-final-rerun-20260504T194758Z/` 作为 V4 closure baseline，但审查当时 README、AGENTS、`docs/00`、`docs/01`、`docs/12` 还没有统一到修复后最终验收状态。2026-05-05 文档同步后，这些入口已经改为修复后最终验收状态。
- 审查当时 `docs/v4/final-acceptance.md` 仍指向旧的 `runs/v4-final-rerun-20260504T162105Z/`。2026-05-05 文档同步后，该文档已经指向 `runs/v4-final-rerun-20260504T194758Z/`，并补充了文档同步 bundle。
- V5 预检缺少 `inspect-v4-inputs`。
- 项目入口文档还没有把 `docs/v5/` 纳入正式阅读路径。

处理结果：

- Stage 0 documentation sync report 覆盖 README、AGENTS、`docs/00-reading-guide.md`、`docs/01-project-positioning-and-requirements.md`、`docs/12-resume-narrative-and-demo-artifacts.md` 和 `docs/v4/final-acceptance.md`。
- V5 基线命令和 Stage 6 命令补入 `inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete`。
- V5 final acceptance 必要输入补入 V4 latest acceptance inputs、V4 review findings closure report、V5 documentation sync report。
- Scope 明确旧 V4 path 只能作为历史记录，不能作为 V5 baseline。

## 3. 第一轮修订后的审查判断

修订后的 V5 scope 更适合作为实施输入：

- 不再把所有展示愿望都塞进 P0。
- 不再把“能通过 core acceptance”和“能写强简历表述”混在一起。
- 对真实 provider、preference pair、export stress test 的证据要求更清楚。
- 对 V4 文档漂移和最新 acceptance baseline 的处理更明确。
- 增加了 canonical demo walkthrough 和 public-safe demo bundle，更贴近面试展示需求。

第一轮修订后，当时没有剩余 P1 阻塞项。后续第二轮和第三轮外部复核继续提出了更细的 final acceptance 绑定、声明门和结果指标问题，处理记录见后续章节。

## 4. 第二轮外部复核处理记录

第二轮外部复核进一步确认 V5 方向适合大模型团队面试，但指出 scope 还需要从“审计链路完整”推进到“验收时序无循环、声明门不会误用、结果数字能一眼看懂、现场 demo 能讲出故事”。

### 4.1 P1 处理

1. Evidence integrity gate 的时间顺序循环风险。

处理结果：

- 将 evidence integrity 拆成三层：`pre_acceptance_evidence_integrity`、`acceptance_report_reference_integrity`、`acceptance_bundle_command_lineage_integrity`。
- 明确 pre-acceptance evidence integrity 只检查 acceptance inputs 之前已经存在的证据。
- 明确 acceptance report 引用检查由 `inspect-v5-acceptance` 执行。
- 明确 acceptance bundle command lineage 检查由 `inspect-acceptance-bundle --assert-immutable` 执行。

2. 成功指标缺少面试官一眼能看懂的量化结果硬门。

处理结果：

- `v5_result_summary_table.json` 增加 accepted rate、pass-to-pass regression rate、failure type distribution、failure owner distribution、token usage、wall time、cost proxy、provider / scaffold / budget comparison conclusion 和样本分区统计。
- V5 成功指标明确要求 result summary 分列 real provider trainable records、mock / replay records、diagnostic records、blocked records 和 synthetic-safe stress records。

3. Provider / scaffold / budget comparison 的最小可比矩阵不够硬。

处理结果：

- 增加 `comparison_axis`、`controlled_variables`、`compared_cells` 和 `comparison_validity`。
- Provider 比较时必须固定 scaffold 和 budget；scaffold 比较时必须固定 provider 和 budget；budget 比较时必须固定 provider 和 scaffold。
- `resume_ready_acceptance` 增加硬门：至少覆盖 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget` 的受控成对比较。

4. 任务运行数量门槛前后文没有完全闭合。

处理结果：

- Stage 3 和成功指标都补上至少 6 个任务产生真实 agent run evidence、至少 4 个任务进入 comparison proof。
- 成功指标拆分为 `core_acceptance`、`resume_ready_acceptance` 和 stretch target。

### 4.2 P2 处理

1. 强简历表述需要拆成多条模板。

处理结果：

- 第 11 节增加三条模板：`core_acceptance` 可用表述、`resume_ready_acceptance` 可用表述、`stress_test_completed` 后才可用表述。
- 明确只通过 `core_acceptance` 时不能使用 `multi-provider agent runs`、`preference export completed` 或 `resumable export stress tests`。

2. Stage 0 文档同步门需要扩展检查项。

处理结果：

- `v5_documentation_sync_report.json` 增加对 `reference/claude-code-typescript-src/AGENTS.md` 实际文件名和引用路径的检查，避免继续写成不准确的 `AGENT.md`。

3. 增加轻量 permission / network policy / risky command audit。

处理结果：

- 新增 `v5_permission_network_risk_audit_report.json`。
- 要求记录 network policy、approval boundary、风险命令命中次数、风险命令是否进入模型可见内容、风险命令是否影响 trainable export。
- 风险命令至少覆盖 `curl`、`wget`、`git clone`、`git remote add`、修改远程地址、访问未固定网络资源和绕过 verifier 的 shell 模式。

4. 增加 reward source taxonomy 和 failure owner。

处理结果：

- 新增 `reward_source_type`、`v5_reward_source_taxonomy_report.json`。
- Reward source 至少区分 unit test、rule-based verifier、rubric、LLM judge audit-only 和 mixed。
- Failure taxonomy 增加 `failure_owner`，至少包含 model behavior、environment unstable、provider error、verifier / config issue、permission / policy 和 unknown。

5. 增加 Claude Code 架构不变量对照表。

处理结果：

- 新增 `v5_claude_code_invariant_mapping.json`。
- 要求以 `Claude Code 不变量 -> RepoHarness 落地证据 -> 明确不实现的边界` 形式覆盖 query loop、tool contract、tool result pairing、permission boundary、hook audit、MCP disabled / frozen facts、context compaction、transcript diagnostics 和 artifact refs。

6. Provider 成本和运行预算降级路径需要机器可验收。

处理结果：

- 新增 `v5_provider_cost_budget_report.json`。
- P0 provider gate 记录 `max_real_provider_calls`、`max_cost_usd`、`cost_proxy_formula`、`actual_real_provider_calls`、`actual_cost_proxy_usd`、`cost_limited_structured_skip` 和 `budget_exhausted_before_run`。

### 4.3 P3 处理

Canonical demo walkthrough 已补充 5 分钟任务剧情要求，并要求至少包含一个现场负例 inspect，例如 sha256 漂移、未绑定 final verifier evidence 或 evaluator-only evidence 泄漏被拒绝。`single_shot_patch` 仍只作为可选 baseline，不扩大 P0 范围。

## 5. 第三轮外部复核处理记录

第三轮外部复核认为第二轮修订整体成立，但指出 final acceptance 绑定和声明门还需要进一步可执行化。

### 5.1 P1 处理

1. Final acceptance 必要输入仍有时间顺序循环风险。

处理结果：

- 第 9 节拆成三组：`Acceptance inputs 必须显式绑定`、`Post-report inspect outputs`、`Bundle final outputs`。
- `v5_acceptance_report_reference_integrity_report.json` 和 bundle command lineage report 不再放入 acceptance inputs，而是分别进入 post-report inspect outputs 和 bundle final outputs。

2. `inspect-v5-acceptance --assert-complete` 没有说明检查 core 还是 resume-ready。

处理结果：

- Stage 6 改为显式运行 `inspect-v5-acceptance --assert-core-complete` 和 `inspect-v5-acceptance --assert-resume-ready`。
- 文档要求 acceptance report 包含 `core_acceptance.status`、`resume_ready_acceptance.status`、`allowed_claims`、`blocked_claims` 和 `claim_gate_report_ref`。
- 如果保留 `--assert-complete`，必须等价于 `--assert-resume-ready`，不能只检查 core acceptance。

3. Final acceptance 必要输入没有显式列出简历成果核心 artifact。

处理结果：

- Acceptance inputs 补入 `v5_resume_artifact_index.json`、`v5_repro_command_index.json`、`v5_result_summary_table.json` 和 `v5_demo_transcript_index.json`。

### 5.2 P2 处理

1. Scaffold / budget comparison 缺少最小成对覆盖门槛。

处理结果：

- `resume_ready_acceptance` 增加 scaffold 比较门：至少 2 个任务，在同一真实 provider、同一 budget、同一 source tree、同一 verifier plan、同一 tool policy 和同一 context policy 下比较 `simple_react` 与 `planner_coder_verifier`。
- `resume_ready_acceptance` 增加 budget 比较门：至少 2 个任务，在同一真实 provider、同一 scaffold、同一 source tree、同一 verifier plan、同一 tool policy 和同一 context policy 下比较 `standard` 与 `constrained`。

2. Result summary 指标缺少 denominator 定义。

处理结果：

- `v5_result_summary_table.json` 增加分母定义：真实 provider accepted rate、mock / replay accepted rate、structured skip、credential missing skip、cost-limited skip、pass-to-pass regression rate、token usage、wall time 和 cost proxy 都必须分区统计。

3. 成功指标缺少 provider raw request / response 泄漏为 0 的硬门。

处理结果：

- `core_acceptance` 成功指标增加：0 个 provider raw request / provider raw response 进入 transcript model-visible content、trainable payload、public-safe demo bundle 或 final acceptance docs。

4. Scope review 第 3 节标题和措辞可能让读者误解。

处理结果：

- 第 3 节改名为“第一轮修订后的审查判断”，并说明第二轮、第三轮外部复核继续提出更细问题，处理记录见后续章节。

### 5.3 P3 处理

第 5 节中旧的“建议最终简历表述”已经删除，避免和第 11 节三条模板重复，降低误复制风险。

## 6. 第四轮外部复核处理记录

第四轮外部复核确认第三轮关键问题已经闭合，只指出执行链路中还需要补三处细节。

### 6.1 P2 处理

1. Stage 6 缺少显式构建 V5 acceptance bundle 的命令。

处理结果：

- Stage 6 退出门在两次 `inspect-v5-acceptance` 之后、`inspect-acceptance-bundle` 之前补入 `build-v5-acceptance-bundle`。
- 命令显式接收当前 V5 acceptance report、post-report inspect output、final command log、post-acceptance documentation refs 和输出 bundle manifest。
- 文档明确 builder 不得扫描 latest acceptance directory，也不得覆盖已经存在的 bundle。

2. 两次 acceptance inspect 只对应了一个 command log entry。

处理结果：

- Post-report inspect outputs 将单个 `inspect_v5_acceptance_command_log_entry` 拆成 `inspect_v5_acceptance_core_command_log_entry` 和 `inspect_v5_acceptance_resume_ready_command_log_entry`。
- 两次 inspect 调用都必须进入 final command log 或 acceptance bundle inspect outputs section。

### 6.2 P3 处理

总目标中的强表述已经标注为 `resume_ready_acceptance` 专用目标表述，不能在只通过 `core_acceptance` 时单独复制使用。
