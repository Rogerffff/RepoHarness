"""B 线计划复核：读取旧候选证据、验证当前日志解析；不运行容器或修改评分。"""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "rh2" / "src"))

from swebench.harness.constants import (  # noqa: E402
    END_TEST_OUTPUT,
    MAP_REPO_VERSION_TO_SPECS,
    START_TEST_OUTPUT,
)
from swebench.harness.grading import (  # noqa: E402
    get_eval_tests_report,
    get_logs_eval,
    get_resolution_status,
)
from swebench.harness.log_parsers import MAP_REPO_TO_PARSER  # noqa: E402


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def log_boundary_cases() -> list[dict]:
    """真实 4.1 get_logs_eval；配置使用其已支持的 requests，不伪造 Gym 接线。"""
    repo = "psf/requests"
    spec = SimpleNamespace(repo=repo, version=next(iter(MAP_REPO_VERSION_TO_SPECS[repo])))
    passed = "PASSED tests/f.py::f\nPASSED tests/p.py::p\n"
    cases = (
        ("no_results_anywhere", "", "collection failed\n"),
        ("passed_only_outside_test_markers", passed, "collection failed\n"),
        ("passed_inside_test_markers", "", passed),
    )
    result = []
    with tempfile.TemporaryDirectory(prefix="rh2-b-log-review-") as directory:
        log = Path(directory) / "eval.log"
        for name, outside, inside in cases:
            log.write_text(outside + START_TEST_OUTPUT + "\n" + inside + END_TEST_OUTPUT + "\n")
            status_map, apply_ok = get_logs_eval(spec, str(log))
            report = get_eval_tests_report(
                status_map, {"FAIL_TO_PASS": ["tests/f.py::f"], "PASS_TO_PASS": ["tests/p.py::p"]}
            )
            result.append({
                "case": name,
                "test_segment_map": MAP_REPO_TO_PARSER[repo](inside, spec),
                "get_logs_eval_map": status_map,
                "apply_ok": apply_ok,
                "report_resolution": get_resolution_status(report),
                "manager_zero_parsed_condition": len(status_map) == 0,
            })
    return result


def candidate_evidence() -> dict:
    relative = "runs/env_probe_20260909_final_sync/ledger/cc_candidate_grading.jsonl"
    path = ROOT / relative
    if not path.exists():
        return {"source": relative, "available": False}
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    groups = {gate: [r for r in rows if r["gate"] == gate] for gate in ("candidate", "candidate_projected")}
    original = groups["candidate"]
    mismatches = []
    for row in original:
        patch = path.parent / "cc_patches" / (row["instance_id"] + ".diff")
        if not patch.exists() or digest(patch.read_bytes()) != row["fixture_digest"]:
            mismatches.append(row["instance_id"])
    return {
        "source": relative,
        "available": True,
        "source_sha256": digest(path.read_bytes()),
        "groups": {
            gate: {"rows": len(items), "unique_tasks": len({r["instance_id"] for r in items}),
                   "verdicts": dict(Counter(r["official_verdict"] for r in items))}
            for gate, items in groups.items()
        },
        "original_patch_file_mismatches": mismatches,
        "original_strict_apply_failed": [
            {"task_id": r["instance_id"], "patch_sha256": r["fixture_digest"],
             "oracle_apply_method": r["patch_apply"], "oracle_verdict": r["official_verdict"]}
            for r in original if r["git_apply_check_ok"] is False
        ],
        "scope": "历史账本及现存 patch 字节核验；未在新 candidate 容器复现 patch 应用。",
    }


if __name__ == "__main__":
    tracked = (
        "rh2/src/repoharness2/envpack/scoring.py",
        "rh2/src/repoharness2/adapters/slime/prepared_task_face.py",
        "rh2/src/repoharness2/grading/manager.py",
    )
    print(json.dumps({
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "swebench_version": importlib.metadata.version("swebench"),
        "source_sha256": {name: digest((ROOT / name).read_bytes()) for name in tracked},
        "get_logs_eval_source_sha256": digest(inspect.getsource(get_logs_eval).encode()),
        "log_boundary": log_boundary_cases(),
        "candidate_evidence": candidate_evidence(),
        "scope": "CPU 函数对照与历史证据读取；没有实现新 driver/parser，没有新 Docker 评分。",
    }, ensure_ascii=False, indent=2))
