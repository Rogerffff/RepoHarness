from repo_harness.cli.main import main


def test_main_without_command_prints_help(capsys):
    exit_code = main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "RepoHarness" in captured.out
    assert "validate-task" in captured.out
