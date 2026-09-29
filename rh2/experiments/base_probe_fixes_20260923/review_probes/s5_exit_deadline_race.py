"""场景 5：退出与期限的竞态。

进程在约 1.0 s 退出（sleep S 扫 0.90..1.10，覆盖 exec 启动开销两侧），deadline 也是 1.0 s；A/B 两组各 30 次，
C 组 60 次集中在实测边界两侧：
A 组 `sleep S; exit 7`，B 组 `sleep S; printf done; exit 7`（退出前还有一帧输出）。
合格：要么 time_budget 且 exit_code=-1，要么 exited 且 exit_code=7；不得出现其它码、其它状态或异常。
另记 time_budget 时那次有界 inspect 看到的事实（进程可能其实已退出）。
"""

from __future__ import annotations

import asyncio
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TMP, collect, env_facts, new_container, rm_container, write_result  # noqa: E402

REPS = 30


async def group(container: str, tag: str, body: str, *, reps: int = REPS, jitter: tuple[float, float] | None = None) -> dict:
    rows = []
    rng = random.Random(20260924)
    for i in range(reps):
        s = round(rng.uniform(*jitter), 4) if jitter else round(0.90 + i * (0.20 / (REPS - 1)), 4)
        rec = await collect(container, TMP / f"s5_{tag}_{i}", f"sleep {s}; {body}", deadline=1.0, progress={})
        res = rec.get("result") or {}
        state, code = res.get("exec_state"), res.get("exit_code")
        ok = (state == "time_budget" and code == -1) or (state == "exited" and code == 7)
        rows.append({"i": i, "sleep": s, "ok": ok, "exec_state": state, "exit_code": code, "wall": rec["wall"],
                     "raised": rec.get("raised"), "inspect": res.get("inspect"), "stdout_bytes": res.get("stdout_bytes"),
                     "log_complete": res.get("log_complete"), "log_partial_reason": res.get("log_partial_reason")})
        await asyncio.sleep(0.3)  # 让上一轮 time_budget 留下的 sleep 自然结束
    return {"tag": tag, "body": body, "all_ok": all(r["ok"] for r in rows),
            "outcomes": dict(Counter(f"{r['exec_state']}:{r['exit_code']}" for r in rows)), "rows": rows}


async def main() -> None:
    c = new_container("s5")
    try:
        a = await group(c, "A", "exit 7")
        b = await group(c, "B", "printf done; exit 7")
        # C 组：60 次集中在 A/B 组实测的边界（sleep≈0.983）两侧 ±7 ms，反复撞竞态窗口
        cc = await group(c, "C", "printf done; exit 7", reps=60, jitter=(0.976, 0.990))
    finally:
        rm_container(c)
    write_result("s5_exit_deadline_race", {"env": env_facts(), "all_ok": a["all_ok"] and b["all_ok"] and cc["all_ok"],
                                           "groups": [a, b, cc]})


if __name__ == "__main__":
    asyncio.run(main())
