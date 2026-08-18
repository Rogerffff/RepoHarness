"""B4 验收：grade(frozen_delta=...) —— grader 不回读 rollout workspace，
直接应用冻结 delta，application 失败 = contract failure（非模型负样本）。
"""

from __future__ import annotations

import base64
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grading_fixtures import FakeDocker, make_fixture_spec  # noqa: E402
from test_manager_unit import BASE, make_manager  # noqa: E402

from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_V1,
    BaselineEntry,
    BaselineWorkspaceManifestV1,
    compute_policy_digest,
)
from repoharness2.contracts.frozen_patch import (  # noqa: E402
    FrozenPatchArtifactV1,
    PatchEntry,
)
from repoharness2.contracts.scoring_projection import (  # noqa: E402
    ScoringProjectionArtifactV1,
)
from repoharness2.grading.manager import FrozenDeltaSource  # noqa: E402


def make_spec(**overrides):
    return make_fixture_spec(BASE, "rh2/fake-image:test",
                             checkout_mode="image_embedded", **overrides)


def _b64(data: bytes):
    return (base64.b64encode(data).decode(),
            "sha256:" + hashlib.sha256(data).hexdigest())


def _delta(entries, baseline_entries=()):
    baseline = BaselineWorkspaceManifestV1(
        task_id="t1", workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40, task_base_commit="b" * 40,
        policy=BASELINE_MANIFEST_POLICY_V1,
        policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        entries=tuple(baseline_entries),
    )
    from repoharness2.contracts.baseline_manifest import (
        compute_baseline_manifest_digest,
    )

    art = FrozenPatchArtifactV1(
        task_id="t1", rollout_execution_id="exec_1",
        physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest=compute_baseline_manifest_digest(baseline),
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head="a" * 40,
        entries=tuple(entries), excluded_pathset_changed=False,
    )
    from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest

    proj = ScoringProjectionArtifactV1(
        frozen_patch_digest=compute_frozen_patch_digest(art),
        rollout_execution_id="exec_1", physical_attempt_id="exec_1#p1-aaaa",
        included_entry_paths=tuple(sorted(e.path for e in art.entries)),
    )
    return FrozenDeltaSource(
        frozen_patch=art, baseline_manifest=baseline, projection=proj,
        frozen_patch_digest=proj.frozen_patch_digest,
    )


class _PoisonWorkspace:
    """B4 同一性负测试：grader 若回读 workspace 立即炸。"""

    async def run_bash(self, script):
        raise AssertionError("grader 不得回读 rollout workspace（B4/A-prime 1）")


async def test_frozen_delta_grades_without_workspace():
    """核心验收：workspace=None + frozen_delta → 直接应用 + 正常评分；
    应用命令落在容器 exec（写/删/链/chmod），全程无 git apply。"""

    b64, dg = _b64(b"print('fixed')\n")
    tb64, tdg = _b64(b"src/target.py")
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    delta = _delta([
        PatchEntry(path="del.py", operation="delete", object_type="regular"),
        PatchEntry(path="run.sh", operation="add", object_type="regular",
                   mode="100755", content_b64=b64, content_digest=dg),
        PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                   mode="100644", content_b64=b64, content_digest=dg),
        PatchEntry(path="src/link", operation="add", object_type="symlink",
                   mode="120000", content_b64=tb64, content_digest=tdg),
    ], baseline_entries=[BaselineEntry(
        path="del.py", object_type="regular", mode="100644",
        content_digest="sha256:" + "d" * 64)])
    # pre-image：FakeDocker 对 sha256sum 返回什么？——delete 有 baseline
    # entry，需 pre-image 命中：让 fake 返回该 digest
    fake.sha256_by_path = {"del.py": "d" * 64}
    report = await manager.grade(
        trajectory_id="traj_fd", workspace=None, spec=make_spec(),
        frozen_delta=delta,
    )
    assert report.outcome == "resolved"
    assert report.patch_hygiene.cleaned_patch_digest == delta.frozen_patch_digest
    scripts = [c[-1] for c in fake.calls if c[0] == "exec"]
    joined = "\n".join(s for s in scripts if isinstance(s, str))
    assert "git apply" not in joined  # FA 路径无 git 应用
    assert "rm -f 'del.py'" in joined
    assert "chmod 755 'run.sh'" in joined
    assert "ln -s 'src/target.py' 'src/link'" in joined


async def test_frozen_delta_never_touches_workspace_object():
    """同一性负测试：毒 workspace 传入也不炸（None 才是生产形态，此测
    双保险——即便误传对象也零访问）。"""

    b64, dg = _b64(b"x")
    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_p", workspace=_PoisonWorkspace(), spec=make_spec(),
        frozen_delta=_delta([PatchEntry(
            path="a.py", operation="add", object_type="regular",
            mode="100644", content_b64=b64, content_digest=dg)]),
    )
    assert report.outcome in ("resolved", "unresolved")  # 毒对象未被触碰


async def test_preimage_mismatch_is_contract_failure_not_reward_zero():
    """A-prime 失败表：matching baseline 上 apply/前置校验失败 →
    failed_to_grade（reward=None），绝不 patch_apply_failed/reward 0。"""

    fake = FakeDocker(base_commit=BASE)
    fake.sha256_by_path = {"mod.py": "f" * 64}  # 现值 ≠ baseline digest
    delta = _delta(
        [PatchEntry(path="mod.py", operation="delete", object_type="regular")],
        baseline_entries=[BaselineEntry(
            path="mod.py", object_type="regular", mode="100644",
            content_digest="sha256:" + "0" * 64)],
    )
    report = await make_manager(fake).grade(
        trajectory_id="traj_pre", workspace=None, spec=make_spec(),
        frozen_delta=delta,
    )
    assert report.outcome == "failed_to_grade"
    assert report.reward is None
    assert "baseline_preimage_mismatch" in (report.infra_failure_detail or "")


async def test_missing_workspace_without_delta_is_infra():
    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_nw", workspace=None, spec=make_spec(),
    )
    assert report.outcome == "failed_to_grade"
    assert "workspace_missing_without_frozen_delta" in (report.infra_failure_detail or "")


def test_test_execution_timeout_category_d1a():
    """D1a 第 2 条落地（S2 协调后）：test_execution_timeout = 模型负样本
    （unresolved + reward 0 合法）；infra 族语义不受影响。"""

    from datetime import datetime, timezone

    from repoharness2.contracts.grading import GradingReport

    from repoharness2.contracts.grading import PatchHygieneResult

    common = dict(
        report_id="rpt_x", trajectory_id="t", task_id="k",
        grader_name="swebench_official", grader_version="v1",
        graded_at_utc=datetime.now(timezone.utc),
        patch_hygiene=PatchHygieneResult(
            verdict="clean", cleaned_patch_digest="sha256:" + "a" * 64,
            test_files_modified=False, forbidden_path_touched=False,
            replayed_on_clean_checkout=True,
        ),
    )
    rep = GradingReport(**common, outcome="unresolved",
                        failure_category="test_execution_timeout", reward=0.0)
    assert rep.reward == 0.0
    with pytest.raises(ValueError):  # 二值锁：不得非 0
        GradingReport(**common, outcome="unresolved",
                      failure_category="test_execution_timeout", reward=0.5)

