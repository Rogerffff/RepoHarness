"""评测运行器和指标模块。"""

from repo_harness.evaluation.metrics import (
    build_metrics_record,
    derive_final_verifier_status,
)
from repo_harness.evaluation.outcome_policy import OUTCOME_POLICY_VERSION, derive_run_outcome
from repo_harness.evaluation.schemas import (
    BaselineResult,
    ExperimentConfig,
    ExperimentMinimums,
    ExperimentRunSpec,
    FeedbackPolicyConfig,
    FeedbackTestsPassedPolicy,
    ResolvedFeedbackPolicyFacts,
    ResolvedVerifierPlan,
    TestFeedbackPolicy,
)

_LAZY_EXPORTS = {
    "inspect_experiment": ("repo_harness.evaluation.experiment", "inspect_experiment"),
    "load_experiment_config": ("repo_harness.evaluation.experiment", "load_experiment_config"),
    "run_experiment": ("repo_harness.evaluation.experiment", "run_experiment"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    import importlib

    module_name, attr_name = target
    value = getattr(importlib.import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "BaselineResult",
    "ExperimentConfig",
    "ExperimentMinimums",
    "ExperimentRunSpec",
    "FeedbackPolicyConfig",
    "FeedbackTestsPassedPolicy",
    "OUTCOME_POLICY_VERSION",
    "ResolvedFeedbackPolicyFacts",
    "ResolvedVerifierPlan",
    "TestFeedbackPolicy",
    "build_metrics_record",
    "derive_final_verifier_status",
    "derive_run_outcome",
    "inspect_experiment",
    "load_experiment_config",
    "run_experiment",
]
