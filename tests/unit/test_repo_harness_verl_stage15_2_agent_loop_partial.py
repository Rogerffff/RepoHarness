from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from verl_reference_stubs import install_reference_verl_stubs

from repo_harness.rl import RepoHarnessRuntime, RepoHarnessRuntimeOptions
from repo_harness.verifier import VerifierResult


@dataclass
class TokenOutputLike:
    token_ids: list[int]
    log_probs: list[float] | None
    stop_reason: str | None = "completed"
    extra_fields: dict[str, Any] = field(default_factory=dict)
    num_preempted: int | None = None
    routed_experts: list[Any] | None = None


class PartialSmokeServer:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        request_id: str,
        *,
        prompt_ids: list[int],
        sampling_params: dict[str, Any],
        image_data: list[Any] | None = None,
        video_data: list[Any] | None = None,
        **kwargs: Any,
    ) -> TokenOutputLike:
        self.calls.append(
            {
                "request_id": request_id,
                "prompt_ids": prompt_ids,
                "sampling_params": sampling_params,
                "kwargs": kwargs,
            }
        )
        if len(self.calls) == 1:
            return TokenOutputLike(
                token_ids=[501],
                log_probs=[-0.1],
                stop_reason="tool_calls",
                extra_fields={
                    "global_steps": 2,
                    "min_global_steps": 2,
                    "max_global_steps": 2,
                    "repo_harness_tool_calls": [
                        {
                            "tool_call_id": "call-create-fixed",
                            "tool_name": "create_file",
                            "arguments": {"path": "fixed.txt", "content": "done\n"},
                        }
                    ],
                },
            )
        return TokenOutputLike(
            token_ids=[502],
            log_probs=[-0.2],
            stop_reason="stop",
            extra_fields={"global_steps": 3, "min_global_steps": 2, "max_global_steps": 3},
        )


class FakeTokenizer:
    def decode(self, ids: list[int], skip_special_tokens: bool = True) -> str:
        return " ".join(f"tok{token_id}" for token_id in ids)


class ConfigWrap:
    def __init__(self, config: Any) -> None:
        self.config = config


def _trainer_config() -> ConfigWrap:
    rollout = SimpleNamespace(name="sglang", prompt_length=32, response_length=16)
    return ConfigWrap(config=SimpleNamespace(actor_rollout_ref=SimpleNamespace(rollout=rollout)))


def _source_repo(tmp_path: Path) -> Path:
    source = tmp_path / "source_repo"
    source.mkdir(parents=True)
    (source / "README.md").write_text("stage 15.2 tiny repo\n", encoding="utf-8")
    return source


def _runtime_options(tmp_path: Path, source: Path) -> RepoHarnessRuntimeOptions:
    def verifier_factory(context):
        def verify() -> VerifierResult:
            fixed_file = context.workspace_path / "fixed.txt"
            accepted = fixed_file.exists() and fixed_file.read_text(encoding="utf-8") == "done\n"
            return VerifierResult(
                verifier_stage="final",
                parser_confidence=1.0,
                command="python - <<'PY'\nprint('ok')\nPY",
                accepted=accepted,
                pass_ratio=1.0 if accepted else 0.0,
                fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
                pass_to_pass={"passed": 1, "total": 1},
                exit_code=0 if accepted else 1,
            )

        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=tmp_path / "runs",
        real_episode_source_resolver=lambda _request: source,
        real_episode_final_verifier_factory=verifier_factory,
        tool_observation_token_projector=lambda _content: [77_001, 77_002],
    )


def _kwargs() -> dict[str, Any]:
    return {
        "raw_prompt": [{"role": "user", "content": "create fixed.txt"}],
        "agent_name": "repo_harness",
        "task_id": "stage15-2-partial-task",
        "repo_harness_task_ref": {"task_ref": "rh://task/stage15-2-partial-task"},
        "repo_harness_run_mode": "training_fast",
        "repo_harness_runtime_execution_mode": "real_episode",
        "repo_harness_expected_route": "verl",
        "repo_harness_partial_rollout_control": {
            "enabled": True,
            "pause_wait_timeout_seconds": 2,
            "resume_wait_timeout_seconds": 5,
            "native_partial_rollout_enabled": True,
        },
        "uid": "stage15-2-uid",
        "index": 0,
        "session_id": 1,
        "global_steps": 2,
    }


def test_stage15_2_agent_loop_runs_controlled_partial_resume(monkeypatch, tmp_path: Path) -> None:
    install_reference_verl_stubs(monkeypatch)
    monkeypatch.delitem(sys.modules, "repo_harness_verl.agent_loop", raising=False)
    event_dir = tmp_path / "events"
    monkeypatch.setenv("REPO_HARNESS_STAGE15_EVENT_DIR", event_dir.as_posix())

    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop

    source = _source_repo(tmp_path)
    runtime = RepoHarnessRuntime(_runtime_options(tmp_path, source))
    server = PartialSmokeServer()
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=_trainer_config(),
        server_manager=server,
        tokenizer=FakeTokenizer(),
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap(config={"apply_chat_template_kwargs": {}}),
        runtime=runtime,
    )
    loop._build_prompt_ids_for_gateway_request = lambda request: [31, 32, 33]  # type: ignore[method-assign]

    output = asyncio.run(loop.run({"max_tokens": 4, "temperature": 0.0}, **_kwargs()))

    assert output.reward_score == 1.0
    assert output.extra_fields["repo_harness_partial_rollout_supported"] is True
    assert output.extra_fields["repo_harness_partial_rollout_status"] == "complete"
    assert output.extra_fields["repo_harness_stage15_controlled_turn_boundary_trigger_used"] is True
    assert output.extra_fields["repo_harness_stage15_native_partial_rollout_enabled"] is True
    assert output.extra_fields["repo_harness_stage15_native_abort_signal_visible_to_repo_harness"] is False
    assert output.extra_fields["repo_harness_resume_attempt_id"].endswith(":resume-0")
    assert len(server.calls) == 2

    events = [
        json.loads(line)
        for line in (event_dir / "stage15_partial_events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    event_types = [event["event_type"] for event in events]
    assert "partial_checkpoint_generated" in event_types
    assert "resume_attempted" in event_types
    assert "resumed_terminal_result" in event_types
    checkpoint_event = next(event for event in events if event["event_type"] == "partial_checkpoint_generated")
    assert checkpoint_event["policy_loss_consumed"] is False
