"""`SandboxCapabilityFacts`：**冻结历史 schema（v1），不进新 formal 链。**

来历与现状（Wave3 前置清理批，决策包 D2+B v2，owner 2026-09-04 已批）：

- W1b 第二段（2026-09-02）把 A3"不许 `findings=()` 假过"落成了**每轨迹**能力事实证明
  系统：sandbox 创建后由 producer 核实并记录本对象，gate 的 security 维要求它在场、
  九项必需能力全部已核实、无违规，缺一即非 online（`sandbox_capability_facts_missing` /
  `sandbox_capability_unverified_<name>` / `sandbox_capability_violation_<name>`），并按
  lease_id 绑定到本次 attempt 的容器租约。
- D2-2 改判了这套机制：声明 ≠ 执行；先跑完昂贵 rollout 再 DROP_GROUP，同 profile 补采
  还会重复失败。sandbox 合规改由 W3b 在**创建期直接配置 + 启动前最小探针**保证（配置
  缺失或实际未生效 → 不启动/停止 run），并只保留一份 run 级记录（`runtime_profile_digest`
  + 探针报告引用），不再逐轨迹证明。于是 gate / wrapper / generate / admission 对本对象的
  全部消费、`REQUIRED_SANDBOX_CAPABILITIES` 必需集、provider 注入位与 lease 绑定检查
  已整体删除（`GATE_VERSION` 升到 `rh2.gate.w3pre.v3`）。

为什么还保留类型：它是曾经公开过的 schema（`rh2.sandbox_capability_facts.v1`），
S1/W1b 时代的 evidence、inspector 与测试夹具可能持有这种形状的 JSON；保留一个只读的
校验器让这些历史材料仍可解析（兼容读路径），但**任何新 formal 代码都不得 import 它做
资格判定**——W3b 的 run 级记录是另一份 schema，不复用本对象。

历史必需集（仅供解读旧材料，不再是消费契约）：non_root_user、linux_capabilities_dropped、
pids_limit_enforced、cpu_limit_enforced、memory_limit_enforced、
writable_mounts_allowlisted_with_quota、network_model_proxy_only、
hidden_and_grader_assets_not_mounted、git_future_refs_reflog_remotes_cleared。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from repoharness2.contracts import NonEmptyStr, SafeIdentifier, StrictModel

__all__ = ["SandboxCapabilityFacts"]


class SandboxCapabilityFacts(StrictModel):
    """一次 rollout sandbox 的正向能力事实——冻结历史 schema（v1），只作兼容读路径。

    字段语义按 W1b 第二段原文保留：`verified_capabilities` 是当时声称已核实生效的能力项名，
    `violations` 是核实过程中发现的违规项；校验器只保证清单无歧义（无重复、已核实与违规
    不重叠）。**没有任何 formal 链代码消费本对象**（见模块 docstring）。
    """

    schema_id: Literal["rh2.sandbox_capability_facts.v1"] = Field(
        default="rh2.sandbox_capability_facts.v1", description="schema 判别字段（冻结）。"
    )
    trajectory_id: NonEmptyStr = Field(description="被核实 sandbox 所属轨迹 id。")
    lease_id: NonEmptyStr = Field(description="SandboxLease.lease_id（能力事实当时锚到的容器租约）。")
    verified_capabilities: list[SafeIdentifier] = Field(
        default_factory=list, description="当时声称已核实生效的能力项名。"
    )
    violations: list[SafeIdentifier] = Field(
        default_factory=list, description="核实时发现的违规项名。"
    )
    evidence_refs: list[NonEmptyStr] = Field(
        default_factory=list, description="核实证据引用（探针输出 artifact 等）。"
    )
    verified_at_utc: AwareDatetime = Field(description="核实时间（必须带时区）。")

    @model_validator(mode="after")
    def _check_capability_facts(self) -> "SandboxCapabilityFacts":
        if len(set(self.verified_capabilities)) != len(self.verified_capabilities):
            raise ValueError("verified_capabilities 含重复项（事实清单必须无歧义）。")
        if len(set(self.violations)) != len(self.violations):
            raise ValueError("violations 含重复项（事实清单必须无歧义）。")
        overlap = sorted(set(self.verified_capabilities) & set(self.violations))
        if overlap:
            raise ValueError(f"同一能力项既声称已核实又列为违规：{overlap}（矛盾事实不可表示）。")
        return self
