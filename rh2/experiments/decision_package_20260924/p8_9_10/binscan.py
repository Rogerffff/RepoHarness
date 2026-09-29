"""只读：在 CC 原生二进制（Bun 打包，内嵌压缩前的 JS 文本）里按字面串定位代码片段。

    python binscan.py <binary> <needle> [--before N] [--after N] [--max K]

用 bytes.find 逐个命中打印 [pos-before, pos+after) 窗口（去重），避免 grep 大窗口正则回溯。
"""

from __future__ import annotations

import argparse
import mmap


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("binary")
    ap.add_argument("needle")
    ap.add_argument("--before", type=int, default=200)
    ap.add_argument("--after", type=int, default=600)
    ap.add_argument("--max", type=int, default=6)
    ns = ap.parse_args()
    needle = ns.needle.encode()
    seen: set[bytes] = set()
    with open(ns.binary, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
        pos = 0
        shown = 0
        total = 0
        while True:
            i = m.find(needle, pos)
            if i < 0:
                break
            total += 1
            win = m[max(0, i - ns.before): i + len(needle) + ns.after]
            if win not in seen and shown < ns.max:
                seen.add(win)
                shown += 1
                print(f"--- hit @{i} ---")
                print(win.decode("utf-8", errors="replace"))
            pos = i + 1
        print(f"=== total hits: {total}, distinct shown: {shown}")


if __name__ == "__main__":
    main()
