"""公开复现：orange3 f237f968 —— OWSelectRows 在上下文部分匹配（缺变量）时把条件的算子参数变成 0。

依据：公开题面（两个条件 [sepal length, 2, ("5.2",)]、[petal length, 2, ("4.2",)]；数据只留 attributes[2:]；期望
conditions[0][1] == 2，实际 0）。题面里的 widget.set_context / send_data 不是真实 API，这里按公开工作区
Orange/widgets/data/tests/test_owselectrows.py 的 widget_with_context 辅助函数与 override_locale(QLocale.C) 改写。
需要 Qt：在 QT_QPA_PLATFORM=minimal + xvfb-run 下运行。
"""
import sys
import traceback
import unittest

OUT = {}


def build_case():
    from AnyQt.QtCore import QLocale
    from orangewidget.settings import VERSION_KEY
    from Orange.data import Domain, Table
    from Orange.widgets.data.owselectrows import OWSelectRows, SelectRowsContextHandler
    from Orange.widgets.tests.base import WidgetTest

    class Repro(WidgetTest):
        def test_partial_context(self):
            QLocale.setDefault(QLocale(QLocale.C))
            iris = Table("iris")
            domain = iris.domain
            ch = SelectRowsContextHandler()
            context = ch.new_context(domain, *ch.encode_domain(domain))
            context.values = {"conditions": [[domain[0].name, 2, ("5.2",)], [domain[2].name, 2, ("4.2",)]],
                              VERSION_KEY: OWSelectRows.settings_version}
            w = self.create_widget(OWSelectRows, dict(context_settings=[context]))
            iris2 = iris.transform(Domain(domain.attributes[2:], None))
            self.send_signal(w.Inputs.data, iris2, widget=w)
            OUT["conditions"] = [tuple(c) for c in w.conditions]
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
    if res.errors or res.failures or "conditions" not in OUT:
        print("REPRO_OBSERVED=0\nREPRO_REASON=script_error")
        sys.exit(3)
    conds = OUT["conditions"]
    print(f"CONDITIONS={conds!r}")
    observed = not conds or conds[0][1] != 2
    print(f"REPRO_OBSERVED={int(observed)}")
    print("REPRO_REASON=" + ("conditions[0][1] is not 2" if observed else "conditions[0][1] == 2"))
    sys.exit(0)
