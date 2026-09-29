"""场景 6 补充 c：正常 exited 0 的 exec，客户端关连接后 dockerd 一侧 hijack socket 何时释放（验证"靠 Go GC 终结器"的假设）。

2026-09-24 在验证机上以内联方式跑过同一段代码，结果记在 local_observations.json（released_after_s≈125）。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TMP, ds, new_container, rm_container, sh  # noqa: E402


async def main() -> None:
    name = new_container("s6c")
    orig = ds._FrameSource.next_frame
    cap: set[str] = set()

    def peers() -> set[str]:
        rows = [ln.split() for ln in sh("ss", "-xpH").stdout.splitlines() if f"pid={os.getpid()}," in ln]
        mine = {f[5] for f in rows}
        return {f[7] for f in rows if f[7] not in mine and f[7] != "0"}

    async def nf(src):
        fr = await orig(src)
        if fr is not None and not cap:
            cap.update(peers())
        return fr

    ds._FrameSource.next_frame = nf
    try:
        run = await ds.run_exec_collected(container_name=name, user="root", workdir="/tmp", env={}, cmd="echo hi; exit 0",
                                          stdout_path=TMP / "s6c" / "out", stderr_path=TMP / "s6c" / "err", deadline_seconds=10)
    finally:
        ds._FrameSource.next_frame = orig

    def held(i: str) -> bool:
        return any(len(ln.split()) > 5 and ln.split()[5] == i and "dockerd" in ln for ln in sh("ss", "-xpH").stdout.splitlines())

    out = {"state": run.exec_state, "code": run.exit_code, "inodes": sorted(cap)}
    await asyncio.sleep(1)
    out["held_1s"] = {i: held(i) for i in cap}
    rm_container(name)
    t = time.time()
    while time.time() - t < 300 and any(held(i) for i in cap):
        await asyncio.sleep(5)
    out["released_after_s"] = round(time.time() - t, 1) if not any(held(i) for i in cap) else "not within 300s"
    print(json.dumps(out))


if __name__ == "__main__":
    asyncio.run(main())
