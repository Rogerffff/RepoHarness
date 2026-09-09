"""SWEGradingManager 单测（FakeDocker 注入，无 docker）：归因决策树 + P2/P4/P5/P7/P8/P10。

真容器行为（P1 清扫 / P3 超时 / P6 只读 / P9 断网 / 杀容器注入）见
test_manager_docker.py；这里用桩把控制流逐条钉死。
"""

import asyncio
import subprocess
import sys

import pytest
from grading_fixtures import (
    FAILING_FAKE_LOG,
    FIXTURE_INSTANCE_ID,
    GARBAGE_FAKE_LOG,
    GOOD_PATCH,
    NO_MARKER_FAKE_LOG,
    POLLUTION_SEGMENT,
    TAMPER_SEGMENT,
    FakeDocker,
    FakeWorkspace,
    make_fixture_spec,
)
from pydantic import ValidationError

from repoharness2.contracts import GradingReport
from repoharness2.envpack.bundles import load_bundle_pairs
from repoharness2.envpack.scoring import GRADER_NAME
from repoharness2.grading.manager import (
    ExecResult,
    GradingManagerConfig,
    SWEGradingManager,
    build_swe_grading_spec,
    run_docker,
)

BASE = "a" * 40


def make_manager(fake: FakeDocker, **config_kwargs) -> SWEGradingManager:
    return SWEGradingManager(GradingManagerConfig(**config_kwargs), docker=fake)


def make_spec(image: str = "fake-image:v1", **overrides):
    """FakeDocker 场景统一走 image_embedded 模式（桩不用应答 git clone）。"""

    return make_fixture_spec(BASE, image, checkout_mode="image_embedded", **overrides)


# ---------------------------------------------------------------------------
# 归因决策树（A7 条 6/7）
# ---------------------------------------------------------------------------


async def test_grade_resolved_end_to_end():
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    report = await manager.grade(
        trajectory_id="traj_ok",
        workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_spec(),
        queue_wait_seconds=1.3,
        queue_depth_at_enqueue=2,
        backpressure_triggered=True,
    )
    assert report.outcome == "resolved" and report.reward == 1.0
    assert report.failure_category is None
    assert (report.f2p_pass_count, report.f2p_total_count) == (1, 1)
    assert (report.p2p_fail_count, report.p2p_total_count) == (0, 1)
    assert report.patch_hygiene is not None and report.patch_hygiene.verdict == "clean"
    assert report.patch_hygiene.replayed_on_clean_checkout is True
    assert report.grader_name == GRADER_NAME
    # queue 事实原样进 timing（F5）
    assert report.timings is not None
    assert report.timings.queue_wait_seconds == 1.3
    assert report.timings.queue_depth_at_enqueue == 2
    assert report.timings.backpressure_triggered is True
    assert report.timings.container_peak_memory_mb == 1.0  # FakeDocker 固定 1 MiB
    # 契约对象 JSON 往返（inspect-rh2-artifact 同路径）
    GradingReport.model_validate(report.model_dump(mode="json"))
    # 评分容器 fresh 起、评完即删（P1 记账在 manager 内）
    run_calls = [c for c in fake.calls if c[0] == "run"]
    assert len(run_calls) == 1 and len(fake.removed) == 1
    # P9：docker 参数由 SandboxLease(deny_all) 推导
    assert ("--network", "none") == tuple(run_calls[0][2:4])
    assert manager.leases[-1].network_policy == "deny_all"
    assert manager.leases[-1].purpose == "grading"


async def test_grade_tests_failed():
    fake = FakeDocker(base_commit=BASE, eval_log=FAILING_FAKE_LOG)
    report = await make_manager(fake).grade(
        trajectory_id="traj_fail", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "unresolved"
    assert report.failure_category == "tests_failed"
    assert report.reward == 0.0
    assert report.f2p_pass_count == 0 and report.f2p_total_count == 1


async def test_grade_patch_apply_failed():
    fake = FakeDocker(base_commit=BASE, apply_exit_code=1)
    report = await make_manager(fake).grade(
        trajectory_id="traj_conflict", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "unresolved"
    assert report.failure_category == "patch_apply_failed"
    assert report.reward == 0.0
    # 测试没跑：四计数必须缺席（契约校验器的要求，这里证明 manager 如实供数）
    assert report.f2p_pass_count is None and report.p2p_total_count is None
    assert report.patch_hygiene is not None  # apply 前 hygiene 已完成，必须附上


async def test_hygiene_rejected_patch_capped_below_resolved():
    """A7 条 3 的封顶行为：篡改测试文件的 patch，即使剥离后测试全过也拿不到 resolved。"""

    fake = FakeDocker(base_commit=BASE)  # eval 日志 = 全过
    report = await make_manager(fake).grade(
        trajectory_id="traj_tamper",
        workspace=FakeWorkspace(GOOD_PATCH + TAMPER_SEGMENT),
        spec=make_spec(),
    )
    assert report.patch_hygiene is not None
    assert report.patch_hygiene.verdict == "rejected_test_tampering"
    assert report.outcome == "unresolved" and report.reward == 0.0
    assert report.failure_category == "tests_failed"
    assert report.f2p_pass_count == 1  # 测试真实跑了且全过——封顶不是伪造计数


async def test_contamination_rejected_and_stripped():
    """A7 条 4：grader-only 文件污染 → verdict 降级 + 污染段不进重放载荷。"""

    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_pollute",
        workspace=FakeWorkspace(GOOD_PATCH + POLLUTION_SEGMENT),
        spec=make_spec(),
    )
    assert report.patch_hygiene is not None
    assert report.patch_hygiene.verdict == "rejected_forbidden_contamination"
    assert report.patch_hygiene.forbidden_paths == ["grader/secret.txt"]
    assert report.outcome == "unresolved" and report.reward == 0.0


async def test_zero_parsed_tests_is_test_log_parse_failed():
    """官方 silent-success 陷阱：标记齐全但 0 条测试解析 → infra 族，绝不给 reward。"""

    fake = FakeDocker(base_commit=BASE, eval_log=GARBAGE_FAKE_LOG)
    report = await make_manager(fake).grade(
        trajectory_id="traj_garbage", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "failed_to_grade"
    assert report.failure_category == "test_log_parse_failed"
    assert report.reward is None
    assert report.infra_failure_detail == "eval_log_zero_parsed_tests"
    assert report.f2p_total_count is None


async def test_missing_markers_after_successful_replay_is_parse_failed():
    """我们的 git apply 已成功，日志却缺官方标记（坏码）→ test_log_parse_failed。"""

    fake = FakeDocker(base_commit=BASE, eval_log=NO_MARKER_FAKE_LOG)
    report = await make_manager(fake).grade(
        trajectory_id="traj_nomarker", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.failure_category == "test_log_parse_failed"
    assert report.reward is None
    assert report.infra_failure_detail == "official_bad_codes_after_successful_replay"


async def test_parser_exception_is_parse_failed():
    def _boom(log_text: str):
        raise RuntimeError("parser exploded")

    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_parserboom",
        workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_spec(parse_log=_boom),
    )
    assert report.failure_category == "test_log_parse_failed"
    assert report.reward is None
    assert "official_parser_exception" in (report.infra_failure_detail or "")


async def test_killed_container_is_infra_failure():
    """P4：eval 失败 + 容器已死 → infra_failure，reward=None（不是 0）。"""

    fake = FakeDocker(base_commit=BASE, eval_exit_code=137, container_running=False)
    report = await make_manager(fake).grade(
        trajectory_id="traj_killed", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "failed_to_grade"
    assert report.failure_category == "infra_failure"
    assert report.reward is None
    assert "grading_container_killed_during_test" == report.infra_failure_detail


async def test_dead_workspace_is_infra_failure():
    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_deadws", workspace=FakeWorkspace(exit_code=1), spec=make_spec()
    )
    assert report.failure_category == "infra_failure"
    assert report.reward is None
    assert "workspace_patch_export_failed" in (report.infra_failure_detail or "")
    assert report.patch_hygiene is None  # 没走到重放，不得伪称做过 clean 重放


# ---------------------------------------------------------------------------
# codex#1：运行期镜像 digest 比对（评分容器侧，S1-7a 前置修复）
# ---------------------------------------------------------------------------

FROZEN_IMG_DIGEST = "sha256:" + "1" * 64


async def test_grade_image_digest_match_passes():
    """正例：容器实际镜像 RepoDigests 命中冻结 digest -> 评分正常，且比对确实发生。"""

    fake = FakeDocker(
        base_commit=BASE, repo_digests=("docker.io/fake/img@" + FROZEN_IMG_DIGEST,)
    )
    report = await make_manager(fake).grade(
        trajectory_id="traj_digest_ok",
        workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_spec(image_manifest_digest=FROZEN_IMG_DIGEST),
    )
    assert report.outcome == "resolved" and report.reward == 1.0
    joined = [" ".join(call) for call in fake.calls]
    assert any("{{.Image}}" in text for text in joined)  # 查容器实际镜像，不是 spec 标签
    assert any("RepoDigests" in text for text in joined)  # 比对 RepoDigests，不是 image ID


async def test_grade_image_digest_mismatch_is_infra_failure():
    """反例：RepoDigests 与冻结 digest 不符 -> infra_failure（reward=None），容器不泄漏。"""

    fake = FakeDocker(
        base_commit=BASE, repo_digests=("docker.io/fake/img@sha256:" + "2" * 64,)
    )
    report = await make_manager(fake).grade(
        trajectory_id="traj_digest_drift",
        workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_spec(image_manifest_digest=FROZEN_IMG_DIGEST),
    )
    assert report.outcome == "failed_to_grade"
    assert report.failure_category == "infra_failure"
    assert report.reward is None
    assert "grading_image_digest_mismatch" in (report.infra_failure_detail or "")
    assert "digest 漂移" in (report.infra_failure_detail or "")
    assert len(fake.removed) == 1  # 已起的容器照常清理


async def test_grade_image_without_repo_digests_and_no_marker_rejected():
    """反例（豁免必须显式）：镜像无 RepoDigests 且 spec 未声明 local_build -> infra 拒。"""

    fake = FakeDocker(base_commit=BASE, repo_digests=())
    report = await make_manager(fake).grade(
        trajectory_id="traj_digest_none",
        workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_spec(image_manifest_digest=FROZEN_IMG_DIGEST),
    )
    assert report.failure_category == "infra_failure" and report.reward is None
    detail = report.infra_failure_detail or ""
    assert "RepoDigests" in detail and "local_build" in detail


async def test_grade_local_build_exemption_skips_digest_probe():
    """豁免路径：image_local_build=True（fixture 默认）不做 RepoDigests 查询。"""

    fake = FakeDocker(base_commit=BASE)
    report = await make_manager(fake).grade(
        trajectory_id="traj_localbuild", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "resolved"
    assert not any("RepoDigests" in " ".join(call) for call in fake.calls)


def test_grading_spec_digest_declaration_is_mandatory():
    """schema 层钉死：digest 与 local_build 二选一——两者都缺或都给，构造即拒。"""

    with pytest.raises(ValueError, match="二选一"):
        make_spec(image_local_build=False)  # 都缺
    with pytest.raises(ValueError, match="二选一"):
        make_spec(image_manifest_digest=FROZEN_IMG_DIGEST, image_local_build=True)  # 都给


# ---------------------------------------------------------------------------
# F3：golden_patch 永不进评分容器（把代码路径事实钉成不变量）
# ---------------------------------------------------------------------------

GOLDEN_SENTINEL = "RH2_GOLDEN_PATCH_SENTINEL_9f3ae1"


async def test_golden_patch_never_reaches_grading_container_surfaces():
    """F3 不变量：从含哨兵 golden_patch 的真实 BundlePair 走生产取数通道
    （build_swe_grading_spec）跑完整 grade()，评分容器的全部注入面——docker
    调用参数（run 挂载/labels、exec 脚本）与全部 stdin 写入字节（cleaned patch、
    eval 脚本，即 manager 的 EVAL_SCRIPT_PATH 注入面）——找不到 golden_patch
    内容。评分必须正常走完，排除"因早退而未泄漏"的假阴性。"""

    from repoharness2.envpack import bundles

    statement = "Fix the broken feature() function so it returns the right value."
    instance_id = "rh2-fixture.golden-0001"
    pair = bundles.BundlePair(
        public=bundles.PublicTaskBundle(
            instance_id=instance_id,
            repo="psf/requests",
            base_commit=BASE,
            image="fake-image:v1",
            image_manifest_digest="sha256:" + "c" * 64,
            problem_statement=statement,
            problem_statement_sha256=bundles.sha256_of_text(statement),
        ),
        private=bundles.PrivateGradingBundle(
            instance_id=instance_id,
            repo="psf/requests",
            version="2.3",
            base_commit=BASE,
            golden_patch=(
                "diff --git a/src/thing.py b/src/thing.py\n"
                "--- a/src/thing.py\n+++ b/src/thing.py\n"
                f"@@ -1 +1 @@\n-broken\n+{GOLDEN_SENTINEL}\n"
            ),
            test_patch=(
                "diff --git a/tests/test_thing.py b/tests/test_thing.py\n"
                "--- a/tests/test_thing.py\n+++ b/tests/test_thing.py\n"
                "@@ -1 +1 @@\n-# a\n+# b\n"
            ),
            fail_to_pass=["tests/test_thing.py::test_feature"],
            pass_to_pass=["tests/test_thing.py::test_stable"],
            eval_script="echo eval",
            test_cmd="python tests/test_thing.py",
        ),
    )
    assert GOLDEN_SENTINEL in pair.private.golden_patch  # 哨兵在场，测试不空转
    spec = build_swe_grading_spec(pair)
    assert GOLDEN_SENTINEL not in spec.eval_script  # golden 不出 bundle 对象（codex#4）

    fake = FakeDocker(
        base_commit=BASE, repo_digests=("docker.io/fake/img@sha256:" + "c" * 64,)
    )
    report = await make_manager(fake).grade(
        trajectory_id="traj_golden_iso", workspace=FakeWorkspace(GOOD_PATCH), spec=spec
    )
    assert report.outcome == "resolved"  # 正常评完（GOOD_FAKE_LOG 覆盖 F2P/P2P）

    for call in fake.calls:  # run 参数（挂载/labels/env）与 exec 脚本
        assert GOLDEN_SENTINEL not in " ".join(call)
    for args, payload in fake.input_payloads:  # 全部 stdin 写入（patch/eval 脚本）
        assert GOLDEN_SENTINEL.encode() not in payload, f"泄漏进容器写入 {args}"


def test_p4_schema_lock_infra_with_reward_is_unrepresentable():
    """P4 第二道锁：就算未来有人改坏 manager，infra+reward 的报告在 schema 层拒收。"""

    payload = {
        "schema_id": "rh2.grading_report.v1",
        "report_id": "rpt_x",
        "trajectory_id": "traj_x",
        "task_id": FIXTURE_INSTANCE_ID,
        "grader_name": GRADER_NAME,
        "grader_version": "swebench-4.1.0",
        "outcome": "failed_to_grade",
        "failure_category": "infra_failure",
        "reward": 0.0,
        "infra_failure_detail": "grading_container_killed",
        "graded_at_utc": "2026-07-07T00:00:00Z",
    }
    with pytest.raises(ValidationError):
        GradingReport.model_validate(payload)


# ---------------------------------------------------------------------------
# P2 / P5 / P10：prepare 预热、竞态冷启动、镜像拉取分档
# ---------------------------------------------------------------------------


async def test_prepare_is_bounded_and_fire_and_forget():
    """P2：prepare 立刻返回 Task；并发拉取数受 prepare_concurrency 信号量约束。"""

    import asyncio

    fake = FakeDocker(base_commit=BASE, image_present=False, pull_delay=0.05)
    manager = make_manager(fake, prepare_concurrency=2)
    tasks = [manager.prepare(make_spec(image=f"fake-image:v{i}")) for i in range(6)]
    assert all(isinstance(t, asyncio.Task) for t in tasks)  # 未阻塞调用方
    await asyncio.gather(*tasks)
    assert fake.pull_count == 6
    assert fake.max_concurrent_pulls <= 2


async def test_grade_cold_start_without_prepare_and_pull_cached():
    """P5 冷启动 + P10 第一档：没预热照样评（自己拉镜像）；同镜像第二次评分零拉取。"""

    fake = FakeDocker(base_commit=BASE, image_present=False)
    manager = make_manager(fake)
    r1 = await manager.grade(
        trajectory_id="traj_cold1", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    r2 = await manager.grade(
        trajectory_id="traj_cold2", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert r1.outcome == r2.outcome == "resolved"
    assert fake.pull_count == 1  # 第二次命中缓存
    assert r2.timings is not None and r2.timings.image_pull_seconds == 0.0


async def test_prepare_grade_race_pulls_image_once():
    """P5 竞态：prepare 在途时 grade 到达——per-image 锁去重，谁先到谁拉，只拉一次。"""

    fake = FakeDocker(base_commit=BASE, image_present=False, pull_delay=0.1)
    manager = make_manager(fake)
    manager.prepare(make_spec())
    report = await manager.grade(
        trajectory_id="traj_race", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "resolved"
    assert fake.pull_count == 1


async def test_prepare_failure_does_not_poison_grade():
    """P5：prepare 拉取失败只记 prepare_failures；随后的 grade 自行重试成功。"""

    import asyncio

    fake = FakeDocker(base_commit=BASE, image_present=False, pull_fail=True)
    manager = make_manager(fake)
    await asyncio.gather(manager.prepare(make_spec()))
    assert manager.prepare_failures and "fake-image:v1" in manager.prepare_failures[0]
    fake.pull_fail = False  # 网络恢复
    report = await manager.grade(
        trajectory_id="traj_recover", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
    )
    assert report.outcome == "resolved"
    assert fake.pull_count == 2  # 失败一次 + 成功一次


# ---------------------------------------------------------------------------
# P1（记账口）/ P8：gc 与跨 trace 不复用
# ---------------------------------------------------------------------------


async def test_no_container_reuse_across_grades():
    """P8：同 trajectory_id 评两次（≈verifiers 重试语义）也各起各的容器，绝不复用。"""

    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    for _ in range(2):
        await manager.grade(
            trajectory_id="traj_retry", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()
        )
    names = {record.name for record in manager.container_records}
    assert len(names) == 2  # 名字含随机 nonce，两次必不同
    assert all(record.removed for record in manager.container_records)
    assert sorted(fake.removed) == sorted(names)


async def test_gc_by_trace_and_ttl():
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    spec = make_spec()
    rec_a = await manager._start_container("traj_a", spec, "aaaa0001")
    rec_b = await manager._start_container("traj_b", spec, "bbbb0001")
    assert await manager.gc(trajectory_id="traj_a") == [rec_a.name]
    assert await manager.gc(ttl_seconds=9999.0) == []  # 都还年轻
    assert await manager.gc(ttl_seconds=0.0) == [rec_b.name]  # TTL 到期全收
    assert await manager.gc() == []  # 账已清


async def test_startup_sweep_age_and_ownership_rules():
    """P1：清扫只动「非本 owner 且超龄」的 label 容器；时间戳非法视为孤儿。"""

    import time as _time

    now = _time.time()
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake, orphan_min_age_seconds=3600.0)
    fake.ps_stdout = (
        f"orphan_old\tdeadrun\t{now - 7200:.0f}\n"  # 外来 + 超龄 → 清
        f"orphan_fresh\totherrun\t{now:.0f}\n"  # 外来但年轻（可能是并行 worker）→ 留
        f"mine\t{manager.run_id}\t{now - 7200:.0f}\n"  # 本 owner → 留
        "orphan_badts\tdeadrun2\tnot_a_number\n"  # 时间戳非法 → 视为孤儿清掉
    )
    removed = await manager.startup()
    assert sorted(removed) == ["orphan_badts", "orphan_old"]
    assert sorted(fake.removed) == ["orphan_badts", "orphan_old"]


async def test_run_id_label_stamped_only_when_env_set(monkeypatch):
    """miles GPU spike 聚焦修复批 #4：launch 经 Ray runtime env 下发
    MILES_RH2_RUN_ID 时，评分容器必须携带本 run owner label
    rh2.run_id=<run_id>（postrun_probes.py shutdown 探针按该 label 精确归属
    本 run 遗留容器）；env 未设时 docker 参数保持原样（非 spike 链零扰动）。"""

    monkeypatch.setenv("MILES_RH2_RUN_ID", "spike-run-1")
    fake = FakeDocker(base_commit=BASE)
    spec = make_spec()
    await make_manager(fake)._start_container("traj_label", spec, "dddd0001")
    run_call = next(c for c in fake.calls if c[0] == "run")
    joined = " ".join(run_call)
    assert "rh2.run_id=spike-run-1" in joined

    monkeypatch.delenv("MILES_RH2_RUN_ID")
    fake2 = FakeDocker(base_commit=BASE)
    await make_manager(fake2)._start_container("traj_label2", spec, "eeee0001")
    run_call2 = next(c for c in fake2.calls if c[0] == "run")
    assert "rh2.run_id" not in " ".join(run_call2)


async def test_cleanup_failure_is_recorded_not_swallowed():
    """Q8：容器 rm 失败必须留痕（cleanup_failures），供 S1-6 收口为 finding。"""

    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    spec = make_spec()
    record = await manager._start_container("traj_stuck", spec, "cccc0001")
    fake.rm_fail_names = (record.name,)
    await manager.gc()
    assert not record.removed
    assert any("container_rm_failed" in item for item in manager.cleanup_failures)


# ---------------------------------------------------------------------------
# P7：backend-neutral 注入 + per-worker 独立实例
# ---------------------------------------------------------------------------


async def test_backend_injection_and_instance_isolation():
    fake1 = FakeDocker(base_commit=BASE)
    fake2 = FakeDocker(base_commit=BASE)
    m1, m2 = make_manager(fake1), make_manager(fake2)
    assert m1.run_id != m2.run_id  # owner 标识独立（同宿主多 worker 互不误伤）
    await m1.grade(trajectory_id="t1", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert fake1.calls and not fake2.calls  # docker 通道完全隔离
    assert SWEGradingManager()._docker is run_docker  # 默认通道 = 真 docker CLI


# ---------------------------------------------------------------------------
# SWE spec 构造（S1-2 bundle -> 评分 spec 的接线；8 题真实回归递延到远程机）
# ---------------------------------------------------------------------------


def test_build_swe_grading_spec_wiring():
    pair = load_bundle_pairs(subset=["django__django-11099"])[0]
    spec = build_swe_grading_spec(pair)
    assert spec.task_id == "django__django-11099"
    assert spec.image == pair.public.image
    assert spec.base_commit == pair.public.base_commit
    # codex#1：冻结镜像 digest 进 spec（运行期 RepoDigests 比对），真实任务无豁免
    assert spec.image_manifest_digest == pair.public.image_manifest_digest
    assert spec.image_local_build is False
    assert spec.eval_script == pair.private.eval_script
    assert spec.checkout_mode == "image_embedded"
    assert spec.grader_name == GRADER_NAME
    assert spec.grader_version.startswith("swebench-")
    # 官方测试文件名单来自 private.test_patch 触碰路径
    assert "tests/auth_tests/test_validators.py" in spec.hygiene.test_files
    # 该名单 + 默认通配能把篡改官方测试的 patch 判成 tampering
    tamper = (
        "diff --git a/tests/auth_tests/test_validators.py b/tests/auth_tests/test_validators.py\n"
        "--- a/tests/auth_tests/test_validators.py\n"
        "+++ b/tests/auth_tests/test_validators.py\n"
        "@@ -1 +1 @@\n-x\n+y\n"
    )
    from repoharness2.grading.manager import clean_patch

    assert clean_patch(tamper, spec.hygiene).verdict == "rejected_test_tampering"


def test_swe_spec_parse_log_binds_private_bundle():
    """spec.parse_log 已绑定 private 材料：直接喂官方坏码日志能得 apply_ok=False。"""

    pair = load_bundle_pairs(subset=["django__django-11099"])[0]
    spec = build_swe_grading_spec(pair)
    verdict = spec.parse_log(">>>>> Patch Apply Failed\nboom\n")
    assert verdict.apply_ok is False and verdict.resolved is False


# ---------------------------------------------------------------------------
# 依赖纪律：grading 包 import 零 verifiers / 零 swebench（与 envpack 同律）
# ---------------------------------------------------------------------------


def test_grading_package_imports_no_verifiers_or_swebench():
    probe = """
import importlib, json, sys
for name in ("repoharness2.grading", "repoharness2.grading.manager", "repoharness2.grading.queue"):
    importlib.import_module(name)
leaked = sorted(
    m for m in sys.modules
    if m.split(".")[0] in ("verifiers", "swebench")
)
print(json.dumps(leaked))
"""
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert proc.returncode == 0, f"grading 模块子进程 import 失败:\n{proc.stderr}"
    import json

    assert json.loads(proc.stdout.strip().splitlines()[-1]) == []


# ---------------------------------------------------------------------------
# 批 D-2（I14 grading 侧；06 A4）：评分容器的有界收口与最终状态三分
# ---------------------------------------------------------------------------


async def test_rm_failure_but_container_stopped_is_diagnostic_only():
    """第一次 rm 失败但 inspect 确认已停止 → 只留 cleanup_failures 诊断，报告照常返回，不 fatal。"""

    fake = FakeDocker(base_commit=BASE, container_running=False)
    manager = make_manager(fake)

    async def rm_always_fails(*args, input_bytes=None):
        if args[0] == "rm":
            return ExecResult(1, "", f"cannot remove {args[-1]}: fake failure")
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    manager._docker = rm_always_fails
    report = await manager.grade(trajectory_id="traj_stop", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome in ("resolved", "unresolved", "failed_to_grade")
    assert any("container_rm_failed" in item for item in manager.cleanup_failures)
    assert any("container_scope_stopped_but_not_removed" in item for item in manager.cleanup_failures)
    assert fake.killed == []  # 已停止就不 kill


async def test_rm_failure_running_container_killed_then_confirmed_stopped_is_diagnostic():
    """rm 失败且仍运行 → docker kill → 确认已停止（rm 仍失败）→ 诊断留痕，不 fatal；停止与删除分开表述。"""

    fake = FakeDocker(base_commit=BASE, container_running=True, kill_stops=True)
    manager = make_manager(fake)

    async def rm_always_fails(*args, input_bytes=None):
        if args[0] == "rm":
            return ExecResult(1, "", f"cannot remove {args[-1]}: fake failure")
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    manager._docker = rm_always_fails
    report = await manager.grade(trajectory_id="traj_kill", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome in ("resolved", "unresolved", "failed_to_grade")
    assert len(fake.killed) == 1
    assert any("container_scope_killed_but_not_removed" in item for item in manager.cleanup_failures)


@pytest.mark.parametrize(
    ("running", "inspect_fail", "expected_state"),
    [
        (True, None, "running"),  # kill 也停不下来
        (True, "Cannot connect to the Docker daemon at unix:///var/run/docker.sock", "unknown"),
    ],
)
async def test_scope_still_running_or_unknown_after_bounded_closure_is_fatal(running, inspect_fail, expected_state):
    """有界收口（rm -f → kill → rm -f）后仍运行 / 无法确认 → GradingScopeTerminationError（穿队列上抛，
    编排转 run-fatal）；清理动作已做完、留痕在 cleanup_failures。"""

    from repoharness2.grading.manager import GradingScopeTerminationError

    fake = FakeDocker(base_commit=BASE, container_running=running, kill_stops=False, inspect_fail=inspect_fail)
    manager = make_manager(fake)

    async def rm_always_fails(*args, input_bytes=None):
        if args[0] == "rm":
            return ExecResult(1, "", f"cannot remove {args[-1]}: fake failure")
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    manager._docker = rm_always_fails
    with pytest.raises(GradingScopeTerminationError, match="grading_scope_termination_failed") as ei:
        await manager.grade(trajectory_id="traj_stuck", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert expected_state in str(ei.value)
    assert any("container_scope_termination_failed" in item for item in manager.cleanup_failures)
    if expected_state == "running":
        assert len(fake.killed) == 1  # 收口确实尝试过 kill


async def test_inspect_failure_during_test_is_state_unknown_not_killed():
    """`_exec_bash_checked`：命令失败且 inspect 不可达 → `grading_container_state_unknown_during_test`
    （不再把 inspect 失败压成"容器已死"）。"""

    fake = FakeDocker(base_commit=BASE, eval_exit_code=137, inspect_fail="Cannot connect to the Docker daemon")
    report = await make_manager(fake).grade(trajectory_id="traj_unknown", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome == "failed_to_grade" and report.failure_category == "infra_failure"
    assert report.infra_failure_detail == "grading_container_state_unknown_during_test"


async def test_manager_run_docker_is_cancel_safe_is_the_default_channel():
    """批 B 已修的 run_docker 是评分侧默认通道（generate 与 manager 同一对象）——这里只钉住引用关系。"""

    from repoharness2.adapters.slime import generate as generate_mod
    from repoharness2.grading import manager as manager_mod

    assert generate_mod.run_docker is manager_mod.run_docker


# ---------------------------------------------------------------------------
# Codex 联合审查 R2：grader 收口的总截止点（rm / inspect / kill 挂起也在预算内产生终止结果）
# ---------------------------------------------------------------------------


def _blocking_docker(fake: FakeDocker, block: str, *, block_once: bool = True):
    """把某个 docker 子命令挂起（默认只挂第一次），其余交给 FakeDocker；rm 除首次挂起外一律失败。"""

    state = {"blocked": 0}

    async def docker(*args, input_bytes=None):
        if args[0] == block and (not block_once or state["blocked"] == 0):
            state["blocked"] += 1
            await asyncio.Event().wait()
        if args[0] == "rm":
            return ExecResult(1, "", f"daemon failed to remove {args[-1]}")
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    return docker


@pytest.mark.parametrize("block", ["rm", "inspect", "kill"])
async def test_closure_io_hang_yields_scope_fatal_within_cleanup_budget(block):
    from repoharness2.grading.manager import GradingScopeTerminationError

    fake = FakeDocker(base_commit=BASE, container_running=True, kill_stops=False)
    manager = make_manager(fake, cleanup_timeout_seconds=1)  # 契约字段是整数秒
    manager._docker = _blocking_docker(fake, block, block_once=(block != "inspect"))
    started = asyncio.get_running_loop().time()
    with pytest.raises(GradingScopeTerminationError, match="grading_scope_termination_failed") as ei:
        await asyncio.wait_for(
            manager.grade(trajectory_id=f"traj_hang_{block}", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()),
            timeout=5,
        )
    elapsed = asyncio.get_running_loop().time() - started
    assert elapsed < 4.0  # 修前：挂起的 IO 让 grade() 永久 pending
    assert "unknown" in str(ei.value) or "running" in str(ei.value)
    assert any("container_scope_termination_failed" in item for item in manager.cleanup_failures)
    if block == "rm":
        assert any("container_rm_timeout" in item for item in manager.cleanup_failures)
    if block == "kill":
        assert any("container_kill_timeout" in item for item in manager.cleanup_failures)


async def test_inspect_hang_during_test_is_state_unknown_within_budget():
    """`_exec_bash_checked` 的状态查询也有界：inspect 挂起 → unknown 归因，随后正常 rm 收口，不 fatal。"""

    fake = FakeDocker(base_commit=BASE, eval_exit_code=137)
    manager = make_manager(fake, cleanup_timeout_seconds=1)
    state = {"n": 0}

    async def docker(*args, input_bytes=None):
        if args[0] == "inspect" and "{{.State.Running}}" in args:
            state["n"] += 1
            await asyncio.Event().wait()
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    manager._docker = docker
    report = await asyncio.wait_for(
        manager.grade(trajectory_id="traj_inspect_hang", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()),
        timeout=5,
    )
    assert report.outcome == "failed_to_grade"
    assert report.infra_failure_detail == "grading_container_state_unknown_during_test"
    assert manager.container_records[-1].removed is True


# ---------------------------------------------------------------------------
# Codex 联合审查 R4：缺 socket ≠ 缺容器
# ---------------------------------------------------------------------------


def _rm_fails_docker(fake: FakeDocker, inspect_reply):
    """rm 一律失败；inspect {{.State.Running}} 由 inspect_reply(name) 决定；其余交 FakeDocker。"""

    async def docker(*args, input_bytes=None):
        if args[0] == "rm":
            return ExecResult(1, "", f"daemon failed to remove {args[-1]}")
        if args[0] == "inspect" and "{{.State.Running}}" in args:
            return inspect_reply(args[-1])
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    return docker


async def test_missing_docker_socket_is_unknown_not_absent():
    """修前：`dial unix /var/run/docker.sock: connect: no such file or directory` 含 "no such" 被判 absent，
    reward 样本照常交付、halt=0；修后 unknown → GradingScopeTerminationError。"""

    from repoharness2.grading.manager import GradingScopeTerminationError

    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake, cleanup_timeout_seconds=1)
    manager._docker = _rm_fails_docker(
        fake, lambda name: ExecResult(1, "", "error during connect: dial unix /var/run/docker.sock: connect: no such file or directory"),
    )
    with pytest.raises(GradingScopeTerminationError, match="unknown"):
        await manager.grade(trajectory_id="traj_socket", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert any("container_scope_termination_failed" in item and ":unknown" in item for item in manager.cleanup_failures)


async def test_target_container_truly_absent_stays_diagnostic():
    """对照：明确指向本容器的 "No such object: <name>" → absent → 只留诊断，报告照常。"""

    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake, cleanup_timeout_seconds=1)
    manager._docker = _rm_fails_docker(fake, lambda name: ExecResult(1, "", f"Error: No such object: {name}"))
    report = await manager.grade(trajectory_id="traj_absent", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome in ("resolved", "unresolved", "failed_to_grade")
    assert any("container_scope_stopped_but_not_removed" in item and ":absent" in item for item in manager.cleanup_failures)


async def test_other_container_absent_or_garbage_success_output_is_unknown():
    """不指向本容器的 "No such object: other" 与成功退出但非 true/false 的输出都只能是 unknown → fatal。"""

    from repoharness2.grading.manager import GradingScopeTerminationError

    for reply in (
        lambda name: ExecResult(1, "", "Error: No such object: some-other-container"),
        lambda name: ExecResult(0, "maybe\n", ""),
    ):
        fake = FakeDocker(base_commit=BASE)
        manager = make_manager(fake, cleanup_timeout_seconds=1)
        manager._docker = _rm_fails_docker(fake, reply)
        with pytest.raises(GradingScopeTerminationError, match="unknown"):
            await manager.grade(trajectory_id="traj_unknown_shape", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())


# ---------------------------------------------------------------------------
# N2a（第 2 组剩余实施 Brief §3.2；Codex 计划审查 R1）：评分工作总期限约束实际评分工作
# ---------------------------------------------------------------------------


def _deadline(seconds: float) -> float:
    return asyncio.get_running_loop().time() + seconds if False else __import__("time").monotonic() + seconds


async def test_deadline_already_exhausted_when_dequeued_does_not_start_a_container():
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    report = await manager.grade(
        trajectory_id="traj_dl_queue", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec(),
        deadline_monotonic=_deadline(-1.0),
    )
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail == "grading_deadline_exhausted:queue"
    assert not any(c[0] == "run" for c in fake.calls)  # 排队已耗尽期限：不起容器


async def test_pull_hang_is_cut_at_the_grading_deadline_without_starting_a_container():
    fake = FakeDocker(base_commit=BASE, image_present=False, pull_delay=5.0)
    manager = make_manager(fake)
    started = asyncio.get_running_loop().time()
    report = await asyncio.wait_for(
        manager.grade(trajectory_id="traj_dl_pull", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec(),
                      deadline_monotonic=_deadline(0.3)),
        timeout=5,
    )
    assert asyncio.get_running_loop().time() - started < 2.0
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail == "grading_deadline_exhausted:image_pull"
    assert not any(c[0] == "run" for c in fake.calls)
    assert fake.pulls_in_flight == 0  # wait_for 取消了 pull（替身在 finally 里归零）


async def test_image_lock_wait_consumes_the_deadline_of_the_waiter():
    fake = FakeDocker(base_commit=BASE, image_present=False, pull_delay=1.0)
    manager = make_manager(fake)
    first = asyncio.create_task(manager.grade(
        trajectory_id="traj_lock_1", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec(), deadline_monotonic=_deadline(30.0),
    ))
    await asyncio.sleep(0.05)  # 第一条持有 per-image 锁在 pull
    second = await asyncio.wait_for(manager.grade(
        trajectory_id="traj_lock_2", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec(), deadline_monotonic=_deadline(0.2),
    ), timeout=5)
    assert second.outcome == "failed_to_grade" and second.infra_failure_detail == "grading_deadline_exhausted:image_lock"
    first_report = await asyncio.wait_for(first, timeout=5)
    assert first_report.outcome in ("resolved", "unresolved")  # 持锁者不受等待者期限影响


async def test_prep_exec_hang_hits_deadline_and_the_container_is_still_cleaned():
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake, cleanup_timeout_seconds=1)
    state = {"n": 0}

    async def docker(*args, input_bytes=None):
        if args[0] == "exec" and state["n"] == 0:
            state["n"] += 1
            await asyncio.Event().wait()  # 第一个 exec（准备阶段）挂起
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    manager._docker = docker
    report = await asyncio.wait_for(
        manager.grade(trajectory_id="traj_dl_prep", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec(),
                      deadline_monotonic=_deadline(0.3)),
        timeout=5,
    )
    assert report.outcome == "failed_to_grade"
    assert report.infra_failure_detail.startswith("grading_deadline_exhausted:")
    assert manager.container_records[-1].removed is True  # 清理沿自己的预算，不因期限耗尽跳过


async def test_test_phase_timeout_is_clamped_by_the_deadline_and_attributed_to_it():
    fake = FakeDocker(base_commit=BASE, eval_delay=5.0)
    manager = make_manager(fake, cleanup_timeout_seconds=1)
    report = await asyncio.wait_for(
        manager.grade(trajectory_id="traj_dl_test", workspace=FakeWorkspace(GOOD_PATCH),
                      spec=make_spec(test_timeout_seconds=100.0), deadline_monotonic=_deadline(0.4)),
        timeout=5,
    )
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail == "grading_deadline_exhausted:test"
    assert manager.container_records[-1].removed is True


async def test_no_deadline_keeps_the_old_behaviour():
    fake = FakeDocker(base_commit=BASE, eval_delay=0.05)
    manager = make_manager(fake)
    report = await manager.grade(trajectory_id="traj_no_dl", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome in ("resolved", "unresolved")


# ---------------------------------------------------------------------------
# N2b（I16，补充说明 §8 已批范围）：镜像就绪 / 容器启动的已识别传输故障最多追加一次评分
# ---------------------------------------------------------------------------


def _fail_first(fake: FakeDocker, cmd: str, stderr: str, *, times: int = 1, on_fail=None):
    """让某个 docker 子命令的前 times 次返回非零 + 给定 stderr（真实 CLI 形态），其余交 FakeDocker。"""

    state = {"n": 0, "names": []}

    async def docker(*args, input_bytes=None):
        if args[0] == cmd and state["n"] < times:
            state["n"] += 1
            if cmd == "run":
                state["names"].append(args[args.index("--name") + 1])
            if on_fail is not None:
                on_fail()
            return ExecResult(1, "", stderr)
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    return docker, state


TLS_TIMEOUT = "Error response from daemon: Get \"https://registry-1.docker.io/v2/\": net/http: TLS handshake timeout"
DAEMON_RESET = "error during connect: Post \"http://%2Fvar%2Frun%2Fdocker.sock/v1.45/containers/create\": read: connection reset by peer"


def test_transport_error_classifier_only_accepts_documented_shapes():
    from repoharness2.grading.manager import classify_docker_transport_error as c

    assert c("image_pull", 1, TLS_TIMEOUT) == "registry_transport"
    assert c("container_start", 1, DAEMON_RESET) == "daemon_connect"
    assert c("image_pull", 1, "Cannot connect to the Docker daemon at unix:///var/run/docker.sock") == "daemon_connect"
    assert c("image_pull", 1, "Error response from daemon: pull access denied for x, repository does not exist") is None
    assert c("image_pull", 1, "Error response from daemon: manifest for x not found: manifest unknown") is None
    assert c("container_start", 1, "docker: invalid reference format.") is None
    assert c("container_start", 1, "Error response from daemon: TLS handshake timeout") is None  # run 阶段不认 registry 暂态
    assert c("image_pull", 1, "timeout") is None and c("image_pull", 1, "EOF") is None  # 泛化子串不兜底
    assert c("image_pull", 0, TLS_TIMEOUT) is None and c("test", 1, DAEMON_RESET) is None  # 非失败 / 阶段不允许
    assert c("image_pull", 1, "unauthorized: authentication required; connection reset by peer") is None  # 确定性错误优先排除


async def test_pull_transport_error_is_retried_once_then_grades():
    fake = FakeDocker(base_commit=BASE, image_present=False)
    manager = make_manager(fake)
    manager._docker, state = _fail_first(fake, "pull", TLS_TIMEOUT)
    report = await manager.grade(trajectory_id="traj_regrade_pull", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome in ("resolved", "unresolved")
    assert state["n"] == 1 and fake.pull_count == 1  # 第一次替身失败（未计入 fake.pull_count），第二次真实成功
    (event,) = manager.regrade_events
    assert event["op"] == "image_pull" and event["category"] == "registry_transport" and event["attempt"] == 1
    assert (await manager.close())["regrade_events"] == 1


async def test_container_start_transport_error_closes_the_named_container_then_retries():
    fake = FakeDocker(base_commit=BASE)
    manager = make_manager(fake)
    manager._docker, state = _fail_first(fake, "run", DAEMON_RESET)
    report = await manager.grade(trajectory_id="traj_regrade_run", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome in ("resolved", "unresolved")
    (first_name,) = state["names"]
    assert first_name in fake.removed  # 创建回包丢失 → 先按本次名字收口（rm -f）
    names = [r.name for r in manager.container_records]
    assert first_name in names and len(set(names)) == 2  # 两次对象都在清理记录里，第二次是新名字
    assert all(r.removed for r in manager.container_records)
    (event,) = manager.regrade_events
    assert event["op"] == "container_start" and event["category"] == "daemon_connect"
    assert (await manager.close())["containers_open"] == []


@pytest.mark.parametrize(
    ("cmd", "stderr", "detail_prefix"),
    [
        ("pull", "Error response from daemon: pull access denied for fake/img, repository does not exist", "grading_image_pull_failed"),
        ("run", "docker: invalid reference format.", "grading_container_start_failed"),
    ],
)
async def test_deterministic_errors_are_not_retried(cmd, stderr, detail_prefix):
    fake = FakeDocker(base_commit=BASE, image_present=(cmd != "pull"))
    manager = make_manager(fake)
    manager._docker, state = _fail_first(fake, cmd, stderr, times=5)
    report = await manager.grade(trajectory_id=f"traj_no_retry_{cmd}", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail.startswith(detail_prefix)
    assert state["n"] == 1 and manager.regrade_events == []


async def test_two_transport_failures_stop_at_two_attempts_and_keep_both_details():
    fake = FakeDocker(base_commit=BASE, image_present=False)
    manager = make_manager(fake)
    manager._docker, state = _fail_first(fake, "pull", TLS_TIMEOUT, times=5)
    report = await manager.grade(trajectory_id="traj_regrade_twice", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome == "failed_to_grade"
    assert "first_attempt: grading_image_pull_failed" in report.infra_failure_detail
    assert state["n"] == 2 and len(manager.regrade_events) == 1  # 总共两次尝试，不是无限循环
    assert not any(c[0] == "run" for c in fake.calls)


async def test_second_attempt_is_still_bounded_by_the_shared_deadline():
    fake = FakeDocker(base_commit=BASE, image_present=False)
    manager = make_manager(fake)
    state = {"n": 0}

    async def docker(*args, input_bytes=None):
        if args[0] == "pull":
            state["n"] += 1
            await asyncio.sleep(0.15)
            if state["n"] == 1:
                return ExecResult(1, "", TLS_TIMEOUT)
            await asyncio.sleep(5)  # 第二次拉取慢：必须被同一期限切断，不重置
        return await FakeDocker.__call__(fake, *args, input_bytes=input_bytes)

    manager._docker = docker
    report = await asyncio.wait_for(
        manager.grade(trajectory_id="traj_regrade_deadline", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec(),
                      deadline_monotonic=__import__("time").monotonic() + 0.4),
        timeout=5,
    )
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail.startswith("grading_deadline_exhausted:image_pull")
    assert state["n"] == 2 and len(manager.regrade_events) == 1


async def test_unconfirmed_old_container_after_start_failure_is_run_fatal_not_retry():
    from repoharness2.grading.manager import GradingScopeTerminationError

    fake = FakeDocker(base_commit=BASE, inspect_fail="Cannot connect to the Docker daemon", container_running=True)
    manager = make_manager(fake, cleanup_timeout_seconds=1)
    base_docker, state = _fail_first(fake, "run", DAEMON_RESET)

    async def docker(*args, input_bytes=None):
        if args[0] == "rm":
            return ExecResult(1, "", "Error response from daemon: cannot remove container")  # 旧工作无法确认结束
        return await base_docker(*args, input_bytes=input_bytes)

    manager._docker = docker
    with pytest.raises(GradingScopeTerminationError):
        await asyncio.wait_for(
            manager.grade(trajectory_id="traj_regrade_unknown", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec()),
            timeout=5,
        )
    assert manager.regrade_events == [] and state["n"] == 1


async def test_shutdown_between_attempts_blocks_the_second_attempt():
    fake = FakeDocker(base_commit=BASE, image_present=False)
    manager = make_manager(fake)
    manager._docker, state = _fail_first(fake, "pull", TLS_TIMEOUT, on_fail=lambda: setattr(manager, "_closed", True))
    report = await manager.grade(trajectory_id="traj_regrade_closed", workspace=FakeWorkspace(GOOD_PATCH), spec=make_spec())
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail.startswith("grading_image_pull_failed")
    assert state["n"] == 1 and manager.regrade_events == []
