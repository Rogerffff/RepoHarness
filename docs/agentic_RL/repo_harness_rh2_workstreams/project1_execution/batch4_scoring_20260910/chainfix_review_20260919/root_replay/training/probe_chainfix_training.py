"""R1–R4 独立 CPU 复核；不调用 Docker/SSH/GPU/API，不修改实现或维护测试。

真实 pytest 与生产内存 compile renderer；真实 manager，容器 I/O 复用维护替身。
旧 helper 已复制进本次目录，历史 evidence 保持只读。
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

sys.dont_write_bytecode = True
import old_probe_copy as old
from repoharness2.envpack import scoring
from repoharness2.grading.manager import ExecResult, classify_execution_failure_shape, execution_failure_trigger

HERE = Path(__file__).resolve().parent
ROOT = old.ROOT
CASES = HERE / "cases"
CASES.mkdir(exist_ok=True)


def redact(text: str, repo: Path | None = None) -> str:
    if repo is not None:
        text = text.replace(str(repo.resolve()), "/testbed")
    return text.replace(str(ROOT), "<REPO>").replace(str(Path.home()), "<USER_HOME>")


def write(repo: Path, path: str, text: str):
    old.write(repo, path, text)


def pytest_run(repo: Path, *, extra: Path | None = None, args: list[str] | None = None):
    run = subprocess.run([sys.executable, "-B", "-m", "pytest", "--rootdir=.", "-p", "no:cacheprovider", "-rA", "-q", *(args or []), "tests/test_thing.py"],
                         cwd=repo, env=old.local_env(repo, extra=extra), text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=20)
    return {"returncode": run.returncode, "stdout": redact(run.stdout, repo)}


def compile_run(repo: Path, paths: list[str]):
    run = old.compile_run(repo, paths)
    return {"returncode": run.returncode, "stdout": redact(run.stdout, repo)}


async def grade_case(name: str, repo: Path, log: str, patch_text: str, *, spec=None, pids=0, oom=0, oom_killed=False, unknown=False):
    docker = old.ProfileGraderFakeDocker(base_commit=old.BASE_COMMIT, eval_log=log)
    docker.pids_events_stdout = f"max {pids}\n"
    docker.memory_events_stdout = f"oom_kill {oom}\n"
    docker.oom_killed = oom_killed
    compile_runs = []

    async def backend(*args, input_bytes=None):
        if args[0] == "exec" and "RH2_COMPILE_EOF" in str(args[-1]):
            script = str(args[-1]).replace("cd /testbed", f"cd {shlex.quote(str(repo))}")
            run = subprocess.run(["bash"], input=script, cwd=repo, env=old.local_env(repo), text=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=10)
            compile_runs.append({"script": redact(script, repo), "rc": run.returncode, "stdout": redact(run.stdout, repo)})
            return ExecResult(run.returncode, redact(run.stdout, repo), "")
        if unknown and ((args[0] == "exec" and "memory.events" in str(args[-1])) or (args[0] == "inspect" and "OOMKilled" in str(args))):
            return ExecResult(1, "", "cpu-probe:resource observation unavailable")
        return await docker(*args, input_bytes=input_bytes)

    manager = old._pa_manager(backend, HERE / "manager" / name)
    spec = spec or old._pa_spec()
    verdict = spec.parse_log(log)
    report = await manager.grade(trajectory_id=name, workspace=old.FakeWorkspace(patch_text=patch_text), spec=spec)
    side = old._pa_side(manager, report)
    return {"verdict": verdict.model_dump(), "source_fields": scoring.grading_outcome_fields(verdict),
            "shape": classify_execution_failure_shape(log, side["candidate"].get("test_rc")),
            "trigger": execution_failure_trigger(verdict), "report": report.model_dump(mode="json"),
            "decision": side["execution_failure_decision"], "compile_runs": compile_runs,
            "resource_reads": sum(args[0] == "exec" and "memory.events" in str(args[-1]) for args in docker.calls)}


async def main():
    result = {"method": "真实 pytest + 真实 python -I -S 内存 compile；真实 SWEGradingManager.grade；容器/资源读数为有界替身，无容器执行"}
    external = CASES / "external"
    # 旧 R1 原反例：不相干的坏文件没有出现在失败日志。
    unrelated = CASES / "unrelated"
    write(external, "qualified_external_fixture.py", "VALUE = 1\n")
    write(unrelated, "src/unused.py", "marker = 1\n")
    write(unrelated, "tests/test_thing.py", "from qualified_external_fixture import VALUE\ndef test_feature():\n    assert VALUE == 1\ndef test_stable():\n    assert VALUE > 0\n")
    base = pytest_run(unrelated, extra=external)
    assert base["returncode"] == 0
    (external / "qualified_external_fixture.py").unlink()
    write(unrelated, "src/unused.py", "def unused(:\n")
    fail = pytest_run(unrelated, extra=external)
    assert fail["returncode"] == 2 and "unused.py" not in fail["stdout"]
    result["old_r1_unrelated"] = {"baseline": base, "pytest": fail, "grade": await grade_case("old_r1_unrelated", unrelated, old._pa_log(fail["stdout"], test_rc=2), old.patch("src/unused.py", "marker = 1", "def unused(:"))}

    # 新边界：pytest 真回溯展示调用参数中的路径；load_metadata 并没有读/导入该文件。
    mention = CASES / "mentioned_argument"
    write(external, "qualified_external_fixture.py", "VALUE = 1\n")
    write(mention, "src/unused.py", "marker = 1\n")
    write(mention, "tests/test_thing.py", 'def load_metadata(source):\n    from qualified_external_fixture import VALUE\n    return VALUE\nVALUE = load_metadata("src/unused.py")\ndef test_feature():\n    assert VALUE == 1\ndef test_stable():\n    assert VALUE > 0\n')
    base = pytest_run(mention, extra=external)
    assert base["returncode"] == 0
    (external / "qualified_external_fixture.py").unlink()
    write(mention, "src/unused.py", "def unused(:\n")
    fail = pytest_run(mention, extra=external)
    assert fail["returncode"] == 2 and 'load_metadata("src/unused.py")' in fail["stdout"]
    log = old._pa_log(fail["stdout"], test_rc=2)
    bad = await grade_case("r1_mentioned_bad", mention, log, old.patch("src/unused.py", "marker = 1", "def unused(:"))
    write(mention, "src/unused.py", "marker = 2\n")
    clean = await grade_case("r1_mentioned_clean", mention, log, old.patch("src/unused.py", "marker = 1", "marker = 2"))
    result["r1_path_in_argument_not_exception_location"] = {"baseline": base, "pytest": fail, "bad": bad, "clean_same_log": clean}

    # 真正候选 SyntaxError：collection 与 conftest 启动两类仍应保留为负样本。
    syntax = CASES / "syntax"
    write(syntax, "src/thing.py", "VALUE = 1\n")
    (syntax / "tests/conftest.py").unlink(missing_ok=True)
    write(syntax, "tests/test_thing.py", "from src.thing import VALUE\ndef test_feature():\n    assert VALUE == 1\ndef test_stable():\n    assert VALUE > 0\n")
    base = pytest_run(syntax)
    assert base["returncode"] == 0
    write(syntax, "src/thing.py", "def feature(:\n")
    fail = pytest_run(syntax)
    assert fail["returncode"] == 2 and "SyntaxError" in fail["stdout"]
    log = old._pa_log(fail["stdout"], test_rc=2)
    delta = old.patch("src/thing.py", "VALUE = 1", "def feature(:")
    result["r3_termination_matrix"] = {"baseline": base, "pytest": fail,
        "known_zero": await grade_case("r3_known_zero", syntax, log, delta),
        "pids_event_only": await grade_case("r3_pids_event_only", syntax, log, delta, pids=1),
        "oom_positive": await grade_case("r3_oom", syntax, log, delta, oom=1),
        "all_unknown": await grade_case("r3_all_unknown", syntax, log.replace("RH2_TEST_RC=2\n", ""), delta, unknown=True),
        "test_rc_unknown": await grade_case("r3_rc_unknown", syntax, log.replace("RH2_TEST_RC=2\n", ""), delta),
    }
    write(syntax, "tests/conftest.py", "from src.thing import VALUE\n")
    startup = pytest_run(syntax)
    assert startup["returncode"] == 4 and "ImportError while loading conftest" in startup["stdout"]
    result["r1_startup_positive"] = {"pytest": startup, "grade": await grade_case("r1_startup", syntax, old._pa_log(startup["stdout"], test_rc=4), delta)}

    # R2：候选同名模块、PYTHONPATH 自动 site、缓存路径冲突均不得执行或阻断复证。
    shadow = CASES / "shadow"
    write(shadow, "src/bad.py", "def f(:\n")
    write(shadow, "src/good.py", "VALUE = 1\n")
    write(shadow, "src/__pycache__", "regular file cache conflict\n")
    for name in ("json.py", "py_compile.py", "sitecustomize.py", "usercustomize.py"):
        write(shadow, name, "print('CANDIDATE_IMPORT_EXECUTED=1')\nraise RuntimeError('candidate imported')\n")
    result["r2_isolated_compile"] = compile_run(shadow, ["src/bad.py", "src/good.py", "json.py", "py_compile.py", "sitecustomize.py", "usercustomize.py"])
    assert result["r2_isolated_compile"]["returncode"] == 0
    assert "CANDIDATE_IMPORT_EXECUTED" not in result["r2_isolated_compile"]["stdout"]

    # 旧 R4 原反例与正常完成的子进程 traceback 对照：只改变测试内部失败形状。
    ids = CASES / "ids"
    write(ids, "src/id_source.py", 'label = "before"\n')
    tests = 'import pytest\nimport subprocess\nimport sys\nfrom src.id_source import label\n@pytest.mark.parametrize("case", [label], ids=[label])\ndef test_feature(case):\n    BODY\n@pytest.mark.parametrize("case", [label], ids=[label])\ndef test_stable(case):\n    assert isinstance(case, str)\n'
    write(ids, "tests/test_thing.py", tests.replace("BODY", 'assert case == "before"'))
    base = pytest_run(ids)
    assert base["returncode"] == 0
    write(ids, "src/id_source.py", 'label = "after"\n')
    simple = pytest_run(ids)
    assert simple["returncode"] == 1 and "1 failed, 1 passed" in simple["stdout"]
    refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
    qualified = old.set_qualification(dataclasses.replace(old._pa_spec(qualified=False), parse_log=old.parser_for(*refs)))
    delta_ids = old.patch("src/id_source.py", 'label = "before"', 'label = "after"')
    result["old_r4_completed"] = {"baseline": base, "pytest": simple, "grade": await grade_case("old_r4", ids, old._pa_log(simple["stdout"], test_rc=1), delta_ids, spec=qualified, unknown=True)}
    write(ids, "tests/test_thing.py", tests.replace("BODY", 'subprocess.run([sys.executable, "-c", "import qualified_external_fixture"], check=True)'))
    write(ids, "src/id_source.py", 'label = "before"\n')
    write(external, "qualified_external_fixture.py", "VALUE = 1\n")
    nested_base = pytest_run(ids, extra=external)
    assert nested_base["returncode"] == 0 and "2 passed" in nested_base["stdout"]
    write(ids, "src/id_source.py", 'label = "after"\n')
    (external / "qualified_external_fixture.py").unlink()
    nested = pytest_run(ids, extra=external)
    assert nested["returncode"] == 1 and "1 failed, 1 passed" in nested["stdout"]
    result["r4_completed_nested_traceback"] = {"baseline": nested_base, "pytest": nested,
        "all_refs_missing": await grade_case("r4_nested", ids, old._pa_log(nested["stdout"], test_rc=1), delta_ids, spec=qualified),
        "one_reference_present": await grade_case("r4_nested_partial_refs", ids, old._pa_log(nested["stdout"], test_rc=1), delta_ids, spec=dataclasses.replace(qualified, parse_log=old.parser_for([refs[0][0]], ["tests/test_thing.py::test_stable[after]"]))),
        "one_reference_present_and_pids_event": await grade_case("r4_nested_partial_refs_pids", ids, old._pa_log(nested["stdout"], test_rc=1), delta_ids, pids=1, spec=dataclasses.replace(qualified, parse_log=old.parser_for([refs[0][0]], ["tests/test_thing.py::test_stable[after]"]))),
    }
    files = ["rh2/src/repoharness2/grading/manager.py", "rh2/src/repoharness2/envpack/scoring.py", "rh2/tests/grading/test_w3b_grader_profile_unit.py", "rh2/tests/adapters/test_batch4_pa_transport.py"]
    result["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files}
    result["old_probe_copy_sha256"] = hashlib.sha256((HERE / "old_probe_copy.py").read_bytes()).hexdigest()
    (HERE / "probe_chainfix_training.json").write_text(redact(json.dumps(result, ensure_ascii=False, indent=2)) + "\n")
    summary = {}
    for name, item in result.items():
        if isinstance(item, dict):
            for variant, value in item.items():
                if isinstance(value, dict) and "report" in value:
                    summary[f"{name}/{variant}"] = {"category": value["report"]["failure_category"], "reward": value["report"]["reward"], "decision": value["decision"]["kind"] if value["decision"] else None}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
