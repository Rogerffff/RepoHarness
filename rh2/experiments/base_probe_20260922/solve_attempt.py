#!/usr/bin/env python3
"""基座探针（2026-09-22，B 线）：一次"真实解题身份"的尝试——薄诊断入口。

**不是正式 actor 全链**（没有 miles / 训练捕获 / receipt / 组装配）。按 `generate.py:_materialize_rollout_sandbox`
的顺序复用真实 helper，差异都写进 attempt.json 的 `deviations`：

  relay（本 attempt 一份）→ attempt 私有 isolated internal 网络 → 正式 rollout profile 的 docker run 参数 →
  镜像身份核对 → /testbed 血缘探针 → git sanitize → root 可信初始化 →（可选）环境配方准备 → 基线未跟踪清单 →
  public bundle / BASH_ENV 写入 → 启动前核对（inspect + agent 身份探针）→
    dev-check：以 agent 身份、经 slime `exec_and_wait`（与 CC 同一 launcher 形状与环境变量）跑确定性开发命令；
    solve   ：`bringup.ClaudeCodeDriver` 离线装 CC 并经 slime `ClaudeCodeHarness` 启动，模型端点 = relay →宿主网关
  → 收集轨迹 / CC 会话目录 / 环境事实 → 以 root 按正式导出口径生成 `<instance_id>.diff`（相对物化时的 HEAD，
  排除基线未跟踪清单）→ 精确清理（容器 → attempt 网络 → relay）。

候选补丁随后交 `scripts/replay_grade.py run --candidate patch-dir:<本次 candidate 目录>`（真实冻结、投影与
SWEGradingManager）。本脚本不接触 private 目录的内容：只读 prepared 公共面。
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RH2_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RH2_ROOT / "src"))

AGENT_ENV_FACTS_SCRIPT = r'''
echo "RH2F_ID=$(id)"; echo "RH2F_PWD=$(pwd)"; echo "RH2F_SHELL_EXE=$(readlink /proc/$$/exe)"
echo "RH2F_BASH_VERSION=${BASH_VERSION-}"
printf 'RH2F_HOME=%s\nRH2F_PATH=%s\nRH2F_BASH_ENV=%s\n' "$HOME" "$PATH" "${BASH_ENV-}"
if [ -n "${BASH_ENV-}" ]; then [ -r "$BASH_ENV" ] && echo "RH2F_BASH_ENV_READABLE=1" || echo "RH2F_BASH_ENV_READABLE=0"; fi
echo "RH2F_CONDA_DEFAULT_ENV=${CONDA_DEFAULT_ENV-}"
for t in python python3 pip pytest git conda; do echo "RH2F_WHICH_$t=$(command -v $t 2>/dev/null)"; done
python -c 'import sys; print("RH2F_PY_EXE="+sys.executable); print("RH2F_PY_VERSION="+sys.version.split()[0]); print("RH2F_PY_PATH="+repr(sys.path))' 2>&1
for d in /testbed "$HOME" /tmp; do f="$d/.rh2_probe_$$"; if ( : > "$f" ) 2>/dev/null && [ -r "$f" ] && rm -f "$f"; then echo "RH2F_WRITABLE_$d=1"; else echo "RH2F_WRITABLE_$d=0"; fi; done
for d in /opt/miniconda3/envs/testbed /opt/miniconda3; do [ -e "$d" ] && { [ -w "$d" ] && echo "RH2F_PREFIX_WRITABLE_$d=1" || echo "RH2F_PREFIX_WRITABLE_$d=0"; }; done
echo "RH2F_DONE=1"
'''


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _slug(text: str, limit: int = 40) -> str:
    return (re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-") or "x")[:limit].lower()


def _docker_bytes(*args: str, timeout: float, input_bytes: bytes | None = None) -> tuple[int, bytes, bytes]:
    """二进制安全的 docker 调用（取轨迹 / tar 用）。"""
    try:
        p = subprocess.run(["docker", *args], input=input_bytes, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, exc.stdout or b"", (exc.stderr or b"") + f"\n[timeout {timeout}s]".encode()


class Attempt:
    def __init__(self, ns: argparse.Namespace) -> None:
        self.ns = ns
        self.out = Path(ns.out_dir).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.rec: dict[str, Any] = {
            "schema": "rh2.base_probe.attempt.v1",
            "entry": "rh2/experiments/base_probe_20260922/solve_attempt.py",
            "entry_sha256": _sha256_file(Path(__file__).resolve()),
            "mode": ns.mode,
            "attempt_id": ns.attempt_id,
            "solver": ns.solver,
            "started_at": _now_iso(),
            "stages": {},
            "timings": {},
            "deviations": [
                "薄诊断入口：没有 miles / 训练捕获 / receipt；模型端点是宿主侧探针网关，不是 slime 训练 adapter（solver 自部署时网关后面才是该 adapter）",
                "每个 attempt 自带一份 egress relay（正式链一 run 一份）",
                "回合上限用 CC 的 --max-turns 与网关的 session 请求上限，不是正式链 adapter 的 turn 预算闸门",
                "候选补丁以 git diff 文本导出后交 replay driver 重放；census 冻结发生在 replay 容器里，不在本求解容器里",
            ],
            "cleanup": {},
            "result": None,
        }
        self.container: str | None = None
        self.network = None
        self.relay = None
        self.pool = None
        self.profile = None
        self.docker = None

    # ------------------------------------------------------------------ 小工具
    def save(self) -> None:
        tmp = self.out / ".attempt.json.tmp"
        tmp.write_text(json.dumps(self.rec, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        os.replace(tmp, self.out / "attempt.json")

    async def dk(self, *args: str, timeout: float = 120.0, input_bytes: bytes | None = None):
        from repoharness2.adapters.slime.sandbox_profile import _call  # 同一有界调用口

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

    def stage(self, name: str, **facts: Any) -> None:
        self.rec["stages"][name] = {"at": _now_iso(), **facts}
        self.save()

    def write_text(self, rel: str, text: str) -> str:
        p = self.out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return rel

    # ------------------------------------------------------------------ 主流程
    async def run(self) -> int:
        ns = self.ns
        os.environ.setdefault("RH2_BRINGUP_ARTIFACT_DIR", str(self.out / "bringup_artifacts"))
        Path(os.environ["RH2_BRINGUP_ARTIFACT_DIR"]).mkdir(parents=True, exist_ok=True)

        from repoharness2.adapters.slime.prepared_task_face import rollout_spec_from_view
        from repoharness2.adapters.slime.replay_grade import load_context
        from repoharness2.adapters.slime.sandbox_profile import (
            EgressSubnetPool, connect_relay_to_network, create_attempt_network, default_docker_runner,
            grader_profile_from_env, rollout_profile_from_env, rollout_trusted_init_script, run_git_sanitize,
            run_rollout_prelaunch_check, run_trusted_init, start_egress_relay,
        )
        from repoharness2.envpack import materialize
        from repoharness2.adapters.slime.generate import PUBLIC_BUNDLE_CONTAINER_PATH
        from repoharness2.grading.manager import BASE_UNTRACKED_MANIFEST, BASE_UNTRACKED_SNAPSHOT_SCRIPT

        self.docker = default_docker_runner
        summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
        profile = rollout_profile_from_env(
            os.environ, model_proxy_upstream_host=ns.gateway_host, model_proxy_upstream_port=int(ns.gateway_port),
        )
        self.profile = profile
        ctx = load_context(
            prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
            manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=profile,
            grader_profile=grader_profile_from_env(os.environ), artifacts_dir=self.out / "unused_artifacts",
            run_id=ns.attempt_id,
        )
        task_id = ctx.resolve_task_id(ns.task)
        view = ctx.rollout_views[task_id]
        spec = rollout_spec_from_view(view, time_budget_seconds=int(ns.wall_seconds))
        public = view.public
        image = ns.image_override or spec.image
        self.rec.update({
            "task_id": task_id, "instance_id": public.instance_id, "repo": public.repo,
            "base_commit": spec.base_commit, "workdir": spec.workdir,
            "image_public": spec.image, "image_used": image, "image_override": bool(ns.image_override),
            "image_recipe_note": ns.image_recipe_note, "image_manifest_digest": spec.image_manifest_digest,
            "public_bundle_digest": view.public_bundle_digest,
            "prompt_sha256": "sha256:" + hashlib.sha256(spec.prompt.encode("utf-8")).hexdigest(),
            "profile_parameters": profile.to_parameters(), "profile_digest": profile.digest(),
            "actor_env": ns.actor_env, "wall_seconds": ns.wall_seconds, "max_turns": ns.max_turns,
            "cc_extra_args": None, "gateway": f"{ns.gateway_host}:{ns.gateway_port}",
            "solver_note": ns.solver_note,
        })
        self.write_text("prompt.txt", spec.prompt)
        self.save()

        labels = ("--label", f"rh2.run_id={ns.attempt_id}", "--label", "rh2.base_probe=1")
        name = f"rh2bp-{_slug(public.instance_id, 28)}-{uuid.uuid4().hex[:8]}"

        # 0. 镜像在场（不在则拉；拉取有独立预算）
        t = time.monotonic()
        insp = await self.dk("image", "inspect", "-f", "{{.Id}}", image, timeout=60)
        if insp.exit_code != 0:
            pull = await self.dk("pull", image, timeout=float(ns.image_pull_seconds))
            if pull.exit_code != 0:
                return self.fail("image_pull_failed", (pull.stderr or pull.stdout)[-400:])
            insp = await self.dk("image", "inspect", "-f", "{{.Id}}", image, timeout=60)
        self.rec["image_id"] = insp.stdout.strip()
        self.rec["timings"]["image_ready"] = round(time.monotonic() - t, 3)

        # 1. relay + attempt 网络 + 容器（参数只由正式 profile 组装）
        t = time.monotonic()
        self.relay = await start_egress_relay(self.docker, profile, run_id=ns.attempt_id, labels=labels)
        self.pool = EgressSubnetPool(profile.egress_subnet_pool, profile.egress_subnet_prefix)
        for _ in range(int(ns.subnet_skip)):  # 并发进程各自错开起点，减少 "Pool overlaps" 重试
            self.pool.mark_foreign(self.pool.allocate())
        self.network = await create_attempt_network(
            self.docker, profile=profile, pool=self.pool, name=f"{name}-net", labels=labels, max_slots=512,
        )
        await connect_relay_to_network(self.docker, relay=self.relay, network=self.network)
        run = await self.dk(*profile.docker_run_args(name=name, network=self.network.name, image=image, labels=labels),
                            timeout=300)
        if run.exit_code != 0:
            return self.fail("container_start_failed", (run.stderr or run.stdout)[-400:])
        self.container = name
        self.rec["container"] = name
        self.rec["timings"]["network_and_container"] = round(time.monotonic() - t, 3)
        self.stage("container_started", network=self.network.name, subnet=self.network.subnet,
                   relay=self.relay.container_name, relay_image_id=self.relay.image_id)

        # 2. 镜像身份：原镜像核 RepoDigests 命中冻结 digest；覆盖镜像记录实际 ID（本地构建豁免，如实标注）
        ref = await self.dk("inspect", "-f", "{{.Image}}", name, timeout=60)
        actual_image_id = ref.stdout.strip()
        digests = await self.dk("image", "inspect", "-f", materialize.IMAGE_REPO_DIGESTS_FORMAT, actual_image_id, timeout=60)
        self.rec["container_image_id"] = actual_image_id
        self.rec["container_image_repo_digests"] = digests.stdout.strip()
        if ns.image_override:
            self.stage("image_identity", mode="override_local_build_exempt", image_id=actual_image_id)
        else:
            chk = materialize.evaluate_image_digest(spec.image_manifest_digest, digests.exit_code, digests.stdout, digests.stderr)
            self.stage("image_identity", mode="repo_digest", ok=chk.ok, detail=None if chk.ok else chk.failure_message()[:400])
            if not chk.ok:
                return self.fail("image_digest_mismatch", chk.failure_message()[:400])

        # 3. /testbed 血缘探针
        probe = await self.sh(materialize.build_probe_script(spec.base_commit), timeout=300)
        check = materialize.evaluate_probe(spec.base_commit, probe.exit_code, probe.stdout, probe.stderr)
        self.write_text("facts/materialize_probe.txt", probe.stdout + "\n--- stderr ---\n" + probe.stderr)
        if probe.exit_code != 0 or not check.ok:
            return self.fail("testbed_lineage_failed", check.failure_message()[:400])
        head = check.head
        self.rec["materialized_head"] = head
        self.stage("materialize_probe", head=head, head_equals_base=(head == spec.base_commit))

        # 4. git sanitize → root 可信初始化（顺序与正式链一致：repack 后再 chown）
        t = time.monotonic()
        try:
            san = await run_git_sanitize(self.docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
        except RuntimeError as exc:
            return self.fail("git_sanitize_failed", str(exc)[:400])
        self.rec["timings"]["git_sanitize"] = round(time.monotonic() - t, 3)
        t = time.monotonic()
        try:
            init = await run_trusted_init(self.docker, name=name, script=rollout_trusted_init_script(profile),
                                          timeout=profile.init_timeout_seconds)
        except RuntimeError as exc:
            return self.fail("trusted_init_failed", str(exc)[:400])
        self.rec["timings"]["trusted_init"] = round(time.monotonic() - t, 3)
        self.stage("sanitize_and_init", git_sanitize=san, trusted_init=init)

        # 5.（可选）环境配方准备：显式分阶段，先于基线清单；输出全文留存
        if ns.prep_script:
            t = time.monotonic()
            prep_text = Path(ns.prep_script).read_text(encoding="utf-8")
            prep = await self.sh(prep_text, user=ns.prep_user, timeout=float(ns.prep_seconds))
            self.write_text("facts/prep_output.txt", prep.stdout + "\n--- stderr ---\n" + prep.stderr)
            self.rec["timings"]["prep"] = round(time.monotonic() - t, 3)
            after = await self.sh(f"cd {shlex.quote(spec.workdir)} && git status --porcelain | head -100", timeout=120)
            self.stage("prep", script=str(ns.prep_script), script_sha256=_sha256_file(Path(ns.prep_script)),
                       user=ns.prep_user, exit_code=prep.exit_code, git_status_after=after.stdout.splitlines()[:100])
            if prep.exit_code != 0 and not ns.prep_allow_failure:
                return self.fail("prep_failed", (prep.stderr or prep.stdout)[-400:])
            if ns.prep_user == "root":  # root 准备可能留下 root 属主的文件：再交回 agent
                await self.sh(f"chown -R {profile.agent_uid}:{profile.agent_uid} {shlex.quote(spec.workdir)}",
                              timeout=profile.init_timeout_seconds)

        # 6. 基线未跟踪清单 + public bundle + BASH_ENV（正式路径原样写；诊断变体另写一份 agent 可读副本）
        snap = await self.sh(f"cd {shlex.quote(spec.workdir)} && "
                             + BASE_UNTRACKED_SNAPSHOT_SCRIPT.format(manifest=BASE_UNTRACKED_MANIFEST), timeout=300)
        if snap.exit_code != 0:
            return self.fail("base_untracked_snapshot_failed", snap.stderr[-300:])
        tracked_dirty = await self.sh(f"cd {shlex.quote(spec.workdir)} && git status --porcelain --untracked-files=no | head -50", timeout=120)
        self.rec["baseline_tracked_dirty"] = tracked_dirty.stdout.splitlines()
        # 镜像自带的"已跟踪但被改过"的文件（如 mypy 镜像里的 test-requirements.txt）不是候选：记下基线内容哈希，
        # 导出时把 agent 没再动过的这类文件排除（正式链的 census 导出天然相对基线，这里是 git diff 口径的补丁）。
        await self.sh(
            f"cd {shlex.quote(spec.workdir)} && git status --porcelain --untracked-files=no | sed -E 's/^.. //' | "
            "while IFS= read -r p; do [ -f \"$p\" ] && printf '%s  %s\\n' \"$(sha256sum < \"$p\" | cut -d' ' -f1)\" \"$p\"; done "
            "> /rh2/base_tracked_dirty.sha256", timeout=300)
        writes = [(PUBLIC_BUNDLE_CONTAINER_PATH, spec.public_bundle_payload),
                  (materialize.BASH_ENV_PATH, materialize.BASH_ENV_CONTENT.encode())]
        if ns.actor_env == "bash_env_v1":
            writes.append((ns.diag_bash_env_path, materialize.BASH_ENV_CONTENT.encode()))
        for path, payload in writes:
            w = await self.sh(f"mkdir -p $(dirname {shlex.quote(path)}) && cat > {shlex.quote(path)} && chmod 0644 {shlex.quote(path)}",
                              input_bytes=payload, timeout=120)
            if w.exit_code != 0:
                return self.fail("workspace_write_failed", f"{path}: {w.stderr[-300:]}")
        self.stage("baseline_and_bundle", base_untracked_manifest=BASE_UNTRACKED_MANIFEST)

        # 7. 启动前核对（一次 inspect + agent 身份探针）：不通过就不启动
        pre = await run_rollout_prelaunch_check(self.docker, name=name, profile=profile, network=self.network.name,
                                                expected_head=head)
        self.write_text("facts/prelaunch.json", json.dumps(pre.to_dict(), ensure_ascii=False, indent=1, default=str))
        self.stage("prelaunch_check", ok=pre.ok, violations=list(pre.violations), seconds=round(pre.seconds, 3))
        if not pre.ok:
            return self.fail("prelaunch_check_failed", "; ".join(pre.violations)[:600])

        # 8. CC 子进程环境（与 slime ClaudeCodeHarness.launch_and_wait 同形；诊断变体只多一个 BASH_ENV）
        extra_envs: dict[str, str] = {}
        if ns.actor_env == "bash_env_v1":
            extra_envs["BASH_ENV"] = ns.diag_bash_env_path
        agent_env = {
            "ANTHROPIC_BASE_URL": profile.harness_adapter_url(),
            "ANTHROPIC_AUTH_TOKEN": ns.attempt_id,
            "ANTHROPIC_MODEL": "slime-actor",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
            "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
            **extra_envs,
        }

        # 9. agent 身份的环境事实（dev-check 与 solve 都采；走 slime exec_and_wait 的 launcher 形状）
        from repoharness2.adapters.slime.docker_sandbox import DockerSandbox
        from slime.agent.sandbox import exec_and_wait

        sb = DockerSandbox(name)
        rc, out = await exec_and_wait(sb, cmd=AGENT_ENV_FACTS_SCRIPT, user="agent", env=agent_env, workdir=spec.workdir,
                                      time_budget_sec=120, tag="rh2facts", want_output=True)
        self.write_text("facts/agent_env_facts.txt", out)
        facts = {ln.split("=", 1)[0]: ln.split("=", 1)[1] for ln in out.splitlines() if ln.startswith("RH2F_") and "=" in ln}
        self.stage("agent_env_facts", exit_code=rc, facts=facts)

        exit_code = 0
        if ns.mode == "dev-check":
            script = Path(ns.dev_script).read_text(encoding="utf-8")
            t = time.monotonic()
            rc, out = await exec_and_wait(sb, cmd=script, user="agent", env=agent_env, workdir=spec.workdir,
                                          time_budget_sec=int(ns.wall_seconds), tag="rh2dev", want_output=True)
            self.write_text("dev_check_output.txt", out)
            self.rec["timings"]["dev_check"] = round(time.monotonic() - t, 3)
            self.stage("dev_check", script=str(ns.dev_script), script_sha256=_sha256_file(Path(ns.dev_script)), exit_code=rc)
            self.rec["result"] = "dev_check_done"
            self.rec["dev_check_exit_code"] = rc
        else:
            exit_code = await self.solve(sb, spec, agent_env, extra_envs)

        # 10. 候选导出（两种模式都做：dev-check 下应为空补丁，可当"入口不污染工作区"的对照）
        await self.export_candidate(spec, head, public.instance_id)
        return exit_code

    async def solve(self, sb, spec, agent_env: dict[str, str], extra_envs: dict[str, str]) -> int:
        ns = self.ns
        from repoharness2.adapters.slime.bringup import ClaudeCodeDriver
        from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS
        from slime.agent.sandbox import EXIT_TIME_BUDGET_EXCEEDED

        extra_args = f"--disallowedTools {ns.disallowed_tools} --max-turns {int(ns.max_turns)}"
        if ns.cc_extra_args:
            extra_args += " " + ns.cc_extra_args
        os.environ["SLIME_AGENT_CC_EXTRA_ARGS"] = extra_args
        if extra_envs:
            os.environ["SLIME_AGENT_CC_EXTRA_ENVS"] = json.dumps(extra_envs, sort_keys=True)
        self.rec["cc_extra_args"] = extra_args
        self.rec["cc_platform_tarball_sha256"] = _sha256_file(Path(os.environ["SLIME_AGENT_CC_PLATFORM_TARBALL"]))

        pre_freeze = await exec_freeze(sb, agent_env, spec.workdir, "rh2frz0")
        self.write_text("facts/pip_freeze_before.txt", pre_freeze)

        self.harness_dir = f"{spec.workdir}/.harness"
        if ns.harness_out == "out_of_tree":
            import slime.agent.harness.claude_code as _cc_mod
            from slime.agent.sandbox import exec_and_wait as _exec_and_wait

            meta_dir = "/tmp/.rh2_harness"
            self.harness_dir = meta_dir

            async def _run_agent_out_of_tree(sb_, *, workdir, start_cmd, env, time_budget_sec):
                await sb_.exec(f"mkdir -p {meta_dir} && chown agent:agent {meta_dir} && chmod 0700 {meta_dir}",
                               user="root", check=True, timeout=30)
                code, _ = await _exec_and_wait(sb_, cmd=start_cmd, user="agent", env=env, workdir=workdir,
                                               out_file=f"{meta_dir}/trajectory.jsonl", time_budget_sec=time_budget_sec,
                                               tag="run", want_output=False)
                return code

            _cc_mod.run_agent = _run_agent_out_of_tree
            self.rec["deviations"].append("harness_out=out_of_tree：CC 的 stream-json 输出改写到 /tmp/.rh2_harness/（不在仓库树内），其余启动形状不变")
        self.rec["harness_out"] = ns.harness_out
        driver = ClaudeCodeDriver()
        launch_facts: dict[str, Any] = {}
        token = HARNESS_LAUNCH_FACTS.set(launch_facts)
        t = time.monotonic()
        termination = "completed"
        try:
            class _Box:  # ClaudeCodeDriver.run 只读 .container_name
                container_name = self.container

            exit_code = await asyncio.wait_for(
                driver.run(_Box(), workdir=spec.workdir, session_id=ns.attempt_id,
                           adapter_url=self.profile.harness_adapter_url(), time_budget_sec=int(ns.wall_seconds),
                           prompt=spec.prompt),
                timeout=float(ns.wall_seconds) + 600.0,
            )
        except asyncio.TimeoutError:
            exit_code = EXIT_TIME_BUDGET_EXCEEDED
            termination = "outer_guard_timeout"
        except Exception as exc:  # noqa: BLE001 - 引导失败等：如实记录，仍走收集与清理
            exit_code = -2
            termination = f"driver_exception:{type(exc).__name__}"
            self.rec["driver_exception"] = f"{type(exc).__name__}: {exc}"[:600]
        finally:
            HARNESS_LAUNCH_FACTS.reset(token)
        seconds = round(time.monotonic() - t, 3)
        if exit_code == EXIT_TIME_BUDGET_EXCEEDED and termination == "completed":
            termination = "wall_clock_exceeded"
        if exit_code == EXIT_TIME_BUDGET_EXCEEDED:
            kill = await self.sh("pkill -KILL -u agent; sleep 2; ps -u agent -o pid= | wc -l", timeout=60)
            self.rec["kill_after_budget"] = {"exit_code": kill.exit_code, "agent_procs_left": kill.stdout.strip()}
        self.rec.update({
            "harness_exit_code": exit_code, "termination": termination, "solve_seconds": seconds,
            "launch_facts": launch_facts, "cc_version_observed": getattr(driver, "cc_version_observed", None),
            "cc_training_guard_envs": getattr(driver, "cc_training_guard_envs", None),
        })
        self.save()

        # 轨迹与 CC 会话目录（二进制安全取回）
        rc, data, err = _docker_bytes("exec", self.container, "cat", f"{self.harness_dir}/trajectory.jsonl", timeout=300)
        (self.out / "trajectory.jsonl").write_bytes(data if rc == 0 else b"")
        self.rec["trajectory_bytes"] = len(data) if rc == 0 else 0
        rc2, tarb, _ = _docker_bytes("exec", self.container, "bash", "-c",
                                     "cd /home/agent && tar -czf - .claude .claude.json 2>/dev/null", timeout=300)
        if tarb:
            (self.out / "cc_home.tgz").write_bytes(tarb)
        self.rec["trajectory_summary"] = summarize_stream((self.out / "trajectory.jsonl").read_text(encoding="utf-8", errors="replace"))

        post_freeze = await exec_freeze(sb, agent_env, spec.workdir, "rh2frz1")
        self.write_text("facts/pip_freeze_after.txt", post_freeze)
        self.rec["pip_freeze_changed"] = (pre_freeze.strip() != post_freeze.strip())
        self.rec["result"] = "ran"
        self.save()
        return 0

    async def export_candidate(self, spec, head: str, instance_id: str) -> None:
        from repoharness2.grading.manager import BASE_UNTRACKED_MANIFEST

        wd = shlex.quote(spec.workdir)
        # 导出前让工作区静止：agent 身份的残留进程（后台服务、未退出的 CC 子进程）一律结束并留数
        quiet = await self.sh("n=$(ps -u agent -o pid= 2>/dev/null | wc -l); pkill -KILL -u agent 2>/dev/null; sleep 1; "
                              "echo BEFORE=$n AFTER=$(ps -u agent -o pid= 2>/dev/null | wc -l)", timeout=60)
        self.rec["agent_procs_at_export"] = quiet.stdout.strip()
        state = await self.sh(
            f"cd {wd} && echo HEAD_AFTER=$(git rev-parse HEAD) && echo COMMITS_AHEAD=$(git rev-list --count {head}..HEAD 2>/dev/null) "
            f"&& git status --porcelain | head -200", timeout=300)
        self.write_text("facts/git_state_after.txt", state.stdout + "\n--- stderr ---\n" + state.stderr)
        # 正式导出口径（grading.manager.build_export_patch_script）的变体：基准取物化时记录的 HEAD sha，
        # agent 自行 commit 时补丁不丢；.harness 是 slime launcher 的输出目录，不属于候选。
        export = (
            f"cd {wd} && rm -rf .harness && git add -N . 1>&2 && excl=() && "
            f"if [ -f {BASE_UNTRACKED_MANIFEST} ]; then while IFS= read -r p; do "
            '[ -n "$p" ] && excl+=(":(exclude,literal)$p"); '
            f"done < {BASE_UNTRACKED_MANIFEST}; fi && "
            + 'if [ -f /rh2/base_tracked_dirty.sha256 ]; then while IFS= read -r line; do h="${line%%  *}"; p="${line#*  }"; '
              'if [ -f "$p" ] && [ "$(sha256sum < "$p" | cut -d" " -f1)" = "$h" ]; then excl+=(":(exclude,literal)$p"); fi; '
              'done < /rh2/base_tracked_dirty.sha256; fi && '
            + f'git -c core.fileMode=false diff --binary {head} -- . "${{excl[@]}}"'
        )
        rc, data, err = _docker_bytes("exec", "-u", "root", self.container, "bash", "-c", export, timeout=600)
        cand = self.out / "candidate"
        cand.mkdir(exist_ok=True)
        if rc == 0:
            (cand / f"{instance_id}.diff").write_bytes(data)
        files = sorted({ln.split(" b/", 1)[1] for ln in data.decode("utf-8", "replace").splitlines()
                        if ln.startswith("diff --git ") and " b/" in ln}) if rc == 0 else []
        self.rec["candidate"] = {
            "export_exit_code": rc, "stderr_tail": err.decode("utf-8", "replace")[-300:], "bytes": len(data) if rc == 0 else 0,
            "sha256": ("sha256:" + hashlib.sha256(data).hexdigest()) if rc == 0 else None, "files": files,
            "touches_tests": [p for p in files if re.search(r"(^|/)tests?(/|_)|(^|/)test_[^/]*\.py$|_test\.py$", p)],
            "empty": rc == 0 and not data.strip(),
        }
        self.save()

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
            chk = await self.dk("ps", "-a", "--filter", f"name=^{self.container}$", "--format", "{{.Names}}", timeout=60)
            c["container_left"] = chk.stdout.strip()
        if self.network is not None:
            c["network_failures"] = await teardown_attempt_network(
                self.docker, network_name=self.network.name, relay=self.relay, pool=self.pool, subnet=self.network.subnet)
        if self.relay is not None:
            c["relay_failures"] = await stop_egress_relay(self.docker, self.relay)
        left = await self.dk("ps", "-a", "--filter", f"label=rh2.run_id={self.ns.attempt_id}", "--format", "{{.Names}}", timeout=60)
        nets = await self.dk("network", "ls", "--filter", f"label=rh2.run_id={self.ns.attempt_id}", "--format", "{{.Name}}", timeout=60)
        c["labeled_containers_left"] = left.stdout.split()
        c["labeled_networks_left"] = nets.stdout.split()
        self.rec["cleanup"] = c
        self.rec["finished_at"] = _now_iso()
        self.save()


async def exec_freeze(sb, agent_env: dict[str, str], workdir: str, tag: str) -> str:
    from slime.agent.sandbox import exec_and_wait

    _rc, out = await exec_and_wait(sb, cmd="python -m pip freeze 2>&1 | sort", user="agent", env=agent_env, workdir=workdir,
                                   time_budget_sec=180, tag=tag, want_output=True)
    return out


def summarize_stream(text: str) -> dict[str, Any]:
    from collections import Counter

    tools: Counter[str] = Counter()
    assistant = 0
    result: dict[str, Any] = {}
    init: dict[str, Any] = {}
    errors = 0
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            ev = json.loads(ln)
        except Exception:  # noqa: BLE001
            continue
        kind = ev.get("type")
        if kind == "system" and ev.get("subtype") == "init":
            init = {k: ev.get(k) for k in ("model", "permissionMode", "claude_code_version", "tools", "mcp_servers", "cwd") if k in ev}
        elif kind == "assistant":
            assistant += 1
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    tools[blk.get("name", "?")] += 1
        elif kind == "user":
            for blk in (ev.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_result" and blk.get("is_error"):
                    errors += 1
        elif kind == "result":
            result = {k: ev.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms",
                                             "total_cost_usd", "stop_reason", "usage", "modelUsage") if k in ev}
    return {"assistant_events": assistant, "tool_calls": dict(tools), "tool_calls_total": sum(tools.values()),
            "tool_result_errors": errors, "cc_result": result, "init": init}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="基座探针：一次真实解题身份的尝试（dev-check | solve）")
    ap.add_argument("--mode", choices=("dev-check", "solve"), required=True)
    ap.add_argument("--prepared-summary", required=True, help="scripts/replay_grade.py prepare 写出的 replay_summary.json")
    ap.add_argument("--task", required=True, help="task_id 或裸 instance_id")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--attempt-id", required=True, help="也是网关的 session token：[A-Za-z0-9_.-]{6,96}")
    ap.add_argument("--solver", default="none", help="solver 配置名（只进记录）")
    ap.add_argument("--solver-note", default=None)
    ap.add_argument("--gateway-host", default="172.17.0.1", help="relay 的上游 = 宿主侧网关地址")
    ap.add_argument("--gateway-port", type=int, default=18080)
    ap.add_argument("--wall-seconds", type=int, default=1800)
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--disallowed-tools", default="Task WebFetch WebSearch")
    ap.add_argument("--cc-extra-args", default=None)
    ap.add_argument("--actor-env", choices=("original", "bash_env_v1"), default="original",
                    help="original = 正式链现状（BASH_ENV 只写 /root，不注入）；bash_env_v1 = 诊断变体：可读副本 + 显式注入 BASH_ENV")
    ap.add_argument("--diag-bash-env-path", default="/rh2/bash_env")
    ap.add_argument("--image-override", default=None, help="派生镜像引用 / image ID（本地构建，如实标注）")
    ap.add_argument("--image-recipe-note", default=None)
    ap.add_argument("--image-pull-seconds", type=int, default=1800)
    ap.add_argument("--prep-script", default=None, help="环境配方准备脚本（host 文件；先于基线清单执行）")
    ap.add_argument("--prep-user", default="root")
    ap.add_argument("--prep-seconds", type=int, default=1800)
    ap.add_argument("--prep-allow-failure", action="store_true")
    ap.add_argument("--dev-script", default=None, help="dev-check 模式的确定性命令脚本（host 文件，只含公开内容）")
    ap.add_argument("--subnet-skip", type=int, default=0)
    ap.add_argument("--harness-out", choices=("in_tree", "out_of_tree"), default="in_tree",
                    help="in_tree = slime run_agent 原样（stream-json 写在 <workdir>/.harness/，agent 可读且在仓库树内）；"
                         "out_of_tree = 诊断变体：改写到 /tmp/.rh2_harness/（首轮分析发现模型会 grep 到自己的轨迹并误当参考解）")
    ns = ap.parse_args(argv)
    if not re.match(r"^[A-Za-z0-9_.-]{6,96}$", ns.attempt_id):
        ap.error("--attempt-id 形态不合法")
    if ns.mode == "dev-check" and not ns.dev_script:
        ap.error("dev-check 需要 --dev-script")
    if ns.mode == "solve" and not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("solve 需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL（claude-code-linux-x64 平台包）")
    return ns


async def _amain(ns: argparse.Namespace) -> int:
    attempt = Attempt(ns)
    code = 4
    try:
        code = await attempt.run()
    except BaseException as exc:  # noqa: BLE001 - 记录后原样处理；清理一定执行
        attempt.rec["result"] = attempt.rec.get("result") or f"infra_failed:exception:{type(exc).__name__}"
        attempt.rec["exception"] = f"{type(exc).__name__}: {exc}"[:800]
        attempt.save()
        if isinstance(exc, (KeyboardInterrupt, asyncio.CancelledError)):
            raise
    finally:
        try:
            await attempt.cleanup()
        except Exception as exc:  # noqa: BLE001
            attempt.rec["cleanup_exception"] = f"{type(exc).__name__}: {exc}"[:400]
            attempt.save()
    print(json.dumps({"attempt_id": ns.attempt_id, "result": attempt.rec.get("result"),
                      "termination": attempt.rec.get("termination"), "candidate": attempt.rec.get("candidate"),
                      "cleanup": attempt.rec.get("cleanup")}, ensure_ascii=False, default=str), flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_amain(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
