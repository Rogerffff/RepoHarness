#!/usr/bin/env python3
"""在 cpu_slot 名额内串行调用冻结 replay_grade；不实现评分规则或模型探针。"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-root", type=Path, required=True)
    ap.add_argument("--release-sha256", required=True)
    ap.add_argument("--prepared-summary", type=Path, required=True)
    ap.add_argument("--overlays", type=Path, required=True)
    ap.add_argument("--inputs-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--expected-total", type=int, required=True)
    ap.add_argument("--run-prefix", required=True)
    ap.add_argument("--cases", help="只运行这些原矩阵行，逗号分隔；不改变候选或期望")
    ns = ap.parse_args()
    assert sha(ns.release_root / "manifest.json") == ns.release_sha256
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ns.run_prefix)
    assert not ns.out_dir.exists(), "必须使用全新输出目录"
    config_path = ns.inputs_dir / "execution_inputs_r6_v1.json"
    config = json.loads(config_path.read_text())
    iid = config["instance_id"]
    prepared = json.loads(ns.prepared_summary.read_text())
    assert "r2e_gym_subset::" + iid in prepared["task_ids"]
    rows = config["rows"]
    if ns.cases:
        names = ns.cases.split(",")
        assert len(names) == len(set(names))
        selected = {row["candidate"]: row for row in rows}
        rows = [selected[name] for name in names]
    for row in rows:
        name = row["candidate"]
        assert re.fullmatch(r"[A-Za-z0-9_-]+", name)
        if row["remote_candidate_rel"]:
            p = ns.inputs_dir / row["remote_candidate_rel"] / (iid + ".diff")
            assert sha(p) == row["patch_sha256"]

    repo = ns.release_root / "repo"
    entry = repo / "rh2/experiments/r2e_lifecycle_20260929/r2e_probe_e2e.py"
    spec = importlib.util.spec_from_file_location("frozen_e2e", entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ns.out_dir.mkdir(parents=True)
    label = "rh2.coveragepy=" + ns.run_prefix
    shim_dir = ns.out_dir / ".docker_label_shim"
    shim_dir.mkdir()
    shim = shim_dir / "docker"
    shim.write_text(module.SHIM.format(label=label, docker=module.REAL_DOCKER))
    shim.chmod(0o755)
    summary = {
        "schema_id": "coveragepy.formal_matrix_execution.v1",
        "instance_id": iid,
        "release_id": ns.release_root.name,
        "release_manifest_sha256": ns.release_sha256,
        "driver_sha256": sha(Path(__file__)),
        "frozen_e2e_helpers_sha256": sha(entry),
        "execution_inputs_sha256": sha(config_path),
        "prepared_summary": str(ns.prepared_summary),
        "prepared_summary_sha256": sha(ns.prepared_summary),
        "overlays": str(ns.overlays),
        "overlays_sha256": sha(ns.overlays),
        "expected_total": ns.expected_total,
        "label": label,
        "started_at_utc": module.now(),
        "status": "running",
        "rows": [],
    }

    def save():
        p = ns.out_dir / ".summary.json.tmp"
        p.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        p.replace(ns.out_dir / "summary.json")

    def residuals():
        result = {}
        for resource, command, fmt in [
            ("containers", [module.REAL_DOCKER, "ps", "-a"], "{{.Names}}"),
            ("networks", [module.REAL_DOCKER, "network", "ls"], "{{.Name}}"),
        ]:
            q = subprocess.run(
                command + ["--filter", "label=" + label, "--format", fmt],
                capture_output=True, text=True, timeout=60,
            )
            result[resource] = {"query_rc": q.returncode, "left": q.stdout.split()}
        return result

    save()
    for row in rows:
        name = row["candidate"]
        target = ns.out_dir / name
        target.mkdir()
        rid = ns.run_prefix + "-" + name
        candidate = (
            "patch-dir:" + str(ns.inputs_dir / row["remote_candidate_rel"])
            if row["remote_candidate_rel"] else "noop"
        )
        command = [
            sys.executable, str(repo / "rh2/scripts/replay_grade.py"), "run",
            "--prepared-summary", str(ns.prepared_summary), "--task-ids", iid,
            "--candidate", candidate, "--repeat", "1",
            "--eval-log-dir", str(target / "eval_logs"),
            "--artifacts-dir", str(target / "artifacts"),
            "--ledger", str(target / "ledger.jsonl"),
            "--image-overlays", str(ns.overlays),
        ]
        env = dict(os.environ)
        env.update({
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(repo / "rh2/src"),
            "PATH": str(shim_dir) + ":" + env.get("PATH", "/usr/bin:/bin"),
            "MILES_RH2_RUN_ID": rid,
        })
        started = time.monotonic()
        # 由正式 manager 的阶段时限和 finally/close 负责取消与清理；
        # 这里不另杀评分进程，不把外层退出替代实际测试状态。
        with (target / "grade.log").open("wb") as log:
            rc = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        ledger = module.last_row(target / "ledger.jsonl")
        report = ledger.get("report") or {}
        stop = module.grade_stop_reason(ledger, rc, module.driver_footer(target / "grade.log"))
        left = residuals()
        expected_mismatch = row.get("expected_only_mismatch")
        diagnostic = ledger.get("diagnostics_ref")
        actual_mismatch = None
        if diagnostic and Path(diagnostic).is_file():
            diagnostic_row = json.loads(Path(diagnostic).read_text())
            actual_mismatch = ((diagnostic_row.get("verdict") or {}).get("expected_match") or {}).get("mismatched")
        result = {
            "candidate": name, "patch_sha256": row["patch_sha256"],
            "expected_reward": row["expected_reward"], "actual_reward": report.get("reward"),
            "driver_rc": rc, "run_id": rid, "stop_reason": stop,
            "seconds": round(time.monotonic() - started, 2),
            "expected_only_mismatch": expected_mismatch, "actual_mismatch": actual_mismatch,
            "ledger": module.ledger_view(ledger), "residuals": left,
        }
        summary["rows"].append(result)
        clean = all(value["query_rc"] == 0 and not value["left"] for value in left.values())
        expected = (
            report.get("reward") == row["expected_reward"]
            and report.get("expected_total") == ns.expected_total
            and (expected_mismatch is None or sorted(actual_mismatch or []) == sorted(expected_mismatch))
        )
        print(json.dumps({key: result[key] for key in ["candidate", "driver_rc", "actual_reward", "actual_mismatch", "stop_reason"]}), flush=True)
        if stop or rc or not clean or not expected:
            summary.update(status="stopped_requires_investigation", finished_at_utc=module.now())
            save()
            return 4
        save()
    summary.update(status="matrix_passed", finished_at_utc=module.now())
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
