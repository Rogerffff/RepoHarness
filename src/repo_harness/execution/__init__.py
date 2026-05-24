"""Shared episode execution specification.

This package is intentionally neutral: evaluation entrypoints and RL runtime
entrypoints may both consume it, but it must not depend on the verl adapter
package or heavy trainer/runtime packages.
"""

from repo_harness.execution.builder import EpisodeExecutionSpecBuilder
from repo_harness.execution.spec import (
    EpisodeExecutionSpec,
    EpisodeExecutionSpecBudgetFacts,
    EpisodeExecutionSpecContextFacts,
    EpisodeExecutionSpecFeedbackFacts,
    EpisodeExecutionSpecRunConfigFacts,
    EpisodeExecutionSpecTaskFacts,
    EpisodeExecutionSpecToolFacts,
    EpisodeExecutionSpecVerifierFacts,
    build_tool_registry_digest,
    build_tool_schema_snapshot_digest,
    compute_spec_payload_sha256,
    validate_episode_execution_spec_runtime_binding,
    validate_request_execution_spec_binding,
)

__all__ = [
    "EpisodeExecutionSpec",
    "EpisodeExecutionSpecBudgetFacts",
    "EpisodeExecutionSpecBuilder",
    "EpisodeExecutionSpecContextFacts",
    "EpisodeExecutionSpecFeedbackFacts",
    "EpisodeExecutionSpecRunConfigFacts",
    "EpisodeExecutionSpecTaskFacts",
    "EpisodeExecutionSpecToolFacts",
    "EpisodeExecutionSpecVerifierFacts",
    "build_tool_registry_digest",
    "build_tool_schema_snapshot_digest",
    "compute_spec_payload_sha256",
    "validate_episode_execution_spec_runtime_binding",
    "validate_request_execution_spec_binding",
]
