"""W2a 中立 termination 事实记录测试。

覆盖：policy horizon / hard wall / infra timeout 三类事实各一例（正向）、
矛盾事实不可表示（负向）、计时区间倒挂拒绝、A5 批准前边界的中立性断言
（无 disposition 类字段/方法）、与 typed view 的 digest join 锚。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
)
from repoharness2.envpack.termination_facts import TerminationFactsV1

EPD = "sha256:" + "c" * 64


def make_facts(**overrides) -> TerminationFactsV1:
    base = dict(
        task_id="swe_gym_lite::getmoto__moto-1",
        environment_package_digest=EPD,
        termination_kind="task_token_budget_exhausted",
        resource_occupancy_started_unix_s=1000.0,
        terminated_unix_s=1600.0,
        capture_closed=True,
        execution_scope_quiescent=True,
        canonical_frozen_patch_formed=True,
        fresh_grading_complete=True,
        triggered_by_policy_horizon=True,
        triggered_by_hard_wall=False,
    )
    base.update(overrides)
    return TerminationFactsV1(**base)


# ---------------------------------------------------------------------------
# 正向：三类 timeout/终止事实各一例
# ---------------------------------------------------------------------------

def test_policy_horizon_fact_example():
    facts = make_facts()
    assert facts.triggered_by_policy_horizon and not facts.triggered_by_hard_wall
    assert facts.coarse_duration_s == 600.0
    assert facts.termination_kind in TERMINATION_KINDS_POLICY_HORIZON


def test_hard_wall_fact_example():
    facts = make_facts(
        termination_kind="hard_wall_timeout",
        triggered_by_policy_horizon=False,
        triggered_by_hard_wall=True,
        # hard wall 时事实布尔可以任意组合真值——记录不做归因/处置
        fresh_grading_complete=False,
    )
    assert facts.termination_kind in TERMINATION_KINDS_WATCHDOG
    assert facts.triggered_by_hard_wall and not facts.triggered_by_policy_horizon


def test_infra_timeout_fact_example():
    facts = make_facts(
        termination_kind="inference_timeout",
        triggered_by_policy_horizon=False,
        triggered_by_hard_wall=False,
        capture_closed=False,
        canonical_frozen_patch_formed=False,
        fresh_grading_complete=False,
    )
    assert not facts.triggered_by_policy_horizon and not facts.triggered_by_hard_wall


def test_owner_cancelled_and_completed_examples():
    for kind in ("owner_cancelled", "completed"):
        facts = make_facts(
            termination_kind=kind,
            triggered_by_policy_horizon=False,
            triggered_by_hard_wall=False,
        )
        assert facts.termination_kind == kind


# ---------------------------------------------------------------------------
# 负向：矛盾事实不可表示 + 计时区间倒挂
# ---------------------------------------------------------------------------

def test_policy_horizon_kind_with_false_flag_rejected():
    with pytest.raises(ValidationError, match="矛盾"):
        make_facts(triggered_by_policy_horizon=False)


def test_hard_wall_kind_with_false_flag_rejected():
    with pytest.raises(ValidationError, match="矛盾"):
        make_facts(
            termination_kind="hard_wall_timeout",
            triggered_by_policy_horizon=False,
            triggered_by_hard_wall=False,
        )


def test_completed_kind_claiming_policy_horizon_rejected():
    with pytest.raises(ValidationError, match="矛盾"):
        make_facts(
            termination_kind="completed",
            triggered_by_policy_horizon=True,
            triggered_by_hard_wall=False,
        )


def test_interval_reversal_rejected():
    with pytest.raises(ValidationError, match="倒挂"):
        make_facts(resource_occupancy_started_unix_s=2000.0, terminated_unix_s=1000.0)


def test_negative_timestamp_rejected():
    with pytest.raises(ValidationError):
        make_facts(resource_occupancy_started_unix_s=-1.0)


# ---------------------------------------------------------------------------
# A5 批准前边界：记录保持中立（无处置字段/方法）
# ---------------------------------------------------------------------------

def test_no_disposition_surface():
    tokens = ("disposition", "admission", "reward", "mask", "train", "penal", "sample")
    for name in TerminationFactsV1.model_fields:
        assert not any(tok in name.lower() for tok in tokens), name
    facts = make_facts()
    for attr in ("disposition", "admission", "should_train", "reward"):
        assert not hasattr(facts, attr)


def test_extra_disposition_field_rejected():
    payload = make_facts().model_dump(mode="json")
    with pytest.raises(ValidationError):
        TerminationFactsV1.model_validate({**payload, "disposition": "KEEP_FULL"})


# ---------------------------------------------------------------------------
# digest join 锚：与 typed view 消费链对上
# ---------------------------------------------------------------------------

def test_environment_package_digest_joins_with_trusted_view():
    from repoharness2.envpack.training_view import TrustedTaskController
    from test_w2a_trusted_views import make_result  # 同目录测试模块（pytest rootdir 插入）

    controller = TrustedTaskController.build_for_tests_from_ingest_result(make_result())
    tid = controller.task_ids()[0]
    view = controller.rollout_view(tid)
    facts = make_facts(task_id=tid,
                       environment_package_digest=view.environment_package_digest)
    # join 消费方拿 termination 事实里的锚回 controller 核对——通过
    controller.verify_environment_package_digest(facts.task_id,
                                                 facts.environment_package_digest)
