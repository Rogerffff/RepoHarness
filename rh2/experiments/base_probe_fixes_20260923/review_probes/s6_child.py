"""场景 6 的子进程：在 asyncio.run 里跑一次被测收集器（exec sleep 120），流开始后向 stdout 报告 exec_id 与自身 pid；
被信号终止时能打印多少就打印多少（默认 SIGTERM/SIGHUP 不会有任何 Python 层输出）。

用法：s6_child.py <mode: default|graceful> <container> <outdir>
- default：不装任何信号处理（asyncio.run 自带 SIGINT→取消主任务；TERM/HUP 为内核默认动作）
- graceful：loop.add_signal_handler(TERM/HUP → 取消主任务)，模拟编排进程的优雅关停
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import ds  # noqa: E402

mode, container, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
progress: dict = {}


def emit(obj: dict) -> None:
    print(json.dumps(obj, default=str), flush=True)


async def main() -> None:
    if mode == "graceful":
        loop, task = asyncio.get_running_loop(), asyncio.current_task()
        for sig in (signal.SIGTERM, signal.SIGHUP):
            loop.add_signal_handler(sig, task.cancel)

    async def reporter() -> None:
        while progress.get("exec_state") != "streaming":
            await asyncio.sleep(0.02)
        emit({"event": "streaming", "exec_id": progress["exec_id"], "pid": os.getpid()})

    rep = asyncio.create_task(reporter())
    try:
        run = await ds.run_exec_collected(
            container_name=container, user="nobody", workdir="/tmp", env={"HOME": "/tmp"},
            cmd="echo started; exec sleep 120", stdout_path=Path(outdir) / "out", stderr_path=Path(outdir) / "err",
            deadline_seconds=300, progress=progress,
        )
        emit({"event": "returned", "facts": run.facts()})
    except BaseException as exc:
        emit({"event": "raised", "type": type(exc).__name__, "progress": progress})
        raise
    finally:
        rep.cancel()


try:
    asyncio.run(main())
except BaseException as exc:
    emit({"event": "top_level", "type": type(exc).__name__, "progress_exec_state": progress.get("exec_state")})
    raise
