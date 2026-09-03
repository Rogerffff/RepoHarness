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
    "DROP_STAGES",
    "GROUP_CONSUMED_EVENT",
    "GROUP_DROP_EVENT",
    "SUMMARY_SCHEMA_ID",
    "iter_event_rows",
    "main",
    "summarize_group_events",
]

GROUP_DROP_EVENT = "group_filtered"
GROUP_CONSUMED_EVENT = "group_consumed"
DROP_STAGES: tuple[str, ...] = ("put_aborted", "dynamic_filter", "consume_stale")
SUMMARY_SCHEMA_ID = "rh2.group_event_summary.v1"
UNKNOWN_TASK = "<unknown>"


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rh2 W4：fully-async buffer 组级事件 run 结束汇总")
    parser.add_argument("paths", nargs="+", help="事件目录（MILES_RH2_EVENT_DIR）或 jsonl 文件")
    parser.add_argument("--run-id", default=None, help="只统计该 run_id 的事件")
    parser.add_argument("--json", default=None, help="把汇总写到该文件（缺省打印到 stdout）")
    args = parser.parse_args(argv)
    summary = summarize_group_events(iter_event_rows(args.paths), run_id=args.run_id)
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=False)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - 命令行入口
    raise SystemExit(main())
