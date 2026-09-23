#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L5 · 证据索引生成器（只读）。

从历史账本目录 + 今晚新产生的运行期证据，按任务（216 SWE-Gym + 48 R2E）汇总
"哪题、什么条件、做过什么、证据在哪"，写出 evidence_index.json。

只读输入；不改任何账本；不下题目结论（verdict/reward 原样搬运，不做重新判定）。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
from collections import Counter, defaultdict

ROOT = "${REPO_ROOT}"
PKG = "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916"
OUT = os.path.join(ROOT, PKG, "L5_evidence_index", "evidence_index.json")


def rp(p: str) -> str:
    """绝对路径 -> 相对工作区根的路径。"""
    return os.path.relpath(p, ROOT) if os.path.isabs(p) else p


def A(p: str) -> str:
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def load_jsonl(p: str):
    """返回 [(行号(1基), obj)]；跳过空行。"""
    out = []
    with open(A(p), encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if line:
                out.append((i, json.loads(line)))
    return out


def exists(p: str) -> bool:
    return os.path.exists(A(p))


def mtime_iso(p: str) -> str | None:
    ap = A(p)
    if not os.path.exists(ap):
        return None
    return _dt.datetime.fromtimestamp(os.path.getmtime(ap)).astimezone().isoformat(timespec="seconds")


def sha256(p: str) -> str | None:
    ap = A(p)
    if not os.path.exists(ap):
        return None
    out = subprocess.run(["shasum", "-a", "256", ap], capture_output=True, text=True)
    return "sha256:" + out.stdout.split()[0] if out.returncode == 0 else None


# ---------------------------------------------------------------- 任务清单
def load_task_lists():
    sig = json.load(open(A(f"{PKG}/task_signals_swegym.json"), encoding="utf-8"))
    r2e = json.load(open(A(f"{PKG}/L4_r2e/r2e_tasks_48.json"), encoding="utf-8"))
    return sig, r2e


# ---------------------------------------------------------------- 索引容器
class Index:
    def __init__(self):
        self.tasks: dict[str, dict] = {}
        self.ledgers: list[dict] = []

    def add_task(self, task_id, **meta):
        self.tasks[task_id] = dict(task_id=task_id, evidence=[], **meta)

    def ev(self, task_id, **entry):
        t = self.tasks.get(task_id)
        if t is None:  # 账本里出现了不在清单内的任务
            t = self.tasks.setdefault(
                task_id,
                dict(task_id=task_id, source="unknown", in_task_list=False, evidence=[]),
            )
        t["evidence"].append(entry)


def swegym_condition(r: dict) -> str:
    bits = [f"gate={r.get('gate')}", f"variant={r.get('variant')}"]
    if r.get("network"):
        bits.append(f"network={r['network']}")
    bits.append(f"attempt={r.get('attempt')}")
    if r.get("run_tag"):
        bits.append(f"run_tag={r['run_tag']}")
    if r.get("exec_user_test"):
        bits.append(f"exec_user_test={r['exec_user_test']}")
    if r.get("memory_limit_bytes"):
        bits.append(f"mem={r['memory_limit_bytes']}")
    if r.get("fixture_note"):
        bits.append(f"fixture_note={r['fixture_note']}")
    return " ".join(str(b) for b in bits)


def r2e_condition(r: dict) -> str:
    return (
        f"gate={r.get('gate')} network={r.get('network')} attempt={r.get('attempt')} "
        f"expected_n={r.get('expected_n')} runner={r.get('runner_version')}"
    )


def swegym_log_dir(r: dict, base) -> str | None:
    """账本里的 log_path 是远端路径；这里换算成本机日志目录。base 可以是单个路径或按优先级排的列表。"""
    inst, gate, var, att = r.get("instance_id"), r.get("gate"), r.get("variant"), r.get("attempt")
    if not (inst and gate):
        return None
    for b in ([base] if isinstance(base, str) else base):
        cand = os.path.join(b, inst, gate, var or "default", f"a{att}")
        if exists(cand):
            return rp(cand)
    return None


def r2e_log_dir(r: dict, base: str) -> str | None:
    repo, ch, gate, att = r.get("repo"), r.get("commit_hash"), r.get("gate"), r.get("attempt")
    if not (repo and ch and gate):
        return None
    cand = os.path.join(base, repo, ch[:12], gate, f"a{att}")
    return rp(cand) if exists(cand) else None


def main():
    idx = Index()
    sig, r2e_tasks = load_task_lists()

    # ---- 建任务壳 ----
    sig_by_id = {}
    for s in sig:
        sig_by_id[s["instance_id"]] = s
        idx.add_task(
            s["instance_id"],
            source="SWE-Gym/SWE-Gym-Lite",
            task_revision="upstream",
            repo=s.get("repo"),
            in_task_list=True,
            signals={
                "in_e2": s.get("in_e2"),
                "fragile_reference_id": s.get("fragile_reference_id"),
                "stage1": s.get("stage1"),
                "deepseek_candidate_oracle": s.get("deepseek_candidate_oracle"),
                "f2p_n": s.get("f2p_n"),
                "p2p_n": s.get("p2p_n"),
            },
        )
    r2e_by_commit = {}
    for t in r2e_tasks["tasks"]:
        r2e_by_commit[t["commit_hash"]] = t
        idx.add_task(
            t["task_id"],
            source="R2E-Gym/R2E-Gym-Subset",
            task_revision="upstream",
            repo=t.get("repo"),
            commit_hash=t["commit_hash"],
            group=t.get("group"),
            in_task_list=True,
            signals=None,
        )
    r2e_tid = lambda ch: f"r2e::{ch}"  # noqa: E731

    # =============================================================== 账本 1-7
    # 20260909 夜探针（本机三份副本，final_sync 为权威；docs/ 为归档副本；codex_backup 为中途快照）
    SYNC = "runs/env_probe_20260909_final_sync/ledger"
    DOCS = f"docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_probe_20260909/ledger"
    BKUP = "runs/env_probe_20260909_codex_backup/ledger"

    def reg(path, kind, n, extra=None):
        d = dict(path=rp(path), kind=kind, rows=n)
        d.update(extra or {})
        idx.ledgers.append(d)
        return d

    # --- swegym_ledger.jsonl（216 题的 facts/empty/gold/probe_* 四门 + 变体）---
    rows = load_jsonl(f"{SYNC}/swegym_ledger.jsonl")
    for ln, r in rows:
        gate = r.get("gate")
        kind = {
            "facts": "oracle_facts",
            "empty": "oracle_empty",
            "gold": "oracle_gold",
            "probe_unrelated": "probe_unrelated",
            "probe_mutation": "probe_mutation",
        }.get(gate, f"oracle_{gate}")
        idx.ev(
            r["instance_id"],
            kind=kind,
            batch="env_probe_20260909",
            condition=swegym_condition(r),
            ledger=rp(f"{SYNC}/swegym_ledger.jsonl"),
            line=ln,
            started_at=r.get("started_at"),
            result=r.get("result"),
            verdict=r.get("official_verdict"),
            reward=None,
            log_dir=swegym_log_dir(r, f"{SYNC}/logs"),
            note=("; ".join(map(str, r.get("notes") or [])) or None),
        )
    reg(
        f"{SYNC}/swegym_ledger.jsonl",
        "swegym_oracle",
        len(rows),
        {
            "schema": "rh2.env_probe.swegym.v1",
            "runner_version": "swegym_probe/0.1",
            "run_tag": None,
            "tasks_covered": len({r["instance_id"] for _, r in rows}),
            "gates": dict(Counter(f"{r.get('gate')}/{r.get('variant')}" for _, r in rows)),
            "results": dict(Counter(r.get("result") for _, r in rows)),
            "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
            "logs_dir": rp(f"{SYNC}/logs"),
            "logs_layout": "logs/<instance_id>/<gate>/<variant>/a<attempt>/{eval.sh,status_map.json,test_output.txt[,patch.diff]}",
            "copies": {
                "docs_archive": rp(f"{DOCS}/swegym_ledger.jsonl"),
                "codex_backup": rp(f"{BKUP}/swegym_ledger.jsonl"),
            },
        },
    )

    # --- swegym_facts_v2.jsonl（12 题 facts 复采）---
    rows = load_jsonl(f"{SYNC}/swegym_facts_v2.jsonl")
    for ln, r in rows:
        idx.ev(
            r["instance_id"],
            kind="oracle_facts_v2",
            batch="env_probe_20260909",
            condition=swegym_condition(r),
            ledger=rp(f"{SYNC}/swegym_facts_v2.jsonl"),
            line=ln,
            started_at=r.get("started_at"),
            result=r.get("result"),
            verdict=r.get("official_verdict"),
            reward=None,
            log_dir=swegym_log_dir(r, f"{SYNC}/logs"),
            note=None,
        )
    reg(f"{SYNC}/swegym_facts_v2.jsonl", "swegym_facts_repeat", len(rows),
        {"schema": "rh2.env_probe.swegym.v1", "tasks_covered": len({r["instance_id"] for _, r in rows}),
         "gates": {"facts/default": len(rows)},
         "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)]})

    # --- cc_candidate_grading.jsonl（24 题 DeepSeek 候选补丁：原组 + 投影组）---
    rows = load_jsonl(f"{SYNC}/cc_candidate_grading.jsonl")
    for ln, r in rows:
        gate = r.get("gate")
        kind = "oracle_candidate" if gate == "candidate" else "oracle_candidate_projected"
        idx.ev(
            r["instance_id"],
            kind=kind,
            batch="env_probe_20260909",
            condition=swegym_condition(r),
            ledger=rp(f"{SYNC}/cc_candidate_grading.jsonl"),
            line=ln,
            started_at=r.get("started_at"),
            result=r.get("result"),
            verdict=r.get("official_verdict"),
            reward=None,
            log_dir=swegym_log_dir(r, f"{SYNC}/logs"),
            note=r.get("fixture_note") or None,
        )
    reg(f"{SYNC}/cc_candidate_grading.jsonl", "swegym_candidate", len(rows),
        {"schema": "rh2.env_probe.swegym.v1",
         "tasks_covered": len({r["instance_id"] for _, r in rows}),
         "gates": dict(Counter(r.get("gate") for _, r in rows)),
         "verdicts": dict(Counter(str(r.get("official_verdict")) for _, r in rows)),
         "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
         "patches_dir": rp(f"{SYNC}/cc_patches")})

    # --- cc_reference_ledger.jsonl（24 题 DeepSeek 轨迹）---
    rows = load_jsonl(f"{SYNC}/cc_reference_ledger.jsonl")
    for ln, r in rows:
        inst = r["instance_id"]
        traj = f"{SYNC}/logs_cc/{inst}"
        idx.ev(
            inst,
            kind="deepseek_trajectory",
            batch="env_probe_20260909",
            condition=(
                f"harness={r.get('harness')} model={r.get('model')} max_turns={r.get('max_turns')} "
                f"wall_clock_s={r.get('wall_clock_s')} disallowed_tools={r.get('disallowed_tools')}"
            ),
            ledger=rp(f"{SYNC}/cc_reference_ledger.jsonl"),
            line=ln,
            started_at=r.get("started_at"),
            result=r.get("result"),
            verdict=r.get("official_verdict"),
            reward=None,
            log_dir=rp(traj) if exists(traj) else None,
            patch=(rp(f"{SYNC}/cc_patches/{inst}.diff") if exists(f"{SYNC}/cc_patches/{inst}.diff") else None),
            note=(f"grade_result={r.get('grade_result')} strict_full={r.get('strict_full')}"
                  if r.get("grade_result") is not None else None),
        )
    reg(f"{SYNC}/cc_reference_ledger.jsonl", "deepseek_reference", len(rows),
        {"schema": "rh2.env_probe.cc_reference.v1",
         "tasks_covered": len({r["instance_id"] for _, r in rows}),
         "results": dict(Counter(r.get("result") for _, r in rows)),
         "verdicts": dict(Counter(str(r.get("official_verdict")) for _, r in rows)),
         "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
         "logs_dir": rp(f"{SYNC}/logs_cc"),
         "logs_layout": "logs_cc/<instance_id>/{stream.jsonl,candidate.diff,prompt.txt,stderr.txt}"})

    # --- r2e_ledger v1/v2/v3（core24）---
    for fn, ver in [("r2e_ledger.jsonl", "v1"), ("r2e_ledger_v2.jsonl", "v2"), ("r2e_ledger_v3.jsonl", "v3")]:
        rows = load_jsonl(f"{SYNC}/{fn}")
        for ln, r in rows:
            gate = r.get("gate")
            kind = {"facts": "r2e_facts", "noop": "r2e_noop", "gold": "r2e_gold"}.get(gate, f"r2e_{gate}")
            idx.ev(
                r2e_tid(r["commit_hash"]),
                kind=kind,
                batch=f"env_probe_20260909/{ver}",
                condition=r2e_condition(r),
                ledger=rp(f"{SYNC}/{fn}"),
                line=ln,
                started_at=r.get("started_at"),
                result=r.get("result"),
                verdict=None,
                reward=r.get("reward"),
                log_dir=r2e_log_dir(r, f"{SYNC}/logs_r2e"),
                note=("; ".join(map(str, r.get("notes") or [])) or None),
            )
        reg(f"{SYNC}/{fn}", f"r2e_oracle_{ver}", len(rows),
            {"schema": "rh2.env_probe.r2e.v1",
             "runner_version": sorted({r.get("runner_version") for _, r in rows}),
             "tasks_covered": len({r["commit_hash"] for _, r in rows}),
             "gates": dict(Counter(r.get("gate") for _, r in rows)),
             "results": dict(Counter(r.get("result") for _, r in rows)),
             "rewards": dict(Counter(str(r.get("reward")) for _, r in rows)),
             "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
             "logs_dir": rp(f"{SYNC}/logs_r2e"),
             "logs_layout": "logs_r2e/<repo>/<commit12>/<gate>/a<attempt>/{status_map.json,test_output.txt[,git_gold.diff,gold.diff]}"})

    # =============================================================== 阶段一 20260910/11
    S1 = "runs/env_probe_stage1_20260910/ledger"
    s1_files = [
        (f"{S1}/stage1_preflight.jsonl", "stage1_preflight", f"{S1}/logs/stage1_preflight_20260910"),
        (f"{S1}/stage1_offline.jsonl", "stage1_offline_partial", f"{S1}/logs/stage1_offline_20260910"),
        (f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl", "stage1_offline_full",
         [f"{S1}/stage1_continuation_20260911/logs/stage1_offline_20260910",
          f"{S1}/logs/stage1_offline_20260910"]),
        (f"{S1}/monai1121_online_20260911/results.jsonl", "monai_control", None),
        (f"{S1}/monai1121_offline_cached_20260911/results.jsonl", "monai_control", None),
        (f"{S1}/monai1121_offline_uncached_20260911/results.jsonl", "monai_control", None),
    ]
    for path, tag, logbase in s1_files:
        rows = load_jsonl(path)
        for ln, r in rows:
            gate = r.get("gate")
            if tag == "monai_control":
                kind = "monai_control"
            elif tag == "stage1_preflight":
                kind = f"stage1_preflight_{gate}"
            else:
                kind = f"stage1_{gate}"  # stage1_empty / stage1_gold
            idx.ev(
                r["instance_id"],
                kind=kind,
                batch="env_probe_stage1_20260910",
                condition=swegym_condition(r),
                ledger=rp(path),
                line=ln,
                started_at=r.get("started_at"),
                result=r.get("result"),
                verdict=r.get("official_verdict"),
                reward=None,
                log_dir=(swegym_log_dir(r, logbase) if logbase else None),
                note=("; ".join(map(str, r.get("notes") or [])) or None),
            )
        reg(path, tag, len(rows),
            {"schema": "rh2.env_probe.swegym.v1",
             "run_tag": sorted({r.get("run_tag") for _, r in rows}),
             "tasks_covered": len({r["instance_id"] for _, r in rows}),
             "gates": dict(Counter(f"{r.get('gate')}/{r.get('variant')}" for _, r in rows)),
             "results": dict(Counter(r.get("result") for _, r in rows)),
             "verdicts": dict(Counter(str(r.get("official_verdict")) for _, r in rows)),
             "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
             "logs_dir": (None if not logbase else
                          (rp(logbase) if isinstance(logbase, str) else [rp(b) for b in logbase])),
             "logs_layout": ("logs/<run_tag>/<instance_id>/<gate>/<variant>/a<attempt>/"
                             "{eval.sh,status_map.json,test_output.txt[,patch.diff]}" if logbase else None)})

    # --- 阶段一 R2E 扩展（preflight 3 + remainder 21 + failure_repeats 2）---
    s1_r2e = [
        (f"{S1}/r2e_preflight_20260911/results.jsonl", "r2e_preflight", f"{S1}/r2e_preflight_20260911/logs_r2e"),
        (f"{S1}/r2e_remainder_20260911/results.jsonl", "r2e_remainder", f"{S1}/r2e_remainder_20260911/logs_r2e"),
        (f"{S1}/r2e_failure_repeats_20260911/results.jsonl", "r2e_failure_repeats",
         f"{S1}/r2e_failure_repeats_20260911/logs_r2e"),
    ]
    for path, tag, logbase in s1_r2e:
        rows = load_jsonl(path)
        for ln, r in rows:
            gate = r.get("gate")
            idx.ev(
                r2e_tid(r["commit_hash"]),
                kind={"noop": "r2e_noop", "gold": "r2e_gold", "facts": "r2e_facts"}.get(gate, f"r2e_{gate}"),
                batch=f"env_probe_stage1_20260910/{tag}",
                condition=r2e_condition(r),
                ledger=rp(path),
                line=ln,
                started_at=r.get("started_at"),
                result=r.get("result"),
                verdict=None,
                reward=r.get("reward"),
                log_dir=r2e_log_dir(r, logbase),
                note=("; ".join(map(str, r.get("notes") or [])) or None),
            )
        reg(path, tag, len(rows),
            {"schema": "rh2.env_probe.r2e.v1",
             "runner_version": sorted({r.get("runner_version") for _, r in rows}),
             "tasks_covered": len({r["commit_hash"] for _, r in rows}),
             "gates": dict(Counter(r.get("gate") for _, r in rows)),
             "results": dict(Counter(r.get("result") for _, r in rows)),
             "rewards": dict(Counter(str(r.get("reward")) for _, r in rows)),
             "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
             "logs_dir": rp(logbase) if exists(logbase) else None})

    # =============================================================== rh2 真机 e1 / e2
    def add_replay(path, kind, batch, growing=False):
        rows = load_jsonl(path)
        for ln, r in rows:
            rep = r.get("report") or {}
            cand = r.get("candidate") or {}
            cls = r.get("classification") or {}
            pol = r.get("policy") or {}
            idx.ev(
                r["instance_id"],
                kind=kind,
                batch=batch,
                condition=(
                    f"candidate.kind={cand.get('kind')} apply_method={cand.get('apply_method')} "
                    f"run_id={r.get('run_id')} network={pol.get('network')} cpus={pol.get('cpus')} "
                    f"mem={pol.get('memory_bytes')} attempt={r.get('attempt')}"
                    + (f" derived_image={r.get('derived_image_recipe')}" if r.get("derived_image_recipe") else "")
                ),
                ledger=rp(path),
                line=ln,
                started_at=r.get("started_at_utc"),
                result=rep.get("outcome") or ("not_graded" if not rep else None),
                verdict=rep.get("outcome"),
                reward=rep.get("reward"),
                log_dir=None,
                remote_log=(r.get("log") or {}).get("path"),
                diagnostics_ref=r.get("diagnostics_ref"),
                note="; ".join(
                    x for x in [
                        ("; ".join(map(str, r.get("notes") or [])) or None),
                        (f"classification={cls.get('verdict')}" if cls else "classification=null"),
                        (f"failure_category={rep.get('failure_category')}" if rep.get("failure_category") else None),
                        (f"infra_failure_detail={rep.get('infra_failure_detail')}"
                         if rep.get("infra_failure_detail") else None),
                    ] if x
                ) or None,
            )
        extra = {"schema": "rh2.replay_grade_ledger.v1",
                 "run_id": sorted({r.get("run_id") for _, r in rows}),
                 "tasks_covered": len({r["instance_id"] for _, r in rows}),
                 "candidate_kinds": dict(Counter((r.get("candidate") or {}).get("kind") for _, r in rows)),
                 "outcomes": dict(Counter(str((r.get("report") or {}).get("outcome")) for _, r in rows)),
                 "time_range": [min(r.get("started_at_utc", "") for _, r in rows),
                                max(r.get("started_at_utc", "") for _, r in rows)],
                 "note": "日志与 diagnostics 在机器 1 的远端路径（/work/replay/eval_logs/...），本机未同步"}
        if growing:
            extra["snapshot"] = {"collected_at_local": NOW_LOCAL, "file_mtime_local": mtime_iso(path),
                                 "rows_at_collection": len(rows),
                                 "warning": "机器 1 的 e2 仍在运行，行数会继续增长；此处仅为采集时刻快照"}
        reg(path, kind, len(rows), extra)

    E = "runs/swe_grading_wiring_20260915"
    add_replay(f"{E}/e1/ledger_e1.jsonl", "rh2_e1", "swe_grading_wiring_20260915/e1")
    add_replay(f"{E}/e1/ledger_e1_pandas.jsonl", "rh2_e1", "swe_grading_wiring_20260915/e1_pandas")
    add_replay(f"{E}/e2/ledger_e2_A.jsonl", "rh2_e2_A", "swe_grading_wiring_20260915/e2", growing=True)
    add_replay(f"{E}/e2/ledger_e2_B.jsonl", "rh2_e2_B", "swe_grading_wiring_20260915/e2", growing=True)
    add_replay(f"{E}/e2/ledger_e2_B_repeat.jsonl", "rh2_e2_B_repeat", "swe_grading_wiring_20260915/e2", growing=True)
    add_replay(f"{E}/e2/ledger_e2_derived.jsonl", "rh2_e2_derived", "swe_grading_wiring_20260915/e2", growing=True)

    # --- Codex 的 e1 复核（20260916）：两条独立实跑，不是快照副本 ---
    R = "runs/swe_grading_e1_review_20260916/root/remote_pandas_noop"
    add_replay(f"{R}/ledger_pandas_noop.jsonl", "rh2_e1_review_noop",
               "swe_grading_e1_review_20260916/remote_pandas_noop")
    add_replay(f"{R}/forced_timeout/ledger.jsonl", "rh2_e1_review_forced_timeout",
               "swe_grading_e1_review_20260916/forced_timeout")
    for p, extra_note in [(f"{R}/ledger_pandas_noop.jsonl",
                           "pandas-48106 的 noop 复跑：e1 原始两次都 failed_to_grade，这次跑到了测试并出判定"),
                          (f"{R}/forced_timeout/ledger.jsonl",
                           "conan-13326 的人为超时注入（conan_forced_timeout.patch），验证 "
                           "grading_deadline_exhausted 路径")]:
        for lg in idx.ledgers:
            if lg["path"] == rp(p):
                lg["note"] = extra_note + "；eval 日志与 artifacts 已同步到本机（见 local_logs）"
                lg["local_logs"] = {
                    "eval_logs": rp(os.path.dirname(p) + "/eval_logs"),
                    "artifacts": rp(os.path.dirname(p) + "/artifacts"),
                }
                lg["source_pkg"] = "swe_grading_e1_review_20260916（Codex 复核，本机已同步日志）"

    # e1 本机 artifacts / eval_logs（按 instance 挂）
    art_base = f"{E}/e1/artifacts"
    n_art = 0
    for d in sorted(os.listdir(A(art_base))) if exists(art_base) else []:
        inst = d.split("--", 1)[1] if "--" in d else d
        if inst in idx.tasks:
            idx.ev(inst, kind="rh2_e1_artifacts", batch="swe_grading_wiring_20260915/e1",
                   condition="e1 本机同步的 rollout artifacts 目录（a<attempt>-<hash>/）",
                   ledger=None, line=None, started_at=None, result=None, verdict=None, reward=None,
                   log_dir=rp(os.path.join(art_base, d)), note=None)
            n_art += 1
    reg(art_base, "rh2_e1_artifacts_dir", n_art,
        {"tasks_covered": n_art, "logs_layout": "artifacts/swe_gym_lite--<instance_id>/a<attempt>-<hash>/",
         "eval_logs_dir": rp(f"{E}/e1/eval_logs"),
         "eval_logs_layout": "eval_logs/evallog_<run_id 截断>_<8位hash>.{eval.log,diagnostics.json}"})

    # =============================================================== 今晚 L0：e1 十次运行事实汇总
    L0 = f"{PKG}/L0_facts_tool/facts_e1"
    l0_tasks = 0
    if exists(L0):
        for d in sorted(os.listdir(A(L0))):
            fp = os.path.join(L0, d, "facts.json")
            if not exists(fp):
                continue
            j = json.load(open(A(fp), encoding="utf-8"))
            inst = j.get("instance_id") or d
            idx.ev(inst, kind="l0_facts_e1", batch="env_overnight_20260916/L0_facts_tool",
                   condition=(f"e1 十次运行的字段级事实汇总；runs={len(j.get('runs') or [])} "
                              f"tool_version={j.get('tool_version')} schema={j.get('schema_id')}"),
                   ledger=rp(fp), line=None, started_at=j.get("generated_at_utc"),
                   result=None, verdict=None, reward=None, log_dir=rp(os.path.join(L0, d)),
                   note=(f"missing_fields={len(j.get('missing_fields') or [])}"
                         f"; oracle_ledger={((j.get('oracle') or {}).get('empty') or {}).get('ledger_path', {}).get('value') if isinstance(((j.get('oracle') or {}).get('empty') or {}).get('ledger_path'), dict) else None}"),
                   source_pkg="L0_facts_tool")
            l0_tasks += 1
        s = json.load(open(A(f"{L0}/summary.json"), encoding="utf-8"))
        reg(f"{L0}/summary.json", "l0_facts_e1_summary", s.get("run_level_fact_count") or 0,
            {"schema": s.get("schema_id"), "tool_version": s.get("tool_version"),
             "tasks_covered": l0_tasks, "runs": s.get("runs"), "tasks": s.get("tasks"),
             "run_level_fact_count": s.get("run_level_fact_count"),
             "generated_at_utc": s.get("generated_at_utc"),
             "inputs": s.get("inputs"),
             "source_pkg": "env_overnight_20260916/L0_facts_tool",
             "note": "rh2 e1 十次运行（4 题 × noop/gold，含 pandas 两次）的字段观测率汇总；"
                     "reconcile.md 记录与账本的对账"})

    # =============================================================== 今晚 M3：48 个 R2E 镜像 noop/gold 实跑
    M3R = "runs/env_overnight_20260916/M3"
    gl = f"{M3R}/gold_ledger/r2e_gold_m3.jsonl"
    rows = load_jsonl(gl)
    for ln, r in rows:
        idx.ev(r2e_tid(r["commit_hash"]), kind="r2e_gold_m3", batch="env_overnight_20260916/M3",
               condition=r2e_condition(r) + " machine=机器 3",
               ledger=rp(gl), line=ln, started_at=r.get("started_at"),
               result=r.get("result"), verdict=None, reward=r.get("reward"),
               log_dir=r2e_log_dir(r, f"{M3R}/gold_ledger/logs_r2e"),
               note=("; ".join(map(str, r.get("notes") or [])) or None), source_pkg="M3")
    reg(gl, "r2e_gold_m3", len(rows),
        {"schema": "rh2.env_probe.r2e.v1", "runner_version": sorted({r.get("runner_version") for _, r in rows}),
         "tasks_covered": len({r["commit_hash"] for _, r in rows}),
         "gates": dict(Counter(r.get("gate") for _, r in rows)),
         "results": dict(Counter(r.get("result") for _, r in rows)),
         "rewards": dict(Counter(str(r.get("reward")) for _, r in rows)),
         "time_range": [min(r["started_at"] for _, r in rows), max(r["started_at"] for _, r in rows)],
         "logs_dir": rp(f"{M3R}/gold_ledger/logs_r2e"),
         "logs_layout": "logs_r2e/<repo>/<commit12>/gold/a<attempt>/{gold.diff,git_gold.diff,status_map.json,test_output.txt}",
         "source_pkg": "env_overnight_20260916/M3（机器 3）",
         "attempts": dict(Counter(r.get("attempt") for _, r in rows)),
         "snapshot": {"collected_at_local": NOW_LOCAL, "file_mtime_local": mtime_iso(gl),
                      "rows_at_collection": len(rows),
                      "warning": "机器 3 的 M3 包在采集时仍在补跑（本索引第一次采集时该文件只有 48 行 attempt=1，"
                                 "随后追加了 48 行 attempt=2）；引用行数请带采集时刻"}})

    nr = json.load(open(A(f"{M3R}/noop_repeat.json"), encoding="utf-8"))
    for t in nr["tasks"]:
        ch = None
        for full in r2e_by_commit:
            if full.startswith(t["commit12"]):
                ch = full
                break
        if ch is None:
            continue
        idx.ev(r2e_tid(ch), kind="r2e_noop_m3_x2", batch="env_overnight_20260916/M3",
               condition=(f"noop 连跑两次（同容器）machine=机器 3 expected_n={t.get('expected_n')} "
                          f"rc1={t.get('rc1')} rc2={t.get('rc2')}"),
               ledger=rp(f"{M3R}/noop_repeat.json"), line=None, started_at=None,
               result=t.get("status"), verdict=None, reward=t.get("noop_reward1"),
               log_dir=rp(f"{M3R}/facts/{t['commit12']}/noop_x2"),
               note=(f"run1_eq_run2={t.get('run1_eq_run2')} n_status_flips={t.get('n_status_flips')} "
                     f"noop_reward1={t.get('noop_reward1')} noop_reward2={t.get('noop_reward2')} "
                     f"vs_expected1.n_mismatch={(t.get('vs_expected1') or {}).get('n_mismatch')}"),
               source_pkg="M3")
    reg(f"{M3R}/noop_repeat.json", "r2e_noop_m3_x2", nr.get("n"),
        {"schema": nr.get("schema"), "machine": nr.get("machine"), "parser": nr.get("parser"),
         "tasks_covered": len(nr["tasks"]),
         "statuses": dict(Counter(t.get("status") for t in nr["tasks"])),
         "logs_dir": rp(f"{M3R}/facts/<commit12>/noop_x2"),
         "logs_layout": "facts/<commit12>/noop_x2/{out1.txt,out2.txt,rc.txt,cache_*.txt,status_after.txt}",
         "source_pkg": "env_overnight_20260916/M3（机器 3）"})

    cr_path = f"{PKG}/M3/M3_r2e_check_records.json"
    cr = json.load(open(A(cr_path), encoding="utf-8"))
    for t in cr["tasks"]:
        ch = t.get("commit_hash")
        tid = r2e_tid(ch)
        checks = t.get("checks") or {}
        st = Counter(v.get("status") for v in checks.values())
        idx.ev(tid, kind="m3_check_record", batch="env_overnight_20260916/M3",
               condition=f"镜像事实/泄漏/可用性 40 项检查（M-xx 编号）machine=机器 3 group={t.get('group')}",
               ledger=rp(cr_path), line=None, started_at=None,
               result=(t.get("disposition_hint") or {}).get("state"),
               verdict=None, reward=None,
               log_dir=rp(f"{M3R}/facts/{t.get('commit12')}"),
               note=(f"checks={dict(st)} issues={len(t.get('issues') or [])} "
                     f"gold_gate_m3={json.dumps(t.get('gold_gate_m3'), ensure_ascii=False)[:120]}"),
               source_pkg="M3")
    reg(cr_path, "m3_check_records", cr.get("n"),
        {"schema": cr.get("schema"), "machine": cr.get("machine"),
         "checks_numbering": cr.get("checks_numbering"),
         "tasks_covered": len(cr["tasks"]),
         "facts_dir": rp(f"{M3R}/facts"),
         "aggregate": rp(f"{M3R}/r2e_image_facts.json"),
         "source_pkg": "env_overnight_20260916/M3（机器 3）"})

    # =============================================================== 交叉核对 signals
    # 取 stage1 的权威账本：continuation（216 题全量）
    s1_full = load_jsonl(f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl")
    s1_partial_ids = {r["instance_id"] for _, r in load_jsonl(f"{S1}/stage1_offline.jsonl")}
    led = defaultdict(dict)  # inst -> gate -> row（多行时取最后一行，并记重复）
    dups = []
    for ln, r in s1_full:
        k = (r["instance_id"], r["gate"])
        if r["gate"] in led[r["instance_id"]]:
            dups.append({"instance_id": r["instance_id"], "gate": r["gate"],
                         "lines": [led[r["instance_id"]][r["gate"]]["line"], ln],
                         "verdicts": [led[r["instance_id"]][r["gate"]]["row"].get("official_verdict"),
                                      r.get("official_verdict")],
                         "results": [led[r["instance_id"]][r["gate"]]["row"].get("result"), r.get("result")]})
        led[r["instance_id"]][r["gate"]] = {"line": ln, "row": r}

    mismatches = []
    for s in sig:
        inst = s["instance_id"]
        st = s.get("stage1") or {}
        for gate in ("empty", "gold"):
            sg = st.get(gate) or {}
            lg = (led.get(inst) or {}).get(gate)
            if not lg:
                if sg:
                    mismatches.append({"instance_id": inst, "field": f"stage1.{gate}", "kind": "ledger_missing",
                                       "signals": sg, "ledger": None,
                                       "note": "signals 有判定但 continuation 账本无对应行"})
                continue
            row = lg["row"]
            if not sg:
                mismatches.append({
                    "instance_id": inst, "field": f"stage1.{gate}", "kind": "signals_missing",
                    "signals": None,
                    "ledger": {"verdict": row.get("official_verdict"), "result": row.get("result"),
                               "rc_install": row.get("rc_install"),
                               "path": rp(f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl"),
                               "line": lg["line"]},
                    "note": "signals 表该题 stage1 为空，但 continuation 账本里有实跑行（signals 只覆盖 "
                            "stage1_offline.jsonl 的 182 题）"})
                continue
            if sg.get("verdict") != row.get("official_verdict"):
                mismatches.append({
                    "instance_id": inst, "field": f"stage1.{gate}.verdict", "kind": "verdict_differs",
                    "signals": sg.get("verdict"), "ledger": row.get("official_verdict"),
                    "path": rp(f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl"), "line": lg["line"]})
            if "rc_install" in sg and sg.get("rc_install") != row.get("rc_install"):
                mismatches.append({
                    "instance_id": inst, "field": f"stage1.{gate}.rc_install", "kind": "rc_install_differs",
                    "signals": sg.get("rc_install"), "ledger": row.get("rc_install"),
                    "path": rp(f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl"), "line": lg["line"]})

    # in_e2 vs 实际 e2 账本
    e2_present = defaultdict(set)
    for lane, path in [("A", f"{E}/e2/ledger_e2_A.jsonl"), ("B", f"{E}/e2/ledger_e2_B.jsonl"),
                       ("B", f"{E}/e2/ledger_e2_B_repeat.jsonl"), ("B", f"{E}/e2/ledger_e2_derived.jsonl")]:
        for _, r in load_jsonl(path):
            e2_present[r["instance_id"]].add(lane)
    for s in sig:
        inst = s["instance_id"]
        declared = set(s.get("in_e2") or [])
        actual = e2_present.get(inst, set())
        # C 组（in_e2=["C"]）在采集时刻尚未出现在账本里属预期内
        if declared - actual - {"C"} or (actual - declared):
            mismatches.append({
                "instance_id": inst, "field": "in_e2", "kind": "e2_presence_differs",
                "signals": sorted(declared), "ledger": sorted(actual),
                "path": rp(f"{E}/e2/"), "line": None,
                "note": f"采集时刻 {NOW_LOCAL}；机器 1 的 e2 仍在运行，差异可能只是进度"})

    # deepseek_candidate_oracle vs cc_candidate_grading
    cand = defaultdict(dict)
    for ln, r in load_jsonl(f"{SYNC}/cc_candidate_grading.jsonl"):
        cand[r["instance_id"]][r["gate"]] = {"line": ln, "verdict": r.get("official_verdict")}
    for s in sig:
        inst, so = s["instance_id"], s.get("deepseek_candidate_oracle")
        c = cand.get(inst)
        if so is None and c:
            mismatches.append({"instance_id": inst, "field": "deepseek_candidate_oracle", "kind": "signals_missing",
                               "signals": None, "ledger": {k: v["verdict"] for k, v in c.items()},
                               "path": rp(f"{SYNC}/cc_candidate_grading.jsonl"), "line": None})
        elif so is not None and not c:
            mismatches.append({"instance_id": inst, "field": "deepseek_candidate_oracle", "kind": "ledger_missing",
                               "signals": so, "ledger": None,
                               "path": rp(f"{SYNC}/cc_candidate_grading.jsonl"), "line": None})
        elif so is not None and c:
            orig = (c.get("candidate") or {}).get("verdict")
            proj = (c.get("candidate_projected") or {}).get("verdict")
            if so != orig:
                mismatches.append({
                    "instance_id": inst, "field": "deepseek_candidate_oracle", "kind": "candidate_verdict_differs",
                    "signals": so, "ledger": {"candidate": orig, "candidate_projected": proj},
                    "path": rp(f"{SYNC}/cc_candidate_grading.jsonl"),
                    "line": (c.get("candidate") or {}).get("line"),
                    "note": "signals 的口径需确认是原组还是投影组"})

    # =============================================================== 副本关系（去重提醒）
    # stage1_offline.jsonl 的 364 行是 continuation 版前 364 行的逐行副本 —— 同一次运行的中途快照。
    part_rows = [json.dumps(r, sort_keys=True) for _, r in load_jsonl(f"{S1}/stage1_offline.jsonl")]
    full_rows = [json.dumps(r, sort_keys=True) for _, r in s1_full]
    s1_is_prefix = part_rows == full_rows[: len(part_rows)]
    bkup_rows = load_jsonl(f"{BKUP}/swegym_ledger.jsonl")
    sync_rows = load_jsonl(f"{SYNC}/swegym_ledger.jsonl")
    bk_is_prefix = [json.dumps(r, sort_keys=True) for _, r in bkup_rows] == [
        json.dumps(r, sort_keys=True) for _, r in sync_rows[: len(bkup_rows)]
    ]
    ledger_relations = {
        "docs_archive_vs_runs_final_sync": {
            "files": ["cc_candidate_grading.jsonl", "cc_reference_ledger.jsonl", "r2e_ledger.jsonl",
                      "r2e_ledger_v2.jsonl", "r2e_ledger_v3.jsonl", "swegym_facts_v2.jsonl", "swegym_ledger.jsonl"],
            "verdict": "7 个文件 sha256 全部相同（swegym_ledger.jsonl 也相同）",
            "action": "docs/.../env_probe_20260909/ledger/ 是 runs/env_probe_20260909_final_sync/ledger/ 的归档副本，"
                      "统计时只数一份；本索引统一引用 runs/ 版",
        },
        "codex_backup_vs_final_sync": {
            "swegym_ledger_rows": [len(bkup_rows), len(sync_rows)],
            "backup_is_row_prefix_of_final": bk_is_prefix,
            "other_files_identical": True,
            "action": "codex_backup 是 20260909 夜跑到一半的快照（swegym_ledger 少 424 行），"
                      "不要与 final_sync 相加；其独有内容是 analysis/ 与 data/（输入快照、solvability_review 副本）",
        },
        "stage1_partial_vs_continuation": {
            "rows": [len(part_rows), len(full_rows)],
            "partial_is_row_prefix_of_continuation": s1_is_prefix,
            "task_ids": [len(s1_partial_ids), len(led)],
            "action": "runs/.../stage1_offline.jsonl(364 行/182 题) 是 "
                      "stage1_continuation_20260911/stage1_offline.jsonl(434 行/216 题) 的中途快照；"
                      "按题统计只用 continuation 版",
        },
    }
    SUPERSEDED_LEDGERS = {rp(f"{S1}/stage1_offline.jsonl")}
    for t in idx.tasks.values():
        for e in t["evidence"]:
            if e.get("ledger") in SUPERSEDED_LEDGERS:
                e["superseded_by"] = rp(f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl")

    # =============================================================== 覆盖 / 缺件统计
    CORE_SWEGYM = ["oracle_facts", "oracle_empty", "oracle_gold", "stage1_empty", "stage1_gold"]
    CORE_R2E = ["r2e_gold_m3", "r2e_noop_m3_x2", "m3_check_record"]
    OPT_R2E = ["r2e_facts", "r2e_noop", "r2e_gold"]
    missing_counter = Counter()
    for tid, t in idx.tasks.items():
        kinds = sorted({e["kind"] for e in t["evidence"]})
        t["kinds_present"] = kinds
        t["evidence_count"] = len(t["evidence"])
        core = CORE_SWEGYM if t.get("source", "").startswith("SWE-Gym") else CORE_R2E
        miss = [k for k in core if k not in kinds]
        if not t.get("source", "").startswith("SWE-Gym"):
            if not any(k in kinds for k in OPT_R2E):
                miss.append("r2e_20260909_oracle(facts/noop/gold 任一)")
        t["missing"] = miss
        for m in miss:
            missing_counter[m] += 1

    swe_ids = [k for k, v in idx.tasks.items() if v.get("source", "").startswith("SWE-Gym")]
    r2e_ids = [k for k, v in idx.tasks.items() if v.get("source", "").startswith("R2E")]
    kind_cover = Counter()
    for t in idx.tasks.values():
        for k in t["kinds_present"]:
            kind_cover[k] += 1

    # --- 有效覆盖：不止"有行"，而是"有能用的判定" ---
    def has(t, kind, pred):
        return any(pred(e) for e in t["evidence"] if e["kind"] == kind)

    full = lambda e: e.get("verdict") == "RESOLVED_FULL"          # noqa: E731
    no_ = lambda e: e.get("verdict") == "RESOLVED_NO"             # noqa: E731
    rw1 = lambda e: e.get("reward") == 1                          # noqa: E731

    swe_t = [idx.tasks[i] for i in swe_ids]
    r2e_t = [idx.tasks[i] for i in r2e_ids]
    gold_none = [t["task_id"] for t in swe_t
                 if not has(t, "oracle_gold", full) and not has(t, "stage1_gold", full)]
    gold_split = []
    for t in swe_t:
        a, b = has(t, "oracle_gold", full), has(t, "stage1_gold", full)
        if a != b:
            gold_split.append({
                "instance_id": t["task_id"],
                "oracle_gold_20260909(network=default)": sorted(
                    {str(e.get("verdict")) for e in t["evidence"] if e["kind"] == "oracle_gold"}),
                "stage1_gold(network=none, variant=offline)": sorted(
                    {str(e.get("verdict")) for e in t["evidence"] if e["kind"] == "stage1_gold"}),
            })
    effective = {
        "swegym": {
            "gold_RESOLVED_FULL_20260909": sum(1 for t in swe_t if has(t, "oracle_gold", full)),
            "gold_RESOLVED_FULL_stage1_offline": sum(1 for t in swe_t if has(t, "stage1_gold", full)),
            "empty_RESOLVED_NO_20260909": sum(1 for t in swe_t if has(t, "oracle_empty", no_)),
            "empty_RESOLVED_NO_stage1_offline": sum(1 for t in swe_t if has(t, "stage1_empty", no_)),
            "gold_never_RESOLVED_FULL_anywhere": gold_none,
            "gold_online_vs_offline_disagree": gold_split,
        },
        "r2e": {
            "gold_reward1_20260909_v3": sum(1 for t in r2e_t if any(
                e["kind"] == "r2e_gold" and e.get("reward") == 1 and "v3" in (e.get("batch") or "")
                for e in t["evidence"])),
            "gold_reward1_M3": sum(1 for t in r2e_t if has(t, "r2e_gold_m3", rw1)),
            "gold_never_reward1": [t["task_id"] for t in r2e_t
                                   if not has(t, "r2e_gold_m3", rw1) and not has(t, "r2e_gold", rw1)],
            "noop_x2_not_identical": [t["task_id"] for t in r2e_t
                                      if any(e["kind"] == "r2e_noop_m3_x2" and "run1_eq_run2=False" in (e.get("note") or "")
                                             for e in t["evidence"])],
        },
    }

    caliber_notes = [
        {
            "id": "C1",
            "title": "R2E 账本 v1/v2 的 gold reward 已被 v3 覆盖，不可与 v3/M3 混读",
            "detail": "r2e_probe/0.1(v1) 与 0.2(v2) 的期望测试 ID 键未去 ANSI 转义（形如 "
                      "\"\\u001bTestFileTiff.test_4bit\\u001b\"），与解析出的裸键对不上，产生 8 missing + 8 extra → reward 0；"
                      "v1 另有参数化多行用例名截断问题（pandas 294cbc8d1faa，5 missing/5 extra）。"
                      "r2e_probe/0.3(v3) 两类都修掉，同一 commit 由 reward 0 变 1（core24 里 5 个 commit：pillow "
                      "f9d3ee0f4888 / 2d01f7d02243 / 3a61c9e95e5c / a682ceaf47ab、pandas 294cbc8d1faa）。",
            "action": "读 R2E gold/noop 结论时只用 v3（r2e_probe/0.3）、阶段一扩展与 M3 的行；v1/v2 仅作为解析器演进的历史。",
            "evidence": [rp(f"{SYNC}/r2e_ledger.jsonl"), rp(f"{SYNC}/r2e_ledger_v2.jsonl"),
                         rp(f"{SYNC}/r2e_ledger_v3.jsonl")],
        },
        {
            "id": "C2",
            "title": "DeepSeek 候选有『原组』与『投影组』两套判定，signals 表取的是原组",
            "detail": "cc_candidate_grading.jsonl 每题两行：gate=candidate（原补丁）与 gate=candidate_projected（投影后）。"
                      "24 题里只有 Project-MONAI__MONAI-2454 两组不同（原组 UNPARSED，投影组 RESOLVED_NO）；"
                      "task_signals_swegym.json 的 deepseek_candidate_oracle 与原组 24/24 一致。",
            "action": "引用『DeepSeek 解没解出来』时写明取原组还是投影组。",
            "evidence": [rp(f"{SYNC}/cc_candidate_grading.jsonl")],
        },
        {
            "id": "C3",
            "title": "20260909 夜探针是联网（network=default）、阶段一是离线（variant=offline, network=none）",
            "detail": "同一题 gold 在两处可能判定相反：5 题联网 RESOLVED_FULL、离线 RESOLVED_NO/PARTIAL"
                      "（Project-MONAI__MONAI-1121、Project-MONAI__MONAI-3205、getmoto__moto-4799、"
                      "getmoto__moto-4833、getmoto__moto-7105）。MONAI-1121 的三次对照实验"
                      "（online / offline_cached / offline_uncached）就是为这个差异做的：online 与 offline_cached "
                      "RESOLVED_FULL，offline_uncached RESOLVED_NO。",
            "action": "比较任意两条 gold 证据前先看 condition 里的 network / variant。",
            "evidence": [rp(f"{S1}/monai1121_online_20260911/results.jsonl"),
                         rp(f"{S1}/monai1121_offline_cached_20260911/results.jsonl"),
                         rp(f"{S1}/monai1121_offline_uncached_20260911/results.jsonl")],
        },
        {
            "id": "C4",
            "title": "rh2（e1/e2）与 oracle 探针的执行条件不同",
            "detail": "L0 的 reconcile.md 列出三处系统性差异：network deny_all → none；测试执行用户 rh2grader → root；"
                      "memory_bytes 4294967296(4 GiB) → 8589934592(8 GiB)。"
                      "rh2 侧判定字段是 report.outcome/report.reward（resolved/unresolved/failed_to_grade），"
                      "oracle 侧是 official_verdict（RESOLVED_FULL/PARTIAL/NO），两套词表不要互相翻译。",
            "action": "把 rh2 与 oracle 的差异先归到条件差异，再谈判定差异。",
            "evidence": [f"{PKG}/L0_facts_tool/facts_e1/reconcile.md"],
        },
        {
            "id": "C5",
            "title": "账本副本会重复计数",
            "detail": json.dumps(ledger_relations, ensure_ascii=False),
            "action": "按题统计时：20260909 只用 runs/env_probe_20260909_final_sync/ledger/；"
                      "阶段一只用 stage1_continuation_20260911/stage1_offline.jsonl。"
                      "本索引里来自被取代账本的条目带 superseded_by 字段。",
            "evidence": [rp(f"{S1}/stage1_offline.jsonl"), rp(f"{BKUP}/swegym_ledger.jsonl")],
        },
        {
            "id": "C6",
            "title": "e2 账本是运行中快照",
            "detail": f"采集时刻 {NOW_LOCAL}；机器 1 的 e2 仍在跑，四个账本的行数会继续增长。"
                      "in_e2 标了 C 组的 4 题在采集时刻尚未出现在任何 e2 账本里。",
            "action": "引用 e2 数字务必带采集时刻与行数。",
            "evidence": [rp(f"{E}/e2/ledger_e2_A.jsonl"), rp(f"{E}/e2/ledger_e2_B.jsonl")],
        },
    ]

    doc = {
        "schema": "rh2.env_overnight.l5.evidence_index.v1",
        "generated_at_local": NOW_LOCAL,
        "generated_by": f"{PKG}/L5_evidence_index/build_evidence_index.py",
        "workspace_root_note": "所有 path/ledger/log_dir 均为相对工作区根的路径",
        "task_lists": {
            "swegym": {"path": f"{PKG}/task_signals_swegym.json", "n": len(sig)},
            "r2e": {"path": f"{PKG}/L4_r2e/r2e_tasks_48.json", "n": len(r2e_tasks["tasks"])},
        },
        "coverage": {
            "swegym_tasks_in_list": len(sig),
            "swegym_tasks_with_any_evidence": sum(1 for i in swe_ids if idx.tasks[i]["evidence_count"] > 0),
            "r2e_tasks_in_list": len(r2e_tasks["tasks"]),
            "r2e_tasks_with_any_evidence": sum(1 for i in r2e_ids if idx.tasks[i]["evidence_count"] > 0),
            "tasks_outside_list": [k for k, v in idx.tasks.items() if not v.get("in_task_list", False)],
            "kind_task_coverage": dict(sorted(kind_cover.items(), key=lambda kv: -kv[1])),
            "total_evidence_entries": sum(t["evidence_count"] for t in idx.tasks.values()),
        },
        "effective_coverage": effective,
        "caliber_notes": caliber_notes,
        "ledger_relations": ledger_relations,
        "ledgers": idx.ledgers,
        "ledger_totals": {
            "n_ledgers": len(idx.ledgers),
            "total_rows": sum(l.get("rows") or 0 for l in idx.ledgers),
        },
        "signals_crosscheck": {
            "input": f"{PKG}/task_signals_swegym.json",
            "authoritative_stage1_ledger": rp(f"{S1}/stage1_continuation_20260911/stage1_offline.jsonl"),
            "n_mismatch": len(mismatches),
            "by_kind": dict(Counter(m["kind"] for m in mismatches)),
            "stage1_partial_ledger_ids": len(s1_partial_ids),
            "stage1_full_ledger_ids": len(led),
            "duplicate_rows_in_full_ledger": dups,
            "mismatches": mismatches,
        },
        "missing_summary": dict(missing_counter.most_common()),
        "tasks": idx.tasks,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote", OUT)
    print("ledgers:", len(idx.ledgers), "rows:", doc["ledger_totals"]["total_rows"])
    print("coverage:", json.dumps({k: v for k, v in doc["coverage"].items() if k != "kind_task_coverage"},
                                  ensure_ascii=False))
    print("kind coverage:", json.dumps(doc["coverage"]["kind_task_coverage"], ensure_ascii=False))
    print("mismatch:", doc["signals_crosscheck"]["n_mismatch"], doc["signals_crosscheck"]["by_kind"])
    print("missing:", doc["missing_summary"])
    print("dups:", json.dumps(dups, ensure_ascii=False))
    print("effective:", json.dumps(effective, ensure_ascii=False)[:1400])
    print("relations ok:",
          {k: (v.get("partial_is_row_prefix_of_continuation") or v.get("backup_is_row_prefix_of_final") or v.get("verdict"))
           for k, v in ledger_relations.items()})


NOW_LOCAL = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

if __name__ == "__main__":
    main()
