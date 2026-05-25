# Stage 16F.6 执行计划：小规模真实模型 `run-episode-task` smoke

创建时间：2026-05-25

状态：待执行。

## 1. 阶段定位

Stage 16F.6 的目标是用新的 canonical Harness 入口：

```text
repo-harness run-episode-task
```

执行一组小规模真实模型 smoke，验证 Stage 16F.0 到 Stage 16F.5 统一后的入口，在真实外部模型调用下仍然能产生可审计、可投影、可验收的 episode 产物。

本阶段要回答的问题是：

```text
新的 run_episode(real_episode) 测评入口是否能替代旧 run_task(...) 承担真实模型小规模诊断？
真实外部模型轨迹是否能走完整的 ContextBuilder、工具集合、verifier、reward、patch hygiene 和 compat projection？
这些外部 API 轨迹是否被正确标记为非 formal online RL policy-loss 样本？
如果执行 Docker case，当前本地 Docker 后端是否能通过一个受控小 smoke；如果不执行，是否有结构化原因说明？
```

Stage 16F.6 不是强化学习训练阶段，也不是 Stage 16.5 的 20 到 30 题代表性 harness 诊断扩展。本阶段只做小规模真实模型入口 smoke，重点验证入口、上下文、工具面、投影和证据口径。

## 2. 与 Stage 16F.5 后续预留的关系

Stage 16F.5 文档中曾把后续阶段预留为：

```text
run-episode-batch / run-episode-experiment
```

本计划将 Stage 16F.6 定义为“小规模真实模型 `run-episode-task` smoke”。这是对当前项目节奏的调整：先用单任务 canonical 入口跑真实模型，确认模型可见上下文、工具面、patch hygiene、verifier、reward 和 projection 在真实 provider 下都闭合；再决定是否需要新增 `run-episode-batch` 或 `run-episode-experiment`。

因此：

```text
Stage 16F.6 不实现 run-episode-batch。
Stage 16F.6 不实现 run-episode-experiment。
run-episode-batch / run-episode-experiment 可以顺延到后续独立阶段。
```

## 3. 前置条件

执行前必须确认：

```text
Stage 16F.0 status=passed
Stage 16F.1 status=passed
Stage 16F.2 status=passed
Stage 16F.3 status=passed
Stage 16F.4 status=passed
Stage 16F.5 status=passed
Stage 16F.5 commit 已存在
```

当前 Stage 16F.5 提交为：

```text
d167d203 feat: add stage16f5 entrypoint policy
```

必须读取并参考：

```text
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/repo_harness_verl_workstreams/45-stage-16f-3-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/46-stage-16f-4-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/47-stage-16f-5-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_5/stage16f5_acceptance_summary.json
```

如果 `inspect-stage16f5-entrypoint-policy --assert-complete` 不能通过，本阶段必须停止，不能用真实模型 smoke 掩盖入口策略尚未完成的问题。

## 4. 非目标

Stage 16F.6 不做以下事情：

1. 不启动远端 GPU 强化学习训练。
2. 不接 `verl` 的 `FullyAsyncTrainer`。
3. 不生成 `DataProto` policy-loss batch。
4. 不把外部 API provider 轨迹伪装成 `route=verl` 或 formal online RL 样本。
5. 不执行 Stage 16.5 的 20 到 30 题代表性诊断扩展。
6. 不执行 Stage 17 的正式数据 registry 冻结。
7. 不批量迁移旧 `run_task(...)` 产物。
8. 不新增 `run-episode-batch` 或 `run-episode-experiment`。
9. 不运行完整 SWE-Bench official harness 大批量评测。
10. 不要求模型解决任务或提升分数；本阶段只要求 Harness 链路、证据和安全边界可验收。

如果执行中发现需要大规模任务池、批量调度或官方 SWE-Bench 全量验证，必须记录为 Stage 16.5、Stage 17 或后续独立阶段需求，而不是扩大 Stage 16F.6。

## 5. Docker 镜像和任务复用决策

### 5.1 不默认复用本机缓存的 SWE-Bench 大镜像题目

本机当前可能已经缓存了多类 Docker 镜像，包括：

```text
sweb.env.py.x86_64.*:latest
repo-harness-swebench-verified-agent:*
sweb.base.py.x86_64:latest
repo-harness-v3-python:stage2
repo-harness-pre-verl-python-*:*
```

Stage 16F.6 不要求、也不应该默认从这些本机缓存的 SWE-Bench 相关镜像里直接挑题运行。

原因是：

```text
本机缓存镜像本身不是任务 registry。
镜像存在不等于任务 manifest、source snapshot、verifier plan 和 official healthcheck 已绑定。
如果直接从缓存镜像挑题，后续无法证明任务来源、镜像摘要、verifier 结果和训练资格事实是一一对应的。
这些镜像很多来自历史评测或另一个工作树的运行缓存，不能自动成为当前 worktree 的 canonical training / evaluation source。
```

因此，Stage 16F.6 的默认任务来源应是当前仓库内已经受控的 micro fixture 或 Stage 16F fixture，例如：

```text
tests/fixtures/tasks/task_stage16f3_passing.yaml
tests/fixtures/tasks/task_001.yaml
tests/fixtures/tasks/task_003_create_file.yaml
tests/fixtures/tasks/task_stage14_negative_boundary.yaml
```

具体实现时可以根据模型成本和任务难度选择 3 到 5 个小任务，不要求全部使用上面列表。

### 5.2 可以加入一个可选 Docker 后端 smoke

Stage 16F.6 可以加入一个可选 Docker 后端 smoke，用来证明：

```text
run-episode-task
-> Docker workspace / diagnostic backend
-> real_episode
-> final verifier
-> compat projection
```

仍然可用。

这个 Docker smoke 建议优先使用当前仓库已有的小型 RepoHarness 镜像配置，例如：

```text
repo-harness-v3-python:stage2
```

或者使用执行环境明确可用、可记录摘要、不需要临时联网拉取的等价小镜像。

该可选 Docker smoke 必须满足：

```text
image_ref 已记录
image_id 或 repo digest 已记录
是否来自本机缓存已记录
如果 image digest 无法取得，必须记录原因
不因缺少本机缓存镜像自动联网拉取，除非执行计划显式允许
Docker smoke 失败不能被静默降级成通过
Docker smoke 若被标记 optional skipped，必须记录 skipped_missing_local_image、docker_unavailable 或 explicit_not_required
```

### 5.3 使用 SWE-Bench 缓存镜像的条件

如果执行者希望在 Stage 16F.6 中复用某个本机已有 SWE-Bench 缓存镜像，必须先满足以下条件：

```text
任务有当前 worktree 内可提交的 task manifest。
task manifest 显式绑定 image_ref 和 image digest。
source snapshot、dataset row digest、verifier plan digest 已记录。
gold patch、no-op 或 expected behavior 事实不泄漏 oracle 信息。
public evidence 只写 image ref、digest、任务 opaque ref 和聚合计数，不写本机路径。
该任务不是从另一个 worktree 的临时运行目录直接借用。
```

如果这些条件不满足，该任务不能作为 Stage 16F.6 的默认 smoke case。它可以作为后续 Stage 16.5 代表性诊断或 Stage 17 数据 registry 准备的一部分，由专门计划处理。

换句话说，Stage 16F.6 不需要因为本机已经有 Docker 镜像就强行复用这些镜像题目。当前阶段最重要的是验证 canonical 入口在真实模型下可用，而不是扩大任务覆盖面。

## 6. 真实模型 provider 范围

Stage 16F.6 默认使用外部 API provider 执行真实模型 smoke。推荐优先级：

```text
DeepSeek V4 或当前评测工作树实际使用的强模型 provider
OpenAI 或其他已接入 provider 作为显式 fallback
```

实现时必须避免把 provider 凭据写入公开 evidence。

公开 evidence 允许记录：

```text
provider_name
provider_route
model_id
provider_request_count
provider_error_count
redacted_failure_category
```

公开 evidence 禁止记录：

```text
API key
完整 request header
完整 provider raw response 中的私有字段
本机配置文件路径
provider secret 名称的实际值
```

如果真实 provider 不可用，本阶段可以生成 diagnostic-only evidence，但不能标记为 `stage16f6_complete=true`。

## 7. 样本设计

### 7.1 最小真实模型 case 数量

`--assert-complete` 模式下，建议最小要求：

```text
real_model_case_count >= 3
completed_real_model_episode_count >= 2
projection_complete_count == completed_real_model_episode_count
```

其中至少包含：

1. 一个不需要隐藏反馈也能完成的简单代码任务。
2. 一个会暴露公开环境上下文和公开测试提示的任务。
3. 一个失败也可以被结构化解释的任务，例如 verifier rejected 或模型格式失败。

如果真实模型一次性全部成功，这当然可以通过；如果其中一个任务失败，只要失败是模型行为或 verifier rejected，并且 Harness 证据完整，也可以通过。基础设施错误、工具异常、projection 缺失、路径泄漏和 provider secret 泄漏不能通过。

### 7.2 patch hygiene 覆盖

至少一个完成的 case 必须产生非空 cleaned patch，或者必须明确记录：

```text
all_completed_cases_have_empty_patch=true
reason=tasks_are_final_answer_only 或 model_failed_to_modify_files
```

如果所有任务都是空 patch，Stage 16F.6 仍可作为 provider smoke，但不能声称已经覆盖 patch hygiene 的真实非空路径。默认建议选择至少一个需要修改文件的小任务，避免这个降级。

### 7.3 public feedback 覆盖

如果选择的 run config 启用了公开测试反馈，本阶段必须用真实轨迹证明模型确实触发了公开反馈事件，不能只看配置字段。

有效的 public feedback case 必须记录：

```text
run_tests_tool_call_observed=true
public_feedback_observation_observed=true
public_feedback_event_count >= 1
hidden_feedback_not_exposed=true
```

如果真实模型没有调用 `run_tests`，该 case 不能计入 `public_feedback_case_count`。

### 7.4 非 `verl` route 训练资格

DeepSeek、OpenAI、mock、replay 等非 `verl` route 的轨迹，都不能成为 formal online RL policy-loss 样本。

每个 Stage 16F.6 case 必须记录：

```text
formal_online_rl_eligible=false
policy_loss_candidate=false
training_data_eligibility_asserted=false
provider_route_qualification_source=entrypoint_report 或 provider_route_qualification.json
```

这不表示这些轨迹永远不能用于 SFT 或偏好数据构造。它只表示它们不能直接进入 `verl` online RL policy loss，因为它们缺少 `route=verl`、response token、response logprob、generation record 和 formal gate 绑定。

## 8. 预期新增或复用的命令

本阶段不要求新增主入口命令。应复用：

```text
repo-harness run-episode-task
repo-harness inspect-stage16f5-entrypoint-policy
```

建议新增或实现等价验收命令：

```text
repo-harness inspect-stage16f6-real-model-smoke
```

该命令读取 Stage 16F.6 evidence 目录或 tarball，并支持：

```text
--assert-complete
```

如果执行者不新增专门命令，也必须提供等价的机器验收脚本，并在 evidence 中记录命令、版本、输入和输出。

## 9. 建议运行命令形态

真实模型 smoke 的命令形态示例：

```bash
PATH=.venv/bin:$PATH PYTHONPATH=src:$PYTHONPATH \
python -m repo_harness.cli.main run-episode-task \
  tests/fixtures/tasks/task_stage16f3_passing.yaml \
  --config tests/fixtures/run_configs/stage16f6_real_model_public_feedback.yaml \
  --output-dir runs/stage16f6-real-model-smoke \
  --run-id stage16f6-real-model-001 \
  --assert-projection-complete
```

Docker 可选 smoke 的命令形态示例：

```bash
docker image inspect repo-harness-v3-python:stage2
```

然后运行一个显式 Docker run config：

```bash
PATH=.venv/bin:$PATH PYTHONPATH=src:$PYTHONPATH \
python -m repo_harness.cli.main run-episode-task \
  tests/fixtures/tasks/task_001.yaml \
  --config tests/fixtures/run_configs/stage16f6_docker_real_model_smoke.yaml \
  --output-dir runs/stage16f6-docker-smoke \
  --run-id stage16f6-docker-001 \
  --assert-projection-complete
```

这些命令只是形态示例。实施时可以根据已有 provider 配置、成本和任务可解性调整 fixture 名称。

## 10. 证据目录

建议生成公开 evidence：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_6/
```

至少包含：

```text
stage16f6_acceptance_summary.json
stage16f6_case_manifest.json
stage16f6_real_model_run_report.json
stage16f6_projection_validation_report.json
stage16f6_tool_and_context_report.json
stage16f6_provider_route_policy_report.json
stage16f6_patch_hygiene_report.json
stage16f6_public_feedback_report.json
stage16f6_docker_optional_report.json
stage16f6_public_leak_scan_report.json
stage16f6_test_report.json
```

这些文件不是“只要存在就通过”。Stage 16F.6 必须生成 canonical evidence map，建议为：

```text
stage16f6_canonical_evidence_map.json
```

该文件至少记录每个 canonical evidence item 的：

```text
relative_path
sha256
artifact_kind
required_for_assert_complete
```

`stage16f6_acceptance_summary.json` 也必须包含每个 canonical evidence item 的 sha256，或者包含 `canonical_evidence_map_sha256` 并由 inspector 读取 map 后逐项校验。两种方式都可以，但不能只校验 summary 自身。

`inspect-stage16f6-real-model-smoke --assert-complete` 必须重新读取所有 canonical report，并重新推导以下字段：

```text
real_model_case_count
completed_real_model_episode_count
projection_complete_count
legacy_run_task_invocation_count
policy_loss_candidate_count
external_provider_case_count
public_feedback_enabled_case_count
public_feedback_observed_case_count
public_feedback_event_count
blocking_reason_count
```

如果删除、篡改、替换、额外增加未知 public evidence 文件，或者 summary 中的计数与 report 重新推导结果不一致，`--assert-complete` 必须失败。额外文件只有在 canonical evidence map 中显式登记并通过泄漏扫描时才能存在。

如果有 raw provider request、raw provider response、真实 API 错误、raw command log 或完整 transcript 需要保存，只能放入运行时私有 evidence，并用不透明引用和 sha256 绑定：

```text
runtime-private:<artifact-kind>:<sha256>
```

公开 evidence 不能包含真实运行时私有路径。

## 11. `stage16f6_case_manifest.json` 最小字段

每个 case 至少包含：

```json
{
  "case_id": "stage16f6-case-001",
  "task_ref": "tests/fixtures/tasks/task_stage16f3_passing.yaml",
  "task_sha256": "...",
  "run_config_ref": "tests/fixtures/run_configs/stage16f6_real_model_public_feedback.yaml",
  "run_config_sha256": "...",
  "entrypoint": "run_episode_task",
  "provider_name": "deepseek",
  "model_id": "...",
  "execution_mode": "local_process",
  "docker_case": false,
  "expected_projection_complete": true,
  "expected_formal_online_rl_eligible": false,
  "expected_policy_loss_candidate": false
}
```

如果是 Docker case，还必须包含：

```json
{
  "docker_case": true,
  "image_ref": "repo-harness-v3-python:stage2",
  "image_id": "...",
  "image_digest_status": "recorded|unavailable_explained",
  "build_if_missing": false,
  "network_pull_allowed": false
}
```

## 12. `stage16f6_real_model_run_report.json` 最小字段

至少包含：

```json
{
  "schema_version": "repo_harness_stage16f6_real_model_run_report_v0",
  "real_model_case_count": 3,
  "completed_real_model_episode_count": 2,
  "failed_real_model_episode_count": 1,
  "infrastructure_failure_count": 0,
  "provider_failure_count": 0,
  "provider_rate_limit_count": 0,
  "tool_error_count": 0,
  "run_episode_task_invocation_count": 3,
  "legacy_run_task_invocation_count": 0,
  "case_records": []
}
```

`case_records` 中每条记录至少包含：

```text
case_id
run_id
entrypoint_report_sha256
episode_execution_spec_sha256
compat_projection_sha256
final_status
status_reason
verifier_status
reward_score
patch_hygiene_status
provider_route
formal_online_rl_eligible
policy_loss_candidate
```

## 13. Projection 和 patch hygiene 验收

每个 completed case 必须通过：

```text
--assert-projection-complete
```

或者等价的 projection validator。

验收必须至少检查：

```text
compat_projection 存在
entrypoint_report.json 存在
episode_execution_spec_sha256 存在
final.patch 存在或明确 empty patch
final.diff 存在或明确 empty diff
final_patch_hygiene_report.json 存在
cleaned_patch_sha256 与 final.patch 一致
cleaned_diff_sha256 与 final.diff 一致
patch hygiene public report 不包含 raw patch audit 字段
public evidence 不泄漏本机路径、运行时私有路径、provider secret 或 hidden verifier
```

Stage 16F.6 的公开 evidence 不能只让 `stage16f6_projection_validation_report.json` 和
`stage16f6_patch_hygiene_report.json` 互相引用同一组摘要。每个 completed case 还必须提供
`runtime-private:<artifact-kind>:<sha256>` opaque ref，并由
`runtime_private/runtime_private_manifest.json` 或等价私有 manifest 绑定到实际私有 artifact。

最低要求：

```text
compat_projection_ref -> runtime-private:compat-projection:<sha256>
final_patch_ref -> runtime-private:final-patch:<sha256>
final_diff_ref -> runtime-private:final-diff:<sha256>
final_patch_hygiene_report_ref -> runtime-private:final-patch-hygiene-report:<sha256>
```

`inspect-stage16f6-real-model-smoke --assert-complete` 必须读取私有 manifest，校验：

```text
ref kind 与期望 artifact kind 一致
ref 中的 sha256 与报告字段一致
manifest 中的 sha256 与 ref 一致
manifest relative_path 位于 runtime_private/ 下，且不是绝对路径或 .. 路径
真实私有 artifact 的字节 sha256 与 ref 一致
```

如果同步篡改公开 projection report 和 patch hygiene report，但没有对应的私有 artifact 摘要绑定，
验收必须失败。

如果 `final.patch` 被删除、篡改或出现敏感 marker，`inspect-stage16f6-real-model-smoke --assert-complete` 必须失败。

## 14. 工具面和上下文验收

Stage 16F.6 需要证明真实模型看到的是 Stage 16C 到 Stage 16F 统一后的上下文和工具面，而不是旧 `run_task(...)` 的上下文。

`stage16f6_tool_and_context_report.json` 至少记录：

```text
public_environment_context_present
public_environment_context_digest
tool_schema_snapshot_digest
allowed_tool_names
execute_bash_policy_summary
diagnostic_shell_enabled
diagnostic_shell_backend
run_tests_feedback_policy
legacy_run_task_context_used=false
```

如果 case 启用了 `diagnostic_shell`，还必须记录：

```text
diagnostic_shell_backend
session_invalidated
workspace_projection_sync_status
background_process_cleanup_status
hidden_projection_path_guard_status
```

如果 case 没有启用 `diagnostic_shell`，必须显式记录：

```text
diagnostic_shell_enabled=false
```

## 15. Provider route 和训练资格验收

`stage16f6_provider_route_policy_report.json` 必须按 case 记录：

```text
provider_route
route_is_verl
formal_online_rl_eligible
policy_loss_candidate
training_data_eligibility_asserted
reason_not_policy_loss_candidate
```

对外部 API provider：

```text
route_is_verl=false
formal_online_rl_eligible=false
policy_loss_candidate=false
reason_not_policy_loss_candidate=external_provider_missing_verl_token_provenance
```

如果某个 case 错误地把 DeepSeek、OpenAI、mock 或 replay 轨迹标成 `policy_loss_candidate=true`，Stage 16F.6 必须失败。

## 16. Docker optional report

`stage16f6_docker_optional_report.json` 必须存在，即使没有执行 Docker case。

最小字段：

```json
{
  "schema_version": "repo_harness_stage16f6_docker_optional_report_v0",
  "docker_case_required": false,
  "docker_case_status": "executed|skipped_missing_local_image|skipped_docker_unavailable|skipped_not_required|failed",
  "docker_daemon_available": true,
  "selected_image_ref": "repo-harness-v3-python:stage2",
  "selected_image_id": "...",
  "selected_image_digest_status": "recorded|unavailable_explained|not_applicable",
  "swebench_cached_image_used": false,
  "reason_swebench_cached_image_not_used": "no_current_task_manifest_digest_verifier_binding"
}
```

如果使用了 SWE-Bench 缓存镜像，报告必须额外包含：

```text
swebench_cached_image_used=true
task_manifest_ref
task_manifest_sha256
source_snapshot_digest
verifier_plan_digest
image_digest
why_safe_for_stage16f6
```

其中 `task_manifest_sha256`、`source_snapshot_digest`、`verifier_plan_digest` 必须是 64 位十六进制
sha256；`image_digest` 必须是 `sha256:<64 hex>`。这些字段不能只检查“非空”，否则垃圾绑定值不能证明
缓存镜像和当前任务、源码快照、verifier plan 有真实绑定。

否则 `--assert-complete` 必须拒绝该 Docker case。

## 17. Public evidence 泄漏扫描

Stage 16F.6 的公开 evidence 必须扫描以下类型：

```text
*.json
*.jsonl
*.md
*.log
*.yaml
*.yml
*.txt
*.patch
*.diff
```

扫描范围应限定为 Stage 16F.6 实际生成的公开 evidence 目录，例如：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16f_6/
```

执行计划文档、训练设计文档或规则说明文档中出现风险术语时，不应被当作泄漏本身；这些说明性上下文应通过 `allowlisted_contexts` 或等价机制记录。真正必须严格拒绝的是公开 evidence 中出现未脱敏的真实路径、真实 secret、真实 hidden verifier 内容或 raw oracle 内容。

禁止出现：

```text
本机绝对路径
真实 run directory 路径
真实 workspace 路径
真实 runtime_private 路径
provider API key
hidden verifier 原文
gold patch 内容
FAIL_TO_PASS / PASS_TO_PASS 的 verifier-only 原始泄漏
test_patch / gold_patch / hidden_verifier 作为泄漏内容
```

允许出现的是规则说明、字段名或不透明引用，例如：

```text
runtime-private:<artifact-kind>:<sha256>
```

但不能出现真实路径形式的运行时私有目录。

## 18. 验收 summary

`stage16f6_acceptance_summary.json` 至少包含：

```json
{
  "schema_version": "repo_harness_stage16f6_acceptance_summary_v0",
  "status": "passed",
  "stage16f6_complete": true,
  "ready_for_stage16_5": true,
  "ready_for_stage17_data_registry_planning": true,
  "real_model_case_count": 3,
  "completed_real_model_episode_count": 2,
  "projection_complete_count": 2,
  "legacy_run_task_invocation_count": 0,
  "policy_loss_candidate_count": 0,
  "external_provider_case_count": 3,
  "public_feedback_enabled_case_count": 1,
  "public_feedback_observed_case_count": 1,
  "public_feedback_event_count": 1,
  "docker_case_status": "executed|skipped_missing_local_image|skipped_docker_unavailable|skipped_not_required",
  "canonical_evidence_map_sha256": "...",
  "public_path_leak_scan_passed": true,
  "provider_secret_leak_scan_passed": true,
  "blocking_reason_count": 0
}
```

如果真实 provider 不可用，summary 可以写：

```text
status=diagnostic_only
stage16f6_complete=false
ready_for_stage16_5=false
```

但不能写成 passed。

## 19. 建议新增测试

实施时建议新增：

```text
tests/unit/test_repo_harness_stage16f6_real_model_smoke_acceptance.py
tests/unit/test_repo_harness_stage16f6_provider_route_policy.py
tests/unit/test_repo_harness_stage16f6_docker_optional_report.py
```

测试重点：

1. 篡改 summary 计数字段，inspector 必须拒绝。
2. 篡改 canonical evidence map 中任意 sha256，inspector 必须拒绝。
3. 删除、替换或额外增加未登记 public evidence 文件，inspector 必须拒绝。
4. 删除或篡改 `final.patch`，inspector 必须拒绝。
5. 把外部 provider case 改成 `policy_loss_candidate=true`，inspector 必须拒绝。
6. Docker optional report 缺失时，inspector 必须拒绝。
7. SWE-Bench 缓存镜像被标记为使用但缺少 task manifest / image digest / verifier binding 时，inspector 必须拒绝。
8. 公开 evidence 中出现 provider secret、真实 runtime-private 路径或本机绝对路径时，inspector 必须拒绝。
9. 配置启用了公开测试反馈但真实轨迹没有 `run_tests` 或 public feedback observation 时，不能计入 `public_feedback_observed_case_count`。

## 20. 建议本地验证命令

实施完成后至少运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16f6_real_model_smoke_acceptance.py \
  tests/unit/test_repo_harness_stage16f6_provider_route_policy.py \
  tests/unit/test_repo_harness_stage16f6_docker_optional_report.py
```

并运行关键前置回归：

```bash
PATH=.venv/bin:$PATH python -m pytest -q \
  tests/unit/test_repo_harness_stage16f5_entrypoint_policy.py \
  tests/unit/test_repo_harness_stage16f5_run_episode_task_metadata.py \
  tests/unit/test_repo_harness_stage16f4_parity_report.py \
  tests/unit/test_repo_harness_stage16f3_run_episode_task_cli.py \
  tests/unit/test_repo_harness_stage16f3_run_episode_projection.py
```

还必须运行：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
git diff --check
```

如果新增 inspector：

```bash
PATH=.venv/bin:$PATH python -m repo_harness.cli.main \
  inspect-stage16f6-real-model-smoke \
  docs/agentic_RL/repo_harness_verl_workstreams/stage16f_6 \
  --assert-complete
```

## 21. 通过标准

Stage 16F.6 通过时必须满足：

1. 至少 3 个真实模型 case 被调度。
2. 至少 2 个真实模型 case 通过 `run-episode-task` 完成 episode，并生成完整 compat projection。
3. 旧 `run_task(...)` 没有被用作本阶段主入口。
4. 每个 completed case 都有 `entrypoint_report.json`，并标记为 canonical `run_episode_task`。
5. 每个 completed case 都通过 projection binding。
6. 每个 completed case 都有 patch hygiene report；如果 patch 为空，必须记录原因。
7. 外部 API 轨迹全部标记为非 formal online RL policy-loss 样本。
8. 至少一个 case 启用了 public feedback，并且真实轨迹中观测到 `run_tests` 工具调用和 public feedback observation。
9. public environment、工具 schema、test feedback policy 和 verifier plan digest 都被记录。
10. 公开 evidence 无路径泄漏、secret 泄漏、hidden verifier 泄漏和 raw oracle 泄漏。
11. Docker optional report 存在，并清楚说明是否执行 Docker smoke、使用了哪个镜像、是否使用了 SWE-Bench 缓存镜像。
12. canonical evidence map 存在，summary 和所有 canonical report 的计数字段能由 inspector 重新推导一致。

## 22. 阻断条件

出现以下任一情况，Stage 16F.6 不能标记为通过：

```text
真实 provider 全部不可用。
run-episode-task 没有实际调用。
任一 completed case 缺少 compat projection。
projection validator 未运行或失败。
public feedback 被声明覆盖，但没有真实 run_tests 调用或 public feedback observation。
外部 API provider 轨迹被标记成 policy_loss_candidate=true。
公开 evidence 泄漏 provider secret、本机路径、真实 runtime-private 路径或 hidden verifier。
Docker smoke 被声明 executed 但没有 image ref / image id / digest 状态。
SWE-Bench 缓存镜像被使用但缺少 task manifest、source snapshot digest 或 verifier binding。
```

## 23. 与 Stage 16.5 和 Stage 17 的关系

Stage 16F.6 通过后，可以更有信心进入：

```text
Stage 16.5：20 到 30 题代表性 harness 诊断扩展
Stage 17：R2E-Gym、SWE-Gym 和内部微型任务池的数据 registry 准备
```

但 Stage 16F.6 本身不冻结训练数据，也不证明任务池可靠。它只证明新的 canonical 入口已经可以在真实模型调用下产生可验收轨迹。

Stage 16.5 仍然需要回答更大范围的问题：

```text
当前工具面是否足够？
diagnostic shell 是否满足真实任务需要？
公开测试反馈是否有用？
patch hygiene 是否在更多任务上稳定？
official verifier 或数据集 verifier 的失败模式是什么？
```

Stage 17 才负责把任务转成可训练、可验证、无 oracle 泄漏的数据 registry。

## 24. 对“是否询问另一个 worktree”的建议

当前 Stage 16F.6 不需要依赖另一个 worktree 才能启动。根据本机检查结果，当前 worktree 已经具备：

```text
run-episode-task
entrypoint policy
compat projection
patch hygiene
public environment
Docker backend smoke 所需的小镜像候选
```

如果只做 3 到 5 个小任务的真实模型 smoke，不必询问另一个 worktree 的执行 agent。

需要询问另一个 worktree 的情况是：

```text
你希望 Stage 16F.6 复用某个具体 SWE-Bench verified 题目。
你希望复用另一个 worktree 的 DeepSeek V4 测评任务清单。
你希望把某个本机缓存的 sweb.env 或 repo-harness-swebench-verified-agent 镜像绑定到当前 smoke case。
你需要确认某个 official harness 运行结果、gold/no-op healthcheck 或 verifier 修复是否已经完成。
```

如果发生这些情况，另一个 worktree 需要提供的不只是“镜像名”或“题目编号”，而是：

```text
task manifest
dataset row digest
source snapshot digest
image ref 和 image digest
verifier plan digest
gold/no-op 或 expected behavior healthcheck evidence
公开安全的 provenance report
```

没有这些材料时，Stage 16F.6 不应该把该题目纳入通过条件。
