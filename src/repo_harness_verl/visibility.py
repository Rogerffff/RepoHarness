"""verl AgentLoopOutput / DataProto 可见性和形状校验。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from repo_harness.rl.visibility import (
    FlatScalar,
    VisibilityContractError,
    validate_batch_extra_fields,
    validate_no_absolute_local_path,
    validate_no_forbidden_model_visible_content,
)


class VerlVisibilityError(ValueError):
    """表示数据越过了 verl batch 可见性边界。"""


TRANSFER_QUEUE_RESERVED_KWARGS = frozenset(
    {
        "prompts",
        "responses",
        "response_mask",
        "rollout_log_probs",
        "rm_scores",
        "extra_fields",
        "teacher_ids",
        "teacher_logprobs",
        "loss_mask",
        "input_ids",
        "position_ids",
        "multi_modal_inputs",
    }
)

_ALLOWED_TRANSFER_QUEUE_KWARGS = frozenset({"raw_prompt"})
_FORBIDDEN_TRANSFER_QUEUE_FIELD_NAMES = frozenset(
    {
        "hidden_verifier",
        "gold_patch",
        "accepted_label",
        "provider_secret",
        "evaluator_only_logs",
        "complete_reward_metadata",
        "reward_extra_info",
        "reward_extra_keys",
        "extra_info",
        "ground_truth",
    }
)


def _as_python_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _iter_array_values(value: Any):
    if isinstance(value, (str, bytes)):
        yield value
        return
    if isinstance(value, Mapping):
        yield value
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield item
        return
    if hasattr(value, "tolist"):
        items = value.tolist()
        if isinstance(items, list):
            for item in items:
                yield item
        else:
            yield items
        return
    try:
        iterator = iter(value)
    except TypeError:
        yield value
        return
    for item in iterator:
        yield item


def _shape_of(value: Any) -> tuple[int, ...]:
    shape = getattr(value, "shape", None)
    if shape is not None:
        return tuple(int(part) for part in shape)
    size = getattr(value, "size", None)
    if callable(size):
        try:
            maybe_shape = size()
        except TypeError:
            maybe_shape = None
        if maybe_shape is not None:
            return tuple(int(part) for part in maybe_shape)
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            return (len(value), len(value[0]))
        return (len(value),)
    raise VerlVisibilityError(f"cannot determine tensor shape for {type(value).__name__}")


def _raise_visibility_error(exc: Exception) -> None:
    raise VerlVisibilityError(str(exc)) from exc


def _normalize_field_name(value: str) -> str:
    normalized = []
    previous_was_separator = False
    for char in value:
        if char.isalnum():
            if char.isupper() and normalized and not previous_was_separator:
                normalized.append("_")
            normalized.append(char.lower())
            previous_was_separator = False
        else:
            if normalized and not previous_was_separator:
                normalized.append("_")
            previous_was_separator = True
    return "".join(normalized).strip("_")


def _validate_transfer_queue_field_name(key: str) -> None:
    normalized = _normalize_field_name(key)
    for forbidden in _FORBIDDEN_TRANSFER_QUEUE_FIELD_NAMES:
        if normalized == forbidden or forbidden in normalized:
            raise VerlVisibilityError(f"forbidden_transfer_queue_field_name: {key}")
    try:
        validate_no_forbidden_model_visible_content(key, field_name=f"transfer_queue_field_name.{key}")
    except VisibilityContractError as exc:
        _raise_visibility_error(exc)


def _validate_transfer_queue_visible_string(value: str, *, field_name: str) -> None:
    normalized = _normalize_field_name(value)
    for forbidden in _FORBIDDEN_TRANSFER_QUEUE_FIELD_NAMES:
        if normalized == forbidden or forbidden in normalized:
            raise VerlVisibilityError(f"forbidden_transfer_queue_field_value: {field_name}")


def _validate_visible_value(value: Any, *, field_name: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _validate_transfer_queue_field_name(str(key))
            _validate_visible_value(item, field_name=f"{field_name}.{key}")
        return
    if isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            _validate_visible_value(item, field_name=f"{field_name}[{index}]")
        return
    try:
        validate_no_forbidden_model_visible_content(value, field_name=field_name)
        if isinstance(value, str):
            validate_no_absolute_local_path(value, field_name=field_name)
            _validate_transfer_queue_visible_string(value, field_name=field_name)
    except VisibilityContractError as exc:
        _raise_visibility_error(exc)


def validate_agent_loop_output_extra_fields(extra_fields: Mapping[str, Any]) -> dict[str, FlatScalar]:
    """校验 converter 输出的 AgentLoopOutput.extra_fields。"""

    if "raw_prompt" in extra_fields:
        raise VerlVisibilityError("raw_prompt_must_be_added_by_verl_postprocess")
    try:
        return validate_batch_extra_fields(extra_fields)
    except VisibilityContractError as exc:
        _raise_visibility_error(exc)


def validate_postprocessed_extra_fields(extra_fields: Mapping[str, Any]) -> None:
    """校验 verl postprocess 后的 extra_fields，包括 extra_fields.raw_prompt。"""

    batch_fields = {key: value for key, value in extra_fields.items() if key != "raw_prompt"}
    validate_agent_loop_output_extra_fields(batch_fields)
    if "raw_prompt" in extra_fields:
        _validate_visible_value(extra_fields["raw_prompt"], field_name="extra_fields.raw_prompt")


def validate_transfer_queue_kwargs(
    kwargs: Mapping[str, Any],
    *,
    allowed_keys: set[str] | None = None,
) -> None:
    """校验未来 main_ppo_sync.py field.update(kwargs) 前的 kwargs。"""

    allowed = set(_ALLOWED_TRANSFER_QUEUE_KWARGS if allowed_keys is None else allowed_keys)
    for key, value in kwargs.items():
        if key in TRANSFER_QUEUE_RESERVED_KWARGS:
            raise VerlVisibilityError(f"transfer_queue_kwargs_reserved_key: {key}")
        _validate_transfer_queue_field_name(key)
        if key not in allowed:
            raise VerlVisibilityError(f"transfer_queue_kwargs_not_allowlisted: {key}")
        _validate_visible_value(value, field_name=key)


def validate_transfer_queue_field_visibility(field: Mapping[str, Any]) -> None:
    """校验 main_ppo_sync.py 准备写入 TransferQueue 的 field。"""

    if "extra_fields" in field:
        validate_agent_loop_output_extra_fields(field["extra_fields"])
    if "raw_prompt" in field:
        _validate_visible_value(field["raw_prompt"], field_name="raw_prompt")
    for key, value in field.items():
        if key in {
            "prompts",
            "responses",
            "response_mask",
            "rollout_log_probs",
            "rm_scores",
            "input_ids",
            "position_ids",
            "attention_mask",
            "teacher_ids",
            "teacher_logprobs",
            "loss_mask",
            "multi_modal_inputs",
            "routed_experts",
        }:
            continue
        if key.startswith("repo_harness_"):
            try:
                validate_batch_extra_fields({key: _as_python_scalar(value)})
            except VisibilityContractError as exc:
                _raise_visibility_error(exc)
        else:
            if key not in {"extra_fields", "raw_prompt"}:
                _validate_transfer_queue_field_name(key)
            _validate_visible_value(value, field_name=key)


def validate_token_output_extra_fields(extra_fields: Mapping[str, Any]) -> None:
    """校验 TokenOutput.extra_fields，不能使用 TransferQueue tensor 字段绕过递归检查。"""

    def visit(value: Any, *, field_name: str) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                key_text = str(key)
                if key_text in TRANSFER_QUEUE_RESERVED_KWARGS:
                    raise VerlVisibilityError(f"token_output_extra_fields_reserved_key: {key_text}")
                _validate_transfer_queue_field_name(key_text)
                visit(item, field_name=f"{field_name}.{key_text}")
            return
        if isinstance(value, (list, tuple, set)):
            for index, item in enumerate(value):
                visit(item, field_name=f"{field_name}[{index}]")
            return
        _validate_visible_value(value, field_name=field_name)

    visit(dict(extra_fields), field_name="token_output.extra_fields")


def validate_dataproto_shapes(
    data_proto: Any,
    *,
    batch_size: int,
    prompt_length: int,
    response_length: int,
) -> None:
    """校验 verl DataProto 的关键 tensor 维度。"""

    batch = data_proto.batch
    expected = {
        "prompts": (batch_size, prompt_length),
        "responses": (batch_size, response_length),
        "response_mask": (batch_size, response_length),
        "input_ids": (batch_size, prompt_length + response_length),
        "attention_mask": (batch_size, prompt_length + response_length),
    }
    for key, shape in expected.items():
        if key not in batch:
            raise VerlVisibilityError(f"missing_dataproto_batch_key: {key}")
        if _shape_of(batch[key]) != shape:
            raise VerlVisibilityError(f"dataproto_shape_mismatch:{key}:{_shape_of(batch[key])}!={shape}")
    if "rollout_log_probs" in batch and _shape_of(batch["rollout_log_probs"]) != (batch_size, response_length):
        raise VerlVisibilityError("dataproto_shape_mismatch:rollout_log_probs")
    if "rm_scores" in batch and _shape_of(batch["rm_scores"]) != (batch_size, response_length):
        raise VerlVisibilityError("dataproto_shape_mismatch:rm_scores")


def validate_dataproto_visibility(data_proto: Any) -> None:
    """校验 DataProto non_tensor_batch 和 meta_info 的可见性。"""

    for key, array_value in getattr(data_proto, "non_tensor_batch", {}).items():
        if key.startswith("repo_harness_"):
            for item in _iter_array_values(array_value):
                try:
                    validate_batch_extra_fields({key: _as_python_scalar(item)})
                except VisibilityContractError as exc:
                    _raise_visibility_error(exc)
            continue
        if key == "raw_prompt":
            for item in _iter_array_values(array_value):
                _validate_visible_value(item, field_name="non_tensor_batch.raw_prompt")
            continue
        _validate_visible_value(key, field_name=f"non_tensor_batch.{key}")
        for item in _iter_array_values(array_value):
            _validate_visible_value(item, field_name=f"non_tensor_batch.{key}")

    for key, value in getattr(data_proto, "meta_info", {}).items():
        if key == "reward_extra_keys" and not value:
            continue
        _validate_visible_value(key, field_name=f"meta_info.{key}")
        _validate_visible_value(value, field_name=f"meta_info.{key}")
