"""基座探针修复 #1（2026-09-23）：actor 拿到项目解释器——激活文件可读不可写、逐 execution 环境注入、启动前解释器核对。

修复前的两处缺口（交接包 §1，已在验证机复现）：激活文件写在 agent 不可读的 /root；BASH_ENV 只写进
HarnessLaunchSpec、没有运输到 CC 子进程。本文件钉住修复后的接线：

- `materialize.BASH_ENV_PATH` 在 /rh2 下；编排把任务面的激活脚本写进去并 chmod 0644；
- 启动前探针核对 ACTIVATION_READ=1 / ACTIVATION_WRITE=DENIED；
- 首次 census 之后、harness 启动之前的激活探针：`python` 必须落在任务面声明的解释器前缀之下，
  否则 typed task-local `rollout_activation_check_failed`；
- HarnessLaunchSpec.env_injections（HOME + BASH_ENV）经编排 → driver → 无状态 `launch_claude_code` 显式运输，
  不经过进程级 SLIME_AGENT_CC_EXTRA_ENVS，也不放进单例（Codex SR1：并发 execution 互不串扰）。
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
from types import SimpleNamespace

import pytest

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))  # tests/：sandbox_test_support
from sandbox_test_support import make_rollout_profile  # noqa: E402

from repoharness2.adapters.slime import bringup  # noqa: E402
from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.generate import SlimeBindingError  # noqa: E402
from repoharness2.adapters.slime.outcome_producer import FAILURE_CODE_TERMINATION_MAP  # noqa: E402
from repoharness2.envpack import materialize  # noqa: E402

from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS,
    TASK_ID_DENSE,
    FakeRolloutDocker,
    _Args,
    build_dense_chain,
    make_task,
)
from test_w3b_sandbox_profile import _formal_chain  # noqa: E402  fa_formal 链：profile + 屏障 + 真实版本事实

PROFILE = make_rollout_profile()


# ---------------------------------------------------------------------------
# 常量与任务面
# ---------------------------------------------------------------------------


def test_activation_file_lives_under_rh2_and_task_spec_carries_source_specific_activation():
    assert materialize.BASH_ENV_PATH == "/rh2/bash_env"  # 不在隐藏的 /root 下
    assert "activate testbed" in materialize.BASH_ENV_CONTENT
    task = make_task(TASK_ID_DENSE)
    assert task.env_activation_script == materialize.BASH_ENV_CONTENT
    assert task.expected_interpreter_prefix == materialize.SWE_GYM_INTERPRETER_PREFIX == "/opt/miniconda3/envs/testbed"
    venv = dataclasses.replace(task, env_activation_script="source /testbed/.venv/bin/activate\n",
                               expected_interpreter_prefix="/testbed/.venv")
    assert venv.env_activation_script.startswith("source /testbed/.venv")  # R2E 形态由任务面给，不写死 conda


# ---------------------------------------------------------------------------
# 启动前探针：激活文件可读 + 不可写
# ---------------------------------------------------------------------------


def test_prelaunch_probe_checks_activation_file_only_when_asked():
    plain = sp.rollout_prelaunch_probe_script(PROFILE)
    assert "ACTIVATION_" not in plain
    with_file = sp.rollout_prelaunch_probe_script(PROFILE, activation_file="/rh2/bash_env")
    assert "[ -r /rh2/bash_env ]" in with_file and ": >> /rh2/bash_env" in with_file
    assert "ACTIVATION_READ=" in with_file and "ACTIVATION_WRITE=DENIED" in with_file


@pytest.mark.parametrize(
    ("facts", "violation_fragment"),
    [
        ({"ACTIVATION_READ": "1", "ACTIVATION_WRITE": "DENIED"}, None),
        ({"ACTIVATION_READ": "0", "ACTIVATION_WRITE": "DENIED"}, "不可读"),
        ({"ACTIVATION_READ": "1", "ACTIVATION_WRITE": "WRITABLE"}, "可写"),
        ({}, "不可读"),
    ],
)
def test_check_rollout_probe_activation_rules(facts, violation_fragment):
    base = {"RH2_PROBE_OK": "1", "UID": str(PROFILE.agent_uid), "CAPEFF": "0", "CAPPRM": "0"}
    violations = sp.check_rollout_probe({**base, **facts}, PROFILE, expected_head=None, require_workdir=False,
                                        activation_file="/rh2/bash_env")
    activation = [v for v in violations if "激活文件" in v]
    if violation_fragment is None:
        assert activation == []
    else:
        assert activation and violation_fragment in activation[0]
    # 不要求核对时（legacy 调用方）：同一事实不产生激活相关违例
    assert not [v for v in sp.check_rollout_probe({**base, **facts}, PROFILE, expected_head=None, require_workdir=False)
                if "激活文件" in v]


# ---------------------------------------------------------------------------
# 首次 census 之后的解释器核对（CC 同形 env）
# ---------------------------------------------------------------------------


def test_activation_probe_script_uses_the_shared_agent_env_and_declared_prefix():
    env = sp.agent_shell_env(PROFILE, activation_file="/rh2/bash_env")
    assert env == {"HOME": f"/home/{PROFILE.agent_user}", "BASH_ENV": "/rh2/bash_env"}
    script = sp.rollout_activation_probe_script(env, expected_interpreter_prefix="/opt/miniconda3/envs/testbed")
    # HOME 与 BASH_ENV 在内层 bash 启动**之前**就位；不写字节码；cwd 不在工作区；只 import sys
    assert "env BASH_ENV=/rh2/bash_env HOME=/home/agent PYTHONDONTWRITEBYTECODE=1 bash -c" in script
    assert "cd /tmp" in script and "import sys" in script and "import conan" not in script
    assert "ACT_EXPECTED_PREFIX=/opt/miniconda3/envs/testbed" in script


@pytest.mark.parametrize(
    ("facts", "ok"),
    [
        ({"ACT_SYS_EXECUTABLE": "/opt/miniconda3/envs/testbed/bin/python", "RH2_ACTIVATION_PROBE_OK": "1"}, True),
        ({"ACT_SYS_EXECUTABLE": "/opt/miniconda3/bin/python", "RH2_ACTIVATION_PROBE_OK": "1"}, False),  # base 解释器
        ({"ACT_PYTHON": "", "RH2_ACTIVATION_PROBE_OK": "1"}, False),  # 没有 python
        ({"ACT_SYS_EXECUTABLE": "/opt/miniconda3/envs/testbed/bin/python"}, False),  # 探针没跑完
        ({"ACT_SYS_EXECUTABLE": "/opt/miniconda3/envs/testbed-old/bin/python", "RH2_ACTIVATION_PROBE_OK": "1"}, False),  # 前缀要按目录边界匹配
    ],
)
def test_check_rollout_activation(facts, ok):
    violations = sp.check_rollout_activation(facts, expected_interpreter_prefix="/opt/miniconda3/envs/testbed/")
    assert (violations == []) is ok, violations


# ---------------------------------------------------------------------------
# 编排：写入、探针、注入运输（profile 路径的 dense chain）
# ---------------------------------------------------------------------------


async def test_orchestrator_writes_activation_from_task_spec_checks_it_and_injects_env_per_execution():
    docker = FakeRolloutDocker()
    task = dataclasses.replace(
        make_task(TASK_ID_DENSE), env_activation_script="source /testbed/.venv/bin/activate\n",
        expected_interpreter_prefix="/testbed/.venv",
    )
    docker.profile_fake.activation_overrides = {
        "ACT_SYS_EXECUTABLE": "/testbed/.venv/bin/python", "ACT_SYS_PREFIX": "/testbed/.venv",
    }
    chain = _formal_chain(task=task, docker=docker)
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert result[0].reward == 1.0
    # ① 写入：内容取自任务面，随后 chmod 0644（root 写、agent 只读）
    assert docker.writes[materialize.BASH_ENV_PATH] == b"source /testbed/.venv/bin/activate\n"
    write_calls = [c for c in docker.calls if c[0] == "exec" and f"cat > {materialize.BASH_ENV_PATH}" in c[-1]]
    assert write_calls and f"chmod 0644 {materialize.BASH_ENV_PATH}" in write_calls[0][-1]
    # ② 启动前探针带激活文件核对；③ 激活探针在基线 census 之后、harness 之前，且核的是任务面声明的前缀
    probe_scripts = [c[-1] for c in docker.calls if c[0] == "exec" and "rollout-prelaunch-probe" in c[-1]]
    assert probe_scripts and "ACTIVATION_READ" in probe_scripts[0]
    exec_ids = [sid for (_c, _u, sid) in docker.profile_fake.exec_scripts]
    assert exec_ids.index("rollout-prelaunch-probe") < exec_ids.index("rollout-activation-probe")
    activation_scripts = [c[-1] for c in docker.calls if c[0] == "exec" and "rollout-activation-probe" in c[-1]]
    assert activation_scripts and "ACT_EXPECTED_PREFIX=/testbed/.venv" in activation_scripts[0]
    audit = chain.orchestrator.audits[0]
    assert audit.activation_check["ok"] is True and audit.activation_check["expected_interpreter_prefix"] == "/testbed/.venv"
    # SR3 顺序：安全探针（census 之前，不动）< 基线 census（find + sha256sum）< 激活核对（census 之后、harness 之前）
    scripts_in_order = [c[-1] for c in docker.calls if c[0] == "exec"]
    prelaunch_idx = next(i for i, sc in enumerate(scripts_in_order) if "rollout-prelaunch-probe" in sc)
    census_idx = next(i for i, sc in enumerate(scripts_in_order) if "find ." in sc and "sha256sum" in sc)
    activation_idx = next(i for i, sc in enumerate(scripts_in_order) if "rollout-activation-probe" in sc)
    assert prelaunch_idx < census_idx < activation_idx
    # ④ 注入：launch spec 的 env_injections（HOME + BASH_ENV）原样运输到 driver；不经进程级变量
    (call,) = chain.driver.calls
    assert call["env_injections"] == {"HOME": "/home/agent", "BASH_ENV": materialize.BASH_ENV_PATH}
    assert call["env_injections"] == dict(audit.launch_spec.env_injections)
    assert "BASH_ENV" not in os.environ.get("SLIME_AGENT_CC_EXTRA_ENVS", "")
    assert call["harness_log_dir"] is None or call["harness_log_dir"].endswith("/harness")


async def test_legacy_chain_without_profile_injects_only_bash_env_and_skips_activation_check():
    chain = build_dense_chain()  # 默认配置无 sandbox profile（无可信初始化 / 探针面）
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert result[0].reward == 1.0
    (call,) = chain.driver.calls
    assert call["env_injections"] == {"BASH_ENV": materialize.BASH_ENV_PATH}
    assert chain.orchestrator.audits[0].activation_check is None
    assert chain.docker.writes[materialize.BASH_ENV_PATH] == materialize.BASH_ENV_CONTENT.encode()


async def test_activation_check_failure_is_task_local_and_blocks_harness():
    docker = FakeRolloutDocker()
    docker.profile_fake.activation_overrides = {"ACT_SYS_EXECUTABLE": "/opt/miniconda3/bin/python"}  # base 解释器
    chain = _formal_chain(docker=docker)
    result = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    (failure,) = chain.orchestrator.audits[0].failure_records
    assert "rollout_activation_check_failed" in failure.detail and "激活未生效" in failure.detail
    assert result[0].remove_sample is True and chain.driver.calls == [] and chain.grading.calls == []
    assert len(docker.removed) == 1  # 容器照常回收
    assert FAILURE_CODE_TERMINATION_MAP["rollout_activation_check_failed"] == ("sandbox_failure", "sandbox_crash")
    assert chain.orchestrator.audits[0].activation_check["ok"] is False


def test_execution_audit_record_persists_activation_check(tmp_path):
    audit = SimpleNamespace()
    # 用真实 write_execution_audit_record 的最小 audit 替身太重：只核序列化键在生产函数源码里（真实落盘在 chain 用例覆盖）
    import inspect

    src = inspect.getsource(bringup.write_execution_audit_record)
    assert '"activation_check": getattr(audit, "activation_check", None)' in src
    del audit


# ---------------------------------------------------------------------------
# driver → 无状态启动函数：逐 execution 注入，不串扰
# ---------------------------------------------------------------------------


class _Sandbox:
    """ClaudeCodeDriver.run 只读 .container_name；exec/write_file 由 DockerSandbox 承担，这里被 monkeypatch 短路。"""

    container_name = "rollout-fake"


def test_claude_code_launch_env_merge_order(monkeypatch):
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", json.dumps({"CLAUDE_CODE_FOO": "guard", "BASH_ENV": "/process/global"}))
    env = bringup.claude_code_launch_env(
        adapter_url="http://relay:18001", session_id="tok", model_label="slime-actor",
        env_injections={"BASH_ENV": "/rh2/bash_env", "HOME": "/home/agent"},
    )
    assert env["ANTHROPIC_BASE_URL"] == "http://relay:18001" and env["ANTHROPIC_AUTH_TOKEN"] == "tok"
    assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1" and env["CLAUDE_CODE_FOO"] == "guard"
    assert env["BASH_ENV"] == "/rh2/bash_env" and env["HOME"] == "/home/agent"  # 逐 execution 注入优先级最高


async def test_launch_claude_code_is_stateless_and_concurrent_executions_keep_their_own_env(monkeypatch, tmp_path):
    from slime.agent import sandbox as slime_sandbox
    from slime.agent.harness import ClaudeCodeHarness

    from repoharness2.adapters.slime import docker_sandbox as ds

    seen: list[dict] = []

    async def fake_ensure(sb, workdir):
        return None

    async def fake_write_config(self, sb, ctx):
        return None

    async def fake_collect(argv, *, stdout_path, stderr_path, deadline_seconds, time_budget_exit_code=-1, chunk_size=65536):
        env = {a.split("=", 1)[0]: a.split("=", 1)[1] for i, a in enumerate(argv) if i > 0 and argv[i - 1] == "-e"}
        await asyncio.sleep(0.01 if env["BASH_ENV"].endswith("A") else 0.0)  # 交错
        seen.append({"argv": list(argv), "cmd": argv[-1], "env": env, "budget": deadline_seconds, "stdout": str(stdout_path)})
        return ds.HostCollectedRun(0, 0, "container_process_exit", str(stdout_path), str(stderr_path), 1, 0, True, None, "", 0.1)

    monkeypatch.setattr(slime_sandbox, "ensure_agent_user", fake_ensure)
    monkeypatch.setattr(ClaudeCodeHarness, "write_config", fake_write_config)
    monkeypatch.setattr(ds, "run_host_collected", fake_collect)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ARGS", "--max-turns 25")

    await asyncio.gather(
        bringup.launch_claude_code(_Sandbox(), workdir="/testbed", session_id="tokA", adapter_url="http://relay:1",
                                   prompt="fix A", time_budget_sec=100, env_injections={"BASH_ENV": "/rh2/A", "HOME": "/home/agent"},
                                   harness_log_dir=str(tmp_path / "A")),
        bringup.launch_claude_code(_Sandbox(), workdir="/testbed", session_id="tokB", adapter_url="http://relay:1",
                                   prompt="fix B", time_budget_sec=200, env_injections={"BASH_ENV": "/rh2/B", "HOME": "/home/agent"},
                                   harness_log_dir=str(tmp_path / "B")),
    )
    by_token = {s["env"]["ANTHROPIC_AUTH_TOKEN"]: s for s in seen}
    assert by_token["tokA"]["env"]["BASH_ENV"] == "/rh2/A" and by_token["tokB"]["env"]["BASH_ENV"] == "/rh2/B"
    assert by_token["tokA"]["budget"] == 100 and by_token["tokB"]["budget"] == 200
    assert by_token["tokA"]["stdout"].endswith("/A/trajectory.jsonl") and by_token["tokB"]["stdout"].endswith("/B/trajectory.jsonl")
    for s in seen:
        assert s["cmd"].startswith("exec /usr/local/bin/claude -p ") and "--output-format stream-json" in s["cmd"]
        assert s["cmd"].endswith("--max-turns 25")
    # 单例上没有留下任何逐 execution 状态
    harness = ClaudeCodeHarness()
    assert not any(k for k in vars(harness) if "env" in k.lower() or "inject" in k.lower())


async def test_driver_passes_env_injections_to_the_launch_function(monkeypatch):
    received: dict = {}

    async def fake_install(self, sb, *, timeout=180):
        return None

    async def fake_launch(sb, **kwargs):
        received.update(kwargs)
        return 0

    monkeypatch.setattr(bringup.ClaudeCodeDriver, "_install_native_cli", fake_install)
    monkeypatch.setattr(bringup, "launch_claude_code", fake_launch)
    monkeypatch.setattr(bringup.DockerSandbox, "exec", _noop_exec)
    code = await bringup.ClaudeCodeDriver().run(
        _Sandbox(), workdir="/testbed", session_id="tok", adapter_url="http://relay:1", time_budget_sec=1800,
        prompt="p", env_injections={"BASH_ENV": "/rh2/bash_env", "HOME": "/home/agent"}, harness_log_dir="/tmp/x/harness",
    )
    assert code == 0
    assert received["env_injections"] == {"BASH_ENV": "/rh2/bash_env", "HOME": "/home/agent"}
    assert received["session_id"] == "tok" and received["prompt"] == "p"


async def _noop_exec(self, cmd, *, user="root", env=None, timeout=120, check=False, idempotent=True):
    return 0, "", ""


def test_typed_error_class_is_the_binding_error():
    assert issubclass(SlimeBindingError, RuntimeError)
