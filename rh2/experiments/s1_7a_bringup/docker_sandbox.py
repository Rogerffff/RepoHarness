"""薄兼容壳（F2-0 迁移，2026-08-07）：正式实现已提升至
`repoharness2.adapters.slime.docker_sandbox`。只做 re-export。"""

from repoharness2.adapters.slime.docker_sandbox import *  # noqa: F401,F403
from repoharness2.adapters.slime.docker_sandbox import DockerSandbox  # noqa: F401
