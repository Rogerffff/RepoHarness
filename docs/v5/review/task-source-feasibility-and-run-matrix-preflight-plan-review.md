# RepoHarness V5 Task Source Feasibility And Run-Matrix Preflight Plan Review

## 0. 文档定位

本文记录 `docs/v5/task-source-feasibility-and-run-matrix-preflight-plan.md` 的 subagent 审查、修订处理和第一轮低风险本机预检结果。

本轮审查目标不是证明 V5 已经完成，而是判断：

1. V4 已有候选池是否足够启动 V5 task source preflight。
2. preflight 计划是否足够约束 provider / scaffold / budget run matrix，避免提前使用强简历表述。
3. 是否可以在本机执行低风险 Level 0 / Level 1 预检。

## 1. Subagent 审查分工

本轮设置三个审查角度：

1. 候选池充分性和简历展示价值审查。
2. Docker、GitHub CLI、provider API smoke、成本预算和网络风险审查。
3. V5 acceptance inputs、evidence integrity、command lineage、claim gate 和 failure taxonomy 审查。

三位审查者的共同结论是：

- V4 已有 5 个 SWE-Bench-like 候选、8 个第一批 PR / issue 强候选和 7 个第二批 PR / issue 备选候选，数量上足够启动本机 preflight。
- 这个结论只表示“足够启动测试”，不表示这些候选已经可以计入 V5 accepted / auditable task definitions。
- 修订后可以直接执行低风险 Level 0 / Level 1。
- 当前仍不能执行真实 provider API smoke、dependency install、source materialization、verifier、agent run 或任何 `resume_ready_acceptance` 声明。

## 2. 主要审查问题和处理结果

| 优先级 | 问题 | 处理结果 |
| --- | --- | --- |
| P1 | 初稿把 Level 3 freeze-ready 门槛写成至少 8 个候选，低于 V5 至少 12 个 accepted / auditable task definitions 的目标。 | 已改为至少 12 个 `freeze_ready`、至少 8 个 PR / issue、至少 3 个 SWE-Bench-like anchors、至少 6 个 `agent_run_ready`、至少 4 个 `comparison_ready`。 |
| P2 | 初稿容易把 20 个候选库存误读为 20 个可计数任务。 | 已明确“足够”只表示候选库存足够启动测试，所有候选仍必须通过 V5 source materialization、verifier、flaky、visibility、artifact manifest 和 command lineage gate。 |
| P2 | SWE-Bench-like anchors 进入测试太晚。 | 已要求第一轮在 6 个 PR / issue 候选之后立刻测试 `sphinx-doc__sphinx-7686`、`django__django-11283` 和 `astropy__astropy-14182` 的 source materialization。 |
| P2 | `comparison_ready` 没有按 provider、scaffold、budget 三个比较轴拆分。 | 已新增 `provider_comparison_ready`、`scaffold_comparison_ready`、`budget_comparison_ready`，并要求三个轴各自至少 2 个候选任务。 |
| P1 | preflight artifact 缺少可进入 acceptance inputs 的 evidence manifest 和 command lineage。 | 已新增 `v5_preflight_evidence_manifest.json`、`v5_preflight_command_log.jsonl` 和 `v5_preflight_command_lineage_report.json`。 |
| P1 | structured skip 被写成可能满足 core provider 条件。 | 已明确 structured skip 只能解释阻塞原因，不能替代真实 provider run evidence。 |
| P1 | OpenAI 被写成独立 primary provider smoke。 | 已对齐当前代码状态：DeepSeek 是 primary provider，OpenAI 当前只能作为 DeepSeek fallback，Anthropic Claude 未实现 adapter。 |
| P2 | provider 成本预算缺少具体上限。 | 已新增 `max_real_provider_smoke_calls=2`、`max_cost_usd=0.50`、`max_output_tokens=64` 和 `request_timeout_seconds=60`。 |
| P2 | network / risky command policy 不够具体。 | 已明确 dependency install 阶段允许命令和 `curl`、`wget`、`git remote add`、额外 `git clone` 等风险命令记录规则。 |
| P2 | visibility 和 provider raw content leak gate 不是机器可检查字段。 | 已新增 finding count、raw provider content leak count、credential marker leak count、model-visible leak count、trainable payload leak count 等字段。 |
| P2 | claim gate 缺少 preflight 前置产物。 | 已新增 `v5_resume_claim_gate_preflight_report.json`，并要求 Level 0 / Level 1 生成 `status=partial`。 |
| P2 | failure owner 和 failure category taxonomy 不完整。 | 已新增稳定 `failure_owner` 和 `failure_category` 枚举。 |
| P2 | GitHub CLI merged 查询语法不兼容。 | 已改为 `gh search prs ... --state closed --merged ...`。 |

## 3. 修订后审查结论

修订后，三位审查者都允许执行低风险 Level 0 / Level 1 本机预检。

允许执行的范围：

- 本机工具版本和基础可用性检查。
- Docker client / server 状态检查，不自动拉取大型镜像。
- GitHub CLI 版本、认证状态和公开 PR metadata 读取。
- `OPENAI_API_KEY`、`DEEPSEEK_API_KEY`、`ANTHROPIC_API_KEY` 的 present / missing / adapter support 状态检查，不读取或打印凭证值。
- 20 个候选的 metadata registry 和 provenance 扫描。
- 初始化 preflight evidence manifest、command log、command lineage report 和 partial claim gate report。

明确禁止的范围：

- 不调用真实 provider API。
- 不安装依赖。
- 不 clone 或 materialize source tree。
- 不运行 verifier。
- 不启动 agent run。
- 不宣称 `core_acceptance`、`resume_ready_acceptance` 或任何强简历表述已经成立。

## 4. 第一轮低风险本机预检结果

执行目录：

```text
runs/v5-task-source-preflight-20260505T080756Z/
```

关键结果：

| 项目 | 结果 |
| --- | --- |
| `host_tooling_status` | `passed` |
| `docker_status` | `passed` |
| `github_status` | `passed` |
| provider API 调用 | `false` |
| dependency install | `false` |
| agent run | `false` |
| 候选总数 | 20 |
| PR / issue 候选数 | 15 |
| SWE-Bench-like 候选数 | 5 |
| GitHub PR metadata probe | 15 / 15 成功 |
| low-risk provider / workspace unit tests | 45 passed |
| command log entries | 24 |
| evidence manifest artifacts | 61 |
| command lineage status | `passed` |
| claim gate status | `partial` |

生成的关键产物：

- `runs/v5-task-source-preflight-20260505T080756Z/preflight_level0_level1_summary.json`
- `runs/v5-task-source-preflight-20260505T080756Z/setup/host_tooling_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/setup/docker_environment_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/setup/github_cli_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/setup/provider_credential_presence_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/inventory/v5_candidate_source_registry.json`
- `runs/v5-task-source-preflight-20260505T080756Z/inventory/v5_candidate_inventory.jsonl`
- `runs/v5-task-source-preflight-20260505T080756Z/inventory/v5_candidate_metadata_probe_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/inventory/v5_candidate_visibility_risk_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/claims/v5_resume_claim_gate_preflight_report.json`
- `runs/v5-task-source-preflight-20260505T080756Z/logs/v5_preflight_command_log.jsonl`
- `runs/v5-task-source-preflight-20260505T080756Z/manifests/v5_preflight_evidence_manifest.json`
- `runs/v5-task-source-preflight-20260505T080756Z/manifests/v5_preflight_command_lineage_report.json`

## 5. 当前判断

当前判断是：V4 文档里的强候选足够满足 V5 第一轮 preflight 的启动要求，不需要在进入 Level 2 前先扩展 GitHub 搜索池。

但当前还没有完成 V5 最终简历成果。原因是本轮只完成了 Level 0 / Level 1：

- 候选还没有 source materialization。
- 候选还没有 dependency、baseline verifier、post-patch verifier 和 flaky probe。
- 还没有真实 provider agent run evidence。
- 还没有 provider / scaffold / budget comparison proof。
- 还没有 export result pack。
- `v5_resume_claim_gate_preflight_report.json` 仍然是 `status=partial`。

下一步建议先执行 Level 2：

1. 对 `spf13/cobra#2356`、`stretchr/testify#1531`、`pallets/click#3208`、`pytest-dev/pluggy#646`、`pelletier/go-toml#1041`、`yargs/yargs#2332` 做 source materialization probe。
2. 同轮对 `sphinx-doc__sphinx-7686`、`django__django-11283`、`astropy__astropy-14182` 做 source materialization probe。
3. 只有 Level 2 通过后，再进入 dependency、verifier、flaky 和 visibility probe。
