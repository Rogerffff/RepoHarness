"""第四组 A（P-A，2026-09-16）：candidate_execution_failed 在正式链上的运输测试。

真实 SWEGradingManager（grader profile、v2 parser、资格记录、编译复证替身）产出 candidate_execution_failed →
RewardFacts（raw_reward 0.0）→ gate（clean_grading 通过）→ Outcome（unresolved、reward 可用）→ admission → 组内成员保留。
消费者零改动：只有契约与 producer 变了（R1）。
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from grading_fixtures import make_fixture_spec  # noqa: E402
from sandbox_test_support import make_grader_profile  # noqa: E402
from test_slime_generate import SAMPLING_PARAMS, TASK_ID_DENSE, _Args, make_task  # noqa: E402
from test_w3a_formal_grading_freeze import BASE_COMMIT, _formal_chain, make_barrier  # noqa: E402
from test_w3b_grader_profile_unit import (  # noqa: E402
    _PA_COLLECTION_FAIL_SEGMENT,
    ProfileGraderFakeDocker,
    _pa_log,
    _pa_v2_parser,
)

from repoharness2.grading.manager import (  # noqa: E402
    EnvQualification,
    GradingManagerConfig,
    SWEGradingManager,
    grading_image_identity,
    grading_scripts_digest,
    render_compile_probe_script,
)


def _pa_task(*, qualified: bool):
    task = make_task(TASK_ID_DENSE)
    spec = make_fixture_spec(
        BASE_COMMIT, "fake-image:v1", checkout_mode="image_embedded", task_id=TASK_ID_DENSE,
        parse_log=_pa_v2_parser(), render_compile_probe=render_compile_probe_script,
    )
    if qualified:
        spec = dataclasses.replace(spec, env_qualification=EnvQualification(
            image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec), reference_missing_count=0,
            source="ledger_e2_A.jsonl:rpt_gold_1", qualified_at_utc="2026-09-16T00:00:00Z",
        ))
    return dataclasses.replace(task, grading_spec=spec)


def _grader():
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=docker)
    return docker, manager


async def _run(qualified: bool):
    docker, manager = _grader()
    chain = _formal_chain(barrier=make_barrier({"src/thing.py": b"def feature(:\n"}), task=_pa_task(qualified=qualified))

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        assert workspace is None and frozen_delta is not None
        return await manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=frozen_delta)

    chain.orchestrator._grading_submit = submit
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    return docker, chain.orchestrator.audits[0], delivered


async def test_pa_candidate_execution_failed_transports_as_reward_zero_member():
    docker, audit, delivered = await _run(qualified=True)
    report = audit.finalized.grading_report
    assert report.outcome == "unresolved" and report.failure_category == "candidate_execution_failed" and report.reward == 0.0
    assert report.execution_failure_stage == "test_collection" and report.f2p_total_count is None
    assert report.patch_hygiene.verdict == "clean" and report.patch_hygiene.replayed_on_clean_checkout is True
    facts = audit.finalized.eligibility_report.facts
    assert facts.clean_grading.ok is True and facts.clean_grading.reason_codes == []
    assert audit.outcome_v2["task_outcome"] == "unresolved" and audit.outcome_v2["reward_unavailable"] is False
    assert audit.outcome_v2.get("failure_category") is None
    (leaf,) = delivered
    assert leaf.remove_sample is False and "rh2_admission" in leaf.metadata
    assert leaf.metadata["rh2_admission"]["grading_outcome"] == "unresolved"
    assert any("RH2_COMPILE_EOF" in str(a[-1]) for a in docker.calls if a and a[0] == "exec")


async def test_pa_unattributed_failure_transports_as_infra_without_reward():
    docker, audit, delivered = await _run(qualified=False)
    report = audit.finalized.grading_report
    assert report.outcome == "failed_to_grade" and report.failure_category == "test_log_parse_failed" and report.reward is None
    assert "qualification:absent" in report.infra_failure_detail
    assert audit.outcome_v2["reward_unavailable"] is True and audit.outcome_v2["failure_category"] == "grading_infra_failure"
    assert not any("RH2_COMPILE_EOF" in str(a[-1]) for a in docker.calls if a and a[0] == "exec")
