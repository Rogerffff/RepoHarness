"""独立审查 CPU 反例：真实 pytest/compile 输出进入生产 manager，Docker 使用维护测试替身。

从仓库根目录运行：
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/implementation_review_20260916/training/probe_training_semantics.py

不执行 Docker/SSH/API，不改生产源码或维护测试。临时题目全部在 TemporaryDirectory 中。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2" / "src").is_dir())
for p in (ROOT / "rh2" / "src", ROOT / "rh2" / "tests", ROOT / "rh2" / "tests" / "grading", ROOT / "rh2" / "tests" / "contracts"):
    sys.path.insert(0, str(p))

from repoharness2.contracts.grading import GradingReport
from repoharness2.envpack import scoring
from repoharness2.envpack.bundles_v2 import PrivateGradingBundleV2
from repoharness2.envpack.spec_vendor import SPEC_VENDOR_ID_SWEGYM_242429C1, derive_eval_cmd
from repoharness2.grading.manager import (
    EnvQualification, ExecResult, execution_failure_trigger,
    grading_image_identity, grading_scripts_digest, render_compile_probe_script,
)
from contract_samples import valid_grading_report
from grading_fixtures import FakeWorkspace
from test_w3b_grader_profile_unit import (
    BASE_COMMIT, ProfileGraderFakeDocker, _pa_log, _pa_manager, _pa_side, _pa_spec,
)


def write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def local_env(repo: Path, *, extra: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.update({
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(repo) + (os.pathsep + str(extra) if extra else ""),
        "PATH": str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""),
    })
    return env


def pytest_run(repo: Path, *, extra: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-rA", "-q", "tests/test_thing.py"],
        cwd=repo, env=local_env(repo, extra=extra), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=20,
    )


def compile_run(repo: Path, paths: list[str]) -> subprocess.CompletedProcess[str]:
    script = render_compile_probe_script(paths, env_lines=["#!/bin/bash", f"cd {shlex.quote(str(repo))}"])
    return subprocess.run(
        ["bash"], input=script, cwd=repo, env=local_env(repo), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=10,
    )


def patch(path: str, before: str, after: str) -> str:
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{before}\n+{after}\n"


def set_qualification(spec, *, install_rc: int | None = None):
    return dataclasses.replace(spec, env_qualification=EnvQualification(
        image_identity=grading_image_identity(spec), scripts_digest=grading_scripts_digest(spec),
        reference_missing_count=0, source="cpu-probe:prior-gold", qualified_at_utc="2026-09-16T00:00:00Z",
        install_rc_last_command=install_rc,
    ))


def parser_for(f2p: list[str], p2p: list[str]):
    bundle = PrivateGradingBundleV2(
        instance_id="getmoto__moto-0001", repo="getmoto/moto", repo_key_lower="getmoto/moto", version="5.0",
        base_commit=BASE_COMMIT, test_patch="diff --git a/tests/t.py b/tests/t.py\n--- a/tests/t.py\n+++ b/tests/t.py\n+x\n",
        fail_to_pass=f2p, pass_to_pass=p2p,
        eval_cmd=derive_eval_cmd(SPEC_VENDOR_ID_SWEGYM_242429C1, "getmoto/moto", "5.0"),
        spec_vendor_id=SPEC_VENDOR_ID_SWEGYM_242429C1,
    )
    return lambda log: scoring.parse_eval_log_v2(bundle, log)


async def grade_case(name: str, *, log: str, patch_text: str, probe_output: str, spec=None, probe_rc=0, unknown_resources=False):
    temporary_manager = tempfile.TemporaryDirectory(prefix="rh2-manager-evidence-")
    directory = Path(temporary_manager.name)
    docker = ProfileGraderFakeDocker(base_commit=BASE_COMMIT, eval_log=log)
    docker.compile_probe_stdout, docker.compile_probe_exit_code = probe_output, probe_rc
    backend = docker
    if unknown_resources:
        async def resource_unavailable(*args, input_bytes=None):
            if (args[0] == "exec" and "memory.events" in str(args[-1])) or (args[0] == "inspect" and "OOMKilled" in str(args)):
                return ExecResult(1, "", "probe unavailable")
            return await docker(*args, input_bytes=input_bytes)
        backend = resource_unavailable
    manager = _pa_manager(backend, directory)
    spec = spec or _pa_spec()
    verdict = spec.parse_log(log)
    old_fields = scoring.grading_outcome_fields(verdict)
    report = await manager.grade(trajectory_id=name, workspace=FakeWorkspace(patch_text=patch_text), spec=spec)
    side = _pa_side(manager, report)
    answer = {
        "parsed_verdict": verdict.model_dump(), "source_fields_before_pa_override": old_fields,
        "trigger": execution_failure_trigger(verdict), "report": report.model_dump(mode="json"),
        "decision": side["execution_failure_decision"],
    }
    temporary_manager.cleanup()
    return answer


async def main() -> None:
    result = {"method": "真实本机 pytest/compile stdout + 生产 SWEGradingManager.grade + 维护 ProfileGraderFakeDocker；未执行容器"}
    with tempfile.TemporaryDirectory(prefix="rh2-training-review-") as temporary:
        tmp = Path(temporary)
        repo, external = tmp / "unrelated", tmp / "external"
        write(repo, "src/unused.py", "marker = 1\n")
        write(external, "qualified_external_fixture.py", "VALUE = 1\n")
        write(repo, "tests/test_thing.py", "from qualified_external_fixture import VALUE\ndef test_feature():\n    assert VALUE == 1\ndef test_stable():\n    assert VALUE > 0\n")
        baseline = pytest_run(repo, extra=external)
        assert baseline.returncode == 0, baseline.stdout
        # 故障注入在候选目录之外：依赖不可用；它与候选 unused.py 的语法相互独立。
        (external / "qualified_external_fixture.py").unlink()
        write(repo, "src/unused.py", "def unused(:\n")
        failed = pytest_run(repo, extra=external)
        probe = compile_run(repo, ["src/unused.py"])
        assert failed.returncode == 2 and "ModuleNotFoundError" in failed.stdout
        assert "unused.py" not in failed.stdout and "RH2_COMPILE_ERROR=src/unused.py:SyntaxError" in probe.stdout
        result["unrelated_syntax"] = {
            "baseline_rc": baseline.returncode, "baseline_log": baseline.stdout,
            "failure_rc": failed.returncode, "failure_log": failed.stdout, "compile_rc": probe.returncode, "compile_log": probe.stdout,
            "bad_unused": await grade_case("unrelated_bad_unused", log=_pa_log(failed.stdout, test_rc=2),
                patch_text=patch("src/unused.py", "marker = 1", "def unused(:"), probe_output=probe.stdout),
        }
        write(repo, "src/unused.py", "marker = 2\n")
        clean_probe = compile_run(repo, ["src/unused.py"])
        result["unrelated_syntax"]["clean_unused_control"] = await grade_case("unrelated_clean_unused", log=_pa_log(failed.stdout, test_rc=2),
            patch_text=patch("src/unused.py", "marker = 1", "marker = 2"), probe_output=clean_probe.stdout)

        # 所有 reference ID 都改变，但 pytest 真实完成两个测试（1 failed + 1 passed），没有全局收集错误。
        repo_ids = tmp / "parameter_ids"
        write(repo_ids, "src/id_source.py", 'label = "before"\n')
        write(repo_ids, "tests/test_thing.py", 'import pytest\nfrom src.id_source import label\n@pytest.mark.parametrize("case", [label], ids=[label])\ndef test_feature(case):\n    assert case == "before"\n@pytest.mark.parametrize("case", [label], ids=[label])\ndef test_stable(case):\n    assert isinstance(case, str)\n')
        before = pytest_run(repo_ids)
        assert before.returncode == 0, before.stdout
        write(repo_ids, "src/id_source.py", 'label = "after"\n')
        after = pytest_run(repo_ids)
        assert after.returncode == 1 and "1 failed, 1 passed" in after.stdout, after.stdout
        refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
        spec_ids = dataclasses.replace(_pa_spec(qualified=False), parse_log=parser_for(*refs))
        log_ids = _pa_log(after.stdout, test_rc=1)
        result["all_reference_missing_completed_tests"] = {
            "baseline_rc": before.returncode, "baseline_log": before.stdout,
            "candidate_rc": after.returncode, "candidate_log": after.stdout,
            "qualified": await grade_case("ids_qualified", log=log_ids, patch_text=patch("src/id_source.py", 'label = "before"', 'label = "after"'),
                probe_output="RH2_COMPILE_OK=src/id_source.py\n", spec=set_qualification(spec_ids)),
            "without_qualification": await grade_case("ids_unqualified", log=log_ids, patch_text=patch("src/id_source.py", 'label = "before"', 'label = "after"'),
                probe_output="RH2_COMPILE_OK=src/id_source.py\n", spec=spec_ids),
        }

        # F3 复证器仍从候选工作目录 import json；先看真实输出，再交回同一 manager 分支。
        shadow = tmp / "shadow"
        write(shadow, "src/thing.py", "def feature(:\n")
        write(shadow, "json.py", 'print("CANDIDATE_JSON_EXECUTED=1")\nraise RuntimeError("candidate json.py executed by compile probe")\n')
        shadow_probe = compile_run(shadow, ["src/thing.py"])
        assert "CANDIDATE_JSON_EXECUTED=1" in shadow_probe.stdout and shadow_probe.returncode == 1
        from test_w3b_grader_profile_unit import _PA_COLLECTION_FAIL_SEGMENT
        syntax_log = _pa_log(_PA_COLLECTION_FAIL_SEGMENT, test_rc=2)
        result["compile_probe_imports_candidate_json"] = {
            "compile_rc": shadow_probe.returncode, "compile_log": shadow_probe.stdout,
            "report": await grade_case("shadow_json", log=syntax_log, patch_text=patch("src/thing.py", "value = 1", "def feature(:"),
                probe_output=shadow_probe.stdout, probe_rc=shadow_probe.returncode),
        }
        # 只记录当前 unknown 事实的处理，不把缺一个可选指标自动判为新缺陷。
        result["all_termination_facts_unknown"] = await grade_case("all_termination_unknown",
            log=syntax_log.replace("RH2_TEST_RC=2\n", ""), patch_text=patch("src/thing.py", "value = 1", "def feature(:"),
            probe_output="RH2_COMPILE_ERROR=src/thing.py:SyntaxError:line=1:invalid syntax\n", unknown_resources=True)

    base = valid_grading_report()
    r2e_fields = {"grading_semantics": "r2e_expected_map", "f2p_pass_count": None, "f2p_total_count": None, "p2p_fail_count": None, "p2p_total_count": None}
    invalid = {**base, **r2e_fields, "outcome": "unresolved", "failure_category": "tests_failed", "reward": 0.0,
               "expected_match_count": 7, "expected_total_count": 0}
    accepted = GradingReport.model_validate(invalid)
    result["r2e_impossible_counts_accepted"] = accepted.model_dump(mode="json")
    expected = {"a": "PASSED", "b": "FAILED", "c": "ERROR", "d": "SKIPPED"}
    result["r2e_union_semantics"] = []
    for observed in (expected, {**expected, "extra": "PASSED"}, {"a": "PASSED"}, {}):
        match = scoring.expected_map_matches(expected, observed)
        report = GradingReport.model_validate({**base, **scoring.grading_outcome_fields_r2e(match)})
        result["r2e_union_semantics"].append({"match": match.model_dump(), "outcome": report.outcome, "reward": report.reward})

    tracked = ["rh2/src/repoharness2/grading/manager.py", "rh2/src/repoharness2/contracts/grading.py", "rh2/src/repoharness2/envpack/scoring.py",
               "rh2/src/repoharness2/adapters/slime/prepared_task_face.py", "rh2/src/repoharness2/adapters/slime/replay_grade.py"]
    result["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked}
    # 临时目录路径换成稳定标识，文档不保存本机私有路径。
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    for private_path, label in (
        (str(Path(temporary).resolve()), "<CPU_TEMP>"), (temporary, "<CPU_TEMP>"),
        (str(ROOT), "<REPO>"), (str(Path.home()), "<USER_HOME>"),
    ):
        encoded = encoded.replace(private_path, label)
    (HERE / "probe_training_semantics.json").write_text(encoded + "\n", encoding="utf-8")
    print(json.dumps({
        "unrelated_bad_unused": result["unrelated_syntax"]["bad_unused"]["report"]["failure_category"],
        "unrelated_clean_control": result["unrelated_syntax"]["clean_unused_control"]["report"]["failure_category"],
        "normal_tests_all_reference_missing": result["all_reference_missing_completed_tests"]["qualified"]["report"]["failure_category"],
        "compile_probe_shadow_rc": result["compile_probe_imports_candidate_json"]["compile_rc"],
        "r2e_impossible_counts": [accepted.expected_match_count, accepted.expected_total_count],
        "all_termination_unknown": result["all_termination_facts_unknown"]["report"]["failure_category"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
