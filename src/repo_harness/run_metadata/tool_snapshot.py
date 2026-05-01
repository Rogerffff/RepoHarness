"""模型可见工具 schema snapshot 生成。"""

from __future__ import annotations

from repo_harness.run_metadata.schemas import ToolProtocolFacts, ToolSchemaEntry, ToolSchemaSnapshot
from repo_harness.schema_base import stable_hash
from repo_harness.schema_versions import TOOL_POLICY_VERSION
from repo_harness.tools import ToolRegistry, default_tool_registry
from repo_harness.trajectory import ArtifactRef, RunRecorder

TOOL_RESULT_FORMAT_VERSION = "repo_harness_tool_result_v0"
TOOL_CALL_PARSER_VERSION = "repo_harness_tool_call_parser_v0"


def build_tool_schema_snapshot(
    registry: ToolRegistry | None = None,
) -> ToolSchemaSnapshot:
    registry = registry or default_tool_registry()
    tools = []
    for name in registry.names():
        definition = registry.get(name)
        tools.append(
            ToolSchemaEntry(
                name=definition.name,
                tool_version=definition.tool_version,
                model_visible_description=definition.model_visible_description,
                input_schema=definition.input_schema,
                output_schema=definition.output_schema,
                tool_result_format_version=TOOL_RESULT_FORMAT_VERSION,
                read_only=definition.is_read_only,
                destructive=definition.is_destructive,
                permission_required=definition.requires_permission,
                max_output_chars=definition.max_result_size,
            )
        )
    payload = {
        "tool_order": registry.names(),
        "tool_parser_version": TOOL_CALL_PARSER_VERSION,
        "tool_result_format_version": TOOL_RESULT_FORMAT_VERSION,
        "tools": [tool.model_dump(mode="json") for tool in tools],
    }
    snapshot_sha256 = stable_hash(payload)
    return ToolSchemaSnapshot(
        snapshot_id=f"tool_schema_snapshot_{snapshot_sha256[:12]}",
        tool_order=registry.names(),
        tool_parser_version=TOOL_CALL_PARSER_VERSION,
        tool_result_format_version=TOOL_RESULT_FORMAT_VERSION,
        tools=tools,
        snapshot_sha256=snapshot_sha256,
    )


def write_tool_schema_snapshot(
    recorder: RunRecorder,
    registry: ToolRegistry | None = None,
) -> tuple[ToolSchemaSnapshot, ArtifactRef, ToolProtocolFacts]:
    snapshot = build_tool_schema_snapshot(registry)
    ref = recorder.write_json_artifact(
        "tool_schema_snapshot",
        snapshot.model_dump(mode="json"),
        {"budget_policy": "preserve_json"},
    )
    protocol = ToolProtocolFacts(
        tool_schema_snapshot_ref=ref,
        tool_schema_snapshot_sha256=snapshot.snapshot_sha256,
        tool_order=snapshot.tool_order,
        tool_parser_version=snapshot.tool_parser_version,
        tool_result_format_version=snapshot.tool_result_format_version,
        tool_policy_version=TOOL_POLICY_VERSION,
    )
    return snapshot, ref, protocol
