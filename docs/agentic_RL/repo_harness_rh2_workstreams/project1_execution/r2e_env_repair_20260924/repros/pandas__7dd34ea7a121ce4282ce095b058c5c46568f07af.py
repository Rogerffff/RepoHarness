"""公开复现：pandas 7dd34ea7 —— 负步长 RangeIndex 的 difference（sort=None）结果是降序。

依据：公开题面示例代码，原样改写（difference 默认 sort=None）。只观测，不写工作区。
"""
import sys
import traceback


def main():
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    idx = pd.RangeIndex(start=1, stop=10, step=1, name="foo")
    reversed_idx = idx[::-1]
    result = reversed_idx.difference(idx[-3:])
    print(f"RESULT={result!r}")
    print("EXPECTED=RangeIndex(start=1, stop=7, step=1, name='foo')")
    if list(result) != list(range(1, 7)):
        return 1, f"result order {list(result)} is not ascending 1..6"
    return 0, "result ascending as expected"


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
