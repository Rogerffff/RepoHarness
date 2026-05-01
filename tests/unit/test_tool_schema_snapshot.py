from __future__ import annotations

import json
from pathlib import Path

from repo_harness.run_metadata.tool_snapshot import build_tool_schema_snapshot, write_tool_schema_snapshot
from repo_harness.tools import DEFAULT_TOOL_ORDER
from repo_harness.trajectory import RunRecorder


def test_tool_schema_snapshot_records_stable_tool_order():
    snapshot = build_tool_schema_snapshot()

    assert snapshot.tool_order == DEFAULT_TOOL_ORDER
    assert [tool.name for tool in snapshot.tools] == DEFAULT_TOOL_ORDER
    assert snapshot.snapshot_sha256
    assert snapshot.tool_parser_version == "repo_harness_tool_call_parser_v0"
    assert snapshot.tool_result_format_version == "repo_harness_tool_result_v0"
    read_file = next(tool for tool in snapshot.tools if tool.name == "read_file")
    assert read_file.read_only is True
    assert read_file.permission_required is True


def test_tool_schema_snapshot_is_manifest_backed_artifact(tmp_path: Path):
    run_dir = tmp_path / "run"
    with RunRecorder("run_001", run_dir, task_id="task_001") as recorder:
        snapshot, ref, protocol = write_tool_schema_snapshot(recorder)

    manifest = json.loads((run_dir / "artifacts.json").read_text(encoding="utf-8"))
    manifest_refs = {artifact["artifact_id"]: artifact for artifact in manifest["artifacts"]}
    payload = json.loads((run_dir / ref.relative_path).read_text(encoding="utf-8"))

    assert ref.artifact_id in manifest_refs
    assert manifest_refs[ref.artifact_id]["kind"] == "tool_schema_snapshot"
    assert payload["snapshot_sha256"] == snapshot.snapshot_sha256
    assert protocol.tool_schema_snapshot_ref == ref
    assert protocol.tool_order == DEFAULT_TOOL_ORDER
