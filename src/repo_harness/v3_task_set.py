"""V3 repository-level task set adapters and inspection."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
import tempfile
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    TASK_ADAPTER_FACTS_SCHEMA_VERSION,
    TASK_SCHEMA_VERSION,
)
from repo_harness.tasks import (
    RealRepositorySourceFacts,
    SweBenchLikeTaskFacts,
    TaskAdapterFacts,
    TaskDefinition,
)
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_swebench_fixture import (
    EXPECTED_ACCEPTED_TASK_IDS,
    EXPECTED_DATASET_NAME,
    EXPECTED_DATASET_REVISION,
    EXPECTED_DATASET_SPLIT,
)
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

REAL_REPOSITORY_TASK_INPUTS_VERSION = "repo_harness_v3_real_repository_task_inputs_v0"
REAL_REPOSITORY_TASK_MANIFEST_VERSION = "repo_harness_real_repository_task_manifest_v3_v0"
SWEBENCH_LIKE_TASK_FACTS_MANIFEST_VERSION = "repo_harness_swebench_like_task_facts_manifest_v3_v0"
TASK_ADAPTER_FACTS_MANIFEST_VERSION = "repo_harness_task_adapter_facts_manifest_v3_v0"
TASK_SET_INSPECT_REPORT_VERSION = "repo_harness_v3_task_set_inspect_report_v0"
TASK_ADAPTER_VERSION = "repo_harness_task_adapter_v3_v0"


def build_v3_task_set(
    *,
    real_repository_inputs: str | Path,
    swebench_fixture_dir: str | Path,
    swebench_manifest: str | Path,
    swebench_evidence_dir: str | Path,
    output_dir: str | Path,
) -> Path:
    """Build Stage 4 task adapter facts and generated task definitions."""

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    real_inputs_path = Path(real_repository_inputs)
    swe_fixture_root = Path(swebench_fixture_dir)
    swe_manifest_path = Path(swebench_manifest)
    swe_evidence_root = Path(swebench_evidence_dir)

    adapter_facts: list[dict[str, Any]] = []
    real_manifest = _build_real_repository_tasks(
        real_inputs_path=real_inputs_path,
        output_root=output_root,
        adapter_facts=adapter_facts,
    )
    swebench_manifest_payload = _build_swebench_like_tasks(
        fixture_root=swe_fixture_root,
        task_input_manifest_path=swe_manifest_path,
        evidence_root=swe_evidence_root,
        output_root=output_root,
        adapter_facts=adapter_facts,
    )

    adapter_facts_manifest = {
        "schema_version": TASK_ADAPTER_FACTS_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "adapter_version": TASK_ADAPTER_VERSION,
        "task_count": len(adapter_facts),
        "facts": adapter_facts,
    }
    _write_json(output_root / "real_repository_task_manifest.json", real_manifest)
    _write_json(output_root / "swebench_like_task_facts.json", swebench_manifest_payload)
    adapter_facts_manifest["real_repository_manifest_ref"] = _artifact_ref(
        output_root / "real_repository_task_manifest.json",
        artifact_id="real_repository_task_manifest",
        kind="json",
        base_dir=output_root,
    ).model_dump(mode="json")
    adapter_facts_manifest["swebench_like_task_facts_ref"] = _artifact_ref(
        output_root / "swebench_like_task_facts.json",
        artifact_id="swebench_like_task_facts",
        kind="json",
        base_dir=output_root,
    ).model_dump(mode="json")
    _write_json(output_root / "task_adapter_facts.json", adapter_facts_manifest)
    return output_root


def inspect_v3_task_set(run_dir: str | Path, *, assert_complete: bool = False) -> str:
    """Read and validate Stage 4 task adapter outputs."""

    run_root = Path(run_dir)
    failures: list[str] = []
    real_manifest_path = run_root / "real_repository_task_manifest.json"
    swe_facts_path = run_root / "swebench_like_task_facts.json"
    adapter_facts_path = run_root / "task_adapter_facts.json"
    real_manifest = _read_json_for_inspect(real_manifest_path, failures)
    swe_facts = _read_json_for_inspect(swe_facts_path, failures)
    adapter_facts = _read_json_for_inspect(adapter_facts_path, failures)
    if failures:
        return _inspect_result(run_root, failures, assert_complete)

    _inspect_real_repository_manifest(run_root, real_manifest, failures)
    _inspect_swebench_like_facts(run_root, swe_facts, failures)
    _inspect_task_adapter_facts(run_root, adapter_facts, failures)
    return _inspect_result(run_root, failures, assert_complete)


def _build_real_repository_tasks(
    *,
    real_inputs_path: Path,
    output_root: Path,
    adapter_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    payload = _read_json(real_inputs_path)
    if payload.get("schema_version") != REAL_REPOSITORY_TASK_INPUTS_VERSION:
        raise ConfigError("真实仓库任务输入 schema_version 不匹配。")
    _require_non_empty(payload, ["dataset_source_revision"])
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ConfigError("真实仓库任务输入必须包含非空 tasks。")

    generated_tasks: list[dict[str, Any]] = []
    source_facts_refs: list[dict[str, Any]] = []
    for record in tasks:
        if not isinstance(record, dict):
            raise ConfigError("真实仓库任务记录必须是 JSON object。")
        _require_non_empty(
            record,
            [
                "task_id",
                "task_version",
                "source_kind",
                "remote_url",
                "base_commit",
                "source_tree_hash",
                "decontamination_status",
                "verifier_evidence_path",
                "issue",
                "test_command",
            ],
        )
        record = {**record, "dataset_source_revision": payload["dataset_source_revision"]}
        task_id = str(record["task_id"])
        source_facts = _real_repository_source_facts(record)
        source_facts_path = output_root / "real_repository_source_facts" / f"{task_id}.json"
        _write_json(source_facts_path, source_facts.model_dump(mode="json"))
        source_facts_ref = _artifact_ref(
            source_facts_path,
            artifact_id=f"{task_id}_source_facts",
            kind="json",
            base_dir=output_root,
        )
        source_facts_refs.append(source_facts_ref.model_dump(mode="json"))

        task_dir = output_root / "generated_tasks" / "real_repository"
        task_definition = _real_repository_task_definition(record, task_dir=task_dir)
        _validate_task_definition(task_definition, task_id)
        task_path = task_dir / f"{task_id}.yaml"
        _write_yaml(task_path, task_definition)
        visibility_path = output_root / "visibility_policies" / f"{task_id}.json"
        _write_json(visibility_path, task_definition["visibility"])
        task_ref = _artifact_ref(task_path, artifact_id=f"{task_id}_task", kind="yaml", base_dir=output_root)
        adapter_fact = TaskAdapterFacts(
            adapter_name="real_repository",
            adapter_version=TASK_ADAPTER_VERSION,
            input_manifest_ref=_artifact_ref(
                real_inputs_path,
                artifact_id="real_repository_task_inputs",
                kind="json",
            ),
            output_task_ref=task_ref,
            task_hash=_sha256_json(task_definition),
            visibility_policy_ref=_artifact_ref(
                visibility_path,
                artifact_id=f"{task_id}_visibility_policy",
                kind="json",
                base_dir=output_root,
            ),
            decontamination_evidence_refs=[source_facts_ref],
            final_only_policy="not_final_only",
        )
        adapter_facts.append(adapter_fact.model_dump(mode="json"))
        generated_tasks.append(
            {
                "task_id": task_id,
                "source_kind": record["source_kind"],
                "remote_url": record["remote_url"],
                "base_commit": record["base_commit"],
                "source_tree_hash": record["source_tree_hash"],
                "decontamination_status": record["decontamination_status"],
                "generated_task_ref": task_ref.model_dump(mode="json"),
                "source_facts_ref": source_facts_ref.model_dump(mode="json"),
                "verifier_evidence_ref": source_facts.verifier_evidence_ref.model_dump(mode="json"),
            }
        )

    return {
        "schema_version": REAL_REPOSITORY_TASK_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "dataset_source_revision": payload.get("dataset_source_revision"),
        "task_count": len(generated_tasks),
        "public_archive_count": sum(1 for item in generated_tasks if item["source_kind"] == "public_archive"),
        "unique_source_tree_hash_count": len({item["source_tree_hash"] for item in generated_tasks}),
        "source_facts_refs": source_facts_refs,
        "tasks": generated_tasks,
    }


def _build_swebench_like_tasks(
    *,
    fixture_root: Path,
    task_input_manifest_path: Path,
    evidence_root: Path,
    output_root: Path,
    adapter_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    adapter_root = fixture_root / "adapter_inputs"
    tasks_path = adapter_root / "swebench_like_tasks.jsonl"
    task_manifest = _read_json(task_input_manifest_path)
    _assert_swebench_task_manifest(task_manifest, task_input_manifest_path, tasks_path, evidence_root)
    rows = _read_jsonl(tasks_path)
    by_manifest_task = {task["instance_id"]: task for task in task_manifest["tasks"]}
    generated: list[dict[str, Any]] = []
    task_ids: list[str] = []
    for row in rows:
        _require_non_empty(
            row,
            [
                "instance_id",
                "repo",
                "base_commit",
                "environment_setup_commit",
                "dataset_name",
                "dataset_revision",
                "dataset_split",
                "problem_statement",
                "problem_statement_sha256",
                "hidden_evidence_hashes",
            ],
        )
        task_id = row["instance_id"]
        task_ids.append(task_id)
        expected = by_manifest_task.get(task_id)
        if expected is None:
            raise ConfigError(f"SWE-Bench-like manifest 缺少任务：{task_id}")
        _assert_swebench_row_matches_manifest(row, expected)
        if expected.get("task_input_sha256") != _sha256_json(row):
            raise ConfigError(f"SWE-Bench-like task_input_sha256 不匹配：{task_id}")
        facts = _swebench_like_task_facts(row, tasks_path, task_manifest)
        facts_path = output_root / "swebench_like_task_facts" / f"{task_id}.json"
        _write_json(facts_path, facts.model_dump(mode="json"))
        task_definition = _swebench_like_task_definition(row)
        _validate_task_definition(task_definition, task_id)
        task_path = output_root / "generated_tasks" / "swebench_like" / f"{task_id}.yaml"
        _write_yaml(task_path, task_definition)
        visibility_path = output_root / "visibility_policies" / f"{task_id}.json"
        _write_json(visibility_path, task_definition["visibility"])
        task_ref = _artifact_ref(task_path, artifact_id=f"{task_id}_task", kind="yaml", base_dir=output_root)
        fact_ref = _artifact_ref(facts_path, artifact_id=f"{task_id}_swebench_facts", kind="json", base_dir=output_root)
        adapter_fact = TaskAdapterFacts(
            adapter_name="swebench_like_fixed",
            adapter_version=TASK_ADAPTER_VERSION,
            input_manifest_ref=_artifact_ref(
                task_input_manifest_path,
                artifact_id="swebench_like_task_input_manifest",
                kind="json",
            ),
            output_task_ref=task_ref,
            task_hash=_sha256_json(task_definition),
            visibility_policy_ref=_artifact_ref(
                visibility_path,
                artifact_id=f"{task_id}_visibility_policy",
                kind="json",
                base_dir=output_root,
            ),
            decontamination_evidence_refs=[fact_ref],
            final_only_policy="disabled_feedback_only",
        )
        adapter_facts.append(adapter_fact.model_dump(mode="json"))
        generated.append(
            {
                "instance_id": task_id,
                "repo": row["repo"],
                "base_commit": row["base_commit"],
                "environment_setup_commit": row["environment_setup_commit"],
                "task_hash": facts.task_hash,
                "generated_task_ref": task_ref.model_dump(mode="json"),
                "facts_ref": fact_ref.model_dump(mode="json"),
                "test_patch_sha256": facts.test_patch_sha256,
                "fail_to_pass_selectors_sha256": facts.fail_to_pass_selectors_sha256,
                "pass_to_pass_selectors_sha256": facts.pass_to_pass_selectors_sha256,
                "fail_to_pass_selector_count": facts.fail_to_pass_selector_count,
                "pass_to_pass_selector_count": facts.pass_to_pass_selector_count,
            }
        )
    if tuple(task_ids) != EXPECTED_ACCEPTED_TASK_IDS:
        raise ConfigError("SWE-Bench-like adapter 输入任务集合与阶段 0 accepted task 不一致。")
    return {
        "schema_version": SWEBENCH_LIKE_TASK_FACTS_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "dataset_name": EXPECTED_DATASET_NAME,
        "dataset_revision": EXPECTED_DATASET_REVISION,
        "dataset_split": EXPECTED_DATASET_SPLIT,
        "task_count": len(generated),
        "accepted_task_ids": task_ids,
        "adapter_input_ref": _artifact_ref(tasks_path, artifact_id="swebench_like_tasks", kind="jsonl").model_dump(
            mode="json"
        ),
        "task_input_manifest_ref": _artifact_ref(
            task_input_manifest_path,
            artifact_id="swebench_like_task_input_manifest",
            kind="json",
        ).model_dump(mode="json"),
        "evaluator_evidence_manifest_ref": _artifact_ref_from_input_ref(
            task_manifest["evaluator_only_manifest_ref"],
            artifact_id="swebench_like_evaluator_evidence_manifest",
            kind="json",
        ).model_dump(mode="json"),
        "tasks": generated,
    }


def _real_repository_source_facts(record: dict[str, Any]) -> RealRepositorySourceFacts:
    source_kind = record["source_kind"]
    verifier_evidence = Path(record["verifier_evidence_path"])
    if not verifier_evidence.exists():
        raise ConfigError(f"真实仓库 verifier evidence 不存在：{verifier_evidence}")
    if source_kind == "public_archive":
        _require_non_empty(record, ["archive_path", "archive_sha256", "expected_root_directory"])
        archive = Path(record["archive_path"])
        if not archive.exists():
            raise ConfigError(f"公开仓库归档不存在：{archive}")
        if compute_file_sha256(archive) != record["archive_sha256"]:
            raise ConfigError(f"公开仓库归档 sha256 不匹配：{archive}")
        extracted_hash = _archive_source_tree_hash(archive, record["expected_root_directory"])
        if extracted_hash != record["source_tree_hash"]:
            raise ConfigError(f"公开仓库 source_tree_hash 不匹配：{record['task_id']}")
        source_ref = _artifact_ref(archive, artifact_id=f"{record['task_id']}_source_archive", kind="source_archive")
        return RealRepositorySourceFacts(
            source_kind="public_archive",
            remote_url=record["remote_url"],
            base_commit=record["base_commit"],
            dataset_source_revision=record.get("dataset_source_revision"),
            archive_sha256=record["archive_sha256"],
            source_tree_hash=record["source_tree_hash"],
            local_materialization_ref=source_ref,
            verifier_evidence_ref=_artifact_ref(
                verifier_evidence,
                artifact_id=f"{record['task_id']}_verifier_evidence",
                kind="json",
            ),
        )
    if source_kind == "fixed_local_mirror":
        _require_non_empty(record, ["source_path", "mirror_sha256"])
        source_path = Path(record["source_path"])
        if not source_path.exists() or not source_path.is_dir():
            raise ConfigError(f"固定本地 mirror 不存在：{source_path}")
        source_hash = compute_source_tree_hash(source_path)
        if source_hash != record["source_tree_hash"] or source_hash != record["mirror_sha256"]:
            raise ConfigError(f"固定本地 mirror source hash 不匹配：{record['task_id']}")
        return RealRepositorySourceFacts(
            source_kind="fixed_local_mirror",
            remote_url=record["remote_url"],
            base_commit=record["base_commit"],
            dataset_source_revision=record.get("dataset_source_revision"),
            mirror_sha256=record["mirror_sha256"],
            source_tree_hash=record["source_tree_hash"],
            local_materialization_ref=_artifact_ref(
                source_path,
                artifact_id=f"{record['task_id']}_source_mirror",
                kind="source_directory",
            ),
            verifier_evidence_ref=_artifact_ref(
                verifier_evidence,
                artifact_id=f"{record['task_id']}_verifier_evidence",
                kind="json",
            ),
        )
    raise ConfigError(f"不支持的真实仓库 source_kind：{source_kind}")


def _real_repository_task_definition(record: dict[str, Any], *, task_dir: Path) -> dict[str, Any]:
    source_kind = record["source_kind"]
    if source_kind == "public_archive":
        archive_path = _path_for_generated_task(Path(record["archive_path"]), task_dir)
        repo_source_spec = {
            "source_type": "public_snapshot",
            "remote_url": record["remote_url"],
            "commit_sha": record["base_commit"],
            "mirror_source": "predownloaded_public_archive",
            "archive_sha256": record["archive_sha256"],
            "archive_path": archive_path,
            "expected_root_directory": record["expected_root_directory"],
            "decontamination_status": record["decontamination_status"],
            "remotes_stripped": True,
            "branches_stripped": True,
            "tags_stripped": True,
        }
        repo = archive_path
        source_archive_sha256 = record["archive_sha256"]
    elif source_kind == "fixed_local_mirror":
        source_path = _path_for_generated_task(Path(record["source_path"]), task_dir)
        repo_source_spec = {
            "source_type": "local_repository",
            "source_path": source_path,
            "current_commit": record["base_commit"],
            "working_tree_clean": True,
            "allow_dirty_snapshot": False,
            "base_commit": record["base_commit"],
            "decontamination_status": record["decontamination_status"],
        }
        repo = source_path
        source_archive_sha256 = None
    else:
        raise ConfigError(f"不支持的真实仓库 source_kind：{source_kind}")
    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "id": record["task_id"],
        "task_version": record["task_version"],
        "dataset_name": "repo_harness_v3_real_repository",
        "source_kind": source_kind,
        "dataset_split": record.get("dataset_split"),
        "created_at": record.get("created_at", "2026-05-02"),
        "repo": repo,
        "repo_source_spec": repo_source_spec,
        "base_commit": record["base_commit"],
        "source_archive_sha256": source_archive_sha256,
        "issue": record["issue"],
        "setup_command": record.get("setup_command"),
        "test_command": record["test_command"],
        "timeouts": _default_timeouts(),
        "environment": _default_environment(source_archive_sha256),
        "expected_files": record.get("expected_files", []),
        "fail_to_pass_tests": record.get("fail_to_pass_tests", []),
        "pass_to_pass_tests": record.get("pass_to_pass_tests", []),
        "visibility": _default_visibility(),
        "decontamination": {
            "status": record["decontamination_status"],
            "known_public_solution": source_kind == "public_archive",
            "source_url": record["remote_url"],
            "overlap_check_notes": "stage_04_adapter_source_fact_only",
        },
        "declared_setup_mutations": [],
        "generated_files": [],
        "tags": record.get("tags", []),
        "metadata": {
            "v3_adapter": "real_repository",
            "source_tree_hash": record["source_tree_hash"],
            "verifier_evidence_path": record["verifier_evidence_path"],
        },
    }


def _swebench_like_task_facts(
    row: dict[str, Any],
    tasks_path: Path,
    task_manifest: dict[str, Any],
) -> SweBenchLikeTaskFacts:
    hidden = row["hidden_evidence_hashes"]
    _require_non_empty(
        hidden,
        [
            "verifier_material_sha256",
            "target_selector_list_sha256",
            "regression_selector_list_sha256",
        ],
    )
    return SweBenchLikeTaskFacts(
        instance_id=row["instance_id"],
        repo=row["repo"],
        base_commit=row["base_commit"],
        environment_setup_commit=row["environment_setup_commit"],
        dataset_name=row["dataset_name"],
        dataset_revision=row["dataset_revision"],
        dataset_split=row["dataset_split"],
        task_hash=_sha256_json(row),
        problem_statement_sha256=row["problem_statement_sha256"],
        test_patch_sha256=hidden["verifier_material_sha256"],
        fail_to_pass_selectors_sha256=hidden["target_selector_list_sha256"],
        pass_to_pass_selectors_sha256=hidden["regression_selector_list_sha256"],
        fail_to_pass_selector_count=int(hidden.get("target_selector_count", 0)),
        pass_to_pass_selector_count=int(hidden.get("regression_selector_count", 0)),
        adapter_input_ref=_artifact_ref(tasks_path, artifact_id="swebench_like_tasks", kind="jsonl"),
        evaluator_evidence_manifest_ref=_artifact_ref_from_input_ref(
            task_manifest["evaluator_only_manifest_ref"],
            artifact_id="swebench_like_evaluator_evidence_manifest",
            kind="json",
        ),
    )


def _swebench_like_task_definition(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": TASK_SCHEMA_VERSION,
        "id": row["instance_id"],
        "task_version": "swebench_like_fixed_v3_v0",
        "dataset_name": row["dataset_name"],
        "source_kind": "swebench_like_fixed_snapshot",
        "dataset_split": row["dataset_split"],
        "created_at": (row.get("created_at") or "2026-05-02")[:10],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "issue": row["problem_statement"],
        "setup_command": None,
        "test_command": "pytest -q",
        "timeouts": _default_timeouts(),
        "environment": _default_environment(None),
        "expected_files": [],
        "fail_to_pass_tests": [],
        "pass_to_pass_tests": [],
        "visibility": _default_visibility(),
        "decontamination": {
            "status": "fixed_dataset_snapshot_visibility_checked",
            "known_public_solution": True,
            "source_url": row["repo"],
            "overlap_check_notes": "adapter_visible_input_contains_hashes_only_for_hidden_verifier_material",
        },
        "declared_setup_mutations": [],
        "generated_files": [],
        "tags": ["v3", "swebench_like", "fixed_snapshot", "swe_bench_like_final_only", "final_only"],
        "metadata": {
            "v3_adapter": "swebench_like_fixed",
            "swe_bench_like_final_only": True,
            "final_only": True,
            "instance_id": row["instance_id"],
            "repo": row["repo"],
            "base_commit": row["base_commit"],
            "environment_setup_commit": row["environment_setup_commit"],
            "benchmark_comparability": row.get(
                "benchmark_comparability",
                "not_public_leaderboard_comparable",
            ),
            "hidden_evidence_hashes": row["hidden_evidence_hashes"],
        },
    }


def _assert_swebench_row_matches_manifest(row: dict[str, Any], expected: dict[str, Any]) -> None:
    task_id = row["instance_id"]
    if row.get("dataset_name") != EXPECTED_DATASET_NAME:
        raise ConfigError(f"SWE-Bench-like row dataset_name 不匹配：{task_id}")
    if row.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        raise ConfigError(f"SWE-Bench-like row dataset revision 不匹配：{task_id}")
    if row.get("dataset_split") != EXPECTED_DATASET_SPLIT:
        raise ConfigError(f"SWE-Bench-like row dataset split 不匹配：{task_id}")
    if row.get("repo") != expected.get("repo"):
        raise ConfigError(f"SWE-Bench-like row repo 与 manifest 不一致：{task_id}")
    if row.get("base_commit") != expected.get("base_commit"):
        raise ConfigError(f"SWE-Bench-like row base_commit 与 manifest 不一致：{task_id}")
    problem_hash = _sha256_text(row["problem_statement"])
    if row.get("problem_statement_sha256") != problem_hash:
        raise ConfigError(f"SWE-Bench-like problem_statement_sha256 不匹配：{task_id}")
    model_visible = row.get("model_visible_field_sha256")
    expected_visible = expected.get("model_visible_field_sha256")
    if not isinstance(model_visible, dict) or not isinstance(expected_visible, dict):
        raise ConfigError(f"SWE-Bench-like model visible field hash 缺失：{task_id}")
    recomputed_visible = {
        "repo": _sha256_text(row["repo"]),
        "instance_id": _sha256_text(row["instance_id"]),
        "base_commit": _sha256_text(row["base_commit"]),
        "problem_statement": problem_hash,
        "environment_setup_commit": _sha256_text(row["environment_setup_commit"]),
    }
    if model_visible != recomputed_visible or expected_visible != recomputed_visible:
        raise ConfigError(f"SWE-Bench-like model_visible_field_sha256 不匹配：{task_id}")
    if row.get("hidden_evidence_hashes") != expected.get("hidden_evidence_hashes"):
        raise ConfigError(f"SWE-Bench-like hidden evidence hash 与 manifest 不一致：{task_id}")


def _assert_swebench_task_manifest(
    task_manifest: dict[str, Any],
    task_input_manifest_path: Path,
    tasks_path: Path,
    evidence_root: Path,
) -> None:
    if task_manifest.get("dataset_name") != EXPECTED_DATASET_NAME:
        raise ConfigError("SWE-Bench-like dataset_name 不匹配。")
    if task_manifest.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        raise ConfigError("SWE-Bench-like dataset revision 不匹配。")
    if task_manifest.get("dataset_split") != EXPECTED_DATASET_SPLIT:
        raise ConfigError("SWE-Bench-like dataset split 不匹配。")
    if tuple(task_manifest.get("accepted_task_ids", [])) != EXPECTED_ACCEPTED_TASK_IDS:
        raise ConfigError("SWE-Bench-like accepted_task_ids 不匹配。")
    _assert_named_sha256_sidecar(task_input_manifest_path)
    adapter_ref = task_manifest.get("adapter_visible_input_ref")
    if not isinstance(adapter_ref, dict):
        raise ConfigError("SWE-Bench-like task manifest 缺少 adapter_visible_input_ref。")
    if Path(adapter_ref.get("path", "")).resolve() != tasks_path.resolve():
        raise ConfigError("SWE-Bench-like adapter input path 不匹配。")
    if compute_file_sha256(tasks_path) != adapter_ref.get("sha256"):
        raise ConfigError("SWE-Bench-like adapter input sha256 不匹配。")
    _assert_named_sha256_sidecar(tasks_path)
    evaluator_ref = task_manifest.get("evaluator_only_manifest_ref")
    if not isinstance(evaluator_ref, dict):
        raise ConfigError("SWE-Bench-like task manifest 缺少 evaluator_only_manifest_ref。")
    evaluator_path = Path(evaluator_ref.get("path", ""))
    try:
        evaluator_path.resolve().relative_to(evidence_root.resolve())
    except ValueError as exc:
        raise ConfigError("SWE-Bench-like evaluator evidence ref 不在 evidence dir 内。") from exc


def _inspect_real_repository_manifest(run_root: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != REAL_REPOSITORY_TASK_MANIFEST_VERSION:
        failures.append("real_repository_task_manifest schema_version 不匹配。")
        return
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        failures.append("real_repository_task_manifest tasks 缺失。")
        return
    if len(tasks) < 3:
        failures.append("真实 repository-level task 少于 3 个。")
    if payload.get("task_count") != len(tasks):
        failures.append("real_repository_task_manifest task_count 与 tasks 数量不一致。")
    source_fact_kinds: list[str] = []
    source_fact_hashes: list[str] = []
    for task in tasks:
        for field in ("task_id", "source_kind", "remote_url", "base_commit", "generated_task_ref", "source_facts_ref"):
            if not task.get(field):
                failures.append(f"真实仓库任务字段为空：{field}")
        _inspect_artifact_ref(run_root, task.get("generated_task_ref"), failures, "generated_task_ref")
        source_facts_path = _inspect_artifact_ref(run_root, task.get("source_facts_ref"), failures, "source_facts_ref")
        if source_facts_path is not None:
            source_facts = _read_source_facts_for_inspect(source_facts_path, failures, str(task.get("task_id")))
            if source_facts:
                source_fact_kinds.append(str(source_facts.get("source_kind")))
                source_fact_hashes.append(str(source_facts.get("source_tree_hash")))
                for field in ("source_kind", "remote_url", "base_commit", "source_tree_hash"):
                    if task.get(field) != source_facts.get(field):
                        failures.append(
                            f"real_repository manifest 与 source facts 字段不一致：{task.get('task_id')}:{field}"
                        )
                _inspect_artifact_ref(
                    run_root,
                    source_facts.get("local_materialization_ref"),
                    failures,
                    "local_materialization_ref",
                )
                _inspect_artifact_ref(
                    run_root,
                    source_facts.get("verifier_evidence_ref"),
                    failures,
                    "verifier_evidence_ref",
                )
        _inspect_artifact_ref(run_root, task.get("verifier_evidence_ref"), failures, "verifier_evidence_ref")
    public_count = source_fact_kinds.count("public_archive")
    if payload.get("public_archive_count") != public_count:
        failures.append("real_repository_task_manifest public_archive_count 与 source facts 不一致。")
    if public_count < 1:
        failures.append("真实 repository-level task 缺少公开固定 archive 来源。")
    if payload.get("unique_source_tree_hash_count") != len(set(source_fact_hashes)):
        failures.append("real_repository_task_manifest unique_source_tree_hash_count 与 source facts 不一致。")
    if len(set(source_fact_hashes)) != len(source_fact_hashes):
        failures.append("真实 repository-level task 存在重复 source_tree_hash。")
    if source_fact_kinds and source_fact_kinds.count("fixed_local_mirror") == len(source_fact_kinds):
        failures.append("真实 repository-level task 不能全部来自本地 fixture。")


def _inspect_swebench_like_facts(run_root: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != SWEBENCH_LIKE_TASK_FACTS_MANIFEST_VERSION:
        failures.append("swebench_like_task_facts schema_version 不匹配。")
        return
    if payload.get("dataset_name") != EXPECTED_DATASET_NAME:
        failures.append("SWE-Bench-like dataset_name 不匹配。")
    if payload.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        failures.append("SWE-Bench-like dataset_revision 不匹配。")
    if tuple(payload.get("accepted_task_ids", [])) != EXPECTED_ACCEPTED_TASK_IDS:
        failures.append("SWE-Bench-like accepted task 集合不匹配。")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        failures.append("swebench_like_task_facts tasks 缺失。")
        return
    if len(tasks) != len(EXPECTED_ACCEPTED_TASK_IDS):
        failures.append("SWE-Bench-like task 数量不是 3。")
    for task in tasks:
        for field in (
            "instance_id",
            "repo",
            "base_commit",
            "environment_setup_commit",
            "test_patch_sha256",
            "fail_to_pass_selectors_sha256",
            "pass_to_pass_selectors_sha256",
            "generated_task_ref",
            "facts_ref",
        ):
            if not task.get(field):
                failures.append(f"SWE-Bench-like task 字段为空：{field}")
        if int(task.get("fail_to_pass_selector_count", 0)) < 1:
            failures.append(f"SWE-Bench-like F2P selector 计数为空：{task.get('instance_id')}")
        if int(task.get("pass_to_pass_selector_count", 0)) < 1:
            failures.append(f"SWE-Bench-like P2P selector 计数为空：{task.get('instance_id')}")
        _inspect_artifact_ref(run_root, task.get("generated_task_ref"), failures, "generated_task_ref")
        _inspect_artifact_ref(run_root, task.get("facts_ref"), failures, "facts_ref")
    _inspect_artifact_ref(run_root, payload.get("adapter_input_ref"), failures, "adapter_input_ref")
    _inspect_artifact_ref(run_root, payload.get("task_input_manifest_ref"), failures, "task_input_manifest_ref")
    _inspect_artifact_ref(
        run_root,
        payload.get("evaluator_evidence_manifest_ref"),
        failures,
        "evaluator_evidence_manifest_ref",
    )


def _inspect_task_adapter_facts(run_root: Path, payload: dict[str, Any], failures: list[str]) -> None:
    if payload.get("schema_version") != TASK_ADAPTER_FACTS_MANIFEST_VERSION:
        failures.append("task_adapter_facts schema_version 不匹配。")
        return
    facts = payload.get("facts")
    if not isinstance(facts, list):
        failures.append("task_adapter_facts facts 缺失。")
        return
    if len(facts) < 6:
        failures.append("task_adapter_facts 必须覆盖 3 个真实仓库和 3 个 SWE-Bench-like task。")
    adapter_names = {fact.get("adapter_name") for fact in facts if isinstance(fact, dict)}
    if "real_repository" not in adapter_names or "swebench_like_fixed" not in adapter_names:
        failures.append("task_adapter_facts 必须同时包含 real_repository 和 swebench_like_fixed adapter。")
    for fact in facts:
        if not isinstance(fact, dict):
            failures.append("task_adapter_facts entry 必须是 object。")
            continue
        try:
            TaskAdapterFacts.model_validate(fact)
        except ValidationError as exc:
            failures.append(f"task_adapter_facts entry 无效：{exc}")
            continue
        _inspect_artifact_ref(run_root, fact.get("input_manifest_ref"), failures, "input_manifest_ref")
        _inspect_artifact_ref(run_root, fact.get("output_task_ref"), failures, "output_task_ref")
        _inspect_artifact_ref(run_root, fact.get("visibility_policy_ref"), failures, "visibility_policy_ref")


def _inspect_artifact_ref(
    run_root: Path,
    value: Any,
    failures: list[str],
    label: str,
) -> Path | None:
    if not isinstance(value, dict):
        failures.append(f"{label} 缺少 ArtifactRef。")
        return None
    try:
        ref = ArtifactRef.model_validate(value)
    except ValidationError as exc:
        failures.append(f"{label} ArtifactRef 无效：{exc}")
        return None
    path = _resolve_ref_path(run_root, ref.relative_path)
    if path is None:
        failures.append(f"{label} 引用的路径不存在：{ref.relative_path}")
        return None
    if path.is_dir():
        actual_sha = compute_source_tree_hash(path)
        actual_size = 0
    else:
        actual_sha = compute_file_sha256(path)
        actual_size = path.stat().st_size
    if actual_sha != ref.sha256:
        failures.append(f"{label} sha256 不匹配：{ref.relative_path}")
    if actual_size != ref.size_bytes:
        failures.append(f"{label} size_bytes 不匹配：{ref.relative_path}")
    return path


def _read_source_facts_for_inspect(path: Path, failures: list[str], task_id: str) -> dict[str, Any] | None:
    try:
        payload = _read_json(path)
        RealRepositorySourceFacts.model_validate(payload)
    except (ConfigError, ValidationError) as exc:
        failures.append(f"real_repository source facts 无效：{task_id}: {exc}")
        return None
    return payload


def _resolve_ref_path(run_root: Path, relative_path: str) -> Path | None:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return None
    for base in (run_root, Path.cwd()):
        path = base / candidate
        if path.exists():
            return path
    return None


def _inspect_result(run_root: Path, failures: list[str], assert_complete: bool) -> str:
    payload = {
        "schema_version": TASK_SET_INSPECT_REPORT_VERSION,
        "run_dir": str(run_root),
        "status": "failed" if failures else "passed",
        "checks": [] if failures else ["v3_task_set=complete"],
        "failures": failures,
    }
    if failures and assert_complete:
        raise ConfigError("V3 task set 检查失败：" + "; ".join(failures))
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        return _read_json(path)
    except ConfigError as exc:
        failures.append(str(exc))
        return {}


def _validate_task_definition(payload: dict[str, Any], task_id: str) -> None:
    try:
        TaskDefinition.model_validate(payload)
    except ValidationError as exc:
        raise ConfigError(f"adapter 生成的 TaskDefinition 无效：{task_id}: {exc}") from exc


def _default_timeouts() -> dict[str, int]:
    return {
        "setup_timeout_sec": 300,
        "test_timeout_sec": 300,
        "agent_timeout_sec": 900,
        "final_verifier_timeout_sec": 600,
    }


def _default_environment(source_archive_sha256: str | None) -> dict[str, Any]:
    return {
        "execution_image": "python:3.12-slim",
        "python_version": "3.12",
        "node_version": None,
        "package_manager": "pip",
        "lockfile_hashes": [],
        "setup_cache_key_inputs": [],
        "required_system_packages": [],
        "setup_network_policy": "deny",
        "source_archive_sha256": source_archive_sha256,
    }


def _default_visibility() -> dict[str, str]:
    return {
        "issue": "model_visible",
        "expected_files": "model_visible",
        "fail_to_pass_tests": "verifier_only",
        "pass_to_pass_tests": "verifier_only",
        "gold_patch": "hidden_reference",
        "decontamination": "reward_only",
    }


def _archive_source_tree_hash(archive: Path, expected_root_directory: str) -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                _reject_unsafe_tar_member(member)
            tar.extractall(temp_dir, filter="data")
        root = Path(temp_dir) / expected_root_directory
        if not root.exists() or not root.is_dir():
            raise ConfigError(f"公开仓库归档缺少 expected root：{expected_root_directory}")
        return compute_source_tree_hash(root)


def _reject_unsafe_tar_member(member: tarfile.TarInfo) -> None:
    name = Path(member.name)
    if name.is_absolute() or ".." in name.parts:
        raise ConfigError(f"公开仓库归档包含不安全路径：{member.name}")


def _require_non_empty(record: dict[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if record.get(field) in (None, "", [], {})]
    if missing:
        raise ConfigError("任务输入字段为空：" + ", ".join(missing))


def _assert_named_sha256_sidecar(path: Path) -> None:
    sidecar = Path(str(path) + ".sha256")
    if not sidecar.exists():
        raise ConfigError(f"sha256 sidecar 缺失：{sidecar}")
    digest = sidecar.read_text(encoding="utf-8").split()[0]
    if digest != compute_file_sha256(path):
        raise ConfigError(f"sha256 sidecar 不匹配：{sidecar}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"JSON 文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 文件无效：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"JSON 顶层必须是 object：{path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ConfigError(f"JSONL 文件不存在：{path}")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"JSONL 第 {line_number} 行无效：{path}") from exc
        if not isinstance(row, dict):
            raise ConfigError(f"JSONL 第 {line_number} 行必须是 object：{path}")
        rows.append(row)
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _artifact_ref(
    path: Path,
    *,
    artifact_id: str,
    kind: str,
    base_dir: Path | None = None,
) -> ArtifactRef:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = compute_file_sha256(path)
        size_bytes = path.stat().st_size
    relative_path = _relative_path(path, base_dir)
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=relative_path,
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status="not_required",
        retention_policy="keep",
    )


def _artifact_ref_from_input_ref(
    value: dict[str, Any],
    *,
    artifact_id: str,
    kind: str,
) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=str(value["path"]),
        kind=kind,
        sha256=str(value["sha256"]),
        size_bytes=int(value["size_bytes"]),
        redaction_status="not_required",
        retention_policy="keep",
    )


def _relative_path(path: Path, base_dir: Path | None = None) -> str:
    resolved = path.resolve()
    candidates = [base_dir.resolve()] if base_dir is not None else []
    candidates.append(Path.cwd().resolve())
    for base in candidates:
        try:
            return resolved.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


def _path_for_generated_task(path: Path, task_dir: Path) -> str:
    target = path if path.is_absolute() else Path.cwd() / path
    return os.path.relpath(target.resolve(), start=task_dir.resolve()).replace(os.sep, "/")


def _sha256_json(value: Any) -> str:
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
