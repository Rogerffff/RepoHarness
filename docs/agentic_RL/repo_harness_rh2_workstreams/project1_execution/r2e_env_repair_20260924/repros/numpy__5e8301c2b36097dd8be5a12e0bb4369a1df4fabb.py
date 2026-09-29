"""公开复现：numpy 5e8301c2 —— einsum(optimize=True) 遇到单例维度（可广播）时抛 ValueError。
依据：公开题面示例（'ti,ti->i'，(10, 2) 与 (1, 2)）；另打印 optimize=False 的结果作对照。只观测，不写 /testbed。
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

p = np.ones((10, 2))
q = np.ones((1, 2))
for opt in (False, True):
    try:
        r = np.einsum("ti,ti->i", p, q, optimize=opt)
        print("optimize=%s -> shape %s values %s" % (opt, r.shape, r.tolist()))
        if opt:
            print("REPRO_OBSERVED=0 (no exception with optimize=True)")
    except ValueError as exc:
        print("optimize=%s -> ValueError: %s" % (opt, exc))
        if opt:
            print("REPRO_OBSERVED=1")
