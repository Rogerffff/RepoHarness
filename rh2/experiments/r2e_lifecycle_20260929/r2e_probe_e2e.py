#!/usr/bin/env python3
"""R2E 探针原型的 CPU 端到端验证（2026-09-29，B 线 R2E）：桩端点 → 宿主网关 → relay → 真实 CC → 正式导出 → 真实评分。

一次运行 = 一个剧本（`scenarios/*.json`），全部是子进程，不改任何共用脚本：

1. 按剧本生成桩脚本（Bash / Read / Edit / Write 的 tool_use，最后 end_turn），起桩端点
   `base_probe_fixes_20260923/stub_anthropic_endpoint.py`（127.0.0.1:<stub-port>）；
2. 起宿主网关 `base_probe_20260922/model_gateway.py`（passthrough，上游 = 桩；监听 docker0:<gw-port>）——明天接真实模型时
   只换网关上游（自部署 adapter 或供应商），求解入口与评分不变；
3. 子进程跑 `r2e_solve_attempt.py --mode solve`（relay 上游 = 网关）；结束后停网关与桩；
4. 候选交 `scripts/replay_grade.py run`（导出成功且为空 → noop；导出失败或 unsafe → 不评分；否则
   `patch-dir:<attempt>/candidate`——与 run_matrix.grade 同口径），带 `--image-overlays`；
5. 往返核对：回放容器的基线清单与重新 apply + 导出的冻结补丁，应与求解容器的逐条一致；账本里的补丁摘要应等于渲染时的摘要；
6. 可选对照（`--controls gold,noop`）：同一题 gold / noop 直接回放评分（只看结果与日志，不读 gold 内容）；
7. 残留核对：本次各 run_id 标签下的容器 / 网络为零。

回放子进程的 docker 调用经一个只加归属标签（`--label`，默认 rh2.r2e_lifecycle=probe_proto）的 shim（写在 out-root 下，
只作用于 `docker run` / `docker create` / `docker network create`）；求解入口自己用 `--extra-label` 加同一标签。

    <rh2>/.venv/bin/python experiments/r2e_lifecycle_20260929/r2e_probe_e2e.py --scenario scenarios/<x>.json \\
        --out-root /work/r2e/probe_proto/runs/<x> --gw-port 18190 --stub-port 18191 \\
        --prepared-summary /work/r2e/prepared_dc/replay_summary.json --overlays /work/r2e/derived/all/overlays_devcheck.jsonl \\
        --cc-tarball /work/r2e/cc/claude-code-linux-x64-2.1.205.tgz [--controls gold,noop --gold-dir /work/r2e/gold]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RH2 = HERE.parents[1]
sys.path.insert(0, str(RH2 / "src"))

STUB = RH2 / "experiments" / "base_probe_fixes_20260923" / "stub_anthropic_endpoint.py"
GATEWAY = RH2 / "experiments" / "base_probe_20260922" / "model_gateway.py"
SOLVE = HERE / "r2e_solve_attempt.py"
REPLAY = RH2 / "scripts" / "replay_grade.py"
REPLAY_BUDGET = HERE / "replay_grade_budget.py"
REAL_DOCKER = "/usr/bin/docker"

SHIM = """#!/bin/bash
# probe_proto：给本进程树新建的容器 / 网络加归属标签（只加 --label，其余参数原样转发）
L={label}
case "$1" in
  run|create) sub=$1; shift; exec {docker} "$sub" --label "$L" "$@" ;;
  container) if [ "${{2-}}" = run ] || [ "${{2-}}" = create ]; then sub=$2; shift 2; exec {docker} container "$sub" --label "$L" "$@"; fi ;;
  network) if [ "${{2-}}" = create ]; then shift 2; exec {docker} network create --label "$L" "$@"; fi ;;
esac
exec {docker} "$@"
"""


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def bash_step(cmd: str, sid: str, timeout_ms: int) -> dict[str, Any]:
    # 每步末尾打印退出码（CC 工具结果里可读）；CC Bash 工具单次上限 10 分钟
    return {"kind": "tool_use", "name": "Bash",
            "input": {"command": f"{cmd}\necho \"RH2_STEP_RC:{sid}=$?\"", "timeout": int(min(600_000, timeout_ms)),
                      "description": f"probe_proto {sid}"}}


def build_stub_script(scn: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from repoharness2.adapters.slime.r2e_grading_scripts import render_r2e_rollout_preflight_script

    steps: list[dict[str, Any]] = []
    prov: list[dict[str, Any]] = []
    for st in scn["steps"]:
        k = st["kind"]
        if k == "bash_r2e_preflight":
            cmd = render_r2e_rollout_preflight_script()
            steps.append(bash_step(cmd, "r2e_preflight", 120_000))
            prov.append({"id": "r2e_preflight", "source": "r2e_grading_scripts.render_r2e_rollout_preflight_script",
                         "cmd_sha256": sha256_bytes(cmd.encode())})
        elif k == "bash_from_commands":
            f = RH2 / st["file"]
            data = f.read_bytes()
            c = {x["id"]: x for x in json.loads(data)}[st["id"]]
            steps.append(bash_step(c["cmd"], st["id"], (int(c.get("timeout_s", 300)) + 30) * 1000))
            prov.append({"id": st["id"], "source": st["file"], "file_sha256": sha256_bytes(data),
                         "cmd_sha256": sha256_bytes(c["cmd"].encode()), "purpose": c.get("purpose")})
        elif k == "bash":
            steps.append(bash_step(st["command"], st["id"], int(st.get("timeout_ms", 120_000))))
            prov.append({"id": st["id"], "source": "scenario", "cmd_sha256": sha256_bytes(st["command"].encode())})
        elif k == "tool_use":
            steps.append({"kind": "tool_use", "name": st["name"], "input": st["input"]})
            prov.append({"id": st.get("id", st["name"]), "source": "scenario", "tool": st["name"]})
        elif k == "text":
            steps.append({"kind": "text", "text": st["text"]})
        else:
            raise SystemExit(f"未知剧本步骤 {k!r}")
    if not steps or steps[-1]["kind"] != "text":
        steps.append({"kind": "text", "text": "Probe prototype steps done."})
    return steps, prov


def wait_http(url: str, seconds: float = 30.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def last_row(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[-1] if rows else None


def ledger_view(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    rep = row.get("report") or {}
    proj = row.get("projection") or {}
    return {
        "outcome": rep.get("outcome"), "reward": rep.get("reward"), "failure_category": rep.get("failure_category"),
        "expected_match": rep.get("expected_match"), "expected_total": rep.get("expected_total"),
        "grading_semantics": rep.get("grading_semantics"), "stage_error": row.get("stage_error"),
        "apply_method": (row.get("candidate") or {}).get("apply_method"),
        "candidate_patch_sha256": (row.get("candidate") or {}).get("patch_sha256"),
        "image_id_actual": row.get("image_id_actual"), "overlay_recipe": (row.get("overlay") or {}).get("recipe_id"),
        "classification": row.get("classification"), "projection_included_paths": proj.get("included_paths"),
        "projection_ignored_paths": proj.get("ignored_paths"), "log": row.get("log"), "diagnostics_ref": row.get("diagnostics_ref"),
        "observations": row.get("observations"), "phases": row.get("phases"), "test": row.get("test"),
        "cleanup": row.get("cleanup"), "notes": row.get("notes"),
    }


def run_logged(cmd: list[str], *, env: dict[str, str], log: Path, timeout: float) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as f:
        f.write(f"\n[{now()}] $ {' '.join(cmd)}\n".encode())
        f.flush()
        try:
            return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            f.write(f"\n[{now()}] killed after {timeout}s\n".encode())
            return 124


class E2E:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.ns = ns
        self.out = Path(ns.out_root).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.scn_path = Path(ns.scenario).resolve()
        self.scn = json.loads(self.scn_path.read_text(encoding="utf-8"))
        self.task = self.scn["task"]
        stamp = time.strftime("%H%M%S")
        self.attempt_id = ns.attempt_id or f"pp-{re.sub(r'[^A-Za-z0-9]+', '-', self.scn['name'])[:40]}-{stamp}"
        self.summary: dict[str, Any] = {
            "schema": "rh2.r2e_probe_proto.e2e.v1", "scenario": self.scn["name"], "scenario_file": str(self.scn_path),
            "scenario_sha256": sha256_bytes(self.scn_path.read_bytes()), "task": self.task, "attempt_id": self.attempt_id,
            "started_at": now(), "label": ns.label, "ports": {"gateway": ns.gw_port, "stub": ns.stub_port},
            "prepared_summary": ns.prepared_summary, "overlays": ns.overlays,
            "overlays_sha256": sha256_bytes(Path(ns.overlays).read_bytes()),
            "code_snapshot_id": (RH2 / "SNAPSHOT_ID").read_text().strip() if (RH2 / "SNAPSHOT_ID").exists() else None,
            "entries_sha256": {p.name: sha256_bytes(p.read_bytes()) for p in (SOLVE, Path(__file__).resolve(), STUB, GATEWAY)},
            "run_ids": [],
        }
        self.procs: list[subprocess.Popen] = []

    def save(self) -> None:
        tmp = self.out / ".summary.json.tmp"
        tmp.write_text(json.dumps(self.summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, self.out / "summary.json")

    def base_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["PYTHONPYCACHEPREFIX"] = str(self.out.parent / ".pycache")  # 不往共享代码目录写字节码
        return env

    def shim_env(self, run_id: str) -> dict[str, str]:
        d = self.out / ".docker_label_shim"
        d.mkdir(exist_ok=True)
        f = d / "docker"
        f.write_text(SHIM.format(label=self.ns.label, docker=REAL_DOCKER), encoding="utf-8")
        f.chmod(0o755)
        env = self.base_env()
        env["PATH"] = f"{d}:{env.get('PATH', '/usr/bin:/bin')}"
        env["MILES_RH2_RUN_ID"] = run_id
        return env

    # ------------------------------------------------------------------ 桩 + 网关
    def start_endpoints(self, steps: list[dict[str, Any]]) -> None:
        ns = self.ns
        (self.out / "stub_script.json").write_text(json.dumps(steps, ensure_ascii=False, indent=1), encoding="utf-8")
        stub = subprocess.Popen([sys.executable, str(STUB), "--listen-host", "127.0.0.1", "--listen-port", str(ns.stub_port),
                                 "--script", str(self.out / "stub_script.json"), "--out-dir", str(self.out / "stub")],
                                stdout=open(self.out / "stub_stdout.log", "ab"), stderr=subprocess.STDOUT, env=self.base_env())
        self.procs.append(stub)
        cfg = {"upstream_base": f"http://127.0.0.1:{ns.stub_port}", "auth_style": "passthrough",
               "max_requests_per_session": int(ns.gateway_request_cap), "upstream_retry_attempts": 1}
        (self.out / "gateway_config.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
        gw = subprocess.Popen([sys.executable, str(GATEWAY), "--config", str(self.out / "gateway_config.json"),
                               "--listen-host", ns.gw_host, "--listen-port", str(ns.gw_port), "--log-dir", str(self.out / "gateway")],
                              stdout=open(self.out / "gateway_stdout.log", "ab"), stderr=subprocess.STDOUT, env=self.base_env())
        self.procs.append(gw)
        ok_stub = wait_http(f"http://127.0.0.1:{ns.stub_port}/__stub_health")
        ok_gw = wait_http(f"http://{ns.gw_host}:{ns.gw_port}/__probe_gateway_health")
        self.summary["endpoints"] = {"stub_up": ok_stub, "gateway_up": ok_gw, "gateway_config": cfg}
        self.save()
        if not (ok_stub and ok_gw):
            raise SystemExit("桩端点或网关没起来")

    def stop_endpoints(self) -> None:
        rcs = []
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=15)
            rcs.append(p.returncode)
        self.procs.clear()
        self.summary.setdefault("endpoints", {})["stopped_rcs"] = rcs

    # ------------------------------------------------------------------ 求解
    def solve(self) -> dict[str, Any]:
        ns = self.ns
        sv = self.scn.get("solve") or {}
        steps = json.loads((self.out / "stub_script.json").read_text(encoding="utf-8"))
        cmd = [sys.executable, str(SOLVE), "--mode", "solve", "--prepared-summary", ns.prepared_summary,
               "--overlays", ns.overlays, "--task", self.task, "--out-dir", str(self.out / "attempt"),
               "--attempt-id", self.attempt_id, "--solver", "stub_script", "--solver-note", self.scn.get("purpose", ""),
               "--gateway-host", ns.gw_host, "--gateway-port", str(ns.gw_port),
               "--wall-seconds", str(int(sv.get("wall_seconds", 1200))), "--max-turns", str(len(steps) + 3),
               "--max-context-len", str(int(sv.get("max_context_len", 32768))),
               "--max-new-tokens", str(int(sv.get("max_new_tokens", 4096))),
               "--subnet-skip", str(ns.subnet_skip), "--extra-label", ns.label]
        if self.scn.get("legacy_gitdiff_compare"):
            cmd.append("--legacy-gitdiff-compare")
        env = self.base_env()
        env["SLIME_AGENT_CC_PLATFORM_TARBALL"] = ns.cc_tarball
        t = time.monotonic()
        rc = run_logged(cmd, env=env, log=self.out / "solve.log", timeout=float(sv.get("wall_seconds", 1200)) + 1800)
        self.summary["run_ids"].append(self.attempt_id)
        arec_path = self.out / "attempt" / "attempt.json"
        arec = json.loads(arec_path.read_text(encoding="utf-8")) if arec_path.exists() else {}
        cand = arec.get("candidate") or {}
        self.summary["solve"] = {
            "rc": rc, "seconds": round(time.monotonic() - t, 1), "result": arec.get("result"),
            "failure_detail": arec.get("failure_detail"), "termination": arec.get("termination"),
            "harness_exit_code": arec.get("harness_exit_code"), "cleanup": arec.get("cleanup"),
            "image_used": arec.get("image_used"), "container_image_id": arec.get("container_image_id"),
            "overlay": arec.get("overlay"), "code_snapshot_id": arec.get("code_snapshot_id"),
            "stages_ok": {k: v.get("ok") for k, v in (arec.get("stages") or {}).items() if isinstance(v, dict) and "ok" in v},
            "r2e_preflight_entry": (arec.get("stages") or {}).get("r2e_preflight"),
            "activation_facts": ((arec.get("stages") or {}).get("activation_check") or {}).get("facts"),
            "baseline_census": (arec.get("stages") or {}).get("baseline_census"),
            "quiescence": (arec.get("stages") or {}).get("quiescence"),
            "timings": arec.get("timings"), "env_injections": arec.get("env_injections"),
            "cc_extra_args": arec.get("cc_extra_args"), "trajectory_summary": arec.get("trajectory_summary"),
            "harness_log_complete": arec.get("harness_log_complete"),
            "candidate": {k: v for k, v in cand.items() if k != "entries"}, "candidate_entries": cand.get("entries"),
            "legacy_gitdiff_compare": arec.get("legacy_gitdiff_compare"),
            "trusted_root_exec_rewrites": arec.get("trusted_root_exec_rewrites"),
        }
        self.summary["cc_tool_results"] = self.cc_tool_facts()
        self.summary["gateway_requests"] = self.gateway_facts()
        self.save()
        return arec

    def cc_tool_facts(self) -> dict[str, Any]:
        """CC 轨迹里的工具结果：各步退出码、经 CC Bash 工具（agent 身份）跑的 R2E 预检判读。"""

        from repoharness2.adapters.slime.r2e_grading_scripts import evaluate_r2e_rollout_preflight

        traj = self.out / "attempt" / "trajectory.jsonl"
        results: list[str] = []
        tools: list[str] = []
        if traj.exists():
            for ln in traj.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    ev = json.loads(ln)
                except Exception:  # noqa: BLE001
                    continue
                for blk in (ev.get("message") or {}).get("content") or []:
                    if not isinstance(blk, dict):
                        continue
                    if ev.get("type") == "assistant" and blk.get("type") == "tool_use":
                        tools.append(blk.get("name", "?"))
                    if ev.get("type") == "user" and blk.get("type") == "tool_result":
                        c = blk.get("content")
                        results.append(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False))
        joined = "\n".join(results)
        rcs = dict(re.findall(r"RH2_STEP_RC:([A-Za-z0-9_.-]+)=(-?\d+)", joined))
        pre_text = next((r for r in results if "RH2_PREFLIGHT_" in r), "")
        return {"tools_called": tools, "step_rcs": rcs, "tool_result_count": len(results),
                "r2e_preflight_via_cc": {"lines": [x for x in pre_text.splitlines() if x.startswith("RH2_PREFLIGHT_")],
                                         "failures": evaluate_r2e_rollout_preflight(pre_text) if pre_text else ["no_output"]},
                "tool_result_tails": [r[-600:] for r in results]}

    def gateway_facts(self) -> dict[str, Any]:
        d = self.out / "gateway" / self.attempt_id
        rows = []
        if (d / "requests.jsonl").exists():
            for ln in (d / "requests.jsonl").read_text(encoding="utf-8").splitlines():
                r = json.loads(ln)
                body = r.get("body") if isinstance(r.get("body"), dict) else {}
                rows.append({"seq": r.get("seq"), "path": r.get("path"), "model": r.get("model_requested"),
                             "stream": r.get("stream"), "max_tokens": body.get("max_tokens"),
                             "tools": sorted(t.get("name") for t in body.get("tools") or [] if isinstance(t, dict))})
        return {"session_dir": str(d), "requests": rows,
                "usage": json.loads((d / "usage.json").read_text()) if (d / "usage.json").exists() else None}

    # ------------------------------------------------------------------ 评分
    def grade(self, candidate: str, tag: str) -> dict[str, Any]:
        ns = self.ns
        gdir = self.out / f"grade_{tag}"
        run_id = f"{self.attempt_id}-g{tag}"[:90]
        self.summary["run_ids"].append(run_id)
        cmd = ["run", "--prepared-summary", ns.prepared_summary, "--task-ids", self.task,
               "--candidate", candidate, "--repeat", "1", "--eval-log-dir", str(gdir / "eval_logs"),
               "--artifacts-dir", str(gdir / "artifacts"), "--ledger", str(gdir / "ledger.jsonl"),
               "--image-overlays", ns.overlays]
        if ns.candidate_stage_seconds:
            cmd += ["--candidate-stage-seconds", str(ns.candidate_stage_seconds)]
        if ns.env_reset_timeout:  # 预算包装：只放宽 grader 基线重建与控制面保护的时限（见 replay_grade_budget.py）
            cmd = [sys.executable, str(REPLAY_BUDGET), "--env-reset-timeout", str(ns.env_reset_timeout), "--", *cmd]
        else:
            cmd = [sys.executable, str(REPLAY), *cmd]
        t = time.monotonic()
        rc = run_logged(cmd, env=self.shim_env(run_id), log=gdir / "grade.log", timeout=float(ns.grade_seconds))
        view = ledger_view(last_row(gdir / "ledger.jsonl"))
        return {"candidate": candidate, "driver_exit": rc, "seconds": round(time.monotonic() - t, 1), "run_id": run_id,
                "budget": {"env_reset_timeout_seconds": ns.env_reset_timeout or 300.0,
                           "candidate_stage_seconds": ns.candidate_stage_seconds or 900.0}, "ledger": view}

    def roundtrip(self, tag: str = "cc") -> dict[str, Any]:
        from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest

        arts = sorted((self.out / f"grade_{tag}" / "artifacts").glob("*/a1-*"))
        if not arts:
            return {"available": False}
        a = arts[-1]
        res: dict[str, Any] = {"available": True, "replay_artifact_dir": str(a)}
        sb = json.loads((self.out / "attempt" / "frozen" / "baseline_manifest.json").read_text(encoding="utf-8"))
        if (a / "baseline_manifest.json").exists():
            rb = json.loads((a / "baseline_manifest.json").read_text(encoding="utf-8"))
            bkey = lambda e: (e["path"], e["object_type"], e["mode"], e.get("content_digest") or e.get("symlink_target_digest"))  # noqa: E731
            sd = compute_baseline_manifest_digest(BaselineWorkspaceManifestV1.model_validate(sb))
            rd = compute_baseline_manifest_digest(BaselineWorkspaceManifestV1.model_validate(rb))
            res["baseline"] = {"solve_digest": sd, "replay_digest": rd, "digest_equal": sd == rd,
                               "entries_equal": sorted(map(bkey, sb["entries"])) == sorted(map(bkey, rb["entries"])),
                               "solve_entries": len(sb["entries"]), "replay_entries": len(rb["entries"]),
                               "excluded_census_equal": sb.get("excluded_census_digest") == rb.get("excluded_census_digest")}
        sp_path = self.out / "attempt" / "frozen" / "frozen_patch.json"
        if (a / "frozen_patch.json").exists() and sp_path.exists():
            sp = json.loads(sp_path.read_text(encoding="utf-8"))
            rp = json.loads((a / "frozen_patch.json").read_text(encoding="utf-8"))
            key = lambda e: (e["path"], e["operation"], e["object_type"], e.get("mode"), e.get("content_digest"))  # noqa: E731
            s_set, r_set = set(map(key, sp["entries"])), set(map(key, rp["entries"]))
            res["frozen_patch"] = {"entries_equal": s_set == r_set, "solve_entries": len(s_set), "replay_entries": len(r_set),
                                   "only_in_solve": sorted(s_set - r_set)[:20], "only_in_replay": sorted(r_set - s_set)[:20],
                                   "excluded_pathset_changed": [sp.get("excluded_pathset_changed"), rp.get("excluded_pathset_changed")]}
        return res

    def residuals(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for rid in self.summary["run_ids"]:
            c = subprocess.run([REAL_DOCKER, "ps", "-a", "--filter", f"label=rh2.run_id={rid}", "--format", "{{.Names}}"],
                               capture_output=True, text=True)
            n = subprocess.run([REAL_DOCKER, "network", "ls", "--filter", f"label=rh2.run_id={rid}", "--format", "{{.Name}}"],
                               capture_output=True, text=True)
            out[rid] = {"containers": c.stdout.split() if c.returncode == 0 else ["<query_failed>"],
                        "networks": n.stdout.split() if n.returncode == 0 else ["<query_failed>"]}
        out["_clean"] = all(not v["containers"] and not v["networks"] for k, v in out.items() if not k.startswith("_"))
        return out

    # ------------------------------------------------------------------ 只重评（求解已完成）
    def regrade(self) -> int:
        ns = self.ns
        tag = ns.regrade
        prev = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        self.summary = prev
        self.attempt_id = prev["attempt_id"]
        self.summary.setdefault("run_ids", [])
        arec = json.loads((self.out / "attempt" / "attempt.json").read_text(encoding="utf-8"))
        cand = arec.get("candidate") or {}
        out: dict[str, Any] = {"started_at": now(), "why": ns.regrade_note}
        self.summary.setdefault("regrade", {})[tag] = out
        if not ns.controls_only:
            if not cand.get("export_ok"):
                out["cc"] = {"not_graded": "candidate_export_missing_or_failed"}
            else:
                spec = "noop" if cand.get("empty") else f"patch-dir:{self.out / 'attempt' / 'candidate'}"
                out["cc"] = self.grade(spec, f"cc{tag}")
                if not cand.get("empty"):
                    rt = self.roundtrip(f"cc{tag}")
                    rt["ledger_patch_sha256_equals_render"] = (out["cc"].get("ledger") or {}).get("candidate_patch_sha256") == cand.get("sha256")
                    out["roundtrip"] = rt
            self.save()
        for ctl in [x for x in (ns.controls or "").split(",") if x]:
            spec = "noop" if ctl == "noop" else f"gold-dir:{ns.gold_dir}"
            out[ctl] = self.grade(spec, f"{ctl}{tag}")
            self.save()
        self.summary["residuals"] = self.residuals()
        out["finished_at"] = now()
        self.save()
        print(json.dumps({"scenario": self.summary.get("scenario"), "regrade": tag,
                          "reward": {k: ((v.get("ledger") or {}).get("reward") if isinstance(v, dict) else None)
                                     for k, v in out.items() if isinstance(v, dict) and "ledger" in v},
                          "residual_clean": self.summary["residuals"]["_clean"]}, ensure_ascii=False, default=str), flush=True)
        return 0 if self.summary["residuals"]["_clean"] else 4

    # ------------------------------------------------------------------ 主流程
    def main(self) -> int:
        ns = self.ns
        if ns.regrade:
            return self.regrade()
        steps, prov = build_stub_script(self.scn)
        self.summary["stub_steps"] = [{"i": i, "kind": s["kind"], "name": s.get("name")} for i, s in enumerate(steps)]
        self.summary["step_provenance"] = prov
        self.save()
        arec: dict[str, Any] = {}
        try:
            self.start_endpoints(steps)
            arec = self.solve()
        finally:
            self.stop_endpoints()
            self.save()
        cand = arec.get("candidate") or {}
        grading: dict[str, Any] = {}
        if not ns.no_grade:
            if (arec.get("cleanup") or {}).get("cleanup_ok") is not True:
                grading["cc"] = {"not_graded": "solve_cleanup_not_confirmed"}
            elif not cand.get("export_ok"):
                grading["cc"] = {"not_graded": "unsafe_artifact" if cand.get("unsafe") else "candidate_export_missing_or_failed"}
            else:
                spec = "noop" if cand.get("empty") else f"patch-dir:{self.out / 'attempt' / 'candidate'}"
                grading["cc"] = self.grade(spec, "cc")
                if not cand.get("empty"):
                    rt = self.roundtrip("cc")
                    rt["ledger_patch_sha256_equals_render"] = (grading["cc"].get("ledger") or {}).get("candidate_patch_sha256") == cand.get("sha256")
                    self.summary["roundtrip"] = rt
            self.summary["grading"] = grading
            self.save()
            for ctl in [x for x in (ns.controls or "").split(",") if x]:
                spec = "noop" if ctl == "noop" else f"gold-dir:{ns.gold_dir}"
                grading[ctl] = self.grade(spec, ctl)
                self.save()
        self.summary["residuals"] = self.residuals()
        self.summary["finished_at"] = now()
        self.save()
        print(json.dumps({"scenario": self.scn["name"], "attempt": self.summary["solve"].get("result"),
                          "export_ok": cand.get("export_ok"), "files": cand.get("files"),
                          "reward": {k: ((v.get("ledger") or {}).get("reward") if isinstance(v, dict) else None) for k, v in grading.items()},
                          "roundtrip": self.summary.get("roundtrip"), "residual_clean": self.summary["residuals"]["_clean"]},
                         ensure_ascii=False, default=str), flush=True)
        return 0 if self.summary["residuals"]["_clean"] else 4


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="R2E 探针原型的 CPU 端到端验证")
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--overlays", required=True)
    ap.add_argument("--cc-tarball", required=True)
    ap.add_argument("--gw-host", default="172.17.0.1")
    ap.add_argument("--gw-port", type=int, required=True)
    ap.add_argument("--stub-port", type=int, required=True)
    ap.add_argument("--gateway-request-cap", type=int, default=40)
    ap.add_argument("--subnet-skip", type=int, default=0)
    ap.add_argument("--attempt-id", default=None)
    ap.add_argument("--label", default="rh2.r2e_lifecycle=probe_proto")
    ap.add_argument("--no-grade", action="store_true")
    ap.add_argument("--controls", default="", help="逗号分隔：gold,noop（只看评分结果，不读 gold 内容）")
    ap.add_argument("--gold-dir", default="/work/r2e/gold")
    ap.add_argument("--grade-seconds", type=int, default=5400)
    ap.add_argument("--env-reset-timeout", type=float, default=0.0,
                    help="非 0：评分经 replay_grade_budget.py 放宽 grader 基线重建 / 控制面保护时限（缺省 300 s）")
    ap.add_argument("--candidate-stage-seconds", type=float, default=0.0, help="非 0：传给 replay_grade 的候选阶段预算（缺省 900 s）")
    ap.add_argument("--regrade", default="", help="只重评已有求解结果；值为标签后缀（例：2 → grade_cc2 / grade_gold2）")
    ap.add_argument("--regrade-note", default="")
    ap.add_argument("--controls-only", action="store_true", help="与 --regrade 连用：只评对照（gold / noop），不重评 CC 候选")
    ns = ap.parse_args(argv)
    for p in (ns.gw_port, ns.stub_port):
        if not 18190 <= p <= 18199:
            ap.error("本批规则：桩 / 网关端口只用 18190–18199")
    return E2E(ns).main()


if __name__ == "__main__":
    raise SystemExit(main())
