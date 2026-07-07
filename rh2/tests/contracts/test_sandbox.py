"""sandbox.py 的 fail-closed 单测：A5 八问契约的关键拒收路径。

最关键的一条（A6 核心规则）：rollout 工作区挂载 private grading bundle 必须拒收。
"""

import pytest
from contract_samples import (
    valid_cleanup_policy,
    valid_harness_launch_spec,
    valid_model_proxy_endpoint,
    valid_sandbox_lease,
    valid_workspace_handle,
    SHA_BUNDLE,
)
from pydantic import ValidationError

from repoharness2.contracts import (
    CleanupPolicy,
    HarnessLaunchSpec,
    ModelProxyEndpoint,
    SandboxLease,
    WorkspaceHandle,
)

# ---------------------------------------------------------------------------
# WorkspaceHandle（Q2/Q6）
# ---------------------------------------------------------------------------


def test_rollout_workspace_mounting_private_bundle_rejected():
    """点名非法样例：private grading bundle 永不进 rollout 容器（A6）。"""

    payload = valid_workspace_handle()
    payload["mounted_bundles"].append(
        {
            "bundle_kind": "private_grading_bundle",
            "bundle_digest": SHA_BUNDLE,
            "mount_path": "/rh2/private_bundle",
        }
    )
    with pytest.raises(ValidationError, match="private_grading_bundle"):
        WorkspaceHandle.model_validate(payload)


def test_grading_workspace_may_mount_private_bundle():
    payload = valid_workspace_handle()
    payload["role"] = "grading_workspace"
    payload["mounted_bundles"].append(
        {
            "bundle_kind": "private_grading_bundle",
            "bundle_digest": SHA_BUNDLE,
            "mount_path": "/rh2/private_bundle",
        }
    )
    handle = WorkspaceHandle.model_validate(payload)
    assert handle.role == "grading_workspace"


def test_lineage_head_equals_base_mismatch_rejected():
    payload = valid_workspace_handle()
    payload["lineage_check"] = "head_equals_base"  # 但 head != base
    with pytest.raises(ValidationError, match="head_equals_base"):
        WorkspaceHandle.model_validate(payload)


def test_lineage_parent_rule_with_identical_commits_rejected():
    payload = valid_workspace_handle()
    payload["head_commit"] = payload["base_commit"]  # 相同却声明叠加提交
    with pytest.raises(ValidationError, match="head_parent_equals_base"):
        WorkspaceHandle.model_validate(payload)


def test_lineage_failed_value_not_representable():
    """血缘校验没有"未通过"取值：失败的物化根本构造不出 WorkspaceHandle。"""

    payload = valid_workspace_handle()
    payload["lineage_check"] = "lineage_failed"
    with pytest.raises(ValidationError):
        WorkspaceHandle.model_validate(payload)


def test_relative_testbed_path_rejected():
    payload = valid_workspace_handle()
    payload["testbed_path"] = "testbed"
    with pytest.raises(ValidationError, match="绝对路径"):
        WorkspaceHandle.model_validate(payload)


# ---------------------------------------------------------------------------
# SandboxLease（Q1/Q5）
# ---------------------------------------------------------------------------


def test_grading_lease_must_deny_all_network():
    payload = valid_sandbox_lease()
    payload["purpose"] = "grading"
    payload["network_policy"] = "allowlist"
    payload["network_allowlist_justification"] = "should not matter"
    with pytest.raises(ValidationError, match="全断网"):
        SandboxLease.model_validate(payload)


def test_host_open_network_not_representable():
    payload = valid_sandbox_lease()
    payload["network_policy"] = "host_open"
    with pytest.raises(ValidationError, match="host_open"):
        SandboxLease.model_validate(payload)


def test_allowlist_requires_justification():
    payload = valid_sandbox_lease()
    payload["network_policy"] = "allowlist"
    with pytest.raises(ValidationError, match="justification"):
        SandboxLease.model_validate(payload)


def test_unknown_owner_party_rejected():
    payload = valid_sandbox_lease()
    payload["created_by"] = "random_third_party"
    with pytest.raises(ValidationError):
        SandboxLease.model_validate(payload)


# ---------------------------------------------------------------------------
# CleanupPolicy（Q7/Q8）
# ---------------------------------------------------------------------------


def test_cleanup_steps_must_be_unique():
    payload = valid_cleanup_policy()
    payload["steps"] = ["remove_container", "remove_container"]
    with pytest.raises(ValidationError, match="重复"):
        CleanupPolicy.model_validate(payload)


def test_cleanup_silent_failure_not_representable():
    """Q8：不存在"清理失败但不记录"的取值。"""

    payload = valid_cleanup_policy()
    payload["on_cleanup_failure"] = "ignore_silently"
    with pytest.raises(ValidationError):
        CleanupPolicy.model_validate(payload)


def test_cleanup_requires_at_least_one_step():
    payload = valid_cleanup_policy()
    payload["steps"] = []
    with pytest.raises(ValidationError):
        CleanupPolicy.model_validate(payload)


# ---------------------------------------------------------------------------
# ModelProxyEndpoint / HarnessLaunchSpec（Q3/Q4）
# ---------------------------------------------------------------------------


def test_protocol_env_var_mismatch_rejected():
    payload = valid_model_proxy_endpoint()
    payload["inject_env_var"] = "OPENAI_BASE_URL"  # anthropic_messages 协议
    with pytest.raises(ValidationError, match="ANTHROPIC_BASE_URL"):
        ModelProxyEndpoint.model_validate(payload)


def test_non_http_base_url_rejected():
    payload = valid_model_proxy_endpoint()
    payload["base_url"] = "10.0.0.5:8200"
    with pytest.raises(ValidationError, match="http"):
        ModelProxyEndpoint.model_validate(payload)


def test_relative_workdir_rejected():
    payload = valid_harness_launch_spec()
    payload["workdir"] = "testbed"
    with pytest.raises(ValidationError, match="绝对路径"):
        HarnessLaunchSpec.model_validate(payload)


def test_env_injection_with_forbidden_marker_rejected():
    """把私有 bundle 路径注进 harness 环境 = 直接泄漏给模型，必须拒收。"""

    payload = valid_harness_launch_spec()
    payload["env_injections"]["RH2_HINT"] = "/rh2/private/test_patch.diff"
    with pytest.raises(ValidationError, match="forbidden marker"):
        HarnessLaunchSpec.model_validate(payload)


def test_env_injection_lowercase_key_rejected():
    payload = valid_harness_launch_spec()
    payload["env_injections"]["bash_env"] = "/root/.rh2_bash_env"
    with pytest.raises(ValidationError, match="大写"):
        HarnessLaunchSpec.model_validate(payload)
