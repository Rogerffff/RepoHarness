from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

from repo_harness.pre_verl_evaluation import _pre_verl_environment_for_repo


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "pre_verl" / "run_agentloop_evaluation.py"


def _load_scheduler_module():
    spec = importlib.util.spec_from_file_location("pre_verl_agentloop_scheduler_env_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repo_specific_environment_freezes_pvlib_version_and_pyvista_platform() -> None:
    pvlib = _pre_verl_environment_for_repo("pvlib/pvlib-python", "0.9")
    pyvista = _pre_verl_environment_for_repo("pyvista/pyvista", "0.39")

    assert "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PVLIB=0.9.0" in pvlib["setup_shell"]
    assert "pytest-mock" in pvlib["setup_shell"]
    assert pvlib["environment_id"] == "pre_verl_pvlib_0.9_python39_v1"
    assert pyvista["requested_container_platform"] == "linux/amd64"
    assert "libgl1" in pyvista["setup_shell"]
    assert "libgl1" in pyvista["runtime_shell_prefix"]
    assert "'meshio<5.4.0'" in pyvista["setup_shell"]
    assert "'tqdm<4.66.0'" in pyvista["setup_shell"]


def test_agentloop_scheduler_propagates_repo_requested_container_platform(tmp_path: Path) -> None:
    script = _load_scheduler_module()
    task = script.SelectedTask(
        task_id="pre_verl_dev_018_pyvista__pyvista_4315",
        source_record_path=tmp_path / "source_record.json",
        source_record={"repo": "pyvista/pyvista", "version": "0.39"},
        adapter_visible_input={},
        evaluator_only_evidence={},
        materialization_entry={},
        verifier_plan={},
    )
    args = SimpleNamespace(
        run_id_prefix="pre_verl_agentloop",
        provider="deepseek",
        model_id="deepseek-v4-pro",
        temperature=0.0,
        max_output_tokens=4096,
        allow_local_secret_file=True,
        deepseek_thinking="disabled",
        scaffold_id="patch_focused_react",
        execution_mode="docker",
        permission_mode="auto",
        test_feedback_policy="disabled",
        max_turns=48,
        max_tool_calls=120,
        max_test_runs=0,
        task_timeout_sec=1200,
        command_timeout_sec=90,
        seed=42,
        max_context_tokens=180000,
        tool_result_aggregate_budget_chars=40000,
        compact_threshold_ratio=0.85,
    )

    config_path = tmp_path / "run_config.yaml"
    script._write_run_config(
        task=task,
        config_path=config_path,
        output_dir=tmp_path,
        args=args,
    )

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["docker_backend"]["build_base_image"] == "python:3.9"
    assert payload["runtime"]["docker_backend"]["requested_container_platform"] == "linux/amd64"


def test_pyvista_task_definition_verifier_command_inherits_runtime_shell_prefix(tmp_path: Path) -> None:
    script = _load_scheduler_module()
    task_id = "pre_verl_dev_018_pyvista__pyvista_4315"
    materialization_entry_path = tmp_path / "materialized" / "entries" / task_id / "entry.json"
    materialization_entry_path.parent.mkdir(parents=True)
    materialization_entry_path.write_text("{}", encoding="utf-8")
    task = script.SelectedTask(
        task_id=task_id,
        source_record_path=tmp_path / "source_record.json",
        source_record={
            "repo": "pyvista/pyvista",
            "version": "0.39",
            "source_instance_id": task_id,
            "swebench_dev_materialization_entry_ref": {"path": materialization_entry_path.as_posix()},
            "source_tree_sha256": "0" * 64,
        },
        adapter_visible_input={"problem_statement": "PyVista needs OpenGL runtime libraries."},
        evaluator_only_evidence={"PASS_TO_PASS": ["tests/test_smoke.py::test_import"]},
        materialization_entry={
            "test_patch_apply_result_ref": {"path": (tmp_path / "apply.json").as_posix()},
            "test_patch_apply_status": "clean",
        },
        verifier_plan={
            "fail_to_pass_selectors": ["tests/test_smoke.py::test_import"],
            "test_patch_ref": {"path": (tmp_path / "hidden.patch").as_posix(), "sha256": "1" * 64},
        },
    )

    task_path, _ = script._write_task_definition(
        task=task,
        task_set_manifest_path=tmp_path / "manifest.json",
        tasks_dir=tmp_path / "tasks",
        selectors_dir=tmp_path / "selectors",
    )

    payload = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    verifier_command = payload["metadata"]["pre_verl_verifier_command"]
    setup_shell = payload["metadata"]["pre_verl_setup_shell"]
    assert "'meshio<5.4.0'" in setup_shell
    assert "'tqdm<4.66.0'" in setup_shell
    assert "apt-get update" in verifier_command
    assert "libgl1" in verifier_command
    assert ". .pre_verl_venv/bin/activate" in verifier_command
    assert "python -m pytest -q" in verifier_command
