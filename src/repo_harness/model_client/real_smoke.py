"""Real provider smoke report generation and inspection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.evaluation.runner import run_task
from repo_harness.model_client.providers.deepseek import (
    DEEPSEEK_DEFAULT_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    DEEPSEEK_OFFICIAL_DOCS_URL,
    deepseek_credential_status,
)
from repo_harness.model_client.redaction import sanitize_provider_error_message
from repo_harness.model_client.providers.openai import (
    OPENAI_BASE_URL,
    OPENAI_DEFAULT_MODEL,
    OPENAI_ENDPOINT_CATEGORY,
    OPENAI_OFFICIAL_DOCS_URL,
    openai_credential_status,
    openai_sdk_available,
)
from repo_harness.trajectory import verify_artifact_manifest

REAL_PROVIDER_SMOKE_SCHEMA_VERSION = "repo_harness_real_provider_smoke_report_v0"
REAL_PROVIDER_FALLBACK_POLICY_VERSION = "repo_harness_real_provider_fallback_v0"
DEEPSEEK_DOCS_CHECKED_AT_DATE = "2026-05-01"
OPENAI_DOCS_CHECKED_AT_DATE = "2026-05-01"
REAL_PROVIDER_TASK = "tests/fixtures/tasks/task_001.yaml"


def run_real_provider_smoke(
    *,
    output_dir: str | Path,
    report_path: str | Path | None = None,
    requested_provider: str = "deepseek",
    allow_openai_fallback: bool = False,
    allow_local_secret_file: bool = False,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_file = Path(report_path) if report_path else output_path / "real_provider_smoke_report.json"
    if requested_provider != "deepseek":
        raise ConfigError("Stage 11 real provider smoke 只支持 requested_provider=deepseek。")

    deepseek_status = deepseek_credential_status(allow_local_secret_file=allow_local_secret_file)
    if deepseek_status["credential_status"] == "missing":
        if allow_openai_fallback:
            fallback_report = _maybe_run_openai_fallback(
                output_path=output_path,
                fallback_reason="deepseek_no_credentials",
            )
            if fallback_report is not None:
                _write_report(report_file, fallback_report)
                return report_file
        report = _skip_report(
            requested_provider="deepseek",
            credential_status="missing_all",
            credential_source="none",
            skip_reason="missing DEEPSEEK_API_KEY and no local DeepSeek secret configured",
        )
        _write_report(report_file, report)
        return report_file

    primary_report = _run_provider_task(
        output_path=output_path,
        provider="deepseek",
        model_id=DEEPSEEK_DEFAULT_MODEL,
        provider_specific_options={
            "base_url": DEEPSEEK_DEFAULT_BASE_URL,
            "endpoint_category": "deepseek_openai_compatible_chat_completions",
            "requested_provider": "deepseek",
            "actual_provider": "deepseek",
            "credential_source": deepseek_status["credential_source"],
            "allow_local_secret_file": allow_local_secret_file,
            "thinking": {"type": "disabled"},
        },
        credential_source=deepseek_status["credential_source"],
        run_id="deepseek-primary-task-001",
        requested_provider="deepseek",
        fallback_used=False,
        fallback_reason=None,
    )
    if primary_report["status"] == "accepted_with_credentials":
        _write_report(report_file, primary_report)
        return report_file
    if allow_openai_fallback:
        fallback_report = _maybe_run_openai_fallback(
            output_path=output_path,
            fallback_reason=f"deepseek_primary_{primary_report['status']}",
            primary_report=primary_report,
        )
        if fallback_report is not None:
            _write_report(report_file, fallback_report)
            return report_file
    _write_report(report_file, primary_report)
    return report_file


def inspect_real_provider_smoke(
    *,
    report: str | Path,
    allow_skip_without_credentials: bool = False,
    require_accepted_with_credentials: bool = False,
) -> str:
    report_path = Path(report)
    payload = _read_json(report_path)
    failures = _validate_report(payload)
    status = payload.get("status")
    credential_status = payload.get("credential_status")
    if status == "skipped_no_credentials":
        if not allow_skip_without_credentials:
            failures.append("real provider smoke skipped without credentials but skip is not allowed")
        if credential_status not in {"missing", "missing_all"}:
            failures.append("skipped_no_credentials must use missing credential status")
    if require_accepted_with_credentials and credential_status not in {"missing", "missing_all"}:
        if status not in {"accepted_with_credentials", "fallback_success"}:
            failures.append("credentials were present, so real provider smoke must be accepted or fallback_success")
    if status == "accepted_with_credentials" and payload.get("actual_provider") != payload.get("requested_provider"):
        failures.append("accepted_with_credentials cannot be used for a fallback provider")
    if status == "fallback_success":
        if payload.get("requested_provider") != "deepseek" or payload.get("actual_provider") != "openai":
            failures.append("fallback_success must record requested_provider=deepseek and actual_provider=openai")
        if not payload.get("fallback_used") or not payload.get("fallback_reason"):
            failures.append("fallback_success must record fallback_used and fallback_reason")
    if payload.get("redaction_status") not in {"redacted", "not_applicable"}:
        failures.append("redaction_status must be redacted or not_applicable")
    if failures:
        raise ConfigError("; ".join(failures))
    lines = [
        f"Real provider smoke report: {report_path}",
        f"Status: {status}",
        f"Requested provider: {payload.get('requested_provider')}",
        f"Actual provider: {payload.get('actual_provider')}",
        f"Credential status: {credential_status}",
        f"Fallback used: {payload.get('fallback_used')}",
        f"Final verifier status: {payload.get('final_verifier_status')}",
        f"Run outcome: {payload.get('run_outcome')}",
        f"Model error type: {payload.get('model_error_type')}",
        "Inspect real provider smoke: passed",
    ]
    return "\n".join(lines)


def _maybe_run_openai_fallback(
    *,
    output_path: Path,
    fallback_reason: str,
    primary_report: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    status = openai_credential_status()
    if status["credential_status"] == "missing":
        if primary_report is not None:
            failed = dict(primary_report)
            failed["fallback_used"] = False
            failed["fallback_reason"] = "openai_fallback_missing_credentials"
            return failed
        return None
    if not openai_sdk_available():
        if primary_report is not None:
            failed = dict(primary_report)
            failed["fallback_used"] = False
            failed["fallback_reason"] = "openai_fallback_sdk_missing"
            failed["provider_failed_runs"] = [
                *failed.get("provider_failed_runs", []),
                {
                    "provider": "openai",
                    "model_error_type": "provider_error",
                    "reason": "official openai Python SDK is not installed",
                },
            ]
            return failed
        return None
    return _run_provider_task(
        output_path=output_path,
        provider="openai",
        model_id=OPENAI_DEFAULT_MODEL,
        provider_specific_options={
            "endpoint_category": OPENAI_ENDPOINT_CATEGORY,
            "requested_provider": "deepseek",
            "actual_provider": "openai",
            "fallback_reason": fallback_reason,
            "fallback_policy_version": REAL_PROVIDER_FALLBACK_POLICY_VERSION,
            "credential_source": status["credential_source"],
        },
        credential_source=status["credential_source"],
        run_id="openai-fallback-task-001",
        requested_provider="deepseek",
        fallback_used=True,
        fallback_reason=fallback_reason,
        primary_report=primary_report,
    )


def _run_provider_task(
    *,
    output_path: Path,
    provider: str,
    model_id: str,
    provider_specific_options: dict[str, Any],
    credential_source: str,
    run_id: str,
    requested_provider: str,
    fallback_used: bool,
    fallback_reason: str | None,
    primary_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config_path = output_path / f"{run_id}.config.yaml"
    config_payload = _run_config_payload(
        provider=provider,
        model_id=model_id,
        output_dir=output_path,
        provider_specific_options=provider_specific_options,
    )
    config_path.write_text(yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8")
    try:
        run_dir = run_task(
            REAL_PROVIDER_TASK,
            config_path=config_path,
            output_dir=output_path,
            run_id=run_id,
        )
    except RepoHarnessError as exc:
        return _failed_report_from_exception(
            provider=provider,
            requested_provider=requested_provider,
            model_id=model_id,
            credential_source=credential_source,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            exc=exc,
            primary_report=primary_report,
        )
    return _report_from_run(
        run_dir=run_dir,
        provider=provider,
        requested_provider=requested_provider,
        model_id=model_id,
        credential_source=credential_source,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        primary_report=primary_report,
    )


def _report_from_run(
    *,
    run_dir: Path,
    provider: str,
    requested_provider: str,
    model_id: str,
    credential_source: str,
    fallback_used: bool,
    fallback_reason: str | None,
    primary_report: dict[str, Any] | None,
) -> dict[str, Any]:
    metrics = _read_json(run_dir / "metrics.json")
    events = _read_jsonl(run_dir / "events.jsonl")
    raw_request_refs, raw_response_refs, redaction_status, redaction_checks = _raw_artifact_facts(run_dir, provider)
    model_error_type = _first_model_error_type(events)
    final_verifier_status = metrics.get("final_verifier_status")
    run_outcome = metrics.get("run_outcome")
    accepted = final_verifier_status == "accepted" and run_outcome == "success"
    status = "fallback_success" if accepted and fallback_used else (
        "accepted_with_credentials" if accepted else (
            "provider_error" if model_error_type else "failed_with_credentials"
        )
    )
    failures = verify_artifact_manifest(run_dir)
    return {
        **_base_report(
            status=status,
            requested_provider=requested_provider,
            actual_provider=provider,
            provider_model=model_id,
            credential_status="present",
            credential_source=credential_source,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        ),
        "model_error_type": model_error_type,
        "run_dir": str(run_dir),
        "raw_request_artifact_ref": raw_request_refs[0] if raw_request_refs else None,
        "raw_response_artifact_ref": raw_response_refs[0] if raw_response_refs else None,
        "raw_request_artifact_refs": raw_request_refs,
        "raw_response_artifact_refs": raw_response_refs,
        "redaction_status": redaction_status,
        "redaction_checks": redaction_checks,
        "final_verifier_status": final_verifier_status,
        "run_outcome": run_outcome,
        "provider_failed_runs": _provider_failed_runs(primary_report),
        "failures": failures,
    }


def _failed_report_from_exception(
    *,
    provider: str,
    requested_provider: str,
    model_id: str,
    credential_source: str,
    fallback_used: bool,
    fallback_reason: str | None,
    exc: Exception,
    primary_report: dict[str, Any] | None,
) -> dict[str, Any]:
    safe_reason = sanitize_provider_error_message(str(exc))[:1000]
    return {
        **_base_report(
            status="provider_error",
            requested_provider=requested_provider,
            actual_provider=provider,
            provider_model=model_id,
            credential_status="present",
            credential_source=credential_source,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        ),
        "model_error_type": "provider_error",
        "run_dir": None,
        "raw_request_artifact_ref": None,
        "raw_response_artifact_ref": None,
        "raw_request_artifact_refs": [],
        "raw_response_artifact_refs": [],
        "redaction_status": "not_applicable",
        "redaction_checks": {},
        "final_verifier_status": None,
        "run_outcome": None,
        "provider_failed_runs": [
            *_provider_failed_runs(primary_report),
            {
                "provider": provider,
                "model_error_type": "provider_error",
                "reason": safe_reason,
            },
        ],
        "failures": [safe_reason],
    }


def _skip_report(
    *,
    requested_provider: str,
    credential_status: str,
    credential_source: str,
    skip_reason: str,
) -> dict[str, Any]:
    return {
        **_base_report(
            status="skipped_no_credentials",
            requested_provider=requested_provider,
            actual_provider="none",
            provider_model=DEEPSEEK_DEFAULT_MODEL,
            credential_status=credential_status,
            credential_source=credential_source,
            fallback_used=False,
            fallback_reason=None,
        ),
        "skip_reason": skip_reason,
        "model_error_type": None,
        "run_dir": None,
        "raw_request_artifact_ref": None,
        "raw_response_artifact_ref": None,
        "raw_request_artifact_refs": [],
        "raw_response_artifact_refs": [],
        "redaction_status": "not_applicable",
        "redaction_checks": {},
        "final_verifier_status": None,
        "run_outcome": None,
        "provider_failed_runs": [],
        "failures": [],
    }


def _base_report(
    *,
    status: str,
    requested_provider: str,
    actual_provider: str,
    provider_model: str,
    credential_status: str,
    credential_source: str,
    fallback_used: bool,
    fallback_reason: str | None,
) -> dict[str, Any]:
    docs_urls = [DEEPSEEK_OFFICIAL_DOCS_URL]
    if actual_provider == "openai" or fallback_used:
        docs_urls.append(OPENAI_OFFICIAL_DOCS_URL)
    return {
        "schema_version": REAL_PROVIDER_SMOKE_SCHEMA_VERSION,
        "status": status,
        "requested_provider": requested_provider,
        "actual_provider": actual_provider,
        "provider_model": provider_model,
        "provider_base_url": DEEPSEEK_DEFAULT_BASE_URL if actual_provider == "deepseek" else None,
        "provider_endpoint_url": (
            f"{DEEPSEEK_DEFAULT_BASE_URL}/chat/completions"
            if actual_provider == "deepseek"
            else (OPENAI_BASE_URL if actual_provider == "openai" else None)
        ),
        "provider_endpoint_category": (
            "deepseek_openai_compatible_chat_completions"
            if actual_provider == "deepseek"
            else (OPENAI_ENDPOINT_CATEGORY if actual_provider == "openai" else None)
        ),
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
        "fallback_policy_version": REAL_PROVIDER_FALLBACK_POLICY_VERSION if fallback_used else None,
        "credential_status": credential_status,
        "credential_source": credential_source,
        "official_docs_checked": True,
        "official_docs_url": docs_urls[0],
        "official_docs_urls": docs_urls,
        "checked_at_date": DEEPSEEK_DOCS_CHECKED_AT_DATE,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _run_config_payload(
    *,
    provider: str,
    model_id: str,
    output_dir: Path,
    provider_specific_options: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id_prefix": "v2_real_provider_smoke",
        "model": {
            "provider": provider,
            "model_id": model_id,
            "temperature": 0.0,
            "max_output_tokens": 2048,
            "retry_policy": "none",
            "credential_policy": "env_only",
            "provider_request_logging": "redact_secrets",
            "provider_specific_options": provider_specific_options,
        },
        "runtime": {
            "scaffold_id": "simple_react",
            "permission_mode": "auto",
            "test_feedback_policy": "public_only",
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 10,
            "max_tool_calls": 20,
            "max_test_runs": 2,
            "task_timeout_sec": 300,
            "seed": 42,
        },
        "workspace": {
            "output_dir": str(output_dir),
            "keep_workspace": True,
            "default_command_timeout_sec": 60,
        },
        "evaluation": {
            "final_verifier_mode": "strict_patch_replay",
        },
    }


def _raw_artifact_facts(run_dir: Path, provider: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, dict[str, bool]]:
    artifacts = _read_json(run_dir / "artifacts.json").get("artifacts", [])
    request_kind = f"raw_{provider}_provider_request"
    response_kind = f"raw_{provider}_provider_response"
    raw_requests = [artifact for artifact in artifacts if artifact.get("kind") == request_kind]
    raw_responses = [artifact for artifact in artifacts if artifact.get("kind") == response_kind]
    raw_artifacts = [*raw_requests, *raw_responses]
    status = "redacted" if raw_artifacts and all(
        artifact.get("redaction_status") == "redacted"
        for artifact in raw_artifacts
    ) else "failed"
    texts = [
        (run_dir / artifact["relative_path"]).read_text(encoding="utf-8")
        for artifact in raw_artifacts
    ]
    lowered = "\n".join(texts).lower()
    checks = {
        "raw_artifacts_present": bool(raw_artifacts),
        "all_raw_artifacts_redacted": status == "redacted",
        "no_authorization_plaintext": "authorization: bearer" not in lowered and "bearer sk-" not in lowered,
        "no_openai_style_key": "sk-" not in lowered,
        "no_raw_request_body_field": "raw_request_body" not in lowered,
        "reasoning_fields_redacted": (
            ("reasoning_content" not in lowered and "reasoning_summary" not in lowered)
            or "<redacted_reasoning>" in lowered
        ),
    }
    if not all(checks.values()):
        status = "failed"
    return raw_requests, raw_responses, status, checks


def _first_model_error_type(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        if event.get("event_type") != "model_call_completed":
            continue
        model_error_type = event.get("data", {}).get("model_error_type")
        if model_error_type:
            return str(model_error_type)
    return None


def _provider_failed_runs(primary_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not primary_report:
        return []
    if primary_report.get("status") in {"accepted_with_credentials", "fallback_success"}:
        return []
    return [
        {
            "provider": primary_report.get("actual_provider"),
            "model_error_type": primary_report.get("model_error_type"),
            "status": primary_report.get("status"),
            "run_dir": primary_report.get("run_dir"),
        }
    ]


def _validate_report(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    required = [
        "status",
        "requested_provider",
        "actual_provider",
        "provider_model",
        "provider_endpoint_category",
        "credential_source",
        "fallback_used",
        "fallback_policy_version",
        "credential_status",
        "model_error_type",
        "run_dir",
        "raw_request_artifact_ref",
        "raw_response_artifact_ref",
        "redaction_status",
        "final_verifier_status",
        "run_outcome",
        "official_docs_checked",
        "official_docs_url",
        "checked_at_date",
    ]
    for key in required:
        if key not in payload:
            failures.append(f"missing required field: {key}")
    if payload.get("official_docs_checked") is not True:
        failures.append("official_docs_checked must be true")
    actual_provider = payload.get("actual_provider")
    if actual_provider == "deepseek" and payload.get("provider_base_url") != DEEPSEEK_DEFAULT_BASE_URL:
        failures.append("DeepSeek report must record provider_base_url=https://api.deepseek.com")
    if actual_provider == "openai" and payload.get("provider_endpoint_category") != OPENAI_ENDPOINT_CATEGORY:
        failures.append("OpenAI fallback report must record provider_endpoint_category")
    if payload.get("status") == "fallback_success" and not payload.get("fallback_policy_version"):
        failures.append("fallback_success must record fallback_policy_version")
    checks = payload.get("redaction_checks") or {}
    if checks and not all(bool(value) for value in checks.values()):
        failures.append("one or more redaction checks failed")
    return failures


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
