#!/usr/bin/env python3
"""DataLad 6b6f 草案的轻量核对；不启动容器，不产生正式评分。"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse, urlunparse

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tree_digest(path):
    files = sorted(path.iterdir(), key=lambda p: ("./" + p.name).encode())
    lines = [f"{digest(p.read_bytes())[7:]}  ./{p.name}\n" for p in files]
    return digest("".join(lines).encode())


def eq_(actual, expected):
    if actual != expected:
        raise AssertionError(f"{actual!r} != {expected!r}")


def ok_(value):
    if not value:
        raise AssertionError(f"{value!r} is not true")


def nok_(value):
    if value:
        raise AssertionError(f"{value!r} is not false")


def isolated_url_namespace(source, helper):
    """只执行原文件中的 URL/相关函数和草案 helper，依赖用本机标准库。"""
    parsed = ast.parse(source)
    nodes = [n for n in parsed.body if
             isinstance(n, ast.ClassDef) and n.name == "URL" or
             isinstance(n, ast.FunctionDef) and n.name in ("_split_colon", "is_url") or
             isinstance(n, ast.For) and isinstance(n.iter, ast.Attribute) and
             ast.unparse(n.iter) == "URL._FIELDS"]
    nodes.append(helper)
    logger = logging.getLogger("datalad_6b6f_isolated_check")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    namespace = dict(ParseResult=ParseResult, parse_qsl=parse_qsl, urlencode=urlencode,
                     urlparse=urlparse, urlunparse=urlunparse, OrderedDict=OrderedDict,
                     re=re, lgr=logger, eq_=eq_, ok_=ok_, nok_=nok_)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "isolated_URL", "exec"), namespace)
    return namespace


def main():
    draft = json.loads((HERE / "revision_draft.json").read_text())
    revision = draft["proposed_revision"]
    parent = ROOT / draft["parent"]["snapshot"]
    original = (parent / "hidden_tests/test_1.py").read_bytes()
    revised = (ROOT / revision["revised_file"]).read_bytes()
    eq_(digest(original), revision["sha256_before"])
    eq_(digest(revised), revision["sha256_after"])
    replayed = original.decode()
    for edit in revision["edits"]:
        eq_(replayed.count(edit["old"]), 1)
        replayed = replayed.replace(edit["old"], edit["new"], 1)
    eq_(replayed.encode(), revised)
    old_ast = ast.parse(original.decode(), feature_version=(3, 7))
    new_ast = ast.parse(revised.decode(), feature_version=(3, 7))
    tests = lambda module: sorted(n.name for n in module.body
                                  if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))
    eq_(tests(old_ast), tests(new_ast))
    for name in ("__init__.py", "conftest.py"):
        eq_((HERE / "private/hidden_tests" / name).read_bytes(),
            (parent / "hidden_tests" / name).read_bytes())
    eq_(tree_digest(parent / "hidden_tests"), draft["parent"]["hidden_tests_tree_sha256"])
    for name, key in (("expected_output.json", "expected_output_json_sha256"),
                      ("run_tests.sh", "run_tests_sh_sha256")):
        data = (HERE / "private" / name).read_bytes()
        eq_(data, (parent / name).read_bytes())
        eq_(digest(data), draft["unchanged"][key])
    expected = json.loads((HERE / "private/expected_output.json").read_text())
    eq_(len(expected), 17)
    eq_(expected["test_get_local_file_url_linux"], "FAILED")
    public = (ROOT / draft["unchanged"]["public_bundle"]).parent
    for name, key in (("public_bundle.json", "public_bundle_sha256"),
                      ("user_prompt.txt", "user_prompt_sha256")):
        eq_(digest((public / name).read_bytes()), draft["unchanged"][key])

    matrix = json.loads((HERE / "acceptance_matrix.json").read_text())
    base_source = (public / "worktree/datalad/support/network.py").read_text()
    helper = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "_check_url")
    samples = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "test_url_samples")
    selected_inputs = {"weired_url:/", "my_host:path/sp1", "data_server.example.org:/srv/ds"}
    checks = []
    for node in samples.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "_check_url" and call.args:
                if isinstance(call.args[0], ast.Constant) and call.args[0].value in selected_inputs:
                    checks.append((call.args[0].value, [node]))
    index = next(i for i, n in enumerate(samples.body)
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_u" for t in n.targets))
    checks.append(("fields_reconstruction", samples.body[index:index + 2]))
    regression_nodes = [n for n in samples.body if isinstance(n, ast.Expr) and
                        isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and
                        n.value.func.id == "_check_url" and n.value.args and
                        isinstance(n.value.args[0], ast.Constant) and
                        n.value.args[0].value not in selected_inputs]
    api_test = next(n for n in new_ast.body if isinstance(n, ast.FunctionDef) and n.name == "test_is_url")
    for node in api_test.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Name) and call.func.id == "ok_" and call.args:
                inner = call.args[0]
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "is_url":
                    if inner.args and isinstance(inner.args[0], ast.Constant) and inner.args[0].value in selected_inputs:
                        checks.append(("is_url:" + inner.args[0].value, [node]))
    eq_(len(checks), 6)
    rows = []
    for candidate in matrix["candidates"]:
        with tempfile.TemporaryDirectory(prefix="datalad6b6f-") as tmp:
            work = Path(tmp)
            source_file = work / "datalad/support/network.py"
            source_file.parent.mkdir(parents=True)
            source_file.write_text(base_source)
            if candidate["patch"]:
                patch = (ROOT / candidate["patch"]).read_bytes()
                eq_(digest(patch), candidate["patch_sha256"])
                subprocess.run(["git", "apply", "--check", "-"], input=patch, cwd=work, check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["git", "apply", "-"], input=patch, cwd=work, check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            namespace = isolated_url_namespace(source_file.read_text(), helper)
            failures = []
            for label, nodes in checks:
                try:
                    exec(compile(ast.Module(body=nodes, type_ignores=[]), "draft_assertions", "exec"), namespace)
                except AssertionError as error:
                    failures.append({"check": label, "error": str(error)})
            eq_(not failures, candidate["expected_reward"] == 1)
            regression_status = "not_checked_for_negative_candidate"
            if candidate["expected_reward"] == 1:
                exec(compile(ast.Module(body=regression_nodes, type_ignores=[]),
                             "existing_helper_calls", "exec"), namespace)
                regression_status = "pass"
            rows.append({"candidate": candidate["id"], "modified_assertions": "reject" if failures else "pass",
                         "failures": failures, "existing_helper_calls": regression_status, "formal_reward": None})
    report = {
        "status": "pass", "scope": "local_material_checks_and_isolated_url_assertions",
        "python_version": sys.version.split()[0], "edit_count": len(revision["edits"]),
        "parent_tree_sha256": tree_digest(parent / "hidden_tests"),
        "draft_tree_sha256": tree_digest(HERE / "private/hidden_tests"),
        "expected_key_count": 17, "test_function_names_unchanged": True,
        "existing_helper_call_count": len(regression_nodes),
        "candidate_assertion_checks": rows,
        "limitations": ["本机标准库与原环境 Python 3.7.9 不同。", "未导入完整 DataLad、nose 或 pytest；只抽取原 URL 代码和修改处断言。",
                        "未运行容器、真实身份、冻结运输、解析器或 17 键正式评分；不是 CPU 验收。", "正式修订编号、发布路径及镜像仍待落实。"]}
    destination = HERE / "checks/local_checks.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "pass", "candidates": len(rows), "formal_reward": None,
                      "report": str(destination.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
