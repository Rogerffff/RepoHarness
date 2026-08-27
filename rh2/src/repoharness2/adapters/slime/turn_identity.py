"""F1 身份制修复的叶侧一步：树走查导出身份 span（finding §3，2026-08-27 拍板）。

背景：TrajectoryManager 把消息树线性化成叶链 Sample 时丢弃 turn 身份
（`get_trajectory` 只产 tokens/loss_mask/logprobs），此前 bringup 给每个
leaf 附"全部 session capture id"，`_match_turns_to_runs` 再用 output_ids
内容反推归属——内容不是单射（重复短输出、工具后固定确认语、rewrite 掉落
轮与活轮同 token），会把活轮绑到已掉落旧轮的 capture/weight_version/
support（P0 静默串账，反例 [11,21,21] 见 finding §3.2）。

本模块承担身份正向流动的叶侧一步：finish 之后拿住树根引用
（get_trajectory 弹树，但树对象仍被引用持有），**只读**重放 vendor 的
线性化算法——直接驱动 vendor `_SampleBuilder`（不复刻 drift 判定，消灭
两套账），同时记录每个 trained 响应段在最终样本座标系里的
(起点, 长度, turn_index)。重放产物与真实 samples 逐 token 对账
（tokens/loss_mask 全等），任何漂移 fail-closed——身份 span 因此保证与
vendor 输出同源。turn_index → capture_record_id 的解析走
CaptureRegistry 的 commit 时刻绑定账（capture_wire.bind_turn_identity）。

树语义要点（与设计三步逐条对应）：
- REALIGN 掉落轮：`_align_to_prompt` 整段覆盖上一响应 span（mask=0），
  被覆盖的 trained span 从身份账中移除——天然不在叶 span 里；
- rewrite-merge 掉落轮：节点被降级 routing-only（turn=None），根本不进
  asst_nodes——同样天然不在；
- FORK 分支：每条叶链只含自身前缀链的轮；共享前缀轮只被第一条叶链
  train（response_trained 首领语义，这里用自有 claimed 集合等价重放——
  get_trajectory 入口处该标志恒为 False，重放顺序与 vendor 相同即忠实）；
- 相邻多轮连成一个 mask=1 段时，span 连续排列，段边界由 span 平铺校验
  （generate._runs_from_identity_spans）兜底。

vendor `rh2/src/slime/agent/trajectory.py` 只读不改字节；本模块 import 其
`_SampleBuilder`/`DriftKind`（下划线名，vendor 刻意模块级可达）在函数内
惰性完成——tests/adapters 老世界（reference/slime path）不受影响。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from repoharness2.adapters.slime.generate import (
    RH2_TURN_IDENTITY_SPANS_ATTR,
    SlimeBindingError,
    TurnIdentitySpan,
)

__all__ = [
    "LeafIdentityExport",
    "attach_turn_identity_spans",
    "export_leaf_identity_spans",
]


@dataclass(frozen=True)
class LeafIdentityExport:
    """一条（重放出的）叶链样本的身份事实。

    ``tokens``/``loss_mask`` 与 vendor ``_SampleBuilder.to_sample`` 的产物
    同形（tokens 为截断后的完整序列，loss_mask 已剥掉首轮 prompt），供
    调用方与真实 Sample 对账；``spans`` 是 response 座标系（loss_mask
    座标系）里的 (起点, 长度, 树 turn_index) 序列，按位置升序。
    """

    tokens: list[int]
    loss_mask: list[int]
    response_start: int  # leading_prompt_len（截断前全序列座标）
    spans: tuple[tuple[int, int, int], ...]  # (response 起点, 长度, turn_index)


def export_leaf_identity_spans(
    root: Any, *, fork_threshold: int, max_sample_tokens: int = 0
) -> list[LeafIdentityExport]:
    """只读重放 vendor 线性化，导出每条叶链样本的身份 span。

    ``root`` = TrajectoryManager 某 sid 的树根（MessageNode；get_trajectory
    弹树前后皆可——树结构在 finish 时已定型，get_trajectory 只翻
    response_trained 标志，本函数不读该标志）。返回列表与
    ``get_trajectory`` 产出的样本一一对应（同序、同过滤：无 trained
    响应的 builder 不产样本）。
    """

    from slime.agent.trajectory import DriftKind, _SampleBuilder

    exports: list[LeafIdentityExport] = []
    claimed: set[int] = set()  # id(node)：response_trained 首领语义的等价重放
    for routing_leaf in root.leaves():
        if routing_leaf.is_root:
            continue
        chain = routing_leaf.path_from_root()
        asst_nodes = [
            n for n in chain if n.role == "assistant" and n.turn is not None
        ]

        builders: list[Any] = []
        spans_per_builder: list[list[tuple[int, int, int]]] = []
        for node in asst_nodes:
            trained = id(node) not in claimed
            claimed.add(id(node))
            # 与 vendor _split_chain_into_builders 逐行同构：FORK 开新
            # builder 并按 CLEAN 追加；否则按判定的 CLEAN/REALIGN 追加。
            if (
                not builders
                or (kind := builders[-1].classify_token_drift(node.turn))
                is DriftKind.FORK
            ):
                builders.append(_SampleBuilder(fork_threshold))
                spans_per_builder.append([])
                kind = DriftKind.CLEAN
            builder = builders[-1]
            spans = spans_per_builder[-1]
            if kind is DriftKind.REALIGN:
                # _align_to_prompt 会把 tokens[last_response_start_idx:] 整段
                # 覆盖为 mask=0 的 prompt 尾——落在覆盖区里的 trained span
                # 掉落，从身份账移除（REALIGN 掉落轮天然不在叶 span）。
                overwrite_from = builder.last_response_start_idx
                while spans and spans[-1][0] >= overwrite_from:
                    spans.pop()
            builder.append_turn(node.turn, kind, trained=trained)
            if trained and node.turn.output_ids:
                if node.turn_index is None:
                    raise SlimeBindingError(
                        "turn_identity_index_missing",
                        "generated 节点缺 turn_index——vendor 附着语义被破坏"
                        "（_attach_assistant_leaf 恒写该字段）。",
                    )
                spans.append(
                    (
                        builder.last_response_start_idx,
                        len(node.turn.output_ids),
                        node.turn_index,
                    )
                )

        for builder, spans in zip(builders, spans_per_builder):
            if not builder.has_trained_response():
                continue  # vendor _chain_to_samples 同款过滤：不产样本
            start = builder.leading_prompt_len
            tokens = list(builder.tokens)
            loss_mask = list(builder.loss_mask)
            if max_sample_tokens and len(tokens) > max_sample_tokens:
                tokens = tokens[:max_sample_tokens]
                loss_mask = loss_mask[:max_sample_tokens]
            limit = len(tokens)
            response_spans: list[tuple[int, int, int]] = []
            for span_start, width, turn_index in spans:
                clipped = min(width, max(0, limit - span_start))
                if clipped <= 0:
                    continue  # 整段被截断丢弃（mask 同步被截断，无失配）
                response_spans.append((span_start - start, clipped, turn_index))
            exports.append(
                LeafIdentityExport(
                    tokens=tokens,
                    loss_mask=loss_mask[start:],
                    response_start=start,
                    spans=tuple(response_spans),
                )
            )
    return exports


def attach_turn_identity_spans(
    samples: list[Any],
    root: Any,
    *,
    fork_threshold: int,
    max_sample_tokens: int = 0,
    resolve_capture_id: Callable[[int], str | None],
) -> None:
    """finish 之后把身份 span 装到每条叶链 Sample 上（生产接线本体）。

    对账全部 fail-closed（重放与 vendor 漂移 = 身份不可信，宁缺勿错）：
    - 重放样本数必须等于真实样本数；
    - 每条样本的 tokens 与 loss_mask 必须与重放产物逐位全等；
    - 每个 trained span 的 turn_index 必须能经 ``resolve_capture_id``
      解析出 capture_record_id（commit 时刻绑定账；解析不到 = 有可训练
      token 没有 capture 凭据）。

    通过后以 ``RH2_TURN_IDENTITY_SPANS_ATTR`` 附加属性写到 Sample 上，
    bringup_leaf_facts 读出装进 LeafFacts.turn_spans。
    """

    exports = export_leaf_identity_spans(
        root, fork_threshold=fork_threshold, max_sample_tokens=max_sample_tokens
    )
    if len(exports) != len(samples):
        raise SlimeBindingError(
            "turn_identity_replay_count_mismatch",
            f"树走查重放出 {len(exports)} 条样本，finish_session 实产 "
            f"{len(samples)} 条——重放与 vendor 线性化漂移，身份 span 不可信。",
        )
    for position, (sample, export) in enumerate(zip(samples, exports)):
        if list(sample.tokens or []) != export.tokens or (
            list(sample.loss_mask or []) != export.loss_mask
        ):
            raise SlimeBindingError(
                "turn_identity_replay_token_drift",
                f"第 {position} 条叶链的 tokens/loss_mask 与树走查重放不等——"
                "重放与 vendor 线性化漂移，身份 span 不可信（fail-closed）。",
            )
        identity_spans: list[TurnIdentitySpan] = []
        for span_start, length, turn_index in export.spans:
            record_id = resolve_capture_id(turn_index)
            if not record_id:
                raise SlimeBindingError(
                    "turn_identity_binding_missing",
                    f"第 {position} 条叶链 trained 轮 turn_index={turn_index} 无 "
                    "capture 绑定——可训练 token 没有捕获凭据（commit 绑定账"
                    "缺失，fail-closed）。",
                )
            identity_spans.append(
                TurnIdentitySpan(
                    start=span_start, length=length, capture_record_id=record_id
                )
            )
        setattr(sample, RH2_TURN_IDENTITY_SPANS_ATTR, tuple(identity_spans))
