"""公开复现：numpy 43e333e2 —— np.ma.average 在被掩码位置的权重为 NaN 时返回 nan（期望 1.5）。
依据：公开题面示例。只观测，不写 /testbed。
导入处理同 numpy 其它题：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
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

a = np.ma.array([1.0, 2.0, 3.0, 4.0], mask=[False, False, True, True])
with np.errstate(all="ignore"):
    avg = np.ma.average(a, weights=[1, 1, 1, np.nan])
print("RESULT=%r" % (avg,))
try:
    ok = bool(np.isclose(float(avg), 1.5))
except Exception as exc:  # 例如结果被整体掩码
    print("CONVERT_ERROR=%s: %s" % (type(exc).__name__, exc))
    ok = False
print("REPRO_OBSERVED=%d%s" % (0 if ok else 1, " (got 1.5)" if ok else " (expected 1.5)"))
