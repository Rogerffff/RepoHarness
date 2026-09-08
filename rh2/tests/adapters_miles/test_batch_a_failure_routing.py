"""批 A（I05，2026-09-09；Codex 批 A 审查 R1 修正后）：错误归因的驱动接缝。

局部失败类型建立在**能证明来源**的容器操作边界上：`DockerSandbox.exec(check=True)` /
`write_file` 失败抛 typed `SandboxExecError`；真实 `ClaudeCodeDriver.run` 只把它转换成
task-local 的 `harness_bootstrap_failed`（在 FAILURE_CODE_TERMINATION_MAP 内 → 编排层
ABORTED 补采）。其它 RuntimeError（我方 / vendored 代码不变量）与 typed 配置错误原样上抛，
编排层按未归因异常 run-halt。

两层验证：
1. driver 单元：包装 / 透传边界；
2. 真实 driver → 真实 fa_formal 编排（移植 Codex `error_routing_probe.py` 五案 + docker 超时案）：
   只在故障来源处注入，断言最终处置、halt 通知次数与清理。
编排层自身的分流在 tests/adapters/test_w1b_termination_facts_producer.py ⑤/⑤b/⑤c/⑤d。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))
from test_slime_generate import SAMPLING_PARAMS, FakeFinalizationStore, _Args  # noqa: E402
from test_w1b_termination_facts_producer import _formal_chain, _steps  # noqa: E402

from repoharness2.adapters.slime.async_worker import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver  # noqa: E402
from repoharness2.adapters.slime.docker_sandbox import SandboxExecError  # noqa: E402
from repoharness2.adapters.slime.generate import SlimeBindingError  # noqa: E402
from repoharness2.adapters.slime.outcome_producer import FAILURE_CODE_TERMINATION_MAP  # noqa: E402


class _Sandbox:
    container_name = "rh2-test-rollout"


async def _run_driver(driver: ClaudeCodeDriver) -> int:
    return await driver.run(
        _Sandbox(), workdir="/testbed", session_id="tok", adapter_url="http://relay:1",
        # 批 B 起引导步骤的 timeout = min(步骤上限, 剩余预算)：预算须大于步骤上限（180/900），
        # 否则 124 超时按构造归 episode 期限而不是引导故障（见 test_budget_deadline）
        time_budget_sec=1800, prompt="p",
    )


# ---------------------------------------------------------------- 1. driver 单元：包装 / 透传边界


async def test_driver_wraps_sandbox_exec_error_as_attributed_task_local(monkeypatch):
    async def _boom(self, sb, **kwargs):
        raise SandboxExecError("docker exec", 124, "tar -xzf /tmp/cc-platform.tgz\ntimeout")

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", _boom)
    with pytest.raises(SlimeBindingError, match=r"^\[harness_bootstrap_failed\]") as ei:
        await _run_driver(ClaudeCodeDriver())
    assert isinstance(ei.value.__cause__, SandboxExecError)
    assert "exit=124" in str(ei.value)  # 原始 exec 输出保留供诊断
    assert FAILURE_CODE_TERMINATION_MAP["harness_bootstrap_failed"] == ("harness_crash", "harness_crash")


async def test_driver_does_not_rename_unknown_runtime_error(monkeypatch):
    """Codex R1 反例：安装函数内部的裸 RuntimeError（不变量）不是容器操作失败，不得改名成局部故障。"""

    async def _bug(self, sb, **kwargs):
        raise RuntimeError("internal installation invariant")

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", _bug)
    with pytest.raises(RuntimeError, match="internal installation invariant") as ei:
        await _run_driver(ClaudeCodeDriver())
    assert not isinstance(ei.value, SlimeBindingError)


async def test_driver_passes_typed_config_errors_through_unwrapped(monkeypatch):
    async def _mismatch(self, sb, **kwargs):
        raise SlimeBindingError("cc_version_mismatch", "观测 '1.0.0' 不含期望 '2.1.205'")

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", _mismatch)
    with pytest.raises(SlimeBindingError, match=r"^\[cc_version_mismatch\]") as ei:
        await _run_driver(ClaudeCodeDriver())
    assert ei.value.__cause__ is None  # 未被二次包装
    assert "cc_version_mismatch" not in FAILURE_CODE_TERMINATION_MAP  # 未归因 → 编排层 run-halt


def test_docker_sandbox_check_failure_is_typed():
    """`SandboxExecError` 仍是 RuntimeError 子类（既有按 RuntimeError 捕获的调用方不受影响），
    且带 exit code 与操作名。"""

    err = SandboxExecError("docker exec", 124, "cmd\nstderr")
    assert isinstance(err, RuntimeError) and err.exit_code == 124 and err.op == "docker exec"


# ---------------------------------------------------------------- 2. 真实 driver → 真实 fa_formal 编排

_CASES = {
    # name: (origin, exception_factory, expected)
    "known_docker_exec_failure": ("docker_exec", None, "aborted"),
    "unknown_install_runtime_error": ("install", lambda: RuntimeError("internal installation invariant"), "fatal"),
    "unknown_runtime_error_after_bootstrap": ("launch", lambda: RuntimeError("internal launch invariant"), "fatal"),
    "unknown_type_error_after_bootstrap": ("launch", lambda: TypeError("internal launch invariant"), "fatal"),
    "typed_cli_version_error": ("install", lambda: SlimeBindingError("cc_version_mismatch", "观测不符"), "fatal"),
}


@pytest.mark.parametrize("name", sorted(_CASES))
async def test_real_driver_through_formal_orchestrator_routes_by_source(name, monkeypatch):
    origin, make_exc, expected = _CASES[name]
    # 测试体内再导入：conftest 会在测试之间重置 vendored `slime.*` 模块，模块顶层捕获的
    # `ClaudeCodeHarness` 类对象会过期，补丁落到旧类上——真实驱动在 run() 内重新 import 到
    # 的是新类，真实 launch_and_wait 就会按 5s 轮询 done marker 直到 1800s（首版曾因此挂起）。
    from slime.agent.harness import ClaudeCodeHarness

    from repoharness2.adapters.slime import docker_sandbox

    monkeypatch.setenv("SLIME_AGENT_CC_EXTRA_ENVS", "{}")  # 守卫 env 合并写回本进程 env，隔离之
    chain = _formal_chain(FakeFinalizationStore())
    chain.orchestrator._harness_driver = ClaudeCodeDriver()  # 真实驱动
    notified: list = []
    chain.orchestrator._notify_fatal_halt = notified.append

    async def install(self, sb, **kwargs):  # 批 B 起 _install_native_cli 带 timeout= 关键字
        if origin == "install":
            raise make_exc()

    async def fake_run(*args, input_bytes=None, timeout=None):
        # 真实 DockerSandbox.exec(check=True) 走这里：docker_exec 案返回非零（useradd 失败形态）→ 抛
        # SandboxExecError；其余案返回 0 让引导步骤（useradd / ensure_agent_user / write_config）通过。
        # 不用 124：批 B 起由期限决定 timeout 的步骤超时按构造归 episode 期限（另有测试）。
        return (1, "", "useradd: cannot lock /etc/passwd") if origin == "docker_exec" else (0, "", "")

    async def launch(self, sb, ctx, prompt, time_budget_sec):
        raise make_exc()

    monkeypatch.setattr(ClaudeCodeDriver, "_install_native_cli", install)
    monkeypatch.setattr(docker_sandbox, "_run", fake_run)
    if origin == "launch":
        monkeypatch.setattr(ClaudeCodeHarness, "launch_and_wait", launch)

    if expected == "aborted":
        (out,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
        audit = chain.orchestrator.audits[0]
        assert out.status == "aborted" and out.remove_sample is True
        assert audit.outcome_v2["reason_code"] == "harness_bootstrap_failed"
        assert audit.outcome_v2["completion_class"] == "missing"
        assert notified == []
        assert any("cannot lock /etc/passwd" in f.detail for f in audit.failure_records)  # 原始 exec 输出可诊断
    else:
        with pytest.raises(FatalExecutionInfrastructureError, match="pre_finalize_failure_unclassified"):
            await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
        audit = chain.orchestrator.audits[0]
        assert [n.reason_code for n in notified] == ["pre_finalize_failure_unclassified"]
        assert audit.outcome_v2 is None
        (failure,) = [f for f in audit.failure_records if f.stage == "harness_run"]
        assert failure.error_type == type(make_exc()).__name__
        if name == "typed_cli_version_error":
            assert "[cc_version_mismatch]" in failure.detail
    assert "cleanup_completed" in _steps(audit) and len(chain.docker.removed) == 1
