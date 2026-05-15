import hashlib
import json
from pathlib import Path
from typing import Any


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
EXPECTED_CANONICAL_FILES = {
    "canonical_episode_request.json",
    "canonical_episode_result.json",
    "canonical_training_view.json",
    "canonical_audit_ref.json",
    "canonical_llm_gateway_request.json",
    "canonical_llm_gateway_response.json",
    "canonical_multiturn_tool_episode_result.json",
    "canonical_response_overflow_invalid_result.json",
    "canonical_empty_response_invalid_result.json",
    "canonical_mixed_logprob_batch_rejected.json",
    "canonical_audit_path_access_denied.json",
}
ALLOWED_ROUTES = {"verl", "openai", "deepseek", "local_vllm", "local_sglang", "replay", "mock"}
PROVIDER_ROUTES = {"openai", "deepseek"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _walk_key_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _walk_key_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_key_values(item)


def _all_fixture_payloads() -> dict[str, Any]:
    return {path.name: _load_json(path) for path in sorted(FIXTURE_ROOT.glob("canonical_*.json"))}


def test_stage0h_expected_fixture_files_are_present_and_parseable() -> None:
    actual = {path.name for path in FIXTURE_ROOT.glob("canonical_*.json")}
    assert actual == EXPECTED_CANONICAL_FILES

    for file_name in EXPECTED_CANONICAL_FILES:
        payload = _load_json(FIXTURE_ROOT / file_name)
        assert payload["contract_version"] == "repo_harness_verl_shared_contracts_v0"
        assert payload["fixture_kind"]


def test_stage0h_sha256_manifest_covers_all_canonical_fixtures() -> None:
    manifest = _load_json(FIXTURE_ROOT / "sha256_manifest.json")
    assert manifest["hash_algorithm"] == "sha256"
    assert set(manifest["files"]) == EXPECTED_CANONICAL_FILES

    for file_name, expected_sha256 in manifest["files"].items():
        actual_sha256 = hashlib.sha256((FIXTURE_ROOT / file_name).read_bytes()).hexdigest()
        assert actual_sha256 == expected_sha256


def test_stage0h_routes_use_the_single_shared_enum() -> None:
    payloads = _all_fixture_payloads()
    seen_routes: set[str] = set()

    for payload in payloads.values():
        for key, value in _walk_key_values(payload):
            if key in {"route", "llm_gateway_route", "gateway_route"}:
                assert value in ALLOWED_ROUTES
                seen_routes.add(value)

    assert {"verl", "openai", "deepseek"}.issubset(seen_routes)


def test_stage0h_provider_route_examples_are_marked_invalid_for_online_rl() -> None:
    request = _load_json(FIXTURE_ROOT / "canonical_episode_request.json")
    examples = request["provider_route_policy_examples"]
    assert examples

    for example in examples:
        assert example["route"] in PROVIDER_ROUTES
        assert example["invalid_for_online_rl"] is True
        assert "offline_diagnostic_replay" in example["allowed_uses"]


def test_stage0h_fixtures_do_not_use_absolute_local_paths() -> None:
    for file_name, payload in _all_fixture_payloads().items():
        for key, value in _walk_key_values(payload):
            if isinstance(value, str):
                assert not value.startswith("/"), (file_name, key, value)
                assert "/Users/" not in value, (file_name, key, value)


def test_stage0h_batch_extra_fields_are_namespaced_flat_scalars() -> None:
    scalar_types = (str, int, float, bool, type(None))
    for file_name, payload in _all_fixture_payloads().items():
        for node in _walk(payload):
            extra_fields = node.get("extra_fields") if isinstance(node, dict) else None
            if not isinstance(extra_fields, dict):
                continue
            if not any(key.startswith("repo_harness_") for key in extra_fields):
                continue
            for key, value in extra_fields.items():
                assert key.startswith("repo_harness_"), (file_name, key)
                assert isinstance(value, scalar_types), (file_name, key, value)
            assert "audit_ref" not in extra_fields
            assert "run_dir" not in extra_fields
