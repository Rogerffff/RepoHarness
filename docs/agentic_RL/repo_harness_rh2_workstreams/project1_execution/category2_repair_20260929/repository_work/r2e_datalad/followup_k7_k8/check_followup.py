#!/usr/bin/env python3
"""只核065增量材料和隔离断言，不产生正式reward。"""

from __future__ import annotations

import ast
import hashlib
import json
import runpy
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OWNER = HERE.parent
LIB = runpy.run_path(str(OWNER / "check_materials.py"))
ROOT = LIB["ROOT"]
digest = LIB["digest"]
eq_ = LIB["eq_"]
tree_digest = LIB["tree_digest"]


def main():
    draft = json.loads((HERE / "revision_draft.json").read_text())
    revision = draft["proposed_revision"]
    parent = (OWNER / "private/hidden_tests/test_1.py").read_bytes()
    revised = (ROOT / revision["revised_file"]).read_bytes()
    eq_(digest(parent), revision["sha256_before"])
    eq_(digest(revised), revision["sha256_after"])
    replay = parent.decode()
    for edit in revision["edits"]:
        eq_(replay.count(edit["old"]), 1)
        replay = replay.replace(edit["old"], edit["new"], 1)
    eq_(replay.encode(), revised)
    old_ast = ast.parse(parent.decode(), feature_version=(3, 7))
    new_ast = ast.parse(revised.decode(), feature_version=(3, 7))
    names = lambda a: sorted(n.name for n in a.body
                             if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))
    eq_(names(old_ast), names(new_ast))
    for name in ("__init__.py", "conftest.py"):
        eq_((HERE / "private/hidden_tests" / name).read_bytes(),
            (OWNER / "private/hidden_tests" / name).read_bytes())
    for name in ("expected_output.json", "run_tests.sh"):
        eq_((HERE / "private" / name).read_bytes(), (OWNER / "private" / name).read_bytes())
    expected = json.loads((HERE / "private/expected_output.json").read_text())
    eq_(len(expected), 17)
    eq_(expected["test_get_local_file_url_linux"], "FAILED")
    eq_(tree_digest(OWNER / "private/hidden_tests"), draft["parent"]["hidden_tests_tree_sha256"])
    eq_(tree_digest(HERE / "private/hidden_tests"), draft["new_hidden_tests_tree_sha256"])
    public = (ROOT / draft["unchanged"]["public_bundle"]).parent
    base_source = (public / "worktree/datalad/support/network.py").read_text()
    helper = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "_check_url")
    samples = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "test_url_samples")
    opts_test = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "test_parse_url_opts")
    old_core_inputs = {"weired_url:/", "my_host:path/sp1", "data_server.example.org:/srv/ds"}
    checks = []
    helper_calls = []
    for node in samples.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "_check_url" and call.args:
                helper_calls.append(node)
                if isinstance(call.args[0], ast.Constant):
                    value = call.args[0].value
                    if value in old_core_inputs or value == "/some/dir:x":
                        checks.append((value, [node]))
    index = next(i for i, n in enumerate(samples.body)
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_u" for t in n.targets))
    checks.append(("fields_reconstruction", samples.body[index:index + 2]))
    api_test = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "test_is_url")
    for node in api_test.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "ok_" and call.args:
                inner = call.args[0]
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "is_url":
                    if inner.args and isinstance(inner.args[0], ast.Constant) and inner.args[0].value in old_core_inputs:
                        checks.append(("is_url:" + inner.args[0].value, [node]))
    checks.append(("parse_url_opts_all_four_assertions", [opts_test]))
    eq_(len(checks), 8)
    matrix = json.loads((OWNER / "acceptance_matrix.json").read_text())
    rows = []
    for candidate in matrix["candidates"]:
        with tempfile.TemporaryDirectory(prefix="datalad-k7k8-") as tmp:
            work = Path(tmp)
            src = work / "datalad/support/network.py"
            src.parent.mkdir(parents=True)
            src.write_text(base_source)
            if candidate["patch"]:
                patch = (ROOT / candidate["patch"]).read_bytes()
                eq_(digest(patch), candidate["patch_sha256"])
                subprocess.run(["git", "apply", "--check", "-"], input=patch, cwd=work,
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["git", "apply", "-"], input=patch, cwd=work,
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            source = src.read_text()
            namespace = LIB["isolated_url_namespace"](source, helper)
            opts = next(n for n in ast.parse(source).body
                        if isinstance(n, ast.FunctionDef) and n.name == "parse_url_opts")
            exec(compile(ast.Module(body=[opts], type_ignores=[]), "isolated_parse_url_opts", "exec"), namespace)
            failures = []
            for label, nodes in checks:
                try:
                    exec(compile(ast.Module(body=nodes, type_ignores=[]), "followup_assertions", "exec"), namespace)
                    if label == "parse_url_opts_all_four_assertions":
                        namespace["test_parse_url_opts"]()
                except (AssertionError, ValueError) as error:
                    failures.append({"check": label, "type": type(error).__name__, "error": str(error)})
            eq_(not failures, candidate["id"] == "C-A")
            if candidate["id"] == "gold":
                eq_([x["check"] for x in failures], ["/some/dir:x", "parse_url_opts_all_four_assertions"])
            if candidate["id"] == "C-A":
                exec(compile(ast.Module(body=helper_calls, type_ignores=[]), "all_helper_calls", "exec"), namespace)
            rows.append({"candidate": candidate["id"], "isolated_assertions": "reject" if failures else "pass",
                         "failures": failures, "formal_reward": None})
    evidence = {}
    for name in ("pcheck_public4_gold.json", "pcheck_public4_CA.json"):
        p = ROOT / "runs/r2e_lifecycle_20260929/inv/datalad_6b6f" / name
        evidence[name] = digest(p.read_bytes())
    report = {"status": "pass", "scope": "local_material_and_isolated_assertions_not_formal_cpu",
              "parent_test_sha256": digest(parent), "new_test_sha256": digest(revised),
              "new_tree_sha256": tree_digest(HERE / "private/hidden_tests"), "edit_count": 2,
              "test_function_names_unchanged": True, "expected_key_count": 17,
              "existing_065_constraints_retained": True, "positive_helper_calls": len(helper_calls),
              "historical_behavior_input_sha256": evidence, "candidate_checks": rows,
              "limitations": ["使用本机标准库，未导入完整DataLad/nose/pytest。",
                              "无容器/正式解析/17键评分/退出清理证据；formal_reward均为空。",
                              "新材料登记、构建和定向CPU验收待完成。"]}
    (HERE / "checks/local_checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "pass", "candidate_count": len(rows), "gold_new_failures": rows[1]["failures"],
                      "new_test_sha256": digest(revised), "formal_reward": None}, ensure_ascii=False))


if __name__ == "__main__":
    main()
