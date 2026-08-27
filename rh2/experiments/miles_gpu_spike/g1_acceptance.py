#!/usr/bin/env python3
"""miles GPU spike G1 机器验收：采集 + 判定（P0-6，租期用；本机可 --self-test）。

设计（沿 miles_integration_lanes.sh 的"manifest 单事实源"模式）：
  - 阈值唯一来源 = 同目录 thresholds.md 的第一个 ```json 代码块（judge 解析；
    脚本内不复制阈值常量）。
  - 证据契约 = 两个归一化 jsonl + 若干探针 json（schema 见下）。collect 子命令
    尽力从 train.log / rollout dumps / dmon 抽取；抽不到的字段留空并写进
    collect_report.json 的 missing 清单——**缺证据不算绿**（judge 记
    MISSING_EVIDENCE，总判定 INCOMPLETE）。
  - 判定档位：PASS / FAIL / MISSING_EVIDENCE；总判定 PASS / FAIL / INCOMPLETE。

证据契约（evidence 目录）：
  step_records.jsonl  每 optimizer step 一行::
      {"rollout_id": int, "step_id": int,
       "outcome": "NORMAL" | "SKIPPED_ZERO_SIGNAL",
       "weight_version_before": int, "weight_version_after": int,
       "dis_accepted_tokens": float, "dis_rejected_tokens": float,
       "dis_microbatch_provenance_tokens": float,
       "worker_ids": [str, ...] | null,
       "queue_consumed_sample_ids": [str, ...] | null,
       "weight_update_seconds": float | null,
       "throughput_tokens_per_sec": float | null}
  sample_records.jsonl  每训练候选样本一行::
      {"sample_id": str, "instance_id": str, "group_id": str,
       "reward": float, "behavior_version": int, "current_version": int,
       "same_version_mean_abs_logprob_diff": float | null,
       "routing_tape": {"shape": [int,int,int], "dtype": str,
                        "digest": str, "expected_rows": int | null} | null,
       "trained": bool}
  checkpoint_probe.json  {"saved": bool, "reloaded": bool, "deleted": bool}
  eval_smoke.json        {"ran": bool, "ok": bool}
  shutdown_probe.json    {"orphan_workers": int, "unfinalized_deliveries": int}
  resource_summary.json  {"gpu_mem_peak_frac": float|null,
                          "throughput_tokens_per_sec": float|null,
                          "weight_update_seconds_max_observed": float|null}

用法::
  python3 g1_acceptance.py collect --train-log L [--rollout-dumps D] \
      [--dmon-csv C --gpu-mem-total-mb N] --out-dir EV
  python3 g1_acceptance.py judge --evidence-dir EV --thresholds thresholds.md \
      --r3 on|off [--custom-config custom_config.yaml] [--out verdict.json]
  python3 g1_acceptance.py --self-test

collect 的日志正则是**租期校准位**：dis_* 指标名与 SKIPPED_ZERO_SIGNAL 枚举来自
rh2 faithful_dis_loss.py 与 miles patch 0002（稳定锚点）；其余（版本前进、
worker id、吞吐）在首开机核对实际日志格式后回填正则——在此之前 judge 会如实
报 MISSING_EVIDENCE，而不是假绿。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

PASS, FAIL, MISSING = "PASS", "FAIL", "MISSING_EVIDENCE"


# ---------------------------------------------------------------------------
# 阈值加载（thresholds.md 第一个 ```json 块 = 唯一事实源）
# ---------------------------------------------------------------------------

def load_thresholds(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    # 行首锚定：正文散文里出现的 "```json" 字样（如引言"脚本解析本页第一个
    # ```json 代码块"）不在行首，不会被误认成代码块开栏。
    m = re.search(r"^```json\s*\n(.*?)^```", text, re.DOTALL | re.MULTILINE)
    if not m:
        raise SystemExit(f"FAIL: {path} 内找不到行首 ```json 阈值块")
    return json.loads(m.group(1))


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# collect：train.log / dumps / dmon -> 归一化证据（尽力抽取，缺失如实登记）
# ---------------------------------------------------------------------------

# 稳定锚点（rh2/miles patch 自有产物）；其余日志格式租期校准。
_RE_DIS = {
    "dis_accepted_tokens": re.compile(r"dis_accepted_tokens[^0-9]{0,8}([0-9.eE+-]+)"),
    "dis_rejected_tokens": re.compile(r"dis_rejected_tokens[^0-9]{0,8}([0-9.eE+-]+)"),
    "dis_microbatch_provenance_tokens": re.compile(
        r"dis_microbatch_provenance_tokens[^0-9]{0,8}([0-9.eE+-]+)"
    ),
}
_RE_SKIPPED = re.compile(r"SKIPPED_ZERO_SIGNAL")
_RE_ROLLOUT_ID = re.compile(r"rollout[_ ]id[^0-9]{0,4}(\d+)")


def cmd_collect(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []

    log_text = Path(args.train_log).read_text(encoding="utf-8", errors="replace")

    # 骨架抽取：逐 rollout 的 dis_* 指标与 SKIPPED 事件计数。step 级完整字段
    # （版本、worker id、吞吐）需按实际日志回填正则——先落空并登记 missing。
    dis_hits = {k: rx.findall(log_text) for k, rx in _RE_DIS.items()}
    rollout_ids = sorted({int(x) for x in _RE_ROLLOUT_ID.findall(log_text)})
    skipped_count = len(_RE_SKIPPED.findall(log_text))

    step_rows: list[dict] = []
    n_steps = max((len(v) for v in dis_hits.values()), default=0)
    for i in range(n_steps):
        row = {
            "rollout_id": rollout_ids[min(i, len(rollout_ids) - 1)] if rollout_ids else None,
            "step_id": i,
            "outcome": None,  # 校准位：从 TrainStepOutcome 日志回填
            "weight_version_before": None,
            "weight_version_after": None,
            "worker_ids": None,
            "queue_consumed_sample_ids": None,
            "weight_update_seconds": None,
            "throughput_tokens_per_sec": None,
        }
        for k, hits in dis_hits.items():
            row[k] = float(hits[i]) if i < len(hits) else None
        step_rows.append(row)
    if not step_rows:
        missing.append("step_records：train.log 未匹配到 dis_* 指标（正则校准位）")
    for name in ("outcome", "weight_version_after", "worker_ids"):
        missing.append(f"step_records.{name}：待首开机核对日志格式后回填正则")

    with (out_dir / "step_records.jsonl").open("w", encoding="utf-8") as fh:
        for row in step_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 样本级：优先 rollout dumps（需要 torch，GPU 机在场；本机缺 torch 则登记）。
    sample_rows: list[dict] = []
    if args.rollout_dumps:
        try:
            import torch  # noqa: PLC0415

            for pt in sorted(Path(args.rollout_dumps).glob("rollout_*.pt")):
                payload = torch.load(pt, map_location="cpu", weights_only=False)
                samples = payload.get("samples", payload) if isinstance(payload, dict) else payload
                for j, s in enumerate(_iter_samples(samples)):
                    sample_rows.append(_sample_row(pt.stem, j, s))
        except ImportError:
            missing.append("sample_records：本机无 torch，rollout dumps 未解析（GPU 机执行 collect）")
        except Exception as exc:  # noqa: BLE001 - 骨架：解析失败如实登记，不吞
            missing.append(f"sample_records：dumps 解析失败 {exc!r}（校准位）")
    else:
        missing.append("sample_records：未提供 --rollout-dumps")
    with (out_dir / "sample_records.jsonl").open("w", encoding="utf-8") as fh:
        for row in sample_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 资源摘要：dmon CSV 峰值显存占比（nvidia-smi dmon -s mu 的 fb 列，MiB）。
    resource = {
        "gpu_mem_peak_frac": None,
        "throughput_tokens_per_sec": None,
        "weight_update_seconds_max_observed": None,
    }
    if args.dmon_csv and args.gpu_mem_total_mb:
        peak = _dmon_peak_fb_mb(Path(args.dmon_csv))
        if peak is not None:
            resource["gpu_mem_peak_frac"] = peak / float(args.gpu_mem_total_mb)
        else:
            missing.append("resource_summary.gpu_mem_peak_frac：dmon CSV 无 fb 列（校准位）")
    else:
        missing.append("resource_summary：未提供 --dmon-csv/--gpu-mem-total-mb")
    missing.append("resource_summary.throughput/weight_update：待日志正则校准")
    (out_dir / "resource_summary.json").write_text(
        json.dumps(resource, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    report = {
        "rollout_ids_seen": rollout_ids,
        "skipped_zero_signal_hits": skipped_count,
        "step_rows": len(step_rows),
        "sample_rows": len(sample_rows),
        "missing": missing,
    }
    (out_dir / "collect_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("collect 完成；missing 清单里的项在 judge 中会成为 MISSING_EVIDENCE（不算绿）。")
    return 0


def _iter_samples(samples):
    for item in samples:
        if isinstance(item, (list, tuple)):
            yield from item
        else:
            yield item


def _sample_row(dump_name: str, idx: int, s) -> dict:
    def g(name, default=None):
        return getattr(s, name, default) if not isinstance(s, dict) else s.get(name, default)

    routing = g("rollout_routed_experts")
    tape = None
    if routing is not None:
        import hashlib

        import numpy as np  # dumps 已含 numpy 对象时可用

        arr = np.asarray(routing)
        tokens = g("tokens") or []
        tape = {
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "digest": hashlib.sha256(arr.tobytes()).hexdigest(),
            "expected_rows": (len(tokens) - 1) if tokens else None,
        }
    versions = g("weight_versions") or []
    meta = g("metadata") or {}
    return {
        "sample_id": f"{dump_name}#{idx}",
        "instance_id": meta.get("instance_id") if isinstance(meta, dict) else None,
        "group_id": f"{dump_name}/g{g('group_index')}",
        "reward": g("reward"),
        "behavior_version": _to_int(versions[0]) if versions else None,
        "current_version": _to_int(versions[-1]) if versions else None,
        "same_version_mean_abs_logprob_diff": None,  # 校准位：对拍摘要需 trainer 侧导出
        "routing_tape": tape,
        "trained": bool(g("trained", True)),
    }


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _dmon_peak_fb_mb(path: Path) -> float | None:
    peak = None
    header_cols: list[str] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") and "fb" in line.split():
            header_cols = line.lstrip("#").split()
            continue
        if line.startswith("#") or not line.strip():
            continue
        if header_cols and "fb" in header_cols:
            parts = line.split()
            i = header_cols.index("fb")
            if i < len(parts):
                try:
                    val = float(parts[i])
                except ValueError:
                    continue
                peak = val if peak is None else max(peak, val)
    return peak


# ---------------------------------------------------------------------------
# judge：证据 -> 逐项判定
# ---------------------------------------------------------------------------

class Judge:
    def __init__(self, th: dict, r3: str):
        self.th = th
        self.r3 = r3
        self.checks: list[dict] = []

    def add(self, key: str, status: str, detail: str) -> None:
        self.checks.append({"check": key, "status": status, "detail": detail})

    def overall(self) -> str:
        statuses = {c["status"] for c in self.checks}
        if FAIL in statuses:
            return "FAIL"
        if MISSING in statuses:
            return "INCOMPLETE"
        return "PASS"


def cmd_judge(args: argparse.Namespace) -> int:
    ev = Path(args.evidence_dir)
    th = load_thresholds(Path(args.thresholds))
    j = Judge(th, args.r3)

    steps = read_jsonl(ev / "step_records.jsonl") if (ev / "step_records.jsonl").exists() else None
    samples = (
        read_jsonl(ev / "sample_records.jsonl") if (ev / "sample_records.jsonl").exists() else None
    )

    # -- G1 规模 --------------------------------------------------------------
    if steps is None:
        j.add("g1_min_rollouts", MISSING, "step_records.jsonl 缺失")
        j.add("g1_min_applied_optimizer_steps", MISSING, "step_records.jsonl 缺失")
    else:
        rids = {s["rollout_id"] for s in steps if s.get("rollout_id") is not None}
        need = th["g1_min_rollouts"]
        j.add(
            "g1_min_rollouts",
            PASS if len(rids) >= need else FAIL,
            f"观测 rollout 轮数={len(rids)}（需 ≥{need}）",
        )
        outcomes = [s.get("outcome") for s in steps]
        if any(o is None for o in outcomes):
            j.add("g1_min_applied_optimizer_steps", MISSING, "存在 outcome 未知的 step（collect 校准位未回填）")
        else:
            applied = sum(1 for o in outcomes if o == "NORMAL")
            need = th["g1_min_applied_optimizer_steps"]
            j.add(
                "g1_min_applied_optimizer_steps",
                PASS if applied >= need else FAIL,
                f"applied(NORMAL) step={applied}（需 ≥{need}；SKIPPED_ZERO_SIGNAL 不计入）",
            )

    # -- worker 保温 ----------------------------------------------------------
    if th.get("g1_worker_warm_across_steps"):
        if not steps or any(s.get("worker_ids") is None for s in steps):
            j.add("g1_worker_warm_across_steps", MISSING, "worker_ids 证据缺失")
        else:
            sets = [frozenset(s["worker_ids"]) for s in steps]
            warm = all(x == sets[0] for x in sets)
            j.add(
                "g1_worker_warm_across_steps",
                PASS if warm else FAIL,
                "worker 集合跨 step 不变" if warm else f"worker 集合变化：{[sorted(x) for x in sets]}",
            )

    # -- 版本前进性 / staleness ----------------------------------------------
    if steps is None or any(s.get("weight_version_after") is None for s in steps):
        j.add("weight_version_monotonic", MISSING, "weight_version 证据缺失")
    else:
        ok, detail = _check_versions(steps)
        j.add("weight_version_monotonic", PASS if ok else FAIL, detail)
    if samples is None:
        j.add("staleness_max_versions", MISSING, "sample_records.jsonl 缺失")
    else:
        vals = [
            s["current_version"] - s["behavior_version"]
            for s in samples
            if s.get("current_version") is not None and s.get("behavior_version") is not None
        ]
        if not vals:
            j.add("staleness_max_versions", MISSING, "无版本对样本")
        else:
            worst = max(vals)
            lim = th["staleness_max_versions"]
            j.add(
                "staleness_max_versions",
                PASS if worst <= lim else FAIL,
                f"最大 staleness={worst}（上限 {lim}）",
            )

    # -- token 记账 -----------------------------------------------------------
    if steps is None:
        j.add("token_accounting_must_balance", MISSING, "step_records.jsonl 缺失")
    else:
        bad, msgs = 0, []
        for s in steps:
            a, r, p = (
                s.get("dis_accepted_tokens"),
                s.get("dis_rejected_tokens"),
                s.get("dis_microbatch_provenance_tokens"),
            )
            if None in (a, r, p):
                j.add("token_accounting_must_balance", MISSING, "dis_* 指标不全")
                break
            if abs((a + r) - p) > 1e-6:
                bad += 1
                msgs.append(f"step{s.get('step_id')}: {a}+{r}!={p}")
            if s.get("outcome") == "NORMAL" and a < th["accepted_tokens_min_on_normal_step"]:
                bad += 1
                msgs.append(f"step{s.get('step_id')}: NORMAL 但 accepted={a}")
        else:
            j.add(
                "token_accounting_must_balance",
                PASS if bad == 0 else FAIL,
                "accepted+rejected==provenance 且 NORMAL step accepted 达标" if bad == 0 else "; ".join(msgs),
            )

    # -- logprob 对拍 ---------------------------------------------------------
    if samples is None:
        j.add("logprob_same_version_mean_abs_diff_max", MISSING, "sample_records.jsonl 缺失")
    else:
        diffs = [
            s["same_version_mean_abs_logprob_diff"]
            for s in samples
            if s.get("same_version_mean_abs_logprob_diff") is not None
        ]
        if not diffs:
            j.add("logprob_same_version_mean_abs_diff_max", MISSING, "无对拍摘要（collect 校准位）")
        else:
            worst = max(diffs)
            lim = th["logprob_same_version_mean_abs_diff_max"]
            j.add(
                "logprob_same_version_mean_abs_diff_max",
                PASS if worst <= lim else FAIL,
                f"同版本逐 token 均值绝对差最大={worst:.4g}（上限 {lim}）",
            )

    # -- routing tape（R3 显式选择对应的形状义务）-----------------------------
    _judge_routing(j, samples)

    # -- 正控组（P0-5）--------------------------------------------------------
    _judge_positive_control(j, samples)

    # -- 熔断阈值配置漂移 ------------------------------------------------------
    cc = Path(args.custom_config) if args.custom_config else HERE / "custom_config.yaml"
    if cc.exists():
        m = re.search(r"^max_consecutive_zero_signal_steps:\s*(\d+)\s*$", cc.read_text(), re.M)
        want = th["max_consecutive_zero_signal_steps"]
        if m and int(m.group(1)) == want:
            j.add("max_consecutive_zero_signal_steps", PASS, f"custom_config 与阈值页一致（{want}）")
        else:
            j.add(
                "max_consecutive_zero_signal_steps",
                FAIL,
                f"custom_config={m.group(1) if m else '缺失'} != thresholds {want}（双事实源漂移）",
            )
    else:
        j.add("max_consecutive_zero_signal_steps", MISSING, f"custom_config 不存在：{cc}")

    # -- 关停 / 队列 -----------------------------------------------------------
    _judge_probe(
        j, ev / "shutdown_probe.json", "shutdown_orphan_workers_max",
        lambda d: d.get("orphan_workers", math.inf) <= th["shutdown_orphan_workers_max"]
        and d.get("unfinalized_deliveries", math.inf) <= th["unfinalized_deliveries_max"],
        "orphan_workers/unfinalized_deliveries 达标",
    )
    if steps and all(s.get("queue_consumed_sample_ids") is not None for s in steps):
        seen = Counter(x for s in steps for x in s["queue_consumed_sample_ids"])
        dups = {k: v for k, v in seen.items() if v > 1}
        j.add(
            "queue_duplicate_sample_ids_max",
            PASS if len(dups) <= th["queue_duplicate_sample_ids_max"] else FAIL,
            "无重复消费" if not dups else f"重复消费：{dups}",
        )
    else:
        j.add("queue_duplicate_sample_ids_max", MISSING, "queue_consumed_sample_ids 证据缺失")

    # -- checkpoint / eval 冒烟 ------------------------------------------------
    _judge_probe(
        j, ev / "checkpoint_probe.json", "g1_checkpoint_save_reload_delete",
        lambda d: d.get("saved") and d.get("reloaded") and d.get("deleted"),
        "checkpoint 存/读/删闭环",
    )
    _judge_probe(
        j, ev / "eval_smoke.json", "g1_eval_smoke_after_worker_stop",
        lambda d: d.get("ran") and d.get("ok"),
        "worker 停止后 eval 冒烟通过",
    )

    # -- 资源 ------------------------------------------------------------------
    res_path = ev / "resource_summary.json"
    if res_path.exists():
        res = json.loads(res_path.read_text())
        for key, val, lim, cmp_ok in (
            ("gpu_mem_peak_frac_max", res.get("gpu_mem_peak_frac"), th["gpu_mem_peak_frac_max"], lambda v, x: v <= x),
            ("throughput_min_tokens_per_sec", res.get("throughput_tokens_per_sec"), th["throughput_min_tokens_per_sec"], lambda v, x: v >= x),
            ("weight_update_seconds_max", res.get("weight_update_seconds_max_observed"), th["weight_update_seconds_max"], lambda v, x: v <= x),
        ):
            if val is None:
                j.add(key, MISSING, "resource_summary 字段为空（collect 校准位）")
            else:
                j.add(key, PASS if cmp_ok(val, lim) else FAIL, f"观测={val}（阈值 {lim}）")
    else:
        for key in ("gpu_mem_peak_frac_max", "throughput_min_tokens_per_sec", "weight_update_seconds_max"):
            j.add(key, MISSING, "resource_summary.json 缺失")

    verdict = {
        "overall": j.overall(),
        "r3": args.r3,
        "pre_formal_note": th.get("pre_formal_note"),
        "checks": j.checks,
    }
    out = json.dumps(verdict, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
    print(out)
    print(f"OVERALL: {verdict['overall']}")
    return 0 if verdict["overall"] == "PASS" else 1


def _check_versions(steps: list[dict]) -> tuple[bool, str]:
    prev = None
    per_rollout_outcomes: dict = defaultdict(list)
    for s in steps:
        b, a = s.get("weight_version_before"), s["weight_version_after"]
        if b is not None and a < b:
            return False, f"step{s.get('step_id')} 版本回退 {b}->{a}"
        if prev is not None and a < prev:
            return False, f"step{s.get('step_id')} 版本非单调 {prev}->{a}"
        prev = a
        per_rollout_outcomes[s.get("rollout_id")].append(s)
    for rid, rows in per_rollout_outcomes.items():
        if all(r.get("outcome") == "SKIPPED_ZERO_SIGNAL" for r in rows):
            vs = {r["weight_version_after"] for r in rows} | {
                r["weight_version_before"] for r in rows if r.get("weight_version_before") is not None
            }
            if len(vs) > 1:
                return False, f"rollout {rid} 全 SKIPPED 但版本前进（patch 0003 语义违约）：{sorted(vs)}"
    return True, "版本单调且全 SKIPPED 轮版本不前进"


def _judge_routing(j: Judge, samples: list[dict] | None) -> None:
    key = "routing_tape"
    if samples is None:
        j.add(key, MISSING, "sample_records.jsonl 缺失")
        return
    th = j.th
    if j.r3 == "off":
        with_tape = [s["sample_id"] for s in samples if s.get("routing_tape")]
        j.add(
            key,
            PASS if not with_tape else FAIL,
            "R3=off：全部样本无 routing tape" if not with_tape else f"R3=off 但存在 tape：{with_tape[:5]}",
        )
        return
    bad = []
    for s in samples:
        tape = s.get("routing_tape")
        if tape is None:
            bad.append(f"{s['sample_id']}: 缺 tape")
            continue
        shape = tape.get("shape") or []
        if len(shape) != 3 or shape[1] != th["routing_tape_num_layers"] or shape[2] != th["routing_tape_topk"]:
            bad.append(f"{s['sample_id']}: shape={shape}")
        elif tape.get("expected_rows") is not None and shape[0] != tape["expected_rows"]:
            bad.append(f"{s['sample_id']}: rows={shape[0]} != len(tokens)-1={tape['expected_rows']}")
        elif tape.get("dtype") != th["routing_tape_dtype"]:
            bad.append(f"{s['sample_id']}: dtype={tape.get('dtype')}")
        elif not tape.get("digest"):
            bad.append(f"{s['sample_id']}: 缺 digest")
    j.add(
        key,
        PASS if not bad else FAIL,
        f"R3=on：{len(samples)} 样本 tape 形状/dtype/digest 全合格" if not bad else "; ".join(bad[:6]),
    )


def _judge_positive_control(j: Judge, samples: list[dict] | None) -> None:
    th = j.th
    if samples is None:
        j.add("positive_control_min_groups_with_reward_std", MISSING, "sample_records.jsonl 缺失")
        j.add("zero_variance_groups_must_not_train", MISSING, "sample_records.jsonl 缺失")
        return
    groups: dict = defaultdict(list)
    for s in samples:
        groups[(s.get("instance_id"), s.get("group_id"))].append(s)
    pc_instances = set(th["positive_control_instances"])
    pc_groups_with_std = 0
    for (iid, _gid), rows in groups.items():
        rewards = [r.get("reward") for r in rows if r.get("reward") is not None]
        if iid in pc_instances and len(rewards) >= 2 and len(set(rewards)) > 1:
            pc_groups_with_std += 1
    need = th["positive_control_min_groups_with_reward_std"]
    j.add(
        "positive_control_min_groups_with_reward_std",
        PASS if pc_groups_with_std >= need else FAIL,
        f"正控实例组中 reward std>0 的组数={pc_groups_with_std}（需 ≥{need}；正控口径 = "
        "基础设施验收记账，不得表述为训练效果——见 positive_control.md）",
    )
    if th.get("zero_variance_groups_must_not_train"):
        offenders = []
        for (iid, gid), rows in groups.items():
            rewards = [r.get("reward") for r in rows]
            if len(rows) >= 2 and len(set(rewards)) == 1 and any(r.get("trained") for r in rows):
                offenders.append(f"{iid}/{gid}")
        j.add(
            "zero_variance_groups_must_not_train",
            PASS if not offenders else FAIL,
            "全等 reward 组均未进训（filter/SKIPPED 语义成立）" if not offenders else f"进训的零方差组：{offenders}",
        )


def _judge_probe(j: Judge, path: Path, key: str, ok_fn, ok_msg: str) -> None:
    if not path.exists():
        j.add(key, MISSING, f"{path.name} 缺失")
        return
    try:
        data = json.loads(path.read_text())
    except ValueError as exc:
        j.add(key, FAIL, f"{path.name} 不是合法 JSON：{exc}")
        return
    j.add(key, PASS if ok_fn(data) else FAIL, ok_msg if ok_fn(data) else f"{path.name} 未达标：{data}")


# ---------------------------------------------------------------------------
# self-test：喂样例 jsonl，断言判定器行为（好例 PASS；各坏例命中对应 FAIL）
# ---------------------------------------------------------------------------

_SELFTEST_SEQ = 0


def _selftest_evidence(tmp: Path, *, mutate: str = "") -> Path:
    global _SELFTEST_SEQ  # noqa: PLW0603 - self-test 专用：同一变体可多次生成（如 bad_tape_shape 在 r3=on/off 各判一次）
    _SELFTEST_SEQ += 1
    ev = tmp / f"ev_{_SELFTEST_SEQ}_{mutate or 'good'}"
    ev.mkdir()
    steps = []
    version = 1
    for rid in range(3):
        for sid in range(2):
            outcome = "NORMAL"
            before = version
            version += 1
            steps.append(
                {
                    "rollout_id": rid, "step_id": rid * 2 + sid, "outcome": outcome,
                    "weight_version_before": before, "weight_version_after": version,
                    "dis_accepted_tokens": 900.0, "dis_rejected_tokens": 100.0,
                    "dis_microbatch_provenance_tokens": 1000.0,
                    "worker_ids": ["w0", "w1"],
                    "queue_consumed_sample_ids": [f"r{rid}s{sid}a", f"r{rid}s{sid}b"],
                    "weight_update_seconds": 42.0, "throughput_tokens_per_sec": 800.0,
                }
            )
    if mutate == "one_applied_step":
        for s in steps[1:]:
            s["outcome"] = "SKIPPED_ZERO_SIGNAL"
    if mutate == "version_regress":
        steps[3]["weight_version_after"] = 1
    samples = []
    for i in range(8):  # 正控组：11099，混合 reward
        samples.append(
            {
                "sample_id": f"pc#{i}", "instance_id": "django__django-11099", "group_id": "d0/g0",
                "reward": 1.0 if i % 4 == 0 else 0.0, "behavior_version": 1, "current_version": 2,
                "same_version_mean_abs_logprob_diff": 0.01,
                "routing_tape": {"shape": [511, 48, 8], "dtype": "int32", "digest": "ab" * 32, "expected_rows": 511},
                "trained": True,
            }
        )
    for i in range(8):  # 全零组：不得进训
        samples.append(
            {
                "sample_id": f"zz#{i}", "instance_id": "psf__requests-2931", "group_id": "d0/g1",
                "reward": 0.0, "behavior_version": 2, "current_version": 2,
                "same_version_mean_abs_logprob_diff": 0.02,
                "routing_tape": {"shape": [400, 48, 8], "dtype": "int32", "digest": "cd" * 32, "expected_rows": 400},
                "trained": False,
            }
        )
    if mutate == "pc_all_zero":
        for s in samples:
            if s["sample_id"].startswith("pc#"):
                s["reward"] = 0.0
                s["trained"] = False
    if mutate == "zero_var_trained":
        for s in samples:
            if s["sample_id"].startswith("zz#"):
                s["trained"] = True
    if mutate == "bad_tape_shape":
        samples[0]["routing_tape"]["shape"] = [511, 47, 8]
    if mutate == "missing_shutdown":
        pass  # 通过不写 shutdown_probe.json 体现
    with (ev / "step_records.jsonl").open("w") as fh:
        for r in steps:
            fh.write(json.dumps(r) + "\n")
    with (ev / "sample_records.jsonl").open("w") as fh:
        for r in samples:
            fh.write(json.dumps(r) + "\n")
    if mutate != "missing_shutdown":
        (ev / "shutdown_probe.json").write_text('{"orphan_workers": 0, "unfinalized_deliveries": 0}')
    (ev / "checkpoint_probe.json").write_text('{"saved": true, "reloaded": true, "deleted": true}')
    (ev / "eval_smoke.json").write_text('{"ran": true, "ok": true}')
    (ev / "resource_summary.json").write_text(
        '{"gpu_mem_peak_frac": 0.9, "throughput_tokens_per_sec": 800.0,'
        ' "weight_update_seconds_max_observed": 42.0}'
    )
    return ev


def _run_judge(ev: Path, r3: str = "on") -> dict:
    ns = argparse.Namespace(
        evidence_dir=str(ev), thresholds=str(HERE / "thresholds.md"), r3=r3,
        custom_config=str(HERE / "custom_config.yaml"), out=str(ev / "verdict.json"),
    )
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_judge(ns)
    return json.loads((ev / "verdict.json").read_text())


def cmd_selftest() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        def check(cond: bool, msg: str) -> None:
            (failures.append(msg) if not cond else None)

        v = _run_judge(_selftest_evidence(tmp))
        check(v["overall"] == "PASS", f"好例应 PASS，得 {v['overall']}")

        v = _run_judge(_selftest_evidence(tmp, mutate="one_applied_step"))
        bad = {c["check"] for c in v["checks"] if c["status"] == FAIL}
        check("g1_min_applied_optimizer_steps" in bad, f"单 applied step 应 FAIL 规模项，got {bad}")

        v = _run_judge(_selftest_evidence(tmp, mutate="version_regress"))
        bad = {c["check"] for c in v["checks"] if c["status"] == FAIL}
        check("weight_version_monotonic" in bad, f"版本回退应 FAIL，got {bad}")

        v = _run_judge(_selftest_evidence(tmp, mutate="pc_all_zero"))
        bad = {c["check"] for c in v["checks"] if c["status"] == FAIL}
        check("positive_control_min_groups_with_reward_std" in bad, f"正控全零应 FAIL，got {bad}")

        v = _run_judge(_selftest_evidence(tmp, mutate="zero_var_trained"))
        bad = {c["check"] for c in v["checks"] if c["status"] == FAIL}
        check("zero_variance_groups_must_not_train" in bad, f"零方差组进训应 FAIL，got {bad}")

        v = _run_judge(_selftest_evidence(tmp, mutate="bad_tape_shape"))
        bad = {c["check"] for c in v["checks"] if c["status"] == FAIL}
        check("routing_tape" in bad, f"坏 tape 形状应 FAIL，got {bad}")

        v = _run_judge(_selftest_evidence(tmp, mutate="bad_tape_shape"), r3="off")
        bad = {c["check"] for c in v["checks"] if c["status"] == FAIL}
        check("routing_tape" in bad, f"R3=off 但携带 tape 应 FAIL，got {bad}")

        v = _run_judge(_selftest_evidence(tmp, mutate="missing_shutdown"))
        check(v["overall"] == "INCOMPLETE", f"缺 shutdown 证据应 INCOMPLETE，得 {v['overall']}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-TEST PASS（好例 PASS；6 个坏例命中对应 FAIL；缺证据 INCOMPLETE 不算绿）")
    return 0


# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return cmd_selftest()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("collect")
    pc.add_argument("--train-log", required=True)
    pc.add_argument("--rollout-dumps")
    pc.add_argument("--artifacts")
    pc.add_argument("--dmon-csv")
    pc.add_argument("--gpu-mem-total-mb", type=float)
    pc.add_argument("--out-dir", required=True)
    pj = sub.add_parser("judge")
    pj.add_argument("--evidence-dir", required=True)
    pj.add_argument("--thresholds", required=True)
    pj.add_argument("--r3", choices=["on", "off"], required=True)
    pj.add_argument("--custom-config")
    pj.add_argument("--out")
    args = parser.parse_args(argv)
    return cmd_collect(args) if args.cmd == "collect" else cmd_judge(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
