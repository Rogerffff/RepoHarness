"""准备 Pydantic 六题的离线修订包；不运行项目、不登记或激活共享入口。"""

from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
IDS = (5662, 6283, 8316, 8511, 8567, 9066)
OWNER = "01a0fd62-62c8-7cc3-b49f-e959fca60a14"
EXEC = "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
CLOUD = "rh2/experiments/category3_cloud_20260929"
FILES = {
    5662: "tests/test_main.py", 6283: "tests/test_root_model.py", 8316: "tests/test_utils.py",
    8511: "tests/test_dataclasses.py", 8567: "tests/test_validators.py", 9066: "tests/test_json_schema.py",
}

EXTRAS = {
    5662: '''


def test_equality_delegation_nonexample():
    class Model(BaseModel):
        value: str

    model = Model(value='ordinary-matcher')

    class Matcher:
        def __init__(self, answer):
            self.answer = answer
            self.seen = None

        def __eq__(self, other):
            self.seen = other
            return self.answer

    for answer in (True, False, NotImplemented):
        matcher = Matcher(answer)
        assert (model == matcher) is (answer is True)
        assert matcher.seen is model

    assert model != {'value': 'ordinary-matcher'}
    assert model != object()
''',
    6283: '''


def test_root_model_construct_equality_nonexample():
    class TextRoot(RootModel):
        root: str

    assert TextRoot('another') == TextRoot.model_construct('another')
''',
    8511: '''


def test_inherited_required_field_without_local_annotations():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: int = Field()

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    assert Child(x='3').x == 3


def test_inherited_hidden_field_without_local_annotations():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: int = Field(repr=False)

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    assert Child(x='3').x == 3


def test_inherited_factory_field_without_local_annotations():
    @pydantic.dataclasses.dataclass
    class Parent:
        x: int = Field(default_factory=lambda: 3)

    @pydantic.dataclasses.dataclass
    class Child(Parent):
        pass

    assert Child().x == 3


def test_field_default_repr_stays_visible():
    @pydantic.dataclasses.dataclass
    class Visible:
        x: int = Field(default=3)

    assert 'x=3' in repr(Visible())
''',
    8567: '''


def test_plain_validator_serializer_unsupported_type_both_orders():
    class Unsupported:
        pass

    serializer = PlainSerializer(lambda value: 'custom!', return_type=str)
    validator = PlainValidator(lambda value: Unsupported())

    class Before(BaseModel):
        value: Annotated[Unsupported, serializer, validator]

    class After(BaseModel):
        value: Annotated[Unsupported, validator, serializer]

    for model in (Before(value=1), After(value=1)):
        assert isinstance(model.value, Unsupported)
        assert model.model_dump() == {'value': 'custom!'}
        assert model.model_dump_json() == '{"value":"custom!"}'


def test_plain_validator_unresolved_inner_forward_reference():
    class Model(BaseModel):
        value: Annotated['NotDefinedAnywhere8567', PlainValidator(lambda value: value)]

    assert Model(value=5).value == 5


def test_plain_validator_typing_typeddict_inner_schema_not_required():
    from typing import TypedDict

    class Inner(TypedDict):
        a: int

    class Model(BaseModel):
        value: Annotated[Inner, PlainValidator(lambda value: value)]

    assert Model(value={'a': 1}).value == {'a': 1}
''',
    9066: '''


def test_default_encoding_preserves_stdlib_dataclass_instance():
    import dataclasses

    @dataclasses.dataclass
    class Point:
        x: int

    class Model(BaseModel):
        point: Point = Point(1)

    assert Model.model_json_schema()['properties']['point']['default'] == {'x': 1}
''',
}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def run(cwd: Path, args: list[str]) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args}: {result.stderr}")


def patch_files(patch: str) -> list[str]:
    names = re.findall(r"^\+\+\+ b/(.+)$", patch, re.M)
    assert names and len(names) == len(set(names)), "补丁路径缺失／重复"
    for name in names:
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
    return names


def apply(base: Path, patch: str) -> dict[str, str]:
    with tempfile.TemporaryDirectory(prefix="pyd-materials-") as temp:
        folder = Path(temp)
        names = patch_files(patch)
        for name in names:
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(base / name, target)
        asset = folder / "input.patch"
        asset.write_text(patch)
        run(folder, ["git", "apply", "--check", str(asset)])
        run(folder, ["git", "apply", str(asset)])
        return {name: (folder / name).read_text() for name in names}


def test_nodes(text: str) -> dict[str, str]:
    return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def input_rows(root: Path, filename: str) -> dict[str, tuple[dict, bytes]]:
    rows = {}
    for raw in (root / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest" / filename).read_bytes().splitlines():
        item = json.loads(raw)
        rows[item["instance_id"]] = (item, raw)
    return rows


def controls(root: Path, n: int, private: Path) -> dict[str, tuple[bytes, str, int]]:
    result = {"noop": (b"", "empty", 0),
              "gold": ((private / "gold.patch").read_bytes(), (private / "gold.patch").relative_to(root).as_posix(), 1)}
    inputs = root / "runs/swegym_cpu_preprobe_20260929/task_inputs" / f"pydantic__pydantic-{n}"
    cloud = root / CLOUD / f"pydantic{n}"
    extra = {}
    if n == 5662:
        extra = {"any_only": (inputs / "private_any_only.patch", 0),
                 "all_nonmodels_equal": (inputs / "private_degenerate_all_nonmodels_equal.patch", 0)}
    elif n == 6283:
        extra = {"validate_construct": (inputs / "private_degenerate_validate_construct.patch", 0)}
    elif n == 8316:
        positive = {"keep_digit", "lookaround", "scan", "upstream_main", "normalize",
                    "rv_tokens", "rv_scan_gold", "rv_split_join", "rv_acr_min2"}
        excluded = {"original_test", "revised_test_v1", "revised_test_v2", "revised_test_v3"}
        extra = {p.stem: (p, int(p.stem in positive)) for p in cloud.glob("*.patch") if p.stem not in excluded}
        assert len(extra) == 32
    elif n == 8511:
        result["gold"] = (*result["gold"][:2], 0)
        extra = {"narrow": (root / "runs/task2_swegym_dev_20260925/runs/semantic/pydantic8511/narrow/cand/pydantic__pydantic-8511.diff", 1)}
    elif n == 8567:
        result["gold"] = (*result["gold"][:2], 0)
        # 保留全部旧 v4 工件。三个候选是新正对照提名，不宣称已通过新增 B06/N3。
        positive = {"c3_reorder", "ok_post_attach", "ok_pv_first_keep_sers"}
        excluded = {"original_test", "revised_test_v1", "revised_test_v2", "revised_test_v3", "revised_test_v4"}
        extra = {p.stem: (p, int(p.stem in positive)) for p in cloud.glob("*.patch") if p.stem not in excluded}
        assert len(extra) == 29
    elif n == 9066:
        result["gold"] = (*result["gold"][:2], 0)
        extra = {"fallback": (cloud / "fallback.patch", 1), "upstream271": (cloud / "upstream271.patch", 1),
                 "gold_catch_user_error": (cloud / "gold_catch_user_error.patch", 0)}
    for name, (path, expected) in extra.items():
        result[name] = (path.read_bytes(), path.relative_to(root).as_posix(), expected)
    return result


def prepare(root: Path) -> None:
    public_rows = input_rows(root, "public_bundles_v0.jsonl")
    grading_rows = input_rows(root, "grading_bundles_v2_v0.jsonl")
    env_rows = input_rows(root, "environment_packages_v0.jsonl")
    packages = json.loads((root / EXEC / "category2_repair_20260929/repository_work_packages_20261002.json").read_text())
    package = next(group for group in packages["groups"] if group["package_id"] == "swe_pydantic")
    evidence = {task["instance_id"]: task["evidence_refs"] for task in package["tasks"]}
    all_results = []
    for n in IDS:
        iid = f"pydantic__pydantic-{n}"
        cache = root / ("runs/swegym_quality_batch01_20260921_v2" if n == 8511 else "runs/swegym_quality_expansion_20260925")
        public = cache / "public" / iid
        private = cache / "private" / iid
        base = public / "base"
        pub, pub_raw = public_rows[iid]
        grading, grading_raw = grading_rows[iid]
        env, env_raw = env_rows[iid]
        assert json.loads((public / "public_bundle.json").read_text()) == pub
        assert json.loads((private / "grading.json").read_text()) == grading
        identity = json.loads((public / "base_identity.json").read_text())
        assert pub["base_commit"] == grading["base_commit"] == env["base_commit"] == identity["base_commit"]
        original = grading["test_patch"]
        assert (private / "test.patch").read_text() == original
        filename = FILES[n]
        baseline = (base / filename).read_text()
        original_text = apply(base, original)[filename]
        if n == 8316:
            effective = (root / CLOUD / "pydantic8316/revised_test_v3.patch").read_text()
            effective_text = apply(base, effective)[filename]
            assert effective == (root / CLOUD / "pydantic8316/review/revised_test_v3_draft.patch").read_text()
        else:
            start = original_text
            if n == 8567:
                start = apply(base, (root / CLOUD / "pydantic8567/revised_test_v4.patch").read_text())[filename]
            effective_text = start.rstrip("\n") + EXTRAS[n]
            effective = f"diff --git a/{filename} b/{filename}\n" + "".join(difflib.unified_diff(
                baseline.splitlines(keepends=True), effective_text.splitlines(keepends=True),
                fromfile=f"a/{filename}", tofile=f"b/{filename}"))
            assert apply(base, effective)[filename] == effective_text
        before_nodes, after_nodes = test_nodes(original_text), test_nodes(effective_text)
        allowed_changes = {8316: {"test_camel2snake"}, 8567: {"test_plain_validator_plain_serializer"}}.get(n, set())
        assert all(after_nodes.get(name) == body for name, body in before_nodes.items() if name not in allowed_changes)
        added_names = [name for name in after_nodes if name not in before_nodes]
        assert all(name.startswith("test_") for name in added_names)
        added_f2p = [f"{filename}::{name}" for name in added_names] if n in (5662, 6283) else []
        if n == 8567:
            added_f2p = [f"{filename}::test_plain_validator_serializer_unsupported_type_both_orders"]
        added_p2p = [f"{filename}::{name}" for name in added_names if f"{filename}::{name}" not in added_f2p]
        f2p, p2p = grading["fail_to_pass"] + added_f2p, grading["pass_to_pass"] + added_p2p
        assert len(f2p + p2p) == len(set(f2p + p2p))
        folder = HERE / "tasks" / iid
        (folder / "public_tests" / "tests").mkdir(parents=True, exist_ok=True)
        (folder / "controls").mkdir(exist_ok=True)
        (folder / "public_tests" / filename).write_bytes((base / filename).read_bytes())
        (folder / "original_test.patch").write_text(original)
        (folder / "effective_test.patch").write_text(effective)
        if n in EXTRAS:
            (folder / "extra_tests.py").write_text(EXTRAS[n])
        recipe = root / EXEC / "env_recipe_repair_20260919/pydantic_v1" / f"{iid}.json"
        shutil.copyfile(recipe, folder / "install_recipe.json")
        matrix = []
        for label, (patch, origin, expected) in controls(root, n, private).items():
            asset = folder / "controls" / f"{label}.patch"
            asset.write_bytes(patch)
            if patch:
                outputs = apply(base, patch.decode())
                for text in outputs.values():
                    ast.parse(text)
            matrix.append({"candidate": label, "patch": f"controls/{label}.patch", "sha256": sha(patch),
                           "source": origin, "expected_reward_not_observed": expected})
        revision = {
            "schema": "pydantic.offline_material_proposal.v1", "runtime_registration": False,
            "as_of": "2026-10-03", "instance_id": iid, "owner_thread_id": OWNER,
            "status": "prepared_pending_independent_review_and_cpu_acceptance",
            "revision_id": {8316: "pyd8316-acronym-v3", 8567: "pyd8567-order-old-behavior-v5"}.get(n, f"pyd{n}-behavior-v1"),
            "base_commit": pub["base_commit"], "base_tree": identity["base_tree"],
            "source_cache": public.relative_to(root).as_posix(),
            "source_bindings": {"public_row_sha256": sha(pub_raw), "grading_row_sha256": sha(grading_raw),
                                "environment_row_sha256": sha(env_raw), "public_bundle_digest": env["public_bundle_digest"],
                                "parent_grading_digest": env["grading_bundle_digest"],
                                "image_manifest_digest": env["image_manifest_digest"]},
            "original_test_patch_sha256": sha(original.encode()), "effective_test_patch_sha256": sha(effective.encode()),
            "test_files": [{"path": filename, "base_sha256": sha((base / filename).read_bytes()),
                            "asset": f"public_tests/{filename}"}],
            "original_fail_to_pass": grading["fail_to_pass"], "original_pass_to_pass": grading["pass_to_pass"],
            "added_fail_to_pass": added_f2p, "added_pass_to_pass": added_p2p,
            "effective_fail_to_pass": f2p, "effective_pass_to_pass": p2p,
            "eval_cmd": grading["eval_cmd"], "python_version": grading["python_version"],
            "public_material_changed": False, "private_solver_material": True,
            "evidence_refs": evidence[iid], "install_recipe_sha256": sha(recipe.read_bytes()),
            "source_row_hash_convention": "原 ingest JSONL 单行字节，不含换行符；缓存 JSON 内容逐字段相等。",
            "matrix": matrix,
            "shared_entry_need": "受信 test_patch 替换；原参考完整保留；按本单追加 F2P/P2P；固定安装资产，发布到新的冻结版本。",
        }
        dump(folder / "revision.json", revision)
        checks = {"instance_id": iid, "scope": "offline_patch_and_ast_only",
                  "cached_rows_equal_original_ingest": True, "identity_matches_source_rows": True,
                  "original_and_effective_patch_apply": True, "preserved_existing_test_ast_except_declared_change": True,
                  "declared_changed_functions": sorted(allowed_changes), "unique_reference_ids": True,
                  "candidate_patch_application_and_ast_checks": len(matrix) - 1,
                  "reference_counts": {"original_f2p": len(grading["fail_to_pass"]), "original_p2p": len(grading["pass_to_pass"]),
                                       "effective_f2p": len(f2p), "effective_p2p": len(p2p)},
                  "project_test_execution": False, "pytest_collection": False, "formal_grade": False,
                  "actor_validation": False, "independent_review": False, "shared_activation": False}
        dump(folder / "static_result.json", checks)
        files = {path.relative_to(folder).as_posix(): {"sha256": sha(path.read_bytes()), "bytes": path.stat().st_size}
                 for path in sorted(folder.rglob("*")) if path.is_file() and path.name != "result_manifest.json"}
        dump(folder / "result_manifest.json", {"instance_id": iid, "as_of": "2026-10-03", "files": files,
                                              "runtime_results": [], "independent_review": "pending", "probe_request": "not_submitted"})
        all_results.append(checks)
    dump(HERE / "offline_checks.json", {"as_of": "2026-10-03", "scope": "six_task_offline_material_preparation", "tasks": all_results})
    print(json.dumps({"tasks": len(all_results), "candidate_patch_checks": sum(x['candidate_patch_application_and_ast_checks'] for x in all_results),
                      "project_tests_run": False, "formal_grade": False}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    prepare(parser.parse_args().repo_root.resolve())
