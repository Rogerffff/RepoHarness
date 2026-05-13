from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace
from pathlib import Path

from repo_harness.config import DockerRuntimeConfig
import repo_harness.workspace.docker_adapter as docker_adapter_module
from repo_harness.workspace.docker_adapter import (
    DockerCommandOutput,
    DockerWorkspaceAdapter,
    _dockerfile_for_base_image,
)


def test_docker_image_exists_requires_requested_platform(monkeypatch) -> None:
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.environment = SimpleNamespace(docker_path="docker")
    adapter.image_ref = "repo-harness-pre-verl-python-3-9:v0"
    adapter.requested_container_platform = "linux/amd64"

    def fake_run(command, **kwargs):
        assert command == [
            "docker",
            "image",
            "inspect",
            "repo-harness-pre-verl-python-3-9:v0",
            "--format",
            "{{.Os}}/{{.Architecture}}",
        ]
        return subprocess.CompletedProcess(command, 0, stdout="linux/arm64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert adapter._image_exists() is False


def test_docker_image_exists_accepts_matching_platform(monkeypatch) -> None:
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.environment = SimpleNamespace(docker_path="docker")
    adapter.image_ref = "repo-harness-pre-verl-python-3-9:v0"
    adapter.requested_container_platform = "linux/amd64"

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="linux/amd64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert adapter._image_exists() is True


def test_default_dockerfile_installs_ripgrep() -> None:
    dockerfile = _dockerfile_for_base_image("python:3.12-slim")

    assert "ripgrep" in dockerfile
    assert "apt-get install -y --no-install-recommends git ripgrep" in dockerfile


def test_docker_adapter_rebuilds_prebuilt_image_when_required_ripgrep_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    env = SimpleNamespace(
        docker_path="docker",
        docker_context="desktop-linux",
        docker_cli_version="24.0.0",
        docker_server_version="24.0.0",
        docker_desktop_version=None,
        server_platform="linux",
        server_architecture="x86_64",
        mem_total_bytes=8_000_000_000,
    )
    build_calls: list[str] = []
    probes = iter(
        [
            {"rg_available": False, "rg_path": None, "rg_version": None, "rg_probe_exit_code": 127},
            {
                "rg_available": True,
                "rg_path": "/usr/bin/rg",
                "rg_version": "ripgrep 13.0.0",
                "rg_probe_exit_code": 0,
            },
        ]
    )

    monkeypatch.setattr(docker_adapter_module, "inspect_docker_environment", lambda: env)
    monkeypatch.setattr(DockerWorkspaceAdapter, "_ensure_image", lambda self: "prebuilt")
    monkeypatch.setattr(
        DockerWorkspaceAdapter,
        "_inspect_image",
        lambda self: ("a" * 64, "linux/amd64"),
    )
    monkeypatch.setattr(DockerWorkspaceAdapter, "_probe_ripgrep", lambda self: next(probes))
    monkeypatch.setattr(
        DockerWorkspaceAdapter,
        "_build_image",
        lambda self: build_calls.append(self.image_ref),
    )
    monkeypatch.setattr(DockerWorkspaceAdapter, "_write_json", lambda self, path, payload: None)

    def fake_execute(self, command, **kwargs):  # noqa: ANN001, ARG001
        return DockerCommandOutput(
            exit_code=0,
            stdout="x86_64\n",
            stderr="",
            duration_ms=1,
            timeout=False,
            container_name="container",
            cleanup_status="completed",
            facts_ref="container_execution_facts/000001.json",
        )

    monkeypatch.setattr(DockerWorkspaceAdapter, "_execute_in_container", fake_execute)

    adapter = DockerWorkspaceAdapter(
        run_id="run",
        run_dir=tmp_path / "run",
        docker_config=DockerRuntimeConfig(
            image_ref="repo-harness-pre-verl-python-3-8:v0",
            build_base_image="python:3.8",
            build_if_missing=True,
            requested_container_platform="linux/amd64",
            require_ripgrep_for_docker_search=True,
        ),
    )

    assert build_calls == ["repo-harness-pre-verl-python-3-8:v0"]
    assert adapter.backend_facts.build_mode == "local_build"
    assert adapter.backend_facts.rg_available is True
    assert adapter.backend_facts.search_backend_default == "ripgrep"


def test_docker_search_text_uses_single_ripgrep_command(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "run" / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.run_id = "run"
    adapter.run_dir = tmp_path / "run"
    adapter.workspaces_dir = tmp_path / "run" / "workspaces"
    adapter.default_command_timeout_sec = 30
    adapter.config = SimpleNamespace(allow_degraded_python_search_fallback=False)
    adapter.backend_facts = SimpleNamespace(rg_available=True)
    calls: list[list[str]] = []

    def fake_execute(command, **kwargs):
        calls.append(command)
        assert kwargs["command_semantics"] == "agent_tool_search"
        stdout = (
            '{"type":"match","data":{"path":{"text":"test/a.py"},'
            '"lines":{"text":"L031 here\\n"},"line_number":1,'
            '"submatches":[{"match":{"text":"L031"},"start":0,"end":4}]}}\n'
            '{"type":"summary","data":{"stats":{"searches":1505,'
            '"searches_with_match":1,"matched_lines":1,"matches":1}}}\n'
        )
        return DockerCommandOutput(
            exit_code=0,
            stdout=stdout,
            stderr="",
            duration_ms=123,
            timeout=False,
            container_name="container",
            cleanup_status="completed",
            facts_ref="container_execution_facts/000001.json",
        )

    monkeypatch.setattr(adapter, "_execute_in_container", fake_execute)

    payload = adapter.search_text(
        workspace,
        root=".",
        query="L031",
        mode="literal",
        output_mode="files_with_matches",
        max_matches=20,
    )

    assert len(calls) == 1
    assert calls[0][0] == "rg"
    assert "python" not in calls[0]
    assert "--json" in calls[0]
    assert "-F" in calls[0]
    assert payload["search_backend"] == "ripgrep"
    assert payload["matches"] == ["test/a.py"]
    assert payload["scanned_file_count"] == 1505
    assert payload["execution_duration_ms"] == 123
    assert payload["container_execution_facts_ref"] == "container_execution_facts/000001.json"


def test_docker_search_text_marks_file_root_candidate_count_from_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "run" / "workspaces" / "agent_workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "demo.py").write_text("present\n", encoding="utf-8")
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.run_id = "run"
    adapter.run_dir = tmp_path / "run"
    adapter.workspaces_dir = tmp_path / "run" / "workspaces"
    adapter.default_command_timeout_sec = 30
    adapter.config = SimpleNamespace(allow_degraded_python_search_fallback=False)
    adapter.backend_facts = SimpleNamespace(rg_available=True)
    calls: list[list[str]] = []

    def fake_execute(command, **kwargs):
        calls.append(command)
        stdout = (
            '{"type":"summary","data":{"stats":{"searches":0,'
            '"searches_with_match":0,"matched_lines":0,"matches":0}}}\n'
        )
        return DockerCommandOutput(
            exit_code=1,
            stdout=stdout,
            stderr="",
            duration_ms=12,
            timeout=False,
            container_name="container",
            cleanup_status="completed",
            facts_ref="container_execution_facts/000001.json",
        )

    monkeypatch.setattr(adapter, "_execute_in_container", fake_execute)

    payload = adapter.search_text(workspace, root="src/demo.py", query="missing", mode="literal")

    assert len(calls) == 1
    assert payload["root_kind"] == "file"
    assert payload["candidate_fact_source"] == "root_is_file"
    assert payload["candidate_count_reliable"] is True
    assert payload["candidate_file_count"] == 1
    assert payload["scanned_candidate_file_count"] == 1
    assert payload["scanned_file_count"] == 1
    assert payload["scan_complete_reason"] == "complete_no_match_all_visible_candidates_read"


def test_docker_search_text_recovers_directory_candidate_count_when_rg_summary_is_zero(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "run" / "workspaces" / "agent_workspace"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "demo.py").write_text("present\n", encoding="utf-8")
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.run_id = "run"
    adapter.run_dir = tmp_path / "run"
    adapter.workspaces_dir = tmp_path / "run" / "workspaces"
    adapter.default_command_timeout_sec = 30
    adapter.config = SimpleNamespace(allow_degraded_python_search_fallback=False)
    adapter.backend_facts = SimpleNamespace(rg_available=True)
    calls: list[list[str]] = []

    def fake_execute(command, **kwargs):
        calls.append(command)
        if "--files" in command:
            return DockerCommandOutput(
                exit_code=0,
                stdout="src/demo.py\n",
                stderr="",
                duration_ms=3,
                timeout=False,
                container_name="container",
                cleanup_status="completed",
                facts_ref="container_execution_facts/000002.json",
            )
        stdout = (
            '{"type":"summary","data":{"stats":{"searches":0,'
            '"searches_with_match":0,"matched_lines":0,"matches":0}}}\n'
        )
        return DockerCommandOutput(
            exit_code=1,
            stdout=stdout,
            stderr="",
            duration_ms=12,
            timeout=False,
            container_name="container",
            cleanup_status="completed",
            facts_ref="container_execution_facts/000001.json",
        )

    monkeypatch.setattr(adapter, "_execute_in_container", fake_execute)

    payload = adapter.search_text(workspace, root="src", query="missing", mode="literal")

    assert len(calls) == 2
    assert payload["root_kind"] == "directory"
    assert payload["candidate_fact_source"] == "workspace_adapter_list_files"
    assert payload["candidate_count_reliable"] is True
    assert payload["candidate_file_count"] == 1
    assert payload["scanned_candidate_file_count"] == 1
    assert payload["scanned_file_count"] == 1
    assert payload["scan_complete_reason"] == "complete_no_match_all_visible_candidates_read"


def test_docker_search_text_retries_resource_errors_with_single_thread(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "run" / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.run_id = "run"
    adapter.run_dir = tmp_path / "run"
    adapter.workspaces_dir = tmp_path / "run" / "workspaces"
    adapter.default_command_timeout_sec = 30
    adapter.config = SimpleNamespace(allow_degraded_python_search_fallback=False)
    adapter.backend_facts = SimpleNamespace(rg_available=True)
    calls: list[list[str]] = []

    def fake_execute(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            return DockerCommandOutput(
                exit_code=2,
                stdout="",
                stderr="failed to spawn worker thread: Resource temporarily unavailable",
                duration_ms=10,
                timeout=False,
                container_name="container",
                cleanup_status="completed",
                facts_ref="container_execution_facts/000001.json",
            )
        stdout = (
            '{"type":"summary","data":{"stats":{"searches":3,'
            '"searches_with_match":0,"matched_lines":0,"matches":0}}}\n'
        )
        return DockerCommandOutput(
            exit_code=1,
            stdout=stdout,
            stderr="",
            duration_ms=20,
            timeout=False,
            container_name="container",
            cleanup_status="completed",
            facts_ref="container_execution_facts/000002.json",
        )

    monkeypatch.setattr(adapter, "_execute_in_container", fake_execute)

    payload = adapter.search_text(workspace, root=".", query="missing", mode="literal")

    assert len(calls) == 2
    assert "-j" not in calls[0]
    assert "-j" in calls[1]
    assert "1" in calls[1]
    assert payload["search_backend"] == "ripgrep_single_thread_retry"
    assert payload["fallback_reason"] == "ripgrep_resource_limited_single_thread_retry"
    assert payload["scan_complete"] is True
    assert payload["execution_duration_ms"] == 30


def test_docker_search_text_filters_sensitive_ripgrep_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "run" / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    adapter = object.__new__(DockerWorkspaceAdapter)
    adapter.run_id = "run"
    adapter.run_dir = tmp_path / "run"
    adapter.workspaces_dir = tmp_path / "run" / "workspaces"
    adapter.default_command_timeout_sec = 30
    adapter.config = SimpleNamespace(allow_degraded_python_search_fallback=False)
    adapter.backend_facts = SimpleNamespace(rg_available=True)
    captured_command: list[str] = []

    def fake_execute(command, **kwargs):
        captured_command.extend(command)
        stdout = "\n".join(
            [
                '{"type":"match","data":{"path":{"text":"src/app.py"},"lines":{"text":"TOKEN use\\n"},"line_number":1,"submatches":[{"match":{"text":"TOKEN"},"start":0,"end":5}]}}',
                '{"type":"match","data":{"path":{"text":".env"},"lines":{"text":"TOKEN=secret\\n"},"line_number":1,"submatches":[{"match":{"text":"TOKEN"},"start":0,"end":5}]}}',
                '{"type":"match","data":{"path":{"text":"secret.txt"},"lines":{"text":"TOKEN=secret\\n"},"line_number":1,"submatches":[{"match":{"text":"TOKEN"},"start":0,"end":5}]}}',
                '{"type":"match","data":{"path":{"text":"credentials.json"},"lines":{"text":"TOKEN=secret\\n"},"line_number":1,"submatches":[{"match":{"text":"TOKEN"},"start":0,"end":5}]}}',
                '{"type":"match","data":{"path":{"text":"keys/id_rsa"},"lines":{"text":"TOKEN=secret\\n"},"line_number":1,"submatches":[{"match":{"text":"TOKEN"},"start":0,"end":5}]}}',
                '{"type":"match","data":{"path":{"text":"certs/client.pem"},"lines":{"text":"TOKEN=secret\\n"},"line_number":1,"submatches":[{"match":{"text":"TOKEN"},"start":0,"end":5}]}}',
                '{"type":"summary","data":{"stats":{"searches":6,"searches_with_match":6,"matched_lines":6,"matches":6}}}',
            ]
        )
        return DockerCommandOutput(
            exit_code=0,
            stdout=stdout + "\n",
            stderr="",
            duration_ms=5,
            timeout=False,
            container_name="container",
            cleanup_status="completed",
            facts_ref="container_execution_facts/000001.json",
        )

    monkeypatch.setattr(adapter, "_execute_in_container", fake_execute)

    payload = adapter.search_text(workspace, root=".", query="TOKEN", mode="literal")

    assert any(glob == "!.env" for glob in captured_command)
    assert any(glob == "!**/*.pem" for glob in captured_command)
    assert payload["matches"] == ["src/app.py:1:>TOKEN use"]
    assert payload["files_with_matches"] == ["src/app.py"]
    assert payload["hidden_path_count"] == 5
    assert ".env" not in json.dumps(payload)
    assert "secret.txt" not in json.dumps(payload)
