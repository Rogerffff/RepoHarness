"""R2E 的开发条件验证：在任务二的共用入口上只加 R2E 来源特有的一层（2026-09-25，B 线 R2E）。

共用入口 = `experiments/task2_swegym_dev_20260925/devcheck.py`：A 线 `acceptance_startup_2` 的正式装配（容器、relay、
专用网络、git sanitize、可信初始化、激活文件、启动前与激活核查、`ClaudeCodeDriver.run`）+ 真实 CC 2.1.205 + 桩端点按
命令清单逐条发出 Bash 调用 + 逐命令 rc 取回 + 清理。本脚本不另写 launcher，只换两处：

1. **任务面**：R2E 题的 `RolloutTaskSpec` 由正式的 `PreparedTaskFace.load(..., image_overlays_path/sha256)` 构造
   （派生镜像 image ID、`.venv` 激活与解释器前缀、覆盖条目与评分面互检，含修订所需环境步骤），替换入口里不带覆盖
   条目的 `rollout_spec_from_view`（后者对 R2E 题会拒绝）。不接受 `--image` 覆盖：镜像只能来自覆盖表。
2. **泄漏核查**：命令清单最前面自动加一条 R2E rollout 预检（与回放同一脚本），经 CC 的 Bash 工具以 agent 身份执行，
   按 `evaluate_r2e_rollout_preflight` 判读（解释器可执行、隐藏测试不可读、HEAD 没有子提交），结果进 `checks`。

用法（从 rh2/；需要 Docker、本机已有的派生镜像与 CC 平台包）：

  SLIME_AGENT_CC_PLATFORM_TARBALL=<claude-code-linux-x64-2.1.205.tgz> \\
  .venv/bin/python experiments/r2e_actor_20260925/r2e_devcheck.py --prepared-summary <prepared/replay_summary.json> \\
      --overlays <overlays.jsonl> --task <iid> --commands <commands/<iid>.json> --out-dir <dir> --attempt-id <id> \\
      [--stub-port 18190]
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import signal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE.parent / "task2_swegym_dev_20260925"))
import devcheck  # noqa: E402  共用入口（任务二）

from repoharness2.adapters.slime import prepared_task_face as ptf  # noqa: E402
from repoharness2.adapters.slime.r2e_grading_scripts import (  # noqa: E402
    evaluate_r2e_rollout_preflight,
    render_r2e_rollout_preflight_script,
)

PREFLIGHT_ID = "r2e_preflight"


class R2EDevRunner(devcheck.DevRunner):
    def __init__(self, ns: argparse.Namespace) -> None:
        summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
        overlays_sha = hashlib.sha256(Path(ns.overlays).read_bytes()).hexdigest()
        # 正式任务面：R2E 题缺覆盖条目、互检不过、修订所需环境步骤缺失，都在这里拒绝（候选阶段之前）
        self.face = ptf.PreparedTaskFace.load(
            prepared_dir=summary["prepared_dir"], manifest_sha256=summary["prepared_manifest_sha256"],
            host_grading_path=Path(summary["private_dir"]) / "host_grading_views.jsonl",
            host_grading_sha256=summary["host_grading_artifact_sha256"], time_budget_seconds=int(ns.wall_seconds),
            image_overlays_path=ns.overlays, image_overlays_sha256=overlays_sha,
        )
        overlay = ptf.load_overlays_input(ns.overlays, overlays_sha).get(ns.task_id)
        # 预检作为第一条命令，经真实 CC 的 Bash 工具以 agent 身份执行
        cmds = json.loads(Path(ns.commands).read_text(encoding="utf-8"))
        if any(c.get("id") == PREFLIGHT_ID for c in cmds):
            raise SystemExit(f"命令清单里不要自带 {PREFLIGHT_ID}（由本脚本注入）")
        pre = {"id": PREFLIGHT_ID, "timeout_s": 60, "expect": "any", "purpose": "R2E rollout 预检（agent 身份，经 CC Bash）",
               "cmd": render_r2e_rollout_preflight_script()}
        Path(ns.out_dir).mkdir(parents=True, exist_ok=True)
        aug = Path(ns.out_dir) / "commands_with_preflight.json"
        aug.write_text(json.dumps([pre, *cmds], ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ns.commands_original = ns.commands
        ns.commands = str(aug)
        super().__init__(ns)
        self.rec.update({
            "r2e_layer": "experiments/r2e_actor_20260925/r2e_devcheck.py",
            "commands_original": ns.commands_original,
            "overlays": ns.overlays, "overlays_sha256": "sha256:" + overlays_sha,
            "overlay": None if overlay is None else {
                "derived_image_id": overlay.derived_image_id, "derived_image_ref": overlay.derived_image_ref,
                "recipe_id": overlay.recipe_id, "base_image_ref": overlay.base_image_ref,
            },
        })

    async def run(self) -> int:
        orig = ptf.rollout_spec_from_view
        face = self.face

        def formal(view, **kw):  # noqa: ANN001, ANN003
            if view.source != ptf.R2E_TASK_SOURCE:
                return orig(view, **kw)
            return face.rollout_spec(view.task_id)

        ptf.rollout_spec_from_view = formal
        try:
            return await super().run()
        finally:
            ptf.rollout_spec_from_view = orig

    def evaluate(self) -> None:
        super().evaluate()
        cap = self.out / "captures" / f"{PREFLIGHT_ID}.out"
        text = cap.read_text(encoding="utf-8") if cap.is_file() else ""
        failures = evaluate_r2e_rollout_preflight(text)
        self.rec["r2e_preflight"] = {"failures": failures,
                                     "lines": [ln for ln in text.splitlines() if ln.startswith("RH2_PREFLIGHT_")]}
        self.rec["checks"]["r2e_preflight_ok"] = not failures
        spec = self.face.rollout_spec(self.rec.get("task_id") or self.ns.task_id)
        self.rec["checks"]["image_is_overlay_derived_id"] = self.rec.get("image") == spec.image == (self.rec.get("overlay") or {}).get("derived_image_id")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--overlays", required=True)
    ap.add_argument("--task", required=True, help="裸 instance_id 或 r2e_gym_subset::<iid>")
    ap.add_argument("--commands", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--attempt-id", required=True)
    ap.add_argument("--stub-host", default="172.17.0.1")
    ap.add_argument("--stub-port", type=int, default=18190)
    ap.add_argument("--wall-seconds", type=int, default=1800)
    ap.add_argument("--prompt", default="Devcheck run: execute exactly the tool calls you are given, then stop.")
    ns = ap.parse_args(argv)
    ns.task_id = f"{ptf.R2E_TASK_SOURCE}::{ns.task.split('::')[-1]}"
    ns.image = None  # 镜像只来自覆盖表
    ns.scenario = "normal"
    if not re.match(r"^[A-Za-z0-9_.-]{6,96}$", ns.attempt_id):
        ap.error("--attempt-id 形态不合法")
    if not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL")
    runner = R2EDevRunner(ns)
    ns.cc_extra_args = f"--max-turns {len(runner.cmds) + 3}"

    async def go() -> int:
        loop = asyncio.get_running_loop()
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

    rc = asyncio.run(go())
    residual = (runner.rec.get("cleanup") or {}).get("residual_after_force")
    print(json.dumps({"result": runner.rec.get("result"), "harness_exit_code": runner.rec.get("harness_exit_code"),
                      "checks": runner.rec.get("checks"), "r2e_preflight": runner.rec.get("r2e_preflight"),
                      "commands": [(r["id"], r["status"], r["rc"], r["pytest"]) for r in runner.rec.get("commands_result") or []],
                      "residual": residual, "failure_detail": runner.rec.get("failure_detail")}, ensure_ascii=False, indent=1))
    return 4 if residual else rc


if __name__ == "__main__":
    raise SystemExit(main())
