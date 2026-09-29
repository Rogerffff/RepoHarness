"""场景 7（代码审读疑点的最小复现，假 daemon）：unix socket 上的可编排 HTTP 服务，逐项攻击收集器的边界。

每个用例只记录观测到的形态（异常类型 / exec_state / progress / 文件内容 / 耗时），结论在报告里判定。
不需要真实 Docker；Linux 与 macOS 都可跑（F2 的 ECONNRESET 语义以 Linux 为准）。
"""

from __future__ import annotations

import asyncio
import inspect as pyinspect
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("IR1_RESULTS", str(HERE / "results"))
from repoharness2.adapters.slime import docker_sandbox as ds  # noqa: E402

RESULTS = Path(os.environ["IR1_RESULTS"])
RESULTS.mkdir(parents=True, exist_ok=True)
EXEC_ID = "exec-fake-ir1"


def frame(t: int, payload: bytes) -> bytes:
    return bytes([t, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload


def http(status: int, payload: bytes = b"", *, reason: str = "X", extra: str = "") -> bytes:
    return f"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n{extra}\r\n".encode() + payload


UPGRADE = b"HTTP/1.1 101 UPGRADED\r\nContent-Type: application/vnd.docker.multiplexed-stream\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n"
CHUNKED200 = b"HTTP/1.1 200 OK\r\nContent-Type: application/vnd.docker.raw-stream\r\nTransfer-Encoding: chunked\r\n\r\n"

Handler = Callable[[str, str, bytes, asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]


class Fake:
    """路由：create / start / inspect 各一个协程；early(method, path, reader, writer) 在只读完请求行时调用，返回 True 即终止。"""

    def __init__(self, *, create: Handler | None = None, start: Handler | None = None, inspect: Handler | None = None,
                 early: Callable[..., Awaitable[bool]] | None = None) -> None:
        self.dir = tempfile.mkdtemp(prefix="ir1f", dir="/tmp")
        self.sock = f"{self.dir}/e.sock"
        self.create, self.start, self.inspect, self.early = create or ok_create, start, inspect or inspect_seq([{"Running": False, "ExitCode": 0}]), early
        self.calls: list[str] = []
        self.tasks: set[asyncio.Task] = set()

    async def __aenter__(self) -> "Fake":
        self.server = await asyncio.start_unix_server(self._handle, path=self.sock)
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self.server.close()
        for t in list(self.tasks):  # 3.12 的 wait_closed 会等所有连接处理结束：先取消仍挂着的处理协程
            t.cancel()
        await asyncio.wait_for(self.server.wait_closed(), 5)
        shutil.rmtree(self.dir, ignore_errors=True)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        me = asyncio.current_task()
        if me is not None:
            self.tasks.add(me)
        try:
            line = await reader.readline()
            if not line:
                return
            method, path, _ = line.decode().split(maxsplit=2)
            self.calls.append(f"{method} {path}")
            if self.early is not None and await self.early(method, path, reader, writer):
                return
            headers: dict[str, str] = {}
            while True:
                h = await reader.readline()
                if h in (b"\r\n", b"\n", b""):
                    break
                k, _, v = h.decode().partition(":")
                headers[k.strip().lower()] = v.strip()
            body = await reader.readexactly(int(headers.get("content-length", "0")))
            if method == "POST" and path.endswith("/exec"):
                await self.create(method, path, body, reader, writer)
            elif method == "POST" and path.endswith("/start"):
                await self.start(method, path, body, reader, writer)
            elif method == "GET" and path.endswith("/json"):
                await self.inspect(method, path, body, reader, writer)
        except (ConnectionError, OSError, asyncio.IncompleteReadError, asyncio.CancelledError):
            pass
        finally:
            if me is not None:
                self.tasks.discard(me)
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass


async def ok_create(method, path, body, reader, writer) -> None:
    writer.write(http(201, json.dumps({"Id": EXEC_ID}).encode()))
    await writer.drain()


def start_frames(frames: list[bytes], *, hold: bool = False, head: bytes = UPGRADE) -> Handler:
    async def h(method, path, body, reader, writer):
        writer.write(head)
        for data in frames:
            writer.write(data)
            await writer.drain()
        if hold:
            try:
                await reader.read()
            except (ConnectionError, OSError):
                pass
    return h


def inspect_seq(states: list[Any]) -> Handler:
    """逐次应答；元素：dict → 200 JSON；None → 404；int → 该 HTTP 状态；("hang", s) → 挂起 s 秒。"""
    calls = {"n": 0}

    async def h(method, path, body, reader, writer):
        st = states[min(calls["n"], len(states) - 1)]
        calls["n"] += 1
        if isinstance(st, tuple) and st[0] == "hang":
            await asyncio.sleep(st[1])
            return
        if st is None:
            writer.write(http(404, b'{"message":"No such exec instance"}'))
        elif isinstance(st, int):
            writer.write(http(st, b'{"message":"boom"}'))
        else:
            writer.write(http(200, json.dumps({"ID": EXEC_ID, "Pid": 1, **st}).encode()))
        await writer.drain()
    h.calls = calls  # type: ignore[attr-defined]
    return h


async def collect(fake: Fake, tmp: Path, *, deadline: float = 10.0, settle: float = 0.6, progress: dict | None = None) -> dict:
    t = time.monotonic()
    rec: dict[str, Any] = {}
    try:
        run = await ds.run_exec_collected(
            container_name="c1", user="agent", workdir="/testbed", env={"HOME": "/home/agent"}, cmd="exec claude",
            stdout_path=tmp / "out", stderr_path=tmp / "err", deadline_seconds=deadline, socket_path=fake.sock,
            settle_seconds=settle, progress=progress,
        )
        rec["result"] = {k: v for k, v in run.facts().items() if k not in ("stdout_path", "stderr_path")}
    except asyncio.CancelledError:
        rec["raised_type"] = "CancelledError"
        raise
    except BaseException as exc:  # noqa: BLE001
        rec["raised_type"] = type(exc).__name__
        rec["raised"] = f"{type(exc).__name__}: {exc}"[:300]
        rec["is_engine_api_error"] = isinstance(exc, ds.EngineApiError)
    finally:
        rec["wall"] = round(time.monotonic() - t, 3)
        if progress is not None:
            rec["progress"] = {k: v for k, v in progress.items() if k not in ("stdout_path", "stderr_path")}
    rec["out"] = (tmp / "out").read_bytes().decode(errors="replace") if (tmp / "out").exists() else None
    rec["err"] = (tmp / "err").read_bytes().decode(errors="replace") if (tmp / "err").exists() else None
    return rec


def tmpdir(tag: str) -> Path:
    p = Path(tempfile.mkdtemp(prefix=f"ir1-{tag}-"))
    return p


# ------------------------------------------------------------------------------------------------ cases


async def f1_hijack_timeout_escapes_unwrapped() -> dict:
    """exec create 成功、exec start 的响应头迟迟不来（daemon 卡住）：engine_hijack 抛什么？经真实 driver 变成什么？"""
    async def hang(method, path, body, reader, writer):
        await asyncio.sleep(3600)

    kw = ds.engine_hijack.__kwdefaults__
    saved = dict(kw)
    kw["timeout"] = 1.0  # 只把本进程里 hijack 的 30 s 默认超时缩到 1 s（真实 daemon 上 30 s 的同一形态见 s2 c_ghost）
    out: dict[str, Any] = {}
    try:
        async with Fake(start=hang) as fake:
            out["collector"] = await collect(fake, tmpdir("f1"), progress={})
            # 端到端：经真实 ClaudeCodeDriver.run（引导步骤替身，与维护测试同法）
            from repoharness2.adapters.slime import bringup
            from repoharness2.adapters.slime.generate import FAILURE_CODE_TERMINATION_MAP, RolloutOrchestrator, SlimeBindingError

            async def install(self, sb, **kwargs):
                return None

            async def fast_run(*args, input_bytes=None, timeout=None):
                return 0, "", ""

            saved_install, saved_run = bringup.ClaudeCodeDriver._install_native_cli, ds._run
            bringup.ClaudeCodeDriver._install_native_cli, ds._run = install, fast_run
            os.environ["SLIME_AGENT_CC_EXTRA_ENVS"] = "{}"
            os.environ["DOCKER_HOST"] = f"unix://{fake.sock}"
            try:
                await bringup.ClaudeCodeDriver().run(type("S", (), {"container_name": "c"})(), workdir="/testbed",
                                                     session_id="tok", adapter_url="http://relay:1", time_budget_sec=100,
                                                     prompt="p", harness_log_dir=str(tmpdir("f1drv")))
                out["driver"] = {"returned": True}
            except BaseException as exc:  # noqa: BLE001
                attributed = RolloutOrchestrator._pre_finalize_exception_is_attributed(
                    SimpleNamespace(_mode="fa_formal"), exc, audit=SimpleNamespace(finalized=None))
                out["driver"] = {"raised_type": type(exc).__name__, "raised": str(exc)[:200],
                                 "is_slime_binding_error": isinstance(exc, SlimeBindingError),
                                 "reason_code": getattr(exc, "reason_code", None),
                                 "orchestrator_pre_finalize_attributed": attributed,
                                 "consequence": "ABORTED(task-local)" if attributed else "pre_finalize_failure_unclassified → run-halt"}
                out["reference_create_404_through_driver"] = None
            finally:
                bringup.ClaudeCodeDriver._install_native_cli, ds._run = saved_install, saved_run
                os.environ.pop("DOCKER_HOST", None)
            out["map_has_bootstrap_failed"] = "harness_bootstrap_failed" in FAILURE_CODE_TERMINATION_MAP
    finally:
        kw.clear()
        kw.update(saved)
    return out


async def f2_hijack_reset_escapes_unwrapped() -> dict:
    """daemon 在 exec start 请求未读完时断开（RST）：engine_hijack 抛什么？"""
    async def early(method, path, reader, writer):
        if path.endswith("/start"):
            writer.transport.abort()  # 请求头 / 体仍在对端未读 → 客户端读到 ECONNRESET（Linux）或 EOF
            return True
        return False

    async with Fake(early=early, start=start_frames([])) as fake:
        return {"collector": await collect(fake, tmpdir("f2"), progress={})}


async def f3_chunked_truncation_is_returned_as_complete() -> dict:
    async def chunked_trunc(method, path, body, reader, writer):
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\n"
                     b"1c\r\n{\"Running\":false,\"ExitCode\":\r\n")  # 截断：没有后续 chunk、没有 0\r\n\r\n
        await writer.drain()

    async with Fake(inspect=chunked_trunc) as fake:
        st, _h, payload = await ds.engine_request("GET", f"{ds._ENGINE_API}/exec/{EXEC_ID}/json", socket_path=fake.sock, timeout=2)
        inspected = await ds._inspect_exec(EXEC_ID, socket_path=fake.sock, timeout=2)
    return {"engine_request_returned": {"status": st, "payload": payload.decode()}, "inspect_exec": inspected}


async def f4_malformed_chunk_in_create_escapes_as_value_error() -> dict:
    async def bad_create(method, path, body, reader, writer):
        writer.write(b"HTTP/1.1 201 Created\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\n\r\nzz\r\n{}\r\n0\r\n\r\n")
        await writer.drain()

    async with Fake(create=bad_create, start=start_frames([])) as fake:
        return {"collector": await collect(fake, tmpdir("f4"), progress={})}


async def f5_pump_exception_leaves_progress_streaming() -> dict:
    async def start(method, path, body, reader, writer):
        writer.write(CHUNKED200)
        data = frame(1, b"partial\n")
        writer.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
        writer.write(b"zz\r\n")  # 畸形 chunk 大小行
        await writer.drain()
        await asyncio.sleep(1)

    progress: dict = {}
    async with Fake(start=start) as fake:
        rec = await collect(fake, tmpdir("f5"), progress=progress)
    return {"collector": rec}


async def f6_cancel_during_time_budget_inspect() -> dict:
    progress: dict = {}
    async with Fake(start=start_frames([frame(1, b"started\n")], hold=True), inspect=inspect_seq([("hang", 10)])) as fake:
        task = asyncio.create_task(collect(fake, tmpdir("f6"), deadline=0.3, progress=progress))
        await asyncio.sleep(1.0)  # 期限 0.3 s 已到，此刻在那次 2 s 有界 inspect 里
        in_inspect = dict(progress)
        task.cancel()
        try:
            await task
            outcome = "returned"
        except asyncio.CancelledError:
            outcome = "CancelledError"
    return {"outcome": outcome, "progress_while_in_budget_inspect": {k: in_inspect.get(k) for k in ("exec_state", "exit_code")},
            "progress_after_cancel": {k: progress.get(k) for k in ("exec_state", "exit_code", "log_partial_reason", "log_complete")}}


async def f7_exit_code_above_255_accepted() -> dict:
    rows = {}
    for code in (255, 256, 4096, 2147483647):
        async with Fake(start=start_frames([frame(1, b"x\n")]), inspect=inspect_seq([{"Running": False, "ExitCode": code}])) as fake:
            rec = await collect(fake, tmpdir("f7"))
        rows[str(code)] = {k: (rec.get("result") or {}).get(k) for k in ("exec_state", "exit_code", "log_complete")}
    return rows


async def f8_frame_types_0_and_3_dropped_silently() -> dict:
    frames = [frame(3, b"SYSTEM-ERROR-TEXT\n"), frame(0, b"stdin?"), frame(1, b"ok\n"), frame(2, b"e\n"), frame(7, b"??")]
    async with Fake(start=start_frames(frames)) as fake:
        rec = await collect(fake, tmpdir("f8"))
    res = rec["result"]
    return {"out": rec["out"], "err": rec["err"], "stdout_bytes": res["stdout_bytes"], "stderr_bytes": res["stderr_bytes"],
            "stderr_tail": res["stderr_tail"], "log_complete": res["log_complete"], "exec_state": res["exec_state"]}


async def f9_byte_by_byte_headers_split_across_reads() -> dict:
    payloads = [(1, b'{"i":%d}\n' % i) for i in range(50)] + [(2, b"E" * 70000), (1, b"L" * 131073 + b"\n")]
    stream = b"".join(frame(t, p) for t, p in payloads)

    async def upgrade_trickle(method, path, body, reader, writer):
        writer.write(UPGRADE)
        for i in range(0, len(stream), 7):  # 7 字节一写：帧头必然跨读
            writer.write(stream[i:i + 7])
            if i % 700 == 0:
                await writer.drain()
                await asyncio.sleep(0)
        await writer.drain()

    async def chunked_trickle(method, path, body, reader, writer):
        writer.write(CHUNKED200)
        for i in range(0, len(stream), 5):  # 5 字节一个 chunk：chunk 边界落在帧头中间
            piece = stream[i:i + 5]
            writer.write(f"{len(piece):x}\r\n".encode() + piece + b"\r\n")
        writer.write(b"0\r\n\r\n")
        await writer.drain()

    want_out = b"".join(p for t, p in payloads if t == 1)
    want_err = b"".join(p for t, p in payloads if t == 2)
    out = {}
    for name, h in (("upgrade_7B_writes", upgrade_trickle), ("chunked_5B_chunks", chunked_trickle)):
        d = tmpdir("f9")
        async with Fake(start=h) as fake:
            rec = await collect(fake, d, deadline=60)
        out[name] = {"exec_state": rec["result"]["exec_state"], "stdout_exact": (d / "out").read_bytes() == want_out,
                     "stderr_exact": (d / "err").read_bytes() == want_err, "stdout_bytes": rec["result"]["stdout_bytes"],
                     "wall": rec["wall"]}
    return out


async def f10_bounded_inspect_is_per_phase() -> dict:
    async def slow(method, path, body, reader, writer):
        payload = json.dumps({"ID": EXEC_ID, "Running": True, "ExitCode": None, "Pid": 1}).encode()
        await asyncio.sleep(1.9)
        writer.write(f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n".encode())
        await writer.drain()
        await asyncio.sleep(1.9)
        writer.write(payload)
        await writer.drain()

    async with Fake(inspect=slow) as fake:
        t = time.monotonic()
        state = await ds._inspect_exec(EXEC_ID, socket_path=fake.sock, timeout=ds._TIME_BUDGET_INSPECT_SECONDS)
        took = round(time.monotonic() - t, 3)
    return {"timeout_constant": ds._TIME_BUDGET_INSPECT_SECONDS, "took_s": took, "state": state}


async def f12_settle_with_intermittent_inspect_failures() -> dict:
    out = {}
    seqs = {
        "running_500_404_then_exited4": [{"Running": True, "ExitCode": None}, 500, None, {"Running": False, "ExitCode": 4}],
        "running_then_only_500s": [{"Running": True, "ExitCode": None}, 500],
        "never_started_shape": [{"Running": False, "ExitCode": None}],
    }
    for name, seq in seqs.items():
        async with Fake(start=start_frames([frame(1, b"x\n")]), inspect=inspect_seq(seq)) as fake:
            rec = await collect(fake, tmpdir("f12"), settle=1.5)
        res = rec["result"]
        out[name] = {k: res.get(k) for k in ("exec_state", "exit_code", "inspect", "log_partial_reason")}
    return out


async def f13_append_mode_mixes_runs() -> dict:
    d = tmpdir("f13")
    res = []
    for payload in (b"attempt-1 line\n" * 3, b"attempt-2\n"):
        async with Fake(start=start_frames([frame(1, payload)])) as fake:
            res.append((await collect(fake, d))["result"])
    return {"second_run_stdout_bytes": res[1]["stdout_bytes"], "second_run_log_complete": res[1]["log_complete"],
            "file_size": (d / "out").stat().st_size, "file_content": (d / "out").read_text()}


async def f14_progress_before_stream_start() -> dict:
    async def slow_create(method, path, body, reader, writer):
        await asyncio.sleep(1.0)
        await ok_create(method, path, body, reader, writer)

    progress: dict = {}
    async with Fake(create=slow_create, start=start_frames([frame(1, b"x\n")])) as fake:
        task = asyncio.create_task(collect(fake, tmpdir("f14"), progress=progress))
        await asyncio.sleep(0.5)
        during_create = dict(progress)
        await task
    return {"progress_during_exec_create": during_create, "progress_after": {k: progress.get(k) for k in ("exec_state", "exit_code")}}


def f15_settle_default_is_bound_at_definition() -> dict:
    saved = ds._EXEC_SETTLE_SECONDS
    ds._EXEC_SETTLE_SECONDS = 0.4
    try:
        default = pyinspect.signature(ds.run_exec_collected).parameters["settle_seconds"].default
    finally:
        ds._EXEC_SETTLE_SECONDS = saved
    return {"module_constant_patched_to": 0.4, "run_exec_collected_default_still": default,
            "hijack_timeout_default": ds.engine_hijack.__kwdefaults__["timeout"]}


BIG = 256 * 1024 * 1024


def f11_big_frame_memory_child() -> None:
    """子进程：假 daemon 宣告并发送一帧 256 MiB；测收集器进程的峰值 RSS。"""
    async def run():
        async def start(method, path, body, reader, writer):
            writer.write(UPGRADE + bytes([1, 0, 0, 0]) + BIG.to_bytes(4, "big"))
            chunk = b"z" * (1 << 20)
            for _ in range(BIG >> 20):
                writer.write(chunk)
                await writer.drain()

        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        async with Fake(start=start) as fake:
            rec = await collect(fake, tmpdir("f11"), deadline=120)
        after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        scale = 1 if sys.platform == "darwin" else 1024  # darwin: bytes；linux: KiB
        print(json.dumps({"frame_bytes": BIG, "maxrss_before_mib": round(before * scale / 2**20, 1),
                          "maxrss_after_mib": round(after * scale / 2**20, 1), "stdout_bytes": rec["result"]["stdout_bytes"],
                          "exec_state": rec["result"]["exec_state"]}))
    asyncio.run(run())


async def main() -> None:
    results: dict[str, Any] = {"python": sys.version.split()[0], "platform": sys.platform,
                               "collector_sha256": __import__("hashlib").sha256(Path(ds.__file__).read_bytes()).hexdigest()}
    for fn in (f1_hijack_timeout_escapes_unwrapped, f2_hijack_reset_escapes_unwrapped, f3_chunked_truncation_is_returned_as_complete,
               f4_malformed_chunk_in_create_escapes_as_value_error, f5_pump_exception_leaves_progress_streaming,
               f6_cancel_during_time_budget_inspect, f7_exit_code_above_255_accepted, f8_frame_types_0_and_3_dropped_silently,
               f9_byte_by_byte_headers_split_across_reads, f10_bounded_inspect_is_per_phase,
               f12_settle_with_intermittent_inspect_failures, f13_append_mode_mixes_runs, f14_progress_before_stream_start):
        try:
            results[fn.__name__] = await fn()
        except BaseException as exc:  # noqa: BLE001 - 探针自身失败也记下
            results[fn.__name__] = {"probe_error": f"{type(exc).__name__}: {exc}"}
        print(f"[ir1] {fn.__name__} done", file=sys.stderr)
    results["f15_settle_default_is_bound_at_definition"] = f15_settle_default_is_bound_at_definition()
    child = subprocess.run([sys.executable, __file__, "--f11"], capture_output=True, text=True, timeout=300)
    results["f11_big_frame_memory"] = json.loads(child.stdout.strip().splitlines()[-1]) if child.returncode == 0 else {
        "probe_error": child.stderr[-400:]}
    tag = os.environ.get("IR1_TAG", sys.platform)
    path = RESULTS / f"s7_fake_daemon_{tag}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    print(f"[ir1] wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    if "--f11" in sys.argv:
        f11_big_frame_memory_child()
    else:
        asyncio.run(main())
