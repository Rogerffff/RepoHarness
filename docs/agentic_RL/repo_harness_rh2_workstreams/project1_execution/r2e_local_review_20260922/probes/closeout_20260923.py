"""本机收尾窄复核：回读六份真实日志；对账工具两种可区分反例。不启动容器。

从仓库根运行：rh2/.venv/bin/python <本文件> > <新结果文件>
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))
spec = importlib.util.spec_from_file_location("r2e_reconcile_review", ROOT / "rh2/scripts/reconcile_r2e.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)
trusted = rc.load_trusted_r2e_ingest_outputs(ROOT)
gradings = {g.instance_id: g for g in trusted.result.grading_bundles}


def real_evidence():
    run = ROOT / "runs/r2e_local_rf_20260923"
    comparisons = json.loads((run / "reconcile/reconcile.json").read_text())
    by_key = {(x["instance_id"], x["kind"]): x for x in comparisons}
    rows = []
    for filename in ("ledger_noop.jsonl", "ledger_gold.jsonl"):
        for line in (run / filename).read_text().splitlines():
            row = json.loads(line)
            g = gradings[row["instance_id"]]
            log = Path(row["log"]["path"])
            assert "sha256:" + hashlib.sha256(log.read_bytes()).hexdigest() == row["log"]["sha256"]
            obs = rc.observed_from_rh2_log(log.read_text())
            expected = rc.normalize_status_map(g.expected_map())
            result = rc.scoring.expected_map_matches(expected, obs)
            report = row["report"]
            assert float(result.resolved) == report["reward"]
            assert (result.match_count, result.total_count) == (report["expected_match"], report["expected_total"])
            side = json.loads(Path(row["diagnostics_ref"]).read_text())
            # 第一份 coveragepy noop sidecar 来自字段扩充前；只回读，不回写旧证据。
            semantics = side["verdict"].get("grading_semantics")
            if semantics is not None:
                assert semantics == "r2e_expected_map"
            entry = by_key[(row["instance_id"], row["candidate"]["kind"])]
            refs = entry["reference_logs"]
            assert refs
            for path in refs:
                text = Path(path).read_text()
                assert obs == rc.normalize_status_map(rc.parse_log_pytest(text))
                assert rc.prime_calculate_reward(text, g.expected_output_json) == report["reward"]
            rows.append({"instance_id": g.instance_id, "kind": row["candidate"]["kind"],
                         "reward": report["reward"], "match": result.match_count, "total": result.total_count,
                         "reference_maps_equal": True, "reference_logs": len(refs), "log_sha256_matches": True,
                         "sidecar_has_new_verdict_fields": semantics is not None and "expected_match" in side["verdict"]})
    recipe = ROOT / "rh2/scripts/r2e_derive/recipe_v1.sh"
    builds = []
    for path in sorted((ROOT / "runs/r2e_derived_local_20260923").glob("*/facts.json")):
        data = json.loads(path.read_text())
        assert data["ok"] and not data["failures"] and all(x["ok"] for x in data["integrity"].values())
        assert data["recipe_sha256"] == "sha256:" + hashlib.sha256(recipe.read_bytes()).hexdigest()
        assert (path.parent / "context/recipe_v1.sh").read_bytes() == recipe.read_bytes()
        builds.append({"instance_id": path.parent.name, "ok": True,
                       "recorded_checks": len(data["integrity"]), "recipe_matches_current": True})
    assert len(rows) == 6 and len(builds) == 3
    return {"ledger_rows": rows, "builds": builds, "scope": "read-only reparse of prior real runs; no containers rerun"}


def counterexample(*, wrong_reference_ledger=False):
    g = next(g for g in gradings.values() if g.instance_id.startswith("aiohttp__240da100"))
    expected = rc.normalize_status_map(g.expected_map())
    key = next(k for k, v in expected.items() if v == "PASSED")
    a, b = dict(expected), dict(expected)
    a[key] = "FAILED"
    b[key] = "FAILED" if wrong_reference_ledger else "ERROR"

    def log(values):
        return "=== short test summary info ===\n" + "".join(f"{v} t.py::{k}\n" for k, v in values.items())

    with tempfile.TemporaryDirectory(prefix="r2e-reconcile-review-") as tmp:
        root = Path(tmp)
        ref = root / "M3/gold_ledger/logs_r2e" / g.repo / g.source_commit_hash[:12] / "gold/a1/test_output.txt"
        ref.parent.mkdir(parents=True)
        ref.write_text(log(b))
        rh2_log = root / "rh2.log"
        rh2_log.write_text(rc.scoring.R2E_EVAL_START_MARKER + "\n" + log(a) + "\n" + rc.scoring.R2E_EVAL_END_MARKER)
        (root / "M3/gold_ledger/r2e_gold_m3.jsonl").write_text(json.dumps({
            "commit_hash": g.source_commit_hash, "gate": "gold", "reward": 1.0 if wrong_reference_ledger else 0.0}) + "\n")
        ledger = root / "rh2.jsonl"
        ledger.write_text(json.dumps({"instance_id": g.instance_id, "candidate": {"kind": "gold"},
                                      "log": {"path": str(rh2_log)}, "report": {"reward": 0.0}}) + "\n")
        with contextlib.redirect_stdout(io.StringIO()):
            assert rc.main(["--repo-root", str(ROOT), "--ledger", str(ledger), "--m3-root", str(root / "M3"),
                            "--out", str(root / "out")]) == 0
        entry = json.loads((root / "out/reconcile.json").read_text())[0]
        comp = entry["comparisons"][0]
        assert entry["agree"] is True
        return {"case": "reference_ledger_reward_disagrees" if wrong_reference_ledger else "different_wrong_statuses",
                "rh2_status": a[key], "reference_status": b[key],
                "observed_maps_equal": comp["comparison"]["observed_maps_equal"],
                "sets_equal": comp["comparison"]["sets_equal"], "actual_agree": entry["agree"],
                "rh2_reward": 0.0, "reference_parsed_reward": comp["reference_prime_reward"],
                "reference_ledger_rewards": entry["m3_ledger_rewards"]}


if __name__ == "__main__":
    print(json.dumps({"real_evidence": real_evidence(), "reconcile_counterexamples": [counterexample(), counterexample(wrong_reference_ledger=True)]},
                     ensure_ascii=False, indent=2))
