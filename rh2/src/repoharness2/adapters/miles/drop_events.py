"""W4（决策包 D2+B v2 B-2）：fully-async buffer 组级事件的 run 结束汇总。

事件来源 = miles 集成分支 `miles/rollout/fully_async_data_buffer.py`（`DefaultDataBuffer`）在
四个终局各发一条的结构化事件（schema 见 `miles/utils/rh2_event_log.py` 的 W4 段）：

    group_filtered   drop_stage ∈ {put_aborted, dynamic_filter, consume_stale}，reason_code、组身份、
                     ABORTED 成员的 member_slot/physical_attempt_id、stale 的 oldest/current/staleness/limit
    group_consumed   get() 交出一组给 trainer（oldest/current/staleness/limit + 组身份）

每个 prompt group 在 buffer 里恰有一个终局，所以：

    尝试（attempts） = 被消费的组数 + 被丢弃的组数
    按 task 的分母   = 该 task_id（缺则 instance_id，再缺则 "<unknown>"）下的尝试数

这只是"从事件流聚合"的一个小函数 + 命令行入口（不建平台、不建 ledger）。它刻意只依赖标准库：
离线看事件文件时不需要 miles/torch。字面量 `DROP_STAGES` 与 miles 侧常量的一致性由
`tests/adapters_miles/test_w4_consume_time_staleness.py` 钉死。

用法::

    python -m repoharness2.adapters.miles.drop_events $MILES_RH2_EVENT_DIR [--run-id RUN] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "ATTEMPT_COST_SNAPSHOT_EVENT",
    "COST_SUMMARY_SCHEMA_ID",
    "DROP_STAGES",
    "GROUP_CONSUMED_EVENT",
    "GROUP_DROP_EVENT",
    "SUMMARY_SCHEMA_ID",
    "iter_event_rows",
    "main",
    "summarize_attempt_costs",
    "summarize_group_events",
]

GROUP_DROP_EVENT = "group_filtered"
GROUP_CONSUMED_EVENT = "group_consumed"
# N1（第 2 组 §4 / I15-I20）：rh2 编排在每个 physical attempt 的 finally 段发出的成本快照
# （schema 见 generate.py `_emit_attempt_cost_snapshot`）。它只是编排阶段的事实（disposition_hint），
# 最终消费 / 丢弃仍由上面两种 buffer 事件判定。
ATTEMPT_COST_SNAPSHOT_EVENT = "attempt_cost_snapshot"
DROP_STAGES: tuple[str, ...] = ("put_aborted", "dynamic_filter", "consume_stale")
SUMMARY_SCHEMA_ID = "rh2.group_event_summary.v1"
COST_SUMMARY_SCHEMA_ID = "rh2.attempt_cost_summary.v1"
UNKNOWN_TASK = "<unknown>"
COST_FIELDS: tuple[str, ...] = (
    "elapsed_seconds", "accepted_turns", "captured_output_tokens", "trainable_tokens_total", "input_tokens_total",
)


def iter_event_rows(paths: Iterable[Path | str]) -> Iterator[dict[str, Any]]:
    """逐行读 jsonl 事件文件（目录则取其下全部 rh2_events_*.jsonl）；坏行跳过并计入 `_malformed`。"""

    for raw in paths:
        path = Path(raw)
        files = sorted(path.glob("rh2_events_*.jsonl")) if path.is_dir() else [path]
        for file in files:
            with open(file, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        yield {"event": "_malformed", "_file": str(file)}
                        continue
                    if isinstance(row, dict):
                        yield row


def _task_key(row: Mapping[str, Any]) -> str:
    for key in ("task_id", "instance_id"):
        value = row.get(key)
        if value:
            return str(value)
    return UNKNOWN_TASK


def _stats(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "histogram": {}}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.fmean(values), 4),
        "histogram": {str(k): v for k, v in sorted(Counter(values).items())},
    }


def _new_task_bucket() -> dict[str, Any]:
    return {
        "attempts": 0,
        "accepted": 0,
        "dropped": 0,
        "dropped_by_stage": {stage: 0 for stage in DROP_STAGES},
        "drop_ratio": None,
    }


def summarize_group_events(rows: Iterable[Mapping[str, Any]], *, run_id: str | None = None) -> dict[str, Any]:
    """把事件流聚合成 run 结束汇总（纯函数，输入顺序无关）。

    - ``totals``：attempts / accepted / dropped / dropped_by_stage / dropped_by_reason；
    - ``consumed_staleness``：被消费组的 staleness 分布（无版本事实的组记入 ``unknown``）；
    - ``stale_drops``：consume_stale 的 staleness 分布与出现过的阈值；
    - ``by_task``：按 task 的尝试/接受/丢弃分母（识别"长任务被系统性丢弃"的分布偏差）；
    - ``rows_skipped``：不属于本 run（run_id 不同）或 schema 不完整（缺 drop_stage）的行数，
      不静默吞掉。
    ``run_id`` 非 None 时只统计带同一 run_id 的行（与 G1 collect 的 run 绑定同一口径）。
    """

    totals = {
        "attempts": 0,
        "accepted": 0,
        "dropped": 0,
        "dropped_by_stage": {stage: 0 for stage in DROP_STAGES},
        "dropped_by_reason": Counter(),
    }
    consumed_staleness: list[int] = []
    consumed_unknown = 0
    stale_staleness: list[int] = []
    stale_limits: Counter = Counter()
    by_task: dict[str, dict[str, Any]] = {}
    skipped = {"foreign_run": 0, "malformed": 0, "unknown_drop_stage": 0}
    aborted_members = 0

    for row in rows:
        kind = row.get("event")
        if kind == "_malformed":
            skipped["malformed"] += 1
            continue
        if kind not in (GROUP_DROP_EVENT, GROUP_CONSUMED_EVENT):
            continue
        if run_id is not None and row.get("run_id") != run_id:
            skipped["foreign_run"] += 1
            continue
        bucket = by_task.setdefault(_task_key(row), _new_task_bucket())
        if kind == GROUP_CONSUMED_EVENT:
            totals["accepted"] += 1
            bucket["accepted"] += 1
            staleness = row.get("staleness")
            if isinstance(staleness, int) and not isinstance(staleness, bool):
                consumed_staleness.append(staleness)
            else:
                consumed_unknown += 1
            continue
        stage = row.get("drop_stage")
        if stage not in DROP_STAGES:
            # 旧 emitter（W4 之前）只有 reason 没有 drop_stage：仍算丢弃，但不能归到分支。
            skipped["unknown_drop_stage"] += 1
            totals["dropped"] += 1
            bucket["dropped"] += 1
            totals["dropped_by_reason"][str(row.get("reason_code") or row.get("reason") or "?")] += 1
            continue
        totals["dropped"] += 1
        totals["dropped_by_stage"][stage] += 1
        totals["dropped_by_reason"][str(row.get("reason_code") or row.get("reason") or stage)] += 1
        bucket["dropped"] += 1
        bucket["dropped_by_stage"][stage] += 1
        if stage == "consume_stale":
            staleness = row.get("staleness")
            if isinstance(staleness, int) and not isinstance(staleness, bool):
                stale_staleness.append(staleness)
            stale_limits[str(row.get("staleness_limit"))] += 1
        elif stage == "put_aborted":
            aborted_members += len(row.get("aborted_members") or [])

    totals["attempts"] = totals["accepted"] + totals["dropped"]
    for bucket in by_task.values():
        bucket["attempts"] = bucket["accepted"] + bucket["dropped"]
        bucket["drop_ratio"] = round(bucket["dropped"] / bucket["attempts"], 4) if bucket["attempts"] else None
    totals["dropped_by_reason"] = dict(sorted(totals["dropped_by_reason"].items()))

    return {
        "schema_id": SUMMARY_SCHEMA_ID,
        "run_id": run_id,
        "totals": totals,
        "consumed_staleness": {**_stats(consumed_staleness), "unknown": consumed_unknown},
        "stale_drops": {**_stats(stale_staleness), "limits_seen": dict(sorted(stale_limits.items()))},
        "aborted_members_total": aborted_members,
        "by_task": dict(sorted(by_task.items())),
        "rows_skipped": skipped,
    }


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _dist(values: list[float], *, unknown: int) -> dict[str, Any]:
    """成员级数值分布：count / min / p50 / max / sum + unknown 计数（未知不填 0，不进统计）。"""

    if not values:
        return {"count": 0, "min": None, "p50": None, "max": None, "sum": None, "unknown": unknown}
    ordered = sorted(values)
    return {
        "count": len(values),
        "min": ordered[0],
        "p50": ordered[(len(ordered) - 1) // 2],
        "max": ordered[-1],
        "sum": round(sum(values), 3),
        "unknown": unknown,
    }


def _new_cost_bucket() -> dict[str, Any]:
    return {
        "groups": 0,
        "members_observed": 0,
        "groups_without_snapshots": 0,
        "member_fields": {name: {"values": [], "unknown": 0} for name in COST_FIELDS},
        # 整组连带成本 = 同组**全部**成员已知 elapsed 之和（成员耗时之和，不是作业墙钟 / GPU 时间）。只有"成员齐全
        # 且每个成员 elapsed 已知"的组进这里；成员缺失 / 有未知成员的组的已知部分和单独放 group_cost_seconds_known_partial
        # （下界，Codex 集成审查 R6：不能让不完整的组看起来是完整成本）；全部未知的组只计数，不填 0。
        "group_cost_seconds": [],
        "group_cost_seconds_known_partial": [],
        "groups_with_unknown_members": 0,  # 有成员 elapsed 未知（快照在但值缺）的组数
        "groups_with_missing_members": 0,  # 终局行 member_count > 观测到的快照数（成员快照缺失）的组数
        "groups_cost_unknown": 0,  # 有快照但没有任何已知 elapsed 的组数
        "root_cause_reasons": Counter(),  # 仅 put_aborted：导致丢组的成员在快照里的原因
        # R6：按根因的成员级成本（仅 put_aborted 的导致成员；同组多根因各记各的，不跨原因累加）
        "by_root_cause": {},
        # R6 余项（Codex 复核）：**整组连带成本**按根因集合归属——单根因组归该原因；多根因组归 "a|b" 组合键
        # （不重复计入各单项，无重叠）。回答的是"哪类故障主要连带丢掉长轨迹"，与上面失败成员自身成本不同。
        "by_root_cause_set": {},
        "disposition_hints": Counter(),
    }


def _new_reason_set_cost() -> dict[str, Any]:
    return {"groups": 0, "group_cost_seconds": [], "group_cost_seconds_known_partial": [], "groups_cost_unknown": 0}


def _finish_reason_set_cost(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "groups": entry["groups"],
        "group_cost_seconds": _dist(entry["group_cost_seconds"], unknown=entry["groups_cost_unknown"]),
        "group_cost_seconds_known_partial": _dist(entry["group_cost_seconds_known_partial"], unknown=0),
    }


def _new_reason_cost() -> dict[str, Any]:
    return {"members": 0, "member_fields": {name: {"values": [], "unknown": 0} for name in COST_FIELDS}}


def _add_member_fields(target: dict[str, Any], snap: Mapping[str, Any]) -> None:
    for name in COST_FIELDS:
        value = _num(snap.get(name))
        entry = target[name]
        if value is None:
            entry["unknown"] += 1
        else:
            entry["values"].append(value)


def _finish_member_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {name: _dist(entry["values"], unknown=entry["unknown"]) for name, entry in fields.items()}


def _finish_cost_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    return {
        "groups": bucket["groups"],
        "members_observed": bucket["members_observed"],
        "groups_without_snapshots": bucket["groups_without_snapshots"],
        "member_fields": _finish_member_fields(bucket["member_fields"]),
        "group_cost_seconds": _dist(bucket["group_cost_seconds"], unknown=bucket["groups_cost_unknown"]),
        "group_cost_seconds_known_partial": _dist(
            bucket["group_cost_seconds_known_partial"],
            unknown=bucket["groups_with_unknown_members"] + bucket["groups_with_missing_members"],
        ),
        "groups_with_unknown_members": bucket["groups_with_unknown_members"],
        "groups_with_missing_members": bucket["groups_with_missing_members"],
        "groups_cost_unknown": bucket["groups_cost_unknown"],
        "root_cause_reasons": dict(sorted(bucket["root_cause_reasons"].items())),
        "by_root_cause": {
            reason: {"members": entry["members"], "member_fields": _finish_member_fields(entry["member_fields"])}
            for reason, entry in sorted(bucket["by_root_cause"].items())
        },
        "by_root_cause_set": {
            key: _finish_reason_set_cost(entry) for key, entry in sorted(bucket["by_root_cause_set"].items())
        },
        "disposition_hints": dict(sorted(bucket["disposition_hints"].items())),
    }


def _new_task_cost() -> dict[str, Any]:
    return {
        "groups": 0,
        "consumed_groups": 0,
        "dropped_groups": Counter(),
        "members_observed": 0,
        "member_fields": {name: {"values": [], "unknown": 0} for name in COST_FIELDS},
        # R6 余项：同 task 内消费 / 丢弃两种终态的成员成本分开（上面 member_fields 是两者合计，保留作总量）
        "consumed_member_fields": {name: {"values": [], "unknown": 0} for name in COST_FIELDS},
        "dropped_member_fields": {name: {"values": [], "unknown": 0} for name in COST_FIELDS},
    }


def _finish_task_cost(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "groups": entry["groups"],
        "consumed_groups": entry["consumed_groups"],
        "dropped_groups": dict(sorted(entry["dropped_groups"].items())),
        "members_observed": entry["members_observed"],
        "member_fields": _finish_member_fields(entry["member_fields"]),
        "consumed_member_fields": _finish_member_fields(entry["consumed_member_fields"]),
        "dropped_member_fields": _finish_member_fields(entry["dropped_member_fields"]),
    }


def _scoped(row: Mapping[str, Any], value: Any) -> str:
    """Codex 集成审查 R5：连接键带 run 身份——组 id（miles_g{group_index}）与 attempt id 只在同一 run 内唯一，
    多目录输入且未指定 --run-id 时不能把两个 run 的同名组连成一组。"""

    return f"{row.get('run_id')}\x00{value}"


def summarize_attempt_costs(rows: Iterable[Mapping[str, Any]], *, run_id: str | None = None) -> dict[str, Any]:
    """N1（第 2 组 §4）：把 `attempt_cost_snapshot` 与 buffer 终局事件按组身份连接，给出各终局的成本分布。

    - 连接键：**(run_id, `rh2_prompt_group_id`)**（组终局行与快照都带 run_id；R5：跨 run 同名组不混连）；
      `put_aborted` 行再按 (run_id, `aborted_members[*].physical_attempt_id`) 找导致丢组的成员及其快照原因。
    - 桶：``consumed`` 与每个丢弃原因（`group_filtered.reason_code`，缺则 drop_stage）。每桶：组数、成员观测数、
      成员级 elapsed / turns / tokens 分布（未知单列，不填 0）、**整组连带成本** = 同组所有已知成员 elapsed 之和
      （七个 600s 成员 + 一个 5s 失败成员 = 4205s；不是失败者的 5s，也不是八条完整轨迹），多根因组保留原因
      集合、不跨桶累加。
    - 分母：组终局数仍是组数；成员观测数单列；无终局事件的快照记 ``unmatched_snapshots``，没有快照的组记
      ``groups_without_snapshots``，缺组身份的旧格式行记 ``legacy_rows``；同一 attempt 多条快照只取最后一条并
      计 ``duplicate_snapshots``（多条 FORK 训练行属同一 attempt，不重复记成员）。
    - R6 维度：每桶 ``by_root_cause``（put_aborted 导致成员**自身**按原因的成本分布）与 ``by_root_cause_set``
      （**整组连带成本**按根因集合归属：单根因归该原因，多根因归 "a|b" 组合键、不重复计入各单项——回答"哪类故障
      主要连带丢掉长轨迹"）、顶层 ``by_task``（按 task 的消费 / 丢弃组数，成员成本合计 + 消费 / 丢弃两种终态各自
      的分布）；成员缺失（终局 member_count > 快照数）或成员 elapsed 未知的组只进
      ``group_cost_seconds_known_partial``（下界），全部未知的组只计 ``groups_cost_unknown``，不填 0。
    """

    snapshots_by_attempt: dict[str, Mapping[str, Any]] = {}
    duplicates = 0
    terminal_rows: list[Mapping[str, Any]] = []
    skipped = {"foreign_run": 0, "malformed": 0}
    for row in rows:
        kind = row.get("event")
        if kind == "_malformed":
            skipped["malformed"] += 1
            continue
        if kind not in (ATTEMPT_COST_SNAPSHOT_EVENT, GROUP_DROP_EVENT, GROUP_CONSUMED_EVENT):
            continue
        if run_id is not None and row.get("run_id") != run_id:
            skipped["foreign_run"] += 1
            continue
        if kind == ATTEMPT_COST_SNAPSHOT_EVENT:
            paid = row.get("physical_attempt_id")
            if not paid:
                skipped["malformed"] += 1
                continue
            key = _scoped(row, paid)
            if key in snapshots_by_attempt:
                duplicates += 1
            snapshots_by_attempt[key] = row
        else:
            terminal_rows.append(row)

    by_group: dict[str, list[Mapping[str, Any]]] = {}
    for snap in snapshots_by_attempt.values():
        group = snap.get("rh2_prompt_group_id")
        if group:
            by_group.setdefault(_scoped(snap, group), []).append(snap)
    matched_groups: set[str] = set()
    buckets: dict[str, dict[str, Any]] = {}
    by_task: dict[str, dict[str, Any]] = {}
    legacy_rows = 0
    for row in terminal_rows:
        group = row.get("rh2_prompt_group_id")
        if not group:
            legacy_rows += 1
            continue
        group_key = _scoped(row, group)
        matched_groups.add(group_key)
        if row.get("event") == GROUP_CONSUMED_EVENT:
            key = "consumed"
        else:
            key = str(row.get("reason_code") or row.get("reason") or row.get("drop_stage") or "?")
        bucket = buckets.setdefault(key, _new_cost_bucket())
        bucket["groups"] += 1
        members = by_group.get(group_key, [])
        task = by_task.setdefault(_task_key(row), _new_task_cost())
        task["groups"] += 1
        if key == "consumed":
            task["consumed_groups"] += 1
        else:
            task["dropped_groups"][key] += 1
        if not members:
            bucket["groups_without_snapshots"] += 1
        bucket["members_observed"] += len(members)
        task["members_observed"] += len(members)
        known_elapsed: list[float] = []
        unknown_member = False
        for snap in members:
            bucket["disposition_hints"][str(snap.get("disposition_hint") or "unknown")] += 1
            _add_member_fields(bucket["member_fields"], snap)
            _add_member_fields(task["member_fields"], snap)
            _add_member_fields(task["consumed_member_fields" if key == "consumed" else "dropped_member_fields"], snap)
            elapsed = _num(snap.get("elapsed_seconds"))
            if elapsed is None:
                unknown_member = True
            else:
                known_elapsed.append(elapsed)
        expected_members = row.get("member_count")
        missing_members = isinstance(expected_members, int) and not isinstance(expected_members, bool) and (
            len(members) < expected_members
        )
        group_cost_kind: str | None = None  # "complete" / "partial" / "unknown"（无快照的组不归成本）
        if members:
            if not known_elapsed:
                bucket["groups_cost_unknown"] += 1  # 有快照但一个已知耗时都没有：不填 0
                group_cost_kind = "unknown"
            elif unknown_member or missing_members:
                bucket["group_cost_seconds_known_partial"].append(round(sum(known_elapsed), 3))  # 下界
                group_cost_kind = "partial"
            else:
                bucket["group_cost_seconds"].append(round(sum(known_elapsed), 3))
                group_cost_kind = "complete"
            if unknown_member:
                bucket["groups_with_unknown_members"] += 1
        if missing_members:
            bucket["groups_with_missing_members"] += 1
        if row.get("drop_stage") == "put_aborted":
            reasons: set[str] = set()
            for member in row.get("aborted_members") or []:
                snap = snapshots_by_attempt.get(_scoped(row, (member or {}).get("physical_attempt_id")))
                if snap is None:
                    bucket["root_cause_reasons"]["<no_snapshot>"] += 1
                    reasons.add("<no_snapshot>")
                    continue
                failure = snap.get("last_failure") or {}
                reason = str(snap.get("reason_code") or failure.get("error_type") or snap.get("termination_kind_hint") or "?")
                reasons.add(reason)
                bucket["root_cause_reasons"][reason] += 1
                cause = bucket["by_root_cause"].setdefault(reason, _new_reason_cost())
                cause["members"] += 1
                _add_member_fields(cause["member_fields"], snap)
            if reasons and group_cost_kind is not None:
                # 整组连带成本归根因集合（多根因 = 组合键，不重复计入各单项）
                cause_set = bucket["by_root_cause_set"].setdefault("|".join(sorted(reasons)), _new_reason_set_cost())
                cause_set["groups"] += 1
                if group_cost_kind == "complete":
                    cause_set["group_cost_seconds"].append(round(sum(known_elapsed), 3))
                elif group_cost_kind == "partial":
                    cause_set["group_cost_seconds_known_partial"].append(round(sum(known_elapsed), 3))
                else:
                    cause_set["groups_cost_unknown"] += 1
    unmatched = sum(
        1 for snap in snapshots_by_attempt.values()
        if not snap.get("rh2_prompt_group_id") or _scoped(snap, snap.get("rh2_prompt_group_id")) not in matched_groups
    )
    return {
        "schema_id": COST_SUMMARY_SCHEMA_ID,
        "run_id": run_id,
        "snapshots": len(snapshots_by_attempt),
        "duplicate_snapshots": duplicates,
        "unmatched_snapshots": unmatched,
        "legacy_rows": legacy_rows,
        "terminals": {key: _finish_cost_bucket(bucket) for key, bucket in sorted(buckets.items())},
        "by_task": {key: _finish_task_cost(entry) for key, entry in sorted(by_task.items())},
        "rows_skipped": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rh2 W4：fully-async buffer 组级事件 run 结束汇总")
    parser.add_argument("paths", nargs="+", help="事件目录（MILES_RH2_EVENT_DIR）或 jsonl 文件")
    parser.add_argument("--run-id", default=None, help="只统计该 run_id 的事件")
    parser.add_argument("--json", default=None, help="把汇总写到该文件（缺省打印到 stdout）")
    parser.add_argument(
        "--costs", action="store_true",
        help="N1：输出 attempt_cost_snapshot 与组终局事件连接后的成本汇总（缺省仍是组级汇总）",
    )
    args = parser.parse_args(argv)
    rows = list(iter_event_rows(args.paths))
    summary = (
        summarize_attempt_costs(rows, run_id=args.run_id) if args.costs
        else summarize_group_events(rows, run_id=args.run_id)
    )
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=False)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - 命令行入口
    raise SystemExit(main())
