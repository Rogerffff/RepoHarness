"""W3b（决策包 D2-2 / D2-4）：唯一正式 rollout Docker profile + 独立 grader profile ——
创建期强制 + 启动前核对 + run 级记录。本文件是**不需要 docker** 的一半（纯函数 + 替身链）；
真实容器行为在 tests/adapters/test_w3b_sandbox_docker.py（@docker）与 tests/grading/test_w3b_grader_profile_docker.py。

覆盖：
- profile 参数校验 / env 解析 / digest 确定性 / docker run 参数只由 profile 组装（无可选安全开关）；
- 纯核对函数：inspect 与探针的每个必需项各一个"未生效即拦"负例；
- 子网池：Pool overlaps 自动换槽、耗尽即错；
- 编排：fa_formal 缺 profile/relay/digest 启动即拒；正常链上 sanitize→trusted-init→prelaunch 先于 harness；
  样本 metadata 与 audit 记录盖 runtime_profile_digest；prelaunch 违规 → typed fatal + 容器与网络已清；
  relay 缺席 → fatal；网络创建瞬时失败 / sanitize 失败 → task-local abort；容器清理连带删网络；
- H7 探针脚本清单与 rh2/scripts/sandbox_probes 副本逐字一致；CLI list-probes 可用。
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_test_support import (  # noqa: E402
    TEST_RELAY,
    ProfileFakeState,
    formal_sandbox_kwargs,
    grader_probe_output,
    make_grader_profile,
    make_rollout_profile,
    rollout_probe_output,
    synthesize_inspect,
)
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    BASE_COMMIT,
    SAMPLING_PARAMS,
    FakeRolloutDocker,
    _Args,
    _formal_config,
    build_dense_chain,
    dense_turns,
)
from test_w1b_termination_facts_producer import _Barrier  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.generate import (  # noqa: E402
    RolloutOrchestrator,
    StartupCheckError,
    rh2_custom_generate,
)

REPO_RH2 = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# profile 定义 / env / digest / run 参数
# ---------------------------------------------------------------------------


def test_profile_parameters_and_digest_are_deterministic():
    a = make_rollout_profile()
    b = make_rollout_profile()
    assert a.digest() == b.digest() and a.digest().startswith("sha256:")
    assert make_rollout_profile(pids_limit=1024).digest() != a.digest()
    g = make_grader_profile()
    assert sp.runtime_profile_digest(a, g) == sp.runtime_profile_digest(a, g)
    assert sp.runtime_profile_digest(a, g) != sp.runtime_profile_digest(a, None)
    params = a.to_parameters()
    assert params["profile_id"] == sp.ROLLOUT_PROFILE_ID and params["cap_drop"] == ["ALL"]
    assert params["swap_bytes"] == 0 and params["network"]["mode"] == "isolated_internal_network_per_attempt"
    assert params["bind_mounts_allowed"] == []


@pytest.mark.parametrize(
    "overrides, code",
    [
        ({"agent_uid": 0}, "rollout_uid_invalid"),
        ({"agent_user": "root"}, "rollout_user_invalid"),
        ({"pids_limit": 4}, "rollout_pids_limit_invalid"),
        ({"cpus": 0.0}, "rollout_cpus_invalid"),
        ({"memory_bytes": 1024}, "rollout_memory_invalid"),
        ({"trusted_init_caps": ("ALL",)}, "rollout_trusted_init_cap_invalid"),
        ({"trusted_init_caps": ("CAP_CHOWN",)}, "rollout_trusted_init_cap_invalid"),
        ({"egress_subnet_pool": "10.0.0.1/8"}, "rollout_egress_subnet_pool_invalid"),
        ({"egress_subnet_prefix": 16}, "rollout_egress_subnet_prefix_invalid"),
        ({"model_proxy_upstream_port": 0}, "rollout_model_proxy_port_invalid"),
        ({"hidden_paths": ("root",)}, "rollout_hidden_path_invalid"),
        ({"profile_id": "other"}, "rollout_profile_id_invalid"),
    ],
)
def test_rollout_profile_rejects_invalid_parameters(overrides, code):
    with pytest.raises(sp.SandboxProfileError, match=code):
        make_rollout_profile(**overrides)


def test_internal_service_listen_port_conflict_rejected():
    svc = sp.InternalService(alias="pypi", upstream_host="10.1.1.1", upstream_port=8080, listen_port=18001)
    with pytest.raises(sp.SandboxProfileError, match="internal_service_listen_port_conflict"):
        make_rollout_profile(internal_services=(svc,))
    ok = make_rollout_profile(internal_services=(sp.InternalService("pypi", "10.1.1.1", 8080, 18002),))
    assert ok.relay_listen_map() == ((18001, "10.0.0.1", 18001), (18002, "10.1.1.1", 8080))


def test_env_parsing_defaults_and_invalid_values():
    r = sp.rollout_profile_from_env({}, model_proxy_upstream_host="172.17.0.1", model_proxy_upstream_port=18001)
    assert (r.pids_limit, r.cpus, r.memory_bytes, r.require_writable_layer_quota) == (512, 2.0, 4 * 1024**3, False)
    r2 = sp.rollout_profile_from_env(
        {"RH2_SANDBOX_PIDS_LIMIT": "256", "RH2_SANDBOX_REQUIRE_WRITABLE_LAYER_QUOTA": "1",
         "RH2_SANDBOX_INTERNAL_SERVICES": json.dumps([{"alias": "pypi", "upstream_host": "10.1.1.1", "upstream_port": 8080, "listen_port": 18002}])},
        model_proxy_upstream_host="172.17.0.1", model_proxy_upstream_port=18001,
    )
    assert r2.pids_limit == 256 and r2.require_writable_layer_quota and r2.internal_services[0].alias == "pypi"
    for env, code in [
        ({"RH2_SANDBOX_PIDS_LIMIT": "many"}, "sandbox_env_not_int"),
        ({"RH2_SANDBOX_CPUS": "two"}, "sandbox_env_not_float"),
        ({"RH2_SANDBOX_REQUIRE_WRITABLE_LAYER_QUOTA": "yes"}, "sandbox_env_not_bool"),
        ({"RH2_SANDBOX_INTERNAL_SERVICES": "{"}, "sandbox_env_services_not_json"),
        ({"RH2_SANDBOX_INTERNAL_SERVICES": "[1]"}, "sandbox_env_service_entry_invalid"),
    ]:
        with pytest.raises(sp.SandboxProfileError, match=code):
            sp.rollout_profile_from_env(env, model_proxy_upstream_host="h", model_proxy_upstream_port=1)
    g = sp.grader_profile_from_env({"RH2_GRADER_UID": "60000"})
    assert g.candidate_exec_uid == 60000


def test_docker_run_args_carry_every_boundary_and_no_switch_can_drop_them():
    r = make_rollout_profile()
    args = r.docker_run_args(name="c", network="net", image="img", labels=("--label", "a=b"))
    joined = " ".join(args)
    assert args[:4] == ["run", "--detach", "--network", "net"]
    assert "--cap-drop ALL" in joined and "--security-opt no-new-privileges" in joined
    for cap in sp.TRUSTED_INIT_CAPS:
        assert f"--cap-add {cap}" in joined
    assert "--pids-limit 512" in joined and "--cpus 2" in joined
    assert f"--memory {r.memory_bytes} --memory-swap {r.memory_bytes}" in joined  # swap 恒禁
    assert "--tmpfs /tmp:size=1073741824,mode=1777" in joined
    assert "--tmpfs /home/agent:size=268435456,mode=0750,uid=54321,gid=54321" in joined
    assert "--storage-opt" not in joined  # 未要求强制时不下发（守护进程不支持会拒起）
    assert "--privileged" not in joined and "--volume" not in joined and "-v " not in joined
    assert args[-4:] == ["img", "sleep", "infinity"][-3:] + [] or args[-3:] == ["img", "sleep", "infinity"]
    quota = make_rollout_profile(require_writable_layer_quota=True)
    assert f"--storage-opt size={quota.writable_layer_quota_bytes}" in " ".join(
        quota.docker_run_args(name="c", network="n", image="i")
    )
    # 参数集合里没有任何"关掉某项约束"的字段：字段名与 docker 参数一一对应，且全是数值/部署事实
    field_names = {f.name for f in r.__dataclass_fields__.values()}
    assert not any(n.startswith(("disable_", "allow_", "skip_", "unsafe_")) for n in field_names)
    g = make_grader_profile()
    gargs = " ".join(g.docker_run_args(name="g", image="img", declared_readonly_binds=(("/snap", "/rh2/snapshot"),)))
    assert "--network none" in gargs and "--volume /snap:/rh2/snapshot:ro" in gargs
    assert "--cap-drop ALL" in gargs and "--security-opt no-new-privileges" in gargs


# ---------------------------------------------------------------------------
# 纯核对函数：正例 + 每个必需项一个负例
# ---------------------------------------------------------------------------


def _good_inspect(profile, network="rh2-egress-x"):
    return synthesize_inspect(tuple(profile.docker_run_args(name="c", network=network, image="img")), name="c")


def test_rollout_inspect_check_passes_on_profile_args_and_flags_each_violation():
    r = make_rollout_profile()
    good = _good_inspect(r)
    assert sp.check_rollout_inspect(good, r, expected_network="rh2-egress-x") == []

    def mutated(fn):
        c = copy.deepcopy(good)
        fn(c)
        return sp.check_rollout_inspect(c, r, expected_network="rh2-egress-x")

    assert any("CapDrop" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("CapDrop", [])))
    assert any("CapAdd" in v for v in mutated(lambda c: c["HostConfig"]["CapAdd"].append("CAP_SYS_ADMIN")))
    assert any("no-new-privileges" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("SecurityOpt", None)))
    assert any("unconfined" in v for v in mutated(lambda c: c["HostConfig"]["SecurityOpt"].append("seccomp=unconfined")))
    assert any("Privileged" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("Privileged", True)))
    assert any("PidsLimit" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("PidsLimit", None)))
    assert any("NanoCpus" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("NanoCpus", 0)))
    assert any("Memory=" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("Memory", 0)))
    assert any("MemorySwap" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("MemorySwap", -1)))
    assert any("Tmpfs" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("Tmpfs", {"/tmp": "size=1"})))
    assert any("NetworkMode" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("NetworkMode", "bridge")))
    assert any("Networks" in v for v in mutated(lambda c: c["NetworkSettings"]["Networks"].__setitem__("bridge", {})))
    assert any("bind mount" in v for v in mutated(lambda c: c["HostConfig"].__setitem__("Binds", ["/etc:/x:rw"])))
    assert any("bind mount" in v for v in mutated(lambda c: c["Mounts"].append({"Type": "bind", "Source": "/etc", "Destination": "/x", "RW": False})))
    assert any("Running" in v for v in mutated(lambda c: c["State"].__setitem__("Running", False)))
    quota = make_rollout_profile(require_writable_layer_quota=True)
    assert any("StorageOpt" in v for v in sp.check_rollout_inspect(good, quota, expected_network="rh2-egress-x"))


def test_rollout_probe_check_passes_and_flags_each_violation():
    r = make_rollout_profile()
    good = sp.parse_key_value_output(rollout_probe_output(r, head=BASE_COMMIT))
    assert sp.check_rollout_probe(good, r, expected_head=BASE_COMMIT) == []
    cases = {
        "UID": "0", "CAPEFF": "000001ffffffffff", "NNP": "0", "CG_PIDS_MAX": "max", "CG_MEMORY_MAX": "max",
        "CG_SWAP_MAX": "max", "CG_CPU_MAX": "max 100000", "NET_relay": "DENIED", "NET_forbidden_0": "CONNECTED",
        "NET_upstream_direct": "CONNECTED", "DNS_EXTERNAL": "RESOLVED", "HIDDEN_0": "READABLE:/root",
        "GIT_REMOTES": "1", "GIT_REFLOG": "2", "WORKDIR_WRITABLE": "0", "WORKDIR_OWNER": "0", "HOME_WRITABLE": "0",
        "TMP_WRITABLE": "0", "ROUTED_IFACES": "eth0,eth1,", "GIT_HEAD": "f" * 40, "RH2_PROBE_OK": "0",
    }
    for key, bad in cases.items():
        facts = dict(good)
        facts[key] = bad
        violations = sp.check_rollout_probe(facts, r, expected_head=BASE_COMMIT)
        assert violations, f"{key}={bad} 应被判违规"
    # 探针中断（无 RH2_PROBE_OK）也是违规
    assert sp.check_rollout_probe({}, r)


def test_grader_checks_pass_and_flag_network_user_and_binds():
    g = make_grader_profile()
    good = synthesize_inspect(tuple(g.docker_run_args(name="g", image="img", declared_readonly_binds=(("/snap", "/rh2/snapshot"),))), name="g")
    assert sp.check_grader_inspect(good, g, declared_readonly_binds=(("/snap", "/rh2/snapshot"),)) == []
    assert any("未声明" in v for v in sp.check_grader_inspect(good, g))  # 未声明的 bind 即违规
    bad_net = copy.deepcopy(good)
    bad_net["HostConfig"]["NetworkMode"] = "bridge"
    assert any("deny_all" in v or "none" in v for v in sp.check_grader_inspect(bad_net, g, declared_readonly_binds=(("/snap", "/rh2/snapshot"),)))
    facts = sp.parse_key_value_output(grader_probe_output(g))
    assert sp.check_grader_probe(facts, g) == []
    for key, bad in {"UID": "0", "ROUTED_IFACES": "eth0,", "NET_forbidden_0": "CONNECTED", "CAPEFF": "1", "NNP": "0", "CG_SWAP_MAX": "max"}.items():
        f = dict(facts)
        f[key] = bad
        assert sp.check_grader_probe(f, g), key


def test_git_sanitize_self_check_and_key_value_parser():
    ok = sp.parse_key_value_output(
        "RH2_GIT_SANITIZE_OK=1\nHEAD_BEFORE=a\nHEAD_AFTER=a\nHISTORY_COUNT_BEFORE=5\nHISTORY_COUNT_AFTER=5\n"
        "REMOTES=0\nREFLOG_ENTRIES=0\nUNREACHABLE_OBJECTS=0\nnoise line\nNET_relay=CONNECTED\n"
    )
    assert ok["NET_relay"] == "CONNECTED" and "noise line" not in ok
    assert sp.git_sanitize_violations(ok) == []
    assert sp.git_sanitize_violations({**ok, "UNREACHABLE_OBJECTS": "3"})
    assert sp.git_sanitize_violations({**ok, "HISTORY_COUNT_AFTER": "4"})
    assert sp.git_sanitize_violations({**ok, "HEAD_AFTER": "b"})
    assert sp.git_sanitize_violations(ok, exit_code=2)


def test_subnet_pool_round_robin_overlap_and_exhaustion():
    pool = sp.EgressSubnetPool("10.212.0.0/28", 30)  # 4 个 /30
    assert pool.capacity == 4
    first = pool.allocate()
    pool.mark_foreign("10.212.0.4/30")
    second = pool.allocate()
    assert first == "10.212.0.0/30" and second == "10.212.0.8/30"
    pool.allocate()
    with pytest.raises(sp.SandboxNetworkError, match="egress_subnet_pool_exhausted"):
        pool.allocate()
    pool.release(first)
    assert pool.allocate() == first


async def test_create_attempt_network_skips_overlapping_slots():
    r = make_rollout_profile()
    state = ProfileFakeState(head=BASE_COMMIT, rollout_profile=r, network_create_overlap_times=2)

    async def docker(*args, input_bytes=None):
        res = state.dispatch(args, input_bytes)
        assert res is not None
        return res

    pool = sp.EgressSubnetPool(r.egress_subnet_pool, r.egress_subnet_prefix)
    net = await sp.create_attempt_network(docker, profile=r, pool=pool, name="rh2-egress-t")
    assert net.subnet == "10.212.0.16/29"  # 前两个槽位 overlap → 第三个
    assert list(state.networks) == ["rh2-egress-t"]


# ---------------------------------------------------------------------------
# 编排：创建期强制 / 顺序 / 记录 / 失败语义
# ---------------------------------------------------------------------------


def _formal_chain(docker: FakeRolloutDocker | None = None, **kw):
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        runtime_quiescence_barrier=_Barrier(), turns=turns, docker=docker, **kw,
    )
    _stamp_fa_identity(chain.base_sample)
    return chain


def test_formal_chain_requires_profile_relay_and_digest_at_construction():
    base = dict(
        config=_formal_config(policy_version="5", execution_mode="fa_formal"),
        task_resolver=lambda s: None, adapter_factory=lambda h, d: None, harness_driver=object(),
        grading_submit=lambda **k: None, runtime_quiescence_barrier=_Barrier(),
        finalization_store=object(), session_drain_owner=lambda sid: None,
    )
    with pytest.raises(StartupCheckError, match="sandbox_profile_required_in_formal_chain"):
        RolloutOrchestrator(**base)
    with pytest.raises(StartupCheckError, match="egress_relay_required_with_sandbox_profile"):
        RolloutOrchestrator(**base, sandbox_profile=make_rollout_profile(), runtime_profile_digest="sha256:x")
    with pytest.raises(StartupCheckError, match="runtime_profile_digest_required_with_sandbox_profile"):
        RolloutOrchestrator(**base, sandbox_profile=make_rollout_profile(), egress_relay=TEST_RELAY)
    # 三者齐全即可构造；fa_audit_only / s1_compat 允许不带 profile（legacy 路径）
    RolloutOrchestrator(**base, **formal_sandbox_kwargs())
    RolloutOrchestrator(**{**base, "config": _formal_config(policy_version="5", execution_mode="fa_audit_only")})


async def test_formal_rollout_orders_network_init_sanitize_prelaunch_before_harness_and_stamps_digest(tmp_path):
    chain = _formal_chain(audit_sink=None)
    result = await rh2_custom_generate(_Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[-1]
    calls = chain.docker.calls
    state = chain.docker.profile_fake
    # 顺序：network create → connect relay → run（profile 参数）→ ... → sanitize → trusted-init → prelaunch(inspect+probe) → harness
    idx = {}
    for i, args in enumerate(calls):
        key = None
        if args[:2] == ("network", "create"):
            key = "net_create"
        elif args[:2] == ("network", "connect"):
            key = "relay_connect"
        elif args[0] == "run":
            key = "run"
        elif args[0] == "inspect" and len(args) == 2:
            key = "inspect"
        elif args[0] == "exec" and sp.script_id_of(args[-1]) in ("git-sanitize", "rollout-trusted-init", "rollout-prelaunch-probe"):
            key = sp.script_id_of(args[-1])
        if key and key not in idx:
            idx[key] = i
    assert idx["net_create"] < idx["relay_connect"] < idx["run"] < idx["git-sanitize"] < idx["rollout-trusted-init"] < idx["inspect"] < idx["rollout-prelaunch-probe"]
    harness_started = next(e.monotonic_ts for e in audit.timeline if e.step == "harness_started")
    prelaunch_passed = next(e.monotonic_ts for e in audit.timeline if e.step == "sandbox_prelaunch_check_passed")
    assert prelaunch_passed <= harness_started
    # run 参数逐字来自 profile（无 bridge、无 root）
    run_args = calls[idx["run"]]
    assert "--network" in run_args and run_args[run_args.index("--network") + 1] == audit.egress_network
    assert "--cap-drop" in run_args and "no-new-privileges" in run_args and "bridge" not in run_args
    # 探针以 agent uid 执行（-u <uid>），可信初始化以 root
    probe_call = calls[idx["rollout-prelaunch-probe"]]
    assert probe_call[1] == "-u" and probe_call[2] == str(state.rollout_profile.agent_uid)
    init_call = calls[idx["rollout-trusted-init"]]
    assert init_call[1] == "-u" and init_call[2] == "root"
    # 记录：audit 与样本 metadata 盖同一个 digest；sandbox_setup / prelaunch_check 在场
    digest = chain.orchestrator._runtime_profile_digest
    assert audit.runtime_profile_digest == digest and digest.startswith("sha256:")
    assert audit.prelaunch_check["ok"] is True and audit.sandbox_setup["git_sanitize"]["UNREACHABLE_OBJECTS"] == "0"
    assert audit.lease.run_as_user == "agent" and "isolated internal" in audit.lease.network_allowlist_justification
    delivered = [s for s in result if not getattr(s, "remove_sample", False)]
    assert delivered and all(s.metadata[sp.RUNTIME_PROFILE_DIGEST_METADATA_KEY] == digest for s in delivered)
    # 清理：容器 rm 之后网络也被删（先断开 relay）
    assert state.removed_networks == [audit.egress_network] and state.networks == {}
    assert state.relay_disconnections == [(audit.egress_network, TEST_RELAY.container_name)]
    assert any(e.step == "egress_network_removed" for e in audit.timeline)
    # bringup 的 execution audit 记录携带 digest 与 sandbox 事实
    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    path = tmp_path / "audit.jsonl"
    write_execution_audit_record(None, audit, path)
    record = json.loads(path.read_text().splitlines()[-1])
    assert record["runtime_profile_digest"] == digest and record["prelaunch_check"]["ok"] is True
    assert record["egress_network"] == audit.egress_network and "git_sanitize" in record["sandbox_setup"]


async def test_prelaunch_violation_is_typed_fatal_and_leaves_no_container_or_network():
    docker = FakeRolloutDocker()
    docker.profile_fake.probe_overrides = {"NET_forbidden_0": "CONNECTED"}  # 云 metadata 竟然可达
    chain = _formal_chain(docker=docker)
    with pytest.raises(FatalExecutionInfrastructureError, match="sandbox_prelaunch_check_failed"):
        await rh2_custom_generate(_Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[-1]
    assert audit.prelaunch_check["ok"] is False and any("egress 未阻断" in v for v in audit.prelaunch_check["violations"])
    assert "probe_facts" in audit.prelaunch_check  # 未通过时保留完整事实
    assert not chain.driver.calls  # harness 从未启动
    assert docker.removed == [audit.lease.container_id] and docker.profile_fake.networks == {}
    assert audit.lease_released


async def test_prelaunch_inspect_violation_is_fatal_too():
    docker = FakeRolloutDocker()

    def strip_nnp(container):
        container["HostConfig"]["SecurityOpt"] = []

    docker.profile_fake.inspect_mutator = strip_nnp
    chain = _formal_chain(docker=docker)
    with pytest.raises(FatalExecutionInfrastructureError, match="sandbox_prelaunch_check_failed"):
        await rh2_custom_generate(_Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS))
    assert any("no-new-privileges" in v for v in chain.orchestrator.audits[-1].prelaunch_check["violations"])
    assert not chain.driver.calls


async def test_relay_missing_is_run_fatal_not_member_loss():
    docker = FakeRolloutDocker()
    docker.profile_fake.relay_missing = True
    chain = _formal_chain(docker=docker)
    with pytest.raises(FatalExecutionInfrastructureError, match="egress_relay_unavailable"):
        await rh2_custom_generate(_Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS))
    assert docker.profile_fake.networks == {}  # 网络已回收
    assert not any(c[0] == "run" for c in docker.calls)  # 容器从未创建


async def test_transient_network_failure_and_sanitize_failure_are_task_local():
    docker = FakeRolloutDocker()
    docker.profile_fake.network_create_fail = "Error response from daemon: could not find an available IP"
    chain = _formal_chain(docker=docker)
    result = await rh2_custom_generate(_Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS))
    assert result[0].remove_sample and "rollout_egress_network_failed" in str(chain.orchestrator.audits[-1].failure_records[0].detail)
    docker2 = FakeRolloutDocker()
    docker2.profile_fake.sanitize_overrides = {"UNREACHABLE_OBJECTS": "7"}
    chain2 = _formal_chain(docker=docker2)
    result2 = await rh2_custom_generate(_Args(chain2.orchestrator), chain2.base_sample, dict(SAMPLING_PARAMS))
    assert result2[0].remove_sample
    audit2 = chain2.orchestrator.audits[-1]
    assert any("rollout_git_sanitize_failed" in f.detail for f in audit2.failure_records)
    assert docker2.removed == [audit2.lease.container_id] and docker2.profile_fake.networks == {}


async def test_legacy_modes_without_profile_keep_old_docker_args():
    chain = build_dense_chain()  # s1_compat：无 profile
    await rh2_custom_generate(_Args(chain.orchestrator), chain.base_sample, dict(SAMPLING_PARAMS))
    run_args = next(c for c in chain.docker.calls if c[0] == "run")
    assert "--network" in run_args and run_args[run_args.index("--network") + 1] == "bridge"
    assert "--cap-drop" not in run_args and not any(c[0] == "network" for c in chain.docker.calls)
    audit = chain.orchestrator.audits[-1]
    assert audit.runtime_profile_digest is None and audit.prelaunch_check is None


# ---------------------------------------------------------------------------
# H7 探针清单 / CLI
# ---------------------------------------------------------------------------


def test_probe_scripts_dir_matches_package_and_cli_lists_them():
    rollout = sp.rollout_profile_from_env({}, model_proxy_upstream_host="172.17.0.1", model_proxy_upstream_port=18001)
    grader = sp.grader_profile_from_env({})
    scripts = sp.list_probe_scripts(rollout, grader)
    assert set(scripts) == {
        "rollout-trusted-init", "git-sanitize", "rollout-prelaunch-probe", "rollout-extended-probe",
        "git-future-probe", "storage-quota-probe", "grader-trusted-init", "grader-prelaunch-probe",
        "grader-chown-before-eval",
    }
    scripts_dir = REPO_RH2 / "scripts" / "sandbox_probes"
    for sid, text in scripts.items():
        assert sp.script_id_of(text) == sid
        assert (scripts_dir / f"{sid}.sh").read_text(encoding="utf-8") == text, f"{sid}.sh 与包内文本不一致（重新 dump-probes）"
    assert (scripts_dir / "h7_boundary_probes.sh").exists()
    out = subprocess.run(
        [sys.executable, "-m", "repoharness2.adapters.slime.sandbox_profile", "list-probes"],
        capture_output=True, text=True, timeout=60, cwd=str(REPO_RH2),
    )
    assert out.returncode == 0, out.stderr
    listed = dict(line.split("\t") for line in out.stdout.strip().splitlines())
    assert listed["git-sanitize"] == "sha256:" + hashlib.sha256(scripts["git-sanitize"].encode()).hexdigest()
