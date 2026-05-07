"""Provider failure injection smoke for pre-verl readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repo_harness.agent_loop import AgentLoop
from repo_harness.budget import BudgetManager
from repo_harness.errors import ConfigError
from repo_harness.model_client import ModelCallEvent, ModelMessage, ModelRequestContext, ModelResponse
from repo_harness.model_client.providers.common import (
    ProviderCredential,
    ProviderErrorInfo,
    ProviderRequestError,
)
from repo_harness.model_client.providers.deepseek import DeepSeekProviderClient
from repo_harness.model_client.schemas import ModelProviderOptions, ProviderCredentialPolicy
from repo_harness.run_metadata import RunConfigFactsRef
from repo_harness.schema_base import stable_hash
from repo_harness.tools import ToolExecutor
from repo_harness.trajectory import ArtifactRef, RunRecorder, TrajectoryEvent

PRE_VERL_PROVIDER_FAILURE_INJECTION_REPORT_VERSION = (
    "repo_harness_pre_verl_provider_failure_injection_report_v0"
)

DEFAULT_PROVIDER_FAILURE_INJECTION_SCENARIOS = [
    "retryable_429",
    "timeout",
    "provider_error_500",
    "auth_error",
    "length",
    "malformed_tool_call",
    "missing_function_name",
    "arguments_not_object",
    "invalid_response",
]


def run_provider_failure_injection_smoke(
    *,
    output_dir: str | Path,
    scenarios: list[str] | None = None,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    requested = scenarios or list(DEFAULT_PROVIDER_FAILURE_INJECTION_SCENARIOS)
    records = [_run_scenario(output_path, scenario) for scenario in requested]
    report = {
        "schema_version": PRE_VERL_PROVIDER_FAILURE_INJECTION_REPORT_VERSION,
        "status": "passed" if all(record["status"] == "passed" for record in records) else "failed",
        "scenario_count": len(records),
        "passed_count": sum(1 for record in records if record["status"] == "passed"),
        "failed_count": sum(1 for record in records if record["status"] != "passed"),
        "records": records,
    }
    report_path = output_path / "pre_verl_provider_failure_injection_smoke_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        failed = [record["scenario"] for record in records if record["status"] != "passed"]
        raise ConfigError(f"provider failure injection smoke failed: {failed}; report={report_path}")
    return report_path


def _run_scenario(output_dir: Path, scenario: str) -> dict[str, Any]:
    scenario_dir = output_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)
    try:
        if scenario == "malformed_tool_call":
            return _run_malformed_tool_call_repair_scenario(scenario_dir, scenario)
        return _run_provider_scenario(scenario_dir, scenario)
    except Exception as exc:  # noqa: BLE001 - smoke must report structured failure.
        return {
            "scenario": scenario,
            "status": "failed",
            "failure_reason": type(exc).__name__,
            "message": str(exc),
            "run_dir": scenario_dir.as_posix(),
            "excluded_from_trainable_accepted_sample": True,
        }


def _run_provider_scenario(scenario_dir: Path, scenario: str) -> dict[str, Any]:
    client = _DeepSeekFailureInjectionClient(
        model_id="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        credential=ProviderCredential(value="sk-test-redacted", source="failure_injection"),
        outcomes=_provider_outcomes_for_scenario(scenario),
    )
    request = _request(retry_policy="provider_retry_no_sleep_v0")
    with RunRecorder(scenario, scenario_dir, task_id="pre_verl_failure_injection") as recorder:
        response = client.generate(request=request, recorder=recorder)
    record = {
        "scenario": scenario,
        "run_dir": scenario_dir.as_posix(),
        "status": "passed",
        "terminal_reason": response.model_error_type or "ok",
        "model_error_type": response.model_error_type,
        "attempt_count": response.attempt_count,
        "retry_count": response.retry_count,
        "terminal_error_type": response.terminal_error_type,
        "attempt_artifact_refs": [ref.model_dump(mode="json") for ref in response.provider_attempt_refs],
        "retry_policy_ref": response.retry_policy_ref.model_dump(mode="json") if response.retry_policy_ref else None,
        "raw_provider_request_ref": (
            response.raw_provider_request_ref.model_dump(mode="json")
            if response.raw_provider_request_ref
            else None
        ),
        "raw_provider_response_ref": (
            response.raw_provider_response_ref.model_dump(mode="json")
            if response.raw_provider_response_ref
            else None
        ),
        "redaction_report_present": _raw_response_has_redaction_report(scenario_dir, response.raw_provider_response_ref),
        "model_visible_repair_message_present": False,
        "excluded_from_trainable_accepted_sample": True,
    }
    _assert_provider_scenario(record, scenario)
    return record


def _run_malformed_tool_call_repair_scenario(scenario_dir: Path, scenario: str) -> dict[str, Any]:
    client = _MalformedRepairSmokeClient()
    with RunRecorder(scenario, scenario_dir, task_id="pre_verl_failure_injection") as recorder:
        state = AgentLoop(
            model_client=client,
            tool_executor=ToolExecutor(),
            allowed_tool_names=["read_file"],
            test_feedback_policy="disabled",
        ).run(
            run_id=scenario,
            task_id="pre_verl_failure_injection",
            initial_messages=[{"role": "system", "content": "system"}],
            tool_context=None,  # type: ignore[arg-type]
            recorder=recorder,
            max_turns=3,
            budget_manager=BudgetManager(
                max_turns=3,
                max_tool_calls=4,
                max_test_runs=0,
                task_timeout_sec=60,
                command_timeout_sec=30,
                verifier_timeout_sec=60,
                max_tool_output_chars=4096,
                max_context_tokens=16000,
                max_output_tokens=1024,
            ),
        )
    events = _read_jsonl(scenario_dir / "events.jsonl")
    completed = [event for event in events if event.get("event_type") == "model_call_completed"]
    first = completed[0]["data"] if completed else {}
    repair_present = any(event.get("event_type") == "tool_call_repair_requested" for event in events)
    record = {
        "scenario": scenario,
        "run_dir": scenario_dir.as_posix(),
        "status": "passed" if state.agent_stop_reason == "final_answer" and repair_present else "failed",
        "terminal_reason": state.agent_stop_reason,
        "model_error_type": state.last_model_error,
        "attempt_count": first.get("attempt_count"),
        "retry_count": first.get("retry_count"),
        "terminal_error_type": first.get("terminal_error_type"),
        "attempt_artifact_refs": first.get("provider_attempt_refs") or [],
        "retry_policy_ref": first.get("retry_policy_ref"),
        "raw_provider_request_ref": first.get("raw_provider_request_ref"),
        "raw_provider_response_ref": first.get("raw_provider_response_ref"),
        "redaction_report_present": True,
        "model_visible_repair_message_present": repair_present,
        "excluded_from_trainable_accepted_sample": True,
    }
    if record["status"] != "passed":
        raise ConfigError("malformed tool call repair smoke did not reach final_answer after one repair")
    return record


def _provider_outcomes_for_scenario(scenario: str) -> list[Any]:
    if scenario == "retryable_429":
        return [
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="rate_limited",
                    message="rate limit",
                    status_code=429,
                    retryable=True,
                )
            ),
            _ok_payload(),
        ]
    if scenario == "timeout":
        return [
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_timeout",
                    message="timed out",
                    retryable=True,
                )
            )
            for _ in range(3)
        ]
    if scenario == "provider_error_500":
        return [
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="provider_error",
                    message="HTTP 500",
                    status_code=500,
                    retryable=True,
                )
            )
            for _ in range(3)
        ]
    if scenario == "auth_error":
        return [
            ProviderRequestError(
                ProviderErrorInfo(
                    model_error_type="auth_error",
                    message="invalid api key",
                    status_code=401,
                    retryable=False,
                )
            )
        ]
    if scenario == "length":
        return [
            {
                "id": "length",
                "choices": [{"finish_reason": "length", "message": {"role": "assistant", "content": "partial"}}],
            }
        ]
    if scenario == "missing_function_name":
        return [_tool_call_payload({"arguments": "{}"})]
    if scenario == "arguments_not_object":
        return [_tool_call_payload({"name": "read_file", "arguments": "[]"})]
    if scenario == "invalid_response":
        return [{"id": "invalid", "choices": []}]
    raise ConfigError(f"unknown provider failure injection scenario: {scenario}")


def _assert_provider_scenario(record: dict[str, Any], scenario: str) -> None:
    if not record["raw_provider_request_ref"] or not record["raw_provider_response_ref"]:
        raise ConfigError(f"{scenario}: raw provider refs missing")
    if not record["attempt_artifact_refs"]:
        raise ConfigError(f"{scenario}: attempt artifacts missing")
    if scenario == "retryable_429" and (record["retry_count"] != 1 or record["terminal_reason"] != "ok"):
        raise ConfigError("retryable_429 did not retry once and recover")
    if scenario in {"timeout", "provider_error_500"} and record["attempt_count"] != 3:
        raise ConfigError(f"{scenario}: expected three attempts")
    if scenario == "auth_error" and record["retry_count"] != 0:
        raise ConfigError("auth_error must not retry")
    if scenario == "length" and record["model_error_type"] != "output_token_limit_reached":
        raise ConfigError("length must map to output_token_limit_reached")
    if scenario in {"missing_function_name", "arguments_not_object"} and record["model_error_type"] != "tool_call_parse_failure":
        raise ConfigError(f"{scenario}: expected tool_call_parse_failure")
    if scenario == "invalid_response" and record["model_error_type"] != "invalid_response":
        raise ConfigError("invalid_response scenario did not map to invalid_response")


class _DeepSeekFailureInjectionClient(DeepSeekProviderClient):
    def __init__(self, *, outcomes: list[Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.outcomes = list(outcomes)

    def _post_json(self, body: dict[str, Any], request: ModelRequestContext) -> tuple[dict[str, Any], str | None]:
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, ProviderRequestError):
            raise outcome
        return outcome, str(outcome.get("id") or "failure-injection")


class _MalformedRepairSmokeClient:
    def __init__(self) -> None:
        self.call_count = 0

    def generate(self, *, request: ModelRequestContext, recorder: RunRecorder) -> ModelResponse:
        self.call_count += 1
        raw_request_ref = recorder.write_json_artifact(
            "raw_failure_injection_provider_request",
            {
                "body": {"messages": request.prepared_messages},
                "redaction_report": {"finding_count": 0},
                "prepared_messages_ref": request.prepared_messages_ref.model_dump(mode="json"),
                "tool_schema_snapshot_ref": request.tool_schema_snapshot_ref.model_dump(mode="json"),
            },
            {"redaction_status": "redacted", "budget_policy": "preserve_json"},
        )
        raw_response_ref = recorder.write_json_artifact(
            "raw_failure_injection_provider_response",
            {
                "status": "ok" if self.call_count > 1 else "error",
                "redaction_report": {"finding_count": 0},
            },
            {"redaction_status": "redacted", "budget_policy": "preserve_json"},
        )
        retry_policy_ref = recorder.write_json_artifact(
            "provider_retry_policy",
            {"policy_id": "provider_retry_no_sleep_v0", "max_attempts": 3},
        )
        attempt_ref = recorder.write_json_artifact(
            "provider_attempt",
            {
                "attempt_index": 1,
                "retryable": False,
                "error_type": "tool_call_parse_failure" if self.call_count == 1 else None,
                "request_ref": raw_request_ref.model_dump(mode="json"),
                "response_ref": raw_response_ref.model_dump(mode="json"),
            },
        )
        event = ModelCallEvent(
            model_call_id=request.model_call_id,
            provider="deepseek",
            model_id=request.provider_options.model_id,
            context_revision=request.context_revision,
            prepared_messages_ref=request.prepared_messages_ref,
            model_input_hash=request.model_input_hash,
            provider_message_format=request.provider_message_format,
            tool_schema_hash=stable_hash(request.allowed_tool_definitions),
            attempt_count=1,
            retry_count=0,
            retry_policy_ref=retry_policy_ref,
            model_error_type="tool_call_parse_failure" if self.call_count == 1 else None,
            terminal_error_type="tool_call_parse_failure" if self.call_count == 1 else None,
        )
        if self.call_count == 1:
            return ModelResponse(
                assistant_message=ModelMessage(
                    role="assistant",
                    content="malformed tool call",
                    metadata={"provider_error_message": "provider tool call arguments were not valid JSON"},
                ),
                raw_provider_request_ref=raw_request_ref,
                raw_provider_response_ref=raw_response_ref,
                provider_attempt_refs=[attempt_ref],
                retry_policy_ref=retry_policy_ref,
                attempt_count=1,
                retry_count=0,
                terminal_error_type="tool_call_parse_failure",
                finish_reason="error",
                model_error_type="tool_call_parse_failure",
                model_call_event=event,
            )
        return ModelResponse(
            assistant_message=ModelMessage(role="assistant", content="done"),
            raw_provider_request_ref=raw_request_ref,
            raw_provider_response_ref=raw_response_ref,
            provider_attempt_refs=[attempt_ref],
            retry_policy_ref=retry_policy_ref,
            attempt_count=1,
            retry_count=0,
            finish_reason="stop",
            model_call_event=event,
        )


def _request(*, retry_policy: str) -> ModelRequestContext:
    return ModelRequestContext(
        run_id="failure-injection",
        task_id="pre_verl_failure_injection",
        turn=1,
        model_call_id="failure_injection_model_call_0001",
        prepared_messages=[{"role": "system", "content": "system"}, {"role": "user", "content": "task"}],
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
                "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}},
            }
        ],
        tool_choice="auto",
        tool_schema_snapshot_ref=_artifact_ref("tool_schema"),
        provider_options=ModelProviderOptions(
            provider="deepseek",
            model_id="deepseek-v4-pro",
            provider_specific_options={"thinking": {"type": "disabled"}},
        ),
        scaffold_id="patch_focused_react",
        scaffold_phase="act",
        run_config_facts_ref=RunConfigFactsRef(sha256="b" * 64),
        budget_state={"turn_count": 1},
        request_timeout_seconds=10,
        raw_request_logging_policy="redact_secrets",
        credential_policy=ProviderCredentialPolicy(
            credential_source="env_only",
            required_env_vars=["DEEPSEEK_API_KEY"],
        ),
        retry_policy=retry_policy,
    )


def _artifact_ref(kind: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=kind,
        relative_path=f"artifacts/{kind}.json",
        kind=kind,
        sha256="0" * 64,
        size_bytes=0,
    )


def _ok_payload() -> dict[str, Any]:
    return {
        "id": "ok",
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "done"}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 1},
    }


def _tool_call_payload(function: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "tool-call",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": function,
                        }
                    ],
                },
            }
        ],
    }


def _raw_response_has_redaction_report(run_dir: Path, ref: ArtifactRef | None) -> bool:
    if ref is None:
        return False
    payload = json.loads((run_dir / ref.relative_path).read_text(encoding="utf-8"))
    return isinstance(payload.get("redaction_report"), dict)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
