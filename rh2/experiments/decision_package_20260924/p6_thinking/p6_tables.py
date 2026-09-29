#!/usr/bin/env python3
"""#6 汇总：只从 p6_replay.py 落盘的 JSONL/JSON（外加 B 线 stats 与 adapter turns 留证）复算全部数字。

输入：runs/decision_package_20260924/p6_thinking/{replay_turns,replay_pairs,replay_coverage}.jsonl、
      task_tool_schema_cost.json、provenance.json；runs/base_probe_20260922/cross_trajectory_stats.json；
      runs/base_probe_20260922/remote/gateway/q36_adapter/*.turns.jsonl（只数 Task* 工具调用）。
输出：summary.json（全部表的机器可读版）与 tables.txt（人读版）。
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
OUT = REPO / "runs/decision_package_20260924/p6_thinking"
VARIANTS = ["current", "a_smoosh", "a2_smoosh_all_text", "b_preserve", "c_no_task_reminder"]
SHORT = {a: a.replace("bp22-qwen3-6-35b-a3b-", "") for a in []}


def short(att: str) -> str:
    return att.replace("bp22-qwen3-6-35b-a3b-", "")


def pct(xs: list[int], q: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main() -> None:
    turns = load_jsonl(OUT / "replay_turns.jsonl")
    pairs = load_jsonl(OUT / "replay_pairs.jsonl")
    cov = load_jsonl(OUT / "replay_coverage.jsonl")
    tool_cost = json.loads((OUT / "task_tool_schema_cost.json").read_text())
    prov = json.loads((OUT / "provenance.json").read_text())
    bstats = json.loads((REPO / "runs/base_probe_20260922/cross_trajectory_stats.json").read_text())
    b_by_att = {a["attempt_id"]: a for a in bstats["attempts"] if str(a.get("solver", "")).startswith("qwen3.6")}

    T = defaultdict(list)  # (variant, att) -> turn rows (seq order)
    for t in turns:
        T[(t["variant"], t["attempt"])].append(t)
    P = defaultdict(list)
    for p in pairs:
        P[(p["variant"], p["attempt"])].append(p)
    C = {(c["variant"], c["attempt"]): c for c in cov}
    atts = sorted({t["attempt"] for t in turns})
    summary: dict = {"provenance": prov}

    # ------------------------------------------------------------------ validation
    cur_turns = [t for t in turns if t["variant"] == "current"]
    summary["validation"] = {
        "turns": len(cur_turns),
        "attempts": len(atts),
        "current_prompt_len_equals_recorded_prompt_tokens": sum(t["matches_recorded"] for t in cur_turns),
        "reencoded_output_len_equals_recorded_output_tokens": sum(t["output_reencode_len_match"] for t in cur_turns),
        "recorded_strict_decreases_from_adapter_log": sum(
            1
            for a in atts
            for x, y in zip([t["recorded_prompt_tokens"] for t in T[("current", a)]], [t["recorded_prompt_tokens"] for t in T[("current", a)]][1:])
            if y < x
        ),
    }

    # ------------------------------------------------------------------ table 1: status quo per attempt
    t1 = []
    tot = Counter()
    seg_checks = Counter()
    for a in atts:
        ps = P[("current", a)]
        ins_pairs = {p["seq_to"] for p in ps if p["insertions"]}
        drop_pairs = {p["seq_to"] for p in ps if p["thinking_only_blocks"] > 0}
        kinds = Counter(x["kind"] for p in ps for x in p["insertions"])
        first_kinds = Counter(x["kind"] for x in T[("current", a)][0]["insertions_in_this_request"])
        row = {
            "attempt": short(a),
            "turns": len(T[("current", a)]),
            "pairs": len(ps),
            "ins_task_reminder": kinds.get("task_reminder", 0),
            "ins_file_modified": kinds.get("file_modified", 0),
            "ins_skill_body": kinds.get("skill_body", 0),
            "ins_total": sum(kinds.values()),
            "seq1_skill_listing": first_kinds.get("skill_listing", 0),
            "thinking_drop_pairs": len(drop_pairs),
            "insertion_pairs_eq_drop_pairs": ins_pairs == drop_pairs,
            "strict_decrease": sum(p["strict_decrease"] for p in ps),
            "prompt_nonprefix": sum(not p["prompt_prefix_ok"] for p in ps),
            "drop_pairs_with_prompt_prefix_intact": sum(1 for p in ps if p["thinking_only_blocks"] > 0 and p["prompt_prefix_ok"]),
            "drop_pairs_before_response": sum(1 for p in ps if p["thinking_only_blocks"] > 0 and p["divergence_position"] == "before_response"),
            "asst_blocks_thinking_dropped": sum(p["thinking_only_blocks"] for p in ps),
            "net_tokens_dropped": sum(p["thinking_net_tokens_dropped"] for p in ps),
            "other_drift_pairs": sum(1 for p in ps if p["other_diff_blocks"] > 0),
            "max_prompt": max(t["prompt_len"] for t in T[("current", a)]),
            "bline_thinking_cleared_events": (b_by_att.get(a) or {}).get("thinking_cleared_events"),
            "bline_max_prompt_tokens": (b_by_att.get(a) or {}).get("max_prompt_tokens"),
        }
        for p in ps:
            for s in p.get("dropped_think_segments", []):
                seg_checks["segments"] += 1
                seg_checks["starts_with_<think>"] += int(s["starts_with_think_tag"])
                seg_checks["ends_with_</think>\\n\\n"] += int(s["ends_with_think_close"])
                seg_checks["in_last_response_block"] += int(s["is_last_response_block"])
        t1.append(row)
        for k, v in row.items():
            if isinstance(v, bool):
                tot[k] += int(v)
            elif isinstance(v, int) and k not in ("max_prompt", "bline_max_prompt_tokens", "bline_thinking_cleared_events"):
                tot[k] += v
    covered = [r for r in t1 if r["bline_thinking_cleared_events"] is not None]
    summary["table1_status_quo"] = {
        "rows": t1,
        "totals": dict(tot),
        "dropped_segment_checks": dict(seg_checks),
        "bline_compare_17": {
            "n_attempts": len(covered),
            "bline_sum": sum(r["bline_thinking_cleared_events"] for r in covered),
            "replay_drop_pairs_sum": sum(r["thinking_drop_pairs"] for r in covered),
            "replay_role_system_insertions_sum": sum(r["ins_task_reminder"] + r["ins_file_modified"] for r in covered),
            "per_attempt_equal_to_role_system_insertions": sum(
                1 for r in covered if r["bline_thinking_cleared_events"] == r["ins_task_reminder"] + r["ins_file_modified"]
            ),
            "per_attempt_equal_to_drop_pairs": sum(1 for r in covered if r["bline_thinking_cleared_events"] == r["thinking_drop_pairs"]),
            "mismatches": [
                {k: r[k] for k in ("attempt", "bline_thinking_cleared_events", "thinking_drop_pairs", "ins_skill_body")}
                for r in covered
                if r["bline_thinking_cleared_events"] != r["thinking_drop_pairs"]
            ],
        },
    }

    # ------------------------------------------------------------------ table 2: variants, totals
    t2 = {}
    for v in VARIANTS:
        ps = [p for a in atts for p in P[(v, a)]]
        ts = [t for a in atts for t in T[(v, a)]]
        cs = [C[(v, a)] for a in atts]
        L = [t["prompt_len"] for t in ts]
        # idealised prefix-cache prefill: first request full, then L_{n+1} - cp_held
        prefill = sum(T[(v, a)][0]["prompt_len"] for a in atts) + sum(p["L_to"] - p["cp_held"] for p in ps)
        t2[v] = {
            "pairs": len(ps),
            "clean": sum(p["cause"] == "clean" for p in ps),
            "thinking_only": sum(p["cause"] == "thinking_only" for p in ps),
            "thinking_and_other": sum(p["cause"] == "thinking_and_other" for p in ps),
            "other_only": sum(p["cause"] == "other_only" for p in ps),
            "strict_decrease": sum(p["strict_decrease"] for p in ps),
            "prompt_nonprefix": sum(not p["prompt_prefix_ok"] for p in ps),
            "fork_events": sum(len(c["fork_events"]) for c in cs),
            "fork_events_before_response": sum(1 for c in cs for f in c["fork_events"] if f["position"] == "before_response"),
            "training_rows": sum(c["training_rows"] for c in cs),
            "routing_leaves": sum(c["routing_leaves"] for c in cs),
            "turns_trained": sum(c["turns_trained"] for c in cs),
            "turns_generated": sum(c["turns_generated"] for c in cs),
            "trainable_tokens_total": sum(c["trainable_tokens_total"] for c in cs),
            "input_tokens_total": sum(c["input_tokens_total"] for c in cs),
            "prompt_len_mean": round(statistics.mean(L), 1),
            "prompt_len_p50": round(pct(L, 0.5), 1),
            "prompt_len_p90": round(pct(L, 0.9), 1),
            "prompt_len_max": max(L),
            "prompt_tokens_sum": sum(L),
            "turns_prompt_gt_32768": sum(x > 32768 for x in L),
            "turns_prompt_gt_65536": sum(x > 65536 for x in L),
            "turns_prompt_gt_131072": sum(x > 131072 for x in L),
            "prefill_tokens_ideal_prefix_cache": prefill,
        }
    # fork-event attribution: events present in current but not in b_preserve
    ev = {v: {(a, f["turn_index"]) for a in atts for f in C[(v, a)]["fork_events"]} for v in VARIANTS}
    summary["table2_variants"] = t2
    summary["fork_event_sets"] = {
        "b_subset_of_current": ev["b_preserve"] <= ev["current"],
        "current_minus_b": len(ev["current"] - ev["b_preserve"]),
        "b_events": sorted([list(x) for x in ev["b_preserve"]]),
        "a_minus_b": sorted([list(x) for x in ev["a_smoosh"] - ev["b_preserve"]]),
        "c_minus_b": sorted([list(x) for x in ev["c_no_task_reminder"] - ev["b_preserve"]]),
    }
    # residual thinking-drop pairs per variant (what each option leaves behind)
    summary["residual_thinking_drop_pairs"] = {
        v: [
            {"attempt": short(p["attempt"]), "seq_to": p["seq_to"], "insertion_kinds": p["insertion_kinds"]}
            for a in atts
            for p in P[(v, a)]
            if p["thinking_only_blocks"] > 0
        ]
        for v in VARIANTS
    }
    # residual non-thinking drift categories (same in every variant) -- first differing text
    cats = Counter()
    for a in atts:
        for p in P[("b_preserve", a)]:
            if p["cause"] == "clean":
                continue
            ex = p["other_diff_examples"][0]
            o, n = ex["old_around"], ex["new_around"]
            i = 0
            while i < min(len(o), len(n)) and o[i] == n[i]:
                i += 1
            if n[i:].startswith("replace_all>") and "replace_all" not in o:
                cats["cc_adds_replace_all_false"] += 1
            elif o[i:].startswith("cd /testbed && "):
                cats["cc_strips_cd_testbed_prefix"] += 1
            elif "<think>" in o[max(0, i - 12) : i + 12] or "</think>" in n[i : i + 12]:
                cats["empty_or_unclosed_think_rerender"] += 1
            else:
                cats["cc_reorders_or_drops_params"] += 1
    summary["residual_non_thinking_drift_categories_b"] = dict(cats)

    # ------------------------------------------------------------------ table 3: per attempt length cost
    t3 = []
    for a in atts:
        r = {"attempt": short(a), "turns": len(T[("current", a)])}
        for v in VARIANTS:
            ts = T[(v, a)]
            L = [t["prompt_len"] for t in ts]
            r[f"{v}.max"] = max(L)
            r[f"{v}.final"] = L[-1]
            r[f"{v}.sum"] = sum(L)
            r[f"{v}.rows"] = C[(v, a)]["training_rows"]
            r[f"{v}.input_tokens"] = C[(v, a)]["input_tokens_total"]
            r[f"{v}.fork_events"] = len(C[(v, a)]["fork_events"])
        r["b_minus_current.max"] = r["b_preserve.max"] - r["current.max"]
        r["b_minus_current.sum"] = r["b_preserve.sum"] - r["current.sum"]
        r["b_over_current.sum_pct"] = round(100 * (r["b_preserve.sum"] / r["current.sum"] - 1), 1)
        r["b_over_current.max_pct"] = round(100 * (r["b_preserve.max"] / r["current.max"] - 1), 1)
        r["a_minus_current.max"] = r["a_smoosh.max"] - r["current.max"]
        r["a_minus_current.sum"] = r["a_smoosh.sum"] - r["current.sum"]
        r["b_over_current.input_tokens_pct"] = round(100 * (r["b_preserve.input_tokens"] / r["current.input_tokens"] - 1), 1)
        # thinking visibility at the final request
        for v in ("current", "a_smoosh", "b_preserve"):
            last = T[(v, a)][-1]
            r[f"{v}.final_n_asst"] = last["n_assistant"]
            r[f"{v}.final_n_asst_with_thinking"] = last["n_assistant_rendered_with_thinking"]
        t3.append(r)
    summary["table3_per_attempt_lengths"] = t3

    # ------------------------------------------------------------------ table 4: per-insertion placement delta (a2 vs b)
    deltas = []
    for a in atts:
        ta, tb = T[("a2_smoosh_all_text", a)], T[("b_preserve", a)]
        prev = 0
        for x, y, tc in zip(ta, tb, T[("current", a)]):
            d = x["prompt_len"] - y["prompt_len"]
            n_ins = len([i for i in tc["insertions_in_this_request"] if i["kind"] != "skill_listing"])
            if d != prev or n_ins:
                deltas.append({"attempt": short(a), "seq": x["seq"], "step": d - prev, "n_new_insertions": n_ins,
                               "kinds": [i["kind"] for i in tc["insertions_in_this_request"]]})
            prev = d
    step_by_kind = defaultdict(Counter)
    for dd in deltas:
        key = ",".join(dd["kinds"]) or "none"
        step_by_kind[key][dd["step"]] += 1
    summary["table4_reminder_placement_token_delta_a2_minus_b"] = {
        "per_step": deltas,
        "step_histogram_by_kind": {k: dict(v) for k, v in step_by_kind.items()},
    }

    # ------------------------------------------------------------------ table 5: candidate (c) facts
    t5 = []
    gw = REPO / "runs/base_probe_20260922/remote/gateway/q36_adapter"
    for a in atts:
        calls = Counter()
        for row in load_jsonl(gw / f"{a}.turns.jsonl"):
            for tc in (row.get("parsed") or {}).get("tool_calls") or []:
                calls[tc["function"]["name"]] += 1
        task_calls = {k: v for k, v in calls.items() if k.startswith("Task")}
        rem_seqs = [p["seq_to"] for p in P[("current", a)] if p["insertion_kinds"].get("task_reminder")]
        t5.append(
            {
                "attempt": short(a),
                "task_reminders": len(rem_seqs),
                "reminder_request_seqs": rem_seqs,
                "reminder_intervals": [y - x for x, y in zip(rem_seqs, rem_seqs[1:])],
                "task_tool_calls": task_calls,
                "total_tool_calls": sum(calls.values()),
                "task_tools_in_tool_list": tool_cost[a]["task_tools"],
                "task_tool_schema_tokens": tool_cost[a]["task_tool_schema_tokens"],
                "todo_v2_tools_schema_tokens": tool_cost[a]["todo_v2_tools_schema_tokens"],
                "per_task_tool_schema_tokens": tool_cost[a]["per_task_tool_schema_tokens"],
                "system_plus_tools_tokens_all": tool_cost[a]["system_plus_tools_tokens_all"],
            }
        )
    summary["table5_candidate_c"] = {
        "rows": t5,
        "totals": {
            "task_reminders": sum(r["task_reminders"] for r in t5),
            "attempts_with_task_tool_calls": sum(1 for r in t5 if r["task_tool_calls"]),
            "task_tool_calls": sum(sum(r["task_tool_calls"].values()) for r in t5),
            "total_tool_calls": sum(r["total_tool_calls"] for r in t5),
            "task_tool_schema_tokens_values": sorted({r["task_tool_schema_tokens"] for r in t5}),
            "reminder_interval_hist": dict(Counter(i for r in t5 for i in r["reminder_intervals"])),
            "first_reminder_seq_hist": dict(Counter(r["reminder_request_seqs"][0] for r in t5 if r["reminder_request_seqs"])),
        },
    }

    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))

    # ------------------------------------------------------------------ human-readable tables
    lines = []
    w = lines.append
    w("# p6 thinking replay tables (generated by p6_tables.py; numbers from replay_*.jsonl)")
    w(json.dumps(summary["validation"], ensure_ascii=False))
    w("")
    w("## T1 status quo (variant=current)")
    cols = ["attempt", "turns", "ins_task_reminder", "ins_file_modified", "ins_skill_body", "thinking_drop_pairs",
            "insertion_pairs_eq_drop_pairs", "strict_decrease", "prompt_nonprefix", "drop_pairs_with_prompt_prefix_intact",
            "asst_blocks_thinking_dropped", "net_tokens_dropped", "other_drift_pairs", "max_prompt",
            "bline_thinking_cleared_events", "bline_max_prompt_tokens"]
    w("\t".join(cols))
    for r in t1:
        w("\t".join(str(r[c]) for c in cols))
    w("TOTAL\t" + json.dumps(summary["table1_status_quo"]["totals"], ensure_ascii=False))
    w("segments\t" + json.dumps(seg_checks, ensure_ascii=False))
    w("bline17\t" + json.dumps(summary["table1_status_quo"]["bline_compare_17"], ensure_ascii=False))
    w("")
    w("## T2 variants (totals over 22 attempts / 617 turns / 595 pairs)")
    keys = list(next(iter(t2.values())).keys())
    w("metric\t" + "\t".join(VARIANTS))
    for k in keys:
        w(k + "\t" + "\t".join(str(t2[v][k]) for v in VARIANTS))
    w("fork_event_sets\t" + json.dumps(summary["fork_event_sets"], ensure_ascii=False))
    w("residual_thinking_drop_pairs\t" + json.dumps(summary["residual_thinking_drop_pairs"], ensure_ascii=False))
    w("residual_non_thinking_drift_categories\t" + json.dumps(summary["residual_non_thinking_drift_categories_b"]))
    w("")
    w("## T3 per attempt: prompt max / sum and training input tokens")
    cols3 = ["attempt", "turns", "current.max", "a_smoosh.max", "b_preserve.max", "b_minus_current.max", "b_over_current.max_pct",
             "current.sum", "b_preserve.sum", "b_minus_current.sum", "b_over_current.sum_pct", "current.rows", "b_preserve.rows",
             "current.input_tokens", "a_smoosh.input_tokens", "b_preserve.input_tokens", "c_no_task_reminder.input_tokens",
             "b_over_current.input_tokens_pct", "current.fork_events", "a_smoosh.fork_events", "b_preserve.fork_events",
             "c_no_task_reminder.fork_events", "current.final_n_asst", "current.final_n_asst_with_thinking",
             "a_smoosh.final_n_asst_with_thinking", "b_preserve.final_n_asst_with_thinking"]
    w("\t".join(cols3))
    for r in t3:
        w("\t".join(str(r[c]) for c in cols3))
    w("")
    w("## T4 reminder placement delta (a2 - b) step histogram by insertion kind")
    w(json.dumps(summary["table4_reminder_placement_token_delta_a2_minus_b"]["step_histogram_by_kind"], ensure_ascii=False))
    w("")
    w("## T5 candidate (c)")
    for r in t5:
        w(json.dumps(r, ensure_ascii=False))
    w("TOTAL " + json.dumps(summary["table5_candidate_c"]["totals"], ensure_ascii=False))
    (OUT / "tables.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
