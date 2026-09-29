"""只在本审查目录的临时夹具里验证 verify CLI；不接触 v1。"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
CLI = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_prep_20260924/prepare_materials_r2e.py"


def put_json(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj))


with tempfile.TemporaryDirectory(prefix="verify-fixture-", dir=HERE) as tmp:
    base = Path(tmp)
    out, imgs = base / "out", base / "images"
    worktree = out / "public/probe/worktree"
    worktree.mkdir(parents=True)
    payload = b"the recorded file\n"
    (worktree / "file.txt").write_bytes(payload)
    fp = {"sha256": hashlib.sha256(payload).hexdigest(), "mode": "0o644"}
    put_json(out / "material_check.json", {"tasks": {"probe": {}}})
    put_json(out / "public/probe/worktree_manifest.json", {"files": {"file.txt": fp}, "export": {}, "base_commit": "a" * 40})
    put_json(imgs / "probe/image_hashes.json", {"instance_id": "probe", "files": {"file.txt": {"kind": "tracked", **fp}}, "head": "a" * 40, "image_ref": "probe", "image_id": "sha256:" + "b" * 64})

    def verify(image_dir):
        p = subprocess.run([sys.executable, "-B", str(CLI), "verify", "--out", str(out), "--image-files", str(image_dir)], capture_output=True, text=True)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "image_verification": json.loads((out / "material_check.json").read_text())["image_verification"]}

    healthy = verify(imgs)
    assert healthy["returncode"] == 0 and healthy["image_verification"]["probe"]["ok"]
    (worktree / "file.txt").write_bytes(b"actual bytes now differ\n")
    corrupt = verify(imgs)
    assert corrupt["returncode"] == 0 and corrupt["image_verification"]["probe"]["ok"]
    empty = verify(base / "missing-image-directory")
    assert empty["returncode"] == 0 and empty["image_verification"] == {}
    result = {"scope": "真实 CLI + 本审查目录内合成夹具；正式 v1 未改", "healthy": healthy, "changed_worktree_still_passes": corrupt, "missing_image_directory_still_passes": empty}
    (HERE / "probe_verify_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v["returncode"] for k, v in result.items() if isinstance(v, dict)}, ensure_ascii=False))
