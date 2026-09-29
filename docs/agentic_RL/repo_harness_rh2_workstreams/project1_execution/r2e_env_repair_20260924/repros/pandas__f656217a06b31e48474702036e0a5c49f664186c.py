"""公开复现：pandas f656217a —— merge 的后缀产生重复列名时没有 FutureWarning。

依据：公开题面示例代码，原样改写；用 warnings.catch_warnings(record=True) + simplefilter("always") 收集警告，
只认类别为 FutureWarning 且消息提到 duplicate 的警告。只观测，不写工作区。
"""
import sys
import traceback
import warnings


def main():
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    left = pd.DataFrame({"a": [1, 2, 3], "b": 1, "b_x": 2})
    right = pd.DataFrame({"a": [1, 2, 3], "b": 2})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = pd.merge(left, right, on="a")
    print(f"RESULT_COLUMNS={list(result.columns)}")
    for w in caught:
        print(f"WARNING={w.category.__name__}: {str(w.message)[:160]}")
    dup = [w for w in caught if issubclass(w.category, FutureWarning) and "duplicate" in str(w.message).lower()]
    if not dup:
        return 1, "no FutureWarning about duplicate columns from suffixes"
    return 0, "FutureWarning about duplicate columns emitted"


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
