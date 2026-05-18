from __future__ import annotations

from pathlib import Path

from repo_harness_verl import build_fully_async_interface_inventory


def test_stage13_2_reference_fully_async_interface_still_matches_bridge_assumptions() -> None:
    inventory = build_fully_async_interface_inventory()

    assert {"full_batch", "sample_id", "epoch", "rollout_status"}.issubset(
        set(inventory.rollout_sample_fields)
    )
    assert inventory.method_signatures["MessageQueue.put_sample"] == "async put_sample(self, sample)"
    assert inventory.method_signatures["MessageQueueClient.put_sample"] == "async put_sample(self, sample)"
    assert inventory.config_paths["fully_async_main"] == "verl.experimental.fully_async_policy.fully_async_main"

    detach_utils = (
        Path(inventory.reference_verl_root)
        / inventory.modules["detach_utils"]
    ).read_text(encoding="utf-8")
    assert 'metrics = output.meta_info.pop("metrics")' in detach_utils
    assert 'output.non_tensor_batch["processing_times"] = processing_times_list' in detach_utils
    assert 'output.non_tensor_batch["tool_calls_times"] = tool_calls_times_list' in detach_utils
