"""初判阶段的探针（读作者材料之前）：base 与 gold 上 set_index 的行守恒与区间归属，disk 与 tasks 两种 shuffle。私有对照，不交给求解者。"""
import numpy as np, pandas as pd, dask, dask.dataframe as dd
dask.config.set(scheduler="sync")
A, B = 612509347682975743, 616762138058293247

def si(vals, dtype, nin, nout, shuffle):
    df = pd.DataFrame({"x": np.array(vals, dtype=dtype), "y": np.arange(len(vals))})
    d = dd.from_pandas(df, npartitions=nin, sort=False)
    r = d.set_index("x", npartitions=nout, shuffle=shuffle)
    parts = [p for p in r.to_delayed()]
    rows = 0; misplaced = 0
    divs = r.divisions
    for i, p in enumerate(parts):
        pdf = p.compute()
        rows += len(pdf)
        if len(pdf):
            lo, hi = divs[i], divs[i + 1]
            ix = pdf.index.values
            bad = [(int(v)) for v in ix if not (int(lo) <= int(v) <= int(hi))]
            misplaced += len(bad)
    return dict(rows=rows, n=len(vals), misplaced=misplaced, div0=int(divs[0]), divN=int(divs[-1]), mn=int(np.min(np.array(vals, dtype=dtype))), mx=int(np.max(np.array(vals, dtype=dtype))))

rng = np.random.RandomState(0)
v = (np.uint64(A) + rng.randint(0, 10**6, size=200).astype(np.uint64))
for sh in ["disk", "tasks"]:
    print("rand200 uint64 nin4 nout3", sh, si(v, np.uint64, 4, 3, sh))
# few unique values, more output partitions -> interp branch
v2 = [B, A, B, A, B, A]
for sh in ["disk", "tasks"]:
    print("2uniq nin2 nout3", sh, si(v2, np.uint64, 2, 3, sh))
# straddle 2**63
v3 = [2**63 + 1, 5, 2**64 - 1, 2**63 - 3, 2**63 + 1025, 7] * 4
for sh in ["disk", "tasks"]:
    print("straddle nin2 nout2", sh, si(v3, np.uint64, 2, 2, sh))
