"""只读复核四题的本地原件；输出仅写入本审查目录，不启动容器或联网。

数值拟合没有在本机重跑。函数探针只执行原件中的小函数/方法，Orange 使用
记录参数的替身底座，所以其输出只证明参数路由，不证明真实拟合通过。
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import re
import runpy
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2").is_dir() and (p / "runs").is_dir())
MATERIAL = ROOT / "runs/r2e_static_prep_20260924/v2"
GRADER = ROOT / "runs/r2e_actor_20260925/grader"
CANDS = ROOT / "runs/r2e_actor_20260925/grader_cands"
TOKENS = ("32dd55cb", "5dbbe143", "9b5494e2", "22e98f8f")
IDS = {token: next((MATERIAL / "public").glob(f"*{token}*")).name for token in TOKENS}


def sha(raw):
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def source(token, rel):
    return (MATERIAL / "public" / IDS[token] / "worktree" / rel).read_text()


def patch_memory(original, patch):
    """在内存应用本批单文件 unified diff，并逐行验证旧文本。"""
    old = original.splitlines(keepends=True)
    out, cursor = [], 0
    lines = patch.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
        if not match:
            i += 1
            continue
        start = int(match.group(1)) - 1
        out.extend(old[cursor:start])
        cursor = start
        i += 1
        while i < len(lines) and not lines[i].startswith(("@@", "diff --git")):
            line = lines[i]
            if line.startswith((" ", "-")):
                assert old[cursor] == line[1:], (cursor, old[cursor], line)
                cursor += 1
            if line.startswith((" ", "+")):
                out.append(line[1:])
            i += 1
    out.extend(old[cursor:])
    return "".join(out)


def method(text, cls, name):
    cl = next(n for n in ast.parse(text).body if isinstance(n, ast.ClassDef) and n.name == cls)
    return next(n for n in cl.body if isinstance(n, ast.FunctionDef) and n.name == name)


parser = runpy.run_path(str(ROOT / "rh2/src/repoharness2/envpack/r2e_parsers.py"))
records = []
for path in sorted(GRADER.glob("ledger_*.jsonl")):
    row = json.loads(path.read_text())
    if not any(token in row["instance_id"] for token in TOKENS):
        continue
    log_path = GRADER / "eval_logs" / Path(row["log"]["path"]).name
    raw = log_path.read_bytes()
    assert sha(raw) == row["log"]["sha256"], path
    expected = parser["normalize_status_map"](json.loads((MATERIAL / "private" / row["instance_id"] / "expected_output.json").read_text()))
    observed = parser["normalize_status_map"](parser["parse_log_pytest"](raw.decode()))
    keys = expected.keys() | observed.keys()
    mismatched = sorted(k for k in keys if expected.get(k) != observed.get(k))
    match_count = sum(expected.get(k) == observed.get(k) for k in keys)
    diag = row["verdict_diagnostics"]["expected_match"]
    assert match_count == diag["match_count"] == row["report"]["expected_match"]
    assert mismatched == sorted(diag["mismatched"])
    assert not diag["missing"] and not diag["unexpected"]
    assert float(not mismatched) == row["report"]["reward"]
    cand = row["candidate"]
    if cand["kind"] == "gold":
        patch = MATERIAL / "private" / row["instance_id"] / "gold.patch"
    else:
        patch = CANDS / Path(cand["origin"]).name
        assert patch.read_bytes() == (GRADER / "cands" / patch.name).read_bytes()
    assert sha(patch.read_bytes()) == cand["patch_sha256"], (path, patch)
    assert not row["candidate_test_like_paths"] and not row["candidate_touched_conftest_or_fixture"]
    assert row["image_id_actual"] == row["overlay"]["derived_image_id"]
    assert not row["runner_integrity_changed"] and row["cleanup"]["removed"]
    records.append({
        "label": path.stem.removeprefix("ledger_"),
        "ledger": str(path.relative_to(ROOT)),
        "instance_id": row["instance_id"],
        "candidate_kind": cand["kind"],
        "candidate": str(patch.relative_to(ROOT)),
        "patch_sha256": cand["patch_sha256"],
        "log": str(log_path.relative_to(ROOT)),
        "log_sha256": sha(raw),
        "reward": row["report"]["reward"],
        "match": f"{match_count}/{len(keys)}",
        "mismatched": mismatched,
        "test_counts": {s: list(observed.values()).count(s) for s in sorted(set(observed.values()))},
        "included_paths": row["projection"]["included_paths"],
        "recipe": row["overlay"]["recipe_id"],
        "image": row["image_id_actual"],
    })
assert len(records) == 14

# coverage：在原函数上运行两个不同 slug，第三次重复第二个 slug。
coverage_results = {}
for name in ("CE1_dedupe_by_message", "CE3_dedupe_by_slug", "CE4_first_once_silences_all"):
    patched = patch_memory(source("5dbbe143", "coverage/control.py"), (CANDS / f"coveragepy_5dbb_{name}.patch").read_text())
    node = method(patched, "Coverage", "_warn")
    ns = {"os": os, "sys": sys}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "coverage-extracted", "exec"), ns)
    obj = SimpleNamespace(config=SimpleNamespace(disable_warnings=[]), _debug=SimpleNamespace(should=lambda _: False),
                          _warnings=[], _warned_once_msgs=set(), _warned_once_slugs=set(), _once_warning_shown=False)
    stream = io.StringIO()
    with contextlib.redirect_stderr(stream):
        for msg, slug in [("first", "x"), ("second", "y"), ("second", "y")]:
            ns["_warn"](obj, msg, slug=slug, once=True)
    coverage_results[name] = {"recorded": obj._warnings, "stderr": stream.getvalue()}
assert coverage_results["CE4_first_once_silences_all"]["recorded"] == ["first"]
assert coverage_results["CE3_dedupe_by_slug"]["recorded"] == ["first", "second"]

# Orange：执行候选原方法，仅由替身记录传给 sklearn 的参数，不调用数值模型。
class ParameterRecorder:
    def __init__(self, preprocessors=None):
        pass

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, vals):
        self._params = {k: v for k, v in vals.items() if k not in ("self", "preprocessors", "__class__")}

    def _initialize_wrapped(self):
        return self.__wraps__(**self.params)

    def fit(self, X, Y, W=None):
        return self._initialize_wrapped()


def orange_cls(patch_name):
    patched = patch_memory(source("9b5494e2", "Orange/classification/logistic_regression.py"), (CANDS / patch_name).read_text())
    original = next(n for n in ast.parse(patched).body if isinstance(n, ast.ClassDef) and n.name == "LogisticRegressionLearner")
    original.bases = [ast.Name(id="ParameterRecorder", ctx=ast.Load())]
    original.body = [n for n in original.body if isinstance(n, ast.FunctionDef)]
    ns = {"ParameterRecorder": ParameterRecorder}
    tree = ast.fix_missing_locations(ast.Module(body=[original], type_ignores=[]))
    exec(compile(tree, "orange-extracted", "exec"), ns)
    cls = ns["LogisticRegressionLearner"]
    cls.__wraps__ = staticmethod(lambda **kwargs: SimpleNamespace(**kwargs))
    return cls


orange_results = {}
for name in ("W1_gold_silently_drop_l1", "V4_resolve_in_fit", "V5_mapping_table", "P1_resolve_in_init"):
    cls = orange_cls(f"orange3_9b54_{name}.patch")
    learner = cls(penalty="l1")
    wrapped = learner.fit(None, None)
    row = {"fresh_l1_selected": {"solver": wrapped.solver, "penalty": wrapped.penalty}}
    learner = cls()
    first = learner.fit(None, None)
    learner.params["penalty"] = "l1"
    second = learner.fit(None, None)
    row["reuse_after_params_penalty_change"] = [{"solver": w.solver, "penalty": w.penalty} for w in (first, second)]
    try:
        wrapped = cls(penalty=None, solver="auto")._initialize_wrapped()
        row["hidden_none_constructor"] = {"solver": wrapped.solver, "penalty": wrapped.penalty}
    except Exception as exc:
        row["hidden_none_constructor"] = {"error": type(exc).__name__, "message": str(exc)}
    orange_results[name] = row
assert orange_results["W1_gold_silently_drop_l1"]["fresh_l1_selected"]["penalty"] == "l2"
assert orange_results["V5_mapping_table"]["hidden_none_constructor"]["error"] == "KeyError"

# 同仓公开树的快照包含关系；只读相关公开函数，不打开其它题私有答案。
lr_gold = patch_memory(source("9b5494e2", "Orange/classification/logistic_regression.py"), (MATERIAL / "private" / IDS["9b5494e2"] / "gold.patch").read_text())
lr_init_ast = ast.dump(method(lr_gold, "LogisticRegressionLearner", "_initialize_wrapped"))
hidden_lr = (MATERIAL / "private" / IDS["9b5494e2"] / "hidden_tests/test_1.py").read_text()
hidden_auto_ast = ast.dump(method(hidden_lr, "TestLogisticRegressionLearner", "test_auto_solver"))
cross_lr = []
for pub in sorted((MATERIAL / "public").glob("orange3__*")):
    lr_file = pub / "worktree/Orange/classification/logistic_regression.py"
    test_file = pub / "worktree/Orange/tests/test_logistic_regression.py"
    try:
        implementation_equal = ast.dump(method(lr_file.read_text(), "LogisticRegressionLearner", "_initialize_wrapped")) == lr_init_ast
        test_equal = ast.dump(method(test_file.read_text(), "TestLogisticRegressionLearner", "test_auto_solver")) == hidden_auto_ast
    except StopIteration:
        continue
    if implementation_equal and test_equal:
        cross_lr.append(pub.name)
assert len(cross_lr) == 5

# 题面泄漏：独立执行题面函数，并与应用 gold 后函数的可执行 body 对比。
prompt = (MATERIAL / "public" / IDS["22e98f8f"] / "user_prompt.txt").read_text()
block = prompt.split("```python\n", 1)[1].split("```", 1)[0]
fn = next(n for n in ast.parse(block).body if isinstance(n, ast.FunctionDef))
gold = patch_memory(source("22e98f8f", "Orange/widgets/data/owcreateclass.py"), (MATERIAL / "private" / IDS["22e98f8f"] / "gold.patch").read_text())
gold_fn = next(n for n in ast.parse(gold).body if isinstance(n, ast.FunctionDef) and n.name == fn.name)
gold_body = gold_fn.body[1:]  # 仓库已有 docstring 不在题面代码中。
assert ast.dump(ast.Module(body=fn.body, type_ignores=[])) == ast.dump(ast.Module(body=gold_body, type_ignores=[]))
cross_mapping = []
for pub in sorted((MATERIAL / "public").glob("orange3__*")):
    candidate_file = pub / "worktree/Orange/widgets/data/owcreateclass.py"
    if not candidate_file.exists():
        continue
    other = next((n for n in ast.parse(candidate_file.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == fn.name), None)
    if other is not None and ast.dump(other) == ast.dump(gold_fn):
        cross_mapping.append(pub.name)
assert len(cross_mapping) == 3
ns = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "statement-extracted", "exec"), ns)
count = 0
for n in range(6):
    for values in itertools.product(range(3), repeat=n):
        uniques, mapping = ns[fn.name](values)
        assert [uniques[i] for i in mapping] == list(values)
        assert len(uniques) == len(set(values))
        assert [values.index(e) for e in uniques] == sorted(values.index(e) for e in uniques)
        count += 1

result = {
    "scope": "local read-only audit; no Docker/network; no actual Orange/sklearn fitting",
    "ledger_rows": records,
    "coverage_extracted_function_probe": coverage_results,
    "orange_parameter_routing_probe": orange_results,
    "orange22_statement_gold_executable_body_equal": True,
    "orange22_statement_invariant_cases": count,
    "orange22_statement_sample": ns[fn.name]([2, 3, 1]),
    "public_cross_snapshot_lr_gold_and_test_matches": cross_lr,
    "public_cross_snapshot_mapping_gold_matches": cross_mapping,
}
(HERE / "audit_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"ledger_rows_verified": len(records), "coverage_CE4_two_slug_output": coverage_results["CE4_first_once_silences_all"]["recorded"], "orange_W1_l1_selected": orange_results["W1_gold_silently_drop_l1"]["fresh_l1_selected"], "orange22_cases": count}, ensure_ascii=False, indent=2))
