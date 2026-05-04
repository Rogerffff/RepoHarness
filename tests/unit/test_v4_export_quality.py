import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.v4_agent_run import build_v4_agent_run_integration
from repo_harness.v4_export_quality import build_v4_export_quality, inspect_v4_export_quality
from repo_harness.v4_visibility import v4_contamination_denylist_sha256
from tests.unit.test_v4_agent_run import _external_inputs


def test_v4_export_quality_build_and_inspect_pass(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)

    assert "complete" in inspect_v4_export_quality(export_dir, assert_complete=True)
    assert main(["inspect-v4-export-quality", str(export_dir), "--assert-complete"]) == 0


def test_v4_export_quality_uses_unified_contamination_denylist_sha256(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    manifest = export_dir / "trajectory_quality_manifest.json"
    payload = _read_json(manifest)
    assert payload["denylist_sha256"] == v4_contamination_denylist_sha256()

    payload["denylist_sha256"] = "726436df4d92301a909a7951cf900ec0e6a45a7fb0a19077b87fe20da7afde99"
    _write_json(manifest, payload)

    with pytest.raises(ConfigError, match="denylist_sha256"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_unbound_final_verifier_result(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][1]["run_id"] = "v4-run-crashed-001"
    payload["samples"][1]["final_verifier_result"] = "rejected"
    payload["samples"][1]["final_verifier_result_ref"] = "audit-only:final-verifier:v4-run-crashed-001:rejected"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="final_verifier_boundary_report"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_reward_scalar_in_trainable_target(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][0]["trainable_payload"]["assistant_target"] = "include reward scalar in target"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="reward scalar"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_reward_label_in_trainable_target(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][0]["trainable_payload"]["assistant_target"] = "include reward label in target"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="reward label"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_hidden_selector_in_trainable_payload(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    fixture = export_dir / "fixtures" / "sft_valid.jsonl"
    records = _read_jsonl(fixture)
    records[0]["payload"]["messages"][0]["content"] = "use hidden_selector details"
    _write_jsonl(fixture, records)
    _refresh_manifest_fixture_ref(export_dir, "sft", "valid_fixture_ref", fixture)

    with pytest.raises(ConfigError, match="hidden_selector|hidden selector"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_packed_sample_without_original_trajectory_ref(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    packing = export_dir / "packing_manifest.json"
    payload = _read_json(packing)
    payload["packed_samples"][0].pop("original_trajectory_ref")
    _write_json(packing, payload)

    with pytest.raises(ConfigError, match="original trajectory"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_reward_promoting_rejected_sample(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][1]["reward_audit_outcome"] = "accepted"
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="verifier rejected"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_outcome_tier_trainability_mixup(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][0]["outcome_tier"] = "trainable"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="outcome_tier"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_outcome_tier_final_verifier_mismatch(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][1]["outcome_tier"] = "verifier_accepted"
    payload["samples"][1]["final_verifier_result"] = "rejected"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="final_verifier_result"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_reward_metadata_missing_required_fields(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["reward_metadata"].pop("reward_version")
    payload["reward_records"][0]["reward_metadata"].pop("formula")
    payload["reward_records"][0]["reward_metadata"].pop("invalid_for_training")
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="reward_version|formula|invalid_for_training"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_reward_metadata_or_structured_reward_model_visible(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["reward_metadata"]["model_visible"] = True
    payload["reward_records"][0]["structured_reward"]["model_visible"] = True
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="model_visible=false"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_reward_fields_outside_allowlist(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["reward_metadata"]["normalizer_debug_note"] = "audit-only extra field"
    payload["reward_records"][0]["structured_reward"]["normalizer_debug_note"] = "audit-only extra field"
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="allowlist"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_empty_object_reward_fields_outside_allowlist(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["reward_metadata"]["unauthorized_empty_object"] = {}
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="allowlist"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_structured_reward_missing_value(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["structured_reward"] = {"model_visible": False}
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="structured_reward.*value"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


@pytest.mark.parametrize(
    "value",
    ["1.0", True, -0.1, 1.1],
)
def test_v4_export_quality_rejects_invalid_structured_reward_value(tmp_path: Path, value) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["structured_reward"]["value"] = value
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="structured_reward.*value"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


@pytest.mark.parametrize(
    "field",
    ["components", "sources"],
)
def test_v4_export_quality_rejects_reward_metadata_empty_object_structure(tmp_path: Path, field: str) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["reward_metadata"][field] = {}
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match=field):
        inspect_v4_export_quality(export_dir, assert_complete=True)


@pytest.mark.parametrize(
    "field",
    ["components", "sources"],
)
def test_v4_export_quality_rejects_reward_metadata_empty_list_structure(tmp_path: Path, field: str) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    payload["reward_records"][0]["reward_metadata"][field] = []
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match=field):
        inspect_v4_export_quality(export_dir, assert_complete=True)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda metadata: metadata["components"][0].pop("name"),
        lambda metadata: metadata["components"][0].pop("weight"),
        lambda metadata: metadata["components"].__setitem__(0, []),
        lambda metadata: metadata["components"][0].__setitem__("weight", True),
        lambda metadata: metadata["sources"][0].pop("source"),
        lambda metadata: metadata["sources"][0].pop("model_visible"),
        lambda metadata: metadata["sources"].__setitem__(0, []),
        lambda metadata: metadata["sources"][0].__setitem__("model_visible", True),
    ],
)
def test_v4_export_quality_rejects_reward_metadata_element_schema_gaps(tmp_path: Path, mutation) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    mutation(payload["reward_records"][0]["reward_metadata"])
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match="components|sources"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda metadata: metadata.__setitem__("reward_version", ""), "reward_version"),
        (lambda metadata: metadata.__setitem__("formula", 7), "formula"),
        (lambda metadata: metadata.__setitem__("acceptance_policy_version", ""), "acceptance_policy_version"),
        (lambda metadata: metadata.__setitem__("invalid_for_training", "false"), "invalid_for_training"),
        (lambda metadata: metadata.__setitem__("invalid_reason", 42), "invalid_reason"),
        (lambda metadata: metadata.__setitem__("reward_clip_range", [0.0]), "reward_clip_range"),
        (lambda metadata: metadata.__setitem__("reward_clip_range", [1.0, 0.0]), "reward_clip_range"),
        (lambda metadata: metadata.__setitem__("reward_clip_range", [False, 1.0]), "reward_clip_range"),
    ],
)
def test_v4_export_quality_rejects_reward_metadata_scalar_schema_gaps(
    tmp_path: Path,
    mutation,
    expected: str,
) -> None:
    export_dir = _build(tmp_path)
    reward = export_dir / "reward_audit_report.json"
    payload = _read_json(reward)
    mutation(payload["reward_records"][0]["reward_metadata"])
    _write_json(reward, payload)

    with pytest.raises(ConfigError, match=expected):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_failure_dataset_missing_binding(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    failure = export_dir / "failure_dataset.jsonl"
    records = _read_jsonl(failure)
    records[0].pop("tool_call_id")
    records[0].pop("workspace_state_ref")
    records[0].pop("final_verifier_result_ref")
    _write_jsonl(failure, records)

    with pytest.raises(ConfigError, match="tool_call_id|workspace_state_ref|final_verifier_result_ref"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_failure_dataset_missing_run_or_category(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    failure = export_dir / "failure_dataset.jsonl"
    records = _read_jsonl(failure)
    records[0].pop("run_id")
    records[0].pop("failure_category")
    _write_jsonl(failure, records)

    with pytest.raises(ConfigError, match="run_id|failure_category"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_missing_negative_fixture(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    manifest = export_dir / "trajectory_quality_manifest.json"
    payload = _read_json(manifest)
    payload["export_fixture_refs"]["rl"].pop("negative_fixture_ref")
    _write_json(manifest, payload)

    with pytest.raises(ConfigError, match="negative_fixture_ref"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_unflagged_test_overfitting_risk(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "test_overfitting_risk_audit_report.json"
    payload = _read_json(report)
    payload["risk_records"][0]["flagged"] = False
    payload["risk_records"][0]["export_blocked"] = False
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="flagged=true"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_missing_verifier_overfitting_risk(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "test_overfitting_risk_audit_report.json"
    payload = _read_json(report)
    payload["risk_records"] = [
        record for record in payload["risk_records"] if record["risk_type"] != "modified_verifier_configuration"
    ]
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="modified_verifier_configuration"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_excessive_patch_as_main_fact(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "patch_quality_report.json"
    payload = _read_json(report)
    payload["patch_records"][1]["accepted_main_fact"] = True
    payload["patch_records"][1]["reward_main_fact"] = True
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="excessive patch"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_missing_patch_quality_metrics(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "patch_quality_report.json"
    payload = _read_json(report)
    payload["patch_records"][0].pop("changed_file_count")
    payload["patch_records"][0].pop("test_file_change_ratio")
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="patch quality metric"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_silent_blocked_pair_report(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "blocked_pair_report.json"
    payload = _read_json(report)
    payload["warning"] = False
    payload["sample_count"] = 0
    payload["rejected_reason_distribution"] = {}
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="blocked_pair_report"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_invalid_trainable_preference_pair(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "preference_pair_trainability_report.json"
    payload = _read_json(report)
    payload["pair_records"][0]["chosen_sample_id"] = "sample-rejected-diagnostic-failure"
    payload["pair_records"][0]["rejected_sample_id"] = "sample-accepted-trainable-sft"
    payload["pair_records"][0]["baseline_blocked"] = True
    payload["pair_records"][0]["compare_scope"] = {}
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="chosen_sample_id|rejected_sample_id|baseline_blocked|compare_scope"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


@pytest.mark.parametrize(
    "field",
    [
        "task_id",
        "source_tree_hash",
        "baseline_verifier_plan_hash",
        "final_verifier_plan_hash",
        "tool_schema_snapshot_hash",
        "context_strategy_id",
    ],
)
def test_v4_export_quality_rejects_preference_pair_compare_fact_mismatch(tmp_path: Path, field: str) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][1][field] = f"mismatch-{field}"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="可比较字段"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_preference_pair_without_comparable_formal_outcomes(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    sample_tier = export_dir / "sample_tier_manifest.json"
    payload = _read_json(sample_tier)
    payload["samples"][1]["final_verifier_result"] = "accepted"
    payload["samples"][1]["final_verifier_result_ref"] = "audit-only:final-verifier:v4-run-interrupted-001:accepted"
    payload["samples"][1]["outcome_tier"] = "verifier_accepted"
    _write_json(sample_tier, payload)

    with pytest.raises(ConfigError, match="rejected_sample_id|final_verifier_boundary_report"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_preference_pair_count_mismatch(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    report = export_dir / "preference_pair_trainability_report.json"
    payload = _read_json(report)
    payload["trainable_preference_pair_count"] = 0
    payload["blocked_pair_count"] = 0
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="count"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_rejects_no_trainable_pair_without_specific_block_reason(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)
    preference = export_dir / "preference_pair_trainability_report.json"
    pref_payload = _read_json(preference)
    pref_payload["pair_records"] = [pref_payload["pair_records"][1]]
    pref_payload["trainable_preference_pair_count"] = 0
    pref_payload["blocked_pair_count"] = 1
    _write_json(preference, pref_payload)
    blocked = export_dir / "blocked_pair_report.json"
    blocked_payload = _read_json(blocked)
    blocked_payload["blocked_reason"] = "preference_pair_baseline_blocked"
    _write_json(blocked, blocked_payload)

    with pytest.raises(ConfigError, match="no_trainable_preference_pair"):
        inspect_v4_export_quality(export_dir, assert_complete=True)


def test_v4_export_quality_build_respects_fail_if_output_exists(tmp_path: Path) -> None:
    export_dir = _build(tmp_path)

    with pytest.raises(ConfigError, match="输出已存在"):
        build_v4_export_quality(
            output_dir=export_dir,
            agent_run_integration=tmp_path / "agent",
            fail_if_output_exists=True,
        )


def _build(tmp_path: Path) -> Path:
    agent_dir = tmp_path / "agent"
    build_v4_agent_run_integration(output_dir=agent_dir, **_external_inputs(tmp_path))
    export_dir = tmp_path / "export"
    build_v4_export_quality(output_dir=export_dir, agent_run_integration=agent_dir)
    return export_dir


def _refresh_manifest_fixture_ref(export_dir: Path, export_format: str, ref_name: str, path: Path) -> None:
    manifest = export_dir / "trajectory_quality_manifest.json"
    payload = _read_json(manifest)
    payload["export_fixture_refs"][export_format][ref_name]["sha256"] = _sha256_file(path)
    payload["export_fixture_refs"][export_format][ref_name]["size_bytes"] = path.stat().st_size
    _write_json(manifest, payload)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()
