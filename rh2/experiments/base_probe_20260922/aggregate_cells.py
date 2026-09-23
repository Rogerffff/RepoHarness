#!/usr/bin/env python3
"""基座探针第二轮分析：聚合各格子报告（cell.md）与首轮逐条报告末尾的 JSON，产出跨轨迹统计。

输入：runs/base_probe_20260922/analysis/<task>/<solver>/cell.md（CELL_PROTOCOL 的 {"cell":…, "attempts":[…]}）
     runs/base_probe_20260922/analysis/<task>/<solver>/a*.md（REVIEW_PROTOCOL 的单条 JSON，字段较少、名字略有不同）
输出：按 solver 汇总的行为统计（答案渠道探测、读 harness 轨迹、改官方测试、草稿文件、无关工具、工具错误拆分、撞上限与因果、
     接口现象频次）+ 逐条明细表；缺字段记 None，不臆补。用法：aggregate_cells.py <analysis_root> [--out stats.json]
"""

from __future__ import annotations

import argparse
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

_JSON_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def json_blocks(text: str) -> list[dict]:
    out = []
    for m in _JSON_RE.findall(text):
        try:
            out.append(json.loads(m))
        except Exception:  # noqa: BLE001
            continue
    return out


def norm_single(j: dict, task: str, solver: str, attempt: str) -> dict:
    """首轮单条报告 JSON → 与 CELL_PROTOCOL 字段对齐（缺的填 None）。"""
    probe = j.get("answer_channel_probe")
    if probe is None:
        probe = j.get("answer_channel_suspect")
    return {
        "task": task, "solver": solver, "attempt": attempt, "attempt_id": j.get("attempt_id"), "reward": j.get("reward"),
        "process_quality": j.get("process_quality"), "repro_before_fix": j.get("repro_built"),
        "verification_run": j.get("verification_run"), "answer_channel_probe": probe,
        "answer_channel_kinds": None, "answer_channel_obtained": j.get("answer_channel_obtained"),
        "read_harness_dir": None, "scratch_files_in_candidate": None, "official_tests_modified": None,
        "non_core_tools": None, "is_error_breakdown": None,
        "hit_turn_cap": ("budget_truncation" in (j.get("labels") or [])) or None,
        "truncation_causal": None, "im_end_leak": None, "cc_param_rewrites": None, "thinking_cleared_events": None,
        "max_prompt_tokens": None, "labels": j.get("labels"), "confidence": j.get("confidence"), "source": "single",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("analysis_root")
    ap.add_argument("--out", default=None)
    ns = ap.parse_args()
    root = Path(ns.analysis_root)
    rows: dict[tuple[str, str, str], dict] = {}
    cells: list[dict] = []
    for f in sorted(glob.glob(str(root / "*" / "*" / "cell.md"))):
        task, solver = Path(f).parts[-3], Path(f).parts[-2]
        for j in json_blocks(Path(f).read_text(encoding="utf-8")):
            if "cell" in j and "attempts" in j:
                cells.append({"task": task, "solver": solver, **j["cell"]})
                for a in j["attempts"]:
                    a = {"task": task, "solver": solver, "source": "cell", **a}
                    rows[(task, solver, str(a.get("attempt")))] = a
    for f in sorted(glob.glob(str(root / "*" / "*" / "a*.md"))):
        task, solver, attempt = Path(f).parts[-3], Path(f).parts[-2], Path(f).stem
        if (task, solver, attempt) in rows:
            continue
        js = json_blocks(Path(f).read_text(encoding="utf-8"))
        if js:
            rows[(task, solver, attempt)] = norm_single(js[-1], task, solver, attempt)

    def frac(vals):
        known = [v for v in vals if v is not None]
        return (sum(1 for v in known if v), len(known))

    by_solver: dict[str, dict] = {}
    for solver in sorted({k[1] for k in rows}):
        rs = [r for k, r in rows.items() if k[1] == solver]
        kinds = defaultdict(int)
        tools = defaultdict(int)
        errs = defaultdict(int)
        for r in rs:
            for kd in (r.get("answer_channel_kinds") or []):
                kinds[kd] += 1
            for t, c in (r.get("non_core_tools") or {}).items():
                tools[t] += int(c or 0)
            for t, c in (r.get("is_error_breakdown") or {}).items():
                errs[t] += int(c or 0)
        by_solver[solver] = {
            "attempts_with_report": len(rs),
            "reward1": sum(1 for r in rs if r.get("reward") == 1),
            "repro_before_fix": frac(r.get("repro_before_fix") for r in rs),
            "verification_run": frac(r.get("verification_run") for r in rs),
            "answer_channel_probe": frac(r.get("answer_channel_probe") for r in rs),
            "answer_channel_obtained": frac(r.get("answer_channel_obtained") for r in rs),
            "answer_channel_kinds": dict(kinds),
            "read_harness_dir": frac(r.get("read_harness_dir") for r in rs),
            "official_tests_modified": frac(r.get("official_tests_modified") for r in rs),
            "scratch_files_total": sum(int(r.get("scratch_files_in_candidate") or 0) for r in rs),
            "non_core_tools": dict(tools),
            "is_error_breakdown": dict(errs),
            "hit_turn_cap": frac(r.get("hit_turn_cap") for r in rs),
            "truncation_causal_true": sum(1 for r in rs if r.get("truncation_causal") is True),
            "im_end_leak": frac(r.get("im_end_leak") for r in rs),
            "cc_param_rewrites_total": sum(int(r.get("cc_param_rewrites") or 0) for r in rs),
            "thinking_cleared_events_total": sum(int(r.get("thinking_cleared_events") or 0) for r in rs),
            "max_prompt_tokens_max": max([int(r.get("max_prompt_tokens") or 0) for r in rs] or [0]),
            "labels": dict(sorted({lab: sum(1 for r in rs if lab in (r.get("labels") or [])) for r in rs for lab in (r.get("labels") or [])}.items())),
        }
    # 逐 attempt 覆盖表（Codex 09-22 §9.3）：full_single / full_cell / task_report_partial / none
    coverage = []
    summary = root.parent / "summary_final.json"
    task_reports = {Path(f).parts[-2] for f in glob.glob(str(root / "*" / "task_investigation.md"))}
    if summary.exists():
        for a in json.loads(summary.read_text(encoding="utf-8"))["attempts"]:
            key = (a["task"], a["solver"], a["attempt"])
            if key in rows:
                kind = "full_single" if rows[key].get("source") == "single" else "full_cell"
            elif a["task"] in task_reports:
                kind = "task_report_partial"
            else:
                kind = "none"
            coverage.append({"task": a["task"], "solver": a["solver"], "attempt": a["attempt"], "reward": a.get("reward"),
                             "status": a.get("status"), "coverage": kind})
    cov_counts = defaultdict(int)
    for c in coverage:
        cov_counts[c["coverage"]] += 1
    out = {"by_solver": by_solver, "cells": cells, "coverage_counts": dict(cov_counts), "coverage": coverage,
           "attempts": sorted(rows.values(), key=lambda r: (r["task"], r["solver"], str(r["attempt"])))}
    if ns.out:
        Path(ns.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(by_solver, ensure_ascii=False, indent=1))
    print(f"attempts with report: {len(rows)} ; cells: {len(cells)} ; coverage: {dict(cov_counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
