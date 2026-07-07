"""public projection 扫描的行为测试：命中降级、确定性排序、结果对象互检。

全部经 finalize_rollout 驱动（扫描函数是模块私有，生产路径只此一条）。
"""

from __future__ import annotations

import pytest
from contract_samples import valid_trajectory_projection
from governance_samples import run_finalize
from pydantic import ValidationError

from repoharness2.governance import ProjectionScanResult


async def test_clean_projection_scan_result_is_clean():
    final = await run_finalize()
    assert final.scan_result.clean is True
    assert final.scan_result.hits == []
    assert final.scan_result.trajectory_id == "traj_0001"
    assert final.scan_result.scanned_schema_id == "rh2.trajectory_projection.v1"


async def test_forbidden_marker_in_projection_fails_security_dimension():
    """marker 命中 -> security 维失败 -> schema 强制 audit 档。

    形态：reward components 的 key "fail_to_pass_bonus" 归一化后含 marker
    "fail_to_pass"（A6 名单）——评分私有字段名混进了训练可见投影。
    """

    projection = valid_trajectory_projection()
    projection["reward_facts"]["components"] = {"fail_to_pass_bonus": 0.25}
    final = await run_finalize(projection=projection)

    scan = final.scan_result
    assert scan.clean is False
    assert len(scan.hits) == 1
    hit = scan.hits[0]
    assert hit.path == "$.reward_facts.components.fail_to_pass_bonus"
    assert hit.marker == "fail_to_pass"
    assert hit.kind == "key"

    report = final.eligibility_report
    fact = report.facts.security_and_leakage
    assert fact.ok is False
    assert "public_projection_marker_hit" in fact.reason_codes
    assert (
        "public_projection_scan:hit:$.reward_facts.components.fail_to_pass_bonus:fail_to_pass:key"
        in fact.evidence_refs
    )
    assert report.eligibility_class == "audit_only_or_rejected"
    assert final.group_repair_signal.failed_dimensions == ["security_and_leakage"]


async def test_multiple_hits_sorted_deterministically():
    """多处命中按 (path, marker, kind) 升序——跨进程 evidence 逐字节可比。"""

    projection = valid_trajectory_projection()
    projection["reward_facts"]["components"] = {"fail_to_pass_bonus": 0.25}
    projection["branches"][0]["branch_id"] = "b0_test_patch"  # value 命中
    final = await run_finalize(projection=projection)

    keys = [(hit.path, hit.marker, hit.kind) for hit in final.scan_result.hits]
    assert keys == sorted(keys)
    assert keys == [
        ("$.branches[0].branch_id", "test_patch", "value"),
        ("$.reward_facts.components.fail_to_pass_bonus", "fail_to_pass", "key"),
    ]


async def test_scan_repeated_runs_identical():
    """同一投影两次扫描结果逐字节一致（sorted 确定性）。"""

    projection = valid_trajectory_projection()
    projection["reward_facts"]["components"] = {"fail_to_pass_bonus": 0.25}
    first = await run_finalize(projection=projection)
    second = await run_finalize(projection=projection)
    assert first.scan_result.model_dump(mode="json") == second.scan_result.model_dump(
        mode="json"
    )


def test_scan_result_clean_flag_must_match_hits():
    """派生结论互检：clean=True 却带命中列表的结果不可表示。"""

    with pytest.raises(ValidationError, match="不一致"):
        ProjectionScanResult.model_validate(
            {
                "trajectory_id": "traj_0001",
                "scanned_schema_id": "rh2.trajectory_projection.v1",
                "hits": [
                    {"path": "$.task_id", "marker": "test_patch", "kind": "value"}
                ],
                "clean": True,
            }
        )


def test_scan_result_rejects_unsorted_hits():
    """乱序命中列表拒收（生产者没走确定性排序路径）。"""

    with pytest.raises(ValidationError, match="升序"):
        ProjectionScanResult.model_validate(
            {
                "trajectory_id": "traj_0001",
                "scanned_schema_id": "rh2.trajectory_projection.v1",
                "hits": [
                    {"path": "$.z_field", "marker": "test_patch", "kind": "value"},
                    {"path": "$.a_field", "marker": "gold_patch", "kind": "value"},
                ],
                "clean": False,
            }
        )


def test_scan_result_clean_evidence_ref_format():
    """干净结果的 evidence 引用串固定格式（报告里"扫过且干净"必须可见）。"""

    result = ProjectionScanResult.model_validate(
        {
            "trajectory_id": "traj_0001",
            "scanned_schema_id": "rh2.trajectory_projection.v1",
            "hits": [],
            "clean": True,
        }
    )
    assert result.evidence_refs() == [
        "public_projection_scan:clean:rh2.trajectory_projection.v1"
    ]
