import json
import shutil
from pathlib import Path

import pytest

from repo_harness import v3_swebench_fixture as fixture_module
from repo_harness.errors import ConfigError
from repo_harness.v3_swebench_fixture import (
    EXPECTED_ACCEPTED_TASK_IDS,
    inspect_v3_swebench_fixture,
    prepare_v3_swebench_fixture,
)

_REAL_EXPECTED_SOURCE_SHA256 = dict(fixture_module.EXPECTED_SOURCE_SHA256)


@pytest.fixture(autouse=True)
def _restore_expected_source_sha256():
    yield
    fixture_module.EXPECTED_SOURCE_SHA256 = dict(_REAL_EXPECTED_SOURCE_SHA256)


def test_prepare_and_inspect_v3_swebench_fixture(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixtures" / "v3" / "swebench_lite_fixed"
    evidence_dir = tmp_path / "docs" / "v3" / "evidence" / "swebench-lite-fixed"

    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    output = inspect_v3_swebench_fixture(
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
        manifest=manifest_path,
        assert_frozen=True,
    )
    payload = json.loads(output)
    adapter_rows = _read_jsonl(fixture_dir / "adapter_inputs" / "swebench_like_tasks.jsonl")
    evaluator_rows = _read_jsonl(evidence_dir / "evaluator_only" / "hidden_verifier_inputs.jsonl")

    assert payload["status"] == "passed"
    assert payload["accepted_task_ids"] == list(EXPECTED_ACCEPTED_TASK_IDS)
    assert "v3_swebench_fixture=frozen" in payload["checks"]
    assert len(adapter_rows) == 3
    assert len(evaluator_rows) == 3
    assert "patch" not in adapter_rows[0]
    assert "test_patch" not in adapter_rows[0]
    assert "FAIL_TO_PASS" not in adapter_rows[0]
    assert "PASS_TO_PASS" not in adapter_rows[0]
    assert "SECRET_TEST_PATCH_pytest-dev__pytest-7220" not in (
        fixture_dir / "adapter_inputs" / "swebench_like_tasks.jsonl"
    ).read_text(encoding="utf-8")
    assert (
        evidence_dir / "evaluator_only" / "gold_patch_predictions.jsonl"
    ).exists()


def test_prepare_rejects_non_green_decision(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    decision_path = source_root / "feasibility_decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["current_v3_entry_status"] = "red_blocked"
    _write_json(decision_path, decision)

    with pytest.raises(ConfigError, match="green_ready_for_v3_implementation_plan"):
        prepare_v3_swebench_fixture(
            feasibility_root=source_root,
            fixture_dir=tmp_path / "fixture",
            evidence_dir=tmp_path / "evidence",
        )


def test_prepare_rejects_dataset_split_mismatch(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    schema_path = source_root / "hf_dataset_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["split"] = "dev"
    _write_json(schema_path, schema)

    with pytest.raises(ConfigError, match="split"):
        prepare_v3_swebench_fixture(
            feasibility_root=source_root,
            fixture_dir=tmp_path / "fixture",
            evidence_dir=tmp_path / "evidence",
        )


def test_prepare_rejects_dataset_field_hash_drift_even_with_updated_sidecars(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    dataset_path = source_root / "dataset" / "level2_dataset.jsonl"
    rows = _read_jsonl(dataset_path)
    rows[0]["problem_statement"] = "Tampered visible problem statement."
    _write_jsonl(dataset_path, rows)
    _write_json(source_root / "level2" / "selected_task_manifest.json", rows)
    _write_named_sha256(dataset_path, source_root / "dataset" / "level2_dataset.jsonl.sha256")
    _write_named_sha256(dataset_path, source_root / "dataset" / "level2_dataset.sha256")
    schema_path = source_root / "hf_dataset_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema["level2_dataset_sha256"] = _file_ref(dataset_path)["sha256"]
    _write_json(schema_path, schema)

    with pytest.raises(ConfigError, match="sha256"):
        prepare_v3_swebench_fixture(
            feasibility_root=source_root,
            fixture_dir=tmp_path / "fixture",
            evidence_dir=tmp_path / "evidence",
        )


def test_prepare_rejects_official_report_sha_drift(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    report_path = source_root / "level2" / "gold_patch_feasibility_probe.level2.json"
    _write_json(report_path, {"resolved": [], "unresolved": ["pytest-dev__pytest-7220"]})

    with pytest.raises(ConfigError, match="sha256"):
        prepare_v3_swebench_fixture(
            feasibility_root=source_root,
            fixture_dir=tmp_path / "fixture",
            evidence_dir=tmp_path / "evidence",
        )


def test_inspect_does_not_require_original_runs_source_after_freeze(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    shutil.rmtree(source_root)

    output = inspect_v3_swebench_fixture(
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
        manifest=manifest_path,
        assert_frozen=True,
    )

    assert json.loads(output)["status"] == "passed"


def test_inspect_rejects_tampered_adapter_file(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    adapter_path = fixture_dir / "adapter_inputs" / "swebench_like_tasks.jsonl"
    adapter_path.write_text(adapter_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="sha256"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_evaluator_only_file_in_adapter_root(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    forbidden_path = fixture_dir / "adapter_inputs" / "gold_patch_predictions.jsonl"
    forbidden_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigError, match="evaluator-only files"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_raw_hidden_content_under_renamed_adapter_file(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    injected_path = fixture_dir / "adapter_inputs" / "renamed_official_payload.json"
    injected_path.write_text(
        json.dumps({"model_patch": "SECRET_TEST_PATCH_pytest-dev__pytest-7220"}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="unexpected files|raw hidden content"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_nested_adapter_input_directory(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    nested_dir = fixture_dir / "adapter_inputs" / "nested_payloads"
    nested_dir.mkdir()
    (nested_dir / "hidden.json").write_text(
        json.dumps({"payload": "SECRET_TEST_PATCH_pytest-dev__pytest-7220"}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="nested directories|unexpected files|raw hidden content"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_json_encoded_hidden_patch_in_allowed_manifest(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    hidden_patch = _read_jsonl(evidence_dir / "evaluator_only" / "hidden_verifier_inputs.jsonl")[0][
        "test_patch"
    ]
    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["leaked_json_encoded_hidden_patch"] = hidden_patch
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="JSON-encoded raw hidden content"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_json_key_hidden_patch_in_allowed_manifest(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    hidden_patch = _read_jsonl(evidence_dir / "evaluator_only" / "hidden_verifier_inputs.jsonl")[0][
        "test_patch"
    ]
    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["leaked_key_container"] = {hidden_patch: "hidden content in JSON key"}
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="JSON-encoded raw hidden content"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_forbidden_keys_in_allowed_adapter_manifest(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["safe_wrapper"] = {
        "completed_ids": ["pytest-dev__pytest-7220"],
        "patch": "sha256-only injection should still be rejected by key",
        "resolved": ["pytest-dev__pytest-7220"],
        "resolved_ids": ["pytest-dev__pytest-7220"],
        "submitted_ids": ["pytest-dev__pytest-7220"],
        "unresolved_ids": [],
        "official_report": {"status": "not raw but forbidden adapter-visible key"},
    }
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="forbidden raw field keys"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_forbidden_terms_in_allowed_adapter_manifest(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["safe_wrapper"] = {
        "audit_marker": "official_harness completed_ids",
        "gold_patch_marker": "hash-only term injection",
        "status_value": "resolved",
        "state": "unresolved_status",
        "officialStatus": "clean-looking value",
        "goldPatch": "hash-only marker",
        "testPatch": "hash-only marker",
        "selector": "failToPass",
        "camel_case_state": "submittedIds",
    }
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="forbidden raw visibility terms"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_evaluator_required_file_ref_outside_canonical_path(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    evaluator_manifest_path = evidence_dir / "evaluator_only" / "evaluator_evidence_manifest.json"
    outside_path = tmp_path / "outside_hidden_verifier_inputs.jsonl"
    outside_path.write_text(
        (evidence_dir / "evaluator_only" / "hidden_verifier_inputs.jsonl").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    _write_sidecar_for_generated_file(outside_path)
    evaluator_manifest = json.loads(evaluator_manifest_path.read_text(encoding="utf-8"))
    evaluator_manifest["files"]["hidden_verifier_inputs"] = _file_ref(outside_path)
    _write_json(evaluator_manifest_path, evaluator_manifest)
    _write_sidecar_for_generated_file(evaluator_manifest_path)

    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["evaluator_only_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    fixture_manifest["evaluator_only_evidence_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="does not match required path"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_evaluator_required_file_ref_with_wrong_type(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    evaluator_manifest_path = evidence_dir / "evaluator_only" / "evaluator_evidence_manifest.json"
    evaluator_manifest = json.loads(evaluator_manifest_path.read_text(encoding="utf-8"))
    evaluator_manifest["files"]["hidden_verifier_inputs"] = "hidden_verifier_inputs.jsonl"
    _write_json(evaluator_manifest_path, evaluator_manifest)
    _write_sidecar_for_generated_file(evaluator_manifest_path)

    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["evaluator_only_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    fixture_manifest["evaluator_only_evidence_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="must be a file ref object"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_evaluator_required_file_ref_missing_sha_or_size(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    evaluator_manifest_path = evidence_dir / "evaluator_only" / "evaluator_evidence_manifest.json"
    evaluator_manifest = json.loads(evaluator_manifest_path.read_text(encoding="utf-8"))
    hidden_path = evidence_dir / "evaluator_only" / "hidden_verifier_inputs.jsonl"
    evaluator_manifest["files"]["hidden_verifier_inputs"] = {"path": str(hidden_path)}
    _write_json(evaluator_manifest_path, evaluator_manifest)
    _write_sidecar_for_generated_file(evaluator_manifest_path)

    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["evaluator_only_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    fixture_manifest["evaluator_only_evidence_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="missing path|sha256 mismatch|size_bytes mismatch"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def test_inspect_rejects_evaluator_manifest_missing_required_file_ref(tmp_path: Path):
    source_root = _write_feasibility_root(tmp_path / "feasibility")
    fixture_dir = tmp_path / "fixture"
    evidence_dir = tmp_path / "evidence"
    manifest_path = prepare_v3_swebench_fixture(
        feasibility_root=source_root,
        fixture_dir=fixture_dir,
        evidence_dir=evidence_dir,
    )
    evaluator_manifest_path = evidence_dir / "evaluator_only" / "evaluator_evidence_manifest.json"
    evaluator_manifest = json.loads(evaluator_manifest_path.read_text(encoding="utf-8"))
    del evaluator_manifest["files"]["gold_patch_predictions"]
    _write_json(evaluator_manifest_path, evaluator_manifest)
    _write_sidecar_for_generated_file(evaluator_manifest_path)

    task_manifest_path = fixture_dir / "adapter_inputs" / "task_input_manifest.json"
    task_manifest = json.loads(task_manifest_path.read_text(encoding="utf-8"))
    task_manifest["evaluator_only_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(task_manifest_path, task_manifest)
    _write_sidecar_for_generated_file(task_manifest_path)

    fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fixture_manifest["adapter_visible_files"]["task_input_manifest"] = _file_ref(task_manifest_path)
    fixture_manifest["evaluator_only_evidence_manifest_ref"] = _file_ref(evaluator_manifest_path)
    _write_json(manifest_path, fixture_manifest)
    _write_sidecar_for_generated_file(manifest_path)

    with pytest.raises(ConfigError, match="missing required files"):
        inspect_v3_swebench_fixture(
            fixture_dir=fixture_dir,
            evidence_dir=evidence_dir,
            manifest=manifest_path,
            assert_frozen=True,
        )


def _write_feasibility_root(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "dataset").mkdir()
    (root / "level1").mkdir()
    (root / "level2").mkdir()
    rows = [_task_row(instance_id) for instance_id in EXPECTED_ACCEPTED_TASK_IDS]
    level2_dataset_path = root / "dataset" / "level2_dataset.jsonl"
    candidate_manifest_path = root / "candidate_task_manifest.json"
    selected_manifest_path = root / "level2" / "selected_task_manifest.json"
    _write_jsonl(level2_dataset_path, rows)
    _write_json(candidate_manifest_path, rows)
    _write_json(selected_manifest_path, rows)
    _write_named_sha256(level2_dataset_path, root / "dataset" / "level2_dataset.jsonl.sha256")
    _write_named_sha256(level2_dataset_path, root / "dataset" / "level2_dataset.sha256")
    _write_named_sha256(candidate_manifest_path, root / "candidate_task_manifest.sha256")
    _write_json(
        root / "hf_dataset_schema.json",
        {
            "candidate_field_sha256": {
                row["instance_id"]: _source_field_sha256(row)
                for row in rows
            },
            "dataset_name": "princeton-nlp/SWE-bench_Lite",
            "dataset_revision": "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2",
            "split": "test",
            "row_count": 300,
            "level2_dataset_sha256": _file_ref(level2_dataset_path)["sha256"],
            "level2_instance_ids": list(EXPECTED_ACCEPTED_TASK_IDS),
        },
    )

    level1_prediction = (
        '{"instance_id":"pytest-dev__pytest-7220","model_patch":"SECRET_GOLD_PATCH_LEVEL1"}\n'
    )
    (root / "level1" / "gold_patch_prediction.jsonl").write_text(
        level1_prediction,
        encoding="utf-8",
    )
    _write_named_sha256(
        root / "level1" / "gold_patch_prediction.jsonl",
        root / "level1" / "gold_patch_prediction.sha256",
    )

    level2_predictions = "".join(
        json.dumps(
            {
                "instance_id": row["instance_id"],
                "model_patch": f"SECRET_GOLD_PATCH_{row['instance_id']}",
            },
            sort_keys=True,
        )
        + "\n"
        for row in rows
    )
    (root / "level2" / "gold_patch_predictions.jsonl").write_text(
        level2_predictions,
        encoding="utf-8",
    )
    _write_named_sha256(
        root / "level2" / "gold_patch_predictions.jsonl",
        root / "level2" / "gold_patch_predictions.sha256",
    )

    _write_json(
        root / "level1" / "gold_patch_feasibility_probe.level1.json",
        {"resolved": ["pytest-dev__pytest-7220"], "unresolved": []},
    )
    _write_json(
        root / "level2" / "gold_patch_feasibility_probe.level2.json",
        {"resolved": list(EXPECTED_ACCEPTED_TASK_IDS), "unresolved": []},
    )
    level1_report_path = root / "level1" / "gold_patch_feasibility_probe.level1.json"
    level2_report_path = root / "level2" / "gold_patch_feasibility_probe.level2.json"
    _write_json(
        root / "feasibility_decision.json",
        {
            "current_v3_entry_status": "green_ready_for_v3_implementation_plan",
            "green_entry_conditions_met": True,
            "dataset_name": "princeton-nlp/SWE-bench_Lite",
            "dataset_revision": "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2",
            "swebench_git_commit": "f7bbbb2ccdf479001d6467c9e34af59e44a840f9",
            "level1": {
                "report_path": str(level1_report_path),
                "report_sha256": _file_ref(level1_report_path)["sha256"],
            },
            "level2": {
                "accepted_count": 3,
                "all_resolved": True,
                "resolved_ids": list(EXPECTED_ACCEPTED_TASK_IDS),
                "selected_instance_ids": list(EXPECTED_ACCEPTED_TASK_IDS),
                "report_path": str(level2_report_path),
                "report_sha256": _file_ref(level2_report_path)["sha256"],
            },
        },
    )
    _set_expected_source_sha256_for_test(root)
    return root


def _task_row(instance_id: str) -> dict[str, str]:
    repo = "sympy/sympy" if instance_id.startswith("sympy") else "pytest-dev/pytest"
    return {
        "instance_id": instance_id,
        "repo": repo,
        "base_commit": f"base-{instance_id}",
        "environment_setup_commit": f"env-{instance_id}",
        "version": "1.0",
        "created_at": "2026-05-02T00:00:00Z",
        "problem_statement": f"Fix visible issue for {instance_id}.",
        "patch": f"SECRET_PATCH_{instance_id}",
        "test_patch": (
            "diff --git a/tests/test_hidden.py b/tests/test_hidden.py\n"
            f"+SECRET_TEST_PATCH_{instance_id}\n"
        ),
        "FAIL_TO_PASS": json.dumps([f"tests/test_{instance_id}.py::test_target"]),
        "PASS_TO_PASS": json.dumps([f"tests/test_{instance_id}.py::test_regression"]),
    }


def _source_field_sha256(row: dict[str, str]) -> dict[str, str]:
    import hashlib

    return {
        field_name: hashlib.sha256(row[field_name].encode("utf-8")).hexdigest()
        for field_name in (
            "repo",
            "instance_id",
            "base_commit",
            "environment_setup_commit",
            "patch",
            "test_patch",
            "problem_statement",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
        )
    }


def _set_expected_source_sha256_for_test(root: Path) -> None:
    fixture_module.EXPECTED_SOURCE_SHA256 = {
        "hf_dataset_schema": _file_ref(root / "hf_dataset_schema.json")["sha256"],
        "level2_dataset": _file_ref(root / "dataset" / "level2_dataset.jsonl")["sha256"],
        "candidate_task_manifest": _file_ref(root / "candidate_task_manifest.json")["sha256"],
        "selected_task_manifest": _file_ref(root / "level2" / "selected_task_manifest.json")[
            "sha256"
        ],
        "level2_gold_patch_predictions": _file_ref(
            root / "level2" / "gold_patch_predictions.jsonl"
        )["sha256"],
        "level1_gold_patch_prediction_sha256": _file_ref(
            root / "level1" / "gold_patch_prediction.sha256"
        )["sha256"],
        "level2_gold_patch_predictions_sha256": _file_ref(
            root / "level2" / "gold_patch_predictions.sha256"
        )["sha256"],
        "level1_official_report": _file_ref(
            root / "level1" / "gold_patch_feasibility_probe.level1.json"
        )["sha256"],
        "level2_official_report": _file_ref(
            root / "level2" / "gold_patch_feasibility_probe.level2.json"
        )["sha256"],
    }


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_named_sha256(path: Path, sha_path: Path) -> None:
    import hashlib

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sha_path.write_text(f"{digest}  {path.name}\n", encoding="utf-8")


def _write_sidecar_for_generated_file(path: Path) -> None:
    _write_named_sha256(path, Path(str(path) + ".sha256"))


def _file_ref(path: Path) -> dict[str, object]:
    import hashlib

    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }
