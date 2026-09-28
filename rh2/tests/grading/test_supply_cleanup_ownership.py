"""AR2 / O1（Codex review_a_remainder_20260928）：包供应的收尾在取消下不丢责任方，最终事实进落盘 sidecar。

真实 manager + 真实 `PackageIndexGateway.release`（不起 HTTP 服务），Docker 用两段执行的替身。为确定性命中"release 正在等
在途请求"的窗口，网关签发时往真实 inflight 集合放一条吞掉取消的任务（与 Codex tracer 同一手法）。三个取消位置：
正常阶段的 release、安装超时后收尾里的 release、收尾里的网络拆除。每案最终要么资源归零，要么句柄仍在、事实写明未完成，
重复 close 不假称完成。另核 sidecar 能区分：摘要完整 / 在途没收齐 / 被打断 / 根本没签发 token。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_supply_two_stage_manager import RELAY, SupplyDocker, _grade, _two_stage_spec  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway  # noqa: E402
from repoharness2.grading.manager import GraderSupplyConfig, GradingManagerConfig, SWEGradingManager  # noqa: E402

FAST = {"release_timeout_seconds": 0.3, "teardown_timeout_seconds": 0.3, "withdraw_timeout_seconds": 5.0}


class HeldGateway(PackageIndexGateway):
    """真实网关；`hold=True` 时每枚 token 签发后带一条"被撤销后仍不收尾"的在途任务，让 release 真的在等。"""

    def __init__(self, *, hold: bool) -> None:
        super().__init__(upstream_simple_url="http://127.0.0.1:1/simple/")
        self.hold = hold
        self.release_entered = asyncio.Event()
        self.let_go = asyncio.Event()
        self.held: list[asyncio.Task] = []

    def issue(self, grant):
        token = super().issue(grant)
        if self.hold:
            state = self._tokens[token]

            async def stubborn():
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    await self.let_go.wait()
                finally:
                    state.inflight.discard(asyncio.current_task())

            task = asyncio.ensure_future(stubborn())
            state.inflight.add(task)
            self.held.append(task)
        return token

    async def release(self, token, *, timeout=10.0):
        self.release_entered.set()
        return await super().release(token, timeout=timeout)

    async def finish(self):
        self.let_go.set()
        await asyncio.gather(*self.held, return_exceptions=True)


class PausingTeardownDocker(SupplyDocker):
    """收尾拆网时断开包供应中转的那次调用挂住，直到 `resume`。"""

    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self.teardown_entered = asyncio.Event()
        self.resume = asyncio.Event()
        self.teardown_calls = 0

    async def __call__(self, *args: str, input_bytes: bytes | None = None):
        if args[:2] == ("network", "disconnect") and args[-1] == RELAY.container_name:
            self.teardown_calls += 1
            self.teardown_entered.set()
            await self.resume.wait()
        return await super().__call__(*args, input_bytes=input_bytes)


def _manager(docker, gateway, log_dir: Path, *, history_limit: int = 256) -> SWEGradingManager:
    rollout = make_rollout_profile()
    supply = GraderSupplyConfig(gateway=gateway, relay=RELAY, network_profile=rollout,
                                subnet_pool=sp.EgressSubnetPool(rollout.egress_subnet_pool, rollout.egress_subnet_prefix),
                                **FAST)
    return SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), supply=supply, eval_log_dir=log_dir,
                             container_history_limit=history_limit),
        docker=docker,
    )


def _resources(manager, docker, gateway) -> dict:
    return {"tokens": gateway.active_token_count(), "networks": len(docker.profile_fake.networks),
            "slots": len(manager.config.supply.subnet_pool._in_use)}


def _sidecar_supply(log_dir: Path, record) -> dict:
    ref = record.persisted_eval_log_ref or record.cancelled_eval_log_ref
    return json.loads((log_dir / f"{ref.ref_id}.diagnostics.json").read_text())["supply"]


async def _settle(manager) -> None:
    running = [t for t in manager._supply_cleanup_tasks if not t.done()]
    if running:
        await asyncio.wait(running, timeout=5)


# ---- 正控 -------------------------------------------------------------------------------------------------------------


async def test_normal_control_releases_everything_and_the_sidecar_says_so(tmp_path):
    docker, gateway = SupplyDocker(), HeldGateway(hold=False)
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager)
    assert report.outcome == "resolved"
    record = manager.container_records[-1]
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0} and record.supply_released
    side = _sidecar_supply(tmp_path, record)
    assert (side["token_release"], side["network_teardown"], side["cleanup"]) == ("released", "done", "done")
    assert side["gateway"]["complete"] is True


async def test_install_timeout_control_releases_everything_in_the_final_cleanup(tmp_path):
    docker, gateway = SupplyDocker(install_delay=5.0), HeldGateway(hold=False)
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager, spec=_two_stage_spec(test_timeout_seconds=0.2))
    assert report.outcome == "failed_to_grade"
    record = manager.container_records[-1]
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0}
    side = _sidecar_supply(tmp_path, record)  # O1：收尾在 sidecar 写出之后才做，事实补进了同一份文件
    assert (side["token_release"], side["network_teardown"], side["cleanup"]) == ("released", "done", "done")


async def test_a_failure_before_any_token_is_issued_is_recorded_as_not_issued(tmp_path):
    docker, gateway = SupplyDocker(setup_exit_code=3, setup_attest=None), HeldGateway(hold=False)
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager)
    assert report.outcome == "failed_to_grade" and "trusted_setup" in report.infra_failure_detail
    side = _sidecar_supply(tmp_path, manager.container_records[-1])
    assert (side["token_release"], side["network_teardown"], side["cleanup"]) == ("not_issued", "done", "done")
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0}


# ---- 三个取消位置 ------------------------------------------------------------------------------------------------------


async def test_cancel_during_the_normal_release_leaves_no_token_network_or_slot(tmp_path):
    docker, gateway = SupplyDocker(), HeldGateway(hold=True)
    manager = _manager(docker, gateway, tmp_path)
    task = asyncio.ensure_future(_grade(manager))
    await asyncio.wait_for(gateway.release_entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await _settle(manager)
    record = manager.container_records[-1]
    assert "test_exec" not in docker.order and record.removed
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0} and record.supply_released
    assert gateway.summary()["totals"]["tokens_release_interrupted"] == 1
    side = _sidecar_supply(tmp_path, record)
    assert (side["token_release"], side["cleanup"]) == ("release_interrupted", "done")
    closed = await manager.close()
    assert closed["supply_open"] == [] and not any("supply_resources_open" in f for f in closed["cleanup_failures"])
    await gateway.finish()


async def test_cancel_during_the_cleanup_release_after_a_timeout_still_finishes_the_cleanup(tmp_path):
    docker, gateway = SupplyDocker(install_delay=5.0), HeldGateway(hold=True)
    manager = _manager(docker, gateway, tmp_path)
    task = asyncio.ensure_future(_grade(manager, spec=_two_stage_spec(test_timeout_seconds=0.2)))
    await asyncio.wait_for(gateway.release_entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await _settle(manager)  # 收尾任务不随评分任务取消：release 到时（在途没收齐）→ 移除 token → 拆网
    record = manager.container_records[-1]
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0} and record.supply_released
    side = _sidecar_supply(tmp_path, record)
    assert (side["token_release"], side["network_teardown"], side["cleanup"]) == ("released_incomplete", "done", "done")
    assert side["gateway"]["complete"] is False and side["gateway"]["inflight_unfinished"] == 1
    assert f"supply_token_release_incomplete:{record.name}" in manager.cleanup_failures  # 没收齐就明说
    await gateway.finish()


async def test_cancel_during_network_teardown_lets_the_teardown_finish_once_docker_answers(tmp_path):
    docker, gateway = PausingTeardownDocker(), HeldGateway(hold=False)
    manager = _manager(docker, gateway, tmp_path)
    task = asyncio.ensure_future(_grade(manager))
    await asyncio.wait_for(docker.teardown_entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    docker.resume.set()
    await _settle(manager)
    record = manager.container_records[-1]
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0} and record.supply_released
    assert _sidecar_supply(tmp_path, record)["cleanup"] == "done"
    assert (await manager.close())["supply_open"] == []


async def test_a_teardown_that_never_answers_is_reported_open_and_repeated_close_does_not_claim_completion(tmp_path):
    docker, gateway = PausingTeardownDocker(), HeldGateway(hold=False)
    # 断开中转的调用不应答期间，中转仍接在网络上：真实守护进程拒绝删除（active endpoints）
    docker.profile_fake.network_rm_fail_for = ("*",)
    manager = _manager(docker, gateway, tmp_path)
    task = asyncio.ensure_future(_grade(manager))
    await asyncio.wait_for(docker.teardown_entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    first = await manager.close()  # 拆网调用一直不返回：有界超时后记失败，句柄仍在
    record = manager.container_records[-1]
    [open_item] = first["supply_open"]
    assert open_item["container"] == record.name and open_item["network"] is not None and not record.supply_released
    assert any(f.startswith(f"supply_resources_open_at_close:{record.name}") for f in first["cleanup_failures"])
    assert _sidecar_supply(tmp_path, record)["cleanup"] == "incomplete"
    assert len(docker.profile_fake.networks) == 1 and len(manager.config.supply.subnet_pool._in_use) == 1
    docker.profile_fake.network_rm_fail_for = ()
    docker.resume.set()  # 守护进程恢复应答后，再次 close 会重试收尾并如实变为清空
    second = await manager.close()
    assert second["supply_open"] == [] and record.supply_released
    assert _resources(manager, docker, gateway) == {"tokens": 0, "networks": 0, "slots": 0}
    assert _sidecar_supply(tmp_path, record)["cleanup"] == "done"


async def test_history_trimming_keeps_a_record_whose_supply_resources_are_still_open(tmp_path):
    docker, gateway = PausingTeardownDocker(), HeldGateway(hold=False)
    manager = _manager(docker, gateway, tmp_path, history_limit=1)
    task = asyncio.ensure_future(_grade(manager, traj="stuck"))
    await asyncio.wait_for(docker.teardown_entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await _settle(manager)  # 拆网超时：网络句柄仍在
    stuck = next(r for r in manager.container_records if r.trajectory_id == "stuck")
    assert stuck.supply_network is not None
    docker.teardown_entered.clear()
    for i in range(3):  # 之后的评分拆网也会先挂住：放行后才完成
        t = asyncio.ensure_future(_grade(manager, traj=f"later{i}"))
        await asyncio.wait_for(docker.teardown_entered.wait(), 5)
        docker.resume.set()
        await t
        docker.resume.clear()
        docker.teardown_entered.clear()
    kept = [r.trajectory_id for r in manager.container_records]
    assert "stuck" in kept  # 历史上限是 1，但资源没收齐的记录不裁剪
    docker.resume.set()
    assert (await manager.close())["supply_open"] == []


# ---- 网关层 -----------------------------------------------------------------------------------------------------------


async def test_an_interrupted_gateway_release_still_removes_the_token():
    gateway = HeldGateway(hold=True)
    from repoharness2.adapters.slime.pkg_index_gateway import SupplyGrant

    token = gateway.issue(SupplyGrant.build(attempt_id="a", task_id="t", plane="grading", phase="install"))
    task = asyncio.ensure_future(gateway.release(token, timeout=30))
    await asyncio.wait_for(gateway.release_entered.wait(), 5)
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not gateway.is_issued(token) and gateway.active_token_count() == 0
    totals = gateway.summary()["totals"]
    assert totals["tokens_release_interrupted"] == 1 and totals["tokens_released_incomplete"] == 1
    assert await gateway.release(token) is None  # 已释放：不再出第二份摘要
    await gateway.finish()
