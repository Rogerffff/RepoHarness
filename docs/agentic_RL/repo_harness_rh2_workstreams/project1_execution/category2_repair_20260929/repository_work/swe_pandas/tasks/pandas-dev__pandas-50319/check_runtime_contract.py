"""CPU 私有对照：真实 checkout 的日期契约和上层回退，禁止交给 solver。"""

import argparse
from datetime import datetime
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", default="/testbed")
    args = parser.parse_args()
    import pandas as pd
    from pandas._libs.tslibs import parsing

    checkout = Path(args.checkout).resolve()
    # 题目镜像使用 Python 3.8；不用 3.9 才加入的 Path.is_relative_to。
    for imported_file in (pd.__file__, parsing.__file__):
        try:
            Path(imported_file).resolve().relative_to(checkout)
        except ValueError:
            raise AssertionError("导入不来自目标 checkout: " + imported_file)
    strings = ["27.03.2003 14:55:00.000", "28.04.2004 16:07:08.123456"]
    expected = [datetime(2003, 3, 27, 14, 55), datetime(2004, 4, 28, 16, 7, 8, 123456)]
    guesses = []
    for string, value in zip(strings, expected):
        result = parsing.guess_datetime_format(string)
        if result is not None:
            assert isinstance(result, str)
            assert datetime.strptime(string, result) == value
        guesses.append(result)
    result = pd.to_datetime(strings, dayfirst=True)
    assert list(result.to_pydatetime()) == expected
    print(json.dumps({"pandas": pd.__file__, "parsing": parsing.__file__,
                      "version": pd.__version__, "guesses": guesses,
                      "array": [value.isoformat() for value in result.to_pydatetime()]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
