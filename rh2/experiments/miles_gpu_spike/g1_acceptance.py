#!/usr/bin/env python3
"""miles GPU spike G1 机器验收：采集 + 判定（P0-6；本机可 --self-test）。

设计（沿 miles_integration_lanes.sh 的"manifest 单事实源"模式）：
  - 阈值唯一来源 = 同目录 thresholds.md 的第一个 ```json 代码块（judge 解析；
    脚本内不复制阈值常量）。
  - 证据输入 = miles 侧结构化事件 jsonl（miles/utils/rh2_event_log.py，由
    MILES_RH2_EVENT_DIR 开启；patch 0004/0005）。collect 只做归一化与联结，
    **不做日志正则**，也没有任何"租期校准位"——事件缺失就在 collect_report
    登记并由 judge 记 MISSING_EVIDENCE（总判定 INCOMPLETE，缺证据不算绿）。
  - 判定档位：PASS / FAIL / MISSING_EVIDENCE / NOT_APPLICABLE；总判定
    PASS / FAIL / INCOMPLETE。NOT_APPLICABLE 只用于按执行模式设计上不存在的
    观测面（如 s1_compat 无 FileFinalizationStore），如实标注，不冒充零。

租前完整审查（codex_miles_prerental_full_audit_20260828.md）修复要点：
  - PR-P0-1：collect 校验每条事件的 run_id（--run-id），异 run 事件 = 污染
    conflict（FAIL）；输出目录先写 .tmp 再原子 rename，collect 失败不会留下
    可被 judge 消费的半成品；judge 用 run_manifest.json 反向核对 run_id 与
    thresholds digest（run_identity 检查）。
  - PR-P0-3A：eval 冒烟绑定 rollout/weight_version，只有发生在最后一次
    applied→publish 之后（版本=期望终版、轮次=最后一轮）的 eval 才能关闭
    g1_eval_smoke_post_train；pre-train eval 冒充必红。
  - PR-P0-3B：shutdown 探针的 docker/ray 查询失败显式 FAIL（查询失败≠零）；
    s1_compat 的 finalization 检查如实 NOT_APPLICABLE。
  - PR-P0-4：integration_tree_identity 要求四类生产 role 全部到场
    （identity_required_role_prefixes）且 expected digest 非空。
  - PR-P0-5：R3 判定新增 trainer 侧 replay fill/consume/exhausted 窄事件
    （routing_replay_trainer_consumption + routing_replay_source_linkage），
    source tape 存在不再单独作数。
  - PR-P0-6：weight_publish_conservation 按 update_weights_interval 双向联结
    applied step ↔ weight_update ↔ weight_publish ↔ 版本 +1。
  - PR-P0-7：train_step_consumed 由 miles 侧真实 micro-batch 边界产出
    （等分推断已删）；collect 对同 (rollout,step,dp) 冲突内容记 conflict。
  - PR-P0-8：queue_multiset_conservation（admitted==consumed、filtered 不相交）、
    train_step_rank_coverage（预期 dp rank 齐全）、staleness 双边界
    （0 <= s <= limit，缺版本 FAIL）、logprob_alignment_and_coverage
    （length_mismatch 必红、同版本样本全覆盖、loss_mask=1 口径）、
    positive_control_accepted_tokens（正控组自身要有 accepted token）。

聚焦复核（codex_pr_p0_recheck）3 个残余假绿的收口（本轮）：
  - finding 1（P0-5/8）：replay 消费链按 thresholds 声明的 run topology
    （expected_trainer_global_ranks/expected_dp_ranks）建立预期 rank census，
    逐 (rollout, global_rank[, step]) 联结 fill/logprob 前向/step 消费/耗尽；
    同 dp 组 PP/EP 副本的 fill sample_digests 必须一致（不再 setdefault 取首条）。
  - finding 2（P0-6）：bootstrap update（rollout_id=None）必须有且唯一；每个
    interval 的 update.version_before/发布后版本与 train_rollout 的 trainer
    current 双向锚定——发布账本自洽不再单独作数。
  - finding 3（P0-8）：staleness 判定逐 turn 验证完整 behavior_versions 列表
    （逐项存在、可解析、<= current），min 折叠不得隐藏 future/损坏项。

事件 -> 证据的联结关系（生产事件 schema 见 rh2_event_log 各 emit 调用点）：
  train_step            每 optimizer step、每 rank 一条：outcome、
                        optimizer_step_applied（真实 optimizer.step() 执行成功
                        才为 true——NORMAL 枚举不作 applied 证据）、Adam/scheduler
                        前后计数、dis_* token 记账（pp 末级 rank 携带）、
                        zero_signal_scan_seconds（P1-2 独立计时）。
  train_step_consumed   每 (rollout, step, dp_rank) 一条：该分片被消费的全局
                        sample index（真实 DataIterator 边界；queue multiset +
                        正控消费证明）。
  train_rollout         trainer 侧消费时刻的 current weight version。
  weight_update /       发布事实（trainer 侧版本推进 + driver 侧 publish/
  weight_publish /      有意跳过），三类原始事实全部保留供守恒判定。
  weight_publish_skipped
  rollout_group         样本身份/reward/逐 turn 行为版本/routing tape digest。
  rollout_workers       每轮引擎身份集合（sglang 引擎稳定性）。
  group_filtered        拒绝路径证据（aborted / 动态过滤丢弃的组）。
  logprob_compare       同版本 behavior vs current 逐 token 均值绝对差
                        （loss_mask=1 口径；length_mismatch 一等事实）。
  sample_dis_accounting 逐样本 DIS accepted/provenance token 计数（custom loss
                        产出；正控归因）。
  replay_fill /         R3 trainer 侧消费证据（fill 队列、logprob 前向与逐
  replay_consume /      optimizer step 的 pop 计数、耗尽）。
  replay_exhausted
  eval_smoke            eval 路径冒烟完成事实（rollout + weight_version 绑定）。
  actor_identity        每类 actor 的 miles tree digest（P0-4 一致性）。

证据契约（evidence 目录布局）：
  evidence/
    run_manifest.json         launch.sh 在 Ray 启动前写入（run_id/代码事实）
    checkpoint_probe.json     postrun_probes.py checkpoint（launch post-run）
    shutdown_probe.json       postrun_probes.py shutdown（launch post-run）
    collected/                collect 原子发布的归一化证据目录：
      step_records.jsonl  sample_records.jsonl  publish_records.json
      replay_records.json actor_identity.json   eval_smoke.json
      resource_summary.json  collect_report.json

用法::
  python3 g1_acceptance.py collect --events-dir E [--run-id RID] \
      [--dmon-csv C --gpu-mem-total-mb N] --out-dir EV/collected
  python3 g1_acceptance.py judge --evidence-dir EV --thresholds thresholds.md \
      --r3 on|off [--custom-config custom_config.yaml] [--out verdict.json]
  python3 g1_acceptance.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

PASS, FAIL, MISSING, NA = "PASS", "FAIL", "MISSING_EVIDENCE", "NOT_APPLICABLE"

COLLECTED_DIR_NAME = "collected"


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


def _load_events(events_dir: Path, run_id: str | None, conflicts: list[str]) -> dict[str, list[dict]]:
    """读入全部事件；--run-id 给定时异 run 事件 = 证据污染（conflict/FAIL）。"""
    by_kind: dict[str, list[dict]] = defaultdict(list)
    foreign: Counter = Counter()
    for path in sorted(events_dir.glob(_EVENT_FILE_GLOB)):
        for row in read_jsonl(path):
            if run_id is not None and row.get("run_id") != run_id:
                foreign[str(row.get("run_id"))] += 1
                continue
            by_kind[row.get("event", "?")].append(row)
    if foreign:
        conflicts.append(
            f"事件目录混入非本 run 事件（run_id 期望 {run_id}）：{dict(foreign)}——"
            "run root 未隔离或旧证据泄漏，判定不可信"
        )
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


def _dedupe_fact(store: dict, key, fact: dict, label: str, conflicts: list[str]) -> None:
    """同 key 重复事实（TP/PP 复本）内容必须一致；不一致 = conflict。"""
    if key in store and store[key] != fact:
        conflicts.append(f"{label} {key} 重复且内容冲突: {store[key]} vs {fact}")
        return
    store[key] = fact


def cmd_collect(args: argparse.Namespace) -> int:
    events_dir = Path(args.events_dir)
    final_dir = Path(args.out_dir)
    if final_dir.exists():
        raise SystemExit(
            f"FAIL: collect 输出目录已存在：{final_dir}（unique run root 不变量——"
            "同一 run 只 collect 一次；重跑请换 run root）"
        )
    # P0-1：先写 .tmp，全部成功后原子 rename 发布；中途失败不留半成品。
    out_dir = final_dir.parent / (final_dir.name + ".tmp")
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    missing: list[str] = []
    conflicts: list[str] = []

    if not events_dir.is_dir() or not list(events_dir.glob(_EVENT_FILE_GLOB)):
        missing.append(f"events：{events_dir} 下无 {_EVENT_FILE_GLOB}（生产侧 MILES_RH2_EVENT_DIR 未启用？）")
        ev = defaultdict(list)
    else:
        ev = _load_events(events_dir, args.run_id, conflicts)

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

    # -- 发布事实（P0-6：update/publish/skipped 三类原始事实全部保留）---------
    publish_records = {
        "updates": [
            {
                "rollout_id": row.get("rollout_id"),
                "version_before": row.get("version_before"),
                "version_after": row.get("version_after"),
                "duration_seconds": row.get("duration_seconds"),
            }
            for row in ev["weight_update"]
        ],
        "publishes": [row.get("rollout_id") for row in ev["weight_publish"]],
        "skips": [row.get("rollout_id") for row in ev["weight_publish_skipped"]],
    }
    (out_dir / "publish_records.json").write_text(
        json.dumps(publish_records, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    weight_updates: dict[int, dict] = {}
    for row in ev["weight_update"]:
        if row.get("rollout_id") is not None:
            weight_updates[row["rollout_id"]] = row
    publish_skipped_rollouts = {row.get("rollout_id") for row in ev["weight_publish_skipped"]}
    if not ev["weight_update"] and not ev["weight_publish_skipped"]:
        missing.append("weight_update/weight_publish_skipped：无发布事实（weight_version_after 无法确定）")

    # -- step 级：train_step ⋈ train_step_consumed ---------------------------
    steps_by_key: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in ev["train_step"]:
        steps_by_key[(row["rollout_id"], row["step_id"])].append(row)
    consumed_by_key: dict[tuple[int, int], dict[int, dict]] = defaultdict(dict)
    for row in ev["train_step_consumed"]:
        # 同 (rollout, step, dp_rank) 多条（TP/PP 复本）内容必须相同；冲突 =
        # 消费账本被改写（P0-8），记 conflict 而不是静默覆盖。
        key = (row["rollout_id"], row["step_id"])
        dp = row.get("dp_rank", 0)
        fact = {
            "sample_indices": row.get("sample_indices"),
            "num_tokens": row.get("num_tokens"),
            "num_microbatches": row.get("num_microbatches"),
            "error": row.get("error"),
        }
        _dedupe_fact(
            consumed_by_key[key], dp, fact, f"train_step_consumed r{key[0]}s{key[1]} dp", conflicts
        )

    workers_by_rollout = {row["rollout_id"]: row.get("worker_ids") for row in ev["rollout_workers"]}
    if not workers_by_rollout:
        missing.append("rollout_workers：无引擎身份事件（sglang 引擎稳定性无证据）")

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
        dp_ranks: list[int] | None = None
        if consumed_shards:
            merged: list[int] = []
            tok = 0
            tok_known = True
            dp_ranks = sorted(consumed_shards)
            for _dp, fact in sorted(consumed_shards.items()):
                if fact.get("sample_indices") is None:
                    conflicts.append(f"step r{rid}s{sid} consumed 分片缺 sample_indices: {fact.get('error')}")
                    continue
                merged.extend(int(i) for i in fact["sample_indices"])
                if fact.get("num_tokens") is None:
                    tok_known = False
                else:
                    tok += int(fact["num_tokens"])
            consumed_ids = sorted(str(i) for i in merged)
            num_tokens = tok if tok_known else None
        duration_vals = [r.get("duration_seconds") for r in rank_rows if r.get("duration_seconds") is not None]
        duration = max(duration_vals) if duration_vals else None
        scan_vals = [
            r.get("zero_signal_scan_seconds") for r in rank_rows if r.get("zero_signal_scan_seconds") is not None
        ]
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
                "dp_ranks": dp_ranks,
                "num_tokens": num_tokens,
                "duration_seconds": duration,
                "zero_signal_scan_seconds_max": max(scan_vals) if scan_vals else None,
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

    # -- 对拍摘要：sample_index -> loss_mask=1 口径事实（P0-8）----------------
    logprob_facts: dict[int, dict] = {}
    for row in ev["logprob_compare"]:
        for entry in row.get("entries", []):
            idx = int(entry["sample_index"])
            fact = {
                "same_version": bool(entry.get("same_version")),
                "mean_abs_diff": entry.get("mean_abs_diff"),
                "length_mismatch": entry.get("length_mismatch"),
                "num_tokens": entry.get("num_tokens"),
            }
            _dedupe_fact(logprob_facts, idx, fact, "logprob_compare sample", conflicts)
    if not ev["logprob_compare"]:
        missing.append("logprob_compare：无对拍事件（同版本 logprob 差无证据）")

    # -- 逐样本 DIS token 记账（正控归因，P0-8）-------------------------------
    dis_facts: dict[int, dict] = {}
    for row in ev["sample_dis_accounting"]:
        for entry in row.get("entries", []):
            idx = int(entry["sample_index"])
            fact = {
                "accepted_tokens": entry.get("accepted_tokens"),
                "provenance_tokens": entry.get("provenance_tokens"),
            }
            _dedupe_fact(dis_facts, idx, fact, "sample_dis_accounting sample", conflicts)

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
            lp = logprob_facts.get(int(sample_index))
            dis = dis_facts.get(int(sample_index))
            sample_rows.append(
                {
                    "sample_id": str(sample_index),
                    "rollout_id": rid,
                    "source": "train_batch",
                    "instance_id": row.get("instance_id"),
                    "group_id": gid,
                    "reward": rewards[i] if i < len(rewards) else None,
                    "behavior_versions": behavior_versions,
                    "behavior_version": _min_numeric_version(behavior_versions),
                    "current_version": current_version.get(rid),
                    "has_logprob_entry": lp is not None,
                    "same_version_mean_abs_logprob_diff": (
                        lp["mean_abs_diff"] if lp and lp["same_version"] else None
                    ),
                    "logprob_length_mismatch": lp["length_mismatch"] if lp else None,
                    "logprob_masked_tokens": lp["num_tokens"] if lp else None,
                    "dis_accepted_tokens": dis["accepted_tokens"] if dis else None,
                    "dis_provenance_tokens": dis["provenance_tokens"] if dis else None,
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
                    "rollout_id": None,
                    "source": "filtered",
                    "filtered_reason": row.get("reason"),
                    "instance_id": row.get("instance_id"),
                    "group_id": f"filtered{ordinal}/g{row.get('group_index')}",
                    "reward": rewards[i] if i < len(rewards) else None,
                    "behavior_versions": None,
                    "behavior_version": None,
                    "current_version": None,
                    "has_logprob_entry": False,
                    "same_version_mean_abs_logprob_diff": None,
                    "logprob_length_mismatch": None,
                    "logprob_masked_tokens": None,
                    "dis_accepted_tokens": None,
                    "dis_provenance_tokens": None,
                    "routing_tape": None,
                    "trained": False,
                }
            )
    write_jsonl(out_dir / "sample_records.jsonl", sample_rows)

    # -- R3 trainer 侧 replay 事实（P0-5）-------------------------------------
    fills: dict[tuple, dict] = {}
    for row in ev["replay_fill"]:
        key = (row.get("manager"), row.get("rollout_id"), row.get("rank"))
        fact = {k: row.get(k) for k in (
            "manager", "rollout_id", "rank", "dp_rank", "enabled", "num_streams",
            "records_min", "records_max", "expected_records", "num_samples", "sample_digests",
        )}
        _dedupe_fact(fills, key, fact, "replay_fill", conflicts)
    consumes: dict[tuple, dict] = {}
    for row in ev["replay_consume"]:
        key = (row.get("manager"), row.get("rollout_id"), row.get("phase"), row.get("step_id"), row.get("rank"))
        fact = {k: row.get(k) for k in (
            "manager", "rollout_id", "phase", "step_id", "rank", "dp_rank", "num_streams",
            "num_microbatches", "forward_pops_min", "forward_pops_max",
            "backward_pops_min", "backward_pops_max", "queue_len_min", "queue_len_max",
        )}
        _dedupe_fact(consumes, key, fact, "replay_consume", conflicts)
    exhausteds: dict[tuple, dict] = {}
    for row in ev["replay_exhausted"]:
        key = (row.get("manager"), row.get("rollout_id"), row.get("rank"))
        fact = {k: row.get(k) for k in (
            "manager", "rollout_id", "rank", "dp_rank", "num_streams", "exhausted",
            "queue_len_min", "queue_len_max", "forward_pops_min", "forward_pops_max",
            "backward_pops_min", "backward_pops_max",
        )}
        _dedupe_fact(exhausteds, key, fact, "replay_exhausted", conflicts)
    (out_dir / "replay_records.json").write_text(
        json.dumps(
            {
                "fills": list(fills.values()),
                "consumes": list(consumes.values()),
                "exhausted": list(exhausteds.values()),
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

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

    # -- eval 冒烟（P0-3A：保留 rollout/version 绑定事实）---------------------
    if ev["eval_smoke"]:
        (out_dir / "eval_smoke.json").write_text(
            json.dumps(
                {
                    "events": [
                        {
                            "rollout_id": r.get("rollout_id"),
                            "ok": bool(r.get("ok")),
                            "weight_version": r.get("weight_version"),
                        }
                        for r in ev["eval_smoke"]
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    else:
        missing.append("eval_smoke：无 eval 冒烟事件（不落盘 eval_smoke.json，judge 记 MISSING）")

    # -- 资源摘要 ------------------------------------------------------------
    resource = {
        "gpu_mem_peak_frac": None,
        "throughput_tokens_per_sec": None,
        "weight_update_seconds_max_observed": None,
        "zero_signal_scan_seconds_max": None,
    }
    throughputs = [r["throughput_tokens_per_sec"] for r in step_rows if r.get("throughput_tokens_per_sec")]
    if throughputs:
        resource["throughput_tokens_per_sec"] = max(throughputs)  # 稳态代理：取最好 step，避免首步预热压低
    else:
        missing.append("resource_summary.throughput：step 事件缺 num_tokens/duration")
    update_secs = [r.get("duration_seconds") for r in ev["weight_update"] if r.get("duration_seconds") is not None]
    if update_secs:
        resource["weight_update_seconds_max_observed"] = max(update_secs)
    scan_secs = [r["zero_signal_scan_seconds_max"] for r in step_rows if r.get("zero_signal_scan_seconds_max")]
    if scan_secs:
        resource["zero_signal_scan_seconds_max"] = max(scan_secs)
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
        "run_id": args.run_id,
        "event_counts": {k: len(v) for k, v in sorted(ev.items())},
        "step_rows": len(step_rows),
        "sample_rows": len(sample_rows),
        "conflicts": conflicts,
        "missing": missing,
    }
    (out_dir / "collect_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # 原子发布：全部文件就绪后一次 rename；此前任何失败都不会产出 collected/。
    os.replace(out_dir, final_dir)
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
    coll = ev / COLLECTED_DIR_NAME
    th = load_thresholds(Path(args.thresholds))
    j = Judge(th, args.r3)

    steps = read_jsonl(coll / "step_records.jsonl") if (coll / "step_records.jsonl").exists() else None
    if steps is not None and not steps:
        steps = None
    samples = (
        read_jsonl(coll / "sample_records.jsonl") if (coll / "sample_records.jsonl").exists() else None
    )
    if samples is not None and not samples:
        samples = None
    train_samples = [s for s in samples if s.get("source") == "train_batch"] if samples else None
    publish = (
        json.loads((coll / "publish_records.json").read_text())
        if (coll / "publish_records.json").exists()
        else None
    )

    # -- run 身份绑定（P0-1）：verdict 只绑定一次不可变 run --------------------
    _judge_run_identity(j, ev, coll, Path(args.thresholds))

    # -- collect 联结冲突（证据在场但互相矛盾 = FAIL，不是 MISSING）-----------
    report_path = coll / "collect_report.json"
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

    # -- sglang 引擎稳定性（P1-1：改名如实描述证据对象——rollout_workers 记录的
    #    是 SGLang engine actor 身份，证明引擎跨轮未重建；fully-async producer
    #    task 的保温是另一对象，不得混称）------------------------------------
    if th.get("g1_sglang_engines_stable_across_steps"):
        if not steps or any(s.get("worker_ids") is None for s in steps):
            j.add("g1_sglang_engines_stable_across_steps", MISSING, "worker_ids 证据缺失")
        else:
            sets = [frozenset(s["worker_ids"]) for s in steps]
            warm = all(x == sets[0] for x in sets)
            j.add(
                "g1_sglang_engines_stable_across_steps",
                PASS if warm else FAIL,
                "sglang 引擎集合跨 step 不变" if warm else f"引擎集合变化：{[sorted(x) for x in sets]}",
            )

    # -- 版本前进性 / publish 守恒 / staleness --------------------------------
    if steps is None or any(
        s.get("weight_version_after") is None or s.get("weight_version_before") is None for s in steps
    ):
        j.add("weight_version_monotonic", MISSING, "weight_version 证据缺失（train_rollout/weight_update 事件不全）")
    else:
        ok, detail = _check_versions(steps)
        j.add("weight_version_monotonic", PASS if ok else FAIL, detail)

    expected_final_version: int | None = None
    if steps is None or publish is None or (not publish["updates"] and not publish["skips"]):
        j.add("weight_publish_conservation", MISSING, "step/publish 事实缺失，无法做 interval 守恒")
    else:
        ok, problems, expected_final_version = _check_publish_conservation(
            steps, publish, int(th.get("update_weights_interval", 1))
        )
        j.add(
            "weight_publish_conservation",
            PASS if ok else FAIL,
            "applied<=>update<=>publish<=>版本+1 按 interval 双向守恒" if ok else "; ".join(problems[:5]),
        )

    if not train_samples:
        j.add("staleness_max_versions", MISSING, "sample_records.jsonl 缺失或无训练批样本")
    else:
        # 聚焦复核 finding 3（P0-8）：不允许用 min 折叠后的单值判定——逐 turn
        # 版本列表必须逐项存在、可解析且 <= current_version；全部单项合法后，
        # 才用最旧版本计算该样本的最大 staleness。["1","99"]+current=1 之类的
        # future/损坏项不得被折叠隐藏。
        incomplete: list[str] = []
        problems: list[str] = []
        vals: list[int] = []
        for s in train_samples:
            cur = s.get("current_version")
            versions = s.get("behavior_versions")
            if cur is None or not versions:
                incomplete.append(s["sample_id"])
                continue
            unparsable = [repr(v) for v in versions if not str(v).isdigit()]
            if unparsable:
                problems.append(
                    f"{s['sample_id']}: 版本列表含不可解析项 {unparsable[:3]}（完整列表 {versions}）"
                )
                continue
            future = sorted({int(v) for v in versions if int(v) > cur})
            if future:
                problems.append(
                    f"{s['sample_id']}: 版本列表含 future 版本 {future[:3]} > current {cur}"
                    f"（完整列表 {versions}）——min 折叠不得隐藏"
                )
                continue
            vals.append(cur - min(int(v) for v in versions))
        lim = th["staleness_max_versions"]
        if problems:
            j.add("staleness_max_versions", FAIL, "; ".join(problems[:4]))
        elif incomplete and not vals:
            j.add("staleness_max_versions", MISSING, "无版本对样本（train_rollout current version 缺失？）")
        elif incomplete:
            j.add(
                "staleness_max_versions",
                FAIL,
                f"{len(incomplete)} 个训练样本缺完整版本事实（如 {incomplete[:4]}）——缺版本不豁免 staleness 判定",
            )
        else:
            worst, least = max(vals), min(vals)
            ok = worst <= lim
            j.add(
                "staleness_max_versions",
                PASS if ok else FAIL,
                f"staleness 区间=[{least},{worst}]（要求 0 <= s <= {lim}；逐 turn 版本已逐项验证"
                "存在/可解析/<=current）",
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

    # -- logprob 对拍（P0-8：对齐 + 覆盖 + 上限三面）--------------------------
    _judge_logprob(j, train_samples)

    # -- routing tape（R3 显式选择对应的形状义务；只约束进入训练批的样本）-----
    _judge_routing(j, train_samples)

    # -- R3 trainer 侧 replay 消费（P0-5）-------------------------------------
    _judge_replay(j, coll, steps, train_samples)

    # -- 正控组（P0-5/P0-8：方差 + applied 消费 + accepted token 归因）--------
    _judge_positive_control(j, samples, steps)

    # -- integration tree identity（P0-4 worker 侧）---------------------------
    if th.get("integration_tree_identity_required"):
        ident_path = coll / "actor_identity.json"
        if not ident_path.exists():
            j.add("integration_tree_identity", MISSING, "actor_identity.json 缺失（无 identity 事件）")
        else:
            ident = json.loads(ident_path.read_text())
            roles = ident.get("roles", [])
            required = th.get("identity_required_role_prefixes", [])
            missing_roles = [
                prefix for prefix in required if not any(str(r).startswith(prefix) for r in roles)
            ]
            expected = ident.get("expected_tree_digests") or []
            problems = []
            if missing_roles:
                problems.append(f"缺必需 role 类别：{missing_roles}（已见 {roles}）——部分 actor 的树身份无证据")
            if not expected:
                problems.append("无任何 expected_tree_digest（launch 未钉死或事件缺字段）——一致性没有外部锚点")
            if not ident.get("consistent"):
                problems.append(
                    f"tree digest 不一致或与钉死值不符：{ident.get('tree_digests')} vs {expected}"
                )
            j.add(
                "integration_tree_identity",
                PASS if not problems else FAIL,
                (
                    f"必需 role（{', '.join(roles)}）全部到场，tree digest 一致且与钉死值相符"
                    if not problems
                    else "; ".join(problems)
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

    # -- 关停（P0-3B：查询失败≠零；s1_compat finalization 如实 NOT_APPLICABLE）-
    _judge_shutdown(j, ev / "shutdown_probe.json", th)

    # -- 队列守恒（P0-8：multiset 相等 + rank 齐全，替代单纯查重）--------------
    _judge_queue(j, steps, samples, th)

    # -- checkpoint / eval 冒烟 ------------------------------------------------
    _judge_probe(
        j, ev / "checkpoint_probe.json", "g1_checkpoint_save_reload_delete",
        lambda d: d.get("saved") and d.get("reloaded") and d.get("deleted"),
        "checkpoint 存/读/删闭环（DCP FileSystemReader 结构化反序列化）",
    )
    _judge_eval(j, coll / "eval_smoke.json", steps, expected_final_version)

    # -- 资源 ------------------------------------------------------------------
    res_path = coll / "resource_summary.json"
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


def _judge_run_identity(j: Judge, ev: Path, coll: Path, thresholds_path: Path) -> None:
    """P0-1：verdict 绑定唯一 run——manifest、collect、thresholds 三方一致。"""
    manifest_path = ev / "run_manifest.json"
    report_path = coll / "collect_report.json"
    if not manifest_path.exists():
        j.add("run_identity", MISSING, "run_manifest.json 缺失（launch 未在 Ray 前写 run 事实）")
        return
    if not report_path.exists():
        j.add("run_identity", MISSING, "collected/collect_report.json 缺失（collect 未成功发布）")
        return
    manifest = json.loads(manifest_path.read_text())
    report = json.loads(report_path.read_text())
    problems = []
    m_rid, c_rid = manifest.get("run_id"), report.get("run_id")
    if not m_rid:
        problems.append("run_manifest.json 无 run_id")
    elif c_rid != m_rid:
        problems.append(f"collect run_id={c_rid!r} != manifest run_id={m_rid!r}（证据不属于本 run）")
    want_sha = manifest.get("thresholds_sha256")
    got_sha = hashlib.sha256(thresholds_path.read_bytes()).hexdigest()
    if want_sha and want_sha != got_sha:
        problems.append(
            f"thresholds.md sha256 与 run manifest 不符（manifest={want_sha[:12]}… judge 输入={got_sha[:12]}…）"
            "——判定阈值在 run 后被改动"
        )
    j.add(
        "run_identity",
        PASS if not problems else FAIL,
        f"run_id={m_rid} 三方一致（manifest/collect/thresholds digest）" if not problems else "; ".join(problems),
    )


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


def _check_publish_conservation(
    steps: list[dict], publish: dict, interval: int
) -> tuple[bool, list[str], int | None]:
    """P0-6：按 publish interval 做 applied↔update↔publish↔version 双向守恒。

    interval 内存在 applied step <=> 恰好一次 trainer weight_update（版本 +1、
    与上一次发布版本连续）<=> 恰好一次 driver weight_publish、零 skip；
    interval 内全 skipped <=> 恰好一次 weight_publish_skipped、零 update/publish。
    rollout_id=None 的 update 是训练前 bootstrap 发布（train_async 先
    update_weights 让引擎拿到训练侧权重），作为版本链起点，不参与 interval 账。

    聚焦复核 finding 2 收紧：bootstrap 必须**有且唯一**（缺失时版本链可从任意
    值重新起根）；每个边界的 update.version_before 必须等于该 interval 的
    trainer current（train_rollout 独立事实，落在 step 的 weight_version_before
    上），version_after 必须与下一 rollout 的 trainer current 联结——发布账本
    自洽不再单独作数。返回 (ok, problems, 期望终版)。
    """
    problems: list[str] = []
    updates_by_rollout: dict[int, list[dict]] = defaultdict(list)
    bootstraps: list[dict] = []
    for u in publish.get("updates", []):
        if u.get("rollout_id") is None:
            bootstraps.append(u)
        else:
            updates_by_rollout[u["rollout_id"]].append(u)
    if len(bootstraps) != 1:
        problems.append(
            f"bootstrap weight_update（rollout_id=None，train_async 训前首发）必须有且唯一，"
            f"观测 {len(bootstraps)} 条——版本链没有可信起根"
        )
    bootstrap_after: int | None = bootstraps[0].get("version_after") if len(bootstraps) == 1 else None
    if len(bootstraps) == 1 and bootstrap_after is None:
        problems.append("bootstrap weight_update 缺 version_after（版本链起点未知）")
    publishes = Counter(p for p in publish.get("publishes", []) if p is not None)
    skips = Counter(s for s in publish.get("skips", []) if s is not None)

    rids = sorted({s["rollout_id"] for s in steps if s.get("rollout_id") is not None})
    # trainer current 独立事实（train_rollout -> collect 落在 weight_version_before）。
    current_by_rid: dict[int, int] = {}
    for s in steps:
        rid, vb = s.get("rollout_id"), s.get("weight_version_before")
        if rid is not None and vb is not None:
            current_by_rid.setdefault(rid, vb)  # 同 rollout 冲突由 collect_consistency 兜住
    boundaries = [rid for rid in rids if (rid + 1) % interval == 0]
    boundary_set = set(boundaries)
    for rid in sorted(updates_by_rollout):
        if rid not in boundary_set:
            problems.append(f"weight_update 出现在非 interval 边界 rollout {rid}")
    for rid in sorted(set(publishes) - boundary_set):
        problems.append(f"weight_publish 出现在非 interval 边界 rollout {rid}")
    for rid in sorted(set(skips) - boundary_set):
        problems.append(f"weight_publish_skipped 出现在非 interval 边界 rollout {rid}")

    def _anchor(tag: str, rid_list: list[int], want: int, what: str) -> None:
        currents = sorted({current_by_rid[r] for r in rid_list if r in current_by_rid})
        if currents and currents != [want]:
            problems.append(f"{tag}: {what}={want} 与 trainer current {currents} 脱锚（train_rollout 独立事实）")

    prev_after = bootstrap_after
    for b in boundaries:
        interval_rids = [r for r in rids if b - interval < r <= b]
        any_applied = any(
            s.get("optimizer_step_applied") is True for s in steps if s.get("rollout_id") in interval_rids
        )
        ups = updates_by_rollout.get(b, [])
        n_pub, n_skip = publishes.get(b, 0), skips.get(b, 0)
        tag = f"interval@r{b}"
        if any_applied:
            if len(ups) != 1:
                problems.append(f"{tag}: 有 applied step 但 weight_update={len(ups)} 次（需恰好 1）")
            if n_pub != 1:
                problems.append(f"{tag}: 有 applied step 但 weight_publish={n_pub} 次（需恰好 1）")
            if n_skip:
                problems.append(f"{tag}: 有 applied step 却出现 weight_publish_skipped")
            if len(ups) == 1:
                u = ups[0]
                vb, va = u.get("version_before"), u.get("version_after")
                if vb is None or va is None or va != vb + 1:
                    problems.append(f"{tag}: 版本未 +1（{vb}->{va}）")
                if prev_after is not None and vb is not None and vb != prev_after:
                    problems.append(f"{tag}: 版本链断裂（上次发布后 {prev_after}，本次 before={vb}）")
                if vb is not None:
                    _anchor(tag, interval_rids, vb, "update.version_before")
                if va is not None:
                    prev_after = va
        else:
            if ups:
                problems.append(f"{tag}: 全 skipped 却有 weight_update（{len(ups)} 次）")
            if n_pub:
                problems.append(f"{tag}: 全 skipped 却有 weight_publish")
            if n_skip != 1:
                problems.append(f"{tag}: 全 skipped 但 weight_publish_skipped={n_skip} 次（需恰好 1）")
            if prev_after is not None:
                _anchor(tag, interval_rids, prev_after, "上次发布后版本")
        # version_after（或 skip 后保持的版本）必须与下一 interval 的 trainer
        # current 联结——否则发布结果与 trainer 实际取到的版本是两本账。
        if prev_after is not None:
            next_rids = [r for r in rids if b < r <= b + interval]
            _anchor(f"{tag}->next", next_rids, prev_after, "发布后版本")
    return (not problems, problems, prev_after)


def _judge_logprob(j: Judge, train_samples: list[dict] | None) -> None:
    if train_samples is None:
        j.add("logprob_same_version_mean_abs_diff_max", MISSING, "sample_records.jsonl 缺失")
        j.add("logprob_alignment_and_coverage", MISSING, "sample_records.jsonl 缺失")
        return
    th = j.th
    with_entry = [s for s in train_samples if s.get("has_logprob_entry")]
    if not with_entry:
        j.add("logprob_same_version_mean_abs_diff_max", MISSING, "无对拍摘要（logprob_compare 事件缺失）")
        j.add("logprob_alignment_and_coverage", MISSING, "无对拍摘要（logprob_compare 事件缺失）")
        return
    diffs = [
        s["same_version_mean_abs_logprob_diff"]
        for s in train_samples
        if s.get("same_version_mean_abs_logprob_diff") is not None
    ]
    if not diffs:
        j.add("logprob_same_version_mean_abs_diff_max", MISSING, "无同版本对拍摘要（全部样本跨版本？）")
    else:
        worst = max(diffs)
        lim = th["logprob_same_version_mean_abs_diff_max"]
        j.add(
            "logprob_same_version_mean_abs_diff_max",
            PASS if worst <= lim else FAIL,
            f"同版本 loss_mask=1 逐 token 均值绝对差最大={worst:.4g}（上限 {lim}）",
        )
    if th.get("logprob_alignment_required"):
        problems = []
        mismatched = [s["sample_id"] for s in train_samples if s.get("logprob_length_mismatch")]
        if mismatched:
            problems.append(f"{len(mismatched)} 个样本 behavior/current 长度错位（如 {mismatched[:4]}）——token 对齐已破坏")
        same_version = [
            s
            for s in train_samples
            if s.get("current_version") is not None
            and s.get("behavior_version") is not None
            and s["current_version"] == s["behavior_version"]
        ]
        uncovered = [s["sample_id"] for s in same_version if not s.get("has_logprob_entry")]
        if uncovered:
            problems.append(f"{len(uncovered)} 个同版本训练样本无对拍条目（如 {uncovered[:4]}）——覆盖不完整")
        total_masked = sum(s.get("logprob_masked_tokens") or 0 for s in with_entry)
        if total_masked <= 0:
            problems.append("loss_mask=1 对拍 token 总数为 0（训练 token 口径下无任何有效对拍）")
        j.add(
            "logprob_alignment_and_coverage",
            PASS if not problems else FAIL,
            (
                f"无长度错位；同版本样本全覆盖；masked token 总数={total_masked}"
                if not problems
                else "; ".join(problems)
            ),
        )


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


def _judge_replay(j: Judge, coll: Path, steps: list[dict] | None, train_samples: list[dict] | None) -> None:
    """P0-5：R3 的 Go 证据 = trainer 真实消费 tape，而不只是 tape 运到门口。

    routing_replay_trainer_consumption：fill 队列（stream 注册、record 数 =
    期望 microbatch 数）、logprob 前向逐 microbatch pop、每个 optimizer step
    的 forward/backward pop 数与该 step 的 microbatch 数一致、rollout 末队列
    耗尽。routing_replay_source_linkage：trainer 侧 fill 的逐样本 digest
    multiset == rollout 侧 rollout_group tape digest multiset（同一份数据）。

    聚焦复核 finding 1 收紧：生产端每个 trainer global rank 独立发 replay 事件
    （事件写失败被有意吞掉，fail-closed 责任在 judge）——因此从 run topology
    声明（thresholds expected_trainer_global_ranks / expected_dp_ranks）导出
    预期 rank census，按 (manager, rollout, global_rank[, step]) 联结完整链：
    任一预期 rank 缺 fill / logprob 前向 / 任一 step 消费 / exhausted 都 FAIL；
    rank->dp 映射必须自洽、dp 覆盖 0..D-1；同 dp 组的 PP/EP 副本消费同一份
    数据，fill 的 sample_digests 必须一致（不再 setdefault 取首条）。
    """
    ck, lk = "routing_replay_trainer_consumption", "routing_replay_source_linkage"
    rec_path = coll / "replay_records.json"
    rec = json.loads(rec_path.read_text()) if rec_path.exists() else None
    fills = [f for f in (rec or {}).get("fills", []) if f.get("manager") == "routing"]
    consumes = [c for c in (rec or {}).get("consumes", []) if c.get("manager") == "routing"]
    exhausted = [x for x in (rec or {}).get("exhausted", []) if x.get("manager") == "routing"]
    if j.r3 == "off":
        extra = len(fills) + len(consumes) + len(exhausted)
        j.add(
            ck,
            PASS if extra == 0 else FAIL,
            "R3=off：无 trainer 侧 replay 事件" if extra == 0 else f"R3=off 但存在 {extra} 条 replay 事件",
        )
        return
    if steps is None:
        j.add(ck, MISSING, "step_records.jsonl 缺失，无法联结 replay 消费与 optimizer step")
        j.add(lk, MISSING, "step_records.jsonl 缺失")
        return
    if not fills:
        j.add(ck, MISSING, "R3=on 但无 replay_fill 事件——tape 是否被 trainer 消费无证据（source tape 不算数）")
        j.add(lk, MISSING, "无 replay_fill 事件（无 trainer 侧 digest 可联结）")
        return
    n_ranks, n_dp = j.th.get("expected_trainer_global_ranks"), j.th.get("expected_dp_ranks")
    if n_ranks is None or n_dp is None:
        j.add(ck, MISSING, "thresholds 缺 expected_trainer_global_ranks/expected_dp_ranks"
                           "（run topology 未声明，无法建立预期 rank census——缺声明不算绿）")
        j.add(lk, MISSING, "无预期 rank census（同 DP 副本一致性无法判定）")
        return
    expected_ranks = set(range(int(n_ranks)))
    problems: list[str] = []

    # rank census：rank->dp 映射自洽、无预期外 rank、dp 覆盖齐全。
    dp_seen_by_rank: dict[int, set] = defaultdict(set)
    for e in [*fills, *consumes, *exhausted]:
        dp_seen_by_rank[e.get("rank")].add(e.get("dp_rank"))
    if None in dp_seen_by_rank:
        problems.append("存在缺 rank 字段的 replay 事件（emitter 版本过旧？）")
        del dp_seen_by_rank[None]
    for rank in sorted(dp_seen_by_rank):
        if None in dp_seen_by_rank[rank]:
            problems.append(f"rank{rank} 存在缺 dp_rank 的 replay 事件")
        elif len(dp_seen_by_rank[rank]) > 1:
            problems.append(f"rank{rank} 的 dp_rank 归属冲突：{sorted(dp_seen_by_rank[rank])}")
    unexpected = sorted(set(dp_seen_by_rank) - expected_ranks)
    if unexpected:
        problems.append(
            f"replay 事件出现预期 census 之外的 rank：{unexpected}"
            f"（expected_trainer_global_ranks={n_ranks} 与实际拓扑不符——census 声明失真）"
        )
    dp_values = {
        next(iter(v)) for v in dp_seen_by_rank.values() if len(v) == 1 and None not in v
    }
    if dp_values and dp_values != set(range(int(n_dp))):
        problems.append(f"dp 覆盖 {sorted(dp_values)} != 预期 0..{int(n_dp) - 1}")
    for f in fills:
        tag = f"fill r{f.get('rollout_id')} rank{f.get('rank')}"
        if not f.get("enabled"):
            problems.append(f"{tag}: replay manager 未启用（enabled=false）——tape 在场但 replay 实际失效")
        if not f.get("num_streams"):
            problems.append(f"{tag}: 注册 stream 数为 0（wrapper 未注册）")
        exp = f.get("expected_records")
        if not exp or f.get("records_min") != exp or f.get("records_max") != exp:
            problems.append(
                f"{tag}: 队列 record 数 {f.get('records_min')}~{f.get('records_max')} != 期望 {exp}"
            )
    step_keys = {(s["rollout_id"], s["step_id"]) for s in steps}
    rollouts = {rid for rid, _ in step_keys}
    fill_keys = {(f.get("rollout_id"), f.get("rank")) for f in fills}
    train_consume_keys = {
        (c.get("rollout_id"), c.get("step_id"), c.get("rank")) for c in consumes if c.get("phase") == "train_step"
    }
    logprob_keys = {
        (c.get("rollout_id"), c.get("rank")) for c in consumes if c.get("phase") == "logprob_forward"
    }
    exhausted_keys = {(x.get("rollout_id"), x.get("rank")) for x in exhausted}
    for c in consumes:
        tag = f"consume {c.get('phase')} r{c.get('rollout_id')}s{c.get('step_id')} rank{c.get('rank')}"
        if c.get("phase") == "train_step":
            nmb = c.get("num_microbatches")
            for side in ("forward", "backward"):
                lo, hi = c.get(f"{side}_pops_min"), c.get(f"{side}_pops_max")
                if not nmb or lo != nmb or hi != nmb:
                    problems.append(f"{tag}: {side} pop {lo}~{hi} != 本 step microbatch 数 {nmb}")
        elif c.get("phase") == "logprob_forward":
            lo, hi = c.get("forward_pops_min"), c.get("forward_pops_max")
            ql, qh = c.get("queue_len_min"), c.get("queue_len_max")
            if not ql or lo != ql or hi != qh or ql != qh:
                problems.append(f"{tag}: logprob 前向 pop {lo}~{hi} != 队列长度 {ql}~{qh}")
    # 逐 (rollout, 预期 global rank) 联结完整链——只有"某个 rank 有事件"不算数；
    # 少一个 rank、或少某 rank 的一个 step，都意味着该 rank 的 replay 消费无证据。
    for rid in sorted(rollouts):
        for rank in sorted(expected_ranks):
            if (rid, rank) not in fill_keys:
                problems.append(f"r{rid} rank{rank}: 无 replay_fill")
            if (rid, rank) not in logprob_keys:
                problems.append(f"r{rid} rank{rank}: 无 logprob_forward 消费事件")
            if (rid, rank) not in exhausted_keys:
                problems.append(f"r{rid} rank{rank}: 无 replay_exhausted（队列是否耗尽无证据）")
    for (rid, sid) in sorted(step_keys):
        for rank in sorted(expected_ranks):
            if (rid, sid, rank) not in train_consume_keys:
                problems.append(
                    f"r{rid}s{sid} rank{rank}: 无 train_step 消费事件（该 rank 该 optimizer step 的 replay 消费无证据）"
                )
    for x in exhausted:
        tag = f"exhausted r{x.get('rollout_id')} rank{x.get('rank')}"
        ql, qh = x.get("queue_len_min"), x.get("queue_len_max")
        ok = (
            x.get("exhausted") is True
            and ql == qh
            and x.get("forward_pops_min") == x.get("forward_pops_max") == ql
            and x.get("backward_pops_min") == x.get("backward_pops_max") == ql
        )
        if not ok:
            problems.append(
                f"{tag}: 未耗尽（queue {ql}~{qh} fwd {x.get('forward_pops_min')}~{x.get('forward_pops_max')} "
                f"bwd {x.get('backward_pops_min')}~{x.get('backward_pops_max')}）"
            )
    j.add(
        ck,
        PASS if not problems else FAIL,
        (
            f"{len(expected_ranks)} 个预期 trainer rank 逐一：fill/logprob 前向/"
            f"{len(step_keys)} 个 step 消费/耗尽全链一致"
            if not problems
            else "; ".join(problems[:6])
        ),
    )

    # source -> trainer digest 联结
    if not train_samples:
        j.add(lk, MISSING, "sample_records.jsonl 缺失或无训练批样本（rollout 侧 tape 来源无证据）")
        return
    if any(f.get("sample_digests") is None for f in fills):
        j.add(lk, MISSING, "replay_fill 缺 sample_digests（无 trainer 侧 tape 身份）")
        return
    link_problems: list[str] = []
    for rid in sorted(rollouts):
        expected = Counter(
            (s.get("routing_tape") or {}).get("digest")
            for s in train_samples
            if s.get("rollout_id") == rid and s.get("routing_tape")
        )
        # 同 dp 组的 PP/EP 副本消费同一份数据：digest multiset 必须逐副本一致
        # （不再 setdefault 取首条——副本间冲突 = 消费账本被改写或错绑）。
        rep_by_dp: dict[int, Counter] = {}
        rep_rank_by_dp: dict[int, object] = {}
        for f in fills:
            if f.get("rollout_id") != rid or f.get("dp_rank") is None:
                continue
            digests = Counter(f.get("sample_digests") or [])
            dp = f["dp_rank"]
            if dp not in rep_by_dp:
                rep_by_dp[dp] = digests
                rep_rank_by_dp[dp] = f.get("rank")
            elif rep_by_dp[dp] != digests:
                link_problems.append(
                    f"r{rid} dp{dp}: 同 DP 副本 sample_digests 冲突"
                    f"（rank{rep_rank_by_dp[dp]} vs rank{f.get('rank')}）——PP/EP 副本必须消费同一份数据"
                )
        actual = Counter()
        for digests in rep_by_dp.values():
            actual += digests
        if expected != actual:
            miss = expected - actual
            extra = actual - expected
            link_problems.append(
                f"r{rid}: trainer 消费的 tape 集合 != rollout 侧来源（缺 {sum(miss.values())} 个、"
                f"多 {sum(extra.values())} 个）"
            )
    j.add(
        lk,
        PASS if not link_problems else FAIL,
        "trainer fill digest multiset == rollout tape digest multiset（逐轮）"
        if not link_problems
        else "; ".join(link_problems[:4]),
    )


def _judge_queue(j: Judge, steps: list[dict] | None, samples: list[dict] | None, th: dict) -> None:
    """P0-8：admitted==consumed multiset、filtered 不相交、预期 dp rank 齐全。"""
    if steps is None or any(s.get("queue_consumed_sample_ids") is None for s in steps):
        j.add("queue_multiset_conservation", MISSING, "queue_consumed_sample_ids 证据缺失")
        j.add("train_step_rank_coverage", MISSING, "train_step_consumed 证据缺失")
        return
    consumed = Counter(x for s in steps for x in s["queue_consumed_sample_ids"])
    train_rows = [s for s in samples if s.get("source") == "train_batch"] if samples else []
    if not train_rows:
        j.add("queue_multiset_conservation", MISSING, "无训练批样本事件（admitted 面无证据）")
    else:
        admitted = Counter(s["sample_id"] for s in train_rows)
        filtered = {s["sample_id"] for s in samples if s.get("source") == "filtered"}
        problems = []
        missing_ids = admitted - consumed
        extra_ids = consumed - admitted
        if missing_ids:
            problems.append(f"admitted 但未消费：{sorted(missing_ids)[:5]}（共 {sum(missing_ids.values())}）")
        if extra_ids:
            problems.append(f"消费了未 admitted 的样本：{sorted(extra_ids)[:5]}（共 {sum(extra_ids.values())}）")
        dups = {k: v for k, v in consumed.items() if v > 1}
        if dups:
            problems.append(f"重复消费：{dict(list(dups.items())[:4])}")
        overlap = filtered & (set(admitted) | set(consumed))
        if overlap:
            problems.append(f"filtered 样本出现在训练/消费面：{sorted(overlap)[:5]}")
        j.add(
            "queue_multiset_conservation",
            PASS if not problems else FAIL,
            (
                f"admitted == consumed（{sum(admitted.values())} 样本 exactly-once），filtered 不相交"
                if not problems
                else "; ".join(problems)
            ),
        )
    expected_ranks = th.get("expected_dp_ranks")
    if expected_ranks is None:
        j.add("train_step_rank_coverage", MISSING, "thresholds 缺 expected_dp_ranks（预期分片数未声明）")
        return
    want = list(range(int(expected_ranks)))
    bad = [
        f"r{s['rollout_id']}s{s['step_id']}: dp_ranks={s.get('dp_ranks')}"
        for s in steps
        if s.get("dp_ranks") != want
    ]
    j.add(
        "train_step_rank_coverage",
        PASS if not bad else FAIL,
        f"每个 step 的 dp 分片齐全（0..{expected_ranks - 1}）" if not bad else "; ".join(bad[:4]),
    )


def _judge_positive_control(j: Judge, samples: list[dict] | None, steps: list[dict] | None) -> None:
    th = j.th
    if samples is None:
        j.add("positive_control_min_groups_with_reward_std", MISSING, "sample_records.jsonl 缺失")
        j.add("positive_control_consumed_by_applied_step", MISSING, "sample_records.jsonl 缺失")
        j.add("positive_control_accepted_tokens", MISSING, "sample_records.jsonl 缺失")
        j.add("zero_variance_groups_must_not_train", MISSING, "sample_records.jsonl 缺失")
        return
    if not any(s.get("source") == "train_batch" for s in samples):
        j.add("positive_control_min_groups_with_reward_std", MISSING, "无训练批样本（rollout_group 事件缺失）")
        j.add("positive_control_consumed_by_applied_step", MISSING, "无训练批样本（rollout_group 事件缺失）")
        j.add("positive_control_accepted_tokens", MISSING, "无训练批样本（rollout_group 事件缺失）")
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
    qualifying: list[tuple] = []
    consumed_evidence_ok = bool(steps) and not any(
        s.get("queue_consumed_sample_ids") is None or s.get("optimizer_step_applied") is None for s in steps
    )
    if th.get("positive_control_must_be_consumed_by_applied_step"):
        if not consumed_evidence_ok:
            j.add("positive_control_consumed_by_applied_step", MISSING, "step 消费/applied 证据缺失")
        else:
            consumed_all = {x for s in steps for x in s["queue_consumed_sample_ids"]}
            applied_consumed = {
                x for s in steps if s["optimizer_step_applied"] is True for x in s["queue_consumed_sample_ids"]
            }
            for key in pc_groups_with_std:
                rows = groups[key]
                ids = {r["sample_id"] for r in rows}
                if ids <= consumed_all and ids & applied_consumed:
                    qualifying.append(key)
            j.add(
                "positive_control_consumed_by_applied_step",
                PASS if qualifying else FAIL,
                (
                    f"正控组 {[k[1] for k in qualifying]} 全部样本被消费且 ≥1 样本进入 optimizer_step_applied=True 的 step"
                    if qualifying
                    else "没有任何 reward std>0 的正控组被真实 applied step 消费（方差 ≠ 驱动更新）"
                ),
            )

    # P0-8：共批 ≠ 归因——正控组自身必须存在 accepted（可产生梯度的）token，
    # 否则该 applied step 可能完全由别的组驱动。
    if th.get("positive_control_requires_accepted_tokens"):
        if not consumed_evidence_ok:
            j.add("positive_control_accepted_tokens", MISSING, "step 消费/applied 证据缺失，无法归因")
        elif not qualifying:
            j.add(
                "positive_control_accepted_tokens",
                FAIL if pc_groups_with_std else MISSING,
                "无 qualifying 正控组（前置检查未过），accepted token 归因无从谈起",
            )
        else:
            facts_missing = [
                r["sample_id"]
                for key in qualifying
                for r in groups[key]
                if r.get("dis_accepted_tokens") is None
            ]
            if facts_missing:
                j.add(
                    "positive_control_accepted_tokens",
                    MISSING,
                    f"正控组样本缺 sample_dis_accounting 事实（如 {facts_missing[:4]}）",
                )
            else:
                good = [
                    key
                    for key in qualifying
                    if sum(r.get("dis_accepted_tokens") or 0 for r in groups[key]) > 0
                ]
                j.add(
                    "positive_control_accepted_tokens",
                    PASS if good else FAIL,
                    (
                        f"正控组 {[k[1] for k in good]} 自身 accepted token > 0（真实贡献训练信号）"
                        if good
                        else "正控组 accepted token 全为 0——applied step 由其他组驱动，正控无有效归因"
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


def _judge_shutdown(j: Judge, path: Path, th: dict) -> None:
    """P0-3B：查询失败显式 FAIL；s1_compat finalization 如实 NOT_APPLICABLE。"""
    if not path.exists():
        j.add("shutdown_orphan_workers_max", MISSING, "shutdown_probe.json 缺失")
        j.add("shutdown_finalization", MISSING, "shutdown_probe.json 缺失")
        return
    try:
        d = json.loads(path.read_text())
    except ValueError as exc:
        j.add("shutdown_orphan_workers_max", FAIL, f"shutdown_probe.json 不是合法 JSON：{exc}")
        j.add("shutdown_finalization", FAIL, f"shutdown_probe.json 不是合法 JSON：{exc}")
        return
    problems = []
    if not d.get("docker_query_ok"):
        problems.append(f"docker 查询失败（detail={d.get('detail', {})}）——无法观测 ≠ 观测为零")
    if not d.get("ray_query_ok"):
        problems.append(f"ray 查询失败（detail={d.get('detail', {})}）——无法观测 ≠ 观测为零")
    orphans = d.get("orphan_workers")
    lim = th["shutdown_orphan_workers_max"]
    if not problems and (orphans is None or orphans > lim):
        problems.append(f"orphan_workers={orphans}（上限 {lim}）")
    j.add(
        "shutdown_orphan_workers_max",
        PASS if not problems else FAIL,
        f"docker/ray 查询成功且孤儿 worker={orphans} ≤ {lim}" if not problems else "; ".join(problems),
    )
    fin = d.get("finalization") or {}
    status = fin.get("status")
    if status == "ok_empty":
        j.add("shutdown_finalization", PASS, "finalization store 在场且无未终结交付")
    elif status == "not_applicable":
        j.add(
            "shutdown_finalization",
            NA,
            "s1_compat 无 FileFinalizationStore（bringup 设计如此）——此项不构成 F5 内存 pending draft "
            "已收口的证据，不冒充零",
        )
    elif status is None:
        j.add("shutdown_finalization", MISSING, "探针未记录 finalization 状态")
    else:
        j.add("shutdown_finalization", FAIL, f"finalization 状态={status}：{fin}")


def _judge_eval(j: Judge, path: Path, steps: list[dict] | None, expected_final_version: int | None) -> None:
    """P0-3A：只有绑定到最后一轮、期望终版权重的 eval 才算训后冒烟。"""
    key = "g1_eval_smoke_post_train"
    if not path.exists():
        j.add(key, MISSING, "eval_smoke.json 缺失（无 eval 事件）")
        return
    data = json.loads(path.read_text())
    events = data.get("events", [])
    if not events:
        j.add(key, MISSING, "eval_smoke.json 无事件")
        return
    if steps is None:
        j.add(key, MISSING, "step_records 缺失，无法确定最后一轮")
        return
    last_rid = max(s["rollout_id"] for s in steps if s.get("rollout_id") is not None)
    if expected_final_version is None:
        j.add(key, MISSING, "publish 守恒未闭合（期望终版未知），无法绑定训后 eval")
        return
    candidates = [e for e in events if e.get("rollout_id") == last_rid]
    if any(e.get("weight_version") is None for e in candidates):
        j.add(key, MISSING, "末轮 eval 事件缺 weight_version 绑定（emitter 版本过旧？）")
        return
    ok = [e for e in candidates if e.get("ok") and e.get("weight_version") == expected_final_version]
    j.add(
        key,
        PASS if ok else FAIL,
        (
            f"末轮（r{last_rid}）eval 在期望终版 v{expected_final_version} 上冒烟通过"
            if ok
            else (
                f"无绑定到末轮+终版的 eval（末轮 r{last_rid}、期望版本 {expected_final_version}；"
                f"观测到 {[(e.get('rollout_id'), e.get('weight_version')) for e in events][:6]}）"
                "——pre-train eval 不能冒充训后 eval"
            )
        ),
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
_RUN_ID = "selftest-run"

# 每 rollout 2 个 optimizer step、dp 2 分片、每轮 2 组 × 8 样本。
_N_ROLLOUTS, _STEPS_PER_ROLLOUT, _GROUP_SIZE = 3, 2, 8
_MB_PER_STEP = 2  # 每 dp rank 每 step 的 microbatch 数（replay 消费联结用）
# trainer 拓扑：与 thresholds 的 expected_trainer_global_ranks / expected_dp_ranks
# 一致（6 actor GPU、TP1*PP3*CP1 -> dp=2）。dp = rank % 2 是代表性映射：oracle 只
# 要求 rank->dp 映射自洽，不假设具体 megatron rank 排序。
_TRAIN_GLOBAL_RANKS, _DP_RANKS = 6, 2
_WORKERS = ["train/aa01", "train/aa02"]
_ROLES = ("driver", "megatron_train_actor", "rollout_manager", "sglang_server")


def _selftest_write_events(ev_dir: Path, *, mutate: str = "") -> None:
    """生成与 miles rh2_event_log 生产 schema 同形的代表性事件文件。"""
    events: list[dict] = []

    def emit(kind: str, **fields):
        events.append({"event": kind, "ts_unix": 0.0, "host": "h", "pid": 1, "run_id": _RUN_ID, **fields})

    for role in _ROLES:
        digest = _TREE_DIGEST
        if mutate == "identity_mismatch" and role == "sglang_server":
            digest = "ee" * 32
        expected = _TREE_DIGEST if mutate != "identity_no_expected" else None
        emit("actor_identity", role=role, miles_file=f"/opt/miles/{role}.py",
             tree_digest=digest, expected_tree_digest=expected)
    if mutate.startswith("drop_role_"):
        gone = mutate.removeprefix("drop_role_")
        events = [e for e in events if not (e["event"] == "actor_identity" and e["role"] == gone)]

    # 训前 bootstrap 发布（train_async 先 update_weights 让引擎拿到训练侧权重）；
    # P0-6：judge 要求它有且唯一——缺失/重复都是版本链起根异常。
    if mutate != "drop_bootstrap":
        emit("weight_update", rollout_id=None, version_before=0, version_after=1, duration_seconds=40.0)
    if mutate == "duplicate_bootstrap":
        emit("weight_update", rollout_id=None, version_before=0, version_after=1, duration_seconds=40.0)

    adam = 0
    sched = 0
    version = 1
    sample_seq = 0
    for rid in range(_N_ROLLOUTS):
        current = version
        if mutate == "next_rollout_current_mismatch" and rid == 1:
            # 发布链自身自洽（0->1->2->3），但 r1 的 trainer current 事实与上一
            # 边界的 version_after 断链——P0-6 反例：版本链必须与 trainer 独立
            # 事实逐 interval 锚定，不允许"账本自洽即通过"。
            current = version + 1
        emit("train_rollout", rollout_id=rid, trainer_current_version=current)
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
            if mutate == "future_behavior_version" and rid == 0 and g == 0:
                behavior = [[str(version + 3)] for _ in indices]  # 来自未来的版本 -> 负 staleness
            if mutate == "mixed_future_behavior" and rid == 0 and g == 0:
                # P0-8 反例：min 折叠会把 ["1","99"] 折成 1、staleness=0——future
                # turn 被隐藏。judge 必须逐项验证完整列表。
                behavior = [[str(version), "99"] for _ in indices]
            if mutate == "nonnumeric_behavior_version" and rid == 0 and g == 0:
                # 数值+非数值混合：min 折叠会静默丢弃不可解析项。
                behavior = [[str(version), "corrupt"] for _ in indices]
            if mutate == "missing_behavior_version" and rid == 0 and g == 0:
                behavior = [[] for _ in indices]
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

        lp_entries = []
        for i in rollout_sample_ids:
            mismatch = mutate == "logprob_length_mismatch_all"
            lp_entries.append({"sample_index": i, "same_version": True,
                               "mean_abs_diff": 0.01 if not mismatch else 0.01,
                               "num_tokens": 320, "total_tokens": 400,
                               "length_mismatch": mismatch})
        if mutate == "logprob_partial_coverage":
            lp_entries = lp_entries[:1]
        emit("logprob_compare", rollout_id=rid, dp_rank=0, trainer_current_version=version,
             entries=lp_entries)

        # 逐样本 DIS token 记账（正控归因）：正控组样本 accepted>0；
        # pc_zero_accepted 时正控组归零、其余组保持正数（"其他组驱动更新"）。
        dis_entries = []
        for i in rollout_sample_ids:
            accepted = 120
            if mutate == "pc_zero_accepted" and rid == 0 and i < _GROUP_SIZE:
                accepted = 0
            dis_entries.append({"sample_index": i, "accepted_tokens": accepted, "provenance_tokens": 320})
        emit("sample_dis_accounting", entries=dis_entries)

        # 2 个 optimizer step；dp0/dp1 各消费一半。
        per_step = len(rollout_sample_ids) // _STEPS_PER_ROLLOUT
        step_shards: dict[tuple[int, int], list[int]] = {}
        for sid in range(_STEPS_PER_ROLLOUT):
            outcome, applied = "NORMAL", True
            if mutate in ("one_skipped_rollout", "all_skipped_but_update") and rid == 2:
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
                shard = list(shard)
                if mutate == "consumed_missing_sample" and rid == 0 and sid == 0 and dp_rank == 0 and shard:
                    shard = shard[1:]
                if mutate == "consumed_extra_sample" and rid == 0 and sid == 0 and dp_rank == 0:
                    shard = [*shard, 9999]
                if mutate == "consumed_missing_rank" and rid == 0 and sid == 0 and dp_rank == 1:
                    continue
                step_shards[(sid, dp_rank)] = shard
                emit("train_step_consumed", rollout_id=rid, step_id=sid, dp_rank=dp_rank,
                     rank=dp_rank, sample_indices=shard, num_tokens=500 * max(len(shard), 1),
                     num_microbatches=_MB_PER_STEP, attribution="micro_batch_indices")
                if mutate == "consumed_rank_conflict" and rid == 0 and sid == 0 and dp_rank == 0:
                    emit("train_step_consumed", rollout_id=rid, step_id=sid, dp_rank=dp_rank,
                         rank=dp_rank + 2, sample_indices=list(reversed(shard))[:1],
                         num_tokens=1, num_microbatches=_MB_PER_STEP, attribution="micro_batch_indices")
            pp_last_first_rank = _TRAIN_GLOBAL_RANKS - _DP_RANKS  # 末级 PP stage 的第一个 rank
            for rank in range(_TRAIN_GLOBAL_RANKS):
                accepted = 900.0 if outcome == "NORMAL" else 0.0
                rejected = 100.0 if outcome == "NORMAL" else 1000.0
                emit("train_step", rollout_id=rid, step_id=sid, attempt=0,
                     outcome=outcome, optimizer_step_applied=applied,
                     adam_step_before=adam_b, adam_step_after=adam,
                     scheduler_steps_before=sched_b, scheduler_steps_after=sched,
                     grad_norm=0.5 if applied else 0.0, duration_seconds=20.0,
                     zero_signal_scan_seconds=0.4,
                     rank=rank, dp_rank=rank % _DP_RANKS,
                     is_pp_last_stage=(rank >= pp_last_first_rank),
                     metrics=(
                         {"dis_accepted_tokens": accepted, "dis_rejected_tokens": rejected,
                          "dis_microbatch_provenance_tokens": accepted + rejected}
                         if rank == pp_last_first_rank else None
                     ))

        # R3 trainer 侧消费事实（fill -> logprob 前向 -> 每 step -> 耗尽）。
        # 生产端每个 trainer global rank 独立发这三类事件（actor.py/model.py 的
        # emit 均带 dist.get_rank() + effective_dp.rank）；同 dp 组的 PP 副本
        # 消费同一份数据，digest 相同。
        queue_len = _MB_PER_STEP * _STEPS_PER_ROLLOUT
        for rank in range(_TRAIN_GLOBAL_RANKS):
            if mutate == "replay_missing_rank" and rank == _TRAIN_GLOBAL_RANKS - 1:
                continue  # 该 rank 的全部 replay 事件丢失（P0-5 census 反例）
            dp_rank = rank % _DP_RANKS
            dp_samples = sorted(
                x for (sid, dp), shard in step_shards.items() if dp == dp_rank for x in shard
            )
            fill_records = queue_len if mutate != "replay_count_mismatch" else queue_len - 1
            digests = ["ab" * 32] * len(dp_samples)
            if mutate == "replay_digest_mismatch" and rid == 0 and dp_rank == 0 and digests:
                digests[0] = "ff" * 32  # dp0 全部副本一致地偏离来源 tape（source 联结反例）
            if mutate == "replay_dp_digest_conflict" and rid == 0 and rank == 4 and digests:
                digests[0] = "ee" * 32  # 仅 rank4 与同 dp 副本（rank0/2）冲突
            emit("replay_fill", manager="routing", rollout_id=rid, rank=rank, dp_rank=dp_rank,
                 enabled=mutate != "replay_fill_disabled",
                 num_streams=16 if mutate != "replay_fill_disabled" else 0,
                 records_min=fill_records, records_max=fill_records,
                 expected_records=queue_len, num_samples=len(dp_samples),
                 sample_digests=digests)
            fwd = queue_len if mutate != "replay_zero_pops" else 0
            emit("replay_consume", phase="logprob_forward", manager="routing", rollout_id=rid,
                 rank=rank, dp_rank=dp_rank, num_streams=16,
                 forward_pops_min=fwd, forward_pops_max=fwd,
                 queue_len_min=queue_len, queue_len_max=queue_len)
            for sid in range(_STEPS_PER_ROLLOUT):
                if (mutate == "replay_missing_rank_step"
                        and rank == _TRAIN_GLOBAL_RANKS - 1 and rid == 0 and sid == 1):
                    continue  # 只丢某 rank 的一个 step 消费事件（census 细粒度反例）
                pops = _MB_PER_STEP if mutate != "replay_zero_pops" else 0
                emit("replay_consume", phase="train_step", manager="routing", rollout_id=rid,
                     step_id=sid, rank=rank, dp_rank=dp_rank, num_streams=16,
                     num_microbatches=_MB_PER_STEP,
                     forward_pops_min=pops, forward_pops_max=pops,
                     backward_pops_min=pops, backward_pops_max=pops,
                     queue_len_min=queue_len, queue_len_max=queue_len)
            drained = queue_len if mutate not in ("replay_zero_pops", "replay_not_exhausted") else 0
            emit("replay_exhausted", manager="routing", rollout_id=rid, rank=rank, dp_rank=dp_rank,
                 num_streams=16, exhausted=mutate not in ("replay_zero_pops", "replay_not_exhausted"),
                 queue_len_min=queue_len, queue_len_max=queue_len,
                 forward_pops_min=drained, forward_pops_max=drained,
                 backward_pops_min=drained, backward_pops_max=drained)

        # 发布语义与 patch 0003 对齐：本轮有 applied step 才发布并进版本。
        any_applied_this_rollout = not (
            (mutate in ("one_skipped_rollout", "all_skipped_but_update") and rid == 2)
            or mutate == "normal_not_applied"
        )
        if mutate == "applied_but_publish_skipped":
            emit("weight_publish_skipped", rollout_id=rid)  # applied 在场却只发"有意跳过"
        elif any_applied_this_rollout:
            before = version
            version += 1
            if mutate == "version_regress" and rid == 1:
                version = before - 1
            after = version
            if mutate == "version_stuck":
                after = before  # Adam 前进但版本账本不动
                version = before
            if mutate == "wrong_first_update_before" and rid == 0:
                # 事件账本声称 99->100，而 trainer current（train_rollout 事实）
                # 是 1、bootstrap 后也是 1——版本链从任意值重新起根（P0-6 反例）。
                before, after = 99, 100
            emit("weight_update", rollout_id=rid, version_before=before, version_after=after,
                 duration_seconds=40.0)
            if mutate != "update_without_publish":
                emit("weight_publish", rollout_id=rid)
            if mutate == "skip_and_update_same_rollout":
                emit("weight_publish_skipped", rollout_id=rid)
        elif mutate == "all_skipped_but_update" and rid == 2:
            # 全 skipped 轮却出现 weight_update（版本被无 applied 事实推进）。
            emit("weight_update", rollout_id=rid, version_before=version,
                 version_after=version + 1, duration_seconds=40.0)
        else:
            emit("weight_publish_skipped", rollout_id=rid)

    eval_rid, eval_version = _N_ROLLOUTS - 1, version
    if mutate == "eval_pre_train_only":
        eval_rid, eval_version = 0, 1
    if mutate == "eval_wrong_version":
        eval_version = 1
    emit("eval_smoke", rollout_id=eval_rid, ok=True, num_metrics=3, weight_version=eval_version)

    if mutate == "publish_without_update":
        events = [e for e in events if not (e["event"] == "weight_update" and e.get("rollout_id") is not None)]
    if mutate == "run_id_mismatch":
        for e in events:
            if e["event"] == "train_rollout":
                e["run_id"] = "other-run"

    drop_kind = {
        "drop_train_step": "train_step",
        "drop_train_step_consumed": "train_step_consumed",
        "drop_train_rollout": "train_rollout",
        "drop_rollout_group": "rollout_group",
        "drop_rollout_workers": "rollout_workers",
        "drop_logprob_compare": "logprob_compare",
        "drop_eval_smoke": "eval_smoke",
        "drop_actor_identity": "actor_identity",
        "drop_sample_dis": "sample_dis_accounting",
    }.get(mutate)
    if drop_kind:
        events = [e for e in events if e["event"] != drop_kind]
    if mutate == "drop_publish_facts":
        events = [e for e in events if e["event"] not in ("weight_update", "weight_publish", "weight_publish_skipped")]
    if mutate == "drop_replay_events":
        events = [e for e in events if not e["event"].startswith("replay_")]

    ev_dir.mkdir(parents=True)
    write_jsonl(ev_dir / "rh2_events_h_1.jsonl", events)


def _selftest_evidence(tmp: Path, *, mutate: str = "") -> Path:
    global _SELFTEST_SEQ  # noqa: PLW0603 - self-test 专用序号
    _SELFTEST_SEQ += 1
    base = tmp / f"case_{_SELFTEST_SEQ}_{mutate or 'good'}"
    events_dir = base / "events"
    ev_dir = base / "evidence"
    ev_dir.mkdir(parents=True)
    _selftest_write_events(events_dir, mutate=mutate)
    ns = argparse.Namespace(
        events_dir=str(events_dir), dmon_csv=None, gpu_mem_total_mb=None,
        out_dir=str(ev_dir / COLLECTED_DIR_NAME), run_id=_RUN_ID,
    )
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_collect(ns)
    coll = ev_dir / COLLECTED_DIR_NAME
    # dmon 在 self-test 无输入：直接补一个合规资源摘要（launch 实跑时由 collect 产出）。
    res = json.loads((coll / "resource_summary.json").read_text())
    if res.get("gpu_mem_peak_frac") is None:
        res["gpu_mem_peak_frac"] = 0.9
    (coll / "resource_summary.json").write_text(json.dumps(res))
    # launch.sh 在 Ray 前写 run_manifest；post-run 探针按 postrun_probes.py 契约。
    (ev_dir / "run_manifest.json").write_text(json.dumps({
        "run_id": _RUN_ID if mutate != "manifest_run_id_mismatch" else "another-run",
        "thresholds_sha256": hashlib.sha256((HERE / "thresholds.md").read_bytes()).hexdigest(),
    }))
    if mutate != "missing_shutdown":
        shutdown = {
            "execution_mode": "s1_compat",
            "docker_query_ok": True,
            "ray_query_ok": True,
            "docker_orphan_containers": [],
            "ray_alive_actors": [],
            "orphan_workers": 0,
            "finalization": {"status": "not_applicable"},
            "detail": {},
        }
        if mutate == "shutdown_query_failed":
            shutdown.update({"docker_query_ok": False, "orphan_workers": None})
        (ev_dir / "shutdown_probe.json").write_text(json.dumps(shutdown))
    (ev_dir / "checkpoint_probe.json").write_text('{"saved": true, "reloaded": true, "deleted": true}')
    return ev_dir


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
              + "; ".join(f"{c['check']}={c['status']}:{c['detail']}" for c in v["checks"] if c["status"] not in (PASS, NA)))

        # --- 删任一必要事件 -> INCOMPLETE（B1 修复验收）---------------------
        for mutate in (
            "drop_train_step", "drop_train_step_consumed", "drop_train_rollout",
            "drop_rollout_group", "drop_rollout_workers", "drop_logprob_compare",
            "drop_eval_smoke", "drop_actor_identity", "drop_publish_facts",
            "drop_sample_dis", "drop_replay_events",
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
        rows = [
            r for r in read_jsonl(ev_dir / COLLECTED_DIR_NAME / "sample_records.jsonl")
            if r.get("behavior_versions") == ["1", "3"]
        ]
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
        check({"routing_tape", "routing_replay_trainer_consumption"} <= failed_checks(v),
              f"R3=off 但携带 tape/replay 事件应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="worker_churn"))
        check("g1_sglang_engines_stable_across_steps" in failed_checks(v),
              f"引擎集合变化应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="identity_mismatch"))
        check("integration_tree_identity" in failed_checks(v),
              f"actor tree digest 不一致应 FAIL，got {failed_checks(v)}")

        # --- P0-4：role 类别不齐 / expected digest 缺失 ----------------------
        for role in _ROLES:
            v = _run_judge(_selftest_evidence(tmp, mutate=f"drop_role_{role}"))
            check("integration_tree_identity" in failed_checks(v),
                  f"缺 {role} identity 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="identity_no_expected"))
        check("integration_tree_identity" in failed_checks(v),
              f"无 expected digest 应 FAIL（自我背书口子），got {failed_checks(v)}")

        # --- P0-1：run 身份污染 ---------------------------------------------
        v = _run_judge(_selftest_evidence(tmp, mutate="run_id_mismatch"))
        check("collect_consistency" in failed_checks(v),
              f"异 run 事件混入应 FAIL collect_consistency，got {failed_checks(v)}")
        check(v["overall"] != "PASS", "异 run 事件混入不得 PASS")
        v = _run_judge(_selftest_evidence(tmp, mutate="manifest_run_id_mismatch"))
        check("run_identity" in failed_checks(v),
              f"manifest run_id 不符应 FAIL run_identity，got {failed_checks(v)}")

        # --- P0-3A：pre-train eval 冒充 / 版本不符 ---------------------------
        v = _run_judge(_selftest_evidence(tmp, mutate="eval_pre_train_only"))
        check("g1_eval_smoke_post_train" in failed_checks(v),
              f"只有 pre-train eval 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="eval_wrong_version"))
        check("g1_eval_smoke_post_train" in failed_checks(v),
              f"eval 版本非终版应 FAIL，got {failed_checks(v)}")

        # --- P0-3B：查询失败 ≠ 零 -------------------------------------------
        v = _run_judge(_selftest_evidence(tmp, mutate="shutdown_query_failed"))
        check("shutdown_orphan_workers_max" in failed_checks(v),
              f"docker 查询失败应 FAIL，got {failed_checks(v)}")

        # --- P0-6：publish 守恒双向反例 --------------------------------------
        v = _run_judge(_selftest_evidence(tmp, mutate="applied_but_publish_skipped"))
        check("weight_publish_conservation" in failed_checks(v),
              f"applied 但只发 skipped 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="version_stuck"))
        check("weight_publish_conservation" in failed_checks(v),
              f"applied 但版本不 +1 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="update_without_publish"))
        check("weight_publish_conservation" in failed_checks(v),
              f"update 无 publish 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="publish_without_update"))
        check("weight_publish_conservation" in failed_checks(v),
              f"publish 无 update 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="skip_and_update_same_rollout"))
        check("weight_publish_conservation" in failed_checks(v),
              f"update 与 skipped 同现应 FAIL，got {failed_checks(v)}")

        # --- P0-6（聚焦复核 finding 2）：bootstrap 有且唯一 + trainer current 锚定
        v = _run_judge(_selftest_evidence(tmp, mutate="drop_bootstrap"))
        check("weight_publish_conservation" in failed_checks(v),
              f"缺 bootstrap update 应 FAIL（版本链无可信起根），got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="duplicate_bootstrap"))
        check("weight_publish_conservation" in failed_checks(v),
              f"bootstrap update 重复应 FAIL（起根不唯一），got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="wrong_first_update_before"))
        check("weight_publish_conservation" in failed_checks(v),
              f"首个 update.version_before 与 trainer current 脱锚应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="next_rollout_current_mismatch"))
        check("weight_publish_conservation" in failed_checks(v),
              f"version_after 与下一 rollout trainer current 断链应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="all_skipped_but_update"))
        check("weight_publish_conservation" in failed_checks(v),
              f"全 skipped 轮出现 weight_update 应 FAIL，got {failed_checks(v)}")

        # --- P0-8：multiset / rank / staleness / logprob / 正控归因 ----------
        v = _run_judge(_selftest_evidence(tmp, mutate="consumed_missing_sample"))
        check("queue_multiset_conservation" in failed_checks(v),
              f"少消费一个样本应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="consumed_extra_sample"))
        check("queue_multiset_conservation" in failed_checks(v),
              f"多消费未知样本应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="consumed_missing_rank"))
        check("train_step_rank_coverage" in failed_checks(v),
              f"缺一个 dp rank 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="consumed_rank_conflict"))
        check("collect_consistency" in failed_checks(v),
              f"同 (r,s,dp) 冲突内容应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="future_behavior_version"))
        check("staleness_max_versions" in failed_checks(v),
              f"behavior version 来自未来（负 staleness）应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="missing_behavior_version"))
        check("staleness_max_versions" in failed_checks(v),
              f"训练样本缺版本（空列表）应 FAIL，got {failed_checks(v)}")
        # --- P0-8（聚焦复核 finding 3）：min 折叠不得隐藏逐 turn 版本异常 ------
        v = _run_judge(_selftest_evidence(tmp, mutate="mixed_future_behavior"))
        check("staleness_max_versions" in failed_checks(v),
              f"混合 future 版本（[1,99]、current=1）应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="nonnumeric_behavior_version"))
        check("staleness_max_versions" in failed_checks(v),
              f"数值+非数值混合版本列表应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="logprob_length_mismatch_all"))
        check("logprob_alignment_and_coverage" in failed_checks(v),
              f"全部长度错位应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="logprob_partial_coverage"))
        check("logprob_alignment_and_coverage" in failed_checks(v),
              f"对拍只剩一条应 FAIL 覆盖，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="pc_zero_accepted"))
        check("positive_control_accepted_tokens" in failed_checks(v),
              f"正控零 accepted token（其他组驱动更新）应 FAIL，got {failed_checks(v)}")

        # --- P0-5：R3 trainer 消费反例 ---------------------------------------
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_fill_disabled"))
        check("routing_replay_trainer_consumption" in failed_checks(v),
              f"replay disabled 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_zero_pops"))
        check("routing_replay_trainer_consumption" in failed_checks(v),
              f"零 pop 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_count_mismatch"))
        check("routing_replay_trainer_consumption" in failed_checks(v),
              f"record 数不符应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_not_exhausted"))
        check("routing_replay_trainer_consumption" in failed_checks(v),
              f"队列未耗尽应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_digest_mismatch"))
        check("routing_replay_source_linkage" in failed_checks(v),
              f"fill digest 与来源 tape 不符应 FAIL，got {failed_checks(v)}")
        # --- P0-5（聚焦复核 finding 1）：rank census + 同 DP 副本一致性 --------
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_missing_rank"))
        check("routing_replay_trainer_consumption" in failed_checks(v),
              f"缺一个 trainer rank 的全部 replay 事件应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_missing_rank_step"))
        check("routing_replay_trainer_consumption" in failed_checks(v),
              f"缺某 rank 的一个 step 消费事件应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="replay_dp_digest_conflict"))
        check("routing_replay_source_linkage" in failed_checks(v),
              f"同 DP 副本 digest 冲突应 FAIL，got {failed_checks(v)}")

        v = _run_judge(_selftest_evidence(tmp, mutate="one_skipped_rollout"))
        check(v["overall"] == "PASS",
              f"全 SKIPPED 轮 + 显式不发布应 PASS（版本保持），得 {v['overall']}: "
              + "; ".join(f"{c['check']}={c['status']}:{c['detail']}" for c in v["checks"] if c["status"] not in (PASS, NA)))

        v = _run_judge(_selftest_evidence(tmp, mutate="missing_shutdown"))
        check(v["overall"] == "INCOMPLETE", f"缺 shutdown 证据应 INCOMPLETE，得 {v['overall']}")

    if failures:
        print("SELF-TEST FAIL:")
        for f in failures:
            print("  -", f)
        return 1
    print(
        "SELF-TEST PASS（代表性事件 collect->judge 全链好例 PASS；11 类事件删除均 INCOMPLETE；"
        "租前审查 P0-1/3/4/5/6/8 全部假绿反例命中对应 FAIL；B2 oracle 坏例保持命中；"
        "聚焦复核 3 个残余 P0 反例——replay rank census/同 DP 副本冲突、bootstrap 唯一+trainer "
        "current 锚定、逐 turn 版本逐项验证——全部命中 FAIL）"
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
    pc.add_argument("--run-id", default=None,
                    help="本 run 的唯一 id；给定时异 run 事件按污染记 conflict（P0-1）")
    pc.add_argument("--dmon-csv")
    pc.add_argument("--gpu-mem-total-mb", type=float)
    pc.add_argument("--out-dir", required=True,
                    help="归一化证据输出目录（先写 .tmp 再原子发布；已存在即拒绝）")
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
