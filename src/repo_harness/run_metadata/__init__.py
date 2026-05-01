"""第二版 run metadata schema。"""

from repo_harness.run_metadata.fingerprint import (
    build_local_environment_fingerprint,
    compute_file_sha256,
    compute_source_tree_hash,
)
from repo_harness.run_metadata.schemas import (
    EnvironmentFingerprint,
    ExecutionModeFacts,
    ExportReadinessFacts,
    FailureCategory,
    FailureDiagnostics,
    FailureType,
    RunConfigFacts,
    RunConfigFactsRef,
    RunMetadata,
    RunMetadataRef,
    RunMetadataSource,
    SourceCheckoutFacts,
    ToolProtocolFacts,
    ToolSchemaEntry,
    ToolSchemaSnapshot,
    WorkspaceBackendFacts,
    WorkspaceExecutionFacts,
)
from repo_harness.run_metadata.tool_snapshot import (
    build_tool_schema_snapshot,
    write_tool_schema_snapshot,
)
from repo_harness.run_metadata.writer import (
    build_run_config_facts,
    build_run_metadata,
    write_run_config_facts,
    write_run_metadata,
)

__all__ = [
    "build_local_environment_fingerprint",
    "build_run_config_facts",
    "build_run_metadata",
    "build_tool_schema_snapshot",
    "compute_file_sha256",
    "compute_source_tree_hash",
    "EnvironmentFingerprint",
    "ExecutionModeFacts",
    "ExportReadinessFacts",
    "FailureCategory",
    "FailureDiagnostics",
    "FailureType",
    "RunConfigFacts",
    "RunConfigFactsRef",
    "RunMetadata",
    "RunMetadataRef",
    "RunMetadataSource",
    "SourceCheckoutFacts",
    "ToolProtocolFacts",
    "ToolSchemaEntry",
    "ToolSchemaSnapshot",
    "WorkspaceBackendFacts",
    "WorkspaceExecutionFacts",
    "write_run_config_facts",
    "write_run_metadata",
    "write_tool_schema_snapshot",
]
