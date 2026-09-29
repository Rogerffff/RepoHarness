"""Verify old F2 fixes through real CLI, only against temporary review fixtures."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
CLI = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_prep_20260924/prepare_materials_r2e.py"


def put(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


with tempfile.TemporaryDirectory(prefix="verify-followup-", dir=HERE) as tmp:
    base = Path(tmp)
    out, imgs = base / "out", base / "images"
    worktree = out / "public/probe/worktree"
    worktree.mkdir(parents=True)
    payload = b"recorded file\n"
    file = worktree / "file.txt"
    file.write_bytes(payload)
    file.chmod(0o644)
    fp = {"sha256": hashlib.sha256(payload).hexdigest(), "mode": "0o644"}
    put(out / "material_check.json", {"tasks": {"probe": {}}})
    put(out / "public/probe/worktree_manifest.json", {
        "files": {"file.txt": fp}, "export": {}, "base_commit": "a" * 40,
    })
    put(imgs / "probe/image_hashes.json", {
        "instance_id": "probe", "files": {"file.txt": {"kind": "tracked", **fp}},
        "head": "a" * 40, "image_ref": "probe", "image_id": "sha256:" + "b" * 64,
    })

    def verify(images):
        p = subprocess.run([sys.executable, "-B", str(CLI), "verify", "--out", str(out),
                            "--image-files", str(images)], capture_output=True, text=True)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

    results = {"healthy": verify(imgs)}
    file.write_bytes(b"actual bytes changed\n")
    results["changed_bytes"] = verify(imgs)
    file.unlink()
    results["missing_file"] = verify(imgs)
    file.write_bytes(payload)
    (worktree / "extra.txt").write_text("extra")
    results["extra_file"] = verify(imgs)
    (worktree / "extra.txt").unlink()
    file.unlink()
    file.symlink_to("missing-target")
    results["changed_to_symlink"] = verify(imgs)
    file.unlink()
    file.write_bytes(payload)
    results["missing_image_directory"] = verify(base / "missing")
    assert results["healthy"]["returncode"] == 0, results
    assert all(r["returncode"] != 0 for n, r in results.items() if n != "healthy"), results
    (HERE / "verify_followup.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({n: r["returncode"] for n, r in results.items()}))
