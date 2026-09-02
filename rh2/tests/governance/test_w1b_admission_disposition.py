"""W1b 第二段：薄处置边界纯函数 + admission 载荷（governance/admission.py）的契约测试。

覆盖（06 计划附录 A 逐行 + §3 W1b 行验收要点）：
- 两层判定的 reason_code → 终态映射逐行钉死（含"未登记 code 一律 FATAL"）；
- disposition 未注入即 fail-fast（A5 三个截断槽位 + A4 agent 违规槽位），同一
  present_truncated 载荷双注入 KEEP_FULL / DROP_GROUP 证明链路中立；
- 显式 staleness 阈值缺失即拒、权威阈值不一致 FATAL；
- 契约封闭豁免集（无 EligibilityReport）→ DROP_GROUP，豁免集之外的形状在 Outcome v2 契约层不可表示；
- 载荷派生/盖章/解引用的 fail-closed 面。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from contract_samples import valid_backend_handshake, valid_eligibility_facts, valid_grading_report
from pydantic import ValidationError

from repoharness2.contracts import BackendHandshake, EligibilityFacts, EligibilityReport, GradingReport
from repoharness2.contracts.fa_runtime import ExecutionIdentity, RolloutAttemptOutcomeV2
from repoharness2.governance import GATE_VERSION
from repoharness2.governance.admission import (
    ADMISSION_METADATA_KEY,
    AdmissionError,
    AdmissionPayloadV1,
    DispositionNotInjectedError,
    DispositionPolicy,
    decide_member_disposition,
    derive_admission_payload,
    resolve_admission_payload,
    stamp_admission_payload,
    truncation_slot,
)

TRAJ = "miles_g0_m1"
PAID = "miles_g0_m1#p1-cafe0001"
ENV = "sha256:" + "b" * 64
PUB = "sha256:" + "e" * 64
CREATED = datetime(2026, 9, 2, tzinfo=timezone.utc)
_AUDIT_DIMS = {"loss_mask_integrity", "reward_scope", "security_and_leakage", "clean_grading"}


# ---------------------------------------------------------------------------
# 夹具工厂
# ---------------------------------------------------------------------------


def _outcome(**over: Any) -> RolloutAttemptOutcomeV2:
    base: dict[str, Any] = dict(
        outcome_id="ov2_x",
        identity=ExecutionIdentity(
            prompt_group_id="miles_g0", group_index=0, rollout_execution_id=TRAJ,
            physical_attempt_id=PAID, physical_attempt_seq=1,
        ),
        member_slot=1, attempt_number=1,
        completion_class="present_complete", termination_kind="completed",
        failure_category=None, reason_code=None, failed_component=None,
        recovery_scope="none", task_outcome="resolved", reward_unavailable=False,
        turn_weight_versions=["5"], intra_execution_version_span=0, current_version_at_finalize="5",
        eligibility_report_id="elig_x", evidence_refs=["audit:x"],
    )
    base.update(over)
    return RolloutAttemptOutcomeV2(**base)


def _infra_outcome(**over: Any) -> RolloutAttemptOutcomeV2:
    return _outcome(
        failure_category="grading_infra_failure", failed_component="grading_container",
        task_outcome="unknown", reward_unavailable=True, **over,
    )


def _unsafe_outcome() -> RolloutAttemptOutcomeV2:
    return _outcome(
        reason_code="unsafe_artifact_permanent_rejection", failed_component="patch_hygiene",
        task_outcome="unknown", reward_unavailable=True, eligibility_report_id=None,
    )


def _facts(failures: dict[str, list[str]] | None = None) -> EligibilityFacts:
    facts = valid_eligibility_facts()
    for dim, codes in (failures or {}).items():
        facts[dim] = {"ok": False, "reason_codes": codes, "evidence_refs": []}
    return EligibilityFacts.model_validate(facts)


def _report(
    failures: dict[str, list[str]] | None = None,
    *,
    eligibility_class: str | None = None,
    reason_codes: list[str] | None = None,
) -> EligibilityReport:
    failures = failures or {}
    if eligibility_class is None:
        if not failures:
            eligibility_class = "online_policy_loss_eligible"
        elif set(failures) & _AUDIT_DIMS:
            eligibility_class = "audit_only_or_rejected"
        else:
            eligibility_class = "offline_or_sft_candidate"
    codes = reason_codes if reason_codes is not None else [c for cs in failures.values() for c in cs]
    return EligibilityReport.finalize(
        report_id="elig_x", trajectory_id=TRAJ, gate_version=GATE_VERSION, facts=_facts(failures),
        eligibility_class=eligibility_class, reason_codes=codes, created_at_utc=CREATED,
    )


def _grading(*, outcome: str = "resolved") -> GradingReport:
    base = valid_grading_report()
    base.update(report_id="rpt_x", trajectory_id=TRAJ)
    if outcome == "unresolved":
        base.update(outcome="unresolved", failure_category="tests_failed", reward=0.0, f2p_pass_count=1)
    elif outcome == "failed_to_grade":
        base.update(
            outcome="failed_to_grade", failure_category="infra_failure", reward=None,
            f2p_pass_count=None, f2p_total_count=None, p2p_fail_count=None, p2p_total_count=None,
            patch_hygiene=None, infra_failure_detail="grading_container_killed_oom",
        )
    return GradingReport.model_validate(base)


def _handshake(steps: int = 1, threshold: int = 4) -> BackendHandshake:
    base = valid_backend_handshake()
    base.update(trajectory_id=TRAJ, staleness_steps=steps, staleness_threshold=threshold,
                staleness_within_threshold=steps <= threshold)
    return BackendHandshake.model_validate(base)


def _payload(
    *,
    outcome: RolloutAttemptOutcomeV2 | None = None,
    report: EligibilityReport | None = "default",  # type: ignore[assignment]
    grading: GradingReport | None = "default",  # type: ignore[assignment]
    handshake: BackendHandshake | None = "default",  # type: ignore[assignment]
    env: str | None = ENV,
) -> AdmissionPayloadV1:
    return derive_admission_payload(
        outcome=outcome or _outcome(),
        eligibility_report=_report() if report == "default" else report,
        grading_report=_grading() if grading == "default" else grading,
        handshake=_handshake() if handshake == "default" else handshake,
        task_id="swe_gym_lite::x", public_bundle_digest=PUB, environment_package_digest=env,
    )


def _decide(payload: AdmissionPayloadV1, policy: DispositionPolicy | None = None, threshold: int | None = 4):
    return decide_member_disposition(payload, policy=policy or DispositionPolicy(), finalize_staleness_threshold=threshold)


# ---------------------------------------------------------------------------
# 七维全过 / 截断双注入 / fail-fast
# ---------------------------------------------------------------------------


def test_all_ok_present_complete_is_keep_full_without_any_injection():
    d = _decide(_payload())
    assert d.verdict == "KEEP_FULL" and d.reason_code == "all_dimensions_ok"


@pytest.mark.parametrize(
    ("kind", "slot"),
    [
        ("task_token_budget_exhausted", "policy_horizon"),
        ("max_turns_exhausted", "policy_horizon"),
        ("context_limit_reached", "policy_horizon"),
        ("hard_wall_timeout", "hard_wall"),
        ("owner_cancelled", "owner_cancelled"),
    ],
)
def test_present_truncated_requires_explicit_injection_and_chain_is_neutral(kind: str, slot: str):
    """A5 归 C：同一 present_truncated 载荷——未注入即 fail-fast；分别注入 KEEP_FULL / DROP_GROUP
    得到相反结论（链路对取值中立）；注入**别的**槽位不算注入。"""

    payload = _payload(outcome=_outcome(completion_class="present_truncated", termination_kind=kind))
    assert truncation_slot(kind) == slot
    with pytest.raises(DispositionNotInjectedError) as info:
        _decide(payload)
    assert info.value.slot == f"{slot}_truncation" and info.value.reason_code == f"disposition_not_injected:{slot}_truncation"
    other = {name: "KEEP_FULL" for name in ("policy_horizon_truncation", "hard_wall_truncation", "owner_cancelled_truncation")}
    other.pop(f"{slot}_truncation")
    with pytest.raises(DispositionNotInjectedError):
        _decide(payload, DispositionPolicy(**other))
    keep = _decide(payload, DispositionPolicy(**{f"{slot}_truncation": "KEEP_FULL"}))
    drop = _decide(payload, DispositionPolicy(**{f"{slot}_truncation": "DROP_GROUP"}))
    assert (keep.verdict, keep.reason_code) == ("KEEP_FULL", f"truncation_{slot}_kept")
    assert (drop.verdict, drop.reason_code) == ("DROP_GROUP", f"truncation_{slot}_excluded")
    assert keep.layer == drop.layer == "disposition"


def test_truncation_disposition_not_consulted_when_dimensions_already_drop():
    """附录 A："七维全过再应用 disposition"——其它维度已 DROP 时不读截断槽位（未注入也不 raise）。"""

    payload = _payload(
        outcome=_outcome(completion_class="present_truncated", termination_kind="hard_wall_timeout"),
        report=_report({"loss_mask_integrity": ["no_trainable_tokens"]}),
    )
    d = _decide(payload)  # policy 全 None
    assert d.verdict == "DROP_GROUP" and d.reason_code == "no_trainable_tokens"


def test_disposition_policy_rejects_mask_member_or_unknown_values():
    with pytest.raises(AdmissionError, match="disposition_choice_invalid"):
        DispositionPolicy(hard_wall_truncation="MASK_MEMBER")  # type: ignore[arg-type]
    with pytest.raises(AdmissionError, match="disposition_policy_invalid"):
        decide_member_disposition(_payload(), policy=object(), finalize_staleness_threshold=4)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 附录 A reason-code 映射逐行
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("dimension", "code", "verdict"),
    [
        ("token_provenance", "capture_record_missing", "FATAL"),
        ("token_provenance", "capture_record_not_complete", "FATAL"),
        ("logprob_alignment", "logprob_missing", "FATAL"),
        ("logprob_alignment", "logprob_partial_or_mismatch", "FATAL"),
        ("loss_mask_integrity", "no_trainable_tokens", "DROP_GROUP"),
        ("loss_mask_integrity", "loss_denominator_mismatch", "FATAL"),
        ("reward_scope", "credit_assignment_unknown", "FATAL"),
        ("reward_scope", "reward_value_mismatch", "FATAL"),
        ("reward_scope", "reward_event_ref_missing", "FATAL"),
        ("security_and_leakage", "sandbox_capability_facts_missing", "DROP_GROUP"),
        ("security_and_leakage", "sandbox_capability_unverified_non_root_user", "DROP_GROUP"),
        ("security_and_leakage", "sandbox_capability_violation_hidden_and_grader_assets_not_mounted", "FATAL"),
        ("security_and_leakage", "public_projection_marker_hit", "DROP_GROUP"),
        ("clean_grading", "not_replayed_on_clean_checkout", "FATAL"),
        ("policy_staleness", "staleness_exceeded", "DROP_GROUP"),
        ("security_and_leakage", "never_registered_code", "FATAL"),  # 未登记 code 一律 FATAL
    ],
)
def test_appendix_a_reason_code_rows(dimension: str, code: str, verdict: str):
    handshake = _handshake(steps=6) if code == "staleness_exceeded" else _handshake()
    payload = _payload(report=_report({dimension: [code]}), handshake=handshake)
    d = _decide(payload)
    assert d.verdict == verdict, d
    if code == "never_registered_code":
        assert d.reason_code == f"unmapped_reason_code:{dimension}:{code}"
    else:
        assert d.reason_code == code


def test_staleness_facts_missing_is_fatal_in_formal_path():
    payload = _payload(report=_report({"policy_staleness": ["staleness_facts_missing"]}), handshake=None)
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("FATAL", "staleness_facts_missing")


def test_grading_infra_failure_with_report_is_drop_and_counts_as_infra():
    """附录 A 行 4a/6a：failed_to_grade 保持 present，report 双维失败，与 outcome 的
    grading_infra_failure 归因一致 → DROP_GROUP（不是 ABORTED、不是 FATAL）。"""

    payload = _payload(
        outcome=_infra_outcome(),
        report=_report({"reward_scope": ["reward_scope_none"], "clean_grading": ["grading_infra_failure"]}),
        grading=_grading(outcome="failed_to_grade"),
    )
    d = _decide(payload)
    assert (d.verdict, d.reason_code, d.layer) == ("DROP_GROUP", "reward_scope_none", "eligibility")


def test_reward_scope_none_without_grading_infra_attribution_is_fatal():
    """行 4a 的账实矛盾半区：report 说 reward_scope_none，outcome 却说 reward 可得。"""

    payload = _payload(report=_report({"reward_scope": ["reward_scope_none"]}))
    d = _decide(payload)
    assert d.verdict == "FATAL" and d.reason_code == "reward_scope_none_without_grading_infra_attribution"


def test_fatal_dominates_pending_and_drop():
    """FATAL > pending > DROP：命中 capture 丢失 + hygiene 篡改 + no_trainable_tokens 时结论 FATAL，
    且不会因 pending 槽位未注入而 raise。"""

    payload = _payload(
        report=_report({
            "token_provenance": ["capture_record_missing"],
            "loss_mask_integrity": ["no_trainable_tokens"],
            "security_and_leakage": ["patch_test_tampering"],
        })
    )
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("FATAL", "capture_record_missing")


def test_class_contradicting_all_ok_facts_is_fatal():
    payload = _payload(report=_report(eligibility_class="offline_or_sft_candidate", reason_codes=["some_policy"]))
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("FATAL", "class_contradicts_facts")


# ---------------------------------------------------------------------------
# hygiene / agent executed 违规：pending → 显式注入
# ---------------------------------------------------------------------------


def _tampered_payload() -> AdmissionPayloadV1:
    return _payload(
        outcome=_outcome(task_outcome="unresolved"),
        report=_report({
            "security_and_leakage": ["patch_test_tampering"],
            "clean_grading": ["hygiene_rejected_test_tampering"],
        }),
        grading=_grading(outcome="unresolved"),
    )


def test_agent_violation_requires_injection_and_is_neutral():
    payload = _tampered_payload()
    with pytest.raises(DispositionNotInjectedError) as info:
        _decide(payload)
    assert info.value.slot == "agent_violation"
    drop = _decide(payload, DispositionPolicy(agent_violation="DROP_GROUP"))
    keep = _decide(payload, DispositionPolicy(agent_violation="KEEP_FULL"))
    assert (drop.verdict, drop.reason_code) == ("DROP_GROUP", "agent_violation_excluded")
    assert keep.verdict == "KEEP_FULL"


def test_anti_cheat_executed_code_is_pending_too():
    payload = _payload(
        outcome=_outcome(task_outcome="unresolved"),
        report=_report({"security_and_leakage": ["anti_cheat_executed_test_tampering"]}),
        grading=_grading(outcome="unresolved"),
    )
    with pytest.raises(DispositionNotInjectedError, match="agent_violation"):
        _decide(payload)


def test_pending_not_consulted_when_another_dimension_drops():
    payload = _payload(
        outcome=_outcome(task_outcome="unresolved"),
        report=_report({
            "security_and_leakage": ["patch_test_tampering"],
            "policy_staleness": ["staleness_exceeded"],
        }),
        grading=_grading(outcome="unresolved"),
        handshake=_handshake(steps=6),
    )
    d = _decide(payload)  # agent_violation 未注入也不 raise：结论已由 staleness 决定
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "staleness_exceeded")


# ---------------------------------------------------------------------------
# 契约封闭豁免集（无 EligibilityReport）
# ---------------------------------------------------------------------------


def test_exemption_grading_infra_without_report_is_drop():
    payload = _payload(outcome=_infra_outcome(eligibility_report_id=None), report=None,
                       grading=_grading(outcome="failed_to_grade"))
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "grading_infra_failure_without_report")


def test_exemption_unsafe_artifact_without_report_is_drop():
    payload = _payload(outcome=_unsafe_outcome(), report=None, grading=None, handshake=None)
    d = _decide(payload)
    assert (d.verdict, d.reason_code) == ("DROP_GROUP", "unsafe_artifact_permanent_rejection")


def test_present_without_report_outside_exemption_is_unrepresentable():
    """豁免集之外的"present_* 缺 EligibilityReport"在 Outcome v2 契约层就构造不出来
    （附录 A：其余形状 → FATAL 由契约不可表示性兜底）。"""

    with pytest.raises(ValidationError, match="豁免"):
        _outcome(eligibility_report_id=None)


# ---------------------------------------------------------------------------
# 显式 staleness 阈值接口
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [None, True, -1, "4"])
def test_explicit_staleness_threshold_required(bad: Any):
    with pytest.raises(AdmissionError, match="staleness_threshold_not_configured"):
        _decide(_payload(), threshold=bad)


def test_staleness_threshold_authority_mismatch_is_fatal():
    d = _decide(_payload(), threshold=8)  # 载荷记录的 finalize 阈值是 4
    assert (d.verdict, d.reason_code) == ("FATAL", "staleness_threshold_authority_mismatch")


def test_payload_pins_finalize_staleness_against_report_dimension():
    """载荷 validator：finalize staleness 数值与 report 的 policy_staleness 维结论必须互洽。"""

    with pytest.raises(AdmissionError, match="admission_payload_inconsistent"):
        _payload(handshake=_handshake(steps=6))  # 6 > 4 却 report 说 ok
    with pytest.raises(AdmissionError, match="admission_payload_inconsistent"):
        _payload(report=_report({"policy_staleness": ["staleness_exceeded"]}))  # 1 <= 4 却 report 说 exceeded


# ---------------------------------------------------------------------------
# 载荷派生 / 盖章 / 解引用的 fail-closed 面
# ---------------------------------------------------------------------------


def test_payload_derivation_rejects_reference_and_reward_contradictions():
    with pytest.raises(AdmissionError, match="admission_payload_inconsistent"):
        _payload(report=None)  # outcome 引用 elig_x 却无报告
    with pytest.raises(AdmissionError, match="admission_payload_inconsistent"):
        _payload(grading=_grading(outcome="failed_to_grade"))  # outcome 说 reward 可得，评分说不可得
    with pytest.raises(AdmissionError, match="admission_payload_inconsistent"):
        _payload(grading=_grading(outcome="unresolved"))  # resolved outcome 配 unresolved 评分
    other = EligibilityReport.finalize(
        report_id="elig_other", trajectory_id=TRAJ, gate_version=GATE_VERSION, facts=_facts(),
        eligibility_class="online_policy_loss_eligible", reason_codes=[], created_at_utc=CREATED,
    )
    with pytest.raises(AdmissionError, match="admission_payload_inconsistent"):
        _payload(report=other)  # 报告 id 与 outcome 引用错位


def _leaf(**meta: Any):
    class _Leaf:
        def __init__(self) -> None:
            self.metadata = dict(meta)

    return _Leaf()


def _identity_meta(**over: Any) -> dict[str, Any]:
    meta = {
        "rh2_physical_attempt_id": PAID, "rh2_rollout_execution_id": TRAJ, "task_id": "swe_gym_lite::x",
        "environment_package_digest": ENV, "public_bundle_digest": PUB,
        "eligibility_report_ref": "elig_x", "training_eligibility_class": "online_policy_loss_eligible",
    }
    meta.update(over)
    return meta


def test_stamp_then_resolve_round_trip_and_join_negatives():
    payload = _payload()
    leaf = _leaf()
    stamp_admission_payload([leaf, [_leaf()]], payload)
    assert ADMISSION_METADATA_KEY in leaf.metadata
    good = {**_identity_meta(), **leaf.metadata}
    assert resolve_admission_payload(good) == payload

    negatives = {
        "admission_attempt_mismatch": {"rh2_physical_attempt_id": "miles_g0_m1#p2-deadbeef"},
        "admission_execution_mismatch": {"rh2_rollout_execution_id": "miles_g0_m0"},
        "admission_task_mismatch": {"task_id": "swe_gym_lite::other"},
        "admission_environment_mismatch": {"environment_package_digest": "sha256:" + "c" * 64},
        "admission_public_bundle_mismatch": {"public_bundle_digest": "sha256:" + "d" * 64},
        "derived_view_mismatch": {"training_eligibility_class": "offline_or_sft_candidate"},
        "attempt_identity_missing": {"rh2_physical_attempt_id": None},
    }
    for code, mutation in negatives.items():
        with pytest.raises(AdmissionError, match=code):
            resolve_admission_payload({**good, **mutation})
    with pytest.raises(AdmissionError, match="admission_payload_missing"):
        resolve_admission_payload(_identity_meta())
    # 复核修复 #6a：组准入（require_dispatch_identity=True）要求分派三键必须在场；legacy 自检模式只在键在场时比较
    for key in ("task_id", "environment_package_digest", "public_bundle_digest"):
        stripped = {k: v for k, v in good.items() if k != key}
        assert resolve_admission_payload(stripped) == payload
        with pytest.raises(AdmissionError, match="admission_dispatch_identity_missing"):
            resolve_admission_payload(stripped, require_dispatch_identity=True)
    no_env = _payload(env=None)
    leaf2 = _leaf()
    stamp_admission_payload(leaf2, no_env)
    with pytest.raises(AdmissionError, match="admission_environment_identity_missing"):
        resolve_admission_payload({**_identity_meta(), **leaf2.metadata, "environment_package_digest": ENV},
                                  require_dispatch_identity=True)
    tampered = {**good, ADMISSION_METADATA_KEY: {**good[ADMISSION_METADATA_KEY]}}
    tampered[ADMISSION_METADATA_KEY]["eligibility_report"] = {
        **tampered[ADMISSION_METADATA_KEY]["eligibility_report"],
        "facts": _facts({"logprob_alignment": ["logprob_missing"]}).model_dump(mode="json"),
    }
    with pytest.raises(AdmissionError, match="admission_payload_invalid"):  # facts_digest 重算失败
        resolve_admission_payload(tampered)


def test_resolve_requires_derived_view_absent_when_no_report():
    payload = _payload(outcome=_unsafe_outcome(), report=None, grading=None, handshake=None)
    leaf = _leaf()
    stamp_admission_payload(leaf, payload)
    base = {**_identity_meta(), **leaf.metadata}
    with pytest.raises(AdmissionError, match="derived_view_without_report"):
        resolve_admission_payload(base)
    base.pop("eligibility_report_ref")
    base.pop("training_eligibility_class")
    assert resolve_admission_payload(base).eligibility_report is None


def test_stamp_rejects_foreign_leaf_and_allows_stale_retry_history():
    payload = _payload()
    with pytest.raises(AdmissionError, match="admission_stamp_attempt_mismatch"):
        stamp_admission_payload(_leaf(rh2_physical_attempt_id="miles_g0_m1#p9-ffffffff"), payload)
    with pytest.raises(AdmissionError, match="admission_stamp_execution_mismatch"):
        stamp_admission_payload(_leaf(rh2_rollout_execution_id="miles_g0_m0"), payload)
    # 同一样本对象上一次 attempt 留下的历史载荷：叶身份已是本次 attempt → 允许覆盖
    old = _payload(outcome=_outcome(identity=ExecutionIdentity(
        prompt_group_id="miles_g0", group_index=0, rollout_execution_id=TRAJ,
        physical_attempt_id="miles_g0_m1#p0-00000000", physical_attempt_seq=1)))
    leaf = _leaf(rh2_physical_attempt_id=PAID)
    leaf.metadata[ADMISSION_METADATA_KEY] = old.model_dump(mode="json")
    stamp_admission_payload(leaf, payload)
    assert leaf.metadata[ADMISSION_METADATA_KEY]["physical_attempt_id"] == PAID
    # fan-out 叶带别的 attempt 的载荷（叶自身无身份）→ 拒
    forged = _leaf()
    forged.metadata[ADMISSION_METADATA_KEY] = old.model_dump(mode="json")
    with pytest.raises(AdmissionError, match="admission_stamp_conflict"):
        stamp_admission_payload(forged, payload)


def test_payload_is_frozen_and_rejects_unknown_fields():
    payload = _payload()
    with pytest.raises(ValidationError):
        payload.task_id = "other"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        AdmissionPayloadV1.model_validate({**payload.model_dump(mode="json"), "smuggled": 1})
