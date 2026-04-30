"""Training export implementations for recorded run directories."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Literal

from repo_harness.errors import ExportError
from repo_harness.export.schemas import ExportPolicy, ExportRecord
from repo_harness.schema_versions import EXPORT_SCHEMA_VERSION
from repo_harness.trajectory import read_jsonl

ExportFormat = Literal["sft_jsonl", "rl_jsonl", "preference_jsonl"]


def export_run_or_runs(
    run_dir_or_runs_dir: str | Path,
    *,
    export_format: ExportFormat,
) -> Path:
    path = Path(run_dir_or_runs_dir)
    if export_format == "sft_jsonl":
        return export_sft_jsonl(path)
    if export_format == "rl_jsonl":
        return export_rl_jsonl(path)
    if export_format == "preference_jsonl":
        return export_preference_jsonl(path)
    raise ExportError(f"不支持的导出格式：{export_format}")


def export_sft_jsonl(run_dir: str | Path) -> Path:
    run_path = _require_run_dir(run_dir)
    record = _build_sft_record(run_path)
    output_path = run_path / "exports" / "sft.jsonl"
    _write_jsonl(output_path, [record.model_dump(mode="json")])
    return output_path


def export_rl_jsonl(run_dir: str | Path) -> Path:
    run_path = _require_run_dir(run_dir)
    record = _build_rl_record(run_path)
    output_path = run_path / "exports" / "rl.jsonl"
    _write_jsonl(output_path, [record.model_dump(mode="json")])
    return output_path


def export_preference_jsonl(runs_dir: str | Path) -> Path:
    root = Path(runs_dir)
    if not root.exists() or not root.is_dir():
        raise ExportError(f"runs directory 不存在：{root}")
    records = _build_preference_records(root)
    output_dir = root / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not records:
        skipped_path = output_dir / "preference_skipped.json"
        skipped_path.write_text(
            json.dumps(
                {
                    "schema_version": EXPORT_SCHEMA_VERSION,
                    "format": "preference_jsonl",
                    "filter_status": "skipped",
                    "reason": "not_enough_runs_for_same_task",
                    "export_policy_version": ExportPolicy().export_policy_version,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return skipped_path
    output_path = output_dir / "preference.jsonl"
    _write_jsonl(output_path, [record.model_dump(mode="json") for record in records])
    return output_path


def _build_sft_record(run_path: Path) -> ExportRecord:
    transcript = read_jsonl(run_path / "transcript.jsonl")
    prepared_observations = _prepared_tool_observations(run_path)
    messages: list[dict[str, Any]] = []
    loss_mask: list[int] = []
    observation_mask: list[int] = []
    trainable_messages: list[int] = []
    for record in transcript:
        if not record.get("model_visible", False):
            continue
        message = _message_from_transcript(record, prepared_observations)
        if message is None:
            continue
        message = _sanitize_for_export(message)
        messages.append(message)
        is_assistant_target = record.get("role") == "assistant" and bool(record.get("trainable"))
        is_tool_observation = record.get("role") == "tool"
        if is_assistant_target:
            trainable_messages.append(len(messages) - 1)
        loss_mask.append(1 if is_assistant_target else 0)
        observation_mask.append(1 if is_tool_observation else 0)

    metadata = _safe_metadata(run_path, export_format="sft_jsonl")
    payload = {
        "messages": messages,
        "trainable_messages": trainable_messages,
        "loss_mask": loss_mask,
        "observation_mask": observation_mask,
        "target": {
            "final_patch": _read_text_if_exists(run_path / "final.patch"),
            "termination_summary": _read_text_if_exists(run_path / "summary.md"),
        },
        "verifier": _safe_verifier_summary(run_path),
        "reward_metadata_ref": _relative_ref(run_path, "reward.json", "reward_metadata"),
        "final_verifier_ref": _relative_ref(run_path, "verifier.json", "final_verifier_result"),
        "prepared_message_refs": _prepared_message_artifacts(run_path),
        "content_replacement_state_refs": _content_replacement_state_artifacts(run_path),
    }
    return ExportRecord(
        sample_id=f"{run_path.name}_sft",
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=_sanitize_for_export(payload),
        metadata=metadata,
        invalid_for_training=_invalid_for_training(run_path),
        invalid_reason=_invalid_reason(run_path),
    )


def _build_rl_record(run_path: Path) -> ExportRecord:
    metadata = _safe_metadata(run_path, export_format="rl_jsonl")
    reward = _read_json_if_exists(run_path / "reward.json")
    formal_final_reason = _formal_final_verifier_invalid_reason(run_path)
    payload = {
        "prompt": _prompt_from_prepared_messages(run_path),
        "trajectory": _trajectory_from_events(run_path),
        "reward": float(reward.get("final_reward", 0.0)) if reward else 0.0,
        "reward_metadata": {
            "reward_version": reward.get("reward_version") if reward else None,
            "reward_metadata_ref": _relative_ref(run_path, "reward.json", "reward_metadata"),
            "source": (
                "formal_final_verifier"
                if formal_final_reason is None
                else "missing_or_non_formal_final_verifier"
            ),
            "formal_final_verifier": formal_final_reason is None,
        },
        "final_verifier_ref": _relative_ref(run_path, "verifier.json", "final_verifier_result"),
        "prepared_message_refs": _prepared_message_artifacts(run_path),
        "content_replacement_state_refs": _content_replacement_state_artifacts(run_path),
    }
    return ExportRecord(
        sample_id=f"{run_path.name}_rl",
        task_id=_task_id(run_path),
        source_run_id=run_path.name,
        payload=_sanitize_for_export(payload),
        metadata=metadata,
        invalid_for_training=_invalid_for_training(run_path),
        invalid_reason=_invalid_reason(run_path),
    )


def _build_preference_records(root: Path) -> list[ExportRecord]:
    runs = [_run_score(run_dir) for run_dir in sorted(root.iterdir()) if _looks_like_run_dir(run_dir)]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        grouped.setdefault(run["task_id"], []).append(run)
    records: list[ExportRecord] = []
    for task_id, task_runs in grouped.items():
        if len(task_runs) < 2:
            continue
        ranked = sorted(
            task_runs,
            key=lambda run: (run["reward"], _outcome_rank(run.get("run_outcome"))),
            reverse=True,
        )
        chosen, rejected = ranked[0], ranked[-1]
        chosen_score = (chosen["reward"], _outcome_rank(chosen.get("run_outcome")))
        rejected_score = (rejected["reward"], _outcome_rank(rejected.get("run_outcome")))
        if chosen["run_id"] == rejected["run_id"] or chosen_score == rejected_score:
            continue
        payload = {
            "chosen": _preference_side(chosen),
            "rejected": _preference_side(rejected),
            "reason": "higher_final_reward_and_verifier_outcome",
        }
        metadata = {
            "export_policy_version": ExportPolicy().export_policy_version,
            "pairing_policy": "same_task_rollout_ranking_v0",
            "chosen_verifier_result_ref": _relative_ref(
                Path(chosen["run_dir"]), "verifier.json", "final_verifier_result"
            ),
            "rejected_verifier_result_ref": _relative_ref(
                Path(rejected["run_dir"]), "verifier.json", "final_verifier_result"
            ),
        }
        records.append(
            ExportRecord(
                sample_id=f"{task_id}_preference_0001",
                task_id=task_id,
                source_run_id=f"{chosen['run_id']}__vs__{rejected['run_id']}",
                payload=_sanitize_for_export(payload),
                metadata=_sanitize_for_export(metadata),
            )
        )
    return records


def _message_from_transcript(
    record: dict[str, Any],
    prepared_observations: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    role = record.get("role")
    content = record.get("content_preview", "")
    if role in {"system", "user"}:
        return {"role": role, "content": content}
    if role == "assistant":
        tool_calls = _parse_tool_calls(content)
        if tool_calls:
            return {"role": "assistant", "content": None, "tool_calls": tool_calls}
        return {"role": "assistant", "content": content}
    if role == "tool":
        tool_call_id = record.get("tool_call_id")
        prepared = prepared_observations.get(str(tool_call_id))
        if prepared is not None:
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": prepared["content"],
                "artifact_refs": prepared["artifact_refs"],
                "observation_source": "prepared_messages",
                "context_revision": prepared["context_revision"],
                "prepared_messages_ref": prepared["prepared_messages_ref"],
                "content_replacement_state_ref": prepared["content_replacement_state_ref"],
                "context_replacement": prepared["context_replacement"],
            }
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
            "artifact_refs": record.get("content_artifact_refs", []),
            "observation_source": "transcript_preview_without_followup_context",
        }
    return None


def _parse_tool_calls(content: str) -> list[dict[str, Any]]:
    try:
        parsed = ast.literal_eval(content)
    except (SyntaxError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    tool_calls = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        tool_calls.append(
            {
                "tool_call_id": item.get("tool_call_id"),
                "tool_name": item.get("tool_name"),
                "arguments": item.get("arguments", {}),
                "turn": item.get("turn"),
            }
        )
    return tool_calls


def _prompt_from_prepared_messages(run_path: Path) -> dict[str, Any]:
    prepared = _prepared_message_artifacts(run_path)
    if not prepared:
        return {"messages": []}
    first = _read_json(run_path / prepared[0]["relative_path"])
    messages = [
        message
        for message in first.get("messages", [])
        if message.get("role") in {"system", "user"}
    ]
    return _sanitize_for_export(
        {
            "messages": messages,
            "prepared_messages_ref": prepared[0],
            "context_revision": first.get("context_revision"),
            "model_input_hash": first.get("model_input_hash"),
            "content_replacement_state_ref": first.get("content_replacement_state_ref"),
        }
    )


def _trajectory_from_events(run_path: Path) -> list[dict[str, Any]]:
    events = read_jsonl(run_path / "events.jsonl")
    prepared_observations = _prepared_tool_observations(run_path)
    results_by_call = {
        event.get("data", {}).get("tool_call_id"): event
        for event in events
        if event.get("event_type")
        in {"tool_completed", "tool_denied", "tool_failed", "tool_timeout", "tool_interrupted"}
    }
    trajectory = []
    for event in events:
        if event.get("event_type") != "tool_requested":
            continue
        call = event.get("data", {})
        result = results_by_call.get(call.get("tool_call_id"))
        observation = {}
        if result is not None:
            data = result.get("data", {})
            prepared = prepared_observations.get(str(call.get("tool_call_id")))
            if prepared is not None:
                observation = {
                    "status": data.get("status"),
                    "preview": prepared["content"],
                    "truncated": data.get("truncated", False),
                    "artifact_refs": prepared["artifact_refs"],
                    "error_type": data.get("error_type"),
                    "observation_source": "prepared_messages",
                    "prepared_messages_ref": prepared["prepared_messages_ref"],
                    "content_replacement_state_ref": prepared["content_replacement_state_ref"],
                    "context_replacement": prepared["context_replacement"],
                }
            else:
                observation = {
                    "status": data.get("status"),
                    "preview": data.get("content_preview", ""),
                    "truncated": data.get("truncated", False),
                    "artifact_refs": data.get("artifact_refs", []),
                    "error_type": data.get("error_type"),
                    "observation_source": "event_preview_without_followup_context",
                }
        trajectory.append(
            _sanitize_for_export(
                {
                    "turn": event.get("turn"),
                    "context_revision": _context_revision_for_turn(events, event.get("turn")),
                    "action": {
                        "type": "tool_call",
                        "tool_call_id": call.get("tool_call_id"),
                        "tool_name": call.get("tool_name"),
                        "arguments": call.get("arguments", {}),
                    },
                    "observation": observation,
                }
            )
        )
    return trajectory


def _context_revision_for_turn(events: list[dict[str, Any]], turn: int | None) -> int | None:
    for event in events:
        if event.get("event_type") == "context_prepared" and event.get("turn") == turn:
            return event.get("data", {}).get("context_revision")
    return None


def _safe_metadata(run_path: Path, *, export_format: str) -> dict[str, Any]:
    task = _read_json_if_exists(run_path / "task.yaml")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    events = read_jsonl(run_path / "events.jsonl")
    first_model = next((event for event in events if event.get("event_type") == "model_call_completed"), {})
    model_data = first_model.get("data", {})
    return _sanitize_for_export(
        {
            "export_policy_version": ExportPolicy().export_policy_version,
            "export_format": export_format,
            "source_run_id": run_path.name,
            "model_id": model_data.get("model_id"),
            "task_version": task.get("task_version"),
            "dataset_name": task.get("dataset_name"),
            "dataset_split": task.get("dataset_split"),
            "source_kind": task.get("source_kind"),
            "decontamination_status": task.get("decontamination", {}).get("status"),
            "repo_base_commit": task.get("base_commit"),
            "scaffold_id": metrics.get("interaction_efficiency", {}).get("scaffold_id", "simple_react"),
            "permission_mode": _initial_user_field(run_path, "permission_mode"),
            "execution_mode": _initial_user_field(run_path, "execution_mode"),
            "schema_version": EXPORT_SCHEMA_VERSION,
        }
    )


def _initial_user_field(run_path: Path, key: str) -> Any:
    prepared = _prepared_message_artifacts(run_path)
    if not prepared:
        return None
    payload = _read_json(run_path / prepared[0]["relative_path"])
    for message in payload.get("messages", []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, dict):
            return content.get(key)
    return None


def _safe_verifier_summary(run_path: Path) -> dict[str, Any]:
    verifier = _read_json_if_exists(run_path / "verifier.json")
    return {
        "accepted": verifier.get("accepted"),
        "pass_ratio": verifier.get("pass_ratio"),
        "error_type": verifier.get("error_type"),
        "verifier_stage": verifier.get("verifier_stage"),
    }


def _invalid_for_training(run_path: Path) -> bool:
    metrics = _read_json_if_exists(run_path / "metrics.json")
    reward = _read_json_if_exists(run_path / "reward.json")
    return bool(
        reward.get("invalid_for_training")
        or _formal_final_verifier_invalid_reason(run_path) is not None
        or metrics.get("run_outcome") in {"invalid_task", "flaky_task", "interrupted", "inconclusive"}
        or metrics.get("final_verifier_status") in {"timeout", "error"}
    )


def _invalid_reason(run_path: Path) -> str | None:
    if not _invalid_for_training(run_path):
        return None
    metrics = _read_json_if_exists(run_path / "metrics.json")
    reward = _read_json_if_exists(run_path / "reward.json")
    return (
        reward.get("invalid_reason")
        or _formal_final_verifier_invalid_reason(run_path)
        or metrics.get("run_outcome")
        or "filtered_by_export_policy"
    )


def _formal_final_verifier_invalid_reason(run_path: Path) -> str | None:
    verifier = _read_json_if_exists(run_path / "verifier.json")
    reward = _read_json_if_exists(run_path / "reward.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    final_mode = metrics.get("interaction_efficiency", {}).get("final_verifier_mode")
    if not verifier:
        return "missing_formal_final_verifier"
    if verifier.get("verifier_stage") != "final":
        return "non_final_verifier_reward_source"
    if final_mode != "strict_patch_replay":
        return "non_strict_patch_replay_reward_source"
    if not reward:
        return "missing_reward_metadata"
    return None


def _run_score(run_path: Path) -> dict[str, Any]:
    reward = _read_json_if_exists(run_path / "reward.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    return {
        "run_id": run_path.name,
        "run_dir": str(run_path),
        "task_id": _task_id(run_path),
        "reward": float(reward.get("final_reward", 0.0)) if reward else 0.0,
        "run_outcome": metrics.get("run_outcome"),
        "final_verifier_status": metrics.get("final_verifier_status"),
    }


def _preference_side(run: dict[str, Any]) -> dict[str, Any]:
    run_path = Path(run["run_dir"])
    return {
        "source_run_id": run["run_id"],
        "reward": run["reward"],
        "run_outcome": run["run_outcome"],
        "final_verifier_status": run["final_verifier_status"],
        "final_patch": _read_text_if_exists(run_path / "final.patch"),
    }


def _prepared_tool_observations(run_path: Path) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    for prepared_ref in _prepared_message_artifacts(run_path):
        payload = _read_json_if_exists(run_path / prepared_ref["relative_path"])
        state_ref = payload.get("content_replacement_state_ref")
        for message in payload.get("messages", []):
            if message.get("role") != "tool":
                continue
            tool_call_id = str(message.get("tool_call_id") or "")
            if not tool_call_id or tool_call_id in observations:
                continue
            observations[tool_call_id] = {
                "content": str(message.get("content", "")),
                "artifact_refs": message.get("artifact_refs", []),
                "context_revision": payload.get("context_revision"),
                "prepared_messages_ref": prepared_ref,
                "content_replacement_state_ref": state_ref,
                "context_replacement": bool(message.get("context_replacement", False)),
            }
    return observations


def _prepared_message_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _read_json_if_exists(run_path / "artifacts.json")
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "prepared_messages"
    ]


def _content_replacement_state_artifacts(run_path: Path) -> list[dict[str, Any]]:
    manifest = _read_json_if_exists(run_path / "artifacts.json")
    return [
        artifact
        for artifact in manifest.get("artifacts", [])
        if artifact.get("kind") == "content_replacement_state"
    ]


def _task_id(run_path: Path) -> str:
    baseline = _read_json_if_exists(run_path / "baseline.json")
    if baseline.get("task_id"):
        return str(baseline["task_id"])
    task = _read_json_if_exists(run_path / "task.yaml")
    if task.get("id"):
        return str(task["id"])
    events = read_jsonl(run_path / "events.jsonl")
    for event in events:
        if event.get("task_id"):
            return str(event["task_id"])
    return "unknown_task"


def _relative_ref(run_path: Path, relative_path: str, kind: str) -> dict[str, Any]:
    path = run_path / relative_path
    return {
        "kind": kind,
        "relative_path": relative_path,
        "exists": path.exists(),
    }


def _outcome_rank(run_outcome: str | None) -> int:
    return {
        "success": 4,
        "failed": 3,
        "inconclusive": 2,
        "interrupted": 1,
        "invalid_task": 0,
        "flaky_task": 0,
    }.get(run_outcome or "", 0)


def _require_run_dir(run_dir: str | Path) -> Path:
    run_path = Path(run_dir)
    if not _looks_like_run_dir(run_path):
        raise ExportError(f"不是有效 run directory：{run_path}")
    return run_path


def _looks_like_run_dir(path: Path) -> bool:
    return path.is_dir() and (path / "metrics.json").exists() and (path / "transcript.jsonl").exists()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)


def _read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return _sanitize_text(path.read_text(encoding="utf-8"))


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _sanitize_for_export(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_export(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_export(nested) for nested in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _sanitize_text(text: str) -> str:
    text = re.sub(
        r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]{8,}",
        r"\1<REDACTED_CREDENTIAL>",
        text,
    )
    text = re.sub(
        r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]{8,}",
        r"\1<REDACTED_CREDENTIAL>",
        text,
    )
    text = re.sub(r"\bsk-[A-Za-z0-9][A-Za-z0-9_-]{8,}\b", "<REDACTED_CREDENTIAL>", text)
    text = re.sub(
        r"(?i)\b(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s,}\]]+",
        lambda match: f"{match.group(1)}=<REDACTED_CREDENTIAL>",
        text,
    )
    text = re.sub(r"/Users/[^\s,'\"})\]]+", "<REDACTED_LOCAL_PATH>", text)
    text = re.sub(r"/private/[^\s,'\"})\]]+", "<REDACTED_LOCAL_PATH>", text)
    if text.startswith("/"):
        return "<REDACTED_LOCAL_PATH>"
    return text
