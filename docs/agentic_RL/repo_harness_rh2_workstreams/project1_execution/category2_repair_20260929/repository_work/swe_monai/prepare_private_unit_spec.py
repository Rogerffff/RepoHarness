"""从本包固定输入生成私有语义检查；不运行 Docker，不生成正式奖励。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_files_command(files):
    return "python - <<'CHECK_SOURCE'\nimport pathlib,hashlib,json\nexpected=" + repr(files) + "\nfor name,expected_sha in expected.items():\n actual=hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()\n assert actual==expected_sha,(name,actual,expected_sha)\nprint('SOURCE_SHA256',json.dumps(expected,sort_keys=True))\nCHECK_SOURCE"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--image-receipt", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--task", choices=["2446", "3715", "6975"], required=True)
    a = p.parse_args()
    manifest = json.loads((a.inputs / "input_manifest.json").read_text())
    for rel, binding in manifest["files"].items():
        file = (a.inputs / rel).resolve()
        assert file.is_relative_to(a.inputs.resolve()) and file.is_file(), rel
        assert file.stat().st_size == binding["bytes"] and sha(file) == binding["sha256"], rel
    receipt = json.loads(a.image_receipt.read_text())
    assert receipt["task"] == a.task and receipt["status"] == "image_prepared_not_task_accepted"
    assert receipt["cleanup"]["remaining"] == [] and receipt["cleanup"]["query_rc"] == 0
    config = manifest["tasks"][a.task]
    assert receipt["source_identity"]["head"] == config["base_commit"]
    base = dict(config["source_sha256"])
    if a.task in ("2446", "3715"):
        folder = a.inputs / "materials" / a.task
        request = json.loads((folder / "revision_request.json").read_text())
        controls = {
            name: {"file": folder / "controls" / Path(binding["path"]).name,
                   "source": binding["source_file"],
                   "after": binding["applied_source_sha256"].removeprefix("sha256:")}
            for name, binding in request["controls"].items()
        }
        tests = [x["path"] for x in request["test_files"]]
        after_tests = {tests[0]: sha(folder / "effective_test.py")}
        node = ("TestSmartCacheDataset::test_shuffle_ndarray_list_and_cache_cpu" if a.task == "2446"
                else "TestPrepareBatchDefault::test_evaluator_string_modes_forward_and_restore_cpu")
        new_node = tests[0] + "::" + node
    else:
        folder = a.inputs / "inherited6975"
        target = "monai/transforms/transform.py"
        controls = {"noop": {"file": folder / "controls/noop.patch", "source": target, "after": base[target]}}
        for name, old, filename in [("gold", "gold", "gold.patch"),
                                    ("discard_dict_output", "degenerate", "degenerate_discard_dict_output.patch")]:
            binding = json.loads((folder / "history/formal_setup1800" / ("grade_" + old) / "frozen_source_checked.json").read_text())
            assert binding["path"] == target and binding["patch"] == filename
            controls[name] = {"file": folder / "controls" / filename, "source": target, "after": binding["sha256"]}
        tests = ["tests/test_compose.py", "tests/test_dataset.py"]
        after_tests = {name: sha(folder / "inspection" / ("effective_" + Path(name).name)) for name in tests}
        new_node = "tests/test_dataset.py::TestDataset::test_dataset_lazy_dict_returns_transformed_pixels_cpu"
    test_patch = folder / "effective_test.patch"
    variants, files = {}, {"effective_test.patch": str(test_patch.resolve())}
    for name, binding in controls.items():
        steps = ["git config --global --add safe.directory /testbed", check_files_command(base)]
        if name != "noop":
            filename = "control-" + name + ".patch"
            files[filename] = str(binding["file"].resolve())
            patch = shlex.quote("/in/" + filename)
            steps.append("git apply --check " + patch + " && git apply " + patch)
        steps.extend([check_files_command({binding["source"]: binding["after"]}),
                      "git apply --check /in/effective_test.patch && git apply /in/effective_test.patch",
                      check_files_command(after_tests),
                      "python - <<'CHECK_IMPORT'\nimport sys,json,pathlib,monai,torch\nprint('PRIVATE_IMPORT',json.dumps({'python':sys.executable,'monai':monai.__file__,'cuda':torch.cuda.is_available()}))\nassert str(pathlib.Path(monai.__file__).resolve()).startswith('/testbed/monai/')\nassert sys.executable=='/opt/miniconda3/envs/testbed/bin/python' and not torch.cuda.is_available()\nCHECK_IMPORT"])
        variants[name] = steps
    expected = {name: {"module_rc": 0 if name in ("gold", "alternative_list_copy", "alternative_local_mode") else 1,
                       "new_node": "fail" if name in ("array_no_shuffle", "discard_dict_output", "eval_only", "always_eval")
                                   or (name == "noop" and a.task == "3715") else "pass"}
                for name in controls}
    spec = {"schema": "monai_private_unit_diagnosis.v1", "scope": "private root only; not formal grading or actor",
            "task": a.task, "image": receipt["actual_image_id"], "cpus": 2, "memory": "4g",
            "python_prefix": "/opt/miniconda3/envs/testbed", "variants": variants, "files": files,
            "commands": [{"id": "module_test", "cmd": "python -m pytest -rA --color=no " + " ".join(tests), "timeout_s": 1800}],
            "new_node": new_node, "expected_not_executed": expected,
            "input_manifest_sha256": sha(a.inputs / "input_manifest.json"),
            "image_receipt_sha256": sha(a.image_receipt)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x") as f:
        f.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"spec": str(a.out), "sha256": sha(a.out), "controls": list(controls), "executed": False}))


if __name__ == "__main__":
    main()
