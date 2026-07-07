"""sandbox 所有权握手契约（补充条款 A5，S1-6 编排的 schema 先行）。

背景：slime 的 Claude Code harness 假设自己拥有 Sandbox Protocol；RepoHarness
envpack 又要负责 /testbed 物化、public/private bundle、评分边界与清理。
两边若没有显式握手契约，S1-6 会变成临时胶水（U-I 风险）。本模块把 A5 的
八个问题逐一固化为字段：

  Q1 谁创建容器            -> SandboxLease.created_by
  Q2 谁物化 /testbed        -> WorkspaceHandle.materialized_by + 血缘字段
  Q3 harness workdir 如何传入 -> HarnessLaunchSpec.workdir
  Q4 模型代理地址如何注入     -> ModelProxyEndpoint（inject_env_var + base_url）
  Q5 网络/权限策略归属        -> SandboxLease.network_policy_owner / permission_policy_owner
  Q6 两类 bundle 如何挂载     -> WorkspaceHandle.mounted_bundles（rollout 禁挂 private）
  Q7 失败后谁负责清理         -> CleanupPolicy.owner + steps
  Q8 清理失败如何记录         -> CleanupPolicy.on_cleanup_failure（必须落 finding/infra_failure）
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts._base import (
    GitSha,
    NonEmptyStr,
    Sha256Digest,
    StrictModel,
)
from repoharness2.contracts.constants import find_forbidden_marker

# 握手双方的所有权词表（封闭枚举：新角色必须先修契约再上场）。
OwnerParty = Literal[
    "repoharness_envpack",  # RepoHarness 环境包库层（物化、血缘校验）
    "slime_adapter",  # custom_generate 编排胶水（S1-6）
    "slime_harness",  # slime 的 Claude Code harness 运行层
    "grading_manager",  # SWEGradingManager（评分沙箱一侧）
]

NetworkPolicy = Literal[
    "deny_all",  # 全断网（评分沙箱的唯一合法值；rollout 默认值）
    "allowlist",  # 白名单放行（必须写明理由，audit artifact 解释为什么允许）
    "host_open",  # 宿主网络直通（verifiers docker 旧形态——本契约禁止表示）
]

BundleKind = Literal[
    "public_task_bundle",  # 模型可见：题面、repo/base_commit、镜像 digest、允许工具、公开提示
    "private_grading_bundle",  # 评分私有：test_patch、F2P/P2P、官方 parser 配置、golden 相关
]


class BundleMount(StrictModel):
    """一次 bundle 挂载事实（哪个 bundle、什么 digest、挂到容器哪个路径）。"""

    bundle_kind: BundleKind = Field(description="bundle 类别（public 或 private，A6 拆分）。")
    bundle_digest: Sha256Digest = Field(description="bundle 内容 digest（S1-2 冻结固化的锚点）。")
    mount_path: NonEmptyStr = Field(description="容器内挂载路径（绝对路径）。")

    @model_validator(mode="after")
    def _check_mount_path(self) -> "BundleMount":
        if not self.mount_path.startswith("/"):
            raise ValueError(f"mount_path 必须是容器内绝对路径，得到 {self.mount_path!r}。")
        return self


class CleanupPolicy(StrictModel):
    """清理责任契约（A5 Q7/Q8）。

    fail-closed 行为：on_cleanup_failure 的取值封闭且都包含"记录"义务——
    "清理失败但不留痕"在本 schema 下不可表示（Q8）。
    """

    schema_id: Literal["rh2.cleanup_policy.v1"] = Field(
        default="rh2.cleanup_policy.v1", description="schema 判别字段。"
    )
    owner: OwnerParty = Field(description="Q7：失败后由谁负责清理容器、临时目录与挂载。")
    steps: list[Literal["remove_container", "remove_temp_dirs", "remove_mounts", "release_lease"]] = Field(
        min_length=1,
        description="清理步骤清单（去重有序）。至少包含一步；漏写的步骤视为没人负责。",
    )
    on_cleanup_failure: Literal[
        "record_runtime_finding_and_infra_failure",  # 记 runtime finding + FailureCategory=infra_failure（默认）
        "record_finding_and_escalate_abort",  # 记录后升级中止本次 run（用于泄漏风险高的场景）
    ] = Field(
        description="Q8：清理失败的处置。两个取值都强制\"先记录\"，不存在静默吞掉的选项。"
    )
    timeout_seconds: int = Field(gt=0, description="单次清理动作的超时（秒）。")

    @model_validator(mode="after")
    def _check_steps_unique(self) -> "CleanupPolicy":
        if len(self.steps) != len(set(self.steps)):
            raise ValueError(f"清理步骤不得重复：{self.steps}。")
        return self


class SandboxLease(StrictModel):
    """一次沙箱容器租约（谁建的、干什么用、网络/权限归谁、怎么清理）。

    fail-closed 校验清单：
    1. network_policy=host_open 一律拒收（宿主网络直通没有审计边界）；
    2. purpose=grading 时 network_policy 必须是 deny_all（P9：评分沙箱同等隔离）；
    3. network_policy=allowlist 必须写 network_allowlist_justification（审计解释）。
    """

    schema_id: Literal["rh2.sandbox_lease.v1"] = Field(
        default="rh2.sandbox_lease.v1", description="schema 判别字段。"
    )
    lease_id: NonEmptyStr = Field(description="租约 id（WorkspaceHandle.lease_id 指向它）。")
    container_id: NonEmptyStr = Field(description="容器 id（docker 容器名或 id）。")
    image_digest: Sha256Digest = Field(
        description="容器镜像 digest（官方任务镜像或 pin 过的 slime 镜像，如 sha256:a7317182…）。"
    )
    purpose: Literal["rollout", "grading"] = Field(
        description="容器用途：agent rollout 或 clean grading（两者永不混用同一容器）。"
    )
    created_by: OwnerParty = Field(description="Q1：谁创建了这个容器。")
    network_policy_owner: OwnerParty = Field(description="Q5a：网络策略由谁拥有与执行。")
    network_policy: NetworkPolicy = Field(description="实际生效的网络策略。")
    network_allowlist_justification: NonEmptyStr | None = Field(
        default=None,
        description="allowlist 时必填：为什么这个任务允许这些外联（audit artifact 语义）。",
    )
    permission_policy_owner: OwnerParty = Field(description="Q5b：容器内权限/用户策略由谁拥有。")
    run_as_user: NonEmptyStr = Field(description="容器内运行身份（如 root——S0 现状，或降权用户）。")
    cleanup: CleanupPolicy = Field(description="Q7/Q8：清理责任契约（内嵌）。")
    created_at_utc: AwareDatetime = Field(description="租约创建时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_lease_contract(self) -> "SandboxLease":
        if self.network_policy == "host_open":
            raise ValueError(
                "network_policy=host_open 不可表示：宿主网络直通没有可审计边界"
                "（verifiers docker 旧形态在 rh2 契约下必须先降为 allowlist/deny_all）。"
            )
        if self.purpose == "grading" and self.network_policy != "deny_all":
            raise ValueError(
                f"评分容器必须全断网（P9），得到 network_policy={self.network_policy}。"
            )
        if self.network_policy == "allowlist" and self.network_allowlist_justification is None:
            raise ValueError("network_policy=allowlist 必须提供 network_allowlist_justification。")
        if self.network_policy != "allowlist" and self.network_allowlist_justification is not None:
            raise ValueError("非 allowlist 策略不得携带 network_allowlist_justification。")
        return self


LineageCheck = Literal[
    "head_equals_base",  # HEAD == base_commit（干净 checkout）
    "head_parent_equals_base",  # HEAD 是官方构建叠加提交且 HEAD^ == base_commit（SWE 官方镜像常态）
]


class WorkspaceHandle(StrictModel):
    """一个已物化工作区的句柄（/testbed 血缘已验证 + bundle 挂载清单）。

    血缘判据（S0-7 发现 2）：官方镜像的 HEAD 都不是 base_commit 本身
    （django-11099：HEAD=2a2861e0…，HEAD^=d26b2424…=base），且叠加的
    "SWE-bench" 提交不保证内容为空，所以只能校验血缘，不能比对树内容。
    `lineage_check` 只有两个"通过"取值——物化校验失败的工作区
    根本构造不出 WorkspaceHandle（fail-closed by construction）。

    fail-closed 校验清单：
    1. role=rollout_workspace 时 mounted_bundles 里禁止出现 private_grading_bundle
       （A6 核心规则：private bundle 永不进 rollout 容器）；
    2. lineage_check=head_equals_base 时 head_commit 必须等于 base_commit；
       head_parent_equals_base 时两者必须不同；
    3. testbed_path 必须是绝对路径。
    """

    schema_id: Literal["rh2.workspace_handle.v1"] = Field(
        default="rh2.workspace_handle.v1", description="schema 判别字段。"
    )
    workspace_id: NonEmptyStr = Field(description="工作区 id。")
    lease_id: NonEmptyStr = Field(description="所属 SandboxLease.lease_id。")
    role: Literal["rollout_workspace", "grading_workspace"] = Field(
        description="工作区角色：agent 读写的 rollout 工作区，或评分用 clean checkout。"
    )
    testbed_path: NonEmptyStr = Field(
        description="容器内代码库路径（SWE 官方镜像约定 /testbed）。"
    )
    materialized_by: OwnerParty = Field(
        description="Q2：谁物化了 /testbed（S1 定案：repoharness_envpack 库层）。"
    )
    base_commit: GitSha = Field(description="任务基准 commit（40 位十六进制）。")
    head_commit: GitSha = Field(description="物化后工作区 HEAD commit。")
    lineage_check: LineageCheck = Field(
        description="血缘校验通过方式。没有\"未通过\"取值——校验失败就不该有这个句柄。"
    )
    mounted_bundles: list[BundleMount] = Field(
        default_factory=list, description="已挂载的 bundle 清单（A6 拆分后的 public/private）。"
    )
    materialized_at_utc: AwareDatetime = Field(description="物化完成时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_workspace_contract(self) -> "WorkspaceHandle":
        if not self.testbed_path.startswith("/"):
            raise ValueError(f"testbed_path 必须是容器内绝对路径，得到 {self.testbed_path!r}。")
        if self.role == "rollout_workspace":
            private = [m for m in self.mounted_bundles if m.bundle_kind == "private_grading_bundle"]
            if private:
                raise ValueError(
                    "rollout_workspace 禁止挂载 private_grading_bundle"
                    f"（A6：评分私有资产永不进 rollout 容器），发现 {len(private)} 个私有挂载。"
                )
        if self.lineage_check == "head_equals_base" and self.head_commit != self.base_commit:
            raise ValueError(
                f"lineage_check=head_equals_base 但 head({self.head_commit}) != base({self.base_commit})。"
            )
        if self.lineage_check == "head_parent_equals_base" and self.head_commit == self.base_commit:
            raise ValueError(
                "lineage_check=head_parent_equals_base 但 HEAD 与 base_commit 相同"
                "（该取值表示 HEAD 是叠加提交，两者必须不同）。"
            )
        return self


class ModelProxyEndpoint(StrictModel):
    """模型代理端点注入契约（A5 Q4：黑盒 harness 的模型请求如何被接管）。

    slime 形态：Anthropic adapter 起一个 HTTP 端点，Claude Code 通过
    ANTHROPIC_BASE_URL 指向它；session_id 兼作 auth token 与路由键，
    把多轮请求归入同一 trajectory。

    fail-closed 行为：wire_protocol 与注入的环境变量名必须匹配
    （anthropic_messages -> ANTHROPIC_BASE_URL；openai_chat -> OPENAI_BASE_URL），
    防止把 OpenAI 客户端指到 Anthropic 端点这类静默错配。
    """

    schema_id: Literal["rh2.model_proxy_endpoint.v1"] = Field(
        default="rh2.model_proxy_endpoint.v1", description="schema 判别字段。"
    )
    base_url: NonEmptyStr = Field(description="代理端点地址（http(s)://host:port）。")
    wire_protocol: Literal["anthropic_messages", "openai_chat"] = Field(
        description="代理暴露的 wire 协议（Claude Code 用 anthropic_messages；Codex 用 openai_chat）。"
    )
    session_id: NonEmptyStr = Field(
        description="会话 id：兼作 auth token 与路由键（X-SMG-Routing-Key），多轮请求归组的唯一依据。"
    )
    inject_env_var: Literal["ANTHROPIC_BASE_URL", "OPENAI_BASE_URL"] = Field(
        description="Q4：地址通过哪个环境变量注入 harness 进程。"
    )

    @model_validator(mode="after")
    def _check_endpoint_contract(self) -> "ModelProxyEndpoint":
        if not (self.base_url.startswith("http://") or self.base_url.startswith("https://")):
            raise ValueError(f"base_url 必须以 http:// 或 https:// 开头，得到 {self.base_url!r}。")
        expected_env = {
            "anthropic_messages": "ANTHROPIC_BASE_URL",
            "openai_chat": "OPENAI_BASE_URL",
        }[self.wire_protocol]
        if self.inject_env_var != expected_env:
            raise ValueError(
                f"wire_protocol={self.wire_protocol} 要求 inject_env_var={expected_env}，"
                f"得到 {self.inject_env_var}（防止客户端与端点协议错配）。"
            )
        return self


class HarnessLaunchSpec(StrictModel):
    """harness 启动契约（A5 Q3/Q4 的合成点：在哪个工作区、什么 workdir、连哪个代理）。

    fail-closed 行为：
    1. workdir 必须是绝对路径（Q3 的"如何传入"必须落成明确值，不接受相对路径）；
    2. env_injections 的 key 必须是大写环境变量名；key 与 value 都过 forbidden
       marker 扫描——把私有 bundle 路径（如 /grading/test_patch.diff）注进
       harness 环境等于直接泄漏给模型。
    """

    schema_id: Literal["rh2.harness_launch_spec.v1"] = Field(
        default="rh2.harness_launch_spec.v1", description="schema 判别字段。"
    )
    harness_name: Literal["claude_code", "codex", "mock_harness"] = Field(
        description="harness 类型（S1 主线 claude_code；mock_harness 供 S1-6 单测）。"
    )
    workspace_id: NonEmptyStr = Field(description="运行所在的 WorkspaceHandle.workspace_id。")
    workdir: NonEmptyStr = Field(
        description="Q3：harness 进程的工作目录（容器内绝对路径，SWE 任务为 /testbed）。"
    )
    model_proxy: ModelProxyEndpoint = Field(description="Q4：模型代理端点（内嵌）。")
    env_injections: dict[str, str] = Field(
        default_factory=dict,
        description="额外注入 harness 进程的环境变量（模型可见面，key/value 都过 marker 扫描）。",
    )
    time_budget_seconds: int = Field(gt=0, description="本次 harness 运行的时间预算（秒）。")

    @model_validator(mode="after")
    def _check_launch_contract(self) -> "HarnessLaunchSpec":
        if not self.workdir.startswith("/"):
            raise ValueError(f"workdir 必须是容器内绝对路径，得到 {self.workdir!r}。")
        for key, value in self.env_injections.items():
            if not key or not key.isupper() or not key.replace("_", "").isalnum():
                raise ValueError(f"环境变量名必须是大写标识符（如 BASH_ENV），得到 {key!r}。")
            for text, kind in ((key, "变量名"), (value, "变量值")):
                marker = find_forbidden_marker(text)
                if marker is not None:
                    raise ValueError(
                        f"env_injections {kind} {text!r} 命中 forbidden marker {marker!r}："
                        "harness 环境是模型可见面，禁止携带评分私有信息。"
                    )
        return self
