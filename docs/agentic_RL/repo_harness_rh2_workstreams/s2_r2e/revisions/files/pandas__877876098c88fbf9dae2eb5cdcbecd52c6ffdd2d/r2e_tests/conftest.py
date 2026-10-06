# rh2 材料修订（B 线 T0-6 第二步，2026-09-24 夜）：R2E 把本题隐藏测试从 pandas/tests/reshape/merge/test_multi.py, pandas/tests/indexes/multi/test_join.py 搬到 r2e_tests/ 后，
# 原目录上各层 conftest 不再生效，隐藏测试用到的 fixture 找不到（用例恒 ERROR）。下面按 pytest 的查找规则（最内层优先），
# 从 base 提交 0be573ee5dc0 的 conftest 链原样摘出这些 fixture 及其依赖（extract_fixtures.py 生成，逐行未改）；
# 不加 autouse fixture 或 hook，不从工作区的 conftest 导入。

import pytest
import numpy as np
from pandas import Index, MultiIndex


# ---- 摘自 base 提交的 pandas/conftest.py（git blob 0a3bf31cf966）原文 ----


@pytest.fixture(params=["inner", "outer", "left", "right"])
def join_type(request):
    """
    Fixture for trying all types of join operations.
    """
    return request.param


# ---- 摘自 base 提交的 pandas/tests/indexes/multi/conftest.py（git blob acaea4ff96ff）原文 ----


@pytest.fixture
def idx():
    # a MultiIndex used to test the general functionality of the
    # general functionality of this object
    major_axis = Index(["foo", "bar", "baz", "qux"])
    minor_axis = Index(["one", "two"])

    major_codes = np.array([0, 0, 1, 2, 3, 3])
    minor_codes = np.array([0, 1, 0, 1, 0, 1])
    index_names = ["first", "second"]
    mi = MultiIndex(
        levels=[major_axis, minor_axis],
        codes=[major_codes, minor_codes],
        names=index_names,
        verify_integrity=False,
    )
    return mi
