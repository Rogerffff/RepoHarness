"""tests/grading 的 pytest fixtures：docker 探测、轻量评分镜像、fixture 仓库。

docker 依赖策略（S1-4 纪律）：需要真容器的测试打 `@pytest.mark.docker`；
本机 daemon 不可用时自动 skip（skip 原因可见），可用时默认全跑——
`uv run pytest -q` 在开发机上就是全量验收，另以 `pytest -m docker`
单独留证（输出进 s1/grading_p_matrix.md）。
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from grading_fixtures import FixtureRepo, build_fixture_repo, clone_workspace

# 轻量本地评分镜像（U-D：绝不拉 x86 SWE 官方镜像）：python:3.12-slim + git。
# git 是评分容器的真实依赖（clean checkout / 血缘探针 / patch 重放都要它），
# 官方 SWE 镜像同样自带 git——fixture 镜像在这一点上如实对齐。
FIXTURE_IMAGE = "rh2-s14-grading-fixture:v1"

_FIXTURE_DOCKERFILE = """\
FROM python:3.12-slim
RUN apt-get update \\
 && apt-get install -y --no-install-recommends git \\
 && rm -rf /var/lib/apt/lists/*
# 评分容器以 root 运行，快照以宿主用户属主只读挂入：safe.directory 放开才可 clone。
RUN git config --global user.email rh2-fixture@test \\
 && git config --global user.name rh2-fixture \\
 && git config --global --add safe.directory '*'
"""


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


DOCKER_AVAILABLE = _docker_available()

requires_docker = pytest.mark.skipif(
    not DOCKER_AVAILABLE, reason="本机 docker daemon 不可用（S1-4 docker 行为测试需要它）"
)


@pytest.fixture(scope="session")
def fixture_image() -> str:
    """确保轻量评分镜像存在（本地命中直接用；否则就地 docker build 一次）。"""

    if not DOCKER_AVAILABLE:
        pytest.skip("docker 不可用")
    inspect = subprocess.run(
        ["docker", "image", "inspect", FIXTURE_IMAGE], capture_output=True
    )
    if inspect.returncode == 0:
        return FIXTURE_IMAGE
    with tempfile.TemporaryDirectory() as ctx:
        (Path(ctx) / "Dockerfile").write_text(_FIXTURE_DOCKERFILE)
        build = subprocess.run(
            ["docker", "build", "-t", FIXTURE_IMAGE, ctx],
            capture_output=True,
            text=True,
            timeout=900,
        )
    assert build.returncode == 0, f"fixture 镜像构建失败:\n{build.stderr[-3000:]}"
    return FIXTURE_IMAGE


@pytest.fixture(scope="session")
def fixture_repo(tmp_path_factory: pytest.TempPathFactory) -> FixtureRepo:
    """手工小 git repo（session 级共享快照）。

    P6 纪律：本目录只作为**只读快照源**给评分容器挂载，任何测试不得改写它
    （test_manager_docker 的 P6 用例会对目录内容做前后 digest 对照）。
    """

    return build_fixture_repo(tmp_path_factory.mktemp("rh2_s14_snapshot") / "repo")


@pytest.fixture
def make_workspace(fixture_repo: FixtureRepo, tmp_path: Path):
    """agent workspace 工厂：每次克隆一份 fixture repo（HEAD==base），供测试注入改动。"""

    counter = {"n": 0}

    def _make(name: str | None = None) -> Path:
        counter["n"] += 1
        return clone_workspace(fixture_repo, tmp_path / (name or f"ws{counter['n']}"))

    return _make
