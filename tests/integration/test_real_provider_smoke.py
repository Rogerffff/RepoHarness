import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError, RepoHarnessError
from repo_harness.model_client.real_smoke import (
    _run_config_payload,
    inspect_real_provider_smoke,
    run_real_provider_smoke,
)


def test_real_provider_smoke_writes_structured_skip_without_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE", "1")
    report = tmp_path / "real_provider_smoke_report.json"

    run_real_provider_smoke(output_dir=tmp_path, report_path=report, allow_openai_fallback=True)

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "skipped_no_credentials"
    assert payload["requested_provider"] == "deepseek"
    assert payload["actual_provider"] == "none"
    assert payload["credential_status"] == "missing_all"
    assert payload["fallback_used"] is False
    assert payload["official_docs_checked"] is True
    assert "api-docs.deepseek.com" in payload["official_docs_url"]
    output = inspect_real_provider_smoke(
        report=report,
        allow_skip_without_credentials=True,
        require_accepted_with_credentials=True,
    )
    assert "Inspect real provider smoke: passed" in output


def test_real_provider_smoke_does_not_use_local_secret_file_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("REPO_HARNESS_DISABLE_LOCAL_SECRET_FILE", raising=False)
    (tmp_path / "reference").mkdir()
    (tmp_path / "reference" / "deepseek_api.md").write_text(
        "local key: sk-local-secret-value-1234567890",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    report = tmp_path / "real_provider_smoke_report.json"

    run_real_provider_smoke(output_dir=tmp_path / "runs", report_path=report)

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "skipped_no_credentials"
    assert payload["credential_status"] == "missing_all"
    assert payload["credential_source"] == "none"


def test_real_provider_run_config_policy_matches_local_secret_source(tmp_path: Path):
    payload = _run_config_payload(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        output_dir=tmp_path,
        provider_specific_options={
            "credential_source": "local_secret_file_redacted",
        },
    )

    assert payload["model"]["credential_policy"] == "local_secret_file_redacted"


def test_real_provider_run_config_policy_keeps_environment_source_as_env_only(tmp_path: Path):
    payload = _run_config_payload(
        provider="deepseek",
        model_id="deepseek-v4-pro",
        output_dir=tmp_path,
        provider_specific_options={
            "credential_source": "environment",
        },
    )

    assert payload["model"]["credential_policy"] == "env_only"


def test_inspect_real_provider_smoke_accepts_deepseek_accepted_schema(tmp_path: Path):
    report = tmp_path / "accepted_real_provider_smoke_report.json"
    report.write_text(
        json.dumps(_base_report("accepted_with_credentials", "deepseek")),
        encoding="utf-8",
    )

    output = inspect_real_provider_smoke(
        report=report,
        allow_skip_without_credentials=True,
        require_accepted_with_credentials=True,
    )

    assert "Inspect real provider smoke: passed" in output


def test_inspect_real_provider_smoke_accepts_openai_fallback_success_schema(tmp_path: Path):
    report = tmp_path / "fallback_real_provider_smoke_report.json"
    payload = _base_report("fallback_success", "openai")
    payload.update(
        {
            "requested_provider": "deepseek",
            "fallback_used": True,
            "fallback_reason": "deepseek_primary_provider_error",
            "fallback_policy_version": "repo_harness_real_provider_fallback_v0",
            "provider_base_url": None,
            "provider_endpoint_category": "openai_chat_completions_sdk",
            "provider_endpoint_url": "https://api.openai.com/v1",
        }
    )
    report.write_text(json.dumps(payload), encoding="utf-8")

    output = inspect_real_provider_smoke(
        report=report,
        allow_skip_without_credentials=True,
        require_accepted_with_credentials=True,
    )

    assert "Inspect real provider smoke: passed" in output


def test_inspect_real_provider_smoke_rejects_fallback_without_policy_version(tmp_path: Path):
    report = tmp_path / "bad_fallback_real_provider_smoke_report.json"
    payload = _base_report("fallback_success", "openai")
    payload.update(
        {
            "requested_provider": "deepseek",
            "fallback_used": True,
            "fallback_reason": "deepseek_primary_provider_error",
            "fallback_policy_version": None,
            "provider_endpoint_category": "openai_chat_completions_sdk",
            "provider_endpoint_url": "https://api.openai.com/v1",
        }
    )
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigError, match="fallback_policy_version"):
        inspect_real_provider_smoke(
            report=report,
            allow_skip_without_credentials=True,
            require_accepted_with_credentials=True,
        )


def test_inspect_real_provider_smoke_accepts_provider_error_schema(tmp_path: Path):
    report = tmp_path / "provider_error_real_provider_smoke_report.json"
    payload = _base_report("provider_error", "deepseek")
    payload.update(
        {
            "model_error_type": "rate_limited",
            "final_verifier_status": None,
            "run_outcome": None,
        }
    )
    report.write_text(json.dumps(payload), encoding="utf-8")

    output = inspect_real_provider_smoke(report=report, allow_skip_without_credentials=True)

    assert "Inspect real provider smoke: passed" in output


def test_real_provider_smoke_redacts_exception_messages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    secret = "sk-testsecret123456789"
    monkeypatch.setenv("DEEPSEEK_API_KEY", secret)

    def fail_run_task(*args, **kwargs):  # noqa: ANN001, ARG001
        raise RepoHarnessError(f"Authorization: Bearer {secret}")

    monkeypatch.setattr("repo_harness.model_client.real_smoke.run_task", fail_run_task)
    report = tmp_path / "real_provider_smoke_report.json"

    run_real_provider_smoke(output_dir=tmp_path, report_path=report)

    text = report.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert payload["status"] == "provider_error"
    assert secret not in text
    assert "Bearer sk-" not in text
    assert "<REDACTED_CREDENTIAL>" in text


def test_inspect_real_provider_smoke_rejects_fallback_masquerading_as_primary(tmp_path: Path):
    report = tmp_path / "bad_real_provider_smoke_report.json"
    report.write_text(
        json.dumps(
            {
                "status": "accepted_with_credentials",
                "requested_provider": "deepseek",
                "actual_provider": "openai",
                "provider_model": "gpt-5-mini",
                "fallback_used": True,
                "fallback_reason": "deepseek_failed",
                "credential_status": "present",
                "credential_source": "environment",
                "model_error_type": None,
                "run_dir": "runs/example",
                "raw_request_artifact_ref": {},
                "raw_response_artifact_ref": {},
                "redaction_status": "redacted",
                "final_verifier_status": "accepted",
                "run_outcome": "success",
                "official_docs_checked": True,
                "official_docs_url": "https://api-docs.deepseek.com/zh-cn/",
                "checked_at_date": "2026-05-01",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="accepted_with_credentials cannot be used"):
        inspect_real_provider_smoke(
            report=report,
            allow_skip_without_credentials=True,
            require_accepted_with_credentials=True,
        )


def _base_report(status: str, actual_provider: str) -> dict:
    return {
        "schema_version": "repo_harness_real_provider_smoke_report_v0",
        "status": status,
        "requested_provider": actual_provider,
        "actual_provider": actual_provider,
        "provider_model": "deepseek-v4-pro" if actual_provider == "deepseek" else "gpt-5-mini",
        "provider_base_url": "https://api.deepseek.com" if actual_provider == "deepseek" else None,
        "provider_endpoint_category": (
            "deepseek_openai_compatible_chat_completions"
            if actual_provider == "deepseek"
            else "openai_chat_completions_sdk"
        ),
        "fallback_used": False,
        "fallback_reason": None,
        "fallback_policy_version": None,
        "credential_status": "present",
        "credential_source": "environment",
        "model_error_type": None,
        "run_dir": "runs/example",
        "raw_request_artifact_ref": {"kind": f"raw_{actual_provider}_provider_request"},
        "raw_response_artifact_ref": {"kind": f"raw_{actual_provider}_provider_response"},
        "redaction_status": "redacted",
        "redaction_checks": {
            "raw_artifacts_present": True,
            "all_raw_artifacts_redacted": True,
            "no_authorization_plaintext": True,
            "no_openai_style_key": True,
            "no_raw_request_body_field": True,
            "reasoning_fields_redacted": True,
        },
        "final_verifier_status": "accepted",
        "run_outcome": "success",
        "official_docs_checked": True,
        "official_docs_url": "https://api-docs.deepseek.com/zh-cn/",
        "checked_at_date": "2026-05-01",
    }
