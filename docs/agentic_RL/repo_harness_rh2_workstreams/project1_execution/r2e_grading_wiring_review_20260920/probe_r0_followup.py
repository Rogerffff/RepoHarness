"""R-0 独立 CPU 接缝复核；不调用 Docker，也不改变生产实现。

从仓库根执行：
  rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_grading_wiring_review_20260920/probe_r0_followup.py

真实 CLI _run → ReplayGrader → manager.grade/close → 持久账本；固定 profile 配置，替换 Docker I/O。
候选材料用既有一题 prepare；清理失败/信号/后观测取消由 I/O 替身注入。
缺补丁案使用真实 FileNotFoundError，未替换 replay_one / grade / close / 状态函数。
输出反映当前实现，观察异常摘要案并不把它当正确期望冻结成维护测试。
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path[:0] = [str(ROOT / p) for p in ("rh2/src", "rh2/tests/adapters", "rh2/tests/grading", "rh2/tests")]

from test_replay_grade import (  # noqa: E402
    GOOD_SETUP_ATTEST, TASK, DriverProfileFakeDocker, FakeDocker, _ctx,
    make_grader_profile, make_rollout_profile,
)
from repoharness2.envpack.prepared_tasks import manifest_file_sha256, prepare_tasks  # noqa: E402
from repoharness2.envpack.training_view import TrustedTaskController  # noqa: E402
from repoharness2.grading.manager import ExecResult, SWEGradingManager, patch_touched_paths  # noqa: E402


def load_cli():
    spec = importlib.util.spec_from_file_location("r0_review_cli", ROOT / "rh2/scripts/replay_grade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FailureDocker(DriverProfileFakeDocker):
    def __init__(self, *, case: str, **kwargs):
        super().__init__(**kwargs)
        self.case = case
        self.grader_rm_counts: dict[str, int] = {}
        self.post_entered = asyncio.Event()

    async def __call__(self, *args, input_bytes=None):
        grader_name = args[-1] if args and str(args[-1]).startswith("rh2-grading-") else None
        if args[0] == "rm" and grader_name:
            count = self.grader_rm_counts.get(grader_name, 0) + 1
            self.grader_rm_counts[grader_name] = count
            if (self.case in {"left_open", "halt_running"}
                    or (self.case == "late_removed" and count == 1)
                    or (self.case == "halt_late_removed" and count <= 2)):
                self.calls.append(args)
                return ExecResult(1, "", f"cannot remove {grader_name}: injected daemon failure")
        if args[0] == "inspect" and "{{.State.Running}}" in args and grader_name in self.grader_rm_counts:
            self.calls.append(args)
            return ExecResult(0, "true\n" if self.case.startswith("halt_") else "false\n", "")
        if self.case.startswith("halt_") and args[0] == "kill" and grader_name:
            self.calls.append(args)
            return ExecResult(1, "", "injected kill failure")
        if self.case == "cancel_after_candidate" and args[0] == "exec" and "RH2_OBS_IMPORT_PATH" in args[-1]:
            self.calls.append(args)
            self.post_entered.set()
            await asyncio.Event().wait()
        return await super().__call__(*args, input_bytes=input_bytes)


async def run_case(prepared, root: Path, case: str) -> dict:
    root.mkdir()
    cli = load_cli()
    initial = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), root)
    public = initial.rollout_views[TASK].public
    bundle = initial.grading_views[TASK].grading
    body = "".join(f"PASSED {key}\n" for key in [*bundle.fail_to_pass, *bundle.pass_to_pass])
    log = ("RH2_PHASE_START=install\nRH2_TS_INSTALL_START=1\nRH2_INSTALL_RC=0\n"
           "RH2_TS_INSTALL_END=2\nRH2_PHASE_END=install\nRH2_TS_TEST_START=3\n"
           "+ : '>>>>> Start Test Output'\n" + body)
    if case != "exec_signal":
        log += "+ : '>>>>> End Test Output'\nRH2_TEST_RC=0\nRH2_TS_TEST_END=4\n"
    docker = FailureDocker(case=case, base_commit=public.base_commit, image_present=True,
                           eval_log=log, eval_exit_code=137 if case == "exec_signal" else 0)
    count = len(set(patch_touched_paths(bundle.test_patch)))
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": str(count), "RH2_SETUP_TEST_FILES": str(count)}
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=same\nRH2_OBS_IMPORT_PATH=/testbed/moto/__init__.py\n"
    original_load = cli.load_context
    manager_ref = []

    def context_factory(**kwargs):
        return original_load(**kwargs, docker=docker)

    def manager_factory(config):
        manager = SWEGradingManager(config, docker=docker)
        manager_ref.append(manager)
        return manager

    summary_path = root / "prepared_summary.json"
    summary_path.write_text(json.dumps({"prepared_dir": str(prepared["prepared"]), "private_dir": str(prepared["private"]),
                                       "prepared_manifest_sha256": prepared["sha"]}))
    ns = argparse.Namespace(
        prepared_summary=str(summary_path), task_ids=TASK,
        candidate=f"patch:{root / 'missing.patch'}" if case == "missing_patch" else "noop",
        repeat=2 if case.startswith("halt_") else 1,
        candidate_stage_seconds=10.0, grading_deadline_seconds=10.0, cleanup_seconds=3.0, image_pull_seconds=3.0,
        eval_log_dir=str(root / "logs"), artifacts_dir=str(root / "artifacts"), ledger=str(root / "ledger.jsonl"),
        derived_image="local/derived:test", derived_image_recipe="cpu-fixture", qualification_ledger=[],
    )
    output = io.StringIO()
    code = None
    error = None
    with patch.object(cli, "load_context", context_factory), patch.object(cli, "SWEGradingManager", manager_factory), \
         patch.object(cli, "rollout_profile_from_env", lambda *a, **k: make_rollout_profile()), \
         patch.object(cli, "grader_profile_from_env", lambda *a, **k: make_grader_profile()), \
         contextlib.redirect_stdout(output):
        task = asyncio.create_task(cli._run(ns))
        if case == "cancel_after_candidate":
            await asyncio.wait_for(docker.post_entered.wait(), timeout=5)
            task.cancel()
        try:
            code = await task
        except BaseException as exc:
            error = type(exc).__name__
    records = [json.loads(line) for line in output.getvalue().splitlines() if line.startswith("{")]
    final = records[-1]
    ledger = Path(ns.ledger)
    rows = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
    report = (rows[-1].get("report") or {}) if rows else {}
    install = (rows[-1].get("install") or {}) if rows else {}
    sides = list((root / "logs").glob("*.diagnostics.json"))
    side_facts = (json.loads(sides[-1].read_text()).get("candidate") or {}) if sides else {}
    result = {
        "case": case, "run_return": code, "exception": error,
        "final_status": final.get("final_status"), "reported_rows": final.get("rows"), "ledger_rows": len(rows),
        "test": rows[-1].get("test") if rows else None,
        "candidate_facts": {key: install.get(key) for key in ("candidate_exec_exit_code", "candidate_segment_completed")},
        "persisted_sidecar_facts": {key: side_facts.get(key) for key in ("candidate_exec_exit_code", "candidate_segment_completed")},
        "ledger_has_log_ref": bool(rows and rows[-1].get("log")),
        "ledger_has_diagnostics_ref": bool(rows and rows[-1].get("diagnostics_ref")),
        "outcome": report.get("outcome"), "reward": report.get("reward"),
        "stage_error": rows[-1].get("stage_error") if rows else None,
        "manager_closed": manager_ref[0].closed,
        "manager_record_count": len(manager_ref[0].container_records),
    }
    if case in {"normal", "late_removed"}:
        assert code == 0 and report["reward"] == 1
        assert rows[-1]["test"]["exec_exit_code"] == 0 and rows[-1]["test"]["segment_completed"] is True
    elif case == "left_open":
        assert code == 3 and report["reward"] == 1 and final["manager_close"]["containers_open"]
    elif case.startswith("halt_"):
        assert code == 2 and len(rows) == 1 and report == {}
        assert side_facts["candidate_exec_exit_code"] == 0 and side_facts["candidate_segment_completed"] is True
        if case == "halt_late_removed":
            assert not final["manager_close"]["containers_open"]
    elif case == "exec_signal":
        assert code == 0 and report["reward"] is None and report["outcome"] == "failed_to_grade"
        assert rows[-1]["test"]["exec_exit_code"] == 137 and rows[-1]["test"]["segment_completed"] is False
    elif case == "missing_patch":
        assert error == "FileNotFoundError" and code is None
    elif case == "cancel_after_candidate":
        assert error == "CancelledError" and len(rows) == 1 and report == {}
    return result


def run_unmocked_cli_missing_patch(prepared, root: Path):
    root.mkdir()
    summary = root / "prepared_summary.json"
    summary.write_text(json.dumps({"prepared_dir": str(prepared["prepared"]), "private_dir": str(prepared["private"]),
                                  "prepared_manifest_sha256": prepared["sha"]}))
    proc = subprocess.run([
        sys.executable, str(ROOT / "rh2/scripts/replay_grade.py"), "run", "--prepared-summary", str(summary),
        "--candidate", f"patch:{root / 'missing.patch'}", "--eval-log-dir", str(root / "logs"),
        "--artifacts-dir", str(root / "artifacts"), "--ledger", str(root / "ledger.jsonl"),
    ], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    records = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
    assert proc.returncode == 1 and "FileNotFoundError" in proc.stderr
    return {"case": "unmocked_cli_missing_patch", "process_exit_code": proc.returncode,
            "final_status": records[-1]["final_status"], "ledger_exists": (root / "ledger.jsonl").exists()}


async def main():
    with tempfile.TemporaryDirectory(prefix="rh2-r0-review-") as tmp:
        root = Path(tmp)
        controller = TrustedTaskController.from_repo_root(ROOT)
        prepare_tasks(controller, out_dir=root / "prepared", private_dir=root / "private", task_ids=[TASK])
        prepared = {"prepared": root / "prepared", "private": root / "private", "sha": manifest_file_sha256(root / "prepared")}
        cases = ("normal", "late_removed", "left_open", "halt_running", "halt_late_removed", "exec_signal", "missing_patch", "cancel_after_candidate")
        results = [await run_case(prepared, root / case, case) for case in cases]
        cli_result = run_unmocked_cli_missing_patch(prepared, root / "unmocked_cli")
    print(json.dumps({"scope": "actual driver/manager control flow; Docker I/O fixture, no containers", "cases": results,
                      "unmocked_cli": cli_result}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
