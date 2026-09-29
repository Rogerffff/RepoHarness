"""R2E 计划审查：固定来源重放 + 现有 manager 接缝；不修改生产代码、不启动 Docker。

从仓库根运行：rh2/.venv/bin/python <本文件>
manager 案例只替代计划尚未实现的 R2E verdict→fields，测试真实报告分支。
candidate 案另替代三路归因结果，仅用于检查报告字段运输，不证明候选归因。
"""
from __future__ import annotations

import ast
import asyncio
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "rh2/tests/grading"))


def pure_functions(path, names, extra=None):
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(nodes) == len(names)
    ns = {"re": re, "json": json, **(extra or {})}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    return ns


def source_replay():
    official_path = ROOT / "runs/env_probe_20260909_codex_backup/analysis/prime_taskset.py"
    official = pure_functions(official_path, {"parse_log_pytest", "_decolor", "calculate_reward"})
    runner_path = ROOT / "rh2/experiments/env_probe_20260909/r2e_probe.py"
    runner = pure_functions(
        runner_path, {"parse_pytest_summary", "_decolor", "normalize_map", "has_ansi", "r2e_reward"},
        {"ANSI_RE": re.compile(r"\x1b\[[0-9;]*m")},
    )
    data_path = ROOT / "runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl"
    rows = [json.loads(x) for x in data_path.read_text().splitlines() if x]
    by_prefix = {x["commit_hash"][:12]: x for x in rows}
    task_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L4_r2e/r2e_tasks_48.json"
    listed = json.loads(task_path.read_text())["tasks"]
    assert {x["commit_hash"] for x in rows} == {x["commit_hash"] for x in listed}
    wrong_path = ROOT / "runs/env_overnight_20260916/M3/inputs/r2e_expansion_preparation/r2e_candidates_full.jsonl"
    wrong_rows = [json.loads(x) for x in wrong_path.read_text().splitlines() if x]
    m3 = ROOT / "runs/env_overnight_20260916/M3"
    paths = list((m3 / "gold_ledger/logs_r2e").glob("*/*/gold/a*/test_output.txt"))
    paths += list((m3 / "facts").glob("*/noop_x2/out*.txt"))
    paths += list((ROOT / "runs/env_probe_20260909_codex_backup/ledger/logs_r2e").glob("*/*/*/a*/test_output.txt"))
    result, diffs, pillow = Counter(), [], []
    for path in sorted(paths):
        ids = [part for part in path.parts if part in by_prefix]
        assert len(ids) == 1, str(path)
        row = by_prefix[ids[0]]
        log = path.read_text(errors="replace")
        exp = row["expected_output_json"]
        official_reward = official["calculate_reward"](log, exp)
        runner_reward, _ = runner["r2e_reward"](runner["parse_pytest_summary"](log), json.loads(exp))
        stage = "gold" if "gold" in path.parts else "noop"
        result[f"{stage}_reward_{int(official_reward)}"] += 1
        if official_reward != runner_reward:
            diffs.append(str(path.relative_to(ROOT)))
        if "gold" in path.parts and row["repo_name"] == "pillow" and any("\x1b" in k for k in json.loads(exp)):
            pillow.append({"commit": row["commit_hash"][:12], "official": official_reward, "runner": runner_reward})
    assert not diffs, diffs
    assert len({x["commit"] for x in pillow}) == 6 and all(x["official"] == 1 for x in pillow)
    literal = next(n.value for n in ast.walk(ast.parse(official_path.read_text()))
                   if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("\x1b"))
    return {
        "official_archive_sha256": hashlib.sha256(official_path.read_bytes()).hexdigest(),
        "official_regex_repr": repr(literal),
        "ansi_example": official["_decolor"]({"\x1b[1mtest_sanity\x1b[0m": "PASSED"}),
        "plan_input_count": len(wrong_rows), "merged_input_count": len(rows), "manifest_count": len(listed),
        "merged_keys_equal_manifest": True, "logs_replayed": len(paths), "reward_counts": dict(result),
        "official_vs_runner_reward_differences": diffs,
        "pillow_ansi_gold_unique_tasks": len({x["commit"] for x in pillow}),
        "pillow_ansi_gold_runs": len(pillow), "pillow_ansi_gold_all_official_reward_1": True,
    }


async def manager_seams():
    from grading_fixtures import FakeDocker, FakeWorkspace, GOOD_PATCH, make_fixture_spec
    from repoharness2.envpack import scoring
    from repoharness2.grading.manager import (
        SWEGradingManager, GradingManagerConfig, execution_failure_trigger,
    )

    def verdict(observed, missing=(), resolved=False):
        return scoring.EvalVerdict(
            instance_id="r2e_example", apply_ok=True,
            resolution="RESOLVED_FULL" if resolved else "RESOLVED_NO", resolved=resolved,
            f2p_rate=0, p2p_rate=0, f2p_success=[], f2p_failure=[], p2p_success=[], p2p_failure=[],
            num_parsed_tests=observed, reference_missing=list(missing),
        )

    v = verdict(1, ["test_b"])
    trigger = execution_failure_trigger(v)
    assert trigger == "reference_all_missing"  # 计划的真实条件此处不成立：test_a 已在场。
    manager = SWEGradingManager(GradingManagerConfig(), docker=FakeDocker(base_commit="a" * 40))
    manager._read_resource_facts = AsyncMock(return_value={
        "oom_kill_events": 0, "pids_events_max": 0, "container_oom_killed": False,
    })
    decision = await manager._decide_execution_failure(
        record=SimpleNamespace(candidate_facts={"test_rc": 2}),
        spec=make_fixture_spec("a" * 40, "fake", checkout_mode="image_embedded"),
        verdict=v, log_text="\n".join([
            ">>>>> Start Test Output", "ERROR collecting r2e_tests/test_b.py",
            "short test summary info", "PASSED r2e_tests/test_a.py::test_a", ">>>>> End Test Output",
        ]), candidate_paths=[], trigger=trigger,
    )
    assert decision["kind"] == "unattributed"
    out = {"partial_reference_present": {"trigger": trigger, "decision": decision["kind"],
            "expected_source_reward": 0, "current_override_reward": None}, "reports": []}
    for case in ("resolved", "tests_failed", "candidate_execution_failed", "infra_before_parser", "patch_apply_failed"):
        fake = FakeDocker(base_commit="a" * 40, pull_fail=(case == "infra_before_parser"),
                          image_present=(case != "infra_before_parser"),
                          apply_exit_code=1 if case == "patch_apply_failed" else 0)
        mgr = SWEGradingManager(GradingManagerConfig(), docker=fake)
        is_candidate = case == "candidate_execution_failed"
        parsed = verdict(0 if is_candidate else 1, resolved=(case == "resolved"))
        match = scoring.expected_map_matches({"test_a": "PASSED"},
                                             {"test_a": "PASSED" if case == "resolved" else "FAILED"})
        spec = make_fixture_spec("a" * 40, "fake", checkout_mode="image_embedded", parse_log=lambda _: parsed,
                                 task_id="r2e_gym_subset::example", grader_version="r2e-plan-probe")
        if is_candidate:
            mgr._decide_execution_failure = AsyncMock(return_value={
                "kind": "candidate", "stage": "test_collection", "evidence": ["probe: attributed"],
            })
        with patch.object(scoring, "grading_outcome_fields", return_value=scoring.grading_outcome_fields_r2e(match)):
            report = await mgr.grade(trajectory_id="probe_" + case, workspace=FakeWorkspace(GOOD_PATCH), spec=spec)
        out["reports"].append({"case": case, "outcome": report.outcome, "reward": report.reward,
                              "grading_semantics": report.grading_semantics, "failure": report.failure_category})
        assert report.grading_semantics == ("r2e_expected_map" if case in {"resolved", "tests_failed"} else "swe_f2p_p2p")
    return out


def runtime_ownership():
    from repoharness2.adapters.slime.sandbox_profile import (
        RolloutSandboxProfile, GraderSandboxProfile,
        rollout_trusted_init_script, grader_protect_control_surface_script,
    )
    rp = RolloutSandboxProfile(model_proxy_upstream_host="127.0.0.1", model_proxy_upstream_port=8080)
    gp = GraderSandboxProfile()
    return {
        "rollout_uid": rp.agent_uid, "grader_uid": gp.candidate_exec_uid,
        "rollout_workdir_chown": [x for x in rollout_trusted_init_script(rp).splitlines() if "chown -R" in x and "/testbed" in x],
        "grader_workdir_chown": [x for x in grader_protect_control_surface_script(gp, ["run_tests.sh"]).splitlines() if "chown -R" in x],
    }


async def main():
    result = {"source_replay": source_replay(), "manager_seams": await manager_seams(), "runtime_ownership": runtime_ownership()}
    paths = ["rh2/src/repoharness2/grading/manager.py", "rh2/src/repoharness2/envpack/scoring.py",
             "rh2/src/repoharness2/adapters/slime/sandbox_profile.py",
             "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_grading_wiring_20260920.md"]
    result["file_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
