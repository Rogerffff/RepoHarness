from pathlib import Path

import yaml

from repo_harness.evaluation.experiment import load_experiment_config
from repo_harness.evaluation.schemas import ExperimentMinimums
from repo_harness.tasks import load_task


TASK_SET_CONFIG = Path("tests/fixtures/run_configs/v2/replay_experiment.yaml")
TASK_SET_THRESHOLDS = Path("tests/fixtures/run_configs/v2/task_set_thresholds.yaml")


def test_v2_replay_task_set_has_at_least_twenty_static_tasks():
    config = load_experiment_config(TASK_SET_CONFIG)

    assert len(config.tasks) >= 20
    loaded = [load_task(path) for path in config.tasks]
    assert len({task.runnable_task.task_id for task in loaded}) == len(loaded)
    assert sum(task.verifier_config.test_command == "pytest -q" for task in loaded) >= 20


def test_v2_replay_task_set_does_not_leak_evaluator_only_fields():
    config = load_experiment_config(TASK_SET_CONFIG)

    for path in config.tasks:
        loaded = load_task(path)
        visible_text = str(loaded.runnable_task.agent_visible_view())
        assert "fail_to_pass_tests" not in visible_text
        assert "pass_to_pass_tests" not in visible_text
        assert "gold_patch" not in visible_text
        assert "hidden_reference" not in visible_text
        assert "tests/fixtures/repos" not in visible_text


def test_v2_task_set_thresholds_cover_stage13_minimums():
    raw = yaml.safe_load(TASK_SET_THRESHOLDS.read_text(encoding="utf-8"))
    thresholds = ExperimentMinimums.model_validate(raw)

    assert thresholds.min_total_runs >= 20
    assert thresholds.min_task_count >= 20
    assert thresholds.min_agent_loop_runs >= 15
    assert thresholds.min_formal_final_verifier_runs >= 15
    assert thresholds.min_success_count >= 3
    assert thresholds.min_structured_skipped_runs >= 1
    assert thresholds.require_export_audit_clean is True
