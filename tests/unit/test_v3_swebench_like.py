from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_harness.errors import ConfigError
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_swebench_like import expand_swebench_selectors, inspect_swebench_like
from repo_harness.workspace.source_hash import compute_file_sha256


def test_expand_swebench_selectors_maps_bare_sympy_function_to_patch_file():
    patch = """diff --git a/sympy/physics/units/tests/test_prefixes.py b/sympy/physics/units/tests/test_prefixes.py
--- a/sympy/physics/units/tests/test_prefixes.py
+++ b/sympy/physics/units/tests/test_prefixes.py
@@ -1,2 +1,3 @@
+def test_prefix_operations():
+    pass
"""

    assert expand_swebench_selectors(
        ["test_prefix_operations"],
        test_patch=patch,
        instance_id="sympy__sympy-24909",
    ) == ["sympy/physics/units/tests/test_prefixes.py::test_prefix_operations"]


def test_expand_swebench_selectors_rejects_ambiguous_bare_function():
    patch = """diff --git a/tests/test_a.py b/tests/test_a.py
--- a/tests/test_a.py
+++ b/tests/test_a.py
@@ -1 +1,2 @@
+def test_a(): pass
diff --git a/tests/test_b.py b/tests/test_b.py
--- a/tests/test_b.py
+++ b/tests/test_b.py
@@ -1 +1,2 @@
+def test_b(): pass
"""

    with pytest.raises(ConfigError, match="裸函数名 selector 无法唯一映射"):
        expand_swebench_selectors(["test_a"], test_patch=patch, instance_id="example")


def test_inspect_swebench_like_rejects_empty_selector_cache(tmp_path: Path):
    manifest = _fake_manifest(tmp_path, empty_selector_task="pytest-dev__pytest-7220")

    with pytest.raises(ConfigError, match="selector cache expanded_fail_to_pass 为空"):
        inspect_swebench_like(tmp_path, manifest=manifest, assert_complete=True)


def _fake_manifest(root: Path, *, empty_selector_task: str) -> Path:
    entries = []
    for task_id in ("pytest-dev__pytest-7220", "pytest-dev__pytest-8365", "sympy__sympy-24909"):
        task_root = root / "tasks" / task_id
        task_root.mkdir(parents=True)
        setup_commands = task_root / "setup_commands.json"
        _write_json(setup_commands, {"schema_version": "repo_harness_swebench_like_setup_commands_v3_v0", "commands": []})
        environment = task_root / "environment.json"
        _write_json(
            environment,
            {
                "schema_version": "repo_harness_swebench_like_environment_spec_v3_v0",
                "instance_id": task_id,
                "repo": "pytest-dev/pytest",
                "base_commit": "abc",
                "execution_image": "python:3.8-slim",
                "requested_container_platform": "linux/amd64",
                "setup_commands_ref": _ref(setup_commands, root).model_dump(mode="json"),
            },
        )
        patch = task_root / "verifier.patch"
        patch.write_text("diff --git a/tests/test_example.py b/tests/test_example.py\n", encoding="utf-8")
        selector_cache = task_root / "selector_cache.json"
        expanded_f2p = [] if task_id == empty_selector_task else ["tests/test_example.py::test_example"]
        _write_json(
            selector_cache,
            {
                "schema_version": "repo_harness_swebench_like_selector_cache_v3_v0",
                "instance_id": task_id,
                "expanded_fail_to_pass": expanded_f2p,
                "expanded_pass_to_pass": ["tests/test_example.py::test_regression"],
            },
        )
        plan = task_root / "plan.json"
        _write_json(
            plan,
            {
                "schema_version": "repo_harness_swebench_like_verifier_plan_v3_v0",
                "instance_id": task_id,
                "base_test_command": "python -m pytest -q",
                "fail_to_pass_command": "python -m pytest -q tests/test_example.py::test_example",
                "pass_to_pass_command": "python -m pytest -q tests/test_example.py::test_regression",
                "selector_source": "evaluator_only_manifest_ref",
                "selector_cache_ref": _ref(selector_cache, root).model_dump(mode="json"),
                "fail_to_pass_selector_count": 1,
                "pass_to_pass_selector_count": 1,
                "verifier_patch_ref": _ref(patch, root).model_dump(mode="json"),
                "per_command_timeout_sec": 30,
            },
        )
        baseline_f2p = task_root / "baseline_f2p.json"
        baseline_p2p = task_root / "baseline_p2p.json"
        gold = task_root / "gold.json"
        final = task_root / "final.json"
        _write_json(baseline_f2p, {"exit_code": 1})
        _write_json(baseline_p2p, {"exit_code": 0})
        _write_json(gold, {"fail_to_pass": {"exit_code": 0}, "pass_to_pass": {"exit_code": 0}})
        _write_json(final, {"accepted": True})
        entries.append(
            {
                "task_id": task_id,
                "repo": "pytest-dev/pytest",
                "environment_spec_ref": _ref(environment, root).model_dump(mode="json"),
                "verifier_plan_ref": _ref(plan, root).model_dump(mode="json"),
                "selector_cache_ref": _ref(selector_cache, root).model_dump(mode="json"),
                "baseline_fail_to_pass_evidence_ref": _ref(baseline_f2p, root).model_dump(mode="json"),
                "pass_to_pass_baseline_evidence_ref": _ref(baseline_p2p, root).model_dump(mode="json"),
                "gold_patch_passing_evidence_ref": _ref(gold, root).model_dump(mode="json"),
                "model_final_verifier_result_ref": _ref(final, root).model_dump(mode="json"),
            }
        )
    for name in ("source.json", "hidden.jsonl", "gold.jsonl"):
        (root / name).write_text("{}\n", encoding="utf-8")
    manifest = root / "swebench_like_task_manifest.json"
    _write_json(
        manifest,
        {
            "schema_version": "repo_harness_swebench_like_task_manifest_v3_v0",
            "accepted_task_ids": ["pytest-dev__pytest-7220", "pytest-dev__pytest-8365", "sympy__sympy-24909"],
            "task_count": 3,
            "official_harness_report_used_as_final_verifier": False,
            "source_materialization_report_ref": _ref(root / "source.json", root).model_dump(mode="json"),
            "hidden_verifier_inputs_ref": _ref(root / "hidden.jsonl", root).model_dump(mode="json"),
            "gold_patch_predictions_ref": _ref(root / "gold.jsonl", root).model_dump(mode="json"),
            "entries": entries,
        },
    )
    return manifest


def _ref(path: Path, root: Path) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=path.stem,
        relative_path=path.relative_to(root).as_posix(),
        kind="json",
        sha256=compute_file_sha256(path),
        size_bytes=path.stat().st_size,
        redaction_status="not_required",
        retention_policy="keep",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
