"""W1b 第二段：交付面 typed admission 载荷 + 三终态薄处置边界（06 计划 §3 W1b 行 / §4 D1 / 附录 A）。

本模块回答两个问题，且**只**回答这两个问题：

1. **一个完整 finalize 的成员，交付给 miles 时带什么 typed 事实？**
   `AdmissionPayloadV1`——由 producer（`adapters/slime/generate.py` 的交付面）从既有权威对象
   派生：`RolloutAttemptOutcomeV2`（completion/termination/失败归因的权威）+
   `EligibilityReport`（七维事实与三档结论的权威，closed 豁免集下可为 None）+ GradingReport
   摘要 + finalize-time lag 观测值 + 环境/分派身份锚。载荷以 `rh2_admission` 键盖到
   Sample.metadata，**只作运输值**：消费方（miles 复合 group filter）在消费时刻
   `model_validate` 重跑全部契约校验（EligibilityReport 的 facts_digest 重算、online⇒七维全过、
   security⇒audit、派生视图互检；Outcome v2 的全部不变量），再与样本自身的六字段身份、分派
   三元组、termination 事实逐字对账。不建 durable ledger，不在热路径扫盘。

2. **一个成员的 final admission 结论是什么？**
   纯函数 `decide_member_disposition(payload, policy=...)`
   → `KEEP_FULL | DROP_GROUP | FATAL`（**不设 MASK_MEMBER**，D1-1a）。判定按附录 A 两层：

   第一层（Outcome / 对象生命周期，权威 = completion_class）：
     结构/身份/引用矛盾                        → FATAL
     completion_class=missing                  → 不该出现在交付面（missing 成员由交付面编码为
                                                  ABORTED，miles put() 先于 filter 处理）→ FATAL
     present_complete / present_truncated       → 进入第二层
   第二层（Eligibility / Admission，权威 = 七维 reason_code）：
     无 EligibilityReport 且命中契约封闭豁免集   → DROP_GROUP（grading_infra_failure /
                                                  unsafe_artifact_permanent_rejection，均 reward 不可得）
     无 EligibilityReport 且不在豁免集           → FATAL（Outcome v2 契约本身已不可表示，此处兜底）
     合法、完整但不满足 online 条件               → DROP_GROUP（filter keep=False，整组固定丢弃）
     账实矛盾（含版本事实缺失/非法）             → FATAL
     hygiene / agent executed 违规               → pending（D2/A4）：显式注入 disposition，未注入即 fail-fast
     七维全过                                    → 再应用显式 termination disposition（A5 归 C：
                                                  未注入即 fail-fast）→ KEEP_FULL / DROP_GROUP

   reason_code → 终态的逐条映射见 `_DIMENSION_REASON_VERDICTS` / `_REASON_PREFIX_VERDICTS`
   （附录 A 表逐行对应，测试逐行钉死）。**未登记的 reason_code 一律 FATAL**——新增 gate 理由码
   而没有登记处置，是接线缺口，不许被补采掩盖。

"显式注入、未注入即 fail-fast"的落实：`DispositionPolicy` 的四个槽位默认全为 None（没有任何
隐藏默认答案）；纯函数**只在该槽位真正决定结论时**读取它——其它维度已经 DROP 时不读（附录 A：
"七维全过再应用 disposition"）；读到 None 即抛 `DispositionNotInjectedError`，调用方（filter）
不捕获，让 miles 的 put() 当场失败而不是静默 keep/drop。本地测试对同一 present_truncated
载荷分别注入 KEEP_FULL / DROP_GROUP，证明链路对 A5 的取值中立。

staleness（B-1 改判 D1-4，决策包 D2+B v2，owner 2026-09-04 已批）：本函数只消费
EligibilityReport **已有**的 policy_staleness 维（"版本事实可用且合法"：`staleness_facts_missing` /
`staleness_facts_invalid` 都是版本账目错误 → FATAL），**不再有** finalize-time 阈值参数、
`staleness_threshold_not_configured` / `staleness_threshold_authority_mismatch` 与 `staleness_exceeded`
→ DROP_GROUP 映射。consume-time staleness 的唯一权威是 miles `DefaultDataBuffer.get()` +
`--max-weight-staleness N`（W4 接线；N 是 profile 参数）。载荷里的 `finalize_staleness_steps`
只是 finalize 时刻 lag 的观测值，本模块不用它做判定。

security（D2-2 / D2-4 同批）：每轨迹 sandbox 能力事实三族理由码（missing / unverified_* /
violation_*）与 `public_projection_marker_hit` 已随 gate 一起删除，不再登记——若旧报告仍带这些
code，按"未登记 reason_code 一律 FATAL"处理（停机，不静默 DROP）。

本模块零 miles/slime import（只依赖 contracts），CPU 任意环境可导；它消费 gate 的产物，不是
gate 的绕行路径（governance 包"唯一公开可调用函数是 finalize_rollout"的纪律针对 gate/scan
的执行函数，本模块的公开函数由 tests/governance/test_governance_api_surface.py 单独钉死）。
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from repoharness2.contracts._base import NonEmptyStr, StrictModel
from repoharness2.contracts.eligibility import EligibilityReport
from repoharness2.contracts.fa_runtime import (
    TERMINATION_KINDS_CONTROL,
    TERMINATION_KINDS_POLICY_HORIZON,
    TERMINATION_KINDS_WATCHDOG,
    RolloutAttemptOutcomeV2,
    is_unsafe_artifact_rejection_shape,
)
from repoharness2.contracts.grading import GradingOutcome, GradingReport
from repoharness2.contracts.handshake import BackendHandshake

__all__ = [
    "ADMISSION_METADATA_KEY",
    "DERIVED_VIEW_CLASS_KEY",
    "DERIVED_VIEW_REPORT_REF_KEY",
    "AdmissionError",
    "AdmissionPayloadV1",
    "DispositionChoice",
    "DispositionNotInjectedError",
    "DispositionPolicy",
    "MemberDisposition",
    "MemberVerdict",
    "decide_member_disposition",
    "derive_admission_payload",
    "resolve_admission_payload",
    "stamp_admission_payload",
    "truncation_slot",
]

# 交付样本 metadata 上的落点键（系统保留前缀 rh2_；值 = AdmissionPayloadV1 的 JSON dump）。
ADMISSION_METADATA_KEY = "rh2_admission"
# 宿主派生视图白名单键（contracts/eligibility.py 载体规则 2）——与 generate.py 逐字一致。
DERIVED_VIEW_REPORT_REF_KEY = "eligibility_report_ref"
DERIVED_VIEW_CLASS_KEY = "training_eligibility_class"
# 与 adapters/miles/identity.py / envpack/prepared_tasks.py 逐字一致的身份键（governance 不 import
# adapters/envpack，字面量钉死；错动即 join 失败而不是静默放行）。
_ATTEMPT_ID_KEY = "rh2_physical_attempt_id"
_EXECUTION_ID_KEY = "rh2_rollout_execution_id"
_TASK_ID_KEY = "task_id"
_ENV_DIGEST_KEY = "environment_package_digest"
_PUBLIC_DIGEST_KEY = "public_bundle_digest"

MemberVerdict = Literal["KEEP_FULL", "DROP_GROUP", "FATAL"]
DispositionChoice = Literal["KEEP_FULL", "DROP_GROUP"]
_CHOICES: frozenset[str] = frozenset({"KEEP_FULL", "DROP_GROUP"})


class AdmissionError(ValueError):
    """admission 边界 fail-closed 错误（reason_code 机器可读）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


class DispositionNotInjectedError(AdmissionError):
    """处置槽位在真正决定结论时仍为 None——A5（C 包）/ A4（D2）尚未拍板，没有隐藏默认答案。"""

    def __init__(self, slot: str, message: str) -> None:
        self.slot = slot
        super().__init__(f"disposition_not_injected:{slot}", message)


@dataclass(frozen=True)
class DispositionPolicy:
    """待拍板处置的显式注入位。四个槽位默认全部 None = 未注入。

    - `policy_horizon_truncation`（A5-a）：task_token_budget_exhausted / max_turns_exhausted /
      context_limit_reached 导致的 present_truncated；
    - `hard_wall_truncation`（A5-b）：hard_wall_timeout 导致的 present_truncated；
    - `owner_cancelled_truncation`（A5-c）：owner_cancelled 导致的 present_truncated；
    - `agent_violation`（A4/D2）：hygiene 实锤篡改 / anti-cheat executed 级违规的成员。

    取值只允许 KEEP_FULL / DROP_GROUP（不设 MASK_MEMBER）。本类不携带任何推荐值——推荐写在
    06 计划里，代码里只有"注入了什么就是什么"。
    """

    policy_horizon_truncation: DispositionChoice | None = None
    hard_wall_truncation: DispositionChoice | None = None
    owner_cancelled_truncation: DispositionChoice | None = None
    agent_violation: DispositionChoice | None = None

    def __post_init__(self) -> None:
        for name in (
            "policy_horizon_truncation",
            "hard_wall_truncation",
            "owner_cancelled_truncation",
            "agent_violation",
        ):
            value = getattr(self, name)
            if value is not None and value not in _CHOICES:
                raise AdmissionError(
                    "disposition_choice_invalid",
                    f"DispositionPolicy.{name}={value!r} 不在 {sorted(_CHOICES)} 内（不设 MASK_MEMBER）。",
                )


def truncation_slot(termination_kind: str) -> Literal["policy_horizon", "hard_wall", "owner_cancelled"]:
    """present_truncated 的 termination_kind → DispositionPolicy 槽位名（五族划分的三个截断族）。"""

    if termination_kind in TERMINATION_KINDS_POLICY_HORIZON:
        return "policy_horizon"
    if termination_kind in TERMINATION_KINDS_WATCHDOG:
        return "hard_wall"
    if termination_kind in TERMINATION_KINDS_CONTROL:
        return "owner_cancelled"
    raise AdmissionError(
        "truncation_kind_not_truncation",
        f"termination_kind={termination_kind!r} 不属于任何截断族（契约上 present_truncated 不可能携带它）。",
    )


# ---------------------------------------------------------------------------
# 交付面载荷
# ---------------------------------------------------------------------------


class AdmissionPayloadV1(StrictModel):
    """交付面 typed admission 载荷（W1b 第二段）。

    全部字段派生自既有权威对象（构造只经 `derive_admission_payload`）。内嵌完整的
    `RolloutAttemptOutcomeV2` 与 `EligibilityReport`：消费时 `model_validate` 会重跑两者的全部
    契约校验（含 facts_digest 重算）——这是不建 ledger、不扫盘也能"全量核对"的唯一办法，
    且不引入第二份可独立修改的资格结论。
    """

    schema_id: Literal["rh2.admission_payload.v1"] = Field(default="rh2.admission_payload.v1")
    physical_attempt_id: NonEmptyStr = Field(description="主键：与样本 rh2_physical_attempt_id 逐字比对。")
    rollout_execution_id: NonEmptyStr = Field(description="= 六字段身份的 rh2_rollout_execution_id（= 轨迹 id）。")
    task_id: NonEmptyStr = Field(description="任务身份锚（与样本 task_id / termination 事实 task_id 比对）。")
    public_bundle_digest: NonEmptyStr = Field(description="RolloutTaskSpec.public_bundle_digest（分派三元组之一）。")
    environment_package_digest: NonEmptyStr | None = Field(
        default=None, description="EnvironmentPackageV1.digest()（prepared 链在场；legacy v1 链为 None）。"
    )
    outcome: RolloutAttemptOutcomeV2 = Field(description="completion/termination/失败归因权威（typed 内嵌）。")
    eligibility_report: EligibilityReport | None = Field(
        default=None, description="七维事实与三档结论权威（typed 内嵌）；契约封闭豁免集下为 None。"
    )
    grading_report_id: NonEmptyStr | None = Field(default=None)
    grading_outcome: GradingOutcome | None = Field(default=None)
    grading_reward: float | None = Field(default=None, description="GradingReport.reward（不可得时 None）。")
    finalize_staleness_steps: int | None = Field(
        default=None,
        ge=0,
        description=(
            "finalize 时刻握手记录的 lag（current − min(seen)）——**只作观测值**（B-1）：不参与"
            "任何准入判定，consume-time staleness 由 miles buffer.get() 按 --max-weight-staleness 判。"
            "None = 无握手事实（此时 report 的 policy_staleness 维必以 staleness_facts_missing 失败）。"
        ),
    )

    @model_validator(mode="after")
    def _check_payload_consistency(self) -> "AdmissionPayloadV1":
        oc = self.outcome
        if oc.identity.physical_attempt_id != self.physical_attempt_id:
            raise ValueError(
                f"outcome.identity.physical_attempt_id={oc.identity.physical_attempt_id!r} != "
                f"physical_attempt_id={self.physical_attempt_id!r}（错 attempt 的 outcome）。"
            )
        if oc.identity.rollout_execution_id != self.rollout_execution_id:
            raise ValueError(
                f"outcome.identity.rollout_execution_id={oc.identity.rollout_execution_id!r} != "
                f"rollout_execution_id={self.rollout_execution_id!r}（错 execution 的 outcome）。"
            )
        if oc.completion_class == "missing":
            raise ValueError("completion_class=missing 的 attempt 没有交付面（它由交付面编码为 ABORTED），不得构造载荷。")
        report = self.eligibility_report
        if (report is None) != (oc.eligibility_report_id is None):
            raise ValueError(
                f"eligibility_report 在场性({report is not None}) 与 outcome.eligibility_report_id"
                f"({oc.eligibility_report_id!r}) 不一致（账实矛盾）。"
            )
        if report is not None:
            if report.report_id != oc.eligibility_report_id:
                raise ValueError(
                    f"eligibility_report.report_id={report.report_id!r} != outcome.eligibility_report_id="
                    f"{oc.eligibility_report_id!r}（报告绑定错位）。"
                )
            if report.trajectory_id != self.rollout_execution_id:
                raise ValueError(
                    f"eligibility_report.trajectory_id={report.trajectory_id!r} != rollout_execution_id="
                    f"{self.rollout_execution_id!r}（报告属于别的轨迹）。"
                )
        if oc.reward_unavailable != (self.grading_reward is None):
            raise ValueError(
                f"outcome.reward_unavailable={oc.reward_unavailable} 与 grading_reward={self.grading_reward!r} "
                "矛盾（reward 可得性两处账目不一致）。"
            )
        if self.grading_reward is not None and not math.isfinite(self.grading_reward):
            raise ValueError("grading_reward 必须是有限数（NaN/inf 不是可信 reward）。")
        if self.grading_report_id is None:
            if self.grading_outcome is not None or self.grading_reward is not None:
                raise ValueError("无 grading_report_id 却携带 grading_outcome/grading_reward（评分引用矛盾）。")
        else:
            if self.grading_outcome is None:
                raise ValueError("有 grading_report_id 必须携带 grading_outcome。")
            if self.grading_outcome == "failed_to_grade":
                if self.grading_reward is not None:
                    raise ValueError("failed_to_grade 的 reward 必须不可得（P4：infra 绝不落 reward）。")
                if oc.failure_category != "grading_infra_failure":
                    raise ValueError(
                        "failed_to_grade 必须对应 outcome.failure_category=grading_infra_failure"
                        f"（得到 {oc.failure_category!r}）。"
                    )
            else:
                if self.grading_reward is None:
                    raise ValueError(f"grading_outcome={self.grading_outcome} 却无 reward（评分结论与 reward 矛盾）。")
                if oc.failure_category is not None:
                    raise ValueError(
                        f"评分成功（{self.grading_outcome}）却携带 outcome.failure_category={oc.failure_category!r}。"
                    )
                expected_task_outcome = "resolved" if self.grading_outcome == "resolved" else "unresolved"
                if oc.task_outcome != expected_task_outcome:
                    raise ValueError(
                        f"grading_outcome={self.grading_outcome} 对应 task_outcome 应为 {expected_task_outcome}，"
                        f"得到 {oc.task_outcome!r}。"
                    )
        if report is not None:
            # 观测值与报告互洽：握手缺席 ⟺ policy_staleness 维以 staleness_facts_missing 失败
            # （只核对"在场性"，不核对任何阈值——阈值判定不在 RH2 finalize 面）。
            dim = report.facts.policy_staleness
            missing = (not dim.ok) and "staleness_facts_missing" in dim.reason_codes
            if (self.finalize_staleness_steps is None) != missing:
                raise ValueError(
                    f"finalize_staleness_steps={self.finalize_staleness_steps!r} 与 policy_staleness 维"
                    f"（ok={dim.ok}, reason_codes={dim.reason_codes}）矛盾：握手缺席当且仅当该维以 "
                    "staleness_facts_missing 失败。"
                )
        return self


def derive_admission_payload(
    *,
    outcome: RolloutAttemptOutcomeV2,
    eligibility_report: EligibilityReport | None,
    grading_report: GradingReport | None,
    handshake: BackendHandshake | None,
    task_id: str,
    public_bundle_digest: str,
    environment_package_digest: str | None,
) -> AdmissionPayloadV1:
    """producer 唯一入口：由既有权威对象派生载荷（构造即跑全部一致性校验，矛盾即拒）。"""

    if outcome.identity.physical_attempt_id is None:
        raise AdmissionError("attempt_identity_missing", "Outcome v2 无 physical_attempt_id——admission 载荷无主键。")
    try:
        return AdmissionPayloadV1(
            physical_attempt_id=outcome.identity.physical_attempt_id,
            rollout_execution_id=outcome.identity.rollout_execution_id,
            task_id=task_id,
            public_bundle_digest=public_bundle_digest,
            environment_package_digest=environment_package_digest,
            outcome=outcome,
            eligibility_report=eligibility_report,
            grading_report_id=grading_report.report_id if grading_report is not None else None,
            grading_outcome=grading_report.outcome if grading_report is not None else None,
            grading_reward=grading_report.reward if grading_report is not None else None,
            finalize_staleness_steps=handshake.staleness_steps if handshake is not None else None,
        )
    except ValidationError as exc:
        raise AdmissionError("admission_payload_inconsistent", f"admission 载荷派生失败：{exc}") from exc


def stamp_admission_payload(output: Any, payload: AdmissionPayloadV1) -> None:
    """producer 落点：把载荷盖到本次交付的全部叶（list 递归，形状不改）。

    规则与 termination 事实的 `stamp_termination_facts` 同：叶上已带六字段身份时 attempt/
    execution 必须一致；叶上已带**不同**载荷只放行"同一样本对象上一次 attempt 留下的历史"
    （miles reset_for_retry 保留 metadata），其余视为 fan-out 叶伪造 / 串入别的 attempt，拒绝。
    """

    if isinstance(output, list):
        for item in output:
            stamp_admission_payload(item, payload)
        return
    meta = getattr(output, "metadata", None)
    if not isinstance(meta, dict):
        raise AdmissionError(
            "member_metadata_not_writable",
            f"交付样本 metadata 不是 dict（得到 {type(meta).__name__}）——admission 载荷无处安放。",
        )
    own_attempt = meta.get(_ATTEMPT_ID_KEY)
    if own_attempt is not None and own_attempt != payload.physical_attempt_id:
        raise AdmissionError(
            "admission_stamp_attempt_mismatch",
            f"交付叶 attempt {own_attempt!r} 与载荷 attempt {payload.physical_attempt_id!r} 不一致。",
        )
    own_execution = meta.get(_EXECUTION_ID_KEY)
    if own_execution is not None and own_execution != payload.rollout_execution_id:
        raise AdmissionError(
            "admission_stamp_execution_mismatch",
            f"交付叶 execution {own_execution!r} 与载荷 execution {payload.rollout_execution_id!r} 不一致。",
        )
    new = payload.model_dump(mode="json")
    existing = meta.get(ADMISSION_METADATA_KEY)
    if existing is not None and existing != new:
        stale_retry_history = (
            isinstance(existing, Mapping)
            and own_attempt == payload.physical_attempt_id
            and existing.get("physical_attempt_id") != payload.physical_attempt_id
        )
        if not stale_retry_history:
            raise AdmissionError(
                "admission_stamp_conflict",
                "交付叶已带不同的 admission 载荷——fan-out 叶伪造 / 串入别的 attempt 的载荷，拒绝。",
            )
    meta[ADMISSION_METADATA_KEY] = new


def resolve_admission_payload(sample_metadata: Any, *, require_dispatch_identity: bool = False) -> AdmissionPayloadV1:
    """consumer 侧 join：解出载荷（重跑全部契约校验）并与样本自身身份/分派/派生视图逐字核对。

    核对项：attempt id、execution id、task_id / environment_package_digest / public_bundle_digest
    （`require_dispatch_identity=True`——组准入 filter 用——三键**必须在场**且与载荷逐字相等，且载荷的
    environment_package_digest 必须非 None；False 时只在样本带该键时比较，供交付面自检/legacy 链）、
    `eligibility_report_ref` / `training_eligibility_class` 派生视图（有报告时必须在场且相等；
    无报告时必须缺席）。
    """

    if not isinstance(sample_metadata, Mapping):
        raise AdmissionError("admission_payload_missing", "样本 metadata 不是 Mapping——无 admission 载荷可 join。")
    raw = sample_metadata.get(ADMISSION_METADATA_KEY)
    if raw is None:
        raise AdmissionError(
            "admission_payload_missing",
            f"样本没有 admission 载荷（{ADMISSION_METADATA_KEY} 缺失）——完整 finalize 的成员必带，fail-closed。",
        )
    try:
        payload = AdmissionPayloadV1.model_validate(raw)
    except ValidationError as exc:
        raise AdmissionError("admission_payload_invalid", f"admission 载荷未通过契约校验：{exc}") from exc
    attempt = sample_metadata.get(_ATTEMPT_ID_KEY)
    if not attempt:
        raise AdmissionError("attempt_identity_missing", "样本没有 rh2_physical_attempt_id——载荷无法归属到样本自身的 attempt。")
    if attempt != payload.physical_attempt_id:
        raise AdmissionError(
            "admission_attempt_mismatch",
            f"样本 attempt {attempt!r} 与载荷 attempt {payload.physical_attempt_id!r} 不一致（同题 sibling / 旧 retry / 错 attempt）。",
        )
    execution = sample_metadata.get(_EXECUTION_ID_KEY)
    if not execution:
        raise AdmissionError("execution_identity_missing", "样本没有 rh2_rollout_execution_id——载荷无法归属到样本自身的 trajectory。")
    if execution != payload.rollout_execution_id:
        raise AdmissionError(
            "admission_execution_mismatch",
            f"样本 execution {execution!r} 与载荷 execution {payload.rollout_execution_id!r} 不一致（错 trajectory）。",
        )
    if require_dispatch_identity and payload.environment_package_digest is None:
        raise AdmissionError(
            "admission_environment_identity_missing",
            "载荷无 environment_package_digest——组准入要求 prepared 链的完整分派三元组（legacy v1 链不可进正式准入）。",
        )
    for key, expected, code in (
        (_TASK_ID_KEY, payload.task_id, "admission_task_mismatch"),
        (_ENV_DIGEST_KEY, payload.environment_package_digest, "admission_environment_mismatch"),
        (_PUBLIC_DIGEST_KEY, payload.public_bundle_digest, "admission_public_bundle_mismatch"),
    ):
        if key not in sample_metadata:
            if require_dispatch_identity:
                raise AdmissionError(
                    "admission_dispatch_identity_missing",
                    f"样本缺分派键 {key}——组准入要求 task_id / environment_package_digest / public_bundle_digest 三键在场。",
                )
            continue
        if sample_metadata[key] != expected:
            raise AdmissionError(
                code, f"样本 {key}={sample_metadata[key]!r} 与载荷 {expected!r} 不一致（环境/分派身份错位）。"
            )
    report = payload.eligibility_report
    ref = sample_metadata.get(DERIVED_VIEW_REPORT_REF_KEY)
    cls = sample_metadata.get(DERIVED_VIEW_CLASS_KEY)
    if report is None:
        if ref is not None or cls is not None:
            raise AdmissionError(
                "derived_view_without_report",
                f"样本携带派生视图（{DERIVED_VIEW_REPORT_REF_KEY}={ref!r}, {DERIVED_VIEW_CLASS_KEY}={cls!r}）"
                "却无 EligibilityReport（引用悬空）。",
            )
    else:
        if ref != report.report_id or cls != report.eligibility_class:
            raise AdmissionError(
                "derived_view_mismatch",
                f"样本派生视图 ({ref!r}, {cls!r}) 与 EligibilityReport ({report.report_id!r}, "
                f"{report.eligibility_class!r}) 不一致（派生视图与 sidecar 互检失败）。",
            )
    return payload


# ---------------------------------------------------------------------------
# 三终态薄处置边界（纯函数）
# ---------------------------------------------------------------------------

_FATAL = "FATAL"
_DROP = "DROP_GROUP"
_PENDING = "PENDING_AGENT_VIOLATION"  # 附录 A 标 pending 的行：要求显式注入 DispositionPolicy.agent_violation
_DROP_IF_GRADING_INFRA = "DROP_IF_GRADING_INFRA"  # 与 outcome 的 grading_infra_failure 归因一致才 DROP，否则账实矛盾 FATAL

# 附录 A reason-code 映射细目（维度 → reason_code → 处置）。code 名与 governance/gate.py 实际发出的一致。
_DIMENSION_REASON_VERDICTS: dict[str, dict[str, str]] = {
    "token_provenance": {
        # 已声称 present 却 capture 丢失/不完整 = 账实矛盾（附录 A 行 1b）
        "capture_record_missing": _FATAL,
        "capture_record_not_complete": _FATAL,
    },
    "logprob_alignment": {
        # formal 路径的 logprob 缺失/错位 = 协议/装配 bug（行 2）
        "logprob_missing": _FATAL,
        "logprob_partial_or_mismatch": _FATAL,
    },
    "loss_mask_integrity": {
        "no_trainable_tokens": _DROP,  # 合法完整但不合格（行 3a）
        "loss_denominator_mismatch": _FATAL,  # 装配 bug（行 3c）
    },
    "reward_scope": {
        "reward_scope_none": _DROP_IF_GRADING_INFRA,  # 行 4a：与 grading infra failure 一致才是"无可信 reward"
        "reward_value_mismatch": _FATAL,  # 行 4b
        "reward_event_ref_missing": _FATAL,  # 行 4b
        "credit_assignment_unknown": _FATAL,  # 行 4c
    },
    "security_and_leakage": {
        # 前置清理批（D2-2 / D2-4）：行 5b `sandbox_capability_facts_missing`、行 5e
        # `public_projection_marker_hit` 已随 gate 删除，不再登记（旧 code 落"未登记 → FATAL"）。
        "patch_test_tampering": _PENDING,  # 行 5/6：pending（D2/A4；可信评分投影归 D2-3/W3a）
        "patch_forbidden_contamination": _PENDING,
    },
    "clean_grading": {
        "grading_infra_failure": _DROP_IF_GRADING_INFRA,  # 行 6a：failed_to_grade 保持 present，DROP，进 infra 计数
        "grading_test_log_parse_failed": _DROP_IF_GRADING_INFRA,
        "not_replayed_on_clean_checkout": _FATAL,  # 行 6c
        "hygiene_rejected_test_tampering": _PENDING,  # 与 security 的 patch_test_tampering 同一事实
        "hygiene_rejected_forbidden_contamination": _PENDING,
    },
    "policy_staleness": {
        # B-1：版本事实缺失/非法/未来版本 = 版本账目错误（FATAL）；`staleness_exceeded`
        # （finalize-time 合法过期 → DROP）已删除——过期组由 miles consume-time 按 B-2 drop。
        "staleness_facts_missing": _FATAL,  # 行 7a：formal 路径版本事实缺失 = 系统损坏
        "staleness_facts_invalid": _FATAL,  # 行 7b（改判后）：非法/未来版本 = 版本账目矛盾
    },
}
# 前缀规则（reason_code 带动态后缀的一类；sandbox_capability_* 两条前缀已随 D2-2 删除）。
_REASON_PREFIX_VERDICTS: tuple[tuple[str, str, str], ...] = (
    ("security_and_leakage", "anti_cheat_executed_", _PENDING),  # 行 5/6：executed 级 agent 违规 → pending
)
_DIMENSIONS: tuple[str, ...] = (
    "token_provenance",
    "logprob_alignment",
    "loss_mask_integrity",
    "reward_scope",
    "security_and_leakage",
    "clean_grading",
    "policy_staleness",
)


@dataclass(frozen=True)
class MemberDisposition:
    """一个成员的 final admission 结论（纯函数产物）。"""

    verdict: MemberVerdict
    reason_code: str
    layer: Literal["outcome", "eligibility", "disposition"]
    detail: str = ""


def _verdict_for(dimension: str, code: str) -> str | None:
    table = _DIMENSION_REASON_VERDICTS.get(dimension, {})
    if code in table:
        return table[code]
    for dim, prefix, verdict in _REASON_PREFIX_VERDICTS:
        if dim == dimension and code.startswith(prefix):
            return verdict
    return None


def _grading_infra_consistent(outcome: RolloutAttemptOutcomeV2) -> bool:
    return outcome.failure_category == "grading_infra_failure" and outcome.reward_unavailable


def decide_member_disposition(
    payload: AdmissionPayloadV1,
    *,
    policy: DispositionPolicy,
) -> MemberDisposition:
    """薄处置边界：base eligibility facts ∧ termination disposition →
    KEEP_FULL | DROP_GROUP | FATAL（附录 A 两层判定；模块 docstring 有逐条说明）。

    抛出（不是返回）的一类：`DispositionNotInjectedError`（槽位在决定结论时仍未注入）——
    配置缺口，不是样本处置。finalize-time staleness 阈值参数已删（B-1）。
    """

    if not isinstance(policy, DispositionPolicy):
        raise AdmissionError("disposition_policy_invalid", f"policy 必须是 DispositionPolicy，得到 {type(policy).__name__}。")
    outcome = payload.outcome

    # ---- 第一层：Outcome / 对象生命周期 ----
    if outcome.completion_class == "missing":
        # 载荷 validator 已不可表示；此处兜底保证附录 A 第一层完整。
        return MemberDisposition(_FATAL, "missing_outcome_delivered_as_present", "outcome", "missing 成员出现在交付面")

    # ---- 第二层：Eligibility / Admission ----
    report = payload.eligibility_report
    if report is None:
        if _grading_infra_consistent(outcome):
            return MemberDisposition(_DROP, "grading_infra_failure_without_report", "eligibility", "契约封闭豁免集：评分基建故障")
        if is_unsafe_artifact_rejection_shape(
            completion_class=outcome.completion_class,
            failure_category=outcome.failure_category,
            reason_code=outcome.reason_code,
            failed_component=outcome.failed_component,
            task_outcome=outcome.task_outcome,
            reward_unavailable=outcome.reward_unavailable,
            eligibility_report_id=outcome.eligibility_report_id,
        ):
            return MemberDisposition(_DROP, "unsafe_artifact_permanent_rejection", "eligibility", "契约封闭豁免集：unsafe artifact 永久拒绝")
        return MemberDisposition(_FATAL, "present_without_eligibility_report", "eligibility", "present_* 缺 EligibilityReport 且不在封闭豁免集")

    fatal: list[str] = []
    drop: list[str] = []
    pending: list[str] = []
    for dimension in _DIMENSIONS:
        fact = getattr(report.facts, dimension)
        if fact.ok:
            continue
        for code in fact.reason_codes:
            verdict = _verdict_for(dimension, code)
            if verdict is None:
                fatal.append(f"unmapped_reason_code:{dimension}:{code}")
            elif verdict == _FATAL:
                fatal.append(code)
            elif verdict == _DROP:
                drop.append(code)
            elif verdict == _DROP_IF_GRADING_INFRA:
                if _grading_infra_consistent(outcome):
                    drop.append(code)
                else:
                    fatal.append(f"{code}_without_grading_infra_attribution")
            elif verdict == _PENDING:
                pending.append(code)
            else:  # pragma: no cover - 表内取值封闭
                fatal.append(f"unmapped_reason_code:{dimension}:{code}")
    if fatal:
        return MemberDisposition(_FATAL, fatal[0], "eligibility", f"账实矛盾：{fatal}")
    if drop:
        return MemberDisposition(_DROP, drop[0], "eligibility", f"合法不合格：{drop}")
    if pending:
        choice = policy.agent_violation
        if choice is None:
            raise DispositionNotInjectedError(
                "agent_violation",
                f"成员命中 hygiene/agent 违规 {pending}，其处置归 D2/A4，尚未注入 DispositionPolicy.agent_violation。",
            )
        if choice == "DROP_GROUP":
            return MemberDisposition(_DROP, "agent_violation_excluded", "disposition", f"注入处置排除：{pending}")
        # KEEP_FULL 注入：按"作弊无收益的负样本"保留（reward 可得由上方 reward_scope 维保证）。
        # 注意 schema 层此时 eligibility_class 仍为 audit_only_or_rejected（security 失败强制），
        # D2 采纳 KEEP 时须同批修订 producer/schema 耦合（06 附录 A 豁免行注）。
    elif report.eligibility_class != "online_policy_loss_eligible":
        return MemberDisposition(
            _FATAL,
            "class_contradicts_facts",
            "eligibility",
            f"七维全过却结论 {report.eligibility_class}（gate 版本/报告被改写）",
        )

    # ---- 七维全过（或 pending 已注入 KEEP）：再应用显式 termination disposition（A5 归 C）----
    if outcome.completion_class == "present_truncated":
        slot = truncation_slot(outcome.termination_kind)
        choice = getattr(policy, f"{slot}_truncation")
        if choice is None:
            raise DispositionNotInjectedError(
                f"{slot}_truncation",
                f"present_truncated（termination_kind={outcome.termination_kind}）的处置归 A5/C 包，"
                f"尚未注入 DispositionPolicy.{slot}_truncation。",
            )
        if choice == "DROP_GROUP":
            return MemberDisposition(_DROP, f"truncation_{slot}_excluded", "disposition", f"注入处置排除截断（{outcome.termination_kind}）")
        return MemberDisposition("KEEP_FULL", f"truncation_{slot}_kept", "disposition", f"注入处置保留截断（{outcome.termination_kind}）")
    return MemberDisposition("KEEP_FULL", "all_dimensions_ok", "eligibility", "七维全过、present_complete")
