from pathlib import Path

from repo_harness.evaluation import ResolvedVerifierPlan
from repo_harness.reward import compute_reward_metadata
from repo_harness.tasks import load_task
from repo_harness.trajectory import RunRecorder
from repo_harness.verifier import PytestVerifier
from repo_harness.workspace import LocalWorkspaceAdapter


def make_plan(loaded, plan_id="plan_001"):
    return ResolvedVerifierPlan(
        verifier_config=loaded.verifier_config,
        initial_fail_to_pass_tests=loaded.verifier_config.fail_to_pass_tests,
        initial_pass_to_pass_tests=loaded.verifier_config.pass_to_pass_tests,
        parser_confidence=0.9,
        resolved_verifier_plan_id=plan_id,
    )


def test_verifier_baseline_and_final_acceptance_on_micro_repo(tmp_path: Path):
    loaded = load_task("tests/fixtures/tasks/task_001.yaml")
    run_dir = tmp_path / "run_verifier"
    with RunRecorder("run_verifier", run_dir, task_id=loaded.runnable_task.task_id) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_verifier", run_dir=run_dir)
        verifier = PytestVerifier(adapter)
        source = adapter.create_source_checkout(loaded.runnable_task)
        dependency_state = adapter.capture_dependency_state(strategy="none")
        setup = adapter.create_setup_workspace(source)
        baseline = verifier.run_baseline(setup, loaded.verifier_config, recorder)
        feedback = verifier.run_feedback(setup, make_plan(loaded), recorder)
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            recorder=recorder,
        )
        original = adapter.read_text(run_workspace.workspace_path, "calculator.py")
        adapter.write_text(
            run_workspace.workspace_path,
            "calculator.py",
            original.replace(
                "def divide(left: int, right: int) -> float:\n    return left / right\n",
                "def divide(left: int, right: int) -> float:\n"
                "    if right == 0:\n"
                "        raise ValueError(\"division by zero\")\n"
                "    return left / right\n",
            ),
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        verification = adapter.create_verification_workspace(
            source_checkout=source,
            dependency_state=dependency_state,
            final_patch_path=capture.patch_path,
            recorder=recorder,
        )
        final = verifier.run_final(verification, make_plan(loaded), recorder)
        reward = compute_reward_metadata(
            final,
            patch_stats={"added_lines": capture.added_lines, "removed_lines": capture.removed_lines},
        )

    assert baseline.accepted is False
    assert baseline.verifier_stage == "baseline"
    assert baseline.raw_output_ref is not None
    assert feedback.verifier_stage == "feedback"
    assert baseline.fail_to_pass == {"passed": 0, "total": 1}
    assert baseline.pass_to_pass == {"passed": 2, "total": 2}
    assert final.accepted is True
    assert final.verifier_stage == "final"
    assert final.raw_output_ref is not None
    assert final.fail_to_pass == {"passed": 1, "total": 1}
    assert reward.invalid_for_training is False


def test_verifier_detects_pass_to_pass_regression(tmp_path: Path):
    loaded = load_task("tests/fixtures/tasks/task_001.yaml")
    run_dir = tmp_path / "run_regression"
    with RunRecorder("run_regression", run_dir, task_id=loaded.runnable_task.task_id) as recorder:
        adapter = LocalWorkspaceAdapter(run_id="run_regression", run_dir=run_dir)
        verifier = PytestVerifier(adapter)
        source = adapter.create_source_checkout(loaded.runnable_task)
        dependency_state = adapter.capture_dependency_state(strategy="none")
        run_workspace = adapter.create_agent_workspace(
            task=loaded.runnable_task,
            source_checkout=source,
            dependency_state=dependency_state,
            recorder=recorder,
        )
        adapter.write_text(
            run_workspace.workspace_path,
            "calculator.py",
            "def add(left: int, right: int) -> int:\n    return 0\n\n"
            "def divide(left: int, right: int) -> float:\n"
            "    if right == 0:\n"
            "        raise ValueError(\"division by zero\")\n"
            "    return left / right\n",
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)
        verification = adapter.create_verification_workspace(
            source_checkout=source,
            dependency_state=dependency_state,
            final_patch_path=capture.patch_path,
            recorder=recorder,
        )
        final = verifier.run_final(verification, make_plan(loaded), recorder)

    assert final.accepted is False
    assert final.error_type == "regression_detected"
