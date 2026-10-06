"""8801 私有诊断协议：采集可见异常；宿主校验封包，不替代语义裁决。"""
import base64
import builtins
import hashlib
import json
import os
import re
import sys


DIAGNOSTIC_PREFIX = "RH2_DASK8801_DIAGNOSTIC_V1:"
IMPORT_PREFIX = "RH2_DASK8801_IMPORT_EXCEPTION_V1:"
COMPAT_PREFIX = "RH2_DASK8801_FALSY_COMPAT_V1:"
FALSY_FIXTURES = {"falsy_list": b"[]", "falsy_str": b'""', "falsy_int": b"0",
                  "falsy_float": b"0.0", "falsy_bool": b"false"}
FIXTURES = {
    "syntax_brace": b"{",
    "syntax_tab": b"a: 1\n\tb: 2\n",
    "nonmapping_list": b"[1234]",
    "nonmapping_str": b"hello",
    "nonmapping_int": b"1234",
    "nonmapping_float": b"1.5",
}


def visible_exception(exc):
    """仅取 Python 显示的消息、notes、chain、内建异常组；无帧/源码/locals。"""
    issues = []
    seen = set()

    def visit(err, depth):
        if depth > 32 or id(err) in seen:
            issues.append("chain_cycle_or_depth_limit")
            return None
        seen.add(id(err))
        try:
            message = str(err)
            notes = getattr(err, "__notes__", []) if sys.version_info >= (3, 11) else []
            if not isinstance(notes, (list, tuple)) or not all(isinstance(n, str) for n in notes):
                raise ValueError("non_string_notes")
            if len(message) + sum(len(n) for n in notes) > 65536:
                raise ValueError("message_limit")
            exception_type = type(err)
            displayed_type = exception_type.__qualname__
            if exception_type.__module__ not in ("builtins", "__main__"):
                displayed_type = exception_type.__module__ + "." + displayed_type
            node = {"displayed_type": displayed_type, "message": message, "visible_notes": list(notes)}
            cause = err.__cause__
            context = err.__context__
            if cause is not None:
                node["visible_predecessor"] = {"relation": "explicit_cause", "exception": visit(cause, depth + 1)}
            elif context is not None and not err.__suppress_context__:
                node["visible_predecessor"] = {"relation": "displayed_context", "exception": visit(context, depth + 1)}
            group_type = getattr(builtins, "BaseExceptionGroup", ())
            if isinstance(err, group_type):
                node["visible_group_members"] = [visit(child, depth + 1) for child in err.exceptions]
            return node
        except Exception as capture_error:
            issues.append("exception_capture_error:" + type(capture_error).__name__)
            return None
        finally:
            seen.remove(id(err))

    diagnostic = visit(exc, 0)
    return {"visible_exception": diagnostic, "capture_issues": issues}


def encode_marker(prefix, value):
    data = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(data) > 1048576:
        raise ValueError("diagnostic_packet_too_large")
    return prefix + base64.b64encode(data).decode("ascii")


def decode_markers(text, prefix):
    """只收独立物理行；重复/损坏不默默忽略。调用方核期望集合与运行身份。"""
    values, issues = [], []
    for line in text.splitlines():
        if prefix not in line:
            continue
        if not line.startswith(prefix):
            # pytest 源码展示中的字符串不是封包；只接受整行协议。
            continue
        try:
            token = line[len(prefix):]
            if len(token) > 1400000:
                raise ValueError("packet_limit")
            value = json.loads(base64.b64decode(token, validate=True).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError("packet_not_object")
            values.append(value)
        except (ValueError, UnicodeError, RecursionError) as exc:
            issues.append("invalid_marker:" + type(exc).__name__)
    return values, issues


def file_fact(path):
    try:
        with open(path, "rb") as stream:
            data = stream.read()
        return {"exists": os.path.isfile(path), "readable": True, "content_sha256": hashlib.sha256(data).hexdigest()}
    except OSError as exc:
        return {"exists": os.path.exists(path), "readable": False, "read_error": type(exc).__name__}


def alias_diagnostic(value, aliases):
    if isinstance(value, str):
        # 一次扫描：插入的身份标记不再扫描；原生占位词不能冒充真实文件。
        pieces = []
        for path, alias in sorted(aliases.items(), key=lambda item: -len(item[0])):
            pieces.append(r"(?<![\w./-])" + re.escape(path) + r"(?![\w.-])")
        literal_tokens = ("BAD_FILE", "GOOD_FILE", "FIXTURE_DIR")
        pieces.extend(re.escape(token) for token in literal_tokens)
        pattern = re.compile("|".join(pieces))

        def replace(match):
            text = match.group(0)
            if text in aliases:
                return aliases[text]
            return "UNMATCHED_LITERAL_TOKEN[" + text.encode("utf-8").hex() + "]"

        return pattern.sub(replace, value)
    if isinstance(value, dict):
        return {key: alias_diagnostic(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [alias_diagnostic(item, aliases) for item in value]
    return value


def emit_diagnostic(fixture, entry, bad_path, good_path, before, diagnostic):
    aliases = {bad_path: "BAD_FILE", good_path: "GOOD_FILE", os.path.dirname(bad_path): "FIXTURE_DIR",
               os.path.basename(bad_path): "BAD_FILE", os.path.basename(good_path): "GOOD_FILE"}
    packet = {
        "schema": "dask8801_diagnostic_packet.v1", "case_id": fixture + ":" + entry,
        "before": before, "after": file_fact(bad_path),
        "diagnostic": {"visible_exception": None, "capture_issues": ["capture_pending"]},
    }
    try:
        packet["diagnostic"] = alias_diagnostic(diagnostic, aliases)
        encoded = encode_marker(DIAGNOSTIC_PREFIX, packet)
    except Exception as capture_error:
        # 限额/编码等采集失败不是求解行为失败，不让采集器使 pytest 失败。
        packet["diagnostic"] = {"visible_exception": None,
                                "capture_issues": ["diagnostic_encoding_error:" + type(capture_error).__name__]}
        encoded = encode_marker(DIAGNOSTIC_PREFIX, packet)
    print(encoded)


def trusted_facts(fixture, entry):
    """宿主的冻结事实，不从候选的消息或封包中采纳解析结论。"""
    content = {**FIXTURES, **FALSY_FIXTURES}[fixture]
    parses = {
        "syntax_brace": {"succeeded": False, "problem": "unfinished YAML flow structure at end of input"},
        "syntax_tab": {"succeeded": False, "problem": "a tab cannot start a YAML token at line 2"},
        "nonmapping_list": {"succeeded": True, "value_type": "list", "value": [1234]},
        "nonmapping_str": {"succeeded": True, "value_type": "str", "value": "hello"},
        "nonmapping_int": {"succeeded": True, "value_type": "int", "value": 1234},
        "nonmapping_float": {"succeeded": True, "value_type": "float", "value": 1.5},
        "falsy_list": {"succeeded": True, "value_type": "list", "value": []},
        "falsy_str": {"succeeded": True, "value_type": "str", "value": ""},
        "falsy_int": {"succeeded": True, "value_type": "int", "value": 0},
        "falsy_float": {"succeeded": True, "value_type": "float", "value": 0.0},
        "falsy_bool": {"succeeded": True, "value_type": "bool", "value": False},
    }
    parse = parses[fixture]
    return {"entry": entry, "bad_file_alias": "BAD_FILE", "file_exists": True, "file_readable": True,
            "content_sha256": hashlib.sha256(content).hexdigest(), "independent_yaml_parse": parse,
            "expected_configuration": "named_key_value_mapping_or_empty_none",
            "good_file_alias": "GOOD_FILE", "good_file_valid_mapping": True,
            "unreadable_directory_alias": "FIXTURE_DIR/0.yaml", "unreadable_entries_are_skipped": True}


def expected_cases(scope):
    cases = {fixture + ":" + entry for fixture in FIXTURES for entry in ("directory", "file")}
    if scope == "full_import":
        cases.add("nonmapping_str:import")
    elif scope != "isolated_api":
        raise ValueError("unknown_scope")
    return cases


def validate_packets(text, scope):
    def valid_file_fact(value, expected):
        return (isinstance(value, dict) and set(value) == set(expected)
                and value.get("exists") is True and value.get("readable") is True
                and isinstance(value.get("content_sha256"), str)
                and value["content_sha256"] == expected["content_sha256"])

    packets, issues = decode_markers(text, DIAGNOSTIC_PREFIX)
    compat, compat_issues = decode_markers(text, COMPAT_PREFIX)
    issues.extend(compat_issues)
    optional = {fixture + ":" + entry for fixture in FALSY_FIXTURES for entry in ("directory", "file")}
    branches, rejected = {}, set()
    for item in compat:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or case_id not in optional or case_id in branches:
            issues.append("invalid_or_duplicate_compat_case")
            continue
        branches[case_id] = item.get("branch")
        fixture, entry = case_id.split(":")
        expected_file = {"exists": True, "readable": True, "content_sha256": trusted_facts(fixture, entry)["content_sha256"]}
        if (set(item) != {"schema", "case_id", "branch", "before", "after"}
                or item.get("schema") != "dask8801_falsy_branch.v1"
                or item.get("branch") not in ("empty_configuration", "diagnostic_failure")
                or not valid_file_fact(item.get("before"), expected_file)
                or not valid_file_fact(item.get("after"), expected_file)):
            issues.append("invalid_compat_branch_or_fixture:" + case_id)
        if item.get("branch") == "diagnostic_failure":
            rejected.add(case_id)
    issues.extend("missing_compat_case:" + name for name in sorted(optional - set(branches)))
    required = expected_cases(scope) | rejected
    found, inputs = set(), []
    for packet in packets:
        case_id = packet.get("case_id")
        if not isinstance(case_id, str) or case_id not in required:
            issues.append("unexpected_case")
            continue
        if case_id in found:
            issues.append("duplicate_case:" + case_id)
            continue
        found.add(case_id)
        fixture, entry = case_id.split(":")
        facts = trusted_facts(fixture, entry)
        expected_file = {"exists": True, "readable": True, "content_sha256": facts["content_sha256"]}
        if (set(packet) != {"schema", "case_id", "before", "after", "diagnostic"}
                or packet.get("schema") != "dask8801_diagnostic_packet.v1"
                or not valid_file_fact(packet.get("before"), expected_file)
                or not valid_file_fact(packet.get("after"), expected_file)):
            issues.append("fixture_identity_or_integrity:" + case_id)
            continue
        diagnostic = packet.get("diagnostic")
        if (not isinstance(diagnostic, dict) or not isinstance(diagnostic.get("capture_issues"), list)
                or diagnostic["capture_issues"] != [] or not isinstance(diagnostic.get("visible_exception"), dict)):
            issues.append("incomplete_diagnostic:" + case_id)
            continue
        # 仅采集器定义的可见文本/关系结构可进入判定器，拒绝源码等附加字段。
        def check_node(node, depth=0):
            if depth > 32 or not isinstance(node, dict) or set(node) - {"displayed_type", "message", "visible_notes", "visible_predecessor", "visible_group_members"}:
                return False
            if not isinstance(node.get("displayed_type"), str) or not node["displayed_type"] or not isinstance(node.get("message"), str) or not isinstance(node.get("visible_notes"), list) or not all(isinstance(n, str) for n in node["visible_notes"]):
                return False
            predecessor = node.get("visible_predecessor")
            if predecessor is not None and (not isinstance(predecessor, dict) or set(predecessor) != {"relation", "exception"} or not isinstance(predecessor["relation"], str) or predecessor["relation"] not in {"explicit_cause", "displayed_context"} or not check_node(predecessor["exception"], depth + 1)):
                return False
            children = node.get("visible_group_members", [])
            return isinstance(children, list) and all(check_node(n, depth + 1) for n in children)
        if set(diagnostic) != {"visible_exception", "capture_issues"} or not check_node(diagnostic["visible_exception"]):
            issues.append("invalid_diagnostic_shape:" + case_id)
            continue
        inputs.append({"case_id": case_id, "semantic_judge_input": {"trusted_facts": facts, "visible_diagnostic": diagnostic["visible_exception"]}})
    missing = required - found
    issues.extend("missing_case:" + name for name in sorted(missing))
    return {"state": "needs_evidence" if issues else "complete", "issues": issues,
            "compatibility_branches": branches, "inputs": sorted(inputs, key=lambda item: item["case_id"])}


def combine_diagnostic_outcome(*, behavior_complete, raw_behavior_score, packets_complete, verdicts, judge_error=None):
    """诊断侧结论；不产生训练 reward。未完成执行不冒作求解失败。"""
    if not behavior_complete or raw_behavior_score not in (0, 1):
        return "needs_evidence"
    if raw_behavior_score == 0:
        return "fail_behavior"
    if not packets_complete:
        return "needs_evidence"
    if judge_error or not verdicts or any(v not in ("pass", "fail", "uncertain") for v in verdicts):
        return "needs_review"
    if "fail" in verdicts:
        return "fail_diagnostic_semantics"
    if "uncertain" in verdicts:
        return "needs_review"
    return "pass_diagnostic_goal"
