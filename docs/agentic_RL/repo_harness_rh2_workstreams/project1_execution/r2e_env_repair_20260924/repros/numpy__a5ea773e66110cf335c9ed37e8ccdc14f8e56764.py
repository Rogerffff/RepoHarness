"""公开复现：numpy a5ea773e —— tile() 在所有重复因子为 1 时不复制输入，修改结果会改到原数组。
依据：公开题面示例（np.tile(np.arange(5), 1) 后 b += 2）。只观测，不写 /testbed。
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

a = np.arange(5)
b = np.tile(a, 1)
print("b is a: %s; may_share_memory: %s" % (b is a, np.may_share_memory(a, b)))  # 1.10 无 shares_memory
b += 2
print("a after b += 2: %s" % a.tolist())
mutated = a.tolist() != [0, 1, 2, 3, 4]
print("REPRO_OBSERVED=%d%s" % (1 if mutated else 0, " (original array mutated)" if mutated else " (original array unchanged)"))
