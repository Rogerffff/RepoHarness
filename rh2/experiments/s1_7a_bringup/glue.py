"""薄兼容壳（F2-0 迁移，2026-08-07）：正式实现已提升至
`repoharness2.adapters.slime.bringup`（src 唯一权威）。

保留本模块路径的硬理由：GPU 启动链 container_train.sh 以
`--custom-generate-function-path s1_7a_bringup.glue.generate` 按模块
路径引用；P3 探针 lib 也从这里导入。只做 re-export，禁止加实现。"""

from repoharness2.adapters.slime.bringup import *  # noqa: F401,F403
from repoharness2.adapters.slime.bringup import (  # noqa: F401 —— 显式钉住关键名
    BringupService,
    build_production_model_call_proxy,
    generate,
    make_per_rollout_adapter,
    write_execution_audit_record,
)
