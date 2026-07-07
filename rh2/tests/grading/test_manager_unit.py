"""SWEGradingManager 单测（FakeDocker 注入，无 docker）：归因决策树 + P2/P4/P5/P7/P8/P10。

真容器行为（P1 清扫 / P3 超时 / P6 只读 / P9 断网 / 杀容器注入）见
test_manager_docker.py；这里用桩把控制流逐条钉死。
"""

import subprocess
import sys
from dataclasses import replace

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
