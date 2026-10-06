"""经固定 cpu_slot 调度的新正式 consumer 矩阵；不重写 recipe/profile/评分器。"""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, required=True)
    ap.add_argument("--release-manifest-sha256", required=True)
    ap.add_argument("--input-root", type=Path, required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--task-dir", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--attempt-id", required=True)
    ap.add_argument("--expected-grader-image-id", required=True)
    ap.add_argument("--expected-setup-seconds", type=int, required=True)
    ns = ap.parse_args()
    assert re.fullmatch(r"dask__dask-[0-9]+", ns.instance)
    assert sha(ns.release / "manifest.json") == ns.release_manifest_sha256
    ns.out.mkdir(parents=True, exist_ok=False)
    repo = ns.release / "repo"
    code = repo / "rh2"
    sys.path.insert(0, str(code / "src"))
    from repoharness2.adapters.slime.replay_grade import load_context
    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
    from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env, rollout_profile_from_env
    from repoharness2.envpack.swegym_parsers import lookup_parser

    task_id = "swe_gym_lite::" + ns.instance
    task_dir = ns.input_root / ns.task_dir
    revision = json.loads((task_dir / "revision.json").read_text())
    matrix = json.loads((task_dir / "acceptance_matrix.json").read_text())
    assert revision["revision_id"] == matrix["revision_id"]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(code / "src"),
           "RH2_GRADER_CPUS": "2", "RH2_GRADER_MEMORY_BYTES": str(4 * 1024**3)}
    state = {"schema": "dask_formal_matrix_attempt.v1", "scope": "fixed_published_consumer_nonroot_candidate_and_grader_matrix",
             "attempt_id": ns.attempt_id, "instance_id": ns.instance, "revision_id": revision["revision_id"],
             "release_manifest_sha256": ns.release_manifest_sha256, "input_matrix_sha256": sha(task_dir / "acceptance_matrix.json"),
             "input_revision_sha256": sha(task_dir / "revision.json"), "started_at": time.time(), "status": "running", "steps": [], "formal_rows": []}
    child = None

    def save():
        write(ns.out / "status.json", state)

    def stop(signum, frame):
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def run(name, command, run_id=None):
        nonlocal child
        step = {"name": name, "started_at": time.time(), "command": [str(x) for x in command]}
        state["steps"].append(step)
        save()
        process_env = {**env, **({"MILES_RH2_RUN_ID": run_id} if run_id else {})}
        with (ns.out / (name + ".log")).open("wb") as log:
            child = subprocess.Popen(step["command"], cwd=code, env=process_env, stdout=log, stderr=subprocess.STDOUT)
            rc = child.wait()
        child = None
        step.update(returncode=rc, finished_at=time.time())
        save()
        if rc or state.get("signal_received"):
            raise RuntimeError("driver_not_complete:" + name)

    try:
        run("verify_release", [sys.executable, "-B", ns.release / "verify_release.py"])
        run("prepare", [sys.executable, "-B", code / "scripts/replay_grade.py", "prepare", "--repo-root", repo,
                        "--out-dir", ns.out / "prepared", "--private-dir", ns.out / "private", "--sources", "swe_gym_lite", "--task-ids", task_id])
        summary = json.loads((ns.out / "prepared/replay_summary.json").read_text())
        assert summary["task_ids"] == [task_id]
        ctx = load_context(prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
                           manifest_sha256=summary["prepared_manifest_sha256"],
                           rollout_profile=rollout_profile_from_env(env, model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1),
                           grader_profile=grader_profile_from_env(env), artifacts_dir=ns.out / "binding_artifacts", run_id=ns.attempt_id + "-binding")
        view = ctx.grading_views[task_id]
        assert hashlib.sha256(view.grading.test_patch.encode()).hexdigest() == revision["effective_test_patch"]["sha256"]
        assert list(view.grading.fail_to_pass) == revision["effective_fail_to_pass"]
        assert list(view.grading.pass_to_pass) == revision["effective_pass_to_pass"]
        spec = build_grading_spec_from_host_view(view, image=revision["image"], image_manifest_digest=revision["image_manifest_digest"])
        if spec.image_local_build:
            assert spec.image_local_build_id == ns.expected_grader_image_id
        else:
            assert spec.image_manifest_digest == revision["image_manifest_digest"]
            inspected = subprocess.run(["docker", "image", "inspect", spec.image], check=True, capture_output=True, timeout=60)
            image_info = json.loads(inspected.stdout)
            assert len(image_info) == 1 and image_info[0]["Id"] == ns.expected_grader_image_id
            assert any(ref.endswith("@" + spec.image_manifest_digest) for ref in image_info[0].get("RepoDigests", []))
            (ns.out / "source_image_inspect.json").write_bytes(inspected.stdout)
        assert spec.env_reset_timeout_seconds == ns.expected_setup_seconds
        state["formal_binding"] = {"host_grading_view_json_sha256": hashlib.sha256(json.dumps(view.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                                   "host_grading_artifact_sha256": summary["host_grading_artifact_sha256"], "grading_bundle_digest": view.grading_bundle_digest,
                                   "environment_package_digest": view.environment_package_digest,
                                   "grading_materials_identity": spec.grading_materials_identity,
                                   "grading_revision": spec.grading_revision.diagnostics(None), "image_id": ns.expected_grader_image_id,
                                   "image_local_build": spec.image_local_build,
                                   "image_manifest_digest": spec.image_manifest_digest,
                                   "setup_seconds": spec.env_reset_timeout_seconds, "prepared_manifest_sha256": summary["prepared_manifest_sha256"]}
        write(ns.out / "formal_binding.json", state["formal_binding"])
        save()
        parser = lookup_parser("dask/dask")
        references = revision["effective_fail_to_pass"] + revision["effective_pass_to_pass"]
        for planned in matrix["rows"]:
            name = planned["name"]
            target = ns.out / name
            target.mkdir()
            patch = planned["patch"]
            if patch is None:
                candidate = "noop"
            else:
                path = ns.input_root / patch["path"]
                assert sha(path) == patch["sha256"]
                candidate = "patch:" + str(path)
            run("grade_" + name, [sys.executable, "-B", code / "scripts/replay_grade.py", "run",
                                 "--prepared-summary", ns.out / "prepared/replay_summary.json", "--task-ids", task_id,
                                 "--candidate", candidate, "--candidate-stage-seconds", "900", "--grading-deadline-seconds", "3600",
                                 "--eval-log-dir", target / "eval_logs", "--artifacts-dir", target / "artifacts", "--ledger", target / "ledger.jsonl"],
                ns.attempt_id + "-" + name)
            ledger = [json.loads(line) for line in (target / "ledger.jsonl").read_text().splitlines() if line.strip()]
            assert len(ledger) == 1
            row = ledger[0]
            assert row["candidate"]["apply_user"] == "agent/54321"
            if spec.image_local_build:
                assert row["image_id_actual"] == ns.expected_grader_image_id
            else:
                # 来源镜像的评分器核实际容器 RepoDigests；该分支不填派生镜像专用 config ID。
                assert row["image_id_actual"] is None
                assert row["image_identity"] == row["image_digest_expected"] == spec.image_manifest_digest
            assert row["image_local_build"] is spec.image_local_build
            assert row["grading_materials_identity"] == state["formal_binding"]["grading_materials_identity"]
            assert not row.get("stage_error") and row["cleanup"]["removed"] and row["reference_missing_count"] == 0
            assert row["test"]["segment_completed"] and row["test"]["rc"] in (0, 1)
            assert row["install"]["install_rc_last_command"] == 0
            log = Path(row["log"]["path"])
            assert sha(log) == row["log"]["sha256"].removeprefix("sha256:")
            text = log.read_text()
            assert text.count(">>>>> Start Test Output") == text.count(">>>>> End Test Output") == 1
            assert text.index(">>>>> Start Test Output") < text.index(">>>>> End Test Output")
            segment = text.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
            statuses = parser(segment)
            assert all(ref in statuses for ref in references)
            report = row["report"]
            assert report["reward"] in (0, 1) and not report.get("infra_failure_detail")
            expected = planned.get("expected_raw_behavior_score", planned.get("expected_reward"))
            assert expected in (0, 1), "矩阵原始分预期缺失；不得猜测或当语义分"
            observed = {"candidate": name, "formal_reward": report["reward"], "expected_reward": expected,
                        "references": {ref: statuses[ref] for ref in references}, "reference_missing": [],
                        "ledger_path": str(target / "ledger.jsonl"), "ledger_sha256": sha(target / "ledger.jsonl"),
                        "eval_log_sha256": sha(log), "image_id_actual": row["image_id_actual"], "cleanup": row["cleanup"],
                        "source_config_id_inspected": ns.expected_grader_image_id if not spec.image_local_build else None,
                        "image_identity": row["image_identity"],
                        "f2p_failed": [ref for ref in revision["effective_fail_to_pass"] if statuses[ref] not in ("PASSED", "XFAIL")],
                        "p2p_failed": [ref for ref in revision["effective_pass_to_pass"] if statuses[ref] not in ("PASSED", "XFAIL")]}
            state["formal_rows"].append(observed)
            save()
            assert observed["formal_reward"] == expected
            # 已知负对照可能专门触发新增P2P；逐参考保留，不把0当基础设施故障。
            if expected == 1:
                assert not observed["p2p_failed"]
            if "expected_failing_references" in planned:
                assert set(observed["f2p_failed"] + observed["p2p_failed"]) == set(planned["expected_failing_references"])
        state["status"] = "formal_matrix_complete_independent_review_pending"
    except BaseException as exc:
        state.update(status="stopped_needs_diagnosis", error=repr(exc))
        raise
    finally:
        state["finished_at"] = time.time()
        save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
