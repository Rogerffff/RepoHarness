#!/bin/bash
cd /testbed || exit 2
cat > /tmp/test_r2e_owcolor_priv.py <<'PY'
import json
from unittest.mock import patch

from Orange.data import Table
from Orange.widgets.data import owcolor
from Orange.widgets.tests import base as wbase

EXAMPLE = {"categorical": {"foo": {"renamed_values": {}},
                           "bar": {"renamed_values": {}}},
           "numeric": {}}


def texts(mock):
    return [" | ".join(str(a) for a in list(c[0][1:]) + list(c[1].values()))
            for c in mock.call_args_list]


class TestPrivUnused(wbase.WidgetTest):
    def setUp(self):
        self.widget = self.create_widget(owcolor.OWColor)

    def _parse(self, js):
        with patch.object(owcolor.QMessageBox, "warning") as warn, \
                patch.object(owcolor.QMessageBox, "critical") as crit:
            self.widget._parse_var_defs(js)
        return texts(warn), texts(crit)

    def test_priv_a_example_with_data(self):
        # statement example while iris is loaded: foo/bar are not in the data
        self.send_signal(self.widget.Inputs.data, Table("iris"))
        warns, crits = self._parse(json.loads(json.dumps(EXAMPLE)))
        print("A warning calls:", warns, "| critical:", crits)
        self.assertEqual(crits, [])
        self.assertTrue(any("foo" in t and "bar" in t for t in warns), warns)

    def test_priv_b_mixed_with_data(self):
        # used definition (iris -> species) plus unused foo (categorical)
        # and unused bar (numeric)
        self.send_signal(self.widget.Inputs.data, Table("iris"))
        js = {"categorical": {"iris": {"rename": "species"},
                              "foo": {"renamed_values": {}}},
              "numeric": {"bar": {"colors": "linear_viridis"}}}
        warns, crits = self._parse(js)
        print("B warning calls:", warns, "| critical:", crits)
        self.assertEqual(crits, [])
        joined = "\n".join(warns)
        self.assertIn("foo", joined)
        self.assertIn("bar", joined)
        out = self.get_output(self.widget.Outputs.data)
        self.assertEqual(out.domain.class_var.name, "species")

    def test_priv_c_numeric_only_no_data(self):
        warns, crits = self._parse({"categorical": {}, "numeric": {"foo": {}}})
        print("C warning calls:", warns, "| critical:", crits)
        self.assertEqual(crits, [])
        self.assertIn("foo", "\n".join(warns))

    def test_priv_d_all_used_no_warning(self):
        # regression guard: every definition matches the data -> no dialog
        self.send_signal(self.widget.Inputs.data, Table("iris"))
        warns, crits = self._parse(
            {"categorical": {"iris": {"rename": "species"}},
             "numeric": {"petal length": {"colors": "linear_viridis"}}})
        print("D warning calls:", warns, "| critical:", crits)
        self.assertEqual(warns, [])
        self.assertEqual(crits, [])
PY
QT_QPA_PLATFORM=minimal xvfb-run --auto-servernum python -m pytest -p no:cacheprovider -q -rA -k test_priv /tmp/test_r2e_owcolor_priv.py

echo RH2_CMD_RC=$?
