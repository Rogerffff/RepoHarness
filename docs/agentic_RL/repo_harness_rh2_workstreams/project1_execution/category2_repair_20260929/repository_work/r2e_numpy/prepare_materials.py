#!/usr/bin/env python3
"""生成本题独占目录里的草案；只做文本、摘要、AST 和补丁检查，不运行 NumPy。"""

from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / "AGENTS.md").is_file() and (p / "rh2").is_dir())
DOCS = Path("docs/agentic_RL/repo_harness_rh2_workstreams")
S2 = DOCS / "s2_r2e"
IID = "numpy__d805e9b66228e68a0eb14d901cd350159c49af18"
OLD = DOCS / "project1_execution/r2e_lifecycle_20260929/results" / IID
PUB = Path("runs/r2e_static_prep_20260924/v3/public") / IID
PRIV = Path("runs/r2e_static_prep_20260924/v3/private") / IID
CAPTURE = Path("runs/r2e_lifecycle_20260929/devcheck_rev/v8") / IID / "orig/captures/repro_issue_repr.out"
PIN = S2 / "t1_input_pins_r2e_v12.json"


def sha(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def save(rel: str, body: str | dict | list) -> None:
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not isinstance(body, str):
        body = json.dumps(body, ensure_ascii=False, indent=2) + "\n"
    dest.write_text(body, encoding="utf-8")


def row(rel: Path) -> dict:
    matches = [json.loads(line) for line in (ROOT / rel).read_text().splitlines()
               if json.loads(line).get("instance_id") == IID]
    assert len(matches) == 1, rel
    return matches[0]


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, (text.count(old), old[:100])
    return text.replace(old, new)


def test_tree(text: str) -> tuple[ast.Module, dict[str, ast.FunctionDef]]:
    tree = ast.parse(text, feature_version=(3, 7))
    tests = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for fn in node.body:
                if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_"):
                    tests[node.name + "." + fn.name] = fn
        elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            tests[node.name] = node
    return tree, tests


def patch(before: str, after: str) -> str:
    rel = "numpy/ma/core.py"
    return (f"diff --git a/{rel} b/{rel}\n" +
            "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                         fromfile="a/" + rel, tofile="b/" + rel)))


def main() -> None:
    pins = json.loads((ROOT / PIN).read_text())
    rev_pin = pins["pins"]["material_revisions"]
    revisions_bytes = (ROOT / rev_pin["path"]).read_bytes()
    assert sha(revisions_bytes) == "sha256:" + rev_pin["sha256"].removeprefix("sha256:"), "父修订单与 pins 不符"
    revisions = json.loads(revisions_bytes)
    old_rev, = [e for e in revisions["revisions"] if e["instance_id"] == IID]
    assert old_rev["revision_id"] == "r2e-mr-056"
    grading = row(S2 / "ingest/grading_bundles_r2e_v0.jsonl")
    public = row(S2 / "ingest/public_bundles_v0.jsonl")
    original_test = (ROOT / PRIV / "hidden_tests/test_1.py").read_text()
    parent_test = (ROOT / old_rev["revised_file"]).read_text()
    assert sha(original_test) == old_rev["sha256_before"]
    assert sha(parent_test) == old_rev["sha256_after"]
    assert next(f["sha256"] for f in grading["hidden_test_files"] if f["path"] == "test_1.py") == sha(parent_test)
    assert grading["material_revisions"] == ["r2e-mr-056"]
    expected = json.loads(grading["expected_output_json"])
    assert len(expected) == 229
    assert sha(grading["expected_output_json"]) == grading["expected_output_json_sha256"]
    save("private/expected_output.json", grading["expected_output_json"])

    anchor = "            assert_equal(s.replace('[', ' ').replace(']', ' ').split(),\n                         expected)\n"
    addition = """

            # 提高阈值后，仍需摘要的数组不能静默丢掉中间值。
            # 首尾显示内容仍由原有打印选项决定。
            a = np.ma.arange(3000)
            a[1:50] = np.ma.masked
            assert_equal(str(a), '[0 -- -- ..., 2997 2998 2999]')

            # 保留配置指定的首尾元素；省略中间值时须有省略号。
            # token 比较允许原有 linewidth 引起的折行。
            np.set_printoptions(threshold=1000, edgeitems=501)
            a = np.ma.arange(3000)
            a[1:50] = np.ma.masked
            s = str(a)
            expected = (['0'] + ['--'] * 49 +
                        [str(i) for i in range(50, 501)] + ['...'] +
                        [str(i) for i in range(2499, 3000)])
            assert_equal(s.replace('[', ' ').replace(']', ' ')
                         .replace(',', ' ').split(), expected)
"""
    delta = {"kind": "hidden_test_text_replace", "target": "test_1.py",
             "edits": [{"old": anchor, "new": anchor + addition}]}
    revised_test = replace_once(parent_test, anchor, anchor + addition)
    save("private/test_1.py", revised_test)
    save("private/trial_delta.json", {"revisions": [delta]})
    combined = copy.deepcopy(old_rev["edits"]) + delta["edits"]
    rebuilt = original_test
    for edit in combined:
        rebuilt = replace_once(rebuilt, edit["old"], edit["new"])
    assert rebuilt == revised_test
    before_tree, before_tests = test_tree(parent_test)
    after_tree, after_tests = test_tree(revised_test)
    assert set(before_tests) == set(after_tests) == set(expected)
    target = "TestMaskedArray.test_str_repr"
    assert all(ast.dump(before_tests[k]) == ast.dump(after_tests[k]) for k in expected if k != target)
    before_tests[target].body = []
    after_tests[target].body = []
    assert ast.dump(before_tree) == ast.dump(after_tree), "目标函数之外有改动"

    source = (ROOT / PUB / "worktree/numpy/ma/core.py").read_text()
    original_loop = """                    for axis in range(self.ndim):
                        if data.shape[axis] > self._print_width:
                            ind = self._print_width // 2
"""
    positive_loop = """                    print_width = self._print_width
                    if self.ndim == 1:
                        options = np.get_printoptions()
                        threshold = options['threshold']
                        if data.size > threshold:
                            threshold_width = int(threshold) + 2
                            edge_width = 2 * options['edgeitems'] + 2
                            if threshold_width > print_width:
                                print_width = threshold_width
                            if edge_width > print_width:
                                print_width = edge_width
                        else:
                            print_width = data.size
                    for axis in range(self.ndim):
                        if data.shape[axis] > print_width:
                            ind = print_width // 2
"""
    hybrid_loop = """                    print_width = self._print_width
                    if self.ndim == 1:
                        threshold = np.get_printoptions()['threshold']
                        print_width = 1500 if data.size > threshold else data.size
                    for axis in range(self.ndim):
                        if data.shape[axis] > print_width:
                            ind = print_width // 2
"""
    positive = replace_once(source, original_loop, positive_loop)
    hybrid = replace_once(source, original_loop, hybrid_loop)
    save("private/candidates/numpy_d805_KA5c.patch", patch(source, positive))
    save("private/candidates/numpy_d805_hybrid.patch", patch(source, hybrid))
    for name, code in [("K-A5c", positive), ("hybrid", hybrid)]:
        ast.parse(code, feature_version=(3, 7))

    original_statement = public["problem_statement"]
    assert sha(original_statement) == public["problem_statement_sha256"]
    actual_capture = (ROOT / CAPTURE).read_text()
    observed = actual_capture[actual_capture.index("masked_array(data = "):].rstrip()
    edits = [
        {"old": "When creating and printing a large 1D masked array, the string representation does not truncate the array as expected. This results in an excessively long output, which can impact performance and readability.",
         "new": "When printing a large 1D masked array, its data section retains more values than the ordinary array summary and omits middle values without an ellipsis. This makes it harder to see which values have been omitted."},
        {"old": "The `repr` of the masked array should truncate the data after a certain number of elements, using an ellipsis to indicate omitted values. For example:",
         "new": "The `repr` of the masked array should truncate the data after a certain number of elements, using an ellipsis to indicate omitted values. The choice between a summary and full output should follow NumPy's existing printing options; when those options request full output, values must not be silently dropped. For example:"},
        {"old": original_statement.split("**Actual Behavior:**\n", 1)[1].split("\n\n[/ISSUE]", 1)[0],
         "new": "For the example above, the initial checkout prints a data section containing 0, the 49 masked values, and 1950 through 1999. The intervening values are omitted, but the data section has no ellipsis:\n```\n" + observed + "\n```"},
    ]
    statement = original_statement
    for edit in edits:
        statement = replace_once(statement, edit["old"], edit["new"])
    revised_public = dict(public, problem_statement=statement, problem_statement_sha256=sha(statement))
    save("public/problem_statement.txt", statement)
    save("public/public_bundle.json", revised_public)
    header = f"Fix the following issue from the `numpy` repository (checked out at /testbed, commit {public['base_commit'][:12]}):\n\n"
    save("public/user_prompt.txt", header + statement)
    save("public/environment_brief.md", (ROOT / PUB / "environment_brief.md").read_text())

    old_draft = json.loads((ROOT / OLD / "revision_draft.json").read_text())
    candidate_paths = {
        "K-A5c": (OUT / "private/candidates/numpy_d805_KA5c.patch").relative_to(ROOT),
        "K-A5b": OLD / "cands/numpy_d805_KA5b.patch",
        "hybrid": (OUT / "private/candidates/numpy_d805_hybrid.patch").relative_to(ROOT),
        "gold": PRIV / "gold.patch", "noop": None,
        **{name: OLD / "cands" / filename for name, filename in
           [("K-DE", "numpy_d805_KDE.patch"), ("K-DC", "numpy_d805_KDC.patch"),
            ("K-DF", "numpy_d805_KDF.patch"), ("DG-e", "numpy_d805_DGe.patch"),
            ("DG-g", "numpy_d805_DGg.patch")]},
    }
    rows, patch_checks = [], []
    with tempfile.TemporaryDirectory(prefix="numpy-d805-static-") as tmp:
        work = Path(tmp)
        for name, rel in candidate_paths.items():
            if rel is not None:
                data = (ROOT / rel).read_bytes()
                if name in old_draft["candidate_patch_sha256"]:
                    assert sha(data) == old_draft["candidate_patch_sha256"][name]
                for f in ["numpy/ma/core.py", "numpy/core/arrayprint.py"]:
                    dst = work / f
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / PUB / "worktree" / f, dst)
                result = subprocess.run(["git", "apply", "--check", str(ROOT / rel)], cwd=work,
                                        capture_output=True, text=True, check=False)
                assert result.returncode == 0, (name, result.stdout, result.stderr)
                patch_checks.append({"candidate": name, "patch_sha256": sha(data), "git_apply_check": True})
            rows.append({"candidate": name, "patch": str(rel) if rel is not None else None,
                         "patch_sha256": sha((ROOT / rel).read_bytes()) if rel is not None else None,
                         "expected_score": 1 if name == "K-A5c" else 0,
                         "status": "not_run", "expected_fail_keys": [] if name == "K-A5c" else [target]})
    save("acceptance_matrix.json", {"instance_id": IID, "status": "planned_not_run", "rows": rows,
         "parent_material_checks": [{"candidate": "hybrid", "expected_score": 1, "status": "not_run"},
                                    {"candidate": "K-A5c", "expected_score": 1, "status": "not_run"}],
         "note": "hybrid 在父材料的得 1 目前仅静态推导；K-A5b 在新增 edgeitems 断言下预期 0。"})
    save("revision_draft.json", {"instance_id": IID, "template": "R-c + R-f", "status": "draft_not_published_not_cpu_validated",
         "revisions": [delta], "statement_edits": edits,
         "parent_hidden_test_sha256": sha(parent_test), "revised_hidden_test_sha256": sha(revised_test),
         "parent_statement_sha256": sha(original_statement), "revised_statement_sha256": sha(statement),
         "expected_after": expected, "expected_change": {"added": {}, "changed": {}, "removed": []},
         "positive_control": str(candidate_paths["K-A5c"]), "positive_control_status": "constructed_not_runtime_verified",
         "acceptance_matrix": "acceptance_matrix.json"})
    save("publication_handoff.json", {"instance_id": IID, "status": "central_publication_pending_cpu_and_review",
         "parent_pins": str(PIN), "parent_pins_sha256": sha((ROOT / PIN).read_bytes()),
         "parent_revisions": rev_pin, "supersedes_hidden_revision": "r2e-mr-056",
         "hidden_test_replacement": {"kind": "hidden_test_text_replace", "target": "test_1.py",
             "revision_id": None, "sha256_before": sha(original_test), "sha256_after": sha(revised_test),
             "edits": combined, "draft_file": str((OUT / "private/test_1.py").relative_to(ROOT)),
             "expected_change": None},
         "statement_revision": {"kind": "statement_text_replace", "target": "problem_statement",
             "revision_id": None, "sha256_before": sha(original_statement), "sha256_after": sha(statement),
             "edits": edits, "revised_file": None, "expected_change": None},
         "instructions": ["由维护者分配正式编号并发布新版本；不修改旧修订单、pins 或旧测试文件。",
             "新版本中替换本题已有 hidden_test_text_replace 条目，不能与 r2e-mr-056 并列同目标；合并 edits 从原始来源重放。",
             "将完整新测试复制到新的版本化 s2_r2e/revisions 路径，再写该新路径；当前独占目录不满足正式 revised_file 路径约束。",
             "旧 formalize_revisions.py 固定读历史 results 目录且拒绝同目标，不能直接拿它发布本包；现有 ingest 支持合并后的条目，无需先重构公共代码。",
             "发布前重核当前生效父版本和本题摘要，保留其他仓库所有条目。"]})
    save("static_checks.json", {"instance_id": IID, "as_of": "2026-10-03", "scope": "text_hash_ast_patch_only_no_numpy_execution",
         "parent_pins_sha256": sha((ROOT / PIN).read_bytes()), "parent_revisions_sha256": sha(revisions_bytes),
         "parent_hidden_test_sha256": sha(parent_test), "revised_hidden_test_sha256": sha(revised_test),
         "expected_sha256": grading["expected_output_json_sha256"], "expected_keys": len(expected),
         "test_keys_unchanged": True, "only_test_str_repr_ast_changed": True,
         "original_to_parent_to_draft_replay_matches": True, "python37_ast_parse": True,
         "candidate_patch_checks": patch_checks,
         "base_actual_capture": str(CAPTURE), "base_actual_capture_sha256": sha(actual_capture),
         "public_statement_sha256": sha(statement), "cpu_validation": "not_run", "model_probe": "not_run"})
    print(json.dumps({"instance_id": IID, "static_checks": "passed", "expected_keys": len(expected),
                      "patch_checks": len(patch_checks), "hidden_sha256": sha(revised_test),
                      "statement_sha256": sha(statement), "cpu_validation": "not_run"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
