"""两次 exec 设计的极小 Bash/真实 renderer/parser 探针；不执行任务或 Docker。

仓库根运行：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rh2/src rh2/.venv/bin/python <本文件>
真实任务测试命令替换为确定性 PASSED 文本，仅验证标记运输和 manager 解析入口。
"""

from __future__ import annotations

import json
import shlex
import subprocess
import tempfile
from pathlib import Path

from repoharness2.adapters.slime.prepared_task_face import (
    build_grading_spec_from_host_view,
)
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import derive_test_command_for_bundle
from repoharness2.envpack.training_view import HostGradingView
from repoharness2.grading.manager import GradingInfraError, SWEGradingManager

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]


def run_bash(script: str, state: Path) -> subprocess.CompletedProcess:
    # 不把宿主凭据或其它环境导出到状态文件。
    return subprocess.run(
        ["/bin/bash", "-c", script, "probe", str(state)],
        env={"PATH": "/usr/bin:/bin", "HOME": str(state)},
        cwd=state,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=5,
    )


def main() -> None:
    path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl"
    row = next(json.loads(line) for line in path.read_text().splitlines() if '"getmoto__moto-6913"' in line)
    grading = PrivateGradingBundleV2(**{key: value for key, value in row.items() if key != "schema_id"})
    view = HostGradingView(
        task_id=f"swe_gym_lite::{grading.instance_id}",
        source="swe_gym_lite",
        instance_id=grading.instance_id,
        environment_package_digest="sha256:" + "0" * 64,
        grading_bundle_digest=grading.digest(),
        grading=grading,
    )
    spec = build_grading_spec_from_host_view(view, image="unused:probe", image_manifest_digest="sha256:" + "1" * 64)
    lines = spec.candidate_test_script.splitlines()
    start = lines.index('echo "RH2_TS_TEST_START=$(date +%s.%N)"')
    tail = "\n".join(lines[start:]) + "\n"
    official = derive_test_command_for_bundle(grading)
    payload = "\n".join(f"PASSED {name}" for name in [*grading.fail_to_pass, *grading.pass_to_pass]) + "\n"
    assert tail.count(official) == 1
    tail = tail.replace(official, "printf %s " + shlex.quote(payload))
    install = """set -xo pipefail
export OMP_NUM_THREADS=1
export PATH="/opt/probe/bin:$PATH"
carry_func() { echo "func-$OMP_NUM_THREADS"; }
export -p > "$1/env.sh"
declare -f > "$1/funcs.sh"
pwd > "$1/cwd"
echo RH2_PHASE_HANDOFF=1
"""
    restore = """. "$1/env.sh"
. "$1/funcs.sh"
cd "$(cat "$1/cwd")"
echo "CARRIED_OMP=$OMP_NUM_THREADS FUNC=$(carry_func)"
"""
    manager = SWEGradingManager()
    cases = {}
    with tempfile.TemporaryDirectory(prefix="falsifier_carry_", dir=HERE) as tmp:
        state = Path(tmp)
        installed = run_bash(install, state)
        assert installed.returncode == 0
        for name, script in {
            "single_shell_control": install + tail,
            "carry_without_shell_options": restore + tail,
            "carry_with_explicit_test_prologue": "set -xo pipefail\n" + restore + tail,
        }.items():
            ran = run_bash(script, state)
            verdict = spec.parse_log(ran.stdout)
            try:
                manager._parse_eval_log(spec, ran.stdout)
                outcome = {"accepted_by_manager_parser": True}
            except GradingInfraError as exc:
                outcome = {"accepted_by_manager_parser": False, "category": exc.category, "detail": exc.detail}
            cases[name] = {
                "exec_rc": ran.returncode,
                "start_marker_present": ">>>>> Start Test Output" in ran.stdout,
                "end_marker_present": ">>>>> End Test Output" in ran.stdout,
                "apply_ok": verdict.apply_ok,
                "num_parsed_tests": verdict.num_parsed_tests,
                "carried_export_and_function": "CARRIED_OMP=1 FUNC=func-1" in ran.stdout,
                **outcome,
            }
    assert cases["single_shell_control"]["accepted_by_manager_parser"]
    assert not cases["carry_without_shell_options"]["accepted_by_manager_parser"]
    assert cases["carry_with_explicit_test_prologue"]["accepted_by_manager_parser"]
    result = {
        "scope": "conditional_future: no network implementation; local Bash and current renderer/parser, test command is a text fixture",
        "task": grading.instance_id,
        "original_shell_prologue": lines[:2],
        "tail_markers": [line for line in lines[start:] if line.startswith(": ")],
        "cases": cases,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    HERE.joinpath("falsifier_two_exec_markers.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
