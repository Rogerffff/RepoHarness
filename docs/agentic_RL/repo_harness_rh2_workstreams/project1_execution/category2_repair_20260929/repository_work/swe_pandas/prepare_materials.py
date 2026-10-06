"""生成 Pandas 题级草案；只读历史原件，只写本工作包，不运行容器或 pandas。"""

from __future__ import annotations

import ast
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
from datetime import datetime
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
PARSER = REPO / "rh2/src/repoharness2/envpack/swegym_parsers.py"
BINDER = REPO / "rh2/experiments/env_recipe_repair_20260919/reference_bindings.py"
PARENT_BINDINGS = REPO / "runs/env_recipe_repair_20260919/pandas_meta_v3/reference_bindings_v1.json"
SOURCES = {
    "48106": {
        "export": "runs/swegym_quality_batch02_20260921_v2",
        "logs": {
            "gold": "runs/env_recipe_repair_20260919/pandas_meta_v3/tasks/pandas-dev__pandas-48106/gold/eval_logs/evallog_replay-er19-pandas_meta__1160016c.eval.log",
            "noop": "runs/env_recipe_repair_20260919/pandas_meta_v3/tasks/pandas-dev__pandas-48106/noop/eval_logs/evallog_replay-er19-pandas_meta__67b00d26.eval.log",
        },
        "prefixes": [
            "pandas/tests/indexing/test_loc.py::TestLocBaseIndependent::test_loc_setitem_datetimeindex_tz[datetime.timezone(datetime.timedelta(days=-1,",
            "pandas/tests/indexing/test_loc.py::TestPartialStringSlicing::test_loc_getitem_partial_slice_non_monotonicity[datetime.timezone(datetime.timedelta(days=-1,",
        ],
    },
    "50319": {
        "export": "runs/swegym_quality_batch03_20260921_v1",
        "logs": {
            "gold": "runs/env_recipe_repair_20260919/reference_v1/runs/pandas-dev__pandas-50319-gold/eval_logs/evallog_replay-er19-ref-v1-panda_c332d5e5.eval.log",
            "noop": "runs/env_recipe_repair_20260919/reference_v1/runs/pandas-dev__pandas-50319-noop/eval_logs/evallog_replay-er19-ref-v1-panda_55456694.eval.log",
        },
        "prefixes": [
            "pandas/tests/tslibs/test_parsing.py::test_guess_datetime_format_with_parseable_formats[2011-12-30",
            "pandas/tests/tslibs/test_parsing.py::test_guess_datetime_format_no_padding[2011-1-1",
        ],
    },
}
TEST_FILE = "pandas/tests/tslibs/test_parsing.py"
SOURCE_FILE = "pandas/_libs/tslibs/parsing.pyx"
NEW_CASES = [
    ("reported", "27.03.2003 14:55:00.000", datetime(2003, 3, 27, 14, 55)),
    ("another-dot-date", "28.04.2004 16:07:08.123456", datetime(2004, 4, 28, 16, 7, 8, 123456)),
]
NEW_TEST = '''@pytest.mark.parametrize(
    "string,expected",
    [
        pytest.param(
            "27.03.2003 14:55:00.000",
            datetime(2003, 3, 27, 14, 55),
            id="reported",
        ),
        pytest.param(
            "28.04.2004 16:07:08.123456",
            datetime(2004, 4, 28, 16, 7, 8, 123456),
            id="another-dot-date",
        ),
    ],
)
def test_guess_datetime_format_dot_date_contract(string, expected):
    # GH50317 permits None when inference is unavailable.
    result = parsing.guess_datetime_format(string)
    if result is not None:
        assert isinstance(result, str)
        assert datetime.strptime(string, result) == expected


'''


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_digest(value) -> str:
    # contracts/_base.py 的既定算法；发布方仍须通过严格模型核对，不以此代替 loader。
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def file_ref(path: Path) -> dict:
    return {"path": relative(path), "sha256": sha(path.read_bytes())}


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summary(text: str) -> tuple[str, dict]:
    assert text.count(">>>>> Start Test Output") == text.count(">>>>> End Test Output") == 1
    segment = text.split(">>>>> Start Test Output", 1)[1].split(">>>>> End Test Output", 1)[0]
    states = {}
    for line in segment.splitlines():
        line = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", line).strip()
        match = re.match(r"^(PASSED|FAILED|ERROR|XFAIL|SKIPPED) (pandas/.*)", line)
        if match:
            node = match[2].split(" - ", 1)[0]
            states.setdefault(node, []).append(match[1])
    return segment, states


def make_patch(path: str, before: str, after: str) -> str:
    return f"diff --git a/{path} b/{path}\n" + "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}", n=3,
    ))


def check_patch(patch: Path, source: Path, relpath: str) -> str:
    # 临时副本只有本补丁所需文件；不改历史 checkout，不需要安装或 git init。
    with tempfile.TemporaryDirectory(prefix="pandas-material-check-") as temp:
        target = Path(temp) / relpath
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
        for args in (["--check", "--whitespace=error"], ["--whitespace=error"]):
            subprocess.run(["git", "apply", *args, str(patch)], cwd=temp, check=True, capture_output=True)
        return target.read_text()


def verify_source_rows(private: Path, public_path: Path) -> list[dict]:
    refs = json.loads((private / "source_refs.json").read_text())
    verified = []
    for kind, export in (("grading", private / "grading.json"), ("public", public_path)):
        ref = refs[kind]
        with (REPO / ref["path"]).open("rb") as handle:
            line = next(value for number, value in enumerate(handle, 1) if number == ref["line"])
        recorded = ref.get("raw_line_sha256")
        # 48106 旧导出只有行号；50319 还登记了原始行摘要。分别保留证据范围。
        digest = hashlib.sha256(line).hexdigest()
        if recorded is not None and digest != recorded:
            digest = hashlib.sha256(line.rstrip(b"\r\n")).hexdigest()
        if recorded is not None:
            assert digest == recorded, (kind, ref)
        value = json.loads(line)
        assert value == json.loads(export.read_text()), (kind, export)
        if kind == "grading":
            assert value["test_patch"].encode() == (private / "test.patch").read_bytes()
        verified.append({"kind": kind, "path": ref["path"], "line": ref["line"],
                         "raw_line_sha256": "sha256:" + digest,
                         "historical_hash_recorded": recorded is not None,
                         "export_equal_to_source": True, "canonical_digest": canonical_digest(value)})
    return verified


def prepare_bindings(parser, binder) -> list[dict]:
    parent = json.loads(PARENT_BINDINGS.read_text())
    reports = []
    for short, source in SOURCES.items():
        iid = f"pandas-dev__pandas-{short}"
        private = REPO / source["export"] / "private" / iid
        grading = json.loads((private / "grading.json").read_text())
        parent_entry = parent["tasks"][iid]
        bindings = {k: list(v) for k, v in parent_entry["bindings"].items()}
        segments = {}
        raw = {}
        for role, path in source["logs"].items():
            segments[role], raw[role] = summary((REPO / path).read_text())
        added = {}
        controls = []
        for prefix in source["prefixes"]:
            members = sorted(node for node in raw["gold"] if node.split()[0] == prefix)
            assert len(members) in (2, 4), (iid, prefix, members)
            assert set(members) == {node for node in raw["noop"] if node.split()[0] == prefix}
            assert prefix in grading["pass_to_pass"] and prefix not in bindings
            assert all(raw[role][node] == ["PASSED"] for role in raw for node in members)
            bindings[prefix] = added[prefix] = members
            all_pass = "\n".join("PASSED " + node for node in members)
            assert binder.bound_states(all_pass, {prefix: members})[0][prefix] == "PASSED"
            controls.append({"alias": prefix, "case": "all_pass", "bound": "PASSED"})
            for node in members:
                for status in ("FAILED", "ERROR", "SKIPPED", "XFAIL", None):
                    # 合成软件控制：PASS 先列，异常状态最后列；不是候选或真实 pytest 会话。
                    text = "\n".join("PASSED " + other for other in members if other != node)
                    if status is not None:
                        text += "\n" + status + " " + node
                    observed = binder.bound_states(text, {prefix: members})[0].get(prefix)
                    assert observed == status, (node, status, observed)
                    controls.append({"alias": prefix, "node": node, "case": status or "missing",
                                     "legacy_alias": parser.parse_log_pytest(text).get(prefix), "bound": observed})
        historical = {}
        for role, segment in segments.items():
            states = parser.parse_log_pytest(segment)
            corrected, _ = binder.bound_states(segment, bindings)
            for alias in bindings:
                states.pop(alias, None)
            states.update(corrected)
            references = grading["fail_to_pass"] + grading["pass_to_pass"]
            assert all(alias in states for alias in references)
            historical[role] = {
                "log": file_ref(REPO / source["logs"][role]),
                "reference_count": len(references), "missing_references": [],
                "new_alias_states": {alias: states[alias] for alias in added},
                "f2p_state_counts": {status: sum(states[n] == status for n in grading["fail_to_pass"])
                                     for status in ("PASSED", "FAILED", "XFAIL", "SKIPPED", "ERROR")},
                "scope": "历史日志在当前解析/诊断绑定函数上的软件回放，不是重新评分或容器执行",
            }
        out = HERE / "tasks" / iid
        base = REPO / source["export"] / "public" / iid / "base"
        public_path = REPO / source["export"] / "public" / iid / "public_bundle.json"
        source_rows = verify_source_rows(private, public_path)
        test_path = "pandas/tests/indexing/test_loc.py" if short == "48106" else TEST_FILE
        write(out / "original_test.patch", (private / "test.patch").read_text())
        write(out / "public_tests" / test_path, (base / test_path).read_text())
        dump(out / "reference_bindings_draft.json", {
            "version": f"pandas{short}-complete-node-bindings-draft-v1",
            "status": "draft_not_registered", "parent": file_ref(PARENT_BINDINGS),
            "tasks": {iid: {"bindings": bindings, "added_aliases": list(added),
                            "meaning": "保留来源参考分组；完整成员缺席不沿用旧别名末值。"}},
        })
        dump(out / "revision_draft.json", {
            "schema": "rh2.swe_pandas_material_preparation.v1", "status": "draft_not_registered_or_cpu_validated",
            "instance_id": iid, "base_commit": grading["base_commit"],
            "parent_grading": file_ref(private / "grading.json"),
            "parent_grading_digest": canonical_digest(grading),
            "public_bundle": file_ref(public_path),
            "public_bundle_digest": canonical_digest(json.loads(public_path.read_text())),
            "original_test_patch": file_ref(out / "original_test.patch"),
            "public_base_test": file_ref(out / "public_tests" / test_path),
            "base_test_exists": True, "test_file": test_path,
            "fail_to_pass_before": grading["fail_to_pass"], "fail_to_pass_after": grading["fail_to_pass"],
            "pass_to_pass_before": grading["pass_to_pass"], "pass_to_pass_after": grading["pass_to_pass"],
            "reference_bindings": file_ref(out / "reference_bindings_draft.json"),
            "public_change": False,
            "shared_entry_need": "固定登记完整参考绑定、材料身份与缺席语义；48106 沿用已验安装配方。",
            "runtime_pending": ["新宿主身份/导入", "正式评分/材料绑定接线", "非作者核查", "发布与探针请求"],
        })
        reports.append({"instance_id": iid, "parent_binding_groups": len(parent_entry["bindings"]),
                        "binding_groups": len(bindings), "added_groups": added,
                        "parent_source_rows": source_rows,
                        "historical_replay": historical, "synthetic_controls": controls})
    return reports


def prepare_50319() -> dict:
    iid = "pandas-dev__pandas-50319"
    export = REPO / SOURCES["50319"]["export"]
    base = export / "public" / iid / "base"
    private = export / "private" / iid
    out = HERE / "tasks" / iid
    source = (base / SOURCE_FILE).read_text()
    tests = (base / TEST_FILE).read_text()
    anchor = '@pytest.mark.parametrize("dayfirst,expected", [(True, "%d/%m/%Y"), (False, "%m/%d/%Y")])'
    assert tests.count(anchor) == 1
    effective = tests.replace(anchor, NEW_TEST + anchor)
    write(out / "test_patch_draft.patch", make_patch(TEST_FILE, tests, effective))
    # 正对照只捕获 _fill_token 的 ValueError，保留既有成功路径和外部 TypeError。
    call = "            token_filled = _fill_token(tokens[i], padding)\n"
    assert source.count(call) == 1
    replacements = {
        "none_fallback": "            try:\n                token_filled = _fill_token(tokens[i], padding)\n            except ValueError:\n                return None\n",
        "bad_format": "            try:\n                token_filled = _fill_token(tokens[i], padding)\n            except ValueError:\n                return \"%Y-%m-%d\"\n",
        "reported_only_none": "            try:\n                token_filled = _fill_token(tokens[i], padding)\n            except ValueError:\n                if dt_str == \"27.03.2003 14:55:00.000\":\n                    return None\n                raise\n",
    }
    candidates = {}
    for name, replacement in replacements.items():
        candidates[name] = source.replace(call, replacement)
    first_body = '    day_attribute_and_format = (("day",), "%d", 2)\n'
    assert source.count(first_body) == 1
    candidates["constant_none"] = source.replace(first_body, "    return None\n\n" + first_body)
    candidates["gold"] = None
    patch_checks = []
    for name, revised in candidates.items():
        patch = out / "candidates" / f"{name}.patch"
        if name == "gold":
            write(patch, (private / "gold.patch").read_text())
        else:
            write(patch, make_patch(SOURCE_FILE, source, revised))
        applied = check_patch(patch, base / SOURCE_FILE, SOURCE_FILE)
        if revised is not None:
            assert applied == revised
        patch_checks.append({"candidate": name, "patch": file_ref(patch), "git_apply_check": "passed",
                             "cython_compile": "not_run"})
    effective = check_patch(out / "test_patch_draft.patch", base / TEST_FILE, TEST_FILE)
    tree = ast.parse(effective)
    # 直接执行新测试函数的独立返回值控制；不导入 pandas，不冒充候选验证。
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "test_guess_datetime_format_dot_date_contract")
    function.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    oracle_controls = []
    for label, value, accept in [
        ("none", None, True), ("valid_format", "%d.%m.%Y %H:%M:%S.%f", True),
        ("wrong_format", "%Y-%m-%d", False), ("wrong_date", "%m.%d.%Y %H:%M:%S.%f", False),
        ("false", False, False), ("zero", 0, False), ("empty_string", "", False),
    ]:
        namespace = {"datetime": datetime, "parsing": SimpleNamespace(guess_datetime_format=lambda s: value)}
        exec(compile(module, "<draft-oracle-control>", "exec"), namespace)
        for case, string, expected in NEW_CASES:
            passed = True
            try:
                namespace[function.name](string, expected)
            except (AssertionError, ValueError, TypeError):
                passed = False
            assert passed == accept, (label, case)
            oracle_controls.append({"case": case, "return_value_control": label, "accepted": passed})
    # 新增 None 接受范围不放宽已有成功格式契约。
    old_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == "test_guess_datetime_format_with_parseable_formats")
    old_function.decorator_list = []
    old_module = ast.fix_missing_locations(ast.Module(body=[old_function], type_ignores=[]))
    namespace = {"parsing": SimpleNamespace(guess_datetime_format=lambda s: None)}
    exec(compile(old_module, "<old-format-control>", "exec"), namespace)
    try:
        namespace[old_function.name]("20111230", "%Y%m%d")
    except AssertionError:
        old_guard_rejects_none = True
    else:
        old_guard_rejects_none = False
    assert old_guard_rejects_none
    grading = json.loads((private / "grading.json").read_text())
    new_f2p = [f"{TEST_FILE}::test_guess_datetime_format_dot_date_contract[{case}]" for case, _, _ in NEW_CASES]
    parent_record = json.loads((out / "revision_draft.json").read_text())
    dump(out / "revision_draft.json", {
        **parent_record, "public_source": file_ref(base / SOURCE_FILE),
        "effective_test_patch": file_ref(out / "test_patch_draft.patch"),
        "fail_to_pass_replacement": {"before": grading["fail_to_pass"], "after": new_f2p},
        "fail_to_pass_after": new_f2p,
        "shared_entry_need": "固定登记有效测试补丁、替换来源 F2P、完整节点绑定，并使正式选择/恢复/保护/解析和材料身份一致。",
        "runtime_pending": ["真实收集节点", "同镜像 Cython 重编译与新进程加载", "原/新评分正负对照",
                            "actor 开发及 to_datetime 回退", "非作者核查", "正式发布与探针请求"],
    })
    return {"instance_id": iid, "patch_checks": patch_checks,
            "test_patch_git_apply_check": "passed", "effective_test_ast": "passed",
            "oracle_return_value_controls": oracle_controls,
            "existing_parseable_format_guard_rejects_none": old_guard_rejects_none,
            "runtime_candidate_results": "not_run"}


def main() -> None:
    parser = load_module("pandas_current_parser", PARSER)
    binder = load_module("pandas_diagnostic_binder", BINDER)
    bindings = prepare_bindings(parser, binder)
    revision = prepare_50319()
    report = {
        "as_of": "2026-10-03", "status": "offline_preparation_only",
        "code": {"parser": file_ref(PARSER), "diagnostic_binding": file_ref(BINDER)},
        "binding_checks": bindings, "test_revision_checks": revision,
        "limits": ["绑定使用已有诊断函数，不是 Pandas 正式 D6 接线验收。",
                   "合成状态与返回值替身仅检查软件语义，未证明真实候选错分或运行结果。",
                   "未执行 pandas、Cython 编译、Docker、SSH 或模型；无 CPU/GPU 正式验收。"],
    }
    dump(HERE / "offline_checks_20261003.json", report)
    artifact_files = sorted(path for path in (HERE / "tasks").rglob("*") if path.is_file())
    dump(HERE / "materials_manifest.json", {
        "schema": "rh2.swe_pandas_material_preparation_manifest.v1", "status": "draft",
        "owner_thread_id": "01a0fd63-67de-77d2-b1fe-6a74a1de4481", "as_of": "2026-10-03",
        "artifacts": [file_ref(path) for path in artifact_files],
        "offline_checks": file_ref(HERE / "offline_checks_20261003.json"),
        "generator": file_ref(Path(__file__).resolve()),
    })
    print(json.dumps({"status": report["status"], "binding_groups": sum(x["binding_groups"] for x in bindings),
                      "synthetic_binding_controls": sum(len(x["synthetic_controls"]) for x in bindings),
                      "oracle_controls": len(revision["oracle_return_value_controls"]),
                      "candidate_patch_checks": len(revision["patch_checks"]),
                      "report": relative(HERE / "offline_checks_20261003.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
