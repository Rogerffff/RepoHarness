"""Patch action parsing for single-shot scaffold runs."""

from __future__ import annotations

import re

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel, stable_hash


class PatchActionParseResult(StrictBaseModel):
    schema_version: str = "repo_harness_patch_action_parse_result_v0"
    success: bool
    patch_text: str = ""
    patch_sha256: str | None = None
    changed_paths: list[str] = Field(default_factory=list)
    error_type: str | None = None
    message: str | None = None


def parse_patch_action(content: str | None) -> PatchActionParseResult:
    text = (content or "").strip()
    if not text:
        return PatchActionParseResult(
            success=False,
            error_type="empty_patch_action",
            message="single_shot_patch response did not contain patch text.",
        )
    patch_text = _extract_fenced_diff(text) or text
    if not patch_text.endswith("\n"):
        patch_text += "\n"
    if not _looks_like_unified_diff(patch_text):
        return PatchActionParseResult(
            success=False,
            error_type="missing_unified_diff",
            message="single_shot_patch response must contain a unified diff.",
        )
    changed_paths = _changed_paths_from_diff(patch_text)
    if not changed_paths:
        return PatchActionParseResult(
            success=False,
            patch_text=patch_text,
            patch_sha256=stable_hash(patch_text),
            error_type="missing_changed_paths",
            message="patch did not declare any changed repository paths.",
        )
    return PatchActionParseResult(
        success=True,
        patch_text=patch_text,
        patch_sha256=stable_hash(patch_text),
        changed_paths=changed_paths,
    )


def _extract_fenced_diff(text: str) -> str | None:
    match = re.search(r"```(?:diff|patch)?\s*\n(?P<body>.*?)\n```", text, flags=re.DOTALL)
    if match is None:
        return None
    return match.group("body").strip() + "\n"


def _looks_like_unified_diff(text: str) -> bool:
    return (
        "diff --git " in text
        or ("\n--- " in f"\n{text}" and "\n+++ " in f"\n{text}" and "\n@@ " in f"\n{text}")
    )


def _changed_paths_from_diff(text: str) -> list[str]:
    paths: list[str] = []
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                paths.extend([_normalize_diff_path(parts[2]), _normalize_diff_path(parts[3])])
            continue
        if line.startswith("--- ") or line.startswith("+++ "):
            token = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) == 2 else ""
            paths.append(_normalize_diff_path(token))
    return sorted({path for path in paths if path})


def _normalize_diff_path(token: str) -> str:
    path = token.strip()
    if "\t" in path:
        path = path.split("\t", 1)[0]
    if path == "/dev/null":
        return ""
    if path.startswith("a/") or path.startswith("b/"):
        path = path[2:]
    return path
