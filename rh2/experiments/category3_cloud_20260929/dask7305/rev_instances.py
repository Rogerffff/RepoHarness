"""逐个执行修订版 F2P 中的各断言实例（不因第一处失败而停），看每个实例单独拦住哪些候选。

在已应用 revised_test_v1.patch 的 /testbed 中运行（私有对照，不交给求解者）。
实例与 revised_test_v1.patch 的 test_set_index_interpolate 一一对应。
"""
import json

import numpy as np
import pandas as pd

import dask.dataframe as dd
from dask.dataframe.tests import test_shuffle as t
from dask.dataframe.utils import assert_eq


def small():
    df = pd.DataFrame({"x": [4, 1, 1, 3, 3], "y": [1.0, 1, 1, 1, 2]})
    d1 = dd.from_pandas(df, 2).set_index("x", npartitions=3)
    assert d1.npartitions == 3
    assert d1.divisions[0] == 1
    assert d1.divisions[-1] == 4
    assert list(d1.divisions) == sorted(d1.divisions)
    assert all(np.issubdtype(type(x), np.integer) for x in d1.divisions)
    assert_eq(d1, df.set_index("x"))


big = 612509347682975743
issue = [big, 616762138058293247]
order = [(i * 7919) % 200 for i in range(200)][::-1]
cases = {
    "small_relaxed": small,
    "issue_1to1": lambda: t._assert_exact_int_divisions(issue, "uint64", 1, 1),
    "issue_1to3": lambda: t._assert_exact_int_divisions(issue, "uint64", 1, 3),
    "uint_200_4to4": lambda: t._assert_exact_int_divisions([big + 997 * k for k in order], "uint64", 4, 4),
    "int64_200_4to4": lambda: t._assert_exact_int_divisions(
        [-big + 6125093476829757 * k for k in order], "int64", 4, 4),
    "span63_200_4to4": lambda: t._assert_exact_int_divisions(
        [big + 89000000000000001 * k for k in order], "uint64", 4, 4),
}
res = {}
for name, fn in cases.items():
    try:
        fn()
        res[name] = "pass"
    except AssertionError as e:
        res[name] = "FAIL " + str(e).splitlines()[0][:80] if str(e) else "FAIL"
    except Exception as e:  # noqa: BLE001
        res[name] = f"ERROR {type(e).__name__}: {e}"[:120]
print(json.dumps(res))
