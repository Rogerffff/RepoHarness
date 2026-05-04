"""V4 visibility policy and contamination denylist.

这份规则集先服务阶段 0 input freeze，后续 V4 阶段继续复用同一
denylist version、allowlist policy version 和扫描语义。
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    V4_ALLOWLIST_POLICY_VERSION,
    V4_CONTAMINATION_DENYLIST_VERSION,
    V4_VISIBILITY_POLICY_VERSION,
)


V4_VISIBILITY_SURFACES = (
    "adapter_visible_task_input",
    "prepared_messages",
    "model_visible_transcript",
    "events",
    "artifacts_manifest",
    "run_metadata",
    "checkpoints",
    "context_compaction_or_replacement",
    "export_records",
    "dataset_card",
    "run_card",
    "export_card",
    "provenance_summary",
    "repro_command_index",
    "implementation_log",
    "acceptance_inputs",
    "acceptance_report",
    "acceptance_command_log",
    "acceptance_bundle",
)
V4_CARD_CLAIM_DENYLIST_VERSION = "repo_harness_v4_card_claim_denylist_v0"
V4_FORBIDDEN_CARD_CLAIMS = (
    "无需人工审查即可直接训练",
    "直接训练即可",
    "公开 leaderboard 可比",
    "public leaderboard comparable",
    "生产级安全沙箱",
    "production grade sandbox",
    "complete SWE-Bench Lite",
    "完整 SWE-Bench Lite",
    "已经训练出 coding agent",
    "trained a coding agent",
)


class V4ContaminationFinding(StrictBaseModel):
    schema_version: str = "repo_harness_v4_contamination_finding_v0"
    surface: str
    path: str
    matched_term: str
    category: Literal[
        "evaluator_only",
        "gold_or_patch",
        "official_evaluation",
        "provider_raw",
        "credential",
        "pull_request_material",
        "ai_session_marker",
        "verifier_raw",
        "reward_or_label",
        "hidden_selector",
        "source_identity",
    ]


class V4ContaminationScanResult(StrictBaseModel):
    schema_version: str = "repo_harness_v4_contamination_scan_result_v0"
    surface: str
    clean: bool
    findings: list[V4ContaminationFinding] = Field(default_factory=list)


class V4ContaminationDenylist(StrictBaseModel):
    schema_version: str = V4_CONTAMINATION_DENYLIST_VERSION
    visibility_policy_version: str = V4_VISIBILITY_POLICY_VERSION
    allowlist_policy_version: str = V4_ALLOWLIST_POLICY_VERSION
    forbidden_terms: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "evaluator_only": [
                "evaluator_only evidence",
                "reward_only evidence",
                "hidden reference",
            ],
            "gold_or_patch": [
                "gold_patch",
                "gold patch",
                "raw test patch",
                "test_patch",
                "patch diff",
                "patch_text",
                "raw_patch",
            ],
            "official_evaluation": [
                "official harness report",
                "official_harness_report",
                "official report",
                "official_report",
                "official resolved status",
                "resolved_status",
                "unresolved_status",
            ],
            "provider_raw": [
                "provider_raw_response",
                "provider raw response",
                "provider_raw_request",
                "raw_provider_response",
            ],
            "credential": [
                "Authorization",
                "api_key",
                "credential marker",
                "provider credential",
            ],
            "pull_request_material": [
                "pull_request_body",
                "pull request body",
                "pr_body",
                "pull_request_diff",
                "pull request diff",
                "pr_diff",
                "review comment",
                "review suggestion",
                "raw commit message",
                "raw_commit_message",
                "commit message after base",
                "fix commit url",
                "merge commit url",
            ],
            "ai_session_marker": [
                "claude.ai",
                "claude.ai/share",
                "chatgpt.com/share",
                "codex session",
                "codex session URL",
                "ai coding session",
                "AI session URL",
                "llm coding session",
            ],
            "verifier_raw": [
                "verifier_raw_output",
                "verifier raw output",
                "verifier_trace",
                "docker verifier stdout",
                "docker verifier stderr",
                "flaky verifier stdout",
                "flaky verifier stderr",
            ],
            "reward_or_label": [
                "reward scalar",
                "reward label",
                "final_reward",
            ],
            "hidden_selector": [
                "hidden selector",
                "hidden_selector",
                "FAIL_TO_PASS",
                "PASS_TO_PASS",
            ],
        }
    )
    adapter_visible_regexes: dict[str, str] = Field(
        default_factory=lambda: {
            "pull_request_url": r"https?://github\.com/[^/\s]+/[^/\s]+/pull/\d+",
            "issue_url": r"https?://github\.com/[^/\s]+/[^/\s]+/issues/\d+",
            "pull_request_number": r"(?i)\b(?:pr|pull request)\s*#?\s*\d+\b",
            "issue_number": r"(?i)\bissue\s*#?\s*\d+\b",
            "fix_commit_hash": r"\b[0-9a-f]{40}\b",
        }
    )

    def scan_payload(
        self,
        *,
        surface: str,
        payload: Any,
        adapter_visible: bool = False,
    ) -> V4ContaminationScanResult:
        findings = self._scan_value(
            surface=surface,
            value=payload,
            path="$",
            adapter_visible=adapter_visible,
        )
        return V4ContaminationScanResult(surface=surface, clean=not findings, findings=findings)

    def assert_clean(
        self,
        *,
        surface: str,
        payload: Any,
        adapter_visible: bool = False,
    ) -> None:
        result = self.scan_payload(
            surface=surface,
            payload=payload,
            adapter_visible=adapter_visible,
        )
        if not result.clean:
            terms = ", ".join(sorted({finding.matched_term for finding in result.findings}))
            raise ValueError(f"V4 contamination denylist failed for {surface}: {terms}")

    def _scan_value(
        self,
        *,
        surface: str,
        value: Any,
        path: str,
        adapter_visible: bool,
    ) -> list[V4ContaminationFinding]:
        findings: list[V4ContaminationFinding] = []
        if isinstance(value, str):
            findings.extend(
                self._scan_text(
                    surface=surface,
                    text=value,
                    path=path,
                    adapter_visible=adapter_visible,
                )
            )
        elif isinstance(value, dict):
            for key, child in value.items():
                key_path = f"{path}.{key}"
                findings.extend(
                    self._scan_text(
                        surface=surface,
                        text=str(key),
                        path=f"{key_path}.__key__",
                        adapter_visible=adapter_visible,
                    )
                )
                findings.extend(
                    self._scan_value(
                        surface=surface,
                        value=child,
                        path=key_path,
                        adapter_visible=adapter_visible,
                    )
                )
        elif isinstance(value, list):
            for index, child in enumerate(value):
                findings.extend(
                    self._scan_value(
                        surface=surface,
                        value=child,
                        path=f"{path}[{index}]",
                        adapter_visible=adapter_visible,
                    )
                )
        return findings

    def _scan_text(
        self,
        *,
        surface: str,
        text: str,
        path: str,
        adapter_visible: bool,
    ) -> list[V4ContaminationFinding]:
        findings: list[V4ContaminationFinding] = []
        text_lower = text.lower()
        normalized_text = _normalize_visibility_term(text)
        for category, terms in self.forbidden_terms.items():
            for term in terms:
                normalized_term = _normalize_visibility_term(term)
                if term.lower() in text_lower or (
                    normalized_term and normalized_term in normalized_text
                ):
                    findings.append(
                        V4ContaminationFinding(
                            surface=surface,
                            path=path,
                            matched_term=term,
                            category=category,  # type: ignore[arg-type]
                        )
                    )
        if adapter_visible:
            for term, pattern in self.adapter_visible_regexes.items():
                if re.search(pattern, text):
                    findings.append(
                        V4ContaminationFinding(
                            surface=surface,
                            path=path,
                            matched_term=term,
                            category="source_identity",
                        )
                    )
        return findings


def _normalize_visibility_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def v4_contamination_denylist_sha256() -> str:
    """Return a stable hash for the active V4 denylist rules."""

    denylist = V4ContaminationDenylist()
    payload = {
        "schema_version": denylist.schema_version,
        "visibility_policy_version": denylist.visibility_policy_version,
        "allowlist_policy_version": denylist.allowlist_policy_version,
        "forbidden_terms": denylist.forbidden_terms,
        "adapter_visible_regexes": denylist.adapter_visible_regexes,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def v4_card_claim_denylist_sha256() -> str:
    """Return a stable hash for V4 card claim deny rules."""

    payload = {
        "schema_version": V4_CARD_CLAIM_DENYLIST_VERSION,
        "visibility_policy_version": V4_VISIBILITY_POLICY_VERSION,
        "allowlist_policy_version": V4_ALLOWLIST_POLICY_VERSION,
        "forbidden_claims": list(V4_FORBIDDEN_CARD_CLAIMS),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def scan_v4_forbidden_card_claims(*, surface: str, payload: Any) -> list[dict[str, str]]:
    """Scan cards and card-adjacent docs for prohibited Stage 7 claims."""

    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = text.lower()
    findings: list[dict[str, str]] = []
    for claim in V4_FORBIDDEN_CARD_CLAIMS:
        if claim.lower() in lowered:
            findings.append(
                {
                    "schema_version": "repo_harness_v4_card_claim_finding_v0",
                    "surface": surface,
                    "path": "$",
                    "matched_term": claim,
                    "category": "forbidden_card_claim",
                    "policy_version": V4_CARD_CLAIM_DENYLIST_VERSION,
                }
            )
    return findings
