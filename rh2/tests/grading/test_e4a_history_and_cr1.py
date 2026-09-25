"""第六组 E4a（E2/E4 Brief §2）：评分 manager 的容器历史有界；同文件的 CR1 诊断余项（manager_cleanup_review_20260920 §3）。

E4a：删除已确认的记录按**确认删除的完成顺序**退役，只保留最近 `container_history_limit` 条；删除未获确认的记录永远
保留；租约随记录退役；累计数与保留长度分开。R6 的两个反例各有一案：早启动、最后完成的记录不被丢；历史已满 + 多条
活动记录时 close 全部清完（遍历快照、裁剪换新列表）。
CR1：exec 已交付输出与退出码之后，取消落在容器状态 inspect 或 tee 读取上，都不丢已交付的内容；tee 比已交付的输出短时
不覆盖（已知的 test 阶段不退回 install）。
"""

from __future__ import annotations

import asyncio
import re
import sys
import tempfile
from pathlib import Path

import pytest
from grading_fixtures import GOOD_FAKE_LOG, GOOD_PATCH, FakeWorkspace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_w3b_grader_profile_unit import BASE_COMMIT, ProfileGraderFakeDocker, _spec  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import make_grader_profile  # noqa: E402

from repoharness2.grading.manager import ExecResult, GradingManagerConfig, SWEGradingManager  # noqa: E402


class _Docker(ProfileGraderFakeDocker):
    """按容器名子串控制：`rm_fail_match` 的容器 rm 失败；`slow_match` 的容器候选测试多等 `slow_seconds`；
    `run_fail_match` 的容器 `docker run` 失败。"""

    def __init__(self, **kw):
        self.rm_fail_match: str | None = kw.pop("rm_fail_match", None)
        self.slow_match: str | None = kw.pop("slow_match", None)
        self.slow_seconds: float = kw.pop("slow_seconds", 0.0)
        self.run_fail_match: str | None = kw.pop("run_fail_match", None)
        super().__init__(base_commit=BASE_COMMIT, eval_log=kw.pop("eval_log", GOOD_FAKE_LOG), **kw)

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "rm" and self.rm_fail_match and self.rm_fail_match in args[-1]:
            return ExecResult(1, "", f"cannot remove {args[-1]}: fake failure")
        if args[0] == "run" and self.run_fail_match and any(self.run_fail_match in a for a in args):
            return ExecResult(1, "", "fake: daemon refused to create")
        if (args[0] == "exec" and self.slow_match and "-u" in args and str(args[-1]).startswith("bash ")
                and any(self.slow_match in a for a in args)):
            await asyncio.sleep(self.slow_seconds)
        return await super().__call__(*args, input_bytes=input_bytes)


def _manager(docker, *, limit: int, log_dir: Path | None = None) -> SWEGradingManager:
    return SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), container_history_limit=limit, eval_log_dir=log_dir),
        docker=docker,
    )


async def _grade(manager, traj: str):
    return await manager.grade(trajectory_id=traj, workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())


# ---- E4a ------------------------------------------------------------------------------------------------------------


async def test_history_stays_bounded_over_n_plus_50_grades_with_exact_totals_and_the_latest_facts():
    limit = 8
    docker = _Docker()
    manager = _manager(docker, limit=limit)
    for i in range(limit + 50):
        report = await _grade(manager, f"t{i}")
        assert report.outcome == "resolved"
        latest = manager.container_records[-1]
        # 刚完成的那一条事实完整可读（driver 与测试按 [-1] / 最近一条取）
        assert latest.trajectory_id == f"t{i}" and latest.removed and latest.parsed_verdict is not None
        assert latest.candidate_facts is not None and latest.lease is not None
        assert len(manager.container_records) <= limit
    assert len(manager.container_records) == limit and len(manager.leases) == limit
    assert [r.trajectory_id for r in manager.container_records] == [f"t{i}" for i in range(50, limit + 50)]
    closed = await manager.close()
    assert closed["containers_created_total"] == closed["containers_removed_total"] == limit + 50
    assert closed["leases_total"] == limit + 50 and closed["container_history_retained"] == limit
    assert closed["containers_open"] == [] and closed["cleanup_failures"] == []


async def test_default_limit_is_256():
    assert GradingManagerConfig().container_history_limit == 256


async def test_early_start_late_finish_is_kept_because_retirement_follows_completion_order():
    docker = _Docker(slow_match="slow", slow_seconds=0.3)
    manager = _manager(docker, limit=2)
    slow = asyncio.ensure_future(_grade(manager, "slow"))
    await asyncio.sleep(0.05)  # slow 先建容器
    for traj in ("fast-a", "fast-b"):
        assert (await _grade(manager, traj)).outcome == "resolved"
    assert (await slow).outcome == "resolved"
    kept = [r.trajectory_id for r in manager.container_records]
    assert "slow" in kept and "fast-b" in kept and "fast-a" not in kept  # 最早确认删除的是 fast-a
    assert manager.containers_created_total == manager.containers_removed_total == 3


async def test_close_with_full_history_and_several_active_records_removes_every_active_one():
    docker = _Docker(rm_fail_match="stuck")
    manager = _manager(docker, limit=3)
    for i in range(3):
        await _grade(manager, f"ok{i}")
    for i in range(3):  # 三条删除失败的活动记录（收口时 rm 失败；kill 后已停止 → 只留诊断，记录保持未删除）
        await _grade(manager, f"stuck{i}")
    active = [r.name for r in manager.container_records if not r.removed]
    assert len(active) == 3 and len(manager.container_records) == 6  # 活动记录超出上限也保留
    failures_before = len(manager.cleanup_failures)
    docker.rm_fail_match = None  # 之后清理成功
    closed = await manager.close()
    assert closed["containers_open"] == [] and sorted(closed["containers_removed"]) == sorted(active)
    assert len(manager.cleanup_failures) == failures_before  # 晚清成功不改累计的失败记录
    assert len(manager.container_records) == 3 and all(r.removed for r in manager.container_records)
    assert closed["containers_created_total"] == closed["containers_removed_total"] == 6


async def test_start_failure_records_without_logs_retire_too():
    docker = _Docker(run_fail_match="boom")
    manager = _manager(docker, limit=2)
    for i in range(3):
        report = await _grade(manager, f"boom{i}")
        assert report.outcome == "failed_to_grade"
    for i in range(2):
        await _grade(manager, f"ok{i}")
    assert [r.trajectory_id for r in manager.container_records] == ["ok0", "ok1"]
    assert manager.containers_created_total == manager.containers_removed_total
    assert manager.leases_total == 2  # 起不来的容器没有租约


async def test_regrade_declined_in_the_close_report_is_the_cumulative_count():
    manager = _manager(_Docker(), limit=2)
    manager.regrade_declined_total = 300  # 累计数与截到 256 条的列表分开
    manager.regrade_declined = [{}] * 256
    assert (await manager.close())["regrade_declined"] == 300


# ---- CR1 ------------------------------------------------------------------------------------------------------------

DELIVERED_LOG = (
    "RH2_PHASE_START=install\nRH2_INSTALL_RC=0\nRH2_PHASE_END=install\n"
    "RH2_TS_TEST_START=104.0\nDELIVERED_OUTPUT_PROBE=1\n"
)


class _PausingDocker(_Docker):
    """候选测试 exec 交付 137 之后，在 `pause_at`（容器状态 inspect / tee 读取）上挂住，等测试取消。"""

    def __init__(self, pause_at: str | None, **kw):
        super().__init__(eval_log=DELIVERED_LOG, eval_exit_code=137, container_running=False, **kw)
        self.pause_at = pause_at
        self.entered = asyncio.Event()
        self.exec_delivered = False

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if self.exec_delivered and (
            (self.pause_at == "inspect" and args[0] == "inspect" and "{{.State.Running}}" in args)
            or (self.pause_at == "partial_read" and args[0] == "exec" and "cat /rh2/candidate/eval.log" in args[-1])
        ):
            self.entered.set()
            await asyncio.Event().wait()
        result = await super().__call__(*args, input_bytes=input_bytes)
        if args[0] == "exec" and "| tee /rh2/candidate/eval.log" in args[-1]:
            self.exec_delivered = True
        return result


@pytest.mark.parametrize("pause_at", ["inspect", "partial_read"])
async def test_cancel_after_the_exec_delivered_keeps_its_output_and_exit_code(pause_at):
    docker = _PausingDocker(pause_at)
    with tempfile.TemporaryDirectory() as d:
        manager = _manager(docker, limit=4, log_dir=Path(d))
        task = asyncio.ensure_future(_grade(manager, "cr1"))
        await asyncio.wait_for(docker.entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        record = manager.container_records[-1]
        assert record.removed  # 取消照常传播、容器照常回收
        log = (Path(d) / f"{record.cancelled_eval_log_ref.ref_id}.eval.log").read_text()
        assert "DELIVERED_OUTPUT_PROBE=1" in log
        assert record.candidate_facts["candidate_exec_exit_code"] == 137


async def test_a_shorter_tee_does_not_replace_the_delivered_output_or_regress_the_phase():
    docker = _PausingDocker(None, inspect_fail="temporary daemon response failure")
    docker.candidate_partial_log = "RH2_PHASE_START=install\n"  # tee 只有安装段开头
    with tempfile.TemporaryDirectory() as d:
        manager = _manager(docker, limit=4, log_dir=Path(d))
        report = await _grade(manager, "short-tee")
        assert report.reward is None and "candidate_phase=test" in report.infra_failure_detail
        log = (Path(d) / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
        assert "DELIVERED_OUTPUT_PROBE=1" in log
        assert manager.container_records[-1].candidate_facts["candidate_exec_exit_code"] == 137


async def test_a_longer_tee_still_supplements_a_timed_out_exec():
    docker = _Docker(eval_delay=5.0)
    docker.candidate_partial_log = DELIVERED_LOG
    spec = _spec(test_timeout_seconds=0.2)
    manager = _manager(docker, limit=4)
    report = await manager.grade(trajectory_id="timeout", workspace=FakeWorkspace(GOOD_PATCH), spec=spec)
    assert report.reward is None and re.search(r"candidate_phase=test", report.infra_failure_detail)
    facts = manager.container_records[-1].candidate_facts
    assert facts["log_partial"] is True and facts["candidate_exec_exit_code"] is None  # exec 没返回：未记录到退出码


async def test_resource_closure_reports_retained_length_and_cumulative_total_separately():
    from repoharness2.shutdown.resource_closure import collect_growth_facts

    manager = _manager(_Docker(), limit=2)
    for i in range(5):
        await _grade(manager, f"t{i}")
    facts = collect_growth_facts(grading_manager=manager)
    assert facts["grading_manager_records"]["length"] == 2 and facts["grading_manager_records"]["total"] == 5
    assert facts["grading_manager_leases"]["length"] == 2 and facts["grading_manager_leases"]["total"] == 5
    assert facts["grading_manager_records"]["bounded"] is True
