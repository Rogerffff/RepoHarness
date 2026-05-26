# Stage 16G.0 Follow-up 执行计划：Claude Code 与 mini-SWE-agent 基线契约补齐

## 1. 阶段定位

Stage 16G.0 follow-up 是 Stage 16G.0 的补充验收阶段。它不做功能实现，不修改模型可见工具，不放宽 `execute_bash`、`diagnostic_shell` 或任何运行时权限策略。它只补齐一个关键缺口：

```text
Stage 16G.1 到 Stage 16G.4 需要对齐的目标工具环境，必须先被逐能力写成可审计、可引用、可验收的 baseline contract。
```

前一轮 Stage 16G.0 已经完成 RepoHarness 当前工具面盘点、差距矩阵和小型可执行 probe。但是现有 `stage16g0_claude_code_tool_inventory.json` 主要引用 `reference/claude-code-typescript-src/AGENTS.md` 这类导航文件，不能充分代表 Claude Code 的真实工具实现；现有 `stage16g0_capability_gap_matrix.json` 中的 `claude_code_baseline` 也过于模板化，不能直接指导后续 Stage 16G.1 到 Stage 16G.4 的实现优先级。

本 follow-up 的目标是把“Claude Code 风格真实工具环境”和“mini-SWE-agent 风格稳定 Bash 环境”分别写成基线契约，然后逐能力对照 RepoHarness 当前状态，生成后续实现要求。这样 Stage 16G.5 只负责改造后的实证 parity probe，而不是第一次认真对比目标工具环境。

## 2. 非目标

本阶段明确不做下面这些事情：

1. 不新增、删除或修改 RepoHarness 的模型可见工具。
2. 不修改 `src/repo_harness/tools/minimal.py`、`src/repo_harness/tasks/command_policy.py`、`src/repo_harness/rl/runtime.py`、scaffold 或 workspace backend 行为。
3. 不把 Claude Code 或 mini-SWE-agent 的实现直接复制到 RepoHarness。
4. 不把 mini-SWE-agent 的 Bash-first 设计误解为 RepoHarness 应该开放完整无约束 shell。
5. 不进入 Stage 17 数据 registry、真实数据冻结、warm-start 数据生产或正式强化学习训练。
6. 不用 Stage 17 是否放行作为本阶段的中心叙事。本阶段的中心问题是 Stage 16G 后续工具能力如何对齐真实 SWE agent 环境。

## 3. 输入来源要求

本阶段必须重新建立 source inventory。任何 baseline 结论都不能只引用二手总结或导航文件。

### 3.1 Claude Code 基线来源

必须至少读取并引用 Claude Code 参考源码中的具体实现文件。可以使用 `reference/claude-code-typescript-src/AGENTS.md` 作为导航，但不能把它作为全部能力证据。

最低证据覆盖：

```text
reference/claude-code-typescript-src/Tool.ts
reference/claude-code-typescript-src/tools.ts
reference/claude-code-typescript-src/services/tools/toolExecution.ts
reference/claude-code-typescript-src/services/tools/toolOrchestration.ts
reference/claude-code-typescript-src/services/tools/StreamingToolExecutor.ts
reference/claude-code-typescript-src/tools/FileReadTool/
reference/claude-code-typescript-src/tools/FileEditTool/
reference/claude-code-typescript-src/tools/FileWriteTool/
reference/claude-code-typescript-src/tools/GlobTool/
reference/claude-code-typescript-src/tools/GrepTool/
reference/claude-code-typescript-src/tools/BashTool/
reference/claude-code-typescript-src/tools/TodoWriteTool/
reference/claude-code-typescript-src/tools/AgentTool/
reference/claude-code-typescript-src/tools/MCPTool/
reference/claude-code-typescript-src/tools/ToolSearchTool/
reference/claude-code-typescript-src/utils/permissions/
reference/claude-code-typescript-src/services/lsp/
reference/claude-code-typescript-src/hooks/
reference/claude-code-typescript-src/plugins/
reference/claude-code-typescript-src/skills/
```

如果某些目录或文件在当前参考源码中不存在，必须在 source inventory 中记录 `exists=false`，不能静默跳过，也不能用导航文件代替具体证据。

### 3.2 mini-SWE-agent 基线来源

必须为 mini-SWE-agent 建立独立 baseline contract。本地当前没有 mini-SWE-agent 官方仓库源码，因此本阶段必须优先使用 evaluation worktree 已经保存的真实配置和运行日志，不允许直接退回 `docs/harness_improve/gpt_advice.md` 的二手总结。

优先级如下：

1. evaluation worktree 中已经保存的 public-safe source excerpt、实际配置和运行日志摘要。
2. 官方仓库、官方文档或固定 commit 的公开源码；如果后续能补充，应该升级证据置信度。
3. `docs/harness_improve/gpt_advice.md` 中的二手总结；只能作为辅助背景，不能作为本阶段 mini-SWE-agent baseline 的主要证据。

最低证据覆盖必须来自下面这些 public-safe opaque ref。公开产物不能写真实本机绝对路径，只能写 `evaluation_worktree`、repo-relative path、sha256 和 opaque ref。

```text
evaluation_worktree:runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_deepseek_v4_pro_high.yaml
evaluation_worktree:runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/public_source_mini_swe_agent_swebench_config_excerpt.txt
evaluation_worktree:runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5.stdout_stderr.log
evaluation_worktree:runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5/minisweagent.log
evaluation_worktree:runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5_official_all5.stdout_stderr.log
evaluation_worktree:runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5_official_completed4.stdout_stderr.log
```

如果某个日志文件不存在或名称已经变化，source inventory 必须记录 `exists=false` 或用同一 run directory 下的等价 `mini_swe_agent_b0_*smoke*` / `official*` 日志替代，并解释替代原因。

如果执行环境无法访问官方仓库或无法确认固定 commit，本阶段不能把二手总结写成高置信基线。此时必须把对应证据标记为：

```json
{
  "confidence": "medium",
  "primary_source_verification_required": true
}
```

基于这些 tier-2 真实文件，本阶段可以对 mini-SWE-agent 的外部可观察行为给出中高置信结论，例如单一 Bash 闭环、stdout / stderr / exit code 反馈、缺少 Claude Code 式结构化工具分层等。框架内部实现细节，例如动作解析、安全机制、完整 sandbox 策略，因为没有官方仓库源码，必须标记：

```json
{
  "confidence": "medium",
  "primary_source_verification_required": true
}
```

mini-SWE-agent baseline 的重点不是工具数量，而是它是否提供稳定、可持续、真实 shell 闭环。至少需要确认：

```text
模型是否主要通过 Bash 或 shell session 操作仓库。
模型是否能运行项目命令、公开测试、复现脚本和诊断命令。
模型是否能通过 shell 完成文件查看、搜索、编辑、新建文件和 patch 生成。
shell 是否在任务内保持足够稳定的工作目录、环境变量或会话状态。
是否有防止 hidden test、gold patch、测试篡改、宿主路径访问或依赖污染的边界。
```

### 3.3 RepoHarness 当前状态来源

必须继续引用当前工作树实现，而不是只引用 Stage 16G.0 旧 JSON 产物。

最低证据覆盖：

```text
src/repo_harness/tools/minimal.py
src/repo_harness/scaffolds/
src/repo_harness/scaffolds/policies.py
src/repo_harness/tasks/command_policy.py
src/repo_harness/tasks/public_environment.py
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/workspace/patch_hygiene.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/evaluation/episode_runner.py
src/repo_harness/evaluation/episode_projection.py
src/repo_harness/execution/spec.py
src/repo_harness/rl/runtime.py
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/*.json
```

## 4. 必须生成的公开产物

本 follow-up 仍然输出到：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/
```

必须新增下面四个 baseline JSON 产物和一个 follow-up 验收摘要。

### 4.1 `stage16g0_claude_code_baseline_contract.json`

该文件记录 Claude Code 类目标工具环境的逐能力契约。它不是简单工具清单，而是说明真实产品态工具能力如何被模型看见、如何执行、如何被权限系统约束、结果如何回流到下一轮模型上下文。

最小字段：

```json
{
  "schema_version": "stage16g0.claude_code_baseline_contract.v1",
  "baseline_label": "claude_code_like_swe_agent",
  "baseline_scope": "reference_source_contract_not_product_replication",
  "source_inventory": [
    {
      "source_label": "claude_code_file_read_tool",
      "relative_path": "reference/claude-code-typescript-src/tools/FileReadTool/FileReadTool.ts",
      "sha256": "<sha256>",
      "exists": true
    }
  ],
  "capability_contracts": [
    {
      "capability_id": "structured_file_read",
      "capability_category": "file_navigation",
      "baseline_statement": "模型可以使用结构化 Read 类工具读取仓库文件，并通过行范围、结果大小限制和工具结果回流控制上下文成本。",
      "model_visible_mechanism": "Read / FileReadTool",
      "execution_semantics": "读取工作区内文件；非文本文件、过大文件和受保护路径有专门处理或拒绝路径。",
      "permission_semantics": "只读能力默认风险较低，但仍受路径保护、敏感文件保护和工具生命周期审计约束。",
      "result_semantics": "工具结果进入下一轮模型上下文；大输出需要截断、保存或分页策略。",
      "repo_harness_design_implication": "RepoHarness 的 read_file、artifact 回读和大文件分页必须保持结构化，不应要求模型通过 shell cat/head/tail 读取源码。",
      "source_evidence": [
        {
          "relative_path": "reference/claude-code-typescript-src/tools/FileReadTool/FileReadTool.ts",
          "evidence_kind": "static_source_scan"
        }
      ],
      "confidence": "high"
    }
  ]
}
```

该文件至少覆盖下面能力：

```text
structured_file_read
non_text_file_read
large_file_paging_or_artifact_replay
glob_file_discovery
grep_content_search
structured_edit_existing_file
structured_write_or_create_file
patch_or_multi_file_edit_equivalent
bash_project_command_execution
persistent_or_background_command_monitoring
public_test_or_project_command_execution
scratch_reproduction_script
permission_approval_and_denial_recovery
sandbox_and_workspace_boundary
tool_result_truncation_and_raw_artifact_privacy
task_management_todo
subagent_or_task_tool
external_tool_mcp_plugin_skill
tool_search_or_deferred_tool_discovery
hooks_and_tool_lifecycle_audit
language_diagnostics_or_lsp_feedback
session_context_resume_compaction
final_answer_and_change_summary
```

### 4.2 `stage16g0_mini_swe_agent_baseline_contract.json`

该文件记录 mini-SWE-agent 类 Bash-first baseline。它必须把 mini-SWE-agent 的能力和 Claude Code 的能力分开描述，不能把两者混成一个笼统的“真实 SWE agent”。

最小字段：

```json
{
  "schema_version": "stage16g0.mini_swe_agent_baseline_contract.v1",
  "baseline_label": "mini_swe_agent_like_bash_first_agent",
  "baseline_scope": "minimal_shell_first_swe_agent_comparison_baseline",
  "source_inventory": [
    {
      "source_label": "mini_swe_agent_primary_source_or_public_excerpt",
      "public_reference_kind": "pinned_source_or_opaque_ref",
      "sha256": "<sha256-or-null>",
      "primary_source_verified": true
    }
  ],
  "capability_contracts": [
    {
      "capability_id": "stable_shell_loop",
      "capability_category": "shell",
      "baseline_statement": "模型至少拥有一个稳定 shell 操作闭环，可以在任务内运行诊断命令、测试命令和复现脚本。",
      "model_visible_mechanism": "Bash / shell command channel",
      "execution_semantics": "主要开发动作通过 shell 完成，结构化工具较少或不是核心能力。",
      "permission_semantics": "具体安全边界依赖运行环境、容器、配置或外部 harness；不能等同于无约束宿主 shell。",
      "result_semantics": "stdout、stderr、exit code 或日志输出回流给模型，支持迭代诊断。",
      "repo_harness_design_implication": "RepoHarness 主训练工具面不能弱到无法运行公开测试、项目命令和复现脚本；即使采用结构化工具优先，也必须提供等价 public diagnostic/action capability。",
      "source_evidence": [
        {
          "source_label": "mini_swe_agent_primary_source_or_public_excerpt",
          "evidence_kind": "primary_source_or_public_safe_excerpt"
        }
      ],
      "confidence": "high"
    }
  ]
}
```

该文件至少覆盖下面能力：

```text
stable_shell_loop
repository_navigation_via_shell
file_view_search_edit_via_shell
public_test_and_project_command_via_shell
scratch_script_and_reproduction_via_shell
dependency_setup_or_environment_use
patch_generation_and_final_diff
stdout_stderr_exit_code_feedback
task_local_state_or_session_continuity
safety_boundary_and_hidden_material_exclusion
```

### 4.3 `stage16g0_per_capability_baseline_comparison.json`

这是本 follow-up 最重要的产物。它把 Claude Code baseline、mini-SWE-agent baseline 和 RepoHarness 当前状态逐能力对齐。

每条记录必须包含用户指定字段，并且字段含义必须稳定：

```json
{
  "schema_version": "stage16g0.per_capability_baseline_comparison.v1",
  "comparison_records": [
    {
      "capability_id": "parameterized_public_test_command",
      "claude_code_baseline": "模型可以通过 Bash 或等价项目命令机制运行定向公开测试，并由权限、sandbox 和工具生命周期审计约束。",
      "mini_swe_agent_baseline": "模型至少可以通过稳定 shell 运行公开测试命令或项目测试命令，并读取 stdout、stderr 和 exit code。",
      "repoharness_current_status": "run_tests 无参数；execute_bash 支持部分安全 pytest；diagnostic_shell 不是默认正式训练工具；final-only 任务会禁用 run_tests。",
      "gap_type": "partial",
      "required_stage": "16G.3",
      "blocking_for_main_swe_rl": true,
      "source_evidence": [
        {
          "source_label": "claude_code_baseline_contract",
          "evidence_ref": "bash_project_command_execution"
        },
        {
          "source_label": "mini_swe_agent_baseline_contract",
          "evidence_ref": "public_test_and_project_command_via_shell"
        },
        {
          "source_label": "repoharness_source",
          "relative_path": "src/repo_harness/tools/minimal.py",
          "evidence_kind": "static_source_scan"
        }
      ]
    }
  ]
}
```

`gap_type` 必须使用下面枚举：

```text
present_and_sufficient
present_but_weaker_than_claude_code
present_but_weaker_than_mini_swe_agent
present_non_default
present_diagnostic_only
partial
missing
blocked_by_policy
blocked_by_backend
blocked_by_training_eligibility
deferred_schema_only
not_required_for_main_swe_rl
unknown
```

`required_stage` 必须使用下面枚举：

```text
16G.1
16G.2
16G.3
16G.4
16G.5
post_16G_optional
not_required
```

本文件至少覆盖下面 capability_id：

```text
structured_file_read
non_text_file_read
large_file_paging_or_artifact_replay
glob_file_discovery
grep_content_search
symbol_search_or_lsp_diagnostics
structured_edit_existing_file
structured_write_or_create_file
apply_patch_or_multi_file_edit
delete_move_mkdir_file_operations
bash_or_public_command_execution
persistent_diagnostic_session
parameterized_public_test_command
scratch_python_or_reproduction_script
project_command_routing
dependency_setup_and_environment_policy
git_diff_status_and_patch_capture
final_answer_verifier_reward_linkage
permission_approval_denial_recovery
sandbox_workspace_and_runtime_private_boundary
tool_result_truncation_raw_artifact_privacy
task_management_todo
subagent_background_task
external_tools_mcp_plugin_skill
hooks_tool_lifecycle_audit
training_eligibility_and_export_projection
reward_hacking_monitoring_and_quarantine
```

### 4.4 `stage16g0_stage16g_implementation_requirements.json`

该文件把逐能力差距转成 Stage 16G.1 到 Stage 16G.5 的执行要求。它不允许把问题推给 Stage 17。

最小字段：

```json
{
  "schema_version": "stage16g0.stage16g_implementation_requirements.v1",
  "design_assumptions": [
    {
      "assumption_id": "structured_public_command_first_core_profile",
      "statement": "主 SWE 强化学习 core 工具面采用结构化公开命令优先：用无状态、可审计的 run_public_command、run_project_test 和 scratch_python 覆盖动态验证能力；persistent shell 归入 swe_public_extended profile，不进入 core 默认。",
      "safety_boundary": "防 reward hacking 依赖确定性边界，包括 sandbox、路径隔离、默认无网络、共享依赖只读、题间 session 重置、每次调用静态或 AST 扫描、artifact hygiene 和 verifier 隔离，而不是通过继续削减真实 SWE 动态诊断能力来获得安全感。"
    },
    {
      "assumption_id": "mini_swe_agent_dynamic_capability_not_shell_shape",
      "statement": "当 RepoHarness 在自由 shell 形态上弱于 mini-SWE-agent 时，后续阶段追求的是覆盖 mini-SWE-agent 的动态诊断能力，而不是复制裸 shell 实现形态。"
    }
  ],
  "requirements": [
    {
      "requirement_id": "stage16g3_parameterized_public_command",
      "required_stage": "16G.3",
      "priority": "P0",
      "source_capability_ids": [
        "parameterized_public_test_command",
        "project_command_routing",
        "scratch_python_or_reproduction_script"
      ],
      "implementation_goal": "设计并实现正式 public diagnostic/action command 能力，支持公开测试、项目命令和受控复现脚本，同时不暴露 hidden verifier、gold patch、test patch、runtime-private 路径或共享依赖写权限。",
      "acceptance_requirements": [
        "模型可见 schema 能表达单个公开测试、项目命令和受控 scratch Python 复现。",
        "拒绝结果包含可学习的 reason_code、retryable、safe_alternative_tool 或 safe_rewrite_example。",
        "成功或拒绝的工具事件都能进入 public-safe audit，并能参与训练资格判断。"
      ],
      "blocking_for_main_swe_rl": true
    }
  ]
}
```

Stage 拆分要求如下：

```text
Stage 16G.1：baseline-derived tool registry 与训练工具面 profile 设计。
Stage 16G.2：结构化文件能力补齐，包括 read、grep、glob、symbol、edit、write/create、apply_patch 或等价多文件编辑、文件操作和 artifact 回读。
Stage 16G.3：公开测试、项目命令、scratch Python 和 reproduction script 能力设计与实现。
Stage 16G.4：controlled diagnostic shell、dependency setup、sandbox、权限拒绝恢复、training eligibility、verifier/reward/export linkage 收口。
Stage 16G.5：改造完成后的 Claude Code / mini-SWE-agent parity probe，不再作为第一次 baseline 对比。
```

### 4.5 `stage16g0_followup_acceptance_summary.json`

该文件是本 follow-up 的顶层验收摘要。它不能修改第一轮 `stage16g0_acceptance_summary.json`，第一轮 summary 视为 immutable；follow-up summary 单独绑定四个新增 baseline 产物，并重新汇总关键计数。

最小字段：

```json
{
  "schema_version": "stage16g0.followup_acceptance_summary.v1",
  "status": "passed",
  "stage16g0_followup_complete": true,
  "claude_code_baseline_contract_sha256": "<sha256>",
  "mini_swe_agent_baseline_contract_sha256": "<sha256>",
  "per_capability_baseline_comparison_sha256": "<sha256>",
  "stage16g_implementation_requirements_sha256": "<sha256>",
  "comparison_record_count": "<derived_int>",
  "blocking_for_main_swe_rl_count": "<derived_int>",
  "gap_type_counts": {
    "partial": "<derived_int>"
  },
  "required_stage_counts": {
    "16G.1": "<derived_int>",
    "16G.2": "<derived_int>",
    "16G.3": "<derived_int>",
    "16G.4": "<derived_int>",
    "16G.5": "<derived_int>"
  },
  "requirement_count": "<derived_int>",
  "p0_requirement_count": "<derived_int>",
  "public_path_leak_scan_passed": true,
  "first_stage16g0_acceptance_summary_left_immutable": true
}
```

`comparison_record_count`、`blocking_for_main_swe_rl_count`、`gap_type_counts`、`required_stage_counts`、`requirement_count` 和 `p0_requirement_count` 必须从 `stage16g0_per_capability_baseline_comparison.json` 与 `stage16g0_stage16g_implementation_requirements.json` 重新推导，不能只信任 summary 自身。

## 5. Baseline 对照原则

### 5.1 Claude Code 对齐原则

Claude Code baseline 不能被简化成“有 Bash”。本阶段必须把它写成分层工具环境：

```text
Read / Grep / Glob / Edit / Write 等结构化工具承担高频读、搜、改、写。
Bash 承担测试、构建、项目命令、复杂诊断和部分 Git / GitHub 工作流。
权限、sandbox、hook、工具生命周期、长输出处理和工具结果回流共同约束强能力。
任务管理、子代理、MCP、插件、技能和工具搜索属于真实产品态扩展能力。
```

RepoHarness 后续不需要完整复刻 Claude Code，但主 SWE 强化学习工具面不能缺失真实 SWE 闭环中的核心动作。

### 5.2 mini-SWE-agent 对齐原则

mini-SWE-agent baseline 不能被简化成“安全性不重要”。它的参考价值是：即使工具极少，只要有稳定可执行 shell，模型也能形成定位、复现、修改、验证的基本闭环。

RepoHarness 可以选择结构化工具优先，也可以把 Bash 能力拆成 `run_public_command`、`run_project_test`、`scratch_python` 和 controlled diagnostic shell，但这些组合能力至少要覆盖 mini-SWE-agent 的核心动态诊断能力。

因此，在 `stage16g0_per_capability_baseline_comparison.json` 中，凡是记录“RepoHarness 在自由 shell 形态上弱于 mini-SWE-agent”的能力，都必须明确说明这是能力覆盖目标，不是实现形态目标。后续实现应优先补齐公开测试、项目命令、scratch Python、stdout / stderr / exit code 回流和可学习拒绝恢复，而不是直接开放无约束 persistent shell。

### 5.3 安全边界原则

对齐真实工具能力不等于开放完整宿主 shell。所有后续 requirement 必须继续显式排除：

```text
hidden verifier
gold patch
test patch
FAIL_TO_PASS / PASS_TO_PASS selector
official verifier private artifact
runtime-private path
host filesystem escape
Git history exploit
test tampering
shared dependency write
network download without explicit policy
provider secret 或 API key
```

## 6. 验收标准

本 follow-up 只有在下面条件全部满足时，才可以视为完成：

1. 四个新增 baseline JSON 产物和 `stage16g0_followup_acceptance_summary.json` 都存在，并能被 `json.loads(...)` 解析。
2. `stage16g0_claude_code_baseline_contract.json` 至少覆盖本计划列出的 Claude Code 能力，并且每条能力至少有一个具体源码文件证据，不允许全部只引用 `AGENTS.md`。
3. `stage16g0_mini_swe_agent_baseline_contract.json` 独立记录 mini-SWE-agent Bash-first baseline，并明确每条证据是 primary source、public-safe excerpt 还是 secondary summary。
4. `stage16g0_per_capability_baseline_comparison.json` 至少覆盖本计划列出的所有 capability_id，且每条记录都有逐能力 `claude_code_baseline` 和 `mini_swe_agent_baseline`，不能使用同一句模板话。
5. `stage16g0_stage16g_implementation_requirements.json` 明确把 P0 / P1 差距映射到 Stage 16G.1 到 Stage 16G.5，不允许把核心工具能力问题推迟到 Stage 17，并且包含结构化公开命令优先的 core profile 设计假设。
6. 所有公开产物不包含真实本机绝对路径、hidden verifier 原文、gold patch、test patch、官方 verifier 私有输出、provider secret 或 API key。
7. 新增产物的 `source_evidence` 可以追溯到 baseline contract、RepoHarness 当前源码或 public-safe opaque ref。
8. 如果 mini-SWE-agent primary source 没有被确认，相关记录必须显式标记 `primary_source_verification_required=true`，并且不能把该 baseline 作为高置信硬结论。
9. `stage16g0_followup_acceptance_summary.json` 用 sha256 绑定四个新增 baseline 产物，并且 summary 计数可以从 comparison 与 requirements 文件重新推导。
10. 第一轮 `stage16g0_acceptance_summary.json` 保持不变；如果需要表达 follow-up 状态，只能写入 follow-up summary。

## 7. 建议实现方式

建议新增或扩展脚本：

```text
scripts/pre_verl/build_stage16g0_baseline_contract_followup.py
```

该脚本可以复用 Stage 16G.0 现有 source hashing、path leak scan 和 JSON 输出逻辑，但必须新增三类检查：

1. Claude Code baseline evidence 检查：禁止所有 Claude Code capability 的 evidence 都只指向 `AGENTS.md`。
2. per-capability baseline 检查：禁止 `claude_code_baseline` 或 `mini_swe_agent_baseline` 在 5 条以上记录中完全相同。
3. Stage mapping 检查：所有 `blocking_for_main_swe_rl=true` 的记录必须映射到 `16G.1`、`16G.2`、`16G.3` 或 `16G.4`，不能只映射到 `16G.5` 或 Stage 17。

如果暂时手工生成 JSON，也必须运行等价检查，并把检查结果写入 follow-up acceptance summary 或新增 public-safe check report。

执行过程中还必须维护：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/implementation-notes.md
```

该文件记录设计决策、偏离、权衡和开放问题。凡是实现者对本计划做出超出原文的解释或调整，都必须在 notes 和最终汇报中显式说明。

## 8. 建议验证命令

本阶段至少运行：

```bash
git diff --check -- docs/agentic_RL/repo_harness_verl_workstreams/50-stage-16g-0-follow-up-baseline-contract-execution-plan.md
python - <<'PY'
import json
from pathlib import Path

root = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0")
for name in [
    "stage16g0_claude_code_baseline_contract.json",
    "stage16g0_mini_swe_agent_baseline_contract.json",
    "stage16g0_per_capability_baseline_comparison.json",
    "stage16g0_stage16g_implementation_requirements.json",
    "stage16g0_followup_acceptance_summary.json",
]:
    json.loads((root / name).read_text())
print("stage16g0_followup_json_parse_ok")
PY
```

如果新增 builder 或 inspector 测试，还必须运行对应单元测试，例如：

```bash
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_stage16g0_baseline_contract_followup.py
```

本阶段不要求运行完整 `python -m pytest -q`，除非实现者修改了共享 Python 代码。

## 9. 完成后的阶段入口规则

本 follow-up 完成后，Stage 16G 后续阶段入口规则如下：

1. Stage 16G.1 只能基于 `stage16g0_per_capability_baseline_comparison.json` 和 `stage16g0_stage16g_implementation_requirements.json` 设计工具 registry、profile 和能力矩阵。
2. Stage 16G.2 到 Stage 16G.4 的每个 P0 / P1 实现项，都必须能追溯到一个或多个 baseline comparison capability_id。
3. Stage 16G.5 只做改造后的实证 parity probe，不能再承担“第一次认真阅读 Claude Code / mini-SWE-agent baseline”的职责。
4. 如果 Stage 16G.5 发现新的能力差距，必须回写 baseline comparison 和 implementation requirements，而不是直接进入 Stage 17。
