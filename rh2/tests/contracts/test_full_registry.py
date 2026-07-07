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
    "rh2.grading_backpressure_event.v1",
    "rh2.group_repair_signal.v1",
    "rh2.public_task_bundle.v1",
    "rh2.private_grading_bundle.v1",
    "rh2.bundle_pair.v1",
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


def test_full_registry_is_contracts_plus_exactly_the_five_new_ids():
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


@pytest.mark.parametrize("schema_id", sorted(EXPECTED_EXTRA_IDS))
def test_unknown_field_rejected_for_every_new_schema(schema_id, frozen_pair):
    factories = {
        "rh2.grading_backpressure_event.v1": _backpressure_payload,
        "rh2.group_repair_signal.v1": _signal_payload,
        "rh2.public_task_bundle.v1": lambda: frozen_pair.public.model_dump(mode="json"),
        "rh2.private_grading_bundle.v1": lambda: frozen_pair.private.model_dump(mode="json"),
        "rh2.bundle_pair.v1": lambda: frozen_pair.model_dump(mode="json"),
    }
    payload = factories[schema_id]()
    payload["unexpected_extra_field"] = "smuggled"
    with pytest.raises(ValidationError, match="unexpected_extra_field"):
        FULL_SCHEMA_REGISTRY[schema_id].model_validate(payload)
