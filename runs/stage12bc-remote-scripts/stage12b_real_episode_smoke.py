from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import torch

import numpy as np
import ray
from omegaconf import OmegaConf
from transformers import AutoTokenizer

MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
IMAGE = "verlai/verl:sgl056.latest"
REPO_ROOT = Path("/workspace/RepoHarness")
SOURCE_REPO = REPO_ROOT / "tests" / "fixtures" / "repos" / "buggy_calculator"
RUN_ROOT = REPO_ROOT / "runs" / ("stage12b-real-episode-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
REAL_RUNS_DIR = RUN_ROOT / "real_episode_runs"
SUMMARY_PATH = RUN_ROOT / "real_episode_smoke_summary.json"
TOOL_PROTOCOL_PATH = RUN_ROOT / "tool_protocol_prompt_v1.txt"

TOOL_PROTOCOL = """You are RepoHarness software engineering agent.

You must obey this exact output grammar.

When using a tool, your entire assistant message must be exactly:
<tool_call>
{"name": "read_file", "arguments": {"path": "calculator.py"}}
</tool_call>

The literal line <tool_call> is mandatory.
The literal line </tool_call> is mandatory.
Do not output bare JSON if you can output the wrapper.
Do not output Markdown code fences.
Do not add explanation before or after the block.

Allowed tools: read_file, grep, edit_file, git_diff.
Arguments must be a JSON object.

For edit_file, old_text must be exact raw text from the file and new_text must be the replacement raw text.
Before editing calculator.py, read calculator.py.
After editing, give a short final answer without using a tool call.

Do not use absolute paths. Do not mention evaluator-only information.
""".strip()

TASK_PROMPT = """Fix calculator.divide so that division by zero raises ValueError with message division by zero. Keep normal division behavior unchanged."""


class ConfigWrap:
    def __init__(self, config: Any) -> None:
        self.config = config


def _trainer_config() -> ConfigWrap:
    rollout = SimpleNamespace(name="sglang", prompt_length=8192, response_length=768)
    return ConfigWrap(SimpleNamespace(actor_rollout_ref=SimpleNamespace(rollout=rollout)))


def _sample_kwargs() -> dict[str, Any]:
    return {
        "raw_prompt": [
            {"role": "system", "content": TOOL_PROTOCOL},
            {"role": "user", "content": TASK_PROMPT},
        ],
        "agent_name": "repo_harness",
        "task_id": "stage12b-buggy-calculator-real-model",
        "repo_harness_task_ref": {"task_ref": "rh://task/stage12b-buggy-calculator-real-model"},
        "repo_harness_run_mode": "training_fast",
        "uid": "uid-stage12b-real-model",
        "index": 0,
        "session_id": 1,
        "global_steps": 1200,
    }


async def _noop_async(*args: Any, **kwargs: Any) -> None:
    return None


def _verifier_result_from_pytest(workspace_path: Path):
    from repo_harness.verifier import VerifierResult

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    accepted = completed.returncode == 0
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=1.0,
        command=f"{sys.executable} -m pytest -q",
        accepted=accepted,
        pass_ratio=1.0 if accepted else 0.0,
        fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
        pass_to_pass={"passed": 2 if accepted else 0, "total": 2},
        exit_code=completed.returncode,
        error_type=None if accepted else "test_command_error",
    )


def _output_logprobs(output: dict[str, Any]) -> list[float]:
    rows = ((output.get("meta_info") or {}).get("output_token_logprobs") or [])
    result: list[float] = []
    for item in rows:
        if isinstance(item, (list, tuple)) and item:
            result.append(0.0 if item[0] is None else float(item[0]))
    return result


def _finish_reason(output: dict[str, Any]) -> str | None:
    reason = (output.get("meta_info") or {}).get("finish_reason")
    if reason is None:
        return None
    if isinstance(reason, dict):
        return str(reason.get("type") or reason.get("reason") or reason)
    return str(reason)


class LocalRemoteGenerate:
    def __init__(self, server: "LocalSGLangServerHandle") -> None:
        self.server = server

    def remote(self, **kwargs: Any):
        return self.server._generate(**kwargs)


class LocalSGLangServerHandle:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.calls: list[dict[str, Any]] = []
        self.generate = LocalRemoteGenerate(self)

    async def _generate(
        self,
        request_id: str,
        *,
        prompt_ids: list[int],
        sampling_params: dict[str, Any],
        image_data: list[Any] | None = None,
        video_data: list[Any] | None = None,
        **kwargs: Any,
    ):
        from verl.workers.rollout.replica import TokenOutput

        clean_sampling = {key: value for key, value in dict(sampling_params or {}).items() if value is not None}
        if "max_new_tokens" not in clean_sampling and "max_output_tokens" in clean_sampling:
            clean_sampling["max_new_tokens"] = clean_sampling["max_output_tokens"]
        for unsupported in ["max_output_tokens", "reasoning_effort", "thinking_mode"]:
            clean_sampling.pop(unsupported, None)
        clean_sampling.setdefault("temperature", 0.0)
        clean_sampling.setdefault("top_p", 1.0)
        clean_sampling.setdefault("max_new_tokens", 96)
        clean_sampling["max_new_tokens"] = min(int(clean_sampling["max_new_tokens"]), 96)
        print("LOCAL_SERVER_GENERATE_START", request_id, len(prompt_ids), clean_sampling, flush=True)
        try:
            output = await self.engine.async_generate(
                input_ids=[int(item) for item in prompt_ids],
                sampling_params=clean_sampling,
                return_logprob=True,
                logprob_start_len=0,
            )
        except Exception as exc:
            print("LOCAL_SERVER_GENERATE_ERROR", exc.__class__.__name__, str(exc), flush=True)
            self.calls.append({"request_id": request_id, "prompt_len": len(prompt_ids), "sampling_params": clean_sampling, "error_type": exc.__class__.__name__, "error_message": str(exc)})
            raise
        text = str(output.get("text") or "")
        print("LOCAL_SERVER_GENERATE_TEXT", text[:500].replace("\n", " "), flush=True)
        token_ids = [int(item) for item in output.get("output_ids") or []]
        log_probs = _output_logprobs(output)
        self.calls.append(
            {
                "request_id": request_id,
                "prompt_len": len(prompt_ids),
                "sampling_params": clean_sampling,
                "text": text,
                "token_count": len(token_ids),
                "finish_reason": _finish_reason(output),
            }
        )
        return TokenOutput(
            token_ids=token_ids,
            log_probs=log_probs,
            stop_reason=_finish_reason(output),
            extra_fields={"global_steps": 1200, "min_global_steps": 1200, "max_global_steps": 1200},
        )


def _runtime_options(tokenizer: Any):
    from repo_harness.rl import RepoHarnessRuntimeOptions

    def verifier_factory(context: Any):
        def verify():
            return _verifier_result_from_pytest(context.workspace_path)
        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=REAL_RUNS_DIR,
        real_episode_source_resolver=lambda _request: SOURCE_REPO,
        real_episode_final_verifier_factory=verifier_factory,
        tool_observation_token_projector=lambda content: tokenizer.encode(str(content), add_special_tokens=False)[:96],
        episode_timeout_seconds=180.0,
    )


def _write_summary(payload: dict[str, Any]) -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), flush=True)


async def _run(tokenizer: Any) -> dict[str, Any]:
    from repo_harness.rl import RepoHarnessRuntime
    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop
    from repo_harness_verl.visibility import validate_transfer_queue_field_visibility
    from verl.workers.rollout.llm_server import GlobalRequestLoadBalancer, LLMServerClient
    import sglang as sgl

    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    TOOL_PROTOCOL_PATH.write_text(TOOL_PROTOCOL + "\n", encoding="utf-8")

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
    server = LocalSGLangServerHandle(engine)
    servers = {"sglang0": server}
    load_balancer = GlobalRequestLoadBalancer.remote({"sglang0": None})
    client = LLMServerClient(OmegaConf.create({}), servers, load_balancer)

    runtime = RepoHarnessRuntime(_runtime_options(tokenizer))
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=_trainer_config(),
        server_manager=client,
        tokenizer=tokenizer,
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap({"apply_chat_template_kwargs": {}}),
        runtime=runtime,
        inference_backend="sglang",
    )

    output = await loop.run({"max_new_tokens": 512, "temperature": 0.0, "top_p": 1.0}, **_sample_kwargs())
    agent_loop_extra_fields_before_postprocess = dict(output.extra_fields)
    field = output.as_dict()
    field.update({"raw_prompt": _sample_kwargs()["raw_prompt"]})
    validate_transfer_queue_field_visibility(field)

    from repo_harness_verl.visibility import validate_dataproto_shapes, validate_dataproto_visibility
    from verl.experimental.agent_loop.agent_loop import AgentLoopWorker
    from verl.trainer.ppo.core_algos import AdvantageEstimator, compute_policy_loss_vanilla
    from verl.trainer.ppo.ray_trainer import compute_advantage
    from verl.workers.config.actor import ActorConfig

    worker = AgentLoopWorker.__new__(AgentLoopWorker)
    worker.tokenizer = tokenizer
    worker.rollout_config = SimpleNamespace(prompt_length=8192, response_length=768)
    worker.processor = None
    worker.reward_loop_worker_handles = None
    worker.distillation_enabled = False
    worker._compute_score = _noop_async
    worker._compute_teacher_logprobs = _noop_async
    internal = await worker._agent_loop_postprocess(output, validate=False, raw_prompt=_sample_kwargs()["raw_prompt"])
    data_proto = worker._postprocess([internal], input_non_tensor_batch=None, validate=False)
    validate_dataproto_shapes(data_proto, batch_size=1, prompt_length=8192, response_length=768)
    validate_dataproto_visibility(data_proto)
    data_proto.batch["token_level_rewards"] = data_proto.batch["rm_scores"].float()
    data_proto.non_tensor_batch.setdefault("uid", np.array(["stage12c_uid_0"], dtype=object))
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
        raise RuntimeError("stage12c_policy_loss_not_finite")

    server_calls = list(server.calls)

    run_id = output.extra_fields.get("repo_harness_run_id")
    run_dir = REAL_RUNS_DIR / str(run_id) if run_id else None
    manifest_path = run_dir / "artifacts.json" if run_dir else None
    artifact_kinds: list[str] = []
    if manifest_path and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_kinds = sorted({str(item.get("kind")) for item in manifest.get("artifacts", [])})

    return {
        "schema_version": "repo_harness_stage12b_real_episode_smoke_summary_v0",
        "status": "completed",
        "model_id": MODEL_ID,
        "image": IMAGE,
        "run_root": str(RUN_ROOT),
        "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "agent_loop_output_class": output.__class__.__name__,
        "reward_score": output.reward_score,
        "num_turns": output.num_turns,
        "response_token_count": len(output.response_ids),
        "response_logprob_count": 0 if output.response_logprobs is None else len(output.response_logprobs),
        "response_mask_count": len(output.response_mask),
        "extra_fields": agent_loop_extra_fields_before_postprocess,
        "run_dir": str(run_dir) if run_dir else None,
        "artifact_kinds": artifact_kinds,
        "server_call_count": len(server_calls),
        "server_calls": server_calls,
        "transfer_queue_visibility": "passed",
        "stage12c_dataproto_shapes": {
            key: list(value.shape) for key, value in data_proto.batch.items()
            if key in {"prompts", "responses", "response_mask", "rollout_log_probs", "rm_scores", "token_level_rewards", "advantages", "returns"}
        },
        "stage12c_dataproto_visibility": "passed",
        "stage12c_postprocessed_extra_fields_contains_raw_prompt": "raw_prompt" in internal.extra_fields,
        "stage12c_advantage_estimator": "GRPO",
        "stage12c_policy_loss": float(policy_loss.detach().cpu()),
        "stage12c_policy_metrics": {key: float(value.detach().cpu()) if hasattr(value, "detach") else float(value) for key, value in policy_metrics.items()},
        "stage12c_loss_path": "compute_advantage_GRPO + compute_policy_loss_vanilla",
    }


def main() -> None:
    os.environ.setdefault("HF_HOME", "/workspace/hf_cache")
    os.environ.setdefault("TRANSFORMERS_CACHE", "/workspace/hf_cache")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    try:
        summary = asyncio.run(_run(tokenizer))
        _write_summary(summary)
    except Exception as exc:
        payload = {
            "schema_version": "repo_harness_stage12b_real_episode_smoke_summary_v0",
            "status": "failed",
            "failure_type": exc.__class__.__name__,
            "failure_message": str(exc),
            "run_root": str(RUN_ROOT),
            "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        }
        _write_summary(payload)
        raise
    finally:
        if ray.is_initialized():
            ray.shutdown()


if __name__ == "__main__":
    main()
