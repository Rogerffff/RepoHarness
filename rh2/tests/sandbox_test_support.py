"""W3b 测试支撑：正式 rollout/grader profile 的测试夹具 + docker 替身对 profile 路径命令的分派。

设计（与 tests/adapters/test_slime_generate.py 的 FakeRolloutDocker 纪律一致）：
- 真实核对函数（`check_rollout_inspect` / `check_rollout_probe` / grader 同款）在单测里**照常运行**，
  替身只负责把 `docker run` 参数"如实"合成为 `docker inspect` JSON、把带标记的容器内脚本换成
  罐头输出——这样单测证明的是"编排层把 profile 参数交给了 docker 且核对逻辑消费了它们"，
  真实 docker 行为由 @docker 测试（tests/adapters/test_w3b_sandbox_docker.py 等）证明。
- 负例通过 `ProfileFakeState` 的旋钮注入：探针事实覆盖、inspect 字段覆盖、网络创建失败、relay 缺席。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from repoharness2.adapters.slime.sandbox_profile import (
    EgressRelayHandle,
    GraderSandboxProfile,
    RolloutSandboxProfile,
    runtime_profile_digest,
    script_id_of,
)
from repoharness2.grading.manager import ExecResult

TEST_UPSTREAM_HOST = "10.0.0.1"
TEST_UPSTREAM_PORT = 18001
RELAY_FAKE_IMAGE_ID = "sha256:" + "re" * 32  # 替身里 relay 容器的 image ID（R2 digest 核对用）
BASE_COMMIT_FOR_RUNTIME_FAKE = "a" * 40


def make_rollout_profile(**overrides: Any) -> RolloutSandboxProfile:
    params: dict[str, Any] = dict(
        model_proxy_upstream_host=TEST_UPSTREAM_HOST, model_proxy_upstream_port=TEST_UPSTREAM_PORT,
    )
    params.update(overrides)
    return RolloutSandboxProfile(**params)


def make_grader_profile(**overrides: Any) -> GraderSandboxProfile:
    return GraderSandboxProfile(**overrides)


TEST_RELAY = EgressRelayHandle(
    container_name="rh2-egress-relay-test",
    alias="rh2-egress-relay",
    listen_map=((TEST_UPSTREAM_PORT, TEST_UPSTREAM_HOST, TEST_UPSTREAM_PORT),),
    image="python:3.12-slim",
    run_id="test-run",
)


def formal_sandbox_kwargs(
    profile: RolloutSandboxProfile | None = None, grader: GraderSandboxProfile | None = None,
) -> dict[str, Any]:
    """RolloutOrchestrator 在 fa_formal 下必需的三个 W3b 构造参数。"""

    rollout = profile if profile is not None else make_rollout_profile()
    return {
        "sandbox_profile": rollout,
        "egress_relay": TEST_RELAY,
        "runtime_profile_digest": runtime_profile_digest(rollout, grader),
    }


# ---------------------------------------------------------------------------
# docker run 参数 → inspect JSON（替身的"如实合成"）
# ---------------------------------------------------------------------------


def synthesize_inspect(run_args: tuple[str, ...], *, name: str, running: bool = True) -> dict[str, Any]:
    """按真实 docker 的字段形状合成 `docker inspect <name>` 单元素（CapAdd 带 CAP_ 前缀、Tmpfs 保留原串）。"""

    args = list(run_args)
    hc: dict[str, Any] = {
        "CapDrop": [], "CapAdd": [], "SecurityOpt": None, "Privileged": False, "PidsLimit": None,
        "NanoCpus": 0, "Memory": 0, "MemorySwap": 0, "Tmpfs": None, "Binds": None, "NetworkMode": "bridge",
        "ReadonlyRootfs": False, "StorageOpt": None, "Ulimits": [],
    }
    labels: dict[str, str] = {}
    mounts: list[dict[str, Any]] = []
    i = 1  # args[0] == "run"
    while i < len(args):
        a = args[i]
        nxt = args[i + 1] if i + 1 < len(args) else None
        if a == "--cap-drop":
            hc["CapDrop"].append(nxt); i += 2
        elif a == "--cap-add":
            hc["CapAdd"].append("CAP_" + nxt); i += 2
        elif a == "--security-opt":
            hc["SecurityOpt"] = (hc["SecurityOpt"] or []) + [nxt]; i += 2
        elif a == "--pids-limit":
            hc["PidsLimit"] = int(nxt); i += 2
        elif a == "--cpus":
            hc["NanoCpus"] = int(round(float(nxt) * 1e9)); i += 2
        elif a == "--memory":
            hc["Memory"] = int(nxt); i += 2
        elif a == "--memory-swap":
            hc["MemorySwap"] = int(nxt); i += 2
        elif a == "--tmpfs":
            path, _, opts = nxt.partition(":")
            hc["Tmpfs"] = {**(hc["Tmpfs"] or {}), path: opts}
            mounts.append({"Type": "tmpfs", "Source": "", "Destination": path, "RW": True})
            i += 2
        elif a == "--network":
            hc["NetworkMode"] = nxt; i += 2
        elif a in ("--volume", "-v"):
            src, dst, *rest = nxt.split(":")
            hc["Binds"] = (hc["Binds"] or []) + [nxt]
            mounts.append({"Type": "bind", "Source": src, "Destination": dst, "RW": not (rest and "ro" in rest[0])})
            i += 2
        elif a == "--storage-opt":
            k, _, v = nxt.partition("=")
            hc["StorageOpt"] = {k: v}; i += 2
        elif a == "--label":
            k, _, v = nxt.partition("=")
            labels[k] = v; i += 2
        elif a == "--privileged":
            hc["Privileged"] = True; i += 1
        elif a == "--read-only":
            hc["ReadonlyRootfs"] = True; i += 1
        elif a in ("--detach", "-d"):
            i += 1
        elif a == "--name":
            i += 2
        elif a in ("--user", "-u", "--env", "-e"):
            i += 2
        else:
            break  # image + command
    return {
        "Id": "f00dfeedcafe" * 5,
        "Name": f"/{name}",
        "Image": "sha256:" + "ab" * 32,
        "State": {"Running": running},
        "HostConfig": hc,
        "Config": {"User": "", "Env": ["PATH=/usr/bin"], "Labels": labels},
        "Mounts": mounts,
        "NetworkSettings": {"Networks": {hc["NetworkMode"]: {}}},
    }


# ---------------------------------------------------------------------------
# 容器内脚本罐头输出
# ---------------------------------------------------------------------------


def _cg(pids: int, cpus: float, memory: int) -> str:
    return (
        f"CG_VERSION=v2\nCG_PIDS_MAX={pids}\nCG_MEMORY_MAX={memory}\nCG_SWAP_MAX=0\n"
        f"CG_CPU_MAX={int(round(cpus * 100000))} 100000\n"
    )


def rollout_probe_output(profile: RolloutSandboxProfile, *, head: str, overrides: dict[str, str] | None = None) -> str:
    facts: dict[str, str] = {
        "UID": str(profile.agent_uid), "GID": str(profile.agent_uid),
        "CAPEFF": "0000000000000000", "CAPPRM": "0000000000000000", "CAPBND": "0000000000000000", "NNP": "1",
    }
    lines = [f"{k}={v}" for k, v in facts.items()]
    lines.append(_cg(profile.pids_limit, profile.cpus, profile.memory_bytes).rstrip("\n"))
    lines += ["IFACES=eth0,lo,", "ROUTED_IFACES=eth0,", "NET_relay=CONNECTED"]
    lines += [f"NET_forbidden_{i}=DENIED" for i in range(len(profile.forbidden_probe_targets))]
    lines += ["NET_upstream_direct=DENIED", "DNS_EXTERNAL=DENIED", "HOME_WRITABLE=1", "TMP_WRITABLE=1"]
    lines += [f"HIDDEN_{i}=DENIED:{p}" for i, p in enumerate(profile.hidden_paths)]
    lines += [
        "GIT_REMOTES=0", "GIT_REFLOG=0", "GIT_REFS=1", f"GIT_HEAD={head}", "WORKDIR_WRITABLE=1",
        f"WORKDIR_OWNER={profile.agent_uid}", "RH2_PROBE_OK=1",
    ]
    text = "\n".join(lines) + "\n"
    for key, value in (overrides or {}).items():
        text = "\n".join(
            (f"{key}={value}" if line.startswith(key + "=") else line) for line in text.splitlines()
        ) + "\n"
        if not any(line.startswith(key + "=") for line in text.splitlines()):
            text += f"{key}={value}\n"
    return text


def grader_probe_output(profile: GraderSandboxProfile, *, overrides: dict[str, str] | None = None) -> str:
    lines = [
        f"UID={profile.candidate_exec_uid}", f"GID={profile.candidate_exec_uid}",
        "CAPEFF=0000000000000000", "CAPPRM=0000000000000000", "CAPBND=0000000000000000", "NNP=1",
        _cg(profile.pids_limit, profile.cpus, profile.memory_bytes).rstrip("\n"),
        "IFACES=lo,sit0,tunl0,", "ROUTED_IFACES=", "DNS_EXTERNAL=DENIED", "HOME_WRITABLE=1", "TMP_WRITABLE=1",
    ]
    lines += [f"NET_forbidden_{i}=DENIED" for i in range(len(profile.forbidden_probe_targets))]
    lines.append("RH2_PROBE_OK=1")
    text = "\n".join(lines) + "\n"
    for key, value in (overrides or {}).items():
        text = "\n".join(
            (f"{key}={value}" if line.startswith(key + "=") else line) for line in text.splitlines()
        ) + "\n"
    return text


def git_sanitize_output(head: str, *, overrides: dict[str, str] | None = None) -> str:
    facts = {
        "RH2_GIT_SANITIZE_OK": "1", "HEAD_BEFORE": head, "HEAD_AFTER": head, "HISTORY_COUNT_BEFORE": "1",
        "HISTORY_COUNT_AFTER": "1", "REFS_DELETED": "0", "REFS_REMAINING": "1", "REMOTES": "0",
        "REFLOG_ENTRIES": "0", "UNREACHABLE_OBJECTS": "0", "SECONDS_ELAPSED": "0.01",
    }
    facts.update(overrides or {})
    return "".join(f"{k}={v}\n" for k, v in facts.items())


# ---------------------------------------------------------------------------
# 替身分派
# ---------------------------------------------------------------------------


@dataclass
class ProfileFakeState:
    """W3b profile 路径的替身状态 + 负例旋钮。"""

    head: str
    rollout_profile: RolloutSandboxProfile | None = None
    grader_profile: GraderSandboxProfile | None = None
    # 旋钮
    probe_overrides: dict[str, str] = field(default_factory=dict)  # rollout 探针事实覆盖（负例）
    grader_probe_overrides: dict[str, str] = field(default_factory=dict)
    sanitize_overrides: dict[str, str] = field(default_factory=dict)
    inspect_mutator: Callable[[dict[str, Any]], None] | None = None  # 篡改合成 inspect（负例）
    network_create_fail: str | None = None  # 非 None = `network create` 失败的 stderr
    network_create_overlap_times: int = 0  # 前 N 次报 "Pool overlaps"
    relay_missing: bool = False  # `network connect` 报 No such container
    trusted_init_fail: bool = False
    # F4 负例旋钮
    network_ls_fail: bool = False  # `network ls` 查询失败（守护进程不可达）
    network_rm_fail_for: tuple[str, ...] = ()  # 这些网络（或 "*"）`network rm` 失败（active endpoints）
    # R2 负例旋钮：relay 实际镜像的 RepoDigests（None = 恰好等于 profile 钉死值）
    relay_repo_digests: tuple[str, ...] | None = None
    # 记录
    networks: dict[str, str] = field(default_factory=dict)  # name → subnet
    removed_networks: list[str] = field(default_factory=list)
    relay_connections: list[tuple[str, str]] = field(default_factory=list)  # (network, relay)
    relay_disconnections: list[tuple[str, str]] = field(default_factory=list)
    run_args_by_name: dict[str, tuple[str, ...]] = field(default_factory=dict)
    exec_scripts: list[tuple[str, str | None, str]] = field(default_factory=list)  # (container, user, script_id)
    overlap_seen: int = 0

    def dispatch(self, args: tuple[str, ...], input_bytes: bytes | None = None) -> ExecResult | None:
        """认识的 profile 路径命令返回结果；不认识的返回 None（交给宿主替身）。"""

        cmd = args[0]
        if cmd == "network":
            return self._network(args)
        if cmd == "run":
            name = args[args.index("--name") + 1]
            self.run_args_by_name[name] = tuple(args)
            return None  # 宿主替身决定成功/失败
        if cmd == "inspect" and "{{.Image}}" in args and str(args[-1]).startswith("rh2-egress-relay"):
            return ExecResult(0, RELAY_FAKE_IMAGE_ID + "\n", "")  # R2：relay 容器实际镜像 ID
        if cmd == "image" and "RepoDigests" in " ".join(args) and args[-1] == RELAY_FAKE_IMAGE_ID:
            import json as _json

            digests = self.relay_repo_digests
            if digests is None:
                assert self.rollout_profile is not None
                digests = (self.rollout_profile.relay_image,)
            return ExecResult(0, _json.dumps(list(digests)) + "\n", "")
        if cmd == "inspect" and len(args) == 2:  # 裸 `inspect <name>`（{{.Image}} 形态归宿主替身）
            name = args[1]
            run_args = self.run_args_by_name.get(name)
            if run_args is None:
                return ExecResult(1, "", f"Error: No such object: {name}")
            payload = synthesize_inspect(run_args, name=name)
            if self.inspect_mutator is not None:
                self.inspect_mutator(payload)
            import json as _json

            return ExecResult(0, _json.dumps([payload]) + "\n", "")
        if cmd == "exec":
            script = args[-1]
            sid = script_id_of(script)
            if sid is None:
                return None
            user = None
            if "-u" in args:
                user = args[args.index("-u") + 1]
            name = args[args.index("bash") - 1]
            self.exec_scripts.append((name, user, sid))
            return self._exec_script(sid, user)
        return None

    def _network(self, args: tuple[str, ...]) -> ExecResult:
        sub = args[1]
        if sub == "create":
            name = args[-1]
            subnet = args[args.index("--subnet") + 1]
            if self.network_create_fail is not None:
                return ExecResult(1, "", self.network_create_fail)
            if self.overlap_seen < self.network_create_overlap_times:
                self.overlap_seen += 1
                return ExecResult(1, "", "Error response from daemon: invalid pool request: Pool overlaps with other one on this address space")
            self.networks[name] = subnet
            return ExecResult(0, "deadbeef" * 8 + "\n", "")
        if sub == "connect":
            network, relay = args[-2], args[-1]
            if self.relay_missing:
                return ExecResult(1, "", f"Error response from daemon: No such container: {relay}")
            if network not in self.networks:
                return ExecResult(1, "", f"Error response from daemon: network {network} not found")
            self.relay_connections.append((network, relay))
            return ExecResult(0, "", "")
        if sub == "disconnect":
            network, relay = args[-2], args[-1]
            self.relay_disconnections.append((network, relay))
            return ExecResult(0, "", "")
        if sub == "rm":
            name = args[-1]
            if "*" in self.network_rm_fail_for or name in self.network_rm_fail_for:
                return ExecResult(1, "", f"Error response from daemon: error while removing network: network {name} has active endpoints")
            if name in self.networks:
                del self.networks[name]
                self.removed_networks.append(name)
                return ExecResult(0, name + "\n", "")
            return ExecResult(1, "", f"Error response from daemon: network {name} not found")
        if sub == "ls":
            if self.network_ls_fail:
                return ExecResult(1, "", "Cannot connect to the Docker daemon at unix:///var/run/docker.sock")
            return ExecResult(0, "".join(n + "\n" for n in self.networks), "")
        raise AssertionError(f"ProfileFakeState 不认识的 network 子命令: {args}")

    def _exec_script(self, sid: str, user: str | None) -> ExecResult:
        rp = self.rollout_profile
        gp = self.grader_profile
        if sid == "rollout-trusted-init":
            if self.trusted_init_fail:
                return ExecResult(4, "RH2_INIT_ERROR=chown_workdir_failed\n", "chown: Operation not permitted")
            assert rp is not None
            return ExecResult(0, f"RH2_INIT_OK=1\nAGENT_UID={rp.agent_uid}\nWORKDIR_PRESENT=1\n", "")
        if sid == "git-sanitize":
            out = git_sanitize_output(self.head, overrides=self.sanitize_overrides)
            code = 0 if "RH2_GIT_SANITIZE_OK=1" in out else 2
            return ExecResult(code, out, "")
        if sid == "rollout-prelaunch-probe":
            assert rp is not None
            return ExecResult(0, rollout_probe_output(rp, head=self.head, overrides=self.probe_overrides), "")
        if sid == "rollout-extended-probe":
            return ExecResult(0, "ESCALATE_SU=DENIED\nESCALATE_SETUID=DENIED\nSU_SETUID_BIT=1\nPROXY_HTTP=HTTP/1.1 404 Not Found\nRH2_PROBE_OK=1\n", "")
        if sid == "grader-trusted-init":
            if self.trusted_init_fail:
                return ExecResult(4, "RH2_INIT_ERROR=chown_home_failed\n", "chown: Operation not permitted")
            assert gp is not None
            return ExecResult(0, f"RH2_INIT_OK=1\nGRADER_UID={gp.candidate_exec_uid}\n", "")
        if sid == "grader-prelaunch-probe":
            assert gp is not None
            return ExecResult(0, grader_probe_output(gp, overrides=self.grader_probe_overrides), "")
        if sid == "grader-protect-control-surface":
            return ExecResult(0, "RH2_PROTECT_OK=1\nPROTECTED_FILES=1\nPROTECTED_DIRS=2\nMISSING_FILES=\nTESTBED_STAT=0 1777\n", "")
        if sid == "storage-quota-probe":
            return ExecResult(0, "QUOTA_ENFORCED=0\n", "")
        if sid == "git-future-probe":
            return ExecResult(0, (
                "FUTURE_BEFORE=RECOVERABLE\nSANITIZE_RH2_GIT_SANITIZE_OK=1\nSANITIZE_UNREACHABLE_OBJECTS=0\n"
                "FUTURE_CATFILE=GONE\nFUTURE_LOSTFOUND=0\nFUTURE_GREP=ABSENT\nFUTURE_TAG=GONE\nFUTURE_BRANCH=GONE\n"
                "BASE_HISTORY=1\nHEAD_IS_BASE=1\nRH2_PROBE_OK=1\n"
            ), "")
        raise AssertionError(f"ProfileFakeState 不认识的脚本 id: {sid}")


# ---------------------------------------------------------------------------
# bringup 级替身：relay 启动/就绪、verify 全流程、关停清理、label 残留可见（tests/adapters 与 tests/adapters_miles 共用）
# ---------------------------------------------------------------------------


class SandboxRuntimeFakeDocker:
    """relay 启动/就绪、verify 全流程、关停清理所需的最小 docker 面（其余交给 ProfileFakeState）。

    F4 旋钮：`network_ls_fail` / `network_rm_fail_for` / `relay_rm_fail` / `relay_never_ready`；
    `containers_with_label()` 模拟 launch trap 的 `docker ps -a --filter label=rh2.run_id=<id>`
    （被 rm 失败的容器仍在，残留检查看得见）。
    """

    def __init__(
        self,
        *,
        probe_overrides: dict[str, str] | None = None,
        network_ls_fail: bool = False,
        network_rm_fail_for: tuple[str, ...] = (),
        relay_rm_fail: bool = False,
        relay_never_ready: bool = False,
        relay_repo_digests: tuple[str, ...] | None = None,
    ) -> None:
        self.state = ProfileFakeState(
            head=BASE_COMMIT_FOR_RUNTIME_FAKE, rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(),
            probe_overrides=probe_overrides or {}, network_ls_fail=network_ls_fail,
            network_rm_fail_for=network_rm_fail_for, relay_repo_digests=relay_repo_digests,
        )
        self.relay_rm_fail = relay_rm_fail
        self.relay_never_ready = relay_never_ready
        self.calls: list[tuple[str, ...]] = []
        self.removed: list[str] = []
        self.containers: dict[str, dict[str, Any]] = {}  # name → {"labels": {...}, "removed": bool}

    def bind_profiles(self, rollout, grader) -> None:
        self.state.rollout_profile = rollout
        self.state.grader_profile = grader

    def containers_with_label(self, label: str) -> list[str]:
        key, _, value = label.partition("=")
        return sorted(
            name for name, c in self.containers.items() if not c["removed"] and c["labels"].get(key) == value
        )

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        handled = self.state.dispatch(args, input_bytes)
        if handled is not None:
            return handled
        cmd = args[0]
        if cmd == "run":
            name = args[args.index("--name") + 1]
            labels: dict[str, str] = {}
            for i, a in enumerate(args):
                if a == "--label" and i + 1 < len(args):
                    k, _, v = args[i + 1].partition("=")
                    labels[k] = v
            self.containers[name] = {"labels": labels, "removed": False}
            return ExecResult(0, "deadbeef\n", "")
        if cmd == "rm":
            name = args[-1]
            if self.relay_rm_fail and name.startswith("rh2-egress-relay-"):
                return ExecResult(1, "", f"Error response from daemon: cannot remove container {name}: device or resource busy")
            self.removed.append(name)
            if name in self.containers:
                self.containers[name]["removed"] = True
            return ExecResult(0, "", "")
        if cmd == "ps":
            label = ""
            for i, a in enumerate(args):
                if a == "--filter" and i + 1 < len(args) and args[i + 1].startswith("label="):
                    label = args[i + 1][len("label="):]
            names = self.containers_with_label(label) if label else [n for n, c in self.containers.items() if not c["removed"]]
            return ExecResult(0, "".join(n + "\n" for n in names), "")
        if cmd == "exec":
            script = args[-1]
            if "RH2_RELAY_LISTENING" in script:
                if self.relay_never_ready:
                    return ExecResult(1, "", "ConnectionRefusedError: [Errno 111] Connection refused")
                return ExecResult(0, "RH2_RELAY_LISTENING\n", "")
            if "test -d" in script and "/.git" in script:
                return ExecResult(0, "", "")  # 探针镜像无 /testbed → sanitize 如实 skipped
            return ExecResult(0, "", "")
        raise AssertionError(f"SandboxRuntimeFakeDocker 不认识的命令: {args}")
