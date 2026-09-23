"""R1 修后窄探针：从真实 DockerSandbox 操作边界验证分类，不调用 Docker。"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests/adapters"))

from test_w1b_termination_facts_producer import _formal_chain
from test_slime_generate import FakeFinalizationStore, SAMPLING_PARAMS, _Args
from slime.agent.harness import ClaudeCodeHarness
from repoharness2.adapters.slime import docker_sandbox
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver


async def run_case(name: str, operation: str, return_code: int | None, *, internal_error=False):
    chain = _formal_chain(FakeFinalizationStore())
    chain.orchestrator._harness_driver = ClaudeCodeDriver()
    notifications = []
    source = {}

    async def fake_run(*args, **kwargs):
        if internal_error and operation != "launch":
            raise RuntimeError("review internal subprocess invariant")
        return return_code or 0, "", "review command result"

    async def install(self, sandbox):
        try:
            if operation == "exec":
                await sandbox.exec("review setup", check=True)
            elif operation == "write_file":
                await sandbox.write_file("/tmp/review-config", b"review")
        except Exception as exc:
            source.update(type=type(exc).__name__, op=getattr(exc, "op", None), exit_code=getattr(exc, "exit_code", None))
            raise

    async def launch(self, *args, **kwargs):
        raise RuntimeError("review internal launch invariant")

    with (
        patch.object(ClaudeCodeDriver, "_install_native_cli", install),
        patch.object(docker_sandbox, "_run", fake_run),
        patch.object(ClaudeCodeHarness, "launch_and_wait", launch),
        patch.object(chain.orchestrator, "_notify_fatal_halt", notifications.append),
    ):
        try:
            (output,) = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
        except Exception as exc:
            result = {"result": type(exc).__name__, "reason": getattr(exc, "reason_code", None)}
        else:
            result = {"result": "returned", "status": str(output.status)}
    audit = chain.orchestrator.audits[-1]
    result.update(
        case=name,
        source=source,
        fatal_notifications=len(notifications),
        outcome_reason=(audit.outcome_v2 or {}).get("reason_code"),
        cleanup_completed=any(event.step == "cleanup_completed" for event in audit.timeline),
    )
    expected_abort = return_code in {17, 124} and not internal_error
    if expected_abort:
        assert result["status"] == "aborted"
        assert source["type"] == "SandboxExecError" and source["exit_code"] == return_code
        assert result["outcome_reason"] == "harness_bootstrap_failed" and not notifications
    else:
        assert result["reason"] == "pre_finalize_failure_unclassified" and len(notifications) == 1
        assert result["outcome_reason"] is None
    assert result["cleanup_completed"]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


async def main():
    for operation in ("exec", "write_file"):
        for code in (17, 124):
            await run_case(f"{operation}_return_{code}", operation, code)
        await run_case(f"{operation}_internal_runtime_error", operation, None, internal_error=True)
    await run_case("post_bootstrap_internal_runtime_error", "launch", 0, internal_error=True)

    async def command_failed(*args, **kwargs):
        return 17, "stdout", "stderr"

    with patch.object(docker_sandbox, "_run", command_failed):
        result = await docker_sandbox.DockerSandbox("cpu-probe").exec("review poll", check=False)
    assert result == (17, "stdout", "stderr")
    print(json.dumps({"case": "exec_check_false_preserves_result", "result": list(result)}))


if __name__ == "__main__":
    asyncio.run(main())
