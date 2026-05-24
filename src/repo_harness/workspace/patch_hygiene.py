"""Stage 16E final patch hygiene helpers.

The functions in this module operate on repository-relative patch paths and
return public-safe summaries. Raw patch contents remain runtime-private.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any, Literal


PATCH_HYGIENE_POLICY_VERSION = "repo_harness_stage16e_patch_hygiene_policy_v0"
PATCH_HYGIENE_REPORT_SCHEMA_VERSION = "repo_harness_stage16e_patch_hygiene_report_v0"

PatchHygieneAction = Literal["include", "exclude", "flag"]


@dataclass(frozen=True)
class PatchHygienePolicy:
    """Path-level rules for training-safe final patch projection."""

    policy_version: str = PATCH_HYGIENE_POLICY_VERSION
    root_hard_exclude_names: tuple[str, ...] = (
        "patch.txt",
        ".DS_Store",
    )
    hard_exclude_suffixes: tuple[str, ...] = (
        ".orig",
        ".rej",
        ".swp",
        ".swo",
        ".pyc",
        "~",
    )
    root_diagnostic_python_prefixes: tuple[str, ...] = (
        "debug_",
        "check_",
        "probe_",
        "tmp_",
        "new_format_",
        "diffbug",
        "repro",
        "reproduce",
    )
    root_diagnostic_suffixes: tuple[str, ...] = (
        ".dot",
        ".fit",
        ".fits",
        ".fits.gz",
    )
    hard_exclude_parts: tuple[str, ...] = (
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".repo_harness_tmp",
        ".repo_harness_runtime",
        ".repo_harness_env_overlay",
        "runtime_private",
        "repo-harness-run",
        "node_modules",
        ".venv",
    )
    root_hard_exclude_dirs: tuple[str, ...] = (
        "tmp",
        "temp",
    )
    hard_exclude_globs: tuple[str, ...] = (
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/.pytest_cache/**",
        "**/.mypy_cache/**",
        "**/.ruff_cache/**",
        "**/.venv/**",
        "**/venv/**",
        "**/*.egg-info/**",
    )
    flag_only_suffixes: tuple[str, ...] = (
        "requirements.txt",
        "requirements.lock",
        "poetry.lock",
        "Pipfile.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    )

    @classmethod
    def default_training_policy(cls) -> "PatchHygienePolicy":
        return cls()


@dataclass(frozen=True)
class StructuredDiffEntry:
    status: str
    paths: tuple[str, ...]

    def public_dict(self) -> dict[str, Any]:
        return {"status": self.status, "paths": list(self.paths)}


@dataclass(frozen=True)
class PathHygieneDecision:
    path: str
    action: PatchHygieneAction
    reason: str
    path_category: str
    public_path: str | None = None
    path_sha256: str | None = None
    basename_redacted: str | None = None

    def public_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": self.action,
            "reason": self.reason,
            "path_category": self.path_category,
        }
        if self.public_path is not None:
            payload["path"] = self.public_path
        else:
            payload["path_sha256"] = self.path_sha256 or _sha256_text(self.path)
            payload["basename_redacted"] = self.basename_redacted or _basename_redacted(self.path)
        return payload


@dataclass(frozen=True)
class PatchBlockDecision:
    action: PatchHygieneAction
    reason: str
    paths: tuple[str, ...]
    path_decisions: tuple[PathHygieneDecision, ...]


@dataclass(frozen=True)
class PatchHygieneFilterResult:
    raw_patch_text: str
    cleaned_patch_text: str
    decisions: tuple[PatchBlockDecision, ...]
    structured_diff_facts_status: str
    structured_diff_entries: tuple[StructuredDiffEntry, ...] = field(default_factory=tuple)

    @property
    def raw_patch_sha256(self) -> str:
        return _sha256_text(self.raw_patch_text)

    @property
    def cleaned_patch_sha256(self) -> str:
        return _sha256_text(self.cleaned_patch_text)

    @property
    def filtered_file_count(self) -> int:
        return len({item.path for decision in self.decisions if decision.action == "exclude" for item in decision.path_decisions})

    @property
    def flagged_file_count(self) -> int:
        return len({item.path for decision in self.decisions if decision.action == "flag" for item in decision.path_decisions})

    @property
    def only_filtered_changes(self) -> bool:
        return bool(self.raw_patch_text.strip()) and not self.cleaned_patch_text.strip() and self.filtered_file_count > 0


class PatchHygieneError(ValueError):
    """Raised when final patch hygiene cannot be computed safely."""


def parse_name_status_z(text: str) -> tuple[StructuredDiffEntry, ...]:
    """Parse `git diff --name-status -z` output.

    The function also accepts line-based output as a fallback for tests and
    older callers, but Stage 16E capture paths should provide the NUL-delimited
    form.
    """

    if not text:
        return ()
    if "\0" not in text:
        entries: list[StructuredDiffEntry] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]
            if status[:1] in {"R", "C"} and len(parts) >= 3:
                entries.append(StructuredDiffEntry(status=status, paths=(parts[1], parts[2])))
            elif len(parts) >= 2:
                entries.append(StructuredDiffEntry(status=status, paths=(parts[-1],)))
        return tuple(entries)

    raw_tokens = text.split("\0")
    if raw_tokens and raw_tokens[-1] == "":
        raw_tokens.pop()
    entries = []
    index = 0
    while index < len(raw_tokens):
        status = raw_tokens[index]
        index += 1
        if not status:
            continue
        if status[:1] in {"R", "C"}:
            if index + 1 >= len(raw_tokens):
                raise PatchHygieneError("malformed_name_status_z_rename_or_copy_entry")
            old_path = raw_tokens[index]
            new_path = raw_tokens[index + 1]
            index += 2
            entries.append(StructuredDiffEntry(status=status, paths=(old_path, new_path)))
            continue
        if index >= len(raw_tokens):
            raise PatchHygieneError("malformed_name_status_z_entry")
        path = raw_tokens[index]
        index += 1
        entries.append(StructuredDiffEntry(status=status, paths=(path,)))
    return tuple(entries)


def classify_patch_path(path: str, policy: PatchHygienePolicy | None = None) -> PathHygieneDecision:
    policy = policy or PatchHygienePolicy.default_training_policy()
    normalized = _normalize_patch_path(path)
    reason = _hard_exclude_reason(normalized, policy)
    if reason is not None:
        return _decision(normalized, "exclude", reason)
    flag_reason = _flag_reason(normalized, policy)
    if flag_reason is not None:
        return _decision(normalized, "flag", flag_reason)
    return _decision(normalized, "include", "allowed_source_path")


def filter_patch_text(
    patch_text: str,
    *,
    policy: PatchHygienePolicy | None = None,
    structured_diff_facts: tuple[StructuredDiffEntry, ...] | list[StructuredDiffEntry] | None = None,
) -> PatchHygieneFilterResult:
    policy = policy or PatchHygienePolicy.default_training_policy()
    entries = tuple(structured_diff_facts or ())
    blocks = _split_diff_blocks(patch_text)
    patch_paths = {
        path
        for _block_text, paths in blocks
        for path in paths
        if path != "/dev/null"
    }
    structured_paths = {
        _normalize_patch_path(path)
        for entry in entries
        for path in entry.paths
        if path != "/dev/null"
    }
    facts_status = "not_provided" if not entries else "matched"
    if entries and patch_paths != structured_paths:
        raise PatchHygieneError(
            "structured_diff_facts_mismatch:"
            f"patch_paths={sorted(patch_paths)} structured_paths={sorted(structured_paths)}"
        )

    cleaned_blocks: list[str] = []
    decisions: list[PatchBlockDecision] = []
    for block_text, paths in blocks:
        path_decisions = tuple(classify_patch_path(path, policy) for path in paths if path != "/dev/null")
        if any(decision.action == "exclude" for decision in path_decisions):
            block_action: PatchHygieneAction = "exclude"
            block_reason = next(decision.reason for decision in path_decisions if decision.action == "exclude")
        elif any(decision.action == "flag" for decision in path_decisions):
            block_action = "flag"
            block_reason = next(decision.reason for decision in path_decisions if decision.action == "flag")
            cleaned_blocks.append(block_text)
        else:
            block_action = "include"
            block_reason = "allowed_source_path"
            cleaned_blocks.append(block_text)
        decisions.append(
            PatchBlockDecision(
                action=block_action,
                reason=block_reason,
                paths=tuple(paths),
                path_decisions=path_decisions,
            )
        )
    cleaned = "".join(cleaned_blocks)
    return PatchHygieneFilterResult(
        raw_patch_text=patch_text,
        cleaned_patch_text=cleaned,
        decisions=tuple(decisions),
        structured_diff_facts_status=facts_status,
        structured_diff_entries=entries,
    )


def build_patch_hygiene_report(
    *,
    patch_result: PatchHygieneFilterResult,
    diff_result: PatchHygieneFilterResult | None = None,
    raw_diff_text: str | None = None,
    cleaned_diff_text: str | None = None,
    raw_patch_ref: dict[str, Any] | None = None,
    raw_diff_ref: dict[str, Any] | None = None,
    final_patch_ref: dict[str, Any] | None = None,
    final_diff_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    filtered_decisions = _unique_public_decisions(patch_result, "exclude")
    flagged_decisions = _unique_public_decisions(patch_result, "flag")
    report = {
        "schema_version": PATCH_HYGIENE_REPORT_SCHEMA_VERSION,
        "patch_hygiene_policy_version": PATCH_HYGIENE_POLICY_VERSION,
        "status": "filtered_changes" if filtered_decisions else "passed",
        "structured_diff_facts_status": patch_result.structured_diff_facts_status,
        "raw_patch_sha256": patch_result.raw_patch_sha256,
        "cleaned_patch_sha256": patch_result.cleaned_patch_sha256,
        "raw_diff_sha256": _sha256_text(raw_diff_text or ""),
        "cleaned_diff_sha256": _sha256_text(cleaned_diff_text or ""),
        "raw_patch_ref": raw_patch_ref,
        "raw_diff_ref": raw_diff_ref,
        "final_patch_ref": final_patch_ref,
        "final_diff_ref": final_diff_ref,
        "filtered_file_count": len(filtered_decisions),
        "flagged_file_count": len(flagged_decisions),
        "filtered_files": [decision.public_dict() for decision in filtered_decisions],
        "flagged_files": [decision.public_dict() for decision in flagged_decisions],
        "only_filtered_changes": patch_result.only_filtered_changes,
        "cleaned_patch_empty": not bool(patch_result.cleaned_patch_text.strip()),
        "raw_patch_nonempty": bool(patch_result.raw_patch_text.strip()),
        "training_target_patch_source": "cleaned_patch_projection",
        "raw_patch_visibility": "runtime_private",
        "public_report_contains_raw_patch": False,
    }
    if diff_result is not None:
        report["diff_structured_diff_facts_status"] = diff_result.structured_diff_facts_status
    return report


def apply_hygiene_to_patch_stats(
    raw_stats: dict[str, object],
    *,
    patch_result: PatchHygieneFilterResult,
    cleaned_added_lines: int,
    cleaned_removed_lines: int,
    hygiene_report: dict[str, Any],
) -> dict[str, object]:
    excluded = {
        decision.path
        for block in patch_result.decisions
        if block.action == "exclude"
        for decision in block.path_decisions
    }

    def keep_paths(paths: object) -> list[str]:
        if not isinstance(paths, list):
            return []
        return [str(path) for path in paths if str(path) not in excluded]

    def keep_renames(value: object) -> list[dict[str, str]]:
        if not isinstance(value, list):
            return []
        kept = []
        for item in value:
            if not isinstance(item, dict):
                continue
            old_path = str(item.get("old_path") or "")
            new_path = str(item.get("new_path") or "")
            if old_path in excluded or new_path in excluded:
                continue
            kept.append({"old_path": old_path, "new_path": new_path})
        return kept

    return {
        "added_lines": cleaned_added_lines,
        "removed_lines": cleaned_removed_lines,
        "changed_files": keep_paths(raw_stats.get("changed_files")),
        "added_files": keep_paths(raw_stats.get("added_files")),
        "modified_files": keep_paths(raw_stats.get("modified_files")),
        "deleted_files": keep_paths(raw_stats.get("deleted_files")),
        "renamed_files": keep_renames(raw_stats.get("renamed_files")),
        "untracked_text_files": keep_paths(raw_stats.get("untracked_text_files")),
        "binary_files": keep_paths(raw_stats.get("binary_files")),
        "symlink_files": keep_paths(raw_stats.get("symlink_files")),
        "patch_hygiene": {
            "schema_version": hygiene_report["schema_version"],
            "patch_hygiene_policy_version": hygiene_report["patch_hygiene_policy_version"],
            "status": hygiene_report["status"],
            "filtered_file_count": hygiene_report["filtered_file_count"],
            "flagged_file_count": hygiene_report["flagged_file_count"],
            "only_filtered_changes": hygiene_report["only_filtered_changes"],
            "cleaned_patch_sha256": hygiene_report["cleaned_patch_sha256"],
            "raw_patch_sha256": hygiene_report["raw_patch_sha256"],
            "raw_added_lines": int(raw_stats.get("added_lines", 0) or 0),
            "raw_removed_lines": int(raw_stats.get("removed_lines", 0) or 0),
        },
    }


def patch_hygiene_invalid_reason(report: dict[str, Any] | None) -> str | None:
    if not isinstance(report, dict):
        return None
    if report.get("status") == "failed":
        return "patch_hygiene_failed"
    if report.get("only_filtered_changes") is True:
        return "patch_hygiene_only_filtered_changes"
    return None


def _split_diff_blocks(patch_text: str) -> list[tuple[str, tuple[str, ...]]]:
    if not patch_text:
        return []
    lines = patch_text.splitlines(keepends=True)
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("diff --git "):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
        elif line.strip():
            raise PatchHygieneError("unexpected_patch_preamble_before_diff_header")
    if current:
        blocks.append(current)
    return [("".join(block), _paths_from_diff_block(block)) for block in blocks]


def _paths_from_diff_block(lines: list[str]) -> tuple[str, ...]:
    header_paths: list[str] = []
    body_paths: list[str] = []
    for line in lines:
        if line.startswith("diff --git "):
            header_paths = _paths_from_diff_git_header(line)
        elif line.startswith("--- ") or line.startswith("+++ "):
            value = line[4:].strip()
            if value != "/dev/null":
                body_paths.append(_strip_git_prefix(_decode_git_path(value)))
    paths = body_paths or header_paths
    deduped: list[str] = []
    for path in paths:
        if path and path != "/dev/null" and path not in deduped:
            deduped.append(_normalize_patch_path(path))
    if not deduped:
        raise PatchHygieneError("diff_block_without_paths")
    return tuple(deduped)


def _paths_from_diff_git_header(line: str) -> list[str]:
    payload = line.strip()[len("diff --git ") :]
    try:
        old_path, new_path = _split_diff_git_header_paths(payload)
    except ValueError as exc:
        raise PatchHygieneError("malformed_diff_git_header") from exc
    return [_strip_git_prefix(old_path), _strip_git_prefix(new_path)]


def _split_diff_git_header_paths(payload: str) -> tuple[str, str]:
    payload = payload.strip()
    if not payload:
        raise ValueError("empty diff header payload")
    if payload.startswith('"'):
        first, index = _consume_git_header_path(payload, 0)
        index = _skip_ascii_spaces(payload, index)
        second, index = _consume_git_header_path(payload, index)
        if payload[index:].strip():
            raise ValueError("extra diff header tokens")
        return first, second

    separator = _find_second_diff_path_separator(payload)
    if not payload.startswith("a/") or separator < 0:
        raise ValueError("unsupported unquoted diff header")
    old_path = payload[:separator]
    new_path_start = separator + 1
    if new_path_start < len(payload) and payload[new_path_start] == '"':
        new_path, index = _consume_git_header_path(payload, new_path_start)
        if payload[index:].strip():
            raise ValueError("extra diff header tokens")
    else:
        new_path = _decode_git_path(payload[new_path_start:])
    if not new_path.startswith("b/"):
        raise ValueError("unsupported unquoted diff header")
    return _decode_git_path(old_path), _decode_git_path(new_path)


def _find_second_diff_path_separator(payload: str) -> int:
    candidates = [
        index
        for index in (payload.find(" b/"), payload.find(' "b/'))
        if index >= 0
    ]
    return min(candidates) if candidates else -1


def _consume_git_header_path(payload: str, start: int) -> tuple[str, int]:
    if start >= len(payload):
        raise ValueError("missing path token")
    if payload[start] != '"':
        end = payload.find(" ", start)
        if end < 0:
            end = len(payload)
        return _decode_git_path(payload[start:end]), end

    index = start + 1
    escaped = False
    while index < len(payload):
        char = payload[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return _decode_git_path(payload[start : index + 1]), index + 1
        index += 1
    raise ValueError("unterminated quoted path")


def _skip_ascii_spaces(value: str, index: int) -> int:
    while index < len(value) and value[index] == " ":
        index += 1
    return index


def _decode_git_path(value: str) -> str:
    value = value.strip()
    if value == "/dev/null":
        return value
    if value.startswith('"') and value.endswith('"'):
        return _decode_git_c_quoted_path(value[1:-1])
    return value


def _decode_git_c_quoted_path(value: str) -> str:
    output = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            output.extend(char.encode("utf-8"))
            index += 1
            continue
        index += 1
        if index >= len(value):
            output.extend(b"\\")
            break
        escaped = value[index]
        if escaped in _GIT_C_QUOTE_ESCAPES:
            output.extend(_GIT_C_QUOTE_ESCAPES[escaped])
            index += 1
            continue
        if escaped in "01234567":
            digits = [escaped]
            index += 1
            while index < len(value) and len(digits) < 3 and value[index] in "01234567":
                digits.append(value[index])
                index += 1
            output.append(int("".join(digits), 8))
            continue
        output.extend(escaped.encode("utf-8"))
        index += 1
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError:
        return output.decode("latin-1")


def _strip_git_prefix(value: str) -> str:
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value


def _normalize_patch_path(path: str) -> str:
    path = path.replace("\\", "/")
    if path == "/dev/null":
        return path
    return PurePosixPath(path).as_posix()


def _hard_exclude_reason(path: str, policy: PatchHygienePolicy) -> str | None:
    if not path or path.startswith("/"):
        return "unsafe_patch_path"
    if any(marker in path for marker in ("\n", "\r", "\t", "\\n", "\\r", "\\t")):
        return "unsafe_patch_path"
    parts = tuple(part for part in path.split("/") if part)
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return "unsafe_patch_path"
    name = parts[-1]
    if len(parts) == 1 and name in policy.root_hard_exclude_names:
        return "root_diagnostic_artifact"
    if any(name.endswith(suffix) for suffix in policy.hard_exclude_suffixes):
        return "temporary_or_cache_artifact"
    if len(parts) == 1 and name.endswith(".py") and name.startswith(policy.root_diagnostic_python_prefixes):
        return "root_diagnostic_script"
    if len(parts) == 1 and name.endswith(policy.root_diagnostic_suffixes):
        return "root_diagnostic_artifact"
    if parts[0] in policy.root_hard_exclude_dirs:
        return "root_temp_directory"
    if any(part in policy.hard_exclude_parts for part in parts):
        return "dependency_cache_or_runtime_private_path"
    if any(_part_has_dependency_or_build_artifact_marker(part, index, parts) for index, part in enumerate(parts)):
        return "dependency_or_build_artifact_path"
    if any(_part_has_runtime_private_marker(part) for part in parts):
        return "repo_harness_runtime_private_path"
    if any(part in {".git", ".env"} or part.startswith(".env.") for part in parts):
        return "hidden_or_environment_path"
    if any(_part_has_sensitive_marker(part) for part in parts):
        return "evaluator_or_hidden_marker_path"
    if any(fnmatch.fnmatch(path, pattern) for pattern in policy.hard_exclude_globs):
        return "dependency_cache_or_runtime_private_path"
    if name.endswith(".egg-info"):
        return "dependency_cache_or_runtime_private_path"
    return None


def _flag_reason(path: str, policy: PatchHygienePolicy) -> str | None:
    parts = tuple(part for part in path.split("/") if part)
    name = parts[-1] if parts else path
    if _is_test_like_path(path):
        return "test_like_file_change"
    if name in policy.flag_only_suffixes:
        return "lock_or_dependency_manifest_change"
    if name in {"pyproject.toml", "setup.py", "setup.cfg", "tox.ini", "noxfile.py", "package.json"}:
        return "project_configuration_change"
    return None


def _decision(path: str, action: PatchHygieneAction, reason: str) -> PathHygieneDecision:
    public_path = path if _path_is_public_safe(path) else None
    return PathHygieneDecision(
        path=path,
        action=action,
        reason=reason,
        path_category=_path_category(path),
        public_path=public_path,
        path_sha256=None if public_path is not None else _sha256_text(path),
        basename_redacted=None if public_path is not None else _basename_redacted(path),
    )


def _unique_public_decisions(
    result: PatchHygieneFilterResult,
    action: PatchHygieneAction,
) -> list[PathHygieneDecision]:
    seen: set[str] = set()
    output: list[PathHygieneDecision] = []
    for block in result.decisions:
        for decision in block.path_decisions:
            if decision.action != action or decision.path in seen:
                continue
            seen.add(decision.path)
            output.append(decision)
    return output


def _is_test_like_path(path: str) -> bool:
    parts = path.split("/")
    name = parts[-1] if parts else path
    return (
        path.startswith(("tests/", "test/", "testing/"))
        or "/tests/" in path
        or "/test/" in path
        or "/testing/" in path
        or name == "conftest.py"
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith((".test.js", ".spec.js", ".test.ts", ".spec.ts"))
    )


def _path_is_public_safe(path: str) -> bool:
    if not path or path.startswith("/"):
        return False
    parts = path.split("/")
    lowered = path.lower()
    if any(marker in lowered for marker in ("gold_patch", "test_patch", "hidden_verifier")):
        return False
    if any(_part_has_runtime_private_marker(part) for part in parts):
        return False
    if any(part in {".git", ".env"} or part.startswith(".env.") for part in parts):
        return False
    if any(marker in path for marker in ("\n", "\r", "\t")):
        return False
    if any(_part_has_sensitive_marker(part) for part in parts):
        return False
    return True


def _path_category(path: str) -> str:
    parts = path.split("/")
    if any(_part_has_runtime_private_marker(part) for part in parts):
        return "runtime_private_or_harness_path"
    if any(part in {".git", ".env"} or part.startswith(".env.") for part in parts):
        return "hidden_environment_or_vcs_path"
    if any(_part_has_sensitive_marker(part) for part in parts):
        return "evaluator_or_hidden_marker_path"
    if path.startswith("/"):
        return "absolute_path"
    return "repository_relative_path"


def _basename_redacted(path: str) -> str:
    name = path.split("/")[-1] if path else ""
    if not name:
        return "<empty>"
    suffix = ""
    if "." in name and not name.startswith("."):
        suffix = "." + name.rsplit(".", 1)[-1]
    return f"<redacted>{suffix}"


def _normalized_marker(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _part_has_sensitive_marker(value: str) -> bool:
    normalized = _normalized_marker(value)
    return any(marker in normalized for marker in _SENSITIVE_PATH_MARKERS)


def _part_has_runtime_private_marker(value: str) -> bool:
    normalized = _normalized_marker(value)
    return any(marker in normalized for marker in _RUNTIME_PRIVATE_PATH_MARKERS)


def _part_has_dependency_or_build_artifact_marker(
    value: str,
    index: int,
    parts: tuple[str, ...],
) -> bool:
    lowered = value.lower()
    if lowered not in _DEPENDENCY_OR_BUILD_ARTIFACT_DIRS:
        return False
    if index == 1 and parts[0].lower() == "src" and lowered in {"env", "build"}:
        return False
    return True


_SENSITIVE_PATH_MARKERS = {
    "goldpatch",
    "testpatch",
    "hiddenverifier",
    "officialverifier",
    "failtopass",
    "passtopass",
    "rewardmetadata",
    "rewardextrainfo",
    "providersecret",
}


_RUNTIME_PRIVATE_PATH_MARKERS = {
    "runtimeprivate",
    "repoharnessruntime",
    "repoharnessenvoverlay",
    "repoharnesstmp",
    "repoharnessrun",
}


_DEPENDENCY_OR_BUILD_ARTIFACT_DIRS = {
    "env",
    "venv",
    "dist",
    "build",
}


_GIT_C_QUOTE_ESCAPES = {
    "\\": b"\\",
    '"': b'"',
    "a": b"\a",
    "b": b"\b",
    "f": b"\f",
    "n": b"\n",
    "r": b"\r",
    "t": b"\t",
    "v": b"\v",
}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_json_sha256(obj: Any) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256_text(data)
