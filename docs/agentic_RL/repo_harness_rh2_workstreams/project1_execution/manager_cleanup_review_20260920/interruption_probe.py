"""审查探针：取消窗口旧新对照、非空短 tee、真实 Bash 收尾正控。

仅调用真实 manager + Docker 替身及本机 Bash；不启动容器。
断言当前残余行为，不能作为修复后的正确性 oracle。
"""

import asyncio
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path[:0] = [str(ROOT / p) for p in ("rh2/src", "rh2/tests/grading", "rh2/tests")]

from grading_fixtures import GOOD_PATCH, FakeWorkspace
from sandbox_test_support import make_grader_profile
from test_w3b_grader_profile_unit import BASE_COMMIT, ProfileGraderFakeDocker, _spec

from repoharness2.adapters.slime import prepared_task_face as renderer
from repoharness2.grading import manager as current

BASELINE = "e3d120b55a62cca5985f688de8cdd481b12ea6be"
baseline_source = subprocess.check_output(
    ["git", "show", f"{BASELINE}:rh2/src/repoharness2/grading/manager.py"], cwd=ROOT, text=True,
)
baseline = types.ModuleType("repoharness2.grading._review_baseline")
baseline.__file__ = "<review-baseline-manager>"
sys.modules[baseline.__name__] = baseline
exec(compile(baseline_source, baseline.__file__, "exec"), baseline.__dict__)

LOG = (
    "RH2_PHASE_START=install\nRH2_INSTALL_RC=0\nRH2_PHASE_END=install\n"
    "RH2_TS_TEST_START=104.0\nDELIVERED_OUTPUT_PROBE=1\n"
)


class Docker(ProfileGraderFakeDocker):
    def __init__(self, pause_at=None, *, unknown=False, partial=""):
        super().__init__(base_commit=BASE_COMMIT, eval_log=LOG, eval_exit_code=137, container_running=False)
        self.pause_at = pause_at
        self.entered = asyncio.Event()
        self.exec_delivered = False
        self.candidate_partial_log = partial
        if unknown:
            self.inspect_fail = "temporary daemon response failure"

    async def __call__(self, *args, input_bytes=None):
        if self.exec_delivered and (
            (self.pause_at == "inspect" and args[0] == "inspect" and "{{.State.Running}}" in args)
            or (self.pause_at == "partial_read" and args[0] == "exec" and "cat /rh2/candidate/eval.log" in args[-1])
        ):
            self.entered.set()
            await asyncio.Event().wait()
        result = await super().__call__(*args, input_bytes=input_bytes)
        if args[0] == "exec" and "| tee /rh2/candidate/eval.log" in args[-1]:
            self.exec_delivered = True
        return result


async def run_case(module, *, pause_at=None, unknown=False, partial=""):
    docker = Docker(pause_at, unknown=unknown, partial=partial)
    with tempfile.TemporaryDirectory(prefix="rh2-manager-review-") as directory:
        out = Path(directory)
        manager = module.SWEGradingManager(
            module.GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=out), docker=docker,
        )
        task = asyncio.create_task(manager.grade(trajectory_id="probe", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec()))
        cancelled = False
        report = None
        if pause_at:
            await asyncio.wait_for(docker.entered.wait(), 3)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                cancelled = True
        else:
            report = await task
        record = manager.container_records[-1]
        ref = record.cancelled_eval_log_ref if cancelled else report.eval_log_ref
        log = (out / f"{ref.ref_id}.eval.log").read_text()
        result = {
            "code": "baseline" if module is baseline else "working_tree", "pause_at": pause_at,
            "exec_delivered": docker.exec_delivered, "cancelled": cancelled,
            "delivered_output_retained": "DELIVERED_OUTPUT_PROBE=1" in log,
            "candidate_facts": record.candidate_facts, "container_removed": record.removed,
            "reward": report.reward if report else None,
            "detail": report.infra_failure_detail if report else None,
        }
        assert docker.exec_delivered and record.removed
        if pause_at:
            assert cancelled and not result["delivered_output_retained"]
        return result


async def main():
    cases = [await run_case(module, pause_at=pause) for module in (baseline, current) for pause in ("inspect", "partial_read")]
    control = await run_case(current)
    assert control["delivered_output_retained"] and control["candidate_facts"]["candidate_exec_exit_code"] == 137
    cases.append(control)
    shorter = await run_case(current, unknown=True, partial="RH2_PHASE_START=install\n")
    assert not shorter["delivered_output_retained"] and "candidate_phase=install" in shorter["detail"]
    cases.append(shorter)

    shell_cases = []
    original = renderer.derive_test_command_for_bundle
    try:
        for code in (0, 1, 137, 255):
            renderer.derive_test_command_for_bundle = lambda _grading, rc=code: f"bash -c 'exit {rc}'"
            script = "\n".join(["set -xo pipefail", "echo RH2_INSTALL_SKIPPED=1", *renderer._v2_candidate_test_lines(None)]) + "\n"
            result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
            facts = current.candidate_segment_facts(result.stdout + result.stderr, result.returncode)
            assert result.returncode == 0 and facts["test_rc"] == code and facts["candidate_segment_completed"] is True
            shell_cases.append({"child_exit": code, "wrapper_exit": result.returncode, "test_rc": facts["test_rc"], "completed": facts["candidate_segment_completed"]})
    finally:
        renderer.derive_test_command_for_bundle = original
    print(json.dumps({"baseline": BASELINE, "scope": "CPU fake Docker + local Bash; no Docker processes", "cases": cases, "shell_cases": shell_cases}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
