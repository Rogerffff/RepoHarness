"""唯一正式 rollout Docker profile + 独立 grader Docker profile（W3b，决策包 D2-2 / D2-4）。

owner 2026-09-04 细化："sandbox profile 只做启动前验证和 run 级记录，不再建立任何逐轨迹
capability eligibility"。本模块因此只做三件事：

1. **创建期强制**：rollout / grader 容器的 `docker run` 参数由本模块的两个 profile 直接组装
   （`RolloutSandboxProfile.docker_run_args` / `GraderSandboxProfile.docker_run_args`），
   formal 路径没有"关掉某项安全约束"的开关——能改的只有数值（PID/CPU/内存/存储预算，
   数值归 C 校准）与部署事实（模型代理上游地址、内部服务清单、relay 镜像）。
2. **启动前核对**：容器创建后、Claude Code / 候选测试启动前，做一次 `docker inspect`
   （结构事实：user/caps/no-new-privileges/pids/cpu/memory+swap/tmpfs/mount/network）
   加一次容器内探针（实际事实：非 root uid、CapEff=0、NoNewPrivs=1、cgroup 限额、
   网络 egress——向公网/云 metadata/宿主直连必须失败、向模型代理 relay 必须成功、
   隐藏路径不可读、Git 远端/reflog 已清）。任一必需项不符 → 不启动模型/测试、停止 run
   （调用方抛 typed fatal 走既有关停链）。
3. **run 级记录**：`runtime_profile_digest`（两个 profile 参数的摘要）+ 启动前验证报告
   （实际值）写入 run evidence 一次；样本/audit 只盖 `runtime_profile_digest` 一个键供 join。
   **不做**每轨迹能力事实、不进 eligibility。

三层边界在 Docker 上的落法（本机 Docker Desktop 29.4 与 Linux 引擎实测，见 w3b_report.md）：

- **模型控制进程非 root**：容器主进程只是 `sleep infinity`；harness 以 `docker exec -u agent`
  启动（slime ClaudeCodeHarness 现状），agent 用户由可信初始化（root）按固定 uid 预建。
  探针以 agent 身份读 `/proc/self/status` 证明 uid≠0、CapEff=0、NoNewPrivs=1。
- **CapEff=0 + no-new-privileges**：容器 `--cap-drop ALL --security-opt no-new-privileges`，
  再 `--cap-add` 一组**只有 root 可信初始化会用到**的能力（CHOWN/DAC_OVERRIDE/
  DAC_READ_SEARCH/FOWNER/KILL：建用户、chown -R /testbed、读 agent 建的 0600 文件、
  屏障 `pkill -u agent`）。非 root 进程拿不到任何能力（无 ambient cap；no_new_privs 下
  setuid 位与文件能力都不生效——实测 `su` 报 Authentication failure、`os.setuid(0)` EPERM）。
- **网络 egress allowlist（真实阻断）**：每个 attempt 一张私有 `--internal` 网络并设
  `com.docker.network.bridge.gateway_mode_ipv4=isolated`（网桥不配地址：公网/云 metadata/
  宿主服务在内核路由层就不可达——实测 `Network is unreachable`；普通 `--internal` 网络
  宿主网关仍可达，所以不采用）。唯一出口是本 run 的 **egress relay 容器**（同时挂在该
  attempt 网络与默认 bridge 上，只把 `rh2-egress-relay:<listen_port>` 转发到模型代理上游
  与环境声明的内部服务）。"仅设代理 env / 普通 bridge"不算证明——探针真的去连。
- **hidden/grader 资产不可访问**：rollout 容器只写 public bundle；private bundle 永不进
  rollout（contracts WorkspaceHandle 已在 schema 层拒绝），探针再核对 mount/env 清单与隐藏
  路径不可读；canary 反例在测试里验证（tests/adapters/test_w3b_sandbox_docker.py）。
- **solution-bearing Git 状态不可恢复**：可信初始化跑 `git-sanitize`：删远端、删所有不是
  HEAD 祖先的 ref（未来 tag/分支/stash）、删 reflog、`repack -a -d` + `prune --expire=now`
  处理 dangling 未来对象，再 `fsck --unreachable --connectivity-only` 证明为零；保留 base
  之前的正常历史（`rev-list --count HEAD` 前后相等）。
- **宿主 bind mount 只来自安全清单**：rollout 容器零 bind mount；grader 只允许显式声明的
  只读快照挂载（fixture 的 clone_from_readonly_snapshot 模式）。
- **资源事实**：PID/CPU/memory+swap（`--memory-swap == --memory` ⇒ 无 swap）/ tmpfs 容量；
  容器可写层总预算 `--storage-opt size=` 只有 overlay2-on-xfs(pquota) 的守护进程真的强制
  ——本机 Docker Desktop 接受该参数但不强制（实测写 100MB 超 64M 配额成功），所以探针用
  `fallocate` 超额分配**实测**强制与否并记录；`require_writable_layer_quota=True` 时未强制
  即失败（GPU 主机由 C 决定是否要求）。

验证/dry-run 模式（供 W7 远端调用，同一入口不复制第二套规则）：
`python -m repoharness2.adapters.slime.sandbox_profile verify --image <镜像> --upstream-host <H>
--upstream-port <P> --out <目录>`；bringup 启动时调用同一个 `verify_sandbox_profiles()`。
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import shlex
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Sequence

__all__ = [
    "GRADER_PROFILE_ID",
    "PROFILE_SCHEMA_ID",
    "ROLLOUT_PROFILE_ID",
    "RUNTIME_PROFILE_DIGEST_METADATA_KEY",
    "RUNTIME_PROFILE_RECORD_SCHEMA_ID",
    "SCRIPT_MARKER_PREFIX",
    "TRUSTED_INIT_CAPS",
    "AttemptNetwork",
    "EgressRelayHandle",
    "EgressRelayUnavailable",
    "EgressSubnetPool",
    "GraderSandboxProfile",
    "InternalService",
    "PrelaunchReport",
    "RolloutSandboxProfile",
    "SandboxNetworkError",
    "SandboxProfileError",
    "check_grader_inspect",
    "check_grader_probe",
    "check_rollout_inspect",
    "check_rollout_probe",
    "connect_relay_to_network",
    "create_attempt_network",
    "default_docker_runner",
    "git_sanitize_script",
    "grader_chown_before_eval_script",
    "grader_prelaunch_probe_script",
    "grader_profile_from_env",
    "grader_trusted_init_script",
    "list_probe_scripts",
    "main",
    "parse_key_value_output",
    "rollout_extended_probe_script",
    "rollout_prelaunch_probe_script",
    "rollout_profile_from_env",
    "rollout_trusted_init_script",
    "run_grader_prelaunch_check",
    "run_labels_from_env",
    "run_rollout_prelaunch_check",
    "runtime_profile_digest",
    "script_id_of",
    "start_egress_relay",
    "stop_egress_relay",
    "teardown_attempt_network",
    "verify_sandbox_profiles",
    "write_runtime_profile_record",
]

PROFILE_SCHEMA_ID = "rh2.sandbox_profile.v1"
ROLLOUT_PROFILE_ID = "rh2.rollout_sandbox_profile.v1"
GRADER_PROFILE_ID = "rh2.grader_sandbox_profile.v1"
RUNTIME_PROFILE_RECORD_SCHEMA_ID = "rh2.runtime_profile_record.v1"
# 样本 metadata / execution audit 上唯一的 join 键（D2-2："样本/audit 只盖 runtime_profile_digest"）
RUNTIME_PROFILE_DIGEST_METADATA_KEY = "runtime_profile_digest"

# 只给 root 可信初始化保留的能力（容器 --cap-drop ALL 之后再 --cap-add 这几项）。非 root 进程
# 不继承任何一项（无 ambient cap；no_new_privs 下 setuid/文件能力不生效）。
TRUSTED_INIT_CAPS: tuple[str, ...] = ("CHOWN", "DAC_OVERRIDE", "DAC_READ_SEARCH", "FOWNER", "KILL")

# 容器内脚本的首行标记：测试替身按它分派罐头输出，H7 按它对照脚本清单。
SCRIPT_MARKER_PREFIX = "# rh2-sandbox-script: "

_GIB = 1024**3
_MIB = 1024**2
_RUN_LABEL_KEY = "rh2.run_id"  # 与 shutdown/run_residue.RUN_LABEL_KEY 相同（本模块不 import 它，保持零依赖）
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_CAP_RE = re.compile(r"^[A-Z_]+$")


class SandboxProfileError(RuntimeError):
    """profile 配置非法（启动期 fail-closed：正式 profile 缺必需配置 → 启动失败，不创建 rollout）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


class SandboxNetworkError(RuntimeError):
    """attempt 私有网络创建/连接失败（瞬时 Docker 故障 → 调用方按既有 task-local infra 语义收口）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


class EgressRelayUnavailable(RuntimeError):
    """本 run 的 egress relay 容器不存在/已死：不是单个 attempt 的故障（同 profile 补采不会修好），
    调用方升 run-fatal。"""

    def __init__(self, message: str) -> None:
        self.reason_code = "egress_relay_unavailable"
        super().__init__(f"[egress_relay_unavailable] {message}")


# ---------------------------------------------------------------------------
# docker 通道（零依赖：不 import grading.manager，避免 manager ↔ 本模块循环 import）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Exec:
    exit_code: int
    stdout: str
    stderr: str


DockerRunner = Callable[..., Awaitable[Any]]


async def default_docker_runner(*args: str, input_bytes: bytes | None = None) -> _Exec:
    """默认 docker CLI 通道（与 grading.manager.run_docker 同形；返回值鸭子类型兼容 ExecResult）。"""

    proc = await asyncio.create_subprocess_exec(
        "docker",
        *args,
        stdin=asyncio.subprocess.PIPE if input_bytes is not None else asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=input_bytes)
    return _Exec(proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace"))


async def _call(docker: DockerRunner, *args: str, timeout: float, input_bytes: bytes | None = None) -> Any:
    """带超时的 docker 调用；超时返回 exit_code=124 的结果（不抛，让调用方按失败语义处理）。"""

    try:
        if input_bytes is not None:
            return await asyncio.wait_for(docker(*args, input_bytes=input_bytes), timeout=timeout)
        return await asyncio.wait_for(docker(*args), timeout=timeout)
    except (TimeoutError, asyncio.TimeoutError):
        return _Exec(124, "", f"docker {' '.join(args[:3])} 超时（>{timeout}s）")


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


def run_labels_from_env(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """本 run owner label 参数（`--label rh2.run_id=<id>`）；MILES_RH2_RUN_ID 未设时为空
    （与 generate.py / grading.manager 既有 label 纪律一致）。"""

    env = os.environ if env is None else env
    run_id = env.get("MILES_RH2_RUN_ID")
    return ("--label", f"{_RUN_LABEL_KEY}={run_id}") if run_id else ()


def _sanitize_name(text: str, limit: int = 24) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "-", text).strip("-.")
    return (cleaned or "x")[:limit]


# ---------------------------------------------------------------------------
# profile 定义
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InternalService:
    """环境声明的内部服务：relay 在 `listen_port` 监听，转发到可信侧 `upstream_host:upstream_port`。
    rollout 容器内以 `http://<relay_alias>:<listen_port>` 访问。"""

    alias: str
    upstream_host: str
    upstream_port: int
    listen_port: int

    def validate(self) -> None:
        if not _NAME_RE.match(self.alias):
            raise SandboxProfileError("internal_service_alias_invalid", f"alias={self.alias!r}")
        if not self.upstream_host:
            raise SandboxProfileError("internal_service_host_empty", f"alias={self.alias}")
        for port in (self.upstream_port, self.listen_port):
            if not (1 <= int(port) <= 65535):
                raise SandboxProfileError("internal_service_port_invalid", f"alias={self.alias} port={port}")


def _check_common_limits(prefix: str, *, pids_limit: int, cpus: float, memory_bytes: int, tmp_tmpfs_bytes: int,
                         writable_layer_quota_bytes: int, caps: Sequence[str]) -> None:
    if not isinstance(pids_limit, int) or isinstance(pids_limit, bool) or pids_limit < 16:
        raise SandboxProfileError(f"{prefix}_pids_limit_invalid", f"pids_limit={pids_limit!r}（须为 ≥16 的整数）")
    if not isinstance(cpus, (int, float)) or isinstance(cpus, bool) or not (0.1 <= float(cpus) <= 1024):
        raise SandboxProfileError(f"{prefix}_cpus_invalid", f"cpus={cpus!r}")
    if not isinstance(memory_bytes, int) or isinstance(memory_bytes, bool) or memory_bytes < 64 * _MIB:
        raise SandboxProfileError(f"{prefix}_memory_invalid", f"memory_bytes={memory_bytes!r}（≥64MiB）")
    if not isinstance(tmp_tmpfs_bytes, int) or isinstance(tmp_tmpfs_bytes, bool) or tmp_tmpfs_bytes < _MIB:
        raise SandboxProfileError(f"{prefix}_tmp_tmpfs_invalid", f"tmp_tmpfs_bytes={tmp_tmpfs_bytes!r}")
    if not isinstance(writable_layer_quota_bytes, int) or isinstance(writable_layer_quota_bytes, bool) \
            or writable_layer_quota_bytes < 64 * _MIB:
        raise SandboxProfileError(f"{prefix}_writable_layer_quota_invalid", f"{writable_layer_quota_bytes!r}")
    for cap in caps:
        if not _CAP_RE.match(cap) or cap == "ALL" or cap.startswith("CAP_"):
            raise SandboxProfileError(f"{prefix}_trusted_init_cap_invalid", f"cap={cap!r}（大写名，不带 CAP_ 前缀）")
    if len(set(caps)) != len(caps):
        raise SandboxProfileError(f"{prefix}_trusted_init_caps_duplicate", f"{list(caps)}")


def _check_user(prefix: str, user: str, uid: int) -> None:
    if not _NAME_RE.match(user) or user == "root":
        raise SandboxProfileError(f"{prefix}_user_invalid", f"user={user!r}")
    if not isinstance(uid, int) or isinstance(uid, bool) or not (1000 <= uid <= 60000):
        raise SandboxProfileError(f"{prefix}_uid_invalid", f"uid={uid!r}（须在 1000..60000，且非 0）")


def _limit_args(*, pids_limit: int, cpus: float, memory_bytes: int) -> list[str]:
    return [
        "--pids-limit", str(pids_limit),
        "--cpus", f"{float(cpus):g}",
        "--memory", str(memory_bytes),
        "--memory-swap", str(memory_bytes),  # == memory ⇒ 禁 swap（cgroup v2 memory.swap.max=0）
    ]


@dataclass(frozen=True)
class RolloutSandboxProfile:
    """唯一正式 rollout Docker profile（参数即事实；没有可选安全开关）。

    数值参数（本地默认值，真实数值归 C 校准，实际值进 run 记录）：pids_limit / cpus /
    memory_bytes（swap 恒禁）/ tmp_tmpfs_bytes（/tmp）/ home_tmpfs_bytes（/home/<agent>）/
    writable_layer_quota_bytes（容器可写层总预算，`require_writable_layer_quota` 决定守护进程
    不强制时是否失败）。部署参数：model_proxy_upstream_*（relay 上游 = 宿主侧 adapter）、
    relay_image、internal_services、egress_subnet_pool。
    """

    model_proxy_upstream_host: str
    model_proxy_upstream_port: int
    agent_user: str = "agent"
    agent_uid: int = 54321
    trusted_init_caps: tuple[str, ...] = TRUSTED_INIT_CAPS
    pids_limit: int = 512
    cpus: float = 2.0
    memory_bytes: int = 4 * _GIB
    tmp_tmpfs_bytes: int = 1 * _GIB
    home_tmpfs_bytes: int = 256 * _MIB
    writable_layer_quota_bytes: int = 8 * _GIB
    require_writable_layer_quota: bool = False
    egress_subnet_pool: str = "10.212.0.0/16"
    egress_subnet_prefix: int = 29
    relay_image: str = "python:3.12-slim"
    relay_alias: str = "rh2-egress-relay"
    model_proxy_listen_port: int = 18001
    internal_services: tuple[InternalService, ...] = ()
    hidden_paths: tuple[str, ...] = ("/root",)
    forbidden_probe_targets: tuple[tuple[str, int], ...] = (
        ("169.254.169.254", 80),  # 云 metadata
        ("1.1.1.1", 443),  # 公网
        ("8.8.8.8", 53),  # 公网 DNS
        ("172.17.0.1", 18001),  # docker0 网关（宿主服务）
    )
    workdir: str = "/testbed"
    init_timeout_seconds: float = 900.0  # useradd + chown -R（django 官方镜像数万文件）
    sanitize_timeout_seconds: float = 600.0  # git repack/prune
    probe_timeout_seconds: float = 120.0

    profile_id: str = ROLLOUT_PROFILE_ID

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.profile_id != ROLLOUT_PROFILE_ID:
            raise SandboxProfileError("rollout_profile_id_invalid", f"{self.profile_id!r}")
        _check_user("rollout", self.agent_user, self.agent_uid)
        _check_common_limits(
            "rollout", pids_limit=self.pids_limit, cpus=self.cpus, memory_bytes=self.memory_bytes,
            tmp_tmpfs_bytes=self.tmp_tmpfs_bytes, writable_layer_quota_bytes=self.writable_layer_quota_bytes,
            caps=self.trusted_init_caps,
        )
        if not isinstance(self.home_tmpfs_bytes, int) or isinstance(self.home_tmpfs_bytes, bool) \
                or self.home_tmpfs_bytes < _MIB:
            raise SandboxProfileError("rollout_home_tmpfs_invalid", f"{self.home_tmpfs_bytes!r}")
        if not self.model_proxy_upstream_host:
            raise SandboxProfileError("rollout_model_proxy_upstream_host_empty", "模型代理上游地址不能为空")
        for port in (self.model_proxy_upstream_port, self.model_proxy_listen_port):
            if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= 65535):
                raise SandboxProfileError("rollout_model_proxy_port_invalid", f"port={port!r}")
        try:
            pool = ipaddress.ip_network(self.egress_subnet_pool, strict=True)
        except ValueError as exc:
            raise SandboxProfileError("rollout_egress_subnet_pool_invalid", str(exc)) from exc
        if not (pool.prefixlen < self.egress_subnet_prefix <= 30):
            raise SandboxProfileError(
                "rollout_egress_subnet_prefix_invalid",
                f"prefix={self.egress_subnet_prefix} 须大于 pool 前缀 {pool.prefixlen} 且 ≤30",
            )
        if not self.relay_image or not _NAME_RE.match(self.relay_alias):
            raise SandboxProfileError("rollout_relay_config_invalid", f"image={self.relay_image!r} alias={self.relay_alias!r}")
        listen_ports = {self.model_proxy_listen_port}
        for svc in self.internal_services:
            svc.validate()
            if svc.listen_port in listen_ports:
                raise SandboxProfileError("internal_service_listen_port_conflict", f"listen_port={svc.listen_port}")
            listen_ports.add(svc.listen_port)
        for path in self.hidden_paths:
            if not path.startswith("/"):
                raise SandboxProfileError("rollout_hidden_path_invalid", f"{path!r}")
        if not self.workdir.startswith("/"):
            raise SandboxProfileError("rollout_workdir_invalid", f"{self.workdir!r}")

    # -- 参数摘要 ----------------------------------------------------------------
    def to_parameters(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "schema_id": PROFILE_SCHEMA_ID,
            "agent_user": self.agent_user,
            "agent_uid": self.agent_uid,
            "trusted_init_caps": list(self.trusted_init_caps),
            "pids_limit": self.pids_limit,
            "cpus": float(self.cpus),
            "memory_bytes": self.memory_bytes,
            "swap_bytes": 0,
            "tmp_tmpfs_bytes": self.tmp_tmpfs_bytes,
            "home_tmpfs_bytes": self.home_tmpfs_bytes,
            "writable_layer_quota_bytes": self.writable_layer_quota_bytes,
            "require_writable_layer_quota": self.require_writable_layer_quota,
            "network": {
                "mode": "isolated_internal_network_per_attempt",
                "egress_subnet_pool": self.egress_subnet_pool,
                "egress_subnet_prefix": self.egress_subnet_prefix,
                "relay_image": self.relay_image,
                "relay_alias": self.relay_alias,
                "model_proxy_listen_port": self.model_proxy_listen_port,
                "model_proxy_upstream": f"{self.model_proxy_upstream_host}:{self.model_proxy_upstream_port}",
                "internal_services": [
                    {"alias": s.alias, "listen_port": s.listen_port, "upstream": f"{s.upstream_host}:{s.upstream_port}"}
                    for s in self.internal_services
                ],
                "forbidden_probe_targets": [f"{h}:{p}" for h, p in self.forbidden_probe_targets],
            },
            "hidden_paths": list(self.hidden_paths),
            "bind_mounts_allowed": [],
            "workdir": self.workdir,
            "security_opt": ["no-new-privileges"],
            "cap_drop": ["ALL"],
        }

    def digest(self) -> str:
        return _sha256(self.to_parameters())

    def harness_adapter_url(self) -> str:
        """harness 进程看到的模型代理地址（经 relay 别名，每个 attempt 网络都以同名别名接入）。"""

        return f"http://{self.relay_alias}:{self.model_proxy_listen_port}"

    def relay_listen_map(self) -> tuple[tuple[int, str, int], ...]:
        entries = [(self.model_proxy_listen_port, self.model_proxy_upstream_host, self.model_proxy_upstream_port)]
        entries += [(s.listen_port, s.upstream_host, s.upstream_port) for s in self.internal_services]
        return tuple(entries)

    def expected_tmpfs(self) -> dict[str, str]:
        return {
            "/tmp": f"size={self.tmp_tmpfs_bytes},mode=1777",
            f"/home/{self.agent_user}": f"size={self.home_tmpfs_bytes},mode=0750,uid={self.agent_uid},gid={self.agent_uid}",
        }

    def docker_run_args(self, *, name: str, network: str, image: str, labels: Sequence[str] = ()) -> list[str]:
        """完整 `docker run` 参数（含首个 "run"）。固定 `sleep infinity` 主进程。"""

        args: list[str] = ["run", "--detach", "--network", network, "--cap-drop", "ALL"]
        for cap in self.trusted_init_caps:
            args += ["--cap-add", cap]
        args += ["--security-opt", "no-new-privileges"]
        args += _limit_args(pids_limit=self.pids_limit, cpus=self.cpus, memory_bytes=self.memory_bytes)
        for path, opts in self.expected_tmpfs().items():
            args += ["--tmpfs", f"{path}:{opts}"]
        if self.require_writable_layer_quota:
            args += ["--storage-opt", f"size={self.writable_layer_quota_bytes}"]
        args += list(labels)
        args += ["--name", name, image, "sleep", "infinity"]
        return args


@dataclass(frozen=True)
class GraderSandboxProfile:
    """独立 grader Docker profile：全断网（deny_all）、执行候选代码的进程非 root、同受资源限制。

    与 rollout 绝不复用同一活动容器（每次评分 fresh 容器，W3a）；不继承 agent 状态（只从持久化
    frozen artifact 重放）。候选代码（官方 eval 脚本 + 候选 patch 上的测试）以 `candidate_exec_user`
    执行；可信步骤（clean checkout / baseline 重建 / delta 应用 / 写 eval 脚本）仍由 root 经宿主
    `docker exec` 执行——容器本身 `--cap-drop ALL` 只保留 TRUSTED_INIT_CAPS。
    """

    candidate_exec_user: str = "rh2grader"
    candidate_exec_uid: int = 54322
    trusted_init_caps: tuple[str, ...] = TRUSTED_INIT_CAPS
    pids_limit: int = 512
    cpus: float = 2.0
    memory_bytes: int = 4 * _GIB
    tmp_tmpfs_bytes: int = 1 * _GIB
    writable_layer_quota_bytes: int = 8 * _GIB
    require_writable_layer_quota: bool = False
    testbed_path: str = "/testbed"
    forbidden_probe_targets: tuple[tuple[str, int], ...] = (
        ("169.254.169.254", 80),
        ("1.1.1.1", 443),
        ("172.17.0.1", 18001),
    )
    init_timeout_seconds: float = 300.0
    probe_timeout_seconds: float = 120.0

    profile_id: str = GRADER_PROFILE_ID

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.profile_id != GRADER_PROFILE_ID:
            raise SandboxProfileError("grader_profile_id_invalid", f"{self.profile_id!r}")
        _check_user("grader", self.candidate_exec_user, self.candidate_exec_uid)
        _check_common_limits(
            "grader", pids_limit=self.pids_limit, cpus=self.cpus, memory_bytes=self.memory_bytes,
            tmp_tmpfs_bytes=self.tmp_tmpfs_bytes, writable_layer_quota_bytes=self.writable_layer_quota_bytes,
            caps=self.trusted_init_caps,
        )
        if self.testbed_path != "/testbed":
            raise SandboxProfileError("grader_testbed_path_invalid", f"{self.testbed_path!r}（探针固定 /testbed）")

    def to_parameters(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "schema_id": PROFILE_SCHEMA_ID,
            "candidate_exec_user": self.candidate_exec_user,
            "candidate_exec_uid": self.candidate_exec_uid,
            "trusted_init_caps": list(self.trusted_init_caps),
            "pids_limit": self.pids_limit,
            "cpus": float(self.cpus),
            "memory_bytes": self.memory_bytes,
            "swap_bytes": 0,
            "tmp_tmpfs_bytes": self.tmp_tmpfs_bytes,
            "writable_layer_quota_bytes": self.writable_layer_quota_bytes,
            "require_writable_layer_quota": self.require_writable_layer_quota,
            "network": {"mode": "deny_all", "forbidden_probe_targets": [f"{h}:{p}" for h, p in self.forbidden_probe_targets]},
            "bind_mounts_allowed": ["declared_readonly_snapshot_only"],
            "testbed_path": self.testbed_path,
            "security_opt": ["no-new-privileges"],
            "cap_drop": ["ALL"],
        }

    def digest(self) -> str:
        return _sha256(self.to_parameters())

    def expected_tmpfs(self) -> dict[str, str]:
        return {"/tmp": f"size={self.tmp_tmpfs_bytes},mode=1777"}

    def docker_run_args(
        self, *, name: str, image: str, labels: Sequence[str] = (),
        declared_readonly_binds: Sequence[tuple[str, str]] = (),
    ) -> list[str]:
        args: list[str] = ["run", "--detach", "--network", "none", "--cap-drop", "ALL"]
        for cap in self.trusted_init_caps:
            args += ["--cap-add", cap]
        args += ["--security-opt", "no-new-privileges"]
        args += _limit_args(pids_limit=self.pids_limit, cpus=self.cpus, memory_bytes=self.memory_bytes)
        for path, opts in self.expected_tmpfs().items():
            args += ["--tmpfs", f"{path}:{opts}"]
        if self.require_writable_layer_quota:
            args += ["--storage-opt", f"size={self.writable_layer_quota_bytes}"]
        args += list(labels)
        for src, dst in declared_readonly_binds:
            args += ["--volume", f"{src}:{dst}:ro"]
        args += ["--name", name, image, "sleep", "infinity"]
        return args


def runtime_profile_digest(rollout: RolloutSandboxProfile, grader: GraderSandboxProfile | None) -> str:
    """run 级 profile 参数摘要（样本 metadata / audit / run evidence 共用的唯一 join 键）。"""

    return _sha256({
        "schema_id": "rh2.runtime_profile_digest.v1",
        "rollout": rollout.to_parameters(),
        "grader": grader.to_parameters() if grader is not None else None,
    })


# ---------------------------------------------------------------------------
# 环境变量 → profile（bringup 与 verify CLI 共用同一解析；非法值启动即拒）
# ---------------------------------------------------------------------------


def _env_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw, 10)
    except ValueError as exc:
        raise SandboxProfileError("sandbox_env_not_int", f"{key}={raw!r} 不是十进制整数") from exc


def _env_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SandboxProfileError("sandbox_env_not_float", f"{key}={raw!r} 不是数值") from exc


def _env_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    if raw not in ("0", "1"):
        raise SandboxProfileError("sandbox_env_not_bool", f"{key}={raw!r} 只认 0/1")
    return raw == "1"


def _env_services(env: Mapping[str, str], key: str) -> tuple[InternalService, ...]:
    raw = env.get(key)
    if not raw:
        return ()
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SandboxProfileError("sandbox_env_services_not_json", f"{key} 不是 JSON：{exc}") from exc
    if not isinstance(entries, list):
        raise SandboxProfileError("sandbox_env_services_not_list", f"{key} 须为 JSON 数组")
    out = []
    for entry in entries:
        try:
            out.append(InternalService(
                alias=str(entry["alias"]), upstream_host=str(entry["upstream_host"]),
                upstream_port=int(entry["upstream_port"]), listen_port=int(entry["listen_port"]),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise SandboxProfileError("sandbox_env_service_entry_invalid", f"{entry!r}: {exc}") from exc
    return tuple(out)


def rollout_profile_from_env(
    env: Mapping[str, str], *, model_proxy_upstream_host: str, model_proxy_upstream_port: int,
) -> RolloutSandboxProfile:
    """`RH2_SANDBOX_*` 环境变量 → 正式 rollout profile（缺省 = 本地默认值；非法即抛）。"""

    return RolloutSandboxProfile(
        model_proxy_upstream_host=model_proxy_upstream_host,
        model_proxy_upstream_port=int(model_proxy_upstream_port),
        agent_user=env.get("RH2_SANDBOX_AGENT_USER") or "agent",
        agent_uid=_env_int(env, "RH2_SANDBOX_AGENT_UID", 54321),
        pids_limit=_env_int(env, "RH2_SANDBOX_PIDS_LIMIT", 512),
        cpus=_env_float(env, "RH2_SANDBOX_CPUS", 2.0),
        memory_bytes=_env_int(env, "RH2_SANDBOX_MEMORY_BYTES", 4 * _GIB),
        tmp_tmpfs_bytes=_env_int(env, "RH2_SANDBOX_TMP_TMPFS_BYTES", 1 * _GIB),
        home_tmpfs_bytes=_env_int(env, "RH2_SANDBOX_HOME_TMPFS_BYTES", 256 * _MIB),
        writable_layer_quota_bytes=_env_int(env, "RH2_SANDBOX_WRITABLE_LAYER_QUOTA_BYTES", 8 * _GIB),
        require_writable_layer_quota=_env_bool(env, "RH2_SANDBOX_REQUIRE_WRITABLE_LAYER_QUOTA", False),
        egress_subnet_pool=env.get("RH2_SANDBOX_EGRESS_SUBNET_POOL") or "10.212.0.0/16",
        egress_subnet_prefix=_env_int(env, "RH2_SANDBOX_EGRESS_SUBNET_PREFIX", 29),
        relay_image=env.get("RH2_SANDBOX_RELAY_IMAGE") or "python:3.12-slim",
        model_proxy_listen_port=_env_int(env, "RH2_SANDBOX_RELAY_PORT", 18001),
        internal_services=_env_services(env, "RH2_SANDBOX_INTERNAL_SERVICES"),
    )


def grader_profile_from_env(env: Mapping[str, str]) -> GraderSandboxProfile:
    """`RH2_GRADER_*` 环境变量 → 独立 grader profile。"""

    return GraderSandboxProfile(
        candidate_exec_user=env.get("RH2_GRADER_USER") or "rh2grader",
        candidate_exec_uid=_env_int(env, "RH2_GRADER_UID", 54322),
        pids_limit=_env_int(env, "RH2_GRADER_PIDS_LIMIT", 512),
        cpus=_env_float(env, "RH2_GRADER_CPUS", 2.0),
        memory_bytes=_env_int(env, "RH2_GRADER_MEMORY_BYTES", 4 * _GIB),
        tmp_tmpfs_bytes=_env_int(env, "RH2_GRADER_TMP_TMPFS_BYTES", 1 * _GIB),
        writable_layer_quota_bytes=_env_int(env, "RH2_GRADER_WRITABLE_LAYER_QUOTA_BYTES", 8 * _GIB),
        require_writable_layer_quota=_env_bool(env, "RH2_GRADER_REQUIRE_WRITABLE_LAYER_QUOTA", False),
    )


# ---------------------------------------------------------------------------
# attempt 私有网络（isolated internal）+ 本 run egress relay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AttemptNetwork:
    name: str
    subnet: str


@dataclass(frozen=True)
class EgressRelayHandle:
    """本 run 的 egress relay 容器（一 run 一份；每个 attempt 网络以 `alias` 别名接入它）。"""

    container_name: str
    alias: str
    listen_map: tuple[tuple[int, str, int], ...]
    image: str
    run_id: str


class EgressSubnetPool:
    """按 profile 的地址池切 /prefix 子网，round-robin 分配；docker 报 "Pool overlaps" 的槽位记为占用
    （其他 run / 残留网络在用），换下一槽。不依赖守护进程的 default-address-pools（其默认只够
    ~30 张网络，实测第 27 张即耗尽）。"""

    def __init__(self, pool_cidr: str, prefix: int) -> None:
        network = ipaddress.ip_network(pool_cidr, strict=True)
        self._subnets = list(network.subnets(new_prefix=prefix))
        self._cursor = 0
        self._in_use: set[str] = set()

    @property
    def capacity(self) -> int:
        return len(self._subnets)

    def allocate(self) -> str:
        for _ in range(len(self._subnets)):
            candidate = str(self._subnets[self._cursor % len(self._subnets)])
            self._cursor += 1
            if candidate not in self._in_use:
                self._in_use.add(candidate)
                return candidate
        raise SandboxNetworkError("egress_subnet_pool_exhausted", f"{len(self._subnets)} 个子网全部占用")

    def mark_foreign(self, subnet: str) -> None:
        self._in_use.add(subnet)

    def release(self, subnet: str) -> None:
        self._in_use.discard(subnet)


async def create_attempt_network(
    docker: DockerRunner, *, profile: RolloutSandboxProfile, pool: EgressSubnetPool, name: str,
    labels: Sequence[str] = (), max_slots: int = 64, timeout: float = 60.0,
) -> AttemptNetwork:
    """创建本 attempt 的 isolated internal 网络（显式 /prefix 子网）。子网重叠 → 换槽重试；其余失败 →
    SandboxNetworkError（task-local）。"""

    last_error = ""
    for _ in range(max_slots):
        subnet = pool.allocate()
        res = await _call(
            docker, "network", "create", "--internal",
            "-o", "com.docker.network.bridge.gateway_mode_ipv4=isolated",
            "--subnet", subnet, "--label", "rh2.egress.attempt=1", *labels, name,
            timeout=timeout,
        )
        if res.exit_code == 0:
            return AttemptNetwork(name=name, subnet=subnet)
        last_error = (res.stderr or res.stdout).strip()[-300:]
        pool.release(subnet)
        if "overlap" in last_error.lower():
            pool.mark_foreign(subnet)
            continue
        break
    raise SandboxNetworkError("egress_network_create_failed", f"{name}: {last_error}")


async def connect_relay_to_network(
    docker: DockerRunner, *, relay: EgressRelayHandle, network: AttemptNetwork, timeout: float = 60.0,
) -> None:
    res = await _call(
        docker, "network", "connect", "--alias", relay.alias, network.name, relay.container_name, timeout=timeout,
    )
    if res.exit_code != 0:
        err = (res.stderr or res.stdout).strip()[-300:]
        if "no such container" in err.lower() or "is not running" in err.lower():
            raise EgressRelayUnavailable(f"{relay.container_name}: {err}")
        raise SandboxNetworkError("egress_relay_connect_failed", f"{network.name}: {err}")


async def teardown_attempt_network(
    docker: DockerRunner, *, network_name: str, relay: EgressRelayHandle | None, pool: EgressSubnetPool | None = None,
    subnet: str | None = None, timeout: float = 60.0,
) -> list[str]:
    """断开 relay 并删除 attempt 网络；返回失败描述列表（空 = 成功）。容器必须已移除。"""

    failures: list[str] = []
    if relay is not None:
        res = await _call(docker, "network", "disconnect", network_name, relay.container_name, timeout=timeout)
        if res.exit_code != 0:
            err = (res.stderr or res.stdout).strip()[-200:]
            if "is not connected" not in err and "no such" not in err.lower():
                failures.append(f"relay_disconnect:{err}")
    res = await _call(docker, "network", "rm", network_name, timeout=timeout)
    if res.exit_code != 0:
        err = (res.stderr or res.stdout).strip()[-200:]
        if "no such network" not in err.lower() and "not found" not in err.lower():
            failures.append(f"network_rm:{err}")
    if pool is not None and subnet is not None and not failures:
        pool.release(subnet)
    return failures


# relay 转发器：纯 stdlib asyncio TCP 转发，只转发到固定 (listen_port → upstream) 映射。
_RELAY_SCRIPT = r'''
import asyncio, os, sys
MAP = {}
for entry in os.environ["RH2_RELAY_MAP"].split(","):
    port, host, upstream = entry.split(":")
    MAP[int(port)] = (host, int(upstream))
async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass
async def handle(reader, writer, target):
    try:
        ur, uw = await asyncio.wait_for(asyncio.open_connection(target[0], target[1]), timeout=15)
    except Exception:
        writer.close()
        return
    await asyncio.gather(pipe(reader, uw), pipe(ur, writer))
async def main():
    servers = []
    for port, target in MAP.items():
        servers.append(await asyncio.start_server(lambda r, w, t=target: handle(r, w, t), host="0.0.0.0", port=port))
    print("RH2_RELAY_READY", flush=True)
    await asyncio.gather(*(s.serve_forever() for s in servers))
asyncio.run(main())
'''


def relay_run_args(profile: RolloutSandboxProfile, *, name: str, labels: Sequence[str] = ()) -> list[str]:
    """relay 容器参数：默认 bridge（能到宿主侧 adapter）、非 root、无能力、只读根、限额。"""

    relay_map = ",".join(f"{lp}:{host}:{up}" for lp, host, up in profile.relay_listen_map())
    return [
        "run", "--detach", "--network", "bridge", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--read-only", "--user", "65534:65534", "--pids-limit", "64", "--memory", str(256 * _MIB),
        "--memory-swap", str(256 * _MIB), "--tmpfs", "/tmp:size=16777216,mode=1777",
        "--env", f"RH2_RELAY_MAP={relay_map}", "--label", "rh2.egress.relay=1", *labels,
        "--name", name, profile.relay_image, "python3", "-c", _RELAY_SCRIPT,
    ]


async def start_egress_relay(
    docker: DockerRunner, profile: RolloutSandboxProfile, *, run_id: str, labels: Sequence[str] = (),
    ready_timeout: float = 30.0,
) -> EgressRelayHandle:
    """启动本 run 的 egress relay 并等它就绪（容器内 127.0.0.1:<listen_port> 可连）。失败 → SandboxNetworkError。"""

    name = f"rh2-egress-relay-{_sanitize_name(run_id, 40)}"
    res = await _call(docker, *relay_run_args(profile, name=name, labels=labels), timeout=120.0)
    if res.exit_code != 0:
        raise SandboxNetworkError("egress_relay_start_failed", (res.stderr or res.stdout).strip()[-300:])
    handle = EgressRelayHandle(
        container_name=name, alias=profile.relay_alias, listen_map=profile.relay_listen_map(),
        image=profile.relay_image, run_id=run_id,
    )
    deadline = time.monotonic() + ready_timeout
    check = (
        "import socket,sys\n"
        f"s=socket.create_connection(('127.0.0.1',{profile.model_proxy_listen_port}),timeout=2)\n"
        "s.close()\nprint('RH2_RELAY_LISTENING')\n"
    )
    while True:
        probe = await _call(docker, "exec", name, "python3", "-c", check, timeout=15.0)
        if probe.exit_code == 0 and "RH2_RELAY_LISTENING" in probe.stdout:
            return handle
        if time.monotonic() > deadline:
            await _call(docker, "rm", "-f", name, timeout=60.0)
            raise SandboxNetworkError(
                "egress_relay_not_ready", f"{name} 在 {ready_timeout}s 内未监听：{(probe.stderr or probe.stdout)[-200:]}"
            )
        await asyncio.sleep(0.25)


async def stop_egress_relay(docker: DockerRunner, relay: EgressRelayHandle, *, timeout: float = 60.0) -> list[str]:
    res = await _call(docker, "rm", "-f", relay.container_name, timeout=timeout)
    if res.exit_code != 0 and "no such container" not in (res.stderr or "").lower():
        return [f"relay_rm:{(res.stderr or res.stdout).strip()[-200:]}"]
    return []


async def list_labeled_networks(docker: DockerRunner, *, label: str, timeout: float = 30.0) -> list[str] | None:
    res = await _call(docker, "network", "ls", "--filter", f"label={label}", "--format", "{{.Name}}", timeout=timeout)
    if res.exit_code != 0:
        return None
    return sorted(line.strip() for line in res.stdout.splitlines() if line.strip())


# ---------------------------------------------------------------------------
# 容器内脚本（首行标记 = 脚本身份；H7 复跑同一组脚本）
# ---------------------------------------------------------------------------


def _marker(script_id: str) -> str:
    return f"{SCRIPT_MARKER_PREFIX}{script_id} v1\n"


def script_id_of(script: str) -> str | None:
    """从脚本文本取首行标记的脚本 id（测试替身 / H7 清单用）。"""

    first = script.lstrip().split("\n", 1)[0]
    if first.startswith(SCRIPT_MARKER_PREFIX):
        return first[len(SCRIPT_MARKER_PREFIX):].split(" ", 1)[0]
    return None


_USER_INIT_BODY = r'''
U=__USER__; UIDV=__UID__
if ! id -u "$U" >/dev/null 2>&1; then
  if command -v useradd >/dev/null 2>&1; then
    getent group "$UIDV" >/dev/null 2>&1 || groupadd -g "$UIDV" "$U"
    useradd -M -u "$UIDV" -g "$UIDV" -s /bin/bash -d "/home/$U" "$U"
  else
    echo "$U:x:$UIDV:$UIDV::/home/$U:/bin/bash" >> /etc/passwd
    echo "$U:x:$UIDV:" >> /etc/group
  fi
fi
ACT=$(id -u "$U")
if [ "$ACT" != "$UIDV" ]; then echo "RH2_INIT_ERROR=uid_mismatch:$ACT"; exit 3; fi
mkdir -p "/home/$U"
git config --system --add safe.directory '*' >/dev/null 2>&1 || true
'''


def rollout_trusted_init_script(profile: RolloutSandboxProfile) -> str:
    """root 可信初始化：按固定 uid 预建 agent 用户、safe.directory、chown -R /home/<agent> 与 workdir。
    幂等（slime ensure_agent_user 之后再跑是 no-op）。"""

    body = _USER_INIT_BODY.replace("__USER__", shlex.quote(profile.agent_user)).replace("__UID__", str(profile.agent_uid))
    wd = shlex.quote(profile.workdir)
    return (
        _marker("rollout-trusted-init") + "set -u\n" + body
        + f"chown -R {profile.agent_uid}:{profile.agent_uid} /home/{shlex.quote(profile.agent_user)} "
        "|| { echo \"RH2_INIT_ERROR=chown_home_failed\"; exit 4; }\n"
        f"if [ -d {wd} ]; then chown -R {profile.agent_uid}:{profile.agent_uid} {wd} "
        "|| { echo \"RH2_INIT_ERROR=chown_workdir_failed\"; exit 4; }; echo \"WORKDIR_PRESENT=1\"; "
        "else echo \"WORKDIR_PRESENT=0\"; fi\n"
        "echo \"RH2_INIT_OK=1\"; echo \"AGENT_UID=$ACT\"\n"
    )


def git_sanitize_script(workdir: str) -> str:
    """solution-bearing Git 状态清除（root）：删远端、删非 HEAD 祖先的 ref、删 reflog、repack+prune 处理
    dangling 未来对象、fsck 证零。输出 KEY=VALUE。"""

    return _marker("git-sanitize") + r'''set -u
cd __WORKDIR__ 2>/dev/null || { echo "RH2_GIT_SANITIZE_ERROR=no_workdir"; exit 2; }
git config --global --add safe.directory '*' >/dev/null 2>&1 || true
HEAD_BEFORE=$(git rev-parse HEAD 2>/dev/null) || { echo "RH2_GIT_SANITIZE_ERROR=no_head"; exit 2; }
COUNT_BEFORE=$(git rev-list --count HEAD)
T0=${EPOCHREALTIME:-$SECONDS}
for r in $(git remote); do git remote remove "$r" >/dev/null 2>&1 || true; done
DELETED=0
for ref in $(git for-each-ref --format='%(refname)'); do
  sha=$(git rev-parse --verify -q "$ref^{commit}" 2>/dev/null || true)
  if [ -z "$sha" ] || ! git merge-base --is-ancestor "$sha" "$HEAD_BEFORE" 2>/dev/null; then
    git update-ref -d "$ref" >/dev/null 2>&1 || git update-ref --no-deref -d "$ref" >/dev/null 2>&1 || true
    DELETED=$((DELETED+1))
  fi
done
rm -rf .git/logs .git/refs/remotes .git/lost-found .git/FETCH_HEAD .git/ORIG_HEAD .git/MERGE_HEAD .git/CHERRY_PICK_HEAD .git/REVERT_HEAD 2>/dev/null
git reflog expire --expire=now --expire-unreachable=now --all >/dev/null 2>&1 || true
git repack -a -d -q 2>/dev/null || { echo "RH2_GIT_SANITIZE_ERROR=repack_failed"; exit 2; }
git prune --expire=now 2>/dev/null || { echo "RH2_GIT_SANITIZE_ERROR=prune_failed"; exit 2; }
git worktree prune >/dev/null 2>&1 || true
UNREACHABLE=$(git fsck --unreachable --no-reflogs --connectivity-only 2>/dev/null | grep -c '^unreachable ' || true)
HEAD_AFTER=$(git rev-parse HEAD)
COUNT_AFTER=$(git rev-list --count HEAD)
T1=${EPOCHREALTIME:-$SECONDS}
echo "RH2_GIT_SANITIZE_OK=1"
echo "HEAD_BEFORE=$HEAD_BEFORE"
echo "HEAD_AFTER=$HEAD_AFTER"
echo "HISTORY_COUNT_BEFORE=$COUNT_BEFORE"
echo "HISTORY_COUNT_AFTER=$COUNT_AFTER"
echo "REFS_DELETED=$DELETED"
echo "REFS_REMAINING=$(git for-each-ref | wc -l | tr -d ' ')"
echo "REMOTES=$(git remote | wc -l | tr -d ' ')"
echo "REFLOG_ENTRIES=$(git reflog 2>/dev/null | wc -l | tr -d ' ')"
echo "UNREACHABLE_OBJECTS=${UNREACHABLE:-0}"
echo "SECONDS_ELAPSED=$(awk "BEGIN{print $T1-$T0}")"
'''.replace("__WORKDIR__", shlex.quote(workdir))


_PROBE_COMMON = r'''
echo "UID=$(id -u)"; echo "GID=$(id -g)"
awk '/^CapEff/{print "CAPEFF="$2} /^CapPrm/{print "CAPPRM="$2} /^CapBnd/{print "CAPBND="$2} /^NoNewPrivs/{print "NNP="$2}' /proc/self/status
if [ -f /sys/fs/cgroup/pids.max ]; then
  echo "CG_VERSION=v2"
  echo "CG_PIDS_MAX=$(cat /sys/fs/cgroup/pids.max 2>/dev/null || echo unreadable)"
  echo "CG_MEMORY_MAX=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unreadable)"
  echo "CG_SWAP_MAX=$(cat /sys/fs/cgroup/memory.swap.max 2>/dev/null || echo unreadable)"
  echo "CG_CPU_MAX=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo unreadable)"
else
  echo "CG_VERSION=v1"
  echo "CG_PIDS_MAX=$(cat /sys/fs/cgroup/pids/pids.max 2>/dev/null || echo unreadable)"
  echo "CG_MEMORY_MAX=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo unreadable)"
  MEMSW=$(cat /sys/fs/cgroup/memory/memory.memsw.limit_in_bytes 2>/dev/null || echo unreadable)
  MEM=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo unreadable)
  if [ "$MEMSW" = "$MEM" ]; then echo "CG_SWAP_MAX=0"; else echo "CG_SWAP_MAX=$MEMSW"; fi
  echo "CG_CPU_MAX=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us 2>/dev/null || echo unreadable) $(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us 2>/dev/null || echo unreadable)"
fi
echo "IFACES=$(ls /sys/class/net 2>/dev/null | sort | tr '\n' ',')"
echo "ROUTED_IFACES=$(awk 'NR>1{print $1}' /proc/net/route 2>/dev/null | sort -u | tr '\n' ',')"
probe() { if timeout 3 bash -c "exec 3<>/dev/tcp/$2/$3" 2>/dev/null; then echo "NET_$1=CONNECTED"; else echo "NET_$1=DENIED"; fi; }
if getent hosts example.com >/dev/null 2>&1; then echo "DNS_EXTERNAL=RESOLVED"; else echo "DNS_EXTERNAL=DENIED"; fi
echo "HOME_WRITABLE=$( [ -n "${HOME:-}" ] && [ -w "$HOME" ] && echo 1 || echo 0 )"
echo "TMP_WRITABLE=$( [ -w /tmp ] && echo 1 || echo 0 )"
'''


def _forbidden_probe_lines(targets: Sequence[tuple[str, int]], extra: Sequence[tuple[str, str, int]] = ()) -> str:
    lines = []
    for i, (host, port) in enumerate(targets):
        lines.append(f"probe forbidden_{i} {shlex.quote(host)} {int(port)}")
    for tag, host, port in extra:
        lines.append(f"probe {tag} {shlex.quote(host)} {int(port)}")
    return "\n".join(lines) + "\n"


def rollout_prelaunch_probe_script(profile: RolloutSandboxProfile) -> str:
    """以 agent 身份运行的启动前探针（每个 rollout 容器一次，~150ms）。"""

    hidden = "\n".join(
        f"if ls {shlex.quote(p)} >/dev/null 2>&1 || cat {shlex.quote(p)} >/dev/null 2>&1; then "
        f"echo \"HIDDEN_{i}=READABLE:{p}\"; else echo \"HIDDEN_{i}=DENIED:{p}\"; fi"
        for i, p in enumerate(profile.hidden_paths)
    )
    return (
        _marker("rollout-prelaunch-probe") + "set -u\n" + _PROBE_COMMON
        + f"probe relay {profile.relay_alias} {profile.model_proxy_listen_port}\n"
        + _forbidden_probe_lines(
            profile.forbidden_probe_targets,
            extra=(("upstream_direct", profile.model_proxy_upstream_host, profile.model_proxy_upstream_port),),
        )
        + hidden + "\n"
        + f"cd {shlex.quote(profile.workdir)} 2>/dev/null && {{ "
        "echo \"GIT_REMOTES=$(git remote 2>/dev/null | wc -l | tr -d ' ')\"; "
        "echo \"GIT_REFLOG=$(git reflog 2>/dev/null | wc -l | tr -d ' ')\"; "
        "echo \"GIT_REFS=$(git for-each-ref 2>/dev/null | wc -l | tr -d ' ')\"; "
        "echo \"GIT_HEAD=$(git rev-parse HEAD 2>/dev/null)\"; "
        "echo \"WORKDIR_WRITABLE=$( [ -w . ] && echo 1 || echo 0 )\"; "
        "echo \"WORKDIR_OWNER=$(stat -c %u . 2>/dev/null)\"; } || echo \"WORKDIR_MISSING=1\"\n"
        "echo \"RH2_PROBE_OK=1\"\n"
    )


def rollout_extended_probe_script(profile: RolloutSandboxProfile) -> str:
    """verify 模式的加长探针（agent 身份）：提权尝试必须失败；经 relay 的 HTTP 往返（上游在场时有状态行）。"""

    return (
        _marker("rollout-extended-probe") + "set -u\n"
        "if (echo x | timeout 5 su -c id root) >/dev/null 2>&1; then echo \"ESCALATE_SU=SUCCEEDED\"; else echo \"ESCALATE_SU=DENIED\"; fi\n"
        "if command -v python3 >/dev/null 2>&1; then "
        "if python3 -c 'import os; os.setuid(0)' >/dev/null 2>&1; then echo \"ESCALATE_SETUID=SUCCEEDED\"; "
        "else echo \"ESCALATE_SETUID=DENIED\"; fi; else echo \"ESCALATE_SETUID=NO_PYTHON\"; fi\n"
        "if [ -u /bin/su ] || [ -u /usr/bin/su ]; then echo \"SU_SETUID_BIT=1\"; else echo \"SU_SETUID_BIT=0\"; fi\n"
        f"STATUS=$(timeout 8 bash -c 'exec 3<>/dev/tcp/{profile.relay_alias}/{profile.model_proxy_listen_port}; "
        "printf \"GET /rh2-sandbox-probe HTTP/1.0\\r\\nHost: rh2\\r\\n\\r\\n\" >&3; head -c 64 <&3 | head -1' 2>/dev/null | tr -d '\\r')\n"
        "if [ -n \"$STATUS\" ]; then echo \"PROXY_HTTP=$STATUS\"; else echo \"PROXY_HTTP=NO_RESPONSE\"; fi\n"
        "echo \"RH2_PROBE_OK=1\"\n"
    )


def storage_quota_probe_script(quota_bytes: int) -> str:
    """root：`fallocate` 超出可写层预算 64MiB，强制时必须失败（ENOSPC）。"""

    return (
        _marker("storage-quota-probe") + "set -u\n"
        f"TARGET=$(( {int(quota_bytes)} + 67108864 ))\n"
        "if ! command -v fallocate >/dev/null 2>&1; then echo \"QUOTA_ENFORCED=UNKNOWN_NO_FALLOCATE\"; exit 0; fi\n"
        "if fallocate -l \"$TARGET\" /rh2_quota_probe.bin 2>/dev/null; then rm -f /rh2_quota_probe.bin; echo \"QUOTA_ENFORCED=0\"; "
        "else rm -f /rh2_quota_probe.bin; echo \"QUOTA_ENFORCED=1\"; fi\n"
    )


def git_future_probe_script(workdir_hint: str) -> str:
    """root：在容器内造一个带"未来解法提交"的仓库，跑同一 git-sanitize，证明未来对象不可恢复
    （cat-file / fsck --lost-found / grep 三路都找不到）且 base 之前历史保留。判定确定，H7 复跑同一脚本。"""

    sanitize = git_sanitize_script("/tmp/rh2_git_future_probe")
    sanitize_body = sanitize.split("\n", 1)[1]  # 去掉标记行，内嵌到本脚本
    return (
        _marker("git-future-probe") + "set -u\n"
        "R=/tmp/rh2_git_future_probe; rm -rf \"$R\"; mkdir -p \"$R\"; cd \"$R\"\n"
        "git init -q -b main . && git config user.email p@rh2 && git config user.name rh2\n"
        "echo base > f.py && git add . && git commit -qm base && BASE=$(git rev-parse HEAD)\n"
        "echo 'RH2_FUTURE_SOLUTION_CANARY_5c1e' > f.py && git commit -qam fix && FUT=$(git rev-parse HEAD)\n"
        "git tag v99.0 && echo more > g.py && git add . && git commit -qm later && git branch feature\n"
        "git reset -q --hard \"$BASE\"\n"
        "if git cat-file -e \"$FUT\" 2>/dev/null; then echo \"FUTURE_BEFORE=RECOVERABLE\"; else echo \"FUTURE_BEFORE=GONE\"; fi\n"
        "( cd \"$R\" && (\n" + sanitize_body + "\n) ) | sed 's/^/SANITIZE_/'\n"
        "cd \"$R\"\n"
        "if git cat-file -e \"$FUT\" 2>/dev/null; then echo \"FUTURE_CATFILE=RECOVERABLE\"; else echo \"FUTURE_CATFILE=GONE\"; fi\n"
        "LOST=$(git fsck --lost-found 2>/dev/null | grep -c dangling || true); echo \"FUTURE_LOSTFOUND=${LOST:-0}\"\n"
        "if grep -rq RH2_FUTURE_SOLUTION_CANARY_5c1e .git 2>/dev/null; then echo \"FUTURE_GREP=FOUND\"; else echo \"FUTURE_GREP=ABSENT\"; fi\n"
        "if git show v99.0 >/dev/null 2>&1; then echo \"FUTURE_TAG=RECOVERABLE\"; else echo \"FUTURE_TAG=GONE\"; fi\n"
        "if git rev-parse --verify -q feature >/dev/null 2>&1; then echo \"FUTURE_BRANCH=RECOVERABLE\"; else echo \"FUTURE_BRANCH=GONE\"; fi\n"
        "echo \"BASE_HISTORY=$(git rev-list --count HEAD)\"; echo \"HEAD_IS_BASE=$( [ \"$(git rev-parse HEAD)\" = \"$BASE\" ] && echo 1 || echo 0 )\"\n"
        "rm -rf \"$R\"; echo \"RH2_PROBE_OK=1\"\n"
    )


def grader_trusted_init_script(profile: GraderSandboxProfile) -> str:
    body = _USER_INIT_BODY.replace("__USER__", shlex.quote(profile.candidate_exec_user)).replace(
        "__UID__", str(profile.candidate_exec_uid)
    )
    return (
        _marker("grader-trusted-init") + "set -u\n" + body
        + f"chown {profile.candidate_exec_uid}:{profile.candidate_exec_uid} /home/{shlex.quote(profile.candidate_exec_user)} "
        "|| { echo \"RH2_INIT_ERROR=chown_failed\"; exit 4; }\n"
        "echo \"RH2_INIT_OK=1\"; echo \"GRADER_UID=$ACT\"\n"
    )


def grader_chown_before_eval_script(profile: GraderSandboxProfile) -> str:
    """root：候选测试启动前把 /testbed 交给候选执行用户（可信步骤写入的文件是 root 属主）。"""

    return (
        _marker("grader-chown-before-eval") + "set -u\n"
        f"chown -R {profile.candidate_exec_uid}:{profile.candidate_exec_uid} {shlex.quote(profile.testbed_path)} "
        "|| { echo \"RH2_CHOWN_ERROR=1\"; exit 4; }\necho \"RH2_CHOWN_OK=1\"\n"
    )


def grader_prelaunch_probe_script(profile: GraderSandboxProfile) -> str:
    """以候选执行用户身份运行：断网（只有 lo）、非 root、CapEff=0、限额。"""

    return (
        _marker("grader-prelaunch-probe") + "set -u\n" + _PROBE_COMMON
        + _forbidden_probe_lines(profile.forbidden_probe_targets)
        + "echo \"RH2_PROBE_OK=1\"\n"
    )


def list_probe_scripts(rollout: RolloutSandboxProfile, grader: GraderSandboxProfile | None) -> dict[str, str]:
    """H7 清单：脚本 id → 文本（同一组脚本在本地与 GPU 复跑）。"""

    scripts = {
        "rollout-trusted-init": rollout_trusted_init_script(rollout),
        "git-sanitize": git_sanitize_script(rollout.workdir),
        "rollout-prelaunch-probe": rollout_prelaunch_probe_script(rollout),
        "rollout-extended-probe": rollout_extended_probe_script(rollout),
        "git-future-probe": git_future_probe_script(rollout.workdir),
        "storage-quota-probe": storage_quota_probe_script(rollout.writable_layer_quota_bytes),
    }
    if grader is not None:
        scripts["grader-trusted-init"] = grader_trusted_init_script(grader)
        scripts["grader-prelaunch-probe"] = grader_prelaunch_probe_script(grader)
        scripts["grader-chown-before-eval"] = grader_chown_before_eval_script(grader)
    return scripts


def parse_key_value_output(text: str) -> dict[str, str]:
    """`KEY=VALUE` 行 → dict（重复键取最后一个；非 KEY=VALUE 行忽略）。"""

    out: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line and re.match(r"^[A-Za-z][A-Za-z0-9_]*=", line):
            key, value = line.split("=", 1)
            out[key] = value.strip()
    return out


# ---------------------------------------------------------------------------
# 纯核对函数（docker inspect JSON + 探针输出 → 违规清单）
# ---------------------------------------------------------------------------


def _norm_caps(values: Sequence[str] | None) -> set[str]:
    out = set()
    for v in values or ():
        v = str(v).upper()
        out.add(v[4:] if v.startswith("CAP_") else v)
    return out


def _security_opt_violations(sec: Sequence[str] | None) -> list[str]:
    opts = [str(o) for o in (sec or ())]
    out = []
    if not any(o == "no-new-privileges" or o.startswith("no-new-privileges:true") for o in opts):
        out.append("security_opt:no-new-privileges 缺失")
    for o in opts:
        if "unconfined" in o:
            out.append(f"security_opt:{o} 关闭了默认约束")
    return out


def _cpu_max_expected(cpus: float) -> str:
    return f"{int(round(float(cpus) * 100000))} 100000"


def _limits_inspect_violations(hc: Mapping[str, Any], *, pids_limit: int, cpus: float, memory_bytes: int,
                               tmpfs: Mapping[str, str], require_quota: bool, quota_bytes: int) -> list[str]:
    v: list[str] = []
    if hc.get("Privileged") is not False:
        v.append(f"Privileged={hc.get('Privileged')!r}")
    if _norm_caps(hc.get("CapDrop")) != {"ALL"}:
        v.append(f"CapDrop={hc.get('CapDrop')!r} != ['ALL']")
    if hc.get("PidsLimit") != pids_limit:
        v.append(f"PidsLimit={hc.get('PidsLimit')!r} != {pids_limit}")
    if hc.get("NanoCpus") != int(round(float(cpus) * 1e9)):
        v.append(f"NanoCpus={hc.get('NanoCpus')!r} != {int(round(float(cpus) * 1e9))}")
    if hc.get("Memory") != memory_bytes:
        v.append(f"Memory={hc.get('Memory')!r} != {memory_bytes}")
    if hc.get("MemorySwap") != memory_bytes:
        v.append(f"MemorySwap={hc.get('MemorySwap')!r} != Memory（swap 必须禁用）")
    if dict(hc.get("Tmpfs") or {}) != dict(tmpfs):
        v.append(f"Tmpfs={hc.get('Tmpfs')!r} != {dict(tmpfs)!r}")
    if hc.get("ReadonlyRootfs") not in (False, None):
        v.append("ReadonlyRootfs 意外为 True（/testbed 须可写）")
    storage = hc.get("StorageOpt") or {}
    if require_quota and str(storage.get("size", "")) != str(quota_bytes):
        v.append(f"StorageOpt={storage!r} 未声明 size={quota_bytes}")
    return v


def _mounts_violations(container: Mapping[str, Any], declared_readonly_binds: Sequence[tuple[str, str]]) -> list[str]:
    v: list[str] = []
    declared = {(src, dst) for src, dst in declared_readonly_binds}
    binds = list((container.get("HostConfig") or {}).get("Binds") or [])
    seen: set[tuple[str, str]] = set()
    for bind in binds:
        parts = str(bind).split(":")
        if len(parts) < 2 or (len(parts) >= 3 and "ro" not in parts[2].split(",")):
            v.append(f"bind mount 非只读：{bind}")
            continue
        key = (parts[0], parts[1])
        if key not in declared:
            v.append(f"未声明的 bind mount：{bind}")
        seen.add(key)
    for m in container.get("Mounts") or []:
        mtype = m.get("Type")
        if mtype == "tmpfs":
            continue
        if mtype == "bind":
            key = (m.get("Source"), m.get("Destination"))
            if key not in declared:
                v.append(f"未声明的 bind mount：{key}")
            elif m.get("RW") is not False:
                v.append(f"bind mount 可写：{key}")
            continue
        v.append(f"意外的 mount 类型 {mtype!r}：{m.get('Destination')!r}")
    return v


def _facts_from_inspect(container: Mapping[str, Any]) -> dict[str, Any]:
    hc = container.get("HostConfig") or {}
    return {
        "cap_drop": list(hc.get("CapDrop") or []),
        "cap_add": list(hc.get("CapAdd") or []),
        "security_opt": list(hc.get("SecurityOpt") or []),
        "privileged": hc.get("Privileged"),
        "pids_limit": hc.get("PidsLimit"),
        "nano_cpus": hc.get("NanoCpus"),
        "memory": hc.get("Memory"),
        "memory_swap": hc.get("MemorySwap"),
        "tmpfs": dict(hc.get("Tmpfs") or {}),
        "storage_opt": dict(hc.get("StorageOpt") or {}),
        "binds": list(hc.get("Binds") or []),
        "network_mode": hc.get("NetworkMode"),
        "networks": sorted((container.get("NetworkSettings") or {}).get("Networks") or {}),
        "mounts": [
            {"type": m.get("Type"), "source": m.get("Source"), "destination": m.get("Destination"), "rw": m.get("RW")}
            for m in container.get("Mounts") or []
        ],
        "config_user": (container.get("Config") or {}).get("User"),
        "config_env": list((container.get("Config") or {}).get("Env") or []),
        "running": (container.get("State") or {}).get("Running"),
        "image": container.get("Image"),
    }


def check_rollout_inspect(
    container: Mapping[str, Any], profile: RolloutSandboxProfile, *, expected_network: str,
) -> list[str]:
    """rollout 容器结构事实核对（纯函数；输入 = `docker inspect <name>` 的单个元素）。"""

    hc = container.get("HostConfig") or {}
    v = _limits_inspect_violations(
        hc, pids_limit=profile.pids_limit, cpus=profile.cpus, memory_bytes=profile.memory_bytes,
        tmpfs=profile.expected_tmpfs(), require_quota=profile.require_writable_layer_quota,
        quota_bytes=profile.writable_layer_quota_bytes,
    )
    if _norm_caps(hc.get("CapAdd")) != set(profile.trusted_init_caps):
        v.append(f"CapAdd={hc.get('CapAdd')!r} != trusted_init_caps {sorted(profile.trusted_init_caps)}")
    v += _security_opt_violations(hc.get("SecurityOpt"))
    if hc.get("NetworkMode") != expected_network:
        v.append(f"NetworkMode={hc.get('NetworkMode')!r} != attempt 网络 {expected_network!r}")
    networks = sorted((container.get("NetworkSettings") or {}).get("Networks") or {})
    if networks != [expected_network]:
        v.append(f"Networks={networks!r} != [{expected_network!r}]")
    v += _mounts_violations(container, ())
    if (container.get("State") or {}).get("Running") is not True:
        v.append("State.Running != True")
    return v


def check_rollout_probe(
    facts: Mapping[str, str], profile: RolloutSandboxProfile, *, expected_head: str | None = None,
    require_workdir: bool = True,
) -> list[str]:
    """rollout 容器内探针事实核对（纯函数；输入 = parse_key_value_output 的结果）。"""

    v: list[str] = []
    if facts.get("RH2_PROBE_OK") != "1":
        v.append("探针未完整执行（RH2_PROBE_OK 缺失）")
    if facts.get("UID") != str(profile.agent_uid):
        v.append(f"UID={facts.get('UID')!r} != {profile.agent_uid}（模型控制进程必须非 root 且为固定 uid）")
    if facts.get("CAPEFF", "").strip("0") != "":
        v.append(f"CapEff={facts.get('CAPEFF')!r} != 0")
    if facts.get("CAPPRM", "").strip("0") != "":
        v.append(f"CapPrm={facts.get('CAPPRM')!r} != 0")
    if facts.get("NNP") != "1":
        v.append(f"NoNewPrivs={facts.get('NNP')!r} != 1")
    v += _cgroup_violations(facts, pids_limit=profile.pids_limit, cpus=profile.cpus, memory_bytes=profile.memory_bytes)
    if facts.get("NET_relay") != "CONNECTED":
        v.append(f"NET_relay={facts.get('NET_relay')!r}：模型代理 relay 不可达")
    for key, value in facts.items():
        if (key.startswith("NET_forbidden_") or key == "NET_upstream_direct") and value != "DENIED":
            v.append(f"{key}={value!r}：egress 未阻断")
    if facts.get("DNS_EXTERNAL") != "DENIED":
        v.append(f"DNS_EXTERNAL={facts.get('DNS_EXTERNAL')!r}")
    for key, value in facts.items():
        if key.startswith("HIDDEN_") and not value.startswith("DENIED"):
            v.append(f"{key}={value}：隐藏路径对 agent 可读")
    routed = {x for x in (facts.get("ROUTED_IFACES") or "").split(",") if x}
    if len(routed) != 1 or "lo" in routed:
        v.append(f"ROUTED_IFACES={sorted(routed)!r}：rollout 只允许恰好一个接口（attempt 网络）有路由")
    if facts.get("WORKDIR_MISSING") == "1":
        if require_workdir:
            v.append("workdir 不存在")
    else:
        if facts.get("GIT_REMOTES") not in ("0", None):
            v.append(f"GIT_REMOTES={facts.get('GIT_REMOTES')!r} != 0")
        if facts.get("GIT_REFLOG") not in ("0", None):
            v.append(f"GIT_REFLOG={facts.get('GIT_REFLOG')!r} != 0")
        if facts.get("WORKDIR_WRITABLE") != "1":
            v.append("workdir 对 agent 不可写")
        if facts.get("WORKDIR_OWNER") != str(profile.agent_uid):
            v.append(f"WORKDIR_OWNER={facts.get('WORKDIR_OWNER')!r} != {profile.agent_uid}")
        if expected_head is not None and facts.get("GIT_HEAD") != expected_head:
            v.append(f"GIT_HEAD={facts.get('GIT_HEAD')!r} != {expected_head}")
    if facts.get("HOME_WRITABLE") != "1":
        v.append("HOME 对 agent 不可写")
    if facts.get("TMP_WRITABLE") != "1":
        v.append("/tmp 对 agent 不可写")
    return v


def _cgroup_violations(facts: Mapping[str, str], *, pids_limit: int, cpus: float, memory_bytes: int) -> list[str]:
    v: list[str] = []
    if facts.get("CG_PIDS_MAX") != str(pids_limit):
        v.append(f"cgroup pids.max={facts.get('CG_PIDS_MAX')!r} != {pids_limit}")
    if facts.get("CG_MEMORY_MAX") != str(memory_bytes):
        v.append(f"cgroup memory.max={facts.get('CG_MEMORY_MAX')!r} != {memory_bytes}")
    if facts.get("CG_SWAP_MAX") != "0":
        v.append(f"cgroup memory.swap.max={facts.get('CG_SWAP_MAX')!r} != 0")
    if facts.get("CG_CPU_MAX") != _cpu_max_expected(cpus):
        v.append(f"cgroup cpu.max={facts.get('CG_CPU_MAX')!r} != {_cpu_max_expected(cpus)!r}")
    return v


def check_grader_inspect(
    container: Mapping[str, Any], profile: GraderSandboxProfile, *,
    declared_readonly_binds: Sequence[tuple[str, str]] = (),
) -> list[str]:
    hc = container.get("HostConfig") or {}
    v = _limits_inspect_violations(
        hc, pids_limit=profile.pids_limit, cpus=profile.cpus, memory_bytes=profile.memory_bytes,
        tmpfs=profile.expected_tmpfs(), require_quota=profile.require_writable_layer_quota,
        quota_bytes=profile.writable_layer_quota_bytes,
    )
    if _norm_caps(hc.get("CapAdd")) != set(profile.trusted_init_caps):
        v.append(f"CapAdd={hc.get('CapAdd')!r} != trusted_init_caps {sorted(profile.trusted_init_caps)}")
    v += _security_opt_violations(hc.get("SecurityOpt"))
    if hc.get("NetworkMode") != "none":
        v.append(f"NetworkMode={hc.get('NetworkMode')!r} != 'none'（grader 全断网）")
    networks = sorted((container.get("NetworkSettings") or {}).get("Networks") or {})
    if networks != ["none"]:
        v.append(f"Networks={networks!r} != ['none']")
    v += _mounts_violations(container, declared_readonly_binds)
    if (container.get("State") or {}).get("Running") is not True:
        v.append("State.Running != True")
    return v


def check_grader_probe(facts: Mapping[str, str], profile: GraderSandboxProfile) -> list[str]:
    v: list[str] = []
    if facts.get("RH2_PROBE_OK") != "1":
        v.append("探针未完整执行（RH2_PROBE_OK 缺失）")
    if facts.get("UID") != str(profile.candidate_exec_uid):
        v.append(f"UID={facts.get('UID')!r} != {profile.candidate_exec_uid}（候选代码执行进程必须非 root）")
    if facts.get("CAPEFF", "").strip("0") != "":
        v.append(f"CapEff={facts.get('CAPEFF')!r} != 0")
    if facts.get("NNP") != "1":
        v.append(f"NoNewPrivs={facts.get('NNP')!r} != 1")
    v += _cgroup_violations(facts, pids_limit=profile.pids_limit, cpus=profile.cpus, memory_bytes=profile.memory_bytes)
    routed = {x for x in (facts.get("ROUTED_IFACES") or "").split(",") if x}
    if routed:
        v.append(f"ROUTED_IFACES={sorted(routed)!r}：grader 不得有任何带路由的接口（只允许 loopback）")
    for key, value in facts.items():
        if key.startswith("NET_") and value != "DENIED":
            v.append(f"{key}={value!r}：grader 不得有任何 egress")
    if facts.get("DNS_EXTERNAL") != "DENIED":
        v.append(f"DNS_EXTERNAL={facts.get('DNS_EXTERNAL')!r}")
    if facts.get("HOME_WRITABLE") != "1":
        v.append("HOME 对候选执行用户不可写（eval 脚本写 ~/.gitconfig 会失败）")
    return v


# ---------------------------------------------------------------------------
# 启动前核对（inspect + 探针）——每个容器一次
# ---------------------------------------------------------------------------


@dataclass
class PrelaunchReport:
    """一次启动前核对的结果（run 记录 / audit 摘要用）。"""

    role: str
    container_name: str
    ok: bool
    violations: list[str] = field(default_factory=list)
    inspect_facts: dict[str, Any] = field(default_factory=dict)
    probe_facts: dict[str, str] = field(default_factory=dict)
    seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "container_name": self.container_name,
            "ok": self.ok,
            "violations": list(self.violations),
            "inspect_facts": dict(self.inspect_facts),
            "probe_facts": dict(self.probe_facts),
            "seconds": round(self.seconds, 4),
        }


async def _inspect_container(docker: DockerRunner, name: str, *, timeout: float) -> tuple[dict[str, Any] | None, str]:
    res = await _call(docker, "inspect", name, timeout=timeout)
    if res.exit_code != 0:
        return None, (res.stderr or res.stdout).strip()[-300:]
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        return None, f"inspect 输出不是 JSON：{exc}"
    if isinstance(payload, list):
        if not payload:
            return None, "inspect 返回空列表"
        payload = payload[0]
    if not isinstance(payload, dict):
        return None, "inspect 输出形状错误"
    return payload, ""


async def _exec_as(docker: DockerRunner, name: str, script: str, *, user: str | None, home: str | None,
                   timeout: float) -> Any:
    args = ["exec"]
    if user is not None:
        args += ["-u", user]
    if home is not None:
        args += ["-e", f"HOME={home}"]
    args += [name, "bash", "-c", script]
    return await _call(docker, *args, timeout=timeout)


async def run_rollout_prelaunch_check(
    docker: DockerRunner, *, name: str, profile: RolloutSandboxProfile, network: str, expected_head: str | None = None,
    require_workdir: bool = True,
) -> PrelaunchReport:
    """容器创建 + 可信初始化之后、harness 启动之前：一次 inspect + 一次 agent 身份探针。"""

    started = time.monotonic()
    report = PrelaunchReport(role="rollout", container_name=name, ok=False)
    container, err = await _inspect_container(docker, name, timeout=profile.probe_timeout_seconds)
    if container is None:
        report.violations.append(f"docker inspect 失败：{err}")
    else:
        report.inspect_facts = _facts_from_inspect(container)
        report.violations += check_rollout_inspect(container, profile, expected_network=network)
    probe = await _exec_as(
        docker, name, rollout_prelaunch_probe_script(profile), user=str(profile.agent_uid),
        home=f"/home/{profile.agent_user}", timeout=profile.probe_timeout_seconds,
    )
    if probe.exit_code != 0 and "RH2_PROBE_OK=1" not in probe.stdout:
        report.violations.append(f"探针执行失败 exit={probe.exit_code}：{(probe.stderr or probe.stdout).strip()[-300:]}")
    report.probe_facts = parse_key_value_output(probe.stdout)
    report.violations += check_rollout_probe(
        report.probe_facts, profile, expected_head=expected_head, require_workdir=require_workdir,
    )
    report.ok = not report.violations
    report.seconds = time.monotonic() - started
    return report


async def run_grader_prelaunch_check(
    docker: DockerRunner, *, name: str, profile: GraderSandboxProfile,
    declared_readonly_binds: Sequence[tuple[str, str]] = (),
) -> PrelaunchReport:
    started = time.monotonic()
    report = PrelaunchReport(role="grader", container_name=name, ok=False)
    container, err = await _inspect_container(docker, name, timeout=profile.probe_timeout_seconds)
    if container is None:
        report.violations.append(f"docker inspect 失败：{err}")
    else:
        report.inspect_facts = _facts_from_inspect(container)
        report.violations += check_grader_inspect(container, profile, declared_readonly_binds=declared_readonly_binds)
    probe = await _exec_as(
        docker, name, grader_prelaunch_probe_script(profile), user=str(profile.candidate_exec_uid),
        home=f"/home/{profile.candidate_exec_user}", timeout=profile.probe_timeout_seconds,
    )
    if probe.exit_code != 0 and "RH2_PROBE_OK=1" not in probe.stdout:
        report.violations.append(f"探针执行失败 exit={probe.exit_code}：{(probe.stderr or probe.stdout).strip()[-300:]}")
    report.probe_facts = parse_key_value_output(probe.stdout)
    report.violations += check_grader_probe(report.probe_facts, profile)
    report.ok = not report.violations
    report.seconds = time.monotonic() - started
    return report


async def run_trusted_init(docker: DockerRunner, *, name: str, script: str, timeout: float) -> dict[str, str]:
    """root 可信初始化（rollout / grader 通用）：失败抛 SandboxNetworkError 之外的 RuntimeError 由调用方分类。"""

    res = await _exec_as(docker, name, script, user="root", home="/root", timeout=timeout)
    facts = parse_key_value_output(res.stdout)
    if res.exit_code != 0 or facts.get("RH2_INIT_OK") != "1":
        raise RuntimeError(
            f"可信初始化失败 exit={res.exit_code}：{facts.get('RH2_INIT_ERROR', '')} {(res.stderr or res.stdout).strip()[-300:]}"
        )
    return facts


async def run_git_sanitize(docker: DockerRunner, *, name: str, workdir: str, timeout: float) -> dict[str, str]:
    """root：跑 git-sanitize 并核对其自证（未来对象为零、远端/reflog 为零、HEAD 与历史计数不变）。"""

    res = await _exec_as(docker, name, git_sanitize_script(workdir), user="root", home="/root", timeout=timeout)
    facts = parse_key_value_output(res.stdout)
    problems = git_sanitize_violations(facts, exit_code=res.exit_code)
    if problems:
        raise RuntimeError(
            "git-sanitize 未达标：" + "; ".join(problems) + f"；stderr={res.stderr.strip()[-200:]}"
        )
    return facts


def git_sanitize_violations(facts: Mapping[str, str], *, exit_code: int = 0) -> list[str]:
    v: list[str] = []
    if exit_code != 0 or facts.get("RH2_GIT_SANITIZE_OK") != "1":
        v.append(f"脚本失败 exit={exit_code} {facts.get('RH2_GIT_SANITIZE_ERROR', '')}")
        return v
    if facts.get("HEAD_BEFORE") != facts.get("HEAD_AFTER"):
        v.append("HEAD 改变")
    if facts.get("HISTORY_COUNT_BEFORE") != facts.get("HISTORY_COUNT_AFTER"):
        v.append("base 之前历史计数改变（不许丢正常历史）")
    if facts.get("REMOTES") != "0":
        v.append(f"REMOTES={facts.get('REMOTES')!r}")
    if facts.get("REFLOG_ENTRIES") != "0":
        v.append(f"REFLOG_ENTRIES={facts.get('REFLOG_ENTRIES')!r}")
    if facts.get("UNREACHABLE_OBJECTS") != "0":
        v.append(f"UNREACHABLE_OBJECTS={facts.get('UNREACHABLE_OBJECTS')!r}（dangling 未来对象仍在）")
    return v


# ---------------------------------------------------------------------------
# verify / dry-run 模式（bringup 启动 + W7 远端调用同一入口）
# ---------------------------------------------------------------------------


def _git_future_violations(facts: Mapping[str, str]) -> list[str]:
    v = []
    if facts.get("RH2_PROBE_OK") != "1":
        v.append("git-future-probe 未完整执行")
    if facts.get("FUTURE_BEFORE") != "RECOVERABLE":
        v.append("探针前置失败：reset 后未来对象本应仍可恢复")
    for key in ("FUTURE_CATFILE", "FUTURE_TAG", "FUTURE_BRANCH"):
        if facts.get(key) != "GONE":
            v.append(f"{key}={facts.get(key)!r}")
    if facts.get("FUTURE_LOSTFOUND") != "0":
        v.append(f"FUTURE_LOSTFOUND={facts.get('FUTURE_LOSTFOUND')!r}")
    if facts.get("FUTURE_GREP") != "ABSENT":
        v.append(f"FUTURE_GREP={facts.get('FUTURE_GREP')!r}")
    if facts.get("BASE_HISTORY") != "1" or facts.get("HEAD_IS_BASE") != "1":
        v.append("base 历史未保留")
    if facts.get("SANITIZE_UNREACHABLE_OBJECTS") != "0":
        v.append(f"sanitize 自证 UNREACHABLE={facts.get('SANITIZE_UNREACHABLE_OBJECTS')!r}")
    return v


async def verify_sandbox_profiles(
    docker: DockerRunner, *, rollout: RolloutSandboxProfile, grader: GraderSandboxProfile | None, image: str,
    run_id: str, relay: EgressRelayHandle, labels: Sequence[str] = (), expect_upstream_http: bool = False,
    name_prefix: str = "rh2-sbverify",
) -> dict[str, Any]:
    """在真实容器上验证两个 profile（结构事实 + 实际事实），返回 run 级记录 dict（`ok` 为总判定）。

    rollout 侧：attempt 网络 + relay 接入 + 容器（同一参数组装器）→ 可信初始化 → git-future 探针
    → 启动前核对 → 加长探针（提权/HTTP 经 relay）→ 存储预算探针；grader 侧：容器 → 可信初始化 →
    启动前核对 → 存储预算探针。全部资源最后清理。任何一步失败都记入 failures，不抛。
    """

    nonce = uuid.uuid4().hex[:8]
    record: dict[str, Any] = {
        "schema_id": RUNTIME_PROFILE_RECORD_SCHEMA_ID,
        "run_id": run_id,
        "verified_at_utc": _now_utc(),
        "probe_image": image,
        "runtime_profile_digest": runtime_profile_digest(rollout, grader),
        "relay": {"container_name": relay.container_name, "alias": relay.alias, "image": relay.image,
                  "listen_map": [list(e) for e in relay.listen_map]},
        "rollout": {"profile_id": rollout.profile_id, "digest": rollout.digest(), "parameters": rollout.to_parameters(),
                    "checks": {}, "ok": False},
        "grader": None,
        "failures": [],
        "ok": False,
    }
    failures: list[str] = record["failures"]
    pool = EgressSubnetPool(rollout.egress_subnet_pool, rollout.egress_subnet_prefix)

    # ---------------- rollout
    net_name = f"{name_prefix}-net-{nonce}"
    cname = f"{name_prefix}-rollout-{nonce}"
    checks: dict[str, Any] = record["rollout"]["checks"]
    network: AttemptNetwork | None = None
    started_container = False
    try:
        t0 = time.monotonic()
        network = await create_attempt_network(docker, profile=rollout, pool=pool, name=net_name, labels=labels)
        await connect_relay_to_network(docker, relay=relay, network=network)
        run = await _call(docker, *rollout.docker_run_args(name=cname, network=net_name, image=image, labels=labels),
                          timeout=180.0)
        if run.exit_code != 0:
            raise RuntimeError(f"rollout 容器启动失败：{(run.stderr or run.stdout).strip()[-300:]}")
        started_container = True
        checks["network_and_start_seconds"] = round(time.monotonic() - t0, 4)
        t0 = time.monotonic()
        init = await run_trusted_init(docker, name=cname, script=rollout_trusted_init_script(rollout),
                                      timeout=rollout.init_timeout_seconds)
        checks["trusted_init"] = {"facts": init, "seconds": round(time.monotonic() - t0, 4)}
        # git-future 探针（确定性最小边界探针之一）
        probe = await _exec_as(docker, cname, git_future_probe_script(rollout.workdir), user="root", home="/root",
                               timeout=rollout.sanitize_timeout_seconds)
        gf = parse_key_value_output(probe.stdout)
        gf_v = _git_future_violations(gf)
        checks["git_future_unrecoverable"] = {"ok": not gf_v, "violations": gf_v, "facts": gf,
                                              "stderr_tail": probe.stderr.strip()[-300:]}
        if gf_v:
            failures.append("rollout.git_future_unrecoverable: " + "; ".join(gf_v))
        # 真实 workdir 的 sanitize（探针镜像有 /testbed 时记录实际值；没有则如实记 skipped）
        has_workdir = await _exec_as(docker, cname, f"test -d {shlex.quote(rollout.workdir)}/.git && echo yes",
                                     user="root", home="/root", timeout=30.0)
        if "yes" in has_workdir.stdout:
            try:
                san = await run_git_sanitize(docker, name=cname, workdir=rollout.workdir,
                                             timeout=rollout.sanitize_timeout_seconds)
                checks["workdir_git_sanitize"] = {"ok": True, "facts": san}
            except RuntimeError as exc:
                checks["workdir_git_sanitize"] = {"ok": False, "error": str(exc)[:500]}
                failures.append(f"rollout.workdir_git_sanitize: {str(exc)[:200]}")
            # sanitize 之后属主再交还 agent（可信初始化已 chown，一致性起见重跑一次）
            await run_trusted_init(docker, name=cname, script=rollout_trusted_init_script(rollout),
                                   timeout=rollout.init_timeout_seconds)
        else:
            checks["workdir_git_sanitize"] = {"ok": None, "skipped": f"{rollout.workdir} 不是 git 仓库（探针镜像）"}
        pre = await run_rollout_prelaunch_check(
            docker, name=cname, profile=rollout, network=net_name, require_workdir=("yes" in has_workdir.stdout),
        )
        checks["prelaunch"] = pre.to_dict()
        if not pre.ok:
            failures.append("rollout.prelaunch: " + "; ".join(pre.violations))
        ext = await _exec_as(docker, cname, rollout_extended_probe_script(rollout), user=str(rollout.agent_uid),
                             home=f"/home/{rollout.agent_user}", timeout=rollout.probe_timeout_seconds)
        ef = parse_key_value_output(ext.stdout)
        ext_v = []
        if ef.get("ESCALATE_SU") != "DENIED":
            ext_v.append(f"ESCALATE_SU={ef.get('ESCALATE_SU')!r}")
        if ef.get("ESCALATE_SETUID") not in ("DENIED", "NO_PYTHON"):
            ext_v.append(f"ESCALATE_SETUID={ef.get('ESCALATE_SETUID')!r}")
        if expect_upstream_http and not str(ef.get("PROXY_HTTP", "")).startswith("HTTP/"):
            ext_v.append(f"PROXY_HTTP={ef.get('PROXY_HTTP')!r}：经 relay 未收到上游 HTTP 状态行")
        checks["extended"] = {"ok": not ext_v, "violations": ext_v, "facts": ef}
        if ext_v:
            failures.append("rollout.extended: " + "; ".join(ext_v))
        sq = await _exec_as(docker, cname, storage_quota_probe_script(rollout.writable_layer_quota_bytes),
                            user="root", home="/root", timeout=rollout.probe_timeout_seconds)
        sqf = parse_key_value_output(sq.stdout)
        enforced = sqf.get("QUOTA_ENFORCED")
        checks["writable_layer_quota"] = {
            "requested": rollout.require_writable_layer_quota, "quota_bytes": rollout.writable_layer_quota_bytes,
            "enforced": enforced,
        }
        if rollout.require_writable_layer_quota and enforced != "1":
            failures.append(f"rollout.writable_layer_quota: 要求强制但实测 enforced={enforced!r}")
    except EgressRelayUnavailable as exc:
        failures.append(f"rollout.relay: {exc}")
    except (SandboxNetworkError, RuntimeError) as exc:
        failures.append(f"rollout: {str(exc)[:400]}")
    finally:
        if started_container:
            await _call(docker, "rm", "-f", cname, timeout=120.0)
        if network is not None:
            td = await teardown_attempt_network(docker, network_name=network.name, relay=relay, pool=pool,
                                                subnet=network.subnet)
            if td:
                failures.append("rollout.cleanup: " + "; ".join(td))
    record["rollout"]["ok"] = not any(f.startswith("rollout") for f in failures)

    # ---------------- grader
    if grader is not None:
        gname = f"{name_prefix}-grader-{nonce}"
        gchecks: dict[str, Any] = {}
        record["grader"] = {"profile_id": grader.profile_id, "digest": grader.digest(),
                            "parameters": grader.to_parameters(), "checks": gchecks, "ok": False}
        gstarted = False
        try:
            run = await _call(docker, *grader.docker_run_args(name=gname, image=image, labels=labels), timeout=180.0)
            if run.exit_code != 0:
                raise RuntimeError(f"grader 容器启动失败：{(run.stderr or run.stdout).strip()[-300:]}")
            gstarted = True
            init = await run_trusted_init(docker, name=gname, script=grader_trusted_init_script(grader),
                                          timeout=grader.init_timeout_seconds)
            gchecks["trusted_init"] = {"facts": init}
            pre = await run_grader_prelaunch_check(docker, name=gname, profile=grader)
            gchecks["prelaunch"] = pre.to_dict()
            if not pre.ok:
                failures.append("grader.prelaunch: " + "; ".join(pre.violations))
            sq = await _exec_as(docker, gname, storage_quota_probe_script(grader.writable_layer_quota_bytes),
                                user="root", home="/root", timeout=grader.probe_timeout_seconds)
            enforced = parse_key_value_output(sq.stdout).get("QUOTA_ENFORCED")
            gchecks["writable_layer_quota"] = {
                "requested": grader.require_writable_layer_quota, "quota_bytes": grader.writable_layer_quota_bytes,
                "enforced": enforced,
            }
            if grader.require_writable_layer_quota and enforced != "1":
                failures.append(f"grader.writable_layer_quota: 要求强制但实测 enforced={enforced!r}")
        except RuntimeError as exc:
            failures.append(f"grader: {str(exc)[:400]}")
        finally:
            if gstarted:
                await _call(docker, "rm", "-f", gname, timeout=120.0)
        record["grader"]["ok"] = not any(f.startswith("grader") for f in failures)

    record["ok"] = not failures
    return record


def write_runtime_profile_record(path: Path, record: Mapping[str, Any]) -> Path:
    """原子写 run 级记录（临时文件 + fsync + replace）。"""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
# CLI：verify / list-probes / dump-probes
# ---------------------------------------------------------------------------


async def _cli_verify(ns: argparse.Namespace) -> int:
    env = dict(os.environ)
    rollout = rollout_profile_from_env(env, model_proxy_upstream_host=ns.upstream_host,
                                       model_proxy_upstream_port=ns.upstream_port)
    grader = None if ns.no_grader else grader_profile_from_env(env)
    run_id = ns.run_id or f"verify-{uuid.uuid4().hex[:8]}"
    labels = ("--label", f"{_RUN_LABEL_KEY}={run_id}")
    docker = default_docker_runner
    relay = await start_egress_relay(docker, rollout, run_id=run_id, labels=labels)
    try:
        record = await verify_sandbox_profiles(
            docker, rollout=rollout, grader=grader, image=ns.image, run_id=run_id, relay=relay, labels=labels,
            expect_upstream_http=ns.expect_upstream_http,
        )
    finally:
        record_failures = await stop_egress_relay(docker, relay)
    if record_failures:
        record["failures"] += record_failures
        record["ok"] = False
    out = Path(ns.out) / "runtime_profile.json"
    write_runtime_profile_record(out, record)
    print(f"[rh2-sandbox-profile] ok={record['ok']} digest={record['runtime_profile_digest']} → {out}")
    for failure in record["failures"]:
        print(f"[rh2-sandbox-profile] FAIL {failure}")
    return 0 if record["ok"] else 1


def _cli_profiles(ns: argparse.Namespace) -> tuple[RolloutSandboxProfile, GraderSandboxProfile | None]:
    env = dict(os.environ)
    rollout = rollout_profile_from_env(env, model_proxy_upstream_host=ns.upstream_host,
                                       model_proxy_upstream_port=ns.upstream_port)
    grader = None if getattr(ns, "no_grader", False) else grader_profile_from_env(env)
    return rollout, grader


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m repoharness2.adapters.slime.sandbox_profile",
        description="W3b：唯一正式 rollout/grader Docker profile 的验证（dry-run）与探针清单。",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="起 relay + 真实容器，跑全部探针，写 <out>/runtime_profile.json，失败非零退出")
    v.add_argument("--image", required=True, help="探针镜像（建议用真实任务镜像；须含 bash/git）")
    v.add_argument("--upstream-host", required=True, help="模型代理上游地址（relay 视角，如 172.17.0.1）")
    v.add_argument("--upstream-port", type=int, required=True)
    v.add_argument("--out", required=True, help="evidence 输出目录")
    v.add_argument("--run-id", default=None)
    v.add_argument("--no-grader", action="store_true")
    v.add_argument("--expect-upstream-http", action="store_true", help="上游 adapter 在场：要求经 relay 收到 HTTP 状态行")
    lp = sub.add_parser("list-probes", help="打印 H7 探针脚本清单（id + sha256）")
    lp.add_argument("--upstream-host", default="172.17.0.1")
    lp.add_argument("--upstream-port", type=int, default=18001)
    dp = sub.add_parser("dump-probes", help="把探针脚本落成文件（H7 对照/离线审阅）")
    dp.add_argument("--out", required=True)
    dp.add_argument("--upstream-host", default="172.17.0.1")
    dp.add_argument("--upstream-port", type=int, default=18001)
    ns = parser.parse_args(argv)
    if ns.cmd == "verify":
        return asyncio.run(_cli_verify(ns))
    rollout, grader = _cli_profiles(ns)
    scripts = list_probe_scripts(rollout, grader)
    if ns.cmd == "list-probes":
        for sid, text in scripts.items():
            print(f"{sid}\tsha256:{hashlib.sha256(text.encode()).hexdigest()}")
        return 0
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=True)
    for sid, text in scripts.items():
        (out / f"{sid}.sh").write_text(text, encoding="utf-8")
    print(f"[rh2-sandbox-profile] {len(scripts)} 个探针脚本 → {out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
