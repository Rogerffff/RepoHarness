"""离线分析：读回传的 dp_* 运行目录（桩落盘的请求体 + attempt.json），产出可复算的数字。

    python analyze_p8910.py <remote_dir> <out_json>

口径：工具字符数 = json.dumps(tool, ensure_ascii=False) 的长度（与交接包 60,863 同口径）；
system 字符数 = 各 text 块长度之和；首请求字节 = messages_000.json 文件字节数（UTF-8 原样落盘）。
"""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path

CORE = ("Bash", "Read", "Edit", "Write", "NotebookEdit")
SKILL_LISTING_MARK = "The following skills are available for use with the Skill tool"


def jlen(x) -> int:
    return len(json.dumps(x, ensure_ascii=False))


def sys_chars(body: dict) -> int:
    """system 字符数 = 各 text 块长度之和（与 first_request_facts 同口径）。"""
    s = body.get("system")
    if isinstance(s, str):
        return len(s)
    return sum(len(b.get("text", "")) for b in (s or []) if isinstance(b, dict))


def sys_text(body: dict) -> str:
    s = body.get("system")
    if isinstance(s, str):
        return s
    return "\n".join(b.get("text", "") for b in (s or []) if isinstance(b, dict))


def msg_text(m: dict) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    out = []
    for b in c or []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            out.append(b.get("text", ""))
        elif b.get("type") == "tool_result":
            cc = b.get("content")
            out.append(cc if isinstance(cc, str) else json.dumps(cc, ensure_ascii=False))
        elif b.get("type") == "tool_use":
            out.append(json.dumps(b.get("input"), ensure_ascii=False))
    return "\n".join(out)


def section(text: str, header: str) -> str | None:
    i = text.find(header)
    if i < 0:
        return None
    j = text.find("\n# ", i + len(header))
    return text[i: j if j >= 0 else len(text)]


def first_request_facts(body: dict, nbytes: int) -> dict:
    tools = body.get("tools") or []
    per = {t.get("name"): jlen(t) for t in tools}
    tools_sum = sum(per.values())
    noncore = sum(v for k, v in per.items() if k not in CORE)
    st = sys_text(body)
    sys_blocks = [len(b.get("text", "")) for b in (body.get("system") or []) if isinstance(b, dict)] if isinstance(body.get("system"), list) else [len(st)]
    msgs = body.get("messages") or []
    listing = None
    for i, m in enumerate(msgs):
        t = msg_text(m)
        if SKILL_LISTING_MARK in t:
            names = re.findall(r"^- ([A-Za-z0-9_.:-]+):", t, flags=re.M)
            listing = {"message_index": i, "role": m.get("role"), "chars": len(t), "n_skills": len(names), "skills": names,
                       "mentions_web_search": bool(re.search(r"web search", t, re.I))}
    mem = section(st, "# Memory")
    memdir = re.search(r"memory at `([^`]+)`", mem or "")
    return {
        "bytes": nbytes, "top_keys": sorted(body.keys()), "model": body.get("model"), "max_tokens": body.get("max_tokens"),
        "thinking": body.get("thinking"), "output_config": body.get("output_config"),
        "n_tools": len(tools), "tool_names": [t.get("name") for t in tools], "tools_array_chars": jlen(tools), "tools_sum_chars": tools_sum,
        "per_tool_chars": per, "per_tool_pct": {k: round(100 * v / tools_sum, 1) for k, v in per.items()} if tools_sum else {},
        "noncore_chars": noncore, "noncore_pct": round(100 * noncore / tools_sum, 1) if tools_sum else None,
        "system_block_chars": sys_blocks, "system_chars": sum(sys_blocks),
        "system_has_memory_section": mem is not None, "memory_section_chars": len(mem) if mem else 0,
        "memory_dir_in_system": memdir.group(1) if memdir else None,
        "system_mentions_skill": "Skill" in st,
        "n_messages": len(msgs), "message_chars": [(m.get("role"), len(msg_text(m))) for m in msgs],
        "messages_chars_total": sum(len(msg_text(m)) for m in msgs),
        "skill_listing": listing,
    }


def load_requests(run: Path, kind: str) -> list[tuple[Path, dict]]:
    out = []
    for p in sorted((run / "stub" / "requests").glob(f"{kind}_*.json")):
        out.append((p, json.loads(p.read_bytes())))
    return out


def analyze_run(run: Path) -> dict:
    att = json.loads((run / "attempt.json").read_text(encoding="utf-8"))
    ts = att.get("trajectory_summary") or {}
    res = ts.get("cc_result") or {}
    log = json.loads((run / "stub" / "stub_log.json").read_text(encoding="utf-8")) if (run / "stub" / "stub_log.json").exists() else []
    msgs = load_requests(run, "messages")
    cts = load_requests(run, "count_tokens")
    rec: dict = {
        "run": run.name, "label": (att.get("condition") or {}).get("label"), "condition": att.get("condition"),
        "harness_exit_code": att.get("harness_exit_code"), "termination": att.get("termination"),
        "cc_result_subtype": res.get("subtype"), "cc_is_error": res.get("is_error"), "num_turns": res.get("num_turns"),
        "terminal_reason": res.get("terminal_reason"), "result_text": (res.get("result") or "")[:300] if isinstance(res.get("result"), str) else res.get("result"),
        "modelUsage": res.get("modelUsage"), "permission_denials": res.get("permission_denials"),
        "init": ts.get("init"), "system_subtypes": ts.get("system_subtypes"), "system_events": ts.get("system_events"),
        "tool_calls": ts.get("tool_calls"), "stub_counts": att.get("stub_counts_final"), "post_run_facts": att.get("post_run_facts"),
        "cc_extra_envs_effective": att.get("cc_extra_envs_effective"), "stderr_tail": (att.get("stderr_tail") or "")[-800:],
    }
    if msgs:
        p0, b0 = msgs[0]
        rec["first_request"] = first_request_facts(b0, p0.stat().st_size)
        rec["requests"] = []
        for (p, b), e in zip(msgs, [x for x in log if x["kind"] == "messages"]):
            st = sys_text(b)
            rec["requests"].append({
                "file": p.name, "bytes": p.stat().st_size, "n_messages": len(b.get("messages") or []), "n_tools": len(b.get("tools") or []),
                "system_chars": sys_chars(b), "system_has_memory_section": "# Memory" in st, "max_tokens": b.get("max_tokens"),
                "compaction_request": e.get("compaction_request"), "usage_input_tokens_reported": e.get("usage_input_tokens_reported"),
                "ramp_j": e.get("ramp_j"), "step_kind": (e.get("step") or {}).get("kind"),
                "last_tool_result_chars": e.get("last_tool_result_chars"), "last_tool_result_is_error": e.get("last_tool_result_is_error"),
                "last_tool_result_head": (e.get("last_tool_result_text") or "")[:400],
            })
    if cts:
        rec["count_tokens"] = []
        for (p, b), e in zip(cts, [x for x in log if x["kind"] == "count_tokens"]):
            ms = b.get("messages") or []
            rec["count_tokens"].append({
                "file": p.name, "bytes": p.stat().st_size, "top_keys": sorted(b.keys()), "model": b.get("model"), "n_messages": len(ms),
                "roles": [m.get("role") for m in ms], "content_is_str": [isinstance(m.get("content"), str) for m in ms],
                "content_chars": [len(msg_text(m)) for m in ms], "n_tools": len(b.get("tools") or []),
                "returned_input_tokens": e.get("returned_input_tokens"), "chars4_estimate": e.get("chars4_estimate"),
                "path": e.get("path"),
            })
    return rec


def diff_vs(base: dict, other: dict) -> dict:
    fb, fo = base.get("first_request") or {}, other.get("first_request") or {}
    return {
        "tools_removed": sorted(set(fb.get("tool_names", [])) - set(fo.get("tool_names", []))),
        "tools_added": sorted(set(fo.get("tool_names", [])) - set(fb.get("tool_names", []))),
        "n_tools": [fb.get("n_tools"), fo.get("n_tools")],
        "tools_array_chars": [fb.get("tools_array_chars"), fo.get("tools_array_chars")],
        "system_chars": [fb.get("system_chars"), fo.get("system_chars")],
        "messages_chars_total": [fb.get("messages_chars_total"), fo.get("messages_chars_total")],
        "bytes": [fb.get("bytes"), fo.get("bytes")],
        "bytes_delta": (fo.get("bytes") or 0) - (fb.get("bytes") or 0),
        "skill_listing_chars": [(fb.get("skill_listing") or {}).get("chars"), (fo.get("skill_listing") or {}).get("chars")],
        "memory_section": [fb.get("system_has_memory_section"), fo.get("system_has_memory_section")],
    }


def system_diff(a: str, b: str) -> list[str]:
    return [ln for ln in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0) if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]


def main() -> None:
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    runs = {p.name: analyze_run(p) for p in sorted(root.glob("dp_*")) if (p / "attempt.json").exists()}
    report: dict = {"runs": runs, "diffs_vs_t10_base": {}, "system_diffs_vs_t10_base": {}}
    base = runs.get("dp_t10_base")
    if base:
        b0 = json.loads((root / "dp_t10_base" / "stub" / "requests" / "messages_000.json").read_bytes())
        for name, r in runs.items():
            if name == "dp_t10_base" or not r.get("first_request"):
                continue
            report["diffs_vs_t10_base"][name] = diff_vs(base, r)
            o0 = json.loads((root / name / "stub" / "requests" / "messages_000.json").read_bytes())
            report["system_diffs_vs_t10_base"][name] = system_diff(sys_text(b0), sys_text(o0))
        mem = section(sys_text(b0), "# Memory")
        report["baseline_memory_section_text"] = mem
    mid = root / "dp_m9_midsess"
    if mid.exists():
        bodies = [json.loads(p.read_bytes()) for p in sorted((mid / "stub" / "requests").glob("messages_*.json"))]
        report["m9_midsess_system_diffs"] = {f"req0_vs_req{i}": system_diff(sys_text(bodies[0]), sys_text(b)) for i, b in enumerate(bodies) if i > 0}
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {out} ({len(runs)} runs)")


if __name__ == "__main__":
    main()
