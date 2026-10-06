"""原镜像下的真实公开 actor 和私有测试诊断；不是修订正式评分。

调用冻结的 trusted prepare、devcheck 和 private_behavior，不改它们。
私有新测试只进入后者的独立容器，actor 只收到原公开题面和公开命令。
外层必须经 cpu_slot.py --mode run；所有产物写到本包新 attempt 目录。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def text_blocks(content) -> list[str]:
    if isinstance(content, str):
        return [content]
    return [block["text"] for block in content if isinstance(block, dict) and block.get("type") == "text"] if isinstance(content, list) else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-manifest-sha256", required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--image-readback", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--candidate-name", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--cc-tarball", type=Path, required=True)
    parser.add_argument("--stub-host", default="172.17.0.1")
    parser.add_argument("--stub-port", type=int, default=18191)
    ns = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{5,78}", ns.attempt_id)
    assert sha(ns.release / "manifest.json") == ns.release_manifest_sha256
    ns.out.mkdir(parents=True, exist_ok=False)
    assert re.fullmatch(r"dask__dask-\d+", ns.instance_id)
    task_id = "swe_gym_lite::" + ns.instance_id
    repo = ns.release / "repo"
    rh2 = repo / "rh2"
    task_dir = ns.input_root / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work/swe_dask/tasks" / ns.instance_id
    revision = json.loads((task_dir / "revision.json").read_text())
    public = json.loads((ns.input_root / "runs/swegym_quality_expansion_20260925/public" / ns.instance_id / "public_bundle.json").read_text())
    matrix = json.loads((task_dir / "acceptance_matrix.json").read_text())
    assert len(set(ns.candidate_name)) == len(ns.candidate_name)
    assert set(ns.candidate_name) <= {row["name"] for row in matrix["rows"]}
    selected_rows = [row for row in matrix["rows"] if row["name"] in ns.candidate_name]
    assert sha(ns.input_root / revision["effective_test_patch"]["path"]) == revision["effective_test_patch"]["sha256"]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(rh2 / "src"),
           "SLIME_AGENT_CC_PLATFORM_TARBALL": str(ns.cc_tarball),
           "RH2_BRINGUP_ARTIFACT_DIR": str(ns.out / "actor/bringup_artifacts")}
    sys.path.insert(0, str(rh2 / "src"))
    from repoharness2.envpack.ingest_swegym_lite import load_trusted_ingest_outputs
    from repoharness2.envpack.swegym_parsers import lookup_parser

    trusted = load_trusted_ingest_outputs(repo)
    parent_public = next(p for p in trusted.result.public_bundles if p.instance_id == ns.instance_id)
    assert parent_public.model_dump(mode="json") == public
    assert parent_public.digest() == revision["trusted_parent_identity"]["public_bundle_digest"]
    image_state = json.loads((ns.image_readback / "status.json").read_text())
    assert image_state["status"] == "base_image_pulled_and_clean_checkout_verified" and not image_state["cleanup"]["residual"]
    image = json.loads((ns.image_readback / "image.json").read_text())
    assert image["instance_id"] == ns.instance_id and image["base_commit"] == public["base_commit"]
    assert image["public_bundle_digest"] == parent_public.digest() and image["dependency_changes"] == []
    assert image["pinned_image"] in image["repo_digests"]
    assert image["pinned_image"].endswith("@" + public["image_manifest_digest"])
    assert image["initial_worktree"] == "HEAD=" + public["base_commit"] + "\nPORCELAIN_BEGIN\nPORCELAIN_RC=0\n"
    state = {"scope": "actual_actor_and_private_root_diagnostic_not_formal_revision_score", "attempt_id": ns.attempt_id,
             "revision_id": revision["revision_id"], "effective_test_patch_sha256": revision["effective_test_patch"]["sha256"],
             "release_manifest_sha256": ns.release_manifest_sha256, "actor_image_id": image["image_id"],
             "base_image_id": image["image_id"], "started_at": time.time(), "status": "running", "steps": [], "private_rows": [], "private_candidate_selection": ns.candidate_name}
    child = None

    def save() -> None:
        write_json(ns.out / "status.json", state)

    def stop(signum, _frame):
        state["signal_received"] = signum
        save()
        if child is not None and child.poll() is None:
            child.send_signal(signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def run(name: str, command: list) -> None:
        nonlocal child
        step = {"name": name, "started_at": time.time(), "command": list(map(str, command))}
        state["steps"].append(step)
        save()
        with (ns.out / (name + ".log")).open("wb") as log:
            child = subprocess.Popen(list(map(str, command)), stdout=log, stderr=subprocess.STDOUT, env=env)
            rc = child.wait()
        child = None
        step.update(returncode=rc, finished_at=time.time())
        save()
        if rc or state.get("signal_received"):
            raise RuntimeError(f"{name} 未正常完成；停止并保留输出")

    try:
        run("verify_release", [sys.executable, "-B", ns.release / "verify_release.py"])
        run("prepare_original_materials", [sys.executable, "-B", rh2 / "scripts/replay_grade.py", "prepare", "--repo-root", repo,
             "--out-dir", ns.out / "prepared", "--private-dir", ns.out / "original_private", "--sources", "swe_gym_lite", "--task-ids", task_id])
        commands = json.loads((task_dir / "public_actor_commands_20261003.json").read_text())
        write_json(ns.out / "public_actor_commands.json", commands)
        prompt = public["public_hints"] + "\n\n" + public["problem_statement"]
        (ns.out / "public_actor_prompt.txt").write_text(prompt)
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex((ns.stub_host, ns.stub_port)) != 0, "预留桩端口已被监听；不终止其它进程"
        run("actor", [sys.executable, "-B", rh2 / "experiments/task2_swegym_dev_20260925/devcheck.py",
             "--prepared-summary", ns.out / "prepared/replay_summary.json", "--task", task_id,
             "--commands", ns.out / "public_actor_commands.json", "--image", image["image_id"], "--out-dir", ns.out / "actor",
             "--attempt-id", ns.attempt_id + "-actor", "--stub-host", ns.stub_host, "--stub-port", str(ns.stub_port), "--wall-seconds", "1800", "--prompt", prompt])
        actual = json.loads((ns.out / "actor/attempt.json").read_text())
        assert actual.get("harness_exit_code") == 0 and not actual.get("cleanup", {}).get("residual_after_force")
        observations = actual.get("commands_result") or []
        assert len(observations) == len(commands)
        for expected, observed in zip(commands, observations):
            assert observed["id"] == expected["id"] and observed["status"] != "not_run"
            if expected["expect"] == "zero":
                assert observed["rc"] == 0
            elif expected["expect"] == "nonzero":
                assert observed["rc"] not in (0, 124, 137, None)
            else:
                assert expected["expect"] == "any" and observed["rc"] not in (124, 137, None)
        assert actual["effective_profile"]["cpus"] == 2 and actual["effective_profile"]["memory_bytes"] == 4 * 1024**3
        initial_worktree = actual["image_facts"]["initial_worktree"]
        assert initial_worktree == "HEAD=" + public["base_commit"] + "\nPORCELAIN_BEGIN\nPORCELAIN_RC=0\n"
        state["public_commands_result"] = observations
        first = json.loads((ns.out / "actor/stub/requests/messages_000.json").read_text())
        user_texts = [s for message in first["messages"] if message.get("role") == "user" for s in text_blocks(message.get("content"))]
        exact = any(public["problem_statement"] in s for s in user_texts)
        normalized = any(public["problem_statement"].replace("\r\n", "\n") in s.replace("\r\n", "\n") for s in user_texts)
        state["actual_public_prompt"] = {"statement_exact_match": exact, "statement_normalized_newlines_match": normalized,
             "original_problem_statement_sha256": public["problem_statement_sha256"], "first_request_sha256": sha(ns.out / "actor/stub/requests/messages_000.json"),
             "model_inference": "scripted_stub_no_baseline_model"}
        assert normalized
        read_statuses = lookup_parser("dask/dask")
        for row in selected_rows:
            name = row["name"]
            files = {"effective_test.patch": str(ns.input_root / revision["effective_test_patch"]["path"])}
            steps = []
            if row["patch"] is not None:
                path = ns.input_root / row["patch"]["path"]
                assert sha(path) == row["patch"]["sha256"]
                files["candidate.patch"] = str(path)
                steps.append("git apply --check /in/candidate.patch && git apply /in/candidate.patch")
            steps.append("git apply --check /in/effective_test.patch && git apply /in/effective_test.patch")
            test_file = revision["effective_test_file"]["repository_path"]
            assert test_file.startswith("dask/") and ".." not in Path(test_file).parts
            command = f"printf '%s\\n' '>>>>> Start Test Output'; python -m pytest -p no:cacheprovider -n0 -rA --color=no {shlex.quote(test_file)}; rc=$?; printf '%s\\n' '>>>>> End Test Output'; exit \"$rc\""
            spec = {"image": image["image_id"], "python_prefix": "/opt/miniconda3/envs/testbed", "memory": "4g", "cpus": 2,
                    "variants": {name: steps}, "files": files, "commands": [{"id": "revised_test_file", "cmd": command, "timeout_s": 600}]}
            spec_file = ns.out / ("private_spec_" + name + ".json")
            write_json(spec_file, spec)
            private_out = ns.out / "private" / name
            run("private_" + name, [sys.executable, "-B", rh2 / "experiments/swegym_cpu_preprobe_20260929/private_behavior.py", spec_file, "--out", private_out])
            fact = json.loads((private_out / "summary.json").read_text())["variants"][name]
            assert not fact["cleanup"]["remaining"] and fact["cleanup"]["query_rc"] == 0 and fact["cleanup"]["rm_rc"] == 0
            initial_lines = (private_out / name / "initial.txt").read_text().splitlines()
            assert "uid=0(root)" in initial_lines[0] and initial_lines[1:] == [public["base_commit"]]
            observed_log = private_out / name / "revised_test_file.out"
            log = observed_log.read_text()
            assert log.count(">>>>> Start Test Output") == 1 and log.count(">>>>> End Test Output") == 1
            segment = log.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
            observed_map = read_statuses(segment)
            references = revision["effective_fail_to_pass"] + revision["effective_pass_to_pass"]
            missing = [n for n in references if n not in observed_map]
            failures = [n for n in references if observed_map.get(n) not in ("PASSED", "XFAIL")]
            result = {"candidate": name, "scope": "private_root_test_diagnostic", "observed_log_sha256": sha(observed_log),
                 "references": {n: observed_map.get(n) for n in references}, "reference_missing": missing,
                 "f2p_failed": [n for n in revision["effective_fail_to_pass"] if n in failures],
                 "p2p_failed": [n for n in revision["effective_pass_to_pass"] if n in failures],
                 "test_rc": fact["commands"][0]["rc"], "private_reference_contract_satisfied": not missing and not failures,
                 "formal_reward": None, "cleanup": fact["cleanup"]}
            state["private_rows"].append(result)
            save()
            assert not missing and not result["p2p_failed"] and result["test_rc"] in (0, 1)
            assert result["private_reference_contract_satisfied"] == bool(row["expected_reward"])
        state["status"] = "actor_and_private_diagnostic_complete_formal_publication_pending"
    except BaseException as exc:
        state.update(status="stopped_needs_diagnosis", error=repr(exc))
        raise
    finally:
        state["finished_at"] = time.time()
        save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
