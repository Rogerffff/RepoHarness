"""V3 fixed source materialization and verifier patch preparation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from repo_harness.errors import ConfigError
from repo_harness.tasks import RunnableTask, TaskDefinition, load_task
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_swebench_fixture import (
    EXPECTED_ACCEPTED_TASK_IDS,
    EXPECTED_DATASET_NAME,
    EXPECTED_DATASET_REVISION,
    EXPECTED_DATASET_SPLIT,
)
from repo_harness.workspace.materialization import materialize_source
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

SOURCE_ARCHIVE_MANIFEST_VERSION = "repo_harness_v3_swebench_like_source_archive_manifest_v0"
SOURCE_CHECKOUT_FACTS_MANIFEST_VERSION = "repo_harness_source_checkout_facts_manifest_v3_v0"
SOURCE_MATERIALIZATION_REPORT_VERSION = "repo_harness_source_materialization_report_v3_v0"
SOURCE_MATERIALIZATION_INSPECT_VERSION = "repo_harness_source_materialization_inspect_v3_v0"


def build_v3_source_materialization(
    *,
    task_set_dir: str | Path,
    swebench_source_manifest: str | Path,
    hidden_verifier_inputs: str | Path,
    output_dir: str | Path,
) -> Path:
    """Materialize fixed sources and prepare verifier-only patched workspaces."""

    task_set_root = Path(task_set_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    source_manifest_path = Path(swebench_source_manifest)
    hidden_inputs_path = Path(hidden_verifier_inputs)
    source_manifest = _read_json(source_manifest_path)
    _assert_source_archive_manifest(source_manifest)
    hidden_rows = _read_jsonl(hidden_inputs_path)
    hidden_by_id = {row["instance_id"]: row for row in hidden_rows}
    source_by_id = {row["instance_id"]: row for row in source_manifest["archives"]}

    entries: list[dict[str, Any]] = []
    for task_path in sorted((task_set_root / "generated_tasks" / "real_repository").glob("*.yaml")):
        loaded = load_task(task_path)
        source_provenance = _real_repository_source_provenance(
            task_set_root=task_set_root,
            task=loaded.runnable_task,
        )
        entries.append(
            _materialize_task(
                output_root=output_root,
                task=loaded.runnable_task,
                task_path=task_path,
                task_category="real_repository",
                verifier_patch_text=None,
                verifier_patch_visibility="not_applicable",
                source_provenance=source_provenance,
                source_manifest_ref=None,
            )
        )

    for task_path in sorted((task_set_root / "generated_tasks" / "swebench_like").glob("*.yaml")):
        payload = yaml.safe_load(task_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ConfigError(f"SWE-Bench-like generated task YAML 无效：{task_path}")
        instance_id = payload["id"]
        source_row = source_by_id.get(instance_id)
        hidden_row = hidden_by_id.get(instance_id)
        if source_row is None:
            raise ConfigError(f"SWE-Bench-like source archive manifest 缺少任务：{instance_id}")
        if hidden_row is None:
            raise ConfigError(f"hidden verifier inputs 缺少任务：{instance_id}")
        task = _swebench_task_with_source(payload, source_row)
        entries.append(
            _materialize_task(
                output_root=output_root,
                task=task,
                task_path=task_path,
                task_category="swebench_like",
                verifier_patch_text=hidden_row["test_patch"],
                verifier_patch_visibility="evaluator_only",
                source_provenance=_swebench_source_provenance(source_row),
                source_manifest_ref=_artifact_ref(
                    source_manifest_path,
                    artifact_id="swebench_source_archive_manifest",
                    kind="json",
                ),
            )
        )

    checkout_manifest = {
        "schema_version": SOURCE_CHECKOUT_FACTS_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "entry_count": len(entries),
        "entries": [
            {
                "task_id": entry["task_id"],
                "task_category": entry["task_category"],
                "source_type": entry["source_type"],
                "remote_url": entry["remote_url"],
                "base_commit": entry["base_commit"],
                "resolved_commit": entry["resolved_commit"],
                "expected_source_tree_hash": entry["expected_source_tree_hash"],
                "source_checkout_facts_ref": entry["source_checkout_facts_ref"],
                "source_tree_hash": entry["source_tree_hash"],
                "agent_workspace_ref": entry["agent_workspace_ref"],
                "verifier_workspace_ref": entry["verifier_workspace_ref"],
            }
            for entry in entries
        ],
    }
    checkout_manifest_path = output_root / "source_checkout_facts.json"
    _write_json(checkout_manifest_path, checkout_manifest)

    report = {
        "schema_version": SOURCE_MATERIALIZATION_REPORT_VERSION,
        "generated_at": _utc_timestamp(),
        "task_count": len(entries),
        "formal_run_network_source_allowed": False,
        "source_checkout_facts_ref": _artifact_ref(
            checkout_manifest_path,
            artifact_id="source_checkout_facts",
            kind="json",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "swebench_source_manifest_ref": _artifact_ref(
            source_manifest_path,
            artifact_id="swebench_source_archive_manifest",
            kind="json",
        ).model_dump(mode="json"),
        "hidden_verifier_inputs_ref": _artifact_ref(
            hidden_inputs_path,
            artifact_id="hidden_verifier_inputs",
            kind="jsonl",
        ).model_dump(mode="json"),
        "entries": entries,
        "contamination_policy": {
            "agent_workspace_contains_verifier_patch": False,
            "raw_test_patch_model_visible": False,
            "verifier_patch_visibility": "evaluator_only",
        },
    }
    _write_json(output_root / "source_materialization_report.json", report)
    return output_root


def inspect_v3_source_materialization(
    run_dir: str | Path,
    *,
    report: str | Path,
    assert_complete: bool = False,
) -> str:
    """Inspect V3 source materialization outputs."""

    run_root = Path(run_dir)
    failures: list[str] = []
    report_path = Path(report)
    payload = _read_json_for_inspect(report_path, failures)
    if failures:
        return _inspect_result(run_root, failures, assert_complete)
    if payload.get("schema_version") != SOURCE_MATERIALIZATION_REPORT_VERSION:
        failures.append("source_materialization_report schema_version 不匹配。")
    if payload.get("formal_run_network_source_allowed") is not False:
        failures.append("正式 V3 source materialization 不允许浮动网络 source。")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) < 6:
        failures.append("source_materialization_report 必须包含 3 个真实仓库和 3 个 SWE-Bench-like task。")
        entries = []
    checkout_ref = payload.get("source_checkout_facts_ref")
    checkout_path = _inspect_artifact_ref(run_root, checkout_ref, failures, "source_checkout_facts_ref")
    if checkout_path is not None:
        checkout_manifest = _read_json_for_inspect(checkout_path, failures)
        if checkout_manifest.get("entry_count") != len(entries):
            failures.append("source_checkout_facts entry_count 与 report entries 不一致。")
    _inspect_artifact_ref(
        run_root,
        payload.get("swebench_source_manifest_ref"),
        failures,
        "swebench_source_manifest_ref",
    )
    for entry in entries:
        _inspect_materialization_entry(run_root, entry, failures)
    return _inspect_result(run_root, failures, assert_complete)


def _materialize_task(
    *,
    output_root: Path,
    task: RunnableTask,
    task_path: Path,
    task_category: str,
    verifier_patch_text: str | None,
    verifier_patch_visibility: str,
    source_provenance: dict[str, Any],
    source_manifest_ref: ArtifactRef | None,
) -> dict[str, Any]:
    task_id = task.task_id
    task_root = output_root / "tasks" / task_id
    source_checkout = materialize_source(task, task_root / "source_checkout")
    expected_source_tree_hash = source_provenance["expected_source_tree_hash"]
    if source_checkout.facts.source_tree_hash != expected_source_tree_hash:
        raise ConfigError(
            "source_tree_hash 不匹配："
            f"{task_id} expected {expected_source_tree_hash}, got {source_checkout.facts.source_tree_hash}"
        )
    agent_workspace = task_root / "agent_workspace"
    verifier_workspace = task_root / "verifier_workspace"
    _copy_tree(source_checkout.root, agent_workspace)
    _copy_tree(source_checkout.root, verifier_workspace)
    task_definition_snapshot = task_root / "task_definition.yaml"
    shutil.copyfile(task_path, task_definition_snapshot)
    source_provenance_path = task_root / "source_provenance.json"
    _write_json(source_provenance_path, source_provenance)

    verifier_patch_ref: ArtifactRef | None = None
    verifier_patch_applied = False
    patch_apply = {"status": "not_applicable", "exit_code": None, "stderr_sha256": None}
    agent_contains_patch = False
    if verifier_patch_text:
        patch_path = task_root / "evaluator_only" / "verifier.patch"
        patch_path.parent.mkdir(parents=True, exist_ok=True)
        patch_path.write_text(verifier_patch_text, encoding="utf-8")
        verifier_patch_ref = _artifact_ref(
            patch_path,
            artifact_id=f"{task_id}_verifier_patch",
            kind="patch",
            base_dir=output_root,
            redaction_status="evaluator_only",
        )
        result = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", patch_path.resolve().as_posix()],
            cwd=verifier_workspace,
            env=_patch_apply_environment(verifier_workspace),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        verifier_patch_applied = result.returncode == 0
        patch_apply = {
            "status": "passed" if verifier_patch_applied else "failed",
            "exit_code": result.returncode,
            "stdout_sha256": _sha256_text(result.stdout),
            "stderr_sha256": _sha256_text(result.stderr),
        }
        agent_contains_patch = _directory_contains_text(agent_workspace, verifier_patch_text)
    facts_path = task_root / "source_checkout_facts.json"
    _write_json(facts_path, source_checkout.facts.model_dump(mode="json"))
    source_checkout_facts = source_checkout.facts
    return {
        "task_id": task_id,
        "task_category": task_category,
        "task_definition_ref": _artifact_ref(
            task_definition_snapshot,
            artifact_id=f"{task_id}_task_definition",
            kind="yaml",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "source_provenance_kind": source_provenance["source_provenance_kind"],
        "source_provenance_ref": _artifact_ref(
            source_provenance_path,
            artifact_id=f"{task_id}_source_provenance",
            kind="json",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "source_type": source_checkout.facts.source_type,
        "source_kind": source_checkout.facts.source_kind,
        "remote_url": source_checkout_facts.remote_url or source_provenance.get("remote_url"),
        "mirror_source": source_checkout_facts.mirror_source or source_provenance.get("mirror_source"),
        "base_commit": source_checkout.facts.base_commit,
        "resolved_commit": source_checkout_facts.resolved_commit or source_checkout.facts.base_commit,
        "archive_sha256": source_checkout.facts.source_archive_sha256,
        "mirror_sha256": source_checkout_facts.mirror_sha256 or source_provenance.get("mirror_sha256"),
        "source_tree_hash": source_checkout.facts.source_tree_hash,
        "expected_source_tree_hash": expected_source_tree_hash,
        "checkout_path_status": source_checkout.facts.checkout_path_status,
        "remotes_stripped": source_checkout.facts.remotes_stripped,
        "branches_stripped": source_checkout.facts.branches_stripped,
        "tags_stripped": source_checkout.facts.tags_stripped,
        "materialization_command_facts": source_checkout_facts.materialization_command_facts,
        "source_checkout_facts_ref": _artifact_ref(
            facts_path,
            artifact_id=f"{task_id}_source_checkout_facts",
            kind="json",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "source_checkout_ref": _artifact_ref(
            source_checkout.root,
            artifact_id=f"{task_id}_source_checkout",
            kind="source_directory",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "agent_workspace_ref": _artifact_ref(
            agent_workspace,
            artifact_id=f"{task_id}_agent_workspace",
            kind="source_directory",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "verifier_workspace_ref": _artifact_ref(
            verifier_workspace,
            artifact_id=f"{task_id}_verifier_workspace",
            kind="source_directory",
            base_dir=output_root,
        ).model_dump(mode="json"),
        "verifier_patch_ref": verifier_patch_ref.model_dump(mode="json") if verifier_patch_ref else None,
        "verifier_patch_visibility": verifier_patch_visibility,
        "verifier_patch_applied": verifier_patch_applied,
        "verifier_patch_apply": patch_apply,
        "agent_workspace_contains_verifier_patch": agent_contains_patch,
        "source_manifest_ref": source_manifest_ref.model_dump(mode="json") if source_manifest_ref else None,
    }


def _real_repository_source_provenance(*, task_set_root: Path, task: RunnableTask) -> dict[str, Any]:
    facts_path = task_set_root / "real_repository_source_facts" / f"{task.task_id}.json"
    facts = _read_json(facts_path)
    if facts.get("source_tree_hash") != task.metadata.get("source_tree_hash"):
        raise ConfigError(f"真实仓库 source_tree_hash 与阶段 4 task metadata 不一致：{task.task_id}")
    if facts.get("base_commit") != task.base_commit:
        raise ConfigError(f"真实仓库 base_commit 与阶段 4 task metadata 不一致：{task.task_id}")
    if facts.get("network_source_allowed_for_formal_run") is not False:
        raise ConfigError(f"真实仓库正式 source materialization 不能允许浮动网络 source：{task.task_id}")
    if not (facts.get("archive_sha256") or facts.get("mirror_sha256")):
        raise ConfigError(f"真实仓库 source facts 缺少 archive_sha256 或 mirror_sha256：{task.task_id}")
    if facts.get("source_kind") == "fixed_local_mirror" and facts.get("mirror_sha256") != facts.get("source_tree_hash"):
        raise ConfigError(f"固定本地 mirror source_tree_hash 与 mirror_sha256 不一致：{task.task_id}")
    if facts.get("source_kind") == "public_archive" and not facts.get("archive_sha256"):
        raise ConfigError(f"公开仓库 source facts 缺少 archive_sha256：{task.task_id}")
    return {
        "source_provenance_kind": "real_repository_source_facts",
        "task_id": task.task_id,
        "source_kind": facts["source_kind"],
        "remote_url": facts["remote_url"],
        "base_commit": facts["base_commit"],
        "resolved_commit": facts["base_commit"],
        "dataset_source_revision": facts.get("dataset_source_revision"),
        "archive_sha256": facts.get("archive_sha256"),
        "mirror_sha256": facts.get("mirror_sha256"),
        "expected_source_tree_hash": facts["source_tree_hash"],
        "network_source_allowed_for_formal_run": facts["network_source_allowed_for_formal_run"],
        "local_materialization_ref": facts["local_materialization_ref"],
        "verifier_evidence_ref": facts["verifier_evidence_ref"],
    }


def _swebench_source_provenance(source_row: dict[str, Any]) -> dict[str, Any]:
    _require_sha256(source_row, "source_tree_hash")
    return {
        "source_provenance_kind": "swebench_source_archive_manifest",
        "task_id": source_row["instance_id"],
        "instance_id": source_row["instance_id"],
        "repo": source_row["repo"],
        "remote_url": source_row["remote_url"],
        "base_commit": source_row["base_commit"],
        "resolved_commit": source_row["base_commit"],
        "mirror_source": "predownloaded_public_archive",
        "archive_sha256": source_row["archive_sha256"],
        "expected_source_tree_hash": source_row["source_tree_hash"],
        "expected_root_directory": source_row["expected_root_directory"],
        "network_source_allowed_for_formal_run": False,
    }


def _swebench_task_with_source(payload: dict[str, Any], source_row: dict[str, Any]) -> RunnableTask:
    for field in (
        "instance_id",
        "repo",
        "base_commit",
        "archive_path",
        "archive_sha256",
        "expected_root_directory",
        "source_tree_hash",
    ):
        if not source_row.get(field):
            raise ConfigError(f"SWE-Bench-like source manifest 字段为空：{field}")
    if source_row["instance_id"] != payload["id"]:
        raise ConfigError("SWE-Bench-like source manifest instance_id 与 task 不一致。")
    if source_row["repo"] != payload["repo"]:
        raise ConfigError("SWE-Bench-like source manifest repo 与 task 不一致。")
    if source_row["base_commit"] != payload["base_commit"]:
        raise ConfigError("SWE-Bench-like source manifest base_commit 与 task 不一致。")
    archive_path = Path(source_row["archive_path"])
    if compute_file_sha256(archive_path) != source_row["archive_sha256"]:
        raise ConfigError(f"SWE-Bench-like source archive sha256 不匹配：{archive_path}")
    payload = dict(payload)
    payload["metadata"] = {**payload.get("metadata", {}), "source_tree_hash": source_row["source_tree_hash"]}
    payload["repo"] = source_row["archive_path"]
    payload["source_archive_sha256"] = source_row["archive_sha256"]
    payload["repo_source_spec"] = {
        "source_type": "public_snapshot",
        "remote_url": source_row["remote_url"],
        "commit_sha": source_row["base_commit"],
        "mirror_source": "predownloaded_public_archive",
        "archive_sha256": source_row["archive_sha256"],
        "archive_path": source_row["archive_path"],
        "expected_root_directory": source_row["expected_root_directory"],
        "decontamination_status": "fixed_swebench_like_source_archive",
        "remotes_stripped": True,
        "branches_stripped": True,
        "tags_stripped": True,
    }
    definition = TaskDefinition.model_validate(payload)
    return RunnableTask.from_definition(definition)


def _assert_source_archive_manifest(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SOURCE_ARCHIVE_MANIFEST_VERSION:
        raise ConfigError("SWE-Bench-like source archive manifest schema_version 不匹配。")
    if payload.get("dataset_name") != EXPECTED_DATASET_NAME:
        raise ConfigError("SWE-Bench-like source archive manifest dataset_name 不匹配。")
    if payload.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        raise ConfigError("SWE-Bench-like source archive manifest dataset_revision 不匹配。")
    if payload.get("dataset_split") != EXPECTED_DATASET_SPLIT:
        raise ConfigError("SWE-Bench-like source archive manifest dataset_split 不匹配。")
    if payload.get("formal_run_network_source_allowed") is not False:
        raise ConfigError("正式 V3 source archive manifest 不能允许浮动网络 source。")
    archives = payload.get("archives")
    if not isinstance(archives, list):
        raise ConfigError("SWE-Bench-like source archive manifest 缺少 archives。")
    ids = [row.get("instance_id") for row in archives]
    if tuple(ids) != EXPECTED_ACCEPTED_TASK_IDS:
        raise ConfigError("SWE-Bench-like source archive manifest accepted task 集合不匹配。")
    for row in archives:
        _require_sha256(row, "archive_sha256")
        _require_sha256(row, "source_tree_hash")


def _require_sha256(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ConfigError(f"source manifest {field} 必须是 sha256。")


def _inspect_materialization_entry(run_root: Path, entry: dict[str, Any], failures: list[str]) -> None:
    task_id = entry.get("task_id")
    required_fields = (
        "task_id",
        "task_category",
        "source_tree_hash",
        "expected_source_tree_hash",
        "source_checkout_facts_ref",
        "source_checkout_ref",
        "source_provenance_ref",
        "task_definition_ref",
        "agent_workspace_ref",
        "remote_url",
        "base_commit",
        "resolved_commit",
        "materialization_command_facts",
    )
    for field in required_fields:
        if not entry.get(field):
            failures.append(f"source materialization entry 字段为空：{task_id}:{field}")
    if entry.get("source_tree_hash") != entry.get("expected_source_tree_hash"):
        failures.append(f"source_tree_hash 未绑定固定 provenance：{task_id}")
    task_definition_path = _inspect_artifact_ref(
        run_root,
        entry.get("task_definition_ref"),
        failures,
        "task_definition_ref",
    )
    provenance_path = _inspect_artifact_ref(
        run_root,
        entry.get("source_provenance_ref"),
        failures,
        "source_provenance_ref",
    )
    if provenance_path is not None:
        provenance = _read_json_for_inspect(provenance_path, failures)
        _inspect_source_provenance(entry, provenance, failures)
    facts_path = _inspect_artifact_ref(
        run_root,
        entry.get("source_checkout_facts_ref"),
        failures,
        "source_checkout_facts_ref",
    )
    if facts_path is not None:
        facts = _read_json_for_inspect(facts_path, failures)
        if facts.get("source_tree_hash") != entry.get("source_tree_hash"):
            failures.append(f"source checkout facts 与 report source_tree_hash 不一致：{task_id}")
        if facts.get("source_tree_hash") != entry.get("expected_source_tree_hash"):
            failures.append(f"source checkout facts 未绑定 expected_source_tree_hash：{task_id}")
        if facts.get("checkout_path_status") != "redacted":
            failures.append(f"source checkout facts 必须 redacted checkout path：{task_id}")
        if not facts.get("base_commit") and not facts.get("synthetic_base_id"):
            failures.append(f"source checkout facts 缺少 base identity：{task_id}")
        if facts.get("remote_url") != entry.get("remote_url"):
            failures.append(f"source checkout facts remote_url 与 report 不一致：{task_id}")
        if facts.get("resolved_commit") != entry.get("resolved_commit"):
            failures.append(f"source checkout facts resolved_commit 与 report 不一致：{task_id}")
        if facts.get("materialization_command_facts") != entry.get("materialization_command_facts"):
            failures.append(f"source checkout facts materialization command facts 与 report 不一致：{task_id}")
        command_facts = facts.get("materialization_command_facts")
        if not isinstance(command_facts, dict) or command_facts.get("network_used") is not False:
            failures.append(f"source checkout facts 必须记录未使用网络的 materialization command facts：{task_id}")
        if not (facts.get("source_archive_sha256") or facts.get("mirror_sha256")):
            failures.append(f"source checkout facts 缺少固定 archive 或 mirror 证据：{task_id}")
        if facts.get("source_type") == "fixed_local_mirror" and facts.get("mirror_sha256") != facts.get("source_tree_hash"):
            failures.append(f"fixed_local_mirror mirror_sha256 与 source_tree_hash 不一致：{task_id}")
    agent_path = _inspect_artifact_ref(run_root, entry.get("agent_workspace_ref"), failures, "agent_workspace_ref")
    source_checkout_path = _inspect_artifact_ref(
        run_root,
        entry.get("source_checkout_ref"),
        failures,
        "source_checkout_ref",
    )
    verifier_path = _inspect_artifact_ref(
        run_root,
        entry.get("verifier_workspace_ref"),
        failures,
        "verifier_workspace_ref",
    )
    if agent_path is not None and compute_source_tree_hash(agent_path) != entry.get("source_tree_hash"):
        failures.append(f"agent workspace source hash 与 base source 不一致：{task_id}")
    if entry.get("task_category") == "swebench_like":
        patch_path = None
        if entry.get("verifier_patch_visibility") != "evaluator_only":
            failures.append(f"SWE-Bench-like verifier patch 必须 evaluator_only：{task_id}")
        if entry.get("verifier_patch_applied") is not True:
            failures.append(f"SWE-Bench-like verifier patch 未应用：{task_id}")
        patch_path = _inspect_artifact_ref(run_root, entry.get("verifier_patch_ref"), failures, "verifier_patch_ref")
        if entry.get("agent_workspace_contains_verifier_patch"):
            failures.append(f"agent workspace 包含 verifier patch 内容：{task_id}")
        if patch_path is not None:
            markers = _patch_leak_markers(patch_path.read_text(encoding="utf-8"))
            if source_checkout_path is not None:
                markers = [
                    marker
                    for marker in markers
                    if not _directory_contains_any_text(source_checkout_path, [marker])
                ]
            if agent_path is not None and _directory_contains_any_text(agent_path, markers):
                failures.append(f"agent workspace 包含 verifier patch 内容：{task_id}")
            task_definition_markers = _raw_patch_markers(patch_path.read_text(encoding="utf-8"))
            if task_definition_path is not None and _file_contains_any_text(task_definition_path, task_definition_markers):
                failures.append(f"task definition 包含 verifier patch 内容：{task_id}")
        if verifier_path is not None and compute_source_tree_hash(verifier_path) == entry.get("source_tree_hash"):
            failures.append(f"verifier workspace 未体现 verifier patch 变更：{task_id}")


def _inspect_source_provenance(
    entry: dict[str, Any],
    provenance: dict[str, Any],
    failures: list[str],
) -> None:
    task_id = entry.get("task_id")
    if provenance.get("source_provenance_kind") != entry.get("source_provenance_kind"):
        failures.append(f"source provenance kind 与 report 不一致：{task_id}")
    for field in ("remote_url", "base_commit", "resolved_commit", "expected_source_tree_hash"):
        if provenance.get(field) != entry.get(field):
            failures.append(f"source provenance {field} 与 report 不一致：{task_id}")
    if provenance.get("expected_source_tree_hash") != entry.get("source_tree_hash"):
        failures.append(f"source provenance source_tree_hash 与 materialized source 不一致：{task_id}")
    if provenance.get("network_source_allowed_for_formal_run") is not False:
        failures.append(f"source provenance 不能允许浮动网络 source：{task_id}")
    if entry.get("source_provenance_kind") == "real_repository_source_facts":
        if not (provenance.get("archive_sha256") or provenance.get("mirror_sha256")):
            failures.append(f"真实仓库 source provenance 缺少 archive 或 mirror sha256：{task_id}")
        if entry.get("archive_sha256") != provenance.get("archive_sha256"):
            failures.append(f"真实仓库 archive_sha256 与 source provenance 不一致：{task_id}")
        if entry.get("mirror_sha256") != provenance.get("mirror_sha256"):
            failures.append(f"真实仓库 mirror_sha256 与 source provenance 不一致：{task_id}")
    if entry.get("source_provenance_kind") == "swebench_source_archive_manifest":
        if provenance.get("archive_sha256") != entry.get("archive_sha256"):
            failures.append(f"SWE-Bench-like archive_sha256 与 source provenance 不一致：{task_id}")
        if provenance.get("instance_id") != task_id:
            failures.append(f"SWE-Bench-like source provenance instance_id 不一致：{task_id}")


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def _patch_apply_environment(workspace: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CEILING_DIRECTORIES"] = workspace.parent.resolve().as_posix()
    return env


def _directory_contains_text(root: Path, needle: str) -> bool:
    if not needle:
        return False
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            if needle in path.read_text(encoding="utf-8"):
                return True
        except UnicodeDecodeError:
            continue
    return False


def _directory_contains_any_text(root: Path, needles: list[str]) -> bool:
    if not needles:
        return False
    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if _file_contains_any_text(path, needles):
            return True
    return False


def _file_contains_any_text(path: Path, needles: list[str]) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(needle and needle in text for needle in needles)


def _patch_leak_markers(patch_text: str) -> list[str]:
    markers: set[str] = set()
    stripped_patch = patch_text.strip()
    if stripped_patch:
        markers.add(stripped_patch)
    for line in patch_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        marker = line[1:].strip()
        if len(marker) >= 16:
            markers.add(marker)
    return sorted(markers, key=len, reverse=True)


def _raw_patch_markers(patch_text: str) -> list[str]:
    markers: set[str] = set()
    stripped_patch = patch_text.strip()
    if stripped_patch:
        markers.add(stripped_patch)
    for line in patch_text.splitlines():
        if line.startswith(("diff --git ", "+++ ", "--- ", "@@ ")):
            markers.add(line.strip())
    return sorted(markers, key=len, reverse=True)


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
        failures.append(f"{label} 引用路径不存在：{ref.relative_path}")
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


def _resolve_ref_path(run_root: Path, relative_path: str) -> Path | None:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return None
    for base in (run_root, Path.cwd()):
        path = base / candidate
        if path.exists():
            return path
    return None


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


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        return _read_json(path)
    except ConfigError as exc:
        failures.append(str(exc))
        return {}


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


def _artifact_ref(
    path: Path,
    *,
    artifact_id: str,
    kind: str,
    base_dir: Path | None = None,
    redaction_status: str = "not_required",
) -> ArtifactRef:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = compute_file_sha256(path)
        size_bytes = path.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status=redaction_status,
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


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _inspect_result(run_root: Path, failures: list[str], assert_complete: bool) -> str:
    payload = {
        "schema_version": SOURCE_MATERIALIZATION_INSPECT_VERSION,
        "run_dir": str(run_root),
        "status": "failed" if failures else "passed",
        "checks": [] if failures else ["v3_source_materialization=complete"],
        "failures": failures,
    }
    if failures and assert_complete:
        raise ConfigError("V3 source materialization 检查失败：" + "; ".join(failures))
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
