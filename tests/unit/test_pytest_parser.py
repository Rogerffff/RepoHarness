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
