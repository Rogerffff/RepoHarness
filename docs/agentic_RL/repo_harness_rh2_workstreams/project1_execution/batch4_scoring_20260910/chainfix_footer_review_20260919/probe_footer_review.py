"""CR2' 窄复核：真实 pytest 收尾、原真机日志和实际 miles 组运输。

只写本审查目录；生产源码/维护测试/历史证据只读。Docker 和模型用维护替身，
parser、manager、orchestrator、DefaultDataBuffer 与训练转换使用真实生产实现。
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "matrix"))
import probe_pytest_shapes as matrix
from repoharness2.grading.manager import outer_session_summary, outer_session_completed_normally


def footer_matrix():
    rows = {}
    for border in (True, False):
        for name, body, normal in (
            ("passed", "2 passed", True),
            ("failed_passed", "1 failed, 1 passed", True),
            ("singular_error", "1 error, 1 passed", False),
            ("plural_errors", "2 errors, 1 passed", False),
            ("no_tests", "no tests ran", False),
            ("rerun_deselected", "1 passed, 2 rerun, 3 deselected, 4 warnings", True),
            ("xfailed_xpassed", "1 xfailed, 1 xpassed, 2 skipped", True),
        ):
            for suffix in ("", " (0:00:01)"):
                line = f"{body} in 1.20s{suffix}"
                if border:
                    line = "===== " + line + " ====="
                rows[f"{'bordered' if border else 'quiet'}_{name}_{bool(suffix)}"] = {
                    "line": line, "summary": outer_session_summary(line + "\n"),
                    "normal": outer_session_completed_normally(line + "\n"), "expected_normal": normal,
                }
    return rows


async def main():
    before = matrix.digest_sources()
    matrix.HERE = HERE / "extra"
    matrix.HERE.mkdir()
    result = {"method": "真实进程日志 + 当前生产评分/组运输；容器操作为维护替身", "footer_formats": footer_matrix()}
    saved = json.loads((HERE / "matrix/probe_pytest_shapes.json").read_text())
    cases = {}
    # 已有真实镜像 Python 3.9 / pytest 6.2.3 日志，不重跑云端作业。
    remote = json.loads((HERE.parent / "chainfix_followup_20260919/remote_nested_pytest.json").read_text())
    run = next(r for r in remote["result"]["rows"] if r["label"] == "after")
    refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
    patch = matrix.old.patch("src/id_source.py", 'label = "before"', 'label = "after"')
    repo = HERE / "matrix/cases/captured_pytest_default_rA"
    grade = await matrix.grade("saved_pytest623", repo, run, patch, refs=refs, qualified=False)
    cases["saved_pytest623"] = {"run": run, "grade": grade, "expected_reward": 0.0}
    assert grade["report"]["reward"] == 0.0 and grade["decision"]["kind"] == "source_rule"
    for name in ("captured_pytest_default_rA", "captured_pytest_quiet_default"):
        c = saved["cases"][name]
        cases[name] = {"run": c["candidate"], "grade": c["grade"], "expected_reward": 0.0}

    # 对照：真实外层收集中断。收集的测试模块会先运行一个成功的子 pytest；
    # 候选模块缺依赖，外层根本没执行参考测试。无资格时应保持未确定 None。
    for mode, flags in (("default", []), ("quiet", ["-q"])):
        name = "outer_collection_child_pass_" + mode
        repo = matrix.HERE / "cases" / name
        matrix.old.write(repo, "child/test_child.py", "def test_child():\n    assert True\n")
        matrix.old.write(repo, "src/thing.py", "VALUE = 1\n")
        matrix.old.write(repo, "tests/test_thing.py", '''import subprocess, sys
subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-rA", "child/test_child.py"], check=True)
from src.thing import VALUE
def test_feature():
    assert VALUE == 1
def test_stable():
    assert VALUE > 0
''')
        baseline = matrix.run_pytest(repo, name + "_baseline", flags)
        assert baseline["rc"] == 0
        matrix.old.write(repo, "src/thing.py", "from rh2_missing_fixture_dependency import VALUE\n")
        run = matrix.run_pytest(repo, name, flags)
        assert run["rc"] == 2
        local_refs = (["tests/test_thing.py::test_feature"], ["tests/test_thing.py::test_stable"])
        patch = matrix.old.patch("src/thing.py", "VALUE = 1", "from rh2_missing_fixture_dependency import VALUE")
        grade = await matrix.grade(name, repo, run, patch, refs=local_refs, qualified=False)
        cases[name] = {"baseline": baseline, "run": run, "grade": grade, "expected_reward": None}

    for c in cases.values():
        c["selected_summary"] = outer_session_summary(c["run"]["stdout"])
        c["final_output_line"] = c["run"]["stdout"].splitlines()[-1]
    result["cases"] = cases

    sys.path.insert(0, str(HERE / "transport"))
    import group_transport_probe as transport
    spec = importlib.util.spec_from_file_location("footer_review_world", matrix.ROOT / "rh2/tests/adapters_miles/conftest.py")
    fixtures = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fixtures
    spec.loader.exec_module(fixtures)
    scope = fixtures._vendor_slime_world.__wrapped__()
    next(scope)
    try:
        world = fixtures._World()
        world.install_sglang_stub()
        result["groups"] = {}
        for name in ("saved_pytest623", "captured_pytest_quiet_default", "outer_collection_child_pass_quiet"):
            c = cases[name]
            collection = name.startswith("outer_collection")
            group_refs = (["tests/test_thing.py::test_feature"], ["tests/test_thing.py::test_stable"]) if collection else refs
            paths = {"src/thing.py": b"from rh2_missing_fixture_dependency import VALUE\n"} if collection else {"src/id_source.py": b'label = "after"\n'}
            result["groups"][name] = await transport.run_group(world, name,
                bad_log=matrix.old._pa_log(c["run"]["stdout"], test_rc=c["run"]["rc"]),
                compile_out="", paths=paths, refs=group_refs, qualified=False)
        assert result["groups"]["saved_pytest623"]["train_data"]["raw_reward"] == [1.0, 0.0]
    finally:
        try:
            next(scope)
        except StopIteration:
            pass
    assert before == matrix.digest_sources()
    result["source_sha256"] = before
    (HERE / "footer_review_result.json").write_text(matrix.redact(json.dumps(result, ensure_ascii=False, indent=2)) + "\n")
    print(json.dumps({name: {"expected": c["expected_reward"], "actual": c["grade"]["report"]["reward"],
        "decision": c["grade"]["decision"]["kind"], "selected_summary": c["selected_summary"],
        "actual_last_line": c["final_output_line"]} for name,c in cases.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
