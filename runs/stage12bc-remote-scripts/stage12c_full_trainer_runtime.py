"""Runtime helper for Stage 12-C full trainer step smoke on the remote GPU box."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from repo_harness.rl import RepoHarnessRuntimeOptions
from repo_harness.verifier import VerifierResult
from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop


def _source_map() -> dict[str, str]:
    path = os.environ.get("STAGE12C_SOURCE_MAP_JSON")
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_resolver(request: Any) -> str | None:
    return _source_map().get(str(request.task_id))


def _verifier_result_from_pytest(workspace_path: Path) -> VerifierResult:
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=45,
        check=False,
    )
    accepted = completed.returncode == 0
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=1.0,
        command=f"{sys.executable} -m pytest -q",
        accepted=accepted,
        pass_ratio=1.0 if accepted else 0.0,
        fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
        pass_to_pass={"passed": 1 if accepted else 0, "total": 1},
        exit_code=completed.returncode,
        error_type=None if accepted else "test_command_error",
    )


def _verifier_factory(context: Any):
    def verify() -> VerifierResult:
        return _verifier_result_from_pytest(Path(context.workspace_path))

    return verify


class Stage12CRepoHarnessAgentLoop(RepoHarnessVerlAgentLoop):
    """RepoHarness agent loop with runtime-only real episode options."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        tokenizer = kwargs.get("tokenizer")
        if tokenizer is None:
            raise RuntimeError("Stage12CRepoHarnessAgentLoop requires tokenizer in hydra kwargs")
        real_runs_dir = os.environ.get("STAGE12C_REAL_RUNS_DIR")
        if not real_runs_dir:
            raise RuntimeError("STAGE12C_REAL_RUNS_DIR is required")

        def project_tool_observation(content: str) -> list[int]:
            return list(tokenizer.encode(str(content), add_special_tokens=False))[:96]

        runtime_options = RepoHarnessRuntimeOptions(
            runtime_execution_mode="real_episode",
            output_dir=real_runs_dir,
            real_episode_source_resolver=_source_resolver,
            real_episode_final_verifier_factory=_verifier_factory,
            tool_observation_token_projector=project_tool_observation,
            episode_timeout_seconds=300.0,
            executor_max_workers=1,
        )
        super().__init__(
            *args,
            runtime_options=runtime_options,
            inference_backend="sglang",
            **kwargs,
        )
