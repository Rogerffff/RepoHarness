"""公开复现：numpy 2f4a9650 —— savetxt 对 0D / >2D 数组抛 IndexError 而不是 ValueError。
依据：公开题面示例（np.array(1) 与 np.array([[[1], [2]]]) 写入 BytesIO）。只观测，不写 /testbed。
导入处理同 numpy 其它题：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
import os
import sys
from io import BytesIO

sys.dont_write_bytecode = True
try:
    import numpy as np
    print("IMPORT_PLAIN=ok")
except ImportError as exc:
    print("IMPORT_PLAIN=fail (%s: %s); retry with cwd %s on sys.path" % (type(exc).__name__, exc, os.getcwd()))
    sys.path.insert(0, os.getcwd())
    import numpy as np
print("NUMPY=%s %s" % (np.__file__, np.__version__))

bad = []
for label, arr in (("0D", np.array(1)), ("3D", np.array([[[1], [2]]]))):
    try:
        np.savetxt(BytesIO(), arr)
        print("%s: no exception" % label)
        bad.append(label)
    except ValueError as exc:
        print("%s: ValueError: %s" % (label, exc))
    except Exception as exc:  # 题面所述错误类型（IndexError）落在这里
        print("%s: %s: %s" % (label, type(exc).__name__, exc))
        bad.append(label)
print("REPRO_OBSERVED=%d%s" % (1 if bad else 0, (" (not ValueError for: %s)" % ",".join(bad)) if bad else " (ValueError for both)"))
