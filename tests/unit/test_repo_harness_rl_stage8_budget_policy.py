from repo_harness.budget import BudgetManager
from repo_harness.rl import (
    EpisodeBudgets,
    NoProgressPolicy,
    build_training_budget_policy,
    build_training_budget_projection,
    budget_manager_from_training_policy,
    decide_no_progress_hard_stop,
    map_budget_stop_to_episode_status,
    map_episode_status,
    recorder_event_type_for_stop_reason,
)


def test_stage8_training_fast_policy_uses_auditable_defaults() -> None:
    policy = build_training_budget_policy(EpisodeBudgets(), run_mode="training_fast")

    assert policy.max_turns == 12
    assert policy.max_model_calls == 12
    assert policy.max_tool_calls == 80
    assert policy.max_context_tokens == 32000
    assert policy.max_output_tokens == 2048
    assert policy.no_progress_policy.hard_stop_enabled is True
    assert policy.no_progress_policy.allow_training_sample is False
    assert policy.defaults_source["max_turns"] == "training_fast_default"
    assert policy.defaults_source["max_model_calls"] == "derived_from_max_turns"


def test_stage8_full_audit_policy_does_not_force_short_defaults() -> None:
    policy = build_training_budget_policy(EpisodeBudgets(), run_mode="full_audit")

    assert policy.max_turns is None
    assert policy.max_model_calls is None
    assert policy.max_tool_calls is None
    assert policy.max_context_tokens is None
    assert policy.no_progress_policy.hard_stop_enabled is False


def test_stage8_policy_projects_to_budget_manager_and_gateway_timeout() -> None:
    base = BudgetManager(
        max_turns=100,
        max_tool_calls=1000,
        max_test_runs=50,
        task_timeout_sec=3600,
        command_timeout_sec=120,
        verifier_timeout_sec=120,
        max_tool_output_chars=50000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )
    budgets = EpisodeBudgets(
        max_turns=8,
        max_model_calls=5,
        max_tool_calls=20,
        max_context_tokens=24000,
        max_tool_observation_tokens=6000,
        max_output_tokens=1024,
        generation_timeout_seconds=7,
        request_timeout_seconds=20,
    )

    policy = build_training_budget_policy(budgets, run_mode="training_fast")
    manager = budget_manager_from_training_policy(policy, base_manager=base)
    projection = build_training_budget_projection(
        budgets,
        run_mode="training_fast",
        base_budget_manager=base,
    )

    assert manager.max_turns == 8
    assert manager.max_model_calls == 5
    assert manager.max_tool_calls == 20
    assert manager.max_context_tokens == 24000
    assert manager.max_tool_output_chars == 6000
    assert projection.gateway_timeout_seconds == 7
    assert projection.sampling_params["max_output_tokens"] == 1024
    assert projection.context_config_overrides == {
        "max_context_tokens": 24000,
        "max_single_tool_result_chars": 6000,
        "max_tool_results_per_turn_chars": 6000,
    }


def test_stage8_subsecond_wall_budget_projects_to_positive_integer_seconds() -> None:
    policy = build_training_budget_policy(
        EpisodeBudgets(max_wall_seconds=0.5, max_verifier_seconds=0.25),
        run_mode="training_fast",
    )

    manager = budget_manager_from_training_policy(policy)

    assert manager.task_timeout_sec == 1
    assert manager.verifier_timeout_sec == 1

    base = BudgetManager(
        max_turns=10,
        max_tool_calls=10,
        max_test_runs=10,
        task_timeout_sec=60,
        command_timeout_sec=30,
        verifier_timeout_sec=30,
        max_tool_output_chars=4000,
        max_context_tokens=120000,
        max_output_tokens=4096,
    )
    updated = budget_manager_from_training_policy(
        build_training_budget_policy(
            EpisodeBudgets(max_wall_seconds=1.9),
            run_mode="training_fast",
        ),
        base_manager=base,
    )

    assert updated.task_timeout_sec == 2


def test_stage8_unmapped_progress_signal_does_not_hard_stop() -> None:
    decision = decide_no_progress_hard_stop(
        {
            "diagnostic_status": "no_progress_suspected",
            "signals": [{"signal_key": "near_turn_budget_with_patch"}],
        },
        NoProgressPolicy(hard_stop_enabled=True),
    )

    assert decision.hard_stop is False
    assert decision.stop_reason is None
    assert decision.signal_keys == ["near_turn_budget_with_patch"]


def test_stage8_stop_reason_mapping_keeps_status_classes_distinct() -> None:
    assert map_budget_stop_to_episode_status("no_progress_read_only_loop").episode_status == "no_progress"
    assert map_budget_stop_to_episode_status("generation_timeout_loop").episode_status == "timeout"
    assert map_budget_stop_to_episode_status("max_turns").episode_status == "timeout"
    assert map_budget_stop_to_episode_status("max_model_calls_exceeded").episode_status == "timeout"
    assert map_budget_stop_to_episode_status("max_tool_calls").episode_status == "timeout"
    assert map_budget_stop_to_episode_status("context_too_large").episode_status == "invalid"
    assert map_budget_stop_to_episode_status("context_limit").episode_status == "invalid"
    assert (
        map_budget_stop_to_episode_status("context_limit_after_reactive_compact").episode_status
        == "invalid"
    )
    assert (
        map_budget_stop_to_episode_status("context_limit_reactive_compact_disabled").episode_status
        == "invalid"
    )
    assert map_budget_stop_to_episode_status("auto_compact_failed_preflight").episode_status == "invalid"
    assert map_budget_stop_to_episode_status("reactive_compact_failed").episode_status == "invalid"
    assert map_budget_stop_to_episode_status("prompt_length_exceeded").episode_status == "invalid"
    assert map_budget_stop_to_episode_status("response_length_exceeded").episode_status == "invalid"

    assert map_episode_status(agent_stop_reason="no_progress_repeated_tool_input") == "no_progress"
    assert map_episode_status(agent_stop_reason="generation_timeout_loop") == "timeout"
    assert map_episode_status(agent_stop_reason="max_turns") == "timeout"
    assert map_episode_status(agent_stop_reason="max_model_calls_exceeded") == "timeout"
    assert map_episode_status(agent_stop_reason="max_tool_calls") == "timeout"
    assert map_episode_status(agent_stop_reason="context_limit") == "invalid"
    assert (
        map_episode_status(
            agent_stop_reason="context_limit",
            provider_error_type="context_limit",
        )
        == "invalid"
    )
    assert map_episode_status(agent_stop_reason="reactive_compact_failed") == "invalid"


def test_stage8_recorder_event_type_depends_on_stop_reason() -> None:
    assert recorder_event_type_for_stop_reason("no_progress_empty_search_loop") == "no_progress_hard_stop"
    assert recorder_event_type_for_stop_reason("generation_timeout_loop") == "generation_timeout"
    assert recorder_event_type_for_stop_reason("max_model_calls_exceeded") == "budget_hard_stop"
    assert recorder_event_type_for_stop_reason("context_limit") == "context_budget_hard_stop"
    assert recorder_event_type_for_stop_reason("prompt_length_exceeded") == "context_budget_hard_stop"
