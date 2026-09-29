"""公开复现（E06，只据公开题面）：aiohttp 1c1c0ea3 —— run_app() 对应用上下文里的异常既向上抛出、又记一次日志。

题面示例原样（cleanup_ctx 里 raise RuntimeError）；另加：root logger 上挂收集器；print=None 只关横幅；SIGALRM 45 s 兜底。
判定：run_app 抛出 RuntimeError，且同一异常出现在日志记录里 → REPRO_OBSERVED=1。
"""
import logging
import os
import signal
import sys

try:
    import aiohttp
    IMPORT = "direct"
except ImportError as exc:  # 包没装进 venv 时只能靠 cwd=/testbed 在 sys.path 上导入
    sys.path.insert(0, os.getcwd())
    IMPORT = f"cwd_fallback({type(exc).__name__})"
    import aiohttp
from aiohttp import web

print("REPRO_IMPORT=" + IMPORT, aiohttp.__file__, aiohttp.__version__)
signal.alarm(45)


class Collect(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


handler = Collect()
logging.getLogger().addHandler(handler)


async def context(app: web.Application):
    raise RuntimeError("Unexpected error occurred")
    yield


app = web.Application()
app.cleanup_ctx.append(context)
raised = None
try:
    web.run_app(app, print=None)
except RuntimeError as exc:
    raised = exc
logged = [r for r in handler.records
          if (r.exc_info and r.exc_info[1] is raised) or "Unexpected error occurred" in r.getMessage()]
print("raised:", repr(raised))
for r in logged:
    print("logged:", r.name, r.levelname, r.getMessage().splitlines()[0][:120])
if raised is not None and logged:
    print("REPRO_OBSERVED=1 (exception raised AND logged %d time(s))" % len(logged))
else:
    print("REPRO_OBSERVED=0 reason=raised=%s logged=%d" % (raised is not None, len(logged)))
