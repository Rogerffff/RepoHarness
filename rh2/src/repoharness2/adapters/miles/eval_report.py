"""I21（第五组）：评测点聚合——接管 miles 的 eval 日志钩子，把"评了分 / 评不了分 / 没跑成"分开统计。

接线：``--custom-eval-rollout-log-function-path repoharness2.adapters.miles.eval_report.log_eval_rollout_data``。

为什么必须接管（Codex I21 审查 R1）：评不了分的评测样本交付 ``reward=None``；miles 默认聚合
（``miles/ray/rollout/metrics.py``）虽然把顶层 rewards 里的 None 换成 0，却又在
``_compute_training_sample_metrics`` 里对原始 ``sample.reward`` 求和 → ``TypeError``，经共享引擎
dispatch 会直接停掉训练驱动；即使不崩，``eval/<dataset>`` 也会把缺失计成 0 分。本钩子返回 True
（miles 不再跑默认日志），自己写指标与 ``eval_point`` 事件。

口径（不产出含糊的单一"准确率"）：

- ``resolved_rate_graded``  = resolved / graded（只看评了分的）；
- ``resolved_rate_planned`` = resolved / planned（整体完成比例的下界——缺失不算解决，但也**不**
  被改写成模型答错：缺失计数单列）；
- ``complete`` = 该次评测调用的**唯一成员集合**与计划完全一致（不是总数相等——重复与遗漏可以
  互相抵消），且没有 ``reward_unavailable`` / ``execution_missing`` / 缺载荷样本；
- ``binding`` = ``verified``（宿主目标版本已知、每条评分结果都有版本事实且全部等于目标）/
  ``mismatch``（观察到别的版本）/ ``unverified``（目标未知或缺版本事实）。全体请求恰好使用同一个
  错误版本也满足"单一版本"，所以单一版本不等于绑定正确。

计划集合不从存活样本反推（Codex I21 实施复核 IR2）：miles `Dataset` 在加载时按 `--eval-max-prompt-len` 过滤长
输入并重排 `prompt_index`，宿主事实里的 `num_prompts` 已经是**过滤后**的数目——两题里的长题被过滤后，按存活样本
反推会得到"计划一题、完成一题、完整"。既定题目集合以**评测题包的 prompts.jsonl**（bringup 已按内容 digest 把它与
题包绑定）为准：计划成员 = 文件里每一行的 `task_id` × 每题样本数；没拿到结果的题逐条列为缺失，加载器少载的题数
单列（`prompts_not_loaded`）。全部被过滤（零样本）时靠宿主在**调用级**附带的事实（fork patch 0019 的
`rh2_eval_call`）仍能给出唯一评测点、`complete=False`、`binding=unverified`，不回落 miles 默认日志（它对空列表
除零，异常会经共享引擎 dispatch 停掉训练驱动），也不产出模型 0 分。读不到题包文件时 `planned_source` 不是
`eval_package`，此时不声称完整。

before/after 对比采用哪个分母、是否接受不完整的评测点，由 B 线统计协议决定；这里只保证事实分开。
有样本但都不带 RH2 载荷（s1_compat 冻结路径）时返回 False，沿用 miles 默认日志。
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from repoharness2.adapters.slime.eval_result import (
    EVAL_RESULT_METADATA_KEY,
    RESULT_EXECUTION_MISSING,
    RESULT_GRADED,
    RESULT_REWARD_UNAVAILABLE,
)

logger = logging.getLogger(__name__)

EVAL_POINT_EVENT = "eval_point"
EVAL_POINT_SCHEMA_ID = "rh2.eval_point_summary.v1"
ATTEMPT_ROW_LIMIT = 2000
EVAL_CALL_RESULT_KEY = "rh2_eval_call"  # fork patch 0019：每个数据集结果里的调用级宿主事实
PLANNED_FROM_PACKAGE = "eval_package"
PLANNED_FROM_HOST = "host_loaded_prompts"  # 宿主加载后的 prompt 数（过滤后）——不足以声称既定题单已完成


def _payload_of(sample: Any) -> Mapping[str, Any] | None:
    meta = getattr(sample, "metadata", None)
    if not isinstance(meta, Mapping):
        return None
    payload = meta.get(EVAL_RESULT_METADATA_KEY)
    return payload if isinstance(payload, Mapping) else None


def has_rh2_eval_payload(samples: Iterable[Any]) -> bool:
    return any(_payload_of(s) is not None for s in samples)


def summarize_eval_samples(
    samples: Iterable[Any],
    *,
    call: Mapping[str, Any] | None = None,
    planned_task_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """一个评测数据集在**一次**评测调用里的结果 → typed 汇总（纯函数）。

    ``call`` = 宿主的调用级事实（零样本时评测点身份的唯一来源）；``planned_task_ids`` = 评测题包
    prompts.jsonl 逐行的 task_id（既定题目集合；None = 拿不到，此时只有宿主"加载后"的数目，不声称完整）。
    """

    samples = list(samples)
    call = call if isinstance(call, Mapping) else None
    payload_missing = 0
    by_attempt: dict[str, Mapping[str, Any]] = {}
    duplicate_attempt_rows = 0
    for sample in samples:
        payload = _payload_of(sample)
        if payload is None:
            payload_missing += 1
            continue
        attempt = str(payload.get("physical_attempt_id"))
        if attempt in by_attempt:
            duplicate_attempt_rows += 1  # 同一 attempt 的多片叶只算一条结果
            continue
        by_attempt[attempt] = payload

    points: set[str] = set()
    targets: set[str | None] = set()
    rollout_ids: set[Any] = set()
    sample_counts: set[int] = set()   # 每题样本数 n（宿主事实，必须一致）
    loaded_prompts: set[int] = set()  # 宿主加载后的 prompt 数
    if call is not None:
        points.add(str(call.get("eval_point_id")))
        targets.add(call.get("target_weight_version"))
        rollout_ids.add(call.get("eval_rollout_id"))
    fact_sources = [call] if call is not None else []
    fact_sources.extend((p.get("eval") or {}) for p in by_attempt.values())
    host_facts_inconsistent = False
    for facts in fact_sources:
        try:
            sample_counts.add(int(facts["n_samples_per_eval_prompt"]))
            loaded_prompts.add(int(facts["num_prompts"]))
        except (KeyError, TypeError, ValueError):
            host_facts_inconsistent = True
    host_facts_inconsistent = host_facts_inconsistent or len(sample_counts) > 1 or len(loaded_prompts) > 1
    n = next(iter(sample_counts)) if len(sample_counts) == 1 else None
    host_prompts = next(iter(loaded_prompts)) if len(loaded_prompts) == 1 else None

    members: Counter[tuple[Any, int]] = Counter()
    use_package = planned_task_ids is not None
    for payload in by_attempt.values():
        facts = payload.get("eval") or {}
        points.add(str(facts.get("eval_point_id")))
        targets.add(facts.get("target_weight_version"))
        rollout_ids.add(facts.get("eval_rollout_id"))
        try:
            slot = int(facts["sample_slot"])
            key = str(payload.get("task_id")) if use_package else int(facts["prompt_index"])
        except (KeyError, TypeError, ValueError):
            host_facts_inconsistent = True
            continue
        members[(key, slot)] += 1

    planned_members: Counter[tuple[Any, int]] = Counter()
    if n is not None:
        if use_package:
            for task_id in planned_task_ids or ():
                for slot in range(n):
                    planned_members[(str(task_id), slot)] += 1
        elif host_prompts is not None:
            planned_members = Counter({(pi, slot): 1 for pi in range(host_prompts) for slot in range(n)})
    planned_source = PLANNED_FROM_PACKAGE if use_package else PLANNED_FROM_HOST
    member_label = "task_id" if use_package else "prompt_index"
    missing = sorted((planned_members - members).elements(), key=str)
    unexpected = sorted((members - planned_members).elements(), key=str)
    duplicate_members = sorted((key for key, count in members.items() if count > max(planned_members.get(key, 0), 1)), key=str)
    planned = sum(planned_members.values())
    planned_prompts = len(planned_task_ids) if use_package else host_prompts
    prompts_not_loaded = (
        max(0, len(planned_task_ids) - host_prompts) if use_package and host_prompts is not None else None
    )

    classes = Counter(str(p.get("result_class")) for p in by_attempt.values())
    graded = [p for p in by_attempt.values() if p.get("result_class") == RESULT_GRADED]
    resolved = sum(1 for p in graded if p.get("task_outcome") == "resolved")
    unresolved = len(graded) - resolved
    unavailable_reasons = Counter(
        str(p.get("unavailable_reason"))
        for p in by_attempt.values()
        if p.get("result_class") in (RESULT_REWARD_UNAVAILABLE, RESULT_EXECUTION_MISSING)
    )
    grading_failure_categories = Counter(
        str(p.get("grading_failure_category")) for p in graded if p.get("task_outcome") != "resolved"
    )

    observed_versions: set[str] = set()
    graded_without_versions = 0
    for payload in by_attempt.values():
        versions = [str(v) for v in (payload.get("turn_weight_versions") or [])]
        observed_versions.update(versions)
        if payload.get("result_class") == RESULT_GRADED and not versions:
            graded_without_versions += 1
    known_targets = {t for t in targets if t is not None}
    target = next(iter(known_targets)) if len(known_targets) == 1 and None not in targets else None
    if target is not None and any(v != target for v in observed_versions):
        binding = "mismatch"
    elif target is not None and observed_versions and graded_without_versions == 0:
        binding = "verified"
    else:
        binding = "unverified"

    points.discard("None")
    mixed_eval_points = len(points) > 1
    complete = (
        planned_source == PLANNED_FROM_PACKAGE  # 只有既定题目集合已知时才谈得上"完整"
        and planned > 0
        and not host_facts_inconsistent
        and not mixed_eval_points
        and not missing
        and not unexpected
        and not duplicate_members
        and payload_missing == 0
        and classes.get(RESULT_REWARD_UNAVAILABLE, 0) == 0
        and classes.get(RESULT_EXECUTION_MISSING, 0) == 0
    )
    attempts = [
        {
            "task_id": p.get("task_id"),
            "prompt_index": (p.get("eval") or {}).get("prompt_index"),
            "sample_slot": (p.get("eval") or {}).get("sample_slot"),
            "physical_attempt_id": p.get("physical_attempt_id"),
            "result_class": p.get("result_class"),
            "task_outcome": p.get("task_outcome"),
            "grading_failure_category": p.get("grading_failure_category"),
            "unavailable_reason": p.get("unavailable_reason"),
            "termination_kind": p.get("termination_kind"),
        }
        for p in by_attempt.values()
    ]
    attempts.sort(key=lambda row: (row["prompt_index"] is None, row["prompt_index"], row["sample_slot"]))

    def _member_rows(keys: list[tuple[Any, int]]) -> list[dict[str, Any]]:
        return [{member_label: key, "sample_slot": slot} for key, slot in keys]

    return {
        "schema_id": EVAL_POINT_SCHEMA_ID,
        "eval_point_ids": sorted(points),
        "eval_rollout_ids": sorted(rollout_ids, key=lambda v: (v is None, v)),
        "planned_source": planned_source,
        "planned_prompts": planned_prompts,
        "host_loaded_prompts": host_prompts,
        "prompts_not_loaded": prompts_not_loaded,  # 题包里有、宿主加载后没有的题数（如被长度过滤）；未知为 None
        "samples_per_prompt": n,
        "planned": planned,
        "received": len(by_attempt),
        "graded": len(graded),
        "resolved": resolved,
        "unresolved": unresolved,
        "reward_unavailable": classes.get(RESULT_REWARD_UNAVAILABLE, 0),
        "execution_missing": classes.get(RESULT_EXECUTION_MISSING, 0),
        "payload_missing": payload_missing,
        "duplicate_attempt_rows": duplicate_attempt_rows,
        "missing_members": _member_rows(missing),  # 既定但没有任何结果行：没派发（被过滤 / 没加载）或结果丢失
        "unexpected_members": _member_rows(unexpected),
        "duplicate_members": _member_rows(duplicate_members),
        "host_facts_inconsistent": host_facts_inconsistent,
        "mixed_eval_points": mixed_eval_points,
        "unavailable_reasons": dict(sorted(unavailable_reasons.items())),
        "grading_failure_categories": dict(sorted(grading_failure_categories.items())),
        "resolved_rate_graded": (resolved / len(graded)) if graded else None,
        "resolved_rate_planned": (resolved / planned) if planned else None,
        # 模型的**配置来源**（miles args.hf_checkpoint）与 rh2 模型标签——不是权重已加载的证明：dummy 加载或
        # engine group 覆盖下路径可以相同 / 不同而本字段不变。独立评测作业没有发布版本可作目标，binding 保持
        # unverified；"打算评的是哪个固定导出"看这里，"实际载入了什么"由真实引擎核验。
        "configured_hf_checkpoints": sorted({str(p.get("configured_hf_checkpoint")) for p in by_attempt.values() if p.get("configured_hf_checkpoint")}),
        "model_names": sorted({str(p.get("model_name")) for p in by_attempt.values() if p.get("model_name")}),
        "target_weight_version": target,
        "target_weight_versions_seen": sorted(known_targets),
        "observed_weight_versions": sorted(observed_versions),
        "graded_without_versions": graded_without_versions,
        "binding": binding,
        "complete": complete,
        "attempts": attempts[:ATTEMPT_ROW_LIMIT],
        "attempts_truncated": max(0, len(attempts) - ATTEMPT_ROW_LIMIT),
    }


def planned_task_ids_for(args: Any, dataset_name: str) -> list[str] | None:
    """既定题目集合：评测数据集文件（= 评测题包的 prompts.jsonl，bringup 已按内容 digest 绑定）逐行的 task_id。

    读不到 / 不是 prepared 产物形状（某行没有 `metadata.task_id`）→ None：计划集合未知，不猜。"""

    for cfg in getattr(args, "eval_datasets", None) or ():
        if getattr(cfg, "name", None) != dataset_name:
            continue
        path = getattr(cfg, "path", None)
        metadata_key = getattr(cfg, "metadata_key", None) or getattr(args, "metadata_key", None) or "metadata"
        try:
            task_ids: list[str] = []
            for line in Path(str(path)).read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                task_id = (json.loads(line).get(metadata_key) or {}).get("task_id")
                if not isinstance(task_id, str) or not task_id:
                    return None
                task_ids.append(task_id)
        except (OSError, ValueError, AttributeError, TypeError):
            return None
        return task_ids
    return None


def eval_point_metrics(name: str, summary: Mapping[str, Any]) -> dict[str, float | int]:
    """汇总 → tracking 指标（键名显式，不产出含糊的 ``eval/<name>``）。None 的比率不写。"""

    prefix = f"eval/{name}/"
    metrics: dict[str, float | int] = {
        prefix + key: int(summary[key])
        for key in ("planned", "received", "graded", "resolved", "unresolved", "reward_unavailable",
                    "execution_missing", "payload_missing")
    }
    metrics[prefix + "missing_members"] = len(summary["missing_members"])
    metrics[prefix + "complete"] = int(bool(summary["complete"]))
    metrics[prefix + "binding_verified"] = int(summary["binding"] == "verified")
    for key in ("resolved_rate_graded", "resolved_rate_planned"):
        if summary[key] is not None:
            metrics[prefix + key] = float(summary[key])
    return metrics


def _emit_event(kind: str, **fields: Any) -> bool:
    try:
        from miles.utils import rh2_event_log
    except Exception:  # noqa: BLE001 —— miles 不在路径上：观测面缺席
        return False
    if not rh2_event_log.enabled():
        return False
    rh2_event_log.emit(kind, **fields)
    return True


def _log_tracking(args: Any, rollout_id: Any, metrics: dict[str, Any]) -> None:
    try:
        from miles.utils.metric_utils import compute_rollout_step
        from miles.utils.tracking_utils import tracking
    except Exception:  # noqa: BLE001 —— CPU / 无 miles 环境：只留日志
        return
    log_dict = dict(metrics)
    log_dict["eval/step"] = compute_rollout_step(args, rollout_id)
    tracking.log(args, log_dict, step_key="eval/step")


def log_eval_rollout_data(rollout_id: Any, args: Any, data: Mapping[str, Mapping[str, Any]], extra_metrics: Any = None) -> bool:
    """miles ``custom_eval_rollout_log_function_path`` 钩子。返回 True = 已接管（miles 跳过默认日志）。

    接管条件：有 RH2 评测载荷；**或者所有数据集都是零样本**——miles 默认日志对空列表除零（异常会停掉训练
    驱动），而零样本恰恰是"题全被加载器过滤掉"这类必须如实记成未完成的情形。有样本但都不带载荷
    （s1_compat 冻结路径）→ 返回 False，沿用默认日志。"""

    per_dataset = {name: list((info or {}).get("samples") or []) for name, info in data.items()}
    any_payload = any(has_rh2_eval_payload(samples) for samples in per_dataset.values())
    any_samples = any(per_dataset.values())
    if not any_payload and any_samples:
        return False  # 非 RH2 formal 评测：沿用 miles 默认日志
    metrics: dict[str, Any] = dict(extra_metrics or {})
    for name, samples in per_dataset.items():
        summary = summarize_eval_samples(
            samples, call=(data.get(name) or {}).get(EVAL_CALL_RESULT_KEY), planned_task_ids=planned_task_ids_for(args, name),
        )
        metrics.update(eval_point_metrics(name, summary))
        _emit_event(EVAL_POINT_EVENT, rollout_id=rollout_id, dataset=name, **summary)
        logger.info(
            "rh2 eval point rollout_id=%s dataset=%s planned=%s (%s) received=%s graded=%s resolved=%s "
            "reward_unavailable=%s execution_missing=%s missing_members=%s complete=%s binding=%s",
            rollout_id, name, summary["planned"], summary["planned_source"], summary["received"], summary["graded"],
            summary["resolved"], summary["reward_unavailable"], summary["execution_missing"],
            len(summary["missing_members"]), summary["complete"], summary["binding"],
        )
    _log_tracking(args, rollout_id, metrics)
    return True


__all__ = [
    "EVAL_POINT_EVENT",
    "EVAL_POINT_SCHEMA_ID",
    "eval_point_metrics",
    "has_rh2_eval_payload",
    "log_eval_rollout_data",
    "planned_task_ids_for",
    "summarize_eval_samples",
]
