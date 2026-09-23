"""R4 固定测试对照：只改变候选 label，测试文件字节保持不变。"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json

import probe_chainfix_training as probe


async def main():
    repo = probe.HERE / "cases" / "r4_fixed_tests"
    test_source = '''import pytest
import subprocess
import sys
from src.id_source import label
@pytest.mark.parametrize("case", [label], ids=[label])
def test_feature(case):
    if case == "after":
        subprocess.run([sys.executable, "-c", "import rh2_missing_child_module"], check=True)
@pytest.mark.parametrize("case", [label], ids=[label])
def test_stable(case):
    assert isinstance(case, str)
'''
    probe.write(repo, "tests/test_thing.py", test_source)
    probe.write(repo, "src/id_source.py", 'label = "before"\n')
    sha_before = hashlib.sha256((repo / "tests/test_thing.py").read_bytes()).hexdigest()
    baseline = probe.pytest_run(repo)
    assert baseline["returncode"] == 0 and "2 passed" in baseline["stdout"]
    probe.write(repo, "src/id_source.py", 'label = "after"\n')
    candidate = probe.pytest_run(repo)
    sha_after = hashlib.sha256((repo / "tests/test_thing.py").read_bytes()).hexdigest()
    assert sha_before == sha_after
    assert candidate["returncode"] == 1 and "1 failed, 1 passed" in candidate["stdout"]
    refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
    spec = dataclasses.replace(probe.old._pa_spec(qualified=False), parse_log=probe.old.parser_for(*refs))
    grade = await probe.grade_case("r4_fixed_tests", repo, probe.old._pa_log(candidate["stdout"], test_rc=1),
        probe.old.patch("src/id_source.py", 'label = "before"', 'label = "after"'), spec=spec)
    assert grade["source_fields"]["reward"] == 0.0
    assert grade["report"]["reward"] == 0.0
    assert grade["shape"] is None and grade["decision"]["kind"] == "source_rule"
    out = {"method": "真实pytest；测试字节不变、只改候选label；真实manager、容器替身；无资格", "test_source": test_source,
           "test_sha256_before": sha_before, "test_sha256_after": sha_after,
           "baseline": baseline, "candidate": candidate, "grade": grade}
    (probe.HERE / "supplemental_r4_fixed_tests.json").write_text(probe.redact(json.dumps(out, ensure_ascii=False, indent=2)) + "\n")
    print(json.dumps({"same_test_bytes": sha_before == sha_after, "baseline_rc": baseline["returncode"],
                      "candidate_rc": candidate["returncode"], "source_reward": grade["source_fields"]["reward"],
                      "actual_reward": grade["report"]["reward"], "decision": grade["decision"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
