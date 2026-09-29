#!/usr/bin/env python3
"""CPU 独立证据复核；不导入 RH2 parser/scoring/reconcile，不改写历史证据。"""
from __future__ import annotations

import ast
import collections
import hashlib
import json
from pathlib import Path
import re


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2").is_dir())
OUT = Path(__file__).resolve().parent
R = ROOT / "runs/r2e_rf_20260923/remote"
DATA = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e"
M3 = ROOT / "runs/env_overnight_20260916/M3"
OLD = ROOT / "runs/env_probe_20260909_codex_backup/ledger"
START, END = ">>>>> Start Test Output", ">>>>> End Test Output"
issues = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_duplicate_keys(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError(f"duplicate JSON key: {k}")
        d[k] = v
    return d


def decode(text):
    return json.loads(text, object_pairs_hook=no_duplicate_keys)


def rows(path):
    return [decode(s) for s in path.read_text().splitlines() if s.strip()]


def rel(path):
    return str(path.relative_to(ROOT))


def check(ok, context, message):
    if not ok:
        issues.append({"context": context, "message": message})


pins = decode((DATA / "t1_input_pins_r2e_v1.json").read_text())["pins"]
pin_results = {name: sha(ROOT / p["path"]) == p["sha256"] for name, p in pins.items()}
assert all(pin_results.values()), pin_results
vendor = ROOT / pins["rule_source"]["path"]
names = {"parse_log_pytest", "_decolor", "calculate_reward", "extract_gold_patch"}
functions = [n for n in ast.parse(vendor.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in functions} == names
scope = {"json": json, "re": re}
exec(compile(ast.Module(body=functions, type_ignores=[]), rel(vendor), "exec"), scope)


def normalize(d):
    d = scope["_decolor"](d)
    return {k.split(" - ")[0]: d[k] for k in sorted(d)}


def parsed(text):
    return normalize(scope["parse_log_pytest"](text))


def match(expected, observed):
    return {
        "expected_count": len(expected),
        "observed_count": len(observed),
        "match_count": sum(k in observed and v == observed[k] for k, v in expected.items()),
        "total_count": len(set(expected) | set(observed)),
        "missing": sorted(set(expected) - set(observed)),
        "unexpected": sorted(set(observed) - set(expected)),
        "mismatched": sorted(k for k in set(expected) & set(observed) if expected[k] != observed[k]),
        "keys_equal": set(expected) == set(observed),
    }


raw_rows = rows(ROOT / pins["raw_archive"]["path"])
raw = {f"{r['repo_name']}__{r['commit_hash']}": r for r in raw_rows}
assert len(raw_rows) == len(raw) == 48
gradings = {r["instance_id"]: r for r in rows(DATA / "ingest/grading_bundles_r2e_v0.jsonl")}
assert set(gradings) == set(raw)
for iid, r in raw.items():
    assert gradings[iid]["expected_output_json"] == r["expected_output_json"], iid
expected = {iid: normalize(decode(r["expected_output_json"])) for iid, r in raw.items()}
overlays = {r["task_id"]: r for r in rows(R / "overlays_all.jsonl")}
reps_overlays = {r["task_id"]: r for r in rows(R / "overlays_reps.jsonl")}


def refs(iid, kind):
    repo, commit = iid.split("__")
    c = commit[:12]
    if kind == "noop":
        a = list((M3 / "facts" / c / "noop_x2").glob("out*.txt"))
    else:
        a = list((M3 / "gold_ledger/logs_r2e" / repo / c / "gold").glob("a*/test_output.txt"))
    return sorted(a + list((OLD / "logs_r2e" / repo / c / kind).glob("a*/test_output.txt")))


def local_path(remote):
    assert remote.startswith("/work/replay/"), remote
    return R / remote.removeprefix("/work/replay/")


reference_cache = {}


def inspect_row(row, stem, lineno):
    iid = row["instance_id"]
    kind = row["candidate"]["kind"]
    context = f"{rel(R / ('ledger_r2e_' + stem + '.jsonl'))}:{lineno}"
    log = local_path(row["log"]["path"])
    side_path = local_path(row["diagnostics_ref"])
    text = log.read_bytes().decode("utf-8", "replace")
    side = decode(side_path.read_text())
    check(row["log"]["sha256"] == "sha256:" + sha(log), context, "log sha256 mismatch")
    check(side["task_id"] == row["task_id"], context, "sidecar task differs")
    for key in ["scripts_digest", "image_identity", "observations", "runner_integrity_changed", "execution_failure_decision", "env_qualification", "resource_facts"]:
        check(side.get(key) == row.get(key), context, f"sidecar {key} differs")
    check(side.get("verdict") == row.get("verdict_diagnostics"), context, "sidecar verdict differs")
    check(side.get("candidate") == row.get("install"), context, "sidecar candidate/install differs")
    check(row["stage_error"] is None, context, "unexpected stage_error")
    check(row["cleanup"]["removed"] is True, context, "cleanup not removed")
    if row["test"]["segment_completed"]:
        check(row["observations"].get("RH2_OBS_RUNNER_DIGEST_PRE") == row["observations"].get("RH2_OBS_RUNNER_DIGEST"), context, "runner before/after differs")
    if START in text and END in text:
        segment = text.split(START, 1)[1].split(END, 1)[0]
    else:
        segment = ""
    observed = parsed(segment)
    stats = match(expected[iid], observed)
    semantic = stats["match_count"] == stats["total_count"]
    complete = row["test"]["segment_completed"]
    if complete:
        check(text.count(START) == text.count(END) == 1, context, "marker multiplicity differs")
        check(row["verdict_diagnostics"]["expected_match"] == stats, context, "independent expected-map stats differ")
        rc = re.findall(r"^RH2_TEST_RC=(\d+)$", text, re.M)
        check(len(rc) == 1 and int(rc[0]) == row["test"]["rc"], context, "raw test rc differs")
    entry = {
        "ledger": context, "kind": kind, "instance_id": iid, "log": rel(log),
        "log_sha256": sha(log), "sidecar": rel(side_path),
        "stats": stats, "raw_prime_reward": scope["calculate_reward"](segment, raw[iid]["expected_output_json"]),
        "report": row["report"], "test": row["test"],
        "observed_status_counts": dict(collections.Counter(observed.values())),
        "reference_comparisons": [], "report_matches_reparse": None,
    }
    if kind in {"noop", "gold"}:
        check(row["report"]["reward"] == float(semantic), context, "report reward differs from union-map reparse")
        check(row["report"]["expected_match"] == stats["match_count"], context, "report match count differs")
        check(row["report"]["expected_total"] == stats["total_count"], context, "report total differs")
        entry["report_matches_reparse"] = row["report"]["reward"] == float(semantic)
        overlay = (reps_overlays if stem.startswith("reps_") else overlays)[row["task_id"]]
        check(overlay["derived_image_id"] == row["image_id_actual"] == row["overlay"]["derived_image_id"], context, "image identity differs from overlay")
        check(overlay["facts"]["hidden_tests_tree_sha256"] == gradings[iid]["hidden_tests_tree_sha256"], context, "overlay hidden tests differ")
        for marker, value in [("RH2_SETUP_HIDDEN_TESTS_TREE", gradings[iid]["hidden_tests_tree_sha256"]), ("RH2_SETUP_ENTRY_SHA256", gradings[iid]["run_tests_sh_sha256"])]:
            check(f"{marker}={value.removeprefix('sha256:')}" in text, context, f"raw {marker} differs")
        if kind == "gold":
            patch = scope["extract_gold_patch"](raw[iid]["parsed_commit_content"])
            check("sha256:" + hashlib.sha256(patch.encode()).hexdigest() == row["candidate"]["patch_sha256"], context, "gold candidate differs from fixed source reconstruction")
        for ref in refs(iid, kind):
            reftext = ref.read_bytes().decode("utf-8", "replace")
            refobs = parsed(reftext)
            refstats = match(expected[iid], refobs)
            reward = scope["calculate_reward"](reftext, raw[iid]["expected_output_json"])
            reference_cache[rel(ref)] = {"sha256": sha(ref), "reward": reward, "instance_id": iid, "kind": kind}
            diff = {k: [observed.get(k), refobs.get(k)] for k in sorted(set(observed) | set(refobs)) if observed.get(k) != refobs.get(k)}
            entry["reference_comparisons"].append({"path": rel(ref), "sha256": sha(ref), "reward": reward, "maps_equal": not diff, "observed_diff": diff, "reference_stats": refstats})
        check(len(entry["reference_comparisons"]) in {2, 5}, context, "reference coverage not 2 or 5")
        entry["all_reference_maps_equal"] = all(c["maps_equal"] for c in entry["reference_comparisons"])
    return entry


stems = ["all_noop", "all_gold", "reps_noop", "reps_gold", "numpy_bigtmp_noop", "numpy_bigtmp_gold", "contrast3_a", "contrast3_b", "contrast3_c"]
results = {}
all_reports, all_logs = [], []
for stem in stems:
    ledger_rows = rows(R / f"ledger_r2e_{stem}.jsonl")
    results[stem] = [inspect_row(r, stem, i) for i, r in enumerate(ledger_rows, 1)]
    ids = [r["instance_id"] for r in ledger_rows]
    check(len(ids) == len(set(ids)), stem, "duplicate instance_id")
    if stem.startswith("all_"):
        check(set(ids) == set(raw), stem, "task omission or unexpected task")
    for r in ledger_rows:
        all_reports.append(r["report"]["report_id"])
        all_logs.append(r["log"]["path"])
check(len(all_reports) == len(set(all_reports)), "all inspected runs", "duplicate report id")
check(len(all_logs) == len(set(all_logs)), "all inspected runs", "duplicate log ref")

copy_checks = []
for copy in sorted(R.glob("ledger*_local*.jsonl")):
    original = R / (copy.stem.split("_local")[0] + ".jsonl")
    a, b = rows(original), rows(copy)
    for seq in [a, b]:
        for r in seq:
            r["log"].pop("path", None)
            r.pop("diagnostics_ref", None)
    copy_checks.append({"copy": rel(copy), "original": rel(original), "same_except_two_references": a == b})
    check(a == b, rel(copy), "localized copy changes non-reference data")

driver_summaries = {}
for stem in ["all_noop", "all_gold", "reps_noop", "reps_gold"]:
    text = (R / f"run_{stem}.log").read_text()
    runrows = [decode(s) for s in text.splitlines() if s.startswith("{")]
    emitted = [r for r in runrows if "task_id" in r]
    final = [r for r in runrows if "final_status" in r]
    ledger_rows = rows(R / f"ledger_r2e_{stem}.jsonl")
    check(len(final) == 1 and final[0]["rows"] == len(ledger_rows), stem, "driver final row count differs")
    check({r["task_id"] for r in emitted} == {r["task_id"] for r in ledger_rows} and len(emitted) == len(ledger_rows), stem, "driver emitted rows differ")
    for a, b in zip(emitted, ledger_rows):
        check(all(a[k] == b["report"][k] for k in ["outcome", "reward"]) and a["task_id"] == b["task_id"], stem, "driver row content differs")
    check(final[0]["final_status"]["exit_code"] == 0 and not final[0]["manager_close"]["containers_open"] and not final[0]["cleanup_failures"], stem, "driver nonclean final")
    driver_summaries[stem] = final[0]

m3_ledger_checks = []
for r in rows(M3 / "gold_ledger/r2e_gold_m3.jsonl"):
    p = M3 / "gold_ledger/logs_r2e" / r["repo"] / r["commit_hash"][:12] / r["gate"] / f"a{r['attempt']}" / "test_output.txt"
    cache = reference_cache[rel(p)]
    m3_ledger_checks.append({"path": rel(p), "sha256_matches": r["log_sha256"] == "sha256:" + cache["sha256"], "reward_matches": r["reward"] == cache["reward"]})
    check(m3_ledger_checks[-1]["sha256_matches"] and m3_ledger_checks[-1]["reward_matches"], rel(p), "M3 ledger hash or reward differs")

old_ledger_checks = []
for r in rows(OLD / "r2e_ledger_v3.jsonl"):
    p = OLD / "logs_r2e" / r["repo"] / r["commit_hash"][:12] / r["gate"] / f"a{r['attempt']}" / "test_output.txt"
    cache = reference_cache[rel(p)]
    old_ledger_checks.append({"path": rel(p), "sha256_matches": r["log_sha256"] == "sha256:" + cache["sha256"], "reward_matches": r["reward"] == cache["reward"]})
    check(old_ledger_checks[-1]["sha256_matches"] and old_ledger_checks[-1]["reward_matches"], rel(p), "09-09 v3 ledger hash or reward differs")

contrast_rows = {k: rows(R / f"ledger_r2e_contrast3_{k}.jsonl")[0] for k in "abc"}
a, b, c = [contrast_rows[k] for k in "abc"]
qualification = next(r for r in rows(R / "ledger_r2e_all_noop.jsonl") if r["report"]["report_id"] == a["env_qualification"].rsplit(":", 1)[1])
qualification_line = next(i for i, r in enumerate(rows(R / "ledger_r2e_all_noop.jsonl"), 1) if r["report"]["report_id"] == qualification["report"]["report_id"])
for key in ["task_id", "image_identity", "scripts_digest", "policy"]:
    check(a[key] == b[key] == c[key] == qualification[key], "contrast3", f"identity/qualification {key} differs")
check(a["candidate"]["patch_sha256"] == b["candidate"]["patch_sha256"] == "sha256:" + sha(R / "contrast/cov_syntax.patch"), "contrast3", "syntax patch differs")
check(c["candidate"]["patch_sha256"] == "sha256:" + sha(R / "contrast/cov_sleep.patch"), "contrast3", "sleep patch differs")
try:
    compile((R / "contrast/cov_broken.py").read_text(), "coverage/inorout.py", "exec")
    syntax_line = None
except SyntaxError as e:
    syntax_line = e.lineno
check(syntax_line == 466, "contrast3", "syntax source location differs")
compile((R / "contrast/cov_sleep.py").read_text(), "coverage/inorout.py", "exec")
for key, row in contrast_rows.items():
    logtext = local_path(row["log"]["path"]).read_text()
    if key in "ab":
        check('File "/testbed/coverage/inorout.py", line 466' in logtext and "SyntaxError: invalid syntax" in logtext, "contrast3_" + key, "raw syntax traceback missing")
        check(parsed(logtext.split(START, 1)[1].split(END, 1)[0]) == {"": "FAILED"}, "contrast3_" + key, "actual all-reference-missing producer differs")
    else:
        check(START in logtext and END not in logtext and "RH2_TEST_RC=" not in logtext, "contrast3_c", "partial log producer differs")
check(a["execution_failure_decision"]["compile_probe"]["error_paths"] == ["coverage/inorout.py:SyntaxError:line=466:invalid syntax"], "contrast3_a", "compile probe differs")
check(b["execution_failure_decision"]["compile_probe"] is None, "contrast3_b", "unexpected compile probe")
check(c["budgets"]["grading_deadline_seconds"] == 150 and not c["test"]["segment_completed"] and c["log"]["partial"] and c["test"]["rc"] is None, "contrast3_c", "timeout producer differs")
contrast_results = {
    "same_task_image_script_policy_with_qualification": True,
    "qualification_ledger": f"runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:{qualification_line}",
    "qualification_report": qualification["report"],
    "syntax_patch_sha256": sha(R / "contrast/cov_syntax.patch"),
    "sleep_patch_sha256": sha(R / "contrast/cov_sleep.patch"),
    "cpu_compile_syntax_line": syntax_line,
    "sleep_source_compiles_on_reviewer_python": True,
    "a_b_observed_map": {"": "FAILED"},
    "rows": {k: {f: v.get(f) for f in ["report", "env_qualification", "execution_failure_decision", "budgets", "resource_facts", "test", "cleanup", "observations"]} for k, v in contrast_rows.items()},
    "c_limitation": "timeout log has no post-test runner digest; do not claim before/after equality for this partial attempt",
}

numpy_iid = next(k for k in raw if "2f4a9650" in k)
numpy_data = raw[numpy_iid]
source = next(d["new_file_content"] for d in decode(numpy_data["parsed_commit_content"])["file_diffs"] if d["header"]["file"]["path"] == "numpy/lib/npyio.py")
savez_node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "_savez")
source_lines = source.splitlines()
numpy_excerpt = {
    "source": rel(ROOT / pins["raw_archive"]["path"]), "source_sha256": pins["raw_archive"]["sha256"],
    "instance_id": numpy_iid, "file": "numpy/lib/npyio.py", "source_version": "new_file_content (gold)",
    "savez_lines": [{"line": i, "text": source_lines[i-1]} for i in range(savez_node.lineno, savez_node.end_lineno + 1)],
    "array_bytes": (1 << 31) + 100000,
    "two_copies_payload_lower_bound_bytes": 2 * ((1 << 31) + 100000),
    "inference": "ZIP_STORED output grows while temporary .npy remains until zipf.write returns; 3 GiB is not a sufficient capacity. This is source inference, not a new threshold run.",
    "observed_profiles": [],
}
for stem in ["all_noop", "all_gold", "numpy_bigtmp_noop", "numpy_bigtmp_gold"]:
    r = next(r for r in rows(R / f"ledger_r2e_{stem}.jsonl") if r["instance_id"] == numpy_iid)
    numpy_excerpt["observed_profiles"].append({"ledger": f"runs/r2e_rf_20260923/remote/ledger_r2e_{stem}.jsonl", "image_identity": r["image_identity"], "scripts_digest": r["scripts_digest"], "candidate_patch_sha256": r["candidate"]["patch_sha256"], "policy": r["policy"], "resource": r["resource"], "report": r["report"], "log": rel(local_path(r["log"]["path"]))})
(OUT / "contrast_producers.json").write_text(json.dumps(contrast_results, ensure_ascii=False, indent=2) + "\n")
(OUT / "numpy_source_and_profiles.json").write_text(json.dumps(numpy_excerpt, ensure_ascii=False, indent=2) + "\n")

summary = {
    "source_pins_verified": pin_results,
    "parser": {"source": rel(vendor), "sha256": sha(vendor), "method": "AST extract fixed upstream pure functions; no RH2/reconcile import"},
    "raw_task_count": len(raw),
    "inspected_row_count": sum(map(len, results.values())),
    "unique_reference_log_count": len(reference_cache),
    "m3_ledger_hashes_and_rewards_verified": sum(r["sha256_matches"] and r["reward_matches"] for r in m3_ledger_checks),
    "old_v3_ledger_hashes_and_rewards_verified": sum(r["sha256_matches"] and r["reward_matches"] for r in old_ledger_checks),
    "ledger_counts": {s: len(rs) for s, rs in results.items()},
    "reward_counts": {s: dict(collections.Counter(str(r["report"]["reward"]) for r in rs)) for s, rs in results.items()},
    "reference_map_equal_counts": {s: sum(r.get("all_reference_maps_equal", False) for r in rs) for s, rs in results.items() if s[:8] != "contrast"},
    "reference_differences": [{"ledger": r["ledger"], "instance_id": r["instance_id"], "diffs": r["reference_comparisons"]} for rs in results.values() for r in rs if r.get("all_reference_maps_equal") is False],
    "localized_copy_count": len(copy_checks),
    "issues": issues,
}
(OUT / "row_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
(OUT / "provenance_checks.json").write_text(json.dumps({"copies": copy_checks, "driver_summaries": driver_summaries, "references": reference_cache, "m3_ledger": m3_ledger_checks, "old_v3_ledger": old_ledger_checks}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "reference_differences"}, ensure_ascii=False, indent=2))
print("reference difference rows:", [(r["instance_id"], r["ledger"].rsplit("/", 1)[1]) for r in summary["reference_differences"]])
raise SystemExit(bool(issues))
