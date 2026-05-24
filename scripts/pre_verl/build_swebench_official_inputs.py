#!/usr/bin/env python
"""Build SWE-bench official harness dataset and predictions from RepoHarness runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repo_harness.workspace.patch_hygiene import (
    PATCH_HYGIENE_POLICY_VERSION,
    classify_patch_path,
    patch_hygiene_invalid_reason,
)


_PATCH_CONTENT_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("hidden_selector_marker", re.compile(r"\b(?:FAIL_TO_PASS|PASS_TO_PASS)\b")),
    ("hidden_patch_marker", re.compile(r"\b(?:test_patch|gold_patch|hidden_verifier|hidden_test)\b", re.IGNORECASE)),
    ("hidden_reward_marker", re.compile(r"\b(?:reward_metadata|reward_extra_info|provider_secret)\b", re.IGNORECASE)),
    ("repo_harness_run_path", re.compile(r"(?:^|[^A-Za-z0-9_.-])/?repo-harness-run(?:/|$)")),
    ("absolute_local_path", re.compile(r"(?:^|[^A-Za-z0-9_.-])/(?:Users|private|home|root|workspace|testbed|tmp|var)(?:/|$)")),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-jsonl", required=True, type=Path)
    parser.add_argument("--run-summary-jsonl", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--stage-id", required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--model-name-or-path", required=True)
    parser.add_argument("--official-run-id", required=True)
    parser.add_argument("--official-report-dir", required=True, type=Path)
    parser.add_argument("--start-index", type=int, required=True)
    parser.add_argument("--end-index", type=int, required=True)
    parser.add_argument(
        "--keep-test-file-changes",
        action="store_true",
        help=(
            "Keep model changes to test-like files in exported official predictions. "
            "By default, SWE-bench exports strip those hunks and record the original patch in the manifest."
        ),
    )
    args = parser.parse_args()

    dataset_rows = _read_jsonl(args.dataset_jsonl)
    rows_by_instance = {row["instance_id"]: row for row in dataset_rows}
    run_records = [
        record
        for record in _read_jsonl(args.run_summary_jsonl)
        if args.start_index <= int(record["index"]) <= args.end_index
        and record.get("status") == "command_success"
    ]
    run_records.sort(key=lambda item: int(item["index"]))

    missing_instances = [record["instance_id"] for record in run_records if record["instance_id"] not in rows_by_instance]
    if missing_instances:
        raise SystemExit(f"run summary contains instances absent from dataset: {missing_instances}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / f"verified_{args.stage_id}_{args.window_id}_dataset.jsonl"
    predictions_path = output_dir / f"repoharness_{args.stage_id}_{args.window_id}_predictions.jsonl"
    manifest_path = output_dir / f"{args.stage_id}_{args.window_id}_prediction_manifest.json"
    stable_manifest_alias_path = output_dir / "official_prediction_manifest.json"
    official_command_path = output_dir / "official_harness_command.md"

    selected_rows = []
    prediction_rows = []
    manifest_records = []
    patch_risks = []
    excluded_predictions = []
    for record in run_records:
        patch_path = Path(record["run_dir"]) / "final.patch"
        patch = patch_path.read_text(encoding="utf-8") if patch_path.exists() else ""
        hygiene_report_path = Path(record["run_dir"]) / "final_patch_hygiene_report.json"
        hygiene_report = _read_json_if_exists(hygiene_report_path)
        hygiene_report_status = "missing_legacy_fallback"
        hygiene_report_reason: str | None = "final_patch_hygiene_report_missing"
        hygiene_filtered_files: list[dict[str, Any]] = []
        if hygiene_report:
            hygiene_report_status = "present"
            hygiene_report_reason = None
            expected_sha = hygiene_report.get("cleaned_patch_sha256")
            actual_sha = hashlib.sha256(patch.encode("utf-8")).hexdigest()
            if expected_sha != actual_sha:
                hygiene_report_status = "mismatch"
                hygiene_report_reason = "final_patch_hygiene_report_cleaned_patch_sha256_mismatch"
            else:
                hygiene_report_reason = patch_hygiene_invalid_reason(hygiene_report)
            raw_filtered = hygiene_report.get("filtered_files")
            if isinstance(raw_filtered, list):
                hygiene_filtered_files = _public_safe_hygiene_filtered_files(raw_filtered)
        if hygiene_report_reason:
            patch_sha256 = hashlib.sha256(patch_path.read_bytes()).hexdigest() if patch_path.exists() else None
            excluded_predictions.append(
                {
                    "index": int(record["index"]),
                    "instance_id": record["instance_id"],
                    "run_id": record["run_id"],
                    "exclusion_reason": hygiene_report_reason,
                    "patch_path": patch_path.as_posix(),
                    "patch_sha256": patch_sha256,
                    "final_patch_hygiene_report_status": hygiene_report_status,
                    "final_patch_hygiene_report_sha256": (
                        hashlib.sha256(hygiene_report_path.read_bytes()).hexdigest()
                        if hygiene_report_path.exists()
                        else None
                    ),
                    "recommended_handling": (
                        "exclude this sample from official predictions until the final patch hygiene report "
                        "and cleaned final.patch are consistent and training-eligible"
                    ),
                }
            )
            continue
        modified_files = _patch_modified_files(patch)
        test_files = _test_like_paths(modified_files)
        temporary_artifact_files = _temporary_artifact_paths(modified_files)
        stripped_paths = set(temporary_artifact_files)
        if not args.keep_test_file_changes:
            stripped_paths.update(test_files)
        exported_patch = _strip_patch_paths(patch, stripped_paths)
        exported_modified_files = _patch_modified_files(exported_patch)
        patch_sha256 = hashlib.sha256(patch_path.read_bytes()).hexdigest() if patch_path.exists() else None
        exported_patch_sha256 = hashlib.sha256(exported_patch.encode("utf-8")).hexdigest()
        content_leaks = _patch_content_leak_findings(exported_patch)
        if content_leaks:
            excluded_predictions.append(
                {
                    "index": int(record["index"]),
                    "instance_id": record["instance_id"],
                    "run_id": record["run_id"],
                    "exclusion_reason": "prediction_patch_content_leak_blocked",
                    "patch_path": patch_path.as_posix(),
                    "patch_sha256": patch_sha256,
                    "exported_patch_sha256": exported_patch_sha256,
                    "content_leak_findings": content_leaks,
                    "recommended_handling": (
                        "exclude this sample from official predictions and inspect the private run artifact; "
                        "do not publish model_patch content until the leak source is removed"
                    ),
                }
            )
            patch_risks.append(
                {
                    "instance_id": record["instance_id"],
                    "risk": "prediction_patch_content_leak_blocked",
                    "patch_path": patch_path.as_posix(),
                    "patch_sha256": patch_sha256,
                    "exported_patch_sha256": exported_patch_sha256,
                    "content_leak_findings": content_leaks,
                    "recommended_handling": "exclude from official predictions and keep details runtime-private",
                }
            )
            continue
        selected_rows.append(rows_by_instance[record["instance_id"]])
        prediction_rows.append(
            {
                "instance_id": record["instance_id"],
                "model_name_or_path": args.model_name_or_path,
                "model_patch": exported_patch,
            }
        )
        manifest_records.append(
            {
                "index": int(record["index"]),
                "instance_id": record["instance_id"],
                "run_id": record["run_id"],
                "patch_path": patch_path.as_posix(),
                "patch_size_bytes": patch_path.stat().st_size if patch_path.exists() else 0,
                "patch_sha256": patch_sha256,
                "modified_files": modified_files,
                "test_like_modified_files": test_files,
                "temporary_artifact_modified_files": temporary_artifact_files,
                "prediction_patch_modifies_test_files": bool(test_files),
                "prediction_patch_modifies_temporary_artifacts": bool(temporary_artifact_files),
                "exported_patch_size_bytes": len(exported_patch.encode("utf-8")),
                "exported_patch_sha256": exported_patch_sha256,
                "exported_modified_files": exported_modified_files,
                "test_file_changes_stripped": bool(test_files and not args.keep_test_file_changes),
                "temporary_artifact_changes_stripped": bool(temporary_artifact_files),
                "stripped_test_like_modified_files": test_files if not args.keep_test_file_changes else [],
                "stripped_temporary_artifact_modified_files": temporary_artifact_files,
                "patch_hygiene_policy_version": (
                    hygiene_report.get("patch_hygiene_policy_version")
                    if hygiene_report
                    else PATCH_HYGIENE_POLICY_VERSION
                ),
                "final_patch_hygiene_report_status": hygiene_report_status,
                "final_patch_hygiene_report_sha256": (
                    hashlib.sha256(hygiene_report_path.read_bytes()).hexdigest()
                    if hygiene_report_path.exists()
                    else None
                ),
                "cleaned_patch_sha256": (
                    hygiene_report.get("cleaned_patch_sha256") if hygiene_report else patch_sha256
                ),
                "raw_patch_sha256": (
                    hygiene_report.get("raw_patch_sha256") if hygiene_report else patch_sha256
                ),
                "hygiene_filtered_file_count": len(hygiene_filtered_files),
                "hygiene_filtered_files": hygiene_filtered_files,
                "official_prediction_uses_cleaned_patch": True,
            }
        )
        if test_files:
            patch_risks.append(
                {
                    "instance_id": record["instance_id"],
                    "risk": "prediction_patch_modifies_test_files",
                    "patch_path": patch_path.as_posix(),
                    "patch_sha256": patch_sha256,
                    "exported_patch_sha256": exported_patch_sha256,
                    "modified_files": modified_files,
                    "test_like_modified_files": test_files,
                    "test_file_changes_stripped": not args.keep_test_file_changes,
                    "recommended_handling": (
                        "export source-only patch to the official SWE-bench harness by default, "
                        "and flag the original patch for leaderboard comparability and training-export hygiene review"
                    ),
                }
            )
        if temporary_artifact_files:
            patch_risks.append(
                {
                    "instance_id": record["instance_id"],
                    "risk": "prediction_patch_modifies_temporary_artifacts",
                    "patch_path": patch_path.as_posix(),
                    "patch_sha256": patch_sha256,
                    "exported_patch_sha256": exported_patch_sha256,
                    "modified_files": modified_files,
                    "temporary_artifact_modified_files": temporary_artifact_files,
                    "temporary_artifact_changes_stripped": True,
                    "recommended_handling": (
                        "strip diagnostic leftovers from official SWE-bench predictions, "
                        "because they are not source changes and can turn a valid model patch into a noisy submission"
                    ),
                }
            )

    _write_jsonl(dataset_path, selected_rows)
    _write_jsonl(predictions_path, prediction_rows)
    manifest = {
        "schema_version": f"repo_harness_swebench_verified_{args.stage_id}_official_prediction_manifest_v0",
        "created_at": _timestamp(),
        "artifact_visibility": "runtime_private_operational_artifact",
        "public_evidence_policy": (
            "Do not commit this manifest or official command as public evidence without sanitizing paths. "
            "Publish only sha256, opaque refs, aggregate counts, and redacted summaries."
        ),
        "stage_id": args.stage_id,
        "window_id": args.window_id,
        "start_index": args.start_index,
        "end_index": args.end_index,
        "dataset_count": len(selected_rows),
        "prediction_count": len(prediction_rows),
        "excluded_prediction_count": len(excluded_predictions),
        "excluded_predictions": excluded_predictions,
        "model_name_or_path": args.model_name_or_path,
        "dataset_path": dataset_path.as_posix(),
        "predictions_path": predictions_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "stable_manifest_alias_path": stable_manifest_alias_path.as_posix(),
        "official_run_id": args.official_run_id,
        "official_report_dir": args.official_report_dir.resolve().as_posix(),
        "source_run_summary": args.run_summary_jsonl.resolve().as_posix(),
        "source_dataset_path": args.dataset_jsonl.resolve().as_posix(),
        "test_file_change_export_policy": (
            "keep_original_prediction_patch"
            if args.keep_test_file_changes
            else "strip_test_file_changes_from_official_predictions"
        ),
        "patch_risk_count": len(patch_risks),
        "patch_risks": patch_risks,
        "records": manifest_records,
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    stable_manifest_alias_path.write_text(manifest_text, encoding="utf-8")
    official_command_path.write_text(_official_command(manifest), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _official_command(manifest: dict[str, Any]) -> str:
    return f"""# Official SWE-bench harness command for {manifest['stage_id']} {manifest['window_id']} RepoHarness patches

This command file is a runtime-private operational artifact. It may contain local output paths supplied by
the caller and must not be committed as public evidence without sanitization.

```bash
python -m swebench.harness.run_evaluation \\
  -d {manifest['dataset_path']} \\
  -s test \\
  -p {manifest['predictions_path']} \\
  --max_workers 1 \\
  --timeout 1800 \\
  --cache_level instance \\
  --clean false \\
  -id {manifest['official_run_id']} \\
  --report_dir {manifest['official_report_dir']}
```
"""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _patch_content_leak_findings(patch: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not patch:
        return findings
    line_findings: dict[tuple[str, int], dict[str, Any]] = {}
    for line_number, line in enumerate(patch.splitlines(), start=1):
        for reason, pattern in _PATCH_CONTENT_LEAK_PATTERNS:
            if pattern.search(line):
                line_findings.setdefault(
                    (reason, line_number),
                    {"reason": reason, "line": line_number},
                )
    findings.extend(line_findings.values())
    return findings


def _public_safe_hygiene_filtered_files(raw_filtered: list[Any]) -> list[dict[str, Any]]:
    public_items: list[dict[str, Any]] = []
    for item in raw_filtered:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str):
            decision = classify_patch_path(path)
            public = decision.public_dict()
            public["action"] = str(item.get("action") or decision.action)
            public["reason"] = str(item.get("reason") or decision.reason)
            public_items.append(public)
            continue
        public_items.append(
            {
                key: value
                for key, value in item.items()
                if key in {"action", "reason", "path_category", "path_sha256", "basename_redacted"}
            }
        )
    return public_items


def _patch_modified_files(patch: str) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    for block in _patch_blocks(patch):
        path = _diff_block_target_path(block)
        if path is not None and path not in seen:
            files.append(path)
            seen.add(path)
    return files


def _test_like_paths(paths: list[str]) -> list[str]:
    test_paths = []
    for path in paths:
        parts = path.split("/")
        name = parts[-1] if parts else path
        if (
            path.startswith("tests/")
            or path.startswith("test/")
            or path.startswith("testing/")
            or "/tests/" in path
            or "/test/" in path
            or "/testing/" in path
            or name == "conftest.py"
            or name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.js")
            or name.endswith(".spec.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.ts")
        ):
            test_paths.append(path)
    return test_paths


def _temporary_artifact_paths(paths: list[str]) -> list[str]:
    temporary_paths = []
    for path in paths:
        name = path.split("/")[-1] if path else path
        hygiene_decision = classify_patch_path(path)
        if (
            hygiene_decision.action == "exclude"
            or path == "patch.txt"
            or path.startswith("tmp/")
            or path.startswith(".repo_harness_tmp/")
            or name.endswith(".orig")
            or name.endswith(".rej")
            or _looks_like_unsafe_patch_path(path)
            or _looks_like_root_diagnostic_artifact(path)
        ):
            temporary_paths.append(path)
    return temporary_paths


def _looks_like_unsafe_patch_path(path: str) -> bool:
    if not path or path.startswith("/"):
        return True
    if any(marker in path for marker in ("\n", "\r", "\t", "\\n", "\\r", "\\t")):
        return True
    parts = path.split("/")
    return any(part in {"", ".", ".."} for part in parts)


def _looks_like_root_diagnostic_artifact(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    if len(parts) != 1:
        return False
    name = parts[0]
    root_artifact_suffixes = (
        ".dot",
        ".fit",
        ".fits",
        ".fits.gz",
    )
    if name.endswith(root_artifact_suffixes):
        return True
    if not name.endswith(".py"):
        return False
    root_probe_prefixes = (
        "check_",
        "debug_",
        "diffbug",
        "new_format_",
        "probe_",
        "repro",
        "reproduce",
        "tmp_",
    )
    return name.startswith(root_probe_prefixes)


def _strip_patch_paths(patch: str, denied_paths: set[str]) -> str:
    if not patch or not denied_paths:
        return patch
    blocks = _patch_blocks(patch)
    kept = [block for block in blocks if _diff_block_target_path(block) not in denied_paths]
    return "".join("".join(block) for block in kept)


def _patch_blocks(patch: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in patch.splitlines(keepends=True):
        if line.startswith("diff --git "):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _diff_block_target_path(block: list[str]) -> str | None:
    if not block:
        return None
    match = re.match(r"^diff --git a/(.*?) b/(.*?)$", block[0])
    if match:
        return match.group(2)
    try:
        parts = shlex.split(block[0].strip())
    except ValueError:
        return None
    if len(parts) >= 4 and parts[0] == "diff" and parts[1] == "--git":
        target = parts[3]
        if target.startswith("b/"):
            return target[2:]
    return None


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
