"""F2-2：每 physical attempt 的 session 授权凭证（capability）。

三层身份拓扑（F2-2 复核 P0-3 定稿——秘密只认证，标识符不保密）：

- **公开稳定身份**：trajectory_id / rollout_execution_id——审计、
  artifact 命名、GRPO 身份，跨物理 attempt 不变。
- **非秘密会话身份**：internal sid（`s-{physical_attempt_id}`）——
  guard 认证成功后把 Authorization 重写为它；slime 的 store/closed/
  turn-count、日志、X-SMG-Routing-Key、异常消息、audit 全部只见它。
  每 attempt 唯一，所以 slime 的 closed 集合与 turn counter 天然按
  attempt 隔离——replay 不沾旧状态。
- **秘密凭证**：capability token（`cap-` + 128-bit 随机）= CC 的
  ANTHROPIC_AUTH_TOKEN。**只用于认证**：guard 验证并兑换成 internal
  sid 后即出局，不进任何下游组件或持久面；token 绑定的会话拿
  internal sid 直接当 bearer 也会被拒（capability_required 集合）。

poison 语义随之收敛（轮次 14 设计规则 1 的根治）：poison registry 按
internal sid 键控 = 只绑定实际 attempt，不再可能经稳定 SID 把一次
infra 抖动放大成任务级拉黑。
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

__all__ = ["SessionCapability", "mint_session_capability"]


@dataclass(frozen=True)
class SessionCapability:
    """一次 physical attempt 的会话凭证（token = 秘密，仅认证用）。

    token 只允许出现在内存、CC 子进程环境与 Authorization 头；guard
    认证后立即兑换为非秘密 internal sid，禁止进入日志/审计/artifact。
    """

    token: str
    physical_attempt_id: str | None


def mint_session_capability(physical_attempt_id: str | None) -> SessionCapability:
    """铸造一枚新 capability（128-bit 随机，`cap-` 前缀便于识别形状）。

    每次调用必然全新——同一逻辑执行的两次物理 attempt 拿到不同 token，
    旧 token 随会话注销失效（registry 认证映射同事务清理）。
    """

    return SessionCapability(
        token="cap-" + secrets.token_hex(16),
        physical_attempt_id=physical_attempt_id,
    )
