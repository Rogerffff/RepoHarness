"""只读生产接缝诊断；不调用 Docker、SSH 或外部 API。"""

from __future__ import annotations

import asyncio
from collections import Counter
import json
from pathlib import Path
import shlex
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "runs/swe_grading_wiring_b_review_20260915/prepared_timeout_repro"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "rh2/src"))
sys.path.insert(0, str(ROOT / "rh2/tests"))
sys.path.insert(0, str(ROOT / "rh2/tests/grading"))

from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
from repoharness2.adapters.slime.sandbox_profile import grader_profile_from_env
from repoharness2.envpack.prepared_tasks import (
    HOST_GRADING_FILE, load_host_grading_views, load_prepared_manifest,
    load_prepared_rollout_views, manifest_file_sha256, prepare_tasks,
)
from repoharness2.envpack.training_view import TrustedTaskController
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager, run_docker
from grading_fixtures import FakeWorkspace, GOOD_PATCH, make_fixture_spec
from sandbox_test_support import make_grader_profile
from test_w3b_grader_profile_unit import BASE_COMMIT, ProfileGraderFakeDocker


def prepared_chain_probe() -> dict:
    controller = TrustedTaskController.from_repo_root(ROOT)
    oracle_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/B_materials_20260908/official_cmd_contract_216.json"
    oracle = {row["instance_id"]: row for row in json.loads(oracle_path.read_text())}
    rows = []
    parser_representatives = {}
    with tempfile.TemporaryDirectory(prefix="prepared-", dir=OUT) as tmp:
        public_dir, private_dir = Path(tmp) / "public", Path(tmp) / "private"
        prepare_tasks(controller, out_dir=public_dir, private_dir=private_dir)
        manifest = load_prepared_manifest(public_dir, expected_sha256=manifest_file_sha256(public_dir))
        rollout = load_prepared_rollout_views(public_dir, manifest)
        grading = load_host_grading_views(
            private_dir / HOST_GRADING_FILE,
            expected_sha256=manifest.host_grading_artifact_sha256,
            manifest=manifest,
        )
        for tid, view in grading.items():
            rv = rollout[tid]
            spec = build_grading_spec_from_host_view(
                view, image=rv.public.image, image_manifest_digest=rv.public.image_manifest_digest,
            )
            lines = spec.candidate_test_script.splitlines()
            current = lines[lines.index(": '>>>>> Start Test Output'") + 1]
            expected = oracle[view.instance_id]["official_test_line"]
            row = {
                "task_id": tid, "repo": view.grading.repo,
                "current": current, "official": expected,
                "exact_equal": current == expected,
                "shell_tokens_equal": shlex.split(current) == shlex.split(expected),
                "candidate_script": spec.candidate_test_script,
                "has_gold_field": any("gold" in name for name in type(view.grading).model_fields),
            }
            rows.append(row)
            if view.grading.repo not in parser_representatives:
                try:
                    spec.parse_log(
                        ">>>>> Start Test Output\nPASSED example.py::test_ok\n>>>>> End Test Output\n"
                    )
                except Exception as exc:
                    stack = traceback.extract_tb(exc.__traceback__)
                    parser_representatives[view.grading.repo] = {
                        "exception": type(exc).__name__, "message": str(exc),
                        "terminal_frame": {"file": str(Path(stack[-1].filename).name),
                                           "line": stack[-1].lineno, "source": stack[-1].line},
                    }
                else:
                    parser_representatives[view.grading.repo] = {"exception": None}
        public_files = sorted(path.name for path in public_dir.iterdir())
        private_files = sorted(path.name for path in private_dir.iterdir())
    (OUT / "prepared_renderer_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    return {
        "tasks": len(rows), "public_files": public_files, "private_files": private_files,
        "exact_mismatches": sum(not r["exact_equal"] for r in rows),
        "shell_token_mismatches_by_repo": dict(Counter(r["repo"] for r in rows if not r["shell_tokens_equal"])),
        "parser_representatives": parser_representatives,
        "gold_field_count": sum(r["has_gold_field"] for r in rows),
    }


async def timeout_log_probe() -> dict:
    # 容器边界用现有 fixture；仅候选 exec 经真实 run_docker/communicate 路径。
    # subprocess 工厂替换为输出哨兵的本地 Python 进程，不运行 docker。
    marker = OUT / "candidate_output_was_emitted.txt"
    marker.unlink(missing_ok=True)
    original_factory = asyncio.create_subprocess_exec

    async def local_process_factory(*args, **kwargs):
        code = (
            "import pathlib,time; "
            "print('RH2_INSTALL_RC=0', flush=True); "
            "print('RH2_PHASE=test', flush=True); "
            f"pathlib.Path({str(marker)!r}).write_text('emitted'); time.sleep(10)"
        )
        return await original_factory(sys.executable, "-u", "-c", code, **kwargs)

    class PartialOutputDocker(ProfileGraderFakeDocker):
        async def __call__(self, *args, input_bytes=None):
            if args[0] == "exec" and "-u" in args and args[-1] == "bash /rh2/eval.sh 2>&1":
                self.calls.append(args)
                return await run_docker(*args, input_bytes=input_bytes)
            return await super().__call__(*args, input_bytes=input_bytes)

    fake = PartialOutputDocker(base_commit=BASE_COMMIT)
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=OUT / "timeout_logs"),
        docker=fake,
    )
    spec = make_fixture_spec(BASE_COMMIT, "fake-image:v1", checkout_mode="image_embedded", test_timeout_seconds=0.5)
    with patch("repoharness2.grading.manager.asyncio.create_subprocess_exec", local_process_factory):
        report = await manager.grade(trajectory_id="timeout-log-evidence", workspace=FakeWorkspace(GOOD_PATCH), spec=spec)
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    eval_path = OUT / "timeout_logs" / f"{report.eval_log_ref.ref_id}.eval.log"
    log = eval_path.read_text()
    closed = await manager.close()
    assert marker.read_text() == "emitted", "候选进程必须确实开始并输出哨兵"
    assert report.outcome == "failed_to_grade" and report.reward is None
    assert "RH2_INSTALL_RC=0" not in log
    assert all(record.removed for record in manager.container_records)
    return {
        "outcome": report.outcome, "failure_category": report.failure_category,
        "detail": report.infra_failure_detail, "reward": report.reward,
        "candidate_process_did_emit": marker.exists(),
        "persisted_log_has_install_rc": "RH2_INSTALL_RC=0" in log,
        "persisted_log_has_test_phase": "RH2_PHASE=test" in log,
        "persisted_log": str(eval_path.relative_to(ROOT)),
        "phase_segments": phase.segments,
        "cleanup": closed,
        "scope": "真实 manager.grade + 真实 run_docker 捕获/取消；容器操作为 fixture；无真实 Docker",
    }


def main():
    result = {"prepared_chain": prepared_chain_probe()}
    profile = grader_profile_from_env({"RH2_GRADER_SHM_BYTES": str(1024**3)})
    result["shm_current"] = {
        "parameter_has_shm": any("shm" in k for k in profile.to_parameters()),
        "docker_args_has_shm": "--shm-size" in profile.docker_run_args(name="probe", image="probe"),
    }
    result["timeout_log"] = asyncio.run(timeout_log_probe())
    (OUT / "probe_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
