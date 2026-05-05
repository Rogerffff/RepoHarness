# RepoHarness V5 执行 Agent Prompt

你现在负责实现 RepoHarness 第五版（V5）。请严格按照当前仓库中的 V5 范围文档、实施计划、预检计划、审查记录、V4 最新验收证据和既有设计文档推进。

仓库路径：

```text
/Users/roger/Desktop/claude-code
```

## 正式实施基线

V5 原始正式实施 baseline commit 是：

```text
9fd7007 docs: add V5 implementation baseline
```

该 commit 必须包含当前已经审查过的 V5 文档，至少包括：

- `docs/v5/scope-and-roadmap.md`
- `docs/v5/implementation-plan.md`
- `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md`
- `docs/v5/review/scope-review.md`
- `docs/v5/review/task-source-feasibility-and-run-matrix-preflight-plan-review.md`

如果用户在任务消息中提供了晚于 `9fd7007` 的 V5 文档修订提交，例如用于澄清 V4 immutable baseline gate 时序的提交，开始前还必须确认当前 `HEAD` 包含该修订提交。没有这个确认时，不要凭记忆沿用旧 prompt。

开始前必须确认当前 `HEAD` 包含 V5 原始 baseline：

```bash
git merge-base --is-ancestor 9fd7007 HEAD
```

同时必须确认 V4 closure commit 仍然是当前分支祖先：

```bash
git merge-base --is-ancestor e0da89c HEAD
```

如果任一命令失败，或者 V5 文档缺失、未跟踪、被删除、被意外修改，请停止实现并报告，不要凭记忆补写。

## 开始前必须检查

开始实现前，请先执行并记录结果：

```bash
pwd
git status --short
git log -1 --oneline
git status --short -- docs/v5
git diff --name-status -- docs/v5
git ls-tree -r --name-only 9fd7007 docs/v5
git merge-base --is-ancestor 9fd7007 HEAD
git merge-base --is-ancestor e0da89c HEAD

PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable

docker version
docker context show
docker info
docker info --format '{{json .MemTotal}}'
docker run --rm hello-world
docker run --rm alpine:3.20 uname -m
docker run --rm alpine:3.20 sh -lc 'grep MemTotal /proc/meminfo'
docker run --rm --platform linux/amd64 alpine:3.20 uname -m
```

这些 V4 检查是 V5 preimplementation baseline gate，只能在 V5 修改 `src/`、`tests/` 或 V4 doc-sync bundle 已绑定文档之前执行。通过结果必须写入 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和对应 command log。进入 V5 实现后，不得在同一个已经包含 V5 源码变更的工作区反复要求旧 V4 doc-sync bundle 的 `--assert-immutable` 通过；旧 V4 bundle 绑定的是 V4 验收当时的文件字节，V5 源码变更导致旧哈希漂移是预期现象。

如果确实需要重新运行 V4 doc-sync bundle immutable inspect，必须使用精确还原到 V4 doc-sync bundle 绑定字节的独立 worktree 或快照，并把结果作为 Stage 0 baseline proof 的补充证据。不要在已经写入 V5 代码的主工作区用旧 V4 bundle 作为阶段门。

如果工作区存在与当前阶段无关的既有改动，不要删除、不要回滚、不要提交。如果这些改动导致 V5 开始前的 V4 baseline、V2 / V3 regression 或 V5 当前阶段验收失败，必须停止实现并报告，不能擅自修复无关改动。

哈希敏感测试运行期间不得继续编辑 `src/`、`tests/` 或相关文档。某些测试会先计算源码哈希，再在后续 inspect 中复查；测试期间源码字节变化会制造 drift。

## 必须先阅读的文档

请先阅读这些文档，并以它们为实现依据：

1. `AGENTS.md`，如果存在 `AGENT.md` 也一并阅读。
2. `docs/v5/scope-and-roadmap.md`
3. `docs/v5/implementation-plan.md`
4. `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md`
5. `docs/v5/review/scope-review.md`
6. `docs/v5/review/task-source-feasibility-and-run-matrix-preflight-plan-review.md`
7. `docs/v4/final-acceptance.md`
8. `docs/v4/walkthrough.md`
9. `docs/v4/implementation-plan.md`
10. `docs/v4/review/implementation/08-final-acceptance-review.md`
11. `docs/00-reading-guide.md`
12. `docs/01-project-positioning-and-requirements.md`
13. `docs/02-system-architecture.md`
14. `docs/03-agent-loop-and-message-protocol.md`
15. `docs/04-tool-system-and-orchestration.md`
16. `docs/05-workspace-sandbox-and-permissions.md`
17. `docs/06-task-dataset-and-environment-adapters.md`
18. `docs/07-verifier-reward-and-evaluation.md`
19. `docs/08-trajectory-store-and-training-export.md`
20. `docs/09-agent-scaffolds-and-multi-agent.md`
21. `docs/10-context-session-and-failure-diagnostics.md`
22. `docs/11-object-model-config-and-data-flow.md`
23. `docs/12-resume-narrative-and-demo-artifacts.md`
24. `docs/13-agentic-technical-report-reading-map.md`
25. `reference/claude-code-typescript-src/AGENTS.md`

实现优先级最高的是：

- `docs/v5/implementation-plan.md`
- `docs/v5/scope-and-roadmap.md`
- `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md`
- `docs/v5/review/scope-review.md`
- `docs/v5/review/task-source-feasibility-and-run-matrix-preflight-plan-review.md`
- 当前阶段相关设计文档

V4 文档是可信 closure baseline 和兼容性参考，不能覆盖 V5 implementation plan。V1 到 V3 文档只作为历史和回归参考，不能覆盖 V4 最新验收状态和 V5 实施计划。

## V5 核心定位

RepoHarness 是一个面向软件工程智能体训练和评测的 Harness，目标是让真实或半真实仓库任务产生可执行、可审计、可导出的训练轨迹。

V5 不是新增一个宽泛功能大版本，也不是复刻 Claude Code、Codex、OpenHands、SWE-agent 或官方 SWE-Bench harness。V5 的目标是在 V4 已经具备的可执行、可审计、可导出闭环之上，交付一个面向简历和面试展示的最终结果包。

V5 必须让面试官能清楚看到：

1. 任务来自真实或半真实软件工程场景，而不是只来自玩具 fixture。
2. 每条真实 agent run 都有固定任务、固定源码、固定 verifier、固定工具策略和可追溯 trajectory。
3. provider、scaffold 和 budget 的比较只在受控变量一致时成立。
4. 训练导出样本能够区分 trainable、diagnostic-only、blocked、mock / replay 和 stress records。
5. 所有关键结论都能通过 path、sha256、command log、inspect 命令和 acceptance bundle 追溯。

禁止把 V5 表述为：

- 完整 SWE-Bench Lite 或 SWE-Bench Verified 榜单复现。
- 公开 leaderboard 可比结果。
- 生产级安全沙箱。
- 分布式强化学习 rollout 集群。
- 完整 Claude Code / Codex 产品复刻。
- 已经训练出 coding agent。
- reward model 训练或强化学习算法训练。

## V4 最新 closure baseline

V4 最新 closure commit 是：

```text
e0da89c test: refresh V4 acceptance evidence after hardening
```

引用 V4 最新状态时，必须使用：

```text
runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json
runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json
runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json
runs/v4-final-rerun-20260504T194758Z/acceptance/final_acceptance_command_log_doc_sync_20260505T075410Z.jsonl
```

原始 `acceptance_bundle_manifest.json` 只保留为历史 bundle，不能作为 V5 latest V4 baseline。

## V5 preflight 输入

V5 implementation 可以使用当前已经完成的本机 preflight 证据作为输入，但不能把这些 preflight 产物直接计为 V5 final accepted task、真实 provider run 或训练样本。

当前 preflight 输入目录：

```text
runs/v5-flaky-visibility-run-matrix-freeze-20260505T130000Z/
```

关键事实：

- 初始冻结候选数量：10 个。
- PR / issue 候选：6 个。
- SWE-Bench-like anchor 候选：4 个。
- flaky probe：10 / 10 stable，0 个 flaky suspected。
- visibility probe：passed，0 个 model-visible leak，0 个 share-safe violation。
- agent-run-ready：10 个。
- comparison-ready：9 个。
- provider comparison ready：4 个。
- scaffold comparison ready：4 个。
- budget comparison ready：4 个。
- planned matrix cells：24 个。
- 本轮是否执行真实 agent run：否。
- 本轮是否调用 provider API：否。

当前 10 个候选还没有满足 V5 core acceptance 的严格任务库存门：

```text
至少 12 个 accepted / auditable task definitions
至少 8 个 PR / issue flow tasks
至少 3 个 SWE-Bench-like anchor tasks
```

因此 Stage 2B 默认必须补齐 2 个 PR / issue 候选，或者通过正式范围变更修改 scope、preflight plan 和 review 记录。不能只在 implementation plan 中悄悄降低标准。

## V5 两层验收口径

V5 使用两层验收：

1. `core_acceptance`：证明 V5 的证据完整性、任务冻结、最小真实运行、训练导出和验收 bundle 都成立。
2. `resume_ready_acceptance`：在 `core_acceptance` 基础上，额外通过多真实 provider、真实可比较 preference pair、share-safe demo bundle 和 canonical demo walkthrough 的声明门。

如果只通过 `core_acceptance`，最终文档和简历不得使用以下强表述：

- multi-provider agent runs
- controlled multi-provider comparison
- preference export completed
- interview-grade evaluation pack 的完整强表述
- resumable export stress tests

这些表述是否允许使用，必须由 `v5_resume_claim_gate_report.json` 决定。

## V5 全局不变量

### Evidence 时序不变量

V5 evidence integrity 必须分成三层：

1. `pre_acceptance_evidence_integrity`：只检查 V5 acceptance inputs 生成之前已经存在的 evidence。
2. `acceptance_report_reference_integrity`：由 `inspect-v5-acceptance` 在 acceptance report 生成之后检查。
3. `acceptance_bundle_command_lineage_integrity`：由 `inspect-acceptance-bundle --assert-immutable` 在 acceptance bundle 构建之后检查。

不得让 pre-acceptance evidence integrity report 预先引用尚未生成的 acceptance report。不得让 V5 acceptance report 把 post-report inspect outputs、bundle final outputs 或 doc-sync outputs 当作自己的输入证据。

Acceptance inputs 只能绑定 acceptance report 生成之前已经存在的 pre-report command log。Post-report inspect command entries、pre-bundle command log、bundle build entry、final command log 和 doc-sync command log 必须按后续时序进入 acceptance bundle 或 doc-sync bundle，不能提前进入 acceptance report 输入。

`V5_PRE_BUNDLE_COMMAND_LOG` 可以作为 `build-v5-acceptance-bundle` 的显式输入，但不能作为 acceptance report 输入。

### 可见性和污染边界不变量

以下内容不得进入 adapter-visible task input、prepared messages、model-visible transcript、trainable payload、public-safe demo bundle 或 final acceptance docs：

- evaluator-only evidence
- gold patch
- raw test patch
- hidden test selector
- official harness report
- official resolved status
- raw PR body
- raw PR diff
- review comment
- fix commit URL
- merge commit URL
- provider raw request
- provider raw response
- Authorization marker
- provider credential marker
- credential path
- final verifier raw output
- reward scalar
- reward label
- post-patch passing log
- Claude / Codex / LLM coding session URL

Reward scalar 和 reward label 只能出现在非模型可见的 structured reward、RewardMetadata 或 audit-only metadata 字段中，并且必须通过 allowlist path 和 visibility policy 检查。

### Final verifier 权威性不变量

Final verifier 是 accepted、rejected、inconclusive 和 pass-to-pass regression 的权威来源。Patch quality、reward audit、LLM judge audit-only note、failure taxonomy、demo card 和 result summary 都不能把 final verifier 未接受的 run 提升为 accepted。

### Provider / scaffold / budget 比较不变量

任何比较结论都必须声明 `comparison_axis`、`controlled_variables`、`compared_cells` 和 `comparison_validity`。

Provider 比较必须固定 task、source tree、final verifier plan、tool policy、context policy、scaffold、budget 和 environment id。Scaffold 比较必须固定 task、source tree、final verifier plan、tool policy、context policy、provider、budget 和 environment id。Budget 比较必须固定 task、source tree、final verifier plan、tool policy、context policy、provider、scaffold 和 environment id。

Mock、replay、fallback success、credential missing skip、adapter not implemented skip 和 cost-limited structured skip 都不得混入真实 provider accepted rate。

## V5 实现阶段

必须严格按照 `docs/v5/implementation-plan.md` 的阶段顺序推进：

0. Stage 0：V4 closure baseline 和 V5 preflight 输入冻结。
1. Stage 1：V5 schema、inspect skeleton 和 evidence integrity gate。
2. Stage 2A：接入当前 10 个初始候选。
3. Stage 2B：补齐 2 个 PR / issue 候选，或通过正式范围变更修改严格任务库存门。
4. Stage 3A：实现 provider registry、credential gate、cost budget 和 provider smoke。
5. Stage 3B：执行最小真实 provider agent runs，先满足 core acceptance 的真实 provider 下限。
6. Stage 3C：如果第二个真实 provider family 可用，执行 resume-ready provider comparison；如果不可用，生成 blocked claim。
7. Stage 4：从 Stage 3 runs 生成 export result pack，并重新生成最终 claim gate 的 export / preference 部分。
8. Stage 5：生成 demo card、public-safe bundle、result summary 和 interview result pack。
9. Stage 6：构建 V5 acceptance inputs、acceptance report、acceptance bundle 和 post-acceptance docs。

Stage 0 不能跳过。不能先做 provider run matrix、task adapter、export pack 或 demo artifacts，再回头冻结 V5 implementation inputs。

## CLI / Python API 落地要求

V5 的每个关键机器产物都必须有明确 builder。Builder 不得扫描 latest run，不得覆盖已有输出；除非命令名明确是 update 或 append，默认都必须支持 `--fail-if-output-exists`。

至少需要实现或规划以下 CLI：

```bash
repo-harness build-v5-preimplementation
repo-harness build-v5-schema-fixtures
repo-harness build-v5-evidence-integrity
repo-harness build-v5-task-set
repo-harness build-v5-supplemental-pr-issue-candidates
repo-harness merge-v5-task-set
repo-harness build-v5-provider-gate
repo-harness build-v5-provider-cost-budget
repo-harness build-v5-run-matrix
repo-harness run-v5-run-matrix
repo-harness build-v5-comparison-reports
repo-harness build-v5-export-pack
repo-harness build-v5-demo-artifacts
repo-harness build-v5-interview-result-pack
repo-harness build-v5-acceptance-inputs
repo-harness build-v5-acceptance-report
repo-harness build-v5-pre-bundle-command-log
repo-harness build-v5-acceptance-bundle
repo-harness plan-acceptance-bundle-inspect-entry
repo-harness build-v5-final-command-log
```

Stage 6 doc sync 必须支持：

```bash
repo-harness build-v5-acceptance-bundle --doc-sync-from-bundle V5_ACCEPTANCE_BUNDLE
```

每个 builder 的最低实现要求：

- 输入必须全部显式传入路径，不能隐式读取 latest run。
- 输出目录必须由 `--output-dir` 或 `--output` 显式指定。
- 输出已经存在时默认失败。
- 命令必须写入 command log entry，包含 argv、cwd、input_refs、output_refs、started_at、finished_at、exit_code、stdout / stderr sha256。
- 对应 inspect 命令必须能在不重新执行 builder 的情况下检查输出。

## V5 必须覆盖的 inspect 命令

至少必须实现或使用：

```bash
repo-harness inspect-v5-preimplementation V5_PREFLIGHT_INPUT_BINDING --assert-complete
repo-harness inspect-v5-evidence-integrity V5_PRE_ACCEPTANCE_EVIDENCE_INTEGRITY_REPORT --assert-complete
repo-harness inspect-v5-task-set V5_TASK_SET_MANIFEST --assert-complete
repo-harness inspect-v5-task-visibility V5_TASK_VISIBILITY_SCAN_REPORT --assert-clean
repo-harness inspect-v5-run-matrix V5_RUN_MATRIX_MANIFEST --assert-complete
repo-harness inspect-v5-provider-gate V5_PROVIDER_CREDENTIAL_GATE_REPORT --assert-consistent
repo-harness inspect-v5-export-pack V5_EXPORT_RESULT_PACK_MANIFEST --assert-clean
repo-harness inspect-v5-demo-artifacts V5_RESUME_ARTIFACT_INDEX --assert-share-safe
repo-harness inspect-v5-inputs V5_ACCEPTANCE_INPUTS --assert-complete
repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-core-complete
repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-resume-ready
```

如果保留 `inspect-v5-acceptance --assert-complete`，它必须等价于 `--assert-resume-ready`。不能让 `--assert-complete` 只检查 core acceptance。

所有 inspect 命令必须显式接收输入路径，不能读取当前目录、默认 latest run 或环境变量来猜测输入。

## Stage 6 final acceptance 口径

Stage 6 必须生成：

- `v5_acceptance_inputs.json`
- `v5_acceptance_report.json`
- `v5_acceptance_report_reference_integrity_report.json`
- `v5_acceptance_bundle_manifest.json`
- `v5_acceptance_bundle_command_lineage_report.json`
- `v5_stage6_command_log_draft.jsonl`
- `v5_pre_bundle_command_log.jsonl`
- `build_v5_acceptance_bundle_command_log_entry.json`
- `inspect_acceptance_bundle_command_log_entry.json`
- `v5_final_acceptance_command_log.jsonl`
- `v5_final_acceptance_pretest_report.json`
- `v5_acceptance_bundle_manifest_doc_sync_*.json`，如果 post-bundle 文档发生更新。
- `v5_final_acceptance_command_log_doc_sync_*.jsonl`，如果 post-bundle 文档发生更新。

Stage 6 的当前工作区检查必须以当前 V5 代码为准：

```bash
PATH=.venv/bin:$PATH python -m compileall src
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v3-acceptance runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json --assert-immutable
PATH=.venv/bin:$PATH repo-harness inspect-v5-preimplementation V5_PREFLIGHT_INPUT_BINDING --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-inputs V5_ACCEPTANCE_INPUTS --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-core-complete
PATH=.venv/bin:$PATH repo-harness inspect-v5-acceptance V5_ACCEPTANCE_REPORT --assert-resume-ready
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle V5_ACCEPTANCE_BUNDLE --assert-immutable
```

Stage 6 不得在已经包含 V5 源码变更的当前工作区重新要求以下旧 V4 命令通过：

```bash
PATH=.venv/bin:$PATH repo-harness inspect-v4-inputs runs/v4-final-rerun-20260504T194758Z/v4_acceptance_inputs.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-v4-acceptance runs/v4-final-rerun-20260504T194758Z/acceptance/v4_acceptance_report.json --assert-complete
PATH=.venv/bin:$PATH repo-harness inspect-acceptance-bundle runs/v4-final-rerun-20260504T194758Z/acceptance/acceptance_bundle_manifest_doc_sync_20260505T075410Z.json --assert-immutable
```

这些旧 V4 命令只能作为 Stage 0 preimplementation baseline proof 的来源，或在独立还原快照中作为补充证明运行。

## core_acceptance 最低完成

`core_acceptance` 必须满足：

- 全量测试通过。
- V2 / V3 当前兼容性 inspect 通过。
- V4 closure baseline 的 immutable inspect 通过结果已经由 Stage 0 的 `v5_baseline_check_report.json`、`v5_preflight_input_binding.json` 和 command log 绑定，并由 `inspect-v5-preimplementation` 复核。
- V5 pre-acceptance evidence integrity inspect 通过。
- V5 task set inspect 通过。
- 至少 12 个 accepted / auditable task definitions，除非范围文档经过正式修订。
- 至少 8 个 accepted / auditable task definitions 来自 PR / issue flow，除非范围文档经过正式修订。
- 至少 3 个 accepted / auditable task definitions 来自 SWE-Bench-like anchors。
- V5 run matrix inspect 通过。
- 至少 6 个任务产生真实 agent run evidence。
- 至少 4 个任务进入 comparison proof。
- 至少 1 个真实 provider family 有实际 agent run evidence。
- V5 provider cost budget report 通过检查。
- V5 export pack inspect 通过。
- V5 acceptance report inspect 通过。
- 至少 1 个合规 SFT、reinforcement learning rollout 和 failure dataset 样本。
- 至少 1 个 diagnostic-only 样本，并由 `inspect-v5-export-pack` 证明没有进入 trainable payload。
- 至少 1 个 blocked export 样本，并由 `inspect-v5-export-pack` 记录阻断原因、failure owner 和 failure category。
- Preference pair 要么真实可比较，要么有完整 blocked report，并在 claim gate 中禁用 preference export 强表述。
- 0 个 trainable payload contamination finding。
- 0 个 evaluator-only evidence model-visible finding。
- 0 个 acceptance report unbound critical evidence finding。
- 0 个 provider credential raw value 泄漏 finding。
- 0 个 provider raw request / response 进入 model-visible content、trainable payload、public-safe demo bundle 或 final acceptance docs。
- 0 个 risky command 或 network policy finding 进入模型可见训练内容。
- Result summary 分列 real provider trainable records、mock / replay records、diagnostic records、blocked records 和 synthetic-safe stress records。
- V5 acceptance bundle immutable inspect 通过。

## resume_ready_acceptance 简历完成

`resume_ready_acceptance` 额外要求：

- 至少 2 个真实 provider family，各有至少 2 条真实 agent run records。DeepSeek API 和 OpenAI API 的使用方式必须参考 `reference/deepseek_api.md` 以及仓库已有 provider 抽象。
- Provider comparison 满足 `2 个任务 x 2 个真实 provider family x 同一 scaffold x 同一 budget`。
- Scaffold comparison 至少覆盖 2 个任务。
- Budget comparison 至少覆盖 2 个任务。
- 至少 1 个真实可比较 preference pair 通过 compare scope gate。
- Canonical demo walkthrough 和 public-safe demo bundle 通过 share-safe 检查。
- `v5_resume_claim_gate_report.json` 明确允许使用完整强表述。

如果只有 1 个真实 provider family 有实际运行，可以争取 core_acceptance，但不得使用 `multi-provider agent runs` 或完整 `controlled multi-provider comparison` 表述。

如果没有真实可比较 preference pair，可以争取 core_acceptance，但必须生成 `v5_preference_pair_blocked_report.json`，不得写 `preference export completed`。

如果没有任何真实 provider family 实际运行，V5 简历目标应标记为 blocked。

## 每个阶段的工作闭环

每完成一个阶段，必须只实现当前阶段范围，保护 V2 / V3 / V4 replay、provider、workspace、trajectory、export、inspect 和 acceptance 兼容行为，运行阶段验证和必要回归测试，生成阶段机器产物，更新 `docs/v5/implementation-log/`，优先安排 subagent 做只读审查并把审查记录保存到 `docs/v5/review/implementation/`。

如果当前环境不支持 subagent，必须执行等价的独立只读自审，并把审查维度、发现、修复记录和是否允许进入下一阶段写入 `docs/v5/review/implementation/`。不能因为没有 subagent 工具而跳过阶段审查。

审查发现中优先级为 P1 或 P2 的问题必须修复后才能进入下一阶段。审查发现中优先级为 P3 的问题如果可以在不扩大阶段范围的情况下修复，则自行修复；否则记录为后续项。

每个阶段通过并产生实现、测试、机器产物或文档改动后创建一个清晰 commit；如果阶段只产生阻塞报告，也应提交报告；如果没有任何可提交文件，阶段日志必须说明原因。

阶段日志必须记录目标、实现内容、主要修改文件、新增或更新的 schema、新增或更新的 inspect 命令、新增或更新的 tests、机器产物 path 和 sha256、验证命令、验证结果、正例证据、负例证据、允许降级项、禁止降级项、已知限制、是否偏离设计文档、subagent 或等价自审结论，以及是否可以进入下一阶段。

## Git 规则

开始前和每次提交前必须执行：

```bash
git status --short
git diff --cached --check
git diff --check -- <本阶段相关路径>
```

`git diff --cached --check` 是提交硬门槛。`git diff --check -- <本阶段相关路径>` 是本阶段硬门槛。全局 `git diff --check` 可以记录；如果失败来自无关既有改动，只记录，不修复、不提交。

只 stage 当前阶段相关文件，不要提交无关旧改动或未跟踪材料。不要使用 `git reset --hard`、`git checkout --` 或其他会丢失用户改动的命令，除非用户明确要求。

每个阶段通过并产生实现、测试、机器产物或文档改动后创建一个清晰 commit。不要 push，除非用户明确要求。

## 最终回答用户时必须说明

最终向用户汇报时，请用清晰详细的中文说明：

- 完成了哪些阶段。
- 每个阶段对应 commit。
- 运行了哪些验证命令。
- 关键机器产物路径。
- subagent 或等价自审结论。
- 是否存在 deferred enhancement。
- 是否存在允许降级项、禁止降级项或残余风险。
- V2 regression 是否通过。
- V3 acceptance inspect 是否通过。
- V3 acceptance bundle inspect 是否通过。
- V4 baseline proof 是否已在 Stage 0 通过并由 `v5_baseline_check_report.json` 绑定。
- 是否错误地在 V5 源码变更后重跑旧 V4 doc-sync bundle immutable inspect；如果发生过，必须说明该结果不能作为 V5 阶段门。
- V5 core_acceptance 是否通过。
- V5 resume_ready_acceptance 是否通过。
- V5 acceptance bundle 或 doc-sync bundle 是否通过 immutable inspect。
