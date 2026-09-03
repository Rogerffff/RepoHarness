"""W3b（D2-2）独立 grader Docker profile 的真实容器验收（@pytest.mark.docker）。

- 评分容器由 grader profile 组装：全断网（只有 loopback）、`--cap-drop ALL` + 可信初始化能力、
  no-new-privileges、PID/CPU/memory+swap/tmpfs 限额、只读声明挂载；
- **执行候选代码的进程非 root**：官方 eval 脚本以候选执行用户运行（日志里 `id -u` 实测），/testbed 在
  候选测试启动前交给该用户；
- 正常评分（resolved / tests_failed）在该 profile 下语义不变；
- 启动前核对不过 → SandboxProfileViolation（run-halt 通道），不是 failed_to_grade；容器已移除。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import requires_docker
from grading_fixtures import SRC_FIXED, SRC_STILL_BROKEN, FixtureRepo, make_eval_script, make_fixture_spec

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/：sandbox_test_support
from sandbox_test_support import make_grader_profile  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sandbox_profile_mod  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    GradingManagerConfig,
    HostWorkspace,
    SandboxProfileViolation,
    SWEGradingManager,
)

pytestmark = [pytest.mark.docker, requires_docker]

_PRELUDE = "echo RH2_EVAL_UID=$(id -u)\necho RH2_TESTBED_OWNER=$(stat -c %u /testbed)\necho RH2_ROUTED_IFACES=$(awk 'NR>1{print $1}' /proc/net/route | tr '\\n' ',')\n"


def _spec(fixture_repo: FixtureRepo, fixture_image: str):
    return make_fixture_spec(
        fixture_repo.base_commit, fixture_image, snapshot_host_path=str(fixture_repo.path),
        eval_script=make_eval_script(fixture_repo.base_commit, extra_prelude=_PRELUDE),
    )


def _manager(tmp_path: Path) -> SWEGradingManager:
    return SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "eval_logs", sandbox_profile=make_grader_profile()))


def _eval_log(manager: SWEGradingManager, report) -> str:
    return (Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.eval.log").read_text()


def _no_leftover(manager: SWEGradingManager) -> None:
    import subprocess

    ps = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"label={manager.config.label_prefix}.owner={manager.run_id}", "--format", "{{.ID}}"],
        capture_output=True, text=True, timeout=60,
    )
    assert ps.stdout.strip() == "", f"评分容器泄漏: {ps.stdout}"


async def test_grader_profile_resolved_with_candidate_code_run_as_nonroot_and_deny_all(fixture_repo, fixture_image, make_workspace, tmp_path):
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="w3b-resolved", workspace=HostWorkspace(ws), spec=_spec(fixture_repo, fixture_image))
    assert report.outcome == "resolved" and report.reward == 1.0
    g = make_grader_profile()
    log = _eval_log(manager, report)
    assert f"RH2_EVAL_UID={g.candidate_exec_uid}" in log  # 候选代码（官方 eval 脚本）以非 root 运行
    assert f"RH2_TESTBED_OWNER={g.candidate_exec_uid}" in log  # /testbed 已交给候选执行用户
    assert "RH2_ROUTED_IFACES=\n" in log or "RH2_ROUTED_IFACES=" in log.splitlines()  # 没有任何带路由的接口
    pre = manager.prelaunch_checks[-1]
    assert pre["ok"], pre["violations"]
    inf = pre["inspect_facts"]
    assert inf["network_mode"] == "none" and inf["cap_drop"] == ["ALL"] and "no-new-privileges" in inf["security_opt"]
    assert inf["pids_limit"] == g.pids_limit and inf["memory"] == g.memory_bytes and inf["memory_swap"] == g.memory_bytes
    assert inf["tmpfs"] == g.expected_tmpfs()
    assert inf["binds"] == [f"{fixture_repo.path}:/rh2/snapshot:ro"]
    assert [m for m in inf["mounts"] if m["type"] == "bind"] == [
        {"type": "bind", "source": str(fixture_repo.path), "destination": "/rh2/snapshot", "rw": False}
    ]
    facts = pre["probe_facts"]
    assert facts["UID"] == str(g.candidate_exec_uid) and facts["CAPEFF"].strip("0") == "" and facts["NNP"] == "1"
    assert facts["ROUTED_IFACES"] == "" and facts["CG_SWAP_MAX"] == "0" and facts["CG_PIDS_MAX"] == str(g.pids_limit)
    assert manager.leases[-1].run_as_user == g.candidate_exec_user and manager.leases[-1].network_policy == "deny_all"
    _no_leftover(manager)


async def test_grader_profile_tests_failed_is_still_reward_zero_negative_sample(fixture_repo, fixture_image, make_workspace, tmp_path):
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_STILL_BROKEN)
    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="w3b-failed", workspace=HostWorkspace(ws), spec=_spec(fixture_repo, fixture_image))
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert "RH2_EVAL_UID=54322" in _eval_log(manager, report)
    _no_leftover(manager)


async def test_grader_prelaunch_violation_is_run_halt_channel_and_removes_container(fixture_repo, fixture_image, make_workspace, tmp_path, monkeypatch):
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _manager(tmp_path)
    real = sandbox_profile_mod.check_grader_probe

    def injected(facts, profile):
        return real(facts, profile) + ["injected: grader probe violation"]

    # 核对函数住在 sandbox_profile 模块（manager 按需 import），替换那里的名字即替换 manager 看到的
    monkeypatch.setattr(sandbox_profile_mod, "check_grader_probe", injected)
    with pytest.raises(SandboxProfileViolation, match="grader_sandbox_profile_violation"):
        await manager.grade(trajectory_id="w3b-violation", workspace=HostWorkspace(ws), spec=_spec(fixture_repo, fixture_image))
    assert manager.prelaunch_checks[-1]["ok"] is False
    assert all(r.removed for r in manager.container_records)
    _no_leftover(manager)
