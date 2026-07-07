"""J4c 结果分析：三元组分类 + I-3 顺带采集（queue_size 曲线、task 异常计数）。

输入：
  --probe  lib/j4c_probe.py 写的 probe_triples.jsonl（custom_generate 入口三元组）
  --log    ray job 日志（含 slime.rollout.fully_async 的 worker 打点）
输出：--out JSON 报告。

分类口径（协议 J4c 修订 + 升级设计 I-2）：
  aborted_reentry_with_stale_tokens  status==ABORTED 且 len_tokens>0 且
      response_length>0 —— "带旧 token 重开沙箱从头跑"（旧 token 悬挂，
      最坏形态；升级档必须走 starts-over+丢弃过渡方案）
  aborted_reentry_clean              status==ABORTED 且 response_length==0
      —— 干净重开
  no_aborted_reentry                 没有 ABORTED 重入记录——检查 abort 是否
      真的被触发（对照日志 update_weights / pause_generation 次数）

I-3 口径（升级设计 N1/N2，监控成本一行）：
  queue_size 曲线：fully_async_rollout.py 的 rollout 打点行
      "fully-async rollout %d: target=%d queue_warm=%d"
  task 异常计数：done_cb 的 "fully-async: process task raised"（N1 静默泄漏面）
      + reap 的 "fully-async task crashed"
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    # ---- 三元组 -------------------------------------------------------------
    triples = []
    probe_path = Path(args.probe)
    if probe_path.exists():
        for line in probe_path.read_text(errors="replace").splitlines():
            try:
                triples.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    stale, clean, first_entries = [], [], 0
    for t in triples:
        status = (t.get("status") or "").lower()
        if "aborted" in status:
            if (t.get("len_tokens") or 0) > 0 and (t.get("response_length") or 0) > 0:
                stale.append(t)
            else:
                clean.append(t)
        else:
            first_entries += 1

    if stale:
        classification = "aborted_reentry_with_stale_tokens（带旧 token 重开，旧 token 悬挂——最坏形态，升级档需 starts-over+丢弃过渡）"
    elif clean:
        classification = "aborted_reentry_clean（干净重开）"
    else:
        classification = "no_aborted_reentry（未观测到 ABORTED 重入——核对 abort 是否真被触发）"

    # ---- 日志指标 -----------------------------------------------------------
    log_text = Path(args.log).read_text(errors="replace") if Path(args.log).exists() else ""
    queue_curve = [
        {"rollout_id": int(m.group(1)), "target": int(m.group(2)), "queue_warm": int(m.group(3))}
        for m in re.finditer(r"fully-async rollout (\d+): target=(\d+) queue_warm=(\d+)", log_text)
    ]
    task_raised = len(re.findall(r"fully-async: process task raised", log_text))
    task_crashed = len(re.findall(r"fully-async task crashed", log_text))
    requeue_failed = len(re.findall(r"failed to requeue aborted group", log_text))
    n_updates = len(re.findall(r"update_weights|pause_generation", log_text, re.IGNORECASE))

    report = {
        "classification": classification,
        "n_probe_entries": len(triples),
        "n_first_entries": first_entries,
        "n_aborted_reentry_stale": len(stale),
        "n_aborted_reentry_clean": len(clean),
        "stale_examples": stale[:5],
        "queue_size_curve": queue_curve,
        "task_exceptions": {
            "done_cb_raised(N1 泄漏面)": task_raised,
            "reap_crashed": task_crashed,
            "requeue_failed": requeue_failed,
        },
        "weight_update_marker_lines": n_updates,
        "startable": bool(queue_curve) or len(triples) > 0,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[j4c_metrics] classification = {classification}")
    print(f"[j4c_metrics] queue curve points={len(queue_curve)}, task raised={task_raised}, crashed={task_crashed}")
    print(f"[j4c_metrics] -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
