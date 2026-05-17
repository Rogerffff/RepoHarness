from __future__ import annotations

import asyncio
import time

from repo_harness.verifier import VerifierJob, VerifierPoolOptions, VerifierResult, VerifierWorkerPool


def _result() -> VerifierResult:
    return VerifierResult.model_validate(
        {
            "verifier_stage": "final",
            "parser_confidence": 0.9,
            "command": "pytest -q",
            "test_cases": [],
            "accepted": True,
            "pass_ratio": 1.0,
            "fail_to_pass": {"passed": 1, "total": 1},
            "pass_to_pass": {"passed": 1, "total": 1},
            "exit_code": 0,
            "timeout": False,
            "error_type": None,
        }
    )


def _job(job_id: str, sleep_seconds: float = 0.0) -> VerifierJob:
    def run() -> VerifierResult:
        if sleep_seconds:
            time.sleep(sleep_seconds)
        return _result()

    return VerifierJob(
        job_id=job_id,
        run_id="stage12-5-run",
        episode_id="stage12-5-episode",
        task_id="stage12-5-task",
        verifier_stage="final",
        callable=run,
    )


def test_stage12_5_verifier_pool_records_queue_wait_and_worker_facts() -> None:
    async def scenario():
        pool = VerifierWorkerPool(
            VerifierPoolOptions(pool_id="stage12-5-pool", max_workers=1, max_pending_jobs=1)
        )
        try:
            first = asyncio.create_task(pool.run(_job("first", sleep_seconds=0.04)))
            await asyncio.sleep(0.01)
            second = asyncio.create_task(pool.run(_job("second")))
            return await asyncio.gather(first, second)
        finally:
            pool.close()

    first, second = asyncio.run(scenario())

    assert first.pool_id == "stage12-5-pool"
    assert second.queue_wait_seconds > 0.0
    assert second.worker_id == "verifier-worker-0"
    assert second.verifier_result is not None
