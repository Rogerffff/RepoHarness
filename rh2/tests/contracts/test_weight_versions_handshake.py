"""WeightVersionsHandshake（preflight §8 H-1，S1-9 落地）的正反测试。

两口径并存：原始 weight_versions list + 派生 max_lag；派生视图互检范式
（声明值必须等于 derive_weight_version_max_lag 重算值）。
"""

import pytest
from contract_samples import valid_trajectory_projection
from pydantic import ValidationError

from repoharness2.contracts import (
    TrajectoryProjection,
    WeightVersionsHandshake,
    derive_weight_version_max_lag,
)

# ---------------------------------------------------------------------------
# 派生函数本体
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("versions", "expected"),
    [
        (["1"], 0),  # 单版本：跨度 0（一条轨迹全程同一权重）
        (["1", "1", "3"], 2),  # 混版本：3-1=2（mid-rollout 权重更新跨两版）
        (["7", "3", "5"], 4),  # 顺序无关：max-min
        (["default"], None),  # 非数值版本：不可派生，绝不猜先后
        (["1", "step_0"], None),  # 任一不可解析即整体不可派生
    ],
)
def test_derive_max_lag(versions, expected):
    assert derive_weight_version_max_lag(versions) == expected


# ---------------------------------------------------------------------------
# 合法形态
# ---------------------------------------------------------------------------


def test_numeric_versions_with_correct_max_lag_pass():
    hs = WeightVersionsHandshake(weight_versions=["1", "1", "3"], max_lag=2)
    assert hs.max_lag == 2 and list(hs.weight_versions) == ["1", "1", "3"]


def test_non_numeric_versions_with_none_max_lag_pass():
    hs = WeightVersionsHandshake(weight_versions=["default"], max_lag=None)
    assert hs.max_lag is None


# ---------------------------------------------------------------------------
# 非法形态（派生视图互检 fail-closed）
# ---------------------------------------------------------------------------


def test_wrong_max_lag_rejected():
    """声明跨度 1、重算跨度 2 -> 拒收（账实不符）。"""
    with pytest.raises(ValidationError, match="派生视图互检失败"):
        WeightVersionsHandshake(weight_versions=["1", "3"], max_lag=1)


def test_numeric_versions_missing_max_lag_rejected():
    """全数值版本却不派生（max_lag=None）-> 拒收：可派生就必须派生。"""
    with pytest.raises(ValidationError, match="派生视图互检失败"):
        WeightVersionsHandshake(weight_versions=["1", "3"], max_lag=None)


def test_non_numeric_versions_with_fabricated_max_lag_rejected():
    """非数值版本配捏造的跨度 -> 拒收：不可派生就必须为 None。"""
    with pytest.raises(ValidationError, match="派生视图互检失败"):
        WeightVersionsHandshake(weight_versions=["default"], max_lag=0)


def test_empty_versions_rejected():
    """空列表不可表示：没有版本事实就不构造本对象（投影层置 None）。"""
    with pytest.raises(ValidationError):
        WeightVersionsHandshake(weight_versions=[], max_lag=None)


# ---------------------------------------------------------------------------
# TrajectoryProjection.handshake 挂点
# ---------------------------------------------------------------------------


def test_projection_carries_handshake_field():
    payload = valid_trajectory_projection()
    payload["handshake"] = {"weight_versions": ["1", "1"], "max_lag": 0}
    projection = TrajectoryProjection.model_validate(payload)
    assert projection.handshake is not None
    assert projection.handshake.max_lag == 0


def test_projection_handshake_defaults_to_none():
    """旧工件（无 handshake 字段）照常通过：字段可选、缺省即"未记账"。"""
    projection = TrajectoryProjection.model_validate(valid_trajectory_projection())
    assert projection.handshake is None


def test_projection_handshake_rejects_inconsistent_derivation():
    payload = valid_trajectory_projection()
    payload["handshake"] = {"weight_versions": ["1", "3"], "max_lag": 9}
    with pytest.raises(ValidationError, match="派生视图互检失败"):
        TrajectoryProjection.model_validate(payload)
