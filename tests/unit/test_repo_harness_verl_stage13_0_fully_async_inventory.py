from __future__ import annotations

import sys

from repo_harness_verl.fully_async_inventory import build_fully_async_interface_inventory


def test_stage13_0_fully_async_inventory_reads_reference_sources_without_heavy_imports() -> None:
    heavy_modules = {"ray", "torch", "tensordict", "verl"}
    before = {name for name in heavy_modules if name in sys.modules}

    inventory = build_fully_async_interface_inventory()

    after = {name for name in heavy_modules if name in sys.modules}
    assert after == before
    assert inventory.heavy_import_required is False
    assert inventory.fully_async_task_runner_present is True
    assert inventory.classes["FullyAsyncTaskRunner"].endswith("fully_async_main.py")
    assert inventory.classes["FullyAsyncRollouter"].endswith("fully_async_rollouter.py")
    assert inventory.classes["FullyAsyncTrainer"].endswith("fully_async_trainer.py")
    assert inventory.classes["MessageQueue"].endswith("message_queue.py")
    assert inventory.classes["MessageQueueClient"].endswith("message_queue.py")
    assert inventory.classes["RolloutSample"].endswith("detach_utils.py")
    assert {"full_batch", "sample_id", "epoch", "rollout_status"}.issubset(
        set(inventory.rollout_sample_fields)
    )
    assert inventory.method_signatures["FullyAsyncTrainer._fit_generate"].startswith("async _fit_generate")
    assert "actor_rollout_ref.actor.use_rollout_log_probs" in inventory.config_paths
    assert "data.gen_batch_size" in inventory.config_paths
