"""最小 Context Builder。"""

from __future__ import annotations

from repo_harness.config import RunConfig
from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.tasks import RunnableTask
from repo_harness.workspace import RunWorkspace


class ContextBuilder:
    def build_initial_messages(
        self,
        *,
        task: RunnableTask,
        workspace: RunWorkspace,
        run_config: RunConfig,
        resolved_verifier_plan: ResolvedVerifierPlan,
        allowed_tools: list[str],
    ) -> list[dict[str, object]]:
        visible_task = task.agent_visible_view()
        system = (
            "You are RepoHarness simple_react replay agent. Use only the allowed tools. "
            "Do not access hidden evaluator metadata, baseline logs, reward metadata, or files outside "
            "the workspace."
        )
        user = {
            "task": visible_task,
            "workspace_root": workspace.workspace_path,
            "test_command": resolved_verifier_plan.verifier_config.test_command,
            "allowed_tools": allowed_tools,
            "permission_mode": run_config.runtime.permission_mode,
            "max_turns": run_config.runtime.max_turns,
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
