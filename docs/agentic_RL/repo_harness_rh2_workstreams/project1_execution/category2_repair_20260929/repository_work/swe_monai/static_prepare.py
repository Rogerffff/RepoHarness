"""MONAI 三题材料准备；仅标准库、隔离补丁检查，不运行项目或远端任务。"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2").is_dir())
OUT = Path(__file__).resolve().parent
EXECUTION = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution"
OLD_PUBLIC = ROOT / "runs/swegym_quality_expansion_20260925/public"
OLD_PRIVATE = ROOT / "runs/swegym_quality_expansion_20260925/private"
INGEST = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest"
OWNER_ID = "01a0fd62-fb0a-7d02-877a-f9ef7ef32399"

TEST_2446 = '''    def test_shuffle_ndarray_list_and_cache_cpu(self):
        for shuffle in (True, False):
            with self.subTest(shuffle=shuffle):
                data = [np.array([i]) for i in range(5)]
                expected = np.stack(data).copy()
                if shuffle:
                    np.random.RandomState(0).shuffle(expected)
                dataset = SmartCacheDataset(
                    data=data,
                    transform=None,
                    cache_rate=0.5,
                    replace_rate=0.4,
                    shuffle=shuffle,
                    seed=0,
                    num_init_workers=1,
                    num_replace_workers=1,
                    progress=False,
                )
                try:
                    np.testing.assert_array_equal(np.stack(dataset.data), expected)
                    self.assertEqual(len(dataset), 2)
                    actual_cache = np.stack([dataset[i] for i in range(len(dataset))])
                    np.testing.assert_array_equal(actual_cache, expected[:2])
                finally:
                    dataset.shutdown()

'''

TEST_3715 = '''    def test_evaluator_string_modes_forward_and_restore_cpu(self):
        from monai.utils import ForwardMode

        class RecordingNet(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.observed = []

            def forward(self, image):
                self.observed.append((self.training, torch.is_grad_enabled()))
                return image * 2

        modes = (
            ("train", True),
            ("eval", False),
            (ForwardMode.TRAIN, True),
            (ForwardMode.EVAL, False),
        )
        for mode, expected_training in modes:
            for initial_training in (False, True):
                for initial_grad in (False, True):
                    with self.subTest(mode=repr(mode), training=initial_training, grad=initial_grad):
                        network = RecordingNet()
                        network.train(initial_training)
                        image = torch.tensor([[1.0, 2.0]], device="cpu", requires_grad=True)
                        batch = {"image": image, "label": torch.zeros_like(image)}
                        with torch.set_grad_enabled(initial_grad):
                            evaluator = SupervisedEvaluator(
                                device=torch.device("cpu"),
                                val_data_loader=[batch],
                                epoch_length=1,
                                network=network,
                                prepare_batch=PrepareBatchDefault(),
                                decollate=False,
                                mode=mode,
                            )
                            evaluator.run()
                            self.assertEqual(network.observed, [(expected_training, expected_training)])
                            self.assertEqual(network.training, initial_training)
                            self.assertEqual(torch.is_grad_enabled(), initial_grad)
                            prediction = evaluator.state.output["pred"]
                            assert_allclose(prediction.detach(), image.detach() * 2)
                            self.assertEqual(prediction.requires_grad, expected_training)
                            if expected_training:
                                with torch.enable_grad():
                                    gradient = torch.autograd.grad(prediction.sum(), image)[0]
                                assert_allclose(gradient.detach(), torch.full_like(image, 2.0))
                            self.assertEqual(torch.is_grad_enabled(), initial_grad)

'''


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def canonical(data: object) -> str:
    return sha(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": relative(path), "sha256": sha(data), "bytes": len(data)}


def select_original(instance_id: str, filename: str) -> tuple[dict, dict]:
    path = INGEST / filename
    matches = [(i, json.loads(line)) for i, line in enumerate(path.read_text().splitlines(), 1)
               if line.strip() and json.loads(line).get("instance_id") == instance_id]
    assert len(matches) == 1, (instance_id, filename)
    line, data = matches[0]
    return data, {"path": relative(path), "line": line, "canonical_json_digest": canonical(data)}


def run_git(worktree: Path, patch: Path, commands: list[dict]) -> None:
    for args in (("git", "apply", "--check", str(patch)), ("git", "apply", str(patch))):
        result = subprocess.run(args, cwd=worktree, text=True, capture_output=True, check=False)
        commands.append({"argv": [*args[:-1], relative(patch)], "rc": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
        assert result.returncode == 0, commands[-1]


def make_diff(path: str, before: str, after: str) -> str:
    if before == after:
        return ""
    return f"diff --git a/{path} b/{path}\n" + "".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile=f"a/{path}", tofile=f"b/{path}"))


def preserve_ast(original: str, effective: str, class_name: str, method_name: str) -> None:
    tree = ast.parse(effective)
    matches = [c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == class_name]
    assert len(matches) == 1
    members = [n for n in matches[0].body if isinstance(n, ast.FunctionDef) and n.name == method_name]
    assert len(members) == 1 and not members[0].decorator_list
    matches[0].body.remove(members[0])
    assert ast.dump(tree, include_attributes=False) == ast.dump(ast.parse(original), include_attributes=False)


def insert_method(original: str, class_name: str, body: str) -> str:
    marker = f"class {class_name}(unittest.TestCase):\n"
    assert original.count(marker) == 1
    return original.replace(marker, marker + body, 1)


def prepare_task(number: str, test_file: str, class_name: str, method_name: str, body: str,
                 operation: str, revision_id: str, controls: dict[str, bytes], matrix: list[dict]) -> dict:
    instance_id = f"Project-MONAI__MONAI-{number}"
    out = OUT / "materials" / number
    out.mkdir(parents=True, exist_ok=True)
    public, public_binding = select_original(instance_id, "public_bundles_v0.jsonl")
    grading, grading_binding = select_original(instance_id, "grading_bundles_v2_v0.jsonl")
    _, environment_binding = select_original(instance_id, "environment_packages_v0.jsonl")
    private = OLD_PRIVATE / instance_id
    assert json.loads((private / "grading.json").read_text()) == grading
    assert json.loads((OLD_PUBLIC / instance_id / "public_bundle.json").read_text()) == public
    assert (private / "test.patch").read_bytes() == grading["test_patch"].encode()

    source_file = "monai/data/dataset.py" if number == "2446" else "monai/engines/evaluator.py"
    base_root = OLD_PUBLIC / instance_id / "base"
    base_test = (base_root / test_file).read_text()
    base_source = (base_root / source_file).read_bytes()
    base_copy = out / "base" / test_file
    base_copy.parent.mkdir(parents=True, exist_ok=True)
    base_copy.write_bytes((base_root / test_file).read_bytes())
    original_patch = out / "original_test.patch"
    original_patch.write_bytes(grading["test_patch"].encode())
    commands: list[dict] = []
    with tempfile.TemporaryDirectory(prefix=f"monai{number}-static-") as tmp:
        worktree = Path(tmp)
        target = worktree / test_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base_copy.read_bytes())
        run_git(worktree, original_patch, commands)
        original = target.read_text()
        effective = insert_method(original, class_name, body)
        assert effective.replace(body, "", 1) == original
        preserve_ast(original, effective, class_name, method_name)
        compile(effective, test_file, "exec")
        extra = out / "extra_tests.patch"
        extra.write_text(make_diff(test_file, original, effective))
        run_git(worktree, extra, commands)
        assert target.read_text() == effective
        effective_patch = out / "effective_test.patch"
        effective_patch.write_text(make_diff(test_file, base_test, effective))
        target.write_text(base_test)
        run_git(worktree, effective_patch, commands)
        assert target.read_text() == effective
        (out / "effective_test.py").write_text(effective)

        control_records = {}
        for name, content in controls.items():
            patch = out / "controls" / f"{name}.patch"
            patch.parent.mkdir(parents=True, exist_ok=True)
            patch.write_bytes(content)
            source = worktree / source_file
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(base_source)
            if content:
                run_git(worktree, patch, commands)
            compile(source.read_text(), source_file, "exec")
            control_records[name] = {**record(patch), "source_file": source_file,
                                     "applied_source_sha256": sha(source.read_bytes()),
                                     "execution_status": "not_executed"}

    node = f"{test_file}::{class_name}::{method_name}"
    partition = "P2P" if operation.endswith("p2p") else "F2P"
    added_f2p = [node] if partition == "F2P" else []
    added_p2p = [node] if partition == "P2P" else []
    refs = {"original_fail_to_pass": grading["fail_to_pass"], "original_pass_to_pass": grading["pass_to_pass"],
            "added_fail_to_pass": added_f2p, "added_pass_to_pass": added_p2p,
            "effective_fail_to_pass": grading["fail_to_pass"] + added_f2p,
            "effective_pass_to_pass": grading["pass_to_pass"] + added_p2p,
            "collection_and_runtime_status": "not_executed"}
    assert not set(refs["effective_fail_to_pass"]) & set(refs["effective_pass_to_pass"])
    assert len(set(refs["effective_fail_to_pass"] + refs["effective_pass_to_pass"])) == (
        len(refs["effective_fail_to_pass"]) + len(refs["effective_pass_to_pass"]))
    write_json(out / "references_candidate.json", refs)
    proposal = {
        "schema": "monai_task_material_proposal.v1", "as_of": "2026-10-03",
        "instance_id": instance_id, "owner_thread_id": OWNER_ID,
        "status": "static_materials_prepared_not_registered_not_cpu_accepted",
        "revision_id_candidate": revision_id, "operation_candidate": operation,
        "repo": public["repo"], "base_commit": public["base_commit"],
        "source_bindings": {"public": public_binding, "grading": grading_binding,
                            "environment": environment_binding},
        "source_image_manifest_digest": public["image_manifest_digest"],
        "public_material_changed": False,
        "test_files": [{"path": test_file, "base_sha256": sha(base_copy.read_bytes()),
                        "base_asset": relative(base_copy)}],
        "original_test_patch": record(original_patch), "effective_test_patch": record(effective_patch),
        "extra_tests_patch": record(extra), "references": record(out / "references_candidate.json"),
        "counts": {"original_f2p": len(grading["fail_to_pass"]), "original_p2p": len(grading["pass_to_pass"]),
                   "effective_f2p": len(refs["effective_fail_to_pass"]),
                   "effective_p2p": len(refs["effective_pass_to_pass"])},
        "controls": control_records, "formal_matrix_expected_not_executed": matrix,
        "source_assets": [record(base_root / test_file), record(base_root / source_file),
                          record(OLD_PUBLIC / instance_id / "user_prompt.txt"),
                          record(OLD_PUBLIC / instance_id / "base_identity.json")],
        "shared_consumer_gap": "当前正式 allowlist 未登记本题；需唯一维护者接入、冻结 producer/registry/code 后正式验收",
        "production_changed": False, "new_test_executed": False,
    }
    if number == "3715":
        proposal["source_assets"].extend(record(base_root / f) for f in (
            "tests/utils.py", "monai/networks/utils.py", "monai/engines/workflow.py", "monai/utils/enums.py"))
        proposal["test_helper_compatibility"] = (
            "该版本 tests.utils.assert_allclose 直接调用 cpu().numpy()；只在数值比较处 detach，"
            "梯度启用/预测 requires_grad/实际 autograd 验收仍使用原 graph")
    write_json(out / "revision_request.json", proposal)
    check = {"instance_id": instance_id, "git_apply_commands": commands,
             "all_apply_commands_rc0": all(c["rc"] == 0 for c in commands),
             "base_plus_original_plus_extra_equals_effective": True,
             "original_test_bytes_and_ast_preserved_after_removing_only_new_method": True,
             "new_test_compile_only": True, "new_node": node, "partition_candidate": partition,
             "production_changed": False, "project_imported_or_executed": False}
    write_json(OUT / "checks" / f"monai{number}_static_20261003.json", check)
    return proposal


def controls_2446() -> dict[str, bytes]:
    iid = "Project-MONAI__MONAI-2446"
    base = (OLD_PUBLIC / iid / "base/monai/data/dataset.py").read_text()
    alternative = base.replace("            self.randomize(data)\n",
                               "            data = list(data)\n            self.randomize(data)\n", 1)
    assert alternative != base
    return {
        "noop": b"", "gold": (OLD_PRIVATE / iid / "gold.patch").read_bytes(),
        "array_no_shuffle": (ROOT / "runs/swegym_cpu_preprobe_20260929/task_inputs" / iid /
                             "private/degenerate_array_no_shuffle.patch").read_bytes(),
        "alternative_list_copy": make_diff("monai/data/dataset.py", base, alternative).encode(),
    }


def controls_3715() -> dict[str, bytes]:
    iid = "Project-MONAI__MONAI-3715"
    path = "monai/engines/evaluator.py"
    base = (OLD_PUBLIC / iid / "base" / path).read_text()
    marker = "        self.mode = look_up_option(mode, ForwardMode)\n"
    assert base.count(marker) == 1
    eval_only = base.replace(marker, "        self.mode = look_up_option(mode, ForwardMode)\n"
                            "        if mode == \"eval\":\n            mode = ForwardMode.EVAL\n", 1)
    start = base.index(marker)
    end = base.index("\n    def run(", start)
    always_eval = base[:start] + "        look_up_option(mode, ForwardMode)\n        self.mode = eval_mode\n" + base[end:]
    alternative = base.replace(marker, "        forward_mode = look_up_option(mode, ForwardMode)\n", 1)
    alternative = alternative.replace("        if mode == ForwardMode.EVAL:\n", "        if forward_mode == ForwardMode.EVAL:\n", 1)
    alternative = alternative.replace("        elif mode == ForwardMode.TRAIN:\n", "        elif forward_mode == ForwardMode.TRAIN:\n", 1)
    return {"noop": b"", "gold": (OLD_PRIVATE / iid / "gold.patch").read_bytes(),
            "eval_only": make_diff(path, base, eval_only).encode(),
            "always_eval": make_diff(path, base, always_eval).encode(),
            "alternative_local_mode": make_diff(path, base, alternative).encode()}


def audit_existing_6975() -> dict:
    manifest_path = EXECUTION / "category2_repair_20260929/swe_materials/monai6975_next/materials_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assets = {**manifest["frozen_source_assets"], **manifest["generated_assets"]}
    mismatches = []
    for key, expected in assets.items():
        path = ROOT / expected["path"]
        if not path.is_file() or path.is_symlink():
            mismatches.append({"asset": key, "problem": "missing_or_not_regular"})
            continue
        data = path.read_bytes()
        expected_sha = expected["sha256"].removeprefix("sha256:")
        if len(data) != expected["bytes"] or hashlib.sha256(data).hexdigest() != expected_sha:
            mismatches.append({"asset": key, "problem": "bytes_or_sha_mismatch"})
    assert not mismatches, mismatches
    pack = ROOT / "runs/category2_repair_20260929/swe_materials/monai6975_next"
    commands = []
    with tempfile.TemporaryDirectory(prefix="monai6975-inherited-static-") as tmp:
        worktree = Path(tmp)
        originals = {}
        for test_file in manifest["proposal"]["test_files"]:
            target = worktree / test_file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((pack / "source/base" / test_file).read_bytes())
        run_git(worktree, pack / "original_test.patch", commands)
        originals = {f: (worktree / f).read_text() for f in manifest["proposal"]["test_files"]}
        run_git(worktree, pack / "extra_tests.patch", commands)
        expected = {f: (worktree / f).read_bytes() for f in manifest["proposal"]["test_files"]}
        for test_file in manifest["proposal"]["test_files"]:
            (worktree / test_file).write_bytes((pack / "source/base" / test_file).read_bytes())
        run_git(worktree, pack / "effective_test.patch", commands)
        for test_file in manifest["proposal"]["test_files"]:
            assert (worktree / test_file).read_bytes() == expected[test_file]
            compile((worktree / test_file).read_text(), test_file, "exec")
        assert expected["tests/test_compose.py"] == originals["tests/test_compose.py"].encode()
        preserve_ast(originals["tests/test_dataset.py"], expected["tests/test_dataset.py"].decode(),
                     "TestDataset", "test_dataset_lazy_dict_returns_transformed_pixels_cpu")
    check = {"schema": "monai6975_inherited_static_recheck.v1", "as_of": "2026-10-03",
             "reviewer_thread_id": OWNER_ID, "manifest": record(manifest_path),
             "assets_verified": len(assets), "mismatches": mismatches,
             "git_apply_commands": commands, "effective_equals_original_plus_extra_both_files": True,
             "original_compose_bytes_preserved": True, "dataset_original_ast_preserved": True,
             "new_node_compile_only": True, "new_node_executed": False,
             "scope": "接续非本线程作者的静态包核对；不替代运行后独立验收"}
    write_json(OUT / "checks/monai6975_existing_pack_20261003.json", check)
    proposal = {"schema": "monai_task_material_proposal.v1", "as_of": "2026-10-03",
                "instance_id": manifest["instance_id"], "owner_thread_id": OWNER_ID,
                "status": "inherited_static_materials_rechecked_not_registered_not_cpu_accepted",
                "revision_id_candidate": manifest["proposal"]["revision_id_candidate"],
                "operation_candidate": manifest["proposal"]["operation_candidate"],
                "existing_material_manifest": record(manifest_path),
                "existing_pack_root": relative(pack), "static_recheck": relative(OUT / "checks/monai6975_existing_pack_20261003.json"),
                "known_remaining": ["两文件受信消费登记/生产冻结", "新增64参考真实0/1/0",
                                    "实际actor原NIfTI路径和公开RandAffine例子核验", "运行后独立核查"],
                "production_changed": False, "new_test_executed": False}
    write_json(OUT / "materials/6975/revision_request.json", proposal)
    return proposal


def main() -> None:
    p2446 = prepare_task("2446", "tests/test_smartcachedataset.py", "TestSmartCacheDataset",
                         "test_shuffle_ndarray_list_and_cache_cpu", TEST_2446,
                         "replace_test_patch_append_p2p", "monai2446-ndarray-shuffle-cache-cpu-v1", controls_2446(),
                         [{"control": name, "expected_reward": reward, "new_node_expected": node}
                          for name, reward, node in (("noop", 0, "pass"), ("gold", 1, "pass"),
                                                    ("array_no_shuffle", 0, "fail"), ("alternative_list_copy", 1, "pass"))])
    p3715 = prepare_task("3715", "tests/test_prepare_batch_default.py", "TestPrepareBatchDefault",
                         "test_evaluator_string_modes_forward_and_restore_cpu", TEST_3715,
                         "replace_test_patch_append_f2p", "monai3715-string-modes-forward-cpu-v1", controls_3715(),
                         [{"control": name, "expected_reward": reward, "new_node_expected": node}
                          for name, reward, node in (("noop", 0, "fail"), ("gold", 1, "pass"),
                                                    ("eval_only", 0, "fail"), ("always_eval", 0, "fail"),
                                                    ("alternative_local_mode", 1, "pass"))])
    p6975 = audit_existing_6975()
    summary = {"schema": "monai_repository_preparation.v1", "as_of": "2026-10-03",
               "package_id": "swe_monai", "owner_thread_id": OWNER_ID,
               "owner_thread_name": "SWE | MONAI 题目修订",
               "status": "static_preparation_complete_cpu_and_shared_publication_pending",
               "task_ids": [p["instance_id"] for p in (p2446, p3715, p6975)],
               "proposals": [record(OUT / "materials" / n / "revision_request.json") for n in ("2446", "3715", "6975")],
               "checks": [record(OUT / "checks" / filename) for filename in (
                   "monai2446_static_20261003.json", "monai3715_static_20261003.json", "monai6975_existing_pack_20261003.json")],
               "ready_for_probe": False, "cpu_experiments_started": False,
               "shared_code_modified": False, "global_registry_modified": False}
    review_receipt = OUT / "reviews/non_author_review_binding_20261003.json"
    if review_receipt.exists():
        receipt = json.loads(review_receipt.read_text())
        unchanged = all(
            sha((ROOT / item["path"]).read_bytes()) == item["sha256"]
            for item in [receipt["report"], *receipt["reviewed_effective_patches"].values()]
        )
        summary["non_author_static_review"] = {
            "binding_receipt": record(review_receipt),
            "current_report_and_patches_match_review": unchanged,
            "status": "no_blocker_in_reviewed_static_scope" if unchanged else "changed_since_review_needs_delta_check",
            "runtime_acceptance_proven": False,
        }
    write_json(OUT / "preparation.json", summary)
    print(json.dumps({"tasks": summary["task_ids"], "status": summary["status"],
                      "new_reference_counts": {"2446": p2446["counts"], "3715": p3715["counts"],
                                               "6975": {"f2p": 4, "p2p": 60}},
                      "inherited_6975_assets_verified": 117}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
