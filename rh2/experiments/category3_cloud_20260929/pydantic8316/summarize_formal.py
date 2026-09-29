"""汇总 pydantic-8316 正式评分账本：每个 ledger_<候选>.jsonl 一行，附评分日志中目标测试的状态行与首条断言失败摘录。
用法：python summarize_formal.py <formal 目录> [<formal 目录> ...]   输出：各目录下 summary.json，并在终端打印 Markdown 表。
"""
import json
import re
import sys
from pathlib import Path

F2P = "tests/test_utils.py::test_camel2snake[CAMELToSnake-camel_to_snake]"


def summarize(d: Path) -> list:
    rows = []
    for led in sorted(d.glob("ledger_*.jsonl")):
        r = json.loads(led.read_text().splitlines()[0])
        rep = r.get("report") or {}
        cand = r.get("candidate") or {}
        log_path = Path((r.get("log") or {}).get("path", ""))
        text = log_path.read_text(errors="replace") if log_path.is_file() else ""
        status = {m.group(2) for m in re.finditer(r"^(\S+::\S+) (PASSED|FAILED|SKIPPED|ERROR)", text, re.M)}
        counts = {k: int(m.group(1)) if (m := re.search(rf"^\s+(\d+) {k.lower()}\s*$", text, re.M)) else 0
                  for k in ("PASSED", "FAILED", "SKIPPED", "ERROR")}
        f2p_line = next((ln for ln in text.splitlines() if ln.startswith(F2P + " ")), None)
        assert_line = next((ln.strip() for ln in text.splitlines() if "AssertionError" in ln), None)
        inst = r.get("install") or {}
        rows.append({
            "candidate": led.stem.removeprefix("ledger_"),
            "patch_sha256": cand.get("patch_sha256"),
            "apply_method": cand.get("apply_method"),
            "reward": rep.get("reward"),
            "f2p": f"{rep.get('f2p_pass')}/{rep.get('f2p_total')}",
            "p2p_pass": None if rep.get("p2p_total") is None else rep["p2p_total"] - (rep.get("p2p_fail") or 0),
            "p2p_total": rep.get("p2p_total"),
            "grader_version": rep.get("grader_version"),
            "reference_missing": r.get("reference_missing_count"),
            "stage_error": r.get("stage_error"),
            "install_rc": inst.get("install_rc_last_command"),
            "test_rc": inst.get("test_rc"),
            "cleanup_removed": (r.get("cleanup") or {}).get("removed"),
            "image_id_actual": r.get("image_id_actual"),
            "image_digest_expected": r.get("image_digest_expected"),
            "derived_image_recipe": r.get("derived_image_recipe"),
            "grader_profile_digest": (r.get("policy") or {}).get("grader_profile_digest"),
            "eval_log": log_path.name,
            "eval_log_sha256": (r.get("log") or {}).get("sha256"),
            "log_counts": counts,
            "f2p_log_line": f2p_line,
            "first_assertion": assert_line,
            "_statuses": sorted(status),
        })
    (d / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    return rows


for arg in sys.argv[1:]:
    d = Path(arg)
    rows = summarize(d)
    print(f"\n### {d.name}\n")
    print("| 候选 | sha256 | reward | F2P | P2P | 日志计数 P/F/S | 首条断言失败 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for x in rows:
        sha = (x["patch_sha256"] or "—").removeprefix("sha256:")[:8]
        c = x["log_counts"]
        print(f"| {x['candidate']} | {sha} | {x['reward']} | {x['f2p']} | {x['p2p_pass']}/{x['p2p_total']} | "
              f"{c['PASSED']}/{c['FAILED']}/{c['SKIPPED']} | {x['first_assertion'] or ''} |")
