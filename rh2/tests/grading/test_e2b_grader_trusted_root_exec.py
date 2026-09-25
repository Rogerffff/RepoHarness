"""第六组 E2b 评分侧（Codex review_next_slices §6；rollout 侧见 tests/adapters/test_trusted_root_exec.py）：评分容器里 root 的
可信操作不执行候选可写程序。

评分容器在候选观测 / 测试（候选身份，cwd=/testbed、候选拥有 /testbed）之后还有 root 读取：超时 / 取消后读回 tee 日志、
cgroup 资源事实、内存峰值。旧形状 `docker exec <c> bash -c …` 连 `bash` 都按镜像 PATH 查找；R2E 派生镜像的 PATH 以
`/testbed/.venv/bin` 开头。修法：root 默认走 `TRUSTED_ROOT_EXEC_PREFIX`；只有来源自带的可信 setup 与 legacy 单脚本 eval
（都在候选代码运行之前）显式保留镜像环境。

- 参数层：一次完整 profile 评分里，root exec 除可信 setup 外全部带前缀；候选身份的 exec 照旧 `bash -c`。
- 真容器（本机 docker + 钉死的 python 镜像在场才跑）：`-e PATH=/testbed/.venv/bin:…` 模拟 R2E 镜像 ENV，在
  `/testbed/.venv/bin` 放假 `bash` / `cat`（执行即留标记文件）。旧形状确实执行假程序；manager 的三个 root 读取读到真实内容、
  不留标记。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from grading_fixtures import GOOD_FAKE_LOG, GOOD_PATCH, FakeWorkspace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_w3b_grader_profile_unit import BASE_COMMIT, ProfileGraderFakeDocker, _spec  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tests/
from sandbox_test_support import make_grader_profile  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.grading.manager import (  # noqa: E402
    CANDIDATE_LOG_PATH,
    TRUSTED_ROOT_EXEC_PREFIX,
    GradingManagerConfig,
    SWEGradingManager,
    _ContainerRecord,
    run_docker,
)


def _shell_part(args: tuple[str, ...]) -> tuple[str, ...]:
    """exec 参数里容器名之后、脚本之前的 shell 入口。"""

    for i, a in enumerate(args):
        if a in ("bash", "/usr/bin/env"):
            return tuple(args[i:-1])
    raise AssertionError(f"没有 shell 入口：{args}")


async def test_profile_grade_runs_every_root_exec_except_the_trusted_setup_through_the_trusted_prefix(tmp_path):
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=GOOD_FAKE_LOG)
    recorded: list[tuple[str, ...]] = []
    inner = docker.__call__

    async def recording(*args: str, input_bytes: bytes | None = None):
        if args and args[0] == "exec":
            recorded.append(args)
        return await inner(*args, input_bytes=input_bytes)

    manager = SWEGradingManager(
        GradingManagerConfig(sandbox_profile=make_grader_profile(), eval_log_dir=tmp_path / "logs"), docker=recording,
    )
    report = await manager.grade(trajectory_id="t-e2b", workspace=FakeWorkspace(GOOD_PATCH), spec=_spec())
    assert report.outcome == "resolved"
    root = [a for a in recorded if "-u" not in a]
    candidate = [a for a in recorded if "-u" in a]
    setup = [a for a in root if a[-1].endswith(".trusted_setup 2>&1")]
    assert len(setup) == 1 and _shell_part(setup[0]) == ("bash", "-c")  # 来源自带的可信 setup：镜像环境，形状不变
    others = [a for a in root if a not in setup]
    assert others and all(_shell_part(a) == TRUSTED_ROOT_EXEC_PREFIX for a in others)
    assert any("memory.peak" in a[-1] for a in others)  # 候选之后的 root 读取在其中
    assert candidate and all(_shell_part(a) == ("bash", "-c") for a in candidate)  # 候选身份：继承镜像 ENV（激活靠它）


def _docker_with_image(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


IMAGE = sp.RELAY_IMAGE_DEFAULT  # 钉死 digest 的 python:3.12-slim（本机已在场，测试不拉镜像）
R2E_LIKE_PATH = "/testbed/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
PLANT = rf"""
set -e
mkdir -p /testbed/.venv/bin {Path(CANDIDATE_LOG_PATH).parent}
printf 'REAL-CANDIDATE-LOG\n' > {CANDIDATE_LOG_PATH}
for tool in bash cat; do
  printf '#!/bin/sh\ntouch /tmp/HIJACKED_%s\necho HIJACKED_%s\n' "$tool" "$tool" > /testbed/.venv/bin/$tool
  chmod 0755 /testbed/.venv/bin/$tool
done
"""


@pytest.mark.docker
@pytest.mark.skipif(not _docker_with_image(IMAGE), reason="本机 docker 不可用或没有钉死的 python 镜像（测试不拉镜像）")
async def test_root_reads_after_candidate_code_do_not_execute_candidate_planted_programs():
    name = f"rh2-e2b-grader-{uuid.uuid4().hex[:8]}"
    run = subprocess.run(["docker", "run", "-d", "--init", "-e", f"PATH={R2E_LIKE_PATH}", "--name", name, IMAGE,
                          "sleep", "300"], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    try:
        planted = subprocess.run(["docker", "exec", name, "/bin/bash", "-c", PLANT], capture_output=True, text=True,
                                 timeout=60)
        assert planted.returncode == 0, planted.stderr
        # 正控：旧形状（继承镜像 PATH 的 `bash -c`）执行的是假 bash
        old = subprocess.run(["docker", "exec", name, "bash", "-c", f"cat {CANDIDATE_LOG_PATH}"], capture_output=True,
                             text=True, timeout=60)
        assert "HIJACKED_bash" in old.stdout
        subprocess.run(["docker", "exec", name, "/bin/rm", "-f", "/tmp/HIJACKED_bash", "/tmp/HIJACKED_cat"], timeout=60)

        manager = SWEGradingManager(GradingManagerConfig(), docker=run_docker)
        record = _ContainerRecord(name=name, trajectory_id="t", created_epoch=time.time(),
                                  created_monotonic=time.monotonic())
        assert await manager._read_candidate_log_partial(record) == "REAL-CANDIDATE-LOG\n"
        await manager._read_peak_memory_mb(record)
        await manager._read_resource_facts(record)
        marks = subprocess.run(["docker", "exec", name, "/bin/ls", "/tmp"], capture_output=True, text=True, timeout=60)
        assert "HIJACKED" not in marks.stdout
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
