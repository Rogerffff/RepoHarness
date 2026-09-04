"""F2（codex Wave3 复核）grader profile 路径的替身测试（不需要 docker）：

- 顺序：root 写/跑 trusted setup → root 权限布置（marker 脚本，chown -R 后收回 official 文件与祖先目录）
  → root 写候选脚本 → **候选 uid** 跑测试；日志 = setup 段 + 测试段；
- `grader_trusted_setup` 与 `test` 分开计时（GradingTimingRecord.test_seconds 不含 setup）；
- 评分材料没有拆分脚本 → SandboxProfileViolation（run-halt 通道），容器已移除；
- legacy（无 profile）路径：仍以 root 跑完整 eval_script，参数形状逐字不变。
"""

from __future__ import annotations

import sys
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
        manager, report, docker, detail_contains="grading_control_surface_protect_failed:protected_count_mismatch"
    )
    assert manager.container_records[-1].control_surface["MISSING_FILES"] == "tests/test_thing.py,"


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


async def test_f2_official_test_patch_deleting_a_test_file_still_grades(tmp_path):
    """正例（不许新增系统性拒绝面）：official test_patch 删掉清单里的一个测试文件时，
    "缺失数"由可信 setup 在 apply 成功之后如实数出，权限布置只需保护剩下那一个——照常评分。"""

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
    assert report.outcome == "resolved" and report.reward == 1.0
    assert _ran_candidate_test(docker)
