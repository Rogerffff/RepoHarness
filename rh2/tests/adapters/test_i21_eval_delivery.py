"""I21（第五组）：编排层的评测交付面——三类分开；unsafe artifact 在评测下只交付一条结果且不带训练 admission 载荷；
s1_compat 冻结路径逐字不变。

与 `test_w3a_formal_grading_freeze.py` 同一套 fa_formal 替身（真实 `SWEGradingManager` + FakeDocker）。
miles 入口侧的运输（身份、题包绑定、canonicalize）见 `tests/adapters_miles/test_i21_eval_entry.py`。
"""

from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
from grading_fixtures import FAILING_FAKE_LOG  # noqa: E402
from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain  # noqa: E402
from test_w3a_formal_grading_freeze import _formal_chain, _RealGrader, make_barrier  # noqa: E402

from repoharness2.adapters.slime.eval_result import EVAL_RESULT_METADATA_KEY  # noqa: E402
from repoharness2.adapters.slime.generate import QuiescenceConfirmed  # noqa: E402
from repoharness2.governance.admission import ADMISSION_METADATA_KEY  # noqa: E402

DISPATCH = {"eval_point_id": "0123abcd4567", "eval_rollout_id": 0, "target_weight_version": "5", "dataset": "swe_dev",
            "dataset_index": 0, "prompt_index": 0, "sample_slot": 0, "n_samples_per_eval_prompt": 1, "num_prompts": 1}


def _as_eval(chain):
    chain.base_sample.metadata = {**(chain.base_sample.metadata or {}), "rh2_eval_dispatch": dict(DISPATCH)}
    return chain


async def test_formal_eval_with_a_failing_official_log_is_a_graded_model_failure_not_missing():
    chain = _as_eval(_formal_chain(barrier=make_barrier({"src/x.py": b"print(1)\n"})))
    grader = _RealGrader(eval_log=FAILING_FAKE_LOG)  # 真实 SWEGradingManager：官方日志未全过 → tests_failed
    chain.orchestrator._grading_submit = grader.submit
    chain.orchestrator._grader_phase_timing_source = grader.manager.take_grader_phase_timing
    async with grader.queue:
        (leaf,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS), evaluation=True)
    payload = leaf.metadata[EVAL_RESULT_METADATA_KEY]
    assert (payload["result_class"], payload["task_outcome"], payload["reward"]) == ("graded", "unresolved", 0.0)
    assert payload["grading_failure_category"] == "tests_failed" and leaf.reward == 0.0 and leaf.status == "completed"
    assert payload["eval"] == DISPATCH and chain.orchestrator.audits[0].evaluation is True
    assert len(grader.calls) == 1


async def test_formal_eval_unsafe_artifact_delivers_one_result_without_the_training_admission_payload():
    target = b"../../etc/passwd"
    tb64, tsha = base64.b64encode(target).decode(), hashlib.sha256(target).hexdigest()

    class _Ws:
        snapshot_ref = "sha256:abc"

        def __init__(self, underlying):
            self._u = underlying

        async def run_bash(self, script):
            if "find ." in script:
                return SimpleNamespace(exit_code=0, stdout=f"symlink\t120000\t{tsha}\tsrc/escape\n", stderr="")
            if "readlink" in script:
                return SimpleNamespace(exit_code=0, stdout=f"src/escape\t{tb64}\n", stderr="")
            return await self._u.run_bash(script)

    class _Barrier:
        async def establish(self, *, workspace, audit):
            return QuiescenceConfirmed(frozen_grading_workspace=_Ws(workspace), snapshot_ref="sha256:abc", evidence_refs=("s",))

    # 训练派发：unsafe artifact = present + 永久拒绝，真实交付并带 admission 载荷（既有行为，对照）
    train = _formal_chain(barrier=_Barrier())
    (train_leaf,) = await train.orchestrator.generate(_Args(), train.base_sample, dict(SAMPLING_PARAMS))
    assert ADMISSION_METADATA_KEY in train_leaf.metadata and EVAL_RESULT_METADATA_KEY not in train_leaf.metadata

    chain = _as_eval(_formal_chain(barrier=_Barrier()))
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS), evaluation=True)
    (leaf,) = delivered  # 一次评测 attempt = 一条结果
    payload = leaf.metadata[EVAL_RESULT_METADATA_KEY]
    assert payload["result_class"] == "reward_unavailable" and payload["unavailable_reason"] == "unsafe_artifact"
    assert "unsafe_symlink_escape:src/escape" in payload["unavailable_detail"] and payload["reward"] is None
    assert leaf.reward is None and leaf.status == "aborted" and leaf.remove_sample is True  # 不是 NaN，也不是 0.0
    assert ADMISSION_METADATA_KEY not in leaf.metadata  # 训练平面的载荷不留在评测叶上
    assert chain.grading.calls == [] and chain.orchestrator.audits[0].evaluation is True


async def test_s1_compat_eval_placeholder_is_byte_for_byte_the_frozen_behaviour():
    chain = build_dense_chain()
    chain.base_sample.metadata = {**(chain.base_sample.metadata or {}), "rh2_eval_dispatch": dict(DISPATCH)}
    (placeholder,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS), evaluation=True)
    assert placeholder.reward == 1.0 and placeholder.status == "completed" and placeholder.remove_sample is True
    assert EVAL_RESULT_METADATA_KEY not in placeholder.metadata  # 冻结路径不经本批接线
    # 冻结路径的 infra 评分仍是旧的占位口径（0.0）——本批不改 s1_compat；formal 下同一情形是 None（见 adapters_miles 用例）
    infra = build_dense_chain(infra_grading=True)
    (infra_placeholder,) = await infra.orchestrator.generate(_Args(), infra.base_sample, dict(SAMPLING_PARAMS), evaluation=True)
    assert EVAL_RESULT_METADATA_KEY not in infra_placeholder.metadata
