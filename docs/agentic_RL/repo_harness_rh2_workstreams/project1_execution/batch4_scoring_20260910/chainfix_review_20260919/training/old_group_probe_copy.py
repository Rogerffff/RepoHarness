"""将 P-A 资源未知反例送到实际 miles integration buffer 与 train-data conversion。"""
from __future__ import annotations

import asyncio
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
OUT = Path(__file__).resolve().parent
os.environ["RH2_MILES_PATH"] = str(REPO / "reference/miles-rh2-integration")
for p in (REPO / "rh2/src", REPO / "rh2/tests", REPO / "rh2/tests/grading", REPO / "rh2/tests/adapters", REPO / "rh2/tests/adapters_miles"):
    sys.path.insert(0, str(p))


async def run_group(world, root: Path, *, qualified: bool) -> dict:
    from test_w1b_group_admission import _build_chain, _dispatch_group, _buffer, _miles_args, _entry, _convert
    from test_w3a_formal_grading_freeze import make_barrier
    from test_w3b_grader_profile_unit import ProfileGraderFakeDocker, _PA_COLLECTION_FAIL_SEGMENT, _pa_log
    from sandbox_test_support import make_grader_profile
    from repoharness2.grading.manager import ExecResult, GradingManagerConfig, SWEGradingManager, EnvQualification, grading_image_identity, grading_scripts_digest

    chain = _build_chain(world, root, grading_kinds={})
    chain.orchestrator._runtime_barrier = make_barrier({"src/thing.py": b"def feature(:\n"})
    reports, managers, raw_decisions = [], [], []

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        assert workspace is None and frozen_delta is not None
        negative_member = trajectory_id.endswith("m1")
        log = (_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2) if negative_member else
               _pa_log("PASSED t.py::judge_1\nPASSED t.py::test_ok\n", test_rc=0))
        docker = ProfileGraderFakeDocker(base_commit=spec.base_commit, eval_log=log,
            repo_digests=("fixture@" + spec.image_manifest_digest,))
        docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"

        async def controlled(*args, input_bytes=None):
            if ((args[0] == "exec" and "memory.events" in args[-1]) or
                    (args[0] == "inspect" and "{{.State.OOMKilled}}" in args)):
                docker.calls.append(args)
                return ExecResult(1, "", "resource observation unavailable")
            return await docker(*args, input_bytes=input_bytes)

        # 条件注入：生产 actor 目前没有资格来源；显式区分此实验与现时 actor 行为。
        if qualified:
            spec = dataclasses.replace(spec, env_qualification=EnvQualification(
                image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec),
                reference_missing_count=0, source="conditional-fixture:gold", qualified_at_utc="2026-09-16T00:00:00Z",
            ))
        manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=controlled)
        managers.append(manager)
        report = await manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=frozen_delta, **kwargs)
        reports.append({"trajectory_id": trajectory_id, "outcome": report.outcome, "failure_category": report.failure_category, "reward": report.reward})
        raw_decisions.append(manager.container_records[-1].execution_failure_decision)
        return report

    chain.orchestrator._grading_submit = submit
    pg, group = await _dispatch_group(world, chain)
    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, pg, group))
    buffered = bool(buf._buffer)
    result = {"qualification_injected_for_experiment": qualified, "reports": reports, "decisions": raw_decisions,
              "group_buffered": buffered, "recycled": len(recycled), "metrics": buf.get_metrics()}
    if buffered:
        got = await buf.get(current_version=5)
        td = _convert(world, args, got.group)
        result["train_data"] = {"raw_reward": td["raw_reward"], "loss_masks": td["loss_masks"]}
    for manager in managers:
        assert all(record.removed for record in manager.container_records)
    return result


async def main():
    spec = importlib.util.spec_from_file_location("production_vendor_test_world", REPO / "rh2/tests/adapters_miles/conftest.py")
    fixtures = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fixtures
    spec.loader.exec_module(fixtures)
    scope = fixtures._vendor_slime_world.__wrapped__()
    next(scope)
    try:
        world = fixtures._World()
        world.install_sglang_stub()
        with tempfile.TemporaryDirectory(prefix="rh2-group-production-") as temp:
            result = {
                "miles_head": subprocess.check_output(["git", "-C", str(world.miles_root), "rev-parse", "HEAD"], text=True).strip(),
                "with_qualification": await run_group(world, Path(temp) / "qualified", qualified=True),
                "without_qualification": await run_group(world, Path(temp) / "unqualified", qualified=False),
            }
        assert result["with_qualification"]["train_data"]["raw_reward"] == [1.0, 0.0]
        assert all(sum(mask) > 0 for mask in result["with_qualification"]["train_data"]["loss_masks"])
        assert result["without_qualification"]["group_buffered"] is False
        (OUT / "group_transport_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        try:
            next(scope)
        except StopIteration:
            pass


if __name__ == "__main__":
    asyncio.run(main())
