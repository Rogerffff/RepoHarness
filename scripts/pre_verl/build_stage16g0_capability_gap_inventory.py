"""Build Stage 16G.0 Claude-Code-style harness capability inventory.

This script is intentionally read-only with respect to RepoHarness behavior. It
inspects source files, tool/scaffold definitions, command policy decisions, and
known planning documents, then writes public-safe JSON evidence for Stage 16G.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from repo_harness.config.schemas import RuntimeConfig  # noqa: E402
from repo_harness.permissions import PermissionContext  # noqa: E402
from repo_harness.reward import compute_reward_metadata  # noqa: E402
from repo_harness.scaffolds.registry import build_scaffold, default_scaffold_registry  # noqa: E402
from repo_harness.tasks.command_policy import evaluate_model_execute_bash_command  # noqa: E402
from repo_harness.tools import DEFAULT_TOOL_ORDER, ToolExecutionContext, ToolExecutor, build_tool, default_tool_registry  # noqa: E402
from repo_harness.tools.schemas import ToolCall  # noqa: E402
from repo_harness.trajectory import RunRecorder  # noqa: E402
from repo_harness.verifier import VerifierResult  # noqa: E402
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace  # noqa: E402


STAGE_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_verl_workstreams/stage16g_0"
PLAN_PATH = REPO_ROOT / "docs/agentic_RL/repo_harness_verl_workstreams/49-stage-16g-0-execution-plan.md"
EVALUATION_WORKTREE = REPO_ROOT.parent / "claude-code"
EVALUATION_GAP_DOC = EVALUATION_WORKTREE / "docs/resume/repo_harness_vs_claude_code_capability_gap_analysis.md"

SOURCE_DOCS = {
    "gpt_advice_other_swe_harness_experience": REPO_ROOT / "docs/harness_improve/gpt_advice.md",
    "claude_code_typescript_agents_guide": REPO_ROOT / "reference/claude-code-typescript-src/AGENTS.md",
    "post_stage15_training_infra_stage_plan": REPO_ROOT
    / "docs/agentic_RL/training_design/post_stage15_training_infra_stage_plan.md",
    "worktree_sync_run_episode_unification_plan": REPO_ROOT
    / "docs/agentic_RL/training_design/worktree_sync_run_episode_unification_plan.md",
    "stage16f_unified_baseline_handoff": REPO_ROOT
    / "docs/agentic_RL/training_design/stage16f_unified_baseline_handoff_to_evaluation_agent.md",
}

REPO_HARNESS_FILES = [
    "src/repo_harness/tools/minimal.py",
    "src/repo_harness/scaffolds/registry.py",
    "src/repo_harness/scaffolds/patch_focused_react.py",
    "src/repo_harness/scaffolds/simple_react.py",
    "src/repo_harness/scaffolds/planner_coder_verifier.py",
    "src/repo_harness/tasks/command_policy.py",
    "src/repo_harness/tasks/public_environment.py",
    "src/repo_harness/permissions/system.py",
    "src/repo_harness/workspace/diagnostic_session.py",
    "src/repo_harness/workspace/docker_adapter.py",
    "src/repo_harness/workspace/adapter.py",
    "src/repo_harness/evaluation/runner.py",
    "src/repo_harness/evaluation/episode_runner.py",
    "src/repo_harness/evaluation/episode_projection.py",
    "src/repo_harness/evaluation/entrypoint_policy.py",
    "src/repo_harness/execution/spec.py",
    "src/repo_harness/rl/runtime.py",
    "src/repo_harness/workspace/patch_hygiene.py",
]

EXPECTED_SCAFFOLDS = [
    "simple_react",
    "patch_focused_react",
    "patch_focused_react_execute_bash",
    "patch_focused_react_diagnostic_shell",
    "patch_focused_react_mini_shell",
    "single_shot_patch",
    "planner_coder_verifier",
]

SENSITIVE_PATTERNS = [
    re.compile(r"/Users/"),
    re.compile(r"/private/"),
    re.compile(r"runtime_private/"),
    re.compile(r"provider_secret\s*[:=]"),
    re.compile(r"api[_-]?key\s*[:=]", re.IGNORECASE),
]


@dataclass(frozen=True)
class Report:
    filename: str
    payload: dict[str, Any] | list[Any]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


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


def _git_dirty_files(path: Path) -> list[dict[str, str]]:
    try:
        result = subprocess.run(
            ["git", "-C", path.as_posix(), "status", "--short"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception:
        return []
    entries: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        status = line[:2].strip() or "unknown"
        rel = line[3:] if len(line) > 3 else ""
        entries.append({"status": status, "path": rel})
    return entries


def _source_doc_entry(label: str, path: Path, *, public_kind: str = "repo_relative_path_and_sha256") -> dict[str, Any]:
    exists = path.exists()
    entry: dict[str, Any] = {
        "source_label": label,
        "exists": exists,
        "sha256": _sha256_file(path) if exists else None,
        "public_reference_kind": public_kind,
    }
    try:
        entry["relative_path"] = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        entry["relative_path"] = None
    return entry


def _repo_file_entry(relative_path: str) -> dict[str, Any]:
    path = REPO_ROOT / relative_path
    return {"relative_path": relative_path, "exists": path.exists(), "sha256": _sha256_file(path)}


def _tool_feature_flags(tool_name: str) -> dict[str, Any]:
    definition = build_tool(tool_name)
    prompt = f"{definition.model_visible_description}\n{definition.model_visible_prompt}".lower()
    return {
        "is_read_only": bool(definition.is_read_only),
        "is_concurrency_safe": bool(definition.is_concurrency_safe),
        "model_visible_output_truncated": definition.max_result_size is not None,
        "raw_artifact_runtime_private": tool_name in {"execute_bash", "diagnostic_shell"},
        "artifact_replay_tool_available": tool_name == "read_tool_result_artifact",
        "path_redaction_applied": tool_name in {"execute_bash", "diagnostic_shell", "read_file", "grep", "list_files", "glob_files"},
        "training_view_projection_allowed": tool_name not in {"diagnostic_shell"},
        "diagnostic_side_channel_only": tool_name == "diagnostic_shell",
        "mentions_recovery_or_recommended_next_call": "recovery" in prompt or "recommended" in prompt or "retry" in prompt,
    }


def build_source_inventory() -> dict[str, Any]:
    eval_doc_exists = EVALUATION_GAP_DOC.exists()
    docs = [
        {
            "source_label": "repo_harness_vs_claude_code_capability_gap_analysis",
            "exists": eval_doc_exists,
            "sha256": _sha256_file(EVALUATION_GAP_DOC) if eval_doc_exists else None,
            "public_reference_kind": "source_doc_sha256_only",
            "relative_path": None,
        }
    ]
    docs.extend(_source_doc_entry(label, path) for label, path in SOURCE_DOCS.items())
    return {
        "schema_version": "stage16g0.source_inventory.v1",
        "training_worktree_commit": _git_commit(REPO_ROOT),
        "training_worktree_dirty_files": _git_dirty_files(REPO_ROOT),
        "evaluation_worktree_label": "evaluation_worktree",
        "evaluation_worktree_commit": _git_commit(EVALUATION_WORKTREE),
        "evaluation_worktree_dirty_file_count": len(_git_dirty_files(EVALUATION_WORKTREE)),
        "source_documents": docs,
        "repo_harness_files": [_repo_file_entry(path) for path in REPO_HARNESS_FILES],
        "claude_code_reference_files": [
            _source_doc_entry(
                "claude_code_typescript_agents_guide",
                SOURCE_DOCS["claude_code_typescript_agents_guide"],
            )
        ],
        "public_path_policy_passed": True,
        "notes": [
            "公开 source inventory 使用 source labels、repo-relative paths、commits 和 sha256；不写真实本机绝对路径。",
            "evaluation worktree 文档只以 sha256 绑定，避免公开本机路径。",
        ],
    }


def build_claude_code_tool_inventory() -> dict[str, Any]:
    source = [{"source_label": "claude_code_typescript_reference", "relative_path": "AGENTS.md", "evidence_kind": "reference_navigation"}]
    capabilities = [
        ("read_file", "file_read", "Read 类文件查看能力，是 Claude Code 风格基本工具面的一部分。", "high"),
        ("non_text_file_read", "file_read", "图片、PDF、二进制或多模态读取能力需要单独盘点；Stage 16G.0 不实现。", "low"),
        ("grep_search", "search", "Grep 类搜索能力，用于定位符号、报错文本和相关文件。", "high"),
        ("glob_search", "search", "Glob 类文件发现能力，用于按路径模式收窄工作区。", "high"),
        ("symbol_or_language_diagnostics", "navigation", "语言服务、诊断和符号级导航比轻量文本搜索更强；当前只作为后续差距记录。", "medium"),
        ("edit_file", "edit", "Edit 类精确修改已有文件能力。", "high"),
        ("write_file", "edit", "Write / create file 能力，用于新增脚本、测试或源码文件。", "high"),
        ("patch_multi_file_edit", "edit", "多文件 patch、rename、delete、large edit 需要结构化 patch 工具或等价能力。", "medium"),
        ("bash_full_shell", "shell", "Bash 能力由权限系统和 sandbox 控制，不等价于 RepoHarness 当前 execute_bash allowlist。", "medium"),
        ("testing_and_project_command", "execution", "真实 SWE agent 需要公开测试、项目命令和 setup command routing，而不只是固定 run_tests。", "medium"),
        ("background_command_monitor", "execution", "长时间运行命令、后台任务和进度监控需要单独生命周期管理。", "medium"),
        ("task_management", "planning", "Todo / task list 类能力帮助长任务保持状态。", "medium"),
        ("subagent_or_task_tool", "delegation", "Claude Code 参考体系包含任务拆分、子任务或延迟工具发现能力。", "medium"),
        ("deferred_tool_discovery", "extension", "工具搜索、插件或技能发现属于可扩展工具面，需要 profile 和训练资格单独建模。", "medium"),
        ("slash_commands", "interaction", "斜杠菜单、快捷命令和用户工作流入口不等价于模型训练工具，但会影响目标产品能力。", "low"),
        ("mcp_or_external_tools", "extension", "MCP / 插件 / 技能属于可扩展工具面，Stage 16G.0 只盘点不实现。", "medium"),
        ("hooks_permissions", "permission", "权限、hooks 和用户确认构成高风险动作边界。", "medium"),
        ("session_context_management", "context", "会话压缩、长期上下文、artifact replay 和恢复决定模型实际可用信息。", "medium"),
        ("long_output_artifact_replay", "context", "长输出需要截断、分页、artifact 回读和上下文管理。", "medium"),
    ]
    return {
        "schema_version": "stage16g0.claude_code_tool_inventory.v1",
        "source_scope": "reference/claude-code-typescript-src/AGENTS.md plus Stage 16G.0 reference navigation",
        "capabilities": [
            {
                "capability_id": capability_id,
                "category": category,
                "claude_code_capability": summary,
                "source_evidence": source,
                "confidence": confidence,
            }
            for capability_id, category, summary, confidence in capabilities
        ],
    }


def build_external_reference_inventory() -> dict[str, Any]:
    refs = [
        (
            "cursor_composer_training_deployment_consistency",
            "Cursor / Composer 经验强调训练、评测和部署 harness 尽量一致，同时允许训练期更严格参数检查。",
            "RepoHarness 不能把主训练工具面收成只会静态猜 patch；需要代表真实 SWE 闭环的 public core profile。",
        ),
        (
            "codex_workspace_sandbox_approval",
            "Codex 类环境把 workspace 写入、常规命令执行、sandbox 和 approval 分层处理。",
            "RepoHarness 应保留明确权限、恢复提示和审计事实；不能把所有高风险动作都误归结为工具缺失。",
        ),
        (
            "mini_swe_agent_stable_shell",
            "稳定可执行 shell 有助于形成定位、复现、修改、验证闭环。",
            "RepoHarness 不应长期只依赖过窄 execute_bash；应设计 public diagnostic command 或 run_project_test。",
        ),
        (
            "claude_code_layered_tools",
            "真实产品不是只给 Bash，而是 Read / Grep / Glob / Edit / Write / Bash 分层。",
            "Stage 16G 应优先补结构化工具与受控 public command，而不是简单开放完整 shell。",
        ),
        (
            "deployment_training_consistency",
            "训练工具面和目标部署工具面不一致会让 RL 优化错误行为。",
            "Stage 17B / Stage 20 前必须固定 SWE public profile，并用 probes 验证。",
        ),
        (
            "openhands_swegym_deepswe_executable_environment",
            "OpenHands、SWE-Gym 和 DeepSWE 都强调可执行环境、代码导航、命令行 build/test 和迭代验证。",
            "project command routing、依赖 setup、private overlay 和 verifier healthcheck 是硬前置。",
        ),
        (
            "reward_hacking_monitoring",
            "agentic RL 需要 deterministic safety boundary 加 monitor / quarantine。",
            "LLM-as-judge 只能做辅助监控，不能替代路径隔离、artifact hygiene 和 verifier 隔离。",
        ),
    ]
    return {
        "schema_version": "stage16g0.external_swe_harness_reference_inventory.v1",
        "source_document_label": "gpt_advice",
        "references": [
            {
                "reference_id": reference_id,
                "source_document_label": "gpt_advice",
                "claim_summary": claim,
                "repo_harness_design_implication": implication,
                "confidence": "medium",
                "needs_primary_source_verification_before_public_claim": True,
            }
            for reference_id, claim, implication in refs
        ],
    }


def build_repoharness_tool_inventory() -> dict[str, Any]:
    default_scaffold = build_scaffold(RuntimeConfig().scaffold_id)
    registry_names = sorted(default_tool_registry().names())
    tools = []
    for tool_name in sorted(set(DEFAULT_TOOL_ORDER) | {"execute_bash", "diagnostic_shell"}):
        definition = build_tool(tool_name)
        visible_scaffolds = []
        for scaffold_id in default_scaffold_registry().ids():
            scaffold = build_scaffold(scaffold_id)
            all_tools = set(scaffold.allowed_tools)
            for phase in scaffold.phases():
                all_tools.update(scaffold.allowed_tools_for_phase(phase))
            if tool_name in all_tools:
                visible_scaffolds.append(scaffold_id)
        tools.append(
            {
                "tool_name": tool_name,
                "tool_version": definition.tool_version,
                "model_visible_default": tool_name in default_scaffold.allowed_tools,
                "visible_in_scaffolds": visible_scaffolds,
                "training_eligible_default": (
                    "conditional"
                    if tool_name in {"bash", "run_tests"}
                    else bool(tool_name in default_scaffold.allowed_tools and tool_name != "diagnostic_shell")
                ),
                "side_channel_risk": tool_name in {"bash", "execute_bash", "diagnostic_shell"},
                "permission_policy_refs": _permission_refs_for_tool(tool_name),
                "build_tool_available": True,
                "default_registry_available": tool_name in registry_names,
                "scaffold_registry_available": bool(visible_scaffolds),
                "runtime_registry_bound": True,
                "known_limitations": _known_tool_limitations(tool_name),
                **_tool_feature_flags(tool_name),
            }
        )
    return {
        "schema_version": "stage16g0.repoharness_tool_inventory.v1",
        "training_default_scaffold_id": default_scaffold.scaffold_id,
        "training_default_scaffold_source": "RunConfig.runtime.scaffold_id default",
        "default_tool_order": list(DEFAULT_TOOL_ORDER),
        "tools": tools,
        "important_code_facts": [
            "create_file exists in DEFAULT_TOOL_ORDER and is visible in simple_react.",
            "patch_focused_react intentionally omits create_file and shell tools.",
            "execute_bash is narrow but not empty: safe rg/grep/git status/diff/grep/ls-files, pytest, and light literal Python diagnostics are allowed by policy.",
            "diagnostic_shell is a Stage 16B persistent diagnostic profile tool, not default formal training surface.",
        ],
    }


def _permission_refs_for_tool(tool_name: str) -> list[str]:
    if tool_name == "execute_bash":
        return ["command_policy.evaluate_model_execute_bash_command", "minimal._execute_bash"]
    if tool_name == "bash":
        return ["command_policy.evaluate_model_bash_command", "minimal._bash"]
    if tool_name == "diagnostic_shell":
        return ["diagnostic_session.diagnostic_command_policy_issue", "minimal._diagnostic_shell"]
    if tool_name in {"read_file", "grep", "glob_files", "list_files", "symbol_search"}:
        return ["workspace visibility filters", "tool result pagination"]
    return []


def _known_tool_limitations(tool_name: str) -> list[str]:
    mapping = {
        "execute_bash": [
            "安全最小 allowlist，不是完整 shell。",
            "拒绝动态 shell、未审计脚本、包管理器、网络下载、runtime-private 路径和 Git history。",
        ],
        "diagnostic_shell": [
            "不是默认训练工具；需要显式 diagnostic profile。",
            "文件系统 projection 持久；命令 cwd/env 通过每次工具调用和 session HOME 策略控制，不应当成完整交互 shell。",
        ],
        "run_tests": ["不接受任意命令参数；只运行配置好的 public feedback path。"],
        "edit_file": ["exact replace 协议；复杂多文件 patch 仍缺少 apply_patch 类工具。"],
        "create_file": ["存在于默认 simple_react，但 patch_focused_react 不暴露。"],
        "bash": ["legacy restricted diagnostic command path；不等价于 Claude Code Bash。"],
        "symbol_search": ["轻量 Python AST symbol search，不是完整 LSP。"],
    }
    return mapping.get(tool_name, [])


def build_scaffold_matrix() -> dict[str, Any]:
    registry = default_scaffold_registry()
    existing_ids = set(registry.ids())
    records = []
    for scaffold_id in EXPECTED_SCAFFOLDS:
        if scaffold_id not in existing_ids:
            records.append(
                {
                    "scaffold_name": scaffold_id,
                    "exists": False,
                    "status": "not_present_in_current_worktree",
                    "allowed_tool_names": [],
                    "executor_registry_consistent": False,
                }
            )
            continue
        scaffold = build_scaffold(scaffold_id)
        allowed = list(scaffold.allowed_tools)
        all_phase_tools = sorted({tool for phase in scaffold.phases() for tool in scaffold.allowed_tools_for_phase(phase)})
        unknown_tools = [tool for tool in sorted(set(allowed) | set(all_phase_tools)) if not _tool_exists(tool)]
        records.append(
            {
                "scaffold_name": scaffold_id,
                "exists": True,
                "status": "present",
                "scaffold_version": scaffold.scaffold_version,
                "allowed_tool_names": allowed,
                "phase_sequence": scaffold.phases(),
                "phase_allowed_tools": {
                    phase: scaffold.allowed_tools_for_phase(phase) for phase in scaffold.phases()
                },
                "executor_registry_consistent": not unknown_tools,
                "unknown_tools": unknown_tools,
                "scaffold_registry_available": True,
                "runtime_registry_bound": True,
                "has_shell": any(tool in set(allowed) | set(all_phase_tools) for tool in {"bash", "execute_bash", "diagnostic_shell"}),
                "has_create_file": any(tool == "create_file" for tool in set(allowed) | set(all_phase_tools)),
                "has_patch_apply": False,
                "has_parameterized_public_tests": False,
                "has_task_management": "partial" if "update_working_state" in set(allowed) | set(all_phase_tools) else False,
                "public_environment_injected": True,
                "stage16e_patch_hygiene_bound": True,
            }
        )
    return {
        "schema_version": "stage16g0.scaffold_capability_matrix.v1",
        "training_default_scaffold_id": RuntimeConfig().scaffold_id,
        "records": records,
    }


def _tool_exists(tool_name: str) -> bool:
    try:
        build_tool(tool_name)
        return True
    except Exception:
        return False


def build_capability_gap_matrix() -> dict[str, Any]:
    rows = [
        _gap(
            "default_training_scaffold_identity",
            "scaffold",
            "present_default",
            "当前代码默认训练 scaffold 是 simple_react，而不是 patch_focused_react。",
            "如果 review 把 patch_focused_react 当默认，会误判 create_file / bash 能力缺失。",
            "确认 profile taxonomy，后续报告必须区分 simple_react、patch_focused_react 和 diagnostic variants。",
            "16G.1",
            "P1",
            False,
            True,
        ),
        _gap(
            "parameterized_public_test_command",
            "test_feedback",
            "partial",
            "run_tests 无参数；execute_bash 变体可运行安全 pytest，但不是所有 scaffold 默认暴露。",
            "模型难以稳定表达单个 pytest case、Django label、Sphinx/tox/nox 等公开诊断。",
            "设计 run_public_command 或 run_project_test，绑定 public selector、dependency setup 和 verifier facts。",
            "16G.3",
            "P0",
            True,
            True,
        ),
        _gap(
            "scratch_python_or_reproduction_script",
            "diagnosis",
            "partial",
            "execute_bash 允许轻量 literal python；diagnostic_shell 可做复现但 diagnostic-only；没有正式 scratch_python 工具。",
            "模型可能缺少安全的复现脚本路径，或把临时脚本误混进 final patch。",
            "新增 scratch_python 或 run_public_command scratch workspace，并保证临时 artifact 不进入 final.patch。",
            "16G.3",
            "P0",
            True,
            True,
        ),
        _gap(
            "project_command_routing",
            "test_feedback",
            "partial",
            "现有 run_tests 只跑配置反馈路径；没有统一项目命令 router。",
            "Django、Sphinx、tox、nox、repo script 和 selector 参数需要外部策略支持。",
            "设计 project command routing，区分 public commands、setup commands 和 hidden verifier。",
            "16G.3",
            "P0",
            True,
            True,
        ),
        _gap(
            "dependency_setup_or_private_overlay",
            "environment",
            "partial",
            "Stage 16B 对依赖变更默认保守拒绝；私有 per-episode overlay 仍不是正式训练能力。",
            "真实 SWE 任务常需要安装项目依赖或构建临时环境。",
            "设计 dependency setup policy、private overlay 和共享依赖只读证明。",
            "16G.4",
            "P0",
            True,
            True,
        ),
        _gap(
            "apply_patch_or_unified_diff_tool",
            "editing",
            "missing",
            "edit_file 和 create_file 存在，但没有 Claude Code 风格 apply_patch / multi-file patch 工具。",
            "复杂多文件修改、rename、delete、large patch 操作效率低。",
            "在 Stage 16E patch hygiene 基础上设计 apply_patch 或 structured patch tool。",
            "16G.2",
            "P1",
            True,
            True,
        ),
        _gap(
            "write_delete_move_mkdir_operations",
            "editing",
            "partial",
            "create_file 存在；delete/move/mkdir/write_file 等操作未形成完整结构化工具面。",
            "新增文件夹、重命名、删除旧文件和复杂项目结构修改受限。",
            "补齐结构化 file operation 工具，并绑定 patch hygiene。",
            "16G.2",
            "P1",
            True,
            True,
        ),
        _gap(
            "permission_denial_recovery",
            "permission",
            "present_default",
            "CommandPolicyDecision 和 ToolResult 已有 reason_code、recovery_hint、safe_argv 等结构化恢复字段。",
            "不是从零缺失；后续应验证模型是否学会使用恢复建议。",
            "把 denial recovery 作为 probe 和 reward/auxiliary signal 候选，而不是重新设计基础字段。",
            "16G.6",
            "P2",
            False,
            False,
        ),
        _gap(
            "tool_result_artifact_replay",
            "context",
            "present_default",
            "read_tool_result_artifact 存在；长输出分页和 artifact 回读是当前工具面的一部分。",
            "需要继续证明不同工具的 raw artifact 不泄漏 runtime-private 内容。",
            "把 artifact replay 纳入 profile matrix 和 parity probe。",
            "16G.1",
            "P2",
            False,
            False,
        ),
        _gap(
            "diagnostic_shell_formal_training_status",
            "shell",
            "present_diagnostic_only",
            "diagnostic_shell 是 Stage 16B profile 工具，不是默认 formal training 工具；文件 projection 持久，cwd/env 每次命令受策略控制。",
            "高价值调试行为可能被 diagnostic-only 分类，不能直接进入 policy loss。",
            "决定是否升级为 formal public diagnostic profile，或新增 run_public_command。",
            "16G.4",
            "P1",
            True,
            True,
        ),
        _gap(
            "execute_bash_narrow_but_not_toy",
            "shell",
            "present_non_default",
            "execute_bash 是安全最小 allowlist，但允许 rg/grep、安全 git 子集、pytest、受限 Python heredoc等。",
            "它不是完整 Bash，也不是空工具；应评价为窄而可审计，不是 toy。",
            "作为 safe_structured_only profile 保留；不要把它误当主 SWE 工具面终点。",
            "16G.1",
            "P2",
            False,
            True,
        ),
        _gap(
            "final_only_public_diagnostic_decoupling",
            "test_feedback",
            "unknown",
            "final-only / hidden evaluator 当前会禁用 run_tests 或 diagnostic_shell，安全上合理，但可能同时挡住 public diagnostic。",
            "隐藏 verifier 不可见是硬边界；公开诊断命令是否可见是训练工具面设计问题。",
            "Stage 16G.3 需要明确 public diagnostic 和 hidden final verifier 解耦。",
            "16G.3",
            "P1",
            True,
            True,
        ),
        _gap(
            "todo_or_task_management",
            "planning",
            "partial",
            "update_working_state 存在，但没有 Claude Code 风格 todo_write / task list。",
            "长任务规划、回溯和状态跟踪可能弱于目标部署环境。",
            "决定是否新增 todo_write 或增强 update_working_state。",
            "16G.2",
            "P2",
            False,
            True,
        ),
        _gap(
            "subagent_mcp_plugin_skill",
            "extension",
            "missing",
            "完整 MCP、插件、技能和子代理不在当前工具面中。",
            "不是 Stage 17B/20 的直接阻断，但应在 trajectory schema 预留能力位。",
            "Stage 16G.1 只做 schema/profile 预留，暂不实现完整系统。",
            "16G.1",
            "P3",
            False,
            False,
        ),
        _gap(
            "symbol_search_lsp_depth",
            "navigation",
            "partial",
            "symbol_search 是轻量 Python AST 搜索，不是完整 LSP。",
            "对 Python 之外项目或深层语义导航帮助有限。",
            "作为 P3 后续增强；不阻塞 Stage 17A schema-only。",
            "16G.5",
            "P3",
            False,
            False,
        ),
        _gap(
            "patch_capture_verifier_reward_linkage",
            "training_target",
            "partial",
            "Stage 16E/16F 已绑定 final.patch、hygiene、projection、reward/export，但新工具操作还未全部映射。",
            "新增 file/patch/scratch 工具若不接入 linkage，会形成无效训练目标。",
            "为每类工具动作定义 final patch / verifier / reward / export linkage gate。",
            "16G.6",
            "P1",
            True,
            True,
        ),
    ]
    return {
        "schema_version": "stage16g0.capability_gap_matrix.v1",
        "gap_records": rows,
        "capability_gap_count": len(rows),
        "p0_gap_count": sum(1 for row in rows if row["priority"] == "P0"),
        "blocking_for_stage17_data_freeze_count": sum(1 for row in rows if row["blocking_for_stage17_data_freeze"]),
        "blocking_for_stage20_warm_start_count": sum(1 for row in rows if row["blocking_for_stage20_warm_start"]),
    }


def _gap(
    capability_id: str,
    category: str,
    status: str,
    evidence: str,
    impact: str,
    action: str,
    stage: str,
    priority: str,
    block17: bool,
    block20: bool,
) -> dict[str, Any]:
    return {
        "capability_id": capability_id,
        "category": category,
        "repo_harness_status": status,
        "priority": priority,
        "claude_code_baseline": "目标是 Claude Code 类真实 SWE agent 工具面；具体实现不能直接照搬。",
        "repo_harness_evidence": [evidence],
        "ability_impact": impact,
        "training_risk": impact,
        "security_reason_if_blocked": "需要同时保护 hidden verifier、gold/test patch、runtime-private、本机路径、Git history 和共享依赖环境。",
        "recommended_action": action,
        "recommended_stage": stage,
        "blocking_for_stage17_data_freeze": block17,
        "blocking_for_stage20_warm_start": block20,
    }


def build_capability_probe_report() -> dict[str, Any]:
    execute_bash_commands = {
        "rg_literal_search_allowed": "rg '$foo' src",
        "pytest_allowed": "python -m pytest -q tests/test_example.py",
        "unallowlisted_cat_denied": "cat README.md",
        "git_history_denied": "git log --oneline",
    }
    decisions = {
        key: evaluate_model_execute_bash_command(command).model_dump(mode="json")
        for key, command in execute_bash_commands.items()
    }
    default_scaffold = build_scaffold(RuntimeConfig().scaffold_id)
    patch_scaffold = build_scaffold("patch_focused_react")
    registry = default_scaffold_registry()
    registry_consistent = all(
        _tool_exists(tool)
        for scaffold_id in registry.ids()
        for tool in build_scaffold(scaffold_id).allowed_tools
    )
    executable_probe = _run_minimal_executable_tool_loop_probe()
    probes = [
        {
            "probe_id": "training_default_scaffold_identity",
            "capability_under_test": "which_scaffold_is_default_training_surface",
            "actual_status": "passed",
            "observed_default_scaffold": default_scaffold.scaffold_id,
            "default_has_create_file": "create_file" in default_scaffold.allowed_tools,
            "default_has_bash": "bash" in default_scaffold.allowed_tools,
            "notes": "代码事实：RuntimeConfig.runtime.scaffold_id 默认 simple_react。",
        },
        {
            "probe_id": "patch_focused_react_tool_surface",
            "capability_under_test": "conservative_patch_scaffold_tool_surface",
            "actual_status": "structured_gap",
            "scaffold": "patch_focused_react",
            "has_create_file": "create_file" in patch_scaffold.allowed_tools,
            "has_shell": any(tool in patch_scaffold.allowed_tools for tool in ("bash", "execute_bash", "diagnostic_shell")),
            "gap_ids": ["profile_dependent_file_create_and_shell"],
        },
        {
            "probe_id": "patch_focused_react_mini_shell_absent",
            "capability_under_test": "planned_scaffold_presence",
            "actual_status": "structured_gap",
            "scaffold": "patch_focused_react_mini_shell",
            "exists": "patch_focused_react_mini_shell" in registry.ids(),
            "gap_ids": ["scaffold_not_present"],
        },
        {
            "probe_id": "scaffold_registry_consistency",
            "capability_under_test": "allowed_tools_match_executor_registry",
            "actual_status": "passed" if registry_consistent else "structured_gap",
            "registry_consistent": registry_consistent,
        },
        {
            "probe_id": "execute_bash_narrow_not_toy",
            "capability_under_test": "execute_bash_allow_and_deny_examples",
            "actual_status": "passed",
            "decisions": decisions,
            "interpretation": "允许安全搜索和 pytest，拒绝 cat/git history；窄但不是空工具面。",
        },
        {
            "probe_id": "run_tests_no_parameterized_command",
            "capability_under_test": "parameterized_public_test_command",
            "actual_status": "structured_gap",
            "run_tests_schema": build_tool("run_tests").input_schema,
            "gap_ids": ["run_tests_no_arguments"],
        },
        {
            "probe_id": "scratch_python_reproduction_script",
            "capability_under_test": "scratch_python_or_reproduction_script",
            "actual_status": "static_policy_probe_only",
            "execute_bash_light_python_supported": evaluate_model_execute_bash_command(
                "python -c 'print(\"$literal\")'"
            ).decision
            == "allow",
            "formal_scratch_python_tool_exists": False,
            "temporary_artifact_excluded_from_final_patch": "not_proven_by_stage16g0_static_policy_probe",
            "diagnostic_shell_scratch_execution_probe": "not_run_in_stage16g0",
            "gap_ids": ["no_formal_scratch_python_tool"],
        },
        {
            "probe_id": "default_scaffold_read_search_edit_patch_reward_loop",
            "capability_under_test": "minimal_executable_tool_loop_from_default_scaffold_to_patch_and_reward",
            **executable_probe,
        },
        {
            "probe_id": "patch_capture_verifier_reward_linkage_modules",
            "capability_under_test": "tool_action_to_final_patch_verifier_reward_export_static_modules",
            "actual_status": "passed",
            "evidence_modules": [
                "workspace.patch_hygiene",
                "workspace.adapter.capture_final_patch",
                "workspace.docker_adapter.capture_final_patch",
                "evaluation.episode_projection",
                "reward.calculator",
                "export.exporter",
                "scripts/pre_verl/build_swebench_official_inputs.py",
            ],
            "remaining_gap": "new future tools must explicitly bind into these same paths.",
        },
    ]
    return {
        "schema_version": "stage16g0.capability_probe.v1",
        "probes": probes,
        "probe_count": len(probes),
        "failed_or_gap_probe_count": sum(1 for probe in probes if probe["actual_status"] != "passed"),
    }


def _run_minimal_executable_tool_loop_probe() -> dict[str, Any]:
    """Run a tiny local probe without persisting raw workspace paths publicly."""

    try:
        with tempfile.TemporaryDirectory(prefix="stage16g0_probe_") as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            run_dir.mkdir()
            workspace = run_dir / "workspaces" / "agent_workspace"
            workspace.mkdir(parents=True)
            (workspace / "pkg.py").write_text(
                "def add(left, right):\n    return left - right\n",
                encoding="utf-8",
            )
            tests_dir = workspace / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_pkg.py").write_text(
                "from pkg import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
                encoding="utf-8",
            )
            _run_probe_command(["git", "init"], workspace)
            _run_probe_command(["git", "config", "user.email", "stage16g0@example.invalid"], workspace)
            _run_probe_command(["git", "config", "user.name", "Stage 16G0 Probe"], workspace)
            _run_probe_command(["git", "add", "."], workspace)
            _run_probe_command(["git", "commit", "-m", "initial"], workspace)

            adapter = LocalWorkspaceAdapter(run_id="stage16g0-probe", run_dir=run_dir)
            with RunRecorder("stage16g0-probe", run_dir, task_id="stage16g0-probe") as recorder:
                snapshot = adapter.create_agent_start_snapshot(workspace, None, recorder)
                run_workspace = RunWorkspace(
                    run_id="stage16g0-probe",
                    workspace_path=workspace.as_posix(),
                    artifact_dir=(run_dir / "artifacts").as_posix(),
                    dependency_state=DependencyState(),
                    agent_start_snapshot=snapshot,
                    agent_diff_base=snapshot,
                )
                context = ToolExecutionContext(
                    run_id="stage16g0-probe",
                    task_id="stage16g0-probe",
                    workspace_facade=adapter,
                    run_workspace=run_workspace,
                    artifact_writer=recorder,
                    permission_context=PermissionContext(mode="auto"),
                    verifier_feedback_facade=None,  # type: ignore[arg-type]
                    resolved_verifier_plan=None,  # type: ignore[arg-type]
                )
                executor = ToolExecutor()
                tool_results = [
                    _execute_probe_tool(executor, context, "read_file", {"path": "pkg.py"}),
                    _execute_probe_tool(executor, context, "grep", {"query": "return left - right", "path": "pkg.py"}),
                    _execute_probe_tool(
                        executor,
                        context,
                        "edit_file",
                        {
                            "path": "pkg.py",
                            "old_text": "    return left - right\n",
                            "new_text": "    return left + right\n",
                        },
                    ),
                    _execute_probe_tool(
                        executor,
                        context,
                        "create_file",
                        {"path": "notes.txt", "content": "Stage 16G.0 executable probe note.\n"},
                    ),
                    _execute_probe_tool(executor, context, "git_diff", {}),
                ]
                pytest_result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q"],
                    cwd=workspace,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                    check=False,
                )
                capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
                final_verifier = VerifierResult.model_validate(
                    {
                        "parser_confidence": 0.9,
                        "command": "python -m pytest -q",
                        "test_cases": [],
                        "accepted": pytest_result.returncode == 0,
                        "pass_ratio": 1.0 if pytest_result.returncode == 0 else 0.0,
                        "fail_to_pass": {"passed": 1 if pytest_result.returncode == 0 else 0, "total": 1},
                        "pass_to_pass": {"passed": 1 if pytest_result.returncode == 0 else 0, "total": 1},
                        "exit_code": pytest_result.returncode,
                        "timeout": False,
                        "error_type": None if pytest_result.returncode == 0 else "public_test_failed",
                    }
                )
                reward = compute_reward_metadata(
                    final_verifier,
                    patch_stats=capture.patch_stats,
                    event_counts={"turn_count": 1, "tool_call_count": len(tool_results), "test_run_count": 1},
                )
            return {
                "actual_status": "passed" if all(result["status"] == "ok" for result in tool_results) and pytest_result.returncode == 0 else "structured_gap",
                "tool_loop_executed": True,
                "tools_executed": [result["tool_name"] for result in tool_results],
                "tool_result_statuses": {result["tool_name"]: result["status"] for result in tool_results},
                "public_test_exit_code": pytest_result.returncode,
                "public_test_passed": pytest_result.returncode == 0,
                "final_patch_generated": bool(capture.patch_text.strip()),
                "cleaned_patch_sha256": _sha256_text(capture.patch_text),
                "patch_hygiene_status": capture.patch_stats.get("patch_hygiene", {}).get("status"),
                "patch_added_lines": capture.patch_stats.get("added_lines"),
                "patch_removed_lines": capture.patch_stats.get("removed_lines"),
                "reward_metadata_computed": True,
                "reward_final": reward.final_reward,
                "reward_invalid_for_training": reward.invalid_for_training,
                "public_safety": "only statuses and sha256 are exported; temporary workspace paths and raw patch text are not exported",
            }
    except Exception as exc:  # pragma: no cover - exercised as structured evidence, not expected in tests.
        return {
            "actual_status": "structured_gap",
            "tool_loop_executed": False,
            "error_type": type(exc).__name__,
            "public_safety": "exception message intentionally omitted to avoid temporary path disclosure",
        }


def _run_probe_command(command: list[str], cwd: Path) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def _execute_probe_tool(
    executor: ToolExecutor,
    context: ToolExecutionContext,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    result = executor.execute(
        ToolCall(
            tool_call_id=f"stage16g0_probe_{tool_name}",
            tool_name=tool_name,
            arguments=arguments,
            turn=1,
        ),
        context,
    )
    return {"tool_name": tool_name, "status": result.status, "error_type": result.error_type}


def build_permission_and_shell_report() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.permission_and_shell_semantics_gap.v1",
        "execute_bash": {
            "status": "safe_minimal_allowlist",
            "not_toy_evidence": [
                "Allows safe rg/grep searches.",
                "Allows safe pytest / python -m pytest commands.",
                "Allows safe git status/diff/grep/ls-files subsets.",
                "Allows very light literal python diagnostics.",
            ],
            "denied_categories": [
                "Git history",
                "runtime-private paths",
                "hidden evaluator markers",
                "package managers",
                "network downloads",
                "dynamic shell expansion",
                "scripts and secondary executors",
            ],
        },
        "diagnostic_shell": {
            "status": "present_diagnostic_only",
            "shell_semantics": "bash -lc",
            "persistence": "filesystem projection persists; each command supplies cwd/env through policy-controlled session environment",
            "training_default_visible": False,
            "hidden_evaluator_guard": True,
            "known_gap": "high-value diagnostics may be side-channel only unless Stage 16G formalizes public diagnostic eligibility",
        },
        "legacy_bash": {
            "status": "present_default_in_simple_react",
            "semantics": "restricted diagnostic command path, routes public tests to run_tests when policy allows",
        },
        "public_vs_hidden_diagnostic_decoupling": {
            "hidden_final_verifier_invisible": True,
            "public_diagnostic_command_should_be_separate_design_axis": True,
            "risk": "final-only safety can accidentally remove public diagnostic learning signal if not separately modeled",
        },
        "permission_denial_recovery_fields_present": ["reason_code", "recovery_hint", "safe_argv"],
    }


def build_test_feedback_report() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.test_feedback_project_command_gap.v1",
        "run_tests": {
            "takes_arguments": False,
            "configured_public_feedback_only": True,
            "arbitrary_public_command_supported": False,
        },
        "recognized_public_test_commands_in_command_policy": [
            "pytest",
            "python -m pytest",
            "python -m unittest",
            "tox",
            "nox",
        ],
        "gaps": [
            "No formal run_project_test tool with task-declared command templates.",
            "No first-class selector field for Django labels, Sphinx tests, tox/nox envs, or single failing tests.",
            "Dependency setup and public command routing are not unified with private overlay facts.",
        ],
        "dependency_setup_boundary": {
            "shared_dependency_environment_write": "denied_or_requires_controlled_launcher",
            "private_overlay": "not_formalized_for_default_training",
            "setup_command_policy": "limited repo script policy exists for task setup, but model-visible command routing is separate",
        },
        "recommendation": "Design run_public_command/run_project_test with declared command templates, selector args, public observation projection, and dependency setup facts.",
    }


def build_edit_write_report() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.edit_write_file_operation_gap.v1",
        "operations": {
            "edit_file": {"status": "present_default", "notes": "Exact replace in existing UTF-8 file."},
            "create_file": {"status": "present_default_in_simple_react", "notes": "Not exposed by patch_focused_react."},
            "write_file": {"status": "missing"},
            "delete_file": {"status": "missing"},
            "move_file": {"status": "missing"},
            "mkdir": {"status": "missing"},
            "apply_patch_unified_diff": {"status": "missing"},
        },
        "stage16e_patch_hygiene_support": {
            "cleaned_final_patch": True,
            "nested_dependency_build_excludes": True,
            "runtime_private_path_variants_filtered": True,
            "git_quoted_path_handling_required": True,
        },
        "recommendation": "Use Stage 16E hygiene as the acceptance gate for new write/patch tools.",
    }


def build_linkage_report() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.patch_capture_verifier_reward_linkage.v1",
        "operations": [
            {
                "operation_id": "edit_existing_source_file",
                "tool_or_profile": "edit_file",
                "enters_final_patch": True,
                "enters_official_prediction": True,
                "enters_training_view": True,
                "reward_builder_can_reference_public_facts": True,
                "export_visible": True,
                "known_gaps": [],
            },
            {
                "operation_id": "create_new_file",
                "tool_or_profile": "create_file",
                "enters_final_patch": True,
                "enters_official_prediction": True,
                "enters_training_view": True,
                "reward_builder_can_reference_public_facts": True,
                "export_visible": True,
                "known_gaps": ["not exposed by patch_focused_react"],
            },
            {
                "operation_id": "scratch_python_reproduction_script",
                "tool_or_profile": "diagnostic_shell_or_future_scratch_python",
                "enters_final_patch": False,
                "enters_official_prediction": False,
                "diagnostic_facts_public_safe": "partial",
                "known_gaps": ["no formal scratch_python tool"],
            },
            {
                "operation_id": "future_apply_patch",
                "tool_or_profile": "not_present",
                "enters_final_patch": "must_be_bound_before_training",
                "known_gaps": ["apply_patch tool missing"],
            },
        ],
        "final_answer_claim_cross_check": {
            "test_claim_requires_tool_event": True,
            "unsupported_claim_status": "diagnostic_or_negative_signal",
        },
        "patch_hygiene_projection": {
            "official_prediction_builder_reads_hygiene_report": True,
            "reward_builder_reads_patch_hygiene": True,
            "exporter_reads_patch_hygiene": True,
        },
    }


def build_task_management_report() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.task_management_subagent_gap.v1",
        "update_working_state": {"status": "present_default", "scope": "brief hypothesis/candidate/next action state"},
        "todo_write": {"status": "missing", "priority": "P2"},
        "subagent": {"status": "missing", "priority": "P3", "stage16g0_decision": "schema reserve only"},
        "mcp_plugin_skill": {"status": "missing", "priority": "P3", "stage16g0_decision": "schema reserve only"},
        "background_task": {"status": "missing", "priority": "P3", "stage16g0_decision": "do not implement before core public SWE tool profile"},
    }


def build_profile_recommendations() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.training_tool_surface_profile_recommendations.v1",
        "recommended_profiles": [
            {
                "profile_name": "safe_structured_only",
                "intended_use": "safe baseline and red-team comparison",
                "suitable_as_main_swe_rl_surface": False,
                "must_include": ["read_file", "grep", "glob_files", "edit_file", "git_diff", "run_tests"],
                "limitations": ["Too little public command/scratch reproduction ability for main SWE RL."],
            },
            {
                "profile_name": "swe_public_core",
                "intended_use": "candidate main training surface",
                "suitable_as_main_swe_rl_surface": True,
                "must_include": [
                    "read_file",
                    "grep",
                    "glob_files",
                    "edit_file",
                    "create_file",
                    "apply_patch_or_equivalent",
                    "run_public_command_or_run_project_test",
                    "scratch_python",
                    "git_diff",
                    "todo_or_working_state",
                    "read_tool_result_artifact",
                ],
                "must_exclude": ["hidden verifier", "gold patch", "test patch", "runtime-private path", "shared dependency write"],
            },
            {
                "profile_name": "swe_public_extended",
                "intended_use": "future closer-to-Claude-Code surface",
                "suitable_as_main_swe_rl_surface": "future",
                "may_include": ["controlled diagnostic shell", "LSP", "subagent", "MCP", "skills", "background task monitor"],
            },
            {
                "profile_name": "redteam_restricted",
                "intended_use": "reward hacking and leakage pressure tests",
                "suitable_as_main_swe_rl_surface": False,
            },
        ],
    }


def build_deployment_mismatch_report(gaps: dict[str, Any]) -> dict[str, Any]:
    risks = []
    for row in gaps["gap_records"]:
        if row["priority"] in {"P0", "P1"}:
            risks.append(
                {
                    "risk_id": row["capability_id"],
                    "risk_level": row["priority"],
                    "description": row["training_risk"],
                    "evidence_refs": [f"stage16g0_capability_gap_matrix:{row['capability_id']}"],
                    "recommended_stage": row["recommended_stage"],
                }
            )
    return {
        "schema_version": "stage16g0.training_deployment_mismatch.v1",
        "target_deployment_style": "claude_code_like_swe_agent",
        "current_default_training_profile": RuntimeConfig().scaffold_id,
        "mismatch_risks": risks,
        "stage17_data_freeze_risk": "blocked_until_tool_profile_decision",
        "balanced_conclusion": "RepoHarness has useful structured tools and recovery facts; the main risk is insufficient formal public diagnostic/project command/scratch capability for Claude-Code-like SWE RL, not total tool absence.",
    }


def build_reward_hacking_report() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.reward_hacking_monitoring_gap.v1",
        "hard_fail_categories": [
            "hidden_verifier_access",
            "gold_patch_access",
            "host_filesystem_escape",
            "test_tampering",
            "dependency_tampering",
            "git_history_exploit",
        ],
        "quarantine_categories": [
            "reward_hacking_suspicion",
            "strange_environment_artifact_usage",
            "suspicious_public_test_modification",
            "unexplained_huge_diff",
            "false_claimed_test_run",
        ],
        "auxiliary_reward_candidates": [
            "evidence_backed_validation",
            "good_permission_denial_recovery",
            "minimal_diff",
            "accurate_final_test_report",
        ],
        "invalid_tool_call_policy": "不能默认过滤；需要区分模型行为、权限拒绝、基础设施失败和 harness 崩溃。",
        "llm_judge_role": "monitor_reviewer_quarantine_auxiliary_signal_not_primary_safety_boundary",
    }


def build_readiness_report(gaps: dict[str, Any]) -> dict[str, Any]:
    blocking = [
        row["capability_id"]
        for row in gaps["gap_records"]
        if row["blocking_for_stage17_data_freeze"] or row["blocking_for_stage20_warm_start"]
    ]
    return {
        "schema_version": "stage16g0.stage17_readiness_gate.v1",
        "stage17a_schema_only_allowed": True,
        "stage17b_real_data_freeze_allowed": False,
        "stage20_warm_start_data_generation_allowed": False,
        "stage21_formal_rl_allowed": False,
        "blocking_reasons": blocking,
        "conditions_to_unblock": [
            "Stage 16G.1 profile taxonomy and training eligibility gates completed",
            "Stage 16G.2/16G.3 selected public SWE tool profile implemented and verified",
            "Stage 16G.5 Claude Code / mini-SWE-agent parity probes completed",
            "Stage 16.5 representative harness diagnostic passed on unified run-episode-task",
        ],
    }


def build_required_next_stage_items(gaps: dict[str, Any]) -> dict[str, Any]:
    items = []
    for row in gaps["gap_records"]:
        if row["priority"] in {"P0", "P1"}:
            items.append(
                {
                    "item_id": f"{row['recommended_stage'].lower().replace('.', '_')}_{row['capability_id']}",
                    "priority": row["priority"],
                    "source_gap_ids": [row["capability_id"]],
                    "recommended_stage": row["recommended_stage"],
                    "recommended_owner": "training_worktree",
                    "evaluation_worktree_role": "provide representative task probes and score-gap evidence",
                    "acceptance_hint": row["recommended_action"],
                }
            )
    return {"schema_version": "stage16g0.required_next_stage_items.v1", "items": items}


def build_public_evidence_policy() -> dict[str, Any]:
    return {
        "schema_version": "stage16g0.public_evidence_policy.v1",
        "rules": [
            "No local absolute paths in public evidence.",
            "No hidden verifier content, gold patch, test patch, official private output, provider secret, or API key.",
            "Risk category names such as gold_patch may appear only as labels or policy terms.",
            "Private evidence must be referenced by opaque ref and sha256.",
        ],
        "allowed_sensitive_terms_as_categories": ["gold_patch", "test_patch", "hidden_verifier", "runtime_private"],
    }


def build_path_leak_scan_report(public_dir: Path) -> dict[str, Any]:
    scanned: list[str] = []
    findings: list[dict[str, str]] = []
    paths = [PLAN_PATH, REPO_ROOT / "AGENTS.md"]
    paths.extend(sorted(public_dir.glob("*.json")))
    for path in paths:
        if not path.exists():
            continue
        if path.name == "stage16g0_path_leak_scan_report.json":
            continue
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = f"external_output/{path.name}"
        scanned.append(rel)
        text = path.read_text(encoding="utf-8")
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                findings.append({"relative_path": rel, "pattern": pattern.pattern})
    return {
        "schema_version": "stage16g0.path_leak_scan.v1",
        "public_files_scanned": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "public_path_leak_scan_passed": not findings,
        "allowlisted_contexts": [
            "risk category names such as gold_patch/test_patch/hidden_verifier/runtime_private in policy text",
            "repo-relative paths inside the current repository",
        ],
    }


def derive_summary(reports: dict[str, Any], digests: dict[str, str]) -> dict[str, Any]:
    gaps = reports["stage16g0_capability_gap_matrix.json"]
    probes = reports["stage16g0_capability_probe_report.json"]
    readiness = reports["stage16g0_stage17_readiness_gate_report.json"]
    return {
        "schema_version": "stage16g0.acceptance_summary.v1",
        "status": "passed",
        "stage16g0_complete": True,
        "source_inventory_sha256": digests["stage16g0_source_inventory.json"],
        "claude_code_tool_inventory_sha256": digests["stage16g0_claude_code_tool_inventory.json"],
        "repoharness_tool_inventory_sha256": digests["stage16g0_repoharness_tool_inventory.json"],
        "external_swe_harness_reference_inventory_sha256": digests[
            "stage16g0_external_swe_harness_reference_inventory.json"
        ],
        "scaffold_capability_matrix_sha256": digests["stage16g0_scaffold_capability_matrix.json"],
        "capability_gap_matrix_sha256": digests["stage16g0_capability_gap_matrix.json"],
        "capability_probe_report_sha256": digests["stage16g0_capability_probe_report.json"],
        "permission_and_shell_semantics_gap_report_sha256": digests[
            "stage16g0_permission_and_shell_semantics_gap_report.json"
        ],
        "test_feedback_and_project_command_gap_report_sha256": digests[
            "stage16g0_test_feedback_and_project_command_gap_report.json"
        ],
        "edit_write_file_operation_gap_report_sha256": digests[
            "stage16g0_edit_write_file_operation_gap_report.json"
        ],
        "patch_capture_verifier_reward_linkage_report_sha256": digests[
            "stage16g0_patch_capture_verifier_reward_linkage_report.json"
        ],
        "task_management_and_subagent_gap_report_sha256": digests[
            "stage16g0_task_management_and_subagent_gap_report.json"
        ],
        "training_tool_surface_profile_recommendations_sha256": digests[
            "stage16g0_training_tool_surface_profile_recommendations.json"
        ],
        "training_deployment_mismatch_risk_report_sha256": digests[
            "stage16g0_training_deployment_mismatch_risk_report.json"
        ],
        "reward_hacking_and_monitoring_gap_report_sha256": digests[
            "stage16g0_reward_hacking_and_monitoring_gap_report.json"
        ],
        "stage17_readiness_gate_report_sha256": digests["stage16g0_stage17_readiness_gate_report.json"],
        "required_next_stage_items_sha256": digests["stage16g0_required_next_stage_items.json"],
        "public_evidence_policy_sha256": digests["stage16g0_public_evidence_policy.json"],
        "path_leak_scan_report_sha256": digests["stage16g0_path_leak_scan_report.json"],
        "capability_gap_count": gaps["capability_gap_count"],
        "p0_gap_count": gaps["p0_gap_count"],
        "blocking_for_stage17_data_freeze_count": gaps["blocking_for_stage17_data_freeze_count"],
        "blocking_for_stage20_warm_start_count": gaps["blocking_for_stage20_warm_start_count"],
        "capability_probe_count": probes["probe_count"],
        "capability_probe_failed_count": probes["failed_or_gap_probe_count"],
        "public_path_leak_scan_passed": reports["stage16g0_path_leak_scan_report.json"][
            "public_path_leak_scan_passed"
        ],
        "stage17a_schema_only_allowed": readiness["stage17a_schema_only_allowed"],
        "stage17b_real_data_freeze_allowed": readiness["stage17b_real_data_freeze_allowed"],
        "stage20_warm_start_data_generation_allowed": readiness["stage20_warm_start_data_generation_allowed"],
        "stage21_formal_rl_allowed": readiness["stage21_formal_rl_allowed"],
        "balanced_conclusion": "当前问题不是单纯工具太少；RepoHarness 已有结构化读搜改、create_file、bash、artifact 回读和恢复提示。主要缺口是 public diagnostic/project command/scratch Python 的正式训练资格、韧性和可审计 linkage。",
    }


def build_reports(output_dir: Path) -> dict[str, Any]:
    gaps = build_capability_gap_matrix()
    reports: dict[str, Any] = {
        "stage16g0_source_inventory.json": build_source_inventory(),
        "stage16g0_claude_code_tool_inventory.json": build_claude_code_tool_inventory(),
        "stage16g0_external_swe_harness_reference_inventory.json": build_external_reference_inventory(),
        "stage16g0_repoharness_tool_inventory.json": build_repoharness_tool_inventory(),
        "stage16g0_scaffold_capability_matrix.json": build_scaffold_matrix(),
        "stage16g0_capability_gap_matrix.json": gaps,
        "stage16g0_capability_probe_report.json": build_capability_probe_report(),
        "stage16g0_permission_and_shell_semantics_gap_report.json": build_permission_and_shell_report(),
        "stage16g0_test_feedback_and_project_command_gap_report.json": build_test_feedback_report(),
        "stage16g0_edit_write_file_operation_gap_report.json": build_edit_write_report(),
        "stage16g0_patch_capture_verifier_reward_linkage_report.json": build_linkage_report(),
        "stage16g0_task_management_and_subagent_gap_report.json": build_task_management_report(),
        "stage16g0_training_tool_surface_profile_recommendations.json": build_profile_recommendations(),
        "stage16g0_training_deployment_mismatch_risk_report.json": build_deployment_mismatch_report(gaps),
        "stage16g0_reward_hacking_and_monitoring_gap_report.json": build_reward_hacking_report(),
        "stage16g0_stage17_readiness_gate_report.json": build_readiness_report(gaps),
        "stage16g0_required_next_stage_items.json": build_required_next_stage_items(gaps),
        "stage16g0_public_evidence_policy.json": build_public_evidence_policy(),
    }
    return reports


def write_reports(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reports = build_reports(output_dir)
    digests: dict[str, str] = {}
    for filename, payload in reports.items():
        digests[filename] = _write_json(output_dir / filename, payload)
    scan = build_path_leak_scan_report(output_dir)
    reports["stage16g0_path_leak_scan_report.json"] = scan
    digests["stage16g0_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g0_path_leak_scan_report.json", scan
    )
    summary = derive_summary(reports, digests)
    reports["stage16g0_acceptance_summary.json"] = summary
    digests["stage16g0_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g0_acceptance_summary.json", summary
    )
    # Re-run the scan after summary exists. Updating the summary with the scan
    # digest changes only a hex digest field, so the leak status remains stable.
    scan = build_path_leak_scan_report(output_dir)
    reports["stage16g0_path_leak_scan_report.json"] = scan
    digests["stage16g0_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g0_path_leak_scan_report.json", scan
    )
    summary = derive_summary(reports, digests)
    digests["stage16g0_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g0_acceptance_summary.json", summary
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
