"""dask__dask-8597 私有行为矩阵（容器内 python 执行；不交给求解者）。

逐个实例独立执行、互不影响，按公开要求判定，不以 gold 为答案：
- Z*（其它轴有零长度的数组做列表索引）：不抛异常；返回 dask Array；shape、dtype 与 NumPy 一致；
  assert_eq（图、逐块 shape/dtype、计算结果）通过；不发 PerformanceWarning／RuntimeWarning。
  split-large-chunks 的三种取值（None 默认、False、True）各跑一遍。
- N*（非空数组、已有的公开行为）：默认配置对真正的大块发 PerformanceWarning；False 静音；True 拆块且不告警；
  小的整数列表索引不告警。场景取自公开旧测试 test_getitem_avoids_large_chunks、test_slicing_integer_no_warnings。
输出：每行一个 JSON；最后一行 SUMMARY。
"""
import json
import warnings

import numpy as np

import dask
import dask.array as da
from dask.array.utils import assert_eq

SPLIT = "array.slicing.split-large-chunks"


def short(e):
    return f"{type(e).__name__}: {str(e).splitlines()[0][:160] if str(e) else ''}"


def index_of(x, idx):
    return x[idx]


# name -> (numpy 输入, chunks, 索引, 取值方式)
ZERO_CASES = {
    "Z1_issue": (lambda: np.zeros((3, 0)), "auto", ([0],)),
    "Z2_zero_first_axis1": (lambda: np.zeros((0, 3)), "auto", (slice(None), [2, 0, 2])),
    "Z3_mid_zero_3d_i4": (lambda: np.zeros((6, 0, 4), dtype="i4"), (2, -1, 2), ([5, 0, 5, -1, 3],)),
    "Z4_multichunk_rows": (lambda: np.zeros((6, 0)), (2, -1), ([5, 0, 5, -1],)),
    "Z5_long_index12": (lambda: np.zeros((3, 0)), "auto", ([0, 1, 2] * 4,)),
    "Z6_int64_2d": (lambda: np.zeros((3, 0), dtype="i8"), "auto", ([1, 2],)),
    "Z7_bool_list": (lambda: np.zeros((3, 0)), "auto", ([True, False, True],)),
    "Z8_da_take": (lambda: np.zeros((3, 0)), "auto", "da_take"),
    "Z9_dask_int_index": (lambda: np.zeros((3, 0)), "auto", "dask_index"),
    "Z10_mixed_slice_list": (lambda: np.ones((3, 4)), 2, (slice(None, 0), [1, 3])),
    "Z11_other_axis_multichunk": (lambda: np.zeros((3, 0, 4)), (-1, -1, 2), ([0, 2],)),
    "Z12_empty_index": (lambda: np.zeros((3, 0)), "auto", ([],)),
}


def zero_case(name, cfg):
    make, chunks, idx = ZERO_CASES[name]
    rec = {"case": name, "cfg": cfg}
    w = []
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            with dask.config.set(cfg):
                xn = make()
                x = da.from_array(xn, chunks=chunks)
                if idx == "da_take":
                    res, exp = da.take(x, [0, 1], axis=0), np.take(xn, [0, 1], axis=0)
                elif idx == "dask_index":
                    res, exp = x[da.from_array(np.array([0, 2]))], xn[np.array([0, 2])]
                else:
                    res, exp = x[idx], xn[idx]
                rec["type"] = type(res).__name__
                rec["shape"] = list(res.shape)
                rec["dtype"] = str(res.dtype)
                rec["expected"] = [list(exp.shape), str(exp.dtype)]
                if isinstance(res, da.Array):
                    rec["chunks"] = [list(c) for c in res.chunks]
                    try:
                        assert_eq(res, exp)
                        rec["assert_eq"] = "ok"
                    except BaseException as e:  # noqa: BLE001
                        rec["assert_eq"] = short(e)
                    try:
                        c = np.asarray(res.compute())
                        rec["computed"] = [list(c.shape), str(c.dtype)]
                    except BaseException as e:  # noqa: BLE001
                        rec["computed"] = short(e)
                else:
                    rec["assert_eq"] = "not a dask Array"
        rec["warnings"] = sorted({f"{x.category.__name__}: {str(x.message).splitlines()[0][:80]}" for x in w})
    except BaseException as e:  # noqa: BLE001
        rec["error"] = short(e)
        rec["warnings"] = sorted({f"{x.category.__name__}: {str(x.message).splitlines()[0][:80]}" for x in w})
    bad_warn = [s for s in rec.get("warnings", []) if s.startswith(("PerformanceWarning", "RuntimeWarning"))]
    rec["ok"] = (
        "error" not in rec
        and rec.get("type") == "Array"
        and rec.get("assert_eq") == "ok"
        and rec.get("computed") == rec.get("expected")
        and not bad_warn
    )
    return rec


def large_case(split):
    """公开旧测试 test_getitem_avoids_large_chunks 的场景（非空数组）。"""
    rec = {"case": "N_large_chunk", "cfg": {SPLIT: split}}
    try:
        with dask.config.set({"array.chunk-size": "0.1Mb", SPLIT: split}):
            a = np.arange(2 * 128 * 128, dtype="int64").reshape(2, 128, 128)
            arr = da.from_array(a, chunks=(1, 128, 128))
            indexer = [0] + [1] * 11
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                res = arr[indexer]
            perf = [x for x in w if issubclass(x.category, da.PerformanceWarning)]
            rec["perf_warnings"] = len(perf)
            rec["chunks0"] = list(res.chunks[0])
            try:
                assert_eq(res, a[indexer])
                rec["assert_eq"] = "ok"
            except BaseException as e:  # noqa: BLE001
                rec["assert_eq"] = short(e)
    except BaseException as e:  # noqa: BLE001
        rec["error"] = short(e)
    want_warn = 1 if split is None else 0
    want_chunks = [1] * 12 if split is True else [1, 11]
    rec["ok"] = (
        "error" not in rec
        and rec.get("assert_eq") == "ok"
        and (rec.get("perf_warnings", 0) >= 1) == bool(want_warn)
        and rec.get("chunks0") == want_chunks
    )
    return rec


def small_no_warning():
    """公开旧测试 test_slicing_integer_no_warnings 的场景。"""
    rec = {"case": "N_small_no_warning", "cfg": {}}
    try:
        X = da.random.random((100, 2), (2, 2))
        idx = np.array([0, 0, 1, 1])
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            X[idx].compute()
        rec["warnings"] = sorted({f"{x.category.__name__}: {str(x.message)[:80]}" for x in w})
    except BaseException as e:  # noqa: BLE001
        rec["error"] = short(e)
    rec["ok"] = "error" not in rec and not rec.get("warnings")
    return rec


def small_chunksize_long_index():
    """边缘规模（登记 T3 用）：chunk-size 设为 1kB，零宽数组用 700 个下标。"""
    rec = {"case": "E_chunksize1kB_index700", "cfg": {"array.chunk-size": "1kB"}}
    try:
        with dask.config.set({"array.chunk-size": "1kB"}):
            x = da.from_array(np.zeros((3, 0)))
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                res = x[[0, 1, 2] * 233 + [0]]
            rec["warnings"] = sorted({f"{x.category.__name__}: {str(x.message).splitlines()[0][:60]}" for x in w})
            rec["shape"] = list(res.shape)
            rec["nchunks0"] = len(res.chunks[0])
    except BaseException as e:  # noqa: BLE001
        rec["error"] = short(e)
    rec["ok"] = "error" not in rec and not rec.get("warnings") and rec.get("shape") == [700, 0]
    return rec


def main():
    out = []
    for split in (None, False, True):
        for name in ZERO_CASES:
            out.append(zero_case(name, {SPLIT: split}))
    for split in (None, False, True):
        out.append(large_case(split))
    out.append(small_no_warning())
    out.append(small_chunksize_long_index())
    for r in out:
        print(json.dumps(r, ensure_ascii=False))
    print("SUMMARY " + json.dumps({f"{r['case']}|{r['cfg'].get(SPLIT, '-')}": r["ok"] for r in out}))


if __name__ == "__main__":
    main()
