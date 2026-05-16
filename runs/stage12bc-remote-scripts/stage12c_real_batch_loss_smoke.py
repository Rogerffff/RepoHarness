from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import ray
import torch
from omegaconf import OmegaConf
from transformers import AutoTokenizer


MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
IMAGE = "verlai/verl:sgl056.latest"
REPO_ROOT = Path("/workspace/RepoHarness")
SCRIPT_ROOT = REPO_ROOT / "runs" / "stage12bc-remote-scripts"
RUN_ROOT = REPO_ROOT / "runs" / ("stage12c-real-batch-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
SOURCE_ROOT = RUN_ROOT / "source_repos"
REAL_RUNS_DIR = RUN_ROOT / "real_episode_runs"
REPORT_PATH = RUN_ROOT / "stage12c_real_batch_loss_path_report.json"
COMMAND_LOG_PATH = RUN_ROOT / "stage12c_real_batch_command_log.jsonl"


def _load_retry_module() -> Any:
    path = SCRIPT_ROOT / "stage12b_failed_task_retries_smoke.py"
    spec = importlib.util.spec_from_file_location("stage12b_failed_task_retries_smoke_for_stage12c", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed_to_load_retry_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.RUN_ROOT = RUN_ROOT
    module.SOURCE_ROOT = SOURCE_ROOT
    module.REAL_RUNS_DIR = REAL_RUNS_DIR
    module.SUMMARY_PATH = RUN_ROOT / "stage12c_reused_retry_task_summary.json"
    return module


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _run_command(name: str, argv: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env={**os.environ, **(env or {})},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    ended = datetime.now(timezone.utc)
    record = {
        "schema_version": "repo_harness_stage12c_real_batch_command_log_entry_v0",
        "name": name,
        "argv": argv,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_seconds": (ended - started).total_seconds(),
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-8000:],
    }
    _append_jsonl(COMMAND_LOG_PATH, record)
    return record


def _response_spans_from_mask(mask: list[int], *, item_index: int, global_steps: int) -> list[Any]:
    from repo_harness.rl.training_view import ResponseSpan

    spans: list[Any] = []
    if not mask:
        return spans
    start = 0
    current = int(mask[0])
    for index in range(1, len(mask) + 1):
        next_value = int(mask[index]) if index < len(mask) else None
        if next_value == current:
            continue
        source_type = "assistant_generation" if current == 1 else "tool_observation"
        spans.append(
            ResponseSpan(
                start=start,
                end=index,
                source_type=source_type,
                model_call_id=f"stage12c-real-batch-output-{item_index}" if current == 1 else None,
                tool_call_id=f"stage12c-real-batch-tool-observation-{item_index}-{len(spans)}" if current == 0 else None,
                artifact_ref=f"rh://artifact/stage12c-real-batch/{item_index}/span-{len(spans)}",
                response_mask_value=current,  # type: ignore[arg-type]
                logprob_policy="provider_logprobs" if current == 1 else "zero_for_observation",
                global_steps=global_steps,
                min_global_steps=global_steps,
                max_global_steps=global_steps,
            )
        )
        start = index
        current = int(next_value) if next_value is not None else current
    return spans


async def _run_one_collect(
    *,
    retry_module: Any,
    tokenizer: Any,
    client: Any,
    server: Any,
    task: Any,
    index: int,
    source_paths: dict[str, str],
) -> dict[str, Any]:
    from repo_harness.rl import RepoHarnessRuntime
    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop
    from repo_harness_verl.visibility import validate_transfer_queue_field_visibility

    start_call_index = len(server.calls)
    runtime = RepoHarnessRuntime(retry_module.runtime_options(tokenizer, task, source_paths))
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=retry_module.trainer_config(),
        server_manager=client,
        tokenizer=tokenizer,
        processor=None,
        dataset_cls=object,
        data_config=retry_module.ConfigWrap({"apply_chat_template_kwargs": {}}),
        runtime=runtime,
        inference_backend="sglang",
    )
    kwargs = retry_module.sample_kwargs(task, index)
    try:
        # Keep the episode-level response budget large enough for multi-turn
        # assistant tokens plus tool observation tokens. The local SGLang handle
        # still caps each individual model generation at 96 tokens below.
        output = await loop.run({"max_new_tokens": 256, "temperature": 0.0, "top_p": 1.0}, **kwargs)
        field = output.as_dict()
        field.update({"raw_prompt": kwargs["raw_prompt"]})
        validate_transfer_queue_field_visibility(field)
        extra_fields = dict(output.extra_fields)
        return {
            "task_id": task.task_id,
            "status": "completed",
            "repo_harness_status": extra_fields.get("repo_harness_status"),
            "invalid_for_training": extra_fields.get("repo_harness_invalid_for_training"),
            "invalid_for_online_rl": extra_fields.get("repo_harness_invalid_for_online_rl"),
            "reward_score": output.reward_score,
            "num_turns": output.num_turns,
            "response_token_count": len(output.response_ids),
            "response_logprob_count": 0 if output.response_logprobs is None else len(output.response_logprobs),
            "response_mask_count": len(output.response_mask),
            "server_call_count": len(server.calls) - start_call_index,
            "server_calls": server.calls[start_call_index:],
            "kwargs": kwargs,
            "output": output,
        }
    except Exception as exc:
        print("STAGE12C_BATCH_TASK_EXCEPTION", task.task_id, exc.__class__.__name__, str(exc), flush=True)
        return {
            "task_id": task.task_id,
            "status": "failed",
            "failure_type": exc.__class__.__name__,
            "failure_message": str(exc),
            "traceback_tail": traceback.format_exc()[-4000:],
            "server_call_count": len(server.calls) - start_call_index,
            "server_calls": server.calls[start_call_index:],
        }


async def _run(tokenizer: Any) -> dict[str, Any]:
    from repo_harness.rl.training_view import ResponseSpan, RolloutLimits, TrainingView, validate_formal_online_rl_batch
    from repo_harness_verl.conversion import training_view_to_agent_loop_output
    from repo_harness_verl.visibility import validate_dataproto_shapes, validate_dataproto_visibility
    from verl.experimental.agent_loop.agent_loop import AgentLoopWorker
    from verl.trainer.ppo.core_algos import AdvantageEstimator, compute_policy_loss_vanilla
    from verl.trainer.ppo.metric_utils import compute_data_metrics
    from verl.trainer.ppo.ray_trainer import compute_advantage
    from verl.workers.config.actor import ActorConfig
    from verl.workers.rollout.llm_server import GlobalRequestLoadBalancer, LLMServerClient
    import sglang as sgl

    retry_module = _load_retry_module()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    source_paths = retry_module.write_sources()
    (RUN_ROOT / "tool_protocol_prompt_stage12c_batch.txt").write_text(
        retry_module.tool_protocol("relative/path.py") + "\n",
        encoding="utf-8",
    )

    env = {"PYTHONPATH": f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'reference' / 'verl'}"}
    command_records = [
        _run_command("compileall_src", [sys.executable, "-m", "compileall", "-q", "src"], env=env),
        _run_command(
            "stage12c_shape_visibility_prereq_tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/unit/test_repo_harness_verl_stage10_agent_loop_output.py",
                "tests/unit/test_repo_harness_verl_stage10_dataproto_shapes.py",
                "tests/unit/test_repo_harness_verl_stage10_postprocess_visibility.py",
                "tests/unit/test_repo_harness_rl_stage1_visibility_gateway.py",
            ],
            env=env,
        ),
    ]

    if ray.is_initialized():
        ray.shutdown()
    ray.init(ignore_reinit_error=True, include_dashboard=False, num_gpus=2, logging_level="ERROR")

    engine = sgl.Engine(
        model_path=MODEL_ID,
        tp_size=1,
        context_length=8192,
        mem_fraction_static=0.55,
        attention_backend="flashinfer",
        disable_cuda_graph=True,
    )
    server = retry_module.LocalSGLangServerHandle(engine)
    servers = {"sglang0": server}
    load_balancer = GlobalRequestLoadBalancer.remote({"sglang0": None})
    client = LLMServerClient(OmegaConf.create({}), servers, load_balancer)

    task_results: list[dict[str, Any]] = []
    collected_outputs: list[tuple[Any, dict[str, Any]]] = []
    for index, task in enumerate(retry_module.TASKS):
        print("STAGE12C_BATCH_TASK_START", task.task_id, flush=True)
        result = await _run_one_collect(
            retry_module=retry_module,
            tokenizer=tokenizer,
            client=client,
            server=server,
            task=task,
            index=index,
            source_paths=source_paths,
        )
        task_results.append(result)
        if (
            result.get("status") == "completed"
            and result.get("repo_harness_status") == "succeeded"
            and result.get("invalid_for_training") is False
            and result.get("invalid_for_online_rl") is False
        ):
            collected_outputs.append((result["output"], result["kwargs"]))
        print("STAGE12C_BATCH_TASK_DONE", task.task_id, result.get("status"), result.get("repo_harness_status"), flush=True)

    if len(collected_outputs) < 2:
        return {
            "schema_version": "repo_harness_stage12c_real_batch_loss_path_report_v0",
            "status": "failed",
            "failure_type": "InsufficientValidOutputs",
            "failure_message": f"insufficient_valid_outputs_for_stage12c_batch:{len(collected_outputs)}",
            "model_id": MODEL_ID,
            "image": IMAGE,
            "run_root": str(RUN_ROOT),
            "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
            "task_count": len(task_results),
            "valid_episode_count": len(collected_outputs),
            "invalid_or_failed_episode_count": len(task_results) - len(collected_outputs),
            "task_results": [{key: value for key, value in result.items() if key not in {"output", "kwargs"}} for result in task_results],
            "command_records": command_records,
            "server_call_count": len(server.calls),
            "full_trainer_global_step_executed": False,
        }

    worker = AgentLoopWorker.__new__(AgentLoopWorker)
    worker.tokenizer = tokenizer
    worker.rollout_config = SimpleNamespace(prompt_length=8192, response_length=768)
    worker.processor = None
    worker.reward_loop_worker_handles = None
    worker.distillation_enabled = False

    async def _noop_async(*args: Any, **kwargs: Any) -> None:
        return None

    worker._compute_score = _noop_async
    worker._compute_teacher_logprobs = _noop_async

    internals = []
    for output, kwargs in collected_outputs:
        internals.append(await worker._agent_loop_postprocess(output, validate=False, raw_prompt=kwargs["raw_prompt"]))

    data_proto = worker._postprocess(internals, input_non_tensor_batch=None, validate=False)
    batch_size = len(collected_outputs)
    validate_dataproto_shapes(data_proto, batch_size=batch_size, prompt_length=8192, response_length=768)
    validate_dataproto_visibility(data_proto)

    valid_views = []
    for item_index, (output, _kwargs) in enumerate(collected_outputs):
        extra_fields = {
            key: value
            for key, value in dict(output.extra_fields).items()
            if str(key).startswith("repo_harness_") and isinstance(value, (str, int, float, bool))
        }
        extra_fields.setdefault("repo_harness_llm_gateway_route", "verl")
        global_step_value = int(extra_fields.get("repo_harness_global_steps") or item_index)
        valid_views.append(
            TrainingView(
                online_rl_eligible=True,
                rollout_limits=RolloutLimits(prompt_length=8192, response_length=768),
                prompt_ids=list(output.prompt_ids),
                response_ids=list(output.response_ids),
                response_mask=list(output.response_mask),
                response_logprobs=list(output.response_logprobs),
                response_spans=_response_spans_from_mask(
                    list(output.response_mask),
                    item_index=item_index,
                    global_steps=global_step_value,
                ),
                reward_score=float(output.reward_score),
                num_turns=int(output.num_turns),
                extra_fields=extra_fields,
            )
        )
    validate_formal_online_rl_batch(valid_views)

    # Exercise the same converter path on each sample before batching, so this smoke
    # proves the formal converter accepts every real episode output independently.
    converted_outputs = [
        training_view_to_agent_loop_output(view, formal_online_rl=True, rollout_prompt_length=8192, rollout_response_length=768)
        for view in valid_views
    ]

    data_proto.batch["token_level_rewards"] = data_proto.batch["rm_scores"].float()
    data_proto.batch["token_level_scores"] = data_proto.batch["rm_scores"].float()
    data_proto.non_tensor_batch["uid"] = np.array([f"stage12c_real_batch_uid_{i}" for i in range(batch_size)], dtype=object)
    data_with_advantage = compute_advantage(
        data_proto,
        adv_estimator=AdvantageEstimator.GRPO,
        norm_adv_by_std_in_grpo=False,
    )
    old_log_prob = data_with_advantage.batch["rollout_log_probs"].float()
    log_prob = old_log_prob.clone()
    advantages = data_with_advantage.batch["advantages"].float()
    response_mask = data_with_advantage.batch["response_mask"].float()
    actor_config = ActorConfig(strategy="fsdp", rollout_n=1, ppo_micro_batch_size=1, clip_ratio=0.2)
    policy_loss, policy_metrics = compute_policy_loss_vanilla(
        old_log_prob=old_log_prob,
        log_prob=log_prob,
        advantages=advantages,
        response_mask=response_mask,
        loss_agg_mode="token-mean",
        config=actor_config,
    )
    if not torch.isfinite(policy_loss):
        raise RuntimeError("stage12c_real_batch_policy_loss_not_finite")

    data_metrics = compute_data_metrics(data_with_advantage, use_critic=False)

    public_results = []
    for result in task_results:
        public = {key: value for key, value in result.items() if key not in {"output", "kwargs"}}
        public_results.append(public)

    valid_task_ids = [result["task_id"] for result in task_results if result.get("task_id") in {r[1]["task_id"] for r in collected_outputs}]
    rejected_task_ids = [result["task_id"] for result in task_results if result.get("task_id") not in set(valid_task_ids)]

    return {
        "schema_version": "repo_harness_stage12c_real_batch_loss_path_report_v0",
        "status": "passed",
        "model_id": MODEL_ID,
        "image": IMAGE,
        "run_root": str(RUN_ROOT),
        "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "task_count": len(task_results),
        "valid_episode_count": batch_size,
        "invalid_or_failed_episode_count": len(task_results) - batch_size,
        "valid_task_ids": valid_task_ids,
        "filtered_task_ids": rejected_task_ids,
        "server_call_count": len(server.calls),
        "task_results": public_results,
        "command_records": command_records,
        "dataproto_shapes": {
            key: list(value.shape)
            for key, value in data_proto.batch.items()
            if key
            in {
                "prompts",
                "responses",
                "response_mask",
                "rollout_log_probs",
                "rm_scores",
                "token_level_rewards",
                "advantages",
                "returns",
            }
        },
        "dataproto_visibility": "passed",
        "formal_batch_validator": "passed",
        "individual_training_view_converter_count": len(converted_outputs),
        "advantage_estimator": "GRPO",
        "loss_path": "AgentLoopOutput_list -> AgentLoopWorker._agent_loop_postprocess -> AgentLoopWorker._postprocess -> DataProto -> compute_advantage_GRPO -> compute_policy_loss_vanilla",
        "policy_loss": float(policy_loss.detach().cpu()),
        "policy_metrics": {
            key: float(value.detach().cpu()) if hasattr(value, "detach") else float(value)
            for key, value in policy_metrics.items()
        },
        "data_metric_keys": sorted(data_metrics.keys()),
        "sample_data_metrics": {
            key: float(value.detach().cpu()) if hasattr(value, "detach") else float(value)
            for key, value in list(data_metrics.items())[:20]
            if isinstance(value, int | float) or hasattr(value, "detach")
        },
        "full_trainer_global_step_executed": False,
        "interpretation": (
            "This smoke uses multiple successful real Qwen2.5-Coder RepoHarness episodes to build one real verl "
            "DataProto batch and execute GRPO advantage plus policy loss. It still does not instantiate the full "
            "RayPPOTrainer.fit global-step orchestration."
        ),
    }


def main() -> None:
    os.environ.setdefault("HF_HOME", "/workspace/hf_cache")
    os.environ.setdefault("TRANSFORMERS_CACHE", "/workspace/hf_cache")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    try:
        report = asyncio.run(_run(tokenizer))
    except Exception as exc:
        report = {
            "schema_version": "repo_harness_stage12c_real_batch_loss_path_report_v0",
            "status": "failed",
            "failure_type": exc.__class__.__name__,
            "failure_message": str(exc),
            "run_root": str(RUN_ROOT),
        }
        raise
    finally:
        if "report" in locals():
            _write_json(REPORT_PATH, report)
            print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), flush=True)
        if ray.is_initialized():
            ray.shutdown()


if __name__ == "__main__":
    main()
