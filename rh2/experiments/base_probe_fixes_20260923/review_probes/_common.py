"""IR1 对抗验证探针的共用工具（2026-09-24，独立验证者）。

只**调用**被测收集器 `repoharness2.adapters.slime.docker_sandbox.run_exec_collected`，不改生产代码；
需要观测内部时序时用可卸载的包装（InspectLog / FrameStats），包装只记录、原样返回。

约定：
- 本批创建的容器都带标签 `rh2.adv_ir1=1`，名字前缀 `ir1-`，结束时按标签清理；
- 结果 JSON 写到 `$IR1_RESULTS`（默认 `<本目录>/results`），临时文件在 `$IR1_TMP`；
- 镜像只用机器上已在场的（`--pull=never`）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RESULTS = Path(os.environ.get("IR1_RESULTS", str(HERE / "results")))
TMP = Path(os.environ.get("IR1_TMP", str(HERE / "tmp")))
RESULTS.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
IMAGE = os.environ.get("IR1_IMAGE", "xingyaoww/sweb.eval.x86_64.conan-io_s_conan-15422:latest")
LABEL = "rh2.adv_ir1=1"

from repoharness2.adapters.slime import docker_sandbox as ds  # noqa: E402


def sh(*args: str, timeout: float = 180, check: bool = False, input: str | None = None) -> subprocess.CompletedProcess:
    p = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout, input=input)
    if check and p.returncode != 0:
        raise RuntimeError(f"{args}: rc={p.returncode} {p.stderr[-400:]}")
    return p


def now() -> float:
    return time.monotonic()


def new_container(prefix: str, *, init: bool = True, extra: tuple[str, ...] = ()) -> str:
    """仿正式 rollout profile 的关键参数：--init、--cap-drop ALL、no-new-privileges、主进程 sleep infinity。"""
    name = f"ir1-{prefix}-{uuid.uuid4().hex[:6]}"
    args = ["docker", "run", "-d", "--pull=never"]
    if init:
        args.append("--init")
    args += ["--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
             "--label", LABEL, *extra, "--name", name, IMAGE, "sleep", "infinity"]
    sh(*args, check=True)
    return name


def rm_container(name: str) -> None:
    sh("docker", "rm", "-f", name)


def container_state(name: str) -> str:
    p = sh("docker", "inspect", "-f", "{{.State.Status}} exit={{.State.ExitCode}} execs={{json .ExecIDs}}", name)
    return p.stdout.strip() if p.returncode == 0 else f"inspect_failed: {p.stderr.strip()[:200]}"


def procs(name: str) -> str:
    """容器内进程：pid + cmdline（不依赖 ps）。"""
    p = sh("docker", "exec", name, "bash", "-c",
           "for p in /proc/[0-9]*; do printf '%s ' ${p#/proc/}; tr '\\0' ' ' < $p/cmdline 2>/dev/null; echo; done")
    return p.stdout if p.returncode == 0 else f"exec_failed rc={p.returncode}: {p.stderr.strip()[:200]}"


async def exec_inspect_raw(exec_id: str | None, timeout: float = 5.0) -> dict[str, Any]:
    if not exec_id:
        return {"skipped": "no exec id"}
    try:
        st, _h, payload = await ds.engine_request("GET", f"{ds._ENGINE_API}/exec/{exec_id}/json", timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    if st != 200:
        return {"status": st, "body": payload.decode(errors="replace")[:200]}
    doc = json.loads(payload)
    return {"status": st, "Running": doc.get("Running"), "ExitCode": doc.get("ExitCode"), "Pid": doc.get("Pid")}


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def file_info(path: Path, *, head: int = 200) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    data = path.read_bytes()
    return {"exists": True, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "head": data[:head].decode(errors="replace"), "tail": data[-head:].decode(errors="replace")}


async def collect(container: str, outdir: Path, cmd: str, *, user: str = "root", workdir: str = "/tmp",
                  env: dict[str, str] | None = None, deadline: float = 30.0, progress: dict | None = None,
                  **kw: Any) -> dict[str, Any]:
    """跑一次被测收集器，返回 {result | raised, wall, progress}；CancelledError 不在这里吞。"""
    outdir.mkdir(parents=True, exist_ok=True)
    t = now()
    rec: dict[str, Any] = {"cmd": cmd, "deadline": deadline, "user": user}
    try:
        run = await ds.run_exec_collected(
            container_name=container, user=user, workdir=workdir, env=env or {"HOME": "/tmp"}, cmd=cmd,
            stdout_path=outdir / "out", stderr_path=outdir / "err", deadline_seconds=deadline, progress=progress, **kw,
        )
        rec["result"] = run.facts()
    except Exception as exc:  # noqa: BLE001 - 记录任何非取消异常的形态
        rec["raised"] = f"{type(exc).__name__}: {exc}"[:500]
        rec["raised_type"] = type(exc).__name__
    rec["wall"] = round(now() - t, 3)
    if progress is not None:
        rec["progress"] = json.loads(json.dumps(progress, default=str))
    return rec


class InspectLog:
    """包装 ds._inspect_exec：记录每次 inspect 的相对时刻、耗时、timeout 与结果（原样返回）。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._orig = ds._inspect_exec
        self.t0 = now()

    def install(self) -> "InspectLog":
        orig, log = self._orig, self

        async def wrapped(exec_id, *, socket_path, timeout):
            t = now()
            res = await orig(exec_id, socket_path=socket_path, timeout=timeout)
            log.calls.append({"t": round(t - log.t0, 3), "dur": round(now() - t, 3), "timeout": timeout, "result": res})
            return res

        ds._inspect_exec = wrapped
        return self

    def uninstall(self) -> None:
        ds._inspect_exec = self._orig


class FrameStats:
    """包装 ds._FrameSource.next_frame：按 source 实例统计帧数 / 各类型字节 / 最大帧。"""

    def __init__(self) -> None:
        self.by_source: dict[int, dict[str, Any]] = {}
        self._orig = ds._FrameSource.next_frame

    def install(self) -> "FrameStats":
        orig, stats = self._orig, self

        async def next_frame(src):
            fr = await orig(src)
            if fr is not None:
                st = stats.by_source.setdefault(id(src), {"frames": 0, "max_frame": 0, "bytes_by_type": {}})
                st["frames"] += 1
                st["max_frame"] = max(st["max_frame"], len(fr[1]))
                key = str(fr[0])
                st["bytes_by_type"][key] = st["bytes_by_type"].get(key, 0) + len(fr[1])
            return fr

        ds._FrameSource.next_frame = next_frame
        return self

    def uninstall(self) -> None:
        ds._FrameSource.next_frame = self._orig

    def summary(self) -> dict[str, Any]:
        vals = list(self.by_source.values())
        return {"sources": len(vals), "max_frame": max((v["max_frame"] for v in vals), default=0),
                "frames": sum(v["frames"] for v in vals),
                "types": sorted({t for v in vals for t in v["bytes_by_type"]})}


def dockerd_pid() -> int | None:
    p = sh("pidof", "dockerd")
    return int(p.stdout.split()[0]) if p.returncode == 0 and p.stdout.strip() else None


def dockerd_unix_conns() -> int:
    """dockerd 持有的已连接 unix socket 数（ss -xp；不含监听）。"""
    p = sh("ss", "-xpH", "state", "connected")
    return sum(1 for line in p.stdout.splitlines() if '"dockerd"' in line)


def wait_daemon(timeout: float = 120.0) -> float:
    t = now()
    while now() - t < timeout:
        if sh("docker", "info", "--format", "{{.ServerVersion}}", timeout=30).returncode == 0:
            return round(now() - t, 2)
        time.sleep(0.5)
    raise RuntimeError("docker daemon 未在期限内恢复")


def write_result(name: str, obj: Any) -> Path:
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str))
    print(f"[ir1] wrote {path}", file=sys.stderr)
    return path


def env_facts() -> dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "collector_sha256": sha256_file(Path(ds.__file__)),
        "docker": sh("docker", "version", "--format",
                     "client={{.Client.Version}} server={{.Server.Version}} api={{.Server.APIVersion}} "
                     "minapi={{.Server.MinAPIVersion}}").stdout.strip(),
        "live_restore": sh("docker", "info", "--format", "{{.LiveRestoreEnabled}}").stdout.strip(),
        "image": IMAGE,
        "engine_api_prefix": ds._ENGINE_API,
        "settle_seconds": ds._EXEC_SETTLE_SECONDS,
        "time_budget_inspect_seconds": ds._TIME_BUDGET_INSPECT_SECONDS,
    }


def cleanup_labelled() -> list[str]:
    ids = sh("docker", "ps", "-aq", "--filter", f"label={LABEL}").stdout.split()
    if ids:
        sh("docker", "rm", "-f", *ids)
    return ids


def run_main(coro) -> None:
    asyncio.run(coro)
