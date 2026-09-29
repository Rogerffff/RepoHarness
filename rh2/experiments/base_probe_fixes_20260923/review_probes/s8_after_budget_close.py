"""补充：time_budget 关闭本次连接之后，容器内仍在跑的进程再写 stdout 会怎样（阻塞？SIGPIPE？照常？）。

deadline 1 s；进程 2 s 后写 N 字节（1 KiB / 1 MiB / 8 MiB），写完 touch 标记文件再 sleep 20。
收集器返回后 6 s 核对：标记是否出现（写没有被卡住）、exec inspect（Running / ExitCode：141 = SIGPIPE）。
这是既有屏障要面对的事实（收集器本身不负责停止进程）。
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import TMP, collect, env_facts, exec_inspect_raw, new_container, rm_container, sh, write_result  # noqa: E402


async def main() -> None:
    c = new_container("s8")
    rows = []
    try:
        for n in (1024, 1024 * 1024, 8 * 1024 * 1024):
            tag = uuid.uuid4().hex[:6]
            cmd = f"echo start; sleep 2; head -c {n} /dev/zero; touch /tmp/after_{tag}; exec sleep 20"
            rec = await collect(c, TMP / f"s8_{n}_{tag}", cmd, deadline=1.0, progress={})
            res = rec.get("result") or {}
            await asyncio.sleep(6.0)
            marker = sh("docker", "exec", c, "bash", "-c", f"test -e /tmp/after_{tag} && echo present || echo absent").stdout.strip()
            rows.append({"bytes_written_after_close": n, "collector_state": res.get("exec_state"), "collector_exit_code": res.get("exit_code"),
                         "marker_after_6s": marker, "exec_inspect_after_6s": await exec_inspect_raw(res.get("exec_id"))})
    finally:
        rm_container(c)
    write_result("s8_after_budget_close", {"env": env_facts(), "rows": rows})
    for r in rows:
        print(r)


if __name__ == "__main__":
    asyncio.run(main())
