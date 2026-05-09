import json
from pathlib import Path

from scripts.pre_verl.inspect_23_dev_issue_patterns import scan_run_dir


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_dev23_issue_scanner_finds_selector_and_output_audit_patterns(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    task_dir = run_dir / "run_task_runs" / "task_001"
    _write_json(
        task_dir / "pre_verl_final_verifier_result.json",
        {
            "fail_to_pass_result": {
                "exit_code": 1,
                "summary_counts": {"failed": 1, "errors": 1},
                "failed_count": 0,
                "error_count": 0,
                "failed_nodeids": ["FAILED tests/test_widget.py::test_param[case0]"],
                "error_nodeids": ["ERROR tests/test_widget.py::test_error"],
            },
            "pass_to_pass_result": {
                "exit_code": 4,
                "summary_counts": {},
                "failed_count": 0,
                "error_count": 0,
                "failed_nodeids": [],
                "error_nodeids": [],
            },
        },
    )

    report = scan_run_dir(run_dir)

    kinds = {issue["kind"] for issue in report["issues"]}
    assert "failed_summary_without_failed_count" in kinds
    assert "failed_nodeids_without_failed_count" in kinds
    assert "error_summary_without_error_count" in kinds
    assert "error_nodeids_without_error_count" in kinds
    assert "status_prefixed_nodeids" in kinds
    assert "pytest_exit_code_4_missing_output_audit" in kinds


def test_dev23_issue_scanner_finds_slow_wide_symbol_search(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    task_dir = run_dir / "run_task_runs" / "task_001"
    task_dir.mkdir(parents=True)
    (task_dir / "events.jsonl").write_text(
        json.dumps(
            {
                "event_type": "tool_completed",
                "data": {
                    "effective_tool_name": "symbol_search",
                    "duration_ms": 6000,
                    "typed": {
                        "root": ".",
                        "candidate_file_count": 200,
                        "result_kind": "complete_no_symbol_match",
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = scan_run_dir(run_dir)

    kinds = {issue["kind"] for issue in report["issues"]}
    assert "slow_symbol_search" in kinds
    assert "wide_symbol_search_without_recovery" in kinds
