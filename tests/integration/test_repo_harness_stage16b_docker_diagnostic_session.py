from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path

import pytest

from repo_harness.config import DockerRuntimeConfig
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace.docker_adapter import DockerWorkspaceAdapter, _diagnostic_workspace_digest


def test_stage16b_docker_diagnostic_session_persists_without_run_dir_mount(tmp_path: Path) -> None:
    platform = _docker_platform_or_skip()
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    (workspace / ".git").mkdir()
    (workspace / ".git" / "HEAD").write_text("hidden-history\n", encoding="utf-8")
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")

    adapter = DockerWorkspaceAdapter(
        run_id="stage16b-docker-diagnostic",
        run_dir=run_dir,
        docker_config=DockerRuntimeConfig(
            image_ref="repo-harness-v3-python:stage2",
            build_if_missing=True,
            requested_container_platform=platform,
            network_policy="deny_agent_run",
            mount_policy="workspace_read_write_tmp_only",
            cleanup_policy="remove_containers_keep_images",
        ),
        default_command_timeout_sec=90,
    )
    with RunRecorder("stage16b-docker-diagnostic", run_dir, task_id="task") as recorder:
        first = adapter.run_diagnostic_shell(
            workspace,
            "printf 'value = 2\\n' > pkg.py; mkdir -p \"$HOME\"; printf keep > \"$HOME/persist\"; "
            "ls /; ls -a /workspace",
            recorder=recorder,
            session_id="docker-session",
            timeout_sec=30,
        )
        second = adapter.run_diagnostic_shell(
            workspace,
            "test -f \"$HOME/persist\"; echo home_persist=$?",
            recorder=recorder,
            session_id="docker-session",
            timeout_sec=30,
        )
        labels = _diagnostic_container_labels(adapter)
    adapter.cleanup_workspaces()

    assert first.exit_code == 0
    assert "repo-harness-run" not in first.stdout_preview
    assert ".git" not in first.stdout_preview
    assert second.exit_code == 0
    assert "home_persist=0" in second.stdout_preview
    assert (workspace / "pkg.py").read_text(encoding="utf-8") == "value = 2\n"
    assert first.diagnostic_session_facts is not None
    assert first.diagnostic_session_facts["run_dir_mount_enabled"] is False
    assert first.diagnostic_session_facts["workspace_projection_sync_status"] == "completed"
    assert labels["repo-harness.session_kind"] == "diagnostic_shell"
    assert labels["repo-harness.run_id"] == "stage16b-docker-diagnostic"
    assert labels["repo-harness.session_id"] == "docker-session"
    assert labels["repo-harness.task_id"] == "unknown"
    assert len(labels["repo-harness.workspace_digest"]) == 64


def test_stage16b_docker_diagnostic_session_detects_background_process(tmp_path: Path) -> None:
    platform = _docker_platform_or_skip()
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")

    adapter = DockerWorkspaceAdapter(
        run_id="stage16b-docker-background",
        run_dir=run_dir,
        docker_config=DockerRuntimeConfig(
            image_ref="repo-harness-v3-python:stage2",
            build_if_missing=True,
            requested_container_platform=platform,
            network_policy="deny_agent_run",
            mount_policy="workspace_read_write_tmp_only",
            cleanup_policy="remove_containers_keep_images",
        ),
        default_command_timeout_sec=90,
    )
    with RunRecorder("stage16b-docker-background", run_dir, task_id="task") as recorder:
        result = adapter.run_diagnostic_shell(
            workspace,
            "sh -c 'sleep infinity &'",
            recorder=recorder,
            session_id="docker-background-session",
            timeout_sec=30,
        )
    adapter.cleanup_workspaces()

    assert result.exit_code == 0
    assert result.diagnostic_session_facts is not None
    assert result.diagnostic_session_facts["background_process_cleanup_status"] == "failed"


def test_stage16b_docker_diagnostic_session_detects_background_process_with_probe_text(
    tmp_path: Path,
) -> None:
    platform = _docker_platform_or_skip()
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")

    adapter = DockerWorkspaceAdapter(
        run_id="stage16b-docker-background-probe-text",
        run_dir=run_dir,
        docker_config=DockerRuntimeConfig(
            image_ref="repo-harness-v3-python:stage2",
            build_if_missing=True,
            requested_container_platform=platform,
            network_policy="deny_agent_run",
            mount_policy="workspace_read_write_tmp_only",
            cleanup_policy="remove_containers_keep_images",
        ),
        default_command_timeout_sec=90,
    )
    try:
        with RunRecorder("stage16b-docker-background-probe-text", run_dir, task_id="task") as recorder:
            result = adapter.run_diagnostic_shell(
                workspace,
                "sh -c 'python -c \"import time; time.sleep(60) # for p in /proc/[0-9]*\" &'",
                recorder=recorder,
                session_id="docker-background-probe-text-session",
                timeout_sec=30,
            )

        assert result.exit_code == 0
        assert result.diagnostic_session_facts is not None
        assert result.diagnostic_session_facts["background_process_cleanup_status"] == "failed"
    finally:
        adapter.cleanup_workspaces()


def test_stage16b_docker_diagnostic_session_timeout_cleans_sanitized_session_id(tmp_path: Path) -> None:
    platform = _docker_platform_or_skip()
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")

    adapter = DockerWorkspaceAdapter(
        run_id="stage16b-docker-timeout",
        run_dir=run_dir,
        docker_config=DockerRuntimeConfig(
            image_ref="repo-harness-v3-python:stage2",
            build_if_missing=True,
            requested_container_platform=platform,
            network_policy="deny_agent_run",
            mount_policy="workspace_read_write_tmp_only",
            cleanup_policy="remove_containers_keep_images",
        ),
        default_command_timeout_sec=90,
    )
    try:
        with RunRecorder("stage16b-docker-timeout", run_dir, task_id="task") as recorder:
            result = adapter.run_diagnostic_shell(
                workspace,
                "sleep 5",
                recorder=recorder,
                session_id="docker/session:timeout",
                timeout_sec=0.2,
            )

        assert result.timeout is True
        assert result.diagnostic_session_facts is not None
        assert result.diagnostic_session_facts["session_invalidated"] is True
        assert adapter._diagnostic_containers == {}
    finally:
        adapter.cleanup_workspaces()


def test_stage16b_docker_diagnostic_session_cleans_matching_orphan_container(tmp_path: Path) -> None:
    platform = _docker_platform_or_skip()
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    (workspace / "pkg.py").write_text("value = 1\n", encoding="utf-8")
    run_id = "stage16b-docker-orphan"
    session_id = "docker-orphan-session"
    orphan_name = f"stage16b-orphan-{abs(hash(tmp_path))}"

    adapter = DockerWorkspaceAdapter(
        run_id=run_id,
        run_dir=run_dir,
        docker_config=DockerRuntimeConfig(
            image_ref="repo-harness-v3-python:stage2",
            build_if_missing=True,
            requested_container_platform=platform,
            network_policy="deny_agent_run",
            mount_policy="workspace_read_write_tmp_only",
            cleanup_policy="remove_containers_keep_images",
        ),
        default_command_timeout_sec=90,
    )
    subprocess.run(["docker", "rm", "-f", orphan_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            orphan_name,
            "--platform",
            platform,
            "--label",
            "repo-harness.session_kind=diagnostic_shell",
            "--label",
            f"repo-harness.run_id={run_id}",
            "--label",
            "repo-harness.task_id=unknown",
            "--label",
            f"repo-harness.session_id={session_id}",
            "--label",
            f"repo-harness.workspace_digest={_diagnostic_workspace_digest(workspace)}",
            "--label",
            f"repo-harness.workspace_path_hash={_workspace_path_hash(workspace)}",
            "repo-harness-v3-python:stage2",
            "sh",
            "-lc",
            "sleep infinity",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
        timeout=30,
    )
    try:
        with RunRecorder("stage16b-docker-orphan", run_dir, task_id="task") as recorder:
            result = adapter.run_diagnostic_shell(
                workspace,
                "echo ok",
                recorder=recorder,
                session_id=session_id,
                timeout_sec=30,
            )
        orphan_inspect = subprocess.run(
            ["docker", "inspect", orphan_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=15,
        )

        assert result.exit_code == 0
        assert orphan_inspect.returncode != 0
    finally:
        subprocess.run(["docker", "rm", "-f", orphan_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        adapter.cleanup_workspaces()


def _docker_platform_or_skip() -> str:
    try:
        subprocess.run(
            ["docker", "version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        architecture = subprocess.run(
            ["docker", "info", "--format", "{{.Architecture}}"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"Docker is unavailable for Stage 16B diagnostic session smoke: {exc}")
    if architecture in {"aarch64", "arm64"}:
        return "linux/arm64"
    return "linux/amd64"


def _diagnostic_container_labels(adapter: DockerWorkspaceAdapter) -> dict[str, str]:
    container_name = next(iter(adapter._diagnostic_containers.values()))
    inspected = subprocess.run(
        ["docker", "inspect", "-f", "{{json .Config.Labels}}", container_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
        timeout=15,
    )
    return json.loads(inspected.stdout)


def _workspace_path_hash(workspace: Path) -> str:
    return hashlib.sha256(workspace.resolve().as_posix().encode("utf-8")).hexdigest()
