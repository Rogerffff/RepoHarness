"""W3a 验收项（决策包 D2-1）：一次 physical attempt 生命周期的**分段计时**——最小可聚合记录，
不建监控平台。

十三个分段（单位秒，全部用 `time.monotonic()` 差值；None = 该段在本 attempt 没有发生/没测到）：

    runtime_quiescence                  Runtime 静止屏障（杀 execution scope + 双读指纹）耗时
    baseline_census                     materialize 尾部的基线 census（harness 动工前）
    post_census                         静止后对模型写过的树做 census（exporter 第 1 步）
    artifact_capture                    变更集内容抓取 + FrozenPatchArtifact 组装（exporter 第 2/3 步）
    artifact_persist                    artifact 本体（frozen patch + baseline）持久化
    grading_queue_wait                  有界评分队列排队等待（含被反压阻塞的时间）
    grader_start_and_verify             grader：绑定检查 + 镜像就绪 + 起容器 + 镜像 digest + clean checkout
    grader_baseline_rebuild             grader：fresh checkout 上重建 baseline manifest 并比对 digest
    delta_apply                         grader：应用 candidate_solution_delta（或 S1 路径的 git apply）
    test                                grader：官方 eval 脚本运行
    parser_and_report                   grader：官方 parser 解析 + GradingReport 组装
    grader_cleanup                      grader：评分容器移除
    rollout_container_hold_after_freeze 静止确认（冻结）到 rollout 容器真正被移除之间的持有时长
                                        ——D2-1 状态所有权转移的直接度量：正常路径 =
                                        post_census + artifact_capture + artifact_persist + rm

另记两个评分队列事实（来自 GradingTimingRecord）：入队瞬间队列深度、本次是否触发过反压。
run 级"评分队列打满次数" = `GradingQueue.backpressure_count`（进程内计数）+ 本记录按 attempt
聚合出的 `attempts_with_backpressure`。

落盘：`RolloutAudit.lifecycle_timing`（进程内）→ `RolloutAudit.timing_summary()["lifecycle_timing"]`
（bringup 的 execution audit JSONL 已原样写 timing_summary，因此**不需要**改 bringup 就落盘）+
交付路径的 sidecar `attempt_lifecycle_timing.json`。聚合：`aggregate_lifecycle_timings()`（p50/p95，
最近秩法，不依赖 numpy），命令行 `python -m repoharness2.adapters.slime.attempt_timing <audit.jsonl>...`。
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "LIFECYCLE_SEGMENTS",
    "AttemptLifecycleTiming",
    "SegmentStopwatch",
    "aggregate_lifecycle_timings",
    "extract_lifecycle_timing",
    "percentile_nearest_rank",
]

LIFECYCLE_SEGMENTS: tuple[str, ...] = (
    "runtime_quiescence",
    "baseline_census",
    "post_census",
    "artifact_capture",
    "artifact_persist",
    "grading_queue_wait",
    "grader_start_and_verify",
    "grader_baseline_rebuild",
    "delta_apply",
    "test",
    "parser_and_report",
    "grader_cleanup",
    "rollout_container_hold_after_freeze",
)

_GRADER_SEGMENTS: tuple[str, ...] = (
    "grader_start_and_verify",
    "grader_baseline_rebuild",
    "delta_apply",
    "test",
    "parser_and_report",
    "grader_cleanup",
)


@dataclass
class AttemptLifecycleTiming:
    """一次 attempt 的十三段计时 + 队列事实。字段名 = 段名，值 = 秒（None 未发生）。"""

    segments: dict[str, float | None] = field(
        default_factory=lambda: {name: None for name in LIFECYCLE_SEGMENTS}
    )
    grading_queue_depth_at_enqueue: int | None = None
    grading_backpressure_triggered: bool = False
    # grader 内部分段的来源：`manager` = 从 SWEGradingManager 的分段记录取到；`report_only` =
    # 只拿到 GradingTimingRecord（test/queue_wait 可填，其余 grader 段为 None）；None = 未评分。
    grader_segment_source: str | None = None
    clock_domain_id: str = f"proc-{os.getpid()}"

    def set(self, segment: str, seconds: float) -> None:
        if segment not in self.segments:
            raise KeyError(f"未知生命周期分段：{segment!r}（合法：{LIFECYCLE_SEGMENTS}）")
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError(f"分段 {segment!r} 的秒数必须是非负有限数，得到 {seconds!r}")
        self.segments[segment] = round(float(seconds), 6)

    def get(self, segment: str) -> float | None:
        return self.segments[segment]

    def apply_grader_segments(self, source: Mapping[str, float | None], *, origin: str) -> None:
        """把 grader 侧分段（manager 的 GraderPhaseTiming.segments 或按报告推导的子集）合并进来。"""

        for name in _GRADER_SEGMENTS:
            value = source.get(name)
            if value is not None:
                self.set(name, value)
        self.grader_segment_source = origin

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "rh2.attempt_lifecycle_timing.v1",
            "clock_domain_id": self.clock_domain_id,
            "segments_seconds": dict(self.segments),
            "grading_queue_depth_at_enqueue": self.grading_queue_depth_at_enqueue,
            "grading_backpressure_triggered": self.grading_backpressure_triggered,
            "grader_segment_source": self.grader_segment_source,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AttemptLifecycleTiming":
        timing = cls()
        raw = payload.get("segments_seconds") or {}
        for name in LIFECYCLE_SEGMENTS:
            value = raw.get(name)
            if value is not None:
                timing.set(name, float(value))
        depth = payload.get("grading_queue_depth_at_enqueue")
        timing.grading_queue_depth_at_enqueue = int(depth) if depth is not None else None
        timing.grading_backpressure_triggered = bool(payload.get("grading_backpressure_triggered", False))
        timing.grader_segment_source = payload.get("grader_segment_source")
        timing.clock_domain_id = str(payload.get("clock_domain_id") or timing.clock_domain_id)
        return timing


class SegmentStopwatch:
    """monotonic 秒表：`start(name)` / `stop(name)` 成对使用，stop 把差值写进 timing。

    同一段多次 start/stop 累加（例如 grader 的 delta_apply 若分两遍应用，总时长才是有意义的
    数字）；未 start 就 stop 是编程错误（KeyError），不静默。"""

    def __init__(self, timing: AttemptLifecycleTiming) -> None:
        self._timing = timing
        self._open: dict[str, float] = {}

    def start(self, segment: str) -> None:
        if segment not in LIFECYCLE_SEGMENTS:
            raise KeyError(f"未知生命周期分段：{segment!r}")
        self._open[segment] = time.monotonic()

    def stop(self, segment: str) -> float:
        started = self._open.pop(segment)
        elapsed = time.monotonic() - started
        previous = self._timing.get(segment) or 0.0
        self._timing.set(segment, previous + elapsed)
        return elapsed

    def is_open(self, segment: str) -> bool:
        return segment in self._open


def percentile_nearest_rank(values: list[float], q: float) -> float | None:
    """最近秩法百分位（q ∈ [0, 100]）：空列表返回 None。p50/p95 用它，避免引入 numpy。"""

    if not values:
        return None
    if not 0 <= q <= 100:
        raise ValueError(f"q 必须在 [0, 100]，得到 {q}")
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100.0 * len(ordered)))
    return ordered[rank - 1]


def aggregate_lifecycle_timings(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """按 run 聚合：每段 count / p50 / p95 / max / mean，外加反压 attempt 数与 grader 段来源分布。

    输入 = `AttemptLifecycleTiming.to_dict()` 形态的记录（或含 `segments_seconds` 键的任意 mapping）。
    """

    per_segment: dict[str, list[float]] = {name: [] for name in LIFECYCLE_SEGMENTS}
    attempts = 0
    with_backpressure = 0
    depths: list[float] = []
    sources: dict[str, int] = {}
    for rec in records:
        attempts += 1
        segs = rec.get("segments_seconds") or {}
        for name in LIFECYCLE_SEGMENTS:
            value = segs.get(name)
            if value is not None:
                per_segment[name].append(float(value))
        if rec.get("grading_backpressure_triggered"):
            with_backpressure += 1
        depth = rec.get("grading_queue_depth_at_enqueue")
        if depth is not None:
            depths.append(float(depth))
        src = rec.get("grader_segment_source") or "none"
        sources[src] = sources.get(src, 0) + 1
    segments_out: dict[str, dict[str, float | int | None]] = {}
    for name, values in per_segment.items():
        segments_out[name] = {
            "count": len(values),
            "p50": percentile_nearest_rank(values, 50),
            "p95": percentile_nearest_rank(values, 95),
            "max": max(values) if values else None,
            "mean": (sum(values) / len(values)) if values else None,
        }
    return {
        "attempts": attempts,
        "attempts_with_backpressure": with_backpressure,
        "queue_depth_at_enqueue_p50": percentile_nearest_rank(depths, 50),
        "queue_depth_at_enqueue_p95": percentile_nearest_rank(depths, 95),
        "grader_segment_source_counts": sources,
        "segments": segments_out,
    }


def extract_lifecycle_timing(audit_record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """从 bringup execution audit JSONL 的一条记录里取出 lifecycle timing（在 timing_summary 下）。"""

    summary = audit_record.get("timing_summary")
    if not isinstance(summary, Mapping):
        return None
    timing = summary.get("lifecycle_timing")
    return timing if isinstance(timing, Mapping) else None


def _iter_records_from_paths(paths: list[str]) -> Iterable[Mapping[str, Any]]:
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        stripped = text.strip()
        if not stripped:
            continue
        if stripped.startswith("{") and "\n" not in stripped:
            # 单个 JSON 对象（sidecar attempt_lifecycle_timing.json）
            payload = json.loads(stripped)
            yield payload if "segments_seconds" in payload else (extract_lifecycle_timing(payload) or {})
            continue
        for line in text.splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if "segments_seconds" in payload:
                yield payload
                continue
            timing = extract_lifecycle_timing(payload)
            if timing is not None:
                yield timing


def main(argv: list[str] | None = None) -> int:
    """`python -m repoharness2.adapters.slime.attempt_timing <audit.jsonl|timing.json>...`：
    打印 run 级聚合 JSON（p50/p95）。"""

    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("用法：attempt_timing <execution_audit.jsonl | attempt_lifecycle_timing.json>...", file=sys.stderr)
        return 2
    result = aggregate_lifecycle_timings(_iter_records_from_paths(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover - 命令行入口
    raise SystemExit(main())
