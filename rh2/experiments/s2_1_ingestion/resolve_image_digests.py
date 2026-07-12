#!/usr/bin/env python3
"""S2-1 T1b（v3）：216 survivor 键控镜像清单——digest + 实证 platform + evidence。

v3（codex 轮次 7）：状态机抽到 `repoharness2.taskset.image_manifest_store`
（可单测，见 rh2/tests/taskset/test_image_manifest_store.py），修复：
  1. manifest ↔ evidence 引用完整性（enriched 判定含逐字段交叉核对；
     evidence 缺失/篡改/多余/重复一律拒绝）。
  2. 双文件事务（evidence 先写，digest+行数入 header，manifest 最后作提交
     记录；崩溃唯一可能 = evidence 超前，load 按提交记录恢复）。
  3. evidence_ref 修正为 `raw/image_registry_evidence.jsonl#imgev-<id>`，
     evidence 行带 schema_id + 稳定 evidence_id + config blob 哈希实证
     （下载 blob 原始字节重算 sha256 必须等于 config_digest）。
  4.（轮次 8）事务恢复对已提交集合做规范化重序列化 SHA 回验；manifest
     重复 id 拒绝；header 机器账目对账；manifest 原始字节 sha256 ==
     Docker-Content-Digest 实证（manifest_blob_sha256_verified）——旧 evidence
     缺该实证的条目归 reverify 通道由完整富化补验（计 pull 限额）。

v2 legacy 产物的升级通道：digest 事实保留，逐条仅重取 config blob
（blob GET 不计 pull 限额）补验哈希与平台后升格——不重复消耗 manifest GET 限额。

退出码：0 = 216/216 全部 enriched；3 = INCOMPLETE_RESUMABLE（限额停车）。
用法：uv run python rh2/experiments/s2_1_ingestion/resolve_image_digests.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "rh2" / "src"))

from repoharness2.taskset.image_manifest_store import (  # noqa: E402
    DIGEST_RE, EVIDENCE_SCHEMA_ID, Store, evidence_id_for, evidence_ref_for,
    finish_assertions, flush_transaction, is_enriched, load_state,
    migrate_v3_manifest, sha256_bytes,
)

DATA_FREEZE = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze"
S2_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2"
OUT_PATH = S2_DIR / "image_manifest_keyed.json"
EVIDENCE_PATH = S2_DIR / "raw/image_registry_evidence.jsonl"
ACCEPT = ", ".join([
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
])
RATE_FLOOR = 8


def fail(msg: str) -> None:
    print(f"[t1b] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def http(url: str, method: str = "GET", headers: dict | None = None):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    return urllib.request.urlopen(req, timeout=30)


def with_backoff(fn, what: str):
    for attempt in range(1, 5):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if attempt == 4:
                raise RuntimeError(f"{what} 4 次尝试后仍失败: {exc}") from exc
            wait = 2 ** attempt
            print(f"[t1b] retry {what} attempt={attempt} wait={wait}s ({exc})", file=sys.stderr)
            time.sleep(wait)
    raise AssertionError("unreachable")


def get_token(repository: str) -> str:
    url = (f"https://auth.docker.io/token?service=registry.docker.io"
           f"&scope=repository:{repository}:pull")
    with with_backoff(lambda: http(url), f"token {repository}") as resp:
        return json.loads(resp.read())["token"]


def get_manifest(repository: str, token: str) -> tuple[dict, bytes, str, str, int | None]:
    url = f"https://registry-1.docker.io/v2/{repository}/manifests/latest"
    hdrs = {"Authorization": f"Bearer {token}", "Accept": ACCEPT}
    with with_backoff(lambda: http(url, "GET", hdrs), f"GET manifest {repository}") as resp:
        raw = resp.read()
        digest = resp.headers.get("Docker-Content-Digest", "")
        ctype = resp.headers.get("Content-Type", "")
        remaining = resp.headers.get("ratelimit-remaining")
    rem = int(remaining.split(";")[0]) if remaining else None
    return json.loads(raw), raw, digest, ctype, rem


def get_config_blob(repository: str, token: str, config_digest: str) -> tuple[dict, bool]:
    """GET config blob（不计 pull 限额）→ (config, 原始字节 sha256 == config_digest)。"""
    url = f"https://registry-1.docker.io/v2/{repository}/blobs/{config_digest}"
    hdrs = {"Authorization": f"Bearer {token}"}
    with with_backoff(lambda: http(url, "GET", hdrs), f"GET config {repository}") as resp:
        raw = resp.read()
    verified = f"sha256:{hashlib.sha256(raw).hexdigest()}" == config_digest
    return json.loads(raw), verified


def expected_ref(iid: str) -> str:
    # Docker 仓库名强制小写（T1 首跑实测坑）
    return f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"


def build_evidence(iid: str, repository: str, digest: str, ctype: str,
                   config_digest: str, platform: dict, blob_ok: bool,
                   manifest_ok: bool) -> dict:
    return {
        "schema_id": EVIDENCE_SCHEMA_ID,
        "evidence_id": evidence_id_for(iid),
        "instance_id": iid,
        "repository": repository,
        "manifest_digest": digest,
        "manifest_content_type": ctype,
        "config_digest": config_digest,
        "config_platform": platform,
        "config_blob_sha256_verified": blob_ok,
        "manifest_blob_sha256_verified": manifest_ok,  # codex 轮次 8 补强：原始字节 sha256 == Docker-Content-Digest
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def verify_blob_and_upgrade(st: Store, iid: str) -> None:
    """legacy 升级通道：只取 config blob（零 pull 限额），补验哈希与平台。"""
    e = st.entries[iid]
    repository = expected_ref(iid).partition(":")[0]
    config_digest = e.get("config_digest") or ""
    if not DIGEST_RE.match(config_digest):
        # v1 形态（无 config_digest）不能走升级通道，转完整富化
        raise KeyError(iid)
    token = get_token(repository)
    cfg, blob_ok = get_config_blob(repository, token, config_digest)
    if not blob_ok:
        fail(f"{iid}: config blob 原始字节 sha256 与 config_digest 不符（内容漂移）")
    platform = {"os": cfg.get("os"), "architecture": cfg.get("architecture")}
    if (platform["os"], platform["architecture"]) != ("linux", "amd64"):
        fail(f"{iid}: 平台断言失败 {platform}")
    st.evidence[iid] = build_evidence(
        iid, repository, e["resolved_manifest_digest"],
        e["manifest_content_type"], config_digest, platform, True,
        manifest_ok=False)  # blob 通道不取 manifest 字节 → 归 reverify，由完整通道补验
    st.reverify_ids.add(iid)
    e["platform"] = "linux/amd64"
    e["platform_source"] = "config_blob"
    e["registry_evidence_ref"] = evidence_ref_for(iid)
    e["method"] = "registry GET manifest + config blob（blob 哈希实证；GET 计 pull 限额，blob 不计）"
    st.legacy_ids.discard(iid)


def enrich_full(st: Store, iid: str) -> int | None:
    """完整富化：manifest GET（计限额，含 digest 漂移检测）+ blob 实证。"""
    repository = expected_ref(iid).partition(":")[0]
    token = get_token(repository)
    body, raw, digest, ctype, remaining = get_manifest(repository, token)
    if not DIGEST_RE.match(digest):
        fail(f"{iid}: GET 未返回合法 Docker-Content-Digest")
    if f"sha256:{hashlib.sha256(raw).hexdigest()}" != digest:
        fail(f"{iid}: manifest 原始字节 sha256 与 Docker-Content-Digest 不符")
    old = st.entries.get(iid, {}).get("resolved_manifest_digest")
    if old not in (None, digest):
        fail(f"{iid}: digest 漂移！已存 {old[:20]}… vs 现取 {digest[:20]}…（:latest 被重推？先人工裁决）")
    if "manifests" in body:
        fail(f"{iid}: 意外的 manifest list（此前实测全为单架构 v2 manifest）")
    config_digest = body["config"]["digest"]
    cfg, blob_ok = get_config_blob(repository, token, config_digest)
    if not blob_ok:
        fail(f"{iid}: config blob 哈希与 config_digest 不符")
    platform = {"os": cfg.get("os"), "architecture": cfg.get("architecture")}
    if (platform["os"], platform["architecture"]) != ("linux", "amd64"):
        fail(f"{iid}: 平台断言失败 {platform}")
    st.evidence[iid] = build_evidence(iid, repository, digest, ctype,
                                      config_digest, platform, True,
                                      manifest_ok=True)
    st.entries[iid] = {
        "instance_id": iid,
        "source_image_ref": expected_ref(iid),
        "resolved_manifest_digest": digest,
        "manifest_content_type": ctype,
        "config_digest": config_digest,
        "platform": "linux/amd64",
        "platform_source": "config_blob",
        "registry_evidence_ref": evidence_ref_for(iid),
        "resolved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "method": "registry GET manifest + config blob（blob 哈希实证；GET 计 pull 限额，blob 不计）",
    }
    st.legacy_ids.discard(iid)
    st.reverify_ids.discard(iid)
    return remaining


def main() -> None:
    survivors_list = [
        s.strip() for s in
        (DATA_FREEZE / "labels/static_gate_survivors.txt").read_text().splitlines()
        if s.strip()
    ]
    survivors = set(survivors_list)
    refs_file = DATA_FREEZE / "meta/image_refs_swegym.txt"
    frozen_refs = {line.strip() for line in refs_file.read_text().splitlines() if line.strip()}
    refs_digest = hashlib.sha256(refs_file.read_bytes()).hexdigest()

    for iid in survivors_list:
        if expected_ref(iid) not in frozen_refs:
            fail(f"规则推导的 {expected_ref(iid)} 不在冻结清单中（映射校验失败）")
    print("[t1b] `_s_`+lower 映射校验 OK：216/216 推导 ref 均存在于冻结清单")

    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--migrate-legacy-sha256", default=None,
                    help="一次性显式迁移旧 v2/v3 manifest：传入旧文件的 sha256 pin"
                         "（只接受已知产物；迁移后立即重写为 v4）")
    args = ap.parse_args()

    try:
        if args.migrate_legacy_sha256:
            st = migrate_v3_manifest(OUT_PATH, EVIDENCE_PATH, survivors, frozen_refs,
                                     refs_digest, expected_ref,
                                     args.migrate_legacy_sha256)
            flush_transaction(OUT_PATH, EVIDENCE_PATH, st, refs_digest)
            print(f"[t1b] legacy 迁移完成并已重写为 v4（entries {len(st.entries)}，"
                  f"reverify {len(st.reverify_ids)}，legacy {len(st.legacy_ids)}）")
        st = load_state(OUT_PATH, EVIDENCE_PATH, survivors, frozen_refs,
                        refs_digest, expected_ref)
    except ValueError as exc:
        fail(str(exc))
    if st.recovered_drop:
        print(f"[t1b] 事务恢复：丢弃 {st.recovered_drop} 条未提交 evidence 行（manifest 为提交记录）")
    n_ok = sum(1 for k in st.entries if is_enriched(st, k))
    print(f"[t1b] 旧状态校验 OK：{len(st.entries)} 条（fully-verified {n_ok}，"
          f"reverify 待 manifest 字节实证 {len(st.reverify_ids)}，legacy 待升级 {len(st.legacy_ids)}）")

    def flush() -> None:
        flush_transaction(OUT_PATH, EVIDENCE_PATH, st, refs_digest)

    # 升级通道（零 pull 限额）
    done = 0
    for iid in sorted(st.legacy_ids):
        try:
            verify_blob_and_upgrade(st, iid)
        except KeyError:
            continue  # v1 形态 → 留给完整富化
        done += 1
        if done % 20 == 0:
            flush()
            print(f"[t1b] legacy 升级 +{done}")
        time.sleep(0.2)
    if done:
        flush()
        print(f"[t1b] legacy 升级完成：{done} 条（blob 哈希全部实证）")

    # 完整富化（计 pull 限额，限额感知停车）
    done = 0
    for iid in survivors_list:
        if is_enriched(st, iid):
            continue
        remaining = enrich_full(st, iid)
        done += 1
        if done % 20 == 0:
            flush()
            print(f"[t1b] progress enriched+{done}（ratelimit-remaining={remaining}）")
        if remaining is not None and remaining < RATE_FLOOR:
            flush()
            n = sum(1 for k in st.entries if is_enriched(st, k))
            print(f"[t1b] INCOMPLETE_RESUMABLE：pull 限额余量 {remaining} < {RATE_FLOOR}，"
                  f"优雅停车（enriched {n}/216；限额窗口重置后重跑续做）")
            sys.exit(3)
        time.sleep(0.4)

    flush()
    problems = finish_assertions(st, survivors)
    if problems:
        fail("完成断言失败：\n  " + "\n  ".join(problems))
    print(f"[t1b] ALL PASS：216/216 digest + blob 实证平台 + evidence 交叉核对 "
          f"→ {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
