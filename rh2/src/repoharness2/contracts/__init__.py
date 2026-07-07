"""rh2 治理层契约（S1-1）：pydantic v2 严格 schema 全家桶。

九个契约模块 + 公共底座：

- trajectory.py  中立轨迹投影（治理层唯一消费的轨迹形态）
- capture.py     GenerationCaptureRecord（SGLang 客户端响应层原始事实 sidecar，A4）
- eligibility.py 三档资格 + 七维事实 EligibilityReport（§5.6 载体定案）
- grading.py     GradingReport + 失败归因三分 + patch hygiene（A7）
- findings.py    AntiCheatFinding / TrajectoryQualityFinding（attempted|executed）
- anti_hack.py   AntiHackEvent（block + dummy 观测 + 继续）
- sandbox.py     sandbox 所有权握手五对象（A5 八问）
- handshake.py   BackendHandshake（policy 版本 / staleness / 组信号）
- timing.py      GradingTimingRecord（F5 五类计时 + 容器峰值/队列等待）
- constants.py   FORBIDDEN_PUBLIC_MARKERS + 泄漏扫描（旧 L4/L5 + A6）

`SCHEMA_REGISTRY` 把每个顶层对象的 schema_id 映射到模型类，
`inspect-rh2-artifact`（repoharness2.cli）按它做"读 JSON -> 判类型 -> 校验"。
"""

from __future__ import annotations

from repoharness2.contracts._base import (
    ArtifactRef,
    NonEmptyStr,
    SafeIdentifier,
    Sha256Digest,
    StrictModel,
    canonical_json_digest,
)
from repoharness2.contracts.anti_hack import AntiHackEvent
from repoharness2.contracts.capture import (
    CaptureSamplingParams,
    GenerationCaptureRecord,
)
from repoharness2.contracts.constants import (
    FORBIDDEN_PUBLIC_MARKERS,
    MarkerHit,
    find_forbidden_marker,
    scan_for_forbidden_markers,
)
from repoharness2.contracts.eligibility import (
    DimensionFact,
    EligibilityFacts,
    EligibilityReport,
    TrainingEligibilityClass,
    compute_facts_digest,
)
from repoharness2.contracts.findings import (
    AntiCheatFinding,
    TrajectoryQualityFinding,
)
from repoharness2.contracts.grading import (
    INFRA_FAILURE_CATEGORIES,
    GradingFailureCategory,
    GradingReport,
    PatchHygieneResult,
)
from repoharness2.contracts.handshake import BackendHandshake, GroupSignal
from repoharness2.contracts.sandbox import (
    BundleMount,
    CleanupPolicy,
    HarnessLaunchSpec,
    ModelProxyEndpoint,
    SandboxLease,
    WorkspaceHandle,
)
from repoharness2.contracts.timing import GradingTimingRecord
from repoharness2.contracts.trajectory import (
    BranchProjection,
    CompactedSubTraceLineage,
    LogprobProvenance,
    LossMaskSpan,
    RewardFacts,
    RoutingTensorRef,
    SamplingMaskRef,
    TokenSpan,
    TrajectoryProjection,
)

# schema_id -> 模型类。inspect-rh2-artifact 的类型判别表。
SCHEMA_REGISTRY: dict[str, type[StrictModel]] = {
    "rh2.trajectory_projection.v1": TrajectoryProjection,
    "rh2.generation_capture_record.v1": GenerationCaptureRecord,
    "rh2.eligibility_report.v1": EligibilityReport,
    "rh2.grading_report.v1": GradingReport,
    "rh2.grading_timing_record.v1": GradingTimingRecord,
    "rh2.anti_cheat_finding.v1": AntiCheatFinding,
    "rh2.trajectory_quality_finding.v1": TrajectoryQualityFinding,
    "rh2.anti_hack_event.v1": AntiHackEvent,
    "rh2.sandbox_lease.v1": SandboxLease,
    "rh2.workspace_handle.v1": WorkspaceHandle,
    "rh2.harness_launch_spec.v1": HarnessLaunchSpec,
    "rh2.model_proxy_endpoint.v1": ModelProxyEndpoint,
    "rh2.cleanup_policy.v1": CleanupPolicy,
    "rh2.backend_handshake.v1": BackendHandshake,
}

# runtime-private 审计资产：内容天然要描述作弊/私有事实（例如 finding 描述
# "agent 试图 cat test_patch"），默认豁免 marker 扫描；但它们永远不得进入
# public projection——那一侧的扫描不看本豁免表。
MARKER_SCAN_EXEMPT_SCHEMAS: frozenset[str] = frozenset(
    {
        "rh2.grading_report.v1",
        "rh2.anti_cheat_finding.v1",
        "rh2.trajectory_quality_finding.v1",
        "rh2.anti_hack_event.v1",
    }
)

__all__ = [
    "ArtifactRef",
    "NonEmptyStr",
    "SafeIdentifier",
    "Sha256Digest",
    "StrictModel",
    "canonical_json_digest",
    "AntiHackEvent",
    "CaptureSamplingParams",
    "GenerationCaptureRecord",
    "FORBIDDEN_PUBLIC_MARKERS",
    "MarkerHit",
    "find_forbidden_marker",
    "scan_for_forbidden_markers",
    "DimensionFact",
    "EligibilityFacts",
    "EligibilityReport",
    "TrainingEligibilityClass",
    "compute_facts_digest",
    "AntiCheatFinding",
    "TrajectoryQualityFinding",
    "GradingFailureCategory",
    "GradingReport",
    "INFRA_FAILURE_CATEGORIES",
    "PatchHygieneResult",
    "BackendHandshake",
    "GroupSignal",
    "BundleMount",
    "CleanupPolicy",
    "HarnessLaunchSpec",
    "ModelProxyEndpoint",
    "SandboxLease",
    "WorkspaceHandle",
    "GradingTimingRecord",
    "BranchProjection",
    "CompactedSubTraceLineage",
    "LogprobProvenance",
    "LossMaskSpan",
    "RewardFacts",
    "RoutingTensorRef",
    "SamplingMaskRef",
    "TokenSpan",
    "TrajectoryProjection",
    "SCHEMA_REGISTRY",
    "MARKER_SCAN_EXEMPT_SCHEMAS",
]
