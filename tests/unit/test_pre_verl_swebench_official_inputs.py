import hashlib
import json

from scripts.pre_verl.build_swebench_official_inputs import (
    main,
    _patch_content_leak_findings,
    _patch_modified_files,
    _public_safe_hygiene_filtered_files,
    _strip_patch_paths,
    _temporary_artifact_paths,
    _test_like_paths,
)


def _write_hygiene_report(run_dir, *, cleaned_patch: str, raw_patch: str, only_filtered: bool = False) -> None:
    run_dir.joinpath("final_patch_hygiene_report.json").write_text(
        json.dumps(
            {
                "schema_version": "repo_harness_stage16e_patch_hygiene_report_v0",
                "patch_hygiene_policy_version": "repo_harness_stage16e_patch_hygiene_policy_v0",
                "status": "filtered_changes" if only_filtered else "passed",
                "cleaned_patch_sha256": hashlib.sha256(cleaned_patch.encode("utf-8")).hexdigest(),
                "raw_patch_sha256": hashlib.sha256(raw_patch.encode("utf-8")).hexdigest(),
                "filtered_file_count": 1 if only_filtered else 0,
                "flagged_file_count": 0,
                "only_filtered_changes": only_filtered,
                "filtered_files": [
                    {
                        "action": "exclude",
                        "reason": "dependency_cache_or_runtime_private_path",
                        "path_category": "runtime_private_or_harness_path",
                        "path_sha256": "abc",
                        "basename_redacted": "<redacted>.py",
                    }
                ]
                if only_filtered
                else [],
                "flagged_files": [],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_strip_patch_paths_removes_test_file_blocks_only() -> None:
    patch = """diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1 @@
-old
+new
diff --git a/tests/test_source.py b/tests/test_source.py
index 3333333..4444444 100644
--- a/tests/test_source.py
+++ b/tests/test_source.py
@@ -1 +1 @@
-assert old
+assert new
"""

    stripped = _strip_patch_paths(patch, {"tests/test_source.py"})

    assert _patch_modified_files(stripped) == ["pkg/source.py"]
    assert "tests/test_source.py" not in stripped
    assert "pkg/source.py" in stripped


def test_test_like_paths_covers_common_test_names() -> None:
    paths = [
        "src/pkg/source.py",
        "tests/test_source.py",
        "testing/helpers.py",
        "pkg/foo_test.py",
        "pkg/conftest.py",
        "pkg/widget.spec.ts",
    ]

    assert _test_like_paths(paths) == [
        "tests/test_source.py",
        "testing/helpers.py",
        "pkg/foo_test.py",
        "pkg/conftest.py",
        "pkg/widget.spec.ts",
    ]


def test_temporary_artifact_paths_cover_diagnostic_patch_leftovers() -> None:
    paths = [
        "pkg/source.py",
        "patch.txt",
        "notes/patch.txt",
        "tmp/check_probe.py",
        "tmp/nested/trace.txt",
        ".repo_harness_tmp/fix.py",
        ".repo_harness_tmp/nested/repro_case.py",
        "pkg/source.py.orig",
        "pkg/source.py.rej",
        "classes.dot",
        "reports/classes.dot",
        "diffbug.fits",
        "astropy/io/fits/tests/data/example.fits",
        "new_format_float.py",
        "manage.py",
    ]

    assert _temporary_artifact_paths(paths) == [
        "patch.txt",
        "tmp/check_probe.py",
        "tmp/nested/trace.txt",
        ".repo_harness_tmp/fix.py",
        ".repo_harness_tmp/nested/repro_case.py",
        "pkg/source.py.orig",
        "pkg/source.py.rej",
        "classes.dot",
        "diffbug.fits",
        "new_format_float.py",
    ]


def test_quoted_diff_header_with_multiline_probe_leftover_is_stripped() -> None:
    weird_path = (
        "{result!r})\\n"
        "    # Simple check: result should not contain bare spaces in math mode\\n"
        "    print(f"
    )
    patch = f"""diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1 @@
-old
+new
diff --git "a/{weird_path}" "b/{weird_path}"
new file mode 100644
index 0000000..e69de29
"""

    assert _patch_modified_files(patch) == ["pkg/source.py", weird_path]
    assert _temporary_artifact_paths([weird_path]) == [weird_path]

    stripped = _strip_patch_paths(patch, {weird_path})

    assert _patch_modified_files(stripped) == ["pkg/source.py"]
    assert weird_path not in stripped


def test_strip_patch_paths_removes_top_level_tmp_probe_blocks() -> None:
    patch = """diff --git a/lib/source.py b/lib/source.py
index 1111111..2222222 100644
--- a/lib/source.py
+++ b/lib/source.py
@@ -1 +1 @@
-old
+new
diff --git a/tmp/debug_case.py b/tmp/debug_case.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/tmp/debug_case.py
@@ -0,0 +1 @@
+print("probe")
"""

    tmp_paths = _temporary_artifact_paths(_patch_modified_files(patch))
    stripped = _strip_patch_paths(patch, set(tmp_paths))

    assert tmp_paths == ["tmp/debug_case.py"]
    assert _patch_modified_files(stripped) == ["lib/source.py"]
    assert "tmp/debug_case.py" not in stripped


def test_strip_patch_paths_removes_repo_harness_tmp_probe_blocks() -> None:
    patch = """diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1 @@
-old
+new
diff --git a/.repo_harness_tmp/fix.py b/.repo_harness_tmp/fix.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/.repo_harness_tmp/fix.py
@@ -0,0 +1 @@
+print("probe")
"""

    tmp_paths = _temporary_artifact_paths(_patch_modified_files(patch))
    stripped = _strip_patch_paths(patch, set(tmp_paths))

    assert tmp_paths == [".repo_harness_tmp/fix.py"]
    assert _patch_modified_files(stripped) == ["pkg/source.py"]
    assert ".repo_harness_tmp/fix.py" not in stripped
    assert "pkg/source.py" in stripped


def test_patch_content_leak_findings_block_hidden_markers_and_local_paths() -> None:
    patch = """diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1,3 @@
 value = 1
+print("FAIL_TO_PASS")
+print("/Users/example/secret")
"""

    findings = _patch_content_leak_findings(patch)

    assert {item["reason"] for item in findings} == {
        "hidden_selector_marker",
        "absolute_local_path",
    }


def test_builder_excludes_prediction_with_content_leak(tmp_path, monkeypatch) -> None:
    dataset = tmp_path / "dataset.jsonl"
    run_summary = tmp_path / "runs.jsonl"
    run_dir = tmp_path / "run"
    output = tmp_path / "out"
    run_dir.mkdir()
    dataset.write_text('{"instance_id":"task-1","problem_statement":"x"}\n', encoding="utf-8")
    run_summary.write_text(
        '{"index":1,"instance_id":"task-1","status":"command_success","run_id":"run-1","run_dir":"'
        + run_dir.as_posix()
        + '"}\n',
        encoding="utf-8",
    )
    (run_dir / "final.patch").write_text(
        """diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1,2 @@
 value = 1
+value = "gold_patch"
""",
        encoding="utf-8",
    )
    _write_hygiene_report(
        run_dir,
        cleaned_patch=(run_dir / "final.patch").read_text(encoding="utf-8"),
        raw_patch=(run_dir / "final.patch").read_text(encoding="utf-8"),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_swebench_official_inputs.py",
            "--dataset-jsonl",
            dataset.as_posix(),
            "--run-summary-jsonl",
            run_summary.as_posix(),
            "--output-dir",
            output.as_posix(),
            "--stage-id",
            "stage16d",
            "--window-id",
            "unit",
            "--model-name-or-path",
            "model",
            "--official-run-id",
            "official-unit",
            "--official-report-dir",
            (tmp_path / "reports").as_posix(),
            "--start-index",
            "1",
            "--end-index",
            "1",
        ],
    )

    assert main() == 0

    manifest = (output / "official_prediction_manifest.json").read_text(encoding="utf-8")
    predictions = (output / "repoharness_stage16d_unit_predictions.jsonl").read_text(encoding="utf-8")
    assert '"excluded_prediction_count": 1' in manifest
    assert "prediction_patch_content_leak_blocked" in manifest
    assert predictions == ""
    assert "runtime_private_operational_artifact" in manifest


def test_builder_excludes_prediction_without_hygiene_report(tmp_path, monkeypatch) -> None:
    dataset = tmp_path / "dataset.jsonl"
    run_summary = tmp_path / "runs.jsonl"
    run_dir = tmp_path / "run"
    output = tmp_path / "out"
    run_dir.mkdir()
    dataset.write_text('{"instance_id":"task-1","problem_statement":"x"}\n', encoding="utf-8")
    run_summary.write_text(
        '{"index":1,"instance_id":"task-1","status":"command_success","run_id":"run-1","run_dir":"'
        + run_dir.as_posix()
        + '"}\n',
        encoding="utf-8",
    )
    (run_dir / "final.patch").write_text(
        """diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1 @@
-old
+new
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_swebench_official_inputs.py",
            "--dataset-jsonl",
            dataset.as_posix(),
            "--run-summary-jsonl",
            run_summary.as_posix(),
            "--output-dir",
            output.as_posix(),
            "--stage-id",
            "stage16e",
            "--window-id",
            "unit",
            "--model-name-or-path",
            "model",
            "--official-run-id",
            "official-unit",
            "--official-report-dir",
            (tmp_path / "reports").as_posix(),
            "--start-index",
            "1",
            "--end-index",
            "1",
        ],
    )

    assert main() == 0

    manifest = (output / "official_prediction_manifest.json").read_text(encoding="utf-8")
    predictions = (output / "repoharness_stage16e_unit_predictions.jsonl").read_text(encoding="utf-8")
    assert "final_patch_hygiene_report_missing" in manifest
    assert predictions == ""


def test_builder_uses_final_patch_hygiene_report(tmp_path, monkeypatch) -> None:
    dataset = tmp_path / "dataset.jsonl"
    run_summary = tmp_path / "runs.jsonl"
    run_dir = tmp_path / "run"
    output = tmp_path / "out"
    run_dir.mkdir()
    dataset.write_text('{"instance_id":"task-1","problem_statement":"x"}\n', encoding="utf-8")
    run_summary.write_text(
        '{"index":1,"instance_id":"task-1","status":"command_success","run_id":"run-1","run_dir":"'
        + run_dir.as_posix()
        + '"}\n',
        encoding="utf-8",
    )
    cleaned_patch = """diff --git a/pkg/source.py b/pkg/source.py
index 1111111..2222222 100644
--- a/pkg/source.py
+++ b/pkg/source.py
@@ -1 +1 @@
-old
+new
"""
    raw_patch = cleaned_patch + """diff --git a/runtime_private/secret.py b/runtime_private/secret.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/runtime_private/secret.py
@@ -0,0 +1 @@
+secret
"""
    (run_dir / "final.patch").write_text(cleaned_patch, encoding="utf-8")
    _write_hygiene_report(run_dir, cleaned_patch=cleaned_patch, raw_patch=raw_patch)
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_swebench_official_inputs.py",
            "--dataset-jsonl",
            dataset.as_posix(),
            "--run-summary-jsonl",
            run_summary.as_posix(),
            "--output-dir",
            output.as_posix(),
            "--stage-id",
            "stage16e",
            "--window-id",
            "unit",
            "--model-name-or-path",
            "model",
            "--official-run-id",
            "official-unit",
            "--official-report-dir",
            (tmp_path / "reports").as_posix(),
            "--start-index",
            "1",
            "--end-index",
            "1",
        ],
    )

    assert main() == 0

    manifest = json.loads((output / "official_prediction_manifest.json").read_text(encoding="utf-8"))
    record = manifest["records"][0]
    assert record["final_patch_hygiene_report_status"] == "present"
    assert record["official_prediction_uses_cleaned_patch"] is True
    assert record["cleaned_patch_sha256"] == record["patch_sha256"]


def test_hygiene_filtered_files_projection_is_public_safe() -> None:
    public = _public_safe_hygiene_filtered_files(
        [
            {
                "action": "exclude",
                "reason": "dependency_cache_or_runtime_private_path",
                "path": "runtime_private/secret.py",
            }
        ]
    )

    assert "path" not in public[0]
    assert public[0]["path_category"] == "runtime_private_or_harness_path"
    assert "path_sha256" in public[0]


def test_builder_excludes_hygiene_only_filtered_patch(tmp_path, monkeypatch) -> None:
    dataset = tmp_path / "dataset.jsonl"
    run_summary = tmp_path / "runs.jsonl"
    run_dir = tmp_path / "run"
    output = tmp_path / "out"
    run_dir.mkdir()
    dataset.write_text('{"instance_id":"task-1","problem_statement":"x"}\n', encoding="utf-8")
    run_summary.write_text(
        '{"index":1,"instance_id":"task-1","status":"command_success","run_id":"run-1","run_dir":"'
        + run_dir.as_posix()
        + '"}\n',
        encoding="utf-8",
    )
    raw_patch = """diff --git a/runtime_private/secret.py b/runtime_private/secret.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/runtime_private/secret.py
@@ -0,0 +1 @@
+secret
"""
    (run_dir / "final.patch").write_text("", encoding="utf-8")
    _write_hygiene_report(run_dir, cleaned_patch="", raw_patch=raw_patch, only_filtered=True)
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_swebench_official_inputs.py",
            "--dataset-jsonl",
            dataset.as_posix(),
            "--run-summary-jsonl",
            run_summary.as_posix(),
            "--output-dir",
            output.as_posix(),
            "--stage-id",
            "stage16e",
            "--window-id",
            "unit",
            "--model-name-or-path",
            "model",
            "--official-run-id",
            "official-unit",
            "--official-report-dir",
            (tmp_path / "reports").as_posix(),
            "--start-index",
            "1",
            "--end-index",
            "1",
        ],
    )

    assert main() == 0

    manifest = (output / "official_prediction_manifest.json").read_text(encoding="utf-8")
    predictions = (output / "repoharness_stage16e_unit_predictions.jsonl").read_text(encoding="utf-8")
    assert "patch_hygiene_only_filtered_changes" in manifest
    assert predictions == ""
