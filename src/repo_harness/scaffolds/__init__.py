"""Agent scaffold 模块。"""

from repo_harness.scaffolds.policies import (
    resolve_allowed_tools,
    resolve_feedback_policy,
    tool_registry_for_allowed_tools,
)
from repo_harness.scaffolds.registry import ScaffoldRegistry, build_scaffold, default_scaffold_registry
from repo_harness.scaffolds.schemas import ScaffoldDefinition
from repo_harness.scaffolds.single_shot_patch import (
    SingleShotPatchScaffold,
    build_single_shot_patch_scaffold,
)
from repo_harness.scaffolds.simple_react import SimpleReactScaffold, build_simple_react_scaffold

__all__ = [
    "ScaffoldDefinition",
    "ScaffoldRegistry",
    "SingleShotPatchScaffold",
    "SimpleReactScaffold",
    "build_scaffold",
    "build_single_shot_patch_scaffold",
    "build_simple_react_scaffold",
    "default_scaffold_registry",
    "resolve_allowed_tools",
    "resolve_feedback_policy",
    "tool_registry_for_allowed_tools",
]
