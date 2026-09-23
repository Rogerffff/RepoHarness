"""只读复核 8 题证据；不启动 Pydantic、Docker、模型或 RH2。

从仓库根执行本脚本。纯 Python 探针仅执行精确基线抽取的方法/排序函数，
其测试替身不等价于完整 Pydantic 集成运行。结果写入本审计目录。
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from unittest.mock import ANY


ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
WORKSTREAMS = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams"
REPO = ROOT / "runs/env_overnight_20260916/repos/pydantic"
IDS = [f"pydantic__pydantic-{n}" for n in [5386, 5662, 5706, 6043, 6283, 8500, 8511, 9134]]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(name: str) -> dict:
    return {
        d["instance_id"]: d
        for d in map(json.loads, (WORKSTREAMS / f"s2/ingest/{name}.jsonl").read_text().splitlines())
        if d["instance_id"] in IDS
    }


def source(commit: str, path: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"], text=True)


def method(text: str, name: str) -> str:
    cls = next(x for x in ast.parse(text).body if isinstance(x, ast.ClassDef) and x.name == "BaseModel")
    fn = next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == name)
    return ast.get_source_segment(text, fn)


def apply_in_memory(text: str, patch: str) -> str:
    """只将统一补丁应用到内存字符串；上下文不符即报错。"""
    lines = text.splitlines(keepends=True)
    result, cursor = [], 0
    chunks = re.split(r"(?=^@@ )", patch, flags=re.M)[1:]
    for chunk in chunks:
        header, *body = chunk.splitlines(keepends=True)
        match = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", header)
        assert match, header
        start = int(match[1]) - 1
        result.extend(lines[cursor:start])
        cursor = start
        for line in body:
            if line.startswith((" ", "-")):
                assert lines[cursor] == line[1:], (cursor, lines[cursor], line)
                if line.startswith(" "):
                    result.append(lines[cursor])
                cursor += 1
            elif line.startswith("+"):
                result.append(line[1:])
    result.extend(lines[cursor:])
    return "".join(result)


def counts(path: Path) -> dict:
    return {key: int(n) for n, key in re.findall(r"^\s*(\d+) (passed|failed|skipped|xfailed|deselected)\s*$", path.read_text(), re.M)}


public, grading, validation = (bundle(x) for x in ["public_bundles_v0", "grading_bundles_v2_v0", "validation_bundles_v0"])
report = {"scope": "历史证据只读复核及本地纯 Python 探针；本轮未跑真实 RH2", "environment": {}, "historical_runs": {}, "local_probes": {}}
catalog = json.loads((WORKSTREAMS / "project1_execution/env_recipe_repair_20260919/repair_catalog.json").read_text())
for task in catalog["tasks"]:
    iid = task["instance_id"]
    if iid not in IDS:
        continue
    item = {"status": task["status"], "selected_batch": task["selected_batch"], "roles": {}}
    assert item["status"] == "verified_environment_pair"
    for role, observation in task["observations"].items():
        path = ROOT / observation["log"]
        digest = sha(path)
        assert digest == observation["log_sha256"]
        assert observation["install"]["install_rc_last_command"] == 0
        assert observation["report"]["reward"] == (1.0 if role == "gold" else 0.0)
        if role == "gold":
            assert observation["install"]["test_rc"] == 0
        item["roles"][role] = {"log": observation["log"], "sha256": digest, "reward": observation["report"]["reward"], "install_rc": observation["install"]["install_rc_last_command"], "test_rc": observation["install"]["test_rc"]}
    report["environment"][iid] = item

# 6043/8500：重解析修正 pytest-pretty 判读后的历史独立脚本日志，按完整参考 ID 核对。
for n in [6043, 8500]:
    iid = f"pydantic__pydantic-{n}"
    data = {}
    for state in ["base", "gold", "fake"]:
        path = ROOT / f"runs/env_overnight_20260916/M2/L7/rerun/{iid}/{state}.txt"
        statuses = dict(re.findall(r"^(tests/\S+) (PASSED|FAILED|SKIPPED|XFAIL)[ \t]*(?:\[[ \t]*\d+%\])?[ \t]*$", path.read_text(), re.M))
        refs = grading[iid]["fail_to_pass"] + grading[iid]["pass_to_pass"]
        missing = [key for key in refs if key not in statuses]
        failed = [key for key in refs if statuses.get(key) != "PASSED"]
        assert not missing
        assert len(failed) == (1 if state == "base" else 0)
        data[state] = {"log": str(path.relative_to(ROOT)), "sha256": sha(path), "reference_count": len(refs), "not_passed": failed, "evidence_kind": "existing_independent_script_not_RH2"}
    report["historical_runs"][f"L7_{n}"] = data

for n, states, run in [(5706, ["base", "gold", "candidate"], "base_sequence_tests"), (8500, ["gold", "candidate"], "diagnostic")]:
    data = {}
    for state in states:
        path = ROOT / f"runs/env_overnight_20260916/M2/counterexamples/pydantic__pydantic-{n}/results/agent/{state}__{run}.txt"
        data[state] = {"log": str(path.relative_to(ROOT)), "sha256": sha(path), "counts": counts(path), "evidence_kind": "existing_independent_script_not_RH2"}
    if n == 5706:
        assert data["base"]["counts"]["passed"] == data["gold"]["counts"]["passed"] == 16
        assert data["candidate"]["counts"]["failed"] == 6
    else:
        assert data["gold"]["counts"]["failed"] == data["candidate"]["counts"]["failed"] == 2
        for state in states:
            assert '{"b":"b","a":"a"}' in (ROOT / data[state]["log"]).read_text()
    report["historical_runs"][f"L3_{n}"] = data

# 5662：使用实际 __eq__ 方法，隔离非 BaseModel 分支的 Python 反向比较协议。
iid = "pydantic__pydantic-5662"
eq = method(source(public[iid]["base_commit"], "pydantic/main.py"), "__eq__")
eq_results = {}
assert "tests/test_main.py::test_model_equality_dump" in grading[iid]["pass_to_pass"]
for variant, replacement in [("base", "return False"), ("bad_delegate", "return other == self"), ("protocol_fix", "return NotImplemented")]:
    namespace = {"Any": object, "Undefined": object()}
    exec("class BaseModel:\n" + "\n".join("    " + line for line in eq.replace("return False", replacement, 1).splitlines()), namespace)
    model = namespace["BaseModel"]()
    outcomes = {}
    for label, other in [("ANY", ANY), ("dict", {}), ("int", 1)]:
        try:
            outcomes[label] = model == other
        except RecursionError:
            outcomes[label] = "RecursionError"
    eq_results[variant] = outcomes
assert eq_results["bad_delegate"]["dict"] == "RecursionError"
assert eq_results["protocol_fix"] == {"ANY": True, "dict": False, "int": False}
report["local_probes"]["5662_exact_eq_with_protocol_doubles"] = eq_results

# 6043：执行 gold 的真实排序函数及既有 fake 的真实插入代码；输入只是 schema 字典。
iid = "pydantic__pydantic-6043"
gold_src = apply_in_memory(source(public[iid]["base_commit"], "pydantic/json_schema.py"), validation[iid]["golden_patch"])
fn = next(x for x in ast.parse(gold_src).body if isinstance(x, ast.FunctionDef) and x.name == "_sort_json_schema")
namespace = {}
exec("from __future__ import annotations\n" + ast.get_source_segment(gold_src, fn), namespace)
fake_patch = (ROOT / "runs/env_overnight_20260916/M2/L7/patches/pydantic__pydantic-6043.fake.diff").read_text()
fake_code = "\n".join(x[1:] for x in fake_patch.splitlines() if x.startswith("+") and not x.startswith("+++"))
fake_code = "\n".join(x[8:] if x.startswith("        ") else x for x in fake_code.splitlines())
schema = {"type": "object", "properties": {"z": {"title": "Z", "type": "object", "properties": {"z": {"type": "integer"}, "a": {"type": "string"}}}, "a": {"type": "string"}}, "prefixItems": [{"type": "string"}, {"type": "integer"}]}
env = {"json_schema": copy.deepcopy(schema)}
exec(fake_code, env)
gold_schema = namespace["_sort_json_schema"](schema)
schema_results = {"fake_top_properties": list(env["json_schema"]["properties"]), "fake_nested_properties": list(env["json_schema"]["properties"]["z"]["properties"]), "gold_nested_properties": list(gold_schema["properties"]["z"]["properties"]), "gold_prefix_items_order": [x["type"] for x in gold_schema["prefixItems"]]}
assert schema_results["fake_nested_properties"] == ["z", "a"]
assert schema_results["gold_nested_properties"] == ["a", "z"]
assert schema_results["gold_prefix_items_order"] == ["string", "integer"]
report["local_probes"]["6043_exact_sort_transforms_on_plain_data"] = schema_results

# 8500：抽取实际 model_construct，只用字段/实例替身检查字典写入；不模拟 serializer。
class FieldDouble:
    alias = None

    def __init__(self, required=True, default=None):
        self.required, self.default = required, default

    def is_required(self):
        return self.required

    def get_default(self, call_default_factory=False):
        return self.default


iid = "pydantic__pydantic-8500"
base_src = source(public[iid]["base_commit"], "pydantic/main.py")
variants = {"base": base_src, "gold": apply_in_memory(base_src, validation[iid]["golden_patch"]), "fake_alphabetical": apply_in_memory(base_src, (ROOT / "runs/env_overnight_20260916/M2/L7/patches/pydantic__pydantic-8500.fake.diff").read_text())}
construct_results = {}
for variant, text in variants.items():
    ns = {"_object_setattr": object.__setattr__}
    exec("from __future__ import annotations\nclass ModelDouble:\n    @classmethod\n" + "\n".join("    " + line for line in method(text, "model_construct").splitlines()), ns)
    cls = ns["ModelDouble"]
    cls.model_config, cls.__pydantic_root_model__, cls.__pydantic_post_init__ = {}, False, None
    observations = {}
    for scenario, fields, values, after in [
        ("original_issue", {"a": FieldDouble(), "b": FieldDouble(False, None)}, {}, {"a": "a", "b": "b"}),
        ("official_case", {"a": FieldDouble(False, "a"), "b": FieldDouble()}, {"b": "b"}, {}),
        ("nonalphabetical", {"z": FieldDouble(False, "z"), "a": FieldDouble()}, {"a": "a"}, {}),
    ]:
        cls.model_fields = fields
        instance = cls.model_construct(**values)
        # The real instance stores these in slots; exclude stand-in internal bookkeeping from key observations.
        for key, value in after.items():
            setattr(instance, key, value)
        observations[scenario] = [key for key in instance.__dict__ if key in fields]
    construct_results[variant] = observations
assert construct_results["gold"]["original_issue"] == ["b", "a"]
assert construct_results["gold"]["nonalphabetical"] == ["z", "a"]
assert construct_results["fake_alphabetical"]["nonalphabetical"] == ["a", "z"]
report["local_probes"]["8500_exact_construct_with_field_doubles_no_serializer"] = construct_results

(OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"environment_tasks": len(report["environment"]), "environment_log_hashes": sum(len(x["roles"]) for x in report["environment"].values()), "historical_groups": len(report["historical_runs"]), "local_probes": list(report["local_probes"]), "new_RH2_runs": 0}, ensure_ascii=False))
