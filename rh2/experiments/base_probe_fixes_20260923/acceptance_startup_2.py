"""基座探针修复 #1/#2 的真实验收（Brief §4 SR4）：真实 CC 2.1.205 + 桩端点，经正式 `ClaudeCodeDriver.run`。

容器、relay、网络、可信初始化、激活文件、启动前探针、激活核查全部走正式函数（与 B 线 solve_attempt.py
同一套装配），只有模型端点是桩（stub_anthropic_endpoint.py，由本脚本拉起）。场景：

  normal       桩让 CC 用 Bash 跑解释器检查与"模型可见面"检查，然后 end_turn：期望退出 0、宿主轨迹完整
               （result 事件在场、trajectory 里的 message_start 数 = 桩收到的 /v1/messages 数）、工具结果里
               sys.executable 落在声明前缀下、容器内无 .harness / /tmp/.run.*、git status 干净、/rh2/bash_env 不可写
  time_budget  桩在第 2 个请求上挂住：期望 driver 返回 -1（EXIT_TIME_BUDGET_EXCEEDED）、harness_log partial=time_budget、
               已收到的部分保留；记录容器内 agent 进程是否残留（生产由 execution_scope 屏障 pkill）
  max_turns    桩无限给 tool_use，CC `--max-turns 3`：期望 CC 自己以非零退出、result 事件 subtype 为 error_max_turns
  cut_stream   桩在第 2 个请求 content_block_start 之后断开连接（#3 复现用；只记录事实，不设期望）

    SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz \
    .venv/bin/python experiments/base_probe_fixes_20260923/acceptance_startup_2.py \
        --prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422 \
        --scenario normal --out-dir /work/probe/runs/acc2_normal --attempt-id acc2normal01
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

PY_CHECK = "python -c 'import sys,os; print(\"RH2_SYS_EXECUTABLE=\" + sys.executable); print(\"RH2_CONDA=\" + str(os.environ.get(\"CONDA_DEFAULT_ENV\")))'"
VISIBLE_SURFACE = (
    "ls -la /testbed/.harness /tmp/.run.sh /tmp/.run.done 2>&1 | head -5; "
    "echo RH2_GIT_STATUS_LINES=$(git -C /testbed status --porcelain | wc -l); "
    "echo RH2_BASHENV_WRITE=$( ( : >> /rh2/bash_env ) 2>/dev/null && echo WRITABLE || echo DENIED ); "
    "echo RH2_PYTHON=$(command -v python); echo RH2_CONDA_ENV=$CONDA_DEFAULT_ENV; echo RH2_HOME=$HOME; echo RH2_BASH_ENV=$BASH_ENV"
)


def scenario_script(name: str) -> list[dict]:
    bash = lambda cmd: {"kind": "tool_use", "name": "Bash", "input": {"command": cmd}}  # noqa: E731
    if name == "normal":
        return [bash(PY_CHECK), bash(VISIBLE_SURFACE), {"kind": "text", "text": "Acceptance checks done."}]
    if name == "time_budget":
        return [bash(PY_CHECK), {"kind": "hang", "seconds": 3600}]
    if name == "max_turns":
        return [bash(f"echo RH2_TURN={i}") for i in range(12)]
    if name == "cut_stream":
        return [bash(PY_CHECK), {"kind": "cut", "after": "content_block_start"}, {"kind": "text", "text": "after cut"}]
    raise SystemExit(f"unknown scenario {name}")


def summarize_stream(text: str) -> dict[str, Any]:
    tools: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    stream_events: Counter[str] = Counter()
    result: dict[str, Any] = {}
    init: dict[str, Any] = {}
    tool_results: list[str] = []
    bad_lines = 0
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            ev = json.loads(ln)
        except Exception:  # noqa: BLE001
            bad_lines += 1
            continue
        kind = ev.get("type")
        kinds[kind] += 1
        if kind == "system" and ev.get("subtype") == "init":
            init = {k: ev.get(k) for k in ("model", "permissionMode", "claude_code_version", "cwd") if k in ev}
        elif kind == "stream_event":
            stream_events[(ev.get("event") or {}).get("type", "?")] += 1
        elif kind == "assistant":
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tools[blk.get("name", "?")] += 1
        elif kind == "user":
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_result":
                    c = blk.get("content")
                    tool_results.append(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False))
        elif kind == "result":
            result = {k: ev.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "stop_reason") if k in ev}
    return {"event_kinds": dict(kinds), "stream_events": dict(stream_events), "tool_calls": dict(tools),
            "tool_results": [t[:1500] for t in tool_results], "cc_result": result, "init": init, "bad_lines": bad_lines,
            "has_result_event": bool(result), "message_start_count": stream_events.get("message_start", 0)}


def _sha256(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


class Runner:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.ns = ns
        self.out = Path(ns.out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.rec: dict[str, Any] = {"scenario": ns.scenario, "attempt_id": ns.attempt_id, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                    "stages": {}, "timings": {}, "checks": {}}
        self.container: str | None = None
        self.network = None
        self.relay = None
        self.pool = None
        self.profile = None
        self.docker = None
        self.stub: subprocess.Popen | None = None

    def save(self) -> None:
        tmp = self.out / ".attempt.json.tmp"
        tmp.write_text(json.dumps(self.rec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, self.out / "attempt.json")

    def stage(self, name: str, **facts: Any) -> None:
        self.rec["stages"][name] = {"at": round(time.time(), 3), **facts}
        self.save()

    async def dk(self, *args: str, timeout: float = 120.0, input_bytes: bytes | None = None):
        from repoharness2.adapters.slime.sandbox_profile import _call

        return await _call(self.docker, *args, timeout=timeout, input_bytes=input_bytes)

    async def sh(self, script: str, *, user: str = "root", timeout: float = 120.0, env: dict[str, str] | None = None,
                 input_bytes: bytes | None = None):
        args = ["exec"]
        if input_bytes is not None:
            args.append("-i")
        args += ["-u", user]
        if user != "root":
            args += ["-e", f"HOME=/home/{self.profile.agent_user}"]
        for k, v in (env or {}).items():
            args += ["-e", f"{k}={v}"]
        args += [self.container, "bash", "-c", script]
        return await self.dk(*args, timeout=timeout, input_bytes=input_bytes)

    # ------------------------------------------------------------------ 桩端点
    def start_stub(self) -> None:
        script = scenario_script(self.ns.scenario)
        (self.out / "stub_script.json").write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
        stub_out = self.out / "stub"
        stub_out.mkdir(exist_ok=True)
        self.stub = subprocess.Popen(
            [sys.executable, str(HERE / "stub_anthropic_endpoint.py"), "--listen-host", self.ns.stub_host, "--listen-port", str(self.ns.stub_port),
             "--script", str(self.out / "stub_script.json"), "--out-dir", str(stub_out)],
            stdout=open(self.out / "stub_stdout.log", "ab"), stderr=subprocess.STDOUT,
        )
        import urllib.request

        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://{self.ns.stub_host}:{self.ns.stub_port}/__stub_health", timeout=1) as r:
                    if r.status == 200:
                        break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        else:
            raise SystemExit("stub endpoint did not come up")
        self.stage("stub_started", host=self.ns.stub_host, port=self.ns.stub_port, pid=self.stub.pid)

    def stub_counts(self) -> dict[str, int]:
        import urllib.request

        with urllib.request.urlopen(f"http://{self.ns.stub_host}:{self.ns.stub_port}/__stub_health", timeout=3) as r:
            return json.loads(r.read())

    # ------------------------------------------------------------------ 主流程
    async def run(self) -> int:
        ns = self.ns
        os.environ.setdefault("RH2_BRINGUP_ARTIFACT_DIR", str(self.out / "bringup_artifacts"))
        Path(os.environ["RH2_BRINGUP_ARTIFACT_DIR"]).mkdir(parents=True, exist_ok=True)
        from repoharness2.adapters.slime.prepared_task_face import rollout_spec_from_view
        from repoharness2.adapters.slime.replay_grade import load_context
        from repoharness2.adapters.slime.sandbox_profile import (
            EgressSubnetPool, agent_shell_env, connect_relay_to_network, create_attempt_network, default_docker_runner,
            grader_profile_from_env, rollout_profile_from_env, rollout_trusted_init_script, run_git_sanitize,
            run_rollout_activation_check, run_rollout_prelaunch_check, run_trusted_init, start_egress_relay,
        )
        from repoharness2.envpack import materialize

        self.docker = default_docker_runner
        summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
        profile = rollout_profile_from_env(os.environ, model_proxy_upstream_host=ns.stub_host, model_proxy_upstream_port=int(ns.stub_port))
        self.profile = profile
        ctx = load_context(
            prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"], manifest_sha256=summary["prepared_manifest_sha256"],
            rollout_profile=profile, grader_profile=grader_profile_from_env(os.environ), artifacts_dir=self.out / "unused_artifacts",
            run_id=ns.attempt_id,
        )
        task_id = ctx.resolve_task_id(ns.task)
        spec = rollout_spec_from_view(ctx.rollout_views[task_id], time_budget_seconds=int(ns.wall_seconds))
        self.rec.update({
            "task_id": task_id, "image": spec.image, "base_commit": spec.base_commit, "workdir": spec.workdir,
            "expected_interpreter_prefix": spec.expected_interpreter_prefix,
            "env_activation_script_sha256": "sha256:" + hashlib.sha256(spec.env_activation_script.encode()).hexdigest(),
            "profile_digest": profile.digest(), "wall_seconds": ns.wall_seconds, "cc_extra_args": ns.cc_extra_args,
            "cc_platform_tarball_sha256": _sha256(Path(os.environ["SLIME_AGENT_CC_PLATFORM_TARBALL"])),
        })
        self.save()
        self.start_stub()

        labels = ("--label", f"rh2.run_id={ns.attempt_id}", "--label", "rh2.acceptance=startup_2")
        name = f"rh2acc-{re.sub(r'[^A-Za-z0-9_.-]', '-', task_id.split('::')[-1])[:28]}-{uuid.uuid4().hex[:8]}"
        t = time.monotonic()
        self.relay = await start_egress_relay(self.docker, profile, run_id=ns.attempt_id, labels=labels)
        self.pool = EgressSubnetPool(profile.egress_subnet_pool, profile.egress_subnet_prefix)
        self.network = await create_attempt_network(self.docker, profile=profile, pool=self.pool, name=f"{name}-net", labels=labels, max_slots=512)
        await connect_relay_to_network(self.docker, relay=self.relay, network=self.network)
        run = await self.dk(*profile.docker_run_args(name=name, network=self.network.name, image=spec.image, labels=labels), timeout=300)
        if run.exit_code != 0:
            return self.fail("container_start_failed", (run.stderr or run.stdout)[-400:])
        self.container = name
        self.rec["container"] = name
        self.rec["timings"]["network_and_container"] = round(time.monotonic() - t, 3)
        self.stage("container_started", relay=self.relay.container_name, network=self.network.name)

        # sanitize → 可信初始化（建 /rh2）
        try:
            san = await run_git_sanitize(self.docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
            init = await run_trusted_init(self.docker, name=name, script=rollout_trusted_init_script(profile), timeout=profile.init_timeout_seconds)
        except RuntimeError as exc:
            return self.fail("sanitize_or_init_failed", str(exc)[:400])
        self.stage("sanitize_and_init", git_sanitize=san, trusted_init=init)
        head = san.get("HEAD_AFTER")

        # 激活文件：与 generate.py 同一条写入脚本（stdin 经 docker exec -i）
        path = materialize.BASH_ENV_PATH
        w = await self.sh(f"mkdir -p $(dirname {path}) && cat > {path} && chmod 0644 {path}", input_bytes=spec.env_activation_script.encode(), timeout=120)
        if w.exit_code != 0:
            return self.fail("activation_write_failed", w.stderr[-300:])
        stat = await self.sh(f"stat -c '%u:%a' {path} $(dirname {path})", timeout=60)
        self.stage("activation_file_written", path=path, stat=stat.stdout.split())

        # 启动前探针（含激活文件三项）→ 激活核查（agent 身份、CC 同形 env）
        pre = await run_rollout_prelaunch_check(self.docker, name=name, profile=profile, network=self.network.name, expected_head=head, activation_file=path)
        (self.out / "prelaunch.json").write_text(json.dumps(pre.to_dict(), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        self.stage("prelaunch_check", ok=pre.ok, violations=list(pre.violations))
        if not pre.ok:
            return self.fail("prelaunch_check_failed", "; ".join(pre.violations)[:600])
        env_inj = agent_shell_env(profile, activation_file=path)
        act = await run_rollout_activation_check(self.docker, name=name, profile=profile, env=env_inj, expected_interpreter_prefix=spec.expected_interpreter_prefix)
        (self.out / "activation_check.json").write_text(json.dumps(act.to_dict(), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        self.stage("activation_check", ok=act.ok, violations=list(act.violations), facts=dict(act.probe_facts))
        if not act.ok:
            return self.fail("activation_check_failed", "; ".join(act.violations)[:600])
        # 工作区静止基线：以激活文件 mtime 为界，之后被写的 /testbed 文件应为空
        await self.sh("touch /rh2/.acceptance_t0", timeout=30)

        # 正式 driver
        exit_code = await self.solve(spec, env_inj)

        # 运行后事实（root 视角 + agent 视角）
        facts_root = await self.sh(
            f"cd {shlex.quote(spec.workdir)}; echo RH2_HARNESS_DIR=$(test -e .harness && echo PRESENT || echo ABSENT); "
            "echo RH2_RUN_SH=$(test -e /tmp/.run.sh && echo PRESENT || echo ABSENT); echo RH2_RUN_DONE=$(test -e /tmp/.run.done && echo PRESENT || echo ABSENT); "
            "echo RH2_GIT_STATUS_LINES=$(git status --porcelain | wc -l); echo RH2_AGENT_PROCS=$(ps -u agent -o pid= 2>/dev/null | wc -l); "
            "echo RH2_NEWER_FILES=$(find /testbed -newer /rh2/.acceptance_t0 -not -path '*/.git' -not -path '*/.git/*' 2>/dev/null | wc -l); "
            "find /testbed -newer /rh2/.acceptance_t0 -not -path '*/.git' -not -path '*/.git/*' 2>/dev/null | head -20",
            timeout=120,
        )
        (self.out / "post_run_facts_root.txt").write_text(facts_root.stdout + "\n--- stderr ---\n" + facts_root.stderr, encoding="utf-8")
        kv = {ln.split("=", 1)[0]: ln.split("=", 1)[1] for ln in facts_root.stdout.splitlines() if ln.startswith("RH2_") and "=" in ln}
        self.rec["post_run_facts"] = kv
        if int(kv.get("RH2_AGENT_PROCS", "0") or 0) > 0:
            # 生产由 execution_scope 屏障终止（pkill -u agent）；这里记录残留并同样收口
            kill = await self.sh("ps -u agent -o pid=,etimes=,comm= | head -20; pkill -KILL -u agent; sleep 2; echo RH2_AGENT_PROCS_AFTER=$(ps -u agent -o pid= | wc -l)", timeout=60)
            self.rec["agent_procs_leftover"] = kill.stdout
        self.rec["stub_counts_final"] = self.stub_counts()
        self.rec["result"] = "ran"
        self.evaluate()
        self.save()
        return 0 if exit_code is not None else 3

    async def solve(self, spec, env_inj: dict[str, str]) -> int | None:
        ns = self.ns
        from repoharness2.adapters.slime.bringup import ClaudeCodeDriver
        from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS

        os.environ["SLIME_AGENT_CC_EXTRA_ARGS"] = ns.cc_extra_args
        driver = ClaudeCodeDriver()
        launch_facts: dict[str, Any] = {}
        token = HARNESS_LAUNCH_FACTS.set(launch_facts)
        t = time.monotonic()
        exit_code: int | None = None
        try:

            class _Box:
                container_name = self.container

            exit_code = await asyncio.wait_for(
                driver.run(_Box(), workdir=spec.workdir, session_id=ns.attempt_id, adapter_url=self.profile.harness_adapter_url(),
                           time_budget_sec=int(ns.wall_seconds), prompt=ns.prompt, env_injections=env_inj, harness_log_dir=str(self.out / "harness")),
                timeout=float(ns.wall_seconds) + 300.0,
            )
            termination = "returned"
        except asyncio.TimeoutError:
            termination = "outer_guard_timeout"
        except Exception as exc:  # noqa: BLE001 - 如实记录 typed 码
            termination = f"driver_exception:{type(exc).__name__}"
            self.rec["driver_exception"] = f"{exc}"[:800]
        finally:
            HARNESS_LAUNCH_FACTS.reset(token)
        self.rec.update({"harness_exit_code": exit_code, "termination": termination, "solve_seconds": round(time.monotonic() - t, 3),
                         "launch_facts": launch_facts, "cc_version_observed": getattr(driver, "cc_version_observed", None)})
        traj = self.out / "harness" / "trajectory.jsonl"
        text = traj.read_text(encoding="utf-8", errors="replace") if traj.exists() else ""
        self.rec["trajectory_bytes"] = len(text.encode("utf-8"))
        self.rec["trajectory_summary"] = summarize_stream(text)
        err = self.out / "harness" / "stderr.log"
        self.rec["stderr_tail"] = err.read_text(encoding="utf-8", errors="replace")[-1500:] if err.exists() else ""
        self.save()
        return exit_code

    def evaluate(self) -> None:
        """场景期望 → checks（True/False），不改事实。"""
        r = self.rec
        hl = (r.get("launch_facts") or {}).get("harness_log") or {}
        ts = r.get("trajectory_summary") or {}
        kv = r.get("post_run_facts") or {}
        stub_msgs = (r.get("stub_counts_final") or {}).get("messages")
        prefix = r.get("expected_interpreter_prefix") or ""
        tool_results = ts.get("tool_results") or []
        py_ok = any(f"RH2_SYS_EXECUTABLE={prefix}/" in t for t in tool_results)
        c = r["checks"]
        c["interpreter_in_tool_result"] = py_ok
        c["host_log_present"] = bool(hl.get("stdout_path")) and r.get("trajectory_bytes", 0) > 0
        c["no_harness_dir_in_container"] = kv.get("RH2_HARNESS_DIR") == "ABSENT"
        c["no_launcher_or_done_marker"] = kv.get("RH2_RUN_SH") == "ABSENT" and kv.get("RH2_RUN_DONE") == "ABSENT"
        c["git_status_clean"] = kv.get("RH2_GIT_STATUS_LINES") == "0"
        c["no_files_written_under_testbed"] = kv.get("RH2_NEWER_FILES") == "0"
        c["message_start_matches_stub_requests"] = stub_msgs is not None and ts.get("message_start_count") == stub_msgs
        s = r["scenario"]
        if s == "normal":
            c["exit_code_zero"] = r.get("harness_exit_code") == 0
            c["result_event_present"] = bool(ts.get("has_result_event"))
            c["log_complete"] = hl.get("log_complete") is True
            c["bashenv_denied_for_agent"] = any("RH2_BASHENV_WRITE=DENIED" in t for t in tool_results)
        elif s == "time_budget":
            c["exit_code_minus_one"] = r.get("harness_exit_code") == -1
            c["partial_reason_time_budget"] = hl.get("log_partial_reason") == "time_budget" and hl.get("log_complete") is False
            c["first_tool_result_kept"] = py_ok
        elif s == "max_turns":
            c["exit_code_nonzero"] = (r.get("harness_exit_code") or 0) != 0
            c["result_event_present"] = bool(ts.get("has_result_event"))
            c["result_subtype"] = (ts.get("cc_result") or {}).get("subtype")
        c["all_expected_ok"] = all(v is True for k, v in c.items() if k not in ("result_subtype", "all_expected_ok"))

    def fail(self, code: str, detail: str) -> int:
        self.rec["result"] = f"infra_failed:{code}"
        self.rec["failure_detail"] = detail
        self.save()
        return 3

    async def cleanup(self) -> None:
        from repoharness2.adapters.slime.sandbox_profile import stop_egress_relay, teardown_attempt_network

        c: dict[str, Any] = {}
        if self.container:
            rm = await self.dk("rm", "-f", self.container, timeout=180)
            c["container_rm"] = rm.exit_code
        if self.network is not None:
            c["network_failures"] = await teardown_attempt_network(self.docker, network_name=self.network.name, relay=self.relay, pool=self.pool, subnet=self.network.subnet)
        if self.relay is not None:
            c["relay_failures"] = await stop_egress_relay(self.docker, self.relay)
        if self.stub is not None:
            self.stub.terminate()
            try:
                self.stub.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.stub.kill()
            c["stub_rc"] = self.stub.returncode
        left = await self.dk("ps", "-a", "--filter", f"label=rh2.run_id={self.ns.attempt_id}", "--format", "{{.Names}}", timeout=60)
        nets = await self.dk("network", "ls", "--filter", f"label=rh2.run_id={self.ns.attempt_id}", "--format", "{{.Name}}", timeout=60)
        c["labeled_containers_left"] = left.stdout.split()
        c["labeled_networks_left"] = nets.stdout.split()
        self.rec["cleanup"] = c
        self.rec["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.save()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--scenario", choices=("normal", "time_budget", "max_turns", "cut_stream"), required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--attempt-id", required=True, help="也是 relay 会话 token 形状：[A-Za-z0-9_.-]{6,96}")
    ap.add_argument("--stub-host", default="172.17.0.1")
    ap.add_argument("--stub-port", type=int, default=18090)
    ap.add_argument("--wall-seconds", type=int, default=600)
    ap.add_argument("--cc-extra-args", default="--disallowedTools Task WebFetch WebSearch --max-turns 8")
    ap.add_argument("--prompt", default="Acceptance run: execute exactly the tool calls you are given, then stop.")
    ns = ap.parse_args(argv)
    if not re.match(r"^[A-Za-z0-9_.-]{6,96}$", ns.attempt_id):
        ap.error("--attempt-id 形态不合法")
    if not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL")
    if ns.scenario == "max_turns":
        ns.cc_extra_args = "--disallowedTools Task WebFetch WebSearch --max-turns 3"
    runner = Runner(ns)

    async def go() -> int:
        try:
            return await runner.run()
        finally:
            await runner.cleanup()

    rc = asyncio.run(go())
    print(json.dumps({"result": runner.rec.get("result"), "harness_exit_code": runner.rec.get("harness_exit_code"),
                      "termination": runner.rec.get("termination"), "checks": runner.rec.get("checks"),
                      "failure_detail": runner.rec.get("failure_detail")}, ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
