import json
from pathlib import Path

import pytest

from repo_harness.export.manifest import sha256_file
from repo_harness.errors import ConfigError
from repo_harness.schema_versions import V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION
from repo_harness.v4_acceptance import (
    V4_RUN_SELECTION_QUERY_SPEC_VERSION,
    build_v4_acceptance_bundle,
    build_v4_acceptance_inputs,
    build_v4_acceptance_report,
    build_v4_run_selection_manifest,
)
from repo_harness.v4_stage1 import inspect_v4_acceptance, inspect_v4_acceptance_bundle, inspect_v4_inputs
from repo_harness.workspace.source_hash import compute_source_tree_hash


def test_v4_acceptance_builders_pass(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)

    assert "complete" in inspect_v4_inputs(inputs, assert_complete=True)
    report = build_v4_acceptance_report(
        acceptance_inputs=inputs,
        output=tmp_path / "acceptance" / "v4_acceptance_report.json",
        fail_if_output_exists=True,
    )
    assert "complete" in inspect_v4_acceptance(report, assert_complete=True)
    final_doc = tmp_path / "docs" / "final.md"
    final_doc.parent.mkdir(parents=True)
    final_doc.write_text("# Final\n", encoding="utf-8")
    bundle_path = report.parent / "acceptance_bundle_manifest.json"
    bundle = build_v4_acceptance_bundle(
        acceptance_report=report,
        output=bundle_path,
        documentation_refs=[final_doc],
        final_command_log=_write_final_command_log(tmp_path, report=report, bundle=bundle_path),
        fail_if_output_exists=True,
    )

    assert "immutable" in inspect_v4_acceptance_bundle(bundle, assert_immutable=True)


def test_v4_run_selection_rejects_report_artifact_path(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    payload = _read_json(query)
    payload["entries"][0]["run_ref"] = "docs/v4/evidence/task-source-freeze/task_freeze_manifest.json"
    _write_json(query, payload)

    with pytest.raises(ConfigError, match="报告类产物"):
        build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")


def test_v4_run_selection_refuses_default_overwrite(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    output = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")

    with pytest.raises(ConfigError, match="已存在"):
        build_v4_run_selection_manifest(query=query, output=output)


def test_v4_acceptance_inputs_refuses_default_overwrite(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)

    with pytest.raises(ConfigError, match="已存在"):
        _build_inputs(tmp_path, run_selection, command_log, output=inputs)


def test_v4_acceptance_bundle_refuses_default_overwrite(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)
    report = build_v4_acceptance_report(
        acceptance_inputs=inputs,
        output=tmp_path / "acceptance" / "v4_acceptance_report.json",
    )
    final_doc = tmp_path / "docs" / "final.md"
    final_doc.parent.mkdir(parents=True)
    final_doc.write_text("# Final\n", encoding="utf-8")
    bundle_path = report.parent / "acceptance_bundle_manifest.json"
    bundle = build_v4_acceptance_bundle(
        acceptance_report=report,
        output=bundle_path,
        documentation_refs=[final_doc],
        final_command_log=_write_final_command_log(tmp_path, report=report, bundle=bundle_path),
    )

    with pytest.raises(ConfigError, match="已存在"):
        build_v4_acceptance_bundle(
            acceptance_report=report,
            output=bundle,
            documentation_refs=[final_doc],
            final_command_log=_write_final_command_log(tmp_path, report=report, bundle=bundle),
        )


def test_v4_acceptance_inputs_reject_missing_contamination_scan(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)

    with pytest.raises(ConfigError, match="contamination_scan"):
        build_v4_acceptance_inputs(
            output=tmp_path / "v4_acceptance_inputs.json",
            pre_acceptance_docs=[Path("docs/v4/implementation-plan.md")],
            run_selection=run_selection,
            v2_acceptance=Path("runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json"),
            v3_acceptance=Path("runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json"),
            v3_acceptance_bundle=Path("runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json"),
            real_repository_regression=Path("docs/v4/evidence/regression/real_repository_regression_report.json"),
            swebench_like_regression=Path("docs/v4/evidence/regression/swebench_like_regression_report.json"),
            implementation_inputs=Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json"),
            rollout_queue=Path("docs/v4/evidence/rollout-orchestration"),
            lease_state=Path("docs/v4/evidence/rollout-orchestration"),
            retry_policy=Path("docs/v4/evidence/rollout-orchestration"),
            budget_control=Path("docs/v4/evidence/rollout-orchestration"),
            resource_locks=Path("docs/v4/evidence/rollout-orchestration"),
            resource_usage=Path("docs/v4/evidence/rollout-orchestration"),
            batch_resume=Path("docs/v4/evidence/rollout-orchestration"),
            run_selection_query=Path("docs/v4/evidence/rollout-orchestration/run_selection_query_report.json"),
            task_freeze=Path("docs/v4/evidence/task-source-freeze/task_freeze_manifest.json"),
            task_validity=Path("docs/v4/evidence/task-source-freeze/task_validity_report.json"),
            tool_contract=Path("docs/v4/evidence/tool-lifecycle"),
            tool_lifecycle=Path("docs/v4/evidence/tool-lifecycle"),
            agent_run_integration=Path("docs/v4/evidence/agent-run-integration"),
            trajectory_store=Path("docs/v4/evidence/agent-run-integration"),
            export_quality=Path("docs/v4/evidence/export-quality"),
            cards=Path("docs/v4/evidence/cards"),
            command_log=command_log,
        )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("empty_log", "至少包含一条记录"),
        ("missing_schema_version", "schema_version"),
        ("missing_argv", "缺少 argv"),
        ("missing_input_refs", "缺少 input_refs"),
        ("missing_output_refs", "缺少 output_refs"),
        ("sha_mismatch", "sha256 不匹配"),
    ],
)
def test_v4_acceptance_inputs_reject_invalid_command_log_lineage(
    tmp_path: Path,
    case: str,
    expected: str,
) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)

    if case == "empty_log":
        command_log.write_text("", encoding="utf-8")
    else:
        record = json.loads(command_log.read_text(encoding="utf-8"))
        if case == "missing_schema_version":
            record.pop("schema_version")
        elif case == "missing_argv":
            record.pop("argv")
        elif case == "missing_input_refs":
            record.pop("input_refs")
        elif case == "missing_output_refs":
            record.pop("output_refs")
        elif case == "sha_mismatch":
            record["input_refs"][0]["sha256"] = "0" * 64
        command_log.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ConfigError, match=expected):
        _build_inputs(tmp_path, run_selection, command_log)


def test_v4_acceptance_report_rejects_existing_acceptance_dir(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)
    acceptance_dir = tmp_path / "acceptance"
    acceptance_dir.mkdir()

    with pytest.raises(ConfigError, match="已存在"):
        build_v4_acceptance_report(
            acceptance_inputs=inputs,
            output=acceptance_dir / "v4_acceptance_report.json",
        )


def test_v4_acceptance_bundle_rejects_post_doc_as_report_input(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    final_doc = tmp_path / "final.md"
    final_doc.write_text("# Final\n", encoding="utf-8")
    inputs = _build_inputs(tmp_path, run_selection, command_log, pre_docs=[final_doc])
    report = build_v4_acceptance_report(
        acceptance_inputs=inputs,
        output=tmp_path / "acceptance" / "v4_acceptance_report.json",
        fail_if_output_exists=True,
    )
    bundle_path = report.parent / "acceptance_bundle_manifest.json"
    bundle = build_v4_acceptance_bundle(
        acceptance_report=report,
        output=bundle_path,
        documentation_refs=[final_doc],
        final_command_log=_write_final_command_log(tmp_path, report=report, bundle=bundle_path),
        fail_if_output_exists=True,
    )

    with pytest.raises(ConfigError, match="post-acceptance"):
        inspect_v4_acceptance_bundle(bundle, assert_immutable=True)


def test_v4_acceptance_inputs_reject_missing_regression_evidence(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)

    with pytest.raises(ConfigError, match="real_repository_regression"):
        build_v4_acceptance_inputs(
            output=tmp_path / "v4_acceptance_inputs.json",
            pre_acceptance_docs=[Path("docs/v4/implementation-plan.md")],
            run_selection=run_selection,
            v2_acceptance=Path("runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json"),
            v3_acceptance=Path("runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json"),
            v3_acceptance_bundle=Path("runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json"),
            implementation_inputs=Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json"),
            rollout_queue=Path("docs/v4/evidence/rollout-orchestration"),
            lease_state=Path("docs/v4/evidence/rollout-orchestration"),
            retry_policy=Path("docs/v4/evidence/rollout-orchestration"),
            budget_control=Path("docs/v4/evidence/rollout-orchestration"),
            resource_locks=Path("docs/v4/evidence/rollout-orchestration"),
            resource_usage=Path("docs/v4/evidence/rollout-orchestration"),
            batch_resume=Path("docs/v4/evidence/rollout-orchestration"),
            run_selection_query=Path("docs/v4/evidence/rollout-orchestration/run_selection_query_report.json"),
            task_freeze=Path("docs/v4/evidence/task-source-freeze/task_freeze_manifest.json"),
            task_validity=Path("docs/v4/evidence/task-source-freeze/task_validity_report.json"),
            tool_contract=Path("docs/v4/evidence/tool-lifecycle"),
            tool_lifecycle=Path("docs/v4/evidence/tool-lifecycle"),
            agent_run_integration=Path("docs/v4/evidence/agent-run-integration"),
            trajectory_store=Path("docs/v4/evidence/agent-run-integration"),
            export_quality=Path("docs/v4/evidence/export-quality"),
            cards=Path("docs/v4/evidence/cards"),
            contamination_scan=Path("docs/v4/evidence/cards/contamination_scan_report.json"),
            command_log=command_log,
        )


def test_v4_acceptance_rejects_regression_role_reusing_task_freeze_evidence(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)
    report = build_v4_acceptance_report(
        acceptance_inputs=inputs,
        output=tmp_path / "acceptance" / "v4_acceptance_report.json",
    )
    payload = _read_json(report)
    payload["role_evidence_refs"]["real_repository_regression"] = payload["role_evidence_refs"]["v4_pr_issue_task_freeze"]
    _write_json(report, payload)

    with pytest.raises(ConfigError, match="不能复用"):
        inspect_v4_acceptance(report, assert_complete=True)


def test_v4_acceptance_bundle_requires_final_command_log(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)
    report = build_v4_acceptance_report(
        acceptance_inputs=inputs,
        output=tmp_path / "acceptance" / "v4_acceptance_report.json",
    )
    final_doc = tmp_path / "docs" / "final.md"
    final_doc.parent.mkdir(parents=True)
    final_doc.write_text("# Final\n", encoding="utf-8")
    bundle = report.parent / "acceptance_bundle_manifest.json"
    _write_json(
        bundle,
        {
            "schema_version": "repo_harness_v4_acceptance_bundle_manifest_v0",
            "acceptance_report_ref": _file_ref_for_bundle(report, "v4_acceptance_report"),
            "acceptance_inputs_ref": _file_ref_for_bundle(inputs, "v4_acceptance_inputs"),
            "acceptance_command_log_ref": _file_ref_for_bundle(
                report.parent / "acceptance_command_log.jsonl",
                "acceptance_command_log",
            ),
            "documentation_refs": [_file_ref_for_bundle(final_doc, "post_acceptance_documentation")],
        },
    )

    with pytest.raises(ConfigError, match="final_acceptance_command_log_ref"):
        inspect_v4_acceptance_bundle(bundle, assert_immutable=True)


def test_v4_acceptance_bundle_rejects_incomplete_final_command_log(tmp_path: Path) -> None:
    query = _write_query(tmp_path)
    run_selection = build_v4_run_selection_manifest(query=query, output=tmp_path / "run_selection_manifest.json")
    command_log = _write_command_log(tmp_path)
    inputs = _build_inputs(tmp_path, run_selection, command_log)
    report = build_v4_acceptance_report(
        acceptance_inputs=inputs,
        output=tmp_path / "acceptance" / "v4_acceptance_report.json",
    )
    final_doc = tmp_path / "docs" / "final.md"
    final_doc.parent.mkdir(parents=True)
    final_doc.write_text("# Final\n", encoding="utf-8")
    bundle_path = report.parent / "acceptance_bundle_manifest.json"
    final_command_log = _write_final_command_log(
        tmp_path,
        report=report,
        bundle=bundle_path,
        omit_command="inspect-acceptance-bundle",
    )
    bundle = build_v4_acceptance_bundle(
        acceptance_report=report,
        output=bundle_path,
        documentation_refs=[final_doc],
        final_command_log=final_command_log,
    )

    with pytest.raises(ConfigError, match="inspect-acceptance-bundle"):
        inspect_v4_acceptance_bundle(bundle, assert_immutable=True)


def _build_inputs(
    tmp_path: Path,
    run_selection: Path,
    command_log: Path,
    *,
    pre_docs: list[Path] | None = None,
    output: Path | None = None,
) -> Path:
    return build_v4_acceptance_inputs(
        output=output or (tmp_path / "v4_acceptance_inputs.json"),
        pre_acceptance_docs=pre_docs or [Path("docs/v4/implementation-plan.md"), Path("docs/v4/review/implementation-plan-review.md")],
        run_selection=run_selection,
        v2_acceptance=Path("runs/v2-final-acceptance-20260501T223447Z/v2_acceptance_report.json"),
        v3_acceptance=Path("runs/v3-final-rerun-20260504T010000Z/acceptance/v3_acceptance_report.json"),
        v3_acceptance_bundle=Path("runs/v3-final-rerun-20260504T010000Z/acceptance/acceptance_bundle_manifest.json"),
        real_repository_regression=Path("docs/v4/evidence/regression/real_repository_regression_report.json"),
        swebench_like_regression=Path("docs/v4/evidence/regression/swebench_like_regression_report.json"),
        implementation_inputs=Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json"),
        rollout_queue=Path("docs/v4/evidence/rollout-orchestration"),
        lease_state=Path("docs/v4/evidence/rollout-orchestration"),
        retry_policy=Path("docs/v4/evidence/rollout-orchestration"),
        budget_control=Path("docs/v4/evidence/rollout-orchestration"),
        resource_locks=Path("docs/v4/evidence/rollout-orchestration"),
        resource_usage=Path("docs/v4/evidence/rollout-orchestration"),
        batch_resume=Path("docs/v4/evidence/rollout-orchestration"),
        run_selection_query=Path("docs/v4/evidence/rollout-orchestration/run_selection_query_report.json"),
        task_freeze=Path("docs/v4/evidence/task-source-freeze/task_freeze_manifest.json"),
        task_validity=Path("docs/v4/evidence/task-source-freeze/task_validity_report.json"),
        tool_contract=Path("docs/v4/evidence/tool-lifecycle"),
        tool_lifecycle=Path("docs/v4/evidence/tool-lifecycle"),
        agent_run_integration=Path("docs/v4/evidence/agent-run-integration"),
        trajectory_store=Path("docs/v4/evidence/agent-run-integration"),
        export_quality=Path("docs/v4/evidence/export-quality"),
        cards=Path("docs/v4/evidence/cards"),
        contamination_scan=Path("docs/v4/evidence/cards/contamination_scan_report.json"),
        command_log=command_log,
    )


def _write_query(tmp_path: Path) -> Path:
    implementation_inputs = Path("docs/v4/evidence/implementation-inputs/v4_implementation_input_manifest.json")
    entries = [
        ("v3_regression", "runs/v3-final-rerun-20260504T010000Z/acceptance"),
        ("v2_regression", "runs/v2-final-acceptance-20260501T223447Z"),
        ("real_repository_regression", "docs/v4/evidence/regression"),
        ("swebench_like_regression", "docs/v4/evidence/regression"),
        ("v4_pr_issue_task_freeze", "docs/v4/evidence/task-source-freeze"),
        ("v4_swebench_like_task_freeze", "docs/v4/evidence/task-source-freeze"),
        ("v4_rollout_orchestration", "docs/v4/evidence/rollout-orchestration"),
        ("v4_rollout_resume", "docs/v4/evidence/rollout-orchestration"),
        ("v4_agent_run_integration", "docs/v4/evidence/agent-run-integration"),
        ("v4_export_quality", "docs/v4/evidence/export-quality"),
        ("v4_tool_lifecycle_audit", "docs/v4/evidence/tool-lifecycle"),
        ("v4_cards", "docs/v4/evidence/cards"),
    ]
    query = {
        "schema_version": V4_RUN_SELECTION_QUERY_SPEC_VERSION,
        "selection_mode": "explicit",
        "latest_run_auto_selection": False,
        "query_predicate": "stage8_fixed_v4_final_acceptance_selection",
        "input_manifest_hash": sha256_file(implementation_inputs),
        "entries": [
            {"role": role, "run_ref": path, "selection_reason": "unit fixture selection"}
            for role, path in entries
        ],
    }
    query_path = tmp_path / "v4_query_spec.json"
    _write_json(query_path, query)
    return query_path


def _write_command_log(tmp_path: Path) -> Path:
    stdout = tmp_path / "pytest.stdout.txt"
    stderr = tmp_path / "pytest.stderr.txt"
    stdout.write_text("ok\n", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    record = {
        "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
        "command_name": "python-m-pytest",
        "argv": ["python", "-m", "pytest", "-q"],
        "cwd": Path.cwd().as_posix(),
        "input_refs": [_artifact_ref(Path("src"), "src")],
        "output_refs": [_artifact_ref(stdout, "stdout"), _artifact_ref(stderr, "stderr")],
        "exit_code": 0,
        "tool_or_cli_version": "repo-harness test",
        "started_at": "2026-05-04T00:00:00Z",
        "finished_at": "2026-05-04T00:00:01Z",
    }
    command_log = tmp_path / "pre_acceptance_command_log.jsonl"
    command_log.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return command_log


def _write_final_command_log(
    tmp_path: Path,
    *,
    report: Path,
    bundle: Path,
    omit_command: str | None = None,
) -> Path:
    stdout = tmp_path / "final.stdout.txt"
    stderr = tmp_path / "final.stderr.txt"
    stdout.write_text("ok\n", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    bundle_ref = bundle.as_posix()
    records = [
        {
            "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
            "command_name": "inspect-v4-acceptance",
            "argv": ["repo-harness", "inspect-v4-acceptance", report.as_posix(), "--assert-complete"],
            "cwd": Path.cwd().as_posix(),
            "input_refs": [_artifact_ref(report, "v4_acceptance_report")],
            "output_refs": [_artifact_ref(stdout, "inspect_v4_acceptance_stdout"), _artifact_ref(stderr, "inspect_v4_acceptance_stderr")],
            "exit_code": 0,
            "tool_or_cli_version": "repo-harness test",
            "started_at": "2026-05-04T00:00:01Z",
            "finished_at": "2026-05-04T00:00:02Z",
        },
        {
            "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
            "command_name": "build-v4-acceptance-bundle",
            "argv": ["repo-harness", "build-v4-acceptance-bundle", "--output", bundle_ref],
            "cwd": Path.cwd().as_posix(),
            "input_refs": [_artifact_ref(report, "v4_acceptance_report")],
            "output_refs": [_artifact_ref(stdout, "build_v4_bundle_stdout"), _artifact_ref(stderr, "build_v4_bundle_stderr")],
            "self_referential_output_paths": [bundle_ref],
            "self_referential_output_reason": "bundle manifest binds this final command log, so its hash is self-referential.",
            "exit_code": 0,
            "tool_or_cli_version": "repo-harness test",
            "started_at": "2026-05-04T00:00:02Z",
            "finished_at": "2026-05-04T00:00:03Z",
        },
        {
            "schema_version": V4_COMMAND_LOG_ENTRY_SCHEMA_VERSION,
            "command_name": "inspect-acceptance-bundle",
            "argv": ["repo-harness", "inspect-acceptance-bundle", bundle_ref, "--assert-immutable"],
            "cwd": Path.cwd().as_posix(),
            "input_refs": [],
            "output_refs": [_artifact_ref(stdout, "inspect_bundle_stdout"), _artifact_ref(stderr, "inspect_bundle_stderr")],
            "self_referential_input_paths": [bundle_ref],
            "self_referential_input_reason": "bundle manifest binds this final command log, so its hash is self-referential.",
            "exit_code": 0,
            "tool_or_cli_version": "repo-harness test",
            "started_at": "2026-05-04T00:00:03Z",
            "finished_at": "2026-05-04T00:00:04Z",
        },
    ]
    command_log = tmp_path / "final_acceptance_command_log.jsonl"
    command_log.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
            if record["command_name"] != omit_command
        ),
        encoding="utf-8",
    )
    return command_log


def _artifact_ref(path: Path, artifact_id: str) -> dict:
    return {
        "artifact_id": artifact_id,
        "relative_path": path.as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
        "redaction_status": "not_required",
        "retention_policy": "keep",
    }


def _file_ref_for_bundle(path: Path, category: str) -> dict:
    return {
        "path": path.as_posix(),
        "kind": "directory" if path.is_dir() else (path.suffix.lstrip(".") or "file"),
        "category": category,
        "sha256": compute_source_tree_hash(path) if path.is_dir() else sha256_file(path),
        "size_bytes": 0 if path.is_dir() else path.stat().st_size,
    }


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
