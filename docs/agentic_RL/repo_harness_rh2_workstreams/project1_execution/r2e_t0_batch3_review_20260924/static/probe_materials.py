"""独立只读核对 R2E v1 静态材料；只向本审查目录写 JSON，不运行题目代码。

从仓库根用 rh2/.venv/bin/python -B <本文件> 运行。
不调用材料生成器或其 verify（后者会写回 v1）；不 fetch / Docker / SSH。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
DOCS = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
RUN = ROOT / "runs/r2e_static_prep_20260924"
SNAP = RUN / "v1"
PREP = DOCS / "project1_execution/r2e_static_prep_20260924"
ROUND = DOCS / "project1_execution/r2e_env_repair_20260924"
INGEST = DOCS / "s2_r2e/ingest"
M3 = ROOT / "runs/env_overnight_20260916/M3/facts"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(p: Path):
    return json.loads(p.read_bytes())


def rows(p: Path) -> dict:
    out = {}
    for n, line in enumerate(p.read_bytes().splitlines(), 1):
        r = json.loads(line)
        assert r["instance_id"] not in out, p
        out[r["instance_id"]] = (n, line, r)
    return out


def git(repo: str, *args: str) -> bytes:
    return subprocess.check_output(["git", "--git-dir", str(RUN / "git" / f"{repo}.git"), *args])


def tree_entries(repo: str, commit: str) -> dict:
    out = {}
    for row in git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if row:
            meta, name = row.split(b"\t", 1)
            out[name.decode()] = tuple(x.decode() for x in meta.split())
    return out


def replay_diff(data: bytes, base: dict, repo: str) -> dict:
    """逐 hunk 校验旧上下文与行数，在内存重建；不调用原生成器或 git apply。"""
    out = {}
    chunks = re.split(br"(?m)^diff --git ", data)[1:]
    for chunk in chunks:
        lines = chunk.splitlines(keepends=True)
        a, b = lines[0].rstrip(b"\n").split(b" ")
        assert a.startswith(b"a/") and b.startswith(b"b/") and a[2:] == b[2:]
        name = a[2:].decode()
        old = git(repo, "cat-file", "blob", base[name][2]) if name in base else b""
        old_lines = old.splitlines(keepends=True)
        result, cursor, pos = [], 0, 1
        while pos < len(lines):
            if not lines[pos].startswith(b"@@ "):
                pos += 1
                continue
            h = re.match(br"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[pos])
            assert h, (name, lines[pos])
            a_start, a_count, b_start, b_count = (int(x) if x is not None else 1 for x in h.groups())
            start = a_start - 1 if a_count else a_start
            assert start >= cursor, name
            result.extend(old_lines[cursor:start])
            assert len(result) == (b_start - 1 if b_count else b_start), name
            cursor = start
            removed = added = 0
            pos += 1
            while pos < len(lines) and not lines[pos].startswith(b"@@ "):
                ln = lines[pos]
                if ln[:1] not in (b" ", b"-", b"+"):
                    break
                op, content = ln[:1], ln[1:]
                if pos + 1 < len(lines) and lines[pos + 1].startswith(b"\\ No newline at end of file"):
                    content = content[:-1]
                    pos += 1
                if op in (b" ", b"-"):
                    assert old_lines[cursor] == content, (name, cursor)
                    cursor += 1
                    removed += 1
                if op in (b" ", b"+"):
                    result.append(content)
                    added += 1
                pos += 1
            assert (removed, added) == (a_count, b_count), (name, removed, added, a_count, b_count)
        result.extend(old_lines[cursor:])
        out[name] = None if b"deleted file mode " in chunk else b"".join(result)
        index = re.search(br"(?m)^index ([0-9a-f]+)\.\.([0-9a-f]+)", chunk)
        if index:
            assert blob_sha(old).startswith(index[1].decode()), name
            if out[name] is not None:
                assert blob_sha(out[name]).startswith(index[2].decode()), name
    return out


def actual_files(root: Path) -> dict:
    out = {}
    for dp, ds, fs in os.walk(root, followlinks=False):
        for name in fs + [d for d in ds if (Path(dp) / d).is_symlink()]:
            p = Path(dp) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                assert p.resolve().is_relative_to(root.resolve()), ("symlink escape", p)
                assert p.exists(), ("dangling symlink", p)
                out[rel] = {"symlink": os.readlink(p)}
            else:
                assert p.is_file(), p
                out[rel] = {"sha256": sha(p.read_bytes()), "mode": oct(p.stat().st_mode & 0o777)}
    return dict(sorted(out.items()))


def main() -> None:
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT / "rh2/src"))
    from repoharness2.envpack.bundles import PublicTaskBundle, render_user_prompt
    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs
    trusted = load_trusted_r2e_ingest_outputs(ROOT)
    public = rows(INGEST / "public_bundles_v0.jsonl")
    grading = rows(INGEST / "grading_bundles_r2e_v0.jsonl")
    valid = rows(INGEST / "validation_bundles_v0.jsonl")
    ids = set(public)
    assert len(ids) == 48 and ids == set(grading) == set(valid)
    assert ids == {g.instance_id for g in trusted.result.grading_bundles}
    check_bytes = (SNAP / "material_check.json").read_bytes()
    assert check_bytes == (PREP / "material_check.json").read_bytes()
    check = json.loads(check_bytes)
    assert set(check["tasks"]) == ids
    assert check["code_sha256"] == sha((PREP / "prepare_materials_r2e.py").read_bytes())
    assert check["inputs"]["ingest_manifest_sha256"] == sha((INGEST / "ingest_manifest_v0.json").read_bytes())
    rev_file = DOCS / "s2_r2e/revisions/material_revisions_v3.json"
    assert check["inputs"]["material_revisions_v3_sha256"] == sha(rev_file.read_bytes())
    revs = load(rev_file)["revisions"]
    raw = {r["repo_name"] + "__" + r["commit_hash"]: r for r in map(json.loads, (DOCS / "s2_r2e/raw/r2e_gym_subset_48_e8b9fcbc.jsonl").read_bytes().splitlines())}
    pins = load(ROUND / "recipes/env_pins_v2.json")["tasks"]
    for area in ("public", "private", "history"):
        assert {p.name for p in (SNAP / area).iterdir()} == ids, area

    counts = Counter()
    tasks = {}
    image_reports = {}
    symlinks = []
    missing_ref_class = Counter()
    latest_overlays = {}
    for rel in ("runs/r2e_rf_20260923/remote/r2e_derived/overlays.jsonl", "runs/r2e_t0_revisions_20260924/derived/overlays.jsonl", "runs/r2e_t0_batch2_20260924/derived3/overlays.jsonl", "runs/r2e_t0_batch3_20260924/derived7/overlays.jsonl"):
        for r in map(json.loads, (ROOT / rel).read_bytes().splitlines()):
            latest_overlays[r["task_id"].split("::", 1)[1]] = r
    for iid in sorted(ids):
        pub, prv, hist = (SNAP / area / iid for area in ("public", "private", "history"))
        assert {p.name for p in pub.iterdir()} == {"public_bundle.json", "user_prompt.txt", "environment_brief.md", "worktree", "worktree_manifest.json"}
        assert {p.name for p in prv.iterdir()} == {"grading_bundle.json", "validation_bundle.json", "expected_output.json", "gold.patch", "run_tests.sh", "hidden_tests", "revisions.json", "refs.json"}
        assert {p.name for p in hist.iterdir()} == {"refs.json"}
        for path, current in ((pub / "public_bundle.json", public), (prv / "grading_bundle.json", grading), (prv / "validation_bundle.json", valid)):
            got = load(path)
            n, line, row = current[iid]
            assert got["row"] == row and got["line_sha256"] == sha(line), path
            assert "line" not in got or got["line"] == n
        g, v, p = grading[iid][2], valid[iid][2], public[iid][2]
        assert (pub / "user_prompt.txt").read_text() == render_user_prompt(PublicTaskBundle.model_validate(p))
        for fn, text, digest in (("expected_output.json", g["expected_output_json"], g["expected_output_json_sha256"]), ("gold.patch", v["golden_patch"], v["golden_patch_sha256"]), ("run_tests.sh", g["run_tests_sh"], g["run_tests_sh_sha256"])):
            assert (prv / fn).read_bytes() == text.encode()
            assert "sha256:" + sha((prv / fn).read_bytes()) == digest
        current_revs = [r for r in revs if r["instance_id"] == iid]
        assert load(prv / "revisions.json") == current_revs
        doc = json.loads(raw[iid]["execution_result_content"])
        codes = dict(zip(doc["test_file_names"], doc["test_file_codes"]))
        expected_hidden = {f["path"]: f["sha256"] for f in g["hidden_test_files"]}
        actual_hidden = actual_files(prv / "hidden_tests")
        assert set(actual_hidden) == set(expected_hidden)
        for name, digest in expected_hidden.items():
            data = (prv / "hidden_tests" / name).read_bytes()
            assert "sha256:" + sha(data) == digest
            rr = [r for r in current_revs if r["target"] == name and r["kind"].startswith("hidden_test_")]
            source_data = (ROOT / rr[-1]["revised_file"]).read_bytes() if rr else codes[name].encode() if name in codes else (M3 / g["source_commit_hash"][:12] / "r2e_tests" / name).read_bytes()
            assert data == source_data, (iid, name)
        counts["hidden_files"] += len(actual_hidden)
        expected = raw[iid]["expected_output_json"]
        for r in current_revs:
            if r["kind"] == "expected_text_replace":
                for edit in r["edits"]:
                    assert expected.count(edit["old"]) == 1
                    expected = expected.replace(edit["old"], edit["new"])
            elif r["kind"] == "expected_file_replace":
                expected = (ROOT / r["revised_file"]).read_text()
        assert expected == g["expected_output_json"]

        man = load(pub / "worktree_manifest.json")
        wt = pub / "worktree"
        af = actual_files(wt)
        assert af == man["files"], (iid, "actual vs manifest")
        assert sha(json.dumps(af, sort_keys=True).encode()) == check["tasks"][iid]["worktree_digest"]
        assert man["instance_id"] == iid and man["base_commit"] == g["base_commit"] == p["base_commit"]
        repo = g["repo_key_lower"]
        entries = tree_entries(repo, g["base_commit"])
        assert git(repo, "rev-parse", g["base_commit"] + "^{tree}").decode().strip() == man["export"]["base_tree"]
        diffp = M3 / g["source_commit_hash"][:12] / "facts/initial.diff"
        diff = diffp.read_bytes()
        m3_head = (diffp.parent / "git_head.txt").read_text().splitlines()[1]
        assert m3_head == g["base_commit"]
        m3_run_sha = re.search(r"(?m)^([0-9a-f]{64})\s+/testbed/run_tests.sh$", (diffp.parent / "run_tests_meta.txt").read_text()).group(1)
        assert "sha256:" + m3_run_sha == g["run_tests_sh_sha256"]
        assert man["initial_diff"]["source"] == str(diffp.relative_to(ROOT))
        assert man["initial_diff"]["bytes"] == len(diff) and man["initial_diff"]["sha256"] == sha(diff)
        patched = replay_diff(diff, entries, repo)
        assert set(patched) == set(man["initial_diff"]["files"])
        for name, (mode, kind, oid) in entries.items():
            fp = wt / name
            if kind == "commit":
                assert mode == "160000" and fp.is_dir() and not fp.is_symlink() and not any(fp.iterdir())
                assert man["export"]["gitlinks"][name] == oid
                counts["gitlinks"] += 1
                continue
            assert kind == "blob"
            counts["base_blobs"] += 1
            if name in patched and patched[name] is None:
                assert not os.path.lexists(fp)
                counts["deleted_files"] += 1
                continue
            data = os.readlink(fp).encode() if fp.is_symlink() else fp.read_bytes()
            if name in patched:
                assert data == patched[name], (iid, name, "patched bytes")
                counts["patched_files"] += 1
            else:
                assert blob_sha(data) == oid, (iid, name, "base blob")
            assert fp.is_symlink() == (mode == "120000")
            if mode != "120000":
                assert bool(fp.stat().st_mode & 0o111) == (mode == "100755"), (iid, name, "executable")
        declared_untracked = (M3 / g["source_commit_hash"][:12] / "facts/untracked.txt").read_text().splitlines()[1:]
        names = declared_untracked[:declared_untracked.index("--count--")]
        assert names == man["untracked_in_image"]
        inc, missing = set(man["untracked_included"]), set(man["untracked_missing"])
        assert set(names) == inc | missing and not inc & missing
        assert (wt / "run_tests.sh").read_bytes() == g["run_tests_sh"].encode()
        assert set(af) == ({n for n, e in entries.items() if e[1] == "blob"} - {n for n, b in patched.items() if b is None}) | inc
        assert all(not os.path.lexists(wt / n) for n in missing)
        for name, f in af.items():
            if "symlink" in f:
                symlinks.append({"instance_id": iid, "path": name, "target": f["symlink"]})
        counts["tasks_with_missing_untracked"] += bool(missing)
        counts["missing_install_sh"] += "install.sh" in missing
        counts["missing_datasets"] += "datasets" in missing
        counts["missing_aiohttp_script"] += "process_aiohttp_updateasyncio.py" in missing
        counts["worktree_files"] += len(af)
        counts["dirty_tasks"] += bool(diff)
        counts["revision_entries"] += len(current_revs)
        for ref in load(hist / "refs.json").values():
            assert (ROOT / ref).exists(), (iid, ref)
        for ref in load(prv / "refs.json")["evidence_refs"]:
            cleaned = ref.split("（")[0].split(" ")[0]
            if not (ROOT / cleaned).exists():
                missing_ref_class["anchor_only" if (ROOT / cleaned.split("#")[0]).exists() else "actually_missing"] += 1
        rec = load(ROUND / "tasks" / iid / "screening_record.json")
        brief = (pub / "environment_brief.md").read_text()
        version = re.search(r"\b3\.\d+\.\d+\b", rec["solver_conditions"]["interpreter"]).group()
        assert f"Python {version}" in brief
        assert ("pip：有" in brief) == rec["solver_conditions"]["pip"].startswith("present")
        for pin in pins.get(iid, {}).get("pins", []):
            assert f"`{pin['dist']}` 固定为 {pin['version']}" in brief
        assert not any(x in brief for x in ("gold", "expected", "findings", "PASSED", "FAILED", "ERROR", "r2e-mr-"))
        tasks[iid] = {"base_commit": g["base_commit"], "worktree_files": len(af), "dirty_paths": sorted(patched), "untracked_missing": sorted(missing), "hidden_files": len(actual_hidden), "public_boundary": "all bytes accounted for by frozen public rows, neutral facts, git blobs, M3 diff and recorded untracked files"}

        hp = RUN / "image_files" / iid / "image_hashes.json"
        if hp.exists():
            image = load(hp)
            assert image["instance_id"] == iid and image["head"] == g["base_commit"]
            compared, mode = 0, []
            for name, f in image["files"].items():
                if f.get("deleted"):
                    assert name not in af
                elif f.get("other"):
                    assert name in man["export"]["gitlinks"]
                else:
                    e = af[name]
                    assert e.get("symlink") == f.get("symlink") and e.get("sha256") == f.get("sha256"), (iid, name, "image bytes")
                    compared += 1
                    if e.get("mode") != f.get("mode"):
                        mode.append({"path": name, "image": f.get("mode"), "export": e.get("mode")})
            assert not set(af) - set(image["files"])
            saved = check["image_verification"][iid]
            assert saved["identical"] == compared and saved["files_compared"] == len(image["files"]) and saved["mode_mismatch_count"] == len(mode) and saved["ok"]
            assert saved["image_id"] == image["image_id"] and saved["image_ref"] == image["image_ref"]
            overlay = latest_overlays.get(iid)
            source_image = p["image_manifest_digest"] == image["image_id"]
            image_reports[iid] = {"image_id": image["image_id"], "image_ref": image["image_ref"], "files_identical": compared, "mode_differences": mode, "latest_recipe_id": overlay["recipe_id"] if overlay else None, "latest_overlay_image_id": overlay["derived_image_id"] if overlay else None, "equals_latest_overlay": bool(overlay and overlay["derived_image_id"] == image["image_id"]), "is_source_image": source_image}
    assert set(check["image_verification"]) == set(image_reports)
    counts["tasks"] = len(ids)
    counts["image_hash_tasks"] = len(image_reports)
    counts["symlinks"] = len(symlinks)
    counts["current_image_hash_tasks"] = sum(r["equals_latest_overlay"] for r in image_reports.values())
    assert (SNAP / "material_check.json").read_bytes() == check_bytes
    result = {"schema_id": "rh2.r2e_static_materials_independent_review.v1", "status": "PASS", "scope": "只读：当前 trusted 摄入面与 v1 文件/manifest/base blob/M3 diff/本地 image_hashes；没有当前容器实测，没有质量审查", "counts": dict(counts), "input_identity": check["inputs"], "missing_reference_classification": dict(missing_ref_class), "tasks": tasks, "images": image_reports, "symlinks": symlinks}
    out = HERE / "probe_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "counts": result["counts"], "missing_refs": dict(missing_ref_class), "output": str(out.relative_to(ROOT))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
