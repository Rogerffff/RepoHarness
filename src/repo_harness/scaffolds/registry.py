"""Scaffold registry."""

from __future__ import annotations

from repo_harness.errors import ConfigError
from repo_harness.scaffolds.schemas import ScaffoldDefinition
from repo_harness.scaffolds.simple_react import build_simple_react_scaffold


class ScaffoldRegistry:
    def __init__(self, definitions: list[ScaffoldDefinition] | None = None) -> None:
        self._definitions: dict[str, ScaffoldDefinition] = {}
        for definition in definitions or [build_simple_react_scaffold()]:
            self.register(definition)

    def register(self, definition: ScaffoldDefinition) -> None:
        if definition.scaffold_id in self._definitions:
            raise ConfigError(f"duplicate scaffold id: {definition.scaffold_id}")
        self._definitions[definition.scaffold_id] = definition

    def get(self, scaffold_id: str) -> ScaffoldDefinition:
        try:
            return self._definitions[scaffold_id]
        except KeyError as exc:
            supported = ", ".join(sorted(self._definitions))
            raise ConfigError(
                f"Unsupported scaffold_id={scaffold_id!r}. Supported scaffolds: {supported}."
            ) from exc

    def ids(self) -> list[str]:
        return sorted(self._definitions)


def default_scaffold_registry() -> ScaffoldRegistry:
    return ScaffoldRegistry()


def build_scaffold(scaffold_id: str) -> ScaffoldDefinition:
    return default_scaffold_registry().get(scaffold_id)
