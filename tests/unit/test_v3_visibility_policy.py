from __future__ import annotations

import pytest
from pydantic import ValidationError

from repo_harness.v3_visibility import V3ContaminationDenylist, V3VisibilityPolicy


def test_v3_visibility_policy_rejects_hidden_model_visible_overlap():
    with pytest.raises(ValidationError, match="evaluator-only"):
        V3VisibilityPolicy(model_visible_categories={"issue_statement", "gold_patch"})


def test_v3_contamination_denylist_scans_required_surfaces():
    denylist = V3ContaminationDenylist()
    payload_by_surface = {
        "prompt": {"content": "contains gold_patch"},
        "prepared_messages": [{"role": "user", "content": "testPatch"}],
        "tool_observation": {"observation": "FAIL_TO_PASS selector"},
        "transcript": {"content_preview": "provider_raw_response"},
        "checkpoint": {"state": "resolvedStatus"},
        "context_compaction_report": {"summary": "final verifier hidden result"},
        "sft_export": {"target": "Authorization: Bearer secret"},
        "rl_export": {"reward": "reward_metadata"},
        "preference_export": {"chosen": "/Users/roger/workspace"},
    }

    for surface, payload in payload_by_surface.items():
        result = denylist.scan_payload(surface=surface, payload=payload)
        assert result.clean is False, surface
        assert result.findings, surface


def test_v3_contamination_denylist_allows_clean_public_payload():
    denylist = V3ContaminationDenylist()

    result = denylist.scan_payload(
        surface="prepared_messages",
        payload=[
            {
                "role": "user",
                "content": "Fix the public issue statement and produce a final patch.",
            }
        ],
    )

    assert result.clean is True
    denylist.assert_clean(surface="prepared_messages", payload={"content": "public only"})
    denylist.assert_clean(
        surface="prepared_messages",
        payload={"content": "This public issue was resolved upstream."},
    )
    denylist.assert_clean(
        surface="transcript",
        payload={
            "content_preview": (
                "WindowsPath('C:/Users/john_doe/AppData/Local/Temp/"
                "pytest-of-contoso/john_doe')"
            )
        },
    )
    denylist.assert_clean(
        surface="transcript",
        payload={"content_preview": r"C:\Python38\lib\pathlib.py:1266: FileNotFoundError"},
    )


def test_v3_contamination_denylist_rejects_delimited_host_paths():
    denylist = V3ContaminationDenylist()

    payloads = [
        {"content_preview": "artifact path: /Users/roger/Desktop/secret.txt"},
        {"content_preview": "artifact uri: file:///Users/roger/Desktop/secret.txt"},
        {"content_preview": "artifact path:/Users/roger/Desktop/secret.txt"},
    ]

    for payload in payloads:
        result = denylist.scan_payload(surface="transcript", payload=payload)
        assert result.clean is False
        assert any(finding.matched_term == "/Users/" for finding in result.findings)

    windows_home = "C:\\Users\\roger\\"
    windows_denylist = V3ContaminationDenylist(host_path_prefixes=[windows_home])
    result = windows_denylist.scan_payload(
        surface="transcript",
        payload={"content_preview": r"artifact path: C:\Users\roger\Desktop\secret.txt"},
    )
    assert result.clean is False
    assert any(finding.matched_term == windows_home for finding in result.findings)


def test_v3_contamination_denylist_rejects_normalized_key_and_value_forms():
    denylist = V3ContaminationDenylist()

    result = denylist.scan_payload(
        surface="tool_observation",
        payload={
            "officialStatus": "resolved",
            "goldPatch": "hash only",
            "selector": "failToPass",
            "other_selector": "passToPass",
        },
    )

    matched_terms = {finding.matched_term for finding in result.findings}
    assert "official_status" in matched_terms
    assert "resolved_status" in matched_terms
    assert "gold_patch" in matched_terms
    assert "failToPass" in matched_terms
    assert "passToPass" in matched_terms
