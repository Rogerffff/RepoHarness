from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from repo_harness.config import load_run_config
from repo_harness.errors import ConfigError
from repo_harness.evaluation import runner
from repo_harness.pre_verl_agentloop import (
    PRE_VERL_RUN_CONFIG_PREFLIGHT_POLICY_VERSION,
    validate_pre_verl_run_config_entry,
)


def test_preflight_rejects_task_image_mismatch(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path, execution_image="python:3.10")
    config_path = _write_run_config(tmp_path, build_base_image="python:3.8")

    report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        assert_resolved_tools_derived=False,
    )

    assert report["passed"] is False
    assert any("docker_backend.build_base_image" in item for item in report["failures"])


def test_preflight_rejects_low_deepseek_thinking_output_budget(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(tmp_path, max_output_tokens=8192)

    report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        assert_resolved_tools_derived=False,
    )

    assert report["passed"] is False
    assert any("model.max_output_tokens>=32768" in item for item in report["failures"])


def test_preflight_allows_explicit_low_thinking_budget_escape_hatch(tmp_path: Path) -> None:
    task_path = _write_task_definition(tmp_path)
    config_path = _write_run_config(
        tmp_path,
        max_output_tokens=8192,
        provider_specific_options={
            "allow_local_secret_file": True,
            "thinking": {"type": "enabled"},
            "reasoning_compatibility": "provider_private_state_replay",
            "allow_low_thinking_output_budget": True,
        },
    )

    report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        assert_resolved_tools_derived=False,
    )

    assert report["passed"] is True


def test_preflight_rejects_missing_required_container_platform(tmp_path: Path) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"requested_container_platform": "linux/amd64"},
    )
    config_path = _write_run_config(tmp_path, requested_container_platform=None)

    report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        assert_resolved_tools_derived=False,
    )

    assert report["passed"] is False
    assert any("requested_container_platform" in item for item in report["failures"])


def test_preflight_rejects_wrong_required_container_platform(tmp_path: Path) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"requested_container_platform": "linux/amd64"},
    )
    config_path = _write_run_config(tmp_path, requested_container_platform="linux/arm64")

    report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        assert_resolved_tools_derived=False,
    )

    assert report["passed"] is False
    assert any("requested_container_platform" in item for item in report["failures"])


def test_preflight_writes_success_report_with_hashes(tmp_path: Path) -> None:
    task_path = _write_task_definition(
        tmp_path,
        metadata_updates={"requested_container_platform": "linux/amd64"},
    )
    config_path = _write_run_config(tmp_path, requested_container_platform="linux/amd64")
    report_path = tmp_path / "report.json"

    report = validate_pre_verl_run_config_entry(
        task_definition_path=task_path,
        config_path=config_path,
        report_path=report_path,
        assert_resolved_tools_derived=False,
    )

    assert report["passed"] is True
    assert report_path.exists()
    persisted = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "repo_harness_pre_verl_run_config_preflight_report_v0"
    assert persisted["preflight_policy_version"] == PRE_VERL_RUN_CONFIG_PREFLIGHT_POLICY_VERSION
    assert persisted["task_id"] == "pre_verl_formal_task"
    assert len(persisted["config_sha256"]) == 64
    assert len(persisted["task_definition_sha256"]) == 64
    assert persisted["resolved_execution_image"] == "python:3.12-slim"
    assert persisted["resolved_container_platform"] == "linux/amd64"
    assert persisted["provider"] == "deepseek"
    assert persisted["model_id"] == "deepseek-v4-pro"
    assert persisted["max_output_tokens"] == 32768
    assert persisted["thinking_mode"] == "enabled"


def test_run_task_preflight_failure_happens_before_provider_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_path = _write_task_definition(tmp_path, execution_image="python:3.10")
    config_path = _write_run_config(tmp_path, build_base_image="python:3.8")
    called = False
    workspace_called = False

    def fail_if_called(*args: object, **kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("provider client must not be created after preflight failure")

    def fail_if_workspace_called(*args: object, **kwargs: object) -> object:
        nonlocal workspace_called
        workspace_called = True
        raise AssertionError("workspace adapter must not be created after preflight failure")

    monkeypatch.setattr(runner, "create_model_client", fail_if_called)
    monkeypatch.setattr(runner, "create_workspace_adapter", fail_if_workspace_called)

    with pytest.raises(ConfigError, match="run_config_preflight_failed"):
        runner.run_task(task_path, config_path=config_path)

    assert called is False
    assert workspace_called is False
    report_path = tmp_path / "runs" / "pre_verl_formal_baseline_pre_verl_formal_task" / "run_config_preflight_report.json"
    assert report_path.exists()
    report = yaml.safe_load(report_path.read_text(encoding="utf-8"))
    assert report["passed"] is False
    assert any("docker_backend.build_base_image" in item for item in report["failures"])


def _write_task_definition(
    tmp_path: Path,
    *,
    execution_image: str = "python:3.12-slim",
    metadata_updates: dict[str, object] | None = None,
) -> Path:
    fixtures_dir = tmp_path / "fixtures"
    tasks_dir = fixtures_dir / "tasks"
    repo_dir = fixtures_dir / "repos" / "sample_repo"
    evaluator_dir = tasks_dir / "evaluator"
    tasks_dir.mkdir(parents=True)
    repo_dir.mkdir(parents=True)
    evaluator_dir.mkdir()
    (repo_dir / "README.md").write_text("fixture\n", encoding="utf-8")
    (evaluator_dir / "hidden.patch").write_text("", encoding="utf-8")
    (evaluator_dir / "fail_to_pass.json").write_text('["tests/test_sample.py::test_bug"]\n', encoding="utf-8")
    (evaluator_dir / "pass_to_pass.json").write_text('["tests/test_sample.py::test_existing"]\n', encoding="utf-8")
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
        metadata.update(metadata_updates)
    task = {
        "id": "pre_verl_formal_task",
        "task_version": "pre_verl_formal_task_v0",
        "dataset_name": "pre_verl_swebench_lite_dev_custom_subset",
        "source_kind": "swebench_lite_dev_materialized",
        "dataset_split": "dev",
        "created_at": "2026-05-11",
        "repo": "../repos/sample_repo",
        "base_commit": "fixture",
        "issue": "Fix the parser bug without using hidden verifier material.",
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
        "tags": ["python"],
        "metadata": metadata,
    }
    task_path = tasks_dir / "formal_task.yaml"
    task_path.write_text(yaml.safe_dump(task, sort_keys=False), encoding="utf-8")
    return task_path


def _write_run_config(
    tmp_path: Path,
    *,
    build_base_image: str = "python:3.12-slim",
    max_output_tokens: int = 32768,
    requested_container_platform: str | None = None,
    provider_specific_options: dict[str, object] | None = None,
) -> Path:
    options = provider_specific_options or {
        "allow_local_secret_file": True,
        "thinking": {"type": "enabled"},
        "reasoning_compatibility": "provider_private_state_replay",
    }
    config = {
        "run_id_prefix": "pre_verl_formal_baseline",
        "model": {
            "provider": "deepseek",
            "model_id": "deepseek-v4-pro",
            "temperature": 0.0,
            "max_output_tokens": max_output_tokens,
            "retry_policy": "provider_retry_v0",
            "provider_specific_options": options,
        },
        "runtime": {
            "scaffold_id": "patch_focused_react",
            "execution_mode": "docker",
            "docker_backend": {
                "build_base_image": build_base_image,
                "image_ref": "repo-harness-pre-verl-test:v0",
                "requested_container_platform": requested_container_platform,
            },
            "permission_mode": "auto",
            "test_feedback_policy": "disabled",
            "feedback_tests_passed_policy": "require_model_final",
            "max_turns": 24,
            "max_tool_calls": 96,
            "max_test_runs": 0,
            "task_timeout_sec": 1200,
        },
        "workspace": {
            "output_dir": str(tmp_path / "runs"),
            "keep_workspace": True,
            "default_command_timeout_sec": 90,
            "network_policy": "deny_agent_run",
        },
    }
    config_path = tmp_path / "formal_run_config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    load_run_config(config_path)
    return config_path


def _evaluator_ref(path: str) -> dict[str, object]:
    return {
        "path": path,
        "visibility": "evaluator_only",
        "redaction_status": "evaluator_only",
    }
