"""S1-1 契约单测的共享样例工厂（供 tests/contracts 各测试模块 import）。

原则：每个工厂返回一个**全新构造**的 JSON 形态 dict（合法样例），
单测在副本上做局部破坏来构造非法样例。数值刻意取自真实探针：
prompt 15 token、生成 16 token、top-p offsets 长 17、routing [30,48,8]
（uh_probe_result.json / S0-6 探针）、评分总时长 53.4s（S0-7 八题均值）。
"""

from __future__ import annotations

from typing import Any

from repoharness2.contracts import EligibilityFacts, compute_facts_digest

# 各类 digest / commit 占位值（格式合法，内容可辨识）。
SHA_TEMPLATE = "sha256:" + "a" * 64
SHA_PROMPT = "sha256:" + "b" * 64
SHA_META = "sha256:" + "c" * 64
SHA_PATCH = "sha256:" + "d" * 64
SHA_IMAGE = "sha256:" + "e" * 64
SHA_BUNDLE = "sha256:" + "f" * 64
BASE_COMMIT = "d26b2424" + "0" * 32  # django-11099 的 base（前 8 位真实）
HEAD_COMMIT = "2a2861e0" + "0" * 32  # 官方镜像叠加提交（前 8 位真实）
TS = "2026-07-07T09:30:25Z"


def valid_routing() -> dict[str, Any]:
    """SGLang 约定的 routing tape 引用：prompt 15 - 1 + 生成 16 = 30 行。"""

    return {
        "alignment": "sglang_prompt_minus1_plus_gen",
        "tensor_ref": {"ref_id": "routing_tape_0001"},
        "num_rows": 30,
        "num_layers": 48,
        "router_topk": 8,
        "dtype": "int32",
        "prompt_token_count": 15,
        "generated_token_count": 16,
    }


def valid_sampling_mask() -> dict[str, Any]:
    """top_p=0.95 的 tape 引用：生成 16 token -> offsets 长 17。"""

    return {
        "mask_kind": "top_p_kept_token_ids",
        "top_p": 0.95,
        "token_ids_ref": {"ref_id": "topp_ids_0001"},
        "offsets_ref": {"ref_id": "topp_offsets_0001"},
        "response_token_count": 16,
        "offsets_len": 17,
        "kept_token_count": 57,
    }


def valid_branch() -> dict[str, Any]:
    return {
        "branch_id": "b0",
        "prompt_token_count": 15,
        "response_token_count": 16,
        "token_spans": [
            {"start": 0, "end": 15, "source_type": "prompt_context"},
            {"start": 15, "end": 31, "source_type": "sampled_assistant"},
        ],
        "loss_mask_spans": [
            {"start": 15, "end": 31, "mask": 1, "reason": "sampled_assistant_trainable"},
        ],
        "logprob_alignment_status": "aligned_per_token",
        "logprob_provenance": {
            "engine_name": "sglang",
            "engine_version": "0.5.9",
            "precision": "bfloat16",
            "sampling_backend": "pytorch",
            "weight_version": "default",
        },
        "routing": valid_routing(),
        "sampling_mask": valid_sampling_mask(),
        "capture_record_refs": ["cap_0001"],
    }


def valid_reward_facts() -> dict[str, Any]:
    return {
        "reward_scope": "group_level",
        "raw_reward": 1.0,
        "components": {},
        "reward_event_refs": ["rpt_grading_0001"],
        "credit_assignment_strategy": "backend_group_normalized",
        "group_id": "group_task42",
        "parent_rollout_id": "rollout_7",
        "segment_index": 0,
        "segment_count": 1,
        "rollout_loss_denominator": 16,
    }


def valid_trajectory_projection() -> dict[str, Any]:
    return {
        "schema_id": "rh2.trajectory_projection.v1",
        "trajectory_id": "traj_0001",
        "task_id": "django__django-11099",
        "source_framework": "slime",
        "source_object_ref": "rollout_7_sample_0",
        "renderer_cls_name": "Qwen3Renderer",
        "tokenizer_name": "Qwen/Qwen3-30B-A3B",
        "chat_template_hash": SHA_TEMPLATE,
        "branches": [valid_branch()],
        "reward_facts": valid_reward_facts(),
        "created_at_utc": TS,
    }


def valid_capture_record() -> dict[str, Any]:
    return {
        "schema_id": "rh2.generation_capture_record.v1",
        "record_id": "cap_0001",
        "request_id": "68ecd97a303343fdb0d984cd8e86e011",
        "turn_id": "turn_0",
        "trajectory_id": "traj_0001",
        "model_name": "Qwen/Qwen3-30B-A3B",
        "backend_name": "sglang",
        "backend_version": "0.5.9",
        "sampling_params": {
            "temperature": 1.0,
            "top_p": 0.95,
            "max_new_tokens": 16,
            "return_top_p_token_ids": True,
            "return_routed_experts": True,
        },
        "renderer_cls_name": "Qwen3Renderer",
        "tokenizer_name": "Qwen/Qwen3-30B-A3B",
        "template_hash": SHA_TEMPLATE,
        "prompt_token_count": 15,
        "response_token_count": 16,
        "prompt_token_ids_ref": {"ref_id": "prompt_ids_0001"},
        "prompt_token_ids_sha256": SHA_PROMPT,
        "response_token_ids_ref": {"ref_id": "output_ids_0001"},
        "raw_meta_info_digest": SHA_META,
        "logprobs_ref": {"ref_id": "logprobs_0001"},
        "top_p_token_ids_ref": {"ref_id": "topp_ids_0001"},
        "top_p_token_offsets_ref": {"ref_id": "topp_offsets_0001"},
        "routed_experts_ref": {"ref_id": "routing_tape_0001"},
        "capture_status": "complete",
        "alignment_status": "aligned",
        "captured_at_utc": TS,
    }


def valid_eligibility_facts(all_ok: bool = True) -> dict[str, Any]:
    ok_fact: dict[str, Any] = {"ok": True, "reason_codes": [], "evidence_refs": []}
    facts = {
        "token_provenance": dict(ok_fact, evidence_refs=["cap_0001"]),
        "logprob_alignment": dict(ok_fact),
        "loss_mask_integrity": dict(ok_fact),
        "reward_scope": dict(ok_fact),
        "security_and_leakage": dict(ok_fact),
        "clean_grading": dict(ok_fact, evidence_refs=["rpt_grading_0001"]),
        "policy_staleness": dict(ok_fact, evidence_refs=["hs_0001"]),
    }
    if not all_ok:
        facts["logprob_alignment"] = {
            "ok": False,
            "reason_codes": ["logprob_missing"],
            "evidence_refs": [],
        }
    return facts


def valid_eligibility_report() -> dict[str, Any]:
    facts = valid_eligibility_facts()
    digest = compute_facts_digest(EligibilityFacts.model_validate(facts))
    return {
        "schema_id": "rh2.eligibility_report.v1",
        "report_id": "elig_0001",
        "trajectory_id": "traj_0001",
        "branch_id": "b0",
        "gate_version": "gate_s1_v1",
        "facts": facts,
        "facts_digest": digest,
        "eligibility_class": "offline_or_sft_candidate",
        "reason_codes": ["s1_default_ceiling_offline"],
        "derived_view_report_ref": "elig_0001",
        "derived_view_class": "offline_or_sft_candidate",
        "created_at_utc": TS,
    }


def valid_timing_record() -> dict[str, Any]:
    return {
        "schema_id": "rh2.grading_timing_record.v1",
        "record_id": "timing_0001",
        "trajectory_id": "traj_0001",
        "task_id": "django__django-11099",
        "image_pull_seconds": 0.0,
        "env_reset_seconds": 3.2,
        "prep_seconds": 2.1,
        "test_seconds": 41.7,
        "total_grading_seconds": 53.4,
        "queue_wait_seconds": 1.3,
        "container_peak_memory_mb": 2048.0,
        "queue_depth_at_enqueue": 2,
        "backpressure_triggered": False,
    }


def valid_patch_hygiene() -> dict[str, Any]:
    return {
        "cleaned_patch_digest": SHA_PATCH,
        "replayed_on_clean_checkout": True,
        "test_files_modified": False,
        "forbidden_path_touched": False,
        "forbidden_paths": [],
        "verdict": "clean",
    }


def valid_grading_report() -> dict[str, Any]:
    return {
        "schema_id": "rh2.grading_report.v1",
        "report_id": "rpt_grading_0001",
        "trajectory_id": "traj_0001",
        "task_id": "django__django-11099",
        "grader_name": "swebench_official_parser",
        "grader_version": "swebench-4.1.0",
        "outcome": "resolved",
        "failure_category": None,
        "reward": 1.0,
        "reward_scale_version": "binary_v1",
        "f2p_pass_count": 3,
        "f2p_total_count": 3,
        "p2p_fail_count": 0,
        "p2p_total_count": 52,
        "patch_hygiene": valid_patch_hygiene(),
        "eval_log_ref": {"ref_id": "eval_log_0001"},
        "timings": valid_timing_record(),
        "graded_at_utc": TS,
    }


def valid_infra_grading_report() -> dict[str, Any]:
    """infra_failure 的合法形态：无 reward、无测试计数、有故障描述。"""

    return {
        "schema_id": "rh2.grading_report.v1",
        "report_id": "rpt_grading_0002",
        "trajectory_id": "traj_0002",
        "task_id": "django__django-11099",
        "grader_name": "swebench_official_parser",
        "grader_version": "swebench-4.1.0",
        "outcome": "failed_to_grade",
        "failure_category": "infra_failure",
        "reward": None,
        "reward_scale_version": "binary_v1",
        "infra_failure_detail": "grading_container_killed_oom",
        "graded_at_utc": TS,
    }


def valid_anti_cheat_finding() -> dict[str, Any]:
    return {
        "schema_id": "rh2.anti_cheat_finding.v1",
        "finding_id": "finding_0001",
        "trajectory_id": "traj_0001",
        "category": "internet_answer_lookup",
        "phase": "rollout",
        "enforcement": "attempted_blocked",
        "detection_layer": "online_interception",
        "anti_hack_event_ref": "antihack_0001",
        "evidence_refs": ["cmd_log_0042"],
        "description": "agent ran `git fetch origin` inside /testbed; blocked by rule block_remote_git",
        "detected_at_utc": TS,
    }


def valid_quality_finding() -> dict[str, Any]:
    return {
        "schema_id": "rh2.trajectory_quality_finding.v1",
        "finding_id": "finding_0002",
        "trajectory_id": "traj_0001",
        "category": "max_turns_reached",
        "severity": "warning",
        "evidence_refs": ["turn_log_0001"],
        "description": "trajectory hit 64-turn cap before final patch",
        "detected_at_utc": TS,
    }


def valid_anti_hack_event() -> dict[str, Any]:
    return {
        "schema_id": "rh2.anti_hack_event.v1",
        "event_id": "antihack_0001",
        "trajectory_id": "traj_0001",
        "turn_id": "turn_3",
        "rule_id": "block_remote_git",
        "channel": "network_egress",
        "blocked_tool_call_ref": {"ref_id": "blocked_call_0001"},
        "dummy_observation_ref": {"ref_id": "dummy_obs_0001"},
        "rollout_continued": True,
        "occurred_at_utc": TS,
    }


def valid_cleanup_policy() -> dict[str, Any]:
    return {
        "schema_id": "rh2.cleanup_policy.v1",
        "owner": "repoharness_envpack",
        "steps": ["remove_container", "remove_temp_dirs", "release_lease"],
        "on_cleanup_failure": "record_runtime_finding_and_infra_failure",
        "timeout_seconds": 120,
    }


def valid_sandbox_lease() -> dict[str, Any]:
    return {
        "schema_id": "rh2.sandbox_lease.v1",
        "lease_id": "lease_0001",
        "container_id": "rh2_rollout_traj_0001",
        "image_digest": SHA_IMAGE,
        "purpose": "rollout",
        "created_by": "repoharness_envpack",
        "network_policy_owner": "repoharness_envpack",
        "network_policy": "deny_all",
        "permission_policy_owner": "repoharness_envpack",
        "run_as_user": "root",
        "cleanup": valid_cleanup_policy(),
        "created_at_utc": TS,
    }


def valid_workspace_handle() -> dict[str, Any]:
    return {
        "schema_id": "rh2.workspace_handle.v1",
        "workspace_id": "ws_0001",
        "lease_id": "lease_0001",
        "role": "rollout_workspace",
        "testbed_path": "/testbed",
        "materialized_by": "repoharness_envpack",
        "base_commit": BASE_COMMIT,
        "head_commit": HEAD_COMMIT,
        "lineage_check": "head_parent_equals_base",
        "mounted_bundles": [
            {
                "bundle_kind": "public_task_bundle",
                "bundle_digest": SHA_BUNDLE,
                "mount_path": "/rh2/task_bundle",
            }
        ],
        "materialized_at_utc": TS,
    }


def valid_model_proxy_endpoint() -> dict[str, Any]:
    return {
        "schema_id": "rh2.model_proxy_endpoint.v1",
        "base_url": "http://10.0.0.5:8200",
        "wire_protocol": "anthropic_messages",
        "session_id": "sess_traj_0001",
        "inject_env_var": "ANTHROPIC_BASE_URL",
    }


def valid_harness_launch_spec() -> dict[str, Any]:
    return {
        "schema_id": "rh2.harness_launch_spec.v1",
        "harness_name": "claude_code",
        "workspace_id": "ws_0001",
        "workdir": "/testbed",
        "model_proxy": valid_model_proxy_endpoint(),
        "env_injections": {"BASH_ENV": "/root/.rh2_bash_env"},
        "time_budget_seconds": 1800,
    }


def valid_group_signal() -> dict[str, Any]:
    return {
        "group_id": "group_task42",
        "expected_group_size": 4,
        "delivered_sample_count": 3,
        "degraded_sample_count": 1,
        "degrade_visible_before_assembly": True,
    }


def valid_backend_handshake() -> dict[str, Any]:
    return {
        "schema_id": "rh2.backend_handshake.v1",
        "handshake_id": "hs_0001",
        "trajectory_id": "traj_0001",
        "backend_name": "slime",
        "policy_version": "step_120",
        "weight_versions_seen": ["default"],
        "staleness_steps": 1,
        "staleness_threshold": 4,
        "staleness_within_threshold": True,
        "group_signal": valid_group_signal(),
        "accepted": True,
        "backend_rejection_reason": None,
        "rejection_note": None,
        "handshaked_at_utc": TS,
    }


# schema_id -> 合法样例工厂（registry 级参数化测试 + CLI 测试共用）。
VALID_SAMPLE_FACTORIES = {
    "rh2.trajectory_projection.v1": valid_trajectory_projection,
    "rh2.generation_capture_record.v1": valid_capture_record,
    "rh2.eligibility_report.v1": valid_eligibility_report,
    "rh2.grading_report.v1": valid_grading_report,
    "rh2.grading_timing_record.v1": valid_timing_record,
    "rh2.anti_cheat_finding.v1": valid_anti_cheat_finding,
    "rh2.trajectory_quality_finding.v1": valid_quality_finding,
    "rh2.anti_hack_event.v1": valid_anti_hack_event,
    "rh2.sandbox_lease.v1": valid_sandbox_lease,
    "rh2.workspace_handle.v1": valid_workspace_handle,
    "rh2.harness_launch_spec.v1": valid_harness_launch_spec,
    "rh2.model_proxy_endpoint.v1": valid_model_proxy_endpoint,
    "rh2.cleanup_policy.v1": valid_cleanup_policy,
    "rh2.backend_handshake.v1": valid_backend_handshake,
}
