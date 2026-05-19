"""RepoHarness AgentLoop adapter for verl."""

from __future__ import annotations

import asyncio
from typing import Any

from repo_harness.rl import RepoHarnessRuntime, RepoHarnessRuntimeOptions

from .conversion import VerlConversionError, episode_result_to_agent_loop_output
from .errors import RepoHarnessVerlAdapterError, RepoHarnessVerlRequestMappingError
from .gateway import VerlLLMGateway
from .request_mapping import build_episode_request_from_verl_kwargs, validate_repo_harness_verl_kwargs

try:
    from verl.experimental.agent_loop.agent_loop import AgentLoopBase, register
except Exception as exc:  # pragma: no cover - exercised by environment preflight.
    raise RepoHarnessVerlAdapterError(
        "failed_to_import_verl_agent_loop_base; expose reference/verl and its dependencies before importing "
        "repo_harness_verl.agent_loop"
    ) from exc


@register("repo_harness")
class RepoHarnessVerlAgentLoop(AgentLoopBase):
    """通过 verl AgentLoopBase 调用 RepoHarnessRuntime.run_episode(...)。"""

    def __init__(
        self,
        *args: Any,
        runtime: RepoHarnessRuntime | None = None,
        runtime_options: RepoHarnessRuntimeOptions | None = None,
        inference_backend: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.runtime = runtime or RepoHarnessRuntime(options=runtime_options)
        self.repo_harness_inference_backend = inference_backend

    async def run(self, sampling_params: dict[str, Any], **kwargs: Any) -> Any:
        """从 verl 样本字段构造 RepoHarness episode，并返回真实 AgentLoopOutput。"""

        try:
            validated_kwargs = validate_repo_harness_verl_kwargs(kwargs)
            request = build_episode_request_from_verl_kwargs(
                validated_kwargs,
                sampling_params=sampling_params,
                trainer_config=self.config,
                rollout_config=self.rollout_config,
                inference_backend=self.repo_harness_inference_backend,
            )
            gateway = VerlLLMGateway(
                server_manager=self.server_manager,
                tokenizer=self.tokenizer,
                processor=self.processor,
                inference_backend=request.inference_backend,
                sampling_params=sampling_params,
                prompt_ids_builder=self._build_prompt_ids_for_gateway_request,
            )
            result = await self.runtime.run_episode(request, llm_gateway=gateway)
            try:
                return episode_result_to_agent_loop_output(
                    result,
                    formal_online_rl=True,
                    rollout_prompt_length=_optional_int_config(self.rollout_config, "prompt_length"),
                    rollout_response_length=_optional_int_config(self.rollout_config, "response_length"),
                )
            except VerlConversionError as exc:
                diagnostics = [
                    f"{diagnostic.code}: {diagnostic.message}"
                    for diagnostic in result.audit_diagnostics[:5]
                ]
                raise RepoHarnessVerlAdapterError(
                    "episode_result_not_formal_online_rl: "
                    f"episode_id={result.episode_id} "
                    f"run_id={result.run_id} "
                    f"status={result.status} "
                    f"status_reason={result.status_reason} "
                    f"diagnostics={diagnostics}: {exc}"
                ) from exc
        except RepoHarnessVerlRequestMappingError:
            raise

    async def _build_prompt_ids_for_gateway_request(self, request: Any) -> list[int]:
        from verl.utils.chat_template import apply_chat_template
        from verl.utils.tokenizer import normalize_token_ids

        loop = asyncio.get_running_loop()
        tools = list(request.tools) if request.tools else None
        if self.processor is not None:
            raw_prompt = await loop.run_in_executor(
                None,
                lambda: apply_chat_template(
                    self.processor,
                    list(request.messages),
                    tools=tools,
                    add_generation_prompt=True,
                    tokenize=False,
                    **self.apply_chat_template_kwargs,
                ),
            )
            model_inputs = self.processor(
                text=[raw_prompt],
                images=None,
                videos=None,
                video_metadata=None,
                return_tensors="pt",
                do_sample_frames=False,
            )
            return list(normalize_token_ids(model_inputs.pop("input_ids")))
        tokenized_prompt = await loop.run_in_executor(
            None,
            lambda: apply_chat_template(
                self.tokenizer,
                list(request.messages),
                tools=tools,
                add_generation_prompt=True,
                tokenize=True,
                **self.apply_chat_template_kwargs,
            ),
        )
        return list(normalize_token_ids(tokenized_prompt))


def _optional_int_config(config: Any, key: str) -> int | None:
    if config is None:
        return None
    value = config.get(key) if isinstance(config, dict) else getattr(config, key, None)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
