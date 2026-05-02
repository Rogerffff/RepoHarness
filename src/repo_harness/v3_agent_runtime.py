"""V3 Agent Loop runtime helpers for final-only SWE-Bench-like tasks."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_harness.errors import ConfigError
from repo_harness.tasks import RunnableTask
from repo_harness.trajectory import ArtifactRef
from repo_harness.v3_swebench_like import (
    SWEBENCH_LIKE_COMMAND_RESULT_VERSION,
    _aggregate_final_result,
    _apply_patch,
    _read_json,
    _run_verifier_command,
)
from repo_harness.verifier.schemas import TestCaseResult, VerifierResult
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

AGENT_LOOP_RUNTIME_VERSION = "repo_harness_v3_agent_loop_runtime_v0"


@dataclass(frozen=True)
class SweBenchLikeRuntimePlan:
    task_id: str
    manifest_path: Path
    manifest_root: Path
    entry: dict[str, Any]
    plan: dict[str, Any]
    selector_cache: dict[str, Any]
    environment_spec: dict[str, Any]


def load_swebench_like_runtime_plan(task: RunnableTask) -> SweBenchLikeRuntimePlan | None:
    """Return the V3 final-only runtime plan declared in task metadata, if any."""

    if task.metadata.get("v3_adapter") != "swebench_like_fixed":
        return None
    manifest_value = task.metadata.get("swebench_like_manifest_path")
    if not manifest_value:
        return None
    manifest_path = Path(str(manifest_value))
    manifest = _read_json(manifest_path)
    entries = manifest.get("entries", [])
    if not isinstance(entries, list):
        raise ConfigError(f"SWE-Bench-like manifest entries 无效：{manifest_path}")
    entry = next((item for item in entries if item.get("task_id") == task.task_id), None)
    if entry is None:
        raise ConfigError(f"SWE-Bench-like manifest 缺少 task：{task.task_id}")
    manifest_root = manifest_path.parent
    plan = _read_json(_resolve_ref(manifest_root, entry["verifier_plan_ref"]["relative_path"]))
    selector_cache = _read_json(_resolve_ref(manifest_root, entry["selector_cache_ref"]["relative_path"]))
    environment_spec = _read_json(
        _resolve_ref(manifest_root, entry["environment_spec_ref"]["relative_path"])
    )
    return SweBenchLikeRuntimePlan(
        task_id=task.task_id,
        manifest_path=manifest_path,
        manifest_root=manifest_root,
        entry=entry,
        plan=plan,
        selector_cache=selector_cache,
        environment_spec=environment_spec,
    )


def build_swebench_like_baseline_verifier(plan: SweBenchLikeRuntimePlan) -> VerifierResult:
    """Build a baseline VerifierResult from frozen Stage 6 evaluator-only evidence."""

    baseline_f2p = _read_json(
        _resolve_ref(plan.manifest_root, plan.entry["baseline_fail_to_pass_evidence_ref"]["relative_path"])
    )
    baseline_p2p = _read_json(
        _resolve_ref(plan.manifest_root, plan.entry["pass_to_pass_baseline_evidence_ref"]["relative_path"])
    )
    f2p_total = int(baseline_f2p.get("total_count", plan.plan.get("fail_to_pass_selector_count", 0)))
    p2p_total = int(baseline_p2p.get("total_count", plan.plan.get("pass_to_pass_selector_count", 0)))
    f2p_passed = int(baseline_f2p.get("passed_count", 0))
    p2p_passed = int(baseline_p2p.get("passed_count", 0))
    total = max(1, f2p_total + p2p_total)
    return VerifierResult(
        verifier_stage="baseline",
        parser_confidence=min(
            float(baseline_f2p.get("parser_confidence", 0.0)),
            float(baseline_p2p.get("parser_confidence", 0.0)),
        ),
        command="swebench_like_frozen_baseline_evidence",
        test_cases=[
            *[
                TestCaseResult(test_id=f"fail_to_pass::{index}", status="failed")
                for index in range(max(0, f2p_total - f2p_passed))
            ],
            *[
                TestCaseResult(test_id=f"pass_to_pass::{index}", status="passed")
                for index in range(p2p_passed)
            ],
        ],
        accepted=False,
        accepted_fallback_reason=None,
        pass_ratio=(f2p_passed + p2p_passed) / total,
        fail_to_pass={"passed": f2p_passed, "total": f2p_total},
        pass_to_pass={"passed": p2p_passed, "total": p2p_total},
        exit_code=1,
        timeout=bool(baseline_f2p.get("timeout") or baseline_p2p.get("timeout")),
        error_type="assertion_failure",
    )


def run_swebench_like_final_verifier(
    *,
    plan: SweBenchLikeRuntimePlan,
    final_patch_path: str | Path,
    run_dir: str | Path,
) -> VerifierResult:
    """Replay the model final patch in an independent SWE-Bench-like verifier workspace."""

    run_root = Path(run_dir)
    task_root = run_root / "v3_swebench_like_final_verifier" / plan.task_id
    if task_root.exists():
        shutil.rmtree(task_root)
    task_root.mkdir(parents=True, exist_ok=True)
    baseline_workspace = _resolve_ref(
        plan.manifest_root,
        plan.entry["baseline_workspace_ref"]["relative_path"],
    )
    verification_workspace = task_root / "verification_workspace"
    shutil.copytree(
        baseline_workspace,
        verification_workspace,
        symlinks=True,
        ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__", "*.pyc"),
    )
    patch_apply = _apply_patch(
        workspace=verification_workspace,
        patch_path=Path(final_patch_path),
        task_root=task_root,
        label=f"{plan.task_id}_agent_loop_final_patch_apply",
        execute=True,
    )
    environment = _environment_from_plan(plan)
    if patch_apply.get("status") == "passed":
        f2p = _run_verifier_command(
            task_id=plan.task_id,
            task_root=task_root,
            workspace=verification_workspace,
            environment=environment,
            command=plan.plan["fail_to_pass_command"],
            selectors=plan.selector_cache["expanded_fail_to_pass"],
            phase="agent_loop_final",
            suite="fail_to_pass",
            execute=True,
        )
        p2p = _run_verifier_command(
            task_id=plan.task_id,
            task_root=task_root,
            workspace=verification_workspace,
            environment=environment,
            command=plan.plan["pass_to_pass_command"],
            selectors=plan.selector_cache["expanded_pass_to_pass"],
            phase="agent_loop_final",
            suite="pass_to_pass",
            execute=True,
        )
    else:
        f2p = _skipped_command_result(plan, "fail_to_pass", "patch_apply_failed")
        p2p = _skipped_command_result(plan, "pass_to_pass", "patch_apply_failed")
    final_result = _aggregate_final_result(
        task_id=plan.task_id,
        final_patch_apply=patch_apply,
        model_results={"fail_to_pass": f2p, "pass_to_pass": p2p},
        selector_cache=plan.selector_cache,
    )
    final_result_path = task_root / "final_verifier_result.json"
    _write_json(final_result_path, final_result)
    report = {
        "schema_version": AGENT_LOOP_RUNTIME_VERSION,
        "task_id": plan.task_id,
        "manifest_ref": _artifact_ref(
            plan.manifest_path,
            base_dir=Path.cwd(),
            artifact_id=f"{plan.task_id}_swebench_like_manifest",
            kind="json",
            redaction_status="evaluator_only",
        ),
        "verification_workspace_ref": _artifact_ref(
            verification_workspace,
            base_dir=run_root,
            artifact_id=f"{plan.task_id}_agent_loop_verification_workspace",
            kind="source_directory",
            redaction_status="evaluator_only",
        ),
        "final_verifier_result_ref": _artifact_ref(
            final_result_path,
            base_dir=run_root,
            artifact_id=f"{plan.task_id}_agent_loop_final_verifier_result",
            kind="json",
            redaction_status="evaluator_only",
        ),
        "official_harness_report_used": False,
        "hidden_visibility_policy": "evaluator_only",
    }
    _write_json(task_root / "swebench_like_agent_loop_final_verifier_report.json", report)
    return _verifier_result_from_swebench_result(final_result)


def _verifier_result_from_swebench_result(payload: dict[str, Any]) -> VerifierResult:
    f2p = payload.get("fail_to_pass_result", {})
    p2p = payload.get("pass_to_pass_result", {})
    test_cases = []
    for suite_payload in (f2p, p2p):
        for case in suite_payload.get("test_cases", []) or []:
            test_cases.append(
                TestCaseResult(
                    test_id=str(case.get("test_id", "unknown")),
                    status=str(case.get("status", "unknown")),  # type: ignore[arg-type]
                )
            )
    total = max(1, len(test_cases))
    passed = sum(1 for case in test_cases if case.status == "passed")
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=float(payload.get("parser_confidence", 0.0)),
        command="swebench_like_fail_to_pass_and_pass_to_pass",
        test_cases=test_cases,
        accepted=bool(payload.get("accepted")),
        pass_ratio=passed / total,
        fail_to_pass=payload.get("fail_to_pass", {"passed": 0, "total": 0}),
        pass_to_pass=payload.get("pass_to_pass", {"passed": 0, "total": 0}),
        exit_code=0 if payload.get("accepted") else 1,
        timeout=bool(f2p.get("timeout") or p2p.get("timeout")),
        error_type=payload.get("error_type"),
    )


def _environment_from_plan(plan: SweBenchLikeRuntimePlan) -> dict[str, Any]:
    repo = plan.entry.get("repo")
    return {
        "execution_image": plan.environment_spec["execution_image"],
        "test_timeout_sec": plan.plan["per_command_timeout_sec"],
        "pythonpath": "src" if repo == "pytest-dev/pytest" else ".",
    }


def _skipped_command_result(
    plan: SweBenchLikeRuntimePlan,
    suite: str,
    reason: str,
) -> dict[str, Any]:
    selectors = plan.selector_cache[
        "expanded_fail_to_pass" if suite == "fail_to_pass" else "expanded_pass_to_pass"
    ]
    return {
        "schema_version": SWEBENCH_LIKE_COMMAND_RESULT_VERSION,
        "instance_id": plan.task_id,
        "phase": "agent_loop_final",
        "suite": suite,
        "status": "skipped",
        "structured_skip_reason": reason,
        "command": plan.plan[
            "fail_to_pass_command" if suite == "fail_to_pass" else "pass_to_pass_command"
        ],
        "selectors": selectors,
        "exit_code": None,
        "timeout": False,
        "parser_confidence": 0.0,
        "error_type": reason,
        "test_cases": [{"test_id": selector, "status": "error"} for selector in selectors],
        "passed_count": 0,
        "total_count": len(selectors),
    }


def _artifact_ref(
    path: Path,
    *,
    base_dir: Path,
    artifact_id: str,
    kind: str,
    redaction_status: str = "not_required",
) -> dict[str, Any]:
    if path.is_dir():
        digest = compute_source_tree_hash(path)
        size_bytes = 0
    else:
        digest = compute_file_sha256(path)
        size_bytes = path.stat().st_size
    return ArtifactRef(
        artifact_id=artifact_id,
        relative_path=_relative_path(path, base_dir),
        kind=kind,
        sha256=digest,
        size_bytes=size_bytes,
        redaction_status=redaction_status,
        retention_policy="keep",
    ).model_dump(mode="json")


def _relative_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_ref(base: Path, relative_path: str) -> Path:
    raw = Path(relative_path)
    if raw.is_absolute():
        return raw
    for candidate_base in (base, Path.cwd()):
        candidate = candidate_base / raw
        if candidate.exists():
            return candidate
    return base / raw


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
