import hashlib
import json
from pathlib import Path

import pytest

from repo_harness.stage16g2_file_surface import inspect_stage16g2b_file_mutation
from repo_harness.permissions import PermissionContext
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolRegistry, build_tool
from repo_harness.tools.schemas import ToolCall
from repo_harness.trajectory import RunRecorder
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace
from scripts.pre_verl.build_stage16g2b_file_mutation import write_stage16g2b_reports


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _refresh_summary_digest(output_dir: Path, filename: str, digest_field: str) -> None:
    summary_path = output_dir / "stage16g2b_acceptance_summary.json"
    summary = json.loads(summary_path.read_text())
    summary[digest_field] = _sha256_file(output_dir / filename)
    _write_json(summary_path, summary)


def _tool_context(tmp_path: Path) -> ToolExecutionContext:
    run_dir = tmp_path / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("stage16g2b-tool-test", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(run_id="stage16g2b-tool-test", run_dir=run_dir)
    return ToolExecutionContext(
        run_id="stage16g2b-tool-test",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="stage16g2b-tool-test",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )


def _execute(context: ToolExecutionContext, tool_name: str, arguments: dict[str, object]):
    executor = ToolExecutor()
    return executor.execute(
        ToolCall(
            tool_call_id=f"call_{tool_name}",
            tool_name=tool_name,
            arguments=arguments,
            turn=1,
        ),
        context,
    )


def test_write_file_create_and_overwrite_are_behavior_enabled(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)

    create = _execute(
        context,
        "write_file",
        {"path": "notes.txt", "content": "first\n", "mode": "create"},
    )
    assert create.status == "ok"
    assert create.typed["operation_facts"][0]["result_kind"] == "file_created"
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "first\n"

    overwrite = _execute(
        context,
        "write_file",
        {
            "path": "notes.txt",
            "content": "second\n",
            "mode": "overwrite",
            "expected_content_hash": _hash_text("first\n"),
        },
    )
    assert overwrite.status == "ok"
    assert overwrite.typed["operation_facts"][0]["result_kind"] == "file_overwritten"
    assert overwrite.typed["policy_loss_candidate"] is False
    assert context.file_state_cache["notes.txt"] == _hash_text("second\n")
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "second\n"


def test_write_file_stale_hash_is_denied_without_mutation(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "notes.txt").write_text("original\n", encoding="utf-8")

    result = _execute(
        context,
        "write_file",
        {
            "path": "notes.txt",
            "content": "changed\n",
            "mode": "overwrite",
            "expected_content_hash": "wrong",
        },
    )

    assert result.status == "denied"
    assert result.error_type == "stage16g2b_file_mutation_denied"
    assert result.typed["reason_code"] == "stale_file_state"
    assert result.typed["repository_mutation_performed"] is False
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "original\n"


def test_apply_patch_applies_batch_file_operations_after_preflight(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "a.txt").write_text("alpha\n", encoding="utf-8")
    (workspace / "delete_me.txt").write_text("delete\n", encoding="utf-8")
    (workspace / "old_name.txt").write_text("move\n", encoding="utf-8")

    result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "replace_text",
                    "path": "a.txt",
                    "old_text": "alpha",
                    "new_text": "beta",
                    "expected_content_hash": _hash_text("alpha\n"),
                },
                {"op": "write_file", "path": "created.txt", "content": "new\n", "mode": "create"},
                {
                    "op": "delete_file",
                    "path": "delete_me.txt",
                    "expected_content_hash": _hash_text("delete\n"),
                    "reason": "Remove obsolete text fixture after the migration.",
                },
                {
                    "op": "move_file",
                    "source_path": "old_name.txt",
                    "target_path": "new_name.txt",
                    "expected_source_hash": _hash_text("move\n"),
                    "reason": "Rename the fixture to match the new module name.",
                },
                {"op": "mkdir", "path": "pkg/subpkg"},
            ]
        },
    )

    assert result.status == "ok"
    assert result.typed["operation_count"] == 5
    facts = {fact["op"]: fact for fact in result.typed["operation_facts"]}
    assert facts["delete_file"]["reason"] == "Remove obsolete text fixture after the migration."
    assert facts["move_file"]["reason"] == "Rename the fixture to match the new module name."
    assert (workspace / "a.txt").read_text(encoding="utf-8") == "beta\n"
    assert (workspace / "created.txt").read_text(encoding="utf-8") == "new\n"
    assert not (workspace / "delete_me.txt").exists()
    assert not (workspace / "old_name.txt").exists()
    assert (workspace / "new_name.txt").read_text(encoding="utf-8") == "move\n"
    assert (workspace / "pkg" / "subpkg").is_dir()


def test_apply_patch_unary_delete_and_unary_move_are_cleanly_expressible(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "delete_one.txt").write_text("obsolete\n", encoding="utf-8")
    (workspace / "move_one.txt").write_text("renamed\n", encoding="utf-8")

    delete_result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "delete_file",
                    "path": "delete_one.txt",
                    "expected_content_hash": _hash_text("obsolete\n"),
                    "reason": "Remove obsolete single-file fixture.",
                }
            ]
        },
    )
    move_result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "move_file",
                    "source_path": "move_one.txt",
                    "target_path": "moved_one.txt",
                    "expected_source_hash": _hash_text("renamed\n"),
                    "reason": "Rename one file to the new public name.",
                }
            ]
        },
    )

    assert delete_result.status == "ok"
    assert delete_result.typed["operation_facts"][0]["op"] == "delete_file"
    assert move_result.status == "ok"
    assert move_result.typed["operation_facts"][0]["op"] == "move_file"
    assert not (workspace / "delete_one.txt").exists()
    assert not (workspace / "move_one.txt").exists()
    assert (workspace / "moved_one.txt").read_text(encoding="utf-8") == "renamed\n"


def test_apply_patch_preflight_failure_is_atomic(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "a.txt").write_text("alpha\n", encoding="utf-8")
    (workspace / "b.txt").write_text("bravo\n", encoding="utf-8")

    result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "replace_text",
                    "path": "a.txt",
                    "old_text": "alpha",
                    "new_text": "beta",
                    "expected_content_hash": _hash_text("alpha\n"),
                },
                {
                    "op": "delete_file",
                    "path": "b.txt",
                    "expected_content_hash": "wrong",
                    "reason": "Remove stale file.",
                },
            ]
        },
    )

    assert result.status == "denied"
    assert result.typed["reason_code"] == "stale_file_state"
    assert result.typed["repository_mutation_performed"] is False
    assert (workspace / "a.txt").read_text(encoding="utf-8") == "alpha\n"
    assert (workspace / "b.txt").read_text(encoding="utf-8") == "bravo\n"


def test_file_mutation_rejects_hidden_absolute_binary_and_symlink_targets(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "binary.dat").write_bytes(b"\x00\x01")
    (workspace / "non_utf8.txt").write_bytes(b"\xff\xfe")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (workspace / "link.txt").symlink_to(outside)

    absolute = _execute(
        context,
        "write_file",
        {"path": workspace.as_posix(), "content": "x", "mode": "create"},
    )
    hidden = _execute(
        context,
        "write_file",
        {"path": ".git/config", "content": "x", "mode": "create"},
    )
    binary = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "delete_file",
                    "path": "binary.dat",
                    "expected_content_hash": "unused",
                    "reason": "Remove generated binary.",
                }
            ]
        },
    )
    non_utf8 = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "delete_file",
                    "path": "non_utf8.txt",
                    "expected_content_hash": "unused",
                    "reason": "Remove generated non UTF-8 file.",
                }
            ]
        },
    )
    symlink = _execute(
        context,
        "write_file",
        {
            "path": "link.txt",
            "content": "changed\n",
            "mode": "overwrite",
            "expected_content_hash": _hash_text("outside\n"),
        },
    )

    assert absolute.status == "denied"
    assert absolute.typed["reason_code"] == "absolute_path_denied"
    assert hidden.status == "denied"
    assert hidden.typed["reason_code"] == "model_hidden_path_denied"
    assert not (workspace / ".git" / "config").exists()
    assert binary.status == "denied"
    assert binary.typed["reason_code"] == "binary_file_denied"
    assert (workspace / "binary.dat").read_bytes() == b"\x00\x01"
    assert non_utf8.status == "denied"
    assert non_utf8.typed["reason_code"] == "non_utf8_file_denied"
    assert (workspace / "non_utf8.txt").read_bytes() == b"\xff\xfe"
    assert symlink.status == "denied"
    assert symlink.typed["reason_code"] == "symlink_not_mutable"
    assert outside.read_text(encoding="utf-8") == "outside\n"


@pytest.mark.parametrize(
    "path",
    [
        "runtime-private/x.py",
        "RuntimePrivate/x.py",
        ".repo-harness-runtime/x.py",
        "repo-harness-run/x.py",
        ".repo-harness-env-overlay/x.py",
        "gold_patch.py",
        "gold-patch.py",
        "test_patch.py",
        "hiddenVerifier.txt",
        "official-verifier.log",
        "FAIL_TO_PASS.txt",
        "PASS_TO_PASS.txt",
        "reward_metadata.json",
        "reward-extra-info.json",
        "provider_secret.txt",
        "provider-secret.txt",
        "final-verifier.json",
    ],
)
def test_write_file_rejects_sensitive_marker_path_variants(tmp_path: Path, path: str) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)

    result = _execute(
        context,
        "write_file",
        {"path": path, "content": "x\n", "mode": "create"},
    )

    assert result.status == "denied"
    assert result.typed["reason_code"] == "model_hidden_path_denied"
    assert not (workspace / path).exists()


def test_apply_patch_rejects_sensitive_marker_variants_for_all_path_fields(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "public.txt").write_text("public\n", encoding="utf-8")
    (workspace / "delete_public.txt").write_text("delete\n", encoding="utf-8")
    (workspace / "move_source.txt").write_text("move\n", encoding="utf-8")

    replace_result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "replace_text",
                    "path": "runtime-private/public.txt",
                    "old_text": "public",
                    "new_text": "changed",
                    "expected_content_hash": _hash_text("public\n"),
                }
            ]
        },
    )
    delete_result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "delete_file",
                    "path": "gold-patch.py",
                    "expected_content_hash": _hash_text("delete\n"),
                    "reason": "Exercise sensitive delete marker denial.",
                }
            ]
        },
    )
    move_target_result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "move_file",
                    "source_path": "move_source.txt",
                    "target_path": "hiddenVerifier.txt",
                    "expected_source_hash": _hash_text("move\n"),
                    "reason": "Exercise sensitive move target marker denial.",
                }
            ]
        },
    )

    assert replace_result.status == "denied"
    assert replace_result.typed["reason_code"] == "model_hidden_path_denied"
    assert delete_result.status == "denied"
    assert delete_result.typed["reason_code"] == "model_hidden_path_denied"
    assert move_target_result.status == "denied"
    assert move_target_result.typed["reason_code"] == "model_hidden_path_denied"
    assert (workspace / "public.txt").read_text(encoding="utf-8") == "public\n"
    assert (workspace / "delete_public.txt").read_text(encoding="utf-8") == "delete\n"
    assert (workspace / "move_source.txt").read_text(encoding="utf-8") == "move\n"
    assert not (workspace / "hiddenVerifier.txt").exists()


def test_apply_patch_rejects_duplicate_path_before_mutation(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "duplicate.txt").write_text("duplicate\n", encoding="utf-8")

    result = _execute(
        context,
        "apply_patch",
        {
            "operations": [
                {
                    "op": "replace_text",
                    "path": "duplicate.txt",
                    "old_text": "duplicate",
                    "new_text": "first",
                    "expected_content_hash": _hash_text("duplicate\n"),
                },
                {
                    "op": "replace_text",
                    "path": "duplicate.txt",
                    "old_text": "duplicate",
                    "new_text": "second",
                    "expected_content_hash": _hash_text("duplicate\n"),
                },
            ]
        },
    )

    assert result.status == "denied"
    assert result.typed["reason_code"] == "duplicate_mutation_path"
    assert result.typed["repository_mutation_performed"] is False
    assert (workspace / "duplicate.txt").read_text(encoding="utf-8") == "duplicate\n"


def test_standalone_delete_move_mkdir_remain_extended_but_executable(tmp_path: Path) -> None:
    context = _tool_context(tmp_path)
    workspace = Path(context.run_workspace.workspace_path)
    (workspace / "remove.txt").write_text("remove\n", encoding="utf-8")
    (workspace / "source.txt").write_text("source\n", encoding="utf-8")
    registry = ToolRegistry([build_tool("delete_file"), build_tool("move_file"), build_tool("mkdir")])
    executor = ToolExecutor(registry=registry)

    delete_result = executor.execute(
        ToolCall(
            tool_call_id="call_delete",
            tool_name="delete_file",
            arguments={
                "path": "remove.txt",
                "expected_content_hash": _hash_text("remove\n"),
                "reason": "Remove an obsolete extended-profile file.",
            },
            turn=1,
        ),
        context,
    )
    move_result = executor.execute(
        ToolCall(
            tool_call_id="call_move",
            tool_name="move_file",
            arguments={
                "source_path": "source.txt",
                "target_path": "target.txt",
                "expected_source_hash": _hash_text("source\n"),
                "reason": "Rename an extended-profile file.",
            },
            turn=1,
        ),
        context,
    )
    mkdir_result = executor.execute(
        ToolCall(
            tool_call_id="call_mkdir",
            tool_name="mkdir",
            arguments={"path": "nested/dir"},
            turn=1,
        ),
        context,
    )

    assert delete_result.status == "ok"
    assert move_result.status == "ok"
    assert mkdir_result.status == "ok"
    assert not (workspace / "remove.txt").exists()
    assert not (workspace / "source.txt").exists()
    assert (workspace / "target.txt").read_text(encoding="utf-8") == "source\n"
    assert (workspace / "nested" / "dir").is_dir()


def test_stage16g2b_writer_outputs_public_safe_evidence_and_inspector(tmp_path: Path) -> None:
    digests = write_stage16g2b_reports(tmp_path)

    assert {
        "stage16g2b_file_mutation_probe_report.json",
        "stage16g2b_safety_denial_probe_report.json",
        "stage16g2b_path_leak_scan_report.json",
        "stage16g2b_acceptance_summary.json",
    } <= set(digests)
    result = json.loads(
        inspect_stage16g2b_file_mutation(
            tmp_path / "stage16g2b_acceptance_summary.json",
            assert_complete=True,
        )
    )

    assert result["status"] == "passed"
    assert result["failure_count"] == 0
    assert result["derived_checks"]["unary_delete_supported_by_apply_patch"] is True
    assert result["derived_checks"]["unary_move_supported_by_apply_patch"] is True
    assert result["derived_checks"]["policy_loss_candidate_for_new_tools"] is False
    safety = json.loads((tmp_path / "stage16g2b_safety_denial_probe_report.json").read_text())
    labels = {record["label"] for record in safety["denials"]}
    assert "sensitive_marker_variant_denial" in labels
    assert safety["sensitive_marker_variant_path_absent"] is True
    assert set(safety["required_reason_codes"]) == {
        "binary_file_denied",
        "duplicate_mutation_path",
        "model_hidden_path_denied",
        "non_utf8_file_denied",
        "stale_file_state",
        "symlink_not_mutable",
    }


def test_stage16g2b_inspector_rejects_safety_tamper_even_if_digest_updated(tmp_path: Path) -> None:
    write_stage16g2b_reports(tmp_path)
    safety_path = tmp_path / "stage16g2b_safety_denial_probe_report.json"
    safety = json.loads(safety_path.read_text())
    safety["denials"] = [
        record
        for record in safety["denials"]
        if record.get("label") != "duplicate_path_denial"
    ]
    _write_json(safety_path, safety)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2b_safety_denial_probe_report.json",
        "safety_denial_probe_report_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2b_file_mutation(
            tmp_path / "stage16g2b_acceptance_summary.json",
            assert_complete=True,
        )

    assert "safety_denial_missing:duplicate_path_denial" in str(exc_info.value)


def test_stage16g2b_inspector_rejects_success_probe_semantic_tamper(tmp_path: Path) -> None:
    write_stage16g2b_reports(tmp_path)
    mutation_path = tmp_path / "stage16g2b_file_mutation_probe_report.json"
    mutation = json.loads(mutation_path.read_text())
    mutation["core_default_tool_behavior"][0]["repository_mutation_performed"] = False
    mutation["core_default_tool_behavior"][0]["changed_path_count"] = 0
    _write_json(mutation_path, mutation)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2b_file_mutation_probe_report.json",
        "file_mutation_probe_report_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2b_file_mutation(
            tmp_path / "stage16g2b_acceptance_summary.json",
            assert_complete=True,
        )

    message = str(exc_info.value)
    assert "core_mutation_probe_not_marked_mutating:write_file_create" in message
    assert "core_mutation_probe_changed_path_count_missing:write_file_create" in message


def test_stage16g2b_inspector_rejects_denial_training_eligibility_tamper(tmp_path: Path) -> None:
    write_stage16g2b_reports(tmp_path)
    safety_path = tmp_path / "stage16g2b_safety_denial_probe_report.json"
    safety = json.loads(safety_path.read_text())
    safety["denials"][0]["policy_loss_candidate"] = True
    safety["denials"][0]["allowed_in_policy_loss_trajectory"] = True
    _write_json(safety_path, safety)
    _refresh_summary_digest(
        tmp_path,
        "stage16g2b_safety_denial_probe_report.json",
        "safety_denial_probe_report_sha256",
    )

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2b_file_mutation(
            tmp_path / "stage16g2b_acceptance_summary.json",
            assert_complete=True,
        )

    message = str(exc_info.value)
    assert "safety_denial_policy_loss_enabled:atomic_preflight_stale_hash" in message
    assert "safety_denial_policy_loss_trajectory_enabled:atomic_preflight_stale_hash" in message


def test_stage16g2b_inspector_rescans_public_evidence(tmp_path: Path) -> None:
    write_stage16g2b_reports(tmp_path)
    summary_path = tmp_path / "stage16g2b_acceptance_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["local_path_probe"] = "/Users/roger/secret"
    _write_json(summary_path, summary)

    with pytest.raises(Exception) as exc_info:
        inspect_stage16g2b_file_mutation(summary_path, assert_complete=True)

    assert "stage16g2b_path_leak_scan_report_stale_or_mismatched" in str(exc_info.value)
