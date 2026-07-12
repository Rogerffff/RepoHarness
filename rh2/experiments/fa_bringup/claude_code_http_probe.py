"""Probe Claude Code HTTP retry and timeout behavior against a local fake API.

This experiment never contacts a real model provider. It starts a loopback-only
Anthropic Messages endpoint, points one Claude Code CLI process at it, and emits
a machine-readable result. The probe intentionally lives outside the rh2
runtime package: its observations are version-specific calibration evidence,
not a training correctness dependency.

Examples::

    python experiments/fa_bringup/claude_code_http_probe.py \
      --scenario delay_success --delay-seconds 30 --process-timeout-seconds 45

    python experiments/fa_bringup/claude_code_http_probe.py \
      --scenario http_500 --process-timeout-seconds 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import select
import signal
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal


Scenario = Literal[
    "delay_success",
    "http_500",
    "http_500_no_retry",
    "http_429",
    "http_404",
    "disconnect_before_headers",
    "partial_sse_disconnect",
    "partial_sse_hang",
    "hang_until_probe_timeout",
]


@dataclass
class RequestObservation:
    request_number: int
    received_offset_seconds: float
    path: str
    body_sha256: str
    body_bytes: int
    stream_requested: bool
    response_headers_offset_seconds: float | None = None
    response_status: int | None = None
    write_error: str | None = None


class ProbeState:
    def __init__(self, scenario: Scenario, delay_seconds: float) -> None:
        self.scenario = scenario
        self.delay_seconds = delay_seconds
        self.started_monotonic = time.monotonic()
        self.lock = threading.Lock()
        self.requests: list[RequestObservation] = []
        self.count_token_requests = 0
        self.first_message_request = threading.Event()

    def offset(self) -> float:
        return time.monotonic() - self.started_monotonic

    def add_request(self, path: str, raw_body: bytes, stream_requested: bool) -> RequestObservation:
        with self.lock:
            observation = RequestObservation(
                request_number=len(self.requests) + 1,
                received_offset_seconds=self.offset(),
                path=path,
                body_sha256=hashlib.sha256(raw_body).hexdigest(),
                body_bytes=len(raw_body),
                stream_requested=stream_requested,
            )
            self.requests.append(observation)
            self.first_message_request.set()
            return observation


class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, state: ProbeState) -> None:
        super().__init__(("127.0.0.1", 0), ProbeHandler)
        self.state = state


def _anthropic_sse() -> bytes:
    events: list[tuple[str, dict[str, Any]]] = [
        (
            "message_start",
            {
                "type": "message_start",
                "message": {
                    "id": "msg_rh2_local_probe",
                    "type": "message",
                    "role": "assistant",
                    "model": "rh2-local-probe-model",
                    "content": [],
                    "stop_reason": None,
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 0},
                },
            },
        ),
        (
            "content_block_start",
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
        ),
        (
            "content_block_delta",
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "ok"},
            },
        ),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        (
            "message_delta",
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        ),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(
        f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
        for event, data in events
    ).encode()


def _anthropic_error(status: int, error_type: str, message: str) -> bytes:
    return json.dumps(
        {"type": "error", "error": {"type": error_type, "message": message}},
        separators=(",", ":"),
    ).encode()


def _anthropic_message() -> bytes:
    return json.dumps(
        {
            "id": "msg_rh2_local_probe_nonstreaming",
            "type": "message",
            "role": "assistant",
            "model": "rh2-local-probe-model",
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        },
        separators=(",", ":"),
    ).encode()


class ProbeHandler(BaseHTTPRequestHandler):
    server: LoopbackServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        length = int(self.headers.get("content-length", "0"))
        raw_body = self.rfile.read(length)
        if self.path.startswith("/v1/messages/count_tokens"):
            with self.server.state.lock:
                self.server.state.count_token_requests += 1
            self._write_json(200, b'{"input_tokens":1}')
            return

        try:
            parsed = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            parsed = {}
        observation = self.server.state.add_request(
            self.path, raw_body, parsed.get("stream") is True
        )
        scenario = self.server.state.scenario

        if scenario in {"delay_success", "hang_until_probe_timeout"}:
            if self._wait_for_delay_or_client_close(observation):
                return
            self._write_sse(observation, _anthropic_sse())
            return
        if scenario == "http_500":
            self._write_json_observed(
                observation,
                500,
                _anthropic_error(500, "api_error", "rh2 injected HTTP 500"),
            )
            return
        if scenario == "http_500_no_retry":
            self._write_json_observed(
                observation,
                500,
                _anthropic_error(500, "api_error", "rh2 injected HTTP 500"),
                extra_headers={"x-should-retry": "false"},
            )
            return
        if scenario == "http_429":
            self._write_json_observed(
                observation,
                429,
                _anthropic_error(429, "rate_limit_error", "rh2 injected HTTP 429"),
                extra_headers={"Retry-After": "2"},
            )
            return
        if scenario == "http_404":
            self._write_json_observed(
                observation,
                404,
                _anthropic_error(404, "not_found_error", "rh2 injected HTTP 404"),
            )
            return
        if scenario == "disconnect_before_headers":
            observation.write_error = "injected_disconnect_before_headers"
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
            return
        if scenario == "partial_sse_disconnect":
            observation.response_headers_offset_seconds = self.server.state.offset()
            observation.response_status = 200
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            partial = (
                'event: message_start\ndata: {"type":"message_start","message":'
                '{"id":"msg_partial","type":"message","role":"assistant",'
                '"model":"rh2-local-probe-model","content":[],"stop_reason":null,'
                '"stop_sequence":null,"usage":{"input_tokens":1,"output_tokens":0}}}\n\n'
            ).encode()
            try:
                self.wfile.write(partial)
                self.wfile.flush()
            finally:
                observation.write_error = "injected_disconnect_after_partial_sse"
                try:
                    self.connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                self.connection.close()
            return
        if scenario == "partial_sse_hang":
            if not observation.stream_requested:
                self._write_json_observed(observation, 200, _anthropic_message())
                return
            observation.response_headers_offset_seconds = self.server.state.offset()
            observation.response_status = 200
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            partial = (
                'event: message_start\ndata: {"type":"message_start","message":'
                '{"id":"msg_partial_hang","type":"message","role":"assistant",'
                '"model":"rh2-local-probe-model","content":[],"stop_reason":null,'
                '"stop_sequence":null,"usage":{"input_tokens":1,"output_tokens":0}}}\n\n'
            ).encode()
            try:
                self.wfile.write(f"{len(partial):X}\r\n".encode())
                self.wfile.write(partial)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
                if self._wait_for_client_close(observation):
                    return
            except (BrokenPipeError, ConnectionResetError) as exc:
                observation.write_error = f"{type(exc).__name__}: {exc}"
            return
        raise AssertionError(f"unknown scenario: {scenario}")

    def _wait_for_delay_or_client_close(self, observation: RequestObservation) -> bool:
        """Wait without sending headers; return True if the client closes first."""

        deadline = time.monotonic() + self.server.state.delay_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            readable, _, _ = select.select([self.connection], [], [], min(0.1, remaining))
            if not readable:
                continue
            try:
                pending = self.connection.recv(1, socket.MSG_PEEK)
            except (BlockingIOError, InterruptedError):
                continue
            except OSError as exc:
                observation.write_error = f"client_socket_error_before_headers: {exc}"
                return True
            if pending == b"":
                observation.write_error = "client_closed_before_response_headers"
                return True

    def _wait_for_client_close(self, observation: RequestObservation) -> bool:
        deadline = time.monotonic() + max(self.server.state.delay_seconds, 30.0)
        while time.monotonic() < deadline:
            readable, _, _ = select.select([self.connection], [], [], 0.1)
            if not readable:
                continue
            try:
                pending = self.connection.recv(1, socket.MSG_PEEK)
            except (BlockingIOError, InterruptedError):
                continue
            except OSError as exc:
                observation.write_error = f"client_socket_error_after_headers: {exc}"
                return True
            if pending == b"":
                observation.write_error = "client_closed_after_partial_sse"
                return True
        observation.write_error = "probe_wait_for_client_close_timed_out"
        return False

    def _write_json(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_json_observed(
        self,
        observation: RequestObservation,
        status: int,
        body: bytes,
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        observation.response_headers_offset_seconds = self.server.state.offset()
        observation.response_status = status
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError) as exc:
            observation.write_error = f"{type(exc).__name__}: {exc}"

    def _write_sse(self, observation: RequestObservation, body: bytes) -> None:
        observation.response_headers_offset_seconds = self.server.state.offset()
        observation.response_status = 200
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError) as exc:
            observation.write_error = f"{type(exc).__name__}: {exc}"


def _cli_version(claude_bin: str) -> str:
    completed = subprocess.run(
        [claude_bin, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return (completed.stdout or completed.stderr).strip()


def _terminate_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)


def _client_event_summary(stdout: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Extract retry/result facts without persisting paths, prompts, or session ids."""

    retries: list[dict[str, Any]] = []
    result: dict[str, Any] | None = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "api_retry":
            retries.append(
                {
                    "attempt": event.get("attempt"),
                    "max_retries": event.get("max_retries"),
                    "retry_delay_ms": event.get("retry_delay_ms"),
                    "error_status": event.get("error_status"),
                    "error": event.get("error"),
                }
            )
        elif event.get("type") == "result":
            result = {
                "subtype": event.get("subtype"),
                "is_error": event.get("is_error"),
                "api_error_status": event.get("api_error_status"),
                "num_turns": event.get("num_turns"),
                "terminal_reason": event.get("terminal_reason"),
            }
    return retries, result


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    state = ProbeState(args.scenario, args.delay_seconds)
    server = LoopbackServer(state)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    env = os.environ.copy()
    env.update(
        {
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}",
            "ANTHROPIC_AUTH_TOKEN": "rh2-local-probe-token",
            "ANTHROPIC_API_KEY": "",
            "ANTHROPIC_MODEL": "rh2-local-probe-model",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
            "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
        }
    )
    control_env = {
        "CLAUDE_CODE_MAX_RETRIES": (
            None if args.max_retries is None else str(args.max_retries)
        ),
        "CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK": (
            "1" if args.disable_nonstreaming_fallback else None
        ),
        "CLAUDE_CODE_UNATTENDED_RETRY": (
            "0" if args.disable_unattended_retry else None
        ),
        "API_TIMEOUT_MS": (
            None if args.api_timeout_ms is None else str(args.api_timeout_ms)
        ),
        "CLAUDE_ENABLE_STREAM_WATCHDOG": (
            "1" if args.enable_stream_watchdog else None
        ),
        "CLAUDE_STREAM_IDLE_TIMEOUT_MS": (
            None
            if args.stream_idle_timeout_ms is None
            else str(args.stream_idle_timeout_ms)
        ),
    }
    for key, value in control_env.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    command = [
        args.claude_bin,
        "-p",
        "Reply with exactly ok",
        "--permission-mode",
        "bypassPermissions",
        "--output-format",
        "stream-json",
        "--include-partial-messages",
        "--include-hook-events",
        "--verbose",
        "--no-session-persistence",
        "--disable-slash-commands",
        "--no-chrome",
    ]
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="rh2-cc-http-probe-") as cwd:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        terminated_by_probe = False
        try:
            stdout, stderr = process.communicate(timeout=args.process_timeout_seconds)
        except subprocess.TimeoutExpired:
            terminated_by_probe = True
            _terminate_process_group(process)
            stdout, stderr = process.communicate()
    elapsed = time.monotonic() - started

    # Give a delayed handler a short chance to observe the closed client. Do not
    # wait for the configured delay: long-hang probes must finish at their cap.
    time.sleep(0.2)
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=2)

    with state.lock:
        requests = [asdict(item) for item in state.requests]
        count_token_requests = state.count_token_requests
    received = [item["received_offset_seconds"] for item in requests]
    hashes = [item["body_sha256"] for item in requests]
    client_retry_events, client_result = _client_event_summary(stdout)
    return {
        "schema_id": "rh2.fa.claude_code_http_probe.v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scenario": args.scenario,
        "claude_version": _cli_version(args.claude_bin),
        "control_env": {key: value for key, value in control_env.items() if value is not None},
        "command_flags": command[3:],
        "delay_seconds": args.delay_seconds,
        "process_timeout_seconds": args.process_timeout_seconds,
        "elapsed_seconds": round(elapsed, 6),
        "process_exit_code": process.returncode,
        "terminated_by_probe": terminated_by_probe,
        "request_count": len(requests),
        "count_token_request_count": count_token_requests,
        "retry_intervals_seconds": [
            round(received[index] - received[index - 1], 6)
            for index in range(1, len(received))
        ],
        "request_bodies_identical": len(set(hashes)) <= 1,
        "requests": requests,
        "client_retry_events": client_retry_events,
        "client_result": client_result,
        "stderr_nonempty": bool(stderr.strip()),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        required=True,
        choices=[
            "delay_success",
            "http_500",
            "http_500_no_retry",
            "http_429",
            "http_404",
            "disconnect_before_headers",
            "partial_sse_disconnect",
            "partial_sse_hang",
            "hang_until_probe_timeout",
        ],
    )
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--process-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-retries", type=int)
    parser.add_argument("--disable-nonstreaming-fallback", action="store_true")
    parser.add_argument("--disable-unattended-retry", action="store_true")
    parser.add_argument("--api-timeout-ms", type=int)
    parser.add_argument("--enable-stream-watchdog", action="store_true")
    parser.add_argument("--stream-idle-timeout-ms", type=int)
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.delay_seconds < 0:
        raise SystemExit("--delay-seconds must be >= 0")
    if args.process_timeout_seconds <= 0:
        raise SystemExit("--process-timeout-seconds must be > 0")
    if args.max_retries is not None and args.max_retries < 0:
        raise SystemExit("--max-retries must be >= 0")
    if args.api_timeout_ms is not None and args.api_timeout_ms <= 0:
        raise SystemExit("--api-timeout-ms must be > 0")
    if args.stream_idle_timeout_ms is not None and args.stream_idle_timeout_ms <= 0:
        raise SystemExit("--stream-idle-timeout-ms must be > 0")
    result = run_probe(args)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
