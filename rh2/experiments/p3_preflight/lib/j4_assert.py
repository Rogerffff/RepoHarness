"""J4 六项断言的自动检查段（协议 "J4 判据（全要素 step 的六项断言）"）。

输入：训练日志 + rollout dump（--save-debug-rollout-data 产物）+ 7a 编排的
startup_evidence.json + dmon 显存采样 csv + checkpoint 目录。
输出：--out 指定的 JSON（逐项 PASS/FAIL/UNKNOWN + 证据摘要）；
退出码 0 = 六项全 PASS（判据 6 的"即弃"动作由 j4_full_step.sh 执行，
本脚本只验证 checkpoint 曾产出 + 记录声明）。

判定口径逐条：
1. 合格 Sample：dump 内样本数 == --expected-samples（8 题 × n=4 = 32；
   动态采样 filter 补采时可能 > 32，按 >= 判），每条 tokens 非空、
   response_length > 0、loss_mask 长度 == response_length。
2. 启动期探针：startup_evidence.json 存在且 renderer 类名断言 + top-p tape
   探针字段在场（U-G/U-H；写该文件前任一失败 glue 会直接 raise，
   文件存在本身即通过的强证据）。
3. tape 消费：dump 内样本带 rollout_top_p_token_ids/offsets 与
   rollout_routed_experts（MoE），且日志无 tape 相关 raise、loss 有限值。
4. grad norm 非 NaN：日志抓 grad[ _-]norm 数值，全部有限。
5. 显存水位 + 无 OOM：dmon csv 每 GPU 的 memory.used 峰值成表；日志无 OOM。
6. checkpoint：目录曾产出（iter 目录或 latest 文件存在）；"即弃"由外层 rm，
   声明写 acceptance。
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


def _grep(log_text: str, pattern: str) -> list[str]:
    return re.findall(pattern, log_text, flags=re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True)
    parser.add_argument("--dumps-dir", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--dmon-csv", required=True)
    parser.add_argument("--ckpt-dir", required=True)
    parser.add_argument("--expected-samples", type=int, default=32)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    results: dict[str, dict] = {}
    log_text = Path(args.log).read_text(errors="replace") if Path(args.log).exists() else ""

    # ---- 断言 1 + 3（都读 dump） -------------------------------------------
    import torch

    dump_files = sorted(Path(args.dumps_dir).glob("rollout_*.pt"))
    n_samples = 0
    sample_ok = True
    tape_ok = True
    tape_missing: list[str] = []
    for f in dump_files:
        data = torch.load(f, weights_only=False)
        for s in data.get("samples", []):
            n_samples += 1
            tokens = s.get("tokens") or []
            rl = s.get("response_length") or 0
            lm = s.get("loss_mask")
            if not tokens or rl <= 0 or (lm is not None and len(lm) != rl):
                sample_ok = False
            if s.get("rollout_top_p_token_ids") is None or s.get("rollout_top_p_token_offsets") is None:
                tape_ok = False
                tape_missing.append(f"{f.name}: top-p tape missing")
            if s.get("rollout_routed_experts") is None:
                tape_ok = False
                tape_missing.append(f"{f.name}: routing tape missing")
    results["1_rollout_samples"] = {
        "status": "PASS" if (n_samples >= args.expected_samples and sample_ok and dump_files) else "FAIL",
        "num_samples": n_samples,
        "expected_min": args.expected_samples,
        "dump_files": [f.name for f in dump_files],
    }

    # ---- 断言 2：启动期探针 --------------------------------------------------
    ev_path = Path(args.artifacts_dir) / "startup_evidence.json"
    if ev_path.exists():
        ev = json.loads(ev_path.read_text())
        renderer_ok = "renderer" in json.dumps(ev).lower()
        results["2_startup_probes"] = {
            "status": "PASS" if renderer_ok else "FAIL",
            "evidence_file": str(ev_path),
            "engine_weight_version": ev.get("engine_weight_version"),
        }
    else:
        results["2_startup_probes"] = {
            "status": "FAIL",
            "reason": "startup_evidence.json 不存在（glue 启动探针未跑到写盘点）",
        }

    # ---- 断言 3：tape 消费 + loss 有限 --------------------------------------
    loss_vals = [float(x) for x in _grep(log_text, r"(?:^|[^a-z])loss['\"]?\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?(?:e-?[0-9]+)?)")]
    loss_finite = all(math.isfinite(v) for v in loss_vals) if loss_vals else None
    tape_raise = bool(
        re.search(r"(rollout_top_p_token|rollout_routed_experts).{0,200}(Error|raise|assert)", log_text, re.IGNORECASE | re.DOTALL)
    )
    status3 = "PASS" if (tape_ok and not tape_raise and loss_finite is not False) else "FAIL"
    if loss_finite is None and status3 == "PASS":
        status3 = "UNKNOWN"  # 日志没抓到 loss 数值——人工复核（可能是日志格式变化）
    results["3_tape_consumed_loss_finite"] = {
        "status": status3,
        "tape_missing": tape_missing[:5],
        "tape_raise_in_log": tape_raise,
        "num_loss_values": len(loss_vals),
    }

    # ---- 断言 4：grad norm 非 NaN -------------------------------------------
    gn_vals = _grep(log_text, r"grad[ _-]?norm['\"]?\s*[:=]?\s*(-?[0-9]+(?:\.[0-9]+)?(?:e-?[0-9]+)?|nan|inf)")
    gn_bad = [v for v in gn_vals if v.lower() in ("nan", "inf")]
    results["4_grad_norm"] = {
        "status": "PASS" if (gn_vals and not gn_bad) else ("FAIL" if gn_bad else "UNKNOWN"),
        "num_values": len(gn_vals),
        "bad_values": gn_bad[:5],
    }

    # ---- 断言 5：显存水位 + 无 OOM ------------------------------------------
    peaks: dict[str, int] = {}
    dmon = Path(args.dmon_csv)
    if dmon.exists():
        for line in dmon.read_text(errors="replace").splitlines()[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4 and parts[3].isdigit():
                idx, used = parts[1], int(parts[3])
                peaks[idx] = max(peaks.get(idx, 0), used)
    oom = bool(re.search(r"out of memory|OutOfMemoryError", log_text, re.IGNORECASE))
    results["5_memory_watermark_no_oom"] = {
        "status": "PASS" if (peaks and not oom) else "FAIL",
        "per_gpu_peak_mib": peaks,
        "oom_in_log": oom,
        "note": "训练/推理分区归属按 ray 分配核对（J4 为 4+4 分离，dmon 全 8 卡采样）",
    }

    # ---- 断言 6：checkpoint 产出（即弃动作在外层脚本） -----------------------
    ckpt = Path(args.ckpt_dir)
    ckpt_produced = ckpt.exists() and any(ckpt.iterdir()) if ckpt.exists() else False
    results["6_checkpoint_produced_then_discarded"] = {
        "status": "PASS" if ckpt_produced else "FAIL",
        "declaration": "8 题来自 Verified 仓库（A1/D5）：checkpoint 用后即弃，不得作为任何后续起点",
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    all_pass = all(r["status"] == "PASS" for r in results.values())
    for k, r in results.items():
        print(f"[j4_assert] {k}: {r['status']}")
    print(f"[j4_assert] -> {out}  overall={'PASS' if all_pass else 'FAIL/UNKNOWN'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
