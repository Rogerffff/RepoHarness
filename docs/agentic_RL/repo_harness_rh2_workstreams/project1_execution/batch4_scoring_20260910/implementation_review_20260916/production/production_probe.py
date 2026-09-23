"""独立生产路径探针；仅 CPU 与 Docker 替身，不连接真实 Docker/SSH/API。"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

REPO = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
OUT = Path(__file__).resolve().parent
for p in (REPO / "rh2/src", REPO / "rh2/tests", REPO / "rh2/tests/grading", REPO / "rh2/tests/adapters"):
    sys.path.insert(0, str(p))

from grading_fixtures import ExecResult
from sandbox_test_support import make_grader_profile
from test_batch4_pa_transport import _pa_task
from test_slime_generate import SAMPLING_PARAMS, _Args
from test_w3a_formal_grading_freeze import BASE_COMMIT, _formal_chain, make_barrier
from test_w3b_grader_profile_unit import ProfileGraderFakeDocker, _PA_COLLECTION_FAIL_SEGMENT, _pa_log
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager, render_compile_probe_script
from repoharness2.governance.admission import AdmissionPayloadV1, DispositionPolicy, decide_member_disposition


def local_compile(work: Path, paths: list[str]) -> dict:
    script = render_compile_probe_script(paths, env_lines=["#!/bin/bash", f"cd {shlex.quote(str(work))}"])
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", ""))
    proc = subprocess.run(["bash"], input=script, text=True, capture_output=True, env=env, timeout=20)
    return {"exit_code": proc.returncode, "stdout": proc.stdout.replace(sys.executable, "/python-under-review"),
            "stderr": proc.stderr.replace(sys.executable, "/python-under-review"),
            "script": script.replace(str(work), "<temporary-workspace>")}


async def formal_case(name: str, log: str, compile_out: str, *, paths: dict[str, bytes] | None = None,
                      unknown_resource: bool = False, qualified: bool = True) -> dict:
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    docker.compile_probe_stdout = compile_out

    async def controlled_docker(*args, input_bytes=None):
        if unknown_resource and ((args[0] == "exec" and "memory.events" in args[-1]) or
                                 (args[0] == "inspect" and "{{.State.OOMKilled}}" in args)):
            docker.calls.append(args)
            return ExecResult(1, "", "resource observation unavailable")
        return await docker(*args, input_bytes=input_bytes)

    log_storage = tempfile.TemporaryDirectory(prefix="rh2-production-logs-")
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=Path(log_storage.name)),
        docker=controlled_docker,
    )
    chain = _formal_chain(barrier=make_barrier(paths or {"src/thing.py": b"def feature(:\n"}), task=_pa_task(qualified=qualified))
    submissions = []

    async def submit(**kw):
        submissions.append({"workspace_none": kw["workspace"] is None, "frozen_delta_present": kw.get("frozen_delta") is not None,
                            "deadline_present": kw.get("deadline_monotonic") is not None})
        return await manager.grade(**kw)

    chain.orchestrator._grading_submit = submit
    leaves = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    report = audit.finalized.grading_report
    payload = AdmissionPayloadV1.model_validate(leaves[0].metadata["rh2_admission"])
    disposition = decide_member_disposition(payload, policy=DispositionPolicy())
    diag = manager.container_records[-1].diagnostics
    assert all(record.removed for record in manager.container_records)
    result = {"report": report.model_dump(mode="json"), "decision": diag["execution_failure_decision"],
            "outcome": audit.outcome_v2, "clean_grading": audit.finalized.eligibility_report.facts.clean_grading.model_dump(mode="json"),
            "member_disposition": dataclasses.asdict(disposition), "leaves": [{"reward": leaf.reward, "remove_sample": leaf.remove_sample} for leaf in leaves],
            "submissions": submissions, "grader_removed": len(docker.removed), "receipt_count": len(chain.finalization.receipts)}
    log_storage.cleanup()
    return result


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


async def main() -> None:
    result = {"scope": "本机 CPU / 真实 orchestrator + manager + finalization + gate + admission；Docker 为维护测试替身"}
    good_error = "RH2_COMPILE_INTERPRETER=/opt/miniconda3/envs/testbed/bin/python\nRH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    log = _pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2)
    result["positive_control"] = await formal_case("positive_control", log, good_error)
    result["no_qualification_control"] = await formal_case("no_qualification_control", log, good_error, qualified=False)
    result["resource_unknown"] = await formal_case("resource_unknown", log, good_error, unknown_resource=True)
    result["resource_and_rc_unknown"] = await formal_case("resource_and_rc_unknown", log.replace("RH2_TEST_RC=2\n", ""), good_error, unknown_resource=True)

    with tempfile.TemporaryDirectory(prefix="rh2-production-probe-") as tmp:
        work = Path(tmp)
        (work / "src").mkdir()
        (work / "src/thing.py").write_text("value = 1\n")
        clean = local_compile(work, ["src/thing.py"])
        (work / "json.py").write_text(
            "open('candidate_json_executed', 'w').write('yes')\n"
            "print('RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:synthetic-from-local-json')\n"
            "def loads(value):\n    return ['src/thing.py']\n"
        )
        shadow = local_compile(work, ["src/thing.py", "json.py"])
        shadow["candidate_module_executed"] = (work / "candidate_json_executed").exists()
        shadow["target_source_is_syntax_valid"] = compile((work / "src/thing.py").read_bytes(), "src/thing.py", "exec") is not None
        result["compile_local_clean"] = clean
        result["compile_local_json_shadow"] = shadow
        result["json_shadow_transport"] = await formal_case("json_shadow_transport", log, shadow["stdout"],
            paths={"src/thing.py": b"value = 1\n", "json.py": (work / "json.py").read_bytes()})

    with tempfile.TemporaryDirectory(prefix="rh2-production-causality-") as tmp:
        work = Path(tmp)
        (work / "src").mkdir()
        (work / "tests").mkdir()
        (work / "src/unused.py").write_text("def unused(:\n")
        (work / "tests/test_thing.py").write_text("import rh2_review_dependency_that_does_not_exist\ndef test_feature(): pass\ndef test_stable(): pass\n")
        proc = subprocess.run([sys.executable, "-m", "pytest", "-rA", "tests/test_thing.py"], cwd=work, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
        actual_log = proc.stdout.replace(str(work.resolve()), "/testbed").replace(str(work), "/testbed").replace(sys.base_prefix, "/python-runtime")
        probe = local_compile(work, ["src/unused.py"])
        result["unrelated_local_failure"] = {"pytest_rc": proc.returncode, "pytest_log": actual_log,
            "candidate_file_appears_in_failure": "src/unused.py" in actual_log, "compile_probe": probe}
        result["unrelated_error_transport"] = await formal_case("unrelated_error_transport", _pa_log(actual_log, test_rc=proc.returncode), probe["stdout"],
            paths={"src/unused.py": b"def unused(:\n"})

    # 不引用本机临时目录，以便 evidence 可提交。
    (OUT / "production_probe_result.json").write_text(json.dumps(json_safe(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    summary = {}
    for key, case in result.items():
        if isinstance(case, dict) and "report" in case:
            summary[key] = {"outcome": case["report"]["outcome"], "failure_category": case["report"]["failure_category"],
                            "reward": case["report"]["reward"], "member_disposition": case["member_disposition"],
                            "resource": (case["decision"] or {}).get("resource")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
