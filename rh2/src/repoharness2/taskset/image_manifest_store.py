"""S2-1 键控镜像清单的状态存储：加载校验 / 事务写 / 完成断言（纯逻辑，零网络）。

演进史（codex 轮次 7~9 审查驱动，存档 s2/codex_reviews.md）：
  v3   轮次 7：manifest↔evidence 引用完整性、双文件事务（evidence 先写、
       manifest 为提交记录）、evidence_ref 修正 + config blob 哈希实证。
  v3.1 轮次 8：事务恢复对已提交集合做规范化重序列化 SHA 回验、manifest
       重复 id 拒绝、header 机器账目对账、manifest 原始字节哈希实证。
  v4   轮次 9：**严格性不再可被"删字段"关闭**——v3.1 把严格对账挂在可选
       字段上（删掉 evidence_file_sha256 / reverify_count / source_refs_
       file_sha256 或改 evidence_file 路径即可降级绕过，fail-open）。v4 是
       显式新 schema：全部 header 字段必填必验；旧 v2/v3 产物只能通过
       `migrate_v3_manifest`（调用方提供旧文件 sha256 pin，只接受已知产物）
       一次性显式迁移并立即重写为 v4；`load_state` 只认 v4。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_SCHEMA_ID = "rh2.s2_1.image_manifest_keyed.v4"
MANIFEST_SCHEMA_VERSION = 4
MIGRATABLE_SCHEMA_IDS = {
    "rh2.s2_1.image_manifest_keyed.v2",
    "rh2.s2_1.image_manifest_keyed.v3",
}
EVIDENCE_SCHEMA_ID = "rh2.s2_1.image_registry_evidence.v1"
EVIDENCE_RELPATH = "raw/image_registry_evidence.jsonl"
SOURCE_REFS_RELPATH = "data_freeze/meta/image_refs_swegym.txt"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ENTRY_REQUIRED = ("manifest_content_type", "resolved_at", "method")
# entry ↔ evidence 必须逐字段一致的事实面
CROSS_FIELDS = (
    ("resolved_manifest_digest", "manifest_digest"),
    ("config_digest", "config_digest"),
    ("manifest_content_type", "manifest_content_type"),
)


def evidence_id_for(iid: str) -> str:
    return f"imgev-{iid}"


def evidence_ref_for(iid: str) -> str:
    return f"{EVIDENCE_RELPATH}#{evidence_id_for(iid)}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Store:
    """内存态：entries 按 instance_id 键控；evidence 同键。"""

    entries: dict[str, dict] = field(default_factory=dict)
    evidence: dict[str, dict] = field(default_factory=dict)
    legacy_ids: set[str] = field(default_factory=set)   # v2 旧条目：blob 补验通道（零限额）
    reverify_ids: set[str] = field(default_factory=set)  # 缺 manifest 字节实证：manifest GET 复验通道（计限额）
    recovered_drop: int = 0  # 事务恢复时丢弃的未提交 evidence 行数
    migrated_dropped_evidence: int = 0  # 显式迁移时丢弃的旧格式 evidence 行数（仅迁移路径允许丢弃）


def validate_entry(e: dict, survivors: set[str], frozen_refs: set[str],
                   expected_ref) -> list[str]:
    problems: list[str] = []
    iid = e.get("instance_id", "")
    if iid not in survivors:
        return [f"未知 instance_id: {iid!r}"]
    if e.get("source_image_ref") != expected_ref(iid) or e["source_image_ref"] not in frozen_refs:
        problems.append(f"{iid}: source_image_ref 非法")
    if not DIGEST_RE.match(e.get("resolved_manifest_digest", "") or ""):
        problems.append(f"{iid}: manifest digest 非法")
    for f in ENTRY_REQUIRED:
        if not e.get(f):
            problems.append(f"{iid}: 缺字段 {f}")
    return problems


def entry_shape_enriched(e: dict) -> bool:
    """entry 自身字段形状是否声称 enriched（不含 evidence 交叉核对）。"""
    return (
        DIGEST_RE.match(e.get("config_digest", "") or "") is not None
        and e.get("platform") == "linux/amd64"
        and e.get("platform_source") == "config_blob"
        and e.get("registry_evidence_ref") == evidence_ref_for(e.get("instance_id", ""))
    )


def cross_check(e: dict, ev: dict) -> list[str]:
    iid = e.get("instance_id", "")
    problems: list[str] = []
    if ev.get("schema_id") != EVIDENCE_SCHEMA_ID:
        problems.append(f"{iid}: evidence schema_id 非法: {ev.get('schema_id')!r}")
    if ev.get("evidence_id") != evidence_id_for(iid):
        problems.append(f"{iid}: evidence_id 不符")
    for ef, vf in CROSS_FIELDS:
        if e.get(ef) != ev.get(vf):
            problems.append(f"{iid}: entry.{ef} 与 evidence.{vf} 不一致")
    repo = e.get("source_image_ref", "").partition(":")[0]
    if ev.get("repository") != repo:
        problems.append(f"{iid}: evidence.repository 不符")
    plat = ev.get("config_platform") or {}
    if (plat.get("os"), plat.get("architecture")) != ("linux", "amd64"):
        problems.append(f"{iid}: evidence 平台事实非 linux/amd64: {plat}")
    if ev.get("config_blob_sha256_verified") is not True:
        problems.append(f"{iid}: config blob 哈希未验证")
    return problems


def fully_verified(e: dict, ev: dict) -> bool:
    """完整实证 = core 交叉核对通过 ∧ manifest 原始字节哈希已验（轮次 8 补强）。"""
    return not cross_check(e, ev) and ev.get("manifest_blob_sha256_verified") is True


def _canonical_evidence_payload(evidence: dict[str, dict]) -> bytes:
    return "".join(
        json.dumps(evidence[k], ensure_ascii=False, sort_keys=True) + "\n"
        for k in sorted(evidence)
    ).encode("utf-8")


def _parse_entries(doc: dict, survivors: set[str], frozen_refs: set[str],
                   expected_ref) -> tuple[dict[str, dict], int]:
    entries: dict[str, dict] = {}
    problems: list[str] = []
    raw_count = 0
    for e in doc.get("entries", []):
        raw_count += 1
        iid = e.get("instance_id", "")
        if iid in entries:
            raise ValueError(f"manifest 重复 instance_id: {iid}")  # 轮次 8 问题 2
        problems.extend(validate_entry(e, survivors, frozen_refs, expected_ref))
        entries[iid] = e
    if problems:
        raise ValueError("manifest entries 校验不过，拒绝续跑：\n  " + "\n  ".join(problems[:10]))
    return entries, raw_count


def _parse_evidence(evidence_path: Path) -> dict[str, dict]:
    raw_lines: dict[str, dict] = {}
    if evidence_path.exists():
        for line in evidence_path.read_text().splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            iid = ev.get("instance_id", "")
            if iid in raw_lines:
                raise ValueError(f"evidence 重复 instance_id: {iid}")
            raw_lines[iid] = ev
    return raw_lines


def _recover_transaction(entries: dict[str, dict], raw_lines: dict[str, dict],
                         committed_sha: str, evidence_path: Path) -> int:
    """提交记录回验（轮次 8 问题 1）：已提交集合规范化重序列化 SHA 必须命中；
    唯一可恢复方向 = evidence 超前（已提交行逐字节原样 + 纯追加）。返回丢弃行数。"""
    actual = sha256_bytes(evidence_path.read_bytes())
    if actual == committed_sha:
        return 0
    claimed = {i for i, e in entries.items() if entry_shape_enriched(e)}
    if not claimed <= set(raw_lines):
        raise ValueError("evidence 与提交记录不符且缺已提交行——不可恢复，拒绝")
    committed_payload = _canonical_evidence_payload({i: raw_lines[i] for i in claimed})
    if sha256_bytes(committed_payload) != committed_sha:
        raise ValueError("evidence 已提交行与提交记录 SHA 回验不符（已提交内容被修改）——拒绝")
    extras = set(raw_lines) - claimed
    for x in extras:
        raw_lines.pop(x)
    return len(extras)


def _classify(st: Store, raw_lines: dict[str, dict], legacy_tolerant: bool) -> int:
    """逐 entry 分类（enriched 需 evidence 交叉一致）；返回 fully-verified 数。"""
    n_fully = 0
    for iid, e in st.entries.items():
        if entry_shape_enriched(e):
            ev = raw_lines.get(iid)
            if ev is None:
                raise ValueError(f"{iid}: entry 声称 enriched 但 evidence 缺失——拒绝")
            errs = cross_check(e, ev)
            if errs:
                raise ValueError("entry↔evidence 交叉核对失败：\n  " + "\n  ".join(errs[:6]))
            st.evidence[iid] = ev
            if ev.get("manifest_blob_sha256_verified") is True:
                n_fully += 1
            else:
                st.reverify_ids.add(iid)
        elif legacy_tolerant and e.get("config_digest"):
            # v2 legacy：digest 事实在 entries；旧格式 evidence 不保留（升级通道重建）
            st.legacy_ids.add(iid)
        # 其余 = digest-only（v1 形态），走完整富化
    extra_ev = set(raw_lines) - set(st.entries)
    if extra_ev:
        raise ValueError(f"evidence 含 manifest 之外的 id（{len(extra_ev)} 条）——拒绝")
    return n_fully


def load_state(manifest_path: Path, evidence_path: Path, survivors: set[str],
               frozen_refs: set[str], refs_digest: str, expected_ref) -> Store:
    """严格 v4 加载：全部 header 字段必填必验，缺任一即拒（fail-closed）。

    轮次 9 修复核心：严格性不可被"删字段"降级——v2/v3 产物不被直接加载，
    报错指向 `migrate_v3_manifest` 显式迁移。
    """
    st = Store()
    if not manifest_path.exists():
        if evidence_path.exists():
            raise ValueError("evidence 存在而 manifest 不存在——无提交记录，拒绝加载（先人工裁决）")
        return st

    doc = json.loads(manifest_path.read_text())
    hdr = doc.get("header", {})
    schema = hdr.get("schema_id")
    if schema in MIGRATABLE_SCHEMA_IDS:
        raise ValueError(
            f"旧 schema {schema!r} 不再被直接加载（防降级伪装）——"
            "用 migrate_v3_manifest 提供旧文件 sha256 pin 做一次性显式迁移")
    if schema != MANIFEST_SCHEMA_ID:
        raise ValueError(f"manifest schema_id 不认识: {schema!r}")

    def _req(fld: str):
        if fld not in hdr or hdr[fld] is None:
            raise ValueError(f"v4 header 缺必填字段 {fld}——拒绝（严格性不可被删字段关闭）")
        return hdr[fld]

    if _req("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"schema_version={hdr['schema_version']} != {MANIFEST_SCHEMA_VERSION}")
    if _req("source_refs_file") != SOURCE_REFS_RELPATH:
        raise ValueError(f"source_refs_file={hdr['source_refs_file']!r} 与固定路径不符")
    if _req("source_refs_file_sha256") != refs_digest:
        raise ValueError("header 的 refs 文件 digest 与当前冻结清单不符（数据面变动？）")
    if _req("evidence_file") != EVIDENCE_RELPATH:
        raise ValueError(f"evidence_file={hdr['evidence_file']!r} 与固定路径不符")
    committed_sha = str(_req("evidence_file_sha256"))
    if not SHA256_RE.match(committed_sha):
        raise ValueError("evidence_file_sha256 不是合法 sha256")
    for fld in ("evidence_line_count", "count", "enriched_count", "reverify_count"):
        v = _req(fld)
        # type(v) is int：显式排除 bool（bool 是 int 子类，True==1 会骗过 ==）
        # 与 float（216.0==216 同理）——轮次 10 问题 3。
        if type(v) is not int or v < 0:
            raise ValueError(f"header.{fld}={v!r} 不是非负 int（严格类型校验）")
    if not (hdr["enriched_count"] + hdr["reverify_count"]
            <= hdr["evidence_line_count"] <= hdr["count"]):
        raise ValueError(
            f"header 计数链不一致：enriched {hdr['enriched_count']} + reverify "
            f"{hdr['reverify_count']} <= evidence {hdr['evidence_line_count']} <= count {hdr['count']} 不成立")

    st.entries, raw_entry_count = _parse_entries(doc, survivors, frozen_refs, expected_ref)
    if not evidence_path.exists():
        raise ValueError("提交记录存在但 evidence 文件缺失——不可恢复，拒绝")
    raw_lines = _parse_evidence(evidence_path)
    st.recovered_drop = _recover_transaction(st.entries, raw_lines, committed_sha, evidence_path)

    if hdr["count"] != raw_entry_count:
        raise ValueError(f"header.count={hdr['count']} 与 entries 实际 {raw_entry_count} 不符")
    if hdr["evidence_line_count"] != len(raw_lines):
        raise ValueError(
            f"header.evidence_line_count={hdr['evidence_line_count']} 与已提交 evidence {len(raw_lines)} 不符")

    n_fully = _classify(st, raw_lines, legacy_tolerant=False)
    unconsumed = set(raw_lines) - set(st.evidence)
    if unconsumed:
        raise ValueError(
            f"evidence 存在无归属行（对应 entry 非 enriched 形状，{len(unconsumed)} 条，"
            f"如 {sorted(unconsumed)[:3]}）——严格加载拒绝（writer 状态必须无损往返）")
    if hdr["enriched_count"] != n_fully:
        raise ValueError(f"header.enriched_count={hdr['enriched_count']} 与实际 fully-verified {n_fully} 不符")
    if hdr["reverify_count"] != len(st.reverify_ids):
        raise ValueError(f"header.reverify_count={hdr['reverify_count']} 与实际 {len(st.reverify_ids)} 不符")
    return st


def migrate_v3_manifest(manifest_path: Path, evidence_path: Path, survivors: set[str],
                        frozen_refs: set[str], refs_digest: str, expected_ref,
                        expected_manifest_sha256: str,
                        expected_evidence_sha256: str) -> Store:
    """一次性显式迁移：manifest 与 evidence **双 sha256 pin** 都命中才接受
    （轮次 10 问题 2：只 pin manifest 时，无内嵌提交 SHA 的旧产物可被换 evidence）。

    旧 header 内嵌 evidence SHA 时与调用方 pin 互检。旧格式 evidence 的丢弃
    只允许发生在本路径，数量记入 `Store.migrated_dropped_evidence`。调用方拿到
    Store 后必须立即 `flush_transaction` 重写为 v4。
    """
    if not manifest_path.exists():
        raise ValueError("迁移目标 manifest 不存在")
    actual = sha256_bytes(manifest_path.read_bytes())
    if actual != expected_manifest_sha256:
        raise ValueError(
            f"旧产物 digest 不符（actual {actual[:16]}… != pin {expected_manifest_sha256[:16]}…）"
            "——只迁移已知产物，拒绝")
    ev_actual = sha256_bytes(evidence_path.read_bytes()) if evidence_path.exists() else sha256_bytes(b"")
    if ev_actual != expected_evidence_sha256:
        raise ValueError(
            f"旧 evidence digest 不符（actual {ev_actual[:16]}… != pin "
            f"{expected_evidence_sha256[:16]}…）——只迁移已知产物，拒绝")
    doc = json.loads(manifest_path.read_text())
    hdr = doc.get("header", {})
    if hdr.get("schema_id") not in MIGRATABLE_SCHEMA_IDS:
        raise ValueError(f"schema {hdr.get('schema_id')!r} 不在可迁移集合 {sorted(MIGRATABLE_SCHEMA_IDS)}")
    if hdr.get("source_refs_file_sha256") not in (None, refs_digest):
        raise ValueError("旧 header 的 refs 文件 digest 与当前冻结清单不符")
    embedded = hdr.get("evidence_file_sha256")
    if embedded is not None and embedded != expected_evidence_sha256:
        raise ValueError("旧 header 内嵌 evidence SHA 与调用方 pin 不符——互检失败，拒绝")

    st = Store()
    st.entries, _ = _parse_entries(doc, survivors, frozen_refs, expected_ref)
    raw_lines = _parse_evidence(evidence_path)
    committed_sha = hdr.get("evidence_file_sha256")
    if committed_sha is not None and evidence_path.exists():
        st.recovered_drop = _recover_transaction(st.entries, raw_lines, committed_sha, evidence_path)
    _classify(st, raw_lines, legacy_tolerant=True)
    st.migrated_dropped_evidence = len(set(raw_lines) - set(st.evidence))
    return st


def is_enriched(st: Store, iid: str) -> bool:
    e = st.entries.get(iid)
    if e is None or iid in st.legacy_ids or iid in st.reverify_ids or not entry_shape_enriched(e):
        return False
    ev = st.evidence.get(iid)
    return ev is not None and fully_verified(e, ev)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def flush_transaction(manifest_path: Path, evidence_path: Path, st: Store,
                      refs_digest: str) -> None:
    """事务序：evidence 先落盘 → digest/行数进 header → manifest 最后作为提交记录。"""
    for iid, ev in st.evidence.items():
        e = st.entries.get(iid)
        if e is None or not entry_shape_enriched(e):
            raise ValueError(f"{iid}: evidence 无归属（entry 缺失或非 enriched 形状）——拒绝写盘")
        errs = cross_check(e, ev)
        if errs:
            raise ValueError("写盘前 entry↔evidence 交叉核对失败：\n  " + "\n  ".join(errs[:6]))
    ev_payload = _canonical_evidence_payload(st.evidence)
    _atomic_write(evidence_path, ev_payload)
    enriched = sum(1 for k in st.entries if is_enriched(st, k))
    reverify = sum(
        1 for k in st.entries
        if entry_shape_enriched(st.entries[k]) and not is_enriched(st, k)
    )
    doc = {
        "header": {
            "schema_id": MANIFEST_SCHEMA_ID,
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "purpose": "S2-1 T1b 键控镜像清单：216 survivor 的稳定镜像身份 + 实证平台",
            "source_refs_file": SOURCE_REFS_RELPATH,
            "source_refs_file_sha256": refs_digest,
            "evidence_file": EVIDENCE_RELPATH,
            "evidence_file_sha256": sha256_bytes(ev_payload),
            "evidence_line_count": len(st.evidence),
            "count": len(st.entries),
            "enriched_count": enriched,
            "reverify_count": reverify,
        },
        "entries": [st.entries[k] for k in sorted(st.entries)],
    }
    payload = (json.dumps(doc, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    _atomic_write(manifest_path, payload)


def finish_assertions(st: Store, survivors: set[str]) -> list[str]:
    problems: list[str] = []
    if set(st.entries) != survivors:
        problems.append(f"entries {len(st.entries)} 与 survivors {len(survivors)} 集合不等")
    if set(st.evidence) != survivors:
        problems.append(f"evidence {len(st.evidence)} 与 survivors {len(survivors)} 集合不等")
    not_enriched = [k for k in st.entries if not is_enriched(st, k)]
    if not_enriched:
        problems.append(f"{len(not_enriched)} 条未 enriched: {sorted(not_enriched)[:5]}")
    return problems
