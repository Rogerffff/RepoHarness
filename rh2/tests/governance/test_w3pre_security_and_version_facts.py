"""Wave3 前置清理批（决策包 D2+B v2，owner 2026-09-04 已批）：security 维与 policy_staleness 维的新语义。

取代 `test_w1b_security_capability_facts.py`（每轨迹 sandbox 能力事实证明系统已随 D2-2 删除）。

被测事实：
- security 维只判本次轨迹的执行级事实（executed finding / hygiene 篡改）：没有任何 sandbox
  sidecar、`findings=()` 的合格轨迹直接 online——证明 gate 不再读能力事实；
- 旧类型 `SandboxCapabilityFacts` 只作冻结历史 schema（可解析、校验器不变），gate / wrapper /
  finalize_rollout 的签名与模块面都不再含它；
- 第七维"版本事实可用且合法"：缺失 / 非法（非十进制）/ 未来版本各一负例，合法一正例；
  finalize-time lag 超过握手记录的阈值镜像也**不**失败（`staleness_exceeded` 不再存在）；
  `require_real_weight_versions=False`（S1 兼容语义）允许 `step_0` 这类哨兵。
"""

from __future__ import annotations

import inspect

import pytest
from contract_samples import valid_backend_handshake
from governance_samples import executed_finding_payload, numeric_backend_handshake, run_finalize
from pydantic import ValidationError

import repoharness2.governance as governance
from repoharness2.governance import GATE_VERSION, SandboxCapabilityFacts, finalize_rollout, gate, wrapper

_LEGACY_REQUIRED = (
    "non_root_user",
    "linux_capabilities_dropped",
    "pids_limit_enforced",
    "cpu_limit_enforced",
    "memory_limit_enforced",
    "writable_mounts_allowlisted_with_quota",
    "network_model_proxy_only",
    "hidden_and_grader_assets_not_mounted",
    "git_future_refs_reflog_remotes_cleared",
)


def _code_strings(fn) -> set[str]:
    """函数代码对象里的字符串常量（剔除 docstring）——用于钉死"某理由码不再由该函数发出"。"""

    return {c for c in fn.__code__.co_consts if isinstance(c, str)} - {fn.__doc__}


def _legacy_capability_facts(**overrides):
    payload = {
        "schema_id": "rh2.sandbox_capability_facts.v1",
        "trajectory_id": "traj_0001",
        "lease_id": "lease_0001",
        "verified_capabilities": list(_LEGACY_REQUIRED),
        "violations": [],
        "evidence_refs": ["sandbox_probe_0001"],
        "verified_at_utc": "2026-07-07T09:30:25Z",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# security 维：不再读任何 sandbox sidecar
# ---------------------------------------------------------------------------


async def test_qualified_trajectory_without_any_sandbox_sidecar_is_online():
    """D2-2 正例：合格轨迹、`findings=()`、没有能力事实 → security 维通过、整体 online。
    这是预期行为：sandbox 合规由创建期强制 + 启动前探针保证，不在 eligibility。"""

    final = await run_finalize(findings=())
    report = final.eligibility_report
    assert report.gate_version == GATE_VERSION == "rh2.gate.w3pre.v3"
    assert report.eligibility_class == "online_policy_loss_eligible"
    assert report.reason_codes == []
    fact = report.facts.security_and_leakage
    assert fact.ok is True and fact.reason_codes == []
    joined = " ".join(fact.evidence_refs)
    assert "sandbox_capability_facts" not in joined and "public_projection_scan" not in joined
    assert final.group_repair_signal.degraded is False


async def test_executed_finding_still_fails_security():
    final = await run_finalize(findings=[executed_finding_payload()])
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is False and fact.reason_codes == ["anti_cheat_executed_test_tampering"]
    assert final.eligibility_report.eligibility_class == "audit_only_or_rejected"


def test_capability_facts_machinery_removed_from_gate_and_finalize_signature():
    """删除清单钉死：provider / required / lease 参数、必需集常量、三族理由码分支都不在了。"""

    params = set(inspect.signature(finalize_rollout).parameters)
    assert not {"sandbox_capability_facts", "sandbox_capability_facts_required", "sandbox_lease_id"} & params
    assert "require_real_weight_versions" in params
    assert not hasattr(gate, "REQUIRED_SANDBOX_CAPABILITIES") and not hasattr(gate, "SandboxCapabilityFacts")
    assert not hasattr(governance, "REQUIRED_SANDBOX_CAPABILITIES")
    assert list(inspect.signature(gate._dim_security_and_leakage).parameters) == ["grading_report", "findings"]
    assert set(inspect.signature(gate._check_wiring).parameters) == {
        "projection", "grading_report", "capture_records", "findings", "handshake",
    }
    # 代码里发出的字符串常量（不含 docstring）：三族能力事实理由码与 marker 命中码都不在了
    emitted = _code_strings(gate._dim_security_and_leakage)
    assert not {"sandbox_capability_facts_missing", "public_projection_marker_hit"} & emitted
    assert not any(s.startswith("sandbox_capability_") for s in emitted)
    assert "SandboxCapabilityFacts" not in wrapper.__dict__ and "_scan_public_projection" not in wrapper.__dict__


def test_frozen_sandbox_capability_facts_schema_still_parses_but_lives_outside_gate():
    """冻结历史 schema：旧 JSON 仍可解析、校验器不变；类型来自独立兼容模块而不是 gate。"""

    from repoharness2.governance import sandbox_capability_facts as frozen

    facts = SandboxCapabilityFacts.model_validate(_legacy_capability_facts())
    assert facts.schema_id == "rh2.sandbox_capability_facts.v1"
    assert SandboxCapabilityFacts is frozen.SandboxCapabilityFacts
    assert SandboxCapabilityFacts.__module__ == "repoharness2.governance.sandbox_capability_facts"
    with pytest.raises(ValidationError, match="重复"):
        SandboxCapabilityFacts.model_validate(
            _legacy_capability_facts(verified_capabilities=["non_root_user", "non_root_user"])
        )
    with pytest.raises(ValidationError, match="矛盾"):
        SandboxCapabilityFacts.model_validate(_legacy_capability_facts(violations=["non_root_user"]))


# ---------------------------------------------------------------------------
# 第七维：版本事实可用且合法（B-1 改判 D1-4）
# ---------------------------------------------------------------------------


async def test_version_facts_missing_fails_dimension():
    final = await run_finalize(handshake=None)
    fact = final.eligibility_report.facts.policy_staleness
    assert fact.ok is False and fact.reason_codes == ["staleness_facts_missing"]
    assert final.eligibility_report.eligibility_class == "offline_or_sft_candidate"


async def test_version_facts_non_numeric_is_invalid():
    """非法：任一版本不是十进制数字串（哨兵 `step_5`、带空白、带符号）。"""

    for bad in (["step_5"], ["120", " 119"], ["+119"], ["119", "1e2"]):
        handshake = numeric_backend_handshake(weight_versions_seen=bad)
        final = await run_finalize(handshake=handshake)
        fact = final.eligibility_report.facts.policy_staleness
        assert fact.ok is False and fact.reason_codes == ["staleness_facts_invalid"], bad
        assert any(ref.startswith("weight_versions_not_numeric:") for ref in fact.evidence_refs)
        assert final.eligibility_report.eligibility_class == "offline_or_sft_candidate"
    final = await run_finalize(handshake=numeric_backend_handshake(policy_version="step_120"))
    assert final.eligibility_report.facts.policy_staleness.reason_codes == ["staleness_facts_invalid"]


async def test_version_facts_future_version_is_invalid():
    """未来版本：任一 seen 版本比 finalize 时刻 current 更新——包括 min ≤ current 但 max > current
    的形状（seen=[119, 121] / current=120），与消费侧 W1b 叶版本绑定的 FATAL 口径一致。"""

    for seen in (["121"], ["119", "121"], ["121", "125"]):
        final = await run_finalize(handshake=numeric_backend_handshake(weight_versions_seen=seen))
        fact = final.eligibility_report.facts.policy_staleness
        assert fact.ok is False and fact.reason_codes == ["staleness_facts_invalid"], seen
        assert "weight_version_ahead_of_current" in fact.evidence_refs


async def test_legal_version_facts_pass_and_lag_is_observation_only():
    """正例：版本合法 → 通过；finalize-time lag 超过握手记录的阈值镜像（6 > 4，
    staleness_within_threshold=False）也不失败——`staleness_exceeded` 已不存在。"""

    handshake = numeric_backend_handshake(
        policy_version="9", weight_versions_seen=["3", "4"], staleness_steps=6,
        staleness_threshold=4, staleness_within_threshold=False,
    )
    final = await run_finalize(handshake=handshake)
    fact = final.eligibility_report.facts.policy_staleness
    assert fact.ok is True and fact.reason_codes == []
    assert "finalize_lag_observed:6" in fact.evidence_refs
    assert "weight_versions_range:3..4:current:9" in fact.evidence_refs
    assert "hs_0001" in fact.evidence_refs
    assert final.eligibility_report.eligibility_class == "online_policy_loss_eligible"
    assert "staleness_exceeded" not in gate._DIMENSION_DEGRADE_FLOOR  # 只是提醒：维度表里没有阈值概念


async def test_legacy_sentinel_versions_allowed_only_when_version_contract_is_off():
    """S1 兼容语义（require_real_weight_versions=False，与 SlimeBindingConfig 同名旗标）：
    `step_120` / `default` 哨兵版本通过并留痕；formal 契约（True）下同一握手判非法。"""

    legacy = valid_backend_handshake()  # policy_version=step_120, seen=[default]
    relaxed = await run_finalize(handshake=legacy, require_real_weight_versions=False)
    fact = relaxed.eligibility_report.facts.policy_staleness
    assert fact.ok is True
    assert "weight_versions_contract:legacy_sentinel_allowed" in fact.evidence_refs
    assert relaxed.eligibility_report.eligibility_class == "online_policy_loss_eligible"

    strict = await run_finalize(handshake=legacy, require_real_weight_versions=True)
    assert strict.eligibility_report.facts.policy_staleness.reason_codes == ["staleness_facts_invalid"]


def test_gate_has_no_threshold_reason_code():
    """`staleness_exceeded` 不再由 gate 发出；握手里的 staleness_threshold / within 字段 gate 不读。"""

    assert "staleness_exceeded" not in _code_strings(gate._dim_policy_staleness)
    assert {"staleness_facts_missing", "staleness_facts_invalid"} <= _code_strings(gate._dim_policy_staleness)
    names = set(gate._dim_policy_staleness.__code__.co_names)
    assert not {"staleness_within_threshold", "staleness_threshold", "accepted"} & names
