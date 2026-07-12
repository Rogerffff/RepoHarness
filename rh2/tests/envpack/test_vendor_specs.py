"""vendor spec 资产的机器复算测试（codex 轮次 12 一般 4）。

把 T2-a 报告里的数字变成可重算断言：冻结 raw archive、216 survivor、
vendor JSON 任一变化都会在此直接红灯，而不是只留报告文字。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoharness2.envpack.spec_vendor import (
    SPEC_VENDOR_ID_SWEGYM_242429C1,
    VendorSpecError,
    derive_eval_cmd,
    load_vendor_specs,
    lookup_spec,
    vendor_pin,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
RAW = DOCS / "s2/raw/swe_gym_lite_full_f70b1a29.jsonl"
SURVIVORS_FILE = DOCS / "data_freeze/labels/static_gate_survivors.txt"


@pytest.fixture(scope="module")
def specs():
    return load_vendor_specs(SPEC_VENDOR_ID_SWEGYM_242429C1)


@pytest.fixture(scope="module")
def survivor_rows():
    survivors = {
        s.strip() for s in SURVIVORS_FILE.read_text().splitlines() if s.strip()
    }
    rows = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    picked = [r for r in rows if r["instance_id"] in survivors]
    assert len(picked) == 216
    return picked


def test_vendor_json_digest_matches_pin(specs):
    # load_vendor_specs 内部已核对 digest；本测试确保加载路径真的走到（非空）
    assert specs, "vendor specs 不应为空"
    pin = vendor_pin(SPEC_VENDOR_ID_SWEGYM_242429C1)
    assert pin.source_commit == "242429c188fcfd06aad13fce9a54d450470bf0ac"


def test_vendor_totals_recomputed(specs):
    assert len(specs) == 33, "仓库数应为 33（T2-a 实测）"
    assert sum(len(v) for v in specs.values()) == 808, "spec 对总数应为 808"


def test_all_vendor_repo_keys_lowercase(specs):
    assert all(k == k.lower() for k in specs), "最终表必须全小写键（fork 末行重绑定语义）"


def test_216_survivors_fully_covered(specs, survivor_rows):
    missing = [
        (r["instance_id"], r["repo"], r["version"])
        for r in survivor_rows
        if r["version"] not in specs.get(r["repo"].lower(), {})
    ]
    assert missing == [], f"survivor spec 缺失: {missing[:5]}"


def test_derive_eval_cmd_for_every_survivor(specs, survivor_rows):
    for r in survivor_rows:
        cmd = derive_eval_cmd(
            SPEC_VENDOR_ID_SWEGYM_242429C1, r["repo"].lower(), r["version"]
        )
        assert cmd.strip(), f"{r['instance_id']}: 空 test_cmd"


def test_lookup_rejects_uppercase_key():
    with pytest.raises(VendorSpecError, match="未小写化"):
        lookup_spec(SPEC_VENDOR_ID_SWEGYM_242429C1, "Project-MONAI/MONAI", "1.0")


def test_official_swebench_covers_zero_of_216(survivor_rows):
    swebench_constants = pytest.importorskip(
        "swebench.harness.constants",
        reason="official swebench 未安装（swe 依赖组），跳过官方零覆盖复算",
    )
    official = swebench_constants.MAP_REPO_VERSION_TO_SPECS
    covered = [
        r["instance_id"]
        for r in survivor_rows
        if r["version"] in official.get(r["repo"], {})
        or r["version"] in official.get(r["repo"].lower(), {})
    ]
    assert covered == [], f"官方表意外覆盖: {covered[:5]}（风险 F 前提变化，需复核）"
