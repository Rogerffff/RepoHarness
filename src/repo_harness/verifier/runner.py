"""pytest verifier runner。"""

from __future__ import annotations

import shlex
from pathlib import Path

from repo_harness.evaluation.schemas import ResolvedVerifierPlan
from repo_harness.tasks import VerifierConfig
from repo_harness.trajectory import RunRecorder
from repo_harness.verifier.acceptance import apply_acceptance_policy
from repo_harness.verifier.pytest_parser import PytestTextParser
from repo_harness.verifier.schemas import TestCaseResult, VerifierResult
from repo_harness.workspace import LocalWorkspaceAdapter


class PytestVerifier:
    """运行 pytest verifier，并生成结构化 VerifierResult。"""

    def __init__(self, workspace_adapter: LocalWorkspaceAdapter) -> None:
        self.workspace_adapter = workspace_adapter
        self.parser = PytestTextParser()

    def run_baseline(
        self,
        workspace_path: str | Path,
        verifier_config: VerifierConfig,
        recorder: RunRecorder,
    ) -> VerifierResult:
        return self._run(workspace_path, verifier_config, recorder, stage="baseline")

    def run_feedback(
        self,
        workspace_path: str | Path,
        resolved_verifier_plan: ResolvedVerifierPlan,
        recorder: RunRecorder,
    ) -> VerifierResult:
        return self._run(
            workspace_path,
            resolved_verifier_plan.verifier_config,
            recorder,
            stage="feedback",
            fail_to_pass_tests=resolved_verifier_plan.initial_fail_to_pass_tests,
            pass_to_pass_tests=resolved_verifier_plan.initial_pass_to_pass_tests,
        )

    def run_final(
        self,
        workspace_path: str | Path,
        resolved_verifier_plan: ResolvedVerifierPlan,
        recorder: RunRecorder,
    ) -> VerifierResult:
        return self._run(
            workspace_path,
            resolved_verifier_plan.verifier_config,
            recorder,
            stage="final",
            fail_to_pass_tests=resolved_verifier_plan.initial_fail_to_pass_tests,
            pass_to_pass_tests=resolved_verifier_plan.initial_pass_to_pass_tests,
        )

    def _run(
        self,
        workspace_path: str | Path,
        verifier_config: VerifierConfig,
        recorder: RunRecorder,
        *,
        stage: str,
        fail_to_pass_tests: list[str] | None = None,
        pass_to_pass_tests: list[str] | None = None,
    ) -> VerifierResult:
        fail_to_pass = fail_to_pass_tests or verifier_config.fail_to_pass_tests
        pass_to_pass = pass_to_pass_tests or verifier_config.pass_to_pass_tests
        timeout = (
            verifier_config.final_verifier_timeout_sec
            if stage == "final"
            else verifier_config.test_timeout_sec
        )
        full_result = self.workspace_adapter.run_command(
            workspace_path,
            _normalize_pytest_command(verifier_config.test_command),
            timeout_sec=timeout,
            recorder=recorder,
            command_semantics=f"verifier_{stage}",
        )
        confidence = self.parser.parser_confidence(
            full_result.stdout_preview, full_result.stderr_preview, full_result.exit_code
        )
        error_type = self.parser.error_type(
            full_result.stdout_preview,
            full_result.stderr_preview,
            full_result.exit_code,
            full_result.timeout,
        )
        test_cases = self._run_declared_tests(
            workspace_path,
            [*fail_to_pass, *pass_to_pass],
            timeout,
            recorder,
        )
        return apply_acceptance_policy(
            command=verifier_config.test_command,
            exit_code=full_result.exit_code,
            timeout=full_result.timeout,
            parser_confidence=confidence,
            test_cases=test_cases,
            fail_to_pass_tests=fail_to_pass,
            pass_to_pass_tests=pass_to_pass,
            error_type=error_type,
            verifier_stage=stage,
            raw_output_ref=full_result.output_artifact_ref,
        )

    def _run_declared_tests(
        self,
        workspace_path: str | Path,
        test_ids: list[str],
        timeout_sec: int,
        recorder: RunRecorder,
    ) -> list[TestCaseResult]:
        seen: set[str] = set()
        results: list[TestCaseResult] = []
        for test_id in test_ids:
            if test_id in seen:
                continue
            seen.add(test_id)
            command = f"python -m pytest -q {shlex.quote(test_id)}"
            execution = self.workspace_adapter.run_command(
                workspace_path,
                command,
                timeout_sec=timeout_sec,
                recorder=recorder,
                command_semantics="verifier_single_test",
            )
            if execution.timeout:
                status = "timeout"
            elif execution.exit_code == 0:
                status = "passed"
            elif execution.exit_code == 1:
                status = "failed"
            else:
                status = "error"
            failure_preview = None if status == "passed" else (
                execution.stderr_preview or execution.stdout_preview
            )
            results.append(
                TestCaseResult(
                    test_id=test_id,
                    status=status,
                    failure_preview=failure_preview,
                    raw_output_ref=execution.output_artifact_ref,
                )
            )
        return results


def _normalize_pytest_command(command: str) -> str:
    stripped = command.strip()
    if stripped == "pytest":
        return "python -m pytest"
    if stripped.startswith("pytest "):
        return "python -m pytest " + stripped[len("pytest ") :]
    return command
