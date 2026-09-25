"""R2E 接线 R-d：环境覆盖表、按 image ID 启动、census 之后的三条预检，以及 R-0 复核的两项 driver 余项（CR1/CR2）。

FakeDocker 编排测试；真实容器里的脚本行为见 tests/grading/test_r2e_docker.py。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402
from test_replay_grade import GOOD_SETUP_ATTEST, DriverFakeDocker, DriverProfileFakeDocker  # noqa: E402

from repoharness2.adapters.slime.r2e_grading_scripts import (  # noqa: E402
    R2E_PRIVATE_HIDDEN_TESTS_DIR,
    evaluate_r2e_rollout_preflight,
    render_r2e_rollout_preflight_script,
)
from repoharness2.adapters.slime.replay_grade import (  # noqa: E402
    EXIT_ABORTED,
    CandidateInput,
    ReplayBudgets,
    ReplayGrader,
    final_exit_status,
    load_context,
    prepare_for_replay,
)
from repoharness2.envpack.environment_overlay import (  # noqa: E402
    EnvironmentOverlayError,
    EnvironmentOverlayFacts,
    EnvironmentOverlayV1,
    load_environment_overlays,
)
from repoharness2.grading.manager import (  # noqa: E402
    ExecResult,
    GradingManagerConfig,
    GradingScopeTerminationError,
    SWEGradingManager,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
IID = "coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae"
TASK = "r2e_gym_subset::" + IID
FAKE_IMAGE_ID = "sha256:" + "ab" * 32  # FakeDocker 对 `image inspect -f {{.Id}}` 的罐头回答

PREFLIGHT_OK = "RH2_PREFLIGHT_INTERPRETER=ok\nRH2_PREFLIGHT_HIDDEN_TESTS=ok\nRH2_PREFLIGHT_GIT_HISTORY=ok\n"


class R2EDriverFakeDocker(DriverFakeDocker):
    def __init__(self, *args, preflight_stdout: str = PREFLIGHT_OK, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.preflight_stdout = preflight_stdout

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec" and "RH2_PREFLIGHT_" in args[-1]:
            self.calls.append(args)
            return ExecResult(0, self.preflight_stdout, "")
        return await super().__call__(*args, input_bytes=input_bytes)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("r2e_replay_prep")
    summary = prepare_for_replay(
        repo_root=REPO_ROOT, out_dir=root / "prepared", private_dir=root / "private", task_ids=[TASK],
        sources=("r2e_gym_subset",),
    )
    assert summary["task_ids"] == [TASK]
    return {"prepared": root / "prepared", "private": root / "private", "sha": summary["prepared_manifest_sha256"]}


def _ctx(prepared: dict, docker, tmp_path: Path, overlays=None):
    return load_context(
        prepared_dir=prepared["prepared"], private_dir=prepared["private"], manifest_sha256=prepared["sha"],
        rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(),
        artifacts_dir=tmp_path / "artifacts", run_id="t", docker=docker, image_overlays=overlays,
    )


def _overlay(ctx, **changes) -> EnvironmentOverlayV1:
    public = ctx.rollout_views[TASK].public
    grading = ctx.grading_views[TASK].grading
    facts = dict(
        interpreter_relocated=True, testbed_owner="root", git_scrubbed=True,
        hidden_tests_location=R2E_PRIVATE_HIDDEN_TESTS_DIR, hidden_tests_tree_sha256=grading.hidden_tests_tree_sha256,
    )
    facts.update(changes.pop("facts", {}))
    fields = dict(
        task_id=TASK, base_image_ref=public.image, base_image_manifest_digest=public.image_manifest_digest,
        derived_image_ref="rh2-r2e-derived/coveragepy:016af5f6", derived_image_id=FAKE_IMAGE_ID,
        recipe_id="r2e_derive_v1", recipe_sha256="sha256:" + "5" * 64,
        built_at_utc=datetime(2026, 9, 21, tzinfo=timezone.utc), facts=EnvironmentOverlayFacts(**facts),
    )
    fields.update(changes)
    return EnvironmentOverlayV1(**fields)


def _gold_like_log(ctx) -> str:
    expected = ctx.grading_views[TASK].grading.expected_map()
    lines = [f"{status} r2e_tests/test_1.py::{key}" + ("" if status == "PASSED" else " - AssertionError") for key, status in expected.items()]
    # 形状与 R2E 候选段脚本的真实输出一致（无安装段标记、时间戳、Start/End、入口退出码）
    return ("RH2_INSTALL_SKIPPED=1\nRH2_TS_TEST_START=1.0\n>>>>> Start Test Output\n==== short test summary info ====\n"
            + "\n".join(lines) + "\n==== done ====\n>>>>> End Test Output\nRH2_TEST_RC=1\nRH2_TS_TEST_END=2.5\n")


def _grader(ctx, docker, tmp_path):
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    budgets = ReplayBudgets(candidate_stage_seconds=30, grading_deadline_seconds=60, cleanup_seconds=5)
    return ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=budgets)


def _base_commit(prepared, tmp_path) -> str:
    return _ctx(prepared, R2EDriverFakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit


# ---------------------------------------------------------------------------
# 覆盖表
# ---------------------------------------------------------------------------


def test_overlay_table_loads_one_entry_per_task_and_rejects_duplicates_and_bad_rows(prepared, tmp_path):
    ctx = _ctx(prepared, R2EDriverFakeDocker(base_commit="0" * 40, image_present=True), tmp_path)
    overlay = _overlay(ctx)
    table = tmp_path / "overlays.jsonl"
    table.write_text(overlay.model_dump_json() + "\n\n", encoding="utf-8")
    assert load_environment_overlays(table) == {TASK: overlay}
    table.write_text(overlay.model_dump_json() + "\n" + overlay.model_dump_json() + "\n", encoding="utf-8")
    with pytest.raises(EnvironmentOverlayError, match="重复 task_id"):
        load_environment_overlays(table)
    bad = json.loads(overlay.model_dump_json())
    bad["derived_image_id"] = "rh2-r2e-derived/coveragepy:latest"  # tag 不是身份
    table.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(EnvironmentOverlayError, match="覆盖条目非法"):
        load_environment_overlays(table)
    with pytest.raises(EnvironmentOverlayError, match="不存在"):
        load_environment_overlays(tmp_path / "missing.jsonl")


async def test_overlay_task_runs_both_containers_by_confirmed_image_id_and_preflights_after_census(prepared, tmp_path):
    docker = R2EDriverFakeDocker(base_commit=_base_commit(prepared, tmp_path), image_present=True)
    ctx0 = _ctx(prepared, docker, tmp_path)
    ctx = _ctx(prepared, docker, tmp_path, overlays={TASK: _overlay(ctx0)})
    docker.eval_log = _gold_like_log(ctx)
    row = await _grader(ctx, docker, tmp_path).replay_one(IID, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] is None, row["stage_error"]
    assert row["source"] == "r2e_gym_subset" and row["baseline_policy_version"] == "baseline_policy_r2e_v1"
    assert row["overlay"]["recipe_id"] == "r2e_derive_v1" and row["image_id_actual"] == FAKE_IMAGE_ID
    assert row["image_local_build"] is True and row["image_identity"] == "local_build:" + FAKE_IMAGE_ID
    report = row["report"]
    assert (report["outcome"], report["reward"], report["grading_semantics"]) == ("resolved", 1.0, "r2e_expected_map")
    assert report["expected_match"] == report["expected_total"] == 15 and report["f2p_total"] is None
    # 两类容器都按 image ID 启动，没有一次 `docker run` 用的是可重指的 tag 或来源镜像
    runs = [c for c in docker.calls if c[0] == "run"]
    assert len(runs) == 2 and all(FAKE_IMAGE_ID in c for c in runs)
    assert not any("rh2-r2e-derived/coveragepy:016af5f6" in c or "namanjain12/coveragepy_final" in " ".join(c) for c in runs)
    # 预检以 agent 身份、排在首次 census 之后
    execs = [c for c in docker.calls if c[0] == "exec"]
    census_at = next(i for i, c in enumerate(execs) if "-prune" in c[-1] and "readlink" in c[-1])
    preflight_at = next(i for i, c in enumerate(execs) if "RH2_PREFLIGHT_" in c[-1])
    assert census_at < preflight_at and "-u" in execs[preflight_at] and "54321" in execs[preflight_at]


async def test_preflight_failure_keeps_the_task_out_of_the_candidate_stage(prepared, tmp_path):
    failing = PREFLIGHT_OK.replace("INTERPRETER=ok", "INTERPRETER=fail:not_executable_as_agent")
    docker = R2EDriverFakeDocker(base_commit=_base_commit(prepared, tmp_path), image_present=True, preflight_stdout=failing)
    ctx = _ctx(prepared, docker, tmp_path)  # 没有覆盖条目：来源镜像的解释器在 /root 下，预检①拦下
    row = await _grader(ctx, docker, tmp_path).replay_one(IID, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] == "r2e_preflight:interpreter:fail:not_executable_as_agent"
    assert row["report"] is None and docker.grade_execs == 0 and row["cleanup"]["removed"] is True


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"base_image_manifest_digest": "sha256:" + "7" * 64}, "overlay:base_image_mismatch"),
        ({"derived_image_id": "sha256:" + "cd" * 32}, "overlay:image_id_mismatch"),
        ({"facts": {"hidden_tests_tree_sha256": "sha256:" + "8" * 64}}, "overlay:hidden_tests_tree_mismatch"),
        ({"facts": {"hidden_tests_location": "/r2e_tests"}}, "overlay:hidden_tests_location_mismatch"),
        ({"facts": {"git_scrubbed": False}}, "overlay:recipe_facts_incomplete"),
    ],
)
async def test_overlay_mismatches_are_stage_errors_and_nothing_is_started(prepared, tmp_path, changes, error):
    docker = R2EDriverFakeDocker(base_commit=_base_commit(prepared, tmp_path), image_present=True)
    ctx0 = _ctx(prepared, docker, tmp_path)
    ctx = _ctx(prepared, docker, tmp_path, overlays={TASK: _overlay(ctx0, **changes)})
    row = await _grader(ctx, docker, tmp_path).replay_one(IID, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"].startswith(error) and row["report"] is None
    assert not [c for c in docker.calls if c[0] == "run"]
    assert json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])["stage_error"].startswith(error)


def test_preflight_script_shape_and_fail_closed_evaluation():
    script = render_r2e_rollout_preflight_script()
    assert "/testbed/.venv/bin/python -B -I -S -c pass" in script  # 不写字节码、不加载 site（B 线 B1）
    assert "git rev-list --children --all" in script and R2E_PRIVATE_HIDDEN_TESTS_DIR in script
    assert evaluate_r2e_rollout_preflight(PREFLIGHT_OK) == []
    assert evaluate_r2e_rollout_preflight("") == [
        "interpreter:fail:no_output", "hidden_tests:fail:no_output", "git_history:fail:no_output"]
    leaked = PREFLIGHT_OK.replace("GIT_HISTORY=ok", "GIT_HISTORY=fail:head_has_children_or_is_unlisted")
    assert evaluate_r2e_rollout_preflight(leaked) == ["git_history:fail:head_has_children_or_is_unlisted"]


# ---------------------------------------------------------------------------
# R-0 复核余项
# ---------------------------------------------------------------------------


def test_cr1_final_status_never_says_ok_while_an_exception_is_propagating():
    closed = {"containers_open": [], "cleanup_failures": []}
    assert final_exit_status(halted=None, manager_close=closed)["reason"] == "ok"
    status = final_exit_status(halted=None, manager_close=closed, aborted="RuntimeError:boom")
    assert (status["exit_code"], status["reason"]) == (EXIT_ABORTED, "aborted:RuntimeError:boom")
    # 停批优先于 aborted；aborted 优先于"仍有未关容器"（后者的清单照常报告）
    assert final_exit_status(halted="x", manager_close=closed, aborted="E:y")["reason"] == "halted:x"
    still_open = final_exit_status(halted=None, manager_close={"containers_open": ["c1"], "cleanup_failures": ["c1"]}, aborted="E:y")
    assert still_open["reason"] == "aborted:E:y" and still_open["grader_containers_open"] == ["c1"]


async def test_cr1_cli_summary_records_the_abort_and_still_reports_cleanup(prepared, tmp_path, monkeypatch, capsys):
    # 脚本导入时把 rh2/src 插到 sys.path 首位；换成副本，测试结束由 monkeypatch 还原原列表，
    # 免得后续测试（例 reference/slime 的差分测试）按被污染的路径取到 vendored slime（Codex 09-24 批次二复核 F1）。
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("replay_cli_cr1", REPO_ROOT / "rh2" / "scripts" / "replay_grade.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    summary = tmp_path / "replay_summary.json"
    summary.write_text(json.dumps({
        "prepared_dir": str(prepared["prepared"]), "private_dir": str(prepared["private"]), "prepared_manifest_sha256": prepared["sha"],
    }), encoding="utf-8")

    async def boom(self, task_ref, candidate, *, attempt=1):
        raise RuntimeError("driver bug")

    monkeypatch.setattr(cli.ReplayGrader, "replay_one", boom)
    ns = argparse.Namespace(
        prepared_summary=str(summary), task_ids=None, candidate="noop", repeat=1, candidate_stage_seconds=5.0,
        grading_deadline_seconds=5.0, cleanup_seconds=5.0, image_pull_seconds=5.0, eval_log_dir=str(tmp_path / "logs"),
        artifacts_dir=str(tmp_path / "artifacts"), ledger=str(tmp_path / "ledger.jsonl"), derived_image=None,
        derived_image_recipe=None, qualification_ledger=[], image_overlays=None,
    )
    with pytest.raises(RuntimeError, match="driver bug"):
        await cli._run(ns)
    out = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    assert out[-1]["aborted"] == "RuntimeError:driver bug"
    assert out[-1]["final_status"]["reason"] == "aborted:RuntimeError:driver bug" and out[-1]["final_status"]["exit_code"] == EXIT_ABORTED
    assert "manager_close" in out[-1]


class R2EProfileDriverDocker(DriverProfileFakeDocker):
    """正式 grader profile 组合（可信 setup / 权限布置 / 候选段替身 + 候选容器初始化）+ R2E 预检罐头
    + 评分容器收口旋钮：`scope="ok"` 正常；`"late_removed"` 首次 rm 失败但容器已停（晚清成功）；
    `"stuck"` rm / kill 都无效且 inspect 恒报运行（scope 无法确认终止 → 停批）。只对 `rh2-grading-*` 生效。"""

    def __init__(self, *args, preflight_stdout: str = PREFLIGHT_OK, scope: str = "ok", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.preflight_stdout = preflight_stdout
        self.scope = scope
        self.grader_rm_attempts = 0

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec" and "RH2_PREFLIGHT_" in str(args[-1]):
            self.calls.append(args)
            return ExecResult(0, self.preflight_stdout, "")
        name = args[-1] if args and str(args[-1]).startswith("rh2-grading-") else None
        if name is not None and self.scope != "ok":
            if args[0] == "rm":
                self.grader_rm_attempts += 1
                if self.scope == "stuck" or self.grader_rm_attempts == 1:
                    self.calls.append(args)
                    return ExecResult(1, "", f"cannot remove {name}: injected daemon failure")
            if args[0] == "inspect" and "{{.State.Running}}" in args:
                self.calls.append(args)
                return ExecResult(0, "true\n" if self.scope == "stuck" else "false\n", "")
            if args[0] == "kill" and self.scope == "stuck":
                self.calls.append(args)
                return ExecResult(1, "", "injected kill failure")
        return await super().__call__(*args, input_bytes=input_bytes)


def _profile_run(prepared, tmp_path, *, scope: str):
    """真实 producer：正式 grader profile 的 SWEGradingManager + 覆盖表 + gold 形状日志 → 正常 resolved 报告已落盘。"""
    docker = R2EProfileDriverDocker(base_commit=_base_commit(prepared, tmp_path), image_present=True, scope=scope)
    ctx0 = _ctx(prepared, docker, tmp_path)
    ctx = _ctx(prepared, docker, tmp_path, overlays={TASK: _overlay(ctx0)})
    docker.eval_log = _gold_like_log(ctx)
    n_official = str(len(ctx.grading_views[TASK].grading.hidden_test_files) + 1)  # 隐藏测试 + run_tests.sh
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": n_official, "RH2_SETUP_TEST_FILES": n_official}
    manager = SWEGradingManager(
        GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=make_grader_profile()), docker=docker,
    )
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl",
                          budgets=ReplayBudgets(candidate_stage_seconds=30, grading_deadline_seconds=60, cleanup_seconds=5))
    return docker, manager, grader


async def test_cr2_normal_report_replaced_by_scope_termination_keeps_log_sidecar_and_facts(prepared, tmp_path):
    """R-0 复核 CR2 的正常报告分支（真实 producer，09-23 补）：测试正常完成、manager 已组好 resolved 报告并把日志 /
    sidecar 落盘，随后评分容器无法确认停止 → GradingScopeTerminationError **替换**报告上抛。driver 停批账本必须带
    已落盘的两个引用与候选段事实，且没有 report / reward；收口摘要退出码 2。"""
    docker, manager, grader = _profile_run(prepared, tmp_path, scope="stuck")
    with pytest.raises(GradingScopeTerminationError):
        await grader.replay_one(IID, CandidateInput(kind="noop", origin="noop"))
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"].startswith("baseline_integrity:") and row["report"] is None
    log_path = Path(row["log"]["path"])
    assert log_path.exists() and row["log"]["partial"] is False
    assert row["log"]["sha256"] == "sha256:" + hashlib.sha256(log_path.read_bytes()).hexdigest()
    assert row["diagnostics_ref"] and Path(row["diagnostics_ref"]).exists()
    assert ">>>>> End Test Output" in log_path.read_text() and "RH2_TEST_RC=1" in log_path.read_text()
    assert row["install"]["install_skipped"] is True and row["install"]["test_rc"] == 1
    assert row["test"] == {"rc": 1, "seconds": 1.5, "exec_exit_code": 0, "segment_completed": True}
    # 已落盘的正是被替换掉的那份正常报告的日志（record 上的引用 == 落盘文件）
    record = manager.container_records[-1]
    assert record.persisted_eval_log_ref is not None and str(log_path).endswith(f"{record.persisted_eval_log_ref.ref_id}.eval.log")
    closed = await manager.close()
    assert closed["containers_open"] == [record.name]
    assert final_exit_status(halted="GradingScopeTerminationError", manager_close=closed)["exit_code"] == 2


async def test_cr2_late_removed_grader_container_still_delivers_the_report(prepared, tmp_path):
    """晚清成功对照：首次 rm 失败但 inspect 说容器已停 → 只留清理诊断，报告照常交付；最终无未关容器 → 退出码 0。"""
    docker, manager, grader = _profile_run(prepared, tmp_path, scope="late_removed")
    row = await grader.replay_one(IID, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] is None and row["report"]["outcome"] == "resolved" and row["report"]["reward"] == 1.0
    assert Path(row["log"]["path"]).exists() and row["diagnostics_ref"]
    assert any(f.startswith("container_scope_stopped_but_not_removed:") for f in manager.cleanup_failures)
    closed = await manager.close()
    status = final_exit_status(halted=None, manager_close=closed)
    assert closed["containers_open"] == [] and status["exit_code"] == 0 and status["cleanup_failures_resolved"] is True


async def test_cr2_manager_remembers_the_infra_log_reference_on_its_record(tmp_path):
    """CR2 的 manager 半边：infra 收口落盘的日志引用记在 record 上——scope 终止失败替换掉 infra 报告时，调用方仍找得到证据。"""
    from grading_fixtures import GOOD_PATCH, NO_MARKER_FAKE_LOG, FakeDocker, FakeWorkspace, make_fixture_spec

    manager = SWEGradingManager(
        GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=FakeDocker(base_commit="a" * 40, eval_log=NO_MARKER_FAKE_LOG))
    report = await manager.grade(
        trajectory_id="traj_infra", workspace=FakeWorkspace(GOOD_PATCH),
        spec=make_fixture_spec("a" * 40, "fake", checkout_mode="image_embedded"),
    )
    assert report.outcome == "failed_to_grade" and report.eval_log_ref is not None
    record = manager.container_records[-1]
    assert record.persisted_eval_log_ref == report.eval_log_ref
    assert (tmp_path / "logs" / f"{record.persisted_eval_log_ref.ref_id}.eval.log").exists()
