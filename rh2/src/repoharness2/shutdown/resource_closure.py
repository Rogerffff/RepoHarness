"""资源闭包一次性取数（W5a 承接原 W6；就绪稿 §2.8 两条资源闭包的最小实现）。

**不是监测面**：启动或关闭时各取一次，输出一个结构化事实文件
`resource_closure.json`（schema_id `rh2.resource_closure_facts.v1`），供 W7 judge
读取；不做采样循环、不做阈值判定、不建观测平台。两部分：

1. **内存估计**（`estimate_memory`，状态恒为 `unbounded_or_unknown`）：按"rollout
   并发数 × 每执行保守占用 + 进程级有界缓存 + buffer 容量 × 每样本 + 计划 attempt 数
   × 每 attempt 累积"相加。它**不是上界**（codex W5a 复核 #7）：dynamic filter 持续拒绝
   会让 producer 无限补采，rh2/miles 没有 attempt 总数上限，这里也不加 cap；Python
   对象开销系数是假设值。因此输出同时列出 `unconstrained_sources`，GPU 验收改看
   peak RSS、集合实测长度与增长趋势。系数逐项公开，judge 拿到的是公式与输入。

   这里最重要的不是数值，而是随 attempt 增长的集合清单（`GROWING_COLLECTIONS`）
   ——就绪稿 §2.8 第 1 条要求"盘点该生产路径上会随 attempt/group/turn 增长的
   内存集合"，其中 `RolloutOrchestrator.audits` / `.outcomes` /
   `SWEGradingManager.leases` / `._records` / `GradingQueue.events` 在生产代码里
   **没有上界**（generate.py / manager.py / queue.py 都只 append 不裁剪）。本模块
   在关闭时把它们的实际长度也取一次（`collect_growth_facts`），上界估算与实测
   长度放在同一个文件里，30~50 step 能否接受由 judge 按 profile 判。

2. **fsync 延迟单次测量**（`measure_fsync_latency`）：在 artifact 目录下写 N 个
   小文件，每个走"写入 → fsync 文件 → os.replace → fsync 父目录"的原子落盘
   路径（与 `FileFinalizationStore._write_once` / audit sink 同一套系统调用），
   记录每次的毫秒数与 p50/p95/p99/max。只测一次，不常驻。
"""

from __future__ import annotations

import json
import os
import platform
import resource
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = [
    "GROWING_COLLECTIONS",
    "MEMORY_ESTIMATE_STATUS",
    "MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES",
    "MemoryEstimateInputs",
    "collect_growth_facts",
    "estimate_memory",
    "measure_fsync_latency",
    "peak_rss_bytes",
    "resource_closure_facts",
    "write_resource_closure_facts",
]

RESOURCE_CLOSURE_SCHEMA_ID = "rh2.resource_closure_facts.v2"  # v2：memory_upper_bound → memory_estimate（W5a 复核 #7）

# 随 attempt/group/turn 增长的进程内集合清单（就绪稿 §2.8 第 1 条的盘点结果）。
# 键 = 报告字段名；值 = (所在对象, 属性路径, 是否有上界, 说明)。
# 有上界的项在这里登记是为了证明"看过了"，无上界的项是 judge 要盯的对象。
GROWING_COLLECTIONS: dict[str, tuple[str, str, bool, str]] = {
    "orchestrator_audits": (
        "RolloutOrchestrator", "audits", False,
        "每次 physical attempt append 一个 RolloutAudit（含 timeline/failure/cleanup 记录），永不裁剪",
    ),
    "orchestrator_outcomes": (
        "RolloutOrchestrator", "outcomes", False, "正式链每个 attempt 的 Outcome v2 dict，永不裁剪",
    ),
    "orchestrator_cleanup_quarantine": (
        "RolloutOrchestrator", "cleanup_quarantine", False, "receipt 写失败/清理异常保留的容器名",
    ),
    "grading_manager_records": (
        "SWEGradingManager", "_records", False, "每次评分一个 _ContainerRecord（removed 标记但不删）",
    ),
    "grading_manager_leases": ("SWEGradingManager", "leases", False, "每次评分一个 SandboxLease"),
    "grading_manager_cleanup_failures": ("SWEGradingManager", "cleanup_failures", False, "清理失败字符串"),
    "grading_queue_events": ("GradingQueue", "events", False, "每次队列打满一个 BackpressureEvent"),
    "proxy_audit_artifacts": (
        "ModelCallProxy", "audit_artifacts", True, "有界（max_audit_artifacts=256，tombstone 8x）",
    ),
    "proxy_attempts_ledger": (
        "ModelCallProxy", "attempts_ledger", True, "审计落盘成功后 ack 移除；写失败时保留（热内存证据）",
    ),
    "registry_hooks": ("CaptureRegistry", "hooks", True, "随 session 注册/注销，上界 = 并发执行数"),
    "poison_archive": ("SessionPoisonRegistry", "_archived", True, "有界（max_archived=4096）"),
}


@dataclass(frozen=True)
class MemoryEstimateInputs:
    """估算的输入（全部是显式 profile 参数；缺一个就不算——不猜默认）。

    **不是上界的输入**：`planned_attempts` 是计划量（steps × batch × n），不是 cap——
    dynamic filter 持续拒绝时 producer 会不断补采，rh2/miles 没有 attempt 总数上限
    （codex W5a 复核 #7：本模块不加 cap，改口径为估计）。
    """

    max_concurrent_executions: int  # rollout 并发执行数（miles: async_max_concurrent_samples 或 batch×n）
    grading_concurrency: int  # RH2_FA_LIMIT_GRADING
    model_call_limit: int  # RH2_FA_LIMIT_MODEL_CALL
    max_turns_per_execution: int  # RH2_MAX_TURNS_PER_SID
    max_new_tokens_per_turn: int  # rollout_max_response_len
    max_context_tokens: int  # rollout_max_context_len（0 = 未知，按 max_new_tokens×max_turns 估）
    top_k_support: int  # sampling-mask 支持集宽度（dense top-p tape 传 1）
    planned_attempts: int  # 计划 attempt 数（steps × batch × n）——计划量，非上限
    buffer_capacity_groups: int = 0  # DefaultDataBuffer 容量（capacity_factor × batch 组）；0 = 未知
    samples_per_group: int = 1  # n_samples_per_prompt（buffer 项换算成样本数）
    max_audit_artifacts: int = 256  # ModelCallProxy 有界缓存
    audit_preview_bytes: int = 4096  # bringup audit sink 的 preview 上限

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"MemoryEstimateInputs.{name}={value!r} 必须是非负整数")
        if self.max_concurrent_executions < 1:
            raise ValueError("max_concurrent_executions 必须 >= 1")
        if self.top_k_support < 1:
            raise ValueError("top_k_support 必须 >= 1（dense top-p tape 传 1）")
        if self.samples_per_group < 1:
            raise ValueError("samples_per_group 必须 >= 1")


# 估算的状态口径：rh2/miles 没有任何强制内存预算，估计值永远是 unbounded_or_unknown——
# judge 看的是 peak RSS、集合长度与增长趋势（`growth_collections`），不是这个数。
MEMORY_ESTIMATE_STATUS = "unbounded_or_unknown"

# 估算没有约束住的来源（逐项列出，judge 与 owner 知道这个数为什么不是上界）。
MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES: tuple[str, ...] = (
    "attempt_total_no_cap: dynamic filter 持续拒绝会让 producer 无限补采，rh2/miles 没有 attempt 总数上限；"
    "planned_attempts 只是计划量",
    "completed_groups_in_buffer: 已完成组在 DefaultDataBuffer 等待 drain，按 buffer_capacity_groups 计入；"
    "为 0 表示未知，且 custom buffer 可能没有容量",
    "python_object_overhead_factor_assumed: ×2 是假设系数，未实测（可能低估）",
    "out_of_process_memory: CC 子进程 / docker 容器 / SGLang 引擎的内存不在本进程估算内",
)

# 每执行在飞期间的保守系数（字节）。全部偏大：
#   - 每个 token 的 capture 事实：token id 4B + logprob 8B + 支持集 (id 4B + logprob 4B) × top_k，
#     再 ×2 留给 Python 对象开销（list[int]/list[float] 的指针与对象头远大于原始字节）；
#   - 每轮 prompt ids：上下文长度 × 4B ×2（同样的 Python 开销）；
#   - 每轮固定开销（PendingTurn/ModelCallAttempt/timeline/dict）：64 KiB。
_PY_OVERHEAD_FACTOR = 2
_PER_TURN_FIXED_BYTES = 64 * 1024
_PER_ATTEMPT_RETAINED_BYTES = 96 * 1024  # RolloutAudit + Outcome v2 dict + lease + record + 若干字符串
_PER_BUFFERED_SAMPLE_BYTES = 96 * 1024  # buffer 里等待 drain 的完成样本（tokens/logprobs/metadata）
_PER_GRADING_LIVE_BYTES = 8 * 1024 * 1024  # 评分容器日志/patch 文本在内存中的一次性副本（保守）


def estimate_memory(inputs: MemoryEstimateInputs) -> dict[str, Any]:
    """返回逐项拆解的内存**估计**（字节），状态恒为 `unbounded_or_unknown`。公式：

        live_per_execution = turns × (tokens_per_turn × per_token + context × 4 × 2 + fixed)
        live_total         = concurrency × live_per_execution + grading_concurrency × grading_live
        process_bounded    = proxy 有界缓存（max_audit_artifacts × (preview + 512)）
        buffer_bytes       = buffer_capacity_groups × samples_per_group × per_buffered_sample
        retained_planned   = planned_attempts × per_attempt_retained（计划量，非上限）
        estimate           = live_total + process_bounded + buffer_bytes + retained_planned

    `unconstrained_sources` 列出估计没有约束住的来源；`unbounded_collections` 列出生产
    代码里只增不裁的集合。GPU 验收看 peak RSS 与 `growth_collections` 的实测长度/趋势。
    """

    per_token = (4 + 8 + (4 + 4) * inputs.top_k_support) * _PY_OVERHEAD_FACTOR
    context = inputs.max_context_tokens or (inputs.max_new_tokens_per_turn * inputs.max_turns_per_execution)
    per_turn = (
        inputs.max_new_tokens_per_turn * per_token
        + context * 4 * _PY_OVERHEAD_FACTOR
        + _PER_TURN_FIXED_BYTES
    )
    live_per_execution = inputs.max_turns_per_execution * per_turn
    live_total = (
        inputs.max_concurrent_executions * live_per_execution
        + inputs.grading_concurrency * _PER_GRADING_LIVE_BYTES
    )
    process_bounded = inputs.max_audit_artifacts * (inputs.audit_preview_bytes + 512)
    buffer_bytes = inputs.buffer_capacity_groups * inputs.samples_per_group * _PER_BUFFERED_SAMPLE_BYTES
    retained_planned = inputs.planned_attempts * _PER_ATTEMPT_RETAINED_BYTES
    estimate = live_total + process_bounded + buffer_bytes + retained_planned
    unconstrained = list(MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES)
    return {
        "status": MEMORY_ESTIMATE_STATUS,
        "inputs": asdict(inputs),
        "coefficients": {
            "per_token_bytes": per_token,
            "per_turn_fixed_bytes": _PER_TURN_FIXED_BYTES,
            "per_attempt_retained_bytes": _PER_ATTEMPT_RETAINED_BYTES,
            "per_buffered_sample_bytes": _PER_BUFFERED_SAMPLE_BYTES,
            "per_grading_live_bytes": _PER_GRADING_LIVE_BYTES,
            "python_overhead_factor": _PY_OVERHEAD_FACTOR,
            "context_tokens_assumed": context,
        },
        "live_per_execution_bytes": live_per_execution,
        "live_total_bytes": live_total,
        "process_bounded_bytes": process_bounded,
        "buffer_bytes": buffer_bytes,
        "retained_planned_bytes": retained_planned,
        "estimate_bytes": estimate,
        "estimate_gib": round(estimate / (1024**3), 3),
        "unconstrained_sources": unconstrained,
        "unbounded_collections": sorted(
            name for name, (_obj, _attr, bounded, _note) in GROWING_COLLECTIONS.items() if not bounded
        ),
    }


def _len_of(obj: Any, attr: str) -> int | None:
    if obj is None:
        return None
    value = getattr(obj, attr, None)
    if value is None:
        return None
    try:
        return len(value)
    except TypeError:
        return None


def collect_growth_facts(
    *,
    orchestrator: Any = None,
    grading_manager: Any = None,
    grading_queue: Any = None,
    registry: Any = None,
) -> dict[str, Any]:
    """取一次 GROWING_COLLECTIONS 各项的实际长度（关闭时刻）。缺的对象记 None。"""

    proxy = getattr(registry, "model_call_proxy", None) if registry is not None else None
    poison = getattr(registry, "poison", None) if registry is not None else None
    objects = {
        "RolloutOrchestrator": orchestrator,
        "SWEGradingManager": grading_manager,
        "GradingQueue": grading_queue,
        "ModelCallProxy": proxy,
        "CaptureRegistry": registry,
        "SessionPoisonRegistry": poison,
    }
    facts: dict[str, Any] = {}
    for name, (owner, attr, bounded, note) in GROWING_COLLECTIONS.items():
        facts[name] = {
            "owner": owner,
            "attr": attr,
            "bounded": bounded,
            "length": _len_of(objects.get(owner), attr),
            "note": note,
        }
    return facts


def peak_rss_bytes() -> int | None:
    """进程峰值 RSS（ru_maxrss：Linux 单位 KiB，macOS 单位字节——按平台归一到字节）。"""

    try:
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ValueError, OSError):
        return None
    if sys.platform == "darwin":
        return int(raw)
    return int(raw) * 1024


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def measure_fsync_latency(
    directory: Path,
    *,
    samples: int = 16,
    payload_bytes: int = 4096,
    clock: Any = time.perf_counter,
) -> dict[str, Any]:
    """单次 fsync 延迟测量：写 `samples` 个文件，每个走原子落盘路径并计时。

    结果里 `per_op_ms` 是每次（写+fsync 文件+replace+fsync 目录）的毫秒数；
    `fsync_only_ms` 只计文件 fsync 那一步。文件用完即删；目录留下（空）。
    """

    if samples < 1:
        raise ValueError("samples 必须 >= 1")
    probe_dir = Path(directory) / ".fsync_probe"
    probe_dir.mkdir(parents=True, exist_ok=True)
    payload = (b"x" * payload_bytes)
    per_op: list[float] = []
    fsync_only: list[float] = []
    for i in range(samples):
        target = probe_dir / f"probe_{i}.bin"
        tmp = probe_dir / f".probe_{i}.tmp"
        t0 = clock()
        with open(tmp, "wb") as fh:
            fh.write(payload)
            fh.flush()
            f0 = clock()
            os.fsync(fh.fileno())
            fsync_only.append((clock() - f0) * 1000.0)
        os.replace(tmp, target)
        dir_fd = os.open(probe_dir, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        per_op.append((clock() - t0) * 1000.0)
        try:
            target.unlink()
        except OSError:
            pass
    ordered = sorted(per_op)
    ordered_fsync = sorted(fsync_only)
    return {
        "samples": samples,
        "payload_bytes": payload_bytes,
        "directory": str(probe_dir),
        "per_op_ms": [round(v, 3) for v in per_op],
        "p50_ms": round(_percentile(ordered, 0.50), 3),
        "p95_ms": round(_percentile(ordered, 0.95), 3),
        "p99_ms": round(_percentile(ordered, 0.99), 3),
        "max_ms": round(ordered[-1], 3),
        "fsync_only_p50_ms": round(_percentile(ordered_fsync, 0.50), 3),
        "fsync_only_max_ms": round(ordered_fsync[-1], 3),
    }


def resource_closure_facts(
    *,
    phase: str,
    memory_inputs: MemoryEstimateInputs | None,
    fsync_dir: Path | None,
    growth: dict[str, Any] | None = None,
    fsync_samples: int = 16,
) -> dict[str, Any]:
    """组装一份完整事实（memory_inputs 为 None 时估计记 unavailable 并说明原因）。"""

    facts: dict[str, Any] = {
        "schema_id": RESOURCE_CLOSURE_SCHEMA_ID,
        "phase": phase,
        "taken_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "peak_rss_bytes": peak_rss_bytes(),
        "memory_estimate": (
            estimate_memory(memory_inputs)
            if memory_inputs is not None
            else {
                "status": "unavailable",
                "reason": "profile 输入不全（见 bringup 的 MemoryEstimateInputs 装配）",
                "unconstrained_sources": list(MEMORY_ESTIMATE_UNCONSTRAINED_SOURCES),
            }
        ),
        "growth_collections": growth if growth is not None else {},
        "fsync_latency": (
            measure_fsync_latency(fsync_dir, samples=fsync_samples)
            if fsync_dir is not None
            else {"status": "unavailable", "reason": "未提供测量目录"}
        ),
    }
    return facts


def write_resource_closure_facts(path: Path, facts: dict[str, Any]) -> Path:
    """原子写（tmp + fsync + replace）。失败抛异常，由关停链记为 evidence 失败。"""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(facts, fh, ensure_ascii=False, indent=1, default=str)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return path
