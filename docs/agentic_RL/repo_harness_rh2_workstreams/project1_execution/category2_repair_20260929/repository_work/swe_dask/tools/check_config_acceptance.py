"""轻量检查 8801 草案的加载行为；不用镜像，不宣称为 Dask/正式评分验收。

直接执行冻结 config.py 中的定义和草案测试的目标函数，省略模块初始化
及完整 import dask 子进程。Python/PyYAML 和操作系统与原镜像不同，结果
只用于发现补丁或措辞检查的明显问题；正式非 root 验收仍须在远端完成。
"""
from __future__ import annotations

import ast
import json
import os
import platform
import stat
import sys
import tempfile
import traceback
import warnings
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

from prepare_materials import CLOUD, HERE, apply_to_file, read, rel, save_json, sha, source


def definitions(source_text: str, filename: str) -> dict:
    tree = ast.parse(source_text, filename=filename)
    # 只执行定义、导入和模块常量，不执行 refresh/_initialize 及其它启动语句。
    allowed = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef, ast.Assign, ast.AnnAssign)
    tree.body = [n for n in tree.body if isinstance(n, allowed)]
    env = {"__name__": "config_isolated", "__file__": filename}
    exec(compile(tree, filename, "exec"), env)
    return env


def test_functions(loader: dict, text: str) -> dict:
    tree = ast.parse(text)
    names = {"_displayed_error", "_collect_yaml_error", "no_read_permissions",
             "test_collect_yaml_malformed_file", "test_collect_yaml_no_top_level_dict",
             "test_collect_yaml_permission_errors"}
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    for n in tree.body:
        if n.name == "test_collect_yaml_no_top_level_dict":
            # 完整 Dask 导入要求真实依赖和 actor 环境；本地仅检查加载 API。
            stop = next(i for i, stmt in enumerate(n.body)
                        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "env" for t in stmt.targets))
            n.body = n.body[:stop]
    env = {"os": os, "sys": sys, "stat": stat, "traceback": traceback, "warnings": warnings,
           "contextmanager": contextmanager, "pytest": pytest, "yaml": yaml,
           "collect_yaml": loader["collect_yaml"], "merge": loader["merge"]}
    exec(compile(tree, "effective_test_config_isolated.py", "exec"), env)
    return env


def main() -> None:
    assert os.geteuid() != 0, "权限控制必须由非 root 执行；root 不能冒作通过"
    public, private, _, _ = source(8801)
    path = "dask/config.py"
    base = (public / "base" / path).read_bytes()
    out = HERE / "tasks/dask__dask-8801"
    patches = {"noop": None, "gold": private / "gold.patch",
               "reasonable_named_values": out / "reasonable_named_values.patch"}
    if (out / "wrong_missing_file_reason.patch").exists():
        patches["wrong_missing_file_reason"] = out / "wrong_missing_file_reason.patch"
    for p in sorted((CLOUD / "dask8801").glob("*.patch")):
        if b"diff --git a/dask/config.py b/dask/config.py" in p.read_bytes():
            patches[p.stem] = p
    tests = read(out / "effective_test.py")
    rows = []
    for name, p in patches.items():
        code = base if p is None else apply_to_file(base, path, p.read_bytes())
        loader = definitions(code.decode(), "config_isolated.py")
        funcs = test_functions(loader, tests)
        checks = {}
        for key, fn, args in [
            ("malformed", "test_collect_yaml_malformed_file", []),
            ("non_mapping_empty_null", "test_collect_yaml_no_top_level_dict", []),
            ("permission_directory", "test_collect_yaml_permission_errors", ["directory"]),
            ("permission_file", "test_collect_yaml_permission_errors", ["file"]),
        ]:
            with tempfile.TemporaryDirectory(prefix="rh2-dask8801-local-") as td:
                try:
                    funcs[fn](Path(td), *args)
                    checks[key] = {"status": "pass"}
                except (Exception, pytest.fail.Exception) as exc:
                    checks[key] = {"status": "fail", "exception": type(exc).__name__,
                                   "detail": str(exc).replace(td, "<scratch>")[:700]}
        rows.append({"candidate": name, "path": None if p is None else rel(p),
                     "sha256": None if p is None else sha(p.read_bytes()),
                     "isolated_checks_pass": all(c["status"] == "pass" for c in checks.values()), "checks": checks})
    report = {"scope": "isolated_config_api_only_not_full_dask_not_formal_grader",
              "runtime": {"python": platform.python_version(), "system": platform.system(),
                          "pyyaml": yaml.__version__, "pytest": pytest.__version__, "identity": "local_non_root"},
              "omitted": ["full import dask subprocess", "remaining P2P", "actor identity and materials transport", "formal score"],
              "effective_test_file_sha256": sha((out / "effective_test.py").read_bytes()), "rows": rows}
    save_json(out / "local_config_checks.json", report)
    print(json.dumps({"checked": len(rows), "passing": [r["candidate"] for r in rows if r["isolated_checks_pass"]],
                      "known_false_accepts": [r["candidate"] for r in rows if r["candidate"] == "wrong_missing_file_reason" and r["isolated_checks_pass"]],
                      "required_wrong_rejected": {k: not next(r for r in rows if r["candidate"] == k)["isolated_checks_pass"]
                                                  for k in ["rv_enum_types", "wr_null_raises", "wr_perm_fatal", "wr_wrong_reason"]}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
