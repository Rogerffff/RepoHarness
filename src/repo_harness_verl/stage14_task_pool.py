"""Stage 14.1 multi-task pool helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel


class Stage14TaskPoolEntry(StrictBaseModel):
    """One auditable task-pool entry for Stage 14.1 remote smoke."""

    name: str
    task_id: str
    task_category: str
    repo_fixture_ref: str
    task_ref: str
    expected_outcome_class: str
    dependency_profile: str = "none"
    dependency_packages: list[dict[str, str]] = Field(default_factory=list)
    source_layout: str = "flat"
    negative_control: bool = False
    diagnostic_control: bool = False
    policy_loss_queue_eligible: bool = True
    max_attempts: int = Field(default=1, ge=1)
    prompt_variant: str | None = None

    @model_validator(mode="after")
    def _validate_entry(self) -> "Stage14TaskPoolEntry":
        if self.diagnostic_control and self.policy_loss_queue_eligible:
            raise ValueError("diagnostic_control entries cannot be policy-loss queue eligible")
        if self.negative_control and self.expected_outcome_class != "final_verifier_rejected_trainable":
            raise ValueError("negative_control entries must use final_verifier_rejected_trainable expected outcome")
        if self.dependency_profile != "none" and not self.dependency_packages:
            raise ValueError("dependency entries must declare dependency_packages")
        return self


class Stage14TaskPoolSpec(StrictBaseModel):
    """Frozen Stage 14.1 task-pool specification."""

    schema_version: str = "repo_harness_verl_stage14_task_pool_spec_v0"
    task_pool_name: str = "stage14_1_default_multitask_pool"
    entries: list[Stage14TaskPoolEntry]

    @model_validator(mode="after")
    def _validate_spec(self) -> "Stage14TaskPoolSpec":
        task_ids = [entry.task_id for entry in self.entries if not entry.diagnostic_control]
        if len(set(task_ids)) < 3:
            raise ValueError("Stage 14.1 task pool requires at least three unique real task ids")
        if not any(entry.expected_outcome_class == "accepted" for entry in self.entries):
            raise ValueError("Stage 14.1 task pool requires at least one accepted task")
        if not any(entry.negative_control for entry in self.entries):
            raise ValueError("Stage 14.1 task pool requires a trainable negative control entry")
        if not any(entry.diagnostic_control for entry in self.entries):
            raise ValueError("Stage 14.1 task pool requires a diagnostic control entry")
        return self

    @property
    def task_pool_digest(self) -> str:
        payload = self.model_dump(mode="json")
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": "repo_harness_verl_stage14_task_pool_manifest_v0",
            "task_pool_name": self.task_pool_name,
            "task_pool_digest": self.task_pool_digest,
            "task_count": len([entry for entry in self.entries if not entry.diagnostic_control]),
            "unique_task_id_count": len({entry.task_id for entry in self.entries if not entry.diagnostic_control}),
            "entries": [entry.model_dump(mode="json") for entry in self.entries],
        }


def default_stage14_1_task_pool() -> Stage14TaskPoolSpec:
    """Return the default Stage 14.1 task pool with repo-relative paths."""

    return Stage14TaskPoolSpec(
        entries=[
            Stage14TaskPoolEntry(
                name="accepted_baseline",
                task_id="task_security_probe",
                task_category="accepted_baseline",
                repo_fixture_ref="tests/fixtures/repos/security_probe",
                task_ref="tests/fixtures/tasks/task_security_probe.yaml",
                expected_outcome_class="accepted",
                source_layout="flat",
            ),
            Stage14TaskPoolEntry(
                name="accepted_src_layout",
                task_id="task_002",
                task_category="accepted_src_layout",
                repo_fixture_ref="tests/fixtures/repos/import_config_bug",
                task_ref="tests/fixtures/tasks/task_002.yaml",
                expected_outcome_class="accepted",
                source_layout="src_or_package",
            ),
            Stage14TaskPoolEntry(
                name="accepted_create_file",
                task_id="task_003_create_file",
                task_category="accepted_create_file",
                repo_fixture_ref="tests/fixtures/repos/missing_helper_file",
                task_ref="tests/fixtures/tasks/task_003_create_file.yaml",
                expected_outcome_class="accepted",
                source_layout="src_or_package",
            ),
            Stage14TaskPoolEntry(
                name="accepted_dependency",
                task_id="task_dependency_packaging_smoke",
                task_category="accepted_dependency",
                repo_fixture_ref="tests/fixtures/repos/dependency_packaging_smoke",
                task_ref="tests/fixtures/tasks/task_dependency_packaging_smoke.yaml",
                expected_outcome_class="accepted",
                dependency_profile="python_pip_hashed_package",
                dependency_packages=[
                    {
                        "name": "tomli",
                        "version": "2.0.1",
                        "artifact": "tomli-2.0.1-py3-none-any.whl",
                        "sha256": "939de3e7a6161af0c887ef91b7d41a53e7c5a1ca976325f429cb46ea9bc30ecc",
                    }
                ],
                source_layout="src_or_package",
            ),
            Stage14TaskPoolEntry(
                name="trainable_negative_control",
                task_id="task_001",
                task_category="trainable_negative_control",
                repo_fixture_ref="tests/fixtures/repos/buggy_calculator",
                task_ref="tests/fixtures/tasks/task_001.yaml",
                expected_outcome_class="final_verifier_rejected_trainable",
                source_layout="flat",
                negative_control=True,
                max_attempts=3,
                prompt_variant="normal_goal_boundary_sensitive_v1",
            ),
            Stage14TaskPoolEntry(
                name="diagnostic_control",
                task_id="stage14_1_diagnostic_side_channel",
                task_category="diagnostic_control",
                repo_fixture_ref="side-channel-only",
                task_ref="side-channel-only",
                expected_outcome_class="diagnostic_rejected",
                diagnostic_control=True,
                policy_loss_queue_eligible=False,
                prompt_variant="side_channel_missing_logprob_or_visibility_rejected_v1",
            ),
        ]
    )


def validate_stage14_task_pool_paths(spec: Stage14TaskPoolSpec, *, repo_root: str | Path = ".") -> list[str]:
    """Validate that real task-pool paths exist and remain repo-relative."""

    root = Path(repo_root)
    failures: list[str] = []
    for entry in spec.entries:
        for field_name in ("repo_fixture_ref", "task_ref"):
            value = getattr(entry, field_name)
            if value == "side-channel-only":
                continue
            path = Path(value)
            if path.is_absolute():
                failures.append(f"{entry.name}:{field_name}_is_absolute")
                continue
            if ".." in path.parts:
                failures.append(f"{entry.name}:{field_name}_contains_parent_segment")
                continue
            if not (root / path).exists():
                failures.append(f"{entry.name}:{field_name}_missing:{value}")
    return failures


def build_stage14_fixture_sha256_report(
    spec: Stage14TaskPoolSpec,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    """Build sha256 facts for every real task yaml and fixture repository file."""

    root = Path(repo_root)
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in spec.entries:
        if entry.diagnostic_control:
            continue
        for relative in _entry_file_refs(entry, root):
            if relative in seen:
                continue
            seen.add(relative)
            path = root / relative
            files.append(
                {
                    "path": relative,
                    "sha256": _sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    return {
        "schema_version": "repo_harness_verl_stage14_fixture_sha256_report_v0",
        "task_pool_digest": spec.task_pool_digest,
        "file_count": len(files),
        "files": sorted(files, key=lambda item: item["path"]),
    }


def _entry_file_refs(entry: Stage14TaskPoolEntry, root: Path) -> list[str]:
    refs: list[str] = [entry.task_ref]
    repo = root / entry.repo_fixture_ref
    if repo.exists() and repo.is_dir():
        for path in sorted(repo.rglob("*")):
            if path.is_file():
                refs.append(path.relative_to(root).as_posix())
    return refs


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
