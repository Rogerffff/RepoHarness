"""任务定义、可运行任务和静态 verifier 配置 schema。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel
from repo_harness.schema_versions import (
    PYTEST_PARSER_VERSION,
    REAL_REPOSITORY_SOURCE_FACTS_SCHEMA_VERSION,
    SWEBENCH_LIKE_ENVIRONMENT_SPEC_VERSION,
    SWEBENCH_LIKE_TASK_FACTS_SCHEMA_VERSION,
    TASK_ADAPTER_FACTS_SCHEMA_VERSION,
    TASK_SCHEMA_VERSION,
)
from repo_harness.trajectory import ArtifactRef

Visibility = Literal["model_visible", "verifier_only", "reward_only", "hidden_reference"]
SHA256_PATTERN = r"^[0-9a-f]{64}$"


class TaskTimeouts(StrictBaseModel):
    schema_version: str = "repo_harness_task_timeouts_v0"
    setup_timeout_sec: int = Field(gt=0)
    test_timeout_sec: int = Field(gt=0)
    agent_timeout_sec: int = Field(gt=0)
    final_verifier_timeout_sec: int = Field(gt=0)

    @model_validator(mode="before")
    @classmethod
    def expand_timeout_shortcut(cls, data: Any) -> Any:
        if isinstance(data, int):
            return {
                "setup_timeout_sec": data,
                "test_timeout_sec": data,
                "agent_timeout_sec": data,
                "final_verifier_timeout_sec": data,
            }
        if isinstance(data, dict) and "timeout_sec" in data:
            timeout = data["timeout_sec"]
            expanded = {
                "setup_timeout_sec": timeout,
                "test_timeout_sec": timeout,
                "agent_timeout_sec": timeout,
                "final_verifier_timeout_sec": timeout,
            }
            expanded.update({key: value for key, value in data.items() if key != "timeout_sec"})
            return expanded
        return data


class LockfileHash(StrictBaseModel):
    schema_version: str = "repo_harness_lockfile_hash_v0"
    path: str
    sha256: str


class FixtureRepositorySource(StrictBaseModel):
    schema_version: str = "repo_harness_fixture_repository_source_v0"
    source_type: Literal["fixture_path"] = "fixture_path"
    path: str
    base_commit: str | None = None
    synthetic_base_id: str | None = None


class LocalArchiveSource(StrictBaseModel):
    schema_version: str = "repo_harness_local_archive_source_v0"
    source_type: Literal["local_archive"] = "local_archive"
    archive_path: str
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_root_directory: str
    base_commit: str | None = None
    synthetic_base_id: str | None = None
    decontamination_status: str = "unknown"
    decontamination_metadata_ref: str | None = None

    @model_validator(mode="after")
    def require_base_identity(self) -> "LocalArchiveSource":
        if not self.base_commit and not self.synthetic_base_id:
            raise ValueError("local_archive source 必须记录 base_commit 或 synthetic_base_id。")
        return self


class LocalRepositorySource(StrictBaseModel):
    schema_version: str = "repo_harness_local_repository_source_v0"
    source_type: Literal["local_repository"] = "local_repository"
    source_path: str
    current_commit: str | None = None
    working_tree_clean: bool | None = None
    allow_dirty_snapshot: bool = False
    base_commit: str | None = None
    synthetic_base_id: str | None = None
    decontamination_status: str = "unknown"
    decontamination_metadata_ref: str | None = None


class PublicSnapshotSource(StrictBaseModel):
    schema_version: str = "repo_harness_public_snapshot_source_v0"
    source_type: Literal["public_snapshot"] = "public_snapshot"
    remote_url: str
    commit_sha: str
    mirror_source: str
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_path: str | None = None
    expected_root_directory: str | None = None
    decontamination_status: str
    decontamination_metadata_ref: str | None = None
    remotes_stripped: bool = True
    branches_stripped: bool = True
    tags_stripped: bool = True


RepoSource = (
    FixtureRepositorySource
    | LocalArchiveSource
    | LocalRepositorySource
    | PublicSnapshotSource
)


class RepoMaterializationResult(StrictBaseModel):
    schema_version: str = "repo_harness_repo_materialization_result_v0"
    source_type: str
    checkout_path_status: Literal["recorded", "redacted", "unknown"] = "redacted"
    source_tree_hash: str
    base_commit: str | None = None
    synthetic_base_id: str | None = None
    source_archive_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    working_tree_clean: bool | None = None
    remotes_stripped: bool | None = None
    branches_stripped: bool | None = None
    tags_stripped: bool | None = None


class RealRepositorySourceFacts(StrictBaseModel):
    schema_version: str = REAL_REPOSITORY_SOURCE_FACTS_SCHEMA_VERSION
    source_kind: Literal["public_archive", "fixed_local_mirror"]
    remote_url: str
    base_commit: str
    dataset_source_revision: str | None = None
    archive_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    mirror_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    source_tree_hash: str = Field(pattern=SHA256_PATTERN)
    local_materialization_ref: ArtifactRef
    verifier_evidence_ref: ArtifactRef
    network_source_allowed_for_formal_run: bool = False

    @model_validator(mode="after")
    def require_fixed_source_hash(self) -> "RealRepositorySourceFacts":
        if not self.archive_sha256 and not self.mirror_sha256:
            raise ValueError("真实仓库 source facts 必须记录 archive_sha256 或 mirror_sha256。")
        if self.network_source_allowed_for_formal_run:
            raise ValueError("正式 V3 run 不能从浮动网络 source 读取源码。")
        return self


class SweBenchLikeTaskFacts(StrictBaseModel):
    schema_version: str = SWEBENCH_LIKE_TASK_FACTS_SCHEMA_VERSION
    instance_id: str
    repo: str
    base_commit: str
    dataset_name: str
    dataset_revision: str
    dataset_split: str
    task_hash: str = Field(pattern=SHA256_PATTERN)
    adapter_input_ref: ArtifactRef
    evaluator_evidence_manifest_ref: ArtifactRef
    final_only: bool = True
    model_visible_contains_hidden_material: bool = False
    benchmark_comparability: Literal["not_public_leaderboard_comparable"] = (
        "not_public_leaderboard_comparable"
    )

    @model_validator(mode="after")
    def final_only_tasks_hide_verifier_material(self) -> "SweBenchLikeTaskFacts":
        if not self.final_only:
            raise ValueError("V3 SWE-Bench-like task 必须是 final-only。")
        if self.model_visible_contains_hidden_material:
            raise ValueError("SWE-Bench-like adapter-visible facts 不能包含 hidden verifier material。")
        return self


class TaskAdapterFacts(StrictBaseModel):
    schema_version: str = TASK_ADAPTER_FACTS_SCHEMA_VERSION
    adapter_name: str
    adapter_version: str
    input_manifest_ref: ArtifactRef
    output_task_ref: ArtifactRef
    task_hash: str = Field(pattern=SHA256_PATTERN)
    visibility_policy_ref: ArtifactRef
    decontamination_evidence_refs: list[ArtifactRef] = Field(default_factory=list)
    final_only_policy: Literal["disabled_feedback_only", "not_final_only"]
    generated_task_schema_version: str = TASK_SCHEMA_VERSION


class SweBenchLikeEnvironmentSpec(StrictBaseModel):
    schema_version: str = SWEBENCH_LIKE_ENVIRONMENT_SPEC_VERSION
    instance_id: str
    repo: str
    base_commit: str
    execution_image: str
    requested_container_platform: Literal["linux/amd64", "linux/arm64"]
    python_version: str | None = None
    setup_commands_ref: ArtifactRef
    dependency_lock_ref: ArtifactRef | None = None
    network_policy: str = "deny_agent_run"
    hidden_verifier_command_visible_to_model: bool = False

    @model_validator(mode="after")
    def hidden_verifier_command_is_not_visible(self) -> "SweBenchLikeEnvironmentSpec":
        if self.hidden_verifier_command_visible_to_model:
            raise ValueError("hidden verifier command 不能进入模型可见上下文。")
        return self


class EnvironmentSpec(StrictBaseModel):
    schema_version: str = "repo_harness_environment_spec_v0"
    execution_image: str | None = None
    python_version: str | None = None
    node_version: str | None = None
    package_manager: str | None = None
    lockfile_hashes: list[LockfileHash] = Field(default_factory=list)
    setup_cache_key_inputs: list[str] = Field(default_factory=list)
    required_system_packages: list[str] = Field(default_factory=list)
    setup_network_policy: str = "deny"
    dependency_state_policy: str = "none"
    setup_artifact_hash: str | None = None
    source_archive_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    dependency_state_ref: str | None = None
    allow_dirty_dependency_state: bool = False


class VisibilityPolicy(StrictBaseModel):
    schema_version: str = "repo_harness_visibility_policy_v0"
    issue: Visibility = "model_visible"
    expected_files: Visibility = "model_visible"
    fail_to_pass_tests: Visibility = "verifier_only"
    pass_to_pass_tests: Visibility = "verifier_only"
    gold_patch: Visibility = "hidden_reference"
    decontamination: Visibility = "reward_only"


class DecontaminationMetadata(StrictBaseModel):
    schema_version: str = "repo_harness_decontamination_metadata_v0"
    status: str = "unknown"
    known_public_solution: bool | None = None
    source_url: str | None = None
    overlap_check_notes: str | None = None
    notes: str | None = None


class MutationRule(StrictBaseModel):
    schema_version: str = "repo_harness_mutation_rule_v0"
    path_pattern: str
    allowed_stage: Literal["setup", "agent_run", "final_verifier"]
    include_in_final_patch: bool
    reason: str
    artifact_policy: str = "record"

    @model_validator(mode="after")
    def final_verifier_outputs_are_not_patch(self) -> "MutationRule":
        if self.allowed_stage == "final_verifier" and self.include_in_final_patch:
            raise ValueError("final_verifier 阶段产物不能进入 final.patch。")
        return self


class TaskDefinition(StrictBaseModel):
    schema_version: str = TASK_SCHEMA_VERSION
    id: str
    task_version: str
    dataset_name: str
    source_kind: str
    dataset_split: str | None = None
    created_at: str
    repo: str
    repo_source_spec: RepoSource | None = None
    base_commit: str | None = None
    source_archive_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    issue: str
    setup_command: str | None = None
    test_command: str
    timeouts: TaskTimeouts
    environment: EnvironmentSpec
    expected_files: list[str] = Field(default_factory=list)
    fail_to_pass_tests: list[str] = Field(default_factory=list)
    pass_to_pass_tests: list[str] = Field(default_factory=list)
    gold_patch: str | None = None
    decontamination: DecontaminationMetadata = Field(default_factory=DecontaminationMetadata)
    declared_setup_mutations: list[MutationRule] = Field(default_factory=list)
    generated_files: list[MutationRule] = Field(default_factory=list)
    visibility: VisibilityPolicy
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_visibility(self) -> "TaskDefinition":
        if self.gold_patch is not None and self.visibility.gold_patch != "hidden_reference":
            raise ValueError("gold_patch 必须标记为 hidden_reference。")
        if self.visibility.fail_to_pass_tests == "model_visible":
            raise ValueError("fail_to_pass_tests 第一版不能标记为 model_visible。")
        if self.visibility.pass_to_pass_tests == "model_visible":
            raise ValueError("pass_to_pass_tests 第一版不能标记为 model_visible。")
        return self

    def to_verifier_config(self) -> "VerifierConfig":
        return VerifierConfig(
            test_command=self.test_command,
            test_timeout_sec=self.timeouts.test_timeout_sec,
            final_verifier_timeout_sec=self.timeouts.final_verifier_timeout_sec,
            fail_to_pass_tests=self.fail_to_pass_tests,
            pass_to_pass_tests=self.pass_to_pass_tests,
            visibility_policy=self.visibility,
        )


class VerifierConfig(StrictBaseModel):
    schema_version: str = "repo_harness_verifier_config_v0"
    test_command: str
    test_timeout_sec: int = Field(gt=0)
    final_verifier_timeout_sec: int = Field(gt=0)
    fail_to_pass_tests: list[str] = Field(default_factory=list)
    pass_to_pass_tests: list[str] = Field(default_factory=list)
    parser: str = "pytest"
    parser_version: str = PYTEST_PARSER_VERSION
    visibility_policy: VisibilityPolicy


class RunnableTask(StrictBaseModel):
    schema_version: str = "repo_harness_runnable_task_v0"
    task_id: str
    task_version: str
    dataset_name: str
    issue_statement: str
    repo_source: str
    repo_source_spec: RepoSource | None = None
    base_commit: str | None = None
    source_archive_sha256: str | None = None
    environment: EnvironmentSpec
    setup_command: str | None = None
    timeouts: TaskTimeouts
    verifier_config: VerifierConfig
    expected_files: list[str] = Field(default_factory=list)
    mutation_policy: list[MutationRule] = Field(default_factory=list)
    generated_files_policy: list[MutationRule] = Field(default_factory=list)
    visibility_policy: VisibilityPolicy
    decontamination_metadata: DecontaminationMetadata = Field(
        default_factory=DecontaminationMetadata
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_definition(cls, task: TaskDefinition) -> "RunnableTask":
        return cls(
            task_id=task.id,
            task_version=task.task_version,
            dataset_name=task.dataset_name,
            issue_statement=task.issue,
            repo_source=task.repo,
            repo_source_spec=task.repo_source_spec,
            base_commit=task.base_commit,
            source_archive_sha256=task.source_archive_sha256,
            environment=task.environment,
            setup_command=task.setup_command,
            timeouts=task.timeouts,
            verifier_config=task.to_verifier_config(),
            expected_files=task.expected_files,
            mutation_policy=task.declared_setup_mutations,
            generated_files_policy=task.generated_files,
            visibility_policy=task.visibility,
            decontamination_metadata=task.decontamination,
            metadata={
                "source_kind": task.source_kind,
                "dataset_split": task.dataset_split,
                "created_at": task.created_at,
                **task.metadata,
            },
        )

    def agent_visible_view(self) -> dict[str, Any]:
        """返回 Context Builder 可以使用的任务投影，不包含 evaluator-only metadata。"""

        visible: dict[str, Any] = {
            "task_id": self.task_id,
            "task_version": self.task_version,
            "dataset_name": self.dataset_name,
            "issue_statement": self.issue_statement,
            "base_commit": self.base_commit,
            "setup_command": self.setup_command,
            "test_command": self.verifier_config.test_command,
            "timeouts": self.timeouts.model_dump(mode="json"),
            "environment": self.environment.model_dump(mode="json"),
        }
        if self.visibility_policy.expected_files == "model_visible":
            visible["expected_files"] = list(self.expected_files)
        return visible
