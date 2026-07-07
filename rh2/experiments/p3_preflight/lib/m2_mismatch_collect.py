"""J5b-M2：训推 logprob 失配采集（P-8：提前备好，不指望 24h 机时内现写）。

协议条目（preflight/8gpu_preflight_protocol.md J5b-M2）：同批 token 的
rollout logprob vs trainer 重算 logprob 的逐 token 差分布（MAI 一等监控项；
GRPO 正确性项）。工具落点：--get-mismatch-metrics 或 debug train data；
本脚本基于 slime examples/train_infer_mismatch_helper/mis.py 的口径改写
（masked_mean/masked_max 的逐 token 统计族），但离线跑在两类输入上：

模式 A（--log）：J4 已开 --get-mismatch-metrics（只出指标不改 loss，
    见 examples/train_infer_mismatch_helper/README.md）——从训练日志抓
    mismatch 指标行（rollout-training KL 等），汇总成表。
模式 B（--dumps-dir）：读 --save-debug-rollout-data 的 rollout_*.pt，
    对 rollout_log_probs 做分布统计（p50/p90/max、每轨迹长度加权），
    并在提供 --recomputed-pt 时（训练侧另存的重算 logprob 张量，
    debug train data 路径）做逐 token 差分布。
    注意：dump 里只有 rollout 侧 logprob；没有重算侧输入时模式 B 只出
    rollout 侧画像 + 长轨迹复合风险的代理指标（logprob 和 = 轨迹级
    log-prob，MAI"小失配跨长轨迹复合"检查的输入之一）。

输出：--out JSON；--use-tis 的开关决策挂本数据（失配大则开，E2 定案钩子）。
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


def _percentile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    idx = min(int(len(sorted_vals) * q), len(sorted_vals) - 1)
    return sorted_vals[idx]


def collect_from_log(log_path: str) -> dict:
    """模式 A：抓 --get-mismatch-metrics 输出的指标行（键名含 mismatch/kl）。"""
    text = Path(log_path).read_text(errors="replace") if Path(log_path).exists() else ""
    metrics: dict[str, list[float]] = {}
    for m in re.finditer(
        r"['\"]?([a-zA-Z0-9_/]*(?:mismatch|rollout_kl|train_rollout|mis_)[a-zA-Z0-9_/]*)['\"]?\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?(?:e-?[0-9]+)?)",
        text,
    ):
        metrics.setdefault(m.group(1), []).append(float(m.group(2)))
    return {
        k: {"n": len(v), "mean": sum(v) / len(v), "max": max(v)} for k, v in metrics.items()
    }


def collect_from_dumps(dumps_dir: str, recomputed_pt: str | None) -> dict:
    """模式 B：rollout dump 的逐 token logprob 画像（+ 可选重算侧差分布）。"""
    import torch

    per_token: list[float] = []
    per_traj_sum: list[float] = []
    diffs: list[float] = []
    recomputed = None
    if recomputed_pt and Path(recomputed_pt).exists():
        recomputed = torch.load(recomputed_pt, weights_only=False)  # {index: list[float]}

    for f in sorted(Path(dumps_dir).glob("rollout_*.pt")):
        data = torch.load(f, weights_only=False)
        for s in data.get("samples", []):
            lps = s.get("rollout_log_probs") or []
            if not lps:
                continue
            per_token.extend(float(x) for x in lps)
            per_traj_sum.append(float(sum(lps)))
            if recomputed is not None:
                rec = recomputed.get(s.get("index"))
                if rec is not None and len(rec) == len(lps):
                    diffs.extend(abs(float(a) - float(b)) for a, b in zip(lps, rec))

    per_token.sort()
    out = {
        "n_tokens": len(per_token),
        "rollout_logprob_p50": _percentile(per_token, 0.5),
        "rollout_logprob_p10": _percentile(per_token, 0.1),
        "per_trajectory_logprob_sum_min": min(per_traj_sum) if per_traj_sum else None,
        "per_trajectory_logprob_sum_mean": (sum(per_traj_sum) / len(per_traj_sum)) if per_traj_sum else None,
    }
    if diffs:
        diffs.sort()
        out["token_abs_diff"] = {
            "n": len(diffs),
            "mean": sum(diffs) / len(diffs),
            "p50": _percentile(diffs, 0.5),
            "p90": _percentile(diffs, 0.9),
            "p99": _percentile(diffs, 0.99),
            "max": diffs[-1],
        }
        # 轨迹级复合：sum(|Δlogprob|) 的粗上界（MAI"跨长轨迹复合"口径的代理）
        out["compound_risk_note"] = "轨迹级失配复合看 token_abs_diff.mean × 平均轨迹长度"
    else:
        out["token_abs_diff"] = None
        out["note"] = "无重算侧输入（--recomputed-pt 未给或不匹配）——逐 token 差需模式 A（--get-mismatch-metrics）或 debug train data"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", default=None, help="模式 A：训练日志（--get-mismatch-metrics 已开）")
    parser.add_argument("--dumps-dir", default=None, help="模式 B：rollout dump 目录")
    parser.add_argument("--recomputed-pt", default=None, help="模式 B 可选：训练侧重算 logprob（{index: list}）")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    assert args.log or args.dumps_dir, "至少给 --log 或 --dumps-dir 之一"

    report: dict = {"tis_decision_hook": "失配大则开 --use-tis（E2 定案预留；slime 官方 30B R3 参照配置用 gspo+--use-tis）"}
    if args.log:
        report["mode_a_log_metrics"] = collect_from_log(args.log)
    if args.dumps_dir:
        report["mode_b_dump_profile"] = collect_from_dumps(args.dumps_dir, args.recomputed_pt)

    # 简单判读（阈值只做提示，不做门）
    kl_means = [v["mean"] for v in report.get("mode_a_log_metrics", {}).values() if isinstance(v, dict)]
    if kl_means:
        report["hint"] = "mismatch 指标非零且量级 >1e-2 时优先复核 --use-tis 决策" if max(
            abs(x) for x in kl_means
        ) > 1e-2 else "mismatch 指标量级小（<1e-2）"

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False, default=lambda o: None if isinstance(o, float) and math.isnan(o) else o))
    print(f"[m2] -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
