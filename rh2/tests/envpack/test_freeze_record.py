"""frozen_v1 冻结账本单测：在盘记录与源数据互证 + 漂移 fail-closed。"""

import json

import pytest

from repoharness2.contracts._base import canonical_json_digest
from repoharness2.envpack.bundles import FROZEN_V1_FILE, TASKS_FILE, load_bundle_pairs
from repoharness2.envpack.freeze import (
    FrozenRecordMismatch,
    build_frozen_v1,
    load_frozen_v1,
    verify_pairs_against_frozen,
)

EXPECTED_INSTANCE_IDS = [
    "django__django-11099",
    "django__django-11133",
    "django__django-16139",
    "sympy__sympy-14711",
    "sympy__sympy-15349",
    "psf__requests-1142",
    "psf__requests-2931",
    "astropy__astropy-14995",
]


def test_frozen_v1_on_disk_matches_regeneration():
    """在盘 frozen_v1.json == 从源数据确定性重建的结果（生成动作可复现）。"""
    on_disk = json.loads(FROZEN_V1_FILE.read_text())
    rebuilt = build_frozen_v1(TASKS_FILE)
    assert on_disk == rebuilt


def test_frozen_v1_covers_exactly_the_eight_frozen_instances():
    frozen = load_frozen_v1()
    assert [r["instance_id"] for r in frozen["tasks"]] == EXPECTED_INSTANCE_IDS
    assert frozen["meta"]["task_count"] == 8
    # 每条记录五个 digest/引用字段齐全
    for record in frozen["tasks"]:
        assert record["image_manifest_digest"].startswith("sha256:")
        assert record["problem_statement_sha256"].startswith("sha256:")
        assert record["public_bundle_digest"].startswith("sha256:")
        assert record["private_grading_bundle_digest"].startswith("sha256:")
        assert record["image"].startswith("swebench/sweb.eval.x86_64.")


def test_records_digest_self_consistent():
    frozen = load_frozen_v1()
    assert frozen["meta"]["records_digest"] == canonical_json_digest(frozen["tasks"])


def test_default_load_verifies_against_frozen_v1():
    """load_bundle_pairs 默认全量对照 frozen_v1（能返回即校验通过）。"""
    assert len(load_bundle_pairs()) == 8


def test_tampered_record_fails_closed(tmp_path):
    """账本里任何一枚 digest 被改 → FrozenRecordMismatch，指名道姓。"""
    frozen = json.loads(FROZEN_V1_FILE.read_text())
    frozen["tasks"][0]["private_grading_bundle_digest"] = "sha256:" + "f" * 64
    tampered = tmp_path / "frozen_tampered.json"
    tampered.write_text(json.dumps(frozen))
    with pytest.raises(FrozenRecordMismatch, match="django__django-11099.private_grading_bundle_digest"):
        load_bundle_pairs(frozen_file=tampered)


def test_instance_missing_from_ledger_fails_closed(tmp_path):
    frozen = json.loads(FROZEN_V1_FILE.read_text())
    frozen["tasks"] = [r for r in frozen["tasks"] if r["instance_id"] != "sympy__sympy-14711"]
    shrunk = tmp_path / "frozen_shrunk.json"
    shrunk.write_text(json.dumps(frozen))
    with pytest.raises(FrozenRecordMismatch, match="sympy__sympy-14711: 不在 frozen_v1 记录里"):
        load_bundle_pairs(subset=["sympy__sympy-14711"], frozen_file=shrunk)


def test_wrong_schema_id_rejected(tmp_path):
    bogus = tmp_path / "frozen_bogus.json"
    bogus.write_text(json.dumps({"schema_id": "rh2.other.v9", "tasks": []}))
    pairs = load_bundle_pairs(frozen_file=None, subset=["django__django-11099"])
    with pytest.raises(FrozenRecordMismatch, match="schema_id"):
        verify_pairs_against_frozen(pairs, bogus)
