#!/usr/bin/env python3
"""R2E 期望映射的来源三方比对（只读；2026-09-24 晚，关闭 known_issues 的 expected_provenance_mixed 族）。

对每题把三份逐键状态放在一起（都用固定的同一套上游规则 `parse_log_pytest` + `normalize_status_map` 解析）：
  E  来源期望（原始行 `expected_output_json`，修订前原件）
  H  来源宿主机执行记录：原始行 `execution_result_content.new_commit_res_stdout`（修复提交上的运行，R2E 生成期望时的执行）
  I  发布镜像里的 gold 实测：R-f 真实 RH2 gold 账本的评分日志（修订前材料，Start/End 标记段）
输出每题 E≠H、E≠I、H≠I 的键数与示例，以及按关系的分组。只标事实，不改材料：E≠I 的键就是"gold 在镜像里拿不到来源定义"
的来源（09-24 后都已归因或按用户批准修订）；E=I≠H 说明期望与镜像一致、宿主机记录反而不同。

用法（从 rh2/）：
  .venv/bin/python scripts/r2e_env/expected_provenance.py --repo-root .. \\
      --gold-ledger ../runs/r2e_rf_20260923/remote/ledger_r2e_all_gold_local.jsonl --out-json <文件> --out-md <文件>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repoharness2.envpack import scoring  # noqa: E402
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest  # noqa: E402


def rh2_segment(text: str) -> str:
    start, end = scoring.R2E_EVAL_START_MARKER, scoring.R2E_EVAL_END_MARKER
    if start not in text:
        return ""
    seg = text.split(start, 1)[1]
    return seg.split(end, 1)[0] if end in seg else ""


def diff(a: dict[str, str], b: dict[str, str]) -> list[tuple[str, str | None, str | None]]:
    return sorted((k, a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--gold-ledger", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve()
    raw = root / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
    rows = {f"{r['repo_name']}__{r['commit_hash']}": r for r in
            (json.loads(x) for x in raw.read_text(encoding="utf-8").splitlines() if x.strip())}
    gold_logs = {}
    for line in Path(args.gold_ledger).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            p = Path((rec.get("log") or {}).get("path") or "")
            if p.is_file() and rec["instance_id"] not in gold_logs:
                gold_logs[rec["instance_id"]] = p.read_text(encoding="utf-8", errors="replace")
    out = {}
    for iid, row in sorted(rows.items()):
        e = normalize_status_map(json.loads(row["expected_output_json"]))
        erc = json.loads(row["execution_result_content"])
        h = normalize_status_map(parse_log_pytest(erc.get("new_commit_res_stdout") or ""))
        i = normalize_status_map(parse_log_pytest(rh2_segment(gold_logs.get(iid, "")))) if iid in gold_logs else None
        d_eh, d_ei = diff(e, h), (diff(e, i) if i is not None else None)
        d_hi = diff(h, i) if i is not None else None
        if d_ei is None:
            rel = "no_image_log"
        elif not d_eh and not d_ei:
            rel = "E=H=I"
        elif not d_ei:
            rel = "E=I≠H"
        elif not d_eh:
            rel = "E=H≠I"
        else:
            rel = "E≠H, E≠I"
        out[iid] = {"relation": rel, "n_expected": len(e), "n_host": len(h), "n_image": None if i is None else len(i),
                    "E_vs_H": d_eh, "E_vs_I": d_ei, "H_vs_I": d_hi}
    Path(args.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    groups: dict[str, list[str]] = {}
    for iid, res in out.items():
        groups.setdefault(res["relation"], []).append(iid)
    lines = ["| 关系 | 题数 | 题 |", "| --- | --- | --- |"]
    for rel in ("E=H=I", "E=I≠H", "E=H≠I", "E≠H, E≠I", "no_image_log"):
        ids = groups.get(rel, [])
        if ids:
            lines.append(f"| {rel} | {len(ids)} | {', '.join(x.split('__')[0] + ' `' + x.split('__')[1][:8] + '`' for x in ids)} |")
    lines += ["", "| 题 | 关系 | E≠H 键数（示例） | E≠I 键数（示例） |", "| --- | --- | --- | --- |"]
    for iid, res in out.items():
        if res["relation"] == "E=H=I":
            continue

        def show(d):
            if d is None:
                return "—"
            ex = "; ".join(f"`{k}` {a}→{b}" for k, a, b in d[:2])
            return f"{len(d)}（{ex}）" if d else "0"
        lines.append(f"| {iid.split('__')[0]} `{iid.split('__')[1][:8]}` | {res['relation']} | {show(res['E_vs_H'])} | {show(res['E_vs_I'])} |")
    Path(args.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
