"""S1-d（评分接线 2026-09-15）：真实评分链 driver 的编排、预算与清理（FakeDocker）。

覆盖：noop 经派生镜像分支评分成功；候选补丁 `git apply --check` 失败即停止不评分；候选阶段超时保留首个失败
原因且容器被清理；镜像 digest 路径；评分异常记录后不吞掉行；gold 受信导出与候选说明解析。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "grading"))  # grading_fixtures
from grading_fixtures import FakeDocker  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # sandbox_test_support
from sandbox_test_support import make_grader_profile, make_rollout_profile  # noqa: E402

from test_w3b_grader_profile_unit import GOOD_SETUP_ATTEST, ProfileGraderFakeDocker  # noqa: E402

from repoharness2.adapters.slime.replay_grade import (  # noqa: E402
    CandidateInput,
    DerivedImage,
    ReplayBudgets,
    ReplayGrader,
    ReplayHaltError,
    candidate_from_spec,
    export_gold_candidates,
    load_context,
)
from repoharness2.envpack.prepared_tasks import manifest_file_sha256, prepare_tasks  # noqa: E402
from repoharness2.envpack.training_view import TrustedTaskController  # noqa: E402
from repoharness2.grading.manager import ExecResult, GradingManagerConfig, SWEGradingManager  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
INGEST = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
TASK = "swe_gym_lite::getmoto__moto-6913"
IID = "getmoto__moto-6913"


class DriverFakeDocker(FakeDocker):
    """在评分 FakeDocker 之上补候选容器路径：可信初始化、补丁写入/校验、可选初始化延迟。"""

    def __init__(self, *args, init_delay: float = 0.0, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.init_delay = init_delay
        self.grade_execs = 0
        self.census_outputs: list[str] = []  # 非空时按顺序作为 census 输出（基线、post）
        self.fetch_output: str = ""

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec":
            script = args[-1]
            if self.census_outputs and "-prune" in script and "readlink" in script:
                self.calls.append(args)
                return ExecResult(0, self.census_outputs.pop(0), "")
            if "base64 <" in script:
                self.calls.append(args)
                return ExecResult(0, self.fetch_output, "")
            if "rollout-trusted-init" in script:
                self.calls.append(args)
                if self.init_delay:
                    await asyncio.sleep(self.init_delay)
                return ExecResult(0, "RH2_INIT_OK=1\nAGENT_UID=54321\nWORKDIR_PRESENT=1\n", "")
            if script.startswith("bash ") and "2>&1" in script:
                self.grade_execs += 1
        if args[0] == "kill":
            self.calls.append(args)
            return ExecResult(0, "", "")
        return await super().__call__(*args, input_bytes=input_bytes)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("replay_prep")
    controller = TrustedTaskController.from_repo_root(REPO_ROOT)
    prepare_tasks(controller, out_dir=root / "prepared", private_dir=root / "private", task_ids=[TASK])
    return {"prepared": root / "prepared", "private": root / "private", "sha": manifest_file_sha256(root / "prepared")}


def _ctx(prepared: dict, docker: FakeDocker, tmp_path: Path, *, derived: bool = True):
    return load_context(
        prepared_dir=prepared["prepared"], private_dir=prepared["private"], manifest_sha256=prepared["sha"],
        rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(),
        artifacts_dir=tmp_path / "artifacts", run_id="t", docker=docker,
        derived_image=DerivedImage(ref="local/derived:test", recipe="fixture") if derived else None,
    )


def _eval_log_for(ctx) -> str:
    g = ctx.grading_views[TASK].grading
    body = "".join(f"PASSED {t}\n" for t in [*g.fail_to_pass, *g.pass_to_pass])
    return f"+ : '>>>>> Start Test Output'\n{body}+ : '>>>>> End Test Output'\n"


def _docker(ctx_base_commit: str, **kw) -> DriverFakeDocker:
    return DriverFakeDocker(base_commit=ctx_base_commit, image_present=True, **kw)


async def test_noop_through_derived_image_path_grades_and_cleans_up(prepared, tmp_path):
    # base_commit 需要先从视图取：先建一个空 docker 的 ctx 读视图
    probe_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path)
    base = probe_ctx.rollout_views[TASK].public.base_commit
    docker = _docker(base)
    ctx = _ctx(prepared, docker, tmp_path)
    docker.eval_log = _eval_log_for(ctx)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(candidate_stage_seconds=30, grading_deadline_seconds=60, cleanup_seconds=5))
    row = await grader.replay_one(IID, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] is None and row["candidate"]["apply_method"] == "noop"
    assert row["image_local_build"] is True and row["image_id_actual"].startswith("sha256:")
    assert row["report"]["outcome"] == "resolved" and row["report"]["reward"] == 1.0
    assert row["classification"]["verdict"] == "projectable" and row["projection"]["included_paths"] == []
    assert row["cleanup"]["removed"] is True and any(n.startswith("rh2-replay-cand-") for n in docker.removed)
    assert row["log"]["path"].endswith(".eval.log") and row["diagnostics_ref"]
    # legacy（无 profile）manager 没有候选段事实；sidecar 里的解析诊断仍在
    g = ctx.grading_views[TASK].grading
    assert row["install"] is None and row["verdict_diagnostics"]["num_parsed_tests"] == len(g.fail_to_pass) + len(g.pass_to_pass)
    assert row["verdict_diagnostics"]["parser_source"].startswith("swegym_parsers@")
    assert row["policy"]["shm_bytes"] == 64 * 1024**2 and row["budgets"]["grading_deadline_seconds"] == 60
    lines = (tmp_path / "ledger.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["task_id"] == TASK
    art_dirs = list((tmp_path / "artifacts").rglob("frozen_patch.json"))
    assert len(art_dirs) == 1 and (art_dirs[0].parent / "baseline_manifest.json").exists()
    assert docker.grade_execs == 1


async def test_apply_check_failure_stops_before_grading(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base, apply_exit_code=1)
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    patch = "diff --git a/moto/x.py b/moto/x.py\n--- a/moto/x.py\n+++ b/moto/x.py\n@@ -1 +1 @@\n-a\n+b\n"
    row = await grader.replay_one(TASK, CandidateInput(kind="cc", origin="unit", patch_text=patch))
    assert row["candidate"]["apply_method"] == "apply_failed" and row["report"] is None
    assert row["candidate"]["patch_sha256"].startswith("sha256:") and "not graded" in row["notes"][0]
    assert docker.grade_execs == 0 and row["cleanup"]["removed"] is True
    assert (tmp_path / "artifacts").rglob("candidate.patch")


async def test_candidate_stage_timeout_records_last_stage_and_cleans_up(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base, init_delay=0.5)
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(candidate_stage_seconds=0.1, grading_deadline_seconds=60, cleanup_seconds=5))
    row = await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] == "candidate_stage_timeout:trusted_init" and row["report"] is None
    assert row["cleanup"]["removed"] is True and docker.grade_execs == 0


async def test_digest_verified_path_without_derived_image(prepared, tmp_path):
    base_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path, derived=False)
    public = base_ctx.rollout_views[TASK].public
    docker = _docker(public.base_commit, repo_digests=(f"{public.image.split(':')[0]}@{public.image_manifest_digest}",))
    ctx = _ctx(prepared, docker, tmp_path, derived=False)
    docker.eval_log = _eval_log_for(ctx)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    row = await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["image_local_build"] is False and row["image_id_actual"] is None
    assert row["stage_error"] is None and row["report"] is not None


async def test_grade_exception_is_recorded_not_raised(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base)
    ctx = _ctx(prepared, docker, tmp_path)

    class BoomManager:
        config = GradingManagerConfig(eval_log_dir=tmp_path / "logs")
        container_records = ()
        regrade_total = 0

        async def grade(self, **kwargs):
            raise RuntimeError("boom")

        def take_grader_phase_timing(self, rid):
            return None

    grader = ReplayGrader(ctx, BoomManager(), ledger_path=tmp_path / "ledger.jsonl")
    row = await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"].startswith("grade_exception:RuntimeError:boom") and row["cleanup"]["removed"] is True
    assert len((tmp_path / "ledger.jsonl").read_text().splitlines()) == 1


def test_export_gold_and_candidate_spec(tmp_path):
    manifest = export_gold_candidates(ingest_dir=INGEST, instance_ids=[IID], out_dir=tmp_path / "gold")
    assert IID in manifest["entries"] and (tmp_path / "gold" / f"{IID}.gold.patch").exists()
    cand = candidate_from_spec(f"gold-dir:{tmp_path / 'gold'}", instance_id=IID)
    assert cand.kind == "gold" and cand.patch_text.startswith("diff --git") and cand.patch_sha256 == manifest["entries"][IID]
    assert candidate_from_spec("noop", instance_id=IID).patch_text is None
    with pytest.raises(ValueError):
        candidate_from_spec("bogus:x", instance_id=IID)
    with pytest.raises(KeyError):
        export_gold_candidates(ingest_dir=INGEST, instance_ids=["nope__nope-1"], out_dir=tmp_path / "gold2")


# ---- §11/§12 修正：I2 清理失败停止本批、I6 取消落账、镜像预拉、正式 profile 组合 ----------------

async def test_i2_cleanup_failure_halts_batch_after_recording(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base)
    ctx = _ctx(prepared, docker, tmp_path)
    docker.eval_log = _eval_log_for(ctx)
    docker.rm_fail_names = {n for n in []}  # 占位：名字在运行时才知道 → 用前缀判断
    original_rm = docker.rm_fail_names

    class RmFail(set):
        def __contains__(self, name):  # 所有候选容器都 rm 失败；grader 容器正常
            return str(name).startswith("rh2-replay-cand-")
    docker.rm_fail_names = RmFail(original_rm)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(cleanup_seconds=2))
    with pytest.raises(ReplayHaltError):
        await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"].startswith("candidate_container_cleanup_failed") and row["report"] is None
    assert row["cleanup"]["removed"] is False and any(s.startswith("kill:") for s in row["cleanup"]["steps"])
    assert docker.grade_execs == 0 and grader.cleanup_failures
    # 持久化先于释放：artifact 已落盘
    assert list((tmp_path / "artifacts").rglob("frozen_patch.json"))


async def test_i6_cancellation_writes_row_then_propagates(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base, init_delay=5.0)
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(cleanup_seconds=2))
    task = asyncio.create_task(grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop")))
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"] == "cancelled:trusted_init" and row["cleanup"]["removed"] is True


async def test_image_pull_uses_its_own_budget(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = DriverFakeDocker(base_commit=base, image_present=False, pull_delay=0.2)
    ctx = _ctx(prepared, docker, tmp_path)
    docker.eval_log = _eval_log_for(ctx)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(candidate_stage_seconds=0.15, image_pull_seconds=5))
    row = await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["image_pull"]["pulled"] is True and row["stage_error"] is None  # 拉镜像 0.2s 没吃掉 0.15s 的候选预算
    slow = DriverFakeDocker(base_commit=base, image_present=False, pull_delay=0.5)
    ctx2 = _ctx(prepared, slow, tmp_path)
    grader2 = ReplayGrader(ctx2, manager, ledger_path=tmp_path / "ledger2.jsonl", budgets=ReplayBudgets(image_pull_seconds=0.1))
    row2 = await grader2.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row2["stage_error"] == "image_pull:timeout" and row2["report"] is None


class DriverProfileFakeDocker(ProfileGraderFakeDocker):
    """正式 grader profile 组合：可信 setup / 权限布置 / 候选段替身 + 候选容器初始化。"""

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec" and "rollout-trusted-init" in str(args[-1]):
            return ExecResult(0, "RH2_INIT_OK=1\nAGENT_UID=54321\nWORKDIR_PRESENT=1\n", "")
        return await super().__call__(*args, input_bytes=input_bytes)


async def test_formal_profile_combination_fills_install_test_and_observations(prepared, tmp_path):
    probe_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path)
    public = probe_ctx.rollout_views[TASK].public
    g = probe_ctx.grading_views[TASK].grading
    install_lines = "RH2_PHASE_START=install\nRH2_TS_INSTALL_START=10.0\nRH2_INSTALL_RC=0\nRH2_TS_INSTALL_END=12.5\nRH2_PHASE_END=install\nRH2_TS_TEST_START=13.0\n"
    body = "".join(f"PASSED {t}\n" for t in [*g.fail_to_pass, *g.pass_to_pass])
    log = install_lines + f"+ : '>>>>> Start Test Output'\n{body}+ : '>>>>> End Test Output'\nRH2_TEST_RC=0\nRH2_TS_TEST_END=20.0\n"
    docker = DriverProfileFakeDocker(base_commit=public.base_commit, image_present=True, eval_log=log)
    n_files = len(set(__import__("repoharness2.grading.manager", fromlist=["patch_touched_paths"]).patch_touched_paths(g.test_patch)))
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": str(n_files), "RH2_SETUP_TEST_FILES": str(n_files)}
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=same\nRH2_OBS_IMPORT_PATH=/testbed/moto/__init__.py\n"
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=make_grader_profile()), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    row = await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] is None and row["report"]["outcome"] == "resolved"
    assert row["install"]["install_rc_last_command"] == 0 and row["install"]["install_seconds"] == 2.5
    # 第四组 P-C（A 线复核 R6）：swe_gym_lite 走政策 v2，grader 应用 delta 前先删可再生缓存目录（一致规范化）
    execs = [str(a[-1]) for a in docker.calls if a and a[0] == "exec"]
    norm = [i for i, sc in enumerate(execs) if "RH2_CACHE_NORMALIZED" in sc]
    write = [i for i, sc in enumerate(execs) if "cat > " in sc and "chmod" in sc]
    assert norm and (not write or norm[0] < write[0])
    assert "-name '__pycache__'" in execs[norm[0]] and "-name '.pytest_cache'" in execs[norm[0]] and "-prune -exec rm -rf -- {} +" in execs[norm[0]]
    assert "-path './.git' -prune -o" in execs[norm[0]]  # CR3：排除命名空间先剪枝
    assert manager.container_records[-1].eval_log_partial is None  # §14.2 余项：日志全文落盘后不再留在记录里
    assert row["test"] == {"rc": 0, "seconds": 7.0}
    assert row["observations"]["RH2_OBS_IMPORT_PATH"] == "/testbed/moto/__init__.py" and row["runner_integrity_changed"] is False
    assert row["policy"]["profile_id"] == make_grader_profile().profile_id and row["log"]["partial"] is False


# ---- §13 修正：R1 持久化失败/清理期间取消仍清理，R3 取消评分的日志引用，R4 镜像预算包住 inspect ----------

async def test_r1_persist_failure_still_removes_container_then_halts(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base)
    ctx = _ctx(prepared, docker, tmp_path)
    (tmp_path / "artifacts").write_text("not a directory")  # 让 mkdir(parents=True) 抛 NotADirectoryError
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    with pytest.raises(ReplayHaltError):
        await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"].startswith("persist_failed:NotADirectoryError") and row["cleanup"]["removed"] is True
    assert any(n.startswith("rh2-replay-cand-") for n in docker.removed) and docker.grade_execs == 0


async def test_r1_cancel_during_cleanup_waits_for_removal_and_records(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    docker = _docker(base, rm_delay=0.6)
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(cleanup_seconds=5))
    task = asyncio.create_task(grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop")))
    await asyncio.sleep(0.3)  # 候选阶段（替身，毫秒级）已结束，此刻正在 rm 里
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"] == "cancelled:cleanup" and row["cleanup"]["removed"] is True
    assert any(n.startswith("rh2-replay-cand-") for n in docker.removed)


async def test_r3_cancelled_grading_row_references_persisted_log(prepared, tmp_path):
    probe_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path)
    public = probe_ctx.rollout_views[TASK].public
    g = probe_ctx.grading_views[TASK].grading
    log = "RH2_INSTALL_RC=0\n+ : '>>>>> Start Test Output'\n" + "".join(f"PASSED {t}\n" for t in [*g.fail_to_pass, *g.pass_to_pass]) + "+ : '>>>>> End Test Output'\n"
    docker = DriverProfileFakeDocker(base_commit=public.base_commit, image_present=True, eval_log=log)
    n_files = len(set(__import__("repoharness2.grading.manager", fromlist=["patch_touched_paths"]).patch_touched_paths(g.test_patch)))
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": str(n_files), "RH2_SETUP_TEST_FILES": str(n_files)}
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=s\n"
    docker.observation_delay = 5.0
    docker.observation_delay_match = "RH2_OBS_IMPORT_PATH"  # 只延迟后观测（v2 前观测脚本没有导入探针）
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=make_grader_profile()), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    task = asyncio.create_task(grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop")))
    await asyncio.sleep(0.5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"] == "cancelled:grading" and row["log"]["path"].endswith(".eval.log") and row["diagnostics_ref"]
    assert "PASSED" in Path(row["log"]["path"]).read_text() and row["install"]["install_rc_last_command"] == 0
    assert row["log"]["partial"] is False  # 接线页 §14.2 余项：候选段已完整结束、后观测期间取消 → 日志完整


async def test_cancel_during_derived_image_inspect_writes_a_row(prepared, tmp_path):
    """接线页 §14.2 余项：派生镜像 inspect 期间被取消也有账本行（此前 row 在 inspect 之后才建立）。"""
    base_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path)
    public = base_ctx.rollout_views[TASK].public
    docker = _docker(public.base_commit, image_inspect_delay=5.0)
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(image_pull_seconds=30.0))
    task = asyncio.create_task(grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop")))
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    row = json.loads((tmp_path / "ledger.jsonl").read_text().splitlines()[-1])
    assert row["stage_error"] == "cancelled:derived_image_inspect" and row["image_local_build"] is True and row["report"] is None


async def test_r4_image_budget_covers_inspect_and_cancel_during_pull(prepared, tmp_path):
    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    slow_inspect = DriverFakeDocker(base_commit=base, image_present=True, image_inspect_delay=0.5)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=slow_inspect)
    # 无派生镜像：`image inspect + pull` 整体受镜像预算约束
    ctx = _ctx(prepared, slow_inspect, tmp_path, derived=False)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl", budgets=ReplayBudgets(image_pull_seconds=0.05))
    row = await grader.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["stage_error"] == "image_pull:timeout" and not any(a[0] == "run" for a in slow_inspect.calls)
    # 派生镜像：其 inspect 同样在预算内，超时落账而不是异常逃出
    ctx_d = _ctx(prepared, slow_inspect, tmp_path)
    grader_d = ReplayGrader(ctx_d, manager, ledger_path=tmp_path / "ledger_d.jsonl", budgets=ReplayBudgets(image_pull_seconds=0.05))
    row_d = await grader_d.replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row_d["stage_error"] == "derived_image:inspect_timeout" and row_d["report"] is None
    slow_pull = DriverFakeDocker(base_commit=base, image_present=False, pull_delay=5.0)
    ctx2 = _ctx(prepared, slow_pull, tmp_path)
    grader2 = ReplayGrader(ctx2, manager, ledger_path=tmp_path / "ledger2.jsonl")
    task = asyncio.create_task(grader2.replay_one(TASK, CandidateInput(kind="noop", origin="noop")))
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    row2 = json.loads((tmp_path / "ledger2.jsonl").read_text().splitlines()[-1])
    assert row2["stage_error"] == "cancelled:image_pull" and not any(a[0] == "run" for a in slow_pull.calls)


# ---- 第四组 P-D：文件变目录经 driver 正常评分；目录变文件仍是 typed 导出错误、不崩溃、容器清理 ----------------

async def test_pd_file_to_dir_candidate_is_graded_and_dir_to_file_is_recorded(prepared, tmp_path):
    import base64
    import hashlib

    base = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path).rollout_views[TASK].public.base_commit
    new = b"{}\n"
    baseline_census = "regular\t100644\t" + hashlib.sha256(b"a=1\n").hexdigest() + "\tconfig\n"
    # file→dir：候选容器基线、post、grader 重建三次 census
    docker = _docker(base)
    docker.census_outputs = [baseline_census, "regular\t100644\t" + hashlib.sha256(new).hexdigest() + "\tconfig/default.json\n", baseline_census]
    docker.fetch_output = "config/default.json\t" + base64.b64encode(new).decode() + "\n"
    ctx = _ctx(prepared, docker, tmp_path)
    docker.eval_log = _eval_log_for(ctx)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    row = await grader.replay_one(TASK, CandidateInput(kind="cc", origin="unit", patch_text="diff --git a/config b/config\n"))
    assert row["stage_error"] is None and row["report"]["outcome"] == "resolved"
    assert row["projection"]["included_paths"] == ["config", "config/default.json"] and row["projection"]["unsupported_shape_reasons"] == []
    assert row["cleanup"]["removed"] is True and docker.grade_execs == 1
    # dir→file：仍是父子前缀冲突 → export 阶段 typed 错误，不评分
    docker2 = _docker(base)
    docker2.census_outputs = ["regular\t100644\t" + hashlib.sha256(b"a=1\n").hexdigest() + "\tconfig/default.json\n",
                              "regular\t100644\t" + hashlib.sha256(new).hexdigest() + "\tconfig\n"]
    docker2.fetch_output = "config\t" + base64.b64encode(new).decode() + "\n"
    ctx2 = _ctx(prepared, docker2, tmp_path)
    grader2 = ReplayGrader(ctx2, manager, ledger_path=tmp_path / "ledger2.jsonl")
    row2 = await grader2.replay_one(TASK, CandidateInput(kind="cc", origin="unit", patch_text="diff --git a/config b/config\n"))
    assert row2["stage_error"].startswith("export:unsupported_delta_shape") and row2["report"] is None
    assert row2["cleanup"]["removed"] is True and docker2.grade_execs == 0


# ---- 第四组 P-D（R5）：必要的祖先删除被控制面排除 → driver 记 projection 阶段错误、不评分 ----------------

async def test_pd_projection_excluded_ancestor_delete_is_recorded_not_graded(prepared, tmp_path):
    import base64
    import hashlib

    probe_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path)
    g = probe_ctx.grading_views[TASK].grading
    official = sorted(__import__("repoharness2.grading.manager", fromlist=["patch_touched_paths"]).patch_touched_paths(g.test_patch))[0]
    base = probe_ctx.rollout_views[TASK].public.base_commit
    docker = _docker(base)
    new = b"{}\n"
    docker.census_outputs = [
        "regular\t100644\t" + hashlib.sha256(b"old\n").hexdigest() + f"\t{official}\n",
        "regular\t100644\t" + hashlib.sha256(new).hexdigest() + f"\t{official}/x.py\n",
    ]
    docker.fetch_output = f"{official}/x.py\t" + base64.b64encode(new).decode() + "\n"
    ctx = _ctx(prepared, docker, tmp_path)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs"), docker=docker)
    grader = ReplayGrader(ctx, manager, ledger_path=tmp_path / "ledger.jsonl")
    row = await grader.replay_one(TASK, CandidateInput(kind="cc", origin="unit", patch_text="diff --git a/x b/x\n"))
    assert row["stage_error"].startswith("projection:unsupported_delta_shape:ancestor_delete_excluded_by_control_plane")
    assert row["report"] is None and row["classification"]["verdict"] == "projectable"
    assert row["projection"]["unsupported_shape_reasons"] and row["cleanup"]["removed"] is True and docker.grade_execs == 0
    assert row["baseline_policy_version"] == "baseline_policy_v2" and row["omitted_cache_count"] is not None


# ---- 第四组 P-A（2026-09-16）：资格账本加载、账本新列、资格随 spec 进 manager ----


async def test_pa_qualification_ledger_round_trip(prepared, tmp_path):
    """gold/noop 成功行（参考缺席 0、带 image_identity/scripts_digest）→ EnvQualification；再次 replay 时资格随 spec 进入 manager，
    账本记录 env_qualification=ok:<来源>；派生镜像下资格因镜像身份不符而无效。"""
    from repoharness2.adapters.slime.replay_grade import load_env_qualifications

    probe_ctx = _ctx(prepared, FakeDocker(base_commit="0" * 40, image_present=True), tmp_path, derived=False)
    public = probe_ctx.rollout_views[TASK].public
    g = probe_ctx.grading_views[TASK].grading
    body = "".join(f"PASSED {t}\n" for t in [*g.fail_to_pass, *g.pass_to_pass])
    log = f"RH2_INSTALL_RC=0\n+ : '>>>>> Start Test Output'\n{body}+ : '>>>>> End Test Output'\nRH2_TEST_RC=0\n"
    docker = DriverProfileFakeDocker(
        base_commit=public.base_commit, image_present=True, eval_log=log,
        repo_digests=(f"{public.image.split(':')[0]}@{public.image_manifest_digest}",),  # 正式 digest 比对路径
    )
    n_files = len(set(__import__("repoharness2.grading.manager", fromlist=["patch_touched_paths"]).patch_touched_paths(g.test_patch)))
    docker.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": str(n_files), "RH2_SETUP_TEST_FILES": str(n_files)}
    ctx = _ctx(prepared, docker, tmp_path, derived=False)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "logs", sandbox_profile=make_grader_profile()), docker=docker)
    ledger = tmp_path / "ledger_gold.jsonl"
    row = await ReplayGrader(ctx, manager, ledger_path=ledger).replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row["report"]["outcome"] == "resolved", row["report"]
    assert row["reference_missing_count"] == 0
    assert row["image_identity"] == public.image_manifest_digest and row["scripts_digest"].startswith("sha256:")
    assert row["env_qualification"] == "absent" and row["execution_failure_decision"] is None
    assert row["report"]["execution_failure_stage"] is None and row["report"]["grading_semantics"] == "swe_f2p_p2p"

    quals = load_env_qualifications([ledger, tmp_path / "missing.jsonl"])
    assert list(quals) == [TASK]
    q = quals[TASK]
    assert q.image_identity == row["image_identity"] and q.scripts_digest == row["scripts_digest"] and q.reference_missing_count == 0
    assert q.source == f"ledger_gold.jsonl:{row['report']['report_id']}" and q.install_rc_last_command == 0

    # cc 候选行 / infra 行 / 旧账本行（无 digest 列）都不算资格
    old_rows = [
        {**row, "candidate": {**row["candidate"], "kind": "cc"}},
        {**row, "report": {**row["report"], "outcome": "failed_to_grade", "failure_category": "infra_failure"}},
        {k: v for k, v in row.items() if k not in ("image_identity", "scripts_digest")},
    ]
    other = tmp_path / "ledger_other.jsonl"
    other.write_text("".join(json.dumps(r, default=str) + "\n" for r in old_rows), encoding="utf-8")
    assert load_env_qualifications([other]) == {}

    ctx_q = load_context(
        prepared_dir=prepared["prepared"], private_dir=prepared["private"], manifest_sha256=prepared["sha"],
        rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(), artifacts_dir=tmp_path / "artifacts2",
        run_id="t2", docker=docker, qualifications=quals,
    )
    row2 = await ReplayGrader(ctx_q, manager, ledger_path=tmp_path / "ledger_2.jsonl").replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    assert row2["env_qualification"] == f"ok:{q.source}"
    ctx_d = load_context(
        prepared_dir=prepared["prepared"], private_dir=prepared["private"], manifest_sha256=prepared["sha"],
        rollout_profile=make_rollout_profile(), grader_profile=make_grader_profile(), artifacts_dir=tmp_path / "artifacts3",
        run_id="t3", docker=docker, qualifications=quals, derived_image=DerivedImage(ref="local/derived:test", recipe="fixture"),
    )
    row3 = await ReplayGrader(ctx_d, manager, ledger_path=tmp_path / "ledger_3.jsonl").replay_one(TASK, CandidateInput(kind="noop", origin="noop"))
    # R5-P2：派生镜像的资格键用实际 image ID（inspect -f {{.Id}}），不是可重指的 tag
    assert row3["env_qualification"] == "image_identity_mismatch" and row3["image_identity"] == "local_build:sha256:" + "ab" * 32
    assert row3["image_id_actual"] == "sha256:" + "ab" * 32
