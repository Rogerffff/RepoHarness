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
from .batch_refill import (
    Stage125BatchRefillReport,
    Stage125RefillPolicy,
    Stage125SampleClassification,
    build_refill_report,
    classify_episode_result_for_refill,
    select_valid_training_views,
)
from .dataproto_profile import DataProtoPaddingProfile, build_dataproto_padding_profile
from .errors import (
    RepoHarnessVerlAdapterError,
    RepoHarnessVerlGatewayError,
    RepoHarnessVerlRequestMappingError,
)
from .fully_async_inventory import FullyAsyncInterfaceInventory, build_fully_async_interface_inventory
from .inference_profile import (
    InferenceMetricSourceInventory,
    InferenceServerProfile,
    build_inference_metric_source_inventory,
    build_inference_server_profile,
)
from .ray_worker_profile import (
    RayWorkerResourceProfile,
    SystemResourceProfile,
    build_ray_worker_resource_profile,
    build_system_resource_profile,
)
from .tokenization_profile import TokenizationProfile, build_tokenization_profile
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
    validate_fully_async_queue_payload_visibility,
    validate_postprocessed_extra_fields,
    validate_pre_serialization_rollout_sample_visibility,
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
    "DataProtoPaddingProfile",
    "FullyAsyncInterfaceInventory",
    "InferenceMetricSourceInventory",
    "InferenceServerProfile",
    "RayWorkerResourceProfile",
    "Stage125BatchRefillReport",
    "Stage125RefillPolicy",
    "Stage125SampleClassification",
    "SystemResourceProfile",
    "TokenizationProfile",
    "VerlLLMGateway",
    "VerlVisibilityError",
    "build_agent_loop_metrics",
    "build_dataproto_padding_profile",
    "build_episode_request_from_verl_kwargs",
    "build_fully_async_interface_inventory",
    "build_inference_metric_source_inventory",
    "build_inference_server_profile",
    "build_ray_worker_resource_profile",
    "build_refill_report",
    "build_safe_episode_identifiers",
    "build_system_resource_profile",
    "build_tokenization_profile",
    "classify_episode_result_for_refill",
    "episode_result_to_agent_loop_output",
    "project_audit_refs_for_extra_fields",
    "project_generation_records_route",
    "select_valid_training_views",
    "token_output_to_llm_gateway_response",
    "training_view_to_agent_loop_output",
    "training_view_with_projected_route",
    "validate_repo_harness_verl_kwargs",
    "validate_agent_loop_output_extra_fields",
    "validate_dataproto_shapes",
    "validate_dataproto_visibility",
    "validate_fully_async_queue_payload_visibility",
    "validate_postprocessed_extra_fields",
    "validate_pre_serialization_rollout_sample_visibility",
    "validate_token_output_extra_fields",
    "validate_transfer_queue_field_visibility",
    "validate_transfer_queue_kwargs",
]
