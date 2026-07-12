#!/usr/bin/env python3
"""S2-1 T1b（v2）：216 survivor 的键控镜像清单——digest + 实证 platform + evidence。

v2 相对 v1 的修复（codex 轮次 6 审查，存档 s2/codex_reviews.md）：
  1. 续跑 fail-closed：加载旧文件先逐条严格校验（id ∈ survivors、ref 与规则
     推导一致且在冻结清单中、digest 是合法 sha256、必填字段齐全、无多余 id、
     header 的 refs 文件 digest 匹配），任何损坏即拒绝续跑；完成时强制
     set(entries) == set(survivors) 且逐条 enriched。
  2. 幂等：header（含 schema_id）由事实重建并与旧值比对，不静默清空。
  3. 原子写：临时文件 + fsync + os.replace，任何时刻磁盘上都是合法 JSON。
  4. 平台实证（计划 §2 交付物 2 的完整口径）：逐镜像 GET manifest（校验
     Docker-Content-Digest == 已存 digest，顺带漂移检测）→ 取 config.digest
     → GET config blob（blob 不计 pull 限额）→ 读 os/architecture 断言
     linux/amd64；evidence 逐镜像落 s2/raw/image_registry_evidence.jsonl
     （manifest/config digest + platform 事实 + 时间戳），entry 带
     registry_evidence_ref 回链。
  5. 限额感知：manifest GET 计入 Docker Hub pull 限额（匿名 100/6h/IP）——
     每次响应读 ratelimit-remaining 头，余量 < 8 时优雅停车（checkpoint
     已落盘，重跑续做），退出码 3 = INCOMPLETE_RESUMABLE。

用法：uv run --group data python rh2/experiments/s2_1_ingestion/resolve_image_digests.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FREEZE = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze"
S2_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2"
OUT_PATH = S2_DIR / "image_manifest_keyed.json"
EVIDENCE_PATH = S2_DIR / "raw/image_registry_evidence.jsonl"
SCHEMA_ID = "rh2.s2_1.image_manifest_keyed.v2"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ACCEPT = ", ".join([
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
])
RATE_FLOOR = 8  # 匿名 pull 限额余量低于此值即优雅停车


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
        except Exception as exc:  # noqa: BLE001 —— 429/5xx/超时统一退避
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


def get_manifest(repository: str, token: str) -> tuple[dict, str, str, int | None]:
    """GET manifest → (body, Docker-Content-Digest, content_type, ratelimit_remaining)。"""
    url = f"https://registry-1.docker.io/v2/{repository}/manifests/latest"
    hdrs = {"Authorization": f"Bearer {token}", "Accept": ACCEPT}
    with with_backoff(lambda: http(url, "GET", hdrs), f"GET manifest {repository}") as resp:
        raw = resp.read()
        digest = resp.headers.get("Docker-Content-Digest", "")
        ctype = resp.headers.get("Content-Type", "")
        remaining = resp.headers.get("ratelimit-remaining")
    rem = int(remaining.split(";")[0]) if remaining else None
    return json.loads(raw), digest, ctype, rem


def get_config_platform(repository: str, token: str, config_digest: str) -> dict:
    """GET config blob（不计 pull 限额）→ {os, architecture}。"""
    url = f"https://registry-1.docker.io/v2/{repository}/blobs/{config_digest}"
    hdrs = {"Authorization": f"Bearer {token}"}
    with with_backoff(lambda: http(url, "GET", hdrs), f"GET config {repository}") as resp:
        cfg = json.loads(resp.read())
    return {"os": cfg.get("os"), "architecture": cfg.get("architecture")}


def expected_ref(iid: str) -> str:
    # Docker 仓库名强制小写（T1 首跑实测坑：Project-MONAI → project-monai）
    return f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"


def atomic_write_json(path: Path, doc: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def atomic_write_evidence(entries: dict[str, dict]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = EVIDENCE_PATH.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for k in sorted(entries):
            fh.write(json.dumps(entries[k], ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, EVIDENCE_PATH)


def validate_entry(e: dict, survivors: set[str], frozen_refs: set[str]) -> list[str]:
    """校验单条 entry；返回问题清单（空 = 合法）。enriched 与否另行判断。"""
    problems = []
    iid = e.get("instance_id", "")
    if iid not in survivors:
        problems.append(f"未知 instance_id: {iid!r}")
        return problems
    if e.get("source_image_ref") != expected_ref(iid) or e["source_image_ref"] not in frozen_refs:
        problems.append(f"{iid}: source_image_ref 非法")
    if not DIGEST_RE.match(e.get("resolved_manifest_digest", "")):
        problems.append(f"{iid}: manifest digest 非法")
    for f in ("manifest_content_type", "resolved_at", "method"):
        if not e.get(f):
            problems.append(f"{iid}: 缺字段 {f}")
    return problems


def is_enriched(e: dict) -> bool:
    return (
        DIGEST_RE.match(e.get("config_digest", "") or "") is not None
        and e.get("platform") == "linux/amd64"
        and e.get("platform_source") == "config_blob"
        and bool(e.get("registry_evidence_ref"))
    )


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

    # ---- 严格加载旧状态（fail-closed 续跑，codex 轮次 6 问题 1/2） ----
    entries: dict[str, dict] = {}
    evidence: dict[str, dict] = {}
    if OUT_PATH.exists():
        doc = json.loads(OUT_PATH.read_text())
        hdr = doc.get("header", {})
        if hdr.get("schema_id") not in (None, SCHEMA_ID):
            fail(f"header schema_id 不认识: {hdr.get('schema_id')}")
        if hdr.get("source_refs_file_sha256") not in (None, refs_digest):
            fail("header 的 refs 文件 digest 与当前冻结清单不符（数据面变动？）")
        problems: list[str] = []
        for e in doc.get("entries", []):
            problems.extend(validate_entry(e, survivors, frozen_refs))
            entries[e.get("instance_id", "")] = e
        if problems:
            fail("旧文件校验不过，拒绝续跑（先人工裁决）：\n  " + "\n  ".join(problems[:10]))
        print(f"[t1b] 旧状态校验 OK：{len(entries)} 条合法（其中 enriched "
              f"{sum(1 for e in entries.values() if is_enriched(e))} 条）")
    if EVIDENCE_PATH.exists():
        for line in EVIDENCE_PATH.read_text().splitlines():
            if line.strip():
                ev = json.loads(line)
                evidence[ev["instance_id"]] = ev

    def flush() -> None:
        doc = {
            "header": {
                "schema_id": SCHEMA_ID,
                "schema_version": 2,
                "purpose": "S2-1 T1b 键控镜像清单：216 survivor 的稳定镜像身份 + 实证平台",
                "source_refs_file": "data_freeze/meta/image_refs_swegym.txt",
                "source_refs_file_sha256": refs_digest,
                "evidence_file": "s2/raw/image_registry_evidence.jsonl",
                "count": len(entries),
                "enriched_count": sum(1 for e in entries.values() if is_enriched(e)),
            },
            "entries": [entries[k] for k in sorted(entries)],
        }
        atomic_write_json(OUT_PATH, doc)
        atomic_write_evidence(evidence)

    # ---- 富化循环（digest 缺 → HEAD 语义由 GET 覆盖；GET 计 1 次 pull） ----
    done = 0
    for iid in survivors_list:
        e = entries.get(iid)
        if e and is_enriched(e):
            continue
        repository = expected_ref(iid).partition(":")[0]
        token = get_token(repository)
        body, digest, ctype, remaining = get_manifest(repository, token)
        if not DIGEST_RE.match(digest):
            fail(f"{iid}: GET 未返回合法 Docker-Content-Digest")
        if e and e.get("resolved_manifest_digest") not in (None, digest):
            fail(f"{iid}: digest 漂移！已存 {e['resolved_manifest_digest'][:20]}… "
                 f"vs 现取 {digest[:20]}…（:latest 被重推？先人工裁决）")
        if "manifests" in body:
            fail(f"{iid}: 意外的 manifest list（此前实测全为单架构 v2 manifest）")
        config_digest = body["config"]["digest"]
        platform = get_config_platform(repository, token, config_digest)
        if (platform["os"], platform["architecture"]) != ("linux", "amd64"):
            fail(f"{iid}: 平台断言失败 {platform}（计划要求 linux/amd64）")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        evidence[iid] = {
            "instance_id": iid,
            "repository": repository,
            "manifest_digest": digest,
            "manifest_content_type": ctype,
            "config_digest": config_digest,
            "config_platform": platform,
            "fetched_at": now,
        }
        entries[iid] = {
            "instance_id": iid,
            "source_image_ref": expected_ref(iid),
            "resolved_manifest_digest": digest,
            "manifest_content_type": ctype,
            "config_digest": config_digest,
            "platform": "linux/amd64",
            "platform_source": "config_blob",
            "registry_evidence_ref": f"image_registry_evidence.jsonl#{iid}",
            "resolved_at": now,
            "method": "registry GET manifest + config blob（GET 计 pull 限额，blob 不计）",
        }
        done += 1
        if done % 20 == 0:
            flush()
            print(f"[t1b] progress enriched+{done}（ratelimit-remaining={remaining}）")
        if remaining is not None and remaining < RATE_FLOOR:
            flush()
            print(f"[t1b] INCOMPLETE_RESUMABLE：pull 限额余量 {remaining} < {RATE_FLOOR}，"
                  f"优雅停车（已 enriched {sum(1 for x in entries.values() if is_enriched(x))}/216；"
                  f"限额窗口重置后重跑本脚本续做）")
            sys.exit(3)
        time.sleep(0.4)

    flush()
    # ---- 完成断言（codex 轮次 6 问题 1 的完成时强制检查） ----
    if set(entries) != survivors:
        fail(f"完成断言失败：entries {len(entries)} 与 survivors 216 集合不等")
    not_enriched = [k for k, e in entries.items() if not is_enriched(e)]
    if not_enriched:
        fail(f"完成断言失败：{len(not_enriched)} 条未 enriched: {not_enriched[:5]}")
    print(f"[t1b] ALL PASS：216/216 digest + 实证平台 linux/amd64 + evidence 回链 "
          f"→ {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
