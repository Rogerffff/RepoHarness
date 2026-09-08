"""I01：用 run8 唯一留存的六轮原始 token 测量训练表示大小。

真实调用顺序已知；只重放 vendor 的 token builder，不恢复缺失的 CC 请求体，
不模拟消息树、C 的在线输出或 GPU 耗时。无截断、无 padding、无 packing。
"""

import hashlib
import json
from pathlib import Path
import struct
import sys


repo_root = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(repo_root / "rh2/src"))
from slime.agent.trajectory import DriftKind, TurnRecord, _SampleBuilder


run_dir = repo_root / "docs/agentic_RL/repo_harness_rh2_workstreams/s1/7a_artifacts/artifacts_run8"
projections = list(run_dir.glob("rollouts/*/trajectory_projection.json"))
assert len(projections) == 1
directory = projections[0].parent
captures = json.loads((directory / "capture_records.json").read_text())
turns = []
for capture in captures:
    columns = []
    for field in ("prompt_token_ids_ref", "response_token_ids_ref"):
        reference = capture[field]
        raw = (directory / "tapes" / f"{reference['ref_id']}.bin").read_bytes()
        assert hashlib.sha256(raw).hexdigest() == reference["sha256"].split(":")[1]
        columns.append(list(struct.unpack("<" + "i" * (len(raw) // 4), raw)))
    prompt, output = columns
    # 这里只比较形状与前缀；占位 logprob 不用作任何概率/梯度计算。
    turns.append(TurnRecord(prompt, output, "stop", [0.0] * len(output)))


def common_prefix(left, right):
    return next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), min(len(left), len(right)))


boundaries = []
for index, (previous, current) in enumerate(zip(turns, turns[1:]), 1):
    old_tokens = previous.prompt_ids + previous.output_ids
    matched = common_prefix(old_tokens, current.prompt_ids)
    boundaries.append({
        "boundary": f"t{index - 1}->t{index}",
        "old_total": len(old_tokens),
        "new_prompt": len(current.prompt_ids),
        "common_prefix": matched,
        "is_exact_extension": matched == len(old_tokens),
        "old_tail_not_reusable_from_immediate_previous_call": len(old_tokens) - matched,
        "new_prompt_after_common_prefix": len(current.prompt_ids) - matched,
    })


results = []
for threshold in (1024, 0):
    builders = [_SampleBuilder(threshold)]
    classifications = []
    for turn in turns:
        kind = builders[-1].classify_token_drift(turn)
        classifications.append(kind.value)
        if kind is DriftKind.FORK:
            builders.append(_SampleBuilder(threshold))
            kind = DriftKind.CLEAN
        builders[-1].append_turn(turn, kind)
    rows = [{
        "total_tokens": len(builder.tokens),
        "leading_prompt_tokens": builder.leading_prompt_len,
        "trainable_tokens": sum(builder.loss_mask),
    } for builder in builders if builder.has_trained_response()]
    results.append({
        "threshold": threshold,
        "classifications": classifications,
        "rows": rows,
        "total_unpadded_tokens": sum(row["total_tokens"] for row in rows),
        "total_trainable_tokens": sum(row["trainable_tokens"] for row in rows),
        "longest_row": max(row["total_tokens"] for row in rows),
    })

assert [boundary["is_exact_extension"] for boundary in boundaries] == [False, True, True, True, True]
assert [item["total_unpadded_tokens"] for item in results] == [26283, 45415]
assert [item["total_trainable_tokens"] for item in results] == [2148, 2772]
assert [row["total_tokens"] for row in results[1]["rows"]] == [19132, 26283]
report = {
    "scope": "单条 run8，真实 token 的无截断 builder 重放；不是完整 producer、C 或 GPU 测量",
    "projection": str(projections[0].relative_to(repo_root)),
    "call_lengths": [{"prompt": len(t.prompt_ids), "output": len(t.output_ids)} for t in turns],
    "boundaries": boundaries,
    "representations": results,
    "B_over_current_total_token_ratio": results[1]["total_unpadded_tokens"] / results[0]["total_unpadded_tokens"],
    "per_request_total_unpadded_tokens": sum(len(t.prompt_ids) + len(t.output_ids) for t in turns),
    "notes": [
        "比较基准是当前欠覆盖的单行，不能当作等训练目标的性能对比。",
        "输入 token 总量不等于 FLOPs、峰值显存或 wall time。",
        "前缀长度只表示相邻请求的可复用机会；缓存驻留、权重与 engine 未模拟。",
    ],
}
print(json.dumps(report, ensure_ascii=False, indent=2))
