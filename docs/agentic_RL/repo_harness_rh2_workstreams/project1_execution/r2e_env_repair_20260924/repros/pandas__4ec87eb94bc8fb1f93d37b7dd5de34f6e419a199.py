"""公开复现：pandas 4ec87eb9 —— Float64 列含 pd.NA 时 GroupBy.quantile 报 TypeError（NAType）。

依据：公开题面示例代码，原样改写。只观测，不写工作区。
"""
import sys
import traceback


def main():
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    df = pd.DataFrame({"group": [1, 1], "values": [2.5, pd.NA]}, dtype="Float64")
    try:
        result = df.groupby("group")["values"].quantile(0.5)
    except TypeError as exc:
        print(f"EXC=TypeError {exc}")
        if "NAType" in str(exc):
            return 1, "TypeError on pd.NA as described"
        return 0, "TypeError with a different message"
    print("RESULT=" + result.to_string().replace("\n", " | "))
    return 0, "quantile succeeded"


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
