import json
from pathlib import Path
from typing import Any


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
REQUIRED_DENYLIST = {
    "hidden_verifier",
    "gold_patch",
    "accepted_label",
    "complete_reward_metadata",
    "provider_secret",
    "evaluator_only_logs",
    "absolute_run_directory",
    "final_verifier_artifact",
    "reward_metadata_artifact",
}
RAW_PROMPT_FORBIDDEN_TOKENS = {
    "hidden_verifier",
    "gold_patch",
    "accepted_label",
    "provider_secret",
    "evaluator_only_logs",
}
FORBIDDEN_BATCH_KEYS = {
    "audit_ref",
    "run_dir",
    "reward_metadata_path",
    "final_verifier_path",
    "gold_patch_path",
}


def _load_json(name: str) -> Any:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _collect_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_collect_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_collect_text(item) for item in value)
    return ""


def test_stage0h_visibility_fixture_declares_required_denylist() -> None:
    payload = _load_json("canonical_audit_path_access_denied.json")
    assert REQUIRED_DENYLIST.issubset(set(payload["visibility_denylist"]))


def test_stage0h_audit_artifact_tool_access_attempts_are_denied() -> None:
    payload = _load_json("canonical_audit_path_access_denied.json")
    attempts = payload["tool_access_attempts"]
    target_kinds = {attempt["target_kind"] for attempt in attempts}

    assert {"run_directory", "reward_metadata_artifact", "final_verifier_artifact", "gold_patch"}.issubset(target_kinds)
    for attempt in attempts:
        assert attempt["tool_name"] in {"read_file", "grep", "read_tool_result_artifact"}
        assert attempt["target_ref"].startswith("rh://audit/")
        assert attempt["expected_status"] == "denied"
        assert attempt["denied_reason"]


def test_stage0h_raw_prompt_and_messages_do_not_contain_hidden_content() -> None:
    payloads = [
        _load_json("canonical_episode_request.json"),
        _load_json("canonical_llm_gateway_request.json"),
    ]

    for payload in payloads:
        visible_text = _collect_text(payload.get("raw_prompt", [])) + " " + _collect_text(payload.get("messages", []))
        for forbidden in RAW_PROMPT_FORBIDDEN_TOKENS:
            assert forbidden not in visible_text


def test_stage0h_batch_visible_extra_fields_do_not_expose_audit_paths() -> None:
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(FIXTURE_ROOT.glob("canonical_*.json"))]

    for payload in payloads:
        for node in _walk(payload):
            extra_fields = node.get("extra_fields") if isinstance(node, dict) else None
            if not isinstance(extra_fields, dict):
                continue
            if not any(key.startswith("repo_harness_") for key in extra_fields):
                continue
            assert not (FORBIDDEN_BATCH_KEYS & set(extra_fields))
            for key, value in extra_fields.items():
                assert key.startswith("repo_harness_")
                assert not isinstance(value, (dict, list))
                if isinstance(value, str):
                    assert not value.startswith("/")
                    assert "/Users/" not in value


def test_stage0h_visibility_fixture_documents_forbidden_extra_field_examples() -> None:
    payload = _load_json("canonical_audit_path_access_denied.json")
    assert FORBIDDEN_BATCH_KEYS.issubset(set(payload["forbidden_extra_fields_examples"]))


def test_stage0h_audit_ref_is_structured_but_not_embedded_in_training_extra_fields() -> None:
    result = _load_json("canonical_episode_result.json")
    assert isinstance(result["audit_ref"], dict)
    assert "audit_ref" not in result["training_view"]["extra_fields"]

    multiturn = _load_json("canonical_multiturn_tool_episode_result.json")
    assert isinstance(multiturn["audit_ref"], dict)
    assert "audit_ref" not in multiturn["training_view"]["extra_fields"]
