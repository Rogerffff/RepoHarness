from __future__ import annotations

import json
from pathlib import Path

from repo_harness.config import RunConfig
from repo_harness.context import ContextBuilder
from repo_harness.evaluation import ResolvedVerifierPlan
from repo_harness.scaffolds import build_scaffold, resolve_allowed_tools, resolve_feedback_policy
from repo_harness.tasks import load_task
from repo_harness.workspace import DependencyState, RunWorkspace


ROOT = Path(__file__).resolve().parents[2]


def test_stage16c_context_builder_injects_public_environment_prompt(tmp_path: Path) -> None:
    loaded = load_task(ROOT / "tests/fixtures/tasks/task_001.yaml")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    plan = ResolvedVerifierPlan(
        verifier_config=loaded.verifier_config,
        initial_fail_to_pass_tests=[],
        initial_pass_to_pass_tests=[],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id="stage16c-plan",
    )
    run_config = RunConfig()
    scaffold = build_scaffold("patch_focused_react")
    feedback_policy = resolve_feedback_policy(
        run_config=run_config,
        scaffold=scaffold,
        task=loaded.runnable_task,
    )
    allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)

    messages = ContextBuilder().build_initial_messages(
        task=loaded.runnable_task,
        workspace=RunWorkspace(
            run_id="stage16c",
            workspace_path=workspace.as_posix(),
            artifact_dir=(tmp_path / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        run_config=run_config,
        resolved_verifier_plan=plan,
        allowed_tools=allowed_tools,
        scaffold=scaffold,
    )

    user = messages[1]["content"]
    assert isinstance(user, dict)
    public_environment = user["public_environment"]
    assert public_environment["public_test_entry"]["status"] == "available"
    prompt_block = public_environment["model_visible_prompt_block"]
    assert "read_file" in prompt_block
    assert "grep" in prompt_block
    assert "edit_file" in prompt_block
    assert "git_diff" in prompt_block
    assert "run_tests" in prompt_block
    assert user["context_metadata"]["public_environment_context_digest"] == (
        public_environment["context_digest"]
    )

    serialized = json.dumps(messages, ensure_ascii=False)
    for forbidden in (
        "/workspace",
        "/testbed",
        "/repo-harness-run",
        "conda activate",
        "pip install -e",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "hidden_verifier",
        "gold_patch",
        "test_patch",
        "reward_metadata",
    ):
        assert forbidden not in serialized


def test_stage16c_context_builder_hides_non_public_test_command(tmp_path: Path) -> None:
    loaded = load_task(ROOT / "tests/fixtures/tasks/task_001.yaml")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    unsafe_verifier_config = loaded.verifier_config.model_copy(
        update={"test_command": "pytest -k FAIL_TO_PASS"}
    )
    plan = ResolvedVerifierPlan(
        verifier_config=unsafe_verifier_config,
        initial_fail_to_pass_tests=[],
        initial_pass_to_pass_tests=[],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id="stage16c-unsafe-command-plan",
    )
    run_config = RunConfig()
    scaffold = build_scaffold("patch_focused_react")
    feedback_policy = resolve_feedback_policy(
        run_config=run_config,
        scaffold=scaffold,
        task=loaded.runnable_task,
    )
    allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)

    messages = ContextBuilder().build_initial_messages(
        task=loaded.runnable_task,
        workspace=RunWorkspace(
            run_id="stage16c-unsafe-command",
            workspace_path=workspace.as_posix(),
            artifact_dir=(tmp_path / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        run_config=run_config,
        resolved_verifier_plan=plan,
        allowed_tools=allowed_tools,
        scaffold=scaffold,
    )

    user = messages[1]["content"]
    assert isinstance(user, dict)
    assert "test_command" not in user["constraints"]
    assert "not shown" in user["constraints"]["tests"]
    serialized = json.dumps(messages, ensure_ascii=False)
    assert "FAIL_TO_PASS" not in serialized
    assert "pytest -k" not in serialized


def test_stage16c_diagnostic_shell_only_appears_when_enabled(tmp_path: Path) -> None:
    loaded = load_task(ROOT / "tests/fixtures/tasks/task_001.yaml")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    plan = ResolvedVerifierPlan(
        verifier_config=loaded.verifier_config,
        initial_fail_to_pass_tests=[],
        initial_pass_to_pass_tests=[],
        flaky_tests=[],
        parser_confidence=1.0,
        resolved_verifier_plan_id="stage16c-plan",
    )

    base_messages = _messages_for_scaffold(
        loaded=loaded,
        workspace=workspace,
        plan=plan,
        scaffold_id="patch_focused_react",
    )
    diagnostic_messages = _messages_for_scaffold(
        loaded=loaded,
        workspace=workspace,
        plan=plan,
        scaffold_id="patch_focused_react_diagnostic_shell",
    )

    base_payload = base_messages[1]["content"]
    diagnostic_payload = diagnostic_messages[1]["content"]
    assert isinstance(base_payload, dict)
    assert isinstance(diagnostic_payload, dict)
    assert "diagnostic_shell is not available" in (
        base_payload["public_environment"]["diagnostic_shell_summary"]
    )
    assert "diagnostic_shell is available" in (
        diagnostic_payload["public_environment"]["diagnostic_shell_summary"]
    )


def _messages_for_scaffold(
    *,
    loaded,
    workspace: Path,
    plan: ResolvedVerifierPlan,
    scaffold_id: str,
) -> list[dict[str, object]]:
    run_config = RunConfig.model_validate({"runtime": {"scaffold_id": scaffold_id}})
    scaffold = build_scaffold(scaffold_id)
    feedback_policy = resolve_feedback_policy(
        run_config=run_config,
        scaffold=scaffold,
        task=loaded.runnable_task,
    )
    allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
    return ContextBuilder().build_initial_messages(
        task=loaded.runnable_task,
        workspace=RunWorkspace(
            run_id=f"stage16c-{scaffold_id}",
            workspace_path=workspace.as_posix(),
            artifact_dir=(workspace.parent / f"artifacts-{scaffold_id}").as_posix(),
            dependency_state=DependencyState(),
        ),
        run_config=run_config,
        resolved_verifier_plan=plan,
        allowed_tools=allowed_tools,
        scaffold=scaffold,
    )
