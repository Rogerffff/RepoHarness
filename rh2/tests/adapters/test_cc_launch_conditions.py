"""决策包 §8（2026-09-24 用户批准）切片 1：#10 工具面 / #9 auto-memory 的启动层单一写入者。

`cc_launch_conditions` 是正式启动与探针共用的来源：`--tools` 白名单拼进 CC 命令（vendored launch_flags 之后、
进程级 SLIME_AGENT_CC_EXTRA_ARGS 之前），`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 并入 CC 子进程环境（vendored
static_env 之后、进程级 extra envs 与逐 execution 注入之前）。真实 CC 的请求形状变化（tools 恰为五个、无 Skill
清单、system 无 "# Memory"、init 无 memory_paths）由真机验收记录在 Brief。
"""

from __future__ import annotations

import json

import pytest

from repoharness2.adapters.slime import bringup
from repoharness2.adapters.slime import cc_launch_conditions as cc
from repoharness2.adapters.slime import docker_sandbox as ds


def test_tool_surface_is_the_five_core_tools_as_a_tools_whitelist():
    assert cc.CC_TOOL_SURFACE == ("Bash", "Read", "Edit", "Write", "NotebookEdit")
    assert cc.cc_tool_surface_args() == "--tools Bash,Read,Edit,Write,NotebookEdit"
    with pytest.raises(ValueError):
        cc.cc_tool_surface_args(("Bash", "Read Edit"))
    with pytest.raises(ValueError):
        cc.cc_tool_surface_args(())


def test_launch_env_disables_auto_memory_below_process_and_per_execution_layers(monkeypatch):
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    env = bringup.claude_code_launch_env(adapter_url="http://relay:18001", session_id="tok", model_label="slime-actor", env_injections={})
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"  # #9
    assert env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"  # vendored static_env 仍在
    # 优先级：vendored static_env < RH2 启动常量 < 进程级 extra envs < 逐 execution 注入
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", json.dumps({"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "0"}))
    env = bringup.claude_code_launch_env(adapter_url="http://relay:18001", session_id="tok", model_label="slime-actor", env_injections={})
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "0"
    env = bringup.claude_code_launch_env(adapter_url="http://relay:18001", session_id="tok", model_label="slime-actor",
                                         env_injections={"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"


class _Sandbox:
    container_name = "rollout-fake"

    async def exec(self, cmd, *, user="root", env=None, timeout=120, check=False, idempotent=True):
        return 0, "", ""

    async def write_file(self, path, content, *, user="root"):
        return None


async def test_launch_command_carries_the_tool_surface_between_launch_flags_and_extra_args(monkeypatch):
    from slime.agent import sandbox as slime_sandbox
    from slime.agent.harness import ClaudeCodeHarness

    async def fake_ensure(sb, workdir):
        return None

    async def fake_write_config(self, sb, ctx):
        return None

    seen: dict = {}

    async def fake_collect(*, container_name, user, workdir, env, cmd, stdout_path, stderr_path, deadline_seconds,
                           time_budget_exit_code=-1, progress=None, socket_path=None, settle_seconds=None):
        seen.update({"cmd": cmd, "env": dict(env)})
        return ds.ExecCollectedRun("exec-1", 0, "exited", str(stdout_path), str(stderr_path), 1, 0, True, None, "", 0.1)

    monkeypatch.setattr(slime_sandbox, "ensure_agent_user", fake_ensure)
    monkeypatch.setattr(ClaudeCodeHarness, "write_config", fake_write_config)
    monkeypatch.setattr(ds, "run_exec_collected", fake_collect)
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")
    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ARGS", "--max-turns 25")
    code = await bringup.launch_claude_code(_Sandbox(), workdir="/testbed", session_id="tok", adapter_url="http://relay:1", prompt="fix",
                                            time_budget_sec=30, env_injections={"BASH_ENV": "/rh2/bash_env", "HOME": "/home/agent"})
    assert code == 0
    cmd = seen["cmd"]
    flags_end = cmd.index(ClaudeCodeHarness.launch_flags) + len(ClaudeCodeHarness.launch_flags)
    assert cmd[flags_end:].strip().startswith("--tools Bash,Read,Edit,Write,NotebookEdit")  # launch_flags 之后
    assert cmd.endswith("--max-turns 25") and cmd.index("--tools ") < cmd.index("--max-turns")  # extra args 之前
    assert "--disallowedTools" not in cmd  # 工具面不再来自脚本里的 disallow 清单
    assert seen["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1" and seen["env"]["BASH_ENV"] == "/rh2/bash_env"


def test_no_other_writer_of_the_tool_surface_in_rh2_sources():
    """单一写入者：rh2 源码里只有 cc_launch_conditions 定义工具面；scripts/实验里的 --disallowedTools 不是来源。"""
    from pathlib import Path

    src = Path(bringup.__file__).resolve().parents[2]
    hits = [p for p in src.rglob("*.py") if "--tools " in p.read_text(encoding="utf-8", errors="replace") and p.name != "cc_launch_conditions.py"]
    assert hits == [], hits
