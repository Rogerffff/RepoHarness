"""image_manifest_store 的无网络单测（codex 轮次 7 要求的七类场景）。

被测对象：S2-1 T1b 键控镜像清单的状态机（加载校验 / 双文件事务 / 完成断言）。
所有场景都在 tmp_path 上用合成状态构造，零网络。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repoharness2.taskset.image_manifest_store import (
    EVIDENCE_SCHEMA_ID, MANIFEST_SCHEMA_ID, Store, evidence_id_for,
    evidence_ref_for, finish_assertions, flush_transaction, is_enriched,
    load_state, sha256_bytes,
)
from repoharness2.taskset import image_manifest_store as ims
from repoharness2.taskset.image_manifest_store import migrate_v3_manifest

SURVIVORS = {"repoA__pkg-1", "repoB__pkg-2"}


def expected_ref(iid: str) -> str:
    return f"org/img.{iid.replace('__', '_s_').lower()}:latest"


FROZEN_REFS = {expected_ref(i) for i in SURVIVORS}
REFS_DIGEST = "0" * 64
DIG = "sha256:" + "a" * 64
CFG = "sha256:" + "b" * 64


def make_entry(iid: str) -> dict:
    return {
        "instance_id": iid,
        "source_image_ref": expected_ref(iid),
        "resolved_manifest_digest": DIG,
        "manifest_content_type": "application/vnd.docker.distribution.manifest.v2+json",
        "config_digest": CFG,
        "platform": "linux/amd64",
        "platform_source": "config_blob",
        "registry_evidence_ref": evidence_ref_for(iid),
        "resolved_at": "2026-07-13T00:00:00+00:00",
        "method": "test",
    }


def make_evidence(iid: str) -> dict:
    return {
        "schema_id": EVIDENCE_SCHEMA_ID,
        "evidence_id": evidence_id_for(iid),
        "instance_id": iid,
        "repository": expected_ref(iid).partition(":")[0],
        "manifest_digest": DIG,
        "manifest_content_type": "application/vnd.docker.distribution.manifest.v2+json",
        "config_digest": CFG,
        "config_platform": {"os": "linux", "architecture": "amd64"},
        "config_blob_sha256_verified": True,
        "manifest_blob_sha256_verified": True,
        "fetched_at": "2026-07-13T00:00:00+00:00",
    }


def paths(tmp: Path) -> tuple[Path, Path]:
    return tmp / "image_manifest_keyed.json", tmp / "raw/image_registry_evidence.jsonl"


def write_complete_state(tmp: Path) -> tuple[Path, Path, Store]:
    mp, ep = paths(tmp)
    st = Store()
    for iid in SURVIVORS:
        st.entries[iid] = make_entry(iid)
        st.evidence[iid] = make_evidence(iid)
    flush_transaction(mp, ep, st, REFS_DIGEST)
    return mp, ep, st


def load(mp: Path, ep: Path) -> Store:
    return load_state(mp, ep, SURVIVORS, FROZEN_REFS, REFS_DIGEST, expected_ref)


# ---- 场景 1：旧 digest 损坏必须拒绝 -----------------------------------------

def test_corrupted_digest_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    doc["entries"][0]["resolved_manifest_digest"] = "bad"
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="digest 非法"):
        load(mp, ep)


# ---- 场景 2：多余 / 未知 id 必须拒绝 ----------------------------------------

def test_unknown_entry_id_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    doc["entries"].append({**make_entry("repoA__pkg-1"), "instance_id": "evil__extra-9"})
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="未知 instance_id"):
        load(mp, ep)


def test_extra_evidence_id_rejected(tmp_path: Path):
    mp, ep, st = write_complete_state(tmp_path)
    lines = ep.read_text() + json.dumps({**make_evidence("repoA__pkg-1"),
                                         "instance_id": "ghost__x-1",
                                         "evidence_id": "imgev-ghost__x-1"}) + "\n"
    ep.write_text(lines)
    # evidence 变动会先触发提交记录不符；ghost 行不在已提交集合内且缺已提交行不成立
    # → 走恢复路径丢弃 ghost；再人为同步 header digest 模拟"digest 匹配但有多余行"
    doc = json.loads(mp.read_text())
    doc["header"]["evidence_file_sha256"] = sha256_bytes(ep.read_bytes())
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="manifest 之外的 id|evidence_line_count"):
        load(mp, ep)


def test_duplicate_evidence_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    first = ep.read_text().splitlines()[0]
    ep.write_text(ep.read_text() + first + "\n")
    with pytest.raises(ValueError, match="重复 instance_id"):
        load(mp, ep)


# ---- 场景 3：evidence 缺失 / 事实不一致必须拒绝 ------------------------------

def test_missing_evidence_file_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    ep.unlink()
    with pytest.raises(ValueError, match="evidence 缺失|提交记录"):
        load(mp, ep)


def test_evidence_fact_mismatch_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    lines = [json.loads(x) for x in ep.read_text().splitlines()]
    lines[0]["config_digest"] = "sha256:" + "f" * 64
    payload = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in lines)
    ep.write_text(payload)
    doc = json.loads(mp.read_text())
    doc["header"]["evidence_file_sha256"] = sha256_bytes(payload.encode())
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="交叉核对失败"):
        load(mp, ep)


def test_unverified_blob_hash_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    lines = [json.loads(x) for x in ep.read_text().splitlines()]
    lines[0]["config_blob_sha256_verified"] = False
    payload = "".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in lines)
    ep.write_text(payload)
    doc = json.loads(mp.read_text())
    doc["header"]["evidence_file_sha256"] = sha256_bytes(payload.encode())
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="config blob 哈希未验证"):
        load(mp, ep)


# ---- 场景 4：完整 checkpoint 无操作重跑字节级不变 ----------------------------

def test_noop_rerun_byte_idempotent(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    before_m, before_e = mp.read_bytes(), ep.read_bytes()
    st = load(mp, ep)
    flush_transaction(mp, ep, st, REFS_DIGEST)
    assert mp.read_bytes() == before_m
    assert ep.read_bytes() == before_e


# ---- 场景 5：incomplete checkpoint 正确续跑 ---------------------------------

def test_incomplete_checkpoint_resumes(tmp_path: Path):
    mp, ep = paths(tmp_path)
    st = Store()
    only = sorted(SURVIVORS)[0]
    st.entries[only] = make_entry(only)
    st.evidence[only] = make_evidence(only)
    flush_transaction(mp, ep, st, REFS_DIGEST)
    st2 = load(mp, ep)
    assert is_enriched(st2, only)
    missing = SURVIVORS - set(st2.entries)
    assert missing == {sorted(SURVIVORS)[1]}
    assert finish_assertions(st2, SURVIVORS)  # 未收满 → 完成断言必须报问题


# ---- 场景 6：manifest/evidence 事务中断可恢复 --------------------------------

def test_transaction_interruption_recovers(tmp_path: Path):
    mp, ep = paths(tmp_path)
    st = Store()
    only = sorted(SURVIVORS)[0]
    st.entries[only] = make_entry(only)
    st.evidence[only] = make_evidence(only)
    flush_transaction(mp, ep, st, REFS_DIGEST)
    # 模拟崩溃窗口：evidence 已含第二条（超前），manifest 仍是旧提交记录
    other = sorted(SURVIVORS)[1]
    ep.write_text(ep.read_text()
                  + json.dumps(make_evidence(other), ensure_ascii=False, sort_keys=True) + "\n")
    st2 = load(mp, ep)
    assert st2.recovered_drop == 1          # 未提交行被丢弃
    assert set(st2.evidence) == {only}      # 恢复到提交记录
    assert is_enriched(st2, only)


def test_manifest_claims_but_evidence_behind_rejected(tmp_path: Path):
    # 反方向（manifest 声称 enriched、evidence 缺该行）不可恢复——必须拒绝
    # （v3.1 起 header 机器账目对账先触发，同样是 fail-closed）
    mp, ep, _ = write_complete_state(tmp_path)
    lines = ep.read_text().splitlines()
    payload = lines[0] + "\n"
    ep.write_text(payload)
    doc = json.loads(mp.read_text())
    doc["header"]["evidence_file_sha256"] = sha256_bytes(payload.encode())
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="evidence 缺失|evidence_line_count"):
        load(mp, ep)


# ---- 场景 7：完成状态恰好 N entry + N evidence -------------------------------

def test_finish_assertions_exact_sets(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    st = load(mp, ep)
    assert finish_assertions(st, SURVIVORS) == []
    assert json.loads(mp.read_text())["header"]["schema_id"] == MANIFEST_SCHEMA_ID
    st.evidence.pop(sorted(SURVIVORS)[0])
    assert any("evidence" in p for p in finish_assertions(st, SURVIVORS))


# ---- legacy（v2）迁移：归类为待升级而非 enriched ------------------------------

def test_legacy_v2_state_requires_explicit_migration(tmp_path: Path):
    mp, ep = paths(tmp_path)
    legacy_entries = []
    for iid in SURVIVORS:
        e = make_entry(iid)
        e["registry_evidence_ref"] = f"image_registry_evidence.jsonl#{iid}"  # v2 旧格式
        legacy_entries.append(e)
    ep.parent.mkdir(parents=True, exist_ok=True)
    ep.write_text("")
    mp.write_text(json.dumps({
        "header": {"schema_id": "rh2.s2_1.image_manifest_keyed.v2",
                   "source_refs_file_sha256": REFS_DIGEST},
        "entries": legacy_entries,
    }))
    # v4 起：直接加载必须拒绝（防降级伪装）
    with pytest.raises(ValueError, match="显式迁移"):
        load(mp, ep)
    # 迁移通道：pin 命中 → 归 legacy 待升级，不算 enriched
    pin = sha256_bytes(mp.read_bytes())
    st = migrate_v3_manifest(mp, ep, SURVIVORS, FROZEN_REFS, REFS_DIGEST,
                             expected_ref, pin)
    assert st.legacy_ids == SURVIVORS
    assert all(not is_enriched(st, i) for i in SURVIVORS)


# ---- 轮次 8 回归：已提交行被修改（非交叉核对字段）必须拒绝 --------------------

def test_committed_line_mutation_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    lines = [json.loads(x) for x in ep.read_text().splitlines()]
    lines[0]["fetched_at"] = "1999-01-01T00:00:00+00:00"  # 不在 cross_check 字段内
    ep.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in lines))
    # manifest 保留旧 committed_sha —— codex 轮次 8 的反例形态
    with pytest.raises(ValueError, match="SHA 回验不符"):
        load(mp, ep)


# ---- 轮次 8 回归：manifest 重复 instance_id 必须拒绝 -------------------------

def test_duplicate_manifest_entry_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    doc["entries"].append(dict(doc["entries"][0]))
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="manifest 重复 instance_id"):
        load(mp, ep)


# ---- 轮次 8 回归：header 机器账目被篡改必须拒绝 ------------------------------

@pytest.mark.parametrize("field", ["count", "enriched_count", "evidence_line_count"])
def test_header_counts_tampered_rejected(tmp_path: Path, field: str):
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    doc["header"][field] = 999
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match=field.replace("_", ".")):
        load(mp, ep)


# ---- 轮次 8：evidence 缺 manifest 字节实证 → 归 reverify 而非 enriched --------

def test_missing_manifest_flag_classified_reverify(tmp_path: Path):
    mp, ep = paths(tmp_path)
    st = Store()
    for iid in SURVIVORS:
        st.entries[iid] = make_entry(iid)
        ev = make_evidence(iid)
        del ev["manifest_blob_sha256_verified"]
        st.evidence[iid] = ev
    flush_transaction(mp, ep, st, REFS_DIGEST)
    st2 = load(mp, ep)
    assert st2.reverify_ids == SURVIVORS
    assert all(not is_enriched(st2, i) for i in SURVIVORS)
    assert finish_assertions(st2, SURVIVORS)  # 未全实证 → 不许收口


# ---- 轮次 9 回归：删除任一必填 header 字段必须拒绝（降级绕过封死） ------------

@pytest.mark.parametrize("field", [
    "schema_version", "source_refs_file", "source_refs_file_sha256",
    "evidence_file", "evidence_file_sha256", "evidence_line_count",
    "count", "enriched_count", "reverify_count",
])
def test_v4_required_header_field_deletion_rejected(tmp_path: Path, field: str):
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    del doc["header"][field]
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="缺必填字段|不符|不是合法"):
        load(mp, ep)


def test_v4_evidence_file_path_mismatch_rejected(tmp_path: Path):
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    doc["header"]["evidence_file"] = "elsewhere/evidence.jsonl"
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="evidence_file"):
        load(mp, ep)


def test_v4_delete_commit_sha_then_mutate_evidence_rejected(tmp_path: Path):
    # codex 轮次 9 组合反例：删提交 SHA + 改已提交 evidence → v3.1 接受，v4 必拒
    mp, ep, _ = write_complete_state(tmp_path)
    lines = [json.loads(x) for x in ep.read_text().splitlines()]
    lines[0]["fetched_at"] = "1999-01-01T00:00:00+00:00"
    ep.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in lines))
    doc = json.loads(mp.read_text())
    del doc["header"]["evidence_file_sha256"]
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="缺必填字段 evidence_file_sha256"):
        load(mp, ep)


def test_v4_downgrade_to_v3_schema_rejected(tmp_path: Path):
    # 删版本标记/伪装旧 schema 不再是降级通道：v3 只能显式迁移
    mp, ep, _ = write_complete_state(tmp_path)
    doc = json.loads(mp.read_text())
    doc["header"]["schema_id"] = "rh2.s2_1.image_manifest_keyed.v3"
    mp.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="显式迁移"):
        load(mp, ep)


# ---- 轮次 9：显式迁移的 digest pin --------------------------------------------

def _write_legacy_v3_state(tmp_path: Path) -> tuple[Path, Path]:
    mp, ep = paths(tmp_path)
    entries = [make_entry(i) for i in sorted(SURVIVORS)]
    ev_lines = {i: make_evidence(i) for i in sorted(SURVIVORS)}
    payload = "".join(json.dumps(ev_lines[k], ensure_ascii=False, sort_keys=True) + "\n"
                      for k in sorted(ev_lines))
    ep.parent.mkdir(parents=True, exist_ok=True)
    ep.write_text(payload)
    mp.write_text(json.dumps({
        "header": {"schema_id": "rh2.s2_1.image_manifest_keyed.v3",
                   "schema_version": 3,
                   "source_refs_file_sha256": REFS_DIGEST,
                   "evidence_file_sha256": sha256_bytes(payload.encode())},
        "entries": entries,
    }))
    return mp, ep


def test_migration_requires_correct_pin(tmp_path: Path):
    mp, ep = _write_legacy_v3_state(tmp_path)
    with pytest.raises(ValueError, match="只迁移已知产物"):
        migrate_v3_manifest(mp, ep, SURVIVORS, FROZEN_REFS, REFS_DIGEST,
                            expected_ref, "0" * 64)


def test_migration_with_pin_then_v4_roundtrip(tmp_path: Path):
    mp, ep = _write_legacy_v3_state(tmp_path)
    pin = sha256_bytes(mp.read_bytes())
    st = migrate_v3_manifest(mp, ep, SURVIVORS, FROZEN_REFS, REFS_DIGEST,
                             expected_ref, pin)
    flush_transaction(mp, ep, st, REFS_DIGEST)
    st2 = load(mp, ep)  # 迁移后必须能被严格 v4 加载
    assert finish_assertions(st2, SURVIVORS) == []
