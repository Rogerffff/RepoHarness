"""第六组 2A 真容器交接一次（network_supply_brief_20260924 §6 顺序第 2 步的"本机 Docker 一次正常交接"）。

宿主：假 PEP 503 上游 + 真实网关（aiohttp）+ 包供应 relay 容器；评分：真实 manager + grader profile + fixture 镜像。
候选安装段经 `pkgidx:3141` → relay → 网关 → 上游用 pip 下到 wheel，并 export 一个变量；宿主断网核对后测试段启动：
变量带到测试段、`pkgidx` 已不可达（§1 的 A 类事实：撤网后名字解析 / 连接都失败），测试照常判分。评分容器以 internal 网络
启动而不是 none（C 类事实决定的形状）。结束后没有残留的评分容器与网络，网关 token 已释放且终态摘要进了诊断。
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from conftest import requires_docker
from grading_fixtures import SRC_FIXED, make_candidate_test_script, make_fixture_spec

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402
from test_pkg_index_gateway import DEMO_WHEEL_NAME, FakeUpstream  # noqa: E402
from test_supply_relay import DOCKER_WITH_RELAY_IMAGE, _host_address_seen_from_containers  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway  # noqa: E402
from repoharness2.adapters.slime.prepared_task_face import SUPPLY_CARRY_RESTORE_LINES, SUPPLY_CARRY_TAIL_LINES  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    GraderSupplyConfig,
    GradingManagerConfig,
    HostWorkspace,
    SupplyPolicy,
    SWEGradingManager,
)

pytestmark = [pytest.mark.docker, requires_docker]

GRADER = make_grader_profile()
INSTALL_SCRIPT = (
    "#!/bin/bash\nset -xo pipefail\ncd /testbed\n"
    "echo RH2_PHASE_START=install\n"
    'python3 -m pip download --no-deps --no-cache-dir --disable-pip-version-check -d "$HOME/dl" rh2demo\n'
    "RH2_INSTALL_RC=$?\n"
    'echo "RH2_INSTALL_RC=$RH2_INSTALL_RC"\n'
    'echo "RH2_DOWNLOADED=$(ls "$HOME/dl" 2>/dev/null | tr \'\\n\' \',\')"\n'
    "export RH2_CARRIED=yes\n"
    "echo RH2_PHASE_END=install\n"
    + "\n".join(SUPPLY_CARRY_TAIL_LINES) + "\n"
)
NET_PROBE = (
    "python3 - <<'RH2_NET_EOF'\n"
    "import socket\n"
    "try:\n"
    "    socket.create_connection(('pkgidx', 3141), timeout=3).close(); print('RH2_TEST_NET=OPEN')\n"
    "except Exception as exc:\n"
    "    print('RH2_TEST_NET=DENIED:' + type(exc).__name__)\n"
    "RH2_NET_EOF\n"
)
TEST_AFTER_INSTALL = make_candidate_test_script(
    extra_prelude="\n".join(SUPPLY_CARRY_RESTORE_LINES) + "\n" + 'echo "RH2_CARRIED_SEEN=${RH2_CARRIED:-absent}"\n' + NET_PROBE,
)


@pytest.mark.skipif(not DOCKER_WITH_RELAY_IMAGE, reason="本机 docker 不可用或没有钉死的 relay 镜像（测试不拉镜像）")
async def test_real_install_through_the_gateway_then_withdraw_then_offline_tests(fixture_repo, fixture_image, make_workspace,
                                                                                 tmp_path):
    docker = sp.default_docker_runner
    upstream = FakeUpstream()
    await upstream.start()
    gateway = PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{upstream.port}/simple/", log_path=tmp_path / "gw.jsonl")
    gateway_port = await gateway.start("0.0.0.0", 0)
    run_id = f"supply2st-{uuid.uuid4().hex[:8]}"
    relay = None
    try:
        host = await asyncio.to_thread(_host_address_seen_from_containers, gateway_port)
        rollout = make_rollout_profile(model_proxy_upstream_host=host, model_proxy_upstream_port=gateway_port)
        relay = await sp.start_supply_relay(docker, rollout, gateway_host=host, gateway_port=gateway_port, run_id=run_id,
                                            labels=("--label", f"rh2.run_id={run_id}"))
        supply = GraderSupplyConfig(gateway=gateway, relay=relay, network_profile=rollout,
                                    subnet_pool=sp.EgressSubnetPool(rollout.egress_subnet_pool, rollout.egress_subnet_prefix))
        manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=GRADER, supply=supply))
        ws = make_workspace()
        (ws / "src" / "thing.py").write_text(SRC_FIXED)
        spec = make_fixture_spec(
            fixture_repo.base_commit, fixture_image, snapshot_host_path=str(fixture_repo.path),
            candidate_install_script=INSTALL_SCRIPT, candidate_test_after_install_script=TEST_AFTER_INSTALL,
            supply_policy=SupplyPolicy(blocked_dists=("rh2blocked",)),
        )
        report = await manager.grade(trajectory_id="supply-2stage", workspace=HostWorkspace(ws), spec=spec)
        record = manager.container_records[-1]
        log = (tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
        assert report.outcome == "resolved" and report.reward == 1.0, (report.infra_failure_detail, log[-2000:])
        assert "\nRH2_INSTALL_RC=0\n" in log and f"RH2_DOWNLOADED={DEMO_WHEEL_NAME}," in log  # 安装段经网关取到 wheel
        assert "\nRH2_CARRIED_SEEN=yes\n" in log  # 导出变量带到测试段
        assert "\nRH2_TEST_NET=DENIED:" in log and "RH2_TEST_NET=OPEN" not in log  # 测试段 pkgidx 不可达
        facts = record.supply
        assert facts["install_shape"] == "handoff" and facts["withdrawal"]["ok"] and facts["withdrawal"]["networks_after"] == []
        assert facts["gateway"]["complete"] is True and facts["gateway"]["stats"]["decision:served_file"] >= 1
        assert record.lease.network_policy == "supply_install_then_none" and record.removed and record.supply_released
        rows = [json.loads(line) for line in (tmp_path / "gw.jsonl").read_text().splitlines() if line.strip()]
        assert {r["decision"] for r in rows if r.get("attempt_id") == record.name} >= {"served_page", "served_file"}
        leftover_nets = subprocess.run(["docker", "network", "ls", "--filter", f"name={record.name}-net", "--format", "{{.Name}}"],
                                       capture_output=True, text=True, timeout=60)
        assert leftover_nets.stdout.strip() == ""
        leftover = subprocess.run(["docker", "ps", "-a", "--filter", f"label={manager.config.label_prefix}.owner={manager.run_id}",
                                   "--format", "{{.ID}}"], capture_output=True, text=True, timeout=60)
        assert leftover.stdout.strip() == ""
    finally:
        if relay is not None:
            await sp.stop_egress_relay(docker, relay)
        await gateway.stop()
        await upstream.stop()
