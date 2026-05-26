# Stage 16G.1 执行计划：工具 Registry、Profile Taxonomy 和训练资格门禁

## 1. 阶段定位

Stage 16G.1 是 Stage 16G 后续工具能力改造的第一步。它不实现新工具，不放宽 `execute_bash`，不把 persistent shell 放入主训练默认工具面，也不进入 Stage 17 数据 registry。

本阶段的目标是把 Stage 16G.0 follow-up 已经确认的能力基线，固化成机器可检查的工具 registry、profile taxonomy 和训练资格门禁。后续 Stage 16G.2 到 Stage 16G.4 的实现必须能追溯到这些契约，而不是继续凭直觉补工具。

Stage 16G.1 必须回答：

```text
哪些工具能力属于主 SWE 强化学习 core profile？
哪些能力只属于 extended / diagnostic profile？
每个能力如何映射到 Claude Code baseline、mini-SWE-agent baseline 和 RepoHarness 当前工具？
每个工具事件如何影响整条 trajectory / sample 的 policy loss、SFT、preference、负样本、quarantine 或 diagnostic-only projection 资格？
这些判断能否由机器验收器稳定检查？
```

## 2. 非目标

Stage 16G.1 明确不做下面这些事情：

1. 不新增模型可见工具。
2. 不修改工具执行语义。
3. 不放宽 `execute_bash` 或 `diagnostic_shell`。
4. 不实现 `apply_patch`、`run_public_command`、`run_project_test` 或 `scratch_python`。
5. 不把 persistent diagnostic shell 放入 `swe_public_core`。
6. 不进入数值型 reward 设计，不定义 process reward 权重。
7. 不冻结真实 SWE 训练数据，不生产 warm-start 数据，不启动正式强化学习训练。
8. 不把旧 `run_task(...)` 作为新工具能力的主验收入口。

## 3. 必须继承的输入

Stage 16G.1 必须以 Stage 16G.0 follow-up 产物作为权威输入：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_claude_code_baseline_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_mini_swe_agent_baseline_contract.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_per_capability_baseline_comparison.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_stage16g_implementation_requirements.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/stage16g0_followup_acceptance_summary.json
```

Stage 16G.1 还必须读取当前 RepoHarness 源码事实，而不是只读 Stage 16G.0 JSON：

```text
src/repo_harness/config/schemas.py
src/repo_harness/tools/minimal.py
src/repo_harness/scaffolds/
src/repo_harness/scaffolds/policies.py
src/repo_harness/tasks/command_policy.py
src/repo_harness/tasks/public_environment.py
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/workspace/patch_hygiene.py
src/repo_harness/evaluation/episode_runner.py
src/repo_harness/evaluation/episode_projection.py
src/repo_harness/evaluation/entrypoint_policy.py
src/repo_harness/execution/spec.py
src/repo_harness/rl/runtime.py
```

如果某个文件不存在、迁移或不适用，source inventory 必须记录，不能静默跳过。

Stage 16G.1 必须重新固定下面这些当前代码事实，并让机器验收器检查。不能只继承 Stage 16G.0 的文字结论：

```text
RuntimeConfig 默认 scaffold 是 simple_react。
create_file 在 simple_react 默认工具面中可见。
patch_focused_react_mini_shell 当前工作树不存在。
execute_bash 是窄但非空的安全工具，不是完整 shell，也不是空工具。
diagnostic_shell 是 diagnostic / extended 能力，不是 swe_public_core 默认能力。
```

## 4. 设计原则

### 4.1 结构化公开命令优先

Stage 16G.1 的 profile 设计必须继承 Stage 16G.0 follow-up 的核心假设：主 SWE 强化学习工具面采用结构化公开命令优先。

```text
run_public_command / run_project_test / scratch_python 是 dynamic diagnostic capability 的目标形态。
persistent shell 是 swe_public_extended 能力，不是 swe_public_core 默认能力。
mini-SWE-agent 的 Bash-first 设计是能力下限，不是实现形态目标。
```

### 4.2 安全边界不靠削弱能力

Stage 16G.1 不能用“继续不给模型真实诊断能力”作为安全方案。它必须把安全边界写成明确 gate：

```text
hidden verifier 隔离
gold patch 隔离
test patch 隔离
runtime-private 隔离
宿主绝对路径禁止
默认无网络
共享依赖只读
raw artifact 私有化
路径脱敏
final patch hygiene
quarantine
```

### 4.3 统一入口优先

Stage 16G.1 的所有验收必须绑定 `run-episode-task` / `RepoHarnessRuntime.run_episode(real_episode)`。旧 `run_task(...)` 只能作为 legacy compatibility 检查，不能作为新增 profile 或训练资格的主事实来源。

### 4.4 工具可见性必须和训练投影同时定义

每个工具或未来工具候选都必须同时定义：

```text
tool schema 状态
模型可见说明状态
scaffold / profile 暴露状态
public environment 提示状态
executor binding 状态
tool result / artifact visibility
denial feedback policy
training projection policy
run_episode visibility
owner stage
```

如果某个工具只有名字，没有模型可见说明、拒绝恢复语义或训练投影策略，Stage 16G.1 必须把它判为不完整。

## 5. 建议实现范围

Stage 16G.1 建议只新增轻量 builder、validator、inspector 和测试，不改工具行为。

建议新增或修改：

```text
scripts/pre_verl/build_stage16g1_tool_profile_registry.py
src/repo_harness/stage16g_tool_profile.py
src/repo_harness/cli/main.py
tests/unit/test_repo_harness_stage16g1_tool_profile_registry.py
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/
```

说明：

1. builder 负责生成公开 evidence JSON。
2. `src/repo_harness/stage16g_tool_profile.py` 负责可复用的 schema 检查和 inspect 逻辑。
3. `repo-harness inspect-stage16g1-tool-profile ... --assert-complete` 或等价 CLI 负责机器验收。
4. 单元测试必须覆盖 builder、validator、CLI inspector 和关键失败模式。

如果实现者认为暂时不需要新增 `src/repo_harness/stage16g_tool_profile.py`，也必须提供等价可复用 inspector 逻辑，不能只把检查写在一次性脚本里。

## 6. 必须生成的公开产物

公开产物目录：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/
```

必须生成：

```text
stage16g1_source_inventory.json
stage16g1_tool_registry_contract.json
stage16g1_profile_taxonomy.json
stage16g1_training_eligibility_gate_spec.json
stage16g1_profile_registry_inspection_report.json
stage16g1_run_episode_profile_smoke_report.json
stage16g1_public_evidence_policy.json
stage16g1_path_leak_scan_report.json
stage16g1_human_readable_tool_profile_summary.md
stage16g1_acceptance_summary.json
```

### 6.1 `stage16g1_source_inventory.json`

记录 Stage 16G.1 使用的输入文件、输入 JSON、源码文件、sha256 和 public-safe reference。公开产物不能写真实本机绝对路径。

### 6.2 `stage16g1_tool_registry_contract.json`

这是 Stage 16G.1 的核心产物。它必须覆盖 Stage 16G.0 follow-up 的 27 条 `capability_id`。

每条 registry 记录至少包含：

```json
{
  "capability_id": "apply_patch_or_multi_file_edit",
  "baseline_gap_type": "missing",
  "blocking_for_main_swe_rl": true,
  "owner_stage": "16G.2",
  "priority": "P0",
  "repo_harness_status": "proposed_tool_required",
  "tool_ids": ["apply_patch"],
  "profiles": {
    "safe_structured_only": "planned",
    "swe_public_core": "planned",
    "swe_public_extended": "planned",
    "redteam_restricted": "allowed_for_negative_or_safety_probe"
  },
  "model_visible_schema_status": "planned",
  "model_visible_prompt_status": "planned",
  "scaffold_exposure_status": "planned",
  "public_environment_hint_status": "planned",
  "executor_binding_status": "not_implemented",
  "run_episode_visibility_status": "planned",
  "allowed_artifact_visibility": {
    "model_visible": "summary_or_public_result",
    "raw_artifact": "private_by_default",
    "export_projection": "public_safe_projection_only"
  },
  "denial_feedback_policy": {
    "requires_reason_code": true,
    "requires_retryable": true,
    "requires_safe_alternative_tool": true,
    "requires_safe_rewrite_example": true
  },
  "training_projection_policy": {
    "tool_event_policy_loss_unit": "not_an_individual_policy_loss_sample",
    "allowed_in_policy_loss_trajectory": false,
    "sample_policy_loss_candidate_effect": "makes_sample_ineligible_until_tool_implemented",
    "sft_eligible": false,
    "preference_eligible": false,
    "negative_sample_eligible": true,
    "quarantine_eligible": true,
    "diagnostic_only": false,
    "eligibility_reason": "工具尚未实现，Stage 16G.2 完成前不能进入主训练。"
  },
  "safety_boundaries": [
    "hidden_verifier_forbidden",
    "gold_patch_forbidden",
    "test_patch_forbidden",
    "runtime_private_forbidden"
  ],
  "source_capability_refs": [
    "stage16g0_per_capability_baseline_comparison"
  ],
  "confidence": "high"
}
```

字段可以扩展，但不能省略能力映射、profile、artifact visibility、denial policy、training projection、owner stage 和 run_episode visibility。训练投影字段必须区分“单个工具事件能否出现在合格轨迹里”和“整条样本能否成为 policy loss 候选”，不能把单个工具事件直接当成 policy loss sample。

### 6.3 `stage16g1_profile_taxonomy.json`

必须定义四个 profile：

```text
safe_structured_only
swe_public_core
swe_public_extended
redteam_restricted
```

每个 profile 至少包含：

```json
{
  "profile_id": "swe_public_core",
  "intended_use": "主 SWE 强化学习默认工具面",
  "allowed_capability_ids": [],
  "planned_capability_ids": [],
  "forbidden_capability_ids": [],
  "must_not_include": ["persistent_diagnostic_session"],
  "required_safety_boundaries": [],
  "training_projection_defaults": {},
  "run_episode_required": true,
  "legacy_run_task_primary_allowed": false
}
```

硬性要求：

1. `swe_public_core` 不允许包含 persistent shell。
2. `swe_public_core` 必须为 Stage 16G.3 的 public command、project test 和 scratch Python 留出 planned capability。
3. `swe_public_extended` 可以包含 persistent diagnostic session，但必须要求 session reset、artifact hygiene、路径脱敏和 public-safe projection。
4. `redteam_restricted` 只能用于安全验证、拒绝恢复、负样本和泄漏测试，不能作为主训练默认 profile。

### 6.4 `stage16g1_training_eligibility_gate_spec.json`

该文件定义工具事件、轨迹和 profile 的训练资格门禁。至少包含：

```text
tool_event_eligibility
trajectory_eligibility
profile_eligibility
provider_provenance_policy
denial_and_failure_projection_policy
quarantine_policy
hard_fail_boundary_policy
export_projection_policy
```

必须明确：

1. 外部 provider 轨迹如果缺少 verl 训练所需 token / logprob provenance，默认不能进入 policy loss。
2. hidden verifier、gold patch、test patch、runtime-private、宿主绝对路径、Git history 作弊和共享依赖污染是 deterministic hard fail。
3. 权限拒绝、bad command、patch failure、unknown path 等不是默认丢弃；它们可以进入负样本、偏好数据、diagnostic facts 或 quarantine。
4. diagnostic-only 工具事件不能让所在样本绕过主训练 gate 进入 policy loss。
5. raw artifact 默认私有，公开 export 只能包含 public-safe projection。
6. `tool_event_eligibility` 和 `trajectory_eligibility` 必须分开。`read_file`、`grep`、`edit_file` 这类工具事件可以出现在合格 trajectory 中，但单个工具事件本身不是 policy loss sample。
7. registry 必须使用类似 `allowed_in_policy_loss_trajectory` 和 `sample_policy_loss_candidate_effect` 的字段，明确工具事件对整条样本 policy loss 资格的影响。

### 6.5 `stage16g1_profile_registry_inspection_report.json`

这是机器验收器输出的报告。必须从 registry、profile taxonomy 和 eligibility gate 重新推导关键计数，不能只信 acceptance summary。

最少检查：

```text
comparison_record_count == 27
blocking_for_main_swe_rl_count == 17
all_capabilities_mapped_to_registry == true
all_blocking_capabilities_have_owner_stage == true
all_tools_have_artifact_visibility == true
all_tools_have_training_projection_policy == true
all_tools_have_denial_feedback_policy == true
swe_public_core_excludes_persistent_shell == true
swe_public_extended_defines_persistent_shell_boundaries == true
post_16g_optional_capabilities_reserved == true
run_episode_primary_entry_declared == true
legacy_run_task_not_primary == true
model_visible_prompt_scaffold_public_environment_consistency_declared == true
counts_derived_from_stage16g0_comparison == true
runtime_default_scaffold_is_simple_react == true
simple_react_exposes_create_file == true
patch_focused_react_mini_shell_not_present == true
execute_bash_narrow_but_nonempty == true
diagnostic_shell_not_core_default == true
```

### 6.6 `stage16g1_run_episode_profile_smoke_report.json`

Stage 16G.1 不需要跑大规模任务，但必须有一个小型 smoke 证明新 profile / registry 能被 `run_episode(real_episode)` 统一入口加载、引用或投影。

可接受形式：

1. 使用 mock / replay 模型和极小 fixture。
2. 不新增模型可见工具。
3. 不放宽 shell。
4. 不需要真实 provider。
5. 只证明 `EpisodeExecutionSpec`、scaffold/profile 声明和 TrainingView / projection 能携带 profile id 或 registry version。

只读取 registry JSON、只运行 builder，或者只检查文件存在，不能算 `run_episode` smoke 通过。smoke 至少必须经过 `EpisodeExecutionSpec`、scaffold/profile 声明或 episode projection 中的一条真实路径，并把 profile id 或 registry version 带到公开 run evidence / projection 中。

如果当前代码结构暂时无法在不改行为的情况下完成此 smoke，Stage 16G.1 必须输出明确 blocked report，并把修复要求列为 Stage 16G.1 P0，而不能静默跳过。未解决的 blocked report 只能产生 `status=blocked`、`stage16g2_allowed_to_start=false`，并且 `inspect-stage16g1-tool-profile --assert-complete` 必须失败。只有 blocked report 对应问题修复后，才允许生成 `status=passed` 的 acceptance summary。

### 6.7 `stage16g1_acceptance_summary.json`

顶层 summary 必须绑定所有产物 sha256，并重新汇总核心计数。

最小字段：

```json
{
  "schema_version": "stage16g1.acceptance_summary.v1",
  "status": "passed",
  "stage16g1_complete": true,
  "comparison_record_count": 27,
  "blocking_for_main_swe_rl_count": 17,
  "post_16g_optional_count": 4,
  "profile_count": 4,
  "tool_registry_contract_sha256": "<sha256>",
  "profile_taxonomy_sha256": "<sha256>",
  "training_eligibility_gate_spec_sha256": "<sha256>",
  "profile_registry_inspection_report_sha256": "<sha256>",
  "run_episode_profile_smoke_report_sha256": "<sha256>",
  "public_path_leak_scan_passed": true,
  "machine_inspector_passed": true,
  "stage16g2_allowed_to_start": true,
  "stage17b_real_data_freeze_allowed": false,
  "stage20_warm_start_data_generation_allowed": false,
  "stage21_formal_rl_allowed": false
}
```

`comparison_record_count`、`blocking_for_main_swe_rl_count`、`post_16g_optional_count`、`profile_count` 等计数必须从输入 comparison、registry 和 taxonomy 重新推导，不能硬编码。`status=passed` 表示 Stage 16G.1 的 registry、profile 和 gate 完整，不表示工具能力已经补齐，也不表示可以进入真实训练。

### 6.8 `stage16g1_public_evidence_policy.json`

该文件定义 Stage 16G.1 公开 evidence 的可传播边界，不能是空壳 JSON。最小字段：

```json
{
  "schema_version": "stage16g1.public_evidence_policy.v1",
  "allowed_reference_kinds": [
    "repo_relative_path",
    "source_label",
    "opaque_ref",
    "sha256",
    "schema_version"
  ],
  "forbidden_content_patterns": [
    "local_user_home_path",
    "private_system_path",
    "generic_home_directory_path",
    "temporary_directory_path",
    "runtime_private_path",
    "provider_secret",
    "api_key"
  ],
  "raw_artifact_policy": "private_by_default",
  "public_projection_policy": "public_safe_summary_and_sha256_only",
  "required_hash_binding": true,
  "path_redaction_required": true
}
```

必须明确：

1. 公开 evidence 可以包含 repo-relative path、source label、opaque ref、sha256、计数和 schema version。
2. 公开 evidence 不能包含本机绝对路径、runtime-private 路径、provider secret、API key、raw patch 中的私有路径或未脱敏 artifact 内容。
3. raw artifact 默认私有，公开文件只能保存 public-safe 摘要、计数、状态和 sha256。
4. acceptance summary 必须绑定公开产物 sha256。

## 7. 机器验收器要求

Stage 16G.1 必须新增或复用命令：

```text
repo-harness inspect-stage16g1-tool-profile docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json --assert-complete
```

该命令至少检查：

1. acceptance summary 引用的 sha256 和实际文件一致。
2. 所有必需 JSON 文件存在且能解析。
3. 27 条 Stage 16G.0 capability 全部进入 registry。
4. 17 条 `blocking_for_main_swe_rl=true` 的 capability 全部有 owner stage。
5. 4 条 `post_16G_optional` capability 全部有 schema reserved 和 revisit stage。
6. 每个 registry record 都有 artifact visibility、denial feedback policy 和 training projection policy。
7. `swe_public_core` 不包含 persistent shell。
8. `swe_public_extended` 的 persistent shell 有 session reset、artifact hygiene 和路径脱敏要求。
9. `redteam_restricted` 没有被标记为主训练默认 profile。
10. `run_episode` 被声明为主入口，旧 `run_task(...)` 没有被标记为主入口。
11. public evidence 不含本机绝对路径、runtime-private 路径或 secrets。
12. 每个 registry record 的 `owner_stage` 必须与 `stage16g0_per_capability_baseline_comparison.json` 中同一 `capability_id` 的 `required_stage` 一致。`not_required`、`16G.5` 和 `post_16G_optional` 也必须保留原阶段语义，不能被静默改写成 Stage 16G.2 到 Stage 16G.4。
13. 如果确实需要改变 owner stage，registry record 必须包含 `stage_override_reason` 和 `source_requirement_update_ref`，并且 source requirement 或 comparison 已经同步更新；否则 inspector 必须失败。
14. 标记为 `implemented`、`present` 或 `enabled` 的 `tool_ids` 必须能被当前工具 registry、`build_tool` 或等价源码入口解析；无法解析时只能标为 `planned`、`proposed` 或 `not_implemented`。
15. profile / scaffold 暴露状态必须能追溯到实际 allowed tools、scaffold policy 或明确的 planned 状态；不能只靠手写声明。
16. public environment 提示状态必须能追溯到 `public_environment.py` 当前行为或明确的 planned 状态。
17. `executor_binding_status=not_implemented`、`model_visible_schema_status=planned` 或 `run_episode_visibility_status=planned` 的能力，必须禁止 `allowed_in_policy_loss_trajectory=true`，并且 `sample_policy_loss_candidate_effect` 不能表示“保持样本可进入 policy loss”。
18. acceptance summary 中的核心计数必须从 Stage 16G.0 comparison、Stage 16G.1 registry 和 profile taxonomy 重新推导，不能硬编码。
19. 必须检查当前源码事实：RuntimeConfig 默认 scaffold 是 `simple_react`、`simple_react` 暴露 `create_file`、`patch_focused_react_mini_shell` 不存在、`execute_bash` 窄但非空、`diagnostic_shell` 不属于 `swe_public_core` 默认能力。

如果 `--assert-complete` 失败，命令必须返回非零退出码，并输出可读失败列表。

## 8. 执行步骤

推荐执行顺序：

```text
16G.1A  固定 JSON schema 和 source inventory
16G.1B  生成 tool registry contract
16G.1C  生成 profile taxonomy
16G.1D  生成 training eligibility gate spec
16G.1E  实现机器 inspector 和失败用例测试
16G.1F  增加 run_episode profile smoke 或 blocked report
16G.1G  生成 acceptance summary、path leak scan 和 human-readable summary
```

### 8.1 Stage 16G.1A

先定义 schema 和 source inventory。不要在 schema 未稳定前开始补工具。

### 8.2 Stage 16G.1B

从 Stage 16G.0 comparison 派生 27 条 registry record。不能手写少量代表项后声称完整。

### 8.3 Stage 16G.1C

定义四个 profile，并明确哪些能力是 present、planned、forbidden、diagnostic-only 或 redteam-only。

### 8.4 Stage 16G.1D

定义训练资格门禁。这里不设计 reward 数值，只定义哪些 tool event 可以进入哪些训练投影。

### 8.5 Stage 16G.1E

实现 inspector。测试必须至少覆盖：

1. 缺少 capability 映射会失败。
2. blocking capability 没有 owner stage 会失败。
3. registry record 缺少 artifact visibility 会失败。
4. `swe_public_core` 包含 persistent shell 会失败。
5. public evidence 出现本机绝对路径会失败。
6. summary sha256 不匹配会失败。
7. registry record 的 `owner_stage` 与 Stage 16G.0 comparison 的 `required_stage` 不一致且没有合法 override 会失败。
8. 标记为 implemented 的工具无法在当前源码工具 registry 中解析会失败。
9. `executor_binding_status=not_implemented` 但 `allowed_in_policy_loss_trajectory=true` 会失败。
10. summary 计数不是从输入重新推导会失败。
11. 关键代码事实和当前源码不一致会失败。

### 8.6 Stage 16G.1F

运行最小 `run_episode` profile smoke。它只证明统一入口可携带 profile / registry 事实，不证明后续工具已经实现。

### 8.7 Stage 16G.1G

生成 acceptance summary，并运行全部验收命令。

## 9. 验收命令

Stage 16G.1 完成前至少运行：

```bash
PATH=.venv/bin:$PATH python scripts/pre_verl/build_stage16g1_tool_profile_registry.py
PATH=.venv/bin:$PATH repo-harness inspect-stage16g1-tool-profile docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/stage16g1_acceptance_summary.json --assert-complete
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_stage16g1_tool_profile_registry.py
PATH=.venv/bin:$PATH python -m compileall -q src/repo_harness scripts/pre_verl/build_stage16g1_tool_profile_registry.py
git diff --check
```

还必须运行 public path leak scan，至少覆盖 Stage 16G.1 公开目录中的 JSON 和 Markdown：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_1/
```

扫描 pattern 至少包含：

```text
local user home path pattern
private system path pattern
generic home directory path pattern
temporary directory path pattern
macOS temporary directory path pattern
runtime_private
provider_secret
api_key
```

## 10. 进入 Stage 16G.2 的条件

只有同时满足下面条件，Stage 16G.2 才允许开始：

1. `stage16g1_acceptance_summary.json` 为 `status=passed`。
2. 机器 inspector `--assert-complete` 通过。
3. 27 条 capability 全部进入 registry。
4. 17 条主 SWE 强化学习阻塞能力都有 owner stage。
5. `swe_public_core` 不包含 persistent shell。
6. Stage 16G.2 的 P0 文件工具能力在 registry 中标为 owner stage `16G.2`。
7. `run_episode` 统一入口 smoke 通过；如果曾经存在 P0 blocked report，该 blocked report 必须已经修复并在 inspection report 中关闭。
8. public evidence path leak scan 通过。

Stage 16G.1 通过不允许直接进入 Stage 17 真实数据冻结、Stage 20 warm-start 或 Stage 21 formal RL。

## 11. 风险和防护

### 11.1 风险：只产出 JSON，没有可执行验收

防护：Stage 16G.1 必须实现 CLI inspector，并用失败用例测试证明检查真实生效。

### 11.2 风险：profile taxonomy 过早锁死后续工具 schema

防护：允许 planned / proposed / deferred 状态，但必须有 owner stage、训练投影策略和安全边界。这样既不阻塞后续设计，也不会让能力缺口消失在文档里。

### 11.3 风险：把 persistent shell 偷偷放进 core

防护：机器 inspector 必须硬检查 `swe_public_core` 不包含 `persistent_diagnostic_session`。

### 11.4 风险：新工具只在 registry 出现，模型看不到

防护：每个 registry record 必须声明模型可见 schema、scaffold/profile 暴露、public environment 提示和 run_episode visibility 状态。

### 11.5 风险：训练资格门禁提前变成 reward builder

防护：Stage 16G.1 只定义 projection eligibility，不定义数值 reward、权重或优化目标。

## 12. 完成定义

Stage 16G.1 完成态必须满足：

```text
有机器可读 registry。
有四类 profile taxonomy。
有训练资格门禁。
有机器 inspector。
有通过的 run_episode 统一入口 smoke；未解决的 blocked report 不能算完成态。
有 public-safe evidence。
有失败用例测试。
有 acceptance summary sha256 绑定。
有明确 Stage 16G.2 启动 gate。
```

完成态的结论应该是：

```text
RepoHarness 还没有补齐 Stage 16G.2 到 Stage 16G.4 的工具能力，
但后续工具改造已经有可审计、可机器验收、可追溯到 Claude Code / mini-SWE-agent baseline 的契约。
```
