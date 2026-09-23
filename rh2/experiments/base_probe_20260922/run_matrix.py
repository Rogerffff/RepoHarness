#!/usr/bin/env python3
"""基座探针：题目 × solver × 重复 的派发与真实 RH2 评分（可续跑）。

每个 attempt 两步，均为子进程：① `solve_attempt.py --mode solve`；② 真实评分 driver
`scripts/replay_grade.py run --candidate patch-dir:<attempt>/candidate`（题目带安装配方时经
`env_recipe_repair_20260919/replay_with_install_recipe.py` 包一层；空补丁按 noop 候选评分，保留 RH2 原分）。
结果逐 attempt 追加到 `<out-root>/matrix_ledger.jsonl`；`attempt.json` 与评分账本是权威记录，本汇总只为看盘。

护栏：`<out-root>/STOP` 存在即不再派发新 attempt；同一 solver 连续 3 次 infra 失败停该 solver；
DeepSeek 类 solver 在派发前查余额，低于保底停该 solver。不重试、不补采：失败如实留账。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RH2_ROOT = HERE.parents[1]
RECIPE_WRAPPER = RH2_ROOT / "experiments/env_recipe_repair_20260919/replay_with_install_recipe.py"


def _slug(text: str, n: int = 24) -> str:
    return (re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-") or "x")[:n]


def deepseek_balance(key_file: str) -> float | None:
    try:
        key = Path(key_file).read_text(encoding="utf-8").strip()
        req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        for b in data.get("balance_infos", []):
            if b.get("currency") == "CNY":
                return float(b.get("total_balance"))
    except Exception:  # noqa: BLE001
        return None
    return None


async def run_proc(cmd: list[str], *, env: dict[str, str], log: Path, timeout: float) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "ab") as f:
        f.write((f"\n$ {' '.join(cmd)}\n").encode())
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=f, stderr=asyncio.subprocess.STDOUT, env=env)
        try:
            return await asyncio.wait_for(proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            f.write(f"\n[run_matrix] killed after {timeout}s\n".encode())
            return 124


def last_ledger_row(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    row = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
    return row


class Matrix:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.ns = ns
        self.out = Path(ns.out_root).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.tasks = json.loads(Path(ns.tasks_config).read_text(encoding="utf-8"))
        self.solvers = json.loads(Path(ns.solvers_config).read_text(encoding="utf-8"))
        self.plan = json.loads(Path(ns.plan).read_text(encoding="utf-8"))
        self.sem = asyncio.Semaphore(int(ns.concurrency))
        self.solver_sems = {name: asyncio.Semaphore(int(cfg.get("max_concurrency", ns.concurrency)))
                            for name, cfg in self.solvers.items()}
        self.infra_streak: dict[str, int] = {}
        self.stopped_solvers: dict[str, str] = {}
        self.slot = 0
        self.lock = asyncio.Lock()

    def ledger(self, row: dict[str, Any]) -> None:
        with open(self.out / "matrix_ledger.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    async def one(self, task: str, solver: str, k: int) -> None:
        ns = self.ns
        tcfg = self.tasks[task]
        scfg = self.solvers[solver]
        adir = self.out / "attempts" / task / solver / f"a{k}"
        attempt_id = f"bp22-{_slug(solver, 16)}-{_slug(task.split('__')[-1], 20)}-a{k}"
        async with self.sem, self.solver_sems[solver]:
            if (self.out / "STOP").exists():
                return
            if solver in self.stopped_solvers:
                self.ledger({"task": task, "solver": solver, "k": k, "skipped": self.stopped_solvers[solver]})
                return
            arec_path = adir / "attempt.json"
            arec = json.loads(arec_path.read_text(encoding="utf-8")) if arec_path.exists() else None
            if not (arec and arec.get("result") == "ran" and arec.get("finished_at")):
                if arec is not None:  # 旧的不完整尝试整目录改名留存，不覆盖
                    adir.rename(adir.with_name(f"a{k}.incomplete-{int(time.time())}"))
                if scfg.get("balance_key_file"):
                    bal = await asyncio.to_thread(deepseek_balance, scfg["balance_key_file"])
                    if bal is not None and bal < float(scfg.get("reserve_cny", 5.0)):
                        self.stopped_solvers[solver] = f"balance_below_reserve:{bal}"
                        self.ledger({"task": task, "solver": solver, "k": k, "skipped": self.stopped_solvers[solver]})
                        return
                async with self.lock:
                    self.slot += 1
                    skip = (self.slot * 7) % 400
                actor = tcfg.get("actor") or {}
                cmd = [sys.executable, str(HERE / "solve_attempt.py"), "--mode", "solve",
                       "--prepared-summary", ns.prepared_summary, "--task", task, "--out-dir", str(adir),
                       "--attempt-id", attempt_id, "--solver", solver, "--solver-note", json.dumps(scfg.get("note", ""), ensure_ascii=False),
                       "--gateway-host", scfg.get("gateway_host", "172.17.0.1"), "--gateway-port", str(scfg["gateway_port"]),
                       "--wall-seconds", str(ns.wall_seconds), "--max-turns", str(ns.max_turns),
                       "--actor-env", actor.get("actor_env", ns.actor_env), "--subnet-skip", str(skip),
                       "--harness-out", ns.harness_out]
                if actor.get("image_override"):
                    cmd += ["--image-override", actor["image_override"], "--image-recipe-note", actor.get("image_recipe_note", "")]
                if actor.get("prep_script"):
                    cmd += ["--prep-script", actor["prep_script"], "--prep-user", actor.get("prep_user", "root")]
                rc = await run_proc(cmd, env=dict(os.environ), log=adir / "solve.log", timeout=float(ns.wall_seconds) + 3600)
                arec = json.loads(arec_path.read_text(encoding="utf-8")) if arec_path.exists() else {"result": f"no_attempt_json rc={rc}"}
            result = str(arec.get("result"))
            if result != "ran":
                self.infra_streak[solver] = self.infra_streak.get(solver, 0) + 1
                if self.infra_streak[solver] >= 3:
                    self.stopped_solvers[solver] = "three_consecutive_infra_failures"
                self.ledger({"task": task, "solver": solver, "k": k, "attempt_id": attempt_id, "result": result,
                             "failure_detail": arec.get("failure_detail"), "dir": str(adir)})
                return
            self.infra_streak[solver] = 0
            grade = await self.grade(task, tcfg, adir, attempt_id, arec) if not ns.no_grade else {"skipped": True}
        summ = arec.get("trajectory_summary") or {}
        ccr = summ.get("cc_result") or {}
        self.ledger({
            "task": task, "solver": solver, "k": k, "attempt_id": attempt_id, "result": result,
            "termination": arec.get("termination"), "harness_exit_code": arec.get("harness_exit_code"),
            "solve_seconds": arec.get("solve_seconds"), "num_turns": ccr.get("num_turns"), "cc_subtype": ccr.get("subtype"),
            "tool_calls_total": summ.get("tool_calls_total"), "tool_result_errors": summ.get("tool_result_errors"),
            "candidate_bytes": (arec.get("candidate") or {}).get("bytes"), "candidate_files": (arec.get("candidate") or {}).get("files"),
            "pip_freeze_changed": arec.get("pip_freeze_changed"), "grade": grade, "dir": str(adir),
        })

    async def grade(self, task: str, tcfg: dict[str, Any], adir: Path, attempt_id: str, arec: dict[str, Any]) -> dict[str, Any]:
        ns = self.ns
        gdir = adir / "grading"
        ledger = gdir / "ledger.jsonl"
        row = last_ledger_row(ledger)
        if row is None:
            cand = arec.get("candidate") or {}
            empty = bool(cand.get("empty")) or not cand.get("bytes")
            candidate = "noop" if empty else f"patch-dir:{adir / 'candidate'}"
            g = tcfg.get("grader") or {}
            base = ["run", "--prepared-summary", ns.prepared_summary, "--task-ids", task, "--candidate", candidate,
                    "--repeat", "1", "--eval-log-dir", str(gdir / "eval_logs"), "--artifacts-dir", str(gdir / "artifacts"),
                    "--ledger", str(ledger)]
            if g.get("derived_image"):
                base += ["--derived-image", g["derived_image"], "--derived-image-recipe", g.get("derived_image_recipe", "unspecified")]
            if g.get("recipe"):
                cmd = [sys.executable, str(RECIPE_WRAPPER), "--code-root", str(RH2_ROOT), "--recipe", g["recipe"],
                       "--audit-dir", str(gdir / "recipe"), "--grading-label-prefix", f"bpg{_slug(attempt_id, 30).lower()}", "--", *base]
            else:
                cmd = [sys.executable, str(RH2_ROOT / "scripts/replay_grade.py"), *base]
            env = dict(os.environ)
            env["MILES_RH2_RUN_ID"] = f"bpg-{attempt_id}"
            for k, v in (g.get("env") or {}).items():
                env[k] = str(v)
            rc = await run_proc(cmd, env=env, log=gdir / "grade.log", timeout=float(ns.grade_seconds))
            row = last_ledger_row(ledger)
            if row is None:
                return {"grading_failed": True, "driver_exit": rc}
            row["_driver_exit"] = rc
            row["_empty_patch_graded_as_noop"] = empty
        rep = row.get("report") or {}
        return {"outcome": rep.get("outcome"), "reward": rep.get("reward"), "failure_category": rep.get("failure_category"),
                "f2p": [rep.get("f2p_pass"), rep.get("f2p_total")], "p2p_fail": rep.get("p2p_fail"), "p2p_total": rep.get("p2p_total"),
                "stage_error": row.get("stage_error"), "apply_method": (row.get("candidate") or {}).get("apply_method"),
                "driver_exit": row.get("_driver_exit"), "empty_patch_graded_as_noop": row.get("_empty_patch_graded_as_noop")}

    async def main(self) -> int:
        jobs = []
        for item in self.plan:
            for k in range(int(item.get("first", 1)), int(item.get("first", 1)) + int(item["n"])):
                jobs.append(self.one(item["task"], item["solver"], k))
        await asyncio.gather(*jobs)
        self.ledger({"matrix_done": True, "at": time.time(), "stopped_solvers": self.stopped_solvers})
        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--tasks-config", required=True, help="JSON：instance_id → {actor:{image_override,prep_script,prep_user,actor_env}, grader:{derived_image,derived_image_recipe,recipe,env}}")
    ap.add_argument("--solvers-config", required=True, help="JSON：solver 名 → {gateway_port, gateway_host?, max_concurrency?, balance_key_file?, reserve_cny?, note}")
    ap.add_argument("--plan", required=True, help='JSON 列表：[{"task":…, "solver":…, "n":2, "first":1}]')
    ap.add_argument("--out-root", required=True)
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--wall-seconds", type=int, default=1800)
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--actor-env", default="original")
    ap.add_argument("--grade-seconds", type=int, default=5400)
    ap.add_argument("--harness-out", choices=("in_tree", "out_of_tree"), default="in_tree")
    ap.add_argument("--no-grade", action="store_true")
    return asyncio.run(Matrix(ap.parse_args(argv)).main())


if __name__ == "__main__":
    raise SystemExit(main())
