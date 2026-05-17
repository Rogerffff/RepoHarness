from __future__ import annotations

import asyncio
import concurrent.futures
import json
from pathlib import Path

import repo_harness.rl.runtime as runtime_module
from repo_harness.rl import FakeLLMGateway, RepoHarnessEpisodeRequest, RepoHarnessRuntime, RepoHarnessRuntimeOptions


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"


def _episode_request() -> RepoHarnessEpisodeRequest:
    payload = json.loads((FIXTURE_ROOT / "canonical_episode_request.json").read_text(encoding="utf-8"))
    payload["run_mode"] = "training_fast"
    return RepoHarnessEpisodeRequest.model_validate(payload)


def test_stage12_5_real_episode_executor_max_workers_controls_sync_runtime(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    real_executor = concurrent.futures.ThreadPoolExecutor

    class RecordingExecutor:
        def __init__(self, *, max_workers: int, thread_name_prefix: str) -> None:
            calls.append({"event": "init", "max_workers": max_workers, "prefix": thread_name_prefix})
            self._inner = real_executor(max_workers=max_workers, thread_name_prefix=thread_name_prefix)

        def submit(self, fn, /, *args, **kwargs):
            return self._inner.submit(fn, *args, **kwargs)

        def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
            calls.append({"event": "shutdown", "wait": wait, "cancel_futures": cancel_futures})
            self._inner.shutdown(wait=wait, cancel_futures=cancel_futures)

    monkeypatch.setattr(runtime_module, "ThreadPoolExecutor", RecordingExecutor)
    runtime = RepoHarnessRuntime(
        RepoHarnessRuntimeOptions(
            runtime_execution_mode="real_episode",
            executor_max_workers=3,
            output_dir="runs/stage12-5-executor-test",
        )
    )

    first = asyncio.run(runtime.run_episode(_episode_request(), llm_gateway=FakeLLMGateway([])))
    second = asyncio.run(runtime.run_episode(_episode_request(), llm_gateway=FakeLLMGateway([])))
    runtime.close()

    assert first.status == "invalid_task"
    assert second.status == "invalid_task"
    assert calls.count({"event": "init", "max_workers": 3, "prefix": "repo-harness-real-episode"}) == 1
    assert {"event": "shutdown", "wait": False, "cancel_futures": True} in calls
