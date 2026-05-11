import json
from pathlib import Path

from repo_harness.model_client import MockProviderClient
from repo_harness.model_client.mock import ERROR_SCENARIOS
from repo_harness.model_client.schemas import (
    ModelProviderOptions,
    ModelRequestContext,
    ProviderCredentialPolicy,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.trajectory import ArtifactRef, RunRecorder


def test_mock_provider_builds_tool_call_from_model_request_context(tmp_path: Path):
    request = _request(tmp_path)
    with RunRecorder("mock", tmp_path / "run", task_id="task_001") as recorder:
        response = MockProviderClient().generate(request=request, recorder=recorder)

    assert response.tool_calls[0].tool_name == "edit_file"
    assert response.model_call_event is not None
    assert response.model_call_event.provider == "mock"
    assert response.model_call_event.model_id == "mock-provider-v0"
    assert response.model_call_event.request_timeout_seconds == 12.5
    assert response.model_call_event.request_timeout_policy_facts == {
        "timeout_policy_version": "unit_test_timeout_policy"
    }
    raw_request = _read_artifact(tmp_path / "run", response.raw_provider_request_ref)
    assert raw_request["tool_schema_snapshot_ref"]["artifact_id"] == "tool_schema"
    assert raw_request["generation_config"] == {"temperature": 0.2, "max_output_tokens": 123}
    assert raw_request["provider_model_settings"] == {"setting": "value"}
    assert raw_request["scaffold_phase"] == "coder"
    assert raw_request["provider_options"]["provider_specific_options"]["mock_scenario"] == "tool_call_success"
    assert raw_request["tool_choice"] == "auto"
    assert raw_request["request_timeout_seconds"] == 12.5
    assert raw_request["request_timeout_policy_facts"] == {
        "timeout_policy_version": "unit_test_timeout_policy"
    }
    assert raw_request["raw_request_logging_policy"] == "redact_secrets"


def test_mock_provider_redacts_raw_artifacts(tmp_path: Path):
    request = _request(tmp_path)
    with RunRecorder("mock-redaction", tmp_path / "run", task_id="task_001") as recorder:
        response = MockProviderClient().generate(request=request, recorder=recorder)

    assert response.raw_provider_request_ref.redaction_status == "redacted"
    assert response.raw_provider_response_ref.redaction_status == "redacted"
    raw_text = (
        tmp_path / "run" / response.raw_provider_request_ref.relative_path
    ).read_text(encoding="utf-8")
    assert "Bearer" not in raw_text
    assert "sk-" not in raw_text
    assert "<REDACTED_CREDENTIAL>" in raw_text


def test_mock_provider_recursively_redacts_provider_specific_options(tmp_path: Path):
    request = _request(tmp_path)
    request.provider_options.provider_specific_options.update(
        {
            "api_key": "plain-secret-value-12345",
            "nested": {
                "token": "token-value-67890",
                "authorization": "Bearer visible-token-12345",
            },
            "safe_option": "visible",
        }
    )
    with RunRecorder("mock-redaction-options", tmp_path / "run", task_id="task_001") as recorder:
        response = MockProviderClient().generate(request=request, recorder=recorder)

    raw_request = _read_artifact(tmp_path / "run", response.raw_provider_request_ref)
    provider_options = raw_request["provider_options"]["provider_specific_options"]
    assert provider_options["api_key"] == "<REDACTED_CREDENTIAL>"
    assert provider_options["nested"]["token"] == "<REDACTED_CREDENTIAL>"
    assert provider_options["nested"]["authorization"] == "<REDACTED_CREDENTIAL>"
    assert provider_options["safe_option"] == "visible"
    raw_text = (
        tmp_path / "run" / response.raw_provider_request_ref.relative_path
    ).read_text(encoding="utf-8")
    assert "plain-secret-value-12345" not in raw_text
    assert "token-value-67890" not in raw_text
    assert "visible-token-12345" not in raw_text


def test_mock_provider_final_answer_scenario(tmp_path: Path):
    request = _request(tmp_path, scenario="final_answer")
    with RunRecorder("mock-final", tmp_path / "run", task_id="task_001") as recorder:
        response = MockProviderClient().generate(request=request, recorder=recorder)

    assert response.finish_reason == "stop"
    assert response.tool_calls == []
    assert response.assistant_message.content == "Mock provider final answer."


def test_mock_provider_error_scenarios_are_structured(tmp_path: Path):
    for scenario, expected_error in ERROR_SCENARIOS.items():
        request = _request(tmp_path / scenario, scenario=scenario)
        with RunRecorder(f"mock-{scenario}", tmp_path / scenario / "run", task_id="task_001") as recorder:
            response = MockProviderClient().generate(request=request, recorder=recorder)

        assert response.finish_reason == "error"
        assert response.model_error_type == expected_error
        assert response.model_call_event is not None
        assert response.model_call_event.model_error_type == expected_error


def _request(tmp_path: Path, *, scenario: str = "tool_call_success") -> ModelRequestContext:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return ModelRequestContext(
        run_id="mock",
        task_id="task_001",
        turn=2,
        model_call_id="mock_model_call_0002",
        prepared_messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": {"task": "fix calculator"}},
        ],
        prepared_messages_ref=_artifact_ref("prepared_messages"),
        model_input_hash="a" * 64,
        context_revision=2,
        provider_message_format="repo_harness_mock_messages_v0",
        context_truncation_facts={"strategy": "none"},
        omitted_context_facts={},
        generation_config={"temperature": 0.2, "max_output_tokens": 123},
        provider_model_settings={"setting": "value"},
        allowed_tool_definitions=[{"name": "edit_file"}, {"name": "run_tests"}],
        tool_choice="auto",
        tool_schema_snapshot_ref=_artifact_ref("tool_schema"),
        provider_options=ModelProviderOptions(
            provider="mock",
            model_id="mock-provider-v0",
            provider_specific_options={"mock_scenario": scenario},
        ),
        scaffold_id="simple_react",
        scaffold_phase="coder",
        run_config_facts_ref=RunConfigFactsRef(sha256="b" * 64),
        budget_state={"turn_count": 2},
        request_timeout_seconds=12.5,
        request_timeout_policy_facts={"timeout_policy_version": "unit_test_timeout_policy"},
        raw_request_logging_policy="redact_secrets",
        credential_policy=ProviderCredentialPolicy(
            credential_source="env_only",
            required_env_vars=["MOCK_API_KEY"],
            credential_source_label="environment",
        ),
        retry_policy="none",
    )


def _artifact_ref(kind: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=kind,
        relative_path=f"artifacts/{kind}.json",
        kind=kind,
        sha256="0" * 64,
        size_bytes=0,
    )


def _read_artifact(run_dir: Path, ref: ArtifactRef | None) -> dict:
    assert ref is not None
    return json.loads((run_dir / ref.relative_path).read_text(encoding="utf-8"))
