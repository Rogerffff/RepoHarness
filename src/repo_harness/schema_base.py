"""共享的 Pydantic 基础设施。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """默认禁止未知字段，避免运行事实被悄悄写错位置。"""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def stable_hash(value: Any) -> str:
    """对 JSON 可序列化对象生成稳定 sha256。"""

    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
