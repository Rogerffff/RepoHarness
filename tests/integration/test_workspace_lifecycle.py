from pathlib import Path

from repo_harness.tasks import load_task
from repo_harness.trajectory import RunRecorder, verify_artifact_manifest
from repo_harness.workspace import LocalWorkspaceAdapter


def test_workspace_lifecycle_captures_patch_and_replays_it(tmp_path: Path):
    loaded = load_task("tests/fixtures/tasks/task_001.yaml")
    run_dir = tmp_path / "run_001"
    with RunRecorder("run_001", run_dir, task_id=loaded.runnable_task.task_id) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_001", run_dir=run_dir)
        source = adapter.create_source_checkout(loaded.runnable_task)
        setup = adapter.create_setup_workspace(source)
        command_result = adapter.run_command(
            setup,
            "python -c \"print('setup ok')\"",
            recorder=recorder,
            command_semantics="setup",
        )
        dependency_state = adapter.capture_dependency_state(strategy="none")
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            recorder=recorder,
        )
        original = adapter.read_text(run_workspace.workspace_path, "calculator.py")
        adapter.write_text(
            run_workspace.workspace_path,
            "calculator.py",
            original.replace(
                "def divide(left: int, right: int) -> float:\n    return left / right\n",
                "def divide(left: int, right: int) -> float:\n"
                "    if right == 0:\n"
                "        raise ValueError(\"division by zero\")\n"
                "    return left / right\n",
            ),
        )

        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        verification = adapter.create_verification_workspace(
            source_checkout=source,
            dependency_state=dependency_state,
            final_patch_path=capture.patch_path,
            recorder=recorder,
        )

    assert command_result.exit_code == 0
    assert command_result.output_artifact_ref is not None
    assert verify_artifact_manifest(run_dir) == []
    assert (run_dir / "final.patch").exists()
    assert (run_dir / "final.diff").exists()
    assert capture.patch_artifact_ref.relative_path.startswith("artifacts/")
    assert capture.diff_artifact_ref.relative_path.startswith("artifacts/")
    assert "ValueError" in capture.patch_text
    assert capture.added_lines >= 2
    assert "ValueError" in (verification / "calculator.py").read_text(encoding="utf-8")


def test_workspace_command_timeout_is_reported(tmp_path: Path):
    run_dir = tmp_path / "run"
    with RunRecorder("run_timeout", run_dir) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_timeout", run_dir=run_dir)
        workspace = adapter.workspaces_dir / "workspace"
        workspace.mkdir(parents=True)

        result = adapter.run_command(
            workspace,
            "python -c \"import time; time.sleep(2)\"",
            timeout_sec=0.1,
            recorder=recorder,
        )

    assert result.timeout is True
    assert result.exit_code != 0
    assert result.output_artifact_ref is not None


def test_workspace_patch_replay_includes_new_and_deleted_text_files(tmp_path: Path):
    loaded = load_task("tests/fixtures/tasks/task_001.yaml")
    run_dir = tmp_path / "run_patch"
    with RunRecorder("run_patch", run_dir, task_id=loaded.runnable_task.task_id) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_patch", run_dir=run_dir)
        source = adapter.create_source_checkout(loaded.runnable_task)
        dependency_state = adapter.capture_dependency_state(strategy="none")
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            recorder=recorder,
        )
        adapter.write_text(run_workspace.workspace_path, "notes/new_file.txt", "new content\n")
        (Path(run_workspace.workspace_path) / "pyproject.toml").unlink()

        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        verification = adapter.create_verification_workspace(
            source_checkout=source,
            dependency_state=dependency_state,
            final_patch_path=capture.patch_path,
            recorder=recorder,
        )

    assert "new_file.txt" in capture.patch_text
    assert "deleted file mode" in capture.patch_text
    assert (verification / "notes" / "new_file.txt").read_text(encoding="utf-8") == "new content\n"
    assert not (verification / "pyproject.toml").exists()


def test_workspace_final_patch_uses_agent_start_snapshot_when_head_moves(tmp_path: Path):
    loaded = load_task("tests/fixtures/tasks/task_001.yaml")
    run_dir = tmp_path / "run_head_moves"
    with RunRecorder("run_head_moves", run_dir, task_id=loaded.runnable_task.task_id) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_head_moves", run_dir=run_dir)
        source = adapter.create_source_checkout(loaded.runnable_task)
        dependency_state = adapter.capture_dependency_state(strategy="none")
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            recorder=recorder,
        )
        original = adapter.read_text(run_workspace.workspace_path, "calculator.py")
        adapter.write_text(
            run_workspace.workspace_path,
            "calculator.py",
            original + "\nANSWER = 42\n",
        )
        adapter.run_command(
            run_workspace.workspace_path,
            "git add calculator.py && git commit -m agent-moved-head",
            recorder=recorder,
            command_semantics="diagnostic_git",
        )

        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)

    assert "ANSWER = 42" in capture.patch_text


def test_workspace_command_rejects_cwd_outside_run_dir(tmp_path: Path):
    run_dir = tmp_path / "run"
    outside = tmp_path / "outside"
    outside.mkdir()
    with RunRecorder("run_cwd", run_dir) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_cwd", run_dir=run_dir)
        try:
            adapter.run_command(outside, "pwd", recorder=recorder)
        except Exception as exc:
            assert "workspaces" in str(exc)
        else:
            raise AssertionError("run_command should reject cwd outside run directory")


def test_workspace_rerun_setup_restores_dependency_state_for_agent_and_verification(
    tmp_path: Path,
):
    loaded = load_task("tests/fixtures/tasks/task_001.yaml")
    run_dir = tmp_path / "run_rerun_setup"
    setup_command = "python -c \"from pathlib import Path; Path('setup_marker.txt').write_text('ok')\""
    with RunRecorder("run_rerun_setup", run_dir, task_id=loaded.runnable_task.task_id) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_rerun_setup", run_dir=run_dir)
        source = adapter.create_source_checkout(loaded.runnable_task)
        dependency_state = adapter.capture_dependency_state(strategy="rerun_setup")
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            setup_command=setup_command,
            recorder=recorder,
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        verification = adapter.create_verification_workspace(
            source_checkout=source,
            dependency_state=dependency_state,
            final_patch_path=capture.patch_path,
            setup_command=setup_command,
            recorder=recorder,
        )

    assert (Path(run_workspace.workspace_path) / "setup_marker.txt").read_text() == "ok"
    assert (verification / "setup_marker.txt").read_text() == "ok"
