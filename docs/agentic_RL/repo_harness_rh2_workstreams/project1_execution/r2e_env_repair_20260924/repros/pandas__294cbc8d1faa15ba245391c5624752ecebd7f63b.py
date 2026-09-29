"""公开复现：pandas 294cbc8d —— 整数列标签的 DataFrame 调 .info(null_counts=True) 时 KeyError: 0。

依据：公开题面示例代码，原样改写（StringIO 缓冲，不写文件）。只观测，不写工作区。
"""
import sys
import traceback
from io import StringIO


def main():
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    df = pd.DataFrame({1: [1, 2], 2: [2, 3]}, index=["A", "B"])
    buf = StringIO()
    try:
        df.info(null_counts=True, buf=buf)
    except KeyError as exc:
        print(f"EXC=KeyError {exc!r}")
        return 1, "KeyError from .info() with integer column labels"
    print("INFO_OUTPUT=" + buf.getvalue().replace("\n", " | "))
    return 0, ".info() succeeded"


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
