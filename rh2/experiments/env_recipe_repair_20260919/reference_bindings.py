"""版本化题目参考绑定：保持原参考分组，恢复完整pytest nodeid与一对多碰撞。

只读取宿主冻结的显式绑定，不对候选输出做猜测式unescape。多个node合并为同一
来源参考时要求全部成功；任一个缺席仍缺席。测试进程输出的既有可伪造性未解决。
"""

import re

VERSION = "reference-bindings-v1"
STATUSES = ("ERROR", "FAILED", "SKIPPED", "XFAIL", "PASSED")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def bound_states(segment, bindings):
    nodes = {node: [] for group in bindings.values() for node in group}
    for raw in segment.splitlines():
        line = ANSI.sub("", raw).strip()
        for node, states in nodes.items():
            for status in STATUSES:
                # -rA摘要与pydantic旧版verbose形态，边界精确到完整nodeid。
                prefix = status + " " + node
                if line == prefix or line.startswith(prefix + " - "):
                    states.append(status)
                if re.fullmatch(re.escape(node) + r"\s+" + status + r"(?:\s+\[\s*\d+%\])?", line):
                    states.append(status)
    result = {}
    for alias, group in bindings.items():
        if any(not nodes[node] for node in group):
            continue
        observed = {status for node in group for status in nodes[node]}
        result[alias] = next(status for status in STATUSES if status in observed)
    return result, nodes


def parse_bound(grading, log_text, bindings, audit=None):
    from repoharness2.envpack.scoring import parse_eval_log_v2
    from repoharness2.envpack.swegym_parsers import lookup_parser
    from swebench.harness.constants import END_TEST_OUTPUT, FAIL_TO_PASS, PASS_TO_PASS, START_TEST_OUTPUT
    from swebench.harness.grading import (
        compute_fail_to_pass,
        compute_pass_to_pass,
        get_eval_tests_report,
        get_resolution_status,
    )

    original = parse_eval_log_v2(grading, log_text)
    if not original.apply_ok:
        return original.model_copy(update={"parser_source": original.parser_source + "+" + VERSION})
    segment = log_text.split(START_TEST_OUTPUT, 1)[1].split(END_TEST_OUTPUT, 1)[0]
    states = lookup_parser(grading.repo_key_lower)(segment)
    corrected, nodes = bound_states(segment, bindings)
    for alias in bindings:
        states.pop(alias, None)  # 完整成员缺席时，不能沿用旧parser的碰撞末值。
    states.update(corrected)
    f2p, p2p = list(grading.fail_to_pass), list(grading.pass_to_pass)
    assert set(bindings) <= set(f2p + p2p)
    report = get_eval_tests_report(states, {FAIL_TO_PASS: f2p, PASS_TO_PASS: p2p})
    resolution = get_resolution_status(report)
    result = original.model_copy(update={
        "resolution": resolution, "resolved": resolution == "RESOLVED_FULL",
        "f2p_rate": compute_fail_to_pass(report), "p2p_rate": compute_pass_to_pass(report),
        "f2p_success": report[FAIL_TO_PASS]["success"], "f2p_failure": report[FAIL_TO_PASS]["failure"],
        "p2p_success": report[PASS_TO_PASS]["success"], "p2p_failure": report[PASS_TO_PASS]["failure"],
        "num_parsed_tests": len(states),
        "reference_missing": [x for x in f2p + p2p if x not in states],
        "reference_skipped": [x for x in f2p + p2p if states.get(x) == "SKIPPED"],
        "parser_source": original.parser_source + "+" + VERSION,
    })
    if audit:
        audit({"version": VERSION, "original": original.model_dump(mode="json"),
               "revised": result.model_dump(mode="json"), "bindings": bindings, "raw_node_states": nodes})
    return result
