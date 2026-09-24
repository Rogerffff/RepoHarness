"""E1（I25）：同一执行内的重复权限初始化——可信初始化写完成标记，driver 预建与 launch 的 vendored ensure_agent_user
先只读核对（非递归）再决定跳过或回退整条命令；vendored 函数不改，legacy 路径命令逐字不变。"""

from __future__ import annotations

import os
import subprocess
import uuid

import pytest

from repoharness2.adapters.slime import bringup as bringup_mod
from repoharness2.adapters.slime import docker_sandbox
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver, ensure_agent_user_once
from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS
from repoharness2.adapters.slime.sandbox_profile import (
    AGENT_USER_READY_MARKER,
    RolloutSandboxProfile,
    agent_user_init_mode,
    agent_user_init_script,
    agent_user_ready_marker_script,
    agent_user_recheck_script,
    agent_user_recheck_state,
    rollout_trusted_init_script,
)

VENDORED_CMD = (
    "id agent >/dev/null 2>&1 || useradd -m -s /bin/bash agent && "
    "chown -R agent:agent /home/agent /testbed && "
    "git config --system --add safe.directory '*' && id agent"
)


class FakeSb:
    """记录 exec；核对脚本按预设状态作答，其它命令返回 0。"""

    container_name = "c"

    def __init__(self, recheck_state: str | None = "ok"):
        self.recheck_state = recheck_state
        self.calls: list[tuple[str, str, int]] = []

    async def exec(self, cmd, *, user="root", env=None, timeout=120, check=False, idempotent=True):  # noqa: ARG002
        self.calls.append((cmd, user, timeout))
        if "RH2_AGENT_USER_RECHECK" in cmd:
            out = "" if self.recheck_state is None else f"RH2_AGENT_USER_RECHECK={self.recheck_state}\nAGENT_UID=54321\n"
            return 0, out, ""
        return 0, "", ""


def _chown_calls(calls):
    return [c for c, _u, _t in calls if "chown -R" in c]


# ---- 脚本本身 --------------------------------------------------------------------------------------------------------


def test_trusted_init_writes_the_marker_after_the_workdir_chown_and_before_ok():
    prof = RolloutSandboxProfile(model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1)
    script = rollout_trusted_init_script(prof)
    i_chown = script.index("chown -R 54321:54321 /testbed")
    i_marker = script.index(AGENT_USER_READY_MARKER)
    i_ok = script.index('echo "RH2_INIT_OK=1"')
    assert i_chown < i_marker < i_ok
    assert 'echo "uid=$(id -u agent)"' in script and 'echo "workdir=/testbed"' in script
    assert "RH2_INIT_ERROR=ready_marker_failed" in script


def test_recheck_script_is_read_only_and_non_recursive():
    script = agent_user_recheck_script("/testbed")
    assert "chown" not in script and "useradd" not in script and "find " not in script
    assert "git config" not in script  # Codex R3 文案修正：复用分支不再跑不幂等的 `git config --system --add`
    init = agent_user_init_script("/testbed")
    assert init.count("git config --system --add") == 1 and init.index("RH2_AGENT_USER_INIT=reused") < init.index("git config")
    assert 'stat -c %u "$WD"' in script and 'stat -c %u "/home/$U"' in script
    for state in ("no_marker", "workdir_mismatch", "uid_mismatch", "owner_mismatch", "ok"):
        assert f"echo {state}; return" in script or (state == "ok" and "  echo ok\n" in script)
    assert 'echo "RH2_AGENT_USER_RECHECK=$STATE"' in script and script.rstrip().endswith("exit 0")
    assert agent_user_recheck_state("x\nRH2_AGENT_USER_RECHECK=ok\nAGENT_UID=1\n") == "ok"
    assert agent_user_recheck_state("") == "unreadable" and agent_user_recheck_state("RH2_AGENT_USER_RECHECK=") == "unreadable"
    assert "install -d -m 0755 -o 0 -g 0 /rh2" in agent_user_ready_marker_script("/testbed")


def test_driver_init_script_embeds_the_unchanged_command_after_the_recheck_and_marks_both_modes():
    script = agent_user_init_script("/testbed")
    assert VENDORED_CMD in script  # 原整条命令逐字不变
    i_recheck, i_reused, i_cmd = script.index("RH2_AGENT_USER_RECHECK="), script.index("RH2_AGENT_USER_INIT=reused; exit 0"), script.index(VENDORED_CMD)
    i_marker, i_chown = script.index("install -d -m 0755 -o 0 -g 0 /rh2"), script.index("echo RH2_AGENT_USER_INIT=chown")
    assert i_recheck < i_reused < i_cmd < i_marker < i_chown
    assert script.count("chown -R") == 1  # 复用分支里没有 chown
    assert agent_user_init_mode("RH2_AGENT_USER_RECHECK=ok\nRH2_AGENT_USER_INIT=reused\n") == "reused"
    assert agent_user_init_mode("RH2_AGENT_USER_RECHECK=no_marker\n") == "unreadable"


# ---- launch 路径（vendored ensure_agent_user 之前的核对） -----------------------------------------------------------------


async def test_launch_path_reuses_the_completed_init_and_skips_the_recursive_chown():
    sb = FakeSb("ok")
    facts = await ensure_agent_user_once(sb, "/testbed")
    assert facts["mode"] == "reused" and facts["recheck"] == "ok" and facts["seconds"] >= 0
    assert _chown_calls(sb.calls) == [] and len(sb.calls) == 1 and sb.calls[0][1] == "root"


@pytest.mark.parametrize("state", ["no_marker", "owner_mismatch", "uid_mismatch", "workdir_mismatch", None])
async def test_launch_path_falls_back_to_the_vendored_command_when_recheck_does_not_pass(state):
    sb = FakeSb(state)
    facts = await ensure_agent_user_once(sb, "/testbed")
    assert facts["mode"] == "chown" and facts["recheck"] == (state or "unreadable")
    assert _chown_calls(sb.calls) == [VENDORED_CMD]  # vendored 命令逐字不变（60s 写死也不变）
    assert sb.calls[-1][2] == 60


# ---- driver 预建（bringup.ClaudeCodeDriver.run）：一次 exec，模式进 launch facts ------------------------------------


async def _run_driver(monkeypatch, *, init_output: str):
    runs: list[tuple[str, float]] = []

    async def install(self, sb, **kwargs):  # noqa: ARG001
        return None

    async def fake_run(*args, input_bytes=None, timeout=None):  # noqa: ARG001
        cmd = args[-1]
        runs.append((cmd, timeout))
        if "RH2_AGENT_USER_INIT" in cmd:
            return 0, init_output, ""
        return 0, "", ""

    launched: list[dict] = []

    async def fake_launch(sb, **kwargs):  # noqa: ARG001
        launched.append(kwargs)
        return 0

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(docker_sandbox, "_run", fake_run)
    monkeypatch.setattr(bringup_mod, "launch_claude_code", fake_launch)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    facts: dict = {}
    token = HARNESS_LAUNCH_FACTS.set(facts)
    try:
        code = await ClaudeCodeDriver().run(
            type("S", (), {"container_name": "c"})(), workdir="/testbed", session_id="tok",
            adapter_url="http://relay:1", time_budget_sec=300, prompt="p",
        )
    finally:
        HARNESS_LAUNCH_FACTS.reset(token)
    assert code == 0 and len(launched) == 1
    return runs, facts


async def test_driver_runs_one_init_exec_and_records_reuse(monkeypatch):
    runs, facts = await _run_driver(monkeypatch, init_output="RH2_AGENT_USER_RECHECK=ok\nRH2_AGENT_USER_INIT=reused\n")
    init_calls = [(c, t) for c, t in runs if "RH2_AGENT_USER_INIT" in c]
    assert len(init_calls) == 1 and init_calls[0][1] == pytest.approx(300, abs=1)  # 一次 exec，上限仍为 min(900, 剩余预算)
    assert VENDORED_CMD in init_calls[0][0]
    assert facts["agent_user_init_bootstrap"]["mode"] == "reused" and facts["agent_user_init_bootstrap"]["recheck"] == "ok"


async def test_driver_records_the_chown_mode_on_the_legacy_path(monkeypatch):
    runs, facts = await _run_driver(monkeypatch, init_output="RH2_AGENT_USER_RECHECK=no_marker\nRH2_AGENT_USER_INIT=chown\n")
    assert facts["agent_user_init_bootstrap"] == {"mode": "chown", "recheck": "no_marker", "seconds": facts["agent_user_init_bootstrap"]["seconds"]}
    assert facts["agent_user_init_bootstrap"]["seconds"] >= 0


# ---- R3：两项初始化事实随 audit 落盘（真实编排 + writer，假 Docker / driver / 模型 / 评分） ----------------------------


def _e1_facts():
    return {
        "agent_user_init_bootstrap": {"mode": "reused", "recheck": "ok", "seconds": 0.1234},
        "agent_user_init_launch": {"mode": "chown", "recheck": "no_marker", "seconds": 0.0123},
    }


async def test_init_facts_travel_from_launch_facts_to_the_audit_and_the_persisted_record(tmp_path):
    import json

    from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain

    from repoharness2.adapters.slime.bringup import write_execution_audit_record

    audit_path = tmp_path / "execution_audit.jsonl"
    chain = build_dense_chain(audit_sink=lambda audit: write_execution_audit_record(None, audit, audit_path))
    original = chain.orchestrator._harness_driver

    class EmitE1Driver:
        async def run(self, *args, **kwargs):
            facts = HARNESS_LAUNCH_FACTS.get()
            assert facts is not None
            facts.update(_e1_facts())
            return await original.run(*args, **kwargs)

    chain.orchestrator._harness_driver = EmitE1Driver()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[-1]
    expected = {"bootstrap": _e1_facts()["agent_user_init_bootstrap"], "launch": _e1_facts()["agent_user_init_launch"]}
    assert audit.agent_user_init == expected
    persisted = json.loads(audit_path.read_text().splitlines()[-1])
    assert persisted["agent_user_init"] == expected


def test_absorb_keeps_only_the_phases_that_ran_and_survives_a_cancel_before_the_stream():
    from repoharness2.adapters.slime.generate import RolloutAudit, RolloutOrchestrator

    audit = RolloutAudit.__new__(RolloutAudit)
    audit.agent_user_init = None
    audit.harness_log = None
    audit.artifact_paths = []
    # 引导已完成、起流前被取消：只有 bootstrap 一项，没有 harness_log → 仍进 audit，launch 缺席不补零
    RolloutOrchestrator._absorb_harness_log(audit, {"agent_user_init_bootstrap": {"mode": "reused", "recheck": "ok", "seconds": 0.5}})
    assert audit.agent_user_init == {"bootstrap": {"mode": "reused", "recheck": "ok", "seconds": 0.5}} and audit.harness_log is None
    # 什么都没交出（替身驱动）→ 保持 None
    audit.agent_user_init = None
    RolloutOrchestrator._absorb_harness_log(audit, {"launch_attempted": False})
    assert audit.agent_user_init is None


# ---- 真容器（本机 docker + 镜像在场才跑；不拉镜像） ---------------------------------------------------------------------

IMAGE = os.environ.get("RH2_EXEC_TEST_IMAGE", "python:3.12-slim")


def _sh(*args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)


DOCKER_AVAILABLE = _sh("docker", "info", timeout=30).returncode == 0
IMAGE_PRESENT = DOCKER_AVAILABLE and _sh("docker", "image", "inspect", IMAGE, timeout=30).returncode == 0
docker_only = pytest.mark.skipif(not IMAGE_PRESENT, reason=f"本机 docker 不可用或没有 {IMAGE}（测试不拉镜像）")


@pytest.fixture(scope="module")
def container():
    name = f"rh2-e1-test-{uuid.uuid4().hex[:8]}"
    run = _sh("docker", "run", "-d", "--init", "--name", name, IMAGE, "sleep", "600")
    assert run.returncode == 0, run.stderr
    try:
        yield name
    finally:
        _sh("docker", "rm", "-f", name)


def _exec(container: str, script: str, *, user: str = "root") -> subprocess.CompletedProcess:
    return _sh("docker", "exec", "-u", user, container, "bash", "-c", script)


@pytest.mark.docker
@docker_only
def test_real_container_recheck_states_and_marker_ownership(container):
    prof = RolloutSandboxProfile(model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=1)
    assert _exec(container, "mkdir -p /testbed && echo hi > /testbed/f").returncode == 0
    # slim 镜像没有 git：给 vendored 命令里的 `git config --system …` 一个空壳（生产镜像自带 git；本测试不测 git）
    _exec(container, "command -v git >/dev/null 2>&1 || { printf '#!/bin/sh\\nexit 0\\n' > /usr/local/bin/git; chmod +x /usr/local/bin/git; }")
    init = _exec(container, rollout_trusted_init_script(prof))
    assert init.returncode == 0 and "RH2_INIT_OK=1" in init.stdout, init.stdout + init.stderr
    ok = _exec(container, agent_user_recheck_script("/testbed"))
    assert ok.returncode == 0 and "RH2_AGENT_USER_RECHECK=ok" in ok.stdout and "AGENT_UID=54321" in ok.stdout
    # agent 造不出 / 改不了标记
    assert _exec(container, f"echo x > {AGENT_USER_READY_MARKER}", user="54321").returncode != 0
    assert _exec(container, "touch /rh2/other", user="54321").returncode != 0
    # 顶层属主被改 → owner_mismatch；改回 → ok
    _exec(container, "chown 0:0 /testbed")
    assert "RH2_AGENT_USER_RECHECK=owner_mismatch" in _exec(container, agent_user_recheck_script("/testbed")).stdout
    _exec(container, "chown 54321:54321 /testbed")
    assert "RH2_AGENT_USER_RECHECK=ok" in _exec(container, agent_user_recheck_script("/testbed")).stdout
    assert "RH2_AGENT_USER_RECHECK=workdir_mismatch" in _exec(container, agent_user_recheck_script("/other")).stdout
    _exec(container, f"rm -f {AGENT_USER_READY_MARKER}")
    assert "RH2_AGENT_USER_RECHECK=no_marker" in _exec(container, agent_user_recheck_script("/testbed")).stdout
    # legacy 路径的标记脚本（uid 取自 id -u agent）
    assert _exec(container, agent_user_ready_marker_script("/testbed")).returncode == 0
    assert "RH2_AGENT_USER_RECHECK=ok" in _exec(container, agent_user_recheck_script("/testbed")).stdout
    # driver 单次 exec 脚本：无标记 → 整条命令 + 写标记（chown 改 ctime）；有标记 → reused（ctime 不变 = 没再 chown）
    _exec(container, f"rm -f {AGENT_USER_READY_MARKER}")
    first = _exec(container, agent_user_init_script("/testbed"))
    assert first.returncode == 0 and "RH2_AGENT_USER_INIT=chown" in first.stdout, first.stdout + first.stderr
    ctime_after_chown = _exec(container, "stat -c %z /testbed/f").stdout
    second = _exec(container, agent_user_init_script("/testbed"))
    assert second.returncode == 0 and "RH2_AGENT_USER_INIT=reused" in second.stdout, second.stdout + second.stderr
    assert _exec(container, "stat -c %z /testbed/f").stdout == ctime_after_chown
    _exec(container, f"rm -f {AGENT_USER_READY_MARKER}")
    third = _exec(container, agent_user_init_script("/testbed"))
    assert "RH2_AGENT_USER_INIT=chown" in third.stdout and _exec(container, "stat -c %z /testbed/f").stdout != ctime_after_chown
