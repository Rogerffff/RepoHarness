"""J5b-M1：staleness 直方图 + turn/版本边界对齐统计（随 J4/J4b 顺带采集）。

协议条目（preflight/8gpu_preflight_protocol.md J5b-M1）：
- Sample.weight_versions 的长度与版本跨度分布（一条 SWE 轨迹平均跨几个
  policy version——升级档位 α 定档的实测依据）。
- 增补（升级设计缺口②可行性数据）：turn 边界与版本边界的对齐统计——
  "跨版本发生在轮间 vs 单轮内部"的比例，直接决定 turn 级版本 mask 方案
  能覆盖多少盲区。
- 采集点显式声明（codex 核查）：slime 的 _convert_samples_to_train_data
  （ray/rollout.py:735）不透传 weight_versions——必须在转换前的 Sample 上
  采集。本脚本支持两个转换前数据源：
    a) --dumps-dir：--save-debug-rollout-data 的 rollout_*.pt
       （Sample.to_dict 原样含 weight_versions）；
    b) --events：7a 编排的 bringup_events.jsonl（weight_versions_sample 字段，
       projection 层采集，H-1 契约的同一事实源）。

对齐统计口径：weight_versions 每条 = 一次 /generate 段（types.py:381-382，
一轮 = 一次 /generate = 一条记录，段边界即 turn 边界）。相邻两条记录版本号
不同 => 一次"轮间跨版本"（turn 级 mask 可覆盖）；"单轮内部跨版本"在该
tape 上物理不可见（升级设计缺口②的盲区本体），本脚本输出
inter_turn_transitions 与不可观测声明，供与引擎 pause 事件对齐后估计盲区。
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def _span(versions: list) -> int:
    nums = []
    for v in versions:
        try:
            nums.append(int(str(v)))
        except (TypeError, ValueError):
            continue
    return (max(nums) - min(nums)) if nums else 0


def _collect_from_dumps(dumps_dir: str) -> list[list]:
    import torch

    out = []
    for f in sorted(Path(dumps_dir).glob("rollout_*.pt")):
        data = torch.load(f, weights_only=False)
        for s in data.get("samples", []):
            out.append(list(s.get("weight_versions") or []))
    return out


def _collect_from_events(events_path: str) -> list[list]:
    out = []
    for line in Path(events_path).read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for wv in event.get("weight_versions_sample") or []:
            out.append(list(wv or []))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dumps-dir", default=None)
    parser.add_argument("--events", default=None)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    assert args.dumps_dir or args.events, "至少给 --dumps-dir 或 --events 之一"

    versions_lists: list[list] = []
    if args.dumps_dir and Path(args.dumps_dir).exists():
        versions_lists += _collect_from_dumps(args.dumps_dir)
    if args.events and Path(args.events).exists():
        versions_lists += _collect_from_events(args.events)

    len_hist = Counter(len(v) for v in versions_lists)
    span_hist = Counter(_span(v) for v in versions_lists)

    inter_turn_transitions = 0
    total_turn_boundaries = 0
    cross_version_samples = 0
    for versions in versions_lists:
        boundaries = max(len(versions) - 1, 0)
        total_turn_boundaries += boundaries
        changes = sum(1 for a, b in zip(versions, versions[1:]) if str(a) != str(b))
        inter_turn_transitions += changes
        if changes:
            cross_version_samples += 1

    n = len(versions_lists)
    report = {
        "n_samples": n,
        "weight_versions_len_hist": dict(sorted(len_hist.items())),
        "version_span_hist(max-min)": dict(sorted(span_hist.items())),
        "avg_versions_per_trajectory": round(sum(len(v) for v in versions_lists) / n, 2) if n else None,
        "cross_version_sample_ratio": round(cross_version_samples / n, 3) if n else None,
        "turn_alignment": {
            "total_turn_boundaries": total_turn_boundaries,
            "inter_turn_version_transitions": inter_turn_transitions,
            "inter_turn_transition_ratio": round(inter_turn_transitions / total_turn_boundaries, 3)
            if total_turn_boundaries
            else None,
            "intra_turn_note": "单轮内部跨版本在 weight_versions tape 上物理不可见"
            "（types.py:381-382 每段一条记录）——需与引擎 pause/continue 事件时间戳"
            "对齐后才能估计盲区规模（升级设计缺口②）",
        },
        "alpha_reference": "升级档 staleness 准入 α=1（RollArt 实证）——span_hist 中 >1 的占比即被准入拒绝的比例预估",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
