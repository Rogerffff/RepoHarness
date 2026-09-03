"""W3b（D2-2 / D2-4）真实容器验收（@pytest.mark.docker，本机 daemon 不可用即 skip）。

这里证明的是**真实边界**，不是替身：
- verify 入口（bringup 启动与 W7 远端调用的同一个函数）在真实 relay + isolated internal 网络 +
  真实容器上跑全部探针：user/caps/no-new-privileges/PID/memory+swap/tmpfs/mount/network 由
  `docker inspect` 与容器内 `/proc`、cgroup、`/dev/tcp` 实测；
- 公网 / direct-IP / 云 metadata / 宿主直连不可达而模型代理 relay 可达（经 relay 的 HTTP 往返到达
  宿主侧上游服务）；
- D2-4 canary 反例：向 private 评分材料注入唯一串，formal 链在真实容器上跑完后，模型可见面
  （prompt、public bundle、容器文件系统、容器 env/label/mount、harness 启动 env、adapter 请求）均无该串；
- solution-bearing Git 状态不可恢复：镜像 /testbed 带"未来解法提交"（含唯一串）+ tag + 分支，
  agent 视角 `git cat-file` / `git fsck --lost-found` / `grep -r .git` / `git show <tag>` 全部找不到，
  base 之前历史保留；
- 正常 formal rollout 在同 profile 下跑完并交付带 runtime_profile_digest 的样本，容器与网络零残留；
- 启动前核对不过（真实 egress 未阻断的负例）→ 不启动 harness、typed fatal、零残留。
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/：sandbox_test_support
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    FakeFinalizationStore,
    FixtureSlimeSample,
    GradingSubmitStub,
    MockSessionAdapter,
    _Args,
    _formal_config,
    dense_leaf_sample,
    dense_turns,
)
from test_w1b_termination_facts_producer import _Barrier  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.generate import (  # noqa: E402
    RolloutOrchestrator,
    RolloutTaskSpec,
    rh2_custom_generate,
    run_docker,
)
from repoharness2.grading.manager import GradingEnvSpec, HygieneRules  # noqa: E402

# 与 tests/grading/conftest.py 同一份轻量镜像定义（python:3.12-slim + git）；本文件不依赖那个 conftest。
BASE_FIXTURE_IMAGE = "rh2-s14-grading-fixture:v1"
_BASE_DOCKERFILE = """\
FROM python:3.12-slim
RUN apt-get update \\
 && apt-get install -y --no-install-recommends git \\
 && rm -rf /var/lib/apt/lists/*
RUN git config --global user.email rh2-fixture@test \\
 && git config --global user.name rh2-fixture \\
 && git config --global --add safe.directory '*'
"""
FUTURE_CANARY = "RH2_FUTURE_SOLUTION_CANARY_" + uuid.uuid4().hex[:10]
PRIVATE_CANARY = "RH2_PRIVATE_GRADING_CANARY_" + uuid.uuid4().hex[:10]


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


DOCKER_AVAILABLE = _docker_available()
pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason="本机 docker daemon 不可用（W3b 真实容器验收需要它）"),
]


def _sh(*args: str, timeout: float = 300.0) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.email=w3b@test", "-c", "user.name=w3b", "-C", str(repo), *args],
        capture_output=True, text=True, check=True,
    )
    return proc.stdout.strip()


# ---------------------------------------------------------------------------
# 宿主侧上游 HTTP 服务（扮演模型代理 adapter；relay 经 host.docker.internal / docker0 网关到达它）
# ---------------------------------------------------------------------------


class _UpstreamHandler(BaseHTTPRequestHandler):
    hits: list[str] = []

    def _reply(self) -> None:
        type(self).hits.append(self.path)
        body = b"rh2-upstream-ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _reply
    do_POST = _reply

    def log_message(self, *a: Any) -> None:  # noqa: D401 - 静音
        return


@dataclass
class RolloutFixture:
    image: str
    base_commit: str
    future_sha: str
    base_history_count: int


@dataclass
class SandboxRuntime:
    profile: sp.RolloutSandboxProfile
    grader: sp.GraderSandboxProfile
    relay: sp.EgressRelayHandle
    run_id: str
    labels: tuple[str, ...]
    upstream_host: str
    upstream_port: int


def _ensure_base_image() -> None:
    if _sh("docker", "image", "inspect", BASE_FIXTURE_IMAGE).returncode == 0:
        return
    with tempfile.TemporaryDirectory() as ctx:
        (Path(ctx) / "Dockerfile").write_text(_BASE_DOCKERFILE)
        build = _sh("docker", "build", "-t", BASE_FIXTURE_IMAGE, ctx, timeout=900)
        assert build.returncode == 0, build.stderr[-2000:]


@pytest.fixture(scope="session")
def rollout_fixture(tmp_path_factory: pytest.TempPathFactory) -> RolloutFixture:
    """镜像 /testbed = 小仓库：base 提交 → 含 FUTURE_CANARY 的"解法"提交（tag v9.9 + 分支 feature）→
    再一个提交 → `git reset --hard base`（SWE 官方镜像构建的形态：未来对象仍在 pack 里、可按 SHA 找回）。"""

    _ensure_base_image()
    ctx = tmp_path_factory.mktemp("w3b_rollout_image")
    repo = ctx / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "thing.py").write_text('def feature():\n    return "broken"\n')
    (repo / "tests" / "test_thing.py").write_text("import sys\nsys.exit(0)\n")
    (repo / "README.md").write_text("rh2 W3b rollout fixture\n")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, capture_output=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "src" / "thing.py").write_text(f'def feature():\n    return "fixed"  # {FUTURE_CANARY}\n')
    _git(repo, "commit", "-qam", "future solution")
    future = _git(repo, "rev-parse", "HEAD")
    _git(repo, "tag", "v9.9")
    (repo / "src" / "later.py").write_text("later = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "later")
    _git(repo, "branch", "feature")
    _git(repo, "reset", "-q", "--hard", base)
    assert _git(repo, "cat-file", "-t", future) == "commit"  # 前置：reset 后未来对象仍可找回
    (ctx / "Dockerfile").write_text(
        f"FROM {BASE_FIXTURE_IMAGE}\nCOPY repo /testbed\nRUN git config --global --add safe.directory /testbed\n"
    )
    image = f"rh2-w3b-rollout-fixture:{uuid.uuid4().hex[:8]}"
    build = _sh("docker", "build", "-t", image, str(ctx), timeout=900)
    assert build.returncode == 0, build.stderr[-2000:]
    yield RolloutFixture(image=image, base_commit=base, future_sha=future, base_history_count=1)
    _sh("docker", "image", "rm", "-f", image)


def _relay_upstream_host(port: int) -> str:
    """relay 视角的宿主地址：Docker Desktop = host.docker.internal；Linux 引擎 = docker0 网关 172.17.0.1。"""

    probe = (
        "import socket,sys\n"
        "for h in ('host.docker.internal','172.17.0.1'):\n"
        "    try:\n"
        f"        s=socket.create_connection((h,{port}),timeout=3); s.close(); print(h); sys.exit(0)\n"
        "    except Exception: pass\n"
        "sys.exit(1)\n"
    )
    res = _sh("docker", "run", "--rm", "--network", "bridge", "python:3.12-slim", "python3", "-c", probe, timeout=120)
    assert res.returncode == 0, f"relay 无法从容器到达宿主侧上游服务：{res.stderr[-300:]}"
    return res.stdout.strip()


@pytest.fixture(scope="session")
def upstream_server():
    server = HTTPServer(("0.0.0.0", 0), _UpstreamHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port
    server.shutdown()


@pytest.fixture(scope="session")
def sandbox_runtime(upstream_server: int) -> SandboxRuntime:
    host = _relay_upstream_host(upstream_server)
    profile = make_rollout_profile(model_proxy_upstream_host=host, model_proxy_upstream_port=upstream_server)
    run_id = f"w3btest-{uuid.uuid4().hex[:8]}"
    labels = ("--label", f"rh2.run_id={run_id}")
    relay = asyncio.run(sp.start_egress_relay(run_docker, profile, run_id=run_id, labels=labels))
    runtime = SandboxRuntime(
        profile=profile, grader=make_grader_profile(), relay=relay, run_id=run_id, labels=labels,
        upstream_host=host, upstream_port=upstream_server,
    )
    yield runtime

    async def _teardown() -> None:
        nets = await sp.list_labeled_networks(run_docker, label=f"rh2.run_id={run_id}") or []
        for net in nets:
            await sp.teardown_attempt_network(run_docker, network_name=net, relay=relay)
        await sp.stop_egress_relay(run_docker, relay)

    asyncio.run(_teardown())


@pytest.fixture(scope="session")
def verify_record(sandbox_runtime: SandboxRuntime, rollout_fixture: RolloutFixture) -> dict[str, Any]:
    """bringup 启动 / W7 远端调用的同一 verify 入口，在真实容器上跑一次。"""

    return asyncio.run(
        sp.verify_sandbox_profiles(
            run_docker, rollout=sandbox_runtime.profile, grader=sandbox_runtime.grader, image=rollout_fixture.image,
            run_id=sandbox_runtime.run_id, relay=sandbox_runtime.relay, labels=sandbox_runtime.labels,
            expect_upstream_http=True,
        )
    )


# ---------------------------------------------------------------------------
# verify 入口：结构事实 + 实际事实
# ---------------------------------------------------------------------------


def test_verify_record_ok_and_digest_matches_profiles(verify_record, sandbox_runtime):
    assert verify_record["ok"], verify_record["failures"]
    assert verify_record["runtime_profile_digest"] == sp.runtime_profile_digest(sandbox_runtime.profile, sandbox_runtime.grader)
    assert verify_record["rollout"]["ok"] and verify_record["grader"]["ok"]
    assert verify_record["schema_id"] == sp.RUNTIME_PROFILE_RECORD_SCHEMA_ID


def test_rollout_inspect_proves_user_caps_nnp_pids_memory_swap_tmpfs_mounts_network(verify_record, sandbox_runtime):
    pre = verify_record["rollout"]["checks"]["prelaunch"]
    assert pre["ok"], pre["violations"]
    inf = pre["inspect_facts"]
    assert inf["cap_drop"] == ["ALL"]
    assert {c.removeprefix("CAP_") for c in inf["cap_add"]} == set(sp.TRUSTED_INIT_CAPS)
    assert "no-new-privileges" in inf["security_opt"] and inf["privileged"] is False
    p = sandbox_runtime.profile
    assert inf["pids_limit"] == p.pids_limit and inf["memory"] == p.memory_bytes and inf["memory_swap"] == p.memory_bytes
    assert inf["nano_cpus"] == int(p.cpus * 1e9)
    assert inf["tmpfs"] == p.expected_tmpfs()
    assert inf["binds"] == [] and all(m["type"] == "tmpfs" for m in inf["mounts"])
    assert inf["network_mode"].startswith("rh2-sbverify-net-") and inf["networks"] == [inf["network_mode"]]
    facts = pre["probe_facts"]
    assert facts["UID"] == str(p.agent_uid) and facts["CAPEFF"].strip("0") == "" and facts["NNP"] == "1"
    assert facts["CG_PIDS_MAX"] == str(p.pids_limit) and facts["CG_MEMORY_MAX"] == str(p.memory_bytes)
    assert facts["CG_SWAP_MAX"] == "0" and facts["CG_CPU_MAX"] == f"{int(p.cpus * 100000)} 100000"
    assert facts["ROUTED_IFACES"] == "eth0,"
    assert facts["WORKDIR_OWNER"] == str(p.agent_uid) and facts["WORKDIR_WRITABLE"] == "1"


def test_rollout_egress_public_direct_ip_metadata_host_denied_relay_reachable(verify_record):
    facts = verify_record["rollout"]["checks"]["prelaunch"]["probe_facts"]
    assert facts["NET_relay"] == "CONNECTED"
    denied = {k: v for k, v in facts.items() if k.startswith("NET_forbidden_") or k == "NET_upstream_direct"}
    assert denied and all(v == "DENIED" for v in denied.values()), denied
    assert facts["DNS_EXTERNAL"] == "DENIED"
    ext = verify_record["rollout"]["checks"]["extended"]
    assert ext["ok"], ext["violations"]
    assert ext["facts"]["PROXY_HTTP"].startswith("HTTP/1.")  # 经 relay 到达宿主侧上游服务


def test_hidden_root_unreadable_and_privilege_escalation_denied(verify_record):
    facts = verify_record["rollout"]["checks"]["prelaunch"]["probe_facts"]
    hidden = {k: v for k, v in facts.items() if k.startswith("HIDDEN_")}
    assert hidden and all(v.startswith("DENIED:") for v in hidden.values()), hidden
    ext = verify_record["rollout"]["checks"]["extended"]["facts"]
    assert ext["ESCALATE_SU"] == "DENIED" and ext["ESCALATE_SETUID"] in ("DENIED", "NO_PYTHON")


def test_git_future_probe_deterministic_unrecoverable(verify_record):
    gf = verify_record["rollout"]["checks"]["git_future_unrecoverable"]
    assert gf["ok"], gf["violations"]
    f = gf["facts"]
    assert f["FUTURE_BEFORE"] == "RECOVERABLE"  # 探针自身的前置：reset 后本可找回
    assert (f["FUTURE_CATFILE"], f["FUTURE_TAG"], f["FUTURE_BRANCH"], f["FUTURE_GREP"]) == ("GONE", "GONE", "GONE", "ABSENT")
    assert f["FUTURE_LOSTFOUND"] == "0" and f["SANITIZE_UNREACHABLE_OBJECTS"] == "0" and f["HEAD_IS_BASE"] == "1"


def test_real_testbed_sanitize_deleted_future_refs_and_kept_base_history(verify_record, rollout_fixture):
    san = verify_record["rollout"]["checks"]["workdir_git_sanitize"]
    assert san["ok"], san
    f = san["facts"]
    assert f["HEAD_BEFORE"] == f["HEAD_AFTER"] == rollout_fixture.base_commit
    assert int(f["REFS_DELETED"]) >= 2  # tag v9.9 + 分支 feature（都指向 base 之后的提交）
    assert f["REMOTES"] == "0" and f["REFLOG_ENTRIES"] == "0" and f["UNREACHABLE_OBJECTS"] == "0"
    assert f["HISTORY_COUNT_BEFORE"] == f["HISTORY_COUNT_AFTER"] == str(rollout_fixture.base_history_count)


def test_writable_layer_quota_enforcement_is_measured_not_assumed(verify_record):
    q = verify_record["rollout"]["checks"]["writable_layer_quota"]
    assert q["requested"] is False and q["enforced"] in ("0", "1", "UNKNOWN_NO_FALLOCATE")


def test_grader_profile_deny_all_nonroot_and_limits_on_real_container(verify_record, sandbox_runtime):
    pre = verify_record["grader"]["checks"]["prelaunch"]
    assert pre["ok"], pre["violations"]
    g = sandbox_runtime.grader
    inf = pre["inspect_facts"]
    assert inf["network_mode"] == "none" and inf["networks"] == ["none"] and inf["cap_drop"] == ["ALL"]
    assert inf["memory_swap"] == g.memory_bytes and inf["pids_limit"] == g.pids_limit
    facts = pre["probe_facts"]
    assert facts["UID"] == str(g.candidate_exec_uid) and facts["CAPEFF"].strip("0") == "" and facts["NNP"] == "1"
    assert facts["ROUTED_IFACES"] == "" and all(v == "DENIED" for k, v in facts.items() if k.startswith("NET_"))
    assert facts["CG_SWAP_MAX"] == "0"


def test_relay_container_is_hardened_and_zero_verify_residue(sandbox_runtime):
    res = _sh("docker", "inspect", sandbox_runtime.relay.container_name)
    assert res.returncode == 0
    c = json.loads(res.stdout)[0]
    hc = c["HostConfig"]
    assert c["Config"]["User"] == "65534:65534" and hc["CapDrop"] == ["ALL"] and hc["ReadonlyRootfs"] is True
    assert hc["NetworkMode"] == "bridge" and "no-new-privileges" in hc["SecurityOpt"]
    assert hc["PidsLimit"] == 64 and hc["MemorySwap"] == hc["Memory"]
    left = _sh("docker", "ps", "-a", "--filter", "name=rh2-sbverify", "--format", "{{.Names}}").stdout.strip()
    assert left == ""


# ---------------------------------------------------------------------------
# formal 链在真实容器上：agent 视角探针 + canary + 交付 + 零残留
# ---------------------------------------------------------------------------


_AGENT_VIEW_SCRIPT = r'''
set -u
cd /testbed
echo "UID=$(id -u)"
awk '/^CapEff/{print "CAPEFF="$2} /^NoNewPrivs/{print "NNP="$2}' /proc/self/status
if git cat-file -e __FUT__ 2>/dev/null; then echo "FUTURE_CATFILE=RECOVERABLE"; else echo "FUTURE_CATFILE=GONE"; fi
if git show v9.9 >/dev/null 2>&1; then echo "FUTURE_TAG=RECOVERABLE"; else echo "FUTURE_TAG=GONE"; fi
if git rev-parse --verify -q feature >/dev/null 2>&1; then echo "FUTURE_BRANCH=RECOVERABLE"; else echo "FUTURE_BRANCH=GONE"; fi
echo "LOSTFOUND=$(git fsck --lost-found 2>/dev/null | grep -c dangling || true)"
echo "UNREACHABLE=$(git fsck --unreachable --no-reflogs 2>/dev/null | grep -c '^unreachable' || true)"
if grep -rq __FUTCANARY__ .git 2>/dev/null; then echo "FUTURE_GREP=FOUND"; else echo "FUTURE_GREP=ABSENT"; fi
echo "HISTORY=$(git rev-list --count HEAD)"; echo "REFLOG=$(git reflog 2>/dev/null | wc -l | tr -d ' ')"; echo "REMOTES=$(git remote | wc -l | tr -d ' ')"
if grep -rq __PRIVCANARY__ /rh2 /testbed /home /tmp /etc /opt /var/tmp 2>/dev/null; then echo "PRIVATE_GREP=FOUND"; else echo "PRIVATE_GREP=ABSENT"; fi
if env | grep -q __PRIVCANARY__; then echo "PRIVATE_ENV=FOUND"; else echo "PRIVATE_ENV=ABSENT"; fi
if ls /root >/dev/null 2>&1; then echo "ROOT_DIR=READABLE"; else echo "ROOT_DIR=DENIED"; fi
BODY=$(timeout 8 bash -c 'exec 3<>/dev/tcp/rh2-egress-relay/__PORT__; printf "GET /agent-view HTTP/1.0\r\nHost: rh2\r\n\r\n" >&3; cat <&3' 2>/dev/null | tail -1)
echo "PROXY_BODY=$BODY"
if timeout 3 bash -c 'exec 3<>/dev/tcp/__UPHOST__/__PORT__' 2>/dev/null; then echo "UPSTREAM_DIRECT=CONNECTED"; else echo "UPSTREAM_DIRECT=DENIED"; fi
if timeout 3 bash -c 'exec 3<>/dev/tcp/1.1.1.1/443' 2>/dev/null; then echo "PUBLIC=CONNECTED"; else echo "PUBLIC=DENIED"; fi
echo "AGENT_VIEW_OK=1"
'''


@dataclass
class AgentViewDriver:
    """替代 Claude Code：以 agent 身份在真实容器里跑一段 bash（= 模型工具可见面），记录事实后退出 0。"""

    fixture: RolloutFixture
    runtime: SandboxRuntime
    adapter_ref: dict[str, MockSessionAdapter] = field(default_factory=dict)
    facts: dict[str, str] = field(default_factory=dict)
    prompts: list[str] = field(default_factory=list)
    adapter_urls: list[str] = field(default_factory=list)
    root_grep: str = ""
    inspect_env_labels: str = ""

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        self.prompts.append(prompt)
        self.adapter_urls.append(adapter_url)
        script = (
            _AGENT_VIEW_SCRIPT.replace("__FUT__", self.fixture.future_sha)
            .replace("__FUTCANARY__", FUTURE_CANARY)
            .replace("__PRIVCANARY__", PRIVATE_CANARY)
            .replace("__PORT__", str(self.runtime.profile.model_proxy_listen_port))
            .replace("__UPHOST__", self.runtime.upstream_host)
        )
        p = self.runtime.profile
        res = await run_docker(
            "exec", "-u", str(p.agent_uid), "-e", f"HOME=/home/{p.agent_user}", sandbox.container_name,
            "bash", "-c", script,
        )
        self.facts = sp.parse_key_value_output(res.stdout)
        self.facts["_stderr"] = res.stderr[-500:]
        # root 视角全盘 grep（canary 绝不在容器任何地方）+ inspect 的 env/label/mount 文本
        grep = await run_docker(
            "exec", sandbox.container_name, "bash", "-c",
            f"grep -rl {PRIVATE_CANARY} / --exclude-dir=proc --exclude-dir=sys --exclude-dir=dev 2>/dev/null | head -5; true",
        )
        self.root_grep = grep.stdout.strip()
        ins = await run_docker("inspect", sandbox.container_name)
        payload = json.loads(ins.stdout)[0]
        self.inspect_env_labels = json.dumps(
            {"Env": payload["Config"].get("Env"), "Labels": payload["Config"].get("Labels"), "Mounts": payload["Mounts"]}
        )
        # 与 MockClaudeCodeDriver 同：模型侧回合由脚本化 adapter 记录（真实 CC 经代理产生 capture 记录）
        await self.adapter_ref["adapter"].run_all_turns()
        return 0


@dataclass
class FormalRun:
    result: list[Any]
    audit: Any
    driver: AgentViewDriver
    grading: GradingSubmitStub
    task: RolloutTaskSpec
    adapter: MockSessionAdapter
    digest: str


def _make_task(fixture: RolloutFixture) -> RolloutTaskSpec:
    public_payload = json.dumps({"instance_id": "w3b__fixture-1", "prompt": "Fix feature() in src/thing.py"}).encode()
    return RolloutTaskSpec(
        task_id="w3b__fixture-1",
        image=fixture.image,
        base_commit=fixture.base_commit,
        prompt="Fix feature() in src/thing.py so it returns fixed.",
        public_bundle_payload=public_payload,
        public_bundle_digest="sha256:" + "0" * 64,
        image_local_build=True,
        grading_spec=GradingEnvSpec(
            task_id="w3b__fixture-1",
            image=fixture.image,
            base_commit=fixture.base_commit,
            image_local_build=True,
            # private 评分材料（只在宿主侧；canary 绝不该出现在任何模型可见面）
            eval_script=f"#!/bin/bash\n# {PRIVATE_CANARY}\ncd /testbed && python tests/test_thing.py\n",
            parse_log=lambda text: (_ for _ in ()).throw(AssertionError("stub 不该调 parser")),
            grader_version="swebench-4.1.0",
            hygiene=HygieneRules(test_files=("tests/test_thing.py",)),
        ),
        time_budget_seconds=300,
    )


async def _run_formal(runtime: SandboxRuntime, fixture: RolloutFixture, *, profile=None) -> FormalRun:
    from repoharness2.adapters.slime.capture_wire import SessionPlaneDrainResult

    profile = profile or runtime.profile
    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    adapter_ref: dict[str, MockSessionAdapter] = {}

    def adapter_factory(hook, session_defaults):
        adapter = MockSessionAdapter(hook, session_defaults, turns, [dense_leaf_sample()])
        adapter_ref["adapter"] = adapter
        return adapter

    async def drain_owner(sid: str):
        return SessionPlaneDrainResult(
            physical_attempt_id=sid.removeprefix("s-"), revoke_enforced=True, inflight_at_drain_start=0,
            inflight_zero_confirmed=True, pending_turns=0, unfinalized_drafts=0, poison_clean=True,
            late_requests_rejected_after_revoke=0, turn_seq_high_water=2, weight_versions_seen=["5"],
            drain_owner="fake_adapter_loop",
        )

    driver = AgentViewDriver(fixture=fixture, runtime=runtime, adapter_ref=adapter_ref)
    grading = GradingSubmitStub()
    task = _make_task(fixture)
    digest = sp.runtime_profile_digest(profile, runtime.grader)
    orchestrator = RolloutOrchestrator(
        config=_formal_config(policy_version="5", execution_mode="fa_formal", adapter_url=profile.harness_adapter_url()),
        task_resolver=task,
        adapter_factory=adapter_factory,
        harness_driver=driver,
        grading_submit=grading,
        docker=run_docker,
        runtime_quiescence_barrier=_Barrier(),
        finalization_store=FakeFinalizationStore(),
        session_drain_owner=drain_owner,
        sandbox_profile=profile,
        egress_relay=runtime.relay,
        runtime_profile_digest=digest,
    )
    sample = FixtureSlimeSample(index=0)
    _stamp_fa_identity(sample)
    result = await rh2_custom_generate(_Args(orchestrator), sample, dict(SAMPLING_PARAMS))
    return FormalRun(result=result, audit=orchestrator.audits[-1], driver=driver, grading=grading, task=task,
                     adapter=adapter_ref["adapter"], digest=digest)


@pytest.fixture(scope="session")
def formal_run(sandbox_runtime: SandboxRuntime, rollout_fixture: RolloutFixture) -> FormalRun:
    return asyncio.run(_run_formal(sandbox_runtime, rollout_fixture))


def test_normal_formal_rollout_completes_under_profile_and_stamps_runtime_profile_digest(formal_run):
    fr = formal_run
    assert fr.driver.facts.get("AGENT_VIEW_OK") == "1", fr.driver.facts
    assert fr.audit.prelaunch_check["ok"] is True and fr.audit.harness_exit_code == 0
    assert "sandbox_prelaunch_check_passed" in [e.step for e in fr.audit.timeline]
    delivered = [s for s in fr.result if not getattr(s, "remove_sample", False)]
    assert delivered, [getattr(s, "metadata", None) for s in fr.result]
    assert all(s.metadata[sp.RUNTIME_PROFILE_DIGEST_METADATA_KEY] == fr.digest for s in delivered)
    assert fr.audit.runtime_profile_digest == fr.digest and fr.audit.finalized is not None
    assert fr.grading.calls and fr.grading.calls[0]["frozen_delta"] is not None
    assert fr.audit.lease.run_as_user == "agent"
    # 模型工具可见面：以 agent 身份、CapEff=0、能经 relay 到达上游、直连与公网都不通
    f = fr.driver.facts
    assert f["UID"] == "54321" and f["CAPEFF"].strip("0") == "" and f["NNP"] == "1"
    assert f["PROXY_BODY"] == "rh2-upstream-ok" and f["UPSTREAM_DIRECT"] == "DENIED" and f["PUBLIC"] == "DENIED"
    assert f["ROOT_DIR"] == "DENIED"
    assert fr.driver.adapter_urls == [fr.audit.launch_spec.model_proxy.base_url] and "rh2-egress-relay" in fr.driver.adapter_urls[0]


def test_git_future_solution_unrecoverable_from_agent_view_on_real_testbed(formal_run, rollout_fixture):
    f = formal_run.driver.facts
    assert (f["FUTURE_CATFILE"], f["FUTURE_TAG"], f["FUTURE_BRANCH"], f["FUTURE_GREP"]) == ("GONE", "GONE", "GONE", "ABSENT")
    assert f["LOSTFOUND"] == "0" and f["UNREACHABLE"] == "0" and f["REFLOG"] == "0" and f["REMOTES"] == "0"
    assert f["HISTORY"] == str(rollout_fixture.base_history_count)  # base 之前历史保留
    san = formal_run.audit.sandbox_setup["git_sanitize"]
    assert san["HEAD_AFTER"] == rollout_fixture.base_commit and int(san["REFS_DELETED"]) >= 2
    assert formal_run.audit.sandbox_setup["trusted_init"]["AGENT_UID"] == "54321"


def test_private_bundle_canary_absent_from_every_model_visible_surface(formal_run):
    fr = formal_run
    # 正向对照：canary 确实在宿主侧 private 评分材料里，且随评分提交到了 grader 侧
    assert PRIVATE_CANARY in fr.task.grading_spec.eval_script
    assert PRIVATE_CANARY in fr.grading.calls[0]["spec"].eval_script
    # 模型可见面逐项为空
    assert PRIVATE_CANARY not in fr.task.prompt and all(PRIVATE_CANARY not in p for p in fr.driver.prompts)
    assert PRIVATE_CANARY not in fr.task.public_bundle_payload.decode()
    assert fr.driver.facts["PRIVATE_GREP"] == "ABSENT" and fr.driver.facts["PRIVATE_ENV"] == "ABSENT"
    assert fr.driver.root_grep == ""  # root 视角全盘 grep 也没有
    assert PRIVATE_CANARY not in fr.driver.inspect_env_labels
    assert PRIVATE_CANARY not in json.dumps(fr.audit.launch_spec.model_dump(mode="json"))
    recorded_requests = json.dumps([t.response for t in fr.adapter.turns], default=str)
    assert PRIVATE_CANARY not in recorded_requests


def test_rollout_container_and_attempt_network_removed_after_attempt(formal_run, sandbox_runtime):
    audit = formal_run.audit
    assert audit.lease_released and audit.rollout_container_released_before_grading
    ps = _sh("docker", "ps", "-a", "--filter", f"name={audit.lease.container_id}", "--format", "{{.Names}}").stdout.strip()
    assert ps == ""
    nets = _sh("docker", "network", "ls", "--filter", f"label=rh2.run_id={sandbox_runtime.run_id}", "--format", "{{.Name}}").stdout.split()
    assert audit.egress_network not in nets
    assert "egress_network_removed" in [e.step for e in audit.timeline]
    assert not audit.cleanup_failures


async def test_prelaunch_failure_on_real_docker_stops_run_without_starting_harness(sandbox_runtime, rollout_fixture):
    """负例：把 relay 本身列进禁止目标——真实探针会连通它，核对判"egress 未阻断"→ typed fatal，harness 未启动，
    容器与网络已清。这证明核对读的是**实测**而不是配置。"""

    p = sandbox_runtime.profile
    bad = make_rollout_profile(
        model_proxy_upstream_host=p.model_proxy_upstream_host, model_proxy_upstream_port=p.model_proxy_upstream_port,
        forbidden_probe_targets=((p.relay_alias, p.model_proxy_listen_port),),
    )
    with pytest.raises(FatalExecutionInfrastructureError, match="sandbox_prelaunch_check_failed"):
        await _run_formal(sandbox_runtime, rollout_fixture, profile=bad)
    left = _sh("docker", "ps", "-a", "--filter", "name=rh2-rollout", "--format", "{{.Names}}").stdout.strip()
    assert left == ""
    nets = _sh("docker", "network", "ls", "--filter", f"label=rh2.run_id={sandbox_runtime.run_id}", "--format", "{{.Name}}").stdout.split()
    assert nets == []
