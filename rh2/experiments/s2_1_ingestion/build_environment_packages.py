#!/usr/bin/env python3
"""S2-1 T2-c 运行器：真实 216 题 → v2 bundle 四件套 + duplicate cluster 报告。

输入均为冻结/账本化资产（路径固定于仓库结构）；任何前置校验不过即拒绝：
strip_spec digest pin、镜像清单 v4 严格加载 + 完成断言、survivor 计数。
输出到 docs/.../s2/ingest/（确定性字节，digest 打印供 manifest 登记）。

用法：uv run python rh2/experiments/s2_1_ingestion/build_environment_packages.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "rh2" / "src"))

from repoharness2.envpack.ingest_swegym_lite import (  # noqa: E402
    ingest_swegym_lite,
    load_trusted_ingest_outputs,
    write_ingest_outputs,
)
from repoharness2.envpack.t1_pins import T1PinsError, load_and_verify_t1_pins  # noqa: E402
from repoharness2.taskset.image_manifest_store import load_state  # noqa: E402

DOCS = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
DATA_FREEZE = DOCS / "data_freeze"
RAW = DOCS / "s2/raw/swe_gym_lite_full_f70b1a29.jsonl"
OUT_DIR = DOCS / "s2/ingest"
KNOWN_ENV_SHARED_PAIRS = [
    ("getmoto__moto-6469", "getmoto__moto-6470"),
    ("python__mypy-11824", "python__mypy-11857"),
]


def expected_ref(iid: str) -> str:
    return f"xingyaoww/sweb.eval.x86_64.{iid.replace('__', '_s_').lower()}:latest"


def fail(msg: str) -> None:
    print(f"[t2c] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    # 前置 0（codex 轮次 14 严重 1）：全部输入对 T1 封板 pins 验证——
    # 不是"读当前文件现算 SHA 当 provenance"，漂移即 fail-closed 报告。
    try:
        pins = load_and_verify_t1_pins(REPO_ROOT)
    except T1PinsError as exc:
        fail(str(exc))
    print("[t2c] T1 封板 pins 验证 OK：7/7 输入资产 digest 命中")

    survivors = [s.strip() for s in
                 (DATA_FREEZE / "labels/static_gate_survivors.txt").read_text().splitlines()
                 if s.strip()]
    frozen_refs = {l.strip() for l in
                   (DATA_FREEZE / "meta/image_refs_swegym.txt").read_text().splitlines()
                   if l.strip()}
    refs_digest = hashlib.sha256((DATA_FREEZE / "meta/image_refs_swegym.txt").read_bytes()).hexdigest()

    try:
        store = load_state(
            DOCS / "s2/image_manifest_keyed.json",
            DOCS / "s2/raw/image_registry_evidence.jsonl",
            set(survivors), frozen_refs, refs_digest, expected_ref,
        )
    except ValueError as exc:
        fail(f"键控镜像清单加载失败: {exc}")

    rows = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]

    try:
        result = ingest_swegym_lite(
            rows=rows, survivors=survivors, image_store=store,
            raw_archive_sha256="sha256:" + pins.raw_archive,          # 来自封板 pins
            image_manifest_keyed_sha256="sha256:" + pins.image_manifest_keyed,
        )
    except ValueError as exc:
        fail(str(exc))

    # 已知同环境两对必须保留且判为 distinct（T1 报告语义定案）
    ids = {p.instance_id for p in result.packages}
    for a, b in KNOWN_ENV_SHARED_PAIRS:
        if not (a in ids and b in ids):
            fail(f"已知同环境对 {a}/{b} 未同时保留（去重语义违约）")
    suspected = [c for c in result.duplicate_clusters if c.classification == "suspected_duplicate"]

    digests = write_ingest_outputs(result, OUT_DIR, pins=pins)
    # trusted 入口回读自检（T2-d/e 唯一正式消费入口在此先行实证）。
    # 注意：重新生成产物后若提交记录 digest 变化，须同步更新
    # ingest_swegym_lite.INGEST_MANIFEST_SHA256_PIN（审计事件）再跑本自检。
    try:
        trusted = load_trusted_ingest_outputs(REPO_ROOT)
    except ValueError as exc:
        fail(f"trusted 回读失败（若刚重生成产物：先按注释更新代码 pin）: {exc}")
    if len(trusted.result.packages) != len(result.packages):
        fail("trusted 回读数量不符")
    print(f"[t2c] trusted 入口回读自检 OK：{len(trusted.result.packages)} 包全链验证通过")
    print(f"[t2c] 216/216 构造成功；duplicate clusters: {len(result.duplicate_clusters)} "
          f"(suspected_duplicate: {len(suspected)})")
    for name, dig in sorted(digests.items()):
        print(f"[t2c] {name} sha256={dig}")
    if suspected:
        print("[t2c] 注意：存在 suspected_duplicate 簇，进入人工复核清单（不自动剔除）")
    print("[t2c] ALL PASS")


if __name__ == "__main__":
    main()
