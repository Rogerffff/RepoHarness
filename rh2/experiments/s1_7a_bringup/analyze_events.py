"""bring-up 事件流（bringup_events.jsonl）-> 假设核对表 + 计时汇总（T3 收口输入）。

用法::

    python analyze_events.py --events .../bringup_events.jsonl \
        --signals .../group_repair_signals.jsonl --out .../bringup_summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--signals", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    events = [json.loads(line) for line in Path(args.events).read_text().splitlines() if line]
    signals = [json.loads(line) for line in Path(args.signals).read_text().splitlines() if line]

    summary: dict = {"n_rollouts": len(events), "n_signals": len(signals)}

    # 组账目（假设 10）：同组 n 条必须共享 group_index，且组数 = 题数
    groups = defaultdict(list)
    for event in events:
        groups[event.get("group_index")].append(event)
    summary["groups"] = {
        str(gi): {
            "n": len(items),
            "instances": sorted({i.get("instance_id") for i in items}),
            "indices": sorted(i.get("index") for i in items),
        }
        for gi, items in sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0]))
    }
    summary["assumption10_group_semantics_ok"] = all(
        len(items) == 4 and len({i.get("instance_id") for i in items}) == 1
        for items in groups.values()
    )

    # 交付/降级/失败面
    outcome_counter: Counter = Counter()
    failure_stages: Counter = Counter()
    abort_reasons: Counter = Counter()
    apply_ok_false = 0
    infra = 0
    parse_failed = 0
    delivered = 0
    for event in events:
        grading = event.get("grading") or {}
        if grading:
            outcome_counter[grading.get("outcome")] += 1
            if grading.get("failure_category") == "infra_failure":
                infra += 1
            if grading.get("failure_category") == "test_log_parse_failed":
                parse_failed += 1
                apply_ok_false += 1
        for record in event.get("failure_records") or []:
            failure_stages[f"{record['stage']}:{record['error_type']}"] += 1
        for reason in event.get("abort_reason") or []:
            if reason:
                abort_reasons[reason] += 1
        if event.get("degraded") is False and not any(event.get("remove_sample") or []):
            delivered += event.get("returned_samples") or 0
    summary["grading_outcomes"] = dict(outcome_counter)
    summary["failure_stages"] = dict(failure_stages)
    summary["abort_reasons"] = dict(abort_reasons)
    summary["delivered_samples"] = delivered
    summary["tests_error_family"] = {
        "verdict_apply_ok_false": apply_ok_false,
        "test_log_parse_failed": parse_failed,
        "infra_failure": infra,
    }

    # 假设 3（REALIGN 回填等长）与假设 2（多叶链）：失败签名统计
    summary["assumption3_backfill_mismatch"] = failure_stages.get(
        "assemble:SlimeBindingError", 0
    ) and {
        k: v
        for k, v in failure_stages.items()
        if "capture_turns_vs_mask_runs" in k or "turn_response_length" in k
    }
    summary["assumption3_hits"] = sum(
        1
        for event in events
        for record in event.get("failure_records") or []
        if "capture_turns_vs_mask_runs_mismatch" in (record.get("detail") or "")
        or "turn_response_length_mismatch" in (record.get("detail") or "")
    )
    summary["assumption2_multileaf_hits"] = sum(
        1
        for event in events
        for record in event.get("failure_records") or []
        if "leaf_facts_extractor_required" in (record.get("detail") or "")
    )

    # 假设 4：引擎 weight_version（按轮）vs 样本回填 weight_versions
    wv_engine = Counter()
    wv_sample = Counter()
    wv_mismatch = 0
    for event in events:
        engine_list = event.get("weight_versions_engine") or []
        for v in engine_list:
            wv_engine[v] += 1
        for versions in event.get("weight_versions_sample") or []:
            for v in versions:
                wv_sample[v] += 1
            if engine_list and versions and set(versions) != set(engine_list):
                wv_mismatch += 1
    summary["assumption4_weight_versions"] = {
        "engine_values": dict(wv_engine),
        "sample_values": dict(wv_sample),
        "per_sample_set_mismatch": wv_mismatch,
    }

    # 假设 6：truncated metadata
    summary["assumption6_truncated_values"] = dict(
        Counter(str(v) for event in events for v in (event.get("truncated_meta") or []))
    )

    # top-p offsets 恒等式（交付样本）：len(offsets) == response_length + 1
    topp_bad = []
    for event in events:
        lens = event.get("top_p_offsets_len") or []
        rls = event.get("response_lengths") or []
        for offsets_len, response_length in zip(lens, rls):
            if offsets_len and response_length and offsets_len != response_length + 1:
                topp_bad.append(event.get("session_id"))
    summary["top_p_offsets_violations"] = topp_bad

    # F5 计时五段汇总（交付与降级都计）
    timing_keys = (
        "image_pull_seconds",
        "env_reset_seconds",
        "prep_seconds",
        "test_seconds",
        "total_grading_seconds",
        "queue_wait_seconds",
    )
    agg = {k: [] for k in timing_keys}
    peak = []
    for event in events:
        timings = (event.get("grading") or {}).get("timings") or {}
        for k in timing_keys:
            if k in timings and timings[k] is not None:
                agg[k].append(timings[k])
        if timings.get("container_peak_memory_mb") is not None:
            peak.append(timings["container_peak_memory_mb"])
    summary["grading_timings"] = {
        k: {
            "n": len(v),
            "mean": round(sum(v) / len(v), 3) if v else None,
            "max": max(v) if v else None,
        }
        for k, v in agg.items()
    }
    summary["container_peak_memory_mb_max"] = max(peak) if peak else None
    summary["rollout_wall_seconds"] = {
        "mean": round(sum(e["wall_seconds"] for e in events) / len(events), 1) if events else None,
        "max": max((e["wall_seconds"] for e in events), default=None),
    }

    # 信号面：degraded 计数与维度
    degraded_signals = [s for s in signals if s.get("degraded")]
    summary["signals"] = {
        "total": len(signals),
        "degraded": len(degraded_signals),
        "failed_dimensions": dict(
            Counter(d for s in degraded_signals for d in s.get("failed_dimensions") or [])
        ),
    }

    Path(args.out).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
