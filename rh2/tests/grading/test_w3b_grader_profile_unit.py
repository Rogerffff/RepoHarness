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
from grading_fixtures import GOOD_FAKE_LOG, GOOD_PATCH, FakeDocker, FakeWorkspace, make_fixture_spec

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import ProfileFakeState, make_grader_profile  # noqa: E402

from repoharness2.adapters.slime.sandbox_profile import script_id_of  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    ExecResult,
    GradingManagerConfig,
    SandboxProfileViolation,
    SWEGradingManager,
)

BASE_COMMIT = "a" * 40
SETUP_LOG = "+ git checkout base -- tests/\nRH2_SETUP_RAN=1\n"


@dataclass
class ProfileGraderFakeDocker(FakeDocker):
    """tests/grading FakeDocker + profile 路径命令（裸 inspect / marker 脚本 / trusted_setup 段）。"""

    profile_fake: ProfileFakeState = field(
        default_factory=lambda: ProfileFakeState(head=BASE_COMMIT, grader_profile=make_grader_profile())
    )
    exec_sequence: list[tuple[str | None, str]] = field(default_factory=list)  # (user, 描述)

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args[0] == "exec":
            user = args[args.index("-u") + 1] if "-u" in args else None
            script = args[-1]
            sid = script_id_of(script)
            desc = sid or ("trusted_setup_run" if ".trusted_setup 2>&1" in script else
                           "candidate_test_run" if script.startswith("bash ") and "2>&1" in script else
                           "write_script" if "cat > " in script else "other")
            self.exec_sequence.append((user, desc))
            if desc == "trusted_setup_run":
                self.calls.append(args)
                return ExecResult(0, SETUP_LOG, "")
        handled = self.profile_fake.dispatch(args, input_bytes)
        if handled is not None:
            self.calls.append(args)
            return handled
        return await super().__call__(*args, input_bytes=input_bytes)


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
