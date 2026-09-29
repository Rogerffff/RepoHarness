# Derived from analyze_results.py SHA256 472bb0c4391afdb410dcf6f9a8e36a25ce95f75275e8aa4d9e73f1c8f876041a; only private view path is now explicit.
"""用本批冻结 parser 重读已结束的真实评分；不替代逐题行为归因。"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code-root", required=True)
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bindings")
    ap.add_argument("--private-views", required=True, help="相对evidence-root的实际host grading视图")
    ns = ap.parse_args()
    code = Path(ns.code_root).resolve()
    root = Path(ns.evidence_root).resolve()
    sys.path.insert(0, str(code / "src"))
    sys.path.insert(1, str(code / "experiments/env_recipe_repair_20260919"))
    from repoharness2.envpack.scoring import parse_eval_log_v2
    from repoharness2.envpack.swegym_parsers import lookup_parser
    from swebench.harness.constants import END_TEST_OUTPUT, START_TEST_OUTPUT

    views = {d["instance_id"]: d["grading"] for d in map(json.loads,
             (root / ns.private_views).read_text().splitlines())}
    bindings = json.loads(Path(ns.bindings).read_text()) if ns.bindings else None
    run = root / "results" / ns.task / ns.run
    records = []
    for ledger in sorted(run.rglob("ledger.jsonl")):
        rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
        for row in rows:
            item = {"run": str(ledger.parent.relative_to(root)), "instance_id": row["instance_id"],
                    "candidate": row["candidate"], "report": row.get("report"), "stage_error": row.get("stage_error"),
                    "cleanup": row.get("cleanup"), "install": row.get("install"),
                    "resource_facts": row.get("resource_facts"), "resource": row.get("resource"),
                    "policy": row.get("policy")}
            records.append(item)
            if not row.get("log", {}).get("path"):
                item["log_missing"] = True
                continue
            path = root / Path(row["log"]["path"]).relative_to("/work/swegym_cpu_preprobe_20260929")
            content = path.read_bytes()
            assert "sha256:" + hashlib.sha256(content).hexdigest() == row["log"]["sha256"], path
            text = content.decode(errors="replace")
            item.update(log=str(path), log_sha256_verified=True)
            grading = views[row["instance_id"]]
            spec = SimpleNamespace(**grading)
            parsed = parse_eval_log_v2(spec, text)
            version = (row.get("report") or {}).get("grader_version", "")
            uses_bindings = "+reference-bindings-v1" in version
            if uses_bindings:
                if bindings is None:
                    raise ValueError("bound grading requires explicit --bindings input")
                from reference_bindings import parse_bound, bound_states
                groups = bindings["tasks"][row["instance_id"]]["bindings"]
                parsed = parse_bound(spec, text, groups)
            segment = text.split(START_TEST_OUTPUT, 1)[1].split(END_TEST_OUTPUT, 1)[0] if START_TEST_OUTPUT in text else ""
            states = lookup_parser(grading["repo_key_lower"])(segment)
            if uses_bindings:
                corrected, _ = bound_states(segment, groups)
                for alias in groups:
                    states.pop(alias, None)
                states.update(corrected)
            diagnostics = row.get("verdict_diagnostics")
            if diagnostics is not None:
                assert parsed.num_parsed_tests == diagnostics["num_parsed_tests"], ledger
                assert parsed.reference_missing == diagnostics["reference_missing"], ledger
            if (row.get("report") or {}).get("reward") is not None:
                assert row["report"]["f2p_pass"] == len(parsed.f2p_success), ledger
                assert row["report"]["p2p_fail"] == len(parsed.p2p_failure), ledger
            reference = {key: [{"id": test, "status": states.get(test, "MISSING")} for test in grading[field]]
                         for key, field in (("f2p", "fail_to_pass"), ("p2p", "pass_to_pass"))}
            keys = set(grading["fail_to_pass"] + grading["pass_to_pass"])
            item.update(reference=reference,
                        reference_counts={k: dict(Counter(x["status"] for x in v)) for k, v in reference.items()},
                        parser_state_counts=dict(Counter(states.values())),
                        outside_reference_failures=[{"id": k, "status": v} for k, v in states.items()
                                                    if k not in keys and v in {"FAILED", "ERROR"}],
                        actual_failure_lines=re.findall(r"^(?:FAILED|ERROR) \S+.*$", segment, re.MULTILINE),
                        pytest_summaries=re.findall(r"^.*?\b(?:passed|failed|error|skipped|deselected)\b.*?\bin [0-9.]+s.*$", segment, re.MULTILINE),
                        terminal_count_lines=re.findall(r"^\s*\d+ (?:passed|failed|skipped|xfailed|xpassed|errors?|deselected)\b.*$", segment, re.MULTILINE),
                        complete_test_log=(END_TEST_OUTPUT in text and (row.get("install") or {}).get("test_rc") is not None
                                           and not (row.get("install") or {}).get("log_partial", True)),
                        pretest_errors=[line for line in text.split(START_TEST_OUTPUT, 1)[0].splitlines() if "ERROR:" in line])
    dest = Path(ns.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    artifact = {"task": ns.task, "run": ns.run, "code_root": str(code),
                "parser_sha256": {str(p.relative_to(code)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                  (code / "src/repoharness2/envpack/scoring.py", code / "src/repoharness2/envpack/swegym_parsers.py")},
                "rows": records}
    dest.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps([{k: r.get(k) for k in ("run", "report", "reference_counts", "install", "complete_test_log", "pytest_summaries", "stage_error")}
                      for r in records], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
