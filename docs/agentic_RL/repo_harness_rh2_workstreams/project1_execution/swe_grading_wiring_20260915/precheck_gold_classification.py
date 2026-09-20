#!/usr/bin/env python3
"""S1-p（评分接线 2026-09-15）：gold 与真实候选补丁的静态控制面分类预检（零 Docker）。

用生产的控制面规则（`HygieneRules`：official test 文件 = test_patch 触碰路径；`DEFAULT_SWE_TEST_GLOBS`；
`DEFAULT_SWE_FORBIDDEN_GLOBS`）与 `classify_control_plane_path` 对每个补丁触碰的路径分类，列出会被
可信评分投影**忽略（不重放）**的路径。目的：在真实链跑 gold/候选之前，先解释"gold 应 resolved"的预期例外。

只做路径级分类：不构造 FrozenPatchArtifact、不判断 symlink/结构安全（那由 classify_frozen_patch 在 driver 里做）。
从仓库根运行：`rh2/.venv/bin/python <本文件> [--out precheck.md]`。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / "rh2/src"))

from repoharness2.grading.manager import (  # noqa: E402
    DEFAULT_SWE_FORBIDDEN_GLOBS,
    DEFAULT_SWE_TEST_GLOBS,
    HygieneRules,
    patch_touched_paths,
)
from repoharness2.grading.trusted_projection import classify_control_plane_path  # noqa: E402

DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
GRADING = DOCS / "s2/ingest/grading_bundles_v2_v0.jsonl"
VALIDATION = DOCS / "s2/ingest/validation_bundles_v0.jsonl"
CC_PATCHES = DOCS / "project1_execution/env_probe_20260909/ledger/cc_patches"

REPRESENTATIVES = [
    "conan-io__conan-13326", "dask__dask-7894", "getmoto__moto-6913", "iterative__dvc-5822",
    "modin-project__modin-6937", "pydantic__pydantic-8500", "Project-MONAI__MONAI-6975",
    "python__mypy-12741", "pandas-dev__pandas-48106",
]
CONTRAST_GOLD = ["Project-MONAI__MONAI-1121", "Project-MONAI__MONAI-3205", "getmoto__moto-4799", "Project-MONAI__MONAI-763"]


AFTER_PB = False  # --after-pb：按第四组 P-B 之后的规则（不再注入测试名通配）


def rules_for(grading_row: dict) -> HygieneRules:
    return HygieneRules(
        test_files=tuple(sorted(patch_touched_paths(grading_row["test_patch"]))),
        test_globs=() if AFTER_PB else DEFAULT_SWE_TEST_GLOBS,
        forbidden_globs=DEFAULT_SWE_FORBIDDEN_GLOBS,
    )


def classify(rules: HygieneRules, patch_text: str) -> dict:
    paths = sorted(patch_touched_paths(patch_text))
    out = {"replayed": [], "ignored": []}
    for p in paths:
        cls = classify_control_plane_path(rules, p)
        (out["ignored"] if cls else out["replayed"]).append((p, cls))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("precheck.md")))
    ap.add_argument("--after-pb", action="store_true", help="按 P-B 之后的规则（test_globs=()）分类")
    args = ap.parse_args()
    global AFTER_PB
    AFTER_PB = args.after_pb
    grading = {json.loads(l)["instance_id"]: json.loads(l) for l in GRADING.read_text().splitlines() if l.strip()}
    gold = {json.loads(l)["instance_id"]: json.loads(l)["golden_patch"] for l in VALIDATION.read_text().splitlines() if l.strip()}

    lines = ["# S1-p 静态控制面分类预检（gold 与真实候选）" + ("——P-B 之后的规则（test_globs=()）" if AFTER_PB else "") + "\n",
             "生成：`precheck_gold_classification.py`。规则 = 生产 `HygieneRules`（official test 文件 + `DEFAULT_SWE_TEST_GLOBS` + 保留命名空间）。"
             "\"忽略\"= 可信评分投影不重放该路径（D2-3 排除法）；本表只做路径级分类，不判结构安全。\n"]
    summary = []

    def section(title: str, items: list[tuple[str, str, str]]):
        lines.append(f"## {title}\n")
        lines.append("| 题 | 来源 | 重放路径 | 忽略路径（类别） | 预期影响 |")
        lines.append("|---|---|---|---|---|")
        for iid, origin, patch in items:
            if iid not in grading:
                lines.append(f"| {iid} | {origin} | — | — | 不在 216 题内 |")
                continue
            r = classify(rules_for(grading[iid]), patch)
            replayed = ", ".join(f"`{p}`" for p, _ in r["replayed"]) or "（无）"
            ignored = ", ".join(f"`{p}`({c})" for p, c in r["ignored"]) or "（无）"
            if not r["replayed"]:
                impact = "**全部被忽略，评分等价 noop**"
            elif r["ignored"]:
                impact = "部分被忽略；若被忽略路径承载修复则 gold/候选可能不通过"
            else:
                impact = "无影响"
            summary.append((iid, origin, len(r["replayed"]), len(r["ignored"]), impact))
            lines.append(f"| {iid} | {origin} | {replayed} | {ignored} | {impact} |")
        lines.append("")

    section("A 组代表题 gold（9）", [(i, "gold", gold[i]) for i in REPRESENTATIVES])
    section("C 组反例 gold（4）", [(i, "gold", gold[i]) for i in CONTRAST_GOLD])
    cc = []
    for f in sorted(CC_PATCHES.glob("*.diff")):
        cc.append((f.stem, "DeepSeek 候选", f.read_text(errors="replace")))
    section("B 组真实候选（24 条 DeepSeek 补丁）", cc)
    n_all_ignored = sum(1 for s in summary if s[2] == 0)
    n_partial = sum(1 for s in summary if s[2] > 0 and s[3] > 0)
    lines.insert(2, f"汇总：{len(summary)} 份补丁；全部被忽略 {n_all_ignored} 份；部分被忽略 {n_partial} 份；其余无影响。\n")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(summary)} patches, all_ignored={n_all_ignored}, partial={n_partial}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
