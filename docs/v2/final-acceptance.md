# RepoHarness V2 Final Acceptance

## 验收结论

RepoHarness 第二版已经完成十五个阶段的实现和验收收口。第二版在第一版 replay-only 最小闭环基础上新增并验证了：

- 第二版 run schema、版本常量、run config facts 和最终 run metadata。
- run metadata 审计、legacy metadata 兼容和 `inspect-run` 第二版展示。
- SFT、RL、preference 三种导出格式的 manifest、audit report JSON 和 audit report Markdown。
- training eligibility、oracle hidden feedback 默认 diagnostic-only、preference pair 硬门控和 compare scope。
- ExperimentConfig 多 rollout runner、aggregate metrics、task-set 阈值检查。
- ModelClient 协议、replay/fake 兼容层、scaffold registry、`single_shot_patch` 和 `planner_coder_verifier`。
- mock provider、DeepSeek primary real provider adapter、OpenAI fallback adapter 和受控 provider artifact。
- repo materialization、命令环境策略门、verifier parser policy 和 20 个 replay task set。
- Docker execution mode 的 Stage 14 `interface_only` 可审计路径。
- 全局 `v2_acceptance_report.json` 和 `inspect-v2-acceptance --assert-complete`。

第二版没有声称以下能力已经完成：

- 没有实现生产级安全沙箱。
- 没有实现完整 SWE-Bench 榜单基础设施。
- 没有实现新的强化学习算法或训练调度器。
- 没有声称已经训练出 coding agent。
- 没有实现 Docker backend 端到端执行；当前 Docker stage 是 `interface_only`，也就是继续清晰拒绝 `runtime.execution_mode=docker`，并保留可验收扩展路径。

## 阶段提交

| 阶段 | Commit | 说明 |
| --- | --- | --- |
| Stage 01 | `a3e1088` | 第二版 schema、版本常量和基础测试 |
| Stage 02 | `88e584d` | run config facts、最终 run metadata、本地环境指纹和 tool schema snapshot |
| Stage 03 | `56bda6e` | `inspect-run` 第二版展示和 legacy metadata 兼容 |
| Stage 04 | `83c1c0b` | export audit、training eligibility、manifest 和 Markdown audit |
| Stage 05 | `7189cfa` | preference pair 硬门控和 compare scope |
| Stage 06 | `83e28fe` | ExperimentConfig 最小多 rollout runner |
| Stage 07 | `e37b8c8` | ModelClient 协议、replay/fake 兼容层和 scaffold registry |
| Stage 08 | `25441e3` | `single_shot_patch` scaffold |
| Stage 09 | `8035015` | `planner_coder_verifier` scaffold |
| Stage 10 | `eb98003` | mock provider 和 provider artifact |
| Stage 11 | `4f36e75` | DeepSeek primary real provider、OpenAI fallback 和 smoke report |
| Stage 12 | `8b60897` | repo materialization、命令环境策略门和 parser policy |
| Stage 13 | `54b2af3` | replay task set 扩展到 20 个任务 |
| Stage 14 | `59cd913` | Workspace backend path 和 Docker `interface_only` 状态检查 |

Stage 15 的提交会包含本文档、walkthrough、implementation log index、acceptance report builder、acceptance inspector 和最终验收日志。

## 关键机器产物

- 全局验收报告：`runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json`
- 验收命令日志：`runs/v2-final-acceptance-20260501T223447Z-command.log`
- V1 replay 回归：`runs/v2-final-v1-regression-20260501T223447Z/batch_manifest.json`
- mock provider smoke：`runs/v2-final-mock-provider-20260501T223447Z/mock_provider_smoke_report.json`
- replay task set：`runs/v2-final-task-set-20260501T223447Z/experiment_manifest.json`
- task set aggregate metrics：`runs/v2-final-task-set-20260501T223447Z/aggregate_metrics.json`
- feedback policy 覆盖：`runs/v2-final-task-set-20260501T223447Z/feedback_policy_report.json`
- real provider smoke：`runs/v2-real-provider-smoke-20260501T214500Z/real_provider_smoke_report.json`
- Docker stage status：`runs/v2-docker-stage-20260501T222345Z/docker_stage_status.json`

## 最终验收结果

`repo-harness inspect-v2-acceptance runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json --assert-complete` 已通过。

关键结果：

- replay task set：20 个任务。
- recorded runs：20 个。
- 进入 Agent Loop：18 个。
- formal final verifier runs：18 个。
- success runs：18 个。
- structured skipped runs：2 个。
- mock provider：accepted。
- real provider：DeepSeek primary accepted with credentials，credential source 只记录为 `local_secret_file_redacted`。
- Docker stage：`interface_only` passed，Docker backend 未实现，`runtime.execution_mode=docker` 继续清晰拒绝。
- export audit formats：`sft_jsonl`、`rl_jsonl`、`preference_jsonl` 均有 audit report。
- feedback policy 覆盖：`disabled`、`public_only`、`structured_public_feedback`、`oracle_hidden_feedback` 均覆盖。
- feedback-tests-passed policy 覆盖：`stop_immediately`、`require_model_final`、`continue` 均覆盖。
- provider raw request、raw response、reasoning summary 和 Authorization marker 没有进入正式训练 payload。
- 正式训练 JSONL 默认只包含 trainable 样本。
- diagnostic-only、skipped 或 invalid 样本只进入 audit report 或诊断产物，不进入正式训练 JSONL。

## 导出审计

最终验收汇总了三个 exports 根目录：

- `runs/v2-final-v1-regression-20260501T223447Z/exports`
- `runs/v2-final-mock-provider-20260501T223447Z/exports`
- `runs/v2-final-task-set-20260501T223447Z/exports`

格式分布：

- `sft_jsonl`：6 个 audit report。
- `rl_jsonl`：6 个 audit report。
- `preference_jsonl`：5 个 audit report。

V1 replay 回归中的 oracle hidden feedback 样本默认是 `diagnostic_only`，因此 SFT 和 RL 正式数据文件没有 trainable 行。mock provider 和 Stage 13 task set 使用 `public_only`，SFT 和 RL 导出包含 trainable 样本。

Preference export 在单 rollout task set 和 V1 batch 中因为同任务可比较 pair 不足而 skipped，原因记录为 `not_enough_runs_for_same_task`，没有伪造 preference pair。

## Provider 结果

mock provider：

- 状态：accepted。
- final verifier：accepted。
- export audit：clean。
- raw provider artifacts：redacted。

DeepSeek primary provider：

- 状态：accepted_with_credentials。
- requested provider：deepseek。
- actual provider：deepseek。
- model：deepseek-v4-pro。
- base URL：`https://api.deepseek.com`。
- final verifier：accepted。
- run outcome：success。
- credential source：`local_secret_file_redacted`，没有记录密钥值。
- official docs checked：true。

OpenAI fallback：

- 已实现为备用 adapter 和 fallback schema。
- 本次最终验收没有使用 fallback，因为 DeepSeek primary 已通过。
- `inspect-v2-acceptance` 会拒绝把 OpenAI fallback 成功伪装成 DeepSeek primary 成功。

## Docker Stage

Stage 14 选择 `interface_only`：

- `mode = "interface_only"`。
- `status = "passed"`。
- `docker_available = true`。
- `docker_backend_implemented = false`。
- `docker_execution_mode_behavior = "clearly_rejected"`。
- `production_sandbox_claimed = false`。

这表示第二版已经为 Docker-based executable repository environment 提供可审计扩展路径，但没有实现 Docker backend。当前运行器会拒绝 `runtime.execution_mode=docker`，不会静默回退到 `local_process`。

## Deferred Enhancement

没有阶段被标记为 deferred enhancement。`planner_coder_verifier` 已在 Stage 09 实现并验收。

## 允许降级项

- Docker backend 未实现，采用 Stage 14 允许的 `interface_only` 模式。
- 20 个 replay task set 满足数量和质量门槛，但成功任务仍以同一个 calculator repository-style fixture 为主，任务多样性后续应继续增强。
- Preference export 在最终单 rollout task set 中 skipped，这是合格行为，因为没有同一任务的两个可比较 rollout。

## 残余风险

- Docker backend 后续如果实现，必须新增独立后端并真实使用 container execution context，不能只改 metadata。
- feedback policy coverage report 当前记录的是测试证据和最终 task set 事实，不直接内嵌 pytest 结果文件；最终验收通过全量测试和命令日志共同证明。
- 真实 provider smoke 使用本地密钥辅助完成 DeepSeek accepted 路径。报告只记录 redacted credential source；后续如在无凭证环境运行，可以结构化 skip，但不能记为 accepted。
