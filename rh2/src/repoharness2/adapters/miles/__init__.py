"""rh2 的 miles 训练后端 adapter（miles 迁移 C0 起步）。

本包依赖 vendor slime（rh2/src/slime）与 miles 均可 import 的环境；与
repoharness2.adapters.slime（slime 冻结回退面，不改动）并列共存。
"""

from repoharness2.adapters.miles.attempt_ledger import LedgerError, Rh2AttemptLedger
from repoharness2.adapters.miles.canonicalize import (
    CanonicalizationError,
    canonicalize_group,
    canonicalize_sample,
)
from repoharness2.adapters.miles.generate_fn import Rh2MilesGenerateFn
from repoharness2.adapters.miles.lifecycle import LifecycleClosedError, Rh2RolloutLifecycle

__all__ = [
    "CanonicalizationError",
    "LedgerError",
    "LifecycleClosedError",
    "Rh2AttemptLedger",
    "Rh2GovernanceConfig",
    "Rh2GovernedBuffer",
    "Rh2MilesGenerateFn",
    "Rh2RolloutLifecycle",
    "canonicalize_group",
    "canonicalize_sample",
]

# governed_buffer 模块级 import miles.rollout.*（其链条经 miles.utils.misc 拉
# ray），而本包其余模块在无 ray/sglang 的 CPU 环境也可导（generate_fn 的
# sglang 卡点同理已延迟）。为不扩大包导入面，两个治理 buffer 符号走 PEP 562
# 惰性导出；miles 真实加载路径 `--custom-async-data-buffer-path
# repoharness2.adapters.miles.governed_buffer.Rh2GovernedBuffer` 本就不经过
# 本 __init__。
_LAZY_EXPORTS = {
    "Rh2GovernanceConfig": "repoharness2.adapters.miles.governed_buffer",
    "Rh2GovernedBuffer": "repoharness2.adapters.miles.governed_buffer",
    "GovernedBufferError": "repoharness2.adapters.miles.governed_buffer",
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        import importlib

        return getattr(importlib.import_module(_LAZY_EXPORTS[name]), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
