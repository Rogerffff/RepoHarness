"""第一版 pytest 输出解析 helper。"""

from __future__ import annotations

import re


class PytestTextParser:
    parser_id = "pytest"
    parser_version = "pytest_parser_v0"

    def parser_confidence(self, stdout: str, stderr: str, exit_code: int | None) -> float:
        combined = f"{stdout}\n{stderr}"
        if "no tests ran" in combined.lower():
            return 0.2
        if re.search(r"\b\d+\s+(passed|failed|error|skipped)", combined):
            return 0.9
        if exit_code == 0 and "." in stdout:
            return 0.75
        if exit_code not in (0, 1):
            return 0.4
        return 0.6

    def error_type(self, stdout: str, stderr: str, exit_code: int | None, timeout: bool) -> str | None:
        combined = f"{stdout}\n{stderr}".lower()
        if timeout:
            return "test_timeout"
        if exit_code == 0:
            return None
        if "no tests ran" in combined or "not found" in combined:
            return "test_command_error"
        if "importerror" in combined or "modulenotfounderror" in combined:
            return "test_command_error"
        if "error" in combined and "failed" not in combined:
            return "test_command_error"
        return "assertion_failure"
