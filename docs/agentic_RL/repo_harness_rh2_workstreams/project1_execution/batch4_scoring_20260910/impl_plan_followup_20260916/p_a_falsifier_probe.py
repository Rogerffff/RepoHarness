"""P-A 修订计划的窄 CPU 反证；生产实现尚未加入该 producer。

只在临时目录运行真实 pytest、py_compile 与无副作用的 compile() 对照。
资源部分仅检查计划中“否决新类别后回落旧评分”的组合，不触发真实 OOM。
所有结果写入本轮新证据文件，不读取 e1，也不改昨日证据或生产源码。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from repoharness2.envpack import scoring
from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1
from repoharness2.envpack.swegym_parsers import parse_log_pytest
from repoharness2.grading.manager import GradingInfraError, SWEGradingManager


OUTPUT = Path(__file__).with_name("p_a_falsifier_result.json")
EXPECTED = "tests/test_thing.py::test_answer"
VALID = "def answer():\n    return 42\n"
INVALID = "def answer(:\n    return 42\n"
TEST = "from src.thing import answer\n\ndef test_answer():\n    assert answer() == 42\n"


def main() -> None:
    env = {
        **os.environ,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    grading = SimpleNamespace(
        spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1,
        repo_key_lower="pandas-dev/pandas",
        instance_id="p-a-falsifier-20260916",
        fail_to_pass=[EXPECTED],
        pass_to_pass=[],
    )
    spec = SimpleNamespace(parse_log=lambda log: scoring.parse_eval_log_v2(grading, log))
    result: dict = {"python_version": sys.version.split()[0], "pytest_version": pytest.__version__}
    with tempfile.TemporaryDirectory(prefix="rh2-pa-falsifier-") as tmp:
        root = Path(tmp).resolve()
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src/__init__.py").write_text("")
        source = root / "src/thing.py"
        source.write_text(INVALID)
        (root / "tests/test_thing.py").write_text(TEST)

        def run(module: str, *args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, "-B", "-m", module, *args],
                cwd=root, env=env, capture_output=True, text=True, check=False,
            )

        pytest_cases = {}
        for name, extra in [("default", [])]:
            execution = run("pytest", "-q", "-rA", *extra, "tests/test_thing.py")
            log = execution.stdout + execution.stderr
            wrapped = ">>>>> Start Test Output\n" + log + "\n>>>>> End Test Output\n"
            verdict = SWEGradingManager._parse_eval_log(None, spec, wrapped)
            fields = scoring.grading_outcome_fields(verdict)
            excerpt = [
                line.replace(str(root), "/testbed")
                for line in log.splitlines()
                if any(token in line for token in ("ERROR collecting", "Interrupted:", 'File "', "SyntaxError"))
            ]
            has_candidate_file = any('File "/testbed/src/thing.py"' in line for line in excerpt)
            pytest_cases[name] = {
                "rc": execution.returncode,
                "parsed": parse_log_pytest(log),
                "num_parsed_tests": verdict.num_parsed_tests,
                "reference_missing": verdict.reference_missing,
                "candidate_file_in_traceback": has_candidate_file,
                "current_outcome_fields": fields,
                "excerpts": excerpt,
            }
            assert execution.returncode == 2
            assert verdict.num_parsed_tests == 1
            assert verdict.reference_missing == [EXPECTED]
            assert fields["failure_category"] == "tests_failed" and fields["reward"] == 0.0
            assert has_candidate_file
        result["pytest_cases"] = pytest_cases

        # 唯一追加变体：pytest 启动期加载候选 conftest 时的真实语法错误。
        source.write_text(VALID)
        conftest = root / "conftest.py"
        conftest.write_text("def pytest_configure(:\n    pass\n")
        startup = run("pytest", "-q", "-rA", "tests/test_thing.py")
        startup_log = startup.stdout + startup.stderr
        startup_wrapped = ">>>>> Start Test Output\n" + startup_log + "\n>>>>> End Test Output\n"
        startup_parsed = parse_log_pytest(startup_log)
        syntax_check = run("py_compile", "conftest.py")
        assert startup.returncode == 4
        assert startup_parsed == {}
        assert syntax_check.returncode == 1 and "SyntaxError" in syntax_check.stderr
        try:
            SWEGradingManager._parse_eval_log(None, spec, startup_wrapped)
        except GradingInfraError as exc:
            startup_manager_result = {"exception": type(exc).__name__, "detail": str(exc)}
        else:
            raise AssertionError("启动期零解析目前必须进入已有 infra 路径")
        result["conftest_startup_syntax_error"] = {
            "rc": startup.returncode,
            "parsed": startup_parsed,
            "has_error_collecting_marker": "ERROR collecting" in startup_log,
            "py_compile_rc": syntax_check.returncode,
            "syntax_error_confirmed": True,
            "current_manager_result": startup_manager_result,
            "excerpts": [
                line.replace(str(root), "/testbed")
                for line in startup_log.splitlines()
                if "conftest.py" in line or "SyntaxError" in line
            ],
        }
        assert not result["conftest_startup_syntax_error"]["has_error_collecting_marker"]
        conftest.unlink()

        try:
            SWEGradingManager._parse_eval_log(
                None, spec, ">>>>> Start Test Output\nno summary\n>>>>> End Test Output\n"
            )
        except GradingInfraError as exc:
            result["zero_parsed"] = {"exception": type(exc).__name__, "detail": str(exc)}
        else:
            raise AssertionError("零解析必须继续进入已有 infra 路径")

        source.write_text(VALID)
        normal_compile = run("py_compile", "src/thing.py")
        pycache = root / "src/__pycache__"
        wrote_bytecode = any(pycache.glob("thing.*.pyc"))
        assert normal_compile.returncode == 0 and wrote_bytecode
        shutil.rmtree(pycache)
        pycache.write_text("ordinary file blocks bytecode directory")
        blocked_compile = run("py_compile", "src/thing.py")
        compile(source.read_bytes(), "src/thing.py", "exec")
        assert blocked_compile.returncode == 1
        assert "Not a directory" in blocked_compile.stderr
        assert "SyntaxError" not in blocked_compile.stderr

        # -m 在工作目录查找模块；该对照只执行本探针生成的无害文件。
        (root / "py_compile.py").write_text(
            "from pathlib import Path\n"
            "Path('local_module_executed').write_text('yes')\n"
            "raise SystemExit(1)\n"
        )
        shadow_compile = run("py_compile", "src/thing.py")
        assert shadow_compile.returncode == 1
        assert (root / "local_module_executed").read_text() == "yes"
        result["py_compile_counterexamples"] = {
            "valid_source_default_rc": normal_compile.returncode,
            "writes_pyc_even_with_B_and_dontwritebytecode": wrote_bytecode,
            "valid_source_blocked_cache_rc": blocked_compile.returncode,
            "blocked_cache_stderr": re.sub(r"\.pyc\.\d+", ".pyc.<temporary-id>", blocked_compile.stderr.strip()),
            "same_source_in_memory_compile": "passed",
            "local_module_shadow_rc": shadow_compile.returncode,
            "local_module_executed": True,
        }

        # 这是资源事实输入组合，并非真实 OOM 实验。只证明旧 fallback 仍给 0。
        fallback = pytest_cases["default"]["current_outcome_fields"]
        result["resource_veto_fallback"] = [
            {
                "resource_input": state,
                "new_category_allowed_by_plan": False,
                "unchanged_fallback_category": fallback["failure_category"],
                "unchanged_fallback_reward": fallback["reward"],
            }
            for state in ["oom_kill > 0 (assumed input)", "required resource read unavailable (assumed input)"]
        ]
        assert all(row["unchanged_fallback_reward"] == 0.0 for row in result["resource_veto_fallback"])

    repo = next(parent for parent in Path(__file__).resolve().parents if (parent / "rh2/src").is_dir())
    sources = [
        "rh2/src/repoharness2/grading/manager.py",
        "rh2/src/repoharness2/envpack/scoring.py",
        "rh2/src/repoharness2/envpack/swegym_parsers.py",
        "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/impl_plan_20260915.md",
    ]
    result["source_sha256"] = {path: hashlib.sha256((repo / path).read_bytes()).hexdigest() for path in sources}
    result["assertions"] = "passed"
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("P-A probe assertions passed; result written to " + OUTPUT.name)


if __name__ == "__main__":
    main()
