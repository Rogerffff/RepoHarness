#!/usr/bin/env python3
"""本轮离线独立证据审：只执行已 pin 的来源 parser/gold 提取函数，不调用作者对账器。"""
from __future__ import annotations

import ast
from collections import Counter
import fnmatch
import hashlib
import json
from pathlib import Path
import re

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2").is_dir())
OUT = Path(__file__).resolve().parent
DATA = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e"
DOC = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924"
RUN = ROOT / "runs/r2e_t0_revisions_20260924"
M3 = ROOT / "runs/env_overnight_20260916/M3"
OLD = ROOT / "runs/env_probe_20260909_codex_backup/ledger"
ISSUES, HASHES = [], {}


def rel(p):
    return str(p.relative_to(ROOT))


def digest(b):
    return "sha256:" + hashlib.sha256(b).hexdigest()


def readtext(p):
    b = p.read_bytes()
    HASHES[rel(p)] = digest(b)
    return b.decode()


def unique(pairs):
    r = {}
    for k, v in pairs:
        assert k not in r, k
        r[k] = v
    return r


def decode(s):
    return json.loads(s, object_pairs_hook=unique)


def read(p):
    return decode(readtext(p))


def rows(p):
    return [decode(s) for s in readtext(p).splitlines() if s.strip()]


def check(ok, where, detail):
    if not ok:
        ISSUES.append({"where": str(where), "detail": detail})


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def changed(a, b):
    return {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


pins = read(DATA / "t1_input_pins_r2e_v2.json")["pins"]
for name, item in pins.items():
    check(digest((ROOT / item["path"]).read_bytes()) == "sha256:" + item["sha256"], name, "pin hash")
vpath = ROOT / pins["rule_source"]["path"]
vendor = readtext(vpath)
assert digest(vendor.encode()) == "sha256:b928139eb0e9b4da9ca5d0ad927e17cf32727a6d18bc444ed57d63ca1a273bed"
names = {"parse_log_pytest", "_decolor", "extract_gold_patch"}
defs = [n for n in ast.parse(vendor).body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in defs} == names
scope = {"json": json, "re": re}
exec(compile(ast.Module(body=defs, type_ignores=[]), str(vpath), "exec"), scope)


def normalize(m):
    d = scope["_decolor"](m)
    return {k.split(" - ")[0]: d[k] for k in sorted(d)}


def parse(t):
    return normalize(scope["parse_log_pytest"](t))


def stats(e, o):
    return {"expected_count": len(e), "observed_count": len(o), "match_count": sum(o.get(k) == v for k, v in e.items()), "total_count": len(set(e) | set(o)), "missing": sorted(set(e) - set(o)), "unexpected": sorted(set(o) - set(e)), "mismatched": sorted(k for k in set(e) & set(o) if e[k] != o[k]), "keys_equal": set(e) == set(o)}


raw = {f"{r['repo_name']}__{r['commit_hash']}": r for r in rows(ROOT / pins["raw_archive"]["path"])}
image_facts = {f"{r['repo'].lower()}__{r['commit_hash']}":r for r in read(ROOT / pins["image_facts"]["path"])["tasks"]}
history = DATA / "ingest_history/source_v0_20260923"
current = DATA / "ingest"
bundles, history_bundles, material_diffs = {}, {}, {}
for prefix in (current, history):
    mf = read(prefix / "ingest_manifest_v0.json")
    dest = bundles if prefix == current else history_bundles
    for name, item in mf["files"].items():
        rs = rows(prefix / name)
        check(HASHES[rel(prefix / name)] == "sha256:" + item["sha256"], prefix / name, "manifest hash")
        check(len(rs) == item["count"] == len({r["instance_id"] for r in rs}) == 48, prefix / name, "48 unique rows")
        dest[name] = {r["instance_id"]: r for r in rs}
for name, rs in bundles.items():
    material_diffs[name] = {iid: changed(history_bundles[name][iid], row) for iid, row in rs.items() if row != history_bundles[name][iid]}
grade = bundles["grading_bundles_r2e_v0.jsonl"]
env = bundles["environment_packages_v0.jsonl"]
revisions = read(ROOT / pins["material_revisions"]["path"])["revisions"]
revision_results = []
for rev in revisions:
    iid = rev["instance_id"]
    if rev["kind"] == "expected_text_replace":
        before = raw[iid]["expected_output_json"]
        after = grade[iid]["expected_output_json"]
    else:
        er = decode(raw[iid]["execution_result_content"])
        before = dict(zip(er["test_file_names"], er["test_file_codes"]))[rev["target"]]
        after = readtext(ROOT / rev["revised_file"])
    check(digest(before.encode()) == rev["sha256_before"] and digest(after.encode()) == rev["sha256_after"], iid, "revision before/after hash")
    check(before.count(rev["old"]) == 1 and before.replace(rev["old"], rev["new"]) == after, iid, "single approved replacement")
    revision_results.append({"revision_id": rev["revision_id"], "before_sha256": digest(before.encode()), "after_sha256": digest(after.encode()), "single_replacement": before.count(rev["old"]) == 1 and before.replace(rev["old"], rev["new"]) == after})
rev_by_iid = {r["instance_id"]: r for r in revisions}
for iid, g in grade.items():
    prev = history_bundles["grading_bundles_r2e_v0.jsonl"][iid]
    er = decode(raw[iid]["execution_result_content"])
    files = dict(zip(er["test_file_names"], er["test_file_codes"]))
    check(prev["expected_output_json"] == raw[iid]["expected_output_json"], iid, "history expected differs from source")
    file_hashes = {f["path"].removeprefix("/r2e_tests/"): "sha256:" + f["sha256"] for f in image_facts[iid]["r2e_tests"]["files"]}
    check(all(file_hashes.get(p) == digest(t.encode()) for p,t in files.items()), iid, "raw file content/image file hash disagreement")
    if iid in rev_by_iid and rev_by_iid[iid]["kind"] == "hidden_test_text_replace":
        rv = rev_by_iid[iid]
        files[rv["target"]] = files[rv["target"]].replace(rv["old"], rv["new"])
    file_hashes.update({p:digest(t.encode()) for p,t in files.items()})
    fs = [{"path": p, "sha256": d} for p, d in sorted(file_hashes.items())]
    check(fs == g["hidden_test_files"], iid, "hidden files differ from source plus approved change")
    tree = digest("".join(f"{f['sha256'][7:]}  ./{f['path']}\n" for f in fs).encode())
    check(tree == g["hidden_tests_tree_sha256"], iid, "hidden tree independent digest")
    check(g["material_revisions"] == ([rev_by_iid[iid]["revision_id"]] if iid in rev_by_iid else []), iid, "revision marker")
    allowed = {"material_revisions"}
    if iid in rev_by_iid:
        allowed |= {"expected_output_json", "expected_output_json_sha256"} if rev_by_iid[iid]["kind"] == "expected_text_replace" else {"hidden_test_files", "hidden_tests_tree_sha256"}
    check(set(changed(prev, g)) <= allowed, iid, "unapproved semantic field changed")
check(not material_diffs["public_bundles_v0.jsonl"] and not material_diffs["validation_bundles_v0.jsonl"], "public/gold", "public or validation material changed")
check(all(set(d) == {"grading_bundle_digest"} for d in material_diffs["environment_packages_v0.jsonl"].values()), "environment", "non-derived field changed")

host = {r["instance_id"]: r for r in rows(RUN / "replay/private_r2e/host_grading_views.jsonl")}
for iid, r in host.items():
    check(r["grading"] == grade[iid], iid, "run host grading view differs from current input")
overlays = {r["task_id"]: r for r in rows(RUN / "derived/overlays.jsonl")}
inspected = []
ledgers = [RUN / "replay" / f"ledger_{kind}.jsonl" for kind in ["t0_noop", "t0_gold", "env43_noop", "env43_gold"]]


def local(remote):
    return RUN / remote.removeprefix("/work/b_r2e/")


def references(iid, kind):
    repo, commit = iid.split("__")
    a = (M3 / "facts" / commit[:12] / "noop_x2").glob("out*.txt") if kind == "noop" else (M3 / "gold_ledger/logs_r2e" / repo / commit[:12] / "gold").glob("a*/test_output.txt")
    b = (OLD / "logs_r2e" / repo / commit[:12] / kind).glob("a*/test_output.txt")
    return sorted(list(a) + list(b))


for ledger in ledgers:
    original = rows(ledger)
    copied = rows(ledger.with_name(ledger.stem + "_local.jsonl"))
    check(len(original) == len(copied), ledger, "localized count")
    for n, (r, copy) in enumerate(zip(original, copied), 1):
        loc = f"{rel(ledger)}:{n}"
        iid, kind = r["instance_id"], r["candidate"]["kind"]
        check(set(changed(r, copy)) <= {"diagnostics_ref", "log", "candidate"}, loc, "localized copy non-path edit")
        check({k:v for k,v in r["candidate"].items() if k != "origin"} == {k:v for k,v in copy["candidate"].items() if k != "origin"}, loc, "localized candidate non-path edit")
        check({k:v for k,v in r["log"].items() if k != "path"} == {k:v for k,v in copy["log"].items() if k != "path"}, loc, "localized log edit")
        logpath = local(r["log"]["path"])
        text = readtext(logpath)
        side = read(local(r["diagnostics_ref"]))
        check(HASHES[rel(logpath)] == r["log"]["sha256"], loc, "log hash")
        for k in ["task_id", "scripts_digest", "image_identity", "observations", "runner_integrity_changed", "execution_failure_decision", "env_qualification", "resource_facts"]:
            check(side.get(k) == r.get(k), loc, "sidecar " + k)
        check(side["verdict"] == r["verdict_diagnostics"] and side["candidate"] == r["install"], loc, "sidecar verdict/candidate")
        start, end = ">>>>> Start Test Output", ">>>>> End Test Output"
        check(text.count(start) == text.count(end) == 1, loc, "segment count")
        obs = parse(text.split(start)[1].split(end)[0])
        exp = normalize(decode(grade[iid]["expected_output_json"]))
        s = stats(exp, obs)
        check(s == r["verdict_diagnostics"]["expected_match"], loc, "independent expected-map stats")
        reward = float(s["match_count"] == s["total_count"])
        check(r["report"]["reward"] == reward and r["report"]["expected_match"] == s["match_count"] and r["report"]["expected_total"] == s["total_count"], loc, "independent reward")
        check(r["stage_error"] is None and r["cleanup"]["removed"] and not r["log"]["partial"] and r["test"]["segment_completed"] and r["test"]["exec_exit_code"] == 0, loc, "execution/cleanup/partial")
        ov = overlays[r["task_id"]]
        check(ov["derived_image_id"] == r["image_id_actual"] == r["overlay"]["derived_image_id"], loc, "image binding")
        check(ov["base_image_manifest_digest"] == env[iid]["image_manifest_digest"] == r["image_digest_expected"], loc, "source image binding")
        check(all(r["overlay"][k] == ov[k] for k in r["overlay"]), loc, "recipe binding")
        for marker, val in [("RH2_SETUP_HIDDEN_TESTS_TREE",grade[iid]["hidden_tests_tree_sha256"]),("RH2_SETUP_ENTRY_SHA256",grade[iid]["run_tests_sh_sha256"])]:
            check(f"{marker}={val[7:]}" in text, loc, marker)
        check(r["observations"]["RH2_OBS_IMPORT_PATH"].startswith("/testbed/") and not r["runner_integrity_changed"], loc, "import/runner binding")
        if kind == "gold":
            gold = scope["extract_gold_patch"](raw[iid]["parsed_commit_content"])
            check(digest(gold.encode()) == r["candidate"]["patch_sha256"] == digest((RUN / "replay/gold_r2e" / (iid + ".gold.patch")).read_bytes()), loc, "source gold binding")
        refs = []
        for rp in references(iid, kind):
            rm = parse(readtext(rp))
            refs.append({"path": rel(rp), "map_diff": changed(rm, obs), "source_expected_stats": stats(normalize(decode(raw[iid]["expected_output_json"])), rm), "revised_expected_stats": stats(exp, rm)})
        inspected.append({"ledger": loc, "instance_id": iid, "kind": kind, "attempt": r["attempt"], "report_id":r["report"]["report_id"], "log":rel(logpath), "image_id": r["image_id_actual"], "overlay": r["overlay"], "budgets":r["budgets"], "scripts_digest":r["scripts_digest"], "candidate":r["candidate"], "stats":s,"reward":reward,"observed":obs,"references":refs})
check(len(inspected) == len({r["report_id"] for r in inspected}) == len({r["log"] for r in inspected}) == 12, "rows", "12 distinct executions")
repeat = []
for iid in {r["instance_id"] for r in inspected}:
    for kind in ("noop", "gold"):
        rs = [r for r in inspected if r["instance_id"] == iid and r["kind"] == kind]
        check(len(rs) == 2 and {r["attempt"] for r in rs} == {1,2}, iid + kind, "repeat counts")
        same = all(rs[0][f] == rs[1][f] for f in ["observed","stats","reward","overlay","budgets","scripts_digest","candidate"])
        check(same, iid + kind, "repeat map/identity")
        repeat.append({"instance_id":iid,"kind":kind,"same":same})
record_results = []
for p in sorted((DOC / "tasks").glob("*/screening_record.json")):
    r = read(p)
    record_results.append({"instance_id":r["instance_id"],"classification":r["classification"],"disposition":r["disposition"],"issue_checks":[k for k,v in r["checks"].items() if v["status"] == "issue"]})
count = Counter(r["disposition"]["state"] for r in record_results)
check(dict(count) == {"environment_qualified":33,"qualified_with_recipe":2,"qualified_with_revision":2,"grading_ok_open_items":8,"needs_decision":3}, "disposition", "count differs")
for r in record_results:
    check(bool(r["disposition"].get("open_items")) == (r["disposition"]["state"] in {"grading_ok_open_items","needs_decision"}), r["instance_id"], "open items/status mismatch")
source_nonpassed = {iid:Counter(v for v in decode(r["expected_output_json"]).values() if v != "PASSED") for iid,r in raw.items()}
revised_nonpassed = {iid:Counter(v for v in decode(r["expected_output_json"]).values() if v != "PASSED") for iid,r in grade.items()}

# numpy 的剩余 10 个失败用原始仓库测试源码核相关性；不把六个 base 用例通过解释为修复已实现。
nid = next(iid for iid in raw if iid.startswith("numpy__43e333e2"))
source_file = next(f for f in decode(raw[nid]["parsed_commit_content"])["file_diffs"] if f["plus_file"]["path"].endswith("tests/test_extras.py"))
source_text = source_file["old_file_content"]
classes = {n.name:n for n in ast.parse(source_text).body if isinstance(n,ast.ClassDef)}
failure_text = readtext(RUN / "agent_pubtest_43e3_env_failures.txt")
failed = re.findall(r"^FAILED numpy/ma/tests/test_extras.py::(\w+)::(\w+)",failure_text,re.M)
check(Counter(c for c,_ in failed) == {"TestCov":4,"TestCorrcoef":6}, "numpy public", "10 residual failures class boundary")
method_evidence = []
for cname,mname in failed:
    method = next(n for n in classes[cname].body if isinstance(n,ast.FunctionDef) and n.name == mname)
    first = ast.unparse(method.body[0])
    calls = sorted({ast.unparse(n.func) for n in ast.walk(method) if isinstance(n,ast.Call)})
    check("self.data" in first and not any(x in {"average","ma.average","np.ma.average"} for x in calls), "numpy " + cname + "." + mname, "failure not in average")
    method_evidence.append({"class":cname,"method":mname,"source_line":method.lineno,"first_statement":first,"calls":calls})
pubtext = readtext(RUN / "agent_pubtest_43e3_env.txt")
check("hypothesis 6.24.1" in pubtext and "pytest 8.3.4" in pubtext and "TESTAVERAGE_RC=0\n6 passed" in pubtext and "10 failed, 78 passed" in pubtext,"numpy public","public evidence summary")
npdir = RUN / "derived" / nid


def integrity_sections(p):
    return {m.group(1):m.group(2).strip().splitlines() for m in re.finditer(r"^## (\w+)\n(.*?)(?=^## |\Z)",readtext(p),re.M|re.S)}


base_i, derived_i = [integrity_sections(npdir / f"integrity_{name}.txt") for name in ("base","derived")]
check(base_i["A"] == derived_i["A"] and base_i["D"] == derived_i["D"],"numpy integrity","workspace or git state changed")
def file_hash_map(lines):
    return {line.split("  ./",1)[1]:line.split("  ./",1)[0] for line in lines}
venv_diff = changed(file_hash_map(base_i["B"]),file_hash_map(derived_i["B"]))
recipe = read(DOC / "recipes/env_pins_v1.json")["tasks"][nid]
check(len(venv_diff) == 129 and all(any(fnmatch.fnmatchcase(p, glob) for glob in recipe["venv_changed_globs"]) for p in venv_diff),"numpy integrity","129 whitelisted hypothesis paths")
wheel = RUN / "derived/_wheel_cache" / recipe["pins"][0]["wheel"]
check(digest(wheel.read_bytes()) == "sha256:" + recipe["pins"][0]["sha256"],"numpy wheel","wheel pin")
npfacts = read(npdir / "facts.json")
probe_container = read(RUN / "dev_probe_env43" / nid / "container.json")
probe_log = readtext(RUN / "dev_probe_env43" / nid / "agent_probe.log")
container_image = probe_container[0]["Image"] if isinstance(probe_container,list) else probe_container.get("Image")
check(container_image == npfacts["derived_image_id"],"numpy dev probe","probe image binding")
check("ID=uid=54321(agent)" in probe_log and "PUBLIC_COLLECT_RC=0" in probe_log and "PUBLIC_RUN_RC=0" in probe_log,"numpy dev probe","agent identity/entry collects")
dry = readtext(ROOT / "runs/r2e_env_repair_20260924/p2/dryrun_58ba/run.log")
dry_comparison = []
for kind in ("noop","gold"):
    segment = dry.split("== " + kind + "_B1\n",1)[1].split("== ",1)[0]
    # dry-run 保存的是筛过的状态行，未保留 pytest summary 标题，故按其明示的状态行读取。
    obs = {node.replace("::", "."): status for status, node in re.findall(r"^(PASSED|FAILED|ERROR) r2e_tests/\S+?::(\S+)", segment, re.M)}
    checks = [r["observed"] == obs for r in inspected if r["instance_id"].startswith("datalad__58ba") and r["kind"] == kind]
    check(all(checks) and len(checks) == 2,"datalad dry-run " + kind,"B1 differs")
    dry_comparison.append({"kind":kind,"map":obs,"equal_new_rows":sum(checks)})
dump("numpy_public.json",{"source_file":"numpy/ma/tests/test_extras.py (raw parsed_commit_content.old_file_content)","source_sha256":digest(source_text.encode()),"residual_failed_methods":method_evidence,"average_methods":[n.name for n in classes["TestAverage"].body if isinstance(n,ast.FunctionDef)],"hypothesis_changed_paths":venv_diff,"public_run_summary":pubtext,"agent_probe_image_id":probe_container[0]["Image"] if isinstance(probe_container,list) else probe_container.get("Image"),"derived_image_id":npfacts["derived_image_id"],"datalad_B1_comparison":dry_comparison})
dump("rows.json", inspected)
dump("material_diffs.json",material_diffs)
dump("revision_checks.json",revision_results)
dump("records.json",record_results)
dump("summary.json",{"issues":ISSUES,"row_count":len(inspected),"repeat_groups":repeat,"dispositions":count,"source_nonpassed":{"tasks":sum(bool(v) for v in source_nonpassed.values()),"keys":dict(sum(source_nonpassed.values(),Counter()))},"revised_nonpassed":{"tasks":sum(bool(v) for v in revised_nonpassed.values()),"keys":dict(sum(revised_nonpassed.values(),Counter()))}})
dump("file_hashes.json",HASHES)
print(json.dumps({"issues":ISSUES,"rows":len(inspected),"dispositions":count},ensure_ascii=False,indent=2))
