"""场景 7：资源卫生（writer.close() 不 await wait_closed、异常 / 取消路径的 finally）。

用 `python -X dev -W always::ResourceWarning` 跑：同一进程内 50 轮 ×（正常退出 / time_budget / 外层取消）共 150 次收集，
核对进程 fd 数前后、本进程残留的 docker.sock 连接、以及 stderr 中的 ResourceWarning / unclosed / Task destroyed。
"""

from __future__ import annotations

import asyncio
import gc
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TMP, collect, new_container, rm_container, sh, write_result  # noqa: E402


def my_socks() -> list[str]:
    return [line for line in sh("ss", "-xpH").stdout.splitlines() if f"pid={os.getpid()}," in line]


async def main() -> None:
    c = new_container("s7hyg")
    counts = {"normal_exited": 0, "time_budget": 0, "cancelled": 0, "other": []}
    try:
        await collect(c, TMP / "hyg_warm", "echo warm", deadline=10)  # 预热：import / 事件循环自身的 fd
        gc.collect()
        fd0, socks0 = len(os.listdir("/proc/self/fd")), my_socks()
        for i in range(50):
            r = await collect(c, TMP / f"hyg_n_{i}", "echo hi", deadline=10)
            if (r.get("result") or {}).get("exec_state") == "exited":
                counts["normal_exited"] += 1
            else:
                counts["other"].append(r)
            r = await collect(c, TMP / f"hyg_t_{i}", "exec sleep 3", deadline=0.2)
            if (r.get("result") or {}).get("exec_state") == "time_budget":
                counts["time_budget"] += 1
            else:
                counts["other"].append(r)
            t = asyncio.create_task(collect(c, TMP / f"hyg_c_{i}", "exec sleep 3", deadline=10))
            await asyncio.sleep(0.2)
            t.cancel()
            try:
                await t
                counts["other"].append("cancel_not_propagated")
            except asyncio.CancelledError:
                counts["cancelled"] += 1
        await asyncio.sleep(0.5)
        gc.collect()
        await asyncio.sleep(0.1)
        fd1, socks1 = len(os.listdir("/proc/self/fd")), my_socks()
    finally:
        rm_container(c)
    write_result("s7_hygiene", {"dev_mode": sys.flags.dev_mode, "counts": counts, "fd_before": fd0, "fd_after": fd1,
                                "own_unix_socks_before": len(socks0), "own_unix_socks_after": len(socks1),
                                "own_unix_socks_after_lines": socks1})
    print(json.dumps({"fd_before": fd0, "fd_after": fd1, "socks_before": len(socks0), "socks_after": len(socks1)}))


if __name__ == "__main__":
    asyncio.run(main())
