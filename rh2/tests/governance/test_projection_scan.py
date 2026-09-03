"""projection 扫描（D2-4 起为**冻结兼容读路径**）：算法与 schema 不变，但不再进 finalize 关口。

前置清理批（决策包 D2+B v2，owner 2026-09-04 已批）之前，本文件全部经 finalize_rollout 驱动、
断言 marker 命中 → security 维失败 → audit 档。D2-4 删除了这条资格语义（TrajectoryProjection
不是模型可见面，字段名命中只会误报丢整组），所以：

- 冻结实现 `_scan_public_projection` 的确定性（命中、排序、重复运行一致）在本文件直接调用
  验证——它不再有生产调用方，这是它唯一的被测入口；
- 关口级断言反转：同一个 `fail_to_pass_bonus` 投影经 finalize_rollout 仍 online，产物没有
  `scan_result`，security 维没有扫描 evidence；
- `ProjectionScanResult` 自身的校验器（clean/hits 互检、排序、evidence 格式）原样保留。
真模型可见面的 marker 扫描仍是拒绝面，测试在 tests/envpack 与 tests/test_w1b_prepared_tasks.py。
"""

from __future__ import annotations

import pytest
from contract_samples import valid_trajectory_projection
from governance_samples import run_finalize
from pydantic import ValidationError

from repoharness2.contracts import TrajectoryProjection
from repoharness2.governance import FinalizedRollout, ProjectionScanResult
from repoharness2.governance.projection_scan import _scan_public_projection  # 冻结实现，仅本测试直接调


def _projection_with_marker_hit() -> dict:
    projection = valid_trajectory_projection()
    projection["reward_facts"]["components"] = {"fail_to_pass_bonus": 0.25}
    return projection


def _scan(payload: dict) -> ProjectionScanResult:
    return _scan_public_projection(TrajectoryProjection.model_validate(payload))


# ---------------------------------------------------------------------------
# 关口：marker 命中不再影响资格
# ---------------------------------------------------------------------------


async def test_marker_hit_in_projection_no_longer_affects_eligibility():
    """D2-4 反转断言：reward components 里的 `fail_to_pass_bonus` 字段名曾让整组落 audit；
    现在同一投影 online、security 维通过、没有 `public_projection_marker_hit`。"""

    final = await run_finalize(projection=_projection_with_marker_hit())
    report = final.eligibility_report
    assert report.eligibility_class == "online_policy_loss_eligible"
    assert report.reason_codes == []
    fact = report.facts.security_and_leakage
    assert fact.ok is True and "public_projection_marker_hit" not in fact.reason_codes
    assert not any("public_projection_scan" in ref for ref in fact.evidence_refs)
    assert final.group_repair_signal.degraded is False
    assert "scan_result" not in FinalizedRollout.model_fields and not hasattr(final, "scan_result")


async def test_clean_projection_leaves_no_scan_evidence_either():
    final = await run_finalize()
    fact = final.eligibility_report.facts.security_and_leakage
    assert fact.ok is True
    assert not any("public_projection_scan" in ref for ref in fact.evidence_refs)


# ---------------------------------------------------------------------------
# 冻结实现：确定性不变（供历史 artifact 重算）
# ---------------------------------------------------------------------------


def test_frozen_scan_detects_key_hit_with_stable_shape():
    scan = _scan(_projection_with_marker_hit())
    assert scan.clean is False and scan.trajectory_id == "traj_0001"
    assert scan.scanned_schema_id == "rh2.trajectory_projection.v1"
    (hit,) = scan.hits
    assert (hit.path, hit.marker, hit.kind) == ("$.reward_facts.components.fail_to_pass_bonus", "fail_to_pass", "key")
    assert scan.evidence_refs() == ["public_projection_scan:hit:$.reward_facts.components.fail_to_pass_bonus:fail_to_pass:key"]


def test_frozen_scan_clean_projection():
    scan = _scan(valid_trajectory_projection())
    assert scan.clean is True and scan.hits == []


def test_frozen_scan_multiple_hits_sorted_deterministically():
    projection = _projection_with_marker_hit()
    projection["branches"][0]["branch_id"] = "b0_test_patch"  # value 命中
    keys = [(hit.path, hit.marker, hit.kind) for hit in _scan(projection).hits]
    assert keys == sorted(keys)
    assert keys == [
        ("$.branches[0].branch_id", "test_patch", "value"),
        ("$.reward_facts.components.fail_to_pass_bonus", "fail_to_pass", "key"),
    ]


def test_frozen_scan_repeated_runs_identical():
    projection = _projection_with_marker_hit()
    assert _scan(projection).model_dump(mode="json") == _scan(projection).model_dump(mode="json")


# ---------------------------------------------------------------------------
# 冻结 schema 校验器原样
# ---------------------------------------------------------------------------


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
    """干净结果的 evidence 引用串固定格式（历史报告里的留痕格式不变）。"""

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
