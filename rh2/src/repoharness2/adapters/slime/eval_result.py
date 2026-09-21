"""I21（第五组）：评测 attempt 的 typed 结果载荷——三类分开，不把"评不了分 / 没跑成"记成 0 分。

背景：训练面靠 admission 载荷 + NaN 占位守住 P4 红线（基础设施失败绝不落 reward=0）；评测面此前
没有对应保护——交付面的 eval 占位写 ``float(grading_reward or 0.0)``、abort 形状写 ``reward = 0.0``，
基础设施失败会被评测统计算成模型 0 分。

本模块只有纯函数，三处共用同一份派生结果（不另建 outcome 库、不存在先落空块再补的窗口）：

- ``RolloutOrchestrator._generate_attempt`` 的 finally 调 audit sink → bringup 落盘 ``evaluation`` 块；
- ``RolloutOrchestrator.generate()`` 出口 → 盖到交付叶的 ``metadata["rh2_eval_result"]`` 并规范化占位样本；
- ``Rh2MilesGenerateFn`` 在身份盖章后核对载荷与本叶身份一致。

三类 ``result_class``：

===================  =====================================================  ==========================
graded               评分报告 resolved / unresolved（含评分侧失败类别）      reward = 1.0 / 0.0，completed
reward_unavailable   ``failed_to_grade``、unsafe artifact 永久拒绝            reward = None，aborted
execution_missing    Outcome 为 missing（harness / sandbox / 代理等已归因）   reward = None，aborted
===================  =====================================================  ==========================

miles ``generate_and_rm`` 对 ABORTED 样本不调 RM，所以 ``reward=None`` 不会触发 rm hub。s1_compat
冻结路径不经过本模块。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

EVAL_RESULT_METADATA_KEY = "rh2_eval_result"
EVAL_RESULT_SCHEMA_ID = "rh2.eval_attempt_result.v1"
RESULT_GRADED = "graded"
RESULT_REWARD_UNAVAILABLE = "reward_unavailable"
RESULT_EXECUTION_MISSING = "execution_missing"
RESULT_CLASSES = (RESULT_GRADED, RESULT_REWARD_UNAVAILABLE, RESULT_EXECUTION_MISSING)

# 与 adapters/miles/identity.py 的键名逐字一致（本模块不 import miles 适配层，避免成环）。
_ATTEMPT_ID_KEY = "rh2_physical_attempt_id"
_EXECUTION_ID_KEY = "rh2_rollout_execution_id"
_EVAL_DISPATCH_METADATA_KEY = "rh2_eval_dispatch"
_DETAIL_LIMIT = 300


class EvalResultError(RuntimeError):
    """评测结果载荷的接线 / 对账错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


def derive_eval_attempt_result(audit: Any, *, model_name: str | None = None) -> dict[str, Any] | None:
    """从 audit **已有事实**派生评测结果载荷；非评测 attempt 返回 None。

    只读 audit：Outcome v2（终止 / 完成类别 / 逐轮权重版本）、评分报告（结论 / 失败类别）、unsafe
    原因、失败记录。同一 audit 多次调用结果相同，sink 落盘与出口盖章因此不会分家。
    """

    if not getattr(audit, "evaluation", False):
        return None
    outcome = getattr(audit, "outcome_v2", None) or {}
    finalized = getattr(audit, "finalized", None)
    report = getattr(finalized, "grading_report", None) if finalized is not None else None
    unsafe_reasons = list(getattr(audit, "unsafe_artifact_reasons", None) or [])
    failure_records = list(getattr(audit, "failure_records", None) or [])

    task_outcome: str | None = None
    reward: float | None = None
    grading_failure_category: str | None = None
    unavailable_reason: str | None = None
    unavailable_detail: str | None = None
    if report is not None and report.reward is not None:
        result_class = RESULT_GRADED
        task_outcome = "resolved" if report.outcome == "resolved" else "unresolved"
        reward = float(report.reward)
        grading_failure_category = report.failure_category
    elif report is not None:
        result_class = RESULT_REWARD_UNAVAILABLE
        grading_failure_category = report.failure_category
        unavailable_reason = f"grading:{report.failure_category}"
        unavailable_detail = getattr(report, "infra_failure_detail", None)
    elif unsafe_reasons:
        result_class = RESULT_REWARD_UNAVAILABLE
        unavailable_reason = "unsafe_artifact"
        unavailable_detail = unsafe_reasons[0]
    else:
        result_class = RESULT_EXECUTION_MISSING
        last = failure_records[-1] if failure_records else None
        unavailable_reason = str(
            outcome.get("reason_code")
            or outcome.get("failure_category")
            or getattr(audit, "termination_kind_hint", None)
            or (getattr(last, "error_type", None) if last is not None else None)
            or "unknown"
        )
        if last is not None:
            unavailable_detail = f"{last.stage}:{last.error_type}"
    deadline = getattr(audit, "episode_deadline", None) or {}
    return {
        "schema_id": EVAL_RESULT_SCHEMA_ID,
        "eval": dict(getattr(audit, "eval_dispatch", None) or {}),
        "task_id": getattr(audit, "task_id", None),
        "physical_attempt_id": getattr(audit, "physical_attempt_id", None),
        "rollout_execution_id": getattr(audit, "trajectory_id", None),
        "result_class": result_class,
        "task_outcome": task_outcome,
        "reward": reward,
        "grading_failure_category": grading_failure_category,
        "unavailable_reason": unavailable_reason,
        "unavailable_detail": (str(unavailable_detail)[:_DETAIL_LIMIT] if unavailable_detail else None),
        "termination_kind": outcome.get("termination_kind") or getattr(audit, "termination_kind_hint", None),
        "completion_class": outcome.get("completion_class"),
        "turn_weight_versions": [str(v) for v in (outcome.get("turn_weight_versions") or [])],
        "current_version_at_finalize": outcome.get("current_version_at_finalize"),
        "grading_report_id": getattr(report, "report_id", None),
        "grader_version": getattr(report, "grader_version", None),
        "model_name": model_name,
        # 配置来源（miles args.hf_checkpoint），不是权重已加载的证明
        "configured_hf_checkpoint": getattr(audit, "configured_hf_checkpoint", None),
        "runtime_profile_digest": getattr(audit, "runtime_profile_digest", None),
        "time_budget_seconds": deadline.get("budget_seconds"),
    }


def _leaves(output: Any) -> list[Any]:
    if isinstance(output, list):
        found: list[Any] = []
        for item in output:
            found.extend(_leaves(item))
        return found
    return [output]


def shape_eval_placeholder(sample: Any, *, tape_top_p: float | None) -> None:
    """把**输入样本**塑成评测占位形状（与交付面 eval 占位 / abort 形状逐字段同形）。

    ``tape_top_p`` 与编排入口的同名量同一条规则：mask 链路（``args.rh2_engine_sampling_mask``）为 None
    ——miles Sample 没有旧 slime 的零宽 top-p tape 字段，写了会被 canonicalize 按未知属性拒绝；旧 slime
    wire 且 top_p<1 时才回填零宽 tape。
    """

    sample.tokens = [0, 0]
    sample.response = ""
    sample.response_length = 1
    sample.loss_mask = [0]
    sample.rollout_log_probs = [0.0]
    if tape_top_p is not None and tape_top_p < 1.0:
        sample.rollout_top_p_token_ids = []
        sample.rollout_top_p_token_offsets = [0, 0]


def apply_eval_result(
    delivered: Any,
    payload: Mapping[str, Any],
    *,
    set_status: Callable[[Any, str], None],
    carrier: Any | None = None,
    tape_top_p: float | None = None,
    training_payload_keys: tuple[str, ...] = (),
) -> list[Any]:
    """把载荷盖到**不进训练的结果载体**上，规范化成一条评测样本（一次 attempt = 一条评测结果）。

    载体统一是本次 generate 的**输入样本**（``carrier``）：评了分的 eval 占位与 abort 形状本来就是它；
    unsafe artifact 路径交付的是 vendor 叶链（真实 token，可能多行）——评测不训练这些 token，若拿 vendor
    叶做载体，`Rh2MilesGenerateFn` 会按**训练**配置的 ``rollout_top_p`` 走 slime→miles 构造分支并要求训练用
    sampling mask（Codex I21 实施复核 IR1：训练 top_p=0.95、评测 top_p=1 时，本应记为"评不了分"的结果变成
    ``sampling_mask_required`` 异常，经共享引擎 dispatch 停掉训练驱动）。改用输入样本后三类结果都走 miles
    直通分支；不给评测补伪造 mask，不要求评测 top_p 与训练相同，训练面的 mask 要求原样保留。

    - reward 不可得 → ``None`` + ABORTED（不是 0.0，也不是 NaN：miles 聚合对 NaN 会整体变 NaN）；
    - ``training_payload_keys``（训练 admission 载荷等）不留在评测样本上：两个平面不混。
    ``carrier=None`` 时退回"第一片交付叶"（只给不经过 miles 入口的调用方 / 旧测试面）。
    """

    leaves = _leaves(delivered)
    if carrier is None:
        if not leaves:
            raise EvalResultError("eval_delivery_empty", "评测 attempt 没有任何交付叶——无处盖结果载荷。")
        carrier = leaves[0]
    elif not any(leaf is carrier for leaf in leaves):
        shape_eval_placeholder(carrier, tape_top_p=tape_top_p)
    meta = dict(getattr(carrier, "metadata", None) or {})
    for key in training_payload_keys:
        meta.pop(key, None)
    if payload.get("task_id") is not None:
        meta.setdefault("instance_id", payload["task_id"])
    meta[EVAL_RESULT_METADATA_KEY] = dict(payload)
    carrier.metadata = meta
    graded = payload.get("result_class") == RESULT_GRADED
    carrier.reward = payload.get("reward") if graded else None
    carrier.remove_sample = True
    set_status(carrier, "completed" if graded else "aborted")
    return [carrier]


def verify_eval_result_binding(output: Any) -> None:
    """交付面自检（`Rh2MilesGenerateFn` 在身份盖章之后调用）：每片评测叶必须带结果载荷，且载荷的
    attempt / execution / 评测点与本叶身份、宿主派发事实逐字一致——缺失或错配 = 接线矛盾。"""

    for leaf in _leaves(output):
        meta = getattr(leaf, "metadata", None)
        if not isinstance(meta, Mapping) or not isinstance(meta.get(EVAL_RESULT_METADATA_KEY), Mapping):
            raise EvalResultError(
                "eval_result_missing",
                "formal 评测派发的交付叶没有 rh2_eval_result 载荷——编排出口未盖章（接线矛盾），拒绝交付。",
            )
        payload = meta[EVAL_RESULT_METADATA_KEY]
        if payload.get("result_class") not in RESULT_CLASSES:
            raise EvalResultError("eval_result_malformed", f"result_class={payload.get('result_class')!r} 不在三类之内。")
        for leaf_key, payload_key in ((_ATTEMPT_ID_KEY, "physical_attempt_id"), (_EXECUTION_ID_KEY, "rollout_execution_id")):
            if meta.get(leaf_key) != payload.get(payload_key):
                raise EvalResultError(
                    "eval_result_binding_mismatch",
                    f"载荷 {payload_key}={payload.get(payload_key)!r} 与叶身份 {leaf_key}={meta.get(leaf_key)!r} 不一致"
                    "——结果串到了别的 attempt，拒绝交付。",
                )
        host = meta.get(_EVAL_DISPATCH_METADATA_KEY)
        if isinstance(host, Mapping) and (payload.get("eval") or {}).get("eval_point_id") != host.get("eval_point_id"):
            raise EvalResultError(
                "eval_result_binding_mismatch",
                f"载荷评测点 {(payload.get('eval') or {}).get('eval_point_id')!r} 与宿主派发事实 "
                f"{host.get('eval_point_id')!r} 不一致，拒绝交付。",
            )


__all__ = [
    "EVAL_RESULT_METADATA_KEY",
    "EVAL_RESULT_SCHEMA_ID",
    "RESULT_CLASSES",
    "RESULT_EXECUTION_MISSING",
    "RESULT_GRADED",
    "RESULT_REWARD_UNAVAILABLE",
    "EvalResultError",
    "apply_eval_result",
    "derive_eval_attempt_result",
    "shape_eval_placeholder",
    "verify_eval_result_binding",
]
