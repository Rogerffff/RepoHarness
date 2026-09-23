"""R1/R2 窄复核：复用首审输入，比对修复前的真实训练行与 capture 归属。"""

import asyncio
import json
from pathlib import Path

import falsifier_probe as original


async def main():
    first = (original.P1, original.R1, [original.USER], original.A1)
    second = (original.P2, original.R2,
              [original.USER, original.A1, original.O1], original.A2)
    third = (original.P3, original.R3,
             [original.USER, original.A1, original.O1, original.A2, original.O2], original.A3)
    rewrite = original.message("assistant", "动作三已改写")
    fourth = (
        original.P3 + [601, 999, 700], [801, 802],
        [original.USER, original.A1, original.O1, original.A2, original.O2, rewrite, original.O3],
        original.A4,
    )
    current = await original.run_case([first, second, third, fourth], 0, cap=100)
    previous = json.loads((Path(__file__).parent / "review_counterexamples.json").read_text())
    prior_shared = previous["shared_prefix_token_fork_then_message_rewrite"]
    for field in ("row_tokens", "mask_sums", "spans_by_row", "used_capture_counts"):
        assert current[field] == prior_shared[field], field
    assert [e["turn_index"] for e in current["coverage"]["fork_events"]] == [2]
    assert current["used_capture_counts"] == {"c1": 1, "c2": 1, "c3": 1, "c4": 1}

    third_drift = ([100, 101, 201, 202, 999, 204, 300, 401, 999, 500], original.R3,
                   [original.USER, original.A1, original.O1, original.A2, original.O2], original.A3)
    independent = await original.run_case([first, second, third_drift], 0, cap=100)
    assert [e["turn_index"] for e in independent["coverage"]["fork_events"]] == [2, 3]
    assert independent["used_capture_counts"] == {"c1": 1, "c2": 1, "c3": 1}

    long_second = (original.P2, list(range(1000, 2024)),
                   [original.USER, original.A1, original.O1], original.A2)
    current_b = await original.run_case([first, long_second], 0, cap=2000)
    baseline = await original.run_case([first, long_second], 1024, cap=2000)
    for result in (current_b, baseline):
        assert result["row_tokens"] == [6, 1031]
        assert result["coverage"]["input_tokens_total"] == 1037
        assert result["coverage"]["input_tokens_excluding_last_row"] == 6
        assert "extra_input_tokens_vs_single_row" not in result["coverage"]
    assert current_b["coverage"]["input_tokens_total"] - baseline["coverage"]["input_tokens_total"] == 0
    print(json.dumps({
        "status": "passed",
        "shared_prefix": current,
        "independent_forks": independent,
        "long_output_b": current_b,
        "long_output_old_threshold": baseline,
        "actual_input_delta": 0,
        "training_representation_unchanged_against_first_review": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
