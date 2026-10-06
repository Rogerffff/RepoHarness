"""仅运行 8316 的纯字符串函数与现有测试断言；不导入 Pydantic 或运行 RH2。"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import tempfile
from pathlib import Path

from prepare_materials import HERE, apply


def check(root: Path) -> None:
    folder = HERE / "tasks/pydantic__pydantic-8316"
    revision = json.loads((folder / "revision.json").read_text())
    base = root / revision["source_cache"] / "base"
    tests = apply(base, (folder / "effective_test.patch").read_text())["tests/test_utils.py"]
    tree = ast.parse(tests)
    func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "test_camel2snake")
    parameters = ast.literal_eval(func.decorator_list[0].args[1])
    func.decorator_list = []
    rows = []
    for candidate in revision["matrix"]:
        patch = (folder / candidate["patch"]).read_text()
        source = apply(base, patch)["pydantic/alias_generators.py"] if patch else (base / "pydantic/alias_generators.py").read_text()
        # 该固定模块只依赖 Python 标准库 re；不加载 Pydantic 包或二进制 core。
        assert all(isinstance(node, (ast.Import, ast.Expr, ast.Assign, ast.FunctionDef)) for node in ast.parse(source).body)
        with tempfile.TemporaryDirectory(prefix="pyd8316-pure-") as temp:
            path = Path(temp) / "alias_generators.py"
            path.write_text(source)
            spec = importlib.util.spec_from_file_location("pyd8316_pure", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            namespace = {"to_snake": module.to_snake}
            exec(compile(ast.Module(body=[func], type_ignores=[]), "8316_test_function", "exec"), namespace)
            failures = []
            for value, expected in parameters:
                try:
                    namespace[func.name](value, expected)
                except AssertionError:
                    failures.append({"input": value, "actual": module.to_snake(value), "expected": expected})
            passed = not failures
            assert passed == bool(candidate["expected_reward_not_observed"]), candidate["candidate"]
            rows.append({"candidate": candidate["candidate"], "string_assertions_pass": passed,
                         "failed_parameters": failures, "parameter_count": len(parameters)})
    output = {"as_of": "2026-10-03", "scope": "local_stdlib_only_8316_function_assertions",
              "effective_test_patch_sha256": revision["effective_test_patch_sha256"],
              "python_version": __import__("sys").version.split()[0],
              "rows": rows, "candidate_count": len(rows), "matches_existing_expected_outcomes": True,
              "pydantic_imported": False, "project_pytest_run": False, "formal_grade": False,
              "limitations": "仅当前宿主 Python 的纯字符串断言；未收集全部测试、未运行其余 P2P、未验 Python3.8／actor／正式评分。"}
    (folder / "pure_function_result.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows), "matches_existing_expected_outcomes": True, "formal_grade": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    check(parser.parse_args().repo_root.resolve())
