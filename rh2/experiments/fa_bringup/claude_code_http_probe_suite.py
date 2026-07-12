#!/usr/bin/env python3
"""Run the source-guided Claude Code HTTP behavior characterization suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Case:
    name: str
    arguments: tuple[str, ...]
    expected_request_count: int
    expected_exit_code: int | None
    expected_stream_flags: tuple[bool, ...]
    expected_probe_termination: bool = False
    diagnostic_only: bool = False


HARDENED = (
    "--max-retries",
    "0",
    "--disable-nonstreaming-fallback",
    "--disable-unattended-retry",
)


CASES = (
    Case(
        "delayed_success_hardened",
        ("--scenario", "delay_success", "--delay-seconds", "1", *HARDENED),
        1,
        0,
        (True,),
    ),
    Case("http500_max0", ("--scenario", "http_500", *HARDENED), 1, 1, (True,)),
    Case("http429_max0", ("--scenario", "http_429", *HARDENED), 1, 1, (True,)),
    Case(
        "disconnect_max0",
        ("--scenario", "disconnect_before_headers", *HARDENED),
        1,
        1,
        (True,),
    ),
    Case(
        "partial_disconnect_hardened",
        ("--scenario", "partial_sse_disconnect", *HARDENED),
        1,
        1,
        (True,),
    ),
    # Version 2.1.205 bypasses CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK for
    # stream-creation 404s. Keep this as a drift detector, not a desired API.
    Case(
        "http404_hardened_exception",
        ("--scenario", "http_404", *HARDENED),
        2,
        1,
        (True, False),
    ),
    Case(
        "http500_header_no_retry",
        ("--scenario", "http_500_no_retry"),
        1,
        1,
        (True,),
    ),
    Case(
        "preheader_timeout_max0",
        (
            "--scenario",
            "hang_until_probe_timeout",
            "--delay-seconds",
            "30",
            "--api-timeout-ms",
            "1000",
            *HARDENED,
        ),
        1,
        1,
        (True,),
    ),
    Case(
        "partial_hang_api_timeout_only",
        (
            "--scenario",
            "partial_sse_hang",
            "--delay-seconds",
            "30",
            "--api-timeout-ms",
            "1000",
            *HARDENED,
        ),
        1,
        143,
        (True,),
        expected_probe_termination=True,
    ),
    # The source snapshot says this should abort after one second, but the
    # pinned 2.1.205 binary did not. Record it without turning an unresolved
    # implementation mismatch into a desired contract.
    Case(
        "stream_watchdog_diagnostic",
        (
            "--scenario",
            "partial_sse_hang",
            "--delay-seconds",
            "30",
            "--api-timeout-ms",
            "5000",
            "--enable-stream-watchdog",
            "--stream-idle-timeout-ms",
            "1000",
            *HARDENED,
        ),
        1,
        143,
        (True,),
        expected_probe_termination=True,
        diagnostic_only=True,
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_case(
    case: Case,
    *,
    probe: Path,
    claude_bin: Path,
    evidence_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    output = evidence_dir / f"{case.name}.json"
    command = [
        sys.executable,
        str(probe),
        *case.arguments,
        "--process-timeout-seconds",
        "3",
        "--claude-bin",
        str(claude_bin),
        "--output",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"probe process failed for {case.name}: exit={completed.returncode} "
            f"stderr_nonempty={bool(completed.stderr.strip())}"
        )
    result = json.loads(output.read_text(encoding="utf-8"))
    failures: list[str] = []
    actual_stream_flags = tuple(item["stream_requested"] for item in result["requests"])
    checks = {
        "request_count": (result["request_count"], case.expected_request_count),
        "process_exit_code": (result["process_exit_code"], case.expected_exit_code),
        "stream_flags": (actual_stream_flags, case.expected_stream_flags),
        "terminated_by_probe": (
            result["terminated_by_probe"],
            case.expected_probe_termination,
        ),
    }
    for name, (actual, expected) in checks.items():
        if actual != expected:
            failures.append(f"{name}: actual={actual!r} expected={expected!r}")
    return result, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude-bin", type=Path, default=Path("claude"))
    parser.add_argument("--expected-version", default="2.1.205")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    claude_bin = args.claude_bin.expanduser().resolve()
    if not claude_bin.is_file():
        raise SystemExit(f"Claude Code binary not found: {claude_bin}")
    actual_sha256 = _sha256(claude_bin)
    if args.expected_sha256 and actual_sha256 != args.expected_sha256:
        raise SystemExit(
            f"Claude Code sha256 mismatch: actual={actual_sha256} "
            f"expected={args.expected_sha256}"
        )

    evidence_dir = args.evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    probe = Path(__file__).with_name("claude_code_http_probe.py")
    cases: list[dict[str, Any]] = []
    hard_failures: list[str] = []
    diagnostic_findings: list[str] = []
    diagnostic_observations: list[dict[str, Any]] = []
    observed_version: str | None = None
    for case in CASES:
        result, failures = _run_case(
            case,
            probe=probe,
            claude_bin=claude_bin,
            evidence_dir=evidence_dir,
        )
        observed_version = observed_version or result["claude_version"]
        entry = {
            "name": case.name,
            "diagnostic_only": case.diagnostic_only,
            "passed_characterization": not failures,
            "failures": failures,
            "request_count": result["request_count"],
            "process_exit_code": result["process_exit_code"],
            "terminated_by_probe": result["terminated_by_probe"],
            "stream_flags": [item["stream_requested"] for item in result["requests"]],
        }
        cases.append(entry)
        target = diagnostic_findings if case.diagnostic_only else hard_failures
        target.extend(f"{case.name}: {failure}" for failure in failures)
        if case.diagnostic_only:
            diagnostic_observations.append(
                {
                    "name": case.name,
                    "observed": (
                        "stream watchdog configured for 1000ms did not terminate "
                        "the request before the 3s probe cap"
                    ),
                    "request_count": result["request_count"],
                    "terminated_by_probe": result["terminated_by_probe"],
                }
            )

    if observed_version is None or args.expected_version not in observed_version:
        hard_failures.append(
            f"version: actual={observed_version!r} expected_contains={args.expected_version!r}"
        )
    summary = {
        "schema_id": "rh2.fa.claude_code_http_source_guided_suite.v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "claude_version": observed_version,
        "claude_binary_sha256": actual_sha256,
        "expected_version": args.expected_version,
        "hard_pass": not hard_failures,
        "hard_failures": hard_failures,
        "diagnostic_findings": diagnostic_findings,
        "diagnostic_observations": diagnostic_observations,
        "cases": cases,
    }
    summary_path = evidence_dir / "suite_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not hard_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
