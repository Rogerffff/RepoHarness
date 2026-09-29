"""dask__dask-7305 私有行为矩阵（容器内 Python 3.8 运行，不交给求解者）。

按公开要求判对错，不以 gold 为答案：
- partition_quantiles 对大整数输入返回精确的最小值与最大值（端点），dtype 保持输入 dtype；
- 结果有序、落在 [min, max] 内；
- set_index 后每个分区的索引都落在自己的 divisions 区间内，内容与 pandas 一致，最小值不落到最后一个分区。
每个用例单独 try/except，一个候选崩溃不影响其它用例。输出一行一个 JSON。
"""
import json
import traceback

import numpy as np
import pandas as pd

import dask
import dask.dataframe as dd
from dask.dataframe.partitionquantiles import partition_quantiles
from dask.dataframe.utils import assert_eq

dask.config.set(scheduler="sync")

ISSUE = [612509347682975743, 616762138058293247]
TWO63 = 2 ** 63


def many_uint(n=1000, seed=0, base=612509347682975743, step=997):
    """n 个互不相同的大 uint64（全在 2**53 以上、2**63 以下），乱序，并把最小值放在最后一行。"""
    rs = np.random.RandomState(seed)
    vals = [base + int(i) * step for i in rs.permutation(n)]
    i = vals.index(min(vals))
    vals[i], vals[-1] = vals[-1], vals[i]
    return vals


def many_int64(n=1000, seed=1):
    """跨 0 的大有符号 int64（|x| 约 6e17），乱序，最小值放最后。"""
    rs = np.random.RandomState(seed)
    vals = [-612509347682975743 + int(i) * 1224937 * 1000 for i in rs.permutation(n)]
    i = vals.index(min(vals))
    vals[i], vals[-1] = vals[-1], vals[i]
    return vals


def span63(n=1000, seed=2):
    """uint64 均匀分布在整个取值范围（哈希类 ID），一半以上在 2**63 以上；最小值放最后。"""
    rs = np.random.RandomState(seed)
    vals = [int(v) for v in rs.randint(0, 2 ** 64, size=n, dtype=np.uint64)]
    vals = list(dict.fromkeys(vals))
    i = vals.index(min(vals))
    vals[i], vals[-1] = vals[-1], vals[i]
    return vals


def few_unique(n_each=100):
    """300 行，只有 3 个不同的大 uint64 值，乱序。"""
    rs = np.random.RandomState(3)
    vals = [612509347682975743, 614000000000000001, 616762138058293247] * n_each
    return [vals[i] for i in rs.permutation(len(vals))]


def emit(rec):
    print(json.dumps(rec, sort_keys=True), flush=True)


def run(case, fn):
    try:
        rec = fn()
        rec["case"] = case
    except Exception as e:  # noqa: BLE001
        rec = {"case": case, "error": f"{type(e).__name__}: {e}"[:300],
               "tb": traceback.format_exc()[-600:]}
    emit(rec)


def pq(values, dtype, in_parts, k):
    def f():
        pdf = pd.DataFrame({"a": np.array(values, dtype=dtype)})
        # sort=False：按行切块，2 行也能切成 2 个分区（sort=True 会并成 1 个）
        ddf = dd.from_pandas(pdf, npartitions=in_parts, sort=False)
        r = partition_quantiles(ddf.a, npartitions=k).compute()
        got = [int(x) for x in r]
        lo, hi = min(int(v) for v in values), max(int(v) for v in values)
        return {
            "kind": "pq", "k": k, "in_parts": ddf.npartitions, "n": len(values),
            "dtype": str(r.dtype), "dtype_ok": r.dtype == np.dtype(dtype),
            "name_ok": r.name == "a",
            "index_ok": list(r.index) == list(np.linspace(0, 1, k + 1)),
            "first": str(got[0]), "last": str(got[-1]),
            "first_minus_min": got[0] - lo, "last_minus_max": got[-1] - hi,
            "ends_ok": got[0] == lo and got[-1] == hi,
            "sorted": got == sorted(got),
            "within": all(lo <= g <= hi for g in got),
        }
    return f


def si(values, dtype, in_parts, k):
    def f():
        pdf = pd.DataFrame({"x": np.array(values, dtype=dtype), "i": np.arange(len(values))})
        ddf = dd.from_pandas(pdf, npartitions=in_parts, sort=False)
        d1 = ddf.set_index("x", npartitions=k)
        divs = [int(v) for v in d1.divisions]
        parts = [d1.get_partition(j).compute() for j in range(d1.npartitions)]
        lo, hi = min(int(v) for v in values), max(int(v) for v in values)
        bounds = []
        for j, p in enumerate(parts):
            if not len(p):
                bounds.append(True)
                continue
            pmin, pmax = int(p.index.min()), int(p.index.max())
            upper_ok = pmax <= divs[j + 1] if j == len(parts) - 1 else pmax < divs[j + 1]
            bounds.append(pmin >= divs[j] and upper_ok)
        min_parts = [j for j, p in enumerate(parts) if len(p) and int(p.index.min()) == lo]
        got = pd.concat(parts)
        content_ok = sorted(zip(got.index.astype(object), got.i)) == sorted(
            zip(pdf.x.astype(object), pdf.i))
        try:
            assert_eq(d1, pdf.set_index("x"))
            ae = True
        except AssertionError as e:
            ae = f"AssertionError: {str(e)[:160]}"
        return {
            "kind": "si", "k": k, "in_parts": ddf.npartitions, "out_parts": d1.npartitions,
            "n": len(values),
            "div_first_minus_min": divs[0] - lo, "div_last_minus_max": divs[-1] - hi,
            "div_ends_ok": divs[0] == lo and divs[-1] == hi,
            "div_types": sorted({type(v).__name__ for v in d1.divisions}),
            "rows_in_bounds": all(bounds), "min_row_partitions": min_parts,
            "content_ok": content_ok, "assert_eq": ae,
        }
    return f


def small_int():
    df = pd.DataFrame({"x": [4, 1, 1, 3, 3], "y": [1.0, 1, 1, 1, 2]})
    d = dd.from_pandas(df, 2)
    d1 = d.set_index("x", npartitions=3)
    d2 = d.set_index("y", npartitions=3)
    try:
        assert_eq(d1, df.set_index("x"))
        ae = True
    except AssertionError as e:
        ae = f"AssertionError: {str(e)[:160]}"
    return {"kind": "small", "x_divisions": [int(v) for v in d1.divisions],
            "x_set": sorted({int(v) for v in d1.divisions}), "x_npart": d1.npartitions,
            "x_assert_eq": ae, "y_divisions": [float(v) for v in d2.divisions]}


def auto_path():
    vals = many_uint()
    pdf = pd.DataFrame({"x": np.array(vals, dtype="uint64")})
    d1 = dd.from_pandas(pdf, 4).set_index("x", npartitions="auto")
    divs = d1.divisions
    return {"kind": "auto", "div_types": sorted({type(v).__name__ for v in divs}),
            "rows": len(d1.compute()), "rows_expected": len(vals),
            "div_first": repr(divs[0]), "div_last": repr(divs[-1]),
            "div_first_eq_min": divs[0] == min(vals), "div_last_eq_max": divs[-1] == max(vals)}


def min_dtype():
    pdf = pd.DataFrame({"a": np.array(ISSUE, dtype=np.uint64)})
    ddf = dd.from_pandas(pdf, npartitions=1)
    col_min = ddf.a.min().compute()
    idx = dd.from_pandas(pdf.set_index("a"), npartitions=1).index
    idx_min = idx.min().compute()
    return {"kind": "min_dtype", "series_min": [str(col_min), type(col_min).__name__],
            "index_min_meta_dtype": str(idx.min().dtype),
            "index_min": [str(idx_min), type(idx_min).__name__, str(getattr(idx_min, "dtype", None))]}


def main():
    U, I = "uint64", "int64"
    rev = list(reversed(ISSUE))
    hi2 = [TWO63 + v for v in ISSUE]
    mu, mi, sp, fu = many_uint(), many_int64(), span63(), few_unique()
    # 直接调用 partition_quantiles
    for k in (1, 2, 3, 5):
        run(f"pq_issue_k{k}", pq(ISSUE, U, 1, k))          # 题面数据，k=1 是题面原例
    for k in (1, 3):
        run(f"pq_issue_rev2p_k{k}", pq(rev, U, 2, k))      # 两个输入分区，最小值在后
    for k in (1, 4, 10):
        run(f"pq_many_uint_k{k}", pq(mu, U, 4, k))
    for k in (1, 4):
        run(f"pq_many_int64_k{k}", pq(mi, I, 4, k))
        run(f"pq_span63_k{k}", pq(sp, U, 4, k))
    for k in (1, 3):
        run(f"pq_above63_k{k}", pq(hi2, U, 1, k))          # 两个值都在 2**63 以上
    run("pq_span63_two_k1", pq([ISSUE[0], 18446744073709551557], U, 1, 1))
    run("pq_few_unique_k5", pq(fu, U, 3, 5))
    run("pq_small_int_k3", pq([4, 1, 1, 3, 3], I, 2, 3))
    # set_index（题面的乱序症状）
    run("si_issue_k1", si(ISSUE, U, 1, 1))                 # 即 P2P large_uint 的数据
    run("si_issue_k3", si(ISSUE, U, 1, 3))                 # 同一数据，请求 3 个输出分区
    run("si_issue_rev2p_k1", si(rev, U, 2, 1))
    run("si_issue_rev2p_k2", si(rev, U, 2, 2))
    for k in (3, 4):
        run(f"si_many_uint_k{k}", si(mu, U, 4, k))
    run("si_many_int64_k4", si(mi, I, 4, 4))
    run("si_span63_k4", si(sp, U, 4, 4))
    run("si_few_unique_k5", si(fu, U, 3, 5))
    run("small_int", small_int)
    run("auto_path", auto_path)
    run("min_dtype", min_dtype)


if __name__ == "__main__":
    main()
