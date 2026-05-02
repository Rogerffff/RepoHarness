"""V3 Agent Loop integration command and inspection helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from repo_harness.errors import ConfigError
from repo_harness.evaluation.runner import run_task
from repo_harness.trajectory import ArtifactRef, read_jsonl, verify_artifact_manifest
from repo_harness.v3_visibility import V3ContaminationDenylist
from repo_harness.workspace.source_hash import compute_file_sha256, compute_source_tree_hash

AGENT_LOOP_INTEGRATION_VERSION = "repo_harness_v3_agent_loop_integration_report_v0"
AGENT_LOOP_INSPECT_VERSION = "repo_harness_v3_agent_loop_integration_inspect_v0"
DEFAULT_REAL_TASK_ID = "realrepo_local_buggy_calculator"
DEFAULT_SWEBENCH_TASK_ID = "pytest-dev__pytest-7220"


def build_v3_agent_loop_integration(
    *,
    source_materialization_run: str | Path,
    swebench_like_run: str | Path,
    output_dir: str | Path,
    real_task_id: str = DEFAULT_REAL_TASK_ID,
    swebench_task_id: str = DEFAULT_SWEBENCH_TASK_ID,
) -> Path:
    """Run one real repository task and one SWE-Bench-like final-only task through run_task."""

    source_root = Path(source_materialization_run)
    swebench_root = Path(swebench_like_run)
    output_root = Path(output_dir)
    if output_root.exists():
        raise ConfigError(f"Stage 7 output directory 已存在，不能覆盖：{output_root}")
    output_root.mkdir(parents=True)
    generated = output_root / "generated_inputs"
    generated.mkdir()
    run_root = output_root / "agent_loop_runs"
    run_root.mkdir()
    source_report = _read_json(source_root / "source_materialization_report.json")
    source_entries = {entry["task_id"]: entry for entry in source_report.get("entries", [])}
    if real_task_id not in source_entries:
        raise ConfigError(f"source materialization 缺少真实仓库任务：{real_task_id}")
    if swebench_task_id not in source_entries:
        raise ConfigError(f"source materialization 缺少 SWE-Bench-like 任务：{swebench_task_id}")

    real_replay = _write_real_replay(generated / f"{real_task_id}_replay.yaml", real_task_id)
    real_config = _write_real_config(
        generated / f"{real_task_id}_run_config.yaml",
        replay_path=real_replay,
        output_dir=run_root,
    )
    real_run_dir = run_task(
        _resolve_source_ref(source_root, source_entries[real_task_id]["task_definition_ref"]),
        config_path=real_config,
        output_dir=run_root,
        run_id=f"v3_stage_07_{real_task_id}",
    )

    swe_task = _write_swebench_agent_task(
        generated / f"{swebench_task_id}_agent_loop_task.yaml",
        source_root=source_root,
        source_entry=source_entries[swebench_task_id],
        swebench_manifest=swebench_root / "swebench_like_task_manifest.json",
    )
    swe_replay = _write_swebench_replay(
        generated / f"{swebench_task_id}_diagnostic_replay.yaml",
        swebench_task_id,
    )
    swe_config = _write_swebench_config(
        generated / f"{swebench_task_id}_run_config.yaml",
        replay_path=swe_replay,
        output_dir=run_root,
    )
    swe_run_dir = run_task(
        swe_task,
        config_path=swe_config,
        output_dir=run_root,
        run_id=f"v3_stage_07_{swebench_task_id}",
    )

    real_scan = scan_v3_run_surfaces(real_run_dir)
    swe_scan = scan_v3_run_surfaces(swe_run_dir)
    real_scan_path = output_root / "real_repository_contamination_scan.json"
    swe_scan_path = output_root / "swebench_like_contamination_scan.json"
    _write_json(real_scan_path, real_scan)
    _write_json(swe_scan_path, swe_scan)
    report = {
        "schema_version": AGENT_LOOP_INTEGRATION_VERSION,
        "generated_at": _utc_timestamp(),
        "source_materialization_report_ref": _artifact_ref(
            source_root / "source_materialization_report.json",
            base_dir=Path.cwd(),
            artifact_id="stage7_source_materialization_report",
            kind="json",
        ),
        "swebench_like_manifest_ref": _artifact_ref(
            swebench_root / "swebench_like_task_manifest.json",
            base_dir=Path.cwd(),
            artifact_id="stage7_swebench_like_manifest",
            kind="json",
            redaction_status="evaluator_only",
        ),
        "runs": {
            "real_repository": _run_summary(real_run_dir),
            "swebench_like": _run_summary(swe_run_dir),
        },
        "contamination_scan_refs": [
            _artifact_ref(
                real_scan_path,
                base_dir=output_root,
                artifact_id="stage7_real_repository_contamination_scan",
                kind="json",
            ),
            _artifact_ref(
                swe_scan_path,
                base_dir=output_root,
                artifact_id="stage7_swebench_like_contamination_scan",
                kind="json",
            ),
        ],
        "tool_pairing": {
            "real_repository": _tool_pairing(real_run_dir),
            "swebench_like": _tool_pairing(swe_run_dir),
        },
        "swebench_like_final_only_policy": {
            "agent_workspace_contains_verifier_patch": False,
            "oracle_hidden_feedback_visible_to_model": False,
            "stage6_final_verifier_reused_as_official_harness": False,
        },
    }
    _write_json(output_root / "v3_agent_loop_integration_report.json", report)
    return output_root


def inspect_v3_agent_loop_integration(
    run_dir: str | Path,
    *,
    report: str | Path,
    assert_complete: bool = False,
) -> str:
    root = Path(run_dir)
    report_path = Path(report)
    failures: list[str] = []
    payload = _read_json_for_inspect(report_path, failures)
    if payload.get("schema_version") != AGENT_LOOP_INTEGRATION_VERSION:
        failures.append("Stage 7 Agent Loop integration report schema_version 不匹配。")
    for role in ("real_repository", "swebench_like"):
        run_payload = payload.get("runs", {}).get(role, {})
        run_path = Path(str(run_payload.get("run_dir", "")))
        _inspect_run(role, run_path, failures)
        if role == "real_repository":
            if run_payload.get("run_outcome") != "success":
                failures.append("真实仓库 Agent Loop run 必须 success。")
            if run_payload.get("final_verifier_status") != "accepted":
                failures.append("真实仓库 Agent Loop run final verifier 必须 accepted。")
            _inspect_docker_status(run_path, failures)
        else:
            final_path = run_path / "v3_swebench_like_final_verifier" / run_payload.get("task_id", "") / "final_verifier_result.json"
            final_payload = _read_json_for_inspect(final_path, failures)
            if not final_payload:
                failures.append("SWE-Bench-like Agent Loop run 缺少 final verifier result。")
            elif final_payload.get("official_harness_report_used") is not False:
                failures.append("SWE-Bench-like Agent Loop final verifier 不能使用 official harness report。")
            if run_payload.get("agent_loop_entered") is not True:
                failures.append("SWE-Bench-like task 必须进入常规 Agent Loop。")
    for scan_ref in payload.get("contamination_scan_refs", []) or []:
        scan_path = _resolve_report_ref(root, scan_ref, failures)
        if scan_path is None:
            continue
        scan_payload = _read_json_for_inspect(scan_path, failures)
        if scan_payload.get("clean") is not True:
            failures.append(f"污染扫描未通过：{scan_ref.get('relative_path')}")
    for role, pairing in (payload.get("tool_pairing") or {}).items():
        if pairing.get("missing_terminal_tool_call_ids"):
            failures.append(f"{role} 存在没有终态 tool result 的 tool call。")
    status = "failed" if failures else "passed"
    result = {
        "schema_version": AGENT_LOOP_INSPECT_VERSION,
        "run_dir": str(root),
        "report": str(report_path),
        "status": status,
        "checks": [] if failures else ["v3_agent_loop_integration=complete"],
        "failures": failures,
    }
    if failures and assert_complete:
        raise ConfigError("V3 Agent Loop integration 检查失败：" + "; ".join(failures))
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)


def scan_v3_run_surfaces(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    denylist = V3ContaminationDenylist()
    surfaces = {
        "prompt": _prompt_payload(run_path),
        "prepared_messages": _prepared_messages_payload(run_path),
        "tool_observation": _tool_observation_payload(run_path),
        "transcript": _transcript_payload(run_path),
        "checkpoint": _optional_json_payloads(run_path, ["checkpoint.json", "checkpoints.json"]),
        "context_compaction_report": _optional_json_payloads(
            run_path,
            ["context_compaction_report.json"],
        ),
        "sft_export": {"status": "not_applicable"},
        "rl_export": {"status": "not_applicable"},
        "preference_export": {"status": "not_applicable"},
        "acceptance_input": {"status": "not_applicable"},
    }
    results = [
        denylist.scan_payload(surface=surface, payload=payload).model_dump(mode="json")
        for surface, payload in surfaces.items()
    ]
    findings = [finding for result in results for finding in result.get("findings", [])]
    return {
        "schema_version": "repo_harness_v3_agent_loop_contamination_scan_v0",
        "run_dir": str(run_path),
        "denylist_version": denylist.schema_version,
        "clean": not findings,
        "surfaces": list(surfaces),
        "results": results,
        "finding_count": len(findings),
        "findings": findings,
    }


def _write_real_replay(path: Path, task_id: str) -> Path:
    payload = {
        "script_id": f"{task_id}_stage7_replay",
        "task_id": task_id,
        "steps": [
            {
                "step_id": "read_calculator",
                "action": "tool_call",
                "tool_call_id": "stage7_read_calculator",
                "tool_name": "read_file",
                "arguments": {"path": "calculator.py"},
                "expected_outcome": {"status": "ok"},
            },
            {
                "step_id": "edit_divide",
                "action": "tool_call",
                "tool_call_id": "stage7_edit_divide",
                "tool_name": "edit_file",
                "arguments": {
                    "path": "calculator.py",
                    "old_text": "def divide(left: int, right: int) -> float:\n    return left / right\n",
                    "new_text": (
                        "def divide(left: int, right: int) -> float:\n"
                        "    if right == 0:\n"
                        "        raise ValueError(\"division by zero\")\n"
                        "    return left / right\n"
                    ),
                },
                "expected_outcome": {"status": "ok"},
            },
            {
                "step_id": "run_public_tests",
                "action": "tool_call",
                "tool_call_id": "stage7_run_tests",
                "tool_name": "run_tests",
                "arguments": {},
                "expected_outcome": {"status": "ok"},
            },
            {
                "step_id": "final",
                "action": "final_answer",
                "assistant_text": "Implemented the divide-by-zero guard and verified the public tests.",
            },
        ],
    }
    _write_yaml(path, payload)
    return path


def _write_real_config(path: Path, *, replay_path: Path, output_dir: Path) -> Path:
    payload = _base_docker_config(output_dir)
    payload.update(
        {
            "run_id_prefix": "v3_stage_07_real",
            "model": {
                "provider": "replay",
                "model_id": "replay-script-v0",
                "replay_script_path": replay_path.as_posix(),
            },
            "runtime": {
                **payload["runtime"],
                "scaffold_id": "simple_react",
                "test_feedback_policy": "structured_public_feedback",
                "feedback_tests_passed_policy": "require_model_final",
                "max_turns": 5,
                "max_tool_calls": 5,
                "max_test_runs": 1,
            },
        }
    )
    _write_yaml(path, payload)
    return path


def _write_swebench_agent_task(
    path: Path,
    *,
    source_root: Path,
    source_entry: dict[str, Any],
    swebench_manifest: Path,
) -> Path:
    original = _read_yaml(_resolve_source_ref(source_root, source_entry["task_definition_ref"]))
    source_checkout = _resolve_source_ref(source_root, source_entry["source_checkout_ref"])
    source_rel = os.path.relpath(source_checkout, start=path.parent)
    original.update(
        {
            "repo": source_rel,
            "repo_source_spec": {
                "source_type": "local_repository",
                "source_path": source_rel,
                "current_commit": original.get("base_commit"),
                "working_tree_clean": True,
                "allow_dirty_snapshot": False,
                "base_commit": original.get("base_commit"),
                "decontamination_status": "fixed_swebench_like_source_materialization",
            },
            "fail_to_pass_tests": [],
            "pass_to_pass_tests": [],
            "metadata": {
                **(original.get("metadata") or {}),
                "v3_agent_loop_projection": True,
                "swebench_like_manifest_path": swebench_manifest.as_posix(),
                "source_materialization_task_ref": source_entry["task_definition_ref"],
            },
        }
    )
    _write_yaml(path, original)
    return path


def _write_swebench_replay(path: Path, task_id: str) -> Path:
    patch = (
        "diff --git a/repo_harness_stage7_marker.txt b/repo_harness_stage7_marker.txt\n"
        "new file mode 100644\n"
        "index 0000000..5aa16c6\n"
        "--- /dev/null\n"
        "+++ b/repo_harness_stage7_marker.txt\n"
        "@@ -0,0 +1 @@\n"
        "+stage7 diagnostic patch\n"
    )
    payload = {
        "script_id": f"{task_id}_stage7_diagnostic_patch",
        "task_id": task_id,
        "steps": [{"step_id": "diagnostic_patch", "action": "patch_action", "patch_text": patch}],
        "expected_outcome": {
            "accepted": False,
            "reason": "diagnostic patch exercises Agent Loop and final verifier without hidden solution material.",
        },
    }
    _write_yaml(path, payload)
    return path


def _write_swebench_config(path: Path, *, replay_path: Path, output_dir: Path) -> Path:
    payload = _base_docker_config(output_dir)
    payload.update(
        {
            "run_id_prefix": "v3_stage_07_swebench",
            "model": {
                "provider": "replay",
                "model_id": "replay-script-v0",
                "replay_script_path": replay_path.as_posix(),
            },
            "runtime": {
                **payload["runtime"],
                "scaffold_id": "single_shot_patch",
                "test_feedback_policy": "disabled",
                "feedback_tests_passed_policy": "stop_immediately",
                "max_turns": 1,
                "max_tool_calls": 0,
                "max_test_runs": 0,
            },
        }
    )
    _write_yaml(path, payload)
    return path


def _base_docker_config(output_dir: Path) -> dict[str, Any]:
    return {
        "runtime": {
            "execution_mode": "docker",
            "permission_mode": "auto",
            "docker_backend": {
                "image_ref": "repo-harness-v3-python:stage2",
                "build_if_missing": True,
                "requested_container_platform": "linux/arm64",
                "network_policy": "deny_agent_run",
                "mount_policy": "workspace_read_write_tmp_only",
                "cleanup_policy": "remove_containers_keep_images",
            },
        },
        "workspace": {
            "output_dir": output_dir.as_posix(),
            "keep_workspace": True,
            "default_command_timeout_sec": 120,
            "max_tool_output_chars": 12000,
        },
        "evaluation": {"concurrency": 1},
        "swebench_like": {"max_workers": 1},
    }


def _run_summary(run_dir: Path) -> dict[str, Any]:
    metrics = _read_json(run_dir / "metrics.json")
    baseline = _read_json(run_dir / "baseline.json")
    task = _read_json(run_dir / "task.yaml")
    return {
        "run_dir": run_dir.as_posix(),
        "run_id": run_dir.name,
        "task_id": str(task.get("id") or baseline.get("task_id")),
        "baseline_status": baseline.get("status"),
        "run_outcome": metrics.get("run_outcome"),
        "final_verifier_status": metrics.get("final_verifier_status"),
        "agent_loop_entered": _agent_loop_entered(run_dir),
        "has_final_patch": (run_dir / "final.patch").exists(),
        "has_run_metadata": (run_dir / "run_metadata.json").exists(),
        "docker_backend_status_ref": "docker_backend_status.json",
    }


def _agent_loop_entered(run_dir: Path) -> bool:
    return any(event.get("event_type") == "model_call_started" for event in read_jsonl(run_dir / "events.jsonl"))


def _inspect_run(role: str, run_path: Path, failures: list[str]) -> None:
    if not run_path.exists():
        failures.append(f"{role} run directory 不存在：{run_path}")
        return
    for name in ("transcript.jsonl", "events.jsonl", "artifacts.json", "run_config_facts.json"):
        if not (run_path / name).exists():
            failures.append(f"{role} run 缺少必需轨迹文件：{name}")
    if not (run_path / "run_metadata.json").exists():
        failures.append(f"{role} completed run 缺少 run_metadata.json")
    if not (run_path / "final.patch").exists():
        failures.append(f"{role} run 缺少 final.patch")
    artifact_errors = verify_artifact_manifest(run_path)
    failures.extend(f"{role} artifact manifest: {error}" for error in artifact_errors)


def _inspect_docker_status(run_path: Path, failures: list[str]) -> None:
    status = _read_json_for_inspect(run_path / "docker_backend_status.json", failures)
    if status.get("mode") != "docker_backend" or status.get("status") != "passed":
        failures.append("真实仓库 run 的 Docker backend status 必须 passed。")
    if not status.get("container_execution_facts_refs"):
        failures.append("真实仓库 run 必须记录 container execution facts。")


def _tool_pairing(run_dir: Path) -> dict[str, Any]:
    events = read_jsonl(run_dir / "events.jsonl")
    requested = [
        event.get("data", {}).get("tool_call_id")
        for event in events
        if event.get("event_type") == "tool_requested"
    ]
    terminal = {
        event.get("data", {}).get("tool_call_id")
        for event in events
        if event.get("event_type")
        in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
    }
    missing = sorted(str(call_id) for call_id in requested if call_id and call_id not in terminal)
    return {
        "requested_tool_call_count": len([call_id for call_id in requested if call_id]),
        "terminal_tool_result_count": len([call_id for call_id in terminal if call_id]),
        "missing_terminal_tool_call_ids": missing,
    }


def _prompt_payload(run_path: Path) -> dict[str, Any]:
    prepared = _prepared_artifact_payloads(run_path)
    if not prepared:
        return {"messages": []}
    messages = [
        message
        for message in prepared[0].get("messages", [])
        if message.get("role") in {"system", "user"}
    ]
    return {"messages": messages}


def _prepared_messages_payload(run_path: Path) -> dict[str, Any]:
    return {"prepared_messages": _prepared_artifact_payloads(run_path)}


def _tool_observation_payload(run_path: Path) -> dict[str, Any]:
    observations = []
    for prepared in _prepared_artifact_payloads(run_path):
        observations.extend(
            message for message in prepared.get("messages", []) if message.get("role") == "tool"
        )
    observations.extend(
        {
            "message_id": record.get("message_id"),
            "content_preview": record.get("content_preview"),
        }
        for record in read_jsonl(run_path / "transcript.jsonl")
        if record.get("role") == "tool" and record.get("model_visible") is True
    )
    return {"tool_observations": observations}


def _transcript_payload(run_path: Path) -> dict[str, Any]:
    return {
        "records": [
            {
                "message_id": record.get("message_id"),
                "role": record.get("role"),
                "content_preview": record.get("content_preview"),
            }
            for record in read_jsonl(run_path / "transcript.jsonl")
            if record.get("model_visible") is True
        ]
    }


def _prepared_artifact_payloads(run_path: Path) -> list[dict[str, Any]]:
    manifest = _read_json(run_path / "artifacts.json")
    payloads = []
    for artifact in manifest.get("artifacts", []):
        if artifact.get("kind") != "prepared_messages":
            continue
        payloads.append(_read_json(run_path / artifact["relative_path"]))
    return payloads


def _optional_json_payloads(run_path: Path, names: list[str]) -> dict[str, Any]:
    payloads = []
    for name in names:
        path = run_path / name
        if path.exists():
            payloads.append(_read_json(path))
    return {"status": "not_applicable" if not payloads else "present", "payloads": payloads}


def _resolve_source_ref(source_root: Path, ref_payload: dict[str, Any]) -> Path:
    relative = Path(ref_payload["relative_path"])
    if relative.is_absolute():
        raise ConfigError(f"Stage 7 source ref 不能是绝对路径：{relative}")
    path = source_root / relative
    if not path.exists():
        raise ConfigError(f"Stage 7 source ref 不存在：{relative}")
    return path


def _resolve_report_ref(root: Path, ref_payload: dict[str, Any], failures: list[str]) -> Path | None:
    if not isinstance(ref_payload, dict):
        failures.append("report ArtifactRef 无效。")
        return None
    try:
        ref = ArtifactRef.model_validate(ref_payload)
    except Exception as exc:
        failures.append(f"report ArtifactRef schema 无效：{exc}")
        return None
    relative = Path(ref.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        failures.append(f"report ArtifactRef relative_path 不安全：{ref.relative_path}")
        return None
    path = root / relative
    if not path.exists():
        failures.append(f"report ArtifactRef 路径不存在：{ref.relative_path}")
        return None
    actual_sha = compute_file_sha256(path)
    if actual_sha != ref.sha256:
        failures.append(f"report ArtifactRef sha256 不匹配：{ref.relative_path}")
    return path


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


def _read_json_for_inspect(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        return _read_json(path)
    except Exception as exc:
        failures.append(str(exc))
        return {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"JSON 文件不存在：{path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON 文件无效：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"JSON 顶层必须是 object：{path}")
    return payload


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"YAML 文件不存在：{path}") from exc
    if not isinstance(payload, dict):
        raise ConfigError(f"YAML 顶层必须是 object：{path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
