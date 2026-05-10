"""上下文构建与上下文管理模块。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from repo_harness.context.budget import (
    ContextBudgetFacts,
    ProviderRequestProjectionEstimate,
    build_provider_request_projection,
    estimate_provider_request_projection,
    resolve_context_budget,
)
from repo_harness.context.manager import ContextManager
from repo_harness.context.schemas import (
    ContentReplacementRecord,
    ContentReplacementState,
    AutoCompactRecord,
    AutoCompactState,
    CompactSummary,
    ContextBuilderConfig,
    ContextCompactionFacts,
    ContextPolicySnapshot,
    ContextReductionRecord,
    MicroCompactRecord,
    ModelInputSnapshot,
    PreparedMessages,
    ToolResultArtifactRecord,
    ToolResultCompactRecord,
)
from repo_harness.context.tool_result_artifacts import (
    ToolResultArtifactError,
    ToolResultArtifactIndex,
    build_persisted_tool_result_preview,
    persist_tool_result_content,
    read_tool_result_artifact,
)

if TYPE_CHECKING:
    from repo_harness.context.builder import ContextBuilder

__all__ = [
    "AutoCompactRecord",
    "AutoCompactState",
    "CompactSummary",
    "ContentReplacementRecord",
    "ContentReplacementState",
    "ContextBuilder",
    "ContextBuilderConfig",
    "ContextBudgetFacts",
    "ContextCompactionFacts",
    "ContextManager",
    "ContextPolicySnapshot",
    "ContextReductionRecord",
    "MicroCompactRecord",
    "ModelInputSnapshot",
    "PreparedMessages",
    "ProviderRequestProjectionEstimate",
    "ToolResultArtifactError",
    "ToolResultArtifactIndex",
    "ToolResultArtifactRecord",
    "ToolResultCompactRecord",
    "build_provider_request_projection",
    "estimate_provider_request_projection",
    "build_persisted_tool_result_preview",
    "persist_tool_result_content",
    "read_tool_result_artifact",
    "resolve_context_budget",
]


def __getattr__(name: str) -> Any:
    if name == "ContextBuilder":
        from repo_harness.context.builder import ContextBuilder

        return ContextBuilder
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
