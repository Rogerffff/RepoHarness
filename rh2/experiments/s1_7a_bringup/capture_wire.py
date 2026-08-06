"""薄兼容壳（F2-0 迁移，2026-08-07）：正式实现已提升至
`repoharness2.adapters.slime.capture_wire`（src 唯一权威）。

本壳只做 re-export。兼容范围（显式边界）：导出函数/类**对象 identity**
+ 旧动态入口可解析；**不承诺**对本壳模块全局变量重绑的传播（壳与
src 是两个 module 对象）。新代码一律直接导入 src；禁止在本文件添加
任何实现。"""

from repoharness2.adapters.slime.capture_wire import *  # noqa: F401,F403
from repoharness2.adapters.slime.capture_wire import (  # noqa: F401 —— 显式钉住关键名
    CapturePendingOverlapError,
    CaptureRegistry,
    DuplicateActiveSessionError,
    PendingTurn,
    UnknownSessionError,
    assert_no_404_guard_installed,
    build_session_guard_middleware,
    ensure_no_404_middleware,
    install_capture_wire,
    rh2_no_404_middleware,
)
