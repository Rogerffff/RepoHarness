import json
from pathlib import Path

import pytest

from repo_harness.cli.main import main
from repo_harness.errors import ConfigError
from repo_harness.export.manifest import sha256_file
from repo_harness.schema_versions import (
    V4_BASELINE_CHECK_REPORT_VERSION,
    V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
)
from repo_harness import v4_implementation_inputs as v4_inputs
from repo_harness.v4_implementation_inputs import (
    build_v4_implementation_inputs,
    inspect_v4_implementation_inputs,
)
from repo_harness.workspace.source_hash import compute_source_tree_hash


def test_build_and_inspect_v4_implementation_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = _write_stage0_feasibility_fixture(tmp_path)
    monkeypatch.setattr(v4_inputs, "_build_baseline_check_report", lambda **_: _baseline_report())

    manifest = build_v4_implementation_inputs(
        pr_issue_run=paths["pr_run"],
        public_swebench_run=paths["public_run"],
        output_dir=tmp_path / "out",
        v2_acceptance=tmp_path / "v2.json",
        v3_acceptance=tmp_path / "v3.json",
        v3_acceptance_bundle=tmp_path / "v3_bundle.json",
        fail_if_output_exists=True,
    )

    output = inspect_v4_implementation_inputs(manifest, assert_complete=True)
    assert "Inspect V4 implementation inputs: complete" in output
    payload = _read_json(manifest)
    assert payload["accepted_counting_allowed"] is False
    assert (tmp_path / "out" / "v4_feasibility_input_binding.json").exists()


def test_v4_implementation_inputs_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    paths = _write_stage0_feasibility_fixture(tmp_path)
    monkeypatch.setattr(v4_inputs, "_build_baseline_check_report", lambda **_: _baseline_report())
    out = tmp_path / "cli_out"

    assert main(
        [
            "build-v4-implementation-inputs",
            "--pr-issue-run",
            str(paths["pr_run"]),
            "--public-swebench-run",
            str(paths["public_run"]),
            "--output-dir",
            str(out),
            "--v2-acceptance",
            str(tmp_path / "v2.json"),
            "--v3-acceptance",
            str(tmp_path / "v3.json"),
            "--v3-acceptance-bundle",
            str(tmp_path / "v3_bundle.json"),
            "--fail-if-output-exists",
        ]
    ) == 0
    assert "V4 implementation input manifest" in capsys.readouterr().out
    assert main(["inspect-v4-implementation-inputs", str(out / "v4_implementation_input_manifest.json"), "--assert-complete"]) == 0
    assert "Inspect V4 implementation inputs: complete" in capsys.readouterr().out


def test_inspect_v4_implementation_inputs_rejects_missing_run_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _built_manifest(tmp_path, monkeypatch)
    binding_path = manifest.parent / "v4_feasibility_input_binding.json"
    binding = _read_json(binding_path)
    binding["sources"][0]["run_path"] = str(tmp_path / "missing-pr-run")
    _write_json(binding_path, binding)
    _refresh_manifest_ref(manifest, "feasibility_input_binding_ref", binding_path)

    with pytest.raises(ConfigError, match="feasibility run path 不存在"):
        inspect_v4_implementation_inputs(manifest, assert_complete=True)


def test_inspect_v4_implementation_inputs_rejects_sha_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _built_manifest(tmp_path, monkeypatch)
    binding_path = manifest.parent / "v4_feasibility_input_binding.json"
    binding = _read_json(binding_path)
    binding["sources"][0]["manifest_refs"][0]["sha256"] = "0" * 64
    _write_json(binding_path, binding)
    _refresh_manifest_ref(manifest, "feasibility_input_binding_ref", binding_path)

    with pytest.raises(ConfigError, match="sha256 不匹配"):
        inspect_v4_implementation_inputs(manifest, assert_complete=True)


@pytest.mark.parametrize(
    "polluted_value, expected",
    [
        ("https://github.com/example/project/pull/123", "pull_request_url"),
        ("https://github.com/example/project/issues/123", "issue_url"),
        ("pull request #123", "pull_request_number"),
        ("issue #123", "issue_number"),
        ("gold_patch", "gold_patch"),
        ("0123456789abcdef0123456789abcdef01234567", "fix_commit_hash"),
        ("hidden_selector", "hidden_selector"),
        ("https://claude.ai/share/example-session", "claude.ai"),
        ("AI session URL", "AI session URL"),
        ("pull_request_body", "pull_request_body"),
        ("pull_request_diff", "pull_request_diff"),
        ("provider_raw_response", "provider_raw_response"),
        ("verifier_raw_output", "verifier_raw_output"),
    ],
)
def test_inspect_v4_implementation_inputs_rejects_adapter_visible_contamination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    polluted_value: str,
    expected: str,
) -> None:
    manifest = _built_manifest(tmp_path, monkeypatch)
    pr_run = tmp_path / "pr_issue_run"
    adapter_input = pr_run / "adapter_visible/task.json"
    payload = _read_json(adapter_input)
    payload["problem_statement"] = polluted_value
    _write_json(adapter_input, payload)

    adapter_manifest = pr_run / "manifests/adapter_visible_task_freeze_manifest.json"
    adapter_payload = _read_json(adapter_manifest)
    adapter_payload["records"][0]["adapter_visible_sha256"] = sha256_file(adapter_input)
    _write_json(adapter_manifest, adapter_payload)
    _refresh_binding_manifest_ref(
        manifest=manifest,
        target_path=adapter_manifest,
        category="adapter_visible_task_freeze_manifest",
    )

    with pytest.raises(ConfigError, match=expected):
        inspect_v4_implementation_inputs(manifest, assert_complete=True)


def test_inspect_v4_implementation_inputs_rejects_count_mismatch_without_downgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _built_manifest(tmp_path, monkeypatch)
    pr_freeze = tmp_path / "pr_issue_run/manifests/pr_issue_task_freeze_readiness_report.json"
    payload = _read_json(pr_freeze)
    payload["candidate_count"] = 2
    _write_json(pr_freeze, payload)
    _refresh_binding_manifest_ref(
        manifest=manifest,
        target_path=pr_freeze,
        category="pr_issue_freeze_readiness_report",
    )

    with pytest.raises(ConfigError, match="candidate_count 与 candidate_rows 数量不一致"):
        inspect_v4_implementation_inputs(manifest, assert_complete=True)


def test_inspect_v4_implementation_inputs_rejects_denylist_sha_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = _built_manifest(tmp_path, monkeypatch)
    payload = _read_json(manifest)
    payload["contamination_denylist_sha256"] = "0" * 64
    _write_json(manifest, payload)

    with pytest.raises(ConfigError, match="contamination_denylist_sha256 不匹配"):
        inspect_v4_implementation_inputs(manifest, assert_complete=True)


def _built_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    paths = _write_stage0_feasibility_fixture(tmp_path)
    monkeypatch.setattr(v4_inputs, "_build_baseline_check_report", lambda **_: _baseline_report())
    return build_v4_implementation_inputs(
        pr_issue_run=paths["pr_run"],
        public_swebench_run=paths["public_run"],
        output_dir=tmp_path / "out",
        v2_acceptance=tmp_path / "v2.json",
        v3_acceptance=tmp_path / "v3.json",
        v3_acceptance_bundle=tmp_path / "v3_bundle.json",
    )


def _write_stage0_feasibility_fixture(tmp_path: Path) -> dict[str, Path]:
    pr_run = tmp_path / "pr_issue_run"
    public_run = tmp_path / "public_swebench_run"
    pr_manifests = pr_run / "manifests"
    public_manifests = public_run / "manifests"
    adapter_dir = pr_run / "adapter_visible"
    adapter_dir.mkdir(parents=True)
    pr_manifests.mkdir(parents=True)
    (public_run / "baseline").mkdir(parents=True)
    (public_run / "freeze").mkdir(parents=True)
    (public_run / "inventory").mkdir(parents=True)
    public_manifests.mkdir(parents=True)

    adapter_input = adapter_dir / "task.json"
    _write_json(
        adapter_input,
        {
            "schema_version": "v4.adapter_visible_task.0",
            "adapter_visible_task_id": "v4_example_task",
            "problem_statement": "A safe public symptom statement.",
            "repository": "example/project",
            "source_ref_id": "source:v4_example_task",
        },
    )
    _write_json(
        pr_manifests / "adapter_visible_task_freeze_manifest.json",
        {
            "schema_version": "v4.adapter_visible_task_freeze_manifest.0",
            "task_count": 1,
            "records": [
                {
                    "adapter_visible_path": "adapter_visible/task.json",
                    "adapter_visible_sha256": sha256_file(adapter_input),
                    "adapter_visible_task_id": "v4_example_task",
                }
            ],
        },
    )
    _write_json(
        pr_manifests / "pr_issue_task_freeze_readiness_report.json",
        {
            "schema_version": "v4.pr_issue_task_freeze_readiness_report.0",
            "candidate_count": 1,
            "freeze_ready_count": 1,
            "accepted_counting_allowed": False,
            "candidate_rows": [{"candidate_id": "example_1", "final_status": "freeze_ready"}],
        },
    )
    for name in (
        "docker_feasibility_summary_report.json",
        "flaky_probe_report.json",
        "training_export_boundary_report.json",
        "adapter_visible_denylist_scan_report.json",
        "source_archive_manifest.json",
    ):
        _write_json(pr_manifests / name, {"schema_version": f"fixture.{name}", "status": "passed"})

    _write_json(public_manifests / "public_swebench_initial_probe_result_manifest.json", {"schema_version": "fixture.public_probe"})
    _write_json(public_run / "baseline/public_swebench_initial_probe_result.json", {"schema_version": "fixture.public_result"})
    _write_json(
        public_run / "freeze/public_swebench_initial_freeze_readiness_report.json",
        {
            "schema_version": "repo_harness_v4_public_swebench_freeze_readiness_report_v0",
            "candidate_count": 1,
            "freeze_ready_public_swebench_like_count": 1,
            "task_readiness": [
                {
                    "candidate_id": "django__django-11283",
                    "final_status": "gold_patch_probe_resolved",
                }
            ],
        },
    )
    _write_json(
        public_run / "inventory/public_swebench_initial_probe_selection.json",
        {
            "schema_version": "fixture.public_selection",
            "selector_metadata_is_audit_only": True,
            "patch_sha256": "1" * 64,
        },
    )
    return {"pr_run": pr_run, "public_run": public_run}


def _baseline_report() -> dict:
    commands = v4_inputs._baseline_commands(  # noqa: SLF001 - test fixture mirrors public Stage 0 contract.
        baseline_commit="f38cb93",
        v3_closure_commit="17b1b95",
        v2_acceptance=Path("v2.json"),
        v3_acceptance=Path("v3.json"),
        v3_acceptance_bundle=Path("v3_bundle.json"),
    )
    keys = (
        "v4_baseline_commit_is_ancestor",
        "v3_closure_commit_is_ancestor",
        "docs_v4_clean_before_stage0_outputs",
        "compileall_src",
        "pytest",
        "v2_acceptance",
        "v3_acceptance",
        "v3_acceptance_bundle",
        "docker_amd64_probe",
    )
    return {
        "schema_version": V4_BASELINE_CHECK_REPORT_VERSION,
        "generated_at": "2026-05-04T00:00:00Z",
        "baseline_commit": "f38cb93",
        "v3_closure_commit": "17b1b95",
        "live_checks_run": True,
        "required_commands": [command["command_name"] for command in commands],
        "command_results": [
            {
                "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
                "command_name": command["command_name"],
                "argv": command["argv"],
                "cwd": ".",
                "input_paths": [],
                "input_sha256": {},
                "output_paths": [],
                "output_sha256": {},
                "exit_code": 0,
                "tool_or_cli_version": "repo-harness fixture",
                "started_at": "2026-05-04T00:00:00Z",
                "finished_at": "2026-05-04T00:00:00Z",
                "structured_skip_reason": None,
                "structured_failure_reason": None,
            }
            for command in commands
        ],
        "baseline_status": {key: "passed" for key in keys},
        "architecture_compatibility_risk": None,
    }


def _refresh_binding_manifest_ref(*, manifest: Path, target_path: Path, category: str) -> None:
    binding_path = manifest.parent / "v4_feasibility_input_binding.json"
    binding = _read_json(binding_path)
    replacement = _file_ref(target_path, category)
    for source in binding["sources"]:
        if source.get("primary_input_manifest_ref", {}).get("path") == replacement["path"]:
            source["primary_input_manifest_ref"] = replacement
        if source.get("adapter_visible_manifest_ref", {}).get("path") == replacement["path"]:
            source["adapter_visible_manifest_ref"] = replacement
        for index, ref in enumerate(source.get("manifest_refs", [])):
            if ref.get("path") == replacement["path"]:
                source["manifest_refs"][index] = replacement
    _write_json(binding_path, binding)
    _refresh_manifest_ref(manifest, "feasibility_input_binding_ref", binding_path)


def _refresh_manifest_ref(manifest: Path, key: str, target_path: Path) -> None:
    payload = _read_json(manifest)
    payload[key] = _file_ref(target_path, payload[key]["category"])
    _write_json(manifest, payload)


def _file_ref(path: Path, category: str) -> dict:
    return {
        "path": path.resolve().as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
        "model_visible": False,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
