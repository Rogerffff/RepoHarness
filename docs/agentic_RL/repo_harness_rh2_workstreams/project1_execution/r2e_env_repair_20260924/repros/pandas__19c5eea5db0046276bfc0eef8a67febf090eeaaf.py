"""公开复现：pandas 19c5eea5 —— 空 DataFrame（带 dtype 的列）用 df.loc[:, "x"] = [1, 2, 3] 赋值时 ValueError。

依据：公开题面示例代码，原样改写。只观测，不写工作区。
"""
import sys
import traceback


def main():
    import numpy as np
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    data = [1, 2, 3]
    df = pd.DataFrame(columns=["x", "y"])
    df["x"] = df["x"].astype(np.int64)
    try:
        df.loc[:, "x"] = data
    except ValueError as exc:
        print(f"EXC=ValueError {exc}")
        if "Must have equal len keys and value" in str(exc):
            return 1, "ValueError as described"
        return 0, "ValueError with a different message"
    print(f"RESULT_SHAPE={df.shape} X={df['x'].tolist()} Y={df['y'].tolist()}")
    return 0, "assignment expanded the frame"


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
