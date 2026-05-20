from __future__ import annotations

import sys

from repo_harness_verl.stage15_inventory import build_stage15_partial_rollout_interface_inventory


def test_stage15_0_inventory_reads_reference_sources_without_heavy_imports() -> None:
    heavy_modules = {"verl", "torch", "ray", "tensordict"}
    before = {name for name in heavy_modules if name in sys.modules}

    inventory = build_stage15_partial_rollout_interface_inventory()

    after = {name for name in heavy_modules if name in sys.modules}
    assert after == before
    assert inventory.static_scan_only is True
    assert inventory.heavy_import_required is False
    assert inventory.reference_verl_root == "reference/verl"
    assert inventory.reference_verl_commit


def test_stage15_0_inventory_captures_checkpoint_engine_abort_resume_chain() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()
    chain = inventory.native_partial_rollout_trigger_chain

    assert chain["weight_sync_calls_checkpoint_manager_update_weights"] is True
    assert chain["checkpoint_manager_aborts_inflight_requests"] is True
    assert chain["checkpoint_manager_abort_gated_by_partial_rollout"] is False
    assert chain["server_resume_generation_after_weight_sync"] is True
    assert chain["fully_llm_client_continue_gated_by_partial_rollout"] is True
    assert chain["abort_stop_reason_visible_to_agent_loop"] is False
    assert "参数同步中断" in chain["repo_harness_checkpoint_implication"]
    assert any(
        item["source_path"].endswith("fully_async_trainer.py")
        for item in chain["evidence"]
    )
    assert any(item["source_path"].endswith("checkpoint_engine/base.py") for item in chain["evidence"])
    assert any(item["source_path"].endswith("workers/rollout/replica.py") for item in chain["evidence"])


def test_stage15_0_inventory_captures_required_config_surface() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()
    config = inventory.config_inventory
    required = {
        "async_training.partial_rollout",
        "async_training.trigger_parameter_sync_step",
        "async_training.require_batches",
        "async_training.staleness_threshold",
        "rollout.total_rollout_steps",
        "actor_rollout_ref.hybrid_engine",
        "data.train_batch_size",
        "data.gen_batch_size",
        "actor_rollout_ref.rollout.calculate_log_probs",
        "actor_rollout_ref.actor.use_rollout_log_probs",
        "actor_rollout_ref.rollout.agent.agent_loop_config_path",
        "actor_rollout_ref.rollout.multi_turn.enable",
        "actor_rollout_ref.rollout.name",
        "trainer.nnodes",
        "trainer.n_gpus_per_node",
        "rollout.nnodes",
        "rollout.n_gpus_per_node",
        "checkpoint_engine.backend",
    }

    assert required.issubset(config)
    for key in required:
        payload = config[key]
        assert payload["source_path"]
        assert payload["source_evidence"]
        assert "current_stage14_override" in payload
        assert "stage15_required_override" in payload
    assert config["rollout.total_rollout_steps"]["current_stage14_override"] == 8
    assert config["rollout.total_rollout_steps"]["stage15_required_override"] == 16
    assert config["async_training.partial_rollout"]["current_stage14_override"] is False
    assert config["async_training.partial_rollout"]["stage15_required_override"] is True
    assert config["actor_rollout_ref.rollout.multi_turn.enable"]["stage15_required_override"] is True
    assert (
        config["actor_rollout_ref.rollout.agent.agent_loop_config_path"]["source_path"]
        == "src/repo_harness_verl/stage14_remote_smoke.py"
    )
    assert (
        config["actor_rollout_ref.rollout.agent.agent_loop_config_path"]["source_evidence"]
        == "actor_rollout_ref.rollout.agent.agent_loop_config_path="
    )
    assert config["actor_rollout_ref.rollout.name"]["source_path"] == (
        "src/repo_harness_verl/stage14_remote_smoke.py"
    )
    assert config["checkpoint_engine.backend"]["source_evidence"] == (
        "actor_rollout_ref.rollout.checkpoint_engine.backend="
    )
    assert config["checkpoint_engine.backend"]["stage15_required_override"] == "nixl"


def test_stage15_0_inventory_captures_fully_llm_server_client_stop_reason_semantics() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()
    llm = inventory.llm_server_stop_reason_inventory

    assert llm["base_client_class"] == "LLMServerClient"
    assert llm["fully_async_client_class"] == "FullyLLMServerClient"
    assert llm["fully_async_client_selected_by_get_client"] is True
    assert llm["abort_auto_continues_inside_fully_llm_server_client"] is True
    assert llm["abort_visible_to_repo_harness_agent_loop"] is False
    assert llm["continue_loop_gated_by_partial_rollout"] is True
    assert llm["backend_specific_stop_reason_mapping_checked"] is True
    assert llm["completed_stop_reason_mapping_checked"] is True
    assert llm["default_stage14_backend"] == "sglang"
    by_backend = llm["normal_completion_stop_reason_by_backend"]
    assert by_backend["vllm"]["normalizes_stop_and_length_to_completed"] is True
    assert by_backend["vllm"]["normal_completion_values_after_adapter"] == ["completed"]
    assert by_backend["sglang"]["returns_raw_finish_reason"] is True
    assert by_backend["sglang"]["normal_completion_values_after_adapter"] == ["stop", "length"]
    assert {"abort", "aborted", "length", "stop", "completed"}.issubset(
        set(llm["stop_reasons_to_inventory"])
    )


def test_stage15_0_inventory_records_backend_specific_abort_resume_risks() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()
    by_backend = {item.backend: item for item in inventory.backend_abort_resume_inventory}

    assert by_backend["vllm"].abort_all_requests_present is True
    assert by_backend["vllm"].resume_generation_present is True
    assert by_backend["vllm"].not_implemented is False
    assert by_backend["sglang"].abort_all_requests_present is True
    assert by_backend["sglang"].resume_generation_present is True
    assert by_backend["sglang"].not_implemented is False
    assert by_backend["trtllm"].abort_all_requests_present is True
    assert by_backend["trtllm"].resume_generation_present is True
    assert by_backend["trtllm"].not_implemented is True
    assert by_backend["trtllm"].risk == "trtllm_abort_resume_not_implemented"


def test_stage15_0_inventory_records_trainer_required_samples_without_repo_harness_filter() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()
    queue = inventory.message_queue_trainer_inventory

    assert queue["message_queue_put_sample_async"] is True
    assert queue["message_queue_client_get_sample_async"] is True
    assert queue["trainer_collects_raw_required_samples"] is True
    assert queue["trainer_cloudpickle_loads_queue_entries"] is True
    assert queue["trainer_side_repo_harness_filter_present"] is False
    assert queue["recommended_source_gate"] == "policy_loss_message_queue_only_accepts_valid_completed_sample"
    assert queue["diagnostic_samples_require_side_channel"] is True


def test_stage15_0_inventory_records_same_agent_loop_worker_ownership_scope() -> None:
    inventory = build_stage15_partial_rollout_interface_inventory()
    lifecycle = inventory.repo_harness_agent_loop_lifecycle_inventory

    assert lifecycle["same_runtime_ownership_scope_required"] is True
    assert lifecycle["same_agent_loop_worker_ray_actor_required"] is True
    assert lifecycle["cross_process_resume_supported"] is False
    assert lifecycle["checkpoint_without_live_handle_goes_to_diagnostic_side_channel"] is True
