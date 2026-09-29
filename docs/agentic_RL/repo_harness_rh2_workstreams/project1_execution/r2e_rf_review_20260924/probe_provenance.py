"""R-f 本地独立复核：镜像工件、运行绑定、代码快照和耗时。无 Docker / 远端调用。

从仓库根运行：rh2/.venv/bin/python <本文件> > <结果文件>
仅新建 runs/r2e_rf_review_20260924/verified_input_snapshot.tar.gz，原始证据不变。
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import statistics
import subprocess
import sys
import tarfile
from collections import defaultdict
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))
spec = importlib.util.spec_from_file_location("rf_derive_review", ROOT / "rh2/scripts/build_r2e_derived.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
REMOTE = ROOT / "runs/r2e_rf_20260923/remote"


def jsonl(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def snapshot():
    manifest = ROOT / "runs/r2e_snapshot_20260923.sha256"
    recovered = []
    contents = {}
    for line in manifest.read_text().splitlines():
        digest, name = line.split(None, 1)
        name = name.lstrip("*")
        data = (ROOT / name).read_bytes()
        origin = "current_tree"
        if hashlib.sha256(data).hexdigest() != digest:
            proc = subprocess.run(["git", "show", f"d4a11940:{name}"], cwd=ROOT, capture_output=True, check=True)
            origin = "git:d4a11940"
            old = proc.stdout
            if hashlib.sha256(old).hexdigest() != digest:
                # 这一个测试含当时未提交的 R2E fx 参数；只逆转随后 A 提交新增的两个签名参数。
                assert name == "rh2/tests/adapters_miles/test_w1b_group_admission.py"
                old = data.replace(b", env_injections=None, harness_log_dir=None):", b"):")
                origin = "current_tree_minus_later_A_optional_driver_args"
            data = old
            recovered.append({"path": name, "origin": origin})
        assert hashlib.sha256(data).hexdigest() == digest, name
        contents[name] = data
    contents["r2e_snapshot_20260923.sha256"] = manifest.read_bytes()
    target = ROOT / "runs/r2e_rf_review_20260924/verified_input_snapshot.tar.gz"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with tarfile.open(target, "w:gz") as tar:
            for name, data in sorted(contents.items()):
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                ti.mode = 0o644
                tar.addfile(ti, io.BytesIO(data))
    with tarfile.open(target, "r:gz") as tar:
        assert set(tar.getnames()) == set(contents)
        for name, data in contents.items():
            assert tar.extractfile(name).read() == data
    return {"manifest_items": len(contents) - 1, "matching_current_tree": len(contents) - 1 - len(recovered),
            "recovered": recovered, "all_hashes_match": True,
            "archive": str(target.relative_to(ROOT)), "archive_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}


def image_evidence():
    trusted = build.load_trusted_r2e_ingest_outputs(ROOT)
    by_id = {g.instance_id: g for g in trusted.result.grading_bundles}
    overlays = {x["task_id"]: x for x in jsonl(REMOTE / "overlays_all.jsonl")}
    reps = {x["task_id"]: x for x in jsonl(REMOTE / "overlays_reps.jsonl")}
    facts = sorted((REMOTE / "r2e_derived").glob("*/facts.json"))
    assert len(facts) == len(overlays) == len(by_id) == 48
    ids = {}
    metadata = []
    for path in facts:
        data = json.loads(path.read_text())
        g = by_id[data["instance_id"]]
        assert data["ok"] and not data["failures"]
        assert all(x["ok"] for x in data["integrity"].values())
        base = (path.parent / "integrity_base.txt").read_text()
        derived = (path.parent / "integrity_derived.txt").read_text()
        cfg = build._kv("\n".join(build._sections(base)["P"]))
        pydir = cfg["home"].removeprefix(build.UVROOT + "/").split("/")[0]
        checks = build.compare_integrity(base, derived, pydir=pydir)
        assert all(x["ok"] for x in checks.values()), data["instance_id"]
        f = data["root_facts"]
        assert f["head"] == g.base_commit
        assert "sha256:" + f["tree"] == g.hidden_tests_tree_sha256
        assert "sha256:" + f["run_tests_sh"] == g.run_tests_sh_sha256
        assert f["private_mode"] == "700" and f["private_owner"] == "root:root"
        assert f["fix_present"] == "no" and f["refs"] == f["remotes"] == f["reflog"] == "0"
        assert data["overlay"] == overlays[data["task_id"]]
        assert data["recipe_sha256"] == "sha256:" + hashlib.sha256((path.parent / "context/recipe_v1.sh").read_bytes()).hexdigest()
        ids[data["task_id"]] = data["derived_image_id"]
        if data["task_id"] in reps:
            text = (path.parent / "build.log").read_text()
            configs = sorted(set(re.findall(r"exporting config (sha256:[0-9a-f]+)", text)))
            indexes = sorted(set(re.findall(r"exporting manifest list (sha256:[0-9a-f]+)", text)))
            attestations = sorted(set(re.findall(r"exporting attestation manifest (sha256:[0-9a-f]+)", text)))
            old, new = reps[data["task_id"]]["derived_image_id"], data["derived_image_id"]
            assert old != new and old in indexes and new in indexes and len(configs) == 1
            metadata.append({"task_id": data["task_id"], "old_id": old, "new_id": new,
                             "exported_configs": configs, "exported_indexes": indexes, "exported_attestations": attestations})
    for kind in ("noop", "gold"):
        rows = jsonl(REMOTE / f"ledger_r2e_all_{kind}.jsonl")
        assert {x["task_id"] for x in rows} == set(ids) and len(rows) == 48
        for x in rows:
            assert x["image_id_actual"] == ids[x["task_id"]]
            assert x["image_identity"] == "local_build:" + ids[x["task_id"]]
            assert x["overlay"]["derived_image_id"] == ids[x["task_id"]]
    return {"derived_count": 48, "integrity_pairs_recomputed": 48, "full_batch_image_bindings_checked": 96,
            "representatives_metadata": metadata}


def phase_stats():
    groups = defaultdict(list)
    for gate in ("noop", "gold"):
        for row in jsonl(REMOTE / f"ledger_r2e_all_{gate}.jsonl"):
            groups[row["instance_id"].split("__")[0]].append(row)
    result = {}
    for repo, rows in sorted(groups.items()):
        totals = [sum(v or 0 for v in r["phases"].values()) for r in rows]
        median = lambda key: round(statistics.median(r["phases"].get(key) or 0 for r in rows), 3)
        result[repo] = {"n": len(rows), "grader_total_median_s": round(statistics.median(totals), 3),
                        "grader_total_max_s": round(max(totals), 3), "setup_median_s": median("grader_trusted_setup"),
                        "test_median_s": median("test"),
                        "setup_share_median": round(statistics.median(r["phases"]["grader_trusted_setup"] / t for r, t in zip(rows, totals)), 3)}
    return result


if __name__ == "__main__":
    print(json.dumps({"snapshot": snapshot(), "images": image_evidence(), "phases": phase_stats()}, ensure_ascii=False, indent=2))
