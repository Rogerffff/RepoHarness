# rh2 材料修订（B 线 T0-6 第二步，2026-09-24 夜）：R2E 把本题隐藏测试从 pandas/tests/reshape/merge/test_merge.py, pandas/tests/reshape/merge/test_join.py 搬到 r2e_tests/ 后，
# 原目录上各层 conftest 不再生效，隐藏测试用到的 fixture 找不到（用例恒 ERROR）。下面按 pytest 的查找规则（最内层优先），
# 从 base 提交 059c8bac51e4 的 conftest 链原样摘出这些 fixture 及其依赖（extract_fixtures.py 生成，逐行未改）；
# 不加 autouse fixture 或 hook，不从工作区的 conftest 导入。

import pytest
import pandas as pd


# ---- 摘自 base 提交的 pandas/conftest.py（git blob 35affa62ccf6）原文 ----


@pytest.fixture(params=["inner", "outer", "left", "right"])
def join_type(request):
    """
    Fixture for trying all types of join operations.
    """
    return request.param


@pytest.fixture
def using_array_manager(request):
    """
    Fixture to check if the array manager is being used.
    """
    return pd.options.mode.data_manager == "array"
