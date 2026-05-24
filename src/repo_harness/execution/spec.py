"""Shared episode execution specification schema for evaluation and RL paths."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal

from pydantic import Field, model_validator

from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.schema_base import StrictBaseModel, stable_hash
from repo_harness.tools import build_tool

if TYPE_CHECKING:
    from repo_harness.rl.episode import RepoHarnessEpisodeRequest


SpecRawPromptSource = Literal["external", "episode_execution_spec"]

_INITIAL_MESSAGE_FORBIDDEN_EXACT_MARKERS = (
    "hidden_verifier",
    "hiddenVerifier",
    "hidden_test_selector",
    "hidden_test_patch",
    "gold_patch",
    "test_patch",
    "accepted_label",
    "reward_metadata",
    "complete_reward_metadata",
    "provider_secret",
    "final_verifier_artifact",
    "reward_metadata_artifact",
    "repo-harness-run",
    ".repo_harness_runtime",
    ".repo-harness-runtime",
    ".repo_harness_env_overlay",
    "runtime_private",
    "runtime-private:",
    "runtime-private/",
    "runtimePrivate",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
)
_INITIAL_MESSAGE_FORBIDDEN_NORMALIZED_MARKERS = (
    "hidden_verifier",
    "hidden_test_selector",
    "hidden_test_patch",
    "gold_patch",
    "test_patch",
    "accepted_label",
    "reward_metadata",
    "complete_reward_metadata",
    "provider_secret",
    "final_verifier_artifact",
    "reward_metadata_artifact",
)
_INITIAL_MESSAGE_FORBIDDEN_PATH_PATTERN = re.compile(
    r"(?i)(^|[\s\"'=:])("
    r"/[A-Za-z0-9._-]+(?:/|$)|"
    r"/Users(?:/|$)|"
    r"/private(?:/|$)|"
    r"/workspace(?:/|$)|"
    r"/testbed(?:/|$)|"
    r"/root(?:/|$)|"
    r"/home/|"
    r"/tmp/|"
    r"/var/folders/|"
    r"/opt(?:/|$)|"
    r"/mnt(?:/|$)|"
    r"/Volumes(?:/|$)|"
    r"[A-Z]:\\"
    r")"
)
_INITIAL_MESSAGE_FORBIDDEN_TEST_MARKERS = re.compile(
    r"(?i)(fail[\s_-]*to[\s_-]*pass|pass[\s_-]*to[\s_-]*pass|"
    r"tests?/[^\s\"']*hidden[^\s\"']*(::[^\s\"']*)?)"
)
_INITIAL_MESSAGE_FORBIDDEN_RUNTIME_PRIVATE_REF = re.compile(
    r"(?i)runtime[\s_-]*private\s+"
    r"(artifact|ref|reference|opaque|path|directory|dir|evidence|payload)\b"
)


def _canonical_model_dump(model: StrictBaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=True)


def compute_spec_payload_sha256(payload: dict[str, Any]) -> str:
    """Hash an EpisodeExecutionSpec payload without self-referential digest fields."""

    canonical = dict(payload)
    canonical.pop("spec_payload_sha256", None)
    canonical.pop("runtime_resolved_verifier_plan", None)
    return stable_hash(canonical)


def _collect_visible_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(_collect_visible_text(item))
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(_collect_visible_text(item) for item in value)
    return ""


def _normalize_visibility_marker(value: str) -> str:
    normalized_chars = [ch.lower() if ch.isalnum() else "_" for ch in value]
    return "_".join(part for part in "".join(normalized_chars).split("_") if part)


def _validate_initial_messages_model_visible(initial_messages: list[dict[str, Any]]) -> None:
    visible_text = _collect_visible_text(initial_messages)
    normalized_text = _normalize_visibility_marker(visible_text)
    compact_text = normalized_text.replace("_", "")
    if _INITIAL_MESSAGE_FORBIDDEN_PATH_PATTERN.search(visible_text):
        raise ValueError("initial_messages contain forbidden local path marker")
    if _INITIAL_MESSAGE_FORBIDDEN_TEST_MARKERS.search(visible_text):
        raise ValueError("initial_messages contain hidden verifier test marker")
    if _INITIAL_MESSAGE_FORBIDDEN_RUNTIME_PRIVATE_REF.search(visible_text):
        raise ValueError("initial_messages contain runtime-private reference marker")
    for marker in _INITIAL_MESSAGE_FORBIDDEN_EXACT_MARKERS:
        if marker in visible_text:
            raise ValueError(f"initial_messages contain evaluator-only marker: {marker}")
    for marker in _INITIAL_MESSAGE_FORBIDDEN_NORMALIZED_MARKERS:
        normalized_marker = _normalize_visibility_marker(marker)
        compact_marker = normalized_marker.replace("_", "")
        if (
            (normalized_marker and normalized_marker in normalized_text)
            or (compact_marker and compact_marker in compact_text)
        ):
            raise ValueError(f"initial_messages contain evaluator-only marker: {marker}")


def _validate_no_runtime_hidden_test_selectors(
    initial_messages: list[dict[str, Any]],
    resolved_verifier_plan: ResolvedVerifierPlan | None,
) -> None:
    if resolved_verifier_plan is None:
        return
    visible_text = _collect_visible_text(initial_messages)
    selectors: set[str] = set()
    for candidate in (
        *resolved_verifier_plan.initial_fail_to_pass_tests,
        *resolved_verifier_plan.initial_pass_to_pass_tests,
        *resolved_verifier_plan.verifier_config.fail_to_pass_tests,
        *resolved_verifier_plan.verifier_config.pass_to_pass_tests,
    ):
        if candidate:
            selectors.add(str(candidate))
    for selector in selectors:
        if selector and selector in visible_text:
            raise ValueError("initial_messages contain runtime hidden verifier selector")


def build_tool_schema_snapshot(allowed_tool_names: list[str]) -> list[dict[str, Any]]:
    snapshot: list[dict[str, Any]] = []
    for name in allowed_tool_names:
        definition = build_tool(name)
        snapshot.append(
            {
                "name": definition.name,
                "tool_version": definition.tool_version,
                "description": definition.model_visible_description,
                "model_visible_prompt": definition.model_visible_prompt,
                "input_schema": definition.input_schema,
                "output_schema": definition.output_schema,
                "read_only": definition.is_read_only,
                "destructive": definition.is_destructive,
            }
        )
    return snapshot


def build_tool_schema_snapshot_digest(allowed_tool_names: list[str]) -> str:
    return stable_hash(build_tool_schema_snapshot(allowed_tool_names))


def build_tool_registry_digest(allowed_tool_names: list[str]) -> str:
    return stable_hash(
        {
            "registry_kind": "repo_harness_tool_registry",
            "allowed_tool_names": list(allowed_tool_names),
            "tool_schema_snapshot_digest": build_tool_schema_snapshot_digest(allowed_tool_names),
        }
    )


class EpisodeExecutionSpecTaskFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_task_facts_v0"
    task_id: str
    task_ref: str | None = None
    task_definition_sha256: str
    dataset_name: str | None = None
    repo_ref: str | None = None
    base_commit: str | None = None
    source_archive_sha256: str | None = None


class EpisodeExecutionSpecRunConfigFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_run_config_facts_v0"
    run_id: str
    run_config_ref: str | None = None
    run_config_sha256: str
    scaffold_id: str
    permission_mode: str
    network_policy: str
    run_mode_hint: str | None = None


class EpisodeExecutionSpecToolFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_tool_facts_v0"
    allowed_tool_names: list[str] = Field(default_factory=list)
    tool_registry_digest: str
    tool_schema_snapshot_digest: str

    @model_validator(mode="after")
    def validate_tool_digests(self) -> "EpisodeExecutionSpecToolFacts":
        expected_schema_digest = build_tool_schema_snapshot_digest(self.allowed_tool_names)
        if self.tool_schema_snapshot_digest != expected_schema_digest:
            raise ValueError("tool_schema_snapshot_digest does not match allowed_tool_names")
        expected_registry_digest = build_tool_registry_digest(self.allowed_tool_names)
        if self.tool_registry_digest != expected_registry_digest:
            raise ValueError("tool_registry_digest does not match allowed_tool_names")
        return self


class EpisodeExecutionSpecContextFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_context_facts_v0"
    initial_messages_digest: str
    raw_prompt_digest: str
    public_environment_context_digest: str | None = None


class EpisodeExecutionSpecVerifierFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_verifier_facts_v0"
    resolved_verifier_plan_digest: str
    resolved_verifier_plan_ref: str | None = None


class EpisodeExecutionSpecFeedbackFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_feedback_facts_v0"
    test_feedback_policy: str
    feedback_tests_passed_policy: str


class EpisodeExecutionSpecBudgetFacts(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_budget_facts_v0"
    max_turns: int | None = None
    max_tool_calls: int | None = None
    max_test_runs: int | None = None
    max_tool_output_chars: int | None = None


class EpisodeExecutionSpec(StrictBaseModel):
    schema_version: str = "repo_harness_episode_execution_spec_v0"
    spec_id: str
    spec_payload_sha256: str | None = None
    task_facts: EpisodeExecutionSpecTaskFacts
    run_config_facts: EpisodeExecutionSpecRunConfigFacts
    tool_facts: EpisodeExecutionSpecToolFacts
    context_facts: EpisodeExecutionSpecContextFacts
    verifier_facts: EpisodeExecutionSpecVerifierFacts
    feedback_facts: EpisodeExecutionSpecFeedbackFacts
    budget_facts: EpisodeExecutionSpecBudgetFacts
    provider_route_policy: str | None = None
    diagnostic_only_reason: str | None = None
    initial_messages: list[dict[str, Any]] = Field(default_factory=list)
    runtime_resolved_verifier_plan: ResolvedVerifierPlan | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="after")
    def validate_spec_digest(self) -> "EpisodeExecutionSpec":
        payload = self.model_dump(mode="json", exclude_none=True)
        expected = compute_spec_payload_sha256(payload)
        if self.spec_payload_sha256 is None:
            self.spec_payload_sha256 = expected
        elif self.spec_payload_sha256 != expected:
            raise ValueError("spec_payload_sha256 does not match canonical spec payload")
        if self.context_facts.initial_messages_digest != stable_hash(self.initial_messages):
            raise ValueError("initial_messages_digest does not match initial_messages")
        if self.context_facts.raw_prompt_digest != self.context_facts.initial_messages_digest:
            raise ValueError("raw_prompt_digest must match initial_messages_digest in Stage 16F.2")
        _validate_initial_messages_model_visible(self.initial_messages)
        _validate_no_runtime_hidden_test_selectors(self.initial_messages, self.runtime_resolved_verifier_plan)
        if self.run_config_facts.run_id and not self.spec_id:
            raise ValueError("spec_id is required")
        return self

    @property
    def task_id(self) -> str:
        return self.task_facts.task_id

    @property
    def run_id(self) -> str:
        return self.run_config_facts.run_id

    @property
    def allowed_tool_names(self) -> list[str]:
        return list(self.tool_facts.allowed_tool_names)

    def public_artifact_payload(self) -> dict[str, Any]:
        """Return the public-safe payload; runtime verifier objects are excluded."""

        payload = self.model_dump(mode="json", exclude_none=True)
        EpisodeExecutionSpec.model_validate(payload)
        _validate_no_runtime_hidden_test_selectors(self.initial_messages, self.runtime_resolved_verifier_plan)
        return payload


def validate_request_execution_spec_binding(
    request: "RepoHarnessEpisodeRequest",
    spec: EpisodeExecutionSpec,
) -> None:
    """Fail closed when a runtime request and execution spec disagree."""

    mismatches: list[str] = []
    if request.episode_execution_spec_sha256 and request.episode_execution_spec_sha256 != spec.spec_payload_sha256:
        mismatches.append("episode_execution_spec_sha256")
    if request.task_id != spec.task_facts.task_id:
        mismatches.append("task_id")
    if request.run_id != spec.run_config_facts.run_id:
        mismatches.append("run_id")
    if request.task_ref.task_ref and spec.task_facts.task_ref and request.task_ref.task_ref != spec.task_facts.task_ref:
        mismatches.append("task_ref")
    if request.task_ref.repo_ref and spec.task_facts.repo_ref and request.task_ref.repo_ref != spec.task_facts.repo_ref:
        mismatches.append("repo_ref")
    if request.task_ref.repo_ref and not spec.task_facts.repo_ref:
        mismatches.append("repo_ref_missing_from_spec")
    if request.task_ref.base_commit and spec.task_facts.base_commit and request.task_ref.base_commit != spec.task_facts.base_commit:
        mismatches.append("base_commit")
    if request.task_ref.base_commit and not spec.task_facts.base_commit:
        mismatches.append("base_commit_missing_from_spec")
    if (
        request.task_ref.source_archive_ref
        and spec.task_facts.source_archive_sha256
        and request.task_ref.source_archive_ref != spec.task_facts.source_archive_sha256
    ):
        mismatches.append("source_archive_ref")
    if request.task_ref.task_path and not request.task_definition_sha256:
        mismatches.append("task_definition_sha256_required_for_task_path")
    if request.task_definition_sha256 and request.task_definition_sha256 != spec.task_facts.task_definition_sha256:
        mismatches.append("task_definition_sha256")
    if request.run_config_sha256 and request.run_config_sha256 != spec.run_config_facts.run_config_sha256:
        mismatches.append("run_config_sha256")
    if request.permission_mode and request.permission_mode != spec.run_config_facts.permission_mode:
        mismatches.append("permission_mode")
    if request.network_policy and request.network_policy != spec.run_config_facts.network_policy:
        mismatches.append("network_policy")
    if request.run_mode_hint and request.run_mode_hint != spec.run_config_facts.run_mode_hint:
        mismatches.append("run_mode_hint")
    if request.allowed_tool_names and list(request.allowed_tool_names) != spec.tool_facts.allowed_tool_names:
        mismatches.append("allowed_tool_names")
    if request.tool_registry_digest and request.tool_registry_digest != spec.tool_facts.tool_registry_digest:
        mismatches.append("tool_registry_digest")
    if (
        request.resolved_verifier_plan_digest
        and request.resolved_verifier_plan_digest != spec.verifier_facts.resolved_verifier_plan_digest
    ):
        mismatches.append("resolved_verifier_plan_digest")
    if request.test_feedback_policy and request.test_feedback_policy != spec.feedback_facts.test_feedback_policy:
        mismatches.append("test_feedback_policy")
    if (
        request.feedback_tests_passed_policy
        and request.feedback_tests_passed_policy != spec.feedback_facts.feedback_tests_passed_policy
    ):
        mismatches.append("feedback_tests_passed_policy")
    budget_pairs = {
        "max_turns": (request.budgets.max_turns, spec.budget_facts.max_turns),
        "max_tool_calls": (request.budgets.max_tool_calls, spec.budget_facts.max_tool_calls),
        "max_test_runs": (request.budgets.max_test_runs, spec.budget_facts.max_test_runs),
        "max_tool_output_chars": (
            request.budgets.max_tool_observation_tokens,
            spec.budget_facts.max_tool_output_chars,
        ),
    }
    for field_name, (request_value, spec_value) in budget_pairs.items():
        if request_value is not None and spec_value is not None and request_value != spec_value:
            mismatches.append(field_name)
    if request.raw_prompt:
        request_raw_prompt_digest = stable_hash(request.raw_prompt)
        if request_raw_prompt_digest != spec.context_facts.raw_prompt_digest:
            mismatches.append("raw_prompt_digest")
    if mismatches:
        joined = ", ".join(sorted(set(mismatches)))
        raise ValueError(f"episode_execution_spec_binding_mismatch: {joined}")


def validate_episode_execution_spec_runtime_binding(spec: EpisodeExecutionSpec) -> EpisodeExecutionSpec:
    """Revalidate public payload and runtime-only verifier object binding."""

    payload = spec.model_dump(mode="json", exclude_none=True)
    payload["runtime_resolved_verifier_plan"] = spec.runtime_resolved_verifier_plan
    parsed = EpisodeExecutionSpec.model_validate(payload)
    if parsed.runtime_resolved_verifier_plan is None:
        raise ValueError("episode_execution_spec_missing_runtime_resolved_verifier_plan")
    verifier_digest = stable_hash(parsed.runtime_resolved_verifier_plan.model_dump(mode="json"))
    if verifier_digest != parsed.verifier_facts.resolved_verifier_plan_digest:
        raise ValueError("episode_execution_spec_verifier_plan_digest_mismatch")
    return parsed
