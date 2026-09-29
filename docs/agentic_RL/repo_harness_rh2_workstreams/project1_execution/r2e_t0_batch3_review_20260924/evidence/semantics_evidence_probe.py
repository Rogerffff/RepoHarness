"""批次三只读语义与证据复核；结果只写本目录，不运行目标测试或容器。"""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path.cwd()
S2 = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e"
RUN = ROOT / "runs/r2e_t0_batch3_20260924"
REPAIR = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924"
OUT = Path(__file__).resolve().with_name("semantics_evidence_result.json")
GIT = ROOT / "runs/r2e_static_prep_20260924/git/pandas.git"
IDS = {"19c5eea5", "294cbc8d", "32dd55cb", "7dd34ea7", "87787609", "f656217a", "9b5494e2"}
CHECKS = []


def load(p):
    return json.loads(p.read_text())


def lines(p):
    return [json.loads(s) for s in p.read_text().splitlines() if s]


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def check(name, result, detail=None):
    CHECKS.append({"name": name, "ok": bool(result), "detail": detail})


def git(*args):
    return subprocess.run(["git", "--git-dir", str(GIT), *args], check=True, capture_output=True).stdout


def log_map(text):
    # 独立读取摘要中的状态行，不调用实现者分析脚本或生产 parser。
    chunks = text.split("short test summary info")
    if len(chunks) < 2:
        return {}
    result = {}
    for line in chunks[1].splitlines():
        m = re.match(r"^(PASSED|FAILED|ERROR)\s+(.*)$", line)
        if m:
            parts = m[2].split("::")
            key = ".".join(parts[1:]) if len(parts) > 1 else line
            # PASSED 的参数 ID 本身可能含 " - "（294c）；只在失败行去尾部原因。
            result[key if m[1] == "PASSED" else key.split(" - ")[0]] = m[1]
    return result


def excluded_summary(text):
    return [line for line in text.split("short test summary info")[1].splitlines()
            if re.match(r"^(SKIPPED|XFAIL|XPASS)\b", line)]


def retained_lines(text, keys):
    # 用 JSON 解码参数 ID 里的反斜杠；比较对象仍是未改写的原行。
    return [line for line in text.splitlines() if line.strip().startswith('"')
            and next(iter(json.loads("{" + line.rstrip(",") + "}"))) in keys]


def node_source(text, node):
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return "".join(text.splitlines(keepends=True)[start - 1:node.end_lineno])


def is_fixture(node):
    return isinstance(node, ast.FunctionDef) and any(
        ast.unparse(d.func if isinstance(d, ast.Call) else d) == "pytest.fixture"
        for d in node.decorator_list
    )


def param_names(decorators):
    out = set()
    for d in decorators:
        if isinstance(d, ast.Call) and ast.unparse(d.func) == "pytest.mark.parametrize":
            first = ast.literal_eval(d.args[0])
            out.update(x.strip() for x in first.split(",")) if isinstance(first, str) else out.update(first)
    return out


def requested(text):
    tree = ast.parse(text)
    local = {n.name: n for n in ast.walk(tree) if is_fixture(n)}
    required = set()

    def walk(nodes, inherited=frozenset()):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                walk(node.body, inherited | param_names(node.decorator_list))
            elif isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                given = inherited | param_names(node.decorator_list)
                required.update(a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                                if a.arg not in given | {"self", "cls"})
    walk(tree.body)
    todo = list(required)
    seen = set()
    out = set()
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in local:
            todo.extend(a.arg for a in local[name].args.args + local[name].args.kwonlyargs)
        elif name not in {"self", "cls", "request", "tmp_path", "tmpdir", "monkeypatch", "capsys", "capfd", "recwarn"}:
            out.add(name)
    return out


raw = {f"{r['repo_name']}__{r['commit_hash']}": r for r in lines(S2 / "raw/r2e_gym_subset_48_e8b9fcbc.jsonl")}
bundles = {r["instance_id"]: r for r in lines(S2 / "ingest/grading_bundles_r2e_v0.jsonl")}
chosen = {iid: b for iid, b in bundles.items() if iid.split("__")[1][:8] in IDS}
report = {"scope": "7 题材料语义、28 行正式证据、48 题状态与非 PASSED 计数；不运行 Docker、远端或 pytest", "tasks": {}}

for iid, bundle in chosen.items():
    source = raw[iid]
    execdata = json.loads(source["execution_result_content"])
    tests = dict(zip(execdata["test_file_names"], execdata["test_file_codes"]))
    bundled_tests = {f["path"]: f["sha256"] for f in bundle["hidden_test_files"]}
    check(f"{iid}: 原隐藏测试字节及断言未改", all(bundled_tests[n] == sha(t.encode()) for n, t in tests.items()))
    entry = report["tasks"][iid] = {"base_commit": bundle["base_commit"], "test_files_unchanged": sorted(tests)}
    if not iid.startswith("pandas__"):
        continue
    conftest_path = S2 / "revisions/files" / iid / "r2e_tests/conftest.py"
    text = conftest_path.read_text()
    picked = {n.name: n for n in ast.parse(text).body if is_fixture(n)}
    check(f"{iid}: conftest 与评分面摘要一致", sha(conftest_path.read_bytes()) == bundled_tests["conftest.py"])
    check(f"{iid}: 无新增 autouse/hook", not any(n.name.startswith("pytest_") for n in ast.parse(text).body if isinstance(n, ast.FunctionDef))
          and not any(kw.arg == "autouse" and ast.literal_eval(kw.value) for n in picked.values() for d in n.decorator_list if isinstance(d, ast.Call) for kw in d.keywords))
    diffs = json.loads(source["parsed_commit_content"])["file_diffs"]
    required_union = set()
    entry["fixture_sources"] = []
    ancestor_sources = {}
    for name, code in tests.items():
        origins = [d["header"]["file"]["path"] for d in diffs if d.get("new_file_content") == code]
        check(f"{iid}/{name}: 原文件映射唯一", len(origins) == 1, origins)
        origin = Path(origins[0])
        chain = []
        for ancestor in reversed(origin.parent.parents):
            candidate = (ancestor / "conftest.py").as_posix()
            try:
                data = git("show", bundle["base_commit"] + ":" + candidate)
            except subprocess.CalledProcessError:
                continue
            chain.append((candidate, data.decode()))
        candidate = (origin.parent / "conftest.py").as_posix()
        try:
            chain.append((candidate, git("show", bundle["base_commit"] + ":" + candidate).decode()))
        except subprocess.CalledProcessError:
            pass
        resolved = {}
        for path, src in chain:
            ancestor_sources[path] = src
            resolved.update({n.name: (path, src, n) for n in ast.parse(src).body if is_fixture(n)})
        needs = requested(code)
        required_union.update(needs)
        for fixture in sorted(needs):
            check(f"{iid}/{name}: fixture {fixture} 在原作用域且已提取", fixture in resolved and fixture in picked)
            if fixture not in resolved or fixture not in picked:
                continue
            path, src, original = resolved[fixture]
            equal = node_source(text, picked[fixture]) == node_source(src, original)
            check(f"{iid}/{name}/{fixture}: 最近原层级函数含参数逐字相同", equal)
            args = [a.arg for a in original.args.args + original.args.kwonlyargs]
            check(f"{iid}/{name}/{fixture}: fixture 参数依赖闭合", all(n == "request" or n in picked for n in args), args)
            blob = hashlib.sha1(b"blob " + str(len(src.encode())).encode() + b"\0" + src.encode()).hexdigest()
            entry["fixture_sources"].append({"hidden_file": name, "original_path": origins[0], "fixture": fixture,
                "conftest_path": path, "git_blob": blob, "source_line": original.lineno,
                "copied_line": picked[fixture].lineno, "decorators": [ast.unparse(d) for d in original.decorator_list], "exact": equal})
    check(f"{iid}: 无多提或漏提 fixture", required_union == set(picked), {"requested": sorted(required_union), "copied": sorted(picked)})
    # 所有导入也要求是相同 base 链里的原语句，没有注入额外全局定义。
    for n in ast.parse(text).body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            check(f"{iid}: 导入原样 {ast.unparse(n)}", any(node_source(text, n) in src for src in ancestor_sources.values()))
        else:
            check(f"{iid}: 顶层非导入仅显式 fixture", is_fixture(n))
    for path, src in ancestor_sources.items():
        archived = RUN / "conftest_sources" / iid / path
        if archived.exists():
            check(f"{iid}/{path}: 存档 source 等于 git base blob", archived.read_text() == src)

for iid, bundle in chosen.items():
    short = iid.split("__")[1][:8]
    fixdir = "dryrun_b3r2" if short in {"32dd55cb", "7dd34ea7"} else "dryrun_b3o" if short == "9b5494e2" else "dryrun_b3"
    prefix = iid.split("__")[0] + "_" + short
    observed = {}
    omitted = {}
    for mode in ("noop", "gold"):
        for suffix in ("orig", "fix_a", "fix_b"):
            p = RUN / fixdir / f"{prefix}_{mode}_{suffix}.test.log"
            observed[(mode, suffix)] = log_map(p.read_text())
            omitted[(mode, suffix)] = excluded_summary(p.read_text())
            if suffix.startswith("fix"):
                setup = p.with_name(p.name.replace(".test.log", ".setup.log")).read_text()
                check(f"{iid}/{mode}/{suffix}: dryrun setup 文件摘要绑定当前材料", "SETUP_RC=0" in setup and all(
                    f["sha256"].removeprefix("sha256:") + "  ./" + f["path"] in setup for f in bundle["hidden_test_files"]))
        check(f"{iid}/{mode}: 最终 dryrun 两次逐键顺序相同", list(observed[(mode, "fix_a")].items()) == list(observed[(mode, "fix_b")].items()))
        check(f"{iid}/{mode}: skip/xfail 未增加或改变", omitted[(mode, "orig")] == omitted[(mode, "fix_a")] == omitted[(mode, "fix_b")])
    before = json.loads(raw[iid]["expected_output_json"])
    after = json.loads(bundle["expected_output_json"])
    gold = observed[("gold", "fix_a")]
    noop = observed[("noop", "fix_a")]
    check(f"{iid}: 当前 expected 等于最终 dryrun gold", after == gold)
    removed = {k: v for k, v in before.items() if k not in after}
    added = {k: v for k, v in after.items() if k not in before}
    changed = {k: [before[k], v] for k, v in after.items() if k in before and before[k] != v}
    stable_keys = {k for k in before if k in after and before[k] == after[k]}
    before_stable = retained_lines(raw[iid]["expected_output_json"], stable_keys)
    after_stable = retained_lines(bundle["expected_output_json"], stable_keys)
    check(f"{iid}: 保留键行及相对顺序逐字不变", len(before_stable) == len(stable_keys) and before_stable == after_stable)
    old_noop = observed[("noop", "orig")]
    old_gold = observed[("gold", "orig")]
    old_targets = {k: [old_noop.get(k), old_gold.get(k)] for k in old_noop.keys() | old_gold.keys() if old_noop.get(k) != old_gold.get(k)}
    new_targets = {k: [noop.get(k), gold.get(k)] for k in noop.keys() | gold.keys() if noop.get(k) != gold.get(k)}
    check(f"{iid}: 原目标 F2P 集合与状态保留", old_targets == new_targets, new_targets)
    if iid.startswith("pandas__"):
        check(f"{iid}: 原样 gold 重建来源 expected 字节", json.dumps(old_gold, indent=4) == raw[iid]["expected_output_json"])
        check(f"{iid}: 只将原 ERROR 恢复/展开", all(v == "ERROR" for v in removed.values()) and all(v == ["ERROR", "PASSED"] for v in changed.values()) and set(added.values()) <= {"PASSED"})
        check(f"{iid}: 新增参数键仅属被删 ERROR 测试函数", {k.split("[")[0] for k in added} == {k.split("[")[0] for k in removed})
        check(f"{iid}: 恢复键在 noop 中均为 PASSED", all(noop[k] == "PASSED" for k in added.keys() | changed.keys()))
        check(f"{iid}: gold 全 PASSED", set(gold.values()) == {"PASSED"})
    else:
        check(f"{iid}: orange 只改批准的两键", not removed and not added and changed == {
            "TestLogisticRegressionLearner.test_LogisticRegression": ["FAILED", "PASSED"],
            "TestLogisticRegressionLearner.test_coefficients": ["FAILED", "PASSED"]})
        for mode in ("noop", "gold"):
            check(f"{iid}/{mode}: env_v2 原样材料共三次相同", observed[(mode, "orig")] == observed[(mode, "fix_a")] == observed[(mode, "fix_b")])
    report["tasks"][iid].update({"fixdir": fixdir, "expected_counts": {"source": len(before), "final": len(after), "removed": len(removed), "added": len(added), "changed": len(changed)}, "target_f2p": new_targets,
        "remaining_nonpassed": {k: v for k, v in after.items() if v != "PASSED"}})

overlays = {r["task_id"].split("::", 1)[1]: r for r in lines(RUN / "derived7/overlays.jsonl")}
formal = []
for mode in ("noop", "gold"):
    rows = lines(RUN / f"replay_b5/ledger_b5_{mode}.jsonl")
    check(f"正式 {mode}: 恰好 7题各2次", Counter(r["instance_id"] for r in rows) == Counter({iid: 2 for iid in chosen}))
    for r in rows:
        iid = r["instance_id"]
        bundle = chosen[iid]
        p = RUN / "replay_b5/eval_logs" / Path(r["log"]["path"]).name
        log = p.read_text()
        got = log_map(log)
        expected = json.loads(bundle["expected_output_json"])
        label = f"{iid}/{mode}/{r['attempt']}"
        fixdir = report["tasks"][iid]["fixdir"]
        prefix = iid.split("__")[0] + "_" + iid.split("__")[1][:8]
        dry = log_map((RUN / fixdir / f"{prefix}_{mode}_fix_a.test.log").read_text())
        match = sum(got.get(k) == expected.get(k) for k in got.keys() | expected.keys())
        total = len(got.keys() | expected.keys())
        facts = load(RUN / "derived7" / iid / "facts.json")
        overlay = overlays[iid]
        check(label + ": 日志 sha256", sha(p.read_bytes()) == r["log"]["sha256"])
        check(label + ": 正式与最终 dryrun 逐键一致", got == dry)
        check(label + ": 正式 skip/xfail 与最终 dryrun 相同", excluded_summary(log) == excluded_summary((RUN / fixdir / f"{prefix}_{mode}_fix_a.test.log").read_text()))
        check(label + ": 当前 expected 重建账本分数", r["report"]["expected_match"] == match and r["report"]["expected_total"] == total and r["report"]["reward"] == float(got == expected))
        check(label + ": noop=0/gold=1", r["report"]["reward"] == (1.0 if mode == "gold" else 0.0))
        check(label + ": 无缺/多键", got.keys() == expected.keys())
        check(label + ": 日志 setup 绑定评分面 hidden tree", "RH2_SETUP_HIDDEN_TESTS_TREE=" + bundle["hidden_tests_tree_sha256"].removeprefix("sha256:") in log)
        check(label + ": 日志入口绑定评分面", "RH2_SETUP_ENTRY_SHA256=" + bundle["run_tests_sh_sha256"].removeprefix("sha256:") in log)
        check(label + ": 账本 overlay 绑定 derived7", all(r["overlay"][k] == overlay[k] for k in ("derived_image_id", "derived_image_ref", "recipe_id", "recipe_sha256")) and r["image_id_actual"] == overlay["derived_image_id"] == facts["derived_image_id"])
        check(label + ": build facts 对应当前 bundle", facts["root_facts"]["tree"] == bundle["hidden_tests_tree_sha256"].removeprefix("sha256:") and facts["root_facts"]["head"] == bundle["base_commit"] and facts["ok"] and not facts["failures"])
        check(label + ": cleanup/segment 完整", r["cleanup"]["removed"] and r["test"]["segment_completed"] and not r["log"]["partial"] and r["stage_error"] is None)
        check(label + ": 未修改测试支撑", not r["candidate_test_like_paths"] and not r["candidate_touched_conftest_or_fixture"])
        formal.append({"instance_id": iid, "candidate": mode, "attempt": r["attempt"], "matched": match, "total": total,
            "image_id": r["image_id_actual"], "recipe_id": overlay["recipe_id"], "recipe_sha256": overlay["recipe_sha256"], "log": str(p.relative_to(ROOT)), "log_sha256": r["log"]["sha256"]})

report["formal_rows"] = formal
check("正式共 28 行", len(formal) == 28)
oldrevs = load(S2 / "revisions/material_revisions_v2.json")["revisions"]
newrevs = load(S2 / "revisions/material_revisions_v3.json")["revisions"]
check("v2 七条保留且 v3 仅追加13条", newrevs[:7] == oldrevs and len(newrevs) == 20 and len(oldrevs) == 7)
oldrevtext = (S2 / "revisions/material_revisions_v2.json").read_text()
newrevtext = (S2 / "revisions/material_revisions_v3.json").read_text()
check("v2 七条序列化片段逐字节保留", oldrevtext.split('"revisions": [', 1)[1].rsplit("\n ]", 1)[0] in newrevtext)
check("新增修订只涉指定7题", {r["instance_id"] for r in newrevs[7:]} == set(chosen))
for file in ("public_bundles_v0.jsonl", "validation_bundles_v0.jsonl"):
    check(file + ": v2 归档至当前逐字节不变", (S2 / "ingest_history/material_v2_20260924" / file).read_bytes() == (S2 / "ingest" / file).read_bytes())
for file in ("grading_bundles_r2e_v0.jsonl", "environment_packages_v0.jsonl"):
    old = lines(S2 / "ingest_history/material_v2_20260924" / file)
    new = lines(S2 / "ingest" / file)
    key = "instance_id" if file.startswith("grading") else "task_id"
    oldmap = {r[key]: r for r in old}
    newmap = {r[key]: r for r in new}
    changed = {k.split("::")[-1] for k in oldmap if oldmap[k] != newmap[k]}
    check(file + ": 仅7题改变", changed == set(chosen), sorted(changed))
pins = load(S2 / "t1_input_pins_r2e_v4.json")
for name, pin in pins["pins"].items():
    check("pins v4/" + name + ": 磁盘摘要匹配", sha((ROOT / pin["path"]).read_bytes()).removeprefix("sha256:") == pin["sha256"])
records = [load(p) for p in (REPAIR / "tasks").glob("*/screening_record.json")]
counts = Counter(r["disposition"]["state"] for r in records)
report["state_counts"] = dict(counts)
check("48 状态计数 32+2+10+4", counts == Counter(environment_qualified=32, qualified_with_recipe=2, qualified_with_revision=10, grading_ok_open_items=4))
nonpassed = {iid: {k: v for k, v in json.loads(b["expected_output_json"]).items() if v != "PASSED"} for iid, b in bundles.items()}
nonpassed = {iid: v for iid, v in nonpassed.items() if v}
report["nonpassed_current_expected"] = nonpassed
check("非 PASSED 当前为11题29键", len(nonpassed) == 11 and sum(map(len, nonpassed.values())) == 29, {"tasks": len(nonpassed), "keys": sum(map(len, nonpassed.values()))})
report["checks"] = CHECKS
report["summary"] = {"checks": len(CHECKS), "passed": sum(c["ok"] for c in CHECKS), "failed": sum(not c["ok"] for c in CHECKS)}
OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"summary": report["summary"], "failures": [c for c in CHECKS if not c["ok"]], "output": str(OUT.relative_to(ROOT))}, ensure_ascii=False, indent=2))
