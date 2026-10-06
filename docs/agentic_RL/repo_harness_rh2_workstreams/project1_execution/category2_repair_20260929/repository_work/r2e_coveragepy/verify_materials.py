"""轻量核对草案、补丁和已归档日志；不启动项目、镜像或正式评分。"""

import ast
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from repoharness2.envpack.ingest_r2e_subset import (
    apply_expected_revisions, apply_hidden_test_revisions, apply_statement_revisions,
    parse_r2e_material_revisions,
)
from repoharness2.envpack.r2e_parsers import normalize_status_map, parse_log_pytest
from repoharness2.envpack.scoring import expected_map_matches

BASE = Path(__file__).resolve().parent
REPO = next(p for p in BASE.parents if (p / "rh2/src/repoharness2").is_dir())
EXEC = REPO / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
PRIV = REPO / "runs/r2e_static_prep_20260924/v3/private"
PUB = REPO / "runs/r2e_static_prep_20260924/v3/public"
CLOUD = REPO / "rh2/experiments/category3_cloud_20260929"


def digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def readj(path):
    return json.loads(path.read_bytes())


def match(expected, body):
    observed = normalize_status_map(parse_log_pytest(body))
    result = expected_map_matches(normalize_status_map(expected), observed)
    return {
        "reward": int(result.keys_equal and result.match_count == result.total_count),
        "expected_keys": len(expected), "observed_keys": len(observed),
        "mismatch": {k: [v, observed.get(k)] for k, v in expected.items() if observed.get(k) != v},
        "unexpected": sorted(set(observed) - set(expected)),
    }


def check_patch(iid, path):
    body = path.read_text()
    names = re.findall(r"^--- a/(.+)$", body, re.M)
    assert names, f"补丁没有原文件：{path}"
    with tempfile.TemporaryDirectory(prefix="coveragepy_patch_") as temp:
        tree = Path(temp)
        for name in names:
            assert not name.startswith("/") and ".." not in Path(name).parts
            source = PUB / iid / "worktree" / name
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        result = subprocess.run(["git", "apply", "--check", "--whitespace=nowarn", str(path)],
            cwd=tree, text=True, capture_output=True)
    assert result.returncode == 0, f"补丁无法应用：{path}\n{result.stderr}"
    return {"patch": str(path.relative_to(REPO)), "sha256": digest(path.read_bytes()), "applies": True}


def main():
    manifests = [readj(f / "results_manifest.json") for f in sorted((BASE / "tasks").iterdir())]
    registry = REPO / manifests[0]["parent_registry"]
    parent_bytes = registry.read_bytes()
    assert all(digest(parent_bytes) == m["parent_registry_sha256"] for m in manifests)
    parent = json.loads(parent_bytes)
    removed = {r for m in manifests for r in m["replace_revision_ids"]}
    merged = {**parent, "revisions": [r for r in parent["revisions"] if r["revision_id"] not in removed]}
    local_files = {}
    for m in manifests:
        folder = BASE / "tasks" / m["instance_id"]
        merged["revisions"].extend(readj(folder / "revision_draft.json")["revisions"])
        local_files.update(m["publication_files"])
        for item in m["materials"]:
            assert digest((REPO / item["path"]).read_bytes()) == item["sha256"]
            if item["path"].endswith(".py"):
                ast.parse((REPO / item["path"]).read_text(), feature_version=(3, 7))
    parsed = parse_r2e_material_revisions(merged)
    output = {"as_of": "2026-10-03", "status": "passed", "scope": "local_static_only",
        "cpu_experiments_run": False, "formal_grading_run": False, "published": False,
        "parent_registry_sha256": digest(parent_bytes), "tasks": {}, "historical_log_readback": {}}
    for m in manifests:
        iid = m["instance_id"]
        folder = BASE / "tasks" / iid
        loaded = []
        for rev in parsed[iid]:
            if rev.revised_file:
                path = REPO / local_files.get(rev.revised_file, rev.revised_file)
                body = path.read_bytes()
                assert digest(body) == rev.sha256_after
                rev = replace(rev, revised_content=body)
            loaded.append(rev)
        revs = tuple(loaded)
        original = {p.name: p.read_text() for p in (PRIV / iid / "hidden_tests").glob("*.py")}
        hidden = tuple((name, digest(body.encode())) for name, body in original.items())
        applied_hidden = dict(apply_hidden_test_revisions(iid, hidden, original, revs))
        expected_source = (PRIV / iid / "expected_output.json").read_text()
        # 016 的 v3 导出已含 001；先逐字还原来源，再从来源重放，不叠加修订。
        old = [r for r in revs if r.revision_id == "r2e-mr-001"]
        if old:
            assert digest(expected_source.encode()) == old[0].sha256_after
            for before, after in reversed(old[0].edits):
                assert expected_source.count(after) == 1
                expected_source = expected_source.replace(after, before, 1)
            assert digest(expected_source.encode()) == old[0].sha256_before
        expected = json.loads(apply_expected_revisions(iid, expected_source, revs))
        public = readj(PUB / iid / "public_bundle.json")["row"]
        statement = apply_statement_revisions(iid, public["problem_statement"], revs)
        patches = [check_patch(iid, REPO / r["patch"]) for r in readj(folder / "cpu_matrix.json")["rows"] if r["patch"]]
        details = {"revision_schema_and_replay": "passed", "python_syntax": "Python 3.7 grammar passed",
            "effective_expected_keys": len(expected), "effective_hidden_files": applied_hidden,
            "effective_statement_sha256": digest(statement.encode()), "candidate_patch_checks": patches}
        if "5dbbe143" in iid:
            assert len(expected) == 76
            for r in readj(folder / "cpu_matrix.json")["rows"]:
                if r.get("historical_reconstruction"):
                    details.setdefault("original_vs_reconstructed_ce", {})[r["candidate"]] = {
                        "same_bytes": (REPO / r["patch"]).read_bytes() == (REPO / r["historical_reconstruction"]).read_bytes(),
                        "selected": "original_patch",
                    }
        output["tasks"][iid] = details

    # 016：重读已归档 v2 日志；不是新实验，不声称 actor 或正式入口通过。
    iid = next(m["instance_id"] for m in manifests if "016af5f6" in m["instance_id"])
    archive = EXEC / "category3_diagnosis_20260929/tasks" / iid / "evidence/revised_v2"
    grades = [json.loads(s) for s in (archive / "grades.jsonl").read_text().splitlines()]
    expected = readj(CLOUD / "cov016/expected_output.json")
    checked = []
    for old in grades:
        log = archive / old["variant"] / "h2_rev2.out"
        result = match(expected, log.read_text(errors="replace"))
        assert result["reward"] == int(old["h2_rev2"]["reward"])
        assert result["mismatch"] == old["h2_rev2"]["mismatch"] and not result["unexpected"]
        checked.append({"candidate": old["variant"], "log": str(log.relative_to(REPO)),
            "log_sha256": digest(log.read_bytes()), **result})
    output["historical_log_readback"]["016af5f6"] = checked
    # f5eb：只重读最终 rb3h；较早 rb3 的 subset 缺口不能混入最终结果。
    grades = [json.loads(s) for s in (CLOUD / "cov_f5eb/review/grades.jsonl").read_text().splitlines()]
    expected = readj(CLOUD / "cov_f5eb/review/materials/expected_rc3.json")
    checked = []
    for old in grades:
        if old["material"] != "rb3h":
            continue
        log = CLOUD / "cov_f5eb/review/logs" / f'{old["tag"]}__{old["cand"]}.log'
        sections = [m for m in re.finditer(r"=====BEGIN (\S+) (\S+)\n(.*?)=====END \1 rc=(\d+)",
            log.read_text(), re.S) if m.group(1) == "rb3h"]
        assert len(sections) == 1
        section = sections[0]
        assert section.group(2) == hashlib.sha256((CLOUD / "cov_f5eb/review/materials/test_1_rb3h.py").read_bytes()).hexdigest()[:12]
        result = match(expected, section.group(3))
        result.update({"material": "rb3h", "test_sha12": section.group(2), "pytest_rc": int(section.group(4))})
        assert result["reward"] == old["rh2_reward"] and result["mismatch"] == old["mismatch"]
        checked.append({"candidate": old["cand"], "log": str(log.relative_to(REPO)),
            "log_sha256": digest(log.read_bytes()), **result})
    output["historical_log_readback"]["f5eb5f21"] = checked
    assert registry.read_bytes() == parent_bytes
    path = BASE / "static_checks.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "passed", "task_count": len(output["tasks"]),
        "patches": sum(len(v["candidate_patch_checks"]) for v in output["tasks"].values()),
        "historical_logs": {k: len(v) for k, v in output["historical_log_readback"].items()},
        "shared_registry_changed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
