"""公开复现：orange3 c3fb72ba —— OWLinearProjection 的 VizRank 把 n_attrs 设为 4 后，用存下的设置重建 widget 仍是 3。

依据：公开题面示例（setValue(4) → settingsHandler.pack_data → create_widget(stored_settings) → send_signal → 读 n_attrs_spin）。
测试夹具照公开工作区的 Orange/widgets/visualize/tests/test_owlinearprojection.py（WidgetTest，数据 Table("iris")，
先送数据再设 spin——spin 的上限随数据里的连续变量数设定）。先后说明：写本脚本前已读过该题 facts.json（含目标键名与
gold 触碰的文件路径，不含 diff）。需要 Qt：在 QT_QPA_PLATFORM=minimal + xvfb-run 下运行。
"""
import sys
import traceback
import unittest

OUT = {}


def build_case():
    from Orange.data import Table
    from Orange.widgets.tests.base import WidgetTest
    from Orange.widgets.visualize.owlinearprojection import OWLinearProjection

    class Repro(WidgetTest):
        def test_n_attrs_persist(self):
            data = Table("iris")
            w1 = self.create_widget(OWLinearProjection)
            self.send_signal(w1.Inputs.data, data, widget=w1)
            w1.vizrank.n_attrs_spin.setValue(4)
            settings = w1.settingsHandler.pack_data(w1)
            w2 = self.create_widget(OWLinearProjection, stored_settings=settings)
            self.send_signal(w2.Inputs.data, data, widget=w2)
            OUT["before"] = w1.vizrank.n_attrs_spin.value()
            OUT["after"] = w2.vizrank.n_attrs_spin.value()
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
    if res.errors or res.failures or "after" not in OUT:
        print("REPRO_OBSERVED=0\nREPRO_REASON=script_error")
        sys.exit(3)
    print(f"N_ATTRS_SET={OUT['before']} N_ATTRS_AFTER_RELOAD={OUT['after']}")
    if OUT["before"] != 4:
        print("REPRO_OBSERVED=0\nREPRO_REASON=could not set n_attrs to 4 on the first widget")
        sys.exit(0)
    observed = OUT["after"] != 4
    print(f"REPRO_OBSERVED={int(observed)}")
    print("REPRO_REASON=" + (f"reloaded n_attrs_spin is {OUT['after']}, not 4" if observed else "value persisted"))
    sys.exit(0)
