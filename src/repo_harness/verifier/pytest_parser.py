"""第一版 pytest 输出解析 helper。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PytestParseResult:
    parser_version: str
    parser_confidence: float
    summary_counts: dict[str, int] = field(default_factory=dict)
    passed_nodeids: set[str] = field(default_factory=set)
    failed_nodeids: set[str] = field(default_factory=set)
    error_nodeids: set[str] = field(default_factory=set)
    skipped_nodeids: set[str] = field(default_factory=set)
    xfailed_nodeids: set[str] = field(default_factory=set)
    xpassed_nodeids: set[str] = field(default_factory=set)
    suite_completed: bool = False
    parse_warnings: list[str] = field(default_factory=list)
    pytest_exit_reason: str = "pytest_exit_reason_unknown"


class PytestTextParser:
    parser_id = "pytest"
    parser_version = "pytest_parser_v1"

    def parser_confidence(self, stdout: str, stderr: str, exit_code: int | None) -> float:
        return self.parse_output(stdout, stderr, exit_code, timeout=False).parser_confidence

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

    def pytest_exit_reason(
        self,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timeout: bool,
    ) -> str:
        parsed = self.parse_output(stdout, stderr, exit_code, timeout=timeout)
        return parsed.pytest_exit_reason

    def parse_output(
        self,
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timeout: bool = False,
    ) -> PytestParseResult:
        combined = f"{stdout}\n{stderr}"
        lower = combined.lower()
        summary_counts = _parse_summary_counts(combined)
        raw_passed_nodeids = _parse_nodeids(combined, "PASSED") | _parse_progress_nodeids(
            combined, "PASSED"
        )
        raw_failed_nodeids = _parse_nodeids(combined, "FAILED") | _parse_progress_nodeids(
            combined, "FAILED"
        )
        raw_error_nodeids = _parse_nodeids(combined, "ERROR") | _parse_progress_nodeids(
            combined, "ERROR"
        )
        raw_skipped_nodeids = _parse_nodeids(combined, "SKIPPED") | _parse_progress_nodeids(
            combined, "SKIPPED"
        )
        raw_xfailed_nodeids = _parse_nodeids(combined, "XFAIL") | _parse_progress_nodeids(
            combined, "XFAIL"
        )
        raw_xpassed_nodeids = _parse_nodeids(combined, "XPASS") | _parse_progress_nodeids(
            combined, "XPASS"
        )
        passed_nodeids = {_normalize_nodeid(item) for item in raw_passed_nodeids}
        failed_nodeids = {_normalize_nodeid(item) for item in raw_failed_nodeids}
        error_nodeids = {_normalize_nodeid(item) for item in raw_error_nodeids}
        skipped_nodeids = {_normalize_nodeid(item) for item in raw_skipped_nodeids}
        xfailed_nodeids = {_normalize_nodeid(item) for item in raw_xfailed_nodeids}
        xpassed_nodeids = {_normalize_nodeid(item) for item in raw_xpassed_nodeids}
        parse_warnings: list[str] = []
        if (
            raw_passed_nodeids != passed_nodeids
            or raw_failed_nodeids != failed_nodeids
            or raw_error_nodeids != error_nodeids
            or raw_skipped_nodeids != skipped_nodeids
            or raw_xfailed_nodeids != xfailed_nodeids
            or raw_xpassed_nodeids != xpassed_nodeids
        ):
            parse_warnings.append("status_prefix_nodeid_normalized")
        if timeout:
            parse_warnings.append("pytest_command_timed_out")
        if "no tests ran" in lower:
            parse_warnings.append("no_tests_ran")
        if "error collecting" in lower or "errors during collection" in lower:
            parse_warnings.append("collection_error")
        if exit_code not in {0, 1, None}:
            parse_warnings.append("pytest_command_error_exit_code")
        if exit_code == 1 and not summary_counts and not failed_nodeids and not error_nodeids:
            parse_warnings.append("failed_exit_without_selector_facts")
        summary_failure_count = int(summary_counts.get("failed", 0)) + int(
            summary_counts.get("errors", 0)
        )
        parsed_failure_count = len(failed_nodeids) + len(error_nodeids)
        if summary_failure_count > parsed_failure_count:
            parse_warnings.append("summary_failures_without_complete_nodeids")
        pytest_exit_reason = _pytest_exit_reason(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            timeout=timeout,
            summary_counts=summary_counts,
            failed_nodeids=failed_nodeids,
            error_nodeids=error_nodeids,
        )
        suite_completed = (
            not timeout
            and exit_code in {0, 1}
            and "collection_error" not in parse_warnings
            and "no_tests_ran" not in parse_warnings
            and (
                bool(summary_counts)
                or exit_code == 0
                or bool(failed_nodeids)
                or bool(error_nodeids)
            )
        )
        if timeout or "no_tests_ran" in parse_warnings:
            confidence = 0.2
        elif summary_counts:
            confidence = 0.95
        elif exit_code == 0 and "." in stdout:
            confidence = 0.75
        elif failed_nodeids or error_nodeids:
            confidence = 0.7
        elif exit_code not in (0, 1):
            confidence = 0.4
        else:
            confidence = 0.55
        return PytestParseResult(
            parser_version=self.parser_version,
            parser_confidence=confidence,
            summary_counts=summary_counts,
            passed_nodeids=passed_nodeids,
            failed_nodeids=failed_nodeids,
            error_nodeids=error_nodeids,
            skipped_nodeids=skipped_nodeids,
            xfailed_nodeids=xfailed_nodeids,
            xpassed_nodeids=xpassed_nodeids,
            suite_completed=suite_completed,
            parse_warnings=parse_warnings,
            pytest_exit_reason=pytest_exit_reason,
        )

    def selector_statuses(
        self,
        selectors: list[str],
        stdout: str,
        stderr: str,
        exit_code: int | None,
        timeout: bool,
    ) -> tuple[list[dict[str, Any]], PytestParseResult]:
        parsed = self.parse_output(stdout, stderr, exit_code, timeout=timeout)
        passed = {_normalize_nodeid(item) for item in parsed.passed_nodeids}
        failed = {_normalize_nodeid(item) for item in parsed.failed_nodeids}
        errors = {_normalize_nodeid(item) for item in parsed.error_nodeids}
        skipped = {_normalize_nodeid(item) for item in parsed.skipped_nodeids}
        xfailed = {_normalize_nodeid(item) for item in parsed.xfailed_nodeids}
        xpassed = {_normalize_nodeid(item) for item in parsed.xpassed_nodeids}
        summary_failure_count = int(parsed.summary_counts.get("failed", 0)) + int(
            parsed.summary_counts.get("errors", 0)
        )
        parsed_failure_count = len(failed) + len(errors)
        can_infer_passed_from_absence = bool(
            parsed.suite_completed
            and (
                exit_code == 0
                or summary_failure_count == parsed_failure_count
                or summary_failure_count == 0
            )
        )
        cases: list[dict[str, Any]] = []
        parameterized_match_used = False
        for selector in selectors:
            normalized = _normalize_nodeid(selector)
            failed_match = _selector_match(normalized, failed)
            error_match = _selector_match(normalized, errors)
            skipped_match = (
                _selector_match(normalized, skipped)
                or _selector_match(normalized, xfailed)
                or _selector_match(normalized, xpassed)
            )
            passed_match = _selector_match(normalized, passed)
            failure_kinds: list[str] = []
            if failed_match is not None:
                failure_kinds.append("failed")
            if error_match is not None:
                failure_kinds.append("error")
            if failed_match and failed_match["match_strategy"] == "parameterized_selector_prefix":
                parameterized_match_used = True
            if error_match and error_match["match_strategy"] == "parameterized_selector_prefix":
                parameterized_match_used = True
            if passed_match and passed_match["match_strategy"] == "parameterized_selector_prefix":
                parameterized_match_used = True
            if error_match is not None:
                status = "error"
                status_source = "pytest_error_nodeid"
                status_match = error_match
            elif failed_match is not None:
                status = "failed"
                status_source = "pytest_failed_nodeid"
                status_match = failed_match
            elif skipped_match is not None:
                status = "skipped"
                status_source = "pytest_skipped_nodeid"
                status_match = skipped_match
            elif passed_match is not None:
                status = "passed"
                status_source = "pytest_passed_nodeid"
                status_match = passed_match
            elif can_infer_passed_from_absence:
                status = "passed"
                status_source = "absence_inference"
                status_match = None
            else:
                status = "unknown"
                status_source = "unmatched_selector"
                status_match = None
            case: dict[str, Any] = {
                "test_id": selector,
                "normalized_test_id": normalized,
                "status": status,
                "status_source": status_source,
                "match_strategy": (
                    status_match["match_strategy"] if status_match is not None else "none"
                ),
                "matched_nodeid": (
                    status_match["matched_nodeid"] if status_match is not None else None
                ),
                "failure_kinds": failure_kinds,
            }
            if failed_match is not None:
                case["matched_failed_nodeid"] = failed_match["matched_nodeid"]
                case["failed_match_strategy"] = failed_match["match_strategy"]
            if error_match is not None:
                case["matched_error_nodeid"] = error_match["matched_nodeid"]
                case["error_match_strategy"] = error_match["match_strategy"]
            cases.append(case)
        if parameterized_match_used and "parameterized_selector_match_used" not in parsed.parse_warnings:
            parsed.parse_warnings.append("parameterized_selector_match_used")
        return cases, parsed


def _parse_summary_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for count, label in re.findall(
        r"\b(\d+)\s+(failed|passed|errors?|skipped|xfailed|xpassed|deselected|warnings?)\b",
        text,
        flags=re.IGNORECASE,
    ):
        normalized = label.lower()
        if normalized == "error":
            normalized = "errors"
        if normalized == "warning":
            normalized = "warnings"
        counts[normalized] = counts.get(normalized, 0) + int(count)
    return counts


def _pytest_exit_reason(
    *,
    stdout: str,
    stderr: str,
    exit_code: int | None,
    timeout: bool,
    summary_counts: dict[str, int],
    failed_nodeids: set[str],
    error_nodeids: set[str],
) -> str:
    combined = f"{stdout}\n{stderr}".lower()
    if timeout:
        return "pytest_timeout"
    if exit_code == 0:
        return "pytest_passed"
    if _looks_like_import_or_config_error(combined):
        return "pytest_config_or_import_error"
    if _looks_like_collection_error(combined):
        return "pytest_collection_error"
    if _looks_like_usage_error(combined):
        return "pytest_usage_error"
    if exit_code == 5 or "no tests ran" in combined or "no tests collected" in combined:
        return "pytest_no_tests_collected"
    if exit_code == 2:
        return "pytest_interrupted"
    if exit_code == 3:
        return "pytest_internal_error"
    if exit_code == 4:
        return "pytest_usage_or_collection_error"
    if exit_code == 1:
        failure_count = int(summary_counts.get("failed", 0) or 0) + int(
            summary_counts.get("errors", 0) or 0
        )
        if failure_count or failed_nodeids or error_nodeids:
            return "pytest_test_failures"
        return "pytest_nonzero_without_test_facts"
    if exit_code is None:
        return "pytest_exit_code_unavailable"
    return "pytest_unknown_nonzero_exit"


def _looks_like_import_or_config_error(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "importerror",
            "modulenotfounderror",
            "cannot open shared object file",
            "dlopen",
            "shared library",
        )
    )


def _looks_like_collection_error(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "error collecting",
            "errors during collection",
            "collection error",
            "collected 0 items /",
        )
    )


def _looks_like_usage_error(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "usage:",
            "unrecognized arguments",
            "file or directory not found",
            "not found:",
            "invalid choice",
            "no match in any of",
        )
    )


def _parse_nodeids(text: str, prefix: str) -> set[str]:
    nodeids: set[str] = set()
    pattern = re.compile(rf"^\s*{re.escape(prefix)}\s+(.+)$", flags=re.MULTILINE)
    for match in pattern.finditer(text):
        nodeid = _extract_summary_nodeid(match.group(1))
        if nodeid and not nodeid.lower().startswith("collecting"):
            nodeids.add(nodeid)
    return nodeids


def _extract_summary_nodeid(summary_tail: str) -> str:
    tail = summary_tail.strip()
    if not tail:
        return ""
    split_index = _first_bracket_aware_summary_separator(tail)
    if split_index is not None:
        return tail[:split_index].strip()
    return tail.strip()


def _first_bracket_aware_summary_separator(text: str) -> int | None:
    bracket_depth = 0
    for index, char in enumerate(text):
        if char == "[":
            bracket_depth += 1
        elif char == "]" and bracket_depth:
            bracket_depth -= 1
        if bracket_depth:
            continue
        if text.startswith(" - ", index) or text.startswith(" -- ", index):
            return index
        if text.startswith(" [", index):
            return index
    return None


def _parse_progress_nodeids(text: str, status: str) -> set[str]:
    nodeids: set[str] = set()
    fallback_pattern = re.compile(
        rf"^\s*(?P<nodeid>.+?::.+?)\s+{re.escape(status)}\b",
        flags=re.MULTILINE | re.IGNORECASE,
    )
    for match in fallback_pattern.finditer(text):
        nodeid = match.group("nodeid").strip()
        if nodeid and not nodeid.upper().startswith(f"{status} "):
            nodeids.add(nodeid)
    return nodeids


def _normalize_nodeid(nodeid: str) -> str:
    normalized = nodeid.strip().rstrip(":")
    normalized = re.sub(
        r"^(FAILED|ERROR|PASSED|SKIPPED|XFAIL|XPASS)\s+",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized.strip().rstrip(":")


def _selector_matches_any(selector: str, nodeids: set[str]) -> bool:
    return _selector_match(selector, nodeids) is not None


def _selector_match(selector: str, nodeids: set[str]) -> dict[str, str] | None:
    for nodeid in sorted(nodeids):
        if nodeid == selector:
            return {"matched_nodeid": nodeid, "match_strategy": "exact"}
    for nodeid in sorted(nodeids):
        if nodeid.startswith(f"{selector}["):
            return {
                "matched_nodeid": nodeid,
                "match_strategy": "parameterized_selector_prefix",
            }
    for nodeid in sorted(nodeids):
        if nodeid.startswith(f"{selector}::"):
            return {"matched_nodeid": nodeid, "match_strategy": "descendant_selector_prefix"}
    return None
