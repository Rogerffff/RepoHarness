from repo_harness.evaluation.runner import _requires_shell_command as runner_requires_shell
from repo_harness.workspace.adapter import _copy_tree
from repo_harness.workspace.adapter import _requires_shell_command as local_requires_shell
from repo_harness.workspace.docker_adapter import _requires_shell_command as docker_requires_shell


def test_requires_shell_for_env_assignment_before_bash() -> None:
    command = "REPOHARNESS_WORKSPACE=${PWD} bash -lc 'python -m pip install -e .[test]'"

    assert local_requires_shell(command)
    assert docker_requires_shell(command)
    assert runner_requires_shell(command)


def test_requires_shell_for_multiline_setup_command() -> None:
    command = "python -m pip install -e .\npython -m pytest -q"

    assert local_requires_shell(command)
    assert docker_requires_shell(command)
    assert runner_requires_shell(command)


def test_does_not_require_shell_for_plain_argv_command() -> None:
    command = "python -m pytest -q tests/test_example.py"

    assert not local_requires_shell(command)
    assert not docker_requires_shell(command)
    assert not runner_requires_shell(command)


def test_copy_tree_preserves_git_metadata_for_setuptools_scm(tmp_path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pkg.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (source / "__pycache__").mkdir()
    (source / "__pycache__" / "pkg.cpython-312.pyc").write_bytes(b"ignored")

    destination = tmp_path / "destination"
    _copy_tree(source, destination)

    assert (destination / ".git" / "HEAD").read_text(encoding="utf-8") == "ref: refs/heads/main\n"
    assert not (destination / "__pycache__").exists()
