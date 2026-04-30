import json
from pathlib import Path

from repo_harness.export.exporter import export_preference_jsonl, export_rl_jsonl
from repo_harness.export.exporter import _sanitize_text


def test_preference_export_writes_skipped_manifest_when_not_enough_runs(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "run_one"
    run_dir.mkdir(parents=True)
    (run_dir / "metrics.json").write_text('{"run_outcome": "success"}\n', encoding="utf-8")
    (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (run_dir / "baseline.json").write_text('{"task_id": "task_001"}\n', encoding="utf-8")

    output = export_preference_jsonl(runs_dir)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "preference_skipped.json"
    assert payload["filter_status"] == "skipped"
    assert payload["reason"] == "not_enough_runs_for_same_task"


def test_export_sanitizes_provider_credentials():
    text = (
        "Authorization: Bearer sk-testsecret123456789 "
        "api_key=abc123456789 password: hunter2 token='tok_123456789'"
    )

    sanitized = _sanitize_text(text)

    assert "sk-testsecret" not in sanitized
    assert "abc123456789" not in sanitized
    assert "hunter2" not in sanitized
    assert "tok_123456789" not in sanitized
    assert sanitized.count("<REDACTED_CREDENTIAL>") >= 3


def test_rl_export_without_formal_final_verifier_is_invalid_for_training(tmp_path: Path):
    run_dir = _minimal_run(tmp_path / "run_missing_formal", task_id="task_001")

    output = export_rl_jsonl(run_dir)
    record = _read_jsonl(output)[0]

    assert record["invalid_for_training"] is True
    assert record["invalid_reason"] == "missing_formal_final_verifier"
    assert record["payload"]["reward_metadata"]["formal_final_verifier"] is False


def test_preference_export_pairs_equal_reward_when_outcome_differs(tmp_path: Path):
    runs_dir = tmp_path / "runs"
    _minimal_run(
        runs_dir / "run_success",
        task_id="task_001",
        reward=0.5,
        run_outcome="success",
        final_verifier_status="accepted",
        include_formal_verifier=True,
    )
    _minimal_run(
        runs_dir / "run_failed",
        task_id="task_001",
        reward=0.5,
        run_outcome="failed",
        final_verifier_status="failed",
        include_formal_verifier=True,
    )

    output = export_preference_jsonl(runs_dir)
    record = _read_jsonl(output)[0]

    assert output.name == "preference.jsonl"
    assert record["payload"]["chosen"]["source_run_id"] == "run_success"
    assert record["payload"]["rejected"]["source_run_id"] == "run_failed"


def _minimal_run(
    run_dir: Path,
    *,
    task_id: str,
    reward: float = 0.0,
    run_outcome: str = "success",
    final_verifier_status: str = "accepted",
    include_formal_verifier: bool = False,
) -> Path:
    run_dir.mkdir(parents=True)
    (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "baseline.json").write_text(
        json.dumps({"task_id": task_id}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "run_outcome": run_outcome,
                "final_verifier_status": final_verifier_status,
                "interaction_efficiency": {"final_verifier_mode": "strict_patch_replay"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "reward.json").write_text(
        json.dumps({"final_reward": reward, "reward_version": "repo_harness_reward_v0"}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "final.patch").write_text("diff --git a/demo.py b/demo.py\n", encoding="utf-8")
    if include_formal_verifier:
        (run_dir / "verifier.json").write_text(
            json.dumps({"verifier_stage": "final"}) + "\n",
            encoding="utf-8",
        )
    return run_dir


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
