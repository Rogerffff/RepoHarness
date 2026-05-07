from __future__ import annotations

import pytest

from repo_harness.cli.main import main


def test_pre_verl_cli_hides_legacy_agent_evaluation_pilot(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "run-pre-verl-agent-evaluation-pilot" not in output


def test_pre_verl_cli_rejects_legacy_agent_evaluation_pilot(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["run-pre-verl-agent-evaluation-pilot"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert "run-pre-verl-agent-evaluation-pilot" in captured.err
