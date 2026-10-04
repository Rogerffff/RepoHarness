"""OpenAI Responses wire protocol adapter for gateway sessions."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from fastapi.responses import StreamingResponse

from uni_agent.gateway.session.session import GenerationOutcome
from uni_agent.gateway.session.types import InternalGenerationRequest

from .openai import openai_to_internal
from .types import MalformedRequestError

logger = logging.getLogger("gateway")

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
_TEXT_BLOCK_TYPES = {"input_text", "output_text", "reasoning_text", "summary_text", "text"}
_NAMESPACE_SEPARATOR = "__"
_DEFAULT_NAMESPACE = "functions"
_SKIPPED_ITEM_TYPES = {"compaction_trigger", "context_compaction"}
_HOSTED_TOOL_TYPES = {
    "apply_patch",
    "computer",
    "computer_use_preview",
    "image_generation",
    "shell",
    "tool_search",
    "web_search",
    "web_search_preview",
}
_IGNORED_TOOL_TYPES = {"code_interpreter", "file_search", "local_shell"}

def responses_error_body(status_code: int, message: str, *, param: str | None = None) -> dict[str, Any]:
    return {
        "error": {
            "message": message,
            "type": "invalid_request_error" if 400 <= status_code < 500 else "internal_server_error",
            "code": None,
            "param": param,
        }
    }


def _content_to_text(content: Any, *, param: str) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_content_to_text(part, param=param) for part in content)
    if isinstance(content, dict):
        if "output" in content:
            return _content_to_text(content["output"], param=param)
        block_type = content.get("type")
        if block_type in _TEXT_BLOCK_TYPES or block_type is None:
            return _content_to_text(content.get("text", content.get("content", "")), param=param)
        if block_type == "encrypted_content":
            value = content.get("encrypted_content", "")
            return value if isinstance(value, str) else str(value)
        if block_type == "input_image":
            return "[Image omitted]"
        salvaged = content.get("text", content.get("content", content.get("refusal")))
        if salvaged is not None:
            return _content_to_text(salvaged, param=param)
        logger.warning("Dropping unknown Responses content block %r at %s", block_type, param)
        return ""
    if isinstance(content, int | float | bool):
        return str(content)
    raise MalformedRequestError(f"Unsupported content value at {param}: {type(content).__name__}")


def _content_to_chat_content(content: Any, *, param: str) -> Any:
    """Preserve Responses images as Chat image parts for the VL processor."""
    blocks = content if isinstance(content, list) else [content]
    parts: list[dict[str, Any]] = []
    has_image = False
    for index, block in enumerate(blocks):
        block_param = f"{param}[{index}]"
        if isinstance(block, dict) and block.get("type") == "input_image":
            image_url = block.get("image_url", block.get("url"))
            if isinstance(image_url, dict):
                image_url = image_url.get("url")
            if not image_url:
                data = block.get("data") or block.get("image_data")
                if isinstance(data, str) and data:
                    mime = block.get("mime_type") or block.get("media_type") or "image/png"
                    image_url = data if data.startswith("data:") else f"data:{mime};base64,{data}"
            if isinstance(image_url, str) and image_url:
                parts.append({"type": "image_url", "image_url": {"url": image_url}})
                has_image = True
                continue
            logger.warning("Responses input_image has no usable URL at %s", block_param)
        text = _content_to_text(block, param=block_param)
        if text:
            parts.append({"type": "text", "text": text})
    return parts if has_image else _content_to_text(content, param=param)


def _json_arguments(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return "{}"
    return json.dumps(value, ensure_ascii=False)


def _custom_arguments(value: Any, *, name: str | None = None) -> str:
    del name
    if isinstance(value, str):
        value = {"input": value}
    elif not isinstance(value, dict) or "input" not in value:
        value = {"input": value}
    return json.dumps(value, ensure_ascii=False)


def _clean_schema_top(schema: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(schema)
    for key in ("$schema", "title"):
        cleaned.pop(key, None)
    if cleaned.get("required") in (None, []):
        cleaned.pop("required", None)
    if cleaned.get("additionalProperties") in (None, {}):
        cleaned.pop("additionalProperties", None)
    return cleaned


def _clean_tool_declaration(declaration: dict[str, Any]) -> dict[str, Any]:
    cleaned = {key: value for key, value in declaration.items() if key != "defer_loading"}
    for schema_key in ("parameters", "input_schema"):
        schema = cleaned.get(schema_key)
        if isinstance(schema, dict):
            cleaned[schema_key] = _clean_schema_top(schema)
    return cleaned


def _clean_message_tools(tools: list[Any]) -> list[Any]:
    cleaned: list[Any] = []
    for tool in tools:
        if not isinstance(tool, dict):
            cleaned.append(tool)
        elif tool.get("type") == "namespace" and isinstance(tool.get("tools"), list):
            cleaned.append({**tool, "tools": _clean_message_tools(tool["tools"])})
        else:
            cleaned.append(_clean_tool_declaration(tool))
    return cleaned


def _flatten_tool(
    tool: dict[str, Any],
    *,
    namespace: str | None = None,
    drop_deferred: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, str], set[str]]:
    tool_type = tool.get("type")
    if tool_type == "namespace":
        name = tool.get("name")
        nested_tools = tool.get("tools")
        if nested_tools is None:
            # Codex can send empty namespace shells. Keep the request
            # servable: rejecting it leaves the item in Codex's local history
            # and makes every later request fail identically.
            logger.warning("Skipping empty Responses namespace tool group %r", name)
            return [], {}, set()
        if not isinstance(name, str) or not name:
            raise MalformedRequestError("Namespace tools require a non-empty name")
        if not isinstance(nested_tools, list):
            raise MalformedRequestError("Namespace tools require a tools list")
        container = name.strip()
        if container in ("", _DEFAULT_NAMESPACE):
            nested_namespace = namespace
        else:
            nested_namespace = f"{namespace}{_NAMESPACE_SEPARATOR}{container}" if namespace else container
        flattened: list[dict[str, Any]] = []
        kinds: dict[str, str] = {}
        namespaced_names: set[str] = set()
        for nested in nested_tools:
            if not isinstance(nested, dict):
                raise MalformedRequestError("Each namespace tool must be an object")
            converted, nested_kinds, nested_names = _flatten_tool(
                nested, namespace=nested_namespace, drop_deferred=drop_deferred
            )
            flattened.extend(converted)
            kinds.update(nested_kinds)
            namespaced_names.update(nested_names)
        return flattened, kinds, namespaced_names

    if tool_type in _IGNORED_TOOL_TYPES:
        logger.warning("Ignoring Responses tool type %r", tool_type)
        return [], {}, set()

    if tool_type not in {"function", "custom"}:
        if tool_type not in _HOSTED_TOOL_TYPES:
            logger.warning("Ignoring unsupported Responses tool type %r", tool_type)
            return [], {}, set()
        # Keep hosted declarations in the model-facing tool table. The parser
        # builds a separate synthetic function view where necessary; the gateway
        # itself is not the tool executor.
        source = tool.get("function") if isinstance(tool.get("function"), dict) else tool
        name = source.get("name") or tool_type
        if not isinstance(name, str) or not name:
            return [], {}, set()
        qualified_name = f"{namespace}{_NAMESPACE_SEPARATOR}{name}" if namespace else name
        declaration = _clean_tool_declaration(tool)
        declaration.setdefault("type", tool_type)
        if isinstance(source.get("name"), str) and source.get("name"):
            declaration["name"] = qualified_name
        namespaced_names = {qualified_name} if namespace else set()
        return [declaration], {qualified_name: str(tool_type)}, namespaced_names

    source = tool.get("function") if isinstance(tool.get("function"), dict) else tool
    name = source.get("name")
    if not isinstance(name, str) or not name:
        raise MalformedRequestError(f"{tool_type} tools require a non-empty name")
    qualified_name = f"{namespace}{_NAMESPACE_SEPARATOR}{name}" if namespace else name

    # Preserve the Responses declaration at the model boundary. In particular,
    # Codex code mode advertises a flat custom ``exec`` tool; converting it to
    # a synthetic function here moves the prompt off the model's training
    # distribution. MessageCodec projects flat declarations only when calling
    # a parser that requires the Chat Completions function schema.
    if drop_deferred and (tool.get("defer_loading") or source.get("defer_loading")):
        return [], {qualified_name: str(tool_type)}, set()

    declaration = _clean_tool_declaration(source)
    declaration.setdefault("type", tool_type)
    declaration["name"] = qualified_name
    namespaced_names = {qualified_name} if namespace else set()
    return [declaration], {qualified_name: str(tool_type)}, namespaced_names


def _convert_tools(
    tools: Any,
    *,
    drop_deferred: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, str], set[str]]:
    if tools is None:
        return [], {}, set()
    if not isinstance(tools, list):
        raise MalformedRequestError("tools must be a list")
    converted: list[dict[str, Any]] = []
    kinds: dict[str, str] = {}
    namespaced_names: set[str] = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise MalformedRequestError("Each tool must be an object")
        items, item_kinds, item_names = _flatten_tool(tool, drop_deferred=drop_deferred)
        converted.extend(items)
        kinds.update(item_kinds)
        namespaced_names.update(item_names)
    return converted, kinds, namespaced_names


def _declared_name(tool: Any) -> str | None:
    if not isinstance(tool, dict):
        return None
    source = tool.get("function") if isinstance(tool.get("function"), dict) else tool
    name = source.get("name") or tool.get("type")
    return str(name) if name else None


def _merge_tool_channels(top: list[Any], additional: list[Any]) -> list[Any]:
    if not top:
        return list(additional)
    if not additional:
        return list(top)
    top_names = {_declared_name(tool) for tool in top}
    additional_names = {_declared_name(tool) for tool in additional}
    if top_names == additional_names:
        return list(top)
    if not (top_names & additional_names):
        return list(top) + list(additional)
    logger.warning("Responses tool channels overlap partially: %s", sorted(top_names & additional_names))
    return list(top) + [tool for tool in additional if _declared_name(tool) not in top_names]


def _collect_tool_defs(payload: dict[str, Any]) -> list[Any]:
    input_value = payload.get("input")
    additional: list[Any] = []
    if isinstance(input_value, list):
        for item in input_value:
            if isinstance(item, dict) and item.get("type") == "additional_tools":
                extra = item.get("tools")
                if not isinstance(extra, list):
                    raise MalformedRequestError("additional_tools requires a tools list")
                additional.extend(extra)
    return _merge_tool_channels(list(payload.get("tools") or []), additional)


def _messages_from_input(payload: dict[str, Any]) -> list[dict[str, Any]]:
    input_value = payload.get("input")
    if not isinstance(input_value, str | list):
        raise MalformedRequestError("input must be a string or a list")

    messages: list[dict[str, Any]] = []
    instructions = payload.get("instructions")
    if instructions is not None:
        if not isinstance(instructions, str):
            raise MalformedRequestError("instructions must be a string")
        if instructions:
            # The Qwen3.5/3.8 tokenizer templates used by this recipe reject
            # the Responses-native developer role. The gateway canonical uses
            # system so instructions remain model-visible without patching the
            # checkpoint's Jinja template.
            messages.append({"role": "system", "content": instructions})

    pending: dict[str, list[Any]] | None = None

    def ensure_pending() -> dict[str, list[Any]]:
        nonlocal pending
        if pending is None:
            pending = {"content": [], "reasoning": [], "tool_calls": []}
        return pending

    def flush_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        content = "".join(pending["content"])
        reasoning = "\n".join(part for part in pending["reasoning"] if part)
        tool_calls = pending["tool_calls"]
        if content or reasoning or tool_calls:
            message: dict[str, Any] = {"role": "assistant", "content": content}
            if reasoning:
                message["reasoning_content"] = reasoning
            if tool_calls:
                message["tool_calls"] = tool_calls
            messages.append(message)
        pending = None

    skipped_by_type = 0
    if isinstance(input_value, str):
        messages.append({"role": "user", "content": input_value})
        return messages

    for index, item in enumerate(input_value):
        param = f"input[{index}]"
        if not isinstance(item, dict):
            raise MalformedRequestError(f"Each input item must be an object at {param}")
        item_type = item.get("type", "message")
        if item_type == "additional_tools":
            skipped_by_type += 1
            continue
        if item_type in _SKIPPED_ITEM_TYPES:
            skipped_by_type += 1
            continue
        if item_type == "message":
            role = item.get("role", "user")
            content = _content_to_chat_content(item.get("content"), param=f"{param}.content")
            if role == "assistant":
                if isinstance(content, list):
                    raise MalformedRequestError("image content is only supported in user messages")
                ensure_pending()["content"].append(content)
                continue
            flush_pending()
            if role not in {"developer", "system", "user", "tool"}:
                logger.warning("Mapping unknown Responses role %r to user", role)
                role = "user"
            message = {"role": role, "content": content}
            if role == "tool":
                message["tool_call_id"] = str(item.get("tool_call_id", item.get("call_id", "")))
            messages.append(message)
            continue
        if item_type == "reasoning":
            for source_name in ("summary", "content"):
                reasoning = _content_to_text(item.get(source_name) or [], param=f"{param}.{source_name}")
                if reasoning:
                    ensure_pending()["reasoning"].append(reasoning)
            continue
        if item_type == "agent_message":
            flush_pending()
            content = _content_to_text(item.get("content"), param=param)
            if content:
                messages.append({"role": "tool", "content": content})
            continue
        if item_type in {"function_call", "custom_tool_call"}:
            name = item.get("name")
            call_id = item.get("call_id")
            if not isinstance(name, str) or not name:
                raise MalformedRequestError(f"{item_type} requires a name")
            if not isinstance(call_id, str) or not call_id:
                raise MalformedRequestError(f"{item_type} requires a call_id")
            namespace = item.get("namespace")
            if (
                isinstance(namespace, str)
                and namespace
                and namespace.strip() not in ("", _DEFAULT_NAMESPACE)
                and namespace != name
            ):
                name = f"{namespace}{_NAMESPACE_SEPARATOR}{name}"
            raw_args = item.get("arguments", item.get("input"))
            arguments = (
                _custom_arguments(raw_args, name=name) if item_type == "custom_tool_call" else _json_arguments(raw_args)
            )
            ensure_pending()["tool_calls"].append(
                {
                    "id": call_id,
                    "type": "custom" if item_type == "custom_tool_call" else "function",
                    "function": {"name": name, "arguments": arguments},
                }
            )
            continue
        if item_type in {"function_call_output", "custom_tool_call_output"}:
            flush_pending()
            call_id = item.get("call_id")
            if not isinstance(call_id, str) or not call_id:
                raise MalformedRequestError(f"{item_type} requires a call_id")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": _content_to_chat_content(item.get("output"), param=f"{param}.output"),
                }
            )
            continue

        if item_type in {"web_search_call", "computer_call", "tool_search_call"}:
            # Hosted/server-side calls have no Chat-native equivalent. Preserve
            # the action payload as an assistant function call so Qwen sees the
            # same completed operation on history replay. The harness remains
            # the executor; this is only a canonical representation.
            if item_type == "web_search_call":
                name = "web_search"
                raw_arguments = item.get("action")
            elif item_type == "computer_call":
                name = "computer"
                raw_arguments = item.get("actions") or []
            else:
                name = "tool_search"
                raw_arguments = item.get("arguments")
            arguments = raw_arguments if isinstance(raw_arguments, str) else json.dumps(
                raw_arguments if raw_arguments is not None else {}, ensure_ascii=False
            )
            ensure_pending()["tool_calls"].append(
                {
                    "id": str(item.get("call_id", item.get("id", "")) or ""),
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            )
            continue

        if item_type == "tool_search_output":
            flush_pending()
            message = {
                "role": "tool",
                "tool_call_id": str(item.get("call_id", "")),
                "content": "",
            }
            discovered = item.get("tools")
            if isinstance(discovered, list) and discovered:
                message["tools"] = _clean_message_tools(discovered)
            messages.append(message)
            continue

        if item_type == "computer_call_output":
            flush_pending()
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": str(item.get("call_id", "")),
                    "content": _content_to_chat_content(item.get("output"), param=f"{param}.output"),
                }
            )
            continue

        if item_type == "image_generation_call":
            flush_pending()
            parts: list[str] = []
            revised_prompt = item.get("revised_prompt")
            if isinstance(revised_prompt, str) and revised_prompt:
                parts.append(revised_prompt)
            if item.get("result"):
                parts.append("[image omitted: this endpoint serves a text-only model]")
            messages.append({"role": "tool", "tool_call_id": "", "content": "".join(parts)})
            continue

        if item_type in {"compaction", "compaction_summary"}:
            # Preserve the trained block boundary without exposing opaque
            # client state to the model.
            flush_pending()
            messages.append({"role": "user", "content": ""})
            continue

        degraded = _content_to_text(item.get("content", item.get("text")), param=param)
        logger.warning("Degrading unknown Responses input item %r", item_type)
        if degraded:
            flush_pending()
            messages.append({"role": "user", "content": degraded})
    flush_pending()
    if not messages and isinstance(input_value, list) and skipped_by_type == len(input_value):
        messages.append({"role": "user", "content": ""})
    return messages


def responses_to_internal(
    payload: dict[str, Any],
    *,
    base_sampling_params: dict[str, Any],
    allowed_sampling_keys: frozenset[str],
) -> InternalGenerationRequest:
    if not isinstance(payload, dict):
        raise MalformedRequestError("Request body must be a JSON object")
    if payload.get("background"):
        raise MalformedRequestError("background Responses are not supported")
    if payload.get("store") is True:
        raise MalformedRequestError("stored Responses are not supported")
    if payload.get("previous_response_id") is not None:
        raise MalformedRequestError("previous_response_id is not supported; send the full input history")

    tools, _, _ = _convert_tools(_collect_tool_defs(payload), drop_deferred=True)

    tool_choice = payload.get("tool_choice", "auto")
    if isinstance(tool_choice, dict):
        choice_type = tool_choice.get("type")
        if choice_type in {"auto", "none"}:
            tool_choice = choice_type
        else:
            raise MalformedRequestError(
                "Responses tool_choice with a specific function is not supported"
            )
    elif not isinstance(tool_choice, str) or tool_choice not in {"auto", "none"}:
        raise MalformedRequestError("tool_choice must be auto, none, or a supported object")
    if tool_choice == "none":
        tools = []
    chat_payload: dict[str, Any] = {
        "messages": _messages_from_input(payload),
        "tools": tools or None,
        "tool_choice": "none" if tool_choice == "none" else "auto",
    }
    for key in ("temperature", "top_p", "top_k", "stop"):
        if payload.get(key) is not None:
            chat_payload[key] = payload[key]
    if payload.get("max_output_tokens") is not None:
        chat_payload["max_tokens"] = payload["max_output_tokens"]
    return openai_to_internal(
        chat_payload,
        base_sampling_params=base_sampling_params,
        allowed_sampling_keys=allowed_sampling_keys,
    )


def _tool_metadata(payload: dict[str, Any]) -> tuple[dict[str, str], set[str]]:
    tool_defs = _collect_tool_defs(payload)
    input_value = payload.get("input")
    discovered: list[Any] = []
    if isinstance(input_value, list):
        for item in input_value:
            if isinstance(item, dict) and item.get("type") == "tool_search_output":
                tools = item.get("tools")
                if isinstance(tools, list):
                    discovered.extend(tools)
    _, kinds, namespaced_names = _convert_tools(tool_defs + discovered)
    return kinds, namespaced_names


def _split_namespaced_name(name: str, namespaced_names: set[str]) -> tuple[str | None, str]:
    if name in namespaced_names:
        namespace, _, bare_name = name.partition(_NAMESPACE_SEPARATOR)
        if namespace and bare_name:
            return namespace, bare_name
    return None, name


def _custom_input(arguments: Any) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return arguments
    if isinstance(arguments, dict) and "input" in arguments:
        value = arguments["input"]
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return json.dumps(arguments, ensure_ascii=False) if arguments is not None else ""


def _usage(outcome: GenerationOutcome) -> dict[str, Any]:
    return {
        "input_tokens": outcome.prompt_tokens,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens": outcome.completion_tokens,
        "output_tokens_details": {"reasoning_tokens": 0},
        "total_tokens": outcome.prompt_tokens + outcome.completion_tokens,
    }


def _response_base(
    payload: dict[str, Any],
    *,
    response_id: str,
    model: str,
    created_at: int,
    status: str,
    output: list[dict[str, Any]],
    usage: dict[str, Any] | None,
    incomplete_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "status": status,
        "background": False,
        "error": None,
        "incomplete_details": {"reason": incomplete_reason} if incomplete_reason else None,
        "instructions": payload.get("instructions"),
        "max_output_tokens": payload.get("max_output_tokens"),
        "model": model,
        "output": output,
        "parallel_tool_calls": bool(payload.get("parallel_tool_calls", True)),
        "previous_response_id": None,
        "reasoning": payload.get("reasoning"),
        "store": False,
        "temperature": payload.get("temperature"),
        "text": payload.get("text", {"format": {"type": "text"}}),
        "tool_choice": payload.get("tool_choice", "auto"),
        "tools": payload.get("tools") or [],
        "top_p": payload.get("top_p"),
        "truncation": payload.get("truncation", "disabled"),
        "usage": usage,
        "metadata": payload.get("metadata") or {},
    }


def _output_items(outcome: GenerationOutcome, payload: dict[str, Any]) -> list[dict[str, Any]]:
    message = outcome.assistant_msg
    kinds, namespaced_names = _tool_metadata(payload)
    output: list[dict[str, Any]] = []
    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning:
        output.append(
            {
                "id": f"rs_{uuid4().hex}",
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": reasoning}],
                "status": "completed",
            }
        )
    content = message.get("content")
    if isinstance(content, str) and content:
        output.append(
            {
                "id": f"msg_{uuid4().hex}",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content, "annotations": [], "logprobs": []}],
            }
        )
    for tool_call in message.get("tool_calls") or []:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function") or {}
        name = str(function.get("name") or "")
        arguments = function.get("arguments", "")
        namespace, bare_name = _split_namespaced_name(name, namespaced_names)
        call_id = str(tool_call.get("id") or f"call_{uuid4().hex}")
        if kinds.get(name) == "custom":
            item: dict[str, Any] = {
                "id": f"ctc_{uuid4().hex}",
                "type": "custom_tool_call",
                "status": "completed",
                "call_id": call_id,
                "name": bare_name,
                "input": _custom_input(arguments),
            }
        else:
            item = {
                "id": f"fc_{uuid4().hex}",
                "type": "function_call",
                "status": "completed",
                "call_id": call_id,
                "name": bare_name,
                "arguments": _json_arguments(arguments),
            }
        if namespace:
            item["namespace"] = namespace
        output.append(item)
    return output


def _terminal_status(outcome: GenerationOutcome) -> tuple[str, str | None]:
    """Map the internal finish_reason onto the Responses terminal status.

    A length-exhausted generation (session capacity or max_output_tokens hit)
    is ``incomplete`` with ``incomplete_details.reason="max_output_tokens"``,
    exactly like upstream. Clients rely on this to tell "the model has no
    room left" apart from a transient empty reply they should retry.
    """
    if outcome.finish_reason == "length":
        return "incomplete", "max_output_tokens"
    return "completed", None


def responses_build_response(outcome: GenerationOutcome, *, payload: dict[str, Any], model: str) -> dict[str, Any]:
    status, incomplete_reason = _terminal_status(outcome)
    return _response_base(
        payload,
        response_id=f"resp_{uuid4().hex}",
        model=model,
        created_at=int(time.time()),
        status=status,
        output=_output_items(outcome, payload),
        usage=_usage(outcome),
        incomplete_reason=incomplete_reason,
    )


def _event_to_sse(event: dict[str, Any]) -> bytes:
    return f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n".encode()


def responses_stream_response(
    run_generation: Callable[[], Awaitable[GenerationOutcome]],
    *,
    payload: dict[str, Any],
    model: str,
    heartbeat_interval_s: float = 15.0,
) -> StreamingResponse:
    """Run a generation behind a Responses SSE stream with parsed heartbeats."""
    response_id = f"resp_{uuid4().hex}"
    created_at = int(time.time())

    async def _gen():
        sequence_number = 0

        def event(event_type: str, **fields: Any) -> dict[str, Any]:
            nonlocal sequence_number
            body = {"type": event_type, "sequence_number": sequence_number, **fields}
            sequence_number += 1
            return body

        in_progress = _response_base(
            payload,
            response_id=response_id,
            model=model,
            created_at=created_at,
            status="in_progress",
            output=[],
            usage=None,
        )
        yield _event_to_sse(event("response.created", response=in_progress))
        yield _event_to_sse(event("response.in_progress", response=in_progress))

        task = asyncio.create_task(run_generation())
        try:
            while not task.done():
                done, _ = await asyncio.wait({task}, timeout=heartbeat_interval_s)
                if not done:
                    yield _event_to_sse(event("response.in_progress", response=in_progress))
            outcome = task.result()
            output = _output_items(outcome, payload)
            for output_index, item in enumerate(output):
                item_type = item["type"]
                if item_type == "reasoning":
                    in_flight = {**item, "status": "in_progress", "summary": []}
                elif item_type == "message":
                    in_flight = {**item, "status": "in_progress", "content": []}
                elif item_type == "custom_tool_call":
                    in_flight = {**item, "status": "in_progress", "input": ""}
                else:
                    in_flight = {**item, "status": "in_progress", "arguments": ""}
                yield _event_to_sse(event("response.output_item.added", output_index=output_index, item=in_flight))

                if item_type == "reasoning":
                    text = item["summary"][0]["text"]
                    yield _event_to_sse(
                        event(
                            "response.reasoning_summary_part.added",
                            item_id=item["id"],
                            output_index=output_index,
                            summary_index=0,
                            part={"type": "summary_text", "text": ""},
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.reasoning_summary_text.delta",
                            item_id=item["id"],
                            output_index=output_index,
                            summary_index=0,
                            delta=text,
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.reasoning_summary_text.done",
                            item_id=item["id"],
                            output_index=output_index,
                            summary_index=0,
                            text=text,
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.reasoning_summary_part.done",
                            item_id=item["id"],
                            output_index=output_index,
                            summary_index=0,
                            part=item["summary"][0],
                        )
                    )
                elif item_type == "message":
                    text = item["content"][0]["text"]
                    yield _event_to_sse(
                        event(
                            "response.content_part.added",
                            item_id=item["id"],
                            output_index=output_index,
                            content_index=0,
                            part={"type": "output_text", "text": "", "annotations": [], "logprobs": []},
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.output_text.delta",
                            item_id=item["id"],
                            output_index=output_index,
                            content_index=0,
                            delta=text,
                            logprobs=[],
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.content_part.done",
                            item_id=item["id"],
                            output_index=output_index,
                            content_index=0,
                            part=item["content"][0],
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.output_text.done",
                            item_id=item["id"],
                            output_index=output_index,
                            content_index=0,
                            text=text,
                            logprobs=[],
                        )
                    )
                elif item_type == "custom_tool_call":
                    yield _event_to_sse(
                        event(
                            "response.custom_tool_call_input.delta",
                            item_id=item["id"],
                            output_index=output_index,
                            delta=item["input"],
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.custom_tool_call_input.done",
                            item_id=item["id"],
                            output_index=output_index,
                            input=item["input"],
                        )
                    )
                else:
                    yield _event_to_sse(
                        event(
                            "response.function_call_arguments.delta",
                            item_id=item["id"],
                            output_index=output_index,
                            delta=item["arguments"],
                        )
                    )
                    yield _event_to_sse(
                        event(
                            "response.function_call_arguments.done",
                            item_id=item["id"],
                            output_index=output_index,
                            arguments=item["arguments"],
                        )
                    )
                yield _event_to_sse(event("response.output_item.done", output_index=output_index, item=item))

            status, incomplete_reason = _terminal_status(outcome)
            completed = _response_base(
                payload,
                response_id=response_id,
                model=model,
                created_at=created_at,
                status=status,
                output=output,
                usage=_usage(outcome),
                incomplete_reason=incomplete_reason,
            )
            yield _event_to_sse(event(f"response.{status}", response=completed))
        except asyncio.CancelledError:
            task.cancel()
            raise
        except Exception as exc:
            logger.exception("Responses generation failed")
            failed = _response_base(
                payload,
                response_id=response_id,
                model=model,
                created_at=created_at,
                status="failed",
                output=[],
                usage=None,
            )
            failed["error"] = {"code": "internal_error", "message": str(exc)}
            yield _event_to_sse(event("response.failed", response=failed))
            yield _event_to_sse(
                event("error", code="internal_error", message=str(exc), param=None)
            )

    return StreamingResponse(_gen(), media_type="text/event-stream", headers=_SSE_HEADERS)
