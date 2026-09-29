"""本批诊断的准备预算覆写；测试、评分、保护脚本及生产文件保持不变。"""
import argparse
import dataclasses
import importlib.util
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setup-seconds", type=float, required=True)
    ap.add_argument("--budget-audit-dir", required=True)
    args, remaining = ap.parse_known_args()
    code = Path(remaining[remaining.index("--code-root") + 1]).resolve()
    if not 300 <= args.setup_seconds <= 1800:
        raise ValueError("this CPU diagnostic permits a bounded 300–1800 second preparation budget")
    audit = Path(args.budget_audit_dir)
    audit.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(code / "src"))
    sys.path.insert(1, str(code / "experiments/env_recipe_repair_20260919"))
    from repoharness2.adapters.slime import replay_grade as replay
    original = replay.build_grading_spec_from_host_view

    def build(view, **kwargs):
        before = original(view=view, **kwargs)
        after = dataclasses.replace(before, env_reset_timeout_seconds=args.setup_seconds)
        (audit / (view.instance_id + ".json")).write_text(json.dumps({
            "instance_id": view.instance_id, "before": before.env_reset_timeout_seconds,
            "after": after.env_reset_timeout_seconds, "test_seconds_unchanged": before.test_timeout_seconds,
            "scope": "CPU host preparation/reset/observation budget only; whole-grading CLI deadline independent",
            "reason": "observed overlay2 metacopy=N prefix chown preparation timeout; no kernel or permission change",
        }, indent=2) + "\n")
        return after

    replay.build_grading_spec_from_host_view = build
    path = code / "experiments/env_recipe_repair_20260919/replay_with_install_recipe.py"
    spec = importlib.util.spec_from_file_location("cpu29_frozen_recipe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.argv = [str(path), *remaining]
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
