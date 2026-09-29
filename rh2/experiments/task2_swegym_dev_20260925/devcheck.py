"""任务二：逐题开发命令在真实 actor 条件下执行（真实 CC 2.1.205 + 桩端点 + 正式启动路径）。

复用 A 线 `acceptance_startup_2.Runner` 的正式装配（容器 / relay / 内网 / sanitize / 可信初始化 / 激活文件 /
启动前与激活核查 / `ClaudeCodeDriver.run`），只换三件事：
  1. 剧本 = 每题命令清单：桩依次发出 Bash tool_use，最后 end_turn；
  2. 判据 = 逐命令结果（Codex R2）：每条命令被包成"写 rc 文件 + 截尾输出文件"，运行后由 root 从容器取回，
     按命令 ID 关联；rc 文件缺失 = 未运行，rc=124 = 命令超时；不以 driver 返回值或脚本总退出码判题；
  3. 允许 `--image` 覆盖 actor 镜像（派生），并记录实际镜像 ID、镜像初态 `git status --porcelain`、
     生效的 sandbox profile（Codex R1 / R3）。
收口（Codex R6）：容器名在 docker run 前就登记；SIGTERM / SIGINT 取消主任务后仍走清理，并按本 attempt 的
`rh2.run_id` 标签有界移除残留容器与网络；清理失败以非零退出，调用方不应继续派发。

命令清单 JSON：[{"id": "py", "cmd": "python -c ...", "timeout_s": 120, "expect": "zero|nonzero|any", "purpose": "..."}]

    SLIME_AGENT_CC_PLATFORM_TARBALL=/work/task2/cc/claude-code-linux-x64-2.1.205.tgz \\
    .venv/bin/python experiments/task2_swegym_dev_20260925/devcheck.py --prepared-summary ... --task dask__dask-8597 \\
        --commands commands/dask__dask-8597.json --out-dir /work/task2/runs/dask8597/orig --attempt-id t2dask8597orig01
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import re
import shlex
import signal
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "base_probe_fixes_20260923"))
import acceptance_startup_2 as acc  # noqa: E402

CAP_DIR = "/tmp/rh2dc"
OUT_TAIL_BYTES = 200_000


def wrap(c: dict) -> str:
    """一条开发命令 → 在 agent shell 里执行并落 rc / 截尾输出；stdout 只回显摘要，完整输出由 root 取回。"""
    cid, t = c["id"], int(c.get("timeout_s", 300))
    body = shlex.quote(c["cmd"])
    return (
        f"mkdir -p {CAP_DIR}; cd /testbed; echo RH2DC_BEGIN id={cid}; "
        f"timeout -k 10 {t} bash -c {body} > {CAP_DIR}/{cid}.full 2>&1; rc=$?; "
        f"tail -c {OUT_TAIL_BYTES} {CAP_DIR}/{cid}.full > {CAP_DIR}/{cid}.out; "
        f"echo $(wc -c < {CAP_DIR}/{cid}.full) > {CAP_DIR}/{cid}.bytes; rm -f {CAP_DIR}/{cid}.full; "
        f"echo $rc > {CAP_DIR}/{cid}.rc; echo RH2DC_END id={cid} rc=$rc; tail -c 1500 {CAP_DIR}/{cid}.out"
    )


def build_script(cmds: list[dict]) -> list[dict]:
    steps: list[dict] = []
    for c in cmds:
        ms = min(600_000, (int(c.get("timeout_s", 300)) + 30) * 1000)  # CC Bash 工具自带上限 10 分钟
        steps.append({"kind": "tool_use", "name": "Bash", "input": {"command": wrap(c), "timeout": ms, "description": f"devcheck {c['id']}"}})
    steps.append({"kind": "text", "text": "Devcheck commands done."})
    return steps


_PYTEST_RE = re.compile(r"=+ (.*?(?:passed|failed|error|errors|skipped|xfailed|xpassed|no tests ran|deselected).*?) in [0-9.]+s", re.I)


def pytest_counts(text: str) -> dict[str, int] | None:
    m = None
    for m in _PYTEST_RE.finditer(text):
        pass
    if not m:
        return None
    out: dict[str, int] = {}
    for n, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed|deselected|warnings?)", m.group(1)):
        out[k.rstrip("s") if k in ("errors", "warnings") else k] = int(n)
    if "no tests ran" in m.group(1):
        out["no_tests_ran"] = 1
    return out


class DevRunner(acc.Runner):
    def __init__(self, ns: argparse.Namespace) -> None:
        super().__init__(ns)
        self.cmds: list[dict] = json.loads(Path(ns.commands).read_text(encoding="utf-8"))
        ids = [c["id"] for c in self.cmds]
        if len(set(ids)) != len(ids) or not all(re.match(r"^[A-Za-z0-9_.-]{1,40}$", i) for i in ids):
            raise SystemExit("命令 id 必须唯一且为 [A-Za-z0-9_.-]{1,40}")
        self.rec.update({"commands_file": ns.commands, "commands": self.cmds, "image_override": ns.image})

    def start_stub(self) -> None:  # 剧本 = 命令清单
        orig = acc.scenario_script
        acc.scenario_script = lambda name: build_script(self.cmds)  # noqa: E731
        try:
            super().start_stub()
        finally:
            acc.scenario_script = orig

    async def run(self) -> int:
        # 镜像覆盖：包一层 rollout_spec_from_view（Runner.run 在函数内 import，改模块属性即可生效）
        import repoharness2.adapters.slime.prepared_task_face as ptf

        orig = ptf.rollout_spec_from_view
        if self.ns.image:
            def patched(view, **kw):
                return dataclasses.replace(orig(view, **kw), image=self.ns.image)

            ptf.rollout_spec_from_view = patched
        try:
            await self.image_facts()
            return await super().run()
        finally:
            ptf.rollout_spec_from_view = orig

    def _profile(self):
        from repoharness2.adapters.slime.sandbox_profile import rollout_profile_from_env

        return rollout_profile_from_env(os.environ, model_proxy_upstream_host=self.ns.stub_host, model_proxy_upstream_port=int(self.ns.stub_port))

    async def image_facts(self) -> None:
        """镜像身份与初态（独立一次性容器，root，不联网）：实际 image ID、HEAD、porcelain（空也记）。"""
        self.docker = acc_docker()
        summary = json.loads(Path(self.ns.prepared_summary).read_text(encoding="utf-8"))
        image = self.ns.image
        if not image:
            from repoharness2.adapters.slime.prepared_task_face import rollout_spec_from_view
            from repoharness2.adapters.slime.replay_grade import load_context
            from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env

            ctx = load_context(prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
                               manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=self._profile(),
                               grader_profile=grader_profile_from_env(os.environ), artifacts_dir=self.out / "unused_artifacts", run_id=self.ns.attempt_id)
            image = rollout_spec_from_view(ctx.rollout_views[ctx.resolve_task_id(self.ns.task)], time_budget_seconds=60).image
        insp = await self.dk("image", "inspect", image, "--format", "{{.Id}} {{json .RepoDigests}}", timeout=120)
        probe = await self.dk("run", "--rm", "--network", "none", "--label", f"rh2.run_id={self.ns.attempt_id}", "--entrypoint", "bash", image, "-c",
                              "cd /testbed && echo HEAD=$(git rev-parse HEAD) && echo PORCELAIN_BEGIN && git status --porcelain; echo PORCELAIN_RC=$?",
                              timeout=300)
        self.rec["image_facts"] = {"image": image, "inspect": insp.stdout.strip(), "inspect_rc": insp.exit_code,
                                   "initial_worktree": probe.stdout[-4000:], "initial_worktree_rc": probe.exit_code}
        self.save()

    async def solve(self, spec, env_inj: dict[str, str]) -> int | None:
        p = self._profile()
        self.rec["effective_profile"] = {k: getattr(p, k) for k in ("cpus", "memory_bytes", "tmp_tmpfs_bytes", "home_tmpfs_bytes",
                                                                     "writable_layer_quota_bytes", "pids_limit")}
        rc = await super().solve(spec, env_inj)
        insp = await self.dk("inspect", self.container, "--format", "{{.Image}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}", timeout=60)
        self.rec["container_inspect"] = insp.stdout.strip()
        await self.collect()
        return rc

    async def collect(self) -> None:
        cap = self.out / "captures"
        cap.mkdir(exist_ok=True)
        rows = []
        for c in self.cmds:
            cid = c["id"]
            r = await self.sh(f"cat {CAP_DIR}/{cid}.rc 2>/dev/null; echo ---; cat {CAP_DIR}/{cid}.bytes 2>/dev/null", timeout=60)
            rc_s, _, by = r.stdout.partition("---")
            out = await self.sh(f"cat {CAP_DIR}/{cid}.out 2>/dev/null", timeout=120)
            (cap / f"{cid}.out").write_text(out.stdout, encoding="utf-8")
            rc = int(rc_s.strip()) if rc_s.strip().lstrip("-").isdigit() else None
            status = "not_run" if rc is None else ("timeout" if rc in (124, 137) else ("rc0" if rc == 0 else "nonzero"))
            exp = c.get("expect", "any")
            rows.append({"id": cid, "rc": rc, "status": status, "expect": exp,
                         "matches_expect": None if rc is None else (exp == "any" or (exp == "zero") == (rc == 0)),
                         "output_bytes": int(by.strip()) if by.strip().isdigit() else None,
                         "output_truncated_to": OUT_TAIL_BYTES, "pytest": pytest_counts(out.stdout), "purpose": c.get("purpose", "")})
        self.rec["commands_result"] = rows
        self.save()

    def evaluate(self) -> None:
        super().evaluate()
        c = self.rec["checks"]
        for k in ("no_files_written_under_testbed", "git_status_clean", "all_expected_ok"):  # 开发命令可以合法写工作区
            c.pop(k, None)
        rows = self.rec.get("commands_result") or []
        c["all_commands_ran"] = bool(rows) and all(r["rc"] is not None for r in rows)
        c["all_match_expect"] = bool(rows) and all(r["matches_expect"] for r in rows)
        c["interpreter_in_tool_result"] = c.get("interpreter_in_tool_result")  # 只有清单含 PY_CHECK 形状时才可能为真

    async def cleanup(self) -> None:
        await super().cleanup()
        c = self.rec.get("cleanup") or {}
        left = c.get("labeled_containers_left") or []
        nets = c.get("labeled_networks_left") or []
        if left:
            c["force_rm_containers"] = (await self.dk("rm", "-f", *left, timeout=180)).exit_code
        for n in nets:
            c.setdefault("force_rm_networks", []).append((await self.dk("network", "rm", n, timeout=60)).exit_code)
        again = await self.dk("ps", "-a", "--filter", f"label=rh2.run_id={self.ns.attempt_id}", "--format", "{{.Names}}", timeout=60)
        again_n = await self.dk("network", "ls", "--filter", f"label=rh2.run_id={self.ns.attempt_id}", "--format", "{{.Name}}", timeout=60)
        # Codex F2：容器与网络都复查；查询自身失败 = 未知（写成 ["<query_failed>"]），不能当零残留
        c["residual_after_force"] = (again.stdout.split() if again.exit_code == 0 else ["<container_query_failed>"]) \
            + (again_n.stdout.split() if again_n.exit_code == 0 else ["<network_query_failed>"])
        self.rec["cleanup"] = c
        self.save()


def acc_docker():
    from repoharness2.adapters.slime.sandbox_profile import default_docker_runner

    return default_docker_runner


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--commands", required=True)
    ap.add_argument("--image", default=None, help="actor 派生镜像（缺省用 prepared view 的公开镜像）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--attempt-id", required=True)
    ap.add_argument("--stub-host", default="172.17.0.1")
    ap.add_argument("--stub-port", type=int, default=18090)
    ap.add_argument("--wall-seconds", type=int, default=1800)
    ap.add_argument("--prompt", default="Devcheck run: execute exactly the tool calls you are given, then stop.")
    ns = ap.parse_args(argv)
    ns.scenario = "normal"
    n = len(json.loads(Path(ns.commands).read_text(encoding="utf-8")))
    ns.cc_extra_args = f"--max-turns {n + 3}"
    if not re.match(r"^[A-Za-z0-9_.-]{6,96}$", ns.attempt_id):
        ap.error("--attempt-id 形态不合法")
    if not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL")
    runner = DevRunner(ns)

    async def go() -> int:
        loop = asyncio.get_running_loop()
        main_task = asyncio.current_task()
        inner = asyncio.ensure_future(runner.run())
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, inner.cancel)
        try:
            return await inner
        except asyncio.CancelledError:
            runner.rec["result"] = "cancelled"
            return 130
        finally:
            await runner.cleanup()
            del main_task

    rc = asyncio.run(go())
    residual = (runner.rec.get("cleanup") or {}).get("residual_after_force")
    print(json.dumps({"result": runner.rec.get("result"), "harness_exit_code": runner.rec.get("harness_exit_code"),
                      "checks": runner.rec.get("checks"), "commands": [(r["id"], r["status"], r["rc"], r["pytest"]) for r in runner.rec.get("commands_result") or []],
                      "residual": residual, "failure_detail": runner.rec.get("failure_detail")}, ensure_ascii=False, indent=1))
    return 4 if residual else rc


if __name__ == "__main__":
    raise SystemExit(main())
