"""Environment specification hashing helpers."""

from __future__ import annotations

from typing import Any

from repo_harness.run_metadata.schemas import SourceCheckoutFacts
from repo_harness.schema_base import stable_hash
from repo_harness.tasks.schemas import EnvironmentSpec

ENVIRONMENT_SPEC_HASH_VERSION = "repo_harness_environment_spec_hash_v0"


def compute_environment_spec_hash(
    *,
    environment: EnvironmentSpec,
    source_checkout_facts: SourceCheckoutFacts,
    dependency_state_strategy: str,
    execution_mode: str,
    setup_artifact_hash: str = "none",
    extra: dict[str, Any] | None = None,
) -> str:
    """Return a stable hash for compare-scope environment identity."""

    payload: dict[str, Any] = {
        "hash_version": ENVIRONMENT_SPEC_HASH_VERSION,
        "environment": environment.model_dump(mode="json"),
        "source_checkout": {
            "source_kind": source_checkout_facts.source_kind,
            "source_type": source_checkout_facts.source_type,
            "base_commit": source_checkout_facts.base_commit,
            "synthetic_base_id": source_checkout_facts.synthetic_base_id,
            "source_archive_sha256": source_checkout_facts.source_archive_sha256,
            "source_tree_hash": source_checkout_facts.source_tree_hash,
            "working_tree_clean": source_checkout_facts.working_tree_clean,
            "dirty_snapshot_allowed": source_checkout_facts.dirty_snapshot_allowed,
        },
        "dependency_state_strategy": dependency_state_strategy,
        "execution_mode": execution_mode,
        "setup_artifact_hash": setup_artifact_hash,
    }
    if extra:
        payload["extra"] = extra
    return stable_hash(payload)
