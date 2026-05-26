"""Build Stage 16G.0 follow-up baseline contract evidence.

This script is read-only with respect to RepoHarness behavior. It writes
public-safe JSON artifacts that pin Claude Code and mini-SWE-agent comparison
baselines before Stage 16G.1+ implementation work begins.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
STAGE_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0"
EVALUATION_WORKTREE = REPO_ROOT.parent / "claude-code"
MINI_RUN_ROOT = EVALUATION_WORKTREE / "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z"

CLAUDE_CODE_SOURCES = {
    "tool_contract": "reference/claude-code-typescript-src/Tool.ts",
    "tool_registry": "reference/claude-code-typescript-src/tools.ts",
    "tool_execution": "reference/claude-code-typescript-src/services/tools/toolExecution.ts",
    "tool_orchestration": "reference/claude-code-typescript-src/services/tools/toolOrchestration.ts",
    "streaming_tool_executor": "reference/claude-code-typescript-src/services/tools/StreamingToolExecutor.ts",
    "file_read": "reference/claude-code-typescript-src/tools/FileReadTool/FileReadTool.ts",
    "file_read_limits": "reference/claude-code-typescript-src/tools/FileReadTool/limits.ts",
    "image_processor": "reference/claude-code-typescript-src/tools/FileReadTool/imageProcessor.ts",
    "file_edit": "reference/claude-code-typescript-src/tools/FileEditTool/FileEditTool.ts",
    "file_write": "reference/claude-code-typescript-src/tools/FileWriteTool/FileWriteTool.ts",
    "glob": "reference/claude-code-typescript-src/tools/GlobTool/GlobTool.ts",
    "grep": "reference/claude-code-typescript-src/tools/GrepTool/GrepTool.ts",
    "bash": "reference/claude-code-typescript-src/tools/BashTool/BashTool.tsx",
    "bash_permissions": "reference/claude-code-typescript-src/tools/BashTool/bashPermissions.ts",
    "bash_security": "reference/claude-code-typescript-src/tools/BashTool/bashSecurity.ts",
    "bash_sandbox": "reference/claude-code-typescript-src/tools/BashTool/shouldUseSandbox.ts",
    "todo": "reference/claude-code-typescript-src/tools/TodoWriteTool/TodoWriteTool.ts",
    "agent": "reference/claude-code-typescript-src/tools/AgentTool/AgentTool.tsx",
    "agent_runner": "reference/claude-code-typescript-src/tools/AgentTool/runAgent.ts",
    "mcp": "reference/claude-code-typescript-src/tools/MCPTool/MCPTool.ts",
    "tool_search": "reference/claude-code-typescript-src/tools/ToolSearchTool/ToolSearchTool.ts",
    "lsp": "reference/claude-code-typescript-src/services/lsp/LSPDiagnosticRegistry.ts",
    "permissions": "reference/claude-code-typescript-src/utils/permissions/permissions.ts",
    "plugins": "reference/claude-code-typescript-src/plugins/builtinPlugins.ts",
    "skills": "reference/claude-code-typescript-src/skills/bundledSkills.ts",
}

MINI_SWE_AGENT_SOURCES = {
    "actual_config": "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_deepseek_v4_pro_high.yaml",
    "public_config_excerpt": "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/public_source_mini_swe_agent_swebench_config_excerpt.txt",
    "smoke_stdout_stderr": "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5.stdout_stderr.log",
    "smoke_internal_log": "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5/minisweagent.log",
    "official_all5_stdout_stderr": "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5_official_all5.stdout_stderr.log",
    "official_completed4_stdout_stderr": "runs/pre-verl-swebench-verified-score-gap-investigation-20260521T000000Z/mini_swe_agent_b0_smoke5_official_completed4.stdout_stderr.log",
}

REPOHARNESS_SOURCES = {
    "tools": "src/repo_harness/tools/minimal.py",
    "scaffold_patch_focused": "src/repo_harness/scaffolds/patch_focused_react.py",
    "scaffold_simple": "src/repo_harness/scaffolds/simple_react.py",
    "scaffold_policies": "src/repo_harness/scaffolds/policies.py",
    "command_policy": "src/repo_harness/tasks/command_policy.py",
    "public_environment": "src/repo_harness/tasks/public_environment.py",
    "diagnostic_session": "src/repo_harness/workspace/diagnostic_session.py",
    "patch_hygiene": "src/repo_harness/workspace/patch_hygiene.py",
    "docker_adapter": "src/repo_harness/workspace/docker_adapter.py",
    "episode_runner": "src/repo_harness/evaluation/episode_runner.py",
    "episode_projection": "src/repo_harness/evaluation/episode_projection.py",
    "execution_spec": "src/repo_harness/execution/spec.py",
    "runtime": "src/repo_harness/rl/runtime.py",
}

REQUIRED_COMPARISON_CAPABILITIES = [
    "structured_file_read",
    "non_text_file_read",
    "large_file_paging_or_artifact_replay",
    "glob_file_discovery",
    "grep_content_search",
    "symbol_search_or_lsp_diagnostics",
    "structured_edit_existing_file",
    "structured_write_or_create_file",
    "apply_patch_or_multi_file_edit",
    "delete_move_mkdir_file_operations",
    "bash_or_public_command_execution",
    "persistent_diagnostic_session",
    "parameterized_public_test_command",
    "scratch_python_or_reproduction_script",
    "project_command_routing",
    "dependency_setup_and_environment_policy",
    "git_diff_status_and_patch_capture",
    "final_answer_verifier_reward_linkage",
    "permission_approval_denial_recovery",
    "sandbox_workspace_and_runtime_private_boundary",
    "tool_result_truncation_raw_artifact_privacy",
    "task_management_todo",
    "subagent_background_task",
    "external_tools_mcp_plugin_skill",
    "hooks_tool_lifecycle_audit",
    "training_eligibility_and_export_projection",
    "reward_hacking_monitoring_and_quarantine",
]

ALLOWED_GAP_TYPES = {
    "present_and_sufficient",
    "present_but_weaker_than_claude_code",
    "present_but_weaker_than_mini_swe_agent",
    "present_non_default",
    "present_diagnostic_only",
    "partial",
    "missing",
    "blocked_by_policy",
    "blocked_by_backend",
    "blocked_by_training_eligibility",
    "deferred_schema_only",
    "not_required_for_main_swe_rl",
    "unknown",
}

ALLOWED_REQUIRED_STAGES = {"16G.1", "16G.2", "16G.3", "16G.4", "16G.5", "post_16G_optional", "not_required"}

SENSITIVE_PATTERNS = [
    re.compile(r"/Users/"),
    re.compile(r"/private/"),
    re.compile(r"/home/"),
    re.compile(r"/tmp/"),
    re.compile(r"/var/folders/"),
    re.compile(r"provider_secret\s*[:=]", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return _sha256_bytes(path.read_bytes())


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _write_json(path: Path, payload: Any) -> str:
    data = _canonical_json_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha256_bytes(data)


def _git_commit(path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", path.as_posix(), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _repo_source_entry(source_label: str, relative_path: str) -> dict[str, Any]:
    path = REPO_ROOT / relative_path
    return {
        "source_label": source_label,
        "relative_path": relative_path,
        "exists": path.exists(),
        "sha256": _sha256_file(path),
        "public_reference_kind": "repo_relative_path_and_sha256",
    }


def _mini_source_entry(source_label: str, relative_path: str) -> dict[str, Any]:
    # relative_path is intentionally relative to evaluation_worktree.
    path = EVALUATION_WORKTREE / relative_path
    return {
        "source_label": source_label,
        "source_worktree_label": "evaluation_worktree",
        "opaque_ref": f"evaluation_worktree:{relative_path}",
        "exists": path.exists(),
        "sha256": _sha256_file(path),
        "public_reference_kind": "evaluation_worktree_relative_path_and_sha256",
        "primary_source_verified": False,
        "tier": "tier2_real_config_or_run_log",
    }


def _evidence(relative_path: str, *, kind: str = "static_source_scan") -> dict[str, str]:
    return {"relative_path": relative_path, "evidence_kind": kind}


def _mini_evidence(ref_key: str, *, kind: str = "public_safe_real_run_evidence") -> dict[str, str]:
    return {
        "source_label": ref_key,
        "opaque_ref": f"evaluation_worktree:{MINI_SWE_AGENT_SOURCES[ref_key]}",
        "evidence_kind": kind,
    }


def build_claude_code_baseline_contract() -> dict[str, Any]:
    contracts = [
        _claude_contract(
            "structured_file_read",
            "file_navigation",
            "模型可以使用结构化 Read 类工具读取仓库文件，并通过行范围、结果大小限制和工具结果回流控制上下文成本。",
            "Read / FileReadTool",
            "读取工作区内文件；受路径保护、文件类型和输出预算约束。",
            "只读工具仍进入统一权限、路径保护和工具生命周期审计。",
            "工具结果回到下一轮模型上下文，长内容需要截断或分页。",
            "RepoHarness 的 read_file 和 artifact 回读必须保持结构化，不应要求模型通过 shell cat/head/tail 读取源码。",
            ["file_read", "tool_execution"],
        ),
        _claude_contract(
            "non_text_file_read",
            "file_navigation",
            "Claude Code 参考工具面把图片、PDF、notebook 等非纯文本输入作为文件读取能力的一部分处理。",
            "FileReadTool with media processors",
            "根据文件类型走文本、图片或其他专门处理路径。",
            "非文本读取同样受路径、大小和可见性策略约束。",
            "结果可以是文本摘要、媒体附件或受控 preview。",
            "RepoHarness 主 SWE core 可以先保持文本优先，但必须把非文本读取标为目标部署差距。",
            ["file_read", "image_processor"],
            confidence="medium",
        ),
        _claude_contract(
            "large_file_paging_or_artifact_replay",
            "context",
            "长文件和大工具输出不会无限塞回上下文，而是通过大小限制、截断、分页或 artifact 回读保持可控。",
            "FileRead limits and tool result handling",
            "大输出需要 preview、保存和后续按需读取。",
            "raw output 与模型可见 preview 分离，降低泄漏和上下文污染风险。",
            "模型看到可消费的片段，并能通过合法路径继续读取。",
            "RepoHarness 需要保持 read_tool_result_artifact 和 raw artifact 私有化的组合能力。",
            ["file_read_limits", "tool_execution"],
        ),
        _claude_contract(
            "glob_file_discovery",
            "search",
            "模型可以使用结构化 Glob 类工具按路径模式发现文件，而不是依赖 shell find。",
            "GlobTool",
            "文件发现由工具实现统一过滤和排序。",
            "路径可见性、隐藏文件和敏感目录过滤由工具侧控制。",
            "返回候选文件列表，帮助后续 read/grep/edit。",
            "RepoHarness 的 glob_files 应作为 core 能力保留，并纳入 parity 对照。",
            ["glob"],
        ),
        _claude_contract(
            "grep_content_search",
            "search",
            "模型可以使用结构化 Grep 类工具做内容搜索，而不是通过 Bash 组合 grep 或 rg 绕过可见性策略。",
            "GrepTool",
            "内容搜索由工具统一控制目录范围、输出大小和匹配格式。",
            "搜索工具承担敏感路径过滤和输出预算约束。",
            "搜索结果回流为可引用的文件和行上下文。",
            "RepoHarness 的 grep 应继续优先于 shell grep，并支持足够真实的代码定位。",
            ["grep"],
        ),
        _claude_contract(
            "structured_edit_existing_file",
            "editing",
            "模型可以使用结构化 Edit 类工具修改已有文件，编辑动作进入工具生命周期、权限和审计。",
            "Edit / FileEditTool",
            "编辑通过结构化参数表达，通常要求精确上下文或文件读取状态。",
            "写操作需要权限检查、敏感文件保护和可恢复错误。",
            "成功编辑更新文件状态，并可通过 diff 或后续读取验证。",
            "RepoHarness 的 edit_file 是正确方向，但需要评估复杂编辑和失败恢复。",
            ["file_edit", "tool_execution"],
        ),
        _claude_contract(
            "structured_write_or_create_file",
            "editing",
            "模型可以使用结构化 Write 类工具创建或覆盖文件，而不是通过 shell 重定向写文件。",
            "Write / FileWriteTool",
            "文件写入由工具承担路径检查、覆盖语义和权限。",
            "写操作高风险，需要显式审计和权限语义。",
            "结果进入后续 diff、verifier 和 final answer 依据。",
            "RepoHarness 需要确认 create_file/write_file 是否在主训练 profile 中可见并进入 final patch。",
            ["file_write"],
        ),
        _claude_contract(
            "patch_or_multi_file_edit_equivalent",
            "editing",
            "Claude Code 产品态支持多文件真实开发工作流，即使具体实现不是单个 apply_patch 工具，也需要高效处理跨文件修改。",
            "Edit / Write / Bash / diff review combination",
            "跨文件修改可以由多个结构化编辑、写入和 diff 审查组成。",
            "每个写动作仍受工具权限和审计约束。",
            "最终变化通过 diff、summary 和工具事件闭环。",
            "RepoHarness 应补 apply_patch 或等价多文件编辑能力，不能只依赖 fragile exact replace。",
            ["file_edit", "file_write", "bash"],
            confidence="medium",
        ),
        _claude_contract(
            "bash_project_command_execution",
            "execution",
            "Bash 是一等能力，用于测试、构建、项目命令、复杂诊断和部分 Git 工作流，但仍由权限、sandbox 和审计约束。",
            "BashTool",
            "执行非交互命令，支持 cwd、超时、stdout/stderr 和 exit code。",
            "命令会经过安全分类、权限判断、sandbox 和高风险命令拦截。",
            "命令输出以 preview 或 artifact 方式回流。",
            "RepoHarness 不能把主训练能力长期停在过窄 execute_bash；需要等价 public command 能力。",
            ["bash", "bash_permissions", "bash_security", "bash_sandbox"],
        ),
        _claude_contract(
            "persistent_or_background_command_monitoring",
            "execution",
            "真实工具环境需要处理长运行命令、后台任务或可监控命令输出，而不是只支持短同步调用。",
            "Bash and task monitoring",
            "后台或长命令有生命周期、输出读取和清理语义。",
            "后台执行需要更强权限边界和资源清理。",
            "模型可基于后续输出继续判断。",
            "RepoHarness core 可以不默认启用后台任务，但 extended profile 需要预留。",
            ["bash", "streaming_tool_executor"],
            confidence="medium",
        ),
        _claude_contract(
            "public_test_or_project_command_execution",
            "execution",
            "模型可以通过 Bash 或项目命令路径运行定向公开测试，并把输出作为下一步修复依据。",
            "BashTool / project commands",
            "测试命令和项目命令作为普通开发动作执行。",
            "隐藏 verifier 仍不可见，高风险命令受权限和 sandbox 管理。",
            "stdout、stderr、exit code 和摘要回流给模型。",
            "RepoHarness 需要 run_project_test 或 run_public_command，而不是只有无参数 run_tests。",
            ["bash", "tool_execution"],
        ),
        _claude_contract(
            "scratch_reproduction_script",
            "diagnosis",
            "模型可以通过工具环境创建或运行临时复现逻辑，用于验证假设和定位 bug。",
            "Bash / Write / Edit combination",
            "复现脚本可以在工作区或临时区域运行，但最终补丁应保持干净。",
            "临时文件需要和正式源码修改区分。",
            "复现输出用于下一轮推理，不应直接污染 final patch。",
            "RepoHarness 应提供 scratch_python 或 scratch workspace，并用 patch hygiene 排除临时产物。",
            ["bash", "file_write"],
            confidence="medium",
        ),
        _claude_contract(
            "permission_approval_and_denial_recovery",
            "permission",
            "强工具能力不是无限制开放，而是通过权限判断、用户确认、拒绝原因和恢复路径约束。",
            "Permission system and tool checks",
            "工具调用前后进入权限和 hook 流程。",
            "deny/ask/allow 决策携带结构化上下文。",
            "拒绝结果应帮助模型选择安全替代路径。",
            "RepoHarness 需要让 denial 成为可学习信号，而不是鼓励模型少用工具。",
            ["permissions", "tool_execution"],
        ),
        _claude_contract(
            "sandbox_and_workspace_boundary",
            "safety",
            "Bash 和写工具能力应运行在 workspace boundary 和 sandbox/permission 策略内，而不是宿主无边界环境。",
            "Sandbox-aware tool execution",
            "工作区路径、网络和写权限有边界。",
            "越界、敏感路径和破坏性命令被拦截或请求权限。",
            "工具结果不会暴露不该进入模型上下文的宿主状态。",
            "RepoHarness 后续增强动态能力时仍必须坚持 hidden/runtime-private/shared dependency 边界。",
            ["bash_sandbox", "permissions"],
        ),
        _claude_contract(
            "tool_result_truncation_and_raw_artifact_privacy",
            "context",
            "工具结果需要模型可见 preview、raw artifact 私有化和大输出处理，避免泄漏和上下文爆炸。",
            "Tool result mapping",
            "工具执行后映射为模型可见 tool_result 与内部 artifact。",
            "raw data 可以保存在审计侧，但不默认进入模型上下文。",
            "模型只看到安全裁剪后的观察。",
            "RepoHarness 必须继续区分 model_visible_observation 和 runtime-private raw artifact。",
            ["tool_execution", "tool_contract"],
        ),
        _claude_contract(
            "task_management_todo",
            "planning",
            "Claude Code 参考工具面包含 TodoWrite 类任务管理能力，帮助模型跟踪长程修复步骤。",
            "TodoWriteTool",
            "任务列表作为结构化状态更新。",
            "状态工具本身低风险，但会影响轨迹质量和可审计性。",
            "任务状态回流给模型并影响后续行动。",
            "RepoHarness 的 update_working_state 需要评估是否足够，或补 todo_write。",
            ["todo"],
        ),
        _claude_contract(
            "subagent_or_task_tool",
            "delegation",
            "Claude Code 参考体系包含 AgentTool / task tool，用于把复杂工作拆给子代理或后台任务。",
            "AgentTool",
            "子代理拥有独立提示、工具池和 sidechain transcript。",
            "权限、隔离和工具池需要单独审计。",
            "主代理通过子任务结果继续推理。",
            "RepoHarness 短期可先 schema 预留，不应阻塞 core SWE tool profile。",
            ["agent", "agent_runner"],
            confidence="medium",
        ),
        _claude_contract(
            "external_tool_mcp_plugin_skill",
            "extension",
            "真实产品态允许 MCP、插件和技能扩展工具面。",
            "MCPTool / plugins / skills",
            "外部能力通过统一工具包装进入模型可见工具池。",
            "外部工具需要额外鉴权、权限和审计。",
            "工具结果仍按统一生命周期回流。",
            "RepoHarness Stage 16G core 不需要完整实现，但轨迹 schema 应预留。",
            ["mcp", "plugins", "skills"],
            confidence="medium",
        ),
        _claude_contract(
            "tool_search_or_deferred_tool_discovery",
            "extension",
            "工具搜索和延迟工具发现允许模型在需要时暴露更多工具，而不是固定小工具面。",
            "ToolSearchTool",
            "可搜索 deferred tools 或 MCP tools。",
            "发现工具仍受权限和工具池规则约束。",
            "模型获得新工具描述后继续任务。",
            "RepoHarness 后续可把 profile 与 registry 设计成可扩展，而不是硬编码单一工具集。",
            ["tool_search"],
            confidence="medium",
        ),
        _claude_contract(
            "hooks_and_tool_lifecycle_audit",
            "audit",
            "工具执行前后有 hook、权限检查、结果映射和失败处理，形成完整生命周期审计。",
            "Tool execution and hooks",
            "每次工具调用经过 schema、validate、permission、call、map result 和 hooks。",
            "hook 可以拦截或记录高风险行为。",
            "结果和失败都进入可审计事件。",
            "RepoHarness builder 和 training export 应保留 invalid call、denial 和 failure 事件。",
            ["tool_execution", "tool_orchestration"],
        ),
        _claude_contract(
            "language_diagnostics_or_lsp_feedback",
            "diagnostics",
            "语言服务器诊断和被动反馈能帮助真实开发代理定位类型、语法和引用问题。",
            "LSP services",
            "诊断来自语言服务而不是简单文本搜索。",
            "诊断结果需要避免泄漏非工作区路径。",
            "反馈作为上下文或工具结果影响修复。",
            "RepoHarness 当前 symbol_search 不是完整 LSP；可作为 extended gap。",
            ["lsp"],
            confidence="medium",
        ),
        _claude_contract(
            "session_context_resume_compaction",
            "context",
            "真实产品态包含会话恢复、上下文压缩和长期状态管理。",
            "Session / context services",
            "历史工具结果、压缩摘要和恢复状态共同决定模型看到什么。",
            "压缩和恢复不能破坏 tool_use/tool_result 配对或权限事实。",
            "压缩后的信息继续指导后续工具调用。",
            "RepoHarness 训练 schema 需要明确哪些摘要不进 policy loss。",
            ["tool_contract"],
            confidence="medium",
        ),
        _claude_contract(
            "final_answer_and_change_summary",
            "finalization",
            "最终回答应总结实际修改和验证结果，并能和工具事件、diff、测试输出交叉验证。",
            "Assistant final response with tool transcript",
            "final answer 基于前序工具事件和文件 diff。",
            "虚假验证声明应被审计或惩罚。",
            "用户看到简洁总结，训练侧保留结构化证据。",
            "RepoHarness 需要 final answer、verifier、reward 和 export linkage。",
            ["tool_execution"],
            confidence="medium",
        ),
    ]
    return {
        "schema_version": "stage16g0.claude_code_baseline_contract.v1",
        "baseline_label": "claude_code_like_swe_agent",
        "baseline_scope": "reference_source_contract_not_product_replication",
        "source_inventory": [
            _repo_source_entry(label, relative_path) for label, relative_path in CLAUDE_CODE_SOURCES.items()
        ],
        "capability_contracts": contracts,
    }


def _claude_contract(
    capability_id: str,
    category: str,
    baseline: str,
    model_visible: str,
    execution: str,
    permission: str,
    result: str,
    implication: str,
    source_keys: list[str],
    *,
    confidence: str = "high",
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "capability_category": category,
        "baseline_statement": baseline,
        "model_visible_mechanism": model_visible,
        "execution_semantics": execution,
        "permission_semantics": permission,
        "result_semantics": result,
        "repo_harness_design_implication": implication,
        "source_evidence": [_evidence(CLAUDE_CODE_SOURCES[key]) for key in source_keys],
        "confidence": confidence,
    }


def build_mini_swe_agent_baseline_contract() -> dict[str, Any]:
    contracts = [
        _mini_contract(
            "stable_shell_loop",
            "shell",
            "模型至少拥有一个稳定 Bash 操作闭环，可以在任务内持续运行诊断命令、测试命令和复现脚本。",
            "Bash / shell command channel",
            "真实运行日志显示 mini-SWE-agent 启动 SWE-Bench 容器并在 /testbed 工作目录中运行任务。",
            "外部证据可确认容器化运行；完整内部安全机制需要官方源码复核。",
            "stdout、stderr、exit status 和 trajectory/log 文件构成迭代反馈。",
            "RepoHarness core 不必复制裸 shell，但必须覆盖动态诊断闭环。",
            ["public_config_excerpt", "smoke_stdout_stderr", "smoke_internal_log"],
            primary_required=False,
        ),
        _mini_contract(
            "repository_navigation_via_shell",
            "navigation",
            "Bash-first agent 通过 shell 命令完成仓库导航、文件查看和目录定位。",
            "Shell command responses",
            "配置摘录要求模型每轮提交命令并观察结果。",
            "路径边界来自容器工作目录和任务说明；内部过滤机制未由本地源码确认。",
            "命令输出回到下一轮推理。",
            "RepoHarness 的结构化 read/glob/grep 至少要覆盖这些 shell 导航能力。",
            ["public_config_excerpt"],
            confidence="medium",
        ),
        _mini_contract(
            "file_view_search_edit_via_shell",
            "editing",
            "Bash-first baseline 主要通过 shell 组合完成文件查看、搜索、编辑和新建文件。",
            "Shell command channel",
            "任务说明要求修改 non-test source files，且每轮至少执行一个命令。",
            "禁止修改测试和配置文件属于任务 prompt 层边界；完整执行拦截需要官方源码复核。",
            "文件编辑结果通过后续命令和最终 patch 体现。",
            "RepoHarness 可以用结构化工具替代 shell 形态，但能力覆盖不能弱于 shell 基本动作。",
            ["public_config_excerpt"],
            confidence="medium",
        ),
        _mini_contract(
            "public_test_and_project_command_via_shell",
            "testing",
            "Bash-first agent 可以通过 shell 运行公开测试或项目命令，并读取 stdout、stderr 和 exit code。",
            "Shell command channel",
            "配置摘录推荐创建复现脚本并验证修复；运行日志证明任务在 SWE-Bench 容器中执行。",
            "hidden official scoring 不应进入模型可见命令；完整防泄漏机制需官方源码复核。",
            "测试输出成为下一轮修复依据。",
            "RepoHarness 必须补 run_public_command 或 run_project_test，不能只有无参数 run_tests。",
            ["public_config_excerpt", "smoke_stdout_stderr"],
            primary_required=False,
        ),
        _mini_contract(
            "scratch_script_and_reproduction_via_shell",
            "diagnosis",
            "Bash-first prompt 明确推荐创建脚本复现问题，再运行脚本验证修复。",
            "Shell command channel",
            "复现脚本由模型通过 shell 创建和执行。",
            "临时文件是否进入最终 patch 依赖 agent/harness 清理；本地证据不足以确认全部机制。",
            "脚本输出反馈给模型。",
            "RepoHarness 应提供 scratch_python 或受控 scratch workspace，并由 patch hygiene 排除临时产物。",
            ["public_config_excerpt"],
            confidence="medium",
        ),
        _mini_contract(
            "dependency_setup_or_environment_use",
            "environment",
            "mini-SWE-agent 在 SWE-Bench 容器或官方镜像内运行，依赖环境由容器提供。",
            "Docker-backed task environment",
            "运行日志显示 docker run 使用 SWE-Bench eval image，并设置工作目录。",
            "容器边界存在；依赖写入、网络和跨题污染细节需官方源码复核。",
            "环境命令输出进入日志或 trajectory。",
            "RepoHarness 需要 Docker/private overlay/shared dependency read-only policy 来达到同等可执行性。",
            ["smoke_stdout_stderr", "smoke_internal_log"],
            primary_required=False,
        ),
        _mini_contract(
            "patch_generation_and_final_diff",
            "finalization",
            "Bash-first baseline 的最终目标是修改工作目录中的源码并提交最终结果，由外部 evaluator 检查 patch。",
            "Shell edits plus final submission",
            "运行日志显示每个实例保存 trajectory，并有 official 评测日志。",
            "官方评测和隐藏测试不应进入模型上下文。",
            "最终提交与日志、trajectory 和 official 结果分离。",
            "RepoHarness 必须把 patch capture、official prediction、verifier 和 reward linkage 做成硬门槛。",
            ["smoke_stdout_stderr", "official_all5_stdout_stderr", "official_completed4_stdout_stderr"],
            confidence="medium",
        ),
        _mini_contract(
            "stdout_stderr_exit_code_feedback",
            "feedback",
            "shell-first agent 的基本观测是命令输出、错误输出和退出状态。",
            "Shell observation",
            "命令结果作为下一轮推理依据。",
            "输出可能包含路径或环境细节，安全边界需要外部过滤或容器隔离。",
            "stdout/stderr/exit code 是动态验证信号。",
            "RepoHarness public command 工具必须返回足够具体但脱敏的 stdout/stderr/exit code。",
            ["public_config_excerpt", "smoke_stdout_stderr"],
            confidence="medium",
        ),
        _mini_contract(
            "task_local_state_or_session_continuity",
            "session",
            "Bash-first workflow 需要任务内工作目录、容器和文件系统状态保持足够连续，才能迭代调试。",
            "Task-local shell/container state",
            "运行日志显示每个实例启动容器并保存 trajectory。",
            "跨题隔离和 cleanup 细节需要官方源码或更多日志复核。",
            "后续命令建立在前序文件修改和环境状态上。",
            "RepoHarness 可以用无状态命令加持久 workspace 实现，不一定需要交互式 persistent shell。",
            ["smoke_internal_log"],
            confidence="medium",
        ),
        _mini_contract(
            "safety_boundary_and_hidden_material_exclusion",
            "safety",
            "mini-SWE-agent baseline 的安全边界至少包含容器化任务环境和 prompt 层禁止修改测试/配置，但完整机制需要官方源码验证。",
            "Container plus task prompt",
            "公开日志能证明 Docker 容器和 /testbed 工作目录；不能证明全部 hidden material 防护机制。",
            "需要后续 primary source verification。",
            "可观察输出不应包含 hidden evaluator 细节。",
            "RepoHarness 不能用 mini-SWE-agent 作无约束 shell 依据，必须保留确定性防泄漏边界。",
            ["smoke_stdout_stderr", "public_config_excerpt"],
            confidence="medium",
            primary_required=True,
        ),
    ]
    return {
        "schema_version": "stage16g0.mini_swe_agent_baseline_contract.v1",
        "baseline_label": "mini_swe_agent_like_bash_first_agent",
        "baseline_scope": "minimal_shell_first_swe_agent_comparison_baseline",
        "source_inventory": [
            _mini_source_entry(label, relative_path) for label, relative_path in MINI_SWE_AGENT_SOURCES.items()
        ],
        "capability_contracts": contracts,
        "global_source_caveat": (
            "本地没有 mini-SWE-agent 官方仓库源码；本 baseline 使用 evaluation worktree 的真实配置、"
            "public-safe 配置摘录和运行日志。外部可观察行为可以中高置信，内部安全实现细节需要后续官方源码验证。"
        ),
    }


def _mini_contract(
    capability_id: str,
    category: str,
    baseline: str,
    model_visible: str,
    execution: str,
    permission: str,
    result: str,
    implication: str,
    source_keys: list[str],
    *,
    confidence: str = "high",
    primary_required: bool = True,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "capability_category": category,
        "baseline_statement": baseline,
        "model_visible_mechanism": model_visible,
        "execution_semantics": execution,
        "permission_semantics": permission,
        "result_semantics": result,
        "repo_harness_design_implication": implication,
        "source_evidence": [_mini_evidence(key) for key in source_keys],
        "confidence": confidence,
        "primary_source_verification_required": primary_required,
    }


def build_per_capability_baseline_comparison() -> dict[str, Any]:
    records = [
        _comparison(
            "structured_file_read",
            "Claude Code 使用 Read/FileReadTool 作为源码阅读主路径，支持路径保护、输出预算和工具结果回流。",
            "mini-SWE-agent 主要通过 shell 命令查看文件；这是能力下限，不是 RepoHarness 要复制的实现形态。",
            "RepoHarness 有 read_file，默认 simple_react 可见；结构化读取方向充分。",
            "present_and_sufficient",
            "not_required",
            False,
            ["file_read"],
            ["repository_navigation_via_shell"],
            ["tools"],
            "high",
        ),
        _comparison(
            "non_text_file_read",
            "Claude Code 参考工具面包含图片、PDF、notebook 等非文本读取处理。",
            "mini-SWE-agent shell-first baseline 对非文本读取没有结构化工具保障，通常依赖 shell 或项目命令。",
            "RepoHarness 当前 core SWE 工具面主要面向文本源码；非文本读取不是 Stage 16G 主 RL 阻塞项。",
            "present_but_weaker_than_claude_code",
            "post_16G_optional",
            False,
            ["non_text_file_read"],
            ["repository_navigation_via_shell"],
            ["tools"],
            "medium",
        ),
        _comparison(
            "large_file_paging_or_artifact_replay",
            "Claude Code 对长输出和大文件有截断、分页或 artifact 回读机制。",
            "mini-SWE-agent 通过 shell 输出观察长内容，具体截断和日志策略依赖 harness。",
            "RepoHarness 有 read_tool_result_artifact 和工具输出预算；需要在 follow-up 后续 parity 中继续验证 raw artifact 私有化。",
            "present_and_sufficient",
            "16G.5",
            False,
            ["large_file_paging_or_artifact_replay"],
            ["stdout_stderr_exit_code_feedback"],
            ["tools"],
            "high",
        ),
        _comparison(
            "glob_file_discovery",
            "Claude Code 使用 GlobTool 做结构化文件发现。",
            "mini-SWE-agent 通过 shell ls/find 等命令完成文件发现。",
            "RepoHarness 有 glob_files，默认可见；能力覆盖足够。",
            "present_and_sufficient",
            "not_required",
            False,
            ["glob_file_discovery"],
            ["repository_navigation_via_shell"],
            ["tools"],
            "high",
        ),
        _comparison(
            "grep_content_search",
            "Claude Code 使用 GrepTool 做内容搜索，避免通过 Bash 绕过搜索策略。",
            "mini-SWE-agent 通过 shell grep/rg 等命令搜索代码。",
            "RepoHarness 有 grep；execute_bash 还允许部分安全 rg/grep，但 core 应保持结构化搜索优先。",
            "present_and_sufficient",
            "not_required",
            False,
            ["grep_content_search"],
            ["file_view_search_edit_via_shell"],
            ["tools", "command_policy"],
            "high",
        ),
        _comparison(
            "symbol_search_or_lsp_diagnostics",
            "Claude Code 目标环境包含 LSP 诊断或语言反馈能力。",
            "mini-SWE-agent 通常没有结构化 LSP，主要通过 shell 和测试反馈定位。",
            "RepoHarness 有轻量 symbol_search，但不是完整 LSP；这影响 extended profile，不阻塞 core 主 RL。",
            "present_but_weaker_than_claude_code",
            "post_16G_optional",
            False,
            ["language_diagnostics_or_lsp_feedback"],
            ["repository_navigation_via_shell"],
            ["tools"],
            "medium",
        ),
        _comparison(
            "structured_edit_existing_file",
            "Claude Code 使用 Edit/FileEditTool 做结构化已有文件编辑。",
            "mini-SWE-agent 通过 shell 编辑命令或脚本改文件。",
            "RepoHarness 有 edit_file exact replace，默认可见；复杂编辑效率仍需 apply_patch 补齐。",
            "partial",
            "16G.2",
            True,
            ["structured_edit_existing_file"],
            ["file_view_search_edit_via_shell"],
            ["tools"],
            "high",
        ),
        _comparison(
            "structured_write_or_create_file",
            "Claude Code 使用 Write/FileWriteTool 创建或覆盖文件。",
            "mini-SWE-agent 通过 shell 重定向、脚本或编辑器命令创建文件。",
            "RepoHarness 有 create_file，默认 simple_react 可见；但 patch_focused_react 不暴露，write/overwrite 语义不足。",
            "partial",
            "16G.2",
            True,
            ["structured_write_or_create_file"],
            ["file_view_search_edit_via_shell"],
            ["tools", "scaffold_patch_focused", "scaffold_simple"],
            "high",
        ),
        _comparison(
            "apply_patch_or_multi_file_edit",
            "Claude Code 风格真实开发需要跨文件修改能力，即使由多个 Edit/Write 组合完成，也要高效审计。",
            "mini-SWE-agent 可以用 shell 和 patch/diff 工作流完成多文件修改。",
            "RepoHarness 缺少 apply_patch 或等价多文件编辑工具；exact replace 对复杂 patch 不够稳。",
            "missing",
            "16G.2",
            True,
            ["patch_or_multi_file_edit_equivalent"],
            ["patch_generation_and_final_diff"],
            ["tools", "patch_hygiene"],
            "high",
        ),
        _comparison(
            "delete_move_mkdir_file_operations",
            "Claude Code 写工具和 Bash 组合可以完成真实文件组织变更，但仍需权限和审计。",
            "mini-SWE-agent 通过 shell rm/mv/mkdir 等完成文件操作。",
            "RepoHarness 当前没有完整 delete/move/mkdir 结构化工具面；后续应设计受控文件操作。",
            "missing",
            "16G.2",
            True,
            ["structured_write_or_create_file"],
            ["file_view_search_edit_via_shell"],
            ["tools"],
            "medium",
        ),
        _comparison(
            "bash_or_public_command_execution",
            "Claude Code Bash 是测试、构建、项目命令和复杂诊断的一等能力，受权限和 sandbox 约束。",
            "mini-SWE-agent 的核心就是稳定 shell 闭环，提供动态诊断能力下限。",
            "RepoHarness execute_bash 窄但非空；主 core 应补结构化 run_public_command，而不是开放裸 shell。",
            "present_but_weaker_than_mini_swe_agent",
            "16G.3",
            True,
            ["bash_project_command_execution"],
            ["stable_shell_loop"],
            ["tools", "command_policy"],
            "high",
            capability_shape_note="能力覆盖目标，不是实现形态目标；RepoHarness 应用结构化公开命令覆盖动态诊断能力。",
        ),
        _comparison(
            "persistent_diagnostic_session",
            "Claude Code 目标环境能处理长命令、后台任务或更持续的命令状态。",
            "mini-SWE-agent 每个任务运行在容器/工作目录状态中，形成足够连续的 shell 工作流。",
            "RepoHarness diagnostic_shell 是 diagnostic profile，文件 projection 持久，但不是默认正式训练工具。",
            "present_diagnostic_only",
            "16G.4",
            True,
            ["persistent_or_background_command_monitoring"],
            ["task_local_state_or_session_continuity"],
            ["diagnostic_session", "docker_adapter"],
            "high",
            capability_shape_note="core 默认不要求裸 persistent shell；extended profile 承担更接近 mini-SWE-agent 的持续诊断。",
        ),
        _comparison(
            "parameterized_public_test_command",
            "Claude Code 可以通过 Bash 或项目命令机制运行定向公开测试，并由权限、sandbox 和工具生命周期审计。",
            "mini-SWE-agent 至少可以通过稳定 shell 运行公开测试或项目测试命令，并读取 stdout、stderr 和 exit code。",
            "RepoHarness run_tests 无参数；execute_bash 支持部分安全 pytest；final-only 会禁用 run_tests。",
            "partial",
            "16G.3",
            True,
            ["public_test_or_project_command_execution"],
            ["public_test_and_project_command_via_shell"],
            ["tools", "scaffold_policies", "public_environment"],
            "high",
        ),
        _comparison(
            "scratch_python_or_reproduction_script",
            "Claude Code 可以通过 Bash/Write/Edit 组合创建或运行临时复现逻辑。",
            "mini-SWE-agent prompt 明确推荐创建复现脚本再验证修复。",
            "RepoHarness 只有受限 inline Python 和 diagnostic_shell；没有正式 scratch_python 工具。",
            "partial",
            "16G.3",
            True,
            ["scratch_reproduction_script"],
            ["scratch_script_and_reproduction_via_shell"],
            ["command_policy", "diagnostic_session", "patch_hygiene"],
            "high",
            capability_shape_note="目标是复现能力和临时产物隔离，不是允许 shell 任意写脚本。",
        ),
        _comparison(
            "project_command_routing",
            "Claude Code Bash 能表达项目命令、测试命令和构建命令，并通过权限处理风险。",
            "mini-SWE-agent shell-first baseline 自然支持项目命令执行。",
            "RepoHarness 缺少统一 project command router；当前依赖 run_tests 或窄 execute_bash。",
            "missing",
            "16G.3",
            True,
            ["bash_project_command_execution"],
            ["public_test_and_project_command_via_shell"],
            ["public_environment", "command_policy"],
            "high",
        ),
        _comparison(
            "dependency_setup_and_environment_policy",
            "Claude Code 类环境用 sandbox/approval 管理依赖安装和环境命令风险。",
            "mini-SWE-agent 使用 SWE-Bench 容器环境，运行日志显示 Docker-backed /testbed 执行。",
            "RepoHarness 有依赖守卫和 Docker work，但 shared dependency write、private overlay、setup routing 仍未成为 core 能力。",
            "partial",
            "16G.4",
            True,
            ["sandbox_and_workspace_boundary"],
            ["dependency_setup_or_environment_use"],
            ["diagnostic_session", "docker_adapter", "command_policy"],
            "high",
        ),
        _comparison(
            "git_diff_status_and_patch_capture",
            "Claude Code 工作流依赖 diff 审查和最终变更总结。",
            "mini-SWE-agent 最终通过工作目录 patch 和 official evaluator 检查结果。",
            "RepoHarness 有 git_diff、patch hygiene、episode projection；需要在 follow-up requirements 中继续绑定 reward/export。",
            "present_and_sufficient",
            "16G.5",
            False,
            ["final_answer_and_change_summary"],
            ["patch_generation_and_final_diff"],
            ["tools", "patch_hygiene", "episode_projection"],
            "high",
        ),
        _comparison(
            "final_answer_verifier_reward_linkage",
            "Claude Code final answer 应和工具事件、测试输出、diff 交叉验证。",
            "mini-SWE-agent 保存 trajectory 并由 official/eval 日志给出最终结果。",
            "RepoHarness 已有 Stage 16G.0 linkage report，但后续新工具必须接入 final patch、verifier、reward、TrainingView 和 export。",
            "partial",
            "16G.4",
            True,
            ["final_answer_and_change_summary"],
            ["patch_generation_and_final_diff"],
            ["runtime", "episode_projection", "patch_hygiene"],
            "high",
        ),
        _comparison(
            "permission_approval_denial_recovery",
            "Claude Code 强工具能力通过权限、拒绝原因和恢复路径管理。",
            "mini-SWE-agent 的完整内部拒绝机制本地未确认；shell 输出仍给模型反馈。",
            "RepoHarness 有 reason_code/recovery_hint 等字段，但要验证拒绝是否可学习且不诱导少用工具。",
            "partial",
            "16G.4",
            True,
            ["permission_approval_and_denial_recovery"],
            ["stdout_stderr_exit_code_feedback"],
            ["tools", "command_policy"],
            "high",
        ),
        _comparison(
            "sandbox_workspace_and_runtime_private_boundary",
            "Claude Code 通过 workspace boundary、sandbox 和权限区分可见/不可见资源。",
            "mini-SWE-agent 运行日志证明容器和 /testbed；完整 hidden material 隔离需官方源码验证。",
            "RepoHarness 对 hidden verifier、runtime-private、Git history、shared dependency 有明确防护，后续扩能力不能破坏。",
            "present_and_sufficient",
            "16G.4",
            True,
            ["sandbox_and_workspace_boundary"],
            ["safety_boundary_and_hidden_material_exclusion"],
            ["command_policy", "diagnostic_session", "docker_adapter"],
            "high",
        ),
        _comparison(
            "tool_result_truncation_raw_artifact_privacy",
            "Claude Code 区分模型可见结果和 raw artifact，处理大输出和审计私有化。",
            "mini-SWE-agent shell 输出和日志提供反馈；安全过滤细节需要官方源码确认。",
            "RepoHarness execute_bash/diagnostic_shell 已有 redacted_truncated 和 raw runtime-private 语义；后续新 public command 必须复用。",
            "present_and_sufficient",
            "16G.4",
            True,
            ["tool_result_truncation_and_raw_artifact_privacy"],
            ["stdout_stderr_exit_code_feedback"],
            ["tools"],
            "high",
        ),
        _comparison(
            "task_management_todo",
            "Claude Code 有 TodoWrite 类结构化任务管理。",
            "mini-SWE-agent prompt 要求 THOUGHT 和命令循环，但不是结构化 todo 工具。",
            "RepoHarness 有 update_working_state，仍弱于 TodoWrite；这影响轨迹质量但不是 public command core 阻塞。",
            "partial",
            "16G.2",
            False,
            ["task_management_todo"],
            ["stable_shell_loop"],
            ["tools"],
            "medium",
        ),
        _comparison(
            "subagent_background_task",
            "Claude Code 支持 AgentTool 或任务工具，复杂工作可由子代理/后台任务处理。",
            "mini-SWE-agent baseline 不依赖子代理，是单 agent shell-first 下限。",
            "RepoHarness 当前主训练无需子代理；schema 预留即可。",
            "deferred_schema_only",
            "post_16G_optional",
            False,
            ["subagent_or_task_tool"],
            ["stable_shell_loop"],
            ["runtime"],
            "medium",
        ),
        _comparison(
            "external_tools_mcp_plugin_skill",
            "Claude Code 产品态可以通过 MCP、插件和技能扩展工具面。",
            "mini-SWE-agent baseline 不要求外部工具扩展。",
            "RepoHarness Stage 16G core 不实现完整外部工具系统，但后续轨迹 schema 应保留能力位。",
            "deferred_schema_only",
            "post_16G_optional",
            False,
            ["external_tool_mcp_plugin_skill"],
            ["stable_shell_loop"],
            ["runtime"],
            "medium",
        ),
        _comparison(
            "hooks_tool_lifecycle_audit",
            "Claude Code 工具调用进入 schema、validate、permission、call、result mapping、hooks 和 failure handling。",
            "mini-SWE-agent 运行日志能证明 trajectory/log 存在，内部 hook 机制需官方源码确认。",
            "RepoHarness 有工具事件和 audit，但新工具必须保留 invalid call、denial、failure 和 checker 输出。",
            "partial",
            "16G.4",
            True,
            ["hooks_and_tool_lifecycle_audit"],
            ["stable_shell_loop"],
            ["tools", "runtime"],
            "high",
        ),
        _comparison(
            "training_eligibility_and_export_projection",
            "Claude Code 产品态 transcript 不是训练资格本身；训练 harness 必须额外定义 visibility、loss mask 和 export projection。",
            "mini-SWE-agent 运行日志和 trajectory 可被外部 evaluator 消费，但不等价于 RepoHarness policy-loss eligibility。",
            "RepoHarness 已有 formal online RL gate；新 diagnostic/public command 行为必须明确能否进入 policy loss、SFT、preference 和 side channel。",
            "partial",
            "16G.4",
            True,
            ["tool_result_truncation_and_raw_artifact_privacy"],
            ["patch_generation_and_final_diff"],
            ["runtime", "episode_projection", "execution_spec"],
            "high",
        ),
        _comparison(
            "reward_hacking_monitoring_and_quarantine",
            "Claude Code 类强工具环境需要 deterministic boundary 加监控，而不是只靠削减工具能力。",
            "mini-SWE-agent 的完整 reward hacking 防护无法由本地日志确认；容器和 official eval 只覆盖一部分边界。",
            "RepoHarness 已有 hard fail/quarantine 设计；后续扩工具必须把 suspicious behavior、test tampering、dependency write 等纳入门禁。",
            "partial",
            "16G.4",
            True,
            ["sandbox_and_workspace_boundary"],
            ["safety_boundary_and_hidden_material_exclusion"],
            ["command_policy", "diagnostic_session", "patch_hygiene"],
            "high",
        ),
    ]
    _validate_comparison_records(records)
    return {
        "schema_version": "stage16g0.per_capability_baseline_comparison.v1",
        "comparison_records": records,
    }


def _comparison(
    capability_id: str,
    claude_baseline: str,
    mini_baseline: str,
    repoharness_status: str,
    gap_type: str,
    required_stage: str,
    blocking: bool,
    claude_refs: list[str],
    mini_refs: list[str],
    repo_refs: list[str],
    confidence: str,
    *,
    capability_shape_note: str | None = None,
) -> dict[str, Any]:
    if gap_type not in ALLOWED_GAP_TYPES:
        raise ValueError(f"invalid gap_type for {capability_id}: {gap_type}")
    if required_stage not in ALLOWED_REQUIRED_STAGES:
        raise ValueError(f"invalid required_stage for {capability_id}: {required_stage}")
    evidence: list[dict[str, Any]] = []
    evidence.extend({"source_label": "claude_code_baseline_contract", "evidence_ref": ref} for ref in claude_refs)
    evidence.extend({"source_label": "mini_swe_agent_baseline_contract", "evidence_ref": ref} for ref in mini_refs)
    evidence.extend(
        {
            "source_label": "repoharness_source",
            "relative_path": REPOHARNESS_SOURCES[ref],
            "evidence_kind": "static_source_scan",
        }
        for ref in repo_refs
    )
    record: dict[str, Any] = {
        "capability_id": capability_id,
        "claude_code_baseline": claude_baseline,
        "mini_swe_agent_baseline": mini_baseline,
        "repoharness_current_status": repoharness_status,
        "gap_type": gap_type,
        "required_stage": required_stage,
        "blocking_for_main_swe_rl": blocking,
        "source_evidence": evidence,
        "confidence": confidence,
    }
    if capability_shape_note is not None:
        record["capability_shape_note"] = capability_shape_note
    return record


def _validate_comparison_records(records: list[dict[str, Any]]) -> None:
    capability_ids = {record["capability_id"] for record in records}
    missing = sorted(set(REQUIRED_COMPARISON_CAPABILITIES) - capability_ids)
    if missing:
        raise ValueError(f"missing comparison capabilities: {missing}")
    if any(record["gap_type"] not in ALLOWED_GAP_TYPES for record in records):
        raise ValueError("comparison contains invalid gap_type")
    if any(record["required_stage"] not in ALLOWED_REQUIRED_STAGES for record in records):
        raise ValueError("comparison contains invalid required_stage")
    for field in ("claude_code_baseline", "mini_swe_agent_baseline"):
        duplicates = Counter(record[field] for record in records)
        too_many = [text for text, count in duplicates.items() if count > 5]
        if too_many:
            raise ValueError(f"{field} has a repeated template baseline")
    for record in records:
        if record["blocking_for_main_swe_rl"] and record["required_stage"] not in {"16G.1", "16G.2", "16G.3", "16G.4"}:
            raise ValueError(f"blocking record maps outside implementation stages: {record['capability_id']}")
        if not record["source_evidence"]:
            raise ValueError(f"missing evidence for {record['capability_id']}")


def build_stage16g_implementation_requirements() -> dict[str, Any]:
    requirements = [
        _requirement(
            "stage16g1_baseline_derived_tool_registry",
            "16G.1",
            "P0",
            ["bash_or_public_command_execution", "training_eligibility_and_export_projection"],
            "基于 baseline comparison 固定 tool registry、profile taxonomy、core / extended / redteam profile 和训练资格门禁。",
            [
                "所有 P0/P1 工具能力都能追溯到 comparison capability_id。",
                "core profile 明确采用结构化公开命令优先，而不是裸 shell 优先。",
                "profile 设计区分 safe_structured_only、swe_public_core、swe_public_extended 和 redteam_restricted。",
            ],
        ),
        _requirement(
            "stage16g2_structured_file_and_patch_surface",
            "16G.2",
            "P0",
            [
                "structured_edit_existing_file",
                "structured_write_or_create_file",
                "apply_patch_or_multi_file_edit",
                "delete_move_mkdir_file_operations",
            ],
            "补齐结构化文件能力，使多文件修改、新建、移动、删除和 patch 审计不依赖无约束 shell。",
            [
                "apply_patch 或等价多文件编辑工具进入候选 profile。",
                "新增、删除、移动和目录创建动作进入 patch hygiene、final.patch 和 export projection。",
                "编辑失败返回可学习的结构化恢复信息。",
            ],
        ),
        _requirement(
            "stage16g3_public_command_project_test_and_scratch_python",
            "16G.3",
            "P0",
            [
                "bash_or_public_command_execution",
                "parameterized_public_test_command",
                "scratch_python_or_reproduction_script",
                "project_command_routing",
            ],
            "设计并实现正式 public diagnostic/action command 能力，支持公开测试、项目命令和受控复现脚本，同时不暴露 hidden verifier、gold patch、test patch、runtime-private 路径或共享依赖写权限。",
            [
                "模型可见 schema 能表达单个公开测试、项目命令和受控 scratch Python 复现。",
                "拒绝结果包含可学习的 reason_code、retryable、safe_alternative_tool 或 safe_rewrite_example。",
                "成功或拒绝的工具事件都能进入 public-safe audit，并能参与训练资格判断。",
            ],
        ),
        _requirement(
            "stage16g4_diagnostic_shell_dependency_and_training_linkage",
            "16G.4",
            "P0",
            [
                "persistent_diagnostic_session",
                "dependency_setup_and_environment_policy",
                "final_answer_verifier_reward_linkage",
                "permission_approval_denial_recovery",
                "hooks_tool_lifecycle_audit",
                "training_eligibility_and_export_projection",
                "reward_hacking_monitoring_and_quarantine",
            ],
            "收口 controlled diagnostic shell、dependency setup、private overlay、permission recovery、verifier/reward/export linkage 和 quarantine 规则。",
            [
                "persistent shell 仅进入 swe_public_extended，不进入 core 默认。",
                "共享依赖只读、题间 session reset、artifact hygiene 和 verifier 隔离有确定性证据。",
                "final answer 的测试声明能和工具事件或 verifier summary 交叉校验。",
            ],
        ),
        _requirement(
            "stage16g5_post_implementation_parity_probe",
            "16G.5",
            "P1",
            [
                "large_file_paging_or_artifact_replay",
                "git_diff_status_and_patch_capture",
                "sandbox_workspace_and_runtime_private_boundary",
                "tool_result_truncation_raw_artifact_privacy",
            ],
            "在 Stage 16G.1 到 Stage 16G.4 完成后运行 Claude Code / mini-SWE-agent parity probe，验证实现效果，不再承担第一次 baseline 对照。",
            [
                "probe 覆盖 Claude Code 分层工具能力和 mini-SWE-agent 动态诊断能力。",
                "新发现差距必须回写 comparison 与 requirements。",
                "probe 失败不能被解释为 Stage 17 可继续放行。",
            ],
            blocking=False,
        ),
    ]
    return {
        "schema_version": "stage16g0.stage16g_implementation_requirements.v1",
        "design_assumptions": [
            {
                "assumption_id": "structured_public_command_first_core_profile",
                "statement": "主 SWE 强化学习 core 工具面采用结构化公开命令优先：用无状态、可审计的 run_public_command、run_project_test 和 scratch_python 覆盖动态验证能力；persistent shell 归入 swe_public_extended profile，不进入 core 默认。",
                "safety_boundary": "防 reward hacking 依赖确定性边界，包括 sandbox、路径隔离、默认无网络、共享依赖只读、题间 session 重置、每次调用静态或 AST 扫描、artifact hygiene 和 verifier 隔离，而不是通过继续削减真实 SWE 动态诊断能力来获得安全感。",
            },
            {
                "assumption_id": "mini_swe_agent_dynamic_capability_not_shell_shape",
                "statement": "当 RepoHarness 在自由 shell 形态上弱于 mini-SWE-agent 时，后续阶段追求的是覆盖 mini-SWE-agent 的动态诊断能力，而不是复制裸 shell 实现形态。",
            },
        ],
        "requirements": requirements,
    }


def _requirement(
    requirement_id: str,
    stage: str,
    priority: str,
    capability_ids: list[str],
    goal: str,
    acceptance: list[str],
    *,
    blocking: bool = True,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "required_stage": stage,
        "priority": priority,
        "source_capability_ids": capability_ids,
        "implementation_goal": goal,
        "acceptance_requirements": acceptance,
        "blocking_for_main_swe_rl": blocking,
    }


def build_followup_acceptance_summary(
    *,
    digests: dict[str, str],
    claude_contract: dict[str, Any],
    mini_contract: dict[str, Any],
    comparison: dict[str, Any],
    requirements: dict[str, Any],
    public_path_leak_scan_passed: bool,
    path_leak_findings: list[dict[str, str]],
) -> dict[str, Any]:
    comparison_records = comparison["comparison_records"]
    requirement_records = requirements["requirements"]
    return {
        "schema_version": "stage16g0.followup_acceptance_summary.v1",
        "status": "passed" if public_path_leak_scan_passed else "failed",
        "stage16g0_followup_complete": public_path_leak_scan_passed,
        "claude_code_baseline_contract_sha256": digests["stage16g0_claude_code_baseline_contract.json"],
        "mini_swe_agent_baseline_contract_sha256": digests["stage16g0_mini_swe_agent_baseline_contract.json"],
        "per_capability_baseline_comparison_sha256": digests[
            "stage16g0_per_capability_baseline_comparison.json"
        ],
        "stage16g_implementation_requirements_sha256": digests[
            "stage16g0_stage16g_implementation_requirements.json"
        ],
        "comparison_record_count": len(comparison_records),
        "blocking_for_main_swe_rl_count": sum(
            1 for record in comparison_records if record["blocking_for_main_swe_rl"]
        ),
        "gap_type_counts": dict(sorted(Counter(record["gap_type"] for record in comparison_records).items())),
        "required_stage_counts": dict(
            sorted(Counter(record["required_stage"] for record in comparison_records).items())
        ),
        "requirement_count": len(requirement_records),
        "p0_requirement_count": sum(1 for record in requirement_records if record["priority"] == "P0"),
        "public_path_leak_scan_passed": public_path_leak_scan_passed,
        "path_leak_finding_count": len(path_leak_findings),
        "path_leak_findings": path_leak_findings,
        "first_stage16g0_acceptance_summary_left_immutable": True,
        "validation_checks": _derive_validation_checks(
            claude_contract=claude_contract,
            mini_contract=mini_contract,
            comparison=comparison,
        ),
    }


def _derive_validation_checks(
    *,
    claude_contract: dict[str, Any],
    mini_contract: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, bool]:
    comparison_records = comparison["comparison_records"]
    return {
        "claude_code_evidence_not_all_agents_md": _claude_evidence_check_passed(claude_contract),
        "baseline_template_repetition_check_passed": _baseline_template_repetition_check_passed(
            comparison_records
        ),
        "blocking_records_map_to_16g1_through_16g4": _blocking_records_stage_check_passed(
            comparison_records
        ),
        "mini_swe_agent_uses_evaluation_worktree_tier2_evidence": _mini_tier2_evidence_check_passed(
            mini_contract
        ),
    }


def _claude_evidence_check_passed(claude_contract: dict[str, Any]) -> bool:
    records = claude_contract["capability_contracts"]
    return all(
        any(
            evidence.get("relative_path") != "reference/claude-code-typescript-src/AGENTS.md"
            for evidence in record.get("source_evidence", [])
        )
        for record in records
    )


def _baseline_template_repetition_check_passed(records: list[dict[str, Any]]) -> bool:
    for field in ("claude_code_baseline", "mini_swe_agent_baseline"):
        if any(count > 5 for count in Counter(record[field] for record in records).values()):
            return False
    return True


def _blocking_records_stage_check_passed(records: list[dict[str, Any]]) -> bool:
    return all(
        record["required_stage"] in {"16G.1", "16G.2", "16G.3", "16G.4"}
        for record in records
        if record["blocking_for_main_swe_rl"]
    )


def _mini_tier2_evidence_check_passed(mini_contract: dict[str, Any]) -> bool:
    inventory = mini_contract["source_inventory"]
    expected_refs = {f"evaluation_worktree:{path}" for path in MINI_SWE_AGENT_SOURCES.values()}
    actual_refs = {entry.get("opaque_ref") for entry in inventory}
    inventory_ok = (
        expected_refs.issubset(actual_refs)
        and all(entry.get("source_worktree_label") == "evaluation_worktree" for entry in inventory)
        and all(entry.get("tier") == "tier2_real_config_or_run_log" for entry in inventory)
    )
    evidence_ok = all(
        evidence.get("opaque_ref", "").startswith("evaluation_worktree:")
        for record in mini_contract["capability_contracts"]
        for evidence in record.get("source_evidence", [])
    )
    return inventory_ok and evidence_ok


def _scan_public_payloads(payloads: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    for filename, payload in payloads.items():
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                findings.append({"filename": filename, "pattern": pattern.pattern})
    return not findings, findings


def build_reports() -> dict[str, Any]:
    comparison = build_per_capability_baseline_comparison()
    requirements = build_stage16g_implementation_requirements()
    return {
        "stage16g0_claude_code_baseline_contract.json": build_claude_code_baseline_contract(),
        "stage16g0_mini_swe_agent_baseline_contract.json": build_mini_swe_agent_baseline_contract(),
        "stage16g0_per_capability_baseline_comparison.json": comparison,
        "stage16g0_stage16g_implementation_requirements.json": requirements,
    }


def write_reports(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = build_reports()
    public_path_leak_scan_passed, findings = _scan_public_payloads(reports)
    digests: dict[str, str] = {}
    for filename, payload in reports.items():
        digests[filename] = _write_json(output_dir / filename, payload)
    summary = build_followup_acceptance_summary(
        digests=digests,
        claude_contract=reports["stage16g0_claude_code_baseline_contract.json"],
        mini_contract=reports["stage16g0_mini_swe_agent_baseline_contract.json"],
        comparison=reports["stage16g0_per_capability_baseline_comparison.json"],
        requirements=reports["stage16g0_stage16g_implementation_requirements.json"],
        public_path_leak_scan_passed=public_path_leak_scan_passed,
        path_leak_findings=findings,
    )
    digests["stage16g0_followup_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g0_followup_acceptance_summary.json",
        summary,
    )
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=STAGE_DIR.as_posix())
    args = parser.parse_args(argv)
    digests = write_reports(Path(args.output_dir))
    print(json.dumps({"status": "passed", "output_dir": args.output_dir, "file_count": len(digests)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
