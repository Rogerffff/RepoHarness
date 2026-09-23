"""CR1/CR2 有界独立复核：真实 pytest 日志 -> 生产 parser/manager，容器 I/O 使用维护替身。

所有新证据在本目录；历史证据、生产源码、维护测试只读。无 SSH/Docker/API。
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

sys.dont_write_bytecode = True
import old_probe_copy as old
import pytest
from repoharness2.envpack import scoring
from repoharness2.grading.manager import (
    ExecResult, classify_execution_failure_shape, execution_failure_trigger,
    strip_captured_sections, syntax_error_locations,
)

HERE = Path(__file__).resolve().parent
ROOT = old.ROOT
FORMATS = {"default_rA": [], "short": ["--tb=short"], "long": ["--tb=long"],
           "native": ["--tb=native"], "quiet_default": ["-q"]}
SOURCE_FILES = ["rh2/src/repoharness2/grading/manager.py", "rh2/src/repoharness2/envpack/scoring.py",
                "rh2/tests/grading/test_w3b_grader_profile_unit.py"]


def redact(text: str, repo: Path | None = None) -> str:
    if repo is not None:
        text = text.replace(str(repo.resolve()), "/testbed")
    return text.replace(str(ROOT), "<REPO>").replace(str(Path.home()), "<USER_HOME>")


def digest_sources():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_FILES}


def run_pytest(repo: Path, name: str, flags: list[str]):
    command = [sys.executable, "-B", "-m", "pytest", "--rootdir=.", "-p", "no:cacheprovider",
               "-rA", *flags, "tests/test_thing.py"]
    result = subprocess.run(command, cwd=repo, env=old.local_env(repo), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=False)
    log = redact(result.stdout, repo)
    destination = HERE / "logs" / f"{name}.log"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(log)
    return {"rc": result.returncode, "command": redact(shlex.join(command)),
            "log_path": str(destination.relative_to(HERE)), "stdout": log}


async def grade(name: str, repo: Path, run: dict, patch: str, *, refs=None, qualified=True):
    log = old._pa_log(run["stdout"], test_rc=run["rc"])
    docker = old.ProfileGraderFakeDocker(base_commit=old.BASE_COMMIT, eval_log=log)
    compile_runs = []

    async def backend(*args, input_bytes=None):
        if args[0] == "exec" and "RH2_COMPILE_EOF" in str(args[-1]):
            script = str(args[-1]).replace("cd /testbed", f"cd {shlex.quote(str(repo))}")
            result = subprocess.run(["bash"], input=script, cwd=repo, env=old.local_env(repo),
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=10, check=False)
            compile_runs.append({"script": redact(script, repo), "rc": result.returncode,
                                 "stdout": redact(result.stdout, repo)})
            return ExecResult(result.returncode, redact(result.stdout, repo), "")
        return await docker(*args, input_bytes=input_bytes)

    spec = old._pa_spec(qualified=qualified)
    if refs:
        spec = dataclasses.replace(spec, parse_log=old.parser_for(*refs))
    manager = old._pa_manager(backend, HERE / "manager" / name)
    verdict = spec.parse_log(log)
    trigger = execution_failure_trigger(verdict)
    report = await manager.grade(trajectory_id=name, workspace=old.FakeWorkspace(patch_text=patch), spec=spec)
    side = old._pa_side(manager, report)
    return {"verdict": verdict.model_dump(), "source_fields": scoring.grading_outcome_fields(verdict),
            "trigger": trigger, "shape_called_with_zero_parsed": trigger == "zero_parsed",
            "shape": classify_execution_failure_shape(log, run["rc"], zero_parsed=trigger == "zero_parsed"),
            "syntax_locations": {k: sorted(v) for k, v in syntax_error_locations(log).items()},
            "stripped_segment": strip_captured_sections(run["stdout"]),
            "report": report.model_dump(mode="json"), "decision": side["execution_failure_decision"],
            "compile_runs": compile_runs,
            "resource_reads": sum(args[0] == "exec" and "memory.events" in str(args[-1]) for args in docker.calls)}


async def main():
    result = {"method": "真实 pytest 和生产 compile 脚本，实际 SWEGradingManager.grade；容器/资源 I/O 使用维护替身",
              "python": sys.version, "pytest": pytest.__version__, "source_before": digest_sources(), "cases": {}}
    cases = result["cases"]
    for mode, flags in FORMATS.items():
        for stage in ("collection", "conftest"):
            name = f"syntax_{stage}_{mode}"
            repo = HERE / "cases" / name
            old.write(repo, "src/thing.py", "VALUE = 1\n")
            old.write(repo, "tests/test_thing.py", "from src.thing import VALUE\ndef test_feature():\n    assert VALUE == 1\ndef test_stable():\n    assert VALUE > 0\n")
            if stage == "conftest":
                old.write(repo, "tests/conftest.py", "from src.thing import VALUE\n")
            baseline = run_pytest(repo, name + "_baseline", flags)
            assert baseline["rc"] == 0
            old.write(repo, "src/thing.py", "def feature(:\n")
            candidate = run_pytest(repo, name, flags)
            assert candidate["rc"] == (2 if stage == "collection" else 4)
            cases[name] = {"baseline": baseline, "candidate": candidate,
                           "grade": await grade(name, repo, candidate, old.patch("src/thing.py", "VALUE = 1", "def feature(:"))}

        name = f"ordinary_argument_{mode}"
        repo = HERE / "cases" / name
        old.write(repo, "src/unused.py", "def unused(:\n")
        old.write(repo, "tests/test_thing.py", 'def load_metadata(source):\n    from rh2_missing_external_fixture import VALUE\n    return VALUE\nVALUE = load_metadata("src/unused.py")\ndef test_feature():\n    assert VALUE == 1\ndef test_stable():\n    assert VALUE > 0\n')
        candidate = run_pytest(repo, name, flags)
        assert candidate["rc"] == 2
        bad = await grade(name + "_bad", repo, candidate, old.patch("src/unused.py", "marker = 1", "def unused(:"))
        old.write(repo, "src/unused.py", "marker = 2\n")
        clean = await grade(name + "_clean", repo, candidate, old.patch("src/unused.py", "marker = 1", "marker = 2"))
        cases[name] = {"candidate": candidate, "bad": bad, "clean_same_log": clean}

        for child in ("python", "pytest"):
            name = f"captured_{child}_{mode}"
            repo = HERE / "cases" / name
            child_command = '[sys.executable, "-c", "import rh2_missing_child_module"]'
            if child == "pytest":
                old.write(repo, "child/test_child.py", "import rh2_missing_child_module\n")
                child_command = '[sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "child/test_child.py"]'
            tests = '''import pytest
import subprocess
import sys
from src.id_source import label
@pytest.mark.parametrize("case", [label], ids=[label])
def test_feature(case):
    if case == "after":
        subprocess.run(CHILD_COMMAND, check=True)
@pytest.mark.parametrize("case", [label], ids=[label])
def test_stable(case):
    assert isinstance(case, str)
'''.replace("CHILD_COMMAND", child_command)
            old.write(repo, "tests/test_thing.py", tests)
            old.write(repo, "src/id_source.py", 'label = "before"\n')
            before = hashlib.sha256((repo / "tests/test_thing.py").read_bytes()).hexdigest()
            baseline = run_pytest(repo, name + "_baseline", flags)
            assert baseline["rc"] == 0
            old.write(repo, "src/id_source.py", 'label = "after"\n')
            candidate = run_pytest(repo, name, flags)
            assert candidate["rc"] == 1 and "1 failed, 1 passed" in candidate["stdout"]
            after = hashlib.sha256((repo / "tests/test_thing.py").read_bytes()).hexdigest()
            assert before == after
            refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
            cases[name] = {"baseline": baseline, "candidate": candidate,
                           "test_sha256_before": before, "test_sha256_after": after,
                           "grade": await grade(name, repo, candidate,
                             old.patch("src/id_source.py", 'label = "before"', 'label = "after"'), refs=refs, qualified=False)}

    result["source_after"] = digest_sources()
    assert result["source_before"] == result["source_after"], "被审源码期间发生变化，请勿把混合版本当作单一基线"
    result["helper_sha256"] = hashlib.sha256((HERE / "old_probe_copy.py").read_bytes()).hexdigest()
    (HERE / "probe_pytest_shapes.json").write_text(redact(json.dumps(result, ensure_ascii=False, indent=2)) + "\n")
    summary = {}
    for name, data in cases.items():
        for variant in ("grade", "bad", "clean_same_log"):
            if variant in data:
                item = data[variant]
                summary[f"{name}/{variant}"] = {"reward": item["report"]["reward"],
                    "category": item["report"]["failure_category"], "decision": item["decision"]["kind"] if item["decision"] else None,
                    "shape": item["shape"]["rule"] if item["shape"] else None,
                    "locations": item["syntax_locations"]}
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
