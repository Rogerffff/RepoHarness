#!/usr/bin/env python3
"""按正式链语义直接评分求解容器的冻结补丁（2026-09-29，B 线 R2E 探针原型的对照）。

正式链（generate.py fa_formal）不经 git 补丁：rollout 容器里 census 冻结导出 → `FrozenDeltaSource(冻结补丁, rollout 基线清单,
可信投影)` → `SWEGradingManager.grade(workspace=None, frozen_delta=…)`；grader 在全新容器里先用同一 census 重建基线清单、
摘要必须相等（`_verify_baseline_rebuild`），再把冻结条目按字节写入。`replay_grade run` 则在自己的候选容器里重新生成
基线与冻结补丁。本脚本走前一条：读 `r2e_solve_attempt.py` 落盘的 `frozen/frozen_patch.json` 与 `frozen/baseline_manifest.json`，
评分 spec 与 `PreparedTaskFace.grading_spec` 同一构造（评分面 → R2E spec → 切到覆盖表派生镜像 ID），正式 grader profile。

    <rh2>/.venv/bin/python experiments/r2e_lifecycle_20260929/grade_frozen_direct.py --prepared-summary <...> \\
        --overlays <overlays.jsonl> --attempt-dir <attempt> --out-dir <dir>
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))

from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view  # noqa: E402
from repoharness2.adapters.slime.replay_grade import load_context  # noqa: E402
from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env, rollout_profile_from_env  # noqa: E402
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest  # noqa: E402
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest  # noqa: E402
from repoharness2.contracts.scoring_projection import classify_frozen_patch  # noqa: E402
from repoharness2.envpack.environment_overlay import load_environment_overlays  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    BaselineIntegrityError, FrozenDeltaSource, GradingManagerConfig, SWEGradingManager,
)
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection  # noqa: E402


async def amain(ns: argparse.Namespace) -> int:
    out = Path(ns.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
    grader = grader_profile_from_env(os.environ)
    ctx = load_context(
        prepared_dir=summary["prepared_dir"], private_dir=summary["private_dir"],
        manifest_sha256=summary["prepared_manifest_sha256"],
        rollout_profile=rollout_profile_from_env(os.environ, model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1),
        grader_profile=grader, artifacts_dir=out / "unused", run_id=os.environ.get("MILES_RH2_RUN_ID"),
    )
    adir = Path(ns.attempt_dir)
    arec = json.loads((adir / "attempt.json").read_text(encoding="utf-8"))
    task_id = arec["task_id"]
    gview, public = ctx.grading_views[task_id], ctx.rollout_views[task_id].public
    overlay = load_environment_overlays(ns.overlays)[task_id]
    # 与 PreparedTaskFace.grading_spec 同一构造：评分面 → spec → 评分容器切到覆盖表派生镜像 ID（不可重指）
    spec = build_grading_spec_from_host_view(gview, image=public.image, image_manifest_digest=public.image_manifest_digest)
    spec = dataclasses.replace(spec, image=overlay.derived_image_id, image_manifest_digest=None, image_local_build=True,
                               image_local_build_id=overlay.derived_image_id)
    art = FrozenPatchArtifactV1.model_validate_json((adir / "frozen" / "frozen_patch.json").read_text(encoding="utf-8"))
    base = BaselineWorkspaceManifestV1.model_validate_json((adir / "frozen" / "baseline_manifest.json").read_text(encoding="utf-8"))
    cls, _ = classify_frozen_patch(art, base)
    res: dict = {"schema": "rh2.r2e_probe_proto.grade_frozen_direct.v1", "task_id": task_id, "attempt_dir": str(adir),
                 "image": spec.image, "frozen_patch_digest": compute_frozen_patch_digest(art),
                 "baseline_manifest_digest": compute_baseline_manifest_digest(base), "classification": cls.verdict,
                 "entries": [e.path for e in art.entries]}
    if cls.verdict != "projectable":
        res["not_graded"] = "unsafe_artifact"
    else:
        projection, split = build_trusted_scoring_projection(art, spec.hygiene)
        res["projection_included_paths"] = list(projection.included_entry_paths)
        res["projection_ignored_paths"] = [e.path for e in split.ignored_entries]
        source = FrozenDeltaSource(frozen_patch=art, baseline_manifest=base, projection=projection,
                                   frozen_patch_digest=compute_frozen_patch_digest(art))
        manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=out / "eval_logs", sandbox_profile=grader))
        await manager.startup()
        t = time.monotonic()
        try:
            rep = await manager.grade(trajectory_id=f"direct-{arec['attempt_id']}"[:80], workspace=None, spec=spec,
                                      frozen_delta=source, deadline_monotonic=time.monotonic() + float(ns.grading_deadline_seconds))
            res["report"] = {"outcome": rep.outcome, "reward": rep.reward, "failure_category": rep.failure_category,
                             "expected_match": rep.expected_match_count, "expected_total": rep.expected_total_count,
                             "infra_failure_detail": rep.infra_failure_detail, "grading_semantics": rep.grading_semantics}
        except BaselineIntegrityError as exc:
            res["baseline_integrity_error"] = {"reason_code": getattr(exc, "reason_code", None), "detail": str(exc)[:800]}
        except Exception as exc:  # noqa: BLE001 - 如实记录
            res["grade_exception"] = f"{type(exc).__name__}: {exc}"[:800]
        finally:
            res["seconds"] = round(time.monotonic() - t, 1)
            res["manager_close"] = await manager.close()
    (out / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("entries",)}, ensure_ascii=False, default=str)[:3000])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepared-summary", required=True)
    ap.add_argument("--overlays", required=True)
    ap.add_argument("--attempt-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--grading-deadline-seconds", type=float, default=3600.0)
    return asyncio.run(amain(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
