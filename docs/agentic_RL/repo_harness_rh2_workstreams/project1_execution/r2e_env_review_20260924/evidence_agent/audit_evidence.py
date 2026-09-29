#!/usr/bin/env python3
"""离线独立核账；只执行固定 vendor 函数，不导入本轮汇总器/判分器。"""
from __future__ import annotations

import ast
import collections
import copy
import hashlib
import json
from pathlib import Path
import re


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2").is_dir())
OUT = Path(__file__).resolve().parent
DOC = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924"
DATA = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e"
RUN = ROOT / "runs/r2e_env_repair_20260924"
RF = ROOT / "runs/r2e_rf_20260923/remote"
M3 = ROOT / "runs/env_overnight_20260916/M3"
OLD = ROOT / "runs/env_probe_20260909_codex_backup/ledger"
START, END = ">>>>> Start Test Output", ">>>>> End Test Output"
issues, observations, hashes = [], [], {}


def rel(p):
    return str(p.relative_to(ROOT))


def sha(p):
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    hashes[rel(p)] = digest
    return digest


def no_duplicate_keys(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"duplicate JSON key: {k}")
        result[k] = v
    return result


def decode(s):
    return json.loads(s, object_pairs_hook=no_duplicate_keys)


def read(p):
    sha(p)
    return decode(p.read_text())


def rows(p):
    sha(p)
    return [decode(s) for s in p.read_text().splitlines() if s.strip()]


def check(ok, where, what):
    if not ok:
        issues.append({"where": str(where), "what": what})


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


pins = read(DATA / "t1_input_pins_r2e_v1.json")["pins"]
for key, pin in pins.items():
    check(sha(ROOT / pin["path"]) == pin["sha256"], key, "input pin hash")
manifest = read(DATA / "ingest/ingest_manifest_v0.json")
for name, fact in manifest["files"].items():
    p = DATA / "ingest" / name
    check(sha(p) == fact["sha256"] and len(rows(p)) == fact["count"] == 48, name, "ingest hash/count")
check({k: p["sha256"] for k, p in pins.items()} == manifest["t1_input_pins"], "ingest", "input pins differ")
names = {"parse_log_pytest", "_decolor", "calculate_reward", "extract_gold_patch"}
vendor = ROOT / pins["rule_source"]["path"]
definitions = [n for n in ast.parse(vendor.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in definitions} == names
scope = {"json": json, "re": re}
exec(compile(ast.Module(body=definitions, type_ignores=[]), rel(vendor), "exec"), scope)


def normalize(mapping):
    clean = scope["_decolor"](mapping)
    return {k.split(" - ")[0]: clean[k] for k in sorted(clean)}


def parsed(text):
    return normalize(scope["parse_log_pytest"](text))


def stats(exp, obs):
    return {
        "expected_count": len(exp), "observed_count": len(obs),
        "match_count": sum(k in obs and obs[k] == v for k, v in exp.items()),
        "total_count": len(set(exp) | set(obs)), "missing": sorted(set(exp) - set(obs)),
        "unexpected": sorted(set(obs) - set(exp)),
        "mismatched": sorted(k for k in set(exp) & set(obs) if exp[k] != obs[k]),
        "keys_equal": set(exp) == set(obs),
    }


def mapping_diff(a, b):
    return {k: [a.get(k), b.get(k)] for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)}


rawrows = rows(ROOT / pins["raw_archive"]["path"])
raw = {f"{r['repo_name']}__{r['commit_hash']}": r for r in rawrows}
check(len(raw) == len(rawrows) == 48, "raw", "48 unique tasks")
expected = {iid: normalize(decode(r["expected_output_json"])) for iid, r in raw.items()}
grading = {r["instance_id"]: r for r in rows(DATA / "ingest/grading_bundles_r2e_v0.jsonl")}
env = {r["instance_id"]: r for r in rows(DATA / "ingest/environment_packages_v0.jsonl")}
overlays = {r["task_id"]: r for r in rows(RF / "overlays_all.jsonl")}
for family, items in [("grading", grading), ("env", env)]:
    check(set(items) == set(raw), family, "task inventory")
for iid in raw:
    check(raw[iid]["expected_output_json"] == grading[iid]["expected_output_json"], iid, "raw/ingest expected differs")


def local(remote):
    for prefix, root in [("/work/envrepair/", RUN), ("/work/replay/", RF)]:
        if remote.startswith(prefix):
            return root / remote.removeprefix(prefix)
    raise ValueError(f"unexpected evidence path {remote}")


def refs(iid, kind):
    repo, commit = iid.split("__")
    if kind == "noop":
        paths = list((M3 / "facts" / commit[:12] / "noop_x2").glob("out*.txt"))
    else:
        paths = list((M3 / "gold_ledger/logs_r2e" / repo / commit[:12] / "gold").glob("a*/test_output.txt"))
    return sorted(paths + list((OLD / "logs_r2e" / repo / commit[:12] / kind).glob("a*/test_output.txt")))


reference_cache = {}
all_report_ids, all_log_paths, all_start_ids = [], [], []
all_results, ledger_rows = {}, {}


def inspect(r, ledger, line):
    context = f"{rel(ledger)}:{line}"
    iid, kind = r["instance_id"], r["candidate"]["kind"]
    check(iid in raw and r["task_id"] == "r2e_gym_subset::" + iid, context, "task identity")
    log, sidepath = local(r["log"]["path"]), local(r["diagnostics_ref"])
    logtext = log.read_text(errors="replace")
    side = read(sidepath)
    check(r["log"]["sha256"] == "sha256:" + sha(log), context, "log hash")
    for key in ["task_id", "scripts_digest", "image_identity", "observations", "runner_integrity_changed", "execution_failure_decision", "env_qualification", "resource_facts"]:
        check(side.get(key) == r.get(key), context, "sidecar " + key)
    check(side.get("verdict") == r["verdict_diagnostics"] and side.get("candidate") == r["install"], context, "sidecar verdict/candidate")
    check(r["stage_error"] is None and r["cleanup"]["removed"] and not r["log"]["partial"], context, "execution/cleanup/partial")
    check(r["test"]["segment_completed"] and logtext.count(START) == logtext.count(END) == 1, context, "test segment/markers")
    segment = logtext.split(START, 1)[1].split(END, 1)[0]
    obs, exp = parsed(segment), expected[iid]
    summary = stats(exp, obs)
    reward = float(summary["match_count"] == summary["total_count"])
    check(summary == r["verdict_diagnostics"]["expected_match"], context, "independent expected-map stats")
    check(r["report"]["reward"] == reward and r["report"]["expected_match"] == summary["match_count"] and r["report"]["expected_total"] == summary["total_count"], context, "independent report")
    check(r["report"]["grading_semantics"] == "r2e_expected_map", context, "grading semantics")
    rcs = re.findall(r"^RH2_TEST_RC=(\d+)$", logtext, re.M)
    check(len(rcs) == 1 and int(rcs[0]) == r["test"]["rc"], context, "raw test rc")
    ov = overlays[r["task_id"]]
    check(ov["derived_image_id"] == r["image_id_actual"] == r["overlay"]["derived_image_id"], context, "overlay/image ID")
    check(ov["base_image_manifest_digest"] == env[iid]["image_manifest_digest"] == r["image_digest_expected"], context, "base image digest")
    check(r["image_identity"] == "local_build:" + r["image_id_actual"], context, "image identity")
    for marker, value in [("RH2_SETUP_HIDDEN_TESTS_TREE", grading[iid]["hidden_tests_tree_sha256"]), ("RH2_SETUP_ENTRY_SHA256", grading[iid]["run_tests_sh_sha256"])]:
        check(f"{marker}={value.removeprefix('sha256:')}" in logtext, context, marker)
    check(r["observations"]["RH2_OBS_RUNNER_DIGEST_PRE"] == r["observations"]["RH2_OBS_RUNNER_DIGEST"] and not r["runner_integrity_changed"], context, "runner integrity")
    check(r["observations"]["RH2_OBS_IMPORT_PATH"].startswith("/testbed/"), context, "grader import path")
    if kind == "gold":
        patch = scope["extract_gold_patch"](raw[iid]["parsed_commit_content"])
        check(r["candidate"]["patch_sha256"] == "sha256:" + hashlib.sha256(patch.encode()).hexdigest(), context, "source gold patch hash")
    comparisons = []
    for ref in refs(iid, kind):
        if rel(ref) not in reference_cache:
            rt = ref.read_text(errors="replace")
            reference_cache[rel(ref)] = {"sha256": sha(ref), "map": parsed(rt), "reward": scope["calculate_reward"](rt, raw[iid]["expected_output_json"])}
        rf = reference_cache[rel(ref)]
        diff = mapping_diff(obs, rf["map"])
        comparisons.append({"path": rel(ref), "maps_equal": not diff, "reward_equal": rf["reward"] == reward, "diff": diff})
    check(len(comparisons) in {2, 5}, context, "reference coverage")
    all_report_ids.append(r["report"]["report_id"])
    all_log_paths.append(r["log"]["path"])
    all_start_ids.append((r["run_id"], iid, r["attempt"]))
    return {"ledger": context, "instance_id": iid, "kind": kind, "run_id": r["run_id"], "log": rel(log), "sidecar": rel(sidepath), "reward": reward, "map": obs, "stats": summary, "references": comparisons, "all_reference_maps_equal": all(x["maps_equal"] for x in comparisons), "policy": r["policy"], "mem_peak_mb": r["resource"]["mem_peak_mb"]}


paths = {
    "central_noop": RUN / "_rerun2/ledger_noop.jsonl", "central_gold": RUN / "_rerun2/ledger_gold.jsonl",
    "central_resource_noop": RUN / "_rerun2/ledger_numpy_bigtmp_noop.jsonl", "central_resource_gold": RUN / "_rerun2/ledger_numpy_bigtmp_gold.jsonl",
    "rf_noop": RF / "ledger_r2e_all_noop.jsonl", "rf_gold": RF / "ledger_r2e_all_gold.jsonl",
    "rf_resource_noop": RF / "ledger_r2e_numpy_bigtmp_noop.jsonl", "rf_resource_gold": RF / "ledger_r2e_numpy_bigtmp_gold.jsonl",
}
for name, p in paths.items():
    rs = rows(p)
    ledger_rows[name] = rs
    ids = [r["instance_id"] for r in rs]
    check(len(ids) == len(set(ids)), name, "duplicate instance")
    check(set(ids) == (set(raw) if "resource" not in name else {"numpy__2f4a965019722c3c56f43433bfa4a99c4c083138"}), name, "missing/unexpected task")
    all_results[name] = [inspect(r, p, i) for i, r in enumerate(rs, 1)]
for name, items in [("reports", all_report_ids), ("log paths", all_log_paths), ("run/task/attempt", all_start_ids)]:
    check(len(items) == len(set(items)), "all 196 rows", "duplicate " + name)

repeat_results = []
for kind in ["noop", "gold", "resource_noop", "resource_gold"]:
    a = {r["instance_id"]: r for r in all_results["central_" + kind]}
    b = {r["instance_id"]: r for r in all_results["rf_" + kind]}
    original_a = {r["instance_id"]: r for r in ledger_rows["central_" + kind]}
    original_b = {r["instance_id"]: r for r in ledger_rows["rf_" + kind]}
    for iid in a:
        diff = mapping_diff(a[iid]["map"], b[iid]["map"])
        fields = ["policy", "scripts_digest", "overlay", "image_id_actual", "image_digest_expected", "candidate", "baseline_policy_version"]
        identity_diff = [k for k in fields if original_a[iid][k] != original_b[iid][k]]
        budget_diff = mapping_diff(original_a[iid]["budgets"], original_b[iid]["budgets"])
        check(not diff and a[iid]["stats"] == b[iid]["stats"] and a[iid]["reward"] == b[iid]["reward"], iid + ":" + kind, "R-f/central map/reward/stats")
        check(not identity_diff, iid + ":" + kind, "repeat identity differs: " + str(identity_diff))
        repeat_results.append({"instance_id": iid, "kind": kind, "maps_equal": not diff, "map_diff": diff, "identity_diff": identity_diff, "budget_diff_central_rf": budget_diff})

observations.append({"kind": "repeat_budget_change", "rows": sum(bool(r["budget_diff_central_rf"]) for r in repeat_results), "difference_central_rf": repeat_results[0]["budget_diff_central_rf"], "interpretation": "资源 policy、镜像、candidate 和评分脚本相同；timeout budgets 不同。全部完整执行且两轮最大 phases 总和小于 900 秒，支持同 profile 的逐键重复，不应称所有运行条件逐字段相同。"})

# 路径本地化副本、远端全量回传副本和 driver 输出各自核账。
copy_results = []
for kind in ["noop", "gold"]:
    p = RUN / f"_rerun2/ledger_{kind}.jsonl"
    q = RUN / f"_rerun2/ledger_{kind}_local.jsonl"
    a, b = rows(p), rows(q)
    for x, y in zip(a, b):
        for key in ["path"]:
            check(Path(y["log"][key]) == local(x["log"][key]), rel(q), "localized log path")
        check(Path(y["diagnostics_ref"]) == local(x["diagnostics_ref"]), rel(q), "localized sidecar path")
        x["log"].pop("path"); y["log"].pop("path")
        x.pop("diagnostics_ref"); y.pop("diagnostics_ref")
    check(a == b, rel(q), "localization changes data")
    output = RUN / f"_rerun2/run_{kind}.log"
    parsed_rows = [decode(s) for s in output.read_text().splitlines() if s.startswith("{")]
    emitted = [r for r in parsed_rows if "task_id" in r]
    final = [r for r in parsed_rows if "final_status" in r]
    check(len(final) == 1 and final[0]["rows"] == 48 and final[0]["final_status"]["exit_code"] == 0 and not final[0]["manager_close"]["containers_open"] and not final[0]["cleanup_failures"], rel(output), "driver final count/cleanup")
    original = ledger_rows["central_" + kind]
    check(len(emitted) == 48 and all(x["task_id"] == y["task_id"] and x["reward"] == y["report"]["reward"] and x["outcome"] == y["report"]["outcome"] for x, y in zip(emitted, original)), rel(output), "driver emitted rows differ")
for p in sorted((RUN / "_rerun2").rglob("*")):
    if p.is_file() and "_local" not in p.name:
        q = RUN / "remote_envrepair_final" / p.relative_to(RUN)
        same = q.exists() and sha(p) == sha(q)
        check(same, rel(p), "remote archive copy differs/missing")
        copy_results.append({"path": rel(p), "same": same})

# 对账工具结果只用作被核对象，不用作 oracle。
reconciliation = read(RUN / "reconcile_rerun2/reconcile.json")
check(len(reconciliation) == 96 and len({(r["instance_id"], r["kind"]) for r in reconciliation}) == 96, "reconcile", "inventory")
for row in reconciliation:
    result = next(r for r in all_results["central_" + row["kind"]] if r["instance_id"] == row["instance_id"])
    check(row["observed_maps_equal"] == result["all_reference_maps_equal"] and row["agree"] == result["all_reference_maps_equal"], row["instance_id"], "reconcile map equality")

reference_ledger_rows = 0
for base, ledger in [(M3, M3 / "gold_ledger/r2e_gold_m3.jsonl"), (OLD, OLD / "r2e_ledger_v3.jsonl")]:
    for r in rows(ledger):
        prefix = base / "gold_ledger" if base == M3 else base
        p = prefix / "logs_r2e" / r["repo"] / r["commit_hash"][:12] / r["gate"] / f"a{r['attempt']}" / "test_output.txt"
        cached = reference_cache[rel(p)]
        check(r["log_sha256"] == "sha256:" + cached["sha256"] and r["reward"] == cached["reward"], rel(p), "reference ledger hash/reward")
        reference_ledger_rows += 1


def parse_probe(path):
    """独立读 KEY=value 和 @@BEGIN/END 块；不调用开发探针解析器。"""
    values, blocks, active, lines = {}, {}, None, []
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("@@BEGIN "):
            active, lines = line.removeprefix("@@BEGIN "), []
        elif line.startswith("@@END "):
            check(active == line.removeprefix("@@END "), rel(path), "block closing")
            blocks[active] = "\n".join(lines).strip()
            active = None
        elif active is not None:
            lines.append(line)
        elif re.match(r"^[A-Za-z_][A-Za-z_0-9-]*=", line):
            k, v = line.split("=", 1)
            check(k not in values, rel(path), "duplicate scalar key " + k)
            values[k] = v
    sha(path)
    return values, blocks


def minimum(values):
    return {
        "interpreter_isolated_ok": values.get("PY_ISOLATED_RC") == "0",
        "python_resolves_to_venv": values.get("WHICH_python") == "/testbed/.venv/bin/python",
        "pytest_ok": values.get("PYTEST_RC") == "0",
        "import_from_testbed_ok": values.get("IMPORT_FROM_TESTBED_RC") == "0",
        "import_from_testbed_path_in_testbed": values.get("IMPORT_FROM_TESTBED", "").startswith("/testbed/"),
        "writable_testbed": values.get("WRITE_TESTBED") == "ok",
        "hidden_tests_denied": "Permission denied" in values.get("PRIVATE_LS", "") and "Permission denied" in values.get("PRIVATE_TESTS_LS", ""),
        "git_head_has_no_children": values.get("GIT_HEAD_CHILDREN_WORDS") == "1",
        "network_blocked": values.get("NET_CONNECT_RC") not in [None, "0"],
        "probe_completed": values.get("PROBE_DONE") == "1",
    }


probe_results, acceptance_results, record_results = [], [], []
records = {}
for iid in sorted(raw):
    fact = read(DOC / "tasks" / iid / "facts.json")
    rec = read(DOC / "tasks" / iid / "screening_record.json")
    records[iid] = rec
    check(rec["instance_id"] == fact["identity"]["instance_id"] == iid and rec["task_id"] == fact["identity"]["task_id"] == env[iid]["task_id"], iid, "record/facts identity")
    ov, ident = overlays[rec["task_id"]], fact["identity"]
    for key in ["derived_image_id", "base_image_manifest_digest", "recipe_id", "recipe_sha256"]:
        check(ident[key] == ov[key], iid, "fact/overlay " + key)
    derived = read(RF / "r2e_derived" / iid / "facts.json")
    check(derived["ok"] and not derived["failures"] and all(d["ok"] for d in derived["integrity"].values()), iid, "derived checks")
    check(derived["root_facts"]["head"] == grading[iid]["base_commit"] == env[iid]["base_commit"] == ident["base_commit"], iid, "base commit")
    check("sha256:" + derived["root_facts"]["tree"] == grading[iid]["hidden_tests_tree_sha256"] == ident["hidden_tests_tree_sha256"], iid, "hidden tree")
    check("sha256:" + derived["root_facts"]["run_tests_sh"] == grading[iid]["run_tests_sh_sha256"] == ident["run_tests_sh_sha256"], iid, "runner SHA")
    for kind in ["noop", "gold"]:
        result = next(r for r in all_results["central_" + kind] if r["instance_id"] == iid)
        matching = [r for r in fact["rh2_runs"] if r["run_id"] == result["run_id"]]
        check(len(matching) == 1, iid, "facts central run coverage")
        if matching:
            check(matching[0]["reward"] == result["reward"] and all(matching[0][k] == result["stats"][k] for k in ["mismatched", "missing", "unexpected"]), iid, "facts central result")
    p = ROOT / rec["dev_probe_ref"]
    probe = read(p)
    values, blocks = parse_probe(p.parent / "agent_probe.log")
    check(values == probe["agent"]["values"], rel(p), "probe scalar values/raw log")
    check({k: v.strip() for k, v in probe["agent"]["blocks"].items()} == blocks, rel(p), "probe blocks/raw log")
    conditions = minimum(values)
    check(all(conditions.values()) == probe["derived"]["min_dev_conditions_ok"] and all(conditions[k] == probe["derived"][k] for k in conditions), rel(p), "independent minimal conditions")
    check(probe["instance_id"] == iid and probe["image_id"] == ov["derived_image_id"] and values["GIT_HEAD"] == ident["base_commit"] and values["ID"].startswith("uid=54321(agent)"), rel(p), "probe task/image/head/uid")
    container = read(p.parent / "container.json")[0]
    config = container["HostConfig"]
    check(container["Image"] == probe["image_id"] and container["Name"] == "/" + probe["container"], rel(p), "container identity")
    check(config["NetworkMode"] == "none" and config["Memory"] == 4294967296 and config["NanoCpus"] == 2000000000 and config["PidsLimit"] == 512 and config["ShmSize"] == 67108864, rel(p), "probe resources/network")
    check(probe["container_removed"] and probe["root_init"]["rc"] == 0 and probe["agent"]["exec_rc"] == 0, rel(p), "probe completion")
    check(set(rec["checks"]) == {f"R{i:02d}" for i in range(1, 21)}, iid, "checks inventory")
    probe_results.append({"instance_id": iid, "probe": rel(p), "minimum": conditions, "all_minimum": all(conditions.values()), "pip_present_raw": values["PIP_VERSION"].startswith("pip "), "repro_observed": "REPRO_OBSERVED=1" in blocks.get("REPRO_OUTPUT", ""), "classification": rec["classification"], "disposition": rec["disposition"]["state"]})
    if rec["disposition"]["state"] in {"environment_qualified", "qualified_with_recipe"}:
        check(all(rec["checks"][k]["status"] == "pass" for k in ["R01", "R02", "R08", "R13", "R15"]) and all(conditions.values()), iid, "documented disposition gate")
    nonpassed = {k: v for k, v in expected[iid].items() if v != "PASSED"}
    check(not nonpassed or (bool(rec["checks"]["R06"].get("note")) and bool(rec["checks"]["R06"].get("evidence_refs"))), iid, "non-PASSED R06 attribution missing")
    record_results.append({"instance_id": iid, "classification": rec["classification"], "disposition": rec["disposition"]["state"], "qualification_checks": {k: rec["checks"][k]["status"] for k in ["R01", "R02", "R08", "R13", "R15"]}, "nonpassed_expected": nonpassed, "R06": rec["checks"]["R06"] if nonpassed else None})

for p in sorted((RUN / "_accept").glob("p*/dev_probe/*/dev_probe.json")):
    sample = read(p)
    rec = records[sample["instance_id"]]
    originalp = ROOT / rec["dev_probe_ref"]
    original = read(originalp)
    av, ab = parse_probe(p.parent / "agent_probe.log")
    bv, bb = parse_probe(originalp.parent / "agent_probe.log")
    stable = ["PY_INFO", "PIP_VERSION", "IMPORT_FROM_TMP_RC", "PUBLIC_COLLECT_RC", "PUBLIC_RUN_RC", "REPRO_RC", "GIT_HEAD", "GIT_STATUS_COUNT", "GIT_STATUS_COUNT_AFTER"]
    fields_diff = {k: [av.get(k), bv.get(k)] for k in stable if av.get(k) != bv.get(k)}
    block_diff = {k: [ab.get(k), bb.get(k)] for k in ["GIT_STATUS"] if ab.get(k) != bb.get(k)}
    derived_diff = mapping_diff(sample["derived"], original["derived"])
    check(not fields_diff and not block_diff and minimum(av) == minimum(bv) and all(minimum(av).values()), rel(p), "sample stable values/minimum")
    check(sample["container"] != original["container"] and sample["image_id"] == original["image_id"] and sample["started_at_utc"] != original["started_at_utc"], rel(p), "sample independent execution identity")
    # 统一 pip 的明确解释后，不运行作者解析器，直接核剩余 derived。
    adjusted = copy.deepcopy(sample["derived"])
    adjusted["pip_ok"] = av.get("PIP_VERSION", "").startswith("pip ")
    residual_diff = mapping_diff(adjusted, original["derived"])
    check(not residual_diff, rel(p), "sample derived differs beyond known pip version fix")
    acceptance_results.append({"instance_id": sample["instance_id"], "path": rel(p), "sample_parser_version": sample.get("parser_version"), "package_parser_version": original.get("parser_version"), "stored_derived_diff": derived_diff, "stable_values_diff": fields_diff, "stable_blocks_diff": block_diff, "same_minimum": minimum(av) == minimum(bv), "derived_diff_after_explicit_pip_fix": residual_diff, "repro_observed": "REPRO_OBSERVED=1" in ab.get("REPRO_OUTPUT", "")})
check(len(acceptance_results) == 8, "acceptance", "expected 8 samples")
dispositions = read(DOC / "dispositions.json")["tasks"]
for iid, entry in dispositions.items():
    check(entry["status"] == records[iid]["disposition"]["state"], iid, "dispositions/record")
check(set(dispositions) == {iid for iid, r in records.items() if r["disposition"]["state"] in {"held_material", "needs_decision"}}, "dispositions", "exception inventory")

all_refs = []
def collect_refs(node, context):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in {"evidence_refs", "revision_refs", "evidence"} and isinstance(v, list):
                all_refs.extend((context, x) for x in v if isinstance(x, str))
            elif k in {"facts_ref", "dev_probe_ref"} and isinstance(v, str):
                all_refs.append((context, v))
            else:
                collect_refs(v, context)
    elif isinstance(node, list):
        for v in node:
            collect_refs(v, context)
for p in sorted((DOC / "tasks").glob("*/*.json")) + [DOC / "dispositions.json", DOC / "known_issues.json", DOC / "recipes/task_resources_v1.json"]:
    collect_refs(read(p), rel(p))
generic_refs = []
for context, ref in all_refs:
    pathpart = re.split(r"#| §|（| \(", ref)[0]
    exists = (ROOT / pathpart).exists() or (DOC / pathpart).exists()
    if not exists and ref == "tasks/<iid>/facts.json → rh2_runs[].non_passed_reasons":
        exists = all((DOC / "tasks" / iid / "facts.json").exists() for iid in raw)
        generic_refs.append(ref)
    if not exists and ref == "runbook_rf §7":
        exists = (DOC.parent / "r2e_grading_wiring_20260920/runbook_rf.md").exists()
        generic_refs.append(ref)
    check(exists, context, "missing evidence reference: " + ref)

observations.extend([
    {"kind": "stale_summary_count", "actual_nonpassed_tasks": 20, "actual_keys": 93, "status_counts": dict(collections.Counter(v for r in record_results for v in r["nonpassed_expected"].values())), "document_claim": "README/known_issues：16 题；可信输入和 facts 均为 20 题，20/20 R06 有原因与引用，没有发现漏审四题。"},
    {"kind": "stale_reference_task_count", "actual": 47, "denominator": 48, "document_claim": "README §2：46 题 agree；94/96 行 = 47 题 × noop/gold，只有 numpy 一题不一致。"},
    {"kind": "sample_parser_version", "stored_derived_equal": sum(not r["stored_derived_diff"] for r in acceptance_results), "after_explicit_pip_fix_equal": 8, "interpretation": "5 份 _accept 的 v2 pip_ok=true 与原始 No module named pip 矛盾；仅该字段不同。最小十条件不含 pip，原始关键字段和最小条件全同。"},
])

summary = {
    "scope": "本机离线；196 条真实评分记录（本轮 98 + R-f 98）、336 份参考日志、48 题 facts/record/probe、8 题抽验；不新增真实容器运行。",
    "issues": issues,
    "observations": observations,
    "rows": {name: {"count": len(rs), "rewards": dict(collections.Counter(str(r["reward"]) for r in rs)), "reference_maps_equal": sum(r["all_reference_maps_equal"] for r in rs)} for name, rs in all_results.items()},
    "repeat_comparisons": len(repeat_results), "repeat_maps_equal": sum(r["maps_equal"] for r in repeat_results),
    "unique_reference_logs": len(reference_cache), "central_archive_files_equal": sum(r["same"] for r in copy_results),
    "reference_ledger_hash_reward_checked": reference_ledger_rows,
    "evidence_references_checked": len(all_refs), "generic_references_resolved_manually": generic_refs,
    "max_phases_seconds_by_ledger": {k: max(sum(r["phases"].values()) for r in rs) for k, rs in ledger_rows.items()},
    "all_minimum_conditions": sum(r["all_minimum"] for r in probe_results),
    "public_repros_observed": sum(r["repro_observed"] for r in probe_results),
    "pip_absent": sum(not r["pip_present_raw"] for r in probe_results),
    "classification": dict(collections.Counter(r["classification"] for r in record_results)),
    "disposition": dict(collections.Counter(r["disposition"] for r in record_results)),
    "nonpassed_expected_tasks": sum(bool(r["nonpassed_expected"]) for r in record_results),
    "nonpassed_expected_status_counts": dict(collections.Counter(v for r in record_results for v in r["nonpassed_expected"].values())),
    "acceptance_count": len(acceptance_results),
    "acceptance_stored_derived_equal": sum(not r["stored_derived_diff"] for r in acceptance_results),
    "acceptance_after_pip_correction_equal": sum(not r["derived_diff_after_explicit_pip_fix"] for r in acceptance_results),
}
dump("summary.json", summary)
dump("rows.json", all_results)
dump("repeats.json", repeat_results)
dump("references.json", reference_cache)
dump("record_checks.json", record_results)
dump("probe_checks.json", probe_results)
dump("acceptance_checks.json", acceptance_results)
dump("file_hashes.json", hashes)
print(json.dumps(summary, ensure_ascii=False, indent=2))
