"""只重建 DVC 独占目录中的材料草案；不发布 ingest，不执行 DVC 或访问远端。"""

from __future__ import annotations

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
ROOT = next(p for p in HERE.parents if (p / "rh2/src").is_dir() and (p / "AGENTS.md").is_file())
INGEST = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
EXECUTION = "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
PREFIX = "tests/func/test_repro_multistage.py::"
CONFIG = {
    "4166": {
        "revision_id": "dvc4166-behavior-v2-draft",
        "snapshot": "runs/swegym_quality_batch02_20260921_v2",
        "append": {"tests/func/test_ignore.py": "dvc4166_tests.py"},
        "f2p": ["tests/func/test_ignore.py::test_directory_rule_prunes_directory",
                "tests/func/test_ignore.py::test_negated_directory_rule_recovers_non_example"],
        "p2p": ["tests/func/test_ignore.py::test_directory_rule_keeps_regular_file"],
        "pins": {"pathspec": "0.8.1", "networkx": "2.3 + 已验 gcd 兼容改动"},
        "recipe": "dvc_install_v1c",
        "candidates": [("noop", 0), ("gold", 1), ("strip_positive_trailing_slash", 0)],
    },
    "5839": {
        "snapshot": "runs/swegym_quality_batch01_20260921_v2",
        "append": {"tests/unit/command/test_metrics.py": "dvc5839_tests.py"},
        "f2p": ["tests/unit/command/test_metrics.py::test_metrics_show_precision_real_values"],
        "p2p": [],
        "pins": {"pathspec": "0.8.1"},
        "recipe": "dvc_install_v1c",
        "candidates": [("noop", 0), ("gold", 1), ("hardcoded_precision8", 0)],
    },
    "6954": {
        "snapshot": "runs/swegym_quality_batch03_20260921_v1",
        "append": {"tests/unit/utils/serialize/test_python.py": "dvc6954_unit_tests.py",
                   "tests/func/params/test_show.py": "dvc6954_workflow_tests.py"},
        "f2p": ["tests/unit/utils/serialize/test_python.py::test_parse_negative_float_and_containers",
                "tests/func/params/test_show.py::test_negative_python_params_lock_and_repro"],
        "p2p": [],
        "pins": {"pygit2": "1.14.1"},
        "recipe": "dvc_install_v1c",
        "candidates": [("noop", 0), ("gold", 1), ("negative_int_only", 0)],
    },
    "9395": {
        "revision_id": "dvc9395-behavior-v2-draft",
        "snapshot": "runs/swegym_quality_batch01_20260921_v2",
        "append": {"tests/func/test_repro_multistage.py": "dvc9395_tests.py"},
        "f2p": [PREFIX + "test_pull_recovers_frozen_stage_for_downstream"],
        "p2p": [PREFIX + "test_pull_dry_preserves_workspace_and_cache[source]",
                PREFIX + "test_pull_dry_preserves_workspace_and_cache[output]",
                PREFIX + "test_pull_without_remote_when_nothing_missing[normal]",
                PREFIX + "test_pull_without_remote_when_nothing_missing[dry]",
                PREFIX + "test_pull_without_remote_preserves_modified_source",
                PREFIX + "test_pull_without_remote_still_errors_for_missing_source",
                PREFIX + "test_pull_no_run_cache_does_not_download_runs",
                PREFIX + "test_pull_existing_output_without_hash_can_run",
                PREFIX + "test_pull_changed_dependency_can_recompute",
                PREFIX + "test_pull_restores_from_http_with_local_run_cache"],
        "pins": {"pygit2": "1.14.1"},
        "recipe": "dvc_tail_v1",
        "candidates": [("noop", 0), ("gold", 0), ("c3_frozenfix", 1),
                       ("c3_missing_only", 0), ("up351_port", 0), ("w_swallow3", 0)],
    },
}


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_rows(name: str) -> dict:
    return {x["instance_id"]: x for x in (
        json.loads(line) for line in (INGEST / name).read_text().splitlines()
    )}


def patch_files(text: str) -> list[str]:
    pairs = re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.M)
    if not pairs or any(a != b or not a.startswith("tests/") or ".." in Path(a).parts for a, b in pairs):
        raise ValueError("测试补丁路径越界或无法解析")
    return sorted({a for a, _ in pairs})


def apply(directory: Path, patch: Path) -> None:
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=directory, check=True, capture_output=True)
    subprocess.run(["git", "apply", str(patch)], cwd=directory, check=True, capture_output=True)


def full_patch(base: Path, work: Path, files: list[str]) -> str:
    chunks = []
    for name in files:
        before = (base / name).read_text() if (base / name).is_file() else ""
        after = (work / name).read_text()
        if before == after:
            continue
        chunks.append(f"diff --git a/{name} b/{name}\n")
        if not (base / name).exists():
            chunks.append("new file mode 100644\n")
        chunks.extend(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"a/{name}" if (base / name).exists() else "/dev/null", tofile=f"b/{name}",
        ))
    return "".join(chunks)


def candidate_patch(source: Path, text: str, output: Path, relative: str) -> None:
    before = source.read_text()
    output.write_text(f"diff --git a/{relative} b/{relative}\n" + "".join(difflib.unified_diff(
        before.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=f"a/{relative}", tofile=f"b/{relative}",
    )))


def canonicalize_ids(task: str, work: Path) -> dict[str, list[str]]:
    if task == "4166":
        path = work / "tests/unit/test_ignore.py"
        text = path.read_text()
        old1 = '(" to_ignore", [" to_ignore"], False),'
        old2 = '(" to_ignore", ["\\\\ to_ignore"], True),'
        assert text.count(old1) == text.count(old2) == 1
        text = text.replace(old1, 'pytest.param(" to_ignore", [" to_ignore"], False, id="leading_space_literal"),')
        text = text.replace(old2, 'pytest.param(" to_ignore", ["\\\\ to_ignore"], True, id="leading_space_escaped"),')
        path.write_text(text)
        alias = "tests/unit/test_ignore.py::test_match_ignore_from_file["
        return {alias: [alias + "leading_space_literal]", alias + "leading_space_escaped]"]}
    if task == "6954":
        path = work / "tests/unit/utils/serialize/test_python.py"
        text = path.read_text()
        marker = "    ],\n)\ndef test_parse_valid_types"
        assert text.count(marker) == 1
        text = text.replace(marker, "    ],\n    ids=[\"bool\", \"int\", \"float\", \"str\", \"dict\", \"list\", \"set\", \"tuple\", \"none\", \"negative_int\", \"class\"],\n)\ndef test_parse_valid_types")
        marker = "    ],\n)\ndef test_parse_invalid_types"
        assert text.count(marker) == 1
        text = text.replace(marker, "    ],\n    ids=[\"constructor\", \"sum\"],\n)\ndef test_parse_invalid_types")
        path.write_text(text)
        prefix = "tests/unit/utils/serialize/test_python.py::"
        names = {"BOOL": "bool", "INT": "int", "FLOAT": "float", "STR": "str", "DICT": "dict",
                 "LIST": "list", "SET": "set", "TUPLE": "tuple", "NONE": "none", "UNARY_OP": "negative_int", "class": "class"}
        result = {prefix + "test_parse_valid_types[" + old: [prefix + "test_parse_valid_types[" + new + "]"] for old, new in names.items()}
        result.update({prefix + "test_parse_invalid_types[" + old: [prefix + "test_parse_invalid_types[" + new + "]"] for old, new in {"CONSTRUCTOR": "constructor", "SUM": "sum"}.items()})
        return result
    return {}


def main() -> None:
    grading = load_rows("grading_bundles_v2_v0.jsonl")
    packages = load_rows("environment_packages_v0.jsonl")
    summary = {}
    for task, config in CONFIG.items():
        instance = "iterative__dvc-" + task
        destination = HERE / "tasks" / instance
        destination.mkdir(parents=True, exist_ok=True)
        snapshot = ROOT / config["snapshot"]
        base = snapshot / "public" / instance / "base"
        original_patch = grading[instance]["test_patch"]
        assert (snapshot / "private" / instance / "test.patch").read_bytes() == original_patch.encode()
        (destination / "original_test.patch").write_text(original_patch)
        files = sorted(set(patch_files(original_patch)) | set(config["append"]))
        with tempfile.TemporaryDirectory(prefix="rh2-dvc-material-") as temporary:
            temporary = Path(temporary)
            work, clean = temporary / "work", temporary / "clean"
            work.mkdir(); clean.mkdir()
            test_files = []
            for name in files:
                source = base / name
                if source.is_file():
                    for target in (work / name, clean / name, destination / "public_tests" / name):
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, target)
                test_files.append({"path": name, "base_exists": source.is_file(),
                                   "base_sha256": digest(source.read_bytes()) if source.is_file() else None})
            apply(work, destination / "original_test.patch")
            if task == "9395":
                v4 = ROOT / "rh2/experiments/category3_cloud_20260929/dvc9395/revised_test_v4.patch"
                # v4 是相对 base 的完整补丁，不能叠在 original_test.patch 后重复应用。
                for name in files:
                    shutil.copyfile(base / name, work / name)
                apply(work, v4)
            bindings = canonicalize_ids(task, work)
            for name, template in config["append"].items():
                target = work / name
                target.write_text(target.read_text().rstrip() + (HERE / "templates" / template).read_text() + "\n")
            syntax = []
            for name in files:
                source = (work / name).read_text()
                ast.parse(source, filename=name)
                syntax.append(name)
            effective = full_patch(base, work, files)
            patch = destination / "effective_test.patch"
            patch.write_text(effective)
            apply(clean, patch)
            assert all((clean / name).read_bytes() == (work / name).read_bytes() for name in files)

        originals = {"fail_to_pass": grading[instance]["fail_to_pass"], "pass_to_pass": grading[instance]["pass_to_pass"]}
        effective_refs = {}
        for group, additions in [("fail_to_pass", config["f2p"]), ("pass_to_pass", config["p2p"])]:
            effective_refs[group] = [target for old in originals[group] for target in bindings.get(old, [old])] + additions
            assert len(effective_refs[group]) == len(set(effective_refs[group]))
        assert not set(effective_refs["fail_to_pass"]) & set(effective_refs["pass_to_pass"])
        candidates = destination / "candidates"
        candidates.mkdir(exist_ok=True)
        (candidates / "noop.patch").write_text("")
        shutil.copyfile(snapshot / "private" / instance / "gold.patch", candidates / "gold.patch")
        if task == "4166":
            name = "dvc/ignore.py"
            source = base / name
            old = "            path_spec_lines = fobj.readlines()"
            text = source.read_text()
            assert text.count(old) == 1
            new = old + "\n            path_spec_lines = [\n                line.rstrip('\\r\\n').removesuffix('/') + '\\n'\n                if not line.startswith('!') else line\n                for line in path_spec_lines\n            ]"
            candidate_patch(source, text.replace(old, new), candidates / "strip_positive_trailing_slash.patch", name)
        if task == "5839":
            text = (candidates / "gold.patch").read_text()
            assert text.count("+                    self.args.precision,") == 1
            (candidates / "hardcoded_precision8.patch").write_text(text.replace("+                    self.args.precision,", "+                    8,"))
        if task == "6954":
            name = "dvc/utils/serialize/_py.py"
            source = base / name
            old = "    else:\n        raise ValueError\n    return result"
            text = source.read_text()
            assert text.count(old) == 1
            new = ("    elif isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):\n"
                   "        number = value.operand\n"
                   "        if isinstance(number, ast.Num) and type(number.n) is int:\n"
                   "            result = -number.n\n"
                   "        else:\n            raise ValueError\n"
                   "    else:\n        raise ValueError\n    return result")
            candidate_patch(source, text.replace(old, new), candidates / "negative_int_only.patch", name)
        if task == "9395":
            cloud = ROOT / "rh2/experiments/category3_cloud_20260929/dvc9395"
            for name, source in [("c3_frozenfix", cloud / "reviewer_cands/c3_frozenfix.patch"),
                                 ("c3_missing_only", cloud / "c3_missing_only.patch"),
                                 ("up351_port", cloud / "reviewer_cands/up351_port.patch"),
                                 ("w_swallow3", cloud / "reviewer_cands/w_swallow3.patch")]:
                if not source.is_file():
                    source = cloud / (name + ".patch")
                shutil.copyfile(source, candidates / (name + ".patch"))

        matrix = [{"candidate": name, "patch": f"candidates/{name}.patch",
                   "patch_sha256": digest((candidates / (name + ".patch")).read_bytes()),
                   "expected_effective_reward": expected, "observed_effective_reward": None,
                   "status": "not_run"} for name, expected in config["candidates"]]
        package = packages[instance]
        revision = {
            "format": "swe_dvc_material_draft.v1", "as_of": "2026-10-03",
            "status": "draft_not_registered_not_cpu_validated", "instance_id": instance,
            "owner_thread_id": "01a0fd62-ca8f-7173-a3fd-0e3795c646bd",
            "revision_id": config.get("revision_id", "dvc" + task + "-behavior-v1-draft"),
            "repo": "iterative/dvc", "base_commit": package["base_commit"],
            "parent_grading_digest": package["grading_bundle_digest"],
            "public_bundle_digest": package["public_bundle_digest"],
            "image_manifest_digest": package["image_manifest_digest"],
            "original_test_patch": "original_test.patch",
            "original_test_patch_sha256": digest(original_patch.encode()),
            "effective_test_patch": "effective_test.patch", "effective_test_patch_sha256": digest(effective.encode()),
            "test_files": test_files, "original_references": originals,
            "effective_references": effective_refs, "reference_bindings": bindings,
            "added_fail_to_pass": config["f2p"], "added_pass_to_pass": config["p2p"],
            "selector": {"type": "pytest_files", "files": files, "collection_verified": False},
            "public_statement_changed": False, "environment_requirements": config["pins"],
            "historical_install_recipe": f"{EXECUTION}/env_recipe_repair_20260919/{config['recipe']}/recipes/{instance}.json",
            "acceptance_matrix": matrix,
            "not_done": ["pytest实际collection", "新宿主环境身份", "正式评分与逐键核对", "非作者核查", "正式登记发布", "模型探针"],
        }
        dump(destination / "revision.json", revision)
        summary[instance] = {"patch_roundtrip": True, "ast_parse": syntax,
                             "effective_test_patch_sha256": revision["effective_test_patch_sha256"],
                             "original_reference_counts": {k: len(v) for k, v in originals.items()},
                             "effective_reference_counts": {k: len(v) for k, v in effective_refs.items()}}
    dump(HERE / "offline_checks.json", {"as_of": "2026-10-03", "scope": "文本/补丁检查，不是pytest或正式评分", "tasks": summary})
    print(json.dumps({"prepared_tasks": list(summary), "runtime_validated": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
