"""Stage 15.0 static inventory for verl partial rollout integration.

This module intentionally reads ``reference/verl`` source files as text.  It
must not import verl, torch, ray, or tensordict because Stage 15.0 is a local
interface inventory stage, not a runtime smoke.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from repo_harness.schema_base import StrictBaseModel


STAGE15_0_ARTIFACTS: tuple[str, ...] = (
    "stage15_0_command_log.jsonl",
    "stage15_0_static_scan_report.json",
    "fully_async_partial_rollout_interface_inventory.json",
    "stage15_partial_rollout_patch_plan.json",
    "stage15_partial_rollout_risk_matrix.json",
    "stage15_0_acceptance_summary.json",
)

_HEAVY_MODULES: tuple[str, ...] = ("verl", "torch", "ray", "tensordict")
_PATH_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"/Users/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/workspace/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/private/[A-Za-z0-9_.\-/]+"),
    re.compile(r"/home/[A-Za-z0-9_.\-/]+"),
    re.compile(r"\.repo_harness_env_overlay"),
    re.compile(r"\.repo_harness_runtime"),
    re.compile(r"hidden_verifier", re.IGNORECASE),
    re.compile(r"gold_patch", re.IGNORECASE),
    re.compile(r"provider_secret", re.IGNORECASE),
)


class Stage15SourceEvidence(StrictBaseModel):
    source_path: str
    line: int | None = None
    line_hint: str


class Stage15BackendAbortResumeFacts(StrictBaseModel):
    backend: str
    source_path: str
    abort_all_requests_present: bool
    resume_generation_present: bool
    not_implemented: bool = False
    risk: str | None = None


class Stage15PartialRolloutInterfaceInventory(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage15_0_partial_rollout_interface_inventory_v0"
    reference_verl_root: str = "reference/verl"
    reference_verl_commit: str | None = None
    reference_verl_dirty_status: str = ""
    heavy_import_required: bool = False
    static_scan_only: bool = True
    config_inventory: dict[str, dict[str, Any]]
    native_partial_rollout_trigger_chain: dict[str, Any]
    llm_server_stop_reason_inventory: dict[str, Any]
    fully_async_rollouter_inventory: dict[str, Any]
    message_queue_trainer_inventory: dict[str, Any]
    repo_harness_agent_loop_lifecycle_inventory: dict[str, Any]
    backend_abort_resume_inventory: list[Stage15BackendAbortResumeFacts]
    source_evidence: list[Stage15SourceEvidence]
    diagnostics: list[str] = Field(default_factory=list)


class Stage15PatchCandidate(StrictBaseModel):
    patch_id: str
    target: str
    kind: str
    purpose: str
    why_needed: str
    enables: list[str]
    risks: list[str]
    compatibility_tests: list[str]
    rollback_plan: str
    patch_manifest_required: bool = True


class Stage15PartialRolloutPatchPlan(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage15_0_partial_rollout_patch_plan_v0"
    reference_verl_patch_or_wrapper_required: bool
    recommended_patch_id: str
    recommended_patch_ids: list[str]
    no_patch_required_claim_allowed: bool
    no_patch_rejection_reasons: list[str] = Field(default_factory=list)
    candidates: list[Stage15PatchCandidate]

    @model_validator(mode="after")
    def _validate_plan(self) -> "Stage15PartialRolloutPatchPlan":
        candidate_ids = {candidate.patch_id for candidate in self.candidates}
        if self.recommended_patch_id not in candidate_ids:
            raise ValueError("recommended_patch_id must reference a candidate")
        for patch_id in self.recommended_patch_ids:
            if patch_id not in candidate_ids:
                raise ValueError("recommended_patch_ids must reference candidates")
        if self.recommended_patch_id not in self.recommended_patch_ids:
            raise ValueError("recommended_patch_ids must include recommended_patch_id")
        if self.no_patch_required_claim_allowed and self.reference_verl_patch_or_wrapper_required:
            raise ValueError("no_patch_required_claim_allowed conflicts with patch_or_wrapper_required")
        return self


class Stage15RiskMatrixEntry(StrictBaseModel):
    risk_id: str
    severity: str
    failure_mode: str
    detection: str
    mitigation: str
    owner_stage: str
    acceptance_gate: str


class Stage15PartialRolloutRiskMatrix(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage15_0_partial_rollout_risk_matrix_v0"
    risks: list[Stage15RiskMatrixEntry]


class Stage15StaticScanReport(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage15_0_static_scan_report_v0"
    scanned_files: list[str]
    heavy_import_modules_forbidden: list[str]
    static_scan_only: bool = True
    diagnostics: list[str] = Field(default_factory=list)


class Stage15AcceptanceSummary(StrictBaseModel):
    schema_version: str = "repo_harness_verl_stage15_0_acceptance_summary_v0"
    stage: str = "15.0"
    passed: bool
    code_commit: str | None = None
    git_status_short: str = ""
    reference_verl_commit: str | None = None
    reference_verl_dirty_status: str = ""
    inventory_sha256: str | None = None
    patch_plan_sha256: str | None = None
    risk_matrix_sha256: str | None = None
    static_scan_report_sha256: str | None = None
    failures: list[str] = Field(default_factory=list)
    artifact_paths: dict[str, str] = Field(default_factory=dict)


def build_stage15_partial_rollout_interface_inventory(
    *,
    repo_root: str | Path | None = None,
    reference_verl_root: str | Path | None = None,
) -> Stage15PartialRolloutInterfaceInventory:
    root = _repo_root(repo_root)
    reference_root = _reference_verl_root(root, reference_verl_root)
    files = _reference_files(reference_root)
    diagnostics = _missing_file_diagnostics(files)

    texts = {key: _read_text(path) for key, path in files.items() if path.exists()}
    source_evidence: list[Stage15SourceEvidence] = []

    def evidence(key: str, needle: str, *, line_hint: str | None = None) -> Stage15SourceEvidence:
        path = files[key]
        text = texts.get(key, "")
        line = _line_number(text, needle)
        item = Stage15SourceEvidence(
            source_path=_relative_to_repo(path, root),
            line=line,
            line_hint=line_hint or needle,
        )
        source_evidence.append(item)
        return item

    config_inventory = _build_config_inventory(texts)

    trigger_chain = {
        "weight_sync_calls_checkpoint_manager_update_weights": _contains(
            texts,
            "fully_async_trainer",
            "await self.checkpoint_manager.update_weights",
        ),
        "checkpoint_manager_aborts_inflight_requests": _contains(
            texts,
            "checkpoint_engine_base",
            "abort_all_requests",
        ),
        "checkpoint_manager_abort_gated_by_partial_rollout": False,
        "server_resume_generation_after_weight_sync": _contains(
            texts,
            "checkpoint_engine_base",
            "resume_generation",
        ),
        "fully_llm_client_continue_gated_by_partial_rollout": _contains(
            texts,
            "llm_server",
            "or not self.config.async_training.partial_rollout",
        ),
        "partial_rollout_config_gate_location": _relative_to_repo(files["fully_async_config"], root),
        "abort_stop_reason_visible_to_agent_loop": False,
        "repo_harness_checkpoint_implication": (
            "参数同步中断发生在 checkpoint engine / rollout server 层，"
            "并且 abort / aborted 会被 FullyLLMServerClient 内部续生成消费；"
            "RepoHarness 不能把该底层中断直接当作 PartialEpisodeCheckpoint。"
        ),
        "evidence": [
            evidence("fully_async_trainer", "await self.checkpoint_manager.update_weights").model_dump(mode="json"),
            evidence("checkpoint_engine_base", "abort_all_requests").model_dump(mode="json"),
            evidence("checkpoint_engine_base", "resume_generation").model_dump(mode="json"),
            evidence("rollout_replica", "async def abort_all_requests").model_dump(mode="json"),
            evidence("rollout_replica", "async def resume_generation").model_dump(mode="json"),
        ],
    }

    llm_stop_inventory = {
        "base_client_class": "LLMServerClient",
        "fully_async_client_class": "FullyLLMServerClient",
        "fully_async_client_selected_by_get_client": _contains(texts, "llm_server", "return FullyLLMServerClient"),
        "abort_auto_continues_inside_fully_llm_server_client": _contains(
            texts,
            "llm_server",
            'output.stop_reason not in ("aborted", "abort")',
        ),
        "abort_visible_to_repo_harness_agent_loop": False,
        "continue_loop_gated_by_partial_rollout": _contains(
            texts,
            "llm_server",
            "self.config.async_training.partial_rollout",
        ),
        "backend_specific_stop_reason_mapping_checked": True,
        "completed_stop_reason_mapping_checked": _contains(texts, "vllm_async_server", 'stop_reason = "completed"'),
        "default_stage14_backend": "sglang",
        "normal_completion_stop_reason_by_backend": {
            "vllm": {
                "source_path": _relative_to_repo(files["vllm_async_server"], root),
                "source_evidence": 'elif finish_reason in ("stop", "length"):',
                "normalizes_stop_and_length_to_completed": _contains(
                    texts,
                    "vllm_async_server",
                    'elif finish_reason in ("stop", "length"):',
                )
                and _contains(texts, "vllm_async_server", 'stop_reason = "completed"'),
                "normal_completion_values_after_adapter": ["completed"],
            },
            "sglang": {
                "source_path": _relative_to_repo(files["sglang_async_server"], root),
                "source_evidence": "stop_reason=finish_reason,",
                "returns_raw_finish_reason": _contains(texts, "sglang_async_server", "stop_reason=finish_reason,"),
                "normal_completion_values_after_adapter": ["stop", "length"],
                "notes": (
                    "当前 Stage 14/15 默认 rollout.name=sglang；SGLang 后端返回原始 finish_reason，"
                    "不能把 vLLM 的 completed 归一化语义直接套到 SGLang。"
                ),
            },
        },
        "stop_reasons_to_inventory": ["abort", "aborted", "length", "stop", "completed"],
        "token_output_fields_to_track": [
            "token_ids",
            "log_probs",
            "num_preempted",
            "global_steps",
            "min_global_steps",
            "max_global_steps",
        ],
        "evidence": [
            evidence("llm_server", "class FullyLLMServerClient").model_dump(mode="json"),
            evidence("llm_server", 'output.stop_reason not in ("aborted", "abort")').model_dump(mode="json"),
            evidence("llm_server", "return FullyLLMServerClient").model_dump(mode="json"),
            evidence("vllm_async_server", 'stop_reason = "completed"').model_dump(mode="json"),
            evidence("sglang_async_server", "stop_reason=finish_reason,").model_dump(mode="json"),
        ],
    }

    rollouter_inventory = {
        "class_present": _contains(texts, "fully_async_rollouter", "class FullyAsyncRollouter"),
        "asserts_hybrid_engine_false": _contains(texts, "fully_async_rollouter", "assert not self.hybrid_engine"),
        "requires_train_batch_size_zero": _contains(
            texts,
            "fully_async_rollouter",
            "train_batch_size must be zero",
        ),
        "requires_gen_batch_size_one": _contains(texts, "fully_async_rollouter", "gen_batch_size must be one"),
        "has_pending_queue": _contains(texts, "fully_async_rollouter", "self.pending_queue"),
        "has_active_tasks": _contains(texts, "fully_async_rollouter", "self.active_tasks"),
        "has_resume_event": _contains(texts, "fully_async_rollouter", "self._resume_event"),
        "has_reset_staleness": _contains(texts, "fully_async_rollouter", "reset_staleness"),
        "computes_required_samples": _contains(texts, "fully_async_rollouter", "self.required_samples"),
        "computes_max_required_samples": _contains(texts, "fully_async_rollouter", "self.max_required_samples"),
        "message_queue_put_sample_present": _contains(texts, "fully_async_rollouter", "put_sample"),
        "evidence": [
            evidence("fully_async_rollouter", "self.pending_queue").model_dump(mode="json"),
            evidence("fully_async_rollouter", "self.active_tasks").model_dump(mode="json"),
            evidence("fully_async_rollouter", "self._resume_event").model_dump(mode="json"),
            evidence("fully_async_rollouter", "self.required_samples").model_dump(mode="json"),
        ],
    }

    message_queue_inventory = {
        "message_queue_put_sample_async": _contains(texts, "message_queue", "async def put_sample"),
        "message_queue_client_put_sample_async": _contains(texts, "message_queue", "async def put_sample"),
        "message_queue_client_get_sample_async": _contains(texts, "message_queue", "async def get_sample"),
        "trainer_collects_raw_required_samples": _contains(
            texts,
            "fully_async_trainer",
            "while len(queue_samples) < self.required_samples",
        ),
        "trainer_cloudpickle_loads_queue_entries": _contains(
            texts,
            "fully_async_trainer",
            "ray.cloudpickle.loads",
        ),
        "trainer_side_repo_harness_filter_present": False,
        "recommended_source_gate": "policy_loss_message_queue_only_accepts_valid_completed_sample",
        "diagnostic_samples_require_side_channel": True,
        "evidence": [
            evidence("message_queue", "async def put_sample").model_dump(mode="json"),
            evidence("message_queue", "async def get_sample").model_dump(mode="json"),
            evidence("fully_async_trainer", "while len(queue_samples) < self.required_samples").model_dump(mode="json"),
            evidence("fully_async_trainer", "ray.cloudpickle.loads").model_dump(mode="json"),
        ],
    }

    lifecycle_inventory = {
        "repo_harness_verl_agent_loop_source": "src/repo_harness_verl/agent_loop.py",
        "async_episode_handle_source": "src/repo_harness/rl/async_runtime.py",
        "resume_state_store_source": "src/repo_harness/rl/pause_resume.py",
        "same_runtime_ownership_scope_required": True,
        "same_agent_loop_worker_ray_actor_required": True,
        "cross_process_resume_supported": False,
        "checkpoint_without_live_handle_goes_to_diagnostic_side_channel": True,
        "run_method_terminal_output_only_until_stage15_patch": True,
    }

    return Stage15PartialRolloutInterfaceInventory(
        reference_verl_root="reference/verl",
        reference_verl_commit=_git_output(reference_root, "rev-parse", "HEAD"),
        reference_verl_dirty_status=_git_output(reference_root, "status", "--short") or "",
        heavy_import_required=False,
        static_scan_only=True,
        config_inventory=config_inventory,
        native_partial_rollout_trigger_chain=trigger_chain,
        llm_server_stop_reason_inventory=llm_stop_inventory,
        fully_async_rollouter_inventory=rollouter_inventory,
        message_queue_trainer_inventory=message_queue_inventory,
        repo_harness_agent_loop_lifecycle_inventory=lifecycle_inventory,
        backend_abort_resume_inventory=_build_backend_abort_resume_inventory(files, texts, root),
        source_evidence=source_evidence,
        diagnostics=diagnostics,
    )


def build_stage15_partial_rollout_patch_plan(
    inventory: Stage15PartialRolloutInterfaceInventory,
) -> Stage15PartialRolloutPatchPlan:
    abort_invisible = not bool(
        inventory.native_partial_rollout_trigger_chain.get("abort_stop_reason_visible_to_agent_loop")
    )
    trainer_filter_missing = not bool(
        inventory.message_queue_trainer_inventory.get("trainer_side_repo_harness_filter_present")
    )
    patch_required = abort_invisible or trainer_filter_missing
    rejection_reasons: list[str] = []
    if abort_invisible:
        rejection_reasons.append("abort_aborted_not_visible_to_repo_harness_agent_loop")
    if trainer_filter_missing:
        rejection_reasons.append("fully_async_trainer_does_not_filter_repo_harness_diagnostic_samples")

    candidates = [
        Stage15PatchCandidate(
            patch_id="stage15_no_checkpoint_engine_abort_boundary_wrapper",
            target="reference/verl/verl/checkpoint_engine/base.py + reference/verl/verl/workers/rollout/replica.py",
            kind="no_patch_required",
            purpose="明确不把 checkpoint engine / rollout server abort-resume 链路当作 RepoHarness checkpoint boundary。",
            why_needed="参数同步中断发生在推理服务层，不能证明工具回合、recorder cursor、workspace writer lease 已处于安全状态。",
            enables=[
                "checkpoint_engine_abort_rationale",
                "backend_specific_partial_rollout_risk_documentation",
            ],
            risks=[
                "future_engine_patch_may_need_revisit",
                "server_level_abort_not_a_safe_repo_harness_turn_boundary",
            ],
            compatibility_tests=[
                "stage15_checkpoint_engine_abort_inventory_test",
                "stage15_abort_not_repo_harness_turn_boundary_test",
            ],
            rollback_plan="如果后续决定支持 server-level abort checkpoint，必须新写 Stage 15.x 设计并扩展 PartialEpisodeCheckpoint contract。",
            patch_manifest_required=False,
        ),
        Stage15PatchCandidate(
            patch_id="stage15_agent_loop_owned_partial_side_channel",
            target="src/repo_harness_verl/agent_loop.py + src/repo_harness/rl/async_runtime.py",
            kind="adapter_only",
            purpose="在同一 AgentLoopWorker / runtime ownership scope 内触发 turn-boundary pause，并把 PartialEpisodeCheckpoint 放入 resume side channel。",
            why_needed="RepoHarness checkpoint 必须绑定 live AsyncEpisodeHandle 和 ResumeStateStore，不能在 run(...) 返回后跨 actor 接管。",
            enables=[
                "partial_checkpoint_side_channel",
                "same_runtime_resume_scheduler",
                "completed_sample_after_resume",
            ],
            risks=[
                "run_returns_before_resume_handle_lost",
                "partial_checkpoint_disguised_as_terminal_output",
            ],
            compatibility_tests=[
                "stage15_same_agent_loop_worker_handle_registry_test",
                "stage15_partial_checkpoint_not_in_policy_loss_queue_test",
            ],
            rollback_plan="禁用 Stage 15 partial trigger，退回 Stage 14.3 同进程 pause/resume facade。",
            patch_manifest_required=False,
        ),
        Stage15PatchCandidate(
            patch_id="stage15_fully_async_rollouter_source_gate_wrapper",
            target="reference/verl/verl/experimental/fully_async_policy/fully_async_rollouter.py",
            kind="wrapper",
            purpose="在 RolloutSample 进入真实 MessageQueue 前，只允许 valid completed sample 进入 policy-loss queue，其余样本进入 diagnostic side channel。",
            why_needed="FullyAsyncTrainer._get_samples_from_queue(...) 会按 required_samples 读取 raw queue entry，不能让 partial / diagnostic 样本污染 required_samples。",
            enables=[
                "valid_completed_sample_queue",
                "diagnostic_side_channel",
                "policy_loss_required_samples_not_polluted",
            ],
            risks=[
                "reference_verl_patch_drift",
                "message_queue_backpressure_when_many_diagnostic_samples",
            ],
            compatibility_tests=[
                "stage15_rollouter_message_queue_shape_test",
                "stage15_required_samples_skip_diagnostic_test",
            ],
            rollback_plan="移除 wrapper 后，Stage 15 remote smoke 只能作为 debug run，不能作为 acceptance。",
            patch_manifest_required=True,
        ),
        Stage15PatchCandidate(
            patch_id="stage15_fully_llm_client_stop_reason_probe",
            target="reference/verl/verl/workers/rollout/llm_server.py",
            kind="wrapper",
            purpose="如果 Stage 15.1 需要直接观察 abort / aborted，则在 FullyLLMServerClient 自动续生成前写入 runtime-private probe 或 side-channel 事件。",
            why_needed="当前 FullyLLMServerClient 会在 partial_rollout=True 时消费 abort / aborted，并继续生成，AgentLoop 默认不可见。",
            enables=[
                "abort_visibility_probe",
                "backend_specific_partial_rollout_diagnostics",
            ],
            risks=[
                "server_level_abort_not_a_safe_repo_harness_turn_boundary",
                "backend_specific_stop_reason_drift",
            ],
            compatibility_tests=[
                "stage15_fully_llm_client_abort_probe_test",
                "stage15_completed_stop_reason_mapping_test",
            ],
            rollback_plan="不启用 stop reason probe；只支持受控 turn-boundary pause trigger。",
            patch_manifest_required=True,
        ),
    ]

    return Stage15PartialRolloutPatchPlan(
        reference_verl_patch_or_wrapper_required=patch_required,
        recommended_patch_id="stage15_agent_loop_owned_partial_side_channel",
        recommended_patch_ids=[
            "stage15_no_checkpoint_engine_abort_boundary_wrapper",
            "stage15_agent_loop_owned_partial_side_channel",
            "stage15_fully_async_rollouter_source_gate_wrapper",
        ],
        no_patch_required_claim_allowed=not patch_required,
        no_patch_rejection_reasons=rejection_reasons,
        candidates=candidates,
    )


def build_stage15_partial_rollout_risk_matrix() -> Stage15PartialRolloutRiskMatrix:
    risks = [
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_invisible_abort",
            severity="P1",
            failure_mode="abort / aborted 被 FullyLLMServerClient 内部续生成消费，RepoHarness 看不到安全 checkpoint boundary。",
            detection="inventory 检查 FullyLLMServerClient.generate(...) 的 stop reason 循环。",
            mitigation="Stage 15.1 使用受控 turn-boundary pause trigger，或登记 stop reason probe wrapper。",
            owner_stage="15.0",
            acceptance_gate="llm_server_stop_reason_inventory.abort_visible_to_repo_harness_agent_loop=false 时必须有 patch plan。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_checkpoint_engine_abort_not_repo_boundary",
            severity="P1",
            failure_mode="CheckpointEngineManager.update_weights(...) 中断推理服务请求，但不是 RepoHarness 安全 turn boundary。",
            detection="inventory 检查 update_weights -> abort_all_requests -> resume_generation 链路。",
            mitigation="Stage 15.1 不把 server abort 直接当作 PartialEpisodeCheckpoint；只在 RepoHarness turn boundary 保存 checkpoint。",
            owner_stage="15.0",
            acceptance_gate="native_partial_rollout_trigger_chain 必须存在并解释 repo_harness_checkpoint_implication。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_trainer_required_samples_polluted",
            severity="P1",
            failure_mode="partial / diagnostic / stale 样本被 FullyAsyncTrainer 计入 required_samples。",
            detection="inventory 检查 _get_samples_from_queue(...) 是否存在 RepoHarness-aware filter。",
            mitigation="policy-loss MessageQueue 源头只放 valid completed sample，或增加 trainer-side wrapper。",
            owner_stage="15.1",
            acceptance_gate="patch plan 必须指定 source gate 或 trainer wrapper。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_cross_actor_resume",
            severity="P1",
            failure_mode="合法 checkpoint 被另一个进程或 Ray actor 接管，丢失 live handle / writer lease。",
            detection="resume scheduler ownership inventory 和 ResumeStateStore 绑定测试。",
            mitigation="第一版只允许同一 AgentLoopWorker / runtime active handle registry 内 resume。",
            owner_stage="15.1",
            acceptance_gate="checkpoint_without_live_handle_goes_to_diagnostic_side_channel=true。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_duplicate_resume_consumption",
            severity="P1",
            failure_mode="同一个 checkpoint 被重复 resume，多个 policy-loss sample 重复计数。",
            detection="检查 source_partial_checkpoint_id、resume_attempt_id、policy_loss_consumed_sample_id 唯一性。",
            mitigation="Stage 15.2 inspector 要求 consumed sample id、source checkpoint id 和 resume attempt id 绑定唯一。",
            owner_stage="15.2",
            acceptance_gate="inspect-stage15-partial-rollout-acceptance unique id checks。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_stale_resumed_sample",
            severity="P1",
            failure_mode="resume 后参数版本过旧的样本进入 policy loss。",
            detection="检查 trajectory_param_versions、min_global_steps、max_global_steps 和 current_param_version。",
            mitigation="resume 后重新计算 staleness，超过阈值时进入 diagnostic side channel。",
            owner_stage="15.1",
            acceptance_gate="post_sync_resumed_valid_sample_count 与 stale rejection report 同时存在。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_visibility_or_path_leak",
            severity="P1",
            failure_mode="partial checkpoint、side channel 或 patch evidence 泄漏路径、hidden verifier 或 reward metadata。",
            detection="公开 evidence path leak scan 和 visibility gate。",
            mitigation="公开 evidence 只保留 opaque ref、digest 和 batch-safe scalar；runtime-private raw evidence 单独登记。",
            owner_stage="15.2",
            acceptance_gate="public_path_leak_scan_passed=true。",
        ),
        Stage15RiskMatrixEntry(
            risk_id="stage15_risk_reference_verl_patch_drift",
            severity="P2",
            failure_mode="reference/verl 源码漂移导致 wrapper hook 失效。",
            detection="记录 reference_verl_commit、dirty status 和 patch manifest sha256。",
            mitigation="Stage 15.0 inventory 和 Stage 15.2 acceptance 都绑定 reference/verl commit。",
            owner_stage="15.0",
            acceptance_gate="reference_verl_commit and patch manifest required for remote acceptance。",
        ),
    ]
    return Stage15PartialRolloutRiskMatrix(risks=risks)


def build_stage15_static_scan_report(
    inventory: Stage15PartialRolloutInterfaceInventory,
) -> Stage15StaticScanReport:
    scanned = sorted({evidence.source_path for evidence in inventory.source_evidence})
    return Stage15StaticScanReport(
        scanned_files=scanned,
        heavy_import_modules_forbidden=list(_HEAVY_MODULES),
        static_scan_only=True,
        diagnostics=list(inventory.diagnostics),
    )


def write_stage15_0_artifacts(
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
    reference_verl_root: str | Path | None = None,
) -> Stage15AcceptanceSummary:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    inventory = build_stage15_partial_rollout_interface_inventory(
        repo_root=root,
        reference_verl_root=reference_verl_root,
    )
    patch_plan = build_stage15_partial_rollout_patch_plan(inventory)
    risk_matrix = build_stage15_partial_rollout_risk_matrix()
    static_scan = build_stage15_static_scan_report(inventory)

    _write_json(out / "fully_async_partial_rollout_interface_inventory.json", inventory.model_dump(mode="json"))
    _write_json(out / "stage15_partial_rollout_patch_plan.json", patch_plan.model_dump(mode="json"))
    _write_json(out / "stage15_partial_rollout_risk_matrix.json", risk_matrix.model_dump(mode="json"))
    _write_json(out / "stage15_0_static_scan_report.json", static_scan.model_dump(mode="json"))
    _write_command_log(out / "stage15_0_command_log.jsonl")

    summary = inspect_stage15_0_artifacts(out, repo_root=root, reference_verl_root=reference_verl_root)
    _write_json(out / "stage15_0_acceptance_summary.json", summary.model_dump(mode="json"))
    return summary


def inspect_stage15_0_artifacts(
    output_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
    reference_verl_root: str | Path | None = None,
) -> Stage15AcceptanceSummary:
    root = _repo_root(repo_root)
    reference_root = _reference_verl_root(root, reference_verl_root)
    out = Path(output_dir)
    failures: list[str] = []
    artifact_paths = {name: name for name in STAGE15_0_ARTIFACTS}

    for name in STAGE15_0_ARTIFACTS:
        if name == "stage15_0_acceptance_summary.json":
            continue
        if not (out / name).is_file():
            failures.append(f"missing_artifact:{name}")

    inventory = _load_model_if_exists(
        out / "fully_async_partial_rollout_interface_inventory.json",
        Stage15PartialRolloutInterfaceInventory,
        failures,
        "inventory",
    )
    patch_plan = _load_model_if_exists(
        out / "stage15_partial_rollout_patch_plan.json",
        Stage15PartialRolloutPatchPlan,
        failures,
        "patch_plan",
    )
    risk_matrix = _load_model_if_exists(
        out / "stage15_partial_rollout_risk_matrix.json",
        Stage15PartialRolloutRiskMatrix,
        failures,
        "risk_matrix",
    )

    if inventory is not None:
        failures.extend(_validate_inventory_for_acceptance(inventory, repo_root=root))
    if patch_plan is not None:
        failures.extend(_validate_patch_plan_for_acceptance(patch_plan))
    if risk_matrix is not None:
        failures.extend(_validate_risk_matrix_for_acceptance(risk_matrix))
    if inventory is not None and patch_plan is not None:
        failures.extend(_validate_patch_plan_against_inventory(patch_plan, inventory))

    failures.extend(_scan_stage15_public_json_for_leaks(out))
    summary = Stage15AcceptanceSummary(
        passed=False,
        code_commit=_git_output(root, "rev-parse", "HEAD"),
        git_status_short=_git_output(root, "status", "--short") or "",
        reference_verl_commit=_git_output(reference_root, "rev-parse", "HEAD"),
        reference_verl_dirty_status=_git_output(reference_root, "status", "--short") or "",
        inventory_sha256=_sha256_file(out / "fully_async_partial_rollout_interface_inventory.json"),
        patch_plan_sha256=_sha256_file(out / "stage15_partial_rollout_patch_plan.json"),
        risk_matrix_sha256=_sha256_file(out / "stage15_partial_rollout_risk_matrix.json"),
        static_scan_report_sha256=_sha256_file(out / "stage15_0_static_scan_report.json"),
        failures=[],
        artifact_paths=artifact_paths,
    )
    failures.extend(_validate_summary_for_acceptance(summary))
    summary.failures = failures
    summary.passed = not failures
    return summary



def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root is not None:
        return Path(repo_root).resolve()
    return Path(__file__).resolve().parents[2]


def _reference_verl_root(repo_root: Path, reference_verl_root: str | Path | None = None) -> Path:
    if reference_verl_root is not None:
        return Path(reference_verl_root).resolve()
    return repo_root / "reference" / "verl"


def _reference_files(reference_root: Path) -> dict[str, Path]:
    return {
        "fully_async_config": reference_root
        / "verl"
        / "experimental"
        / "fully_async_policy"
        / "config"
        / "fully_async_ppo_trainer.yaml",
        "fully_async_trainer": reference_root
        / "verl"
        / "experimental"
        / "fully_async_policy"
        / "fully_async_trainer.py",
        "fully_async_rollouter": reference_root
        / "verl"
        / "experimental"
        / "fully_async_policy"
        / "fully_async_rollouter.py",
        "message_queue": reference_root / "verl" / "experimental" / "fully_async_policy" / "message_queue.py",
        "detach_utils": reference_root / "verl" / "experimental" / "fully_async_policy" / "detach_utils.py",
        "checkpoint_engine_base": reference_root / "verl" / "checkpoint_engine" / "base.py",
        "rollout_replica": reference_root / "verl" / "workers" / "rollout" / "replica.py",
        "llm_server": reference_root / "verl" / "workers" / "rollout" / "llm_server.py",
        "vllm_async_server": reference_root
        / "verl"
        / "workers"
        / "rollout"
        / "vllm_rollout"
        / "vllm_async_server.py",
        "sglang_async_server": reference_root
        / "verl"
        / "workers"
        / "rollout"
        / "sglang_rollout"
        / "async_sglang_server.py",
        "trtllm_async_server": reference_root
        / "verl"
        / "workers"
        / "rollout"
        / "trtllm_rollout"
        / "trtllm_async_server.py",
    }


def _missing_file_diagnostics(files: Mapping[str, Path]) -> list[str]:
    diagnostics: list[str] = []
    for key, path in files.items():
        if not path.exists():
            diagnostics.append(f"missing_reference_file:{key}:{path.name}")
    return diagnostics


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _contains(texts: Mapping[str, str], key: str, needle: str) -> bool:
    return needle in texts.get(key, "")


def _line_number(text: str, needle: str) -> int | None:
    if not needle:
        return None
    for idx, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return idx
    return None


def _method_body_contains(text: str, method_name: str, needle: str) -> bool:
    pattern = re.compile(
        rf"^\s*async\s+def\s+{re.escape(method_name)}\s*\([^)]*\):(?P<body>.*?)(?=^\s*async\s+def\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        return False
    return needle in match.group("body")


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _build_config_inventory(texts: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    config_text = texts.get("fully_async_config", "")

    def value_for(key: str) -> Any:
        match = re.search(rf"^\s*{re.escape(key)}:\s*(.+?)\s*$", config_text, re.MULTILINE)
        if match is None:
            return None
        raw = match.group(1).strip()
        if raw in {"True", "true"}:
            return True
        if raw in {"False", "false"}:
            return False
        try:
            if "." in raw:
                return float(raw)
            return int(raw)
        except ValueError:
            return raw.strip("\"'")

    def item(
        *,
        default_value: Any | None = None,
        current_stage14_override: Any | None = None,
        stage15_required_override: Any | None = None,
        source_path: str,
        source_evidence: str,
        notes: str,
    ) -> dict[str, Any]:
        return {
            "default_value": default_value,
            "current_stage14_override": current_stage14_override,
            "stage15_required_override": stage15_required_override,
            "source_path": source_path,
            "source_evidence": source_evidence,
            "notes": notes,
        }

    config_path = "reference/verl/verl/experimental/fully_async_policy/config/fully_async_ppo_trainer.yaml"
    rollouter_path = "reference/verl/verl/experimental/fully_async_policy/fully_async_rollouter.py"
    stage14_remote_smoke_path = "src/repo_harness_verl/stage14_remote_smoke.py"
    return {
        "async_training.partial_rollout": item(
            default_value=value_for("partial_rollout"),
            current_stage14_override=False,
            stage15_required_override=True,
            source_path=config_path,
            source_evidence="partial_rollout: True",
            notes="Stage 15 需要开启真实 verl partial rollout，但不能把 server-level abort 直接当成 RepoHarness checkpoint。",
        ),
        "async_training.trigger_parameter_sync_step": item(
            default_value=value_for("trigger_parameter_sync_step"),
            current_stage14_override=2,
            stage15_required_override=2,
            source_path=config_path,
            source_evidence="trigger_parameter_sync_step:",
            notes="短 smoke 使用较小同步间隔，便于观察 post-sync resumed sample。",
        ),
        "async_training.require_batches": item(
            default_value=value_for("require_batches"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=config_path,
            source_evidence="require_batches:",
            notes="required_samples = ppo_mini_batch_size * require_batches。",
        ),
        "async_training.staleness_threshold": item(
            default_value=value_for("staleness_threshold"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=config_path,
            source_evidence="staleness_threshold:",
            notes="resume 后必须重新计算 staleness。",
        ),
        "rollout.total_rollout_steps": item(
            default_value=value_for("total_rollout_steps"),
            current_stage14_override=8,
            stage15_required_override=16,
            source_path=config_path,
            source_evidence="total_rollout_steps:",
            notes="远端短步数 smoke 的 rollout 样本总量入口。",
        ),
        "actor_rollout_ref.hybrid_engine": item(
            default_value=None,
            current_stage14_override=False,
            stage15_required_override=False,
            source_path=rollouter_path,
            source_evidence="assert not self.hybrid_engine",
            notes="FullyAsyncRollouter 要求 hybrid_engine=False。",
        ),
        "data.train_batch_size": item(
            default_value=None,
            current_stage14_override=0,
            stage15_required_override=0,
            source_path=rollouter_path,
            source_evidence="train_batch_size must be zero",
            notes="fully async rollouter 要求 train_batch_size=0。",
        ),
        "data.gen_batch_size": item(
            default_value=value_for("gen_batch_size"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=config_path,
            source_evidence="gen_batch_size: 1",
            notes="fully async streaming 生成路径当前只支持 1。",
        ),
        "actor_rollout_ref.rollout.calculate_log_probs": item(
            default_value=value_for("calculate_log_probs"),
            current_stage14_override=True,
            stage15_required_override=True,
            source_path=rollouter_path,
            source_evidence="must rollout calculate log_probs",
            notes="policy loss 必须绑定 rollout log probability。",
        ),
        "actor_rollout_ref.actor.use_rollout_log_probs": item(
            default_value=value_for("use_rollout_log_probs"),
            current_stage14_override=True,
            stage15_required_override=True,
            source_path=config_path,
            source_evidence="use_rollout_log_probs: True",
            notes="trainer 侧使用 rollout logprobs。",
        ),
        "actor_rollout_ref.rollout.agent.agent_loop_config_path": item(
            default_value=None,
            current_stage14_override="repo_harness_agent_loop_config.yaml",
            stage15_required_override="repo_harness_agent_loop_config.yaml",
            source_path=stage14_remote_smoke_path,
            source_evidence="actor_rollout_ref.rollout.agent.agent_loop_config_path=",
            notes="RepoHarnessVerlAgentLoop 需要 agent loop config path 指向 repo_harness entry。",
        ),
        "actor_rollout_ref.rollout.multi_turn.enable": item(
            default_value=None,
            current_stage14_override=True,
            stage15_required_override=True,
            source_path=stage14_remote_smoke_path,
            source_evidence="actor_rollout_ref.rollout.multi_turn.enable=",
            notes="必须开启 multi-turn，避免被 single_turn_agent 覆盖。",
        ),
        "actor_rollout_ref.rollout.name": item(
            default_value=None,
            current_stage14_override="sglang",
            stage15_required_override="sglang",
            source_path=stage14_remote_smoke_path,
            source_evidence="actor_rollout_ref.rollout.name=",
            notes="Stage 14/15 开发 smoke 默认沿用 SGLang。",
        ),
        "trainer.nnodes": item(
            default_value=value_for("nnodes"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=stage14_remote_smoke_path,
            source_evidence="trainer.nnodes=",
            notes="双卡 smoke 中 trainer 与 rollout 资源池拆分时需要显式配置。",
        ),
        "trainer.n_gpus_per_node": item(
            default_value=value_for("n_gpus_per_node"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=stage14_remote_smoke_path,
            source_evidence="trainer.n_gpus_per_node=",
            notes="双卡 smoke 中 trainer 侧 GPU 数。",
        ),
        "rollout.nnodes": item(
            default_value=value_for("nnodes"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=stage14_remote_smoke_path,
            source_evidence="rollout.nnodes=",
            notes="双卡 smoke 中 rollout 侧节点数。",
        ),
        "rollout.n_gpus_per_node": item(
            default_value=value_for("n_gpus_per_node"),
            current_stage14_override=1,
            stage15_required_override=1,
            source_path=stage14_remote_smoke_path,
            source_evidence="rollout.n_gpus_per_node=",
            notes="双卡 smoke 中 rollout 侧 GPU 数。",
        ),
        "checkpoint_engine.backend": item(
            default_value="nccl",
            current_stage14_override="nixl",
            stage15_required_override="nixl",
            source_path=stage14_remote_smoke_path,
            source_evidence="actor_rollout_ref.rollout.checkpoint_engine.backend=",
            notes="Stage 14 已验证 NIXL CUDA 小模型全量训练基线。",
        ),
    }


def _build_backend_abort_resume_inventory(
    files: Mapping[str, Path],
    texts: Mapping[str, str],
    repo_root: Path,
) -> list[Stage15BackendAbortResumeFacts]:
    backend_keys = {
        "vllm": "vllm_async_server",
        "sglang": "sglang_async_server",
        "trtllm": "trtllm_async_server",
    }
    facts: list[Stage15BackendAbortResumeFacts] = []
    for backend, key in backend_keys.items():
        text = texts.get(key, "")
        not_implemented = _method_body_contains(
            text,
            "abort_all_requests",
            "raise NotImplementedError",
        ) or _method_body_contains(
            text,
            "resume_generation",
            "raise NotImplementedError",
        )
        risk = None
        if not_implemented:
            risk = f"{backend}_abort_resume_not_implemented"
        elif not ("abort_all_requests" in text and "resume_generation" in text):
            risk = f"{backend}_abort_resume_missing"
        facts.append(
            Stage15BackendAbortResumeFacts(
                backend=backend,
                source_path=_relative_to_repo(files[key], repo_root),
                abort_all_requests_present="abort_all_requests" in text,
                resume_generation_present="resume_generation" in text,
                not_implemented=not_implemented,
                risk=risk,
            )
        )
    return facts


def _validate_inventory_for_acceptance(
    inventory: Stage15PartialRolloutInterfaceInventory,
    *,
    repo_root: Path,
) -> list[str]:
    failures: list[str] = []
    required_config_keys = {
        "async_training.partial_rollout",
        "async_training.trigger_parameter_sync_step",
        "async_training.require_batches",
        "async_training.staleness_threshold",
        "rollout.total_rollout_steps",
        "actor_rollout_ref.hybrid_engine",
        "data.train_batch_size",
        "data.gen_batch_size",
        "actor_rollout_ref.rollout.calculate_log_probs",
        "actor_rollout_ref.actor.use_rollout_log_probs",
        "actor_rollout_ref.rollout.agent.agent_loop_config_path",
        "actor_rollout_ref.rollout.multi_turn.enable",
        "actor_rollout_ref.rollout.name",
        "trainer.nnodes",
        "trainer.n_gpus_per_node",
        "rollout.nnodes",
        "rollout.n_gpus_per_node",
        "checkpoint_engine.backend",
    }
    missing_config_keys = sorted(required_config_keys - set(inventory.config_inventory))
    for key in missing_config_keys:
        failures.append(f"inventory_missing_config_key:{key}")
    for key, payload in inventory.config_inventory.items():
        for field in ("source_path", "source_evidence", "current_stage14_override", "stage15_required_override"):
            if field not in payload:
                failures.append(f"inventory_config_key_missing_field:{key}:{field}")
        if "source_path" in payload and "source_evidence" in payload:
            failures.extend(
                _validate_literal_source_evidence(
                    repo_root=repo_root,
                    label=f"inventory_config_key_source_evidence:{key}",
                    source_path=str(payload["source_path"]),
                    source_evidence=str(payload["source_evidence"]),
                )
            )

    chain = inventory.native_partial_rollout_trigger_chain
    if not chain.get("weight_sync_calls_checkpoint_manager_update_weights"):
        failures.append("inventory_missing_weight_sync_update_weights_chain")
    if not chain.get("checkpoint_manager_aborts_inflight_requests"):
        failures.append("inventory_missing_checkpoint_manager_abort")
    if not chain.get("server_resume_generation_after_weight_sync"):
        failures.append("inventory_missing_resume_generation_after_weight_sync")
    if "repo_harness_checkpoint_implication" not in chain:
        failures.append("inventory_missing_repo_harness_checkpoint_implication")
    if not chain.get("evidence"):
        failures.append("inventory_missing_trigger_chain_evidence")

    llm = inventory.llm_server_stop_reason_inventory
    if llm.get("fully_async_client_class") != "FullyLLMServerClient":
        failures.append("inventory_missing_fully_llm_server_client")
    if not llm.get("abort_auto_continues_inside_fully_llm_server_client"):
        failures.append("inventory_missing_abort_auto_continue")
    if not llm.get("completed_stop_reason_mapping_checked"):
        failures.append("inventory_missing_completed_stop_reason_mapping")
    if not llm.get("backend_specific_stop_reason_mapping_checked"):
        failures.append("inventory_missing_backend_specific_stop_reason_mapping")
    backend_stop_reasons = llm.get("normal_completion_stop_reason_by_backend")
    if not isinstance(backend_stop_reasons, Mapping):
        failures.append("inventory_missing_backend_normal_completion_stop_reason_inventory")
    else:
        vllm_stop = backend_stop_reasons.get("vllm")
        sglang_stop = backend_stop_reasons.get("sglang")
        if not isinstance(vllm_stop, Mapping):
            failures.append("inventory_missing_vllm_normal_completion_stop_reason_inventory")
        elif not vllm_stop.get("normalizes_stop_and_length_to_completed"):
            failures.append("inventory_missing_vllm_completed_stop_reason_mapping")
        if not isinstance(sglang_stop, Mapping):
            failures.append("inventory_missing_sglang_normal_completion_stop_reason_inventory")
        elif not sglang_stop.get("returns_raw_finish_reason"):
            failures.append("inventory_missing_sglang_raw_finish_reason_mapping")
        if llm.get("default_stage14_backend") == "sglang" and isinstance(sglang_stop, Mapping):
            values = sglang_stop.get("normal_completion_values_after_adapter")
            if values != ["stop", "length"]:
                failures.append("inventory_stage14_sglang_normal_completion_values_not_raw")
    if not llm.get("evidence"):
        failures.append("inventory_missing_llm_stop_reason_evidence")

    rollouter_required = {
        "class_present",
        "asserts_hybrid_engine_false",
        "requires_train_batch_size_zero",
        "requires_gen_batch_size_one",
        "has_pending_queue",
        "has_active_tasks",
        "has_resume_event",
        "has_reset_staleness",
        "computes_required_samples",
        "computes_max_required_samples",
        "message_queue_put_sample_present",
    }
    for field in sorted(rollouter_required):
        if not inventory.fully_async_rollouter_inventory.get(field):
            failures.append(f"inventory_missing_rollouter_field:{field}")

    message_queue_required = {
        "message_queue_put_sample_async",
        "message_queue_client_put_sample_async",
        "message_queue_client_get_sample_async",
        "trainer_collects_raw_required_samples",
        "trainer_cloudpickle_loads_queue_entries",
        "diagnostic_samples_require_side_channel",
    }
    for field in sorted(message_queue_required):
        if not inventory.message_queue_trainer_inventory.get(field):
            failures.append(f"inventory_missing_message_queue_field:{field}")
    if not inventory.message_queue_trainer_inventory.get("trainer_collects_raw_required_samples"):
        failures.append("inventory_missing_trainer_required_samples_semantics")
    if inventory.message_queue_trainer_inventory.get("recommended_source_gate") != (
        "policy_loss_message_queue_only_accepts_valid_completed_sample"
    ):
        failures.append("inventory_missing_policy_loss_source_gate_recommendation")

    lifecycle_required_true = {
        "same_runtime_ownership_scope_required",
        "same_agent_loop_worker_ray_actor_required",
        "checkpoint_without_live_handle_goes_to_diagnostic_side_channel",
        "run_method_terminal_output_only_until_stage15_patch",
    }
    for field in sorted(lifecycle_required_true):
        if not inventory.repo_harness_agent_loop_lifecycle_inventory.get(field):
            failures.append(f"inventory_missing_lifecycle_field:{field}")
    if inventory.repo_harness_agent_loop_lifecycle_inventory.get("cross_process_resume_supported") is not False:
        failures.append("inventory_cross_process_resume_not_explicitly_false")

    backends = {item.backend: item for item in inventory.backend_abort_resume_inventory}
    for backend in ("vllm", "sglang", "trtllm"):
        item = backends.get(backend)
        if item is None:
            failures.append(f"inventory_missing_backend_abort_resume:{backend}")
            continue
        if not item.abort_all_requests_present:
            failures.append(f"inventory_backend_missing_abort_all_requests:{backend}")
        if not item.resume_generation_present:
            failures.append(f"inventory_backend_missing_resume_generation:{backend}")
    if not backends.get("trtllm") or backends["trtllm"].not_implemented is not True:
        failures.append("inventory_missing_trtllm_not_implemented_risk")

    if not inventory.source_evidence:
        failures.append("inventory_missing_source_evidence")
    for evidence in inventory.source_evidence:
        if evidence.line is None:
            failures.append(f"inventory_source_evidence_missing_line:{evidence.source_path}:{evidence.line_hint}")
        failures.extend(
            _validate_literal_source_evidence(
                repo_root=repo_root,
                label=f"inventory_source_evidence:{evidence.source_path}:{evidence.line_hint}",
                source_path=evidence.source_path,
                source_evidence=evidence.line_hint,
            )
        )

    if inventory.heavy_import_required:
        failures.append("inventory_declares_heavy_import_required")
    if not inventory.static_scan_only:
        failures.append("inventory_not_static_scan_only")
    return failures


def _validate_literal_source_evidence(
    *,
    repo_root: Path,
    label: str,
    source_path: str,
    source_evidence: str,
) -> list[str]:
    failures: list[str] = []
    if not source_path:
        return [f"{label}:missing_source_path"]
    if not source_evidence:
        return [f"{label}:missing_source_evidence"]
    path = Path(source_path)
    if path.is_absolute():
        return [f"{label}:absolute_source_path"]
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return [f"{label}:source_path_outside_repo"]
    if not resolved.is_file():
        return [f"{label}:source_path_not_found"]
    text = resolved.read_text(encoding="utf-8")
    if source_evidence not in text:
        return [f"{label}:source_evidence_not_found"]
    return failures


def _validate_patch_plan_for_acceptance(plan: Stage15PartialRolloutPatchPlan) -> list[str]:
    failures: list[str] = []
    if plan.reference_verl_patch_or_wrapper_required and plan.no_patch_required_claim_allowed:
        failures.append("patch_plan_allows_no_patch_despite_required_patch")
    if plan.reference_verl_patch_or_wrapper_required and not plan.no_patch_rejection_reasons:
        failures.append("patch_plan_missing_no_patch_rejection_reasons")
    candidate_ids = {candidate.patch_id for candidate in plan.candidates}
    required = {
        "stage15_no_checkpoint_engine_abort_boundary_wrapper",
        "stage15_agent_loop_owned_partial_side_channel",
        "stage15_fully_async_rollouter_source_gate_wrapper",
        "stage15_fully_llm_client_stop_reason_probe",
    }
    missing = sorted(required - candidate_ids)
    for patch_id in missing:
        failures.append(f"patch_plan_missing_candidate:{patch_id}")
    return failures


def _validate_patch_plan_against_inventory(
    plan: Stage15PartialRolloutPatchPlan,
    inventory: Stage15PartialRolloutInterfaceInventory,
) -> list[str]:
    failures: list[str] = []
    abort_invisible = not bool(
        inventory.native_partial_rollout_trigger_chain.get("abort_stop_reason_visible_to_agent_loop")
    )
    trainer_filter_missing = not bool(
        inventory.message_queue_trainer_inventory.get("trainer_side_repo_harness_filter_present")
    )
    patch_required_by_inventory = abort_invisible or trainer_filter_missing
    if patch_required_by_inventory and plan.no_patch_required_claim_allowed:
        failures.append("patch_plan_no_patch_claim_conflicts_with_inventory")
    if patch_required_by_inventory and not plan.reference_verl_patch_or_wrapper_required:
        failures.append("patch_plan_missing_required_patch_or_wrapper_flag")
    required_combo = {
        "stage15_agent_loop_owned_partial_side_channel",
        "stage15_fully_async_rollouter_source_gate_wrapper",
    }
    missing_combo = sorted(required_combo - set(plan.recommended_patch_ids))
    for patch_id in missing_combo:
        failures.append(f"patch_plan_recommended_combo_missing:{patch_id}")
    return failures


def _validate_risk_matrix_for_acceptance(matrix: Stage15PartialRolloutRiskMatrix) -> list[str]:
    required = {
        "stage15_risk_invisible_abort",
        "stage15_risk_checkpoint_engine_abort_not_repo_boundary",
        "stage15_risk_trainer_required_samples_polluted",
        "stage15_risk_cross_actor_resume",
        "stage15_risk_duplicate_resume_consumption",
        "stage15_risk_stale_resumed_sample",
        "stage15_risk_visibility_or_path_leak",
        "stage15_risk_reference_verl_patch_drift",
    }
    present = {risk.risk_id for risk in matrix.risks}
    return [f"risk_matrix_missing:{risk_id}" for risk_id in sorted(required - present)]


def _validate_summary_for_acceptance(summary: Stage15AcceptanceSummary) -> list[str]:
    failures: list[str] = []
    required_sha_fields = {
        "inventory_sha256": summary.inventory_sha256,
        "patch_plan_sha256": summary.patch_plan_sha256,
        "risk_matrix_sha256": summary.risk_matrix_sha256,
        "static_scan_report_sha256": summary.static_scan_report_sha256,
    }
    if not summary.code_commit:
        failures.append("acceptance_summary_missing_code_commit")
    if not summary.reference_verl_commit:
        failures.append("acceptance_summary_missing_reference_verl_commit")
    for field, value in required_sha_fields.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            failures.append(f"acceptance_summary_missing_{field}")
    for artifact in STAGE15_0_ARTIFACTS:
        if artifact not in summary.artifact_paths:
            failures.append(f"acceptance_summary_missing_artifact_path:{artifact}")
    return failures


def _scan_stage15_public_json_for_leaks(output_dir: Path) -> list[str]:
    failures: list[str] = []
    for path in list(output_dir.glob("*.json")) + list(output_dir.glob("*.jsonl")):
        text = path.read_text(encoding="utf-8")
        for pattern in _PATH_LEAK_PATTERNS:
            if pattern.search(text):
                failures.append(f"public_evidence_path_or_secret_leak:{path.name}:{pattern.pattern}")
                break
    return failures


def _load_model_if_exists(
    path: Path,
    model_type: type[StrictBaseModel],
    failures: list[str],
    label: str,
) -> Any | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return model_type.model_validate(payload)
    except Exception as exc:
        failures.append(f"invalid_{label}:{exc}")
        return None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_command_log(path: Path) -> None:
    entry = {
        "schema_version": "repo_harness_verl_stage15_0_command_log_entry_v0",
        "command_name": "build_stage15_0_artifacts",
        "status": "passed",
        "notes": "static source inventory only; no verl, torch, ray, or tensordict import",
    }
    path.write_text(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _git_output(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return completed.stdout.strip()
