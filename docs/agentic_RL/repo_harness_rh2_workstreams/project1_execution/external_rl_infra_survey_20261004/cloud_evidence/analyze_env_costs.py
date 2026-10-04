#!/usr/bin/env python3
"""52 题双模型 GPU 探针：逐题环境准备与评分开销分析。

对仓库与既有证据只读；只往本脚本所在目录写输出。

输入（仓库相对路径）：
  - docs/.../dataset_status/tasks.json：52 题（work_group == current52）
  - docs/.../category2_repair_20260929/experiment_artifact_index_20261004.json：106 次历史尝试及本地文件
  - 每次尝试：attempt/attempt.json、gateway_audit.json 与网关 requests.jsonl（只读第一行）、
    grading/report.json、grading/eval_logs/*.diagnostics.json、*.eval.log、
    attempt/frozen/baseline_census.txt、队列 state.json（作业墙钟）

输出（本目录）：
  per_attempt.json / .csv：每次历史尝试一行（106）
  per_task.json / .csv：每题一行（52），对可用尝试 / 评分取中位数
  summary.json：覆盖率、跨题汇总、排序、编译缓存候选
  report.md：简短可读表
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import json
import os
import re
import statistics
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXEC = "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
TASKS_JSON = f"{EXEC}/dataset_status/tasks.json"
INDEX_JSON = f"{EXEC}/category2_repair_20260929/experiment_artifact_index_20261004.json"
GPU_REMOTE_PREFIX = "/work/ordinary_gpu_probe_20261002/"
GPU_LOCAL_PREFIX = "runs/ordinary_gpu_probe_20261002/remote/"

COMPILE_CACHE_INSTALL_THRESHOLD_S = 60.0

# ---------------------------------------------------------------- helpers


def rp(p: str) -> Path:
    return ROOT / p


def load(p: str):
    with open(rp(p), encoding="utf-8") as fh:
        return json.load(fh)


def ts(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(s).timestamp()


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 3) if xs else None


def quantile(xs, q):
    """Linear-interpolation quantile (same as numpy 'linear')."""
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return round(xs[0], 3)
    pos = (len(xs) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (pos - lo), 3)


def fnum(x, nd=3):
    try:
        return round(float(x), nd)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- eval-log install-phase parsing

RE_COMPILER = re.compile(
    r"^\s*(?:\+\s*)*(?:\S*/)?(?:x86_64-conda[_-]linux-gnu-|x86_64-linux-gnu-|x86_64-pc-linux-gnu-)?"
    r"(?:gcc|g\+\+|cc|c\+\+|clang|clang\+\+|gfortran)(?:-\d+(?:\.\d+)*)?\s+-\S"
)
RE_EXT = re.compile(r"building '([^']+)' extension")
RE_CYTHON = re.compile(r"Cythonizing |Compiling \S+\.pyx because|\[\d+/\d+\] Cythonizing")
RE_NINJA = re.compile(r"\[\d+/\d+\] (?:Compiling|Linking) (?:C|C\+\+|Cython|Fortran)")
RE_SO_COPY = re.compile(r"(?:copying|creating) \S*\.so\b")
RE_WHEEL = re.compile(r"Building (?:wheel|editable) for (\S+)")
RE_DOWNLOAD = re.compile(r"^\s*Downloading\s+\S+")
RE_COLLECT = re.compile(r"^\s*Collecting\s+\S+")
RE_INSTALL_CMD = re.compile(r"^\+ (.*(?:pip install|setup\.py|build_ext|make\b|meson|ninja|cmake|uv pip|conda install).*)$")


def parse_eval_log(path: str) -> dict:
    out = {
        "install_phase_present": False, "install_skipped_marker": False,
        "compiler_compile": 0, "compiler_link": 0, "compiler_total": 0,
        "extensions_built": 0, "cython_steps": 0, "ninja_steps": 0, "so_copies": 0,
        "wheels_built": [], "downloads": 0, "collecting": 0,
        "install_ts_start": None, "install_ts_end": None, "install_commands": [],
    }
    inside = False
    with open(rp(path), encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            ln = raw.rstrip("\n")
            plain = not ln.startswith("+")
            if plain and ln.startswith("RH2_INSTALL_SKIPPED=1"):
                out["install_skipped_marker"] = True
            if plain and ln.startswith("RH2_TS_INSTALL_START="):
                out["install_ts_start"] = fnum(ln.split("=", 1)[1], 6)
            if plain and ln.startswith("RH2_TS_INSTALL_END="):
                out["install_ts_end"] = fnum(ln.split("=", 1)[1], 6)
            if plain and ln.strip() == "RH2_PHASE_START=install":
                inside = True
                out["install_phase_present"] = True
                continue
            if plain and ln.strip() == "RH2_PHASE_END=install":
                inside = False
                continue
            if not inside:
                continue
            if RE_COMPILER.search(ln):
                out["compiler_total"] += 1
                if re.search(r"\s-c\s", ln):
                    out["compiler_compile"] += 1
                elif "-shared" in ln:
                    out["compiler_link"] += 1
            if RE_EXT.search(ln):
                out["extensions_built"] += 1
            if RE_CYTHON.search(ln):
                out["cython_steps"] += 1
            if RE_NINJA.search(ln):
                out["ninja_steps"] += 1
            if RE_SO_COPY.search(ln):
                out["so_copies"] += 1
            m = RE_WHEEL.search(ln)
            if m and m.group(1) not in out["wheels_built"]:
                out["wheels_built"].append(m.group(1))
            if RE_DOWNLOAD.search(ln):
                out["downloads"] += 1
            if RE_COLLECT.search(ln):
                out["collecting"] += 1
            m = RE_INSTALL_CMD.match(ln)
            if m and len(out["install_commands"]) < 6:
                cmd = m.group(1).strip()
                if not cmd.startswith("trap") and cmd not in out["install_commands"]:
                    out["install_commands"].append(cmd[:160])
    if out["install_ts_start"] and out["install_ts_end"]:
        out["install_wall_from_ts_s"] = round(out["install_ts_end"] - out["install_ts_start"], 3)
    else:
        out["install_wall_from_ts_s"] = None
    out["compile_evidence"] = bool(out["compiler_compile"] or out["cython_steps"] or out["ninja_steps"] or out["extensions_built"])
    return out


# ---------------------------------------------------------------- census (in-tree native code)

RE_NATIVE_BIN = re.compile(r"\.(?:so|pyd)$|\.so\.\d")
RE_NATIVE_SRC = re.compile(r"\.(?:c|cc|cpp|cxx|h|hpp|pyx|pxd|pxi|f|f90)$")


def parse_census(path: str) -> dict:
    nbin = nsrc = n = 0
    with open(rp(path), encoding="utf-8", errors="replace") as fh:
        for ln in fh:
            parts = ln.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            n += 1
            name = parts[-1]
            if RE_NATIVE_BIN.search(name):
                nbin += 1
            if RE_NATIVE_SRC.search(name):
                nsrc += 1
    return {"census_entries": n, "intree_native_binaries": nbin, "intree_native_sources": nsrc}


# ---------------------------------------------------------------- gateway first request


def first_gateway_request_ts(files: list[str], job_id: str, model: str):
    audit = next((f for f in files if f.endswith("/gateway_audit.json")), None)
    cands = []
    if audit:
        src = load(audit).get("source")
        if src and src.startswith(GPU_REMOTE_PREFIX):
            cands.append(GPU_LOCAL_PREFIX + src[len(GPU_REMOTE_PREFIX):] + "/requests.jsonl")
    cands += sorted(glob.glob(str(rp(GPU_LOCAL_PREFIX + f"services*/*/gateway/{job_id}/requests.jsonl"))))
    for c in cands:
        p = Path(c)
        if not p.is_absolute():
            p = rp(c)
        if p.exists():
            with open(p, encoding="utf-8", errors="replace") as fh:
                first = fh.readline()
            try:
                return float(json.loads(first)["ts"]), str(p.relative_to(ROOT))
            except Exception:  # noqa: BLE001
                continue
    return None, None


# ---------------------------------------------------------------- queue state (job wall)


def job_wall(attempt_path: str, job_id: str):
    qdir = attempt_path.split("/results/")[0]
    st = rp(qdir + "/state.json")
    if not st.exists():
        return None, None, None
    try:
        j = json.loads(st.read_text(encoding="utf-8")).get("jobs", {}).get(job_id)
    except Exception:  # noqa: BLE001
        return None, None, None
    if not j:
        return None, None, None
    a, b = ts(j.get("started_at")), ts(j.get("ended_at"))
    return a, b, (round(b - a, 3) if a and b else None)


# ---------------------------------------------------------------- per attempt


def attempt_row(task: dict, att: dict) -> dict:
    files = [f["path"] for f in att["local_artifact_files"]]
    A = load(att["attempt"])
    tm = A.get("timings") or {}
    st = A.get("stages") or {}
    lf = A.get("launch_facts") or {}
    hl = lf.get("harness_log") or {}
    cc = ((A.get("trajectory_summary") or {}).get("cc_result")) or {}
    san = ((st.get("sanitize_and_init") or {}).get("git_sanitize")) or {}
    started, finished = ts(A.get("started_at")), ts(A.get("finished_at"))
    env_facts_at = ts((st.get("agent_env_facts") or {}).get("at"))
    boot = fnum(lf.get("bootstrap_seconds"))
    uinit = fnum((lf.get("agent_user_init_bootstrap") or {}).get("seconds"))
    gw_ts, gw_path = first_gateway_request_ts(files, att["job_id"], att["model"])
    row = {
        "instance_id": task["instance_id"], "source": task["source"], "repository": task["repository"],
        "job_id": att["job_id"], "model": att["model"], "attempt_json": att["attempt"],
        "termination": A.get("termination"), "result": A.get("result"),
        "actor_started_at": A.get("started_at"), "actor_finished_at": A.get("finished_at"),
        "actor_wall_s": round(finished - started, 3) if started and finished else None,
        "image_ready_s": fnum(tm.get("image_ready")),
        "network_and_container_s": fnum(tm.get("network_and_container")),
        "git_sanitize_s": fnum(tm.get("git_sanitize")),
        "git_sanitize_inner_s": fnum(san.get("SECONDS_ELAPSED")),
        "git_history_count": int(san["HISTORY_COUNT_BEFORE"]) if str(san.get("HISTORY_COUNT_BEFORE", "")).isdigit() else None,
        "trusted_init_s": fnum(tm.get("trusted_init")),
        "baseline_census_s": fnum(tm.get("baseline_census")),
        "baseline_archive_s": fnum((A.get("baseline_archive") or {}).get("seconds")),
        "quiescence_s": fnum(tm.get("quiescence")),
        "prep_s": fnum(tm.get("prep")),
        "start_to_env_facts_s": round(env_facts_at - started, 3) if env_facts_at and started else None,
        "cc_bootstrap_s": boot,
        "agent_user_init_s": uinit,
        "cc_cli_install_s": round(boot - uinit, 3) if boot is not None and uinit is not None else None,
        "harness_exec_s": fnum(hl.get("seconds")),
        "solve_s": fnum(A.get("solve_seconds")),
        "cc_duration_s": round(cc["duration_ms"] / 1000.0, 3) if cc.get("duration_ms") is not None else None,
        "cc_num_turns": cc.get("num_turns"),
        "gateway_first_request_log": gw_path,
    }
    row["pre_launch_s"] = (round(row["start_to_env_facts_s"] + boot, 3)
                           if row["start_to_env_facts_s"] is not None and boot is not None else None)
    row["time_to_first_model_request_s"] = round(gw_ts - started, 3) if gw_ts and started else None
    if row["time_to_first_model_request_s"] is not None and row["pre_launch_s"] is not None:
        row["launch_gap_s"] = round(row["time_to_first_model_request_s"] - row["pre_launch_s"], 3)
    else:
        row["launch_gap_s"] = None
    row["actor_non_cc_overhead_s"] = (round(row["actor_wall_s"] - row["harness_exec_s"], 3)
                                      if row["actor_wall_s"] is not None and row["harness_exec_s"] is not None else None)
    # post-solve ≈ actor wall − CC exec − time to first request (CC start-up overlap of ~1–2 s is not separable)
    if row["actor_wall_s"] is not None and row["harness_exec_s"] is not None and row["time_to_first_model_request_s"] is not None:
        row["post_solve_approx_s"] = round(row["actor_wall_s"] - row["harness_exec_s"] - row["time_to_first_model_request_s"], 3)
    else:
        row["post_solve_approx_s"] = None
    q_at = ts((st.get("quiescence") or {}).get("at"))
    row["post_quiescence_to_finish_s"] = round(finished - q_at, 3) if q_at and finished else None  # export + render + container/network cleanup
    # agent env-facts exec (slime exec_and_wait has a 5 s first-poll floor)
    prev = [ts(v.get("at")) for k, v in st.items() if isinstance(v, dict) and v.get("at") and k != "agent_env_facts"
            and ts(v.get("at")) and env_facts_at and ts(v.get("at")) < env_facts_at]
    row["env_facts_step_s"] = round(env_facts_at - max(prev), 3) if prev and env_facts_at else None
    row["actor_image_id"] = A.get("container_image_id") or A.get("image_id")
    # census
    cen = next((f for f in files if f.endswith("/attempt/frozen/baseline_census.txt")), None)
    row.update(parse_census(cen) if cen else {"census_entries": None, "intree_native_binaries": None, "intree_native_sources": None})
    cand = A.get("candidate") or {}
    row["candidate_native_source_files"] = [f for f in (cand.get("files") or []) if RE_NATIVE_SRC.search(f)]
    # job wall
    ja, jb, jw = job_wall(att["attempt"], att["job_id"])
    row["job_wall_s"] = jw
    # grading
    rep = next((f for f in files if f.endswith("/grading/report.json")), None)
    diag = next((f for f in files if f.endswith(".diagnostics.json")), None)
    evl = next((f for f in files if f.endswith(".eval.log")), None)
    row["grading_report"] = rep
    row["grading_present"] = bool(rep)
    if rep:
        R = load(rep)
        t = R.get("timings") or {}
        row.update({
            "grading_outcome": R.get("outcome"), "grading_failure_category": R.get("failure_category"),
            "grading_infra_detail": (R.get("infra_failure_detail") or None),
            "reward": R.get("reward"),
            "grading_total_s": fnum(t.get("total_grading_seconds")),
            "grading_env_reset_s": fnum(t.get("env_reset_seconds")),
            "grading_prep_s": fnum(t.get("prep_seconds")),
            "grading_test_phase_s": fnum(t.get("test_seconds")),
            "grading_image_pull_s": fnum(t.get("image_pull_seconds")),
            "grading_queue_wait_s": fnum(t.get("queue_wait_seconds")),
            "grading_peak_mem_mb": fnum(t.get("container_peak_memory_mb"), 1),
            "graded_at": R.get("graded_at_utc"),
        })
        gend = ts(R.get("graded_at_utc"))
        row["grading_end_ts"] = gend
        row["grading_start_ts"] = (gend - row["grading_total_s"]) if gend and row["grading_total_s"] else None
    if diag:
        D = load(diag)
        c = D.get("candidate") or {}
        ps = D.get("phase_segments_seconds") or {}
        g = D.get("git_sanitize") or {}
        perf = D.get("performance")
        row.update({
            "grading_diagnostics": diag,
            "grader_git_sanitize_s": fnum(g.get("seconds")),
            "grader_start_and_verify_s": fnum(ps.get("grader_start_and_verify")),
            "grader_trusted_setup_s": fnum(ps.get("grader_trusted_setup")),
            "grader_baseline_rebuild_s": fnum(ps.get("grader_baseline_rebuild")),
            "grader_delta_apply_s": fnum(ps.get("delta_apply")),
            "grader_candidate_phase_s": fnum(ps.get("test")),
            "install_s": fnum(c.get("install_seconds")),
            "install_skipped": c.get("install_skipped"),
            "candidate_test_s": fnum(c.get("test_seconds")),
            "candidate_segment_completed": c.get("candidate_segment_completed"),
            "install_failed_commands": len(c.get("install_failed_commands") or []),
            "grading_supply": D.get("supply"),
            "grading_image_identity": D.get("image_identity"),
            # v13 performance diagnostics (permission templates) were never part of the GPU frozen_code_v8 run;
            # their absence plus a plain local_build image identity means the plain fresh path.
            "grading_permission_mode": ("prepared_template" if (perf and (perf.get("template") or perf.get("prepared_template")))
                                        else ("performance_diag_present" if perf else "plain_fresh_no_template")),
        })
        img = str(D.get("image_identity") or "")
        row["grading_image_same_as_actor"] = bool(row.get("actor_image_id")) and img.endswith(str(row["actor_image_id"]))
        parts = [row.get(k) for k in ("grader_start_and_verify_s", "grader_baseline_rebuild_s", "grader_delta_apply_s",
                                      "grader_trusted_setup_s", "grader_candidate_phase_s")]
        if row.get("grading_total_s") is not None and all(p is not None for p in parts):
            row["grader_other_s"] = round(row["grading_total_s"] - sum(parts), 3)
        else:
            row["grader_other_s"] = None
    if evl:
        E = parse_eval_log(evl)
        row["eval_log"] = evl
        row.update({f"evl_{k}": v for k, v in E.items()})
    return row


# ---------------------------------------------------------------- per task


def classify_compile(rows: list[dict]) -> tuple[str, str]:
    gr = [r for r in rows if r.get("eval_log")]
    if not gr:
        return "unknown", "no eval log"
    comp = max((r.get("evl_compiler_compile") or 0) for r in gr)
    cy = max((r.get("evl_cython_steps") or 0) for r in gr)
    ext = max((r.get("evl_extensions_built") or 0) for r in gr)
    nin = max((r.get("evl_ninja_steps") or 0) for r in gr)
    skipped = all(r.get("install_skipped") or r.get("evl_install_skipped_marker") for r in gr)
    inst = med([r.get("install_s") for r in gr])
    if skipped:
        return "no (install skipped)", "grading install phase skipped in every grading"
    if comp or cy or ext or nin:
        if inst is not None and inst > COMPILE_CACHE_INSTALL_THRESHOLD_S:
            return "needs compile cache", f"compile={comp} cython={cy} ext={ext}; install median {inst}s"
        return "maybe", f"compile={comp} cython={cy} ext={ext}; install median {inst}s"
    return "no", f"no compiler/Cython/extension lines; install median {inst}s"


def task_row(task: dict, rows: list[dict]) -> dict:
    act = [r for r in rows if r.get("git_sanitize_s") is not None]
    grd = [r for r in rows if r.get("grading_present")]
    # complete = candidate install/test actually ran (not cut off before the candidate segment)
    cmp_ = [r for r in grd if r.get("candidate_segment_completed")]
    cens = [r for r in grd if not r.get("candidate_segment_completed")]
    out = {
        "instance_id": task["instance_id"], "source": task["source"], "repository": task["repository"],
        "n_attempts": len(rows), "n_actor_timed": len(act),
        "n_gradings": len(grd), "n_gradings_candidate_ran": len(cmp_),
        "gradings_cut_short": [f"{r['job_id']}:{r.get('grading_infra_detail') or r.get('grading_outcome')}" for r in cens],
        "gradings_other_flags": [f"{r['job_id']}:{r.get('grading_outcome')}/{r.get('grading_failure_category')}"
                                 for r in cmp_ if r.get("grading_outcome") not in ("resolved", "unresolved")],
        "missing_grading": [r["job_id"] for r in rows if not r.get("grading_present")],
    }
    for k in ("image_ready_s", "network_and_container_s", "git_sanitize_s", "git_sanitize_inner_s", "trusted_init_s",
              "baseline_census_s", "baseline_archive_s", "quiescence_s", "start_to_env_facts_s", "cc_bootstrap_s",
              "cc_cli_install_s", "agent_user_init_s", "pre_launch_s", "time_to_first_model_request_s", "launch_gap_s",
              "actor_non_cc_overhead_s", "actor_wall_s", "cc_duration_s", "harness_exec_s", "job_wall_s",
              "post_solve_approx_s", "post_quiescence_to_finish_s", "env_facts_step_s"):
        out[f"actor_{k}_med" if not k.startswith("actor_") else f"{k}_med"] = med([r.get(k) for r in act])
    out["git_history_count"] = max([r["git_history_count"] for r in act if r.get("git_history_count")] or [None]) if act else None
    for k in ("grading_total_s", "grader_git_sanitize_s", "grader_start_and_verify_s", "grader_trusted_setup_s",
              "install_s", "candidate_test_s", "grader_candidate_phase_s", "grading_peak_mem_mb", "grader_other_s"):
        out[f"{k}_med"] = med([r.get(k) for r in cmp_])
    out["grading_image_same_as_actor_all"] = bool(grd) and all(r.get("grading_image_same_as_actor") for r in grd)
    out["grading_total_s_cut_short_values"] = [r.get("grading_total_s") for r in cens]
    out["grading_permission_modes"] = sorted({r.get("grading_permission_mode") for r in grd if r.get("grading_permission_mode")})
    out["grading_image_pull_s_max"] = max([r.get("grading_image_pull_s") or 0 for r in grd] or [None]) if grd else None
    out["install_skipped_all"] = bool(grd) and all(r.get("install_skipped") for r in grd if r.get("grading_diagnostics"))
    ev = [r for r in rows if r.get("eval_log")]
    out["evl_compiler_compile_max"] = max([r.get("evl_compiler_compile") or 0 for r in ev] or [None]) if ev else None
    out["evl_compiler_link_max"] = max([r.get("evl_compiler_link") or 0 for r in ev] or [None]) if ev else None
    out["evl_extensions_built_max"] = max([r.get("evl_extensions_built") or 0 for r in ev] or [None]) if ev else None
    out["evl_cython_steps_max"] = max([r.get("evl_cython_steps") or 0 for r in ev] or [None]) if ev else None
    out["evl_downloads_max"] = max([r.get("evl_downloads") or 0 for r in ev] or [None]) if ev else None
    out["evl_wheels_built"] = sorted({w for r in ev for w in (r.get("evl_wheels_built") or [])})
    out["evl_install_commands"] = next((r.get("evl_install_commands") for r in ev if r.get("evl_install_commands")), [])
    out["install_wall_from_ts_med"] = med([r.get("evl_install_wall_from_ts_s") for r in ev])
    out["intree_native_binaries"] = max([r.get("intree_native_binaries") or 0 for r in rows] or [0])
    out["intree_native_sources"] = max([r.get("intree_native_sources") or 0 for r in rows] or [0])
    out["candidates_touching_native_sources"] = [r["job_id"] for r in rows if r.get("candidate_native_source_files")]
    out["compile_class"], out["compile_basis"] = classify_compile(rows)
    a_over = out.get("actor_non_cc_overhead_s_med")
    g_tot = out.get("grading_total_s_med")
    out["non_model_cost_per_attempt_s"] = round((a_over or 0) + (g_tot or 0), 3) if (a_over is not None or g_tot is not None) else None
    out["evidence_attempts"] = [r["attempt_json"] for r in rows]
    return out


# ---------------------------------------------------------------- main


def main() -> None:
    tasks_doc = load(TASKS_JSON)
    t52 = [t for t in tasks_doc["tasks"] if t.get("work_group") == "current52"]
    idx = load(INDEX_JSON)
    by_id = {t["instance_id"]: t for t in idx["tasks"]}
    src_name = {"swe_gym": "SWE-Gym", "swe-gym": "SWE-Gym", "swe": "SWE-Gym", "r2e": "R2E"}

    attempt_rows, task_rows = [], []
    for t in t52:
        it = by_id.get(t["instance_id"])
        task = {"instance_id": t["instance_id"], "source": src_name.get(str(t.get("source")).lower(), t.get("source")),
                "repository": (it or {}).get("repository") or t.get("repository")}
        rows = [attempt_row(task, a) for a in (it or {}).get("attempts", [])]
        attempt_rows += rows
        task_rows.append(task_row(task, rows))

    # concurrency: overlap of [actor start, grading end] windows across all attempts
    win = []
    for r in attempt_rows:
        a = ts(r.get("actor_started_at"))
        b = r.get("grading_end_ts") or ts(r.get("actor_finished_at"))
        win.append((a, b))
    for i, r in enumerate(attempt_rows):
        a, b = win[i]
        r["overlapping_jobs"] = (sum(1 for j, (c, d) in enumerate(win) if j != i and a and b and c and d and c < b and d > a)
                                 if a and b else None)

    # ------------------------------------------------ aggregates across tasks (per-task medians)
    def agg(key, rows=task_rows, pred=lambda r: True):
        xs = [r.get(key) for r in rows if pred(r) and r.get(key) is not None]
        return {"n_tasks": len(xs), "median": quantile(xs, 0.5), "p90": quantile(xs, 0.9),
                "min": round(min(xs), 3) if xs else None, "max": round(max(xs), 3) if xs else None}

    keys_actor = ["actor_git_sanitize_s_med", "actor_trusted_init_s_med", "actor_baseline_census_s_med",
                  "actor_network_and_container_s_med", "actor_cc_bootstrap_s_med", "actor_cc_cli_install_s_med",
                  "actor_env_facts_step_s_med", "actor_launch_gap_s_med",
                  "actor_pre_launch_s_med", "actor_time_to_first_model_request_s_med", "actor_post_solve_approx_s_med",
                  "actor_post_quiescence_to_finish_s_med", "actor_non_cc_overhead_s_med", "actor_cc_duration_s_med"]
    keys_grade = ["grading_total_s_med", "grader_git_sanitize_s_med", "grader_trusted_setup_s_med", "install_s_med",
                  "candidate_test_s_med", "grader_other_s_med", "non_model_cost_per_attempt_s"]
    aggregates = {"all": {k: agg(k) for k in keys_actor + keys_grade}}
    for s in ("SWE-Gym", "R2E"):
        aggregates[s] = {k: agg(k, pred=lambda r, s=s: r["source"] == s) for k in keys_actor + keys_grade}
    aggregates["install_s_med_where_install_ran"] = agg("install_s_med", pred=lambda r: not r["install_skipped_all"])

    # share of total non-model time across all attempts with complete evidence
    comp_att = [r for r in attempt_rows if r.get("candidate_segment_completed") and r.get("actor_non_cc_overhead_s") is not None]
    tot = {
        "actor_git_sanitize": sum(r["git_sanitize_s"] or 0 for r in comp_att),
        "actor_trusted_init": sum(r["trusted_init_s"] or 0 for r in comp_att),
        "actor_cc_bootstrap": sum(r["cc_bootstrap_s"] or 0 for r in comp_att),
        "actor_other_non_cc": sum((r["actor_non_cc_overhead_s"] or 0) - (r["git_sanitize_s"] or 0) - (r["trusted_init_s"] or 0)
                                  - (r["cc_bootstrap_s"] or 0) for r in comp_att),
        "grader_git_sanitize": sum(r.get("grader_git_sanitize_s") or 0 for r in comp_att),
        "grader_trusted_setup": sum(r.get("grader_trusted_setup_s") or 0 for r in comp_att),
        "grader_install": sum(r.get("install_s") or 0 for r in comp_att),
        "grader_candidate_test": sum(r.get("candidate_test_s") or 0 for r in comp_att),
    }
    tot["grader_other"] = sum(r.get("grading_total_s") or 0 for r in comp_att) - tot["grader_git_sanitize"] - tot["grader_trusted_setup"] - tot["grader_install"] - tot["grader_candidate_test"]
    grand = sum(tot.values())
    shares = {k: {"seconds": round(v, 1), "share": round(v / grand, 4) if grand else None} for k, v in tot.items()}
    cc_total = sum(r.get("harness_exec_s") or 0 for r in comp_att)

    ranked = sorted([r for r in task_rows if r.get("non_model_cost_per_attempt_s") is not None],
                    key=lambda r: -r["non_model_cost_per_attempt_s"])
    compile_list = [r for r in task_rows if r["compile_class"] in ("needs compile cache", "maybe")]

    coverage = {
        "tasks_in_scope": len(t52),
        "tasks_with_attempts_in_index": sum(1 for t in task_rows if t["n_attempts"] > 0),
        "attempts_total": len(attempt_rows),
        "attempts_with_actor_timings": sum(1 for r in attempt_rows if r.get("git_sanitize_s") is not None),
        "attempts_with_gateway_first_request": sum(1 for r in attempt_rows if r.get("time_to_first_model_request_s") is not None),
        "attempts_with_cc_result_duration": sum(1 for r in attempt_rows if r.get("cc_duration_s") is not None),
        "attempts_with_grading_report": sum(1 for r in attempt_rows if r.get("grading_present")),
        "gradings_candidate_ran": sum(1 for r in attempt_rows if r.get("candidate_segment_completed")),
        "tasks_with_actor_evidence": sum(1 for t in task_rows if t["n_actor_timed"] > 0),
        "tasks_with_any_grading": sum(1 for t in task_rows if t["n_gradings"] > 0),
        "tasks_with_uncensored_grading": sum(1 for t in task_rows if t["n_gradings_candidate_ran"] > 0),
        "tasks_with_both_gradings_uncensored": sum(1 for t in task_rows if t["n_gradings_candidate_ran"] >= 2),
        "missing_or_cut_short": {t["instance_id"]: {"missing": t["missing_grading"], "cut_short": t["gradings_cut_short"]}
                                 for t in task_rows if t["missing_grading"] or t["gradings_cut_short"]},
        "grading_permission_modes": dict(Counter(r.get("grading_permission_mode") for r in attempt_rows if r.get("grading_present"))),
        "gradings_on_same_image_as_actor": sum(1 for r in attempt_rows if r.get("grading_image_same_as_actor")),
        "post_quiescence_to_finish_over_30s": [f"{r['job_id']}:{r.get('post_quiescence_to_finish_s')}" for r in attempt_rows
                                               if (r.get("post_quiescence_to_finish_s") or 0) > 30],
        "grading_image_pull_s_nonzero": sum(1 for r in attempt_rows if (r.get("grading_image_pull_s") or 0) > 0),
        "actor_image_ready_s_max": max((r.get("image_ready_s") or 0) for r in attempt_rows),
        "eval_logs_with_network_downloads": sum(1 for r in attempt_rows if (r.get("evl_downloads") or 0) > 0),
        "overlapping_jobs_max": max((r.get("overlapping_jobs") or 0) for r in attempt_rows),
        "attempts_with_any_overlap": sum(1 for r in attempt_rows if (r.get("overlapping_jobs") or 0) > 0),
    }

    summary = {
        "schema": "rh2.env_pipeline_cost_analysis.v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {"tasks": TASKS_JSON, "attempt_index": INDEX_JSON,
                   "evidence_root": "runs/ordinary_gpu_probe_20261002/{remote,closed_snapshots}/…/results/<job_id>/"},
        "definitions": {
            "pre_launch_s": "agent_env_facts 阶段时刻 − attempt started_at，再加 launch_facts.bootstrap_seconds（CC CLI 安装 + agent 用户初始化）；不含未计时的求解前 pip freeze",
            "time_to_first_model_request_s": "网关第一条请求 ts − attempt started_at（含 CC 进程启动）",
            "actor_non_cc_overhead_s": "actor 墙钟（finished_at − started_at）− harness_log.seconds（CC 执行）；actor 侧全部非模型时间，含求解后导出与清理",
            "grading medians": "只对候选段实际运行的评分取中位数；中途被截断（超时）的评分单列",
            "non_model_cost_per_attempt_s": "actor_non_cc_overhead_s_med + grading_total_s_med（每次尝试的非模型开销）",
            "compile_class": f"needs compile cache = 安装段出现 C/C++/Cython 编译且安装中位数 > {COMPILE_CACHE_INSTALL_THRESHOLD_S:.0f}s；maybe = 有编译但较短；no = 无编译行；'no (install skipped)' = 安装段被跳过",
            "quantiles": "先取逐题中位数，再跨题取 median/p90（线性插值）",
        },
        "coverage": coverage,
        "aggregates_across_tasks": aggregates,
        "non_model_time_shares_all_complete_attempts": {"n_attempts": len(comp_att), "components": shares,
                                                         "total_non_model_s": round(grand, 1),
                                                         "cc_exec_total_s_same_attempts": round(cc_total, 1)},
        "ranking_non_model_cost_per_attempt": [
            {k: r.get(k) for k in ("instance_id", "source", "repository", "non_model_cost_per_attempt_s",
                                   "actor_non_cc_overhead_s_med", "actor_git_sanitize_s_med", "actor_trusted_init_s_med",
                                   "grading_total_s_med", "grader_trusted_setup_s_med", "grader_git_sanitize_s_med",
                                   "install_s_med", "candidate_test_s_med", "actor_cc_duration_s_med", "n_gradings_candidate_ran")}
            for r in ranked],
        "compile_cache_candidates": [
            {k: r.get(k) for k in ("instance_id", "repository", "compile_class", "compile_basis", "install_s_med",
                                   "evl_compiler_compile_max", "evl_compiler_link_max", "evl_extensions_built_max",
                                   "evl_cython_steps_max", "evl_install_commands", "candidates_touching_native_sources")}
            for r in compile_list],
        "native_code_but_no_grading_compile": [
            {k: r.get(k) for k in ("instance_id", "repository", "compile_class", "intree_native_binaries",
                                   "intree_native_sources", "candidates_touching_native_sources")}
            for r in task_rows if r["compile_class"].startswith("no") and (r["intree_native_binaries"] or 0) > 0],
    }

    # ------------------------------------------------ write outputs
    def dump(name, obj):
        (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")

    dump("per_attempt.json", attempt_rows)
    dump("per_task.json", task_rows)
    dump("summary.json", summary)

    def write_csv(name, rows, cols):
        with open(HERE / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for r in rows:
                w.writerow([json.dumps(r.get(c), ensure_ascii=False) if isinstance(r.get(c), (list, dict)) else r.get(c) for c in cols])

    acols = ["instance_id", "source", "repository", "job_id", "model", "termination", "actor_wall_s",
             "image_ready_s", "network_and_container_s", "git_sanitize_s", "git_sanitize_inner_s", "git_history_count",
             "trusted_init_s", "baseline_census_s", "baseline_archive_s", "start_to_env_facts_s", "cc_bootstrap_s",
             "cc_cli_install_s", "agent_user_init_s", "pre_launch_s", "time_to_first_model_request_s", "launch_gap_s",
             "env_facts_step_s", "harness_exec_s", "cc_duration_s", "cc_num_turns", "post_solve_approx_s",
             "post_quiescence_to_finish_s", "actor_non_cc_overhead_s", "quiescence_s", "job_wall_s",
             "overlapping_jobs", "grading_present", "grading_outcome", "grading_failure_category", "grading_infra_detail",
             "grading_total_s", "grading_env_reset_s", "grader_git_sanitize_s", "grader_start_and_verify_s",
             "grader_trusted_setup_s", "grader_baseline_rebuild_s", "grader_delta_apply_s", "grader_candidate_phase_s",
             "install_s", "install_skipped", "candidate_test_s", "grader_other_s", "install_failed_commands",
             "grading_image_pull_s", "grading_permission_mode", "grading_image_same_as_actor", "evl_compiler_compile", "evl_compiler_link", "evl_extensions_built",
             "evl_cython_steps", "evl_ninja_steps", "evl_downloads", "evl_wheels_built", "evl_install_wall_from_ts_s",
             "intree_native_binaries", "intree_native_sources", "candidate_native_source_files", "attempt_json", "eval_log"]
    write_csv("per_attempt.csv", attempt_rows, acols)
    tcols = ["instance_id", "source", "repository", "n_attempts", "n_gradings", "n_gradings_candidate_ran",
             "actor_git_sanitize_s_med", "actor_trusted_init_s_med", "actor_baseline_census_s_med",
             "actor_network_and_container_s_med", "actor_cc_bootstrap_s_med", "actor_pre_launch_s_med",
             "actor_time_to_first_model_request_s_med", "actor_post_solve_approx_s_med",
             "actor_post_quiescence_to_finish_s_med", "actor_non_cc_overhead_s_med", "actor_cc_duration_s_med",
             "grading_total_s_med", "grader_git_sanitize_s_med", "grader_trusted_setup_s_med", "install_s_med",
             "candidate_test_s_med", "grader_other_s_med", "non_model_cost_per_attempt_s", "grading_permission_modes",
             "grading_image_same_as_actor_all", "compile_class",
             "compile_basis", "evl_compiler_compile_max", "evl_extensions_built_max", "evl_cython_steps_max",
             "install_skipped_all", "intree_native_binaries", "candidates_touching_native_sources", "git_history_count",
             "gradings_cut_short", "missing_grading", "gradings_other_flags"]
    write_csv("per_task.csv", task_rows, tcols)

    # markdown table
    def f(x, nd=0):
        return "–" if x is None else (f"{x:.{nd}f}" if isinstance(x, (int, float)) else str(x))

    lines = ["# 52 题探针：逐题环境准备与评分开销", "",
             f"生成于 {summary['generated_at']}（analyze_env_costs.py，只读 GPU 探针证据）。",
             "单位秒；actor 列为可用尝试的中位数，评分列为候选段实际运行的评分的中位数。",
             "列：GS=actor git_sanitize，TI=actor trusted_init（chown -R /testbed），Cen=baseline_census，Net=network_and_container，",
             "Boot=CC 引导（CLI 安装 + agent 用户初始化），Pre=启动前合计，TTFR=到第一条模型请求，",
             "Ovh=actor 非 CC 开销，CC=CC 求解时长，Gtot=评分合计，gGS=评分侧 git sanitize，",
             "Setup=评分可信 setup（官方测试恢复 + 权限交接），Inst=安装，Test=候选测试，",
             "Cost=Ovh+Gtot，n_g=未截断评分数 / 评分数。", "",
             "| task | src | GS | TI | Cen | Net | Boot | Pre | TTFR | Ovh | CC | Gtot | gGS | Setup | Inst | Test | Cost | n_g | compile |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for r in sorted(task_rows, key=lambda r: -(r.get("non_model_cost_per_attempt_s") or 0)):
        lines.append("| " + " | ".join([
            r["instance_id"][:48], "SWE" if r["source"] == "SWE-Gym" else "R2E",
            f(r.get("actor_git_sanitize_s_med"), 1), f(r.get("actor_trusted_init_s_med"), 1), f(r.get("actor_baseline_census_s_med"), 1),
            f(r.get("actor_network_and_container_s_med"), 1), f(r.get("actor_cc_bootstrap_s_med"), 1), f(r.get("actor_pre_launch_s_med"), 1),
            f(r.get("actor_time_to_first_model_request_s_med"), 1), f(r.get("actor_non_cc_overhead_s_med"), 1), f(r.get("actor_cc_duration_s_med"), 0),
            f(r.get("grading_total_s_med"), 1), f(r.get("grader_git_sanitize_s_med"), 1), f(r.get("grader_trusted_setup_s_med"), 1),
            ("skip" if r.get("install_skipped_all") else f(r.get("install_s_med"), 1)), f(r.get("candidate_test_s_med"), 1),
            f(r.get("non_model_cost_per_attempt_s"), 0), f"{r['n_gradings_candidate_ran']}/{r['n_gradings']}", r["compile_class"],
        ]) + " |")
    # summary sections
    cov = coverage
    lines += ["", "## 覆盖率", "",
              f"- 题目 {cov['tasks_in_scope']}（SWE-Gym 34，R2E 18）；尝试 {cov['attempts_total']}；actor 计时 {cov['attempts_with_actor_timings']}/106；"
              f"网关首请求 {cov['attempts_with_gateway_first_request']}/106；评分报告 {cov['attempts_with_grading_report']}/106；"
              f"候选段实际运行的评分 {cov['gradings_candidate_ran']}/105。",
              f"- 两次评分都未截断的题 {cov['tasks_with_both_gradings_uncensored']}/52；缺失或截断："
              + "；".join(f"{k}（{', '.join(v['missing'] + v['cut_short'])}）" for k, v in cov["missing_or_cut_short"].items()),
              f"- 评分权限路径：{cov['grading_permission_modes']}（GPU frozen_code_v6–v9 无 prepared_image.py / performance.py）。",
              f"- 时间重叠的作业数最大 {cov['overlapping_jobs_max']}（严格串行）。安装日志中的网络下载：{cov['eval_logs_with_network_downloads']}。",
              "", "## 跨题汇总（逐题中位数 → 跨题 median / p90）", "",
              "| metric | all n | all median | all p90 | SWE median | SWE p90 | R2E median | R2E p90 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k in keys_actor + keys_grade:
        a, s_, r_ = aggregates["all"][k], aggregates["SWE-Gym"][k], aggregates["R2E"][k]
        lines.append(f"| {k} | {a['n_tasks']} | {f(a['median'], 1)} | {f(a['p90'], 1)} | {f(s_['median'], 1)} | {f(s_['p90'], 1)} | {f(r_['median'], 1)} | {f(r_['p90'], 1)} |")
    lines += ["", f"## 非模型时间构成（{len(comp_att)} 次评分完整的尝试；同批 CC 执行合计 {cc_total:.0f}s）", ""]
    for k, v in shares.items():
        lines.append(f"- {k}: {v['seconds']:.0f}s ({100 * v['share']:.1f}%)")
    lines += ["", "## 编译缓存分类", ""]
    for r in task_rows:
        if r["compile_class"] in ("needs compile cache", "maybe"):
            lines.append(f"- {r['instance_id']}: {r['compile_class']} — {r['compile_basis']}; link={r['evl_compiler_link_max']}; "
                         f"改动原生源码的候选：{r['candidates_touching_native_sources'] or '无'}")
    nat = [r for r in task_rows if r["compile_class"].startswith("no (install") and (r["intree_native_binaries"] or 0) > 0]
    lines.append(f"- 仓库内有原生二进制、但评分安装段被跳过的 R2E 题（候选的 C/Cython 改动不会被评分侧重编）："
                 + ", ".join(f"{r['instance_id'][:24]}({r['intree_native_binaries']} .so)" for r in nat))
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"coverage": coverage, "shares": shares}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
