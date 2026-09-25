"""R2E 接线 R-e：`r2e_expected_map` 报告在正式链上的运输（单成员）。

报告**不手工构造**：真实 SWEGradingManager（grader profile）+ `build_r2e_grading_spec` 渲染的脚本与 parser 产出
GradingReport → RewardFacts → gate（clean_grading）→ Outcome v2 → admission 载荷 → 交付叶。

消费者零改动：训练侧（governance / adapters.miles / generate）不读 F2P/P2P 计数，也不读 `grading_semantics`——
它们只消费 outcome / failure_category / reward / hygiene。这里钉住的就是这件事：四个 F2P/P2P 计数恒为 None 的
R2E 报告，走完与 SWE 报告完全相同的路。组级（真实 miles buffer：同批一个 SWE 组 + 一个 R2E 组、混来源组拒绝）
要进 tests/adapters_miles，那里的精确用例计数由 A 线的 lane manifest 管，见 R2E 计划 §11 的协调项。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_test_support import make_grader_profile  # noqa: E402
from test_slime_generate import SAMPLING_PARAMS, TASK_ID_DENSE, _Args, make_task  # noqa: E402
from test_w3a_formal_grading_freeze import BASE_COMMIT, _formal_chain, make_barrier  # noqa: E402
from test_w3b_grader_profile_unit import GOOD_SETUP_ATTEST, ProfileGraderFakeDocker  # noqa: E402

from repoharness2.adapters.slime.r2e_grading_scripts import build_r2e_grading_spec, r2e_official_files  # noqa: E402
from repoharness2.envpack.bundles_v2 import (  # noqa: E402
    PrivateGradingBundleR2E,
    R2EHiddenTestFile,
    r2e_hidden_tests_tree_digest,
)
from repoharness2.envpack.r2e_parsers import R2E_DATASET_REVISION, R2E_GRADER_VERSION_TAG  # noqa: E402
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager  # noqa: E402

EXPECTED = {"TestCore.test_fixed": "PASSED", "TestCore.test_known_failure": "FAILED"}


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bundle() -> PrivateGradingBundleR2E:
    text, entry = json.dumps(EXPECTED), ".venv/bin/python -W ignore -m pytest -rA r2e_tests"
    files = [R2EHiddenTestFile(path="test_1.py", sha256=_sha("t"))]
    return PrivateGradingBundleR2E(
        instance_id="demo__" + "f" * 40, repo="demo", repo_key_lower="demo", base_commit=BASE_COMMIT,
        source_commit_hash="f" * 40, expected_output_json=text, expected_output_json_sha256=_sha(text),
        run_tests_sh=entry, run_tests_sh_sha256=_sha(entry), hidden_test_files=files,
        hidden_tests_tree_sha256=r2e_hidden_tests_tree_digest((f.path, f.sha256) for f in files),
        source_revision=R2E_DATASET_REVISION,
    )


def _log(*summary: str, rc: int, markers: bool = True) -> str:
    body = "==== short test summary info ====\n" + "\n".join(summary) + "\n==== done in 0.1s ====\n"
    if not markers:
        return body
    return f"RH2_INSTALL_SKIPPED=1\n>>>>> Start Test Output\n{body}>>>>> End Test Output\nRH2_TEST_RC={rc}\nRH2_TS_TEST_END=1.0\n"


GOLD_LOG = _log("PASSED r2e_tests/test_1.py::TestCore::test_fixed",
                "FAILED r2e_tests/test_1.py::TestCore::test_known_failure - AssertionError", rc=1)
NOOP_LOG = _log("FAILED r2e_tests/test_1.py::TestCore::test_fixed - AssertionError: broken",
                "FAILED r2e_tests/test_1.py::TestCore::test_known_failure - AssertionError", rc=1)


async def _run(eval_log: str):
    bundle = _bundle()
    spec = build_r2e_grading_spec(
        task_id=TASK_ID_DENSE, grading=bundle, image="fake-image:v1", image_manifest_digest="sha256:" + "0" * 64)
    spec = dataclasses.replace(spec, image_manifest_digest=None, image_local_build=True)
    task = dataclasses.replace(make_task(TASK_ID_DENSE), grading_spec=spec)
    n_official = str(len(r2e_official_files(bundle)))
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=eval_log)
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": n_official, "RH2_SETUP_TEST_FILES": n_official}
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=docker)
    chain = _formal_chain(barrier=make_barrier({"src/thing.py": b"def feature():\n    return 'fixed'\n"}), task=task)

    async def submit(*, trajectory_id, workspace, spec, frozen_delta=None, **kwargs):
        assert workspace is None and frozen_delta is not None  # 正式链：只依赖冻结输入
        return await manager.grade(trajectory_id=trajectory_id, workspace=None, spec=spec, frozen_delta=frozen_delta)

    chain.orchestrator._grading_submit = submit
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    return docker, chain.orchestrator.audits[0], delivered


@pytest.mark.parametrize(
    ("eval_log", "outcome", "reward", "match"),
    [(GOLD_LOG, "resolved", 1.0, (2, 2)), (NOOP_LOG, "unresolved", 0.0, (1, 2))],
)
async def test_r2e_source_rule_reports_transport_as_binary_reward_members(eval_log, outcome, reward, match):
    docker, audit, delivered = await _run(eval_log)
    report = audit.finalized.grading_report
    assert (report.outcome, report.reward, report.grading_semantics) == (outcome, reward, "r2e_expected_map")
    assert (report.expected_match_count, report.expected_total_count) == match
    assert report.f2p_pass_count is None and report.p2p_total_count is None  # R2E 报告没有 F2P/P2P 计数
    assert report.grader_version == R2E_GRADER_VERSION_TAG
    assert report.patch_hygiene.verdict == "clean" and report.patch_hygiene.replayed_on_clean_checkout is True
    facts = audit.finalized.eligibility_report.facts
    assert facts.clean_grading.ok is True and facts.clean_grading.reason_codes == []
    assert audit.outcome_v2["task_outcome"] == outcome and audit.outcome_v2["reward_unavailable"] is False
    (leaf,) = delivered
    assert leaf.remove_sample is False and leaf.metadata["rh2_admission"]["grading_outcome"] == outcome
    # 可信 setup 与候选段确实是 R2E 渲染器那一组脚本（不是回落到 SWE 形状）
    written = [p.decode("utf-8", "replace") for _, p in docker.input_payloads]
    assert any("/rh2_private/r2e_tests" in s and "RH2_APPLY_RC=0" in s for s in written)
    assert any("bash run_tests.sh" in s and "RH2_INSTALL_SKIPPED=1" in s for s in written)


async def test_r2e_missing_markers_transports_as_infra_without_reward():
    _, audit, delivered = await _run(_log("PASSED r2e_tests/test_1.py::TestCore::test_fixed", rc=0, markers=False))
    report = audit.finalized.grading_report
    assert (report.outcome, report.failure_category, report.reward) == ("failed_to_grade", "test_log_parse_failed", None)
    assert report.grading_semantics == "r2e_expected_map" and report.expected_total_count is None
    assert audit.outcome_v2["reward_unavailable"] is True and audit.outcome_v2["failure_category"] == "grading_infra_failure"
    (leaf,) = delivered
    assert leaf.metadata["rh2_admission"]["grading_outcome"] == "failed_to_grade"


async def test_r2e_zero_parse_without_qualification_is_unattributed_infra_not_a_zero():
    """零解析且没有环境资格记录：P-A 三路判定走"未确定"→ infra 族、无 reward（不把环境问题记成模型负样本）。"""
    _, audit, _ = await _run(_log(rc=2).replace("==== short test summary info ====\n", "ImportError: boom\n"))
    report = audit.finalized.grading_report
    assert (report.outcome, report.reward, report.grading_semantics) == ("failed_to_grade", None, "r2e_expected_map")
    assert "unattributed" in report.infra_failure_detail and "qualification:absent" in report.infra_failure_detail
    assert audit.outcome_v2["reward_unavailable"] is True
