"""public projection 扫描（S1-5）——**冻结兼容读路径，不再是资格语义**。

状态（Wave3 前置清理批，决策包 D2-4，owner 2026-09-04 已批）：

- 本模块曾运行在唯一 finalize 关口（`governance/wrapper.py`）内部，扫描
  `TrajectoryProjection` 并把命中作为 security 维事实（理由码
  `public_projection_marker_hit` → audit 档 / admission DROP_GROUP）。这条资格语义
  已删除：`TrajectoryProjection` 是 rollout 结束后的 trainer / offline-export 中立投影
  （token 计数 / span / mask / 引用 / reward facts / 版本握手），**不是模型可见输入**；
  扫描发生在 rollout 与评分之后、不解引用 token/artifact 内容，测不到 prompt / mount /
  env / 工具输出里的泄漏，却会因 `fail_to_pass_bonus` 这类字段名误报丢整组。
- 现在 `finalize_rollout` 不再调用 `_scan_public_projection`，`FinalizedRollout` 没有
  `scan_result` 字段，gate / admission / offline exporter 都不消费扫描结论。
  `ProjectionScanResult` / `ProjectionMarkerHit` 保留为**冻结 schema**，供历史 S1
  artifact（`experiments/s1_7a_bringup/export_sample.py` 之类的重算脚本）与 inspector
  解析；`_scan_public_projection` 保留为同一确定性算法的只读实现。
- 真模型可见面的 marker 扫描**原样保留且仍是拒绝面**：envpack 的
  `PublicTaskBundle`（bundles.py）、`RolloutTaskView`（training_view.py）、prepared
  任务公开产物（prepared_tasks.py）都对整树调 `contracts.scan_for_forbidden_markers`，
  命中即拒。hidden / grader 泄漏的主验证改为结构与数据流证据 + canary 反例（W3b）。

历史设计口径（保留供解读旧文档）：marker 名单**复用** `contracts/constants.py` 的
`FORBIDDEN_PUBLIC_MARKERS`（旧 L4/L5 + 补充条款 A6，共 23 项），本模块不自建第二份
名单——两份名单迟早漂移，漂移就是漏报。

确定性（evidence 可复现比对的前提）：

1. 单串匹配层面：`find_forbidden_marker` 已按字典序遍历名单（S1-1b 定案）；
2. 结果层面：本模块把全部命中按 `(path, marker, kind)` 升序排序后写入
   `ProjectionScanResult.hits`，且校验器强制该顺序——同一份投影在任何机器、
   任何 PYTHONHASHSEED 下扫描，结果逐字节相同。

扫描结论（历史）曾如何进入资格判定：命中即 security 维 `ok=False`（理由码
`public_projection_marker_hit`），schema 层再强制该结论只能落 `audit_only_or_rejected`。
具体例子：投影的 reward components 里出现 key "fail_to_pass_bonus"，归一化后含 marker
"fail_to_pass"，扫描产出 `path="$.reward_facts.components.fail_to_pass_bonus", kind="key"`
的命中——D2-4 之后这只是一条可复算的观测记录，**不再影响**资格、组准入与导出。

本模块的扫描函数保持模块私有（`_scan_public_projection`）：它不是新 formal 链的一环，
只有历史 artifact 重算脚本按同一算法复算时才引用。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from repoharness2.contracts import (
    NonEmptyStr,
    StrictModel,
    TrajectoryProjection,
    scan_for_forbidden_markers,
)

__all__ = [
    "ProjectionMarkerHit",
    "ProjectionScanResult",
]


class ProjectionMarkerHit(StrictModel):
    """一次 marker 命中的结构化记录（constants.MarkerHit 的契约化形态）。"""

    path: NonEmptyStr = Field(
        description="命中位置的 JSON path（如 $.reward_facts.components.fail_to_pass_bonus）。"
    )
    marker: NonEmptyStr = Field(
        description="命中的 marker 原文（FORBIDDEN_PUBLIC_MARKERS 中的项，如 fail_to_pass）。"
    )
    kind: Literal["key", "value"] = Field(
        description="命中发生在 dict key 还是字符串 value 上。"
    )


class ProjectionScanResult(StrictModel):
    """一次 public projection 扫描的完整结论（冻结 schema；D2-4 起不再是 gate 事实输入）。

    fail-closed 校验清单：
    1. `clean` 是派生结论，必须等于 `len(hits) == 0` 的重算值
       （派生视图互检范式：说"干净"却带着命中列表的结果不可表示）；
    2. `hits` 必须按 (path, marker, kind) 升序——乱序结果说明生产者
       没有走确定性排序路径，拒收。
    """

    scanner: Literal["rh2.public_projection_marker_scan.v1"] = Field(
        default="rh2.public_projection_marker_scan.v1",
        description="扫描器版本判别字段（升级扫描语义必须换版本号）。",
    )
    trajectory_id: NonEmptyStr = Field(description="被扫描投影的轨迹 id。")
    scanned_schema_id: NonEmptyStr = Field(
        description="被扫描对象的 schema_id（S1 恒为 rh2.trajectory_projection.v1）。"
    )
    hits: list[ProjectionMarkerHit] = Field(
        default_factory=list,
        description="全部 marker 命中，按 (path, marker, kind) 升序（空列表 = 干净）。",
    )
    clean: bool = Field(description="是否零命中（派生结论，校验器强制与 hits 一致）。")

    @model_validator(mode="after")
    def _check_scan_contract(self) -> "ProjectionScanResult":
        if self.clean != (len(self.hits) == 0):
            raise ValueError(
                f"clean({self.clean}) 与 hits 数量({len(self.hits)}) 不一致"
                "（派生视图互检失败：扫描结论与命中列表必须账实相符）。"
            )
        keys = [(hit.path, hit.marker, hit.kind) for hit in self.hits]
        if keys != sorted(keys):
            raise ValueError(
                "hits 必须按 (path, marker, kind) 升序排序（确定性要求："
                "同一投影在任何进程下扫描结果逐字节一致），得到乱序列表。"
            )
        return self

    def evidence_refs(self) -> list[str]:
        """生成写入 DimensionFact.evidence_refs 的证据引用串。

        干净时也要留痕（"扫描确实跑过"必须在 EligibilityReport 里可见，
        否则无法区分"扫过且干净"与"根本没扫"）：
        例：["public_projection_scan:clean:rh2.trajectory_projection.v1"]。
        """

        if self.clean:
            return [f"public_projection_scan:clean:{self.scanned_schema_id}"]
        return [
            f"public_projection_scan:hit:{hit.path}:{hit.marker}:{hit.kind}"
            for hit in self.hits
        ]


def _scan_public_projection(projection: TrajectoryProjection) -> ProjectionScanResult:
    """扫描一个 TrajectoryProjection 的 JSON 形态，产出确定性排序的扫描结论。

    冻结兼容实现（D2-4）：新 formal 链不调用；保留给历史 artifact 的确定性重算
    （API 面测试仍钉住它是模块私有、不经包级转出）。
    """

    raw_hits = scan_for_forbidden_markers(projection.model_dump(mode="json"))
    ordered = sorted(raw_hits, key=lambda hit: (hit.path, hit.marker, hit.kind))
    return ProjectionScanResult(
        trajectory_id=projection.trajectory_id,
        scanned_schema_id=projection.schema_id,
        hits=[
            ProjectionMarkerHit(path=hit.path, marker=hit.marker, kind=hit.kind)
            for hit in ordered
        ],
        clean=not ordered,
    )
