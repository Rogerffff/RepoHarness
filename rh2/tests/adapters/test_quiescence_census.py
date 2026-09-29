"""模型结束后的静止检查不执行候选 Git；沿基线政策保留内容/模式/普通软链事实。

Docker 用例只使用已有镜像，不拉包、不运行模型。使用正式 profile 的能力/资源限制和 internal 网络，
只建小仓库；不替代整条 CC/relay/训练链验收。旧 Git 指纹仅作为一次性容器里的修前反例。
"""

from __future__ import annotations

import base64
import hashlib
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from repoharness2.adapters.slime import sandbox_profile as sp
from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest
from repoharness2.adapters.slime.generate import TRUSTED_ROOT_EXEC_PREFIX, QuiescenceConfirmed, RolloutContainerWorkspace
from repoharness2.adapters.slime.patch_exporter import PatchExportError, export_frozen_patch
from repoharness2.adapters.slime.quiescence_barrier import DockerQuiescenceBarrier, _digest_script
from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_R2E_V1,
    BASELINE_MANIFEST_POLICY_V1,
    BASELINE_MANIFEST_POLICY_V2,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_f2_2b_barrier import _Exec, _audit  # noqa: E402
from test_f2_2_capability import _stamp_fa_identity  # noqa: E402
from test_slime_generate import (  # noqa: E402
    SAMPLING_PARAMS, _Args, _formal_config, build_dense_chain, dense_turns, make_task,
)


async def test_cache_counts_do_not_become_a_stability_rejection():
    body = "regular\t100644\t" + "a" * 64 + "\tfile.py\n"
    ws = _Exec(digests=[body + "CACHE_OMITTED_DIRS\t1\nCACHE_OMITTED_FILES\t2\n",
                        body + "CACHE_OMITTED_DIRS\t2\nCACHE_OMITTED_FILES\t7\n"])
    q = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    assert isinstance(q, QuiescenceConfirmed)


@pytest.mark.parametrize(("task_id", "policy"), [
    ("t", BASELINE_MANIFEST_POLICY_V1),
    ("swe_gym_lite::repo-1", BASELINE_MANIFEST_POLICY_V2),
    ("r2e_gym_subset::repo-1", BASELINE_MANIFEST_POLICY_R2E_V1),
])
async def test_formal_materialization_baseline_and_barrier_share_the_task_policy(task_id, policy):
    seen = []

    class Barrier(DockerQuiescenceBarrier):
        async def establish(self, *, workspace, audit):
            seen.append(workspace.census_policy)
            q = await super().establish(workspace=workspace, audit=audit)
            assert isinstance(q, QuiescenceConfirmed)
            assert q.frozen_grading_workspace.census_policy is workspace.census_policy
            return q

    turns = dense_turns()
    for t in turns:
        t.response["meta_info"]["weight_version"] = "5"
    chain = build_dense_chain(task=make_task(task_id), turns=turns,
                              config=_formal_config(policy_version="5", execution_mode="fa_formal"),
                              runtime_quiescence_barrier=Barrier())
    _stamp_fa_identity(chain.base_sample)
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    assert seen == [policy]
    assert chain.grading.calls[0]["frozen_delta"].baseline_manifest.policy is policy
    assert any(not getattr(s, "remove_sample", False) for s in delivered)


IMAGE = "rh2-r2e-derived/aiohttp:240da1001519-r2e_derive_v1"
WORKDIR = "/rh2_git_fixture"


def _has_image():
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.fixture
def box():
    if not _has_image():
        pytest.skip("需要本机已有 aiohttp 派生镜像；本测试不下载")
    name = "rh2-git-boundary-" + uuid.uuid4().hex[:10]
    network = name + "-net"
    profile = sp.RolloutSandboxProfile(model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=18001)

    def run(*args):
        return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=120)

    created = run("network", "create", "--internal", network)
    assert created.returncode == 0, created.stderr
    try:
        started = run(*profile.docker_run_args(name=name, network=network, image=IMAGE))
        assert started.returncode == 0, started.stderr
        prep = run("exec", name, *TRUSTED_ROOT_EXEC_PREFIX, f"""
set -e
id -u agent >/dev/null 2>&1 || useradd -u 54321 -M agent
mkdir -p {WORKDIR}; cd {WORKDIR}
git init -q
git config user.email fixture@example.invalid; git config user.name fixture
git config --system --add safe.directory '*'
printf 'old\\n' > tracked.txt
printf '*.so\\n' > .gitignore
git add .; git commit -qm base
chown -R 54321:54321 {WORKDIR}
""")
        assert prep.returncode == 0, prep.stderr
        yield name, run
    finally:
        run("rm", "-f", name)
        run("network", "rm", network)


def _workspace(name, policy=BASELINE_MANIFEST_POLICY_R2E_V1):
    return RolloutContainerWorkspace(docker=sp.default_docker_runner, container_name=name,
                                     testbed_path=WORKDIR, census_policy=policy)


async def _baseline(ws):
    return await generate_baseline_manifest(
        ws, task_id="r2e_gym_subset::fixture", workdir=WORKDIR, public_bundle_digest="sha256:" + "e" * 64,
        runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40, task_base_commit="a" * 40,
        policy=ws.census_policy,
    )


@pytest.mark.docker
async def test_formal_profile_root_git_counterexample_and_census_frozen_export(box):
    name, run = box
    ws = _workspace(name)
    baseline = await _baseline(ws)
    planted = run("exec", "-u", "agent", name, "/bin/bash", "--noprofile", "--norc", "-c", f"""
set -e
cd {WORKDIR}
git config filter.trip.clean 'id -u > /root/rh2_git_uid; cat'
printf '*.txt filter=trip\\n' > .gitattributes
printf 'changed\\n' >> tracked.txt
printf 'binary\\0data' > ignored.so
chmod +x tracked.txt
ln -s /root/unreadable link
""")
    assert planted.returncode == 0, planted.stderr
    # 修前脚本，使用修前已有的可信 PATH，仍能执行候选 clean filter。
    old = await ws.run_bash(f"cd {WORKDIR} && git status --porcelain 2>/dev/null; git -C {WORKDIR} diff 2>/dev/null")
    assert old.exit_code == 0
    marker = await ws.run_bash("cat /root/rh2_git_uid; rm /root/rh2_git_uid")
    assert marker.exit_code == 0 and marker.stdout.strip() == "0"
    bg = run("exec", "-d", "-u", "agent", name, "/bin/sleep", "300")
    assert bg.returncode == 0, bg.stderr
    before = await ws.run_bash("ps -o pid= -u agent | wc -l")
    assert int(before.stdout) > 0
    audit = SimpleNamespace(session_plane_drained=True, termination={})
    q = await DockerQuiescenceBarrier().establish(workspace=ws, audit=audit)
    assert isinstance(q, QuiescenceConfirmed)
    assert audit.termination["barrier_stop"]["residual"] == 0
    assert await q.frozen_grading_workspace.verify_integrity()
    artifact = await export_frozen_patch(q.frozen_grading_workspace, baseline,
                                         rollout_execution_id="fixture", physical_attempt_id="fixture#p1")
    entries = {e.path: e for e in artifact.entries}
    assert entries["tracked.txt"].mode == "100755"
    assert base64.b64decode(entries["ignored.so"].content_b64) == b"binary\0data"
    assert entries["link"].object_type == "symlink"
    assert (await ws.run_bash("test ! -e /root/rh2_git_uid")).exit_code == 0


@pytest.mark.docker
async def test_census_fingerprint_sees_ignored_content_modes_and_symlink_targets(box):
    name, _ = box
    ws = _workspace(name)
    setup = await ws.run_bash("printf a > ignored.so; ln -s nowhere link; printf outside > /tmp/rh2_target")
    assert setup.exit_code == 0

    async def fingerprint():
        r = await ws.run_bash(_digest_script(WORKDIR, ws.census_policy))
        assert r.exit_code == 0, r.stderr
        return hashlib.sha256(r.stdout.encode()).hexdigest()

    last = await fingerprint()
    for change in ("printf b > ignored.so", "chmod +x ignored.so", "rm link; ln -s /tmp/rh2_target link"):
        assert (await ws.run_bash(change)).exit_code == 0
        current = await fingerprint()
        assert current != last
        last = current
    assert (await ws.run_bash("printf changed > /tmp/rh2_target")).exit_code == 0
    assert await fingerprint() == last  # no-follow：外部目标字节不读入指纹


@pytest.mark.docker
@pytest.mark.parametrize(("make_unsupported", "object_type"), [
    ("mkfifo odd", "fifo"), ("touch $'odd\\001name'", "unsupported_path_name"),
])
async def test_stable_unsupported_candidate_still_reaches_exporter_unsafe(box, make_unsupported, object_type):
    name, _ = box
    ws = _workspace(name)
    baseline = await _baseline(ws)
    assert (await ws.run_bash(make_unsupported)).exit_code == 0
    q = await DockerQuiescenceBarrier().establish(workspace=ws, audit=_audit())
    assert isinstance(q, QuiescenceConfirmed)
    with pytest.raises(PatchExportError) as err:
        await export_frozen_patch(q.frozen_grading_workspace, baseline,
                                  rollout_execution_id="fixture", physical_attempt_id="fixture#p1")
    assert err.value.reason_code == "unsupported_object_in_patch"
    assert err.value.object_type == object_type
