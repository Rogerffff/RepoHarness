"""第二批 v2 材料运输的独立本机探针；不写生产、测试、材料或历史 evidence。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))

from repoharness2.adapters.slime.r2e_grading_scripts import build_r2e_grading_spec, r2e_official_files
from repoharness2.envpack import ingest_r2e_subset as r2e
from repoharness2.grading.manager import grading_scripts_digest

DOCS = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e"
RUN = ROOT / "runs/r2e_t0_batch2_20260924"
IIDS = (
    "pandas__4ec87eb94bc8fb1f93d37b7dd5de34f6e419a199",
    "scrapy__cfed9b6659c90e0799361911b1d72ed127edf471",
)


def sha(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def rejected(fn, message: str) -> str:
    try:
        fn()
    except r2e.R2EIngestError as exc:
        assert message in str(exc), str(exc)
        return str(exc)
    raise AssertionError("应拒绝的材料被接受")


def main() -> dict:
    trusted = r2e.load_trusted_r2e_ingest_outputs(ROOT)
    rows, source_revision = r2e.load_r2e_rows(ROOT, trusted.pins)
    by_row = {f"{r['repo_name']}__{r['commit_hash']}": r for r in rows}
    rebuilt = r2e.ingest_r2e_subset(
        rows=rows, image_facts=trusted.image_facts,
        raw_archive_sha256="sha256:" + trusted.pins.raw_archive,
        image_facts_sha256="sha256:" + trusted.pins.image_facts,
        source_revision=source_revision, revisions=trusted.revisions,
    )
    changes = {}
    for field, filename in (
        ("packages", "environment_packages_v0.jsonl"),
        ("public_bundles", "public_bundles_v0.jsonl"),
        ("grading_bundles", "grading_bundles_r2e_v0.jsonl"),
        ("validation_bundles", "validation_bundles_v0.jsonl"),
    ):
        models = getattr(rebuilt, field)
        body = "".join(json.dumps(m.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n" for m in models).encode()
        current = (DOCS / "ingest" / filename).read_bytes()
        assert body == current, filename
        old_lines = (DOCS / "ingest_history/material_v1_20260924" / filename).read_bytes().splitlines()
        new_lines = current.splitlines()
        assert len(old_lines) == len(new_lines) == 48
        changed = [json.loads(a)["instance_id"] for a, b in zip(old_lines, new_lines) if a != b]
        assert set(changed) == (set(IIDS) if field in ("packages", "grading_bundles") else set())
        changes[filename] = {"rebuild_exact": True, "changed": changed, "unchanged_count": 48 - len(changed)}

    spec = importlib.util.spec_from_file_location("review_build_r2e_derived", ROOT / "rh2/scripts/build_r2e_derived.py")
    build = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    try:
        spec.loader.exec_module(build)
    finally:
        sys.path[:] = saved_path
    gradings = {g.instance_id: g for g in rebuilt.grading_bundles}
    publics = {p.instance_id: p for p in rebuilt.public_bundles}
    prepared = {d["instance_id"]: d for d in jsonl(RUN / "replay_b3/private/host_grading_views.jsonl")}
    ledger = jsonl(RUN / "replay_b3/ledger_b3_noop_local.jsonl") + jsonl(RUN / "replay_b3/ledger_b3_gold_local.jsonl")
    assert len(ledger) == 8
    tasks = {}
    for iid in IIDS:
        g, p, revs = gradings[iid], publics[iid], trusted.revisions[iid]
        assert prepared[iid]["grading"] == g.model_dump(mode="json")
        assert prepared[iid]["grading_bundle_digest"] == g.digest()
        fact = trusted.image_facts[g.source_commit_hash]
        originals = dict(fact.hidden_files)
        for rev in revs:
            if rev.revised_file:
                assert sha((ROOT / rev.revised_file).read_bytes()) == rev.sha256_after
            if rev.kind == r2e.REVISION_KIND_HIDDEN_ADD:
                assert rev.target not in originals and rev.sha256_before is None
        before, after = json.loads(by_row[iid]["expected_output_json"]), g.expected_map()
        expected_revs = [r for r in revs if r.kind in r2e.EXPECTED_REVISION_KINDS]
        assert len(expected_revs) == 1
        delta = r2e.R2EExpectedChange.diff(before, after)
        assert delta == expected_revs[0].expected_change
        hidden_revs = [r for r in revs if r.kind in r2e.HIDDEN_REVISION_KINDS]
        manifest = build.material_manifest(hidden_revs)
        recipe = build.material_recipe_digest(manifest)
        facts = json.loads((RUN / "derived3" / iid / "facts.json").read_text())
        assert facts["ok"] and not facts["failures"] and facts["recipe_sha256"] == recipe
        assert facts["material_revisions"] == [r.revision_id for r in hidden_revs]
        rf = facts["root_facts"]
        assert "sha256:" + rf["tree"] == g.hidden_tests_tree_sha256
        assert rf["private_owner"] == "root:root" and rf["private_mode"] == "700"
        assert rf["r2e_tests_root"] == rf["r2e_tests_workdir"] == "absent"
        for user in ("agent_uid_facts", "grader_uid_facts"):
            assert facts[user]["private_ls"] == facts[user]["private_cat"] == "denied"
        build_log = (RUN / "derived3" / iid / "build.log").read_text()
        assert f"RH2_MATERIAL_TREE={rf['tree']}" in build_log and "RH2_MATERIAL_OK=1" in build_log
        for rev in hidden_revs:
            verb = "ADDED" if rev.kind == r2e.REVISION_KIND_HIDDEN_ADD else "APPLIED"
            assert f"RH2_MATERIAL_{verb}={rev.target}" in build_log
        grading_spec = build_r2e_grading_spec(task_id="r2e_gym_subset::" + iid, grading=g,
                                            image=facts["tag"], image_manifest_digest=p.image_manifest_digest)
        script_hash = grading_scripts_digest(grading_spec)
        count = len(r2e_official_files(g))
        observations = []
        for row in (r for r in ledger if r["instance_id"] == iid):
            assert row["image_id_actual"] == facts["derived_image_id"]
            assert row["overlay"]["recipe_sha256"] == recipe
            assert row["scripts_digest"] == script_hash
            log = RUN / "replay_b3/eval_logs" / Path(row["log"]["path"]).name
            diag = json.loads((RUN / "replay_b3/eval_logs" / Path(row["diagnostics_ref"]).name).read_text())
            text = log.read_text()
            assert f"RH2_SETUP_HIDDEN_TESTS_TREE={rf['tree']}" in text
            assert f"RH2_SETUP_ENTRY_SHA256={g.run_tests_sh_sha256.removeprefix('sha256:')}" in text
            assert diag["scripts_digest"] == script_hash
            assert diag["trusted_setup"]["RH2_SETUP_OK"] == "1"
            assert diag["trusted_setup"]["RH2_SETUP_EXPECTED_TEST_FILES"] == str(count)
            assert diag["control_surface"]["RH2_PROTECT_OK"] == "1"
            assert diag["control_surface"]["EXPECTED_FILES"] == diag["control_surface"]["PROTECTED_FILES"] == str(count)
            assert diag["control_surface"]["MISSING_FILES_COUNT"] == "0"
            assert diag["control_surface"]["IRREGULAR_FILES"] == ""
            verdict = grading_spec.parse_log(text)
            assert verdict.expected_match.model_dump(mode="json") == diag["verdict"]["expected_match"]
            assert verdict.expected_match.match_count == row["report"]["expected_match"]
            assert verdict.expected_match.total_count == row["report"]["expected_total"]
            assert int(verdict.resolved) == row["report"]["reward"]
            observations.append({"candidate": row["candidate"]["kind"], "attempt": row["attempt"],
                                 "match": verdict.expected_match.match_count, "total": verdict.expected_match.total_count,
                                 "log": str(log.relative_to(ROOT)), "protected_files": count})
        assert len(observations) == 4
        tasks[iid] = {"expected_delta": asdict(delta), "manifest": manifest.decode(), "recipe_sha256": recipe,
                      "hidden_tree": g.hidden_tests_tree_sha256, "image_id": facts["derived_image_id"],
                      "scripts_digest": script_hash, "observations": observations}

    pandas_revs = trusted.revisions[IIDS[0]]
    exp = next(r for r in pandas_revs if r.kind == r2e.REVISION_KIND_EXPECTED_FILE)
    modified = json.loads(exp.revised_content)
    modified["undeclared_review_probe"] = "PASSED"
    content = json.dumps(modified).encode()
    injected = replace(exp, revised_content=content, sha256_after=sha(content))
    expected_rejection = rejected(
        lambda: r2e.apply_expected_revisions(IIDS[0], by_row[IIDS[0]]["expected_output_json"], (injected,)),
        "expected_change 不符",
    )
    scrapy_add = next(r for r in trusted.revisions[IIDS[1]] if r.kind == r2e.REVISION_KIND_HIDDEN_ADD)
    fact = trusted.image_facts[gradings[IIDS[1]].source_commit_hash]
    existing = replace(scrapy_add, target="test_1.py")
    add_rejection = rejected(
        lambda: r2e.apply_hidden_test_revisions(IIDS[1], fact.hidden_files, {}, (existing,)), "已存在",
    )
    return {"status": "pass", "trusted_task_count": len(trusted.result.packages), "artifact_comparison": changes,
            "tasks": tasks, "failure_boundaries": {"undeclared_expected_key": expected_rejection, "add_existing_file": add_rejection},
            "scope": "本机读现有材料与 evidence；未起 Docker、未访问远端；未审 reconcile。"}


if __name__ == "__main__":
    result = main()
    Path(__file__).with_name("probe_transport.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "tasks": len(result["tasks"]), "trusted_task_count": result["trusted_task_count"],
                      "ledger_rows": sum(len(t["observations"]) for t in result["tasks"].values()), "failure_boundaries": len(result["failure_boundaries"])}, ensure_ascii=False))
