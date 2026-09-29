"""启动 Brief 的独立 CPU 证据；不修改生产类或历史运行证据。"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))

from slime.agent.harness.claude_code import ClaudeCodeHarness


class ConstructorProbe(ClaudeCodeHarness):
    def __init__(self, value):
        self.value = value


class MutationProbe(ClaudeCodeHarness):
    pass


async def singleton_probe():
    first, second = ConstructorProbe("A"), ConstructorProbe("B")
    a_entered, b_entered = asyncio.Event(), asyncio.Event()

    async def job_a():
        instance = MutationProbe()
        instance.value = "A"
        a_entered.set()
        await b_entered.wait()
        return instance.value

    async def job_b():
        await a_entered.wait()
        instance = MutationProbe()
        instance.value = "B"
        b_entered.set()
        return instance.value

    return {
        "same_instance": first is second,
        "second_constructor_value": second.value,
        "concurrent_instance_mutation": await asyncio.gather(job_a(), job_b()),
        "scope": "真实 vendored 基类的两种假设实现；不是尚未编写的 RS 子类回归",
    }


def baseline_facts():
    root = ROOT / "runs/base_probe_fixes_20260923/remote/a1_devcheck"
    rows = []
    for path in sorted(root.glob("*/*/attempt.json")):
        attempt = json.loads(path.read_text())
        facts = attempt["stages"]["agent_env_facts"]["facts"]
        steps = {}
        step = None
        for line in (path.parent / "dev_check_output.txt").read_text().splitlines():
            if line.startswith("=== STEP "):
                step = line.removeprefix("=== STEP ")
            elif line.startswith("=== RC "):
                steps[step] = int(line.removeprefix("=== RC "))
        cleanup = attempt["cleanup"]
        rows.append({
            "task": path.parent.parent.name,
            "variant": path.parent.name,
            "bash_env": facts.get("RH2F_BASH_ENV"),
            "python": facts.get("RH2F_PY_EXE"),
            "pytest": facts.get("RH2F_WHICH_pytest"),
            "top_level_rc": attempt["dev_check_exit_code"],
            "step_rc": steps,
            "container_removed": cleanup["container_rm"] == 0 and not cleanup["container_left"],
        })
    return rows


def transcript_facts():
    path = ROOT / "runs/base_probe_20260922/remote/runs/p2_smoke/coder/conan-15422/trajectory.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {
        "path": str(path.relative_to(ROOT)),
        "jsonl_lines": len(rows),
        "types": dict(Counter(row.get("type") for row in rows)),
        "message_start": sum(row.get("event", {}).get("type") == "message_start" for row in rows),
        "result": sum(row.get("type") == "result" for row in rows),
    }


async def main():
    print(json.dumps({
        "singleton": await singleton_probe(),
        "baseline": baseline_facts(),
        "transcript": transcript_facts(),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
