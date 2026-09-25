"""第六组 E2b（Codex review_next_slices §6）：rollout 容器里 root 的可信操作不执行候选可写程序。

R2E 派生镜像的 PATH 以 agent 可写的 `/testbed/.venv/bin` 开头；rollout 工作区通道（两次 census、内容抓取、停止合同的
pkill / ps、静止指纹的 git）以 root 执行、继承镜像 ENV，候选在那里放同名程序就能被 root 执行。修法：该通道用
`env -i PATH=<系统目录> ... /bin/bash --noprofile --norc -c`。

- 参数层：通道的 exec 形状与前缀逐项固定；agent 身份的启动与激活不经过它（此处只核通道本身）。
- 真容器（本机 docker + 钉死的 python 镜像在场才跑）：用 `-e PATH=/testbed/.venv/bin:...` 模拟 R2E 镜像的 ENV，在
  `/testbed/.venv/bin` 放假 `find` / `pkill`；旧形状（继承 PATH）确实会找到假程序，本通道找到的是系统程序，真实 census
  产出不含假 `find` 注入的条目，停止合同脚本没有执行假 `pkill`。
"""

from __future__ import annotations

import shutil
import subprocess
import uuid

import pytest

from repoharness2.adapters.slime import sandbox_profile as sp
from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest
from repoharness2.adapters.slime.execution_scope import KILL_SCRIPT
from repoharness2.adapters.slime.generate import TRUSTED_ROOT_EXEC_PREFIX, RolloutContainerWorkspace
from repoharness2.grading.manager import ExecResult


async def test_rollout_workspace_exec_uses_a_cleared_environment_and_system_tool_path():
    calls: list[tuple[str, ...]] = []

    async def docker(*args: str, input_bytes: bytes | None = None) -> ExecResult:
        calls.append(args)
        return ExecResult(0, "", "")

    await RolloutContainerWorkspace(docker=docker, container_name="c").run_bash("find . -type f")
    assert calls == [(
        "exec", "c", "/usr/bin/env", "-i", "PATH=/usr/sbin:/usr/bin:/sbin:/bin", "HOME=/root",
        "/bin/bash", "--noprofile", "--norc", "-c", "cd /testbed && find . -type f",
    )]
    assert TRUSTED_ROOT_EXEC_PREFIX[0].startswith("/") and "/testbed" not in " ".join(TRUSTED_ROOT_EXEC_PREFIX)


def _docker_with_image(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


IMAGE = sp.RELAY_IMAGE_DEFAULT  # 钉死 digest 的 python:3.12-slim（relay 同一张；本机已在场）
R2E_LIKE_PATH = "/testbed/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
PLANT = r"""
set -e
mkdir -p /testbed/.venv/bin /testbed/src
echo 'x = 1' > /testbed/src/a.py
cat > /testbed/.venv/bin/find <<'EOF'
#!/bin/sh
echo HIJACKED_FIND >&2
printf 'regular\t100644\t0000000000000000000000000000000000000000000000000000000000000000\tHIJACKED\n'
EOF
cat > /testbed/.venv/bin/pkill <<'EOF'
#!/bin/sh
echo HIJACKED_PKILL
exit 0
EOF
chmod 0755 /testbed/.venv/bin/find /testbed/.venv/bin/pkill
"""


@pytest.mark.docker
@pytest.mark.skipif(not _docker_with_image(IMAGE), reason="本机 docker 不可用或没有钉死的 python 镜像（测试不拉镜像）")
async def test_candidate_planted_tools_on_the_image_path_are_not_executed_by_root_commands():
    name = f"rh2-trusted-exec-{uuid.uuid4().hex[:8]}"
    run = subprocess.run(["docker", "run", "-d", "--init", "-e", f"PATH={R2E_LIKE_PATH}", "--name", name, IMAGE,
                          "sleep", "300"], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    try:
        planted = subprocess.run(["docker", "exec", name, "bash", "-c", PLANT], capture_output=True, text=True, timeout=60)
        assert planted.returncode == 0, planted.stderr
        # 旧形状（继承镜像 PATH）确实会先找到候选放的程序——这就是要修的面
        old = subprocess.run(["docker", "exec", name, "bash", "-c", "command -v find; command -v pkill"],
                             capture_output=True, text=True, timeout=60)
        assert old.stdout.split() == ["/testbed/.venv/bin/find", "/testbed/.venv/bin/pkill"]

        ws = RolloutContainerWorkspace(docker=sp.default_docker_runner, container_name=name)
        which = await ws.run_bash("command -v find; command -v pkill || echo PKILL_NOT_ON_TRUSTED_PATH; echo PATH=$PATH")
        assert which.stdout.split() == ["/usr/bin/find", "PKILL_NOT_ON_TRUSTED_PATH", "PATH=/usr/sbin:/usr/bin:/sbin:/bin"]
        manifest = await generate_baseline_manifest(
            ws, task_id="t", workdir="/testbed", public_bundle_digest="sha256:" + "e" * 64,
            runtime_image_digest="sha256:" + "1" * 64, materialized_head="a" * 40, task_base_commit="a" * 40,
        )
        paths = [e.path for e in manifest.entries]
        assert "src/a.py" in paths and "HIJACKED" not in paths  # 真 find 枚举了真文件
        assert ".venv/bin/find" in paths  # 候选放的文件照常作为普通文件被记录，只是不被执行
        kill = await ws.run_bash(KILL_SCRIPT)
        assert "HIJACKED_PKILL" not in kill.stdout and "pkill_status=127" in kill.stdout  # 该镜像无 procps：找不到，而不是执行假的
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
