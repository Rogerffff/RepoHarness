"""npartitions="auto" 路径（T3）：1000 个乱序大 uint64、4 个输入分区，看 set_index 是否丢行、divisions 端点是否精确。私有对照。"""
import numpy as np, pandas as pd, dask, dask.dataframe as dd
dask.config.set(scheduler="sync")
rs = np.random.RandomState(0)
vals = [612509347682975743 + int(i) * 997 for i in rs.permutation(1000)]
i = vals.index(min(vals)); vals[i], vals[-1] = vals[-1], vals[i]
df = pd.DataFrame({"x": np.array(vals, dtype="uint64")})
d1 = dd.from_pandas(df, npartitions=4, sort=False).set_index("x", npartitions="auto")
divs = d1.divisions
print({"rows": len(d1.compute()), "expected": len(vals), "div_types": sorted({type(v).__name__ for v in divs}),
       "first_minus_min": int(divs[0]) - min(vals), "last_minus_max": int(divs[-1]) - max(vals)})
