"""P3 真实事件元数据的夹具加载器（FA-3 A/B 两类失败复现的数据源）。

来源：`docs/agentic_RL/repo_harness_rh2_workstreams/preflight/
remote_evidence_20260708/bringup_selected/`。本地没有 .pt 张量 dump（远程
同步排除大文件，codex 轮次 1 核实），能且只能重建**结构事实**：逐 rollout
的保留样本数、fan-out 分布、rollout id 序。样本 token 总长不在事件里——
需要长度的夹具用显式校准值并在调用处如实标注。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_EVIDENCE_ROOT = (
    Path(__file__).resolve().parents[3].parent
    / "docs/agentic_RL/repo_harness_rh2_workstreams/preflight/remote_evidence_20260708"
    / "bringup_selected"
)

J4_FORMAL = "j4_formal_20260708T160749Z"
J5_GBS16 = "j5_reduced_20260708T165218Z"


def load_events(run_name: str) -> list[dict]:
    """读取一次 run 的 bringup_events（按 index 排序）；evidence 缺席时 skip。"""

    run_dir = _EVIDENCE_ROOT / run_name
    if not run_dir.exists():
        pytest.skip(f"P3 evidence {run_name} 不在本地（浅 checkout）")
    files = sorted(run_dir.rglob("bringup_events.jsonl"))
    if not files:
        pytest.skip(f"{run_name} 无 bringup_events.jsonl")
    events = [json.loads(line) for line in files[0].read_text().splitlines() if line.strip()]
    events.sort(key=lambda e: e["index"])
    return events


def kept_rollout_structure(events: list[dict]) -> list[tuple[int, int]]:
    """[(rollout_index, kept_sample_count)]，只含 kept>0 的有效 rollout。"""

    result = []
    for event in events:
        kept = sum(1 for flag in (event.get("remove_sample") or []) if flag is False)
        if kept > 0:
            result.append((int(event["index"]), kept))
    return result


def as_schedule_inputs(
    structure: list[tuple[int, int]], *, sample_length: int
) -> tuple[list[int], list[int]]:
    """结构 → (total_lengths, rollout_indices)。

    sample_length 是校准值（真实 token 总长不在事件元数据里）——凡使用本
    函数的测试必须在 docstring 声明该口径。
    """

    lengths: list[int] = []
    rollout_indices: list[int] = []
    for rollout_index, kept in structure:
        for _ in range(kept):
            lengths.append(sample_length)
            rollout_indices.append(rollout_index)
    return lengths, rollout_indices
