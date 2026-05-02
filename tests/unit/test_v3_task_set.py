from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import pytest
import yaml

from repo_harness.config import RunConfig
from repo_harness.errors import ConfigError
from repo_harness.scaffolds import build_scaffold, resolve_feedback_policy
from repo_harness.tasks import RunnableTask, TaskDefinition, load_task
from repo_harness.v3_task_set import build_v3_task_set, inspect_v3_task_set

ROOT = Path(__file__).resolve().parents[2]
REAL_INPUTS = ROOT / "tests/fixtures/v3/real_repositories/real_repository_task_inputs.json"
SWEBENCH_FIXTURE = ROOT / "tests/fixtures/v3/swebench_lite_fixed"
SWEBENCH_MANIFEST = SWEBENCH_FIXTURE / "adapter_inputs/task_input_manifest.json"
SWEBENCH_EVIDENCE = ROOT / "docs/v3/evidence/swebench-lite-fixed"


def test_build_v3_task_set_generates_real_and_swebench_facts(tmp_path: Path):
    output = build_v3_task_set(
        real_repository_inputs=REAL_INPUTS,
        swebench_fixture_dir=SWEBENCH_FIXTURE,
        swebench_manifest=SWEBENCH_MANIFEST,
        swebench_evidence_dir=SWEBENCH_EVIDENCE,
        output_dir=tmp_path / "task_set",
    )

    real_manifest = _read_json(output / "real_repository_task_manifest.json")
    swebench_facts = _read_json(output / "swebench_like_task_facts.json")
    adapter_facts = _read_json(output / "task_adapter_facts.json")

    assert real_manifest["task_count"] == 3
    assert real_manifest["public_archive_count"] == 1
    assert real_manifest["unique_source_tree_hash_count"] == 3
    assert swebench_facts["accepted_task_ids"] == [
        "pytest-dev__pytest-7220",
        "pytest-dev__pytest-8365",
        "sympy__sympy-24909",
    ]
    assert adapter_facts["task_count"] == 6
    assert "v3_task_set=complete" in inspect_v3_task_set(output, assert_complete=True)
    public_source_facts = _read_json(
        output / "real_repository_source_facts/realrepo_public_sampleproject_add_two.json"
    )
    assert public_source_facts["dataset_source_revision"] == "repo_harness_v3_real_repository_tasks_20260502"

    public_task = output / "generated_tasks/real_repository/realrepo_public_sampleproject_add_two.yaml"
    local_task = output / "generated_tasks/real_repository/realrepo_local_buggy_calculator.yaml"
    swebench_task = output / "generated_tasks/swebench_like/pytest-dev__pytest-7220.yaml"
    assert load_task(public_task).runnable_task.task_id == "realrepo_public_sampleproject_add_two"
    assert load_task(local_task).runnable_task.task_id == "realrepo_local_buggy_calculator"
    swebench_definition = TaskDefinition.model_validate(
        yaml.safe_load(swebench_task.read_text(encoding="utf-8"))
    )
    assert swebench_definition.metadata["swe_bench_like_final_only"] is True
    assert "swe_bench_like_final_only" in swebench_definition.tags
    feedback_policy = resolve_feedback_policy(
        run_config=RunConfig.model_validate({"runtime": {"scaffold_id": "simple_react"}}),
        scaffold=build_scaffold("simple_react"),
        task=RunnableTask.from_definition(swebench_definition),
    )
    assert feedback_policy.resolved_test_feedback_policy == "disabled"


def test_build_v3_task_set_rejects_empty_real_repository_field(tmp_path: Path):
    inputs = _copy_real_inputs(tmp_path)
    payload = _read_json(inputs)
    payload["tasks"][0]["issue"] = ""
    _write_json(inputs, payload)

    with pytest.raises(ConfigError, match="issue"):
        build_v3_task_set(
            real_repository_inputs=inputs,
            swebench_fixture_dir=SWEBENCH_FIXTURE,
            swebench_manifest=SWEBENCH_MANIFEST,
            swebench_evidence_dir=SWEBENCH_EVIDENCE,
            output_dir=tmp_path / "task_set",
        )


def test_build_v3_task_set_rejects_swebench_revision_mismatch(tmp_path: Path):
    manifest = tmp_path / "task_input_manifest.json"
    payload = _read_json(SWEBENCH_MANIFEST)
    payload["dataset_revision"] = "floating-default-branch"
    _write_json(manifest, payload)

    with pytest.raises(ConfigError, match="dataset revision"):
        build_v3_task_set(
            real_repository_inputs=REAL_INPUTS,
            swebench_fixture_dir=SWEBENCH_FIXTURE,
            swebench_manifest=manifest,
            swebench_evidence_dir=SWEBENCH_EVIDENCE,
            output_dir=tmp_path / "task_set",
        )


def test_build_v3_task_set_rejects_swebench_jsonl_sha_mismatch(tmp_path: Path):
    manifest = tmp_path / "task_input_manifest.json"
    payload = _read_json(SWEBENCH_MANIFEST)
    payload["adapter_visible_input_ref"]["sha256"] = "0" * 64
    _write_json(manifest, payload)

    with pytest.raises(ConfigError, match="sha256"):
        build_v3_task_set(
            real_repository_inputs=REAL_INPUTS,
            swebench_fixture_dir=SWEBENCH_FIXTURE,
            swebench_manifest=manifest,
            swebench_evidence_dir=SWEBENCH_EVIDENCE,
            output_dir=tmp_path / "task_set",
        )


def test_build_v3_task_set_rejects_swebench_row_revision_drift(tmp_path: Path):
    fixture = tmp_path / "fixture"
    shutil.copytree(SWEBENCH_FIXTURE, fixture)
    adapter_dir = fixture / "adapter_inputs"
    tasks_path = adapter_dir / "swebench_like_tasks.jsonl"
    manifest_path = adapter_dir / "task_input_manifest.json"
    rows = _read_jsonl(tasks_path)
    rows[0]["dataset_revision"] = "floating-default-branch"
    _write_jsonl(tasks_path, rows)
    manifest = _read_json(manifest_path)
    manifest["adapter_visible_input_ref"]["path"] = tasks_path.as_posix()
    manifest["adapter_visible_input_ref"]["sha256"] = _sha256_file(tasks_path)
    manifest["adapter_visible_input_ref"]["size_bytes"] = tasks_path.stat().st_size
    manifest["tasks"][0]["task_input_sha256"] = _sha256_json(rows[0])
    _write_json(manifest_path, manifest)
    _write_named_sha256(tasks_path)
    _write_named_sha256(manifest_path)

    with pytest.raises(ConfigError, match="row dataset revision"):
        build_v3_task_set(
            real_repository_inputs=REAL_INPUTS,
            swebench_fixture_dir=fixture,
            swebench_manifest=manifest_path,
            swebench_evidence_dir=SWEBENCH_EVIDENCE,
            output_dir=tmp_path / "task_set",
        )


def test_inspect_v3_task_set_rejects_all_local_real_repository_tasks(tmp_path: Path):
    inputs = _copy_real_inputs(tmp_path)
    payload = _read_json(inputs)
    payload["tasks"][0]["source_kind"] = "fixed_local_mirror"
    payload["tasks"][0]["remote_url"] = "local://tests/fixtures/repos/missing_helper_file"
    payload["tasks"][0]["source_path"] = "tests/fixtures/repos/missing_helper_file"
    payload["tasks"][0]["mirror_sha256"] = "98f067029e82433bb127e4cf49fa709d15ad857adab4b7edcad306305dde6437"
    payload["tasks"][0]["source_tree_hash"] = "98f067029e82433bb127e4cf49fa709d15ad857adab4b7edcad306305dde6437"
    payload["tasks"][0].pop("archive_path", None)
    payload["tasks"][0].pop("archive_sha256", None)
    payload["tasks"][0].pop("expected_root_directory", None)
    _write_json(inputs, payload)
    output = build_v3_task_set(
        real_repository_inputs=inputs,
        swebench_fixture_dir=SWEBENCH_FIXTURE,
        swebench_manifest=SWEBENCH_MANIFEST,
        swebench_evidence_dir=SWEBENCH_EVIDENCE,
        output_dir=tmp_path / "task_set",
    )

    with pytest.raises(ConfigError, match="不能全部来自本地 fixture"):
        inspect_v3_task_set(output, assert_complete=True)


def test_inspect_v3_task_set_rejects_duplicate_local_fixture_sources(tmp_path: Path):
    inputs = _copy_real_inputs(tmp_path)
    payload = _read_json(inputs)
    payload["tasks"][2]["remote_url"] = payload["tasks"][1]["remote_url"]
    payload["tasks"][2]["source_path"] = payload["tasks"][1]["source_path"]
    payload["tasks"][2]["mirror_sha256"] = payload["tasks"][1]["mirror_sha256"]
    payload["tasks"][2]["source_tree_hash"] = payload["tasks"][1]["source_tree_hash"]
    _write_json(inputs, payload)
    output = build_v3_task_set(
        real_repository_inputs=inputs,
        swebench_fixture_dir=SWEBENCH_FIXTURE,
        swebench_manifest=SWEBENCH_MANIFEST,
        swebench_evidence_dir=SWEBENCH_EVIDENCE,
        output_dir=tmp_path / "task_set",
    )

    with pytest.raises(ConfigError, match="重复 source_tree_hash"):
        inspect_v3_task_set(output, assert_complete=True)


def test_inspect_v3_task_set_rejects_manifest_source_hash_forgery(tmp_path: Path):
    output = _build_task_set(tmp_path)
    manifest_path = output / "real_repository_task_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["tasks"][2]["source_tree_hash"] = "f" * 64
    manifest["unique_source_tree_hash_count"] = 3
    _write_json(manifest_path, manifest)

    with pytest.raises(ConfigError, match="source facts 字段不一致"):
        inspect_v3_task_set(output, assert_complete=True)


def _build_task_set(tmp_path: Path) -> Path:
    return build_v3_task_set(
        real_repository_inputs=REAL_INPUTS,
        swebench_fixture_dir=SWEBENCH_FIXTURE,
        swebench_manifest=SWEBENCH_MANIFEST,
        swebench_evidence_dir=SWEBENCH_EVIDENCE,
        output_dir=tmp_path / "task_set",
    )


def _copy_real_inputs(tmp_path: Path) -> Path:
    target = tmp_path / "real_repository_task_inputs.json"
    _write_json(target, _read_json(REAL_INPUTS))
    return target


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_named_sha256(path: Path) -> None:
    Path(str(path) + ".sha256").write_text(f"{_sha256_file(path)}  {path.name}\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_json(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
