"""rh2 的 miles 训练后端 adapter（miles 迁移 C0 起步）。

本包依赖 vendor slime（rh2/src/slime）与 miles 均可 import 的环境；与
repoharness2.adapters.slime（slime 冻结回退面，不改动）并列共存。
"""

from repoharness2.adapters.miles.canonicalize import (
    CanonicalizationError,
    canonicalize_group,
    canonicalize_sample,
)
from repoharness2.adapters.miles.generate_fn import Rh2MilesGenerateFn

__all__ = [
    "CanonicalizationError",
    "Rh2MilesGenerateFn",
    "canonicalize_group",
    "canonicalize_sample",
]
