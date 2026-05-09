import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from repo_harness.errors import WorkspaceError
from repo_harness.run_metadata.fingerprint import compute_file_sha256
from repo_harness.tasks import load_task
from repo_harness.workspace import materialize_source


def test_local_archive_materializes_and_records_source_facts(tmp_path: Path):
    archive = _archive_fixture_repo(tmp_path)
    sha = compute_file_sha256(archive)
    task_path = _archive_task(tmp_path, archive, sha)
    loaded = load_task(task_path)

    checkout = materialize_source(loaded.runnable_task, tmp_path / "checkout")

    assert (checkout.root / "calculator.py").is_file()
    assert checkout.facts.source_type == "local_archive"
    assert checkout.facts.source_archive_sha256 == sha
    assert checkout.facts.synthetic_base_id == "archive-fixture-v0"
    assert checkout.facts.source_tree_hash
    assert checkout.facts.checkout_path_status == "redacted"


def test_local_repository_dirty_snapshot_is_rejected_unless_allowed(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "repo-harness@example.test")
    _git(repo, "config", "user.name", "Repo Harness")
    (repo / "file.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    (repo / "file.txt").write_text("dirty\n", encoding="utf-8")
    task_path = _local_repo_task(tmp_path, repo, allow_dirty=False)
    loaded = load_task(task_path)

    with pytest.raises(WorkspaceError, match="dirty working tree"):
        materialize_source(loaded.runnable_task, tmp_path / "checkout")


def test_local_repository_source_requires_git_repository(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    task_path = _local_repo_task(tmp_path, repo, allow_dirty=False)
    loaded = load_task(task_path)

    with pytest.raises(WorkspaceError, match="Git repository"):
        materialize_source(loaded.runnable_task, tmp_path / "checkout")


def test_local_repository_clean_status_materializes(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "repo-harness@example.test")
    _git(repo, "config", "user.name", "Repo Harness")
    (repo / "file.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    task_path = _local_repo_task(tmp_path, repo, allow_dirty=False, working_tree_clean=True)
    loaded = load_task(task_path)

    checkout = materialize_source(loaded.runnable_task, tmp_path / "checkout")

    assert (checkout.root / "file.txt").read_text(encoding="utf-8") == "clean\n"
    assert checkout.facts.source_type == "local_repository"
    assert checkout.facts.working_tree_clean is True
    assert checkout.facts.dirty_snapshot_allowed is False
    assert not (checkout.root / ".git").exists()


def test_fixture_source_materialization_preserves_symlink_directories(tmp_path: Path):
    source = tmp_path / "fixture_with_symlink"
    source.mkdir()
    (source / "file.txt").write_text("content\n", encoding="utf-8")
    link = source / "loop"
    try:
        link.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is not supported in this environment: {exc}")
    task_path = tmp_path / "fixture_task.yaml"
    payload = _minimal_task_payload()
    payload["repo"] = source.as_posix()
    payload["repo_source_spec"] = {
        "source_type": "local_repository",
        "source_path": source.as_posix(),
        "base_commit": "fixed-symlink-fixture-v0",
        "synthetic_base_id": "fixed-symlink-fixture-v0",
        "decontamination_status": "manual_checked",
    }
    payload["base_commit"] = "fixed-symlink-fixture-v0"
    payload["expected_files"] = ["file.txt"]
    task_path.write_text(_dump_json_as_yaml(payload), encoding="utf-8")
    loaded = load_task(task_path)

    checkout = materialize_source(loaded.runnable_task, tmp_path / "checkout")

    assert (checkout.root / "file.txt").read_text(encoding="utf-8") == "content\n"
    assert (checkout.root / "loop").is_symlink()
    assert (checkout.root / "loop").readlink() == source
    assert sorted(path.name for path in checkout.root.iterdir()) == ["file.txt", "loop"]


def test_local_repository_dirty_status_declaration_cannot_override_git_status(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "repo-harness@example.test")
    _git(repo, "config", "user.name", "Repo Harness")
    (repo / "file.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    (repo / "file.txt").write_text("dirty\n", encoding="utf-8")
    task_path = _local_repo_task(tmp_path, repo, allow_dirty=False, working_tree_clean=True)
    loaded = load_task(task_path)

    with pytest.raises(WorkspaceError, match="working_tree_clean declaration"):
        materialize_source(loaded.runnable_task, tmp_path / "checkout")


def test_local_repository_commit_declaration_must_match_head(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "repo-harness@example.test")
    _git(repo, "config", "user.name", "Repo Harness")
    (repo / "file.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    task_path = _local_repo_task(
        tmp_path,
        repo,
        allow_dirty=False,
        current_commit="0" * 40,
    )
    loaded = load_task(task_path)

    with pytest.raises(WorkspaceError, match="current_commit"):
        materialize_source(loaded.runnable_task, tmp_path / "checkout")


def test_local_repository_dirty_snapshot_can_be_explicitly_allowed(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "repo-harness@example.test")
    _git(repo, "config", "user.name", "Repo Harness")
    (repo / "file.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    (repo / "file.txt").write_text("dirty\n", encoding="utf-8")
    task_path = _local_repo_task(tmp_path, repo, allow_dirty=True)
    loaded = load_task(task_path)

    checkout = materialize_source(loaded.runnable_task, tmp_path / "checkout")

    assert (checkout.root / "file.txt").read_text(encoding="utf-8") == "dirty\n"
    assert checkout.facts.source_type == "local_repository"
    assert checkout.facts.working_tree_clean is False
    assert checkout.facts.dirty_snapshot_allowed is True
    assert not (checkout.root / ".git").exists()


def test_public_snapshot_schema_validates_without_network_download(tmp_path: Path):
    task_path = tmp_path / "public_snapshot.yaml"
    payload = _minimal_task_payload()
    payload["repo"] = "https://example.com/repo.git"
    payload["repo_source_spec"] = {
        "source_type": "public_snapshot",
        "remote_url": "https://example.com/repo.git",
        "commit_sha": "abc123",
        "mirror_source": "preseeded-fixture",
        "archive_sha256": "0" * 64,
        "decontamination_status": "unknown",
    }
    task_path.write_text(_dump_json_as_yaml(payload), encoding="utf-8")

    loaded = load_task(task_path)

    assert loaded.runnable_task.repo_source_spec is not None
    assert loaded.definition.base_commit == "abc123"


def test_public_snapshot_without_predownloaded_archive_does_not_materialize(tmp_path: Path):
    task_path = tmp_path / "public_snapshot.yaml"
    payload = _minimal_task_payload()
    payload["repo"] = "https://example.com/repo.git"
    payload["repo_source_spec"] = {
        "source_type": "public_snapshot",
        "remote_url": "https://example.com/repo.git",
        "commit_sha": "abc123",
        "mirror_source": "preseeded-fixture",
        "archive_sha256": "0" * 64,
        "decontamination_status": "unknown",
    }
    task_path.write_text(_dump_json_as_yaml(payload), encoding="utf-8")
    loaded = load_task(task_path)

    with pytest.raises(WorkspaceError, match="does not download from network"):
        materialize_source(loaded.runnable_task, tmp_path / "checkout")


def _archive_fixture_repo(tmp_path: Path) -> Path:
    source = Path("tests/fixtures/repos/buggy_calculator")
    archive = tmp_path / "buggy_calculator.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                zip_file.write(path, Path("buggy_calculator") / path.relative_to(source))
    return archive


def _archive_task(tmp_path: Path, archive: Path, sha: str) -> Path:
    task_path = tmp_path / "archive_task.yaml"
    payload = _minimal_task_payload()
    payload["repo"] = archive.as_posix()
    payload["repo_source_spec"] = {
        "source_type": "local_archive",
        "archive_path": archive.as_posix(),
        "archive_sha256": sha,
        "expected_root_directory": "buggy_calculator",
        "synthetic_base_id": "archive-fixture-v0",
        "decontamination_status": "manual_checked",
    }
    payload["source_archive_sha256"] = sha
    payload["base_commit"] = None
    task_path.write_text(_dump_json_as_yaml(payload), encoding="utf-8")
    return task_path


def _local_repo_task(
    tmp_path: Path,
    repo: Path,
    *,
    allow_dirty: bool,
    working_tree_clean: bool | None = None,
    current_commit: str | None = None,
) -> Path:
    task_path = tmp_path / f"local_repo_{allow_dirty}_{working_tree_clean}_{current_commit}.yaml"
    payload = _minimal_task_payload()
    payload["repo"] = repo.as_posix()
    source_spec = {
        "source_type": "local_repository",
        "source_path": repo.as_posix(),
        "allow_dirty_snapshot": allow_dirty,
        "synthetic_base_id": "local-repo-v0",
        "decontamination_status": "unknown",
    }
    if working_tree_clean is not None:
        source_spec["working_tree_clean"] = working_tree_clean
    if current_commit is not None:
        source_spec["current_commit"] = current_commit
    payload["repo_source_spec"] = source_spec
    payload["expected_files"] = ["file.txt"]
    payload["test_command"] = "pytest -q"
    task_path.write_text(_dump_json_as_yaml(payload), encoding="utf-8")
    return task_path


def _minimal_task_payload() -> dict:
    return {
        "id": "materialized_task",
        "task_version": "materialized_task_v0",
        "dataset_name": "repo_harness_materialization",
        "source_kind": "repository_style_fixture",
        "created_at": "2026-05-01",
        "repo": "unused",
        "base_commit": "fixture",
        "issue": "Exercise materialized source handling.",
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
        "expected_files": ["calculator.py"],
        "visibility": {
            "issue": "model_visible",
            "expected_files": "model_visible",
            "fail_to_pass_tests": "verifier_only",
            "pass_to_pass_tests": "verifier_only",
            "gold_patch": "hidden_reference",
        },
    }


def _dump_json_as_yaml(payload: dict) -> str:
    # JSON is valid YAML and avoids a test dependency on YAML formatting details.
    return json.dumps(payload, indent=2)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", repo.as_posix(), *args], check=True, stdout=subprocess.PIPE)
