"""私有行为对照：题面示例（顶层与 ma 入口）、隐藏测试同款 3x2 分块数据的逐元素 mask/值/dtype/类型。"""
import json

import numpy as np

import dask.array as da

out = {}
arr = da.ma.masked_array([2, 3, 4], mask=[0, 0, 1])
for ns_name, ns in (("toplevel", da), ("ma", da.ma)):
    for fn in ("ones_like", "zeros_like", "empty_like"):
        f = getattr(ns, fn, None)
        if f is None:
            out[f"example.{ns_name}.{fn}"] = "missing"
            continue
        try:
            r = f(arr).compute()
            out[f"example.{ns_name}.{fn}"] = {"type": type(r).__name__, "mask": np.ma.getmaskarray(r).tolist(),
                                              "data": None if fn == "empty_like" else np.ma.getdata(r).tolist()}
        except Exception as e:  # noqa: BLE001
            out[f"example.{ns_name}.{fn}"] = f"{type(e).__name__}: {e}"
mask = np.array([[True, False], [True, True], [False, True]])
data = np.arange(6).reshape((3, 2))
a = np.ma.array(data, mask=mask)
d_a = da.ma.masked_array(data=data, mask=mask, chunks=2)
for ns_name, ns in (("toplevel", da), ("ma", da.ma)):
    for fn in ("ones_like", "zeros_like", "empty_like"):
        f = getattr(ns, fn, None)
        if f is None:
            out[f"fixture.{ns_name}.{fn}"] = "missing"
            continue
        r = f(d_a).compute()
        sol = getattr(np.ma.core, fn)(a)
        out[f"fixture.{ns_name}.{fn}"] = {
            "type": type(r).__name__, "dtype": str(r.dtype),
            "mask_equal_numpy": bool((np.ma.getmaskarray(r) == np.ma.getmaskarray(sol)).all()),
            "unmasked_values_equal": None if fn == "empty_like" else bool(np.ma.allclose(r, sol, masked_equal=True)),
            "all_values_equal": None if fn == "empty_like" else bool((np.ma.getdata(r) == np.ma.getdata(sol)).all())}
print(json.dumps(out, ensure_ascii=False, indent=1))
