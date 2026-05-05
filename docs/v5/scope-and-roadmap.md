# RepoHarness V5 Scope And Roadmap

## 0. 文档使用方式

这份文档定义 RepoHarness V5 的范围和路线图。V5 的目标不是重新发明一个新的功能大版本，而是在 V4 已经完成的可执行、可审计、可导出闭环之上，补齐可以写进简历、可以现场展示、可以经受大厂面试追问的最终结果。

V5 的设计重点是结果可信度和展示价值：

- 让任务集更像真实软件工程评测，而不是玩具 fixture。
- 让 provider、scaffold 和 budget 的对比足够公平、可复现、可审计。
- 让训练导出样本能够清楚说明为什么可以训练、为什么只能诊断、为什么必须阻断。
- 让每个重要结论都能追溯到显式路径、sha256、inspect 命令和 acceptance bundle。

V5 不以完整 SWE-Bench Lite、SWE-Bench Verified 或公开榜单可比结果作为主目标。完整 benchmark 复现会把项目重心从 RepoHarness 自身的训练数据闭环转移到大规模任务维护、依赖稳定性和榜单运行成本上，容易稀释当前项目最有价值的工程主线。V5 可以支持 SWE-Bench-like / PR-issue mixed showcase subset，但必须继续明确：它是可审计展示子集，不是公开 leaderboard。

## 1. V5 背景和 V4 基线

RepoHarness 的核心数据流保持不变：

```text
task -> executable workspace -> tools -> agent loop -> trajectory -> verifier -> reward/eval/export
```

V1 到 V4 已经把这条链路从 micro-repo 最小闭环推进到真实或半真实仓库任务、Docker-based executable repository environment、固定 SWE-Bench-like 子集、rollout orchestration、tool lifecycle audit、agent run integration、export quality audit 和 acceptance bundle。

V5 的正式实施基线建议使用当前 V4 修复收口后的 commit：

```text
e0da89c test: refresh V4 acceptance evidence after hardening
```

实施 V5 前必须确认：

```bash
git merge-base --is-ancestor e0da89c HEAD
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable
```

V4 latest acceptance bundle 必须优先使用文档同步后的 bundle：

```text
runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json
runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl
```

原始 `acceptance_bundle_manifest.json` 只保留为历史 bundle，不能作为 V5 的 latest V4 baseline。

如果这些命令失败，V5 不应继续扩大范围。应先修复 V4 基线或记录阻塞报告。

V5 必须继承并保护以下 V4 已实现能力：

1. V4 task source freeze 和 accepted / auditable task gate。
2. Adapter-visible task input 与 evaluator-only evidence 的隔离。
3. 统一污染 denylist、visibility policy 和 RewardMetadata allowlist。
4. Rollout queue、lease、retry、budget control、resource lock、checkpoint state、batch resume 和 run selection query。
5. Permission decision trace、tool lifecycle trace、hook audit-only facts、MCP disabled / frozen facts。
6. Agent run integration、RunSpec metadata、PreparedMessages binding、final verifier boundary report 和 trajectory store 字段级检查。
7. Export quality、sample tier、failure dataset、reward audit、reward hacking risk audit、patch quality、test overfitting risk audit 和 preference pair trainability。
8. Dataset card、run card、export card、provenance summary、contamination scan summary 和 repro command index。
9. V4 final acceptance report 和 acceptance bundle 的显式输入、不可变绑定和 command log lineage。

## 2. V5 核心判断

V4 已经足够支撑一个有含金量的工程研究型简历项目。它的强项不是模型排行榜，而是训练友好的软件工程智能体 Harness：

- 能把真实或半真实仓库任务变成可执行环境。
- 能记录工具调用、权限判断、轨迹、事件和 artifacts。
- 能用 final verifier 产生评测结论和 reward metadata。
- 能把轨迹导出为 SFT、reinforcement learning rollout、preference pair 和 failure dataset。
- 能通过 inspect 命令和 acceptance bundle 证明证据没有漂移。

V5 的中心判断是：现在最值得补的不是更多产品功能，而是一个面试官可以直接理解的结果包。

这个结果包必须回答五个问题：

1. 你的任务是不是足够真实，还是只有玩具 fixture？
2. 你的 agent run 是不是可复现，还是只展示一次成功样例？
3. 你的不同 provider、scaffold、budget 对比是不是公平，还是混合了不同任务和不同验证口径？
4. 你的训练样本是不是真的可训练，还是把 reward、hidden verifier 或 evaluator-only evidence 泄漏进了模型可见文本？
5. 你的验收是不是可审计，还是只是终端里口头说通过？

因此，V5 的一句话定位是：

> V5 将 RepoHarness 从 V4 的可审计实现闭环升级为面试级软件工程智能体评测和训练数据展示包，重点补齐 evidence integrity、SWE-Bench-like / PR-issue mixed task subset、薄 provider / scaffold / budget matrix、高质量训练导出包和可复现 demo artifacts。

## 3. V5 总目标

V5 总目标是交付一个可写进简历的最终结果。下面这句是 `resume_ready_acceptance` 专用目标表述，不能在只通过 `core_acceptance` 时单独复制使用：

> Built an interview-grade software engineering agent evaluation and training-data harness with SWE-Bench-like task freezing, Docker-based repository execution, multi-provider agent runs, scaffold and budget comparison, verifier-aligned reward metadata, contamination-resistant export audit, resumable rollout orchestration, and immutable acceptance bundles.

这句话要求 V5 最终必须有真实证据支撑，不能只停留在文档。

V5 使用两层验收口径，避免为了写出漂亮简历句子而凑证据：

1. `core_acceptance`：证明 V5 的证据完整性、任务冻结、最小真实运行、训练导出和验收 bundle 都成立。这个状态可以说明 RepoHarness V5 的工程闭环完成，但不自动允许使用所有强简历表述。
2. `resume_ready_acceptance`：在 `core_acceptance` 基础上，额外通过多真实 provider、真实可比较 preference pair、share-safe demo bundle 和 canonical demo walkthrough 的声明门。只有这个状态通过后，才能在简历中使用 `multi-provider agent runs`、`preference export`、`interview-grade evaluation pack` 这类强表述。

V5 最小完成定义包含五条 P0 主线，但其中 provider / scaffold / budget 只做最小可比较运行，不把完整多 provider 矩阵作为 P0 硬门：

1. V4 closure synchronization 和 evidence integrity gate。
2. SWE-Bench-like / PR-issue mixed showcase task subset。
3. 最小 provider / scaffold / budget comparison proof 和 provider credential gate。
4. 面向训练的高质量 export result pack。
5. Interview demo card、public-safe artifact pack 和最终 acceptance bundle。

V5 不追求完整 SWE-Bench Lite、SWE-Bench Verified、公开 leaderboard、大规模 RL training、生产级安全沙箱或完整开发者产品复刻。

## 4. V5 与 V4 的差异

V4 的重点是把 V3 的端到端能力扩展为稳定的数据生产和审计流程。V5 的重点是把这些流程整理成可以展示的结果。

具体差异如下：

- V4 证明了 accepted / auditable task gate；V5 要形成 12 到 20 个高质量任务的展示子集。
- V4 保留 provider / scaffold / budget 元数据；V5 要做最小可比较运行，并把多 provider 强表述放入单独的声明门。
- V4 修复了 preference pair trainability 的实现漏洞；V5 要么产生一个真实可比较、可训练的 preference pair，要么生成 blocked report 并禁止使用 preference export 强表述。
- V4 有 export quality inspect；V5 要交付 SFT、RL rollout、preference pair 和 failure dataset 四类可解释样本。
- V4 有 cards；V5 要生成真正可用于简历、面试讲解和项目展示的 interview demo card。
- V4 有 final acceptance；V5 要增加 evidence integrity gate，明确 acceptance report 不得引用未绑定关键证据。

## 5. V5 P0 范围

### P0-0：V4 closure synchronization 和基线冻结

目标是先把 V4 最新通过状态同步到 V5 的正式基线，避免后续实现建立在过期路径或过期结论上。

必须完成：

1. 确认 `e0da89c` 是 V5 开始前的 V4 closure baseline。
2. 确认 V2、V3、V4 最新 acceptance inspect 和 bundle inspect 通过。
3. 把 V5 文档中的 V4 基线路径统一指向 `runs/v4-final-rerun-20260504T194758Z/`。
4. 明确旧的 V4 acceptance 路径只作为历史记录，不能作为 V5 baseline。
5. 生成 `v4_review_findings_closure_report.json`，逐项绑定 V4 修复前复核 finding、修复 commit、重新生成 evidence、inspect 命令和最新 acceptance bundle。
6. 生成 `v5_documentation_sync_report.json`，检查 README、AGENTS、`docs/00-reading-guide.md`、`docs/01-project-positioning-and-requirements.md`、`docs/12-resume-narrative-and-demo-artifacts.md` 和 `docs/v4/final-acceptance.md` 是否仍然把 V4 描述为待修复状态，是否仍把旧的 `runs/v4-final-rerun-20260504T162105Z/` 当作最新 V4 baseline，是否已经把 `docs/v5/scope-and-roadmap.md` 纳入入口文档索引。
7. 如果上述文档存在漂移，Stage 0 必须先用 closure report 证明 V4 修复已经由 evidence 关闭，再修正文档；不能只通过文字覆盖旧结论。

建议机器产物：

- `v5_baseline_check_report.json`
- `v5_v4_closure_binding.json`
- `v4_review_findings_closure_report.json`
- `v5_documentation_sync_report.json`
- `v5_preimplementation_command_log.jsonl`

验收原则：

- `v5_baseline_check_report.json` 必须记录命令、路径、exit code、stdout / stderr sha256、started_at、finished_at 和当前 HEAD。
- V5 baseline 不允许引用已经被后续 V4 修复替代的旧 acceptance report。
- Stage 0 必须明确区分历史 V4 acceptance 目录和最新 V4 closure baseline 目录。

### P0-1：Evidence integrity gate

目标是补齐面试中最容易被追问的证据可信度问题。V5 不能只说 inspect 通过，而要证明所有关键证据都被 acceptance inputs 显式绑定，并且 acceptance report 不能引用未绑定 evidence。

Evidence integrity 必须拆成三层，避免 acceptance report、acceptance bundle 和 evidence integrity report 之间形成时间顺序循环：

1. `pre_acceptance_evidence_integrity`：在构建 V5 acceptance inputs 之前运行，只检查 task、provider comparison、trajectory、final verifier boundary、export、cards、documentation sync、pre-test evidence 和 pre-acceptance command logs 等已经存在的输入证据。
2. `acceptance_report_reference_integrity`：由 `inspect-v5-acceptance` 执行，检查 V5 acceptance report 中的关键 evidence ref 是否全部来自 V5 acceptance inputs，不能由 pre-acceptance evidence integrity report 预先检查尚未生成的 acceptance report。
3. `acceptance_bundle_command_lineage_integrity`：由 `inspect-acceptance-bundle --assert-immutable` 执行，检查 acceptance bundle、final command log、`inspect-v5-acceptance`、`build-v5-acceptance-bundle` 和 `inspect-acceptance-bundle` 的 argv / input_refs / output_refs 是否指向当前 report 和当前 bundle。

必须完成：

1. 定义 `V5EvidenceRef`，包含 path、sha256、size_bytes、kind、purpose、visibility、producer_command、producer_stage 和 inspect_command。
2. 定义 `V5CriticalEvidenceClass`，至少覆盖 task source、baseline verifier、final verifier boundary、rollout queue、agent run trajectory、export quality、provider comparison proof、scaffold comparison proof、preference pair 或 blocked pair、cards、pre-acceptance command log、final acceptance report 和 acceptance bundle。
3. 实现 `v5_pre_acceptance_evidence_integrity_report.json`，递归检查所有 pre-acceptance 关键 evidence ref 是否存在、sha256 是否匹配、是否准备进入 acceptance inputs。
4. `inspect-v5-acceptance` 必须执行 report 引用检查：acceptance report 中所有关键 evidence ref 都必须属于 acceptance inputs。Post-acceptance 文档只能进入 acceptance bundle 的 documentation section，不能被 acceptance report 用作完成证据。
5. `inspect-acceptance-bundle --assert-immutable` 必须执行 bundle command lineage 检查：acceptance bundle 递归绑定 final command log，并验证 final inspect / build bundle / inspect bundle 命令的 argv 和 input_refs 指向当前 report / bundle。
6. 将 trainable payload、diagnostic-only payload、audit-only metadata、evaluator-only evidence 分区纳入 evidence integrity gate。
7. 明确 evidence 生成时间顺序：pre-acceptance evidence 先生成并进入 acceptance inputs，acceptance report 再生成，post-acceptance docs 最后生成并只由 bundle 绑定。

建议机器产物：

- `v5_pre_acceptance_evidence_integrity_report.json`
- `v5_acceptance_report_reference_integrity_report.json`
- `v5_acceptance_bundle_command_lineage_report.json`
- `v5_critical_evidence_manifest.json`
- `v5_unbound_evidence_negative_case_report.json`
- `v5_acceptance_lineage_report.json`

必须实现的 inspect 命令：

```bash
repo-harness inspect-v5-evidence-integrity V5_PRE_ACCEPTANCE_EVIDENCE_INTEGRITY_REPORT --assert-complete
```

负例必须覆盖：

- acceptance report 引用 acceptance inputs 之外的 final verifier evidence。
- command log 中 `inspect-v5-acceptance` 指向旧 report。
- evidence ref sha256 被更新但 acceptance inputs 未更新。
- post-acceptance doc 被错误放入 acceptance report 输入。
- trainable export record 引用没有 final verifier boundary 支撑的 outcome。

### P0-2：SWE-Bench-like / PR-issue mixed showcase task subset

目标是形成足够真实、足够稳定、足够可审计的任务展示集。V5 不做完整 SWE-Bench Lite 或 SWE-Bench Verified，但要让任务集足以说明 RepoHarness 能服务真实软件工程智能体训练和评测。

建议规模：

- 12 到 20 个 accepted / auditable task definitions。
- 至少 8 个来自 V4 PR / issue task construction flow。
- 至少 3 个来自固定 SWE-Bench-like 锚点。
- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入最小 provider / scaffold / budget comparison proof。

任务来源和复用策略：

- V4 已冻结任务可以计入 V5 数量，但必须重新通过 V5 task inventory、source materialization、flaky probe、dependency cache、environment stability 和 visibility scan。
- 新增任务必须先进入 `candidate`，通过 feasibility、baseline verifier、license / provenance、source freeze 和污染扫描后，才能进入 accepted / auditable。
- 如果新增任务失败，不能用重复复制同一 fixture 或降低 verifier 门槛来补数量；必须降级为 diagnostic-only、quarantined 或 rejected，并在 task inventory 中说明。
- 任务数量的目标是证明覆盖面，而不是追求榜单规模。V5 core acceptance 的下限是 12 个 accepted / auditable task definitions；20 个只是 stretch target。

每个 accepted / auditable task 必须包含：

- `task_id`
- `task_family`
- `source_kind`
- `repo_url_or_archive_id`
- `base_commit`
- `source_archive_sha256`
- `source_tree_hash`
- `task_input_hash`
- `adapter_visible_input_ref`
- `evaluator_only_evidence_ref`
- `baseline_verifier_plan_ref`
- `final_verifier_plan_ref`
- `fail_to_pass_evidence_ref`
- `pass_to_pass_evidence_ref`
- `flaky_probe_report_ref`
- `license_provenance_ref`
- `environment_stability_ref`
- `dependency_cache_ref`
- `contamination_scan_ref`
- `task_diversity_ref`

验收原则：

- 不稳定任务必须进入 `quarantined` 或 `diagnostic_only`，不能计入 accepted / auditable 数量。
- 使用 SWE-Bench-like 任务时，必须固定本地输入、固定源码、固定 verifier plan，不能从浮动网络分支或默认 dataset revision 动态读取。
- gold patch、raw test patch、hidden test selector、official resolved status、official harness report 和 evaluator-only trace 不得进入 model-visible task input。
- 对真实 PR / issue 任务，raw PR body、raw PR diff、review comment、fix commit URL、AI session URL 或 provider raw response 进入 adapter-visible input 时必须被拒绝。
- `v5_task_diversity_report.json` 必须记录语言、仓库文件数量、目标文件数量、预期修改文件数量、测试类型、是否需要代码定位、是否需要探索、是否多文件修改、issue 清晰度和任务难度分层，避免 12 个任务只是数量更大的窄 fixture。

建议机器产物：

- `v5_task_inventory_report.json`
- `v5_task_set_manifest.json`
- `v5_task_construction_report.json`
- `v5_swebench_like_subset_manifest.json`
- `v5_pr_issue_task_manifest.json`
- `v5_task_diversity_report.json`
- `v5_task_stability_report.json`
- `v5_task_visibility_scan_report.json`

必须实现的 inspect 命令：

```bash
repo-harness inspect-v5-task-set V5_TASK_SET_MANIFEST --assert-complete
repo-harness inspect-v5-task-visibility V5_TASK_VISIBILITY_SCAN_REPORT --assert-clean
```

### P0-3：最小 provider / scaffold / budget comparison proof

目标是补齐 V4 只保留 provider / scaffold / budget 元数据的缺口，同时避免把 V5 拖成完整 provider leaderboard。P0 只要求最小可比较运行和 provider credential gate；多真实 provider 强表述由 `resume_ready_acceptance` 单独控制。

P0 core comparison proof：

- Provider 条件：
  - 至少 1 个真实 provider family 有实际 agent run evidence。
  - `openai`、`deepseek`、`anthropic_claude` 都应进入 provider registry 和 credential gate。
  - `mock` 或 `replay` 只作为结构性回归、负例和无凭证 fallback，不得计入真实 provider accepted rate。
- Scaffold 条件：
  - `simple_react`
  - `planner_coder_verifier`
- Budget 条件：
  - `standard`
  - `constrained`
- Task 条件：
  - 至少 4 个稳定 accepted / auditable tasks 进入 core comparison proof。

每条 comparison proof 必须显式声明：

- `comparison_axis`：当前比较的是 provider、scaffold、budget 还是 diagnostic baseline。
- `controlled_variables`：比较中保持不变的 task、source tree、final verifier plan、tool policy、context policy、scaffold、budget、provider、model settings 和 environment id。
- `compared_cells`：参与同一比较结论的 matrix cell refs。
- `comparison_validity`：valid、diagnostic_only 或 invalid。

Resume-ready multi-provider claim gate：

- 至少 2 个真实 provider family 有实际 agent run evidence。
- 每个计入 multi-provider claim 的 provider family 至少有 2 条真实 agent run records。
- Resume-ready 的 provider 比较必须至少覆盖 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget` 的成对比较；这 4 个 provider-task cell 必须共享同一 source tree、final verifier plan、tool policy、context policy 和 environment id。
- 第 3 个 provider 可以 structured skip，但必须在 `v5_provider_credential_gate_report.json` 中说明凭证状态和不计入比较统计的原因。
- 如果只有 1 个真实 provider family 有实际运行，V5 可以进入 `core_acceptance`，但最终简历表述必须降级为 `credential-gated provider interface with one real-provider run and structured skips`，不得写 `multi-provider agent runs`。
- 如果没有任何真实 provider family 有实际运行，V5 不满足本阶段简历目标，final acceptance 应为 `blocked_real_provider` 或等价结构化阻塞状态。

矩阵不要求所有 provider 凭证都存在。如果凭证缺失，必须输出 structured skip，并记录 provider id、credential status、skip reason、affected matrix cells、是否影响 `core_acceptance`、是否影响 `resume_ready_acceptance`。凭证缺失不能伪装成 accepted run。

Provider cost 和预算边界必须机器可验收：

- `max_real_provider_calls`
- `max_cost_usd`
- `cost_proxy_formula`
- `actual_real_provider_calls`
- `actual_cost_proxy_usd`
- `cost_limited_structured_skip`
- `budget_exhausted_before_run`

如果达到 `max_real_provider_calls` 或 `max_cost_usd`，后续真实 provider matrix cell 必须 structured skip，不能静默改用 mock / replay 后仍计入真实 provider 结果。

每个 matrix cell 必须记录：

- `task_id`
- `provider_id`
- `provider_mode`
- `model_id`
- `model_version_date`
- `api_endpoint_type`
- `temperature`
- `top_p`
- `max_tokens`
- `tool_call_mode`
- `scaffold_id`
- `budget_policy_id`
- `tool_policy_id`
- `context_policy_id`
- `verifier_id`
- `environment_id`
- `source_tree_hash`
- `run_id`
- `run_dir`
- `final_verifier_status`
- `token_usage`
- `wall_time_ms`
- `tool_call_count`
- `test_run_count`
- `invalid_tool_call_count`
- `permission_denial_count`
- `patch_line_count`
- `changed_files_count`
- `patch_quality_ref`
- `test_overfitting_risk_ref`
- `regression_summary_ref`
- `review_notes_ref`
- `final_patch_ref`
- `trajectory_ref`
- `provider_error_category`
- `fallback_policy_result`
- `comparison_axis`
- `controlled_variables_ref`

比较原则：

- 只能比较同一 task、同一 source tree、同一 verifier plan、同一 tool policy、同一 context policy 和明确预算策略下的结果。
- Provider 比较时必须固定 scaffold 和 budget；scaffold 比较时必须固定 provider 和 budget；budget 比较时必须固定 provider 和 scaffold。
- fallback 成功必须单独标记，不能算 primary provider accepted。
- mock / replay 不能与真实 provider 混在一个成功率指标里。
- Provider raw request、provider raw response、Authorization marker、credential path 和 reasoning summary 原文不得进入 transcript、model-visible content 或 trainable payload。
- patch quality、review notes 和 test overfitting risk 只能作为诊断辅助，不能替代 final verifier，也不能把 final verifier rejected 的运行提升为 accepted。

建议机器产物：

- `v5_run_matrix_manifest.json`
- `v5_provider_registry_report.json`
- `v5_provider_credential_gate_report.json`
- `v5_provider_cost_budget_report.json`
- `v5_scaffold_comparison_report.json`
- `v5_budget_comparison_report.json`
- `v5_matrix_cell_results.jsonl`
- `v5_matrix_compare_scope_report.json`
- `v5_resume_claim_gate_report.json`

必须实现的 inspect 命令：

```bash
repo-harness inspect-v5-run-matrix V5_RUN_MATRIX_MANIFEST --assert-complete
repo-harness inspect-v5-provider-gate V5_PROVIDER_CREDENTIAL_GATE_REPORT --assert-consistent
```

### P0-4：高质量训练导出结果包

目标是交付可以向面试官展示的训练数据样本包。V5 不声称已经训练模型，但必须证明 RepoHarness 能把 agent 轨迹转成严格审计过的训练样本。

最小导出要求：

- 至少 1 个合规 SFT export 样本。
- 至少 1 个合规 reinforcement learning rollout export 样本。
- 至少 1 个 failure dataset 样本。
- 至少 1 个 diagnostic-only 样本，说明为什么不能训练。
- 至少 1 个 blocked export 样本，说明阻断原因。
- Preference pair 是 `resume_ready_acceptance` 的声明门：V5 目标是至少 1 个真实可比较 preference pair；如果真实运行没有自然产生合规 pair，必须生成 `v5_preference_pair_blocked_report.json`，V5 可以保留 export pack core acceptance，但不得在简历中写 preference pair export 已完成。

每条 trainable 样本必须绑定：

- `task_id`
- `run_id`
- `source_tree_hash`
- `prepared_messages_ref`
- `prepared_messages_sha256`
- `model_input_hash`
- `context_revision`
- `tool_observation_ref`
- `observation_source_event_ref`
- `observation_matches_prepared_messages`
- `trajectory_ref`
- `final_verifier_boundary_ref`
- `reward_metadata_ref`
- `reward_source_type`
- `export_policy_ref`
- `contamination_scan_ref`

Preference pair 必须满足：

- chosen 和 rejected 来自同一 task。
- chosen 和 rejected 来自同一 fixed source。
- chosen 和 rejected 使用同一 final verifier plan。
- chosen 和 rejected 使用同一 tool policy 和 context policy，或 compare scope 明确允许差异。
- outcome tier 可比较。
- chosen / rejected 的 final verifier boundary evidence 都存在。
- reward scalar 和 reward label 不进入模型可见文本、SFT target 或 preference target。
- chosen 和 rejected 必须来自 run matrix 或同一 frozen compare scope 下的真实 agent runs；不能用 mock、replay、不同 verifier plan、不同 source tree 或手写假记录凑 pair。

样本来源统计必须分列：

- `real_provider_trainable_records`
- `mock_or_replay_records`
- `diagnostic_records`
- `blocked_records`
- `synthetic_safe_stress_records`

failure dataset 必须同时生成失败类型汇总，至少统计 dependency failure、test timeout、invalid tool call、permission denial、context limit、provider error、final verifier fail、pass-to-pass regression、environment unstable 和 no progress。

Reward source taxonomy 必须至少区分：

- `unit_test`
- `rule_based_verifier`
- `rubric`
- `llm_judge_audit_only`
- `mixed`

Failure taxonomy 必须同时记录 `failure_owner`，至少包含：

- `model_behavior`
- `environment_unstable`
- `provider_error`
- `verifier_or_config_issue`
- `permission_or_policy`
- `unknown`

建议机器产物：

- `v5_export_result_pack_manifest.json`
- `v5_sft_export.jsonl`
- `v5_rl_rollout_export.jsonl`
- `v5_preference_pair_export.jsonl`
- `v5_preference_pair_blocked_report.json`
- `v5_failure_dataset.jsonl`
- `v5_failure_taxonomy_report.json`
- `v5_reward_source_taxonomy_report.json`
- `v5_export_audit_report.json`
- `v5_duplicate_record_report.json`

必须实现的 inspect 命令：

```bash
repo-harness inspect-v5-export-pack V5_EXPORT_RESULT_PACK_MANIFEST --assert-clean
```

### P0-5：Interview demo card 和 resume artifact pack

目标是把 V5 的工程结果整理成简历和面试可用材料。这个产物不是宣传页，而是可以被现场追问的技术索引。

必须回答：

1. RepoHarness 解决什么问题。
2. 为什么不做完整 SWE-Bench Lite 或 SWE-Bench Verified。
3. 如何构造和冻结任务。
4. 如何防止 evaluator-only evidence 泄漏。
5. 如何保证 final verifier 是权威结果来源。
6. 如何比较 provider、scaffold 和 budget。
7. 如何把 trajectory 转成训练样本。
8. 如何恢复中断运行和导出。
9. 当前边界和非目标是什么。
10. Claude Code 参考架构中的哪些不变量被 RepoHarness 吸收，哪些产品能力明确不实现。
11. network policy、approval boundary 和 risky command audit 如何防止 reward hacking 风险被误写成训练样本。

建议机器产物：

- `v5_interview_demo_card.md`
- `v5_interview_demo_card.json`
- `v5_canonical_demo_walkthrough.md`
- `v5_resume_artifact_index.json`
- `v5_public_demo_bundle_manifest.json`
- `v5_repro_command_index.json`
- `v5_result_summary_table.json`
- `v5_demo_transcript_index.json`
- `v5_permission_network_risk_audit_report.json`
- `v5_claude_code_invariant_mapping.json`

`v5_canonical_demo_walkthrough.md` 必须绑定一个代表性任务和一条真实 run，沿着 task freeze、agent run、trajectory、final verifier、export sample、acceptance binding 讲完整闭环。它必须包含可复现命令、关键 artifact 路径、预期 inspect 结果、可展示的 redacted transcript excerpt、现场演示失败时的降级讲法。

Canonical demo walkthrough 必须包含一条 5 分钟任务剧情：

- 原始失败是什么。
- agent 如何定位相关文件。
- 哪个关键工具 observation 改变了下一步动作。
- final patch 改了哪些文件和核心逻辑。
- final verifier 为什么接受。
- 导出样本为什么 trainable 或为什么 diagnostic-only。
- 至少一个现场负例 inspect，例如 sha256 漂移、未绑定 final verifier evidence 或 evaluator-only evidence 泄漏被拒绝。

`v5_public_demo_bundle_manifest.json` 必须只包含 `share_safe=true` 的 artifact。Demo card 和 walkthrough 只能引用 public-safe artifact，不能现场打开 provider raw response、credential marker、hidden verifier detail、本机私密路径、evaluator-only raw evidence 或未脱敏 transcript。

`v5_result_summary_table.json` 必须提供面试官一眼能看懂的量化结果，至少包含：

- accepted rate，按 overall、provider family、scaffold、budget 和 task family 分组。
- pass-to-pass regression rate。
- failure type distribution 和 failure owner distribution。
- token usage summary。
- wall time summary。
- cost proxy summary。
- provider comparison conclusion，必须绑定 controlled variables。
- scaffold comparison conclusion，必须绑定 controlled variables。
- budget comparison conclusion，必须绑定 controlled variables。
- trainable、diagnostic、blocked、mock / replay 和 synthetic-safe stress records 的分区统计。

指标分母必须显式定义：

- accepted rate 的真实 provider 分母只包含实际启动并到达 final verifier 或结构化 terminal outcome 的真实 provider runs，不包含 credential missing skip、cost-limited skip、mock / replay 或 synthetic stress records。
- mock / replay accepted rate 必须单独统计，不能混入真实 provider accepted rate。
- structured skip、credential missing skip 和 cost-limited skip 必须单独统计为 coverage / availability 指标，不能算作成功或失败。
- pass-to-pass regression rate 的分母是成功应用 final patch 并运行 pass-to-pass verifier 的 runs；verifier 未运行、environment unstable 或 setup failed 必须单独进入 failure taxonomy。
- token usage、wall time 和 cost proxy 必须分别按 real provider、mock / replay 和 stress records 分区，不能合并出一个含混平均值。

`v5_permission_network_risk_audit_report.json` 必须记录 network policy、approval boundary、风险命令命中次数、风险命令是否进入模型可见内容、风险命令是否影响 trainable export。风险命令至少包括 `curl`、`wget`、`git clone`、`git remote add`、修改远程地址、访问未固定网络资源和绕过 verifier 的 shell 模式。

`v5_claude_code_invariant_mapping.json` 必须是一张对照表：`Claude Code 不变量 -> RepoHarness 落地证据 -> 明确不实现的边界`。至少覆盖 query loop、tool contract、tool result pairing、permission boundary、hook audit、MCP disabled / frozen facts、context compaction、transcript diagnostics 和 artifact refs。这个表用于说明 RepoHarness 借鉴架构不变量，而不是复刻 Claude Code 产品。

如果 `resume_ready_acceptance` 没有通过，最终简历表述必须根据 `v5_resume_claim_gate_report.json` 自动降级。例如缺少两个真实 provider family 时，不能写 `multi-provider agent runs`；缺少真实可比较 preference pair 时，不能写 `preference export` 已完成；只完成 export stress test 时，不能写大规模真实训练数据。

## 6. V5 P1 候选范围

P1 是有面试价值但不应阻塞 V5 最小完成的增强项。

### P1-0：Multi-provider matrix expansion

如果时间和凭证条件允许，可以把 P0 的最小 comparison proof 扩展为更完整的 thin matrix：

- 2 到 3 个真实 provider family。
- 2 个 scaffold。
- 2 档 budget。
- 4 到 6 个稳定任务。

这个增强可以支撑 `resume_ready_acceptance` 中的 multi-provider 强表述，但仍然不是 provider leaderboard。缺少任一 provider 凭证时必须 structured skip，并由 `v5_resume_claim_gate_report.json` 降级最终表述。

### P1-1：Provider adapter polish

如果时间允许，可以增强真实 provider adapter 的错误分类和成本统计：

- OpenAI、DeepSeek、Anthropic Claude 的统一 provider registry。
- 统一 token usage、latency、retry、rate limit、context length、tool call format error 分类。
- provider-specific raw artifact redaction。
- provider cost proxy report。

边界：

- 不做 provider leaderboard。
- 不把真实 provider 结果写成公开模型能力排名。
- 不把凭证缺失的 provider 计入失败率。

P0 只要求最小 provider registry、credential gate、raw artifact redaction gate 和基础 token usage。P1-1 才扩展更细的 latency、rate limit、context length、provider-specific error taxonomy 和成本估算。

### P1-2：Context strategy micro-comparison

如果时间允许，可以在 2 到 3 个任务上比较：

- keep-recent。
- summary。
- artifact-only。

必须继续绑定 PreparedMessages、model input hash、context revision 和 observation replacement trace。

边界：

- 不做产品级长期记忆。
- 不做 KV cache 恢复。
- 不做跨实验用户记忆继承。

### P1-3：Code retrieval diagnostic

如果时间允许，可以增加小规模代码检索诊断：

- file localization task。
- grep / rg trace。
- target file found before edit 的事实。
- retrieval quality report。

边界：

- 不建设向量数据库。
- 不训练 retrieval agent。
- 不用 retrieval metrics 替代 final verifier。

### P1-4：Prompt injection diagnostic-only task

如果时间允许，可以增加少量 diagnostic-only prompt injection 或 instruction conflict fixture。

边界：

- 诊断任务不得进入 trainable payload。
- hidden instruction 和 evaluator-only trap 不能进入模型可见训练样本。
- LLM judge 只能作为 audit-only 辅助，不能替代 deterministic final verifier。

### P1-5：Export stress test 和可恢复导出

如果时间允许，可以增加 1,000 条以上 replay / synthetic-safe export records 的 sharded export stress test。

验收原则：

- stress test 用于证明导出管线、manifest、sha256、resume 和 duplicate detection，不得宣传为大规模真实训练数据。
- stress records 必须与真实 trainable records 分区，不能混入真实 provider 样本统计。
- result summary 和 demo card 必须分列 `real_trainable_records`、`diagnostic_records`、`blocked_records` 和 `synthetic_safe_stress_records`。

建议机器产物：

- `v5_export_stress_manifest.json`
- `v5_export_resume_report.json`
- `v5_export_shard_manifest.json`

Inspect 命令：

```bash
repo-harness inspect-v5-export-stress V5_EXPORT_STRESS_MANIFEST --assert-resumable
```

## 7. V5 明确非目标

V5 不做：

1. 完整 SWE-Bench Lite。
2. SWE-Bench Verified。
3. SWE-Bench Pro 或任何公开 leaderboard 复现。
4. 大规模自动 PR mining。
5. 不可人工审计的大规模任务生成。
6. Kubernetes、分布式 rollout 或异步强化学习集群。
7. 训练强化学习算法。
8. 训练 reward model。
9. 大规模真实训练数据生产承诺。
10. provider leaderboard。
11. 生产级安全沙箱或多租户隔离承诺。
12. 完整 Claude Code、Cursor、Codex、OpenHands 或 SWE-agent 产品复刻。
13. 完整插件系统、完整 MCP 生态或远程工具市场。
14. 真实并行多智能体 swarm。
15. GUI / browser / search agent 多领域扩展。

## 8. V5 阶段建议

### Stage 0：V4 closure baseline 和文档同步

目标：

- 冻结 V4 最新通过状态。
- 逐项证明 V4 复核问题已经由修复 commit、重新生成 evidence、inspect 命令和 latest acceptance bundle 关闭。
- 修正文档中的 V4 状态漂移，并把 V5 文档纳入项目入口索引。
- 生成 V5 preimplementation baseline evidence。

退出门：

- V2 / V3 / V4 inspect 全部通过。
- 最新 V4 acceptance inputs inspect 通过。
- `e0da89c` 是当前 HEAD 的祖先。
- `v5_baseline_check_report.json` 生成并通过 inspect。
- `v4_review_findings_closure_report.json` 生成并绑定旧 findings、修复 commits 和最新 evidence。
- `v5_documentation_sync_report.json` 覆盖 README、AGENTS、`docs/00-reading-guide.md`、`docs/01-project-positioning-and-requirements.md`、`docs/12-resume-narrative-and-demo-artifacts.md` 和 `docs/v4/final-acceptance.md`。
- `v5_documentation_sync_report.json` 还必须检查 `reference/claude-code-typescript-src/AGENTS.md` 的实际文件名和引用路径，避免继续写成不存在或不准确的 `AGENT.md`。

### Stage 1：V5 schema 和 evidence integrity gate

目标：

- 定义 V5 evidence ref、critical evidence class、acceptance lineage schema。
- 实现 pre-acceptance evidence integrity inspect，并把 acceptance report 引用检查和 bundle command lineage 检查分别放入 `inspect-v5-acceptance` 与 `inspect-acceptance-bundle`。

退出门：

- 正例 pre-acceptance evidence integrity report 通过。
- unbound evidence、sha256 drift、旧 report command log、未绑定 final verifier evidence 等负例被拒绝。

### Stage 2：V5 task subset freeze

目标：

- 先建立 task inventory 和复用策略，明确哪些 V4 task 可以继承计数，哪些必须重新验收。
- 建立 12 到 20 个 accepted / auditable task definitions。
- 固定 SWE-Bench-like 锚点和 PR / issue mixed task subset。

退出门：

- `inspect-v5-task-set --assert-complete` 通过。
- `inspect-v5-task-visibility --assert-clean` 通过。
- `v5_task_inventory_report.json` 和 `v5_task_diversity_report.json` 生成并通过检查。
- 至少 12 个 accepted / auditable tasks。
- 至少 8 个 PR / issue flow tasks。
- 至少 3 个 SWE-Bench-like anchor tasks。

### Stage 3：Provider / scaffold / budget comparison proof

目标：

- 接入 OpenAI、DeepSeek、Anthropic Claude 的 credential-gated provider registry 和 credential gate。
- 完成至少 1 个真实 provider family、2 个 scaffold、2 档 budget 的最小 comparison proof。
- 至少 6 个任务产生真实 agent run evidence，至少 4 个任务进入 comparison proof。
- 如果要获得 `resume_ready_acceptance` 的 multi-provider 声明门，至少 2 个真实 provider family 必须各有至少 2 条真实 agent run records。
- Resume-ready provider 比较必须至少覆盖 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget` 的受控成对比较。

退出门：

- `inspect-v5-run-matrix --assert-complete` 通过。
- `inspect-v5-provider-gate --assert-consistent` 通过。
- 至少 1 个真实 provider family 有实际 agent run evidence。
- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入 comparison proof。
- 凭证缺失必须 structured skip。
- `v5_resume_claim_gate_report.json` 明确最终允许和禁止使用哪些简历表述。

### Stage 4：Training export result pack

目标：

- 生成 SFT、RL rollout、preference pair 和 failure dataset。
- 如果没有真实可比较 preference pair，生成 blocked preference pair report，不得凑样本。

退出门：

- 至少 1 个合规 SFT 样本。
- 至少 1 个合规 RL rollout 样本。
- 至少 1 个 failure dataset 样本。
- 至少 1 个 diagnostic-only 样本。
- 至少 1 个 blocked export 样本。
- `inspect-v5-export-pack --assert-clean` 通过。
- preference pair 要么通过真实 compare scope gate，要么以 `v5_preference_pair_blocked_report.json` 明确阻塞，并在 `v5_resume_claim_gate_report.json` 禁止 preference export 强表述。
- `v5_failure_taxonomy_report.json` 生成并通过检查。
- `v5_reward_source_taxonomy_report.json` 生成并通过检查。

### Stage 5：Interview demo card 和 result artifacts

目标：

- 生成面试展示卡片、canonical demo walkthrough、public-safe demo bundle、结果汇总表、demo transcript index 和 repro command index。

退出门：

- Demo card 中每个数字和结论都能追溯到 evidence ref。
- Demo card 不包含 provider raw response、hidden verifier detail、credential marker 或 evaluator-only raw evidence。
- canonical demo walkthrough 可以沿一个真实任务讲通 task freeze、agent run、trajectory、final verifier、export sample 和 acceptance binding。
- public-safe demo bundle 只包含 `share_safe=true` 的 artifact。
- `v5_result_summary_table.json` 包含 accepted rate、pass-to-pass regression rate、failure type distribution、failure owner distribution、token usage、wall time、cost proxy、provider / scaffold / budget comparison conclusion 和样本分区统计。
- `v5_permission_network_risk_audit_report.json` 和 `v5_claude_code_invariant_mapping.json` 生成并通过检查。

### Stage 6：Final acceptance 和 post-acceptance docs

目标：

- 生成 V5 acceptance inputs、acceptance report 和 acceptance bundle。
- 更新 V5 final acceptance 和 walkthrough。

退出门：

```bash
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs V5_ACCEPTANCE_INPUTS --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-core-complete --reference-integrity-output V5_ACCEPTANCE_REPORT_REFERENCE_INTEGRITY_REPORT --command-log-entry-output INSPECT_V5_ACCEPTANCE_CORE_COMMAND_LOG_ENTRY
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-resume-ready --reference-integrity-input V5_ACCEPTANCE_REPORT_REFERENCE_INTEGRITY_REPORT --command-log-entry-output INSPECT_V5_ACCEPTANCE_RESUME_READY_COMMAND_LOG_ENTRY
PATH=.venv/bin:$PATH repo-harness build-v5-pre-bundle-command-log --base-command-log V5_STAGE6_COMMAND_LOG_DRAFT --command-log-entry INSPECT_V5_ACCEPTANCE_CORE_COMMAND_LOG_ENTRY --command-log-entry INSPECT_V5_ACCEPTANCE_RESUME_READY_COMMAND_LOG_ENTRY --output V5_PRE_BUNDLE_COMMAND_LOG --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness build-v5-acceptance-bundle --acceptance-report V5_ACCEPTANCE_REPORT --post-report-inspect-output V5_ACCEPTANCE_REPORT_REFERENCE_INTEGRITY_REPORT --pre-bundle-command-log V5_PRE_BUNDLE_COMMAND_LOG --bundle-build-command-log-entry-output BUILD_V5_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY --documentation-ref docs/v5/final-acceptance.md --documentation-ref docs/v5/walkthrough.md --output V5_ACCEPTANCE_BUNDLE --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness plan-acceptance-bundle-inspect-entry --acceptance-bundle V5_ACCEPTANCE_BUNDLE --final-command-log V5_FINAL_ACCEPTANCE_COMMAND_LOG --output INSPECT_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY
PATH=.venv/bin:$PATH repo-harness build-v5-final-command-log --pre-bundle-command-log V5_PRE_BUNDLE_COMMAND_LOG --command-log-entry BUILD_V5_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY --command-log-entry INSPECT_ACCEPTANCE_BUNDLE_COMMAND_LOG_ENTRY --output V5_FINAL_ACCEPTANCE_COMMAND_LOG --fail-if-output-exists
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle V5_ACCEPTANCE_BUNDLE --final-command-log V5_FINAL_ACCEPTANCE_COMMAND_LOG --assert-immutable
```

`inspect-v5-acceptance` 必须支持分层断言：

- `--assert-core-complete`：要求 `core_acceptance.status=passed`，并检查 acceptance report reference integrity。
- `--assert-resume-ready`：要求 `core_acceptance.status=passed`、`resume_ready_acceptance.status=passed`，并检查 `allowed_claims` 和 `blocked_claims` 与 `v5_resume_claim_gate_report.json` 一致。
- `--assert-complete`：如果保留该兼容参数，必须等价于 `--assert-resume-ready`；不能只检查 core acceptance 后仍叫 complete。

V5 acceptance report 必须显式包含：

- `core_acceptance.status`
- `core_acceptance.required_checks`
- `resume_ready_acceptance.status`
- `resume_ready_acceptance.required_checks`
- `allowed_claims`
- `blocked_claims`
- `claim_gate_report_ref`
- `acceptance_report_reference_integrity`

## 9. V5 最终 acceptance 必要输入

V5 final acceptance 相关证据分为三组，避免把后生成的 inspect 输出错误放回 acceptance inputs。

### 9.1 Acceptance inputs 必须显式绑定

- V2 acceptance report。
- V3 acceptance report。
- V3 acceptance bundle。
- V4 latest acceptance inputs。
- V4 latest acceptance report。
- V4 latest doc-sync acceptance bundle。
- V4 latest doc-sync final command log。
- V5 baseline check report。
- V4 review findings closure report。
- V5 documentation sync report。
- V5 pre-acceptance evidence integrity report。
- V5 task set manifest。
- V5 task inventory report。
- V5 task diversity report。
- V5 task visibility scan report。
- V5 run matrix manifest。
- V5 provider credential gate report。
- V5 provider cost budget report。
- V5 resume claim gate report。
- V5 export result pack manifest。
- V5 preference pair blocked report，如果没有真实可比较 preference pair。
- V5 failure taxonomy report。
- V5 reward source taxonomy report。
- V5 interview demo card。
- V5 canonical demo walkthrough。
- V5 public demo bundle manifest。
- V5 resume artifact index。
- V5 repro command index。
- V5 result summary table。
- V5 demo transcript index。
- V5 permission / network risk audit report。
- V5 Claude Code invariant mapping。
- V5 pre-report command log。
- V5 implementation logs。
- V5 review records。
- V5 final acceptance pre-test evidence。

如果 P1 export stress test 被实际执行，`v5_export_stress_manifest.json` 和 `v5_export_resume_report.json` 也必须显式绑定；如果没有执行 P1 stress test，final acceptance 不能要求它存在，也不能在最终简历表述中写 resumable export stress tests。

Acceptance builder 不得扫描 latest run。所有输入必须通过显式路径传入，并记录 sha256。

Acceptance inputs 中的 V5 command logs 只能绑定 acceptance report 生成之前已经存在的 pre-report command log。Post-report inspect command entries、pre-bundle command log、bundle build entry 和 final command log 必须按后续时序进入 acceptance bundle，不能提前进入 acceptance report 输入。

### 9.2 Post-report inspect 和 pre-bundle outputs

这些产物在 V5 acceptance report 生成之后由 inspect 命令产生，不能作为 acceptance report 输入：

- `v5_acceptance_report_reference_integrity_report.json`
- `inspect_v5_acceptance_core_command_log_entry`
- `inspect_v5_acceptance_resume_ready_command_log_entry`
- V5 pre-bundle command log。

它们必须进入 final command log 或 acceptance bundle 的 post-report outputs section，由 bundle immutable inspect 绑定。`V5_PRE_BUNDLE_COMMAND_LOG` 可以作为 `build-v5-acceptance-bundle` 的显式输入，但不能作为 acceptance report 输入。

### 9.3 Bundle final outputs

这些产物在 acceptance bundle 构建期间或之后产生，不能作为 acceptance report 输入：

- V5 acceptance bundle manifest。
- V5 acceptance bundle command lineage report。
- `build_v5_acceptance_bundle_command_log_entry`
- final acceptance command log。
- `inspect_acceptance_bundle_command_log_entry`
- Post-acceptance `docs/v5/final-acceptance.md`，如果生成。
- Post-acceptance `docs/v5/walkthrough.md`，如果生成。

`build-v5-acceptance-bundle` 必须显式接收当前 V5 acceptance report、post-report inspect outputs、pre-bundle command log、post-acceptance documentation refs 和输出 bundle manifest；不得扫描 latest acceptance directory，也不得覆盖已经存在的 bundle，不得读取随后还会生成或追加的 final command log。

## 10. V5 成功指标

V5 成功指标分成三层，分别控制“工程闭环是否完成”和“哪些简历表述可以使用”。

`core_acceptance` 必须满足：

- 全量测试通过。
- V2 / V3 / V4 回归 inspect 通过。
- V5 pre-acceptance evidence integrity inspect 通过。
- V5 task set inspect 通过。
- V5 run matrix inspect 通过。
- V5 provider cost budget report 通过检查。
- V5 export pack inspect 通过。
- V5 acceptance report inspect 通过。
- V5 acceptance bundle immutable inspect 通过。
- 至少 12 个 accepted / auditable task definitions。
- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入 comparison proof。
- 至少 1 个真实 provider family 有实际 agent run evidence。
- 至少 1 个合规 SFT、RL rollout 和 failure dataset 样本。
- 至少 1 个 diagnostic-only 样本，并由 export pack inspect 证明没有进入 trainable payload。
- 至少 1 个 blocked export 样本，并由 export pack inspect 记录阻断原因、failure owner 和 failure category。
- Preference pair 要么有 1 个真实可比较样本，要么有完整 blocked report，并在 resume claim gate 中禁用 preference export 强表述。
- 0 个 trainable payload contamination finding。
- 0 个 evaluator-only evidence model-visible finding。
- 0 个 acceptance report unbound critical evidence finding。
- 0 个 provider credential raw value 泄漏 finding。
- 0 个 provider raw request / provider raw response 进入 transcript model-visible content、trainable payload、public-safe demo bundle 或 final acceptance docs。
- 0 个 risky command 或 network policy finding 进入模型可见训练内容。
- result summary 必须分列 real provider trainable records、mock / replay records、diagnostic records、blocked records 和 synthetic-safe stress records。
- result summary 必须展示 accepted rate、pass-to-pass regression rate、failure type distribution、failure owner distribution、token usage、wall time、cost proxy、provider / scaffold / budget comparison conclusion 和 trainable / diagnostic / blocked / mock-replay 分区统计。

`resume_ready_acceptance` 额外要求：

- 至少 2 个真实 provider family 各有至少 2 条真实 agent run records。
- Provider 比较至少覆盖 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget` 的受控成对比较。
- Scaffold 比较至少覆盖 2 个任务，在同一真实 provider、同一 budget、同一 source tree、同一 verifier plan、同一 tool policy 和同一 context policy 下比较 `simple_react` 与 `planner_coder_verifier`。
- Budget 比较至少覆盖 2 个任务，在同一真实 provider、同一 scaffold、同一 source tree、同一 verifier plan、同一 tool policy 和同一 context policy 下比较 `standard` 与 `constrained`。
- 至少 1 个真实可比较 preference pair 通过 compare scope gate。
- `v5_canonical_demo_walkthrough.md` 和 `v5_public_demo_bundle_manifest.json` 通过 share-safe 检查。
- `v5_resume_claim_gate_report.json` 明确允许使用完整强表述。

Stretch target 不影响 `core_acceptance`：

- 20 个 accepted / auditable task definitions。
- 3 个真实 provider family 都有实际 agent run evidence。
- P1 export stress test 通过。
- P1 context strategy micro-comparison 或 code retrieval diagnostic 通过。

## 11. 面试叙事

V5 完成后，推荐面试叙事是：

1. 我没有复刻 Claude Code 或 SWE-Bench 官方 harness，而是实现了一个训练友好的 repository-level software engineering agent harness。
2. 它统一了 task adapter、Docker-based executable repository environment、tool lifecycle、agent loop、trajectory store、final verifier、reward metadata 和 training export。
3. 我把 SWE-Bench-like 和 PR / issue task 都降维成固定、可审计、可冻结的 task subset，避免浮动数据源和 hidden evidence 泄漏。
4. 我做了最小 provider / scaffold / budget comparison proof，用同一任务、同一源码、同一 verifier 和同一工具策略比较运行结果；只有在至少两个真实 provider family 有实际运行证据时，才使用 multi-provider 强表述。
5. 我没有声称训练出模型，而是交付了可训练样本的审计管线：SFT、RL rollout 和 failure dataset 都有字段级 visibility、sha256、final verifier boundary 和 contamination scan；preference pair 只有在真实 compare scope gate 通过时才作为完成结果表述。
6. 我把 acceptance 做成不可变 bundle，任何 evidence 漂移、command log 指错 report、provider raw response 泄漏、reward label 进入训练目标都会被 inspect 拒绝。

简历上可以写结果，不要写夸张承诺。V5 必须提供三条模板，由 `v5_resume_claim_gate_report.json` 决定哪一条可以使用。

`core_acceptance` 可用表述：

```text
Implemented RepoHarness, a local-first software engineering agent evaluation and training-data harness: built Docker-based executable repository tasks, auditable rollout orchestration, credential-gated provider runs, scaffold/budget comparison proof, verifier-aligned reward metadata, contamination-resistant SFT/RL export audit, failure taxonomy, and immutable acceptance bundles.
```

`resume_ready_acceptance` 可用表述：

```text
Implemented RepoHarness, a local-first software engineering agent evaluation and training-data harness: built Docker-based executable repository tasks, auditable rollout orchestration, controlled multi-provider/scaffold/budget comparison, verifier-aligned reward metadata, contamination-resistant SFT/RL/preference export, share-safe demo artifacts, and immutable acceptance bundles.
```

`stress_test_completed` 后才可用表述：

```text
Extended RepoHarness export infrastructure with sharded synthetic-safe stress records, resumable export manifests, duplicate detection, and strict separation between real trainable records and pipeline stress-test records.
```

`resume_ready_acceptance` 表述只有在对应声明门通过后才能使用。`stress_test_completed` 表述只有在 P1 export stress test 实际完成并通过 inspect 后才能使用。

如果只通过 `core_acceptance`，不能使用 `multi-provider agent runs`、`preference export completed` 或 `resumable export stress tests` 这些强表述。

如果 V5 未完成，只能写 V1-V4 已完成结果，并把 V5 描述为 scope 或 roadmap。

## 12. 风险和降级路径

### 风险：任务数量压倒任务质量

如果 12 到 20 个任务中有任务无法稳定复现 baseline verifier、source materialization、flaky probe 或 final verifier，应降级为 quarantined 或 diagnostic-only。不能为了数量把不可信任务放入 accepted / auditable。

### 风险：provider 凭证和真实调用成本不稳定

真实 provider 条件必须 credential-gated。缺少凭证时使用 structured skip，不影响结构性验收，但不能把 skipped provider 写成 accepted。

如果最终只有一个真实 provider family 有实际运行，项目可以通过 `core_acceptance`，但不能使用 `multi-provider agent runs` 的简历表述。如果没有任何真实 provider family 有实际运行，应阻塞 V5 的简历目标。

### 风险：矩阵组合爆炸

V5 只做薄矩阵。若运行成本过高，优先减少任务数量，不减少 evidence integrity、visibility policy 和 final verifier boundary 检查。

### 风险：导出规模被误解为真实训练规模

Export stress test 只证明管线能力。真实 trainable samples 必须单独统计，不能和 replay / synthetic-safe stress records 混写。

如果没有执行 P1 export stress test，文档和简历不得声称支持 resumable export stress tests。

### 风险：SWE-Bench-like 子集被误解为 leaderboard

V5 必须持续声明：它是可审计 showcase subset，不是完整 SWE-Bench Lite、SWE-Bench Verified 或公开榜单复现。
