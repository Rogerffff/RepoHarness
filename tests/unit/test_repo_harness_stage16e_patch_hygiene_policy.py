from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState, RunWorkspace
from repo_harness.workspace.adapter import LocalWorkspaceAdapter
from repo_harness.workspace.patch_hygiene import (
    PatchHygieneError,
    build_patch_hygiene_report,
    filter_patch_text,
    parse_name_status_z,
)


def _block(path: str, old: str = "old", new: str = "new") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


def test_patch_hygiene_filters_diagnostic_and_dependency_paths() -> None:
    patch = (
        _block("src/pkg.py")
        + _block("debug_probe.py")
        + _block("pkg/node_modules/left-pad/index.js")
        + _block("tests/test_pkg.py")
    )
    structured = parse_name_status_z(
        "M\0src/pkg.py\0A\0debug_probe.py\0A\0pkg/node_modules/left-pad/index.js\0M\0tests/test_pkg.py\0"
    )

    result = filter_patch_text(patch, structured_diff_facts=structured)
    report = build_patch_hygiene_report(patch_result=result, raw_diff_text=patch, cleaned_diff_text=result.cleaned_patch_text)

    assert "src/pkg.py" in result.cleaned_patch_text
    assert "debug_probe.py" not in result.cleaned_patch_text
    assert "node_modules" not in result.cleaned_patch_text
    assert "tests/test_pkg.py" in result.cleaned_patch_text
    assert report["filtered_file_count"] == 2
    assert report["flagged_file_count"] == 1
    assert report["only_filtered_changes"] is False


def test_patch_hygiene_public_report_redacts_runtime_private_path() -> None:
    patch = _block("runtime_private/secret.py")
    structured = parse_name_status_z("A\0runtime_private/secret.py\0")
    result = filter_patch_text(patch, structured_diff_facts=structured)
    report = build_patch_hygiene_report(patch_result=result, raw_diff_text=patch, cleaned_diff_text="")

    assert report["only_filtered_changes"] is True
    filtered = report["filtered_files"][0]
    assert "path" not in filtered
    assert filtered["path_category"] == "runtime_private_or_harness_path"
    assert "path_sha256" in filtered
    assert "runtime_private/secret.py" not in json.dumps(filtered)


@pytest.mark.parametrize(
    "path",
    [
        "runtime-private/secret.py",
        "Runtime-Private/secret.py",
        "RuntimePrivate/secret.py",
        ".repo-harness-runtime/secret.py",
        ".repo_harness_env_overlay/workspace/bin/python",
        "repo-harness-run/task.yaml",
    ],
)
def test_patch_hygiene_filters_and_redacts_runtime_private_variants(path: str) -> None:
    patch = _block(path)
    structured = parse_name_status_z(f"A\0{path}\0")
    result = filter_patch_text(patch, structured_diff_facts=structured)
    report = build_patch_hygiene_report(patch_result=result, raw_diff_text=patch, cleaned_diff_text="")
    filtered = report["filtered_files"][0]

    assert result.cleaned_patch_text == ""
    assert filtered["path_category"] == "runtime_private_or_harness_path"
    assert "path" not in filtered
    assert path not in json.dumps(filtered)


@pytest.mark.parametrize(
    "path",
    [
        "venv/x.py",
        "env/x.py",
        "dist/x.py",
        "build/x.py",
        "pkg/venv/x.py",
        "pkg/env/x.py",
        "pkg/dist/x.py",
        "pkg/build/x.py",
    ],
)
def test_patch_hygiene_filters_dependency_and_build_artifact_dirs(path: str) -> None:
    patch = _block(path)
    structured = parse_name_status_z(f"A\0{path}\0")
    result = filter_patch_text(patch, structured_diff_facts=structured)

    assert result.cleaned_patch_text == ""
    assert result.only_filtered_changes is True


@pytest.mark.parametrize(
    "path",
    [
        "gold_patch.py",
        "hidden_verifier.py",
        "reward_metadata.json",
        "provider_secret.txt",
        "fail_to_pass.py",
    ],
)
def test_patch_hygiene_filters_sensitive_marker_filenames(path: str) -> None:
    patch = _block(path)
    structured = parse_name_status_z(f"A\0{path}\0")
    result = filter_patch_text(patch, structured_diff_facts=structured)

    assert result.cleaned_patch_text == ""
    assert result.only_filtered_changes is True


def test_patch_hygiene_public_report_redacts_sensitive_marker_directory() -> None:
    patch = _block("goldpatch/secret.py")
    structured = parse_name_status_z("A\0goldpatch/secret.py\0")
    result = filter_patch_text(patch, structured_diff_facts=structured)
    report = build_patch_hygiene_report(patch_result=result, raw_diff_text=patch, cleaned_diff_text="")
    filtered = report["filtered_files"][0]

    assert "path" not in filtered
    assert filtered["path_category"] == "evaluator_or_hidden_marker_path"
    assert "goldpatch/secret.py" not in json.dumps(filtered)


@pytest.mark.parametrize("path", ["src/env/config.py", "src/build/plugin.py"])
def test_patch_hygiene_does_not_filter_legitimate_nested_source_dirs(path: str) -> None:
    patch = _block(path)
    structured = parse_name_status_z(f"M\0{path}\0")
    result = filter_patch_text(patch, structured_diff_facts=structured)

    assert path in result.cleaned_patch_text
    assert result.filtered_file_count == 0


def test_patch_hygiene_requires_structured_diff_facts_to_match_patch() -> None:
    patch = _block("src/pkg.py")
    structured = parse_name_status_z("M\0src/other.py\0")

    with pytest.raises(PatchHygieneError, match="structured_diff_facts_mismatch"):
        filter_patch_text(patch, structured_diff_facts=structured)


def test_patch_hygiene_handles_space_and_git_quoted_paths() -> None:
    patch = (
        "diff --git a/src/name with space.py b/src/name with space.py\n"
        "index 1111111..2222222 100644\n"
        "--- a/src/name with space.py\t\n"
        "+++ b/src/name with space.py\t\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        'diff --git "a/src/tab\\tname.py" "b/src/tab\\tname.py"\n'
        "index 1111111..2222222 100644\n"
        '--- "a/src/tab\\tname.py"\n'
        '+++ "b/src/tab\\tname.py"\n'
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    structured = parse_name_status_z("M\0src/name with space.py\0M\0src/tab\tname.py\0")

    result = filter_patch_text(patch, structured_diff_facts=structured)
    report = build_patch_hygiene_report(
        patch_result=result,
        raw_diff_text=patch,
        cleaned_diff_text=result.cleaned_patch_text,
    )

    assert "src/name with space.py" in result.cleaned_patch_text
    assert "tab\\tname.py" not in result.cleaned_patch_text
    assert report["filtered_file_count"] == 1
    assert report["filtered_files"][0]["reason"] == "unsafe_patch_path"
    assert "src/tab\tname.py" not in json.dumps(report["filtered_files"], ensure_ascii=False)


def test_patch_hygiene_header_fallback_handles_space_path_without_body_paths() -> None:
    patch = "diff --git a/src/name with space.py b/src/name with space.py\nnew file mode 100644\n"
    structured = parse_name_status_z("A\0src/name with space.py\0")

    result = filter_patch_text(patch, structured_diff_facts=structured)

    assert "src/name with space.py" in result.cleaned_patch_text
    assert result.filtered_file_count == 0


@pytest.mark.parametrize(
    ("old_path", "header_old"),
    [
        ("src/old.py", "a/src/old.py"),
        ("src/old name.py", "a/src/old name.py"),
    ],
)
def test_patch_hygiene_header_fallback_handles_mixed_quoted_rename(
    old_path: str,
    header_old: str,
) -> None:
    patch = (
        f'diff --git {header_old} "b/src/tab\\tnew.py"\n'
        "similarity index 100%\n"
        f"rename from {old_path}\n"
        'rename to "src/tab\\tnew.py"\n'
    )
    structured = parse_name_status_z(f"R100\0{old_path}\0src/tab\tnew.py\0")

    result = filter_patch_text(patch, structured_diff_facts=structured)
    report = build_patch_hygiene_report(
        patch_result=result,
        raw_diff_text=patch,
        cleaned_diff_text=result.cleaned_patch_text,
    )

    assert result.cleaned_patch_text == ""
    assert report["only_filtered_changes"] is True
    assert report["filtered_file_count"] == 1
    assert report["filtered_files"][0]["reason"] == "unsafe_patch_path"
    assert "src/tab\tnew.py" not in json.dumps(report["filtered_files"], ensure_ascii=False)


def test_capture_final_patch_writes_cleaned_patch_and_private_raw_patch(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "workspace"
    workspace.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=workspace, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "unit@example.com"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Unit"], cwd=workspace, check=True)
    (workspace / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "src.py"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=workspace, check=True, stdout=subprocess.PIPE)

    adapter = LocalWorkspaceAdapter(run_id="stage16e", run_dir=run_dir)
    with RunRecorder("stage16e", run_dir, task_id="task") as recorder:
        snapshot = adapter.create_agent_start_snapshot(workspace, None, recorder)
        (workspace / "src.py").write_text("VALUE = 2\n", encoding="utf-8")
        (workspace / "debug_probe.py").write_text("print('debug')\n", encoding="utf-8")
        run_workspace = RunWorkspace(
            run_id="stage16e",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(),
            agent_start_snapshot=snapshot,
            agent_diff_base=snapshot,
        )
        capture = adapter.capture_final_patch(run_workspace, recorder=recorder)

    report = json.loads((run_dir / "final_patch_hygiene_report.json").read_text(encoding="utf-8"))
    assert "src.py" in capture.patch_text
    assert "debug_probe.py" not in capture.patch_text
    assert capture.raw_patch_path is not None
    assert "debug_probe.py" in capture.raw_patch_path.read_text(encoding="utf-8")
    assert report["filtered_file_count"] == 1
    assert capture.patch_stats["added_lines"] == 1
    assert capture.patch_stats["patch_hygiene"]["raw_added_lines"] == 2
