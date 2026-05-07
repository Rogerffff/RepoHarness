from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from repo_harness.errors import ConfigError
from repo_harness.pre_verl_agentloop import (
    _selector_input_error,
    inspect_pre_verl_agentloop_run_config,
    inspect_pre_verl_agentloop_task_definitions,
    load_pre_verl_swebench_dev_runtime_plan,
)
from repo_harness.scaffolds import build_scaffold, resolve_feedback_policy
from repo_harness.tasks import RunnableTask, TaskDefinition
from repo_harness.config import load_run_config


def test_pre_verl_agentloop_task_definitions_pass_formal_gates(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path)
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    result = inspect_pre_verl_agentloop_task_definitions(
        manifest,
        assert_run_task_compatible=True,
        assert_evaluator_only_hidden_inputs=True,
        assert_no_hidden_material_in_model_visible_fields=True,
    )

    assert "passed" in result


def test_pre_verl_agentloop_task_definitions_reject_legacy_v3_adapter(tmp_path: Path) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"v3_adapter": "swebench_like_fixed"},
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="legacy v3_adapter=swebench_like_fixed"):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_run_task_compatible=True,
            assert_evaluator_only_hidden_inputs=True,
        )


def test_pre_verl_agentloop_task_definitions_do_not_accept_tag_only_final_only(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"swe_bench_like_final_only": None, "final_only": None},
        tags=["swe_bench_like_final_only", "final_only"],
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="metadata.swe_bench_like_final_only"):
        inspect_pre_verl_agentloop_task_definitions(manifest, assert_run_task_compatible=True)


def test_pre_verl_agentloop_runtime_helper_rejects_missing_final_only_metadata(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"swe_bench_like_final_only": None, "final_only": None},
    )
    definition = TaskDefinition.model_validate(yaml.safe_load(task_path.read_text(encoding="utf-8")))

    with pytest.raises(ConfigError, match="metadata is incomplete"):
        load_pre_verl_swebench_dev_runtime_plan(RunnableTask.from_definition(definition))


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("pre_verl_adapter", "other_adapter", "metadata.pre_verl_adapter"),
        ("pre_verl_agentloop_mode", "ad_hoc", "metadata.pre_verl_agentloop_mode"),
        (
            "pre_verl_agentloop_baseline_source",
            "direct_provider_prompt",
            "metadata.pre_verl_agentloop_baseline_source",
        ),
        (
            "pre_verl_swebench_dev_manifest_path",
            ["not", "a", "string"],
            "pre_verl_swebench_dev_manifest_path must be a non-empty string",
        ),
        (
            "pre_verl_swebench_dev_manifest_path",
            "   ",
            "pre_verl_swebench_dev_manifest_path must be a non-empty string",
        ),
    ],
)
def test_pre_verl_agentloop_task_definitions_reject_bad_formal_metadata(
    tmp_path: Path,
    key: str,
    value: object,
    message: str,
) -> None:
    task_path = _write_task_definition(tmp_path, metadata_updates={key: value})
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match=message):
        inspect_pre_verl_agentloop_task_definitions(manifest, assert_run_task_compatible=True)


@pytest.mark.parametrize(
    ("ref_update", "message"),
    [
        ({"visibility": "model_visible"}, "visibility=evaluator_only"),
        ({"path": 123}, "must bind path or relative_path"),
        ({"path": "   "}, "must bind path or relative_path"),
        ({"sha256": "Z" * 64}, "must bind sha256"),
        ({"sha256": "a" * 63}, "must bind sha256"),
        ({"size_bytes": -1}, "must bind non-negative size_bytes"),
    ],
)
def test_pre_verl_agentloop_task_definitions_reject_bad_evaluator_refs(
    tmp_path: Path,
    ref_update: dict[str, object],
    message: str,
) -> None:
    bad_ref = _evaluator_ref("evaluator/hidden.patch")
    bad_ref.update(ref_update)
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"hidden_test_patch_ref": bad_ref},
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match=message):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_evaluator_only_hidden_inputs=True,
        )


def test_pre_verl_agentloop_task_definitions_reject_truncated_selector_ref(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    selector_path = task_path.parent / "evaluator" / "pass_to_pass.json"
    selector_path.write_text(
        '["tests/test_sample.py::test_valid["]\n',
        encoding="utf-8",
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="不可 collect 的 pytest selector"):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_evaluator_only_hidden_inputs=True,
        )


def test_pre_verl_agentloop_task_definitions_reject_hidden_visible_markers(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(
        tmp_path,
        issue="Fix the bug. hidden_test.patch should not be visible.",
    )
    manifest = _write_manifest(tmp_path, {"task_definition_refs": [{"path": _rel(tmp_path, task_path)}]})

    with pytest.raises(ConfigError, match="model-visible field issue contains hidden marker"):
        inspect_pre_verl_agentloop_task_definitions(
            manifest,
            assert_no_hidden_material_in_model_visible_fields=True,
        )


def test_pre_verl_selector_exit_code_four_is_not_implicitly_harness_input_error() -> None:
    assert _selector_input_error(
        {
            "exit_code": 4,
            "error_type": "test_command_error",
            "selector_input_validated": True,
            "selector_input_invalid": False,
        }
    ) is False
    assert _selector_input_error({"selector_input_invalid": True}) is True


def test_pre_verl_agentloop_run_config_passes_formal_gates(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(tmp_path, test_feedback_policy="disabled", max_test_runs=0)
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
                }
            ]
        },
    )

    result = inspect_pre_verl_agentloop_run_config(
        manifest,
        assert_final_only_test_feedback_disabled=True,
        assert_resolved_tools_derived=True,
        assert_no_hidden_feedback_visible=True,
    )

    assert "passed" in result


def test_pre_verl_agentloop_run_config_rejects_structured_public_feedback(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="structured_public_feedback",
        max_test_runs=4,
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="test_feedback_policy=disabled"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_without_formal_reasoning_policy(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="local_process",
        provider_specific_options={"allow_local_secret_file": True},
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="execution_mode=docker"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_docker_image_mismatch(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
            "reasoning_compatibility": "provider_private_state_replay",
        },
        docker_build_base_image="python:3.11-slim",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="docker_backend.build_base_image"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_missing_task_image(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path, execution_image=None)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
            "reasoning_compatibility": "provider_private_state_replay",
        },
        docker_build_base_image="python:3.12-slim",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="environment.execution_image"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_pre_verl_agentloop_run_config_rejects_deepseek_thinking_without_compatibility(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="disabled",
        max_test_runs=0,
        provider="deepseek",
        execution_mode="docker",
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
        },
        docker_build_base_image="python:3.12-slim",
    )
    manifest = _write_manifest(
        tmp_path,
        {
            "entries": [
                {
                    "task_definition_ref": {"path": _rel(tmp_path, task_path)},
                    "run_config_ref": {"path": config_path.name},
                    "resolved_tools": ["list_files", "read_file", "grep", "edit_file", "git_diff"],
                }
            ]
        },
    )

    with pytest.raises(ConfigError, match="reasoning_compatibility=provider_private_state_replay"):
        inspect_pre_verl_agentloop_run_config(
            manifest,
            assert_final_only_test_feedback_disabled=True,
            assert_resolved_tools_derived=True,
            assert_no_hidden_feedback_visible=True,
        )


def test_feedback_policy_rejects_non_disabled_for_swebench_like_final_only(
    tmp_path: Path,
) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        test_feedback_policy="structured_public_feedback",
        max_test_runs=4,
    )
    definition = TaskDefinition.model_validate(yaml.safe_load(task_path.read_text(encoding="utf-8")))
    config = load_run_config(config_path)
    scaffold = build_scaffold("patch_focused_react")

    with pytest.raises(ConfigError, match="SWE-Bench-like final-only task requires"):
        resolve_feedback_policy(run_config=config, scaffold=scaffold, task=definition)


def _write_task_definition(
    tmp_path: Path,
    *,
    metadata_updates: dict[str, object] | None = None,
    issue: str = "Fix the parser bug without using hidden verifier material.",
    tags: list[str] | None = None,
    execution_image: str | None = "python:3.12-slim",
) -> Path:
    fixtures = tmp_path / "fixtures"
    tasks_dir = fixtures / "tasks"
    repo_dir = fixtures / "repos" / "sample_repo"
    evaluator_dir = tasks_dir / "evaluator"
    tasks_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)
    evaluator_dir.mkdir()
    metadata = {
        "pre_verl_adapter": "swebench_lite_dev_agentloop_v0",
        "pre_verl_swebench_dev_manifest_path": "runs/pre_verl/dev_manifest.json",
        "pre_verl_agentloop_mode": "formal_baseline",
        "pre_verl_agentloop_baseline_source": "repo_harness_agentloop_run_task",
        "swe_bench_like_final_only": True,
        "final_only": True,
        "hidden_test_patch_ref": _evaluator_ref("evaluator/hidden.patch"),
        "fail_to_pass_selectors_ref": _evaluator_ref("evaluator/fail_to_pass.json"),
        "pass_to_pass_selectors_ref": _evaluator_ref("evaluator/pass_to_pass.json"),
    }
    if metadata_updates:
        for key, value in metadata_updates.items():
            if value is None:
                metadata.pop(key, None)
            else:
                metadata[key] = value
    task = {
        "id": "pre_verl_formal_task",
        "task_version": "pre_verl_formal_task_v0",
        "dataset_name": "pre_verl_swebench_lite_dev_custom_subset",
        "source_kind": "swebench_lite_dev_materialized",
        "dataset_split": "dev",
        "created_at": "2026-05-07",
        "repo": "../repos/sample_repo",
        "base_commit": "fixture",
        "issue": issue,
        "setup_command": None,
        "test_command": "pytest -q",
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 30,
            "agent_timeout_sec": 120,
            "final_verifier_timeout_sec": 60,
        },
        "environment": {
            "execution_image": execution_image,
            "python_version": "3.12",
            "package_manager": "pip",
            "setup_network_policy": "deny",
        },
        "expected_files": ["src/sample.py"],
        "fail_to_pass_tests": ["tests/test_sample.py::test_bug"],
        "pass_to_pass_tests": ["tests/test_sample.py::test_existing"],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
        "tags": tags or ["python"],
        "metadata": metadata,
    }
    task_path = tasks_dir / "formal_task.yaml"
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    return task_path


def _write_run_config(
    tmp_path: Path,
    *,
    test_feedback_policy: str,
    max_test_runs: int,
    provider: str = "replay",
    execution_mode: str = "local_process",
    provider_specific_options: dict[str, object] | None = None,
    docker_build_base_image: str | None = None,
) -> Path:
    config = {
        "run_id_prefix": "pre_verl_formal_baseline",
        "model": {
            "provider": provider,
            "model_id": "deepseek-v4-flash" if provider == "deepseek" else "replay-script-v0",
            "temperature": 0.0,
            "max_output_tokens": 4096,
            "provider_specific_options": provider_specific_options or {},
        },
        "runtime": {
            "scaffold_id": "patch_focused_react",
            "execution_mode": execution_mode,
            "permission_mode": "auto",
            "test_feedback_policy": test_feedback_policy,
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 24,
            "max_tool_calls": 96,
            "max_test_runs": max_test_runs,
            "task_timeout_sec": 1200,
        },
        "workspace": {
            "output_dir": str(tmp_path / "runs"),
            "keep_workspace": True,
            "default_command_timeout_sec": 90,
            "network_policy": "deny_agent_run",
        },
    }
    if docker_build_base_image is not None:
        config["runtime"]["docker_backend"] = {
            "build_base_image": docker_build_base_image,
            "image_ref": "repo-harness-pre-verl-test:v0",
        }
    config_path = tmp_path / "formal_run_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return manifest


def _rel(base: Path, path: Path) -> str:
    return path.relative_to(base).as_posix()


def _evaluator_ref(path: str) -> dict[str, object]:
    return {
        "path": path,
        "sha256": "a" * 64,
        "size_bytes": 1,
        "visibility": "evaluator_only",
    }
