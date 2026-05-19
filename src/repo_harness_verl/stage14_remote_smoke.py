"""Stage 14 remote fully async smoke profile helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import Field

from repo_harness.schema_base import StrictBaseModel


class Stage14RemoteSmokeProfile(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage14_remote_smoke_profile_v0"
    profile_name: str = "dev_smoke_2x96gb_small_full_sync"
    gpu_count: int = Field(default=2, ge=1)
    gpu_memory_gb_per_device: int = Field(default=96, ge=1)
    model_id: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    inference_backend: str = "sglang"
    training_strategy: str = "full"
    weight_sync_strategy: str = "nixl_cuda"
    required_samples: int = Field(default=1, ge=1)
    total_rollout_steps: int = Field(default=8, ge=1)
    trigger_parameter_sync_step: int = Field(default=2, ge=1)
    require_batches: int = Field(default=1, ge=1)
    staleness_threshold: int = Field(default=1, ge=0)
    partial_rollout: bool = False
    rollout_mode: str = "async"
    checkpoint_engine_backend: str = "nixl"
    checkpoint_engine_device: str | None = "cuda"
    gpu_memory_utilization: float = Field(default=0.25, gt=0.0, le=1.0)
    max_model_len: int = Field(default=4608, ge=1)
    max_num_seqs: int = Field(default=2, ge=1)
    max_num_batched_tokens: int = Field(default=6144, ge=1)
    log_prob_micro_batch_size_per_gpu: int = Field(default=1, ge=1)
    agent_default_agent_loop: str = "repo_harness"
    agent_num_workers: int = Field(default=1, ge=1)
    lora_rank: int = Field(default=0, ge=0)
    lora_alpha: int = Field(default=16, ge=1)
    lora_target_modules: list[str] = Field(default_factory=list)
    lora_merge: bool = False
    trust_remote_code: bool = True
    use_remove_padding: bool = True
    enable_gradient_checkpointing: bool = True
    enable_activation_offload: bool = True
    calculate_log_probs: bool = True
    use_rollout_log_probs: bool = True
    ppo_mini_batch_size: int = Field(default=1, ge=1)
    ppo_micro_batch_size_per_gpu: int = Field(default=1, ge=1)
    ppo_epochs: int = Field(default=1, ge=1)
    actor_param_offload: bool = True
    actor_optimizer_offload: bool = True
    actor_use_orig_params: bool = True
    critic_enabled: bool = False
    reward_model_enabled: bool = False
    rollout_correction_bypass_mode: bool = True
    hybrid_engine: bool = False
    multi_turn_enabled: bool = True
    rollout_nnodes: int = Field(default=1, ge=1)
    rollout_n_gpus_per_node: int = Field(default=1, ge=1)
    trainer_nnodes: int = Field(default=1, ge=1)
    trainer_n_gpus_per_node: int = Field(default=1, ge=1)
    data_prompt_key: str = "prompt"
    data_return_raw_chat: bool = True
    data_train_batch_size: int = Field(default=0, ge=0)
    data_gen_batch_size: int = Field(default=1, ge=1)
    sglang_attention_backend: str = "flashinfer"
    sglang_decode_attention_backend: str = "flashinfer"
    sglang_prefill_attention_backend: str = "flashinfer"


def stage14_default_remote_smoke_profile() -> Stage14RemoteSmokeProfile:
    return Stage14RemoteSmokeProfile()


def build_stage14_agent_loop_config() -> list[dict[str, str]]:
    return [
        {
            "name": "repo_harness",
            "_target_": "repo_harness_verl.agent_loop.RepoHarnessVerlAgentLoop",
        }
    ]


def build_stage14_hydra_overrides(
    profile: Stage14RemoteSmokeProfile | None = None,
    *,
    train_files: str = "stage14_train.parquet",
    val_files: str = "stage14_val.parquet",
    agent_loop_config_path: str = "repo_harness_agent_loop_config.yaml",
) -> list[str]:
    profile = profile or stage14_default_remote_smoke_profile()
    bool_value = {True: "True", False: "False"}
    return [
        f"data.train_files={train_files}",
        f"data.val_files={val_files}",
        f"data.prompt_key={profile.data_prompt_key}",
        f"data.return_raw_chat={bool_value[profile.data_return_raw_chat]}",
        f"data.train_batch_size={profile.data_train_batch_size}",
        f"data.gen_batch_size={profile.data_gen_batch_size}",
        f"actor_rollout_ref.model.path={profile.model_id}",
        f"actor_rollout_ref.hybrid_engine={bool_value[profile.hybrid_engine]}",
        f"actor_rollout_ref.rollout.name={profile.inference_backend}",
        f"actor_rollout_ref.rollout.mode={profile.rollout_mode}",
        f"actor_rollout_ref.rollout.checkpoint_engine.backend={profile.checkpoint_engine_backend}",
        *(
            [
                "actor_rollout_ref.rollout.checkpoint_engine.engine_kwargs.nixl.device="
                f"{profile.checkpoint_engine_device}"
            ]
            if profile.checkpoint_engine_backend == "nixl" and profile.checkpoint_engine_device
            else []
        ),
        f"actor_rollout_ref.rollout.gpu_memory_utilization={profile.gpu_memory_utilization}",
        f"actor_rollout_ref.rollout.max_model_len={profile.max_model_len}",
        f"actor_rollout_ref.rollout.max_num_seqs={profile.max_num_seqs}",
        f"actor_rollout_ref.rollout.max_num_batched_tokens={profile.max_num_batched_tokens}",
        f"actor_rollout_ref.rollout.engine_kwargs.sglang.attention_backend={profile.sglang_attention_backend}",
        f"actor_rollout_ref.rollout.engine_kwargs.sglang.decode_attention_backend={profile.sglang_decode_attention_backend}",
        f"actor_rollout_ref.rollout.engine_kwargs.sglang.prefill_attention_backend={profile.sglang_prefill_attention_backend}",
        f"actor_rollout_ref.rollout.calculate_log_probs={bool_value[profile.calculate_log_probs]}",
        f"actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu={profile.log_prob_micro_batch_size_per_gpu}",
        f"actor_rollout_ref.rollout.agent.default_agent_loop={profile.agent_default_agent_loop}",
        f"actor_rollout_ref.rollout.agent.num_workers={profile.agent_num_workers}",
        f"actor_rollout_ref.rollout.agent.agent_loop_config_path={agent_loop_config_path}",
        f"actor_rollout_ref.rollout.multi_turn.enable={bool_value[profile.multi_turn_enabled]}",
        f"actor_rollout_ref.model.lora_rank={profile.lora_rank}",
        *(
            [
                f"actor_rollout_ref.model.lora_alpha={profile.lora_alpha}",
                "actor_rollout_ref.model.target_modules="
                + json.dumps(profile.lora_target_modules, separators=(",", ":")),
                f"actor_rollout_ref.model.lora.merge={bool_value[profile.lora_merge]}",
            ]
            if profile.lora_rank > 0
            else []
        ),
        f"actor_rollout_ref.model.trust_remote_code={bool_value[profile.trust_remote_code]}",
        f"actor_rollout_ref.model.use_remove_padding={bool_value[profile.use_remove_padding]}",
        f"actor_rollout_ref.model.enable_gradient_checkpointing={bool_value[profile.enable_gradient_checkpointing]}",
        f"actor_rollout_ref.model.enable_activation_offload={bool_value[profile.enable_activation_offload]}",
        f"actor_rollout_ref.actor.use_rollout_log_probs={bool_value[profile.use_rollout_log_probs]}",
        f"actor_rollout_ref.actor.ppo_mini_batch_size={profile.ppo_mini_batch_size}",
        f"actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu={profile.ppo_micro_batch_size_per_gpu}",
        f"actor_rollout_ref.actor.ppo_epochs={profile.ppo_epochs}",
        f"actor_rollout_ref.actor.fsdp_config.param_offload={bool_value[profile.actor_param_offload]}",
        f"actor_rollout_ref.actor.fsdp_config.optimizer_offload={bool_value[profile.actor_optimizer_offload]}",
        f"actor_rollout_ref.actor.fsdp_config.use_orig_params={bool_value[profile.actor_use_orig_params]}",
        f"critic.enable={bool_value[profile.critic_enabled]}",
        f"reward.reward_model.enable={bool_value[profile.reward_model_enabled]}",
        f"algorithm.rollout_correction.bypass_mode={bool_value[profile.rollout_correction_bypass_mode]}",
        f"rollout.nnodes={profile.rollout_nnodes}",
        f"rollout.n_gpus_per_node={profile.rollout_n_gpus_per_node}",
        f"trainer.nnodes={profile.trainer_nnodes}",
        f"trainer.n_gpus_per_node={profile.trainer_n_gpus_per_node}",
        f"async_training.trigger_parameter_sync_step={profile.trigger_parameter_sync_step}",
        f"async_training.require_batches={profile.require_batches}",
        f"async_training.staleness_threshold={profile.staleness_threshold}",
        f"async_training.partial_rollout={bool_value[profile.partial_rollout]}",
        f"rollout.total_rollout_steps={profile.total_rollout_steps}",
    ]


def build_stage14_remote_environment() -> dict[str, str]:
    return {
        "PYTHONPATH": "src:reference/verl:${PYTHONPATH}",
        "SGLANG_ATTENTION_BACKEND": "flashinfer",
        "TOKENIZERS_PARALLELISM": "false",
        "TORCH_CUDA_ARCH_LIST": "12.0",
        "VLLM_ALLOW_RUNTIME_LORA_UPDATING": "true",
        "CUDA_DEVICE_MAX_CONNECTIONS": "1",
    }


def _agent_loop_config_yaml(config: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for item in config:
        lines.append(f"- name: {item['name']}")
        lines.append(f"  _target_: {item['_target_']}")
    return "\n".join(lines) + "\n"


def write_stage14_remote_smoke_kit(output_dir: str | Path) -> dict[str, Any]:
    """写出本地可复查的 Stage 14 远端 smoke 配置骨架。"""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    profile = stage14_default_remote_smoke_profile()
    agent_loop_config = build_stage14_agent_loop_config()
    hydra_overrides = build_stage14_hydra_overrides(profile)
    environment = build_stage14_remote_environment()
    (root / "stage14_training_profile.json").write_text(
        profile.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "repo_harness_agent_loop_config.yaml").write_text(
        _agent_loop_config_yaml(agent_loop_config),
        encoding="utf-8",
    )
    (root / "stage14_hydra_overrides.json").write_text(
        json.dumps(hydra_overrides, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "stage14_remote_environment.json").write_text(
        json.dumps(environment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "profile": profile.model_dump(mode="json"),
        "agent_loop_config": agent_loop_config,
        "hydra_overrides": hydra_overrides,
        "environment": environment,
    }
