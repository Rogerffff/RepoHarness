"""contracts 公共底座：严格 pydantic 基类、通用受限类型与 digest 工具。

设计原则（S1-1"宪法"级约定，所有契约模块共享）：

1. fail-closed：所有模型 `extra="forbid"`（未知字段一律拒收），`frozen=True`
   （对象一旦构造完成就是不可变 evidence，禁止事后篡改字段）。
2. 非法状态不可表示：能用 Literal / 受限类型 / 模型校验器排除的非法组合，
   一律在 schema 层拒绝，而不是等 gate 或人工审查兜底。
3. 引用而非载荷：token ids、logprobs、routing tape 等大对象只存 `ArtifactRef`
   （opaque 引用 + digest），契约对象本身不携带原始张量或私有文本，
   这也让 forbidden marker 扫描不会被海量正文淹没。
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# ---------------------------------------------------------------------------
# 通用受限类型
# ---------------------------------------------------------------------------

# 非空字符串：所有 id / 名称字段的最低要求（空串是最常见的"静默缺失"形态）。
NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]

# 安全标识符：沿用旧 rl/visibility.py 的 SAFE_IDENTIFIER_PATTERN 语义，
# 禁止路径分隔符 / 空白 / 前导符号，用于组件名、reason code、bundle 名等。
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
SafeIdentifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]

# sha256 digest：统一带 "sha256:" 前缀 + 64 位十六进制，
# 与 S1-0 的镜像 pin 写法一致（例如 sha256:a7317182…）。
Sha256Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]

# git commit sha：40 位十六进制（/testbed 血缘判据用）。
GitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class StrictModel(BaseModel):
    """所有 rh2 契约对象的基类：未知字段拒收 + 构造后不可变。

    `extra="forbid"` 是治理层的第一道防线：任何生产者悄悄塞进来的
    额外字段（例如把 golden patch 内容塞进某个临时 key）都会在
    schema 校验时直接失败，而不是被静默透传给下游。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactRef(StrictModel):
    """对 runtime-private 大对象（token ids / logprobs / tape / 日志）的 opaque 引用。

    继承重定位文档 §16.2 的规则："runtime-private artifact 只能通过 opaque ref
    被公开文件引用"。契约对象里永远不直接内嵌张量或原始文本，
    只存引用 id + 可选完整性 digest。
    """

    ref_id: SafeIdentifier = Field(
        description=(
            "artifact 存储层内的 opaque 引用 id（安全标识符，不允许本机绝对路径）。"
            "解析该 id 需要 artifact store 的访问权限，因此 ref 本身可以安全出现在"
            "审计 sidecar 里而不泄漏内容。"
        )
    )
    sha256: Sha256Digest | None = Field(
        default=None,
        description="被引用对象的 sha256 digest（可选）。提供后 inspector 可以重算比对，防篡改。",
    )
    byte_size: int | None = Field(
        default=None,
        ge=0,
        description="被引用对象的字节大小（可选，>=0），用于粗粒度一致性检查与容量核算。",
    )


def canonical_json_digest(data: Any) -> str:
    """对任意 JSON 可序列化对象计算规范化 sha256 digest（带 sha256: 前缀）。

    规范化规则：key 排序 + 最紧凑分隔符 + 不转义非 ASCII。
    EligibilityReport.facts_digest 等"报告自证"字段都用本函数计算，
    inspector 侧用同一函数重算比对（四步范式第一步：digest 重算）。
    """

    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
