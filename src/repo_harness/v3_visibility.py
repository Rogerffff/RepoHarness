"""V3 visibility policy and contamination denylist."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    V3_CONTAMINATION_DENYLIST_VERSION,
    V3_VISIBILITY_POLICY_VERSION,
)


V3_VISIBILITY_SURFACES = (
    "prompt",
    "prepared_messages",
    "tool_observation",
    "transcript",
    "checkpoint",
    "context_compaction_report",
    "sft_export",
    "rl_export",
    "preference_export",
    "acceptance_input",
)


class V3ContaminationFinding(StrictBaseModel):
    schema_version: str = "repo_harness_v3_contamination_finding_v0"
    surface: str
    path: str
    matched_term: str
    category: Literal[
        "hidden_reference",
        "official_evaluation",
        "provider_raw",
        "credential",
        "host_path",
        "verifier_hidden_result",
        "reward_or_outcome",
    ]


class V3ContaminationScanResult(StrictBaseModel):
    schema_version: str = "repo_harness_v3_contamination_scan_result_v0"
    surface: str
    clean: bool
    findings: list[V3ContaminationFinding] = Field(default_factory=list)


class V3VisibilityPolicy(StrictBaseModel):
    schema_version: str = V3_VISIBILITY_POLICY_VERSION
    model_visible_categories: set[str] = Field(
        default_factory=lambda: {
            "issue_statement",
            "public_repo_metadata",
            "public_setup_hint",
            "public_tool_result_preview",
        }
    )
    evaluator_only_categories: set[str] = Field(
        default_factory=lambda: {
            "gold_patch",
            "test_patch",
            "fail_to_pass_tests",
            "pass_to_pass_tests",
            "official_report",
            "resolved_status",
            "final_verifier_hidden_result",
        }
    )
    audit_only_categories: set[str] = Field(
        default_factory=lambda: {
            "provider_raw_request",
            "provider_raw_response",
            "reasoning_summary_raw",
            "credential_status_detail",
            "host_absolute_path",
        }
    )
    training_payload_policy: str = "model_visible_only_after_v3_denylist_scan"

    @model_validator(mode="after")
    def hidden_categories_are_not_model_visible(self) -> "V3VisibilityPolicy":
        overlap = self.model_visible_categories.intersection(self.evaluator_only_categories)
        if overlap:
            raise ValueError(
                "model_visible_categories 不能包含 evaluator-only 类别："
                + ", ".join(sorted(overlap))
            )
        audit_overlap = self.model_visible_categories.intersection(self.audit_only_categories)
        if audit_overlap:
            raise ValueError(
                "model_visible_categories 不能包含 audit-only 类别："
                + ", ".join(sorted(audit_overlap))
            )
        return self


class V3ContaminationDenylist(StrictBaseModel):
    schema_version: str = V3_CONTAMINATION_DENYLIST_VERSION
    visibility_policy_version: str = V3_VISIBILITY_POLICY_VERSION
    forbidden_terms: dict[str, list[str]] = Field(default_factory=lambda: {
        "hidden_reference": [
            "gold_patch",
            "test_patch",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
            "failToPass",
            "passToPass",
            "oracle_hidden_feedback",
            "decontamination_metadata",
        ],
        "official_evaluation": [
            "official_status",
            "official_report",
            "official_harness",
            "completed_ids",
            "submitted_ids",
            "resolved_ids",
            "unresolved_ids",
            "resolved_status",
            "unresolved_status",
        ],
        "provider_raw": [
            "provider_raw_request",
            "provider_raw_response",
            "reasoning_summary",
            "reasoning summary",
        ],
        "credential": [
            "Authorization",
            "api_key",
            "credential_path",
            "credential_status_detail",
        ],
        "verifier_hidden_result": [
            "final_verifier_hidden_result",
            "hidden_failure_diagnostics",
            "hidden verifier result",
        ],
        "reward_or_outcome": [
            "reward_metadata",
            "run_outcome",
            "final_reward",
            "hidden failure diagnostics",
        ],
    })
    host_path_prefixes: list[str] = Field(
        default_factory=lambda: _default_host_path_prefixes()
    )
    status_value_terms: dict[str, str] = Field(
        default_factory=lambda: {
            "resolved": "resolved_status",
            "unresolved": "unresolved_status",
        }
    )

    def scan_payload(self, *, surface: str, payload: Any) -> V3ContaminationScanResult:
        findings = self._scan_value(surface=surface, value=payload, path="$")
        return V3ContaminationScanResult(
            surface=surface,
            clean=not findings,
            findings=findings,
        )

    def assert_clean(self, *, surface: str, payload: Any) -> None:
        result = self.scan_payload(surface=surface, payload=payload)
        if not result.clean:
            terms = ", ".join(sorted({finding.matched_term for finding in result.findings}))
            raise ValueError(f"V3 contamination denylist failed for {surface}: {terms}")

    def _scan_value(
        self,
        *,
        surface: str,
        value: Any,
        path: str,
    ) -> list[V3ContaminationFinding]:
        findings: list[V3ContaminationFinding] = []
        if isinstance(value, str):
            findings.extend(self._scan_text(surface=surface, text=value, path=path))
        elif isinstance(value, dict):
            for key, child in value.items():
                key_path = f"{path}.{key}"
                normalized_key = _normalize_visibility_term(str(key))
                findings.extend(
                    self._scan_text(surface=surface, text=str(key), path=f"{key_path}.__key__")
                )
                if normalized_key in self.status_value_terms:
                    findings.append(
                        V3ContaminationFinding(
                            surface=surface,
                            path=f"{key_path}.__key__",
                            matched_term=self.status_value_terms[normalized_key],
                            category="official_evaluation",
                        )
                    )
                if _is_status_key(normalized_key) and isinstance(child, str):
                    findings.extend(
                        self._scan_status_value(
                            surface=surface,
                            text=child,
                            path=key_path,
                        )
                    )
                findings.extend(self._scan_value(surface=surface, value=child, path=key_path))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                findings.extend(self._scan_value(surface=surface, value=child, path=f"{path}[{index}]"))
        return findings

    def _scan_text(
        self,
        *,
        surface: str,
        text: str,
        path: str,
    ) -> list[V3ContaminationFinding]:
        findings: list[V3ContaminationFinding] = []
        text_lower = text.lower()
        normalized_text = _normalize_visibility_term(text)
        for category, terms in self.forbidden_terms.items():
            for term in terms:
                normalized_term = _normalize_visibility_term(term)
                if term.lower() in text_lower or (
                    normalized_term and normalized_term in normalized_text
                ):
                    findings.append(
                        V3ContaminationFinding(
                            surface=surface,
                            path=path,
                            matched_term=term,
                            category=category,  # type: ignore[arg-type]
                        )
                    )
        for prefix in self.host_path_prefixes:
            if _contains_host_path_prefix(text, prefix):
                findings.append(
                    V3ContaminationFinding(
                        surface=surface,
                        path=path,
                        matched_term=prefix,
                        category="host_path",
                    )
                )
        return findings

    def _scan_status_value(
        self,
        *,
        surface: str,
        text: str,
        path: str,
    ) -> list[V3ContaminationFinding]:
        normalized_text = _normalize_visibility_term(text)
        matched_term = self.status_value_terms.get(normalized_text)
        if matched_term is None:
            return []
        return [
            V3ContaminationFinding(
                surface=surface,
                path=path,
                matched_term=matched_term,
                category="official_evaluation",
            )
        ]


def _normalize_visibility_term(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def _is_status_key(normalized_key: str) -> bool:
    return "status" in normalized_key or normalized_key in {
        "resolved",
        "unresolved",
        "officialstatus",
    }


def _contains_host_path_prefix(text: str, prefix: str) -> bool:
    start = text.find(prefix)
    while start != -1:
        if _is_windows_drive_path_prefix(text, start):
            start = text.find(prefix, start + 1)
            continue
        if start == 0:
            return True
        previous = text[start - 1]
        if previous.isspace() or previous in {"'", '"', "`", "(", "[", "{", "<", "=", ":", "/"}:
            return True
        start = text.find(prefix, start + 1)
    return False


def _is_windows_drive_path_prefix(text: str, prefix_start: int) -> bool:
    drive_index = prefix_start - 2
    colon_index = prefix_start - 1
    if drive_index < 0 or text[colon_index] != ":":
        return False
    if not text[drive_index].isalpha():
        return False
    if drive_index == 0:
        return True
    return not text[drive_index - 1].isalnum()


def _default_host_path_prefixes() -> list[str]:
    prefixes = ["/Users/", "/private/", "C:\\", "D:\\"]
    home = Path.home().as_posix().rstrip("/")
    if home and home not in {"/", "/root"}:
        prefixes.append(f"{home}/")
    return list(dict.fromkeys(prefixes))
