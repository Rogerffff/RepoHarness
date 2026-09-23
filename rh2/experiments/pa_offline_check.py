"""P-A 规则离线核对：对一份重放账本 + eval 日志 / sidecar，重算触发条件、失败形状与"若接入 P-A 会落到哪一路"。

用法：python experiments/pa_offline_check.py --ledger <ledger.jsonl> [--ledger ...] --logs <eval_logs_dir> [--qual-ledger <ledger.jsonl>]
输出：每行一条（task / kind / outcome / trigger / shape / install rc / test rc / conftest 触碰 / 资格 / 预期落点），末尾汇总。
编译复证需要容器，这里只标 "needs_probe"。
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from repoharness2.grading.manager import classify_execution_failure_shape


def _rows(paths):
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield Path(p).name, json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", action="append", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--qual-ledger", action="append", default=[])
    ns = ap.parse_args()
    qual: dict[str, dict] = {}
    for name, row in _rows(ns.qual_ledger):
        rep = row.get("report") or {}
        vd = row.get("verdict_diagnostics") or {}
        if (row.get("candidate") or {}).get("kind") in ("gold", "noop") and rep.get("outcome") in ("resolved", "unresolved") \
                and rep.get("failure_category") in (None, "tests_failed") and vd and len(vd.get("reference_missing") or []) == 0:
            qual[row["task_id"]] = {"source": f"{name}:{rep.get('report_id')}", "image": row.get("image_ref"), "local_build": row.get("image_local_build")}
    logs = Path(ns.logs)
    summary = Counter()
    for name, row in _rows(ns.ledger):
        rep = row.get("report") or {}
        vd = row.get("verdict_diagnostics") or {}
        inst = row.get("install") or {}
        log_path = (row.get("log") or {}).get("path")
        text = None
        if log_path:
            cand = logs / Path(log_path).name
            if cand.exists():
                text = cand.read_text(encoding="utf-8", errors="replace")
        n_parsed = vd.get("num_parsed_tests")
        missing = len(vd.get("reference_missing") or [])
        trigger = None
        if vd:
            if n_parsed == 0:
                trigger = "zero_parsed"
            else:
                # 参考清单在场条数 = 四桶 - 缺席（sidecar 没有四桶，用报告计数近似：f2p_total+p2p_total 为桶数）
                bucketed = (rep.get("f2p_total") or 0) + (rep.get("p2p_total") or 0)
                if missing > 0 and bucketed - missing <= 0:
                    trigger = "reference_all_missing"
        shape = classify_execution_failure_shape(text, (row.get("test") or {}).get("rc")) if text and trigger else None
        q = qual.get(row["task_id"])
        same_image = bool(q) and q["image"] == row.get("image_ref") and q["local_build"] == row.get("image_local_build")
        if trigger is None:
            expected = "-"
        else:
            rc = (row.get("test") or {}).get("rc")
            if rc is not None and rc >= 128:
                expected = "resource(signal)"
            elif not same_image:
                expected = "unattributed:qualification"
            elif shape is None:
                expected = "unattributed:shape"
            elif inst.get("install_rc_last_command") not in (0, None) and not inst.get("install_skipped"):
                expected = "unattributed:install_rc"
            elif not [p for p in ((row.get("projection") or {}).get("included_paths") or []) if p.endswith(".py")]:
                expected = "unattributed:no_py_paths"
            else:
                expected = f"needs_probe({shape['stage']}:{shape['rule']})"
        summary[(rep.get("failure_category") or rep.get("outcome") or row.get("stage_error") or "?", trigger, expected.split("(")[0])] += 1
        print(json.dumps({
            "ledger": name, "task": row["task_id"].split("::")[-1], "kind": (row.get("candidate") or {}).get("kind"),
            "outcome": rep.get("outcome"), "category": rep.get("failure_category"), "reward": rep.get("reward"),
            "stage_error": row.get("stage_error"), "num_parsed": n_parsed, "ref_missing": missing, "trigger": trigger,
            "shape": shape and {"stage": shape["stage"], "rule": shape["rule"]},
            "install_rc": inst.get("install_rc_last_command"), "test_rc": (row.get("test") or {}).get("rc"),
            "conftest_touch": row.get("candidate_touched_conftest_or_fixture"), "test_like": row.get("candidate_test_like_paths"),
            "qualified_same_image": same_image, "expected_pa": expected,
        }, ensure_ascii=False))
    print("SUMMARY (category, trigger, expected_pa) -> n")
    for k, v in sorted(summary.items(), key=lambda kv: str(kv[0])):
        print(f"  {k} -> {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
