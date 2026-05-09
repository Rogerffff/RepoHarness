from repo_harness.budget import BudgetManager
from repo_harness.config import ContextManagementConfig, RunConfig
from repo_harness.context.budget import (
    build_provider_request_projection,
    estimate_provider_request_projection,
    resolve_context_budget,
)


def test_context_budget_uses_large_known_model_window():
    budget = resolve_context_budget(
        config=ContextManagementConfig(),
        provider="openai",
        model_id="gpt-5.5",
    )

    assert budget.model_context_window_tokens == 1_000_000
    assert budget.model_context_window_resolution == "exact_model_registry"
    assert budget.estimator_safety_margin_tokens == 30_000
    assert budget.effective_context_budget_tokens == 938_000
    assert budget.hard_context_limit_tokens == int(938_000 * 0.97)
    assert budget.post_compact_target_tokens == 300_000


def test_context_budget_harness_cap_overrides_large_model_window():
    budget = resolve_context_budget(
        config=ContextManagementConfig(harness_context_cap_tokens=120000),
        provider="openai",
        model_id="gpt-5.5",
    )

    assert budget.model_context_window_tokens == 1_000_000
    assert budget.budget_base_window_tokens == 120000
    assert budget.estimator_safety_margin_tokens == 20000
    assert budget.effective_context_budget_tokens == 68000


def test_context_budget_unknown_model_preserves_legacy_effective_default():
    budget = resolve_context_budget(
        config=ContextManagementConfig(),
        provider="local",
        model_id="unknown-model",
    )

    assert budget.model_context_window_resolution == "unknown_model_uses_legacy_default"
    assert budget.effective_context_budget_tokens == 120000


def test_provider_request_projection_estimate_includes_tool_schema_tokens():
    budget = resolve_context_budget(
        config=ContextManagementConfig(),
        provider="local",
        model_id="unknown-model",
    )
    projection = build_provider_request_projection(
        provider="openai",
        model_id="unknown-model",
        provider_message_format="repo_harness_openai_messages_v0",
        messages=[{"role": "user", "content": "short"}],
        tools=[
            {
                "name": "large_tool",
                "description": "x" * 4000,
                "input_schema": {"type": "object"},
            }
        ],
        tool_choice=None,
        generation_config={"temperature": 0.0},
        provider_model_settings={},
    )
    estimate = estimate_provider_request_projection(
        projection=projection,
        budget_facts=budget,
    )

    assert estimate.provider_request_projection_hash
    assert projection["tool_choice"] == "auto"
    assert projection["tools"][0]["type"] == "function"
    assert estimate.tool_schema_token_estimate > estimate.message_token_estimate
    assert estimate.provider_request_token_estimate >= estimate.tool_schema_token_estimate
    assert estimate.effective_context_budget_tokens == 120000


def test_budget_manager_from_run_config_uses_effective_context_budget():
    config = RunConfig.model_validate(
        {
            "model": {"provider": "openai", "model_id": "gpt-5.5"},
        }
    )
    budget = BudgetManager.from_run_config(config)

    assert budget.max_context_tokens == 938000
