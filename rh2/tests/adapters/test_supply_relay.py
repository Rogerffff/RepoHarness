"""第六组 受控依赖供应（1A + 2A）：grader 安装段的包供应 relay（Brief §2 / §4.1；Codex 方向复核 §5.1）。

- 参数层：egress relay 的容器参数在抽出共用构造后逐字不变；包供应 relay 同镜像、同加固，但监听表只有网关一项。
- 启动层（替身 docker）：就绪探测看的是供应端口；镜像 digest 漂移 / 不就绪 / 起不来都按 `supply_relay_*` 失败并自清理。
- 真容器（本机 docker + 钉死的 relay 镜像在场才跑，不拉镜像）：一个接在 attempt internal 网络上的容器，经 `pkgidx:3141`
  → 包供应 relay → 宿主网关 → 假上游，用真实 pip 下到 wheel、被封禁项目拒绝；模型代理端口在这个 relay 上不存在；
  直连外网不可达。
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/：sandbox_test_support
from sandbox_test_support import make_rollout_profile  # noqa: E402
from test_pkg_index_gateway import DEMO_WHEEL_NAME, FakeUpstream  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.pkg_index_gateway import PackageIndexGateway, SupplyGrant  # noqa: E402
from repoharness2.grading.manager import ExecResult  # noqa: E402

_MIB = 1024 * 1024


# ---- 参数层 ---------------------------------------------------------------------------------------------------------


def test_egress_relay_args_are_unchanged_by_the_shared_builder():
    r = make_rollout_profile()
    relay_map = ",".join(f"{lp}:{host}:{up}" for lp, host, up in r.relay_listen_map())
    expected = [
        "run", "--detach", "--network", "bridge", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--read-only", "--user", "65534:65534", "--pids-limit", "64", "--memory", str(256 * _MIB),
        "--memory-swap", str(256 * _MIB), "--tmpfs", "/tmp:size=16777216,mode=1777",
        "--env", f"RH2_RELAY_MAP={relay_map}", "--label", "rh2.egress.relay=1", "--label", "rh2.run_id=x",
        "--name", "n", r.relay_image, "python3", "-c", sp._RELAY_SCRIPT,
    ]
    assert sp.relay_run_args(r, name="n", labels=("--label", "rh2.run_id=x")) == expected


def test_supply_relay_listens_only_on_the_gateway_entry_with_the_same_hardening():
    r = make_rollout_profile()
    labels = ("--label", "rh2.run_id=x")
    supply = sp.supply_relay_run_args(r, name="n", gateway_host="172.17.0.1", gateway_port=39999, labels=labels)
    envs = [supply[i + 1] for i, arg in enumerate(supply) if arg == "--env"]
    assert envs == ["RH2_RELAY_MAP=3141:172.17.0.1:39999"]  # 没有模型代理 / 其它内部服务
    assert "rh2.supply.relay=1" in supply and "rh2.egress.relay=1" not in supply

    def hardening(args: list[str]) -> list[str]:
        out, skip = [], False
        for i, arg in enumerate(args):
            if skip:
                skip = False
                continue
            if arg in ("--env",) or (arg == "--label" and args[i + 1].startswith("rh2.") and args[i + 1].endswith(".relay=1")):
                skip = True
                continue
            out.append(arg)
        return out

    assert hardening(supply) == hardening(sp.relay_run_args(r, name="n", labels=labels))
    for bad_host in ("", "::1", "a,b", "a b"):
        with pytest.raises(sp.SandboxProfileError, match="supply_relay_gateway_host_invalid"):
            sp.supply_relay_run_args(r, name="n", gateway_host=bad_host, gateway_port=1)
    for bad_port in (0, 70000, True):
        with pytest.raises(sp.SandboxProfileError, match="supply_relay_port_invalid"):
            sp.supply_relay_run_args(r, name="n", gateway_host="h", gateway_port=bad_port)


# ---- 启动层（替身 docker） ---------------------------------------------------------------------------------------------


class _RelayFake:
    def __init__(self, *, digests: tuple[str, ...] | None = None, never_ready: bool = False, run_fail: bool = False,
                 rm_fail: bool = False) -> None:
        self.digests = digests
        self.never_ready = never_ready
        self.run_fail = run_fail
        self.rm_fail = rm_fail
        self.calls: list[tuple[str, ...]] = []

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        cmd = args[0]
        if cmd == "run":
            return ExecResult(1, "", "pull access denied") if self.run_fail else ExecResult(0, "cid\n", "")
        if cmd == "exec":
            return ExecResult(1, "", "ConnectionRefusedError") if self.never_ready else ExecResult(0, "RH2_RELAY_LISTENING\n", "")
        if cmd == "inspect":
            return ExecResult(0, "sha256:relayimage\n", "")
        if cmd == "image":
            digests = self.digests if self.digests is not None else (make_rollout_profile().relay_image,)
            return ExecResult(0, json.dumps(list(digests)) + "\n", "")
        if cmd == "rm":
            return ExecResult(1, "", "device or resource busy") if self.rm_fail else ExecResult(0, "", "")
        raise AssertionError(f"未预期的 docker 调用：{args}")


async def test_supply_relay_start_probes_the_supply_port_and_returns_a_pkgidx_handle():
    fake = _RelayFake()
    r = make_rollout_profile()
    handle = await sp.start_supply_relay(fake, r, gateway_host="h", gateway_port=4000, run_id="run1",
                                         labels=("--label", "rh2.run_id=run1"))
    assert handle.container_name == "rh2-supply-relay-run1" and handle.alias == sp.SUPPLY_RELAY_ALIAS == "pkgidx"
    assert handle.listen_map == ((3141, "h", 4000),) and handle.repo_digests == (r.relay_image,)
    [probe] = [c for c in fake.calls if c[0] == "exec"]
    assert "('127.0.0.1',3141)" in probe[-1] and str(r.model_proxy_listen_port) not in probe[-1]


@pytest.mark.parametrize(
    ("fake", "code", "leftover"),
    [
        (_RelayFake(digests=("python@sha256:" + "1" * 64,)), "supply_relay_image_digest_mismatch", ()),
        (_RelayFake(never_ready=True), "supply_relay_not_ready", ()),
        (_RelayFake(never_ready=True, rm_fail=True), "supply_relay_not_ready", ("rh2-supply-relay-run2",)),
        (_RelayFake(run_fail=True), "supply_relay_start_failed", ()),
    ],
)
async def test_supply_relay_failures_are_typed_and_clean_up_after_themselves(fake, code, leftover):
    with pytest.raises(sp.SandboxNetworkError, match=code) as err:
        await sp.start_supply_relay(fake, make_rollout_profile(), gateway_host="h", gateway_port=4000, run_id="run2",
                                    ready_timeout=0.3)
    assert err.value.leftover_containers == leftover
    if code != "supply_relay_start_failed":
        assert any(c[0] == "rm" and c[-1] == "rh2-supply-relay-run2" for c in fake.calls)


# ---- 真容器 ----------------------------------------------------------------------------------------------------------


def _docker_ready_with_relay_image() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        probe = subprocess.run(["docker", "image", "inspect", sp.RELAY_IMAGE_DEFAULT], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


DOCKER_WITH_RELAY_IMAGE = _docker_ready_with_relay_image()


def _host_address_seen_from_containers(port: int) -> str:
    """容器视角的宿主地址：Docker Desktop = host.docker.internal；Linux 引擎 = docker0 网关 172.17.0.1。"""

    probe = (
        "import socket,sys\n"
        "for h in ('host.docker.internal','172.17.0.1'):\n"
        "    try:\n"
        f"        s=socket.create_connection((h,{port}),timeout=3); s.close(); print(h); sys.exit(0)\n"
        "    except Exception: pass\n"
        "sys.exit(1)\n"
    )
    res = subprocess.run(["docker", "run", "--rm", "--network", "bridge", sp.RELAY_IMAGE_DEFAULT, "python3", "-c", probe],
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, f"容器到不了宿主网关：{res.stderr[-300:]}"
    return res.stdout.strip()


@pytest.mark.docker
@pytest.mark.skipif(not DOCKER_WITH_RELAY_IMAGE, reason="本机 docker 不可用或没有钉死的 relay 镜像（测试不拉镜像）")
async def test_container_on_an_internal_network_reaches_only_the_gateway_through_the_supply_relay(tmp_path):
    docker = sp.default_docker_runner
    upstream = FakeUpstream()
    await upstream.start()
    gateway = PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{upstream.port}/simple/",
                                  log_path=tmp_path / "gw.jsonl")
    gateway_port = await gateway.start("0.0.0.0", 0)
    run_id = f"supplytest-{uuid.uuid4().hex[:8]}"
    labels = ("--label", f"rh2.run_id={run_id}")
    profile = relay = network = pool = None
    try:
        host = await asyncio.to_thread(_host_address_seen_from_containers, gateway_port)
        profile = make_rollout_profile(model_proxy_upstream_host=host, model_proxy_upstream_port=gateway_port)
        relay = await sp.start_supply_relay(docker, profile, gateway_host=host, gateway_port=gateway_port,
                                            run_id=run_id, labels=labels)
        pool = sp.EgressSubnetPool(profile.egress_subnet_pool, profile.egress_subnet_prefix)
        network = await sp.create_attempt_network(docker, profile=profile, pool=pool, name=f"rh2-supplynet-{run_id}",
                                                  labels=labels)
        await sp.connect_relay_to_network(docker, relay=relay, network=network)
        token = gateway.issue(SupplyGrant.build(attempt_id="att-docker", task_id="task-docker", plane="grading",
                                                phase="install", blocked_dists=["rh2blocked"]))
        alias, port = sp.SUPPLY_RELAY_ALIAS, sp.SUPPLY_RELAY_LISTEN_PORT
        index = f"http://{alias}:{port}{gateway.index_path(token)}"
        pip = f"pip download --no-deps --no-cache-dir --disable-pip-version-check --index-url {index} --trusted-host {alias}"
        script = (
            "python3 - <<'PY'\n"
            "import socket, urllib.request\n"
            "def probe(host, port):\n"
            "    try:\n"
            "        socket.create_connection((host, port), timeout=3).close(); return 'open'\n"
            "    except Exception as exc:\n"
            "        return type(exc).__name__\n"
            f"print('MODEL_PROXY_PORT=' + probe('{alias}', {profile.model_proxy_listen_port}))\n"
            "print('DIRECT_EGRESS=' + probe('1.1.1.1', 80))\n"
            f"print('PAGE=' + str(urllib.request.urlopen('{index}rh2demo/', timeout=20).status))\n"
            "PY\n"
            f"{pip} -d /tmp/ok rh2demo >/tmp/ok.log 2>&1; echo \"PIP_OK_RC=$?\"; ls /tmp/ok\n"
            f"{pip} -d /tmp/blocked rh2blocked >/tmp/blocked.log 2>&1; echo \"PIP_BLOCKED_RC=$?\"\n"
            "echo \"BLOCKED_MSG=$(grep -c 'No matching distribution found' /tmp/blocked.log)\"\n"
        )
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm", "--network", network.name, *labels, profile.relay_image, "bash", "-c", script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        text = out.decode(errors="replace")
        facts = dict(line.split("=", 1) for line in text.splitlines() if "=" in line and line.split("=", 1)[0].isupper())
        assert facts.get("PAGE") == "200", text
        assert facts.get("PIP_OK_RC") == "0" and DEMO_WHEEL_NAME in text, text
        assert facts.get("PIP_BLOCKED_RC") not in (None, "0") and facts.get("BLOCKED_MSG") not in (None, "0"), text
        assert facts.get("MODEL_PROXY_PORT") not in (None, "open"), text  # 包供应 relay 上没有模型代理端口
        assert facts.get("DIRECT_EGRESS") not in (None, "open"), text
        rows = [json.loads(line) for line in (tmp_path / "gw.jsonl").read_text().splitlines()]
        served = {r["decision"] for r in rows if r.get("attempt_id") == "att-docker"}
        assert {"served_page", "served_file", "blocked_by_policy"} <= served
        assert token not in (tmp_path / "gw.jsonl").read_text()
        assert upstream.saw("/simple/rh2blocked") == []
    finally:
        if network is not None:
            await sp.teardown_attempt_network(docker, network_name=network.name, relay=relay, pool=pool,
                                              subnet=network.subnet)
        if relay is not None:
            assert await sp.stop_egress_relay(docker, relay) == []
        await gateway.stop()
        await upstream.stop()
    leftovers = subprocess.run(["docker", "ps", "-a", "--filter", f"label=rh2.run_id={run_id}", "--format", "{{.Names}}"],
                               capture_output=True, text=True, timeout=60)
    assert leftovers.stdout.strip() == ""


# ---- 撤出口：断开 + inspect 核对（Brief §4.1 第 4 步） -------------------------------------------------------------------


class _WithdrawFake:
    def __init__(self, *, disconnect: ExecResult, inspect: ExecResult) -> None:
        self.disconnect, self.inspect = disconnect, inspect
        self.calls: list[tuple[str, ...]] = []

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        if args[:2] == ("network", "disconnect"):
            return self.disconnect
        if args[0] == "inspect":
            return self.inspect
        raise AssertionError(f"未预期的 docker 调用：{args}")


@pytest.mark.parametrize(
    ("disconnect", "inspect", "ok", "after", "has_disconnect_error", "has_inspect_error"),
    [
        (ExecResult(0, "", ""), ExecResult(0, "{}\n", ""), True, (), False, False),
        # 先前已断开：断开报错但核对为空 → 仍 ok，报错原文留痕
        (ExecResult(1, "", "container c is not connected to network n"), ExecResult(0, "{}\n", ""), True, (), True, False),
        (ExecResult(0, "", ""), ExecResult(0, '{"rh2-net":{"IPAddress":"10.212.0.2"}}\n', ""), False, ("rh2-net",), False, False),
        (ExecResult(0, "", ""), ExecResult(0, '{"none":{}}\n', ""), False, ("none",), False, False),
        (ExecResult(0, "", ""), ExecResult(1, "", "Error: No such object: c"), False, None, False, True),
        (ExecResult(0, "", ""), ExecResult(0, "null\n", ""), False, None, False, True),
        (ExecResult(124, "", "docker network disconnect 超时"), ExecResult(0, "garbage", ""), False, None, True, True),
    ],
)
async def test_withdraw_is_ok_only_when_inspect_shows_no_network_left(disconnect, inspect, ok, after, has_disconnect_error,
                                                                      has_inspect_error):
    fake = _WithdrawFake(disconnect=disconnect, inspect=inspect)
    result = await sp.withdraw_container_network(fake, container="c", network="n")
    assert result.ok is ok and result.networks_after == after
    assert (result.disconnect_error is not None) is has_disconnect_error
    assert (result.inspect_error is not None) is has_inspect_error
    assert fake.calls[0] == ("network", "disconnect", "n", "c")
    assert fake.calls[1] == ("inspect", "-f", "{{json .NetworkSettings.Networks}}", "c")  # 不重试、不重连
    assert len(fake.calls) == 2 and result.to_dict()["ok"] is ok


@pytest.mark.docker
@pytest.mark.skipif(not DOCKER_WITH_RELAY_IMAGE, reason="本机 docker 不可用或没有钉死的 relay 镜像（测试不拉镜像）")
async def test_withdraw_cuts_a_running_container_off_the_gateway_for_good(tmp_path):
    docker = sp.default_docker_runner
    upstream = FakeUpstream()
    await upstream.start()
    gateway = PackageIndexGateway(upstream_simple_url=f"http://127.0.0.1:{upstream.port}/simple/",
                                  log_path=tmp_path / "gw.jsonl")
    gateway_port = await gateway.start("0.0.0.0", 0)
    run_id = f"withdrawtest-{uuid.uuid4().hex[:8]}"
    labels = ("--label", f"rh2.run_id={run_id}")
    container = f"rh2-withdraw-{run_id}"
    relay = network = pool = None
    try:
        host = await asyncio.to_thread(_host_address_seen_from_containers, gateway_port)
        profile = make_rollout_profile(model_proxy_upstream_host=host, model_proxy_upstream_port=gateway_port)
        relay = await sp.start_supply_relay(docker, profile, gateway_host=host, gateway_port=gateway_port,
                                            run_id=run_id, labels=labels)
        pool = sp.EgressSubnetPool(profile.egress_subnet_pool, profile.egress_subnet_prefix)
        network = await sp.create_attempt_network(docker, profile=profile, pool=pool, name=f"rh2-wdnet-{run_id}",
                                                  labels=labels)
        await sp.connect_relay_to_network(docker, relay=relay, network=network)
        started = await docker("run", "--detach", "--init", "--network", network.name, *labels, "--name", container,
                               profile.relay_image, "sleep", "300")
        assert started.exit_code == 0, started.stderr
        token = gateway.issue(SupplyGrant.build(attempt_id="att-wd", task_id="task-wd", plane="grading", phase="install"))
        url = f"http://{sp.SUPPLY_RELAY_ALIAS}:{sp.SUPPLY_RELAY_LISTEN_PORT}{gateway.index_path(token)}rh2demo/"
        fetch = ("import sys, urllib.request\n"
                 "try:\n"
                 f"    print('STATUS=' + str(urllib.request.urlopen('{url}', timeout=5).status))\n"
                 "except Exception as exc:\n"
                 "    print('ERROR=' + type(exc).__name__ + ':' + str(getattr(exc, 'reason', exc))[:80])\n")
        before = await docker("exec", container, "python3", "-c", fetch)
        assert "STATUS=200" in before.stdout, before.stdout + before.stderr
        result = await sp.withdraw_container_network(docker, container=container, network=network.name)
        assert result.ok and result.networks_after == () and result.disconnect_error is None, result
        after = await docker("exec", container, "python3", "-c", fetch)
        assert "ERROR=" in after.stdout and "STATUS=" not in after.stdout, after.stdout + after.stderr
        again = await sp.withdraw_container_network(docker, container=container, network=network.name)
        assert again.ok and again.disconnect_error is not None  # 再撤一次：断开报"未连接"，核对仍为空
    finally:
        await docker("rm", "-f", container)
        if network is not None:
            await sp.teardown_attempt_network(docker, network_name=network.name, relay=relay, pool=pool,
                                              subnet=network.subnet)
        if relay is not None:
            await sp.stop_egress_relay(docker, relay)
        await gateway.stop()
        await upstream.stop()


# ---- NG2（Codex review_supply_components §2）：交出 handle 之前被取消 / 意外异常也按名字回收 ------------------------------------


class _GatedRelayFake(_RelayFake):
    """`gate` 那一步（run / readiness / inspect）一直阻塞到被取消；`exec_raises` 让就绪探测抛意外异常。"""

    def __init__(self, *, gate: str | None = None, rm_fail: bool = False, exec_raises: Exception | None = None) -> None:
        super().__init__(rm_fail=rm_fail)
        self.gate, self.exec_raises = gate, exec_raises
        self.entered = asyncio.Event()

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        step = {"run": "run", "exec": "readiness", "inspect": "inspect"}.get(args[0])
        if step is not None and step == self.gate:
            self.calls.append(args)
            self.entered.set()
            await asyncio.Event().wait()  # 永远阻塞，直到被取消
        if args[0] == "exec" and self.exec_raises is not None:
            self.calls.append(args)
            raise self.exec_raises
        return await super().__call__(*args, input_bytes=input_bytes)


@pytest.mark.parametrize("gate", ["run", "readiness", "inspect"])
async def test_cancel_before_the_handle_is_handed_over_reclaims_the_container_and_propagates(gate):
    fake = _GatedRelayFake(gate=gate)
    report: list[str] = []
    task = asyncio.ensure_future(sp.start_supply_relay(
        fake, make_rollout_profile(), gateway_host="h", gateway_port=4000, run_id="run3", cancel_report=report))
    await asyncio.wait_for(fake.entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert fake.calls[-1] == ("rm", "-f", "rh2-supply-relay-run3") and report == []


async def test_failed_reclaim_after_cancel_is_reported_with_the_container_name():
    fake = _GatedRelayFake(gate="readiness", rm_fail=True)
    report: list[str] = []
    task = asyncio.ensure_future(sp.start_egress_relay(fake, make_rollout_profile(), run_id="run4", cancel_report=report))
    await asyncio.wait_for(fake.entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(report) == 1 and report[0].startswith("relay_rm_after_cancel:rh2-egress-relay-run4:")


@pytest.mark.parametrize("rm_fail", [False, True])
async def test_unexpected_exception_reclaims_and_keeps_the_original_error(rm_fail):
    fake = _GatedRelayFake(exec_raises=OSError("docker 通道断了"), rm_fail=rm_fail)
    with pytest.raises(OSError, match="docker 通道断了") as err:
        await sp.start_supply_relay(fake, make_rollout_profile(), gateway_host="h", gateway_port=4000, run_id="run5")
    assert ("rm", "-f", "rh2-supply-relay-run5") in fake.calls
    notes = getattr(err.value, "__notes__", [])
    assert (len(notes) == 1 and "残留 rh2-supply-relay-run5" in notes[0]) if rm_fail else notes == []


async def test_failed_docker_run_also_reclaims_a_possibly_created_container():
    fake = _RelayFake(run_fail=True)
    with pytest.raises(sp.SandboxNetworkError, match="supply_relay_start_failed") as err:
        await sp.start_supply_relay(fake, make_rollout_profile(), gateway_host="h", gateway_port=4000, run_id="run6")
    assert ("rm", "-f", "rh2-supply-relay-run6") in fake.calls and err.value.leftover_containers == ()


@pytest.mark.docker
@pytest.mark.skipif(not DOCKER_WITH_RELAY_IMAGE, reason="本机 docker 不可用或没有钉死的 relay 镜像（测试不拉镜像）")
async def test_real_docker_cancel_while_waiting_for_readiness_removes_the_created_relay():
    run_id = f"relaycancel-{uuid.uuid4().hex[:8]}"
    name = f"rh2-supply-relay-{run_id}"
    entered = asyncio.Event()

    async def slow_readiness(*args: str, input_bytes: bytes | None = None):
        if args[0] == "exec" and "RH2_RELAY_LISTENING" in args[-1]:
            entered.set()
            await asyncio.sleep(120)
        return await sp.default_docker_runner(*args, input_bytes=input_bytes)

    report: list[str] = []
    task = asyncio.ensure_future(sp.start_supply_relay(
        slow_readiness, make_rollout_profile(), gateway_host="127.0.0.1", gateway_port=9, run_id=run_id,
        labels=("--label", f"rh2.run_id={run_id}"), cancel_report=report))
    try:
        await asyncio.wait_for(entered.wait(), 120)
        running = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name], capture_output=True, text=True, timeout=60)
        assert running.stdout.strip() == "true"  # 真实容器已建出、handle 尚未交出
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        left = subprocess.run(["docker", "ps", "-a", "--filter", f"label=rh2.run_id={run_id}", "--format", "{{.Names}}"],
                              capture_output=True, text=True, timeout=60)
        assert left.stdout.strip() == "" and report == []
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)

