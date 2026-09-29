"""Recheck first12 static materials against frozen hashes and local Git trees."""
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

B = Path(__file__).resolve().parent
ROOT = next(p for p in B.parents if (p / "rh2/src/repoharness2").is_dir())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    errors, rows = [], []
    manifest_path = B / "manifest.json"
    manifest_sha = sha(manifest_path)
    assert manifest_sha == "52649a38cadccdeacc2317f8d4fb7beee798247e2c9adbc00a198dea88261c7e"
    manifest = json.loads(manifest_path.read_text())
    material = json.loads((B / "material_check.json").read_text())
    assert sha(B / "material_check.json") == "c7c92808b15decb72702bc4723fa9e864ead8e0b636bd08f1934ea2c420aff89"
    for source in (manifest["source_index"], manifest["prior_review_exclusion"]):
        assert sha(ROOT / source["path"]) == source["sha256"]
    tasks = [t for t in manifest["tasks"] if t["stage"] == "first12"]
    assert len(tasks) == 12
    artifacts = histories = blobs = byte_count = executables = symlinks = 0
    for task in tasks:
        tid = task["instance_id"]
        try:
            record = next(r for r in material["tasks"] if r["instance_id"] == tid)
            for artifact in record["artifact_hashes"]:
                assert sha(ROOT / artifact["path"]) == artifact["sha256"], artifact["path"]
                artifacts += 1
            for source in task["history_source_availability"].values():
                assert source["exists"]
            for path, source in task["history_source_availability"].items():
                assert sha(ROOT / path) == source["sha256"], path
                histories += 1
            public = ROOT / task["public_dir"]
            assert {p.name for p in public.iterdir()} == {
                "base", "base_identity.json", "environment_brief.md", "public_bundle.json", "user_prompt.txt"}
            base = public / "base"
            tree = subprocess.run(
                ["git", "-C", str(ROOT / task["repo_mirror"]), "ls-tree", "-rz", task["base_commit"]],
                check=True, capture_output=True).stdout
            expected, local_blobs, local_bytes = set(), 0, 0
            for item in tree.split(b"\0"):
                if not item:
                    continue
                meta, raw_path = item.split(b"\t", 1)
                mode, kind, oid = meta.decode().split()
                path = os.fsdecode(raw_path)
                assert kind == "blob", (tid, path, kind)
                expected.add(path)
                target = base / path
                if mode == "120000":
                    assert target.is_symlink(), path
                    raw = os.fsencode(os.readlink(target))
                    symlinks += 1
                else:
                    assert target.is_file() and not target.is_symlink(), path
                    raw = target.read_bytes()
                    assert bool(target.stat().st_mode & 0o111) == (mode == "100755"), path
                    executables += mode == "100755"
                assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == oid, path
                local_blobs += 1
                local_bytes += len(raw)
            actual = set()
            for parent, dirs, files in os.walk(base, followlinks=False):
                for name in dirs + files:
                    path = Path(parent) / name
                    if path.is_symlink() or path.is_file():
                        actual.add(str(path.relative_to(base)))
            assert actual == expected, "export path set differs from Git tree"
            assert local_blobs == record["materialized_blob_entries"]
            assert local_bytes == record["blob_bytes"]
            blobs += local_blobs
            byte_count += local_bytes
            rows.append({"instance_id": tid, "artifact_hashes_verified": 12,
                         "git_blob_oid_mode_path_set_verified": True,
                         "blob_count": local_blobs, "blob_bytes": local_bytes})
        except (AssertionError, OSError, subprocess.CalledProcessError) as exc:
            errors.append(f"{tid}: {exc}")
    assignments = json.loads((B / "assignments.json").read_text())
    reserve = set(manifest["reserve20_task_ids"])
    dispatched = [a["agent_id"] for a in assignments["assignments"]
                  if a["role"] in ("public_reader", "investigator", "reviewer")
                  and reserve.intersection(a["instance_ids"])]
    unexpected_dirs = [str(ROOT / t[key]) for t in manifest["tasks"] if t["instance_id"] in reserve
                       for key in ("public_dir", "private_dir", "history_dir", "output_dir")
                       if (ROOT / t[key]).exists()]
    if dispatched or unexpected_dirs:
        errors.append(f"reserve20 released unexpectedly: agents={dispatched}, directories={unexpected_dirs}")
    return {"schema": "quality_expansion.material_freeze.v1",
            "checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "passed": not errors, "errors": errors, "manifest_sha256": manifest_sha,
            "task_count": len(rows), "artifact_hashes_verified": artifacts,
            "history_source_hashes_verified": histories, "git_blobs_verified": blobs,
            "blob_bytes": byte_count, "executable_blobs": executables, "symlinks": symlinks,
            "reserve20_directories_absent": not unexpected_dirs, "reserve20_review_roles_absent": not dispatched,
            "tasks": rows,
            "limits": "Static material bytes and local Git trees only; does not prove actual actor worktree, image assets, runtime or isolation."}


if __name__ == "__main__":
    result = verify()
    (B / "first12_material_freeze_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("passed", "errors", "task_count", "artifact_hashes_verified", "history_source_hashes_verified", "git_blobs_verified", "blob_bytes", "reserve20_directories_absent", "reserve20_review_roles_absent")}, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)
