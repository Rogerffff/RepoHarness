"""F2b：exec start 请求被对端未读即关闭（Linux AF_UNIX：接收队列非空时关闭 → 对端 ECONNRESET）。

原始 socket 线程服务：第 1 个连接（exec create）正常回 201；第 2 个连接（exec start）等 0.3 s 让请求进内核队列，
然后**不读**直接 close。对照：同样的对端行为下 engine_request（GET inspect）会把 OSError 包成 EngineApiError。
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("IR1_RESULTS", str(Path(__file__).resolve().parent / "results"))
from repoharness2.adapters.slime import docker_sandbox as ds  # noqa: E402


def serve(path: str, plan: list[str]) -> threading.Thread:
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(8)

    def run():
        for step in plan:
            conn, _ = srv.accept()
            if step == "create":
                buf = b""
                while b"\r\n\r\n" not in buf:
                    buf += conn.recv(65536)
                head, _, rest = buf.partition(b"\r\n\r\n")
                n = int([l.split(b":")[1] for l in head.split(b"\r\n") if l.lower().startswith(b"content-length")][0])
                while len(rest) < n:
                    rest += conn.recv(65536)
                body = json.dumps({"Id": "exec-rst"}).encode()
                conn.sendall(b"HTTP/1.1 201 Created\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
                conn.close()
            else:  # "rst"：请求留在接收队列里不读，直接关闭
                time.sleep(0.3)
                conn.close()
        srv.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


async def main() -> None:
    out: dict = {"platform": sys.platform}
    d = tempfile.mkdtemp(prefix="ir1rst", dir="/tmp")
    sock = f"{d}/e.sock"
    serve(sock, ["create", "rst"])
    try:
        await ds.run_exec_collected(container_name="c1", user="agent", workdir="/t", env={}, cmd="true",
                                    stdout_path=Path(d) / "o", stderr_path=Path(d) / "e", deadline_seconds=5, socket_path=sock)
        out["run_exec_collected"] = "returned"
    except BaseException as exc:  # noqa: BLE001
        out["run_exec_collected"] = {"type": type(exc).__name__, "is_engine_api_error": isinstance(exc, ds.EngineApiError),
                                     "is_oserror": isinstance(exc, OSError), "msg": str(exc)[:200]}
    os.unlink(sock)
    serve(sock, ["rst"])
    try:
        await ds.engine_request("GET", "/v1.44/exec/x/json", socket_path=sock, timeout=5)
        out["engine_request_same_peer"] = "returned"
    except BaseException as exc:  # noqa: BLE001
        out["engine_request_same_peer"] = {"type": type(exc).__name__, "is_engine_api_error": isinstance(exc, ds.EngineApiError),
                                           "msg": str(exc)[:200]}
    Path(os.environ["IR1_RESULTS"], f"s7_rst_{sys.platform}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
