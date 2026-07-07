"""public projection 扫描（S1-5）：TrajectoryProjection 出站前的 forbidden marker 检查。

位置与职责（设计文档 2 §5.6"载体与执行位置"定案 3/4）：

- 本扫描运行在**双拓扑共享的唯一 finalize 关口**（`governance/wrapper.py` 的
  `finalize_rollout`）内部，扫描对象是即将交给训练后端 / 离线导出的
  `TrajectoryProjection`（public / 模型可见 / 训练可见的那一面）；
- EnvServer 出站扫描只是 service_driven 拓扑的**第二道防线**，不是唯一防线——
  trainer_native 直调路径不经过 EnvServer，但同样必须经过本关口；
- marker 名单**复用** `contracts/constants.py` 的 `FORBIDDEN_PUBLIC_MARKERS`
  （旧 L4/L5 + 补充条款 A6，共 23 项），本模块不自建第二份名单——
  两份名单迟早漂移，漂移就是漏报。

确定性（evidence 可复现比对的前提）：

1. 单串匹配层面：`find_forbidden_marker` 已按字典序遍历名单（S1-1b 定案）；
2. 结果层面：本模块把全部命中按 `(path, marker, kind)` 升序排序后写入
   `ProjectionScanResult.hits`，且校验器强制该顺序——同一份投影在任何机器、
   任何 PYTHONHASHSEED 下扫描，结果逐字节相同。

扫描结论如何进入资格判定：`ProjectionScanResult` 是 gate（`governance/gate.py`）
`security_and_leakage` 维度的事实输入之一——命中即该维 `ok=False`
（理由码 `public_projection_marker_hit`），schema 层再强制该结论只能落
`audit_only_or_rejected`。具体例子：投影的 reward components 里出现
key "fail_to_pass_bonus"，归一化后含 marker "fail_to_pass"，扫描产出
`path="$.reward_facts.components.fail_to_pass_bonus", kind="key"` 的命中，
该样本直接进 audit 档。

本模块的扫描函数是模块私有（`_scan_public_projection`）：S1-6 与一切编排代码
只准调 `finalize_rollout`，不准绕过 gate 单独"补扫"（见 wrapper 模块 docstring）。
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
    """一次 public projection 扫描的完整结论（gate security 维度的事实输入）。

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

    模块私有：只允许 `governance/wrapper.py` 的 finalize_rollout 调用
    （API 面测试钉住"wrapper 是唯一公开入口"）。
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
