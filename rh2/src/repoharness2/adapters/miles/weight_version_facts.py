"""叶链 per-token 权重版本区间事实（vendor refresh V2，miles 边界侧）。

背景（adv_miles 反例）：sglang-miles（SGLANG_COMMIT=4e230c3d，模块
python/sglang/srt/utils/weight_versions.py）支持一条 /generate 请求跨多次
权重更新并在 `meta_info.weight_versions` 返回逐 token 版本区间，例如::

    [{"version": "10", "start": 0, "end": 300},
     {"version": "11", "start": 300, "end": 500}]

单数 `meta_info.weight_version="11"` 只表示最后一个区间。只记单数会把
v10+v11 的轮记成"全 v11"——miles `Sample.oldest_weight_version`（min）随之
高估、`DefaultDataBuffer` 的 staleness=current-oldest 低报，可能把本应被
`--max-weight-staleness` 拒绝的组放进训练。

分工（谁修什么）：

- **staleness 语义修复**走 `Sample.weight_versions` 本身——rh2 backfill
  （generate.py `backfill_leaf_sample`）把区间的全部版本依序并入该列表，
  canonicalize 原样复制，miles 的 oldest/min 与 buffer staleness 过滤自动
  恢复正确，**不需要**本模块参与。
- 本模块承载的是**结构化 provenance 证据**：逐入训轮的区间明细 + 记账
  provenance（engine_spans / single_version_only），供 G1 验收 judge 做
  "记账列表与引擎一手区间证据一致"的独立审计（低报在样本级只表现为
  版本列表变短，没有区间证据就无法从事件层看穿）。

机制（与 `sampling_mask_assembly.ATTACHED_MASK_ATTR` 完全同款）：backfill
构造 `LeafWeightVersionFacts` 挂到 vendor slime Sample 的附加属性
`rh2_weight_version_spans` 上；canonicalize 的 slime->miles 构造分支消费该
属性（类型校验 + 与 `weight_versions` 列表互检，fail-closed），转成纯 JSON
结构写进 miles `Sample.metadata["rh2_weight_version_spans"]`——metadata 不在
训练 wire 白名单（P0-3 已证不透传 trainer），但随 Sample 走完 buffer/
rollout_manager，`rollout_group` 验收事件从这里取证。

本模块纯 stdlib（dataclasses/typing），无 miles/slime/torch 依赖；slime 侧
backfill 按需 lazy import（`repoharness2.adapters.miles` 包 __init__ 依赖
miles checkout，无 spans 的既有 321 测试面不得被迫加载）。
"""

from __future__ import annotations

import dataclasses
from typing import Any

__all__ = [
    "ATTACHED_WEIGHT_VERSION_SPANS_ATTR",
    "LeafWeightVersionFacts",
    "TurnWeightVersionFact",
    "attach_leaf_weight_version_facts",
    "leaf_facts_to_metadata_payload",
]

# vendor slime Sample 上的附加属性名（canonicalize 允许集与消费点的唯一锚）。
ATTACHED_WEIGHT_VERSION_SPANS_ATTR = "rh2_weight_version_spans"

# metadata 落点键名（canonicalize 写入 miles Sample.metadata 的键；
# rollout_manager 的 rollout_group 事件按同名键取证）。
WEIGHT_VERSION_SPANS_METADATA_KEY = "rh2_weight_version_spans"


@dataclasses.dataclass(frozen=True)
class TurnWeightVersionFact:
    """一个入训轮的版本记账事实。

    - ``provenance="engine_spans"``：``spans`` 非 None（非空），每项为
      ``(version, start, end)``——半开区间 [start, end) 按该轮生成 token
      位置计数，来源 = 引擎 meta_info.weight_versions（capture 已校验：
      连续无缝隙无重叠、start=0、end=该轮生成 token 数、相邻版本不同）。
    - ``provenance="single_version_only"``：``spans`` 为 None，
      ``single_version`` 是该轮唯一记账版本（旧引擎单数回退；turn 内跨
      更新时该值只等于最后区间版本，低报形态由 provenance 显式声明）。
    """

    capture_record_id: str
    provenance: str
    spans: tuple[tuple[str, int, int], ...] | None
    single_version: str | None


@dataclasses.dataclass(frozen=True)
class LeafWeightVersionFacts:
    """整条叶链（一个 Sample）的逐入训轮版本区间事实（装配产物类型）。

    ``flat_versions`` = 逐轮逐区间展平后的版本序列，必须与 backfill 写进
    ``Sample.weight_versions`` 的列表**逐项相等**（canonicalize 消费时互检，
    两本账对不上 = 记账损坏，fail-closed）。
    """

    turns: tuple[TurnWeightVersionFact, ...]
    flat_versions: tuple[str, ...]

    def flatten_turn_versions(self) -> tuple[str, ...]:
        """按（轮次序, 区间序）重算展平版本序列（互检用）。"""

        flat: list[str] = []
        for turn in self.turns:
            if turn.spans is not None:
                flat.extend(version for version, _start, _end in turn.spans)
            elif turn.single_version is not None:
                flat.append(turn.single_version)
        return tuple(flat)


def attach_leaf_weight_version_facts(slime_sample: Any, facts: LeafWeightVersionFacts) -> None:
    """把装配产物挂到 vendor slime Sample 的附加属性上（backfill 调用）。

    与 `attach_assembled_mask` 同款：canonicalize 的 slime 分支是唯一消费者，
    消费后不进 miles 对象 __dict__ 外挂（转 metadata 落点）。
    """

    if not isinstance(facts, LeafWeightVersionFacts):
        raise TypeError(
            f"attach_leaf_weight_version_facts 只接受 LeafWeightVersionFacts，"
            f"got {type(facts).__name__}"
        )
    setattr(slime_sample, ATTACHED_WEIGHT_VERSION_SPANS_ATTR, facts)


def leaf_facts_to_metadata_payload(facts: LeafWeightVersionFacts) -> list[dict[str, Any]]:
    """装配产物 -> 纯 JSON 结构（canonicalize 写 metadata 的 wire 形态）。

    形态（rollout_group 事件与 G1 judge 的消费合同）::

        [{"capture_record_id": "cap_..._t0",
          "provenance": "engine_spans",
          "spans": [{"version": "10", "start": 0, "end": 300},
                    {"version": "11", "start": 300, "end": 500}],
          "version": "11"},                      # 单数 = finalize 时刻值
         {"capture_record_id": "cap_..._t1",
          "provenance": "single_version_only",
          "spans": None,
          "version": "11"}]
    """

    payload: list[dict[str, Any]] = []
    for turn in facts.turns:
        payload.append(
            {
                "capture_record_id": turn.capture_record_id,
                "provenance": turn.provenance,
                "spans": (
                    [
                        {"version": version, "start": start, "end": end}
                        for version, start, end in turn.spans
                    ]
                    if turn.spans is not None
                    else None
                ),
                "version": (
                    turn.spans[-1][0] if turn.spans else turn.single_version
                ),
            }
        )
    return payload
