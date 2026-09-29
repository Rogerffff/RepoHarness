"""复用已复制的旧组运输探针形状，检验本轮真实 pytest 反例对实际 miles group 的影响。"""
from __future__ import annotations

import asyncio
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "rh2/pyproject.toml").is_file())
os.environ["RH2_MILES_PATH"] = str(REPO / "reference/miles-rh2-integration")
for p in (REPO / "rh2/src", REPO / "rh2/tests", REPO / "rh2/tests/grading", REPO / "rh2/tests/adapters", REPO / "rh2/tests/adapters_miles"):
    sys.path.insert(0, str(p))
import old_probe_copy as old


async def run_group(world, name: str, *, bad_log: str, compile_out: str, paths: dict[str, bytes], refs, qualified=True):
    from test_w1b_group_admission import _build_chain, _dispatch_group, _buffer, _miles_args, _entry, _convert
    from test_w3a_formal_grading_freeze import make_barrier
    from sandbox_test_support import make_grader_profile
    from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager, render_compile_probe_script

    chain = _build_chain(world, HERE / "group_cases" / name, grading_kinds={})
    chain.orchestrator._runtime_barrier = make_barrier(paths)
    reports, decisions, managers = [], [], []

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        assert workspace is None and frozen_delta is not None
        negative = trajectory_id.endswith("m1")
        good_log = old._pa_log("".join(f"PASSED {test_id}\n" for ids in refs for test_id in ids), test_rc=0)
        docker = old.ProfileGraderFakeDocker(base_commit=spec.base_commit, eval_log=bad_log if negative else good_log,
            repo_digests=("fixture@" + spec.image_manifest_digest,))
        docker.compile_probe_stdout = compile_out
        spec = dataclasses.replace(spec, parse_log=old.parser_for(*refs), render_compile_probe=render_compile_probe_script)
        if qualified:
            spec = old.set_qualification(spec)
        manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=docker)
        managers.append(manager)
        report = await manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=frozen_delta, **kwargs)
        reports.append({"trajectory_id": trajectory_id, "outcome": report.outcome, "category": report.failure_category, "reward": report.reward})
        decisions.append(manager.container_records[-1].execution_failure_decision)
        return report

    chain.orchestrator._grading_submit = submit
    pg, group = await _dispatch_group(world, chain)
    args = _miles_args(world, chain)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, pg, group))
    result = {"qualification_injected_for_cpu_experiment": qualified, "reports": reports, "decisions": decisions,
              "group_buffered": bool(buf._buffer), "recycled": len(recycled), "metrics": buf.get_metrics()}
    if result["group_buffered"]:
        got = await buf.get(current_version=5)
        td = _convert(world, args, got.group)
        result["train_data"] = {"raw_reward": td["raw_reward"], "loss_masks": td["loss_masks"]}
    for manager in managers:
        assert all(record.removed for record in manager.container_records)
    return result


async def main():
    data = json.loads((HERE / "probe_chainfix_training.json").read_text())
    fixture_spec = importlib.util.spec_from_file_location("chainfix_training_vendor_world", REPO / "rh2/tests/adapters_miles/conftest.py")
    fixtures = importlib.util.module_from_spec(fixture_spec)
    sys.modules[fixture_spec.name] = fixtures
    fixture_spec.loader.exec_module(fixtures)
    scope = fixtures._vendor_slime_world.__wrapped__()
    next(scope)
    try:
        world = fixtures._World()
        world.install_sglang_stub()
        r1 = data["r1_path_in_argument_not_exception_location"]
        refs = (["tests/test_thing.py::test_feature"], ["tests/test_thing.py::test_stable"])
        out = {"miles_head": subprocess.check_output(["git", "-C", str(world.miles_root), "rev-parse", "HEAD"], text=True).strip()}
        for variant, source in (("bad", "def unused(:\n"), ("clean_same_log", "marker = 2\n")):
            out[f"r1_{variant}"] = await run_group(world, f"r1_{variant}", bad_log=old._pa_log(r1["pytest"]["stdout"], test_rc=2),
                compile_out=(r1[variant]["compile_runs"][0]["stdout"] if r1[variant]["compile_runs"] else ""), paths={"src/unused.py": source.encode()}, refs=refs)
        refs_ids = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
        for name, log in (("r4_simple", data["old_r4_completed"]["pytest"]["stdout"]),
                          ("r4_nested", data["r4_completed_nested_traceback"]["pytest"]["stdout"])):
            out[name] = await run_group(world, name, bad_log=old._pa_log(log, test_rc=1), compile_out="",
                paths={"src/id_source.py": b'label = "after"\n'}, refs=refs_ids, qualified=False)
        assert not out["r1_bad"]["group_buffered"]
        assert not out["r1_clean_same_log"]["group_buffered"]
        assert out["r4_simple"]["train_data"]["raw_reward"] == [1.0, 0.0]
        assert out["r4_nested"]["train_data"]["raw_reward"] == [1.0, 0.0]
        text = json.dumps(out, ensure_ascii=False, indent=2).replace(str(REPO), "<REPO>").replace(str(Path.home()), "<USER_HOME>")
        (HERE / "group_transport_result.json").write_text(text + "\n")
        print(json.dumps({key: {"reports": val["reports"], "group_buffered": val["group_buffered"], "raw_reward": val.get("train_data", {}).get("raw_reward")} for key, val in out.items() if isinstance(val, dict)}, ensure_ascii=False, indent=2))
    finally:
        try:
            next(scope)
        except StopIteration:
            pass


if __name__ == "__main__":
    asyncio.run(main())
