"""B4 验收：grade(frozen_delta=...) —— grader 不回读 rollout workspace；
apply 前 exact-baseline 重建比对（T0 第 2 条）；task-aware hygiene 筛查
（S1 镜像）；直接应用先 unlink 再写（P0-2）；application 失败 = contract
failure（非模型负样本）。真实文件系统测试见文件末段（不依赖 FakeDocker
命令字符串）。
"""

from __future__ import annotations

import base64
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from grading_fixtures import (  # noqa: E402
    FIXTURE_INSTANCE_ID,
    FakeDocker,
    make_fixture_spec,
)
from test_manager_unit import BASE, make_manager  # noqa: E402

from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_V1,
    BaselineEntry,
    BaselineWorkspaceManifestV1,
    compute_baseline_manifest_digest,
    compute_policy_digest,
)
from repoharness2.contracts.frozen_patch import (  # noqa: E402
    FrozenPatchArtifactV1,
    PatchEntry,
    compute_frozen_patch_digest,
)
from repoharness2.contracts.scoring_projection import (  # noqa: E402
    ScoringProjectionArtifactV1,
)
from repoharness2.grading.manager import (  # noqa: E402
    BaselineIntegrityError,
    FrozenDeltaSource,
    HygieneRules,
    build_delta_delete_command,
    build_delta_symlink_command,
    build_delta_write_command,
    compute_applied_entry_set_digest,
    screen_frozen_entries,
)


def make_spec(**overrides):
    return make_fixture_spec(BASE, "rh2/fake-image:test",
                             checkout_mode="image_embedded", **overrides)


def _b64(data: bytes):
    return (base64.b64encode(data).decode(),
            "sha256:" + hashlib.sha256(data).hexdigest())


def _census_line(entry: BaselineEntry) -> str:
    sha = (entry.content_digest or entry.symlink_target_digest).removeprefix("sha256:")
    return f"{entry.object_type}\t{entry.mode}\t{sha}\t{entry.path}"


def _delta(entries, baseline_entries=(), **baseline_overrides):
    """构造与 fixture spec **绑定一致** 的 FrozenDeltaSource：
    task_id/workdir/base/head 全部对齐（P0-1 之后不一致会直接 run-halt）。"""

    base_fields = dict(
        task_id=FIXTURE_INSTANCE_ID, workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64,
        materialized_head=BASE, task_base_commit=BASE,
        policy=BASELINE_MANIFEST_POLICY_V1,
        policy_digest=compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        entries=tuple(baseline_entries),
    )
    base_fields.update(baseline_overrides)
    baseline = BaselineWorkspaceManifestV1(**base_fields)
    art = FrozenPatchArtifactV1(
        task_id=baseline.task_id, rollout_execution_id="exec_1",
        physical_attempt_id="exec_1#p1-aaaa",
        baseline_manifest_digest=compute_baseline_manifest_digest(baseline),
        public_bundle_digest=baseline.public_bundle_digest,
        runtime_image_digest=baseline.runtime_image_digest,
        materialized_head=baseline.materialized_head,
        entries=tuple(entries), excluded_pathset_changed=False,
    )
    proj = ScoringProjectionArtifactV1(
        frozen_patch_digest=compute_frozen_patch_digest(art),
        rollout_execution_id="exec_1", physical_attempt_id="exec_1#p1-aaaa",
        included_entry_paths=tuple(sorted(e.path for e in art.entries)),
    )
    return FrozenDeltaSource(
        frozen_patch=art, baseline_manifest=baseline, projection=proj,
        frozen_patch_digest=proj.frozen_patch_digest,
    )


def _fake_with_baseline(delta, **kwargs) -> FakeDocker:
    """census 罐头 = baseline entries 原样（重建比对通过的对照面）。"""

    fake = FakeDocker(base_commit=BASE, **kwargs)
    fake.census_output = "".join(
        _census_line(e) + "\n" for e in delta.baseline_manifest.entries
    )
    return fake


class _PoisonWorkspace:
    """B4 同一性负测试：grader 若回读 workspace 立即炸。"""

    async def run_bash(self, script):
        raise AssertionError("grader 不得回读 rollout workspace（B4/A-prime 1）")


# ---------------------------------------------------------------- FA 主链路
async def test_frozen_delta_grades_without_workspace():
    """核心验收：workspace=None + frozen_delta → exact-baseline 重建比对
    通过 → 直接应用（--、先 unlink）→ 正常评分；全程无 git apply。"""

    b64, dg = _b64(b"print('fixed')\n")
    tb64, tdg = _b64(b"src/target.py")
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
    fake = _fake_with_baseline(delta)
    report = await make_manager(fake).grade(
        trajectory_id="traj_fd", workspace=None, spec=make_spec(),
        frozen_delta=delta,
    )
    assert report.outcome == "resolved"
    assert report.patch_hygiene.digest_kind == "applied_entry_set"
    assert report.patch_hygiene.cleaned_patch_digest == (
        compute_applied_entry_set_digest(list(delta.frozen_patch.entries))
    )
    assert report.patch_hygiene.replayed_on_clean_checkout is True
    scripts = [c[-1] for c in fake.calls if c[0] == "exec"]
    joined = "\n".join(s for s in scripts if isinstance(s, str))
    assert "git apply" not in joined  # FA 路径无 git 应用
    assert "rm -f './del.py'" in joined
    assert "chmod 755 './run.sh'" in joined
    assert "ln -s -- 'src/target.py' './src/link'" in joined
    assert "-prune" in joined  # census 重建确实执行了


async def test_frozen_delta_never_touches_workspace_object():
    """同一性负测试：毒 workspace 传入也不炸（None 才是生产形态，此测
    双保险——即便误传对象也零访问）。"""

    b64, dg = _b64(b"x")
    delta = _delta([PatchEntry(
        path="a.py", operation="add", object_type="regular",
        mode="100644", content_b64=b64, content_digest=dg)])
    report = await make_manager(_fake_with_baseline(delta)).grade(
        trajectory_id="traj_p", workspace=_PoisonWorkspace(), spec=make_spec(),
        frozen_delta=delta,
    )
    assert report.outcome in ("resolved", "unresolved")  # 毒对象未被触碰


async def test_missing_workspace_without_delta_is_infra():
    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_nw", workspace=None, spec=make_spec(),
    )
    assert report.outcome == "failed_to_grade"
    assert "workspace_missing_without_frozen_delta" in (report.infra_failure_detail or "")


# ------------------------------------------------- P0-1 exact-baseline 校验
async def test_spec_binding_mismatch_is_run_halt_not_member_loss():
    """codex B4-P0-1 探针闭合：delta 的 task 与 spec 不一致时**不再**评分
    成功，也不转 failed_to_grade——BaselineIntegrityError 穿透（run-halt）。"""

    b64, dg = _b64(b"x")
    delta = _delta(
        [PatchEntry(path="a.py", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)],
        task_id="some-other-task",  # baseline/artifact 一致但与 spec 不符
    )
    fake = _fake_with_baseline(delta)
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(fake).grade(
            trajectory_id="traj_bind", workspace=None, spec=make_spec(),
            frozen_delta=delta,
        )
    assert exc_info.value.reason_code == "grading_spec_binding_mismatch"
    # fail-fast：起容器之前就拦下（没有 run 调用）
    assert not any(c[0] == "run" for c in fake.calls)


async def test_source_internal_binding_mismatch_detected():
    """source 内部分家（projection 锚被换）→ frozen_delta_binding_mismatch。"""

    b64, dg = _b64(b"x")
    good = _delta([PatchEntry(path="a.py", operation="add", object_type="regular",
                              mode="100644", content_b64=b64, content_digest=dg)])
    tampered = FrozenDeltaSource(
        frozen_patch=good.frozen_patch,
        baseline_manifest=good.baseline_manifest,
        projection=good.projection.model_copy(
            update={"frozen_patch_digest": "sha256:" + "9" * 64}
        ),
        frozen_patch_digest=good.frozen_patch_digest,
    )
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(_fake_with_baseline(good)).grade(
            trajectory_id="traj_tamper", workspace=None, spec=make_spec(),
            frozen_delta=tampered,
        )
    assert exc_info.value.reason_code == "frozen_delta_binding_mismatch"


async def test_baseline_rebuild_digest_mismatch_is_run_halt():
    """fresh checkout census ≠ baseline（多出一个文件）→
    baseline_digest_mismatch run-halt；绝不 failed_to_grade 静默损耗。"""

    b64, dg = _b64(b"x")
    delta = _delta([PatchEntry(
        path="a.py", operation="add", object_type="regular",
        mode="100644", content_b64=b64, content_digest=dg)])
    fake = _fake_with_baseline(delta)
    fake.census_output += "regular\t100644\t" + "f" * 64 + "\tdrifted.txt\n"
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(fake).grade(
            trajectory_id="traj_drift", workspace=None, spec=make_spec(),
            frozen_delta=delta,
        )
    assert exc_info.value.reason_code == "baseline_digest_mismatch"


async def test_baseline_rebuild_census_failure_is_run_halt():
    b64, dg = _b64(b"x")
    delta = _delta([PatchEntry(
        path="a.py", operation="add", object_type="regular",
        mode="100644", content_b64=b64, content_digest=dg)])
    fake = _fake_with_baseline(delta)
    fake.census_exit_code = 7
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(fake).grade(
            trajectory_id="traj_cf", workspace=None, spec=make_spec(),
            frozen_delta=delta,
        )
    assert exc_info.value.reason_code == "baseline_rebuild_census_failed"


# ------------------------------------------------- P1 task-aware hygiene
def test_screen_frozen_entries_priorities():
    rules = HygieneRules(test_globs=("tests/*",), forbidden_globs=("grader/*",))

    def entry(path):
        b64, dg = _b64(b"x")
        return PatchEntry(path=path, operation="add", object_type="regular",
                          mode="100644", content_b64=b64, content_digest=dg)

    plan = screen_frozen_entries(
        [entry("src/ok.py"), entry("tests/test_evil.py"), entry("grader/conf")],
        rules,
    )
    assert plan.applied_paths == ("src/ok.py",)
    assert plan.stripped_test_paths == ("tests/test_evil.py",)
    assert plan.forbidden_paths == ("grader/conf",)
    assert plan.verdict == "rejected_test_tampering"  # 篡改 > 污染
    only_forbidden = screen_frozen_entries([entry("grader/conf")], rules)
    assert only_forbidden.verdict == "rejected_forbidden_contamination"
    clean = screen_frozen_entries([entry("src/ok.py")], rules)
    assert clean.verdict == "clean"
    # digest = 实际应用子集（剔除后与纯净单文件集相等，证明其为子集 digest）
    assert plan.applied_entry_set_digest == clean.applied_entry_set_digest


async def test_projection_including_control_plane_entry_is_binding_mismatch():
    """W3a（D2-3，T1 oracle 改动，原 test_unscreened_tampering_entry_is_infra_belt）：
    控制面路径（tests/*）不再是 unsafe，也不是"漏筛 → infra 成员损耗"——它根本不该出现在
    投影里。projection 夹带了控制面 entry ⇒ 与 grader 按同一 HygieneRules 独立重算的
    candidate_solution 路径集不等 ⇒ frozen_delta_binding_mismatch run-halt；grader 容器一个
    都不起、eval 一次都不跑。"""

    b64, dg = _b64(b"broken oracle")
    delta = _delta([
        PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                   mode="100644", content_b64=b64, content_digest=dg),
        PatchEntry(path="tests/test_hidden_behavior.py", operation="add",
                   object_type="regular", mode="100644",
                   content_b64=b64, content_digest=dg),
    ])  # _delta 的 projection = 全路径集（含控制面 entry）= 夹带
    fake = _fake_with_baseline(delta)
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(fake).grade(
            trajectory_id="traj_tamp", workspace=None, spec=make_spec(),
            frozen_delta=delta,
        )
    assert exc_info.value.reason_code == "frozen_delta_binding_mismatch"
    assert "candidate_solution" in str(exc_info.value)
    assert not any(c[0] == "run" for c in fake.calls)  # 容器都没起


async def test_projection_excluding_control_plane_entry_grades_candidate_only():
    """W3a（D2-3 正例）：artifact 同时含 src/fix.py 与 tests/test_x.py，投影只含 src/fix.py
    （= 可信评分投影的 candidate 集）→ 正常评分；只重放 src/fix.py，测试文件一个字节都不写；
    hygiene 描述的是已重放子集：clean、digest = 该子集 digest。"""

    b64, dg = _b64(b"print('fixed')\n")
    full = _delta([
        PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                   mode="100644", content_b64=b64, content_digest=dg),
        PatchEntry(path="tests/test_x.py", operation="add", object_type="regular",
                   mode="100644", content_b64=b64, content_digest=dg),
    ])
    trusted = FrozenDeltaSource(
        frozen_patch=full.frozen_patch,
        baseline_manifest=full.baseline_manifest,
        projection=full.projection.model_copy(update={"included_entry_paths": ("src/fix.py",)}),
        frozen_patch_digest=full.frozen_patch_digest,
    )
    fake = _fake_with_baseline(trusted)
    report = await make_manager(fake).grade(
        trajectory_id="traj_trusted", workspace=None, spec=make_spec(),
        frozen_delta=trusted,
    )
    assert report.outcome == "resolved" and report.reward == 1.0
    assert report.patch_hygiene.verdict == "clean"
    assert report.patch_hygiene.test_files_modified is False
    assert report.patch_hygiene.cleaned_patch_digest == compute_applied_entry_set_digest(
        [e for e in full.frozen_patch.entries if e.path == "src/fix.py"]
    )
    scripts = [c[-1] for c in fake.calls if c[0] == "exec" and isinstance(c[-1], str)]
    joined = "\n".join(scripts)
    assert "'./src/fix.py'" in joined
    assert "test_x.py" not in joined  # 控制面 entry 未重放


# ------------------------------------------------- P0 官方镜像 overlay HEAD
OVERLAY = "b" * 40  # 官方镜像构建叠加 commit（HEAD^ == base_commit 形态）


async def test_official_overlay_head_image_grades_normally():
    """codex B4 复核 P0 正例：materialized_head = overlay commit ≠
    task_base_commit（官方 SWE 镜像常态，S0-7 实证），rollout 与 grader
    HEAD 一致 → 正常评分，不得 run-halt。"""

    b64, dg = _b64(b"fix")
    delta = _delta(
        [PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)],
        materialized_head=OVERLAY,
    )
    fake = _fake_with_baseline(delta)
    fake.head_commit = OVERLAY  # grader checkout 与 rollout 同一 overlay HEAD
    report = await make_manager(fake).grade(
        trajectory_id="traj_ov", workspace=None, spec=make_spec(),
        frozen_delta=delta,
    )
    assert report.outcome == "resolved"


async def test_grader_head_differs_from_materialized_head_is_run_halt():
    """P0 负例：grader 实际 HEAD ≠ baseline.materialized_head（评分树与
    模型开工树不是同一 commit）→ grading_head_mismatch run-halt。"""

    b64, dg = _b64(b"fix")
    delta = _delta(
        [PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)],
        materialized_head=OVERLAY,
    )
    fake = _fake_with_baseline(delta)  # 探针默认 HEAD=BASE ≠ OVERLAY
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(fake).grade(
            trajectory_id="traj_hm", workspace=None, spec=make_spec(),
            frozen_delta=delta,
        )
    assert exc_info.value.reason_code == "grading_head_mismatch"


# ------------------------------------------------- P1-2 三对象完整对账
async def test_projection_omitting_solution_entry_is_run_halt():
    """codex 反例 (a) 的 W3a 形态（T1 oracle 改动）：raw delta 改了两个源码文件、projection
    隐去其中一个 **solution** entry → 与重算的 candidate 集不等 → run-halt（拿不完整改动评分
    不许发生）。旧版本用"隐去测试 entry"作反例——D2-3 起测试 entry 本来就该被排除，隐去它
    不再是矛盾，见 test_projection_excluding_control_plane_entry_grades_candidate_only。"""

    b64, dg = _b64(b"x")
    good = _delta([
        PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                   mode="100644", content_b64=b64, content_digest=dg),
        PatchEntry(path="src/other.py", operation="add",
                   object_type="regular", mode="100644",
                   content_b64=b64, content_digest=dg),
    ])
    hiding = FrozenDeltaSource(
        frozen_patch=good.frozen_patch,
        baseline_manifest=good.baseline_manifest,
        projection=good.projection.model_copy(
            update={"included_entry_paths": ("src/fix.py",)}  # 隐去 solution entry
        ),
        frozen_patch_digest=good.frozen_patch_digest,
    )
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(_fake_with_baseline(good)).grade(
            trajectory_id="traj_hide", workspace=None, spec=make_spec(),
            frozen_delta=hiding,
        )
    assert exc_info.value.reason_code == "frozen_delta_binding_mismatch"
    assert "路径集" in str(exc_info.value)


async def test_projection_with_unknown_path_is_run_halt():
    """投影引用 artifact 里不存在的路径 = 悬空引用（同样 run-halt，单独的错误文案）。"""

    b64, dg = _b64(b"x")
    good = _delta([PatchEntry(path="src/fix.py", operation="add", object_type="regular",
                              mode="100644", content_b64=b64, content_digest=dg)])
    dangling = FrozenDeltaSource(
        frozen_patch=good.frozen_patch, baseline_manifest=good.baseline_manifest,
        projection=good.projection.model_copy(
            update={"included_entry_paths": ("src/fix.py", "src/ghost.py")}
        ),
        frozen_patch_digest=good.frozen_patch_digest,
    )
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(_fake_with_baseline(good)).grade(
            trajectory_id="traj_dangling", workspace=None, spec=make_spec(),
            frozen_delta=dangling,
        )
    assert exc_info.value.reason_code == "frozen_delta_binding_mismatch"
    assert "不存在" in str(exc_info.value)


async def test_delete_of_path_absent_from_baseline_is_run_halt():
    """codex 反例 (b)：删除 baseline 不存在的路径 → 语义矛盾 delta，
    prestate 对账拒绝（不再被 rm -f 幂等静默吞掉后 resolved）。"""

    delta = _delta([PatchEntry(
        path="ghost.py", operation="delete", object_type="regular")])
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(_fake_with_baseline(delta)).grade(
            trajectory_id="traj_ghost", workspace=None, spec=make_spec(),
            frozen_delta=delta,
        )
    assert exc_info.value.reason_code == "frozen_delta_prestate_mismatch"


async def test_delete_object_type_mismatch_and_add_collision_prestate():
    """delete 类型必须与 baseline 一致；add 路径必须原先不存在。"""

    b64, dg = _b64(b"x")
    type_mismatch = _delta(
        [PatchEntry(path="link", operation="delete", object_type="regular")],
        baseline_entries=[BaselineEntry(
            path="link", object_type="symlink", mode="120000",
            symlink_target_digest="sha256:" + "c" * 64)],
    )
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(_fake_with_baseline(type_mismatch)).grade(
            trajectory_id="traj_tm", workspace=None, spec=make_spec(),
            frozen_delta=type_mismatch,
        )
    assert exc_info.value.reason_code == "frozen_delta_prestate_mismatch"
    add_collision = _delta(
        [PatchEntry(path="exists.py", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)],
        baseline_entries=[BaselineEntry(
            path="exists.py", object_type="regular", mode="100644",
            content_digest="sha256:" + "d" * 64)],
    )
    with pytest.raises(BaselineIntegrityError) as exc_info:
        await make_manager(_fake_with_baseline(add_collision)).grade(
            trajectory_id="traj_ac", workspace=None, spec=make_spec(),
            frozen_delta=add_collision,
        )
    assert exc_info.value.reason_code == "frozen_delta_prestate_mismatch"


# ------------------------------------------------- D1a 契约
def test_test_execution_timeout_category_d1a():
    """D1a 第 2 条落地（S2 协调后）：test_execution_timeout = 模型负样本
    （unresolved + reward 0 合法）；infra 族语义不受影响。"""

    from datetime import datetime, timezone

    from repoharness2.contracts.grading import GradingReport, PatchHygieneResult

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


# ------------------------------------------------- 真实文件系统（P0-2）
def _bash(script: str, cwd: Path, input_bytes: bytes | None = None):
    return subprocess.run(
        ["bash", "-c", script], cwd=cwd, input=input_bytes, capture_output=True
    )


def test_realfs_symlink_to_regular_modify_does_not_write_through(tmp_path):
    """codex B4-P0-2 确定性复现的回归钉：baseline `link -> victim`，delta
    把 link 改成 regular——旧实现 `cat > link` 会写穿进 victim；新实现先
    unlink 再写，victim 必须原封不动。"""

    tb = tmp_path / "testbed"
    tb.mkdir()
    (tb / "victim").write_bytes(b"VICTIM ORIGINAL\n")
    (tb / "link").symlink_to("victim")
    cmd = build_delta_write_command(str(tb), "link", mode="100644", operation="modify")
    proc = _bash(cmd, tmp_path, input_bytes=b"model content\n")
    assert proc.returncode == 0, proc.stderr
    assert (tb / "victim").read_bytes() == b"VICTIM ORIGINAL\n"  # 未被写穿
    assert not (tb / "link").is_symlink()
    assert (tb / "link").read_bytes() == b"model content\n"


def test_realfs_delete_symlink_no_follow(tmp_path):
    tb = tmp_path / "testbed"
    tb.mkdir()
    (tb / "victim").write_bytes(b"KEEP\n")
    (tb / "link").symlink_to("victim")
    proc = _bash(build_delta_delete_command(str(tb), "link"), tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert not (tb / "link").exists(follow_symlinks=False)
    assert (tb / "victim").read_bytes() == b"KEEP\n"


def test_realfs_dash_prefixed_path_and_target(tmp_path):
    """`--` 纪律：`-` 开头的路径/target 不被当成命令选项。"""

    tb = tmp_path / "testbed"
    tb.mkdir()
    w = _bash(build_delta_write_command(str(tb), "-dashfile", mode="100755",
                                        operation="add"),
              tmp_path, input_bytes=b"#!/bin/sh\n")
    assert w.returncode == 0, w.stderr
    assert (tb / "-dashfile").read_bytes() == b"#!/bin/sh\n"
    assert (tb / "-dashfile").stat().st_mode & 0o111  # chmod 755 生效
    s = _bash(build_delta_symlink_command(str(tb), "-dashlink", "-dashtarget"),
              tmp_path)
    assert s.returncode == 0, s.stderr
    assert (tb / "-dashlink").readlink() == Path("-dashtarget")
    d = _bash(build_delta_delete_command(str(tb), "-dashfile"), tmp_path)
    assert d.returncode == 0, d.stderr
    assert not (tb / "-dashfile").exists()


def test_realfs_add_collision_guard(tmp_path):
    """add 断言目标原本不存在（census 比对之外的防御双保险）。"""

    tb = tmp_path / "testbed"
    tb.mkdir()
    (tb / "exists.py").write_bytes(b"old")
    proc = _bash(build_delta_write_command(str(tb), "exists.py", mode="100644",
                                           operation="add"),
                 tmp_path, input_bytes=b"new")
    assert proc.returncode == 3
    assert b"add_target_exists" in proc.stderr
    assert (tb / "exists.py").read_bytes() == b"old"  # 未覆盖


def test_realfs_symlink_replaces_existing_symlink(tmp_path):
    """symlink modify：旧链先 unlink，新链不落进旧 target 目录。"""

    tb = tmp_path / "testbed"
    tb.mkdir()
    (tb / "d").mkdir()
    (tb / "link").symlink_to("d")  # 旧链指向目录：裸 ln -s 会在 d/ 里建新链
    proc = _bash(build_delta_symlink_command(str(tb), "link", "elsewhere"), tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (tb / "link").readlink() == Path("elsewhere")
    assert not (tb / "d" / "link").exists(follow_symlinks=False)


# ------------------------------------------------- Falsifier F5 / F6
def test_control_char_paths_rejected_no_digest_collision():
    """Falsifier F5：PatchEntry.path 含 TAB/LF → 构造即拒（碰撞向量关闭）。
    单条 entry 无法再伪造多条 entry 的规范行。"""

    b64, dg = _b64(b"x")
    for bad in ("a\tb", "a\nmodify\tregular", "x\x7f", "d\x01e"):
        with pytest.raises(ValueError, match="控制字符"):
            PatchEntry(path=bad, operation="add", object_type="regular",
                       mode="100644", content_b64=b64, content_digest=dg)
    # 空格仍合法（真实文件名可含空格）
    ok = PatchEntry(path="a b/c d.py", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)
    assert ok.path == "a b/c d.py"


async def test_baseline_symlink_ancestor_apply_refused(tmp_path):
    """Falsifier F6：baseline 祖先目录是软链 → 拒绝应用其下的写入
    （GradingInfraError 成员损耗，不跟随软链写出 testbed）。"""

    b64, dg = _b64(b"payload")
    # 写入 d/x，且 baseline 把 d 记为 symlink（官方镜像逃逸软链场景）
    delta = _delta(
        [PatchEntry(path="d/x", operation="add", object_type="regular",
                    mode="100644", content_b64=b64, content_digest=dg)],
        baseline_entries=[BaselineEntry(
            path="d", object_type="symlink", mode="120000",
            symlink_target_digest="sha256:" + "c" * 64)],
    )
    report = await make_manager(_fake_with_baseline(delta)).grade(
        trajectory_id="traj_f6", workspace=None, spec=make_spec(),
        frozen_delta=delta,
    )
    assert report.outcome == "failed_to_grade"
    assert report.reward is None
    assert "apply_path_ancestor_is_symlink" in (report.infra_failure_detail or "")
