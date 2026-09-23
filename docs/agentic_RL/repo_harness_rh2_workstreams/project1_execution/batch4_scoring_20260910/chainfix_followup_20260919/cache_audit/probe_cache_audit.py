"""09-19 有界反证：真实临时树/Bash，容器生命周期复用维护 FakeDocker。

从仓库根运行：
PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python \
  docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/chainfix_review_20260919/falsifier/probe_falsifier.py

不发起 SSH、Docker、网络、模型；结果写本文件所在目录。断言描述本轮观测。
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / "rh2/src").is_dir())
sys.path[:0] = [str(ROOT / "rh2/src"), str(ROOT / "rh2/tests/grading"), str(ROOT / "rh2/tests/adapters")]

from grading_fixtures import FakeDocker, make_fixture_spec
from test_w3a_formal_grading_freeze import _formal_chain, make_barrier
from test_slime_generate import FakeRolloutDocker, _Args, SAMPLING_PARAMS, make_task
from test_w1b_delivery_face import _resolve, _decide
from repoharness2.adapters.slime.baseline_census import generate_baseline_manifest
from repoharness2.adapters.slime.patch_exporter import export_frozen_patch
from repoharness2.adapters.slime.prepared_task_face import _v2_install_lines
from repoharness2.adapters.slime.bringup import write_execution_audit_record
from repoharness2.contracts.baseline_manifest import (
    BASELINE_MANIFEST_POLICY_V1, BASELINE_MANIFEST_POLICY_V2, compute_baseline_manifest_digest,
)
from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest
from repoharness2.contracts.scoring_projection import classify_frozen_patch
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import load_vendor_specs, SPEC_VENDOR_ID_SWEGYM_242429C1
from repoharness2.grading.manager import (
    ExecResult, FrozenDeltaSource, GradingManagerConfig, HygieneRules, SWEGradingManager, candidate_facts_from_log,
)
from repoharness2.grading.trusted_projection import build_trusted_scoring_projection

BASE = "a" * 40


def shell(script, input_bytes=None, *, cwd=None, env=None):
    r = subprocess.run(["bash", "-c", script], input=input_bytes, capture_output=True, cwd=cwd, env=env, timeout=20)
    return ExecResult(r.returncode, r.stdout.decode(), r.stderr.decode())


class LocalWorkspace:
    def __init__(self, tree):
        self.tree = tree

    async def run_bash(self, script):
        return shell(script.replace("/testbed", str(self.tree)))


class LocalTreeFakeDocker(FakeDocker):
    """只实跑 census、normalization、delta；不创建 Docker 客户端或容器。"""
    def __init__(self, tree):
        super().__init__(base_commit=BASE, image_present=True)
        self.tree = tree
        self.real_phases = []

    async def __call__(self, *args, input_bytes=None):
        if args[0] == "exec":
            script = args[-1]
            phase = None
            if "find ." in script and "sha256sum" in script:
                phase = "census"
            elif "RH2_CACHE_NORMALIZED=1" in script:
                phase = "normalization"
            elif script.startswith("cd ") and any(s in script for s in ("add_target_exists:", "rm -f ./", "rm -f './")):
                phase = "delta"
            if phase:
                assert "/testbed" in script
                self.real_phases.append(phase)
                return shell(script.replace("/testbed", str(self.tree)), input_bytes)
        return await super().__call__(*args, input_bytes=input_bytes)


async def census(tree, policy=BASELINE_MANIFEST_POLICY_V2, omitted=None):
    return await generate_baseline_manifest(
        LocalWorkspace(tree), task_id="swe_gym_lite::falsifier", workdir="/testbed",
        public_bundle_digest="sha256:" + "e" * 64, runtime_image_digest="sha256:" + "1" * 64,
        materialized_head=BASE, task_base_commit=BASE, policy=policy, omitted_sink=omitted,
    )


async def export_and_grade(tree, baseline, grader_tree, logs):
    artifact = await export_frozen_patch(LocalWorkspace(tree), baseline, rollout_execution_id="exec", physical_attempt_id="exec#p1-aaaa")
    hygiene, _ = classify_frozen_patch(artifact, baseline)
    assert hygiene.verdict == "projectable"
    spec = dataclasses.replace(
        make_fixture_spec(BASE, "fake-image:v1", checkout_mode="image_embedded", task_id=baseline.task_id),
        hygiene=HygieneRules(test_files=(), test_globs=(), forbidden_globs=()),
    )
    projection, split = build_trusted_scoring_projection(artifact, spec.hygiene)
    assert split.unsupported_shape_reasons == ()
    source = FrozenDeltaSource(frozen_patch=artifact, baseline_manifest=baseline, projection=projection,
                               frozen_patch_digest=compute_frozen_patch_digest(artifact))
    docker = LocalTreeFakeDocker(grader_tree)
    manager = SWEGradingManager(GradingManagerConfig(eval_log_dir=logs), docker=docker)
    report = await manager.grade(trajectory_id="local-chainfix-probe", workspace=None, spec=spec, frozen_delta=source)
    return artifact, report, docker


def replace_object(path, kind):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "directory":
        path.mkdir()
        (path / "old").write_text("old cache\n")
    elif kind == "regular":
        path.write_text("ordinary source\n")
    elif kind == "symlink":
        path.symlink_to("target.py")


async def cache_matrix(tmp):
    rows = []
    for n, (name, before, after) in enumerate([
        (".pytest_cache", "absent", "regular"),
        (".pytest_cache", "directory", "regular"),
        ("__pycache__", "directory", "symlink"),
        ("pkg/__pycache__", "directory", "regular"),
        (".pytest_cache", "regular", "regular"),
        ("__pycache__", "symlink", "regular"),
    ]):
        case = tmp / f"matrix-{n}"
        tree = case / "rollout"
        tree.mkdir(parents=True)
        (tree / "target.py").write_text("target\n")
        replace_object(tree / name, before)
        counts = {}
        baseline = await census(tree, omitted=counts)
        fresh = case / "grader"
        shutil.copytree(tree, fresh, symlinks=True)
        replace_object(tree / name, after)
        if before == after == "regular":
            (tree / name).write_text("updated ordinary source\n")
        artifact, report, docker = await export_and_grade(tree, baseline, fresh, case / "logs")
        assert report.outcome == "resolved", report
        assert (fresh / name).is_symlink() if after == "symlink" else (fresh / name).read_bytes() == (tree / name).read_bytes()
        assert docker.real_phases[0:2] == ["census", "normalization"]
        rows.append({"path": name, "before": before, "after": after, "baseline_omitted": counts,
                     "delta": [(e.path, e.operation, e.object_type) for e in artifact.entries],
                     "phases": docker.real_phases, "outcome": report.outcome, "reward": report.reward})
    # v1 不做规范化；一般 file→directory 仍按真实 shell 重放。
    for v, policy in [("v1", BASELINE_MANIFEST_POLICY_V1), ("v2", BASELINE_MANIFEST_POLICY_V2)]:
        case = tmp / f"file-dir-{v}"
        tree = case / "rollout"
        tree.mkdir(parents=True)
        (tree / "config").write_text("old\n")
        baseline = await census(tree, policy)
        fresh = case / "grader"
        shutil.copytree(tree, fresh)
        (tree / "config").unlink()
        (tree / "config").mkdir()
        (tree / "config/default.json").write_text("{}\n")
        artifact, report, docker = await export_and_grade(tree, baseline, fresh, case / "logs")
        assert report.outcome == "resolved" and (fresh / "config/default.json").read_text() == "{}\n"
        assert ("normalization" in docker.real_phases) == (v == "v2")
        rows.append({"path": "config", "policy": v, "before": "regular", "after": "directory",
                     "delta": [(e.path, e.operation, e.object_type) for e in artifact.entries],
                     "phases": docker.real_phases, "outcome": report.outcome})
    return rows


async def namespace_probe(tmp):
    tree = tmp / "namespace-rollout"
    tree.mkdir()
    (tree / "app.py").write_text("print('app')\n")
    for cmd in (["git", "init", "-q"], ["git", "add", "app.py"],
                ["git", "-c", "user.name=RH2 probe", "-c", "user.email=rh2-probe@example.invalid", "commit", "-qm", "initial"],
                ["git", "checkout", "-qb", "__pycache__/probe"]):
        subprocess.run(cmd, cwd=tree, check=True, capture_output=True)
    for rel in (".harness/__pycache__/private.json", ".pytest_cache/value", "pkg/__pycache__/value"):
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("sentinel\n")
    outside = tmp / "outside"
    (outside / "__pycache__").mkdir(parents=True)
    (outside / "__pycache__/keep").write_text("outside\n")
    (tree / "linked").symlink_to(outside, target_is_directory=True)
    (tree / "regular").mkdir()
    (tree / "regular/__pycache__").write_text("ordinary\n")
    (tree / "symbolic").mkdir()
    (tree / "symbolic/.pytest_cache").symlink_to(outside, target_is_directory=True)
    before_counts = {}
    baseline = await census(tree, omitted=before_counts)
    fresh = tmp / "namespace-grader"
    shutil.copytree(tree, fresh, symlinks=True)
    head_before = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=fresh, text=True, capture_output=True)
    artifact, report, docker = await export_and_grade(tree, baseline, fresh, tmp / "namespace-logs")
    after = await census(fresh)
    head_after = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=fresh, text=True, capture_output=True)
    assert artifact.entries == () and report.outcome == "resolved"
    assert head_before.returncode == head_after.returncode == 0
    assert head_before.stdout == head_after.stdout
    assert (fresh / ".git/refs/heads/__pycache__/probe").exists()
    assert (fresh / ".harness/__pycache__/private.json").exists()
    assert (fresh / "regular/__pycache__").read_text() == "ordinary\n"
    assert (fresh / "symbolic/.pytest_cache").is_symlink() and (fresh / "linked").is_symlink()
    assert (outside / "__pycache__/keep").read_text() == "outside\n"
    assert baseline.entries == after.entries
    assert baseline.excluded_census_digest == after.excluded_census_digest
    assert compute_baseline_manifest_digest(baseline) == compute_baseline_manifest_digest(after)
    # 最小局部候选修法只在此探针实跑：沿同一 policy 先 prune 排除区，无新增状态/拒绝分支。
    preserved = tmp / "namespace-local-alternative"
    shutil.copytree(tree, preserved, symlinks=True)
    namespaces = " -o ".join(f"-path {shlex.quote('./' + ns.rstrip('/'))}" for ns in baseline.policy.excluded_namespaces)
    names = " -o ".join(f"-name {shlex.quote(n)}" for n in baseline.policy.regenerable_cache_dirs)
    alternative = f"find . -mindepth 1 \\( {namespaces} \\) -prune -o -type d \\( {names} \\) -prune -exec rm -rf -- {{}} +"
    local_fix = shell(alternative, cwd=preserved)
    preserved_manifest = await census(preserved)
    preserved_head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=preserved, text=True, capture_output=True)
    assert local_fix.exit_code == 0 and preserved_head.returncode == 0
    assert compute_baseline_manifest_digest(baseline) == compute_baseline_manifest_digest(preserved_manifest)
    assert not (preserved / ".pytest_cache").exists() and not (preserved / "pkg/__pycache__").exists()
    assert (preserved / ".harness/__pycache__/private.json").read_text() == "sentinel\n"
    return {"real_phases": docker.real_phases, "noop_artifact_entries": 0,
            "fixture_report_outcome": report.outcome, "report_limit": "评分测试输出由维护 FakeDocker 提供；Git 状态与删除是本机真实结果",
            "baseline_omitted": before_counts, "scoreable_entries_equal": baseline.entries == after.entries,
            "excluded_digest_before": baseline.excluded_census_digest, "excluded_digest_after": after.excluded_census_digest,
            "manifest_digest_equal_after_normalization": compute_baseline_manifest_digest(baseline) == compute_baseline_manifest_digest(after),
            "head_before_rc": head_before.returncode, "head_after_rc": head_after.returncode,
            "head_after_stderr": head_after.stderr.strip(), "active_branch_deleted": not (fresh / ".git/refs/heads/__pycache__/probe").exists(),
            "harness_private_file_deleted": not (fresh / ".harness/__pycache__/private.json").exists(), "regular_same_name_preserved": True,
            "symlinks_not_followed": True, "outside_sentinel_preserved": True,
            "local_alternative": {"script": alternative, "rc": local_fix.exit_code,
                                  "active_head_preserved": True, "all_manifest_identity_preserved": True,
                                  "scoreable_caches_still_removed": True, "production_source_modified": False}}


class BaselineDocker(FakeRolloutDocker):
    def __init__(self, files):
        super().__init__(exec_after_rm_raises=True)
        self.files = files

    async def __call__(self, *args, input_bytes=None):
        if args[0] == "exec" and "find ." in args[-1] and "sha256sum" in args[-1]:
            text = "".join(f"regular\t100644\t{hashlib.sha256(raw).hexdigest()}\t{path}\n" for path, raw in sorted(self.files.items()))
            if "CACHE_OMITTED" in args[-1]:
                text += "CACHE_OMITTED_DIRS\t2\nCACHE_OMITTED_FILES\t3\n"
            return ExecResult(0, text, "")
        return await super().__call__(*args, input_bytes=input_bytes)


async def conflict_probe(tmp):
    rows = []
    for i, ancestor in enumerate(["config", "config'quote", 'config"quote', r"config\name"]):
        child = ancestor + "/default.json"
        docker = BaselineDocker({child: b"old\n"})
        audit_path = tmp / f"audit-{i}.jsonl"
        inner = make_barrier({ancestor: b"new\n"})

        class CountedBarrier:
            async def establish(self, **kwargs):
                result = await inner.establish(**kwargs)
                ws = result.frozen_grading_workspace

                class CountedWorkspace:
                    async def run_bash(self, script):
                        out = await ws.run_bash(script)
                        if "CACHE_OMITTED" in script:
                            return ExecResult(out.exit_code, out.stdout + "CACHE_OMITTED_DIRS\t4\nCACHE_OMITTED_FILES\t5\n", out.stderr)
                        return out

                return dataclasses.replace(result, frozen_grading_workspace=CountedWorkspace())

        chain = _formal_chain(barrier=CountedBarrier(), docker=docker, task=make_task("swe_gym_lite::falsifier"),
                              audit_sink=lambda audit: write_execution_audit_record(None, audit, audit_path))
        delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
        audit = chain.orchestrator.audits[0]
        (receipt,) = chain.finalization.receipts
        receipt_json = receipt.model_dump(mode="json")
        # 真生产 audit writer 完成 flush+fsync 后重新从磁盘读；不是仅断言内存对象。
        stored = json.loads(audit_path.read_text().splitlines()[-1])
        (leaf,) = delivered
        verdict = _decide(_resolve(leaf))
        assert verdict.verdict == "DROP_GROUP" and not chain.grading.calls
        assert audit.lease.container_id in docker.removed
        assert receipt.rejection_evidence.object_path == child
        reason = stored["unsafe_artifact_reasons"][0]
        assert f"ancestor={ancestor}(add/regular)" in reason and f"child={child}(delete/regular)" in reason
        assert stored["physical_attempt_id"] == receipt.physical_attempt_id
        assert audit.omitted_cache_counts == {"baseline": {"dirs": 2, "files": 3}, "post": {"dirs": 4, "files": 5}}
        assert stored["omitted_cache_counts"] == audit.omitted_cache_counts
        rows.append({"ancestor": ancestor, "child": child, "receipt_rejection_evidence": receipt_json["rejection_evidence"],
                     "receipt_has_full_conflict": "ancestor_operation" in json.dumps(receipt_json),
                     "durable_audit_reason": reason, "audit_receipt_attempt_id_equal": True,
                     "workspace_removed": True, "group_disposition": verdict.verdict,
                     "in_memory_omitted_counts": audit.omitted_cache_counts,
                     "durable_audit_has_omitted_counts": "omitted_cache_counts" in stored})
        (OUT / f"conflict_audit_{i}.json").write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n")
        (OUT / f"conflict_receipt_{i}.json").write_text(json.dumps(receipt_json, ensure_ascii=False, indent=2) + "\n")
    return rows


def install_probe(tmp):
    specs = load_vendor_specs(SPEC_VENDOR_ID_SWEGYM_242429C1)
    groups = {}
    for repo, versions in specs.items():
        for version, spec in versions.items():
            command = spec.get("install")
            groups.setdefault(command, []).append(f"{repo}@{version}")
    inventory = [{"install": cmd, "spec_count": len(users), "examples": users[:4]} for cmd, users in groups.items()]
    (OUT / "vendor_install_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    bundle_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl"
    g = next(PrivateGradingBundleV2(**{k: v for k, v in row.items() if k != "schema_id"})
             for row in map(json.loads, bundle_path.read_text().splitlines()) if row["instance_id"] == "getmoto__moto-6913")
    render_lines = _v2_install_lines(g)
    shim = tmp / "shim"
    shim.mkdir()
    # 仅外部叶命令替身；Bash 控制操作、pipe、重定向和生产 trap 原样执行。无 pip/网络/构建。
    leaf = '#!/bin/bash\nprintf "%s %s\\n" "${0##*/}" "$*" >> "$FALSIFIER_CALLS"\nif [[ -n "$FALSIFIER_FAIL_MATCH" && "$*" == *"$FALSIFIER_FAIL_MATCH"* ]]; then exit 7; fi\nexit 0\n'
    for name in ("python", "pip", "bokeh", "sed"):
        p = shim / name
        p.write_text(leaf)
        p.chmod(0o755)
    dvc = specs["iterative/dvc"]["1.0"]["install"]
    dvc_last = specs["iterative/dvc"]["3.10"]["install"]
    bokeh = specs["bokeh/bokeh"]["0.12"]["install"]
    hydra = specs["facebookresearch/hydra"]["0.10"]["install"]
    cases = [("dvc_nonfinal_and", dvc, "cython<3.0.0"),
             ("dvc_or_true", dvc, "tests/requirements.txt"),
             ("dvc_simple_failure_then_success", dvc, ".[tests,dev,all_remotes,all,testing]"),
             ("dvc_last_command_failure", dvc_last, ".[tests,dev,all_remotes,all,testing]"),
             ("bokeh_pipeline_last_fails", bokeh, "setup.py develop"),
             ("hydra_blank_tail_conditional", hydra, ""),
             ("diagnostic_subshell_function_boundary", "f() { return 7; }; f; (false); false || true; false && true; false | true; true", "")]
    rows = []
    for n, (name, command, fail_match) in enumerate(cases):
        pair = []
        for with_trap in (False, True):
            cwd = tmp / f"install-{n}-{int(with_trap)}"
            (cwd / "requirements").mkdir(parents=True)
            (cwd / "requirements/requirements.txt").write_text("initial_requirement\n\n")
            (cwd / "requirements/dev.txt").write_text("initial_dev\n")
            call_log = cwd / "calls.txt"
            env = {**os.environ, "PATH": str(shim) + os.pathsep + os.environ["PATH"],
                   "FALSIFIER_CALLS": str(call_log), "FALSIFIER_FAIL_MATCH": fail_match}
            lines = [command if i == 3 else line for i, line in enumerate(render_lines)]
            if not with_trap:
                lines = [line for i, line in enumerate(lines) if i not in (2, 5)]
            script = "set -o pipefail\n" + "\n".join(lines) + '\nprintf "POST_TRAP=%s\\n" "$(trap -p ERR)"\nprintf "POST_ERRTRACE=%s\\n" "$-"\nfalse\necho POST_FALSE_REACHED\n'
            out = shell(script, cwd=cwd, env=env)
            facts = candidate_facts_from_log(out.stdout)
            assert out.exit_code == 0 and "POST_TRAP=\n" in out.stdout
            assert "E" not in next(line for line in out.stdout.splitlines() if line.startswith("POST_ERRTRACE=")).split("=", 1)[1]
            calls = call_log.read_text().splitlines() if call_log.exists() else []
            pair.append({"with_trap": with_trap, "install_rc": facts["install_rc_last_command"],
                         "failed_commands": facts["install_failed_commands"], "calls": calls,
                         "requirements_after": (cwd / "requirements/requirements.txt").read_text(),
                         "stdout": out.stdout, "stderr": out.stderr})
        assert pair[0]["install_rc"] == pair[1]["install_rc"]
        assert pair[0]["calls"] == pair[1]["calls"]
        assert pair[0]["requirements_after"] == pair[1]["requirements_after"]
        rows.append({"name": name, "command": command, "fail_match": fail_match,
                     "same_exit_status_leaf_calls_and_file_bytes": True, "runs": pair})
    return {"vendor_repo_count": len(specs), "vendor_spec_count": sum(map(len, specs.values())),
            "unique_install_including_none": len(groups), "cases": rows,
            "limit": "当前 vendor 的控制语义真实执行；pip/python 等外部叶命令是无网络替身。额外子 shell/function 用于解释观测边界，不增加支持要求。"}


async def main():
    with tempfile.TemporaryDirectory(prefix="rh2-chainfix-falsifier-") as td:
        tmp = Path(td)
        result = {"cache_matrix": await cache_matrix(tmp), "namespace_boundary": await namespace_probe(tmp),
                  "conflict_persistence": await conflict_probe(tmp)}
    (OUT / "probe_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    paths = ["adapters/slime/baseline_census.py", "adapters/slime/patch_exporter.py", "adapters/slime/prepared_task_face.py",
             "adapters/slime/generate.py", "adapters/slime/bringup.py", "adapters/slime/replay_grade.py", "grading/manager.py",
             "contracts/finalization.py", "contracts/frozen_patch.py", "contracts/baseline_manifest.py"]
    snap = {"git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "files": {"rh2/src/repoharness2/" + p: hashlib.sha256((ROOT / "rh2/src/repoharness2" / p).read_bytes()).hexdigest() for p in paths}}
    (OUT / "source_snapshot.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cache_cases": len(result["cache_matrix"]), "namespace": result["namespace_boundary"],
                      "conflict_cases": len(result["conflict_persistence"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
