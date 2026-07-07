"""rh2 治理层（S1-5）：训练资格门 + public projection 扫描 + 唯一 finalize 关口。

模块分工：

- gate.py             TrainingEligibilityGate 本体：七维事实合取 -> 三档资格，
                      S1 封顶（S1_TIER_CAP）、组修复信号（GroupRepairSignal）。
- projection_scan.py  public projection 泄漏扫描（marker 名单复用
                      contracts/constants.py，确定性排序）。
- wrapper.py          唯一公开入口 `finalize_rollout`：把
                      grade -> project -> scan -> gate 固化为一次调用。

公开 API 纪律（§5.6 定案 3/4，API 面测试钉住）：本包**唯一**公开可调用
函数是 `finalize_rollout`。gate 与 projection_scan 的执行函数都是模块私有
（`_evaluate` / `_scan_public_projection`），S1-6 编排与一切下游代码不准
散装调用——绕过关口的样本没有扫描与判定 evidence，视为违规路径。
其余公开名字全部是数据类型与常量（供类型标注、测试断言与 S1-9 inspector 用）。
"""

from __future__ import annotations

from repoharness2.governance.gate import (
    GATE_VERSION,
    S1_CEILING_REASON_CODE,
    S1_TIER_CAP,
    GateInputError,
    GateOutcome,
    GroupRepairSignal,
)
from repoharness2.governance.projection_scan import (
    ProjectionMarkerHit,
    ProjectionScanResult,
)
from repoharness2.governance.wrapper import FinalizedRollout, finalize_rollout

__all__ = [
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
]
