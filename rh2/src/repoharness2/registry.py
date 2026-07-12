"""聚合 schema registry（S1-9，codex#5 收编）：CLI 层的全量 schema_id -> 模型表。

为什么不直接写进 `contracts.SCHEMA_REGISTRY`：依赖方向必须保持
envpack/grading/governance -> contracts（单向），把 BundlePair/BackpressureEvent/
GroupRepairSignal 注册进 contracts 会造成反向 import。S1-2/S1-4/S1-5 的
implementation-notes 都把这个决定递延到 S1-9，本模块就是定案落点：
**在 CLI 层聚合**——contracts 保持自洽的 15 个核心契约，其余带 schema_id 的
持久化对象在这里补齐，`inspect-rh2-artifact` / `inspect-rh2-s1` 统一消费本表。

收编清单（S1-9）：

    rh2.grading_backpressure_event.v1  grading/queue.py（P11 反压事实，gate evidence）
    rh2.group_repair_signal.v1         governance/gate.py（7a 起按 jsonl sidecar 落盘）
    rh2.public_task_bundle.v1          envpack/bundles.py（模型可见任务面）
    rh2.private_grading_bundle.v1      envpack/bundles.py（评分私有面，marker 豁免）
    rh2.bundle_pair.v1                 envpack/bundles.py（配对容器，含私有半区，marker 豁免）

显式豁免（记录在案，不是遗漏）：

- `manifest.json`（rh2.offline_export_manifest.v1）：文件级 digest 清单
  （dataclass，判别字段名是 manifest_schema 不是 schema_id），其防线是
  "逐文件重算 digest"（exporter 幂等 + parity 独立复跑），pydantic 字段校验
  覆盖不了这个语义；且 7a 已产出 evidence（export_sample/manifest.json），
  改序列化形态会破坏既有证据。S2 导出面扩展时再议收编。
- `frozen_v1.json`（rh2.envpack.frozen_v1）：冻结账本自带专用 fail-closed
  校验器（`envpack.freeze.verify_pairs_against_frozen`，默认加载即全量重算
  比对），强度高于 schema 校验；`inspect-rh2-s1` 直接调 `load_bundle_pairs()`
  复跑该校验。

marker 扫描豁免的聚合口径：contracts.MARKER_SCAN_EXEMPT_SCHEMAS（runtime-private
审计资产）+ 本模块补充的 envpack 私有面两项。PrivateGradingBundle/BundlePair 的
内容**天然就是** test_patch/F2P/P2P 本身——它们是评分材料的容器，不是泄漏；
真正的防线是"私有面永不进 rollout 容器/public projection/导出"（WorkspaceHandle
schema + golden 哨兵 negative test 钉死），不是对容器自身做 marker 扫描。
"""

from __future__ import annotations

from repoharness2.contracts import (
    MARKER_SCAN_EXEMPT_SCHEMAS,
    SCHEMA_REGISTRY,
    StrictModel,
)
from repoharness2.contracts.fa_runtime import (
    ExecutionIdentity,
    ModelCallAttempt,
    RolloutAttemptOutcome,
    TrainingRuntimeWindow,
)
from repoharness2.envpack.bundles import (
    BundlePair,
    PrivateGradingBundle,
    PublicTaskBundle,
)
from repoharness2.governance import GroupRepairSignal
from repoharness2.grading.queue import BackpressureEvent

__all__ = [
    "EXTRA_SCHEMA_REGISTRY",
    "FULL_SCHEMA_REGISTRY",
    "FULL_MARKER_SCAN_EXEMPT_SCHEMAS",
]

# contracts 之外、带 schema_id 的持久化对象（见模块 docstring 收编清单）。
# FA-0（2026-07-12）补充：contracts/fa_runtime.py 的四个 FA 契约物理上在
# contracts 包内（无反向依赖问题），但注册在本聚合表——S1 核心 registry
# 保持验收口径的 15 个契约冻结（done_contracts_15_schemas），FA 面按
# S1-9 建立的扩展机制走 CLI 层聚合。
EXTRA_SCHEMA_REGISTRY: dict[str, type[StrictModel]] = {
    "rh2.grading_backpressure_event.v1": BackpressureEvent,
    "rh2.group_repair_signal.v1": GroupRepairSignal,
    "rh2.public_task_bundle.v1": PublicTaskBundle,
    "rh2.private_grading_bundle.v1": PrivateGradingBundle,
    "rh2.bundle_pair.v1": BundlePair,
    "rh2.fa.execution_identity.v1": ExecutionIdentity,
    "rh2.fa.rollout_attempt_outcome.v1": RolloutAttemptOutcome,
    "rh2.fa.training_runtime_window.v1": TrainingRuntimeWindow,
    "rh2.fa.model_call_attempt.v1": ModelCallAttempt,
}

_overlap = set(EXTRA_SCHEMA_REGISTRY) & set(SCHEMA_REGISTRY)
assert not _overlap, f"聚合 registry 出现重复 schema_id：{sorted(_overlap)}"

# schema_id 键必须与模型默认值一致（键写错会让 CLI 判型永远失配，启动即炸）。
for _schema_id, _model_cls in EXTRA_SCHEMA_REGISTRY.items():
    _default = _model_cls.model_fields["schema_id"].default
    assert _default == _schema_id, f"registry 键 {_schema_id!r} 与模型默认 {_default!r} 不一致"

FULL_SCHEMA_REGISTRY: dict[str, type[StrictModel]] = {
    **SCHEMA_REGISTRY,
    **EXTRA_SCHEMA_REGISTRY,
}

# 私有评分面容器：内容即评分材料本身，按 runtime-private 资产豁免默认 marker
# 扫描（--force-marker-scan 仍可强制）；public_task_bundle 不豁免——它是模型
# 可见面，必须保持 0 命中（S1-2 实测 8 题 0 误报）。
FULL_MARKER_SCAN_EXEMPT_SCHEMAS: frozenset[str] = MARKER_SCAN_EXEMPT_SCHEMAS | {
    "rh2.private_grading_bundle.v1",
    "rh2.bundle_pair.v1",
}
