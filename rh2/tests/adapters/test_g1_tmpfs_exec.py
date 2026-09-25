"""G1（任务二发现，2026-09-25）：正式沙箱的 /tmp 与 HOME 是 tmpfs，Docker `--tmpfs` 默认 noexec，里面构建出来的程序
（Conan 功能测试的 `./build/Debug/foo`、`mytool.sh` 等）以 agent 身份执行报 Permission denied。

修法：rollout 的 /tmp 与 /home/<agent>、grader 的 /tmp 显式 `exec,nosuid,nodev`（容量、mode、uid/gid 不变）；启动前探针以
探针身份（rollout = agent，grader = 候选执行用户）读回实际挂载标志，并在两处各建一个脚本真的执行一次。

- 参数层：挂载选项、docker run 参数、profile 参数（进 runtime_profile_digest）。
- 核对层：探针事实 → 违规（不能执行 / 仍 noexec / 丢了 nosuid 或 nodev / 读不到挂载点）。
- 真容器（本机 docker + 钉死的 python 镜像在场才跑）：按 profile 的挂载选项起容器，以 uid 54321 跑真实启动前探针，
  零违规；同一探针在旧挂载（Docker 默认 noexec）下给出四条违规——复现 G1。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/：sandbox_test_support
from sandbox_test_support import grader_probe_output, make_grader_profile, make_rollout_profile, rollout_probe_output  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402

HEAD = "a" * 40


def test_both_profiles_mount_tmpfs_with_exec_and_keep_nosuid_nodev_size_and_mode():
    r, g = make_rollout_profile(), make_grader_profile()
    assert sp.TMPFS_MOUNT_FLAGS == "exec,nosuid,nodev"
    assert r.expected_tmpfs() == {
        "/tmp": f"size={r.tmp_tmpfs_bytes},mode=1777,exec,nosuid,nodev",
        f"/home/{r.agent_user}": f"size={r.home_tmpfs_bytes},mode=0750,uid={r.agent_uid},gid={r.agent_uid},exec,nosuid,nodev",
    }
    assert g.expected_tmpfs() == {"/tmp": f"size={g.tmp_tmpfs_bytes},mode=1777,exec,nosuid,nodev"}
    args = r.docker_run_args(name="c", network="n", image="img")
    assert f"/tmp:{r.expected_tmpfs()['/tmp']}" in args and "--tmpfs" in args
    assert r.to_parameters()["tmpfs_mount_flags"] == g.to_parameters()["tmpfs_mount_flags"] == "exec,nosuid,nodev"


def test_prelaunch_probes_read_mounts_and_try_to_execute_in_both_places():
    for script in (sp.rollout_prelaunch_probe_script(make_rollout_profile()), sp.grader_prelaunch_probe_script(make_grader_profile())):
        assert "done < /proc/mounts" in script and "MOUNT_TMP=" in script and "MOUNT_HOME=" in script
        assert "rh2_exec_probe /tmp TMP" in script and 'rh2_exec_probe "$HOME" HOME' in script


@pytest.mark.parametrize(("override", "fragment"), [
    ({"TMP_EXEC": "0"}, "TMP_EXEC='0'"),
    ({"HOME_EXEC": "UNWRITABLE"}, "HOME_EXEC='UNWRITABLE'"),
    ({"MOUNT_TMP": "rw,nosuid,nodev,noexec,relatime"}, "仍是 noexec"),
    ({"MOUNT_HOME": "rw,nodev,relatime"}, "缺 ['nosuid']"),
    ({"MOUNT_TMP": ""}, "MOUNT_TMP 缺失"),
])
def test_rollout_probe_check_flags_every_way_exec_or_the_privilege_flags_can_be_wrong(override, fragment):
    r = make_rollout_profile()
    assert sp.check_rollout_probe(sp.parse_key_value_output(rollout_probe_output(r, head=HEAD)), r, expected_head=HEAD) == []
    facts = sp.parse_key_value_output(rollout_probe_output(r, head=HEAD, overrides=override))
    violations = sp.check_rollout_probe(facts, r, expected_head=HEAD)
    assert any(fragment in v for v in violations), violations


def test_grader_probe_check_requires_exec_in_tmp_and_home_but_mount_flags_only_for_tmp():
    g = make_grader_profile()
    assert sp.check_grader_probe(sp.parse_key_value_output(grader_probe_output(g)), g) == []  # 没有 MOUNT_HOME（HOME 在可写层）
    bad = sp.parse_key_value_output(grader_probe_output(g, overrides={"TMP_EXEC": "0", "MOUNT_TMP": "rw,nosuid,nodev,noexec"}))
    violations = sp.check_grader_probe(bad, g)
    assert any("TMP_EXEC='0'" in v for v in violations) and any("仍是 noexec" in v for v in violations)


def _docker_with_image(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.mark.docker
@pytest.mark.skipif(not _docker_with_image(sp.RELAY_IMAGE_DEFAULT), reason="本机 docker 不可用或没有钉死的 python 镜像（测试不拉镜像）")
def test_real_container_probe_as_the_agent_uid_passes_with_the_profile_mounts_and_reproduces_g1_with_docker_defaults():
    r = make_rollout_profile()
    script = sp.rollout_prelaunch_probe_script(r)
    results = {}
    for label, tmp_opts, home_opts in (
        ("profile", r.expected_tmpfs()["/tmp"], r.expected_tmpfs()[f"/home/{r.agent_user}"]),
        ("docker_default", f"size={r.tmp_tmpfs_bytes},mode=1777",
         f"size={r.home_tmpfs_bytes},mode=0750,uid={r.agent_uid},gid={r.agent_uid}"),
    ):
        name = f"rh2-g1-{label.replace('_', '-')}-{uuid.uuid4().hex[:6]}"
        started = subprocess.run(["docker", "run", "-d", "--init", "--tmpfs", f"/tmp:{tmp_opts}",
                                  "--tmpfs", f"/home/{r.agent_user}:{home_opts}", "--name", name, sp.RELAY_IMAGE_DEFAULT,
                                  "sleep", "120"], capture_output=True, text=True, timeout=120)
        assert started.returncode == 0, started.stderr
        try:
            out = subprocess.run(["docker", "exec", "-u", str(r.agent_uid), "-e", f"HOME=/home/{r.agent_user}", name,
                                  "bash", "-c", script], capture_output=True, text=True, timeout=60).stdout
            facts = sp.parse_key_value_output(out)
            results[label] = (facts, sp._tmpfs_exec_violations(facts, who="agent", tmpfs_keys=("MOUNT_TMP", "MOUNT_HOME")))
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
    facts, violations = results["profile"]
    assert violations == [] and facts["TMP_EXEC"] == facts["HOME_EXEC"] == "1"
    assert {"nosuid", "nodev"} <= set(facts["MOUNT_TMP"].split(",")) and "noexec" not in facts["MOUNT_HOME"].split(",")
    facts, violations = results["docker_default"]
    assert facts["TMP_EXEC"] == facts["HOME_EXEC"] == "0" and len(violations) == 4  # G1 复现：两处都不能执行、都 noexec
