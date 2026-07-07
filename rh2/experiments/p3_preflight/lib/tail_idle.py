"""rollout 尾部空闲占比计算（协议口径照抄实现，J4b/首训双处共用）。

协议原文（preflight/8gpu_preflight_protocol.md "rollout 尾部空闲占比"）：
    尾部空闲占比 = （rollout 阶段内，推理分区 GPU 平均利用率 < 30% 阈值的
                  尾段时长）/ 当前 step 总墙钟
    测量方式：nvidia-smi dmon 1s 采样（推理分区卡）+ 每条轨迹的完成时间戳；
    "尾段"起点 = 最后 25% 轨迹开始完成的时刻。

输入：
  --dmon    common.sh p3_dmon_start 的 csv（列：timestamp,index,util,mem_used,mem_total）
  --events  7a 编排的 bringup_events.jsonl（每行一条轨迹完成事件，字段 ts=epoch 秒）
  --rollout-gpus  推理分区 GPU 编号（如 "4,5,6,7"——按 ray 实际分配核对）
  --steps   本次运行的 step 数：完成时间戳按最大时间间隙切成 steps 簇，
            每簇独立算尾部空闲，再取平均（事件流里没有 rollout_id，
            以簇近似 step 归属——J4b 各拓扑 2~3 步下最大间隙切分足够稳）
输出：stdout 打平均尾部空闲占比（0~1，3 位小数）；--out 写逐 step 明细 JSON。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

UTIL_THRESHOLD = 30.0  # 协议阈值：平均利用率 < 30% 记空闲
TAIL_FRACTION = 0.25  # 尾段起点 = 最后 25% 轨迹开始完成的时刻


def parse_dmon(path: str, gpus: set[str]) -> list[tuple[float, float]]:
    """返回 [(epoch_s, 推理分区平均 util), ...]，1s 粒度。

    输入行来自 common.sh p3_dmon_start：
    ``timestamp, index, utilization.gpu, memory.used, memory.total``（nounits），
    timestamp 形如 ``2026/07/08 12:34:56.789``。同一秒内多块卡取平均。
    """
    per_second: dict[str, list[float]] = {}
    for line in Path(path).read_text(errors="replace").splitlines()[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        ts_raw, idx, util = parts[0], parts[1], parts[2]
        if idx not in gpus:
            continue
        try:
            float(util)
        except ValueError:
            continue
        per_second.setdefault(ts_raw.split(".")[0], []).append(float(util))
    out = []
    for ts_str, utils in per_second.items():
        try:
            epoch = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S").timestamp()
        except ValueError:
            continue
        out.append((epoch, sum(utils) / len(utils)))
    return sorted(out)


def split_steps(ts_list: list[float], steps: int) -> list[list[float]]:
    """按最大时间间隙把完成时间戳切成 steps 簇。"""
    ts_sorted = sorted(ts_list)
    if steps <= 1 or len(ts_sorted) <= steps:
        return [ts_sorted]
    gaps = sorted(range(1, len(ts_sorted)), key=lambda i: ts_sorted[i] - ts_sorted[i - 1], reverse=True)
    cuts = sorted(gaps[: steps - 1])
    clusters, prev = [], 0
    for c in cuts:
        clusters.append(ts_sorted[prev:c])
        prev = c
    clusters.append(ts_sorted[prev:])
    return [c for c in clusters if c]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dmon", required=True)
    parser.add_argument("--events", required=True)
    parser.add_argument("--rollout-gpus", required=True, help='如 "4,5,6,7"')
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    gpus = {g.strip() for g in args.rollout_gpus.split(",")}
    util_curve = parse_dmon(args.dmon, gpus)
    events = [
        json.loads(line)
        for line in Path(args.events).read_text(errors="replace").splitlines()
        if line.strip()
    ]
    completion_ts = [float(e["ts"]) for e in events if e.get("ts")]
    if not util_curve or not completion_ts:
        print("parse_failed")
        return 1

    details = []
    prev_end: float | None = None
    max_wall = max((float(e.get("wall_seconds") or 0) for e in events), default=0.0)
    for cluster in split_steps(completion_ts, args.steps):
        # step 起点近似：上一簇结束时刻；首簇用"最早完成时刻 - 该批最长轨迹墙钟"
        step_start = prev_end if prev_end is not None else (min(cluster) - max_wall)
        step_end = max(cluster)
        prev_end = step_end
        # 尾段起点 = 最后 25% 轨迹开始完成的时刻
        k = max(0, int(len(cluster) * (1 - TAIL_FRACTION)) - 1)
        tail_start = sorted(cluster)[k]
        step_wall = max(step_end - step_start, 1.0)
        idle_s = sum(
            1.0
            for (t, u) in util_curve
            if tail_start <= t <= step_end and u < UTIL_THRESHOLD
        )
        details.append(
            {
                "step_wall_s": round(step_wall, 1),
                "tail_start_epoch": tail_start,
                "tail_idle_s": idle_s,
                "tail_idle_pct": round(idle_s / step_wall, 3),
                "n_trajectories": len(cluster),
            }
        )
    avg = sum(d["tail_idle_pct"] for d in details) / len(details)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(
                {
                    "definition": "尾部空闲占比 =（推理分区 GPU 平均 util<30% 的尾段时长）/ step 总墙钟；尾段起点 = 最后 25% 轨迹开始完成的时刻",
                    "rollout_gpus": sorted(gpus),
                    "per_step": details,
                    "avg_tail_idle_pct": round(avg, 3),
                    "upgrade_trigger": "avg > 0.25 触发 fully_async 升级档（预注册）",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    print(f"{avg:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
