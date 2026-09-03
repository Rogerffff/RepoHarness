"""rh2 治理层（S1-5）：训练资格门 + 唯一 finalize 关口（+ 两份冻结兼容 schema）。

模块分工：

- gate.py             TrainingEligibilityGate 本体：七维事实合取 -> 三档资格
                      （A3 起无封顶：七维全过即 online；Wave3 前置清理批起 security 维
                      只判执行级事实、policy_staleness 维只判"版本事实可用且合法"）、
                      组修复信号（GroupRepairSignal）。
- admission.py        W1b 第二段：交付面 typed admission 载荷（AdmissionPayloadV1）
                      + 三终态薄处置边界纯函数（decide_member_disposition）。
                      它**消费** gate 的产物（EligibilityReport），不是 gate 的
                      绕行路径——其公开函数由 API 面测试单独钉死。
- wrapper.py          唯一公开入口 `finalize_rollout`：把 grade -> project -> gate
                      固化为一次调用。
- projection_scan.py  **冻结兼容读路径**（D2-4，2026-09-04）：TrajectoryProjection 的
                      marker 扫描不再是资格语义，新 formal 链不再调用；类型保留给历史
                      S1 artifact / inspector 解析。真模型可见面的扫描在 envpack。
- sandbox_capability_facts.py
                      **冻结历史 schema**（D2-2，2026-09-04）：每轨迹能力事实证明系统已
                      删除，类型只保留给历史 evidence / 测试夹具解析，不进新 formal 链。

公开 API 纪律（§5.6 定案 3/4，API 面测试钉住）：本包**唯一**公开可调用
函数是 `finalize_rollout`。gate 的执行函数是模块私有（`_evaluate`），S1-6 编排与
一切下游代码不准散装调用——绕过关口的样本没有判定 evidence，视为违规路径。
其余公开名字全部是数据类型与常量（供类型标注、测试断言与 S1-9 inspector 用）。
"""

from __future__ import annotations

from repoharness2.governance.gate import (
    GATE_VERSION,
    GateInputError,
    GateOutcome,
    GroupRepairSignal,
)
from repoharness2.governance.projection_scan import (
    ProjectionMarkerHit,
    ProjectionScanResult,
)
from repoharness2.governance.sandbox_capability_facts import SandboxCapabilityFacts
from repoharness2.governance.wrapper import FinalizedRollout, finalize_rollout

__all__ = [
    "GATE_VERSION",
    "FinalizedRollout",
    "GateInputError",
    "GateOutcome",
    "GroupRepairSignal",
    "ProjectionMarkerHit",
    "ProjectionScanResult",
    "SandboxCapabilityFacts",
    "finalize_rollout",
]
