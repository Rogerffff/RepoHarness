import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.schema_versions import V5_TASK_SET_MANIFEST_VERSION
from repo_harness.v5_evidence import (
    inspect_v5_provider_cost_budget,
    inspect_v5_provider_gate,
)
from repo_harness.v5_provider_gate import (
    build_provider_cost_budget_report,
    build_provider_gate_report,
)


def test_v5_provider_gate_builder_redacts_env_credentials_and_inspects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek-secret-123456789")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-secret-123456789")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-api03-test-secret-123456789")
    task_set = _write_task_set(tmp_path)

    gate_path = build_provider_gate_report(
        task_set_manifest=task_set,
        output_dir=tmp_path / "provider_gate",
    )

    text = gate_path.read_text(encoding="utf-8")
    assert "sk-test-deepseek-secret" not in text
    assert "sk-test-openai-secret" not in text
    assert "sk-ant-api03-test-secret" not in text
    payload = _read_json(gate_path)
    assert payload["credential_status_by_provider"]["deepseek"] == "present"
    assert payload["credential_status_by_provider"]["openai"] == "present"
    assert payload["adapter_status_by_provider"]["openai"] == "fallback_only"
    assert payload["adapter_status_by_provider"]["anthropic_claude"] == "adapter_not_implemented"
    assert payload["fallback_success_counts_toward_primary_openai"] is False
    assert "Inspect V5 provider gate: complete" in inspect_v5_provider_gate(
        gate_path,
        assert_consistent=True,
    )

    cost_path = build_provider_cost_budget_report(
        provider_gate_report=gate_path,
        output=tmp_path / "provider_gate" / "v5_provider_cost_budget_report.json",
        max_real_provider_calls=24,
        max_cost_usd=5.0,
    )
    assert "Inspect V5 provider cost budget: complete" in inspect_v5_provider_cost_budget(
        cost_path,
        assert_consistent=True,
    )


def test_v5_provider_gate_records_missing_credential_and_adapter_skips(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    task_set = _write_task_set(tmp_path)

    gate_path = build_provider_gate_report(
        task_set_manifest=task_set,
        output_dir=tmp_path / "provider_gate",
    )

    payload = _read_json(gate_path)
    skip_types = {(item["provider_id"], item["skip_type"]) for item in payload["structured_skips"]}
    assert ("deepseek", "credential_missing_skip") in skip_types
    assert ("openai", "credential_missing_skip") in skip_types
    assert ("openai", "primary_provider_comparison_not_enabled_skip") in skip_types
    assert ("anthropic_claude", "adapter_not_implemented_skip") in skip_types
    assert payload["actual_real_provider_calls"] == 0
    assert inspect_v5_provider_gate(gate_path, assert_consistent=True)


def test_v5_provider_gate_refuses_task_set_before_strict_inventory_gate(tmp_path: Path) -> None:
    task_set = _write_task_set(
        tmp_path,
        strict_inventory_gate="blocked_pending_stage2b",
        accepted_count=10,
        pr_issue_count=6,
    )

    with pytest.raises(ConfigError, match="strict_inventory_gate=passed"):
        build_provider_gate_report(
            task_set_manifest=task_set,
            output_dir=tmp_path / "provider_gate",
        )


def test_v5_provider_gate_inspect_rejects_openai_primary_or_secret_marker(tmp_path: Path) -> None:
    gate_path = build_provider_gate_report(
        task_set_manifest=_write_task_set(tmp_path),
        output_dir=tmp_path / "provider_gate",
    )
    payload = _read_json(gate_path)
    payload["adapter_status_by_provider"]["openai"] = "primary_supported"
    bad_openai = tmp_path / "bad_openai_provider_gate.json"
    _write_json(bad_openai, payload)
    with pytest.raises(ConfigError, match="openai 当前只能是 fallback_only"):
        inspect_v5_provider_gate(bad_openai, assert_consistent=True)

    payload = _read_json(gate_path)
    payload["credential_source_by_provider"]["deepseek"] = "sk-test-raw-secret-123456789"
    bad_secret = tmp_path / "bad_secret_provider_gate.json"
    _write_json(bad_secret, payload)
    with pytest.raises(ConfigError, match="raw provider credential"):
        inspect_v5_provider_gate(bad_secret, assert_consistent=True)


def test_v5_provider_cost_budget_rejects_overrun(tmp_path: Path) -> None:
    gate_path = build_provider_gate_report(
        task_set_manifest=_write_task_set(tmp_path),
        output_dir=tmp_path / "provider_gate",
    )

    with pytest.raises(ConfigError, match="actual_real_provider_calls"):
        build_provider_cost_budget_report(
            provider_gate_report=gate_path,
            output=tmp_path / "provider_gate" / "v5_provider_cost_budget_report.json",
            max_real_provider_calls=1,
            max_cost_usd=5.0,
            actual_real_provider_calls=2,
        )


def test_v5_provider_cost_budget_refuses_existing_custom_output(tmp_path: Path) -> None:
    gate_path = build_provider_gate_report(
        task_set_manifest=_write_task_set(tmp_path),
        output_dir=tmp_path / "provider_gate",
    )
    output = tmp_path / "provider_gate" / "custom_cost_budget.json"
    output.write_text("{}", encoding="utf-8")

    with pytest.raises(ConfigError, match="已存在"):
        build_provider_cost_budget_report(
            provider_gate_report=gate_path,
            output=output,
        )


def test_v5_provider_gate_cli_exposes_builders_and_inspects(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "build-v5-provider-gate" in output
    assert "build-v5-provider-cost-budget" in output

    task_set = _write_task_set(tmp_path)
    gate_dir = tmp_path / "provider_gate"
    assert main(
        [
            "build-v5-provider-gate",
            "--task-set-manifest",
            str(task_set),
            "--output-dir",
            str(gate_dir),
        ]
    ) == 0
    gate_path = gate_dir / "v5_provider_credential_gate_report.json"
    assert main(["inspect-v5-provider-gate", str(gate_path), "--assert-consistent"]) == 0

    cost_path = gate_dir / "v5_provider_cost_budget_report.json"
    assert main(
        [
            "build-v5-provider-cost-budget",
            "--provider-gate-report",
            str(gate_path),
            "--output",
            str(cost_path),
        ]
    ) == 0
    assert main(["inspect-v5-provider-cost-budget", str(cost_path), "--assert-consistent"]) == 0


def _write_task_set(
    tmp_path: Path,
    *,
    strict_inventory_gate: str = "passed",
    accepted_count: int = 12,
    pr_issue_count: int = 8,
) -> Path:
    path = tmp_path / "v5_task_set_manifest.json"
    _write_json(
        path,
        {
            "schema_version": V5_TASK_SET_MANIFEST_VERSION,
            "task_set_stage": "stage2b_merged_12",
            "strict_inventory_gate": strict_inventory_gate,
            "accepted_auditable_task_count": accepted_count,
            "pr_issue_task_count": pr_issue_count,
            "swebench_like_anchor_count": 4,
            "task_refs": [],
            "inventory_report_ref": {},
            "visibility_scan_ref": {},
            "status": "passed",
        },
    )
    return path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
