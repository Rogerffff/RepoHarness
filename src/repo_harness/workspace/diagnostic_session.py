"""Persistent diagnostic session helpers for Stage 16B.

This module keeps the high-permission diagnostic shell separate from the
Stage 16A execute_bash policy surface.  The shell runs against a public
workspace projection that excludes git metadata and runtime-private files,
then synchronizes only model-visible workspace changes back to the agent
workspace.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_harness.errors import WorkspaceError
from repo_harness.tasks.command_policy import _command_mutates_dependency_environment

MODEL_HIDDEN_PROJECTION_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".env",
        ".env.local",
        ".repo_harness_env_overlay",
        ".repo_harness_runtime",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".cache",
        ".tox",
        ".venv",
        ".aws",
        ".ssh",
        ".gnupg",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "__pycache__",
        "cache",
        "node_modules",
        "scratch",
        "temp",
        "tmp",
        "runtime_private",
        "official_selector",
        "official_verifier",
        "hidden_verifier",
        "evaluator_only",
        "fail_to_pass",
        "pass_to_pass",
        "accepted_label",
        "reward_metadata",
        "reward_extra_info",
        "ground_truth",
        "repo-harness-run",
        "credentials",
        "credentials.json",
        "secret",
        "secret.json",
        "secret.txt",
        "secrets.json",
        "token",
        "token.json",
        "token.txt",
    }
)

MODEL_HIDDEN_PROJECTION_SUFFIXES = frozenset(
    {".pem", ".key", ".p12", ".pfx", ".crt", ".cer", ".pyc"}
)

BACKGROUND_SHELL_MARKERS = (
    "nohup",
    "disown",
    "setsid",
    "tmux",
    "screen",
    "daemon",
    "coproc",
)

DEPENDENCY_MUTATION_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bpip(?:\d+(?:\.\d+)*)?\s+(?:install|uninstall|download|wheel)\b",
        r"\bpip\s+cache\s+(?:purge|remove)\b",
        r"\bpython(?:\d+(?:\.\d+)*)?\s+-m\s+pip\b.*\b(?:install|uninstall|download|wheel)\b",
        r"\buv\b.*\b(?:add|sync)\b",
        r"\buv\s+pip\b.*\b(?:install|uninstall|compile)\b",
        r"\buv\s+tool\s+(?:run|install|upgrade|uninstall)\b",
        r"\buv\s+run\b.*\b--with(?:=| |-)",
        r"\b(?:poetry|pipenv|pipx|pdm|rye|pixi|npm|pnpm|yarn|bun|bunx|conda|mamba|micromamba|gem|bundle|composer|pear|cpan)\b.*\b(?:add|install|uninstall|update|remove|sync|run|test|exec|x|dlx|create|pack|inject|require)\b",
        r"\b(?:apt|apt-get|brew|apk|yum|dnf|zypper|pacman|cargo|go|rustup|nvm|asdf|pyenv|rbenv|virtualenv)\b.*\b(?:add|install|update|remove|fetch|get|run|create)\b",
    )
)

HIDDEN_COMMAND_PATH_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"(^|[\s'\";:&|<>])\.git(/|[\s'\";:&|<>]|$)",
        r"(^|[\s'\";:&|<>])\.env(?:\.[A-Za-z0-9_.-]+)?(/|[\s'\";:&|<>]|$)",
        r"(^|[\s'\";:&|<>])runtime_private(/|[\s'\";:&|<>]|$)",
        r"(^|[\s'\";:&|<>])\.repo_harness_runtime(/|[\s'\";:&|<>]|$)",
        r"(^|[\s'\";:&|<>])\.repo_harness_env_overlay(/|[\s'\";:&|<>]|$)",
        r"(^|[\s'\";:&|<>])repo-harness-run(/|[\s'\";:&|<>]|$)",
    )
)


@dataclass(frozen=True)
class DiagnosticSessionPaths:
    session_id: str
    session_root: Path
    projection_workspace: Path
    home_dir: Path
    tmp_dir: Path
    pip_cache_dir: Path
    uv_cache_dir: Path


@dataclass
class DiagnosticSessionFacts:
    schema_version: str = "repo_harness_stage16b_diagnostic_session_facts_v0"
    tool_surface_profile: str = "persistent_diagnostic_session"
    diagnostic_session_backend: str = "local_filesystem_persistent"
    diagnostic_session_persistent: bool = True
    run_dir_mount_enabled: bool = False
    diagnostic_session_cleanup_status: str = "not_started"
    session_invalidated: bool = False
    background_process_cleanup_status: str = "completed"
    workspace_projection_sync_status: str = "not_started"
    workspace_projection_sync_passed: bool = False
    diagnostic_temp_artifact_excluded_from_final_patch: bool = True
    shared_dependency_environment_written: bool = False
    dependency_mutation_allowed: bool = False
    dependency_mutation_scope: str = "unsupported_in_stage16b"
    symlink_escape_blocked: bool = False
    local_backend_filesystem_isolation_verified: bool = False
    shared_dependency_environment_roots_present: bool = False
    hidden_evaluator_guard_passed: bool = True
    hidden_evaluator_guard_reason: str | None = None
    invalidation_reason: str | None = None
    reused: bool = False
    session_state_root_ref: str = "runtime_private_diagnostic_session"
    diagnostic_session_execution_shell: str = "bash"
    diagnostic_session_execution_argv_digest: str | None = None
    diagnostic_session_shell_semantics_version: str = "stage16f1_bash_lc_v0"
    diagnostic_session_shell_login_mode: str = "login"
    diagnostic_session_shell_interactive_mode: str = "non_interactive"
    diagnostic_session_shell_startup_policy: str = "recorded"
    diagnostic_session_shell_home_policy: str = "session_home"
    diagnostic_session_shell_bash_env_policy: str = "cleared"
    diagnostic_session_shell_env_policy: str = "cleared"
    diagnostics: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_surface_profile": self.tool_surface_profile,
            "diagnostic_session_backend": self.diagnostic_session_backend,
            "diagnostic_session_persistent": self.diagnostic_session_persistent,
            "run_dir_mount_enabled": self.run_dir_mount_enabled,
            "diagnostic_session_cleanup_status": self.diagnostic_session_cleanup_status,
            "session_invalidated": self.session_invalidated,
            "background_process_cleanup_status": self.background_process_cleanup_status,
            "workspace_projection_sync_status": self.workspace_projection_sync_status,
            "workspace_projection_sync_passed": self.workspace_projection_sync_passed,
            "diagnostic_temp_artifact_excluded_from_final_patch": self.diagnostic_temp_artifact_excluded_from_final_patch,
            "shared_dependency_environment_written": self.shared_dependency_environment_written,
            "dependency_mutation_allowed": self.dependency_mutation_allowed,
            "dependency_mutation_scope": self.dependency_mutation_scope,
            "symlink_escape_blocked": self.symlink_escape_blocked,
            "local_backend_filesystem_isolation_verified": self.local_backend_filesystem_isolation_verified,
            "shared_dependency_environment_roots_present": self.shared_dependency_environment_roots_present,
            "hidden_evaluator_guard_passed": self.hidden_evaluator_guard_passed,
            "hidden_evaluator_guard_reason": self.hidden_evaluator_guard_reason,
            "invalidation_reason": self.invalidation_reason,
            "reused": self.reused,
            "session_state_root_ref": self.session_state_root_ref,
            "diagnostic_session_execution_shell": self.diagnostic_session_execution_shell,
            "diagnostic_session_execution_argv_digest": self.diagnostic_session_execution_argv_digest,
            "diagnostic_session_shell_semantics_version": self.diagnostic_session_shell_semantics_version,
            "diagnostic_session_shell_login_mode": self.diagnostic_session_shell_login_mode,
            "diagnostic_session_shell_interactive_mode": self.diagnostic_session_shell_interactive_mode,
            "diagnostic_session_shell_startup_policy": self.diagnostic_session_shell_startup_policy,
            "diagnostic_session_shell_home_policy": self.diagnostic_session_shell_home_policy,
            "diagnostic_session_shell_bash_env_policy": self.diagnostic_session_shell_bash_env_policy,
            "diagnostic_session_shell_env_policy": self.diagnostic_session_shell_env_policy,
            "diagnostics": list(self.diagnostics),
        }


def diagnostic_shell_argv_digest(argv: list[str]) -> str:
    payload = json.dumps(argv, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_diagnostic_session_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip(".-")
    return safe[:96] or "diagnostic-session"


def diagnostic_session_paths(
    run_dir: Path,
    session_id: str,
    *,
    external_root: Path | None = None,
) -> DiagnosticSessionPaths:
    safe_id = safe_diagnostic_session_id(session_id)
    root_base = external_root if external_root is not None else run_dir / "diagnostic_sessions"
    root = root_base / safe_id
    return DiagnosticSessionPaths(
        session_id=safe_id,
        session_root=root,
        projection_workspace=root / "workspace",
        home_dir=root / "home",
        tmp_dir=root / "tmp",
        pip_cache_dir=root / "cache" / "pip",
        uv_cache_dir=root / "cache" / "uv",
    )


def prepare_diagnostic_projection(source_workspace: Path, projection_workspace: Path) -> None:
    source = source_workspace.resolve()
    projection = projection_workspace.resolve(strict=False)
    if projection.exists():
        purge_model_hidden_projection_paths(projection)
        sync_projection_to_workspace(source, projection, purge_hidden_source=False)
        purge_model_hidden_projection_paths(projection)
        return
    projection.parent.mkdir(parents=True, exist_ok=True)
    projection.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(source):
        root_path = Path(root)
        rel_root = root_path.relative_to(source)
        dirs[:] = [
            name
            for name in dirs
            if not is_model_hidden_projection_path(rel_root / name)
            and not _is_symlink_escape(source, root_path / name)
        ]
        target_root = projection / rel_root
        target_root.mkdir(parents=True, exist_ok=True)
        for name in files:
            rel = rel_root / name
            if is_model_hidden_projection_path(rel):
                continue
            source_file = root_path / name
            if _is_symlink_escape(source, source_file):
                continue
            target = target_root / name
            if source_file.is_symlink():
                link_target = os.readlink(source_file)
                target.symlink_to(link_target)
            else:
                shutil.copy2(source_file, target)


def sync_projection_to_workspace(
    projection_workspace: Path,
    target_workspace: Path,
    *,
    purge_hidden_source: bool = True,
) -> DiagnosticSessionFacts:
    facts = DiagnosticSessionFacts(
        workspace_projection_sync_status="completed",
        workspace_projection_sync_passed=True,
    )
    projection = projection_workspace.resolve()
    target_root = target_workspace.resolve()
    if not projection.exists():
        facts.workspace_projection_sync_status = "failed"
        facts.workspace_projection_sync_passed = False
        facts.diagnostics.append("diagnostic_projection_missing")
        return facts
    purged_hidden_paths = purge_model_hidden_projection_paths(projection) if purge_hidden_source else []
    if purged_hidden_paths:
        facts.workspace_projection_sync_status = "failed"
        facts.workspace_projection_sync_passed = False
        facts.diagnostics.extend(
            f"hidden_projection_path_purged:{path}" for path in purged_hidden_paths
        )
    if _has_symlink_escape(projection):
        facts.symlink_escape_blocked = True
        facts.diagnostics.append("symlink_escape_blocked")

    projection_public_files = set(_iter_public_files(projection))
    target_public_files = set(_iter_public_files(target_root))
    for rel in sorted(target_public_files - projection_public_files):
        target = target_root / rel
        if target.exists() or target.is_symlink():
            target.unlink()
    for rel in sorted(projection_public_files):
        src = projection / rel
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            resolved = src.resolve(strict=False)
            try:
                target_rel = resolved.relative_to(projection)
            except ValueError:
                facts.symlink_escape_blocked = True
                facts.diagnostics.append(f"symlink_escape_blocked:{rel.as_posix()}")
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                continue
            if is_model_hidden_projection_path(target_rel):
                facts.symlink_escape_blocked = True
                facts.diagnostics.append(f"symlink_hidden_target_blocked:{rel.as_posix()}")
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                continue
            link_target = os.readlink(src)
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.symlink_to(link_target)
        else:
            if not src.is_file():
                facts.workspace_projection_sync_status = "failed"
                facts.workspace_projection_sync_passed = False
                facts.diagnostics.append(f"non_regular_file_blocked:{rel.as_posix()}")
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                continue
            _ensure_safe_destination_parent(target_root, dst)
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            try:
                shutil.copy2(src, dst)
            except (OSError, shutil.SpecialFileError) as exc:
                facts.workspace_projection_sync_status = "failed"
                facts.workspace_projection_sync_passed = False
                facts.diagnostics.append(f"non_regular_file_copy_failed:{rel.as_posix()}:{type(exc).__name__}")
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
    return facts


def ensure_diagnostic_session_dirs(paths: DiagnosticSessionPaths) -> None:
    for directory in (
        paths.session_root,
        paths.projection_workspace,
        paths.home_dir,
        paths.tmp_dir,
        paths.pip_cache_dir,
        paths.uv_cache_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def diagnostic_command_policy_issue(command: str) -> str | None:
    if _diagnostic_dependency_mutation_requested(command):
        return "dependency_mutation_unsupported_in_stage16b"
    if _diagnostic_hidden_path_requested(command):
        return "diagnostic_shell_hidden_projection_path_denied"
    if _has_unquoted_background_operator(command):
        return "diagnostic_shell_background_execution_denied"
    if ".." in command:
        return "diagnostic_shell_parent_path_denied"
    if "/repo-harness-run" in command:
        return "diagnostic_shell_run_directory_path_denied"
    normalized = _normalized_words(command)
    for marker in BACKGROUND_SHELL_MARKERS:
        if marker in normalized:
            return f"diagnostic_shell_background_process_entry_denied:{marker}"
    if " jobs " in normalized or normalized.startswith("jobs ") or normalized.endswith(" jobs"):
        return "diagnostic_shell_job_control_denied"
    if " bg " in normalized or normalized.startswith("bg ") or normalized.endswith(" bg"):
        return "diagnostic_shell_job_control_denied"
    if " fg " in normalized or normalized.startswith("fg ") or normalized.endswith(" fg"):
        return "diagnostic_shell_job_control_denied"
    for marker in (
        "subprocess",
        "popen",
        "start_new_session",
        "devnull",
        "os.system",
        "spawn",
        "spawnlp",
        "spawnl",
        "spawnv",
        "spawnve",
        "fork",
    ):
        if marker in normalized:
            return f"diagnostic_shell_background_process_entry_denied:{marker}"
    return None


def _diagnostic_dependency_mutation_requested(command: str) -> bool:
    if _command_mutates_dependency_environment(command):
        return True
    normalized = _normalized_words(command)
    return any(pattern.search(normalized) for pattern in DEPENDENCY_MUTATION_PATTERNS)


def _diagnostic_hidden_path_requested(command: str) -> bool:
    return any(pattern.search(command) for pattern in HIDDEN_COMMAND_PATH_PATTERNS)


def diagnostic_command_environment(
    base_env: dict[str, str],
    paths: DiagnosticSessionPaths,
) -> dict[str, str]:
    env = dict(base_env)
    env.update(
        {
            "HOME": paths.home_dir.as_posix(),
            "TMPDIR": paths.tmp_dir.as_posix(),
            "TEMP": paths.tmp_dir.as_posix(),
            "TMP": paths.tmp_dir.as_posix(),
            "PIP_CACHE_DIR": paths.pip_cache_dir.as_posix(),
            "UV_CACHE_DIR": paths.uv_cache_dir.as_posix(),
            "PYTHONPYCACHEPREFIX": (paths.tmp_dir / "pycache").as_posix(),
            "BASH_ENV": "",
            "ENV": "",
        }
    )
    return env


def redact_diagnostic_output(text: str, *, run_dir: Path, workspace: Path, paths: DiagnosticSessionPaths) -> str:
    replacements = {
        paths.projection_workspace.as_posix(): "[repo_harness_diagnostic_workspace]",
        paths.session_root.as_posix(): "[repo_harness_diagnostic_session]",
        paths.home_dir.as_posix(): "[repo_harness_diagnostic_home]",
        paths.tmp_dir.as_posix(): "[repo_harness_diagnostic_tmp]",
        run_dir.as_posix(): "[repo_harness_run_dir]",
        workspace.as_posix(): "[repo_harness_workspace_path]",
    }
    redacted = text
    for raw, marker in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        redacted = redacted.replace(raw, marker)
    return redacted


def resolve_projection_cwd(paths: DiagnosticSessionPaths, cwd: str) -> Path:
    raw = Path(cwd)
    if raw.is_absolute():
        raise WorkspaceError("diagnostic_shell cwd must be workspace-relative.")
    if ".." in raw.parts:
        raise WorkspaceError("diagnostic_shell cwd must not contain '..'.")
    candidate = (paths.projection_workspace / raw).resolve(strict=False)
    try:
        candidate.relative_to(paths.projection_workspace.resolve())
    except ValueError as exc:
        raise WorkspaceError("diagnostic_shell cwd resolves outside diagnostic workspace projection.") from exc
    if not candidate.exists() or not candidate.is_dir():
        raise WorkspaceError("diagnostic_shell cwd does not exist inside diagnostic workspace projection.")
    return candidate


def is_model_hidden_projection_path(relative_path: Path) -> bool:
    parts = relative_path.parts
    if not parts:
        return False
    for part in parts:
        normalized = part.lower()
        compact = normalized.replace("-", "").replace("_", "")
        if normalized in MODEL_HIDDEN_PROJECTION_NAMES:
            return True
        if normalized.startswith(".") and normalized not in {".", ".."}:
            return True
        if compact in {
            "runtimeprivate",
            "repoharnessrun",
            "repoharnessruntime",
            "repoharnessenvoverlay",
            "hiddenverifier",
            "officialselector",
            "officialverifier",
            "evaluatoronly",
            "failtopass",
            "passtopass",
            "acceptedlabel",
            "goldpatch",
            "testpatch",
            "rewardmetadata",
            "rewardextrainfo",
            "groundtruth",
            "providersecret",
        }:
            return True
    return relative_path.name.lower().endswith(tuple(MODEL_HIDDEN_PROJECTION_SUFFIXES))


def _iter_public_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        rel_root = current_path.relative_to(root)
        dirs[:] = [
            name
            for name in dirs
            if not is_model_hidden_projection_path(rel_root / name)
            and not _is_symlink_escape(root, current_path / name)
        ]
        for name in names:
            rel = rel_root / name
            if is_model_hidden_projection_path(rel):
                continue
            source = current_path / name
            if _is_symlink_escape(root, source):
                files.append(rel)
                continue
            files.append(rel)
    return files


def _is_symlink_escape(root: Path, path: Path) -> bool:
    if not path.is_symlink():
        return False
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return True
    return False


def _has_symlink_escape(root: Path) -> bool:
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        for name in [*dirs, *files]:
            if _is_symlink_escape(root, current_path / name):
                return True
    return False


def purge_model_hidden_projection_paths(root: Path) -> list[str]:
    purged: list[str] = []
    if not root.exists():
        return purged
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if not is_model_hidden_projection_path(relative):
            continue
        if not path.exists() and not path.is_symlink():
            continue
        purged.append(relative.as_posix())
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    return purged


def _ensure_safe_destination_parent(root: Path, destination: Path) -> None:
    root_resolved = root.resolve()
    relative_parent = destination.parent.relative_to(root)
    current = root
    for part in relative_parent.parts:
        current = current / part
        if current.is_symlink():
            current.unlink()
        current.mkdir(exist_ok=True)
        try:
            current.resolve().relative_to(root_resolved)
        except ValueError as exc:
            raise WorkspaceError(f"diagnostic projection sync destination escapes workspace: {destination}") from exc


def _has_unquoted_background_operator(command: str) -> bool:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(command):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == "&":
            previous_char = command[index - 1] if index > 0 else ""
            next_char = command[index + 1] if index + 1 < len(command) else ""
            if previous_char == "&" or next_char == "&" or next_char == ">":
                continue
            return True
    return False


def _normalized_words(command: str) -> str:
    return " " + re.sub(r"[^a-zA-Z0-9_.-]+", " ", command.lower()).strip() + " "


def default_local_diagnostic_session_root(run_id: str) -> Path:
    return Path(tempfile.gettempdir()) / "repo_harness_diagnostic_sessions" / safe_diagnostic_session_id(run_id)
