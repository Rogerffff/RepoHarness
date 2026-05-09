from __future__ import annotations

import subprocess
from types import SimpleNamespace

from repo_harness.workspace.docker_adapter import DockerWorkspaceAdapter


def test_docker_image_exists_rejects_matching_name_with_wrong_platform(monkeypatch) -> None:
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.environment = SimpleNamespace(docker_path="docker")
    adapter.image_ref = "repo-harness-pre-verl-python-3-9:v0"
    adapter.requested_container_platform = "linux/amd64"

    def fake_run(command, **kwargs):  # noqa: ANN001
        assert command == [
            "docker",
            "image",
            "inspect",
            "repo-harness-pre-verl-python-3-9:v0",
            "--format",
            "{{.Os}}/{{.Architecture}}",
        ]
        assert kwargs["stdout"] == subprocess.PIPE
        return subprocess.CompletedProcess(command, 0, stdout="linux/arm64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert adapter._image_exists() is False


def test_docker_image_exists_accepts_matching_name_and_platform(monkeypatch) -> None:
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.environment = SimpleNamespace(docker_path="docker")
    adapter.image_ref = "repo-harness-pre-verl-python-3-9:v0"
    adapter.requested_container_platform = "linux/amd64"

    def fake_run(command, **kwargs):  # noqa: ANN001, ARG001
        return subprocess.CompletedProcess(command, 0, stdout="linux/amd64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert adapter._image_exists() is True
