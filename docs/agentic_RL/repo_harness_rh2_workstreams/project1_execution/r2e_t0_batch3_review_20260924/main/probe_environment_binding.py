"""Read-only review probe: current orange3 expected vs saved source/new overlays and logs.

Runs no container and changes no production code or historical evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root = args.repo_root.resolve()
    sys.path.insert(0, str(root / "rh2/src"))
    from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
    from repoharness2.adapters.slime.replay_grade import _overlay_static_mismatch
    from repoharness2.envpack.environment_overlay import load_environment_overlays
    from repoharness2.envpack.ingest_r2e_subset import load_trusted_r2e_ingest_outputs
    from repoharness2.envpack.training_view import HostGradingView

    iid = "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
    task_id = "r2e_gym_subset::" + iid
    trusted = load_trusted_r2e_ingest_outputs(root)
    grading = next(g for g in trusted.result.grading_bundles if g.instance_id == iid)
    public = next(g for g in trusted.result.public_bundles if g.instance_id == iid)
    package = next(g for g in trusted.result.packages if g.instance_id == iid)
    view = HostGradingView(
        task_id=task_id, source="r2e_gym_subset", instance_id=iid,
        environment_package_digest=package.digest(), grading_bundle_digest=grading.digest(),
        grading=grading,
    )
    inputs = {
        "source_environment": (
            "runs/r2e_rf_20260923/remote/r2e_derived/overlays.jsonl",
            "runs/r2e_rf_20260923/remote/ledger_r2e_all_gold_local_local.jsonl",
        ),
        "repaired_environment": (
            "runs/r2e_t0_batch3_20260924/derived7/overlays.jsonl",
            "runs/r2e_t0_batch3_20260924/reconcile/ledgers_local/ledger_b5_gold.jsonl",
        ),
    }
    results = {}
    for name, (overlay_path, ledger_path) in inputs.items():
        overlay = load_environment_overlays(root / overlay_path)[task_id]
        rows = [json.loads(line) for line in (root / ledger_path).read_text().splitlines() if line]
        row = next(r for r in rows if r["instance_id"] == iid)
        assert row["overlay"]["derived_image_id"] == overlay.derived_image_id
        raw = Path(row["log"]["path"]).read_bytes()
        assert "sha256:" + hashlib.sha256(raw).hexdigest() == row["log"]["sha256"]
        spec = build_grading_spec_from_host_view(
            view, image=overlay.derived_image_id, image_manifest_digest=overlay.derived_image_id,
        )
        verdict = spec.parse_log(raw.decode("utf-8", "replace"))
        results[name] = {
            "overlay_file": overlay_path, "ledger_file": ledger_path,
            "log_sha256": row["log"]["sha256"], "recipe_id": overlay.recipe_id,
            "recipe_sha256": overlay.recipe_sha256,
            "overlay_static_mismatch": _overlay_static_mismatch(
                overlay, public=public, gview=view, shadowed=False,
            ),
            "original_recorded_reward": row["report"]["reward"],
            "current_expected_reward": verdict.reward,
            "current_expected_match": verdict.expected_match.model_dump(mode="json"),
        }
    result = {
        "task_id": task_id, "current_material_revisions": grading.material_revisions,
        "grading_bundle_digest": grading.digest(),
        "scope": "Existing log replay and production static overlay check; no new Docker run.",
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
