import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.trajectory import (
    ArtifactRef,
    RunRecorder,
    RunRecorderError,
    TrajectoryEvent,
    TranscriptRecord,
    inspect_run,
    read_jsonl,
    verify_artifact_manifest,
)


def test_run_recorder_writes_jsonl_and_artifact_manifest(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    with RunRecorder("run_001", run_dir, task_id="task_001") as recorder:
        event_id = recorder.next_event_id()
        artifact = recorder.write_artifact(
            "tool_stdout",
            "hello artifact",
            {"created_by_event_id": event_id, "redaction_status": "not_needed"},
        )
        event = TrajectoryEvent(
            event_id=event_id,
            timestamp="2026-04-30T00:00:00Z",
            run_id="run_001",
            task_id="task_001",
            event_type="artifact_written",
            artifact_refs=[artifact],
        )
        recorder.append_event(event)
        record = TranscriptRecord(
            record_id=recorder.next_record_id(),
            run_id="run_001",
            task_id="task_001",
            message_id="msg_001",
            turn=1,
            role="tool",
            tool_call_id="call_001",
            tool_result_id="result_001",
            content_preview="hello",
            content_artifact_refs=[artifact],
            model_visible=True,
            trainable=False,
            created_at="2026-04-30T00:00:00Z",
        )
        recorder.append_transcript(record)
        recorder.write_json_artifact("verifier_result", {"accepted": True})
        recorder.finalize_run("# Summary\n\n完成。")

    events = read_jsonl(run_dir / "events.jsonl")
    transcript = read_jsonl(run_dir / "transcript.jsonl")
    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))

    assert events[0]["event_id"] == event_id
    assert transcript[0]["tool_result_id"] == "result_001"
    for jsonl_path in [run_dir / "events.jsonl", run_dir / "transcript.jsonl"]:
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            assert isinstance(json.loads(line), dict)
    assert len(manifest["artifacts"]) == 2
    assert verify_artifact_manifest(run_dir) == []
    assert (run_dir / manifest["artifacts"][0]["relative_path"]).read_text(encoding="utf-8") == (
        "hello artifact"
    )


def test_run_recorder_rejects_second_writer_for_same_run_dir(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    recorder = RunRecorder("run_001", run_dir)
    try:
        with pytest.raises(RunRecorderError, match="锁定"):
            RunRecorder("run_001", run_dir)
    finally:
        recorder.close()


def test_inspect_run_reports_running_finalized_and_interrupted(tmp_path: Path):
    running_dir = tmp_path / "running"
    running = RunRecorder("running", running_dir)
    try:
        assert "Status: RUNNING" in inspect_run(running_dir)
    finally:
        running.close()

    finalized_dir = tmp_path / "finalized"
    with RunRecorder("finalized", finalized_dir) as finalized:
        finalized.finalize_run("# Summary\n")
        finalized.finalize_run("# Summary\n")
        with pytest.raises(RunRecorderError, match="不能改写"):
            finalized.finalize_run("# Summary again\n")
    finalized_text = inspect_run(finalized_dir)
    assert "Status: FINALIZED" in finalized_text
    assert "Summary: present" in finalized_text
    with pytest.raises(RunRecorderError, match="FINALIZED"):
        RunRecorder("finalized", finalized_dir)

    interrupted_dir = tmp_path / "interrupted"
    with RunRecorder("interrupted", interrupted_dir) as interrupted:
        interrupted.mark_interrupted("# Interrupted\n")
    assert "Status: INTERRUPTED" in inspect_run(interrupted_dir)


def test_cli_inspect_run_reads_partial_run_directory(tmp_path: Path, capsys):
    run_dir = tmp_path / "partial"
    recorder = RunRecorder("partial", run_dir)
    try:
        exit_code = main(["inspect-run", str(run_dir)])
    finally:
        recorder.close()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Status: RUNNING" in captured.out
    assert "Metrics: missing" in captured.out
    assert "Summary: missing" in captured.out


def test_manifest_verification_detects_tampered_artifact(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    with RunRecorder("run_001", run_dir) as recorder:
        artifact = recorder.write_artifact("large_stdout", "original")

    artifact_path = run_dir / artifact.relative_path
    artifact_path.write_text("tampered", encoding="utf-8")

    errors = verify_artifact_manifest(run_dir)
    assert errors
    assert "sha256 mismatch" in errors[0] or "size mismatch" in errors[0]
    assert "Artifacts manifest: invalid" in inspect_run(run_dir)


def test_artifacts_without_explicit_event_id_get_creation_event(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    with RunRecorder("run_001", run_dir, task_id="task_001") as recorder:
        artifact = recorder.write_json_artifact("verifier_result", {"accepted": True})

    events = read_jsonl(run_dir / "events.jsonl")
    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    manifest_ref = manifest["artifacts"][0]

    assert artifact.created_by_event_id is not None
    assert manifest_ref["created_by_event_id"] == artifact.created_by_event_id
    assert any(
        event["event_id"] == artifact.created_by_event_id
        and event["event_type"] == "artifact_created"
        and event["artifact_refs"][0]["artifact_id"] == artifact.artifact_id
        for event in events
    )


def test_manifest_verification_rejects_unsafe_relative_path(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    with RunRecorder("run_001", run_dir) as recorder:
        recorder.write_artifact("stdout", "safe")

    manifest_path = run_dir / "artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["relative_path"] = "../outside.txt"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    errors = verify_artifact_manifest(run_dir)

    assert errors
    assert "unsafe relative_path" in errors[0]


def test_inspect_run_reports_corrupt_partial_jsonl_and_manifest(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text('{"ok": true}\n{broken\n', encoding="utf-8")
    (run_dir / "artifacts.json").write_text("{broken\n", encoding="utf-8")
    (run_dir / "run_status.json").write_text('{"status": "RUNNING"}\n', encoding="utf-8")

    output = inspect_run(run_dir)

    assert "Status: CORRUPT_PARTIAL" in output
    assert "events.jsonl is corrupt" in output
    assert "artifacts.json is corrupt" in output


def test_artifact_ref_schema_can_validate_manifest_entry(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    with RunRecorder("run_001", run_dir) as recorder:
        recorder.write_artifact("stdout", b"bytes")

    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    ref = ArtifactRef.model_validate(manifest["artifacts"][0])

    assert ref.relative_path.startswith("artifacts/")
    assert not Path(ref.relative_path).is_absolute()


def test_run_recorder_truncates_artifacts_over_configured_budget(tmp_path: Path):
    run_dir = tmp_path / "run_budget"
    with RunRecorder("run_budget", run_dir, task_id="task_001", max_artifact_bytes=20) as recorder:
        artifact = recorder.write_artifact("command_output", "x" * 100)

    events = read_jsonl(run_dir / "events.jsonl")
    stored = (run_dir / artifact.relative_path).read_bytes()

    assert artifact.size_bytes <= 20
    assert len(stored) <= 20
    assert verify_artifact_manifest(run_dir) == []
    assert any(
        event["event_type"] == "artifact_budget_exhausted"
        and event["data"]["artifact_id"] == artifact.artifact_id
        and event["data"]["original_size_bytes"] == 100
        for event in events
    )


def test_run_recorder_preserves_json_artifacts_over_text_budget(tmp_path: Path):
    run_dir = tmp_path / "run_json_budget"
    payload = {"messages": [{"role": "system", "content": "x" * 200}]}
    with RunRecorder("run_json_budget", run_dir, task_id="task_001", max_artifact_bytes=20) as recorder:
        artifact = recorder.write_json_artifact("prepared_messages", payload)

    stored = json.loads((run_dir / artifact.relative_path).read_text(encoding="utf-8"))
    events = read_jsonl(run_dir / "events.jsonl")

    assert stored == payload
    assert artifact.size_bytes > 20
    assert verify_artifact_manifest(run_dir) == []
    assert not any(event["event_type"] == "artifact_budget_exhausted" for event in events)
