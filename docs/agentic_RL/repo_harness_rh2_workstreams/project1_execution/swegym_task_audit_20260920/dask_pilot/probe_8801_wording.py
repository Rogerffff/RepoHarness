"""8801 的错误文案对照；在仓库根用 rh2/.venv/bin/python 执行。

从精确 base 应用来源补丁，抽取两个配置函数和两个来源测试。
这是本地函数级反例，不是 Docker / 完整 pytest / RH2 评分复跑。
"""

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import pytest
import yaml


ROOT = Path.cwd()
INGEST = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
IID = "dask__dask-8801"
CLONE = ROOT / "runs/env_overnight_20260916/repos/dask"


def row(name):
    return next(
        r for r in map(json.loads, (INGEST / name).read_text().splitlines())
        if r["instance_id"].split("::")[-1] == IID
    )


def functions(source, names):
    tree = ast.parse(source)
    return "\n\n".join(
        ast.unparse(n) for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name in names
    )


public = row("public_bundles_v0.jsonl")
grading = row("grading_bundles_v2_v0.jsonl")
validation = row("validation_bundles_v0.jsonl")
with tempfile.TemporaryDirectory(prefix="rh2-8801-audit-") as tmp:
    work = Path(tmp)
    for rel in ("dask/config.py", "dask/tests/test_config.py"):
        target = work / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output([
            "git", "-C", str(CLONE), "show", public["base_commit"] + ":" + rel
        ]))
    for patch in (validation["golden_patch"], grading["test_patch"]):
        subprocess.run(["git", "apply", "-"], cwd=work, input=patch, text=True, check=True)
    gold = (work / "dask/config.py").read_text()
    variant = gold.replace("is malformed", "is invalid").replace(
        "original error ", "underlying error "
    ).replace("must have ", "must contain ")
    assert variant != gold
    test_names = [x.split("::")[-1] for x in grading["fail_to_pass"]]
    tests = functions((work / "dask/tests/test_config.py").read_text(), test_names)
    results = {}
    for label, source in (("gold", gold), ("wording_only_variant", variant)):
        namespace = {"os": os, "yaml": yaml, "pytest": pytest, "paths": []}
        body = functions(source, {"_load_config_file", "collect_yaml"})
        exec(compile("from __future__ import annotations\n" + body + "\n" + tests, label, "exec"), namespace)
        outcomes = {}
        for name in test_names:
            with tempfile.TemporaryDirectory(prefix="rh2-8801-case-") as case:
                try:
                    namespace[name](case)
                    outcomes[name] = "passed"
                except (Exception, pytest.fail.Exception) as error:
                    outcomes[name] = type(error).__name__
        semantic = []
        for payload, required in (("{", "error"), ("[1234]", "dict")):
            path = work / "semantic.yaml"
            path.write_text(payload)
            try:
                namespace["collect_yaml"]([str(path)])
            except ValueError as error:
                assert repr(str(path)) in str(error) and required in str(error)
                semantic.append({"input": payload, "type": "ValueError", "path_and_cause": True})
            else:
                raise AssertionError("missing actionable validation error")
        path.write_text("x: 1\n")
        assert namespace["collect_yaml"]([str(path)]) == [{"x": 1}]
        results[label] = {
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "official_f2p_functions": outcomes,
            "semantic_checks": semantic,
            "valid_mapping_preserved": True,
        }
    report = {
        "instance_id": IID,
        "base_commit": public["base_commit"],
        "scope": "local_extracted_source_and_official_test_functions_not_RH2",
        "change": "error wording only; exception type, file path, reason and valid input behavior preserved",
        "results": results,
    }
    output = Path(__file__).with_name("probe_8801_wording.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
