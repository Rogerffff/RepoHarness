"""只读复核 13 份材料提案的可信来源及既有日志；仅向本审查目录写产物。

从仓库根运行：python -B <本文件路径>
不运行 Docker、远端或候选，不改变 expected、摄入面、生产代码或原证据。
"""
from __future__ import annotations

import hashlib
import json
import re
import runpy
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
REPAIR = BASE / "project1_execution/r2e_env_repair_20260924"
RAW = BASE / "s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
PARSER = ROOT / "rh2/src/repoharness2/envpack/r2e_parsers.py"
RF = ROOT / "runs/r2e_rf_20260923/remote"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> None:
    assert (ROOT / "AGENTS.md").exists(), ROOT
    parser = runpy.run_path(str(PARSER))
    parse = parser["parse_log_pytest"]
    normalize = parser["normalize_status_map"]
    wanted = {p.stem for p in (REPAIR / "material_revisions").glob("*.md")}
    assert len(wanted) == 13
    indexed = {}
    for lineno, raw_line in enumerate(RAW.read_bytes().splitlines(), 1):
        row = json.loads(raw_line)
        iid = f"{row['repo_name']}__{row['commit_hash']}"
        if iid in wanted:
            indexed[iid] = (lineno, raw_line, row)
    ledgers = {}
    for candidate in ("noop", "gold"):
        path = RF / f"ledger_r2e_all_{candidate}.jsonl"
        ledgers[candidate] = {
            row["instance_id"]: (lineno, row)
            for lineno, line in enumerate(path.read_text().splitlines(), 1)
            for row in [json.loads(line)]
        }
    result = {
        "scope": "既有原始材料与日志的离线重算；不是候选执行或新环境复验",
        "raw_sha256": sha(RAW.read_bytes()),
        "parser_sha256": sha(PARSER.read_bytes()),
        "tasks": {},
    }
    for iid, (lineno, raw_line, row) in sorted(indexed.items()):
        expected = normalize(json.loads(row["expected_output_json"]))
        execution = json.loads(row["execution_result_content"])
        commit = json.loads(row["parsed_commit_content"])
        task = {
            "raw_ref": f"{relative(RAW)}:{lineno}",
            "raw_line_sha256": sha(raw_line),
            "expected_count": len(expected),
            "expected_non_passed": {k: v for k, v in expected.items() if v != "PASSED"},
            "source_new_equals_expected": normalize(parse(execution["new_commit_res_stdout"])) == expected,
            "runs": {},
        }
        for candidate in ("noop", "gold"):
            ledger_line, ledger = ledgers[candidate][iid]
            log = RF / "eval_logs_r2e" / Path(ledger["log"]["path"]).name
            log_bytes = log.read_bytes()
            log_text = log_bytes.decode()
            observed = normalize(parse(log_text))
            missing = sorted(expected.keys() - observed.keys())
            unexpected = sorted(observed.keys() - expected.keys())
            mismatched = sorted(k for k in expected.keys() & observed.keys() if expected[k] != observed[k])
            task["runs"][candidate] = {
                "ledger_ref": f"{relative(RF / f'ledger_r2e_all_{candidate}.jsonl')}:{ledger_line}",
                "log_ref": relative(log),
                "log_sha256": sha(log_bytes),
                "sha_matches_ledger": ledger["log"]["sha256"].removeprefix("sha256:") == sha(log_bytes),
                "observed_count": len(observed),
                "observed_status_counts": dict(Counter(observed.values())),
                "missing": missing, "unexpected": unexpected, "mismatched": mismatched,
                "resolved_recomputed": not (missing or unexpected or mismatched),
                "reward_recorded": ledger["report"]["reward"],
                "fixture_not_found_lines": [
                    {"line": n, "text": text.strip()}
                    for n, text in enumerate(log_text.splitlines(), 1)
                    if re.search(r"E\s+fixture '.+' not found", text)
                ],
            }
        if row["commit_hash"].startswith(("016af5f6", "58ba5165", "9b5494e2", "4ec87eb9", "2b061b68", "cfed9b66")):
            excerpt = OUT / "source_excerpts" / iid
            excerpt.mkdir(parents=True, exist_ok=True)
            (excerpt / "problem_statement.txt").write_text(row["problem_statement"])
            codes = dict(zip(execution["test_file_names"], execution["test_file_codes"]))
            for name, content in codes.items():
                assert Path(name).name == name
                (excerpt / (name + ".txt")).write_text(content)
            for fd in commit["file_diffs"]:
                name = fd.get("header", {}).get("file", {}).get("path", "")
                if name.endswith(".py"):
                    for kind in ("old", "new"):
                        content = fd.get(f"{kind}_file_content")
                        if isinstance(content, str):
                            (excerpt / f"{name.replace('/', '__')}.{kind}.txt").write_text(content)
            if row["commit_hash"].startswith("58ba5165"):
                docs = next(fd for fd in commit["file_diffs"] if fd["header"]["file"]["path"] == "datalad/interface/tests/test_docs.py")
                task["hidden_test2_equals_upstream_new_docs"] = codes["test_2.py"] == docs["new_file_content"]
                task["cmdline_demo_text_appears_in_public_prompt"] = "multiline cli-only with [ brackets\n[] ]" in row["problem_statement"]
        result["tasks"][iid] = task
    (OUT / "audit_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("材料数:", len(result["tasks"]))
    print("引用日志摘要全部相符:", all(r["sha_matches_ledger"] for t in result["tasks"].values() for r in t["runs"].values()))
    print("pandas ERROR 键数:", sum(len(t["expected_non_passed"]) for iid, t in result["tasks"].items() if iid.startswith("pandas__")))
    for iid, t in result["tasks"].items():
        counts = dict(Counter(t["expected_non_passed"].values()))
        print(iid, t["expected_count"], counts, "noop/gold=", t["runs"]["noop"]["resolved_recomputed"], t["runs"]["gold"]["resolved_recomputed"])


if __name__ == "__main__":
    main()
