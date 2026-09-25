#!/usr/bin/env python3
"""由逐题 `screening_record.json` 生成本轮处置总表 `results_<日期>.md`（只读记录，只写 `--out`）。

每题一行：分类、处置、依赖（配方 / 材料修订）、未完成项类型、venv 有无 pip、当前为 issue 的检查项。
表头给分类 / 处置计数与"venv 无 pip"计数。记录变了就重跑，不手改生成结果。

用法（从 rh2/）：
  .venv/bin/python scripts/r2e_env/render_results.py \\
      --tasks-dir ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/tasks \\
      --out ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/results_20260924.md \\
      --title "48 题处置（…）"
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

STATE_ORDER = ["environment_qualified", "qualified_with_recipe", "qualified_with_revision", "grading_ok_open_items",
               "held_material", "needs_decision", "unknown"]


def _pip(rec: dict) -> str:
    pip = str((rec.get("solver_conditions") or {}).get("pip") or "")
    if pip.startswith("absent"):
        return "无"
    if pip.startswith("present"):
        return "有"
    return "?"


def _depends(rec: dict) -> str:
    parts = []
    recipe = rec.get("recipe_ref") or {}
    derived = recipe.get("derived_image") or ""
    if derived and derived != "r2e_derive_v1":
        parts.append(derived)
    if recipe.get("resources") and recipe["resources"] != "default":
        parts.append(str(recipe["resources"]))
    for ref in rec.get("revision_refs") or []:
        if "#r2e-mr-" in ref:
            parts.append(ref.split("#", 1)[1])
    return "、".join(parts) or "-"


def render(tasks_dir: Path, title: str) -> str:
    rows, by_cls, by_state, no_pip = [], collections.Counter(), collections.Counter(), 0
    for d in sorted(p for p in tasks_dir.iterdir() if p.is_dir()):
        rp = d / "screening_record.json"
        if not rp.is_file():
            continue
        rec = json.loads(rp.read_text(encoding="utf-8"))
        disp = rec.get("disposition") or {}
        state, cls = disp.get("state"), rec.get("classification")
        by_cls[cls] += 1
        by_state[state] += 1
        pip = _pip(rec)
        no_pip += pip == "无"
        issues = sorted(k for k, v in (rec.get("checks") or {}).items() if (v or {}).get("status") == "issue")
        open_kinds = sorted({it.get("kind") for it in disp.get("open_items") or []})
        repo, commit = d.name.split("__", 1)
        rows.append(f"| {repo} `{commit[:8]}` | {cls} | {state} | {_depends(rec)} | {', '.join(open_kinds) or '-'} | {pip} | {', '.join(issues) or '-'} |")
    total = sum(by_state.values())
    cls_line = ", ".join(f"{k} {v}" for k, v in sorted(by_cls.items()))
    state_line = ", ".join(f"{k} {by_state[k]}" for k in STATE_ORDER if by_state.get(k))
    head = [
        f"# {title}",
        "",
        f"由 `tasks/*/screening_record.json` 经 `rh2/scripts/r2e_env/render_results.py` 生成，不手改。共 {total} 题。",
        "",
        f"处置：{state_line}。",
        f"分类：{cls_line}；venv 无 pip {no_pip}/{total}。",
        "",
        "\"依赖\"列：派生配方（默认 `r2e_derive_v1` 不列）、逐题资源配方、材料修订编号。\"未完成项\"列：`disposition.open_items` 的类型。"
        "\"issue 项\"是记录里当前状态为 issue 的检查项。",
        "",
        "| 题 | 分类 | 处置 | 依赖 | 未完成项 | pip | issue 项 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    return "\n".join(head + rows) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tasks-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    args = ap.parse_args(argv)
    text = render(Path(args.tasks_dir).resolve(), args.title)
    Path(args.out).write_text(text, encoding="utf-8")
    print(text.splitlines()[4])
    print(text.splitlines()[5])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
