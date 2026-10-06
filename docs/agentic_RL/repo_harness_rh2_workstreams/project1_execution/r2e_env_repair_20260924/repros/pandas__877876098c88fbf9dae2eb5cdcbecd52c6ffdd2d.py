"""公开复现：pandas 87787609 —— 两个层名相同但顺序不同的 MultiIndex 做 join 时 RecursionError。

依据：公开题面示例代码。偏离：题面里 right 的 'y' 只有 3 个值、索引有 4 行，按字面在构造 DataFrame 时就报长度不符
（本脚本先按字面试一次并打印结果），然后补成 4 个值再做 join。只观测，不写工作区。
"""
import sys
import traceback


def main():
    import pandas as pd

    print(f"PANDAS={pd.__version__} FILE={pd.__file__}")
    midx1 = pd.MultiIndex.from_product([[1, 2], [3, 4]], names=["a", "b"])
    midx2 = pd.MultiIndex.from_product([[1, 2], [3, 4]], names=["b", "a"])
    left = pd.DataFrame(index=midx1, data={"x": [10, 20, 30, 40]})
    try:
        pd.DataFrame(index=midx2, data={"y": ["foo", "bar", "fing"]})
        print("LITERAL_RIGHT=constructed")
    except ValueError as exc:
        print(f"LITERAL_RIGHT=ValueError {exc}")
    right = pd.DataFrame(index=midx2, data={"y": ["foo", "bar", "fing", "baz"]})
    try:
        result = left.join(right)
    except RecursionError as exc:
        print(f"EXC=RecursionError {str(exc)[:120]}")
        return 1, "RecursionError on join of MultiIndexes with swapped level order"
    print("RESULT=" + result.to_string().replace("\n", " | "))
    return 0, "join succeeded"


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
