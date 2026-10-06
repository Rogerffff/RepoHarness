"""R-a/R-b 独立离线复核；从仓库根用 rh2/.venv/bin/python 运行。

只读仓库材料，重建产物写临时目录；stdout 是 JSON 结果。无网络、Docker 或维护测试修改。
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path


def main() -> None:
    root = Path.cwd()
    sys.path.insert(0, str(root / "rh2/src"))
    from repoharness2.envpack import ingest_r2e_subset as ingest
    from repoharness2.envpack import r2e_parsers as port
    from repoharness2.envpack import scoring

    result: dict = {}
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source_pairs = {
        "raw": (ingest.R2E_RAW_ARCHIVE_RELPATH,
                "runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl"),
        "revision": (ingest.R2E_SOURCE_REVISION_RELPATH,
                     "runs/env_overnight_20260916/M3/probe_data/r2e_subset.revision"),
        "facts": (ingest.R2E_IMAGE_FACTS_RELPATH,
                  "runs/env_overnight_20260916/M3/r2e_image_facts.json"),
        "rules": (port.R2E_RULE_SOURCE_VENDOR_RELPATH,
                  "runs/env_probe_20260909_codex_backup/analysis/prime_taskset.py"),
    }
    result["source_copy_matches"] = {
        k: {"equal": sha(root / a) == sha(root / b), "sha256": sha(root / a)}
        for k, (a, b) in source_pairs.items()
    }
    assert all(x["equal"] for x in result["source_copy_matches"].values())

    trusted = ingest.load_trusted_r2e_ingest_outputs(root)
    rows, revision = ingest.load_r2e_rows(root, trusted.pins)
    fresh = ingest.ingest_r2e_subset(
        rows=rows, image_facts=trusted.image_facts,
        raw_archive_sha256="sha256:" + trusted.pins.raw_archive,
        image_facts_sha256="sha256:" + trusted.pins.image_facts,
        source_revision=revision,
    )
    with tempfile.TemporaryDirectory(prefix="r2e_falsifier_ingest_") as tmp:
        digests = ingest.write_r2e_ingest_outputs(fresh, Path(tmp), pins=trusted.pins)
        result["regenerated_artifact_matches"] = {
            name: digest == sha(root / ingest.R2E_INGEST_OUT_RELPATH / name)
            for name, digest in digests.items()
        }
    assert all(result["regenerated_artifact_matches"].values())

    names = {"parse_log_pytest", "_decolor", "calculate_reward", "extract_gold_patch"}
    raw_rules = root / port.R2E_RULE_SOURCE_VENDOR_RELPATH
    ast_rules = ast.parse(raw_rules.read_text(encoding="utf-8"))
    pure = [node for node in ast_rules.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(pure) == len(names)
    upstream = {"json": json, "re": re}
    exec(compile(ast.Module(body=pure, type_ignores=[]), str(raw_rules), "exec"), upstream)

    def up_normalize(status_map: dict) -> dict:
        decolored = upstream["_decolor"](status_map)
        return {key.split(" - ")[0]: decolored[key] for key in sorted(decolored)}

    actual_validation = {v.instance_id: v for v in trusted.result.validation_bundles}
    by_prefix = {g.source_commit_hash[:12]: g for g in trusted.result.grading_bundles}
    census = Counter()
    issues = []
    for row in rows:
        prefix = row["commit_hash"][:12]
        pairs = json.loads(row["expected_output_json"], object_pairs_hook=lambda pairs: pairs)
        expected = dict(pairs)
        census["tasks"] += 1
        census["duplicate_expected_keys"] += len(pairs) - len(expected)
        census["empty_raw_expected_keys"] += sum(not k for k in expected)
        census["empty_normalized_expected_keys"] += sum(not k for k in up_normalize(expected))
        census["normalization_collisions"] += len(expected) - len(up_normalize(expected))
        census["unexpected_status_values"] += sum(v not in {"PASSED", "FAILED", "ERROR"} for v in expected.values())
        census["expected_keys_with_cr"] += sum("\r" in k for k in expected)
        census["expected_keys_with_multi_parameter_sgr"] += sum(bool(re.search(r"\x1b\[[0-9]+;", k)) for k in expected)
        census["expected_keys_with_ansi"] += sum("\x1b[" in k for k in expected)
        if up_normalize(expected) != port.normalize_status_map(expected):
            issues.append([prefix, "expected_normalization"])
        gold = upstream["extract_gold_patch"](row["parsed_commit_content"])
        ours = port.extract_gold_patch(row["parsed_commit_content"])
        bundle = actual_validation[f"{row['repo_name']}__{row['commit_hash']}"]
        if gold != ours or gold != bundle.golden_patch:
            issues.append([prefix, "gold_bytes_differ_from_pinned_upstream"])
    result["input_census"] = dict(census)

    m3 = root / "runs/env_overnight_20260916/M3"
    paths = list((m3 / "gold_ledger/logs_r2e").glob("*/*/gold/a*/test_output.txt"))
    paths += list((m3 / "facts").glob("*/noop_x2/out*.txt"))
    paths += list((root / "runs/env_probe_20260909_codex_backup/ledger/logs_r2e").glob("*/*/*/a*/test_output.txt"))
    assert len(paths) == 336
    rewards = Counter()
    empty_observed_keys = 0
    raw_cr_logs = 0
    for path in paths:
        prefix, = {part.split(".")[0] for part in path.parts if part.split(".")[0] in by_prefix}
        grading = by_prefix[prefix]
        # 直接 decode 保留 CR 字节，避免 read_text 的 universal-newline 转换掩盖差异。
        text = path.read_bytes().decode("utf-8", errors="replace")
        raw_cr_logs += "\r" in text
        up_parse = upstream["parse_log_pytest"](text)
        obs = up_normalize(up_parse)
        exp = up_normalize(json.loads(grading.expected_output_json))
        reward = upstream["calculate_reward"](text, grading.expected_output_json)
        rewards[str(reward)] += 1
        empty_observed_keys += "" in obs
        ours = scoring.parse_eval_log_r2e(
            grading, f"{scoring.R2E_EVAL_START_MARKER}\n{text}\n{scoring.R2E_EVAL_END_MARKER}\n")
        if up_parse != port.parse_log_pytest(text):
            issues.append([str(path.relative_to(root)), "raw_parse_map"])
        if obs != port.normalize_status_map(port.parse_log_pytest(text)):
            issues.append([str(path.relative_to(root)), "observed_normalization"])
        if float(ours.resolved) != reward:
            issues.append([str(path.relative_to(root)), "reward"])
        if ours.expected_match.missing != sorted(set(exp) - set(obs)):
            issues.append([str(path.relative_to(root)), "missing_keys"])
        if ours.expected_match.unexpected != sorted(set(obs) - set(exp)):
            issues.append([str(path.relative_to(root)), "unexpected_keys"])
        mismatch = sorted(k for k in set(exp) & set(obs) if exp[k] != obs[k])
        if ours.expected_match.mismatched != mismatch:
            issues.append([str(path.relative_to(root)), "mismatched_keys"])
    result["corpus"] = {
        "logs": len(paths), "rewards": dict(rewards), "logs_with_empty_observed_key": empty_observed_keys,
        "logs_with_raw_cr": raw_cr_logs,
    }
    result["differences"] = issues
    assert issues == []
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
