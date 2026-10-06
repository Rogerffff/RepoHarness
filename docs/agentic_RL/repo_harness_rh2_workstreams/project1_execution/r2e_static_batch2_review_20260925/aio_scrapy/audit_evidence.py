"""只读核对四题现有材料；不启动容器、不运行项目测试。

输出仅写入本脚本所在的独立审查目录。日志解析使用当前固定的 R2E 纯函数。
这不是新增 actor/grader 执行，也不把诊断命令退出码解释成语义正确。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import runpy


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "AGENTS.md").exists())
G = ROOT / "runs/r2e_actor_20260925/grader"
V = ROOT / "runs/r2e_static_prep_20260924/v3"
PARSER = runpy.run_path(str(ROOT / "rh2/src/repoharness2/envpack/r2e_parsers.py"))


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


rows = []
for p in sorted(G.glob("ledger_*.jsonl")):
    if not any(p.name.startswith("ledger_" + x) for x in ("a1c1c_", "a22a1_", "se938_", "s7545_")):
        continue
    for lineno, line in enumerate(p.read_text().splitlines(), 1):
        row = json.loads(line)
        iid = row["instance_id"]
        log = G / "eval_logs" / Path(row["log"]["path"]).name
        assert digest(log) == row["log"]["sha256"], p
        patch = None
        if row["candidate"]["kind"] == "gold":
            patch = V / "private" / iid / "gold.patch"
        elif row["candidate"]["kind"] != "noop":
            patch = ROOT / "runs/r2e_actor_20260925/grader_cands" / Path(row["candidate"]["origin"]).name
        if patch:
            assert digest(patch) == row["candidate"]["patch_sha256"], p
        text = log.read_text()
        observed = PARSER["normalize_status_map"](PARSER["parse_log_pytest"](text))
        expected = PARSER["normalize_status_map"](json.loads((V / "private" / iid / "expected_output.json").read_text()))
        mismatch = sorted(k for k in set(expected) | set(observed) if expected.get(k) != observed.get(k))
        matched = sum(observed.get(k) == v for k, v in expected.items())
        assert matched == row["report"]["expected_match"], p
        assert len(expected) == row["report"]["expected_total"], p
        assert set(mismatch) == set(row["verdict_diagnostics"]["expected_match"]["mismatched"]), p
        assert row["report"]["reward"] == float(not mismatch), p
        assert not row["candidate_touched_conftest_or_fixture"], p
        assert not row["log"]["partial"], p
        assert row["verdict_diagnostics"]["apply_ok"], p
        marks = dict(re.findall(r"RH2_TS_TEST_(START|END)=([0-9.]+)", text))
        rows.append({"ledger": rel(p), "line": lineno, "patch": rel(patch) if patch else None,
                     "patch_sha256": row["candidate"]["patch_sha256"], "log": rel(log),
                     "reward": row["report"]["reward"], "matched": matched, "total": len(expected),
                     "mismatch": mismatch, "test_interval": {k: float(v) for k, v in marks.items()},
                     "image": row["image_id_actual"]})

private = []
for p in sorted((G / "private_public_b2").glob("*.json")):
    if not any(p.name.startswith(x) for x in ("a22a1_", "se938_", "s7545_")):
        continue
    j = json.loads(p.read_text())
    if j["gold"] != "none":
        assert j["apply"].endswith("rc=0\n"), p
    for key, v in j["results"].items():
        assert not v["truncated"], p
        private.append({"artifact": rel(p), "command_id": key, "wrapper_rc": v["rc"],
                        "stdout": v["stdout"], "stderr": v["stderr"],
                        "note": "仅存现有观测；wrapper_rc 不是语义验收"})

postchecks = []
for p in sorted((G / "postcheck_b2").glob("a1c1c_*.json")):
    j = json.loads(p.read_text())
    if j.get("patch"):
        assert j["apply_rc"] == 0, p
    postchecks.append({"artifact": rel(p), "result": j["result"], "check_rc": j["check_rc"]})

raw_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
raw = json.loads(raw_path.read_text().splitlines()[5])
assert raw["commit_hash"] == "1c1c0ea353041c8814a6131c3a92978dc2373e52"
source = json.loads(raw["execution_result_content"])
historical = {}
for side in ("old", "new"):
    log = source[f"{side}_commit_res_stdout"]
    historical[side] = {
        "target_status": PARSER["parse_log_pytest"](log).get("TestShutdown.test_shutdown_handler_cancellation_suppressed"),
        "reason_lines": [s for s in log.splitlines() if ("Connect call failed" in s or "plugins:" in s)],
        "note": "来源记录与当前镜像的执行路径/插件不同；仅凭路径不判定是否裸机。",
    }

parallel = [x for x in rows if "gold_par" in x["ledger"]]
intersection = min(x["test_interval"]["END"] for x in parallel) - max(x["test_interval"]["START"] for x in parallel)
assert len(parallel) == 6 and intersection > 0

out = {"scope": "本机只读复算既有材料与纯解析函数，无新增项目/容器执行",
       "formal_rows": len(rows), "formal_identity_and_reparse_checks": "pass", "rows": rows,
       "six_gold_test_intervals_common_overlap_seconds": intersection,
       "private": private, "postchecks": postchecks, "historical_source": historical}
(HERE / "audit_evidence.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"formal_rows": len(rows), "identity_and_reparse": "pass",
                  "parallel_gold": len(parallel), "common_overlap_seconds": round(intersection, 3),
                  "private_command_results": len(private), "cleanup_postchecks": len(postchecks)}, ensure_ascii=False))
