"""S2-1 键控镜像清单的状态存储：加载校验 / 事务写 / 完成断言（纯逻辑，零网络）。

从 `rh2/experiments/s2_1_ingestion/resolve_image_digests.py` 抽出（codex 轮次 7：
数据脚本的状态机必须可单测），修复该轮指出的三个缺口：

1. **manifest ↔ evidence 引用完整性**：`is_enriched` 只看 entry 字段形状；
   真正的 enriched 判定发生在 `load_state` / `finish_assertions`——逐 entry
   交叉核对 evidence 行（manifest/config digest、repository、content type、
   platform、evidence_id），evidence 不得有多余/重复 id。
2. **双文件事务**：`flush_transaction` 先原子写 evidence → 计算其 sha256 +
   行数写进 manifest header → 最后原子写 manifest（manifest = 提交记录）。
   崩溃只可能留下"evidence 超前于 manifest"的状态，`load_state` 按提交记录
   恢复（丢弃未提交的 evidence 行并告警），反方向（manifest 声称而 evidence
   缺失/不符）一律拒绝。
3. **引用路径**：`registry_evidence_ref = raw/image_registry_evidence.jsonl#<evidence_id>`
   （相对 manifest 所在目录可解析；evidence 行带稳定 `evidence_id` 与 schema_id）。

legacy 迁移：v2 产物（旧 ref 格式、evidence 无 schema_id、未验 config blob
哈希）加载时归类为 `legacy`——digest 事实保留，但不算 enriched，由脚本的
升级通道（仅 blob GET，不计 pull 限额）补验后升格。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_SCHEMA_ID = "rh2.s2_1.image_manifest_keyed.v3"
LEGACY_MANIFEST_SCHEMA_IDS = {"rh2.s2_1.image_manifest_keyed.v2"}
EVIDENCE_SCHEMA_ID = "rh2.s2_1.image_registry_evidence.v1"
EVIDENCE_RELPATH = "raw/image_registry_evidence.jsonl"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

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
    reverify_ids: set[str] = field(default_factory=set)  # evidence 缺 manifest 字节实证：manifest GET 复验通道（计限额）
    recovered_drop: int = 0  # 事务恢复时丢弃的未提交 evidence 行数


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
    """完整实证 = core 交叉核对通过 ∧ manifest 原始字节哈希已验（codex 轮次 8 补强）。"""
    return not cross_check(e, ev) and ev.get("manifest_blob_sha256_verified") is True


def load_state(manifest_path: Path, evidence_path: Path, survivors: set[str],
               frozen_refs: set[str], refs_digest: str, expected_ref) -> Store:
    """fail-closed 加载；唯一允许的降级 = 事务恢复（evidence 超前）与 legacy 归类。"""
    st = Store()
    if not manifest_path.exists():
        if evidence_path.exists():
            raise ValueError("evidence 存在而 manifest 不存在——无提交记录，拒绝加载（先人工裁决）")
        return st

    doc = json.loads(manifest_path.read_text())
    hdr = doc.get("header", {})
    schema = hdr.get("schema_id")
    legacy_manifest = schema in LEGACY_MANIFEST_SCHEMA_IDS
    if schema != MANIFEST_SCHEMA_ID and not legacy_manifest:
        raise ValueError(f"manifest schema_id 不认识: {schema!r}")
    if hdr.get("source_refs_file_sha256") not in (None, refs_digest):
        raise ValueError("header 的 refs 文件 digest 与当前冻结清单不符（数据面变动？）")

    problems: list[str] = []
    raw_entry_count = 0
    for e in doc.get("entries", []):
        raw_entry_count += 1
        iid = e.get("instance_id", "")
        if iid in st.entries:
            raise ValueError(f"manifest 重复 instance_id: {iid}")  # codex 轮次 8 问题 2
        problems.extend(validate_entry(e, survivors, frozen_refs, expected_ref))
        st.entries[iid] = e
    if problems:
        raise ValueError("manifest entries 校验不过，拒绝续跑：\n  " + "\n  ".join(problems[:10]))

    # evidence 读入（重复 id 即拒）
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

    # 事务恢复判定：header 记录的 evidence digest 是提交记录。
    committed_sha = hdr.get("evidence_file_sha256")
    claimed = {i for i, e in st.entries.items() if entry_shape_enriched(e)}
    if committed_sha is not None and not evidence_path.exists():
        raise ValueError("提交记录存在但 evidence 文件缺失——不可恢复，拒绝")
    if committed_sha is not None and evidence_path.exists():
        actual = sha256_bytes(evidence_path.read_bytes())
        if actual != committed_sha:
            # 唯一可恢复方向：evidence 超前 = 已提交行**逐字节原样**存在 + 若干
            # 未提交新行。已提交集合按 flush 同规则规范化重序列化后回验 SHA
            # ——已提交行的任何字段变更（含 cross_check 之外的字段，如
            # fetched_at）都会使回验失败而被拒绝（codex 轮次 8 问题 1）。
            if not claimed <= set(raw_lines):
                raise ValueError("evidence 与提交记录不符且缺已提交行——不可恢复，拒绝")
            committed_payload = _canonical_evidence_payload({i: raw_lines[i] for i in claimed})
            if sha256_bytes(committed_payload) != committed_sha:
                raise ValueError("evidence 已提交行与提交记录 SHA 回验不符（已提交内容被修改）——拒绝")
            extras = set(raw_lines) - claimed
            for x in extras:
                raw_lines.pop(x)
            st.recovered_drop = len(extras)

    # header 机器账目对账（codex 轮次 8 问题 3；legacy v2 header 无这些字段则跳过）
    if hdr.get("count") is not None and hdr["count"] != raw_entry_count:
        raise ValueError(f"header.count={hdr['count']} 与 entries 实际 {raw_entry_count} 不符")
    if hdr.get("evidence_line_count") is not None and hdr["evidence_line_count"] != len(raw_lines):
        raise ValueError(
            f"header.evidence_line_count={hdr['evidence_line_count']} 与已提交 evidence {len(raw_lines)} 不符")

    # 逐 entry 分类：fully-verified / reverify（缺 manifest 字节实证）/ legacy / digest-only
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
                st.reverify_ids.add(iid)  # manifest GET 复验通道（计限额）
        elif legacy_manifest or e.get("config_digest"):
            # v2 legacy：digest 事实在 entries 里；旧格式 evidence 不保留
            # （升级通道从 blob 重建，事实无损）
            st.legacy_ids.add(iid)
        # 其余 = digest-only（v1 形态），走完整富化
    # enriched_count 严格对账只对 v3.1+ 文件（带 reverify_count 标记）执行；
    # v3.0 文件的 enriched_count 是"cross-check 通过"旧口径，一次性迁移时跳过。
    if hdr.get("reverify_count") is not None:
        if hdr.get("enriched_count") != n_fully:
            raise ValueError(f"header.enriched_count={hdr.get('enriched_count')} 与实际 fully-verified {n_fully} 不符")
        if hdr["reverify_count"] != len(st.reverify_ids):
            raise ValueError(f"header.reverify_count={hdr['reverify_count']} 与实际 {len(st.reverify_ids)} 不符")
    extra_ev = set(raw_lines) - set(st.entries)
    if extra_ev:
        raise ValueError(f"evidence 含 manifest 之外的 id（{len(extra_ev)} 条）——拒绝")
    for iid in set(raw_lines) - claimed:
        # 非 enriched-shape 条目名下的 evidence 行（如 legacy 旧格式）不保留
        raw_lines.pop(iid, None)
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


def _canonical_evidence_payload(evidence: dict[str, dict]) -> bytes:
    return "".join(
        json.dumps(evidence[k], ensure_ascii=False, sort_keys=True) + "\n"
        for k in sorted(evidence)
    ).encode("utf-8")


def flush_transaction(manifest_path: Path, evidence_path: Path, st: Store,
                      refs_digest: str) -> None:
    """事务序：evidence 先落盘 → digest/行数进 header → manifest 最后作为提交记录。"""
    ev_payload = _canonical_evidence_payload(st.evidence)
    _atomic_write(evidence_path, ev_payload)
    enriched = sum(1 for k in st.entries if is_enriched(st, k))
    doc = {
        "header": {
            "schema_id": MANIFEST_SCHEMA_ID,
            "schema_version": 3,
            "purpose": "S2-1 T1b 键控镜像清单：216 survivor 的稳定镜像身份 + 实证平台",
            "source_refs_file": "data_freeze/meta/image_refs_swegym.txt",
            "source_refs_file_sha256": refs_digest,
            "evidence_file": EVIDENCE_RELPATH,
            "evidence_file_sha256": sha256_bytes(ev_payload),
            "evidence_line_count": len(st.evidence),
            "count": len(st.entries),
            "enriched_count": enriched,  # v3.1 起 = fully-verified 数
            "reverify_count": sum(
                1 for k in st.entries
                if entry_shape_enriched(st.entries[k]) and not is_enriched(st, k)
            ),  # v3.1 标记字段：存在即启用 enriched_count 严格对账
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
