from __future__ import annotations

import json
from pathlib import Path

from repo_harness_verl.stage14_remote_smoke import (
    build_stage14_agent_loop_config,
    build_stage14_hydra_overrides,
    build_stage14_remote_environment,
    stage14_default_remote_smoke_profile,
    write_stage14_remote_smoke_kit,
)


def test_stage14_remote_smoke_profile_encodes_known_working_2x96gb_baseline() -> None:
    profile = stage14_default_remote_smoke_profile()

    assert profile.profile_name == "dev_smoke_2x96gb_small_full_sync"
    assert profile.gpu_count == 2
    assert profile.gpu_memory_gb_per_device == 96
    assert profile.model_id == "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    assert profile.inference_backend == "sglang"
    assert profile.training_strategy == "full"
    assert profile.weight_sync_strategy == "nixl_cuda"
    assert profile.checkpoint_engine_backend == "nixl"
    assert profile.checkpoint_engine_device == "cuda"
    assert profile.lora_rank == 0
    assert profile.calculate_log_probs is True
    assert profile.hybrid_engine is False
    assert profile.multi_turn_enabled is True


def test_stage14_hydra_overrides_include_fully_async_repo_harness_requirements() -> None:
    overrides = build_stage14_hydra_overrides()

    assert "actor_rollout_ref.hybrid_engine=False" in overrides
    assert "actor_rollout_ref.rollout.mode=async" in overrides
    assert "actor_rollout_ref.rollout.checkpoint_engine.backend=nixl" in overrides
    assert "actor_rollout_ref.rollout.checkpoint_engine.engine_kwargs.nixl.device=cuda" in overrides
    assert "actor_rollout_ref.rollout.agent.agent_loop_config_path=repo_harness_agent_loop_config.yaml" in overrides
    assert "actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness" in overrides
    assert "actor_rollout_ref.rollout.agent.num_workers=1" in overrides
    assert "actor_rollout_ref.rollout.multi_turn.enable=True" in overrides
    assert "actor_rollout_ref.rollout.calculate_log_probs=True" in overrides
    assert "actor_rollout_ref.actor.use_rollout_log_probs=True" in overrides
    assert "actor_rollout_ref.model.path=Qwen/Qwen2.5-Coder-1.5B-Instruct" in overrides
    assert "actor_rollout_ref.model.lora_rank=0" in overrides
    assert not any(value.startswith("actor_rollout_ref.model.lora_alpha=") for value in overrides)
    assert not any(value.startswith("actor_rollout_ref.model.lora.merge=") for value in overrides)
    assert "actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1" in overrides
    assert "actor_rollout_ref.actor.fsdp_config.param_offload=True" in overrides
    assert "actor_rollout_ref.actor.fsdp_config.optimizer_offload=True" in overrides
    assert "reward.reward_model.enable=False" in overrides
    assert "reward_model.enable=False" not in overrides
    assert "data.train_batch_size=0" in overrides
    assert "data.gen_batch_size=1" in overrides
    assert "actor_rollout_ref.rollout.engine_kwargs.sglang.attention_backend=flashinfer" in overrides
    assert "actor_rollout_ref.rollout.engine_kwargs.sglang.decode_attention_backend=flashinfer" in overrides
    assert "actor_rollout_ref.rollout.engine_kwargs.sglang.prefill_attention_backend=flashinfer" in overrides
    assert "data.prompt_key=prompt" in overrides
    assert "data.return_raw_chat=True" in overrides
    assert "async_training.trigger_parameter_sync_step=2" in overrides
    assert "async_training.require_batches=1" in overrides
    assert "async_training.staleness_threshold=1" in overrides


def test_stage14_agent_loop_config_uses_repo_harness_verl_agent_loop() -> None:
    config = build_stage14_agent_loop_config()

    assert config == [
        {
            "name": "repo_harness",
            "_target_": "repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop",
        }
    ]


def test_stage14_remote_environment_keeps_local_package_importable() -> None:
    env = build_stage14_remote_environment()

    assert env["PYTHONPATH"].startswith("src:reference/verl:")
    assert env["SGLANG_ATTENTION_BACKEND"] == "flashinfer"
    assert env["TORCH_CUDA_ARCH_LIST"] == "12.0"
    assert env["VLLM_ALLOW_RUNTIME_LORA_UPDATING"] == "true"
    assert env["CUDA_DEVICE_MAX_CONNECTIONS"] == "1"


def test_stage14_remote_smoke_kit_writes_auditable_files(tmp_path: Path) -> None:
    result = write_stage14_remote_smoke_kit(tmp_path)

    assert result["profile"]["profile_name"] == "dev_smoke_2x96gb_small_full_sync"
    assert (tmp_path / "stage14_training_profile.json").exists()
    assert (tmp_path / "repo_harness_agent_loop_config.yaml").exists()
    assert (tmp_path / "stage14_hydra_overrides.json").exists()
    agent_loop_config_path = next(
        value.split("=", 1)[1]
        for value in result["hydra_overrides"]
        if value.startswith("actor_rollout_ref.rollout.agent.agent_loop_config_path=")
    )
    assert agent_loop_config_path == "repo_harness_agent_loop_config.yaml"
    overrides = json.loads((tmp_path / "stage14_hydra_overrides.json").read_text(encoding="utf-8"))
    assert "actor_rollout_ref.hybrid_engine=False" in overrides
