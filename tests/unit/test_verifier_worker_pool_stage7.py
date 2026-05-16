import asyncio
import time

import pytest

from repo_harness.verifier import (
    VerifierJob,
    VerifierPoolOptions,
    VerifierResult,
    VerifierWorkerPool,
    VerifierWorkerPoolClosedError,
)


def _verifier_result(**updates):
    payload = {
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
    payload.update(updates)
    return VerifierResult.model_validate(payload)


def _job(job_id: str, callable):
    return VerifierJob(
        job_id=job_id,
        run_id="stage7-run",
        episode_id="stage7-episode",
        task_id="stage7-task",
        verifier_stage="final",
        callable=callable,
    )


def test_stage7_worker_pool_records_worker_facts_and_queue_wait() -> None:
    async def scenario():
        pool = VerifierWorkerPool(
            VerifierPoolOptions(max_workers=1, max_pending_jobs=1, queue_timeout_seconds=1.0)
        )
        try:
            first = asyncio.create_task(pool.run(_job("first", lambda: (time.sleep(0.05), _verifier_result())[1])))
            await asyncio.sleep(0.01)
            second = asyncio.create_task(pool.run(_job("second", _verifier_result)))
            return await asyncio.gather(first, second)
        finally:
            pool.close()

    first_result, second_result = asyncio.run(scenario())

    assert first_result.pool_id == "verifier-pool-local-v1"
    assert first_result.worker_id == "verifier-worker-0"
    assert first_result.verifier_result is not None
    assert second_result.worker_id == "verifier-worker-0"
    assert second_result.queue_wait_seconds > 0.0
    assert second_result.execution_seconds >= 0.0


def test_stage7_worker_pool_queue_timeout_happens_before_unbounded_executor_queue() -> None:
    second_callable_count = 0

    def second_callable():
        nonlocal second_callable_count
        second_callable_count += 1
        return _verifier_result()

    async def scenario():
        pool = VerifierWorkerPool(
            VerifierPoolOptions(max_workers=1, max_pending_jobs=0, queue_timeout_seconds=0.01)
        )
        try:
            first = asyncio.create_task(pool.run(_job("first", lambda: (time.sleep(0.08), _verifier_result())[1])))
            await asyncio.sleep(0.01)
            second = await pool.run(_job("second", second_callable))
            first_result = await first
            return first_result, second
        finally:
            pool.close()

    first_result, second_result = asyncio.run(scenario())

    assert first_result.verifier_result is not None
    assert second_result.error_type == "queue_timeout"
    assert second_result.timeout is True
    assert second_result.verifier_result is None
    assert second_callable_count == 0
    assert "not submitted to executor" in " ".join(second_result.diagnostics)


def test_stage7_worker_pool_callable_exception_is_structured() -> None:
    def fail():
        raise RuntimeError("verifier boom")

    async def scenario():
        pool = VerifierWorkerPool(VerifierPoolOptions(max_workers=1))
        try:
            return await pool.run(_job("failure", fail))
        finally:
            pool.close()

    result = asyncio.run(scenario())

    assert result.error_type == "pool_executor_error"
    assert result.error_message == "verifier boom"
    assert result.verifier_result is None


def test_stage7_worker_pool_pending_timeout_before_worker_start_never_executes_later() -> None:
    second_callable_count = 0

    def second_callable():
        nonlocal second_callable_count
        second_callable_count += 1
        return _verifier_result()

    async def scenario():
        pool = VerifierWorkerPool(
            VerifierPoolOptions(max_workers=1, max_pending_jobs=1, queue_timeout_seconds=0.02)
        )
        try:
            first = asyncio.create_task(pool.run(_job("first", lambda: (time.sleep(0.08), _verifier_result())[1])))
            await asyncio.sleep(0.01)
            second = await pool.run(_job("second", second_callable))
            await first
            await asyncio.sleep(0.03)
            return second, second_callable_count
        finally:
            pool.close()

    result, count_after_first_and_wait = asyncio.run(scenario())

    assert result.error_type == "queue_timeout"
    assert result.started_at_seconds is None
    assert result.queue_wait_seconds > 0.0
    assert result.execution_seconds == 0.0
    assert count_after_first_and_wait == 0


def test_stage7_worker_pool_cancelled_pending_job_releases_admission_slot() -> None:
    async def scenario():
        pool = VerifierWorkerPool(
            VerifierPoolOptions(max_workers=1, max_pending_jobs=1, queue_timeout_seconds=1.0)
        )
        try:
            first = asyncio.create_task(pool.run(_job("first", lambda: (time.sleep(0.08), _verifier_result())[1])))
            await asyncio.sleep(0.01)
            pending = asyncio.create_task(pool.run(_job("pending", _verifier_result)))
            await asyncio.sleep(0.01)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            await first
            await asyncio.sleep(0.01)
            return pool._admission_slots._value
        finally:
            pool.close()

    assert asyncio.run(scenario()) == 2


def test_stage7_worker_pool_cancelled_running_job_keeps_slot_until_thread_finishes() -> None:
    async def scenario():
        pool = VerifierWorkerPool(VerifierPoolOptions(max_workers=1, max_pending_jobs=0))
        try:
            running = asyncio.create_task(pool.run(_job("running", lambda: (time.sleep(0.08), _verifier_result())[1])))
            await asyncio.sleep(0.02)
            running.cancel()
            await asyncio.sleep(0.01)
            task_done_while_thread_runs = running.done()
            value_while_thread_runs = pool._worker_slots._value
            with pytest.raises(asyncio.CancelledError):
                await running
            value_after_thread_finishes = pool._worker_slots._value
            return task_done_while_thread_runs, value_while_thread_runs, value_after_thread_finishes
        finally:
            pool.close()

    assert asyncio.run(scenario()) == (False, 0, 1)


def test_stage7_worker_pool_close_rejects_later_submission() -> None:
    async def scenario():
        pool = VerifierWorkerPool(VerifierPoolOptions(max_workers=1))
        pool.close()
        with pytest.raises(VerifierWorkerPoolClosedError):
            await pool.run(_job("after-close", _verifier_result))

    asyncio.run(scenario())


def test_stage7_verifier_job_callable_is_runtime_only_not_schema_dumped() -> None:
    job = _job("runtime-only", _verifier_result)

    async def scenario():
        pool = VerifierWorkerPool(VerifierPoolOptions(max_workers=1))
        try:
            return await pool.run(job)
        finally:
            pool.close()

    result = asyncio.run(scenario())

    assert not hasattr(job, "model_dump")
    dumped = result.model_dump(mode="json")
    assert "callable" not in dumped
    assert dumped["verifier_result"]["accepted"] is True
