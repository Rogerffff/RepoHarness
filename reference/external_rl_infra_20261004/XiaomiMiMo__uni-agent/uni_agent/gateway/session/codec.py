"""Model-scoped codec for tokenizer, processor, tool-parser, and decode paths.

This layer stays within the model boundary: it applies chat templates, handles
processor-backed multimodal inputs, parses tools, and decodes backend outputs.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import logging
import re
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from verl.utils.tokenizer import normalize_token_ids
from verl.utils.tokenizer.chat_template import apply_chat_template as _apply_chat_template
from verl.utils.tokenizer.chat_template import initialize_turn_separator


logger = logging.getLogger(__name__)

# Map backend stop_reason values into the gateway's internal finish_reason vocabulary.
_FINISH_REASON_MAP = {
    "completed": "stop",
    "stop": "stop",
    "matched_stop": "stop",
    "eos": "stop",
    "length": "length",
    "max_tokens": "length",
    "aborted": "stop",
    "abort": "stop",
}

_SGLANG_TOOL_PARSER_ALIASES = {
    "qwen3_xml": "qwen3_coder",
}

_VLLM_TOOL_PARSER_ALIASES = {
    "qwen": "qwen3_xml",
    "qwen25": "qwen3_xml",
    "qwen3": "qwen3_xml",
}

_FREEFORM_PROBE_NAME = "__uni_agent_freeform_probe__"
_FREEFORM_PROBE_BODY = "__uni_agent_freeform_body__"
_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
_FUNCTION_BLOCK_RE = re.compile(r"<function=([^>]+)>(.*?)</function>", re.DOTALL)


class ToolParserPayloadError(ValueError):
    """The selected parser rejected model-generated tool payload bytes."""


def _is_missing_optional_backend(exc: ModuleNotFoundError, root: str) -> bool:
    """Return whether an optional backend itself (rather than its dependency) is absent."""
    missing = exc.name
    return missing == root or (isinstance(missing, str) and missing.startswith(f"{root}."))


def _canonical_tools_hash(tools: list[dict[str, Any]]) -> str:
    """Return a stable hash for a tool schema independent of dict key order."""
    canonical = json.dumps(tools, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def initialize_generation_prompt(processing_class, **apply_chat_template_kwargs) -> list[int]:
    """Initialize the token suffix inserted by ``add_generation_prompt=True``."""
    without_generation_prompt = normalize_token_ids(
        _apply_chat_template(
            processing_class,
            [{"role": "user", "content": ""}],
            add_generation_prompt=False,
            **apply_chat_template_kwargs,
        )
    )
    with_generation_prompt = normalize_token_ids(
        _apply_chat_template(
            processing_class,
            [{"role": "user", "content": ""}],
            add_generation_prompt=True,
            **apply_chat_template_kwargs,
        )
    )
    if with_generation_prompt[: len(without_generation_prompt)] != without_generation_prompt:
        raise ValueError("Generation prompt is not a stable token suffix")
    return with_generation_prompt[len(without_generation_prompt) :]


def _split_generation_thinking(text: str, *, prompt_opens_thinking: bool) -> tuple[str | None, str]:
    """Normalize model text when a chat template owns the think opening tag.

    Qwen3.5 appends ``<think>`` to the generation prompt, so its completion
    starts with reasoning and normally contains only ``</think>``. Other
    templates (including MiMo-V2) leave both tags to the model. Keep this
    helper model-agnostic and fail open on malformed output so no generated
    text is silently discarded.
    """
    if not isinstance(text, str) or not text:
        return None, text or ""

    if prompt_opens_thinking:
        opening = "<think>"
        if text.startswith(opening):
            text = text[len(opening) :]
        close = text.find("</think>")
        if close < 0:
            return None, text
        reasoning = text[:close].rstrip("\n")
        content = text[close + len("</think>") :].lstrip("\n")
        return reasoning or None, content

    if text.startswith("<think>"):
        close = text.find("</think>", len("<think>"))
        if close < 0:
            return None, text
        reasoning = text[len("<think>") : close].strip("\n")
        content = text[close + len("</think>") :].lstrip("\n")
        return reasoning or None, content
    return None, text


def _canonicalize_tool_arguments_for_comparison(arguments: Any) -> tuple[str, Any]:
    if isinstance(arguments, dict | list):
        canonical: tuple[str, Any] = ("json", arguments)
    elif isinstance(arguments, str):
        try:
            canonical = ("json", json.loads(arguments))
        except json.JSONDecodeError:
            canonical = ("raw", arguments)
    else:
        canonical = ("raw", arguments)

    if canonical[0] == "json" and isinstance(canonical[1], dict) and set(canonical[1]) == {"input"}:
        return _canonicalize_tool_arguments_for_comparison(canonical[1]["input"])
    return canonical


def _custom_exec_parameters() -> dict[str, Any]:
    """Return Qwen's single-string view of Codex's custom exec input.

    ``input`` is intentionally unconstrained text: Codex may send JavaScript
    that composes multiple ``tools.xxx`` calls, not just one shell command.
    The surrounding function/parameter envelope keeps Qwen's stock template
    and parser usable without reducing the payload to ``cmd`` only.
    """
    return {
        "type": "object",
        "properties": {
            "input": {"type": "string"},
        },
        "required": ["input"],
        "additionalProperties": False,
    }


def _supports_freeform_tool_calls(processing_class) -> bool:
    """Probe whether the active Jinja renders ``tool_call.input`` verbatim."""
    probe = [
        {"role": "user", "content": "__uni_agent_probe_user__"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"name": _FREEFORM_PROBE_NAME, "input": _FREEFORM_PROBE_BODY}],
        },
    ]
    try:
        rendered = processing_class.apply_chat_template(
            probe,
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception:
        return False
    return f"<function={_FREEFORM_PROBE_NAME}>{_FREEFORM_PROBE_BODY}</function>" in rendered


def _supports_developer_role(processing_class) -> bool:
    """Probe whether the active Jinja accepts ``developer`` messages."""
    try:
        rendered = processing_class.apply_chat_template(
            [
                {"role": "developer", "content": "__uni_agent_developer_probe__"},
                {"role": "user", "content": "__uni_agent_probe_user__"},
            ],
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception:
        return False
    return "<|im_start|>developer" in rendered or "developer:" in rendered


def _parser_tool_view(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project prompt-facing tools onto parser schemas without changing prompt bytes."""
    view: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict) or isinstance(tool.get("function"), dict):
            view.append(tool)
            continue
        tool_name = tool.get("name") or tool.get("type")
        if tool.get("type") == "custom":
            parameters = _custom_exec_parameters()
        else:
            parameters = tool.get("parameters") or {"type": "object", "properties": {}}
        view.append(
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool.get("description") or "",
                    "parameters": parameters,
                },
            }
        )
    return view


def _prompt_tool_view(
    tools: list[dict[str, Any]] | None,
    *,
    freeform_tool_calls: bool = False,
) -> list[dict[str, Any]] | None:
    """Return the model-facing tool declarations for the active Jinja contract.

    MiMo-v2.6 keeps flat ``custom`` declarations. Older Qwen templates need a
    synthetic function schema, so the fallback remains available for legacy
    checkpoints but is never used for the canonical v2.6 template.
    """
    if tools is None:
        return None
    if freeform_tool_calls:
        return tools
    view: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict) or isinstance(tool.get("function"), dict):
            view.append(tool)
            continue
        if tool.get("type") != "custom":
            view.append(tool)
            continue
        name = tool.get("name")
        description = str(tool.get("description") or "")
        view.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": _custom_exec_parameters() if name == "exec" else {
                        "type": "object",
                        "properties": {"input": {"type": "string"}},
                        "required": ["input"],
                        "additionalProperties": False,
                    },
                },
            }
        )
    return view


def _freeform_call_input(arguments: Any) -> str:
    """Unwrap the internal ``{"input": raw}`` envelope for v2.6 Jinja."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
    if isinstance(arguments, dict) and len(arguments) == 1 and isinstance(arguments.get("input"), str):
        return arguments["input"]
    if isinstance(arguments, str):
        return arguments
    return json.dumps(arguments, ensure_ascii=False) if arguments is not None else ""


def _tool_name(tool: Any) -> str | None:
    if not isinstance(tool, dict):
        return None
    if isinstance(tool.get("function"), dict):
        name = tool["function"].get("name")
        return str(name) if name else None
    name = tool.get("name") or tool.get("type")
    return str(name) if name else None


def _assistant_history_message(
    message: dict[str, Any],
    tools: list[dict[str, Any]] | None,
    *,
    freeform_tool_calls: bool,
) -> dict[str, Any]:
    """Convert stored Chat-style tool calls into the active Jinja contract."""
    normalized = dict(message)
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return normalized

    custom_names = {
        _tool_name(tool)
        for tool in tools or []
        if isinstance(tool, dict) and tool.get("type") == "custom"
    }
    rendered_calls: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function")
        if not isinstance(function, dict):
            function = tool_call.get("custom") if isinstance(tool_call.get("custom"), dict) else tool_call
        name = function.get("name") if isinstance(function, dict) else None
        if not isinstance(name, str) or not name:
            continue
        arguments = function.get("arguments") if isinstance(function, dict) else None
        is_custom = tool_call.get("type") == "custom" or name in custom_names or "input" in tool_call
        if is_custom:
            raw_input = _freeform_call_input(
                tool_call.get("input") if "input" in tool_call else arguments
            )
            if freeform_tool_calls:
                rendered_calls.append({"name": name, "input": raw_input})
            else:
                rendered_calls.append({"name": name, "arguments": {"input": raw_input}})
        elif isinstance(arguments, dict):
            rendered_calls.append({"name": name, "arguments": arguments})
        else:
            rendered_calls.append(
                {"name": name, "arguments": {"arguments": _freeform_call_input(arguments)}}
            )
    if rendered_calls:
        normalized["tool_calls"] = rendered_calls
    else:
        normalized.pop("tool_calls", None)
    return normalized


def _prompt_message_view(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    *,
    freeform_tool_calls: bool = False,
    supports_developer: bool = True,
) -> list[dict[str, Any]]:
    """Project semantic messages onto the active Jinja message contract."""
    projected: list[dict[str, Any]] = []
    changed = False
    for message in messages:
        if message.get("role") == "assistant":
            view = _assistant_history_message(message, tools, freeform_tool_calls=freeform_tool_calls)
            changed = changed or view != message
        else:
            view = message
        projected.append(view)
    if supports_developer:
        return projected if changed else messages

    system_parts: list[str] = []
    non_system: list[dict[str, Any]] = []
    for message in projected:
        if message.get("role") in {"system", "developer"}:
            content = message.get("content")
            if isinstance(content, str) and content:
                system_parts.append(content)
        else:
            non_system.append(message)
    if not system_parts:
        return projected if changed else messages
    return [{"role": "system", "content": "\n\n".join(system_parts)}, *non_system]


def _flatten_message_tools_for_parser(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten message-level discovered tools only for parser construction."""
    flattened: list[dict[str, Any]] = []

    def visit(tool: Any, namespace: str | None = None) -> None:
        if not isinstance(tool, dict):
            return
        if tool.get("type") == "namespace":
            container = str(tool.get("name") or "").strip()
            next_namespace = None if container in ("", "functions") else container
            for nested in tool.get("tools") or []:
                visit(nested, next_namespace)
            return
        source = tool.get("function") if isinstance(tool.get("function"), dict) else tool
        name = source.get("name") or tool.get("type")
        if not isinstance(name, str) or not name:
            return
        declaration = dict(tool)
        if namespace and isinstance(source.get("name"), str):
            declaration["name"] = f"{namespace}__{source['name']}"
        flattened.append(declaration)

    for message in messages:
        for tool in message.get("tools") or []:
            visit(tool)
    return flattened


async def _extract_tool_calls(
    response_ids: list[int],
    tools: list[dict[str, Any]],
    parser_name: str,
    tokenizer,
) -> tuple[str, list[Any]]:
    """Compatibility dispatcher for flat Responses custom-tool requests."""
    text = tokenizer.decode(response_ids, skip_special_tokens=False)
    sglang_name = _SGLANG_TOOL_PARSER_ALIASES.get(parser_name, parser_name)
    try:
        from sglang.srt.entrypoints.openai.protocol import Function as SglFunction
        from sglang.srt.entrypoints.openai.protocol import Tool as SglTool
        from sglang.srt.function_call.function_call_parser import FunctionCallParser
    except ModuleNotFoundError as exc:
        if not _is_missing_optional_backend(exc, "sglang"):
            raise
    else:
        sglang_tools = [SglTool(type=tool["type"], function=SglFunction(**tool["function"])) for tool in tools]
        parser = FunctionCallParser(sglang_tools, sglang_name)
        try:
            has_tool_call = parser.has_tool_call(text)
        except ValueError as exc:
            raise ToolParserPayloadError("SGLang rejected the model tool payload") from exc
        if not has_tool_call:
            return text, []
        try:
            content, calls = parser.parse_non_stream(text)
        except ValueError as exc:
            raise ToolParserPayloadError("SGLang rejected the model tool payload") from exc
        return content, [SimpleNamespace(name=call.name, arguments=call.parameters) for call in calls]

    vllm_name = _VLLM_TOOL_PARSER_ALIASES.get(parser_name, parser_name)
    try:
        from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionToolsParam
        from vllm.tool_parsers import ToolParserManager
    except ModuleNotFoundError as exc:
        if not _is_missing_optional_backend(exc, "vllm"):
            raise
    else:
        parser_cls = ToolParserManager.get_tool_parser(vllm_name)
        vllm_tools = [ChatCompletionToolsParam(**tool) for tool in tools]
        parser_parameters = inspect.signature(parser_cls).parameters
        parser = parser_cls(tokenizer, tools=vllm_tools) if "tools" in parser_parameters else parser_cls(tokenizer)
        request = SimpleNamespace(tools=vllm_tools, tool_choice="auto", skip_special_tokens=True)
        try:
            parsed = parser.extract_tool_calls(text, request)
        except ValueError as exc:
            raise ToolParserPayloadError("vLLM rejected the model tool payload") from exc
        if not parsed.tools_called:
            return text, []
        return parsed.content or "", [tool_call.function for tool_call in parsed.tool_calls]

    from verl.experimental.agent_loop.tool_parser import ToolParser
    from verl.tools.schemas import OpenAIFunctionToolSchema

    parser = ToolParser.get_tool_parser(parser_name, tokenizer)
    tool_schemas = [OpenAIFunctionToolSchema.model_validate(tool) for tool in tools]
    try:
        content, calls = await parser.extract_tool_calls(response_ids, tool_schemas)
    except ValueError as exc:
        raise ToolParserPayloadError("VERL rejected the model tool payload") from exc
    return content, [SimpleNamespace(name=call.name, arguments=call.arguments) for call in calls]


class MessageCodec:
    """Model-scoped request codec used by gateway sessions.

    ``_GatewayActor`` owns one codec per actor and injects it into
    ``GatewaySession`` instances. The codec renders chat templates, handles
    multimodal processor inputs, and decodes backend token outputs without
    reading session state.
    """

    def __init__(
        self,
        tokenizer,
        *,
        processor=None,
        vision_info_extractor=None,
        vision_info_extractor_kwargs: dict[str, Any] | None = None,
        tool_parser_name: str | None = None,
        rollout_backend: str | None = None,
        enable_tool_parser_cache: bool = True,
        apply_chat_template_kwargs: dict[str, Any] | None = None,
    ):
        self._tokenizer = tokenizer
        self._processor = processor
        self._vision_info_extractor = vision_info_extractor or self._default_vision_info_extractor
        self._vision_info_extractor_kwargs = dict(vision_info_extractor_kwargs or {})
        self._apply_chat_template_kwargs = dict(apply_chat_template_kwargs or {})
        processing_class = self._processor if self._processor is not None else tokenizer
        self._freeform_tool_calls = _supports_freeform_tool_calls(processing_class)
        self._supports_developer = _supports_developer_role(processing_class)
        self._generation_prompt = initialize_generation_prompt(
            processing_class,
            **self._apply_chat_template_kwargs,
        )
        generation_prompt_text = self._tokenizer.decode(
            self._generation_prompt,
            skip_special_tokens=False,
        )
        self._generation_prompt_opens_thinking = (
            "<think>" in generation_prompt_text and "</think>" not in generation_prompt_text
        )
        self._turn_separator = initialize_turn_separator(
            processing_class,
            **self._apply_chat_template_kwargs,
        )
        self._tool_parser_name = tool_parser_name
        self._rollout_backend = rollout_backend
        self._enable_tool_parser_cache = enable_tool_parser_cache
        # Backend parser construction performs expensive setup, so reuse parsers
        # within this actor-scoped codec. SGLang/vLLM bind tool schemas at
        # construction, while verl receives schemas per extraction call; this is
        # why their cache keys differ. Keep the cache codec-scoped because parser
        # instances may retain mutable request state and dynamic schemas can grow
        # the mapping over the codec lifetime. Callers can disable this
        # optimization for parser implementations that require request-scoped
        # instances.
        self._tool_parser_cache: dict[tuple[str, ...], Any] = {}

    @property
    def generation_prompt(self) -> list[int]:
        """Return the configured chat template's generation-prompt token suffix."""
        return list(self._generation_prompt)

    @property
    def turn_separator(self) -> list[int]:
        """Return the configured chat template's inter-turn separator tokens."""
        return list(self._turn_separator)

    async def _default_vision_info_extractor(
        self,
        messages: list[dict[str, Any]],
        *,
        image_patch_size: int,
        **_extra: Any,
    ) -> tuple[list[Any] | None, list[Any] | None]:
        # Lazy import so callers without multi-modal needs do not load
        # qwen_vl_utils. ``_extra`` absorbs ``vision_info_extractor_kwargs`` that
        # ``extract_multi_modal_data`` forwards for custom extractors; the
        # default path needs nothing beyond ``messages`` and patch size.
        from qwen_vl_utils import process_vision_info

        extractor_messages: list[dict[str, Any]] = []
        for message in messages:
            projected = dict(message)
            content = message.get("content")
            if isinstance(content, list):
                projected_content: list[Any] = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        image_url = part.get("image_url")
                        if isinstance(image_url, dict):
                            image_url = image_url.get("url")
                        projected_content.append({"type": "image", "image": image_url})
                    elif isinstance(part, dict) and part.get("type") == "video_url":
                        video_url = part.get("video_url")
                        if isinstance(video_url, dict):
                            video_url = video_url.get("url")
                        projected_content.append({"type": "video", "video": video_url})
                    else:
                        projected_content.append(part)
                projected["content"] = projected_content
            extractor_messages.append(projected)

        return process_vision_info(
            extractor_messages,
            image_patch_size=image_patch_size,
            return_video_metadata=True,
        )

    async def extract_multi_modal_data(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[list[Any] | None, list[Any] | None]:
        """Extract image and video inputs when a processor-backed request needs them."""
        if self._processor is None:
            return None, None

        has_multi_modal_blocks = False
        for message in messages:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") in {"image", "image_url", "video", "video_url"}:
                    has_multi_modal_blocks = True
                    break
            if has_multi_modal_blocks:
                break

        if not has_multi_modal_blocks:
            return None, None

        return await self._vision_info_extractor(
            messages,
            image_patch_size=self._processor.image_processor.patch_size,
            **self._vision_info_extractor_kwargs,
        )

    def parser_tools_for_messages(
        self,
        tools: list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        """Add message-level discovered tools to the parser input only."""
        discovered = _flatten_message_tools_for_parser(messages)
        if not discovered:
            return tools
        return list(tools or []) + discovered

    def model_tools_for(self, tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Return the declarations actually supplied to the active Jinja."""
        return _prompt_tool_view(tools, freeform_tool_calls=self._freeform_tool_calls)

    def model_messages_for(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        """Return the history view actually supplied to the active Jinja."""
        return _prompt_message_view(
            messages,
            tools,
            freeform_tool_calls=self._freeform_tool_calls,
            supports_developer=self._supports_developer,
        )

    def _encode_prompt_text(
        self,
        prompt: str,
        image_data: list[Any] | None = None,
        video_data: list[Any] | None = None,
    ) -> list[int]:
        """Encode rendered prompt text with the configured tokenizer or processor."""
        if self._processor is None:
            return normalize_token_ids(self._tokenizer.encode(prompt, add_special_tokens=False))

        videos = video_data
        video_metadata = None
        if videos is not None:
            videos, video_metadata = zip(*videos, strict=False)
            videos, video_metadata = list(videos), list(video_metadata)
        model_inputs = self._processor(
            text=[prompt],
            images=image_data,
            videos=videos,
            video_metadata=video_metadata,
            return_tensors="pt",
            do_sample_frames=False,
        )
        return normalize_token_ids(model_inputs["input_ids"])

    def encode_full(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        image_data: list[Any] | None = None,
        video_data: list[Any] | None = None,
    ) -> list[int]:
        """Encode a full chat history into prompt token IDs."""
        processing_class = self._processor if self._processor is not None else self._tokenizer
        raw_prompt = _apply_chat_template(
            processing_class,
            _prompt_message_view(
                messages,
                tools,
                freeform_tool_calls=self._freeform_tool_calls,
                supports_developer=self._supports_developer,
            ),
            tools=_prompt_tool_view(tools, freeform_tool_calls=self._freeform_tool_calls),
            add_generation_prompt=True,
            tokenize=False,
            **self._apply_chat_template_kwargs,
        )
        return self._encode_prompt_text(raw_prompt, image_data, video_data)

    def supports_incremental(self, messages: list[dict[str, Any]]) -> bool:
        """Return whether ``messages`` can safely extend one stored chain."""
        return not any(message.get("role") == "assistant" for message in messages[1:])

    def encode_incremental(
        self,
        messages: list[dict[str, Any]],
        image_data: list[Any] | None = None,
        video_data: list[Any] | None = None,
    ) -> list[int]:
        """Encode continuation messages using a dummy-user anchored delta."""
        if not messages:
            return []

        processing_class = self._processor if self._processor is not None else self._tokenizer
        anchor_content = [{"type": "text", "text": ""}] if self._processor is not None else ""
        anchor = [{"role": "user", "content": anchor_content}]

        if not self.supports_incremental(messages):
            raise ValueError("An incremental assistant message may only appear first")

        # TODO: Replace this user/tool empty-user fallback with continuous-token merging.
        # A user -> tool anchor is not valid for every chat template.
        anchor_prompt = _apply_chat_template(
            processing_class,
            anchor,
            add_generation_prompt=False,
            tokenize=False,
            **self._apply_chat_template_kwargs,
        )
        full_prompt = _apply_chat_template(
            processing_class,
            anchor
            + _prompt_message_view(
                messages,
                None,
                freeform_tool_calls=self._freeform_tool_calls,
                supports_developer=self._supports_developer,
            ),
            tools=None,
            add_generation_prompt=True,
            tokenize=False,
            **self._apply_chat_template_kwargs,
        )
        prefix_prompt = anchor_prompt
        if self._turn_separator:
            separator_text = self._tokenizer.decode(self._turn_separator, skip_special_tokens=False)
            if not separator_text or not anchor_prompt.endswith(separator_text):
                raise ValueError("Turn separator is not a stable text suffix")
            prefix_prompt = anchor_prompt[: -len(separator_text)]
        if not full_prompt.startswith(prefix_prompt):
            raise ValueError("Incremental chat template is not prefix-stable")
        return self._encode_prompt_text(
            full_prompt[len(prefix_prompt) :],
            image_data,
            video_data,
        )

    def _process_tool_calls_sglang(
        self,
        text: str,
        tools: list[dict[str, Any]],
        parser_name: str,
    ) -> tuple[str, list[Any]]:
        cache_key = ("sglang", parser_name, _canonical_tools_hash(tools))
        parser = self._tool_parser_cache.get(cache_key) if self._enable_tool_parser_cache else None
        if parser is None:
            from sglang.srt.entrypoints.openai.protocol import Function as SglFunction
            from sglang.srt.entrypoints.openai.protocol import Tool as SglTool
            from sglang.srt.function_call.function_call_parser import FunctionCallParser

            sglang_tools = [SglTool(type=tool["type"], function=SglFunction(**tool["function"])) for tool in tools]
            parser = FunctionCallParser(sglang_tools, parser_name)
            if self._enable_tool_parser_cache:
                self._tool_parser_cache[cache_key] = parser

        try:
            has_tool_call = parser.has_tool_call(text)
        except ValueError as exc:
            raise ToolParserPayloadError("SGLang rejected the model tool payload") from exc
        if not has_tool_call:
            return text, []

        blocks = self._sglang_tool_call_blocks(text, tools)
        if not blocks:
            if _TOOL_CALL_BLOCK_RE.search(text) is None and "<tool_call>" in text:
                return self._malformed_tool_call_result(text)
            try:
                content, calls = parser.parse_non_stream(text)
            except ValueError as exc:
                raise ToolParserPayloadError("SGLang rejected the model tool payload") from exc
            return content, [SimpleNamespace(name=call.name, arguments=call.parameters) for call in calls]

        parsed_calls: list[Any] = []
        for start, end, name, body in blocks:
            if self._is_direct_function_body(body):
                parsed_calls.append(
                    SimpleNamespace(
                        name=name,
                        arguments=body if body.strip() else "{}",
                    )
                )
                continue

            try:
                _, regular_calls = parser.parse_non_stream(text[start:end])
            except ValueError as exc:
                raise ToolParserPayloadError("SGLang rejected the model tool payload") from exc
            if regular_calls:
                parsed_calls.extend(
                    SimpleNamespace(name=call.name, arguments=call.parameters)
                    for call in regular_calls
                )
            else:
                declared_names = {
                    (tool.get("function") or {}).get("name")
                    for tool in tools
                    if isinstance(tool, dict) and isinstance(tool.get("function"), dict)
                }
                if name not in declared_names:
                    parsed_calls.append(SimpleNamespace(name=name, arguments=body or "{}"))
                else:
                    parsed_calls.append(self._malformed_tool_call(name, body))

        normal_parts: list[str] = []
        cursor = 0
        for start, end, *_ in blocks:
            normal_parts.append(text[cursor:start])
            cursor = end
        normal_parts.append(text[cursor:])
        result = "".join(normal_parts), parsed_calls

        last_end = blocks[-1][1]
        unmatched = text.find("<tool_call>", last_end)
        if unmatched >= 0:
            result = (
                result[0][:unmatched],
                result[1] + [self._malformed_tool_call_from_text(text[unmatched:])],
            )
        return result

    @staticmethod
    def _malformed_tool_call(name: str, body: str) -> SimpleNamespace:
        del name
        return SimpleNamespace(
            name="__malformed_tool_call__",
            arguments=json.dumps(
                {"error": "malformed or incomplete tool call", "raw_body": body},
                ensure_ascii=False,
            ),
        )

    @classmethod
    def _malformed_tool_call_from_text(cls, text: str) -> SimpleNamespace:
        function_match = _FUNCTION_BLOCK_RE.search(text)
        if function_match is None:
            return cls._malformed_tool_call("", text)
        return cls._malformed_tool_call(function_match.group(1).strip(), function_match.group(2))

    @classmethod
    def _malformed_tool_call_result(cls, text: str) -> tuple[str, list[SimpleNamespace]]:
        start = text.find("<tool_call>")
        return text[:start], [cls._malformed_tool_call_from_text(text[start:])]

    @staticmethod
    def _is_direct_function_body(body: str) -> bool:
        """Recognize a body placed directly inside ``<function=...>``.

        The stock Qwen3-Coder detector only reads ``<parameter=...>`` tags. A
        model using the v2.6 MiMo template may instead place a complete JSON
        object, JavaScript, or another raw payload directly inside
        ``<function=...>``. Keep it as-is and let the harness perform the final
        object/schema validation. Returning malformed text preserves a useful
        format error rather than irreversibly replacing the model payload with
        ``{}``.
        """
        stripped = body.strip()
        if not stripped or "<parameter=" in stripped:
            return False
        return True

    @staticmethod
    def _sglang_tool_call_blocks(
        text: str,
        tools: list[dict[str, Any]],
    ) -> list[tuple[int, int, str, str]]:
        """Return ordered complete ``<tool_call>`` blocks.

        The parser-facing tool schema is intentionally irrelevant here. The
        body shape determines the dialect: parameter-tag bodies go through the
        stock SGLang parser, while direct bodies are retained verbatim for the
        harness (ordinary JSON and custom/freeform payloads alike).
        """
        blocks: list[tuple[int, int, str, str]] = []
        for match in _TOOL_CALL_BLOCK_RE.finditer(text):
            function_match = _FUNCTION_BLOCK_RE.search(match.group(1))
            if function_match is None:
                continue
            name = function_match.group(1).strip()
            body = function_match.group(2)
            blocks.append((match.start(), match.end(), name, body))
        return blocks

    def _process_tool_calls_vllm(
        self,
        text: str,
        tools: list[dict[str, Any]],
        parser_name: str,
    ) -> tuple[str, list[Any]]:
        from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionToolsParam

        cache_key = ("vllm", parser_name, _canonical_tools_hash(tools))
        parser = self._tool_parser_cache.get(cache_key) if self._enable_tool_parser_cache else None
        vllm_tools = [ChatCompletionToolsParam(**tool) if isinstance(tool, dict) else tool for tool in tools]
        if parser is None:
            from vllm.tool_parsers import ToolParserManager

            parser_cls = ToolParserManager.get_tool_parser(parser_name)
            parser_parameters = inspect.signature(parser_cls).parameters
            if "tools" in parser_parameters:
                parser = parser_cls(self._tokenizer, tools=vllm_tools)
            else:
                parser = parser_cls(self._tokenizer)
            if self._enable_tool_parser_cache:
                self._tool_parser_cache[cache_key] = parser

        request = SimpleNamespace(tools=vllm_tools, tool_choice="auto", skip_special_tokens=True)
        parsed = parser.extract_tool_calls(text, request)
        if not parsed.tools_called:
            return text, []
        return parsed.content or "", [tool_call.function for tool_call in parsed.tool_calls]

    async def _process_tool_calls_verl(
        self,
        response_ids: list[int],
        tools: list[dict[str, Any]],
        parser_name: str,
    ) -> tuple[str, list[Any]]:
        """Parse tool calls with verl's built-in tool-parser registry."""
        from verl.experimental.agent_loop.tool_parser import ToolParser
        from verl.tools.schemas import OpenAIFunctionToolSchema

        cache_key = ("verl", parser_name)
        parser = self._tool_parser_cache.get(cache_key) if self._enable_tool_parser_cache else None
        if parser is None:
            parser = ToolParser.get_tool_parser(parser_name, self._tokenizer)
            if self._enable_tool_parser_cache:
                self._tool_parser_cache[cache_key] = parser

        tool_schemas = [OpenAIFunctionToolSchema.model_validate(tool) for tool in tools]
        content, calls = await parser.extract_tool_calls(response_ids, tool_schemas)
        return content, [SimpleNamespace(name=call.name, arguments=call.arguments) for call in calls]

    async def _extract_tool_calls(
        self,
        response_ids: list[int],
        tools: list[dict[str, Any]],
        parser_name: str,
    ) -> tuple[str, list[Any]]:
        original_tools = tools
        tools = _parser_tool_view(tools)
        text = self._tokenizer.decode(response_ids, skip_special_tokens=False)
        parser_backend = self._rollout_backend if self._rollout_backend in {"sglang", "vllm"} else "verl"

        try:
            if parser_backend == "verl" and tools != original_tools:
                result = await _extract_tool_calls(
                    response_ids,
                    tools,
                    parser_name,
                    self._tokenizer,
                )
            elif parser_backend == "sglang":
                sglang_name = _SGLANG_TOOL_PARSER_ALIASES.get(parser_name, parser_name)
                result = self._process_tool_calls_sglang(text, tools, sglang_name)
            elif parser_backend == "vllm":
                vllm_name = _VLLM_TOOL_PARSER_ALIASES.get(parser_name, parser_name)
                result = self._process_tool_calls_vllm(text, tools, vllm_name)
            elif parser_backend == "verl":
                result = await self._process_tool_calls_verl(response_ids, tools, parser_name)

            try:
                self._validate_tool_call_names(result[1], original_tools)
            except ValueError as exc:
                logger.warning(
                    "Forwarding undeclared tool calls to harness: %s",
                    exc,
                )
            if not result[1] and self._has_malformed_tool_envelope(text):
                return self._malformed_tool_call_result(text)
            return result
        except ToolParserPayloadError as exc:
            if _TOOL_CALL_BLOCK_RE.search(text) or "<tool_call>" in text:
                logger.warning(
                    "Tool parser %r rejected model payload; forwarding malformed feedback",
                    parser_name,
                )
                return self._malformed_tool_call_result(text)
            raise RuntimeError(f"{parser_backend} tool parser {parser_name!r} rejected payload") from exc
        except ImportError as exc:
            raise RuntimeError(f"{parser_backend} tool parser {parser_name!r} failed") from exc
        except Exception as exc:
            logger.warning(
                "Tool parser %r failed for %s backend",
                parser_name,
                parser_backend,
                exc_info=True,
            )
            raise RuntimeError(f"{parser_backend} tool parser {parser_name!r} failed") from exc

    @staticmethod
    def _has_malformed_tool_envelope(text: str) -> bool:
        """Detect an incomplete XML tool envelope without parsing arguments."""
        if text.count("<tool_call>") > text.count("</tool_call>"):
            return True
        for match in _TOOL_CALL_BLOCK_RE.finditer(text):
            inner = match.group(1)
            if "<function=" in inner and _FUNCTION_BLOCK_RE.search(inner) is None:
                return True
        return "<tool_call>" in text and text.count("<function=") > text.count("</function>")

    @staticmethod
    def _validate_tool_call_names(function_calls: list[Any], tools: list[dict[str, Any]]) -> None:
        """Reject parser calls that were not declared by the client."""
        declared: set[str] = set()

        def visit(tool: Any, namespace: str | None = None) -> None:
            if not isinstance(tool, dict):
                return
            if tool.get("type") == "namespace":
                container = str(tool.get("name") or "").strip()
                next_namespace = None if container in ("", "functions") else container
                for nested in tool.get("tools") or []:
                    visit(nested, next_namespace)
                return
            source = tool.get("function") if isinstance(tool.get("function"), dict) else tool
            name = source.get("name") or tool.get("type")
            if isinstance(name, str) and name:
                declared.add(f"{namespace}__{name}" if namespace else name)

        for tool in tools or []:
            visit(tool)
        unknown = sorted(
            str(call.name)
            for call in function_calls or []
            if getattr(call, "name", None) not in declared
        )
        if unknown:
            raise ValueError(f"Undeclared tool call(s): {', '.join(unknown)}")

    async def decode_response(
        self,
        response_ids: list[int],
        *,
        tools: list[dict[str, Any]] | None = None,
        parser_tools: list[dict[str, Any]] | None = None,
        stop_reason: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Decode model output tokens into an assistant message and finish reason."""
        parser_tools = parser_tools or tools
        if self._tool_parser_name and parser_tools:
            content, function_calls = await self._extract_tool_calls(
                response_ids,
                parser_tools,
                self._tool_parser_name,
            )
            if function_calls:
                custom_names = {
                    _tool_name(tool)
                    for tool in tools or []
                    if isinstance(tool, dict) and tool.get("type") == "custom"
                }
                tool_calls = [
                    {
                        "id": f"call_{uuid4().hex[:8]}",
                        "type": "custom" if fc.name in custom_names else "function",
                        "function": {"name": fc.name, "arguments": fc.arguments},
                    }
                    for fc in function_calls
                ]
                reasoning, visible_content = _split_generation_thinking(
                    self._strip_trailing_stop_token(content or ""),
                    prompt_opens_thinking=self._generation_prompt_opens_thinking,
                )
                message = {
                    "role": "assistant",
                    "content": visible_content,
                    "tool_calls": tool_calls,
                }
                if reasoning:
                    message["reasoning_content"] = reasoning
                return message, "tool_calls"
        response_text = self._tokenizer.decode(response_ids, skip_special_tokens=True)
        reasoning, visible_content = _split_generation_thinking(
            response_text,
            prompt_opens_thinking=self._generation_prompt_opens_thinking,
        )
        finish_reason = _FINISH_REASON_MAP.get(stop_reason, stop_reason) if stop_reason else "stop"
        message: dict[str, Any] = {"role": "assistant", "content": visible_content}
        if reasoning:
            message["reasoning_content"] = reasoning
        return message, finish_reason

    def _strip_trailing_stop_token(self, content: str) -> str:
        """Drop the EOS / stop token text that closes a tool-call generation.

        The tool-call branch decodes with ``skip_special_tokens=False`` so the
        template-owned ``<think>`` tags survive for ``_split_generation_thinking``,
        but that also keeps the generation's closing ``<|im_end|>`` in the text
        the backend parser returns next to the ``<tool_call>`` blocks. Left in
        place it reaches every client as visible content (measured:
        99% of tool-calling assistant turns across Claude Code / Codex / pi /
        opencode and the whitebox harnesses carried a literal ``<|im_end|>``),
        and a client that replays that history is re-tokenized into a second
        EOS inside the assistant turn whenever the session falls back to a full
        encode. The no-tool branch already decodes with ``skip_special_tokens=True``.
        """
        eos = getattr(self._tokenizer, "eos_token", None)
        if not isinstance(eos, str) or not eos.strip():
            return content
        stripped = content.rstrip()
        while stripped.endswith(eos):
            stripped = stripped[: -len(eos)].rstrip()
        return stripped if stripped != content.rstrip() else content

    def canonicalize_message_for_prefix_comparison(self, message: dict[str, Any]) -> dict[str, Any]:
        """Canonicalize one message before session prefix comparison."""
        normalized = dict(message)
        normalized.pop("tool_call_id", None)
        tool_calls = normalized.get("tool_calls")
        if not isinstance(tool_calls, list):
            return normalized

        normalized_tool_calls: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            normalized_tool_call = dict(tool_call)
            normalized_tool_call.pop("id", None)
            normalized_tool_call["type"] = "function"
            function = normalized_tool_call.get("function")
            if isinstance(function, dict) and "arguments" in function:
                normalized_function = dict(function)
                normalized_function["arguments"] = _canonicalize_tool_arguments_for_comparison(
                    function["arguments"]
                )
                normalized_tool_call["function"] = normalized_function
            normalized_tool_calls.append(normalized_tool_call)
        normalized["tool_calls"] = normalized_tool_calls
        return normalized
