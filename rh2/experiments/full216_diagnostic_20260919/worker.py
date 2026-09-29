"""诊断外壳：调用现有 replay/manager，不改变评分、资源默认值或资格规则。"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repoharness2.adapters.slime.replay_grade import (  # noqa: E402
    ReplayBudgets, ReplayGrader, candidate_from_spec, load_context,
)
from repoharness2.adapters.slime.sandbox_profile import (  # noqa: E402
    grader_profile_from_env, rollout_profile_from_env,
)
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager  # noqa: E402


def write_json(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(value, ensure_ascii=False, default=str) + "\n")
    tmp.replace(path)


def append(path: Path, value: object) -> None:
    with path.open("a") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")
        stream.flush()


def best_effort(fn, *args) -> None:
    """异常收口时，证据盘失败不能阻止容器清理。正常运行仍让写盘错误上抛。"""
    try:
        fn(*args)
    except OSError as exc:
        try:
            print(f"diagnostic write failed: {exc}", file=sys.stderr, flush=True)
        except OSError:
            pass


def memory(manager: SWEGradingManager) -> dict:
    result = {}
    for filename, keys in [("status", {"VmRSS", "VmHWM", "VmSize"}), ("smaps_rollup", {"Pss"})]:
        try:
            for line in Path(f"/proc/self/{filename}").read_text().splitlines():
                key, _, value = line.partition(":")
                if key in keys:
                    result[key + "_kib"] = int(value.split()[0])
        except (OSError, ValueError):
            result[filename + "_unavailable"] = True
    # 只读观测，不清空 manager 的记录或日志，避免掩盖长期留存。
    records = manager.container_records
    result["manager_records"] = len(records)
    result["retained_log_chars"] = sum(len(r.eval_log_partial or "") for r in records)
    return result


async def run(ns: argparse.Namespace) -> int:
    root, out = Path(ns.root), Path(ns.out)
    out.mkdir(parents=True, exist_ok=False)
    jobs = json.loads(Path(ns.jobs).read_text())
    os.environ["MILES_RH2_RUN_ID"] = ns.run_id
    summary = json.loads((root / "replay/prepared/replay_summary.json").read_text())
    rollout = rollout_profile_from_env(os.environ, model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1)
    profile = grader_profile_from_env(os.environ)
    context = load_context(
        prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
        manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=rollout,
        grader_profile=profile, artifacts_dir=out / "artifacts", run_id=ns.run_id,
        qualifications={},
    )
    manager = SWEGradingManager(
        GradingManagerConfig(eval_log_dir=out / "eval_logs", sandbox_profile=profile),
        stop_requested=lambda: Path(ns.halt_file).exists(),
    )
    runner = ReplayGrader(context, manager, ledger_path=out / "ledger.jsonl", budgets=ReplayBudgets())
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)
    state = {"pid": os.getpid(), "run_id": ns.run_id, "planned": len(jobs), "finished": 0,
             "phase": "startup", "phase_started": time.time(), "qualifications": 0}
    write_json(out / "status.json", state)
    rc = 0
    try:
        await asyncio.wait_for(manager.startup(), timeout=120)
        for job in jobs:
            if Path(ns.halt_file).exists():
                state["phase"] = "stopped_by_global_halt"
                rc = 2
                break
            state.update(phase="attempt", phase_started=time.time(), job=job)
            write_json(out / "status.json", state)
            before = memory(manager)
            start = time.monotonic()
            append(out / "events.jsonl", {"event": "started", "at": time.time(), "job": job, "memory": before})
            task_id = context.resolve_task_id(job["task_id"])
            iid = context.grading_views[task_id].instance_id
            candidate = candidate_from_spec(job["candidate"], instance_id=iid)
            row = await runner.replay_one(task_id, candidate, attempt=job["attempt"])
            state["finished"] += 1
            append(out / "events.jsonl", {
                "event": "finished", "at": time.time(), "job": job, "seconds": time.monotonic() - start,
                "memory": memory(manager), "report": row.get("report"), "stage_error": row.get("stage_error"),
            })
            write_json(out / "status.json", state)
            if str(row.get("stage_error") or "").startswith(("grade_exception", "classify:契约矛盾")):
                raise RuntimeError("grade exception or projection contradiction: " + row["stage_error"])
            detail = str((row.get("report") or {}).get("infra_failure_detail") or "")
            if detail.startswith(("grading_trusted_setup_failed", "grading_control_surface_protect_failed")):
                raise RuntimeError("trusted setup/control surface failure: " + detail)
    except BaseException as exc:
        rc = 2
        state["failure"] = {"type": type(exc).__name__, "detail": str(exc)}
        best_effort(append, out / "events.jsonl", {"event": "fatal", "at": time.time(), "job": state.get("job"),
                                                "error": state["failure"], "traceback": traceback.format_exc()})
        best_effort(write_json, Path(ns.halt_file), {"at": time.time(), "worker": ns.run_id, "failure": state["failure"]})
    finally:
        state.update(phase="closing", phase_started=time.time())
        best_effort(write_json, out / "status.json", state)
        try:
            close = await asyncio.wait_for(manager.close(), timeout=150)
            best_effort(append, out / "events.jsonl", {"event": "closed", "at": time.time(), "close": close, "memory": memory(manager)})
            if close.get("containers_open"):
                raise RuntimeError("manager close did not confirm clean release: " + repr(close))
        except BaseException as exc:
            rc = 2
            state["close_failure"] = {"type": type(exc).__name__, "detail": str(exc)}
            best_effort(write_json, Path(ns.halt_file), {"at": time.time(), "worker": ns.run_id, "failure": state["close_failure"]})
        state.update(phase="done", exit_code=rc, ended_at=time.time())
        best_effort(write_json, out / "status.json", state)
    return rc


def main() -> int:
    p = argparse.ArgumentParser()
    for name in ("root", "out", "jobs", "run-id", "halt-file"):
        p.add_argument("--" + name, required=True)
    return asyncio.run(run(p.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
