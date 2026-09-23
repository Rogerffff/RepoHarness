"""第三次窄复核：重试后的可信确认对照，以及真实血缘脚本的失败分类。

生产停止 helper、屏障、编排、Outcome、准入与 receipt 都不替换返回值。
沿用 CPU formal 夹具的模型轨迹、评分、持久化通道与预算事件入口；新增故障只在 Docker IO，
停止时刻使用同一可控观测钟。等待次数、间隔和总预算保留生产值。
血缘案另在临时 git 仓库实际执行 build_probe_script，只替换固定 /testbed 路径；全局 git
配置被重定向到同一临时目录。它不读写主仓库 git 状态，不启动 Docker、CC、模型服务或 GPU。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from test_slime_generate import SAMPLING_PARAMS, TASK_ID_DENSE, _Args, make_task
from test_w1b_termination_facts_producer import _formal_chain, _steps

from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError, fatal_halt_notifier
from repoharness2.adapters.slime.bringup import make_disposition_policy
from repoharness2.adapters.slime.execution_scope import COUNT_SCRIPT, KILL_SCRIPT
from repoharness2.adapters.slime.quiescence_barrier import DockerQuiescenceBarrier
from repoharness2.envpack.materialize import build_probe_script, evaluate_probe
from repoharness2.governance.admission import AdmissionPayloadV1, decide_member_disposition
from repoharness2.grading.manager import ExecResult


class Budget:
    """CPU 夹具的预算事件入口；不替换任何停止与归类实现。"""

    def __init__(self):
        self.callbacks, self.states = {}, {}

    def subscribe(self, sid, callback):
        self.callbacks[sid] = callback

    def unsubscribe(self, sid):
        self.callbacks.pop(sid, None)

    def snapshot(self, sid):
        return self.states.get(sid)

    def exhaust(self, sid):
        self.states[sid] = {"cap": 3, "accepted": 3, "exhausted": True, "refused_count": 1}
        self.callbacks[sid](sid)


async def stop_case(*, late_postprocessing: bool) -> dict:
    now, budget = [0.0], Budget()
    chain = _formal_chain(barrier=DockerQuiescenceBarrier(clock=lambda: now[0]))
    orch = chain.orchestrator
    orch._clock = lambda: now[0]
    orch._turn_budget_subscribe = budget.subscribe
    orch._turn_budget_unsubscribe = budget.unsubscribe
    orch._turn_budget_snapshot = budget.snapshot
    original_docker = orch._docker
    events, drivers, notices = [], [], []
    kills, counts = 0, 0

    async def io(*args, input_bytes=None):
        nonlocal kills, counts
        if args[0] == "exec" and KILL_SCRIPT in args[-1]:
            kills += 1
            counts = 0
            if kills == 2:
                now[0] = 899.93
            elif kills == 3:
                now[0] = 901.1 if late_postprocessing else 899.96
            events.append({"kind": "kill", "number": kills, "returned_at": now[0]})
            return ExecResult(0, "pkill_status=0\n", "")
        if args[0] == "exec" and COUNT_SCRIPT in args[-1]:
            counts += 1
            issued = now[0]
            if kills == 1:
                # 首次 kill 成功返回，但真实 helper 的十次计数均不可读；没有归零证明。
                events.append({"kind": "count_unreadable", "kill_number": kills,
                               "issued_at": issued, "returned_at": now[0]})
                return ExecResult(1, "", "probe: docker exec query failed")
            now[0] = 899.95 if kills == 2 else (901.2 if late_postprocessing else 899.97)
            events.append({"kind": "count_zero", "kill_number": kills,
                           "issued_at": issued, "returned_at": now[0]})
            return ExecResult(0, "0\n", "")
        if args[0] == "exec" and "git status --porcelain" in args[-1] and kills >= 3:
            now[0] = 905.0 if late_postprocessing else 899.99
            events.append({"kind": "fingerprint", "returned_at": now[0]})
        return await original_docker(*args, input_bytes=input_bytes)

    class Driver:
        name = "cpu_followup3_stop_control"

        async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
            drivers.append(asyncio.current_task())
            adapter = chain.adapter_ref["adapter"]
            await adapter.run_all_turns()
            now[0] = 899.9
            budget.exhaust(adapter.opened[-1])
            await asyncio.Event().wait()

    orch._docker, orch._harness_driver = io, Driver()
    token = fatal_halt_notifier.set(notices.append)
    try:
        delivered = await asyncio.wait_for(
            orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS)), timeout=20,
        )
    finally:
        fatal_halt_notifier.reset(token)
    audit = orch.audits[-1]
    payloads = [AdmissionPayloadV1.model_validate(s.metadata["rh2_admission"]) for s in delivered]
    verdicts = [decide_member_disposition(p, policy=make_disposition_policy()).verdict for p in payloads]
    receipt = chain.finalization.receipts[-1]
    result = {
        "case": "retry_confirmed_then_late_postprocessing" if late_postprocessing else "retry_confirmed_control",
        "mode": orch._mode, "deadline": audit.episode_deadline_monotonic, "events": events,
        "stop": audit.termination["stop"], "barrier_stop": audit.termination["barrier_stop"],
        "outcome_termination": audit.outcome_v2["termination_kind"],
        "outcome_count": len(orch.outcomes), "completion": audit.outcome_v2["completion_class"],
        "payload_matches_outcome": all(p.outcome.model_dump(mode="json") == audit.outcome_v2 for p in payloads),
        "receipt_matches_outcome": receipt.outcome_v2.model_dump(mode="json") == audit.outcome_v2,
        "member_verdicts": verdicts,
        "grading_calls": len(chain.grading.calls), "harness_tasks_settled": all(t.done() for t in drivers),
        "halt_notifications": len(notices), "cleaned": "cleanup_completed" in _steps(audit),
    }
    assert result["mode"] == "fa_formal"
    assert result["stop"]["stop_attempts"] == 2 and result["stop"]["confirmed_at_monotonic"] == 899.95
    assert len(result["stop"]["observations"]) == 11
    assert all(o["residual"] == -1 for o in result["stop"]["observations"][:10])
    assert result["stop"]["stop_before_deadline"] is True
    assert result["stop"]["stop_before_deadline_evidence"] == "zero_confirmed_before_deadline"
    assert result["outcome_termination"] == "max_turns_exhausted" and result["completion"] == "present_truncated"
    assert result["outcome_count"] == 1 and result["payload_matches_outcome"] and result["receipt_matches_outcome"]
    assert verdicts == ["KEEP_FULL"]
    assert result["grading_calls"] == 1 and result["harness_tasks_settled"] and result["cleaned"]
    assert not notices
    return result


def real_lineage_outputs() -> dict:
    """以真实 git 读结果区分“对象不存在”与“对象在场但血缘不符”；不把 stderr 解析写入生产逻辑。"""

    with tempfile.TemporaryDirectory(prefix="rh2-followup3-git-") as tmp:
        directory = Path(tmp)
        repo = directory / "repo"
        repo.mkdir()
        env = dict(os.environ)
        env.update({"GIT_CONFIG_GLOBAL": str(directory / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"})

        def run(*args, check=True):
            return subprocess.run(args, cwd=repo, env=env, check=check, capture_output=True, text=True)

        def commit(message):
            run("git", "-c", "user.name=RH2 Probe", "-c", "user.email=probe@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", message)
            return run("git", "rev-parse", "HEAD").stdout.strip()

        def probe(base):
            script = build_probe_script(base)
            actual = run("bash", "-c", script.replace("/testbed", str(repo)), check=False)
            parsed = evaluate_probe(base, actual.returncode, actual.stdout, actual.stderr)
            return {"expected_base": base, "script_sha256": hashlib.sha256(script.encode()).hexdigest(),
                    "exit_code": actual.returncode, "stdout": actual.stdout, "stderr": actual.stderr,
                    "parsed": parsed.model_dump(mode="json"), "parsed_ok": parsed.ok}

        run("git", "init", "-q")
        first = commit("baseline")
        present = probe(first)
        missing = "f" * 40
        absent_check = run("git", "cat-file", "-e", missing + "^{commit}", check=False)
        assert first != missing and absent_check.returncode != 0
        missing_result = probe(missing)
        second = commit("child")
        third = commit("grandchild")
        mismatch_result = probe(first)
        fsck = run("git", "fsck", "--full", check=False)
        assert present["exit_code"] == 0 and present["parsed_ok"]
        assert missing_result["exit_code"] != 0 and missing_result["stdout"].strip() == "HEAD=" + first
        assert mismatch_result["exit_code"] == 0 and not mismatch_result["parsed_ok"]
        assert mismatch_result["parsed"]["base_object_ok"] is True
        assert fsck.returncode == 0
        return {"present_control": present, "missing_base": missing_result,
                "head_mismatch": mismatch_result, "temporary_commits": [first, second, third],
                "fsck_exit_code": fsck.returncode, "temporary_repository_removed": True}


async def lineage_case(kind: str, output: dict) -> dict:
    task = dataclasses.replace(make_task(TASK_ID_DENSE), base_commit=output["expected_base"])
    chain = _formal_chain(task=task)
    orch, notices = chain.orchestrator, []
    original_docker = orch._docker
    injected = []

    async def io(*args, input_bytes=None):
        if args[0] == "exec" and args[-1] == build_probe_script(task.base_commit):
            injected.append({"exit_code": output["exit_code"], "stdout": output["stdout"],
                             "stderr": output["stderr"]})
            return ExecResult(output["exit_code"], output["stdout"], output["stderr"])
        return await original_docker(*args, input_bytes=input_bytes)

    orch._docker = io
    token = fatal_halt_notifier.set(notices.append)
    fatal, delivered = None, []
    try:
        delivered = await orch.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    except FatalExecutionInfrastructureError as exc:
        fatal = exc.reason_code
    finally:
        fatal_halt_notifier.reset(token)
    audit, receipt = orch.audits[-1], chain.finalization.receipts[-1]
    result = {
        "case": kind, "mode": orch._mode, "raw_io": injected, "fatal": fatal,
        "outcome": audit.outcome_v2, "receipt_disposition": receipt.attempt_disposition,
        "receipt_reason": receipt.terminal_reason_code,
        "halt_notifications": [e.reason_code for e in notices],
        "delivered_statuses": [getattr(s.status, "value", s.status) for s in delivered],
        "delivered_remove_sample": [s.remove_sample for s in delivered],
        "failure_records": [dataclasses.asdict(f) for f in audit.failure_records],
        "grading_calls": len(chain.grading.calls), "container_rm_count": len(chain.docker.removed),
        "cleaned": "cleanup_completed" in _steps(audit),
    }
    assert len(injected) == 1 and result["mode"] == "fa_formal"
    assert result["grading_calls"] == 0 and result["container_rm_count"] == 1 and result["cleaned"]
    if kind == "head_mismatch_with_base_present":
        assert fatal == "rollout_testbed_lineage_failed" and len(notices) == 1
        assert receipt.attempt_disposition == "fatal_run_halt" and audit.outcome_v2 is None and not delivered
    else:
        # 当前实现的复现断言：缺对象与传输失败共用 task-local 分类；不是修复验收 oracle。
        assert fatal is None and not notices
        assert receipt.attempt_disposition == "aborted" and receipt.terminal_reason_code == "rollout_testbed_probe_failed"
        assert audit.outcome_v2["completion_class"] == "missing"
        assert result["delivered_statuses"] == ["aborted"] and result["delivered_remove_sample"] == [True]
    return result


async def main():
    paths = (
        "rh2/src/repoharness2/adapters/slime/execution_scope.py",
        "rh2/src/repoharness2/adapters/slime/quiescence_barrier.py",
        "rh2/src/repoharness2/adapters/slime/generate.py",
        "rh2/src/repoharness2/adapters/slime/outcome_producer.py",
        "rh2/src/repoharness2/envpack/materialize.py",
    )
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    print(json.dumps({"case": "source_snapshot", "source_sha256": before}, ensure_ascii=False), flush=True)
    for late in (False, True):
        print(json.dumps(await stop_case(late_postprocessing=late), ensure_ascii=False), flush=True)
    actual = real_lineage_outputs()
    print(json.dumps({"case": "real_git_producer", **actual}, ensure_ascii=False), flush=True)
    for kind, data in (
        ("base_missing_in_intact_repository", actual["missing_base"]),
        ("head_mismatch_with_base_present", actual["head_mismatch"]),
        ("docker_transport_failure_control", {"expected_base": "a" * 40, "exit_code": 1,
          "stdout": "", "stderr": "Cannot connect to the Docker daemon (CPU IO control)"}),
    ):
        print(json.dumps(await lineage_case(kind, data), ensure_ascii=False), flush=True)
    assert before == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}


if __name__ == "__main__":
    asyncio.run(main())
