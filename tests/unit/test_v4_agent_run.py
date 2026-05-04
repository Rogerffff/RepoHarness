import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.schema_versions import (
    V4_ROLLOUT_QUEUE_MANIFEST_VERSION,
    V4_TASK_FREEZE_MANIFEST_VERSION,
    V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
    V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
)
from repo_harness.v4_agent_run import (
    build_v4_agent_run_integration,
    inspect_v4_agent_run_integration,
    inspect_v4_trajectory_store,
)


def test_v4_agent_run_build_and_inspect_pass(tmp_path: Path) -> None:
    report = build_v4_agent_run_integration(output_dir=tmp_path / "agent", **_external_inputs(tmp_path))
    run_dir = report.parent

    assert "complete" in inspect_v4_agent_run_integration(run_dir, assert_complete=True)
    assert "readable" in inspect_v4_trajectory_store(run_dir, assert_readable=True)
    assert main(["inspect-v4-agent-run-integration", str(run_dir), "--assert-complete"]) == 0
    assert main(["inspect-v4-trajectory-store", str(run_dir), "--assert-readable"]) == 0


def test_v4_agent_run_rejects_final_verifier_in_model_visible_observation(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    events_path = run_dir / "runs" / "v4-run-completed-001" / "events.jsonl"
    records = _read_jsonl(events_path)
    records[1]["model_visible_payload"] = "final_verifier_result accepted"
    _write_jsonl(events_path, records)

    with pytest.raises(ConfigError, match="final verifier result"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_final_verifier_in_tool_observation_artifact(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    observation = run_dir / "runs" / "v4-run-completed-001" / "tool_observation.json"
    payload = _read_json(observation)
    payload["content"] = "The final_verifier_result was accepted."
    _write_json(observation, payload)

    with pytest.raises(ConfigError, match="final verifier result"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_final_verifier_in_transcript(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    transcript_path = run_dir / "runs" / "v4-run-completed-001" / "transcript.jsonl"
    records = _read_jsonl(transcript_path)
    records[0]["content"] = "The final_verifier_result was accepted."
    _write_jsonl(transcript_path, records)

    with pytest.raises(ConfigError, match="final verifier result"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_final_verifier_in_prepared_messages(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    prepared = run_dir / "runs" / "v4-run-completed-001" / "prepared_messages.json"
    payload = _read_json(prepared)
    payload["messages"][1]["content"] = "The hidden final_verifier_result was accepted."
    _write_json(prepared, payload)

    with pytest.raises(ConfigError, match="final verifier result"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_final_verifier_in_model_visible_artifact(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    observation = run_dir / "runs" / "v4-run-completed-001" / "tool_observation.json"
    payload = _read_json(observation)
    payload["content"] = "accepted final_verifier_result"
    _write_json(observation, payload)

    with pytest.raises(ConfigError, match="final verifier result"):
        inspect_v4_trajectory_store(run_dir, assert_readable=True)


@pytest.mark.parametrize("field", ["scaffold_id", "tool_policy_id", "verifier_id", "environment_id"])
def test_v4_agent_run_rejects_missing_runspec_metadata(tmp_path: Path, field: str) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "runspec_metadata_report.json"
    payload = _read_json(report)
    payload["run_metadata_records"][0]["metadata"][field] = ""
    _write_json(report, payload)

    with pytest.raises(ConfigError, match=field):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_fallback_success_without_policy_ref(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "runspec_metadata_report.json"
    payload = _read_json(report)
    payload["run_metadata_records"][0]["metadata"]["provider_error_category"] = "fallback_success"
    payload["run_metadata_records"][0]["metadata"]["fallback_policy_id"] = ""
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="fallback policy"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_trajectory_store_rejects_artifact_sha_mismatch(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    artifacts = run_dir / "runs" / "v4-run-completed-001" / "artifacts.json"
    payload = _read_json(artifacts)
    payload["artifacts"][0]["sha256"] = "0" * 64
    _write_json(artifacts, payload)

    with pytest.raises(ConfigError, match="sha256"):
        inspect_v4_trajectory_store(run_dir, assert_readable=True)


def test_v4_trajectory_store_rejects_missing_artifact_not_marked_half_written(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    patch_path = run_dir / "runs" / "v4-run-completed-001" / "final.patch"
    patch_path.unlink()

    with pytest.raises(ConfigError, match="half_written|final.patch"):
        inspect_v4_trajectory_store(run_dir, assert_readable=True)


def test_v4_trajectory_store_rejects_duplicate_record_and_event_ids(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    completed = run_dir / "runs" / "v4-run-completed-001"
    transcript = _read_jsonl(completed / "transcript.jsonl")
    transcript[1]["record_id"] = transcript[0]["record_id"]
    _write_jsonl(completed / "transcript.jsonl", transcript)
    events = _read_jsonl(completed / "events.jsonl")
    events[1]["event_id"] = events[0]["event_id"]
    _write_jsonl(completed / "events.jsonl", events)

    with pytest.raises(ConfigError, match="重复|不稳定"):
        inspect_v4_trajectory_store(run_dir, assert_readable=True)


def test_v4_trajectory_store_rejects_duplicate_terminal_facts(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    events_path = run_dir / "runs" / "v4-run-completed-001" / "events.jsonl"
    events = _read_jsonl(events_path)
    duplicate = dict(events[2])
    duplicate["event_id"] = "event-v4-run-completed-001-duplicate-terminal"
    duplicate["offset"] = len(events)
    events.append(duplicate)
    _write_jsonl(events_path, events)

    with pytest.raises(ConfigError, match="terminal facts"):
        inspect_v4_trajectory_store(run_dir, assert_readable=True)


def test_v4_agent_run_rejects_prepared_messages_binding_gaps(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "prepared_messages_binding_report.json"
    payload = _read_json(report)
    payload["binding_records"][0].pop("content_replacement_state_hash")
    payload["binding_records"][0].pop("observation_source_event_ref")
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="PreparedMessages|observation_source_event_ref"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_prepared_messages_tool_schema_hash_drift(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "prepared_messages_binding_report.json"
    payload = _read_json(report)
    payload["binding_records"][0]["tool_schema_snapshot_hash"] = "0" * 64
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="tool_schema_snapshot_hash"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_empty_prepared_messages_binding_records(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "prepared_messages_binding_report.json"
    payload = _read_json(report)
    payload["binding_records"] = []
    _write_json(report, payload)
    _refresh_integration_report_ref(run_dir, "prepared_messages_binding_report_ref", report)

    with pytest.raises(ConfigError, match="binding_records"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_partial_prepared_messages_binding_records(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "prepared_messages_binding_report.json"
    payload = _read_json(report)
    payload["binding_records"] = payload["binding_records"][:1]
    _write_json(report, payload)
    _refresh_integration_report_ref(run_dir, "prepared_messages_binding_report_ref", report)

    with pytest.raises(ConfigError, match="覆盖每个 trajectory run"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_duplicate_prepared_messages_binding_run_id(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "prepared_messages_binding_report.json"
    payload = _read_json(report)
    payload["binding_records"].append(dict(payload["binding_records"][0]))
    _write_json(report, payload)
    _refresh_integration_report_ref(run_dir, "prepared_messages_binding_report_ref", report)

    with pytest.raises(ConfigError, match="run_id 必须唯一|数量必须等于"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_prepared_messages_sha_mismatch(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "prepared_messages_binding_report.json"
    payload = _read_json(report)
    payload["binding_records"][0]["prepared_messages_sha256"] = "0" * 64
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="prepared_messages_sha256"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_missing_stage2_stage3_stage4_external_ref(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    report = run_dir / "v4_agent_run_integration_report.json"
    payload = _read_json(report)
    payload["external_refs"].pop("task_freeze_manifest_ref")
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="task_freeze_manifest_ref"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_generated_task_definition_schema_drift(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    external = _external_ref_path(run_dir, "generated_task_definition_ref")
    records = _read_jsonl(external)
    records[0]["schema_version"] = "wrong"
    _write_jsonl(external, records)
    _refresh_external_ref(run_dir, "generated_task_definition_ref", external)

    with pytest.raises(ConfigError, match="generated_task_definition_ref"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_permission_trace_schema_drift(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    external = _external_ref_path(run_dir, "permission_decision_trace_ref")
    records = _read_jsonl(external)
    records[0]["schema_version"] = "wrong"
    _write_jsonl(external, records)
    _refresh_external_ref(run_dir, "permission_decision_trace_ref", external)

    with pytest.raises(ConfigError, match="permission_decision_trace_ref"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_tool_lifecycle_schema_hash_drift(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    external = _external_ref_path(run_dir, "tool_lifecycle_trace_ref")
    records = _read_jsonl(external)
    records[0]["tool_schema_hash"] = "0" * 64
    _write_jsonl(external, records)
    _refresh_external_ref(run_dir, "tool_lifecycle_trace_ref", external)

    with pytest.raises(ConfigError, match="tool_schema_hash"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


@pytest.mark.parametrize(
    "report_name",
    [
        "runspec_metadata_report.json",
        "final_verifier_boundary_report.json",
        "prepared_messages_binding_report.json",
    ],
)
def test_v4_agent_run_rejects_missing_required_report(tmp_path: Path, report_name: str) -> None:
    run_dir = _build(tmp_path)
    (run_dir / report_name).unlink()

    with pytest.raises(ConfigError, match=report_name):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_rejects_missing_interrupted_or_crash_facts(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)
    (run_dir / "runs" / "v4-run-interrupted-001" / "interrupted_run_facts.json").unlink()

    with pytest.raises(ConfigError, match="interrupted_or_crash_facts_ref|路径不存在"):
        inspect_v4_agent_run_integration(run_dir, assert_complete=True)


def test_v4_agent_run_build_respects_fail_if_output_exists(tmp_path: Path) -> None:
    run_dir = _build(tmp_path)

    with pytest.raises(ConfigError, match="输出已存在"):
        build_v4_agent_run_integration(output_dir=run_dir, fail_if_output_exists=True, **_external_inputs(tmp_path))


def _build(tmp_path: Path) -> Path:
    return build_v4_agent_run_integration(output_dir=tmp_path / "agent", **_external_inputs(tmp_path)).parent


def _external_inputs(tmp_path: Path) -> dict:
    external = tmp_path / "external"
    task_dir = external / "task"
    rollout_dir = external / "rollout"
    tool_dir = external / "tool"
    task_dir.mkdir(parents=True, exist_ok=True)
    rollout_dir.mkdir(parents=True, exist_ok=True)
    tool_dir.mkdir(parents=True, exist_ok=True)
    _write_json(task_dir / "task_freeze_manifest.json", {"schema_version": V4_TASK_FREEZE_MANIFEST_VERSION})
    _write_jsonl(
        task_dir / "generated_task_definition.jsonl",
        [
            {
                "schema_version": "repo_harness_v4_stage2_generated_task_definition_record_v0",
                "task_id": "v4_go_cobra_completion_args",
                "model_visible": True,
                "task_visibility_policy_id": "repo_harness_v4_visibility_policy_v0",
            }
        ],
    )
    _write_json(task_dir / "environment_stability_report.json", {"records": [{"docker_probe_status": "passed"}]})
    _write_json(rollout_dir / "rollout_queue_manifest.json", {"schema_version": V4_ROLLOUT_QUEUE_MANIFEST_VERSION})
    tool_schema_hash = "a" * 64
    _write_json(
        tool_dir / "tool_contract_v4_snapshot.json",
        {
            "schema_version": V4_TOOL_CONTRACT_SNAPSHOT_VERSION,
            "tool_schema_hash": tool_schema_hash,
        },
    )
    _write_jsonl(
        tool_dir / "permission_decision_trace.jsonl",
        [
            {
                "schema_version": "repo_harness_v4_permission_decision_trace_entry_v0",
                "event_id": "permission-allow-read-file",
                "decision": "allow",
                "executed_as_tool_call": True,
            }
        ],
    )
    _write_jsonl(
        tool_dir / "tool_lifecycle_trace.jsonl",
        [
            {
                "schema_version": V4_TOOL_LIFECYCLE_TRACE_ENTRY_VERSION,
                "tool_call_id": "tool-call-001",
                "tool_schema_hash": tool_schema_hash,
            }
        ],
    )
    return {
        "task_freeze": task_dir / "task_freeze_manifest.json",
        "rollout_queue": rollout_dir / "rollout_queue_manifest.json",
        "tool_lifecycle": tool_dir,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _external_ref_path(run_dir: Path, ref_name: str) -> Path:
    payload = _read_json(run_dir / "v4_agent_run_integration_report.json")
    return Path(payload["external_refs"][ref_name]["path"])


def _refresh_external_ref(run_dir: Path, ref_name: str, path: Path) -> None:
    payload = _read_json(run_dir / "v4_agent_run_integration_report.json")
    payload["external_refs"][ref_name]["sha256"] = _sha256_file(path)
    payload["external_refs"][ref_name]["size_bytes"] = path.stat().st_size
    _write_json(run_dir / "v4_agent_run_integration_report.json", payload)


def _refresh_integration_report_ref(run_dir: Path, report_ref_name: str, path: Path) -> None:
    payload = _read_json(run_dir / "v4_agent_run_integration_report.json")
    payload["reports"][report_ref_name]["sha256"] = _sha256_file(path)
    payload["reports"][report_ref_name]["size_bytes"] = path.stat().st_size
    _write_json(run_dir / "v4_agent_run_integration_report.json", payload)


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
