"""跨 manager 窄复核：真实 manager 的日志/退出码运输；只替换 Docker，不改工作区源码。"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src/repoharness2").is_dir())
BASELINE = "e3d120b55a62cca5985f688de8cdd481b12ea6be"
sys.path[:0] = [str(ROOT / "rh2/tests/grading"), str(ROOT / "rh2/tests")]
spec = importlib.util.spec_from_file_location("manager_review_fixtures", ROOT / "rh2/tests/grading/test_w3b_grader_profile_unit.py")
fx = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fx
spec.loader.exec_module(fx)
from repoharness2.grading import manager as gm


def prior_eval_method():
    """只在内存中用审查起点的旧 _run_eval 作差分；其余 manager 与 Docker 替身保持相同。"""
    source = subprocess.check_output(["git", "show", f"{BASELINE}:rh2/src/repoharness2/grading/manager.py"], cwd=ROOT, text=True)
    cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "SWEGradingManager")
    node = next(n for n in cls.body if getattr(n, "name", None) == "_run_eval")
    unit = ast.Module(body=ast.parse("from __future__ import annotations").body + [node], type_ignores=[])
    ns = dict(vars(gm))
    exec(compile(ast.fix_missing_locations(unit), "HEAD:_run_eval", "exec"), ns)
    return ns["_run_eval"]


class PriorEvalManager(gm.SWEGradingManager):
    _run_eval = prior_eval_method()


async def run_case(directory, name, log, rc, *, running=True, prior=False):
    docker = fx.ProfileGraderFakeDocker(base_commit=fx.BASE_COMMIT, eval_log=log, eval_exit_code=rc, container_running=running)
    docker.candidate_partial_log = ""  # 模拟容器死亡后文件已读不到；已交付 stdout 仍应保留
    cls = PriorEvalManager if prior else gm.SWEGradingManager
    manager = cls(gm.GradingManagerConfig(sandbox_profile=fx.make_grader_profile(), eval_log_dir=directory / name), docker=docker)
    report = await manager.grade(trajectory_id=name, workspace=fx.FakeWorkspace(patch_text=fx.GOOD_PATCH), spec=fx._spec())
    record = manager.container_records[-1]
    ref = report.eval_log_ref
    saved = (manager.config.eval_log_dir / f"{ref.ref_id}.eval.log").read_text() if ref else ""
    sidecar = json.loads((manager.config.eval_log_dir / f"{ref.ref_id}.diagnostics.json").read_text()) if ref else {}
    result = {
        "outcome": report.outcome, "reward": report.reward, "failure_category": report.failure_category,
        "detail": report.infra_failure_detail, "candidate": record.candidate_facts,
        "candidate_output_retained": log in saved, "sidecar_matches_record": sidecar.get("candidate") == record.candidate_facts,
        "close": await manager.close(), "regrade_total": manager.regrade_total,
    }
    assert result["close"]["containers_open"] == []
    assert result["sidecar_matches_record"]
    return result


async def main():
    old_dir = ROOT / "runs/env_recipe_repair_20260919/numeric_v1e/tasks/Project-MONAI__MONAI-763/gold"
    ledger = json.loads((old_dir / "ledger.jsonl").read_text().splitlines()[0])
    log_path = old_dir / "eval_logs" / Path(ledger["log"]["path"]).name
    raw = log_path.read_bytes()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == ledger["log"]["sha256"]
    monai = raw.decode()
    prefix = "RH2_INSTALL_SKIPPED=1\nRH2_TS_TEST_START=100\n"
    success = prefix + fx.GOOD_FAKE_LOG + "\nRH2_TEST_RC=0\nRH2_TS_TEST_END=101\n"
    failure = success.replace("PASSED tests/test_thing.py::test_feature", "FAILED tests/test_thing.py::test_feature")
    with tempfile.TemporaryDirectory(prefix="rh2-manager-review-") as temp:
        directory = Path(temp)
        cases = {}
        for name, log, rc, kwargs in (
            ("resolved_control", success, 0, {}),
            ("model_failure_control", failure, 0, {}),
            ("monai_race_prior_method", monai, 137, {"prior": True}),
            ("monai_race_fixed", monai, 137, {}),
            ("monai_already_dead_fixed", monai, 137, {"running": False}),
            ("finished_wrapper_with_killed_child", success.replace("RH2_TEST_RC=0", "RH2_TEST_RC=137"), 0, {}),
            ("candidate_supplied_finish_marker_prior", success, 137, {"prior": True}),
            ("candidate_supplied_finish_marker_fixed", success, 137, {}),
        ):
            cases[name] = await run_case(directory, name, log, rc, **kwargs)
        assert cases["resolved_control"]["reward"] == 1.0
        assert cases["model_failure_control"]["reward"] == 0.0
        assert cases["monai_race_prior_method"]["failure_category"] == "test_log_parse_failed"
        assert cases["monai_race_prior_method"]["candidate"]["log_partial"] is False
        for name in ("monai_race_fixed", "monai_already_dead_fixed"):
            case = cases[name]
            assert case["reward"] is None and case["failure_category"] == "infra_failure"
            assert case["candidate"]["log_partial"] and case["candidate"]["candidate_exec_exit_code"] == 137
            assert case["candidate"]["candidate_segment_completed"] is False
            assert case["candidate_output_retained"] and case["regrade_total"] == 0
        # stdout 可伪造的既有边界：本修复没有消除它，也不是本修复新引入。
        assert cases["candidate_supplied_finish_marker_prior"]["reward"] == cases["candidate_supplied_finish_marker_fixed"]["reward"]
        print(json.dumps({"scope": "CPU 真实 manager + Docker 替身，rc/state 显式注入；不是重跑 MONAI",
                          "historical_log_sha256": ledger["log"]["sha256"], "cases": cases}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
