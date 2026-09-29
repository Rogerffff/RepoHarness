"""R2E R-b/R-e 独立 CPU 接缝探针；不改维护测试、manifest 或生产函数。

从 rh2/ 运行：uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_local_review_20260922/probes/training_transport_probe.py
容器、harness、session adapter、编译结果是现有测试接口替身；报告、身份、准入、buffer、conversion 为真实代码。
"""
from __future__ import annotations

import asyncio
import dataclasses
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2").is_dir())
RH2 = ROOT / "rh2"
MILES = ROOT / "reference/miles-rh2-integration"
os.environ["RH2_MILES_PATH"] = str(MILES)
for p in (RH2 / "tests/envpack", RH2 / "tests/grading", RH2 / "tests/adapters", RH2 / "tests/adapters_miles", RH2 / "tests", MILES, RH2 / "src"):
    sys.path.insert(0, str(p))

spec = importlib.util.spec_from_file_location("review_miles_fixtures", RH2 / "tests/adapters_miles/conftest.py")
fixtures = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fixtures
spec.loader.exec_module(fixtures)
fixtures._install_ray_stub()
fixtures.install_sglang_stub()

import test_w1b_group_admission as group_fixture
import test_ingest_r2e_subset as ingest_fixture
from test_w1b_prepared_chain import _dispatch_groups
from test_w3a_formal_grading_freeze import make_barrier
from test_w3b_grader_profile_unit import GOOD_SETUP_ATTEST, ProfileGraderFakeDocker, _PA_COLLECTION_FAIL_SEGMENT, _PA_STARTUP_FAIL_SEGMENT
from sandbox_test_support import make_grader_profile
from w1b_synthetic_tasks import PreparedFixture, TID1, make_result

from repoharness2.envpack.prepared_tasks import prepare_tasks
from repoharness2.envpack.training_view import TrustedTaskController
from repoharness2.grading.manager import EnvQualification, GradingManagerConfig, SWEGradingManager, grading_image_identity, grading_scripts_digest
from repoharness2.adapters.miles.group_admission import GroupAdmissionFatal
from miles.rollout.base_types import GenerateFnInput
from miles.ray.rollout.rollout_data_conversion import postprocess_rollout_data
from miles.ray.rollout.train_data_conversion import convert_samples_to_train_data

EXPECTED = {"TestCore.test_x": "PASSED", "TestCore.test_legacy": "FAILED", "TestCore.test_env": "ERROR"}
R2E_ID = "r2e_gym_subset::demo__" + "f" * 40
RESULTS = {}


def r2e_log(lines=(), *, body=None, rc=1, markers=True):
    counts = {label: sum(line.startswith(prefix + " ") for line in lines)
              for prefix, label in (("PASSED", "passed"), ("FAILED", "failed"), ("ERROR", "error"))}
    summary = ", ".join(f"{n} {label}" for label, n in counts.items() if n) or "no tests ran"
    segment = body if body is not None else "=== short test summary info ===\n" + "\n".join(lines) + f"\n=== {summary} in 0.1s ===\n"
    if not markers:
        return segment
    return "RH2_INSTALL_SKIPPED=1\n>>>>> Start Test Output\n" + segment + f">>>>> End Test Output\nRH2_TEST_RC={rc}\n"


GOLD = r2e_log(("PASSED r2e_tests/t.py::TestCore::test_x", "FAILED r2e_tests/t.py::TestCore::test_legacy - known", "ERROR r2e_tests/t.py::TestCore::test_env - known"))
LOGS = {
    "gold": GOLD,
    "all_wrong": r2e_log(("FAILED r2e_tests/t.py::TestCore::test_x - fail", "PASSED r2e_tests/t.py::TestCore::test_legacy", "PASSED r2e_tests/t.py::TestCore::test_env")),
    "partial": r2e_log(("PASSED r2e_tests/t.py::TestCore::test_x",)),
    "all_missing": r2e_log(("PASSED r2e_tests/t.py::Other::test_else",), rc=0),
    "zero": r2e_log(body="ImportError: missing_dependency\n", rc=2),
    "candidate_collection": r2e_log(body=_PA_COLLECTION_FAIL_SEGMENT, rc=2),
    "candidate_startup": r2e_log(body=_PA_STARTUP_FAIL_SEGMENT, rc=4),
    "unknown_termination": r2e_log(body=_PA_STARTUP_FAIL_SEGMENT, rc=4),
    "infra_setup": GOLD,
    "no_markers": r2e_log(body="parser never began\n", markers=False),
    "extra": r2e_log(("PASSED r2e_tests/t.py::TestCore::test_x", "FAILED r2e_tests/t.py::TestCore::test_legacy - known", "ERROR r2e_tests/t.py::TestCore::test_env - known", "PASSED r2e_tests/t.py::Other::test_else")),
}


def mixed_fixture(path):
    row = ingest_fixture._row(commit="f" * 40)
    row["expected_output_json"] = json.dumps(EXPECTED)
    facts = ingest_fixture._facts_doc(commit="f" * 40, expected_n=3)
    facts["tasks"][0]["git"]["head"] = "a" * 40
    facts["tasks"][0]["image"]["repo_digest"] = "namanjain12/demo_final@sha256:" + "b" * 64
    r2e = ingest_fixture._ingest([row], facts)
    controller = TrustedTaskController.build_for_tests_from_ingest_result(make_result(("getmoto__moto-1",)), r2e)
    prepared, private = path / "prepared", path / "private"
    manifest = prepare_tasks(controller, out_dir=prepared, private_dir=private, task_ids=[TID1, R2E_ID])
    return PreparedFixture(controller, prepared, private, manifest)


async def run_groups(world, path, case, *, mix=False):
    fx = mixed_fixture(path)
    # 仅替换维护测试的装配工厂，生产 loader / face / registry 均不替代。
    group_fixture.prepare_synthetic = lambda *_a, **_kw: fx
    chain = group_fixture._build_chain(world, path, grading_kinds={})
    chain.orchestrator._runtime_barrier = make_barrier({"src/thing.py": b"def feature(:\n"})
    report_rows = []

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        assert workspace is None and frozen_delta is not None
        slot = int(trajectory_id.rsplit("m", 1)[1])
        kind = "gold" if slot == 0 else case
        is_r2e = spec.task_id == R2E_ID
        if is_r2e:
            log = LOGS[kind]
        else:
            status = "PASSED" if slot == 0 else "FAILED"
            log = f">>>>> Start Test Output\n{status} t.py::judge_1\nPASSED t.py::test_ok\n>>>>> End Test Output\nRH2_TEST_RC={slot}\n"
        docker = ProfileGraderFakeDocker(base_commit="a" * 40, eval_log=log, repo_digests=("fixture@sha256:" + "b" * 64,))
        n = str(len(spec.hygiene.test_files))
        docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": n, "RH2_SETUP_TEST_FILES": n}
        if is_r2e and kind in ("candidate_collection", "candidate_startup", "unknown_termination"):
            spec = dataclasses.replace(spec, env_qualification=EnvQualification(
                image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec),
                reference_missing_count=0, source="cpu_review_qualified", qualified_at_utc="2026-09-22T00:00:00Z",
            ))
            docker.compile_probe_stdout = "RH2_COMPILE_INTERPRETER=/testbed/.venv/bin/python\nRH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
        if is_r2e and kind == "unknown_termination":
            docker.pids_events_stdout = "unreadable\n"
        if is_r2e and kind == "infra_setup":
            docker.setup_exit_code = 17
        manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=path / "logs"), docker=docker)
        report = await manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=frozen_delta)
        rec = manager.container_records[-1]
        report_rows.append({
            "trajectory_id": trajectory_id, "task_id": spec.task_id, "kind": kind,
            "semantics": report.grading_semantics, "outcome": report.outcome, "reward": report.reward,
            "failure_category": report.failure_category, "detail": report.infra_failure_detail,
            "expected_counts": [report.expected_match_count, report.expected_total_count],
            "swe_counts": [report.f2p_pass_count, report.f2p_total_count, report.p2p_fail_count, report.p2p_total_count],
            "decision": rec.execution_failure_decision,
            "compile_calls": sum("RH2_COMPILE_EOF" in str(c[-1]) for c in docker.calls if c and c[0] == "exec"),
        })
        return report

    chain.orchestrator._grading_submit = submit
    args = group_fixture._miles_args(world, chain)
    args.rollout_batch_size = 2
    args.global_batch_size = 4
    args.rewards_normalization = True
    args.grpo_std_normalization = False
    prompt_groups = _dispatch_groups(fx, n=2)
    if mix:
        # 生产 Dataset 派出两个来源后，以真实分派三元组生成一个混题组。
        # 只改变第二个 prompt 的 group/index 以模拟 caller 组装错误，身份仍由真实 generate 入口铸造。
        prompt_groups = [[prompt_groups[0][0], prompt_groups[1][1]]]
        prompt_groups[0][1].group_index = 0
        prompt_groups[0][1].index = 1
    fn = world.Rh2MilesGenerateFn()
    groups = []
    for pg in prompt_groups:
        group = []
        for sample in pg:
            out = await fn(GenerateFnInput(state=SimpleNamespace(args=args), sample=sample,
                                          sampling_params=dict(group_fixture.SAMPLING_PARAMS), evaluation=False))
            group.append(out.samples)
        groups.append(group)
    assert len(chain.registry) == 0
    buf, recycled = group_fixture._buffer(world, args)
    fatal = None
    try:
        for pg, group in zip(prompt_groups, groups):
            await buf.put(group_fixture._entry(world, pg, group))
    except GroupAdmissionFatal as exc:
        fatal = exc.reason_code
    buffered = len(buf._buffer)
    metrics = buf.get_metrics()
    train = None
    if buffered == 2:
        got = [(await buf.get(current_version=5)).group for _ in range(buffered)]
        data, metadata = postprocess_rollout_data(args, got, train_parallel_config=None)
        converted = convert_samples_to_train_data(args, data, metadata, None, None)
        train = {k: converted[k] for k in ("raw_reward", "rewards", "sample_indices", "rollout_ids", "rollout_mask_sums")}
        train["mask_sums"] = [sum(x) for x in converted["loss_masks"]]
        train["task_ids"] = [s.metadata["task_id"] for s in data]
        # 正式派发 metadata 不带 source；来源由可信 task_id 的命名空间可确定。
        train["sources_from_task_id"] = [s.metadata["task_id"].split("::", 1)[0] for s in data]
    audits = [{"grading_report": a.finalized.grading_report.model_dump(mode="json"),
               "reward_facts": a.finalized.projection.reward_facts.model_dump(mode="json"),
               "clean_grading": a.finalized.eligibility_report.facts.clean_grading.ok,
               "outcome_reward_unavailable": a.outcome_v2["reward_unavailable"]} for a in chain.orchestrator.audits]
    await buf.aclose()
    return {"reports": report_rows, "audits": audits, "buffered": buffered,
            "metrics": metrics, "train": train, "fatal": fatal, "recycled": len(recycled)}


async def main():
    world = fixtures._World()
    expected = {
        "all_wrong": ("tests_failed", 0.0, [0, 3], 2),
        "partial": ("tests_failed", 0.0, [1, 3], 2),
        "all_missing": ("tests_failed", 0.0, [0, 4], 2),
        "zero": ("test_log_parse_failed", None, [None, None], 1),
        "candidate_collection": ("candidate_execution_failed", 0.0, [None, None], 2),
        "candidate_startup": ("candidate_execution_failed", 0.0, [None, None], 2),
        "unknown_termination": ("test_log_parse_failed", None, [None, None], 1),
        "infra_setup": ("infra_failure", None, [None, None], 1),
        "no_markers": ("test_log_parse_failed", None, [None, None], 1),
        "extra": ("tests_failed", 0.0, [3, 4], 2),
    }
    with tempfile.TemporaryDirectory(prefix="r2e-training-review-") as temp:
        for case, (category, reward, counts, buffered) in expected.items():
            row = await run_groups(world, Path(temp) / case, case)
            target = row["reports"][-1]
            assert (target["failure_category"], target["reward"], target["expected_counts"]) == (category, reward, counts), row
            assert row["buffered"] == buffered and row["recycled"] == 0, row
            gold = row["reports"][-2]
            assert (gold["outcome"], gold["reward"], gold["expected_counts"]) == ("resolved", 1.0, [3, 3])
            assert target["semantics"] == gold["semantics"] == "r2e_expected_map"
            assert target["swe_counts"] == gold["swe_counts"] == [None] * 4
            if row["train"]:
                assert row["train"]["raw_reward"] == [1.0, 0.0, 1.0, 0.0], row
                assert row["train"]["rewards"] == [0.5, -0.5, 0.5, -0.5], row
                assert row["train"]["sources_from_task_id"] == ["swe_gym_lite"] * 2 + ["r2e_gym_subset"] * 2
                assert all(x > 0 for x in row["train"]["mask_sums"])
            if case == "all_missing":
                assert target["decision"]["kind"] == "source_rule" and target["decision"]["qualification"] is None
            if case.startswith("candidate_"):
                assert target["compile_calls"] == 1 and target["decision"]["kind"] == "candidate"
            if case == "unknown_termination":
                assert target["compile_calls"] == 0 and "termination_facts_unknown:pids_events_max" in target["detail"]
            RESULTS[case] = row
            print(case + ": PASS", flush=True)
        mixed = await run_groups(world, Path(temp) / "mixed", "all_wrong", mix=True)
        assert mixed["fatal"] == "mixed_group_members" and mixed["buffered"] == 0 and mixed["train"] is None, mixed
        RESULTS["mixed_group"] = mixed
        print("mixed_group: PASS", flush=True)
    output = Path(__file__).with_name("training_transport_results.json")
    output.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2) + "\n")
    print(str(output), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
