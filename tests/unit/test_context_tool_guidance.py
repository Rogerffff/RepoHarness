from pathlib import Path

from repo_harness.config import RunConfig
from repo_harness.context import ContextBuilder
from repo_harness.evaluation import ResolvedVerifierPlan
from repo_harness.tasks import load_task
from repo_harness.workspace import DependencyState, RunWorkspace


ROOT = Path(__file__).resolve().parents[2]


def test_symbol_search_guidance_prefers_repository_hint_roots(tmp_path: Path):
    loaded = load_task(ROOT / "tests/fixtures/tasks/task_001.yaml")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    plan = ResolvedVerifierPlan(
        verifier_config=loaded.verifier_config,
        initial_fail_to_pass_tests=loaded.verifier_config.fail_to_pass_tests,
        initial_pass_to_pass_tests=loaded.verifier_config.pass_to_pass_tests,
        parser_confidence=1.0,
        resolved_verifier_plan_id="plan",
    )

    messages = ContextBuilder().build_initial_messages(
        task=loaded.runnable_task,
        workspace=RunWorkspace(
            run_id="run",
            workspace_path=workspace.as_posix(),
            artifact_dir=(tmp_path / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        run_config=RunConfig(),
        resolved_verifier_plan=plan,
        allowed_tools=["read_file", "symbol_search"],
    )

    guidance = messages[1]["content"]["tool_use_guidance"]  # type: ignore[index]
    rendered = str(guidance)
    assert "symbol_search.root" in rendered
    assert "repository_hints" in rendered
    assert "repository_action_index" not in rendered
    assert "root='.'" in rendered
    assert "result_envelope" not in rendered
    assert "semantic_complete" not in rendered
