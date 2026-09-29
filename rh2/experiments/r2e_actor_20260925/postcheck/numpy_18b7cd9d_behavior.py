"""numpy 18b7cd9d 的事后复核（在应用了候选补丁的 /testbed 里、用 /testbed/.venv 的 python 运行）。

题面要求：poly1d 与非 poly1d 对象比较时不抛异常，`==` 得到 False（`__eq__` 返回 False 或 NotImplemented 都可以），
poly1d 之间仍按系数比较。隐藏测试只比较了 None 与同一对象，所以"只特判 None"、"退回对象身份比较"这类错误实现
也能得 1（2026-09-25 真实评分已证实）。本脚本逐项检查，每项单独 try/except，一个异常不会让后面的项跳过；
不要求照 gold 返回 NotImplemented。输出一行 JSON：各项结果与总判定。
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    sys.path.insert(0, "/testbed")
    from numpy import poly1d as P

    p = P([1, 2, 3])
    items = [
        # (名称, 表达式, 期望值)
        ("eq_none", lambda: p == None, False),  # noqa: E711
        ("ne_none", lambda: p != None, True),  # noqa: E711
        ("none_eq", lambda: None == p, False),  # noqa: E711
        ("eq_object", lambda: p == object(), False),
        ("ne_object", lambda: p != object(), True),
        ("eq_scalar", lambda: p == 3, False),
        ("eq_list_same_coeffs", lambda: p == [1, 2, 3], False),
        ("eq_equal_value_other_object", lambda: p == P([1, 2, 3]), True),
        ("ne_equal_value_other_object", lambda: p != P([1, 2, 3]), False),
        ("eq_same_len_other_value", lambda: p == P([3, 4, 5]), False),
        ("eq_different_len", lambda: p == P([1, 2]), False),
        ("ne_different_len", lambda: p != P([1, 2]), True),
    ]
    results = []
    for name, fn, want in items:
        try:
            got = fn()
            ok = (got is want) or (type(got).__name__ in ("bool_", "bool") and bool(got) is want)
            results.append({"item": name, "ok": ok, "got": repr(got), "want": want})
        except Exception as exc:  # noqa: BLE001 — 逐项记录异常，不中断
            results.append({"item": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"[:160], "want": want})
    failed = [r["item"] for r in results if not r["ok"]]
    print("RH2_POSTCHECK=" + json.dumps({"task": "numpy__18b7cd9d", "verdict": "pass" if not failed else "fail",
                                         "failed": failed, "items": results}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
