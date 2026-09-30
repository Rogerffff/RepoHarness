"""看 exact_full 等在取值顶端（float64 舍入到 2**64 后转回 uint64 溢出）的内部分界值；只作质量观察。"""
import numpy as np, pandas as pd, dask, dask.dataframe as dd
from dask.dataframe.partitionquantiles import partition_quantiles
dask.config.set(scheduler="sync")
T64 = 2 ** 64
ORDER = [(i * 7919) % 200 for i in range(200)][::-1]
print("float->uint64 of 2**64:", np.array([2.0 ** 64]).astype(np.uint64), " float->int64 of 2**63:", np.array([2.0 ** 63]).astype(np.int64))
print("np.uint64(A) < A+1 via numpy:", np.uint64(612509347682975743) < 612509347682975744)
vals = [T64 - 200 + k for k in ORDER]
s = pd.Series(np.array(vals, dtype="uint64"), name="x")
r = partition_quantiles(dd.from_pandas(s, npartitions=4, sort=False), npartitions=4).compute()
print("top64_dense k=4:", [int(v) - T64 for v in r])
mix = [612509347682975743 + 997 * k for k in range(150)] + [T64 - 1 - j for j in range(50)]
mix = [mix[k] for k in ORDER]
s = pd.Series(np.array(mix, dtype="uint64"), name="x")
r = partition_quantiles(dd.from_pandas(s, npartitions=4, sort=False), npartitions=8).compute()
print("mix150+50top k=8:", [int(v) for v in r])
