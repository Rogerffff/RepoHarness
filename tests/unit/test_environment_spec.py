from repo_harness.run_metadata.schemas import SourceCheckoutFacts
from repo_harness.tasks import EnvironmentSpec
from repo_harness.tasks.environment import compute_environment_spec_hash


def test_environment_spec_hash_is_stable_for_same_inputs():
    environment = EnvironmentSpec(python_version="3.12", package_manager="pip")
    source = _source_facts(source_tree_hash="a" * 64)

    first = compute_environment_spec_hash(
        environment=environment,
        source_checkout_facts=source,
        dependency_state_strategy="none",
        execution_mode="local_process",
    )
    second = compute_environment_spec_hash(
        environment=environment,
        source_checkout_facts=source,
        dependency_state_strategy="none",
        execution_mode="local_process",
    )

    assert first == second


def test_environment_spec_hash_changes_when_dependency_state_changes():
    environment = EnvironmentSpec(python_version="3.12", package_manager="pip")
    source = _source_facts(source_tree_hash="a" * 64)

    baseline = compute_environment_spec_hash(
        environment=environment,
        source_checkout_facts=source,
        dependency_state_strategy="none",
        execution_mode="local_process",
    )
    changed = compute_environment_spec_hash(
        environment=environment,
        source_checkout_facts=source,
        dependency_state_strategy="rerun_setup",
        execution_mode="local_process",
    )

    assert baseline != changed


def test_environment_spec_hash_changes_when_source_tree_changes():
    environment = EnvironmentSpec(python_version="3.12", package_manager="pip")

    first = compute_environment_spec_hash(
        environment=environment,
        source_checkout_facts=_source_facts(source_tree_hash="a" * 64),
        dependency_state_strategy="none",
        execution_mode="local_process",
    )
    second = compute_environment_spec_hash(
        environment=environment,
        source_checkout_facts=_source_facts(source_tree_hash="b" * 64),
        dependency_state_strategy="none",
        execution_mode="local_process",
    )

    assert first != second


def _source_facts(*, source_tree_hash: str) -> SourceCheckoutFacts:
    return SourceCheckoutFacts(
        source_kind="repository_style_fixture",
        source_type="local_archive",
        synthetic_base_id="archive-v0",
        source_tree_hash=source_tree_hash,
    )
