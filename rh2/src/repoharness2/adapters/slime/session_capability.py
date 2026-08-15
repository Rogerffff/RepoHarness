"""F2-2：每 physical attempt 的 session 授权凭证（capability）。

背景（05 计划 F2-1/F2-2 身份与凭证 + F2-2 钉死验收）：CC harness 的
wire 凭证与 session id 是同一个字符串（`ANTHROPIC_AUTH_TOKEN=session_id`，
slime `AnthropicAdapter._session_id` 从 auth 头解出 sid）。S1 时代 sid 由
task/index 稳定派生——replay 会复用同一 sid，而真实 slime 的
`shutdown_session` 把 sid 永久留在 `closed` 集合（`open_session` 只查
`store` 不清 `closed`），且 `_sid_turn_count` 同样不随 finish/drop 清理：
稳定 sid 的第二次物理 attempt 一开口就收 503，或继承上次的 turn 计数
提前 429。

设计（D2 四层身份已批准）：

- `rollout_execution_id` / trajectory_id：**公开、replay 稳定**——审计、
  artifact 命名、GRPO 身份都用它，跨物理 attempt 不变。
- `session_auth_capability`：**128-bit 随机、每 physical attempt 铸造、
  仅当前会话有效、会话关闭即失效**。它就是 wire 上的 sid + auth token，
  所以 slime 的 closed/turn-count 状态天然按 attempt 隔离——replay 用
  新 capability，旧状态不可能沾染。
- token 是秘密（进内存与 CC 环境变量，不落任何持久 artifact）；持久面
  一律用 `fingerprint`（sha256 截断，不可逆推 token）。

poison 语义随之收敛（轮次 14 设计规则 1 的根治）：poison registry 按
wire sid 键控 = 按 capability 键控 = **只绑定实际 attempt**，不再可能
经稳定 SID 把一次 infra 抖动放大成任务级拉黑。
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

__all__ = ["SessionCapability", "mint_session_capability"]


@dataclass(frozen=True)
class SessionCapability:
    """一次 physical attempt 的会话凭证。

    token：秘密（wire sid + auth token 本体）。只允许出现在内存、
    CC 子进程环境与 HTTP 头；禁止写进 audit JSON/公开 artifact/日志。
    fingerprint：token 的 sha256 截断（`capfp-` 前缀），可安全落盘，
    用于把持久记录回链到当次会话而不暴露凭证。
    """

    token: str
    fingerprint: str
    physical_attempt_id: str | None


def capability_fingerprint(token: str) -> str:
    """token → 可落盘指纹（确定性；16 hex ≈ 64 bit 碰撞面，审计回链够用）。"""

    return "capfp-" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def mint_session_capability(physical_attempt_id: str | None) -> SessionCapability:
    """铸造一枚新 capability（128-bit 随机，`cap-` 前缀便于识别形状）。

    每次调用必然全新——同一逻辑执行的两次物理 attempt 拿到不同 token，
    这是"新 attempt 不受旧 closed 集合与 turn counter 影响"的机制本体。
    """

    token = "cap-" + secrets.token_hex(16)
    return SessionCapability(
        token=token,
        fingerprint=capability_fingerprint(token),
        physical_attempt_id=physical_attempt_id,
    )
