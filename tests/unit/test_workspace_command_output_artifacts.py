from __future__ import annotations

from pathlib import Path

from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import LocalWorkspaceAdapter


def test_local_workspace_command_records_split_output_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)

    with RunRecorder("run_output_refs", run_dir) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_output_refs", run_dir=run_dir)
        result = adapter.run_command(
            workspace,
            "python -c \"import sys; print('out'); print('err', file=sys.stderr)\"",
            recorder=recorder,
            command_semantics="unit_test_command",
        )

    assert result.exit_code == 0
    assert result.output_artifact_ref is not None
    assert result.stdout_ref is not None
    assert result.stderr_ref is not None
    assert result.stdout_preview == "out\n"
    assert result.stderr_preview == "err\n"
    assert "out" in (run_dir / result.stdout_ref.relative_path).read_text(encoding="utf-8")
    assert "err" in (run_dir / result.stderr_ref.relative_path).read_text(encoding="utf-8")
