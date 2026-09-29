"""决策包 #8/#9/#10 事实采集：真实 CC 2.1.205 + 桩端点，经正式 `ClaudeCodeDriver.run`。

复制自 `experiments/base_probe_fixes_20260923/acceptance_startup_2.py`（原脚本不改）：容器、relay、网络、可信初始化、
激活文件、启动前探针、激活核查、driver 全部走正式函数，只有模型端点是桩（本目录 stub_p8910.py）。本脚本新增：

  场景  probe     Bash echo → end_turn（#10 工具面 / #9 memory 的首请求）
        memwrite  第 1 步让 CC 用 Bash 把 autoMemoryEnabled:false 写进 ~/.claude/settings.json，看第 2 个请求的 system 是否变化
        bigread   第 1 步 Bash 生成 /tmp/p8_big.py（约 180 KB、1,800 行），第 2 步 Read 它（#8 i/ii）
        ramp      N 步 Bash echo；配合桩的 --usage-start/--usage-step 报递增 usage（#8 iii）
        reactive  第 3 个主循环请求回 400 "prompt is too long: 40000 tokens > 32768 maximum"（#8 iii 的被动压缩）
        bigread_limit  同 bigread，但 Read 显式带 offset=1 limit=1800（超限时走报错分支而不是截断分支）
        emptylen  第 3 个主循环请求回空 text + stop_reason=max_tokens（vendored adapter 在 prompt ≥ max_context_tokens 时的回复形状）
        emptylen_repeat  第 2 个主循环请求起连续 6 次回上述空回复（真实溢出时重发必然再溢出）
  --cc-extra-envs JSON   经 SLIME_AGENT_CC_EXTRA_ENVS 并入 CC 进程环境（与生产同一通道；driver 再并入训练守卫）
  --settings-extra JSON  只在本实验进程内包装 vendored ClaudeCodeHarness.write_config：写入的 settings JSON 追加这些键
                         （模拟"write_config 里加 autoMemoryEnabled:false"这一候选修法；不改任何源文件）
  --stub-extra-args      原样传给桩（--count-tokens-mode / --usage-start / --usage-step）

    SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz \
    .venv/bin/python experiments/decision_package_20260924/p8_9_10/run_p8910.py \
        --prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422 \
        --scenario probe --out-dir /work/probe/runs/dp_t10_base --attempt-id dp8t10base --stub-port 18101
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

BIG_FILE = "/tmp/p8_big.py"
GEN_BIG = (
    "python3 -c \"import sys\n"
    "lines=['# p8 big file for Read token-limit probe\\n']\n"
    "for i in range(1, 1800):\n"
    "    lines.append('    value_%05d = compute_something(alpha=%d, beta=\\'%s\\', gamma=[%d, %d, %d])  # line %d\\n' % (i, i, 'x'*40, i, i+1, i+2, i))\n"
    f"open('{BIG_FILE}','w').write(''.join(lines))\n"
    "print('RH2_BIG_BYTES=%d RH2_BIG_LINES=%d' % (sum(len(l) for l in lines), len(lines)))\"; "
    f"wc -c {BIG_FILE}; wc -l {BIG_FILE}"
)
PROMPT_TOO_LONG = {"type": "error", "error": {"type": "invalid_request_error", "message": "prompt is too long: 40000 tokens > 32768 maximum"}}
SETTINGS_WITH_MEMORY_OFF = '{"hasCompletedOnboarding":true,"bypassPermissionsModeAccepted":true,"autoMemoryEnabled":false}'


def scenario_script(name: str, ramp_steps: int) -> list[dict]:
    bash = lambda cmd: {"kind": "tool_use", "name": "Bash", "input": {"command": cmd}}  # noqa: E731
    if name == "probe":
        return [bash("echo RH2_PROBE_OK"), {"kind": "text", "text": "Probe done."}]
    if name == "memwrite":
        return [bash(f"printf '%s' '{SETTINGS_WITH_MEMORY_OFF}' > $HOME/.claude/settings.json && cat $HOME/.claude/settings.json"),
                bash("echo RH2_AFTER_SETTINGS_WRITE"), {"kind": "text", "text": "Memwrite done."}]
    if name == "bigread":
        return [bash(GEN_BIG), {"kind": "tool_use", "name": "Read", "input": {"file_path": BIG_FILE}}, {"kind": "text", "text": "Bigread done."}]
    if name == "ramp":
        return [bash(f"echo RH2_RAMP_{i}") for i in range(ramp_steps)] + [{"kind": "text", "text": "Ramp done."}]
    if name == "bigread_limit":
        return [bash(GEN_BIG), {"kind": "tool_use", "name": "Read", "input": {"file_path": BIG_FILE, "offset": 1, "limit": 1800}},
                {"kind": "text", "text": "Bigread-limit done."}]
    if name == "emptylen":
        # 第 3 个主循环请求回 vendored adapter 溢出时的形状：空 text 块 + stop_reason=max_tokens（common.py:457–467）
        return [bash("echo RH2_E1"), bash("echo RH2_E2"),
                {"kind": "text", "text": "", "stop_reason": "max_tokens", "output_tokens": 0, "input_tokens": 33000},
                bash("echo RH2_E3_AFTER_EMPTY"), {"kind": "text", "text": "Emptylen done."}]
    if name == "emptylen_repeat":
        # 真实溢出时每次重发都会再溢出：连续 6 次回空 text + max_tokens，看 CC 的恢复次数与收尾
        empty = {"kind": "text", "text": "", "stop_reason": "max_tokens", "output_tokens": 0, "input_tokens": 33000}
        return [bash("echo RH2_E1")] + [dict(empty) for _ in range(6)] + [{"kind": "text", "text": "Emptylen-repeat done."}]
    if name == "reactive":
        return [bash("echo RH2_R1"), bash("echo RH2_R2"), {"kind": "http_error", "status": 400, "body": PROMPT_TOO_LONG},
                bash("echo RH2_R3_AFTER_PTL"), {"kind": "text", "text": "Reactive done."}]
    raise SystemExit(f"unknown scenario {name}")


def summarize_stream(text: str) -> dict[str, Any]:
    tools: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    stream_events: Counter[str] = Counter()
    system_subtypes: Counter[str] = Counter()
    system_events: list[dict] = []
    result: dict[str, Any] = {}
    init: dict[str, Any] = {}
    tool_results: list[dict] = []
    assistant_texts: list[str] = []
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
        if kind == "system":
            st = ev.get("subtype")
            system_subtypes[st] += 1
            if st == "init":
                init = {k: ev.get(k) for k in ("model", "permissionMode", "claude_code_version", "cwd", "tools", "skills", "slash_commands",
                                                "agents", "memory_paths", "mcp_servers", "plugins", "output_style") if k in ev}
            elif st != "status" or ev.get("status") not in ("requesting",):
                system_events.append({k: v for k, v in ev.items() if k not in ("uuid", "session_id")})
        elif kind == "stream_event":
            stream_events[(ev.get("event") or {}).get("type", "?")] += 1
        elif kind == "assistant":
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tools[blk.get("name", "?")] += 1
                elif isinstance(blk, dict) and blk.get("type") == "text":
                    assistant_texts.append(blk.get("text", "")[:300])
        elif kind == "user":
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_result":
                    c = blk.get("content")
                    s = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
                    tool_results.append({"chars": len(s), "is_error": blk.get("is_error"), "head": s[:1200]})
        elif kind == "result":
            result = {k: v for k, v in ev.items() if k not in ("uuid", "session_id")}
    return {"event_kinds": dict(kinds), "stream_events": dict(stream_events), "system_subtypes": dict(system_subtypes),
            "system_events": system_events[:40], "tool_calls": dict(tools), "tool_results": tool_results, "assistant_texts": assistant_texts[:20],
            "cc_result": result, "init": init, "bad_lines": bad_lines, "has_result_event": bool(result),
            "message_start_count": stream_events.get("message_start", 0)}


def _sha256(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def patch_write_config(extra: dict[str, Any]) -> None:
    """只在本实验进程内：让 vendored write_config 写入的 settings JSON 追加 extra 键（其余与 vendored 逐字相同）。"""
    from slime.agent.harness import ClaudeCodeHarness

    async def write_config(self, sb, ctx) -> None:  # noqa: ANN001
        settings = json.dumps({"hasCompletedOnboarding": True, "bypassPermissionsModeAccepted": True, **extra})
        await sb.exec(
            "mkdir -p /home/agent/.claude && "
            f"echo {shlex.quote(settings)} "
            "| tee /home/agent/.claude.json /home/agent/.claude/settings.json > /dev/null && "
            "chown -R agent:agent /home/agent/.claude /home/agent/.claude.json",
            user="root", check=True, timeout=60,
        )

    ClaudeCodeHarness.write_config = write_config


class Runner:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.ns = ns
        self.out = Path(ns.out_dir)
        self.out.mkdir(parents=True, exist_ok=True)
        self.rec: dict[str, Any] = {"scenario": ns.scenario, "attempt_id": ns.attempt_id, "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                    "stages": {}, "timings": {}, "checks": {}, "condition": {
                                        "cc_extra_args": ns.cc_extra_args, "cc_extra_envs": ns.cc_extra_envs, "settings_extra": ns.settings_extra,
                                        "stub_extra_args": ns.stub_extra_args, "ramp_steps": ns.ramp_steps, "label": ns.label}}
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
        script = scenario_script(self.ns.scenario, self.ns.ramp_steps)
        (self.out / "stub_script.json").write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
        stub_out = self.out / "stub"
        stub_out.mkdir(exist_ok=True)
        self.stub = subprocess.Popen(
            [sys.executable, str(HERE / "stub_p8910.py"), "--listen-host", self.ns.stub_host, "--listen-port", str(self.ns.stub_port),
             "--script", str(self.out / "stub_script.json"), "--out-dir", str(stub_out), *shlex.split(self.ns.stub_extra_args)],
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
            "expected_interpreter_prefix": spec.expected_interpreter_prefix, "profile_digest": profile.digest(), "wall_seconds": ns.wall_seconds,
            "cc_platform_tarball_sha256": _sha256(Path(os.environ["SLIME_AGENT_CC_PLATFORM_TARBALL"])),
        })
        self.save()
        self.start_stub()

        labels = ("--label", f"rh2.run_id={ns.attempt_id}", "--label", "rh2.acceptance=dp8_p8910")
        name = f"rh2dp8-{re.sub(r'[^A-Za-z0-9_.-]', '-', task_id.split('::')[-1])[:24]}-{uuid.uuid4().hex[:8]}"
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

        try:
            san = await run_git_sanitize(self.docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
            init = await run_trusted_init(self.docker, name=name, script=rollout_trusted_init_script(profile), timeout=profile.init_timeout_seconds)
        except RuntimeError as exc:
            return self.fail("sanitize_or_init_failed", str(exc)[:400])
        self.stage("sanitize_and_init", git_sanitize=san, trusted_init=init)
        head = san.get("HEAD_AFTER")

        path = materialize.BASH_ENV_PATH
        w = await self.sh(f"mkdir -p $(dirname {path}) && cat > {path} && chmod 0644 {path}", input_bytes=spec.env_activation_script.encode(), timeout=120)
        if w.exit_code != 0:
            return self.fail("activation_write_failed", w.stderr[-300:])
        self.stage("activation_file_written", path=path)

        pre = await run_rollout_prelaunch_check(self.docker, name=name, profile=profile, network=self.network.name, expected_head=head, activation_file=path)
        (self.out / "prelaunch.json").write_text(json.dumps(pre.to_dict(), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        self.stage("prelaunch_check", ok=pre.ok, violations=list(pre.violations))
        if not pre.ok:
            return self.fail("prelaunch_check_failed", "; ".join(pre.violations)[:600])
        env_inj = agent_shell_env(profile, activation_file=path)
        act = await run_rollout_activation_check(self.docker, name=name, profile=profile, env=env_inj, expected_interpreter_prefix=spec.expected_interpreter_prefix)
        self.stage("activation_check", ok=act.ok, violations=list(act.violations))
        if not act.ok:
            return self.fail("activation_check_failed", "; ".join(act.violations)[:600])
        await self.sh("touch /rh2/.acceptance_t0", timeout=30)

        exit_code = await self.solve(spec, env_inj)

        facts_root = await self.sh(
            f"cd {shlex.quote(spec.workdir)}; echo RH2_GIT_STATUS_LINES=$(git status --porcelain | wc -l); "
            "echo RH2_AGENT_PROCS=$(ps -u agent -o pid= 2>/dev/null | wc -l); "
            "echo RH2_NEWER_FILES=$(find /testbed -newer /rh2/.acceptance_t0 -not -path '*/.git' -not -path '*/.git/*' 2>/dev/null | wc -l); "
            "echo RH2_MEMDIR=$(test -d /home/agent/.claude/projects/-testbed/memory && echo PRESENT || echo ABSENT); "
            "echo '--- settings.json'; cat /home/agent/.claude/settings.json 2>&1; echo; "
            "echo '--- ~/.claude tree (dirs, depth 4)'; find /home/agent/.claude -maxdepth 4 -type d 2>&1 | sort | head -40; "
            "echo '--- memory dir'; ls -la /home/agent/.claude/projects/-testbed/memory 2>&1 | head -20; "
            "echo '--- git status'; git status --porcelain | head -20",
            timeout=120,
        )
        (self.out / "post_run_facts_root.txt").write_text(facts_root.stdout + "\n--- stderr ---\n" + facts_root.stderr, encoding="utf-8")
        kv = {ln.split("=", 1)[0]: ln.split("=", 1)[1] for ln in facts_root.stdout.splitlines() if ln.startswith("RH2_") and "=" in ln}
        self.rec["post_run_facts"] = kv
        if int(kv.get("RH2_AGENT_PROCS", "0") or 0) > 0:
            kill = await self.sh("ps -u agent -o pid=,etimes=,comm= | head -20; pkill -KILL -u agent; sleep 2; echo RH2_AGENT_PROCS_AFTER=$(ps -u agent -o pid= | wc -l)", timeout=60)
            self.rec["agent_procs_leftover"] = kill.stdout
        self.rec["stub_counts_final"] = self.stub_counts()
        self.rec["result"] = "ran"
        r = self.rec
        ts = r.get("trajectory_summary") or {}
        r["checks"] = {"exit_code_zero": r.get("harness_exit_code") == 0, "result_event_present": bool(ts.get("has_result_event")),
                       "message_start_matches_stub_requests": ts.get("message_start_count") == (r.get("stub_counts_final") or {}).get("messages")}
        self.save()
        return 0 if exit_code is not None else 3

    async def solve(self, spec, env_inj: dict[str, str]) -> int | None:
        ns = self.ns
        from repoharness2.adapters.slime.bringup import ClaudeCodeDriver
        from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS

        os.environ["SLIME_AGENT_CC_EXTRA_ARGS"] = ns.cc_extra_args
        if ns.cc_extra_envs:
            os.environ["SLIME_AGENT_CC_EXTRA_ENVS"] = json.dumps(json.loads(ns.cc_extra_envs), sort_keys=True)
        else:
            os.environ.pop("SLIME_AGENT_CC_EXTRA_ENVS", None)
        if ns.settings_extra:
            patch_write_config(json.loads(ns.settings_extra))
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
        except Exception as exc:  # noqa: BLE001
            termination = f"driver_exception:{type(exc).__name__}"
            self.rec["driver_exception"] = f"{exc}"[:800]
        finally:
            HARNESS_LAUNCH_FACTS.reset(token)
        self.rec.update({"harness_exit_code": exit_code, "termination": termination, "solve_seconds": round(time.monotonic() - t, 3),
                         "launch_facts": launch_facts, "cc_version_observed": getattr(driver, "cc_version_observed", None),
                         "cc_extra_envs_effective": os.environ.get("SLIME_AGENT_CC_EXTRA_ENVS"),
                         "cc_training_guard_envs": getattr(driver, "cc_training_guard_envs", None)})
        traj = self.out / "harness" / "trajectory.jsonl"
        text = traj.read_text(encoding="utf-8", errors="replace") if traj.exists() else ""
        self.rec["trajectory_bytes"] = len(text.encode("utf-8"))
        self.rec["trajectory_summary"] = summarize_stream(text)
        err = self.out / "harness" / "stderr.log"
        self.rec["stderr_tail"] = err.read_text(encoding="utf-8", errors="replace")[-3000:] if err.exists() else ""
        self.save()
        return exit_code

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
    ap.add_argument("--scenario", choices=("probe", "memwrite", "bigread", "bigread_limit", "ramp", "reactive", "emptylen", "emptylen_repeat"), required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--attempt-id", required=True, help="dp8 开头；也是 relay 会话 token 形状：[A-Za-z0-9_.-]{6,96}")
    ap.add_argument("--label", default="", help="条件的人读名字，记进 attempt.json")
    ap.add_argument("--stub-host", default="172.17.0.1")
    ap.add_argument("--stub-port", type=int, default=18100)
    ap.add_argument("--wall-seconds", type=int, default=600)
    ap.add_argument("--cc-extra-args", default="--disallowedTools Task WebFetch WebSearch --max-turns 8")
    ap.add_argument("--cc-extra-envs", default="", help="JSON object，经 SLIME_AGENT_CC_EXTRA_ENVS 并入 CC 进程环境")
    ap.add_argument("--settings-extra", default="", help="JSON object，追加进 write_config 写的 settings（仅本进程内包装）")
    ap.add_argument("--stub-extra-args", default="")
    ap.add_argument("--ramp-steps", type=int, default=10)
    ap.add_argument("--prompt", default="Acceptance run: execute exactly the tool calls you are given, then stop.")
    ns = ap.parse_args(argv)
    if not re.match(r"^dp8[A-Za-z0-9_.-]{3,93}$", ns.attempt_id):
        ap.error("--attempt-id 须以 dp8 开头且形态合法")
    if not (18100 <= ns.stub_port <= 18199):
        ap.error("--stub-port 须在 18100–18199")
    if not ns.out_dir.startswith("/work/probe/runs/dp_"):
        ap.error("--out-dir 须在 /work/probe/runs/dp_* 下")
    if not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL")
    runner = Runner(ns)

    async def go() -> int:
        try:
            return await runner.run()
        finally:
            await runner.cleanup()

    rc = asyncio.run(go())
    ts = runner.rec.get("trajectory_summary") or {}
    print(json.dumps({"label": ns.label, "result": runner.rec.get("result"), "harness_exit_code": runner.rec.get("harness_exit_code"),
                      "termination": runner.rec.get("termination"), "checks": runner.rec.get("checks"),
                      "stub_counts": runner.rec.get("stub_counts_final"), "system_subtypes": ts.get("system_subtypes"),
                      "cc_result_subtype": (ts.get("cc_result") or {}).get("subtype"),
                      "failure_detail": runner.rec.get("failure_detail"), "cleanup": runner.rec.get("cleanup")}, ensure_ascii=False, indent=1))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
