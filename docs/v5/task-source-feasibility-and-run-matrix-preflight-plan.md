# RepoHarness V5 Task Source Feasibility And Run-Matrix Preflight Plan

## 0. 文档定位

本文定义进入 V5 implementation plan 之前必须先完成的任务来源可行性和运行矩阵预检计划。它回答三个问题：

1. V4 已经整理出的 SWE-Bench-like 任务和 GitHub PR / issue 任务候选，是否足够支撑 V5 的简历展示目标。
2. 在当前本机 Docker 和真实 provider API 条件下，哪些候选可以优先进入 V5 task freeze、真实 agent run 和 provider / scaffold / budget comparison proof。
3. 如果 V4 候选不足，应该用什么规则继续通过 GitHub CLI 或搜索工具扩展候选池。

本文不实现 V5 代码，不把任何候选直接宣称为 accepted task，也不把 provider smoke 结果宣称为 agent 能力评测结果。本文的产物应作为 V5 Stage 1 task source、Stage 2 task freeze、Stage 3 provider / scaffold / budget run matrix 和最终 acceptance evidence integrity 的正式输入。

## 1. 为什么 V5 前仍需要单独做 preflight

V5 的目标是形成可以写进简历、可以现场展示、可以被面试官追问的最终结果包。这个目标比 V4 的“闭环功能是否实现”更依赖真实任务和真实运行质量。

进入 V5 implementation plan 前先做 preflight 是必要的，原因如下：

1. V5 要形成 12 到 20 个 accepted / auditable task definitions，其中至少 8 个来自 PR / issue 构造流程，至少 3 个来自固定 SWE-Bench-like 锚点。如果任务池不足，后续 implementation plan 会把最大风险留到中后期。
2. V5 至少需要 6 个任务产生真实 agent run evidence，至少 4 个任务进入 comparison proof。任务如果只能冻结但不能稳定运行，不能支撑简历展示数字。
3. V5 的 `resume_ready_acceptance` 要求 provider、scaffold 和 budget 的受控成对比较。如果任务难度、运行时间或验证器不稳定，比较矩阵会被环境噪声污染。
4. V5 需要展示训练导出包，包括 SFT、reinforcement learning rollout、preference pair 或 blocked preference pair，以及 failure dataset。任务来源和 evaluator-only evidence 隔离必须提前验证。
5. V5 最终要产生 public-safe demo bundle。候选任务如果包含 raw provider response、AI coding session 链接、上游 patch 泄漏、hidden verifier 泄漏或 license provenance 风险，必须在 preflight 阶段提前发现。

## 2. 预检结论先验

基于 V4 文档已经整理的强候选，V5 第一轮不需要先扩展 GitHub 搜索池。当前已有候选足够启动本机 preflight：

- SWE-Bench-like 锚点候选：5 个。
- V4 第一批 PR / issue 强候选：8 个。
- V4 第二批 PR / issue 备选候选：7 个。
- 合计候选池：20 个。

这里的“足够”只表示候选库存数量足够启动测试，不表示已经有 20 个可计数 accepted / auditable tasks。所有候选仍必须重新通过 V5 的 inventory、source materialization、dependency probe、baseline verifier、post-patch verifier、flaky probe、visibility scan、artifact manifest 和 command lineage gate，才能计入 V5 最终成果。

第一轮策略是先用 V4 已有候选做本机可行性测试；只有当 freeze-ready 候选数量、生态多样性、comparison-ready 候选数量或 provider readiness 低于门槛时，才启动新的 GitHub CLI 搜索。

## 3. 输入文档

本 preflight 必须引用以下文档作为输入：

- `docs/v5/scope-and-roadmap.md`
- `docs/v5/review/scope-review.md`
- `docs/v4/swe-task-feasibility-experiment-plan.md`
- `docs/v4/pr-issue-task-source-plan.md`
- `docs/12-resume-narrative-and-demo-artifacts.md`
- `docs/13-agentic-technical-report-reading-map.md`

V5 implementation plan 不应直接引用对话结论作为任务来源依据；必须引用本文和本文对应的机器产物。

## 4. 顶层机器产物和审计闭环

preflight 不是一次临时脚本运行，而是 V5 evidence chain 的第一层。因此本计划要求所有预检产物进入显式 manifest 和 command log。

顶层产物：

- `v5_preflight_evidence_manifest.json`
- `v5_preflight_command_log.jsonl`
- `v5_preflight_command_lineage_report.json`
- `v5_resume_claim_gate_preflight_report.json`

`v5_preflight_evidence_manifest.json` 顶层至少记录：

- `schema_version`
- `created_at`
- `repo_root`
- `current_head`
- `run_dir`
- `producer_command_log_ref`

`v5_preflight_evidence_manifest.json` 中每个 artifact 至少记录：

- `artifact_id`
- `path`
- `sha256`
- `size_bytes`
- `kind`
- `purpose`
- `visibility`
- `share_safe`
- `producer_stage`
- `producer_command`
- `producer_command_log_ref`
- `input_refs`
- `output_refs`
- `inspect_command`
- `inspect_status`

`v5_preflight_command_log.jsonl` 中每条命令至少记录：

- `command_id`
- `argv`
- `cwd`
- `env_policy`
- `network_policy`
- `risk_command_hits`
- `input_refs`
- `output_refs`
- `started_at`
- `finished_at`
- `exit_code`
- `stdout_ref`
- `stderr_ref`
- `stdout_sha256`
- `stderr_sha256`

`v5_preflight_command_lineage_report.json` 必须检查每个关键 artifact 都能追溯到唯一 producer command，且每条 producer command 的输出都被 manifest 绑定。它不得扫描 latest run，也不得把未绑定输出当成通过证据。

`v5_resume_claim_gate_preflight_report.json` 至少包含：

- `allowed_claims`
- `blocked_claims`
- `blocking_reasons`
- `required_followup_work`
- `core_acceptance_preflight_status`
- `resume_ready_acceptance_preflight_status`
- `provider_claim_status`
- `preference_pair_claim_status`
- `stress_test_claim_status`

preflight 阶段如果没有真实 provider run evidence，只能把 provider 强表述放入 `blocked_claims`。structured skip 可以解释阻塞原因，不能替代真实运行证据。只执行 Level 0 / Level 1 时，必须生成 `status=partial` 的 claim gate report；这个 partial report 只表达当前已知阻塞和后续需要补的工作，不能宣称 `core_acceptance` 或 `resume_ready_acceptance` 已经通过。

## 5. 候选池

### 5.1 SWE-Bench-like 锚点候选

这些候选用于满足 V5 至少 3 个固定 SWE-Bench-like 锚点的要求，也用于向面试官说明 RepoHarness 可以处理接近公开软件工程评测风格的任务。

| 候选标识 | 项目家族 | 预期用途 | 初始判断 |
| --- | --- | --- | --- |
| `django__django-11283` | Django | 重型 Python Web framework 锚点 | 高价值，但可能依赖重，优先做 source 和 verifier probe。 |
| `astropy__astropy-14182` | Astropy | 科学计算任务锚点 | 高价值，适合展示复杂依赖和验证器隔离。 |
| `sphinx-doc__sphinx-7686` | Sphinx | 文档构建工具任务锚点 | 高价值，适合展示非业务逻辑类软件工程任务。 |
| `matplotlib__matplotlib-18869` | Matplotlib | 科学计算 / 可视化任务锚点 | 高价值，但依赖和测试时间风险较高。 |
| `scikit-learn__scikit-learn-10297` | scikit-learn | 机器学习库任务锚点 | 简历展示价值高，但应默认按高成本候选处理。 |

第一轮目标不是让 5 个全部进入真实 agent run，而是至少选出 3 个 freeze-ready anchors，并从中挑选 1 到 2 个低风险任务进入 demo 或 result summary。

### 5.2 PR / issue 第一批强候选

这些候选用于满足 V5 至少 8 个 PR / issue 构造任务的核心要求，也用于提供跨技术栈展示价值。

| 候选标识 | 生态 | 仓库 | 来源 | 初始用途 |
| --- | --- | --- | --- | --- |
| `spf13/cobra#2356` | Go | `spf13/cobra` | 修复 issue `#2257` | 第一轮本机 execution probe，优先 comparison-ready。 |
| `stretchr/testify#1531` | Go | `stretchr/testify` | 修复 issue `#1462` | 第一轮本机 execution probe，优先 comparison-ready。 |
| `pelletier/go-toml#1041` | Go | `pelletier/go-toml` | 修复 issue `#1032` | 第一轮或第二轮 execution probe，注意 PR body 中的 AI session 链接不能进入模型可见输入。 |
| `pallets/click#3208` | Python | `pallets/click` | 修复 issue `#2790` | 第一轮本机 execution probe，优先 demo-ready。 |
| `pytest-dev/pluggy#646` | Python | `pytest-dev/pluggy` | 修复 issue `#431` | 第一轮本机 execution probe，优先 comparison-ready。 |
| `sindresorhus/execa#1176` | JavaScript / TypeScript | `sindresorhus/execa` | 修复 issue `#1175` | 第二轮 execution probe，适合补跨生态展示。 |
| `yargs/yargs#2332` | JavaScript / TypeScript | `yargs/yargs` | 修复 issue `#2330` | 第二轮 execution probe，适合补跨生态展示。 |
| `sharkdp/fd#1805` | Rust | `sharkdp/fd` | 修复 issue `#1797` | diagnostic-first，多样性价值高，但不作为第一轮硬依赖。 |

### 5.3 PR / issue 第二批备选候选

如果第一批候选低于 V5 门槛，则从以下候选补位：

| 候选标识 | 生态 | 仓库 | 预期用途 |
| --- | --- | --- | --- |
| `pallets/click#3364` | Python | `pallets/click` | Python 稳定补位。 |
| `python-attrs/attrs#1428` | Python | `python-attrs/attrs` | Python 语义型任务补位。 |
| `pypa/packaging#1124` | Python | `pypa/packaging` | Python packaging 任务补位，注意可能需要拆分 issue 语义。 |
| `hynek/structlog#620` | Python | `hynek/structlog` | 低成本稳定补位。 |
| `chalk/chalk#335` | JavaScript | `chalk/chalk` | JavaScript smoke 或 fallback accepted 候选。 |
| `colinhacks/zod#5708` | TypeScript | `colinhacks/zod` | diagnostic probe，accepted 需要人工 review note。 |
| `clap-rs/clap#6340` | Rust | `clap-rs/clap` | Rust diagnostic probe，默认不阻塞 V5。 |

## 6. V5 run-matrix 预检目标

V5 不需要在 preflight 阶段跑完整 agent 矩阵，但必须提前判断哪些任务能支撑最终矩阵。

### 6.1 最小矩阵形状

`resume_ready_acceptance` 最终至少需要以下受控比较：

1. Provider comparison proof：至少 2 个任务，2 个真实 provider family，同一 scaffold，同一 budget。
2. Scaffold comparison proof：至少 2 个任务，同一真实 provider，同一 budget，比较 `simple_react` 和 `planner_coder_verifier`。
3. Budget comparison proof：至少 2 个任务，同一真实 provider，同一 scaffold，比较 `standard` 和 `constrained`。

因此 preflight 需要提前标记候选是否适合进入以下角色：

- `freeze_ready_only`：适合进入 task set，但不适合作为真实 agent run 核心任务。
- `agent_run_ready`：适合真实 provider agent run。
- `comparison_ready`：适合 provider / scaffold / budget 成对比较。
- `demo_ready`：适合 canonical demo walkthrough，因为任务故事清楚、验证器短、证据链好讲。
- `diagnostic_only`：有研究价值，但不计入 accepted / auditable 最低门槛。
- `blocked`：因为环境、license、visibility、provider 成本或验证器不稳定而阻塞。

通用的 `comparison_ready` 不足以支撑最终验收。preflight 必须按比较轴拆分统计：

- `provider_comparison_ready`：适合在同一 scaffold、同一 budget、同一 source tree、同一 final verifier plan、同一 tool policy、同一 context policy 和同一 environment id 下比较不同真实 provider family。
- `scaffold_comparison_ready`：适合在同一真实 provider、同一 budget 和同一任务条件下比较 `simple_react` 与 `planner_coder_verifier`。
- `budget_comparison_ready`：适合在同一真实 provider、同一 scaffold 和同一任务条件下比较 `standard` 与 `constrained`。

进入 V5 implementation plan 前，至少要有 4 个不同任务进入某一种 comparison-ready 状态，并且 provider、scaffold、budget 三个比较轴各自至少有 2 个候选任务。如果同一个任务同时适合多个比较轴，必须分别记录 `compare_scope_id` 和 `controlled_variables_ref`，不能只用一个宽泛标签代替。

### 6.2 第一轮推荐矩阵候选

第一轮本机 execution probe 优先覆盖 6 个低到中等风险候选：

| 候选标识 | 预期角色 | 原因 |
| --- | --- | --- |
| `spf13/cobra#2356` | `provider_comparison_ready`、`budget_comparison_ready` | Go 任务、issue / PR provenance 清楚、测试命令直接。 |
| `stretchr/testify#1531` | `provider_comparison_ready`、`scaffold_comparison_ready` | Go 任务、语义清楚、适合低成本重复运行。 |
| `pallets/click#3208` | `demo_ready`、`scaffold_comparison_ready` | Python CLI 任务、错误提示行为清楚、适合 5 分钟讲解，也适合 scaffold 对比 fallback。 |
| `pytest-dev/pluggy#646` | `scaffold_comparison_ready`、`budget_comparison_ready` | Python 小仓库、hook 行为清楚、适合 scaffold 对比。 |
| `pelletier/go-toml#1041` | `agent_run_ready`、`provider_comparison_fallback` | Go parser 任务、patch 小，但必须处理 AI session 链接可见性风险。 |
| `yargs/yargs#2332`，如果依赖不稳定则切换到 `sindresorhus/execa#1176` | `agent_run_ready`、`budget_comparison_fallback` | JavaScript / TypeScript 多样性候选，选择依赖安装更稳定者。 |

如果这 6 个候选中少于 4 个达到 `agent_run_ready`，应立即从第二批候选补位，不应等到 V5 Stage 3 才发现矩阵不足。

第一轮还必须尽早降低 SWE-Bench-like anchor 风险。完成 6 个 PR / issue 候选的 metadata 和 source materialization 后，应立刻对 `sphinx-doc__sphinx-7686`、`django__django-11283` 和 `astropy__astropy-14182` 做 source materialization probe，并尽量做 lightweight verifier feasibility probe。不能等所有 PR / issue 候选都乐观通过后才开始验证 3 个 SWE-Bench-like anchors。

## 7. 执行阶段

### Level 0：本机环境、Docker 和工具可用性

目标是确认本机可以执行 V5 preflight。

建议产物：

- `host_tooling_report.json`
- `docker_environment_report.json`
- `docker_platform_probe_report.json`
- `github_cli_report.json`
- `provider_credential_presence_report.json`
- `v5_preflight_evidence_manifest.json`
- `v5_preflight_command_log.jsonl`
- `v5_resume_claim_gate_preflight_report.json`

检查项：

- Docker client 和 server 均可用。
- `linux/arm64` 基础容器可运行。
- 如果候选需要 `linux/amd64`，必须记录 emulation probe 结果。
- GitHub CLI 可用，并且可以读取公开 PR / issue metadata。
- `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`ANTHROPIC_API_KEY` 只记录 present / missing，不记录实际值。
- Level 0 默认只做 provider credential presence，不发起真实 provider API 调用。

通过标准：

- Docker 基础 probe 通过。
- GitHub CLI 能读取至少 1 个公开 PR metadata。
- provider credential presence report 能明确区分 `present`、`missing` 和 `not_supported_by_current_adapter`。
- 如果没有任何真实 provider credential，Level 0 可以继续完成任务来源预检，但必须把 provider 强表述放入 `v5_resume_claim_gate_preflight_report.json` 的 `blocked_claims`。
- 只执行 Level 0 / Level 1 时，`v5_resume_claim_gate_preflight_report.json` 必须使用 `status=partial`，并记录哪些 claim 因为尚未执行 Level 2 到 Level 6 而保持 blocked。

### Level 1：候选 metadata 和 provenance 扫描

目标是不运行 agent，只确认候选来源可以审计。

建议产物：

- `v5_candidate_source_registry.json`
- `v5_candidate_inventory.jsonl`
- `v5_candidate_metadata_probe_report.json`
- `v5_candidate_visibility_risk_report.json`

每个候选至少记录：

- `candidate_id`
- `source_track`
- `repo`
- `repository_url`
- `license`
- `base_commit`
- `merge_commit`
- `issue_url`
- `pull_request_url`
- `fix_commit_url`
- `primary_language_ecosystem`
- `expected_verifier_command`
- `adapter_visible_source_policy`
- `evaluator_only_evidence_policy`
- `initial_visibility_risk`
- `initial_execution_risk`

通过标准：

- 至少 20 个候选有 registry 记录，或者有明确原因说明为什么候选池缩小。
- 至少 12 个候选有完整 PR / issue 或 SWE-Bench-like provenance。
- 至少 8 个 PR / issue 候选具备 accepted / auditable 的初始来源条件。
- 至少 3 个 SWE-Bench-like 候选具备固定 instance id 和 source materialization 计划。

### Level 2：source materialization 和 archive probe

目标是确认候选仓库可以固定到 base revision，并产生可重复 source archive。

建议产物：

- `v5_source_materialization_report.json`
- `v5_source_archive_manifest.json`
- `v5_source_tree_hash_report.json`

检查项：

- clone 或 source fetch 命令显式记录，不依赖 floating default branch。
- base commit 可以 checkout。
- source archive 可以生成 sha256。
- 重复 materialization 的 source tree hash 一致。
- 正式 agent workspace 不包含 evaluator-only patch、上游新增测试、PR diff、official report 或 hidden selector。

通过标准：

- 至少 12 个候选 source materialization 成功。
- 至少 8 个 PR / issue 候选 source materialization 成功。
- 至少 3 个 SWE-Bench-like 候选 source materialization 成功。

### Level 3：dependency、baseline verifier 和 post-patch verifier probe

目标是确认任务不是只在文档上成立，而是在 Docker-based executable repository environment 中可以运行。

建议产物：

- `v5_dependency_probe_report.json`
- `v5_baseline_verifier_probe_report.json`
- `v5_post_patch_verifier_probe_report.json`
- `v5_flaky_probe_report.json`

检查项：

- dependency install 阶段可以联网，但必须记录命令、lockfile、package manager、下载策略和 network policy。
- verifier 阶段默认不联网。
- dependency install 阶段允许的联网命令必须限定在 `git clone`、`git fetch`、`gh`、`pip`、`uv`、`npm`、`pnpm`、`yarn`、`go`、`cargo` 和系统包管理器的显式依赖安装命令。`curl`、`wget`、`git remote add`、额外 `git clone`、下载二进制资产或访问任意 URL 必须进入 `risk_command_hits` 并触发人工审查。
- verifier 阶段如果必须联网，候选默认降级为 `diagnostic_only`，除非有明确例外记录和 network policy ref。
- baseline verifier 的失败必须区分 expected fail-to-pass、setup failure、dependency failure、environment unstable 和 verifier config issue。
- post-patch verifier 必须在干净 workspace 上应用 evaluator-only patch。
- flaky probe 默认重复 3 次；如果有不一致，扩展到 5 次并记录。

通过标准：

- 至少 12 个候选达到 `freeze_ready`。
- 其中至少 8 个来自 PR / issue 构造流程。
- 至少 3 个来自 SWE-Bench-like 锚点。
- 至少 6 个候选被标记为 `agent_run_ready`。
- 至少 4 个候选被标记为 `comparison_ready`。
- `provider_comparison_ready`、`scaffold_comparison_ready` 和 `budget_comparison_ready` 三个比较轴各自至少有 2 个候选任务。

如果第一轮结果低于这些门槛，必须先补跑第二批候选或扩展 GitHub 搜索池，不能直接进入 V5 implementation plan。

### Level 4：visibility、reward source 和 export boundary probe

目标是确认候选任务可以产生训练友好的 evidence，而不是把答案或 evaluator-only material 泄漏给模型。

建议产物：

- `v5_adapter_visible_denylist_scan_report.json`
- `v5_evaluator_only_evidence_manifest.json`
- `v5_training_export_boundary_probe_report.json`
- `v5_reward_source_taxonomy_preflight_report.json`
- `v5_provider_raw_content_leak_probe_report.json`

硬门：

- adapter-visible task input 不得包含上游 patch、PR diff、上游新增测试、fix commit、official resolved status、hidden selector、provider raw response、Claude / Codex session URL 或 credential marker。
- trainable payload 不得包含 final verifier raw output、reward scalar、reward label、post-patch passing log 或 evaluator-only raw evidence。
- provider raw request 和 provider raw response 不得进入 transcript model-visible content、trainable payload、public-safe demo bundle 或 final acceptance docs。
- 如果候选必须依赖敏感或 evaluator-only 信息才能表达任务，必须降级为 `diagnostic_only` 或 `blocked`。

这些报告必须包含机器可检查字段：

- `finding_count`
- `raw_provider_content_leak_count`
- `credential_marker_leak_count`
- `model_visible_leak_count`
- `trainable_payload_leak_count`
- `share_safe_violation_count`
- `evaluator_only_raw_content_copied_count`
- `hidden_verifier_detail_leak_count`
- `ai_session_url_leak_count`

上述计数字段必须全部为 `0`，候选才能进入 `freeze_ready` 或 `agent_run_ready`。扫描范围必须覆盖 adapter-visible task input、候选 metadata、GitHub metadata 摘要、provider smoke report、preflight evidence manifest、preflight command log、后续 public-safe bundle 候选和任何可能进入 final acceptance docs 的摘要文本。

### Level 5：provider API smoke 和成本预算 probe

目标是提前验证真实 provider API 在 RepoHarness 的 adapter 中是否可用，并为 V5 Stage 3 的 run matrix 设预算上限。

建议产物：

- `v5_provider_smoke_report.json`
- `v5_provider_cost_budget_preflight_report.json`
- `v5_provider_error_taxonomy_preflight_report.json`

检查项：

- DeepSeek primary provider smoke。当前代码中 DeepSeek 是唯一可以作为 primary provider 直接运行的真实 provider。
- OpenAI fallback smoke。当前代码中 OpenAI adapter 存在，但 `model.provider=openai` 只允许作为 DeepSeek fallback smoke；在解除 primary 限制并产生真实 primary run evidence 前，不能计入 `resume_ready_acceptance` 所需的第二个真实 provider family。
- Anthropic Claude provider smoke，如果 V5 实现了 adapter；如果当前没有 adapter，只能记录 `adapter_not_implemented_skip`，不能计入真实 provider family。
- 每个 provider family 记录 model alias、max prompt tokens、max output tokens、temperature、timeout、retry policy、structured skip reason、token usage、wall time 和 cost proxy。
- 不保存 raw provider request 或 raw provider response 到 share-safe 产物。
- preflight 默认成本预算为 `max_real_provider_smoke_calls=2`、`max_cost_usd=0.50`、`max_output_tokens=64`、`request_timeout_seconds=60`。达到任一上限后，后续真实 provider 调用必须记录为 `cost_limited_structured_skip`。

通过标准：

- 任务来源 preflight 可以在没有真实 provider smoke 通过时继续，但 provider preflight status 必须是 `blocked_real_provider_preflight`，不能写成 provider gate satisfied。
- `core_acceptance` 的真实 provider 条件最终需要至少 1 个真实 provider family 的实际 agent run evidence。`credential_missing_skip`、`adapter_not_implemented_skip`、`fallback_only_skip` 和 `cost_limited_structured_skip` 都不能替代真实运行证据。
- `resume_ready_acceptance` 前至少 2 个真实 provider family 有 primary provider agent run evidence，并且后续真实 run matrix 使用相同 scaffold 和相同 budget 做成对比较。
- 如果 Anthropic Claude adapter 尚未实现，preflight 只能记录 `adapter_not_implemented_skip`，不能把它计入 2 个真实 provider family。

### Level 6：run-matrix readiness 分类

目标是把任务可行性结果转化成 V5 implementation plan 可以直接使用的矩阵输入。

建议产物：

- `v5_run_matrix_preflight_manifest.json`
- `v5_task_selection_preflight_report.json`
- `v5_comparison_candidate_report.json`
- `v5_demo_candidate_report.json`

每个候选输出以下分类：

- `final_preflight_status`
- `freeze_ready`
- `agent_run_ready`
- `comparison_ready`
- `provider_comparison_ready`
- `scaffold_comparison_ready`
- `budget_comparison_ready`
- `compare_scope_id`
- `comparison_axis`
- `controlled_variables_ref`
- `source_tree_hash`
- `final_verifier_plan_ref`
- `tool_policy_id`
- `context_policy_id`
- `environment_id`
- `scaffold_id`
- `budget_policy_id`
- `provider_family`
- `model_settings_ref`
- `dependency_snapshot_ref`
- `demo_ready`
- `primary_failure_owner`
- `primary_failure_category`
- `secondary_failure_owners`
- `secondary_failure_categories`
- `recommended_v5_role`
- `recommended_budget_tier`
- `recommended_scaffold_set`
- `provider_family_allowlist`
- `provider_family_blocklist`
- `expected_wall_time_sec`
- `expected_cost_proxy`

failure owner 必须使用稳定枚举：

- `model_behavior`
- `environment_unstable`
- `provider_error`
- `verifier_config_issue`
- `dependency_external`
- `task_source_provenance`
- `permission_policy`
- `network_policy`
- `cost_budget`
- `adapter_not_implemented`
- `credential_missing`
- `unknown`

`primary_failure_owner` 选择最接近可修复根因的一项；多原因失败写入 `secondary_failure_owners`，不能把所有问题都折叠成 `unknown`。

failure category 必须使用稳定枚举：

- `expected_fail_to_pass`
- `pass_to_pass_regression`
- `dependency_install_failure`
- `dependency_timeout`
- `image_build_failure`
- `image_build_timeout`
- `source_materialization_failure`
- `source_hash_mismatch`
- `patch_apply_failure`
- `post_patch_verifier_failure`
- `verifier_timeout`
- `flaky_suspected`
- `environment_unstable`
- `network_policy_violation`
- `permission_policy_violation`
- `visibility_leak`
- `provider_error`
- `credential_missing_skip`
- `adapter_not_implemented_skip`
- `fallback_only_skip`
- `cost_limited_structured_skip`
- `unknown`

`primary_failure_category` 选择导致当前候选无法进入下一阶段的直接类别；多原因失败写入 `secondary_failure_categories`。result summary 只能统计这些枚举值，不能临时创造同义字段。

## 8. 第一轮执行边界

为了避免 preflight 变成无界批量实验，第一轮设置以下边界：

- 第一轮低风险执行只做 Level 0 和 Level 1 metadata probe，不发起真实 provider API 调用，不运行 dependency install，不启动 agent run。
- 第一轮完整 execution probe 最多覆盖 6 个 PR / issue 候选，并且同轮必须对 3 个 SWE-Bench-like anchors 做 source materialization probe。
- 每个候选 dependency install timeout 默认为 30 分钟。
- 每个候选 verifier timeout 默认为 20 分钟。
- 每个候选最多 1 次 primary attempt 和 1 次 retry attempt。
- provider smoke 必须等 Level 0 / Level 1 通过、provider registry 与当前 adapter 状态对齐、成本预算报告生成后再执行。
- 不启动真实 agent run，除非 Level 0 到 Level 5 已经通过并且用户明确要求继续执行。
- 不自动清理用户已有 Docker image、volume、仓库工作区或 runs 目录中与本次 preflight 无关的文件。
- 本次 preflight 生成的临时目录必须位于 `runs/v5-task-source-preflight-YYYYMMDDTHHMMSSZ/`。

当前已经允许直接执行的范围只有 Level 0 和 Level 1。下面第 3 步到第 9 步是后续完整 execution probe 的推荐顺序，不属于本次低风险执行范围；只有在 Level 0 / Level 1 产物检查通过并再次确认后，才应继续执行。

第一轮推荐执行顺序：

1. Docker、GitHub CLI 和 provider credential presence probe。
2. 20 个候选的 metadata registry。
3. 6 个第一轮 PR / issue 候选的 source materialization probe。
4. `sphinx-doc__sphinx-7686`、`django__django-11283`、`astropy__astropy-14182` 的 source materialization probe。
5. 通过 source materialization 后，再执行 6 个 PR / issue 候选的 dependency 和 verifier probe。
6. 对已通过 source materialization 的 3 个 SWE-Bench-like anchors 执行 lightweight verifier feasibility probe，或记录为什么只能暂时停在 source materialization。
7. 已通过候选的 visibility 和 export boundary probe。
8. 生成 run-matrix readiness 分类、claim gate preflight report 和 command lineage report。
9. 如果低于门槛，补跑第二批候选或进入 GitHub candidate expansion。

## 9. GitHub candidate expansion 触发条件

只有出现以下任一情况，才启动新的 GitHub CLI 或搜索工具扩展：

1. PR / issue 候选中少于 8 个达到 `freeze_ready`。
2. 总候选中少于 12 个达到 `freeze_ready`。
3. 少于 6 个任务达到 `agent_run_ready`。
4. 少于 4 个任务达到 `comparison_ready`。
5. `provider_comparison_ready`、`scaffold_comparison_ready` 或 `budget_comparison_ready` 任一比较轴少于 2 个候选任务。
6. 候选全部集中在单一生态，无法支撑 V5 简历展示中的多样性叙事。
7. 第一轮候选存在 license、AI session 链接、raw provider content 或 evaluator-only leakage 风险，导致可用任务不足。

扩展规则：

- 优先查找 merged PR，且最好有明确 linked issue。
- 优先选择 patch 规模中等、测试局部、依赖可缓存、无需外部服务的任务。
- 优先选择 Go、Python、JavaScript / TypeScript 小到中型库；Rust 只作为多样性候选，不作为核心数量依赖。
- 不选择需要 GPU、浏览器端到端环境、真实云服务、私有 credential、大型数据库集群或超大二进制资产的任务。
- 每条 GitHub 查询必须记录到 `github_discovery_query_log.jsonl`。
- 每个新增候选必须写入 `v5_candidate_inventory.jsonl`，并通过与 V4 候选相同的 pipeline。

建议 GitHub CLI 查询方向：

```bash
gh search prs "fixes issue tests" --repo spf13/cobra --state closed --merged --limit 10 --json repository,number,title,state,url,closedAt
gh search prs "fixes issue tests" --repo pallets/click --state closed --merged --limit 10 --json repository,number,title,state,url,closedAt
gh search prs "fixes issue tests" --repo pytest-dev/pluggy --state closed --merged --limit 10 --json repository,number,title,state,url,closedAt
gh search prs "fixes issue test" --repo sindresorhus/execa --state closed --merged --limit 10 --json repository,number,title,state,url,closedAt
gh search prs "fixes issue test" --repo yargs/yargs --state closed --merged --limit 10 --json repository,number,title,state,url,closedAt
```

这些命令只作为扩展入口，不能直接把搜索结果计入 accepted task。

## 10. 进入 V5 implementation plan 的门槛

只有满足以下条件，才建议编写并执行 V5 implementation plan：

1. V4 closure baseline 已确认，且 V2 / V3 / V4 acceptance inspect 通过。
2. V5 候选 registry 至少覆盖 20 个候选，或者有审查记录说明为什么少于 20 个仍足够。
3. 至少 12 个候选达到 `freeze_ready`。
4. 至少 8 个 PR / issue 候选达到 `freeze_ready`。
5. 至少 3 个 SWE-Bench-like 锚点达到 `freeze_ready`。
6. 至少 6 个候选达到 `agent_run_ready`。
7. 至少 4 个候选达到 `comparison_ready`。
8. 至少 1 个候选达到 `demo_ready`。
9. `provider_comparison_ready`、`scaffold_comparison_ready` 和 `budget_comparison_ready` 三个比较轴各自至少有 2 个候选任务。
10. provider smoke 对 `core_acceptance` 的真实 provider 条件给出通过、`blocked_real_provider_preflight` 或明确 V5 实施阶段要补的 adapter work；structured skip 不能替代真实 provider run evidence。
11. provider smoke 对 `resume_ready_acceptance` 的 2 个真实 provider family 条件给出通过、阻塞或明确 V5 实施阶段要补的 adapter work。
12. 所有 candidate artifact 都记录 path、sha256、size_bytes、生成命令、visibility policy、producer command 和 inspect command。
13. 所有失败都有 `failure_owner` 和 `failure_category`。
14. `v5_preflight_evidence_manifest.json`、`v5_preflight_command_log.jsonl`、`v5_preflight_command_lineage_report.json` 和 `v5_resume_claim_gate_preflight_report.json` 已生成。

如果只满足 `core_acceptance` 相关条件，不满足 `resume_ready_acceptance` 条件，则 V5 implementation plan 必须把强简历表述继续放在 blocked claims 中。

## 11. 预检通过后的执行决策

当前建议执行决策如下：

1. 使用 V4 已有候选池启动本机 preflight。
2. 第一轮先执行 Level 0 和 Level 1 的低风险本机检查，确认 Docker、GitHub CLI、provider credential presence、candidate registry、evidence manifest 和 command log 都能生成。
3. 第一轮完整 execution probe 只测试 6 个低到中等风险 PR / issue 候选，同时尽早测试 3 个 SWE-Bench-like anchors 的 source materialization。
4. 如果 6 个 PR / issue 候选中至少 4 个达到 `agent_run_ready`，且 3 个 SWE-Bench-like anchors 至少达到 source materialization 成功，再继续测试剩余第一批 PR / issue 候选和 SWE-Bench-like verifier feasibility。
5. 如果第一轮低于门槛，先使用 V4 第二批备选候选补位。
6. 只有 V4 第二批候选仍不足时，才启动新的 GitHub candidate expansion。

这个决策可以最大化利用已经审查过的 V4 候选，减少 V5 进入实施前的不确定性，同时避免为了扩大候选池而引入新的 provenance 和 license 风险。
