from pathlib import Path

import pytest
import yaml

from repo_harness.cli.main import main
from repo_harness.errors import TaskValidationError
from repo_harness.model_client import ReplayScript
from repo_harness.tasks import load_task


VALID_TASKS = [
    "task_001.yaml",
    "task_002.yaml",
    "task_003_create_file.yaml",
    "task_security_probe.yaml",
    "task_invalid_baseline.yaml",
    "task_flaky.yaml",
]


def task_path(name: str) -> Path:
    return Path("tests/fixtures/tasks") / name


@pytest.mark.parametrize("name", VALID_TASKS)
def test_fixture_tasks_load_and_normalize_repo_paths(name: str):
    loaded = load_task(task_path(name))

    assert loaded.runnable_task.task_id == loaded.definition.id
    assert loaded.verifier_config.test_command == loaded.definition.test_command
    assert Path(loaded.definition.repo).is_absolute()
    assert "tests/fixtures/repos" in loaded.definition.repo
    assert loaded.runnable_task.agent_visible_view()["issue_statement"] == loaded.definition.issue


def test_task_adapter_is_independent_of_current_working_directory(tmp_path: Path, monkeypatch):
    absolute_task_path = task_path("task_001.yaml").resolve()
    monkeypatch.chdir(tmp_path)

    loaded = load_task(absolute_task_path)

    assert loaded.runnable_task.task_id == "task_001"
    assert Path(loaded.definition.repo).exists()


@pytest.mark.parametrize("name", VALID_TASKS)
def test_fixture_agent_visible_view_does_not_leak_evaluator_only_fields(name: str):
    loaded = load_task(task_path(name))
    visible_text = str(loaded.runnable_task.agent_visible_view())

    assert "gold_patch" not in visible_text
    assert "fail_to_pass_tests" not in visible_text
    assert "pass_to_pass_tests" not in visible_text
    assert "decontamination" not in visible_text
    assert "overlap_check_notes" not in visible_text
    assert "repo_source" not in visible_text
    assert "tests/fixtures/repos" not in visible_text


def test_bad_visibility_task_is_rejected():
    with pytest.raises(TaskValidationError, match="gold_patch"):
        load_task(task_path("task_bad_visibility.yaml"))


def test_task_repo_cannot_escape_fixture_root(tmp_path: Path):
    fixture_tasks = tmp_path / "tests" / "fixtures" / "tasks"
    fixture_repos = tmp_path / "tests" / "fixtures" / "repos"
    fixture_tasks.mkdir(parents=True)
    fixture_repos.mkdir(parents=True)
    task = fixture_tasks / "escape.yaml"
    task.write_text(
        """
id: escape
task_version: escape_v0
dataset_name: repo_harness_micro
source_kind: micro_repo_fixture
created_at: "2026-04-30"
repo: ../../..
issue: "bad"
test_command: "pytest -q"
timeouts:
  timeout_sec: 60
environment:
  execution_image: "python:3.12-slim"
  python_version: "3.12"
  package_manager: pip
visibility:
  issue: model_visible
  expected_files: model_visible
  fail_to_pass_tests: verifier_only
  pass_to_pass_tests: verifier_only
  gold_patch: hidden_reference
""",
        encoding="utf-8",
    )

    with pytest.raises(TaskValidationError, match="fixture 根目录"):
        load_task(task)


@pytest.mark.parametrize(
    ("field", "command", "match"),
    [
        ("test_command", "python -c \"print('unsafe')\"", "test_command"),
        ("test_command", "pytest -q; printf unsafe", "shell"),
        ("test_command", "pytest --basetemp=../../outside -q", "pytest"),
        ("setup_command", "python - <<'PY'\nprint('unsafe')\nPY", "setup_command"),
        ("setup_command", "python setup.py; printf unsafe", "shell"),
        ("setup_command", "python -m pip install definitely-not-safe", "setup_command"),
    ],
)
def test_task_adapter_rejects_unsafe_task_commands(
    tmp_path: Path,
    field: str,
    command: str,
    match: str,
):
    fixture_tasks = tmp_path / "tests" / "fixtures" / "tasks"
    fixture_repos = tmp_path / "tests" / "fixtures" / "repos"
    repo = fixture_repos / "repo"
    fixture_tasks.mkdir(parents=True)
    repo.mkdir(parents=True)
    task = fixture_tasks / "unsafe_command.yaml"
    payload = _minimal_task_payload("../repos/repo")
    payload[field] = command
    task.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(TaskValidationError, match=match):
        load_task(task)


def test_task_adapter_allows_conservative_setup_command(tmp_path: Path):
    fixture_tasks = tmp_path / "tests" / "fixtures" / "tasks"
    fixture_repos = tmp_path / "tests" / "fixtures" / "repos"
    repo = fixture_repos / "repo"
    fixture_tasks.mkdir(parents=True)
    repo.mkdir(parents=True)
    (repo / "setup_task.py").write_text("print('setup')\n", encoding="utf-8")
    task = fixture_tasks / "safe_setup.yaml"
    payload = _minimal_task_payload("../repos/repo")
    payload["setup_command"] = "python setup_task.py"
    task.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    loaded = load_task(task)

    assert loaded.runnable_task.setup_command == "python setup_task.py"


def test_validate_task_cli_succeeds_for_valid_task(capsys):
    exit_code = main(["validate-task", str(task_path("task_001.yaml"))])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "任务校验通过：task_001" in captured.out
    assert "测试命令：pytest -q" in captured.out


def test_validate_task_cli_fails_for_invalid_task(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["validate-task", str(task_path("task_bad_visibility.yaml"))])

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "任务校验失败" in captured.err


@pytest.mark.parametrize(
    "name",
    [
        "task_001_success.yaml",
        "task_001_failure.yaml",
        "security_negative.yaml",
        "task_003_create_file_success.yaml",
        "task_001_bash_pytest.yaml",
        "task_001_schema_error.yaml",
        "task_001_unknown_tool.yaml",
    ],
)
def test_replay_fixtures_are_static_and_schema_valid(name: str):
    replay_path = Path("tests/fixtures/replays") / name
    script = ReplayScript.model_validate(yaml.safe_load(replay_path.read_text(encoding="utf-8")))
    visible = script.model_visible_steps()

    assert script.steps
    assert "expected_outcome" not in str(visible)


def _minimal_task_payload(repo: str) -> dict:
    return {
        "id": "command_task",
        "task_version": "command_task_v0",
        "dataset_name": "repo_harness_micro",
        "source_kind": "micro_repo_fixture",
        "created_at": "2026-04-30",
        "repo": repo,
        "issue": "Exercise task command validation.",
        "setup_command": None,
        "test_command": "pytest -q",
        "timeouts": {
            "setup_timeout_sec": 60,
            "test_timeout_sec": 30,
            "agent_timeout_sec": 120,
            "final_verifier_timeout_sec": 60,
        },
        "environment": {
            "execution_image": "python:3.12-slim",
            "python_version": "3.12",
            "package_manager": "pip",
        },
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
    }
