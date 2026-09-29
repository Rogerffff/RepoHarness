"""重放本批已完成日志，保留与原始 baseline01 的逐参考 ID 对照。"""

from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "rh2/src"))

from repoharness2.envpack.scoring import parse_eval_log_v2
from repoharness2.envpack.swegym_parsers import lookup_parser
from swebench.harness.constants import END_TEST_OUTPUT, START_TEST_OUTPUT

OLD = REPO / "runs/full216_rh2_diagnostic_20260919"
ROOT = REPO / "runs/env_recipe_repair_20260919"
REMOTE_ROOT = Path("/work/env_recipe_repair_20260919")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--batch", default="remote", help="本地证据子目录；remote为第一批，round2为第二批")
    cli.add_argument("--run-prefix", default="")
    cli.add_argument("--bindings", help="显式参考绑定JSON；不用于未修订的旧运行")
    args = cli.parse_args()
    batch = ROOT / args.batch
    remote = REMOTE_ROOT if args.batch == "remote" else REMOTE_ROOT / args.batch
    bindings = json.loads(Path(args.bindings).read_text()) if args.bindings else None
    # 本机正在与 Claude 共享：只允许用与原诊断相同的解析器重放。
    sources = json.loads((OLD / "source_snapshot.json").read_text())
    for source in sources:
        if source["path"] in (
            "rh2/src/repoharness2/envpack/scoring.py",
            "rh2/src/repoharness2/envpack/swegym_parsers.py",
        ):
            assert hashlib.sha256((REPO / source["path"]).read_bytes()).hexdigest() == source["sha256"]
    views = {
        row["instance_id"]: row["grading"]
        for row in map(json.loads, (OLD / "remote/replay/private/host_grading_views.jsonl").read_text().splitlines())
    }
    baseline = {
        (row["instance_id"], row["kind"]): row
        for row in map(json.loads, (OLD / "zero_audit/parsed_facts.jsonl").read_text().splitlines())
        if row["campaign"] == "baseline01"
    }
    result = []
    ledgers = sorted(batch.rglob("ledger.jsonl"))
    for ledger in ledgers:
        if args.run_prefix and not ledger.parent.name.startswith(args.run_prefix):
            continue
        rows = [json.loads(line) for line in ledger.read_text().splitlines()]
        assert len(rows) == 1
        row = rows[0]
        log = batch / Path(row["log"]["path"]).relative_to(remote)
        assert "sha256:" + hashlib.sha256(log.read_bytes()).hexdigest() == row["log"]["sha256"]
        text = log.read_text()
        grading = views[row["instance_id"]]
        spec = SimpleNamespace(**grading)
        parsed = parse_eval_log_v2(spec, text)
        uses_bindings = bool(bindings and "+reference-bindings-v1" in row["report"]["grader_version"])
        if uses_bindings:
            from reference_bindings import parse_bound
            parsed = parse_bound(spec, text, bindings["tasks"][row["instance_id"]]["bindings"])
        diagnostics = row["verdict_diagnostics"]
        if diagnostics is not None:
            assert parsed.num_parsed_tests == diagnostics["num_parsed_tests"]
            assert parsed.reference_missing == diagnostics["reference_missing"]
        else:
            # timeout/资源终止可在parser之前返回；重放部分日志不能冒充运行时评分结论。
            assert row["report"]["reward"] is None
        if row["report"]["reward"] is not None:
            assert row["report"]["f2p_pass"] == len(parsed.f2p_success)
            assert row["report"]["p2p_fail"] == len(parsed.p2p_failure)
        segment = text.split(START_TEST_OUTPUT, 1)[1].split(END_TEST_OUTPUT, 1)[0] if START_TEST_OUTPUT in text else ""
        states = lookup_parser(grading["repo_key_lower"])(segment)
        if uses_bindings:
            from reference_bindings import bound_states
            groups = bindings["tasks"][row["instance_id"]]["bindings"]
            corrected, _ = bound_states(segment, groups)
            for alias in groups:
                states.pop(alias, None)
            states.update(corrected)
        old = baseline.get((row["instance_id"], row["candidate"]["kind"]))
        reference = {
            bucket: [{"id": item, "status": states.get(item, "MISSING")} for item in grading[key]]
            for bucket, key in (("f2p", "fail_to_pass"), ("p2p", "pass_to_pass"))
        }
        changed = []
        for bucket, values in reference.items():
            if old is None:
                continue  # 人为安装canary不是原始gold，不自动套用gold对照。
            before = {item["id"]: item["status"] for item in old["reference"][bucket]}
            changed.extend(
                {"bucket": bucket, "id": item["id"], "before": before[item["id"]], "after": item["status"]}
                for item in values if before[item["id"]] != item["status"]
            )
        result.append({
            "run": str(ledger.parent.relative_to(batch)), "instance_id": row["instance_id"], "kind": row["candidate"]["kind"],
            "log": str(log.relative_to(REPO)), "sha256_verified": True,
            "runtime_parser_compared": diagnostics is not None,
            # 外部删容器可能留下log_partial=False；必须核对实际测试收口标记。
            "reference_completeness": "complete_log" if (
                not row["install"].get("log_partial")
                and row["install"].get("test_rc") is not None
                and END_TEST_OUTPUT in text
            ) else "unknown_partial_log",
            "before_report": old["report"] if old else None, "report": row["report"],
            "reference": reference, "reference_changes": changed,
            "reference_counts": {bucket: dict(Counter(item["status"] for item in values))
                                 for bucket, values in reference.items()},
            "parser_state_counts": dict(Counter(states.values())),
            "outside_reference_failures": [{"id": key, "status": value} for key, value in states.items()
                                           if key not in set(grading["fail_to_pass"] + grading["pass_to_pass"])
                                           and value in {"FAILED", "ERROR"}],
            "install_before": old["install"] if old else None, "install": row["install"],
            "pre_test_errors": [line for line in text.split(START_TEST_OUTPUT, 1)[0].splitlines()
                                if "ERROR:" in line],
            "pytest_summaries": re.findall(r"^=+ .*?\bin [0-9.]+s.*?=+$", segment, re.MULTILINE),
            "actual_failure_lines": re.findall(r"^(?:FAILED|ERROR) \S+.*$", segment, re.MULTILINE),
            "resource": row["resource"], "resource_facts": row.get("resource_facts"),
            "policy_matches_baseline": row["policy"] == old["policy"] if old else None,
            "policy": row["policy"],
            "cleanup": row["cleanup"], "stage_error": row["stage_error"],
        })
    dest = ROOT / f"analysis_{len(result)}.json" if args.batch == "remote" else batch / f"analysis_{len(result)}.json"
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"attempts": len(result), "output": str(dest),
                      "rows": [{"run": x["run"], "reference": x["reference_counts"],
                                "changed_reference_ids": len(x["reference_changes"]),
                                "summary": x["pytest_summaries"]} for x in result]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
