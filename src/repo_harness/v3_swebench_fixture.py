"""V3 SWE-Bench-like fixture freezing and inspection."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError

V3_FEASIBILITY_INPUT_MANIFEST_VERSION = "repo_harness_v3_feasibility_input_manifest_v0"
V3_TASK_INPUT_MANIFEST_VERSION = "repo_harness_v3_swebench_like_task_input_manifest_v0"
V3_ADAPTER_INPUT_ROW_VERSION = "repo_harness_v3_swebench_like_adapter_input_v0"
V3_EVALUATOR_EVIDENCE_MANIFEST_VERSION = "repo_harness_v3_evaluator_evidence_manifest_v0"
V3_HIDDEN_VERIFIER_INPUT_VERSION = "repo_harness_v3_hidden_verifier_input_v0"

EXPECTED_DATASET_NAME = "princeton-nlp/SWE-bench_Lite"
EXPECTED_DATASET_REVISION = "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2"
EXPECTED_DATASET_SPLIT = "test"
EXPECTED_SWEBENCH_COMMIT = "f7bbbb2ccdf479001d6467c9e34af59e44a840f9"
EXPECTED_ENTRY_STATUS = "green_ready_for_v3_implementation_plan"
EXPECTED_ACCEPTED_TASK_IDS = (
    "pytest-dev__pytest-7220",
    "pytest-dev__pytest-8365",
    "sympy__sympy-24909",
)
EXPECTED_SOURCE_SHA256 = {
    "hf_dataset_schema": "09770b9bb43312074b0ca2c1eafd1c8d6c66837288441f28593f51fcef7d976d",
    "level2_dataset": "33932d6bccd5beec4aae19dbeaf8d60682d17c8e3b3f41b1bc66c5dcf646b9eb",
    "candidate_task_manifest": "4777a33715af8882e2757c784f088390833562ce6d078ed77a1e3abef26c7cb6",
    "selected_task_manifest": "eede45a11f3f38154392ef3681dc56491cc6679fc8e8def8ddc6ce4b72d044d8",
    "level2_gold_patch_predictions": "bef681f06d6d28288a5f61862156a197aab00b6e3dc3f403f3c453f0b99d0776",
    "level1_gold_patch_prediction_sha256": "82494f29a4b146146f497520357f85830b33f5a330437cf0ef284c1f7cb6da0c",
    "level2_gold_patch_predictions_sha256": "37728a681628e9476223d0503a0c657372f70e175f2a460e16744e4f44cab9b1",
    "level1_official_report": "e33fd8d2569d6859671a120862eca4f8c5f4c067fa50491e6f80613d36d553c6",
    "level2_official_report": "a7235aa65b2c1671bb716e5a8925f4d5c6f9c8f98286ef68d1f3e8dff3eaf844",
}

ADAPTER_INPUT_DIRNAME = "adapter_inputs"
EVALUATOR_ONLY_DIRNAME = "evaluator_only"
ADAPTER_TASKS_FILENAME = "swebench_like_tasks.jsonl"
TASK_INPUT_MANIFEST_FILENAME = "task_input_manifest.json"
V3_FEASIBILITY_MANIFEST_FILENAME = "v3_feasibility_input_manifest.json"
GOLD_PATCH_PREDICTIONS_FILENAME = "gold_patch_predictions.jsonl"
OFFICIAL_HARNESS_REPORTS_FILENAME = "official_harness_reports.json"
HIDDEN_VERIFIER_INPUTS_FILENAME = "hidden_verifier_inputs.jsonl"
EVALUATOR_EVIDENCE_MANIFEST_FILENAME = "evaluator_evidence_manifest.json"

FORBIDDEN_ADAPTER_FILENAMES = {
    GOLD_PATCH_PREDICTIONS_FILENAME,
    OFFICIAL_HARNESS_REPORTS_FILENAME,
    HIDDEN_VERIFIER_INPUTS_FILENAME,
}
FORBIDDEN_ADAPTER_KEYS = {
    "completed",
    "completed_id",
    "completed_ids",
    "completed_instance",
    "completed_instances",
    "patch",
    "test_patch",
    "FAIL_TO_PASS",
    "FAIL_TO_FAIL",
    "PASS_TO_PASS",
    "PASS_TO_FAIL",
    "gold_patch",
    "gold_patch_prediction",
    "gold_patch_predictions",
    "gold_patch_resolved",
    "model_patch",
    "official_harness",
    "official_harness_report",
    "official_harness_reports",
    "official_status",
    "official_report",
    "resolved",
    "resolved_id",
    "resolved_ids",
    "resolved_instance",
    "resolved_instances",
    "resolved_status",
    "submitted",
    "submitted_id",
    "submitted_ids",
    "submitted_instance",
    "submitted_instances",
    "unresolved",
    "unresolved_id",
    "unresolved_ids",
    "unresolved_instance",
    "unresolved_instances",
    "unresolved_status",
    "v3_candidate_status",
    "patch_exists",
    "patch_is_None",
    "patch_successfully_applied",
    "tests_status",
}
FORBIDDEN_ADAPTER_TERMS = {
    "completed",
    "completedids",
    "completed_ids",
    "completedinstances",
    "completed_instances",
    "fail_to_fail",
    "fail_to_pass",
    "gold_patch",
    "official_harness",
    "official_status",
    "pass_to_fail",
    "pass_to_pass",
    "resolved",
    "resolvedids",
    "resolved_ids",
    "resolvedinstances",
    "resolved_instances",
    "resolvedstatus",
    "submitted",
    "submittedids",
    "submitted_ids",
    "submittedinstances",
    "submitted_instances",
    "test_patch",
    "unresolved",
    "unresolvedids",
    "unresolved_ids",
    "unresolvedinstances",
    "unresolved_instances",
    "unresolvedstatus",
}
SOURCE_REQUIRED_FILES = {
    "hf_dataset_schema": "hf_dataset_schema.json",
    "level2_dataset": "dataset/level2_dataset.jsonl",
    "candidate_task_manifest": "candidate_task_manifest.json",
    "selected_task_manifest": "level2/selected_task_manifest.json",
    "level2_gold_patch_predictions": "level2/gold_patch_predictions.jsonl",
    "level1_gold_patch_prediction_sha256": "level1/gold_patch_prediction.sha256",
    "level2_gold_patch_predictions_sha256": "level2/gold_patch_predictions.sha256",
}


def prepare_v3_swebench_fixture(
    *,
    feasibility_root: str | Path,
    fixture_dir: str | Path,
    evidence_dir: str | Path,
) -> Path:
    """Freeze the Green-path SWE-Bench-like feasibility inputs for V3."""

    source_root = Path(feasibility_root)
    fixture_root = Path(fixture_dir)
    evidence_root = Path(evidence_dir)
    adapter_root = fixture_root / ADAPTER_INPUT_DIRNAME
    evaluator_root = evidence_root / EVALUATOR_ONLY_DIRNAME

    decision = _load_decision(source_root)
    _assert_green_decision(decision)
    schema = _assert_dataset_schema(source_root)
    source_files = _source_provenance_refs(source_root, decision)
    _assert_source_sha_files(source_root, decision, schema)

    rows = _read_jsonl(source_root / SOURCE_REQUIRED_FILES["level2_dataset"])
    selected_rows = _read_json(source_root / SOURCE_REQUIRED_FILES["selected_task_manifest"])
    if not isinstance(selected_rows, list):
        raise ConfigError("selected_task_manifest.json 顶层必须是 JSON array。")
    _assert_accepted_rows(rows, selected_rows, decision, schema)

    adapter_root.mkdir(parents=True, exist_ok=True)
    evaluator_root.mkdir(parents=True, exist_ok=True)

    sanitized_rows: list[dict[str, Any]] = []
    hidden_rows: list[dict[str, Any]] = []
    accepted_task_records: list[dict[str, Any]] = []
    for row in rows:
        task_record = _accepted_task_record(row)
        accepted_task_records.append(task_record)
        sanitized_rows.append(_adapter_visible_row(row, task_record))
        hidden_rows.append(_hidden_verifier_row(row, task_record))

    adapter_tasks_path = adapter_root / ADAPTER_TASKS_FILENAME
    _write_jsonl(adapter_tasks_path, sanitized_rows)

    hidden_inputs_path = evaluator_root / HIDDEN_VERIFIER_INPUTS_FILENAME
    _write_jsonl(hidden_inputs_path, hidden_rows)

    gold_predictions_path = evaluator_root / GOLD_PATCH_PREDICTIONS_FILENAME
    shutil.copyfile(source_root / SOURCE_REQUIRED_FILES["level2_gold_patch_predictions"], gold_predictions_path)

    official_reports_path = evaluator_root / OFFICIAL_HARNESS_REPORTS_FILENAME
    _write_json(official_reports_path, _official_harness_reports(source_root, decision))

    evaluator_manifest_path = evaluator_root / EVALUATOR_EVIDENCE_MANIFEST_FILENAME
    evaluator_manifest = {
        "schema_version": V3_EVALUATOR_EVIDENCE_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "purpose": "evaluator_only_and_audit_only_v3_swebench_like_evidence",
        "visibility": "evaluator_only",
        "adapter_must_not_read": True,
        "files": {
            "hidden_verifier_inputs": _file_ref(hidden_inputs_path),
            "gold_patch_predictions": _file_ref(gold_predictions_path),
            "official_harness_reports": _file_ref(official_reports_path),
        },
        "source_provenance_refs": source_files,
        "accepted_task_ids": list(EXPECTED_ACCEPTED_TASK_IDS),
        "source_hash_binding": {
            "hf_dataset_schema_candidate_field_sha256_checked": True,
            "sidecar_sha256_checked": True,
            "decision_report_sha256_checked": True,
        },
    }
    _write_json(evaluator_manifest_path, evaluator_manifest)

    task_manifest_path = adapter_root / TASK_INPUT_MANIFEST_FILENAME
    task_manifest = {
        "schema_version": V3_TASK_INPUT_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "dataset_name": EXPECTED_DATASET_NAME,
        "dataset_revision": EXPECTED_DATASET_REVISION,
        "dataset_split": EXPECTED_DATASET_SPLIT,
        "task_count": len(sanitized_rows),
        "accepted_task_ids": [row["instance_id"] for row in sanitized_rows],
        "adapter_visible_input_ref": _file_ref(adapter_tasks_path),
        "evaluator_only_manifest_ref": _file_ref(evaluator_manifest_path),
        "tasks": [
            {
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "base_commit": row["base_commit"],
                "task_input_sha256": _sha256_json(row),
                "model_visible_field_sha256": row["model_visible_field_sha256"],
                "hidden_evidence_hashes": row["hidden_evidence_hashes"],
            }
            for row in sanitized_rows
        ],
        "visibility_policy_ref": {
            "policy_id": "repo_harness_v3_adapter_visibility_policy_v0",
            "policy_terms_visibility": "evaluator_only",
        },
    }
    _write_json(task_manifest_path, task_manifest)

    feasibility_manifest_path = adapter_root / V3_FEASIBILITY_MANIFEST_FILENAME
    feasibility_manifest = {
        "schema_version": V3_FEASIBILITY_INPUT_MANIFEST_VERSION,
        "generated_at": _utc_timestamp(),
        "feasibility_root_provenance": _directory_ref(source_root),
        "fixture_dir": str(fixture_root),
        "adapter_input_dir": str(adapter_root),
        "evidence_dir": str(evidence_root),
        "evaluator_only_dir": str(evaluator_root),
        "decision": {
            "current_v3_entry_status": decision.get("current_v3_entry_status"),
            "green_entry_conditions_met": decision.get("green_entry_conditions_met"),
            "dataset_name": decision.get("dataset_name"),
            "dataset_revision": decision.get("dataset_revision"),
            "dataset_split": EXPECTED_DATASET_SPLIT,
            "swebench_git_commit": decision.get("swebench_git_commit"),
            "accepted_task_ids": list(EXPECTED_ACCEPTED_TASK_IDS),
        },
        "source_provenance_refs": _adapter_source_provenance_refs(source_files),
        "adapter_visible_files": {
            "swebench_like_tasks": _file_ref(adapter_tasks_path),
            "task_input_manifest": _file_ref(task_manifest_path),
        },
        "evaluator_only_evidence_manifest_ref": _file_ref(evaluator_manifest_path),
        "accepted_tasks": accepted_task_records,
        "contamination_policy": {
            "adapter_visible_directory": str(adapter_root),
            "evaluator_only_directory": str(evaluator_root),
            "adapter_visibility_policy_id": "repo_harness_v3_adapter_visibility_policy_v0",
            "hidden_material_categories": [
                "reference_material_evidence",
                "verification_material_evidence",
                "selector_evidence",
                "feasibility_audit_evidence",
            ],
            "adapter_visible_inputs_contain_raw_hidden_fields": False,
        },
        "checks": {
            "green_entry_status_checked": True,
            "dataset_revision_checked": True,
            "accepted_task_set_checked": True,
            "source_sha256_recomputed": True,
            "adapter_evaluator_split_checked": True,
        },
    }
    _write_json(feasibility_manifest_path, feasibility_manifest)

    generated_files = [
        adapter_tasks_path,
        task_manifest_path,
        feasibility_manifest_path,
        hidden_inputs_path,
        gold_predictions_path,
        official_reports_path,
        evaluator_manifest_path,
    ]
    for path in generated_files:
        _write_sha256_file(path)
    return feasibility_manifest_path


def inspect_v3_swebench_fixture(
    *,
    fixture_dir: str | Path,
    evidence_dir: str | Path,
    manifest: str | Path,
    assert_frozen: bool = False,
) -> str:
    """Inspect frozen V3 SWE-Bench-like fixture inputs without writing files."""

    fixture_root = Path(fixture_dir)
    evidence_root = Path(evidence_dir)
    manifest_path = Path(manifest)
    payload = _read_json(manifest_path)
    failures = _fixture_failures(
        fixture_root=fixture_root,
        evidence_root=evidence_root,
        manifest_path=manifest_path,
        manifest=payload,
    )
    if assert_frozen and failures:
        raise ConfigError("; ".join(failures))
    return json.dumps(
        {
            "status": "passed" if not failures else "failed",
            "manifest": str(manifest_path),
            "fixture_dir": str(fixture_root),
            "evidence_dir": str(evidence_root),
            "task_count": len(payload.get("accepted_tasks", [])),
            "accepted_task_ids": [
                task.get("instance_id") for task in payload.get("accepted_tasks", [])
            ],
            "checks": ["v3_swebench_fixture=frozen"] if assert_frozen and not failures else [],
            "failures": failures,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def _fixture_failures(
    *,
    fixture_root: Path,
    evidence_root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if manifest.get("schema_version") != V3_FEASIBILITY_INPUT_MANIFEST_VERSION:
        failures.append("invalid v3 fixture manifest schema_version")
    adapter_root = fixture_root / ADAPTER_INPUT_DIRNAME
    evaluator_root = evidence_root / EVALUATOR_ONLY_DIRNAME
    if Path(str(manifest.get("adapter_input_dir", ""))) != adapter_root:
        failures.append("manifest adapter_input_dir does not match explicit fixture-dir")
    if Path(str(manifest.get("evaluator_only_dir", ""))) != evaluator_root:
        failures.append("manifest evaluator_only_dir does not match explicit evidence-dir")
    decision = manifest.get("decision", {})
    if decision.get("current_v3_entry_status") != EXPECTED_ENTRY_STATUS:
        failures.append("fixture decision is not green_ready_for_v3_implementation_plan")
    if decision.get("dataset_name") != EXPECTED_DATASET_NAME:
        failures.append("fixture dataset_name mismatch")
    if decision.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        failures.append("fixture dataset_revision mismatch")
    if decision.get("dataset_split") != EXPECTED_DATASET_SPLIT:
        failures.append("fixture dataset_split mismatch")
    if decision.get("swebench_git_commit") != EXPECTED_SWEBENCH_COMMIT:
        failures.append("fixture swebench git commit mismatch")
    accepted_ids = [task.get("instance_id") for task in manifest.get("accepted_tasks", [])]
    if accepted_ids != list(EXPECTED_ACCEPTED_TASK_IDS):
        failures.append("fixture accepted task ids mismatch")

    for name, ref in _iter_file_refs(manifest):
        failures.extend(_file_ref_failures(name, ref))
        if isinstance(ref, dict) and "path" in ref:
            referenced_path = Path(ref["path"])
            if _is_under(referenced_path, adapter_root) or _is_under(referenced_path, evaluator_root):
                failures.extend(_sha256_sidecar_failures(referenced_path))
    failures.extend(_sha256_sidecar_failures(manifest_path))

    forbidden_adapter_files = sorted(
        path.name
        for path in adapter_root.iterdir()
        if path.is_file() and path.name in FORBIDDEN_ADAPTER_FILENAMES
    ) if adapter_root.exists() else []
    if forbidden_adapter_files:
        failures.append(
            "adapter input directory contains evaluator-only files: "
            + ", ".join(forbidden_adapter_files)
        )

    tasks_path = adapter_root / ADAPTER_TASKS_FILENAME
    hidden_path = evaluator_root / HIDDEN_VERIFIER_INPUTS_FILENAME
    if tasks_path.exists():
        adapter_text = tasks_path.read_text(encoding="utf-8")
        try:
            adapter_rows = _read_jsonl(tasks_path)
        except ConfigError as exc:
            failures.append(str(exc))
            adapter_rows = []
        for index, row in enumerate(adapter_rows, start=1):
            bad_keys = sorted(_forbidden_keys_in(row))
            if bad_keys:
                failures.append(
                    f"adapter task row {index} contains forbidden raw field keys: "
                    + ", ".join(bad_keys)
                )
        if hidden_path.exists():
            for marker in _hidden_content_markers(hidden_path):
                if marker and marker in adapter_text:
                    failures.append("adapter visible input contains raw hidden verifier content")
                    break
    else:
        failures.append(f"adapter visible task file missing: {tasks_path}")
    failures.extend(_adapter_root_failures(adapter_root, evaluator_root))

    task_manifest_path = adapter_root / TASK_INPUT_MANIFEST_FILENAME
    if task_manifest_path.exists():
        task_manifest = _read_json(task_manifest_path)
        if task_manifest.get("schema_version") != V3_TASK_INPUT_MANIFEST_VERSION:
            failures.append("task_input_manifest schema_version mismatch")
        if task_manifest.get("accepted_task_ids") != list(EXPECTED_ACCEPTED_TASK_IDS):
            failures.append("task_input_manifest accepted task ids mismatch")
    else:
        failures.append(f"task input manifest missing: {task_manifest_path}")

    evaluator_manifest_path = evaluator_root / EVALUATOR_EVIDENCE_MANIFEST_FILENAME
    if evaluator_manifest_path.exists():
        evaluator_manifest = _read_json(evaluator_manifest_path)
        if evaluator_manifest.get("schema_version") != V3_EVALUATOR_EVIDENCE_MANIFEST_VERSION:
            failures.append("evaluator evidence manifest schema_version mismatch")
        if not evaluator_manifest.get("adapter_must_not_read"):
            failures.append("evaluator evidence manifest must mark adapter_must_not_read=true")
        expected_evaluator_files = {
            "hidden_verifier_inputs",
            "gold_patch_predictions",
            "official_harness_reports",
        }
        evaluator_files = evaluator_manifest.get("files")
        if not isinstance(evaluator_files, dict):
            failures.append("evaluator evidence manifest files must be an object")
        else:
            missing_evaluator_files = sorted(
                expected_evaluator_files.difference(evaluator_files.keys())
            )
            if missing_evaluator_files:
                failures.append(
                    "evaluator evidence manifest missing required files: "
                    + ", ".join(missing_evaluator_files)
                )
            expected_paths = {
                "hidden_verifier_inputs": evaluator_root / HIDDEN_VERIFIER_INPUTS_FILENAME,
                "gold_patch_predictions": evaluator_root / GOLD_PATCH_PREDICTIONS_FILENAME,
                "official_harness_reports": evaluator_root / OFFICIAL_HARNESS_REPORTS_FILENAME,
            }
            for key, expected_path in expected_paths.items():
                ref = evaluator_files.get(key)
                if not isinstance(ref, dict):
                    failures.append(
                        f"evaluator evidence manifest {key} must be a file ref object"
                    )
                    continue
                failures.extend(_file_ref_failures(f"evaluator_manifest.files.{key}", ref))
                actual_path = Path(str(ref.get("path", "")))
                if actual_path != expected_path:
                    failures.append(
                        f"evaluator evidence manifest {key} does not match required path: "
                        f"{expected_path}"
                    )
                failures.extend(_sha256_sidecar_failures(expected_path))
        for name, ref in _iter_file_refs(evaluator_manifest, prefix="evaluator_manifest"):
            failures.extend(_file_ref_failures(name, ref))
            if isinstance(ref, dict) and "path" in ref:
                referenced_path = Path(ref["path"])
                if _is_under(referenced_path, evaluator_root):
                    failures.extend(_sha256_sidecar_failures(referenced_path))
    else:
        failures.append(f"evaluator evidence manifest missing: {evaluator_manifest_path}")
    return failures


def _load_decision(source_root: Path) -> dict[str, Any]:
    if not source_root.exists():
        raise ConfigError(f"V3 feasibility root 不存在：{source_root}")
    decision_path = source_root / "feasibility_decision.json"
    if not decision_path.exists():
        raise ConfigError(f"feasibility_decision.json 不存在：{decision_path}")
    payload = _read_json(decision_path)
    if not isinstance(payload, dict):
        raise ConfigError("feasibility_decision.json 顶层必须是 JSON object。")
    return payload


def _assert_green_decision(decision: dict[str, Any]) -> None:
    if decision.get("current_v3_entry_status") != EXPECTED_ENTRY_STATUS:
        raise ConfigError(
            "V3 feasibility decision 不是 green_ready_for_v3_implementation_plan。"
        )
    if not decision.get("green_entry_conditions_met"):
        raise ConfigError("V3 feasibility decision 未满足 Green entry conditions。")
    if decision.get("dataset_name") != EXPECTED_DATASET_NAME:
        raise ConfigError("V3 feasibility dataset_name 与实施计划不一致。")
    if decision.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        raise ConfigError("V3 feasibility dataset_revision 与实施计划不一致。")
    if decision.get("swebench_git_commit") != EXPECTED_SWEBENCH_COMMIT:
        raise ConfigError("V3 feasibility SWE-Bench commit 与实施计划不一致。")
    level2 = decision.get("level2", {})
    if level2.get("selected_instance_ids") != list(EXPECTED_ACCEPTED_TASK_IDS):
        raise ConfigError("V3 feasibility accepted task 清单与实施计划不一致。")
    if level2.get("accepted_count") != len(EXPECTED_ACCEPTED_TASK_IDS):
        raise ConfigError("V3 feasibility accepted task 数量不等于 3。")
    if not level2.get("all_resolved"):
        raise ConfigError("V3 feasibility Level 2 gold patch evaluation 未全部 resolved。")


def _source_provenance_refs(source_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    refs = {}
    for name, relative_path in SOURCE_REQUIRED_FILES.items():
        path = source_root / relative_path
        if not path.exists():
            raise ConfigError(f"V3 feasibility 来源文件缺失：{path}")
        _assert_expected_source_sha256(name, path)
        refs[name] = _source_provenance_ref(source_root, path)
    for report_name, report_key in (
        ("level1_official_report", "level1"),
        ("level2_official_report", "level2"),
    ):
        report_path = _path_from_decision(source_root, decision.get(report_key, {}).get("report_path"))
        if not report_path.exists():
            raise ConfigError(f"V3 feasibility official harness report 缺失：{report_path}")
        _assert_expected_source_sha256(report_name, report_path)
        refs[report_name] = _source_provenance_ref(source_root, report_path)
    return refs


def _assert_expected_source_sha256(name: str, path: Path) -> None:
    expected = EXPECTED_SOURCE_SHA256.get(name)
    if expected and expected != _sha256_file(path):
        raise ConfigError(f"V3 feasibility fixed Green source sha256 不匹配：{name}")


def _adapter_source_provenance_refs(source_files: dict[str, Any]) -> dict[str, Any]:
    adapter_visible_source_names = {
        "hf_dataset_schema",
        "level2_dataset",
        "candidate_task_manifest",
        "selected_task_manifest",
    }
    return {
        name: ref
        for name, ref in source_files.items()
        if name in adapter_visible_source_names
    }


def _path_from_decision(source_root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ConfigError("feasibility decision 缺少 official report path。")
    path = Path(value)
    if path.is_absolute():
        return path
    return source_root / path


def _assert_source_sha_files(
    source_root: Path,
    decision: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    for data_relative, sha_relative in (
        ("candidate_task_manifest.json", "candidate_task_manifest.sha256"),
        ("dataset/level2_dataset.jsonl", "dataset/level2_dataset.jsonl.sha256"),
        ("dataset/level2_dataset.jsonl", "dataset/level2_dataset.sha256"),
        ("level1/gold_patch_prediction.jsonl", "level1/gold_patch_prediction.sha256"),
        ("level2/gold_patch_predictions.jsonl", "level2/gold_patch_predictions.sha256"),
    ):
        data_path = source_root / data_relative
        sha_path = source_root / sha_relative
        if not data_path.exists() or not sha_path.exists():
            raise ConfigError(f"V3 feasibility sha256 来源文件缺失：{data_path} / {sha_path}")
        expected = _read_sha256_sidecar(sha_path)
        actual = _sha256_file(data_path)
        if expected != actual:
            raise ConfigError(f"V3 feasibility sha256 不匹配：{data_path}")
    level2_dataset_sha256 = schema.get("level2_dataset_sha256")
    if level2_dataset_sha256 != _sha256_file(source_root / SOURCE_REQUIRED_FILES["level2_dataset"]):
        raise ConfigError("hf_dataset_schema.json level2_dataset_sha256 与 level2 dataset 不匹配。")
    candidate_manifest_sha256 = _read_sha256_sidecar(
        source_root / "candidate_task_manifest.sha256"
    )
    if candidate_manifest_sha256 != _sha256_file(
        source_root / SOURCE_REQUIRED_FILES["candidate_task_manifest"]
    ):
        raise ConfigError("candidate_task_manifest.sha256 与 candidate task manifest 不匹配。")
    for report_key in ("level1", "level2"):
        report_path = _path_from_decision(
            source_root, decision.get(report_key, {}).get("report_path")
        )
        expected_report_sha = decision.get(report_key, {}).get("report_sha256")
        if expected_report_sha != _sha256_file(report_path):
            raise ConfigError(
                f"feasibility_decision.json {report_key}.report_sha256 与 report 文件不匹配。"
            )


def _assert_dataset_schema(source_root: Path) -> dict[str, Any]:
    schema_path = source_root / "hf_dataset_schema.json"
    schema = _read_json(schema_path)
    if not isinstance(schema, dict):
        raise ConfigError("hf_dataset_schema.json 顶层必须是 JSON object。")
    if schema.get("dataset_name") != EXPECTED_DATASET_NAME:
        raise ConfigError("hf_dataset_schema.json dataset_name 与实施计划不一致。")
    if schema.get("dataset_revision") != EXPECTED_DATASET_REVISION:
        raise ConfigError("hf_dataset_schema.json dataset_revision 与实施计划不一致。")
    if schema.get("split") != EXPECTED_DATASET_SPLIT:
        raise ConfigError("hf_dataset_schema.json split 与实施计划不一致。")
    if schema.get("level2_instance_ids") != list(EXPECTED_ACCEPTED_TASK_IDS):
        raise ConfigError("hf_dataset_schema.json Level 2 task ids 与固定 Green 路径不一致。")
    if not isinstance(schema.get("candidate_field_sha256"), dict):
        raise ConfigError("hf_dataset_schema.json 缺少 candidate_field_sha256。")
    if not isinstance(schema.get("level2_dataset_sha256"), str):
        raise ConfigError("hf_dataset_schema.json 缺少 level2_dataset_sha256。")
    return schema


def _assert_accepted_rows(
    rows: list[dict[str, Any]],
    selected_rows: list[dict[str, Any]],
    decision: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    ids = [row.get("instance_id") for row in rows]
    selected_ids = [row.get("instance_id") for row in selected_rows]
    resolved_ids = decision.get("level2", {}).get("resolved_ids")
    expected = list(EXPECTED_ACCEPTED_TASK_IDS)
    if ids != expected or selected_ids != expected or resolved_ids != expected:
        raise ConfigError("V3 feasibility accepted task ids 与固定 Green 路径不一致。")
    if selected_rows != rows:
        raise ConfigError("selected_task_manifest.json 与 level2 dataset rows 不一致。")
    candidate_hashes = schema.get("candidate_field_sha256", {})
    for row in rows:
        missing = [
            key
            for key in (
                "repo",
                "instance_id",
                "base_commit",
                "problem_statement",
                "patch",
                "test_patch",
                "FAIL_TO_PASS",
                "PASS_TO_PASS",
                "environment_setup_commit",
            )
            if not row.get(key)
        ]
        if missing:
            raise ConfigError(
                f"V3 feasibility task {row.get('instance_id')} 缺少字段："
                + ", ".join(missing)
            )
        expected_field_hashes = candidate_hashes.get(row["instance_id"])
        if not isinstance(expected_field_hashes, dict):
            raise ConfigError(
                f"hf_dataset_schema.json 缺少 {row['instance_id']} 的 candidate field sha256。"
            )
        for field_name in (
            "repo",
            "instance_id",
            "base_commit",
            "problem_statement",
            "patch",
            "test_patch",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
        ):
            if expected_field_hashes.get(field_name) != _sha256_text(row[field_name]):
                raise ConfigError(
                    f"V3 feasibility task {row['instance_id']} field sha256 不匹配："
                    f"{field_name}"
                )
        if (
            "environment_setup_commit" in expected_field_hashes
            and expected_field_hashes["environment_setup_commit"]
            != _sha256_text(row["environment_setup_commit"])
        ):
            raise ConfigError(
                f"V3 feasibility task {row['instance_id']} field sha256 不匹配："
                "environment_setup_commit"
            )
        _parse_selector_list(row["FAIL_TO_PASS"], row["instance_id"], "FAIL_TO_PASS")
        _parse_selector_list(row["PASS_TO_PASS"], row["instance_id"], "PASS_TO_PASS")


def _adapter_visible_row(row: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": V3_ADAPTER_INPUT_ROW_VERSION,
        "task_style": "swebench_like",
        "dataset_name": EXPECTED_DATASET_NAME,
        "dataset_revision": EXPECTED_DATASET_REVISION,
        "dataset_split": EXPECTED_DATASET_SPLIT,
        "instance_id": row["instance_id"],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "environment_setup_commit": row["environment_setup_commit"],
        "version": row.get("version"),
        "created_at": row.get("created_at"),
        "problem_statement": row["problem_statement"],
        "problem_statement_sha256": record["model_visible_field_sha256"]["problem_statement"],
        "model_visible_field_sha256": record["model_visible_field_sha256"],
        "hidden_evidence_hashes": {
            "reference_material_sha256": record["hidden_field_sha256"]["reference_material"],
            "verifier_material_sha256": record["hidden_field_sha256"]["verifier_material"],
            "target_selector_list_sha256": record["hidden_field_sha256"]["target_test_selectors"],
            "regression_selector_list_sha256": record["hidden_field_sha256"][
                "regression_test_selectors"
            ],
            "target_selector_count": record["selector_counts"]["target_test_selectors"],
            "regression_selector_count": record["selector_counts"]["regression_test_selectors"],
        },
        "visibility_policy": {
            "issue_statement": "model_visible",
            "hidden_reference_material": "evaluator_only",
            "hidden_verification_material": "evaluator_only",
            "external_feasibility_audit_material": "evaluator_only",
        },
        "benchmark_comparability": "not_public_leaderboard_comparable",
        "source_snapshot": {
            "source": "v3_feasibility_level2_fixed_revision_jsonl",
            "source_row_sha256": _sha256_json(row),
        },
    }


def _hidden_verifier_row(row: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": V3_HIDDEN_VERIFIER_INPUT_VERSION,
        "visibility": "evaluator_only",
        "instance_id": row["instance_id"],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "dataset_revision": EXPECTED_DATASET_REVISION,
        "test_patch": row["test_patch"],
        "FAIL_TO_PASS": row["FAIL_TO_PASS"],
        "PASS_TO_PASS": row["PASS_TO_PASS"],
        "model_visible_field_sha256": record["model_visible_field_sha256"],
        "hidden_field_sha256": record["hidden_field_sha256"],
        "selector_counts": record["selector_counts"],
    }


def _accepted_task_record(row: dict[str, Any]) -> dict[str, Any]:
    fail_to_pass = _parse_selector_list(row["FAIL_TO_PASS"], row["instance_id"], "FAIL_TO_PASS")
    pass_to_pass = _parse_selector_list(row["PASS_TO_PASS"], row["instance_id"], "PASS_TO_PASS")
    return {
        "instance_id": row["instance_id"],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "environment_setup_commit": row["environment_setup_commit"],
        "model_visible_field_sha256": {
            "repo": _sha256_text(row["repo"]),
            "instance_id": _sha256_text(row["instance_id"]),
            "base_commit": _sha256_text(row["base_commit"]),
            "problem_statement": _sha256_text(row["problem_statement"]),
            "environment_setup_commit": _sha256_text(row["environment_setup_commit"]),
        },
        "hidden_field_sha256": {
            "reference_material": _sha256_text(row["patch"]),
            "verifier_material": _sha256_text(row["test_patch"]),
            "target_test_selectors": _sha256_text(row["FAIL_TO_PASS"]),
            "regression_test_selectors": _sha256_text(row["PASS_TO_PASS"]),
        },
        "selector_counts": {
            "target_test_selectors": len(fail_to_pass),
            "regression_test_selectors": len(pass_to_pass),
        },
    }


def _official_harness_reports(source_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    level1_report = _path_from_decision(source_root, decision["level1"]["report_path"])
    level2_report = _path_from_decision(source_root, decision["level2"]["report_path"])
    return {
        "schema_version": "repo_harness_v3_official_harness_reports_evaluator_only_v0",
        "visibility": "evaluator_only",
        "purpose": "stage_0_feasibility_source_proof_only_not_v3_final_verifier",
        "swebench_git_commit": decision.get("swebench_git_commit"),
        "dataset_name": decision.get("dataset_name"),
        "dataset_revision": decision.get("dataset_revision"),
        "dataset_split": EXPECTED_DATASET_SPLIT,
        "reports": {
            "level1": {
                "source_provenance_ref": _source_provenance_ref(source_root, level1_report),
                "payload": _read_json(level1_report),
            },
            "level2": {
                "source_provenance_ref": _source_provenance_ref(source_root, level2_report),
                "payload": _read_json(level2_report),
            },
        },
    }


def _adapter_root_failures(adapter_root: Path, evaluator_root: Path) -> list[str]:
    failures: list[str] = []
    if not adapter_root.exists():
        return [f"adapter input directory missing: {adapter_root}"]
    allowed_files = {
        ADAPTER_TASKS_FILENAME,
        TASK_INPUT_MANIFEST_FILENAME,
        V3_FEASIBILITY_MANIFEST_FILENAME,
        ADAPTER_TASKS_FILENAME + ".sha256",
        TASK_INPUT_MANIFEST_FILENAME + ".sha256",
        V3_FEASIBILITY_MANIFEST_FILENAME + ".sha256",
    }
    nested_directories = sorted(
        path.relative_to(adapter_root).as_posix()
        for path in adapter_root.rglob("*")
        if path.is_dir()
    )
    if nested_directories:
        failures.append(
            "adapter input directory contains nested directories: "
            + ", ".join(nested_directories)
        )
    unexpected = sorted(
        path.relative_to(adapter_root).as_posix()
        for path in adapter_root.rglob("*")
        if path.is_file() and path.name not in allowed_files
    )
    if unexpected:
        failures.append("adapter input directory contains unexpected files: " + ", ".join(unexpected))
    markers = _all_hidden_content_markers(evaluator_root)
    for path in sorted(adapter_root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker and marker in text:
                failures.append(f"adapter input file contains raw hidden content: {path}")
                return failures
        failures.extend(_json_file_adapter_visibility_failures(path, markers))
    return failures


def _iter_file_refs(value: Any, prefix: str = "") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if {"path", "sha256", "size_bytes"}.issubset(value.keys()):
            yield prefix or "file_ref", value
            return
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_file_refs(child, child_prefix)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_file_refs(child, f"{prefix}[{index}]")


def _file_ref_failures(name: str, ref: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(ref, dict):
        return [f"{name} is not a file ref object"]
    path_value = ref.get("path")
    if not isinstance(path_value, str):
        return [f"{name} file ref missing path"]
    path = Path(path_value)
    if not path.exists():
        return [f"{name} file ref path does not exist: {path}"]
    actual_sha = _sha256_file(path)
    actual_size = path.stat().st_size
    if ref.get("sha256") != actual_sha:
        failures.append(f"{name} sha256 mismatch: {path}")
    if ref.get("size_bytes") != actual_size:
        failures.append(f"{name} size_bytes mismatch: {path}")
    return failures


def _sha256_sidecar_failures(path: Path) -> list[str]:
    sidecar = Path(str(path) + ".sha256")
    if not sidecar.exists():
        return [f"sha256 sidecar missing: {sidecar}"]
    try:
        expected = _read_sha256_sidecar(sidecar)
    except ConfigError as exc:
        return [str(exc)]
    if not path.exists():
        return [f"sha256 sidecar target missing: {path}"]
    actual = _sha256_file(path)
    if expected != actual:
        return [f"sha256 sidecar mismatch: {path}"]
    return []


def _read_sha256_sidecar(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ConfigError(f"sha256 文件为空：{path}")
    value = text.split()[0]
    if len(value) != 64:
        raise ConfigError(f"sha256 文件格式无效：{path}")
    return value


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _forbidden_keys_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_ADAPTER_KEYS:
                found.add(key)
            found.update(_forbidden_keys_in(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_forbidden_keys_in(child))
    return found


def _forbidden_terms_in(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, str):
        normalized = value.lower()
        for term in FORBIDDEN_ADAPTER_TERMS:
            normalized_term = _normalize_visibility_term(term)
            if term in normalized or (
                normalized_term and normalized_term in _normalize_visibility_term(value)
            ):
                found.add(term)
    elif isinstance(value, dict):
        for key, child in value.items():
            found.update(_forbidden_terms_in(str(key)))
            found.update(_forbidden_terms_in(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_forbidden_terms_in(child))
    return found


def _normalize_visibility_term(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _hidden_content_markers(hidden_path: Path) -> list[str]:
    markers: list[str] = []
    for row in _read_jsonl(hidden_path):
        for key in ("test_patch", "FAIL_TO_PASS", "PASS_TO_PASS"):
            value = row.get(key)
            if isinstance(value, str) and value:
                markers.append(value)
    return markers


def _all_hidden_content_markers(evaluator_root: Path) -> list[str]:
    markers: list[str] = []
    hidden_path = evaluator_root / HIDDEN_VERIFIER_INPUTS_FILENAME
    if hidden_path.exists():
        markers.extend(_hidden_content_markers(hidden_path))
    predictions_path = evaluator_root / GOLD_PATCH_PREDICTIONS_FILENAME
    if predictions_path.exists():
        for row in _read_jsonl(predictions_path):
            value = row.get("model_patch")
            if isinstance(value, str) and value:
                markers.append(value)
    official_reports_path = evaluator_root / OFFICIAL_HARNESS_REPORTS_FILENAME
    if official_reports_path.exists():
        markers.append(official_reports_path.read_text(encoding="utf-8"))
    return markers


def _json_file_adapter_visibility_failures(path: Path, markers: list[str]) -> list[str]:
    if path.suffix == ".sha256":
        return []
    payloads: list[Any] = []
    try:
        if path.suffix == ".json":
            payloads.append(_read_json(path))
        elif path.suffix == ".jsonl":
            payloads.extend(_read_jsonl(path))
    except ConfigError as exc:
        return [str(exc)]
    forbidden_keys: set[str] = set()
    forbidden_terms: set[str] = set()
    for payload in payloads:
        forbidden_keys.update(_forbidden_keys_in(payload))
        forbidden_terms.update(_forbidden_terms_in(payload))
        if _value_contains_marker(payload, markers):
            return [f"adapter input file contains JSON-encoded raw hidden content: {path}"]
    if forbidden_keys:
        return [
            f"adapter input file contains forbidden raw field keys: {path}: "
            + ", ".join(sorted(forbidden_keys))
        ]
    if forbidden_terms:
        return [
            f"adapter input file contains forbidden raw visibility terms: {path}: "
            + ", ".join(sorted(forbidden_terms))
        ]
    return []


def _value_contains_marker(value: Any, markers: list[str]) -> bool:
    if isinstance(value, str):
        return any(marker and marker in value for marker in markers)
    if isinstance(value, dict):
        return any(
            _value_contains_marker(str(key), markers)
            or _value_contains_marker(child, markers)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_value_contains_marker(child, markers) for child in value)
    return False


def _parse_selector_list(value: Any, instance_id: str, field_name: str) -> list[str]:
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{instance_id} {field_name} 不是有效 JSON list。") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ConfigError(f"{instance_id} {field_name} 必须是字符串列表。")
    if not parsed:
        raise ConfigError(f"{instance_id} {field_name} 不能为空。")
    return parsed


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"JSON 文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 文件无效：{path}") from exc


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
            raise ConfigError(f"JSONL 第 {line_number} 行必须是 JSON object：{path}")
        rows.append(row)
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in rows
    )
    path.write_text(text, encoding="utf-8")


def _write_sha256_file(path: Path) -> None:
    sha_path = Path(str(path) + ".sha256")
    sha_path.write_text(f"{_sha256_file(path)}  {path.name}\n", encoding="utf-8")


def _file_ref(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _source_provenance_ref(source_root: Path, path: Path) -> dict[str, Any]:
    try:
        original_path = path.resolve().relative_to(source_root.resolve()).as_posix()
    except ValueError:
        original_path = path.name
    return {
        "original_path": original_path,
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _directory_ref(path: Path) -> dict[str, Any]:
    return {
        "original_path": str(path),
        "existed_at_freeze": path.exists(),
    }


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_json(value: Any) -> str:
    return _sha256_text(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
