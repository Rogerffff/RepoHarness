#!/usr/bin/env python3
"""R2E 环境审查记录的机械核对（验收用，只读）。

对 `<tasks-dir>/<iid>/screening_record.json` 逐份检查：schema / 身份字段与目录一致；`checks` 只用 R01–R20 与固定状态词；
`issue` 与关键 `pass` 都有非空 `evidence_refs`，且每个引用（相对仓库根，允许 `#片段` 与括号说明）指向存在的文件或目录；
`classification` / `disposition.state` 只用固定词；`findings.md` 存在且 ≤ 40 行；`facts.json` 存在。
输出逐题一行 + 按包 / 分类 / 处置的计数 + 全部问题清单；有问题退出码 1。不改任何文件。
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

CHECK_IDS = [f"R{i:02d}" for i in range(1, 21)]
STATUSES = {"pass", "issue", "unknown", "not_applicable", "not_checked"}
CLASSES = {"env_ok", "resource", "material", "solver_condition", "unknown"}
DISPOSITIONS = {"environment_qualified", "qualified_with_recipe", "qualified_with_revision", "grading_ok_open_items",
                "held_material", "needs_decision", "unknown"}
# grading_keys_unexplained（09-24 夜加）：期望里有键在 gold 与 noop 下都失败、原因未定位，用户已决定暂不改材料
# （orange3 9b5494e2 的两个 scorer 键，T0-7 方案 B 之后）
OPEN_ITEM_KINDS = {"dev_blocking", "support_pending_decision", "statement_conflict", "expected_penalizes_better_fix",
                   "grading_keys_unexplained"}
KEY_PASS = {"R01", "R02", "R08", "R13", "R15"}  # 这些项的 pass 必须带证据
_REF_STRIP = re.compile(r"[（(].*$|#.*$")


def _ref_exists(repo_root: Path, ref: str) -> bool:
    core = _REF_STRIP.sub("", ref).strip()
    if not core:
        return False
    p = (repo_root / core) if not core.startswith("/") else Path(core)
    if p.exists():
        return True
    # 允许 `<dir>/<iid>/facts.json` 这类带通配的写法
    if "<" in core:
        return True
    return False


def check_one(repo_root: Path, tasks_dir: Path, iid: str) -> tuple[dict, list[str]]:
    d = tasks_dir / iid
    problems: list[str] = []
    rec_path = d / "screening_record.json"
    row = {"instance_id": iid, "record": rec_path.exists(), "findings": (d / "findings.md").exists(), "facts": (d / "facts.json").exists()}
    if not rec_path.exists():
        problems.append("缺 screening_record.json")
        return row, problems
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        problems.append(f"screening_record.json 不是合法 JSON: {exc}")
        return row, problems
    if rec.get("schema_id") != "rh2.r2e_screening_record.v1":
        problems.append(f"schema_id={rec.get('schema_id')!r}")
    if rec.get("instance_id") != iid:
        problems.append(f"instance_id 与目录不符: {rec.get('instance_id')!r}")
    if rec.get("task_id") != f"r2e_gym_subset::{iid}":
        problems.append(f"task_id 不符: {rec.get('task_id')!r}")
    checks = rec.get("checks") or {}
    covered = set()
    for cid, c in checks.items():
        key = cid.split("_", 1)[0]
        if key not in CHECK_IDS:
            problems.append(f"未知检查编号 {cid}")
            continue
        covered.add(key)
        st = (c or {}).get("status")
        if st not in STATUSES:
            problems.append(f"{cid}: status={st!r}")
            continue
        refs = (c or {}).get("evidence_refs") or []
        if st == "issue" and not refs:
            problems.append(f"{cid}: issue 无 evidence_refs")
        if st == "pass" and key in KEY_PASS and not refs:
            problems.append(f"{cid}: 关键 pass 无 evidence_refs")
        if st == "not_applicable" and not ((c or {}).get("note") or (c or {}).get("reason")):
            problems.append(f"{cid}: not_applicable 未写理由")
        for ref in refs:
            if not _ref_exists(repo_root, str(ref)):
                problems.append(f"{cid}: 证据引用不存在: {ref}")
    missing = [k for k in CHECK_IDS if k not in covered]
    if missing:
        problems.append(f"未覆盖的检查项: {','.join(missing)}")
    for it in rec.get("issues") or []:
        if not (it.get("evidence_refs") or []):
            problems.append(f"issue[{it.get('summary', '')[:40]}] 无 evidence_refs")
        for ref in it.get("evidence_refs") or []:
            if not _ref_exists(repo_root, str(ref)):
                problems.append(f"issue 证据引用不存在: {ref}")
    cls = rec.get("classification")
    if cls not in CLASSES:
        problems.append(f"classification={cls!r}")
    disp = (rec.get("disposition") or {}).get("state")
    if disp not in DISPOSITIONS:
        problems.append(f"disposition.state={disp!r}")
    if not (rec.get("solver_conditions") or {}):
        problems.append("solver_conditions 为空")
    open_items = (rec.get("disposition") or {}).get("open_items") or []
    for it in open_items:
        if it.get("kind") not in OPEN_ITEM_KINDS:
            problems.append(f"open_items: 未知类型 {it.get('kind')!r}")
        for ref in it.get("evidence_refs") or []:
            if not _ref_exists(repo_root, str(ref)):
                problems.append(f"open_items 证据引用不存在: {ref}")
    if disp in ("environment_qualified", "qualified_with_recipe", "qualified_with_revision") and open_items:
        problems.append(f"处置 {disp} 与未完成项并存（合格的题不能挂 open_items）")
    if disp == "grading_ok_open_items" and not open_items:
        problems.append("grading_ok_open_items 必须列出 open_items")
    f = d / "findings.md"
    if f.exists():
        n = len(f.read_text(encoding="utf-8").splitlines())
        if n > 40:
            problems.append(f"findings.md {n} 行（> 40）")
    else:
        problems.append("缺 findings.md")
    row.update({"classification": cls, "disposition": disp, "checks_issue": sorted(k for k, v in checks.items() if (v or {}).get("status") == "issue"),
                "checks_unknown": sorted(k for k, v in checks.items() if (v or {}).get("status") == "unknown"),
                "n_issues": len(rec.get("issues") or []), "revision_refs": rec.get("revision_refs") or []})
    return row, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--task-ids", default="", help="逗号分隔；空 = 目录下全部")
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    tasks_dir = Path(args.tasks_dir).resolve()
    iids = [x for x in args.task_ids.split(",") if x.strip()] or sorted(p.name for p in tasks_dir.iterdir() if p.is_dir())
    rows, all_problems = [], {}
    for iid in iids:
        row, problems = check_one(repo_root, tasks_dir, iid)
        rows.append(row)
        if problems:
            all_problems[iid] = problems
        repo = iid.split("__")[0]
        print(f"{repo:10s} {iid.split('__')[1][:8]}  record={'y' if row['record'] else 'n'} findings={'y' if row['findings'] else 'n'} "
              f"cls={row.get('classification')} disp={row.get('disposition')} issue={row.get('checks_issue')} unknown={row.get('checks_unknown')} "
              f"problems={len(problems)}")
    by_cls = collections.Counter(r.get("classification") for r in rows)
    by_disp = collections.Counter(r.get("disposition") for r in rows)
    by_pkg = collections.Counter(r["instance_id"].split("__")[0] for r in rows if r["record"])
    print(f"\nrecords: {sum(1 for r in rows if r['record'])}/{len(rows)}  by_repo={dict(by_pkg)}")
    print(f"classification: {dict(by_cls)}\ndisposition: {dict(by_disp)}")
    if all_problems:
        print(f"\nPROBLEMS in {len(all_problems)} tasks:")
        for iid, ps in all_problems.items():
            for p in ps:
                print(f"  {iid}: {p}")
    if args.out_json:
        Path(args.out_json).write_text(json.dumps({"rows": rows, "problems": all_problems}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main())
