from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.v3_context_diagnostics import (
    build_v3_context_diagnostics,
    inspect_context_report,
    inspect_long_rollout_diagnostics,
)


def test_v3_context_diagnostics_builds_and_inspects(tmp_path: Path):
    output_dir = tmp_path / "v3_context"

    result_dir = build_v3_context_diagnostics(output_dir=output_dir)
    context_output = inspect_context_report(
        result_dir,
        report=result_dir / "context_compaction_report.json",
        assert_consistent=True,
    )
    long_output = inspect_long_rollout_diagnostics(
        result_dir,
        report=result_dir / "long_rollout_diagnostics.json",
        assert_complete=True,
    )

    context_report = _read_json(result_dir / "context_compaction_report.json")
    long_report = _read_json(result_dir / "long_rollout_diagnostics.json")

    assert "Inspect context report: passed" in context_output
    assert "Inspect long rollout diagnostics: passed" in long_output
    assert context_report["compaction_observed"] is True
    assert context_report["observation_matches_prepared_messages"] is True
    assert context_report["context_events"][0]["replaced_tool_result_ids"]
    assert "repeated_tool_call" in long_report["diagnostic_type_distribution"]
    assert long_report["context_report_ref"]


def test_v3_context_diagnostics_cli(tmp_path: Path, capsys):
    output_dir = tmp_path / "v3_context_cli"

    assert main(["build-v3-context-diagnostics", "--output-dir", str(output_dir)]) == 0
    assert "V3 context diagnostics 产物目录" in capsys.readouterr().out
    assert main(
        [
            "inspect-context-report",
            str(output_dir),
            "--report",
            str(output_dir / "context_compaction_report.json"),
            "--assert-consistent",
        ]
    ) == 0
    assert "Inspect context report: passed" in capsys.readouterr().out
    assert main(
        [
            "inspect-long-rollout-diagnostics",
            str(output_dir),
            "--report",
            str(output_dir / "long_rollout_diagnostics.json"),
            "--assert-complete",
        ]
    ) == 0
    assert "Inspect long rollout diagnostics: passed" in capsys.readouterr().out


def test_inspect_context_report_rejects_prepared_message_sha_drift(tmp_path: Path):
    output_dir = tmp_path / "v3_context_bad_sha"
    result_dir = build_v3_context_diagnostics(output_dir=output_dir)
    report_path = result_dir / "context_compaction_report.json"
    report = _read_json(report_path)
    report["context_events"][0]["prepared_messages_sha256"] = "0" * 64
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="prepared_messages_sha256"):
        inspect_context_report(
            result_dir,
            report=report_path,
            assert_consistent=True,
        )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
