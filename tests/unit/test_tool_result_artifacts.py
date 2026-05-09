from __future__ import annotations

import pytest

from repo_harness.context.tool_result_artifacts import (
    ToolResultArtifactError,
    ToolResultArtifactIndex,
    build_persisted_tool_result_preview,
    persist_tool_result_content,
    read_tool_result_artifact,
)
from repo_harness.trajectory import RunRecorder


def test_tool_result_artifact_preview_and_paged_recovery(tmp_path):
    content = "0123456789" * 1200
    with RunRecorder("tool-artifacts", tmp_path / "run", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_read_result",
            tool_call_id="call_read",
            tool_name="read_file",
            content=content,
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
    index.add(record)
    preview = build_persisted_tool_result_preview(record, content, preview_chars=50)

    assert record.artifact_id in preview
    assert record.content_sha256 in preview
    assert "read_tool_result_artifact" in preview
    assert "Preview (first 50 chars)" in preview

    with pytest.raises(ToolResultArtifactError, match="not unlocked"):
        read_tool_result_artifact(index, artifact_id=record.artifact_id)

    index.unlock_after_provider_commit(record.artifact_id)
    first = read_tool_result_artifact(index, artifact_id=record.artifact_id, offset=0, limit=8000)
    second = read_tool_result_artifact(
        index,
        artifact_id=record.artifact_id,
        offset=first["next_offset"],
        limit=8000,
    )

    assert first["content"] == content[:8000]
    assert first["next_offset"] == 8000
    assert second["content"] == content[8000:]
    assert second["next_offset"] is None
    assert first["content_sha256"] == record.content_sha256


def test_tool_result_artifact_rejects_unsafe_or_unknown_ids(tmp_path):
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")

    for artifact_id in ("../secret", "/absolute", "nested/path", ""):
        with pytest.raises(ToolResultArtifactError):
            read_tool_result_artifact(index, artifact_id=artifact_id)

    with pytest.raises(ToolResultArtifactError, match="not registered"):
        read_tool_result_artifact(index, artifact_id="unknown_artifact")


def test_tool_result_artifact_rejects_non_current_run_artifact(tmp_path):
    with RunRecorder("other-run", tmp_path / "other", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_result",
            tool_call_id="call",
            tool_name="grep",
            content="other run content",
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "current")
    index.add(record)
    index.unlock_after_provider_commit(record.artifact_id)

    with pytest.raises(ToolResultArtifactError, match="missing"):
        read_tool_result_artifact(index, artifact_id=record.artifact_id)


def test_unpublishable_tool_result_artifact_preview_does_not_expose_capability(tmp_path):
    with RunRecorder("tool-artifacts-redacted", tmp_path / "run", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_hidden_result",
            tool_call_id="call_hidden",
            tool_name="read_file",
            content="hidden content",
            publishable_after_visibility_scan=False,
            contamination_scan_status="failed",
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
    index.add(record)
    preview = build_persisted_tool_result_preview(record, "hidden content")

    assert record.artifact_id not in preview
    assert record.content_sha256 not in preview
    assert "read_tool_result_artifact" not in preview
    with pytest.raises(ToolResultArtifactError, match="not unlocked"):
        read_tool_result_artifact(index, artifact_id=record.artifact_id)


def test_candidate_preview_artifact_does_not_unlock_recovery(tmp_path):
    with RunRecorder("tool-artifacts-candidate", tmp_path / "run", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_result",
            tool_call_id="call",
            tool_name="bash",
            content="candidate only",
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
    index.add(record)

    with pytest.raises(ToolResultArtifactError, match="not unlocked"):
        read_tool_result_artifact(index, artifact_id=record.artifact_id)


def test_rejected_provider_request_artifact_remains_locked(tmp_path):
    with RunRecorder("tool-artifacts-context-limit", tmp_path / "run", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_result",
            tool_call_id="call",
            tool_name="run_tests",
            content="provider rejected before model consumed preview",
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
    index.add(record)

    with pytest.raises(ToolResultArtifactError, match="not unlocked"):
        read_tool_result_artifact(index, artifact_id=record.artifact_id)


def test_default_persisted_tool_result_is_not_publishable_without_scan(tmp_path):
    with RunRecorder("tool-artifacts-default-scan", tmp_path / "run", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_result",
            tool_call_id="call",
            tool_name="grep",
            content="not scanned",
        )

    assert record.publishable_after_visibility_scan is False
    assert record.contamination_scan_status == "not_scanned"
    preview = build_persisted_tool_result_preview(record, "not scanned")
    assert record.artifact_id not in preview
    assert "read_tool_result_artifact" not in preview


def test_tool_result_artifact_is_preserved_with_recorder_artifact_budget(tmp_path):
    content = "x" * 200
    with RunRecorder(
        "tool-artifacts-budget",
        tmp_path / "run",
        task_id="task",
        max_artifact_bytes=20,
    ) as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_result",
            tool_call_id="call",
            tool_name="grep",
            content=content,
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
    index.add(record)
    index.unlock_after_provider_commit(record.artifact_id)

    recovered = read_tool_result_artifact(index, artifact_id=record.artifact_id, limit=500)

    assert recovered["content"] == content
    assert recovered["next_offset"] is None


def test_tool_result_artifact_hash_mismatch_is_rejected(tmp_path):
    with RunRecorder("tool-artifacts-tamper", tmp_path / "run", task_id="task") as recorder:
        record = persist_tool_result_content(
            recorder=recorder,
            tool_result_id="call_result",
            tool_call_id="call",
            tool_name="grep",
            content="original",
            publishable_after_visibility_scan=True,
            contamination_scan_status="clean",
        )
    path = tmp_path / "run" / record.artifact_ref.relative_path
    path.write_text("tampered", encoding="utf-8")
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")
    index.add(record)
    index.unlock_after_provider_commit(record.artifact_id)

    with pytest.raises(ToolResultArtifactError, match="does not match"):
        read_tool_result_artifact(index, artifact_id=record.artifact_id)


def test_plain_manifest_artifact_id_is_not_recoverable_without_index_record(tmp_path):
    with RunRecorder("tool-artifacts-manifest-only", tmp_path / "run", task_id="task") as recorder:
        ref = recorder.write_artifact(
            "tool_result_original_content",
            "manifest only",
            {"budget_policy": "preserve_json"},
        )
    index = ToolResultArtifactIndex(run_dir=tmp_path / "run")

    with pytest.raises(ToolResultArtifactError, match="not registered"):
        read_tool_result_artifact(index, artifact_id=ref.artifact_id)
