"""上下文构建与上下文管理模块。"""

from repo_harness.context.builder import ContextBuilder
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

__all__ = [
    "AutoCompactRecord",
    "AutoCompactState",
    "CompactSummary",
    "ContentReplacementRecord",
    "ContentReplacementState",
    "ContextBuilder",
    "ContextBuilderConfig",
    "ContextCompactionFacts",
    "ContextManager",
    "ContextPolicySnapshot",
    "ContextReductionRecord",
    "MicroCompactRecord",
    "ModelInputSnapshot",
    "PreparedMessages",
    "ToolResultArtifactRecord",
    "ToolResultCompactRecord",
]
