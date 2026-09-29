"""R2E 正式 actor 任务面的真实核对（不建网络、不起 relay 与 Claude Code；2026-09-25，B 线）。

对选定的 R2E 题，按正式代码构造任务面（`PreparedTaskFace.load` + 覆盖表），然后用 `RolloutTaskSpec.image`（派生镜像的
image ID）起一个 `--network none` 容器，按正式函数依次执行：

1. `rollout_trusted_init_script`（root 可信初始化：固定 uid 的 agent 用户、属主）；
2. 把任务面的 `env_activation_script` 写到 `/rh2/bash_env`（root 0644，与 generate.py 的写法相同）；
3. `run_rollout_activation_check`（agent 身份、与 CC launcher 同一份 env，`python` 必须落在任务面声明的前缀下）；
4. R2E rollout 预检（agent 身份：解释器可执行、隐藏测试不可读、HEAD 没有子提交）——回放路径的同一脚本；
5. 反例：同一容器改用 SWE-Gym 的 conda 前缀做激活核查，应当失败。

这只核对"派生镜像 + R2E 激活 + 前缀 + 预检"在真实镜像里成立；真实 CC 启动链（relay、桩端点、专用网络）不在本脚本里，
另行安排。用法（从 rh2/，需要 Docker 与本机已有的派生镜像）：

  .venv/bin/python experiments/r2e_actor_20260925/activation_check.py --repo-root .. \\
      --overlays /work/b_r2e/derived7/overlays.jsonl --task-ids <iid>[,<iid>…] --out <结果 json>
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace  # noqa: E402
from repoharness2.adapters.slime.r2e_grading_scripts import (  # noqa: E402
    evaluate_r2e_rollout_preflight,
    render_r2e_rollout_preflight_script,
)
from repoharness2.adapters.slime.replay_grade import prepare_for_replay  # noqa: E402
from repoharness2.adapters.slime.sandbox_profile import (  # noqa: E402
    _exec_as,
    agent_shell_env,
    default_docker_runner,
    rollout_profile_from_env,
    rollout_trusted_init_script,
    run_rollout_activation_check,
    run_trusted_init,
)
from repoharness2.envpack import materialize  # noqa: E402


async def check_one(face: PreparedTaskFace, task_id: str, profile) -> dict:
    docker = default_docker_runner
    spec = face.rollout_spec(task_id)
    rec: dict = {"task_id": task_id, "image": spec.image, "image_local_build": spec.image_local_build,
                 "expected_interpreter_prefix": spec.expected_interpreter_prefix,
                 "env_activation_script_sha256": "sha256:" + hashlib.sha256(spec.env_activation_script.encode()).hexdigest()}
    name = f"rh2-r2e-actcheck-{uuid.uuid4().hex[:10]}"
    run = await docker("run", "-d", "--network", "none", "--label", "rh2.b_r2e=activation_check", "--name", name,
                       spec.image, "sleep", "infinity")
    rec["container_started"] = run.exit_code == 0
    if run.exit_code != 0:
        rec["error"] = run.stderr.strip()[-300:]
        return rec
    try:
        img = await docker("inspect", "-f", "{{.Image}}", name)
        rec["container_image_is_spec_image"] = img.stdout.strip() == spec.image
        rec["trusted_init"] = await run_trusted_init(docker, name=name, script=rollout_trusted_init_script(profile),
                                                     timeout=profile.probe_timeout_seconds)
        path = materialize.BASH_ENV_PATH
        write = await docker("exec", "-i", name, "bash", "-c", f"mkdir -p $(dirname {path}) && cat > {path} && chmod 0644 {path}",
                             input_bytes=spec.env_activation_script.encode())
        rec["activation_file_written"] = write.exit_code == 0
        env = agent_shell_env(profile, activation_file=path)
        good = await run_rollout_activation_check(docker, name=name, profile=profile, env=env,
                                                  expected_interpreter_prefix=spec.expected_interpreter_prefix)
        rec["activation_check"] = {"ok": good.ok, "violations": good.violations, "facts": dict(good.probe_facts)}
        bad = await run_rollout_activation_check(docker, name=name, profile=profile, env=env,
                                                 expected_interpreter_prefix=materialize.SWE_GYM_INTERPRETER_PREFIX)
        rec["negative_conda_prefix"] = {"ok": bad.ok, "violations": bad.violations}
        pre = await _exec_as(docker, name, render_r2e_rollout_preflight_script(), user=str(profile.agent_uid),
                             home=env["HOME"], timeout=profile.probe_timeout_seconds)
        rec["r2e_preflight"] = {"failures": evaluate_r2e_rollout_preflight(pre.stdout),
                                "lines": [ln for ln in pre.stdout.splitlines() if ln.startswith("RH2_PREFLIGHT_")]}
        rec["ok"] = (rec["container_image_is_spec_image"] and rec["activation_file_written"] and good.ok and not bad.ok
                     and not rec["r2e_preflight"]["failures"])
    finally:
        rm = await docker("rm", "-f", name)
        rec["container_removed"] = rm.exit_code == 0
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--overlays", required=True)
    ap.add_argument("--task-ids", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    ids = [f"r2e_gym_subset::{x.strip().split('::')[-1]}" for x in ns.task_ids.split(",") if x.strip()]
    overlays_sha = hashlib.sha256(Path(ns.overlays).read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="r2e_actcheck_") as tmp:
        summary = prepare_for_replay(repo_root=ns.repo_root, out_dir=Path(tmp) / "prepared", private_dir=Path(tmp) / "private",
                                     task_ids=ids, sources=("r2e_gym_subset",))
        face = PreparedTaskFace.load(
            prepared_dir=Path(tmp) / "prepared", manifest_sha256=summary["prepared_manifest_sha256"],
            host_grading_path=Path(tmp) / "private" / "host_grading_views.jsonl",
            host_grading_sha256=summary["host_grading_artifact_sha256"], time_budget_seconds=600,
            image_overlays_path=ns.overlays, image_overlays_sha256=overlays_sha,
        )
        profile = rollout_profile_from_env(os.environ, model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1)

        async def go() -> list[dict]:
            return [await check_one(face, tid, profile) for tid in ids]

        results = asyncio.run(go())
    doc = {"schema": "rh2.b_r2e.activation_check.v1", "overlays": ns.overlays, "overlays_sha256": overlays_sha,
           "profile_digest": profile.digest(), "results": results}
    Path(ns.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for r in results:
        print(json.dumps({"task_id": r["task_id"], "ok": r.get("ok"), "activation_ok": (r.get("activation_check") or {}).get("ok"),
                          "negative_rejected": not (r.get("negative_conda_prefix") or {}).get("ok", True),
                          "preflight_failures": (r.get("r2e_preflight") or {}).get("failures"),
                          "removed": r.get("container_removed")}, ensure_ascii=False))
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
