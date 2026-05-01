"""Stable source tree hashing utilities shared by workspace and metadata code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

EXCLUDED_TREE_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}


def compute_file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_source_tree_hash(root: str | Path) -> str:
    """Hash a source checkout while excluding VCS data, caches, and build outputs."""

    root_path = Path(root)
    entries: list[dict[str, str]] = []
    for path in sorted(root_path.rglob("*")):
        relative = path.relative_to(root_path)
        if _is_excluded(relative):
            continue
        if path.is_dir():
            continue
        if path.is_symlink():
            entries.append(
                {
                    "path": relative.as_posix(),
                    "kind": "symlink",
                    "target": str(path.readlink()),
                }
            )
            continue
        if path.is_file():
            entries.append(
                {
                    "path": relative.as_posix(),
                    "kind": "file",
                    "sha256": compute_file_sha256(path),
                }
            )
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_excluded(relative: Path) -> bool:
    return any(part in EXCLUDED_TREE_PARTS for part in relative.parts)
