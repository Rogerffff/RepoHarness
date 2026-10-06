"""第四组 P-A 计划的窄 CPU 探针：collection 错误不等于零解析。

从仓库根运行：
  rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/impl_plan_review_20260915/training_semantics_probe.py

只在临时目录运行 pytest，并写同目录 JSON 证据；不运行 Docker、模型或 GPU。
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "rh2/src").is_dir())
sys.path.insert(0, str(REPO_ROOT / "rh2/src"))

from repoharness2.envpack import scoring  # noqa: E402
from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1  # noqa: E402
from repoharness2.envpack.swegym_parsers import parse_log_pytest  # noqa: E402
from repoharness2.grading.manager import SWEGradingManager  # noqa: E402


BASELINE_SOURCE = "def answer():\n    return 42\n"
CANDIDATE_SOURCE = "def answer(:\n    return 42\n"
TEST_SOURCE = (
    "from pathlib import Path\n"
    "from src.thing import answer\n\n"
    "def test_answer():\n"
    "    Path('test_body_executed').write_text('yes')\n"
    "    assert answer() == 42\n"
)
EXPECTED_CASE = "tests/test_thing.py::test_answer"


def main() -> None:
    command = [sys.executable, "-m", "pytest", "-q", "-rA", "tests/test_thing.py"]
    environment = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    with tempfile.TemporaryDirectory(prefix="rh2-batch4-training-semantics-", dir="/tmp") as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src/__init__.py").write_text("")
        (root / "tests/test_thing.py").write_text(TEST_SOURCE)
        (root / "src/thing.py").write_text(BASELINE_SOURCE)
        baseline = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, check=False)
        baseline_body_executed = (root / "test_body_executed").exists()
        (root / "test_body_executed").unlink(missing_ok=True)
        (root / "src/thing.py").write_text(CANDIDATE_SOURCE)
        candidate = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, check=False)
        candidate_body_executed = (root / "test_body_executed").exists()

    grading = SimpleNamespace(
        spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1,
        repo_key_lower="pandas-dev/pandas",
        instance_id="cpu-training-semantics-plan-review",
        fail_to_pass=[EXPECTED_CASE],
        pass_to_pass=[],
    )
    log = ">>>>> Start Test Output\n" + candidate.stdout + candidate.stderr + "\n>>>>> End Test Output\n"
    spec = SimpleNamespace(parse_log=lambda text: scoring.parse_eval_log_v2(grading, text))
    # 调用当前 manager 的纯解析方法；本方法不使用 self，不构造 Docker 客户端。
    verdict = SWEGradingManager._parse_eval_log(None, spec, log)
    status_map = parse_log_pytest(candidate.stdout + candidate.stderr)
    # 原始 traceback 含本机解释器路径：完整日志进 git 忽略的 runs；提交证据仅替换路径前缀。
    raw_root = REPO_ROOT / "runs/impl_plan_review_20260915/raw_logs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    raw_root.mkdir(parents=True)
    raw_logs = {
        "baseline.stdout": baseline.stdout,
        "baseline.stderr": baseline.stderr,
        "candidate.stdout": candidate.stdout,
        "candidate.stderr": candidate.stderr,
        "wrapped_parser_input.log": log,
    }
    for name, content in raw_logs.items():
        (raw_root / name).write_text(content)

    def portable_log(text: str) -> str:
        return text.replace(str(REPO_ROOT), "<repo>").replace(str(Path.home()), "<user-home>")

    source_paths = (
        "rh2/src/repoharness2/envpack/swegym_parsers.py",
        "rh2/src/repoharness2/envpack/scoring.py",
        "rh2/src/repoharness2/grading/manager.py",
    )
    result = {
        "scope": "计划覆盖反例；当前 binary 0 可成立，参考集合缺席计数不等于逐项执行失败。",
        "command": ["<rh2-venv-python>", *command[1:]],
        "environment_override": {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        "sources": {
            "src/__init__.py": "",
            "src/thing.py.baseline": BASELINE_SOURCE,
            "src/thing.py.candidate": CANDIDATE_SOURCE,
            "tests/test_thing.py": TEST_SOURCE,
        },
        "baseline": {"exit_code": baseline.returncode, "test_body_executed": baseline_body_executed, "stdout": portable_log(baseline.stdout), "stderr": portable_log(baseline.stderr)},
        "candidate": {"exit_code": candidate.returncode, "test_body_executed": candidate_body_executed, "stdout": portable_log(candidate.stdout), "stderr": portable_log(candidate.stderr)},
        "wrapped_parser_input": portable_log(log),
        "log_path_redactions": ["repository absolute prefix -> <repo>", "user home prefix -> <user-home>"],
        "raw_log_refs": {name: str((raw_root / name).relative_to(REPO_ROOT)) for name in raw_logs},
        "parser_inputs": {"repo_key_lower": grading.repo_key_lower, "fail_to_pass": grading.fail_to_pass, "pass_to_pass": grading.pass_to_pass},
        "parsed_status_map": status_map,
        "expected_case_has_observed_status": EXPECTED_CASE in status_map,
        "num_parsed_tests": verdict.num_parsed_tests,
        "reference_missing": verdict.reference_missing,
        "planned_zero_parse_branch_would_run": verdict.num_parsed_tests == 0,
        "current_grading_fields": scoring.grading_outcome_fields(verdict),
        "current_source_sha256": {path: hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() for path in source_paths},
        "current_functions": {
            "parse_log_pytest": inspect.getsource(parse_log_pytest),
            "parse_eval_log_v2": inspect.getsource(scoring.parse_eval_log_v2),
            "SWEGradingManager._parse_eval_log": inspect.getsource(SWEGradingManager._parse_eval_log),
            "grading_outcome_fields": inspect.getsource(scoring.grading_outcome_fields),
        },
    }
    assert baseline.returncode == 0 and baseline_body_executed
    assert candidate.returncode == 2 and not candidate_body_executed
    assert status_map == {"tests/test_thing.py": "ERROR"}
    assert verdict.num_parsed_tests == 1 and EXPECTED_CASE in verdict.reference_missing
    output = Path(__file__).with_name("training_semantics_probe_result.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("num_parsed_tests", "expected_case_has_observed_status", "planned_zero_parse_branch_would_run", "current_grading_fields")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
