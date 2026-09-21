"""F2（codex Wave3 复核）grader profile 路径的替身测试（不需要 docker）：

- 顺序：root 写/跑 trusted setup → root 权限布置（marker 脚本，chown -R 后收回 official 文件与祖先目录）
  → root 写候选脚本 → **候选 uid** 跑测试；日志 = setup 段 + 测试段；
- `grader_trusted_setup` 与 `test` 分开计时（GradingTimingRecord.test_seconds 不含 setup）；
- 评分材料没有拆分脚本 → SandboxProfileViolation（run-halt 通道），容器已移除；
- legacy（无 profile）路径：仍以 root 跑完整 eval_script，参数形状逐字不变。
"""

from __future__ import annotations

import json

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from grading_fixtures import (
    FIXTURE_HYGIENE,
    GOOD_FAKE_LOG,
    GOOD_PATCH,
    FakeDocker,
    FakeWorkspace,
    make_fixture_spec,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import ProfileFakeState, make_grader_profile  # noqa: E402

from repoharness2.adapters.slime.sandbox_profile import (  # noqa: E402
    GRADER_TRUSTED_SETUP_ATTEST_PATH,
    script_id_of,
)
from repoharness2.grading.manager import (  # noqa: E402
    ExecResult,
    GradingManagerConfig,
    GradingScopeTerminationError,
    SandboxProfileViolation,
    SWEGradingManager,
)

BASE_COMMIT = "a" * 40
SETUP_LOG = "+ git checkout base -- tests/\nRH2_SETUP_RAN=1\n"
# root 可信 setup 写进自证文件的默认内容（正常任务：1 个 official test 文件，apply 成功）
GOOD_SETUP_ATTEST = {
    "RH2_SETUP_APPLY_RC": "0",
    "RH2_SETUP_RESTORED": "1",
    "RH2_SETUP_EXPECTED_TEST_FILES": "1",
    "RH2_SETUP_TEST_FILES": "1",
    "RH2_SETUP_ABSENT_TEST_FILES": "0",
    "RH2_SETUP_IRREGULAR_TEST_FILES": "",
    "RH2_SETUP_OK": "1",
}


@dataclass
class ProfileGraderFakeDocker(FakeDocker):
    """tests/grading FakeDocker + profile 路径命令（裸 inspect / marker 脚本 / trusted_setup 段 / 自证读回）。

    F2 负例旋钮：``setup_exit_code`` = 可信 setup 脚本的退出码；``setup_attest`` = 自证文件内容
    （None 表示文件根本不存在——脚本半路 exit，自证从未写出）。
    """

    profile_fake: ProfileFakeState = field(
        default_factory=lambda: ProfileFakeState(head=BASE_COMMIT, grader_profile=make_grader_profile())
    )
    exec_sequence: list[tuple[str | None, str]] = field(default_factory=list)  # (user, 描述)
    setup_exit_code: int = 0
    setup_attest: dict[str, str] | None = field(default_factory=lambda: dict(GOOD_SETUP_ATTEST))

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec":
            user = args[args.index("-u") + 1] if "-u" in args else None
            script = args[-1]
            sid = script_id_of(script)
            desc = sid or ("trusted_setup_run" if ".trusted_setup 2>&1" in script else
                           "setup_attest_read" if script.startswith(f"cat {GRADER_TRUSTED_SETUP_ATTEST_PATH}") else
                           "candidate_test_run" if script.startswith("bash ") and "2>&1" in script else
                           "write_script" if "cat > " in script else "other")
            self.exec_sequence.append((user, desc))
            if desc == "trusted_setup_run":
                self.calls.append(args)
                return ExecResult(self.setup_exit_code, SETUP_LOG, "")
            if desc == "setup_attest_read":
                self.calls.append(args)
                if self.setup_attest is None:
                    return ExecResult(1, "", "")
                return ExecResult(0, "".join(f"{k}={v}\n" for k, v in self.setup_attest.items()), "")
        handled = self.profile_fake.dispatch(args, input_bytes)
        if handled is not None:
            self.calls.append(args)
            return handled
        return await super().__call__(*args, input_bytes=input_bytes)


def _ran_candidate_test(docker: ProfileGraderFakeDocker) -> bool:
    return any(desc == "candidate_test_run" for _, desc in docker.exec_sequence)


def _manager(docker: FakeDocker, *, profile=True) -> SWEGradingManager:
    return SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile() if profile else None), docker=docker,
    )


def _spec(**overrides):
    return make_fixture_spec(BASE_COMMIT, "fake-image:v1", checkout_mode="image_embedded", **overrides)


async def test_profile_path_runs_root_setup_then_protect_then_candidate_test_and_merges_logs(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
    )
    report = await manager.grade(trajectory_id="t-split", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())
    assert report.outcome == "resolved" and report.reward == 1.0
    seq = docker.exec_sequence
    # 关键顺序与身份：trusted setup（root）→ 权限布置（root，marker）→ 候选脚本写入（root）→ 候选测试（uid 54322）
    idx_setup = seq.index((None, "trusted_setup_run"))
    idx_protect = seq.index((None, "grader-protect-control-surface"))
    idx_test = seq.index((str(make_grader_profile().candidate_exec_uid), "candidate_test_run"))
    assert idx_setup < idx_protect < idx_test
    assert all(user is None for user, desc in seq if desc in ("trusted_setup_run", "grader-protect-control-surface", "write_script"))
    # 日志 = setup 段 + 测试段，parser 仍按官方标记解析
    log = (tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
    assert log.startswith(SETUP_LOG) and ">>>>> Start Test Output" in log
    record = manager.container_records[-1]
    assert record.control_surface["RH2_PROTECT_OK"] == "1"
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    assert phase.segments["grader_trusted_setup"] is not None and phase.segments["test"] is not None
    assert report.timings.test_seconds == pytest.approx(phase.segments["test"], abs=1e-3)


async def test_profile_path_requires_split_scripts_else_run_halt_and_container_removed():
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT)
    manager = _manager(docker)
    with pytest.raises(SandboxProfileViolation, match="grader_eval_split_required"):
        await manager.grade(
            trajectory_id="t-nosplit", workspace=FakeWorkspace(GOOD_PATCH),
            spec=_spec(trusted_setup_script=None, candidate_test_script=None),
        )
    assert all(r.removed for r in manager.container_records) and manager.container_records
    assert not any(desc == "candidate_test_run" for _, desc in docker.exec_sequence)


async def test_legacy_path_without_profile_runs_whole_eval_script_as_root_unchanged():
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    manager = _manager(docker, profile=False)
    report = await manager.grade(trajectory_id="t-legacy", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())
    assert report.outcome == "resolved"
    assert not any(desc in ("trusted_setup_run", "grader-protect-control-surface") for _, desc in docker.exec_sequence)
    assert (None, "candidate_test_run") in docker.exec_sequence  # 整段 eval 以 root（无 -u）执行
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    assert phase.segments["grader_trusted_setup"] == 0.0


# ---------------------------------------------------------------------------
# codex Wave3 §9.2 反例：setup / 权限布置任一判据不达标，都不许启动候选测试、不许产生 0/1 reward
# ---------------------------------------------------------------------------


async def _graded_with(tmp_path, docker: ProfileGraderFakeDocker, **spec_overrides):
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
    )
    report = await manager.grade(
        trajectory_id="t-f2-neg", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec(**spec_overrides),
    )
    return manager, report


def _assert_typed_infra_no_reward(manager, report, docker, *, detail_contains: str) -> None:
    """反例共同断言：typed grading-infra 处置（reward 不可得）+ 零候选测试执行 + 计时/审计留痕。"""

    assert report.outcome == "failed_to_grade" and report.reward is None
    assert report.failure_category == "infra_failure"
    assert detail_contains in report.infra_failure_detail, report.infra_failure_detail
    assert not _ran_candidate_test(docker), docker.exec_sequence
    # root 可信 setup 段照记（被判据挡下的那次也要在计时里看得见）
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    assert phase.segments["grader_trusted_setup"] is not None
    assert phase.segments["test"] is None and report.timings.test_seconds == 0.0
    # 原始输出留在审计面：setup 段日志落盘，自证事实挂在容器记账条目上
    assert report.eval_log_ref is not None
    assert SETUP_LOG in (Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.eval.log").read_text()


async def test_f2_trusted_setup_nonzero_exit_blocks_candidate_test_and_is_typed_infra(tmp_path):
    """反例 (a)：official test_patch 应用失败（setup 非零退出、自证文件只有失败原因），
    而候选测试脚本本来会打印一份"全过"的日志——必须零候选测试执行、零 0/1 reward。"""

    docker = ProfileGraderFakeDocker(
        base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG, setup_exit_code=17,
        setup_attest={**GOOD_SETUP_ATTEST, "RH2_SETUP_APPLY_RC": "1",
                      "RH2_SETUP_OK": "", "RH2_SETUP_ERROR": "official_test_patch_apply_failed:1"},
    )
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(manager, report, docker, detail_contains="grading_trusted_setup_failed:setup_exit_code")
    assert manager.container_records[-1].trusted_setup["RH2_SETUP_APPLY_RC"] == "1"
    assert manager.container_records[-1].control_surface is None  # 权限布置都没开始


async def test_f2_trusted_setup_attest_missing_blocks_candidate_test(tmp_path):
    """setup 退出码为 0，但自证文件根本没写出（脚本被改坏/半路退出）：仍然不许跑候选测试。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG, setup_attest=None)
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(manager, report, docker, detail_contains="grading_trusted_setup_failed:setup_not_attested")


async def test_f2_trusted_setup_official_test_file_list_mismatch_blocks_candidate_test(tmp_path):
    """自证里的 official test 清单数量与评分 spec 的 hygiene.test_files 不符 = 脚本与 spec 分家，拒。"""

    docker = ProfileGraderFakeDocker(
        base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG,
        setup_attest={**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": "2"},
    )
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(
        manager, report, docker, detail_contains="grading_trusted_setup_failed:official_test_file_list_mismatch"
    )


async def test_f2_protect_reporting_zero_protected_and_missing_file_blocks_candidate_test(tmp_path):
    """反例 (b1)：权限脚本如实报出 `PROTECTED_FILES=0` / `MISSING_FILES=tests/test_thing.py,`
    却仍写 `RH2_PROTECT_OK=1`（codex 复核里的原样反例）——manager 按 setup 自证的在位数比对后必须拒。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    docker.profile_fake.protect_facts_override = {
        "PROTECTED_FILES": "0", "MISSING_FILES": "tests/test_thing.py,", "MISSING_FILES_COUNT": "1",
    }
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(
        manager, report, docker, detail_contains="grading_control_surface_protect_failed:official_test_file_missing"
    )
    assert manager.container_records[-1].control_surface["MISSING_FILES"] == "tests/test_thing.py,"


async def test_f2_protect_claiming_more_protected_files_than_setup_saw_blocks_candidate_test(tmp_path):
    """权限脚本报出的受保护数比可信 setup 数出的在位数还多（凭空多保护了一个）：两侧事实分家，拒。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    docker.profile_fake.protect_facts_override = {"PROTECTED_FILES": "2"}
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(
        manager, report, docker, detail_contains="grading_control_surface_protect_failed:protected_count_mismatch"
    )


async def test_f2_protect_reporting_symlink_official_test_file_blocks_candidate_test(tmp_path):
    """反例 (b2)：official test 文件是 symlink（保护住 symlink 本身不等于保护住被执行的测试）——拒。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    docker.profile_fake.protect_facts_override = {
        "PROTECTED_FILES": "0", "IRREGULAR_FILES": "tests/test_thing.py,",
    }
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(
        manager, report, docker, detail_contains="grading_control_surface_protect_failed:official_test_file_not_regular"
    )


async def test_f2_protect_expected_count_mismatch_blocks_candidate_test(tmp_path):
    """权限脚本内嵌的 official test 清单与评分 spec 的清单数量不符：脚本与 spec 分家，拒。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    docker.profile_fake.protect_facts_override = {"EXPECTED_FILES": "3"}
    manager, report = await _graded_with(tmp_path, docker)
    _assert_typed_infra_no_reward(
        manager, report, docker, detail_contains="grading_control_surface_protect_failed:official_test_file_list_mismatch"
    )


async def test_f2_official_test_path_missing_after_setup_blocks_candidate_test(tmp_path):
    """codex Wave3 §10.2 纠正：official patch 删除/改名导致清单里某个路径在 setup 之后不在位时，
    **不再放行**。理由是 sticky 祖先目录只挡"改写/删除已存在条目"，挡不住候选在这个缺失的名字上
    新建文件，而候选测试命令又会把旧路径一起传给 runner——真 Docker 反例见
    `test_w3b_grader_profile_docker.py::test_f2_missing_official_path_is_recreatable_by_candidate_so_grading_stops_first`。"""

    docker = ProfileGraderFakeDocker(
        base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG,
        setup_attest={**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": "2",
                      "RH2_SETUP_TEST_FILES": "1", "RH2_SETUP_ABSENT_TEST_FILES": "1"},
    )
    docker.profile_fake.protect_facts_override = {
        "PROTECTED_FILES": "1", "MISSING_FILES": "tests/test_gone.py,", "MISSING_FILES_COUNT": "1",
    }
    hygiene = FIXTURE_HYGIENE.__class__(
        test_files=("tests/test_thing.py", "tests/test_gone.py"),
        test_globs=FIXTURE_HYGIENE.test_globs, forbidden_globs=FIXTURE_HYGIENE.forbidden_globs,
    )
    manager, report = await _graded_with(tmp_path, docker, hygiene=hygiene)
    _assert_typed_infra_no_reward(
        manager, report, docker,
        detail_contains="grading_trusted_setup_failed:official_test_file_missing_after_setup",
    )


# ---------------------------------------------------------------------------
# Codex 复核 R2 余项：prelaunch 失败分支不再自己做无 timeout 的 rm——容器由 _start_container 有界收口
# ---------------------------------------------------------------------------


def _rm_hanging_docker(fake: ProfileGraderFakeDocker, *, inspect_unknown: bool, hang_times: int = 1):
    """替身：前 hang_times 次 `rm` 挂起直到被取消（模拟 Docker 卡住）；inspect_unknown=True 时状态查询报 daemon 不可达。"""

    state = {"rm_calls": 0, "cancelled": 0}

    async def docker(*args, input_bytes=None):
        if args[0] == "rm":
            state["rm_calls"] += 1
            if state["rm_calls"] <= hang_times:
                try:
                    await asyncio.sleep(3600)
                except asyncio.CancelledError:
                    state["cancelled"] += 1
                    raise
        if inspect_unknown and args[0] == "inspect" and "{{.State.Running}}" in args:
            return ExecResult(1, "", "Cannot connect to the Docker daemon at unix:///var/run/docker.sock")
        return await fake(*args, input_bytes=input_bytes)

    return docker, state


async def test_trusted_init_failure_is_still_a_profile_violation_and_the_container_is_closed_by_the_owner():
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT)
    docker.profile_fake.trusted_init_fail = True
    manager = _manager(docker)
    with pytest.raises(SandboxProfileViolation, match="grader_trusted_init_failed"):
        await manager.grade(trajectory_id="t-init-fail", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())
    (record,) = manager.container_records
    assert record.removed is True and manager.cleanup_failures == [] and manager.regrade_total == 0
    assert not any(desc == "candidate_test_run" for _, desc in docker.exec_sequence)


async def test_trusted_init_failure_with_hanging_rm_ends_within_the_cleanup_budget_as_run_fatal():
    """Codex 复核反例：可信初始化失败后第一次 rm 卡住。此前该 rm 无 timeout、异常到不了外层、worker 一直占槽；现在由
    _start_container 的有界收口接管：rm 在独立清理预算（1s）内被切断，预算随之耗尽 = 状态无法确认（D-2 合同）→
    GradingScopeTerminationError（run-fatal）替换 profile 违规，记录保留、close() 仍能再次清理。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT)
    docker.profile_fake.trusted_init_fail = True
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), cleanup_timeout_seconds=1), docker=docker,
    )
    manager._docker, state = _rm_hanging_docker(docker, inspect_unknown=False)
    started = time.monotonic()
    with pytest.raises(GradingScopeTerminationError):
        await asyncio.wait_for(
            manager.grade(trajectory_id="t-init-rm-hang", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec()), timeout=5
        )
    elapsed = time.monotonic() - started
    assert 0.9 <= elapsed < 3.0, elapsed  # = 清理预算，不是无限等待
    (record,) = manager.container_records
    assert record.removed is False and state["cancelled"] == 1
    assert any(f.startswith("container_rm_timeout:") for f in manager.cleanup_failures)
    assert any("container_scope_termination_failed" in f for f in manager.cleanup_failures)
    close = await manager.close()  # 记录仍在：关停 gc 的第二次 rm（替身不再挂起）完成清理
    assert close["containers_removed"] == [record.name] and close["containers_open"] == []


async def test_trusted_init_failure_with_hanging_rm_and_unknown_state_is_run_fatal_within_the_budget():
    """rm 卡住且状态无法确认：清理预算耗尽后 GradingScopeTerminationError（run-fatal）替换 profile 违规，记录保留供后续清理。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT)
    docker.profile_fake.trusted_init_fail = True
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), cleanup_timeout_seconds=1), docker=docker,
    )
    manager._docker, state = _rm_hanging_docker(docker, inspect_unknown=True, hang_times=1)
    started = time.monotonic()
    with pytest.raises(GradingScopeTerminationError):
        await asyncio.wait_for(
            manager.grade(trajectory_id="t-init-rm-unknown", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec()), timeout=5
        )
    assert time.monotonic() - started < 3.0
    (record,) = manager.container_records
    assert record.removed is False and state["cancelled"] == 1
    assert any("container_scope_termination_failed" in f for f in manager.cleanup_failures)
    assert (await manager.close())["containers_open"] == []  # 记录仍在：关停 gc 再次清理（替身此时不再挂起）


async def test_prelaunch_check_violation_is_still_raised_and_the_container_is_closed_by_the_owner():
    """R2 余项第二个分支：prelaunch 检查不合格（探针报候选身份是 root）→ SandboxProfileViolation 照常上抛，
    容器由 _start_container 的有界收口删除；分支内不再有无 timeout 的 rm。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT)
    docker.profile_fake.grader_probe_overrides = {"UID": "0"}
    manager = _manager(docker)
    with pytest.raises(SandboxProfileViolation, match="grader_sandbox_profile_violation"):
        await manager.grade(trajectory_id="t-probe-violation", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())
    (record,) = manager.container_records
    assert record.removed is True and manager.cleanup_failures == [] and manager.regrade_total == 0
    assert record.prelaunch is not None and not record.prelaunch["ok"]  # 核对摘要仍留档
    assert not any(desc == "candidate_test_run" for _, desc in docker.exec_sequence)



# ---- S1-m（评分接线 2026-09-15）：候选段事实、root 观测、超时保留部分输出、诊断 sidecar ----------------

_CANDIDATE_LOG_WITH_FACTS = (
    "+ echo RH2_PHASE_START=install\nRH2_PHASE_START=install\nRH2_TS_INSTALL_START=100.0\n"
    "RH2_INSTALL_RC=2\nRH2_TS_INSTALL_END=103.5\nRH2_PHASE_END=install\n"
    "RH2_TS_TEST_START=104.0\n+ : '>>>>> Start Test Output'\n"
    "PASSED tests/test_thing.py::test_feature\nPASSED tests/test_thing.py::test_stable\n"
    "+ : '>>>>> End Test Output'\nRH2_TS_TEST_END=110.25\n"
)


async def test_s1m_candidate_facts_observations_and_sidecar(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_CANDIDATE_LOG_WITH_FACTS)
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=abc\nRH2_OBS_IMPORT_PATH=/testbed/src/thing.py\nnoise\n"
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
    )
    report = await manager.grade(
        trajectory_id="s1m-facts", workspace=FakeWorkspace(patch_text=GOOD_PATCH),
        spec=_spec(pre_candidate_observation_script="echo RH2_OBS_RUNNER_DIGEST=abc",
                   post_candidate_observation_script="echo RH2_OBS_RUNNER_DIGEST=abc"),
    )
    assert report.outcome == "resolved"
    rec = manager.container_records[-1]
    assert rec.candidate_facts == {
        "install_rc_last_command": 2, "install_failed_commands": [], "install_skipped": False, "install_seconds": 3.5, "test_rc": None, "test_seconds": 6.25,
        "markers_seen": ["RH2_INSTALL_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"],
        "log_partial": False, "candidate_exec_exit_code": 0, "candidate_segment_completed": True,
    }
    assert rec.observations["RH2_OBS_RUNNER_DIGEST_PRE"] == "abc" and rec.observations["RH2_OBS_RUNNER_DIGEST"] == "abc"
    assert rec.observations["RH2_OBS_IMPORT_PATH"] == "/testbed/src/thing.py"
    side = json.loads((tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["candidate"]["install_rc_last_command"] == 2 and side["runner_integrity_changed"] is False
    assert side["verdict"]["num_parsed_tests"] == 2 and side["peak_memory_unavailable_or_zero"] is False
    # 候选命令仍以候选用户执行且把输出 tee 到候选属主文件
    cand = [a for a in docker.calls if a and a[0] == "exec" and "-u" in a and str(a[-1]).startswith("bash ")]
    assert cand and "| tee /rh2/candidate/eval.log; exit ${PIPESTATUS[0]}" in cand[-1][-1]


_KILLED_MID_TEST_LOG = (
    "RH2_PHASE_START=install\nRH2_TS_INSTALL_START=100.0\nRH2_INSTALL_RC=0\nRH2_TS_INSTALL_END=103.5\nRH2_PHASE_END=install\n"
    "RH2_TS_TEST_START=104.0\n+ : '>>>>> Start Test Output'\nPASSED tests/test_thing.py::test_feature\n"
)  # 没有 End 标记、RH2_TEST_RC、RH2_TS_TEST_END：脚本没跑到结尾


async def test_candidate_exec_killed_by_signal_is_recorded_as_interrupted_even_when_inspect_still_says_running(tmp_path):
    """2026-09-19 真机：评分容器被另一个 manager `rm -f`，exec 以 137 返回；删除尚未完成时 inspect 仍报 running，
    `_exec_bash_checked` 的"容器已死"检测落空，截断日志被当成完整日志——sidecar 写 log_partial=false、测试退出码
    缺失，报告落到 parser 的 official_bad_codes。候选段是否跑完现在看日志里的收口事实（RH2_TEST_RC / RH2_TS_TEST_END）与 exec 退出码。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_KILLED_MID_TEST_LOG, eval_exit_code=137)
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
    )
    report = await manager.grade(trajectory_id="killed-mid-test", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_spec())
    assert report.outcome == "failed_to_grade" and report.reward is None and report.failure_category == "infra_failure"
    assert report.infra_failure_detail == "grading_candidate_exec_killed:signal=9:candidate_phase=test"
    side = json.loads((tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["candidate"]["log_partial"] is True and side["candidate"]["candidate_exec_exit_code"] == 137
    assert side["candidate"]["candidate_segment_completed"] is False and side["candidate"]["test_rc"] is None
    log = (tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
    assert "PASSED tests/test_thing.py::test_feature" in log  # 已产生的输出保留
    assert manager.regrade_total == 0 and manager.container_records[-1].removed is True  # 不追加评分；自己的容器照常回收


async def test_container_found_dead_after_exec_keeps_the_exit_code_and_output_the_exec_channel_delivered(tmp_path):
    """同一事故的另一支：exec 返回后 inspect 已看到容器停止 / 不在（既有 grading_container_killed_during_test）。
    容器不在了，tee 文件读不回（替身：读回为空）——此前这里只剩 setup 日志、candidate_phase=unknown、退出码不记。
    现在用 exec 通道已交付的输出与退出码。"""

    docker = ProfileGraderFakeDocker(
        base_commit=BASE_COMMIT, eval_log=_KILLED_MID_TEST_LOG, eval_exit_code=137, container_running=False,
    )
    docker.candidate_partial_log = ""
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
    )
    report = await manager.grade(trajectory_id="dead-after-exec", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_spec())
    assert report.outcome == "failed_to_grade" and report.reward is None and report.failure_category == "infra_failure"
    assert report.infra_failure_detail == "grading_container_killed_during_test:candidate_phase=test"
    facts = manager.container_records[-1].candidate_facts
    assert (facts["log_partial"], facts["candidate_segment_completed"], facts["candidate_exec_exit_code"]) == (True, False, 137)
    assert facts["install_rc_last_command"] == 0 and facts["test_rc"] is None
    log = (tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
    assert "PASSED tests/test_thing.py::test_feature" in log


@pytest.mark.parametrize(
    ("log", "exit_code", "partial", "completed", "killed"),
    [
        # 测试进程被杀、脚本自己正常收尾（RH2_TEST_RC=137 + END 标记）：候选段是完整的，走既有解析路径
        (_KILLED_MID_TEST_LOG + "+ : '>>>>> End Test Output'\nRH2_TEST_RC=137\nRH2_TS_TEST_END=110.0\n", 0, False, True, False),
        # fixture 形态的脚本只打 RH2_TEST_RC、不打末行时间戳：收口事实在场即完整（真实 Docker fixture 即此形态）
        (_KILLED_MID_TEST_LOG + "+ : '>>>>> End Test Output'\nRH2_TEST_RC=0\n", 0, False, True, False),
        # 脚本以普通非零码提前结束（不是信号）：事实如实记未完成，判定仍走既有 parser 路径
        (_KILLED_MID_TEST_LOG, 3, True, False, False),
        # 任何输出之前就被杀
        ("", 137, True, None, True),
    ],
)
async def test_candidate_segment_completion_comes_from_log_markers_and_the_real_exit_code(tmp_path, log, exit_code, partial, completed, killed):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log, eval_exit_code=exit_code)
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker,
    )
    report = await manager.grade(trajectory_id="segment-facts", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_spec())
    facts = manager.container_records[-1].candidate_facts
    assert (facts["log_partial"], facts["candidate_segment_completed"], facts["candidate_exec_exit_code"]) == (partial, completed, exit_code)
    assert report.reward is None or completed  # 没跑完的候选段从不产出 reward
    assert ("grading_candidate_exec_killed" in (report.infra_failure_detail or "")) is killed


async def test_s1m_timeout_keeps_partial_candidate_output(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log="never returned", eval_delay=2.0)
    docker.candidate_partial_log = "RH2_PHASE_START=install\nRH2_INSTALL_RC=0\nRH2_TS_TEST_START=1.0\n+ : '>>>>> Start Test Output'\n"
    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs", cleanup_timeout_seconds=5),
        docker=docker,
    )
    report = await manager.grade(
        trajectory_id="s1m-timeout", workspace=FakeWorkspace(patch_text=GOOD_PATCH),
        spec=_spec(test_timeout_seconds=0.2),
    )
    assert report.outcome == "failed_to_grade" and report.reward is None
    assert "grading_test_timeout_after_0s" in (report.infra_failure_detail or "")
    assert report.infra_failure_detail.endswith(":candidate_phase=install")  # A2：部分日志只有安装段开始标记
    log = (tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.eval.log").read_text()
    assert "RH2_INSTALL_RC=0" in log and "RH2_PHASE_START=install" in log
    side = json.loads((tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["candidate"]["log_partial"] is True and side["candidate"]["install_rc_last_command"] == 0
    assert side["candidate"]["test_seconds"] is None and side["verdict"] is None


async def test_s1m_observation_failure_is_recorded_not_fatal(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_CANDIDATE_LOG_WITH_FACTS)
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=x\n"
    docker.observation_exit_code = 3
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=docker)
    report = await manager.grade(
        trajectory_id="s1m-obs-fail", workspace=FakeWorkspace(patch_text=GOOD_PATCH),
        spec=_spec(post_candidate_observation_script="echo RH2_OBS_RUNNER_DIGEST=x; exit 3"),
    )
    assert report.outcome == "resolved"
    obs = manager.container_records[-1].observations
    assert obs["RH2_OBS_ERROR"].startswith("post_candidate_observation:exit=3") and obs["RH2_OBS_RUNNER_DIGEST"] == "x"


def test_s1m_candidate_facts_parser_ignores_trace_and_missing():
    from repoharness2.grading.manager import candidate_facts_from_log

    assert candidate_facts_from_log("+ echo RH2_INSTALL_RC=7\n") == {
        "install_rc_last_command": None, "install_failed_commands": [], "install_skipped": False, "install_seconds": None,
        "test_rc": None, "test_seconds": None, "markers_seen": [],
    }
    # 2026-09-19：安装段 ERR trap 的失败命令行（`+ ` 回显不算；上限 20 条）
    facts = candidate_facts_from_log("+ echo RH2_INSTALL_CMD_FAILED=2 make init\nRH2_INSTALL_CMD_FAILED=2 make init\nRH2_INSTALL_CMD_FAILED=127 pdm add pre-commit\nRH2_INSTALL_RC=2\n")
    assert facts["install_failed_commands"] == [{"rc": 2, "cmd": "make init"}, {"rc": 127, "cmd": "pdm add pre-commit"}] and facts["install_rc_last_command"] == 2
    assert candidate_facts_from_log("RH2_INSTALL_SKIPPED=1\nRH2_INSTALL_RC=9\nRH2_INSTALL_RC=1\n")["install_rc_last_command"] == 9


# ---- §11/§12 修正（2026-09-15）：I1 观测以候选身份、I5 零解析保留诊断、I7 测试 RC、A2/A3 ----------------

async def test_i1_observation_scripts_run_as_candidate_user(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_CANDIDATE_LOG_WITH_FACTS)
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=d\n"
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=docker)
    await manager.grade(
        trajectory_id="i1", workspace=FakeWorkspace(patch_text=GOOD_PATCH),
        spec=_spec(pre_candidate_observation_script="echo RH2_OBS_RUNNER_DIGEST=d", post_candidate_observation_script="echo RH2_OBS_RUNNER_DIGEST=d"),
    )
    obs_execs = [a for a in docker.calls if a and a[0] == "exec" and "RH2_OBS_" in str(a[-1])]
    assert len(obs_execs) == 2
    for a in obs_execs:
        assert "-u" in a and a[a.index("-u") + 1] == str(make_grader_profile().candidate_exec_uid) and "HOME=/home/rh2grader" in " ".join(a)


async def test_i5_zero_parsed_keeps_parser_diagnostics_in_sidecar(tmp_path):
    log = "+ : '>>>>> Start Test Output'\nno tests collected\n+ : '>>>>> End Test Output'\nPASSED tests/test_thing.py::test_feature\n"
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker)
    from repoharness2.envpack import scoring as _scoring
    from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
    from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1, derive_eval_cmd
    g = PrivateGradingBundleV2(
        instance_id="getmoto__moto-0001", repo="getmoto/moto", repo_key_lower="getmoto/moto", version="5.0", base_commit="a" * 40,
        test_patch="diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ b/tests/t.py\n+x\n",
        fail_to_pass=["tests/test_thing.py::test_feature"], pass_to_pass=[],
        eval_cmd=derive_eval_cmd(SPEC_VENDOR_ID_SWEGYM_242429C1, "getmoto/moto", "5.0"), spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1,
    )
    report = await manager.grade(
        trajectory_id="i5", workspace=FakeWorkspace(patch_text=GOOD_PATCH),
        spec=_spec(parse_log=lambda text: _scoring.parse_eval_log_v2(g, text)),
    )
    assert report.outcome == "failed_to_grade" and report.failure_category == "test_log_parse_failed" and report.reward is None
    side = json.loads((tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["verdict"]["num_parsed_tests"] == 0 and side["verdict"]["num_parsed_outside_segment"] == 1
    assert side["verdict"]["reference_missing"] == ["tests/test_thing.py::test_feature"]


def test_i7_and_a2_candidate_fact_helpers():
    from repoharness2.grading.manager import candidate_facts_from_log, candidate_phase_at

    facts = candidate_facts_from_log("RH2_INSTALL_RC=0\nRH2_TEST_RC=5\n")
    assert facts["test_rc"] == 5 and facts["install_rc_last_command"] == 0
    assert candidate_phase_at("RH2_PHASE_START=install\nfoo") == "install"
    assert candidate_phase_at("RH2_PHASE_START=install\nRH2_PHASE_END=install\n") == "test"
    assert candidate_phase_at("RH2_INSTALL_SKIPPED=1\n") == "test" and candidate_phase_at("") == "unknown"


async def test_a3_partial_log_read_refuses_symlink_and_ignores_deadline(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log="never", eval_delay=2.0)
    docker.candidate_partial_log = "RH2_PARTIAL_LOG_UNAVAILABLE=irregular_or_missing\n"
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs", cleanup_timeout_seconds=5), docker=docker)
    report = await manager.grade(trajectory_id="a3", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_spec(test_timeout_seconds=0.2))
    assert report.outcome == "failed_to_grade"
    reads = [a for a in docker.calls if a and a[0] == "exec" and "cat /rh2/candidate/eval.log" in str(a[-1])]
    assert reads and "[ ! -L /rh2/candidate/eval.log ]" in reads[-1][-1]
    side = json.loads((tmp_path / "logs" / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["candidate"]["log_partial"] is True and side["candidate"]["markers_seen"] == []
    assert report.infra_failure_detail.endswith(":candidate_phase=unknown")


# ---- §13 修正（2026-09-15）：R3 取消后的日志/诊断落盘 ----------------------------------------

async def test_r3_cancel_during_post_observation_persists_full_log(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_CANDIDATE_LOG_WITH_FACTS)
    docker.observation_stdout = "RH2_OBS_RUNNER_DIGEST=x\n"
    docker.observation_delay = 5.0
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=docker)
    task = asyncio.create_task(manager.grade(
        trajectory_id="r3-postobs", workspace=FakeWorkspace(patch_text=GOOD_PATCH),
        spec=_spec(post_candidate_observation_script="echo RH2_OBS_RUNNER_DIGEST=x"),
    ))
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    rec = manager.container_records[-1]
    assert rec.cancelled_eval_log_ref is not None
    log = (tmp_path / "logs" / f"{rec.cancelled_eval_log_ref.ref_id}.eval.log").read_text()
    assert "PASSED tests/test_thing.py::test_feature" in log and "RH2_INSTALL_RC=2" in log  # 完整测试日志未丢
    side = json.loads((tmp_path / "logs" / f"{rec.cancelled_eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["candidate"]["log_partial"] is False and side["candidate"]["install_rc_last_command"] == 2


async def test_r3_cancel_during_candidate_exec_persists_partial_log(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log="never", eval_delay=5.0)
    docker.candidate_partial_log = "RH2_PHASE_START=install\nRH2_INSTALL_RC=0\n"
    manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs", cleanup_timeout_seconds=5), docker=docker)
    task = asyncio.create_task(manager.grade(trajectory_id="r3-exec", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_spec()))
    await asyncio.sleep(0.3)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    rec = manager.container_records[-1]
    assert rec.cancelled_eval_log_ref is not None
    assert "RH2_INSTALL_RC=0" in (tmp_path / "logs" / f"{rec.cancelled_eval_log_ref.ref_id}.eval.log").read_text()
    side = json.loads((tmp_path / "logs" / f"{rec.cancelled_eval_log_ref.ref_id}.diagnostics.json").read_text())
    assert side["candidate"]["log_partial"] is True


# ---------------------------------------------------------------------------
# 第四组 A（P-A，2026-09-16）：候选全局执行失败的三路判定（v2 parser + 资格记录 + 编译复证）
# ---------------------------------------------------------------------------

_PA_INSTALL_OK = (
    "+ echo RH2_PHASE_START=install\nRH2_PHASE_START=install\nRH2_TS_INSTALL_START=100.0\n"
    "RH2_INSTALL_RC=0\nRH2_TS_INSTALL_END=103.5\nRH2_PHASE_END=install\nRH2_TS_TEST_START=104.0\n"
)
_PA_COLLECTION_FAIL_SEGMENT = (
    "============================= test session starts ==============================\n"
    "collected 0 items / 1 error\n"
    "==================================== ERRORS ====================================\n"
    "_________________ ERROR collecting tests/test_thing.py _________________\n"
    "ImportError while importing test module '/testbed/tests/test_thing.py'.\n"
    "E     File \"/testbed/src/thing.py\", line 1\nE       def feature(:\nE                   ^\nE   SyntaxError: invalid syntax\n"
    "=========================== short test summary info ============================\n"
    "ERROR tests/test_thing.py\n"
    "!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!\n"
    "=============================== 1 error in 0.12s ===============================\n"
)
_PA_STARTUP_FAIL_SEGMENT = (
    "ImportError while loading conftest '/testbed/tests/conftest.py'.\n"
    "tests/conftest.py:3: in <module>\n    from src.thing import feature\n"
    "E     File \"/testbed/src/thing.py\", line 1\nE       def feature(:\nE   SyntaxError: invalid syntax\n"
)


def _pa_log(segment: str, *, test_rc: int, install: str = _PA_INSTALL_OK) -> str:
    return (
        f"{install}+ : '>>>>> Start Test Output'\n{segment}+ : '>>>>> End Test Output'\n"
        f"RH2_TEST_RC={test_rc}\nRH2_TS_TEST_END=110.25\n"
    )


def _pa_v2_parser():
    from repoharness2.envpack import scoring as _scoring
    from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
    from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1, derive_eval_cmd

    g = PrivateGradingBundleV2(
        instance_id="getmoto__moto-0001", repo="getmoto/moto", repo_key_lower="getmoto/moto", version="5.0", base_commit="a" * 40,
        test_patch="diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ b/tests/t.py\n+x\n",
        fail_to_pass=["tests/test_thing.py::test_feature"], pass_to_pass=["tests/test_thing.py::test_stable"],
        eval_cmd=derive_eval_cmd(SPEC_VENDOR_ID_SWEGYM_242429C1, "getmoto/moto", "5.0"), spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1,
    )
    return lambda text: _scoring.parse_eval_log_v2(g, text)


def _pa_spec(*, qualified: bool = True, probe: bool = True, **overrides):
    import dataclasses

    from repoharness2.grading.manager import EnvQualification, grading_image_identity, grading_scripts_digest, render_compile_probe_script

    spec = _spec(parse_log=_pa_v2_parser(), render_compile_probe=(render_compile_probe_script if probe else None), **overrides)
    if qualified:
        q = EnvQualification(
            image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec), reference_missing_count=0,
            source="ledger_e2_A.jsonl:rpt_gold_1", qualified_at_utc="2026-09-16T00:00:00Z",
        )
        spec = dataclasses.replace(spec, env_qualification=q)
    return spec


def _pa_manager(docker, tmp_path, *, profile=True):
    return SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile() if profile else None, eval_log_dir=tmp_path / "logs"), docker=docker,
    )


def _pa_side(manager, report):
    return json.loads((Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.diagnostics.json").read_text())


def _compile_probe_calls(docker):
    return [a for a in docker.calls if a and a[0] == "exec" and "RH2_COMPILE_EOF" in str(a[-1])]


async def test_pa_collection_failure_proven_by_compile_probe_is_candidate_execution_failed(tmp_path):
    """全部条件齐备：资格有效 ∧ 测试段收集失败形状确定 ∧ 安装段 rc=0 ∧ 候选改了 .py ∧ 编译复证在候选路径报 SyntaxError
    → candidate_execution_failed、reward 0、四计数 None、阶段 test_collection、证据含日志行 + 复证行 + 资格来源。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    docker.compile_probe_stdout = "RH2_COMPILE_INTERPRETER=/opt/miniconda3/envs/testbed/bin/python\nRH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-cand", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "unresolved" and report.failure_category == "candidate_execution_failed" and report.reward == 0.0
    assert report.f2p_total_count is None and report.p2p_total_count is None
    assert report.execution_failure_stage == "test_collection"
    ev = report.execution_failure_evidence
    assert any("ERROR collecting tests/test_thing.py" in line for line in ev) and "test_rc=2" in ev
    assert "compile_probe:src/thing.py:SyntaxError:line=1:invalid syntax" in ev and "env_qualification:ok:ledger_e2_A.jsonl:rpt_gold_1" in ev
    # 复证以候选身份执行，探的是候选改动的 .py 路径
    (probe,) = _compile_probe_calls(docker)
    assert "-u" in probe and probe[probe.index("-u") + 1] == str(make_grader_profile().candidate_exec_uid)
    assert "src/thing.py" in str(probe[-1]) and "RH2_COMPILE_EOF" in str(probe[-1])
    side = _pa_side(manager, report)
    dec = side["execution_failure_decision"]
    assert dec["kind"] == "candidate" and dec["trigger"] == "reference_all_missing" and dec["rule"] == "pytest_error_collecting"
    assert dec["candidate_python_paths"] == ["src/thing.py"] and side["resource_facts"]["oom_kill_events"] == 0
    assert side["env_qualification"].startswith("ok:") and side["scripts_digest"].startswith("sha256:")


async def test_pa_startup_conftest_syntax_error_is_candidate_execution_failed_with_zero_parse(tmp_path):
    """F1：conftest 加载阶段就炸（零解析、pytest rc=4）——阶段 test_startup。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_STARTUP_FAIL_SEGMENT, test_rc=4))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-startup", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.failure_category == "candidate_execution_failed" and report.execution_failure_stage == "test_startup"
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["trigger"] == "zero_parsed" and dec["rule"] == "pytest_conftest_import_error"


@pytest.mark.parametrize("variant,expect_missing", [
    ("qualification_absent", "qualification:absent"),
    ("scripts_digest_mismatch", "qualification:scripts_digest_mismatch"),
    ("image_identity_mismatch", "qualification:image_identity_mismatch"),
    ("compile_probe_clean", "compile_probe_clean"),
    ("compile_probe_timeout", "compile_probe_timeout"),
    ("no_probe_renderer", "no_compile_probe_renderer"),
    ("install_failed", "install_segment_rc=1:baseline=0"),
    ("termination_facts_unknown", "termination_facts_unknown:oom_kill_events+pids_events_max"),
    ("test_rc_unknown", "termination_facts_unknown:test_rc"),
    ("unrelated_syntax_file", "no_syntax_error_at_candidate_path"),
])
async def test_pa_missing_condition_goes_to_infra_without_reward(tmp_path, variant, expect_missing):
    """任一条件缺席 → 未确定：failed_to_grade / test_log_parse_failed / reward None，detail 列出缺失条件。"""
    import dataclasses

    segment, rc, install = _PA_COLLECTION_FAIL_SEGMENT, 2, _PA_INSTALL_OK
    if variant == "install_failed":
        install = _PA_INSTALL_OK.replace("RH2_INSTALL_RC=0", "RH2_INSTALL_RC=1")
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(segment, test_rc=rc, install=install))
    if variant == "termination_facts_unknown":
        docker.memory_events_stdout = ""  # 读不到 cgroup 事件（R3：未知 ≠ 已排除）
        docker.pids_events_stdout = ""
    if variant == "test_rc_unknown":
        docker.eval_log = _pa_log(segment, test_rc=rc, install=install).replace("RH2_TEST_RC=2\n", "")
    docker.compile_probe_stdout = (
        "RH2_COMPILE_OK=src/thing.py\n" if variant == "compile_probe_clean"
        else "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    )
    spec = _pa_spec(qualified=variant != "qualification_absent", probe=variant != "no_probe_renderer")
    if variant == "scripts_digest_mismatch":
        spec = dataclasses.replace(spec, env_qualification=dataclasses.replace(spec.env_qualification, scripts_digest="sha256:" + "0" * 64))
    if variant == "image_identity_mismatch":
        spec = dataclasses.replace(spec, env_qualification=dataclasses.replace(spec.env_qualification, image_identity="sha256:" + "1" * 64))
    manager = _pa_manager(docker, tmp_path)
    if variant == "compile_probe_timeout":
        docker.observation_delay = 0.0
        real = docker.__call__

        async def slow(*args, input_bytes=None):
            if args[0] == "exec" and "RH2_COMPILE_EOF" in str(args[-1]):
                await asyncio.sleep(0.3)
            return await real(*args, input_bytes=input_bytes)

        docker.__call__ = slow  # type: ignore[method-assign]
        manager = _pa_manager(slow, tmp_path)
        spec = dataclasses.replace(spec, apply_timeout_seconds=0.05)
    # R1 反例：候选另一份没被导入的坏文件（src/unused.py）不能解释这次失败——失败文字只点名 src/thing.py
    patch = GOOD_PATCH.replace("src/thing.py", "src/unused.py") if variant == "unrelated_syntax_file" else GOOD_PATCH
    if variant == "unrelated_syntax_file":
        docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/unused.py:SyntaxError:line=1:invalid syntax\n"
    report = await manager.grade(trajectory_id=f"pa-{variant}", workspace=FakeWorkspace(patch_text=patch), spec=spec)
    assert report.outcome == "failed_to_grade" and report.failure_category == "test_log_parse_failed" and report.reward is None
    assert report.infra_failure_detail.startswith("reference_all_missing:unattributed:"), report.infra_failure_detail
    assert expect_missing in report.infra_failure_detail
    if variant in ("qualification_absent", "scripts_digest_mismatch", "image_identity_mismatch", "install_failed", "no_probe_renderer",
                   "termination_facts_unknown", "test_rc_unknown", "unrelated_syntax_file"):
        assert _compile_probe_calls(docker) == []  # 前置条件不齐不发起复证 I/O
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["kind"] == "unattributed" and expect_missing in dec["missing"]


@pytest.mark.parametrize("variant", ["oom_kill_events", "container_oom_killed", "signal_exit"])
async def test_pa_proven_resource_termination_is_infra_without_reward(tmp_path, variant):
    """已证保护性资源终止（cgroup oom_kill / 容器 OOMKilled / 测试命令被信号杀 rc>=128）→ infra_failure、reward None，
    即使其它候选归因条件全部齐备也不判模型负样本。"""

    rc = 137 if variant == "signal_exit" else 2
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=rc))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    if variant == "oom_kill_events":
        docker.memory_events_stdout = "low 0\nhigh 3\nmax 12\noom 1\noom_kill 1\n"
    if variant == "container_oom_killed":
        docker.oom_killed = True
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id=f"pa-{variant}", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "failed_to_grade" and report.failure_category == "infra_failure" and report.reward is None
    assert report.infra_failure_detail.startswith("candidate_resource_terminated:reference_all_missing:")
    assert variant.replace("signal_exit", "signal_exit_rc=137") in report.infra_failure_detail
    assert _compile_probe_calls(docker) == []
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["kind"] == "resource" and dec["resource"]["test_rc"] == rc


async def test_pa_legacy_path_without_profile_stays_infra_and_names_the_missing_profile(tmp_path):
    docker = FakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    manager = _pa_manager(docker, tmp_path, profile=False)
    report = await manager.grade(trajectory_id="pa-legacy", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "failed_to_grade" and report.reward is None
    assert "no_sandbox_profile" in report.infra_failure_detail and _compile_probe_calls(docker) == []


async def test_pa_partial_reference_results_do_not_trigger_the_decision(tmp_path):
    """参考清单里只要有一条拿到结果就不是全局失败：照旧 tests_failed（缺席计失败），不发起判定 I/O。"""

    segment = "PASSED tests/test_thing.py::test_stable\n_________________ ERROR collecting tests/test_other.py _________________\n"
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(segment, test_rc=2))
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-partial", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed"
    assert (report.f2p_pass_count, report.f2p_total_count, report.p2p_fail_count, report.p2p_total_count) == (0, 1, 0, 1)
    assert _pa_side(manager, report)["execution_failure_decision"] is None and _compile_probe_calls(docker) == []


def test_pa_shape_classifier_and_trigger_helpers():
    from repoharness2.grading.manager import classify_execution_failure_shape, execution_failure_trigger, parse_compile_probe_output

    assert classify_execution_failure_shape("no markers at all", 2) is None
    shape = classify_execution_failure_shape(_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2), 2)
    assert shape["stage"] == "test_collection" and shape["rule"] == "pytest_error_collecting" and shape["evidence"][-1] == "test_rc=2"
    shape = classify_execution_failure_shape(_pa_log("Traceback (most recent call last):\n  File \"tests/test_thing.py\", line 5\nSyntaxError: invalid syntax\n", test_rc=1), 1)
    assert shape["stage"] == "test_startup" and shape["rule"] == "python_traceback_startup_error"
    # 段外的失败文字不算（只看 Start/End 之间）
    assert classify_execution_failure_shape("ERROR collecting x.py\n+ : '>>>>> Start Test Output'\nfine\n+ : '>>>>> End Test Output'\n", 0) is None
    parsed = parse_compile_probe_output("noise\nRH2_COMPILE_INTERPRETER=/x/python\nRH2_COMPILE_OK=a.py\nRH2_COMPILE_ERROR=b.py:SyntaxError:line=2:bad\nRH2_COMPILE_MISSING=c.py\n")
    assert parsed == {"ok": ["a.py"], "error": ["b.py:SyntaxError:line=2:bad"], "missing": ["c.py"], "interpreter": "/x/python"}
    v = _pa_v2_parser()(_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    assert v.num_parsed_tests == 1 and execution_failure_trigger(v) == "reference_all_missing"
    v = _pa_v2_parser()(_pa_log("nothing\n", test_rc=5))
    assert execution_failure_trigger(v) == "zero_parsed"
    v = _pa_v2_parser()(_pa_log("PASSED tests/test_thing.py::test_stable\n", test_rc=1))
    assert execution_failure_trigger(v) is None


async def test_pa_install_rc_matching_the_qualified_baseline_does_not_block_attribution(tmp_path):
    """e2 实测：moto / pydantic 的安装段末命令在 gold/noop 下也恒为 rc=2（无网络 / 无 pdm），测试跑在镜像既有的可编辑安装上。
    资格记录带基线 rc=2 → 候选同为 2 不算偏离，仍可归因；基线 0（或未知）时 rc=2 → 未确定。"""
    import dataclasses

    log = _pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2, install=_PA_INSTALL_OK.replace("RH2_INSTALL_RC=0", "RH2_INSTALL_RC=2"))
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    spec = _pa_spec()
    spec_b2 = dataclasses.replace(spec, env_qualification=dataclasses.replace(spec.env_qualification, install_rc_last_command=2))
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-b2", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=spec_b2)
    assert report.failure_category == "candidate_execution_failed" and report.reward == 0.0
    assert _pa_side(manager, report)["execution_failure_decision"]["install_rc_baseline"] == 2
    docker2 = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    docker2.compile_probe_stdout = docker.compile_probe_stdout
    manager2 = _pa_manager(docker2, tmp_path / "b0")
    report2 = await manager2.grade(trajectory_id="pa-b0", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=spec)
    assert report2.outcome == "failed_to_grade" and "install_segment_rc=2:baseline=0" in report2.infra_failure_detail
    assert _compile_probe_calls(docker2) == []


async def test_pa_r4_completed_tests_with_all_reference_missing_follow_the_source_rule(tmp_path):
    """A 线复核 R4：测试正常跑完（有逐测试状态、rc=1）、只是参数化 ID 随源码改了，参考清单全缺席——
    不是全局执行失败：按来源规则计 tests_failed / 0（缺席计失败），不读资源事实、不复证；判定记 source_rule。"""

    segment = "F.                                                                       [100%]\nFAILED tests/test_thing.py::test_feature[after]\nPASSED tests/test_thing.py::test_stable[after]\n1 failed, 1 passed in 0.01s\n"
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(segment, test_rc=1))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-r4", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert (report.f2p_pass_count, report.f2p_total_count, report.p2p_fail_count, report.p2p_total_count) == (0, 1, 1, 1)
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["kind"] == "source_rule" and dec["trigger"] == "reference_all_missing" and dec["resource"] is None
    assert _compile_probe_calls(docker) == [] and not any("memory.events" in str(a[-1]) for a in docker.calls if a and a[0] == "exec")
    # 零解析 + 形状不确定仍是未确定（silent success 不能信）
    docker2 = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log("nothing here\n", test_rc=5))
    manager2 = _pa_manager(docker2, tmp_path / "z")
    report2 = await manager2.grade(trajectory_id="pa-r4z", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report2.outcome == "failed_to_grade" and "shape_undetermined" in report2.infra_failure_detail


async def test_pa_r3_pids_quota_hits_are_resource_termination(tmp_path):
    """B 线 216 题诊断：进程配额撞满（pids.events max>0）是保护性资源终止事实 → infra、None，即便其它条件齐备。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    docker.pids_events_stdout = "max 37\n"
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-pids", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "failed_to_grade" and report.failure_category == "infra_failure"
    assert "pids_quota_hits" in report.infra_failure_detail and _compile_probe_calls(docker) == []
    assert _pa_side(manager, report)["resource_facts"]["pids_events_max"] == 37


async def test_pa_r1_only_referenced_candidate_paths_are_probed(tmp_path):
    """R1 正例：候选改了两个 .py，失败文字只点名 src/thing.py → 只复证它；证据带点名行；未点名的路径不进复证。"""

    two = GOOD_PATCH + GOOD_PATCH.replace("src/thing.py", "src/other.py")
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n"
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-r1", workspace=FakeWorkspace(patch_text=two), spec=_pa_spec())
    assert report.failure_category == "candidate_execution_failed"
    (probe,) = _compile_probe_calls(docker)
    assert "src/thing.py" in str(probe[-1]) and "src/other.py" not in str(probe[-1])
    assert "python -I -S -" in str(probe[-1]) and "import json" not in str(probe[-1])
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["referenced_candidate_paths"] == ["src/thing.py"] and set(dec["candidate_python_paths"]) == {"src/other.py", "src/thing.py"}
    assert any('File "/testbed/src/thing.py"' in line for line in report.execution_failure_evidence)


def test_pa_r2_compile_probe_never_imports_repo_modules(tmp_path):
    """R2 真实子进程对照：仓库根放 json.py / py_compile.py / sitecustomize.py（导入即打印伪 RH2_COMPILE_ERROR 并抛错），
    真语法错误与合法源码的复证结果都不受影响，伪行不出现。"""
    import subprocess

    from repoharness2.grading.manager import parse_compile_probe_output, render_compile_probe_script

    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "bad.py").write_text("def f(:\n    pass\n")
    (repo / "src" / "good.py").write_text("x = 1\n")
    for name in ("json.py", "py_compile.py", "sitecustomize.py", "usercustomize.py"):
        (repo / name).write_text("print('RH2_COMPILE_ERROR=src/good.py:SyntaxError:line=1:forged')\nraise RuntimeError('shadow executed')\n")
    script = render_compile_probe_script(["src/bad.py", "src/good.py", "json.py"], env_lines=("#!/bin/bash", f"cd {repo}"))
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "shadow executed" not in out.stderr
    parsed = parse_compile_probe_output(out.stdout)
    assert parsed["ok"] == ["src/good.py", "json.py"] and parsed["error"][0].startswith("src/bad.py:SyntaxError:line=1:")
    assert "forged" not in out.stdout and "RH2_COMPILE_INTERPRETER=" in out.stdout


def test_pa_referenced_candidate_paths_boundaries():
    from repoharness2.grading.manager import referenced_candidate_paths

    log = _pa_log(_PA_COLLECTION_FAIL_SEGMENT + "src/thing.py:1: in <module>\nsrc/thing.pyx built\n", test_rc=2)
    assert referenced_candidate_paths(log, ["src/thing.py", "src/unused.py", "thing.py"]) == ["src/thing.py"]
    assert referenced_candidate_paths("no markers src/thing.py", ["src/thing.py"]) == []  # 只看标记段
    assert referenced_candidate_paths(_pa_log("Traceback\n  File \"tests/conftest.py\", line 2\n", test_rc=4), ["tests/conftest.py"]) == ["tests/conftest.py"]


async def test_infra_timeout_sidecar_keeps_resource_facts(tmp_path):
    """2026-09-19：候选测试超时（infra）也把 cgroup oom_kill / pids max / OOMKilled 事实留进 sidecar（modin 撞配额挂死的现场）。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log("collected 3527 items\n", test_rc=1), eval_delay=5.0)
    docker.candidate_partial_log = "RH2_PHASE_END=install\ncollected 3527 items\n"
    docker.pids_events_stdout = "max 9\n"
    manager = _pa_manager(docker, tmp_path)
    import dataclasses
    spec = dataclasses.replace(_pa_spec(), test_timeout_seconds=0.2)
    report = await manager.grade(trajectory_id="pa-timeout", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=spec)
    assert report.outcome == "failed_to_grade" and report.infra_failure_detail.startswith("grading_test_timeout")
    side = _pa_side(manager, report)
    assert side["resource_facts"]["pids_events_max"] == 9 and side["resource_facts"]["oom_kill_events"] == 0


# ---- A 线 09-19 复核 CR1 / CR2 / CR3 ----

_CR1_ARGUMENT_MENTION_SEGMENT = (
    "==================================== ERRORS ====================================\n"
    "_____________________ ERROR collecting tests/test_thing.py _____________________\n"
    "ImportError while importing test module '/testbed/tests/test_thing.py'.\n"
    "Hint: make sure your test modules/packages have valid Python names.\n"
    "Traceback:\n"
    "/opt/miniconda3/envs/testbed/lib/python3.12/importlib/__init__.py:90: in import_module\n"
    "    return _bootstrap._gcd_import(name[level:], package, level)\n"
    "tests/test_thing.py:4: in <module>\n"
    "    VALUE = load_metadata(\"src/unused.py\")\n"
    "tests/test_thing.py:2: in load_metadata\n"
    "    from qualified_external_fixture import VALUE\n"
    "E   ModuleNotFoundError: No module named 'qualified_external_fixture'\n"
    "=========================== short test summary info ============================\n"
    "ERROR tests/test_thing.py\n"
    "!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!\n"
    "1 error in 0.04s\n"
)


async def test_pa_cr1_path_mentioned_as_argument_is_not_a_syntax_location(tmp_path):
    """CR1：失败是缺外部依赖（ModuleNotFoundError），回溯的源码行里只是把 `src/unused.py` 当字符串参数；
    候选把这个从未被读取的文件写坏也不能归因——没有语法异常位置 → 未确定，不发起复证。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_CR1_ARGUMENT_MENTION_SEGMENT, test_rc=2))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/unused.py:SyntaxError:line=1:invalid syntax\n"
    manager = _pa_manager(docker, tmp_path)
    patch = GOOD_PATCH.replace("src/thing.py", "src/unused.py")
    report = await manager.grade(trajectory_id="pa-cr1", workspace=FakeWorkspace(patch_text=patch), spec=_pa_spec())
    assert report.outcome == "failed_to_grade" and report.reward is None
    assert "no_syntax_error_at_candidate_path" in report.infra_failure_detail and _compile_probe_calls(docker) == []
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["syntax_error_locations"] == {} and dec["rule"] == "pytest_error_collecting"


async def test_pa_cr1_compile_result_must_match_the_logged_syntax_location(tmp_path):
    """CR1 正例仍归因（`E     File "/testbed/src/thing.py", line 1` 紧跟 `E   SyntaxError`），复证行号对不上则未确定。"""

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2))
    docker.compile_probe_stdout = "RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=7:invalid syntax\n"
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-cr1-line", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "failed_to_grade" and "compile_probe_location_mismatch" in report.infra_failure_detail
    dec = _pa_side(manager, report)["execution_failure_decision"]
    assert dec["syntax_error_locations"] == {"src/thing.py": [1]} and dec["referenced_candidate_paths"] == ["src/thing.py"]


_CR2_FIXED_TESTS_SEGMENT = (
    "F.                                                                       [100%]\n"
    "=================================== FAILURES ===================================\n"
    "_____________________________ test_feature[after] ______________________________\n"
    "\n"
    "case = 'after'\n"
    "\n"
    "    def test_feature(case):\n"
    "        if case == \"after\":\n"
    ">           subprocess.run([sys.executable, \"-c\", \"import rh2_missing_child_module\"], check=True)\n"
    "\n"
    "tests/test_thing.py:8: \n"
    "E           subprocess.CalledProcessError: Command '[...]' returned non-zero exit status 1.\n"
    "----------------------------- Captured stderr call -----------------------------\n"
    "Traceback (most recent call last):\n"
    "  File \"<string>\", line 1, in <module>\n"
    "ModuleNotFoundError: No module named 'rh2_missing_child_module'\n"
    "=========================== short test summary info ============================\n"
    "FAILED tests/test_thing.py::test_feature[after] - subprocess.CalledProcessError\n"
    "PASSED tests/test_thing.py::test_stable[after]\n"
    "========================= 1 failed, 1 passed in 0.12s ==========================\n"
)


async def test_pa_cr2_captured_subprocess_traceback_is_not_a_global_startup_failure(tmp_path):
    """CR2：测试正常跑完 1 failed + 1 passed（参数 ID 随源码变了，参考全缺席），单测试 Captured stderr 里的子进程
    Traceback / ModuleNotFoundError 不是运行器启动失败 → 来源规则 tests_failed / 0，不进 P-A。"""
    from repoharness2.grading.manager import classify_execution_failure_shape, strip_captured_sections

    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=_pa_log(_CR2_FIXED_TESTS_SEGMENT, test_rc=1))
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-cr2", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert (report.f2p_pass_count, report.f2p_total_count, report.p2p_fail_count, report.p2p_total_count) == (0, 1, 1, 1)
    assert _pa_side(manager, report)["execution_failure_decision"]["kind"] == "source_rule"
    log = _pa_log(_CR2_FIXED_TESTS_SEGMENT, test_rc=1)
    assert classify_execution_failure_shape(log, 1, zero_parsed=False) is None
    # 零解析时同一段文本里的顶层异常行才算（Captured 块已剥离，这里剥离后没有异常行）
    assert classify_execution_failure_shape(log, 1, zero_parsed=True) is None
    assert "ModuleNotFoundError" not in strip_captured_sections(_CR2_FIXED_TESTS_SEGMENT)
    # 同一异常行若在测试失败块（非 Captured）里出现，解析到测试时也不算全局失败
    inline = _CR2_FIXED_TESTS_SEGMENT.replace("----------------------------- Captured stderr call -----------------------------\n", "")
    assert classify_execution_failure_shape(_pa_log(inline, test_rc=1), 1, zero_parsed=False) is None
    assert classify_execution_failure_shape(_pa_log(inline, test_rc=1), 1, zero_parsed=True)["rule"] == "python_traceback_startup_error"


def test_pa_cr1_syntax_error_locations_forms():
    from repoharness2.grading.manager import syntax_error_locations

    seg = (
        "E     File \"/testbed/src/thing.py\", line 3\n"
        "E       def feature(:\n"
        "E                   ^\n"
        "E   SyntaxError: invalid syntax\n"
        "src/other.py:9: in <module>\n"
        "    x = (\n"
        "E   IndentationError: unexpected indent\n"
        "  File \"./src/third.py\", line 2\n"
        "  File \"/testbed/src/fourth.py\", line 5\n"
        "ImportError: cannot import name\n"
        "----------------------------- Captured stderr call -----------------------------\n"
        "  File \"/testbed/src/captured.py\", line 1\n"
        "SyntaxError: bad\n"
    )
    assert syntax_error_locations(_pa_log(seg, test_rc=2)) == {"src/thing.py": {3}, "src/other.py": {9}}


def test_pc_cr3_cache_normalization_prunes_excluded_namespaces(tmp_path):
    """CR3：规范化命令先剪掉 manifest 的排除命名空间（.git/、.harness/），只删可评分区里的缓存目录；软链/普通文件不动。"""
    import os
    import subprocess

    from repoharness2.grading.manager import build_cache_normalization_command

    root = tmp_path / "tb"
    for d in (".git/refs/heads/__pycache__", ".harness/__pycache__", "src/__pycache__", ".pytest_cache/v", "pkg/sub/.pytest_cache"):
        (root / d).mkdir(parents=True)
    (root / ".git/refs/heads/__pycache__/probe").write_text("ref\n")
    (root / ".harness/__pycache__/x").write_text("x\n")
    (root / "src/__pycache__/a.pyc").write_text("pyc\n")
    (root / ".pytest_cache/v/x").write_text("v\n")
    (root / "src/thing.py").write_text("x = 1\n")
    (root / "tests").mkdir(); (root / "tests/__pycache__").write_text("regular file\n")
    os.symlink("thing.py", root / "src/.pytest_cache")
    cmd = build_cache_normalization_command(str(root), ("__pycache__", ".pytest_cache"), (".git/", ".harness/"))
    assert "-path './.git' -prune -o -path './.harness' -prune -o -type d" in cmd
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "RH2_CACHE_NORMALIZED=1" in out.stdout, out.stderr
    assert (root / ".git/refs/heads/__pycache__/probe").exists() and (root / ".harness/__pycache__/x").exists()
    assert not (root / "src/__pycache__").exists() and not (root / ".pytest_cache").exists() and not (root / "pkg/sub/.pytest_cache").exists()
    assert (root / "tests/__pycache__").is_file() and (root / "src/.pytest_cache").is_symlink() and (root / "src/thing.py").exists()


# ---- A 线 09-19 复核余项 CR2'：Captured 里嵌套的子 pytest 标题 ----

_CR2_NESTED_PYTEST_SEGMENT = (
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.9.19, pytest-6.2.3, py-1.11.0, pluggy-0.13.1\n"
    "rootdir: /testbed\n"
    "collected 2 items\n"
    "\n"
    "tests/test_thing.py F.                                                   [100%]\n"
    "\n"
    "=================================== FAILURES ===================================\n"
    "_____________________________ test_feature[after] ______________________________\n"
    "\n"
    "case = 'after'\n"
    "\n"
    "    def test_feature(case):\n"
    "        if case == \"after\":\n"
    ">           subprocess.run([sys.executable, \"-m\", \"pytest\", \"child/test_child.py\"], check=True)\n"
    "\n"
    "tests/test_thing.py:8: \n"
    "E           subprocess.CalledProcessError: Command '[...]' returned non-zero exit status 2.\n"
    "----------------------------- Captured stdout call -----------------------------\n"
    "============================= test session starts ==============================\n"
    "platform linux -- Python 3.9.19, pytest-6.2.3, py-1.11.0, pluggy-0.13.1\n"
    "rootdir: /testbed\n"
    "collected 0 items / 1 error\n"
    "\n"
    "==================================== ERRORS ====================================\n"
    "_____________________ ERROR collecting child/test_child.py _____________________\n"
    "ImportError while importing test module '/testbed/child/test_child.py'.\n"
    "Hint: make sure your test modules/packages have valid Python names.\n"
    "Traceback:\n"
    "child/test_child.py:1: in <module>\n"
    "    import rh2_missing_child_module\n"
    "E   ModuleNotFoundError: No module named 'rh2_missing_child_module'\n"
    "=========================== short test summary info ============================\n"
    "ERROR child/test_child.py\n"
    "!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!\n"
    "=============================== 1 error in 0.20s ===============================\n"
    "==================================== PASSES ====================================\n"
    "=========================== short test summary info ============================\n"
    "PASSED tests/test_thing.py::test_stable[after]\n"
    "FAILED tests/test_thing.py::test_feature[after] - subprocess.CalledProcessErr...\n"
    "========================= 1 failed, 1 passed in 0.91s ==========================\n"
)


async def test_pa_cr2_nested_child_pytest_in_captured_output_keeps_source_rule(tmp_path):
    """Codex 真实镜像（Python 3.9 / pytest 6.2.3）反例：父测试调用子 pytest，子进程的 `test session starts` /
    `ERROR collecting` / `Interrupted` 都在 Captured stdout 里；父会话正常完成 1 failed + 1 passed。参考 ID 全缺席
    （`[before]` → `[after]`）时按来源规则 tests_failed / 0，不因子 pytest 的标题被判成全局失败。"""
    from repoharness2.grading.manager import classify_execution_failure_shape, outer_session_completed_normally, outer_session_summary

    log = _pa_log(_CR2_NESTED_PYTEST_SEGMENT, test_rc=1)
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id="pa-cr2-nested", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert _pa_side(manager, report)["execution_failure_decision"]["kind"] == "source_rule"
    # parser 把子进程的文件级 ERROR 也计了数（3 条），所以不能凭 parsed>0 判完成——靠外层收尾行
    assert _pa_v2_parser()(log).num_parsed_tests == 3
    summary = outer_session_summary(_CR2_NESTED_PYTEST_SEGMENT)
    assert summary["counts"] == {"failed": 1, "passed": 1} and outer_session_completed_normally(_CR2_NESTED_PYTEST_SEGMENT, 1)
    assert classify_execution_failure_shape(log, 1, zero_parsed=False) is None
    # 外层自己的 collection 中断（`1 error, 1 passed` 收尾）仍是参考测试的全局失败 → 形状确定
    partial = _CR2_NESTED_PYTEST_SEGMENT.replace("========================= 1 failed, 1 passed in 0.91s ==========================", "==================== 1 error, 1 passed in 0.91s ====================") \
        .replace("=================================== FAILURES ===================================", "_____________________ ERROR collecting tests/test_ref.py _____________________\n=================================== FAILURES ===================================")
    assert not outer_session_completed_normally(partial, 1)
    assert classify_execution_failure_shape(_pa_log(partial, test_rc=2), 2, zero_parsed=False)["rule"] == "pytest_error_collecting"
    # conftest 启动失败没有收尾行 → 不是"正常完成"
    assert not outer_session_completed_normally(_PA_STARTUP_FAIL_SEGMENT, 4)
    assert outer_session_summary("=== no tests ran in 0.01s ===\n")["no_tests_ran"] and not outer_session_completed_normally("=== no tests ran in 0.01s ===\n", 5)
    assert outer_session_summary("===== 2 passed, 1 skipped, 3 warnings in 1.2s (0:00:01) =====\n")["counts"] == {"passed": 2, "skipped": 1, "warnings": 3}


# ---- A 线 09-19 footer 复核：裸收尾行（-q）与"子会话摘要不能代替外层完成事实" ----

_CHILD_PASS_BLOCK = (
    "============================= test session starts ==============================\n"
    "collected 1 item\n"
    "\n"
    "child/test_child.py .                                                    [100%]\n"
    "\n"
    "==================================== PASSES ====================================\n"
    "=========================== short test summary info ============================\n"
    "PASSED child/test_child.py::test_child\n"
    "============================== 1 passed in 0.01s ===============================\n"
)
_QUIET_NESTED_SEGMENT = _CR2_NESTED_PYTEST_SEGMENT.split("collected 2 items\n", 1)[1].replace(
    "========================= 1 failed, 1 passed in 0.91s ==========================", "1 failed, 1 passed in 0.23s"
)
_QUIET_OUTER_COLLECTION_INTERRUPTED = (
    _CHILD_PASS_BLOCK
    + "=========================== short test summary info ============================\n"
    "ERROR tests/test_thing.py\n"
    "!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!\n"
    "1 error in 0.16s\n"
)
_CONFTEST_STARTUP_AFTER_CHILD_PASS = (
    "ImportError while loading conftest '/testbed/tests/conftest.py'.\n"
    "tests/conftest.py:5: in <module>\n"
    "    from rh2_missing_fixture_dependency import VALUE\n"
    "E   ModuleNotFoundError: No module named 'rh2_missing_fixture_dependency'\n"
    + _CHILD_PASS_BLOCK
)


@pytest.mark.parametrize("name,segment,rc,expect", [
    ("quiet_nested_child_collection_error", _QUIET_NESTED_SEGMENT, 1, "source_rule"),
    ("quiet_outer_collection_interrupted_after_child_pass", _QUIET_OUTER_COLLECTION_INTERRUPTED, 2, "unattributed"),
    ("conftest_startup_failure_after_child_pass", _CONFTEST_STARTUP_AFTER_CHILD_PASS, 4, "unattributed"),
    ("child_pass_footer_with_unknown_outer_rc", _CONFTEST_STARTUP_AFTER_CHILD_PASS, None, "unattributed"),
])
async def test_pa_footer_outer_completion_needs_exit_code_and_last_footer(tmp_path, name, segment, rc, expect):
    """Codex footer 复核的真实 pytest 形态：`-q` 裸收尾行要认；子 pytest 的成功摘要不能代替外层完成事实——
    外层命令退出码不是 0/1（收集中断 2、conftest 启动失败 4、未知）时继续三路判定，无语法复证 → 未确定 None。"""

    log = _pa_log(segment, test_rc=rc if rc is not None else 0)
    if rc is None:
        log = log.replace("RH2_TEST_RC=0\n", "")
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    manager = _pa_manager(docker, tmp_path)
    report = await manager.grade(trajectory_id=f"pa-footer-{name}", workspace=FakeWorkspace(patch_text=GOOD_PATCH), spec=_pa_spec())
    dec = _pa_side(manager, report)["execution_failure_decision"]
    if expect == "source_rule":
        assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
        assert dec["kind"] == "source_rule"
    else:
        assert report.outcome == "failed_to_grade" and report.reward is None, (report.failure_category, dec)
        assert dec["kind"] == "unattributed" and dec["rule"] in ("pytest_errors_during_collection", "pytest_conftest_import_error")
        assert _compile_probe_calls(docker) == []


def test_pa_footer_grammar_bare_and_bordered():
    from repoharness2.grading.manager import outer_session_completed_normally, outer_session_summary

    assert outer_session_summary("1 failed, 1 passed in 0.23s\n")["counts"] == {"failed": 1, "passed": 1}
    assert outer_session_summary("2 passed, 1 warning in 1.05s (0:00:01)\n")["counts"] == {"passed": 2, "warnings": 1}
    assert outer_session_summary("no tests ran in 0.01s\n")["no_tests_ran"] is True
    assert outer_session_summary("===== 3 passed, 2 deselected, 1 rerun in 0.5s =====\n")["counts"] == {"passed": 3, "deselected": 2, "rerun": 1}
    # 不是收尾行：正文里夹了别的词、或不在行首
    assert outer_session_summary("took 3 passed in 2s\nretried 1 passed in 0.1s again\n") is None
    # 最后一条才算；外层退出码不是 0/1 时即使最后一条是成功摘要也不算正常完成
    seg = "=== 1 error in 0.2s ===\n1 failed, 1 passed in 0.23s\n"
    assert outer_session_completed_normally(seg, 1) and not outer_session_completed_normally(seg, 2)
    assert not outer_session_completed_normally("=== 1 passed in 0.01s ===\n", 4) and not outer_session_completed_normally("=== 1 passed in 0.01s ===\n", None)
    assert not outer_session_completed_normally("1 error, 1 passed in 0.3s\n", 1)  # --continue-on-collection-errors：有 error 计数
    # pytest-pretty（pydantic 配方，e2 真机日志尾部形态）：`Results (Xs):` + 缩进计数行
    pretty = "tests/test_construction.py::test_x PASSED\n\n==================================== PASSES ====================================\nResults (0.89s):\n        45 passed\n         1 failed\n"
    assert outer_session_summary(pretty)["counts"] == {"passed": 45, "failed": 1} and outer_session_completed_normally(pretty, 1)
    assert outer_session_summary("Results (0.2s):\nnot a count line\n") is None
    # 位置靠后的收尾才算：子会话的标准收尾在前、外层 pretty 在后
    assert outer_session_summary("=== 1 error in 0.1s ===\n" + pretty)["counts"] == {"passed": 45, "failed": 1}

