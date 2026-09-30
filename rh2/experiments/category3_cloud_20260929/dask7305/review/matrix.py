"""dask__dask-7305 复核者的私有行为矩阵（容器内 Python 3.8 运行，不交给求解者）。

按公开要求判对错，不以 gold 为答案：
- pq：partition_quantiles 的首项 == 精确最小值、末项 == 精确最大值，结果有序，全部落在 [min, max]，dtype 保持；
- si：set_index 的 divisions 首尾精确、有序，每行落在自己的区间，行不丢、不重复。
所有比较都转成 Python int，避免 numpy 把 uint64 与 int 的比较提升到 float64。
每个用例单独 try/except，输出一行一个 JSON。
"""
import json
import sys
import traceback

import numpy as np
import pandas as pd

import dask
import dask.dataframe as dd
from dask.dataframe.partitionquantiles import partition_quantiles

dask.config.set(scheduler="sync")

BIG = 612509347682975743
ISSUE = [BIG, 616762138058293247]
ORDER = [(i * 7919) % 200 for i in range(200)][::-1]  # 与修订 v1 相同的排列，k=0 在最后一行


def pq(values, dtype, nin, k):
    df = pd.DataFrame({"x": np.array(values, dtype=dtype)})
    ddf = dd.from_pandas(df, npartitions=nin, sort=False)
    r = partition_quantiles(ddf.x, npartitions=k).compute()
    got = [int(v) for v in r]
    lo, hi = min(values), max(values)
    ok = {
        "ends": got[0] == lo and got[-1] == hi,
        "sorted": got == sorted(got),
        "within": all(lo <= g <= hi for g in got),
        "dtype": r.dtype == np.dtype(dtype),
    }
    return {"ok": all(ok.values()), "detail": {k2: v for k2, v in ok.items() if not v},
            "d_first": got[0] - lo, "d_last": got[-1] - hi}


def si(values, dtype, nin, k, shuffle=None):
    df = pd.DataFrame({"x": np.array(values, dtype=dtype), "i": np.arange(len(values))})
    ddf = dd.from_pandas(df, npartitions=nin, sort=False)
    d1 = ddf.set_index("x", npartitions=k, shuffle=shuffle)
    divs = [int(v) for v in d1.divisions]
    parts = [d1.get_partition(j).compute() for j in range(d1.npartitions)]
    lo, hi = min(values), max(values)
    in_bounds = True
    for j, p in enumerate(parts):
        if not len(p):
            continue
        pmin, pmax = int(p.index.min()), int(p.index.max())
        upper = pmax <= divs[j + 1] if j == len(parts) - 1 else pmax < divs[j + 1]
        in_bounds = in_bounds and pmin >= divs[j] and upper
    rows = sorted((int(v), int(i)) for p in parts for v, i in zip(p.index, p.i))
    want = sorted((int(v), int(i)) for v, i in zip(values, range(len(values))))
    ok = {
        "div_ends": divs[0] == lo and divs[-1] == hi,
        "div_sorted": divs == sorted(divs),
        "in_bounds": in_bounds,
        "rows": rows == want,
    }
    return {"ok": all(ok.values()), "detail": {k2: v for k2, v in ok.items() if not v},
            "lost": len(want) - len(rows)}


def perm(vals):
    """按 ORDER 打乱（长度 200）；最小元素（下标 0）落在最后一行。"""
    return [vals[k] for k in ORDER]


U, I = "uint64", "int64"
T64, T63 = 2 ** 64, 2 ** 63
CASES = {
    # 修订 v1 已有的 5 个实例（对照用）
    "v1_issue_k1": (ISSUE, U, 1, 1),
    "v1_issue_k3": (ISSUE, U, 1, 3),
    "v1_uint200": (perm([BIG + 997 * k for k in range(200)]), U, 4, 4),
    "v1_int64": (perm([-BIG + 6125093476829757 * k for k in range(200)]), I, 4, 4),
    "v1_span63": (perm([BIG + 89000000000000001 * k for k in range(200)]), U, 4, 4),
    # 新实例：值密集（相邻差 1，小于 float64 在该量级的间距 128）
    "dense_mid": (perm([BIG + k for k in range(200)]), U, 4, 4),
    "dense_mid_k3": (perm([BIG + k for k in range(200)]), U, 4, 3),
    "dense_two_k3": ([BIG, BIG + 1], U, 1, 3),
    "dense_two_rev2p_k3": ([BIG + 1, BIG], U, 2, 3),
    "few_unique_dense_k5": ([[BIG, BIG + 1, BIG + 2][(7 * j) % 3] for j in range(300)], U, 3, 5),
    # float64 把 BIG+99..BIG+101 都舍入成 BIG+129（高于真实最大值）
    "dense_two_hi_k3": ([BIG + 100, BIG + 101], U, 1, 3),
    "few_unique_dense_hi_k5": ([[BIG + 99, BIG + 100, BIG + 101][j % 3] for j in range(300)], U, 3, 5),
    # 新实例：取值范围顶端（float64 会舍入到 2**64 / 2**63，再转回整数时溢出）
    "top64_dense": (perm([T64 - 200 + k for k in range(200)]), U, 4, 4),
    "top64_two_k3": ([T64 - 2, T64 - 1], U, 1, 3),
    "sentinel64": (perm([BIG + 997 * k for k in range(195)] + [T64 - 1] * 5), U, 4, 4),
    "top63_int64_dense": (perm([T63 - 200 + k for k in range(200)]), I, 4, 4),
    "bottom_int64_dense": (perm([-T63 + k for k in range(200)]), I, 4, 4),
    # 新实例：全为大负数；有序跨 0（第一个分区全为负）
    "neg_int64": (perm([-BIG - 997 * (199 - k) for k in range(200)]), I, 4, 4),
    "int64_sorted_span0": ([-BIG + 6125093476829757 * k for k in range(200)], I, 4, 4),
    # 其它规模
    "v1_uint200_k10": (perm([BIG + 997 * k for k in range(200)]), U, 4, 10),
    "v1_span63_k1": (perm([BIG + 89000000000000001 * k for k in range(200)]), U, 4, 1),
}


def small_int():
    df = pd.DataFrame({"x": [4, 1, 1, 3, 3], "y": [1.0, 1, 1, 1, 2]})
    d1 = dd.from_pandas(df, 2).set_index("x", npartitions=3)
    return {"divisions": [int(v) for v in d1.divisions]}


def ext_dtype():
    """可空整数扩展类型：只作回归对照（与 base 比较是否报错、结果是否一致）。"""
    res = {}
    for label, vals in (("small", [4, 1, 1, 3, 3, 2, 9, 7]), ("large", ISSUE * 4)):
        try:
            s = pd.Series(pd.array(vals, dtype="UInt64"), name="x")
            ds = dd.from_pandas(s, npartitions=2, sort=False)
            r = partition_quantiles(ds, npartitions=3).compute()
            res[label + "_pq"] = [str(v) for v in r] + [str(r.dtype)]
        except Exception as e:  # noqa: BLE001
            res[label + "_pq"] = f"{type(e).__name__}: {e}"[:120]
        try:
            df = pd.DataFrame({"x": pd.array(vals, dtype="UInt64"), "i": np.arange(len(vals))})
            d1 = dd.from_pandas(df, npartitions=2, sort=False).set_index("x", npartitions=3)
            res[label + "_si"] = [str(v) for v in d1.divisions] + [len(d1.compute())]
        except Exception as e:  # noqa: BLE001
            res[label + "_si"] = f"{type(e).__name__}: {e}"[:120]
    return res


def run(name, fn):
    try:
        rec = fn()
    except Exception as e:  # noqa: BLE001
        rec = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200], "tb": traceback.format_exc()[-400:]}
    rec["case"] = name
    print(json.dumps(rec, sort_keys=True), flush=True)


def main():
    only = set(sys.argv[1:])
    for name, (vals, dt, nin, k) in CASES.items():
        if only and name not in only:
            continue
        run("pq:" + name, lambda: pq(vals, dt, nin, k))
        run("si:" + name, lambda: si(vals, dt, nin, k))
    run("small_int", small_int)
    run("ext_dtype", ext_dtype)


if __name__ == "__main__":
    main()
