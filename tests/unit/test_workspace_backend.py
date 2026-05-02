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

    with pytest.raises(WorkspaceBackendError, match="16 GiB"):
        inspect_workspace_backend_status(status_file=status_path, assert_stage_complete=True)


def test_docker_backend_status_requires_v3_resource_and_worker_facts(tmp_path: Path):
    status_path = tmp_path / "docker_backend_status.json"
    status = _valid_docker_backend_status().model_copy(update={"docker_mem_total_bytes": 8})
    _write_status(status_path, status)
    with pytest.raises(WorkspaceBackendError, match="16 GiB"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    status = _valid_docker_backend_status().model_copy(update={"evaluation_concurrency": 2})
    _write_status(status_path, status)
    with pytest.raises(WorkspaceBackendError, match="evaluation.concurrency"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    status = _valid_docker_backend_status().model_copy(
        update={"swebench_like_effective_max_workers": 2}
    )
    _write_status(status_path, status)
    with pytest.raises(WorkspaceBackendError, match="effective SWE workers"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    status = _valid_docker_backend_status().model_copy(update={"container_uname_m": ""})
    _write_status(status_path, status)
    with pytest.raises(WorkspaceBackendError, match="uname -m"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    _write_status(status_path, _valid_docker_backend_status())
    summary = inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)
    assert "docker_backend=passed" in summary


def test_docker_backend_inspect_rejects_inconsistent_evidence(tmp_path: Path):
    status_path = tmp_path / "docker_backend_status.json"
    status = _valid_docker_backend_status()
    _write_status(status_path, status)
    facts_path = tmp_path / status.container_execution_facts_refs[0]
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["container_uname_m"] = ""
    facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(WorkspaceBackendError, match="container architecture"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    _write_status(status_path, status)
    facts = json.loads(facts_path.read_text(encoding="utf-8"))
    facts["cleanup_status"] = "skipped"
    facts_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(WorkspaceBackendError, match="cleanup status"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    _write_status(status_path, status)
    backend_path = tmp_path / status.docker_backend_facts_ref
    backend_facts = json.loads(backend_path.read_text(encoding="utf-8"))
    backend_facts["image_platform"] = "linux/amd64"
    backend_path.write_text(
        json.dumps(backend_facts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceBackendError, match="image platform"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    _write_status(status_path, status)
    matrix_path = tmp_path / status.docker_phase_coverage_matrix_ref
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["phases"] = [phase for phase in matrix["phases"] if phase["phase"] != "final_verifier"]
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(WorkspaceBackendError, match="final_verifier"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    _write_status(status_path, status)
    manifest_path = tmp_path / status.container_execution_manifest_ref
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["entry_count"] = manifest["entry_count"] + 1
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(WorkspaceBackendError, match="entry_count"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)

    _write_status(status_path, status)
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["container_execution_manifest_ref"] = "container_execution_facts/other_manifest.json"
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(WorkspaceBackendError, match="manifest ref"):
        inspect_workspace_backend_status(status_file=status_path, assert_docker_backend=True)


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


def _valid_docker_backend_status():
    return build_workspace_backend_status(
        mode="docker_backend",
        docker_available=True,
        docker_available_reason="test_docker_available",
        docker_context="desktop-linux",
        docker_server_platform="linux",
        docker_server_architecture="arm64",
        docker_mem_total_bytes=32 * 1024 * 1024 * 1024,
        evaluation_concurrency=1,
        swebench_like_effective_max_workers=1,
        requested_container_platform="linux/arm64",
        container_uname_m="aarch64",
        image_id="a" * 64,
        image_platform="linux/arm64",
        build_mode="prebuilt",
        network_policy="deny_agent_run",
        mount_policy="workspace_read_write_tmp_only",
        command_timeout_sec=60,
        cleanup_policy="remove_containers_keep_images",
        cleanup_status="completed",
        docker_backend_facts_ref="docker_backend_facts.json",
        container_execution_facts_refs=["container_execution_facts/probe.json"],
        container_execution_manifest_ref="container_execution_facts/manifest.json",
        docker_phase_coverage_matrix_ref="docker_phase_coverage_matrix.json",
    )


def _write_status(path: Path, status) -> None:
    path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if status.docker_backend_facts_ref:
        backend_path = path.parent / status.docker_backend_facts_ref
        backend_path.parent.mkdir(parents=True, exist_ok=True)
        backend_path.write_text(
            json.dumps(
                {
                    "docker_context": status.docker_context,
                    "docker_server_version": "29.4.1",
                    "server_platform": status.docker_server_platform,
                    "server_architecture": status.docker_server_architecture,
                    "requested_container_platform": status.requested_container_platform,
                    "image_ref": "repo-harness-v3-python:stage2",
                    "image_id": status.image_id,
                    "image_platform": status.image_platform,
                    "build_mode": status.build_mode,
                    "cross_architecture_emulation": False,
                    "network_policy": status.network_policy,
                    "mount_policy": status.mount_policy,
                    "timeout_sec": status.command_timeout_sec,
                    "cleanup_policy": status.cleanup_policy,
                    "cleanup_status": status.cleanup_status,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    for ref in status.container_execution_facts_refs:
        facts_path = path.parent / ref
        facts_path.parent.mkdir(parents=True, exist_ok=True)
        facts_path.write_text(
            json.dumps(
                {
                    "command_id": "cmd",
                    "container_id": "container",
                    "image_id": status.image_id,
                    "requested_container_platform": status.requested_container_platform,
                    "container_uname_m": status.container_uname_m,
                    "command": ["uname", "-m"],
                    "workdir": "/repo-harness-run/workspaces/source_checkout",
                    "exit_code": 0,
                    "duration_ms": 1,
                    "network_policy": status.network_policy,
                    "mount_policy": status.mount_policy,
                    "cleanup_status": status.cleanup_status,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if status.container_execution_manifest_ref:
        manifest_path = path.parent / status.container_execution_manifest_ref
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": "repo_harness_container_execution_manifest_v3_v0",
                    "run_id": "run",
                    "entry_count": len(status.container_execution_facts_refs),
                    "entries": [
                        {
                            "command_id": "cmd",
                            "facts_ref": status.container_execution_facts_refs[0],
                            "command_semantics": "source_checkout",
                            "phase": "source_checkout",
                            "exit_code": 0,
                            "timeout": False,
                            "cleanup_status": "completed",
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if status.docker_phase_coverage_matrix_ref:
        matrix_path = path.parent / status.docker_phase_coverage_matrix_ref
        matrix_path.parent.mkdir(parents=True, exist_ok=True)
        required_phases = [
            "source_checkout",
            "setup",
            "agent_tool",
            "run_tests",
            "final_patch_capture",
            "verification_workspace_creation",
            "verifier_patch_apply",
            "test_patch_apply",
            "model_final_patch_apply",
            "fail_to_pass_test_execution",
            "pass_to_pass_test_execution",
            "final_verifier",
        ]
        matrix_path.write_text(
            json.dumps(
                {
                    "schema_version": "repo_harness_docker_phase_coverage_matrix_v3_v0",
                    "run_id": "run",
                    "container_execution_manifest_ref": "container_execution_facts/manifest.json",
                    "required_phases": required_phases,
                    "phases": [
                        {
                            "phase": phase,
                            "status": "passed",
                            "facts_refs": [status.container_execution_facts_refs[0]],
                        }
                        for phase in required_phases
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
