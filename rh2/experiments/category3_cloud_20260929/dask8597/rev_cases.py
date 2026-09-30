"""修订测试草案 v1／v2 的逐实例核对（容器内执行；不交给求解者）。

把修订版 F2P 的每个实例拆成独立的 pytest 用例，写到 /testbed/dask/array/tests/ 下的临时模块里再跑，
这样仓库 setup.cfg 的 filterwarnings（dask 等模块归属的警告即错误）与修订版 F2P 完全相同；跑完删除临时文件。
实例与 revised_test_v1.patch／revised_test_v2.patch 中的字面值逐一对应（两版只差 c4 的下标个数）：
- orig：原 F2P 的 3 行（题面原例、默认配置）；
- c1_issue／c2_zero_first_axis1／c3_mid_zero_i4_multichunk／c4_index120（草案 v1）／c4_index12000（草案 v2）：实例 × split None/False/True；
- default_warning：非空数组真正的大块在默认配置下仍发 PerformanceWarning。
"""
import subprocess
import sys
from pathlib import Path

MODULE = '''
import numpy as np
import pytest

import dask
import dask.array as da
from dask.array.utils import assert_eq

CASES = {
    "c1_issue": lambda: (np.zeros((3, 0)), "auto", ([0],)),
    "c2_zero_first_axis1": lambda: (np.zeros((0, 3)), "auto", (slice(None), [2, 0, 2])),
    "c3_mid_zero_i4_multichunk": lambda: (np.zeros((6, 0, 4), dtype="i4"), (2, -1, 2), ([5, 0, 5, -1, 3],)),
    "c4_index120": lambda: (np.zeros((3, 0)), "auto", ([0, 1, 2] * 40,)),
    "c4_index12000": lambda: (np.zeros((3, 0)), "auto", ([0, 1, 2] * 4000,)),
}


def test_orig():
    array = da.from_array(np.zeros((3, 0)))
    expected = np.zeros((3, 0))[[0]]
    assert_eq(array[[0]], expected)


@pytest.mark.parametrize("split", [None, False, True])
@pytest.mark.parametrize("case", list(CASES))
def test_case(case, split):
    x, chunks, index = CASES[case]()
    with dask.config.set({"array.slicing.split-large-chunks": split}):
        result = da.from_array(x, chunks=chunks)[index]
        assert isinstance(result, da.Array)
        assert_eq(result, x[index])


def test_default_warning():
    with dask.config.set({"array.chunk-size": "0.1Mb"}):
        a = np.arange(2 * 128 * 128, dtype="int64").reshape(2, 128, 128)
        arr = da.from_array(a, chunks=(1, 128, 128))
        with pytest.warns(da.PerformanceWarning):
            arr[[0] + [1] * 11]
'''


def main():
    path = Path("/testbed/dask/array/tests/test_c3_rev_cases_tmp.py")
    path.write_text(MODULE)
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-n0", "-rA", "--color=no", "-p", "no:cacheprovider",
                            "-q", str(path.relative_to("/testbed"))], cwd="/testbed", capture_output=True, text=True)
        print(r.stdout[-60000:])
        print(r.stderr[-5000:])
    finally:
        path.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
