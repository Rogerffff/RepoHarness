"""验证只把 stdout 换成 JUnit XML，是否能摆脱同进程 hook 对结果的影响。"""
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/pyproject.toml").is_file())


def main():
    with tempfile.TemporaryDirectory(prefix="rh2_junit_review_") as raw:
        p = Path(raw)
        (p / "test_answer.py").write_text("def test_answer():\n    assert 1 == 2\n")
        rows = []
        for name, hook in (
            ("baseline", ""),
            ("same_process_report_hook", "import pytest\n@pytest.hookimpl(hookwrapper=True, tryfirst=True)\ndef pytest_runtest_makereport(item, call):\n    outcome = yield\n    report = outcome.get_result()\n    report.outcome = 'passed'\n    report.longrepr = None\n"),
        ):
            (p / "conftest.py").write_text(hook)
            r = subprocess.run([str(ROOT / "rh2/.venv/bin/python"), "-m", "pytest", "test_answer.py", "-q", "--junitxml=result.xml"], cwd=p, text=True, capture_output=True)
            tree = ET.parse(p / "result.xml")
            suites = [dict(x.attrib) for x in tree.iter("testsuite")]
            for suite in suites:
                suite.pop("hostname", None)
            rows.append({"name": name, "exit_code": r.returncode, "testsuites": suites,
                         "assertion_source_unchanged": (p / "test_answer.py").read_text() == "def test_answer():\n    assert 1 == 2\n"})
    result = {"scope": "真实本机 pytest 与官方 JUnit XML plugin；未模拟 root 文件权限、未运行 RH2 或容器；仅验证改变输出格式不能建立进程内信任隔离", "rows": rows}
    (HERE / "junit_channel_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
