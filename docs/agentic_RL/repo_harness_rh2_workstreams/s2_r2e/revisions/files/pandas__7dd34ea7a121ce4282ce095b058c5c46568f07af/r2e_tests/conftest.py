# rh2 材料修订（B 线 T0-6 第二步，2026-09-24 夜）：R2E 把本题隐藏测试从 pandas/tests/indexes/ranges/test_setops.py 搬到 r2e_tests/ 后，
# 原目录上各层 conftest 不再生效，隐藏测试用到的 fixture 找不到（用例恒 ERROR）。下面按 pytest 的查找规则（最内层优先），
# 从 base 提交 f5c224215ad0 的 conftest 链原样摘出这些 fixture 及其依赖（extract_fixtures.py 生成，逐行未改）；
# 不加 autouse fixture 或 hook，不从工作区的 conftest 导入。

import pytest


# ---- 摘自 base 提交的 pandas/conftest.py（git blob 75711b19dfcf）原文 ----


@pytest.fixture(
    params=[
        ("foo", None, None),
        ("Egon", "Venkman", None),
        ("NCC1701D", "NCC1701D", "NCC1701D"),
    ]
)
def names(request):
    """
    A 3-tuple of names, the first two for operands, the last for a result.
    """
    return request.param


# ---- 摘自 base 提交的 pandas/tests/indexes/conftest.py（git blob 2eae51c62aa0）原文 ----


@pytest.fixture(params=[None, False])
def sort(request):
    """
    Valid values for the 'sort' parameter used in the Index
    setops methods (intersection, union, etc.)

    Caution:
        Don't confuse this one with the "sort" fixture used
        for DataFrame.append or concat. That one has
        parameters [True, False].

        We can't combine them as sort=True is not permitted
        in the Index setops methods.
    """
    return request.param
