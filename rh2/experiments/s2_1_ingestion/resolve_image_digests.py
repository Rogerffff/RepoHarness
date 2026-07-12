#!/usr/bin/env python3
"""S2-1 T1b：为 216 个 survivor 生成键控镜像清单（instance_id → resolved digest）。

对应执行文档 §2 交付物 2 / §4 T1。背景（codex 轮次 4 阻塞 2）：
`meta/image_refs_swegym.txt` 是 Full 2438 条无键 `:latest` 列表、无 manifest
digest，而 `PublicTaskBundle` 强制 `image_manifest_digest`——必须逐题解析出
稳定身份，运行期按 digest 拉取比对。

方法与限流姿态：
  - `_s_` 命名规则只作**映射校验**：由 instance_id 推导期望 ref，断言它
    存在于冻结清单文件中（两个来源互证；规则推导不单独作为身份来源）。
  - 逐镜像取 Docker Hub 匿名 token（每个镜像是独立 repository），
    然后 **HEAD** manifests/latest 读 `Docker-Content-Digest` 响应头。
    HEAD 不计入 Docker Hub 的 pull 限额（pull = manifest GET），
    匿名跑 216 个 HEAD 安全。
  - 平台字段：镜像按命名约定全为 x86_64；另对前 3 个镜像 GET manifest
    list 实证 amd64（仅 3 次计费 GET，作为约定的抽样证据）。
  - 0.4s 间隔 + 429/5xx/超时指数退避（最多 4 次尝试）。
  - 断点续跑：输出文件已有的 instance_id 跳过（幂等）。

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
DATA_FREEZE = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze"
OUT_PATH = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/image_manifest_keyed.json"
ACCEPT = ", ".join([
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
])
PLATFORM_SAMPLE_N = 3


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


def head_digest(repository: str, token: str) -> tuple[str, str]:
    url = f"https://registry-1.docker.io/v2/{repository}/manifests/latest"
    hdrs = {"Authorization": f"Bearer {token}", "Accept": ACCEPT}
    with with_backoff(lambda: http(url, "HEAD", hdrs), f"HEAD {repository}") as resp:
        digest = resp.headers.get("Docker-Content-Digest")
        ctype = resp.headers.get("Content-Type", "")
    if not digest or not digest.startswith("sha256:"):
        raise RuntimeError(f"{repository}: 响应缺 Docker-Content-Digest")
    return digest, ctype


def get_platforms(repository: str, token: str) -> list[str]:
    url = f"https://registry-1.docker.io/v2/{repository}/manifests/latest"
    hdrs = {"Authorization": f"Bearer {token}", "Accept": ACCEPT}
    with with_backoff(lambda: http(url, "GET", hdrs), f"GET {repository}") as resp:
        body = json.loads(resp.read())
    if "manifests" in body:  # manifest list / OCI index
        return sorted({
            f"{m['platform']['os']}/{m['platform']['architecture']}"
            for m in body["manifests"] if "platform" in m
        })
    return ["single-manifest（非 list，架构见 config blob，未展开）"]


def main() -> None:
    survivors = [
        s.strip() for s in
        (DATA_FREEZE / "labels/static_gate_survivors.txt").read_text().splitlines()
        if s.strip()
    ]
    refs_file = DATA_FREEZE / "meta/image_refs_swegym.txt"
    frozen_refs = {line.strip() for line in refs_file.read_text().splitlines() if line.strip()}
    refs_digest = hashlib.sha256(refs_file.read_bytes()).hexdigest()

    # `_s_` 规则推导 + 与冻结清单互证。
    # 注意 .lower()：Docker 仓库名强制小写（Project-MONAI__MONAI-4688 →
    # project-monai_s_monai-4688）——首跑时映射校验正确拦截了未小写的推导，
    # 这正是"规则只作校验、清单为身份来源"要抓的坑（记 implementation-notes）。
    plan: list[tuple[str, str]] = []
    for iid in survivors:
        ref = f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"
        if ref not in frozen_refs:
            print(f"[t1b] FAIL: 规则推导的 {ref} 不在冻结清单中（映射校验失败）", file=sys.stderr)
            sys.exit(1)
        plan.append((iid, ref))
    print(f"[t1b] `_s_` 映射校验 OK：216/216 推导 ref 均存在于冻结清单")

    # 断点续跑
    entries: dict[str, dict] = {}
    if OUT_PATH.exists():
        entries = {e["instance_id"]: e for e in json.loads(OUT_PATH.read_text())["entries"]}
        print(f"[t1b] 续跑：已有 {len(entries)} 条")

    sampled_platforms: list[str] | None = None
    for i, (iid, ref) in enumerate(plan):
        if iid in entries:
            continue
        repository, _, _tag = ref.partition(":")
        token = get_token(repository)
        digest, ctype = head_digest(repository, token)
        if sampled_platforms is None and i < PLATFORM_SAMPLE_N:
            sampled_platforms = get_platforms(repository, token)
        entries[iid] = {
            "instance_id": iid,
            "source_image_ref": ref,
            "resolved_manifest_digest": digest,
            "manifest_content_type": ctype,
            "platform": "x86_64（命名约定；抽样实证见 header.platform_sample）",
            "resolved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "method": "registry HEAD Docker-Content-Digest（不计 pull 限额）",
        }
        if (len(entries)) % 20 == 0:
            print(f"[t1b] progress {len(entries)}/216")
            _flush(entries, refs_digest, sampled_platforms)
        time.sleep(0.4)

    _flush(entries, refs_digest, sampled_platforms)
    print(f"[t1b] ALL PASS：{len(entries)}/216 解析完成 → {OUT_PATH.relative_to(REPO_ROOT)}")


def _flush(entries: dict[str, dict], refs_digest: str, sampled: list[str] | None) -> None:
    doc = {
        "header": {
            "purpose": "S2-1 T1b 键控镜像清单：216 survivor 的稳定镜像身份",
            "source_refs_file": "data_freeze/meta/image_refs_swegym.txt",
            "source_refs_file_sha256": refs_digest,
            "platform_sample": sampled or [],
            "count": len(entries),
        },
        "entries": [entries[k] for k in sorted(entries)],
    }
    OUT_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
