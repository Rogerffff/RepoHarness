"""R2E actor 环境绑定的 CPU 审查探针；不启动 Docker、不联网、不改原始 evidence。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ARTIFACT_ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--run-dir", type=Path, help="指定本 actor 审查目录内的全新输出目录；默认每次新建 probe_runs/<随机ID>")
args = parser.parse_args()
OUT = (args.run_dir or (ARTIFACT_ROOT / "probe_runs" / uuid.uuid4().hex[:12])).resolve()
if not OUT.is_relative_to(ARTIFACT_ROOT):
    parser.error("--run-dir 必须位于本 actor 审查目录内")
OUT.mkdir(parents=True, exist_ok=False)
ROOT = next(p for p in ARTIFACT_ROOT.parents if (p / "rh2/src/repoharness2").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))

from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace, overlay_binding_mismatch
from repoharness2.adapters.slime.replay_grade import prepare_for_replay
from repoharness2.envpack.environment_overlay import env_requirement_mismatch, load_environment_overlays
from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs


IID = "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
TID = "r2e_gym_subset::" + IID
spec = importlib.util.spec_from_file_location("r2e_actor_build_review", ROOT / "rh2/scripts/build_r2e_derived.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
trusted = load_trusted_r2e_ingest_outputs(ROOT)
public = next(p for p in trusted.result.public_bundles if p.instance_id == IID)
grading = next(g for g in trusted.result.grading_bundles if g.instance_id == IID)
pins = json.loads((ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/recipes/env_pins_v2.json").read_text())
approved = pins["tasks"][IID]
wrong = copy.deepcopy(pins["tasks"]["numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d"])
wrong["env_step"] = "env_v2.sh"
wrong["venv_changed_globs"] = [s.replace("python3.10", "python3.7") for s in wrong["venv_changed_globs"]]
# 此输入使用仓库已有、真实有效的 universal wheel / sha，不伪造覆盖表。它只安装 hypothesis，保留来源镜像的 SciPy。
wrong_path = OUT / "wrong_package_pins.json"
wrong_path.write_text(json.dumps({"schema_id": build.ENV_PINS_SCHEMA_ID, "tasks": {IID: wrong}}, ensure_ascii=False, indent=2) + "\n")
validated_wrong = build.load_env_pins(wrong_path)[IID]


class StopBeforeDocker:
    """边界探针：只记录构建器抵达的第一条 Docker 请求，绝不执行。"""

    def __init__(self):
        self.calls = []

    def inspect(self, ref):
        self.calls.append({"operation": "image_inspect", "ref": ref})
        raise RuntimeError("CPU_PROBE_STOP_AT_DOCKER_BOUNDARY")


build_rows = {}
for name, ent in (("no_environment_step", None), ("approved_scipy", approved), ("wrong_package", validated_wrong)):
    boundary = StopBeforeDocker()
    result = build.build_one(
        boundary, out=OUT / "build_boundary" / name, public=public, grading=grading,
        tag_prefix="cpu-probe-do-not-build", skip_pull=True, timeouts={"pull": 1, "build": 1, "check": 1},
        repo_root=ROOT, revisions=trusted.revisions.get(IID, ()), env_entry=ent,
    )
    build_rows[name] = {
        "pins": result["env_pins"], "recipe_id": result["recipe_id"], "recipe_sha256": result["recipe_sha256"],
        "material_guard": env_requirement_mismatch(result["recipe_id"], grading.material_revisions),
        "docker_boundary_calls": boundary.calls, "stopped_result_failures": result["failures"],
        "built": False,
    }

assert not build_rows["no_environment_step"]["docker_boundary_calls"]
assert build_rows["approved_scipy"]["docker_boundary_calls"]
assert build_rows["wrong_package"]["docker_boundary_calls"]
assert build_rows["approved_scipy"]["recipe_id"] == build_rows["wrong_package"]["recipe_id"]
assert build_rows["approved_scipy"]["recipe_sha256"] != build_rows["wrong_package"]["recipe_sha256"]

old = load_environment_overlays(ROOT / "runs/r2e_rf_20260923/remote/r2e_derived/overlays.jsonl")[TID]
good = load_environment_overlays(ROOT / "runs/r2e_t0_batch3_20260924/derived7/overlays.jsonl")[TID]
overlay_rows = {
    "actual_old_overlay": {"image": old.derived_image_id, "recipe": old.recipe_id,
                           "rejection": overlay_binding_mismatch(old, public=public, grading=grading)},
    "actual_approved_overlay": {"image": good.derived_image_id, "recipe": good.recipe_id,
                                "rejection": overlay_binding_mismatch(good, public=public, grading=grading)},
}
assert overlay_rows["actual_old_overlay"]["rejection"]
assert overlay_rows["actual_approved_overlay"]["rejection"] is None

prep = OUT / "prepared_probe"
summary = prepare_for_replay(repo_root=ROOT, out_dir=prep / "public", private_dir=prep / "private", task_ids=[TID], sources=("r2e_gym_subset",))
overlay_path = OUT / "approved_overlay.jsonl"
overlay_path.write_text(good.model_dump_json() + "\n")
overlay_sha = hashlib.sha256(overlay_path.read_bytes()).hexdigest()


def load_face(**kwargs):
    return PreparedTaskFace.load(
        prepared_dir=prep / "public", manifest_sha256=summary["prepared_manifest_sha256"],
        host_grading_path=prep / "private/host_grading_views.jsonl", host_grading_sha256=summary["host_grading_artifact_sha256"],
        time_budget_seconds=600, **kwargs,
    )


with patch.dict(os.environ, {"RH2_IMAGE_OVERLAYS_PATH": str(overlay_path), "RH2_IMAGE_OVERLAYS_SHA256": overlay_sha}):
    face = load_face()
    rollout = face.rollout_spec(TID)
    record = face.manifest.record(TID)
    gspec = face.grading_spec(SimpleNamespace(task_id=TID, environment_package_digest=record.environment_package_digest,
                                            public_bundle_digest=record.public_bundle_digest))
    task_face = {
        "loaded_via_environment": True, "rollout_image": rollout.image, "grading_image": gspec.image,
        "grading_local_build_id": gspec.image_local_build_id, "rollout_local_build": rollout.image_local_build,
        "grading_local_build": gspec.image_local_build, "rollout_interpreter_prefix": rollout.expected_interpreter_prefix,
        "rollout_manifest_digest": rollout.image_manifest_digest, "grading_manifest_digest": gspec.image_manifest_digest,
        "public_payload_keeps_source_image": json.loads(rollout.public_bundle_payload)["image"] == public.image,
    }
    assert task_face["rollout_image"] == task_face["grading_image"] == good.derived_image_id
    assert gspec.image_local_build_id == good.derived_image_id

source_files = [
    "rh2/src/repoharness2/adapters/slime/prepared_task_face.py",
    "rh2/src/repoharness2/envpack/environment_overlay.py",
    "rh2/scripts/build_r2e_derived.py", "rh2/scripts/r2e_derive/env_v2.sh",
    "rh2/src/repoharness2/adapters/slime/bringup.py", "rh2/src/repoharness2/adapters/slime/generate.py",
    "rh2/experiments/miles_gpu_spike/launch.sh",
    "rh2/experiments/r2e_actor_20260925/r2e_devcheck.py",
    "rh2/experiments/task2_swegym_dev_20260925/devcheck.py",
    "rh2/experiments/base_probe_fixes_20260923/acceptance_startup_2.py",
]
result = {
    "scope": "CPU only; no Docker, network, SSH, model, or scoring execution. Build probe stops at first Docker boundary.",
    "task_id": TID, "material_revisions": list(grading.material_revisions), "build_boundary": build_rows,
    "actual_overlay_checks": overlay_rows, "task_face": task_face,
    "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in source_files},
}
(OUT / "probe_actor_binding.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"run_dir": str(OUT.relative_to(ROOT)), "output": str((OUT / "probe_actor_binding.json").relative_to(ROOT)), "old_overlay_rejected": True,
                  "wrong_package_reached_docker_boundary": True, "actual_task_face_both_sides_same_image": True}, ensure_ascii=False))
