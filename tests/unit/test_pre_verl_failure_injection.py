from __future__ import annotations

import json
from pathlib import Path

from repo_harness.cli.main import main
from repo_harness.pre_verl_failure_injection import (
    DEFAULT_PROVIDER_FAILURE_INJECTION_SCENARIOS,
    run_provider_failure_injection_smoke,
)


def test_provider_failure_injection_smoke_writes_passed_report(tmp_path: Path) -> None:
    report_path = run_provider_failure_injection_smoke(
        output_dir=tmp_path / "smoke",
        scenarios=None,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "passed"
    assert report["scenario_count"] == len(DEFAULT_PROVIDER_FAILURE_INJECTION_SCENARIOS) == 9
    records = {record["scenario"]: record for record in report["records"]}
    assert "provider_error_500" in records
    assert records["retryable_429"]["retry_count"] == 1
    assert records["timeout"]["attempt_count"] == 3
    assert records["provider_error_500"]["attempt_count"] == 3
    assert records["auth_error"]["retry_count"] == 0
    assert records["length"]["model_error_type"] == "output_token_limit_reached"
    assert records["malformed_tool_call"]["model_visible_repair_message_present"] is True
    assert all(record["excluded_from_trainable_accepted_sample"] is True for record in records.values())


def test_provider_failure_injection_smoke_cli(tmp_path: Path) -> None:
    exit_code = main(
        [
            "run-provider-failure-injection-smoke",
            "--output-dir",
            (tmp_path / "cli-smoke").as_posix(),
            "--scenario",
            "retryable_429,length,malformed_tool_call",
        ]
    )

    assert exit_code == 0
    report = json.loads(
        (tmp_path / "cli-smoke" / "pre_verl_provider_failure_injection_smoke_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "passed"
