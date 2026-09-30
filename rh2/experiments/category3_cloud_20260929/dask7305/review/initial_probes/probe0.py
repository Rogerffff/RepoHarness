"""初判阶段的探针（读作者材料之前）：base 与 gold 上 partition_quantiles 端点。私有对照，不交给求解者。"""
import numpy as np, pandas as pd, dask, dask.dataframe as dd
from dask.dataframe.partitionquantiles import partition_quantiles
dask.config.set(scheduler="sync")

def pq(vals, dtype, nin, nout):
    s = pd.Series(np.array(vals, dtype=dtype), name="a")
    ds = dd.from_pandas(s, npartitions=nin)
    r = partition_quantiles(ds, npartitions=nout).compute()
    ok = (int(r.iloc[0]) == int(s.min())) and (int(r.iloc[-1]) == int(s.max()))
    return ok, r.dtype, [int(x) for x in r.tolist()]

A, B = 612509347682975743, 616762138058293247
print("example nout=1:", pq([A, B], np.uint64, 1, 1))
print("example nout=3 (interp branch):", pq([A, B], np.uint64, 1, 3))
print("example int64 nout=1:", pq([A, B], np.int64, 1, 1))
big = [2**63 + 1, 2**63 + 1025, 5, 2**64 - 1]
print("uint64 straddle 2**63 nout=1:", pq(big, np.uint64, 1, 1))
print("uint64 straddle 2**63 nin=2 nout=2:", pq(big * 3, np.uint64, 2, 2))
neg = [-(2**62) - 1, -(2**62) + 1001, 2**62 + 7]
print("int64 neg nout=1:", pq(neg * 2, np.int64, 1, 1))
# set_index row conservation
rng = np.random.RandomState(0)
vals = (np.uint64(A) + rng.randint(0, 10**6, size=200).astype(np.uint64))
df = pd.DataFrame({"x": vals, "y": np.arange(200)})
d = dd.from_pandas(df, npartitions=4)  # from_pandas sorts? no, sort=True sorts by index, x unsorted
r = d.set_index("x", npartitions=3)
out = r.compute()
print("set_index rows:", len(out), "divisions0<=min:", r.divisions[0] <= int(vals.min()), r.divisions[0], int(vals.min()), "last<=max", r.divisions[-1] >= int(vals.max()))
