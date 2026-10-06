"""公开复现：numpy 18b7cd9d —— poly1d.__eq__ 与非 poly1d 对象比较时抛 AttributeError。
依据：公开题面示例（p == None）。只观测，不写 /testbed。
导入：探针以 `cd /testbed && python /rh2/repro.py` 运行，sys.path[0] 是脚本目录而非 cwd；
先试普通导入并记录结果，失败再把 cwd 加进 sys.path（记录"脚本不在 /testbed 时导入失败"这一解题侧条件）。"""
import os
import sys

sys.dont_write_bytecode = True
try:
    import numpy as np
    print("IMPORT_PLAIN=ok")
except ImportError as exc:
    print("IMPORT_PLAIN=fail (%s: %s); retry with cwd %s on sys.path" % (type(exc).__name__, exc, os.getcwd()))
    sys.path.insert(0, os.getcwd())
    import numpy as np
print("NUMPY=%s %s" % (np.__file__, np.__version__))

p = np.poly1d([1, 2, 3])
try:
    r = (p == None)  # noqa: E711  题面原样
    print("RESULT p == None -> %r" % (r,))
    print("REPRO_OBSERVED=0 (no exception raised)")
except AttributeError as exc:
    print("EXC=AttributeError: %s" % exc)
    print("REPRO_OBSERVED=1")
