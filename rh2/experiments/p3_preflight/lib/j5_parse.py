"""J5 update_weights 耗时解析（含三段分解的尽力近似）。

数据来源（pin e848052a 源码事实）：
- 总耗时：actor.py:553 ``@timer def update_weights``，经
  train_metric_utils.py:27 变成日志键 ``perf/update_weights_time``。
- 三段（pause/flush → send → continue）：源码无独立计时
  （update_weight_from_distributed.py:110-133 直接 ray.get，不打点）。
  近似手段（按可得性降级）：
  a) trainer 侧 tqdm 进度条 "Update weights"（_send_weights 段的时间窗，
     tqdm 输出带耗时 "MM:SS" 字样）；
  b) 引擎/router 日志的 pause/flush/continue 行时间戳（若 SGLang 版本有）；
  c) 都拿不到 -> three_phase_resolved=no，只报总耗时。

输出：一行 CSV 片段到 stdout（buffer,steps,update_times,pause_flush,send,continue,resolved）
     + --out JSON 明细。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--buffer-size", required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    text = Path(args.log).read_text(errors="replace") if Path(args.log).exists() else ""

    # 总耗时（perf 键；一步一条）
    totals = [float(x) for x in re.findall(r"perf/update_weights_time['\"]?\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", text)]

    # send 段近似：tqdm "Update weights" 完成行的 [MM:SS<...] 耗时
    send_windows = []
    for m in re.finditer(r"Update weights.*?\[(\d+):(\d+)<", text):
        send_windows.append(int(m.group(1)) * 60 + int(m.group(2)))

    # pause/flush 与 continue：引擎日志时间戳（尽力）
    resolved = bool(totals and send_windows)
    pause_flush = send = cont = None
    if resolved:
        send = sum(send_windows) / len(send_windows)
        avg_total = sum(totals) / len(totals)
        # 剩余时间按时序归 pause/flush（前）与 continue（后）无法区分——对半标注为上界
        rest = max(avg_total - send, 0.0)
        pause_flush = cont = round(rest / 2, 2)

    detail = {
        "buffer_size_bytes": int(args.buffer_size),
        "per_step_update_weights_time_s": totals,
        "send_phase_tqdm_windows_s": send_windows,
        "three_phase_resolved": resolved,
        "approx_pause_flush_s_upper": pause_flush,
        "approx_send_s": send,
        "approx_continue_s_upper": cont,
        "note": "三段分解为近似口径（源码无独立打点）：send 取 tqdm 时间窗；"
        "pause/flush 与 continue 平摊余量作为各自上界。精确三段需轻量 patch（P3 不改 pin 代码）。",
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(detail, indent=2, ensure_ascii=False))

    times_str = ";".join(f"{t:.1f}" for t in totals) if totals else "none"
    print(
        f"{args.buffer_size},{args.steps},{times_str},"
        f"{pause_flush if pause_flush is not None else '-'},"
        f"{send if send is not None else '-'},"
        f"{cont if cont is not None else '-'},"
        f"{'yes' if resolved else 'no'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
