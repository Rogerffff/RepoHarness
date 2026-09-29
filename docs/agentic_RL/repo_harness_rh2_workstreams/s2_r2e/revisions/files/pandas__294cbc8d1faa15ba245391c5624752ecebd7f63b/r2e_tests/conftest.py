# rh2 材料修订（B 线 T0-6 第二步，2026-09-24 夜）：R2E 把本题隐藏测试从 pandas/tests/io/formats/test_info.py 搬到 r2e_tests/ 后，
# 原目录上各层 conftest 不再生效，隐藏测试用到的 fixture 找不到（用例恒 ERROR）。下面按 pytest 的查找规则（最内层优先），
# 从 base 提交 13df3ec070e8 的 conftest 链原样摘出这些 fixture 及其依赖（extract_fixtures.py 生成，逐行未改）；
# 不加 autouse fixture 或 hook，不从工作区的 conftest 导入。

import pytest
from pandas import DataFrame
import pandas._testing as tm


# ---- 摘自 base 提交的 pandas/conftest.py（git blob ebb24c184d9a）原文 ----


@pytest.fixture
def float_frame():
    """
    Fixture for DataFrame of floats with index of unique strings

    Columns are ['A', 'B', 'C', 'D'].

                       A         B         C         D
    P7GACiRnxd -0.465578 -0.361863  0.886172 -0.053465
    qZKh6afn8n -0.466693 -0.373773  0.266873  1.673901
    tkp0r6Qble  0.148691 -0.059051  0.174817  1.598433
    wP70WOCtv8  0.133045 -0.581994 -0.992240  0.261651
    M2AeYQMnCz -1.207959 -0.185775  0.588206  0.563938
    QEPzyGDYDo -0.381843 -0.758281  0.502575 -0.565053
    r78Jwns6dn -0.653707  0.883127  0.682199  0.206159
    ...              ...       ...       ...       ...
    IHEGx9NO0T -0.277360  0.113021 -1.018314  0.196316
    lPMj8K27FA -1.313667 -0.604776 -1.305618 -0.863999
    qa66YMWQa5  1.110525  0.475310 -0.747865  0.032121
    yOa0ATsmcE -0.431457  0.067094  0.096567 -0.264962
    65znX3uRNG  1.528446  0.160416 -0.109635 -0.032987
    eCOBvKqf3e  0.235281  1.622222  0.781255  0.392871
    xSucinXxuV -1.263557  0.252799 -0.552247  0.400426

    [30 rows x 4 columns]
    """
    return DataFrame(tm.getSeriesData())
