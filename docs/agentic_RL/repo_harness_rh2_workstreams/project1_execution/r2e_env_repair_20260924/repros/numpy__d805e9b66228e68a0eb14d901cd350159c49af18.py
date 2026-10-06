"""公开复现：numpy d805e9b6 —— 大的一维 masked array 的 repr 没有按预期截断。
依据：公开题面示例（np.ma.arange(2000)，a[1:50] 掩码）。题面期望 data 段为 "[0 -- -- ..., 1997 1998 1999]"，
即只出现 2 个 "--"；实际 data 段出现大量 "--"。判据：data 段 "--" 个数 > 3 视为复现。只观测，不写 /testbed。
导入处理同 numpy 其它题：先普通导入并记录，失败再把 cwd 加进 sys.path。"""
import os
import re
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

a = np.ma.arange(2000)
a[1:50] = np.ma.masked
r = repr(a)
m = re.search(r"data\s*=\s*\[(.*?)\]", r, re.S)  # 只取 data 段（"masked_array(" 本身含 "mask"）
data_part = m.group(1) if m else r
n = data_part.count("--")
print("REPR_CHARS=%d DATA_DASHES=%d" % (len(r), n))
print("REPR_HEAD=%r" % r[:160])
print("REPRO_OBSERVED=%d%s" % (1 if n > 3 else 0, " (data not truncated as expected)" if n > 3 else " (truncated)"))
