import json
import zipfile
from pathlib import Path

from repo_harness.evaluation.runner import run_task
from repo_harness.export import ExportPolicy
from repo_harness.export.exporter import export_sft_jsonl
from repo_harness.run_metadata.fingerprint import compute_file_sha256


ROOT = Path(__file__).resolve().parents[2]


def test_local_archive_materialization_smoke_records_source_facts_and_exports_metadata(
    tmp_path: Path,
):
    archive = _archive_fixture_repo(tmp_path)
    archive_sha = compute_file_sha256(archive)
    task_path = _archive_task(tmp_path, archive, archive_sha)

    run_dir = run_task(
        task_path,
        config_path=ROOT / "tests/fixtures/run_configs/replay_success.yaml",
        output_dir=tmp_path / "runs",
        run_id="archive-materialization-smoke",
    )

    run_config = _read_json(run_dir / "run_config_facts.json")
    run_metadata = _read_json(run_dir / "run_metadata.json")
    source_checkout = run_config["environment_fingerprint"]["workspace_execution"][
        "source_checkout"
    ]
    assert source_checkout["source_type"] == "local_archive"
    assert source_checkout["source_archive_sha256"] == archive_sha
    assert source_checkout["source_tree_hash"]
    assert source_checkout["decontamination_status"] == "source_checked"
    assert run_metadata["source_checkout"]["source_tree_hash"] == source_checkout["source_tree_hash"]
    assert run_metadata["environment_spec_hash"] == run_config["environment_fingerprint"][
        "environment_spec_hash"
    ]
    assert run_config["source_archive_sha256"] == archive_sha

    export_sft_jsonl(run_dir, policy=ExportPolicy(allow_oracle_feedback_training=True))
    exported = _read_jsonl(run_dir / "exports" / "sft.jsonl")
    assert exported
    metadata = exported[0]["metadata"]
    assert metadata["source_type"] == "local_archive"
    assert metadata["source_archive_sha256"] == archive_sha
    assert metadata["source_tree_hash"] == source_checkout["source_tree_hash"]
    assert metadata["decontamination_status"] == "source_checked"


def _archive_fixture_repo(tmp_path: Path) -> Path:
    source = ROOT / "tests/fixtures/repos/buggy_calculator"
    archive = tmp_path / "buggy_calculator.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                zip_file.write(path, Path("buggy_calculator") / path.relative_to(source))
    return archive


def _archive_task(tmp_path: Path, archive: Path, sha: str) -> Path:
    task_path = tmp_path / "archive_task.yaml"
    payload = _read_json_compatible_yaml(ROOT / "tests/fixtures/tasks/task_001.yaml")
    payload["id"] = "archive_task_001"
    payload["task_version"] = "archive_task_001_v0"
    payload["dataset_name"] = "repo_harness_materialization"
    payload["source_kind"] = "repository_style_fixture"
    payload["repo"] = archive.as_posix()
    payload["base_commit"] = None
    payload["source_archive_sha256"] = sha
    payload["repo_source_spec"] = {
        "source_type": "local_archive",
        "archive_path": archive.as_posix(),
        "archive_sha256": sha,
        "expected_root_directory": "buggy_calculator",
        "synthetic_base_id": "archive-fixture-v0",
        "decontamination_status": "source_checked",
    }
    task_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return task_path


def _read_json_compatible_yaml(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
