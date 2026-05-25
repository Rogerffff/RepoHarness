import json

import pytest

from repo_harness.cli.main import main
from repo_harness.evaluation.episode_parity import run_stage16f4_parity_audit


def test_stage16f4_cli_inspect_accepts_complete_evidence(tmp_path, capsys):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)

    exit_code = main(["inspect-stage16f4-parity", str(evidence_dir), "--assert-complete"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["passed"] is True


def test_stage16f4_cli_inspect_rejects_public_path_leak(tmp_path):
    evidence_dir = run_stage16f4_parity_audit(tmp_path / "evidence", clean_output_dir=True)
    report_path = evidence_dir / "stage16f4_run_task_run_episode_parity_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["leak_probe"] = "/Users/roger/private"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["inspect-stage16f4-parity", str(evidence_dir), "--assert-complete"])
