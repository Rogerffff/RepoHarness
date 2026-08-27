#!/usr/bin/env python3
"""miles GPU spike G1 机器验收：采集 + 判定（P0-6；本机可 --self-test）。

设计（沿 miles_integration_lanes.sh 的"manifest 单事实源"模式）：
  - 阈值唯一来源 = 同目录 thresholds.md 的第一个 ```json 代码块（judge 解析；
    脚本内不复制阈值常量）。
  - 证据输入 = miles 侧结构化事件 jsonl（miles/utils/rh2_event_log.py，由
    MILES_RH2_EVENT_DIR 开启；patch 0004）。collect 只做归一化与联结，**不做
    日志正则**，也没有任何"租期校准位"——事件缺失就在 collect_report 登记并
    由 judge 记 MISSING_EVIDENCE（总判定 INCOMPLETE，缺证据不算绿）。
  - 判定档位：PASS / FAIL / MISSING_EVIDENCE；总判定 PASS / FAIL / INCOMPLETE。

事件 -> 证据的联结关系（生产事件 schema 见 rh2_event_log 各 emit 调用点）：
  train_step            每 optimizer step、每 rank 一条：outcome、
                        optimizer_step_applied（真实 optimizer.step() 执行成功
                        才为 true——NORMAL 枚举不作 applied 证据）、Adam/scheduler
                        前后计数、dis_* token 记账（pp 末级 rank 携带）。
  train_step_consumed   每 (rollout, step, dp_rank) 一条：该分片被消费的全局
                        sample index（queue exactly-once + 正控消费证明）。
  train_rollout         trainer 侧消费时刻的 current weight version（staleness
                        的独立事实；行为版本列表不得顶替）。
  weight_update /       发布事实：version before/after、耗时；
  weight_publish_skipped 全 SKIPPED 区间的"有意不发布"显式事实。
  rollout_group         样本身份/reward/逐 turn 行为版本/routing tape digest。
  rollout_workers       每轮引擎身份集合（worker 保温）。
  group_filtered        拒绝路径证据（aborted / 动态过滤丢弃的组）。
  logprob_compare       同版本 behavior(support-normalized) vs current
                        (support-renorm，trainer 复算) 逐 token 均值绝对差。
  eval_smoke            eval 路径冒烟完成事实。
  actor_identity        每类 actor 的 miles tree digest（P0-4 一致性）。

证据契约（evidence 目录，collect 产出 + launch post-run 探针）：
  step_records.jsonl、sample_records.jsonl、actor_identity.json、
  eval_smoke.json、resource_summary.json（collect 产出）；
  checkpoint_probe.json、shutdown_probe.json（launch.sh post-run 产出）。

用法::
  python3 g1_acceptance.py collect --events-dir E \
      [--dmon-csv C --gpu-mem-total-mb N] --out-dir EV
  python3 g1_acceptance.py judge --evidence-dir EV --thresholds thresholds.md \
      --r3 on|off [--custom-config custom_config.yaml] [--out verdict.json]
  python3 g1_acceptance.py --self-test
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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# collect：结构化事件 -> 归一化证据（联结缺口如实登记，不补正则不留占位）
# ---------------------------------------------------------------------------

_EVENT_FILE_GLOB = "rh2_events_*.jsonl"


def _load_events(events_dir: Path) -> dict[str, list[dict]]:
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(events_dir.glob(_EVENT_FILE_GLOB)):
        for row in read_jsonl(path):
            by_kind[row.get("event", "?")].append(row)
    return by_kind


def _consistent(values: list, label: str, conflicts: list[str]):
    """跨 rank 事实必须一致；不一致登记 conflict（judge 判 FAIL，不是 MISSING）。"""
    distinct = {json.dumps(v, sort_keys=True) for v in values}
    if len(distinct) > 1:
        conflicts.append(f"{label} 跨 rank 不一致: {sorted(distinct)}")
        return None
    return values[0] if values else None


def _min_numeric_version(versions: list) -> int | None:
    numeric = [int(v) for v in versions if str(v).isdigit()]
    return min(numeric) if numeric else None


def cmd_collect(args: argparse.Namespace) -> int:
    events_dir = Path(args.events_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    conflicts: list[str] = []

    if not events_dir.is_dir() or not list(events_dir.glob(_EVENT_FILE_GLOB)):
        missing.append(f"events：{events_dir} 下无 {_EVENT_FILE_GLOB}（生产侧 MILES_RH2_EVENT_DIR 未启用？）")
        ev = defaultdict(list)
    else:
        ev = _load_events(events_dir)

    # -- trainer current version（rollout -> version）------------------------
    current_version: dict[int, int] = {}
    for row in ev["train_rollout"]:
        rid, v = row.get("rollout_id"), row.get("trainer_current_version")
        if rid is None or v is None:
            continue
        if rid in current_version and current_version[rid] != v:
            conflicts.append(f"train_rollout r{rid} current_version 冲突: {current_version[rid]} vs {v}")
        current_version[rid] = int(v)
    if not current_version:
        missing.append("train_rollout：无 trainer current version 事件（staleness/版本前进无独立事实）")

    # -- 发布事实 -------------------------------------------------------------
    weight_updates: dict[object, dict] = {}
    for row in ev["weight_update"]:
        weight_updates[row.get("rollout_id")] = row
    publish_skipped_rollouts = {row.get("rollout_id") for row in ev["weight_publish_skipped"]}
    if not ev["weight_update"] and not ev["weight_publish_skipped"]:
        missing.append("weight_update/weight_publish_skipped：无发布事实（weight_version_after 无法确定）")

    # -- step 级：train_step ⋈ train_step_consumed ---------------------------
    steps_by_key: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in ev["train_step"]:
        steps_by_key[(row["rollout_id"], row["step_id"])].append(row)
    consumed_by_key: dict[tuple[int, int], dict[int, dict]] = defaultdict(dict)
    for row in ev["train_step_consumed"]:
        # 同 (rollout, step, dp_rank) 多条（TP/PP 复本）内容相同，保留一条。
        consumed_by_key[(row["rollout_id"], row["step_id"])][row.get("dp_rank", 0)] = row

    workers_by_rollout = {row["rollout_id"]: row.get("worker_ids") for row in ev["rollout_workers"]}
    if not workers_by_rollout:
        missing.append("rollout_workers：无引擎身份事件（worker 保温无证据）")

    step_rows: list[dict] = []
    last_step_of_rollout: dict[int, int] = {}
    for (rid, sid) in steps_by_key:
        last_step_of_rollout[rid] = max(last_step_of_rollout.get(rid, -1), sid)
    for (rid, sid) in sorted(steps_by_key):
        rank_rows = steps_by_key[(rid, sid)]
        outcome = _consistent([r.get("outcome") for r in rank_rows], f"step r{rid}s{sid}.outcome", conflicts)
        applied = _consistent(
            [r.get("optimizer_step_applied") for r in rank_rows], f"step r{rid}s{sid}.applied", conflicts
        )
        counters = {}
        for key in ("adam_step_before", "adam_step_after", "scheduler_steps_before", "scheduler_steps_after"):
            vals = [r.get(key) for r in rank_rows if r.get(key) is not None]
            counters[key] = _consistent(vals, f"step r{rid}s{sid}.{key}", conflicts) if vals else None
        metric_rows = [r for r in rank_rows if r.get("metrics")]
        metrics = metric_rows[0]["metrics"] if metric_rows else {}
        consumed_shards = consumed_by_key.get((rid, sid), {})
        consumed_ids: list[str] | None = None
        num_tokens = None
        if consumed_shards:
            merged: list[int] = []
            tok = 0
            tok_known = True
            for _dp, row in sorted(consumed_shards.items()):
                if row.get("sample_indices") is None:
                    conflicts.append(f"step r{rid}s{sid} consumed 分片缺 sample_indices: {row.get('error')}")
                    continue
                merged.extend(int(i) for i in row["sample_indices"])
                if row.get("num_tokens") is None:
                    tok_known = False
                else:
                    tok += int(row["num_tokens"])
            consumed_ids = sorted(str(i) for i in merged)
            num_tokens = tok if tok_known else None
        duration_vals = [r.get("duration_seconds") for r in rank_rows if r.get("duration_seconds") is not None]
        duration = max(duration_vals) if duration_vals else None
        v_before = current_version.get(rid)
        if sid == last_step_of_rollout.get(rid):
            if rid in weight_updates:
                v_after = weight_updates[rid].get("version_after")
            elif rid in publish_skipped_rollouts:
                v_after = v_before  # 显式"有意不发布"事实：版本保持
            else:
                v_after = None  # 无发布事实 -> MISSING（不是默认保持）
        else:
            v_after = v_before
        step_rows.append(
            {
                "rollout_id": rid,
                "step_id": sid,
                "outcome": outcome,
                "optimizer_step_applied": applied,
                **counters,
                "weight_version_before": v_before,
                "weight_version_after": v_after,
                "dis_accepted_tokens": metrics.get("dis_accepted_tokens"),
                "dis_rejected_tokens": metrics.get("dis_rejected_tokens"),
                "dis_microbatch_provenance_tokens": metrics.get("dis_microbatch_provenance_tokens"),
                "worker_ids": workers_by_rollout.get(rid),
                "queue_consumed_sample_ids": consumed_ids,
                "num_tokens": num_tokens,
                "duration_seconds": duration,
                "weight_update_seconds": (
                    weight_updates[rid].get("duration_seconds")
                    if sid == last_step_of_rollout.get(rid) and rid in weight_updates
                    else None
                ),
                "throughput_tokens_per_sec": (
                    round(num_tokens / duration, 3) if num_tokens and duration else None
                ),
            }
        )
    if not step_rows:
        missing.append("train_step：无 optimizer step 事件（step_records 为空）")
    write_jsonl(out_dir / "step_records.jsonl", step_rows)

    # -- 训练消费面：sample_index -> 是否被真实 applied step 消费 --------------
    consumed_step_applied: dict[str, bool] = {}
    for row in step_rows:
        for sid_ in row.get("queue_consumed_sample_ids") or []:
            consumed_step_applied[sid_] = consumed_step_applied.get(sid_, False) or bool(
                row.get("optimizer_step_applied")
            )

    # -- 对拍摘要：sample_index -> 同版本均值绝对差 ---------------------------
    logprob_diff: dict[int, float] = {}
    for row in ev["logprob_compare"]:
        for entry in row.get("entries", []):
            if entry.get("same_version") and entry.get("mean_abs_diff") is not None:
                logprob_diff[int(entry["sample_index"])] = float(entry["mean_abs_diff"])
    if not ev["logprob_compare"]:
        missing.append("logprob_compare：无对拍事件（同版本 logprob 差无证据）")

    # -- sample 级：rollout_group + group_filtered ---------------------------
    sample_rows: list[dict] = []
    for row in sorted(ev["rollout_group"], key=lambda r: (r.get("rollout_id", -1), r.get("group_index", -1))):
        rid = row.get("rollout_id")
        gid = f"r{rid}/g{row.get('group_index')}"
        indices = row.get("sample_indices") or []
        rewards = row.get("rewards") or []
        versions = row.get("behavior_versions") or []
        tapes = row.get("routing_tape") or []
        for i, sample_index in enumerate(indices):
            behavior_versions = versions[i] if i < len(versions) else []
            sample_rows.append(
                {
                    "sample_id": str(sample_index),
                    "source": "train_batch",
                    "instance_id": row.get("instance_id"),
                    "group_id": gid,
                    "reward": rewards[i] if i < len(rewards) else None,
                    "behavior_versions": behavior_versions,
                    "behavior_version": _min_numeric_version(behavior_versions),
                    "current_version": current_version.get(rid),
                    "same_version_mean_abs_logprob_diff": logprob_diff.get(int(sample_index)),
                    "routing_tape": tapes[i] if i < len(tapes) else None,
                    "trained": consumed_step_applied.get(str(sample_index), False),
                }
            )
    if not any(r["source"] == "train_batch" for r in sample_rows):
        missing.append("rollout_group：无训练批样本事件（sample_records 无训练面）")
    for ordinal, row in enumerate(ev["group_filtered"]):
        indices = row.get("sample_indices") or []
        rewards = row.get("rewards") or []
        for i, sample_index in enumerate(indices):
            sample_rows.append(
                {
                    "sample_id": str(sample_index),
                    "source": "filtered",
                    "filtered_reason": row.get("reason"),
                    "instance_id": row.get("instance_id"),
                    "group_id": f"filtered{ordinal}/g{row.get('group_index')}",
                    "reward": rewards[i] if i < len(rewards) else None,
                    "behavior_versions": None,
                    "behavior_version": None,
                    "current_version": None,
                    "same_version_mean_abs_logprob_diff": None,
                    "routing_tape": None,
                    "trained": False,
                }
            )
    write_jsonl(out_dir / "sample_records.jsonl", sample_rows)

    # -- identity ------------------------------------------------------------
    if ev["actor_identity"]:
        digests = sorted({row.get("tree_digest") for row in ev["actor_identity"]})
        expected = sorted({row.get("expected_tree_digest") for row in ev["actor_identity"] if row.get("expected_tree_digest")})
        (out_dir / "actor_identity.json").write_text(
            json.dumps(
                {
                    "roles": sorted({row.get("role") for row in ev["actor_identity"]}),
                    "num_events": len(ev["actor_identity"]),
                    "tree_digests": digests,
                    "expected_tree_digests": expected,
                    "consistent": len(digests) == 1 and (not expected or expected == digests),
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    else:
        missing.append("actor_identity：无 identity 事件（P0-4 worker 侧 integration tree 无证据）")

    # -- eval 冒烟 -----------------------------------------------------------
    if ev["eval_smoke"]:
        (out_dir / "eval_smoke.json").write_text(
            json.dumps({"ran": True, "ok": all(bool(r.get("ok")) for r in ev["eval_smoke"])}),
            encoding="utf-8",
        )
    else:
        missing.append("eval_smoke：无 eval 冒烟事件（不落盘 eval_smoke.json，judge 记 MISSING）")

    # -- 资源摘要 ------------------------------------------------------------
    resource = {
        "gpu_mem_peak_frac": None,
        "throughput_tokens_per_sec": None,
        "weight_update_seconds_max_observed": None,
    }
    throughputs = [r["throughput_tokens_per_sec"] for r in step_rows if r.get("throughput_tokens_per_sec")]
    if throughputs:
        resource["throughput_tokens_per_sec"] = max(throughputs)  # 稳态代理：取最好 step，避免首步预热压低
    else:
        missing.append("resource_summary.throughput：step 事件缺 num_tokens/duration")
    update_secs = [r.get("duration_seconds") for r in ev["weight_update"] if r.get("duration_seconds") is not None]
    if update_secs:
        resource["weight_update_seconds_max_observed"] = max(update_secs)
    if args.dmon_csv and args.gpu_mem_total_mb:
        peak = _dmon_peak_fb_mb(Path(args.dmon_csv))
        if peak is not None:
            resource["gpu_mem_peak_frac"] = peak / float(args.gpu_mem_total_mb)
        else:
            missing.append("resource_summary.gpu_mem_peak_frac：dmon CSV 无 fb 列")
    else:
        missing.append("resource_summary：未提供 --dmon-csv/--gpu-mem-total-mb")
    (out_dir / "resource_summary.json").write_text(
        json.dumps(resource, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    report = {
        "event_counts": {k: len(v) for k, v in sorted(ev.items())},
        "step_rows": len(step_rows),
        "sample_rows": len(sample_rows),
        "conflicts": conflicts,
        "missing": missing,
    }
    (out_dir / "collect_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print("collect 完成；missing 项在 judge 中成为 MISSING_EVIDENCE，conflicts 项成为 FAIL（都不算绿）。")
    return 0


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


_VALID_OUTCOMES = {"NORMAL", "SKIPPED_ZERO_SIGNAL"}


def cmd_judge(args: argparse.Namespace) -> int:
    ev = Path(args.evidence_dir)
    th = load_thresholds(Path(args.thresholds))
    j = Judge(th, args.r3)

    steps = read_jsonl(ev / "step_records.jsonl") if (ev / "step_records.jsonl").exists() else None
    if steps is not None and not steps:
        steps = None
    samples = (
        read_jsonl(ev / "sample_records.jsonl") if (ev / "sample_records.jsonl").exists() else None
    )
    if samples is not None and not samples:
        samples = None
    train_samples = [s for s in samples if s.get("source") == "train_batch"] if samples else None

    # -- collect 联结冲突（证据在场但互相矛盾 = FAIL，不是 MISSING）-----------
    report_path = ev / "collect_report.json"
    if report_path.exists():
        conflicts = json.loads(report_path.read_text()).get("conflicts", [])
        if conflicts:
            j.add("collect_consistency", FAIL, "; ".join(conflicts[:6]))

    # -- G1 规模 --------------------------------------------------------------
    if steps is None:
        j.add("g1_min_rollouts", MISSING, "step_records.jsonl 缺失或为空")
        j.add("g1_min_applied_optimizer_steps", MISSING, "step_records.jsonl 缺失或为空")
    else:
        rids = {s["rollout_id"] for s in steps if s.get("rollout_id") is not None}
        need = th["g1_min_rollouts"]
        j.add(
            "g1_min_rollouts",
            PASS if len(rids) >= need else FAIL,
            f"观测 rollout 轮数={len(rids)}（需 ≥{need}）",
        )
        bad_outcomes = sorted({s.get("outcome") for s in steps} - _VALID_OUTCOMES - {None})
        if bad_outcomes:
            j.add("g1_min_applied_optimizer_steps", FAIL, f"未知 outcome：{bad_outcomes}")
        elif any(s.get("outcome") is None or s.get("optimizer_step_applied") is None for s in steps):
            j.add("g1_min_applied_optimizer_steps", MISSING, "存在 outcome/optimizer_step_applied 未知的 step")
        else:
            applied = sum(1 for s in steps if s["optimizer_step_applied"] is True)
            need = th["g1_min_applied_optimizer_steps"]
            j.add(
                "g1_min_applied_optimizer_steps",
                PASS if applied >= need else FAIL,
                f"optimizer_step_applied=True 的 step={applied}（需 ≥{need}；判据是独立 applied 事实，"
                "NORMAL 枚举不计入——found-inf/debug 路径可为 NORMAL 而未更新）",
            )

    # -- applied 与 Adam/scheduler 计数一致性（B2 独立事实交叉验证）-----------
    if steps is None:
        j.add("optimizer_step_progress_consistent", MISSING, "step_records.jsonl 缺失")
    else:
        problems, unknown = [], 0
        for s in steps:
            ab, aa = s.get("adam_step_before"), s.get("adam_step_after")
            sb, sa = s.get("scheduler_steps_before"), s.get("scheduler_steps_after")
            applied = s.get("optimizer_step_applied")
            if None in (ab, aa, sb, sa) or applied is None:
                unknown += 1
                continue
            tag = f"r{s.get('rollout_id')}s{s.get('step_id')}"
            if applied and not (aa == ab + 1 and sa > sb):
                problems.append(f"{tag}: applied 但计数未前进 adam {ab}->{aa} sched {sb}->{sa}")
            if not applied and not (aa == ab and sa == sb):
                problems.append(f"{tag}: 未 applied 但计数前进 adam {ab}->{aa} sched {sb}->{sa}")
        if problems:
            j.add("optimizer_step_progress_consistent", FAIL, "; ".join(problems[:4]))
        elif unknown:
            j.add("optimizer_step_progress_consistent", MISSING, f"{unknown} 个 step 缺计数/applied 事实")
        else:
            j.add(
                "optimizer_step_progress_consistent",
                PASS,
                "applied<=>Adam step +1 且 scheduler 前进；skip 步计数不动",
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
    if steps is None or any(
        s.get("weight_version_after") is None or s.get("weight_version_before") is None for s in steps
    ):
        j.add("weight_version_monotonic", MISSING, "weight_version 证据缺失（train_rollout/weight_update 事件不全）")
    else:
        ok, detail = _check_versions(steps)
        j.add("weight_version_monotonic", PASS if ok else FAIL, detail)
    if train_samples is None:
        j.add("staleness_max_versions", MISSING, "sample_records.jsonl 缺失")
    else:
        vals = [
            s["current_version"] - s["behavior_version"]
            for s in train_samples
            if s.get("current_version") is not None and s.get("behavior_version") is not None
        ]
        if not vals:
            j.add("staleness_max_versions", MISSING, "无版本对样本（train_rollout current version 缺失？）")
        else:
            worst = max(vals)
            lim = th["staleness_max_versions"]
            j.add(
                "staleness_max_versions",
                PASS if worst <= lim else FAIL,
                f"最大 staleness={worst}（上限 {lim}；current=trainer 事实，behavior=逐 turn 最旧版本）",
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
                j.add("token_accounting_must_balance", MISSING, "dis_* 指标不全（train_step.metrics 缺失）")
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
    if train_samples is None:
        j.add("logprob_same_version_mean_abs_diff_max", MISSING, "sample_records.jsonl 缺失")
    else:
        diffs = [
            s["same_version_mean_abs_logprob_diff"]
            for s in train_samples
            if s.get("same_version_mean_abs_logprob_diff") is not None
        ]
        if not diffs:
            j.add("logprob_same_version_mean_abs_diff_max", MISSING, "无同版本对拍摘要（logprob_compare 事件缺失）")
        else:
            worst = max(diffs)
            lim = th["logprob_same_version_mean_abs_diff_max"]
            j.add(
                "logprob_same_version_mean_abs_diff_max",
                PASS if worst <= lim else FAIL,
                f"同版本逐 token 均值绝对差最大={worst:.4g}（上限 {lim}）",
            )

    # -- routing tape（R3 显式选择对应的形状义务；只约束进入训练批的样本）-----
    _judge_routing(j, train_samples)

    # -- 正控组（P0-5：方差 + 被真实 applied step 消费）-----------------------
    _judge_positive_control(j, samples, steps)

    # -- integration tree identity（P0-4 worker 侧）---------------------------
    if th.get("integration_tree_identity_required"):
        ident_path = ev / "actor_identity.json"
        if not ident_path.exists():
            j.add("integration_tree_identity", MISSING, "actor_identity.json 缺失（无 identity 事件）")
        else:
            ident = json.loads(ident_path.read_text())
            ok = bool(ident.get("consistent"))
            j.add(
                "integration_tree_identity",
                PASS if ok else FAIL,
                (
                    f"全部 actor（{', '.join(ident.get('roles', []))}）tree digest 一致且与钉死值相符"
                    if ok
                    else f"tree digest 不一致或与钉死值不符：{ident.get('tree_digests')} vs {ident.get('expected_tree_digests')}"
                ),
            )

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
            "无重复消费（跨全部 step/rollout exactly-once）" if not dups else f"重复消费：{dups}",
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
        "训练消费完成后 eval 路径冒烟通过",
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
                j.add(key, MISSING, "resource_summary 字段为空（对应事件/dmon 输入缺失）")
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
    if not samples:
        j.add(key, MISSING, "R3=on 但无训练批样本（rollout_group 事件缺失）——零样本不能证明 tape 合形")
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


def _judge_positive_control(j: Judge, samples: list[dict] | None, steps: list[dict] | None) -> None:
    th = j.th
    if samples is None:
        j.add("positive_control_min_groups_with_reward_std", MISSING, "sample_records.jsonl 缺失")
        j.add("positive_control_consumed_by_applied_step", MISSING, "sample_records.jsonl 缺失")
        j.add("zero_variance_groups_must_not_train", MISSING, "sample_records.jsonl 缺失")
        return
    if not any(s.get("source") == "train_batch" for s in samples):
        j.add("positive_control_min_groups_with_reward_std", MISSING, "无训练批样本（rollout_group 事件缺失）")
        j.add("positive_control_consumed_by_applied_step", MISSING, "无训练批样本（rollout_group 事件缺失）")
        j.add("zero_variance_groups_must_not_train", MISSING, "无训练批样本（rollout_group 事件缺失）")
        return
    groups: dict = defaultdict(list)
    for s in samples:
        groups[(s.get("instance_id"), s.get("group_id"))].append(s)
    pc_instances = set(th["positive_control_instances"])
    pc_groups_with_std: list[tuple] = []
    for key, rows in groups.items():
        iid, _gid = key
        rewards = [r.get("reward") for r in rows if r.get("reward") is not None]
        if iid in pc_instances and len(rewards) >= 2 and len(set(rewards)) > 1:
            pc_groups_with_std.append(key)
    need = th["positive_control_min_groups_with_reward_std"]
    j.add(
        "positive_control_min_groups_with_reward_std",
        PASS if len(pc_groups_with_std) >= need else FAIL,
        f"正控实例组中 reward std>0 的组数={len(pc_groups_with_std)}（需 ≥{need}；正控口径 = "
        "基础设施验收记账，不得表述为训练效果——见 positive_control.md）",
    )

    # B2：正控不止有方差，还必须被某个真实 applied optimizer step 消费。
    if th.get("positive_control_must_be_consumed_by_applied_step"):
        if not steps or any(s.get("queue_consumed_sample_ids") is None or s.get("optimizer_step_applied") is None for s in steps):
            j.add("positive_control_consumed_by_applied_step", MISSING, "step 消费/applied 证据缺失")
        else:
            consumed_all = {x for s in steps for x in s["queue_consumed_sample_ids"]}
            applied_consumed = {
                x for s in steps if s["optimizer_step_applied"] is True for x in s["queue_consumed_sample_ids"]
            }
            qualifying = []
            for key in pc_groups_with_std:
                rows = groups[key]
                ids = {r["sample_id"] for r in rows}
                if ids <= consumed_all and ids & applied_consumed:
                    qualifying.append(key[1])
            j.add(
                "positive_control_consumed_by_applied_step",
                PASS if qualifying else FAIL,
                (
                    f"正控组 {qualifying} 全部样本被消费且 ≥1 样本进入 optimizer_step_applied=True 的 step"
                    if qualifying
                    else "没有任何 reward std>0 的正控组被真实 applied step 消费（方差 ≠ 驱动更新）"
                ),
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
            "全等 reward 组均未被 applied step 消费（filter/SKIPPED 语义成立）"
            if not offenders
            else f"进训的零方差组：{offenders}",
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
# self-test：代表性事件目录 -> collect -> judge 全链；
# 好例 PASS；坏例命中对应 FAIL；删任一必要事件 -> INCOMPLETE。
# ---------------------------------------------------------------------------

_SELFTEST_SEQ = 0

_TREE_DIGEST = "d1" * 32  # 代表性 identity digest

# 每 rollout 2 个 optimizer step、dp 2 分片、每轮 2 组 × 8 样本。
_N_ROLLOUTS, _STEPS_PER_ROLLOUT, _GROUP_SIZE = 3, 2, 8
_WORKERS = ["train/aa01", "train/aa02"]


def _selftest_write_events(ev_dir: Path, *, mutate: str = "") -> None:
    """生成与 miles rh2_event_log 生产 schema 同形的代表性事件文件。"""
    events: list[dict] = []

    def emit(kind: str, **fields):
        events.append({"event": kind, "ts_unix": 0.0, "host": "h", "pid": 1, **fields})

    for role in ("driver", "megatron_train_actor", "rollout_manager", "sglang_server"):
        digest = _TREE_DIGEST
        if mutate == "identity_mismatch" and role == "sglang_server":
            digest = "ee" * 32
        emit("actor_identity", role=role, miles_file=f"/opt/miles/{role}.py",
             tree_digest=digest, expected_tree_digest=_TREE_DIGEST)

    emit("weight_update", rollout_id=None, version_before=0, version_after=1, duration_seconds=40.0)

    adam = 0
    sched = 0
    version = 1
    sample_seq = 0
    for rid in range(_N_ROLLOUTS):
        emit("train_rollout", rollout_id=rid, trainer_current_version=version)
        emit("rollout_workers", rollout_id=rid,
             worker_ids=list(_WORKERS) if not (mutate == "worker_churn" and rid == 2) else ["train/bb99"],
             weight_version=version)

        # 每轮 2 组：rollout 0 的第 0 组是唯一正控组（reward 混合），其余轮用
        # 非正控实例——保证 pc_* 坏例不会被别的轮的正控组洗绿；
        # 另有一个零方差组被动态过滤（group_filtered 事件）。
        pc_iid = "django__django-11099" if rid == 0 else f"sympy__sympy-2059{rid}"
        group_specs = [
            (pc_iid, [1.0 if k % 4 == 0 else 0.0 for k in range(_GROUP_SIZE)]),
            ("astropy__astropy-14365", [1.0 if k % 2 == 0 else 0.0 for k in range(_GROUP_SIZE)]),
        ]
        if mutate == "pc_all_zero" and rid == 0:
            group_specs[0] = (pc_iid, [0.0] * _GROUP_SIZE)
        rollout_sample_ids: list[int] = []
        for g, (iid, rewards) in enumerate(group_specs):
            indices = list(range(sample_seq, sample_seq + _GROUP_SIZE))
            sample_seq += _GROUP_SIZE
            rollout_sample_ids.extend(indices)
            behavior = [[str(version)] for _ in indices]
            if mutate == "stale_behavior" and rid == 0 and g == 0:
                behavior = [["1", "3"] for _ in indices]  # trainer current=version；行为列表末位≠current
            tapes = [
                {"shape": [511, 48, 8], "dtype": "int32", "digest": "ab" * 32, "expected_rows": 511}
                for _ in indices
            ]
            if mutate == "bad_tape_shape" and rid == 0 and g == 0:
                tapes[0] = {"shape": [511, 47, 8], "dtype": "int32", "digest": "ab" * 32, "expected_rows": 511}
            emit("rollout_group", rollout_id=rid, group_index=g, instance_id=iid,
                 sample_indices=indices, rewards=rewards,
                 behavior_versions=behavior,
                 statuses=["Status.COMPLETED"] * _GROUP_SIZE,
                 response_lengths=[400] * _GROUP_SIZE,
                 routing_tape=tapes)
        zero_var_indices = list(range(sample_seq, sample_seq + _GROUP_SIZE))
        sample_seq += _GROUP_SIZE
        emit("group_filtered", reason="zero_std_0.0", group_index=90 + rid,
             instance_id="psf__requests-2931", sample_indices=zero_var_indices,
             rewards=[0.0] * _GROUP_SIZE)
        if mutate == "zero_var_trained":
            # 零方差组混进训练批并被 applied step 消费：必须 FAIL。
            emit("rollout_group", rollout_id=rid, group_index=90 + rid, instance_id="psf__requests-2931",
                 sample_indices=zero_var_indices, rewards=[0.0] * _GROUP_SIZE,
                 behavior_versions=[[str(version)]] * _GROUP_SIZE,
                 statuses=["Status.COMPLETED"] * _GROUP_SIZE, response_lengths=[400] * _GROUP_SIZE,
                 routing_tape=[{"shape": [511, 48, 8], "dtype": "int32", "digest": "cd" * 32, "expected_rows": 511}] * _GROUP_SIZE)
            rollout_sample_ids.extend(zero_var_indices)

        emit("logprob_compare", rollout_id=rid, dp_rank=0, trainer_current_version=version,
             entries=[{"sample_index": i, "same_version": True, "mean_abs_diff": 0.01,
                       "num_tokens": 400, "length_mismatch": False}
                      for i in rollout_sample_ids])

        # 2 个 optimizer step；dp0/dp1 各消费一半。
        per_step = len(rollout_sample_ids) // _STEPS_PER_ROLLOUT
        for sid in range(_STEPS_PER_ROLLOUT):
            outcome, applied = "NORMAL", True
            if mutate == "one_skipped_rollout" and rid == 2:
                outcome, applied = "SKIPPED_ZERO_SIGNAL", False
            if mutate == "normal_not_applied":
                applied = False  # found-inf 型：NORMAL 但没有真实 optimizer.step()
            if mutate == "pc_not_applied" and rid == 0 and sid == 0:
                # 正控组所在 step 被跳过：方差在场但没有驱动更新。
                outcome, applied = "SKIPPED_ZERO_SIGNAL", False
            adam_b, sched_b = adam, sched
            if applied:
                adam += 1
                sched += 32
            if mutate == "counter_mismatch" and rid == 0 and sid == 0:
                adam = adam_b  # applied=True 但 Adam 计数没动：交叉验证必须 FAIL
            step_samples = rollout_sample_ids[sid * per_step:(sid + 1) * per_step]
            half = len(step_samples) // 2
            for dp_rank, shard in ((0, step_samples[:half]), (1, step_samples[half:])):
                emit("train_step_consumed", rollout_id=rid, step_id=sid, dp_rank=dp_rank,
                     rank=dp_rank, sample_indices=shard, num_tokens=500 * max(len(shard), 1))
            for rank in range(2):
                accepted = 900.0 if outcome == "NORMAL" else 0.0
                rejected = 100.0 if outcome == "NORMAL" else 1000.0
                emit("train_step", rollout_id=rid, step_id=sid, attempt=0,
                     outcome=outcome, optimizer_step_applied=applied,
                     adam_step_before=adam_b, adam_step_after=adam,
                     scheduler_steps_before=sched_b, scheduler_steps_after=sched,
                     grad_norm=0.5 if applied else 0.0, duration_seconds=20.0,
                     rank=rank, dp_rank=rank, is_pp_last_stage=(rank == 0),
                     metrics=(
                         {"dis_accepted_tokens": accepted, "dis_rejected_tokens": rejected,
                          "dis_microbatch_provenance_tokens": accepted + rejected}
                         if rank == 0 else None
                     ))

        # 发布语义与 patch 0003 对齐：本轮有 applied step 才发布并进版本。
        any_applied_this_rollout = not (
            (mutate == "one_skipped_rollout" and rid == 2) or mutate == "normal_not_applied"
        )
        if any_applied_this_rollout:
            before = version
            version += 1
            if mutate == "version_regress" and rid == 1:
                version = before - 1
            emit("weight_update", rollout_id=rid, version_before=before, version_after=version,
                 duration_seconds=40.0)
            emit("weight_publish", rollout_id=rid)
        else:
            emit("weight_publish_skipped", rollout_id=rid)

    emit("eval_smoke", rollout_id=_N_ROLLOUTS - 1, ok=True, num_metrics=3)

    drop_kind = {
        "drop_train_step": "train_step",
        "drop_train_step_consumed": "train_step_consumed",
        "drop_train_rollout": "train_rollout",
        "drop_rollout_group": "rollout_group",
        "drop_rollout_workers": "rollout_workers",
        "drop_logprob_compare": "logprob_compare",
        "drop_eval_smoke": "eval_smoke",
        "drop_actor_identity": "actor_identity",
    }.get(mutate)
    if drop_kind:
        events = [e for e in events if e["event"] != drop_kind]
    if mutate == "drop_publish_facts":
        events = [e for e in events if e["event"] not in ("weight_update", "weight_publish", "weight_publish_skipped")]

    ev_dir.mkdir(parents=True)
    write_jsonl(ev_dir / "rh2_events_h_1.jsonl", events)


def _selftest_evidence(tmp: Path, *, mutate: str = "") -> Path:
    global _SELFTEST_SEQ  # noqa: PLW0603 - self-test 专用序号
    _SELFTEST_SEQ += 1
    base = tmp / f"case_{_SELFTEST_SEQ}_{mutate or 'good'}"
    events_dir = base / "events"
    out_dir = base / "evidence"
    _selftest_write_events(events_dir, mutate=mutate)
    ns = argparse.Namespace(
        events_dir=str(events_dir), dmon_csv=None, gpu_mem_total_mb=None, out_dir=str(out_dir)
    )
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_collect(ns)
    # dmon 在 self-test 无输入：直接补一个合规资源摘要（launch 实跑时由 collect 产出）。
    res = json.loads((out_dir / "resource_summary.json").read_text())
    if res.get("gpu_mem_peak_frac") is None:
        res["gpu_mem_peak_frac"] = 0.9
    (out_dir / "resource_summary.json").write_text(json.dumps(res))
    if mutate != "missing_shutdown":
        (out_dir / "shutdown_probe.json").write_text('{"orphan_workers": 0, "unfinalized_deliveries": 0}')
    (out_dir / "checkpoint_probe.json").write_text('{"saved": true, "reloaded": true, "deleted": true}')
    return out_dir


def _run_judge(ev: Path, r3: str = "on") -> dict:
    ns = argparse.Namespace(
        evidence_dir=str(ev), thresholds=str(HERE / "thresholds.md"), r3=r3,
        custom_config=str(HERE / "custom_config.yaml"), out=str(ev / "verdict.json"),
    )
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_judge(ns)
    return json.loads((ev / "verdict.json").read_text())


def cmd_selftest() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        def check(cond: bool, msg: str) -> None:
            (failures.append(msg) if not cond else None)

        def failed_checks(v: dict) -> set[str]:
            return {c["check"] for c in v["checks"] if c["status"] == FAIL}

        v = _run_judge(_selftest_evidence(tmp))
        check(v["overall"] == "PASS", f"好例应 PASS，得 {v['overall']}: "
              + "; ".join(f"{c['check']}={c['status']}" for c in v["checks"] if c["status"] != PASS))

        # --- 删任一必要事件 -> INCOMPLETE（B1 修复验收）---------------------
        for mutate in (
            "drop_train_step", "drop_train_step_consumed", "drop_train_rollout",
            "drop_rollout_group", "drop_rollout_workers", "drop_logprob_compare",
            "drop_eval_smoke", "drop_actor_identity", "drop_publish_facts",
        ):
            v = _run_judge(_selftest_evidence(tmp, mutate=mutate))
            check(
                v["overall"] == "INCOMPLETE",
                f"{mutate} 应 INCOMPLETE，得 {v['overall']}",
            )

        # --- B2 oracle：NORMAL 枚举不再当 applied 证据 ----------------------
        v = _run_judge(_selftest_evidence(tmp, mutate="normal_not_applied"))
        check("g1_min_applied_optimizer_steps" in failed_checks(v),
              f"全 NORMAL 但无 applied 应 FAIL 规模项，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="counter_mismatch"))
        check("optimizer_step_progress_consistent" in failed_checks(v),
              f"applied 但计数未前进应 FAIL，got {failed_checks(v)}")

        # current_version 必须来自 train_rollout 的 trainer 事实，不得取行为
        # 版本列表末位（B2 复现：behavior=["1","3"] 而 trainer current=1）。
        ev_dir = _selftest_evidence(tmp, mutate="stale_behavior")
        rows = [r for r in read_jsonl(ev_dir / "sample_records.jsonl") if r.get("behavior_versions") == ["1", "3"]]
        check(bool(rows) and all(r["current_version"] == 1 for r in rows),
              f"current_version 必须取 trainer 事实（=1）而非 behavior[-1]=3，got {[r.get('current_version') for r in rows][:3]}")
        check(bool(rows) and all(r["behavior_version"] == 1 for r in rows),
              "behavior_version 应为逐 turn 最旧数值版本 min=1")

        v = _run_judge(_selftest_evidence(tmp, mutate="pc_not_applied"))
        check("positive_control_consumed_by_applied_step" in failed_checks(v),
              f"正控组只进 skipped step 应 FAIL 消费项，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="version_regress"))
        check("weight_version_monotonic" in failed_checks(v), f"版本回退应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="pc_all_zero"))
        check("positive_control_min_groups_with_reward_std" in failed_checks(v),
              f"正控全零应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="zero_var_trained"))
        check("zero_variance_groups_must_not_train" in failed_checks(v),
              f"零方差组进训应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="bad_tape_shape"))
        check("routing_tape" in failed_checks(v), f"坏 tape 形状应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="bad_tape_shape"), r3="off")
        check("routing_tape" in failed_checks(v), f"R3=off 但携带 tape 应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="worker_churn"))
        check("g1_worker_warm_across_steps" in failed_checks(v),
              f"worker 集合变化应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="identity_mismatch"))
        check("integration_tree_identity" in failed_checks(v),
              f"actor tree digest 不一致应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="one_skipped_rollout"))
        check(v["overall"] == "PASS",
              f"全 SKIPPED 轮 + 显式不发布应 PASS（版本保持），得 {v['overall']}: "
              + "; ".join(f"{c['check']}={c['status']}:{c['detail']}" for c in v["checks"] if c["status"] != PASS))

        v = _run_judge(_selftest_evidence(tmp, mutate="missing_shutdown"))
        check(v["overall"] == "INCOMPLETE", f"缺 shutdown 证据应 INCOMPLETE，得 {v['overall']}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print(
        "SELF-TEST PASS（代表性事件 collect->judge 全链好例 PASS；9 类事件删除均 INCOMPLETE；"
        "B2 oracle 坏例（NORMAL 非 applied/计数不进/正控未被 applied 消费）及其余坏例命中对应 FAIL）"
    )
    return 0


# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return cmd_selftest()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("collect")
    pc.add_argument("--events-dir", required=True)
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
