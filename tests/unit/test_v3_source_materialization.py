from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.v3_source_materialization import (
    build_v3_source_materialization,
    inspect_v3_source_materialization,
)
from repo_harness.v3_task_set import build_v3_task_set
from repo_harness.workspace.source_hash import compute_source_tree_hash

ROOT = Path(__file__).resolve().parents[2]
REAL_INPUTS = ROOT / "tests/fixtures/v3/real_repositories/real_repository_task_inputs.json"
SWEBENCH_FIXTURE = ROOT / "tests/fixtures/v3/swebench_lite_fixed"
SWEBENCH_MANIFEST = SWEBENCH_FIXTURE / "adapter_inputs/task_input_manifest.json"
SWEBENCH_EVIDENCE = ROOT / "docs/v3/evidence/swebench-lite-fixed"
SOURCE_MANIFEST = SWEBENCH_FIXTURE / "source_archives/source_archive_manifest.json"
HIDDEN_INPUTS = SWEBENCH_EVIDENCE / "evaluator_only/hidden_verifier_inputs.jsonl"


def test_build_v3_source_materialization_applies_verifier_patch_only_to_verifier_workspace(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    output = build_v3_source_materialization(
        task_set_dir=task_set,
        swebench_source_manifest=SOURCE_MANIFEST,
        hidden_verifier_inputs=HIDDEN_INPUTS,
        output_dir=tmp_path / "sources",
    )

    report = _read_json(output / "source_materialization_report.json")
    assert report["task_count"] == 6
    assert "v3_source_materialization=complete" in inspect_v3_source_materialization(
        output,
        report=output / "source_materialization_report.json",
        assert_complete=True,
    )
    swebench_entries = [entry for entry in report["entries"] if entry["task_category"] == "swebench_like"]
    assert len(swebench_entries) == 3
    for entry in swebench_entries:
        assert entry["verifier_patch_applied"] is True
        assert entry["verifier_patch_visibility"] == "evaluator_only"
        assert entry["agent_workspace_contains_verifier_patch"] is False
        assert entry["agent_workspace_ref"]["sha256"] == entry["source_tree_hash"]
        assert entry["verifier_workspace_ref"]["sha256"] != entry["source_tree_hash"]
        assert entry["expected_source_tree_hash"] == entry["source_tree_hash"]
        assert entry["source_provenance_kind"] == "swebench_source_archive_manifest"
        assert entry["remote_url"].startswith("https://github.com/")
        assert entry["archive_sha256"]
        assert entry["resolved_commit"] == entry["base_commit"]
        assert entry["materialization_command_facts"]["network_used"] is False

    real_entries = [entry for entry in report["entries"] if entry["task_category"] == "real_repository"]
    assert len(real_entries) == 3
    for entry in real_entries:
        assert entry["expected_source_tree_hash"] == entry["source_tree_hash"]
        assert entry["source_provenance_kind"] == "real_repository_source_facts"
        assert entry["remote_url"]
        assert entry["resolved_commit"] == entry["base_commit"]
        assert entry["materialization_command_facts"]["network_used"] is False
        if entry["source_type"] == "fixed_local_mirror":
            assert entry["mirror_sha256"] == entry["source_tree_hash"]
        else:
            assert entry["archive_sha256"]


def test_build_v3_source_materialization_rejects_floating_network_source(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    source_manifest = tmp_path / "source_archive_manifest.json"
    payload = _read_json(SOURCE_MANIFEST)
    payload["formal_run_network_source_allowed"] = True
    _write_json(source_manifest, payload)

    with pytest.raises(ConfigError, match="浮动网络 source"):
        build_v3_source_materialization(
            task_set_dir=task_set,
            swebench_source_manifest=source_manifest,
            hidden_verifier_inputs=HIDDEN_INPUTS,
            output_dir=tmp_path / "sources",
        )


def test_build_v3_source_materialization_rejects_source_archive_sha_mismatch(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    source_manifest = tmp_path / "source_archive_manifest.json"
    payload = _read_json(SOURCE_MANIFEST)
    payload["archives"][0]["archive_sha256"] = "0" * 64
    _write_json(source_manifest, payload)

    with pytest.raises(ConfigError, match="source archive sha256"):
        build_v3_source_materialization(
            task_set_dir=task_set,
            swebench_source_manifest=source_manifest,
            hidden_verifier_inputs=HIDDEN_INPUTS,
            output_dir=tmp_path / "sources",
        )


def test_build_v3_source_materialization_rejects_source_tree_hash_mismatch(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    source_manifest = tmp_path / "source_archive_manifest.json"
    payload = _read_json(SOURCE_MANIFEST)
    payload["archives"][0]["source_tree_hash"] = "0" * 64
    _write_json(source_manifest, payload)

    with pytest.raises(ConfigError, match="source_tree_hash"):
        build_v3_source_materialization(
            task_set_dir=task_set,
            swebench_source_manifest=source_manifest,
            hidden_verifier_inputs=HIDDEN_INPUTS,
            output_dir=tmp_path / "sources",
        )


def test_build_v3_source_materialization_rejects_real_source_facts_hash_mismatch(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    facts_path = task_set / "real_repository_source_facts/realrepo_local_buggy_calculator.json"
    facts = _read_json(facts_path)
    facts["source_tree_hash"] = "0" * 64
    _write_json(facts_path, facts)

    with pytest.raises(ConfigError, match="source_tree_hash"):
        build_v3_source_materialization(
            task_set_dir=task_set,
            swebench_source_manifest=SOURCE_MANIFEST,
            hidden_verifier_inputs=HIDDEN_INPUTS,
            output_dir=tmp_path / "sources",
        )


def test_inspect_v3_source_materialization_rejects_reported_agent_workspace_contamination(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    output = build_v3_source_materialization(
        task_set_dir=task_set,
        swebench_source_manifest=SOURCE_MANIFEST,
        hidden_verifier_inputs=HIDDEN_INPUTS,
        output_dir=tmp_path / "sources",
    )
    report_path = output / "source_materialization_report.json"
    report = _read_json(report_path)
    for entry in report["entries"]:
        if entry["task_category"] == "swebench_like":
            entry["agent_workspace_contains_verifier_patch"] = True
            break
    _write_json(report_path, report)

    with pytest.raises(ConfigError, match="agent workspace 包含 verifier patch"):
        inspect_v3_source_materialization(output, report=report_path, assert_complete=True)


def test_inspect_v3_source_materialization_rejects_real_agent_workspace_contamination(tmp_path: Path):
    task_set = _build_task_set(tmp_path)
    output = build_v3_source_materialization(
        task_set_dir=task_set,
        swebench_source_manifest=SOURCE_MANIFEST,
        hidden_verifier_inputs=HIDDEN_INPUTS,
        output_dir=tmp_path / "sources",
    )
    report_path = output / "source_materialization_report.json"
    report = _read_json(report_path)
    swebench_entry = next(entry for entry in report["entries"] if entry["task_id"] == "pytest-dev__pytest-7220")
    patch_path = output / swebench_entry["verifier_patch_ref"]["relative_path"]
    patch_text = patch_path.read_text(encoding="utf-8")
    leaked_line = next(
        line[1:].strip()
        for line in patch_text.splitlines()
        if line.startswith("+") and not line.startswith("+++") and len(line[1:].strip()) > 30
    )
    agent_workspace = output / swebench_entry["agent_workspace_ref"]["relative_path"]
    (agent_workspace / "leaked_verifier_material.txt").write_text(leaked_line + "\n", encoding="utf-8")
    swebench_entry["agent_workspace_ref"]["sha256"] = compute_source_tree_hash(agent_workspace)
    _write_json(report_path, report)

    with pytest.raises(ConfigError, match="agent workspace 包含 verifier patch 内容"):
        inspect_v3_source_materialization(output, report=report_path, assert_complete=True)


def _build_task_set(tmp_path: Path) -> Path:
    return build_v3_task_set(
        real_repository_inputs=REAL_INPUTS,
        swebench_fixture_dir=SWEBENCH_FIXTURE,
        swebench_manifest=SWEBENCH_MANIFEST,
        swebench_evidence_dir=SWEBENCH_EVIDENCE,
        output_dir=tmp_path / "task_set",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
