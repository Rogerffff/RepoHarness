"""小反例：原心跳读数可含夹具准备；本机 int32 解码的 Python 对象数依赖编号范围。"""

import asyncio
import importlib.util
import json
from pathlib import Path
import random
import struct
import time

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/pyproject.toml").is_file())
spec = importlib.util.spec_from_file_location(
    "author_bench", ROOT / "rh2/experiments/batch6_e3_20260922/lifecycle_bench.py",
)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


async def heartbeat_case(settle):
    heartbeat = bench.Heartbeat(0.001)
    heartbeat.start()
    await asyncio.sleep(0.005)
    time.sleep(0.08)  # 模拟计时函数外合成 response 的准备工作
    if settle:
        await asyncio.sleep(0.005)
    _, elapsed, delay = await heartbeat.measure(lambda: time.sleep(0.004))
    await heartbeat.stop()
    return {"timed_function_ms": elapsed * 1000, "reported_heartbeat_ms": delay * 1000}


async def main():
    out = {"heartbeat_original": await heartbeat_case(False),
           "heartbeat_settled": await heartbeat_case(True)}
    for name, payload in (
        ("experts128", struct.pack("<128i", *range(128)) * 16),
        ("random32", random.Random(42).randbytes(2048 * 4)),
    ):
        values = struct.unpack("<2048i", payload)
        out[name] = {"elements": len(values), "unique_python_int_objects": len({id(v) for v in values}),
                     "min_value": min(values), "max_value": max(values)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
