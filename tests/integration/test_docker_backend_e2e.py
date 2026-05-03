import json
import subprocess
import textwrap
from pathlib import Path

import pytest

from repo_harness.config import DockerRuntimeConfig
from repo_harness.evaluation.runner import run_task
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import inspect_workspace_backend_status
from repo_harness.workspace.docker_adapter import (
    EFFECTIVE_DOCKER_MOUNT_POLICY,
    DockerWorkspaceAdapter,
)


ROOT = Path(__file__).resolve().parents[2]


def test_docker_backend_replay_smoke_records_facts(tmp_path: Path):
    platform = _docker_platform_or_skip()
    config_path = tmp_path / "docker_backend.yaml"
    run_root = tmp_path / "runs"
    config_path.write_text(
        textwrap.dedent(
            f"""
            run_id_prefix: v3_docker
            model:
              provider: replay
              model_id: replay-script-v0
              replay_script_path: {ROOT / "tests/fixtures/replays/task_001_success.yaml"}
            runtime:
              scaffold_id: simple_react
              execution_mode: docker
              permission_mode: auto
              docker_backend:
                image_ref: repo-harness-v3-python:stage2
                build_if_missing: true
                requested_container_platform: {platform}
                network_policy: deny_agent_run
                mount_policy: workspace_read_write_tmp_only
                cleanup_policy: remove_containers_keep_images
            workspace:
              output_dir: {run_root}
              keep_workspace: true
              default_command_timeout_sec: 90
            evaluation:
              concurrency: 1
            swebench_like:
              max_workers: 1
            """
        ).lstrip(),
        encoding="utf-8",
    )

    run_dir = run_task(
        ROOT / "tests/fixtures/tasks/task_001.yaml",
        config_path=config_path,
        output_dir=run_root,
        run_id="v3-docker-smoke",
    )

    status_path = run_dir / "docker_backend_status.json"
    summary = inspect_workspace_backend_status(
        status_file=status_path,
        assert_docker_backend=True,
    )
    status = json.loads(status_path.read_text(encoding="utf-8"))
    matrix = json.loads((run_dir / "docker_phase_coverage_matrix.json").read_text(encoding="utf-8"))
    container_manifest = json.loads(
        (run_dir / "container_execution_facts" / "manifest.json").read_text(encoding="utf-8")
    )
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    run_config_facts = json.loads((run_dir / "run_config_facts.json").read_text(encoding="utf-8"))

    assert "docker_backend=passed" in summary
    assert status["docker_backend_implemented"] is True
    assert status["docker_execution_mode_behavior"] == "docker_backend_active"
    assert status["evaluation_concurrency"] == 1
    assert status["swebench_like_effective_max_workers"] == 1
    assert status["container_uname_m"]
    assert status["cleanup_status"] == "completed"
    assert status["container_execution_facts_refs"]
    assert status["container_execution_manifest_ref"] == "container_execution_facts/manifest.json"
    assert status["docker_phase_coverage_matrix_ref"] == "docker_phase_coverage_matrix.json"
    assert container_manifest["entry_count"] == len(container_manifest["entries"])
    phase_status = {phase["phase"]: phase["status"] for phase in matrix["phases"]}
    assert phase_status["source_checkout"] == "passed"
    assert phase_status["setup"] == "passed"
    assert phase_status["agent_tool"] == "passed"
    assert phase_status["run_tests"] == "passed"
    assert phase_status["final_patch_capture"] == "passed"
    assert phase_status["verification_workspace_creation"] == "passed"
    assert phase_status["model_final_patch_apply"] == "passed"
    assert phase_status["fail_to_pass_test_execution"] == "passed"
    assert phase_status["pass_to_pass_test_execution"] == "passed"
    assert phase_status["final_verifier"] == "passed"
    assert phase_status["verifier_patch_apply"] == "not_applicable"
    assert phase_status["test_patch_apply"] == "not_applicable"
    assert phase_status["supporting_execution"] == "passed"
    covered_refs = {
        ref
        for phase in matrix["phases"]
        for ref in phase.get("facts_refs", [])
    }
    manifest_refs = {entry["facts_ref"] for entry in container_manifest["entries"]}
    assert manifest_refs == covered_refs
    assert metrics["run_outcome"] == "success"
    assert (
        run_config_facts["environment_fingerprint"]["workspace_execution"]["workspace_backend"][
            "backend"
        ]
        == "docker"
    )
    assert status["mount_policy"] == EFFECTIVE_DOCKER_MOUNT_POLICY


def test_docker_backend_mounts_run_evidence_read_only(tmp_path: Path):
    platform = _docker_platform_or_skip()
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "tamper_workspace"
    workspace.mkdir(parents=True)
    guard_path = run_dir / "evidence_guard.json"
    guard_path.write_text("original\n", encoding="utf-8")

    adapter = DockerWorkspaceAdapter(
        run_id="v3-docker-mount-guard",
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

    with RunRecorder("v3-docker-mount-guard", run_dir, task_id="mount_guard") as recorder:
        result = adapter.run_command(
            workspace,
            "printf workspace-ok > workspace_ok.txt; printf tampered > /repo-harness-run/evidence_guard.json",
            recorder=recorder,
            allow_shell=True,
            command_semantics="agent_tool",
        )

    assert result.exit_code != 0
    assert (workspace / "workspace_ok.txt").read_text(encoding="utf-8") == "workspace-ok"
    assert guard_path.read_text(encoding="utf-8") == "original\n"


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
        pytest.skip(f"Docker is unavailable for integration smoke: {exc}")
    if architecture in {"aarch64", "arm64"}:
        return "linux/arm64"
    return "linux/amd64"
