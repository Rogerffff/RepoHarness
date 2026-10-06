# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/nedbat/coveragepy/blob/master/NOTICE.txt

"""R2E revision tests (2026-09-29) for the .gitignore in the HTML report directory.

HtmlGitignoreTest: the generated .gitignore really makes git ignore the report files.
ReportingTest.test_no_data_to_report_on_html: copied unchanged from the public
tests/test_coverage.py (no data: a nice message, and no output directory).
"""

import os
import subprocess

import pytest

import coverage
from coverage.exceptions import CoverageException

from tests.coveragetest import CoverageTest


def run_git(*args):
    """Run git in the current directory, isolated from user and system config."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["HOME"] = os.getcwd()
    for name in ("XDG_CONFIG_HOME", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    return subprocess.run(
        ["git"] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env,
    )


class HtmlGitignoreTest(CoverageTest):
    """The .gitignore in the HTML output directory makes git ignore the report."""

    def test_html_report_is_ignored_by_git(self):
        init = run_git("init", "-q", ".")
        assert init.returncode == 0, init.stderr
        self.make_file("main_file.py", """\
            import helper1
            helper1.func1(12)
            """)
        self.make_file("helper1.py", """\
            def func1(x):
                if x % 2:
                    print("odd")
            """)
        cov = coverage.Coverage()
        self.start_import_stop(cov, "main_file")
        cov.html_report(directory="report_out")

        report_files = [f for f in os.listdir("report_out") if f != ".gitignore"]
        assert "index.html" in report_files
        status = run_git("status", "--porcelain", "--untracked-files=all", "--", "report_out")
        assert status.returncode == 0, status.stderr
        not_ignored = sorted(
            line[3:] for line in status.stdout.splitlines()
            if line[3:] != "report_out/.gitignore"
        )
        assert not_ignored == []


    def test_existing_gitignore_is_preserved_and_report_ignored(self):
        # 接续当前清单：保留用户内容，同时用真实 git 核对新报告。
        init = run_git("init", "-q", ".")
        assert init.returncode == 0, init.stderr
        self.make_file("main_file.py", "a = 1\n")
        os.makedirs("report_out")
        prior = b"# User-owned rules\ncustom.tmp\n"
        path = os.path.join("report_out", ".gitignore")
        with open(path, "wb") as stream:
            stream.write(prior)
        cov = coverage.Coverage()
        self.start_import_stop(cov, "main_file")
        for _ in range(2):
            cov.html_report(directory="report_out")
            with open(path, "rb") as stream:
                assert prior in stream.read(), "Existing user .gitignore content was lost"
            assert os.path.exists(os.path.join("report_out", "index.html"))
            status = run_git("status", "--porcelain", "--untracked-files=all", "--", "report_out")
            assert status.returncode == 0, status.stderr
            not_ignored = sorted(
                line[3:] for line in status.stdout.splitlines()
                if line[3:] != "report_out/.gitignore"
            )
            assert not_ignored == [], status.stdout



class ReportingTest(CoverageTest):
    """Tests of some reporting behavior."""

    def test_no_data_to_report_on_html(self):
        # Reporting with no data produces a nice message and no output
        # directory.
        with pytest.raises(CoverageException, match="No data to report."):
            self.command_line("html -d htmlcov")
        self.assert_doesnt_exist("htmlcov")
