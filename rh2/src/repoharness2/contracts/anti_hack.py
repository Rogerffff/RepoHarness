"""AntiHackEvent：在线拦截事件（设计文档 2 §5.3 定案的"block + dummy 观测 + 继续"语义）。

拦截语义（GLM-5.2 online guard 同款）：运行期规则层检出可疑动作（外联下载答案、
git 历史挖掘、读私有资产…）时，**拦截该次工具调用**、给模型返回一个脱敏的
dummy 观测、rollout 继续——处理具体无效行为而非整轨拒绝，避免掐断 rollout
造成训练不稳定。每次拦截产生一条本事件，作为 AntiCheatFinding
（enforcement=attempted_blocked）的证据底座。

schema 先行说明：S1-1 只落 schema；真正的拦截 filter 在 S2 接入。
本对象是 runtime-private 审计资产（它要描述被拦的私有路径与命令），
在 marker 扫描中属豁免名单，但禁止进入 public projection。
"""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field

from repoharness2.contracts._base import ArtifactRef, NonEmptyStr, StrictModel

InterceptionChannel = Literal[
    "network_egress",  # 外联通道（remote git / GitHub raw / release asset / gist …）
    "git_history",  # 本地 git 残留挖掘（reflog、未来对象恢复…）
    "filesystem_probe",  # 读运行时私有 / grader-only 路径的尝试
    "suspicious_command",  # 其他规则命中的可疑命令
]


class AntiHackEvent(StrictModel):
    """一次在线拦截的完整事实（block 了什么、回了什么 dummy、rollout 是否继续）。

    创建者：运行期命令过滤 / 网络拦截层（S2 接入，schema 先行）。
    消费者：AntiCheatFinding（attempted_blocked 必须回链本事件）、
    EligibilityGate 的 security_and_leakage 维度、审计与红队回放。

    fail-closed 行为：blocked_tool_call_ref 与 dummy_observation_ref 都是必填——
    "拦了但没存证"或"没告诉模型任何观测"的拦截在本 schema 下不可表示。
    """

    schema_id: Literal["rh2.anti_hack_event.v1"] = Field(
        default="rh2.anti_hack_event.v1", description="schema 判别字段。"
    )
    event_id: NonEmptyStr = Field(description="拦截事件 id（AntiCheatFinding.anti_hack_event_ref 指向它）。")
    trajectory_id: NonEmptyStr = Field(description="发生拦截的轨迹 id。")
    turn_id: NonEmptyStr | None = Field(
        default=None, description="发生拦截的轮次 id（可定位到具体生成轮；不可定位时为 None）。"
    )
    rule_id: NonEmptyStr = Field(
        description="命中的拦截规则 id（如 block_remote_git、block_github_raw），规则集版本化管理。"
    )
    channel: InterceptionChannel = Field(description="被拦截动作走的通道分类。")
    blocked_tool_call_ref: ArtifactRef = Field(
        description=(
            "被拦截的原始工具调用存证（完整命令/参数，runtime-private）。"
            "必填：没有原始调用存证的拦截无法审计、无法回放。"
        )
    )
    dummy_observation_ref: ArtifactRef = Field(
        description=(
            "返回给模型的脱敏 dummy 观测存证。必填：治理层必须能核对模型上下文里"
            "实际注入了什么（证明泄漏内容没有进入模型可见面）。"
        )
    )
    rollout_continued: bool = Field(
        description=(
            "拦截后 rollout 是否继续（定案语义应为 True；False 表示拦截意外中断了轨迹，"
            "这本身是需要审计的异常事实，允许表示但 gate 会关注）。"
        )
    )
    occurred_at_utc: AwareDatetime = Field(description="拦截发生时间（必须带时区）。")
