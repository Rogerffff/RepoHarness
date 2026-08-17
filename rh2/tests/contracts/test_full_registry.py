"""聚合 registry（S1-9，codex#5 收编）测试：五个新 schema 经 CLI 全流程可校验。

覆盖：① 聚合表 = contracts 表 + 恰好五个新条目、零冲突；② 每个新对象
合法样例过 inspect-rh2-artifact（退出码 0）；③ 未知字段拒收；④ marker
豁免口径——private 半区（评分材料容器）默认豁免、public 半区照扫。
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from repoharness2.cli import EXIT_FORBIDDEN_MARKER, EXIT_OK, main
from repoharness2.contracts import SCHEMA_REGISTRY
from repoharness2.envpack.bundles import load_bundle_pairs
from repoharness2.governance import GroupRepairSignal
from repoharness2.grading.queue import BackpressureEvent
from repoharness2.registry import (
    EXTRA_SCHEMA_REGISTRY,
    FULL_MARKER_SCAN_EXEMPT_SCHEMAS,
    FULL_SCHEMA_REGISTRY,
)

EXPECTED_EXTRA_IDS = {
    # S1-9 收编的五个
    "rh2.grading_backpressure_event.v1",
    "rh2.group_repair_signal.v1",
    "rh2.public_task_bundle.v1",
    "rh2.private_grading_bundle.v1",
    "rh2.private_grading_bundle.v2",
    "rh2.validation_only_bundle.v1",
    "rh2.environment_package.v1",
    "rh2.bundle_pair.v1",
    # FA-0（2026-07-12）：fa_runtime 四契约（S1 核心 15 个保持冻结，走聚合扩展）
    "rh2.fa.execution_identity.v1",
    "rh2.fa.rollout_attempt_outcome.v1",
    "rh2.fa.rollout_attempt_outcome.v2",
    "rh2.fa.baseline_workspace_manifest.v1",
    "rh2.fa.frozen_patch_artifact.v1",
    "rh2.fa.training_runtime_window.v1",
    "rh2.fa.model_call_attempt.v1",
}


def _write(tmp_path, name, payload) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _backpressure_payload() -> dict:
    return BackpressureEvent(
        event_id="bp_full_reg",
        trajectory_id="traj_0001",
        task_id="django__django-11099",
        queue_capacity=8,
        queue_depth=8,
        active_grading_count=4,
        concurrency_limit=4,
        occurred_at_utc=datetime(2026, 7, 7, 9, 30, 25, tzinfo=timezone.utc),
    ).model_dump(mode="json")


def _signal_payload() -> dict:
    return GroupRepairSignal(
        trajectory_id="traj_0001",
        group_id="group_task42",
        report_ref="elig_test_0001",
        eligibility_class="offline_or_sft_candidate",
        degraded=False,
        failed_dimensions=[],
        reason_codes=["s1_default_ceiling_offline"],
    ).model_dump(mode="json")


@pytest.fixture(scope="module")
def frozen_pair():
    """真实冻结题（含 frozen_v1 防漂移校验）——bundle 样例不手搓，用生产数据。"""
    return load_bundle_pairs(subset=["django__django-11099"])[0]


def test_full_registry_is_contracts_plus_exactly_the_expected_extra_ids():
    assert set(EXTRA_SCHEMA_REGISTRY) == EXPECTED_EXTRA_IDS
    assert set(FULL_SCHEMA_REGISTRY) == set(SCHEMA_REGISTRY) | EXPECTED_EXTRA_IDS
    assert not set(EXTRA_SCHEMA_REGISTRY) & set(SCHEMA_REGISTRY)
    # 聚合表键与模型默认 schema_id 一致（registry.py 的 import 期断言在此复证）
    for schema_id, model_cls in FULL_SCHEMA_REGISTRY.items():
        assert model_cls.model_fields["schema_id"].default == schema_id


def test_backpressure_event_passes_cli(tmp_path):
    assert main([_write(tmp_path, "bp.json", _backpressure_payload())]) == EXIT_OK


def test_group_repair_signal_passes_cli(tmp_path):
    assert main([_write(tmp_path, "signal.json", _signal_payload())]) == EXIT_OK


def test_public_bundle_passes_cli_with_marker_scan(tmp_path, frozen_pair, capsys):
    """public 半区不豁免：模型可见面必须 0 命中（S1-2 实测 8 题 0 误报）。"""
    assert "rh2.public_task_bundle.v1" not in FULL_MARKER_SCAN_EXEMPT_SCHEMAS
    path = _write(tmp_path, "public.json", frozen_pair.public.model_dump(mode="json"))
    assert main([path]) == EXIT_OK
    assert "marker 扫描通过" in capsys.readouterr().out


def test_private_bundle_exempt_by_default_hits_when_forced(tmp_path, frozen_pair):
    """private 半区 = 评分材料容器：默认豁免（退出码 0），强制扫描必命中
    （它的字段名就是 F2P/P2P/test_patch 本身——这是内容不是泄漏）。"""
    assert "rh2.private_grading_bundle.v1" in FULL_MARKER_SCAN_EXEMPT_SCHEMAS
    path = _write(tmp_path, "private.json", frozen_pair.private.model_dump(mode="json"))
    assert main([path]) == EXIT_OK
    assert main([path, "--force-marker-scan"]) == EXIT_FORBIDDEN_MARKER


def test_bundle_pair_passes_cli_via_exemption(tmp_path, frozen_pair):
    assert "rh2.bundle_pair.v1" in FULL_MARKER_SCAN_EXEMPT_SCHEMAS
    path = _write(tmp_path, "pair.json", frozen_pair.model_dump(mode="json"))
    assert main([path]) == EXIT_OK


def test_eligibility_report_exempt_when_evidence_quotes_marker(tmp_path):
    """S1-9 定策回归（任务点名形态）：security 维 evidence 串引用命中的 marker 本身
    （S1-5 实测形如 `public_projection_scan:hit:$.path:fail_to_pass:key`，
    此前该报告过 inspect-rh2-artifact 会 exit 4）——现按 runtime-private 审计
    资产以 schema_id 白名单豁免（沿用既有豁免机制），--force-marker-scan 保留
    强制通道。注意真正的 marker 防线在 S1-5 public projection 扫描（不看豁免表）。"""
    from contract_samples import valid_eligibility_facts, valid_eligibility_report

    from repoharness2.contracts import EligibilityFacts, compute_facts_digest

    assert "rh2.eligibility_report.v1" in FULL_MARKER_SCAN_EXEMPT_SCHEMAS

    facts = valid_eligibility_facts()
    facts["security_and_leakage"] = {
        "ok": False,
        "reason_codes": ["public_projection_marker_hit"],
        # S1-5 的真实 evidence 形态：命中路径 + marker 名 + key/value 位置
        "evidence_refs": ["public_projection_scan:hit:$.reward_facts.components.bonus:fail_to_pass:key"],
    }
    payload = valid_eligibility_report()
    payload["facts"] = facts
    payload["facts_digest"] = compute_facts_digest(EligibilityFacts.model_validate(facts))
    payload["eligibility_class"] = "audit_only_or_rejected"  # security 失败强制 audit
    payload["reason_codes"] = ["public_projection_marker_hit"]
    payload["derived_view_class"] = "audit_only_or_rejected"

    path = _write(tmp_path, "elig_hit.json", payload)
    assert main([path]) == EXIT_OK  # 默认豁免：审计资产引用泄漏名词合法
    assert main([path, "--force-marker-scan"]) == EXIT_FORBIDDEN_MARKER  # 强制通道仍在


def _fa_identity_payload() -> dict:
    return {
        "schema_id": "rh2.fa.execution_identity.v1",
        "prompt_group_id": "pg_5",
        "group_index": 5,
        "rollout_execution_id": "exec_22",
    }


def _fa_outcome_payload() -> dict:
    return {
        "schema_id": "rh2.fa.rollout_attempt_outcome.v1",
        "outcome_id": "o1",
        "identity": _fa_identity_payload(),
        "member_slot": 2,
        "attempt_number": 1,
        "completion_class": "present",
        "task_outcome": "unresolved",
        "recovery_scope": "none",
        "turn_weight_versions": ["1", "1"],
        "intra_execution_version_span": 0,
        "current_version_at_finalize": "1",
        "eligibility_report_id": "er_1",
    }


def _fa_outcome_v2_payload() -> dict:
    # v2 强制四层身份（F2-1b codex 审查 P1-2）：样例必须带 paid/seq
    identity = {
        **_fa_identity_payload(),
        "physical_attempt_id": "exec_22#p1-cafe0123",
        "physical_attempt_seq": 1,
    }
    return {
        "schema_id": "rh2.fa.rollout_attempt_outcome.v2",
        "outcome_id": "o2",
        "identity": identity,
        "member_slot": 2,
        "attempt_number": 1,
        "completion_class": "present_truncated",
        "termination_kind": "task_token_budget_exhausted",
        "task_outcome": "unresolved",
        "recovery_scope": "none",
        "turn_weight_versions": ["1", "1"],
        "intra_execution_version_span": 0,
        "current_version_at_finalize": "1",
        "eligibility_report_id": "er_2",
    }


def _baseline_manifest_payload() -> dict:
    from repoharness2.contracts.baseline_manifest import (
        BASELINE_MANIFEST_POLICY_V1,
        compute_policy_digest,
    )

    return {
        "schema_id": "rh2.fa.baseline_workspace_manifest.v1",
        "task_id": "t1",
        "workdir": "/testbed",
        "public_bundle_digest": "sha256:" + "e" * 64,
        "runtime_image_digest": "sha256:" + "1" * 64,
        "materialized_head": "a" * 40,
        "task_base_commit": "b" * 40,
        "policy": BASELINE_MANIFEST_POLICY_V1.model_dump(mode="json"),
        "policy_digest": compute_policy_digest(BASELINE_MANIFEST_POLICY_V1),
        "entries": [{
            "path": "a.py", "object_type": "regular", "mode": "100644",
            "content_digest": "sha256:" + "c" * 64,
        }],
    }


def _frozen_patch_payload() -> dict:
    import base64 as _b64
    import hashlib as _h

    raw = b"data"
    return {
        "schema_id": "rh2.fa.frozen_patch_artifact.v1",
        "task_id": "t1",
        "rollout_execution_id": "exec_1",
        "physical_attempt_id": "exec_1#p1-aaaa",
        "baseline_manifest_digest": "sha256:" + "b" * 64,
        "public_bundle_digest": "sha256:" + "e" * 64,
        "runtime_image_digest": "sha256:" + "1" * 64,
        "materialized_head": "a" * 40,
        "entries": [{
            "path": "a.py", "operation": "add", "object_type": "regular",
            "mode": "100644",
            "content_b64": _b64.b64encode(raw).decode(),
            "content_digest": "sha256:" + _h.sha256(raw).hexdigest(),
        }],
        "excluded_pathset_changed": False,
    }


def _fa_window_payload() -> dict:
    return {
        "schema_id": "rh2.fa.training_runtime_window.v1",
        "update_epoch": 3,
        "phase": "ACTIVE",
        "old_version": "2",
        "target_version": "3",
        "active_version": "3",
        "window_started_at": "2026-07-12T00:00:00+00:00",
        "window_completed_at": "2026-07-12T00:00:12+00:00",
        "fencing_token": "fence_3",
    }


def _fa_attempt_payload() -> dict:
    return {
        "schema_id": "rh2.fa.model_call_attempt.v1",
        "logical_turn_id": "turn_7",
        "model_call_attempt_id": "attempt_7_2",
        "attempt_number": 2,
        "delivery_status": "delivered",
        "capture_record_ref": "cap_7",
        "weight_version": "3",
    }


def _grading_v2_payload():
    return {
        "schema_id": "rh2.private_grading_bundle.v2",
        "instance_id": "getmoto__moto-1",
        "repo": "getmoto/moto",
        "repo_key_lower": "getmoto/moto",
        "version": "4.1",
        "base_commit": "0" * 40,
        "test_patch": "diff --git a/t.py b/t.py\n+x\n",
        "fail_to_pass": ["t.py::test_a"],
        "pass_to_pass": [],
        "eval_cmd": "pytest -n0 -rA",
        "spec_vendor_id": "swegym_constants_242429c1",
    }


def _validation_only_payload():
    import hashlib as _h
    patch = "diff --git a/m.py b/m.py\n-bug\n+fix\n"
    return {
        "schema_id": "rh2.validation_only_bundle.v1",
        "instance_id": "getmoto__moto-1",
        "golden_patch": patch,
        "golden_patch_sha256": "sha256:" + _h.sha256(patch.encode()).hexdigest(),
    }


def _environment_package_payload():
    d = "sha256:" + "a" * 64
    return {
        "schema_id": "rh2.environment_package.v1",
        "task_id": "swe_gym_lite::getmoto__moto-1",
        "source": "swe_gym_lite",
        "instance_id": "getmoto__moto-1",
        "repo": "getmoto/moto",
        "repo_key_lower": "getmoto/moto",
        "base_commit": "0" * 40,
        "image": "xingyaoww/sweb.eval.x86_64.getmoto_s_moto-1:latest",
        "image_manifest_digest": d,
        "public_bundle_digest": d,
        "grading_bundle_digest": d,
        "validation_bundle_digest": d,
        "raw_archive_sha256": d,
        "image_manifest_keyed_sha256": d,
        "spec_vendor_json_sha256": d,
    }


@pytest.mark.parametrize("schema_id", sorted(EXPECTED_EXTRA_IDS))
def test_unknown_field_rejected_for_every_new_schema(schema_id, frozen_pair):
    factories = {
        "rh2.grading_backpressure_event.v1": _backpressure_payload,
        "rh2.group_repair_signal.v1": _signal_payload,
        "rh2.public_task_bundle.v1": lambda: frozen_pair.public.model_dump(mode="json"),
        "rh2.private_grading_bundle.v1": lambda: frozen_pair.private.model_dump(mode="json"),
        "rh2.private_grading_bundle.v2": _grading_v2_payload,
        "rh2.validation_only_bundle.v1": _validation_only_payload,
        "rh2.environment_package.v1": _environment_package_payload,
        "rh2.bundle_pair.v1": lambda: frozen_pair.model_dump(mode="json"),
        "rh2.fa.execution_identity.v1": _fa_identity_payload,
        "rh2.fa.rollout_attempt_outcome.v1": _fa_outcome_payload,
        "rh2.fa.rollout_attempt_outcome.v2": _fa_outcome_v2_payload,
        "rh2.fa.baseline_workspace_manifest.v1": _baseline_manifest_payload,
        "rh2.fa.frozen_patch_artifact.v1": _frozen_patch_payload,
        "rh2.fa.training_runtime_window.v1": _fa_window_payload,
        "rh2.fa.model_call_attempt.v1": _fa_attempt_payload,
    }
    payload = factories[schema_id]()
    payload["unexpected_extra_field"] = "smuggled"
    with pytest.raises(ValidationError, match="unexpected_extra_field"):
        FULL_SCHEMA_REGISTRY[schema_id].model_validate(payload)


# ---- S2-1 T2（codex 轮次 12 一般 4）：v2 三 schema 的 CLI 扫描行为 -------------

def test_grading_v2_exempt_by_default_hits_when_forced(tmp_path):
    assert "rh2.private_grading_bundle.v2" in FULL_MARKER_SCAN_EXEMPT_SCHEMAS
    path = _write(tmp_path, "g2.json", _grading_v2_payload())
    assert main([path]) == EXIT_OK
    assert main([path, "--force-marker-scan"]) == EXIT_FORBIDDEN_MARKER


def test_validation_only_exempt_by_default_hits_when_forced(tmp_path):
    assert "rh2.validation_only_bundle.v1" in FULL_MARKER_SCAN_EXEMPT_SCHEMAS
    payload = _validation_only_payload()
    payload["golden_patch"] = payload["golden_patch"] + "\n# touches test_patch semantics\n"
    import hashlib as _h
    payload["golden_patch_sha256"] = "sha256:" + _h.sha256(payload["golden_patch"].encode()).hexdigest()
    path = _write(tmp_path, "vo.json", payload)
    assert main([path]) == EXIT_OK
    assert main([path, "--force-marker-scan"]) == EXIT_FORBIDDEN_MARKER


def test_environment_package_passes_default_and_forced(tmp_path):
    assert "rh2.environment_package.v1" not in FULL_MARKER_SCAN_EXEMPT_SCHEMAS
    path = _write(tmp_path, "pkg.json", _environment_package_payload())
    assert main([path]) == EXIT_OK
    assert main([path, "--force-marker-scan"]) == EXIT_OK
