from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from repo_harness.rl import RepoHarnessEpisodeResult
from repo_harness_verl import (
    InMemoryFullyAsyncMessageQueueClient,
    RepoHarnessFullyAsyncQueueFacts,
    attach_queue_facts_to_rollout_sample,
    build_queue_facts_from_episode_result,
    serialize_rollout_sample_for_message_queue,
    select_valid_samples_from_message_queue,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "repo_harness_verl"
VISIBILITY_DIGEST = "sha256:stage13-3a-visibility"


def _episode_result(suffix: str) -> RepoHarnessEpisodeResult:
    payload: dict[str, Any] = json.loads((FIXTURE_ROOT / "canonical_episode_result.json").read_text(encoding="utf-8"))
    payload["episode_id"] = f"stage13-3a-filter-episode-{suffix}"
    payload["run_id"] = f"stage13-3a-filter-run-{suffix}"
    payload["task_id"] = f"stage13-3a-filter-task-{suffix}"
    payload["training_view"]["online_rl_eligible"] = True
    payload["training_view"]["extra_fields"] = {
        **payload["training_view"]["extra_fields"],
        "repo_harness_episode_id": payload["episode_id"],
        "repo_harness_run_id": payload["run_id"],
        "repo_harness_task_id": payload["task_id"],
        "repo_harness_llm_gateway_route": "verl",
    }
    return RepoHarnessEpisodeResult.model_validate(payload)


def _rollout_sample(sample_id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        full_batch=SimpleNamespace(
            batch={"responses": [[1, 2]], "response_mask": [[1, 1]]},
            non_tensor_batch={},
            meta_info={"metrics": [{"generate_sequences": 0.1, "tool_calls": 0.0}]},
        ),
        sample_id=sample_id,
        epoch=0,
        rollout_status={},
    )


def _rejected_facts(suffix: str, reason: str, *, diagnostic: bool = False) -> RepoHarnessFullyAsyncQueueFacts:
    return RepoHarnessFullyAsyncQueueFacts(
        sample_id=f"stage13-3a-filter-{suffix}",
        sample_attempt_id=f"stage13-3a-filter-{suffix}:attempt-0",
        episode_id=f"stage13-3a-filter-{suffix}",
        run_id=f"stage13-3a-filter-run-{suffix}",
        task_id=f"stage13-3a-filter-task-{suffix}",
        dataset_uid=f"stage13-3a-filter-task-{suffix}",
        rollout_uid=f"stage13-3a-filter-run-{suffix}",
        visibility_scan_status="passed",
        visibility_scan_digest=VISIBILITY_DIGEST,
        sample_classification="diagnostic" if diagnostic else "rejected",
        rejection_reason=None if diagnostic else reason,
        invalid_reason=reason,
    )


async def _put_facts(
    queue: InMemoryFullyAsyncMessageQueueClient,
    facts: RepoHarnessFullyAsyncQueueFacts,
    *,
    ledger: bool = True,
) -> None:
    sample = attach_queue_facts_to_rollout_sample(_rollout_sample(facts.sample_id), facts)
    payload = serialize_rollout_sample_for_message_queue(
        sample,
        visibility_scan_status="passed",
        visibility_scan_digest=VISIBILITY_DIGEST,
        serializer="pickle",
    )
    if ledger:
        await queue.put_sample(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
        )
    else:
        await queue.put_sample(payload)


def test_stage13_3a_trainer_side_filter_reads_past_invalid_backlog_until_required_valid_count() -> None:
    async def scenario() -> None:
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=16)
        valid_a = build_queue_facts_from_episode_result(
            _episode_result("valid-a"),
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
            current_global_steps=10,
            staleness_threshold=2,
        )
        valid_b = build_queue_facts_from_episode_result(
            _episode_result("valid-b"),
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
            current_global_steps=10,
            staleness_threshold=2,
        )
        backlog = [
            valid_a,
            _rejected_facts("invalid-training", "invalid_for_training"),
            _rejected_facts("missing-logprobs", "missing_response_logprobs"),
            _rejected_facts("non-verl-route", "non_verl_route_invalid_for_online_rl"),
            _rejected_facts("partial", "partial_rollout_unsupported_in_stage13_3_a"),
            _rejected_facts("stale", "stale_trajectory"),
            _rejected_facts("visibility", "visibility_rejected_or_malformed_visibility_payload"),
            _rejected_facts("pending", "pending_reward_or_pending_finality"),
            _rejected_facts("cancelled", "episode_status_cancelled", diagnostic=True),
            _rejected_facts("timeout", "episode_status_timeout", diagnostic=True),
            _rejected_facts("diagnostic", "diagnostic_only", diagnostic=True),
            valid_b,
        ]
        for index, facts in enumerate(backlog):
            await _put_facts(queue, facts, ledger=facts.sample_id != "stage13-3a-filter-visibility")

        selected, report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=2,
            current_global_steps=10,
            staleness_threshold=2,
            serializer="pickle",
            max_dequeue_count=16,
        )

        assert [item.sample_id for item in selected] == [valid_a.sample_id, valid_b.sample_id]
        assert report.valid_sample_count == 2
        assert report.observed_queue_samples == len(backlog)
        assert report.rejected_sample_count >= 6
        assert report.diagnostic_sample_count >= 2
        assert any("missing_external_visibility_scan_ledger" in reason for reason in report.rejected_reasons.values())
        assert "stage13-3a-filter-pending" in report.rejected_reasons

    asyncio.run(scenario())


def test_stage13_3a_filter_reports_insufficient_valid_samples_without_using_bad_occupancy() -> None:
    async def scenario() -> None:
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        await _put_facts(queue, _rejected_facts("invalid-a", "missing_response_logprobs"))
        await _put_facts(queue, _rejected_facts("invalid-b", "non_verl_route_invalid_for_online_rl"))
        await queue.put_sample(None)

        selected, report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=1,
            serializer="pickle",
        )

        assert selected == []
        assert report.valid_sample_count == 0
        assert report.insufficient_valid_samples is True
        assert report.insufficient_reason == "insufficient_valid_queue_samples"

    asyncio.run(scenario())


def test_stage13_3a_queue_ledger_is_consumed_per_entry_not_reused_by_payload_digest() -> None:
    async def scenario() -> None:
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        facts = build_queue_facts_from_episode_result(
            _episode_result("duplicate-ledger"),
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
            current_global_steps=10,
            staleness_threshold=2,
        )
        sample = attach_queue_facts_to_rollout_sample(_rollout_sample(facts.sample_id), facts)
        payload = serialize_rollout_sample_for_message_queue(
            sample,
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
            serializer="pickle",
        )

        await queue.put_sample(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
        )
        first_selected, first_report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=1,
            current_global_steps=10,
            staleness_threshold=2,
            serializer="pickle",
        )
        assert [item.sample_id for item in first_selected] == [facts.sample_id]
        assert first_report.valid_sample_count == 1

        await queue.put_sample(payload)
        await queue.put_sample(None)
        second_selected, second_report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=1,
            current_global_steps=10,
            staleness_threshold=2,
            serializer="pickle",
        )

        assert second_selected == []
        assert second_report.valid_sample_count == 0
        assert second_report.rejected_sample_count == 1
        assert any(
            "missing_external_visibility_scan_ledger" in reason
            for reason in second_report.rejected_reasons.values()
        )

    asyncio.run(scenario())


def test_stage13_3a_explicit_ledger_callback_does_not_leave_internal_ledger_for_duplicate_payload() -> None:
    async def scenario() -> None:
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)
        facts = build_queue_facts_from_episode_result(
            _episode_result("mixed-ledger"),
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
            current_global_steps=10,
            staleness_threshold=2,
        )
        sample = attach_queue_facts_to_rollout_sample(_rollout_sample(facts.sample_id), facts)
        payload = serialize_rollout_sample_for_message_queue(
            sample,
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
            serializer="pickle",
        )

        await queue.put_sample(
            payload,
            visibility_scan_status="passed",
            visibility_scan_digest=VISIBILITY_DIGEST,
        )
        first_selected, first_report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=1,
            visibility_scan_ledger=lambda _payload: ("passed", VISIBILITY_DIGEST),
            current_global_steps=10,
            staleness_threshold=2,
            serializer="pickle",
        )
        assert [item.sample_id for item in first_selected] == [facts.sample_id]
        assert first_report.valid_sample_count == 1

        await queue.put_sample(payload)
        await queue.put_sample(None)
        second_selected, second_report = await select_valid_samples_from_message_queue(
            queue,
            required_samples=1,
            current_global_steps=10,
            staleness_threshold=2,
            serializer="pickle",
        )

        assert second_selected == []
        assert second_report.valid_sample_count == 0
        assert any(
            "missing_external_visibility_scan_ledger" in reason
            for reason in second_report.rejected_reasons.values()
        )

    asyncio.run(scenario())


def test_stage13_3a_filter_empty_queue_uses_bounded_default_dequeue_timeout() -> None:
    async def scenario() -> None:
        queue = InMemoryFullyAsyncMessageQueueClient(max_queue_size=4)

        selected, report = await asyncio.wait_for(
            select_valid_samples_from_message_queue(
                queue,
                required_samples=1,
                serializer="pickle",
            ),
            timeout=2,
        )

        assert selected == []
        assert report.valid_sample_count == 0
        assert report.insufficient_valid_samples is True
        assert report.insufficient_reason == "insufficient_valid_queue_samples"
        assert report.rejected_reasons == {"queue-timeout-0": "queue_get_timeout"}

    asyncio.run(scenario())
