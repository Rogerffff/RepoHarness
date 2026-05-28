"""Structured Stage 16G.2 file mutation service."""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from repo_harness.errors import WorkspaceError

STAGE16G2_PATH_MAX_CHARS = 1024
STAGE16G2_PATH_SEGMENT_MAX_CHARS = 255
STAGE16G2_CONTENT_MAX_BYTES = 1024 * 1024
STAGE16G2_APPLY_PATCH_TOTAL_WRITE_MAX_BYTES = 2 * 1024 * 1024
STAGE16G2_REASON_MAX_CHARS = 2000
STAGE16G2_MUTATION_POLICY_VERSION = "repo_harness_stage16g2b_file_mutation_v0"

_FORBIDDEN_PATH_PARTS = frozenset(
    {
        ".aws",
        ".cache",
        ".config",
        ".env",
        ".git",
        ".gnupg",
        ".hg",
        ".mypy_cache",
        ".netrc",
        ".npmrc",
        ".pip",
        ".pre_verl_venv",
        ".pypirc",
        ".pytest_cache",
        ".repo_harness_env_overlay",
        ".repo_harness_runtime",
        ".ruff_cache",
        ".ssh",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "credentials",
        "dist",
        "node_modules",
        "runtime_private",
        "secret",
        "secrets",
        "token",
        "venv",
    }
)
_FORBIDDEN_SUFFIXES = frozenset({".cer", ".crt", ".key", ".p12", ".pem", ".pfx"})
_SENSITIVE_PATH_MARKERS = frozenset(
    {
        "failtopass",
        "finalverifier",
        "goldpatch",
        "groundtruth",
        "hiddenfeedback",
        "hiddentestpatch",
        "hiddentestselector",
        "hiddenverifier",
        "officialverifier",
        "passtopass",
        "providersecret",
        "rewardextrainfo",
        "rewardmetadata",
        "testpatch",
    }
)
_RUNTIME_PRIVATE_PATH_MARKERS = frozenset(
    {
        "repoharnessenvoverlay",
        "repoharnessrun",
        "repoharnessruntime",
        "repoharnesstmp",
        "runtimeprivate",
    }
)


@dataclass(frozen=True)
class FileMutationDenial(Exception):
    reason_code: str
    message: str
    retryable: bool = True
    path: str | None = None
    safe_alternative_tool: str | None = None
    safe_rewrite_example: str | None = None
    operation_id: str | None = None


@dataclass(frozen=True)
class PreparedFileMutation:
    operation_id: str
    op: str
    path: str | None = None
    source_path: str | None = None
    target_path: str | None = None
    resolved_path: Path | None = None
    resolved_source_path: Path | None = None
    resolved_target_path: Path | None = None
    content: str | None = None
    old_text: str | None = None
    new_text: str | None = None
    mode: str | None = None
    reason: str | None = None
    previous_content_hash: str | None = None
    content_hash: str | None = None
    replacement_count: int | None = None
    result_kind: str = "mutation_prepared"
    repository_mutation_performed: bool = True
    touched_paths: tuple[Path, ...] = ()
    cache_updates: dict[str, str] = field(default_factory=dict)
    cache_removals: tuple[str, ...] = ()

    def fact(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation_id": self.operation_id,
            "op": self.op,
            "path": self.path,
            "source_path": self.source_path,
            "target_path": self.target_path,
            "mode": self.mode,
            "reason": self.reason,
            "previous_content_hash": self.previous_content_hash,
            "content_hash": self.content_hash,
            "replacement_count": self.replacement_count,
            "result_kind": self.result_kind,
            "repository_mutation_performed": self.repository_mutation_performed,
        }
        return {key: value for key, value in payload.items() if value is not None}


@dataclass(frozen=True)
class FileMutationOutcome:
    tool_name: str
    result_kind: str
    operation_facts: list[dict[str, Any]]
    changed_paths: list[str]
    cache_updates: dict[str, str]
    cache_removals: list[str]
    repository_mutation_performed: bool
    partial_failure: bool = False
    rollback_attempted: bool = False
    rollback_status: str = "not_needed"
    invalid_for_training: bool = False
    policy_loss_candidate: bool = False
    official_prediction_eligible: bool = False
    training_export_eligible: bool = False
    diagnostic_side_channel_only: bool = False

    def audit_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "stage16g2b.file_mutation_audit.v1",
            "policy_version": STAGE16G2_MUTATION_POLICY_VERSION,
            "tool_name": self.tool_name,
            "result_kind": self.result_kind,
            "operation_count": len(self.operation_facts),
            "operation_facts": self.operation_facts,
            "changed_paths": self.changed_paths,
            "repository_mutation_performed": self.repository_mutation_performed,
            "partial_failure": self.partial_failure,
            "rollback_attempted": self.rollback_attempted,
            "rollback_status": self.rollback_status,
            "invalid_for_training": self.invalid_for_training,
            "policy_loss_candidate": self.policy_loss_candidate,
            "official_prediction_eligible": self.official_prediction_eligible,
            "training_export_eligible": self.training_export_eligible,
            "diagnostic_side_channel_only": self.diagnostic_side_channel_only,
        }


def execute_structured_file_mutation(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    context: Any,
) -> FileMutationOutcome:
    operations = _normalize_operations(tool_name, arguments)
    prepared = _prepare_operations(operations, context)
    snapshot_paths = _snapshot_paths(prepared, context)
    snapshots = {path: _snapshot_path(path) for path in snapshot_paths}
    applied_ids: list[str] = []
    try:
        for mutation in prepared:
            _apply_prepared_operation(mutation)
            applied_ids.append(mutation.operation_id)
    except Exception as exc:  # noqa: BLE001 - rollback facts must survive runtime failures.
        rollback_status = _rollback_snapshots(snapshots)
        operation_facts = [mutation.fact() for mutation in prepared]
        operation_facts.append(
            {
                "result_kind": "runtime_apply_failed",
                "applied_operation_ids": applied_ids,
                "failed_error_type": type(exc).__name__,
            }
        )
        return FileMutationOutcome(
            tool_name=tool_name,
            result_kind="partial_failure",
            operation_facts=operation_facts,
            changed_paths=sorted(_relative_touched_paths(prepared)),
            cache_updates={},
            cache_removals=[],
            repository_mutation_performed=bool(applied_ids),
            partial_failure=True,
            rollback_attempted=True,
            rollback_status=rollback_status,
            invalid_for_training=True,
            policy_loss_candidate=False,
            official_prediction_eligible=False,
            training_export_eligible=False,
            diagnostic_side_channel_only=True,
        )
    cache_updates: dict[str, str] = {}
    cache_removals: list[str] = []
    for mutation in prepared:
        cache_updates.update(mutation.cache_updates)
        cache_removals.extend(mutation.cache_removals)
    return FileMutationOutcome(
        tool_name=tool_name,
        result_kind="file_mutation_applied",
        operation_facts=[mutation.fact() for mutation in prepared],
        changed_paths=sorted(_relative_touched_paths(prepared)),
        cache_updates=cache_updates,
        cache_removals=sorted(set(cache_removals)),
        repository_mutation_performed=any(mutation.repository_mutation_performed for mutation in prepared),
        policy_loss_candidate=False,
        official_prediction_eligible=False,
        training_export_eligible=False,
    )


def _normalize_operations(tool_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    if tool_name == "apply_patch":
        return [dict(operation) for operation in arguments["operations"]]
    if tool_name == "write_file":
        return [
            {
                "op": "write_file",
                "path": arguments["path"],
                "content": arguments["content"],
                "mode": arguments["mode"],
                **({"expected_content_hash": arguments["expected_content_hash"]} if "expected_content_hash" in arguments else {}),
            }
        ]
    if tool_name == "delete_file":
        return [
            {
                "op": "delete_file",
                "path": arguments["path"],
                "expected_content_hash": arguments["expected_content_hash"],
                "reason": arguments["reason"],
            }
        ]
    if tool_name == "move_file":
        return [
            {
                "op": "move_file",
                "source_path": arguments["source_path"],
                "target_path": arguments["target_path"],
                "expected_source_hash": arguments["expected_source_hash"],
                "reason": arguments["reason"],
            }
        ]
    if tool_name == "mkdir":
        return [{"op": "mkdir", "path": arguments["path"]}]
    raise FileMutationDenial(
        reason_code="unsupported_file_mutation_tool",
        message=f"{tool_name} is not a Stage 16G.2B file mutation tool.",
        retryable=False,
    )


def _prepare_operations(operations: list[dict[str, Any]], context: Any) -> list[PreparedFileMutation]:
    total_write_bytes = 0
    prepared: list[PreparedFileMutation] = []
    touched: set[Path] = set()
    for index, operation in enumerate(operations):
        op_name = str(operation["op"])
        operation_id = f"op_{index:03d}"
        mutation = _prepare_operation(operation_id, op_name, operation, context)
        total_write_bytes += _operation_write_bytes(mutation)
        if total_write_bytes > STAGE16G2_APPLY_PATCH_TOTAL_WRITE_MAX_BYTES:
            raise FileMutationDenial(
                reason_code="patch_too_large",
                message="apply_patch total write payload is larger than the Stage 16G.2B safety limit.",
                retryable=True,
                operation_id=operation_id,
                safe_alternative_tool="apply_patch",
                safe_rewrite_example="Split the change into smaller structured apply_patch calls.",
            )
        for path in mutation.touched_paths:
            if path in touched:
                raise FileMutationDenial(
                    reason_code="duplicate_mutation_path",
                    message="Stage 16G.2B rejects multiple operations touching the same path in one apply_patch call.",
                    retryable=True,
                    operation_id=operation_id,
                    safe_alternative_tool="write_file",
                    safe_rewrite_example="Use one write_file overwrite for a large same-file rewrite, or split the patch.",
                )
            touched.add(path)
        prepared.append(mutation)
    return prepared


def _prepare_operation(
    operation_id: str,
    op_name: str,
    operation: dict[str, Any],
    context: Any,
) -> PreparedFileMutation:
    if op_name == "replace_text":
        return _prepare_replace_text(operation_id, operation, context)
    if op_name == "write_file":
        return _prepare_write_file(operation_id, operation, context)
    if op_name == "delete_file":
        return _prepare_delete_file(operation_id, operation, context)
    if op_name == "move_file":
        return _prepare_move_file(operation_id, operation, context)
    if op_name == "mkdir":
        return _prepare_mkdir(operation_id, operation, context)
    raise FileMutationDenial(
        reason_code="unsupported_apply_patch_operation",
        message=f"Unsupported apply_patch operation: {op_name}",
        operation_id=operation_id,
    )


def _prepare_replace_text(operation_id: str, operation: dict[str, Any], context: Any) -> PreparedFileMutation:
    path = _normalize_relative_path(operation["path"])
    resolved = _resolve_workspace_path(context, path, must_exist=True)
    content = _read_existing_utf8_file(resolved, path, operation_id=operation_id)
    current_hash = _sha256_text(content)
    expected_hash = operation["expected_content_hash"]
    if expected_hash != current_hash:
        raise FileMutationDenial(
            reason_code="stale_file_state",
            message="expected_content_hash does not match current file content.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example=f"Call read_file(path={path!r}) and retry with the returned content_hash.",
        )
    old_text = operation["old_text"]
    if _looks_like_numbered_read_file_snippet(old_text):
        raise FileMutationDenial(
            reason_code="line_number_prefix_in_old_text",
            message="old_text appears to include read_file line-number prefixes.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example="Copy old_text from raw_content_preview, not numbered_content_preview.",
        )
    count = content.count(old_text)
    if count != 1:
        raise FileMutationDenial(
            reason_code="old_text_not_unique",
            message=f"old_text matched {count} times; Stage 16G.2B replace_text requires exactly one match.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example="Read a wider raw snippet and include enough context so old_text is unique.",
        )
    new_text = operation["new_text"]
    updated = content.replace(old_text, new_text, 1)
    updated_hash = _sha256_text(updated)
    return PreparedFileMutation(
        operation_id=operation_id,
        op="replace_text",
        path=path,
        resolved_path=resolved,
        old_text=old_text,
        new_text=new_text,
        content=updated,
        previous_content_hash=current_hash,
        content_hash=updated_hash,
        replacement_count=1,
        result_kind="text_replaced",
        touched_paths=(resolved,),
        cache_updates={path: updated_hash},
    )


def _prepare_write_file(operation_id: str, operation: dict[str, Any], context: Any) -> PreparedFileMutation:
    path = _normalize_relative_path(operation["path"])
    mode = operation["mode"]
    content = str(operation["content"])
    _validate_content_size(content, operation_id=operation_id, path=path)
    resolved = _resolve_workspace_path(context, path, must_exist=False)
    _deny_if_mutation_symlink(resolved, path, operation_id=operation_id)
    previous_hash: str | None = None
    if mode == "create":
        if resolved.exists():
            raise FileMutationDenial(
                reason_code="file_exists",
                message="write_file(mode='create') requires the target path to be absent.",
                path=path,
                operation_id=operation_id,
                safe_alternative_tool="write_file",
                safe_rewrite_example="Use mode='overwrite' with expected_content_hash after read_file if overwriting is intended.",
            )
        result_kind = "file_created"
    elif mode == "overwrite":
        existing = _read_existing_utf8_file(resolved, path, operation_id=operation_id)
        previous_hash = _sha256_text(existing)
        expected_hash = operation["expected_content_hash"]
        if expected_hash != previous_hash:
            raise FileMutationDenial(
                reason_code="stale_file_state",
                message="expected_content_hash does not match current file content.",
                path=path,
                operation_id=operation_id,
                safe_alternative_tool="read_file",
                safe_rewrite_example=f"Call read_file(path={path!r}) and retry with the returned content_hash.",
            )
        result_kind = "file_overwritten"
    else:
        raise FileMutationDenial(
            reason_code="unsupported_write_mode",
            message="write_file supports mode='create' or mode='overwrite'.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="write_file",
            safe_rewrite_example="Use mode='create' for new files or mode='overwrite' with expected_content_hash.",
        )
    content_hash = _sha256_text(content)
    return PreparedFileMutation(
        operation_id=operation_id,
        op="write_file",
        path=path,
        resolved_path=resolved,
        content=content,
        mode=mode,
        previous_content_hash=previous_hash,
        content_hash=content_hash,
        result_kind=result_kind,
        touched_paths=(resolved,),
        cache_updates={path: content_hash},
    )


def _prepare_delete_file(operation_id: str, operation: dict[str, Any], context: Any) -> PreparedFileMutation:
    path = _normalize_relative_path(operation["path"])
    resolved = _resolve_workspace_path(context, path, must_exist=True)
    content = _read_existing_utf8_file(resolved, path, operation_id=operation_id)
    current_hash = _sha256_text(content)
    expected_hash = operation["expected_content_hash"]
    if expected_hash != current_hash:
        raise FileMutationDenial(
            reason_code="stale_file_state",
            message="expected_content_hash does not match current file content.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example=f"Call read_file(path={path!r}) and retry with the returned content_hash.",
        )
    reason = _normalize_reason(operation["reason"], operation_id=operation_id)
    return PreparedFileMutation(
        operation_id=operation_id,
        op="delete_file",
        path=path,
        resolved_path=resolved,
        reason=reason,
        previous_content_hash=current_hash,
        result_kind="file_deleted",
        touched_paths=(resolved,),
        cache_removals=(path,),
    )


def _prepare_move_file(operation_id: str, operation: dict[str, Any], context: Any) -> PreparedFileMutation:
    source_path = _normalize_relative_path(operation["source_path"])
    target_path = _normalize_relative_path(operation["target_path"])
    if source_path == target_path:
        raise FileMutationDenial(
            reason_code="source_target_same_path",
            message="move_file requires different source_path and target_path.",
            path=source_path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example="Use read_file if no move is actually needed.",
        )
    source_resolved = _resolve_workspace_path(context, source_path, must_exist=True)
    target_resolved = _resolve_workspace_path(context, target_path, must_exist=False)
    _deny_if_mutation_symlink(target_resolved, target_path, operation_id=operation_id)
    content = _read_existing_utf8_file(source_resolved, source_path, operation_id=operation_id)
    current_hash = _sha256_text(content)
    expected_hash = operation["expected_source_hash"]
    if expected_hash != current_hash:
        raise FileMutationDenial(
            reason_code="stale_file_state",
            message="expected_source_hash does not match current source file content.",
            path=source_path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example=f"Call read_file(path={source_path!r}) and retry with the returned content_hash.",
        )
    if target_resolved.exists():
        raise FileMutationDenial(
            reason_code="target_exists",
            message="move_file refuses to overwrite an existing target path.",
            path=target_path,
            operation_id=operation_id,
            safe_alternative_tool="apply_patch",
            safe_rewrite_example="Move to a new target path, or explicitly delete the target first in a separate audited operation.",
        )
    reason = _normalize_reason(operation["reason"], operation_id=operation_id)
    return PreparedFileMutation(
        operation_id=operation_id,
        op="move_file",
        source_path=source_path,
        target_path=target_path,
        resolved_source_path=source_resolved,
        resolved_target_path=target_resolved,
        reason=reason,
        previous_content_hash=current_hash,
        content_hash=current_hash,
        result_kind="file_moved",
        touched_paths=(source_resolved, target_resolved),
        cache_updates={target_path: current_hash},
        cache_removals=(source_path,),
    )


def _prepare_mkdir(operation_id: str, operation: dict[str, Any], context: Any) -> PreparedFileMutation:
    path = _normalize_relative_path(operation["path"])
    resolved = _resolve_workspace_path(context, path, must_exist=False)
    _deny_if_mutation_symlink(resolved, path, operation_id=operation_id)
    if resolved.exists() and not resolved.is_dir():
        raise FileMutationDenial(
            reason_code="path_exists_not_directory",
            message="mkdir target exists but is not a directory.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="read_file",
            safe_rewrite_example="Inspect the existing path before deciding whether a directory is needed.",
        )
    return PreparedFileMutation(
        operation_id=operation_id,
        op="mkdir",
        path=path,
        resolved_path=resolved,
        result_kind="directory_created" if not resolved.exists() else "directory_already_exists",
        repository_mutation_performed=not resolved.exists(),
        touched_paths=(resolved,),
    )


def _apply_prepared_operation(mutation: PreparedFileMutation) -> None:
    if mutation.op in {"replace_text", "write_file"}:
        assert mutation.resolved_path is not None
        assert mutation.content is not None
        mutation.resolved_path.parent.mkdir(parents=True, exist_ok=True)
        mutation.resolved_path.write_text(mutation.content, encoding="utf-8")
        return
    if mutation.op == "delete_file":
        assert mutation.resolved_path is not None
        mutation.resolved_path.unlink()
        return
    if mutation.op == "move_file":
        assert mutation.resolved_source_path is not None
        assert mutation.resolved_target_path is not None
        mutation.resolved_target_path.parent.mkdir(parents=True, exist_ok=True)
        mutation.resolved_source_path.rename(mutation.resolved_target_path)
        return
    if mutation.op == "mkdir":
        assert mutation.resolved_path is not None
        mutation.resolved_path.mkdir(parents=True, exist_ok=True)
        return
    raise RuntimeError(f"unhandled file mutation op: {mutation.op}")


def _normalize_relative_path(value: Any) -> str:
    if not isinstance(value, str):
        raise FileMutationDenial("path_not_string", "Path must be a string.")
    raw = value.strip()
    if not raw:
        raise FileMutationDenial("path_empty", "Path must be a non-empty workspace-relative path.")
    if len(raw) > STAGE16G2_PATH_MAX_CHARS:
        raise FileMutationDenial("path_too_long", "Path is longer than the Stage 16G.2B limit.")
    if "\\" in raw:
        raise FileMutationDenial("path_separator_not_allowed", "Use POSIX-style '/' workspace-relative paths.")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or Path(raw).is_absolute():
        raise FileMutationDenial("absolute_path_denied", "Absolute paths are not allowed.")
    parts = pure.parts
    if any(part in {"", ".", ".."} for part in parts):
        raise FileMutationDenial("path_traversal_denied", "Path must not include empty, '.', or '..' segments.")
    for part in parts:
        lowered = part.lower()
        normalized_marker = _normalized_path_marker(part)
        if len(part) > STAGE16G2_PATH_SEGMENT_MAX_CHARS:
            raise FileMutationDenial("path_segment_too_long", "A path segment is longer than the Stage 16G.2B limit.")
        if (
            lowered in _FORBIDDEN_PATH_PARTS
            or Path(part).suffix.lower() in _FORBIDDEN_SUFFIXES
            or any(marker in normalized_marker for marker in _SENSITIVE_PATH_MARKERS)
            or any(marker in normalized_marker for marker in _RUNTIME_PRIVATE_PATH_MARKERS)
        ):
            raise FileMutationDenial("model_hidden_path_denied", "This path is hidden from model-visible file mutation tools.")
    return pure.as_posix()


def _normalized_path_marker(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _normalize_reason(value: Any, *, operation_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FileMutationDenial(
            reason_code="model_reason_required",
            message="delete_file and move_file operations require a non-empty model-provided reason.",
            operation_id=operation_id,
            safe_alternative_tool="apply_patch",
            safe_rewrite_example="Include reason explaining why this deletion or move is correct for the task.",
        )
    reason = value.strip()
    if len(reason) > STAGE16G2_REASON_MAX_CHARS:
        raise FileMutationDenial(
            reason_code="reason_too_long",
            message="The model-provided reason is longer than the Stage 16G.2B limit.",
            operation_id=operation_id,
            safe_alternative_tool="apply_patch",
            safe_rewrite_example="Provide a concise reason for the deletion or move.",
        )
    return reason


def _resolve_workspace_path(context: Any, rel_path: str, *, must_exist: bool) -> Path:
    candidate = Path(context.run_workspace.workspace_path) / rel_path
    if candidate.is_symlink():
        raise FileMutationDenial(
            reason_code="symlink_not_mutable",
            message="Structured file mutation tools reject symlink targets.",
            path=rel_path,
            retryable=False,
        )
    try:
        return context.workspace_adapter.resolve_workspace_path(
            context.run_workspace.workspace_path,
            rel_path,
            must_exist=must_exist,
        )
    except WorkspaceError as exc:
        raise FileMutationDenial(
            reason_code="workspace_path_denied",
            message=str(exc),
            retryable=True,
            path=rel_path,
            safe_alternative_tool="list_files",
            safe_rewrite_example="Use list_files or glob_files to find a workspace-relative public path.",
        ) from exc


def _read_existing_utf8_file(path: Path, rel_path: str, *, operation_id: str) -> str:
    _deny_if_mutation_symlink(path, rel_path, operation_id=operation_id)
    if not path.exists():
        raise FileMutationDenial(
            reason_code="file_not_found",
            message="Expected file does not exist.",
            path=rel_path,
            operation_id=operation_id,
            safe_alternative_tool="list_files",
            safe_rewrite_example="Use list_files or glob_files to confirm the path before mutating it.",
        )
    if not path.is_file():
        raise FileMutationDenial(
            reason_code="not_regular_file",
            message="Structured file mutation tools only operate on regular UTF-8 files.",
            path=rel_path,
            operation_id=operation_id,
            safe_alternative_tool="list_files",
            safe_rewrite_example="Use list_files to inspect the path type.",
        )
    data = path.read_bytes()
    if b"\0" in data:
        raise FileMutationDenial(
            reason_code="binary_file_denied",
            message="Structured file mutation tools reject binary files.",
            path=rel_path,
            operation_id=operation_id,
            retryable=False,
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FileMutationDenial(
            reason_code="non_utf8_file_denied",
            message="Structured file mutation tools only support UTF-8 text files.",
            path=rel_path,
            operation_id=operation_id,
            retryable=False,
        ) from exc


def _deny_if_mutation_symlink(path: Path, rel_path: str, *, operation_id: str) -> None:
    if path.is_symlink():
        raise FileMutationDenial(
            reason_code="symlink_not_mutable",
            message="Structured file mutation tools reject symlink targets.",
            path=rel_path,
            operation_id=operation_id,
            retryable=False,
        )


def _validate_content_size(content: str, *, operation_id: str, path: str) -> None:
    if len(content.encode("utf-8")) > STAGE16G2_CONTENT_MAX_BYTES:
        raise FileMutationDenial(
            reason_code="content_too_large",
            message="Content is larger than the Stage 16G.2B single-file write limit.",
            path=path,
            operation_id=operation_id,
            safe_alternative_tool="apply_patch",
            safe_rewrite_example="Split the change into smaller structured operations.",
        )


def _operation_write_bytes(mutation: PreparedFileMutation) -> int:
    if mutation.content is None:
        return 0
    return len(mutation.content.encode("utf-8"))


def _snapshot_paths(prepared: list[PreparedFileMutation], context: Any) -> set[Path]:
    root = Path(context.run_workspace.workspace_path).resolve(strict=False)
    paths: set[Path] = set()
    for mutation in prepared:
        for path in mutation.touched_paths:
            paths.add(path)
            current = path.parent
            while root in {current, *current.parents} and current != root:
                paths.add(current)
                current = current.parent
    return paths


def _snapshot_path(path: Path) -> dict[str, Any]:
    if path.exists() and path.is_file() and not path.is_symlink():
        return {"exists": True, "kind": "file", "bytes": path.read_bytes()}
    if path.exists() and path.is_dir() and not path.is_symlink():
        return {"exists": True, "kind": "dir"}
    if path.exists() and path.is_symlink():
        return {"exists": True, "kind": "symlink"}
    return {"exists": False, "kind": "absent"}


def _rollback_snapshots(snapshots: dict[Path, dict[str, Any]]) -> str:
    try:
        for path, snapshot in sorted(snapshots.items(), key=lambda item: len(item[0].parts), reverse=True):
            if snapshot["exists"] is False:
                if path.exists() or path.is_symlink():
                    if path.is_dir() and not path.is_symlink():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                continue
            if snapshot["kind"] == "file":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(snapshot["bytes"])
            elif snapshot["kind"] == "dir":
                path.mkdir(parents=True, exist_ok=True)
        return "clean"
    except Exception:  # noqa: BLE001 - rollback failure is reported as a training quarantine fact.
        return "failed"


def _relative_touched_paths(prepared: list[PreparedFileMutation]) -> set[str]:
    paths: set[str] = set()
    for mutation in prepared:
        if mutation.path is not None:
            paths.add(mutation.path)
        if mutation.source_path is not None:
            paths.add(mutation.source_path)
        if mutation.target_path is not None:
            paths.add(mutation.target_path)
    return paths


def _sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _looks_like_numbered_read_file_snippet(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    prefixed = sum(1 for line in lines[:5] if re.match(r"^\s*\d+\s*\|\s?", line))
    return prefixed >= max(1, min(len(lines[:5]), 2))
