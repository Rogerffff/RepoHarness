"""公开复现：orange3 4014f248 —— EqualFreq 对只差几个 eps 的值给出重复切点，建区间时 AssertionError。

依据：公开题面示例代码，原样改写（Table.from_numpy(None, X) + discretize.EqualFreq(n=4)）。
只观测，不写工作区。
"""
import sys
import traceback


def main():
    import numpy as np
    from Orange.data import Table
    from Orange.preprocess import discretize

    eps = np.finfo(float).eps
    X = np.array([[1], [1 + eps], [1 + 2 * eps], [1 + 3 * eps]])
    table = Table.from_numpy(None, X)
    disc = discretize.EqualFreq(n=4)
    try:
        var = disc(table, table.domain[0])
        points = [float(p) for p in var.compute_value.points]
    except AssertionError:
        tail = traceback.format_exc().strip().splitlines()[-3:]
        print("EXC=AssertionError | " + " | ".join(t.strip() for t in tail))
        return 1, "AssertionError while building discretized intervals"
    print(f"POINTS={points!r}")
    if len(set(points)) != len(points):
        return 1, "threshold points are not unique"
    return 0, "points unique and no AssertionError"


if __name__ == "__main__":
    try:
        observed, why = main()
    except Exception:  # 脚本自身或环境出错
        traceback.print_exc()
        print("REPRO_OBSERVED=0")
        print("REPRO_REASON=unexpected_exception")
        sys.exit(3)
    print(f"REPRO_OBSERVED={observed}")
    print(f"REPRO_REASON={why}")
    sys.exit(0)
