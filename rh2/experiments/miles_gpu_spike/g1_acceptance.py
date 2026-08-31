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

V2（vendor refresh 第二批，per-token weight version spans）：
  - `weight_version_spans_coverage`（新检查，无新阈值键、纯语义）：
    rollout_group 事件新增 per-sample `weight_version_spans` 列（miles
    Sample.metadata rh2_weight_version_spans，rh2 canonicalize 从引擎
    meta_info.weight_versions 逐轮落下）。判定：记账列表
    （behavior_versions）必须与引擎一手区间证据逐项一致（跨更新 turn 只记
    单版本的 staleness 低报形态必红——此时 staleness_max_versions 自身按
    记账算是绿的）；区间结构合法（缝隙/重叠/空区间/越界必红，token 覆盖
    与 logprob_compare 的训练 token 数交叉）；生成期间权重前进过的 run
    必须携带 spans 证据（single_version_only 只在无 mid-run 更新窗口时
    合法，bootstrap 豁免）。staleness_max_versions 的逐项版本自动含区间
    全部版本（min over spans）。

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
import math
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


def _leaf_id(sample_index, leaf_ordinal) -> str:
    """leaf 唯一身份字符串（聚焦修复批 #1）。

    slime fan-out 的多个叶继承同一 Sample.index，(sample_index, leaf_ordinal)
    才是唯一叶身份（ordinal = 该 agent run 内的出现序号，rollout 侧与 trainer
    侧按同一扁平顺序计算）。leaf_ordinal 缺失（旧 wire/emitter）时退化为纯
    index 字符串——此时 collect 会登记 leaf_identity 缺口，judge 记 MISSING。
    """
    if leaf_ordinal is None:
        return str(sample_index)
    return f"{int(sample_index)}:{int(leaf_ordinal)}"


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
    # leaf 唯一身份缺口清单（聚焦修复批 #1）：任何一处事件缺 leaf_ordinal
    # 都在此登记；judge 的 leaf_identity 检查读 collect_report 记 MISSING
    # （缺身份不算绿，也不冒充 FAIL——身份缺失时对调/重复本就不可判）。
    identity_missing: list[str] = []
    steps_by_key: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for row in ev["train_step"]:
        steps_by_key[(row["rollout_id"], row["step_id"])].append(row)
    # per-rank 事实（聚焦修复批 #2：trainer per-rank oracle 的输入）。同一
    # (rollout, step, attempt, rank) 出现两条（无论内容是否相同）= 该 rank
    # 双重发射，记 conflict——census 要求每 rank 恰好一条。
    rank_facts: dict[tuple, dict] = {}
    for row in ev["train_step"]:
        rkey = (row["rollout_id"], row["step_id"], row.get("attempt"), row.get("rank"))
        fact = {
            k: row.get(k)
            for k in (
                "rollout_id", "step_id", "attempt", "rank", "dp_rank", "is_pp_last_stage",
                "outcome", "optimizer_step_applied", "adam_step_before", "adam_step_after",
                "scheduler_steps_before", "scheduler_steps_after", "num_rollouts",
                "grad_norm", "metrics",
            )
        }
        if rkey in rank_facts:
            conflicts.append(
                f"train_step r{rkey[0]}s{rkey[1]}a{rkey[2]} rank{rkey[3]} 重复发射"
                "（每 rank 每 step 恰好一条）"
            )
            continue
        rank_facts[rkey] = fact
    write_jsonl(
        out_dir / "step_rank_records.jsonl",
        [
            rank_facts[k]
            for k in sorted(
                rank_facts,
                key=lambda t: tuple(-1 if x is None else x for x in t),
            )
        ],
    )
    consumed_by_key: dict[tuple[int, int], dict[int, dict]] = defaultdict(dict)
    for row in ev["train_step_consumed"]:
        # 同 (rollout, step, dp_rank) 多条（TP/PP 复本）内容必须相同；冲突 =
        # 消费账本被改写（P0-8），记 conflict 而不是静默覆盖。
        key = (row["rollout_id"], row["step_id"])
        dp = row.get("dp_rank", 0)
        fact = {
            "sample_indices": row.get("sample_indices"),
            "leaf_ordinals": row.get("leaf_ordinals"),
            "num_tokens": row.get("num_tokens"),
            "num_microbatches": row.get("num_microbatches"),
            "error": row.get("error"),
        }
        if fact["sample_indices"] is not None and fact["leaf_ordinals"] is None:
            identity_missing.append(
                f"train_step_consumed r{key[0]}s{key[1]} dp{dp}：缺 leaf_ordinals（wire/emitter 过旧）"
            )
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
        # PP-last 各 rank 的 metrics 经 DP 组 all-reduce，应逐 rank 一致；
        # 不一致 = 归约面被破坏（聚焦修复批 #2：不再"随便取第一条"）。
        metrics = (
            _consistent([r["metrics"] for r in metric_rows], f"step r{rid}s{sid}.metrics", conflicts)
            if metric_rows
            else {}
        ) or {}
        consumed_shards = consumed_by_key.get((rid, sid), {})
        consumed_ids: list[str] | None = None
        num_tokens = None
        dp_ranks: list[int] | None = None
        if consumed_shards:
            merged: list[str] = []
            tok = 0
            tok_known = True
            dp_ranks = sorted(consumed_shards)
            for _dp, fact in sorted(consumed_shards.items()):
                if fact.get("sample_indices") is None:
                    conflicts.append(f"step r{rid}s{sid} consumed 分片缺 sample_indices: {fact.get('error')}")
                    continue
                ords = fact.get("leaf_ordinals")
                if ords is not None and len(ords) != len(fact["sample_indices"]):
                    conflicts.append(
                        f"step r{rid}s{sid} consumed 分片 leaf_ordinals 长度 {len(ords)} != "
                        f"sample_indices 长度 {len(fact['sample_indices'])}"
                    )
                    ords = None
                merged.extend(
                    _leaf_id(i, ords[pos] if ords is not None else None)
                    for pos, i in enumerate(fact["sample_indices"])
                )
                if fact.get("num_tokens") is None:
                    tok_known = False
                else:
                    tok += int(fact["num_tokens"])
            consumed_ids = sorted(merged)
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

    # -- 对拍摘要：(sample_index, leaf_ordinal) -> loss_mask=1 口径事实（P0-8）-
    logprob_facts: dict[str, dict] = {}
    for row in ev["logprob_compare"]:
        for entry in row.get("entries", []):
            idx = int(entry["sample_index"])
            ordinal = entry.get("leaf_ordinal")
            if ordinal is None:
                identity_missing.append(f"logprob_compare sample{idx}：entry 缺 leaf_ordinal")
            fact = {
                "same_version": bool(entry.get("same_version")),
                "mean_abs_diff": entry.get("mean_abs_diff"),
                "length_mismatch": entry.get("length_mismatch"),
                "num_tokens": entry.get("num_tokens"),
            }
            _dedupe_fact(logprob_facts, _leaf_id(idx, ordinal), fact, "logprob_compare sample", conflicts)
    if not ev["logprob_compare"]:
        missing.append("logprob_compare：无对拍事件（同版本 logprob 差无证据）")

    # -- 逐样本 DIS token 记账（正控归因，P0-8）-------------------------------
    dis_facts: dict[str, dict] = {}
    for row in ev["sample_dis_accounting"]:
        for entry in row.get("entries", []):
            idx = int(entry["sample_index"])
            ordinal = entry.get("leaf_ordinal")
            if ordinal is None:
                identity_missing.append(f"sample_dis_accounting sample{idx}：entry 缺 leaf_ordinal")
            fact = {
                "accepted_tokens": entry.get("accepted_tokens"),
                "provenance_tokens": entry.get("provenance_tokens"),
            }
            _dedupe_fact(dis_facts, _leaf_id(idx, ordinal), fact, "sample_dis_accounting sample", conflicts)

    # -- sample 级：rollout_group + group_filtered ---------------------------
    sample_rows: list[dict] = []
    for row in sorted(ev["rollout_group"], key=lambda r: (r.get("rollout_id", -1), r.get("group_index", -1))):
        rid = row.get("rollout_id")
        gid = f"r{rid}/g{row.get('group_index')}"
        indices = row.get("sample_indices") or []
        rewards = row.get("rewards") or []
        versions = row.get("behavior_versions") or []
        tapes = row.get("routing_tape") or []
        # V2：per-sample 结构化版本区间证据（miles Sample.metadata
        # rh2_weight_version_spans -> rollout_group 事件同名列；旧 emitter
        # 无该字段 -> 整列 None，judge 按"无 spans 证据面"处理）。
        spans_col = row.get("weight_version_spans")
        ordinals = row.get("leaf_ordinals")
        if ordinals is None:
            identity_missing.append(f"rollout_group {gid}：缺 leaf_ordinals（emitter 过旧）")
        elif len(ordinals) != len(indices):
            conflicts.append(
                f"rollout_group {gid}：leaf_ordinals 长度 {len(ordinals)} != sample_indices 长度 {len(indices)}"
            )
            ordinals = None
        for i, sample_index in enumerate(indices):
            behavior_versions = versions[i] if i < len(versions) else []
            ordinal = ordinals[i] if ordinals is not None else None
            leaf = _leaf_id(sample_index, ordinal)
            lp = logprob_facts.get(leaf)
            dis = dis_facts.get(leaf)
            sample_rows.append(
                {
                    "sample_id": leaf,
                    "sample_index": int(sample_index),
                    "leaf_ordinal": None if ordinal is None else int(ordinal),
                    "rollout_id": rid,
                    "source": "train_batch",
                    "instance_id": row.get("instance_id"),
                    "group_id": gid,
                    "reward": rewards[i] if i < len(rewards) else None,
                    "behavior_versions": behavior_versions,
                    "behavior_version": _min_numeric_version(behavior_versions),
                    "weight_version_spans": (
                        spans_col[i]
                        if isinstance(spans_col, list) and i < len(spans_col)
                        else None
                    ),
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
                    "trained": consumed_step_applied.get(leaf, False),
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
                    # 被过滤组不进训练面，无 leaf fan-out 身份要求；保留纯
                    # index 身份供拒绝面不相交检查（按 sample_index 对比）。
                    "sample_id": str(sample_index),
                    "sample_index": int(sample_index),
                    "leaf_ordinal": None,
                    "rollout_id": None,
                    "source": "filtered",
                    "filtered_reason": row.get("reason"),
                    "instance_id": row.get("instance_id"),
                    "group_id": f"filtered{ordinal}/g{row.get('group_index')}",
                    "reward": rewards[i] if i < len(rewards) else None,
                    "behavior_versions": None,
                    "behavior_version": None,
                    "weight_version_spans": None,
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
            "records_min", "records_max", "expected_records", "num_samples",
            "sample_indices", "leaf_ordinals", "sample_digests",
        )}
        if fact["sample_digests"] is not None and (
            fact["sample_indices"] is None or fact["leaf_ordinals"] is None
        ):
            identity_missing.append(
                f"replay_fill r{row.get('rollout_id')} rank{row.get('rank')}："
                "缺 sample_indices/leaf_ordinals（digest 无法绑定到具体 leaf）"
            )
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
        # leaf 身份缺口（聚焦修复批 #1）：judge 的 leaf_identity 检查消费；
        # 非空 = MISSING_EVIDENCE（身份缺失时重复/对调不可判，不算绿）。
        "leaf_identity_missing": identity_missing,
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
        report = json.loads(report_path.read_text())
        conflicts = report.get("conflicts", [])
        if conflicts:
            j.add("collect_consistency", FAIL, "; ".join(conflicts[:6]))
        # -- leaf 唯一身份完整性（聚焦修复批 #1）：训练面任一事件缺
        #    (sample_index, leaf_ordinal) 身份 → MISSING（身份缺失时 fan-out
        #    叶的重复消费/tape 对调本就不可判，缺身份不算绿）。
        id_missing = report.get("leaf_identity_missing", [])
        if id_missing:
            leaf_identity_ok = False
            j.add(
                "leaf_identity",
                MISSING,
                "; ".join(id_missing[:4]) + f"（共 {len(id_missing)} 处身份缺口）",
            )
        else:
            leaf_identity_ok = True
            j.add("leaf_identity", PASS, "训练面事件均携带 (sample_index, leaf_ordinal) 唯一叶身份")
    else:
        leaf_identity_ok = False
        j.add("leaf_identity", MISSING, "collect_report.json 缺失（collect 未成功发布）")

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

    # -- trainer per-rank oracle（聚焦修复批 #2：rank census / 跨 step 持续 /
    #    metrics 覆盖与有限性——聚合面无法证明"所有 rank 的 optimizer 状态
    #    都齐全且持续"，三个已复现反例见 thresholds.md 对应行）--------------
    _judge_train_step_ranks(j, coll, th)

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
                "存在/可解析/<=current；V2 起版本列表含 per-token 区间的全部版本，"
                "min 覆盖 turn 内跨更新的真实最旧版本）",
            )

    # -- V2：per-token 权重版本区间证据（spans 覆盖 / 低报审计）---------------
    _judge_weight_version_spans(j, train_samples, publish)

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

    # -- fan-out 多叶覆盖（聚焦修复批 #1：G1 数据形态要求"fan-out 多叶"，全
    #    线性 fixture/运行不得冒充覆盖——必须证明真的出现过 ≥N 个多叶 run）--
    _judge_fanout_coverage(j, train_samples)

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

    # -- 队列守恒（P0-8：multiset 相等 + rank 齐全，替代单纯查重；leaf 身份
    #    缺失时守恒双向不可判——纯 index 口径会把合法 fan-out 判成重复消费，
    #    也检不出真正的同 leaf 双消费——记 MISSING 而非沿旧口径判）-----------
    _judge_queue(j, steps, samples, th, leaf_identity_ok=leaf_identity_ok)

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


def _judge_weight_version_spans(j: Judge, train_samples, publish) -> None:
    """`weight_version_spans_coverage`：per-token 权重版本区间证据判定（V2）。

    背景（adv_miles 反例）：sglang-miles（4e230c3d weight_versions.py）对跨
    权重更新的请求返回 `meta_info.weight_versions=[{version,start,end},...]`，
    单数 `weight_version` 只是最后区间——只记单数会把 v10+v11 的 turn 记成
    全 v11，`staleness_max_versions` 用 min(behavior_versions) 算出的
    staleness 因此低报，可能放本应拒绝的过期样本入训。**staleness 检查本身
    已改逐区间参与**（capture/backfill 把区间全部版本并入 behavior_versions，
    min over spans）；本检查补上独立审计面——记账列表必须与引擎一手区间
    证据一致，有更新窗口的 run 必须携带区间证据。

    证据形态（rollout_group 事件 `weight_version_spans` 列 -> sample_records
    行同名字段）：逐入训轮列表，每轮
    `{"provenance": "engine_spans", "spans": [{version,start,end},...]}` 或
    `{"provenance": "single_version_only", "spans": null, "version": v}`。

    判定规则（无新阈值键，纯语义）：

    A. 全部训练样本无 spans 证据：若 run 内存在 mid-run 权重前进
       （publish updates 中 rollout_id 非 None 的条目；bootstrap 豁免——它
       发生在任何生成之前）→ FAIL（"权重更新期间在途 turn"的验收联结：
       生成与更新并发的 run 里 single_version_only 无法排除 turn 内低报）；
       无 mid-run 更新 → PASS（单版本记账合法窗口）；publish 事实缺失 →
       MISSING（无法判定更新窗口，缺证据不算绿）。
    B. 任一样本有 spans（引擎已证明支持）：每个训练样本都必须有——逐轮
       校验结构（缝隙/重叠/空区间/首 start≠0/相邻同版本/版本不可解析 →
       FAIL），展平版本序列必须与 behavior_versions **逐项相等**（跨更新
       turn 只记单版本的低报形态在此必红），engine_spans 轮的区间覆盖
       token 总数与训练 token 数（logprob_compare 的 loss_mask=1 计数，
       独立证据面）交叉相等（区间越界/欠覆盖必红；行无对拍或长度错位时
       跳过交叉，由对拍检查自己负责）。

    诚实边界（detail 也写明）：引擎自身低报（该报多区间却只报一个）无法从
    事件层证伪——那由 sglang 侧单测/GPU tests 覆盖（本仓 pin 的
    SGLANG_COMMIT 已含）；本检查证明的是 rh2/miles 记账层没有丢失或改写
    引擎报告的区间事实。
    """

    key = "weight_version_spans_coverage"
    if not train_samples:
        j.add(key, MISSING, "sample_records.jsonl 缺失或无训练批样本")
        return
    updates_mid_run = None
    if publish is not None:
        updates_mid_run = [
            u for u in publish.get("updates", []) if u.get("rollout_id") is not None
        ]
    has_any = any(r.get("weight_version_spans") for r in train_samples)
    if not has_any:
        if updates_mid_run is None:
            j.add(
                key,
                MISSING,
                "无任何 spans 证据且 publish_records.json 缺失——无法判定 run 内是否存在更新窗口",
            )
        elif updates_mid_run:
            j.add(
                key,
                FAIL,
                f"生成期间权重版本前进 {len(updates_mid_run)} 次而训练样本无任何 per-token "
                "spans 证据——single_version_only 记账只在无更新窗口时合法，turn 内跨更新的 "
                "staleness 低报不可排除（需 sglang-miles spans 引擎 + emitter 的 "
                "weight_version_spans 列）",
            )
        else:
            j.add(
                key,
                PASS,
                "run 内无 mid-run 权重更新（仅 bootstrap）——单版本记账处于合法窗口，"
                "spans 证据缺席不构成低报风险",
            )
        return

    problems: list[str] = []
    checked = 0
    multi_span_samples = 0
    for r in train_samples:
        sid_ = r["sample_id"]
        entry = r.get("weight_version_spans")
        if not entry:
            problems.append(f"{sid_}: 缺 spans 证据（同 run 其它样本已证明引擎支持 spans）")
            continue
        if not isinstance(entry, list):
            problems.append(f"{sid_}: spans 证据不是逐轮列表（{type(entry).__name__}）")
            continue
        flat: list[str] = []
        total_tokens = 0
        coverage_known = True  # single_version_only 轮无 token 覆盖声明 -> 跳过交叉
        bad = False
        for t_i, turn in enumerate(entry):
            if not isinstance(turn, dict):
                problems.append(f"{sid_}: 第 {t_i} 轮不是结构化对象")
                bad = True
                break
            prov = turn.get("provenance")
            spans = turn.get("spans")
            if prov == "engine_spans":
                if not isinstance(spans, list) or not spans:
                    problems.append(
                        f"{sid_}: 第 {t_i} 轮 provenance=engine_spans 但无区间列表"
                    )
                    bad = True
                    break
                prev_end: int | None = None
                prev_version: str | None = None
                for s_i, sp in enumerate(spans):
                    shape_ok = (
                        isinstance(sp, dict)
                        and isinstance(sp.get("start"), int)
                        and isinstance(sp.get("end"), int)
                        and not isinstance(sp.get("start"), bool)
                        and not isinstance(sp.get("end"), bool)
                        and sp.get("version") is not None
                    )
                    if not shape_ok:
                        problems.append(f"{sid_}: 第 {t_i} 轮第 {s_i} 区间形状非法 {sp!r}")
                        bad = True
                        break
                    ver = str(sp["version"])
                    if not ver.isdigit():
                        problems.append(
                            f"{sid_}: 第 {t_i} 轮区间版本不可解析 {ver!r}（miles 版本为十进制计数器）"
                        )
                        bad = True
                        break
                    if s_i == 0 and sp["start"] != 0:
                        problems.append(f"{sid_}: 第 {t_i} 轮首区间 start={sp['start']} != 0")
                        bad = True
                        break
                    if prev_end is not None and sp["start"] != prev_end:
                        kind = "缝隙" if sp["start"] > prev_end else "重叠"
                        problems.append(
                            f"{sid_}: 第 {t_i} 轮区间{kind}：[..,{prev_end}) 与 "
                            f"[{sp['start']},{sp['end']})"
                        )
                        bad = True
                        break
                    if prev_version is not None and ver == prev_version:
                        problems.append(
                            f"{sid_}: 第 {t_i} 轮相邻区间同版本 {ver!r}（引擎侧必合并，重复=证据被改写）"
                        )
                        bad = True
                        break
                    if sp["end"] <= sp["start"]:
                        problems.append(
                            f"{sid_}: 第 {t_i} 轮空/倒置区间 [{sp['start']},{sp['end']})"
                        )
                        bad = True
                        break
                    prev_end, prev_version = sp["end"], ver
                    flat.append(ver)
                if bad:
                    break
                total_tokens += prev_end or 0
            elif prov == "single_version_only":
                if spans:
                    problems.append(
                        f"{sid_}: 第 {t_i} 轮声称 single_version_only 却携带区间列表"
                    )
                    bad = True
                    break
                if updates_mid_run is None:
                    problems.append(
                        f"{sid_}: 第 {t_i} 轮 single_version_only 且 publish 事实缺失——无法证明无更新窗口"
                    )
                    bad = True
                    break
                if updates_mid_run:
                    problems.append(
                        f"{sid_}: 第 {t_i} 轮 provenance=single_version_only 而 run 内权重前进过"
                        "——该轮 turn 内跨更新的低报不可排除"
                    )
                    bad = True
                    break
                ver_single = turn.get("version")
                if ver_single is None:
                    problems.append(f"{sid_}: 第 {t_i} 轮 single_version_only 缺 version")
                    bad = True
                    break
                flat.append(str(ver_single))
                coverage_known = False
            else:
                problems.append(f"{sid_}: 第 {t_i} 轮未知 provenance={prov!r}")
                bad = True
                break
        if bad:
            continue
        behavior = [str(v) for v in (r.get("behavior_versions") or [])]
        if flat != behavior:
            problems.append(
                f"{sid_}: 版本记账与引擎区间证据不一致：behavior_versions={behavior} vs "
                f"spans 展平={flat}——跨更新 turn 只记单版本（staleness 低报）或记账被改写"
            )
            continue
        if (
            coverage_known
            and r.get("has_logprob_entry")
            and r.get("logprob_length_mismatch") is False
            and isinstance(r.get("logprob_masked_tokens"), int)
            and r["logprob_masked_tokens"] > 0
            and total_tokens != r["logprob_masked_tokens"]
        ):
            problems.append(
                f"{sid_}: 区间覆盖 token 总数 {total_tokens} != 训练 token 数 "
                f"{r['logprob_masked_tokens']}（区间越界/欠覆盖——end 声明超出或不足真实生成量）"
            )
            continue
        checked += 1
        if len(set(flat)) > 1:
            multi_span_samples += 1
    if problems:
        j.add(key, FAIL, "; ".join(problems[:4]))
    else:
        j.add(
            key,
            PASS,
            f"{checked} 个训练样本的区间证据结构合法、与版本记账逐项一致、token 覆盖与训练 "
            f"token 数交叉相符（其中 {multi_span_samples} 个样本携带跨更新多版本证据；"
            "引擎自身漏报区间无法从事件层证伪，由 sglang 侧测试覆盖）",
        )


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
    # 聚焦修复批 #5：thresholds_sha256 缺失/空/非法不得 PASS——否则 manifest
    # 丢字段时 verdict 仍声称"三方一致"，判定阈值失去外部锚点。
    want_sha = manifest.get("thresholds_sha256")
    got_sha = hashlib.sha256(thresholds_path.read_bytes()).hexdigest()
    if not (isinstance(want_sha, str) and re.fullmatch(r"[0-9a-f]{64}", want_sha)):
        problems.append(
            f"run_manifest.json 的 thresholds_sha256 缺失/空/非法（got {want_sha!r}）——"
            "阈值页没有被 run 钉死，不得声称三方一致"
        )
    elif want_sha != got_sha:
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
        # 逐条有限性/非负校验必须先于 max：Python 的 max 对 NaN 顺序敏感
        # （max([0.01, nan]) == 0.01），尾部 NaN 会被静默掩掉——parity 用的是
        # 独立 forward-only 结果，训练 forward 的 finite 检查兜不住它。
        bad = [d for d in diffs if not (isinstance(d, (int, float)) and math.isfinite(d) and d >= 0)]
        if bad:
            j.add(
                "logprob_same_version_mean_abs_diff_max",
                FAIL,
                f"对拍摘要含非有限/负值 {bad[:4]}（共 {len(bad)} 条）——NaN/Inf/负数一律 FAIL",
            )
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


def _judge_fanout_coverage(j: Judge, train_samples: list[dict] | None) -> None:
    """聚焦修复批 #1：G1 必须证明运行中真出现 ≥N 个多叶 fan-out run。

    多叶 run = 同一 sample_index（= 同一 agent run）在训练批中出现 ≥2 个不同
    leaf_ordinal 的叶。全线性数据（每 run 单叶）不满足 G1 数据形态里的
    "fan-out 多叶"覆盖要求，不得冒充。身份缺失（leaf_ordinal=None）时记
    MISSING（与 leaf_identity 检查同因）。
    """
    key = "g1_fanout_multileaf_coverage"
    need = j.th["g1_min_multileaf_fanout_runs"]
    if not train_samples:
        j.add(key, MISSING, "sample_records.jsonl 缺失或无训练批样本")
        return
    if any(s.get("leaf_ordinal") is None for s in train_samples):
        j.add(key, MISSING, "训练样本缺 leaf_ordinal（见 leaf_identity 检查）——多叶覆盖不可判")
        return
    leaves_by_run: dict[int, set] = defaultdict(set)
    for s in train_samples:
        leaves_by_run[s["sample_index"]].add(s["leaf_ordinal"])
    multi = sorted(k for k, v in leaves_by_run.items() if len(v) >= 2)
    j.add(
        key,
        PASS if len(multi) >= need else FAIL,
        (
            f"多叶 fan-out run 数={len(multi)}（如 sample_index {multi[:4]}；需 ≥{need}）"
            if len(multi) >= need
            else f"多叶 fan-out run 数={len(multi)} < {need}——全线性数据不构成 G1 fan-out 覆盖"
        ),
    )


def _judge_train_step_ranks(j: Judge, coll: Path, th: dict) -> None:
    """聚焦修复批 #2：trainer per-rank oracle（三个已复现假绿反例的判定面）。

    - train_step_global_rank_census：每个 (rollout, step, attempt) 必须恰好
      覆盖全部预期 global rank（无缺失/额外；重复由 collect 记 conflict）；
      rank→dp/pp 映射跨 step 稳定，dp 覆盖 0..D-1（反例：删除 rank5 全部
      train_step、其余 rank 齐全，聚合面照常 PASS）。
    - optimizer_state_continuity_per_rank：逐 rank 按真实 step 顺序验证
      next.before == prev.after（Adam 与 scheduler 两条链），applied step 的
      Adam 恰 +1、scheduler 恰 +num_rollouts（反例：每步 Adam 0→1、scheduler
      0→32 模拟每步重建 optimizer——单步自洽但链断裂）。
    - train_step_metrics_coverage：pp-last 各 dp 都必须携带 metrics 且逐
      rank 一致（不得只取第一条）；applied step 的 grad_norm（全 rank）与
      metrics.loss（pp-last）必须在场且有限（反例：NaN loss/grad_norm）。
    """
    checks = (
        "train_step_global_rank_census",
        "optimizer_state_continuity_per_rank",
        "train_step_metrics_coverage",
    )
    path = coll / "step_rank_records.jsonl"
    rows = read_jsonl(path) if path.exists() else None
    if not rows:
        for ck in checks:
            j.add(ck, MISSING, "step_rank_records.jsonl 缺失或为空（train_step 事件不全）")
        return
    n_ranks, n_dp = th.get("expected_trainer_global_ranks"), th.get("expected_dp_ranks")
    if n_ranks is None or n_dp is None:
        for ck in checks:
            j.add(ck, MISSING, "thresholds 缺 expected_trainer_global_ranks/expected_dp_ranks（拓扑未声明）")
        return
    expected_ranks = set(range(int(n_ranks)))

    # -- census + rank→dp/pp 映射稳定 ---------------------------------------
    problems: list[str] = []
    by_step: dict[tuple, set] = defaultdict(set)
    for r in rows:
        by_step[(r.get("rollout_id"), r.get("step_id"), r.get("attempt"))].add(r.get("rank"))
    for skey in sorted(by_step, key=lambda t: tuple(-1 if x is None else x for x in t)):
        ranks = by_step[skey]
        tag = f"r{skey[0]}s{skey[1]}a{skey[2]}"
        if None in ranks:
            problems.append(f"{tag}: 存在缺 rank 字段的 train_step 事件")
            ranks = ranks - {None}
        missing_ranks = sorted(expected_ranks - ranks)
        extra_ranks = sorted(ranks - expected_ranks)
        if missing_ranks:
            problems.append(f"{tag}: 缺 rank {missing_ranks}（该 rank 的 optimizer 状态无证据）")
        if extra_ranks:
            problems.append(f"{tag}: 预期 census 之外的 rank {extra_ranks}（拓扑声明失真）")
    map_by_rank: dict[int, set] = defaultdict(set)
    for r in rows:
        if r.get("rank") is not None:
            map_by_rank[r["rank"]].add((r.get("dp_rank"), bool(r.get("is_pp_last_stage"))))
    dp_values: set = set()
    for rank in sorted(map_by_rank):
        pairs = map_by_rank[rank]
        if len(pairs) > 1:
            problems.append(f"rank{rank} 的 dp/pp 归属跨 step 漂移：{sorted(pairs)}")
            continue
        dp, _is_last = next(iter(pairs))
        if dp is None:
            problems.append(f"rank{rank} 缺 dp_rank 字段")
        else:
            dp_values.add(dp)
    if dp_values and dp_values != set(range(int(n_dp))):
        problems.append(f"dp 覆盖 {sorted(dp_values)} != 预期 0..{int(n_dp) - 1}")
    j.add(
        "train_step_global_rank_census",
        PASS if not problems else FAIL,
        (
            f"每个 (rollout, step, attempt) 恰好覆盖 {len(expected_ranks)} 个 global rank；"
            "rank→dp/pp 映射稳定且 dp 齐全"
            if not problems
            else "; ".join(problems[:6])
        ),
    )

    # -- 逐 rank 跨 step 持续性 + 精确步进 -----------------------------------
    problems2: list[str] = []
    unknown = 0
    rows_by_rank: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("rank") is not None:
            rows_by_rank[r["rank"]].append(r)
    for rank in sorted(rows_by_rank):
        ordered = sorted(
            rows_by_rank[rank],
            key=lambda r: (r.get("rollout_id"), r.get("step_id"), r.get("attempt") or 0),
        )
        prev = None
        for r in ordered:
            ab, aa = r.get("adam_step_before"), r.get("adam_step_after")
            sb, sa = r.get("scheduler_steps_before"), r.get("scheduler_steps_after")
            applied = r.get("optimizer_step_applied")
            tag = f"rank{rank} r{r.get('rollout_id')}s{r.get('step_id')}"
            if None in (ab, aa, sb, sa) or applied is None:
                unknown += 1
                prev = None  # 链条断口：不拿未知值当锚点
                continue
            if applied:
                if aa != ab + 1:
                    problems2.append(f"{tag}: applied 但 Adam {ab}->{aa}（应恰 +1）")
                nroll = r.get("num_rollouts")
                if nroll is None:
                    unknown += 1
                elif sa != sb + int(nroll):
                    problems2.append(
                        f"{tag}: scheduler {sb}->{sa} != +num_rollouts({nroll})——LR 步进不精确"
                    )
            elif aa != ab or sa != sb:
                problems2.append(f"{tag}: 未 applied 但计数前进 adam {ab}->{aa} sched {sb}->{sa}")
            if prev is not None and (ab != prev[0] or sb != prev[1]):
                problems2.append(
                    f"{tag}: 与上一 step 断链（adam prev.after={prev[0]} -> before={ab}，"
                    f"sched prev.after={prev[1]} -> before={sb}）——optimizer/scheduler 状态"
                    "未持续（疑似每步重建）"
                )
            prev = (aa, sa)
    if problems2:
        j.add("optimizer_state_continuity_per_rank", FAIL, "; ".join(problems2[:6]))
    elif unknown:
        j.add("optimizer_state_continuity_per_rank", MISSING, f"{unknown} 条 rank 级 step 缺计数/num_rollouts 事实")
    else:
        j.add(
            "optimizer_state_continuity_per_rank",
            PASS,
            "逐 rank next.before==prev.after；applied 步 Adam 恰 +1、scheduler 恰 +num_rollouts",
        )

    # -- pp-last metrics 覆盖全 DP + applied 步 loss/grad_norm 有限 -----------
    problems3: list[str] = []
    by_step_rows: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_step_rows[(r.get("rollout_id"), r.get("step_id"), r.get("attempt"))].append(r)
    for skey in sorted(by_step_rows, key=lambda t: tuple(-1 if x is None else x for x in t)):
        rs = by_step_rows[skey]
        tag = f"r{skey[0]}s{skey[1]}"
        pp_last = [r for r in rs if r.get("is_pp_last_stage")]
        if not pp_last:
            problems3.append(f"{tag}: 无任何 is_pp_last_stage=True 的 rank（指标面缺失）")
            continue
        no_metrics = sorted(r.get("rank") for r in pp_last if not r.get("metrics"))
        if no_metrics:
            problems3.append(f"{tag}: pp-last rank{no_metrics} 缺 metrics（指标必须覆盖全部 DP，不得只取一条）")
        with_metrics = [r for r in pp_last if r.get("metrics")]
        dps = {r.get("dp_rank") for r in with_metrics}
        if dps != set(range(int(n_dp))):
            problems3.append(f"{tag}: 携带 metrics 的 pp-last dp 覆盖 {sorted(dps)} != 0..{int(n_dp) - 1}")
        blobs = {json.dumps(r.get("metrics"), sort_keys=True) for r in with_metrics}
        if len(blobs) > 1:
            problems3.append(f"{tag}: pp-last metrics 跨 dp 不一致（DP all-reduce 面破坏）")
        if all(r.get("optimizer_step_applied") is True for r in rs) and rs:
            bad_gn = [
                r.get("rank")
                for r in rs
                if r.get("grad_norm") is None or not math.isfinite(float(r["grad_norm"]))
            ]
            if bad_gn:
                problems3.append(f"{tag}: applied 但 rank{sorted(bad_gn)[:4]} 的 grad_norm 缺失/非有限")
            bad_loss = [
                r.get("rank")
                for r in with_metrics
                if r["metrics"].get("loss") is None or not math.isfinite(float(r["metrics"]["loss"]))
            ]
            if bad_loss:
                problems3.append(f"{tag}: applied 但 pp-last rank{sorted(bad_loss)[:4]} 的 loss 缺失/非有限")
    j.add(
        "train_step_metrics_coverage",
        PASS if not problems3 else FAIL,
        (
            "pp-last metrics 覆盖全部 DP、逐 rank 一致；applied 步 loss/grad_norm 在场且有限"
            if not problems3
            else "; ".join(problems3[:6])
        ),
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

    # source -> trainer 联结（聚焦修复批 #1：leaf_id → digest **精确**联结。
    # digest multiset 相等不能证明 tape 属于正确 leaf——两个 fan-out 叶的
    # tape 对调后 multiset 不变；这里要求逐 leaf 的映射完全一致）。
    if not train_samples:
        j.add(lk, MISSING, "sample_records.jsonl 缺失或无训练批样本（rollout 侧 tape 来源无证据）")
        return
    if any(f.get("sample_digests") is None for f in fills):
        j.add(lk, MISSING, "replay_fill 缺 sample_digests（无 trainer 侧 tape 身份）")
        return
    if any(f.get("sample_indices") is None or f.get("leaf_ordinals") is None for f in fills):
        j.add(lk, MISSING, "replay_fill 缺 sample_indices/leaf_ordinals（digest 无法绑定 leaf，见 leaf_identity）")
        return
    if any(s.get("leaf_ordinal") is None for s in train_samples if s.get("routing_tape")):
        j.add(lk, MISSING, "rollout 侧 tape 样本缺 leaf_ordinal（见 leaf_identity）")
        return
    link_problems: list[str] = []
    for rid in sorted(rollouts):
        expected: dict[str, str | None] = {
            s["sample_id"]: (s.get("routing_tape") or {}).get("digest")
            for s in train_samples
            if s.get("rollout_id") == rid and s.get("routing_tape")
        }
        # 同 dp 组的 PP/EP 副本消费同一份数据：leaf→digest 映射必须逐副本一致
        # （不再 setdefault 取首条——副本间冲突 = 消费账本被改写或错绑）。
        rep_by_dp: dict[int, dict[str, str]] = {}
        rep_rank_by_dp: dict[int, object] = {}
        for f in fills:
            if f.get("rollout_id") != rid or f.get("dp_rank") is None:
                continue
            idxs, ords, digs = f["sample_indices"], f["leaf_ordinals"], f["sample_digests"]
            if not (len(idxs) == len(ords) == len(digs)):
                link_problems.append(
                    f"r{rid} rank{f.get('rank')}: fill 身份列与 digest 列长度不一致"
                    f"（{len(idxs)}/{len(ords)}/{len(digs)}）"
                )
                continue
            fmap: dict[str, str] = {}
            for i, o, d in zip(idxs, ords, digs):
                lid = _leaf_id(i, o)
                if lid in fmap and fmap[lid] != d:
                    link_problems.append(f"r{rid} rank{f.get('rank')}: fill 内 leaf {lid} 重复且 digest 冲突")
                fmap[lid] = d
            dp = f["dp_rank"]
            if dp not in rep_by_dp:
                rep_by_dp[dp] = fmap
                rep_rank_by_dp[dp] = f.get("rank")
            elif rep_by_dp[dp] != fmap:
                link_problems.append(
                    f"r{rid} dp{dp}: 同 DP 副本 leaf→digest 映射冲突"
                    f"（rank{rep_rank_by_dp[dp]} vs rank{f.get('rank')}）——PP/EP 副本必须消费同一份数据"
                )
        actual: dict[str, str] = {}
        for dp in sorted(rep_by_dp):
            for lid, d in rep_by_dp[dp].items():
                if lid in actual:
                    link_problems.append(f"r{rid}: leaf {lid} 出现在多个 dp 分片（重复消费）")
                actual[lid] = d
        if actual != expected:
            miss_leaves = sorted(set(expected) - set(actual))
            extra_leaves = sorted(set(actual) - set(expected))
            wrong = sorted(lid for lid in set(actual) & set(expected) if actual[lid] != expected[lid])
            parts = []
            if miss_leaves:
                parts.append(f"缺 leaf {miss_leaves[:4]}")
            if extra_leaves:
                parts.append(f"多 leaf {extra_leaves[:4]}")
            if wrong:
                parts.append(f"digest 与来源 tape 错绑的 leaf {wrong[:4]}（含 fan-out 叶 tape 对调）")
            link_problems.append(f"r{rid}: trainer leaf→digest 精确联结失败（{'；'.join(parts)}）")
    j.add(
        lk,
        PASS if not link_problems else FAIL,
        "trainer fill 的 leaf_id→digest 映射与 rollout 侧逐 leaf 精确一致（逐轮）"
        if not link_problems
        else "; ".join(link_problems[:4]),
    )


def _judge_queue(
    j: Judge, steps: list[dict] | None, samples: list[dict] | None, th: dict, *, leaf_identity_ok: bool = True
) -> None:
    """P0-8：admitted==consumed multiset、filtered 不相交、预期 dp rank 齐全。"""
    if steps is None or any(s.get("queue_consumed_sample_ids") is None for s in steps):
        j.add("queue_multiset_conservation", MISSING, "queue_consumed_sample_ids 证据缺失")
        j.add("train_step_rank_coverage", MISSING, "train_step_consumed 证据缺失")
        return
    consumed = Counter(x for s in steps for x in s["queue_consumed_sample_ids"])
    train_rows = [s for s in samples if s.get("source") == "train_batch"] if samples else []
    if not leaf_identity_ok:
        j.add(
            "queue_multiset_conservation",
            MISSING,
            "leaf 身份缺失（见 leaf_identity）——纯 index 口径会把合法 fan-out 判成重复消费、"
            "又检不出同 leaf 双消费，守恒不可判",
        )
    elif not train_rows:
        j.add("queue_multiset_conservation", MISSING, "无训练批样本事件（admitted 面无证据）")
    else:
        # 身份口径（聚焦修复批 #1）：sample_id = leaf 唯一身份
        # "<index>:<ordinal>"——合法的两个 fan-out 叶不再被当成"重复消费"
        # 假红；同一 leaf 真被消费两次仍然 FAIL。filtered 不相交检查按
        # sample_index（agent run 身份）对比：被过滤组没有 leaf 身份。
        admitted = Counter(s["sample_id"] for s in train_rows)
        filtered_idx = {s["sample_index"] for s in samples if s.get("source") == "filtered"}
        problems = []
        missing_ids = admitted - consumed
        extra_ids = consumed - admitted
        if missing_ids:
            problems.append(f"admitted 但未消费：{sorted(missing_ids)[:5]}（共 {sum(missing_ids.values())}）")
        if extra_ids:
            problems.append(f"消费了未 admitted 的样本：{sorted(extra_ids)[:5]}（共 {sum(extra_ids.values())}）")
        dups = {k: v for k, v in consumed.items() if v > 1}
        if dups:
            problems.append(f"重复消费（同一 leaf）：{dict(list(dups.items())[:4])}")
        admitted_idx = {s["sample_index"] for s in train_rows}
        consumed_idx = {int(str(x).split(":")[0]) for x in consumed}
        overlap = filtered_idx & (admitted_idx | consumed_idx)
        if overlap:
            problems.append(f"filtered 样本出现在训练/消费面：{sorted(overlap)[:5]}")
        j.add(
            "queue_multiset_conservation",
            PASS if not problems else FAIL,
            (
                f"admitted == consumed（{sum(admitted.values())} 个 leaf exactly-once），filtered 不相交"
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

# 每 rollout 2 个 optimizer step、dp 2 分片、每轮 2 组 × 8 run；rollout 0 的
# 第 1 组第一个 run 产生 2 个 fan-out 叶（G1 数据形态"fan-out 多叶"覆盖，
# 聚焦修复批 #1——两叶共享 sample_index，靠 leaf_ordinal 区分）。
_N_ROLLOUTS, _STEPS_PER_ROLLOUT, _GROUP_SIZE = 3, 2, 8
_MB_PER_STEP = 2  # 每 dp rank 每 step 的 microbatch 数（replay 消费联结用）
_NUM_ROLLOUTS_PER_STEP = 32  # applied step 的 scheduler 精确步进（opt_param_scheduler.step(increment=...)）
# trainer 拓扑：与 thresholds 的 expected_trainer_global_ranks / expected_dp_ranks
# 一致（6 actor GPU、TP1*PP3*CP1 -> dp=2）。dp = rank % 2 是代表性映射：oracle 只
# 要求 rank->dp 映射自洽，不假设具体 megatron rank 排序。
_TRAIN_GLOBAL_RANKS, _DP_RANKS = 6, 2
_PP_LAST_FIRST_RANK = _TRAIN_GLOBAL_RANKS - _DP_RANKS  # 末级 PP stage 的第一个 rank
_WORKERS = ["train/aa01", "train/aa02"]
# sglang_engine（聚焦修复批 #3）：SGLangEngine actor 在 broadcast 与 RDT 两种
# 传输模式下都创建并发 identity；sglang_server 只在 RDT 分支存在，broadcast
# 启动（launch.sh 当前模式）下把它设为必需角色会确定性假红。
_ROLES = ("driver", "megatron_train_actor", "rollout_manager", "sglang_engine")


def _leaf_digest(idx: int, ordinal: int) -> str:
    """代表性 per-leaf tape digest（64 hex；逐 leaf 唯一，fan-out 对调可检出）。"""
    return f"{idx:06x}{ordinal:02x}" * 8


def _wvs_entry(versions: list, total: int = 320) -> list | None:
    """把一个叶的行为版本列表铺成与之一致的 engine_spans 证据（V2 基线）。

    单入训轮、区间均分 ``total`` 个训练 token（= lp entry 的 num_tokens，
    区间覆盖与训练 token 数的交叉校验因此成立）；空版本列表返回 None
    （该叶无 spans 证据）。多版本时相邻区间版本天然不同（judge 相邻同
    版本校验不受触发）。
    """

    if not versions:
        return None
    n = len(versions)
    seg = max(total // n, 1)
    spans = []
    pos = 0
    for k, v in enumerate(versions):
        end = total if k == n - 1 else pos + seg
        spans.append({"version": str(v), "start": pos, "end": end})
        pos = end
    return [
        {
            "capture_record_id": "cap_t0",
            "provenance": "engine_spans",
            "spans": spans,
            "version": str(versions[-1]),
        }
    ]


def _selftest_write_events(ev_dir: Path, *, mutate: str = "") -> None:
    """生成与 miles rh2_event_log 生产 schema 同形的代表性事件文件。"""
    events: list[dict] = []

    def emit(kind: str, **fields):
        events.append({"event": kind, "ts_unix": 0.0, "host": "h", "pid": 1, "run_id": _RUN_ID, **fields})

    for role in _ROLES:
        digest = _TREE_DIGEST
        if mutate == "identity_mismatch" and role == "sglang_engine":
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
        # rollout 0 第 1 组的第一个 run 产生 2 个 fan-out 叶（同 sample_index、
        # leaf_ordinal 0/1、同 run reward、各自唯一 tape digest）。
        pc_iid = "django__django-11099" if rid == 0 else f"sympy__sympy-2059{rid}"
        group_specs = [
            (pc_iid, [1.0 if k % 4 == 0 else 0.0 for k in range(_GROUP_SIZE)]),
            ("astropy__astropy-14365", [1.0 if k % 2 == 0 else 0.0 for k in range(_GROUP_SIZE)]),
        ]
        if mutate == "pc_all_zero" and rid == 0:
            group_specs[0] = (pc_iid, [0.0] * _GROUP_SIZE)
        rollout_leaves: list[tuple[int, int]] = []  # (sample_index, leaf_ordinal)
        fanout_idx: int | None = None  # rollout 0 的多叶 run 的 sample_index
        for g, (iid, run_rewards) in enumerate(group_specs):
            run_indices = list(range(sample_seq, sample_seq + _GROUP_SIZE))
            sample_seq += _GROUP_SIZE
            leaves: list[tuple[int, int]] = []
            leaf_rewards: list[float] = []
            for k, idx in enumerate(run_indices):
                n_leaves = 1
                if rid == 0 and g == 1 and k == 0 and mutate != "no_fanout":
                    n_leaves = 2  # fan-out：同 run 两叶
                    fanout_idx = idx
                for o in range(n_leaves):
                    leaves.append((idx, o))
                    leaf_rewards.append(run_rewards[k])  # sibling 叶共享 run reward
            rollout_leaves.extend(leaves)
            behavior = [[str(version)] for _ in leaves]
            if mutate == "stale_behavior" and rid == 0 and g == 0:
                behavior = [["1", "3"] for _ in leaves]  # trainer current=version；行为列表末位≠current
            if mutate == "future_behavior_version" and rid == 0 and g == 0:
                behavior = [[str(version + 3)] for _ in leaves]  # 来自未来的版本 -> 负 staleness
            if mutate == "mixed_future_behavior" and rid == 0 and g == 0:
                # P0-8 反例：min 折叠会把 ["1","99"] 折成 1、staleness=0——future
                # turn 被隐藏。judge 必须逐项验证完整列表。
                behavior = [[str(version), "99"] for _ in leaves]
            if mutate == "nonnumeric_behavior_version" and rid == 0 and g == 0:
                # 数值+非数值混合：min 折叠会静默丢弃不可解析项。
                behavior = [[str(version), "corrupt"] for _ in leaves]
            if mutate == "missing_behavior_version" and rid == 0 and g == 0:
                behavior = [[] for _ in leaves]
            # V2 正向覆盖：基线必须真实出现"跨更新 turn 携带多区间证据"的
            # 样本（rid2/g1 组：turn 从 version-1 跨到 version；version-1 <
            # current，staleness=1 合法）——否则 spans 检查的多版本路径只被
            # 负例触达。
            if rid == 2 and g == 1:
                behavior = [[str(version - 1), str(version)] for _ in leaves]
            # V2 spans 证据基线：逐叶与 behavior 一致的 engine_spans 结构
            # （单轮、区间覆盖 320 训练 token = lp num_tokens）。
            spans_evidence = [_wvs_entry(b) for b in behavior]
            if rid == 1 and g == 0:
                if mutate == "span_understate":
                    # 低报反例（adv_miles）：引擎区间证据 v1+v2，记账只记末
                    # 版本 v2——staleness 用 min(behavior)=2 算出 0（静默低
                    # 报），只有 spans 一致性检查能抓红。
                    behavior = [["2"] for _ in leaves]
                    spans_evidence = [_wvs_entry(["1", "2"]) for _ in leaves]
                if mutate == "span_gap":
                    behavior = [["1", "2"] for _ in leaves]
                    spans_evidence = [[{
                        "capture_record_id": "cap_t0", "provenance": "engine_spans",
                        "spans": [{"version": "1", "start": 0, "end": 150},
                                  {"version": "2", "start": 170, "end": 320}],
                        "version": "2"}] for _ in leaves]
                if mutate == "span_overlap":
                    behavior = [["1", "2"] for _ in leaves]
                    spans_evidence = [[{
                        "capture_record_id": "cap_t0", "provenance": "engine_spans",
                        "spans": [{"version": "1", "start": 0, "end": 200},
                                  {"version": "2", "start": 150, "end": 320}],
                        "version": "2"}] for _ in leaves]
                if mutate == "span_out_of_bounds":
                    # 区间声明覆盖 500 token，而该叶训练 token（lp num_tokens）
                    # 只有 320——交叉校验必红（越界）。
                    behavior = [["2"] for _ in leaves]
                    spans_evidence = [[{
                        "capture_record_id": "cap_t0", "provenance": "engine_spans",
                        "spans": [{"version": "2", "start": 0, "end": 500}],
                        "version": "2"}] for _ in leaves]
            if mutate in ("spans_absent_with_update", "no_update_no_spans"):
                spans_evidence = [None for _ in leaves]
            tapes = [
                {"shape": [511, 48, 8], "dtype": "int32", "digest": _leaf_digest(i, o), "expected_rows": 511}
                for (i, o) in leaves
            ]
            if mutate == "bad_tape_shape" and rid == 0 and g == 0:
                tapes[0] = {"shape": [511, 47, 8], "dtype": "int32",
                            "digest": tapes[0]["digest"], "expected_rows": 511}
            emit("rollout_group", rollout_id=rid, group_index=g, instance_id=iid,
                 sample_indices=[i for i, _ in leaves],
                 leaf_ordinals=[o for _, o in leaves],
                 rewards=leaf_rewards,
                 behavior_versions=behavior,
                 weight_version_spans=spans_evidence,
                 statuses=["Status.COMPLETED"] * len(leaves),
                 response_lengths=[400] * len(leaves),
                 routing_tape=tapes)
        zero_var_indices = list(range(sample_seq, sample_seq + _GROUP_SIZE))
        sample_seq += _GROUP_SIZE
        emit("group_filtered", reason="zero_std_0.0", group_index=90 + rid,
             instance_id="psf__requests-2931", sample_indices=zero_var_indices,
             rewards=[0.0] * _GROUP_SIZE)
        if mutate == "zero_var_trained":
            # 零方差组混进训练批并被 applied step 消费：必须 FAIL。
            emit("rollout_group", rollout_id=rid, group_index=90 + rid, instance_id="psf__requests-2931",
                 sample_indices=zero_var_indices, leaf_ordinals=[0] * _GROUP_SIZE,
                 rewards=[0.0] * _GROUP_SIZE,
                 behavior_versions=[[str(version)]] * _GROUP_SIZE,
                 weight_version_spans=[_wvs_entry([str(version)])] * _GROUP_SIZE,
                 statuses=["Status.COMPLETED"] * _GROUP_SIZE, response_lengths=[400] * _GROUP_SIZE,
                 routing_tape=[
                     {"shape": [511, 48, 8], "dtype": "int32", "digest": _leaf_digest(i, 0), "expected_rows": 511}
                     for i in zero_var_indices
                 ])
            rollout_leaves.extend((i, 0) for i in zero_var_indices)

        lp_entries = []
        for pos, (i, o) in enumerate(rollout_leaves):
            mismatch = mutate == "logprob_length_mismatch_all"
            # codex 复核反例：Python 的 max 对 NaN 顺序敏感（max([0.01, nan])
            # == 0.01），尾部 NaN 会被静默掩掉——judge 必须逐条校验坏值。
            # 四种坏值形态各占一个 mutate：尾部 NaN（原始掩掉反例）、首位
            # NaN、+Inf、负数。NaN/Inf 经 write_jsonl 的 json.dumps 写成
            # NaN/Infinity 字面量，与生产 rh2_event_log.emit 的 wire 形态一致。
            first = rid == 0 and pos == 0
            last = rid == _N_ROLLOUTS - 1 and pos == len(rollout_leaves) - 1
            diff = 0.01
            if mutate == "logprob_diff_finite_then_nan" and last:
                diff = float("nan")
            elif mutate == "logprob_diff_nan_then_finite" and first:
                diff = float("nan")
            elif mutate == "logprob_diff_inf" and first:
                diff = float("inf")
            elif mutate == "logprob_diff_negative" and first:
                diff = -0.01
            lp_entries.append({"sample_index": i, "leaf_ordinal": o, "same_version": True,
                               "mean_abs_diff": diff,
                               "num_tokens": 320, "total_tokens": 400,
                               "length_mismatch": mismatch})
        if mutate == "logprob_partial_coverage":
            lp_entries = lp_entries[:1]
        emit("logprob_compare", rollout_id=rid, dp_rank=0, trainer_current_version=version,
             entries=lp_entries)

        # 逐样本 DIS token 记账（正控归因）：正控组样本 accepted>0；
        # pc_zero_accepted 时正控组归零、其余组保持正数（"其他组驱动更新"）。
        dis_entries = []
        for i, o in rollout_leaves:
            accepted = 120
            if mutate == "pc_zero_accepted" and rid == 0 and i < _GROUP_SIZE:
                accepted = 0
            dis_entries.append({"sample_index": i, "leaf_ordinal": o,
                                "accepted_tokens": accepted, "provenance_tokens": 320})
        emit("sample_dis_accounting", entries=dis_entries)

        # 2 个 optimizer step；dp0/dp1 各消费一半（leaf 粒度；rollout 0 因
        # fan-out 多 1 叶，step 0 取 ceil 半）。
        per_step = -(-len(rollout_leaves) // _STEPS_PER_ROLLOUT)
        step_shards: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for sid in range(_STEPS_PER_ROLLOUT):
            outcome, applied = "NORMAL", True
            if mutate in ("one_skipped_rollout", "all_skipped_but_update") and rid == 2:
                outcome, applied = "SKIPPED_ZERO_SIGNAL", False
            if mutate in ("normal_not_applied", "no_update_no_spans"):
                applied = False  # found-inf 型：NORMAL 但没有真实 optimizer.step()
                # no_update_no_spans（V2）：借同一"全场无 applied"形态制造
                # "无 mid-run 更新窗口"的 run——单版本记账的合法窗口正例。
            if mutate == "pc_not_applied" and rid == 0 and sid == 0:
                # 正控组所在 step 被跳过：方差在场但没有驱动更新。
                outcome, applied = "SKIPPED_ZERO_SIGNAL", False
            adam_b, sched_b = adam, sched
            if applied:
                adam += 1
                sched += 1 if mutate == "scheduler_wrong_increment" else _NUM_ROLLOUTS_PER_STEP
            if mutate == "counter_mismatch" and rid == 0 and sid == 0:
                adam = adam_b  # applied=True 但 Adam 计数没动：交叉验证必须 FAIL
            step_samples = rollout_leaves[sid * per_step:(sid + 1) * per_step]
            half = len(step_samples) // 2
            for dp_rank, shard in ((0, step_samples[:half]), (1, step_samples[half:])):
                shard = list(shard)
                if mutate == "consumed_missing_sample" and rid == 0 and sid == 0 and dp_rank == 0 and shard:
                    shard = shard[1:]
                if mutate == "consumed_extra_sample" and rid == 0 and sid == 0 and dp_rank == 0:
                    shard = [*shard, (9999, 0)]
                if mutate == "fanout_duplicate_consumed" and rid == 0 and fanout_idx is not None:
                    # 同一 leaf 消费两次：把多叶 run 的第 1 叶换成第 0 叶——
                    # 纯 index 口径下 multiset 不变（旧判定洗绿），leaf 口径必红。
                    shard = [((i, 0) if (i, o) == (fanout_idx, 1) else (i, o)) for (i, o) in shard]
                if mutate == "consumed_missing_rank" and rid == 0 and sid == 0 and dp_rank == 1:
                    continue
                step_shards[(sid, dp_rank)] = shard
                emit("train_step_consumed", rollout_id=rid, step_id=sid, dp_rank=dp_rank,
                     rank=dp_rank, sample_indices=[i for i, _ in shard],
                     leaf_ordinals=[o for _, o in shard],
                     num_tokens=500 * max(len(shard), 1),
                     num_microbatches=_MB_PER_STEP, attribution="micro_batch_indices")
                if mutate == "consumed_rank_conflict" and rid == 0 and sid == 0 and dp_rank == 0:
                    emit("train_step_consumed", rollout_id=rid, step_id=sid, dp_rank=dp_rank,
                         rank=dp_rank + 2, sample_indices=[i for i, _ in reversed(shard)][:1],
                         leaf_ordinals=[o for _, o in reversed(shard)][:1],
                         num_tokens=1, num_microbatches=_MB_PER_STEP, attribution="micro_batch_indices")
            for rank in range(_TRAIN_GLOBAL_RANKS):
                if mutate == "rank_missing_all_steps" and rank == _TRAIN_GLOBAL_RANKS - 1:
                    continue  # 该 rank 的全部 train_step 事件缺失（census 反例）
                accepted = 900.0 if outcome == "NORMAL" else 0.0
                rejected = 100.0 if outcome == "NORMAL" else 1000.0
                loss_val = 0.5 if outcome == "NORMAL" else 0.0
                grad_norm = 0.5 if applied else 0.0
                # 每步重建 optimizer 反例：单步内自洽（0->1、0->32）但跨 step
                # 断链——聚合面的 "+1 且前进" 判定会被洗绿。
                e_ab, e_aa, e_sb, e_sa = adam_b, adam, sched_b, sched
                if mutate == "optimizer_rebuilt":
                    e_ab, e_aa, e_sb, e_sa = (
                        (0, 1, 0, _NUM_ROLLOUTS_PER_STEP) if applied else (0, 0, 0, 0)
                    )
                if mutate == "nan_loss_grad" and applied:
                    grad_norm = float("nan")
                    loss_val = float("nan")
                is_pp_last = rank >= _PP_LAST_FIRST_RANK
                # 生产事实：loss_reduced 经 DP 组 all-reduce，**每个** pp-last
                # rank 都携带同一份 metrics（不再只发首 rank——那正是
                # "PP-last 指标未覆盖全 DP" 的反例形态，见 pp_last_metrics_missing_dp）。
                metrics = None
                if is_pp_last:
                    metrics = {"loss": loss_val,
                               "dis_accepted_tokens": accepted, "dis_rejected_tokens": rejected,
                               "dis_microbatch_provenance_tokens": accepted + rejected}
                    if mutate == "pp_last_metrics_missing_dp" and rank != _PP_LAST_FIRST_RANK:
                        metrics = None
                emit("train_step", rollout_id=rid, step_id=sid, attempt=0,
                     outcome=outcome, optimizer_step_applied=applied,
                     adam_step_before=e_ab, adam_step_after=e_aa,
                     scheduler_steps_before=e_sb, scheduler_steps_after=e_sa,
                     num_rollouts=_NUM_ROLLOUTS_PER_STEP,
                     grad_norm=grad_norm, duration_seconds=20.0,
                     zero_signal_scan_seconds=0.4,
                     rank=rank, dp_rank=rank % _DP_RANKS,
                     is_pp_last_stage=is_pp_last,
                     metrics=metrics)
                if mutate == "train_step_dup_rank" and rank == 0 and rid == 0 and sid == 0:
                    emit("train_step", rollout_id=rid, step_id=sid, attempt=0,
                         outcome=outcome, optimizer_step_applied=applied,
                         adam_step_before=e_ab, adam_step_after=e_aa,
                         scheduler_steps_before=e_sb, scheduler_steps_after=e_sa,
                         num_rollouts=_NUM_ROLLOUTS_PER_STEP,
                         grad_norm=grad_norm, duration_seconds=20.0,
                         zero_signal_scan_seconds=0.4,
                         rank=rank, dp_rank=rank % _DP_RANKS,
                         is_pp_last_stage=is_pp_last, metrics=metrics)
            if mutate == "train_step_extra_rank" and rid == 0 and sid == 0:
                emit("train_step", rollout_id=rid, step_id=sid, attempt=0,
                     outcome=outcome, optimizer_step_applied=applied,
                     adam_step_before=adam_b, adam_step_after=adam,
                     scheduler_steps_before=sched_b, scheduler_steps_after=sched,
                     num_rollouts=_NUM_ROLLOUTS_PER_STEP,
                     grad_norm=0.5 if applied else 0.0, duration_seconds=20.0,
                     zero_signal_scan_seconds=0.4,
                     rank=_TRAIN_GLOBAL_RANKS, dp_rank=_TRAIN_GLOBAL_RANKS % _DP_RANKS,
                     is_pp_last_stage=False, metrics=None)

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
            # fanout_tape_swap：两个 fan-out 叶的 tape 对调——digest multiset
            # 不变（旧 multiset 判定必然洗绿），leaf→digest 精确联结必红。
            digests = [
                _leaf_digest(
                    i,
                    (1 - o)
                    if (mutate == "fanout_tape_swap" and rid == 0 and i == fanout_idx)
                    else o,
                )
                for i, o in dp_samples
            ]
            if mutate == "replay_digest_mismatch" and rid == 0 and dp_rank == 0 and digests:
                digests[0] = "ff" * 32  # dp0 全部副本一致地偏离来源 tape（source 联结反例）
            if mutate == "replay_dp_digest_conflict" and rid == 0 and rank == 4 and digests:
                digests[0] = "ee" * 32  # 仅 rank4 与同 dp 副本（rank0/2）冲突
            emit("replay_fill", manager="routing", rollout_id=rid, rank=rank, dp_rank=dp_rank,
                 enabled=mutate != "replay_fill_disabled",
                 num_streams=16 if mutate != "replay_fill_disabled" else 0,
                 records_min=fill_records, records_max=fill_records,
                 expected_records=queue_len, num_samples=len(dp_samples),
                 sample_indices=[i for i, _ in dp_samples],
                 leaf_ordinals=[o for _, o in dp_samples],
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
            or mutate in ("normal_not_applied", "no_update_no_spans")
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
    if mutate == "strip_leaf_ordinals":
        # 旧 emitter/wire 形态：全部 leaf 身份字段缺失——judge 必须 MISSING
        # （INCOMPLETE），不得按纯 index 口径继续判绿。
        for e in events:
            e.pop("leaf_ordinals", None)
            if e["event"] == "replay_fill":
                e.pop("sample_indices", None)
            for entry in e.get("entries") or []:
                entry.pop("leaf_ordinal", None)

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
    # 聚焦修复批 #5：thresholds_sha256 缺失/空/非法必须 FAIL（不再"缺字段即跳过"）。
    manifest = {
        "run_id": _RUN_ID if mutate != "manifest_run_id_mismatch" else "another-run",
        "thresholds_sha256": hashlib.sha256((HERE / "thresholds.md").read_bytes()).hexdigest(),
    }
    if mutate == "manifest_missing_thresholds_sha":
        del manifest["thresholds_sha256"]
    elif mutate == "manifest_empty_thresholds_sha":
        manifest["thresholds_sha256"] = ""
    elif mutate == "manifest_bad_thresholds_sha":
        manifest["thresholds_sha256"] = "not-a-sha256"
    (ev_dir / "run_manifest.json").write_text(json.dumps(manifest))
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
        # V2：基线必须真实包含"跨更新 turn 多区间证据"的正向覆盖（rid2/g1），
        # 否则 spans 检查的多版本路径只被负例触达。
        base_spans_detail = {c["check"]: c["detail"] for c in v["checks"]}[
            "weight_version_spans_coverage"]
        check("其中 0 个样本" not in base_spans_detail,
              f"基线应包含跨更新多版本正例证据，got {base_spans_detail}")

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
        # --- V2：per-token weight version spans 覆盖/低报审计 -----------------
        # 核心负测试（adv_miles 反例）：引擎区间证据 v1+v2、记账只记 v2——
        # staleness 检查自身此时是**绿**的（min(behavior)=2、current=2、
        # staleness=0，低报静默），必须由 spans 一致性检查抓红。
        v = _run_judge(_selftest_evidence(tmp, mutate="span_understate"))
        check("weight_version_spans_coverage" in failed_checks(v),
              f"跨更新 turn 只记单版本（staleness 低报）应 FAIL spans 检查，got {failed_checks(v)}")
        check("staleness_max_versions" not in failed_checks(v),
              "低报形态下 staleness 检查按记账列表算是绿的——正是 spans 检查存在的理由；"
              f"若它红了说明本反例构造错位，got {failed_checks(v)}")
        check(v["overall"] != "PASS", f"低报 run 总判定不得 PASS，got {v['overall']}")
        for mutate in ("span_gap", "span_overlap", "span_out_of_bounds", "spans_absent_with_update"):
            v = _run_judge(_selftest_evidence(tmp, mutate=mutate))
            check("weight_version_spans_coverage" in failed_checks(v),
                  f"{mutate} 应 FAIL spans 检查，got {failed_checks(v)}")
            check(v["overall"] != "PASS", f"{mutate} 总判定不得 PASS，got {v['overall']}")
        # 正例：无 mid-run 更新窗口的 run，single_version_only（无 spans 证据）
        # 合法——spans 检查必须 PASS（其余检查如 applied 步数按各自语义红）。
        v = _run_judge(_selftest_evidence(tmp, mutate="no_update_no_spans"))
        spans_status = {c["check"]: c["status"] for c in v["checks"]}.get(
            "weight_version_spans_coverage")
        check(spans_status == PASS,
              f"无 mid-run 更新窗口时单版本记账（无 spans 证据）应 PASS spans 检查，got {spans_status}")
        v = _run_judge(_selftest_evidence(tmp, mutate="logprob_length_mismatch_all"))
        check("logprob_alignment_and_coverage" in failed_checks(v),
              f"全部长度错位应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="logprob_partial_coverage"))
        check("logprob_alignment_and_coverage" in failed_checks(v),
              f"对拍只剩一条应 FAIL 覆盖，got {failed_checks(v)}")
        # --- codex 复核：max 的 NaN 顺序敏感性不得掩掉坏对拍值 ----------------
        for mutate in ("logprob_diff_finite_then_nan", "logprob_diff_nan_then_finite",
                       "logprob_diff_inf", "logprob_diff_negative"):
            v = _run_judge(_selftest_evidence(tmp, mutate=mutate))
            check("logprob_same_version_mean_abs_diff_max" in failed_checks(v),
                  f"{mutate} 应 FAIL 对拍上限项（坏值不得被 max 掩掉），got {failed_checks(v)}")
            check(v["overall"] != "PASS", f"{mutate} 总判定不得 PASS，got {v['overall']}")
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

        # --- 聚焦修复批 #1：leaf 唯一身份（假红与假绿双向反例）----------------
        # 好例已含一个双叶 fan-out run：两个合法叶不再被判"重复消费"（假红
        # 消除由好例 PASS 证明）；以下钉住假绿面。
        v = _run_judge(_selftest_evidence(tmp, mutate="fanout_tape_swap"))
        check("routing_replay_source_linkage" in failed_checks(v),
              f"fan-out 两叶 tape 对调（digest multiset 不变）应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="fanout_duplicate_consumed"))
        check("queue_multiset_conservation" in failed_checks(v),
              f"同一 leaf 消费两次（纯 index multiset 不变）应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="no_fanout"))
        check("g1_fanout_multileaf_coverage" in failed_checks(v),
              f"全线性数据应 FAIL fan-out 多叶覆盖，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="strip_leaf_ordinals"))
        check(v["overall"] == "INCOMPLETE",
              f"leaf 身份字段全缺（旧 emitter）应 INCOMPLETE，得 {v['overall']}")
        check(any(c["check"] == "leaf_identity" and c["status"] == MISSING for c in v["checks"]),
              "leaf 身份字段全缺时 leaf_identity 应记 MISSING")

        # --- 聚焦修复批 #2：trainer per-rank oracle（三个已复现假绿反例）------
        v = _run_judge(_selftest_evidence(tmp, mutate="rank_missing_all_steps"))
        check("train_step_global_rank_census" in failed_checks(v),
              f"删除 rank5 全部 train_step（保留 replay/consume）应 FAIL census，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="train_step_extra_rank"))
        check("train_step_global_rank_census" in failed_checks(v),
              f"census 之外的额外 rank 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="train_step_dup_rank"))
        check("collect_consistency" in failed_checks(v),
              f"同 (r,s,attempt,rank) 重复发射应 FAIL collect_consistency，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="optimizer_rebuilt"))
        check("optimizer_state_continuity_per_rank" in failed_checks(v),
              f"每步 Adam 0->1/scheduler 0->32（每步重建 optimizer）应 FAIL 跨 step 链，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="scheduler_wrong_increment"))
        check("optimizer_state_continuity_per_rank" in failed_checks(v),
              f"scheduler 步进 != num_rollouts 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="nan_loss_grad"))
        check("train_step_metrics_coverage" in failed_checks(v),
              f"applied step 的 loss/grad_norm=NaN 应 FAIL，got {failed_checks(v)}")
        v = _run_judge(_selftest_evidence(tmp, mutate="pp_last_metrics_missing_dp"))
        check("train_step_metrics_coverage" in failed_checks(v),
              f"pp-last 指标只覆盖 dp0 应 FAIL（不得只取第一条 metrics），got {failed_checks(v)}")

        # --- 聚焦修复批 #5：manifest thresholds digest 缺失/空/非法不得 PASS --
        for mutate in (
            "manifest_missing_thresholds_sha",
            "manifest_empty_thresholds_sha",
            "manifest_bad_thresholds_sha",
        ):
            v = _run_judge(_selftest_evidence(tmp, mutate=mutate))
            check("run_identity" in failed_checks(v),
                  f"{mutate} 应 FAIL run_identity，got {failed_checks(v)}")

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
        "SELF-TEST PASS（代表性事件 collect->judge 全链好例 PASS（含双叶 fan-out run）；"
        "11 类事件删除均 INCOMPLETE；租前审查 P0-1/3/4/5/6/8 全部假绿反例命中对应 FAIL；"
        "B2 oracle 坏例保持命中；聚焦复核 3 个残余 P0 反例——replay rank census/同 DP 副本"
        "冲突、bootstrap 唯一+trainer current 锚定、逐 turn 版本逐项验证——全部命中 FAIL；"
        "租前聚焦修复批反例——leaf 身份（tape 对调/同 leaf 重复消费/全线性冒充 fan-out 覆盖/"
        "身份字段缺失 INCOMPLETE）、trainer per-rank oracle（rank 缺失/额外/重复、每步重建 "
        "optimizer、scheduler 步进不精确、NaN loss/grad_norm、pp-last 指标未覆盖全 DP）、"
        "manifest thresholds digest 缺失/空/非法——全部命中；"
        "V2 weight-version spans 反例——跨更新 turn 只记单版本（staleness 自身绿时低报必由 "
        "spans 一致性抓红）、区间缝隙/重叠/越界、有更新窗口的 run 无 spans 证据——全部命中 "
        "FAIL，无更新窗口的 single_version_only 正例 PASS，基线含跨更新多区间正向覆盖）"
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
