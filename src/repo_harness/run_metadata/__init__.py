"""第二版 run metadata schema 和辅助函数导出。"""

from repo_harness.run_metadata.schemas import (
    EnvironmentFingerprint,
    ExecutionModeFacts,
    ExportReadinessFacts,
    FailureCategory,
    FailureDiagnostics,
    FailureType,
    HookPolicySnapshot,
    MCPPolicySnapshot,
    PermissionPolicySnapshot,
    RunConfigFacts,
    RunConfigFactsRef,
    RunMetadata,
    RunMetadataRef,
    RunMetadataSource,
    SourceCheckoutFacts,
    ToolProtocolFacts,
    ToolContractSnapshot,
    ToolSchemaEntry,
    ToolSchemaSnapshot,
    WorkspaceBackendFacts,
    WorkspaceExecutionFacts,
)

_LAZY_EXPORTS = {
    "build_local_environment_fingerprint": (
        "repo_harness.run_metadata.fingerprint",
        "build_local_environment_fingerprint",
    ),
    "build_run_config_facts": ("repo_harness.run_metadata.writer", "build_run_config_facts"),
    "build_run_metadata": ("repo_harness.run_metadata.writer", "build_run_metadata"),
    "build_tool_schema_snapshot": (
        "repo_harness.run_metadata.tool_snapshot",
        "build_tool_schema_snapshot",
    ),
    "compute_file_sha256": ("repo_harness.run_metadata.fingerprint", "compute_file_sha256"),
    "compute_source_tree_hash": ("repo_harness.run_metadata.fingerprint", "compute_source_tree_hash"),
    "RunMetadataInspection": ("repo_harness.run_metadata.reader", "RunMetadataInspection"),
    "inspect_run_metadata": ("repo_harness.run_metadata.reader", "inspect_run_metadata"),
    "write_run_config_facts": ("repo_harness.run_metadata.writer", "write_run_config_facts"),
    "write_run_metadata": ("repo_harness.run_metadata.writer", "write_run_metadata"),
    "write_tool_schema_snapshot": ("repo_harness.run_metadata.tool_snapshot", "write_tool_schema_snapshot"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr_name = target
    import importlib

    value = getattr(importlib.import_module(module_name), attr_name)
    globals()[name] = value
    return value

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
    "HookPolicySnapshot",
    "MCPPolicySnapshot",
    "PermissionPolicySnapshot",
    "RunConfigFacts",
    "RunConfigFactsRef",
    "RunMetadata",
    "RunMetadataInspection",
    "RunMetadataRef",
    "RunMetadataSource",
    "SourceCheckoutFacts",
    "ToolProtocolFacts",
    "ToolContractSnapshot",
    "ToolSchemaEntry",
    "ToolSchemaSnapshot",
    "WorkspaceBackendFacts",
    "WorkspaceExecutionFacts",
    "inspect_run_metadata",
    "write_run_config_facts",
    "write_run_metadata",
    "write_tool_schema_snapshot",
]
