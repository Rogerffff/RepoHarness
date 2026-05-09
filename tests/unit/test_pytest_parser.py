from repo_harness.verifier import PytestTextParser


def test_pytest_parser_confidence_for_common_output():
    parser = PytestTextParser()

    confidence = parser.parser_confidence(
        "1 failed, 2 passed in 0.12s",
        "",
        1,
    )

    assert confidence >= 0.8
    assert parser.error_type("1 failed", "", 1, False) == "assertion_failure"


def test_pytest_parser_marks_command_errors_and_timeouts():
    parser = PytestTextParser()

    assert parser.error_type("", "ModuleNotFoundError: app", 2, False) == "test_command_error"
    assert parser.error_type("", "", None, True) == "test_timeout"
    assert parser.parser_confidence("no tests ran", "", 5) < 0.5


def test_pytest_parser_maps_selectors_from_failed_nodeids_without_suite_level_fanout():
    parser = PytestTextParser()
    stdout = """
tests/test_widget.py::test_keeps_existing_behavior PASSED
tests/test_widget.py::test_new_edge_case FAILED
tests/test_widget.py::test_other_behavior PASSED

=================================== FAILURES ===================================
____________________________ test_new_edge_case ____________________________

short test summary info
FAILED tests/test_widget.py::test_new_edge_case - AssertionError: bad edge
========================= 1 failed, 2 passed in 0.12s =========================
"""

    cases, parsed = parser.selector_statuses(
        selectors=[
            "tests/test_widget.py::test_keeps_existing_behavior",
            "tests/test_widget.py::test_new_edge_case",
            "tests/test_widget.py::test_other_behavior",
        ],
        stdout=stdout,
        stderr="",
        exit_code=1,
        timeout=False,
    )

    assert parsed.summary_counts == {"failed": 1, "passed": 2}
    assert parsed.suite_completed is True
    assert {case["test_id"]: case["status"] for case in cases} == {
        "tests/test_widget.py::test_keeps_existing_behavior": "passed",
        "tests/test_widget.py::test_new_edge_case": "failed",
        "tests/test_widget.py::test_other_behavior": "passed",
    }


def test_pytest_parser_keeps_absent_selectors_unknown_when_failure_nodeids_are_incomplete():
    parser = PytestTextParser()

    cases, parsed = parser.selector_statuses(
        selectors=[
            "tests/test_widget.py::test_first",
            "tests/test_widget.py::test_second",
        ],
        stdout="========================= 1 failed, 1 passed in 0.12s =========================",
        stderr="",
        exit_code=1,
        timeout=False,
    )

    assert "summary_failures_without_complete_nodeids" in parsed.parse_warnings
    assert [case["status"] for case in cases] == ["unknown", "unknown"]


def test_pytest_parser_reads_verbose_progress_statuses_before_absence_inference():
    parser = PytestTextParser()
    stdout = """
tests/test_widget.py::test_regular PASSED                                [ 25%]
tests/test_widget.py::test_skip SKIPPED (requires optional dependency)    [ 50%]
tests/test_widget.py::test_expected_bug XFAIL                             [ 75%]
tests/test_widget.py::test_unexpected_pass XPASS                          [100%]
==================== 1 passed, 1 skipped, 1 xfailed, 1 xpassed in 0.12s ====================
"""

    cases, parsed = parser.selector_statuses(
        selectors=[
            "tests/test_widget.py::test_regular",
            "tests/test_widget.py::test_skip",
            "tests/test_widget.py::test_expected_bug",
            "tests/test_widget.py::test_unexpected_pass",
        ],
        stdout=stdout,
        stderr="",
        exit_code=0,
        timeout=False,
    )

    assert parsed.passed_nodeids == {"tests/test_widget.py::test_regular"}
    assert parsed.skipped_nodeids == {"tests/test_widget.py::test_skip"}
    assert parsed.xfailed_nodeids == {"tests/test_widget.py::test_expected_bug"}
    assert parsed.xpassed_nodeids == {"tests/test_widget.py::test_unexpected_pass"}
    assert {case["test_id"]: case["status"] for case in cases} == {
        "tests/test_widget.py::test_regular": "passed",
        "tests/test_widget.py::test_skip": "skipped",
        "tests/test_widget.py::test_expected_bug": "skipped",
        "tests/test_widget.py::test_unexpected_pass": "skipped",
    }


def test_pytest_parser_maps_unparameterized_selector_to_parameterized_failure():
    parser = PytestTextParser()
    stdout = """
short test summary info
FAILED tests/cli/test_fix.py::test__cli__command_fix_stdin[stdin0-output0] - AssertionError
========================= 1 failed, 3 passed in 0.12s =========================
"""

    cases, parsed = parser.selector_statuses(
        selectors=["tests/cli/test_fix.py::test__cli__command_fix_stdin"],
        stdout=stdout,
        stderr="",
        exit_code=1,
        timeout=False,
    )

    assert parsed.failed_nodeids == {
        "tests/cli/test_fix.py::test__cli__command_fix_stdin[stdin0-output0]"
    }
    assert "parameterized_selector_match_used" in parsed.parse_warnings
    assert cases == [
        {
            "test_id": "tests/cli/test_fix.py::test__cli__command_fix_stdin",
            "normalized_test_id": "tests/cli/test_fix.py::test__cli__command_fix_stdin",
            "status": "failed",
            "status_source": "pytest_failed_nodeid",
            "match_strategy": "parameterized_selector_prefix",
            "matched_nodeid": "tests/cli/test_fix.py::test__cli__command_fix_stdin[stdin0-output0]",
            "failure_kinds": ["failed"],
            "matched_failed_nodeid": "tests/cli/test_fix.py::test__cli__command_fix_stdin[stdin0-output0]",
            "failed_match_strategy": "parameterized_selector_prefix",
        }
    ]


def test_pytest_parser_preserves_parameterized_nodeids_with_spaces():
    parser = PytestTextParser()
    stdout = """
short test summary info
FAILED tests/test_example.py::test_param[a b] - AssertionError
========================= 1 failed in 0.12s =========================
"""

    cases, parsed = parser.selector_statuses(
        selectors=["tests/test_example.py::test_param[a b]"],
        stdout=stdout,
        stderr="",
        exit_code=1,
        timeout=False,
    )

    assert parsed.failed_nodeids == {"tests/test_example.py::test_param[a b]"}
    assert cases[0]["status"] == "failed"
    assert cases[0]["status_source"] == "pytest_failed_nodeid"
    assert cases[0]["matched_nodeid"] == "tests/test_example.py::test_param[a b]"


def test_pytest_parser_preserves_parameterized_nodeids_with_summary_separators():
    parser = PytestTextParser()
    stdout = """
short test summary info
FAILED tests/test_example.py::test_param[a - b] - AssertionError
FAILED tests/test_example.py::test_param[c -- d] - AssertionError
========================= 2 failed in 0.12s =========================
"""

    cases, parsed = parser.selector_statuses(
        selectors=[
            "tests/test_example.py::test_param[a - b]",
            "tests/test_example.py::test_param[c -- d]",
        ],
        stdout=stdout,
        stderr="",
        exit_code=1,
        timeout=False,
    )

    assert parsed.failed_nodeids == {
        "tests/test_example.py::test_param[a - b]",
        "tests/test_example.py::test_param[c -- d]",
    }
    assert [case["status"] for case in cases] == ["failed", "failed"]
    assert [case["matched_nodeid"] for case in cases] == [
        "tests/test_example.py::test_param[a - b]",
        "tests/test_example.py::test_param[c -- d]",
    ]


def test_pytest_parser_normalizes_status_prefixed_error_nodeids():
    parser = PytestTextParser()
    stdout = """
ERROR tests/test_widget.py::test_import_error - ImportError: libGL.so.1
========================= 1 error in 0.12s =========================
"""

    cases, parsed = parser.selector_statuses(
        selectors=["tests/test_widget.py::test_import_error"],
        stdout=stdout,
        stderr="",
        exit_code=1,
        timeout=False,
    )

    assert parsed.error_nodeids == {"tests/test_widget.py::test_import_error"}
    assert [case["status"] for case in cases] == ["error"]
    assert cases[0]["matched_error_nodeid"] == "tests/test_widget.py::test_import_error"
