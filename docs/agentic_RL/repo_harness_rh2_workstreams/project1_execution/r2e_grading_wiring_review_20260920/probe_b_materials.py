"""B 线计划复核：旧日志逐键对拍、gold 应用结果、排除区基线边界。

仓库根执行：rh2/.venv/bin/python <本文件>。只输出 JSON，不启动 Docker。
gold 对照仅在来源 old_file_content 临时树应用补丁，不代表真实镜像验证。
"""
from __future__ import annotations

import asyncio
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import probe_plan_seams as a_review

ROOT = a_review.ROOT
RAW = ROOT / "runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl"
PRIME = ROOT / "runs/env_probe_20260909_codex_backup/analysis/prime_taskset.py"
RUNNER = ROOT / "rh2/experiments/env_probe_20260909/r2e_probe.py"


def normalized_prime(functions, mapping):
    decolored = functions["_decolor"](mapping)
    return {key.split(" - ")[0]: decolored[key] for key in sorted(decolored)}


def material_comparison():
    prime = a_review.pure_functions(PRIME, {"parse_log_pytest", "_decolor", "extract_gold_patch"})
    runner = a_review.pure_functions(
        RUNNER, {"parse_pytest_summary", "_decolor", "normalize_map", "is_test_path", "build_gold_patch"},
        {"ANSI_RE": re.compile(r"\x1b\[[0-9;]*m"), "difflib": difflib},
    )
    rows = [json.loads(line) for line in RAW.read_text().splitlines() if line]
    by_prefix = {row["commit_hash"][:12]: row for row in rows}
    m3 = ROOT / "runs/env_overnight_20260916/M3"
    logs = list((m3 / "gold_ledger/logs_r2e").glob("*/*/gold/a*/test_output.txt"))
    logs += list((m3 / "facts").glob("*/noop_x2/out*.txt"))
    logs += list((ROOT / "runs/env_probe_20260909_codex_backup/ledger/logs_r2e").glob("*/*/*/a*/test_output.txt"))
    differences = []
    for path in sorted(logs):
        prefix, = [part for part in path.parts if part in by_prefix]
        text = path.read_text(errors="replace")
        expected = json.loads(by_prefix[prefix]["expected_output_json"])
        observed_equal = normalized_prime(prime, prime["parse_log_pytest"](text)) == runner["normalize_map"](runner["parse_pytest_summary"](text))
        expected_equal = normalized_prime(prime, expected) == runner["normalize_map"](expected)
        if not observed_equal or not expected_equal:
            differences.append({"path": str(path.relative_to(ROOT)), "observed_equal": observed_equal, "expected_equal": expected_equal})
    assert len(logs) == 336 and not differences, differences

    gold = []
    for row in rows:
        source_patch = prime["extract_gold_patch"](row["parsed_commit_content"])
        runner_patch, metadata = runner["build_gold_patch"](row["parsed_commit_content"])
        source_paths = sorted(line.split(" b/", 1)[1] for line in source_patch.splitlines() if line.startswith("diff --git "))
        paths = sorted(metadata["included"])
        assert source_paths == paths, row["commit_hash"]
        outputs = {}
        for kind, patch in (("prime", source_patch), ("runner", runner_patch)):
            with tempfile.TemporaryDirectory(prefix="r2e-b-review-") as directory:
                root = Path(directory)
                for entry in json.loads(row["parsed_commit_content"])["file_diffs"]:
                    name = entry["header"]["file"]["path"]
                    if name not in paths:
                        continue
                    assert not Path(name).is_absolute() and ".." not in Path(name).parts
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if entry.get("old_file_content") is not None:
                        target.write_bytes(entry["old_file_content"].encode())
                for arguments in (("--check",), ()):
                    result = subprocess.run(["git", "apply", *arguments, "-"], input=patch, text=True, cwd=directory, capture_output=True, check=False)
                    assert result.returncode == 0, (row["commit_hash"], kind, arguments, result.stderr)
                outputs[kind] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() if (root / name).exists() else None for name in paths}
        assert outputs["prime"] == outputs["runner"], row["commit_hash"]
        gold.append({
            "task": row["repo_name"] + "__" + row["commit_hash"],
            "patch_bytes_equal": source_patch == runner_patch,
            "selected_paths_equal": True, "applied_file_sha256": outputs["prime"],
            "applied_files_equal": True,
        })
    return {"logs_compared": len(logs), "normalized_expected_and_observed_map_differences": differences,
            "gold_tasks": len(gold), "gold_patch_bytes_equal": sum(row["patch_bytes_equal"] for row in gold),
            "gold_selected_paths_and_applied_files_equal": len(gold), "gold_details": gold}


def excluded_namespace_boundary():
    """合成路径行调用真实 parser/digest；不声称 48 镜像已经产生这个缓存。"""
    from repoharness2.adapters.slime.baseline_census import build_census_script, parse_census_output
    from repoharness2.contracts.baseline_manifest import BaselineManifestPolicy, compute_baseline_manifest_digest

    policy = BaselineManifestPolicy(
        policy_version="r2e_b_review_only",
        excluded_namespaces=(".git/", ".harness/", ".venv/"),
        regenerable_cache_dirs=(".pytest_cache", "__pycache__"),
    )
    common = dict(task_id="r2e_gym_subset::probe", workdir="/testbed", public_bundle_digest="sha256:" + "a" * 64,
                  runtime_image_digest="sha256:" + "b" * 64, materialized_head="c" * 40,
                  task_base_commit="c" * 40, policy=policy)
    cold = "regular\t100644\t" + "d" * 64 + "\tmodule.py\nEXCL\t.venv/lib/site.py\n"
    warm = cold + "EXCL\t.venv/lib/__pycache__/site.cpython-39.pyc\n"
    before = parse_census_output(cold, **common)
    after = parse_census_output(warm, **common)
    assert before.entries == after.entries
    assert compute_baseline_manifest_digest(before) != compute_baseline_manifest_digest(after)
    script = build_census_script("/testbed", policy)
    return {"reachability": "conditional_future; actual R2E cold-image behavior unverified",
            "scoreable_entries_equal": True, "manifest_digest_equal": False,
            "excluded_walk": [line for line in script.splitlines() if "find './.venv'" in line]}


async def main():
    result = {"a_probe_recheck": {"source_replay": a_review.source_replay(),
                                  "manager_seams": await a_review.manager_seams(),
                                  "runtime_ownership": a_review.runtime_ownership()},
              "b_material_comparison": material_comparison(), "excluded_namespace_boundary": excluded_namespace_boundary()}
    paths = [RAW, PRIME, RUNNER, Path(__file__), Path(a_review.__file__),
             ROOT / "rh2/src/repoharness2/grading/manager.py",
             ROOT / "rh2/src/repoharness2/adapters/slime/baseline_census.py",
             ROOT / "rh2/src/repoharness2/contracts/baseline_manifest.py"]
    result["source_sha256"] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
