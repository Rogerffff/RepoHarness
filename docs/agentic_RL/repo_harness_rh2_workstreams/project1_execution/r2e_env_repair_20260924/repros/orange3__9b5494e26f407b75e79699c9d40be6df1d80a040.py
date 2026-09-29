"""公开复现：orange3 9b5494e2 —— LogisticRegressionLearner(penalty='l1') 在默认 solver（lbfgs）下报 ValueError。

依据：公开题面示例；题面里的 iris_data 用仓库自带数据集 Table("iris")（Orange/datasets/iris.tab，不需要网络）。
只观测，不写工作区。
"""
import sys
import traceback


def main():
    from Orange.classification import LogisticRegressionLearner
    from Orange.data import Table

    iris_data = Table("iris")
    learn = LogisticRegressionLearner(penalty="l1")
    try:
        model = learn(iris_data)
    except ValueError as exc:
        print(f"EXC=ValueError {exc}")
        if "l1" in str(exc):
            return 1, "ValueError: solver does not support penalty='l1'"
        return 0, "ValueError but message does not mention l1"
    print(f"MODEL={type(model).__name__}")
    return 0, "fit succeeded with penalty='l1'"


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
