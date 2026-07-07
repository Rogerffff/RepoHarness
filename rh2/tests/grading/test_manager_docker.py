"""S1-4 docker 行为验证（@pytest.mark.docker）：真容器上的评分闭环与故障注入。

镜像 = 本地轻量 fixture 镜像（python:3.12-slim + git，U-D：不拉 x86 SWE 镜像）。
每个用例走完整 grade 流程：HostWorkspace 导出 → fresh 容器（--network none）
只读快照 clone 出 clean checkout（血缘核验）→ git apply 重放 → 真跑测试 →
官方 parser（psf/requests 的 pytest 解析器）→ GradingReport。

故障注入四类（任务验收项）：
  杀评分容器      -> infra_failure（reward=None）
  篡改测试文件    -> hygiene 降级（rejected_test_tampering，封顶 unresolved）
  日志不可解析    -> test_log_parse_failed（reward=None）
  队列打满        -> 反压事件（见 test_queue.py，纯 asyncio 可测无需 docker）
外加 P1 孤儿清扫、P3 分段超时、P6 快照只读、P9 评分容器断网。
"""

import asyncio
import hashlib
import subprocess
import time
import uuid
from pathlib import Path

import pytest
from conftest import requires_docker
from grading_fixtures import (
    GARBAGE_EVAL_SCRIPT,
    SLOW_EVAL_SCRIPT,
    SRC_FIXED,
    SRC_STILL_BROKEN,
    TEST_FILE_CONTENT,
    FixtureRepo,
    git_in,
    make_eval_script,
    make_fixture_spec,
)

from repoharness2.contracts import GradingReport
from repoharness2.grading.manager import (
    GradingManagerConfig,
    HostWorkspace,
    SWEGradingManager,
)

pytestmark = [pytest.mark.docker, requires_docker]


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _docker(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)


def _dir_content_digest(root: Path) -> str:
    """目录内容 digest（相对路径 + 文件字节，P6 前后对照用）。"""

    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(root)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _make_manager(tmp_path: Path, **config_kwargs) -> SWEGradingManager:
    config_kwargs.setdefault("eval_log_dir", tmp_path / "eval_logs")
    return SWEGradingManager(GradingManagerConfig(**config_kwargs))


def _read_eval_log(manager: SWEGradingManager, report: GradingReport) -> str:
    assert report.eval_log_ref is not None
    log_path = Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.eval.log"
    payload = log_path.read_bytes()
    # ArtifactRef 自证：digest 与字节数可独立重算
    assert report.eval_log_ref.sha256 == "sha256:" + hashlib.sha256(payload).hexdigest()
    assert report.eval_log_ref.byte_size == len(payload)
    return payload.decode()


def _assert_no_leftover_containers(manager: SWEGradingManager) -> None:
    ps = _docker(
        "ps", "-a", "--filter", f"label={manager.config.label_prefix}.owner={manager.run_id}",
        "--format", "{{.ID}}",
    )
    assert ps.stdout.strip() == "", f"评分容器泄漏: {ps.stdout}"


def _spec(fixture_repo: FixtureRepo, fixture_image: str, **overrides):
    return make_fixture_spec(
        fixture_repo.base_commit,
        fixture_image,
        snapshot_host_path=str(fixture_repo.path),
        **overrides,
    )


# ---------------------------------------------------------------------------
# 正常三态
# ---------------------------------------------------------------------------


async def test_grade_resolved_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-resolved",
        workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image),
    )
    assert report.outcome == "resolved" and report.reward == 1.0
    assert (report.f2p_pass_count, report.f2p_total_count) == (1, 1)
    assert (report.p2p_fail_count, report.p2p_total_count) == (0, 1)
    assert report.patch_hygiene is not None
    assert report.patch_hygiene.verdict == "clean"
    assert report.patch_hygiene.replayed_on_clean_checkout is True
    # F5 五类计时：真容器上 env_reset/test 必然可观测，总时长covering测试段
    t = report.timings
    assert t is not None
    assert t.image_pull_seconds == 0.0  # 本地镜像命中（预拉取语义）
    assert t.env_reset_seconds > 0.0 and t.test_seconds > 0.0
    assert t.total_grading_seconds >= t.test_seconds
    # eval 原始日志落盘且 digest 自证；官方标记在场
    log_text = _read_eval_log(manager, report)
    assert ">>>>> Start Test Output" in log_text
    assert f"PASSED tests/test_thing.py::test_feature" in log_text
    # P9 租约 evidence + P1 容器零泄漏
    assert manager.leases[-1].network_policy == "deny_all"
    GradingReport.model_validate(report.model_dump(mode="json"))
    _assert_no_leftover_containers(manager)


async def test_grade_tests_failed_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_STILL_BROKEN)  # 改了但没修好
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-testsfail",
        workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image),
    )
    assert report.outcome == "unresolved"
    assert report.failure_category == "tests_failed"
    assert report.reward == 0.0
    assert report.f2p_pass_count == 0 and report.f2p_total_count == 1
    assert "FAILED tests/test_thing.py::test_feature" in _read_eval_log(manager, report)
    _assert_no_leftover_containers(manager)


async def test_grade_patch_apply_failed_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """agent 在 workspace 里 commit 过：导出 diff 的上下文基线漂移，clean base 上 apply 失败。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text('def feature():\n    return "committed change"\n')
    git_in(ws, "add", "-A")
    git_in(ws, "commit", "-q", "-m", "agent local commit")
    (ws / "src" / "thing.py").write_text('def feature():\n    return "post-commit edit"\n')
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-applyfail",
        workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image),
    )
    assert report.outcome == "unresolved"
    assert report.failure_category == "patch_apply_failed"
    assert report.reward == 0.0
    assert report.f2p_pass_count is None  # 测试未运行，四计数缺席
    assert report.patch_hygiene is not None and report.patch_hygiene.verdict == "clean"
    _assert_no_leftover_containers(manager)


# ---------------------------------------------------------------------------
# 故障注入：篡改 / 污染 / 日志不可解析 / 杀容器 / 超时
# ---------------------------------------------------------------------------


async def test_tampered_tests_downgraded_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """篡改测试文件 + 真实修复并存：篡改段被剥离、真实测试照跑，结论封顶 unresolved。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    (ws / "tests" / "test_thing.py").write_text(
        TEST_FILE_CONTENT.replace("ok = check()", "ok = True")  # 让测试永远通过的企图
    )
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-tamper",
        workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image),
    )
    assert report.patch_hygiene is not None
    assert report.patch_hygiene.verdict == "rejected_test_tampering"
    assert report.patch_hygiene.test_files_modified is True
    assert report.outcome == "unresolved" and report.reward == 0.0  # A7：被拒 patch 无满分
    assert report.failure_category == "tests_failed"
    assert report.f2p_pass_count == 1  # 剥离后 cleaned patch 真实通过——封顶但不伪造计数
    # 评分用的是 clean checkout 的原版测试文件（篡改企图从未进评分容器）
    log_text = _read_eval_log(manager, report)
    assert "PASSED tests/test_thing.py::test_feature" in log_text
    _assert_no_leftover_containers(manager)


async def test_contamination_downgraded_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """grader-only 路径污染（未跟踪新文件形态）：检出、剥离、降级。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    (ws / "grader").mkdir()
    (ws / "grader" / "secret.txt").write_text("planted\n")
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-pollute",
        workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image),
    )
    assert report.patch_hygiene is not None
    assert report.patch_hygiene.verdict == "rejected_forbidden_contamination"
    assert report.patch_hygiene.forbidden_paths == ["grader/secret.txt"]
    assert report.outcome == "unresolved" and report.reward == 0.0
    _assert_no_leftover_containers(manager)


async def test_unparseable_log_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """日志不可解析（标记在、内容垃圾）→ test_log_parse_failed 且 reward=None。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-garbage",
        workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image, eval_script=GARBAGE_EVAL_SCRIPT),
    )
    assert report.outcome == "failed_to_grade"
    assert report.failure_category == "test_log_parse_failed"
    assert report.reward is None
    assert report.infra_failure_detail == "eval_log_zero_parsed_tests"
    assert report.f2p_total_count is None
    _assert_no_leftover_containers(manager)


async def test_killed_grading_container_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """杀评分容器 → infra_failure（reward=None），trace 不丢（报告照常产出）。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _make_manager(tmp_path)
    traj = f"traj-kill-{uuid.uuid4().hex[:6]}"
    grade_task = asyncio.create_task(
        manager.grade(
            trajectory_id=traj,
            workspace=HostWorkspace(ws),
            spec=_spec(
                fixture_repo, fixture_image,
                eval_script=SLOW_EVAL_SCRIPT, test_timeout_seconds=120.0,
            ),
        )
    )
    # 等评分容器进入 eval 段（SLOW_EVAL 先 touch /rh2/eval_started 再长睡）
    container_id = ""
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ps = _docker(
            "ps", "--filter", f"label={manager.config.label_prefix}.trajectory={traj}",
            "--format", "{{.ID}}",
        )
        container_id = ps.stdout.strip()
        if container_id:
            started = _docker("exec", container_id, "test", "-f", "/rh2/eval_started")
            if started.returncode == 0:
                break
        await asyncio.sleep(0.2)
    assert container_id, "评分容器迟迟未进入 eval 段"
    kill = _docker("rm", "-f", container_id)
    assert kill.returncode == 0
    report = await asyncio.wait_for(grade_task, timeout=60)
    assert report.outcome == "failed_to_grade"
    assert report.failure_category == "infra_failure"
    assert report.reward is None
    assert "grading_container_killed" in (report.infra_failure_detail or "")
    GradingReport.model_validate(report.model_dump(mode="json"))
    _assert_no_leftover_containers(manager)


async def test_segment_timeout_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """P3：manager 内部分段 timeout——eval 超时判 infra_failure 并写明超时段。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-timeout",
        workspace=HostWorkspace(ws),
        spec=_spec(
            fixture_repo, fixture_image,
            eval_script=SLOW_EVAL_SCRIPT, test_timeout_seconds=3.0,
        ),
    )
    assert report.outcome == "failed_to_grade"
    assert report.failure_category == "infra_failure"
    assert report.reward is None
    assert report.infra_failure_detail == "grading_test_timeout_after_3s"
    _assert_no_leftover_containers(manager)


# ---------------------------------------------------------------------------
# P1 孤儿清扫 / P6 快照只读 / P9 评分容器断网
# ---------------------------------------------------------------------------


async def test_orphan_sweep_real(fixture_image, tmp_path):
    """P1：启动清扫按 label 找孤儿——超龄外来容器清掉，年轻外来容器留下。"""

    now = int(time.time())
    suffix = uuid.uuid4().hex[:6]
    orphan_name = f"rh2-grading-orphan-{suffix}"
    fresh_name = f"rh2-grading-fresh-{suffix}"

    def _spawn(name: str, epoch: int) -> None:
        run = _docker(
            "run", "-d", "--network", "none",
            "--label", "rh2.grading.owner=stale-run",
            "--label", f"rh2.grading.trajectory={name}",
            "--label", f"rh2.grading.created_at_epoch={epoch}",
            "--name", name, fixture_image, "sleep", "infinity",
        )
        assert run.returncode == 0, run.stderr

    _spawn(orphan_name, now - 7200)  # 两小时前 → 孤儿
    _spawn(fresh_name, now)  # 刚创建 → 可能是并行 worker 的活容器
    try:
        manager = _make_manager(tmp_path, orphan_min_age_seconds=3600.0)
        removed = await manager.startup()
        assert removed, "启动清扫应至少移除一个孤儿容器"
        assert _docker("inspect", orphan_name).returncode != 0  # 孤儿已消失
        assert _docker("inspect", fresh_name).returncode == 0  # 年轻容器幸存
    finally:
        _docker("rm", "-f", orphan_name)
        _docker("rm", "-f", fresh_name)


async def test_snapshot_readonly_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """P6：共享快照以 :ro 挂载——评分容器内写入失败，宿主快照内容前后不变。"""

    before = _dir_content_digest(fixture_repo.path)
    probe_prelude = (
        "if touch /rh2/snapshot/.rh2_write_probe 2>/dev/null; "
        "then echo SNAPSHOT_WRITABLE; else echo SNAPSHOT_WRITE_DENIED; fi\n"
    )
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-rosnap",
        workspace=HostWorkspace(ws),
        spec=_spec(
            fixture_repo, fixture_image,
            eval_script=make_eval_script(fixture_repo.base_commit, extra_prelude=probe_prelude),
        ),
    )
    assert report.outcome == "resolved"  # 只读探针不影响正常评分
    log_text = _read_eval_log(manager, report)
    assert "SNAPSHOT_WRITE_DENIED" in log_text
    assert "SNAPSHOT_WRITABLE" not in log_text
    assert _dir_content_digest(fixture_repo.path) == before  # 共享底座未被任何评分改写
    _assert_no_leftover_containers(manager)


async def test_grading_network_isolated_real(fixture_repo, fixture_image, make_workspace, tmp_path):
    """P9：评分容器 --network none——容器内出网必须失败（deny_all 的行为证明）。"""

    net_prelude = (
        "(echo probe > /dev/tcp/1.1.1.1/80) 2>/dev/null "
        "&& echo NET_OPEN || echo NET_BLOCKED\n"
    )
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _make_manager(tmp_path)
    report = await manager.grade(
        trajectory_id="traj-netiso",
        workspace=HostWorkspace(ws),
        spec=_spec(
            fixture_repo, fixture_image,
            eval_script=make_eval_script(fixture_repo.base_commit, extra_prelude=net_prelude),
        ),
    )
    assert report.outcome == "resolved"
    log_text = _read_eval_log(manager, report)
    assert "NET_BLOCKED" in log_text
    assert manager.leases[-1].network_policy == "deny_all"
    _assert_no_leftover_containers(manager)
