"""Builder for shared EpisodeExecutionSpec objects."""

from __future__ import annotations

from typing import Any

from repo_harness.config import RunConfig
from repo_harness.context import ContextBuilder
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.schema_base import stable_hash
from repo_harness.scaffolds import build_scaffold, resolve_allowed_tools, resolve_feedback_policy
from repo_harness.tasks import RunnableTask
from repo_harness.tasks.public_environment import (
    PublicEnvironmentContext,
    build_public_environment_context,
)
from repo_harness.workspace import RunWorkspace, WorkspaceAdapter

from .spec import (
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
)


class EpisodeExecutionSpecBuilder:
    """Build the shared execution facts used by evaluation and RL entrypoints."""

    def build_spec_from_loaded_task(
        self,
        *,
        task: RunnableTask,
        workspace: RunWorkspace,
        run_config: RunConfig,
        resolved_verifier_plan: ResolvedVerifierPlan,
        run_id: str,
        task_ref: str | None = None,
        run_config_ref: str | None = None,
        workspace_facade: WorkspaceAdapter | None = None,
        model_visible_repo_context: dict[str, Any] | None = None,
        public_environment_context: PublicEnvironmentContext | None = None,
    ) -> EpisodeExecutionSpec:
        scaffold = build_scaffold(run_config.runtime.scaffold_id)
        feedback_policy = resolve_feedback_policy(
            run_config=run_config,
            scaffold=scaffold,
            task=task,
        )
        allowed_tools = resolve_allowed_tools(scaffold=scaffold, feedback_policy=feedback_policy)
        if public_environment_context is None:
            public_environment_context = build_public_environment_context(
                task=task,
                resolved_verifier_plan=resolved_verifier_plan,
                test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
                allowed_tools=allowed_tools,
            )
        initial_messages = ContextBuilder().build_initial_messages(
            task=task,
            workspace=workspace,
            run_config=run_config,
            resolved_verifier_plan=resolved_verifier_plan,
            allowed_tools=allowed_tools,
            scaffold=scaffold,
            workspace_facade=workspace_facade,
            model_visible_repo_context=model_visible_repo_context,
            public_environment_context=public_environment_context,
        )
        task_definition_payload = {
            "task_id": task.task_id,
            "task_version": task.task_version,
            "dataset_name": task.dataset_name,
            "issue_statement": task.issue_statement,
            "repo_source": task.repo_source,
            "base_commit": task.base_commit,
            "source_archive_sha256": task.source_archive_sha256,
            "expected_files": list(task.expected_files),
            "metadata": task.metadata,
            "visibility_policy": task.visibility_policy.model_dump(mode="json"),
            "verifier_config": task.verifier_config.model_dump(mode="json"),
        }
        task_definition_sha256 = stable_hash(task_definition_payload)
        run_config_sha256 = stable_hash(run_config.model_dump(mode="json"))
        initial_messages_digest = stable_hash(initial_messages)
        resolved_verifier_plan_digest = stable_hash(resolved_verifier_plan.model_dump(mode="json"))
        return EpisodeExecutionSpec(
            spec_id=f"{run_id}:episode-execution-spec",
            task_facts=EpisodeExecutionSpecTaskFacts(
                task_id=task.task_id,
                task_ref=task_ref,
                task_definition_sha256=task_definition_sha256,
                dataset_name=task.dataset_name,
                repo_ref=task.repo_source,
                base_commit=task.base_commit or workspace.repo_base_commit,
                source_archive_sha256=task.source_archive_sha256,
            ),
            run_config_facts=EpisodeExecutionSpecRunConfigFacts(
                run_id=run_id,
                run_config_ref=run_config_ref,
                run_config_sha256=run_config_sha256,
                scaffold_id=scaffold.scaffold_id,
                permission_mode=run_config.runtime.permission_mode,
                network_policy=run_config.workspace.network_policy,
                run_mode_hint=None,
            ),
            tool_facts=EpisodeExecutionSpecToolFacts(
                allowed_tool_names=allowed_tools,
                tool_registry_digest=build_tool_registry_digest(allowed_tools),
                tool_schema_snapshot_digest=build_tool_schema_snapshot_digest(allowed_tools),
            ),
            context_facts=EpisodeExecutionSpecContextFacts(
                initial_messages_digest=initial_messages_digest,
                raw_prompt_digest=initial_messages_digest,
                public_environment_context_digest=public_environment_context.context_digest,
            ),
            verifier_facts=EpisodeExecutionSpecVerifierFacts(
                resolved_verifier_plan_digest=resolved_verifier_plan_digest,
                resolved_verifier_plan_ref=None,
            ),
            feedback_facts=EpisodeExecutionSpecFeedbackFacts(
                test_feedback_policy=feedback_policy.resolved_test_feedback_policy.value,
                feedback_tests_passed_policy=feedback_policy.resolved_feedback_tests_passed_policy,
            ),
            budget_facts=EpisodeExecutionSpecBudgetFacts(
                max_turns=run_config.runtime.max_turns,
                max_tool_calls=run_config.runtime.max_tool_calls,
                max_test_runs=run_config.runtime.max_test_runs,
                max_tool_output_chars=run_config.workspace.max_tool_output_chars,
            ),
            provider_route_policy=run_config.model.provider,
            diagnostic_only_reason=(
                "provider_route_invalid_for_online_rl"
                if run_config.model.provider not in {"verl", "fake", "mock", "replay"}
                else None
            ),
            initial_messages=[dict(message) for message in initial_messages],
            runtime_resolved_verifier_plan=resolved_verifier_plan,
        )

    def build_spec_from_task_path_and_run_config(self, *_args: Any, **_kwargs: Any) -> EpisodeExecutionSpec:
        raise NotImplementedError(
            "Stage 16F.2 only requires loaded task construction; task-path loading belongs to Stage 16F.3."
        )
