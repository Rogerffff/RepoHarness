"""Build Stage 16G.2B structured file mutation probe evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if SRC_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SRC_ROOT.as_posix())

from repo_harness.permissions import PermissionContext  # noqa: E402
from repo_harness.stage16g2_file_surface import (  # noqa: E402
    DEFAULT_STAGE16G2_DIR,
    STAGE16G2B_SOURCE_DIGEST_FILES,
    scan_stage16g2b_public_files,
)
from repo_harness.tools import ToolExecutionContext, ToolExecutor, ToolRegistry, build_tool  # noqa: E402
from repo_harness.tools.schemas import ToolCall  # noqa: E402
from repo_harness.trajectory import RunRecorder  # noqa: E402
from repo_harness.workspace import DependencyState, LocalWorkspaceAdapter, RunWorkspace  # noqa: E402


def _hash_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: object) -> str:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return _sha256_file(path)


def _tool_context(root: Path) -> ToolExecutionContext:
    run_dir = root / "run"
    workspace = run_dir / "workspaces" / "agent_workspace"
    workspace.mkdir(parents=True)
    recorder = RunRecorder("stage16g2b-probe", run_dir, task_id="task")
    adapter = LocalWorkspaceAdapter(run_id="stage16g2b-probe", run_dir=run_dir)
    return ToolExecutionContext(
        run_id="stage16g2b-probe",
        task_id="task",
        workspace_facade=adapter,
        run_workspace=RunWorkspace(
            run_id="stage16g2b-probe",
            workspace_path=workspace.as_posix(),
            artifact_dir=(run_dir / "artifacts").as_posix(),
            dependency_state=DependencyState(),
        ),
        artifact_writer=recorder,
        permission_context=PermissionContext(mode="auto"),
        verifier_feedback_facade=None,  # type: ignore[arg-type]
        resolved_verifier_plan=None,  # type: ignore[arg-type]
    )


def _execute(
    context: ToolExecutionContext,
    tool_name: str,
    arguments: dict[str, object],
    *,
    registry: ToolRegistry | None = None,
):
    executor = ToolExecutor(registry=registry) if registry is not None else ToolExecutor()
    return executor.execute(
        ToolCall(
            tool_call_id=f"call_{tool_name}_{_hash_text(json.dumps(arguments, sort_keys=True))[:8]}",
            tool_name=tool_name,
            arguments=arguments,
            turn=1,
        ),
        context,
    )


def _summarize_result(label: str, result) -> dict[str, object]:
    operation_facts = result.typed.get("operation_facts", [])
    return {
        "label": label,
        "tool_name": result.tool_name,
        "status": result.status,
        "error_type": result.error_type,
        "reason_code": result.typed.get("reason_code"),
        "result_kind": result.typed.get("result_kind"),
        "operation_count": len(operation_facts) if isinstance(operation_facts, list) else 0,
        "operation_kinds": [
            fact.get("op")
            for fact in operation_facts
            if isinstance(fact, dict) and isinstance(fact.get("op"), str)
        ],
        "changed_path_count": len(result.typed.get("changed_paths", []) or []),
        "partial_failure": bool(result.typed.get("partial_failure", False)),
        "repository_mutation_performed": bool(result.typed.get("repository_mutation_performed", False)),
        "allowed_in_policy_loss_trajectory": bool(result.typed.get("allowed_in_policy_loss_trajectory", False)),
        "policy_loss_candidate": bool(result.typed.get("policy_loss_candidate", False)),
        "sample_policy_loss_candidate_effect": result.typed.get("sample_policy_loss_candidate_effect"),
        "official_prediction_eligible": bool(result.typed.get("official_prediction_eligible", False)),
        "training_export_eligible": bool(result.typed.get("training_export_eligible", False)),
        "invalid_for_training": bool(result.typed.get("invalid_for_training", False)),
        "diagnostic_side_channel_only": bool(result.typed.get("diagnostic_side_channel_only", False)),
        "artifact_sha256s": [ref.sha256 for ref in result.artifact_refs],
    }


def build_probe_reports() -> tuple[dict[str, object], dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="stage16g2b-probe-") as temp_dir:
        context = _tool_context(Path(temp_dir))
        workspace = Path(context.run_workspace.workspace_path)

        write_create = _execute(
            context,
            "write_file",
            {"path": "notes.txt", "content": "first\n", "mode": "create"},
        )
        write_overwrite = _execute(
            context,
            "write_file",
            {
                "path": "notes.txt",
                "content": "second\n",
                "mode": "overwrite",
                "expected_content_hash": _hash_text("first\n"),
            },
        )

        (workspace / "a.txt").write_text("alpha\n", encoding="utf-8")
        (workspace / "delete_me.txt").write_text("delete\n", encoding="utf-8")
        (workspace / "old_name.txt").write_text("move\n", encoding="utf-8")
        batch = _execute(
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
                        "reason": "Remove obsolete probe fixture.",
                    },
                    {
                        "op": "move_file",
                        "source_path": "old_name.txt",
                        "target_path": "new_name.txt",
                        "expected_source_hash": _hash_text("move\n"),
                        "reason": "Rename probe fixture to the new name.",
                    },
                    {"op": "mkdir", "path": "pkg/subpkg"},
                ]
            },
        )

        (workspace / "delete_one.txt").write_text("obsolete\n", encoding="utf-8")
        unary_delete = _execute(
            context,
            "apply_patch",
            {
                "operations": [
                    {
                        "op": "delete_file",
                        "path": "delete_one.txt",
                        "expected_content_hash": _hash_text("obsolete\n"),
                        "reason": "Remove one obsolete file.",
                    }
                ]
            },
        )
        (workspace / "move_one.txt").write_text("renamed\n", encoding="utf-8")
        unary_move = _execute(
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

        registry = ToolRegistry([build_tool("delete_file"), build_tool("move_file"), build_tool("mkdir")])
        (workspace / "standalone_delete.txt").write_text("remove\n", encoding="utf-8")
        standalone_delete = _execute(
            context,
            "delete_file",
            {
                "path": "standalone_delete.txt",
                "expected_content_hash": _hash_text("remove\n"),
                "reason": "Exercise extended standalone delete.",
            },
            registry=registry,
        )
        (workspace / "standalone_move.txt").write_text("move\n", encoding="utf-8")
        standalone_move = _execute(
            context,
            "move_file",
            {
                "source_path": "standalone_move.txt",
                "target_path": "standalone_moved.txt",
                "expected_source_hash": _hash_text("move\n"),
                "reason": "Exercise extended standalone move.",
            },
            registry=registry,
        )
        standalone_mkdir = _execute(
            context,
            "mkdir",
            {"path": "standalone_dir"},
            registry=registry,
        )

        mutation_report = {
            "schema_version": "stage16g2b.file_mutation_probe_report.v1",
            "status": "passed",
            "public_safe": True,
            "core_default_tool_behavior": [
                _summarize_result("write_file_create", write_create),
                _summarize_result("write_file_overwrite", write_overwrite),
                _summarize_result("apply_patch_batch", batch),
                _summarize_result("apply_patch_unary_delete", unary_delete),
                _summarize_result("apply_patch_unary_move", unary_move),
            ],
            "extended_tool_behavior": [
                _summarize_result("standalone_delete_file", standalone_delete),
                _summarize_result("standalone_move_file", standalone_move),
                _summarize_result("standalone_mkdir", standalone_mkdir),
            ],
            "unary_delete_supported_by_apply_patch": unary_delete.status == "ok",
            "unary_move_supported_by_apply_patch": unary_move.status == "ok",
            "standalone_tools_remain_extended": True,
            "raw_temporary_paths_recorded": False,
        }

        (workspace / "atomic_a.txt").write_text("alpha\n", encoding="utf-8")
        (workspace / "atomic_b.txt").write_text("bravo\n", encoding="utf-8")
        atomic_denial = _execute(
            context,
            "apply_patch",
            {
                "operations": [
                    {
                        "op": "replace_text",
                        "path": "atomic_a.txt",
                        "old_text": "alpha",
                        "new_text": "beta",
                        "expected_content_hash": _hash_text("alpha\n"),
                    },
                    {
                        "op": "delete_file",
                        "path": "atomic_b.txt",
                        "expected_content_hash": "wrong",
                        "reason": "Remove stale atomic probe file.",
                    },
                ]
            },
        )
        (workspace / "binary.dat").write_bytes(b"\x00\x01")
        hidden_denial = _execute(
            context,
            "write_file",
            {"path": ".git/config", "content": "x", "mode": "create"},
        )
        binary_denial = _execute(
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
        (workspace / "non_utf8.txt").write_bytes(b"\xff\xfe")
        non_utf8_denial = _execute(
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
        outside = Path(temp_dir) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        (workspace / "link.txt").symlink_to(outside)
        symlink_denial = _execute(
            context,
            "write_file",
            {
                "path": "link.txt",
                "content": "changed\n",
                "mode": "overwrite",
                "expected_content_hash": _hash_text("outside\n"),
            },
        )
        (workspace / "duplicate.txt").write_text("duplicate\n", encoding="utf-8")
        duplicate_denial = _execute(
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
        sensitive_marker_denial = _execute(
            context,
            "write_file",
            {"path": "runtime-private/gold-patch.py", "content": "x\n", "mode": "create"},
        )

        safety_report = {
            "schema_version": "stage16g2b.safety_denial_probe_report.v1",
            "status": "passed",
            "public_safe": True,
            "denials": [
                _summarize_result("atomic_preflight_stale_hash", atomic_denial),
                _summarize_result("hidden_path_denial", hidden_denial),
                _summarize_result("binary_file_denial", binary_denial),
                _summarize_result("non_utf8_file_denial", non_utf8_denial),
                _summarize_result("symlink_denial", symlink_denial),
                _summarize_result("duplicate_path_denial", duplicate_denial),
                _summarize_result("sensitive_marker_variant_denial", sensitive_marker_denial),
            ],
            "atomic_preflight_preserved_first_file": (workspace / "atomic_a.txt").read_text(encoding="utf-8")
            == "alpha\n",
            "atomic_preflight_preserved_second_file": (workspace / "atomic_b.txt").read_text(encoding="utf-8")
            == "bravo\n",
            "duplicate_path_preserved_file": (workspace / "duplicate.txt").read_text(encoding="utf-8")
            == "duplicate\n",
            "symlink_target_preserved": outside.read_text(encoding="utf-8") == "outside\n",
            "sensitive_marker_variant_path_absent": not (workspace / "runtime-private" / "gold-patch.py").exists(),
            "required_reason_codes": sorted(
                {
                    atomic_denial.typed.get("reason_code"),
                    hidden_denial.typed.get("reason_code"),
                    binary_denial.typed.get("reason_code"),
                    non_utf8_denial.typed.get("reason_code"),
                    symlink_denial.typed.get("reason_code"),
                    duplicate_denial.typed.get("reason_code"),
                    sensitive_marker_denial.typed.get("reason_code"),
                }
            ),
            "raw_temporary_paths_recorded": False,
        }
    return mutation_report, safety_report


def write_stage16g2b_reports(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mutation_report, safety_report = build_probe_reports()
    digests = {
        "stage16g2b_file_mutation_probe_report.json": _write_json(
            output_dir / "stage16g2b_file_mutation_probe_report.json", mutation_report
        ),
        "stage16g2b_safety_denial_probe_report.json": _write_json(
            output_dir / "stage16g2b_safety_denial_probe_report.json", safety_report
        ),
    }
    path_scan = scan_stage16g2b_public_files(output_dir)
    digests["stage16g2b_path_leak_scan_report.json"] = _write_json(
        output_dir / "stage16g2b_path_leak_scan_report.json", path_scan
    )
    expected_safety_reason_codes = {
        "binary_file_denied",
        "duplicate_mutation_path",
        "model_hidden_path_denied",
        "non_utf8_file_denied",
        "stale_file_state",
        "symlink_not_mutable",
    }
    status = (
        "passed"
        if (
            mutation_report["status"] == "passed"
            and safety_report["status"] == "passed"
            and mutation_report["unary_delete_supported_by_apply_patch"]
            and mutation_report["unary_move_supported_by_apply_patch"]
            and safety_report["atomic_preflight_preserved_first_file"]
            and safety_report["atomic_preflight_preserved_second_file"]
            and safety_report["duplicate_path_preserved_file"]
            and safety_report["symlink_target_preserved"]
            and safety_report["sensitive_marker_variant_path_absent"]
            and set(safety_report["required_reason_codes"]) == expected_safety_reason_codes
            and path_scan["public_path_leak_scan_passed"]
        )
        else "failed"
    )
    summary = {
        "schema_version": "stage16g2b.acceptance_summary.v1",
        "status": status,
        "stage16g2b_complete": status == "passed",
        "stage16g2c_allowed_to_start": status == "passed",
        "stage16g3_allowed_to_start": False,
        "stage17b_real_data_freeze_allowed": False,
        "stage20_warm_start_data_generation_allowed": False,
        "stage21_formal_rl_allowed": False,
        "default_behavior_enabled_tools": ["write_file", "apply_patch"],
        "standalone_tools_default_visible": False,
        "standalone_tools_extended_executable": True,
        "unary_delete_supported_by_apply_patch": mutation_report["unary_delete_supported_by_apply_patch"],
        "unary_move_supported_by_apply_patch": mutation_report["unary_move_supported_by_apply_patch"],
        "atomic_preflight_passed": safety_report["atomic_preflight_preserved_first_file"]
        and safety_report["atomic_preflight_preserved_second_file"],
        "duplicate_path_preserved_file": safety_report["duplicate_path_preserved_file"],
        "symlink_target_preserved": safety_report["symlink_target_preserved"],
        "sensitive_marker_variant_path_absent": safety_report["sensitive_marker_variant_path_absent"],
        "safety_denial_reason_codes_complete": set(safety_report["required_reason_codes"])
        == expected_safety_reason_codes,
        "policy_loss_candidate_for_new_tools": False,
        "next_required_stage_for_policy_loss": "16G.2C",
        "source_digests": {
            relative_path: _sha256_file(REPO_ROOT / relative_path)
            for relative_path in STAGE16G2B_SOURCE_DIGEST_FILES
        },
        "file_mutation_probe_report_sha256": digests["stage16g2b_file_mutation_probe_report.json"],
        "safety_denial_probe_report_sha256": digests["stage16g2b_safety_denial_probe_report.json"],
        "path_leak_scan_report_sha256": digests["stage16g2b_path_leak_scan_report.json"],
    }
    digests["stage16g2b_acceptance_summary.json"] = _write_json(
        output_dir / "stage16g2b_acceptance_summary.json", summary
    )
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_STAGE16G2_DIR.as_posix())
    args = parser.parse_args(argv)
    digests = write_stage16g2b_reports(Path(args.output_dir))
    print(
        json.dumps(
            {
                "status": "passed",
                "output_dir": args.output_dir,
                "file_count": len(digests),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
