"""8801 v7 的本机采集/控制检查；隔离 API，不冒作原镜像或正式评分。"""
import ast
import argparse
import base64
import contextlib
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import types
from pathlib import Path

import pytest
import yaml

import config_diagnostic_protocol as protocol
from check_config_acceptance import definitions
from prepare_materials import HERE, ROOT, apply_to_file, rel, save_json, sha


def test_env(loader, test_text):
    tree = ast.parse(test_text)
    names = {"_collect_yaml_error", "test_collect_yaml_malformed_file", "test_collect_yaml_no_top_level_dict", "test_collect_yaml_permission_errors", "no_read_permissions"}
    helpers = {"visible_exception", "encode_marker", "decode_markers", "file_fact", "alias_diagnostic", "emit_diagnostic"}
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
            if not module.startswith("dask"):
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in names | helpers:
            if node.name == "test_collect_yaml_no_top_level_dict":
                stop = next(i for i, statement in enumerate(node.body) if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "env" for t in statement.targets))
                node.body = node.body[:stop]
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"DIAGNOSTIC_PREFIX", "IMPORT_PREFIX", "IMPORT_CAPTURE_PROGRAM"} for t in node.targets):
            selected.append(node)
    tree.body = selected
    env = {"collect_yaml": loader["collect_yaml"], "merge": loader["merge"]}
    exec(compile(tree, "v7_isolated_trusted_test.py", "exec"), env)
    return env


def protocol_checks(import_program):
    checks = {}
    nesting = b'{"nested":' + b"[" * 3000 + b"0" + b"]" * 3000 + b"}"
    text = protocol.DIAGNOSTIC_PREFIX + base64.b64encode(nesting).decode() + "\n"
    assert protocol.validate_packets(text, "isolated_api")["state"] == "needs_evidence"
    checks["deep_json_is_missing_evidence_not_uncaught_recursion"] = True
    try:
        try:
            raise ValueError("hidden correct explanation")
        except ValueError:
            raise RuntimeError("BAD_FILE: missing") from None
    except RuntimeError as err:
        captured = protocol.visible_exception(err)
        assert "hidden correct" not in json.dumps(captured)
        assert "traceback" not in json.dumps(captured) and "locals" not in json.dumps(captured)
        checks["hidden_context_excluded"] = True
    cause = ValueError("BAD_FILE: needs labelled values")
    outer = RuntimeError("loading failed")
    outer.__cause__ = cause
    captured = protocol.visible_exception(outer)
    assert captured["visible_exception"]["visible_predecessor"]["exception"]["message"] == str(cause)
    checks["visible_cause_preserved"] = True
    note = ValueError("message")
    note.__notes__ = ["visible on Python 3.11+"]
    actual_sys = protocol.sys
    try:
        protocol.sys = types.SimpleNamespace(version_info=(3, 9))
        assert protocol.visible_exception(note)["visible_exception"]["visible_notes"] == []
    finally:
        protocol.sys = actual_sys
    checks["python39_notes_not_displayed_excluded"] = True
    class ConfigurationRequiresNamedValuesError(Exception):
        pass
    class FileDoesNotExistError(Exception):
        pass
    correct = protocol.visible_exception(ConfigurationRequiresNamedValuesError("/synthetic/fixture/a.yaml"))
    wrong = protocol.visible_exception(FileDoesNotExistError("/synthetic/fixture/a.yaml"))
    assert correct["visible_exception"]["message"] == wrong["visible_exception"]["message"]
    assert correct["visible_exception"]["displayed_type"] != wrong["visible_exception"]["displayed_type"]
    checks["displayed_descriptive_exception_type_preserved_not_merged"] = True
    aliases = {"/synthetic/fixture/a.yaml": "BAD_FILE", "/synthetic/fixture/b.yaml": "GOOD_FILE",
               "/synthetic/fixture": "FIXTURE_DIR", "a.yaml": "BAD_FILE", "b.yaml": "GOOD_FILE"}
    assert protocol.alias_diagnostic("/synthetic/fixture/a.yaml: detail", aliases) == "BAD_FILE: detail"
    assert protocol.alias_diagnostic("a.yaml: detail", aliases) == "BAD_FILE: detail"
    assert "BAD_FILE" not in protocol.alias_diagnostic("BAD_FILE: detail", aliases)
    assert "BAD_FILE" not in protocol.alias_diagnostic("mega.yaml: detail", aliases)
    assert "BAD_FILE" not in protocol.alias_diagnostic("/wrong/place/a.yaml: detail", aliases)
    checks["native_placeholder_and_other_path_cannot_impersonate_bad_file"] = True
    if sys.version_info >= (3, 11):
        repeated = ValueError("same visible exception")
        group = ExceptionGroup("both", [repeated, repeated])
        value = protocol.visible_exception(group)
        assert not value["capture_issues"] and len(value["visible_exception"]["visible_group_members"]) == 2
        checks["repeated_group_member_preserved_python311_extension"] = True
    with tempfile.TemporaryDirectory(prefix="rh2-long-diagnostic-") as scratch:
        bad_path = str(Path(scratch) / "a.yaml")
        good_path = str(Path(scratch) / "b.yaml")
        Path(bad_path).write_bytes(b"hello")
        long_exception = ValueError("x" * 64000)
        for _ in range(17):
            outer = ValueError("y" * 64000)
            outer.__cause__ = long_exception
            long_exception = outer
        diagnostic = protocol.visible_exception(long_exception)
        assert not diagnostic["capture_issues"]
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            protocol.emit_diagnostic("nonmapping_str", "file", bad_path, good_path, protocol.file_fact(bad_path), diagnostic)
        values, issues = protocol.decode_markers(stream.getvalue(), protocol.DIAGNOSTIC_PREFIX)
        assert not issues and len(values) == 1 and values[0]["diagnostic"]["capture_issues"]
        assert protocol.validate_packets(stream.getvalue(), "isolated_api")["state"] == "needs_evidence"
        checks["oversized_capture_is_missing_evidence_not_behavior_failure"] = True
    with tempfile.TemporaryDirectory(prefix="rh2-diagnostic-protocol-") as scratch:
        td = Path(scratch)
        fake = td / "dask.py"
        fake.write_text("try:\n raise ValueError('BAD_FILE: expected named settings')\nexcept ValueError as cause:\n raise RuntimeError('loading failed') from cause\n")
        result = subprocess.run([sys.executable, "-c", import_program], cwd=td, env={**os.environ, "PYTHONPATH": str(td)}, capture_output=True, text=True, timeout=20)
        values, issues = protocol.decode_markers(result.stderr, protocol.IMPORT_PREFIX)
        assert result.returncode != 0 and len(values) == 1 and not issues
        assert values[0]["visible_exception"]["visible_predecessor"]["exception"]["message"].startswith("BAD_FILE:")
        checks["import_hook_synthetic_nonzero_and_chain_capture"] = True
        fake.write_text("VALUE = 1\n")
        result = subprocess.run([sys.executable, "-c", import_program], cwd=td, env={**os.environ, "PYTHONPATH": str(td)}, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and protocol.decode_markers(result.stderr, protocol.IMPORT_PREFIX) == ([], [])
        checks["successful_import_cannot_supply_failure_packet"] = True
        # 不假定 -rA 会保留 PASSED stdout；实际检查当前本机 pytest 命令。
        (td / "test_stdout.py").write_text("def test_capture():\n print('RH2_CAPTURE_AVAILABILITY_CHECK')\n")
        result = subprocess.run([sys.executable, "-m", "pytest", "-rA", "--color=no", "test_stdout.py"], cwd=td, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0 and result.stdout.splitlines().count("RH2_CAPTURE_AVAILABILITY_CHECK") == 1
        checks["pytest_rA_passed_stdout_preserved_local_only"] = True
    for expected, arguments in [
        ("needs_evidence", dict(behavior_complete=False, raw_behavior_score=0, packets_complete=False, verdicts=[])),
        ("fail_behavior", dict(behavior_complete=True, raw_behavior_score=0, packets_complete=False, verdicts=[])),
        ("needs_evidence", dict(behavior_complete=True, raw_behavior_score=1, packets_complete=False, verdicts=["pass"])),
        ("needs_review", dict(behavior_complete=True, raw_behavior_score=1, packets_complete=True, verdicts=["uncertain"])),
        ("needs_review", dict(behavior_complete=True, raw_behavior_score=1, packets_complete=True, verdicts=["pass"], judge_error="unavailable")),
        ("fail_diagnostic_semantics", dict(behavior_complete=True, raw_behavior_score=1, packets_complete=True, verdicts=["fail"])),
        ("pass_diagnostic_goal", dict(behavior_complete=True, raw_behavior_score=1, packets_complete=True, verdicts=["pass"])),
    ]:
        assert protocol.combine_diagnostic_outcome(**arguments) == expected
    checks["missing_uncertain_unavailable_and_separate_behavior_semantics"] = True
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-name", default="local_behavior_capture_v7_20261003.json")
    arguments = parser.parse_args()
    assert Path(arguments.output_name).name == arguments.output_name and arguments.output_name.endswith(".json")
    assert os.geteuid() != 0
    out = HERE / "tasks/dask__dask-8801"
    matrix = json.loads((out / "acceptance_matrix.json").read_text())
    revision = json.loads((out / "revision.json").read_text())
    base = (ROOT / "runs/swegym_quality_batch01_20260921/public/dask__dask-8801/base/dask/config.py").read_bytes()
    text = (out / "effective_test.py").read_text()
    empty_tests = test_env(definitions(base.decode(), "config_isolated.py"), text)
    checks = protocol_checks(empty_tests["IMPORT_CAPTURE_PROGRAM"])
    rows = []
    for planned in matrix["rows"]:
        candidate = planned["name"]
        patch = planned["patch"]
        patch_bytes = None if patch is None else (ROOT / patch["path"]).read_bytes()
        if patch is not None:
            assert sha(patch_bytes) == patch["sha256"]
        code = base if patch is None else apply_to_file(base, "dask/config.py", patch_bytes)
        funcs = test_env(definitions(code.decode(), "config_isolated.py"), text)
        stream, states = io.StringIO(), {}
        for label, fn, args in [
            ("malformed", "test_collect_yaml_malformed_file", []),
            ("nonmapping_empty_null", "test_collect_yaml_no_top_level_dict", []),
            ("permission_directory", "test_collect_yaml_permission_errors", ["directory"]),
            ("permission_file", "test_collect_yaml_permission_errors", ["file"]),
        ]:
            with tempfile.TemporaryDirectory(prefix="rh2-dask8801-v7-") as scratch:
                try:
                    with contextlib.redirect_stdout(stream):
                        funcs[fn](Path(scratch), *args)
                    states[label] = {"status": "pass"}
                except (Exception, pytest.fail.Exception) as exc:
                    states[label] = {"status": "fail", "exception": type(exc).__name__, "detail": str(exc).replace(scratch, "FIXTURE_DIR")}
        validated = protocol.validate_packets(stream.getvalue(), "isolated_api")
        if candidate == "gold":
            assert validated["state"] == "complete" and len(validated["inputs"]) == 12
            assert protocol.validate_packets(stream.getvalue() + stream.getvalue(), "isolated_api")["state"] == "needs_evidence"
            assert protocol.validate_packets(stream.getvalue().splitlines()[0], "isolated_api")["state"] == "needs_evidence"
            assert protocol.validate_packets(stream.getvalue() + protocol.DIAGNOSTIC_PREFIX + "corrupt\n", "isolated_api")["state"] == "needs_evidence"
            checks["duplicate_missing_corrupt_packets_not_pass"] = True
        rows.append({"candidate": candidate, "patch": patch, "production_code_sha256": sha(code), "isolated_behavior_checks": states,
                     "isolated_behavior_pass": all(v["status"] == "pass" for v in states.values()), "diagnostic_capture": validated,
                     "full_import": "not_run", "formal_raw_behavior_score": None, "semantic_verdict": None})
    report = {"schema": "dask8801_local_behavior_capture.v1", "revision_id": revision["revision_id"],
              "scope": "isolated_config_api_and_protocol_checks_only_not_full_dask_not_cpu_not_formal_score_not_semantic_adjudication",
              "runtime": {"python": platform.python_version(), "yaml": yaml.__version__, "pytest": pytest.__version__, "os": platform.system(), "identity": "local_non_root"},
              "test_file_sha256": sha(text.encode()), "collector_protocol_sha256": sha((HERE / "tools/config_diagnostic_protocol.py").read_bytes()),
              "judge_prompt_sha256": revision["diagnostic_side_policy"]["semantic_judge_prompt"]["sha256"], "protocol_checks": checks, "rows": rows}
    target = out / arguments.output_name
    if target.exists():
        raise ValueError("已有原件不得覆盖；修订后另用新文件名")
    save_json(target, report)
    print(json.dumps({"local_controls": len(rows), "api_pass": [r["candidate"] for r in rows if r["isolated_behavior_pass"]],
                      "complete_12case_captures": [r["candidate"] for r in rows if r["diagnostic_capture"]["state"] == "complete"], "protocol_checks": checks}, ensure_ascii=False))


if __name__ == "__main__":
    main()
