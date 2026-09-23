"""I01 B 独立反例探针：只用 CPU，不改生产源码，不调用引擎或容器。"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "rh2/src"))

from slime.agent.adapters.anthropic import AnthropicAdapter
from slime.agent.trajectory import TurnRecord
from slime.utils.types import Sample

from repoharness2.adapters.slime.bringup import make_per_rollout_adapter
from repoharness2.adapters.slime.capture_wire import CaptureRegistry
from repoharness2.adapters.slime.generate import (
    RH2_TURN_IDENTITY_SPANS_ATTR,
    TurnTape,
    backfill_leaf_sample,
    take_turn_coverage,
)


def message(role, content):
    return {"role": role, "content": content}


USER = message("user", "任务")
A1 = message("assistant", "动作一")
A2 = message("assistant", "动作二")
A3 = message("assistant", "动作三")
A4 = message("assistant", "动作四")
O1 = message("tool", "观察一")
O2 = message("tool", "观察二")
O3 = message("tool", "观察三")
P1 = [100, 101]
R1 = [201, 202, 203, 204]
P2 = [100, 101, 201, 202, 999, 204, 300]
R2 = [401, 402]
P3 = P2 + R2 + [500]
R3 = [601, 602]


class Tokenizer:
    def decode(self, token_ids, **kwargs):
        return ",".join(map(str, token_ids))


async def run_case(specs, threshold, *, cap=0, backfill=True):
    """真实包装 + AnthropicAdapter 会话面；仅生成请求用指定 TurnRecord 代入。"""

    registry = CaptureRegistry()
    shared = AnthropicAdapter(
        tokenizer=Tokenizer(),
        sglang_url="http://unused",
        fork_threshold_tokens=threshold,
    )
    adapter = make_per_rollout_adapter(registry, shared, SimpleNamespace())
    sid = "falsifier"
    adapter.open_session(sid, max_context_tokens=cap)
    tapes = {}
    for i, (prompt, response, history, reply) in enumerate(specs, start=1):
        turn = TurnRecord(prompt, response, "stop", [-0.2] * len(response))
        shared.manager.record_turn(
            sid, turn=turn, prompt_messages=history, response_message=reply
        )
        registry.bind_turn_identity(sid, i, f"c{i}")
        tapes[f"c{i}"] = TurnTape(
            record_id=f"c{i}",
            turn_index=i,
            prompt_token_count=len(prompt),
            response_token_count=len(response),
            output_ids=tuple(response),
            output_log_probs=tuple(turn.output_log_probs),
            top_p_token_ids=None,
            top_p_token_offsets=None,
            routed_experts_flat=None,
            weight_version=str(i),
        )
    samples = await adapter.finish_session(
        sid, base_sample=Sample(index=0, group_index=0, prompt="任务")
    )
    coverage = take_turn_coverage(samples)
    captures = []
    spans_by_row = []
    for sample in samples:
        spans = getattr(sample, RH2_TURN_IDENTITY_SPANS_ATTR)
        spans_by_row.append(
            [[s.capture_record_id, s.start, s.length] for s in spans]
        )
        if backfill:
            used = backfill_leaf_sample(
                sample,
                [tapes[s.capture_record_id] for s in spans],
                identity_spans=spans,
                require_real_weight_versions=True,
            )
            captures.extend(t.record_id for t in used)
    return {
        "coverage": coverage,
        "row_tokens": [len(s.tokens) for s in samples],
        "mask_sums": [sum(s.loss_mask) for s in samples],
        "spans_by_row": spans_by_row,
        "used_capture_counts": dict(Counter(captures)),
    }


async def main():
    first = (P1, R1, [USER], A1)
    second = (P2, R2, [USER, A1, O1], A2)
    third = (P3, R3, [USER, A1, O1, A2, O2], A3)
    # 前两轮共享；第四轮消息改写第三轮，因此第二轮的 token FORK 被两条叶路径重放。
    rewrite = message("assistant", "动作三已改写")
    fourth = (
        P3 + [601, 999] + [700],
        [801, 802],
        [USER, A1, O1, A2, O2, rewrite, O3],
        A4,
    )
    shared_fork = await run_case([first, second, third, fourth], 0, cap=100)
    events = shared_fork["coverage"]["fork_events"]
    assert len(events) == 2 and events[0] == events[1]
    assert events[0]["turn_index"] == 2
    assert shared_fork["used_capture_counts"] == {"c1": 1, "c2": 1, "c3": 1, "c4": 1}
    assert shared_fork["coverage"]["turns_trained"] == 4

    # 新输出达旧阈值，旧路线原本就 FORK；真实 B 增量为零，观测字段仍报 6。
    long_second = (P2, list(range(1000, 2024)), [USER, A1, O1], A2)
    zero = await run_case([first, long_second], 0, cap=2000)
    old = await run_case([first, long_second], 1024, cap=2000)
    true_delta = sum(zero["row_tokens"]) - sum(old["row_tokens"])
    assert zero["row_tokens"] == old["row_tokens"] == [6, 1031]
    assert true_delta == 0
    assert zero["coverage"]["extra_input_tokens_vs_single_row"] == 6

    # 多次 token FORK 且无消息分枝：保留三轮，按 capture 核对不存在重复训练。
    third_drift = ([100, 101, 201, 202, 999, 204, 300, 401, 999, 500], R3,
                   [USER, A1, O1, A2, O2], A3)
    multiple = await run_case([first, second, third_drift], 0, cap=100)
    assert multiple["used_capture_counts"] == {"c1": 1, "c2": 1, "c3": 1}
    assert [e["turn_index"] for e in multiple["coverage"]["fork_events"]] == [2, 3]
    assert multiple["coverage"]["turns_trained"] == 3

    # 人工违反生成预算：第二轮应在 cap=7 时由生产请求面返回空输出，本例刻意给非空。
    clean_second = (P1 + R1 + [300], R2, [USER, A1, O1], A2)
    clipped = await run_case([first, clean_second], 0, cap=7, backfill=False)
    assert clipped["coverage"]["turns_trained"] == 2
    assert clipped["spans_by_row"] == [[["c1", 0, 4]]]
    assert clipped["mask_sums"] == [4]

    print(json.dumps({
        "shared_prefix_token_fork_then_message_rewrite": shared_fork,
        "long_output_b": zero,
        "long_output_old_threshold": old,
        "actual_b_delta_against_1024": true_delta,
        "multiple_token_forks": multiple,
        "artificial_over_budget_clipping": clipped,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
