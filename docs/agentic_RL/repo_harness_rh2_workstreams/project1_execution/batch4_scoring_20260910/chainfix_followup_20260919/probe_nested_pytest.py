"""主审独立重现：固定父测试捕获真实子 pytest 输出，候选仅改变参数 label。"""
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "independent"))
spec = importlib.util.spec_from_file_location("nested_followup_helpers", BASE / "independent/probe_pytest_shapes.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
helpers.HERE = BASE / "root_nested"
helpers.HERE.mkdir(exist_ok=True)


async def main():
    repo = helpers.HERE / "case"
    tests = '''import pytest
import subprocess
import sys
from src.id_source import label
@pytest.mark.parametrize("case", [label], ids=[label])
def test_feature(case):
    if case == "after":
        subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "child/test_child.py"], check=True)
@pytest.mark.parametrize("case", [label], ids=[label])
def test_stable(case):
    assert isinstance(case, str)
'''
    helpers.old.write(repo, "tests/test_thing.py", tests)
    helpers.old.write(repo, "child/test_child.py", "import rh2_missing_child_module\n")
    helpers.old.write(repo, "src/id_source.py", 'label = "before"\n')
    before_sha = hashlib.sha256((repo / "tests/test_thing.py").read_bytes()).hexdigest()
    baseline = helpers.run_pytest(repo, "baseline", [])
    helpers.old.write(repo, "src/id_source.py", 'label = "after"\n')
    candidate = helpers.run_pytest(repo, "candidate", [])
    after_sha = hashlib.sha256((repo / "tests/test_thing.py").read_bytes()).hexdigest()
    assert baseline["rc"] == 0 and "2 passed" in baseline["stdout"]
    assert candidate["rc"] == 1 and "1 failed, 1 passed" in candidate["stdout"]
    assert before_sha == after_sha
    refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
    grade = await helpers.grade("nested", repo, candidate,
        helpers.old.patch("src/id_source.py", 'label = "before"', 'label = "after"'), refs=refs, qualified=False)
    assert grade["source_fields"]["reward"] == 0.0
    assert grade["report"]["reward"] is None
    assert grade["decision"]["rule"] == "pytest_error_collecting"
    report = {"test_sha_before": before_sha, "test_sha_after": after_sha,
              "baseline": baseline, "candidate": candidate, "grade": grade}
    (helpers.HERE / "result.json").write_text(helpers.redact(json.dumps(report, ensure_ascii=False, indent=2)) + "\n")
    print(json.dumps({"same_tests": before_sha == after_sha, "parent_rc": candidate["rc"],
                      "source_reward": grade["source_fields"]["reward"], "actual_reward": grade["report"]["reward"],
                      "rule": grade["decision"]["rule"]}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
