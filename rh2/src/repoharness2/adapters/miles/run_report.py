"""I20 首版（第三组 §0 / §0.1 第 4 条，owner 2026-09-10）：离线 run 报告——七面基础摘要，**只消费已有记录**。

输入（一个 run 目录或若干文件）：
  - `rh2_events_*.jsonl`（miles 集成分支 `rh2_event_log`；未设 MILES_RH2_EVENT_DIR 时根本没有这些文件——
    此时事件面报 not_collected，**不能显示成"没有损耗"**）：group_filtered / group_consumed / drain_complete /
    attempt_cost_snapshot / grading_regrade / rollout_group / train_step / train_step_consumed / weight_update /
    logprob_compare / engine_versions_after_publish / run_restarted / sample_dis_accounting；
  - `fa_execution_audit.jsonl`（rh2 bringup 的 execution 终态审计，每条 = 一个已结束 attempt）。

口径（Brief §3，也是测试 oracle）：单位分开（组 / 成员执行 / 训练行 / token / step）；`train_step.metrics` 是
÷ num_rollouts 的每 execution 均值，总量 = 均值 × num_rollouts，跨 step 比例用总量之和；多 rank 副本只取一份；
缺失 / 未匹配 / 未知不记 0；进行中的 attempt 不在 audit 里（单列为未知，不推造）；会话级上下文长度下降只是线索，
不称压缩次数；同版本 logprob 差异与跨版本差异分列；只诊断不处置。可对进行中的 run 快照运行。
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from repoharness2.adapters.miles.drop_events import (
    ATTEMPT_COST_SNAPSHOT_EVENT,
    GROUP_CONSUMED_EVENT,
    GROUP_DROP_EVENT,
    iter_event_rows,
    summarize_attempt_costs,
    summarize_group_events,
)

REPORT_SCHEMA_ID = "rh2.run_report.v1"
AUDIT_FILE_NAME = "fa_execution_audit.jsonl"
EVENT_FILE_GLOB = "rh2_events_*.jsonl"

TRAIN_STEP_EVENT = "train_step"
TRAIN_STEP_CONSUMED_EVENT = "train_step_consumed"
WEIGHT_UPDATE_EVENT = "weight_update"
LOGPROB_COMPARE_EVENT = "logprob_compare"
ROLLOUT_GROUP_EVENT = "rollout_group"
DRAIN_COMPLETE_EVENT = "drain_complete"
ENGINE_VERSIONS_EVENT = "engine_versions_after_publish"
RUN_RESTARTED_EVENT = "run_restarted"
GRADING_REGRADE_EVENT = "grading_regrade"
SAMPLE_DIS_EVENT = "sample_dis_accounting"

COLLECTED, PARTIAL, NOT_COLLECTED = "collected", "partial", "not_collected"

# faithful_dis_loss.py 的线性计数键（每 execution 均值 → × num_rollouts 还原总量）
DIS_COUNT_KEYS: tuple[str, ...] = (
    "dis_microbatch_provenance_tokens",
    "dis_accepted_tokens",
    "dis_rejected_tokens",
    "dis_nonsingleton_provenance_tokens",
    "dis_singleton_accepted_tokens",
    "dis_candidate_signal_tokens",
    "dis_zero_advantage_accepted_tokens",
    "dis_rejected_low_tokens",
    "dis_rejected_high_tokens",
    "dis_support_size_1",
    "dis_support_size_2_3",
    "dis_support_size_4_7",
    "dis_support_size_8_15",
    "dis_support_size_16_plus",
)
DIS_FLAG_KEYS: tuple[str, ...] = ("dis_zero_contribution_microbatch",)

TURN_COVERAGE_SUM_KEYS: tuple[str, ...] = (
    "turns_generated",
    "turns_trained",
    "turns_empty_output",
    "turns_dropped_realign",
    "turns_dropped_merge",
    "training_rows",
    "trainable_tokens_total",
    "input_tokens_total",
    "input_tokens_excluding_last_row",
)
TIMING_SUMMARY_KEYS: tuple[str, ...] = (
    "materialize_seconds",
    "harness_run_seconds",
    "capture_finish_backfill_seconds",
    "grading_seconds",
    "projection_seconds",
    "eligibility_gate_seconds",
    "delivery_seconds",
    "cleanup_seconds",
    "total_audit_seconds",
)

CALIBER_NOTES: tuple[str, ...] = (
    "组、成员执行、训练行、token、optimizer step 是不同单位；一个 execution FORK 成多行不是多做多题。",
    "train_step.metrics 是 ÷ num_rollouts 的每 execution 均值；本报告按 均值 × num_rollouts 还原总量，跨 step 比例用总量之和。",
    "多 rank 副本只取一份（同 (rollout_id, step_id) 取 pp 末段且 dp_rank 最小的一条）。",
    "缺失记录、未匹配、未知版本不记 0；进行中的 attempt 不在 audit 里，未知就是未知。",
    "context_length_drop_clues 是会话级 prompt 长度下降线索，不是压缩次数。",
    "同版本 logprob 差异（logprob_compare.same_version）与跨版本差异分列；跨版本差不叫 KL。",
    "本工具只诊断，不重采样、不改预算、不改准入。",
)


# ---------------------------------------------------------------------------
# 输入
# ---------------------------------------------------------------------------


def load_run_inputs(paths: Iterable[Path | str]) -> dict[str, Any]:
    """收集事件行与审计行。目录：递归找 `rh2_events_*.jsonl` 与 `fa_execution_audit.jsonl`；文件按名字归类。"""

    event_files: list[Path] = []
    audit_files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            event_files += sorted(path.rglob(EVENT_FILE_GLOB))
            audit_files += sorted(path.rglob(AUDIT_FILE_NAME))
        elif path.name == AUDIT_FILE_NAME:
            audit_files.append(path)
        else:
            event_files.append(path)
    events = list(iter_event_rows(event_files)) if event_files else []
    audits: list[dict[str, Any]] = []
    malformed_audit_rows = 0
    for path in audit_files:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    malformed_audit_rows += 1
                    continue
                if isinstance(row, dict):
                    audits.append(row)
                else:
                    malformed_audit_rows += 1
    return {
        "events": events,
        "audits": audits,
        "sources": {
            "event_files": [str(p) for p in event_files],
            "audit_files": [str(p) for p in audit_files],
            "event_rows": len(events),
            "audit_rows": len(audits),
            "malformed_audit_rows": malformed_audit_rows,
        },
    }


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return float(value)


def _dist(values: list[float], *, unknown: int = 0) -> dict[str, Any]:
    """count / min / p50 / p95 / max / sum + unknown 计数（未知不填 0，不进统计）。"""

    if not values:
        return {"count": 0, "min": None, "p50": None, "p95": None, "max": None, "sum": None, "unknown": unknown}
    ordered = sorted(values)
    n = len(ordered)
    return {
        "count": n,
        "min": ordered[0],
        "p50": ordered[(n - 1) // 2],
        "p95": ordered[min(n - 1, int(math.ceil(0.95 * n)) - 1)],
        "max": ordered[-1],
        "sum": round(sum(values), 3),
        "unknown": unknown,
    }


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _by_kind(events: Iterable[Mapping[str, Any]], run_id: str | None) -> tuple[dict[str, list[Mapping[str, Any]]], int]:
    rows: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    foreign = 0
    for row in events:
        if run_id is not None and row.get("run_id") != run_id:
            foreign += 1
            continue
        kind = row.get("event")
        if isinstance(kind, str):
            rows[kind].append(row)
    return rows, foreign


def _dedupe_train_steps(rows: list[Mapping[str, Any]]) -> dict[tuple[Any, Any], Mapping[str, Any]]:
    """同 (rollout_id, step_id) 多 rank 副本只取一份：优先 pp 末段（带 metrics）且 dp_rank 最小。"""

    chosen: dict[tuple[Any, Any], Mapping[str, Any]] = {}
    for row in rows:
        key = (row.get("rollout_id"), row.get("step_id"))
        current = chosen.get(key)
        if current is None:
            chosen[key] = row
            continue
        better = (bool(row.get("is_pp_last_stage")) and row.get("metrics") is not None, -(_num(row.get("dp_rank")) or 0.0))
        worse = (bool(current.get("is_pp_last_stage")) and current.get("metrics") is not None, -(_num(current.get("dp_rank")) or 0.0))
        if better > worse:
            chosen[key] = row
    return chosen


def _step_order(key: tuple[Any, Any]) -> tuple[float, float]:
    return (_num(key[0]) if _num(key[0]) is not None else float("inf"), _num(key[1]) if _num(key[1]) is not None else float("inf"))


# ---------------------------------------------------------------------------
# 七面
# ---------------------------------------------------------------------------


def _facet_execution(events_by_kind, audits, run_id, all_events) -> dict[str, Any]:
    have_events = bool(events_by_kind.get(GROUP_DROP_EVENT) or events_by_kind.get(GROUP_CONSUMED_EVENT) or events_by_kind.get(ATTEMPT_COST_SNAPSHOT_EVENT))
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": []}
    if have_events:
        out["groups"] = summarize_group_events(all_events, run_id=run_id)
        out["costs"] = summarize_attempt_costs(all_events, run_id=run_id)
    else:
        out["groups"] = None
        out["costs"] = None
        out["reasons"].append("no_group_or_cost_events: 未设 MILES_RH2_EVENT_DIR 或事件文件缺失——不能据此说没有损耗")
    regrades = events_by_kind.get(GRADING_REGRADE_EVENT, [])
    out["grading_regrades"] = {
        "events": len(regrades),
        "by_op_and_category": dict(sorted(Counter(f"{r.get('op')}:{r.get('category')}" for r in regrades).items())),
    }
    if audits:
        out["attempts_audited"] = len(audits)
        out["dispositions"] = dict(sorted(Counter(str(a.get("disposition")) for a in audits).items()))
        out["termination_kinds"] = dict(sorted(Counter(str(((a.get("termination") or {}) or {}).get("kind")) for a in audits).items()))
        failures = Counter(f.get("error_type") for a in audits for f in (a.get("failure_records") or []) if isinstance(f, dict))
        out["failure_error_types_top"] = dict(failures.most_common(20))
        out["attempts_without_grading"] = sum(1 for a in audits if not a.get("grading"))
    else:
        out["attempts_audited"] = 0
        out["reasons"].append("no_audit_rows: fa_execution_audit.jsonl 缺失或为空")
    out["in_progress_attempts"] = None  # audit 只覆盖已结束 attempt；进行中的数量本工具不知道，不推造
    out["status"] = COLLECTED if have_events and audits else PARTIAL if (have_events or audits) else NOT_COLLECTED
    return out


def _facet_action_coverage(audits) -> dict[str, Any]:
    covered = [a for a in audits if isinstance(a.get("turn_coverage"), dict)]
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": [], "attempts_with_turn_coverage": len(covered),
                           "attempts_without_turn_coverage": len(audits) - len(covered)}
    if not covered:
        out["reasons"].append("no_turn_coverage: 没有 audit 行或旧树没有 turn_coverage 键")
        return out
    sums: dict[str, int] = {}
    unknown: dict[str, int] = {}
    for key in TURN_COVERAGE_SUM_KEYS:
        values = [_num(a["turn_coverage"].get(key)) for a in covered]
        sums[key] = int(sum(v for v in values if v is not None))
        unknown[key] = sum(1 for v in values if v is None)
    out["sums"] = sums
    out["sums_unknown_attempts"] = unknown
    out["fork_events_total"] = sum(len(a["turn_coverage"].get("fork_events") or []) for a in covered)
    out["training_rows_per_attempt"] = _dist([v for v in (_num(a["turn_coverage"].get("training_rows")) for a in covered) if v is not None])
    out["input_tokens_total_per_attempt"] = _dist([v for v in (_num(a["turn_coverage"].get("input_tokens_total")) for a in covered) if v is not None])
    out["trainable_tokens_per_attempt"] = _dist([v for v in (_num(a["turn_coverage"].get("trainable_tokens_total")) for a in covered) if v is not None])
    out["trainable_share_of_input"] = _ratio(sums["trainable_tokens_total"], sums["input_tokens_total"])
    clues = [len(a.get("context_shrink_reasons") or []) for a in audits]
    out["context_length_drop_clues"] = {
        "attempts_with_clues": sum(1 for c in clues if c),
        "clue_lines_total": sum(clues),
        "note": "会话级 prompt 长度下降线索（压缩 / 工具结果裁剪 / 短上下文子 agent 都会触发），不是压缩次数",
    }
    out["status"] = COLLECTED if len(covered) == len(audits) else PARTIAL
    return out


def _facet_reward(events_by_kind, audits, run_id) -> dict[str, Any]:
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": []}
    graded = [a.get("grading") for a in audits if isinstance(a.get("grading"), dict)]
    if graded:
        rewards = [_num(g.get("reward")) for g in graded]
        known = [r for r in rewards if r is not None]
        out["audit_grading"] = {
            "outcomes": dict(sorted(Counter(str(g.get("outcome")) for g in graded).items())),
            "failure_categories": dict(sorted(Counter(str(g.get("failure_category")) for g in graded if g.get("failure_category")).items())),
            "reward": _dist(known, unknown=len(rewards) - len(known)),
            "reward_value_counts": dict(sorted(Counter(str(r) for r in known).items())),
        }
        by_task: dict[str, dict[str, Any]] = {}
        for audit in audits:
            grading = audit.get("grading")
            if not isinstance(grading, dict):
                continue
            entry = by_task.setdefault(str(audit.get("task_id") or "<unknown>"), {"graded": 0, "reward_known": 0, "reward_sum": 0.0})
            entry["graded"] += 1
            reward = _num(grading.get("reward"))
            if reward is not None:
                entry["reward_known"] += 1
                entry["reward_sum"] += reward
        for entry in by_task.values():
            entry["reward_mean"] = round(entry["reward_sum"] / entry["reward_known"], 4) if entry["reward_known"] else None
            entry["reward_sum"] = round(entry["reward_sum"], 3)
        out["by_task"] = dict(sorted(by_task.items()))
    else:
        out["audit_grading"] = None
        out["reasons"].append("no_graded_audits: 没有带 grading 块的 audit 行")
    groups = events_by_kind.get(ROLLOUT_GROUP_EVENT, [])
    consumed_keys = {(r.get("run_id"), tuple(r.get("sample_indices") or [])) for r in events_by_kind.get(GROUP_CONSUMED_EVENT, [])}
    if groups:
        zero_var = all0 = all1 = 0
        pos = neg = zero = 0
        consumed_group_rewards: list[float] = []
        unmatched = 0
        for row in groups:
            rewards = [v for v in (_num(x) for x in (row.get("rewards") or [])) if v is not None]
            if not rewards:
                continue
            if len(set(rewards)) == 1:
                zero_var += 1
                all0 += rewards[0] == 0.0
                all1 += rewards[0] == 1.0
            mean = sum(rewards) / len(rewards)
            for r in rewards:
                delta = r - mean
                pos += delta > 0
                neg += delta < 0
                zero += delta == 0
            key = (row.get("run_id"), tuple(row.get("sample_indices") or []))
            if key in consumed_keys:
                consumed_group_rewards += rewards
            else:
                unmatched += 1
        out["rollout_groups"] = {
            "groups": len(groups),
            "zero_variance_groups": zero_var,
            "all_zero_groups": all0,
            "all_one_groups": all1,
            "advantage_sign_approximation": {"positive": pos, "negative": neg, "zero": zero,
                                              "note": "reward − 组均值 的符号近似；真实优势在 trainer 内部，不导出"},
            "consumed_member_rewards": _dist(consumed_group_rewards),
            "groups_not_matched_to_consumed_event": unmatched,
        }
    else:
        out["rollout_groups"] = None
        out["reasons"].append("no_rollout_group_events")
    out["status"] = COLLECTED if graded and groups else PARTIAL if (graded or groups) else NOT_COLLECTED
    return out


def _facet_dis(events_by_kind) -> dict[str, Any]:
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": []}
    steps = _dedupe_train_steps(events_by_kind.get(TRAIN_STEP_EVENT, []))
    with_metrics = {k: r for k, r in steps.items() if isinstance(r.get("metrics"), dict)}
    out["steps_seen"] = len(steps)
    out["steps_with_metrics"] = len(with_metrics)
    if with_metrics:
        totals: dict[str, float] = {}
        missing: Counter = Counter()
        flags: dict[str, float] = {}
        for row in with_metrics.values():
            n = _num(row.get("num_rollouts"))
            metrics = row["metrics"]
            for key in DIS_COUNT_KEYS:
                value = _num(metrics.get(key))
                if value is None or n is None:
                    missing[key] += 1
                    continue
                totals[key] = totals.get(key, 0.0) + value * n
            for key in DIS_FLAG_KEYS:
                value = _num(metrics.get(key))
                if value is not None and n is not None:
                    flags[key] = flags.get(key, 0.0) + value * n  # 聚合值 = 零贡献 microbatch 数 / num_rollouts，×n 还原个数
        out["totals_restored"] = {k: round(v, 3) for k, v in sorted(totals.items())}
        out["totals_missing_steps"] = dict(sorted(missing.items()))
        out["zero_contribution_microbatches_restored"] = {k: round(v, 3) for k, v in flags.items()}
        acc = totals.get("dis_accepted_tokens")
        prov = totals.get("dis_microbatch_provenance_tokens")
        out["ratios_over_totals"] = {
            "accepted_over_provenance": _ratio(acc, prov),
            "rejected_low_over_provenance": _ratio(totals.get("dis_rejected_low_tokens"), prov),
            "rejected_high_over_provenance": _ratio(totals.get("dis_rejected_high_tokens"), prov),
            "singleton_accepted_over_accepted": _ratio(totals.get("dis_singleton_accepted_tokens"), acc),
            "zero_advantage_accepted_over_accepted": _ratio(totals.get("dis_zero_advantage_accepted_tokens"), acc),
            "candidate_signal_over_accepted": _ratio(totals.get("dis_candidate_signal_tokens"), acc),
            "candidate_signal_over_provenance": _ratio(totals.get("dis_candidate_signal_tokens"), prov),
        }
        out["support_size_buckets_restored"] = {
            k: round(totals[k], 3) for k in DIS_COUNT_KEYS if k.startswith("dis_support_size_") and k in totals
        }
        out["note"] = "候选信号 = accepted ∧ support>1 ∧ advantage≠0 的计数，不是已证明的非零梯度 token 数；全局零信号以 train_step.outcome 为准"
    else:
        out["reasons"].append("no_train_step_metrics: 没有 train_step 事件或其 metrics 为空（非 pp 末段 / 未启用事件）")
    samples = events_by_kind.get(SAMPLE_DIS_EVENT, [])
    if samples:
        entries = [e for r in samples for e in (r.get("entries") or []) if isinstance(e, dict)]
        out["sample_dis_accounting"] = {
            "events": len(samples),
            "entries": len(entries),
            "accepted_tokens_sum": sum(int(_num(e.get("accepted_tokens")) or 0) for e in entries),
            "provenance_tokens_sum": sum(int(_num(e.get("provenance_tokens")) or 0) for e in entries),
            "entries_without_leaf_ordinal": sum(1 for e in entries if e.get("leaf_ordinal") is None),
            "note": "只有 accepted / provenance 两个身份计数，不能从它补造候选信号或 log-ratio 分布",
        }
    out["log_ratio_distribution"] = {"status": NOT_COLLECTED, "reason": "当前没有有界 log-ratio 分布的 producer"}
    out["status"] = COLLECTED if with_metrics else PARTIAL if steps else NOT_COLLECTED
    return out


def _facet_staleness(events_by_kind, execution) -> dict[str, Any]:
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": []}
    groups = execution.get("groups")
    if groups:
        out["consumed_staleness"] = groups.get("consumed_staleness")
        out["stale_drops"] = groups.get("stale_drops")
    else:
        out["reasons"].append("no_group_events")
    rollout_groups = events_by_kind.get(ROLLOUT_GROUP_EVENT, [])
    if rollout_groups:
        multi = single = unknown = 0
        for row in rollout_groups:
            for versions in row.get("behavior_versions") or []:
                if not versions:
                    unknown += 1
                elif len({str(v) for v in versions}) > 1:
                    multi += 1
                else:
                    single += 1
        out["behavior_versions_per_sample"] = {"single_version": single, "multi_version": multi, "unknown": unknown}
    compares = events_by_kind.get(LOGPROB_COMPARE_EVENT, [])
    if compares:
        entries = [e for r in compares for e in (r.get("entries") or []) if isinstance(e, dict)]
        same = [e for e in entries if e.get("same_version") is True]
        cross = [e for e in entries if e.get("same_version") is False]
        unknown_version = [e for e in entries if e.get("same_version") is None]

        def block(items):
            return {
                "rows": len(items),
                "comparable_action_tokens": sum(int(_num(e.get("num_tokens")) or 0) for e in items),
                "mean_abs_diff_per_row": _dist([v for v in (_num(e.get("mean_abs_diff")) for e in items) if v is not None]),
                "length_mismatch_rows": sum(1 for e in items if e.get("length_mismatch")),
            }

        out["logprob_compare"] = {
            "events": len(compares),
            "same_version": block(same),
            "cross_version": block(cross),
            "version_unknown_rows": len(unknown_version),
            "no_comparable_same_version_samples": not same,
            "note": "same_version 按行的全部版本判断，不是逐 token 子集；完全异步时可能没有同版本样本",
        }
    else:
        out["reasons"].append("no_logprob_compare_events")
    out["status"] = COLLECTED if groups and compares else PARTIAL if (groups or rollout_groups or compares) else NOT_COLLECTED
    return out


def _facet_optimizer(events_by_kind) -> dict[str, Any]:
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": []}
    steps = _dedupe_train_steps(events_by_kind.get(TRAIN_STEP_EVENT, []))
    if steps:
        ordered = [steps[k] for k in sorted(steps, key=_step_order)]
        applied = [bool(r.get("optimizer_step_applied")) for r in ordered]
        longest_not_applied = current = 0
        for flag in applied:
            current = 0 if flag else current + 1
            longest_not_applied = max(longest_not_applied, current)
        adam_ok = sum(
            1 for r in ordered
            if bool(r.get("optimizer_step_applied")) and _num(r.get("adam_step_after")) is not None
            and _num(r.get("adam_step_before")) is not None and r["adam_step_after"] - r["adam_step_before"] == 1
        )
        out["train_steps"] = {
            "steps": len(ordered),
            "outcomes": dict(sorted(Counter(str(r.get("outcome")) for r in ordered).items())),
            "optimizer_steps_applied": sum(applied),
            "optimizer_steps_not_applied": len(applied) - sum(applied),
            "longest_run_without_applied_step": longest_not_applied,
            "applied_steps_with_adam_increment_1": adam_ok,
            "grad_norm": _dist([v for v in (_num(r.get("grad_norm")) for r in ordered) if v is not None],
                               unknown=sum(1 for r in ordered if _num(r.get("grad_norm")) is None)),
            "duration_seconds": _dist([v for v in (_num(r.get("duration_seconds")) for r in ordered) if v is not None]),
            "num_rollouts_per_step": _dist([v for v in (_num(r.get("num_rollouts")) for r in ordered) if v is not None]),
        }
    else:
        out["reasons"].append("no_train_step_events")
    consumed = events_by_kind.get(TRAIN_STEP_CONSUMED_EVENT, [])
    if consumed:
        union: dict[tuple[Any, Any], set] = defaultdict(set)
        errors = 0
        for row in consumed:
            if row.get("sample_indices") is None:
                errors += 1
                continue
            union[(row.get("rollout_id"), row.get("step_id"))].update(int(i) for i in row["sample_indices"])
        out["consumed_samples_per_step"] = _dist([float(len(s)) for s in union.values()])
        out["train_step_consumed_error_rows"] = errors
    updates = events_by_kind.get(WEIGHT_UPDATE_EVENT, [])
    if updates:
        seq = [(_num(r.get("version_before")), _num(r.get("version_after"))) for r in updates]
        gaps = sum(1 for b, a in seq if b is not None and a is not None and a != b + 1)
        out["weight_updates"] = {
            "count": len(updates),
            "versions": [[b, a] for b, a in seq][:200],
            "non_increment_by_one": gaps,
            "duration_seconds": _dist([v for v in (_num(r.get("duration_seconds")) for r in updates) if v is not None]),
        }
    else:
        out["reasons"].append("no_weight_update_events")
    out["engine_version_checks"] = len(events_by_kind.get(ENGINE_VERSIONS_EVENT, []))
    out["run_restarts"] = len(events_by_kind.get(RUN_RESTARTED_EVENT, []))
    out["learning_rate"] = {"status": NOT_COLLECTED, "reason": "train_step 事件不带学习率"}
    out["status"] = COLLECTED if steps and updates else PARTIAL if (steps or updates or consumed) else NOT_COLLECTED
    return out


def _lifecycle_segments(audit: Mapping[str, Any]) -> Mapping[str, Any]:
    timing = audit.get("timing_summary") or {}
    lifecycle = timing.get("lifecycle_timing") if isinstance(timing, dict) else None
    if isinstance(lifecycle, dict):
        segments = lifecycle.get("segments")
        return segments if isinstance(segments, dict) else lifecycle
    return {}


def _facet_throughput(events_by_kind, audits, execution) -> dict[str, Any]:
    out: dict[str, Any] = {"status": NOT_COLLECTED, "reasons": []}
    if audits:
        summary: dict[str, Any] = {}
        for key in TIMING_SUMMARY_KEYS:
            values = [_num((a.get("timing_summary") or {}).get(key)) for a in audits]
            summary[key] = _dist([v for v in values if v is not None], unknown=sum(1 for v in values if v is None))
        out["timing_summary_seconds"] = summary
        segments: dict[str, list[float]] = defaultdict(list)
        segment_unknown: Counter = Counter()
        for audit in audits:
            for name, value in _lifecycle_segments(audit).items():
                number = _num(value)
                if number is None:
                    segment_unknown[name] += 1
                else:
                    segments[name].append(number)
        segment_names = sorted(set(segments) | set(segment_unknown))  # 只有未知值的段也要列出（unknown 计数，不填 0）
        out["lifecycle_segments_seconds"] = {
            name: _dist(segments.get(name, []), unknown=segment_unknown.get(name, 0)) for name in segment_names
        }
        queue_wait = [_num(((a.get("episode_deadline") or {}) or {}).get("model_call_queue_wait_seconds_total")) for a in audits]
        out["model_call_queue_wait_seconds_total"] = _dist([v for v in queue_wait if v is not None], unknown=sum(1 for v in queue_wait if v is None))
        grading_timings: dict[str, list[float]] = defaultdict(list)
        for audit in audits:
            timings = (audit.get("grading") or {}).get("timings") if isinstance(audit.get("grading"), dict) else None
            if isinstance(timings, dict):
                for key, value in timings.items():
                    number = _num(value)
                    if number is not None:
                        grading_timings[key].append(number)
        out["grading_timings"] = {k: _dist(v) for k, v in sorted(grading_timings.items())}
        out["note_lifecycle"] = "各段分开列，重叠段不相加；成员 elapsed 之和不是 run 墙钟或 GPU 秒"
    else:
        out["reasons"].append("no_audit_rows")
    drains = events_by_kind.get(DRAIN_COMPLETE_EVENT, [])
    if drains:
        out["drain_complete"] = {
            "count": len(drains),
            "elapsed_seconds": _dist([v for v in (_num(r.get("elapsed_seconds")) for r in drains) if v is not None]),
            "target_groups": _dist([v for v in (_num(r.get("target_groups")) for r in drains) if v is not None]),
        }
    costs = execution.get("costs")
    if costs:
        out["captured_output_tokens_per_member"] = {
            terminal: bucket.get("member_fields", {}).get("captured_output_tokens")
            for terminal, bucket in (costs.get("terminals") or {}).items()
        }
    out["gpu_and_container_resources"] = {"status": NOT_COLLECTED, "reason": "现有 logger / Docker 资源指标不在本工具输入内"}
    out["status"] = COLLECTED if audits and drains else PARTIAL if (audits or drains) else NOT_COLLECTED
    return out


# ---------------------------------------------------------------------------
# 装配
# ---------------------------------------------------------------------------


def build_run_report(*, events: list[Mapping[str, Any]], audits: list[dict[str, Any]], run_id: str | None = None,
                     sources: Mapping[str, Any] | None = None) -> dict[str, Any]:
    events_by_kind, foreign = _by_kind(events, run_id)
    if run_id is not None:
        audits = [a for a in audits if a.get("run_id") in (None, run_id)]  # audit 行通常不带 run_id：不按它过滤掉
    execution = _facet_execution(events_by_kind, audits, run_id, events)
    facets = {
        "execution_and_loss": execution,
        "action_coverage": _facet_action_coverage(audits),
        "reward_and_distribution": _facet_reward(events_by_kind, audits, run_id),
        "dis_and_support": _facet_dis(events_by_kind),
        "staleness_and_alignment": _facet_staleness(events_by_kind, execution),
        "optimizer_and_publish": _facet_optimizer(events_by_kind),
        "throughput_and_resources": _facet_throughput(events_by_kind, audits, execution),
    }
    return {
        "schema_id": REPORT_SCHEMA_ID,
        "run_id": run_id,
        "sources": dict(sources or {}),
        "event_kinds": dict(sorted(Counter(k for k in events_by_kind for _ in events_by_kind[k]).items())),
        "events_foreign_run": foreign,
        "coverage": {name: facet["status"] for name, facet in facets.items()},
        "facets": facets,
        "caliber_notes": list(CALIBER_NOTES),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="I20 首版：离线 run 报告（七面基础摘要，只消费已有记录）")
    parser.add_argument("paths", nargs="+", help="run 目录（递归找 rh2_events_*.jsonl 与 fa_execution_audit.jsonl）或文件")
    parser.add_argument("--run-id", default=None, help="只统计该 run_id 的事件（不指定时按 run_id 分开连接，不混连）")
    parser.add_argument("--json", default=None, help="把报告写到该文件（同时打印到 stdout）")
    args = parser.parse_args(argv)
    inputs = load_run_inputs(args.paths)
    report = build_run_report(events=inputs["events"], audits=inputs["audits"], run_id=args.run_id, sources=inputs["sources"])
    text = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
