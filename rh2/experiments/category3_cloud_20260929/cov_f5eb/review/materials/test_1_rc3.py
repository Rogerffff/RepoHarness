# coding: utf-8
# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""Test json-based summary reporting for coverage.py"""
from datetime import datetime
import json
import os

import coverage
from tests.coveragetest import UsingModulesMixin, CoverageTest


class JsonReportTest(UsingModulesMixin, CoverageTest):
    """Tests of the JSON reports from coverage.py."""
    def _assert_expected_json_report(self, cov, expected_result):
        """
        Helper for tests that handles the common ceremony so the tests can be clearly show the
        consequences of setting various arguments.
        """
        self.make_file("a.py", """\
            a = {'b': 1}
            if a.get('a'):
                b = 1
            """)
        a = self.start_import_stop(cov, "a")
        output_path = os.path.join(self.temp_dir, "a.json")
        cov.json_report(a, outfile=output_path)
        with open(output_path) as result_file:
            parsed_result = json.load(result_file)
        self.assert_recent_datetime(
            datetime.strptime(parsed_result['meta']['timestamp'], "%Y-%m-%dT%H:%M:%S.%f")
        )
        del (parsed_result['meta']['timestamp'])
        assert parsed_result == expected_result

    def test_branch_coverage(self):
        cov = coverage.Coverage(branch=True)
        expected_result = {
            'meta': {
                "version": coverage.__version__,
                "branch_coverage": True,
                "show_contexts": False,
            },
            'files': {
                'a.py': {
                    'executed_lines': [1, 2],
                    'missing_lines': [3],
                    'excluded_lines': [],
                    'summary': {
                        'missing_lines': 1,
                        'covered_lines': 2,
                        'num_statements': 3,
                        'num_branches': 2,
                        'excluded_lines': 0,
                        'num_partial_branches': 1,
                        'percent_covered': 60.0
                    }
                }
            },
            'totals': {
                'missing_lines': 1,
                'covered_lines': 2,
                'num_statements': 3,
                'num_branches': 2,
                'excluded_lines': 0,
                'num_partial_branches': 1,
                'percent_covered': 60.0,
                'covered_branches': 1,
                'missing_branches': 1
            }
        }
        self._assert_expected_json_report(cov, expected_result)

    def test_simple_line_coverage(self):
        cov = coverage.Coverage()
        expected_result = {
            'meta': {
                "version": coverage.__version__,
                "branch_coverage": False,
                "show_contexts": False,
            },
            'files': {
                'a.py': {
                    'executed_lines': [1, 2],
                    'missing_lines': [3],
                    'excluded_lines': [],
                    'summary': {
                        'excluded_lines': 0,
                        'missing_lines': 1,
                        'covered_lines': 2,
                        'num_statements': 3,
                        'percent_covered': 66.66666666666667
                    }
                }
            },
            'totals': {
                'excluded_lines': 0,
                'missing_lines': 1,
                'covered_lines': 2,
                'num_statements': 3,
                'percent_covered': 66.66666666666667
            }
        }
        self._assert_expected_json_report(cov, expected_result)

    def run_context_test(self, relative_files):
        """A helper for two tests below."""
        self.make_file("config", """\
            [run]
            relative_files = {}

            [json]
            show_contexts = True
            """.format(relative_files))
        cov = coverage.Coverage(context="cool_test", config_file="config")
        expected_result = {
            'meta': {
                "version": coverage.__version__,
                "branch_coverage": False,
                "show_contexts": True,
            },
            'files': {
                'a.py': {
                    'executed_lines': [1, 2],
                    'missing_lines': [3],
                    'excluded_lines': [],
                    "contexts": {
                        "1": [
                            "cool_test"
                        ],
                        "2": [
                            "cool_test"
                        ]
                    },
                    'summary': {
                        'excluded_lines': 0,
                        'missing_lines': 1,
                        'covered_lines': 2,
                        'num_statements': 3,
                        'percent_covered': 66.66666666666667
                    }
                }
            },
            'totals': {
                'excluded_lines': 0,
                'missing_lines': 1,
                'covered_lines': 2,
                'num_statements': 3,
                'percent_covered': 66.66666666666667
            }
        }
        self._assert_expected_json_report(cov, expected_result)

    def test_context_non_relative(self):
        self.run_context_test(relative_files=False)

    def test_context_relative(self):
        self.run_context_test(relative_files=True)

    # R2E revision (2026-09-29, R-c): the issue asks for totals that give
    # "detailed branch coverage information", so the counts are checked on a
    # program other than the issue's one-branch example.  In BRANCHY, f and g
    # take both branches of their `if`, and h never runs.
    BRANCHY = """\
        def f(x):
            if x:
                return 1
            return 2

        def g(x):
            if x:
                return 1
            return 2

        def h(x):
            if x:
                return 1
            return 2

        f(0)
        f(1)
        g(0)
        g(1)
        """

    def _branchy_report(self, modname, report_from_saved_data=False):
        """Measure BRANCHY with branch=True and return the parsed JSON report."""
        self.make_file(modname + ".py", self.BRANCHY)
        data_file = os.path.join(self.temp_dir, modname + ".coverage")
        cov = coverage.Coverage(branch=True, data_file=data_file)
        mod = self.start_import_stop(cov, modname)
        if report_from_saved_data:
            # Like `coverage run --branch` followed by a separate `coverage json`:
            # the reporting object's own config does not set branch.
            cov.save()
            cov = coverage.Coverage(data_file=data_file)
            cov.load()
        output_path = os.path.join(self.temp_dir, modname + ".json")
        cov.json_report(mod, outfile=output_path)
        with open(output_path) as result_file:
            return json.load(result_file)

    def test_branch_totals_count_branch_arcs(self):
        # 6 branch destinations (two per `if`), 4 taken, 2 never taken.  h's `if`
        # never runs, so it is not a partial branch.
        report = self._branchy_report("branchy")
        totals = report['totals']
        assert totals['num_branches'] == 6
        assert totals['num_partial_branches'] == 0
        assert totals['covered_branches'] == 4
        assert totals['missing_branches'] == 2

    def test_branch_totals_from_saved_branch_data(self):
        # R2E revision (2026-09-29, R-c): the report follows the measured data,
        # as the other reporters do, not the reporting object's own settings.
        report = self._branchy_report("branchy_saved", report_from_saved_data=True)
        assert report['meta']['branch_coverage'] is True
        assert report['totals']['covered_branches'] == 4
        assert report['totals']['missing_branches'] == 2

    def test_branch_totals_add_up_across_files(self):
        # R2E revision (2026-09-30, R-c): like the other totals keys, the two
        # counts add up every reported file.  branchy_sum.py is BRANCHY (6
        # branch destinations, 4 taken, 2 never taken); branchy_sum_main.py is
        # the issue's one-branch example after an import (2 destinations, 1
        # taken, 1 not taken, 1 partial branch line).
        self.make_file("branchy_sum.py", self.BRANCHY)
        self.make_file("branchy_sum_main.py", """\
            import branchy_sum
            a = {'b': 1}
            if a.get('a'):
                b = 1
            """)
        cov = coverage.Coverage(branch=True)
        main = self.start_import_stop(cov, "branchy_sum_main")
        output_path = os.path.join(self.temp_dir, "branchy_sum.json")
        cov.json_report([main, main.branchy_sum], outfile=output_path)
        with open(output_path) as result_file:
            report = json.load(result_file)
        assert sorted(report['files']) == ['branchy_sum.py', 'branchy_sum_main.py']
        totals = report['totals']
        assert totals['num_branches'] == 8
        assert totals['num_partial_branches'] == 1
        assert totals['covered_branches'] == 5
        assert totals['missing_branches'] == 3

    def test_branch_totals_without_branches(self):
        # Reviewer draft (2026-09-30, R-c): with branch coverage enabled, the two
        # counts belong in totals even when the reported code has no branch at
        # all, just as num_branches does (0 here).
        self.make_file("straight.py", """\
            a = 1
            b = a + 1
            """)
        cov = coverage.Coverage(branch=True)
        mod = self.start_import_stop(cov, "straight")
        output_path = os.path.join(self.temp_dir, "straight.json")
        cov.json_report(mod, outfile=output_path)
        with open(output_path) as result_file:
            report = json.load(result_file)
        assert report['meta']['branch_coverage'] is True
        totals = report['totals']
        assert totals['num_branches'] == 0
        assert totals['covered_branches'] == 0
        assert totals['missing_branches'] == 0
