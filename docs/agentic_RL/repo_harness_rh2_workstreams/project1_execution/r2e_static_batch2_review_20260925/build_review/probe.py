"""本机只读源材料探针：核 R1/O1、既有 orange3 日志及正式冻结产物路径。

只在本脚本同目录创建临时夹具与结果；不启动 Docker、不访问网络、不编译原生扩展。
冻结路径使用二进制哨兵字节，不代表 orange3 真实构建/导入通过。
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / "rh2/src"))

from repoharness2.adapters.slime.baseline_census import baseline_policy_for_task_id, generate_baseline_manifest
from repoharness2.adapters.slime.patch_exporter import export_frozen_patch
from repoharness2.adapters.slime.prepared_task_face import load_overlays_input, overlay_binding_mismatch
from repoharness2.adapters.slime.r2e_grading_scripts import build_r2e_grading_spec
from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest
from repoharness2.contracts.scoring_projection import classify_frozen_patch
from repoharness2.envpack.environment_overlay import REVISION_ENV_REQUIREMENTS
from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest
from repoharness2.grading.manager import FrozenDeltaSource, SWEGradingManager, screen_frozen_entries
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection

IID = "orange3__4014f2483e3bab0621c9ae0f994947c008183253"
TID = "r2e_gym_subset::" + IID
ENV_IID = "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
RUN = ROOT / "runs/r2e_actor_20260925"
PUBLIC_ROOT = ROOT / "runs/r2e_static_prep_20260924/v3/public" / IID
checks: list[dict] = []


def check(name: str, condition: bool, **facts) -> None:
    checks.append({"name": name, "passed": bool(condition), **facts})
    assert condition, name


def sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class LocalWorkspace:
    def __init__(self):
        self.scripts = []

    async def run_bash(self, script: str):
        self.scripts.append(script)
        proc = subprocess.run(["/bin/bash", "-c", script], capture_output=True, check=False)
        return SimpleNamespace(exit_code=proc.returncode, stdout=proc.stdout.decode(), stderr=proc.stderr.decode())


class LocalApplyManager(SWEGradingManager):
    async def _exec_bash_checked(self, record, script, *, phase, timeout, input_bytes=None):
        proc = subprocess.run(["/bin/bash", "-c", script], input=input_bytes, capture_output=True, timeout=timeout, check=False)
        return SimpleNamespace(exit_code=proc.returncode, stdout=proc.stdout.decode(), stderr=proc.stderr.decode())


async def frozen_binary_probe(public, grading, scratch: Path) -> None:
    tree = scratch / "rollout"
    tree.mkdir()
    so_path = "Orange/preprocess/_discretize.cpython-37m-x86_64-linux-gnu.so"
    pyx_path = "Orange/preprocess/_discretize.pyx"
    c_path = "Orange/preprocess/_discretize.c"
    obj_path = "build/temp.linux-x86_64-3.7/Orange/preprocess/_discretize.o"
    files = {
        ".gitignore": (PUBLIC_ROOT / "worktree/.gitignore").read_bytes(),
        so_path: b"BINARY_SENTINEL_OLD\x00\xff",
        pyx_path: b"old pyx\n",
        c_path: b"old generated C\n",
        "datasets": b"unchanged initial untracked file\n",
        ".git/keep": b"excluded\n",
        ".venv/keep": b"excluded\n",
        "pkg/__pycache__/keep.pyc": b"omitted cache\n",
    }
    for name, body in files.items():
        path = tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    replica = scratch / "grader"
    shutil.copytree(tree, replica)
    workspace = LocalWorkspace()
    baseline = await generate_baseline_manifest(
        workspace, task_id=TID, workdir=str(tree),
        public_bundle_digest="sha256:" + "a" * 64, runtime_image_digest="sha256:" + "b" * 64,
        materialized_head=public.base_commit, task_base_commit=public.base_commit,
        policy=baseline_policy_for_task_id(TID),
    )
    changed = {
        so_path: b"BINARY_SENTINEL_CHANGED\x00\xff\x01",
        pyx_path: b"modified pyx\n", c_path: b"modified generated C\n",
        obj_path: b"OBJECT_SENTINEL\x00\xfe",
    }
    for name, body in changed.items():
        path = tree / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    artifact = await export_frozen_patch(workspace, baseline, rollout_execution_id="review_binary_probe", physical_attempt_id="review_binary_probe#p1")
    report, projection = classify_frozen_patch(artifact, baseline)
    spec = build_r2e_grading_spec(task_id=TID, grading=grading, image=public.image, image_manifest_digest=public.image_manifest_digest)
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection, frozen_patch_digest=compute_frozen_patch_digest(artifact))
    plan = screen_frozen_entries(list(split.candidate_entries), spec.hygiene)
    manager = object.__new__(LocalApplyManager)
    await manager._apply_frozen_delta(None, SimpleNamespace(testbed_path=str(replica), apply_timeout_seconds=30), source, plan)
    paths = [entry.path for entry in artifact.entries]
    actual_bytes = {entry.path: base64.b64decode(entry.content_b64) for entry in artifact.entries}
    check("frozen_export_keeps_ignored_binary_and_generated_files", set(paths) == set(changed) and actual_bytes == changed,
          artifact_paths=paths, policy=baseline.policy.model_dump(), note="真实本机文件 census/export；所有 .so/.o 内容为哨兵字节，未编译或导入。")
    check("r2e_projection_and_apply_preserve_binary_bytes", report.verdict == "projectable" and plan.verdict == "clean"
          and set(split.candidate_paths) == set(changed) and not split.ignored_paths
          and plan.apply_completed and all((replica / name).read_bytes() == body for name, body in changed.items()),
          candidate_paths=list(split.candidate_paths), ignored_paths=list(split.ignored_paths), apply_completed=plan.apply_completed,
          byte_digests={name: sha(body) for name, body in changed.items()})
    check("unchanged_initial_untracked_file_not_exported", "datasets" not in paths)


def existing_evidence(grading) -> None:
    candidate = RUN / "grader_cands/orange3_4014_C2_pyx_only.patch"
    ledger = json.loads((RUN / "grader/ledger_o4014_C2_pyx_only.jsonl").read_text())
    log_path = RUN / "grader/eval_logs" / Path(ledger["log"]["path"]).name
    log_raw = log_path.read_bytes()
    expected = normalize_status_map(json.loads((ROOT / "runs/r2e_static_prep_20260924/v3/private" / IID / "expected_output.json").read_text()))
    observed = normalize_status_map(parse_log_pytest(log_raw.decode()))
    mismatch = {k: {"expected": v, "observed": observed.get(k)} for k, v in expected.items() if observed.get(k) != v}
    check("C2_grader_log_and_patch_identity", ledger["candidate"]["patch_sha256"] == sha(candidate.read_bytes()) and ledger["log"]["sha256"] == sha(log_raw),
          log_path=str(log_path.relative_to(ROOT)), patch_sha256=sha(candidate.read_bytes()), log_sha256=sha(log_raw))
    check("C2_grader_original_result", ledger["report"]["reward"] == 0.0 and len(expected) == 27
          and sum(observed.get(k) == v for k, v in expected.items()) == 26
          and list(mismatch) == ["TestEqualFreq.test_below_precision"],
          matched=26, total=27, mismatch=mismatch, included_paths=ledger["projection"]["included_paths"], install_skipped=ledger["install"]["install_skipped"])
    for name, match, build in [("o4014_C2_nobuild", 26, None), ("o4014_C2_build", 27, 0), ("o4014_gold_build", 27, 0)]:
        rec = json.loads((RUN / "grader/private_regrade" / (name + ".json")).read_text())
        obs = normalize_status_map(parse_log_pytest(rec["log_tail"]))
        check(name, rec["user"] == "root" and rec["image"] == ledger["image_id_actual"]
              and rec.get("build_rc") == build and rec["expected_match"] == match
              and sum(obs.get(k) == v for k, v in expected.items()) == match,
              user=rec["user"], expected_match=match, expected_total=len(expected), build_rc=rec.get("build_rc"),
              cythonized=rec.get("build_cythonized"), note="核对既有 root 实跑记录；本轮未重跑容器或构建。")
    capture = RUN / "devcheck" / IID[:40]
    failed = (capture / "agentpath2/captures/build_full_error.out").read_text()
    facts = (capture / "agentpath2/captures/linker_facts.out").read_text()
    check("agent_link_failure_is_specific_and_recorded", "BUILD_RC=1" in failed and "cannot find -lpython3.7m" in failed
          and "-L/root/.local/share/uv/python/cpython-3.7.9-linux-x86_64-gnu/lib" in failed
          and "Permission denied" in facts and "libpython3.7m.so" in facts,
          build_log=str((capture / "agentpath2/captures/build_full_error.out").relative_to(ROOT)),
          linker_facts=str((capture / "agentpath2/captures/linker_facts.out").relative_to(ROOT)))
    script = build_r2e_grading_spec(task_id=TID, grading=grading, image="local:test", image_manifest_digest="sha256:" + "1" * 64).candidate_test_script
    check("candidate_stage_has_no_automatic_rebuild", "RH2_INSTALL_SKIPPED=1" in script and "bash run_tests.sh" in script
          and "build_ext" not in script and "build_ext" not in grading.run_tests_sh)


def binding_probe(trusted, scratch: Path) -> None:
    public = next(p for p in trusted.result.public_bundles if p.instance_id == ENV_IID)
    grading = next(g for g in trusted.result.grading_bundles if g.instance_id == ENV_IID)
    overlay_path = ROOT / "runs/r2e_t0_batch3_20260924/derived7/overlays.jsonl"
    verified = overlay_path.read_bytes()
    count = 0
    orig = Path.read_bytes
    orig_text = Path.read_text

    def one_read(path):
        nonlocal count
        if path == overlay_path:
            count += 1
            assert count == 1, "覆盖表被重复读取"
            return verified
        return orig(path)

    def no_text_reread(path, *args, **kwargs):
        assert path != overlay_path, "覆盖表通过 read_text 被重读"
        return orig_text(path, *args, **kwargs)

    with patch.object(Path, "read_bytes", one_read), patch.object(Path, "read_text", no_text_reread):
        overlays = load_overlays_input(overlay_path, sha(verified))
    check("O1_verified_bytes_read_once", count == 1, read_bytes_count=count)
    overlay = overlays["r2e_gym_subset::" + ENV_IID]
    check("R1_real_approved_overlay_accepted", overlay_binding_mismatch(overlay, public=public, grading=grading) is None,
          approved_recipe_sha256=overlay.recipe_sha256)
    bad = overlay.model_copy(update={"recipe_sha256": "sha256:" + "0" * 64})
    error = overlay_binding_mismatch(bad, public=public, grading=grading)
    check("R1_same_step_wrong_digest_rejected", error is not None and "env_recipe_not_approved:r2e-mr-020" in error, error=error)
    module_spec = importlib.util.spec_from_file_location("review_build_r2e", ROOT / "rh2/scripts/build_r2e_derived.py")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    pins_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/recipes/env_pins_v2.json"
    approved = module.load_env_pins(pins_path)[ENV_IID]
    digest = module.composite_recipe_digest(material_manifest_bytes=None, env_manifest_bytes=module.env_manifest(approved), env_step=approved["env_step"])
    check("R1_digest_recomputed_matches_approved_real_build", digest == overlay.recipe_sha256
          and digest in REVISION_ENV_REQUIREMENTS["r2e-mr-020"].approved_recipe_sha256, recipe_sha256=digest)
    wrong = {**approved, "pins": [{**approved["pins"][0], "version": "1.7.3", "sha256": "f" * 64}]}

    class DockerForbidden:
        def __getattr__(self, name):
            raise AssertionError("本探针禁止 Docker: " + name)

    result = module.build_one(DockerForbidden(), out=scratch / "wrong_recipe", public=public, grading=grading,
                              tag_prefix="review", skip_pull=True, timeouts={"pull": 1, "build": 1, "check": 1},
                              repo_root=ROOT, revisions=trusted.revisions.get(ENV_IID, ()), env_entry=wrong)
    check("R1_build_rejects_wrong_content_before_Docker", not result["ok"] and result["failures"][0].startswith("env_recipe_not_approved"),
          failures=result["failures"])


def main() -> None:
    trusted = load_trusted_r2e_ingest_outputs(ROOT)
    public = next(p for p in trusted.result.public_bundles if p.instance_id == IID)
    grading = next(g for g in trusted.result.grading_bundles if g.instance_id == IID)
    existing_evidence(grading)
    with tempfile.TemporaryDirectory(prefix="probe_scratch_", dir=HERE) as temp:
        scratch = Path(temp)
        binding_probe(trusted, scratch)
        asyncio.run(frozen_binary_probe(public, grading, scratch))
    result = {"scope": "CPU-only：原始证据校验、R1/O1 纯函数/构建前拒绝、真实本机哨兵文件冻结导出与字节重放；无原生编译/容器/网络。", "checks": checks}
    (HERE / "probe_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": len(checks), "failed": 0, "result": str((HERE / "probe_result.json").relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
