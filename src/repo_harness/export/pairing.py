"""Preference pair hard gates and compare scope helpers."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_harness.export.schemas import CompareScope, ExportPolicy, PairingPolicy
from repo_harness.trajectory import verify_artifact_manifest

OPTIONAL_COMPARE_FIELDS = {"source_archive_sha256"}


@dataclass(frozen=True)
class PairCandidate:
    run_id: str
    run_dir: Path
    task_id: str
    reward: float | None
    run_outcome: str | None
    final_verifier_status: str | None
    facts: dict[str, Any]
    metadata_summary: dict[str, Any]


@dataclass(frozen=True)
class PairDecision:
    chosen: PairCandidate
    rejected: PairCandidate
    allowed: bool
    blocked_reasons: tuple[str, ...] = ()
    chosen_score: tuple[float, int] | None = None
    rejected_score: tuple[float, int] | None = None


@dataclass(frozen=True)
class PairingSummary:
    candidate_run_count: int
    candidate_pair_count: int
    blocked_pair_count: int
    blocked_reason_distribution: dict[str, int]
    pairing_policy_version: str
    compare_scope: dict[str, Any]
    decisions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class PairingResult:
    decisions: list[PairDecision]
    summary: PairingSummary


def load_pairing_policy(path: str | Path | None) -> PairingPolicy:
    if path is None:
        return PairingPolicy()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if "compare_scope" in payload:
        return PairingPolicy.model_validate(payload)
    return PairingPolicy(compare_scope=CompareScope.model_validate(payload))


def build_preference_pairing(
    run_paths: list[Path],
    *,
    pairing_policy: PairingPolicy,
    export_policy: ExportPolicy,
) -> PairingResult:
    candidates = [_candidate_from_run(run_path, export_policy=export_policy) for run_path in run_paths]
    grouped: dict[str, list[PairCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.task_id, []).append(candidate)

    decisions: list[PairDecision] = []
    for task_candidates in grouped.values():
        if len(task_candidates) < 2:
            continue
        for index, left in enumerate(task_candidates):
            for right in task_candidates[index + 1:]:
                decisions.append(_decide_pair(left, right, pairing_policy=pairing_policy))
    return PairingResult(
        decisions=decisions,
        summary=_summary(candidates, decisions, pairing_policy=pairing_policy),
    )


def _candidate_from_run(run_path: Path, *, export_policy: ExportPolicy) -> PairCandidate:
    reward = _read_json_if_exists(run_path / "reward.json")
    metrics = _read_json_if_exists(run_path / "metrics.json")
    baseline = _read_json_if_exists(run_path / "baseline.json")
    config = _read_json_if_exists(run_path / "run_config_facts.json")
    facts = _compare_facts(run_path, config=config, baseline=baseline, export_policy=export_policy)
    return PairCandidate(
        run_id=run_path.name,
        run_dir=run_path,
        task_id=str(facts.get("task_id") or baseline.get("task_id") or "unknown_task"),
        reward=float(reward["final_reward"]) if "final_reward" in reward else None,
        run_outcome=metrics.get("run_outcome"),
        final_verifier_status=metrics.get("final_verifier_status"),
        facts=facts,
        metadata_summary={
            "run_id": run_path.name,
            "task_id": facts.get("task_id"),
            "task_version": facts.get("task_version"),
            "base_commit": facts.get("base_commit"),
            "source_archive_sha256": facts.get("source_archive_sha256"),
            "environment_spec_hash": facts.get("environment_spec_hash"),
            "dependency_state_policy": facts.get("dependency_state_policy"),
            "execution_mode": facts.get("execution_mode"),
            "verifier_name": facts.get("verifier_name"),
            "verifier_version": facts.get("verifier_version"),
            "reward_formula_version": facts.get("reward_formula_version"),
            "final_verifier_mode": facts.get("final_verifier_mode"),
            "tool_schema_snapshot_hash": facts.get("tool_schema_snapshot_hash"),
            "tool_order": facts.get("tool_order"),
            "tool_parser_version": facts.get("tool_parser_version"),
            "tool_result_format_version": facts.get("tool_result_format_version"),
            "context_policy_version": facts.get("context_policy_version"),
            "prompt_template_version": facts.get("prompt_template_version"),
            "model_provider": facts.get("model_provider"),
            "model_id": facts.get("model_id"),
            "temperature": facts.get("temperature"),
            "max_output_tokens": facts.get("max_output_tokens"),
            "scaffold_id": facts.get("scaffold_id"),
            "scaffold_version": facts.get("scaffold_version"),
            "allowed_tools_policy": facts.get("allowed_tools_policy"),
            "phase_policy": facts.get("phase_policy"),
            "turn_budget": facts.get("turn_budget"),
            "tool_budget": facts.get("tool_budget"),
            "test_budget": facts.get("test_budget"),
            "task_timeout": facts.get("task_timeout"),
            "reward": reward.get("final_reward"),
            "run_outcome": metrics.get("run_outcome"),
            "final_verifier_status": metrics.get("final_verifier_status"),
        },
    )


def _compare_facts(
    run_path: Path,
    *,
    config: dict[str, Any],
    baseline: dict[str, Any],
    export_policy: ExportPolicy,
) -> dict[str, Any]:
    environment = config.get("environment_fingerprint", {})
    workspace_execution = environment.get("workspace_execution", {})
    workspace_backend = workspace_execution.get("workspace_backend", {})
    execution_mode = workspace_backend.get("execution_mode", {})
    source_checkout = workspace_execution.get("source_checkout", {})
    tool_protocol = config.get("tool_protocol", {})
    return {
        "task_id": config.get("task_id") or baseline.get("task_id"),
        "task_version": config.get("task_version"),
        "base_commit": config.get("base_commit") or source_checkout.get("base_commit"),
        "source_archive_sha256": (
            config.get("source_archive_sha256")
            or source_checkout.get("source_archive_sha256")
        ),
        "environment_spec_hash": environment.get("environment_spec_hash")
        or workspace_execution.get("environment_spec_hash"),
        "dependency_state_policy": _dependency_state_policy(workspace_execution),
        "execution_mode": execution_mode.get("resolved_execution_mode") or workspace_backend.get("backend"),
        "verifier_name": config.get("verifier_name"),
        "verifier_version": config.get("verifier_version"),
        "reward_formula_version": config.get("reward_formula_version"),
        "final_verifier_mode": config.get("final_verifier_mode"),
        "tool_schema_snapshot_hash": tool_protocol.get("tool_schema_snapshot_sha256"),
        "tool_order": tool_protocol.get("tool_order"),
        "tool_parser_version": tool_protocol.get("tool_parser_version"),
        "tool_result_format_version": tool_protocol.get("tool_result_format_version"),
        "context_policy_version": config.get("context_policy_version"),
        "prompt_template_version": config.get("prompt_template_version"),
        "export_policy_version": export_policy.export_policy_version,
        "scaffold_id": config.get("scaffold_id"),
        "scaffold_version": config.get("scaffold_version"),
        "allowed_tools_policy": config.get("allowed_tools_policy"),
        "phase_policy": config.get("phase_policy"),
        "model_provider": config.get("provider"),
        "model_id": config.get("model_id"),
        "temperature": config.get("temperature"),
        "max_output_tokens": config.get("max_output_tokens"),
        "turn_budget": config.get("max_turns"),
        "tool_budget": config.get("max_tool_calls"),
        "test_budget": config.get("max_test_runs"),
        "task_timeout": config.get("task_timeout_sec"),
    }


def _decide_pair(
    left: PairCandidate,
    right: PairCandidate,
    *,
    pairing_policy: PairingPolicy,
) -> PairDecision:
    blocked: list[str] = []
    blocked.extend(_precondition_blockers(left))
    blocked.extend(_precondition_blockers(right))
    blocked.extend(_compare_blockers(left, right, pairing_policy.compare_scope))
    ranked = sorted(
        [left, right],
        key=lambda candidate: (_reward_score(candidate), _outcome_rank(candidate.run_outcome)),
        reverse=True,
    )
    chosen, rejected = ranked[0], ranked[-1]
    chosen_score = (_reward_score(chosen), _outcome_rank(chosen.run_outcome))
    rejected_score = (_reward_score(rejected), _outcome_rank(rejected.run_outcome))
    if chosen.reward is not None and rejected.reward is not None and chosen.reward == rejected.reward:
        blocked.append("reward_tie")
    blocked_reasons = tuple(sorted(set(blocked)))
    return PairDecision(
        chosen=chosen,
        rejected=rejected,
        allowed=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        chosen_score=chosen_score,
        rejected_score=rejected_score,
    )


def _precondition_blockers(candidate: PairCandidate) -> list[str]:
    blocked: list[str] = []
    if candidate.reward is None:
        blocked.append("missing_reward")
    verifier = _read_json_if_exists(candidate.run_dir / "verifier.json")
    metrics = _read_json_if_exists(candidate.run_dir / "metrics.json")
    if not verifier:
        blocked.append("missing_formal_final_verifier")
    elif verifier.get("verifier_stage") != "final":
        blocked.append("non_formal_reward_source")
    elif metrics.get("interaction_efficiency", {}).get("final_verifier_mode") != "strict_patch_replay":
        blocked.append("non_formal_reward_source")
    if verify_artifact_manifest(candidate.run_dir):
        blocked.append("artifact_manifest_invalid")
    if not candidate.facts.get("tool_schema_snapshot_hash"):
        blocked.append("tool_schema_snapshot_mismatch")
    return blocked


def _compare_blockers(
    left: PairCandidate,
    right: PairCandidate,
    compare_scope: CompareScope,
) -> list[str]:
    blocked: list[str] = []
    controlled = set(compare_scope.controlled_sampling_variables)
    experimental = set(compare_scope.experimental_variables)
    for field_name in compare_scope.canonical_key_fields:
        left_value = left.facts.get(field_name)
        right_value = right.facts.get(field_name)
        if field_name in controlled:
            continue
        if left_value == right_value and (
            left_value is not None or field_name in OPTIONAL_COMPARE_FIELDS
        ):
            continue
        if field_name in experimental:
            if not compare_scope.training_export_allowed:
                blocked.append("experimental_variable_not_training_approved")
            continue
        blocked.append(_field_blocked_reason(field_name))
    return blocked


def _field_blocked_reason(field_name: str) -> str:
    if field_name in {"tool_schema_snapshot_hash", "tool_order", "tool_parser_version", "tool_result_format_version"}:
        return "tool_schema_snapshot_mismatch"
    if field_name in {"context_policy_version", "prompt_template_version"}:
        return "context_policy_mismatch"
    if field_name in {"turn_budget", "tool_budget", "test_budget", "task_timeout", "max_output_tokens"}:
        return "budget_mismatch"
    return "compare_key_mismatch"


def _summary(
    candidates: list[PairCandidate],
    decisions: list[PairDecision],
    *,
    pairing_policy: PairingPolicy,
) -> PairingSummary:
    reason_counts: Counter[str] = Counter()
    for decision in decisions:
        reason_counts.update(decision.blocked_reasons)
    return PairingSummary(
        candidate_run_count=len(candidates),
        candidate_pair_count=len(decisions),
        blocked_pair_count=sum(1 for decision in decisions if not decision.allowed),
        blocked_reason_distribution=dict(sorted(reason_counts.items())),
        pairing_policy_version=pairing_policy.pairing_policy_version,
        compare_scope=pairing_policy.compare_scope.model_dump(mode="json"),
        decisions=[
            {
                "chosen_run_id": decision.chosen.run_id,
                "rejected_run_id": decision.rejected.run_id,
                "allowed": decision.allowed,
                "blocked_reasons": list(decision.blocked_reasons),
                "chosen_metadata": decision.chosen.metadata_summary,
                "rejected_metadata": decision.rejected.metadata_summary,
            }
            for decision in decisions
        ],
    )


def _dependency_state_policy(workspace_execution: dict[str, Any]) -> str | None:
    if workspace_execution.get("dependency_state_ref"):
        return "artifact_backed"
    setup_hash = workspace_execution.get("setup_artifact_hash")
    if setup_hash:
        return f"setup_artifact_hash:{setup_hash}"
    return None


def _reward_score(candidate: PairCandidate) -> float:
    return float(candidate.reward or 0.0)


def _outcome_rank(run_outcome: str | None) -> int:
    return {
        "success": 4,
        "failed": 3,
        "inconclusive": 2,
        "interrupted": 1,
        "invalid_task": 0,
        "flaky_task": 0,
    }.get(run_outcome or "", 0)


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
