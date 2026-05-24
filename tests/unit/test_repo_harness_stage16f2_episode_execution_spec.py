from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from repo_harness.config import RunConfig
from repo_harness.context import ContextBuilder
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.execution import (
    EpisodeExecutionSpec,
    EpisodeExecutionSpecBuilder,
    build_tool_registry_digest,
    build_tool_schema_snapshot_digest,
    compute_spec_payload_sha256,
)
from repo_harness.schema_base import stable_hash
from repo_harness.tasks import (
    EnvironmentSpec,
    RunnableTask,
    TaskTimeouts,
    VerifierConfig,
    VisibilityPolicy,
    build_public_environment_context,
)
from repo_harness.workspace import DependencyState, RunWorkspace


def _source_repo(tmp_path: Path) -> Path:
    source = tmp_path / "source_repo"
    source.mkdir()
    (source / "README.md").write_text("stage16f2 repo context\n", encoding="utf-8")
    (source / "pkg.py").write_text("VALUE = 1\n", encoding="utf-8")
    return source


def _task() -> RunnableTask:
    visibility = VisibilityPolicy()
    verifier = VerifierConfig(
        test_command="python -m pytest tests/test_public.py -q",
        test_timeout_sec=30,
        final_verifier_timeout_sec=60,
        fail_to_pass_tests=["tests/test_hidden.py::test_fix"],
        pass_to_pass_tests=["tests/test_public.py::test_existing"],
        visibility_policy=visibility,
    )
    return RunnableTask(
        task_id="stage16f2_task",
        task_version="v1",
        dataset_name="stage16f2_fixture",
        issue_statement="Update the package behaviour.",
        repo_source="stage16f2_repo",
        environment=EnvironmentSpec(),
        timeouts=TaskTimeouts(
            setup_timeout_sec=30,
            test_timeout_sec=30,
            agent_timeout_sec=120,
            final_verifier_timeout_sec=60,
        ),
        verifier_config=verifier,
        expected_files=["pkg.py"],
        visibility_policy=visibility,
    )


def _run_config(*, scaffold_id: str = "patch_focused_react_diagnostic_shell") -> RunConfig:
    return RunConfig.model_validate(
        {
            "model": {"provider": "fake", "model_id": "fake-stage16f2"},
            "runtime": {
                "scaffold_id": scaffold_id,
                "permission_mode": "auto",
                "test_feedback_policy": "public_only",
                "feedback_tests_passed_policy": "require_model_final",
                "max_turns": 3,
                "max_tool_calls": 5,
                "max_test_runs": 2,
            },
            "workspace": {
                "network_policy": "deny_agent_run",
                "max_tool_output_chars": 8000,
            },
        }
    )


def _workspace(tmp_path: Path, run_id: str = "stage16f2_run") -> RunWorkspace:
    source = _source_repo(tmp_path)
    return RunWorkspace(
        run_id=run_id,
        workspace_path=source.as_posix(),
        repo_base_commit="stage16f2-base",
        execution_mode="local_process",
        artifact_dir=(tmp_path / "artifacts").as_posix(),
        dependency_state=DependencyState(),
    )


def _resolved_plan(task: RunnableTask, run_id: str = "stage16f2_run") -> ResolvedVerifierPlan:
    return ResolvedVerifierPlan(
        verifier_config=task.verifier_config,
        initial_fail_to_pass_tests=["tests/test_hidden.py::test_fix"],
        initial_pass_to_pass_tests=["tests/test_public.py::test_existing"],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id=f"{run_id}_verifier_plan",
    )


def _build_spec(tmp_path: Path, *, scaffold_id: str = "patch_focused_react_diagnostic_shell") -> EpisodeExecutionSpec:
    task = _task()
    run_config = _run_config(scaffold_id=scaffold_id)
    workspace = _workspace(tmp_path)
    plan = _resolved_plan(task)
    return EpisodeExecutionSpecBuilder().build_spec_from_loaded_task(
        task=task,
        workspace=workspace,
        run_config=run_config,
        resolved_verifier_plan=plan,
        run_id=workspace.run_id,
        task_ref="rh://task/stage16f2_task",
        run_config_ref="rh://run-config/stage16f2",
    )


def test_stage16f2_builder_matches_context_builder_digest(tmp_path: Path) -> None:
    task = _task()
    run_config = _run_config()
    workspace = _workspace(tmp_path)
    plan = _resolved_plan(task)
    spec = EpisodeExecutionSpecBuilder().build_spec_from_loaded_task(
        task=task,
        workspace=workspace,
        run_config=run_config,
        resolved_verifier_plan=plan,
        run_id=workspace.run_id,
    )
    public_environment = build_public_environment_context(
        task=task,
        resolved_verifier_plan=plan,
        test_feedback_policy=spec.feedback_facts.test_feedback_policy,
        allowed_tools=spec.allowed_tool_names,
    )
    direct_messages = ContextBuilder().build_initial_messages(
        task=task,
        workspace=workspace,
        run_config=run_config,
        resolved_verifier_plan=plan,
        allowed_tools=spec.allowed_tool_names,
        public_environment_context=public_environment,
    )

    assert spec.context_facts.initial_messages_digest == stable_hash(direct_messages)
    assert spec.context_facts.raw_prompt_digest == stable_hash(direct_messages)
    assert spec.initial_messages == direct_messages
    assert spec.context_facts.public_environment_context_digest == public_environment.context_digest


def test_stage16f2_builder_records_tool_and_feedback_facts(tmp_path: Path) -> None:
    spec = _build_spec(tmp_path)

    assert "diagnostic_shell" in spec.allowed_tool_names
    assert spec.tool_facts.tool_schema_snapshot_digest == build_tool_schema_snapshot_digest(spec.allowed_tool_names)
    assert spec.tool_facts.tool_registry_digest == build_tool_registry_digest(spec.allowed_tool_names)
    assert spec.feedback_facts.test_feedback_policy == "public_only"
    assert spec.feedback_facts.feedback_tests_passed_policy == "require_model_final"
    assert spec.verifier_facts.resolved_verifier_plan_digest
    assert spec.runtime_resolved_verifier_plan is not None


def test_stage16f2_public_payload_excludes_runtime_verifier_plan(tmp_path: Path) -> None:
    spec = _build_spec(tmp_path)
    payload = spec.public_artifact_payload()
    encoded = json.dumps(payload, sort_keys=True)

    assert "runtime_resolved_verifier_plan" not in payload
    assert "tests/test_hidden.py::test_fix" not in encoded
    assert "resolved_verifier_plan_digest" in encoded
    assert spec.spec_payload_sha256 == EpisodeExecutionSpec.model_validate(payload).spec_payload_sha256


@pytest.mark.parametrize(
    "hidden_content",
    [
        "hidden_verifier /Users/roger/private",
        "tests/test_hidden.py::test_fix",
        "FAIL_TO_PASS tests/test_public.py",
        "pass to pass selector leak",
        "runtime private artifact /opt/repo-harness-run",
        "Runtime_Private C:\\Users\\roger\\secret",
        "runtime-private:/opaque/raw",
        "/mnt/shared/runtime_private/evidence",
        "/Volumes/data/repo-harness-run",
        "/etc/passwd",
        "/srv/repo/private",
        "/a/b/c",
        "runtime private ref opaque_ref_123",
        "runtime-private ref opaque_ref_123",
    ],
)
def test_stage16f2_initial_messages_visibility_tamper_is_rejected(
    tmp_path: Path,
    hidden_content: str,
) -> None:
    spec = _build_spec(tmp_path)
    payload = spec.public_artifact_payload()
    hidden_messages = [{"role": "user", "content": hidden_content}]
    payload["initial_messages"] = hidden_messages
    payload["context_facts"]["initial_messages_digest"] = stable_hash(hidden_messages)
    payload["context_facts"]["raw_prompt_digest"] = stable_hash(hidden_messages)
    payload["spec_payload_sha256"] = compute_spec_payload_sha256(payload)

    with pytest.raises(ValueError, match="initial_messages"):
        EpisodeExecutionSpec.model_validate(payload)


def test_stage16f2_public_payload_revalidates_model_copy_tamper(tmp_path: Path) -> None:
    spec = _build_spec(tmp_path)
    hidden_messages = [{"role": "user", "content": "tests/test_public.py::test_existing"}]
    context_facts = spec.context_facts.model_copy(
        update={
            "initial_messages_digest": stable_hash(hidden_messages),
            "raw_prompt_digest": stable_hash(hidden_messages),
        }
    )
    payload = spec.public_artifact_payload()
    payload["initial_messages"] = hidden_messages
    payload["context_facts"] = context_facts.model_dump(mode="json")
    payload["spec_payload_sha256"] = compute_spec_payload_sha256(payload)
    tampered = spec.model_copy(
        update={
            "initial_messages": hidden_messages,
            "context_facts": context_facts,
            "spec_payload_sha256": payload["spec_payload_sha256"],
        }
    )

    with pytest.raises(ValueError, match="runtime hidden verifier selector"):
        tampered.public_artifact_payload()


def test_stage16f2_builder_and_spec_imports_do_not_load_heavy_modules(tmp_path: Path) -> None:
    _build_spec(tmp_path)

    loaded = [name for name in ("torch", "ray", "tensordict", "verl") if name in sys.modules]
    assert loaded == []


def test_stage16f2_builder_does_not_import_forbidden_entrypoints() -> None:
    import repo_harness.execution as execution

    assert execution.__name__ == "repo_harness.execution"
    execution_root = Path("src/repo_harness/execution")
    forbidden = ("repo_harness_verl", "from verl", "import verl", "repo_harness.evaluation.runner")
    matches: list[tuple[str, str]] = []
    for path in sorted(execution_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                matches.append((path.as_posix(), marker))
    assert matches == []
