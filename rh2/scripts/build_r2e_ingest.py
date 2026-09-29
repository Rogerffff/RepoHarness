"""R2E-Gym-Subset 48 题 ingestion 运行器（R2E 接线 R-a）。

两步，都从 `rh2/` 运行：

    # 1) 封板输入 pins（只在输入文件定稿时做一次；打印的 sha256 写进 ingest_r2e_subset.R2E_PINS_SHA256）
    .venv/bin/python scripts/build_r2e_ingest.py seal-pins

    # 2) 生成产物（pins 记录必须已与代码常量一致；打印的提交记录 sha256 写进 R2E_INGEST_MANIFEST_SHA256_PIN）
    .venv/bin/python scripts/build_r2e_ingest.py ingest

`seal-pins` 不覆盖已有 pins 记录（封板记录不可变；确需重封 = 删除旧记录 + 改代码常量，是评审可见的事件）。
产物不含时间戳，同一输入重跑逐字节相同。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from repoharness2.envpack import ingest_r2e_subset as r2e
from repoharness2.envpack.r2e_parsers import R2E_RULE_SOURCE_VENDOR_RELPATH

REPO_ROOT = Path(__file__).resolve().parents[2]

_PIN_PATHS = {
    "raw_archive": r2e.R2E_RAW_ARCHIVE_RELPATH,
    "source_revision": r2e.R2E_SOURCE_REVISION_RELPATH,
    "image_facts": r2e.R2E_IMAGE_FACTS_RELPATH,
    "rule_source": R2E_RULE_SOURCE_VENDOR_RELPATH,
    "material_revisions": r2e.R2E_MATERIAL_REVISIONS_RELPATH,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal_pins(repo_root: Path) -> int:
    pins_path = repo_root / r2e.R2E_PINS_RELPATH
    if pins_path.exists():
        print(f"pins 记录已存在，不覆盖: {r2e.R2E_PINS_RELPATH}", file=sys.stderr)
        return 2
    doc = {
        "schema_id": r2e.R2E_PINS_SCHEMA_ID,
        "purpose": "R2E-Gym-Subset 48 题 ingestion 的封板输入（v12：v1 四项 + 材料修订单 v11（v1 §9 D4 模板授权修订经 Codex 复核）；v1–v11 记录保留为历史）；封板后不可追加、不可修改",
        "pins": {
            key: {"kind": "repo_file", "path": rel, "sha256": _sha256_file(repo_root / rel)}
            for key, rel in sorted(_PIN_PATHS.items())
        },
    }
    payload = (json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    pins_path.parent.mkdir(parents=True, exist_ok=True)
    pins_path.write_bytes(payload)
    print(json.dumps({"pins_record": r2e.R2E_PINS_RELPATH, "R2E_PINS_SHA256": hashlib.sha256(payload).hexdigest()}, indent=1))
    return 0


def ingest(repo_root: Path) -> int:
    pins = r2e.load_and_verify_r2e_pins(repo_root)
    image_facts = r2e.load_r2e_image_facts(repo_root, pins)
    revisions = r2e.load_r2e_material_revisions(repo_root, pins)
    rows, revision = r2e.load_r2e_rows(repo_root, pins)
    result = r2e.ingest_r2e_subset(
        rows=rows, image_facts=image_facts,
        raw_archive_sha256="sha256:" + pins.raw_archive,
        image_facts_sha256="sha256:" + pins.image_facts,
        source_revision=revision, revisions=revisions,
    )
    out_dir = repo_root / r2e.R2E_INGEST_OUT_RELPATH
    digests = r2e.write_r2e_ingest_outputs(result, out_dir, pins=pins, revisions=revisions)
    # 写完立刻用 strict loader 读回（不经代码 pin——那一步要等常量更新后由 load_trusted_* 验）
    expected_ids = {p.instance_id for p in result.packages}
    r2e.load_r2e_ingest_outputs(out_dir, pins=pins, image_facts=image_facts, expected_instance_ids=expected_ids,
                                revisions=revisions)
    print(json.dumps({
        "out_dir": r2e.R2E_INGEST_OUT_RELPATH,
        "package_count": len(result.packages),
        "R2E_INGEST_MANIFEST_SHA256_PIN": digests[r2e.R2E_INGEST_MANIFEST_NAME],
        "code_pin_matches": digests[r2e.R2E_INGEST_MANIFEST_NAME] == r2e.R2E_INGEST_MANIFEST_SHA256_PIN,
    }, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["seal-pins", "ingest"])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    ns = parser.parse_args(argv)
    root = Path(ns.repo_root).resolve()
    return seal_pins(root) if ns.command == "seal-pins" else ingest(root)


if __name__ == "__main__":  # pragma: no cover - 进程入口
    raise SystemExit(main())
