"""批 A 独立 CPU 探针：真实驱动与编排的错误来源分类；不用 Docker。"""

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
from repoharness2.adapters.slime.bringup import ClaudeCodeDriver
from repoharness2.adapters.slime.docker_sandbox import DockerSandbox
from repoharness2.adapters.slime.generate import SlimeBindingError


async def case(name: str, exception: BaseException, *, origin: str) -> dict:
    chain = _formal_chain(FakeFinalizationStore())
    chain.orchestrator._harness_driver = ClaudeCodeDriver()
    fatal_notifications = []

    async def install(self, sandbox):
        if origin == "install":
            raise exception

    async def docker_exec(self, *args, **kwargs):
        if origin == "docker_exec":
            raise exception
        return 0, "", ""

    async def launch(self, *args, **kwargs):
        raise exception

    with (
        patch.object(ClaudeCodeDriver, "_install_native_cli", install),
        patch.object(DockerSandbox, "exec", docker_exec),
        patch.object(ClaudeCodeHarness, "launch_and_wait", launch),
        patch.object(chain.orchestrator, "_notify_fatal_halt", fatal_notifications.append),
    ):
        try:
            output = await chain.orchestrator.generate(_Args(), chain.base_sample, SAMPLING_PARAMS)
        except Exception as exc:
            result = {"result": type(exc).__name__, "reason_code": getattr(exc, "reason_code", None)}
        else:
            result = {"result": "returned", "status": str(output[0].status)}
    audit = chain.orchestrator.audits[-1]
    result.update(
        case=name,
        origin=origin,
        original_type=type(exception).__name__,
        fatal_notifications=len(fatal_notifications),
        outcome_reason=(audit.outcome_v2 or {}).get("reason_code"),
        completion=(audit.outcome_v2 or {}).get("completion_class"),
        cleanup_completed=any(event.step == "cleanup_completed" for event in audit.timeline),
    )
    return result


async def main():
    cases = (
        ("known_docker_failure", RuntimeError("docker exec failed (exit=124): review timeout"), "docker_exec"),
        ("unknown_install_runtime_error", RuntimeError("review internal installation invariant"), "install"),
        ("unknown_runtime_error_after_bootstrap", RuntimeError("review internal launch invariant"), "launch"),
        ("unknown_type_error_after_bootstrap", TypeError("review internal launch invariant"), "launch"),
        ("typed_cli_version_error", SlimeBindingError("cc_version_mismatch", "review version mismatch"), "install"),
    )
    for name, exception, origin in cases:
        print(json.dumps(await case(name, exception, origin=origin), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
