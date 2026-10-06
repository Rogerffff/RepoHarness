"""设计验证：最终 pytest 摘要的正常完成证据，避免继续猜 captured 中任意分节头。

仅本进程替换 classifier 入口作对照，恢复后退出；不修改生产源码或维护测试。
此探针验证一个局部修法方向，不表示该修法已经实施或穷尽日志形态。
"""
from __future__ import annotations

import asyncio
import json
import re

import probe_pytest_shapes as probe
import repoharness2.grading.manager as manager_module


def completion_evidence(segment):
    lines = segment.splitlines()
    summaries = [i for i, line in enumerate(lines) if re.fullmatch(r"=+ short test summary info =+", line.strip())]
    if not summaries:
        return {"normal_completion": False, "reason": "no_final_pytest_summary"}
    tail = [line.strip() for line in lines[summaries[-1] + 1:] if line.strip()]
    if not tail:
        return {"normal_completion": False, "reason": "empty_final_summary"}
    footer = tail[-1].strip("= ")
    has_totals = bool(re.fullmatch(r"[0-9]+ (?:failed|passed|skipped|xfailed|xpassed|error|errors|warning|warnings|deselected)(?:, [0-9]+ (?:failed|passed|skipped|xfailed|xpassed|error|errors|warning|warnings|deselected))* in [0-9.]+s(?: \([^)]*\))?", footer))
    statuses = [line for line in tail[:-1] if re.match(r"^(?:PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) \S+::\S+", line)]
    collection_error_rows = [line for line in tail[:-1] if line.startswith("ERROR ") and "::" not in line.split(" - ", 1)[0]]
    interruption = any("Interrupted:" in line or "during collection" in line for line in tail)
    return {"normal_completion": has_totals and bool(statuses) and not collection_error_rows and not interruption,
            "footer": footer, "test_status_rows": statuses, "collection_error_rows": collection_error_rows,
            "interruption": interruption}


async def main():
    original = manager_module.classify_execution_failure_shape
    source_before = probe.digest_sources()
    inputs = json.loads((probe.HERE / "probe_pytest_shapes.json").read_text())
    result = {"status": "设计对照；未修改生产实现", "cases": {}}

    def classify_with_completion(log_text, test_rc, *, zero_parsed=True):
        segment = manager_module._candidate_test_segment(log_text)
        if not zero_parsed and segment is not None:
            # 标记行来自 `set -x`，只保留真正 pytest 文本来检查末尾摘要。
            segment = segment.rstrip().removesuffix("+ : '").rstrip()
            if completion_evidence(segment)["normal_completion"]:
                return None
        return original(log_text, test_rc, zero_parsed=zero_parsed)

    try:
        manager_module.classify_execution_failure_shape = classify_with_completion
        for name, item in inputs["cases"].items():
            repo = probe.HERE / "cases" / name
            refs = None
            qualified = True
            if name.startswith("syntax_"):
                patch = probe.old.patch("src/thing.py", "VALUE = 1", "def feature(:")
                before = item["grade"]
            elif name.startswith("ordinary_"):
                patch = probe.old.patch("src/unused.py", "marker = 1", "marker = 2")
                before = item["clean_same_log"]
            else:
                patch = probe.old.patch("src/id_source.py", 'label = "before"', 'label = "after"')
                refs = (["tests/test_thing.py::test_feature[before]"], ["tests/test_thing.py::test_stable[before]"])
                qualified = False
                before = item["grade"]
            after = await probe.grade("completion_" + name, repo, item["candidate"], patch, refs=refs, qualified=qualified)
            entry = {"completion_evidence": completion_evidence(item["candidate"]["stdout"]),
                     "current_reward": before["report"]["reward"], "hypothesis_reward": after["report"]["reward"],
                     "hypothesis_category": after["report"]["failure_category"], "hypothesis_decision": after["decision"]}
            if name.startswith("captured_pytest_"):
                assert entry["hypothesis_category"] == "tests_failed" and entry["hypothesis_reward"] == 0.0
            else:
                assert before["report"]["failure_category"] == entry["hypothesis_category"]
                assert entry["current_reward"] == entry["hypothesis_reward"]
            result["cases"][name] = entry
    finally:
        manager_module.classify_execution_failure_shape = original
    assert source_before == probe.digest_sources()
    result["source_sha256"] = source_before
    (probe.HERE / "completion_evidence.json").write_text(probe.redact(json.dumps(result, ensure_ascii=False, indent=2)) + "\n")
    print(json.dumps({"replayed_cases": len(result["cases"]), "nested_pytest_0_restored": 5,
                      "other_case_outcomes_unchanged": 20, "production_source_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
