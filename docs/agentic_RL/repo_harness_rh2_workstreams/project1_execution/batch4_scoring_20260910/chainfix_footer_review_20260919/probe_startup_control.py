"""有成功子 pytest 输出的真实 conftest 启动失败；仍属外层完成判据的对照。"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "matrix"))
import probe_pytest_shapes as probe
from repoharness2.grading.manager import outer_session_summary

async def main():
    probe.HERE = HERE / "startup_control"
    probe.HERE.mkdir()
    repo = probe.HERE / "case"
    probe.old.write(repo, "child/test_child.py", "def test_child():\n    assert True\n")
    probe.old.write(repo, "src/thing.py", "VALUE = 1\n")
    probe.old.write(repo, "tests/conftest.py", '''import subprocess, sys
subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-rA", "child/test_child.py"], check=True)
from src.thing import VALUE
''')
    probe.old.write(repo, "tests/test_thing.py", "def test_feature():\n    assert True\ndef test_stable():\n    assert True\n")
    before = probe.run_pytest(repo, "baseline", [])
    assert before["rc"] == 0
    probe.old.write(repo, "src/thing.py", "from rh2_missing_fixture_dependency import VALUE\n")
    after = probe.run_pytest(repo, "candidate", [])
    assert after["rc"] == 4
    patch = probe.old.patch("src/thing.py", "VALUE = 1", "from rh2_missing_fixture_dependency import VALUE")
    grade = await probe.grade("startup_child_pass", repo, after, patch, qualified=False)
    result = {"baseline": before, "candidate": after, "grade": grade, "expected_reward": None,
              "selected_summary": outer_session_summary(after["stdout"])}
    (probe.HERE / "result.json").write_text(probe.redact(json.dumps(result, ensure_ascii=False, indent=2)) + "\n")
    print(json.dumps({"rc": after["rc"], "summary": result["selected_summary"], "reward": grade["report"]["reward"],
                      "decision": grade["decision"], "log": after["stdout"]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
