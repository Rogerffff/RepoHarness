"""四题原件的只读审计；不运行项目、容器或候选补丁。输出限于本目录。"""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
PREP = ROOT / "runs/r2e_static_prep_20260924/v2"
GR = ROOT / "runs/r2e_actor_20260925/grader"
DEV = ROOT / "runs/r2e_actor_20260925/devcheck"
KEYS = ["18b7cd9d", "61833518", "2b061b68", "9a15fcf8"]
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def sha(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def load(path):
    return json.loads(path.read_text())


materials = {}
for key in KEYS:
    directory = next((PREP / "private").glob("*__" + key + "*"))
    bundle = load(directory / "grading_bundle.json")["row"]
    checks = {
        "expected_sha_matches": sha(directory / "expected_output.json")
        == bundle["expected_output_json_sha256"],
        "entry_sha_matches": sha(directory / "run_tests.sh")
        == bundle["run_tests_sh_sha256"],
        "hidden_files_sha_match": all(
            sha(directory / "hidden_tests" / item["path"]) == item["sha256"]
            for item in bundle["hidden_test_files"]
        ),
    }
    assert all(checks.values()), (key, checks)
    materials[directory.name] = {
        "directory": relative(directory),
        "expected": {
            ANSI.sub("", name): value
            for name, value in load(directory / "expected_output.json").items()
        },
        "bundle": bundle,
        "checks": checks,
    }


def audit_row(ledger, line, log_dir, old=False):
    row = json.loads(ledger.read_text().splitlines()[line - 1])
    iid = row["instance_id"]
    material = materials[iid]
    log = log_dir / Path(row["log"]["path"]).name
    text = ANSI.sub("", log.read_text())
    segment = text.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
    observed = {}
    for status, node in re.findall(r"^(PASSED|FAILED|ERROR)\s+(r2e_tests/\S+)", segment, re.M):
        key = ".".join(node.split("::")[1:])
        assert key not in observed, (ledger, key)
        observed[key] = status
    expected = material["expected"]
    mismatch = sorted(k for k in expected.keys() & observed.keys() if expected[k] != observed[k])
    missing = sorted(expected.keys() - observed.keys())
    unexpected = sorted(observed.keys() - expected.keys())
    matches = sum(expected[k] == observed.get(k) for k in expected)
    candidate_name = Path(row["candidate"]["origin"]).name
    if old:
        candidate_path = ledger.parent / "overfix" / candidate_name
    elif row["candidate"]["kind"] == "gold":
        candidate_path = PREP / "private" / iid / "gold.patch"
    else:
        candidate_path = GR / "cands" / candidate_name
    checks = {
        "log_sha_matches": sha(log) == row["log"]["sha256"],
        "patch_sha_matches": sha(candidate_path) == row["candidate"]["patch_sha256"],
        "hidden_tree_marker_matches": "RH2_SETUP_HIDDEN_TESTS_TREE="
        + material["bundle"]["hidden_tests_tree_sha256"].removeprefix("sha256:") in text,
        "entry_marker_matches": "RH2_SETUP_ENTRY_SHA256="
        + material["bundle"]["run_tests_sh_sha256"].removeprefix("sha256:") in text,
        "report_matches_reparse": matches == row["report"]["expected_match"]
        and len(expected) == row["report"]["expected_total"],
        "diagnostic_matches_reparse": mismatch
        == sorted(row["verdict_diagnostics"]["expected_match"]["mismatched"])
        and missing == row["verdict_diagnostics"]["expected_match"]["missing"]
        and unexpected == row["verdict_diagnostics"]["expected_match"]["unexpected"],
        "reward_matches_reparse": row["report"]["reward"]
        == float(not (mismatch or missing or unexpected)),
        "no_test_or_fixture_edit_recorded": not row["candidate_test_like_paths"]
        and not row["candidate_touched_conftest_or_fixture"],
    }
    second_copy = ROOT / "runs/r2e_actor_20260925/grader_cands" / candidate_name
    if second_copy.exists():
        checks["candidate_copy_matches"] = sha(second_copy) == sha(candidate_path)
    assert all(checks.values()), (ledger, checks)
    return {
        "ledger": relative(ledger),
        "line": line,
        "instance_id": iid,
        "old_p4_not_current_batch": old,
        "started_at_utc": row["started_at_utc"],
        "reward": row["report"]["reward"],
        "match": f"{matches}/{len(expected)}",
        "observed_status_counts": {s: list(observed.values()).count(s) for s in set(observed.values())},
        "mismatched": mismatch,
        "missing": missing,
        "unexpected": unexpected,
        "patch": relative(candidate_path),
        "patch_sha256": sha(candidate_path),
        "log": relative(log),
        "log_sha256": sha(log),
        "included_paths": row["projection"]["included_paths"],
        "image_id_actual": row["image_id_actual"],
        "checks": checks,
    }


rows = []
for pattern in ["ledger_np_*.jsonl", "ledger_aio_*.jsonl", "ledger_pil_*.jsonl"]:
    for ledger in sorted(GR.glob(pattern)):
        assert len(ledger.read_text().splitlines()) == 1
        rows.append(audit_row(ledger, 1, GR / "eval_logs"))
assert len(rows) == 12
assert not any("scrapy__9a15fcf8" in p.read_text() for p in GR.glob("ledger_*.jsonl"))
p4 = ROOT / "runs/r2e_env_repair_20260924/p4"
old_row = audit_row(p4 / "ledger_overfix.jsonl", 1, p4 / "eval_logs", old=True)

devchecks = []
for key in KEYS:
    directory = next(DEV.glob("*__" + key + "*"))
    attempt = load(directory / "orig/attempt.json")
    gold = load(directory / "private_gold/private_control.json")
    commands = []
    for item in attempt["commands_result"]:
        capture = directory / "orig/captures" / (item["id"] + ".out")
        text = ANSI.sub("", capture.read_text())
        commands.append({
            "id": item["id"],
            "base_rc": item["rc"],
            "base_rc_expectation": item["expect"],
            "base_summary": [s for s in text.splitlines() if re.search(r"=+.*(?:passed|failed|deselected).*?=+", s)],
            "gold_rc": gold["results"].get(item["id"], {}).get("rc"),
            "capture": relative(capture),
            "capture_sha256": sha(capture),
        })
    env = (directory / "orig/captures/env.out").read_text()
    checks = {
        "base_is_agent": "uid=54321(agent)" in env,
        "python_is_testbed_venv": "RH2_SYS_EXECUTABLE=/testbed/.venv/bin/python" in env,
        "gold_is_explicit_private_root_control": "uid=0(root)" in gold["results"]["env"]["tail"],
        "same_image_base_gold_overlay": attempt["image"]
        == gold["image"] == attempt["overlay"]["derived_image_id"],
        "preflight_marker_values": (directory / "orig/captures/r2e_preflight.out").read_text().splitlines()
        == ["RH2_PREFLIGHT_INTERPRETER=ok", "RH2_PREFLIGHT_HIDDEN_TESTS=ok", "RH2_PREFLIGHT_GIT_HISTORY=ok"],
        "cleanup_no_residuals": not attempt["cleanup"]["labeled_containers_left"]
        and not attempt["cleanup"]["labeled_networks_left"]
        and not attempt["cleanup"]["residual_after_force"],
    }
    assert all(checks.values()), (key, checks)
    devchecks.append({
        "directory": relative(directory),
        "attempt_sha256": sha(directory / "orig/attempt.json"),
        "private_gold_sha256": sha(directory / "private_gold/private_control.json"),
        "cc_version": attempt["cc_version_observed"],
        "commands": commands,
        "checks": checks,
    })

report = {
    "scope": "本批三题12行；scrapy旧P4一行；四题已有devcheck；纯读取与重算，不是容器重跑",
    "material_checks": {key: value["checks"] for key, value in materials.items()},
    "current_batch_rows": rows,
    "scrapy_current_batch_row_count": 0,
    "scrapy_historical_p4": old_row,
    "devchecks": devchecks,
}
review_root = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_20260925"
review_docs = [review_root / name for name in ["README.md", "grader_candidates.md", "actor_devcheck.md"]]
for key in KEYS:
    task_dir = next((review_root / "results").glob("*__" + key + "*"))
    review_docs.extend(task_dir / name for name in ["card.md", "review.md", "screening_record.json"])
report["reviewed_document_hashes_at_audit"] = {relative(path): sha(path) for path in review_docs}
path = OUT / "evidence_audit.json"
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"current_batch_rows": len(rows), "old_scrapy_rows": 1,
                  "devchecks": len(devchecks), "all_assertions_passed": True,
                  "output": relative(path)}, ensure_ascii=False))
