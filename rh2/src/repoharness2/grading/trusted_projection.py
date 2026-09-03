"""W3a（决策包 D2-3，owner 2026-09-04 已批）：可信评分投影——把 FrozenPatchArtifact 拆成
`candidate_solution_delta`（重放到 fresh grader）与 `ignored_validation_delta`（测试/评分控制面，
**不重放**，只记录）。

公共不变量（D2-3 原文）：agent 对测试与评分控制面的修改**不能对最终 reward 产生因果影响**；
不判断意图，不因测试路径变化自动 DROP_GROUP、也不再当作 unsafe artifact。做法是"排除法"：
控制面之外的每一个 entry 都重放；控制面 entry 一个都不重放；grader 之后自己后写 official
test_patch、跑可信 eval_cmd，正常产出 0/1。

首训口径（owner 细化"暂按当前 SWE adapter 实现"）：控制面 = 当前 SWE adapter 的 `HygieneRules`
三类规则，按优先级分类（一条路径只记一个类别，供遥测分布统计）：

    official_test_file   official test_patch 触碰的精确文件（HygieneRules.test_files）
    test_glob            测试文件通配命中（HygieneRules.test_globs，如 *tests/*、test_*.py）
    reserved_namespace   rh2 保留路径（HygieneRules.forbidden_globs = .rh2* / rh2/*）——这是
                         **命名空间冲突**，不进投影，但**不**宣称安全边界被突破（D2-3 原文）

已知不足（登记不修，等 taskset 定后由 environment adapter 声明通用控制面）：conftest.py /
pytest.ini / tox.ini / setup.cfg·pyproject 的 pytest 段 / 插件 / 启动脚本等真正能改变测试收集
的文件并不在上述规则内，本批不设计通用规则引擎。

**仍是 infra/security failure、不进本投影**（由 contracts.scoring_projection.classify_frozen_patch
在本模块之前判定）：symlink escape、FIFO/device 等结构不安全 artifact、排除 namespace 内的 entry。

信任边界：本模块是纯函数，producer（adapters/slime/generate.py）用它出具投影，grader
（grading/manager.py `_verify_frozen_delta_binding`）用**同一函数**对 artifact 独立重算并要求
投影路径集与重算结果**完全相等**——投影既不能"隐去"solution 路径（少了会被发现），也不能
"夹带"控制面路径（多了同样会被发现），两者都是 run-halt 级契约矛盾，不是成员损耗。
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from repoharness2.contracts.frozen_patch import (
    FrozenPatchArtifactV1,
    PatchEntry,
    compute_frozen_patch_digest,
)
from repoharness2.contracts.scoring_projection import ScoringProjectionArtifactV1

__all__ = [
    "TRUSTED_PROJECTION_RULE_VERSION",
    "ControlPlaneClass",
    "ControlPlaneRules",
    "IgnoredValidationEntry",
    "TrustedProjectionSplit",
    "build_trusted_scoring_projection",
    "classify_control_plane_path",
    "expected_candidate_paths",
    "split_trusted_scoring_projection",
]

# 投影规则版本：随 audit/sidecar 落盘，日后换通用控制面定义时可区分"按哪套规则拆的"。
TRUSTED_PROJECTION_RULE_VERSION = "rh2.trusted_scoring_projection.swe_hygiene.v1"

ControlPlaneClass = Literal["official_test_file", "test_glob", "reserved_namespace"]

# Outcome v2 evidence_refs 里逐条列出的被忽略路径上限——超出部分只在 audit/sidecar 记录全量，
# evidence 里用 `ignored_validation_delta_truncated:<余量>` 标注（Outcome 是每条 attempt 都要
# 持久化的小记录，不该被一个改了几百个测试文件的 patch 撑爆）。
EVIDENCE_IGNORED_PATH_LIMIT = 50


class ControlPlaneRules(Protocol):
    """`grading.manager.HygieneRules` 的鸭子形状（本模块不 import manager，避免成环）。"""

    test_files: tuple[str, ...]
    test_globs: tuple[str, ...]
    forbidden_globs: tuple[str, ...]

    def is_test_path(self, path: str) -> bool: ...

    def is_forbidden_path(self, path: str) -> bool: ...


def classify_control_plane_path(rules: ControlPlaneRules, path: str) -> ControlPlaneClass | None:
    """路径属于控制面则返回类别（优先级 official > glob > reserved），否则 None（= solution surface）。"""

    if path in rules.test_files:
        return "official_test_file"
    if rules.is_test_path(path):
        return "test_glob"
    if rules.is_forbidden_path(path):
        return "reserved_namespace"
    return None


@dataclass(frozen=True)
class IgnoredValidationEntry:
    """一条被忽略（不重放）的控制面改动：只记路径/操作/对象类型/类别，不带内容——内容仍在
    完整 FrozenPatchArtifact 里供审计。"""

    path: str
    operation: str  # add / modify / delete
    object_type: str  # regular / symlink
    control_plane_class: ControlPlaneClass

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "operation": self.operation,
            "object_type": self.object_type,
            "control_plane_class": self.control_plane_class,
        }


@dataclass(frozen=True)
class TrustedProjectionSplit:
    """拆分结果（纯值对象）：candidate entries 按 path 排序、ignored entries 按 path 排序，
    两者路径集不相交且并集 = 输入 entries 路径集。"""

    candidate_entries: tuple[PatchEntry, ...]
    ignored_entries: tuple[IgnoredValidationEntry, ...]
    rule_version: str = TRUSTED_PROJECTION_RULE_VERSION

    @property
    def candidate_paths(self) -> tuple[str, ...]:
        return tuple(e.path for e in self.candidate_entries)

    @property
    def ignored_paths(self) -> tuple[str, ...]:
        return tuple(e.path for e in self.ignored_entries)

    def ignored_counts_by_class(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "official_test_file": 0, "test_glob": 0, "reserved_namespace": 0,
        }
        for e in self.ignored_entries:
            counts[e.control_plane_class] += 1
        return counts

    def evidence_refs(self) -> list[str]:
        """写进 Outcome v2 evidence_refs 的紧凑形态（NonEmptyStr 列表）。"""

        refs = [
            f"trusted_projection:{self.rule_version}",
            f"trusted_projection:candidate={len(self.candidate_entries)}"
            f":ignored={len(self.ignored_entries)}",
        ]
        for e in self.ignored_entries[:EVIDENCE_IGNORED_PATH_LIMIT]:
            refs.append(
                f"ignored_validation_delta:{e.control_plane_class}:{e.operation}:{e.path}"
            )
        overflow = len(self.ignored_entries) - EVIDENCE_IGNORED_PATH_LIMIT
        if overflow > 0:
            refs.append(f"ignored_validation_delta_truncated:{overflow}")
        return refs

    def to_record(self) -> dict[str, Any]:
        """审计 / sidecar 落盘形态（全量路径清单 + 计数）。"""

        return {
            "rule_version": self.rule_version,
            "candidate_solution_paths": list(self.candidate_paths),
            "candidate_solution_count": len(self.candidate_entries),
            "ignored_validation_entries": [e.to_dict() for e in self.ignored_entries],
            "ignored_validation_count": len(self.ignored_entries),
            "ignored_validation_counts_by_class": self.ignored_counts_by_class(),
        }


def split_trusted_scoring_projection(
    entries: Iterable[PatchEntry], rules: ControlPlaneRules
) -> TrustedProjectionSplit:
    """排除法拆分：控制面 entry → ignored（不重放），其余全部 → candidate（重放）。纯函数。"""

    candidate: list[PatchEntry] = []
    ignored: list[IgnoredValidationEntry] = []
    for e in sorted(entries, key=lambda x: x.path):
        cls = classify_control_plane_path(rules, e.path)
        if cls is None:
            candidate.append(e)
        else:
            ignored.append(
                IgnoredValidationEntry(
                    path=e.path, operation=e.operation, object_type=e.object_type,
                    control_plane_class=cls,
                )
            )
    return TrustedProjectionSplit(
        candidate_entries=tuple(candidate), ignored_entries=tuple(ignored),
    )


def build_trusted_scoring_projection(
    artifact: FrozenPatchArtifactV1, rules: ControlPlaneRules
) -> tuple[ScoringProjectionArtifactV1, TrustedProjectionSplit]:
    """从 projectable 的 raw artifact 出具**只引用 candidate_solution 路径**的
    ScoringProjectionArtifactV1（契约对象，digest 锚 = artifact 重算 digest）+ 拆分记录。

    前置条件：调用方已用 contracts.scoring_projection.classify_frozen_patch 判定 artifact 为
    projectable（结构不安全的 artifact 不会走到这里）。"""

    split = split_trusted_scoring_projection(artifact.entries, rules)
    projection = ScoringProjectionArtifactV1(
        frozen_patch_digest=compute_frozen_patch_digest(artifact),
        rollout_execution_id=artifact.rollout_execution_id,
        physical_attempt_id=artifact.physical_attempt_id,
        included_entry_paths=split.candidate_paths,
    )
    return projection, split


def expected_candidate_paths(entries: Sequence[PatchEntry], rules: ControlPlaneRules) -> set[str]:
    """grader 侧独立重算：给定 artifact entries 与规则，投影**应当**包含的路径集。"""

    return set(split_trusted_scoring_projection(entries, rules).candidate_paths)
