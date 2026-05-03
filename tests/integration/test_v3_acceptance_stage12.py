from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_base import stable_hash
from repo_harness.v3_acceptance import (
    V3_REQUIRED_RUN_SELECTION_ROLES,
    build_v3_acceptance_bundle,
    build_v3_acceptance_inputs,
    build_v3_acceptance_report,
    build_v3_run_selection_manifest,
    inspect_acceptance_bundle,
    inspect_tool_contract,
    inspect_trajectory_store,
    inspect_v3_acceptance,
)
from repo_harness.workspace.backend_status import build_workspace_backend_status


REQUIRED_DOCS = [
    "docs/v3/scope-and-roadmap.md",
    "docs/v3/implementation-plan.md",
    "docs/v3/review/scope-review.md",
    "docs/v3/review/implementation-plan-review.md",
    "docs/v3/review/swe-task-feasibility-results.md",
    "docs/v3/swe-task-feasibility-experiment-plan.md",
]
V2_ACCEPTANCE_REPORT = Path("runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json")


def test_v3_stage12_acceptance_flow_and_bundle(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    export_root = tmp_path / "v3_export_root"
    export_root.mkdir()
    (export_root / "export_manifest.json").write_text('{"schema_version":"test"}\n', encoding="utf-8")
    documentation_manifest = tmp_path / "pre_acceptance_documentation_manifest.json"
    documentation_manifest.write_text('{"docs":["stage logs","stage reviews"]}\n', encoding="utf-8")
    pre_command_log = tmp_path / "pre_acceptance_command_log.jsonl"
    _write_valid_command_log(pre_command_log)
    test_evidence = tmp_path / "pre_acceptance_evidence"
    test_evidence.mkdir()
    (test_evidence / "pytest.json").write_text('{"exit_code":0}\n', encoding="utf-8")

    acceptance_inputs = build_v3_acceptance_inputs(
        run_selection_manifest=run_selection,
        export_root=export_root,
        v2_report=V2_ACCEPTANCE_REPORT,
        pre_acceptance_docs=[Path(doc) for doc in REQUIRED_DOCS],
        documentation_manifest=documentation_manifest,
        command_log=pre_command_log,
        test_evidence=test_evidence,
        output=tmp_path / "v3_acceptance_inputs.json",
    )
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=acceptance_inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )

    assert "Inspect V3 acceptance: complete" in inspect_v3_acceptance(report, assert_complete=True)
    command_records = [
        json.loads(line)
        for line in (report.parent / "acceptance_command_log.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert command_records[0]["self_referential_output_paths"]

    final_doc = tmp_path / "final-acceptance.md"
    walkthrough = tmp_path / "walkthrough.md"
    final_doc.write_text("# Final acceptance\n", encoding="utf-8")
    walkthrough.write_text("# Walkthrough\n", encoding="utf-8")
    bundle = build_v3_acceptance_bundle(
        acceptance_dir=report.parent,
        input_manifest=report.parent / "acceptance_inputs_manifest.json",
        report=report,
        documentation_refs=[final_doc, walkthrough],
        output=report.parent / "acceptance_bundle_manifest.json",
    )
    assert "Inspect acceptance bundle: immutable" in inspect_acceptance_bundle(bundle, assert_immutable=True)

    final_doc.write_text("# Final acceptance changed\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="sha256"):
        inspect_acceptance_bundle(bundle, assert_immutable=True)


def test_v3_stage12_inspect_trajectory_and_tool_contract_negatives(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    assert "Inspect trajectory store: readable" in inspect_trajectory_store(run_dir, assert_readable=True)
    assert "Inspect tool contract: frozen" in inspect_tool_contract(run_dir, assert_frozen=True)

    polluted = _copy_tree(run_dir, tmp_path / "v3_stage_12_polluted")
    transcript = polluted / "transcript.jsonl"
    transcript.write_text(
        json.dumps(
            {
                "role": "user",
                "content_preview": "gold_patch must never be model visible",
                "model_visible": True,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="污染"):
        inspect_trajectory_store(polluted, assert_readable=True)

    missing_events = _copy_tree(run_dir, tmp_path / "v3_stage_12_missing_events")
    (missing_events / "events.jsonl").unlink()
    with pytest.raises(ConfigError, match="events.jsonl"):
        inspect_trajectory_store(missing_events, assert_readable=True)

    bad_artifact = _copy_tree(run_dir, tmp_path / "v3_stage_12_bad_artifact")
    artifact_path = next((bad_artifact / "artifacts").glob("*tool_schema_snapshot.json"))
    artifact_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="sha256"):
        inspect_trajectory_store(bad_artifact, assert_readable=True)

    missing_tool_snapshot = _copy_tree(run_dir, tmp_path / "v3_stage_12_missing_tool_snapshot")
    facts = _read_json(missing_tool_snapshot / "run_config_facts.json")
    del facts["tool_protocol"]["tool_schema_snapshot_ref"]
    _write_json(missing_tool_snapshot / "run_config_facts.json", facts)
    with pytest.raises(ConfigError, match="tool_schema_snapshot_ref"):
        inspect_tool_contract(missing_tool_snapshot, assert_frozen=True)


def test_v3_stage12_acceptance_negative_inputs(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)

    existing_acceptance = tmp_path / "existing_acceptance"
    existing_acceptance.mkdir()
    with pytest.raises(ConfigError, match="不存在的新目录"):
        build_v3_acceptance_report(
            acceptance_dir=existing_acceptance,
            input_manifest=inputs,
            output=existing_acceptance / "v3_acceptance_report.json",
        )

    polluted_inputs = tmp_path / "polluted_inputs.json"
    payload = _read_json(inputs)
    payload["prompt"] = "gold_patch"
    _write_json(polluted_inputs, payload)
    with pytest.raises(ConfigError, match="污染"):
        build_v3_acceptance_report(
            acceptance_dir=tmp_path / "polluted_acceptance",
            input_manifest=polluted_inputs,
            output=tmp_path / "polluted_acceptance" / "v3_acceptance_report.json",
        )

    official_inputs = tmp_path / "official_inputs.json"
    payload = _read_json(inputs)
    payload["official_harness_report"] = {"status": "resolved"}
    _write_json(official_inputs, payload)
    with pytest.raises(ConfigError, match="official"):
        build_v3_acceptance_report(
            acceptance_dir=tmp_path / "official_acceptance",
            input_manifest=official_inputs,
            output=tmp_path / "official_acceptance" / "v3_acceptance_report.json",
        )

    checkpoint_inputs = tmp_path / "checkpoint_inputs.json"
    payload = _read_json(inputs)
    payload["checkpoint"] = {"reward_metadata": "hidden score"}
    payload["context_compaction_report"] = {"final_verifier_hidden_result": "leak"}
    _write_json(checkpoint_inputs, payload)
    with pytest.raises(ConfigError, match="污染"):
        build_v3_acceptance_report(
            acceptance_dir=tmp_path / "checkpoint_acceptance",
            input_manifest=checkpoint_inputs,
            output=tmp_path / "checkpoint_acceptance" / "v3_acceptance_report.json",
        )

    fake_v2 = tmp_path / "fake_v2_acceptance_report.json"
    fake_v2.write_text('{"status":"passed"}\n', encoding="utf-8")
    fake_v2_inputs = build_v3_acceptance_inputs(
        run_selection_manifest=run_selection,
        export_root=tmp_path / "v3_export_root",
        v2_report=fake_v2,
        pre_acceptance_docs=[Path(doc) for doc in REQUIRED_DOCS],
        documentation_manifest=tmp_path / "pre_acceptance_documentation_manifest.json",
        command_log=tmp_path / "pre_acceptance_command_log.jsonl",
        test_evidence=tmp_path / "pre_acceptance_evidence",
        output=tmp_path / "fake_v2_inputs.json",
    )
    fake_v2_report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "fake_v2_acceptance",
        input_manifest=fake_v2_inputs,
        output=tmp_path / "fake_v2_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="V2 acceptance report 复查失败"):
        inspect_v3_acceptance(fake_v2_report, assert_complete=True)


def test_v3_stage12_acceptance_inspect_detects_tampering(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    assert "Inspect V3 acceptance: complete" in inspect_v3_acceptance(report, assert_complete=True)

    command_log = report.parent / "acceptance_command_log.jsonl"
    command_log.write_text(command_log.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="command_log_ref sha256"):
        inspect_v3_acceptance(report, assert_complete=True)

    report_payload = _read_json(report)
    report_payload["input_manifest_ref"]["sha256"] = "0" * 64
    tampered_report = report.parent / "tampered_report.json"
    _write_json(tampered_report, report_payload)
    with pytest.raises(ConfigError, match="sha256"):
        inspect_v3_acceptance(tampered_report, assert_complete=False)


def test_v3_stage12_acceptance_rejects_selected_docker_run_missing_verifier_phase(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    bad_swebench_run = _make_minimal_v3_run(
        tmp_path / "v3_stage_12_bad_swebench_run",
        missing_docker_phase="fail_to_pass_test_execution",
    )
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    replacement = build_v3_run_selection_manifest(
        run_refs=[f"role=swebench_like,path={bad_swebench_run}"],
        output=tmp_path / "bad_swebench_selection.json",
    )
    bad_entry = _read_json(replacement)["entries"][0]
    payload = _read_json(run_selection)
    for entry in payload["entries"]:
        if entry["role"] == "swebench_like":
            entry.update(bad_entry)
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="docker phase coverage 缺失：fail_to_pass_test_execution"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_scans_bound_prepared_messages_artifact(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(
        tmp_path / "v3_stage_12_run",
        prepared_message_content="model visible gold_patch leak",
    )
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    report_payload = _read_json(report)
    assert report_payload["status"] == "failed"
    with pytest.raises(ConfigError, match="prepared_messages|prompt"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_bundle_rechecks_report_transitively(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    acceptance_dir = tmp_path / "v3_acceptance"
    acceptance_dir.mkdir()
    _write_valid_command_log(acceptance_dir / "acceptance_command_log.jsonl")
    final_doc = tmp_path / "final-acceptance.md"
    walkthrough = tmp_path / "walkthrough.md"
    final_doc.write_text("# Final acceptance\n", encoding="utf-8")
    walkthrough.write_text("# Walkthrough\n", encoding="utf-8")
    bad_report = acceptance_dir / "v3_acceptance_report.json"
    input_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "bad_report_input_ref",
        "relative_path": inputs.as_posix(),
        "kind": "json",
        "sha256": sha256_file(inputs),
        "size_bytes": inputs.stat().st_size,
        "created_by_event_id": "bad_report",
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    _write_json(
        bad_report,
        {
            "schema_version": "repo_harness_v3_acceptance_report_v0",
            "acceptance_id": "bad",
            "status": "passed",
            "input_manifest_ref": input_ref,
        },
    )
    bundle = build_v3_acceptance_bundle(
        acceptance_dir=acceptance_dir,
        input_manifest=inputs,
        report=bad_report,
        documentation_refs=[final_doc, walkthrough],
        output=acceptance_dir / "acceptance_bundle_manifest.json",
    )
    with pytest.raises(ConfigError, match="传递性复查 v3_acceptance_report 失败"):
        inspect_acceptance_bundle(bundle, assert_immutable=True)


def test_v3_stage12_acceptance_bundle_rejects_post_docs_in_report_inputs(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    final_doc = tmp_path / "final-acceptance.md"
    walkthrough = tmp_path / "walkthrough.md"
    final_doc.write_text("# Final acceptance\n", encoding="utf-8")
    walkthrough.write_text("# Walkthrough\n", encoding="utf-8")
    documentation_manifest = tmp_path / "pre_acceptance_documentation_manifest.json"
    documentation_manifest.write_text(
        json.dumps({"implementation_log_refs": [{"path": final_doc.as_posix()}]}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    export_root = tmp_path / "v3_export_root"
    export_root.mkdir()
    (export_root / "export_manifest.json").write_text('{"schema_version":"test"}\n', encoding="utf-8")
    command_log = tmp_path / "pre_acceptance_command_log.jsonl"
    _write_valid_command_log(command_log)
    evidence = tmp_path / "pre_acceptance_evidence"
    evidence.mkdir()
    (evidence / "pytest.json").write_text('{"exit_code":0}\n', encoding="utf-8")
    inputs = build_v3_acceptance_inputs(
        run_selection_manifest=run_selection,
        export_root=export_root,
        v2_report=V2_ACCEPTANCE_REPORT,
        pre_acceptance_docs=[Path(doc) for doc in REQUIRED_DOCS],
        documentation_manifest=documentation_manifest,
        command_log=command_log,
        test_evidence=evidence,
        output=tmp_path / "v3_acceptance_inputs.json",
    )
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    bundle = build_v3_acceptance_bundle(
        acceptance_dir=report.parent,
        input_manifest=report.parent / "acceptance_inputs_manifest.json",
        report=report,
        documentation_refs=[final_doc, walkthrough],
        output=report.parent / "acceptance_bundle_manifest.json",
    )

    with pytest.raises(ConfigError, match="post-acceptance documentation"):
        inspect_acceptance_bundle(bundle, assert_immutable=True)


def test_v3_stage12_acceptance_bundle_allows_explicitly_excluded_post_docs(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    final_doc = tmp_path / "final-acceptance.md"
    walkthrough = tmp_path / "walkthrough.md"
    final_doc.write_text("# Final acceptance\n", encoding="utf-8")
    walkthrough.write_text("# Walkthrough\n", encoding="utf-8")
    documentation_manifest = tmp_path / "pre_acceptance_documentation_manifest.json"
    documentation_manifest.write_text(
        json.dumps(
            {
                "documentation_refs": [{"path": "docs/v3/implementation-log/stage-00.md"}],
                "excluded_post_acceptance_docs": [final_doc.as_posix(), walkthrough.as_posix()],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    export_root = tmp_path / "v3_export_root"
    export_root.mkdir()
    (export_root / "export_manifest.json").write_text('{"schema_version":"test"}\n', encoding="utf-8")
    command_log = tmp_path / "pre_acceptance_command_log.jsonl"
    _write_valid_command_log(command_log)
    evidence = tmp_path / "pre_acceptance_evidence"
    evidence.mkdir()
    (evidence / "pytest.json").write_text('{"exit_code":0}\n', encoding="utf-8")
    inputs = build_v3_acceptance_inputs(
        run_selection_manifest=run_selection,
        export_root=export_root,
        v2_report=V2_ACCEPTANCE_REPORT,
        pre_acceptance_docs=[Path(doc) for doc in REQUIRED_DOCS],
        documentation_manifest=documentation_manifest,
        command_log=command_log,
        test_evidence=evidence,
        output=tmp_path / "v3_acceptance_inputs.json",
    )
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    bundle = build_v3_acceptance_bundle(
        acceptance_dir=report.parent,
        input_manifest=report.parent / "acceptance_inputs_manifest.json",
        report=report,
        documentation_refs=[final_doc, walkthrough],
        output=report.parent / "acceptance_bundle_manifest.json",
    )

    assert "Inspect acceptance bundle: immutable" in inspect_acceptance_bundle(bundle, assert_immutable=True)


def test_v3_stage12_acceptance_detects_credential_skip_disguised_as_accepted(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    payload = _read_json(run_selection)
    for entry in payload["entries"]:
        if entry["role"] == "credential_gated_real_provider":
            entry["structured_skip_reason"] = "missing_credentials"
            entry["accepted"] = True
            entry["run_state"] = "accepted"
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="credential-gated"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_rejects_wrong_provider_and_failed_role(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    payload = _read_json(run_selection)
    for entry in payload["entries"]:
        if entry["role"] == "credential_gated_real_provider":
            entry["provider"] = "replay"
            entry["actual_provider"] = "replay"
            entry["requested_provider"] = "replay"
        if entry["role"] == "swebench_like":
            entry["accepted"] = True
            entry["run_state"] = "failed"
            entry["run_outcome"] = "failed"
            entry["final_verifier_status"] = "failed"
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="credential-gated|swebench_like"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_rejects_replay_core_agent_loop_roles(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    payload = _read_json(run_selection)
    replay_entry = next(entry for entry in payload["entries"] if entry["role"] == "replay")
    for entry in payload["entries"]:
        if entry["role"] in {"real_repository", "swebench_like"}:
            entry["path_ref"] = replay_entry["path_ref"]
            entry["evidence_refs"] = replay_entry["evidence_refs"]
            entry["provider"] = "replay"
            entry["actual_provider"] = "replay"
            entry["requested_provider"] = "replay"
            entry["accepted"] = True
            entry["run_state"] = "success"
            entry["run_outcome"] = "success"
            entry["final_verifier_status"] = "accepted"
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="real_repository|swebench_like"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_rejects_core_agent_loop_structured_skip(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    payload = _read_json(run_selection)
    for entry in payload["entries"]:
        if entry["role"] == "real_repository":
            entry["structured_skip_reason"] = "temporarily unavailable"
            entry["accepted"] = False
            entry["run_state"] = "skipped"
            entry["run_outcome"] = "skipped"
            entry["final_verifier_status"] = "skipped"
            break
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="不能用 structured skip"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_rejects_replay_identity_on_credential_skip(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    payload = _read_json(run_selection)
    replay_entry = next(entry for entry in payload["entries"] if entry["role"] == "replay")
    for entry in payload["entries"]:
        if entry["role"] == "credential_gated_real_provider":
            entry["structured_skip_reason"] = "missing_credentials"
            entry["path_ref"] = replay_entry["path_ref"]
            entry["evidence_refs"] = replay_entry["evidence_refs"]
            entry.pop("provider", None)
            entry.pop("actual_provider", None)
            entry.pop("requested_provider", None)
            entry["accepted"] = False
            entry["run_state"] = "skipped"
            entry["run_outcome"] = "skipped"
            entry["final_verifier_status"] = "skipped"
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="replay/mock"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_rejects_bound_failed_run_even_when_manifest_claims_success(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    failed_real_provider = _make_minimal_v3_run(
        tmp_path / "v3_stage_12_failed_real_provider_run",
        provider="deepseek",
        run_outcome="failed",
        final_verifier_status="failed",
    )
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    replacement = build_v3_run_selection_manifest(
        run_refs=[f"role=credential_gated_real_provider,path={failed_real_provider}"],
        output=tmp_path / "failed_real_provider_selection.json",
    )
    failed_entry = _read_json(replacement)["entries"][0]
    payload = _read_json(run_selection)
    for entry in payload["entries"]:
        if entry["role"] == "credential_gated_real_provider":
            entry["path_ref"] = failed_entry["path_ref"]
            entry["evidence_refs"] = failed_entry["evidence_refs"]
            entry["provider"] = "deepseek"
            entry["actual_provider"] = "deepseek"
            entry["requested_provider"] = "deepseek"
            entry["accepted"] = True
            entry["run_state"] = "success"
            entry["run_outcome"] = "success"
            entry["final_verifier_status"] = "accepted"
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="credential-gated"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_rejects_replay_identity_in_neutral_evidence_ref(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    payload = _read_json(run_selection)
    replay_entry = next(entry for entry in payload["entries"] if entry["role"] == "replay")
    real_entry = next(entry for entry in payload["entries"] if entry["role"] == "credential_gated_real_provider")
    replay_config_ref = replay_entry["evidence_refs"]["run_config_facts.json"]
    for entry in payload["entries"]:
        if entry["role"] == "credential_gated_real_provider":
            entry["structured_skip_reason"] = "missing_credentials"
            entry["path_ref"] = real_entry["path_ref"]
            entry["evidence_refs"] = {"smoke_report": replay_config_ref}
            entry["accepted"] = False
            entry["run_state"] = "skipped"
            entry["run_outcome"] = "skipped"
            entry["final_verifier_status"] = "skipped"
    _write_json(run_selection, payload)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=inputs,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="replay/mock"):
        inspect_v3_acceptance(report, assert_complete=True)


def test_v3_stage12_acceptance_requires_complete_categories(tmp_path: Path) -> None:
    run_dir = _make_minimal_v3_run(tmp_path / "v3_stage_12_run")
    run_selection = _build_full_run_selection(tmp_path, run_dir)
    inputs = _minimal_acceptance_inputs(tmp_path, run_selection)
    payload = _read_json(inputs)
    del payload["input_refs_by_category"]["test_evidence"]
    incomplete = tmp_path / "incomplete_inputs.json"
    _write_json(incomplete, payload)
    report = build_v3_acceptance_report(
        acceptance_dir=tmp_path / "v3_acceptance",
        input_manifest=incomplete,
        output=tmp_path / "v3_acceptance" / "v3_acceptance_report.json",
    )
    with pytest.raises(ConfigError, match="test_evidence"):
        inspect_v3_acceptance(report, assert_complete=True)


def _minimal_acceptance_inputs(tmp_path: Path, run_selection: Path) -> Path:
    export_root = tmp_path / "v3_export_root"
    export_root.mkdir(exist_ok=True)
    (export_root / "export_manifest.json").write_text('{"schema_version":"test"}\n', encoding="utf-8")
    v2_report = V2_ACCEPTANCE_REPORT
    documentation_manifest = tmp_path / "pre_acceptance_documentation_manifest.json"
    documentation_manifest.write_text('{"docs":["stage logs","stage reviews"]}\n', encoding="utf-8")
    command_log = tmp_path / "pre_acceptance_command_log.jsonl"
    _write_valid_command_log(command_log)
    evidence = tmp_path / "pre_acceptance_evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "pytest.json").write_text('{"exit_code":0}\n', encoding="utf-8")
    return build_v3_acceptance_inputs(
        run_selection_manifest=run_selection,
        export_root=export_root,
        v2_report=v2_report,
        pre_acceptance_docs=[Path(doc) for doc in REQUIRED_DOCS],
        documentation_manifest=documentation_manifest,
        command_log=command_log,
        test_evidence=evidence,
        output=tmp_path / "v3_acceptance_inputs.json",
    )


def _build_full_run_selection(tmp_path: Path, run_dir: Path) -> Path:
    mock_run = _make_minimal_v3_run(tmp_path / "v3_stage_12_mock_run", provider="mock")
    real_provider_run = _make_minimal_v3_run(
        tmp_path / "v3_stage_12_real_provider_run",
        provider="deepseek",
    )
    real_repository_run = _make_minimal_v3_run(
        tmp_path / "v3_stage_12_real_repository_run",
        provider="deepseek",
    )
    swebench_like_run = _make_minimal_v3_run(
        tmp_path / "v3_stage_12_swebench_like_run",
        provider="deepseek",
    )
    role_paths = {
        "mock_provider": mock_run,
        "credential_gated_real_provider": real_provider_run,
        "real_repository": real_repository_run,
        "swebench_like": swebench_like_run,
    }
    return build_v3_run_selection_manifest(
        run_refs=[
            f"role={role},path={role_paths.get(role, run_dir)}"
            for role in V3_REQUIRED_RUN_SELECTION_ROLES
        ],
        output=tmp_path / "v3_run_selection_manifest.json",
    )


def _make_minimal_v3_run(
    run_dir: Path,
    *,
    provider: str = "replay",
    run_outcome: str = "success",
    final_verifier_status: str = "accepted",
    missing_docker_phase: str | None = None,
    prepared_message_content: str = "safe public task context",
) -> Path:
    run_dir.mkdir(parents=True)
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir()
    canonical_tool_payload = {
        "tool_order": ["read_file"],
        "tool_parser_version": "repo_harness_tool_call_parser_v0",
        "tool_result_format_version": "repo_harness_tool_result_v0",
        "tools": [
            {
                "schema_version": "repo_harness_tool_schema_entry_v2_v0",
                "name": "read_file",
                "tool_version": "repo_harness_read_file_v0",
                "model_visible_description": "Read a file.",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "tool_result_format_version": "repo_harness_tool_result_v0",
                "read_only": True,
                "destructive": False,
                "permission_required": True,
                "max_output_chars": 4000,
            }
        ],
    }
    snapshot_sha = stable_hash(canonical_tool_payload)
    snapshot_payload = {
        "schema_version": "repo_harness_tool_schema_snapshot_v2_v0",
        "snapshot_id": f"tool_schema_snapshot_{snapshot_sha[:12]}",
        "snapshot_sha256": snapshot_sha,
        **canonical_tool_payload,
    }
    snapshot_path = artifacts_dir / "v3_stage_12_run_artifact_000001_tool_schema_snapshot.json"
    _write_json(snapshot_path, snapshot_payload)
    snapshot_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "v3_stage_12_run_artifact_000001",
        "relative_path": "artifacts/v3_stage_12_run_artifact_000001_tool_schema_snapshot.json",
        "kind": "tool_schema_snapshot",
        "sha256": sha256_file(snapshot_path),
        "size_bytes": snapshot_path.stat().st_size,
        "created_by_event_id": "event_001",
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    prepared_messages_path = artifacts_dir / "v3_stage_12_run_artifact_000002_prepared_messages.json"
    _write_json(
        prepared_messages_path,
        {
            "provider_format": "chat",
            "context_revision": 1,
            "model_input_hash": "b" * 64,
            "messages": [
                {
                    "role": "system",
                    "content": "RepoHarness test system prompt.",
                },
                {
                    "role": "user",
                    "content": prepared_message_content,
                },
            ],
        },
    )
    prepared_messages_ref = {
        "schema_version": "repo_harness_artifact_v0",
        "artifact_id": "v3_stage_12_run_artifact_000002",
        "relative_path": "artifacts/v3_stage_12_run_artifact_000002_prepared_messages.json",
        "kind": "prepared_messages",
        "sha256": sha256_file(prepared_messages_path),
        "size_bytes": prepared_messages_path.stat().st_size,
        "created_by_event_id": "event_002",
        "redaction_status": "not_scanned",
        "retention_policy": "keep",
    }
    _write_json(
        run_dir / "artifacts.json",
        {
            "schema_version": "repo_harness_schema_v0",
            "run_id": "v3_stage_12_run",
            "artifacts": [snapshot_ref, prepared_messages_ref],
        },
    )
    run_config = {
        "schema_version": "repo_harness_run_config_facts_v2_v0",
        "run_id": "v3_stage_12_run",
        "task_id": "v3_stage_12_task",
        "tool_protocol": {
            "schema_version": "repo_harness_tool_protocol_facts_v2_v0",
            "tool_schema_snapshot_ref": snapshot_ref,
            "tool_schema_snapshot_sha256": snapshot_sha,
            "tool_order": ["read_file"],
            "tool_parser_version": "repo_harness_tool_call_parser_v0",
            "tool_result_format_version": "repo_harness_tool_result_v0",
            "tool_policy_version": "repo_harness_tools_v0",
        },
        "allowed_tools_policy": "repo_harness_stage12_policy_v0",
        "permission_mode": "auto",
        "permission_policy_version": "repo_harness_permissions_v0",
        "shell_command_policy_version": "repo_harness_command_policy_v0",
        "context_policy_version": "repo_harness_context_policy_v0",
        "context_builder_version": "repo_harness_context_v0",
        "provider": provider,
        "actual_provider": provider,
        "requested_provider": provider,
        "environment_fingerprint": {
            "workspace_execution": {
                "workspace_backend": {"backend": "docker"},
                "source_checkout": {"source_tree_hash": "a" * 64},
            }
        },
    }
    _write_json(run_dir / "run_config_facts.json", run_config)
    config_sha = sha256_file(run_dir / "run_config_facts.json")
    _write_json(
        run_dir / "run_metadata.json",
        {
            "schema_version": "repo_harness_run_metadata_v2_v0",
            "run_id": "v3_stage_12_run",
            "run_status": "completed",
            "run_outcome": run_outcome,
            "final_verifier_status": final_verifier_status,
            "run_config_facts_ref": {
                "schema_version": "repo_harness_run_config_facts_ref_v2_v0",
                "kind": "run_config_facts",
                "relative_path": "run_config_facts.json",
                "sha256": config_sha,
            },
            "tool_protocol": {"tool_schema_snapshot_ref": snapshot_ref},
        },
    )
    _write_json(
        run_dir / "metrics.json",
        {
            "schema_version": "repo_harness_metrics_v0",
            "run_outcome": run_outcome,
            "final_verifier_status": final_verifier_status,
        },
    )
    _write_json(run_dir / "run_status.json", {"schema_version": "repo_harness_schema_v0", "run_id": "v3_stage_12_run", "status": "FINALIZED"})
    (run_dir / "events.jsonl").write_text(
        '{"event_type":"model_call_started"}\n{"event_type":"completed"}\n',
        encoding="utf-8",
    )
    (run_dir / "transcript.jsonl").write_text(
        json.dumps(
            {
                "role": "assistant",
                "content_preview": "safe public answer",
                "model_visible": True,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "summary.md").write_text("# Summary\n", encoding="utf-8")
    _write_docker_backend_status(run_dir, missing_phase=missing_docker_phase)
    return run_dir


def _write_docker_backend_status(run_dir: Path, *, missing_phase: str | None = None) -> None:
    executed_specs = _docker_phase_specs()
    facts_refs = [
        f"container_execution_facts/{phase}.json"
        for phase, _, _ in executed_specs
    ]
    status = build_workspace_backend_status(
        mode="docker_backend",
        docker_available=True,
        docker_available_reason="test_docker_available",
        docker_context="desktop-linux",
        docker_server_platform="linux",
        docker_server_architecture="arm64",
        docker_mem_total_bytes=32 * 1024 * 1024 * 1024,
        evaluation_concurrency=1,
        swebench_like_effective_max_workers=1,
        requested_container_platform="linux/arm64",
        container_uname_m="aarch64",
        image_id="a" * 64,
        image_platform="linux/arm64",
        build_mode="prebuilt",
        network_policy="deny_agent_run",
        mount_policy="workspace_read_write_tmp_only",
        command_timeout_sec=60,
        cleanup_policy="remove_containers_keep_images",
        cleanup_status="completed",
        docker_backend_facts_ref="docker_backend_facts.json",
        container_execution_facts_refs=facts_refs,
        container_execution_manifest_ref="container_execution_facts/manifest.json",
        docker_phase_coverage_matrix_ref="docker_phase_coverage_matrix.json",
    )
    _write_json(run_dir / "docker_backend_status.json", status.model_dump(mode="json"))
    _write_json(
        run_dir / "docker_backend_facts.json",
        {
            "schema_version": "repo_harness_docker_backend_facts_v3_v0",
            "backend": "docker",
            "backend_version": "repo_harness_docker_backend_v3_v0",
            "docker_context": "desktop-linux",
            "docker_cli_version": "test",
            "docker_server_version": "test",
            "server_platform": "linux",
            "server_architecture": "arm64",
            "requested_container_platform": "linux/arm64",
            "image_ref": "repo-harness-v3-test",
            "image_id": "a" * 64,
            "image_platform": "linux/arm64",
            "build_mode": "prebuilt",
            "cross_architecture_emulation": False,
            "network_policy": "deny_agent_run",
            "mount_policy": "workspace_read_write_tmp_only",
            "timeout_sec": 60,
            "cleanup_policy": "remove_containers_keep_images",
            "cleanup_status": "completed",
        },
    )
    for phase, semantics, _manifest_phase in executed_specs:
        _write_json(
            run_dir / f"container_execution_facts/{phase}.json",
            {
                "schema_version": "repo_harness_container_execution_facts_v3_v0",
                "command_id": f"cmd_{phase}",
                "container_id": "container",
                "image_id": "a" * 64,
                "requested_container_platform": "linux/arm64",
                "container_uname_m": "aarch64",
                "command": ["python", "-c", "pass"],
                "command_semantics": semantics,
                "workdir": "/repo-harness-run/workspaces/source_checkout",
                "exit_code": 0,
                "timeout": False,
                "duration_ms": 1,
                "network_policy": "deny_agent_run",
                "mount_policy": "workspace_read_write_tmp_only",
                "cleanup_status": "completed",
            },
        )
    _write_json(
        run_dir / "container_execution_facts" / "manifest.json",
        {
            "schema_version": "repo_harness_container_execution_manifest_v3_v0",
            "run_id": run_dir.name,
            "entry_count": len(executed_specs),
            "entries": [
                {
                    "command_id": f"cmd_{phase}",
                    "facts_ref": f"container_execution_facts/{phase}.json",
                    "command_semantics": semantics,
                    "phase": manifest_phase,
                    "exit_code": 0,
                    "timeout": False,
                    "cleanup_status": "completed",
                }
                for phase, semantics, manifest_phase in executed_specs
            ],
        },
    )
    required_phases = [
        "source_checkout",
        "setup",
        "agent_tool",
        "run_tests",
        "final_patch_capture",
        "verification_workspace_creation",
        "verifier_patch_apply",
        "test_patch_apply",
        "model_final_patch_apply",
        "fail_to_pass_test_execution",
        "pass_to_pass_test_execution",
        "final_verifier",
    ]
    _write_json(
        run_dir / "docker_phase_coverage_matrix.json",
        {
            "schema_version": "repo_harness_docker_phase_coverage_matrix_v3_v0",
            "run_id": run_dir.name,
            "container_execution_manifest_ref": "container_execution_facts/manifest.json",
            "required_phases": required_phases,
            "phases": [
                {
                    "phase": phase,
                    "status": (
                        "missing"
                        if phase == missing_phase
                        else "not_applicable"
                        if phase in {"verifier_patch_apply", "test_patch_apply"}
                        else "passed"
                    ),
                    "structured_reason": (
                        "no verifier patch is configured for this task"
                        if phase == "verifier_patch_apply"
                        else "no test patch is configured for this task"
                        if phase in {"verifier_patch_apply", "test_patch_apply"} and phase != missing_phase
                        else None
                    ),
                    "facts_refs": (
                        []
                        if phase == missing_phase or phase in {"verifier_patch_apply", "test_patch_apply"}
                        else [f"container_execution_facts/{phase}.json"]
                    ),
                }
                for phase in required_phases
            ],
        },
    )


def _docker_phase_specs() -> list[tuple[str, str, str]]:
    return [
        ("source_checkout", "source_checkout", "source_checkout"),
        ("setup", "setup", "setup"),
        ("agent_tool", "file_read", "agent_tool"),
        ("run_tests", "verifier_feedback", "run_tests"),
        ("final_patch_capture", "final_patch_capture", "final_patch_capture"),
        (
            "verification_workspace_creation",
            "verification_workspace_creation",
            "verification_workspace_creation",
        ),
        ("model_final_patch_apply", "model_final_patch_apply", "model_final_patch_apply"),
        (
            "fail_to_pass_test_execution",
            "fail_to_pass_test_execution",
            "fail_to_pass_test_execution",
        ),
        (
            "pass_to_pass_test_execution",
            "pass_to_pass_test_execution",
            "pass_to_pass_test_execution",
        ),
        ("final_verifier", "verifier_final", "final_verifier"),
    ]


def _copy_tree(source: Path, target: Path) -> Path:
    import shutil

    shutil.copytree(source, target)
    return target


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_valid_command_log(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_command_log_entry_v3_v0",
                "command_name": "pre-acceptance-test",
                "argv": ["python", "-m", "pytest", "-q"],
                "cwd": str(Path.cwd()),
                "input_refs": [],
                "output_refs": [],
                "exit_code": 0,
                "tool_or_cli_version": "pytest",
                "started_at": "2026-05-03T00:00:00Z",
                "finished_at": "2026-05-03T00:00:01Z",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
