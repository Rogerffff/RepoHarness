"""公开复现：numpy d89bc4bb —— histogram2d / histogramdd 不接受 density 关键字（TypeError）。
依据：公开题面示例（histogram2d(x, y, bins=5, density=True)）；histogramdd 用同一组数据的 (N, 2) 形式。
只观测，不写 /testbed。导入处理同 numpy 其它题：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
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

x = [1, 2, 3, 4, 5]
y = [5, 4, 3, 2, 1]
calls = (("histogram2d", lambda: np.histogram2d(x, y, bins=5, density=True)),
         ("histogramdd", lambda: np.histogramdd(np.array([x, y]).T, bins=5, density=True)))
failed = []
for name, call in calls:
    try:
        hist = call()[0]
        print("%s: ok, hist sum=%r" % (name, float(np.sum(hist))))
    except TypeError as exc:
        print("%s: TypeError: %s" % (name, exc))
        failed.append(name)
print("REPRO_OBSERVED=%d%s" % (1 if failed else 0, (" (TypeError in: %s)" % ",".join(failed)) if failed else ""))
