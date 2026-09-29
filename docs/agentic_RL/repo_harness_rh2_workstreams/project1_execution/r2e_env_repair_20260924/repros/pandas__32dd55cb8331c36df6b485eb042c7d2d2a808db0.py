"""公开复现：pandas 32dd55cb —— 含 Int64 扩展数组列的 DataFrame 调 mean(numeric_only=True) 报 'dtype' 参数不支持。

依据：公开题面示例代码；列 A 的随机整数改用固定种子（结果与题面无关，只为可重复）。只观测，不写工作区。
"""
import sys
import traceback


def main():
    import numpy as np
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    df = pd.DataFrame({
        "A": np.random.RandomState(0).randint(0, 100, size=10),
        "B": pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype="Int64"),
    })
    try:
        result = df.mean(numeric_only=True)
    except Exception as exc:  # 题面没给异常类型，只给消息内容
        print(f"EXC={type(exc).__name__} {exc}")
        if "dtype" in str(exc):
            return 1, "reduction raised about unsupported 'dtype' parameter"
        return 0, "reduction raised a different error"
    print("RESULT=" + result.to_string().replace("\n", " | "))
    return 0, "mean(numeric_only=True) succeeded"


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
