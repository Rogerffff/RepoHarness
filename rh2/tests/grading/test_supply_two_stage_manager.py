"""第六组 2A：评分 manager 的两段执行生命周期（network_supply_brief_20260924 §4.1–§4.2.1；假 runner 各终点一次）。

启用供应（`GradingManagerConfig.supply`）且该题有安装段时：本次评分建 internal attempt 网络并接入包供应 relay → 容器以该
网络启动、启动前核对"恰好这张网络、恰好一个带路由的接口" → root 可信 setup / 权限布置照旧 → 安装 exec（候选身份，注入
包索引地址）→ 宿主断网并核对 `Networks == {}`、网关撤销并收齐终态摘要 → 只有核对成功且安装段正常交接才启动测试 exec。
收口时容器删除之后拆网络、释放 token。未启用供应、没有安装段的题（R2E 形态）照旧单 shell、全断网。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest
from grading_fixtures import GOOD_FAKE_LOG, GOOD_PATCH, FakeWorkspace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_w3b_grader_profile_unit import BASE_COMMIT, ProfileGraderFakeDocker, _spec  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    SUPPLY_INSTALL_CARRY_WRITE_FAILED,
    SUPPLY_INSTALL_EXITED_EARLY,
    SUPPLY_INSTALL_HANDOFF,
    ExecResult,
    GraderSupplyConfig,
    GradingManagerConfig,
    SandboxProfileViolation,
    SupplyPolicy,
    SWEGradingManager,
    grading_scripts_digest,
)

HANDOFF_LOG = "RH2_PHASE_START=install\nRH2_INSTALL_RC=0\nRH2_PHASE_END=install\nRH2_PHASE_CARRY=start\nRH2_PHASE_HANDOFF=1\n"
EARLY_EXIT_LOG = "RH2_PHASE_START=install\n+ exit 3\n"
CARRY_FAILED_LOG = "RH2_PHASE_START=install\nRH2_INSTALL_RC=0\nRH2_PHASE_END=install\nRH2_PHASE_CARRY=start\nRH2_PHASE_CARRY_FAILED=1\n"


class FakeGateway:
    def __init__(self) -> None:
        self.issued: list[tuple[str, object]] = []
        self.withdrawn: list[str] = []
        self.released: list[str] = []

    def issue(self, grant) -> str:
        token = f"tok{len(self.issued)}"
        self.issued.append((token, grant))
        return token

    @staticmethod
    def index_path(token: str) -> str:
        return f"/a/{token}/simple/"

    def withdraw(self, token: str) -> bool:
        self.withdrawn.append(token)
        return True

    async def release(self, token: str, *, timeout: float = 10.0) -> dict:
        self.released.append(token)
        return {"token_ref": "ref", "complete": True, "inflight_unfinished": 0, "stats": {"requests": 3, "bytes": 42}}


class SupplyDocker(ProfileGraderFakeDocker):
    """profile 路径替身 + 两段执行：`.install` 脚本的 exec 返回 install_log；`tee -a` 的测试 exec 返回 eval_log；
    宿主对评分容器的 `network disconnect` 与 `inspect … NetworkSettings.Networks` 模拟撤网核对。"""

    def __init__(self, *, install_log: str = HANDOFF_LOG, install_exit_code: int = 0, withdraw_leaves_network: bool = False,
                 install_delay: float = 0.0, **kw) -> None:
        super().__init__(base_commit=BASE_COMMIT, eval_log=kw.pop("eval_log", GOOD_FAKE_LOG), **kw)
        self.profile_fake.rollout_profile = make_rollout_profile()
        self.install_log, self.install_exit_code, self.install_delay = install_log, install_exit_code, install_delay
        self.withdraw_leaves_network = withdraw_leaves_network
        self.withdrawn: set[str] = set()
        self.install_env: list[str] = []
        self.order: list[str] = []

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec" and "rh2-sandbox-script: grader-prelaunch-probe" in str(args[-1]):
            # 探针事实随容器实际的网络：接在 attempt 网络上的有一个带路由的接口，全断网的没有
            name = args[args.index("bash") - 1]
            run_args = self.profile_fake.run_args_by_name[name]
            on_net = run_args[run_args.index("--network") + 1] != "none"
            self.profile_fake.grader_probe_overrides = {"ROUTED_IFACES": "eth0,"} if on_net else {}
        if args[0] == "exec" and ".install 2>&1" in str(args[-1]):
            self.order.append("install_exec")
            self.install_env = [args[i + 1] for i, a in enumerate(args) if a == "-e"]
            if self.install_delay:
                await asyncio.sleep(self.install_delay)
            return ExecResult(self.install_exit_code, self.install_log, "")
        if args[0] == "exec" and "tee -a" in str(args[-1]):
            self.order.append("test_exec")
        elif args[0] == "exec" and str(args[-1]).startswith("bash ") and "-u" in args:
            self.order.append("single_shell_exec")
        if args[0] == "network" and args[1] == "disconnect" and args[-1].startswith("rh2-grading"):
            self.order.append("withdraw")
            self.withdrawn.add(args[-1])
            return ExecResult(0, "", "")
        if args[0] == "inspect" and "{{json .NetworkSettings.Networks}}" in args:
            name = args[-1]
            gone = name in self.withdrawn and not self.withdraw_leaves_network
            return ExecResult(0, "{}\n" if gone else json.dumps({f"{name}-net": {}}) + "\n", "")
        if args[0] == "run":
            self.order.append("run:" + args[args.index("--network") + 1])
        if args[0] == "network" and args[1] in ("create", "connect", "rm"):
            self.order.append(f"network_{args[1]}")
        return await super().__call__(*args, input_bytes=input_bytes)


RELAY = sp.EgressRelayHandle(container_name="rh2-supply-relay-run1", alias=sp.SUPPLY_RELAY_ALIAS,
                             listen_map=((3141, "host.docker.internal", 4000),), image=sp.RELAY_IMAGE_DEFAULT, run_id="run1")
POLICY = SupplyPolicy(blocked_dists=("moto",))


def _supply(gateway: FakeGateway) -> GraderSupplyConfig:
    profile = make_rollout_profile()
    return GraderSupplyConfig(gateway=gateway, relay=RELAY, network_profile=profile,
                              subnet_pool=sp.EgressSubnetPool(profile.egress_subnet_pool, profile.egress_subnet_prefix))


def _two_stage_spec(**overrides):
    base = {"candidate_install_script": "# install\n", "candidate_test_after_install_script": "# test\n", "supply_policy": POLICY}
    base.update(overrides)
    return _spec(**base)


def _manager(docker, gateway: FakeGateway | None, tmp_path: Path | None = None) -> SWEGradingManager:
    return SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), supply=_supply(gateway) if gateway else None,
                             eval_log_dir=tmp_path),
        docker=docker,
    )


async def _grade(manager, spec=None, traj: str = "t-supply"):
    return await manager.grade(trajectory_id=traj, workspace=FakeWorkspace(GOOD_PATCH), spec=spec or _two_stage_spec())


async def test_normal_handoff_runs_install_then_withdraws_then_tests_and_cleans_up(tmp_path):
    docker, gateway = SupplyDocker(), FakeGateway()
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager)
    assert report.outcome == "resolved" and report.reward == 1.0
    net = next(o for o in docker.order if o.startswith("run:")).split(":", 1)[1]
    assert net.endswith("-net") and net != "none"
    seq = [o for o in docker.order if o in ("network_create", "network_connect", "install_exec", "withdraw", "test_exec", "network_rm")]
    assert seq == ["network_create", "network_connect", "install_exec", "withdraw", "test_exec", "network_rm"]
    # 安装 exec 拿到经 pkgidx 的索引地址（token 只在这一次 exec 的环境里）
    assert "PIP_INDEX_URL=http://pkgidx:3141/a/tok0/simple/" in docker.install_env and "PIP_TRUSTED_HOST=pkgidx" in docker.install_env
    grant = gateway.issued[0][1]
    assert grant.plane == "grading" and grant.phase == "install" and "moto" in grant.blocked_dists
    assert gateway.withdrawn == ["tok0"] and gateway.released == ["tok0"]  # 撤网核对后撤销并收齐一次，收口不再重复
    record = manager.container_records[-1]
    facts = record.supply
    assert facts["install_shape"] == SUPPLY_INSTALL_HANDOFF and facts["withdrawal"]["ok"] is True
    assert facts["withdrawal"]["networks_after"] == [] and facts["test_exec_started"] is True
    assert facts["gateway"]["complete"] is True and "tok0" not in json.dumps(facts)  # 事实里没有 token 本身
    assert record.lease.network_policy == "supply_install_then_none" and record.supply_released
    assert net not in docker.profile_fake.networks and (net, RELAY.container_name) in docker.profile_fake.relay_disconnections
    diag = json.loads((tmp_path / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert diag["supply"]["install_shape"] == SUPPLY_INSTALL_HANDOFF
    assert diag["scripts_digest"] == grading_scripts_digest(_two_stage_spec(), two_stage=True) != grading_scripts_digest(_two_stage_spec())
    log = (tmp_path / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
    assert HANDOFF_LOG in log and ">>>>> Start Test Output" in log  # 安装输出 + 测试输出顺序拼接


async def _single_shell_equivalent(tmp_path, log: str, exit_code: int):
    """同一份候选输出在今天的单 shell 下的评分结论（对照：shell 已死、测试没跑）。"""
    docker = SupplyDocker(eval_log=log, eval_exit_code=exit_code)
    return await _grade(_manager(docker, None, tmp_path / "single"), spec=_two_stage_spec(supply_policy=None))


@pytest.mark.parametrize(("log", "exit_code", "shape"), [
    (EARLY_EXIT_LOG, 3, SUPPLY_INSTALL_EXITED_EARLY),
    (CARRY_FAILED_LOG, 0, SUPPLY_INSTALL_CARRY_WRITE_FAILED),
])
async def test_install_ending_without_handoff_skips_the_test_exec_like_a_dead_single_shell(tmp_path, log, exit_code, shape):
    docker, gateway = SupplyDocker(install_log=log, install_exit_code=exit_code), FakeGateway()
    report = await _grade(_manager(docker, gateway, tmp_path))
    assert "test_exec" not in docker.order and "withdraw" in docker.order  # 不跑测试段，但照样撤网
    single = await _single_shell_equivalent(tmp_path, log, exit_code)
    assert (report.outcome, report.reward, report.failure_category) == (single.outcome, single.reward, single.failure_category)
    assert report.reward != 1.0


async def test_install_shape_is_recorded_for_the_no_handoff_endings(tmp_path):
    docker, gateway = SupplyDocker(install_log=EARLY_EXIT_LOG, install_exit_code=3), FakeGateway()
    manager = _manager(docker, gateway, tmp_path)
    await _grade(manager)
    facts = manager.container_records[-1].supply
    assert facts["install_shape"] == SUPPLY_INSTALL_EXITED_EARLY and facts["install_exit_code"] == 3
    assert facts["test_exec_started"] is False and gateway.released == ["tok0"]


async def test_withdraw_verification_failure_is_typed_infra_and_never_starts_the_test_exec(tmp_path):
    docker, gateway = SupplyDocker(withdraw_leaves_network=True), FakeGateway()
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager)
    assert report.outcome == "failed_to_grade" and report.reward is None
    assert report.infra_failure_detail.startswith("grader_supply_withdraw_failed")
    assert "test_exec" not in docker.order
    record = manager.container_records[-1]
    assert record.supply["withdrawal"]["ok"] is False and gateway.withdrawn == ["tok0"] and gateway.released == ["tok0"]
    assert record.removed and record.supply_released  # 容器照常收口，token 在收口里释放


async def test_install_timeout_is_infra_in_the_install_phase_and_resources_are_released(tmp_path):
    docker, gateway = SupplyDocker(install_delay=5.0), FakeGateway()
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager, spec=_two_stage_spec(test_timeout_seconds=0.2))
    assert report.outcome == "failed_to_grade" and report.reward is None and "timeout" in report.infra_failure_detail
    assert "withdraw" not in docker.order and "test_exec" not in docker.order
    record = manager.container_records[-1]
    assert record.removed and record.supply_released and gateway.released == ["tok0"]
    assert not docker.profile_fake.networks  # attempt 网络已拆


async def test_cancel_during_install_propagates_and_releases_network_and_token(tmp_path):
    docker, gateway = SupplyDocker(install_delay=30.0), FakeGateway()
    manager = _manager(docker, gateway, tmp_path)
    task = asyncio.ensure_future(_grade(manager))
    for _ in range(200):
        await asyncio.sleep(0.01)
        if "install_exec" in docker.order:
            break
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    record = manager.container_records[-1]
    assert record.removed and record.supply_released and gateway.released == ["tok0"]
    assert not docker.profile_fake.networks and "test_exec" not in docker.order


async def test_a_task_without_an_install_segment_grades_single_shell_without_network_even_with_supply_enabled(tmp_path):
    docker, gateway = SupplyDocker(), FakeGateway()
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager, spec=_spec())  # R2E 形态：没有两段脚本
    assert report.outcome == "resolved"
    assert "run:none" in docker.order and "network_create" not in docker.order and "single_shell_exec" in docker.order
    assert gateway.issued == [] and manager.container_records[-1].lease.network_policy == "deny_all"


async def test_missing_supply_policy_is_run_halt_before_any_container():
    docker, gateway = SupplyDocker(), FakeGateway()
    manager = _manager(docker, gateway)
    with pytest.raises(SandboxProfileViolation, match="grader_supply_policy_missing"):
        await _grade(manager, spec=_two_stage_spec(supply_policy=None))
    assert not any(o.startswith("run:") for o in docker.order) and manager.container_records == ()


async def test_supply_disabled_keeps_the_default_single_shell_and_no_network(tmp_path):
    docker = SupplyDocker()
    manager = _manager(docker, None, tmp_path)
    report = await _grade(manager)
    assert report.outcome == "resolved" and "run:none" in docker.order and "single_shell_exec" in docker.order
    assert "install_exec" not in docker.order and manager.container_records[-1].supply is None


async def test_network_creation_failure_is_infra_and_no_container_is_started(tmp_path):
    docker, gateway = SupplyDocker(), FakeGateway()
    docker.profile_fake.network_create_fail = "Error response from daemon: boom"
    manager = _manager(docker, gateway, tmp_path)
    report = await _grade(manager)
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail.startswith("grader_supply_network_failed")
    assert not any(o.startswith("run:") for o in docker.order) and gateway.issued == []


async def test_missing_supply_relay_is_run_halt(tmp_path):
    docker, gateway = SupplyDocker(), FakeGateway()
    docker.profile_fake.relay_missing = True
    manager = _manager(docker, gateway, tmp_path)
    with pytest.raises(SandboxProfileViolation, match="grader_supply_relay_unavailable"):
        await _grade(manager)
    assert not docker.profile_fake.networks  # 已建的网络在收口时拆掉
