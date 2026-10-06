"""cpu_slot 内串行编排冻结 runner 的原材料诊断；不登记修订或替代评分。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


RELEASE_SHA = "282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--instance-id", choices=("python__mypy-10174", "python__mypy-15184"), required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--candidates", default="noop,gold,bad")
    args = parser.parse_args()
    release = args.root / "releases/cat2-cpu-r2e064065-swe5-20261003-v1"
    assert hashlib.sha256((release / "manifest.json").read_bytes()).hexdigest() == RELEASE_SHA
    assert args.image_id.startswith("sha256:") and len(args.image_id) == 71
    source = release / "repo/rh2"
    python = args.root / "runtime_cpu_v2/rh2/.venv/bin/python"
    inputs = args.root / "packages/swe_mypy/input_v1"
    out = args.root / "packages/swe_mypy/attempts" / args.job
    out.mkdir(parents=True, exist_ok=False)
    state = {"instance_id": args.instance_id, "job": args.job, "state": "running",
             "scope": "原登记材料的私有CPU诊断；新题面/新增P2P未生效，不是新版本验收",
             "release_id": release.name, "release_manifest_sha256": RELEASE_SHA,
             "image_id": args.image_id, "steps": [], "started_at_utc": time.strftime(
                 "%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(source / "src")}

    def save() -> None:
        (out / "baseline_matrix.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    def interrupted(signum, _frame) -> None:
        raise KeyboardInterrupt(f"signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def run(name: str, argv: list[str], timeout: int = 4800) -> None:
        step = {"name": name, "command": [str(v) for v in argv], "started_at": time.time()}
        state["steps"].append(step)
        save()
        with (out / (name + ".log")).open("wb") as log:
            proc = subprocess.Popen(argv, cwd=source, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = proc.wait(timeout=timeout)
            except BaseException:
                if proc.poll() is None:
                    # asyncio 原入口接收 SIGINT 后取消并执行既有 finally 清理。
                    os.killpg(proc.pid, signal.SIGINT)
                    try:
                        proc.wait(timeout=300)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=30)
                        step["forced_kill"] = True
                step.update(returncode=proc.returncode, interrupted=True, finished_at=time.time())
                save()
                raise
        step.update(returncode=rc, finished_at=time.time())
        save()
        if rc:
            raise RuntimeError(f"{name}: rc={rc}; stop before next candidate")

    try:
        run("verify_release", [str(python), "-B", str(release / "verify_release.py")], 300)
        # 从受信 loader 核父材料；不使用上传草案替换准备产物。
        iid = args.instance_id
        original_public = json.loads((inputs / "original" / iid / "public/public_bundle.json").read_text())
        original_grading = json.loads((inputs / "original" / iid / "private/grading.json").read_text())
        canonical = lambda value: "sha256:" + hashlib.sha256(json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        readback = ("import json; from pathlib import Path; "
                    "from repoharness2.envpack.swe_material_revisions import load_trusted_swe_revision_outputs; "
                    f"r=load_trusted_swe_revision_outputs(Path({str(release / 'repo')!r})).result; "
                    f"p=next(p for p in r.public_bundles if p.instance_id=={iid!r}); "
                    f"g=next(g for g in r.grading_bundles if g.instance_id=={iid!r}); "
                    f"assert p.digest()=={canonical(original_public)!r}; "
                    f"assert g.digest()=={canonical(original_grading)!r}; "
                    "print(json.dumps({'public_digest':p.digest(),'grading_digest':g.digest(),'baseline_identity':'verified'}))")
        run("baseline_identity", [str(python), "-B", "-c", readback], 300)
        cli = source / "scripts/replay_grade.py"
        run("prepare", [str(python), "-B", str(cli), "prepare", "--repo-root", str(release / "repo"),
                        "--out-dir", str(out / "prepared"), "--private-dir", str(out / "private"),
                        "--task-ids", "swe_gym_lite::" + iid], 300)
        private = inputs / "proposals" / iid / "private"
        bad = private / ("disable_non_strict_comparisons.patch" if iid.endswith("10174")
                         else "gold_but_always_reject_assert_type.patch")
        gold = inputs / "original" / iid / "private/gold.patch"
        candidates = {"noop": "noop", "gold": "patch:" + str(gold), "bad": "patch:" + str(bad)}
        if iid.endswith("15184"):
            candidates["top_only"] = "patch:" + str(
                args.root / "packages/swe_mypy/private_calibration_v1/qualify_top_level_only.patch")
        selected = args.candidates.split(",")
        assert selected and len(set(selected)) == len(selected) and set(selected) <= candidates.keys()
        for name in selected:
            candidate = candidates[name]
            dest = out / name
            dest.mkdir()
            env["MILES_RH2_RUN_ID"] = "swe-mypy-" + args.job + "-" + name
            run(name, [str(python), "-B", str(cli), "run", "--prepared-summary",
                       str(out / "prepared/replay_summary.json"), "--task-ids", iid,
                       "--candidate", candidate, "--derived-image", args.image_id,
                       "--derived-image-recipe", "mypy-install-wave1-copy-wheels-20261003",
                       "--eval-log-dir", str(dest / "eval_logs"), "--artifacts-dir", str(dest / "artifacts"),
                       "--ledger", str(dest / "ledger.jsonl")])
            rows = [json.loads(line) for line in (dest / "ledger.jsonl").read_text().splitlines() if line]
            assert len(rows) == 1
            row = rows[0]
            assert row["cleanup"]["removed"] and row["stage_error"] is None
            assert row["image_id_actual"] == args.image_id
            state.setdefault("raw_results", {})[name] = {
                "report": row["report"], "reference": row["reference"],
                "install": row["install"], "cleanup": row["cleanup"],
                "evidence_requires_audit": True}
            save()
        state["state"] = "raw_matrix_completed_pending_audit"
        save()
    except BaseException as exc:
        state.update(state="stopped_pending_diagnosis", error=repr(exc))
        save()
        raise


if __name__ == "__main__":
    main()
