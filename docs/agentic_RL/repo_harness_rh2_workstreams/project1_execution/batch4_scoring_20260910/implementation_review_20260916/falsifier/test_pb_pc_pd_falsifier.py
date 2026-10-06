"""独立 CPU 反例；仅本机临时树与既有 FakeDocker，不启动容器/网络/模型。

从仓库根运行：
  PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python -m pytest -q -s -p no:cacheprovider \
    docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/implementation_review_20260916/falsifier/test_pb_pc_pd_falsifier.py

断言是审查时观察到的当前行为，不表示错误行为是验收目标。
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/grading"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from grading_fixtures import FakeDocker, make_fixture_spec
from test_w3a_formal_grading_freeze import _formal_chain, make_barrier
from test_slime_generate import FakeRolloutDocker, _Args, SAMPLING_PARAMS
from test_w1b_delivery_face import _resolve, _decide
from repoharness2.adapters.slime import patch_exporter
from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest
from repoharness2.adapters.slime.patch_exporter import export_frozen_patch
from repoharness2.adapters.slime.generate import FatalExecutionInfrastructureError
from repoharness2.contracts.baseline_manifest import BASELINE_MANIFEST_POLICY_V2
from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest
from repoharness2.contracts.scoring_projection import classify_frozen_patch
from repoharness2.grading.manager import ExecResult, FrozenDeltaSource, GradingManagerConfig, HygieneRules, SWEGradingManager
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection

BASE = "a" * 40


def shell(script: str, input_bytes: bytes | None = None) -> ExecResult:
    result = subprocess.run(["bash", "-c", script], input=input_bytes, capture_output=True)
    return ExecResult(result.returncode, result.stdout.decode(), result.stderr.decode())


class LocalWorkspace:
    def __init__(self, tree: Path):
        self.tree = tree

    async def run_bash(self, script: str) -> ExecResult:
        return shell(script.replace("/testbed", str(self.tree)))


class RealApplyFakeDocker(FakeDocker):
    """只把 census 和已验证临时树的冻结写入脚本交给真实 bash，其余容器交互仍为替身。"""
    def __init__(self, tree: Path):
        super().__init__(base_commit=BASE, image_present=True)
        self.tree = tree
        self.executed_apply = []

    async def __call__(self, *args: str, input_bytes: bytes | None = None):
        if args[0] == "exec":
            script = args[-1]
            if "find ." in script and "sha256sum" in script:
                assert "/testbed" in script
                return shell(script.replace("/testbed", str(self.tree)))
            if script.startswith("cd ") and any(x in script for x in ("add_target_exists:", "rm -f ./", "rm -f './")):
                assert "/testbed" in script
                self.executed_apply.append(script)
                return shell(script.replace("/testbed", str(self.tree)), input_bytes)
        return await super().__call__(*args, input_bytes=input_bytes)


@pytest.mark.asyncio
@pytest.mark.parametrize("prior_cache_dir", [False, True])
async def test_pc_cache_named_regular_add_with_and_without_prior_cache_dir(tmp_path, prior_cache_dir):
    tree = tmp_path / "tree"
    tree.mkdir()
    cache = tree / ".pytest_cache"
    if prior_cache_dir:
        cache.mkdir()
        (cache / "old").write_text("cache\n")
    base_counts = {}
    baseline = await generate_baseline_manifest(
        LocalWorkspace(tree), task_id="swe_gym_lite::probe", workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64, runtime_image_digest="sha256:" + "1" * 64,
        materialized_head=BASE, task_base_commit=BASE, policy=BASELINE_MANIFEST_POLICY_V2,
        omitted_sink=base_counts,
    )
    if prior_cache_dir:
        shutil.rmtree(cache)
    cache.write_text("ordinary answer file\n")
    artifact = await export_frozen_patch(LocalWorkspace(tree), baseline, rollout_execution_id="exec", physical_attempt_id="exec#p1-aaaa")
    assert [(e.path, e.operation, e.object_type) for e in artifact.entries] == [(".pytest_cache", "add", "regular")]
    hygiene, _ = classify_frozen_patch(artifact, baseline)
    assert hygiene.verdict == "projectable"
    spec = dataclasses.replace(
        make_fixture_spec(BASE, "fake-image:v1", checkout_mode="image_embedded", task_id=baseline.task_id),
        hygiene=HygieneRules(test_files=(), test_globs=(), forbidden_globs=()),
    )
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert split.unsupported_shape_reasons == ()
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection,
                               frozen_patch_digest=compute_frozen_patch_digest(artifact))
    # fresh grader 恢复最初的真实树；与 baseline 身份完全一致。
    cache.unlink()
    if prior_cache_dir:
        cache.mkdir()
        (cache / "old").write_text("cache\n")
    docker = RealApplyFakeDocker(tree)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    report = await manager.grade(trajectory_id="cache-type-probe", workspace=None, spec=spec, frozen_delta=source)
    assert len(docker.executed_apply) == 1
    observation = {
        "case": "existing_cache_dir_to_regular" if prior_cache_dir else "absent_to_regular",
        "baseline_omitted": base_counts, "exported": [(e.path, e.operation) for e in artifact.entries],
        "classification": hygiene.verdict, "projection_reasons": list(split.unsupported_shape_reasons),
        "report": {k: getattr(report, k) for k in ("outcome", "failure_category", "reward", "infra_failure_detail")},
    }
    print(json.dumps(observation, ensure_ascii=False))
    if prior_cache_dir:
        assert report.failure_category == "infra_failure" and report.reward is None
        assert "add_target_exists" in report.infra_failure_detail
    else:
        assert report.outcome == "resolved" and cache.read_text() == "ordinary answer file\n"


@pytest.mark.asyncio
async def test_pd_regular_file_to_directory_applies_real_shell(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    config = tree / "config"
    config.write_text("old\n")
    baseline = await generate_baseline_manifest(
        LocalWorkspace(tree), task_id="swe_gym_lite::probe", workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64, runtime_image_digest="sha256:" + "1" * 64,
        materialized_head=BASE, task_base_commit=BASE, policy=BASELINE_MANIFEST_POLICY_V2,
    )
    config.unlink()
    config.mkdir()
    (config / "default.json").write_text("{}\n")
    artifact = await export_frozen_patch(LocalWorkspace(tree), baseline, rollout_execution_id="exec", physical_attempt_id="exec#p1-aaaa")
    hygiene, _ = classify_frozen_patch(artifact, baseline)
    assert hygiene.verdict == "projectable"
    spec = dataclasses.replace(
        make_fixture_spec(BASE, "fake-image:v1", checkout_mode="image_embedded", task_id=baseline.task_id),
        hygiene=HygieneRules(test_files=(), test_globs=(), forbidden_globs=()),
    )
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert split.unsupported_shape_reasons == ()
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection,
                               frozen_patch_digest=compute_frozen_patch_digest(artifact))
    shutil.rmtree(config)
    config.write_text("old\n")
    docker = RealApplyFakeDocker(tree)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    report = await manager.grade(trajectory_id="file-to-dir-probe", workspace=None, spec=spec, frozen_delta=source)
    assert report.outcome == "resolved" and report.patch_hygiene.replayed_on_clean_checkout
    assert len(docker.executed_apply) == 2 and (config / "default.json").read_text() == "{}\n"
    print(json.dumps({"case": "file_to_dir_real_apply", "exported": [(e.path, e.operation) for e in artifact.entries],
                      "apply_commands": len(docker.executed_apply), "final_content": (config / "default.json").read_text(),
                      "outcome": report.outcome}, ensure_ascii=False))


class BaselineDocker(FakeRolloutDocker):
    def __init__(self, baseline_regular):
        super().__init__(exec_after_rm_raises=True)
        self.baseline_regular = baseline_regular

    async def __call__(self, *args: str, input_bytes: bytes | None = None):
        if args[0] == "exec" and "find ." in args[-1] and "sha256sum" in args[-1]:
            census = "".join(f"regular\t100644\t{hashlib.sha256(data).hexdigest()}\t{path}\n" for path, data in sorted(self.baseline_regular.items()))
            return ExecResult(0, census, "")
        return await super().__call__(*args, input_bytes=input_bytes)


@pytest.mark.asyncio
@pytest.mark.parametrize("ancestor", ["config", "config'quote"])
async def test_pd_reverse_shape_receipt_and_drop_group(ancestor):
    child = ancestor + "/default.json"
    docker = BaselineDocker({child: b"old\n"})
    chain = _formal_chain(barrier=make_barrier({ancestor: b"new\n"}), docker=docker)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (receipt,) = chain.finalization.receipts
    assert audit.lease.container_id in docker.removed and chain.grading.calls == []
    (leaf,) = delivered
    disposition = _decide(_resolve(leaf))
    assert disposition.verdict == "DROP_GROUP"
    assert disposition.reason_code == "unsafe_artifact_permanent_rejection"
    evidence = receipt.rejection_evidence.model_dump(mode="json")
    print(json.dumps({"case": "reverse_shape_receipt", "ancestor": ancestor, "child": child,
                      "receipt": evidence, "unsafe_reasons": audit.unsafe_artifact_reasons,
                      "outcome_evidence": audit.outcome_v2["evidence_refs"],
                      "group_disposition": disposition.verdict}, ensure_ascii=False))
    assert evidence["object_type"] == "prefix_conflict"
    if "'" in ancestor:
        assert evidence["object_path"] is None
    else:
        assert evidence["object_path"] == child


@pytest.mark.asyncio
async def test_pd_internal_sorting_error_stays_run_fatal(monkeypatch):
    original = patch_exporter.diff_census_against_baseline
    monkeypatch.setattr(patch_exporter, "diff_census_against_baseline", lambda *args: list(reversed(original(*args))))
    chain = _formal_chain(barrier=make_barrier({"a.py": b"a\n", "b.py": b"b\n"}))
    with pytest.raises(FatalExecutionInfrastructureError) as caught:
        await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[0]
    (receipt,) = chain.finalization.receipts
    assert receipt.attempt_disposition == "fatal_run_halt"
    assert audit.rejection_evidence is None
    print(json.dumps({"case": "internal_sorting_error", "exception": caught.value.reason_code,
                      "receipt_disposition": receipt.attempt_disposition}, ensure_ascii=False))
