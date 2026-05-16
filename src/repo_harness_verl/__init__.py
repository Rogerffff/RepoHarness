"""Optional verl adapter helpers for RepoHarness.

This package is intentionally outside ``repo_harness.rl`` so ordinary
RepoHarness schema/runtime imports do not require a full verl installation.
"""

from .conversion import (
    REPO_HARNESS_AGENT_LOOP_EXTRA_FIELDS,
    VERL_AGENT_LOOP_METRIC_KEYS,
    VerlConversionError,
    build_agent_loop_metrics,
    episode_result_to_agent_loop_output,
    project_audit_refs_for_extra_fields,
    project_generation_records_route,
    training_view_to_agent_loop_output,
    training_view_with_projected_route,
)
from .errors import (
    RepoHarnessVerlAdapterError,
    RepoHarnessVerlGatewayError,
    RepoHarnessVerlRequestMappingError,
)
from .gateway import VerlLLMGateway, token_output_to_llm_gateway_response
from .request_mapping import (
    REPO_HARNESS_VERL_ALLOWED_KWARGS,
    REQUEST_CONSTRUCTION_KWARGS,
    VERL_CONTROL_KWARGS,
    RepoHarnessVerlIdentifiers,
    build_episode_request_from_verl_kwargs,
    build_safe_episode_identifiers,
    validate_repo_harness_verl_kwargs,
)
from .visibility import (
    TRANSFER_QUEUE_RESERVED_KWARGS,
    VerlVisibilityError,
    validate_agent_loop_output_extra_fields,
    validate_dataproto_shapes,
    validate_dataproto_visibility,
    validate_postprocessed_extra_fields,
    validate_token_output_extra_fields,
    validate_transfer_queue_field_visibility,
    validate_transfer_queue_kwargs,
)

__all__ = [
    "REPO_HARNESS_AGENT_LOOP_EXTRA_FIELDS",
    "REPO_HARNESS_VERL_ALLOWED_KWARGS",
    "REQUEST_CONSTRUCTION_KWARGS",
    "TRANSFER_QUEUE_RESERVED_KWARGS",
    "VERL_CONTROL_KWARGS",
    "VERL_AGENT_LOOP_METRIC_KEYS",
    "VerlConversionError",
    "RepoHarnessVerlAdapterError",
    "RepoHarnessVerlGatewayError",
    "RepoHarnessVerlIdentifiers",
    "RepoHarnessVerlRequestMappingError",
    "VerlLLMGateway",
    "VerlVisibilityError",
    "build_agent_loop_metrics",
    "build_episode_request_from_verl_kwargs",
    "build_safe_episode_identifiers",
    "episode_result_to_agent_loop_output",
    "project_audit_refs_for_extra_fields",
    "project_generation_records_route",
    "token_output_to_llm_gateway_response",
    "training_view_to_agent_loop_output",
    "training_view_with_projected_route",
    "validate_repo_harness_verl_kwargs",
    "validate_agent_loop_output_extra_fields",
    "validate_dataproto_shapes",
    "validate_dataproto_visibility",
    "validate_postprocessed_extra_fields",
    "validate_token_output_extra_fields",
    "validate_transfer_queue_field_visibility",
    "validate_transfer_queue_kwargs",
]
