"""补强 D1：exec start 阶段的超时 / 连接重置，经**正式编排**（fa_formal 链，维护测试的同一夹具）最终变成什么。

链路：RolloutOrchestrator.generate → 真实 ClaudeCodeDriver.run → launch_claude_code → run_exec_collected → 假 daemon：
  start_timeout：exec create 正常，exec start 不回响应头（本进程把 engine_hijack 的 30 s 默认超时缩到 1 s）
  start_reset  ：exec create 正常，exec start 连接被对端未读即关闭（Linux ECONNRESET）
  control_create_404：exec create 回 404（对照：设计上的"起执行失败" → harness_bootstrap_failed，task-local）
引导步骤替身与维护测试相同（_install_native_cli 空实现、ds._run 快速成功）。只读取结果，不改生产代码。
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[2]
sys.path.insert(0, str(RH2 / "tests" / "adapters"))
sys.path.insert(0, str(HERE))
os.environ.setdefault("IR1_RESULTS", str(HERE / "results"))

from test_slime_generate import SAMPLING_PARAMS, FakeFinalizationStore, _Args  # noqa: E402
from test_w1b_termination_facts_producer import _formal_chain  # noqa: E402

from repoharness2.adapters.slime import bringup  # noqa: E402
from repoharness2.adapters.slime import docker_sandbox as ds  # noqa: E402


def serve(path: str, plan: list[str]) -> None:
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(16)

    def run():
        for step in plan:
            conn, _ = srv.accept()
            if step in ("create", "create404"):
                buf = b""
                while b"\r\n\r\n" not in buf:
                    buf += conn.recv(65536)
                head, _, rest = buf.partition(b"\r\n\r\n")
                n = int([ln.split(b":")[1] for ln in head.split(b"\r\n") if ln.lower().startswith(b"content-length")][0])
                while len(rest) < n:
                    rest += conn.recv(65536)
                if step == "create":
                    body, status = json.dumps({"Id": "exec-s9"}).encode(), b"201 Created"
                else:
                    body, status = b'{"message":"No such container: c1"}', b"404 Not Found"
                conn.sendall(b"HTTP/1.1 " + status + b"\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
                conn.close()
            elif step == "hang":
                time.sleep(5)  # 不回任何字节（客户端 1 s 超时）
                conn.close()
            elif step == "rst":
                time.sleep(0.3)  # 请求进入接收队列后不读即关 → 对端 ECONNRESET
                conn.close()
        srv.close()

    threading.Thread(target=run, daemon=True).start()


class RealDriverOnFakeDaemon:
    name = "claude_code"

    def __init__(self) -> None:
        self.inner = bringup.ClaudeCodeDriver()

    async def run(self, sandbox, **kw):
        return await self.inner.run(type("S", (), {"container_name": "c1"})(), **kw)


async def case(kind: str) -> dict:
    d = tempfile.mkdtemp(prefix="ir1s9", dir="/tmp")
    sock = f"{d}/e.sock"
    serve(sock, {"start_timeout": ["create", "hang"], "start_reset": ["create", "rst"],
                 "control_create_404": ["create404"]}[kind])
    os.environ["DOCKER_HOST"] = f"unix://{sock}"
    os.environ["SLIME_AGENT_CC_EXTRA_ENVS"] = "{}"

    async def install(self, sb, **kwargs):
        return None

    async def fast_run(*args, input_bytes=None, timeout=None):
        return 0, "", ""

    saved = (bringup.ClaudeCodeDriver._install_native_cli, ds._run, dict(ds.engine_hijack.__kwdefaults__))
    bringup.ClaudeCodeDriver._install_native_cli, ds._run = install, fast_run
    ds.engine_hijack.__kwdefaults__["timeout"] = 1.0
    rec: dict = {"case": kind}
    try:
        chain = _formal_chain(FakeFinalizationStore())
        chain.orchestrator._harness_driver = RealDriverOnFakeDaemon()
        try:
            (out,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
            audit = chain.orchestrator.audits[0]
            rec["generate"] = "returned"
            rec["sample_status"] = str(getattr(out, "status", None))
            rec["remove_sample"] = getattr(out, "remove_sample", None)
            rec["outcome_reason_code"] = (audit.outcome_v2 or {}).get("reason_code")
            rec["completion_class"] = (audit.outcome_v2 or {}).get("completion_class")
        except BaseException as exc:  # noqa: BLE001
            rec["generate"] = "raised"
            rec["raised_type"] = type(exc).__name__
            rec["reason_code"] = getattr(exc, "reason_code", None)
            rec["raised"] = str(exc)[:400]
            cause = exc.__cause__
            rec["cause_type"] = type(cause).__name__ if cause else None
            audit = chain.orchestrator.audits[0] if chain.orchestrator.audits else None
        if audit is not None:
            rec["failure_records"] = [{"stage": f.stage, "error_type": f.error_type, "detail": f.detail[:160]}
                                      for f in audit.failure_records][:6]
            rec["harness_log"] = {k: (audit.harness_log or {}).get(k) for k in ("exec_id", "exec_state", "log_partial_reason")}
    finally:
        bringup.ClaudeCodeDriver._install_native_cli, ds._run = saved[0], saved[1]
        ds.engine_hijack.__kwdefaults__.clear()
        ds.engine_hijack.__kwdefaults__.update(saved[2])
        os.environ.pop("DOCKER_HOST", None)
    return rec


async def main() -> None:
    rows = [await case(k) for k in ("control_create_404", "start_timeout", "start_reset")]
    out = {"platform": sys.platform, "rows": rows}
    Path(os.environ["IR1_RESULTS"], f"s9_orchestrator_start_error_{sys.platform}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str))
    for r in rows:
        print(json.dumps(r, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
