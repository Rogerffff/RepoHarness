import asyncio
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from repo_harness.rl import (
    FakeLLMGateway,
    LLMGateway,
    LLMGatewayRequest,
    LLMGatewayResponse,
    ProviderRoutePolicy,
    RepoHarnessEpisodeRequest,
    default_invalid_for_online_rl,
    validate_batch_extra_fields,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
OFFLINE_ALLOWED_USES = [
    "evaluation",
    "teacher_data_generation",
    "sft_export",
    "preference_data",
    "offline_diagnostic_replay",
]


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_stage1_provider_routes_default_invalid_for_online_rl() -> None:
    assert default_invalid_for_online_rl("openai") is True
    assert default_invalid_for_online_rl("deepseek") is True
    assert default_invalid_for_online_rl("mock") is True
    assert default_invalid_for_online_rl("replay") is True
    assert default_invalid_for_online_rl("local_vllm") is True
    assert default_invalid_for_online_rl("local_sglang") is True
    assert default_invalid_for_online_rl("verl") is False

    ProviderRoutePolicy(route="openai", invalid_for_online_rl=True, allowed_uses=OFFLINE_ALLOWED_USES)
    defaulted = ProviderRoutePolicy(route="openai", allowed_uses=OFFLINE_ALLOWED_USES)
    assert defaulted.invalid_for_online_rl is True
    subset = ProviderRoutePolicy(route="openai", allowed_uses=["evaluation"])
    assert subset.invalid_for_online_rl is True

    with pytest.raises(ValidationError, match="provider routes must default invalid_for_online_rl=true"):
        ProviderRoutePolicy(route="openai", invalid_for_online_rl=False, allowed_uses=OFFLINE_ALLOWED_USES)
    with pytest.raises(ValidationError, match="unknown offline provider allowed use"):
        ProviderRoutePolicy(route="openai", allowed_uses=["online_ppo_rollout"])


def test_stage1_batch_extra_fields_reject_nested_audit_and_paths() -> None:
    with pytest.raises(ValueError, match="flat scalar"):
        validate_batch_extra_fields({"repo_harness_audit_manifest_ref": {"nested": "audit_ref"}})

    with pytest.raises(ValueError, match="absolute local path"):
        validate_batch_extra_fields({"repo_harness_reward_metadata_ref": "/Users/roger/secret/reward.json"})

    with pytest.raises(ValueError, match="forbidden batch extra field"):
        validate_batch_extra_fields({"repo_harness_audit_ref": "rh://audit/run/full-object"})


@pytest.mark.parametrize(
    "key",
    [
        "repo_harness_hidden_verifier",
        "repo_harness_gold_patch",
        "repo_harness_provider_secret",
        "repo_harness_complete_reward_metadata",
        "repo_harness_evaluator_only_logs",
        "repo_harness_run_dir",
    ],
)
def test_stage1_batch_extra_fields_reject_namespaced_evaluator_only_keys(key: str) -> None:
    with pytest.raises(ValueError, match="forbidden batch extra field"):
        validate_batch_extra_fields({key: "secret"})


def test_stage1_gateway_extra_fields_are_not_batch_extra_fields() -> None:
    payload = _load_json("canonical_llm_gateway_response.json")
    payload["extra_fields"] = {
        "global_steps": 10,
        "min_global_steps": 10,
        "max_global_steps": 10,
    }
    LLMGatewayResponse.model_validate(payload)

    payload["extra_fields"] = {"audit_ref": {"run_dir": "runs/example"}}
    with pytest.raises(ValidationError, match="forbidden gateway extra field"):
        LLMGatewayResponse.model_validate(payload)


@pytest.mark.parametrize(
    "extra_fields",
    [
        {"safe_container": ["repo_harness_gold_patch"]},
        {"safe_container": {"nested": ["repo_harness_gold_patch"]}},
    ],
)
def test_stage1_gateway_extra_fields_reject_list_value_evaluator_only_leaks(
    extra_fields: dict[str, Any],
) -> None:
    payload = _load_json("canonical_llm_gateway_response.json")
    payload["extra_fields"] = extra_fields

    with pytest.raises(ValidationError, match="forbidden gateway extra field value"):
        LLMGatewayResponse.model_validate(payload)


def test_stage1_gateway_response_mask_must_be_all_model_generated_tokens() -> None:
    payload = _load_json("canonical_llm_gateway_response.json")
    payload["response_mask"] = [0, 1]
    payload["output_logprobs"] = [0.0, -0.12]

    with pytest.raises(ValidationError, match="LLMGatewayResponse.response_mask"):
        LLMGatewayResponse.model_validate(payload)


@pytest.mark.parametrize(
    ("fixture_name", "field_name", "payload_value"),
    [
        (
            "canonical_episode_request.json",
            "raw_prompt",
            [{"role": "user", "hidden_verifier": "secret verifier output"}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "messages",
            [{"role": "user", "gold_patch": "diff contents"}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "tools",
            [{"type": "function", "function": {"name": "hidden_verifier", "description": "secret"}}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "tools",
            [{"type": "function", "function": {"name": "hiddenVerifier", "description": "secret"}}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "tools",
            [{"type": "function", "function": {"name": "goldPatch", "description": "secret"}}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "tools",
            [{"type": "function", "function": {"name": "providerSecret", "description": "secret"}}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "tools",
            [{"type": "function", "function": {"name": "acceptedLabel", "description": "secret"}}],
        ),
        (
            "canonical_llm_gateway_request.json",
            "tools",
            [{"type": "function", "function": {"name": "completeRewardMetadata", "description": "secret"}}],
        ),
    ],
)
def test_stage1_model_visible_content_rejects_forbidden_keys(
    fixture_name: str,
    field_name: str,
    payload_value: list[dict[str, str]],
) -> None:
    payload = _load_json(fixture_name)
    payload[field_name] = payload_value

    model_cls = RepoHarnessEpisodeRequest if field_name == "raw_prompt" else LLMGatewayRequest
    with pytest.raises(ValidationError, match=field_name):
        model_cls.model_validate(payload)


def test_stage1_fake_gateway_implements_minimal_protocol() -> None:
    request = LLMGatewayRequest.model_validate(_load_json("canonical_llm_gateway_request.json"))
    gateway = FakeLLMGateway()

    assert isinstance(gateway, LLMGateway)
    assert inspect.iscoroutinefunction(FakeLLMGateway.generate_turn)
    response = asyncio.run(gateway.generate_turn(request))

    assert response.route == "verl"
    assert response.inference_backend == "sglang"
    assert response.model_call_id == "model-call-001"
    assert response.output_token_ids
    assert response.output_logprobs is not None
    assert len(response.output_token_ids) == len(response.output_logprobs) == len(response.response_mask)
    assert gateway.requests == [request]


def test_stage1_rl_schema_package_does_not_import_verl() -> None:
    package_root = Path(__file__).resolve().parents[2] / "src" / "repo_harness" / "rl"
    for path in sorted(package_root.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "import verl" not in text
        assert "from verl" not in text
