"""独立复核开发条件与 R-f 窄收尾；只写本审查目录，不改来源证据。"""
from __future__ import annotations

import argparse
import collections
import errno
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/scripts/r2e_env").is_dir())
TASKS = HERE.parent / "r2e_env_repair_20260924/tasks"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "dev_and_tools.json")
    ns = ap.parse_args()
    dev = module("review_dev", ROOT / "rh2/scripts/r2e_env/run_dev_probe.py")
    build = module("review_build", ROOT / "rh2/scripts/build_r2e_derived.py")
    rows = []
    for rp in sorted(TASKS.glob("*/screening_record.json")):
        rec = json.loads(rp.read_text())
        probe = json.loads((ROOT / rec["dev_probe_ref"]).read_text())
        raw_path = (ROOT / rec["dev_probe_ref"]).with_name("agent_probe.log")
        raw = raw_path.read_text().split("\n[stderr]\n", 1)[0]
        kv, blocks = dev._parse_kv_blocks(raw)
        derived = dev._derive(kv, blocks)
        rows.append({
            "instance_id": rec["instance_id"],
            "disposition": rec["disposition"]["state"],
            "classification": rec["classification"],
            "raw_ref": str(raw_path.relative_to(ROOT)),
            "raw_reparse_matches_saved": derived == probe["derived"],
            "core_pass": derived["min_dev_conditions_ok"],
            "pip_present": derived["pip_ok"],
            "public_collect_rc": kv.get("PUBLIC_COLLECT_RC"),
            "public_run_rc": kv.get("PUBLIC_RUN_RC"),
            "repro_rc": kv.get("REPRO_RC"),
            "repro_observation": [l for l in blocks.get("REPRO_OUTPUT", "").splitlines() if l.startswith("REPRO_OBSERVED=")],
            "R09": rec["checks"]["R09"],
            "known_issues": rec.get("issues", []),
        })
    # 原窄修：锁说明写入失败时也要释放锁；不启动构建或 Docker。
    lock_dir = HERE / "lock_header_failure_probe"
    lock_dir.mkdir(exist_ok=True)
    real_fdopen = os.fdopen

    class FailingWriter:
        def __init__(self, fd, *a, **kw):
            self.file = real_fdopen(fd, *a, **kw)

        def __enter__(self):
            return self

        def write(self, text):
            raise OSError(errno.ENOSPC, "review injected lock header failure")

        def __exit__(self, *exc):
            self.file.close()

    caught = None
    with patch.object(build.os, "fdopen", FailingWriter):
        try:
            build.main(["--repo-root", str(ROOT), "--out-dir", str(lock_dir), "--regenerate-overlays"])
        except OSError as exc:
            caught = exc.errno
    assert caught == errno.ENOSPC
    assert not (lock_dir / ".build.lock").exists()
    summary = {
        "tasks": len(rows), "raw_reparse_matches": sum(r["raw_reparse_matches_saved"] for r in rows),
        "ten_core_pass": sum(r["core_pass"] for r in rows),
        "pip_present": sum(r["pip_present"] for r in rows),
        "public_collect_rc": dict(collections.Counter(r["public_collect_rc"] for r in rows)),
        "public_run_rc": dict(collections.Counter(r["public_run_rc"] for r in rows)),
        "repro_flags": dict(collections.Counter(s.split("=", 1)[1].split()[0] for r in rows for s in r["repro_observation"])),
        "lock_header_enospc_released": True,
    }
    ns.out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
