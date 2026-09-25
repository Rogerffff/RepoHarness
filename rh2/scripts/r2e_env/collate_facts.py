#!/usr/bin/env python3
"""R2E 48 题环境审查：只读汇总器（facts.json）。

把已有证据归到"一题一份"的事实文件里，供环境审查 / 修复的 sub-agent 与验收者直接消费；**只归纳，不重跑、
不改原账本、不裁定 reward 或题目去留**（对应 environment_screening_definition_20260915.md 里 facts.json 的定义）。

输入（全部只读）：
- `--repo-root`：可信摄入面（`s2_r2e/`，经 `load_trusted_r2e_ingest_outputs` 三级 pin 校验）——题目身份、期望映射、
  入口脚本、隐藏测试清单、题面；
- `--evidence-root`：R-f 真机证据目录（`runs/r2e_rf_20260923/`）——`remote/ledger_r2e_*.jsonl` 账本（含 noop / gold /
  reps / requal / numpy_bigtmp，不含错误对照 contrast*）、`remote/eval_logs_r2e/` 原始日志与 sidecar、
  `remote/r2e_derived/<iid>/facts.json` 派生镜像 21 项复核、`reconcile_all/reconcile.json` 逐键对账；
- `--extra-evidence <local_dir>=<remote_prefix>`（可重复）：额外账本目录（如 09-24 中央复跑），其账本 `ledger_{noop,gold}.jsonl`
  与日志按前缀映射到本地；
- `--m3-root`（可选）：09-16 M3 来源镜像事实（`facts/<commit12>/{interp.txt,pkgsrc.txt,image_summary.txt}`）——
  Python 版本、来源解释器路径、包导入方式（editable finder / 路径项）、"cwd 不在 /testbed 时能否导入"。

输出：`<out-dir>/<instance_id>/facts.json`（schema `rh2.r2e_env_facts.v1`）+ `<out-dir>/summary.json` + 可选 `--summary-md`。
账本里的绝对路径统一改写成**相对仓库根**的引用（`runs/…`）；facts 里不出现本机私有路径。

自动检查项（只填能由既有证据机械判定的项，其余留给 sub-agent）：R01 身份对应、R02 初态含问题、R08 候选代码生效、
R12 资源余量、R13 重复一致性、R15 参考解析一致、R16 分差键集合。状态词汇 pass / issue / unknown / not_applicable。
"""

from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "src"))

from repoharness2.adapters.slime.r2e_grading_scripts import _R2E_IMPORT_PROBE_MODULES  # noqa: E402
from repoharness2.envpack import scoring  # noqa: E402
from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs  # noqa: E402


FACTS_SCHEMA_ID = "rh2.r2e_env_facts.v1"
LEDGER_GLOB_NAMES = ("ledger_r2e_all_*.jsonl", "ledger_r2e_reps_*.jsonl", "ledger_r2e_requal_*.jsonl", "ledger_r2e_numpy_bigtmp_*.jsonl")
REMOTE_REPLAY_PREFIX = "/work/replay/"


class Evidence:
    """证据根解析：账本里的路径（远端绝对路径或本机绝对路径）→ 本地文件 + 相对仓库根的引用。

    主根 `runs/r2e_rf_<date>/`（远端 `/work/replay/` ↔ `<root>/remote/`）；`--extra-evidence <local_dir>=<remote_prefix>`
    可加任意个（如 09-24 中央复跑 `runs/r2e_env_repair_20260924/_rerun2/` ↔ `/work/envrepair/_rerun2/`）。"""

    def __init__(self, repo_root: Path, main_root: Path, extras: list[tuple[Path, str]]) -> None:
        self.repo_root = repo_root.resolve()
        self.main_root = main_root.resolve()
        self.maps: list[tuple[str, Path]] = [(REMOTE_REPLAY_PREFIX, self.main_root / "remote")] + [(pre, d.resolve()) for d, pre in extras]

    def local(self, path: str | None) -> Path | None:
        if not path:
            return None
        for prefix, local_dir in self.maps:
            if path.startswith(prefix):
                return local_dir / path[len(prefix):]
        return Path(path)

    def ref(self, path: str | None) -> str | None:
        p = self.local(path)
        if p is None:
            return None
        try:
            return str(p.resolve().relative_to(self.repo_root))
        except ValueError:
            return p.name

    def ref_of(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.repo_root))
        except ValueError:
            return p.name

    def read(self, path: str | None) -> str | None:
        p = self.local(path)
        return p.read_text(encoding="utf-8", errors="replace") if p is not None and p.is_file() else None

    def ledger_dirs(self) -> list[Path]:
        return [local_dir for _, local_dir in self.maps]
MEMORY_HEADROOM_WARN = 0.6  # 峰值内存 / 限额 超过它就标 memory_headroom_low
_STATUS_LINE_RE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(.*)$")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")  # 原因行提取前去色（pillow 日志带颜色；P4 09-24）；只影响诊断字段，不影响判分


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _summary_reasons(log_text: str | None) -> dict[str, str]:
    """pytest short summary 段里非 PASSED 行的原因（键归一化与 parse_log_pytest 相同）。"""

    if not log_text:
        return {}
    seg = log_text
    if scoring.R2E_EVAL_START_MARKER in seg:
        seg = seg.split(scoring.R2E_EVAL_START_MARKER, 1)[1]
    if scoring.R2E_EVAL_END_MARKER in seg:
        seg = seg.split(scoring.R2E_EVAL_END_MARKER, 1)[0]
    if "short test summary info" not in seg:
        return {}
    out: dict[str, str] = {}
    for raw_line in seg.split("short test summary info")[1].strip().split("\n"):
        line = _ANSI_RE.sub("", raw_line)
        m = _STATUS_LINE_RE.match(line.strip())
        if not m or m.group(1) not in ("FAILED", "ERROR"):
            continue  # 期望映射只含 PASSED / FAILED / ERROR；SKIPPED 等不参与判分
        rest = m.group(2)
        nodeid, _, reason = rest.partition(" - ")
        parts = nodeid.split("::")
        key = ".".join(parts[1:]) if len(parts) > 1 else line.strip().split(" - ")[0]
        out[key.strip()] = f"{m.group(1)}: {reason.strip()}" if reason else m.group(1)
    return out


def _dirty_tree_lines(log_text: str | None) -> list[str]:
    """可信 setup 开头的 `git status --short | head -n 200` 输出（候选应用后、隐藏测试恢复前的工作区状态）。"""

    if not log_text:
        return []
    head = log_text.split("RH2_SETUP_HIDDEN_TESTS_TREE=", 1)[0]
    return [l for l in head.splitlines() if re.match(r"^([ MADRCU?!]{2})\s", l)][:200]


def _runner_kind(run_tests_sh: str) -> str:
    cmds = [l for l in run_tests_sh.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    body = " ".join(cmds)
    if "-m pytest" not in body:
        return "custom"
    return "xvfb_pytest" if "xvfb-run" in body else "pytest"


def _runner_prefix(run_tests_sh: str) -> str:
    """入口脚本里解释器之前的部分（环境变量赋值 + xvfb-run 等），给开发条件探针复用。"""

    cmds = [l for l in run_tests_sh.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    body = " ".join(cmds)
    return body.split(".venv/bin/python", 1)[0].strip() if ".venv/bin/python" in body else ""


def _m3_facts(m3_root: Path | None, commit12: str) -> dict:
    out = {"available": False}
    if m3_root is None:
        return out
    d = m3_root / "facts" / commit12
    if not d.is_dir():
        return out
    out["available"] = True
    interp = (d / "interp.txt").read_text(errors="replace") if (d / "interp.txt").is_file() else ""
    m = re.search(r"^version_info\s*=\s*(\S+)", interp, re.M)
    out["python_version"] = m.group(1) if m else None
    lines = interp.splitlines()
    out["interpreter_source_path"] = lines[1].split()[0] if len(lines) > 1 and lines[1].startswith("/") else None
    pkgsrc = (d / "pkgsrc.txt").read_text(errors="replace") if (d / "pkgsrc.txt").is_file() else ""

    def _section(marker: str) -> list[str]:
        """标记之后、下一个 `###` 之前的非空行（DataLad 会先打一行 git 身份警告，不能只取第一行——P2 09-24）。"""
        if marker not in pkgsrc:
            return []
        rest = pkgsrc.split(marker, 1)[1]
        body = rest.split("\n###", 1)[0]
        return [l.strip() for l in body.splitlines() if l.strip()]

    def _after(marker: str) -> str | None:
        lines = _section(marker)
        return lines[0] if lines else None

    tmp_lines = _section("### import from /tmp (cwd=/tmp)")
    frm_tmp = next((l for l in tmp_lines if l.startswith("/")), None) or (tmp_lines[-1] if tmp_lines else None)
    out["import_from_tmp_m3"] = frm_tmp
    if not tmp_lines:
        out["import_outside_testbed_ok_m3"] = None
    elif any(l.startswith("/testbed") for l in tmp_lines):
        out["import_outside_testbed_ok_m3"] = True
    elif any("Error" in l for l in tmp_lines):
        out["import_outside_testbed_ok_m3"] = False
    else:
        out["import_outside_testbed_ok_m3"] = None
    pth = _after("### pth targets") or ""
    if "__editable__" in pth:
        out["install_mode"] = "editable_finder"
    elif pth.startswith("/testbed"):
        out["install_mode"] = "path_entry"
    else:
        out["install_mode"] = "unknown"
    out["pth_line"] = pth[:120] if pth else None
    return out


def _load_ledgers(ev: Evidence) -> dict[str, list[dict]]:
    rows_by_iid: dict[str, list[dict]] = collections.defaultdict(list)
    seen: set[str] = set()
    for d in ev.ledger_dirs():
        for pat in LEDGER_GLOB_NAMES + ("ledger_noop.jsonl", "ledger_gold.jsonl"):
            for p in sorted(glob.glob(str(d / pat))):
                if p.endswith("_local.jsonl") or p.endswith("_local_local.jsonl"):
                    continue  # 同内容、路径改写版；用远端原版 + 统一映射
                _load_ledger_file(Path(p), rows_by_iid, seen)
    return rows_by_iid


def _load_ledger_file(p: Path, rows_by_iid: dict[str, list[dict]], seen: set[str]) -> None:
    if True:
        if True:
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                rid = (r.get("report") or {}).get("report_id") or f"{p}:{r.get('instance_id')}:{r.get('attempt')}"
                if rid in seen:
                    continue
                seen.add(rid)
                r["_ledger"] = p.name
                rows_by_iid[r["instance_id"]].append(r)


def _run_entry(ev: Evidence, r: dict) -> dict:
    rep = r.get("report") or {}
    vd = r.get("verdict_diagnostics") or {}
    em = vd.get("expected_match") or {}
    ph = r.get("phases") or {}
    pol = r.get("policy") or {}
    obs = r.get("observations") or {}
    log_rel = ev.ref((r.get("log") or {}).get("path"))
    log_text = ev.read((r.get("log") or {}).get("path"))
    grader_total = sum(v for v in ph.values() if isinstance(v, (int, float)))
    return {
        "run_id": r.get("run_id"), "ledger": r.get("_ledger"), "kind": (r.get("candidate") or {}).get("kind"),
        "attempt": r.get("attempt"), "started_at_utc": r.get("started_at_utc"),
        "stage_error": r.get("stage_error"),
        "reward": rep.get("reward"), "outcome": rep.get("outcome"), "failure_category": rep.get("failure_category"),
        "grader_version": rep.get("grader_version"),
        "expected_match": rep.get("expected_match"), "expected_total": rep.get("expected_total"),
        "num_parsed_tests": vd.get("num_parsed_tests"), "resolution": vd.get("resolution"),
        "mismatched": em.get("mismatched"), "missing": em.get("missing"), "unexpected": em.get("unexpected"),
        "test_rc": (r.get("test") or {}).get("rc"), "test_seconds": (r.get("test") or {}).get("seconds"),
        "setup_seconds": ph.get("grader_trusted_setup"), "grader_seconds_total": round(grader_total, 3),
        "mem_peak_mb": (r.get("resource") or {}).get("mem_peak_mb"),
        "policy": {"cpus": pol.get("cpus"), "memory_bytes": pol.get("memory_bytes"), "tmpfs_bytes": pol.get("tmpfs_bytes"),
                   "pids_limit": pol.get("pids_limit"), "shm_bytes": pol.get("shm_bytes")},
        "image_id_actual": r.get("image_id_actual"),
        "import_path_grader": obs.get("RH2_OBS_IMPORT_PATH"), "pkg_version_grader": obs.get("RH2_OBS_PKG_VERSION"),
        "runner_integrity_changed": r.get("runner_integrity_changed"),
        "cleanup_removed": (r.get("cleanup") or {}).get("removed"), "log_partial": (r.get("log") or {}).get("partial"),
        "eval_log": log_rel, "diagnostics": ev.ref(r.get("diagnostics_ref")),
        "non_passed_reasons": _summary_reasons(log_text),
        "dirty_tree_lines": _dirty_tree_lines(log_text),
        "gold_included_paths": (r.get("projection") or {}).get("included_paths"),
    }


def _latest(runs: list[dict], kind: str, *, run_prefix: str = "r2e-rf-all") -> dict | None:
    cands = [x for x in runs if x["kind"] == kind and (x.get("run_id") or "").startswith(run_prefix) and not x.get("stage_error")]
    return sorted(cands, key=lambda x: x.get("started_at_utc") or "")[-1] if cands else None


def _reconcile_for(recon: list[dict], iid: str, recon_ref: str = "reconcile.json") -> list[dict]:
    out = []
    for e in recon:
        if e.get("instance_id") != iid:
            continue
        out.append({
            "kind": e.get("kind"), "ledger": Path(e.get("ledger") or "").name, "agree": e.get("agree"),
            "reward_equal": e.get("reward_equal"), "diff_sets_equal": e.get("diff_sets_equal"),
            "observed_maps_equal": e.get("observed_maps_equal"),
            "reference_ledger_consistent": e.get("reference_ledger_consistent"),
            "reference_log_count": len(e.get("reference_logs") or []), "notes": e.get("notes") or e.get("note"),
            "reference_prime_rewards": [c.get("reference_prime_reward") for c in e.get("comparisons") or []],
            "ref": recon_ref,
        })
    return out


def _auto_checks(identity_ok: list[str], noop: dict | None, gold: dict | None, runs: list[dict], recon: list[dict],
                 derived_ok: bool | None, derived_ref: str = "") -> tuple[dict, list[str]]:
    checks: dict = {}
    flags: list[str] = []

    def put(cid: str, status: str, note: str, refs: list[str]) -> None:
        checks[cid] = {"status": status, "note": note, "evidence_refs": refs, "by": "collate_facts.py"}

    # R01 身份对应
    if derived_ok is None:
        put("R01_identity", "unknown", "缺派生镜像 facts.json", [])
    elif derived_ok and not identity_ok:
        put("R01_identity", "pass", "派生镜像 21 项复核通过；覆盖表 / 隐藏测试树 / 入口脚本 / HEAD 与评分面一致", [derived_ref])
    else:
        put("R01_identity", "issue", "; ".join(identity_ok) or "派生镜像复核未通过", [derived_ref])

    # R02 初态含问题（noop 的 0 必须来自目标测试的 mismatched，而不是零解析 / 缺席）
    if noop is None:
        put("R02_noop_shows_problem", "unknown", "无有效 noop 行", [])
    elif noop["reward"] == 0 and (noop["num_parsed_tests"] or 0) > 0 and not noop["missing"] and noop["mismatched"]:
        put("R02_noop_shows_problem", "pass", f"noop 0 来自 {len(noop['mismatched'])} 个 mismatched 键（无 missing、无零解析）", [noop["eval_log"]])
    elif noop["reward"] == 0:
        put("R02_noop_shows_problem", "issue", f"noop 0 但 parsed={noop['num_parsed_tests']} missing={len(noop['missing'] or [])}", [noop["eval_log"]])
        flags.append("noop_zero_not_from_target")
    else:
        put("R02_noop_shows_problem", "issue", f"noop reward={noop['reward']}（初态已通过？）", [noop["eval_log"]])
        flags.append("noop_nonzero")

    # R08 候选代码生效（grader 侧导入路径在 /testbed；gold 达到来源定义）
    if gold is None:
        put("R08_candidate_code_effective", "unknown", "无有效 gold 行", [])
    else:
        imp = gold.get("import_path_grader") or ""
        if not imp.startswith("/testbed"):
            put("R08_candidate_code_effective", "issue", f"gold 后导入路径不在 /testbed: {imp!r}", [gold["diagnostics"] or gold["eval_log"]])
            flags.append("import_outside_testbed")
        elif gold["reward"] == 1:
            put("R08_candidate_code_effective", "pass", f"导入 {imp}；gold {gold['expected_match']}/{gold['expected_total']}", [gold["eval_log"]])
        else:
            put("R08_candidate_code_effective", "unknown", f"导入 {imp} 但 gold reward={gold['reward']}（mismatched={gold['mismatched']}）——需人工归因", [gold["eval_log"]])
            flags.append("gold_zero")

    # R12 资源余量（默认 profile 下的峰值内存 / 限额；tmpfs 只能靠日志判断）
    if gold is None:
        put("R12_resources", "unknown", "无 gold 行", [])
    else:
        lim = (gold["policy"] or {}).get("memory_bytes") or 0
        peak = gold.get("mem_peak_mb") or 0
        ratio = round(peak * 1024 * 1024 / lim, 3) if lim else None
        note = f"峰值 {peak:.0f} MB / 限额 {lim / 2**30:.0f} GiB = {ratio}; setup {gold['setup_seconds']:.0f}s test {gold['test_seconds']:.0f}s"
        status = "pass"
        if ratio is not None and ratio > MEMORY_HEADROOM_WARN:
            status, note = "issue", note + "（提示：memory.peak 含 chown 产生的可回收页缓存，不等于资源需求；P3 实测 orange3 2 GiB 限额仍通过——需人工判定）"
            flags.append("memory_headroom_low")
        bigger = [x for x in runs if x["kind"] == "gold" and (x["policy"] or {}).get("tmpfs_bytes", 0) > (gold["policy"] or {}).get("tmpfs_bytes", 0)]
        if gold["reward"] != 1 and any(x["reward"] == 1 for x in bigger):
            status = "issue"
            note += "；默认 profile gold=0、放大 /tmp+内存后 gold=1 → 需逐题资源配方"
            flags.append("resource_recipe_required")
        put("R12_resources", status, note, [gold["diagnostics"] or gold["eval_log"]])

    # R13 重复一致性（同 profile 的多次 RH2 运行：reward 与 mismatched 集合逐条相同）
    for kind in ("noop", "gold"):
        same = [x for x in runs if x["kind"] == kind and not x.get("stage_error") and x.get("reward") is not None]
        by_policy: dict[tuple, list[dict]] = collections.defaultdict(list)
        for x in same:
            by_policy[(x["policy"]["memory_bytes"], x["policy"]["tmpfs_bytes"])].append(x)
        groups = [g for g in by_policy.values() if len(g) >= 2]
        cid = f"R13_repeat_{kind}"
        if not groups:
            put(cid, "unknown", f"{kind} 同条件只有 {len(same)} 次运行（R-f 每题 1 次；复跑后再判）", [x["eval_log"] for x in same if x["eval_log"]])
            continue
        bad = []
        for g in groups:
            sig = {(x["reward"], tuple(sorted(x["mismatched"] or [])), tuple(sorted(x["missing"] or []))) for x in g}
            if len(sig) > 1:
                bad.append(g)
        if bad:
            put(cid, "issue", f"{kind} 同条件运行结果不一致", [x["eval_log"] for g in bad for x in g])
            flags.append(f"repeat_inconsistent_{kind}")
        else:
            n = sum(len(g) for g in groups)
            put(cid, "pass", f"{kind} 同条件 {n} 次 reward 与差异集合一致", [x["eval_log"] for g in groups for x in g if x["eval_log"]])

    # R15 参考解析一致（与 M3 / 09-09 独立 runner 逐键对账）
    if not recon:
        put("R15_reference_parse", "unknown", "无对账行", [])
    elif all(e["agree"] for e in recon):
        put("R15_reference_parse", "pass", f"{len(recon)} 行 agree（reward、差异集合、观测映射逐键相同）", [recon[0]["ref"]])
    else:
        notes = [f"{e['kind']}: reward_equal={e['reward_equal']} diff_sets_equal={e['diff_sets_equal']} maps_equal={e['observed_maps_equal']} ref_rewards={e['reference_prime_rewards']}" for e in recon if not e["agree"]]
        put("R15_reference_parse", "issue", "; ".join(notes)[:400], [recon[0]["ref"]])
        flags.append("reference_disagreement")

    # R16 分差键集合（noop mismatched 且 gold 通过 = 目标测试）
    if noop and gold:
        target = sorted(set(noop["mismatched"] or []) - set(gold["mismatched"] or []))
        leftover = sorted(set(gold["mismatched"] or []))
        put("R16_f2p_keys", "pass" if target and not leftover else ("issue" if leftover else "unknown"),
            f"目标键 {len(target)}：{target[:8]}{'…' if len(target) > 8 else ''}" + (f"；gold 仍不符 {leftover}" if leftover else ""),
            [noop["eval_log"], gold["eval_log"]])
    else:
        put("R16_f2p_keys", "unknown", "缺 noop 或 gold", [])
    return checks, flags


def build(args: argparse.Namespace) -> dict:
    repo_root = Path(args.repo_root).resolve()
    evidence_root = Path(args.evidence_root).resolve()
    extras: list[tuple[Path, str]] = []
    for item in args.extra_evidence or []:
        local, _, prefix = item.partition("=")
        if not local or not prefix.startswith("/"):
            raise SystemExit(f"--extra-evidence 需要 <local_dir>=<remote_prefix>: {item!r}")
        extras.append((Path(local), prefix if prefix.endswith("/") else prefix + "/"))
    ev = Evidence(repo_root, evidence_root, extras)
    m3_root = Path(args.m3_root).resolve() if args.m3_root else None
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    trusted = load_trusted_r2e_ingest_outputs(repo_root)
    grading = {b.instance_id: b for b in trusted.result.grading_bundles}
    public = {b.instance_id: b for b in trusted.result.public_bundles}
    packages = {p.instance_id: p for p in trusted.result.packages}
    image_facts = {f.commit_hash: f for f in trusted.image_facts.values()}

    ledgers = _load_ledgers(ev)
    recon_path = evidence_root / "reconcile_all" / "reconcile.json"
    recon = json.loads(recon_path.read_text(encoding="utf-8")) if recon_path.is_file() else []
    recon_ref = ev.ref_of(recon_path)
    prompts: dict[str, str] = {}
    pp = evidence_root / "remote" / "prepared_r2e" / "prompts.jsonl"
    if pp.is_file():
        for line in pp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                prompts[row["metadata"]["instance_id"]] = row["prompt"]

    generator = {"script": str(HERE.relative_to(repo_root)) if HERE.is_relative_to(repo_root) else HERE.name, "sha256": _sha256_file(HERE)}
    summary_rows = []
    for iid in sorted(grading):
        g = grading[iid]
        pub = public[iid]
        pkg = packages[iid]
        commit12 = g.source_commit_hash[:12]
        derived_path = evidence_root / "remote" / "r2e_derived" / iid / "facts.json"
        derived_ref = ev.ref_of(derived_path)
        derived = json.loads(derived_path.read_text(encoding="utf-8")) if derived_path.is_file() else None
        overlay = (derived or {}).get("overlay") or {}
        root_facts = (derived or {}).get("root_facts") or {}
        expected = json.loads(g.expected_output_json)
        counts = dict(collections.Counter(expected.values()))
        runs = [_run_entry(ev, r) for r in sorted(ledgers.get(iid, []), key=lambda r: r.get("started_at_utc") or "")]
        noop, gold = _latest(runs, "noop"), _latest(runs, "gold")
        m3 = _m3_facts(m3_root, commit12)
        module = _R2E_IMPORT_PROBE_MODULES.get(g.repo_key_lower, g.repo_key_lower)

        identity_issues: list[str] = []
        if derived:
            if overlay.get("base_image_manifest_digest") != pkg.image_manifest_digest:
                identity_issues.append("overlay.base_image_manifest_digest != package")
            if (overlay.get("facts") or {}).get("hidden_tests_tree_sha256") != g.hidden_tests_tree_sha256:
                identity_issues.append("hidden_tests_tree_sha256 != grading bundle")
            if root_facts.get("run_tests_sh") != g.run_tests_sh_sha256.removeprefix("sha256:"):
                identity_issues.append("run_tests.sh sha != grading bundle")
            if root_facts.get("head") != g.base_commit:
                identity_issues.append("HEAD != base_commit")
        checks, flags = _auto_checks(identity_issues, noop, gold, runs, _reconcile_for(recon, iid, recon_ref),
                                     (derived or {}).get("ok") if derived else None, derived_ref)

        runner_kind = _runner_kind(g.run_tests_sh)
        if runner_kind != "pytest":
            flags.append(runner_kind)
        non_passed = {k: v for k, v in expected.items() if v != "PASSED"}
        if non_passed:
            flags.append("expected_has_non_passed_keys")
        dirty = (noop or gold or {}).get("dirty_tree_lines") or []
        if len(dirty) > 2:
            flags.append("dirty_tree_gt2")
        if m3.get("import_outside_testbed_ok_m3") is False:
            flags.append("testbed_must_be_on_sys_path")

        facts = {
            "schema_id": FACTS_SCHEMA_ID, "generated_at_utc": _now(), "generator": generator,
            "evidence_roots": [ev.ref_of(evidence_root)] + [ev.ref_of(d) for d, _ in extras], "m3_root": ev.ref_of(m3_root) if m3_root else None,
            "identity": {
                "task_id": pkg.task_id, "instance_id": iid, "repo": g.repo, "module": module,
                "base_commit": g.base_commit, "source_commit_hash": g.source_commit_hash,
                "base_image_ref": pkg.image, "base_image_manifest_digest": pkg.image_manifest_digest,
                "derived_image_ref": overlay.get("derived_image_ref"), "derived_image_id": overlay.get("derived_image_id"),
                "recipe_id": overlay.get("recipe_id"), "recipe_sha256": overlay.get("recipe_sha256"),
                "hidden_tests_tree_sha256": g.hidden_tests_tree_sha256, "run_tests_sh_sha256": g.run_tests_sh_sha256,
                "head_commit_m3": image_facts[g.source_commit_hash].head_commit if g.source_commit_hash in image_facts else None,
                "grader_version": (gold or noop or {}).get("grader_version"),
            },
            "source": {
                "expected_total": len(expected), "expected_status_counts": counts, "expected_non_passed": non_passed,
                "hidden_test_files": [f.path for f in g.hidden_test_files],
                "runner_kind": runner_kind, "runner_prefix": _runner_prefix(g.run_tests_sh), "run_tests_sh": g.run_tests_sh,
                "problem_statement_chars": len(pub.problem_statement),
                "problem_statement_has_code_block": "```" in pub.problem_statement,
                "public_prompt_chars": len(prompts.get(iid, "")) or None,
                "public_hints_mention_conda": "conda" in (pub.public_hints or ""),
            },
            "environment": {
                "python_version": m3.get("python_version"),
                "interpreter_source_path": m3.get("interpreter_source_path"),
                "interpreter_derived_path": root_facts.get("interp"),
                "install_mode_m3": m3.get("install_mode"), "pth_line_m3": m3.get("pth_line"),
                "import_outside_testbed_ok_m3": m3.get("import_outside_testbed_ok_m3"),
                "import_path_grader": (gold or noop or {}).get("import_path_grader"),
                "pkg_version_grader": (gold or noop or {}).get("pkg_version_grader"),
                "dirty_tree_lines": dirty,
                "testbed_owner_derived": root_facts.get("testbed_owner"),
                "metacopy": root_facts.get("metacopy"),
            },
            "derived_image": None if not derived else {
                "ok": derived.get("ok"), "failures": derived.get("failures"),
                "checks_total": len(derived.get("integrity") or {}),
                "checks_failed": [k for k, v in (derived.get("integrity") or {}).items() if not (v or {}).get("ok")],
                "build_seconds": derived.get("build_seconds"),
                "base_size_bytes": derived.get("base_size_bytes"), "derived_size_bytes": derived.get("derived_size_bytes"),
                "built_at_utc": overlay.get("built_at_utc"), "preflight_stdout": derived.get("preflight_stdout"),
            },
            "rh2_runs": runs,
            "latest_default_profile": {"noop": noop and noop["run_id"], "gold": gold and gold["run_id"]},
            "reference": {
                "m3_facts_available": m3.get("available"),
                "reconcile": _reconcile_for(recon, iid, recon_ref),
            },
            "auto_checks": checks,
            "flags": sorted(set(flags)),
        }
        (out_dir / iid).mkdir(parents=True, exist_ok=True)
        (out_dir / iid / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        summary_rows.append({
            "instance_id": iid, "repo": g.repo, "python": m3.get("python_version"), "runner": runner_kind,
            "expected": counts, "noop": noop and f"{noop['reward']:g} {noop['expected_match']}/{noop['expected_total']}",
            "gold": gold and f"{gold['reward']:g} {gold['expected_match']}/{gold['expected_total']} rc={gold['test_rc']}",
            "mem_peak_mb": gold and round(gold["mem_peak_mb"] or 0), "setup_s": gold and round(gold["setup_seconds"] or 0),
            "test_s": gold and round(gold["test_seconds"] or 0),
            "reconcile_agree": [e["agree"] for e in _reconcile_for(recon, iid, recon_ref)],
            "checks_issue": sorted(k for k, v in checks.items() if v["status"] == "issue"),
            "checks_unknown": sorted(k for k, v in checks.items() if v["status"] == "unknown"),
            "flags": sorted(set(flags)),
        })
    summary = {"schema_id": "rh2.r2e_env_facts_summary.v1", "generated_at_utc": _now(), "generator": generator,
               "task_count": len(summary_rows), "rows": summary_rows}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if args.summary_md:
        lines = ["| 题 | py | runner | 期望 | noop | gold | 峰值MB | setup s | test s | 对账 | issue | unknown | flags |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in summary_rows:
            exp = "/".join(f"{k[0]}{v}" for k, v in sorted(r["expected"].items()))
            lines.append(f"| {r['repo']} `{r['instance_id'].split('__')[1][:8]}` | {r['python']} | {r['runner']} | {exp} | {r['noop']} | {r['gold']} | {r['mem_peak_mb']} | {r['setup_s']} | {r['test_s']} | {''.join('✓' if a else '✗' for a in r['reconcile_agree'])} | {', '.join(r['checks_issue']) or '-'} | {', '.join(x.replace('R13_repeat_', 'R13:') for x in r['checks_unknown']) or '-'} | {', '.join(r['flags']) or '-'} |")
        Path(args.summary_md).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--evidence-root", required=True, help="runs/r2e_rf_<date>/（含 remote/ 与 reconcile_all/）")
    ap.add_argument("--m3-root", default=None, help="runs/env_overnight_20260916/M3（可选）")
    ap.add_argument("--extra-evidence", action="append", default=[],
                    help="额外证据根 <local_dir>=<remote_prefix>（可重复），如 runs/r2e_env_repair_20260924/_rerun2=/work/envrepair/_rerun2/")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--summary-md", default=None)
    args = ap.parse_args(argv)
    summary = build(args)
    issues = sum(1 for r in summary["rows"] if r["checks_issue"])
    print(f"facts written: {summary['task_count']} tasks → {args.out_dir}; tasks with auto-check issues: {issues}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
