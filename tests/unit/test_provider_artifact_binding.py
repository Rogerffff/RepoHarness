import json
from pathlib import Path
from typing import Any

from repo_harness.model_client.providers.common import (
    build_chat_completion_payload,
    write_provider_request_artifact,
    write_provider_response_artifact,
)
from repo_harness.model_client.redaction import REDACTED_CREDENTIAL, redact_provider_payload_with_report
from repo_harness.model_client.schemas import (
    ModelProviderOptions,
    ModelRequestContext,
    ProviderCredentialPolicy,
)
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.trajectory import ArtifactRef, RunRecorder


def test_provider_redaction_is_span_based_for_ordinary_long_text() -> None:
    long_issue = (
        "Fix parser case ABC123 where a long issue statement includes digits, paths, and "
        "repository context that must remain auditable for the benchmark report."
    )
    redacted, report = redact_provider_payload_with_report(
        {
            "messages": [{"role": "user", "content": long_issue}],
            "note": f"api_key=sk-test-secret-value-1234567890 remains hidden while {long_issue}",
            "authorization": "Bearer sk-header-secret-value-1234567890",
        }
    )

    assert redacted["messages"][0]["content"] == long_issue
    assert REDACTED_CREDENTIAL in redacted["note"]
    assert "sk-test-secret-value" not in redacted["note"]
    assert redacted["authorization"] == REDACTED_CREDENTIAL
    assert report["secret_field_redaction_count"] == 1
    assert report["secret_span_redaction_count"] >= 1
    assert report["ordinary_text_whole_field_redaction_allowed"] is False


def test_provider_redaction_handles_quoted_assignments_and_camel_case_tokens() -> None:
    redacted, report = redact_provider_payload_with_report(
        {
            "message": 'password="hunter22" token: "abcdef123456" plain content stays',
            "accessToken": "opaque-access-token-value",
            "refreshToken": "opaque-refresh-token-value",
            "idToken": "opaque-id-token-value",
        }
    )

    assert 'password="<REDACTED_CREDENTIAL>"' in redacted["message"]
    assert 'token: "<REDACTED_CREDENTIAL>"' in redacted["message"]
    assert "hunter22" not in redacted["message"]
    assert "abcdef123456" not in redacted["message"]
    assert redacted["accessToken"] == REDACTED_CREDENTIAL
    assert redacted["refreshToken"] == REDACTED_CREDENTIAL
    assert redacted["idToken"] == REDACTED_CREDENTIAL
    assert report["secret_field_redaction_count"] == 3
    assert report["secret_span_redaction_count"] == 2


def test_provider_request_artifact_binds_prepared_messages_and_body_projection(tmp_path: Path) -> None:
    request = _request(prepared_messages=[
        {"role": "system", "content": "system"},
        {"role": "user", "content": "Fix issue ABC123 without leaking sk-test-secret-value-1234567890."},
    ])
    provider_payload = build_chat_completion_payload(
        request,
        model_id="gpt-5.4-nano",
        provider="openai",
        base_url="https://api.openai.com/v1",
    )
    with RunRecorder("provider-binding", tmp_path / "run", task_id="task") as recorder:
        ref = write_provider_request_artifact(
            provider="openai",
            recorder=recorder,
            payload=provider_payload,
            request=request,
        )

    payload = json.loads((tmp_path / "run" / ref.relative_path).read_text(encoding="utf-8"))
    assert payload["prepared_messages_ref"]["artifact_id"] == "prepared_messages"
    assert payload["tool_schema_snapshot_ref"]["artifact_id"] == "tool_schema"
    assert payload["model_input_hash"] == request.model_input_hash
    assert payload["prepared_messages_body_equivalent"] is True
    assert payload["provider_body_hash_before_redaction"] != payload["redacted_body_hash"]
    assert "sk-test-secret-value" not in json.dumps(payload, ensure_ascii=False)
    assert REDACTED_CREDENTIAL in json.dumps(payload, ensure_ascii=False)


def test_provider_response_artifact_binds_request_and_parsed_tool_calls(tmp_path: Path) -> None:
    request = _request()
    response_payload = {
        "schema_version": "repo_harness_openai_provider_response_v0",
        "provider": "openai",
        "status": "ok",
        "response": {
            "id": "response-1",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": "I will inspect.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "{\"path\":\"demo.py\"}",
                                },
                            }
                        ],
                    },
                }
            ],
        },
    }
    with RunRecorder("provider-response-binding", tmp_path / "run", task_id="task") as recorder:
        request_ref = recorder.write_json_artifact("raw_openai_provider_request", {"request": "redacted"})
        response_ref = write_provider_response_artifact(
            provider="openai",
            recorder=recorder,
            payload=response_payload,
            request=request,
            raw_request_ref=request_ref,
        )

    payload = json.loads((tmp_path / "run" / response_ref.relative_path).read_text(encoding="utf-8"))
    assert payload["raw_provider_request_ref"]["sha256"] == request_ref.sha256
    assert payload["prepared_messages_ref"]["artifact_id"] == "prepared_messages"
    assert payload["tool_schema_snapshot_ref"]["artifact_id"] == "tool_schema"
    assert payload["finish_reason"] == "tool_calls"
    assert payload["parsed_tool_calls_hash"] != "0" * 64
    assert payload["response_body_hash_before_redaction"] == payload["redacted_response_body_hash"]


def _request(*, prepared_messages: list[dict[str, Any]] | None = None) -> ModelRequestContext:
    return ModelRequestContext(
        run_id="provider-binding-run",
        task_id="task",
        turn=1,
        model_call_id="provider-binding-run_model_call_0001",
        prepared_messages=prepared_messages
        or [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "Fix the issue."},
        ],
        prepared_messages_ref=_artifact_ref("prepared_messages"),
        model_input_hash="a" * 64,
        context_revision=1,
        provider_message_format="repo_harness_messages_v0",
        context_truncation_facts={},
        omitted_context_facts={},
        generation_config={"temperature": 0.0, "max_output_tokens": 128},
        provider_model_settings={},
        allowed_tool_definitions=[
            {
                "name": "read_file",
                "description": "Read a file",
                "model_visible_prompt": "Use read_file with path.",
                "input_schema": {"type": "object", "required": ["path"]},
            }
        ],
        tool_choice="auto",
        tool_schema_snapshot_ref=_artifact_ref("tool_schema"),
        provider_options=ModelProviderOptions(
            provider="openai",
            model_id="gpt-5.4-nano",
            provider_specific_options={},
        ),
        scaffold_id="patch_focused_react",
        scaffold_phase="react",
        run_config_facts_ref=RunConfigFactsRef(sha256="b" * 64),
        budget_state={"turn_count": 1},
        request_timeout_seconds=10,
        raw_request_logging_policy="redact_secrets",
        credential_policy=ProviderCredentialPolicy(
            credential_source="env_only",
            required_env_vars=["OPENAI_API_KEY"],
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
