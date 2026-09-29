"""公开复现：orange3 50f6a758 —— OWColor._parse_var_defs 遇到数据里没有的变量（foo、bar）时不给警告。

依据：公开题面（_parse_var_defs 的输入；期望出现提到 'foo' 与 'bar' 的警告）。方法所在类由公开工作区 grep 得到
（Orange/widgets/data/owcolor.py）；widget 构造方式照公开的 Orange/widgets/data/tests/test_owcolor.py（WidgetTest + iris，
patch QMessageBox.warning）。题面说的 TypeError（'NoneType' object is not subscriptable）是测试对"未被调用的 mock"
取 call_args[0] 时产生的，这里直接看 warning 是否被调用及其文本。需要 Qt：在 QT_QPA_PLATFORM=minimal + xvfb-run 下运行。
"""
import sys
import traceback
import unittest
from unittest.mock import patch

OUT = {}


def build_case():
    from Orange.data import Table
    from Orange.widgets.data import owcolor
    from Orange.widgets.tests.base import WidgetTest

    class Repro(WidgetTest):
        def test_unused_vars(self):
            w = self.create_widget(owcolor.OWColor)
            self.send_signal(w.Inputs.data, Table("iris"), widget=w)
            with patch("Orange.widgets.data.owcolor.QMessageBox.warning") as warn:
                w._parse_var_defs({"categorical": {"foo": {"renamed_values": {}},
                                                   "bar": {"renamed_values": {}}},
                                   "numeric": {}})
            OUT["called"], OUT["args"] = warn.called, warn.call_args
    return Repro


if __name__ == "__main__":
    try:
        case = build_case()
    except Exception:
        traceback.print_exc()
        print("REPRO_OBSERVED=0\nREPRO_REASON=import_failed")
        sys.exit(3)
    res = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(case))
    if res.errors or res.failures or "called" not in OUT:
        print("REPRO_OBSERVED=0\nREPRO_REASON=script_error")
        sys.exit(3)
    print(f"WARNING_CALLED={OUT['called']} CALL_ARGS={OUT['args']!r}")
    text = str(OUT["args"][0][2]) if OUT["called"] else ""
    observed = not ("foo" in text and "bar" in text)
    print(f"REPRO_OBSERVED={int(observed)}")
    print("REPRO_REASON=" + ("no warning naming unused 'foo'/'bar'" if observed else "warning names foo and bar"))
    sys.exit(0)
