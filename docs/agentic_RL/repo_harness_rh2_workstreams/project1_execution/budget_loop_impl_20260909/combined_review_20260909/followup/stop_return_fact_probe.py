"""R3 独立窄反证：真实停止 helper 的返回时间不是已停止事实。

只给 workspace.run_bash 返回可控 ExecResult；不调用 Docker 或真实进程。
完整 formal/准入路径由主审另行验证，本脚本不重复。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from repoharness2.adapters.slime.execution_scope import COUNT_SCRIPT, KILL_SCRIPT, terminate_agent_processes
from repoharness2.grading.manager import ExecResult


async def one_case(*, failed_kill):
    now = [899.5]
    history = []

    class Workspace:
        count = 0

        async def run_bash(self, script):
            if script == KILL_SCRIPT:
                if failed_kill:
                    result = ExecResult(1, "", "probe: docker exec failed, no signal delivered")
                else:
                    # 实际停止 899.5；这里只把命令回包延至 901，不让进程跨墙执行。
                    now[0] = 901.0
                    result = ExecResult(0, "", "")
                history.append({"operation": "kill", "return_at": now[0], "exit_code": result.exit_code})
                return result
            assert script == COUNT_SCRIPT
            self.count += 1
            now[0] = 900.1 if failed_kill and self.count == 1 else 901.0
            residual = 1 if failed_kill and self.count == 1 else 0
            history.append({"operation": "count", "at": now[0], "residual": residual})
            return ExecResult(0, f"{residual}\n", "")

    result = await terminate_agent_processes(Workspace(), interval=0, clock=lambda: now[0])
    # generate.py 本次实现使用的条件，原式展开，仅用于说明该停止结果被怎样消费。
    consumer_stopped_before_wall = result.kill_returned_at is not None and result.kill_returned_at <= 900.0
    if failed_kill:
        assert result.kill_returned_at == 899.5 and result.confirmed_at == 901.0
        assert result.verified and consumer_stopped_before_wall
    else:
        assert result.verified and not consumer_stopped_before_wall
    return dict(case="kill_failed_then_live_after_wall" if failed_kill else "already_stopped_late_kill_reply",
                history=history, stop_result=asdict(result),
                consumer_stopped_before_wall=consumer_stopped_before_wall)


async def main():
    for failed in (True, False):
        print(json.dumps(await one_case(failed_kill=failed), ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
