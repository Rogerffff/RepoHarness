"""公开复现：datalad 6b6fa389 —— 'weired_url:/' 被解析成 file:implicit 而不是 ssh:implicit。
依据：公开题面示例（URL('weired_url:/') 的 scheme / hostname / path）。只观测，不写 /testbed。
导入：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
import os
import sys

sys.dont_write_bytecode = True
try:
    import datalad
    print("IMPORT_PLAIN=ok %s" % datalad.__file__)
except ImportError as exc:
    print("IMPORT_PLAIN=fail (%s: %s); retry with cwd %s on sys.path" % (type(exc).__name__, exc, os.getcwd()))
    sys.path.insert(0, os.getcwd())
from datalad.support.network import URL

u = URL("weired_url:/")
got = (u.scheme, u.hostname, u.path)
print("GOT scheme=%r hostname=%r path=%r" % got)
expected = ("ssh:implicit", "weired_url", "/")
print("REPRO_OBSERVED=%d%s" % (0 if got == expected else 1, "" if got == expected else " (expected %r)" % (expected,)))
