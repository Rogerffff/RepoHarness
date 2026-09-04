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
    ExecResult,
    GradingEnvSpec,
    GradingManagerConfig,
    HostWorkspace,
    HygieneRules,
    SandboxProfileViolation,
    SWEGradingManager,
    run_docker,
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


class RecordingDocker:
    """真实 docker CLI 的透明记录壳：反例里用来证明"候选 uid 的 exec 一次都没发生过"。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        return await run_docker(*args, input_bytes=input_bytes)

    def candidate_test_execs(self) -> list[tuple[str, ...]]:
        """以候选执行用户身份跑 eval 脚本的 exec（启动前探针也用候选 uid，但跑的是探针脚本文本，
        不是 `bash <eval_script_path>`，按脚本形态区分）。"""

        return [
            a for a in self.calls
            if a and a[0] == "exec" and "-u" in a and a[a.index("-u") + 1] == str(UID)
            and str(a[-1]).startswith("bash ")
        ]


def _manager(tmp_path: Path, docker: RecordingDocker | None = None) -> SWEGradingManager:
    return SWEGradingManager(
        GradingManagerConfig(eval_log_dir=tmp_path / "eval_logs", sandbox_profile=GRADER), docker=docker,
    )


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
    # codex Wave3 §9.2：setup / 权限布置两段自证的原始事实都进审计面，且判据全部对得上
    assert record.control_surface["EXPECTED_FILES"] == "1" and record.control_surface["MISSING_FILES_COUNT"] == "0"
    assert record.control_surface["MISSING_FILES"] == "" and record.control_surface["IRREGULAR_FILES"] == ""
    assert record.trusted_setup["RH2_SETUP_OK"] == "1" and record.trusted_setup["RH2_SETUP_APPLY_RC"] == "0"
    assert record.trusted_setup["RH2_SETUP_TEST_FILES"] == "1"
    assert record.trusted_setup["RH2_SETUP_EXPECTED_TEST_FILES"] == "1"
    assert record.trusted_setup["RH2_SETUP_ABSENT_TEST_FILES"] == "0"
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
        trusted_setup_script=make_trusted_setup_script(
            repo.base_commit, test_files=("tests/test_a.py", "tests/test_z.py")
        ),
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


# ---------------------------------------------------------------------------
# codex Wave3 §9.2 反例（真实容器）：可信 setup / 权限布置任一判据不达标 → 候选测试不启动、无 0/1 reward
# ---------------------------------------------------------------------------

# 打不上的 official test_patch（上下文行在 fixture 仓库里不存在，`git apply` 必然失败）
_UNAPPLIABLE_TEST_PATCH = (
    "diff --git a/tests/test_thing.py b/tests/test_thing.py\n"
    "--- a/tests/test_thing.py\n"
    "+++ b/tests/test_thing.py\n"
    "@@ -1 +1 @@\n"
    "-# 这一行在 fixture 仓库里并不存在\n"
    "+# golden\n"
)


def _lying_setup_script(base_commit: str, mutate: str) -> str:
    """负例专用的可信 setup：手写一份"一切正常"的自证文件（绕开共享自证尾段），
    但实际把 official test 文件改成 symlink / 删掉——用来单独验收**权限布置这一层**的判据。"""

    return (
        "#!/bin/bash\nset -xo pipefail\ncd /testbed\n"
        f"git checkout {base_commit} -- tests/\n"
        f"{mutate}\n"
        "mkdir -p /rh2\n"
        "{ echo 'RH2_SETUP_APPLY_RC=0'; echo 'RH2_SETUP_RESTORED=1'; echo 'RH2_SETUP_EXPECTED_TEST_FILES=1';"
        " echo 'RH2_SETUP_TEST_FILES=1'; echo 'RH2_SETUP_ABSENT_TEST_FILES=0';"
        " echo 'RH2_SETUP_IRREGULAR_TEST_FILES='; echo 'RH2_SETUP_OK=1'; } > /rh2/rh2_trusted_setup_attest\n"
        "cat /rh2/rh2_trusted_setup_attest\n"
    )


def _assert_blocked(manager, report, docker, log, *, detail_contains: str) -> None:
    assert report.outcome == "failed_to_grade" and report.reward is None
    assert report.failure_category == "infra_failure"
    assert detail_contains in report.infra_failure_detail, report.infra_failure_detail
    assert docker.candidate_test_execs() == []  # 候选执行用户跑 eval 脚本的 exec 一次都没发生
    assert ">>>>> Start Test Output" not in log and f"RH2_EVAL_UID={UID}" not in log
    assert report.timings.test_seconds == 0.0
    phase = manager.take_grader_phase_timing(report.timings.record_id)
    assert phase.segments["grader_trusted_setup"] is not None and phase.segments["test"] is None


async def test_f2_official_test_patch_apply_failure_blocks_candidate_test(fixture_repo, fixture_image, make_workspace, tmp_path):
    """反例 (a)：official test_patch 应用失败，而候选代码本来会让测试全过（SRC_FIXED → 正常路径是
    resolved / reward=1.0）——必须零候选测试执行、零 0/1 reward，走 typed grading-infra。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    docker = RecordingDocker()
    manager = _manager(tmp_path, docker)
    report = await manager.grade(
        trajectory_id="w3b-setup-apply-fail", workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image,
                   trusted_setup_script=make_trusted_setup_script(
                       fixture_repo.base_commit, test_patch=_UNAPPLIABLE_TEST_PATCH)),
    )
    log = _eval_log(manager, report)  # 候选测试没跑成，落盘的是 setup 段原始输出（证据面）
    _assert_blocked(manager, report, docker, log, detail_contains="grading_trusted_setup_failed:setup_exit_code")
    assert "RH2_SETUP_ERROR=official_test_patch_apply_failed" in log
    record = manager.container_records[-1]
    assert record.trusted_setup["RH2_SETUP_APPLY_RC"] != "0" and "RH2_SETUP_OK" not in record.trusted_setup
    assert record.control_surface is None  # 权限布置根本没开始
    _no_leftover(manager)


async def test_f2_official_test_file_missing_after_setup_blocks_candidate_test(fixture_repo, fixture_image, make_workspace, tmp_path):
    """反例 (b1)：official test 文件在 setup 之后不在位（此处：唯一的一个被删掉）——拒。
    codex Wave3 §10.2 之后"缺失"本身就是失败判据，不再要求"一个都不剩"才拒。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    docker = RecordingDocker()
    manager = _manager(tmp_path, docker)
    report = await manager.grade(
        trajectory_id="w3b-setup-missing", workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image,
                   trusted_setup_script=make_trusted_setup_script(
                       fixture_repo.base_commit, extra="rm -f tests/test_thing.py")),
    )
    log = _eval_log(manager, report)
    _assert_blocked(manager, report, docker, log, detail_contains="grading_trusted_setup_failed:setup_exit_code")
    assert "RH2_SETUP_ERROR=official_test_file_missing_after_setup:1" in log
    _no_leftover(manager)


async def test_f2_official_test_file_symlink_is_rejected_by_protect_step(fixture_repo, fixture_image, make_workspace, tmp_path):
    """反例 (b2)：official test 文件是 symlink，且可信 setup 谎报"一切正常"——真实权限脚本自己发现
    它不是普通文件（保护 symlink 本身挡不住改写目标），拒绝并阻止候选测试。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    docker = RecordingDocker()
    manager = _manager(tmp_path, docker)
    mutate = "cp tests/test_thing.py /tmp/real_test.py && rm -f tests/test_thing.py && ln -s /tmp/real_test.py tests/test_thing.py"
    report = await manager.grade(
        trajectory_id="w3b-protect-symlink", workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image,
                   trusted_setup_script=_lying_setup_script(fixture_repo.base_commit, mutate)),
    )
    log = _eval_log(manager, report)
    _assert_blocked(manager, report, docker, log,
                    detail_contains="grading_control_surface_protect_failed:protect_exit_code")
    assert "official_test_file_not_regular" in report.infra_failure_detail
    record = manager.container_records[-1]
    assert record.control_surface["IRREGULAR_FILES"] == "tests/test_thing.py,"
    assert record.control_surface["PROTECTED_FILES"] == "0" and "RH2_PROTECT_OK" not in record.control_surface
    _no_leftover(manager)


async def test_f2_protect_step_rejects_missing_official_test_file_it_was_told_to_protect(fixture_repo, fixture_image, make_workspace, tmp_path):
    """反例 (b3)：可信 setup 谎报"1 个 official test 在位"，实际文件不存在——真实权限脚本数出
    `PROTECTED_FILES=0` / `MISSING_FILES=tests/test_thing.py,` 并自行 `exit 5`（§10.2：缺失即拒），
    manager 随后也与 setup 自证比对不上。这是 codex 原样反例（`PROTECTED_FILES=0` 却给 reward）的生产路径版。"""

    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    docker = RecordingDocker()
    manager = _manager(tmp_path, docker)
    report = await manager.grade(
        trajectory_id="w3b-protect-missing", workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image,
                   trusted_setup_script=_lying_setup_script(fixture_repo.base_commit, "rm -f tests/test_thing.py")),
    )
    log = _eval_log(manager, report)
    _assert_blocked(manager, report, docker, log,
                    detail_contains="grading_control_surface_protect_failed:protect_exit_code")
    assert "official_test_file_missing:tests/test_thing.py," in report.infra_failure_detail
    record = manager.container_records[-1]
    assert record.control_surface["PROTECTED_FILES"] == "0"
    assert record.control_surface["MISSING_FILES"] == "tests/test_thing.py,"
    assert "RH2_PROTECT_OK" not in record.control_surface  # 判据没过就不写 OK
    _no_leftover(manager)


async def test_f2_missing_official_path_is_recreatable_by_candidate_so_grading_stops_first(
    fixture_repo, fixture_image, make_workspace, tmp_path
):
    """codex Wave3 §10.2 的纠正反例（真实容器，两半）：

    上半（为什么必须 fail-closed）：按**生产权限脚本**处理"一个在位 + 一个缺失"的 official 清单——
    脚本把祖先目录设成 root:root 1777 之后，候选 uid 依然能在那个**缺失的名字**上新建文件
    （sticky 位只阻止删除/改名别人已存在的条目，不阻止新建）。也就是说"official patch 规定为不存在
    的路径保持不存在"这半条不变量，靠 sticky 目录根本保不住。

    下半（所以评分链在候选测试之前就停）：同样形状的一次真实 `grade()` 必须走 typed grading-infra
    （`failed_to_grade` / `reward=None`），候选测试零执行——即使候选真能重建那个路径，也到不了 runner。
    """

    # —— 上半：生产权限形状下，候选 uid 能重建缺失路径 ——
    name = f"rh2-f2-recreate-{tmp_path.name[:8]}"
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
    run = subprocess.run(
        ["docker", "run", "-d", "--name", name, "--entrypoint", "sleep", fixture_image, "300"],
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 0, run.stderr
    try:
        setup = (
            "mkdir -p /testbed/tests && echo 'print(\"PASSED tests/present.py::t\")' > /testbed/tests/present.py"
        )
        assert subprocess.run(["docker", "exec", name, "bash", "-c", setup], capture_output=True, timeout=60).returncode == 0
        protect = sandbox_profile_mod.grader_protect_control_surface_script(
            GRADER, ("tests/present.py", "tests/deleted_official_test.py")
        )
        got = subprocess.run(["docker", "exec", name, "bash", "-c", protect], capture_output=True, text=True, timeout=120)
        facts = sandbox_profile_mod.parse_key_value_output(got.stdout)
        # 权限脚本现在自己就拒（§10.2）：缺失非 0 → 不写 RH2_PROTECT_OK=1
        assert got.returncode != 0 and "RH2_PROTECT_OK" not in facts, got.stdout
        assert facts["MISSING_FILES"] == "tests/deleted_official_test.py," and facts["MISSING_FILES_COUNT"] == "1"
        assert facts["PROTECTED_FILES"] == "1" and facts["TESTBED_STAT"] == "0 1777"
        # 但目录形状（root:root 1777）已经布置好了——候选 uid 仍能把缺失路径重建出来
        stat = subprocess.run(
            ["docker", "exec", "-u", str(UID), name, "bash", "-c",
             "cd /testbed && echo 'print(\"PASSED x::y\")' > tests/deleted_official_test.py"
             " && stat -c '%u %a' tests/deleted_official_test.py"],
            capture_output=True, text=True, timeout=60,
        )
        assert stat.returncode == 0 and stat.stdout.strip() == f"{UID} 644", (stat.stdout, stat.stderr)
        # 对照：在位的 official 文件仍然改不动（保护本身没退化）
        deny = subprocess.run(
            ["docker", "exec", "-u", str(UID), name, "bash", "-c", "cd /testbed && : > tests/present.py"],
            capture_output=True, text=True, timeout=60,
        )
        assert deny.returncode != 0
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)

    # —— 下半：同形状的真实评分必须在候选测试之前 typed 停止 ——
    ws = make_workspace()
    (ws / "src" / "thing.py").write_text(SRC_FIXED)
    docker = RecordingDocker()
    manager = _manager(tmp_path, docker)
    hygiene = HygieneRules(
        test_files=("tests/test_thing.py", "tests/deleted_official_test.py"),
        test_globs=FIXTURE_HYGIENE.test_globs, forbidden_globs=FIXTURE_HYGIENE.forbidden_globs,
    )
    report = await manager.grade(
        trajectory_id="w3b-missing-path", workspace=HostWorkspace(ws),
        spec=_spec(fixture_repo, fixture_image, hygiene=hygiene,
                   trusted_setup_script=make_trusted_setup_script(
                       fixture_repo.base_commit,
                       test_files=("tests/test_thing.py", "tests/deleted_official_test.py"))),
    )
    log = _eval_log(manager, report)
    _assert_blocked(manager, report, docker, log,
                    detail_contains="grading_trusted_setup_failed:setup_exit_code")
    assert "RH2_SETUP_ERROR=official_test_file_missing_after_setup:1" in log
    record = manager.container_records[-1]
    assert record.trusted_setup["RH2_SETUP_ABSENT_TEST_FILES"] == "1"
    assert "RH2_SETUP_OK" not in record.trusted_setup and record.control_surface is None
    _no_leftover(manager)
