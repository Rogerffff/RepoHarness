"""导入边界回归测试。"""

from __future__ import annotations

import subprocess
import sys


def _run_clean_import(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )


def test_tools_and_scaffolds_import_in_clean_process() -> None:
    result = _run_clean_import(
        "import repo_harness.tools\n"
        "import repo_harness.scaffolds\n"
    )

    assert result.returncode == 0, result.stderr


def test_context_builder_remains_importable_after_tools_in_clean_process() -> None:
    result = _run_clean_import(
        "import repo_harness.tools\n"
        "from repo_harness.context import ContextBuilder\n"
        "assert ContextBuilder.__name__ == 'ContextBuilder'\n"
    )

    assert result.returncode == 0, result.stderr
