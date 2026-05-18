"""只读记录 reference/verl fully async 接口形状。"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel


class FullyAsyncInterfaceInventory(StrictBaseModel):
    schema_version: str = "repo_harness_verl_fully_async_interface_inventory_v0"
    reference_verl_root: str
    reference_verl_commit: str | None = None
    modules: dict[str, str]
    classes: dict[str, str]
    rollout_sample_fields: list[str]
    method_signatures: dict[str, str]
    config_paths: dict[str, str]
    fully_async_task_runner_present: bool
    heavy_import_required: bool = False
    diagnostics: list[str] = Field(default_factory=list)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_reference_verl_root() -> Path:
    return _repo_root() / "reference" / "verl"


def _relative_module_path(path: Path, *, reference_verl_root: Path) -> str:
    return str(path.relative_to(reference_verl_root))


def _read_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef | None:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _dataclass_field_names(class_node: ast.ClassDef | None) -> list[str]:
    if class_node is None:
        return []
    fields: list[str] = []
    for node in class_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fields.append(node.target.id)
    return fields


def _method_signature(class_node: ast.ClassDef | None, method_name: str) -> str | None:
    if class_node is None:
        return None
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name:
            args = [arg.arg for arg in node.args.args]
            if node.args.vararg is not None:
                args.append("*" + node.args.vararg.arg)
            if node.args.kwarg is not None:
                args.append("**" + node.args.kwarg.arg)
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            return f"{prefix}{method_name}({', '.join(args)})"
    return None


def _reference_verl_commit(reference_verl_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(reference_verl_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return completed.stdout.strip() or None


def build_fully_async_interface_inventory(
    reference_verl_root: str | Path | None = None,
) -> FullyAsyncInterfaceInventory:
    """通过源码读取生成 fully async interface inventory，不 import torch / ray / verl。"""

    root = Path(reference_verl_root) if reference_verl_root is not None else _default_reference_verl_root()
    root = root.resolve()
    diagnostics: list[str] = []
    files = {
        "fully_async_main": root / "verl" / "experimental" / "fully_async_policy" / "fully_async_main.py",
        "fully_async_rollouter": root / "verl" / "experimental" / "fully_async_policy" / "fully_async_rollouter.py",
        "message_queue": root / "verl" / "experimental" / "fully_async_policy" / "message_queue.py",
        "fully_async_trainer": root / "verl" / "experimental" / "fully_async_policy" / "fully_async_trainer.py",
        "detach_utils": root / "verl" / "experimental" / "fully_async_policy" / "detach_utils.py",
        "fully_async_config": root
        / "verl"
        / "experimental"
        / "fully_async_policy"
        / "config"
        / "fully_async_ppo_trainer.yaml",
    }
    for name, path in files.items():
        if not path.exists():
            diagnostics.append(f"missing:{name}:{path}")

    parsed: dict[str, ast.Module] = {}
    for name, path in files.items():
        if path.suffix == ".py" and path.exists():
            parsed[name] = _read_ast(path)

    main_task_runner = _find_class(parsed.get("fully_async_main", ast.Module(body=[], type_ignores=[])), "FullyAsyncTaskRunner")
    rollouter = _find_class(parsed.get("fully_async_rollouter", ast.Module(body=[], type_ignores=[])), "FullyAsyncRollouter")
    trainer = _find_class(parsed.get("fully_async_trainer", ast.Module(body=[], type_ignores=[])), "FullyAsyncTrainer")
    message_queue = _find_class(parsed.get("message_queue", ast.Module(body=[], type_ignores=[])), "MessageQueue")
    message_queue_client = _find_class(
        parsed.get("message_queue", ast.Module(body=[], type_ignores=[])),
        "MessageQueueClient",
    )
    rollout_sample = _find_class(parsed.get("detach_utils", ast.Module(body=[], type_ignores=[])), "RolloutSample")

    modules = {
        name: _relative_module_path(path, reference_verl_root=root)
        for name, path in files.items()
        if path.exists()
    }
    classes = {}
    if main_task_runner is not None:
        classes["FullyAsyncTaskRunner"] = modules.get("fully_async_main", "")
    if rollouter is not None:
        classes["FullyAsyncRollouter"] = modules.get("fully_async_rollouter", "")
    if trainer is not None:
        classes["FullyAsyncTrainer"] = modules.get("fully_async_trainer", "")
    if message_queue is not None:
        classes["MessageQueue"] = modules.get("message_queue", "")
    if message_queue_client is not None:
        classes["MessageQueueClient"] = modules.get("message_queue", "")
    if rollout_sample is not None:
        classes["RolloutSample"] = modules.get("detach_utils", "")

    method_signatures = {}
    for key, signature in {
        "FullyAsyncTrainer._fit_generate": _method_signature(trainer, "_fit_generate"),
        "FullyAsyncTrainer._compute_old_log_prob": _method_signature(trainer, "_compute_old_log_prob"),
        "MessageQueue.put_sample": _method_signature(message_queue, "put_sample"),
        "MessageQueueClient.put_sample": _method_signature(message_queue_client, "put_sample"),
        "FullyAsyncRollouter._feed_samples": _method_signature(rollouter, "_feed_samples"),
    }.items():
        if signature is not None:
            method_signatures[key] = signature

    config_paths = {
        "fully_async_main": "verl.experimental.fully_async_policy.fully_async_main",
        "actor_rollout_ref.actor.use_rollout_log_probs": "actor_rollout_ref.actor.use_rollout_log_probs",
        "algorithm.rollout_correction.bypass_mode": "algorithm.rollout_correction.bypass_mode",
        "data.train_batch_size": "data.train_batch_size=0 in fully async mode",
        "data.gen_batch_size": "data.gen_batch_size=1 in streaming fully async mode",
        "async_training.require_batches": "async_training.require_batches",
        "async_training.trigger_parameter_sync_step": "async_training.trigger_parameter_sync_step",
        "async_training.staleness_threshold": "async_training.staleness_threshold",
        "async_training.partial_rollout": "async_training.partial_rollout",
    }

    return FullyAsyncInterfaceInventory(
        reference_verl_root=str(root),
        reference_verl_commit=_reference_verl_commit(root),
        modules=modules,
        classes=classes,
        rollout_sample_fields=_dataclass_field_names(rollout_sample),
        method_signatures=method_signatures,
        config_paths=config_paths,
        fully_async_task_runner_present=main_task_runner is not None,
        heavy_import_required=False,
        diagnostics=diagnostics,
    )
