"""W3b（D2-2）独立 grader Docker profile + codex Wave3 复核 F2 的真实容器验收（@pytest.mark.docker）。

- 评分容器由 grader profile 组装：全断网（只有 loopback）、`--cap-drop ALL` + 可信初始化能力、
  no-new-privileges、PID/CPU/memory+swap/tmpfs 限额、只读声明挂载；
- **F2**：eval 拆成 root 可信 setup（恢复 official tests、应用 test_patch）与候选执行用户的测试命令；
  official test files root:root 0644，其全部祖先目录（含 /testbed）root:root 1777（sticky）——候选进程对
  它们截断写/unlink/rename/同路径重建全部失败，候选 module 的 import 副作用改写不了尚未执行的测试；
  `/tmp`、候选 HOME、/testbed 下的构建目录与 `__pycache__` 仍可写（编译/缓存类任务不误伤）；
- 正常评分（resolved / tests_failed）在该 profile 下语义不变；
- 启动前核对不过 → SandboxProfileViolation（run-halt 通道），不是 failed_to_grade；容器已移除。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import requires_docker
from grading_fixtures import (
    FIXTURE_HYGIENE,
    SRC_FIXED,
    SRC_STILL_BROKEN,
    FixtureRepo,
    git_in,
    make_candidate_test_script,
    make_fixture_spec,
    make_trusted_setup_script,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/：sandbox_test_support
from sandbox_test_support import make_grader_profile  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sandbox_profile_mod  # noqa: E402
from repoharness2.envpack import scoring  # noqa: E402
from repoharness2.envpack.bundles import PrivateGradingBundle  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    GradingEnvSpec,
    GradingManagerConfig,
    HostWorkspace,
    HygieneRules,
    SandboxProfileViolation,
    SWEGradingManager,
)

pytestmark = [pytest.mark.docker, requires_docker]

GRADER = make_grader_profile()
UID = GRADER.candidate_exec_uid

_PRELUDE = (
    "echo RH2_EVAL_UID=$(id -u)\n"
    "echo \"RH2_STAT_TESTBED=$(stat -c '%u %a' /testbed)\"\n"
    "echo \"RH2_STAT_TESTS_DIR=$(stat -c '%u %a' /testbed/tests)\"\n"
    "echo \"RH2_STAT_TEST_FILE=$(stat -c '%u %a' /testbed/tests/test_thing.py)\"\n"
    "echo \"RH2_STAT_SRC=$(stat -c '%u' /testbed/src)\"\n"
    "echo \"RH2_ROUTED_IFACES=$(awk 'NR>1{print $1}' /proc/net/route | tr '\\n' ',')\"\n"
)

# 权限反例：候选执行用户对 official test file 的截断写 / unlink / rename / 同路径重建 / 父目录 rename / chmod
_ATTACKS = (
    "f=tests/test_thing.py\n"
    "( : > \"$f\" ) 2>/dev/null && echo RH2_ATTACK_TRUNCATE=SUCCEEDED || echo RH2_ATTACK_TRUNCATE=DENIED\n"
    "( rm -f \"$f\" ) 2>/dev/null && [ ! -e \"$f\" ] && echo RH2_ATTACK_UNLINK=SUCCEEDED || echo RH2_ATTACK_UNLINK=DENIED\n"
    "( mv \"$f\" \"$f.bak\" ) 2>/dev/null && echo RH2_ATTACK_RENAME=SUCCEEDED || echo RH2_ATTACK_RENAME=DENIED\n"
    "( mv tests tests_old ) 2>/dev/null && echo RH2_ATTACK_DIR_RENAME=SUCCEEDED || echo RH2_ATTACK_DIR_RENAME=DENIED\n"
    "( cp /dev/null \"$f\" ) 2>/dev/null && echo RH2_ATTACK_RECREATE=SUCCEEDED || echo RH2_ATTACK_RECREATE=DENIED\n"
    "( chmod 666 \"$f\" ) 2>/dev/null && echo RH2_ATTACK_CHMOD=SUCCEEDED || echo RH2_ATTACK_CHMOD=DENIED\n"
    "( echo x > tests/scratch.tmp ) 2>/dev/null && echo RH2_NEWFILE_IN_TESTS=OK || echo RH2_NEWFILE_IN_TESTS=DENIED\n"
    "echo \"RH2_FILE_AFTER=$(stat -c '%u %a %s' \"$f\")\"\n"
)


def _spec(fixture_repo: FixtureRepo, fixture_image: str, *, prelude: str = _PRELUDE, **overrides):
    return make_fixture_spec(
        fixture_repo.base_commit, fixture_image, snapshot_host_path=str(fixture_repo.path),
        candidate_test_script=make_candidate_test_script(extra_prelude=prelude),
        **overrides,
    )


def _manager(tmp_path: Path) -> SWEGradingManager:
    return SWEGradingManager(GradingManagerConfig(eval_log_dir=tmp_path / "eval_logs", sandbox_profile=GRADER))


def _eval_log(manager: SWEGradingManager, report) -> str:
    return (Path(manager.config.eval_log_dir) / f"{report.eval_log_ref.ref_id}.eval.log").read_text()


def _no_leftover(manager: SWEGradingManager) -> None:
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
    log = _eval_log(manager, report)
    assert f"RH2_EVAL_UID={UID}" in log  # 候选代码（测试命令）以非 root 运行
    # F2（T1 改判旧 oracle"整个 /testbed 属候选用户"）：/testbed 与 official 测试目录 root 属主 + sticky，
    # official 测试文件 root 0644；候选自己的源码目录属候选用户
    assert "RH2_STAT_TESTBED=0 1777" in log and "RH2_STAT_TESTS_DIR=0 1777" in log
    assert "RH2_STAT_TEST_FILE=0 644" in log and f"RH2_STAT_SRC={UID}" in log
    assert "RH2_ROUTED_IFACES=\n" in log  # 没有任何带路由的接口
    assert ">>>>> Start Test Output" in log and "git checkout" in log  # root setup 段与候选测试段合并成一份日志
    pre = manager.prelaunch_checks[-1]
    assert pre["ok"], pre["violations"]
    inf = pre["inspect_facts"]
    assert inf["network_mode"] == "none" and inf["cap_drop"] == ["ALL"] and "no-new-privileges" in inf["security_opt"]
    assert inf["pids_limit"] == GRADER.pids_limit and inf["memory"] == GRADER.memory_bytes and inf["memory_swap"] == GRADER.memory_bytes
    assert inf["tmpfs"] == GRADER.expected_tmpfs()
    assert inf["binds"] == [f"{fixture_repo.path}:/rh2/snapshot:ro"]
    assert [m for m in inf["mounts"] if m["type"] == "bind"] == [
        {"type": "bind", "source": str(fixture_repo.path), "destination": "/rh2/snapshot", "rw": False}
    ]
    facts = pre["probe_facts"]
    assert facts["UID"] == str(UID) and facts["CAPEFF"].strip("0") == "" and facts["NNP"] == "1"
    assert facts["ROUTED_IFACES"] == "" and facts["CG_SWAP_MAX"] == "0" and facts["CG_PIDS_MAX"] == str(GRADER.pids_limit)
    assert manager.leases[-1].run_as_user == GRADER.candidate_exec_user and manager.leases[-1].network_policy == "deny_all"
    record = manager.container_records[-1]
    assert record.control_surface["RH2_PROTECT_OK"] == "1" and record.control_surface["PROTECTED_FILES"] == "1"
    assert record.control_surface["TESTBED_STAT"] == "0 1777"
    # P2-4/F2：root 可信 setup 与候选测试时间分开记
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    assert phase.segments["grader_trusted_setup"] is not None and phase.segments["grader_trusted_setup"] > 0.0
    assert phase.segments["test"] is not None and report.timings.test_seconds == pytest.approx(phase.segments["test"], abs=1e-3)
    _no_leftover(manager)


async def test_grader_profile_tests_failed_is_still_reward_zero_negative_sample(fixture_repo, fixture_image, make_workspace, tmp_path):
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_STILL_BROKEN)
    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="w3b-failed", workspace=HostWorkspace(ws), spec=_spec(fixture_repo, fixture_image))
    assert report.outcome == "unresolved" and report.failure_category == "tests_failed" and report.reward == 0.0
    assert f"RH2_EVAL_UID={UID}" in _eval_log(manager, report)
    _no_leftover(manager)


async def test_f2_candidate_cannot_truncate_unlink_rename_or_recreate_official_test_file(fixture_repo, fixture_image, make_workspace, tmp_path):
    """权限反例：official test patch 应用后，候选执行用户对 official test file 的六种改写都失败；
    在同一测试目录里新建文件仍可以（sticky 目录"可新建、不可替换"）。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _manager(tmp_path)
    report = await manager.grade(
        trajectory_id="w3b-attacks", workspace=HostWorkspace(ws), spec=_spec(fixture_repo, fixture_image, prelude=_ATTACKS),
    )
    log = _eval_log(manager, report)
    for attack in ("TRUNCATE", "UNLINK", "RENAME", "DIR_RENAME", "RECREATE", "CHMOD"):
        assert f"RH2_ATTACK_{attack}=DENIED" in log, (attack, log[-2000:])
    assert "RH2_NEWFILE_IN_TESTS=OK" in log
    assert "RH2_FILE_AFTER=0 644 " in log  # 文件仍是 root 0644、非零长度
    assert report.outcome == "resolved" and report.reward == 1.0  # 攻击全部无效，评分照常
    _no_leftover(manager)


def _build_az_repo(root: Path) -> FixtureRepo:
    """两个顺序执行的 official 测试：A 导入候选 module（含改写 Z 的 import 副作用），Z 独立。"""

    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "thing.py").write_text('def feature():\n    return "broken"\n')
    (root / "tests" / "test_a.py").write_text(
        "import pathlib, sys\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
        "from src.thing import feature\n"
        "print(('PASSED ' if feature() == 'fixed' else 'FAILED ') + 'tests/test_a.py::test_a')\n"
    )
    (root / "tests" / "test_z.py").write_text("print('PASSED tests/test_z.py::test_z')\n")
    (root / "README.md").write_text("rh2 W3b F2 A/Z fixture\n")
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True, capture_output=True)
    git_in(root, "add", "-A")
    git_in(root, "commit", "-q", "-m", "az base")
    return FixtureRepo(path=root, base_commit=git_in(root, "rev-parse", "HEAD"))


_AZ_ATTACK_SRC = '''import os, pathlib
_ROOT = pathlib.Path(__file__).resolve().parents[1]
_Z = _ROOT / "tests" / "test_z.py"


def _try(tag, fn):
    try:
        fn()
        print(f"RH2_ATTACK_{tag}=SUCCEEDED")
    except OSError as exc:
        print(f"RH2_ATTACK_{tag}=DENIED:{exc.errno}")


# 候选 module 的 import 副作用：试图改写尚未执行的 official 测试 Z（六条路径）
_try("Z_WRITE", lambda: _Z.write_text('print("FAILED tests/test_z.py::test_z")\\n'))
_try("Z_UNLINK", lambda: _Z.unlink())
_try("Z_RENAME", lambda: _Z.rename(_ROOT / "tests" / "test_z_old.py"))
_try("Z_DIR_RENAME", lambda: (_ROOT / "tests").rename(_ROOT / "tests_old"))
_try("Z_TESTBED_RENAME", lambda: os.rename(str(_ROOT), str(_ROOT.parent / "testbed_old")))
_try("Z_CHMOD", lambda: _Z.chmod(0o666))


def feature():
    return "fixed"
'''


async def test_f2_candidate_import_side_effect_cannot_rewrite_later_official_test(fixture_image, tmp_path):
    """行为反例：顺序执行 A/Z；A 导入的候选 module 在 import 时试图改写 Z——parser 结果不受影响（Z 仍 PASSED，
    resolved），且日志记录每条改写路径都被拒。"""

    repo = _build_az_repo(tmp_path / "az_snapshot")
    ws = tmp_path / "az_ws"
    subprocess.run(["git", "clone", "-q", str(repo.path), str(ws)], check=True, capture_output=True)
    (ws / "src" / "thing.py").write_text(_AZ_ATTACK_SRC)
    private = PrivateGradingBundle(
        instance_id="rh2-fixture.az-0001", repo="psf/requests", version="2.3", base_commit=repo.base_commit,
        golden_patch="diff --git a/src/thing.py b/src/thing.py\n--- a/src/thing.py\n+++ b/src/thing.py\n@@ -1,2 +1,2 @@\n def feature():\n-    return \"broken\"\n+    return \"fixed\"\n",
        test_patch=(
            "diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1 @@\n-# a\n+# golden a\n"
            "diff --git a/tests/test_z.py b/tests/test_z.py\n--- a/tests/test_z.py\n+++ b/tests/test_z.py\n@@ -1 +1 @@\n-# z\n+# golden z\n"
        ),
        fail_to_pass=["tests/test_a.py::test_a"], pass_to_pass=["tests/test_z.py::test_z"],
        eval_script="#!/bin/bash\ncd /testbed\npython tests/test_a.py; python tests/test_z.py\n",
        test_cmd="python tests/test_a.py; python tests/test_z.py",
    )
    spec = GradingEnvSpec(
        task_id="rh2-fixture.az-0001", image=fixture_image, base_commit=repo.base_commit,
        eval_script=private.eval_script, parse_log=lambda text: scoring.parse_eval_log(private, text),
        grader_version=f"swebench-{scoring.swebench_version()}",
        hygiene=HygieneRules(test_files=("tests/test_a.py", "tests/test_z.py"), test_globs=FIXTURE_HYGIENE.test_globs,
                             forbidden_globs=FIXTURE_HYGIENE.forbidden_globs),
        checkout_mode="clone_from_readonly_snapshot", snapshot_host_path=str(repo.path), eval_script_path="/rh2/eval.sh",
        image_local_build=True,
        trusted_setup_script=make_trusted_setup_script(repo.base_commit),
        candidate_test_script=make_candidate_test_script(test_cmd="python tests/test_a.py; python tests/test_z.py"),
    )
    manager = _manager(tmp_path)
    report = await manager.grade(trajectory_id="w3b-az", workspace=HostWorkspace(ws), spec=spec)
    log = _eval_log(manager, report)
    for tag in ("Z_WRITE", "Z_UNLINK", "Z_RENAME", "Z_DIR_RENAME", "Z_TESTBED_RENAME", "Z_CHMOD"):
        assert f"RH2_ATTACK_{tag}=DENIED" in log, (tag, log[-2000:])
    assert "RH2_ATTACK_" in log and "SUCCEEDED" not in log
    assert "PASSED tests/test_a.py::test_a" in log and "PASSED tests/test_z.py::test_z" in log
    assert report.outcome == "resolved" and report.reward == 1.0
    assert manager.container_records[-1].control_surface["PROTECTED_FILES"] == "2"
    _no_leftover(manager)


async def test_f2_compile_cache_and_build_writes_still_allowed_for_candidate(fixture_repo, fixture_image, make_workspace, tmp_path):
    """正例：需要编译/缓存的任务不被误伤——候选用户能在 official 测试目录里写 __pycache__、在 /testbed 下建构建目录、
    写 /tmp 与 HOME，随后评分照常 resolved。"""

    prelude = (
        "python -c \"import compileall, sys; sys.exit(0 if compileall.compile_dir('tests', quiet=1) else 1)\" "
        "&& [ -d tests/__pycache__ ] && echo RH2_COMPILE_TESTS=OK || echo RH2_COMPILE_TESTS=DENIED\n"
        "python -c \"import compileall, sys; sys.exit(0 if compileall.compile_dir('src', quiet=1) else 1)\" "
        "&& echo RH2_COMPILE_SRC=OK || echo RH2_COMPILE_SRC=DENIED\n"
        "mkdir -p build/lib && echo obj > build/lib/out.o && echo RH2_BUILD_DIR=OK || echo RH2_BUILD_DIR=DENIED\n"
        "echo cache > /tmp/rh2_cache.bin && echo RH2_TMP=OK || echo RH2_TMP=DENIED\n"
        "mkdir -p \"$HOME/.cache/rh2\" && echo RH2_HOME=OK || echo RH2_HOME=DENIED\n"
        "echo x > src/generated.py && echo RH2_SRC_WRITE=OK || echo RH2_SRC_WRITE=DENIED\n"
    )
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    manager = _manager(tmp_path)
    report = await manager.grade(
        trajectory_id="w3b-build", workspace=HostWorkspace(ws), spec=_spec(fixture_repo, fixture_image, prelude=prelude),
    )
    log = _eval_log(manager, report)
    for key in ("RH2_COMPILE_TESTS", "RH2_COMPILE_SRC", "RH2_BUILD_DIR", "RH2_TMP", "RH2_HOME", "RH2_SRC_WRITE"):
        assert f"{key}=OK" in log, (key, log[-2000:])
    assert report.outcome == "resolved" and report.reward == 1.0
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
