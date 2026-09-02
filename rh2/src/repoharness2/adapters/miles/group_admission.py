"""W1b 第二段：miles 复合 group admission filter（`--dynamic-sampling-filter-path` 的唯一入口）。

职责（06 计划 A2 / §3 W1b 行 / 附录 A；D1 已批）：

1. **组准入 = 全员 KEEP_FULL 才 keep=True**。对组内每个成员从交付样本 metadata 取回 typed
   admission 载荷（`rh2_admission`，运输值）与 termination 事实（`rh2_termination_facts`），
   消费时刻**全量核对**（载荷重跑契约校验，再与六字段身份 / 分派三元组 / termination 事实 /
   派生视图逐字对账），然后调 `governance.admission.decide_member_disposition` 得到每个成员的
   `KEEP_FULL | DROP_GROUP | FATAL`：任一 DROP → `keep=False`（miles `DefaultDataBuffer.put()` 对
   dynamic filter 的 keep=False 是**固定丢弃、不进 unused handler、不 retry**——持续 producer 用
   后续 prompt 补足 buffer，这就是 A2 的"整组拒绝 + 补采"）；任一 FATAL → **raise**
   `GroupAdmissionFatal`（结构矛盾/接线 bug 不得被补采掩盖，让 miles 的 put() 当场失败）。
2. **零方差过滤**（stock `check_reward_nonzero_std` 的职责并入本 filter）：全员 KEEP_FULL 且
   reward 全组相同 → `keep=False`（reason `zero_std_<r>`，与 stock 同形制便于指标对照）。
3. **prompt_group ↔ group 对账**：miles stock `DefaultDataBuffer.put()` 只把 `DataBufferInput.group`
   交给 filter（`fully_async_data_buffer.py:133`，`prompt_group` 不在 filter 签名内），因此对账
   用的是 miles 从派发 prompt 样本**逐字复制**到每个生成样本上的组事实（`Sample.group_index` /
   `Sample.index`；canonicalize 已在 generate 边界钉死输出 index/group_index == 输入）与派发时刻
   从同一组事实铸造的六字段身份（W1a：`rh2_prompt_group_id = miles_g{group_index}`、
   `rh2_member_slot = index - group_index*n`、`rh2_rollout_execution_id = {gid}_m{slot}`）以及
   bind 时经 prep manifest 核对过的分派三元组：组成员必须恰好是同一 group_index 的 n 个不同
   slot、同一任务/环境 digest、attempt 两两不同、fan-out 叶与本成员身份逐字相同——任何不一致
   = FATAL。不延长 `AttemptAssignmentRegistry` 生命周期（GenerateFn 返回前已 release），不建
   ledger、不扫盘。

三终态在本层的对应：
    FATAL   → raise GroupAdmissionFatal / DispositionNotInjectedError（put() 失败，run 停）
    ABORTED → 本 filter **永远看不到**（miles put() 先把含 ABORTED 的组交 unused handler，语义归 B 包）；
              若竟然看到 ABORTED 成员，按接线矛盾 FATAL
    DROP    → keep=False（固定丢弃）

staleness 两阶段：finalize-time 判定消费 EligibilityReport 的 policy_staleness 维（载荷内），
阈值权威 = `args.rh2_orchestrator.config.staleness_threshold`（与 generate.py 交付面同一配置
对象，禁止第二份配置；缺失即 FATAL，不继承隐式默认）；consume-time 由 miles `buffer.get()`
按 `--max-weight-staleness` 复查（归 W4，本模块不做）。

待拍板处置的注入位：`args.rh2_disposition_policy`（`governance.admission.DispositionPolicy`
实例；缺席 = 四槽位全 None）。present_truncated / hygiene 违规成员在其它维度都通过、真正需要
该槽位决定结论时若仍为 None → `DispositionNotInjectedError` 直接抛出（未注入即 fail-fast，
不存在隐藏默认答案）。

import 面：本模块**模块级零 miles import**（`DynamicFilterOutput` 在 filter 函数内延迟 import），
因此 `Rh2MilesGenerateFn` 可以在模块级引用 `GROUP_ADMISSION_FILTER_PATH` 做接线守卫。
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from repoharness2.adapters.miles.identity import (
    ATTEMPT_ID_KEY,
    ATTEMPT_SEQ_KEY,
    EXECUTION_ID_KEY,
    GROUP_ID_KEY,
    GROUP_INDEX_KEY,
    MEMBER_SLOT_KEY,
)
from repoharness2.envpack.termination_facts import (
    TerminationFactsError,
    TerminationFactsPayloadV1,
    resolve_termination_facts,
)
from repoharness2.governance.admission import (
    AdmissionError,
    AdmissionPayloadV1,
    DispositionPolicy,
    MemberDisposition,
    decide_member_disposition,
    resolve_admission_payload,
)

__all__ = [
    "DISPOSITION_POLICY_ARGS_KEY",
    "GROUP_ADMISSION_FILTER_PATH",
    "AdmissionWiringError",
    "GroupAdmissionFatal",
    "GroupAdmissionResult",
    "MemberAdmission",
    "admit_group",
    "rh2_group_admission_filter",
]

# miles `--dynamic-sampling-filter-path` 必须指向的路径（generate_fn 在非 s1_compat 模式守卫）。
GROUP_ADMISSION_FILTER_PATH = "repoharness2.adapters.miles.group_admission.rh2_group_admission_filter"
# miles args 上的处置注入位（DispositionPolicy 实例）。
DISPOSITION_POLICY_ARGS_KEY = "rh2_disposition_policy"
# 分派三元组键（与 envpack/prepared_tasks.DISPATCH_METADATA_KEYS 逐字一致；本模块不 import envpack.prepared_tasks，
# 避免把 prepared 链的读取面拉进 filter 的 import 闭包）。
_DISPATCH_KEYS: tuple[str, ...] = ("task_id", "environment_package_digest", "public_bundle_digest")
_ZERO_STD_EPS = 1e-8  # 与 miles stock check_reward_nonzero_std 同阈值


class GroupAdmissionFatal(RuntimeError):
    """组准入的结构矛盾（三终态 ①）：必须 raise，不许 keep=False 让补采掩盖。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


class AdmissionWiringError(RuntimeError):
    """非 s1_compat 的 miles 派发链没有挂上本 filter（generate_fn 守卫）。"""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"[{reason_code}] {message}")


@dataclass(frozen=True)
class MemberAdmission:
    """一个成员（prompt group 的一个 slot）的对账结果与处置。"""

    member_slot: int
    rollout_execution_id: str
    physical_attempt_id: str
    leaf_count: int
    reward: float | None
    disposition: MemberDisposition


@dataclass(frozen=True)
class GroupAdmissionResult:
    keep: bool
    reason: str | None
    members: tuple[MemberAdmission, ...]


def _meta(leaf: Any) -> Mapping[str, Any]:
    meta = getattr(leaf, "metadata", None)
    if not isinstance(meta, Mapping):
        raise GroupAdmissionFatal(
            "member_metadata_missing", f"交付样本 metadata 不是 Mapping（{type(meta).__name__}）——无身份/载荷可对账。"
        )
    return meta


def _status_value(leaf: Any) -> str:
    raw = getattr(leaf, "status", None)
    value = getattr(raw, "value", raw)
    if not isinstance(value, str) or not value:
        raise GroupAdmissionFatal("member_status_unreadable", f"交付样本 status={raw!r} 不可读。")
    return value.lower()


def _int_fact(value: Any, *, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GroupAdmissionFatal("identity_field_malformed", f"{key}={value!r} 不是非负 int。")
    return value


def _str_fact(value: Any, *, key: str) -> str:
    if not isinstance(value, str) or not value:
        raise GroupAdmissionFatal("identity_field_malformed", f"{key}={value!r} 不是非空字符串。")
    return value


@dataclass(frozen=True)
class _Identity:
    group_id: str
    group_index: int
    execution_id: str
    slot: int
    attempt_id: str
    attempt_seq: int


def _read_identity(meta: Mapping[str, Any], *, n_samples_per_prompt: int) -> _Identity:
    missing = [k for k in (GROUP_ID_KEY, GROUP_INDEX_KEY, EXECUTION_ID_KEY, MEMBER_SLOT_KEY, ATTEMPT_ID_KEY, ATTEMPT_SEQ_KEY) if k not in meta]
    if missing:
        raise GroupAdmissionFatal("identity_missing", f"交付样本缺六字段身份 {missing}——formal 成员必带，fail-closed。")
    ident = _Identity(
        group_id=_str_fact(meta[GROUP_ID_KEY], key=GROUP_ID_KEY),
        group_index=_int_fact(meta[GROUP_INDEX_KEY], key=GROUP_INDEX_KEY),
        execution_id=_str_fact(meta[EXECUTION_ID_KEY], key=EXECUTION_ID_KEY),
        slot=_int_fact(meta[MEMBER_SLOT_KEY], key=MEMBER_SLOT_KEY),
        attempt_id=_str_fact(meta[ATTEMPT_ID_KEY], key=ATTEMPT_ID_KEY),
        attempt_seq=_int_fact(meta[ATTEMPT_SEQ_KEY], key=ATTEMPT_SEQ_KEY),
    )
    # 与 W1a 铸造规则对账（identity.py 模块 docstring）：组身份/执行身份是组事实的纯函数。
    if ident.group_id != f"miles_g{ident.group_index}":
        raise GroupAdmissionFatal(
            "identity_group_mismatch", f"{GROUP_ID_KEY}={ident.group_id!r} 与 group_index={ident.group_index} 推导值不一致。"
        )
    if not (0 <= ident.slot < n_samples_per_prompt):
        raise GroupAdmissionFatal(
            "identity_slot_out_of_range", f"member_slot={ident.slot} 不在 0..{n_samples_per_prompt - 1} 内。"
        )
    if ident.execution_id != f"{ident.group_id}_m{ident.slot}":
        raise GroupAdmissionFatal(
            "identity_execution_mismatch",
            f"{EXECUTION_ID_KEY}={ident.execution_id!r} 与 ({ident.group_id}, slot={ident.slot}) 推导值不一致。",
        )
    if ident.attempt_seq < 1 or not ident.attempt_id.startswith(f"{ident.execution_id}#p{ident.attempt_seq}-"):
        raise GroupAdmissionFatal(
            "identity_attempt_mismatch",
            f"{ATTEMPT_ID_KEY}={ident.attempt_id!r} 不是 execution {ident.execution_id!r} 第 {ident.attempt_seq} 次 attempt 的形制。",
        )
    return ident


def _reward_scalar(value: Any) -> float | None:
    """交付样本 reward → 有限 float / None（None 或 NaN 都表示"不可得"）。"""

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GroupAdmissionFatal("reward_not_scalar", f"交付样本 reward={value!r} 不是标量（组准入只认标量 reward）。")
    if math.isnan(value):
        return None
    if not math.isfinite(value):
        raise GroupAdmissionFatal("reward_not_finite", f"交付样本 reward={value!r} 非有限。")
    return float(value)


def _check_leaf_shape_claims(leaf: Any, payload: AdmissionPayloadV1, *, reward: float | None) -> None:
    """声称 vs 交付形状（三终态 ① 的账实矛盾面）。"""

    if getattr(leaf, "remove_sample", False):
        # 交付面自 W1b 第二段起不再用 remove_sample 表达"不合格"：完整成员一律真实交付、由本
        # filter 整组裁决；remove_sample=True 的非 ABORTED 样本只可能是 eval 占位或接线矛盾。
        raise GroupAdmissionFatal(
            "remove_sample_on_delivered_member",
            f"成员 {payload.physical_attempt_id} 交付形状带 remove_sample=True——与"
            "'完整成员真实交付、组级裁决'的交付面语义矛盾。",
        )
    outcome = payload.outcome
    if outcome.reward_unavailable:
        if reward is not None:
            raise GroupAdmissionFatal(
                "reward_present_but_unavailable_claimed",
                f"成员 {payload.physical_attempt_id} 载荷声称 reward 不可得，样本却带 reward={reward!r}。",
            )
    else:
        if reward is None or payload.grading_reward is None or reward != float(payload.grading_reward):
            raise GroupAdmissionFatal(
                "reward_mismatch_on_delivery",
                f"成员 {payload.physical_attempt_id} 样本 reward={reward!r} 与 GradingReport reward="
                f"{payload.grading_reward!r} 不一致。",
            )
    report = payload.eligibility_report
    if report is not None and report.eligibility_class == "online_policy_loss_eligible":
        loss_mask = getattr(leaf, "loss_mask", None)
        logprobs = getattr(leaf, "rollout_log_probs", None)
        response_length = getattr(leaf, "response_length", None)
        tokens = getattr(leaf, "tokens", None)
        trainable = sum(1 for m in (loss_mask or []) if m == 1)
        if (
            not loss_mask
            or trainable == 0
            or logprobs is None
            or len(logprobs) != len(loss_mask)
            or response_length != len(loss_mask)
            or not tokens
            or len(tokens) < response_length
            or not getattr(leaf, "weight_versions", None)
        ):
            raise GroupAdmissionFatal(
                "online_claim_without_trainable_provenance",
                f"成员 {payload.physical_attempt_id} 声称 online，交付形状却无可训 provenance"
                f"（trainable={trainable}, logprobs={None if logprobs is None else len(logprobs)}, "
                f"response_length={response_length}, weight_versions={getattr(leaf, 'weight_versions', None)!r}）。",
            )


def _check_outcome_identity(ident: _Identity, payload: AdmissionPayloadV1) -> None:
    """复核修复 #6b：Outcome 内部身份（identity 五字段 + member_slot）与外层六字段逐项对账。"""

    oid = payload.outcome.identity
    pairs = (
        ("prompt_group_id", oid.prompt_group_id, ident.group_id),
        ("group_index", oid.group_index, ident.group_index),
        ("rollout_execution_id", oid.rollout_execution_id, ident.execution_id),
        ("physical_attempt_id", oid.physical_attempt_id, ident.attempt_id),
        ("physical_attempt_seq", oid.physical_attempt_seq, ident.attempt_seq),
        ("member_slot", payload.outcome.member_slot, ident.slot),
    )
    mismatched = [(name, a, b) for name, a, b in pairs if a != b]
    if mismatched:
        raise GroupAdmissionFatal(
            "outcome_identity_mismatch",
            f"成员 {ident.execution_id} 的 Outcome 内部身份与六字段身份不一致：{mismatched}。",
        )


def _parse_version(value: Any, *, what: str, member: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("bool")
        return int(str(value), 10)
    except (TypeError, ValueError):
        raise GroupAdmissionFatal(
            "version_not_numeric",
            f"成员 {member} 的 {what}={value!r} 不能解析为十进制整数版本（formal 版本契约）。",
        ) from None


def _check_leaf_version_binding(leaf: Any, payload: AdmissionPayloadV1) -> None:
    """复核修复 #4：叶版本事实必须与 Outcome 的版本事实合法相关（消费侧版本绑定）。

    规则（现有版本投影语义）：叶 `weight_versions` 非空 ⟺ Outcome 有版本事实；每个叶版本可解析为
    int 且 ∈ Outcome.turn_weight_versions（**子集**——fan-out 叶只回链自己的入训轮，不得要求集合
    相等）；max(叶版本) ≤ Outcome.current_version_at_finalize。反例：叶被改成未来版本 999 而 Outcome
    仍为 5——miles get() 的 staleness = current − oldest 会算成负数并"满足"任何阈值。consume-time
    的负 lag 拒绝在 miles get() 侧（归 W4，不改 reference/），本函数在 finalize 事实层先钉死。
    """

    member = payload.physical_attempt_id
    outcome = payload.outcome
    leaf_versions = list(getattr(leaf, "weight_versions", None) or [])
    outcome_versions = list(outcome.turn_weight_versions or [])
    if bool(leaf_versions) != bool(outcome_versions):
        raise GroupAdmissionFatal(
            "version_facts_presence_mismatch",
            f"成员 {member} 叶 weight_versions={leaf_versions!r} 与 Outcome.turn_weight_versions={outcome_versions!r} "
            "在场性不一致（版本事实两处账目分家）。",
        )
    if not leaf_versions:
        return
    leaf_ints = {_parse_version(v, what="leaf weight_version", member=member) for v in leaf_versions}
    outcome_ints = {_parse_version(v, what="Outcome.turn_weight_version", member=member) for v in outcome_versions}
    current = _parse_version(outcome.current_version_at_finalize, what="Outcome.current_version_at_finalize", member=member)
    if not leaf_ints <= outcome_ints:
        raise GroupAdmissionFatal(
            "leaf_version_not_in_outcome",
            f"成员 {member} 叶版本 {sorted(leaf_ints)} 不是 Outcome 逐轮版本 {sorted(outcome_ints)} 的子集。",
        )
    if max(leaf_ints) > current:
        raise GroupAdmissionFatal(
            "leaf_version_ahead_of_finalize",
            f"成员 {member} 叶版本 max={max(leaf_ints)} 超过 finalize 时刻 current_version={current}"
            "（未来版本会让 consume-time staleness 变负并绕过阈值）。",
        )


def _check_facts_vs_payload(facts: TerminationFactsPayloadV1, payload: AdmissionPayloadV1) -> None:
    pairs = (
        ("physical_attempt_id", facts.physical_attempt_id, payload.physical_attempt_id),
        ("rollout_execution_id", facts.rollout_execution_id, payload.rollout_execution_id),
        ("task_id", facts.task_id, payload.task_id),
        ("outcome_id", facts.outcome_id, payload.outcome.outcome_id),
        ("termination_kind", facts.termination_kind, payload.outcome.termination_kind),
        ("eligibility_report_id", facts.eligibility_report_id, payload.outcome.eligibility_report_id),
        ("grading_report_id", facts.grading_report_id, payload.grading_report_id),
        ("fresh_grading_complete", facts.fresh_grading_complete, payload.grading_report_id is not None),
    )
    mismatched = [(name, a, b) for name, a, b in pairs if a != b]
    if mismatched:
        raise GroupAdmissionFatal(
            "admission_termination_facts_mismatch",
            f"成员 {payload.physical_attempt_id} 的 termination 事实与 admission 载荷不一致：{mismatched}。",
        )


def admit_group(
    group: Any,
    *,
    n_samples_per_prompt: int,
    disposition_policy: DispositionPolicy,
    finalize_staleness_threshold: int | None,
    reward_of: Callable[[Any], Any],
) -> GroupAdmissionResult:
    """组准入本体（与 miles 类型解耦，便于单测）。抛出即 FATAL；返回 keep=False 即 DROP。"""

    if isinstance(n_samples_per_prompt, bool) or not isinstance(n_samples_per_prompt, int) or n_samples_per_prompt < 1:
        raise GroupAdmissionFatal("group_size_config_missing", f"n_samples_per_prompt={n_samples_per_prompt!r} 非法。")
    if not isinstance(group, list) or not group:
        raise GroupAdmissionFatal("group_shape_mismatch", f"组不是非空 list（{type(group).__name__}）。")
    if len(group) != n_samples_per_prompt:
        raise GroupAdmissionFatal(
            "group_shape_mismatch",
            f"组有 {len(group)} 个成员，n_samples_per_prompt={n_samples_per_prompt}——prompt_group 与生成结果对不上。",
        )

    members: list[MemberAdmission] = []
    group_index: int | None = None
    group_task: tuple[Any, ...] | None = None
    seen_slots: set[int] = set()
    seen_attempts: set[str] = set()
    seen_executions: set[str] = set()
    for element in group:
        leaves = element if isinstance(element, list) else [element]
        if not leaves:
            raise GroupAdmissionFatal("group_shape_mismatch", "组成员是空 list（无事实的交付形状）。")
        meta0 = _meta(leaves[0])
        ident = _read_identity(meta0, n_samples_per_prompt=n_samples_per_prompt)
        try:
            payload0 = resolve_admission_payload(meta0, require_dispatch_identity=True)
        except AdmissionError as exc:
            raise GroupAdmissionFatal(exc.reason_code, f"成员 {ident.execution_id}：{exc}") from exc
        try:
            facts0 = resolve_termination_facts(meta0)
        except TerminationFactsError as exc:
            raise GroupAdmissionFatal("termination_facts_unresolvable", f"成员 {ident.execution_id}：{exc}") from exc
        _check_facts_vs_payload(facts0, payload0)
        _check_outcome_identity(ident, payload0)
        dispatch0 = tuple(meta0.get(k) for k in _DISPATCH_KEYS)
        member_reward: float | None = None
        for position, leaf in enumerate(leaves):
            meta = _meta(leaf)
            status = _status_value(leaf)
            if status == "aborted":
                raise GroupAdmissionFatal(
                    "aborted_member_reached_filter",
                    f"成员 {ident.execution_id} 带 ABORTED 叶到达 filter——miles put() 应先交 unused handler，接线矛盾。",
                )
            if status not in ("completed", "truncated"):
                raise GroupAdmissionFatal("member_status_not_delivered", f"成员 {ident.execution_id} 叶 status={status!r}。")
            # fan-out：同一成员的全部叶身份/载荷/事实/分派逐字相同（叶不是新 member/新 attempt）
            if position > 0:
                leaf_ident = _read_identity(meta, n_samples_per_prompt=n_samples_per_prompt)
                if leaf_ident != ident:
                    raise GroupAdmissionFatal(
                        "fan_out_leaf_identity_forgery",
                        f"成员 {ident.execution_id} 的 fan-out 叶携带不同身份 {leaf_ident}——叶冒充新 member/attempt。",
                    )
                try:
                    leaf_payload = resolve_admission_payload(meta, require_dispatch_identity=True)
                    leaf_facts = resolve_termination_facts(meta)
                except (AdmissionError, TerminationFactsError) as exc:
                    raise GroupAdmissionFatal("fan_out_leaf_payload_unresolvable", f"成员 {ident.execution_id}：{exc}") from exc
                if leaf_payload != payload0 or leaf_facts != facts0 or tuple(meta.get(k) for k in _DISPATCH_KEYS) != dispatch0:
                    raise GroupAdmissionFatal(
                        "fan_out_leaf_payload_forgery",
                        f"成员 {ident.execution_id} 的 fan-out 叶携带不同的载荷/事实/分派三元组。",
                    )
            # prompt_group ↔ group 对账：miles 逐字复制的组事实必须与身份推导一致
            if getattr(leaf, "group_index", None) != ident.group_index:
                raise GroupAdmissionFatal(
                    "prompt_group_index_mismatch",
                    f"成员 {ident.execution_id} 叶 group_index={getattr(leaf, 'group_index', None)!r} != 身份 {ident.group_index}。",
                )
            expected_index = ident.group_index * n_samples_per_prompt + ident.slot
            if getattr(leaf, "index", None) != expected_index:
                raise GroupAdmissionFatal(
                    "prompt_group_index_mismatch",
                    f"成员 {ident.execution_id} 叶 index={getattr(leaf, 'index', None)!r} != group_index*n+slot={expected_index}"
                    "（不是本 prompt group 派发出的样本）。",
                )
            reward = _reward_scalar(reward_of(leaf))
            _check_leaf_version_binding(leaf, payload0)  # 版本事实绑定先于形状声称（更具体的矛盾先报）
            _check_leaf_shape_claims(leaf, payload0, reward=reward)
            if position == 0:
                member_reward = reward
            elif reward != member_reward:
                raise GroupAdmissionFatal(
                    "fan_out_leaf_reward_mismatch", f"成员 {ident.execution_id} 的 fan-out 叶 reward 不一致（{member_reward!r} vs {reward!r}）。"
                )
        # 组级对账：同一组、同一任务/环境、slot/attempt/execution 两两不同
        if group_index is None:
            group_index = ident.group_index
            group_task = (payload0.task_id, payload0.environment_package_digest, payload0.public_bundle_digest)
        else:
            if ident.group_index != group_index:
                raise GroupAdmissionFatal(
                    "mixed_group_members", f"成员 {ident.execution_id} group_index={ident.group_index} != 组 {group_index}（跨组混入）。"
                )
            task_triple = (payload0.task_id, payload0.environment_package_digest, payload0.public_bundle_digest)
            if task_triple != group_task:
                raise GroupAdmissionFatal(
                    "mixed_group_members", f"成员 {ident.execution_id} 任务/环境 {task_triple} != 组 {group_task}（同组不同任务）。"
                )
        if ident.slot in seen_slots:
            raise GroupAdmissionFatal("member_slot_duplicated", f"slot {ident.slot} 在组内重复（成员冒充/重复交付）。")
        if ident.attempt_id in seen_attempts:
            raise GroupAdmissionFatal("attempt_id_reused", f"attempt {ident.attempt_id!r} 在组内重复（身份复用）。")
        if ident.execution_id in seen_executions:
            raise GroupAdmissionFatal("execution_id_reused", f"execution {ident.execution_id!r} 在组内重复。")
        seen_slots.add(ident.slot)
        seen_attempts.add(ident.attempt_id)
        seen_executions.add(ident.execution_id)

        disposition = decide_member_disposition(
            payload0, policy=disposition_policy, finalize_staleness_threshold=finalize_staleness_threshold
        )
        if disposition.verdict == "FATAL":
            raise GroupAdmissionFatal(
                disposition.reason_code,
                f"成员 {ident.execution_id}（attempt {ident.attempt_id}）终态 FATAL：{disposition.detail}",
            )
        members.append(
            MemberAdmission(
                member_slot=ident.slot,
                rollout_execution_id=ident.execution_id,
                physical_attempt_id=ident.attempt_id,
                leaf_count=len(leaves),
                reward=member_reward,
                disposition=disposition,
            )
        )
    if seen_slots != set(range(n_samples_per_prompt)):
        raise GroupAdmissionFatal(
            "slot_set_mismatch", f"组内 slot 集合 {sorted(seen_slots)} != 0..{n_samples_per_prompt - 1}（成员缺席/重复）。"
        )

    dropped = [m for m in members if m.disposition.verdict == "DROP_GROUP"]
    if dropped:
        first = dropped[0]
        return GroupAdmissionResult(
            keep=False, reason=f"admission_{first.disposition.reason_code}", members=tuple(members)
        )
    # 全员 KEEP_FULL：reward 必须全部可得（KEEP_FULL 的 reward_scope 维已保证；此处再钉一次）
    rewards = [m.reward for m in members]
    if any(r is None for r in rewards):
        raise GroupAdmissionFatal("keep_full_without_reward", "全员 KEEP_FULL 却有成员 reward 不可得（账实矛盾）。")
    std = statistics.pstdev(rewards) if len(rewards) > 1 else 0.0  # type: ignore[arg-type]
    if std <= _ZERO_STD_EPS:
        return GroupAdmissionResult(keep=False, reason=f"zero_std_{round(rewards[0], 1)}", members=tuple(members))
    return GroupAdmissionResult(keep=True, reason=None, members=tuple(members))


def _threshold_from_args(args: Any) -> int | None:
    """finalize-time staleness 阈值的唯一权威 = 交付面用的同一 SlimeBindingConfig。"""

    orchestrator = getattr(args, "rh2_orchestrator", None)
    config = getattr(orchestrator, "config", None)
    if config is None:
        raise GroupAdmissionFatal(
            "staleness_threshold_authority_unreachable",
            "args.rh2_orchestrator.config 不可达——filter 无法引用与交付面同一份 staleness 阈值配置。",
        )
    return getattr(config, "staleness_threshold", None)


def _policy_from_args(args: Any) -> DispositionPolicy:
    policy = getattr(args, DISPOSITION_POLICY_ARGS_KEY, None)
    if policy is None:
        return DispositionPolicy()  # 未注入：四槽位全 None，遇到需要它的成员即 fail-fast
    if not isinstance(policy, DispositionPolicy):
        raise GroupAdmissionFatal(
            "disposition_policy_invalid", f"args.{DISPOSITION_POLICY_ARGS_KEY} 必须是 DispositionPolicy，得到 {type(policy).__name__}。"
        )
    return policy


def rh2_group_admission_filter(args: Any, samples: Any, **kwargs: Any):
    """miles dynamic filter 入口（签名 = `fn(args, samples, **kwargs)`）。"""

    from miles.rollout.filter_hub.base_types import DynamicFilterOutput  # 延迟 import（见模块 docstring）

    n = getattr(args, "n_samples_per_prompt", None)

    def _reward_of(leaf: Any) -> Any:
        getter = getattr(leaf, "get_reward_value", None)
        return getter(args) if callable(getter) else getattr(leaf, "reward", None)

    try:
        result = admit_group(
            samples,
            n_samples_per_prompt=n,
            disposition_policy=_policy_from_args(args),
            finalize_staleness_threshold=_threshold_from_args(args),
            reward_of=_reward_of,
        )
    except (GroupAdmissionFatal, AdmissionError) as exc:
        # W5a 复核 #3 接缝：filter 在 miles put() 内运行，与执行 task 不同 context，
        # generate.py 的 contextvar 通知器够不到——显式经进程级入口触发同一条
        # 关停链（未在关停 → 调度；关停中 → 吸收进报告）。通知失败不得吞掉首因。
        try:
            from repoharness2.adapters.slime.bringup import notify_run_fatal  # 延迟 import,避免环

            notify_run_fatal(exc)
        except Exception:  # noqa: BLE001 - 通知只是附加动作,首因异常必须原样传播
            pass
        raise
    return DynamicFilterOutput(keep=result.keep, reason=result.reason)
