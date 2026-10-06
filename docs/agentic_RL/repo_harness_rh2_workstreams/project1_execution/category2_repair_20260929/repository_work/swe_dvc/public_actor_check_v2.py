"""DVC 公开 actor 窄核；继承冻结 devcheck，镜像初态探针也使用原受限 profile；4166仅允许逐字匹配旧镜像元数据差异。

输入 JSON 由题主按新冻结交付生成。必须在 cpu_slot 内运行；本入口不解除门控，
不安装活动工作区，不修改评分对象，不执行或挂载私有测试。桩端点仅用于交付核查。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys


def sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--attempt-id", required=True)
    ns = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{6,96}", ns.attempt_id):
        ap.error("attempt_id must be a unique Docker label")
    if ns.out_dir.exists():
        ap.error("output already exists; use a fresh attempt")
    cfg = json.loads(ns.input.read_text())
    repo = Path(cfg["release_repo_root"])
    for entry in cfg["code_files"]:
        if sha(repo / entry["path"]) != entry["sha256"]:
            raise ValueError("frozen actor code SHA mismatch: " + entry["path"])
    prepared_summary = Path(cfg["prepared_summary"])
    if sha(prepared_summary) != cfg["prepared_summary_sha256"]:
        raise ValueError("prepared summary identity differs")
    summary = json.loads(prepared_summary.read_text())
    prepared = Path(summary["prepared_dir"])
    if sha(prepared / "prepared_manifest.json") != "sha256:" + summary["prepared_manifest_sha256"]:
        raise ValueError("prepared manifest differs")
    public_view = next(json.loads(line) for line in (prepared / "rollout_task_views.jsonl").read_text().splitlines()
                       if json.loads(line)["task_id"] == cfg["task_id"])
    public = public_view["public"]
    if public_view["public_bundle_digest"] != cfg["public_bundle_digest"]:
        raise ValueError("public bundle identity differs")
    development = Path(cfg["public_development"])
    if sha(development) != cfg["public_development_sha256"]:
        raise ValueError("public development instructions differ")
    commands = Path(cfg["commands"])
    if sha(commands) != cfg["commands_sha256"]:
        raise ValueError("public command list differs")
    prompt_row = next(json.loads(line) for line in (prepared / "prompts.jsonl").read_text().splitlines()
                      if json.loads(line)["metadata"]["task_id"] == cfg["task_id"])
    statement = public["problem_statement"]
    if "sha256:" + hashlib.sha256(statement.encode()).hexdigest() != public["problem_statement_sha256"]:
        raise ValueError("public statement identity differs")
    development_text = development.read_bytes().decode("utf-8")
    prompt = prompt_row["prompt"] + "\n\n" + development_text
    if statement not in prompt:
        raise ValueError("prepared prompt omitted public task")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["RH2_SANDBOX_RELAY_PORT"] = str(cfg["actor_gateway_port"])
    os.environ["SLIME_AGENT_CC_PLATFORM_TARBALL"] = cfg["cc_platform_tarball"]
    os.environ["MILES_RH2_RUN_ID"] = ns.attempt_id
    sys.path.insert(0, str(repo / "rh2/src"))
    entry = repo / "rh2/experiments/task2_swegym_dev_20260925/devcheck.py"
    loader = importlib.util.spec_from_file_location("dvc_frozen_devcheck", entry)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)

    class BoundedDevRunner(module.DevRunner):
        async def image_facts(self) -> None:
            self.docker = module.acc_docker()
            image = self.ns.image
            profile = self._profile()
            if (profile.cpus, profile.memory_bytes, profile.pids_limit) != (2.0, 4 * 1024**3, 512):
                raise ValueError("ordinary CPU actor profile must remain 2 CPU / 4 GiB / PID512")
            labels = ("--label", "rh2.run_id=" + self.ns.attempt_id)
            name = "rh2-dvc-image-" + hashlib.sha256(self.ns.attempt_id.encode()).hexdigest()[:12]
            inspect = await self.dk("image", "inspect", image, "--format", "{{.Id}} {{json .RepoDigests}}", timeout=120)
            if inspect.exit_code != 0 or inspect.stdout.split()[0] != cfg["actual_image_id"]:
                raise RuntimeError("actor image inspect identity differs")
            run_args = profile.docker_run_args(name=name, network="none", image=image, labels=labels)
            probe = host = cleanup = None
            try:
                started = await self.dk(*run_args, timeout=120)
                if started.exit_code != 0:
                    raise RuntimeError("bounded image-facts container start failed")
                host = await self.dk("inspect", name, "--format", "{{json .HostConfig}}", timeout=60)
                script = "cd /testbed && echo HEAD=$(git rev-parse HEAD) && echo PORCELAIN_BEGIN && git status --porcelain; echo PORCELAIN_RC=$?"
                probe = await self.dk("exec", "--user", "0", name, "bash", "-c", script, timeout=120)
                if probe.exit_code != 0 or ("HEAD=" + public["base_commit"]) not in probe.stdout:
                    raise RuntimeError("actor base image checkout differs")
                expected_porcelain = cfg.get("expected_initial_porcelain", "")
                if expected_porcelain:
                    # 原4166镜像仅有已存档的依赖元数据改动；精确核字节，不泛化允许脏树。
                    if (cfg["task_id"] != "swe_gym_lite::iterative__dvc-4166"
                            or expected_porcelain != " M setup.py\n"
                            or cfg.get("expected_initial_diff_sha256") != "sha256:8bd072b6e35dd358d920432c24b35048d4e51a9d0bc78972ceeb18e302b8dfbf"):
                        raise ValueError("initial metadata exception is not the pinned DVC4166 image")
                    initial_diff = await self.dk("exec", "--user", "0", name, "bash", "-c",
                                                 "cd /testbed && git diff --binary", timeout=60)
                    if (initial_diff.exit_code != 0 or "sha256:" + hashlib.sha256(initial_diff.stdout.encode()).hexdigest()
                            != cfg["expected_initial_diff_sha256"]):
                        raise RuntimeError("original DVC4166 metadata bytes differ")
                    self.rec["initial_metadata_diff"] = {"text": initial_diff.stdout,
                        "sha256": cfg["expected_initial_diff_sha256"], "candidate_change": False,
                        "source": "original dependency image; archived source_worktree_before.txt"}
                if ("PORCELAIN_BEGIN\n" + expected_porcelain + "PORCELAIN_RC=0") not in probe.stdout:
                    raise RuntimeError("actor base worktree differs from its pinned initial state")
                for item in cfg["baseline_test_files"]:
                    path = shlex.quote(item["path"])
                    command = ("sha256sum -- " + path) if item["base_exists"] else ("test ! -e " + path + " && test ! -L " + path)
                    row = await self.dk("exec", "--user", "0", name, "bash", "-c", "cd /testbed && " + command, timeout=60)
                    if row.exit_code != 0 or (item["base_exists"] and row.stdout.split()[0] != item["base_sha256"].removeprefix("sha256:")):
                        raise RuntimeError("public baseline test bytes differ: " + item["path"])
            finally:
                cleanup = await self.dk("rm", "-f", name, timeout=120)
                self.rec["image_facts"] = {"image": image, "inspect": inspect.stdout.strip(), "inspect_rc": inspect.exit_code,
                    "initial_worktree": probe.stdout if probe else None, "initial_worktree_rc": probe.exit_code if probe else None,
                    "probe_uses_original_rollout_profile": True, "probe_run_args": run_args,
                    "probe_host_config": json.loads(host.stdout) if host and host.exit_code == 0 else None,
                    "probe_cleanup_rc": cleanup.exit_code}
                self.save()
                if cleanup.exit_code != 0:
                    raise RuntimeError("image-facts cleanup not confirmed")

    original = argparse.Namespace(prepared_summary=str(prepared_summary), task=cfg["task_id"], commands=str(commands),
        image=cfg["actual_image_id"], out_dir=str(ns.out_dir), attempt_id=ns.attempt_id,
        stub_host=cfg.get("stub_host", "172.17.0.1"), stub_port=cfg["actor_stub_port"],
        wall_seconds=cfg.get("wall_seconds", 1800), prompt=prompt, scenario="normal",
        cc_extra_args="--max-turns " + str(len(json.loads(commands.read_text())) + 3))
    runner = BoundedDevRunner(original)
    runner.rec["input_sha256"] = sha(ns.input)
    runner.rec["frozen_release_id"] = cfg["release_id"]
    runner.rec["formal_grading"] = False
    runner.rec["model_probe"] = False

    async def go() -> int:
        inner = asyncio.ensure_future(runner.run())
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, inner.cancel)
        try:
            return await inner
        except asyncio.CancelledError:
            runner.rec["result"] = "cancelled"
            return 130
        finally:
            await runner.cleanup()

    rc = asyncio.run(go())
    first = runner.out / "stub/requests/messages_000.json"
    delivered = False
    if first.exists():
        body = json.loads(first.read_text())
        texts = []
        for message in body.get("messages", []):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                texts.extend(block["text"] for block in content if block.get("type") == "text")
        received = "\n".join(texts)
        delivered = statement in received and development_text in received
    checks = runner.rec.get("checks") or {}
    runner.rec["public_delivery"] = {"task_statement_sha256": public["problem_statement_sha256"],
        "development_sha256": cfg["public_development_sha256"], "first_request_has_exact_statement_and_development": delivered,
        "first_request_sha256": sha(first) if first.exists() else None}
    runner.save()
    residual = (runner.rec.get("cleanup") or {}).get("residual_after_force")
    clean = isinstance(residual, list) and residual == []
    ok = rc == 0 and clean and delivered and bool(checks) and all(value is True for value in checks.values())
    print(json.dumps({"attempt_id": ns.attempt_id, "actor_checks_passed": ok,
        "public_delivery": runner.rec["public_delivery"], "checks": checks, "clean": clean}, ensure_ascii=False))
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
