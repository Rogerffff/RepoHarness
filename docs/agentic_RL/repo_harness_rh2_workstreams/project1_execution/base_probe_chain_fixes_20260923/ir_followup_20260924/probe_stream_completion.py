"""独立复核：损坏的 Engine 帧流与可信 exec 终态应分别表达。

从 rh2/ 运行：
  .venv/bin/python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/base_probe_chain_fixes_20260923/ir_followup_20260924/probe_stream_completion.py

只替换 Unix socket 上的 daemon；运行真实 create/start/inspect 和收集器。
输出是当前实现的观测值，不把已发现的错误行为固化为通过标准。
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import tempfile

from repoharness2.adapters.slime.docker_sandbox import run_exec_collected


def frame(payload: bytes) -> bytes:
    return bytes([1, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload


async def one_case(name: str, stream: bytes, *, chunked: bool = False) -> dict:
    requests: list[str] = []
    with tempfile.TemporaryDirectory(prefix="irfollow", dir="/tmp") as tmp:
        root = Path(tmp)
        socket_path = root / "engine.sock"

        async def daemon(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                method, path, _ = (await reader.readline()).decode().split()
                headers: dict[str, str] = {}
                while True:
                    line = await reader.readline()
                    if line in (b"", b"\r\n"):
                        break
                    key, value = line.decode().split(":", 1)
                    headers[key.lower()] = value.strip()
                await reader.readexactly(int(headers.get("content-length", "0")))
                requests.append(f"{method} {path}")
                if path.endswith("/exec"):
                    code, data = 201, {"Id": "same-exec-id"}
                elif path.endswith("/start"):
                    if chunked:
                        head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
                    else:
                        head = b"HTTP/1.1 101 UPGRADED\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n\r\n"
                    writer.write(head + stream)
                    await writer.drain()
                    return
                elif path == "/v1.44/exec/same-exec-id/json":
                    code, data = 200, {"ID": "same-exec-id", "Running": False, "ExitCode": 0, "Pid": 123}
                else:
                    code, data = 404, {"message": "unexpected request"}
                body = json.dumps(data).encode()
                writer.write(f"HTTP/1.1 {code} X\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body)
                await writer.drain()
            finally:
                writer.close()

        server = await asyncio.start_unix_server(daemon, path=socket_path)
        try:
            result = await run_exec_collected(
                container_name="review-only", user="agent", workdir="/testbed", env={},
                cmd="exec claude", stdout_path=root / "stdout.jsonl", stderr_path=root / "stderr.log",
                deadline_seconds=2, settle_seconds=0.5, socket_path=str(socket_path),
            )
            record = asdict(result)
            keep = ("exec_id", "exec_state", "exit_code", "stdout_bytes", "stderr_bytes", "log_complete",
                    "log_partial_reason", "stream_error", "inspect")
            return {"case": name, "requests": requests, **{key: record[key] for key in keep},
                    "stdout": (root / "stdout.jsonl").read_text()}
        finally:
            server.close()
            await server.wait_closed()


async def main() -> None:
    good = frame(b"good\n")
    chunk = f"{len(good):x}\r\n".encode() + good + b"\r\n"
    cases = [
        ("valid_raw", good, False),
        ("truncated_frame_header", good + b"\x01\x00\x00", False),
        ("truncated_frame_payload", good + bytes([1, 0, 0, 0]) + (9).to_bytes(4, "big") + b"cut", False),
        ("valid_chunked", chunk + b"0\r\n\r\n", True),
        ("chunked_missing_terminator", chunk, True),
        ("chunked_invalid_size", chunk + b"not-hex\r\n", True),
    ]
    observations = [await one_case(name, wire, chunked=chunked) for name, wire, chunked in cases]
    print(json.dumps({"scope": "Unix fake daemon; actual collector; all inspect states terminal exit 0",
                      "cases": observations}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
