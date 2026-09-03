"""API 面测试：wrapper 是治理层唯一公开入口（绕过路径钉死）+ 未知字段拒收。"""

from __future__ import annotations

import inspect

import pytest
from governance_samples import run_finalize
from pydantic import ValidationError

import repoharness2.governance as governance
from repoharness2.governance import (
    FinalizedRollout,
    GateOutcome,
    GroupRepairSignal,
    ProjectionMarkerHit,
    ProjectionScanResult,
)
from repoharness2.governance import gate, projection_scan, sandbox_capability_facts, wrapper


def test_governance_public_api_is_exact():
    """governance 包公开面精确钉死：新增公开名字必须显式改本测试（防 API 面漂移）。"""

    assert set(governance.__all__) == {
        "GATE_VERSION",
        "SandboxCapabilityFacts",  # 冻结历史 schema（D2-2），只作兼容读路径
        "FinalizedRollout",
        "GateInputError",
        "GateOutcome",
        "GroupRepairSignal",
        "ProjectionMarkerHit",
        "ProjectionScanResult",
        "finalize_rollout",
    }


def test_admission_module_public_functions_pinned():
    """W1b 第二段：governance/admission.py 消费 gate 产物（不是 gate 绕行路径）——其公开函数
    精确钉死，且不经包级 __init__ 转出（消费方按模块路径 import）。"""

    from repoharness2.governance import admission

    public_functions = {
        name
        for name, obj in vars(admission).items()
        if not name.startswith("_") and inspect.isfunction(obj) and obj.__module__ == admission.__name__
    }
    assert public_functions == {
        "decide_member_disposition",
        "derive_admission_payload",
        "resolve_admission_payload",
        "stamp_admission_payload",
        "truncation_slot",
    }
    assert not any(name in governance.__all__ for name in public_functions)


def test_finalize_rollout_is_the_only_public_callable():
    """四个模块里本模块定义的公开函数只有 wrapper.finalize_rollout 一个——
    "直接调 gate/scan 绕过 wrapper"的路径不存在于公开 API 面。"""

    public_functions: set[str] = set()
    for module in (gate, projection_scan, sandbox_capability_facts, wrapper):
        for name, obj in vars(module).items():
            if name.startswith("_"):
                continue
            if inspect.isfunction(obj) and obj.__module__ == module.__name__:
                public_functions.add(f"{module.__name__.rsplit('.', 1)[-1]}.{name}")
    assert public_functions == {"wrapper.finalize_rollout"}


def test_gate_and_scan_execution_functions_are_module_private():
    """底层执行函数模块级私有：无下划线别名可供 import。"""

    assert not hasattr(gate, "evaluate")
    assert hasattr(gate, "_evaluate")  # 存在但私有（wrapper 内部用）
    assert not hasattr(projection_scan, "scan_public_projection")
    assert hasattr(projection_scan, "_scan_public_projection")
    # 包层不转出私有函数
    assert not hasattr(governance, "_evaluate")
    assert not hasattr(governance, "evaluate")


async def test_finalize_rollout_does_not_run_projection_scan(monkeypatch):
    """D2-4：projection 扫描已不是关口的一步——把冻结实现换成炸弹，finalize 仍完整走通。"""

    def _boom(projection):
        raise AssertionError("finalize_rollout 不得再调用 _scan_public_projection")

    monkeypatch.setattr(projection_scan, "_scan_public_projection", _boom)
    final = await run_finalize()
    assert final.eligibility_report.eligibility_class == "online_policy_loss_eligible"
    assert "scan_result" not in FinalizedRollout.model_fields


async def test_unknown_fields_rejected_on_governance_models():
    """未知字段拒收（宪法 extra=forbid 在 S1-5 新对象上逐一复证）。"""

    final = await run_finalize()

    cases: list[tuple[type, dict]] = [
        (FinalizedRollout, final.model_dump(mode="json")),
        (
            GateOutcome,
            {
                "report": final.eligibility_report.model_dump(mode="json"),
                "group_repair_signal": final.group_repair_signal.model_dump(mode="json"),
            },
        ),
        (GroupRepairSignal, final.group_repair_signal.model_dump(mode="json")),
        (
            ProjectionScanResult,  # 冻结 schema，样例手工构造（FinalizedRollout 已无 scan_result）
            {
                "trajectory_id": "traj_0001",
                "scanned_schema_id": "rh2.trajectory_projection.v1",
                "hits": [],
                "clean": True,
            },
        ),
        (
            ProjectionMarkerHit,
            {"path": "$.task_id", "marker": "test_patch", "kind": "value"},
        ),
    ]
    for model_cls, payload in cases:
        model_cls.model_validate(payload)  # 合法样例先通过
        smuggled = dict(payload)
        smuggled["golden_patch_content"] = "diff --git a/x b/x"
        with pytest.raises(ValidationError):
            model_cls.model_validate(smuggled)


async def test_governance_models_are_frozen():
    """构造后不可变（evidence 禁止事后篡改字段）。"""

    final = await run_finalize()
    with pytest.raises(ValidationError):
        final.group_repair_signal.degraded = True  # type: ignore[misc]
    frozen_scan = ProjectionScanResult.model_validate(
        {"trajectory_id": "traj_0001", "scanned_schema_id": "rh2.trajectory_projection.v1", "hits": [], "clean": True}
    )
    with pytest.raises(ValidationError):
        frozen_scan.clean = False  # type: ignore[misc]
