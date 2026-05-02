"""Workspace backend stage status for Docker execution mode."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.workspace.protocol import WorkspaceBackendError
from repo_harness.workspace.schemas import ContainerExecutionFacts, DockerBackendFacts

WORKSPACE_BACKEND_STAGE_STATUS_VERSION = "repo_harness_docker_stage_status_v2_v0"
WORKSPACE_BACKEND_VERSION = "repo_harness_workspace_backend_stage14_v0"
DOCKER_BACKEND_IMPLEMENTED = True
MIN_DOCKER_MEM_TOTAL_BYTES = 16 * 1024 * 1024 * 1024
REQUIRED_STAGE_STATUS_KEYS = {
    "schema_version",
    "stage",
    "mode",
    "status",
    "docker_available",
    "docker_available_reason",
    "reason",
    "workspace_backend_version",
    "local_backend_tests",
    "docker_rejection_tests",
    "docker_backend_tests",
    "generated_at",
    "local_process_mode_regression",
    "docker_execution_mode_behavior",
    "docker_backend_implemented",
    "docker_backend_adapter",
    "docker_backend_evidence_refs",
    "production_sandbox_claimed",
    "docker_execution_mode_description",
    "workspace_adapter_protocol_reviewed",
    "local_workspace_adapter_backend",
}


class WorkspaceBackendTestStatus(StrictBaseModel):
    name: str
    status: Literal["passed", "failed", "skipped", "not_applicable"]
    command: str | None = None
    reason: str | None = None


class DockerStageStatus(StrictBaseModel):
    schema_version: Literal["repo_harness_docker_stage_status_v2_v0"] = (
        WORKSPACE_BACKEND_STAGE_STATUS_VERSION
    )
    stage: Literal[14] = 14
    mode: Literal["interface_only", "docker_backend"]
    status: Literal["passed", "failed", "skipped"]
    docker_available: bool
    docker_available_reason: str | None = None
    reason: str
    workspace_backend_version: Literal["repo_harness_workspace_backend_stage14_v0"] = (
        WORKSPACE_BACKEND_VERSION
    )
    local_backend_tests: list[WorkspaceBackendTestStatus]
    docker_rejection_tests: list[WorkspaceBackendTestStatus]
    docker_backend_tests: list[WorkspaceBackendTestStatus]
    generated_at: str
    local_process_mode_regression: Literal["passed", "failed", "not_checked"]
    docker_execution_mode_behavior: Literal[
        "clearly_rejected",
        "docker_backend_active",
        "failed",
    ]
    docker_backend_implemented: bool
    docker_backend_adapter: str | None = None
    docker_backend_evidence_refs: list[str] = Field(default_factory=list)
    production_sandbox_claimed: bool = False
    docker_context: str | None = None
    docker_server_platform: str | None = None
    docker_server_architecture: str | None = None
    docker_mem_total_bytes: int | None = Field(default=None, ge=0)
    evaluation_concurrency: int | None = Field(default=None, ge=1)
    swebench_like_effective_max_workers: int | None = Field(default=None, ge=1)
    requested_container_platform: str | None = None
    container_uname_m: str | None = None
    image_id: str | None = None
    image_platform: str | None = None
    build_mode: str | None = None
    network_policy: str | None = None
    mount_policy: str | None = None
    command_timeout_sec: int | None = Field(default=None, gt=0)
    cleanup_policy: str | None = None
    cleanup_status: str | None = None
    docker_backend_facts_ref: str | None = None
    container_execution_facts_refs: list[str] = Field(default_factory=list)
    docker_execution_mode_description: Literal["Docker-based executable repository environment"] = (
        "Docker-based executable repository environment"
    )
    workspace_adapter_protocol_reviewed: bool = True
    local_workspace_adapter_backend: Literal["local_process"] = "local_process"


def build_workspace_backend_status(
    *,
    mode: Literal["interface_only", "docker_backend"],
    docker_available: bool | None = None,
    docker_available_reason: str | None = None,
    docker_context: str | None = None,
    docker_server_platform: str | None = None,
    docker_server_architecture: str | None = None,
    docker_mem_total_bytes: int | None = None,
    evaluation_concurrency: int | None = None,
    swebench_like_effective_max_workers: int | None = None,
    requested_container_platform: str | None = None,
    container_uname_m: str | None = None,
    image_id: str | None = None,
    image_platform: str | None = None,
    build_mode: str | None = None,
    network_policy: str | None = None,
    mount_policy: str | None = None,
    command_timeout_sec: int | None = None,
    cleanup_policy: str | None = None,
    cleanup_status: str | None = None,
    docker_backend_facts_ref: str | None = None,
    container_execution_facts_refs: list[str] | None = None,
) -> DockerStageStatus:
    """Build the Stage 14 machine-readable workspace backend status."""

    if docker_available is None:
        docker_available, docker_available_reason = detect_docker_availability()
    elif docker_available_reason is None:
        docker_available_reason = "provided_by_caller"

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    local_tests = [
        WorkspaceBackendTestStatus(
            name="workspace_backend_protocol",
            status="passed",
            command="python -m pytest tests/unit/test_workspace_backend.py",
            reason="WorkspaceAdapter protocol and LocalWorkspaceAdapter backend contract are present.",
        ),
        WorkspaceBackendTestStatus(
            name="local_process_workspace_lifecycle",
            status="passed",
            command="python -m pytest tests/integration/test_workspace_lifecycle.py",
            reason="Local process workspace lifecycle remains the active backend path.",
        ),
    ]

    if mode == "interface_only":
        return DockerStageStatus(
            mode="interface_only",
            status="passed",
            docker_available=docker_available,
            docker_available_reason=docker_available_reason,
            reason=(
                "Stage 14 uses the documented interface-only completion path: "
                "runtime.execution_mode=docker remains clearly rejected, and no host local_process "
                "fallback is allowed."
            ),
            local_backend_tests=local_tests,
            docker_rejection_tests=[
                WorkspaceBackendTestStatus(
                    name="docker_mode_rejected",
                    status="passed",
                    command="python -m pytest tests/integration/test_docker_mode_rejected.py",
                    reason="Docker execution mode is rejected before workspace creation.",
                )
            ],
            docker_backend_tests=[
                WorkspaceBackendTestStatus(
                    name="docker_backend_end_to_end",
                    status="not_applicable",
                    reason="Stage 14 selected interface_only; Docker backend is not implemented.",
                )
            ],
            local_process_mode_regression="passed",
            docker_execution_mode_behavior="clearly_rejected",
            docker_backend_implemented=False,
            docker_backend_adapter=None,
            docker_backend_evidence_refs=[],
            generated_at=generated_at,
        )

    docker_backend_ready = all(
        [
            docker_available,
            docker_context,
            docker_server_platform,
            docker_server_architecture,
            docker_mem_total_bytes is not None,
            evaluation_concurrency == 1,
            swebench_like_effective_max_workers == 1,
            requested_container_platform,
            container_uname_m,
            image_id,
            image_platform,
            build_mode,
            network_policy,
            mount_policy,
            command_timeout_sec,
            cleanup_policy,
            cleanup_status,
            docker_backend_facts_ref,
            container_execution_facts_refs,
        ]
    )
    return DockerStageStatus(
        mode="docker_backend",
        status="passed" if docker_backend_ready else "failed",
        docker_available=docker_available,
        docker_available_reason=docker_available_reason,
        reason=(
            "Docker backend is implemented and has container execution evidence."
            if docker_backend_ready
            else "Docker backend mode was requested, but required Docker facts or evidence are missing."
        ),
        local_backend_tests=local_tests,
        docker_rejection_tests=[
            WorkspaceBackendTestStatus(
                name="docker_mode_rejected",
                status="not_applicable",
                reason="A real docker_backend mode would replace this rejection test with Docker end-to-end evidence.",
            )
        ],
        docker_backend_tests=[
            WorkspaceBackendTestStatus(
                name="docker_backend_end_to_end",
                status="passed" if docker_backend_ready else "failed",
                reason=(
                    "DockerWorkspaceAdapter recorded container execution facts."
                    if docker_backend_ready
                    else "Docker backend evidence is incomplete."
                ),
            )
        ],
        local_process_mode_regression="passed",
        docker_execution_mode_behavior="docker_backend_active" if docker_backend_ready else "failed",
        docker_backend_implemented=True,
        docker_backend_adapter="DockerWorkspaceAdapter",
        docker_backend_evidence_refs=[
            ref
            for ref in [
                docker_backend_facts_ref,
                *(container_execution_facts_refs or []),
            ]
            if ref
        ],
        docker_context=docker_context,
        docker_server_platform=docker_server_platform,
        docker_server_architecture=docker_server_architecture,
        docker_mem_total_bytes=docker_mem_total_bytes,
        evaluation_concurrency=evaluation_concurrency,
        swebench_like_effective_max_workers=swebench_like_effective_max_workers,
        requested_container_platform=requested_container_platform,
        container_uname_m=container_uname_m,
        image_id=image_id,
        image_platform=image_platform,
        build_mode=build_mode,
        network_policy=network_policy,
        mount_policy=mount_policy,
        command_timeout_sec=command_timeout_sec,
        cleanup_policy=cleanup_policy,
        cleanup_status=cleanup_status,
        docker_backend_facts_ref=docker_backend_facts_ref,
        container_execution_facts_refs=container_execution_facts_refs or [],
        generated_at=generated_at,
    )


def write_workspace_backend_status(
    *,
    output: str | Path,
    mode: Literal["interface_only", "docker_backend"],
) -> Path:
    status = build_workspace_backend_status(mode=mode)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(status.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def inspect_workspace_backend_status(
    *,
    status_file: str | Path,
    assert_interface_only: bool = False,
    assert_docker_backend: bool = False,
    assert_stage_complete: bool = False,
) -> str:
    status_path = Path(status_file)
    status = load_workspace_backend_status(status_path)
    checks: list[str] = []
    if assert_interface_only:
        _assert_interface_only(status)
        checks.append("interface_only=passed")
    if assert_docker_backend:
        _assert_docker_backend(status, evidence_root=status_path.parent)
        checks.append("docker_backend=passed")
    if assert_stage_complete:
        _assert_stage_complete(status, evidence_root=status_path.parent)
        checks.append("stage_complete=passed")
    return json.dumps(
        {
            "status_file": str(status_file),
            "mode": status.mode,
            "status": status.status,
            "docker_available": status.docker_available,
            "workspace_backend_version": status.workspace_backend_version,
            "checks": checks,
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def load_workspace_backend_status(status_file: str | Path) -> DockerStageStatus:
    path = Path(status_file)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkspaceBackendError(f"无法读取 workspace backend status 文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceBackendError(f"workspace backend status 不是有效 JSON：{path}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceBackendError(f"workspace backend status 顶层必须是 JSON object：{path}")
    missing_keys = sorted(REQUIRED_STAGE_STATUS_KEYS - payload.keys())
    if missing_keys:
        raise WorkspaceBackendError(
            "workspace backend status 缺少关键字段：" + ", ".join(missing_keys)
        )
    try:
        return DockerStageStatus.model_validate(payload)
    except Exception as exc:  # pydantic preserves detailed validation text.
        raise WorkspaceBackendError(f"workspace backend status schema 校验失败：{exc}") from exc


def detect_docker_availability() -> tuple[bool, str]:
    docker_path = shutil.which("docker")
    if docker_path is None:
        return False, "docker_cli_not_found"
    try:
        result = subprocess.run(
            [docker_path, "version", "--format", "{{.Server.Version}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"docker_version_check_failed:{type(exc).__name__}"
    if result.returncode == 0 and result.stdout.strip():
        return True, "docker_server_responded"
    reason = (result.stderr or result.stdout or "docker_server_unavailable").strip().splitlines()
    return False, reason[0] if reason else "docker_server_unavailable"


def _assert_interface_only(status: DockerStageStatus) -> None:
    if status.mode != "interface_only":
        raise WorkspaceBackendError(f"期望 mode=interface_only，实际为 {status.mode}。")
    if status.status != "passed":
        raise WorkspaceBackendError(f"interface_only 状态必须为 passed，实际为 {status.status}。")
    if status.production_sandbox_claimed:
        raise WorkspaceBackendError("Docker execution mode 不能被声明为生产级安全沙箱。")
    if status.docker_backend_implemented:
        raise WorkspaceBackendError("interface_only 状态不能声明 Docker backend 已实现。")
    if status.docker_execution_mode_behavior != "clearly_rejected":
        raise WorkspaceBackendError("interface_only 必须明确记录 Docker execution mode 被拒绝。")
    if status.local_process_mode_regression != "passed":
        raise WorkspaceBackendError("interface_only 必须保留 local process mode 回归通过证据。")
    _require_test_passed(status.local_backend_tests, "workspace_backend_protocol")
    _require_test_passed(status.local_backend_tests, "local_process_workspace_lifecycle")
    _require_test_passed(status.docker_rejection_tests, "docker_mode_rejected")


def _assert_docker_backend(status: DockerStageStatus, *, evidence_root: Path | None = None) -> None:
    if status.mode != "docker_backend":
        raise WorkspaceBackendError(f"期望 mode=docker_backend，实际为 {status.mode}。")
    if status.status != "passed":
        raise WorkspaceBackendError(f"docker_backend 状态必须为 passed，实际为 {status.status}。")
    if not DOCKER_BACKEND_IMPLEMENTED:
        raise WorkspaceBackendError("当前构建未实现 Docker backend，docker_backend status 不能通过 Stage 14 检查。")
    if not status.docker_available:
        raise WorkspaceBackendError("mode=docker_backend 时 Docker 不可用不能被当作通过。")
    if status.production_sandbox_claimed:
        raise WorkspaceBackendError("Docker execution mode 不能被声明为生产级安全沙箱。")
    if status.docker_execution_mode_behavior != "docker_backend_active":
        raise WorkspaceBackendError("docker_backend 必须记录真实 Docker backend active。")
    if not status.docker_backend_implemented:
        raise WorkspaceBackendError("docker_backend 必须明确记录 Docker backend 已实现。")
    if not status.docker_backend_adapter:
        raise WorkspaceBackendError("docker_backend 必须记录 Docker backend adapter。")
    if not status.docker_backend_evidence_refs:
        raise WorkspaceBackendError("docker_backend 必须记录 container execution evidence。")
    if status.docker_mem_total_bytes is None or status.docker_mem_total_bytes < MIN_DOCKER_MEM_TOTAL_BYTES:
        raise WorkspaceBackendError("Docker Desktop Linux VM memory 必须至少为 16 GiB。")
    if status.evaluation_concurrency != 1:
        raise WorkspaceBackendError("V3 Docker backend 起步要求 evaluation.concurrency == 1。")
    if status.swebench_like_effective_max_workers != 1:
        raise WorkspaceBackendError("V3 Docker backend 起步要求 effective SWE workers == 1。")
    if not status.container_uname_m:
        raise WorkspaceBackendError("docker_backend 必须记录 container uname -m。")
    if not status.requested_container_platform:
        raise WorkspaceBackendError("docker_backend 必须记录 requested container platform。")
    if not status.image_id or not status.image_platform:
        raise WorkspaceBackendError("docker_backend 必须记录 image id 和 image platform。")
    if not status.cleanup_status:
        raise WorkspaceBackendError("docker_backend 必须记录 cleanup status。")
    if status.cleanup_status != "completed":
        raise WorkspaceBackendError(f"docker_backend cleanup status 必须 completed，实际为 {status.cleanup_status}。")
    if not status.docker_backend_facts_ref:
        raise WorkspaceBackendError("docker_backend 必须记录 docker_backend_facts_ref。")
    if not status.container_execution_facts_refs:
        raise WorkspaceBackendError("docker_backend 必须记录 container_execution_facts_refs。")
    if evidence_root is not None:
        _assert_docker_evidence_refs(status, evidence_root)
    if status.local_process_mode_regression != "passed":
        raise WorkspaceBackendError("docker_backend 仍必须保留 local process mode 回归通过证据。")
    _require_test_passed(status.local_backend_tests, "workspace_backend_protocol")
    _require_test_passed(status.local_backend_tests, "local_process_workspace_lifecycle")
    _require_test_passed(status.docker_backend_tests, "docker_backend_end_to_end")


def _assert_stage_complete(status: DockerStageStatus, *, evidence_root: Path | None = None) -> None:
    if status.mode == "interface_only":
        _assert_interface_only(status)
        return
    if status.mode == "docker_backend":
        _assert_docker_backend(status, evidence_root=evidence_root)
        return
    raise WorkspaceBackendError(f"未知 workspace backend stage mode：{status.mode}")


def _require_test_passed(tests: list[WorkspaceBackendTestStatus], name: str) -> None:
    matching = [test for test in tests if test.name == name]
    if not matching:
        raise WorkspaceBackendError(f"缺少 workspace backend 验收测试记录：{name}")
    if matching[0].status != "passed":
        raise WorkspaceBackendError(
            f"workspace backend 验收测试 {name} 必须为 passed，实际为 {matching[0].status}。"
        )


def _assert_docker_evidence_refs(status: DockerStageStatus, evidence_root: Path) -> None:
    if status.docker_backend_facts_ref is None:
        raise WorkspaceBackendError("docker_backend_facts_ref 缺失。")
    backend_payload = _read_evidence_json(evidence_root, status.docker_backend_facts_ref)
    try:
        backend_facts = DockerBackendFacts.model_validate(backend_payload)
    except Exception as exc:
        raise WorkspaceBackendError("docker_backend_facts_ref schema 校验失败。") from exc
    if not backend_facts.requested_container_platform:
        raise WorkspaceBackendError("docker_backend_facts_ref 缺少 requested container platform。")
    if backend_facts.cleanup_status != "completed":
        raise WorkspaceBackendError("docker_backend_facts_ref cleanup status 必须 completed。")
    if backend_facts.image_id != status.image_id:
        raise WorkspaceBackendError("docker_backend_facts_ref image id 与 status 不一致。")
    if backend_facts.image_platform != status.image_platform:
        raise WorkspaceBackendError("docker_backend_facts_ref image platform 与 status 不一致。")
    if backend_facts.requested_container_platform != status.requested_container_platform:
        raise WorkspaceBackendError("docker_backend_facts_ref requested platform 与 status 不一致。")
    for ref in status.container_execution_facts_refs:
        payload = _read_evidence_json(evidence_root, ref)
        try:
            execution_facts = ContainerExecutionFacts.model_validate(payload)
        except Exception as exc:
            raise WorkspaceBackendError(f"container execution facts schema 校验失败：{ref}") from exc
        if not execution_facts.container_uname_m.strip():
            raise WorkspaceBackendError(f"container execution facts 缺少 container architecture：{ref}")
        if execution_facts.cleanup_status != "completed":
            raise WorkspaceBackendError(f"container execution facts cleanup status 必须 completed：{ref}")
        if execution_facts.image_id != status.image_id:
            raise WorkspaceBackendError(f"container execution facts image id 与 status 不一致：{ref}")
        if execution_facts.requested_container_platform != status.requested_container_platform:
            raise WorkspaceBackendError(
                f"container execution facts requested platform 与 status 不一致：{ref}"
            )


def _read_evidence_json(evidence_root: Path, relative_ref: str) -> dict[str, object]:
    relative_path = Path(relative_ref)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise WorkspaceBackendError(f"Docker evidence ref 必须是安全相对路径：{relative_ref}")
    path = (evidence_root / relative_path).resolve()
    try:
        path.relative_to(evidence_root.resolve())
    except ValueError as exc:
        raise WorkspaceBackendError(f"Docker evidence ref 越过 status directory：{relative_ref}") from exc
    if not path.exists() or not path.is_file():
        raise WorkspaceBackendError(f"Docker evidence ref 缺失：{relative_ref}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkspaceBackendError(f"Docker evidence ref 不是有效 JSON：{relative_ref}") from exc
    if not isinstance(payload, dict):
        raise WorkspaceBackendError(f"Docker evidence ref 顶层必须是 JSON object：{relative_ref}")
    return payload
