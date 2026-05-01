"""Mock provider smoke report inspection."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.export import inspect_export
from repo_harness.trajectory import verify_artifact_manifest


def inspect_mock_provider_smoke(
    *,
    run_dir: str | Path,
    output: str | Path | None = None,
    assert_accepted: bool = False,
    assert_export_clean: bool = False,
) -> str:
    run_path = Path(run_dir)
    report = build_mock_provider_smoke_report(
        run_path,
        assert_export_clean=assert_export_clean,
    )
    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    failures = list(report["failures"])
    if assert_accepted and report["status"] != "accepted":
        failures.append(f"mock provider smoke was not accepted: {report['status']}")
    if assert_export_clean and report["export_audit_status"] != "clean":
        failures.append("export audit was not clean")
    lines = [
        f"Mock provider smoke run: {run_path}",
        f"Status: {report['status']}",
        f"Provider: {report['provider']}",
        f"Final verifier status: {report['final_verifier_status']}",
        f"Model error type: {report['model_error_type']}",
        f"Export audit status: {report['export_audit_status']}",
        f"Raw artifact redaction: {report['raw_artifact_redaction_status']}",
    ]
    if failures:
        raise ConfigError("; ".join(failures))
    lines.append("Inspect mock provider smoke: passed")
    return "\n".join(lines)


def build_mock_provider_smoke_report(
    run_dir: str | Path,
    *,
    assert_export_clean: bool = False,
) -> dict[str, Any]:
    input_path = Path(run_dir)
    run_path = _resolve_mock_run_path(input_path)
    metrics = _read_json(run_path / "metrics.json")
    run_config = _read_json(run_path / "run_config_facts.json")
    events = _read_jsonl(run_path / "events.jsonl")
    artifacts = _read_json(run_path / "artifacts.json").get("artifacts", [])
    model_error_type = _first_model_error_type(events)
    raw_artifacts = [
        artifact
        for artifact in artifacts
        if artifact.get("kind") in {"raw_mock_provider_request", "raw_mock_provider_response"}
    ]
    failures = verify_artifact_manifest(run_path)
    if run_config.get("provider") != "mock":
        failures.append("run_config_facts provider is not mock")
    if not raw_artifacts:
        failures.append("raw mock provider artifacts missing")
    redaction_status = _raw_redaction_status(run_path, raw_artifacts, failures)
    redaction_checks = _raw_redaction_checks(run_path, raw_artifacts)
    for check_name, passed in redaction_checks.items():
        if not passed:
            failures.append(f"raw artifact redaction check failed: {check_name}")
    export_status = _export_status(
        run_path,
        input_path=input_path,
        assert_export_clean=assert_export_clean,
    )
    if export_status.startswith("failed"):
        failures.append(export_status)
    final_verifier_status = metrics.get("final_verifier_status")
    run_outcome = metrics.get("run_outcome")
    status = "accepted" if final_verifier_status == "accepted" and run_outcome == "success" else "failed"
    return {
        "schema_version": "repo_harness_mock_provider_smoke_report_v0",
        "status": status,
        "provider": run_config.get("provider"),
        "run_dir": str(run_path),
        "final_verifier_status": final_verifier_status,
        "run_outcome": run_outcome,
        "model_error_type": model_error_type,
        "export_audit_status": "clean" if export_status == "clean" else export_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "raw_request_artifact_refs": [
            artifact for artifact in raw_artifacts if artifact.get("kind") == "raw_mock_provider_request"
        ],
        "raw_response_artifact_refs": [
            artifact for artifact in raw_artifacts if artifact.get("kind") == "raw_mock_provider_response"
        ],
        "raw_artifact_redaction_status": redaction_status,
        "raw_artifact_redaction_checks": redaction_checks,
        "failures": failures,
    }


def _raw_redaction_status(run_path: Path, raw_artifacts: list[dict[str, Any]], failures: list[str]) -> str:
    status_values = {str(artifact.get("redaction_status")) for artifact in raw_artifacts}
    for artifact in raw_artifacts:
        if artifact.get("redaction_status") != "redacted":
            failures.append(f"{artifact.get('artifact_id')}: raw artifact is not redacted")
        text = (run_path / artifact["relative_path"]).read_text(encoding="utf-8")
        lowered = text.lower()
        if "authorization: bearer" in lowered or "sk-" in lowered:
            failures.append(f"{artifact.get('artifact_id')}: credential-like text found")
        if "raw_request_body" in lowered or "reasoning_summary" in lowered:
            failures.append(f"{artifact.get('artifact_id')}: blocked provider raw field found")
    return "redacted" if status_values == {"redacted"} else "failed"


def _raw_redaction_checks(run_path: Path, raw_artifacts: list[dict[str, Any]]) -> dict[str, bool]:
    texts = [
        (run_path / artifact["relative_path"]).read_text(encoding="utf-8")
        for artifact in raw_artifacts
    ]
    combined = "\n".join(texts)
    lowered = combined.lower()
    return {
        "secret_like_fields_redacted": all(_secret_like_fields_redacted(text) for text in texts),
        "no_authorization_plaintext": "authorization: bearer" not in lowered
        and "bearer " not in lowered,
        "no_raw_request_body": "raw_request_body" not in lowered,
        "no_reasoning_summary": "reasoning_summary" not in lowered,
        "no_openai_style_key": "sk-" not in lowered,
    }


def _secret_like_fields_redacted(text: str) -> bool:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    return _secret_like_value_ok(payload)


def _secret_like_value_ok(value: Any, *, key: str = "") -> bool:
    if isinstance(value, dict):
        return all(_secret_like_value_ok(nested, key=str(nested_key)) for nested_key, nested in value.items())
    if isinstance(value, list):
        return all(_secret_like_value_ok(item, key=key) for item in value)
    if _secret_like_key(key):
        return value == "<REDACTED_CREDENTIAL>" or value is None or value == ""
    return True


def _secret_like_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if any(marker in lowered for marker in ("api_key", "apikey", "authorization", "password", "secret")):
        return True
    return lowered == "token" or lowered.endswith("_token")


def _export_status(run_path: Path, *, input_path: Path, assert_export_clean: bool) -> str:
    exports = _exports_path(run_path, input_path=input_path)
    if not exports.exists():
        return "not_generated"
    try:
        inspect_export(exports, all_exports=True, assert_clean=assert_export_clean)
    except Exception as exc:  # noqa: BLE001 - report captures failure text for smoke summary
        return f"failed:{type(exc).__name__}"
    return "clean"


def _resolve_mock_run_path(path: Path) -> Path:
    if (path / "metrics.json").exists() and (path / "run_config_facts.json").exists():
        return path
    candidates = [
        child
        for child in sorted(path.iterdir()) if child.is_dir()
        and (child / "metrics.json").exists()
        and (child / "run_config_facts.json").exists()
    ] if path.exists() and path.is_dir() else []
    mock_candidates = [
        child
        for child in candidates
        if _read_json(child / "run_config_facts.json").get("provider") == "mock"
    ]
    if len(mock_candidates) == 1:
        return mock_candidates[0]
    if len(candidates) == 1:
        return candidates[0]
    raise ConfigError(f"无法从路径定位唯一 mock provider run directory：{path}")


def _exports_path(run_path: Path, *, input_path: Path) -> Path:
    if (input_path / "exports").exists():
        return input_path / "exports"
    if (run_path / "exports").exists():
        return run_path / "exports"
    return run_path.parent / "exports"


def _first_model_error_type(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        if event.get("event_type") != "model_call_completed":
            continue
        model_error_type = event.get("data", {}).get("model_error_type")
        if model_error_type:
            return str(model_error_type)
    return None


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
