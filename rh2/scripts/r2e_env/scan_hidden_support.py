#!/usr/bin/env python3
"""R2E 隐藏测试支撑缺口的批量静态扫描（只读；2026-09-24 晚，把 T0-2 / T0-5 / T0-6 的逐题发现推广到全池）。

R2E 把上游测试文件搬进 `r2e_tests/`（不一定带上 conftest、夹具、同目录资源，也不改测试里对原模块路径的引用），
gold 按规则又排除所有测试路径。于是出现三类"测试支撑缺口"：被掩盖的用例恒 ERROR / FAILED（验证强度打折），
或者用了修复前的支撑常量（datalad 58ba5165）。本脚本对每题的隐藏测试原文（来源行 execution_result_content）
与修复提交（parsed_commit_content）做五项检查，只标候选，不下结论：

  S1 `__file__` 相对资源：同一行里 `__file__` 与字符串字面量同时出现时，取字面量里的文件名，隐藏测试目录里没有 → 候选缺夹具
  S2 字符串自引用原模块路径：字面量形如 `tests.<模块>…`、`<包>.tests.<模块>…`（点分路径）→ 候选类身份错位
  S3 从仓库测试树导入：`from/import <包>.tests.…` / `tests.…`；若该模块文件被修复提交改过 → 候选"支撑用了修复前版本"
  S4 用到但隐藏目录里没定义的 fixture：pytest 风格测试函数（非 unittest 类方法）的参数，减去隐藏测试里定义的 fixture、
     parametrize 参数名与 pytest 内置 fixture → 候选缺 fixture（与 S5 的实测互核）
  S5 R-f gold 日志实测：`fixture '<名>' not found` 的次数与名字（真实评分链的原始日志）

用法（从 rh2/）：
  .venv/bin/python scripts/r2e_env/scan_hidden_support.py --repo-root .. \\
      --gold-ledger ../runs/r2e_rf_20260923/remote/ledger_r2e_all_gold_local.jsonl --out-json <文件> --out-md <文件>
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

PYTEST_BUILTIN_FIXTURES = {
    "request", "tmp_path", "tmpdir", "tmp_path_factory", "tmpdir_factory", "monkeypatch", "capsys", "capsysbinary",
    "capfd", "capfdbinary", "caplog", "recwarn", "pytestconfig", "cache", "record_property", "record_xml_attribute",
    "record_testsuite_property", "doctest_namespace", "testdir", "pytester", "self", "cls",
}
_DOTTED = re.compile(r"""['"]((?:[A-Za-z_][A-Za-z0-9_]*\.)*tests?(?:\.[A-Za-z_][A-Za-z0-9_]*)+)['"]""")
_LITERAL = re.compile(r"""['"]([^'"\s]+\.[A-Za-z0-9]{1,8})['"]""")


def _hidden_files(row: dict) -> dict[str, str]:
    doc = json.loads(row.get("execution_result_content") or "{}")
    return dict(zip(doc.get("test_file_names") or [], doc.get("test_file_codes") or []))


def _fix_changed_files(row: dict) -> set[str]:
    """修复提交改过的文件路径（parsed_commit_content.file_diffs[].header.file.path）。"""

    doc = json.loads(row["parsed_commit_content"])
    return {((fd.get("header") or {}).get("file") or {}).get("path") for fd in doc.get("file_diffs") or []} - {None}


def _fixture_names(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                text = ast.unparse(target)
                if text.endswith("fixture"):
                    name = node.name
                    if isinstance(dec, ast.Call):
                        for kw in dec.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                name = kw.value.value
                    names.add(name)
    return names


def _parametrize_names(func: ast.FunctionDef) -> set[str]:
    out = set()
    for dec in func.decorator_list:
        if isinstance(dec, ast.Call) and ast.unparse(dec.func).endswith("parametrize") and dec.args:
            a0 = dec.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
                out |= {x.strip() for x in a0.value.split(",") if x.strip()}
            elif isinstance(a0, (ast.List, ast.Tuple)):
                out |= {e.value for e in a0.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return out


def _uses_positional_injection(func: ast.FunctionDef) -> bool:
    """nose / datalad 风格装饰器按位置追加参数（with_tempfile、with_tree、with_testrepos…）：参数不是 fixture。"""

    for dec in func.decorator_list:
        text = ast.unparse(dec.func if isinstance(dec, ast.Call) else dec)
        if text.startswith(("with_", "mock.patch", "patch", "skip_", "assert_cwd_unchanged", "serve_path_via_http")) or ".with_" in text:
            return True
    return False


def scan_task(row: dict) -> dict:
    files = _hidden_files(row)
    py = {n: c for n, c in files.items() if n.endswith(".py")}
    names = set(files)
    changed = _fix_changed_files(row)
    s1, s2, s3, s4 = [], [], [], []
    defined = set()
    trees = {}
    for n, code in py.items():
        try:
            trees[n] = ast.parse(code)
        except SyntaxError:
            continue
        defined |= _fixture_names(trees[n])
    for n, code in py.items():
        for i, line in enumerate(code.splitlines(), 1):
            if "__file__" in line:
                for lit in _LITERAL.findall(line):
                    base = lit.split("/")[-1]
                    if base not in {Path(x).name for x in names} and not base.endswith(".py"):
                        s1.append({"file": n, "line": i, "resource": lit, "text": line.strip()[:160]})
            for m in _DOTTED.findall(line):
                if line.lstrip().startswith(("import ", "from ")):
                    continue
                s2.append({"file": n, "line": i, "literal": m, "text": line.strip()[:160]})
        tree = trees.get(n)
        if tree is None:
            continue
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mod = node.module
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if ".tests" in a.name or a.name.startswith(("tests.", "test.")):
                        mod = a.name
            if mod and (".tests" in mod or mod.startswith(("tests.", "test.")) or mod in ("tests", "test")):
                cand = mod.replace(".", "/")
                hits = sorted(p for p in changed if p.endswith(".py") and (p[:-3] == cand or p[:-3].endswith("/" + cand) or p == cand + "/__init__.py"))
                s3.append({"file": n, "line": node.lineno, "module": mod, "modified_by_fix": hits})
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                if node.args.args and node.args.args[0].arg in ("self", "cls"):
                    continue  # unittest / 类方法：参数不是 fixture
                if _uses_positional_injection(node):
                    continue
                params = {a.arg for a in node.args.args} - PYTEST_BUILTIN_FIXTURES - defined - _parametrize_names(node)
                if params:
                    s4.append({"file": n, "line": node.lineno, "test": node.name, "undefined": sorted(params)})
    return {"hidden_files": sorted(files), "S1_file_relative_resources_missing": s1, "S2_self_reference_strings": s2,
            "S3_repo_test_imports": s3, "S4_undefined_fixture_params": s4}


def gold_log_fixture_errors(log_text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in re.finditer(r"fixture '([^']+)' not found", log_text):
        out[m.group(1)] = out.get(m.group(1), 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--gold-ledger", required=True, help="R-f gold 账本（log.path 已改写为本地路径的 _local 版本）")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)
    root = Path(args.repo_root).resolve()
    raw = root / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
    rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines() if line.strip()]
    logs = {}
    for line in Path(args.gold_ledger).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            p = Path((r.get("log") or {}).get("path") or "")
            if p.is_file():
                logs[r["instance_id"]] = p.read_text(encoding="utf-8", errors="replace")
    report = {}
    for row in rows:
        iid = f"{row['repo_name']}__{row['commit_hash']}"
        res = scan_task(row)
        res["S5_gold_log_fixture_not_found"] = gold_log_fixture_errors(logs.get(iid, "")) if iid in logs else None
        res["flagged"] = sorted(k for k in ("S1_file_relative_resources_missing", "S2_self_reference_strings", "S4_undefined_fixture_params",
                                            "S5_gold_log_fixture_not_found") if res.get(k)) + \
            (["S3_imports_module_modified_by_fix"] if any(x["modified_by_fix"] for x in res["S3_repo_test_imports"]) else [])
        report[iid] = res
    Path(args.out_json).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lines = ["| 题 | 标记 | 细节 |", "| --- | --- | --- |"]
    for iid, res in sorted(report.items()):
        if not res["flagged"]:
            continue
        det = []
        for x in res["S1_file_relative_resources_missing"]:
            det.append(f"S1 {x['file']}:{x['line']} 缺 `{x['resource']}`")
        for x in res["S2_self_reference_strings"]:
            det.append(f"S2 {x['file']}:{x['line']} `{x['literal']}`")
        for x in res["S3_repo_test_imports"]:
            if x["modified_by_fix"]:
                det.append(f"S3 {x['file']}:{x['line']} 导入 `{x['module']}`（修复提交改过 {', '.join(x['modified_by_fix'])}）")
        for x in res["S4_undefined_fixture_params"]:
            det.append(f"S4 {x['file']}:{x['line']} {x['test']} 用到未定义 {x['undefined']}")
        if res["S5_gold_log_fixture_not_found"]:
            det.append("S5 " + ", ".join(f"`{k}`×{v}" for k, v in sorted(res["S5_gold_log_fixture_not_found"].items())))
        lines.append(f"| {iid.split('__')[0]} `{iid.split('__')[1][:8]}` | {', '.join(res['flagged'])} | {'；'.join(det)} |")
    flagged = sum(1 for r in report.values() if r["flagged"])
    lines.append(f"\n被标记的题：{flagged} / {len(report)}（只是候选，逐条人工归因）")
    Path(args.out_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
