"""公开复现（E06，只据公开题面）：coveragepy 97997d2c —— get_option / set_option 不认 "paths"。

照题面示例原样；cwd 先切到 /tmp 临时目录（不读 /testbed 的 setup.cfg / tox.ini 配置、不写工作区）。
判定：抛出提到 'paths' 的异常（题面：CoverageException: No such option: 'paths'）→ REPRO_OBSERVED=1。
"""
import os
import sys
import tempfile
from collections import OrderedDict

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
try:
    paths = cov.get_option("paths")
    print("get_option('paths') ->", repr(paths))
    new_paths = OrderedDict()
    new_paths['magic'] = ['src', 'ok']
    cov.set_option("paths", new_paths)
    got = cov.get_option("paths")
    print("after set_option ->", repr(got))
    if got == new_paths:
        print("REPRO_OBSERVED=0 reason=paths option can be read and set")
    else:
        print("REPRO_OBSERVED=1 (set value not returned)")
except Exception as exc:
    print(type(exc).__module__ + "." + type(exc).__name__ + ":", exc)
    if "paths" in str(exc):
        print("REPRO_OBSERVED=1 (paths option rejected)")
    else:
        print("REPRO_OBSERVED=0 reason=unrelated exception")
