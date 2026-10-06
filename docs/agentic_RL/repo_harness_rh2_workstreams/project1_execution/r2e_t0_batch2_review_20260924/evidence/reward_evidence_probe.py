"""批次二独立离线核对；只读原材料和历史证据，不运行 Docker/远端。"""

import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[6]
DOC = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
BATCH = ROOT / "runs/r2e_t0_batch2_20260924"
REVISIONS = DOC / "s2_r2e/revisions"
PD = "pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199"
SC = "scrapy__cfed9b6659c90e0799361911b1d72ed127edf471"
O3 = "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"


def load(path):
    return json.loads(path.read_text())


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def statuses(text):
    """独立提取本次 pytest 摘要中的真实 nodeid，不调用生产 parser/reconcile。"""
    chunks = text.split("short test summary info")
    assert len(chunks) == 2, len(chunks)
    pairs = []
    for line in chunks[1].splitlines():
        match = re.match(r"^(PASSED|FAILED|ERROR)\s+(?:/testbed/)?r2e_tests/[^:]+::(.+?)(?: - .*)?$", line)
        if match:
            pairs.append((match[2].replace("::", "."), match[1]))
    assert pairs and len(pairs) == len(dict(pairs)), "摘要为空或重名"
    return dict(pairs)


def fixture_text(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    first = min([node.lineno] + [d.lineno for d in node.decorator_list])
    return "\n".join(text.splitlines()[first - 1:node.end_lineno])


raw = {}
for line in (DOC / "s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl").read_text().splitlines():
    row = json.loads(line)
    raw[row["repo_name"].split("/")[-1] + "__" + row["commit_hash"]] = row
if PD not in raw:  # repo_name 已可能是缩写或带组织名，统一由 commit 定位。
    raw = {next(x for x in [PD, SC, O3] if x.endswith(r["commit_hash"])): r
           for r in raw.values() if any(x.endswith(r["commit_hash"]) for x in [PD, SC, O3])}

result = {"scope": "只读两题原断言、修订与 8 正式行、16 次 dryrun，orange3 7 次诊断及 48 份状态记录"}
conf_src = (BATCH / "drafts_src/pandas_conftest_base_baa10328.py").read_bytes()
conf_rev = (REVISIONS / "files" / PD / "r2e_tests/conftest.py").read_text()
assert git_blob(conf_src) == "46975aa039b18fbb29f9edffb339d0ad96066ddb"
for fixture in ("any_float_dtype", "any_int_ea_dtype"):
    assert fixture_text(conf_src.decode(), fixture) == fixture_text(conf_rev, fixture)
egg_src = (BATCH / "drafts_src/scrapy_test_54216d7a.egg").read_bytes()
egg_rev = (REVISIONS / "files" / SC / "r2e_tests/test.egg").read_bytes()
assert egg_src == egg_rev and git_blob(egg_src) == "238517694b306bb2daa59a6734d26f14f0a55c98"
result["support_provenance"] = {
    "pandas_base_conftest_git_blob": git_blob(conf_src),
    "fixture_decorators_and_bodies_byte_equal": True,
    "scrapy_egg_git_blob": git_blob(egg_src), "scrapy_egg_bytes": len(egg_src),
    "scrapy_egg_revision_equals_captured_base": True,
    "limit": "本次核对本地来源快照及已记录 git blob；未重新访问远端仓库或镜像",
}

source_tests = {}
for iid, expected_paths in [(PD, ["pandas/tests/groupby/test_quantile.py"]),
                            (SC, ["tests/test_utils_misc/__init__.py", "tests/test_middleware.py"])]:
    execution = json.loads(raw[iid]["execution_result_content"])
    codes = dict(zip(execution["test_file_names"], execution["test_file_codes"]))
    commit = json.loads(raw[iid]["parsed_commit_content"])
    files = {f["header"]["file"]["path"]: f for f in commit["file_diffs"]}
    for number, path in enumerate(expected_paths, 1):
        assert codes[f"test_{number}.py"] == files[path]["new_file_content"]
    source_tests[iid] = {"tests_equal_original_fix_commit_new_file_content": True,
                         "base_commit": commit["old_commit_hash"], "test_paths": expected_paths}
source_sc = json.loads(raw[SC]["execution_result_content"])
sc_old = dict(zip(source_sc["test_file_names"], source_sc["test_file_codes"]))["test_2.py"]
sc_new = (REVISIONS / "files" / SC / "r2e_tests/test_2.py").read_text()
assert sc_old.count("'tests.test_middleware.%s'") == 1
assert sc_old.count("'tests.test_middleware.M1'") == 1
assert sc_new == sc_old.replace("'tests.test_middleware.%s'", "'r2e_tests.test_2.%s'").replace(
    "'tests.test_middleware.M1'", "'r2e_tests.test_2.M1'")
source_tests[SC]["only_changes_two_self_references"] = True
result["original_assertions"] = source_tests

expected = {PD: load(REVISIONS / "files" / PD / "expected_output.json"),
            SC: json.loads(raw[SC]["expected_output_json"])}
changed_sc = ["UtilsMiscTestCase.test_walk_modules_egg", "MiddlewareManagerTest.test_enabled_from_settings",
              "MiddlewareManagerTest.test_instances_from_settings"]
for key in changed_sc:
    assert expected[SC][key] == "FAILED"
    expected[SC][key] = "PASSED"
diffs = {}
for iid in (PD, SC):
    before = json.loads(raw[iid]["expected_output_json"])
    after = expected[iid]
    diffs[iid] = {
        "before_count": len(before), "after_count": len(after),
        "removed": {k: before[k] for k in before.keys() - after.keys()},
        "added": {k: after[k] for k in after.keys() - before.keys()},
        "changed": {k: [before[k], after[k]] for k in before.keys() & after.keys() if before[k] != after[k]},
    }
assert len(diffs[PD]["removed"]) == 2 and len(diffs[PD]["added"]) == 13 and not diffs[PD]["changed"]
assert len(diffs[SC]["changed"]) == 3 and not diffs[SC]["removed"] and not diffs[SC]["added"]
result["expected_changes"] = diffs

dryruns = {}
for path in sorted((BATCH / "dryrun_b2").glob("*.test.log")):
    observed = statuses(path.read_text())
    label = path.name.removesuffix(".test.log")
    dryruns[label] = observed
result["dryruns"] = {label: {"count": len(observed), "non_passed": {k: v for k, v in observed.items() if v != "PASSED"}}
                     for label, observed in dryruns.items()}
for iid, prefix in [(PD, "pandas"), (SC, "scrapy")]:
    assert json.dumps(dryruns[prefix + "_gold_orig"], indent=4) == raw[iid]["expected_output_json"]
    assert dryruns[prefix + "_gold_fix_a"] == dryruns[prefix + "_gold_fix_b"] == expected[iid]
    assert dryruns[prefix + "_noop_fix_a"] == dryruns[prefix + "_noop_fix_b"]
result["dryruns_original_gold_reconstructs_source_expected_exact_text"] = True

formal = []
for kind in ("noop", "gold"):
    path = BATCH / f"replay_b3/ledger_b3_{kind}_local.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 4
    for row in rows:
        iid = row["instance_id"]
        logpath = BATCH / "replay_b3/eval_logs" / Path(row["log"]["path"]).name
        logbytes = logpath.read_bytes()
        assert sha(logbytes) == row["log"]["sha256"]
        observed = statuses(logbytes.decode())
        exp = expected[iid]
        mismatch = sorted(k for k in exp.keys() & observed.keys() if exp[k] != observed[k])
        missing = sorted(exp.keys() - observed.keys())
        extra = sorted(observed.keys() - exp.keys())
        vd = row["verdict_diagnostics"]["expected_match"]
        assert mismatch == vd["mismatched"] and missing == vd["missing"] and extra == vd["unexpected"]
        assert row["report"]["expected_match"] == len(exp) - len(mismatch) - len(missing)
        assert row["report"]["expected_total"] == len(exp) == len(observed)
        assert row["report"]["reward"] == float(not (mismatch or missing or extra)) == float(kind == "gold")
        prefix = "pandas" if iid == PD else "scrapy"
        assert observed == dryruns[f"{prefix}_{kind}_fix_a"]
        assert row["overlay"]["recipe_id"] == "r2e_derive_v1+material_v2"
        assert row["image_id_actual"] == row["overlay"]["derived_image_id"]
        assert row["stage_error"] is None and row["cleanup"]["removed"]
        assert row["runner_integrity_changed"] is False and row["log"]["partial"] is False
        assert row["observations"]["RH2_OBS_IMPORT_PATH"] == f"/testbed/{prefix}/__init__.py"
        assert row["projection"]["included_paths"] == ([] if kind == "noop" else
                ["pandas/core/groupby/groupby.py"] if iid == PD else ["scrapy/middleware.py", "scrapy/utils/misc.py"])
        formal.append({"instance_id": iid, "kind": kind, "attempt": row["attempt"],
                       "expected_match": row["report"]["expected_match"], "total": len(exp),
                       "reward": row["report"]["reward"], "mismatched": mismatch,
                       "log": str(logpath.relative_to(ROOT)), "log_sha256_checked": True,
                       "dryrun_map_equal": True, "cleanup_removed": True})
result["formal_rows"] = formal

orange = {}
for path in sorted((BATCH / "diag_orange3").glob("*.test.log")):
    label = path.name.removesuffix(".test.log")
    obs = statuses(path.read_text())
    setup = path.with_name(label + ".setup.log").read_text()
    versions = re.search(r"^VERSIONS (.+)$", setup, re.M)[1]
    assert versions.split()[1:] == ["0.22.2.post1", "1.17.5"]
    assert "SETUP_RC=0" in setup
    orange[label] = {"versions_scipy_sklearn_numpy": versions, "count": len(obs),
                     "non_passed": {k: v for k, v in obs.items() if v != "PASSED"}}
    if label.startswith(("s141", "s154")):
        assert obs["TestLogisticRegressionLearner.test_LogisticRegression"] == "PASSED"
        assert obs["TestLogisticRegressionLearner.test_coefficients"] == "PASSED"
        assert obs["TestLogisticRegressionLearner.test_learner_scorer"] == "FAILED"
        assert obs["TestLogisticRegressionLearner.test_learner_scorer_multiclass"] == "FAILED"
    warn = path.with_name(label + ".warn.log")
    if warn.exists():
        orange[label]["separate_warning_rerun_reports_convergence_warning"] = "ConvergenceWarning" in warn.read_text()
result["orange_diagnostics"] = orange

taskroot = DOC / "project1_execution/r2e_env_repair_20260924/tasks"
records = [load(p) for p in sorted(taskroot.glob("*/screening_record.json"))]
counts = dict(Counter(r["disposition"]["state"] for r in records))
assert len(records) == 48 and counts == {"environment_qualified": 32, "qualified_with_recipe": 2,
    "qualified_with_revision": 4, "grading_ok_open_items": 10}
groups = defaultdict(list)
rendered = (taskroot.parent / "results_20260924.md").read_text()
for rec in records:
    iid = rec["instance_id"]
    state = rec["disposition"]["state"]
    groups[state].append(iid)
    repo, commit = iid.split("__")
    line = next(line for line in rendered.splitlines() if line.startswith(f"| {repo} `{commit[:8]}` |"))
    assert line.split("|")[3].strip() == state
    assert bool(rec["disposition"].get("open_items")) == (state == "grading_ok_open_items")
result["record_counts"] = counts
result["record_status_groups"] = dict(groups)
result["results_table_matches_all_record_states"] = True
result["all_assertions_passed"] = True
print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
