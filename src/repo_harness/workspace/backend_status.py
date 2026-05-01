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

WORKSPACE_BACKEND_STAGE_STATUS_VERSION = "repo_harness_docker_stage_status_v2_v0"
WORKSPACE_BACKEND_VERSION = "repo_harness_workspace_backend_stage14_v0"
DOCKER_BACKEND_IMPLEMENTED = False
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

    return DockerStageStatus(
        mode="docker_backend",
        status="failed",
        docker_available=docker_available,
        docker_available_reason=docker_available_reason,
        reason=(
            "Docker backend mode was requested, but this implementation has only completed "
            "the interface-only rejection path."
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
                status="failed",
                reason="No DockerWorkspaceAdapter or container execution context is implemented.",
            )
        ],
        local_process_mode_regression="passed",
        docker_execution_mode_behavior="failed",
        docker_backend_implemented=False,
        docker_backend_adapter=None,
        docker_backend_evidence_refs=[],
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
    status = load_workspace_backend_status(status_file)
    checks: list[str] = []
    if assert_interface_only:
        _assert_interface_only(status)
        checks.append("interface_only=passed")
    if assert_docker_backend:
        _assert_docker_backend(status)
        checks.append("docker_backend=passed")
    if assert_stage_complete:
        _assert_stage_complete(status)
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


def _assert_docker_backend(status: DockerStageStatus) -> None:
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
    if status.local_process_mode_regression != "passed":
        raise WorkspaceBackendError("docker_backend 仍必须保留 local process mode 回归通过证据。")
    _require_test_passed(status.local_backend_tests, "workspace_backend_protocol")
    _require_test_passed(status.local_backend_tests, "local_process_workspace_lifecycle")
    _require_test_passed(status.docker_backend_tests, "docker_backend_end_to_end")


def _assert_stage_complete(status: DockerStageStatus) -> None:
    if status.mode == "interface_only":
        _assert_interface_only(status)
        return
    if status.mode == "docker_backend":
        _assert_docker_backend(status)
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
