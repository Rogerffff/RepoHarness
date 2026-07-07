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
from repoharness2.governance import gate, projection_scan, wrapper


def test_governance_public_api_is_exact():
    """governance 包公开面精确钉死：新增公开名字必须显式改本测试（防 API 面漂移）。"""

    assert set(governance.__all__) == {
        "GATE_VERSION",
        "S1_CEILING_REASON_CODE",
        "S1_TIER_CAP",
        "FinalizedRollout",
        "GateInputError",
        "GateOutcome",
        "GroupRepairSignal",
        "ProjectionMarkerHit",
        "ProjectionScanResult",
        "finalize_rollout",
    }


def test_finalize_rollout_is_the_only_public_callable():
    """三个模块里本模块定义的公开函数只有 wrapper.finalize_rollout 一个——
    "直接调 gate/scan 绕过 wrapper"的路径不存在于公开 API 面。"""

    public_functions: set[str] = set()
    for module in (gate, projection_scan, wrapper):
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
        (ProjectionScanResult, final.scan_result.model_dump(mode="json")),
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
    with pytest.raises(ValidationError):
        final.scan_result.clean = False  # type: ignore[misc]
