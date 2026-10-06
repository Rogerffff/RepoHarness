"""局部设计对照，未实施：兼容裸收尾行 + 已知非正常退出码不得提供正常完成证据。

只在探针进程临时替换 helper，恢复后退出；不据退出码直接归因候选失败。
这只验证已复现接缝的可修性，不主张解决所有复合命令/结果可信性问题。
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "matrix"))
import probe_pytest_shapes as probe
import repoharness2.grading.manager as module

async def main():
    source = probe.digest_sources()
    probe.HERE = HERE / "hypothesis"
    probe.HERE.mkdir()
    original_footer = module._PYTEST_FOOTER
    original_classifier = module.classify_execution_failure_shape
    original_probe_classifier = probe.classify_execution_failure_shape
    original_normal = module.outer_session_completed_normally
    # 只放宽边框，不改变既有计数与 no-tests 判据。
    module._PYTEST_FOOTER = re.compile(r"^(?:=+ )?(?P<body>[^=\n]*?) in [0-9.]+s(?: \([0-9:]+\))?(?: =+)?\s*$", re.M)
    def with_completion_consistency(log, test_rc, *, zero_parsed=True):
        # 已知 2/3/4/5/信号退出与 pytest 正常执行测试不一致。
        # 禁用正向短路，让已有形状与三路判定照常工作；不把非零 rc 判成候选 0 分。
        if test_rc is not None and test_rc not in (0, 1):
            module.outer_session_completed_normally = lambda _segment: False
        try:
            return original_classifier(log, test_rc, zero_parsed=zero_parsed)
        finally:
            module.outer_session_completed_normally = original_normal
    module.classify_execution_failure_shape = with_completion_consistency
    probe.classify_execution_failure_shape = with_completion_consistency
    rows = {}
    async def one(name, repo, run, patch, *, refs=None, qualified=True, expected=None):
        g = await probe.grade(name, repo, run, patch, refs=refs, qualified=qualified)
        rows[name] = {"expected_reward": expected, "actual_reward": g["report"]["reward"],
                      "category": g["report"]["failure_category"], "decision": g["decision"]["kind"]}
        assert g["report"]["reward"] == expected, (name, rows[name])
    try:
        data = json.loads((HERE / "matrix/probe_pytest_shapes.json").read_text())
        for name,c in data["cases"].items():
            repo = HERE / "matrix/cases" / name
            if name.startswith("syntax_"):
                await one(name, repo, c["candidate"], probe.old.patch("src/thing.py", "VALUE = 1", "def feature(:"), expected=0.0)
            elif name.startswith("ordinary_"):
                await one(name, repo, c["candidate"], probe.old.patch("src/unused.py", "marker = 1", "marker = 2"))
            else:
                refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
                await one(name, repo, c["candidate"], probe.old.patch("src/id_source.py", 'label = "before"', 'label = "after"'), refs=refs, qualified=False, expected=0.0)
        more = json.loads((HERE / "footer_review_result.json").read_text())
        for name,c in more["cases"].items():
            if not name.startswith("outer_collection"): continue
            await one(name, HERE / "extra/cases" / name, c["run"], probe.old.patch("src/thing.py", "VALUE = 1", "from rh2_missing_fixture_dependency import VALUE"), qualified=False)
        c = json.loads((HERE / "startup_control/result.json").read_text())
        await one("startup_child_pass", HERE / "startup_control/case", c["candidate"], probe.old.patch("src/thing.py", "VALUE = 1", "from rh2_missing_fixture_dependency import VALUE"), qualified=False)
    finally:
        module._PYTEST_FOOTER = original_footer
        module.outer_session_completed_normally = original_normal
        module.classify_execution_failure_shape = original_classifier
        probe.classify_execution_failure_shape = original_probe_classifier
    assert source == probe.digest_sources()
    (HERE / "hypothesis_result.json").write_text(json.dumps({"status":"设计对照，未修改生产实现", "cases":rows,"source_sha256":source},ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"cases":len(rows),"all_expected":True,"production_unchanged":True},ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
