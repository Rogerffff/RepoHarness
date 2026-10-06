"""公开复现：orange3 22e98f8f —— unique_in_order_mapping([2, 3, 1]) 返回的映射不对。

依据：公开题面（函数名、输入 [2, 3, 1]、期望 mapping [0, 1, 2]、实际 [2, 0, 1]）。
函数位置由公开工作区源码 grep 函数名得到：Orange/widgets/data/owcreateclass.py。
注意：题面里标为 "Example Buggy Code" 的函数体按字面执行得到的正是期望值 [0, 1, 2]，
与仓库实现（np.unique + argsort）不同；本脚本只调用仓库实现，不执行题面那段代码。
只观测，不写工作区。
"""
import sys
import traceback


def main():
    from Orange.widgets.data.owcreateclass import unique_in_order_mapping

    u, m = unique_in_order_mapping([2, 3, 1])
    u, m = [int(x) for x in u], [int(x) for x in m]
    print(f"UNIQUE={u} MAPPING={m} EXPECTED_MAPPING=[0, 1, 2]")
    if m != [0, 1, 2]:
        return 1, f"mapping {m} != [0, 1, 2] (issue says actual [2, 0, 1])"
    return 0, "mapping already [0, 1, 2]"


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
