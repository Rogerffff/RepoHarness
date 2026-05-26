# Stage 16G.0 执行计划：Claude Code 类工具面与完整 scaffold 能力差距盘点

## 1. 阶段定位

Stage 16G.0 是一个只做识别、盘点和验收的阶段。它的目标不是立刻扩大 RepoHarness 的工具权限，也不是马上修改训练链路，而是系统性回答一个更前置的问题：

```text
当前 RepoHarness 提供给模型的工具、权限、scaffold、测试反馈和任务管理能力，
距离 Claude Code 这类真实软件工程智能体工具环境还有哪些差距？
这些差距会不会让后续强化学习训练学到错误的行为模式？
```

这个阶段被列为 Stage 17A 数据 registry 之前的 P0 分析任务。原因是：如果当前工具面过窄，模型在 RepoHarness 中可能会学到“少运行命令、少复现问题、少验证补丁、靠静态阅读猜测修改”的行为。这样的训练目标与真实 Claude Code 类产品希望模型掌握的能力不一致。

Stage 16G.0 完成后，后续再进入 Stage 16G.1+ 的工具面改造设计与实现。Stage 16G.0 本身不做行为改造。

本阶段不是纯静态文档盘点。它必须包含少量可执行能力 probe，用当前工作树已有工具和 fixture 验证默认 scaffold、候选 scaffold 和 diagnostic profile 的真实能力边界。probe 的目标是证明“当前能力能不能完成常见 SWE 闭环”，而不是为了绕过或放宽现有安全策略。

## 2. 非目标

本阶段明确不做下面这些事情：

1. 不新增或修改模型可见工具。
2. 不放宽 `execute_bash` 或 `diagnostic_shell` 策略。
3. 不修改 `run_episode(...)`、`run-episode-task`、`AgentLoop` 或 `EpisodeExecutionSpec` 的行为。
4. 不启动远端 GPU 或真实强化学习训练。
5. 不冻结 Stage 17 的真实训练数据 split。
6. 不把 Claude Code 的实现直接复制到 RepoHarness。
7. 不把 Claude Code 的权限系统描述成 RepoHarness 当前已经具备的能力。

## 3. 输入材料

### 3.1 外部参考材料

本阶段需要读取并摘要化下面的外部参考材料，但公开提交产物不能写入真实本机绝对路径。

```json
{
  "source_worktree_label": "evaluation_worktree",
  "source_doc_ref": "repo_harness_vs_claude_code_capability_gap_analysis",
  "claude_code_reference_label": "claude_code_typescript_reference",
  "public_path_policy": "公开产物只允许 source_worktree_label、source_doc_sha256、source_commit、opaque_ref，不允许真实本机路径"
}
```

需要重点读取：

1. 测评工作树中关于 RepoHarness 与 Claude Code 能力差距的分析文档。
2. 当前工作树中的 `docs/harness_improve/gpt_advice.md`，其中汇总了 Cursor、Claude Code、Codex、SWE-agent、OpenHands、SWE-Gym、DeepSWE 等 SWE harness 经验。
3. 当前工作树中复制进来的 Claude Code TypeScript 参考源码，尤其是工具、权限、任务管理、hooks、插件、技能和子代理相关实现。
4. Claude Code 参考源码的 `reference/claude-code-typescript-src/AGENTS.md` 导航说明。

### 3.2 RepoHarness 当前实现材料

本阶段至少需要盘点下面这些 RepoHarness 文件或模块：

```text
src/repo_harness/tools/minimal.py
src/repo_harness/scaffolds/
src/repo_harness/tasks/command_policy.py
src/repo_harness/tasks/public_environment.py
src/repo_harness/permissions/system.py
src/repo_harness/workspace/diagnostic_session.py
src/repo_harness/workspace/docker_adapter.py
src/repo_harness/workspace/adapter.py
src/repo_harness/evaluation/runner.py
src/repo_harness/evaluation/episode_runner.py
src/repo_harness/execution/spec.py
src/repo_harness/rl/runtime.py
docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md
docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md
docs/agentic_RL/training_design/stage16f_unified_baseline_handoff_to_evaluation_agent.md
docs/harness_improve/gpt_advice.md
reference/claude-code-typescript-src/AGENTS.md
```

如果某个文件不存在或已经迁移，必须在 source inventory 中记录，不允许静默跳过。

## 4. 需要回答的核心问题

Stage 16G.0 的最终报告必须回答下面这些问题。

### 4.1 工具能力问题

1. Claude Code 默认提供哪些模型可见工具？
2. RepoHarness 当前默认 scaffold 提供哪些模型可见工具？
3. RepoHarness 哪些工具只在非默认 scaffold 或 diagnostic profile 中出现？
4. 哪些能力是 Claude Code 有、RepoHarness 没有的？
5. 哪些能力 RepoHarness 有，但因为权限、后端、训练资格或 side channel 分类而不能进入正式训练轨迹？
6. 当前模型是否能完成真实软件工程常见闭环：

```text
查看文件 -> 搜索定位 -> 运行公开诊断命令 -> 写复现脚本 -> 修改代码 -> 运行定向测试 -> 查看 diff -> 收口
```

### 4.2 scaffold 能力问题

1. `patch_focused_react`、`patch_focused_react_execute_bash`、`patch_focused_react_diagnostic_shell` 等 scaffold 的可见工具集合分别是什么？
2. scaffold 声明的工具集合和实际 executor registry 是否一致？
3. 默认训练 scaffold 是否包含 shell、文件创建、patch 编辑、任务管理、公开测试命令和 artifact 回读能力？
4. 当前 scaffold 的提示语是否让模型误以为“尽量少运行命令”或“公开诊断不可用”？
5. final-only verifier 与 public diagnostic 能力是否被错误绑定？

### 4.3 shell 与测试反馈问题

1. `execute_bash` 当前是正式训练工具，还是安全最小 shell 子集？
2. `diagnostic_shell` 当前是正式解题工具，还是诊断侧通道工具？
3. 模型是否能运行定向公开测试，例如单个 pytest case、Django test label、Sphinx test、轻量 import smoke test？
4. `run_tests` 是否支持参数化命令？如果不支持，会造成哪些能力缺口？
5. 工具拒绝后是否提供可学习的恢复路径，例如安全替代工具、安全命令写法、是否可重试？

### 4.4 编辑与补丁问题

1. 当前 `edit_file` 的 exact replace 协议是否足以覆盖多文件复杂修改？
2. 是否缺少 `create_file`、`write_file`、`delete_file`、`move_file`、`mkdir`、`apply_patch` 或 unified diff 工具？
3. Stage 16E 的 patch hygiene 是否已经能支持更强的 patch 级编辑工具？
4. 新增文件、重命名文件和批量修改是否能进入 final patch、reward、official prediction 和 export？

### 4.5 任务管理、子代理和外部工具问题

1. 当前 `update_working_state` 是否足以替代 Claude Code 的任务管理能力？
2. 是否需要 `todo_write` 或等价任务管理工具？
3. 是否需要在训练轨迹 schema 中预留子代理、后台任务、外部工具、插件或技能的能力位？
4. 短期是否应该只做 schema 预留，而不实现完整 MCP 或插件系统？

### 4.6 训练风险问题

1. 当前工具面是否会鼓励静态猜测，而不是动态验证？
2. 当前权限拒绝是否会让模型学会少用工具？
3. 当前 diagnostic-only 分类是否会让最有价值的调试行为被排除在训练数据之外？
4. 当前工具面是否弱于只提供稳定 shell 的 mini-SWE-agent 类环境？
5. 哪些缺口会阻塞 Stage 17 数据冻结、Stage 20 warm-start 或 Stage 21 强化学习？

### 4.7 可执行能力 probe 问题

Stage 16G.0 必须用少量可执行 probe 验证静态盘点结论。probe 不能修改 harness 行为，不能放宽工具权限，不能写入真实训练数据，只能在测试 fixture 或临时 workspace 中运行。

至少回答：

1. 默认 scaffold 是否能完成“读文件 -> 搜索 -> 修改已有文件 -> 生成 final patch -> verifier / reward 收口”的最小闭环？
2. 默认 scaffold 是否能新建文件？如果不能，是工具缺失、scaffold 未暴露、patch capture 不支持，还是 policy 拒绝？
3. 默认 scaffold 是否能运行单个公开测试或参数化公开测试？如果不能，拒绝是否有可学习的替代建议？
4. 候选 diagnostic scaffold 是否能执行 scratch Python 或复现脚本，并保证临时脚本不进入 final patch？
5. scaffold 声明的 allowed tools、实际 tool registry、运行时 executor registry 是否一致？
6. 工具输出被截断后，模型是否有合法 artifact 回读路径？

### 4.8 其他 SWE harness 经验与部署一致性问题

`docs/harness_improve/gpt_advice.md` 明确指出，Cursor、Claude Code、Codex、SWE-agent、OpenHands、SWE-Gym、DeepSWE 等经验共同指向一个原则：训练环境不能为了安全把真实软件工程动作空间压得过窄，否则强化学习优化的是错误环境。

Stage 16G.0 必须回答：

1. 当前 RepoHarness 的训练工具面和目标部署工具面是否一致？
2. 当前是否存在“安全 baseline 可以接受，但不适合作为主 SWE 强化学习默认工具面”的能力缺口？
3. 是否应该把 `safe_structured_only`、`swe_public_core`、`swe_public_extended`、`redteam_restricted` 这类 profile 作为后续 Stage 16G.1 的设计输入？
4. 是否需要把 `run_public_command(...)` 或等价 public action shell 作为正式训练工具面候选，而不是继续依赖极窄 `execute_bash` 和 diagnostic-only `diagnostic_shell`？
5. 是否需要把 `apply_patch`、`create_file`、任务管理和 artifact 回读列为进入 Stage 20 warm-start 前的硬门槛？

### 4.9 reward hacking、权限拒绝和无效工具调用问题

本阶段还必须检查当前 RepoHarness 是否会把重要模型行为错误过滤掉。

至少回答：

1. 权限拒绝是否包含结构化恢复信息，例如 `denied_reason_code`、`policy_version`、`retryable`、`safe_alternative_tool`、`safe_rewrite_example`？
2. 无效工具调用、权限拒绝、patch apply failure、bad command、unknown file path 是否会被全部过滤掉，还是能作为训练负样本、局部反馈或诊断信号保留？
3. 哪些行为应该是 deterministic hard fail，例如读取 hidden verifier、读取 gold patch、访问宿主文件系统、测试篡改、依赖污染、git history exploit？
4. 哪些行为应该进入 quarantine 或 LLM-as-judge monitor，例如可疑 reward hacking、环境残留 artifact 使用、过宽修改、假验证、权限拒绝后的恢复质量差？
5. LLM-as-judge 在 RepoHarness 中应该作为 monitor / reviewer / quarantine / auxiliary signal，还是被错误当成唯一安全边界？

### 4.10 工具动作到训练目标的 linkage 问题

Stage 16G.0 还必须回答“工具动作是否真的进入训练目标”。不能只记录工具是否存在。

至少回答：

1. `edit_file`、未来 `create_file` / `apply_patch`、diagnostic shell 同步回来的公开源码修改，是否会进入 `final.patch`、`final.diff`、official prediction、TrainingView、reward builder、SFT / preference export？
2. scratch Python、复现脚本、临时 cache、临时 HOME / TMP 文件是否默认排除在 final patch 和训练目标之外？
3. final answer 中“我跑了测试”“测试通过 / 失败”的声明，是否能和真实 tool event、public feedback observation、verifier summary 交叉校验？
4. patch hygiene 的过滤事实是否能投影到 official prediction manifest、reward metadata 和 export metadata？
5. diagnostic-only 工具行为是否被完全丢弃，还是能以 public-safe facts 进入诊断、负样本、偏好数据或辅助 reward 候选？

## 5. 必须生成的公开产物

Stage 16G.0 的公开产物放在：

```text
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/
```

必须生成下面这些文件。

### 5.1 `stage16g0_acceptance_summary.json`

这是 Stage 16G.0 的顶层验收摘要。它不能只写“通过”，必须绑定所有公开报告的 sha256，并重新汇总关键计数。

最小字段：

```json
{
  "schema_version": "stage16g0.acceptance_summary.v1",
  "status": "passed",
  "stage16g0_complete": true,
  "source_inventory_sha256": "<sha256>",
  "claude_code_tool_inventory_sha256": "<sha256>",
  "repoharness_tool_inventory_sha256": "<sha256>",
  "external_swe_harness_reference_inventory_sha256": "<sha256>",
  "scaffold_capability_matrix_sha256": "<sha256>",
  "capability_gap_matrix_sha256": "<sha256>",
  "capability_probe_report_sha256": "<sha256>",
  "permission_and_shell_semantics_gap_report_sha256": "<sha256>",
  "test_feedback_and_project_command_gap_report_sha256": "<sha256>",
  "edit_write_file_operation_gap_report_sha256": "<sha256>",
  "patch_capture_verifier_reward_linkage_report_sha256": "<sha256>",
  "task_management_and_subagent_gap_report_sha256": "<sha256>",
  "training_tool_surface_profile_recommendations_sha256": "<sha256>",
  "training_deployment_mismatch_risk_report_sha256": "<sha256>",
  "reward_hacking_and_monitoring_gap_report_sha256": "<sha256>",
  "stage17_readiness_gate_report_sha256": "<sha256>",
  "required_next_stage_items_sha256": "<sha256>",
  "public_evidence_policy_sha256": "<sha256>",
  "path_leak_scan_report_sha256": "<sha256>",
  "capability_gap_count": 12,
  "p0_gap_count": 4,
  "blocking_for_stage17_data_freeze_count": 3,
  "blocking_for_stage20_warm_start_count": 5,
  "capability_probe_count": 8,
  "capability_probe_failed_count": 5,
  "public_path_leak_scan_passed": true,
  "stage17a_schema_only_allowed": true,
  "stage17b_real_data_freeze_allowed": false,
  "stage20_warm_start_data_generation_allowed": false,
  "stage21_formal_rl_allowed": false
}
```

`status=passed` 只有在所有必需报告都存在、sha256 都匹配、公开泄漏扫描通过、并且 Stage 17 readiness gate 已经明确给出放行或阻断结论时才允许出现。

上面的计数是非零示例，实际值必须从报告重新推导。`status=passed` 表示“盘点、probe 和验收完整”，不表示没有能力差距。`capability_gap_count`、`p0_gap_count`、`blocking_for_stage17_data_freeze_count`、`blocking_for_stage20_warm_start_count` 等计数字段必须从 `stage16g0_capability_gap_matrix.json`、`stage16g0_capability_probe_report.json` 和 `stage16g0_stage17_readiness_gate_report.json` 重新推导，不能只信任 summary 自身。

### 5.2 `stage16g0_source_inventory.json`

记录本阶段使用的输入来源。

最小字段：

```json
{
  "schema_version": "stage16g0.source_inventory.v1",
  "training_worktree_commit": "<commit>",
  "evaluation_worktree_label": "evaluation_worktree",
  "evaluation_worktree_commit": "<commit-or-unknown>",
  "source_documents": [
    {
      "source_label": "repo_harness_vs_claude_code_capability_gap_analysis",
      "sha256": "<sha256>",
      "public_reference_kind": "source_doc_sha256_only"
    },
    {
      "source_label": "gpt_advice_other_swe_harness_experience",
      "relative_path": "docs/harness_improve/gpt_advice.md",
      "sha256": "<sha256>",
      "public_reference_kind": "repo_relative_path_and_sha256"
    },
    {
      "source_label": "claude_code_typescript_agents_guide",
      "relative_path": "reference/claude-code-typescript-src/AGENTS.md",
      "sha256": "<sha256>",
      "public_reference_kind": "repo_relative_path_and_sha256"
    }
  ],
  "repo_harness_files": [
    {
      "relative_path": "src/repo_harness/tools/minimal.py",
      "exists": true,
      "sha256": "<sha256>"
    }
  ],
  "claude_code_reference_files": [
    {
      "source_label": "claude_code_typescript_reference",
      "relative_path": "<relative-path-under-reference>",
      "exists": true,
      "sha256": "<sha256>"
    }
  ],
  "public_path_policy_passed": true
}
```

公开文件不能包含真实本机绝对路径。真实路径只能保存在不提交的运行时私有记录中，并通过 sha256 绑定。

### 5.3 `stage16g0_claude_code_tool_inventory.json`

记录 Claude Code 参考实现中的工具能力。

至少覆盖：

```text
文件读取
图片、PDF、notebook 等非纯文本读取
文件搜索
文件编辑
文件创建
patch 或多文件编辑
Bash / shell
后台任务和命令监控
测试或命令执行
任务管理
子代理或后台任务
外部工具 / MCP / 插件 / 技能
延迟工具发现 / tool search
权限与用户确认
hooks
斜杠命令和命令扩展
语言服务器诊断
会话与上下文管理
长输出、分页和 artifact 回读
```

每条记录至少包含：

```json
{
  "capability_id": "bash_full_shell",
  "category": "shell",
  "claude_code_capability": "模型可以通过 Bash 工具执行非交互 shell 命令，并由权限系统决定是否允许。",
  "source_evidence": [
    {
      "source_label": "claude_code_typescript_reference",
      "relative_path": "<relative-path>",
      "evidence_kind": "static_source_scan"
    }
  ],
  "confidence": "high"
}
```

### 5.4 `stage16g0_external_swe_harness_reference_inventory.json`

记录 `docs/harness_improve/gpt_advice.md` 中提到的其他 SWE harness 经验，并将其转成 RepoHarness 后续设计约束。

至少覆盖：

```text
Cursor / Composer 类训练部署一致性原则
Claude Code 的真实工具能力和权限系统
Codex 的 workspace sandbox 与 approval 思路
SWE-agent / mini-SWE-agent 的稳定 shell 经验
OpenHands / SWE-Gym / DeepSWE 的可执行环境和测试闭环经验
reward hacking 与 agentic monitoring 经验
```

每条记录至少包含：

```json
{
  "reference_id": "mini_swe_agent_stable_shell",
  "source_document_label": "gpt_advice",
  "claim_summary": "稳定、可执行的 shell 能力是 SWE agent 形成定位、复现、修改、验证闭环的重要条件。",
  "repo_harness_design_implication": "不能把主训练工具面长期限制在极窄 execute_bash 上；必须评估正式 public diagnostic command 或 public action shell。",
  "confidence": "medium",
  "needs_primary_source_verification_before_public_claim": true
}
```

说明：`gpt_advice.md` 中引用的外部论文、博客和文档可以作为 Stage 16G.0 的设计参考，但如果后续要把这些结论写进正式公开技术报告，必须再用原始来源复核。Stage 16G.0 的工程计划只要求记录它们对 RepoHarness 工具面设计的影响。

### 5.5 `stage16g0_repoharness_tool_inventory.json`

记录 RepoHarness 当前工具能力。

每条记录至少包含：

```json
{
  "tool_name": "diagnostic_shell",
  "model_visible_default": false,
  "visible_in_scaffolds": ["patch_focused_react_diagnostic_shell"],
  "training_eligible_default": false,
  "side_channel_risk": true,
  "permission_policy_refs": ["command_policy", "diagnostic_session"],
  "build_tool_available": true,
  "default_registry_available": false,
  "scaffold_registry_available": true,
  "runtime_registry_bound": true,
  "known_limitations": [
    "第一版主要作为诊断工具，不是默认正式解题工具"
  ]
}
```

RepoHarness 当前已有的基础导航和长输出能力也必须显式盘点，不能只关注 shell。至少需要覆盖：

```text
list_files
glob_files
grep
symbol_search
read_file
read_tool_result_artifact
git_diff
edit_file
bash
execute_bash
diagnostic_shell
run_tests
update_working_state
```

其中 `bash`、`execute_bash`、`diagnostic_shell` 必须作为三个不同工具或能力层级分别建模，不能合并成一个笼统的 shell 能力。

每个工具还必须记录输出可见性和 artifact 语义：

```text
model_visible_output_truncated
raw_artifact_runtime_private
artifact_replay_tool_available
path_redaction_applied
training_view_projection_allowed
diagnostic_side_channel_only
```

尤其是 `read_tool_result_artifact`、长输出分页、raw command artifact 私有化和路径脱敏，必须作为能力矩阵中的显式列，不能只依赖最终 path leak scan。

### 5.6 `stage16g0_scaffold_capability_matrix.json`

按 scaffold 记录模型真实可见能力。

必须至少覆盖：

```text
simple_react
patch_focused_react
patch_focused_react_execute_bash
patch_focused_react_diagnostic_shell
patch_focused_react_mini_shell
single_shot_patch
planner_coder_verifier 或当前存在的等价多角色 scaffold
```

如果某个 scaffold 不存在，必须记录：

```json
{
  "scaffold_name": "planner_coder_verifier",
  "exists": false,
  "status": "not_present_in_current_worktree"
}
```

每个存在的 scaffold 至少记录：

```json
{
  "scaffold_name": "patch_focused_react",
  "allowed_tool_names": ["read_file", "grep", "edit_file"],
  "executor_registry_consistent": true,
  "scaffold_registry_available": true,
  "runtime_registry_bound": true,
  "registry_binding_notes": "scaffold 声明工具集合、构造出的 registry 和运行时注入 registry 必须一致",
  "has_shell": false,
  "has_file_create": false,
  "has_patch_apply": false,
  "has_parameterized_public_tests": false,
  "has_task_management": "partial",
  "public_environment_injected": true,
  "stage16e_patch_hygiene_bound": true
}
```

### 5.7 `stage16g0_capability_gap_matrix.json`

这是本阶段最重要的报告。

每条差距记录必须包含：

```json
{
  "capability_id": "parameterized_public_test_command",
  "category": "test_feedback",
  "claude_code_baseline": "模型可以通过 shell 或测试命令执行定向公开测试。",
  "repo_harness_status": "partial",
  "repo_harness_evidence": [
    "run_tests 不支持任意测试命令参数",
    "diagnostic_shell 可用但不是默认正式训练工具"
  ],
  "ability_impact": "模型难以运行单个失败测试或自写复现，信用分配变差。",
  "training_risk": "模型可能学习静态猜测而不是动态验证。",
  "security_reason_if_blocked": "需要隔离 hidden verifier、共享依赖环境和宿主敏感路径。",
  "recommended_action": "设计正式 public diagnostic shell 或 run_public_command 工具。",
  "recommended_stage": "16G.1",
  "blocking_for_stage17_data_freeze": true,
  "blocking_for_stage20_warm_start": true
}
```

必须额外包含下面这些能力项，不能只在自然语言中提到：

```text
scratch_python_or_reproduction_script
project_command_routing
dependency_setup_or_private_overlay
parameterized_public_test_command
tool_result_artifact_replay
patch_capture_verifier_reward_linkage
permission_denial_recovery
```

`repo_harness_status` 必须使用下面的枚举：

```text
present_default
present_non_default
present_diagnostic_only
partial
missing
unknown
blocked_by_policy
blocked_by_backend
deferred
```

### 5.7.1 `stage16g0_capability_probe_report.json`

记录 Stage 16G.0 的小型可执行能力 probe。probe 必须使用当前已有 fixture 或临时 workspace，不允许修改 harness 行为，不允许放宽安全策略。

至少覆盖下面的 probe：

```json
{
  "schema_version": "stage16g0.capability_probe.v1",
  "probes": [
    {
      "probe_id": "default_scaffold_read_search_edit_patch_reward",
      "scaffold": "patch_focused_react",
      "profile": "current_default",
      "capability_under_test": "read_search_edit_patch_verifier_reward_loop",
      "expected_result": "pass_or_structured_gap",
      "actual_status": "structured_gap",
      "gap_ids": ["parameterized_public_test_command_missing"],
      "evidence_refs": ["repo_relative_fixture:<sha256>"],
      "model_visible_tool_sequence": ["read_file", "grep", "edit_file"],
      "final_patch_generated": true,
      "verifier_or_reward_reached": true
    },
    {
      "probe_id": "scratch_python_reproduction_script",
      "capability_under_test": "scratch_python_or_reproduction_script",
      "actual_status": "blocked_or_diagnostic_only",
      "temporary_artifact_excluded_from_final_patch": true,
      "training_eligibility_status": "not_training_candidate"
    },
    {
      "probe_id": "scaffold_registry_consistency",
      "capability_under_test": "allowed_tools_match_executor_registry",
      "actual_status": "passed"
    }
  ],
  "probe_count": 3,
  "failed_or_gap_probe_count": 2
}
```

`actual_status` 必须使用稳定枚举，例如：

```text
passed
structured_gap
blocked_by_policy
blocked_by_missing_tool
blocked_by_scaffold
diagnostic_only
not_run_with_reason
```

probe 失败不代表 Stage 16G.0 失败；它代表能力差距被实证记录。只有 probe 缺失、证据不可复核、公开泄漏或把失败误标为通过，才应导致 Stage 16G.0 失败。

### 5.8 `stage16g0_permission_and_shell_semantics_gap_report.json`

专门记录权限和 shell 语义差距。

至少覆盖：

```text
execute_bash 安全最小工具面
diagnostic_shell 是否默认可见
Docker diagnostic shell
Local filesystem-persistent diagnostic shell
bash -lc 语义
run directory 隔离
共享依赖环境只读
公开 workspace 与 runtime-private 隔离
命令拒绝后的恢复建议
legacy bash 工具的真实语义和限制
public_action_shell / run_public_command 候选能力
final-only hidden verifier 与 public diagnostic command 解耦
```

必须明确区分：

```text
hidden final verifier 不可见
public diagnostic command 可以可见
```

这两个概念不能混在一起。

如果当前代码把 final-only / hidden evaluator facts 与 public diagnostic command 一起禁用，报告必须把它标成能力缺口或待确认风险，而不能只写“安全策略拒绝”。隐藏 verifier 不可见是硬边界，公开诊断命令是否可见是训练工具面设计问题。

### 5.9 `stage16g0_test_feedback_and_project_command_gap_report.json`

专门记录公开测试和项目命令能力差距。

至少回答：

1. 当前 `run_tests` 能否运行任意公开测试命令？
2. 当前模型能否表达“只运行一个 pytest case”？
3. 当前模型能否运行项目脚本、Django test label、Sphinx test、tox 或 nox？
4. 当前是否应该设计 `run_public_command(...)` 或 `run_project_test(...)`？
5. 哪些命令可以作为正式训练工具，哪些只能作为诊断侧通道？
6. 当前任务 schema 是否能声明公开命令模板、测试 selector 参数和允许的 public diagnostic command。
7. 项目 setup 命令、依赖安装、私有 virtualenv / overlay、共享依赖环境只读策略分别由谁控制。
8. 如果依赖 setup 被拒绝，拒绝是否结构化说明 `shared_dependency_write_denied`、`private_overlay_missing` 或 `dependency_setup_unsupported`，而不是让模型只能猜测。
9. 哪些公开命令结果可以作为 public feedback observation 进入模型上下文，哪些只能进入 runtime-private artifact。

### 5.10 `stage16g0_edit_write_file_operation_gap_report.json`

专门记录编辑和文件操作差距。

至少覆盖：

```text
edit_file exact replace
create_file
write_file
delete_file
move_file
mkdir
apply_patch / unified diff
批量编辑
新增文件进入 final.patch
Stage 16E patch hygiene 对这些操作的支持情况
```

### 5.10.1 `stage16g0_patch_capture_verifier_reward_linkage_report.json`

专门记录工具动作是否能进入训练目标。该报告必须把“工具定义存在”和“训练事实可消费”分开。

至少覆盖：

```json
{
  "schema_version": "stage16g0.patch_capture_verifier_reward_linkage.v1",
  "operations": [
    {
      "operation_id": "edit_existing_source_file",
      "tool_or_profile": "edit_file",
      "enters_final_patch": true,
      "enters_official_prediction": true,
      "enters_training_view": true,
      "reward_builder_can_reference_public_facts": true,
      "export_visible": true,
      "known_gaps": []
    },
    {
      "operation_id": "scratch_python_reproduction_script",
      "tool_or_profile": "diagnostic_shell_or_future_scratch_python",
      "enters_final_patch": false,
      "enters_official_prediction": false,
      "diagnostic_facts_public_safe": "partial",
      "known_gaps": ["no_formal_scratch_python_tool"]
    }
  ],
  "final_answer_claim_cross_check": {
    "test_claim_requires_tool_event": true,
    "unsupported_claim_status": "diagnostic_or_negative_signal"
  }
}
```

必须明确：

1. 公开源码修改如何进入 `final.patch`、`final.diff`、official prediction、TrainingView、reward metadata 和 export。
2. 临时脚本、cache、复现 artifact、HOME / TMP 文件如何被排除在 final patch 之外。
3. final answer 中的测试声明如何和真实 tool event / verifier summary 交叉校验。
4. patch hygiene 的过滤事实如何投影到 official prediction manifest、reward metadata 和 export metadata。
5. 只在 diagnostic side channel 中出现的行为，是否可作为训练负样本或辅助 reward 候选。

### 5.11 `stage16g0_task_management_and_subagent_gap_report.json`

专门记录任务管理、子代理和外部工具差距。

至少覆盖：

```text
update_working_state
todo_write 或等价任务列表
subagent / background task
external tools / MCP / plugin / skill
hooks
权限确认与恢复路径
```

短期不要求实现完整外部工具系统，但必须说明训练轨迹 schema 是否需要预留这些能力位。

### 5.12 `stage16g0_training_tool_surface_profile_recommendations.json`

给出后续可能的工具面 profile 设计建议。

至少包含：

```json
{
  "recommended_profiles": [
    {
      "profile_name": "swe_public_diagnostic_default",
      "intended_use": "正式 SWE 训练和 Stage 16.5 强模型诊断",
      "must_include": [
        "read_file",
        "grep",
        "glob_files",
        "edit_file",
        "create_file",
        "apply_patch_or_equivalent",
        "public_diagnostic_shell_or_run_public_command",
        "git_diff",
        "todo_or_working_state"
      ],
      "must_exclude": [
        "hidden verifier",
        "gold patch",
        "official verifier private artifact",
        "runtime-private path",
        "shared dependency write"
      ],
      "open_questions": [
        "是否将 diagnostic_shell 升级为正式训练工具，还是新增更结构化的 run_public_command"
      ]
    }
  ]
}
```

该报告必须显式评估下面四类 profile 是否适合作为后续阶段目标：

```text
safe_structured_only：安全结构化基线，可以保留，但不能默认视为主 SWE 强化学习工具面。
swe_public_core：候选主训练工具面，至少覆盖读、搜、编辑、新建文件、patch、公开命令、diff、任务状态和 artifact 回读。
swe_public_extended：更接近 Claude Code / Cursor 的扩展工具面，可以包含持久 shell、LSP、后台任务、子代理、MCP 或外部工具代理。
redteam_restricted：用于 reward hacking、越权访问和隐藏信息泄漏压力测试的受限 profile。
```

### 5.13 `stage16g0_training_deployment_mismatch_risk_report.json`

专门记录训练工具面与目标部署工具面不一致的风险。

最小字段：

```json
{
  "schema_version": "stage16g0.training_deployment_mismatch.v1",
  "target_deployment_style": "claude_code_like_swe_agent",
  "current_default_training_profile": "<profile-or-scaffold>",
  "mismatch_risks": [
    {
      "risk_id": "static_guessing_due_to_missing_public_command",
      "risk_level": "P0",
      "description": "模型无法稳定运行公开诊断命令和定向测试，可能学习静态猜测补丁。",
      "evidence_refs": ["stage16g0_capability_gap_matrix:parameterized_public_test_command"],
      "recommended_stage": "16G.1"
    }
  ],
  "stage17_data_freeze_risk": "blocked_until_tool_profile_decision"
}
```

### 5.14 `stage16g0_reward_hacking_and_monitoring_gap_report.json`

专门记录 reward hacking、权限拒绝恢复、无效工具调用和 LLM-as-judge 监控差距。

至少包含：

```json
{
  "schema_version": "stage16g0.reward_hacking_monitoring_gap.v1",
  "hard_fail_categories": [
    "hidden_verifier_access",
    "gold_patch_access",
    "host_filesystem_escape",
    "test_tampering",
    "dependency_tampering",
    "git_history_exploit"
  ],
  "quarantine_categories": [
    "reward_hacking_suspicion",
    "strange_environment_artifact_usage",
    "suspicious_public_test_modification",
    "unexplained_huge_diff"
  ],
  "auxiliary_reward_candidates": [
    "evidence_backed_validation",
    "good_permission_denial_recovery",
    "minimal_diff",
    "accurate_final_test_report"
  ],
  "invalid_tool_call_policy": "不能默认过滤；需要区分模型行为、权限拒绝、基础设施失败和 harness 崩溃。",
  "llm_judge_role": "monitor_reviewer_quarantine_auxiliary_signal_not_primary_safety_boundary"
}
```

必须明确：

```text
基础安全边界依赖 deterministic policy、sandbox、路径隔离、artifact hygiene 和 verifier 隔离；
LLM-as-judge 只能作为监控、审查、隔离或辅助奖励信号，不能替代确定性权限边界。
```

### 5.15 `stage16g0_stage17_readiness_gate_report.json`

明确 Stage 17 是否可以继续推进。

必须至少包含：

```json
{
  "stage17a_schema_only_allowed": true,
  "stage17b_real_data_freeze_allowed": false,
  "stage20_warm_start_data_generation_allowed": false,
  "stage21_formal_rl_allowed": false,
  "blocking_reasons": [
    "default_training_scaffold_lacks_formal_public_diagnostic_shell",
    "parameterized_public_test_command_missing_or_diagnostic_only"
  ],
  "conditions_to_unblock": [
    "Stage 16G.1 formal tool surface design completed",
    "Stage 16G.2 selected tool profile implemented and verified",
    "Stage 16.5 representative harness diagnostic passed on unified run-episode-task"
  ]
}
```

如果盘点发现当前工具面已经足够，也可以把 `stage17b_real_data_freeze_allowed` 设为 true，但必须提供具体 evidence。不能只凭主观判断放行。

### 5.16 `stage16g0_required_next_stage_items.json`

把差距转成后续可执行阶段项。

每条记录至少包含：

```json
{
  "item_id": "stage16g1_formal_public_diagnostic_profile_design",
  "priority": "P0",
  "source_gap_ids": ["parameterized_public_test_command", "formal_shell_capability"],
  "recommended_stage": "16G.1",
  "recommended_owner": "training_worktree",
  "evaluation_worktree_role": "provide representative task probes",
  "acceptance_hint": "必须证明 public diagnostic 能力不暴露 hidden verifier，并且可以进入正式训练候选轨迹"
}
```

### 5.17 `stage16g0_public_evidence_policy.json`

记录公开证据规则。

至少要求：

1. 公开产物不包含真实本机绝对路径。
2. 公开产物不包含 hidden verifier 原文、gold patch、test patch、官方 verifier 私有输出、provider secret、API key。
3. 允许出现风险类别名称本身，例如 `gold_patch`，但只能作为规则说明或枚举值，不能出现真实内容。
4. 如果需要引用私有证据，使用 opaque ref 和 sha256。

### 5.18 `stage16g0_path_leak_scan_report.json`

记录公开产物泄漏扫描结果。

扫描范围至少包含：

```text
docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/*.json
docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0/*.md
```

注意：计划文档和规则文档允许以“风险类别说明”的形式出现 `gold_patch`、`test_patch`、`hidden_verifier` 等词；但是正式 inventory、matrix 和 summary 不能包含真实泄漏内容。泄漏扫描器必须区分“风险类别名称”和“真实敏感内容”。

## 6. 建议的实现方式

Stage 16G.0 可以先用脚本或一次性工具生成报告，但必须保证输出稳定、可复查、可重跑。

建议新增脚本：

```text
scripts/pre_verl/build_stage16g0_capability_gap_inventory.py
```

如果实现者认为不需要新增脚本，也可以手工生成报告；但必须满足：

1. 每个报告都是合法 JSON。
2. 每个 source evidence 都能回查到相应文件和 sha256。
3. 每个 gap item 都有 evidence，不允许只有主观描述。
4. 报告中的结论可以被 reviewer 复核。

## 7. 验收命令

本阶段至少需要运行：

```bash
git diff --check -- docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md
```

Stage 16G.0 实施完成后，还需要运行：

```bash
PATH=.venv/bin:$PATH python -m compileall -q src
PATH=.venv/bin:$PATH python -m pytest -q tests/unit/test_repo_harness_stage16f6_real_model_smoke.py
```

如果新增了 inventory builder 或 inspector，则必须新增对应测试，并运行：

```bash
PATH=.venv/bin:$PATH python -m pytest -q <stage16g0-new-tests>
```

还需要进行 JSON 解析检查：

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path("docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0")
for path in sorted(root.glob("*.json")):
    json.loads(path.read_text())
print("stage16g0_json_parse_ok")
PY
```

如果生成了 capability probe evidence，还必须运行 probe 结果一致性检查：

```bash
PATH=.venv/bin:$PATH python -m pytest -q <stage16g0-capability-probe-tests>
```

检查项至少包括：

```text
probe record 中的 actual_status 与真实 probe 输出一致
scaffold allowed tools 与 executor registry 一致
scratch / temporary artifact 不进入 final.patch
final answer test claim 能被 tool event 或 verifier summary 交叉校验
```

## 8. 完成标准

Stage 16G.0 只有在下面条件全部满足时，才可以视为完成：

1. 所有必需公开产物都存在。
2. 所有 JSON 产物都能解析。
3. `stage16g0_acceptance_summary.json` 绑定所有必需公开报告的 sha256，并且 summary 中的计数可以从报告重新推导。
4. `stage16g0_capability_gap_matrix.json` 至少覆盖 shell、测试反馈、编辑、文件创建、patch、任务管理、子代理或外部工具、权限恢复、长输出分页和 artifact 回读这九类能力。
5. `stage16g0_capability_probe_report.json` 已经记录最小可执行 probe，且 probe 失败被结构化归类为能力差距，不被伪装成通过。
6. `stage16g0_scaffold_capability_matrix.json` 明确记录每个 scaffold 的模型可见工具集合和 executor registry 一致性。
7. `stage16g0_test_feedback_and_project_command_gap_report.json` 明确记录 public test selector、project command routing、dependency setup / private overlay 和共享依赖只读边界。
8. `stage16g0_patch_capture_verifier_reward_linkage_report.json` 明确记录工具动作如何进入 final patch、verifier、reward、TrainingView、official prediction 和 export。
9. `stage16g0_external_swe_harness_reference_inventory.json` 已经把其他 SWE harness 经验转成 RepoHarness 后续设计约束。
10. `stage16g0_training_deployment_mismatch_risk_report.json` 明确判断当前默认训练工具面是否足够接近目标部署工具面。
11. `stage16g0_reward_hacking_and_monitoring_gap_report.json` 明确区分 deterministic hard fail、quarantine、auxiliary reward、invalid tool call 和基础设施失败。
12. `stage16g0_stage17_readiness_gate_report.json` 明确给出 Stage 17A、Stage 17B、Stage 20、Stage 21 的放行或阻断结论。
13. 公开产物不包含真实本机绝对路径或敏感私有内容。
14. 子代理或 reviewer 完成只读复核，并且没有 P1 / P2 阻断问题。

## 9. 后续阶段预期

Stage 16G.0 完成后，根据差距矩阵再决定下一阶段。预计可能拆成：

```text
Stage 16G.1：工具 registry 与能力矩阵设计，固定 profile taxonomy 和训练资格门禁
Stage 16G.2：结构化 read / grep / glob / edit / write / apply_patch 能力补齐
Stage 16G.3：run_public_command / run_project_test / scratch_python 公开诊断工具设计和实现
Stage 16G.4：controlled diagnostic shell、dependency setup、private overlay 和项目命令 routing
Stage 16G.5：改造完成后的 Claude Code / mini-SWE-agent parity probe；它只验证 Stage 16G.1 到 Stage 16G.4 的实现效果，不承担第一次 baseline 对照
Stage 16G.6：training eligibility gates、export / reward / policy-loss 接入验收
Stage 17A：数据 registry / manifest / split 规则 schema
```

如果 Stage 16G.0 发现当前工具面不足以支持真实 SWE 强化学习，那么 Stage 17A 可以继续做 schema-only 工作，但 Stage 17B 的真实数据冻结、Stage 20 的 warm-start 数据生产和 Stage 21 的正式强化学习都必须等待工具面改造和代表性诊断完成。
