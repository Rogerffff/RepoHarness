"""独立窄复核：真实摄入/prepared/评分接缝；Docker 仅用替身，不启动容器。"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / "rh2").is_dir())
for directory in (ROOT / "rh2/src", ROOT / "rh2/tests", ROOT / "rh2/tests/adapters", ROOT / "rh2/tests/grading"):
    sys.path.insert(0, str(directory))

from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace, build_grading_spec_from_host_view
from repoharness2.adapters.slime.replay_grade import CandidateInput, ReplayBudgets, ReplayGrader, load_context, prepare_for_replay
from repoharness2.envpack import ingest_r2e_subset as r2e
from repoharness2.envpack import ingest_swegym_lite as swe
from repoharness2.envpack.environment_overlay import EnvironmentOverlayV1
from repoharness2.envpack.prepared_tasks import HOST_GRADING_FILE
from repoharness2.envpack.training_view import TrustedTaskController
from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager, grading_scripts_digest
from sandbox_test_support import make_grader_profile, make_rollout_profile
from test_r2e_replay_overlay import FAKE_IMAGE_ID, R2EProfileDriverDocker
from test_w3b_grader_profile_unit import GOOD_SETUP_ATTEST


S2 = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e"
RUN = ROOT / "runs/r2e_t0_revisions_20260924"
COV = "coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae"
DAT = "datalad__58ba5165234cb16de0e8463ee75097362099835f"
NUM = "numpy__43e333e2ff641f6dce852e46c9c650333b0d4b3d"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def refusal(fn, contains):
    try:
        fn()
    except Exception as exc:
        assert contains in str(exc), (contains, str(exc))
        return {"exception": type(exc).__name__, "matched": contains}
    raise AssertionError(f"未拒绝：{contains}")


def spec_for(ctx, tid):
    public = ctx.rollout_views[tid].public
    return build_grading_spec_from_host_view(ctx.grading_views[tid], image=public.image,
                                           image_manifest_digest=public.image_manifest_digest)


async def main():
    evidence = {}
    trusted = r2e.load_trusted_r2e_ingest_outputs(ROOT)
    source_rows, revision = r2e.load_r2e_rows(ROOT, trusted.pins)
    replayed = r2e.ingest_r2e_subset(
        rows=source_rows, image_facts=trusted.image_facts, raw_archive_sha256="sha256:" + trusted.pins.raw_archive,
        image_facts_sha256="sha256:" + trusted.pins.image_facts, source_revision=revision, revisions=trusted.revisions,
    )
    for name in ("public_bundles", "grading_bundles", "validation_bundles", "packages"):
        assert [m.model_dump(mode="json") for m in getattr(replayed, name)] == [m.model_dump(mode="json") for m in getattr(trusted.result, name)]
    evidence["trusted_ingest"] = {"count": len(replayed.packages), "pins": vars(trusted.pins),
        "all_four_faces_reproduced": True, "manifest_sha256": sha(S2 / "ingest/ingest_manifest_v0.json")}

    old = S2 / "ingest_history/source_v0_20260923"
    old_g = {r["instance_id"]: r for r in rows(old / "grading_bundles_r2e_v0.jsonl")}
    cur_g = {g.instance_id: g for g in trusted.result.grading_bundles}
    public_same = (old / "public_bundles_v0.jsonl").read_bytes() == (S2 / "ingest/public_bundles_v0.jsonl").read_bytes()
    validation_same = (old / "validation_bundles_v0.jsonl").read_bytes() == (S2 / "ingest/validation_bundles_v0.jsonl").read_bytes()
    changes = {}
    for iid, g in cur_g.items():
        now = g.model_dump(mode="json")
        del now["material_revisions"]
        changed = [k for k in sorted(now) if now[k] != old_g[iid][k]]
        if changed:
            changes[iid] = changed
    assert set(changes) == {COV, DAT}
    assert changes[COV] == ["expected_output_json", "expected_output_json_sha256"]
    assert changes[DAT] == ["hidden_test_files", "hidden_tests_tree_sha256"]
    assert public_same and validation_same
    old_p = {p["instance_id"]: p for p in rows(old / "environment_packages_v0.jsonl")}
    package_changes = {p.instance_id: [k for k, v in p.model_dump(mode="json").items() if v != old_p[p.instance_id][k]]
                       for p in trusted.result.packages}
    assert all(v == ["grading_bundle_digest"] for v in package_changes.values())
    assert all(not cur_g[iid].material_revisions for iid in cur_g if iid not in {COV, DAT})
    evidence["historical_comparison"] = {"public_bytes_equal": public_same, "validation_bytes_equal": validation_same,
        "domain_changes": changes, "unchanged_material_tasks": 46, "untouched_by_all_three_interventions": 45,
        "package_digest_changed_count": len(package_changes), "package_only_changed_field": "grading_bundle_digest",
        "note": "所有48包摘要变化；46题由新增空 material_revisions 字段引起，内容仅两题修订。numpy43环境配方不改摄入材料。"}

    with tempfile.TemporaryDirectory(prefix="probe_", dir=OUT) as temp:
        temp = Path(temp)
        rebuilt = temp / "ingest"
        digests = r2e.write_r2e_ingest_outputs(replayed, rebuilt, pins=trusted.pins, revisions=trusted.revisions)
        assert digests[r2e.R2E_INGEST_MANIFEST_NAME] == r2e.R2E_INGEST_MANIFEST_SHA256_PIN
        evidence["r2e_reserialization_manifest_identical"] = True
        sw = swe.load_trusted_ingest_outputs(ROOT)
        sw_digests = swe.write_ingest_outputs(sw.result, temp / "swe", pins=sw.pins)
        assert sw_digests[swe.INGEST_MANIFEST_NAME] == swe.INGEST_MANIFEST_SHA256_PIN
        assert len(TrustedTaskController.from_repo_root(ROOT).task_ids()) == 216
        evidence["swe_compatibility"] = {"count": len(sw.result.packages), "manifest_and_four_files_identical": True,
            "default_controller_count": 216, "material_revisions_field_in_swe": False}

        summary = prepare_for_replay(repo_root=ROOT, out_dir=temp / "prepared", private_dir=temp / "private",
                                     task_ids=None, sources=("r2e_gym_subset",))
        face = PreparedTaskFace.load(prepared_dir=temp / "prepared", manifest_sha256=summary["prepared_manifest_sha256"],
            host_grading_path=temp / "private" / HOST_GRADING_FILE,
            host_grading_sha256=summary["host_grading_artifact_sha256"], time_budget_seconds=60)
        ctx = load_context(prepared_dir=temp / "prepared", private_dir=temp / "private",
            manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=make_rollout_profile(),
            grader_profile=make_grader_profile(), artifacts_dir=temp / "artifacts")
        assert len(face.task_ids()) == 48
        for tid in face.task_ids():
            assert ctx.grading_views[tid].grading == cur_g[ctx.grading_views[tid].instance_id]
            rec = face.manifest.record(tid)
            assignment = SimpleNamespace(task_id=tid, environment_package_digest=rec.environment_package_digest,
                                         public_bundle_digest=rec.public_bundle_digest)
            spec = face.grading_spec(assignment)
            assert spec.grading_semantics == "r2e_expected_map"
            public_dump = face.rollout_spec(tid).public_bundle_payload.decode()
            assert "material_revisions" not in public_dump and "r2e-mr-" not in public_dump
        for name in ("prompts.jsonl", "rollout_task_views.jsonl"):
            payload = (temp / "prepared" / name).read_text()
            assert "material_revisions" not in payload and "r2e-mr-" not in payload
            assert all(g.expected_output_json not in payload for g in cur_g.values())
        evidence["prepared_live_chain"] = {"tasks": 48, "grading_views_round_trip": True,
            "both_spec_factories": True, "no_revision_content_in_solver_payload": True}

        archived_summary = json.loads((RUN / "replay/prepared_r2e/replay_summary.json").read_text())
        archived_ctx = load_context(prepared_dir=RUN / "replay/prepared_r2e", private_dir=RUN / "replay/private_r2e",
            manifest_sha256=archived_summary["prepared_manifest_sha256"], rollout_profile=make_rollout_profile(),
            grader_profile=make_grader_profile(), artifacts_dir=temp / "unused")
        assert archived_ctx.grading_views == ctx.grading_views
        assert archived_ctx.rollout_views == ctx.rollout_views
        assert (RUN / "replay/private_r2e" / HOST_GRADING_FILE).read_bytes() == (temp / "private" / HOST_GRADING_FILE).read_bytes()
        evidence["archived_prepared_binding"] = {"manifest_sha256": archived_summary["prepared_manifest_sha256"],
            "host_grading_sha256": archived_summary["host_grading_artifact_sha256"], "matches_current_all_48": True}

        archived_overlays = {r["task_id"]: EnvironmentOverlayV1.model_validate(r) for r in rows(RUN / "derived/overlays.jsonl")}
        archived_rows = []
        for filename in ("ledger_t0_noop.jsonl", "ledger_t0_gold.jsonl", "ledger_env43_noop.jsonl", "ledger_env43_gold.jsonl"):
            archived_rows.extend(rows(RUN / "replay" / filename))
        assert len(archived_rows) == 12
        parsed = []
        for row in archived_rows:
            tid = row["task_id"]
            log_path = RUN / "replay/eval_logs" / Path(row["log"]["path"]).name
            assert "sha256:" + sha(log_path) == row["log"]["sha256"]
            log = log_path.read_text(errors="replace")
            spec = spec_for(archived_ctx, tid)
            verdict = spec.parse_log(log)
            assert verdict.resolved == bool(row["report"]["reward"])
            match = verdict.expected_match
            assert (match.match_count, match.expected_count) == (row["report"]["expected_match"], row["report"]["expected_total"])
            assert grading_scripts_digest(spec) == row["scripts_digest"]
            diag_path = RUN / "replay/eval_logs" / Path(row["diagnostics_ref"]).name
            diag = json.loads(diag_path.read_text())
            assert diag["scripts_digest"] == row["scripts_digest"]
            assert row["report"]["grading_semantics"] == "r2e_expected_map"
            assert row["stage_error"] is None and row["cleanup"]["removed"] is True
            assert row["overlay"]["derived_image_id"] == archived_overlays[tid].derived_image_id
            parsed.append({"instance_id": row["instance_id"], "candidate": row["candidate"]["kind"],
                "attempt": row["attempt"], "reward": row["report"]["reward"], "match": match.match_count,
                "total": match.expected_count, "log_sha256": row["log"]["sha256"], "scripts_digest": row["scripts_digest"]})
        evidence["archived_reports_recomputed"] = parsed

        refusals = {}
        for iid in (COV, DAT):
            i = next(i for i, p in enumerate(trusted.result.packages) if p.instance_id == iid)
            args = (trusted.result.packages[i], trusted.result.public_bundles[i], trusted.result.grading_bundles[i], trusted.result.validation_bundles[i])
            refusals[iid + ":missing_revisions"] = refusal(lambda: r2e.verify_r2e_package_relations(
                *args, pins=trusted.pins, image_facts=trusted.image_facts), "修订标记")
        cov_tid = "r2e_gym_subset::" + COV
        rec = face.manifest.record(cov_tid)
        old_digest = "sha256:" + hashlib.sha256(json.dumps(old_p[COV], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        assert old_digest != rec.environment_package_digest
        assignment = SimpleNamespace(task_id=cov_tid, environment_package_digest=old_digest, public_bundle_digest=rec.public_bundle_digest)
        refusals["stale_environment_package_digest"] = refusal(lambda: face.grading_spec(assignment), "分派 digest")

        runtime_cases = []
        for iid in (COV, DAT):
            tid = "r2e_gym_subset::" + iid
            public = ctx.rollout_views[tid].public
            for kind in ("noop", "gold"):
                original = next(r for r in archived_rows if r["instance_id"] == iid and r["candidate"]["kind"] == kind)
                fake = R2EProfileDriverDocker(base_commit=public.base_commit, image_present=True)
                fake.eval_log = (RUN / "replay/eval_logs" / Path(original["log"]["path"]).name).read_text(errors="replace")
                count = str(len(cur_g[iid].hidden_test_files) + 1)
                fake.setup_attest = {**GOOD_SETUP_ATTEST, "RH2_SETUP_EXPECTED_TEST_FILES": count, "RH2_SETUP_TEST_FILES": count}
                overlay = archived_overlays[tid].model_copy(update={"derived_image_id": FAKE_IMAGE_ID})
                case = temp / (iid[:20] + kind)
                rt = load_context(prepared_dir=temp / "prepared", private_dir=temp / "private",
                    manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=make_rollout_profile(),
                    grader_profile=make_grader_profile(), artifacts_dir=case / "artifacts", docker=fake,
                    image_overlays={tid: overlay})
                manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=case / "logs", sandbox_profile=make_grader_profile()), docker=fake)
                driver = ReplayGrader(rt, manager, ledger_path=case / "ledger.jsonl",
                    budgets=ReplayBudgets(candidate_stage_seconds=30, grading_deadline_seconds=30, cleanup_seconds=5))
                # 候选材料不在替身里执行；给真实生产 manager 注入归档的候选日志来验证版本/编排/判分接缝。
                observed = await driver.replay_one(tid, CandidateInput(kind="noop", origin="transport-probe-archived-log"))
                assert observed["stage_error"] is None, observed["stage_error"]
                assert observed["report"]["reward"] == original["report"]["reward"], observed
                assert observed["report"]["expected_match"] == original["report"]["expected_match"]
                payloads = [payload.decode("utf-8", "replace") for _, payload in fake.input_payloads]
                assert any(cur_g[iid].hidden_tests_tree_sha256.removeprefix("sha256:") in p for p in payloads)
                assert any("bash run_tests.sh" in p for p in payloads)
                runtime_cases.append({"instance_id": iid, "injected_log_kind": kind, "reward": observed["report"]["reward"],
                    "expected_match": observed["report"]["expected_match"], "candidate_container_removed": observed["cleanup"]["removed"]})
                closed = await manager.close()
                assert not closed["containers_open"]

        tid = "r2e_gym_subset::" + DAT
        public = ctx.rollout_views[tid].public
        fake = R2EProfileDriverDocker(base_commit=public.base_commit, image_present=True)
        overlay = archived_overlays[tid].model_copy(update={"derived_image_id": FAKE_IMAGE_ID,
            "facts": archived_overlays[tid].facts.model_copy(update={"hidden_tests_tree_sha256": old_g[DAT]["hidden_tests_tree_sha256"]})})
        stale_ctx = load_context(prepared_dir=temp / "prepared", private_dir=temp / "private",
            manifest_sha256=summary["prepared_manifest_sha256"], rollout_profile=make_rollout_profile(),
            grader_profile=make_grader_profile(), artifacts_dir=temp / "stale_artifacts", docker=fake, image_overlays={tid: overlay})
        manager = SWEGradingManager(GradingManagerConfig(sandbox_profile=make_grader_profile()), docker=fake)
        driver = ReplayGrader(stale_ctx, manager, ledger_path=temp / "stale_ledger.jsonl")
        stale_row = await driver.replay_one(tid, CandidateInput(kind="noop", origin="probe"))
        assert stale_row["stage_error"] == "overlay:hidden_tests_tree_mismatch"
        assert stale_row["report"] is None and not fake.calls
        await manager.close()
        refusals["old_datalad_overlay"] = {"stage_error": stale_row["stage_error"], "docker_calls": len(fake.calls)}
        evidence["refusal_probes"] = refusals
        evidence["real_driver_and_manager_with_fake_docker"] = runtime_cases

    mod_spec = importlib.util.spec_from_file_location("review_r2e_build", ROOT / "rh2/scripts/build_r2e_derived.py")
    build = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(build)
    revs = list(trusted.revisions[DAT])
    facts = json.loads((RUN / "derived" / DAT / "facts.json").read_text())
    assert facts["recipe_sha256"] == build.material_recipe_digest(build.material_manifest(revs))
    assert facts["material_revisions"] == ["r2e-mr-002"]
    assert facts["root_facts"]["tree"] == cur_g[DAT].hidden_tests_tree_sha256.removeprefix("sha256:")
    revised_file = ROOT / trusted.revisions[DAT][0].revised_file
    assert sha(revised_file) == trusted.revisions[DAT][0].sha256_after.removeprefix("sha256:")
    build_log = (RUN / "derived" / DAT / "build.log").read_text(errors="replace")
    assert "RH2_MATERIAL_APPLIED=test_1.py" in build_log and "RH2_MATERIAL_OK=1" in build_log
    assert "RH2_MATERIAL_TREE=" + facts["root_facts"]["tree"] in build_log
    evidence["material_build_binding"] = {"recipe_sha256": facts["recipe_sha256"],
        "hidden_tree_sha256": cur_g[DAT].hidden_tests_tree_sha256, "revised_file_sha256": "sha256:" + sha(revised_file),
        "root_private_mode": facts["root_facts"]["private_mode"], "recorded_material_script_succeeded": True,
        "archival_limit": "本机只归档build.log/facts/integrity，未归档Docker context；脚本与清单组合摘要对事实表、修订全文对受信修订单。"}
    (OUT / "transport_probe.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ok": True, "checks": list(evidence), "real_archived_reports": len(parsed),
                      "fake_runtime_cases": len(runtime_cases)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
