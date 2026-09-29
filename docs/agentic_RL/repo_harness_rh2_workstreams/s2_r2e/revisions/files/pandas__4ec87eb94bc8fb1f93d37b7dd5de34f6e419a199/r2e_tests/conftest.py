# rh2 材料修订（B 线 T0-6 代表修复，2026-09-24）：R2E 把本题隐藏测试从 pandas/tests/groupby/test_quantile.py
# 搬到 r2e_tests/ 后，pytest 不再加载 pandas/conftest.py，隐藏测试用到的下面两个 fixture 不可达（两个用例恒 ERROR）。
# 这里从 base 提交 baa10328 的 pandas/conftest.py（git blob 46975aa039b1）原样摘出这两个 fixture；
# 不加其它 fixture、autouse 或 hook，不从工作区的 conftest 导入。
import pytest

import pandas._testing as tm


@pytest.fixture(params=tm.FLOAT_NUMPY_DTYPES + tm.FLOAT_EA_DTYPES)
def any_float_dtype(request):
    """
    Parameterized fixture for float dtypes.

    * float
    * 'float32'
    * 'float64'
    * 'Float32'
    * 'Float64'
    """
    return request.param


@pytest.fixture(params=tm.ALL_INT_EA_DTYPES)
def any_int_ea_dtype(request):
    """
    Parameterized fixture for any nullable integer dtype.

    * 'UInt8'
    * 'Int8'
    * 'UInt16'
    * 'Int16'
    * 'UInt32'
    * 'Int32'
    * 'UInt64'
    * 'Int64'
    """
    return request.param
