"""将已绑定正式运行的可见诊断交给新鲜裁决者；仅诊断侧，不产训练reward。"""
import argparse
import hashlib
import json
from pathlib import Path

from config_diagnostic_protocol import combine_diagnostic_outcome, validate_packets
from validate_semantic_verdicts import read, validate


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def _prepare(ledger_path, log_path, expected_material_identity, config_path, prompt_path, out):
    result = {"schema": "dask8801_diagnostic_job.v1", "automatic_training_reward_authorized": False,
              "state": "needs_evidence", "expected_material_identity": expected_material_identity,
              "ledger_sha256": sha(ledger_path.read_bytes()), "eval_log_sha256": sha(log_path.read_bytes()),
              "judge_config_sha256": sha(config_path.read_bytes()), "judge_prompt_sha256": sha(prompt_path.read_bytes())}
    ledger_rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    assert len(ledger_rows) == 1, "必须绑定一份实际候选账本"
    row = ledger_rows[0]
    report, test, install = row.get("report") or {}, row.get("test") or {}, row.get("install") or {}
    complete = (not row.get("stage_error") and not report.get("infra_failure_detail")
                and row.get("grading_materials_identity") == expected_material_identity
                and row.get("candidate", {}).get("apply_user") == "agent/54321"
                and row.get("reference_missing_count") == 0
                and row.get("cleanup", {}).get("removed") is True
                and test.get("segment_completed") is True and test.get("rc") in (0, 1)
                and install.get("install_rc_last_command") == 0
                and row.get("log", {}).get("sha256", "").removeprefix("sha256:") == result["eval_log_sha256"])
    result.update(behavior_complete=bool(complete), raw_behavior_score=report.get("reward"), run_id=row.get("run_id"))
    config = json.loads(config_path.read_text())
    if config.get("prompt_sha256") != result["judge_prompt_sha256"]:
        result["issue"] = "fixed_judge_prompt_identity_mismatch"
    elif not complete or report.get("reward") not in (0, 1):
        result["issue"] = "formal_execution_or_identity_incomplete"
    elif report["reward"] == 0:
        result["state"] = "fail_behavior"
    else:
        text = log_path.read_text()
        if (text.count(">>>>> Start Test Output") != 1 or text.count(">>>>> End Test Output") != 1
                or text.find(">>>>> Start Test Output") >= text.find(">>>>> End Test Output")):
            result["issue"] = "test_segment_missing_or_duplicated"
        else:
            segment = text.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
            packets = validate_packets(segment, "full_import")
            result["capture_issues"] = packets["issues"]
            result["compatibility_branches"] = packets["compatibility_branches"]
            if packets["state"] == "complete":
                inputs, bindings = [], []
                for item in packets["inputs"]:
                    payload = item["semantic_judge_input"]
                    payload_sha = sha(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())
                    key = sha(json.dumps([expected_material_identity, result["ledger_sha256"], result["eval_log_sha256"],
                                          result["judge_config_sha256"], result["judge_prompt_sha256"], payload_sha]).encode())
                    inputs.append({"id": "r" + key, "semantic_judge_input": payload})
                    bindings.append({"case_id": item["case_id"], "id": "r" + key, "payload_sha256": payload_sha, "cache_key": key})
                write(out / "judge_inputs.json", {"schema": "dask8801_semantic_inputs.v1", "inputs": inputs})
                write(out / "private_run_binding.json", {"bindings": bindings, "candidate_patch_sha256": row["candidate"].get("patch_sha256")})
                result.update(state="awaiting_independent_semantic_judge", required_results=len(inputs),
                              judge_inputs_sha256=sha((out / "judge_inputs.json").read_bytes()))
    write(out / "job.json", result)
    return result


def prepare(ledger_path, log_path, expected_material_identity, config_path, prompt_path, out):
    out.mkdir(parents=True, exist_ok=False)
    try:
        return _prepare(ledger_path, log_path, expected_material_identity, config_path, prompt_path, out)
    except (OSError, ValueError, RecursionError, TypeError, AttributeError, KeyError, AssertionError) as exc:
        result = {"schema": "dask8801_diagnostic_job.v1", "state": "needs_evidence", "automatic_training_reward_authorized": False,
                  "expected_material_identity": expected_material_identity, "issue": "host_artifact_input_error:" + type(exc).__name__}
        write(out / "job.json", result)
        return result


def finish(out, verdict_path):
    job = read(out / "job.json")
    if not isinstance(job, dict) or not isinstance(job.get("state"), str):
        final = {"schema": "dask8801_diagnostic_job.v1", "state": "needs_evidence", "automatic_training_reward_authorized": False,
                 "issue": "job_artifact_missing_or_invalid"}
        out.mkdir(parents=True, exist_ok=True)
        path = out / "diagnostic_outcome.json"
        if path.exists():
            raise ValueError("已有诊断原件不得覆盖")
        write(path, final)
        return final
    if job.get("state") != "awaiting_independent_semantic_judge":
        return job
    if (job.get("behavior_complete") is not True or job.get("raw_behavior_score") != 1
            or type(job.get("required_results")) is not int or not 13 <= job["required_results"] <= 23):
        final = {**job, "state": "needs_evidence", "issue": "awaiting_job_metadata_missing_or_invalid"}
        path = out / "diagnostic_outcome.json"
        if path.exists():
            raise ValueError("已有诊断原件不得覆盖")
        write(path, final)
        return final
    inputs_path = out / "judge_inputs.json"
    try:
        identity_matches = sha(inputs_path.read_bytes()) == job.get("judge_inputs_sha256")
    except OSError:
        identity_matches = False
    if not identity_matches:
        final = {**job, "state": "needs_evidence", "issue": "judge_input_identity_changed"}
    else:
        input_artifact = read(inputs_path)
        inputs = input_artifact.get("inputs", []) if isinstance(input_artifact, dict) else None
        validation = validate(inputs, read(verdict_path))
        state = combine_diagnostic_outcome(behavior_complete=job["behavior_complete"], raw_behavior_score=job["raw_behavior_score"],
                                           packets_complete=True, verdicts=[r.get("verdict") for r in validation["results"].values()],
                                           judge_error=None if validation["state"] == "complete" else validation["issues"])
        if validation["state"] == "needs_evidence" or not isinstance(inputs, list) or len(inputs) != job.get("required_results"):
            state = "needs_evidence"
        final = {**job, "state": state, "semantic_output_validation": validation["state"], "semantic_output_issues": validation["issues"],
                 "verdict_sha256": sha(verdict_path.read_bytes()) if verdict_path.exists() else None,
                 "semantic_verdicts": validation["results"]}
    path = out / "diagnostic_outcome.json"
    if path.exists():
        raise ValueError("已有诊断原件不得覆盖；新复核另存新版本")
    write(path, final)
    return final


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="action", required=True)
    p = sub.add_parser("prepare")
    for name in ("ledger", "log", "config", "prompt", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--formal-materials-identity", required=True)
    f = sub.add_parser("finish")
    f.add_argument("--out", type=Path, required=True)
    f.add_argument("--verdict", type=Path, required=True)
    ns = ap.parse_args()
    result = prepare(ns.ledger, ns.log, ns.formal_materials_identity, ns.config, ns.prompt, ns.out) if ns.action == "prepare" else finish(ns.out, ns.verdict)
    print(json.dumps({k: result.get(k) for k in ("state", "raw_behavior_score", "required_results", "issue")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
