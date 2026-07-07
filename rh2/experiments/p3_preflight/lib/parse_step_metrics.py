"""从 slime 训练日志解析每步墙钟（J3/J4/J4b 共用）。

解析优先级：
1. 日志里的计时指标行——slime 的 perf 打点（形如 ``perf/train_time`` /
   ``rollout_time`` / ``step_time`` 的 key: value 或 dict 打印）；取每步训练
   耗时的均值。key 集合宽松匹配，因为 pin 版本（e848052a）与 wandb 关闭时
   的 stdout 格式并不承诺稳定。
2. 兜底：--fallback-wall（整个 ray job 的墙钟秒）÷ --steps。
   注意兜底口径偏保守（含 ray 启动、模型加载、编译 warmup），首 step 与
   均值差异大时以 dmon 曲线人工复核——协议 §4"排障留给分析阶段"。

输出：单个数字（秒，保留 1 位小数）到 stdout。
"""

from __future__ import annotations

import argparse
import re
import sys

# 宽松匹配 "…train_time…: 123.4" / "'step_time': 123.4" / "perf/actor_train_time 123.4"
_PATTERNS = [
    re.compile(r"(?:perf/)?(?:actor[_-])?train[_-]time['\"]?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"),
    re.compile(r"(?:perf/)?step[_-]time['\"]?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--fallback-wall", type=float, required=True)
    parser.add_argument("--steps", type=int, required=True)
    args = parser.parse_args()

    values: list[float] = []
    try:
        with open(args.log, errors="replace") as fh:
            for line in fh:
                for pat in _PATTERNS:
                    m = pat.search(line)
                    if m:
                        values.append(float(m.group(1)))
                        break
    except OSError as exc:
        print(f"parse_step_metrics: cannot read log: {exc}", file=sys.stderr)

    if values:
        print(f"{sum(values) / len(values):.1f}")
    else:
        print(f"{args.fallback_wall / max(args.steps, 1):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
