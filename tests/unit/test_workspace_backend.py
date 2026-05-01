import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.workspace import (
    LocalWorkspaceAdapter,
    WorkspaceAdapter,
    WorkspaceBackend,
    WorkspaceBackendError,
    WorkspaceBackendTestStatus,
    build_workspace_backend_status,
    inspect_workspace_backend_status,
    load_workspace_backend_status,
)


def test_local_workspace_adapter_satisfies_workspace_protocol(tmp_path: Path):
    adapter = LocalWorkspaceAdapter(run_id="backend-protocol", run_dir=tmp_path / "run")

    assert isinstance(adapter, WorkspaceAdapter)
    assert adapter.backend == WorkspaceBackend.local_process


def test_interface_only_status_passes_stage_complete(tmp_path: Path):
    status = build_workspace_backend_status(
        mode="interface_only",
        docker_available=False,
        docker_available_reason="test_no_docker_required",
    )
    status_path = tmp_path / "docker_stage_status.json"
    status_path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    loaded = load_workspace_backend_status(status_path)
    summary = inspect_workspace_backend_status(
        status_file=status_path,
        assert_interface_only=True,
        assert_stage_complete=True,
    )

    assert loaded.mode == "interface_only"
    assert loaded.status == "passed"
    assert loaded.docker_execution_mode_behavior == "clearly_rejected"
    assert loaded.docker_backend_implemented is False
    assert loaded.production_sandbox_claimed is False
    assert "stage_complete=passed" in summary


def test_workspace_backend_status_cli_maps_interface_only_mode(tmp_path: Path):
    status_path = tmp_path / "docker_stage_status.json"

    assert main(["workspace-backend-status", "--output", str(status_path), "--mode", "interface-only"]) == 0
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "interface_only"
    assert payload["docker_backend_implemented"] is False

    assert (
        main(
            [
                "inspect-workspace-backend",
                "--status-file",
                str(status_path),
                "--assert-stage-complete",
            ]
        )
        == 0
    )


def test_docker_backend_status_cannot_pass_without_backend(tmp_path: Path):
    status = build_workspace_backend_status(
        mode="docker_backend",
        docker_available=True,
        docker_available_reason="test_docker_available",
    )
    status_path = tmp_path / "docker_stage_status.json"
    status_path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceBackendError, match="docker_backend 状态必须为 passed"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    with pytest.raises(WorkspaceBackendError, match="docker_backend 状态必须为 passed"):
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)


def test_forged_docker_backend_passed_status_is_rejected(tmp_path: Path):
    status = build_workspace_backend_status(
        mode="interface_only",
        docker_available=True,
        docker_available_reason="test_docker_available",
    ).model_copy(
        update={
            "mode": "docker_backend",
            "status": "passed",
            "docker_execution_mode_behavior": "docker_backend_active",
            "docker_backend_implemented": True,
            "docker_backend_adapter": "DockerWorkspaceAdapter",
            "docker_backend_evidence_refs": ["runs/fake/docker_e2e.json"],
            "docker_backend_tests": [
                WorkspaceBackendTestStatus(
                    name="docker_backend_end_to_end",
                    status="passed",
                    reason="forged by test",
                )
            ],
        }
    )
    status_path = tmp_path / "docker_stage_status.json"
    status_path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceBackendError, match="当前构建未实现 Docker backend"):
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)


def test_workspace_backend_status_requires_explicit_key_fields(tmp_path: Path):
    status = build_workspace_backend_status(
        mode="interface_only",
        docker_available=False,
        docker_available_reason="test_no_docker_required",
    )
    payload = status.model_dump(mode="json")
    del payload["schema_version"]
    del payload["workspace_backend_version"]
    status_path = tmp_path / "docker_stage_status.json"
    status_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceBackendError, match="schema_version"):
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)


def test_interface_only_rejects_production_sandbox_claim(tmp_path: Path):
    status = build_workspace_backend_status(
        mode="interface_only",
        docker_available=False,
        docker_available_reason="test_no_docker_required",
    ).model_copy(update={"production_sandbox_claimed": True})
    status_path = tmp_path / "docker_stage_status.json"
    status_path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceBackendError, match="生产级安全沙箱"):
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)


def test_interface_only_requires_docker_rejection_evidence(tmp_path: Path):
    status = build_workspace_backend_status(
        mode="interface_only",
        docker_available=False,
        docker_available_reason="test_no_docker_required",
    ).model_copy(
        update={
            "docker_rejection_tests": [
                WorkspaceBackendTestStatus(
                    name="docker_mode_rejected",
                    status="failed",
                    reason="test failure",
                )
            ]
        }
    )
    status_path = tmp_path / "docker_stage_status.json"
    status_path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorkspaceBackendError, match="docker_mode_rejected"):
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)
