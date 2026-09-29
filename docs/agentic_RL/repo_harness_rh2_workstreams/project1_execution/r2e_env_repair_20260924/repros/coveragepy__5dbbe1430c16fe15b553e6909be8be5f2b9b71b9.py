"""公开复现（E06，只据公开题面）：coveragepy 5dbbe143 —— Coverage._warn() 不认 once= 参数（TypeError）。

照题面示例：Coverage().load() 后连续两次 _warn(..., slug="bot", once=True)。cwd 先切到 /tmp 临时目录
（load() 在没有数据文件时会新建 .coverage，不能落在 /testbed）。判定：TypeError 且消息提到 'once' → REPRO_OBSERVED=1。
"""
import os
import sys
import tempfile

try:
    import coverage
    IMPORT = "direct"
except ImportError as exc:
    sys.path.insert(0, os.getcwd())
    IMPORT = f"cwd_fallback({type(exc).__name__})"
    import coverage

print("REPRO_IMPORT=" + IMPORT, coverage.__file__, coverage.__version__)
os.chdir(tempfile.mkdtemp())
cov = coverage.Coverage()
cov.load()
try:
    cov._warn("Warning, warning 1!", slug="bot", once=True)
    cov._warn("Warning, warning 2!", slug="bot", once=True)
    print("REPRO_OBSERVED=0 reason=_warn accepted once=True")
except TypeError as exc:
    print("TypeError:", exc)
    if "once" in str(exc):
        print("REPRO_OBSERVED=1 (TypeError on once=)")
    else:
        print("REPRO_OBSERVED=0 reason=TypeError unrelated to once")
