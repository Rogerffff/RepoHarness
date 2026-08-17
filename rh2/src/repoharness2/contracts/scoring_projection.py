"""B3（F2-2b 重构切片）：hygiene 分类 + ScoringProjectionArtifact。

A-prime T0 第 5 条：raw FrozenPatchArtifact 先过 schema/digest/baseline/
hygiene/security 检查，之后才产生 grading projection；projection 是
**引用** raw entries 的派生 manifest（不复制内容，不成为第二本事实账）。
第 6 条：runtime 私有面变化只记事实；tamper 判定需权限/命令/ownership
证据（v1 无此证据源 → 只记录，不判 tamper）。

v1 分类规则（递延扩充已登记）：
- unsafe：patch entry 落在排除 namespace（结构矛盾——exporter 按政策
  prune，出现即 artifact 畸形）；symlink target 逃逸（绝对路径 / ..
  段——应用到干净 checkout 后可指向树外，私测注入前的隔离击穿面）。
- projectable：其余全部 entry 按引用进入 projection。
"""

from __future__ import annotations

import base64
from typing import Literal

from pydantic import Field, model_validator

from ._base import NonEmptyStr, Sha256Digest, StrictModel
from .frozen_patch import FrozenPatchArtifactV1

__all__ = [
    "HygieneReport",
    "ScoringProjectionArtifactV1",
    "classify_frozen_patch",
]


class HygieneReport(StrictModel):
    """hygiene/security 分类结果（B3 唯一判定载体）。"""

    verdict: Literal["projectable", "unsafe_artifact"] = Field(description="判定。")
    reason_codes: tuple[NonEmptyStr, ...] = Field(
        default=(), description="unsafe 时至少一条（unsafe_symlink_escape 等）。"
    )
    runtime_private_pathset_changed: bool = Field(
        description="排除区路径集合变化事实（**不是 tamper 判定**——A-prime 6）。"
    )

    @model_validator(mode="after")
    def _check(self) -> "HygieneReport":
        if self.verdict == "unsafe_artifact" and not self.reason_codes:
            raise ValueError("unsafe_artifact 必须携带 reason_codes。")
        if self.verdict == "projectable" and self.reason_codes:
            raise ValueError("projectable 不得携带 unsafe reason_codes。")
        return self


class ScoringProjectionArtifactV1(StrictModel):
    """grader 被允许消费的 delta——**按引用**（路径列表 + raw digest 锚），
    不复制内容；消费方经锚取 raw entries。"""

    schema_id: Literal["rh2.fa.scoring_projection.v1"] = Field(
        default="rh2.fa.scoring_projection.v1", description="schema 判别字段。"
    )
    frozen_patch_digest: Sha256Digest = Field(description="raw artifact 身份锚。")
    rollout_execution_id: NonEmptyStr = Field(description="逻辑执行 id。")
    physical_attempt_id: NonEmptyStr = Field(description="物理 attempt id。")
    included_entry_paths: tuple[NonEmptyStr, ...] = Field(
        description="进入评分的 raw entry 路径（排序唯一；引用不复制）。"
    )

    @model_validator(mode="after")
    def _check(self) -> "ScoringProjectionArtifactV1":
        if list(self.included_entry_paths) != sorted(set(self.included_entry_paths)):
            raise ValueError("included_entry_paths 必须排序且唯一。")
        return self


def _symlink_target_escapes(target: bytes) -> bool:
    text = target.decode("utf-8", errors="replace")
    if text.startswith("/"):
        return True
    return any(seg == ".." for seg in text.split("/"))


def classify_frozen_patch(
    artifact: FrozenPatchArtifactV1,
    *,
    excluded_namespaces: tuple[str, ...],
    frozen_patch_digest: str,
) -> tuple[HygieneReport, ScoringProjectionArtifactV1 | None]:
    """分类 raw artifact；projectable 时出具引用式 projection，unsafe 时
    projection = None（不运行 grader——A-prime 失败表 unsafe 行）。"""

    reasons: list[str] = []
    for e in artifact.entries:
        for ns in excluded_namespaces:
            if e.path == ns.rstrip("/") or e.path.startswith(ns):
                reasons.append(f"entry_in_excluded_namespace:{e.path}")
        if e.object_type == "symlink" and e.operation != "delete":
            target = base64.b64decode(e.content_b64 or "", validate=True)
            if _symlink_target_escapes(target):
                reasons.append(f"unsafe_symlink_escape:{e.path}")
    if reasons:
        report = HygieneReport(
            verdict="unsafe_artifact",
            reason_codes=tuple(sorted(set(reasons))),
            runtime_private_pathset_changed=artifact.excluded_pathset_changed,
        )
        return report, None
    report = HygieneReport(
        verdict="projectable",
        runtime_private_pathset_changed=artifact.excluded_pathset_changed,
    )
    projection = ScoringProjectionArtifactV1(
        frozen_patch_digest=frozen_patch_digest,
        rollout_execution_id=artifact.rollout_execution_id,
        physical_attempt_id=artifact.physical_attempt_id,
        included_entry_paths=tuple(e.path for e in artifact.entries),
    )
    return report, projection
